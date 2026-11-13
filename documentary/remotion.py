from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
from typing import Any
from urllib.parse import quote


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RemotionManager:
    def __init__(
        self,
        project_dir: str | Path,
        studio_port: int = 8890,
        tools_dir: str | Path | None = None,
        nle_port: int = 8891,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.studio_port = int(studio_port)
        self.nle_port = int(nle_port)
        self.tools_dir = Path(tools_dir).resolve() if tools_dir else None
        self._comp_reg_cache: dict[str, tuple[float, bool]] = {}

    def _ffmpeg_bin(self) -> str | None:
        if self.tools_dir:
            bundled = self.tools_dir / "ffmpeg.exe"
            if bundled.exists():
                return str(bundled)
        return shutil.which("ffmpeg")

    def _ensure_preview_proxy(self, source: Path, preview_dir: Path) -> Path | None:
        """Create a lightweight 30fps Studio-only proxy while preserving the canonical source.

        The proxy is deliberately optimized for WebCodecs/browser decoding and scrubbing
        (baseline profile, fastdecode, g=15, muted -an). Final Remotion renders continue
        to use the canonical 1080p file published beside it.
        """
        ffmpeg = self._ffmpeg_bin()
        if not ffmpeg:
            return None
        preview_dir.mkdir(parents=True, exist_ok=True)
        target = preview_dir / f"{source.stem}.preview.mp4"
        if target.exists() and target.stat().st_size > 1024 and target.stat().st_mtime >= source.stat().st_mtime:
            return target
        from .render_cache import background_worker_creationflags, detect_hardware_profile

        ff_threads = str(max(1, int(detect_hardware_profile().get("edit_ffmpeg_threads") or 2)))
        temp = target.with_suffix(".tmp.mp4")
        command = [
            ffmpeg,
            "-hide_banner", "-loglevel", "error", "-y",
            "-threads", ff_threads,
            "-i", str(source),
            "-map", "0:v:0", "-an",
            "-vf", "scale=1920:-2:force_original_aspect_ratio=decrease,fps=30",
            "-c:v", "libx264", "-profile:v", "high", "-tune", "fastdecode",
            "-preset", "fast", "-crf", "18",
            "-threads", ff_threads,
            "-pix_fmt", "yuv420p", "-g", "15", "-keyint_min", "15", "-sc_threshold", "0",
            # Studio preview proxies strip source audio (-an) to guarantee zero bleed
            "-movflags", "+faststart",
            str(temp),
        ]
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
        result = subprocess.run(command, **kwargs)
        if result.returncode != 0 or not temp.exists() or temp.stat().st_size <= 0:
            temp.unlink(missing_ok=True)
            return None
        temp.replace(target)
        return target

    def ensure_job_preview_proxies(self, job_id: str, workspace: Path | None = None, *, skip_encode: bool = False) -> dict[str, Any]:
        """Ensure 30fps muted fastdecode _preview proxies exist for all video clips of a job
        (both top-level public/jobs/<job_id>/*.mp4 and subfolders like footage/*.mp4 & vox/*.mp4).
        """
        job_id = str(job_id or "").strip()
        if not job_id:
            return {"generated": 0, "total": 0}
        public_dir = self.project_dir / "public" / "jobs" / job_id
        preview_root = public_dir / "_preview"
        if not public_dir.exists():
            return {"generated": 0, "total": 0}

        if workspace is not None:
            ws_root = Path(workspace).resolve()
            ws_footage = ws_root / "footage"
            if ws_footage.exists():
                pub_footage = public_dir / "footage"
                pub_footage.mkdir(parents=True, exist_ok=True)
                for clip in ws_footage.glob("*.mp4"):
                    dst = pub_footage / clip.name
                    if not dst.exists() or dst.stat().st_size != clip.stat().st_size or dst.stat().st_mtime < clip.stat().st_mtime:
                        shutil.copy2(clip, dst)
            ws_vox_plates = ws_root / "vox_plates"
            if ws_vox_plates.exists():
                pub_vox_plates = public_dir / "vox_plates"
                pub_vox_plates.mkdir(parents=True, exist_ok=True)
                for plate_file in ws_vox_plates.iterdir():
                    if plate_file.is_file() and plate_file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".svg", ".mp4", ".webm", ".json", ".geojson"}:
                        dst = pub_vox_plates / plate_file.name
                        if not dst.exists() or dst.stat().st_size != plate_file.stat().st_size or dst.stat().st_mtime < plate_file.stat().st_mtime:
                            shutil.copy2(plate_file, dst)
            for ws_ai_dir in (ws_root / "media" / "ai", ws_root / "ai"):
                if ws_ai_dir.exists():
                    pub_ai = public_dir / "ai"
                    pub_ai.mkdir(parents=True, exist_ok=True)
                    for ai_file in ws_ai_dir.iterdir():
                        if ai_file.is_file() and ai_file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm"}:
                            dst = pub_ai / ai_file.name
                            if not dst.exists() or dst.stat().st_size != ai_file.stat().st_size or dst.stat().st_mtime < ai_file.stat().st_mtime:
                                shutil.copy2(ai_file, dst)
        if skip_encode:
            return {"generated": 0, "total": 0}

        video_exts = {".mp4", ".webm", ".mov", ".m4v"}
        tasks: list[tuple[Path, Path, str]] = []
        for candidate in public_dir.rglob("*"):
            if not candidate.is_file() or candidate.suffix.lower() not in video_exts:
                continue
            rel = candidate.relative_to(public_dir)
            if rel.parts and rel.parts[0] == "_preview":
                continue
            if candidate.name.endswith(".preview.mp4") or candidate.name.endswith(".tmp.mp4"):
                continue
            target_dir = preview_root / rel.parent if str(rel.parent) != "." else preview_root
            tasks.append((candidate, target_dir, rel.as_posix()))

        if not tasks:
            return {"generated": 0, "total": 0}

        from concurrent.futures import ThreadPoolExecutor
        from .render_cache import detect_hardware_profile

        max_proxy_workers = max(1, min(2, int(detect_hardware_profile().get("edit_worker_concurrency") or 2)))
        proxy_map: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=max_proxy_workers) as pool:
            futures = [
                (rel_key, pool.submit(self._ensure_preview_proxy, src, tdir))
                for src, tdir, rel_key in tasks
            ]
            for rel_key, fut in futures:
                try:
                    out = fut.result()
                    if out is not None:
                        proxy_map[rel_key] = out.relative_to(public_dir).as_posix()
                except Exception:
                    continue

        preview_root.mkdir(parents=True, exist_ok=True)
        (preview_root / "index.json").write_text(
            json.dumps(
                {
                    "job_id": job_id,
                    "count": len(proxy_map),
                    "updated_at": _now(),
                    "proxies": proxy_map,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"generated": len(proxy_map), "total": len(tasks)}

    @property
    def studio_url(self) -> str:
        return f"http://127.0.0.1:{self.studio_port}"

    @property
    def nle_base_url(self) -> str:
        return f"http://127.0.0.1:{self.nle_port}"

    def nle_url(self, job_id: str | None, composition_id: str | None) -> str:
        jid = quote(str(job_id or "").strip(), safe="")
        cid = quote(str(composition_id or "").strip(), safe="")
        return f"{self.nle_base_url}/?jobId={jid}&compId={cid}"

    def composition_url(self, composition_id: str | None) -> str:
        composition_id = str(composition_id or "").strip()
        if not composition_id:
            return self.studio_url
        return f"{self.studio_url}/{quote(composition_id, safe='')}"

    def is_running(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", self.studio_port), timeout=0.35):
                return True
        except OSError:
            return False

    def is_nle_running(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", self.nle_port), timeout=0.35):
                return True
        except OSError:
            return False

    def ensure_nle_server(self) -> bool:
        if self.is_nle_running():
            return True
        script = self.project_dir / "scripts" / "nle-player-server.mjs"
        node = shutil.which("node")
        if not node or not script.exists():
            return False
        command = [node, str(script), f"--port={self.nle_port}"]
        kwargs: dict[str, Any] = {
            "cwd": str(self.project_dir),
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
        }
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        else:
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
            startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
            kwargs["startupinfo"] = startupinfo
        try:
            subprocess.Popen(command, **kwargs)
            for _ in range(12):
                if self.is_nle_running():
                    return True
                time.sleep(0.15)
        except OSError:
            return False
        return self.is_nle_running()

    def status(self) -> dict[str, Any]:
        return {
            "ok": self.project_dir.exists(),
            "project_path": str(self.project_dir),
            "studio_running": self.is_running(),
            "studio_url": self.studio_url,
            "nle_running": self.is_nle_running(),
            "nle_base_url": self.nle_base_url,
        }

    def composition_registered(self, composition_id: str | None) -> bool:
        composition_id = str(composition_id or "").strip()
        src = self.project_dir / "src"
        if not composition_id or not src.exists():
            return False
        candidate_files = [
            p for p in src.rglob("*")
            if p.is_file()
            and p.suffix.lower() in {".tsx", ".jsx", ".ts", ".js"}
            and not p.name.endswith("Data.ts")
        ]
        latest_mtime = max((p.stat().st_mtime for p in candidate_files), default=0.0)
        cached = self._comp_reg_cache.get(composition_id)
        if cached is not None and cached[0] >= latest_mtime:
            return cached[1]
        escaped = re.escape(composition_id)
        value = rf'(?:"{escaped}"|\'{escaped}\'|\{{\s*"{escaped}"\s*\}}|\{{\s*\'{escaped}\'\s*\}})'
        pattern = re.compile(rf"<Composition\b(?:(?!>).){{0,1200}}?\bid\s*=\s*{value}", re.DOTALL)
        root_tsx = src / "Root.tsx"
        ordered = ([root_tsx] if root_tsx.exists() else []) + [p for p in candidate_files if p != root_tsx]
        for path in ordered:
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if pattern.search(source):
                self._comp_reg_cache[composition_id] = (latest_mtime, True)
                return True
        self._comp_reg_cache[composition_id] = (latest_mtime, False)
        return False

    def prepare_job_media(self, job: dict[str, Any], workspace: str | Path, *, skip_preview_proxies: bool = False) -> dict[str, Any]:
        """Publish canonical workspace media into Remotion's public job directory.

        Edit workers should be able to reference approved assets immediately instead
        of discovering and copying them ad hoc during the Codex turn.
        """
        workspace = Path(workspace).resolve()
        job_id = str(job.get("id") or "").strip()
        if not job_id:
            raise RuntimeError("Không có job_id để chuẩn bị media cho Remotion")

        public_dir = (self.project_dir / "public" / "jobs" / job_id).resolve()
        preview_dir = public_dir / "_preview"
        public_dir.mkdir(parents=True, exist_ok=True)
        allowed_suffixes = {
            ".mp4", ".webm", ".mov", ".m4v",
            ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg",
            ".wav", ".mp3", ".m4a", ".aac", ".ogg",
            ".json", ".geojson",
        }
        published_by_name: dict[str, Path] = {}
        published_assets: list[dict[str, Any]] = []

        def publish_file(raw_path: str | Path, *, role: str, asset: dict[str, Any] | None = None) -> str:
            source = Path(raw_path)
            if not source.is_absolute():
                source = workspace / source
            source = source.resolve()
            in_workspace = True
            rel_in_public: Path | None = None
            try:
                source.relative_to(workspace)
            except ValueError as exc:
                in_workspace = False
                try:
                    rel_in_public = source.relative_to(public_dir)
                except ValueError:
                    raise RuntimeError(f"Media Edit nằm ngoài workspace: {source}") from exc
            if not source.exists() or not source.is_file():
                raise RuntimeError(f"Thiếu media Edit đã được duyệt: {source}")
            if source.suffix.lower() not in allowed_suffixes:
                raise RuntimeError(f"Định dạng media Edit không hỗ trợ: {source.name}")

            if in_workspace:
                public_rel_str = source.name
                previous = published_by_name.get(public_rel_str)
                if previous is not None and previous != source:
                    raise RuntimeError(f"Trùng tên media từ hai file khác nhau: {source.name}")
                target = public_dir / source.name
                if target.resolve() != source:
                    shutil.copy2(source, target)
                published_by_name[public_rel_str] = source
            else:
                assert rel_in_public is not None
                public_rel_str = rel_in_public.as_posix()
                previous = published_by_name.get(public_rel_str)
                if previous is not None and previous != source:
                    raise RuntimeError(f"Trùng tên media từ hai file khác nhau: {public_rel_str}")
                mirror_dst = (workspace / "media" / "edit_plates" / rel_in_public).resolve()
                mirror_dst.parent.mkdir(parents=True, exist_ok=True)
                if mirror_dst != source:
                    shutil.copy2(source, mirror_dst)
                published_by_name[public_rel_str] = source

            if asset is not None:
                published = {
                    "asset_id": asset.get("id"),
                    "beat_id": asset.get("beat_id"),
                    "kind": asset.get("kind"),
                    "source_path": str(source),
                    "public_file": public_rel_str,
                }
                if asset.get("kind") == "sourced_video" and not skip_preview_proxies:
                    preview = self._ensure_preview_proxy(source, preview_dir)
                    if preview is not None:
                        published["preview_file"] = f"_preview/{preview.name}"
                published_assets.append(published)
            return public_rel_str

        registry_path = workspace / "asset_registry.json"
        registry: dict[str, Any] = {}
        if registry_path.exists():
            try:
                loaded = json.loads(registry_path.read_text(encoding="utf-8"))
                registry = loaded if isinstance(loaded, dict) else {}
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Không đọc được asset_registry.json để chuẩn bị Remotion: {exc}") from exc
        for asset in registry.get("assets") or []:
            if not isinstance(asset, dict) or not asset.get("path"):
                continue
            publish_file(asset["path"], role="asset", asset=asset)

        narration_file = None
        narration_candidates: list[Path] = []
        voice_manifest_path = workspace / "voice_manifest.json"
        if voice_manifest_path.exists():
            try:
                voice_manifest = json.loads(voice_manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                voice_manifest = {}
            narration_path = voice_manifest.get("narration_path") if isinstance(voice_manifest, dict) else None
            if narration_path:
                cand = Path(narration_path)
                if not cand.is_absolute():
                    cand = workspace / cand
                if cand.exists() and cand.is_file():
                    narration_candidates.append(cand.resolve())
        fallback_narration = workspace / "audio" / "narration.wav"
        if fallback_narration.exists() and fallback_narration.is_file():
            fb_resolved = fallback_narration.resolve()
            if fb_resolved not in narration_candidates:
                narration_candidates.append(fb_resolved)
        if narration_candidates:
            newest_narration = max(narration_candidates, key=lambda p: p.stat().st_mtime)
            narration_file = publish_file(newest_narration, role="narration")
            job_audio_sync_dir = public_dir / "audio"
            job_audio_sync_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(newest_narration, job_audio_sync_dir / newest_narration.name)
            newest_mtime = newest_narration.stat().st_mtime
            for stale_dir in (public_dir, job_audio_sync_dir):
                for stale_proxy in stale_dir.glob("narration*.m4a"):
                    if stale_proxy.stat().st_mtime < newest_mtime:
                        stale_proxy.unlink(missing_ok=True)

        subtitles_file = None
        subtitles_path = workspace / "subtitles.srt"
        if subtitles_path.exists():
            target = public_dir / subtitles_path.name
            shutil.copy2(subtitles_path, target)
            subtitles_file = subtitles_path.name
        for score_file in ("edit_rhythm_score.json", "editorial_voice_plan.json"):
            score_src = workspace / score_file
            if score_src.exists() and score_src.is_file():
                shutil.copy2(score_src, public_dir / score_file)

        audio_lib_dir = Path(__file__).resolve().parents[1] / "presets" / "audio_library"
        published_audio_lib: list[str] = []
        if audio_lib_dir.exists():
            job_audio_dir = public_dir / "audio"
            job_audio_dir.mkdir(parents=True, exist_ok=True)
            for sub in ("bgm", "sfx"):
                sub_dir = audio_lib_dir / sub
                if sub_dir.exists():
                    for audio_file in sorted(sub_dir.glob("*.mp3")):
                        shutil.copy2(audio_file, job_audio_dir / audio_file.name)
                        published_audio_lib.append(f"audio/{audio_file.name}")

        subfolder_proxies = self.ensure_job_preview_proxies(job_id, workspace=workspace, skip_encode=skip_preview_proxies)
        manifest = {
            "job_id": job_id,
            "public_dir": str(public_dir),
            "asset_count": len(published_assets),
            "preview_proxy_count": max(
                int(subfolder_proxies.get("generated") or 0),
                sum(1 for item in published_assets if item.get("preview_file")),
            ),
            "assets": published_assets,
            "narration_file": narration_file,
            "subtitles_file": subtitles_file,
            "audio_library": published_audio_lib,
            "prepared_at": _now(),
        }
        manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2)
        (workspace / "remotion_media_manifest.json").write_text(manifest_text, encoding="utf-8")
        (public_dir / "remotion_media_manifest.json").write_text(manifest_text, encoding="utf-8")
        return manifest

    def ensure_session(self, job: dict[str, Any], workspace: str | Path) -> dict[str, Any]:
        workspace = Path(workspace).resolve()
        path = workspace / "edit_session.json"
        self.ensure_nle_server()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    expected_composition_id = job.get("composition_id") or f"Documentary-{job.get('id')}"
                    data["composition_id"] = expected_composition_id
                    data["studio_url"] = self.studio_url
                    data["composition_url"] = self.composition_url(expected_composition_id)
                    data["nle_url"] = self.nle_url(job.get("id"), expected_composition_id)
                    data["nle_running"] = self.is_nle_running()
                    data["studio_running"] = self.is_running()
                    data["composition_registered"] = self.composition_registered(expected_composition_id)
                    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    return data
            except json.JSONDecodeError:
                pass
        composition_id = job.get("composition_id") or f"Documentary-{job.get('id')}"
        data = {
            "job_id": job.get("id"),
            "project_path": str(self.project_dir),
            "composition_id": composition_id,
            "studio_url": self.studio_url,
            "composition_url": self.composition_url(composition_id),
            "nle_url": self.nle_url(job.get("id"), composition_id),
            "nle_running": self.is_nle_running(),
            "studio_running": self.is_running(),
            "composition_registered": self.composition_registered(composition_id),
            "created_at": _now(),
            "last_edit_at": None,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def _source_hashes(self) -> list[dict[str, Any]]:
        src = self.project_dir / "src"
        result: list[dict[str, Any]] = []
        if not src.exists():
            return result
        for path in sorted(p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".css", ".json"}):
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            result.append({
                "path": str(path.relative_to(self.project_dir)),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
            })
        return result

    def checkpoint(self, job: dict[str, Any], workspace: str | Path, *, note: str = "") -> dict[str, Any]:
        workspace = Path(workspace).resolve()
        job_id = str(job.get("id") or "").strip()
        if job_id:
            try:
                self.ensure_job_preview_proxies(job_id, workspace=workspace)
            except Exception:
                pass
        session = self.ensure_session(job, workspace)
        data = {
            "job_id": job.get("id"),
            "composition_id": session.get("composition_id"),
            "project_path": str(self.project_dir),
            "studio_url": self.studio_url,
            "composition_url": self.composition_url(session.get("composition_id")),
            "composition_registered": bool(session.get("composition_registered")),
            "saved_at": _now(),
            "note": note,
            "source_hashes": self._source_hashes(),
        }
        (workspace / "edit_checkpoint.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        session["last_edit_at"] = data["saved_at"]
        (workspace / "edit_session.json").write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def _run_auto_update(self) -> None:
        script = self.project_dir / "scripts" / "auto-update-remotion.mjs"
        node = shutil.which("node")
        if not node or not script.exists():
            return
        log_dir = self.project_dir / ".tmp"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "remotion-auto-update.log"
        if log_path.exists() and (time.time() - log_path.stat().st_mtime) < 86400:
            return
        try:
            with log_path.open("a", encoding="utf-8") as log:
                subprocess.run(
                    [node, str(script)],
                    cwd=str(self.project_dir),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    timeout=330,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
        except (OSError, subprocess.TimeoutExpired):
            # Auto-update must never prevent Studio from starting with the
            # already-installed, verified Remotion version.
            return

    def start_studio(self, job: dict[str, Any], workspace: str | Path) -> dict[str, Any]:
        session = self.ensure_session(job, workspace)
        if self.is_running():
            session["studio_running"] = True
            return session
        npx = shutil.which("npx")
        if not npx:
            raise RuntimeError("Không tìm thấy npx để chạy Remotion Studio")
        self._run_auto_update()
        command = [npx, "remotion", "studio", "--no-open", f"--port={self.studio_port}"]
        shell = str(npx).lower().endswith((".cmd", ".bat"))
        launch = subprocess.list2cmdline(command) if shell else command
        kwargs: dict[str, Any] = {
            "cwd": str(self.project_dir),
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
            "shell": shell,
        }
        if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        else:
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
            startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
            kwargs["startupinfo"] = startupinfo
        subprocess.Popen(launch, **kwargs)
        for _ in range(20):
            if self.is_running():
                break
            time.sleep(0.25)
        return self.ensure_session(job, workspace)

    def stop_studio(self) -> bool:
        """Stop Remotion Studio on ``studio_port`` to free ~725MB RAM when not actively used."""
        from .cache_manager import stop_port_listener_process

        return stop_port_listener_process(self.studio_port)

