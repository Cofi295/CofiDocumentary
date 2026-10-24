from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Callable
from urllib.parse import quote, unquote, urlparse
import uuid

import httpx

from .source_discovery import SourceDiscoveryHub
from .vision import EvidenceVerifier, MatchContract, VisionProvider


VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        for attempt in range(8):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                if attempt >= 7:
                    raise
                time.sleep(0.025 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def _tool(name: str) -> str | None:
    env_names = {
        "yt-dlp.exe": "COFI_YTDLP_BIN",
        "ffmpeg.exe": "COFI_FFMPEG_BIN",
        "ffprobe.exe": "COFI_FFPROBE_BIN",
    }
    configured = str(os.getenv(env_names.get(name, ""), "") or "").strip()
    if configured and Path(configured).exists():
        return configured
    bundled = Path(__file__).resolve().parents[1] / "tools" / name
    if bundled.exists():
        return str(bundled)
    return shutil.which(name) or shutil.which(Path(name).stem)


def _seconds(value: str) -> float:
    text = str(value or "").strip().replace(",", ".")
    parts = text.split(":")
    try:
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
        if len(parts) == 2:
            minutes, seconds = parts
            return float(minutes) * 60 + float(seconds)
    except ValueError:
        return 0.0
    return 0.0


def parse_webvtt(value: str) -> list[dict[str, Any]]:
    text = str(value or "").replace("\r\n", "\n")
    blocks = re.split(r"\n\s*\n", text)
    cues: list[dict[str, Any]] = []
    timing = re.compile(
        r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?[\.,]\d{3})\s+-->\s+"
        r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?[\.,]\d{3})"
    )
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), -1)
        if timing_index < 0:
            continue
        match = timing.search(lines[timing_index])
        if not match:
            continue
        cue_text = " ".join(lines[timing_index + 1:])
        cue_text = re.sub(r"<[^>]+>", " ", cue_text)
        cue_text = " ".join(cue_text.split())
        if not cue_text:
            continue
        cues.append({
            "start_sec": round(_seconds(match.group("start")), 3),
            "end_sec": round(_seconds(match.group("end")), 3),
            "text": cue_text,
        })
    return cues


def _tokens(value: str) -> set[str]:
    text = str(value or "").lower()
    return {
        token
        for token in re.findall(r"[\w가-힣ぁ-んァ-ヶ一-龯'-]{2,}", text, flags=re.UNICODE)
        if len(token) >= 2
    }


def _char_ngrams(value: str, size: int = 3) -> set[str]:
    compact = re.sub(r"\s+", "", str(value or "").lower())
    if len(compact) <= size:
        return {compact} if compact else set()
    return {compact[index:index + size] for index in range(len(compact) - size + 1)}


def _similarity(reference: str, candidate: str) -> float:
    left = _tokens(reference)
    right = _tokens(candidate)
    token_score = len(left & right) / max(1, len(left))
    left_grams = _char_ngrams(reference)
    right_grams = _char_ngrams(candidate)
    gram_score = len(left_grams & right_grams) / max(1, len(left_grams))
    return token_score * 0.72 + gram_score * 0.28


def best_transcript_window(
    cues: list[dict[str, Any]],
    *,
    voice_text: str,
    visual_description: str = "",
    target_duration_sec: float = 10.0,
) -> dict[str, Any]:
    if not cues:
        return {"start_sec": 0.0, "end_sec": max(8.0, float(target_duration_sec)), "text": "", "score": 0.0}
    reference = " ".join(value for value in (voice_text, visual_description) if str(value).strip())
    target = max(6.0, float(target_duration_sec or 0.0))
    best: dict[str, Any] | None = None
    for index, cue in enumerate(cues):
        start = max(0.0, float(cue.get("start_sec") or 0.0) - 2.0)
        end_limit = start + target + 4.0
        selected: list[dict[str, Any]] = []
        for row in cues[index:]:
            row_start = float(row.get("start_sec") or 0.0)
            if row_start > end_limit and selected:
                break
            selected.append(row)
            if float(row.get("end_sec") or row_start) >= end_limit:
                break
        text = " ".join(str(row.get("text") or "") for row in selected).strip()
        score = _similarity(reference, text)
        raw_end = float(selected[-1].get("end_sec") or start + target) if selected else start + target
        end = min(max(raw_end, start + target), end_limit)
        # Documentary beats never need more than 20-25 seconds from a single candidate clip
        end = min(end, start + 25.0)
        candidate = {
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "text": text,
            "score": round(score, 4),
        }
        if best is None or candidate["score"] > best["score"]:
            best = candidate
    if best is not None:
        best["end_sec"] = min(float(best["end_sec"]), float(best["start_sec"]) + 25.0)
        return best
    return {"start_sec": 0.0, "end_sec": target, "text": "", "score": 0.0}


