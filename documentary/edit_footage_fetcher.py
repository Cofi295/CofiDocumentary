from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from typing import Any
import urllib.parse
import urllib.request

from .editorial_brain import measure_clip_signalstats
from .footage_engine import best_transcript_window, parse_webvtt
from .remotion import RemotionManager
from .render_cache import background_worker_creationflags, detect_hardware_profile
from PIL import Image, ImageDraw


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _subproc_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = background_worker_creationflags()
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = startupinfo
    return kwargs


def _edit_ffmpeg_threads() -> str:
    try:
        return str(max(1, int(detect_hardware_profile().get("edit_ffmpeg_threads") or 2)))
    except Exception:
        return "2"


_THREAD_REGISTRY_LOCKS_GUARD = threading.Lock()
_THREAD_REGISTRY_LOCKS: dict[str, threading.RLock] = {}


def _ytdlp_max_height() -> int:
    """Cap archival source downloads to 720p by default for 3x faster fetching."""
    try:
        val = int(os.getenv("COFI_FOOTAGE_MAX_HEIGHT", "720") or 720)
    except (TypeError, ValueError):
        val = 720
    return max(480, min(1080, val))


def _ytdlp_format_selector(*, include_audio: bool = False) -> str:
    h = _ytdlp_max_height()
    if include_audio:
        return f"bestvideo[height<={h}][ext=mp4]+bestaudio/best[height<={h}][ext=mp4]/best[height<={h}]/best"
    return f"bestvideo[height<={h}][ext=mp4]/best[height<={h}][ext=mp4]/best[height<={h}]/best"


@contextmanager
def _workspace_registry_lock(workspace: Path, *, timeout_sec: float = 30.0):
    """Cross-thread and cross-process lock protecting shared footage JSON registries."""
    key = str(Path(workspace).resolve())
    with _THREAD_REGISTRY_LOCKS_GUARD:
        t_lock = _THREAD_REGISTRY_LOCKS.setdefault(key, threading.RLock())
    lock_file = Path(workspace) / ".producer" / ".footage_registry.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with t_lock:
        fd: int | None = None
        deadline = time.monotonic() + timeout_sec
        while True:
            try:
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(fd, f"{os.getpid()}".encode("ascii", errors="ignore"))
                break
            except FileExistsError:
                try:
                    if time.time() - lock_file.stat().st_mtime > 30.0:
                        lock_file.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.05)
            except OSError:
                break
        try:
            yield
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                try:
                    lock_file.unlink(missing_ok=True)
                except OSError:
                    pass


