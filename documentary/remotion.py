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
    ):
        self.project_dir = Path(project_dir).resolve()
        self.studio_port = int(studio_port)
        self.tools_dir = Path(tools_dir).resolve() if tools_dir else None

    def _ffmpeg_bin(self) -> str | None:
        if self.tools_dir:
            bundled = self.tools_dir / "ffmpeg.exe"
            if bundled.exists():
                return str(bundled)
        return shutil.which("ffmpeg")

    def _ensure_preview_proxy(self, source: Path, preview_dir: Path) -> Path | None:
        """Create a lightweight Studio-only proxy while preserving the canonical source.

        The proxy is deliberately optimized for browser decoding and scrubbing. Final
        Remotion renders must continue to use the canonical file published beside it.
        """
        ffmpeg = self._ffmpeg_bin()
        if not ffmpeg:
            return None
        preview_dir.mkdir(parents=True, exist_ok=True)
        target = preview_dir / f"{source.stem}.preview.mp4"
        if target.exists() and target.stat().st_size > 0 and target.stat().st_mtime >= source.stat().st_mtime:
            return target
        temp = target.with_suffix(".tmp.mp4")
        command = [
            ffmpeg,
            "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", "scale=960:-2:force_original_aspect_ratio=decrease,fps=30",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
            "-pix_fmt", "yuv420p", "-g", "30", "-keyint_min", "30", "-sc_threshold", "0",
            "-c:a", "aac", "-b:a", "96k",
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
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
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

    @property
    def studio_url(self) -> str:
        return f"http://127.0.0.1:{self.studio_port}"

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

    def status(self) -> dict[str, Any]:
        return {
            "ok": self.project_dir.exists(),
            "project_path": str(self.project_dir),
            "studio_running": self.is_running(),
            "studio_url": self.studio_url,
        }

    def composition_registered(self, composition_id: str | None) -> bool:
        composition_id = str(composition_id or "").strip()
        src = self.project_dir / "src"
        if not composition_id or not src.exists():
            return False
        escaped = re.escape(composition_id)
        value = rf'(?:"{escaped}"|\'{escaped}\'|\{{\s*"{escaped}"\s*\}}|\{{\s*\'{escaped}\'\s*\}})'
        pattern = re.compile(rf"<Composition\b(?:(?!>).){{0,1200}}?\bid\s*=\s*{value}", re.DOTALL)
        for path in src.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"}:
                continue
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if pattern.search(source):
                return True
        return False

    def prepare_job_media(self, job: dict[str, Any], workspace: str | Path) -> dict[str, Any]:
        """Publish canonical workspace media into Remotion's public job directory.

        Edit workers should be able to reference approved assets immediately instead
        of discovering and copying them ad hoc during the Codex turn.
        """
        workspace = Path(workspace).resolve()
        job_id = str(job.get("id") or "").strip()
        if not job_id:
            raise RuntimeError("Không có job_id để chuẩn bị media cho Remotion")

        public_dir = self.project_dir / "public" / "jobs" / job_id
        preview_dir = public_dir / "_preview"
        public_dir.mkdir(parents=True, exist_ok=True)
        allowed_suffixes = {
            ".mp4", ".webm", ".mov", ".m4v",
            ".jpg", ".jpeg", ".png", ".webp", ".gif",
            ".wav", ".mp3", ".m4a", ".aac", ".ogg",
        }
        published_by_name: dict[str, Path] = {}
        published_assets: list[dict[str, Any]] = []

        def publish_file(raw_path: str | Path, *, role: str, asset: dict[str, Any] | None = None) -> str:
            source = Path(raw_path)
            if not source.is_absolute():
                source = workspace / source
            source = source.resolve()
            try:
                source.relative_to(workspace)
            except ValueError as exc:
                raise RuntimeError(f"Media Edit nằm ngoài workspace: {source}") from exc
            if not source.exists() or not source.is_file():
                raise RuntimeError(f"Thiếu media Edit đã được duyệt: {source}")
            if source.suffix.lower() not in allowed_suffixes:
                raise RuntimeError(f"Định dạng media Edit không hỗ trợ: {source.name}")

            previous = published_by_name.get(source.name)
            if previous is not None and previous != source:
                raise RuntimeError(f"Trùng tên media từ hai file khác nhau: {source.name}")
            target = public_dir / source.name
            shutil.copy2(source, target)
            published_by_name[source.name] = source
            if asset is not None:
                published = {
                    "asset_id": asset.get("id"),
                    "beat_id": asset.get("beat_id"),
                    "kind": asset.get("kind"),
                    "source_path": str(source),
                    "public_file": source.name,
                }
                if asset.get("kind") == "sourced_video":
                    preview = self._ensure_preview_proxy(source, preview_dir)
                    if preview is not None:
                        published["preview_file"] = f"_preview/{preview.name}"
                published_assets.append(published)
            return source.name

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
        voice_manifest_path = workspace / "voice_manifest.json"
        if voice_manifest_path.exists():
            try:
                voice_manifest = json.loads(voice_manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                voice_manifest = {}
            narration_path = voice_manifest.get("narration_path") if isinstance(voice_manifest, dict) else None
            if narration_path:
                narration_file = publish_file(narration_path, role="narration")
        fallback_narration = workspace / "audio" / "narration.wav"
        if narration_file is None and fallback_narration.exists():
            narration_file = publish_file(fallback_narration, role="narration")

        subtitles_file = None
        subtitles_path = workspace / "subtitles.srt"
        if subtitles_path.exists():
            target = public_dir / subtitles_path.name
            shutil.copy2(subtitles_path, target)
            subtitles_file = subtitles_path.name

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

        manifest = {
            "job_id": job_id,
            "public_dir": str(public_dir),
            "asset_count": len(published_assets),
            "preview_proxy_count": sum(1 for item in published_assets if item.get("preview_file")),
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
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    expected_composition_id = job.get("composition_id") or f"Documentary-{job.get('id')}"
                    data["composition_id"] = expected_composition_id
                    data["studio_url"] = self.studio_url
                    data["composition_url"] = self.composition_url(expected_composition_id)
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