def _timecode(seconds: float) -> str:
    total = max(0, int(round(float(seconds))))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@dataclass(slots=True)
class MediaRetriever:
    runner: Callable[..., Any] = subprocess.run
    library_root: str | Path | None = None
    client: Any | None = None

    def __post_init__(self) -> None:
        configured = self.library_root or os.getenv("COFI_FOOTAGE_LIBRARY_DIR")
        if configured:
            self.library_root = Path(configured).resolve()
        else:
            self.library_root = (Path(__file__).resolve().parents[1] / "data" / "footage_library").resolve()
        Path(self.library_root).mkdir(parents=True, exist_ok=True)
        if self.client is None:
            self.client = httpx.Client(
                timeout=max(3.0, float(os.getenv("COFI_FOOTAGE_IMAGE_TIMEOUT_SEC", "20") or 20)),
                follow_redirects=True,
                headers={"User-Agent": "COFI-Documentary/1.0 footage-retriever"},
            )

    def _run(self, command: list[str], *, timeout: int = 180) -> Any:
        kwargs: dict[str, Any] = {
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": timeout,
            "check": False,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
            startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
            kwargs["startupinfo"] = startupinfo
        try:
            return self.runner(command, **kwargs)
        except Exception as exc:
            class _FailedResult:
                returncode = 1
                stdout = ""
                stderr = str(exc)
            return _FailedResult()

    @staticmethod
    def _archive_identifier(source_url: str) -> str:
        parsed = urlparse(str(source_url or ""))
        host = (parsed.hostname or "").lower()
        if host != "archive.org" and not host.endswith(".archive.org"):
            return ""
        parts = [unquote(part).strip() for part in parsed.path.split("/") if part.strip()]
        if len(parts) < 2 or parts[0].lower() != "details":
            return ""
        return parts[1]

    @staticmethod
    def _archive_file_size(value: Any) -> int:
        try:
            return max(0, int(str(value or "0").strip()))
        except (TypeError, ValueError):
            return 0

    def _archive_derivative_url(self, source_url: str) -> str:
        """Resolve an Archive item page to a bounded, streamable video derivative."""
        identifier = self._archive_identifier(source_url)
        if not identifier:
            return source_url
        try:
            response = self.client.get(
                f"https://archive.org/metadata/{quote(identifier, safe='')}",
                timeout=max(3.0, float(os.getenv("COFI_FOOTAGE_ARCHIVE_METADATA_TIMEOUT_SEC", "8") or 8)),
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise RuntimeError(f"Archive metadata lookup failed: {exc}") from exc

        choices: list[tuple[int, int, str]] = []
        for row in payload.get("files") or []:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            suffix = Path(name).suffix.lower()
            if suffix not in {".mp4", ".m4v", ".webm"}:
                continue
            fmt = str(row.get("format") or "").lower()
            source_kind = str(row.get("source") or "").lower()
            size = self._archive_file_size(row.get("size"))
            # Prefer H.264/MPEG4 derivatives. Avoid giant masters because a
            # short footage window should never require multi-GB remote reads.
            score = 0
            if suffix == ".mp4":
                score += 100
            elif suffix == ".m4v":
                score += 80
            else:
                score += 55
            if "h.264" in fmt or "h264" in fmt or "mpeg4" in fmt or "mpeg-4" in fmt:
                score += 30
            if source_kind == "derivative":
                score += 25
            elif source_kind == "original":
                score -= 25
            if 0 < size <= 750 * 1024 * 1024:
                score += 20
            elif size > 1500 * 1024 * 1024:
                score -= 80
            choices.append((score, size or 2**63 - 1, name))

        if not choices:
            raise RuntimeError("Archive item has no bounded MP4/WebM derivative")
        choices.sort(key=lambda item: (-item[0], item[1], item[2].lower()))
        best_score, _size, best_name = choices[0]
        if best_score < 40:
            raise RuntimeError("Archive item has no suitable streamable video derivative")
        return f"https://archive.org/download/{quote(identifier, safe='')}/{quote(best_name, safe='/')}"

    def _cache_dir(self, workspace: Path, source_url: str) -> Path:
        digest = hashlib.sha256(source_url.encode("utf-8", errors="ignore")).hexdigest()[:20]
        path = Path(self.library_root) / "sources" / digest
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _window_dir(source_root: Path, start_sec: float, end_sec: float) -> Path:
        key = f"{max(0.0, float(start_sec)):.3f}-{max(float(start_sec) + 1.0, float(end_sec)):.3f}"
        digest = hashlib.sha256(key.encode("ascii")).hexdigest()[:12]
        path = source_root / "windows" / digest
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _metadata(self, source_url: str) -> dict[str, Any]:
        ytdlp = _tool("yt-dlp.exe")
        if not ytdlp:
            raise RuntimeError("Missing yt-dlp for local Footage Engine")
        result = self._run([ytdlp, "--quiet", "--no-warnings", "--dump-single-json", "--skip-download", source_url])
        if int(getattr(result, "returncode", 1)) != 0:
            return {}
        try:
            payload = json.loads(str(getattr(result, "stdout", "") or "{}"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _subtitles(self, source_url: str, root: Path, language: str) -> list[dict[str, Any]]:
        cached = sorted(root.glob("source*.vtt"))
        if not cached:
            ytdlp = _tool("yt-dlp.exe")
            if not ytdlp:
                return []
            langs = [value for value in [language, "en", "ko", "vi", "ja"] if str(value).strip()]
            seen: set[str] = set()
            ordered_langs = [item for item in langs if not (item in seen or seen.add(item))]
            command = [
                ytdlp,
                "--quiet",
                "--no-warnings",
                "--skip-download",
                "--write-subs",
                "--write-auto-subs",
                "--sub-format",
                "vtt",
                "--sub-langs",
                ",".join(ordered_langs),
                "-o",
                str(root / "source.%(ext)s"),
                source_url,
            ]
            self._run(command, timeout=120)
            cached = sorted(root.glob("source*.vtt"))
        cues: list[dict[str, Any]] = []
        for path in cached[:3]:
            try:
                cues.extend(parse_webvtt(path.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                continue
        cues.sort(key=lambda item: (float(item.get("start_sec") or 0), float(item.get("end_sec") or 0)))
        return cues

    def _download_window(self, source_url: str, root: Path, start_sec: float, end_sec: float) -> Path:
        existing = [path for path in root.glob("clip.*") if path.suffix.lower() in VIDEO_EXTENSIONS and path.is_file()]
        if existing:
            return existing[0]
        ytdlp = _tool("yt-dlp.exe")
        if not ytdlp:
            raise RuntimeError("Missing yt-dlp for local Footage Engine")
        archive_identifier = self._archive_identifier(source_url)
        download_url = self._archive_derivative_url(source_url) if archive_identifier else source_url
        max_clip_sec = max(10.0, float(os.getenv("COFI_FOOTAGE_MAX_CLIP_SEC", "25.0") or 25.0))
        capped_end = min(float(end_sec), float(start_sec) + max_clip_sec)
        section = f"*{max(0.0, start_sec):.3f}-{max(start_sec + 1.0, capped_end):.3f}"
        command = [
            ytdlp,
            "--quiet",
            "--no-warnings",
            "--download-sections",
            section,
            "--force-keyframes-at-cuts",
            "-f",
            "bv*[height<=720]+ba/b[height<=720]/b",
            "--merge-output-format",
            "mp4",
            "-o",
            str(root / "clip.%(ext)s"),
            download_url,
        ]
        if archive_identifier:
            section_timeout = max(10, int(os.getenv("COFI_FOOTAGE_ARCHIVE_SECTION_TIMEOUT_SEC", "35") or 35))
        else:
            section_timeout = max(15, int(os.getenv("COFI_FOOTAGE_SECTION_TIMEOUT_SEC", "60") or 60))
        result = self._run(command, timeout=section_timeout)
        files = [path for path in root.glob("clip.*") if path.suffix.lower() in VIDEO_EXTENSIONS and path.is_file()]
        if int(getattr(result, "returncode", 1)) == 0 and files:
            return files[0]

        for partial in root.glob("clip*.part"):
            partial.unlink(missing_ok=True)

        # Never download a full long-form source just to inspect a short footage
        # window. Archive and other documentary sources can be multi-GB, while
        # YouTube DASH URLs sometimes need the embedded client for ranged cuts.
        host = (urlparse(source_url).hostname or "").lower()
        youtube_source = host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")
        if not youtube_source:
            error = str(getattr(result, "stderr", "") or "").strip()[-400:]
            raise RuntimeError(f"yt-dlp bounded section download failed: {error or 'no output file'}")

        embedded_command = [
            ytdlp,
            "--quiet",
            "--no-warnings",
            "--extractor-args",
            "youtube:player_client=web_embedded",
            "--download-sections",
            section,
            "--force-keyframes-at-cuts",
            "-f",
            "bv*[height<=720]+ba/b[height<=720]/b",
            "--merge-output-format",
            "mp4",
            "-o",
            str(root / "clip.%(ext)s"),
            source_url,
        ]
        retry_result = self._run(embedded_command, timeout=section_timeout)
        files = [path for path in root.glob("clip.*") if path.suffix.lower() in VIDEO_EXTENSIONS and path.is_file()]
        if int(getattr(retry_result, "returncode", 1)) != 0 or not files:
            error = str(getattr(retry_result, "stderr", "") or "").strip()[-400:]
            raise RuntimeError(f"yt-dlp bounded YouTube retry failed: {error or 'no output file'}")
        return files[0]

    def _duration(self, path: Path) -> float:
        ffprobe = _tool("ffprobe.exe")
        if not ffprobe:
            return 0.0
        result = self._run([
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ], timeout=30)
        try:
            return max(0.0, float(str(getattr(result, "stdout", "") or "0").strip()))
        except ValueError:
            return 0.0

    def _download_still(self, candidate: dict[str, Any], root: Path) -> Path:
        existing = [path for path in root.glob("still.*") if path.suffix.lower() in IMAGE_EXTENSIONS and path.is_file()]
        if existing:
            return existing[0]
        urls = [
            str(candidate.get("source_url") or "").strip(),
            str(candidate.get("thumbnail_url") or "").strip(),
        ]
        seen: set[str] = set()
        errors: list[str] = []
        for url in urls:
            if not url or url.lower() in seen:
                continue
            seen.add(url.lower())
            try:
                response = self.client.get(url)
                response.raise_for_status()
                raw = bytes(response.content)
                if not raw:
                    raise RuntimeError("empty image response")
                if len(raw) > 25 * 1024 * 1024:
                    raise RuntimeError("image is larger than 25 MB")
                content_type = str(response.headers.get("content-type") or "").lower()
                suffix = Path(url.split("?", 1)[0]).suffix.lower()
                if suffix not in IMAGE_EXTENSIONS:
                    if "png" in content_type:
                        suffix = ".png"
                    elif "webp" in content_type:
                        suffix = ".webp"
                    elif "gif" in content_type:
                        suffix = ".gif"
                    else:
                        suffix = ".jpg"
                target = root / f"still{suffix}"
                target.write_bytes(raw)
                try:
                    from PIL import Image

                    with Image.open(target) as image:
                        image.verify()
                except Exception as exc:
                    target.unlink(missing_ok=True)
                    raise RuntimeError(f"invalid image: {exc}") from exc
                return target
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
        raise RuntimeError("could not download still candidate: " + " | ".join(errors[-2:]))

    def _frames(self, path: Path, root: Path, count: int = 4) -> list[str]:
        ffmpeg = _tool("ffmpeg.exe")
        if not ffmpeg:
            raise RuntimeError("Missing ffmpeg for local Footage Engine")
        duration = self._duration(path)
        if duration <= 0.2:
            raise RuntimeError("Candidate clip has no usable duration")
        frame_dir = root / "frames"
        frame_dir.mkdir(parents=True, exist_ok=True)
        frames: list[str] = []
        for index in range(max(1, int(count))):
            position = duration * ((index + 1) / (count + 1))
            target = frame_dir / f"frame_{index + 1:02d}.jpg"
            if not target.exists():
                result = self._run([
                    ffmpeg,
                    "-hide_banner", "-loglevel", "error",
                    "-ss", f"{position:.3f}",
                    "-i", str(path),
                    "-frames:v", "1",
                    "-q:v", "3",
                    "-y",
                    str(target),
                ], timeout=45)
                if int(getattr(result, "returncode", 1)) != 0:
                    continue
            if target.exists() and target.stat().st_size > 0:
                frames.append(str(target))
        if not frames:
            raise RuntimeError("Could not extract representative frames from candidate clip")
        return frames

    def prepare(
        self,
        candidate: dict[str, Any],
        beat: dict[str, Any],
        workspace: str | Path,
        job: dict[str, Any],
    ) -> dict[str, Any]:
        workspace = Path(workspace).resolve()
        source_url = str(candidate.get("source_url") or "").strip()
        if not source_url:
            raise RuntimeError("Candidate has no source_url")
        root = self._cache_dir(workspace, source_url)
        kind = str(candidate.get("kind") or "video").strip().lower()
        if kind in {"still", "image", "sourced_still"}:
            still = self._download_still(candidate, root)
            title = str(candidate.get("title") or "")
            description = str(candidate.get("description") or "")
            reference = " ".join(filter(None, [
                str(beat.get("narration_text") or ""),
                str(beat.get("visual_description") or ""),
            ]))
            return {
                "local_path": str(still),
                "frames": [str(still)],
                "transcript": "",
                "transcript_score": round(_similarity(reference, f"{title} {description}"), 4),
                "timestamp_range": "",
                "metadata": {
                    "title": title,
                    "uploader": str(candidate.get("source_name") or ""),
                    "duration": None,
                    "webpage_url": str(candidate.get("source_page") or source_url),
                    "description": description[:1200],
                },
            }
        metadata = self._metadata(source_url)
        language = str(job.get("language") or "").strip()
        cues = self._subtitles(source_url, root, language)
        window = best_transcript_window(
            cues,
            voice_text=str(beat.get("narration_text") or ""),
            visual_description=str(beat.get("visual_description") or ""),
            target_duration_sec=float(beat.get("target_duration_sec") or 10.0),
        )
        window_root = self._window_dir(root, float(window["start_sec"]), float(window["end_sec"]))
        clip = self._download_window(source_url, window_root, float(window["start_sec"]), float(window["end_sec"]))
        frames = self._frames(clip, window_root)
        return {
            "local_path": str(clip),
            "frames": frames,
            "transcript": str(window.get("text") or ""),
            "transcript_score": float(window.get("score") or 0.0),
            "timestamp_range": f"{_timecode(float(window['start_sec']))}-{_timecode(float(window['end_sec']))}",
            "metadata": {
                "title": str(metadata.get("title") or candidate.get("title") or ""),
                "uploader": str(metadata.get("uploader") or candidate.get("source_name") or ""),
                "duration": metadata.get("duration"),
                "webpage_url": str(metadata.get("webpage_url") or source_url),
                "description": str(metadata.get("description") or candidate.get("description") or "")[:1200],
            },
        }


class FootageEngine:
    def __init__(
        self,
        *,
        source_discovery: Any | None = None,
        retriever: Any | None = None,
        vision_provider: VisionProvider | None = None,
        verifier: EvidenceVerifier | None = None,
        max_candidates_per_beat: int | None = None,
        max_candidates_per_provider: int | None = None,
    ) -> None:
        self.source_discovery = source_discovery or SourceDiscoveryHub()
        self.retriever = retriever or MediaRetriever()
        self.vision_provider = vision_provider
        self.verifier = verifier or EvidenceVerifier()
        configured = max_candidates_per_beat if max_candidates_per_beat is not None else os.getenv("COFI_VISION_CANDIDATES_PER_BEAT", "12")
        try:
            self.max_candidates_per_beat = max(1, min(20, int(configured)))
        except (TypeError, ValueError):
            self.max_candidates_per_beat = 3
        configured_provider = (
            max_candidates_per_provider
            if max_candidates_per_provider is not None
            else os.getenv("COFI_FOOTAGE_CANDIDATES_PER_PROVIDER", "2")
        )
        try:
            self.max_candidates_per_provider = max(1, min(8, int(configured_provider)))
        except (TypeError, ValueError):
            self.max_candidates_per_provider = 2
        try:
            self.max_total_candidates_per_beat = max(
                self.max_candidates_per_provider,
                min(20, int(os.getenv("COFI_FOOTAGE_MAX_CANDIDATES_PER_BEAT", "4") or 4)),
            )
        except (TypeError, ValueError):
            self.max_total_candidates_per_beat = 4
        try:
            self.download_workers = max(
                1,
                min(6, int(os.getenv("COFI_FOOTAGE_DOWNLOAD_WORKERS", "4") or 4)),
            )
        except (TypeError, ValueError):
            self.download_workers = 4

    def _materialize_candidates(
        self,
        specs: list[dict[str, Any]],
        beat: dict[str, Any],
        workspace: Path,
        job: dict[str, Any],
        *,
        control_callback: Callable[[], None] | None,
        failures: list[dict[str, Any]],
        unavailable_sources: dict[str, tuple[str, str]],
    ) -> dict[int, dict[str, Any]]:
        """Download/cut independent candidates with a small bounded worker pool."""
        if not specs:
            return {}

        materials: dict[int, dict[str, Any]] = {}
        worker_count = min(self.download_workers, len(specs))

        def prepare_one(spec: dict[str, Any]) -> dict[str, Any]:
            return self.retriever.prepare(spec["source"], beat, workspace, job)

        def record_live(spec: dict[str, Any], material: dict[str, Any]) -> None:
            path = str(material.get("local_path") or "").strip()
            if not path:
                return
            manifest_path = workspace / "footage_live_downloads.json"
            try:
                existing = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
            except (OSError, json.JSONDecodeError):
                existing = {}
            items = existing.get("items") if isinstance(existing, dict) else []
            if not isinstance(items, list):
                items = []
            source_url = str(spec.get("source_url") or "")
            key = (str(beat.get("beat_id") or ""), source_url, path)
            if not any(
                (
                    str(row.get("beat_id") or ""),
                    str(row.get("source_url") or ""),
                    str(row.get("path") or ""),
                ) == key
                for row in items
                if isinstance(row, dict)
            ):
                source = spec.get("source") if isinstance(spec.get("source"), dict) else {}
                items.append({
                    "beat_id": str(beat.get("beat_id") or ""),
                    "path": path,
                    "source_url": source_url,
                    "name": Path(path).name,
                    "kind": str(source.get("kind") or "video"),
                    "downloaded_at": _now(),
                })
            _write_json_atomic(manifest_path, {"version": 1, "updated_at": _now(), "items": items})

        if worker_count <= 1:
            for spec in specs:
                if control_callback is not None:
                    control_callback()
                try:
                    material = prepare_one(spec)
                    materials[int(spec["index"])] = material
                    record_live(spec, material)
                except Exception as exc:
                    error_type = type(exc).__name__
                    error = str(exc)[:500]
                    source_url = str(spec["source_url"])
                    unavailable_sources[source_url] = (error_type, error)
                    failures.append({
                        "beat_id": str(beat.get("beat_id") or ""),
                        "source_url": source_url,
                        "error_type": error_type,
                        "error": error,
                    })
            return materials

        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="cofi-footage") as executor:
            pending = {executor.submit(prepare_one, spec): spec for spec in specs}
            for future in as_completed(pending):
                if control_callback is not None:
                    control_callback()
                spec = pending[future]
                source_url = str(spec["source_url"])
                try:
                    material = future.result()
                    materials[int(spec["index"])] = material
                    record_live(spec, material)
                except Exception as exc:
                    error_type = type(exc).__name__
                    error = str(exc)[:500]
                    unavailable_sources[source_url] = (error_type, error)
                    failures.append({
                        "beat_id": str(beat.get("beat_id") or ""),
                        "source_url": source_url,
                        "error_type": error_type,
                        "error": error,
                    })
        return materials

    def health(self) -> dict[str, Any]:
        if self.vision_provider is not None:
            provider_health = self.vision_provider.health()
        else:
            provider_health = {
                "ok": True,
                "provider": "ai-router",
                "role": "final-media-review",
                "local_vision_required": False,
            }
        semantic = getattr(self.source_discovery, "semantic_reranker", None)
        semantic_health = (
            semantic.health()
            if semantic is not None and callable(getattr(semantic, "health", None))
            else {"ok": True, "provider": "metadata-ranking", "enabled": False}
        )
        yt_dlp = bool(_tool("yt-dlp.exe"))
        ffmpeg = bool(_tool("ffmpeg.exe"))
        ffprobe = bool(_tool("ffprobe.exe"))
        source_tools = [
            str(getattr(provider, "name", provider.__class__.__name__)).strip()
            for provider in (getattr(self.source_discovery, "providers", None) or [])
        ]
        return {
            "ok": bool(provider_health.get("ok")) and ffmpeg and ffprobe,
            "vision": provider_health,
            "semantic_prefilter": semantic_health,
            "yt_dlp": yt_dlp,
            "ffmpeg": ffmpeg,
            "ffprobe": ffprobe,
            "source_tools": source_tools,
            "search_mode": "tools-only",
            "review_mode": "selected-ai-router",
            "download_workers": self.download_workers,
        }

    @staticmethod
    def _candidate_id(beat_id: str, source_url: str, index: int) -> str:
        digest = hashlib.sha256(source_url.encode("utf-8", errors="ignore")).hexdigest()[:8]
        return f"FT-{beat_id}-{index:02d}-{digest}"

    def prepare(
        self,
        job: dict[str, Any],
        beats: list[dict[str, Any]],
        workspace: str | Path,
        *,
        control_callback: Callable[[], None] | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
        discovery_progress_callback: Callable[[int, int, str, str], None] | None = None,
        prepared_beat_callback: Callable[[dict[str, Any], list[dict[str, Any]], int, int], None] | None = None,
        reset_live_downloads: bool = True,
        persist_queue: bool = True,
    ) -> dict[str, Any]:
        workspace = Path(workspace).resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        if reset_live_downloads:
            _write_json_atomic(
                workspace / "footage_live_downloads.json",
                {"version": 1, "updated_at": _now(), "items": []},
            )
        if control_callback is not None:
            control_callback()
        discover = self.source_discovery.discover_for_beats
        try:
            discovered = discover(
                job,
                beats,
                workspace,
                control_callback=control_callback,
                progress_callback=discovery_progress_callback,
            )
        except TypeError as exc:
            # Keep injected/test discovery adapters compatible while the real
            # SourceDiscoveryHub supports cooperative pause/stop callbacks.
            if "control_callback" not in str(exc) and "progress_callback" not in str(exc):
                raise
            discovered = discover(job, beats, workspace)
        candidate_rows: list[dict[str, Any]] = []
        queue_beats: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        unavailable_sources: dict[str, tuple[str, str]] = {}
        total_beats = len([beat for beat in beats if str(beat.get("beat_id") or "").strip()])
        completed_beats = 0

        for beat in beats:
            if control_callback is not None:
                control_callback()
            beat_id = str(beat.get("beat_id") or "").strip()
            if not beat_id:
                continue
            contract = MatchContract.from_beat(beat)
            prepared_for_beat: list[dict[str, Any]] = []
            excluded_source_urls = {
                str(value or "").strip().lower()
                for value in (beat.get("footage_excluded_source_urls") or [])
                if str(value or "").strip()
            }
            source_rows = discovered.get(beat_id) if isinstance(discovered, dict) else []
            provider_counts: dict[str, int] = {}
            search_pool_limit = (
                self.max_candidates_per_beat * 3
                if self.vision_provider is not None
                else min(len(source_rows or []), self.max_total_candidates_per_beat * 3)
            )
            material_specs: list[dict[str, Any]] = []
            seen_source_urls: set[str] = set()
            planned_provider_counts: dict[str, int] = {}
            for index, source in enumerate((source_rows or [])[:search_pool_limit], start=1):
                if control_callback is not None:
                    control_callback()
                if not isinstance(source, dict):
                    continue
                provider_name = str(source.get("provider") or "unknown").strip().lower() or "unknown"
                source_url = str(source.get("source_url") or "").strip()
                if not source_url:
                    continue
                if source_url.lower() in excluded_source_urls:
                    continue
                source_key = source_url.lower()
                if source_key in seen_source_urls:
                    continue
                seen_source_urls.add(source_key)
                cached_failure = unavailable_sources.get(source_url)
                if cached_failure:
                    error_type, error = cached_failure
                    failures.append({
                        "beat_id": beat_id,
                        "source_url": source_url,
                        "error_type": error_type,
                        "error": error,
                        "cached": True,
                    })
                    continue
                if self.vision_provider is None:
                    if planned_provider_counts.get(provider_name, 0) >= self.max_candidates_per_provider:
                        continue
                    if len(material_specs) >= self.max_total_candidates_per_beat:
                        break
                material_specs.append({
                    "index": index,
                    "source": source,
                    "source_url": source_url,
                    "provider_name": provider_name,
                })
                if self.vision_provider is None:
                    planned_provider_counts[provider_name] = planned_provider_counts.get(provider_name, 0) + 1

            materials = self._materialize_candidates(
                material_specs,
                beat,
                workspace,
                job,
                control_callback=control_callback,
                failures=failures,
                unavailable_sources=unavailable_sources,
            )

            for spec in material_specs:
                if control_callback is not None:
                    control_callback()
                index = int(spec["index"])
                source = spec["source"]
                source_url = str(spec["source_url"])
                provider_name = str(spec["provider_name"])
                material = materials.get(index)
                if material is None:
                    continue
                if self.vision_provider is None and provider_counts.get(provider_name, 0) >= self.max_candidates_per_provider:
                    continue
                verdict: dict[str, Any] | None = None
                if self.vision_provider is not None:
                    try:
                        evidence = self.vision_provider.verify(
                            voice_text=str(beat.get("narration_text") or ""),
                            frames=[Path(path) for path in (material.get("frames") or [])],
                            transcript=str(material.get("transcript") or ""),
                            metadata=dict(material.get("metadata") or {}),
                            contract=contract,
                        )
                        verdict = self.verifier.decide(contract, evidence)
                    except Exception as exc:
                        failures.append({
                            "beat_id": beat_id,
                            "source_url": source_url,
                            "error_type": type(exc).__name__,
                            "error": str(exc)[:500],
                        })
                        continue
                    if verdict["decision"] == "REJECT":
                        continue
                semantic_score = float(source.get("semantic_score") or 0.0)
                verification_provider = (
                    str(getattr(self.vision_provider, "name", "vision"))
                    if self.vision_provider is not None
                    else str(source.get("semantic_provider") or "metadata-semantic")
                )
                candidate = {
                    "candidate_id": self._candidate_id(beat_id, source_url, index),
                    "beat_id": beat_id,
                    "source_priority": str(beat.get("source_priority") or "prefer_real"),
                    "decision": "REVIEW",
                    "verification_provider": verification_provider,
                    "visually_inspected_actual_content": self.vision_provider is not None,
                    "source_url": source_url,
                    "source_name": str(source.get("source_name") or ""),
                    "title": str(source.get("title") or ""),
                    "local_path": str(material.get("local_path") or ""),
                    "kind": str(source.get("kind") or "video").replace("video", "sourced_video"),
                    "timestamp_range": str(material.get("timestamp_range") or ""),
                    "rights_risk": str(source.get("rights_risk") or "UNKNOWN"),
                    "reason": str(
                        (verdict or {}).get("summary")
                        or "Semantic source match prepared locally; waiting for Codex/Gemini final media review."
                    ),
                    "semantic_prefilter": {
                        "semantic_score": semantic_score,
                        "semantic_text_score": source.get("semantic_text_score"),
                        "visual_semantic_score": source.get("visual_semantic_score"),
                        "provider": str(source.get("semantic_provider") or "metadata-semantic"),
                        "discovery_score": source.get("discovery_score"),
                    },
                    "representative_frames": [str(path) for path in (material.get("frames") or [])],
                    "transcript_excerpt": str(material.get("transcript") or "")[:1600],
                    "transcript_score": float(material.get("transcript_score") or 0.0),
                    "source_metadata": dict(material.get("metadata") or {}),
                    "verification_contract": contract.as_prompt_payload(),
                    "real_video_search_complete": True,
                    "real_still_search_complete": True,
                    "ai_fallback_recommended": False,
                }
                if self.vision_provider is not None and verdict is not None:
                    candidate["local_vision_decision"] = verdict["decision"]
                    candidate["local_vision_verification"] = verdict
                prepared_for_beat.append(candidate)
                candidate_rows.append(candidate)
                if self.vision_provider is not None:
                    if len(prepared_for_beat) >= self.max_candidates_per_beat:
                        break
                else:
                    provider_counts[provider_name] = provider_counts.get(provider_name, 0) + 1
                    if len(prepared_for_beat) >= self.max_total_candidates_per_beat:
                        break
            queue_beats.append({
                "beat_id": beat_id,
                "voice_text": str(beat.get("narration_text") or ""),
                "visual_description": str(beat.get("visual_description") or ""),
                "candidates": prepared_for_beat,
                "needs_codex_review": bool(prepared_for_beat),
                "needs_fallback": not prepared_for_beat,
            })
            completed_beats += 1
            partial_queue = {
                "version": 1,
                "provider": str(getattr(self.vision_provider, "name", "semantic+ai-review")) if self.vision_provider is not None else "semantic+ai-review",
                "status": "running" if completed_beats < total_beats else "completed",
                "updated_at": _now(),
                "completed_beats": completed_beats,
                "total_beats": total_beats,
                "beats": queue_beats,
                "failures": failures,
            }
            if persist_queue:
                _write_json_atomic(workspace / "footage_candidate_queue.json", partial_queue)
            if progress_callback is not None:
                progress_callback(completed_beats, total_beats, beat_id)
            if prepared_beat_callback is not None:
                prepared_beat_callback(beat, prepared_for_beat, completed_beats, total_beats)
            if control_callback is not None:
                control_callback()

        queue = {
            "version": 1,
            "provider": str(getattr(self.vision_provider, "name", "semantic+ai-review")) if self.vision_provider is not None else "semantic+ai-review",
            "status": "completed",
            "updated_at": _now(),
            "completed_beats": completed_beats,
            "total_beats": total_beats,
            "beats": queue_beats,
            "failures": failures,
        }
        if persist_queue:
            _write_json_atomic(workspace / "footage_candidate_queue.json", queue)
        return {
            "worker": "vision",
            "status": "completed",
            "candidates": candidate_rows,
            "assets": [],
            "native_treatments": [],
            "presentation_effects": [],
            "queue_path": str(workspace / "footage_candidate_queue.json") if persist_queue else "",
            "failures": failures,
        }

