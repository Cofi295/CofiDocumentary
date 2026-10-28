from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

from .remotion import RemotionManager


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
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = startupinfo
    return kwargs


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
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def search_candidates(self, query: str, max_results: int = 5, *, prefer_case_footage: bool = True) -> list[dict[str, Any]]:
        if not self.ytdlp:
            return []
        clean_q = re.sub(r"\s+", " ", str(query or "").strip())
        if not clean_q:
            return []
        if prefer_case_footage:
            search_spec = f"ytsearch{max_results}:{clean_q} -shorts -tiktok -reaction -podcast -commentary"
        else:
            search_spec = f"ytsearch{max_results}:{clean_q} 4k cinematic b-roll no text -shorts -tiktok -reaction -podcast"
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
            url = str(item.get("url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "")).strip()
            duration = float(item.get("duration") or 0)
            if not url or (duration and (duration < 12 or duration > 3600)):
                continue
            candidates.append({
                "id": vid_id,
                "url": url,
                "title": str(item.get("title") or ""),
                "duration": duration or 60.0,
            })
        return candidates

    def download_and_slice_clip(
        self,
        url: str,
        output_stem: str,
        *,
        duration_hint: float = 60.0,
        clip_duration_sec: float = 5.0,
        start_offset_sec: float | None = None,
    ) -> Path | None:
        if not self.ytdlp or not self.ffmpeg:
            return None
        target = self.media_dir / f"{output_stem}.mp4"
        if target.exists() and target.stat().st_size > 8192:
            return target

        # Strict 3-6s footage slice law (default ~5.0s, clamped 3.0s..6.0s)
        strict_slice_sec = max(3.5, min(6.0, float(clip_duration_sec or 5.0)))
        raw_tmp = self.media_dir / f".raw_{output_stem}.mp4"
        if start_offset_sec is not None and start_offset_sec >= 0:
            max_start = max(18.0, duration_hint - strict_slice_sec - 8.0) if duration_hint > 30 else 600.0
            start_sec = max(15.0, min(max_start, round(float(start_offset_sec), 1)))
        else:
            # Skip opening 28% where TV news anchors / channel hosts typically appear
            start_sec = max(18.0, min(140.0, round(duration_hint * 0.28, 1)))
        end_sec = start_sec + strict_slice_sec
        section_arg = f"*{start_sec:.1f}-{end_sec:.1f}"

        dl_cmd = [
            self.ytdlp,
            "--no-playlist",
            "--no-warnings",
            "--socket-timeout", "15",
            "-f", "bestvideo[height<=1080][ext=mp4]/best[height<=1080][ext=mp4]/best[height<=1080]",
            "--download-sections", section_arg,
            "-o", str(raw_tmp),
            url,
        ]
        try:
            subprocess.run(dl_cmd, timeout=60, check=False, **_subproc_kwargs())
        except Exception:
            raw_tmp.unlink(missing_ok=True)
            return None

        if not raw_tmp.exists() or raw_tmp.stat().st_size < 4096:
            raw_tmp.unlink(missing_ok=True)
            return None

        # Normalize to 1920x1080 30fps H.264, strip source audio (-an),
        # and apply aggressive safe-zone crop to eliminate third-party station logos,
        # top news banners, and bottom burned-in Chinese/foreign subtitles/chyrons.
        norm_tmp = self.media_dir / f".norm_{output_stem}.mp4"
        ff_cmd = [
            self.ffmpeg,
            "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(raw_tmp),
            "-t", f"{strict_slice_sec:.2f}",
            "-an",
            "-vf", "crop=iw*0.72:ih*0.56:iw*0.14:ih*0.19,scale=1920:1080:flags=lanczos,unsharp=3:3:0.55,fps=30,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
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
            return target
        except Exception:
            raw_tmp.unlink(missing_ok=True)
            norm_tmp.unlink(missing_ok=True)
            return None

    def fetch_for_beats(
        self,
        job_id: str,
        beat_ids: list[str],
        query: str,
        *,
        direct_url: str | None = None,
        used_urls: set[str] | None = None,
        url_slice_counts: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        used = used_urls if used_urls is not None else set()
        slice_counts = url_slice_counts if url_slice_counts is not None else {}
        stem = f"edit_broll_{beat_ids[0]}"
        existing_target = self.media_dir / f"{stem}.mp4"
        clip_path: Path | None = existing_target if (existing_target.exists() and existing_target.stat().st_size > 8192) else None
        chosen_url = f"cached://{stem}" if clip_path is not None else ""
        chosen_title = query or stem if clip_path is not None else ""

        if clip_path is None and direct_url:
            s_idx = slice_counts.get(direct_url, 0)
            clip_path = self.download_and_slice_clip(
                direct_url,
                stem,
                start_offset_sec=16.0 + s_idx * 24.0,
            )
            if clip_path:
                chosen_url = direct_url
                chosen_title = query or direct_url
                slice_counts[direct_url] = s_idx + 1
        if clip_path is None:
            candidates = self.search_candidates(query, max_results=8, prefer_case_footage=True)
            for cand in candidates:
                url = cand["url"]
                dur = float(cand.get("duration") or 60.0)
                s_idx = slice_counts.get(url, 0)
                # Only allow slicing multiple non-overlapping scenes from long documentaries (>= 120s)
                if url in used and (dur < 120.0 or (18.0 + s_idx * 26.0 + 18.0) >= dur):
                    continue
                clip_path = self.download_and_slice_clip(
                    url,
                    stem,
                    duration_hint=dur,
                    start_offset_sec=18.0 + s_idx * 26.0 if dur >= 90.0 else None,
                )
                if clip_path is not None:
                    chosen_url = url
                    chosen_title = str(cand.get("title") or query)
                    used.add(url)
                    slice_counts[url] = s_idx + 1
                    break

        if clip_path is None:
            return {"ok": False, "beat_ids": beat_ids, "query": query, "error": "No usable B-roll clip downloaded"}

        rel_path = str(clip_path.relative_to(self.workspace))
        registry_path = self.workspace / "asset_registry.json"
        registry = self._read_json(registry_path, {"assets": [], "ai_fallback_beats": [], "ai_usage_notes": []})
        assets = [
            item for item in (registry.get("assets") or [])
            if isinstance(item, dict) and str(item.get("beat_id") or "") not in set(beat_ids)
        ]
        for bid in beat_ids:
            # Each beat gets its own symlink/copy or canonical reference in media/edit_footage so RemotionManager.prepare_job_media can publish unique file names per beat
            beat_file = self.media_dir / f"{bid}_edit_broll.mp4"
            if beat_file.resolve() != clip_path.resolve():
                shutil.copy2(clip_path, beat_file)
            assets.append({
                "id": f"edit_broll_{bid}",
                "beat_id": bid,
                "kind": "sourced_video",
                "path": str(beat_file.relative_to(self.workspace)),
                "source": {
                    "fetched_by": "edit_direct_footage_agent",
                    "query": query,
                    "url": chosen_url,
                    "title": chosen_title,
                    "fetched_at": _now(),
                },
            })
        registry["assets"] = assets
        self._write_json(registry_path, registry)
        return {
            "ok": True,
            "beat_ids": beat_ids,
            "query": query,
            "url": chosen_url,
            "path": rel_path,
        }

    def auto_fetch_missing_beats(
        self,
        job: dict[str, Any] | None = None,
        *,
        max_workers: int = 3,
        max_unique_clips: int = 48,
    ) -> dict[str, Any]:
        if job is None:
            job = self._read_json(self.workspace / "input.json", {"id": self.job_id})
        job_id = str(job.get("id") or self.job_id or self.workspace.name).strip()
        job["id"] = job_id
        visual = self._read_json(self.workspace / "visual_manifest.json", {"beats": []})
        registry = self._read_json(self.workspace / "asset_registry.json", {"assets": []})
        covered_ids = {
            str(a.get("beat_id") or "").strip()
            for a in (registry.get("assets") or [])
            if isinstance(a, dict)
            and str(a.get("beat_id") or "").strip()
            and (self.workspace / str(a.get("path") or "")).is_file()
        }
        beats = [b for b in (visual.get("beats") or []) if isinstance(b, dict) and str(b.get("beat_id") or "").strip()]
        uncovered_footage_beats = [
            b for b in beats
            if str(b.get("beat_id") or "").strip() not in covered_ids
            and str(b.get("visual_route") or "").strip().lower() != "ai_visual"
        ]
        if not uncovered_footage_beats:
            manager = RemotionManager(self.remotion_dir, tools_dir=Path(__file__).resolve().parents[1] / "tools")
            manifest = manager.prepare_job_media(job, self.workspace)
            return {"ok": True, "fetched_groups": 0, "published_assets": manifest.get("asset_count", 0)}

        profile_id = str(
            job.get("channel_profile_id")
            or ((job.get("channel_profile_snapshot") or {}).get("id") if isinstance(job.get("channel_profile_snapshot"), dict) else "")
            or ""
        ).strip()
        preset_id = str(((job.get("editing_dna") or {}).get("preset_id") if isinstance(job.get("editing_dna"), dict) else "") or "").strip()
        is_financial_crime = profile_id == "channel-cn-cyber-finance-kr" or preset_id == "financial_forensic_vox"

        # Group adjacent uncovered beats by story_group (max 3 beats per clip group)
        groups: list[tuple[list[str], str]] = []
        current_ids: list[str] = []
        current_group = ""
        current_query = ""

        if is_financial_crime:
            fallback_queries = [
                "bank cash counting machine yuan currency close up 4k",
                "cyber police server room data center investigation 4k",
                "cryptocurrency bitcoin trading chart monitor dark room 4k",
                "smartphone farm racks automation server room b-roll",
                "london hampstead luxury mansion aerial drone 4k",
                "financial district skyscrapers night timelapse 4k",
                "police cyber crime unit computer forensic lab",
                "hardware crypto cold wallet usb ledger close up",
            ]
        else:
            fallback_queries = [
                "sunrise over misty mountains cinematic 4k nature",
                "calm ocean waves golden hour sunset 4k",
                "sunlight rays through peaceful forest trees 4k",
                "open bible pages warm candlelight table cinematic",
                "rain drops on window glass warm bokeh night",
                "starry night sky milky way timelapse mountains",
                "gentle river stream flowing through autumn forest 4k",
                "wheat field blowing in golden sunset wind cinematic",
            ]

        for idx, beat in enumerate(uncovered_footage_beats):
            bid = str(beat.get("beat_id") or "").strip()
            queries = beat.get("footage_search_queries")
            q = ""
            if isinstance(queries, list) and queries:
                q = str(queries[0] or "").strip()
            if not q:
                q = str(beat.get("visual_description") or "").strip()[:90]
            if not q:
                q = fallback_queries[idx % len(fallback_queries)]
            groups.append(([bid], q))

        if max_unique_clips and max_unique_clips > 0:
            groups = groups[: max(int(max_unique_clips), len(uncovered_footage_beats))]

        used_urls: set[str] = set()
        url_slice_counts: dict[str, int] = {}
        results: list[dict[str, Any]] = []
        for beat_ids, query in groups:
            res = self.fetch_for_beats(job_id, beat_ids, query, used_urls=used_urls, url_slice_counts=url_slice_counts)
            if not res.get("ok"):
                fb_q = fallback_queries[len(results) % len(fallback_queries)]
                res = self.fetch_for_beats(job_id, beat_ids, fb_q, used_urls=used_urls, url_slice_counts=url_slice_counts)
            results.append(res)

        manager = RemotionManager(self.remotion_dir, tools_dir=Path(__file__).resolve().parents[1] / "tools")
        manifest = manager.prepare_job_media(job, self.workspace)
        return {
            "ok": True,
            "fetched_groups": sum(1 for r in results if r.get("ok")),
            "total_groups": len(groups),
            "published_assets": manifest.get("asset_count", 0),
            "results": results,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Edit-Direct Footage Fetcher for CofiRemotion Edit Agent")
    parser.add_argument("--workspace", required=True, help="Absolute path to the job workspace")
    parser.add_argument("--job-id", required=True, help="Job ID")
    parser.add_argument("--remotion-dir", default="", help="Path to CofiRemotion project")
    parser.add_argument("--auto", action="store_true", help="Automatically fetch B-roll for all uncovered footage beats")
    parser.add_argument("--max-unique-clips", type=int, default=48, help="Max unique clip groups to fetch in auto mode")
    parser.add_argument("--beat-id", default="", help="Comma-separated beat IDs to fetch footage for")
    parser.add_argument("--query", default="", help="Search query for B-roll footage")
    parser.add_argument("--url", default="", help="Optional direct video URL")
    parser.add_argument("--duration", type=float, default=5.0, help="Target clip slice duration in seconds (strictly 3-6s)")
    args = parser.parse_args()

    fetcher = EditDirectFootageFetcher(args.workspace, args.remotion_dir or None, job_id=args.job_id)
    job_payload = fetcher._read_json(Path(args.workspace) / "input.json", {"id": args.job_id})
    job_payload["id"] = args.job_id

    if args.auto:
        summary = fetcher.auto_fetch_missing_beats(job_payload, max_unique_clips=args.max_unique_clips)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    beat_ids = [b.strip() for b in str(args.beat_id or "").split(",") if b.strip()]
    if not beat_ids or not (args.query or args.url):
        parser.error("Provide --auto OR both --beat-id and --query/--url")

    res = fetcher.fetch_for_beats(args.job_id, beat_ids, args.query, direct_url=args.url or None)
    if res.get("ok"):
        manager = RemotionManager(fetcher.remotion_dir, tools_dir=Path(__file__).resolve().parents[1] / "tools")
        manager.prepare_job_media(job_payload, fetcher.workspace)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