class EditDirectFootageFetcher:
    """Allows the Edit AI Agent to search, download, trim, and publish real B-roll footage directly during Edit."""

    def __init__(
        self,
        workspace: str | Path,
        remotion_dir: str | Path | None = None,
        job_id: str | None = None,
    ):
        self.workspace = Path(workspace).resolve()
        self.remotion_dir = (
            Path(remotion_dir).resolve()
            if remotion_dir
            else Path(__file__).resolve().parents[1] / "CofiRemotion"
        )
        self.job_id = str(job_id or self.workspace.name).strip()
        self.media_dir = self.workspace / "media" / "edit_footage"
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.ytdlp = _tool("yt-dlp.exe")
        self.ffmpeg = _tool("ffmpeg.exe")
        self.ffprobe = _tool("ffprobe.exe")

    def _read_json(self, path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
        if not path.exists():
            return dict(default or {})
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else dict(default or {})
        except Exception:
            return dict(default or {})

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        import time
        from uuid import uuid4

        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        tmp = path.parent / f".{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp"
        tmp.write_text(serialized, encoding="utf-8")
        for attempt in range(6):
            try:
                tmp.replace(path)
                return
            except PermissionError:
                if attempt < 5:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                try:
                    path.write_text(serialized, encoding="utf-8")
                finally:
                    tmp.unlink(missing_ok=True)
                return

    _NOISE_TITLE_RE = re.compile(
        r"(?:#shorts|\bshorts\b|\btiktok\b|\breaction\b|\bpodcast\b|\bcommentary\b|\bvlog\b|游戏|动漫|搞笑|鬼畜|解说|盘点|说案|讲案|合集|片头|片尾)",
        re.IGNORECASE,
    )
    _CJK_RE = re.compile(r"[\u4e00-\u9fff]")

    def _is_director_v2_profile(self, job: dict[str, Any] | None = None) -> bool:
        payload = job if isinstance(job, dict) else self._read_json(self.workspace / "input.json", {})
        prof_id = str(
            payload.get("channel_profile_id")
            or ((payload.get("channel_profile_snapshot") or {}).get("id") if isinstance(payload.get("channel_profile_snapshot"), dict) else "")
            or ""
        ).strip()
        ed_dna = payload.get("editing_dna") if isinstance(payload.get("editing_dna"), dict) else {}
        preset_id = str(ed_dna.get("preset_id") or "").strip()
        return prof_id in {"channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2"} or preset_id == "forensic_noir_director_v2"

    def _search_cctv_video_archive(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Query official CCTV broadcast video archive (tv.cctv.com / news.cctv.com) for authentic Chinese case/police/court footage."""
        clean_q = re.sub(r"\s+", " ", str(query or "").strip())
        if not clean_q:
            return []
        api_url = (
            "https://search.cctv.com/ifsearch.php?page=1"
            f"&qtext={urllib.parse.quote(clean_q)}&sort=relevance&pageSize={max(5, max_results * 2)}&type=video"
        )
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            return []
        items = payload.get("list") if isinstance(payload, dict) else []
        if not isinstance(items, list):
            return []
        out: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for row in items:
            if not isinstance(row, dict):
                continue
            raw_link = str(row.get("urllink") or row.get("url") or "").strip()
            if not raw_link or raw_link in seen_urls:
                continue
            if not (".cctv.com/" in raw_link or ".cntv.cn/" in raw_link):
                continue
            title = re.sub(r"<[^>]+>", "", str(row.get("all_title") or row.get("title") or "")).strip()
            if self._NOISE_TITLE_RE.search(title):
                continue
            dur_str = str(row.get("duration") or row.get("playtime") or "").strip()
            dur_sec = 90.0
            if ":" in dur_str:
                parts = [p for p in dur_str.split(":") if p.strip().isdigit()]
                if len(parts) == 2:
                    dur_sec = float(int(parts[0]) * 60 + int(parts[1]))
                elif len(parts) == 3:
                    dur_sec = float(int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]))
            if dur_sec < 12 or dur_sec > 14400:
                continue
            seen_urls.add(raw_link)
            out.append({
                "id": str(row.get("id") or Path(urllib.parse.urlparse(raw_link).path).stem or len(out)),
                "url": raw_link,
                "title": title,
                "duration": dur_sec,
                "provider": "cctv_archive",
            })
            if len(out) >= max_results:
                break
        return out

    def _run_ytdlp_search_spec(self, search_spec: str, max_results: int) -> list[dict[str, Any]]:
        if not self.ytdlp:
            return []
        cmd = [
            self.ytdlp,
            "--dump-json",
            "--flat-playlist",
            "--no-warnings",
            "--socket-timeout", "12",
            search_spec,
        ]
        try:
            res = subprocess.run(cmd, timeout=25, check=False, **_subproc_kwargs())
        except Exception:
            return []
        candidates: list[dict[str, Any]] = []
        for line in (res.stdout or "").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            vid_id = str(item.get("id") or "").strip()
            url = str(item.get("url") or item.get("webpage_url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "")).strip()
            title = str(item.get("title") or "").strip()
            duration = float(item.get("duration") or 0)
            if not url or (duration and (duration < 10 or duration > 14400)):
                continue
            if self._NOISE_TITLE_RE.search(title):
                continue
            candidates.append({
                "id": vid_id,
                "url": url,
                "title": title,
                "duration": duration or 60.0,
            })
            if len(candidates) >= max_results:
                break
        return candidates

    def search_candidates(self, query: str, max_results: int = 5, *, prefer_case_footage: bool = True) -> list[dict[str, Any]]:
        clean_q = re.sub(r"\s+", " ", str(query or "").strip())
        if not clean_q:
            return []
        candidates: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        # 1. For Chinese / CJK case queries, check official CCTV video archive first
        if prefer_case_footage and self._CJK_RE.search(clean_q):
            for item in self._search_cctv_video_archive(clean_q, max_results=max_results):
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    candidates.append(item)

        # 2. Query YouTube WITHOUT appending 5 '-' operators that break CJK query parsing; filter noise titles in Python
        if self.ytdlp and len(candidates) < max_results:
            yt_q = clean_q if prefer_case_footage else (clean_q if "4k" in clean_q.lower() else f"{clean_q} 4k")
            fetch_n = max(max_results * 2, 8)
            for item in self._run_ytdlp_search_spec(f"ytsearch{fetch_n}:{yt_q}", max_results=max_results):
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    candidates.append(item)
                    if len(candidates) >= max_results:
                        break

        # 3. Bilibili archival fallback when CJK case queries still need candidates
        if self.ytdlp and prefer_case_footage and self._CJK_RE.search(clean_q) and len(candidates) < max(2, max_results // 2):
            for item in self._run_ytdlp_search_spec(f"bilisearch{max_results}:{clean_q}", max_results=max_results):
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    candidates.append(item)
                    if len(candidates) >= max_results:
                        break

        return candidates[:max_results]

    CROP_FILTERS: dict[str, str] = {
        "none": "scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080",
        "bottom_14": "crop=iw:ih*0.86:0:0,scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080",
        "bottom_18": "crop=iw:ih*0.82:0:0,scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080",
        "top_10_bottom_16": "crop=iw:ih*0.74:0:ih*0.10,scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080",
        "cctv_clean": "crop=iw*0.76:ih*0.66:iw*0.12:ih*0.15,scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080",
        "forensic_v2_clean": "crop=iw*0.74:ih*0.64:iw*0.13:ih*0.16,scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080",
        "eye_calibrated_deep": "crop=iw*0.72:ih*0.62:iw*0.14:ih*0.17,scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080",
    }

    @staticmethod
    def _dhash_pil(im: Image.Image) -> int:
        g = im.convert("L").resize((9, 8), Image.Resampling.BILINEAR)
        px = list(g.getdata())
        bits = 0
        for r in range(8):
            row_off = r * 9
            for c in range(8):
                bits = (bits << 1) | (1 if px[row_off + c] > px[row_off + c + 1] else 0)
        return bits

    @staticmethod
    def hamming_distance_64(a: int, b: int) -> int:
        return int((a ^ b).bit_count())

    def compute_clip_dhash(self, video_path: Path) -> int | None:
        """Compute 64-bit perceptual dHash at the 50% midpoint of a sliced clip to enforce dHash >= 14 uniqueness."""
        sheet_jpg = video_path.parent / f"{video_path.stem}_3frames.jpg"
        if not sheet_jpg.exists():
            self.extract_3frame_contact_sheet(video_path, sheet_jpg)
        if not sheet_jpg.exists():
            return None
        try:
            im = Image.open(sheet_jpg).convert("RGB")
            # Middle panel of 3-frame strip (x=648..1288, y=32..392)
            mid_crop = im.crop((648, 32, 1288, 392))
            return self._dhash_pil(mid_crop)
        except Exception:
            return None

    def extract_calibration_grid_100px(self, video_path: Path, out_jpg: Path | None = None) -> Path | None:
        """Render a 2x2 full-frame (1920x1080) contact sheet overlaid with a 100px X/Y coordinate ruler grid
        so the AI Agent inspects exact logo/watermark/subtitle pixel coordinates with its own eyes (`read_file` / `vision_inspect_frames`)."""
        if not self.ffmpeg or not self.ffprobe or not video_path.exists():
            return None
        try:
            pr = subprocess.run(
                [self.ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video_path)],
                timeout=8,
                check=False,
                **_subproc_kwargs(),
            )
            dur = max(2.0, float((pr.stdout or "30").strip() or 30.0))
        except Exception:
            dur = 30.0

        grid_path = out_jpg or (video_path.parent / f"GRID_{video_path.stem}.jpg")
        fw, fh = 960, 540  # Half-scale display of 1920x1080 with 1920x1080 coordinate labels every 100px
        canvas = Image.new("RGB", (fw * 2 + 16, fh * 2 + 64), (12, 15, 20))
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (12, 8),
            f"100px COORDINATE CALIBRATION GRID (1920x1080 SPACE) · {video_path.name} · Inspect with read_file & set --crop-mode crop=W:H:X:Y",
            fill=(250, 204, 21),
        )
        for idx, pct in enumerate((0.20, 0.42, 0.64, 0.82)):
            ts = max(0.5, min(dur - 0.5, dur * pct))
            tmp_jpg = video_path.parent / f".grid_tmp_{video_path.stem}_{idx}.jpg"
            subprocess.run(
                [
                    self.ffmpeg, "-v", "error", "-y", "-threads", _edit_ffmpeg_threads(),
                    "-ss", f"{ts:.2f}", "-i", str(video_path),
                    "-frames:v", "1", "-vf", "scale=1920:1080", str(tmp_jpg),
                ],
                timeout=15,
                check=False,
                **_subproc_kwargs(),
            )
            col = idx % 2
            row = idx // 2
            ox = 6 + col * (fw + 4)
            oy = 34 + row * (fh + 24)
            if tmp_jpg.exists():
                im_full = Image.open(tmp_jpg).convert("RGB")
                im_half = im_full.resize((fw, fh), Image.Resampling.BILINEAR)
                gdraw = ImageDraw.Draw(im_half)
                for x1080 in range(100, 1920, 100):
                    xh = int(x1080 * 0.5)
                    color = (239, 68, 68) if x1080 in (200, 300, 1600, 1700) else (56, 189, 248)
                    gdraw.line([(xh, 0), (xh, fh)], fill=color, width=1)
                    if x1080 % 200 == 0:
                        gdraw.text((xh + 2, 2), f"X{x1080}", fill=(254, 240, 138))
                for y1080 in range(100, 1080, 100):
                    yh = int(y1080 * 0.5)
                    color = (239, 68, 68) if y1080 in (150, 200, 800, 900) else (56, 189, 248)
                    gdraw.line([(0, yh), (fw, yh)], fill=color, width=1)
                    gdraw.text((4, yh + 2), f"Y{y1080}", fill=(254, 240, 138))
                canvas.paste(im_half, (ox, oy + 18))
                tmp_jpg.unlink(missing_ok=True)
            draw.text((ox + 6, oy), f"Sample {int(pct*100)}% ({ts:.1f}s)", fill=(167, 243, 208))
        canvas.save(grid_path, quality=90)
        return grid_path

    def find_transcript_offset(
        self,
        url: str,
        reference_text: str,
        *,
        target_duration_sec: float = 6.0,
    ) -> float | None:
        """Read YouTube WebVTT subtitles when available to pinpoint the exact event timestamp instead of blind 28%."""
        if not self.ytdlp or not str(reference_text or "").strip():
            return None
        sub_dir = self.media_dir / f".subs_{os.getpid()}"
        sub_dir.mkdir(parents=True, exist_ok=True)
        try:
            cmd = [
                self.ytdlp,
                "--skip-download",
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs", "zh.*,en.*,vi.*,ko.*",
                "--sub-format", "vtt",
                "--no-warnings",
                "--socket-timeout", "10",
                "-o", str(sub_dir / "cand.%(ext)s"),
                url,
            ]
            subprocess.run(cmd, timeout=18, check=False, **_subproc_kwargs())
            vtts = list(sub_dir.glob("*.vtt"))
            if not vtts:
                return None
            cues = parse_webvtt(vtts[0].read_text(encoding="utf-8", errors="ignore"))
            if not cues:
                return None
            best = best_transcript_window(cues, voice_text=reference_text, target_duration_sec=target_duration_sec)
            if float(best.get("score") or 0.0) >= 0.08:
                return float(best.get("start_sec") or 0.0)
            return None
        except Exception:
            return None
        finally:
            shutil.rmtree(sub_dir, ignore_errors=True)

    def _find_clean_subshot_start(self, raw_video: Path, target_dur: float) -> tuple[float, float]:
        """Detect internal scene cuts via ffmpeg scenedetect and pick the longest clean continuous subshot."""
        if not self.ffmpeg or not self.ffprobe or not raw_video.exists():
            return 0.0, target_dur
        try:
            pr = subprocess.run(
                [self.ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(raw_video)],
                timeout=10,
                check=False,
                **_subproc_kwargs(),
            )
            total_dur = float((pr.stdout or "0").strip() or 0.0)
        except Exception:
            total_dur = 0.0
        if total_dur <= 0.5:
            return 0.0, target_dur

        cmd = [
            self.ffmpeg, "-hide_banner",
            "-threads", _edit_ffmpeg_threads(),
            "-i", str(raw_video),
            "-vf", "select='gt(scene,0.30)',showinfo",
            "-an", "-f", "null", "-",
        ]
        res = subprocess.run(cmd, timeout=20, check=False, **_subproc_kwargs())
        cuts = [0.0]
        for m in re.finditer(r"pts_time:([0-9]+(?:\.[0-9]+)?)", res.stderr or ""):
            t = float(m.group(1))
            if 0.15 < t < total_dur - 0.15:
                cuts.append(t)
        cuts.append(total_dur)
        cuts = sorted(set(cuts))

        spans = [(cuts[i], cuts[i + 1], cuts[i + 1] - cuts[i]) for i in range(len(cuts) - 1)]
        best_span = max(spans, key=lambda x: x[2])
        s0, s1, sdur = best_span
        # Trim 0.12s away from detected scene transitions so no transition flash leaks in
        clean_start = s0 + (0.12 if s0 > 0 else 0.0)
        usable = max(1.5, min(target_dur, max(1.5, s1 - clean_start - 0.10)))
        return round(clean_start, 2), round(usable, 2)

    def extract_3frame_contact_sheet(self, video_path: Path, out_jpg: Path | None = None) -> Path | None:
        """Extract 15% - 50% - 85% inspection strip so the Step-6 AI Agent inspects every clip with Vision eyes."""
        if not self.ffmpeg or not self.ffprobe or not video_path.exists():
            return None
        try:
            pr = subprocess.run(
                [self.ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video_path)],
                timeout=8,
                check=False,
                **_subproc_kwargs(),
            )
            dur = max(1.0, float((pr.stdout or "5").strip() or 5.0))
        except Exception:
            dur = 5.0

        sheet_path = out_jpg or (video_path.parent / f"{video_path.stem}_3frames.jpg")
        w, h = 640, 360
        canvas = Image.new("RGB", (w * 3 + 16, h + 38), (15, 18, 24))
        draw = ImageDraw.Draw(canvas)
        for idx, pct in enumerate((0.15, 0.50, 0.85)):
            ts = max(0.05, min(dur - 0.08, dur * pct))
            tmp_jpg = video_path.parent / f".tmp_{video_path.stem}_{idx}.jpg"
            subprocess.run(
                [self.ffmpeg, "-v", "error", "-y", "-threads", _edit_ffmpeg_threads(), "-ss", f"{ts:.2f}", "-i", str(video_path), "-frames:v", "1", "-vf", f"scale={w}:{h}", str(tmp_jpg)],
                timeout=12,
                check=False,
                **_subproc_kwargs(),
            )
            x0 = 4 + idx * (w + 4)
            if tmp_jpg.exists():
                im = Image.open(tmp_jpg).convert("RGB")
                canvas.paste(im, (x0, 32))
                tmp_jpg.unlink(missing_ok=True)
            draw.text((x0 + 8, 8), f"{int(pct*100)}% ({ts:.2f}s) · {video_path.name}", fill=(250, 204, 21))
        canvas.save(sheet_path, quality=88)
        return sheet_path

    def download_and_slice_clip(
        self,
        url: str,
        output_stem: str,
        *,
        duration_hint: float = 60.0,
        clip_duration_sec: float = 6.2,
        start_offset_sec: float | None = None,
        crop_mode: str = "none",
        reference_text: str = "",
        force_redownload: bool = False,
    ) -> Path | None:
        if not self.ffmpeg:
            return None
        # STRICT BAN ON BLIND AUTOMATIC CUTTING & UNCALIBRATED CROPS:
        # Every footage cut MUST provide an explicit eye-verified `start_offset_sec >= 0`
        # from `STORYBOARD_<id>.jpg` and an explicit calibrated `crop_mode` (never 'none') from `GRID_<id>.jpg`.
        if start_offset_sec is None or float(start_offset_sec) < 0:
            return None
        clean_crop_mode = str(crop_mode or "").strip()
        if not clean_crop_mode or clean_crop_mode.lower() == "none":
            return None

        target = self.media_dir / f"{output_stem}.mp4"
        if not force_redownload and target.exists() and target.stat().st_size > 8192:
            return target

        strict_slice_sec = max(2.5, min(9.0, float(clip_duration_sec or 6.2)))
        download_window_sec = strict_slice_sec
        raw_tmp = self.media_dir / f".raw_{output_stem}.mp4"

        # Use the EXACT timestamp selected by the AI Agent's eyes on `STORYBOARD_<id>.jpg`
        # without any automatic offset clamping or subshot shifting that would desync image from voice.
        start_sec = round(float(start_offset_sec), 2)
        end_sec = round(start_sec + download_window_sec, 2)
        section_arg = f"*{start_sec:.2f}-{end_sec:.2f}"

        # Support local source video files in workspace (e.g., media/footage/sources/*.mp4)
        local_src = Path(url)
        if not local_src.is_file():
            cand_rel = (self.workspace / url).resolve()
            if cand_rel.is_file():
                local_src = cand_rel
            else:
                cand_sources = (self.workspace / "media" / "footage" / "sources" / Path(url).name).resolve()
                if cand_sources.is_file():
                    local_src = cand_sources

        if local_src.is_file():
            slice_cmd = [
                self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{start_sec:.2f}",
                "-i", str(local_src),
                "-t", f"{download_window_sec:.2f}",
                "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                str(raw_tmp),
            ]
            try:
                subprocess.run(slice_cmd, timeout=35, check=False, **_subproc_kwargs())
            except Exception:
                raw_tmp.unlink(missing_ok=True)
                return None
            if not raw_tmp.exists() or raw_tmp.stat().st_size < 4096:
                raw_tmp.unlink(missing_ok=True)
                return None
        else:
            if not self.ytdlp:
                return None
            dl_cmd = [
                self.ytdlp,
                "--no-playlist",
                "--no-warnings",
                "--socket-timeout", "15",
                "-f", _ytdlp_format_selector(include_audio=False),
                "--download-sections", section_arg,
                "-o", str(raw_tmp),
                url,
            ]
            try:
                subprocess.run(dl_cmd, timeout=65, check=False, **_subproc_kwargs())
            except Exception:
                raw_tmp.unlink(missing_ok=True)
                return None

            if not raw_tmp.exists() or raw_tmp.stat().st_size < 4096:
                raw_tmp.unlink(missing_ok=True)
                # Fallback for HLS broadcast archives (e.g. tv.cctv.com) where --download-sections can fail on HLS segment boundaries
                if duration_hint <= 1200.0 or ".cctv.com/" in url or ".cntv.cn/" in url:
                    full_tmp = self.media_dir / f".full_{output_stem}.mp4"
                    fb_cmd = [
                        self.ytdlp,
                        "--no-playlist",
                        "--no-warnings",
                        "--socket-timeout", "18",
                        "-f", _ytdlp_format_selector(include_audio=True),
                        "--merge-output-format", "mp4",
                        "-o", str(full_tmp),
                        url,
                    ]
                    try:
                        subprocess.run(fb_cmd, timeout=90, check=False, **_subproc_kwargs())
                        if full_tmp.exists() and full_tmp.stat().st_size >= 8192:
                            slice_cmd = [
                                self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                                "-ss", f"{start_sec:.2f}",
                                "-i", str(full_tmp),
                                "-t", f"{download_window_sec:.2f}",
                                "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                                str(raw_tmp),
                            ]
                            subprocess.run(slice_cmd, timeout=35, check=False, **_subproc_kwargs())
                    except Exception:
                        pass
                    finally:
                        full_tmp.unlink(missing_ok=True)
                if not raw_tmp.exists() or raw_tmp.stat().st_size < 4096:
                    raw_tmp.unlink(missing_ok=True)
                    return None

        eff_crop_mode = clean_crop_mode
        grid_jpg = self.media_dir / f"GRID_{output_stem}.jpg"
        if not grid_jpg.exists():
            self.extract_calibration_grid_100px(raw_tmp, grid_jpg)
        sub_start = 0.0
        sub_dur = strict_slice_sec
        if eff_crop_mode in self.CROP_FILTERS:
            vf_crop = self.CROP_FILTERS[eff_crop_mode]
        elif "crop=" in str(eff_crop_mode):
            vf_crop = (
                eff_crop_mode
                if "scale=1920:1080" in str(eff_crop_mode)
                else f"{eff_crop_mode},scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080"
            )
        else:
            raw_tmp.unlink(missing_ok=True)
            return None
        norm_tmp = self.media_dir / f".norm_{output_stem}.mp4"
        ff_cmd = [
            self.ffmpeg,
            "-hide_banner", "-loglevel", "error", "-y",
            "-threads", _edit_ffmpeg_threads(),
            "-ss", f"{sub_start:.2f}",
            "-i", str(raw_tmp),
            "-t", f"{sub_dur:.2f}",
            "-an",
            "-vf", f"{vf_crop},fps=30,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            "-threads", _edit_ffmpeg_threads(),
            "-movflags", "+faststart",
            str(norm_tmp),
        ]
        try:
            res = subprocess.run(ff_cmd, timeout=45, check=False, **_subproc_kwargs())
            raw_tmp.unlink(missing_ok=True)
            if res.returncode != 0 or not norm_tmp.exists() or norm_tmp.stat().st_size < 8192:
                norm_tmp.unlink(missing_ok=True)
                return None
            norm_tmp.replace(target)
            try:
                from .critic_loops import _inspect_media_file_frames

                frame_check = _inspect_media_file_frames(target, is_video=True)
                if frame_check.get("internal_hard_cut_detected") or frame_check.get("edge_banner_detected"):
                    target.unlink(missing_ok=True)
                    (target.parent / f"{target.stem}_3frames.jpg").unlink(missing_ok=True)
                    return None
            except Exception:
                pass
            self.extract_3frame_contact_sheet(target)
            # Enforce perceptual dHash >= 14 uniqueness against already-sliced clips (locked across parallel workers)
            with _workspace_registry_lock(self.workspace):
                cand_hash = self.compute_clip_dhash(target)
                if cand_hash is not None:
                    for other_mp4 in self.media_dir.glob("edit_broll_*.mp4"):
                        if other_mp4.resolve() == target.resolve():
                            continue
                        oh = self.compute_clip_dhash(other_mp4)
                        if oh is not None and self.hamming_distance_64(cand_hash, oh) < 14:
                            target.unlink(missing_ok=True)
                            (target.parent / f"{target.stem}_3frames.jpg").unlink(missing_ok=True)
                            return None
            return target
        except Exception:
            raw_tmp.unlink(missing_ok=True)
            norm_tmp.unlink(missing_ok=True)
            return None

    def probe_video_storyboard(
        self,
        url_or_path: str,
        probe_id: str,
        *,
        sample_count: int = 12,
    ) -> dict[str, Any]:
        """Extract a timestamped storyboard contact sheet + 100px coordinate calibration grid
        so Agent @footage can inspect the source video with `read_file` before cutting."""
        probes_dir = self.media_dir / "probes"
        probes_dir.mkdir(parents=True, exist_ok=True)
        src_path = Path(url_or_path)
        if not src_path.is_file():
            src_path = self.media_dir / f".probe_raw_{probe_id}.mp4"
            if not src_path.is_file() and self.ytdlp:
                dl_cmd = [
                    self.ytdlp,
                    "--no-playlist",
                    "--no-warnings",
                    "--socket-timeout", "18",
                    "-f", _ytdlp_format_selector(include_audio=False),
                    "-o", str(src_path),
                    url_or_path,
                ]
                subprocess.run(dl_cmd, timeout=90, check=False, **_subproc_kwargs())
        if not src_path.is_file():
            return {"ok": False, "probe_id": probe_id, "error": "Unable to load source video for storyboard probe"}

        grid_jpg = probes_dir / f"GRID_{probe_id}.jpg"
        self.extract_calibration_grid_100px(src_path, grid_jpg)
        storyboard_jpg = probes_dir / f"STORYBOARD_{probe_id}.jpg"
        if self.ffmpeg:
            vf = f"fps=1/12,scale=480:270:force_original_aspect_ratio=decrease,pad=480:270:(ow-iw)/2:(oh-ih)/2,tile=4x{max(2, (sample_count + 3) // 4)}"
            sb_cmd = [
                self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(src_path),
                "-frames:v", "1",
                "-vf", vf,
                "-q:v", "3",
                str(storyboard_jpg),
            ]
            subprocess.run(sb_cmd, timeout=35, check=False, **_subproc_kwargs())
        return {
            "ok": True,
            "probe_id": probe_id,
            "source_video": str(src_path),
            "grid_100px_jpg": str(grid_jpg.relative_to(self.workspace)) if grid_jpg.is_file() else "",
            "storyboard_jpg": str(storyboard_jpg.relative_to(self.workspace)) if storyboard_jpg.is_file() else "",
        }

    def fetch_for_beats(
        self,
        job_id: str,
        beat_ids: list[str],
        query: str,
        *,
        direct_url: str | None = None,
        start_offset_sec: float | None = None,
        clip_duration_sec: float = 6.2,
        crop_mode: str = "none",
        reference_text: str = "",
        observed_content: str = "",
        force_redownload: bool = False,
        used_urls: set[str] | None = None,
        url_slice_counts: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        used = used_urls if used_urls is not None else set()
        slice_counts = url_slice_counts if url_slice_counts is not None else {}
        clean_obs = str(observed_content or "").strip()
        clean_crop = str(crop_mode or "").strip()
        if (
            start_offset_sec is None
            or float(start_offset_sec) < 0
            or not clean_crop
            or clean_crop.lower() == "none"
            or len(clean_obs) < 10
        ):
            return {
                "ok": False,
                "beat_ids": beat_ids,
                "query": query,
                "error": (
                    "FORBIDDEN_AUTO_CUT: Every footage cut requires an eye-verified --start-offset >= 0 "
                    "from STORYBOARD_<id>.jpg, an eye-calibrated --crop-mode (never 'none') from GRID_<id>.jpg "
                    "that strips 100% of third-party logos and running text, and --observed-content (>= 10 chars) "
                    "confirming 100% match with the spoken sentence. Automatic blind cutting is strictly banned."
                ),
            }

        stem = f"edit_broll_{beat_ids[0]}"
        existing_target = self.media_dir / f"{stem}.mp4"
        clip_path: Path | None = (
            existing_target
            if (not force_redownload and existing_target.exists() and existing_target.stat().st_size > 8192)
            else None
        )
        chosen_url = f"cached://{stem}" if clip_path is not None else ""
        chosen_title = query or stem if clip_path is not None else ""

        resolved_crop_mode = clean_crop
        if clip_path is None and direct_url:
            s_idx = slice_counts.get(direct_url, 0)
            clip_path = self.download_and_slice_clip(
                direct_url,
                stem,
                clip_duration_sec=clip_duration_sec,
                start_offset_sec=float(start_offset_sec),
                crop_mode=resolved_crop_mode,
                reference_text=reference_text or query,
                force_redownload=force_redownload,
            )
            if clip_path:
                chosen_url = direct_url
                chosen_title = query or direct_url
                slice_counts[direct_url] = s_idx + 1
        if clip_path is None and not direct_url:
            candidates = self.search_candidates(query, max_results=8, prefer_case_footage=True)
            for cand in candidates:
                url = cand["url"]
                dur = float(cand.get("duration") or 60.0)
                s_idx = slice_counts.get(url, 0)
                if url in used:
                    continue
                clip_path = self.download_and_slice_clip(
                    url,
                    stem,
                    duration_hint=dur,
                    clip_duration_sec=clip_duration_sec,
                    start_offset_sec=float(start_offset_sec),
                    crop_mode=resolved_crop_mode,
                    reference_text=reference_text or query,
                    force_redownload=force_redownload,
                )
                if clip_path is not None:
                    chosen_url = url
                    chosen_title = str(cand.get("title") or query)
                    used.add(url)
                    slice_counts[url] = s_idx + 1
                    break

        if clip_path is None:
            return {"ok": False, "beat_ids": beat_ids, "query": query, "error": "No usable B-roll clip downloaded"}

        sig_stats = measure_clip_signalstats(clip_path)
        sheet_path = clip_path.parent / f"{clip_path.stem}_3frames.jpg"
        if not sheet_path.exists():
            self.extract_3frame_contact_sheet(clip_path, sheet_path)
        rel_path = str(clip_path.relative_to(self.workspace))
        rel_sheet = str(sheet_path.relative_to(self.workspace)) if sheet_path.exists() else ""

        self._commit_sliced_clips_to_registries(
            job_id,
            [
                {
                    "beat_id": bid,
                    "clip_path": clip_path,
                    "rel_sheet": rel_sheet,
                    "crop_mode": resolved_crop_mode,
                    "observed_content": clean_obs,
                    "start_offset_sec": round(float(start_offset_sec), 2),
                    "duration_sec": round(float(clip_duration_sec), 2),
                    "signalstats": sig_stats,
                    "query": query,
                    "chosen_url": chosen_url,
                    "chosen_title": chosen_title,
                }
                for bid in beat_ids
            ],
        )
        return {
            "ok": True,
            "beat_ids": beat_ids,
            "query": query,
            "url": chosen_url,
            "title": chosen_title,
            "path": rel_path,
            "contact_sheet_3frame": rel_sheet,
            "crop_mode": resolved_crop_mode,
            "signalstats": sig_stats,
        }

    def _commit_sliced_clips_to_registries(
        self,
        job_id: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Atomically persist eye-verified clip metadata across asset_registry.json and footage_review.json."""
        if not records:
            return []
        target_bids = {str(rec.get("beat_id") or "").strip() for rec in records if str(rec.get("beat_id") or "").strip()}
        if not target_bids:
            return []

        clips_dir = self.workspace / "media" / "footage" / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        pub_ftg_dir = self.remotion_dir / "public" / "jobs" / str(job_id) / "footage"
        pub_ftg_dir.mkdir(parents=True, exist_ok=True)

        committed_entries: list[dict[str, Any]] = []
        with _workspace_registry_lock(self.workspace):
            registry_path = self.workspace / "asset_registry.json"
            registry = self._read_json(registry_path, {"assets": [], "ai_fallback_beats": [], "ai_usage_notes": []})
            assets = [
                item for item in (registry.get("assets") or [])
                if isinstance(item, dict) and str(item.get("beat_id") or "") not in target_bids
            ]

            ftg_review_path = self.workspace / "footage_review.json"
            ftg_review = self._read_json(ftg_review_path, {"selected_candidates": []})
            sel_list = [
                item for item in (ftg_review.get("selected_candidates") or [])
                if isinstance(item, dict)
            ]
            existing_sf_by_beat = {
                str(item.get("beat_id") or ""): str(item.get("path") or "")
                for item in sel_list
                if str(item.get("beat_id") or "")
            }
            sel_list = [
                item for item in sel_list
                if str(item.get("beat_id") or "") not in target_bids
            ]

            for rec in records:
                bid = str(rec.get("beat_id") or "").strip()
                clip_path = Path(rec["clip_path"])
                if not bid or not clip_path.is_file():
                    continue
                rel_sheet = str(rec.get("rel_sheet") or "")
                resolved_crop_mode = str(rec.get("crop_mode") or "")
                clean_obs = str(rec.get("observed_content") or "")
                start_offset_sec = round(float(rec.get("start_offset_sec") or 0.0), 2)
                clip_duration_sec = round(float(rec.get("duration_sec") or 6.2), 2)
                sig_stats = rec.get("signalstats") or {}
                query = str(rec.get("query") or "")
                chosen_url = str(rec.get("chosen_url") or "")
                chosen_title = str(rec.get("chosen_title") or "")

                beat_file = self.media_dir / f"{bid}_edit_broll.mp4"
                if beat_file.resolve() != clip_path.resolve():
                    shutil.copy2(clip_path, beat_file)
                assets.append({
                    "id": f"edit_broll_{bid}",
                    "beat_id": bid,
                    "kind": "sourced_video",
                    "path": str(beat_file.relative_to(self.workspace)),
                    "contact_sheet_3frame": rel_sheet,
                    "crop_mode": resolved_crop_mode,
                    "eye_verified": True,
                    "observed_content": clean_obs,
                    "selection_method": "eye_verified_cut",
                    "start_offset_sec": start_offset_sec,
                    "signalstats": sig_stats,
                    "source": {
                        "fetched_by": "edit_direct_footage_agent",
                        "query": query,
                        "url": chosen_url,
                        "title": chosen_title,
                        "fetched_at": _now(),
                    },
                })

                prev_rel = existing_sf_by_beat.get(bid) or ""
                sf_name = Path(prev_rel).name if prev_rel.endswith(".mp4") else f"{bid}_edit_broll.mp4"
                sf_clip_path = clips_dir / sf_name
                if sf_clip_path.resolve() != clip_path.resolve():
                    shutil.copy2(clip_path, sf_clip_path)
                shutil.copy2(clip_path, pub_ftg_dir / sf_name)
                shutil.copy2(clip_path, pub_ftg_dir / f"{bid}_edit_broll.mp4")
                sel_entry = {
                    "beat_id": bid,
                    "candidate_id": Path(sf_name).stem,
                    "path": str(sf_clip_path.relative_to(self.workspace)),
                    "source_file": Path(chosen_url).name if chosen_url else query,
                    "source_url": chosen_url,
                    "start_offset_sec": start_offset_sec,
                    "duration_sec": clip_duration_sec,
                    "crop_mode": resolved_crop_mode,
                    "eye_verified": True,
                    "selection_method": "eye_verified_cut",
                    "observed_content": clean_obs,
                    "contact_sheet_3frame": rel_sheet,
                    "signalstats": sig_stats,
                }
                sel_list.append(sel_entry)
                committed_entries.append(sel_entry)

            registry["assets"] = assets
            self._write_json(registry_path, registry)
            ftg_review["selected_candidates"] = sel_list
            ftg_review["selection_method"] = "eye_verified_cut"
            ftg_review["updated_at"] = _now()
            self._write_json(ftg_review_path, ftg_review)
        return committed_entries

    def _voice_text_by_beat(self) -> dict[str, str]:
        vm = self._read_json(self.workspace / "visual_manifest.json", {})
        beats = [b for b in (vm.get("beats") or []) if isinstance(b, dict)]
        return {str(b.get("id") or b.get("beat_id") or ""): str(b.get("voice_text") or b.get("narration_text") or "") for b in beats}

    def _render_contact_sheet_page(
        self,
        batch: list[dict[str, Any]],
        out_sheet: Path,
        voice_by_beat: dict[str, str],
    ) -> Path:
        """Render a readable multi-clip 3-frame contact sheet with voice_text & observed_content."""
        from PIL import Image, ImageDraw, ImageFont

        try:
            font = ImageFont.truetype("malgun.ttf", 14)
        except Exception:
            font = ImageFont.load_default()

        row_h = 92
        img_w = 1280
        img_h = max(row_h * max(1, len(batch)), 180)
        canvas = Image.new("RGB", (img_w, img_h), (15, 18, 24))
        draw = ImageDraw.Draw(canvas)
        for r_i, entry in enumerate(batch):
            y0 = r_i * row_h
            bid = str(entry.get("beat_id") or "")
            rel_p = str(entry.get("path") or "")
            mp4_p = self.workspace / rel_p if rel_p else self.media_dir / f"{bid}_edit_broll.mp4"
            sheet_3 = mp4_p.parent / f"{mp4_p.stem}_3frames.jpg"
            if not sheet_3.is_file():
                alt_3 = self.media_dir / f"edit_broll_{bid}_3frames.jpg"
                if alt_3.is_file():
                    sheet_3 = alt_3
            if mp4_p.is_file() and not sheet_3.is_file():
                self.extract_3frame_contact_sheet(mp4_p, sheet_3)
            if sheet_3.is_file():
                try:
                    with Image.open(sheet_3) as s3:
                        s3_resized = s3.convert("RGB").resize((480, 86))
                        canvas.paste(s3_resized, (6, y0 + 3))
                except Exception:
                    pass
            src_name = str(entry.get("source_file") or (entry.get("source") or {}).get("url") or "")
            start_off = entry.get("start_offset_sec", 0.0)
            v_txt = voice_by_beat.get(bid, "")[:68]
            obs_txt = str(entry.get("observed_content") or "")[:68]
            draw.text((496, y0 + 8), f"{bid} | src={Path(src_name).name} @ {start_off}s", fill=(125, 211, 252), font=font)
            draw.text((496, y0 + 34), f"Voice: {v_txt}", fill=(241, 245, 249), font=font)
            draw.text((496, y0 + 58), f"Eye: {obs_txt}", fill=(167, 243, 208), font=font)
        out_sheet.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_sheet, quality=88)
        return out_sheet

    def fetch_batch_manifest(
        self,
        job_id: str,
        manifest_items: list[dict[str, Any]],
        *,
        sheet_out: Path | None = None,
        max_workers: int = 4,
    ) -> dict[str, Any]:
        """Slice a batch of 10-15 eye-verified beats in parallel and emit a single Contact Sheet."""
        valid_items: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for idx, raw in enumerate(manifest_items):
            if not isinstance(raw, dict):
                continue
            bid = str(raw.get("beat_id") or "").strip()
            url = str(raw.get("url") or raw.get("source") or "").strip()
            query = str(raw.get("query") or bid).strip()
            crop_mode = str(raw.get("crop_mode") or "").strip()
            obs = str(raw.get("observed_content") or "").strip()
            try:
                start_offset = float(raw.get("start_offset", -1.0))
            except (TypeError, ValueError):
                start_offset = -1.0
            try:
                duration = float(raw.get("duration") or 6.2)
            except (TypeError, ValueError):
                duration = 6.2
            if not bid or not url or start_offset < 0 or not crop_mode or crop_mode.lower() == "none" or len(obs) < 10:
                rejected.append({
                    "index": idx,
                    "beat_id": bid,
                    "error": "FORBIDDEN_AUTO_CUT: requires beat_id, url, start_offset>=0, calibrated crop_mode, observed_content>=10 chars",
                })
                continue
            valid_items.append({
                "beat_id": bid,
                "url": url,
                "query": query,
                "crop_mode": crop_mode,
                "observed_content": obs,
                "start_offset": start_offset,
                "duration": duration,
                "force": bool(raw.get("force", True)),
            })

        def _slice_one(item: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
            bid = item["beat_id"]
            stem = f"edit_broll_{bid}"
            clip_path = self.download_and_slice_clip(
                item["url"],
                stem,
                clip_duration_sec=item["duration"],
                start_offset_sec=item["start_offset"],
                crop_mode=item["crop_mode"],
                reference_text=item["query"],
                force_redownload=item["force"],
            )
            if clip_path is None:
                return None, {"beat_id": bid, "error": "Failed to slice or rejected by dHash/hard-cut/banner filter"}
            sig_stats = measure_clip_signalstats(clip_path)
            sheet_path = clip_path.parent / f"{clip_path.stem}_3frames.jpg"
            if not sheet_path.exists():
                self.extract_3frame_contact_sheet(clip_path, sheet_path)
            rel_sheet = str(sheet_path.relative_to(self.workspace)) if sheet_path.exists() else ""
            return {
                "beat_id": bid,
                "clip_path": clip_path,
                "rel_sheet": rel_sheet,
                "crop_mode": item["crop_mode"],
                "observed_content": item["observed_content"],
                "start_offset_sec": round(item["start_offset"], 2),
                "duration_sec": round(item["duration"], 2),
                "signalstats": sig_stats,
                "query": item["query"],
                "chosen_url": item["url"],
                "chosen_title": item["query"],
            }, None

        records: list[dict[str, Any]] = []
        if valid_items:
            workers = max(1, min(max_workers, len(valid_items)))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_slice_one, it) for it in valid_items]
                for fut in as_completed(futures):
                    rec, err = fut.result()
                    if rec is not None:
                        records.append(rec)
                    elif err is not None:
                        rejected.append(err)

        records.sort(key=lambda r: str(r.get("beat_id") or ""))
        committed = self._commit_sliced_clips_to_registries(job_id, records)
        batch_sheet_rel = ""
        if committed:
            probes_dir = self.workspace / "media" / "footage" / "probes"
            out_path = Path(sheet_out) if sheet_out else probes_dir / f"BATCH_VERIFY_{records[0]['beat_id']}_{records[-1]['beat_id']}.jpg"
            self._render_contact_sheet_page(committed, out_path, self._voice_text_by_beat())
            batch_sheet_rel = str(out_path.relative_to(self.workspace))

        return {
            "ok": bool(committed) and not rejected,
            "sliced_count": len(committed),
            "rejected_count": len(rejected),
            "sliced_beats": [str(r.get("beat_id") or "") for r in committed],
            "rejected": rejected,
            "batch_verify_sheet": batch_sheet_rel,
        }

    def build_verify_ftg_clips_sheets(self, job: dict[str, Any]) -> dict[str, Any]:
        """Generate paginated VERIFY_FTG_CLIPS_*.jpg (<=25 clips/sheet) showing 3 frames (15%-50%-85%)
        of every REAL_FTG clip alongside beat_id, source_file, start_offset_sec, and voice_text,
        then run audit_footage_hygiene(workspace, job)."""
        from .critic_loops import audit_footage_hygiene

        with _workspace_registry_lock(self.workspace):
            ftg_review = self._read_json(self.workspace / "footage_review.json", {})
            sel_map = {
                str(item.get("beat_id") or ""): item
                for item in (ftg_review.get("selected_candidates") or [])
                if isinstance(item, dict) and str(item.get("beat_id") or "")
            }
            registry = self._read_json(self.workspace / "asset_registry.json", {})
            for item in (registry.get("assets") or []):
                if isinstance(item, dict) and str(item.get("beat_id") or "") and str(item.get("beat_id") or "") not in sel_map:
                    sel_map[str(item.get("beat_id") or "")] = item

        voice_by_beat = self._voice_text_by_beat()
        items = sorted(sel_map.values(), key=lambda x: str(x.get("beat_id") or ""))
        probes_dir = self.workspace / "media" / "footage" / "probes"
        probes_dir.mkdir(parents=True, exist_ok=True)

        sheet_paths: list[str] = []
        per_sheet = 25
        total_sheets = max(1, (len(items) + per_sheet - 1) // per_sheet)
        for sheet_idx in range(total_sheets):
            batch = items[sheet_idx * per_sheet : (sheet_idx + 1) * per_sheet]
            out_sheet = probes_dir / f"VERIFY_FTG_CLIPS_{sheet_idx + 1}.jpg"
            self._render_contact_sheet_page(batch, out_sheet, voice_by_beat)
            sheet_paths.append(str(out_sheet.relative_to(self.workspace)))

        audit_report = audit_footage_hygiene(self.workspace, job)
        return {
            "ok": str(audit_report.get("status") or "").upper() == "PASSED",
            "verify_sheets": sheet_paths,
            "audit_status": audit_report.get("status"),
            "assets_inspected": audit_report.get("assets_inspected", 0),
            "failed_assets_count": audit_report.get("failed_assets_count", 0),
            "failed_assets": audit_report.get("failed_assets", []),
        }

    def auto_fetch_missing_beats(
        self,
        job: dict[str, Any] | None = None,
        *,
        max_workers: int | None = None,
        max_unique_clips: int = 48,
    ) -> dict[str, Any]:
        raise RuntimeError(
            "FORBIDDEN_AUTO_CUT_AND_SPLICE: Automatic batch cutting and automatic splicing "
            "(auto_fetch_missing_beats / --auto) are strictly banned. Every footage clip must be "
            "individually inspected by the AI Agent's eyes (--probe-storyboard -> read_file on STORYBOARD_*.jpg "
            "& GRID_*.jpg -> exact --start-offset, calibrated --crop-mode stripping 100% of third-party logos "
            "and running text, and --observed-content matching 100% of the spoken sentence)."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Edit-Direct Footage Fetcher for CofiRemotion Edit Agent")
    parser.add_argument("--workspace", required=True, help="Absolute path to the job workspace")
    parser.add_argument("--job-id", required=True, help="Job ID")
    parser.add_argument("--remotion-dir", default="", help="Path to CofiRemotion project")
    parser.add_argument("--auto", action="store_true", help="DISABLED: Automatic batch cutting is strictly forbidden")
    parser.add_argument("--max-unique-clips", type=int, default=48, help="Deprecated")
    parser.add_argument("--beat-id", default="", help="Comma-separated beat IDs to fetch footage for")
    parser.add_argument("--query", default="", help="Search query for B-roll footage")
    parser.add_argument("--url", default="", help="Optional direct video URL")
    parser.add_argument("--start-offset", type=float, default=-1.0, help="Mandatory eye-verified start offset in seconds (>= 0)")
    parser.add_argument("--duration", type=float, default=6.2, help="Target clip slice duration in seconds")
    parser.add_argument("--crop-mode", default="none", help="Mandatory calibrated crop (e.g. crop=W:H:X:Y or forensic_v2_clean; 'none' is forbidden)")
    parser.add_argument("--observed-content", default="", help="Mandatory eye-verified description of what appears in the frame and how it matches 100% of the voice sentence")
    parser.add_argument("--probe-storyboard", default="", help="URL or local video path to extract a storyboard + 100px grid for eye inspection before cutting")
    parser.add_argument("--probe-id", default="raw_source_01", help="Identifier for the storyboard/grid probe output")
    parser.add_argument("--batch-manifest", default="", help="Path to JSON array of 10-15 eye-verified clip specs for parallel slicing + 1 Contact Sheet output")
    parser.add_argument("--batch-sheet-out", default="", help="Optional output path for the batch verification Contact Sheet JPG")
    parser.add_argument("--build-verify-sheets", action="store_true", help="Build VERIFY_FTG_CLIPS_*.jpg contact sheets and run audit_footage_hygiene")
    parser.add_argument("--force", action="store_true", help="Force redownload and re-slice even if cached")
    args = parser.parse_args()

    fetcher = EditDirectFootageFetcher(args.workspace, args.remotion_dir or None, job_id=args.job_id)
    job_payload = fetcher._read_json(Path(args.workspace) / "input.json", {"id": args.job_id})
    job_payload["id"] = args.job_id

    if args.build_verify_sheets:
        verify_res = fetcher.build_verify_ftg_clips_sheets(job_payload)
        print(json.dumps(verify_res, ensure_ascii=False, indent=2))
        return 0 if verify_res.get("ok") else 1

    if args.probe_storyboard:
        probe_res = fetcher.probe_video_storyboard(args.probe_storyboard, args.probe_id)
        print(json.dumps(probe_res, ensure_ascii=False, indent=2))
        return 0 if probe_res.get("ok") else 1

    if args.auto:
        parser.error(
            "FORBIDDEN: --auto automatic cutting and splicing is strictly banned. "
            "Run --probe-storyboard first, inspect STORYBOARD_<id>.jpg and GRID_<id>.jpg by eye, "
            "then slice each beat with explicit --start-offset, --crop-mode, and --observed-content."
        )

    if args.batch_manifest:
        manifest_path = Path(args.batch_manifest)
        raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(raw_manifest, dict):
            raw_manifest = raw_manifest.get("items") or raw_manifest.get("clips") or []
        if not isinstance(raw_manifest, list) or not raw_manifest:
            parser.error("--batch-manifest must point to a non-empty JSON list of beat slice specs")
        sheet_out = Path(args.batch_sheet_out) if args.batch_sheet_out else None
        batch_res = fetcher.fetch_batch_manifest(args.job_id, raw_manifest, sheet_out=sheet_out)
        if batch_res.get("sliced_count"):
            with _workspace_registry_lock(fetcher.workspace):
                manager = RemotionManager(fetcher.remotion_dir, tools_dir=Path(__file__).resolve().parents[1] / "tools")
                manager.prepare_job_media(job_payload, fetcher.workspace)
        print(json.dumps(batch_res, ensure_ascii=False, indent=2))
        return 0 if batch_res.get("sliced_count") and not batch_res.get("rejected_count") else 1

    beat_ids = [b.strip() for b in str(args.beat_id or "").split(",") if b.strip()]
    if not beat_ids or not (args.query or args.url):
        parser.error("Provide --probe-storyboard OR both --beat-id and --query/--url with --start-offset, --crop-mode, and --observed-content")

    if args.start_offset < 0 or str(args.crop_mode or "").strip().lower() in {"", "none"} or len(str(args.observed_content or "").strip()) < 10:
        parser.error(
            "FORBIDDEN: Every footage cut requires eye-verified --start-offset >= 0, "
            "calibrated --crop-mode (not 'none'), and --observed-content (>= 10 chars) matching 100% of the spoken sentence."
        )

    res = fetcher.fetch_for_beats(
        args.job_id,
        beat_ids,
        args.query,
        direct_url=args.url or None,
        start_offset_sec=args.start_offset,
        clip_duration_sec=args.duration,
        crop_mode=args.crop_mode,
        observed_content=args.observed_content,
        force_redownload=args.force,
    )
    if res.get("ok"):
        manager = RemotionManager(fetcher.remotion_dir, tools_dir=Path(__file__).resolve().parents[1] / "tools")
        manager.prepare_job_media(job_payload, fetcher.workspace)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
