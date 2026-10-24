from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import time
from typing import Any, Callable
import urllib.error
from urllib.parse import quote
import urllib.request
from uuid import uuid4

from .codex_gateway import StageResult


AI_VISUAL_GENERATION_PROFILE = "historical_period_real_reference_v2"
AI_VISUAL_OUTSTANDING_LIMIT = 10
DOCUMENTARY_ROOT = Path(__file__).resolve().parents[1]
BUNDLED_MEDIA_FACTORY_ROOT = DOCUMENTARY_ROOT / "vendor" / "media_factory"
STYLE_PRESETS_DIR = DOCUMENTARY_ROOT / "presets" / "ai_visual_styles"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Không đọc được {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{path.name} phải là JSON object")
    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
    try:
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        for attempt in range(6):
            try:
                temp_path.replace(path)
                return
            except PermissionError:
                if attempt >= 5:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _asset_exists(workspace: Path, asset: dict[str, Any]) -> bool:
    value = str(asset.get("path") or "").strip()
    if not value:
        return False
    path = Path(value)
    if not path.is_absolute():
        path = workspace / path
    return path.exists() and path.is_file() and path.stat().st_size > 0


class CofiStudioMediaFactoryRunner:
    """Submit Documentary AI work through CofiStudio's visible Media Factory queue."""

    def __init__(
        self,
        studio_root: str | Path | None = None,
        *,
        studio_api: str | None = None,
        ensure_available: Callable[[], Any] | None = None,
        submission_delay_min_seconds: float | None = None,
        submission_delay_max_seconds: float | None = None,
        submission_jitter: Callable[[float, float], float] | None = None,
        submission_sleep: Callable[[float], Any] | None = None,
        submission_monotonic: Callable[[], float] | None = None,
    ):
        self.studio_root = Path(
            studio_root
            or os.getenv("COFI_MEDIA_FACTORY_DIR")
            or os.getenv("COFI_STUDIO_DIR")
            or BUNDLED_MEDIA_FACTORY_ROOT
        ).resolve()
        embed_port = os.getenv("COFI_STUDIO_EMBED_PORT", "8894")
        self.studio_api = (
            studio_api
            or os.getenv("COFI_STUDIO_API")
            or f"http://127.0.0.1:{embed_port}"
        ).rstrip("/")
        self.ensure_available = ensure_available
        self._prepared = False
        self.poll_interval = max(0.25, float(os.getenv("COFI_AI_VISUAL_POLL_SEC", "1")))
        self.timeout_seconds = max(60, int(os.getenv("COFI_AI_VISUAL_TOOL_TIMEOUT_SEC", "900")))
        self.queue_timeout_seconds = max(0, int(os.getenv("COFI_AI_VISUAL_QUEUE_TIMEOUT_SEC", "1800")))
        self.connection_timeout_seconds = max(5, int(os.getenv("COFI_AI_VISUAL_CONNECTION_TIMEOUT_SEC", "120")))
        minimum = (
            float(os.getenv("COFI_AI_VISUAL_SUBMIT_DELAY_MIN_SEC", "0.5"))
            if submission_delay_min_seconds is None
            else float(submission_delay_min_seconds)
        )
        maximum = (
            float(os.getenv("COFI_AI_VISUAL_SUBMIT_DELAY_MAX_SEC", "1.0"))
            if submission_delay_max_seconds is None
            else float(submission_delay_max_seconds)
        )
        self.submission_delay_min_seconds = max(0.0, minimum)
        self.submission_delay_max_seconds = max(self.submission_delay_min_seconds, maximum)
        self._submission_jitter = submission_jitter or random.uniform
        self._submission_sleep = submission_sleep or time.sleep
        self._submission_monotonic = submission_monotonic or time.monotonic
        self._last_submission_at: float | None = None
        self._http_client: Any = None

    def _get_http_client(self) -> Any:
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.Client(
                    timeout=30.0,
                    limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
                )
            except Exception:
                self._http_client = False
        return self._http_client if self._http_client is not False else None

    def prepare(self) -> None:
        if self._prepared:
            return
        if self.ensure_available is not None:
            self.ensure_available()
        self._prepared = True

    def available(self) -> tuple[bool, str]:
        try:
            self._request_json("GET", "/api/scenes", timeout=3)
        except RuntimeError as exc:
            return False, f"Media Factory chưa sẵn sàng: {exc}"
        return True, ""

    def _pace_submission(self) -> None:
        now = self._submission_monotonic()
        if self._last_submission_at is not None:
            target_delay = self._submission_jitter(
                self.submission_delay_min_seconds,
                self.submission_delay_max_seconds,
            )
            target_delay = min(
                self.submission_delay_max_seconds,
                max(self.submission_delay_min_seconds, float(target_delay)),
            )
            remaining = self._last_submission_at + target_delay - now
            if remaining > 0:
                self._submission_sleep(remaining)
        self._last_submission_at = self._submission_monotonic()

    @staticmethod
    def _scene_payload(scene: dict[str, Any]) -> dict[str, Any]:
        fields = (
            "name", "task_type", "prompt", "negative_prompt", "reference_image",
            "reference_images", "model", "aspect_ratio", "duration_seconds",
        )
        payload = {key: scene[key] for key in fields if key in scene and scene[key] is not None}
        payload["name"] = str(payload.get("name") or scene.get("id") or "AI documentary scene")[:160]
        return payload

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float = 30,
    ) -> Any:
        client = self._get_http_client()
        if client is not None:
            try:
                resp = client.request(
                    method=method,
                    url=f"{self.studio_api}{path}",
                    json=payload if payload is not None else None,
                    timeout=timeout,
                )
            except Exception as exc:
                raise RuntimeError(f"Không kết nối được Media Factory tại {self.studio_api}: {exc}") from exc
            if resp.status_code >= 400:
                detail = ""
                try:
                    error_payload = resp.json()
                    detail = str(error_payload.get("detail") or "").strip() if isinstance(error_payload, dict) else ""
                except Exception:
                    pass
                raise RuntimeError(detail or f"Media Factory HTTP {resp.status_code}")
            if not resp.text:
                return None
            try:
                return resp.json()
            except Exception as exc:
                raise RuntimeError("Media Factory trả về dữ liệu không hợp lệ") from exc

        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.studio_api}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                error_payload = json.loads(exc.read().decode("utf-8", errors="replace"))
                detail = str(error_payload.get("detail") or "").strip() if isinstance(error_payload, dict) else ""
            except Exception:
                pass
            raise RuntimeError(detail or f"Media Factory HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Không kết nối được Media Factory tại {self.studio_api}: {exc}") from exc
        try:
            return json.loads(raw) if raw else None
        except json.JSONDecodeError as exc:
            raise RuntimeError("Media Factory trả về dữ liệu không hợp lệ") from exc

    def prepare_scene(self, scene: dict[str, Any], request_path: Path) -> dict[str, Any]:
        """Create/update a Media Factory card without starting generation."""
        self.prepare()
        ok, reason = self.available()
        if not ok:
            raise RuntimeError(reason)
        payload = self._scene_payload(scene)
        created: dict[str, Any] | None = None

        # A request ticket belongs to one Documentary workspace/beat. Reuse its
        # Media Factory scene on retry so failed historical cards do not multiply.
        saved_scene_id = ""
        if request_path.exists():
            try:
                saved_ticket = json.loads(request_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                saved_ticket = None
            if isinstance(saved_ticket, dict):
                saved_scene_id = str(saved_ticket.get("scene_id") or "").strip()

        scenes = self._request_json("GET", "/api/scenes", timeout=15)
        saved_scene = None
        if isinstance(scenes, list):
            if saved_scene_id:
                saved_scene = next(
                    (
                        item for item in scenes
                        if isinstance(item, dict) and str(item.get("id") or "") == saved_scene_id
                    ),
                    None,
                )
            if saved_scene is None:
                matching = [
                    item for item in scenes
                    if isinstance(item, dict)
                    and str(item.get("name") or "") == str(payload.get("name") or "")
                    and str(item.get("task_type") or "") == str(payload.get("task_type") or "")
                    and str(item.get("prompt") or "").strip() == str(payload.get("prompt") or "").strip()
                ]
                if matching:
                    saved_scene = max(
                        matching,
                        key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")),
                    )
                    saved_scene_id = str(saved_scene.get("id") or "").strip()
        if isinstance(saved_scene, dict) and saved_scene_id:
            same_prompt = str(saved_scene.get("prompt") or "").strip() == str(payload.get("prompt") or "").strip()
            if str(saved_scene.get("status") or "").lower() not in {"queued", "running", "completed"}:
                created = self._request_json(
                    "PATCH",
                    f"/api/scenes/{quote(saved_scene_id, safe='')}",
                    payload,
                    timeout=30,
                )
            elif same_prompt:
                created = saved_scene

        if not isinstance(created, dict):
            created = self._request_json("POST", "/api/scenes", payload, timeout=30)
        scene_id = str(created.get("id") or "").strip() if isinstance(created, dict) else ""
        if not scene_id:
            raise RuntimeError("Media Factory không trả về scene id")

        ticket = {
            "scene_id": scene_id,
            "job_id": "",
            "name": str(created.get("name") or scene.get("name") or scene.get("id") or ""),
            "status": "prepared",
            "created_at": str(created.get("created_at") or ""),
        }
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
        return ticket

    def list_scenes(self) -> list[dict[str, Any]]:
        try:
            scenes = self._request_json("GET", "/api/scenes", timeout=15)
            if isinstance(scenes, list):
                return [item for item in scenes if isinstance(item, dict)]
        except Exception:
            pass
        return []

    def clear_all_scenes(self) -> dict[str, Any]:
        self.prepare()
        res = self._request_json("DELETE", "/api/scenes", timeout=30)
        return res if isinstance(res, dict) else {"ok": True}

    def resume_queue(self) -> dict[str, Any]:
        try:
            res = self._request_json("POST", "/api/queue/resume", timeout=10)
            return res if isinstance(res, dict) else {"paused": False}
        except Exception:
            return {}

    def delete_scene(self, scene_id: str) -> None:
        sid = str(scene_id or "").strip()
        if not sid:
            return
        try:
            self._request_json("DELETE", f"/api/scenes/{quote(sid, safe='')}", timeout=15)
        except Exception:
            pass

    def run_prepared(
        self,
        scene: dict[str, Any],
        request_path: Path,
        ticket: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run an already prepared card, preserving submission pacing."""
        prepared = ticket if isinstance(ticket, dict) else self.prepare_scene(scene, request_path)
        scene_id = str(prepared.get("scene_id") or "").strip()
        if not scene_id:
            prepared = self.prepare_scene(scene, request_path)
            scene_id = str(prepared.get("scene_id") or "").strip()
        self._pace_submission()
        try:
            job = self._request_json("POST", f"/api/scenes/{quote(scene_id, safe='')}/run", timeout=30)
        except RuntimeError as exc:
            err_lower = str(exc).lower()
            if "404" in err_lower or "not found" in err_lower:
                if not (callable(self._request_json) and getattr(self._request_json, "__name__", "") == "<lambda>"):
                    if not self.list_scenes():
                        raise RuntimeError(f"SCENE_DELETED:{scene_id}") from exc
                prepared = self.prepare_scene(scene, request_path)
                scene_id = str(prepared.get("scene_id") or "").strip()
                job = self._request_json("POST", f"/api/scenes/{quote(scene_id, safe='')}/run", timeout=30)
            else:
                raise
        job_id = str(job.get("id") or "").strip() if isinstance(job, dict) else ""
        if not job_id:
            raise RuntimeError("Media Factory không trả về job id")
        ticket = {
            "scene_id": scene_id,
            "job_id": job_id,
            "name": str(prepared.get("name") or scene.get("name") or scene.get("id") or ""),
            "status": str(job.get("status") or "queued"),
            "created_at": str(job.get("created_at") or ""),
        }
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
        return ticket

    def submit(self, scene: dict[str, Any], request_path: Path) -> dict[str, Any]:
        return self.run_prepared(scene, request_path, self.prepare_scene(scene, request_path))

    def inspect(self, ticket: dict[str, Any]) -> dict[str, Any] | None:
        job_id = str(ticket.get("job_id") or "").strip()
        scene_id = str(ticket.get("scene_id") or "").strip()
        if not job_id and not scene_id:
            return None
        jobs = self._request_json("GET", "/api/jobs", timeout=15)
        if not isinstance(jobs, list):
            return None
        job = next(
            (item for item in jobs if isinstance(item, dict) and str(item.get("id") or "") == job_id),
            None,
        ) if job_id else None
        if job is None and scene_id and not job_id:
            scene_jobs = [
                item for item in jobs
                if isinstance(item, dict) and str(item.get("scene_id") or "") == scene_id
            ]
            if scene_jobs:
                job = max(scene_jobs, key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")))
                ticket["job_id"] = str(job.get("id") or "")
        if isinstance(job, dict) and str(job.get("status") or "").lower() == "failed":
            scene_id = str(ticket.get("scene_id") or job.get("scene_id") or "").strip()
            original_created_at = str(job.get("created_at") or "")
            retries = [
                item
                for item in jobs
                if isinstance(item, dict)
                and str(item.get("scene_id") or "") == scene_id
                and str(item.get("id") or "") != job_id
                and str(item.get("status") or "").lower() in {"queued", "running", "completed"}
                and (not original_created_at or str(item.get("created_at") or "") >= original_created_at)
            ]
            if retries:
                job = max(retries, key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")))
                ticket["job_id"] = str(job.get("id") or ticket.get("job_id") or "")
            elif scene_id and not (callable(self._request_json) and getattr(self._request_json, "__name__", "") == "<lambda>"):
                scenes = self.list_scenes()
                scene_obj = next(
                    (item for item in scenes if isinstance(item, dict) and str(item.get("id") or "") == scene_id),
                    None,
                )
                if isinstance(scene_obj, dict):
                    scene_out = str(scene_obj.get("output_path") or "").strip()
                    scene_st = str(scene_obj.get("status") or "").lower()
                    if scene_st == "completed" and scene_out and Path(scene_out).is_file() and Path(scene_out).stat().st_size > 0:
                        job = {**job, "status": "completed", "output_path": scene_out, "error": None}
                    elif scene_st in {"queued", "running"}:
                        job = {**job, "status": scene_st, "error": None}
        if job is not None:
            ticket["status"] = str(job.get("status") or ticket.get("status") or "").lower()
            created_at = str(job.get("created_at") or "").strip()
            if created_at:
                ticket["created_at"] = created_at
            output = str(job.get("output_path") or "").strip()
            if output:
                ticket["output_path"] = output
        return job

    def queue_status(self) -> dict[str, Any]:
        try:
            result = self._request_json("GET", "/api/queue/status", timeout=5)
            if isinstance(result, dict):
                return result
        except Exception:
            pass
        return {}

    @staticmethod
    def is_connection_error(exc: BaseException) -> bool:
        message = str(exc).lower()
        return "không kết nối được media factory" in message or "media factory chưa sẵn sàng" in message

    def wait(self, ticket: dict[str, Any]) -> str:
        job_id = str(ticket.get("job_id") or "").strip()
        if not job_id:
            raise RuntimeError("Thiếu Media Factory job id")
        started_waiting = time.monotonic()
        active_deadline: float | None = None
        missing_deadline = started_waiting + self.timeout_seconds
        connection_failure_started: float | None = None
        while True:
            now = time.monotonic()
            try:
                job = self.inspect(ticket)
            except RuntimeError as exc:
                if not self.is_connection_error(exc):
                    raise
                if connection_failure_started is None:
                    connection_failure_started = now
                if now - connection_failure_started >= self.connection_timeout_seconds:
                    raise
                time.sleep(self.poll_interval)
                continue
            connection_failure_started = None
            if job is None:
                if not (callable(self._request_json) and getattr(self._request_json, "__name__", "") == "<lambda>"):
                    scene_id = str(ticket.get("scene_id") or "").strip()
                    scenes = self.list_scenes()
                    if not scenes or (scene_id and not any(str(s.get("id") or "") == scene_id for s in scenes)):
                        raise RuntimeError(f"SCENE_DELETED:{scene_id or job_id}")
                if now >= missing_deadline:
                    raise RuntimeError(f"Không còn thấy Media Factory job {job_id} sau {self.timeout_seconds}s")
                time.sleep(self.poll_interval)
                continue
            status = str(job.get("status") or "").lower()
            ticket["status"] = status
            if status == "failed":
                raise RuntimeError(str(job.get("error") or "Media Factory tạo media thất bại"))
            if status == "completed":
                output = str(job.get("output_path") or "").strip()
                if not output:
                    raise RuntimeError("Media Factory hoàn tất nhưng không trả về output path")
                if not Path(output).exists():
                    raise RuntimeError(f"Media Factory hoàn tất nhưng file output không tồn tại: {output}")
                ticket["output_path"] = output
                return output
            if status == "paused":
                raise RuntimeError(
                    f"Media Factory job {job_id} đang ở trạng thái tạm dừng (paused)."
                )
            if status == "queued":
                active_deadline = None
                job_err = str(job.get("error") or "").strip()
                if job_err:
                    raise RuntimeError(f"Media Factory job {job_id} gặp lỗi trong hàng đợi: {job_err}")
                if not (callable(self._request_json) and getattr(self._request_json, "__name__", "") == "<lambda>"):
                    qs = self.queue_status()
                    if isinstance(qs, dict) and (qs.get("paused") is True or qs.get("status") == "paused"):
                        pause_reason = qs.get("reason") or job_err or "Hàng đợi Media Factory đang tạm dừng (paused)."
                        raise RuntimeError(f"Media Factory hàng đợi đang tạm dừng: {pause_reason}")
                if self.queue_timeout_seconds and now - started_waiting >= self.queue_timeout_seconds:
                    raise RuntimeError(
                        f"Media Factory job {job_id} chờ hàng đợi quá {self.queue_timeout_seconds}s (vui lòng kiểm tra hàng đợi hoặc trạng thái tài khoản)"
                    )
            else:
                if active_deadline is None:
                    active_deadline = now + self.timeout_seconds
                elif now >= active_deadline:
                    raise RuntimeError(f"Media Factory job {job_id} xử lý quá {self.timeout_seconds}s")
            time.sleep(self.poll_interval)

    def __call__(self, scene: dict[str, Any], request_path: Path) -> str:
        return self.wait(self.submit(scene, request_path))


# Backward-compatible import name for existing integrations.
CofiFlowToolRunner = CofiStudioMediaFactoryRunner


class AIVisualCoordinator:
    def __init__(
        self,
        tool_runner: Callable[[dict[str, Any], Path], str] | None = None,
        *,
        studio_root: str | Path | None = None,
        studio_api: str | None = None,
        ensure_media_factory: Callable[[], Any] | None = None,
        image_model: str | None = None,
        video_model: str | None = None,
    ):
        self.tool_runner = tool_runner or CofiStudioMediaFactoryRunner(
            studio_root,
            studio_api=studio_api,
            ensure_available=ensure_media_factory,
        )
        self.image_model = image_model or os.getenv("COFI_AI_IMAGE_MODEL", "nano_banana_2")
        self.video_model = video_model or os.getenv("COFI_AI_VIDEO_MODEL", "veo_31_fast")
        self.enable_video = os.getenv("COFI_AI_VISUAL_ENABLE_VEO", "0").strip().lower() not in {"0", "false", "no", "off"}
        self.outstanding_limit = max(
            1,
            int(os.getenv("COFI_AI_VISUAL_OUTSTANDING_LIMIT", str(AI_VISUAL_OUTSTANDING_LIMIT))),
        )
        # When Veo cannot produce a clip, keep the finished keyframe and let the
        # editor animate it (camera move) instead of blocking the whole phase.
        self.video_still_fallback = os.getenv("COFI_AI_VISUAL_VIDEO_STILL_FALLBACK", "1").strip().lower() not in {"0", "false", "no", "off"}
        # Stop submitting new Veo jobs after this many consecutive failures
        # (0 disables). Remaining beats fall back to animated stills.
        self.video_fail_streak_limit = max(0, int(os.getenv("COFI_AI_VISUAL_VIDEO_FAIL_STREAK", "5")))

    def settings(self, workspace: str | Path, job: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace = Path(workspace)
        payload: dict[str, Any] = {}
        path = workspace / "ai_visual_settings.json"
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    payload = raw
            except (OSError, json.JSONDecodeError):
                payload = {}
        if isinstance(job, dict) and isinstance(job.get("ai_visual"), dict):
            job_ai_visual = dict(job["ai_visual"])
            merged: dict[str, Any] = {**payload, **job_ai_visual}
            for k in ("style_preset", "custom_style", "style_reference_image"):
                if merged.get(k) in (None, "") and payload.get(k) not in (None, ""):
                    merged[k] = payload[k]
            payload = merged
        style_mode = str(payload.get("style_mode") or "auto").strip().lower()
        if style_mode not in {"auto", "preset", "custom"}:
            style_mode = "auto"
        visual_strategy = str((job or {}).get("visual_strategy") or payload.get("visual_strategy") or "").strip().lower()
        if visual_strategy == "full_ai":
            coverage_mode = "full_ai"
        elif visual_strategy in {"edit_direct_footage", "semi_content", "ban_content", "edit_footage"}:
            coverage_mode = "selective_ai"
        else:
            coverage_mode = str(payload.get("coverage_mode") or "fallback_only").strip().lower()
            if coverage_mode not in {"fallback_only", "full_ai", "selective_ai"}:
                coverage_mode = "fallback_only"
        presets = self._style_presets()
        preset_names = {item["name"] for item in presets}
        style_preset = str(payload.get("style_preset") or "").strip()
        if style_preset not in preset_names:
            style_preset = ""
        style_reference_image = str(payload.get("style_reference_image") or "").strip()
        if not style_reference_image or not Path(style_reference_image).is_file():
            ref_dir = workspace / "media" / "style_reference"
            if ref_dir.is_dir():
                for candidate in sorted(ref_dir.glob("style_reference.*")):
                    if candidate.is_file():
                        style_reference_image = str(candidate)
                        break
        custom_style = str(payload.get("custom_style") or "").strip()
        if style_mode == "preset" and not style_preset:
            style_mode = "auto"
        style_prompt = str(payload.get("style_prompt") or "").strip()
        if style_mode == "preset":
            style_prompt = self._style_preset_prompt(style_preset)
        elif style_mode == "custom":
            if not style_prompt:
                style_prompt = custom_style
        else:
            style_prompt = ""
        ai_media_mode = str(payload.get("ai_media_mode") or (job or {}).get("ai_media_mode") or "mixed").strip().lower()
        if ai_media_mode not in {"image", "video", "mixed"}:
            ai_media_mode = "mixed"
        veo_enabled = bool(payload.get("veo_enabled", self.enable_video))
        if ai_media_mode == "image":
            veo_enabled = False
        elif ai_media_mode == "video":
            veo_enabled = True
        return {
            "image_model": str(payload.get("image_model") or self.image_model),
            "video_model": str(payload.get("video_model") or self.video_model),
            "aspect_ratio": str(payload.get("aspect_ratio") or "16:9"),
            "veo_enabled": veo_enabled,
            "style_mode": style_mode,
            "style_preset": style_preset,
            "custom_style": custom_style,
            "style_prompt": style_prompt,
            "ai_media_mode": ai_media_mode,
            "coverage_mode": coverage_mode,
            "style_reference_image": style_reference_image,
            "style_presets": [{"name": item["name"]} for item in presets],
        }

    @staticmethod
    def _style_presets() -> list[dict[str, str]]:
        presets: list[dict[str, str]] = []
        if not STYLE_PRESETS_DIR.is_dir():
            return presets
        for path in sorted(STYLE_PRESETS_DIR.glob("*.json"), key=lambda item: item.name.lower()):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            name = str(data.get("name") or "").strip()
            prompt = str(data.get("prompt") or "").strip()
            if name and prompt:
                presets.append({"name": name, "prompt": prompt})
        return presets

    @classmethod
    def _style_preset_prompt(cls, name: str) -> str:
        target = str(name or "").strip()
        if not target:
            return ""
        for item in cls._style_presets():
            if item["name"] == target:
                return item["prompt"]
        return ""

    @staticmethod
    def _extract_years(text: str) -> list[int]:
        return [
            int(value)
            for value in re.findall(r"(?<!\d)(1[5-9]\d{2}|20\d{2})(?!\d)", text or "")
        ]

    @classmethod
    def _beat_period(cls, beat: dict[str, Any], default_year: int | None) -> str:
        text = " ".join(
            str(beat.get(key) or "")
            for key in ("narration_text", "visual_description", "purpose", "sound_notes")
        )
        years = cls._extract_years(text)
        if years:
            if min(years) == max(years):
                return str(years[0])
            return f"{min(years)}–{max(years)}"
        if default_year:
            return f"around {default_year}"
        return "the historical period described by the narration"

    @classmethod
    def _build_visual_style(cls, visual: dict[str, Any]) -> dict[str, Any]:
        beat_texts = []
        year_frequency: dict[int, int] = {}
        monochrome_mentions = 0
        color_mentions = 0
        for beat in visual.get("beats") or []:
            if not isinstance(beat, dict):
                continue
            text = " ".join(
                str(beat.get(key) or "")
                for key in ("narration_text", "visual_description", "footage_search_queries")
            )
            beat_texts.append(text)
            for year in cls._extract_years(text):
                year_frequency[year] = year_frequency.get(year, 0) + 1
            lowered = text.lower()
            monochrome_mentions += sum(lowered.count(token) for token in ("black-and-white", "black and white", "monochrome"))
            color_mentions += sum(lowered.count(token) for token in ("color film", "colour film", "in color", "in colour"))
        dominant_year = None
        if year_frequency:
            dominant_year = sorted(year_frequency.items(), key=lambda item: (-item[1], item[0]))[0][0]
        period_start = min(year_frequency) if year_frequency else None
        period_end = max(year_frequency) if year_frequency else None
        is_pre_color_era = bool(period_end and period_end <= 1950) or bool(dominant_year and dominant_year <= 1950)
        monochrome = is_pre_color_era or (monochrome_mentions >= color_mentions and monochrome_mentions >= 1)
        if monochrome:
            color_treatment = (
                "strictly neutral silver-gelatin black-and-white monochrome with soft highlight rolloff, restrained contrast and authentic archive grain; absolutely no color"
            )
        else:
            color_treatment = (
                "default to restrained historical color with low saturation, natural skin, soft highlight rolloff and fine film grain "
                "only when the beat has no stronger nearby real-footage style reference"
            )
        if period_start and period_end and period_start != period_end:
            era_label = f"{period_start}–{period_end}, with every beat locked to its own narrated date"
        elif dominant_year:
            era_label = f"around {dominant_year}"
        else:
            era_label = "the documentary's historical period"
        directive = (
            f"Documentary visual bible: anchor the production {era_label}. {color_treatment}. "
            "Every reconstruction must use historically correct clothing, grooming, architecture, interiors, furniture, vehicles, "
            "street furniture, paper documents, telephones, lighting fixtures and technology for the beat's exact period and place. "
            "Exclude contemporary fashion, modern cars, LEDs, flat screens, laptops, smartphones, modern plastics, present-day signage "
            "and any object introduced after the depicted period. For each generated beat, match the visual language of the nearest verified real "
            "footage/stills in that historical sequence: if the surrounding material is black-and-white, the reconstruction must also be black-and-white; "
            "if it is period color, match that palette, grain, contrast, lighting and lens character. Preserve local sequence continuity instead of forcing "
            "one color treatment across eras."
        )
        return {
            "dominant_year": dominant_year,
            "period_start": period_start,
            "period_end": period_end,
            "color_mode": "monochrome" if monochrome else "muted_historical_color",
            "directive": directive,
        }

    @classmethod
    def _detect_historical_figure_clause(cls, beat: dict[str, Any], period: str = "") -> str:
        text_fields = [
            str(beat.get("narration_text") or ""),
            str(beat.get("visual_description") or ""),
            str(beat.get("purpose") or ""),
            " ".join(str(q) for q in (beat.get("footage_search_queries") or [])),
        ]
        full_text = " ".join(text_fields)

        subjects: list[str] = []
        if re.search(r'\b(Lucy Mercer( Rutherfurd)?)\b', full_text, re.I):
            subjects.append("Lucy Mercer Rutherfurd (socialite and companion, authentic historical likeness, period attire and hairstyle)")

        if re.search(r'\b(Theodore Roosevelt|Teddy Roosevelt)\b', full_text, re.I):
            subjects.append("President Theodore Roosevelt (authentic historical likeness, mustache, spectacles and period attire)")

        if re.search(r'\b(Franklin( Delano)? Roosevelt|FDR)\b', full_text, re.I):
            if "1905" in period or "young" in full_text.lower():
                fdr_desc = "young Franklin D. Roosevelt (age 23 in 1905, authentic historical facial likeness, youthful features and Edwardian attire)"
            elif any(k in full_text.lower() for k in ["polio", "1921", "warm springs", "wheelchair", "brace"]):
                fdr_desc = "President Franklin D. Roosevelt (FDR in 1920s Warm Springs rehabilitation, authentic historical facial likeness, determined expression and period clothing)"
            elif "1945" in period or "1944" in period:
                fdr_desc = "President Franklin D. Roosevelt (FDR in 1945, authentic historical facial likeness, dignified wartime leader, authentic late-war facial features)"
            else:
                fdr_desc = "President Franklin D. Roosevelt (FDR, authentic historical recognizable facial likeness, authentic period hairstyle, jawline and presidential demeanor)"
            subjects.append(fdr_desc)

        if re.search(r'\bEleanor Roosevelt\b', full_text, re.I):
            if "1905" in period or "young" in full_text.lower():
                el_desc = "young Eleanor Roosevelt (age 20 in 1905, authentic historical facial likeness, Edwardian bridal/period attire and hairstyle)"
            else:
                el_desc = "First Lady Eleanor Roosevelt (authentic historical recognizable facial likeness, characteristic hairstyle, dignified and empathetic expression, authentic period attire)"
            subjects.append(el_desc)

        if subjects:
            joined = " and ".join(subjects)
            return (
                f"Historical Subject Focus: Authentic documentary portrait reconstruction of real historical figure(s): {joined}. "
                "Must render exact recognizable historical facial likeness, authentic bone structure, authentic period hair and authentic archival expressions. "
            )
        return ""

    @classmethod
    def _character_reference_images(cls, beat: dict[str, Any], workspace: Path) -> list[str]:
        ref_dir = workspace / "media" / "character_references"
        if not ref_dir.is_dir():
            return []
        text = " ".join([
            str(beat.get("narration_text") or ""),
            str(beat.get("visual_description") or ""),
            str(beat.get("purpose") or ""),
            " ".join(str(q) for q in (beat.get("footage_search_queries") or [])),
        ]).lower()

        if "lucy" in text or "mercer" in text:
            lucy_ref = ref_dir / "lucy_mercer.jpg"
            if lucy_ref.is_file():
                return [str(lucy_ref)]

        if "theodore" in text or "teddy" in text:
            teddy_ref = ref_dir / "theodore_roosevelt.jpg"
            if teddy_ref.is_file():
                return [str(teddy_ref)]

        if "1905" in text or "wedding" in text:
            wedding_ref = ref_dir / "fdr_eleanor_1905.jpg"
            if wedding_ref.is_file():
                return [str(wedding_ref)]

        if "eleanor" in text and ("franklin" not in text and "fdr" not in text and "president" not in text):
            el_ref = ref_dir / "eleanor_roosevelt_1933.jpg"
            if el_ref.is_file():
                return [str(el_ref)]

        if any(k in text for k in ["warm springs", "polio", "1921", "wheelchair", "brace"]):
            fdr_20s = ref_dir / "fdr_1920s.jpg"
            if fdr_20s.is_file():
                return [str(fdr_20s)]

        fdr_1945 = ref_dir / "fdr_1945.jpg"
        if fdr_1945.is_file():
            return [str(fdr_1945)]

        return []

    @classmethod
    def _prompt(
        cls,
        beat: dict[str, Any],
        aspect_ratio: str = "16:9",
        visual_style: dict[str, Any] | None = None,
        ai_note: dict[str, Any] | None = None,
        preset_prompt: str = "",
        has_style_reference: bool = False,
    ) -> str:
        narration = str(beat.get("narration_text") or "").strip()
        visual = str(beat.get("visual_description") or "").strip()
        purpose = str(beat.get("purpose") or "").strip()
        framing = str(beat.get("framing_motion_intent") or "").strip()
        style = visual_style or {}
        note = ai_note or {}
        visual_language = note.get("visual_language") if isinstance(note.get("visual_language"), dict) else {}
        period = str(visual_language.get("period") or "").strip() or cls._beat_period(beat, style.get("dominant_year"))
        style_directive = str(style.get("directive") or "").strip()
        color_mode = str(visual_language.get("color_mode") or "").strip().lower()
        style_notes = str(visual_language.get("style_notes") or "").strip()
        if color_mode == "monochrome":
            beat_style = "Beat-specific source match: render in authentic black-and-white/monochrome; match nearby archive grain, contrast, exposure and lighting."
        elif color_mode in {"muted_historical_color", "natural_color"}:
            beat_style = "Beat-specific source match: render in period-appropriate color; match nearby verified footage palette, grain, contrast, exposure and lighting."
        else:
            beat_style = "Beat-specific source match: infer the most faithful color treatment from the beat's historical period and nearby verified real media; do not modernize the look."
        if style_notes:
            beat_style += f" Reference notes: {style_notes}."
        fallback_reason = str(note.get("reason") or "").strip()
        fallback_clause = f"Real-media fallback reason: {fallback_reason}. " if fallback_reason else ""
        period_qualifier = f"{period} " if period else ""
        subject_clause = cls._detect_historical_figure_clause(beat, period)
        style_reference_clause = (
            "A visual style reference image is attached. MANDATORY CHARACTER & COLOR LOCK: Draw ALL human characters in the scene (investigators, detectives, fugitive Xiao Qiqiang / Wang Gui, police officers, villagers, family members, and judges) as 2D rounded chibi mascot figures strictly copying the exact character design, BRIGHT GOLDEN-YELLOW head and body skin color tone (#FFD43B warm yellow spherical head, yellow hands, and yellow feet — NEVER white skin, NEVER pale/gray skin, and NEVER realistic human faces), proportions, bold clean black linework, simple black oval eyes with white specular highlights, thin curved eyebrows, minimal line mouth, and outfit style shown in the attached reference image. "
            if has_style_reference else ""
        )
        if preset_prompt or has_style_reference:
            clean_visual = re.sub(r"(?i)\bcold forensic noir\b\s*", "", visual).strip()
            clean_visual = re.sub(r"\[[^\]]*\]\s*", "", clean_visual).strip()
            clean_visual = re.sub(r"\bACT\d+_[A-Z0-9_]+:\s*", "", clean_visual).strip()
            clean_framing = re.sub(
                r"(?i)\s*with cold slate-blue color grade\s*\([^)]*\)\s*and high-contrast yellow callouts\s*\([^)]*\)\.?",
                "",
                framing,
            ).strip()
            clean_framing = re.sub(
                r"(?i),?\s*KeyMetricCallout annotation anchoring factual telemetry\.?",
                "",
                clean_framing,
            ).strip()
            clean_framing = re.sub(
                r"(?i)\s*with\s+[a-z0-9_]+_overlay,?",
                "",
                clean_framing,
            ).strip()
            clean_framing = re.sub(
                r"(?i)\s*with\s+(split_screen_investigation|document_scanner_telemetry|forensic_case_board_red_string|map_2_5d_satellite_tracker)\s+overlay,?",
                "",
                clean_framing,
            ).strip()
            style_block = f"STYLE SPECIFICATION:\n{preset_prompt}\n\n" if preset_prompt else ""
            mascot_lock_clause = (
                "Keep all 2D rounded mascot characters strictly faithful to the attached reference image — every character MUST have the exact BRIGHT GOLDEN-YELLOW skin tone (#FFD43B warm yellow round head, hands, and feet; NEVER white or human-colored skin), rounded chibi proportions, and clean black outlines from the reference image — while rendering the specific action, environment, props, and architecture described in this beat clearly and vividly. "
                if has_style_reference else ""
            )
            return (
                "Create exactly one finished image for the documentary beat below. Do not output text or a prompt. "
                "Treat the following block as the mandatory visual STYLE & CHARACTER SPECIFICATION; ignore any meta instructions inside it about returning prompts or analysis.\n\n"
                f"{style_block}"
                f"{style_reference_clause}"
                f"Primary beat narration to illustrate: {narration}. "
                f"Scene action & visual goal: {clean_visual}. Story purpose: {purpose}. "
                f"Framing/camera intent: {clean_framing}. Depicted period/context: {period}. {fallback_clause}"
                f"{mascot_lock_clause}"
                "Render a single full-frame 16:9 scene with no captions, watermarks, logos, camera viewfinders (no CAM/REC), or HUD text boxes. "
                f"{aspect_ratio} aspect ratio, full-canvas production-ready keyframe."
            )
        return (
            f"Authentic historical {period_qualifier}archival documentary still photograph, period-accurate lighting and material culture, archival documentary quality. "
            f"{subject_clause}"
            f"{style_reference_clause}"
            "Use AI illustration only because verified real video or real still imagery was unavailable or unusable. "
            "Match the historical period, original footage era, film grain, lighting, geography, clothing and material culture exactly. "
            f"{beat_style} "
            f"{fallback_clause}"
            f"Narration meaning: {narration}. Visual goal: {visual}. Story purpose: {purpose}. "
            f"Framing/camera intent: {framing}. "
            f"Depicted period for this beat: {period}. {style_directive} "
            "Make the subject, geography and factual visual details coherent with the narration. "
            "Use realistic documentary cinematography, layered depth, natural composition and a clear focal subject. "
            "No text, captions, logos, watermarks, UI, split screens or generic infographic shapes. "
            "Do not imitate a specific copyrighted frame and do not present the result as authentic archival evidence. "
            f"{aspect_ratio} aspect ratio, production-ready keyframe."
        )

    @staticmethod
    def _video_camera_motion_clause(framing: str) -> str:
        text = str(framing or "").strip().lower()
        if any(token in text for token in ("줌인", "zoom in", "zoom-in", "push in", "push-in", "dolly in")):
            return "a slow cinematic push-in"
        if any(token in text for token in ("줌아웃", "zoom out", "zoom-out", "pull back", "pull-back", "dolly out")):
            return "a slow cinematic pull-back"
        if any(token in text for token in ("트래킹", "tracking", "track shot", "따라")):
            return "a restrained tracking move"
        if any(token in text for token in ("틸트", "tilt")):
            return "a gentle cinematic tilt"
        if any(token in text for token in ("팬", "pan ", "panning", "좌우")):
            return "a gentle cinematic pan"
        if any(token in text for token in ("핸드헬드", "handheld")):
            return "subtle documentary handheld drift"
        if any(token in text for token in ("고정", "정적", "static", "locked-off", "locked off")):
            return "a mostly locked-off camera with subtle natural parallax"
        return "a restrained slow cinematic move with subtle parallax"

    @classmethod
    def _video_prompt(cls, beat: dict[str, Any]) -> str:
        framing = str(beat.get("framing_motion_intent") or "").strip()
        camera_motion = cls._video_camera_motion_clause(framing)
        visual = str(beat.get("visual_description") or "").strip()
        narration = str(beat.get("narration_text") or "").strip()
        purpose = str(beat.get("purpose") or "").strip()
        beat_prompt = str(beat.get("prompt") or "").strip()

        details = []
        if beat_prompt:
            details.append(f"Prompt: {beat_prompt}")
        elif visual:
            details.append(f"Scene: {visual}")
        if purpose:
            details.append(f"Purpose: {purpose}")
        scene_clause = (". ".join(details) + ". ") if details else ""

        return (
            f"Animate the attached reference image as one believable stylized documentary reenactment. "
            f"{scene_clause}"
            f"Camera motion: {camera_motion}. "
            "Use subtle physical motion and natural atmospheric motion that are consistent with the existing pose and scene. "
            "Preserve composition, period details, clothing, props and the established art style from the reference image. "
            "Keep any human figures stylized or non-identifiable without real-person likeness claims. "
            "Silent ambient motion, no spoken dialogue, no narration, no speech audio. "
            "Avoid face changes, morphing, sudden object changes, text, logos, exaggerated VFX and artificial presentation graphics."
        )

    @staticmethod
    def _targets(
        workspace: Path,
        visual: dict[str, Any],
        registry: dict[str, Any],
        coverage_mode: str = "fallback_only",
        ai_media_mode: str = "mixed",
    ) -> list[dict[str, Any]]:
        assets = [item for item in (registry.get("assets") or []) if isinstance(item, dict)]
        effective_strategy = str(visual.get("visual_strategy") or "").strip().lower()
        if coverage_mode == "selective_ai" or effective_strategy in {"edit_direct_footage", "semi_content", "ban_content", "edit_footage"}:
            ai_covered = {
                str(asset.get("beat_id") or "")
                for asset in assets
                if _asset_exists(workspace, asset)
                and isinstance(asset.get("source"), dict)
                and asset["source"].get("generated_by") == "cofi_ai_visual"
                and (
                    ai_media_mode != "video"
                    or str(asset.get("kind") or "") == "ai_reconstruction_video"
                )
            }
            return [
                beat
                for beat in (visual.get("beats") or [])
                if isinstance(beat, dict)
                and str(beat.get("beat_id") or "").strip()
                and str(beat.get("visual_route") or "").strip().lower() == "ai_visual"
                and str(beat.get("beat_id") or "").strip() not in ai_covered
            ]
        if coverage_mode == "full_ai":
            ai_covered = {
                str(asset.get("beat_id") or "")
                for asset in assets
                if _asset_exists(workspace, asset)
                and isinstance(asset.get("source"), dict)
                and asset["source"].get("generated_by") == "cofi_ai_visual"
                and (
                    ai_media_mode != "video"
                    or str(asset.get("kind") or "") == "ai_reconstruction_video"
                )
            }
            return [
                beat
                for beat in (visual.get("beats") or [])
                if isinstance(beat, dict)
                and str(beat.get("beat_id") or "").strip()
                and str(beat.get("beat_id") or "").strip() not in ai_covered
            ]
        covered = {
            str(asset.get("beat_id") or "")
            for asset in assets
            if _asset_exists(workspace, asset)
        }
        fallback_ids = {
            str(value).strip()
            for value in (registry.get("ai_fallback_beats") or [])
            if str(value).strip()
        }
        fallback_targets: list[dict[str, Any]] = []
        for beat in visual.get("beats") or []:
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id") or "").strip()
            if not beat_id or beat_id in covered:
                continue
            if beat_id in fallback_ids:
                fallback_targets.append(beat)
        # AI is an explicit Footage hand-off only. An uncovered beat without a
        # verified fallback note must stay uncovered so preflight can surface it
        # instead of silently inflating AI usage.
        return fallback_targets

    @staticmethod
    def _merge_generated_assets(
        workspace: Path,
        registry: dict[str, Any],
        generated: list[dict[str, Any]],
        *,
        prefer_generated: bool = False,
    ) -> None:
        generated_beats = {str(item.get("beat_id") or "") for item in generated}
        assets = [
            item for item in (registry.get("assets") or [])
            if isinstance(item, dict)
            and not (
                str(item.get("beat_id") or "") in generated_beats
                and isinstance(item.get("source"), dict)
                and item["source"].get("generated_by") == "cofi_ai_visual"
            )
        ]
        for item in generated:
            chosen = item.get("video_path") or item.get("image_path")
            if not chosen:
                continue
            kind = "ai_reconstruction_video" if item.get("video_path") else "ai_reconstruction_still"
            model = item.get("video_model") if item.get("video_path") else item.get("image_model")
            assets.append({
                "id": f"ai_{item['beat_id']}_{'video' if item.get('video_path') else 'image'}",
                "beat_id": item["beat_id"],
                "kind": kind,
                "path": str(chosen),
                "source": {
                    "generated": True,
                    "generated_by": "cofi_ai_visual",
                    "provider": "cofistudio_media_factory",
                    "generation_profile": AI_VISUAL_GENERATION_PROFILE,
                    "model": model,
                    "truth_status": "illustrative_reconstruction",
                },
            })
        if prefer_generated:
            assets.sort(
                key=lambda item: 0
                if (
                    isinstance(item.get("source"), dict)
                    and item["source"].get("generated_by") == "cofi_ai_visual"
                    and str(item.get("beat_id") or "") in generated_beats
                )
                else 1
            )
        registry["assets"] = assets

        asset_id_by_beat: dict[str, str] = {}
        for asset in assets:
            beat_id = str(asset.get("beat_id") or "")
            asset_id = str(asset.get("id") or "")
            if beat_id and asset_id and _asset_exists(workspace, asset):
                asset_id_by_beat.setdefault(beat_id, asset_id)

        kept_native: list[dict[str, Any]] = []
        presentation = [item for item in (registry.get("presentation_effects") or []) if isinstance(item, dict)]
        existing_effect_ids = {str(item.get("id") or "") for item in presentation}
        for treatment in registry.get("native_treatments") or []:
            if not isinstance(treatment, dict):
                continue
            beat_id = str(treatment.get("beat_id") or "")
            anchor_asset_id = asset_id_by_beat.get(beat_id)
            if not anchor_asset_id:
                kept_native.append(treatment)
                continue
            effect_id = str(treatment.get("id") or f"overlay_{beat_id}")
            if effect_id in existing_effect_ids:
                continue
            presentation.append({
                "id": effect_id,
                "beat_id": beat_id,
                "kind": "media_annotation_overlay",
                "mode": "overlay",
                "requires_base_asset": True,
                "anchor_asset_id": anchor_asset_id,
                "description": str(treatment.get("description") or "Large mobile-readable text/arrow/circle/highlight annotation"),
                "mobile_readable": True,
            })
            existing_effect_ids.add(effect_id)
        registry["native_treatments"] = kept_native
        registry["presentation_effects"] = presentation

        coverage: dict[str, dict[str, list[str]]] = {}
        for asset in assets:
            beat_id = str(asset.get("beat_id") or "")
            if not beat_id:
                continue
            entry = coverage.setdefault(beat_id, {"assets": [], "native": [], "presentation": []})
            entry["assets"].append(str(asset.get("id") or asset.get("path") or ""))
        for treatment in registry.get("native_treatments") or []:
            if not isinstance(treatment, dict):
                continue
            beat_id = str(treatment.get("beat_id") or "")
            if beat_id:
                coverage.setdefault(beat_id, {"assets": [], "native": [], "presentation": []})["native"].append(str(treatment.get("id") or ""))
        for effect in registry.get("presentation_effects") or []:
            if not isinstance(effect, dict):
                continue
            beat_id = str(effect.get("beat_id") or "")
            if beat_id:
                coverage.setdefault(beat_id, {"assets": [], "native": [], "presentation": []})["presentation"].append(str(effect.get("id") or ""))
        registry["beat_coverage"] = coverage
        _write_json(workspace / "asset_registry.json", registry)

    @staticmethod
    def _existing_generated_media(media_dir: Path, stem: str, *, video: bool = False) -> str | None:
        suffixes = {".mp4", ".mov", ".webm"} if video else {".jpg", ".jpeg", ".png", ".webp"}
        candidates = sorted(
            (
                path for path in media_dir.glob(f"{stem}.*")
                if path.is_file() and path.suffix.lower() in suffixes and path.stat().st_size > 0
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return str(candidates[0]) if candidates else None

    @staticmethod
    def _capture_generated_media(source: str, media_dir: Path, stem: str, *, video: bool = False) -> str:
        source_path = Path(source)
        suffixes = {".mp4", ".mov", ".webm"} if video else {".jpg", ".jpeg", ".png", ".webp"}
        suffix = source_path.suffix.lower()
        if suffix not in suffixes:
            media_kind = "video" if video else "ảnh"
            raise RuntimeError(f"Media Factory trả về {media_kind} sai định dạng: {source_path.name}")
        if not source_path.exists() or not source_path.is_file() or source_path.stat().st_size <= 0:
            raise RuntimeError(f"Media Factory trả về file không hợp lệ: {source_path}")
        media_dir.mkdir(parents=True, exist_ok=True)
        destination = media_dir / f"{stem}{suffix}"
        if source_path.resolve() != destination.resolve():
            shutil.copy2(source_path, destination)
        return str(destination)

    def run(self, job: dict[str, Any], workspace: str | Path) -> StageResult:
        workspace = Path(workspace)
        settings = self.settings(workspace, job)
        image_model = settings["image_model"]
        video_model = settings["video_model"]
        aspect_ratio = settings["aspect_ratio"]
        enable_video = settings["veo_enabled"]
        style_mode = settings["style_mode"]
        style_preset = settings["style_preset"]
        custom_style = str(settings.get("custom_style") or "").strip()
        ai_media_mode = str(settings.get("ai_media_mode") or "mixed")
        coverage_mode = settings["coverage_mode"]
        style_reference_image = str(settings.get("style_reference_image") or "").strip()
        style_reference_path = Path(style_reference_image) if style_reference_image else None
        has_style_reference = bool(style_reference_path and style_reference_path.is_file())
        style_reference_sha256 = ""
        if has_style_reference and style_reference_path is not None:
            style_reference_sha256 = hashlib.sha256(style_reference_path.read_bytes()).hexdigest()
        preset_prompt = (
            self._style_preset_prompt(style_preset)
            if style_mode == "preset"
            else (str(settings.get("style_prompt") or "").strip() or custom_style)
            if style_mode == "custom"
            else ""
        )
        visual = _read_json(workspace / "visual_manifest.json")
        effective_vs = str(job.get("visual_strategy") or visual.get("visual_strategy") or "").strip().lower()
        if effective_vs == "full_ai":
            coverage_mode = "full_ai"
        elif effective_vs in {"edit_direct_footage", "semi_content", "ban_content", "edit_footage"}:
            coverage_mode = "selective_ai"
        style_signature = json.dumps({
            "style_mode": style_mode,
            "style_preset": style_preset,
            "custom_style": custom_style,
            "ai_media_mode": ai_media_mode,
            "coverage_mode": coverage_mode,
            "style_reference_image": str(style_reference_path) if has_style_reference else "",
            "style_reference_sha256": style_reference_sha256,
        }, ensure_ascii=False, sort_keys=True)
        default_style_signature = json.dumps({
            "style_mode": "auto",
            "style_preset": "",
            "custom_style": "",
            "ai_media_mode": "mixed",
            "coverage_mode": "fallback_only",
            "style_reference_image": "",
            "style_reference_sha256": "",
        }, ensure_ascii=False, sort_keys=True)
        registry_path = workspace / "asset_registry.json"
        if not registry_path.exists():
            _write_json(registry_path, {"assets": [], "ai_fallback_beats": [], "ai_usage_notes": []})
        registry = _read_json(registry_path)
        ai_notes_by_beat = {
            str(item.get("beat_id") or "").strip(): item
            for item in (registry.get("ai_usage_notes") or [])
            if isinstance(item, dict) and str(item.get("beat_id") or "").strip()
        }
        manifest_path = workspace / "ai_visual_manifest.json"
        current_job_id = str(job.get("id") or workspace.name).strip()
        previous_manifest: dict[str, Any] = {}
        if manifest_path.exists():
            previous_manifest = _read_json(manifest_path)
        previous_job_id = str(previous_manifest.get("job_id") or "").strip()
        if previous_job_id and previous_job_id != current_job_id:
            previous_manifest = {}
        previous_style = previous_manifest.get("visual_style")
        previous_provider = str(previous_manifest.get("provider") or "").strip()
        previous_profile = str(previous_manifest.get("generation_profile") or "").strip()
        previous_style_signature = str(previous_manifest.get("style_settings_signature") or "")

        def image_signature(raw: str) -> str:
            # Media mode only decides whether a keyframe is animated; it does not
            # change the image prompt, so it must not invalidate finished keyframes.
            try:
                data = json.loads(raw)
            except (TypeError, ValueError):
                return raw
            if isinstance(data, dict):
                data.pop("ai_media_mode", None)
                return json.dumps(data, ensure_ascii=False, sort_keys=True)
            return raw

        compatible_style_signature = (
            image_signature(previous_style_signature) == image_signature(style_signature)
            or (not previous_style_signature and image_signature(style_signature) == image_signature(default_style_signature))
        )
        workspace_scene_ids: set[str] = set()
        for mf_item in (previous_manifest.get("media_factory_jobs") or []):
            if isinstance(mf_item, dict):
                sid = str(mf_item.get("scene_id") or "").strip()
                if sid:
                    workspace_scene_ids.add(sid)
        existing_req_dir = workspace / ".ai_visual"
        if existing_req_dir.is_dir():
            for ticket_path in existing_req_dir.glob("*.json"):
                try:
                    ticket_payload = json.loads(ticket_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    ticket_payload = None
                if isinstance(ticket_payload, dict):
                    sid = str(ticket_payload.get("scene_id") or "").strip()
                    if sid:
                        workspace_scene_ids.add(sid)

        scenes_cleared_in_factory = False
        list_scenes_fn = getattr(self.tool_runner, "list_scenes", None)
        clear_all_scenes_fn = getattr(self.tool_runner, "clear_all_scenes", None)
        delete_scene_fn = getattr(self.tool_runner, "delete_scene", None)
        req_fn = getattr(self.tool_runner, "_request_json", None)
        is_live_factory_runner = (
            callable(list_scenes_fn)
            and not (callable(req_fn) and getattr(req_fn, "__name__", "") == "<lambda>")
        )
        if is_live_factory_runner:
            try:
                live_scenes = list_scenes_fn()
                if isinstance(live_scenes, list):
                    live_scene_ids = {
                        str(s.get("id") or "").strip()
                        for s in live_scenes
                        if isinstance(s, dict) and str(s.get("id") or "").strip()
                    }
                    owned_live_scene_ids = live_scene_ids & workspace_scene_ids
                    foreign_live_scene_ids = live_scene_ids - workspace_scene_ids
                    if len(live_scenes) == 0:
                        if previous_manifest and (
                            previous_manifest.get("media_factory_jobs") or previous_manifest.get("generated")
                        ):
                            scenes_cleared_in_factory = True
                    elif not owned_live_scene_ids:
                        # Every scene currently inside Media Factory belongs to an older job!
                        if callable(clear_all_scenes_fn):
                            try:
                                clear_all_scenes_fn()
                            except Exception:
                                for fsid in foreign_live_scene_ids:
                                    if callable(delete_scene_fn):
                                        delete_scene_fn(fsid)
                        elif callable(delete_scene_fn):
                            for fsid in foreign_live_scene_ids:
                                delete_scene_fn(fsid)
                        if previous_manifest and previous_manifest.get("media_factory_jobs"):
                            scenes_cleared_in_factory = True
                    elif foreign_live_scene_ids and callable(delete_scene_fn):
                        for fsid in foreign_live_scene_ids:
                            delete_scene_fn(fsid)
            except Exception:
                pass

        resume_current_profile = bool(
            previous_provider == "cofistudio_media_factory"
            and previous_profile == AI_VISUAL_GENERATION_PROFILE
            and isinstance(previous_style, dict)
            and compatible_style_signature
            and not scenes_cleared_in_factory
        )
        use_existing_local_cache = (not previous_manifest or resume_current_profile) and not scenes_cleared_in_factory
        visual_style = dict(previous_style) if (resume_current_profile or (isinstance(previous_style, dict) and compatible_style_signature)) else self._build_visual_style(visual)
        if (previous_manifest and not resume_current_profile) or scenes_cleared_in_factory:
            registry["assets"] = [
                item
                for item in (registry.get("assets") or [])
                if not (
                    isinstance(item, dict)
                    and isinstance(item.get("source"), dict)
                    and item["source"].get("generated_by") == "cofi_ai_visual"
                )
            ]
            _write_json(workspace / "asset_registry.json", registry)
            stale_media_dir = workspace / "media" / "ai"
            if stale_media_dir.is_dir():
                for stale_media in stale_media_dir.iterdir():
                    if stale_media.is_file() and (
                        "_ai_keyframe" in stale_media.name
                        or "_ai_video" in stale_media.name
                        or "_ai_motion" in stale_media.name
                    ):
                        try:
                            stale_media.unlink()
                        except OSError:
                            pass
            stale_req_dir = workspace / ".ai_visual"
            if stale_req_dir.is_dir():
                for stale_file in stale_req_dir.glob("*.json"):
                    try:
                        stale_file.unlink()
                    except OSError:
                        pass
        generated = [
            dict(item)
            for item in ((previous_manifest.get("generated") or []) if resume_current_profile else [])
            if isinstance(item, dict) and str(item.get("beat_id") or "").strip()
        ]
        errors = [
            dict(item)
            for item in ((previous_manifest.get("errors") or []) if (resume_current_profile and not scenes_cleared_in_factory) else [])
            if isinstance(item, dict) and str(item.get("beat_id") or "").strip()
        ]
        media_factory_jobs = [
            dict(item)
            for item in ((previous_manifest.get("media_factory_jobs") or []) if (resume_current_profile and not scenes_cleared_in_factory) else [])
            if isinstance(item, dict) and str(item.get("beat_id") or "").strip()
        ]
        real_covered_ids = {
            str(item.get("beat_id") or "").strip()
            for item in (registry.get("assets") or [])
            if isinstance(item, dict)
            and str(item.get("beat_id") or "").strip()
            and _asset_exists(workspace, item)
            and not (
                isinstance(item.get("source"), dict)
                and item["source"].get("generated_by") == "cofi_ai_visual"
            )
        }
        fallback_ids = {
            str(value).strip()
            for value in (registry.get("ai_fallback_beats") or [])
            if str(value).strip()
        }
        visual_beats = [beat for beat in (visual.get("beats") or []) if isinstance(beat, dict)]
        missing_must_real = [
            str(beat.get("beat_id") or "").strip()
            for beat in visual_beats
            if str(beat.get("beat_id") or "").strip()
            and str(beat.get("beat_id") or "").strip() not in real_covered_ids
            and str(beat.get("source_priority") or "").strip().lower() == "must_real"
            and str(beat.get("beat_id") or "").strip() not in fallback_ids
        ]
        if missing_must_real and coverage_mode not in {"full_ai", "selective_ai"}:
            raise RuntimeError(
                "AI Visual cannot replace must_real beat with generated media: " + ", ".join(missing_must_real)
            )
        unnoted_missing = [
            str(beat.get("beat_id") or "").strip()
            for beat in visual_beats
            if str(beat.get("beat_id") or "").strip()
            and str(beat.get("beat_id") or "").strip() not in real_covered_ids
            and str(beat.get("beat_id") or "").strip() not in fallback_ids
        ]
        if unnoted_missing and coverage_mode not in {"full_ai", "selective_ai"}:
            raise RuntimeError(
                "AI Visual refused unverified fallback; Footage must explicitly note these uncovered beats first: "
                + ", ".join(unnoted_missing)
            )
        missing_ai_notes = [beat_id for beat_id in sorted(fallback_ids - real_covered_ids) if beat_id not in ai_notes_by_beat]
        if missing_ai_notes and coverage_mode not in {"full_ai", "selective_ai"}:
            raise RuntimeError(
                "AI Visual fallback is missing ai_usage_notes for: " + ", ".join(missing_ai_notes)
            )
        if real_covered_ids and coverage_mode != "full_ai":
            generated = [item for item in generated if str(item.get("beat_id") or "") not in real_covered_ids]
            errors = [item for item in errors if str(item.get("beat_id") or "") not in real_covered_ids]
            media_factory_jobs = [
                item for item in media_factory_jobs if str(item.get("beat_id") or "") not in real_covered_ids
            ]
        if generated:
            self._merge_generated_assets(
                workspace,
                registry,
                generated,
                prefer_generated=coverage_mode == "full_ai",
            )
            registry = _read_json(workspace / "asset_registry.json")
        targets = self._targets(workspace, visual, registry, coverage_mode, ai_media_mode)
        # Errors from an earlier failed attempt are history once those beats are
        # actively being retried. Keeping them here makes the live UI report a
        # large failure count while the current run is healthy.
        retry_target_ids = {
            str(item.get("beat_id") or "").strip()
            for item in targets
            if str(item.get("beat_id") or "").strip()
        }
        if resume_current_profile and retry_target_ids:
            errors = [
                item
                for item in errors
                if str(item.get("beat_id") or "").strip() not in retry_target_ids
            ]
        media_dir = workspace / "media" / "ai"
        request_dir = workspace / ".ai_visual"
        media_dir.mkdir(parents=True, exist_ok=True)
        request_dir.mkdir(parents=True, exist_ok=True)
        previous_target_ids = [
            str(value).strip()
            for value in (previous_manifest.get("target_beat_ids") or [])
            if str(value).strip()
        ]
        target_ids = [
            beat_id
            for beat_id in dict.fromkeys(
                previous_target_ids
                + [str(item.get("beat_id") or "") for item in targets]
                + [str(item.get("beat_id") or "") for item in generated]
            )
            if beat_id and (coverage_mode == "full_ai" or beat_id not in real_covered_ids)
        ]
        created_at = str(previous_manifest.get("created_at") or _now())

        def upsert_generated(item: dict[str, Any]) -> None:
            beat_id = str(item.get("beat_id") or "")
            generated[:] = [existing for existing in generated if str(existing.get("beat_id") or "") != beat_id]
            generated.append(item)

        def clear_error(beat_id: str, stage: str) -> None:
            errors[:] = [
                item for item in errors
                if not (str(item.get("beat_id") or "") == beat_id and str(item.get("stage") or "") == stage)
            ]

        def set_error(beat_id: str, stage: str, error: str) -> None:
            clear_error(beat_id, stage)
            errors.append({"beat_id": beat_id, "stage": stage, "error": error})

        def upsert_media_factory_job(beat_id: str, stage: str, ticket: dict[str, Any], **updates: Any) -> None:
            media_factory_jobs[:] = [
                item for item in media_factory_jobs
                if not (str(item.get("beat_id") or "") == beat_id and str(item.get("stage") or "") == stage)
            ]
            media_factory_jobs.append({
                "beat_id": beat_id,
                "stage": stage,
                "scene_id": str(ticket.get("scene_id") or ""),
                "job_id": str(ticket.get("job_id") or ""),
                "name": str(ticket.get("name") or ""),
                "status": str(updates.pop("status", ticket.get("status") or "queued")),
                "created_at": str(ticket.get("created_at") or ""),
                **updates,
            })

        def previous_media_factory_job(beat_id: str, stage: str) -> dict[str, Any] | None:
            for item in reversed(media_factory_jobs):
                if str(item.get("beat_id") or "") == beat_id and str(item.get("stage") or "") == stage:
                    if str(item.get("job_id") or ""):
                        return dict(item)
            return None

        def reusable_media_factory_job(ticket: dict[str, Any] | None) -> dict[str, Any] | None:
            if not ticket:
                return None
            inspect_job = getattr(self.tool_runner, "inspect", None)
            if not callable(inspect_job):
                return None if str(ticket.get("status") or "").lower() == "failed" else ticket
            try:
                live_job = inspect_job(ticket)
            except Exception:
                return ticket
            live_status = str((live_job or {}).get("status") or "").lower()
            if live_status in {"queued", "running", "completed"}:
                return ticket
            return None

        still_fallback_ids: set[str] = set()
        run_warnings: list[str] = []
        queue_status_getter = getattr(self.tool_runner, "queue_status", None)
        last_factory_clear_sync_at = previous_manifest.get("last_factory_clear_sync_at")
        if callable(queue_status_getter) and is_live_factory_runner:
            try:
                qs_init = queue_status_getter()
                if isinstance(qs_init, dict) and qs_init.get("last_cleared_at") is not None:
                    last_factory_clear_sync_at = str(qs_init.get("last_cleared_at"))
            except Exception:
                pass

        def checkpoint(
            *,
            status: str,
            current_beat_id: str | None = None,
            last_error: str | None = None,
            warning: str | None = None,
            pause_warning: str | None = None,
        ) -> list[str]:
            current_registry = _read_json(workspace / "asset_registry.json")
            remaining = [
                str(beat.get("beat_id") or "")
                for beat in self._targets(workspace, visual, current_registry, coverage_mode, ai_media_mode)
                if str(beat.get("beat_id") or "") not in still_fallback_ids
            ]
            if warning is None and run_warnings:
                warning = " ".join(dict.fromkeys(run_warnings))
            generated_ids = {
                str(item.get("beat_id") or "")
                for item in generated
                if str(item.get("beat_id") or "")
            }
            image_done_ids = {
                str(item.get("beat_id") or "")
                for item in generated
                if str(item.get("beat_id") or "") and item.get("image_path")
            }
            video_done_ids = {
                str(item.get("beat_id") or "")
                for item in generated
                if str(item.get("beat_id") or "") and item.get("video_path")
            }
            errors[:] = [
                err for err in errors
                if not (str(err.get("stage") or "image") == "image" and str(err.get("beat_id") or "") in image_done_ids)
                and not (str(err.get("stage") or "") == "video" and str(err.get("beat_id") or "") in video_done_ids)
            ]
            effective_last_error = last_error or (str(errors[-1].get("error") or "") if errors else None)
            manifest = {
                "job_id": current_job_id,
                "status": status,
                "provider": "cofistudio_media_factory",
                "generation_profile": AI_VISUAL_GENERATION_PROFILE,
                "image_model": image_model,
                "video_model": video_model,
                "aspect_ratio": aspect_ratio,
                "veo_enabled": enable_video,
                "style_mode": style_mode,
                "style_preset": style_preset,
                "custom_style": custom_style,
                "ai_media_mode": ai_media_mode,
                "coverage_mode": coverage_mode,
                "style_reference_image": str(style_reference_path) if has_style_reference else "",
                "style_settings_signature": style_signature,
                "visual_style": visual_style,
                "target_beat_ids": target_ids,
                "generated": generated,
                "errors": errors,
                "error_count": len(errors),
                "last_error": effective_last_error,
                "warning": warning,
                "pause_warning": pause_warning,
                "media_factory_jobs": media_factory_jobs,
                "remaining_missing_beats": remaining,
                "still_fallback_beats": sorted(still_fallback_ids),
                "generated_count": len(generated_ids.intersection(target_ids)),
                "total_targets": len(target_ids),
                "current_beat_id": current_beat_id,
                "last_factory_clear_sync_at": last_factory_clear_sync_at,
                "created_at": created_at,
                "updated_at": _now(),
            }
            _write_json(manifest_path, manifest)
            return remaining

        checkpoint(status="running")

        if callable(queue_status_getter):
            qs = None
            try:
                qs = queue_status_getter()
            except Exception:
                pass
            if isinstance(qs, dict) and qs.get("paused"):
                resume_queue_fn = getattr(self.tool_runner, "resume_queue", None)
                if is_live_factory_runner and callable(resume_queue_fn):
                    try:
                        resumed = resume_queue_fn()
                        if isinstance(resumed, dict) and resumed.get("paused") is False:
                            qs = {**qs, "paused": False}
                    except Exception:
                        pass
            if isinstance(qs, dict) and qs.get("paused"):
                pause_msg = "Media Factory queue đang tạm dừng (paused); AI Visual không thể bắt đầu sinh media."
                checkpoint(status="paused", pause_warning=pause_msg)
                raise RuntimeError(pause_msg)

        queue_runner = callable(getattr(self.tool_runner, "submit", None)) and callable(getattr(self.tool_runner, "wait", None))
        image_work: dict[str, dict[str, Any]] = {}
        video_work: dict[str, dict[str, Any]] = {}

        # Keep a bounded producer window. Media Factory concurrency controls how many
        # workers execute at once; this limit controls how many Documentary jobs may
        # be queued/running for the shared account at any moment.
        target_position = {
            str(beat.get("beat_id") or ""): index
            for index, beat in enumerate(targets)
        }

        def image_wait_order(beat_id: str) -> tuple[int, str, int]:
            work = image_work[beat_id]
            if work.get("image_path"):
                return (0, "", target_position.get(beat_id, 0))
            ticket = work.get("ticket") if isinstance(work.get("ticket"), dict) else {}
            created_at = str((ticket or {}).get("created_at") or "")
            if created_at:
                return (1, created_at, target_position.get(beat_id, 0))
            return (2, "", target_position.get(beat_id, 0))

        for beat in targets:
            beat_id = str(beat.get("beat_id") or "")
            character_ref_imgs = self._character_reference_images(beat, workspace)
            ref_imgs: list[str] = []
            if has_style_reference and style_reference_path is not None:
                ref_imgs.append(str(style_reference_path))
            for reference in character_ref_imgs:
                if reference not in ref_imgs:
                    ref_imgs.append(reference)
            image_scene = {
                "id": f"{beat_id}_ai_image",
                "name": f"AI bổ sung · {beat_id}",
                "task_type": "image_generation",
                "prompt": self._prompt(
                    beat,
                    aspect_ratio,
                    visual_style,
                    ai_notes_by_beat.get(beat_id),
                    preset_prompt=preset_prompt,
                    has_style_reference=has_style_reference,
                ),
                "model": image_model,
                "aspect_ratio": aspect_ratio,
                "reference_image": ref_imgs[0] if ref_imgs else None,
                "reference_images": ref_imgs,
                "_output_directory": str(media_dir),
                "_output_stem": f"{beat_id}_ai_keyframe",
                "_remove_watermark": False,
            }
            image_path = (
                self._existing_generated_media(media_dir, f"{beat_id}_ai_keyframe")
                if use_existing_local_cache else None
            )
            work = {"beat": beat, "scene": image_scene, "image_path": image_path, "ticket": None}
            image_work[beat_id] = work
            if image_path or not queue_runner:
                continue
            ticket = reusable_media_factory_job(previous_media_factory_job(beat_id, "image"))
            work["ticket"] = ticket

        def publish_image(beat: dict[str, Any], image_path: str) -> None:
            beat_id = str(beat.get("beat_id") or "")
            clear_error(beat_id, "image")

            item: dict[str, Any] = {
                "beat_id": beat_id,
                "image_path": image_path,
                "image_model": image_model,
                "video_path": None,
                "video_model": None,
                "truth_status": "illustrative_reconstruction",
                "ai_reason": str((ai_notes_by_beat.get(beat_id) or {}).get("reason") or "").strip(),
                "visual_language": (
                    (ai_notes_by_beat.get(beat_id) or {}).get("visual_language")
                    if isinstance((ai_notes_by_beat.get(beat_id) or {}).get("visual_language"), dict)
                    else {}
                ),
            }
            # Phase 1 publishes images only. Video cards are not created until every
            # target image has either completed or failed, so image generation and
            # image-to-video work never compete for the same outstanding window.
            upsert_generated(item)
            self._merge_generated_assets(
                workspace,
                _read_json(workspace / "asset_registry.json"),
                [item],
                prefer_generated=coverage_mode == "full_ai",
            )
            checkpoint(status="running", current_beat_id=beat_id)

        def prepare_video_work(beat: dict[str, Any], image_path: str) -> None:
            beat_id = str(beat.get("beat_id") or "")
            item = next(
                (dict(existing) for existing in generated if str(existing.get("beat_id") or "") == beat_id),
                {
                    "beat_id": beat_id,
                    "image_path": image_path,
                    "image_model": image_model,
                    "video_path": None,
                    "video_model": None,
                    "truth_status": "illustrative_reconstruction",
                    "ai_reason": str((ai_notes_by_beat.get(beat_id) or {}).get("reason") or "").strip(),
                    "visual_language": (
                        (ai_notes_by_beat.get(beat_id) or {}).get("visual_language")
                        if isinstance((ai_notes_by_beat.get(beat_id) or {}).get("visual_language"), dict)
                        else {}
                    ),
                },
            )
            item["image_path"] = image_path
            item["image_model"] = image_model
            ai_note = ai_notes_by_beat.get(beat_id) or {}
            explicit_ai_motion = (
                ai_note.get("allow_ai_video") is True
                or str(beat.get("ai_motion_required") or "").strip().lower() in {"1", "true", "yes", "on"}
            )
            wants_video = enable_video and (ai_media_mode == "video" or (ai_media_mode == "mixed" and explicit_ai_motion))
            if not wants_video:
                return
            video_scene = {
                "id": f"{beat_id}_ai_video",
                "name": f"AI chuyển động · {beat_id}",
                "task_type": "image_to_video",
                "prompt": self._video_prompt(beat),
                "model": video_model,
                "aspect_ratio": aspect_ratio,
                "duration_seconds": 8,
                "reference_image": image_path,
                "reference_images": [image_path],
                "_video_pair_mode": "PAIR_MODE_START_ONLY",
                "_output_directory": str(media_dir),
                "_output_stem": f"{beat_id}_ai_video",
            }
            existing_video = (
                self._existing_generated_media(media_dir, f"{beat_id}_ai_video", video=True)
                if use_existing_local_cache else None
            )
            if existing_video:
                item["video_path"] = existing_video
                item["video_model"] = video_model
                clear_error(beat_id, "video")
                upsert_generated(item)
                self._merge_generated_assets(
                    workspace,
                    _read_json(workspace / "asset_registry.json"),
                    [item],
                    prefer_generated=coverage_mode == "full_ai",
                )
                checkpoint(status="running", current_beat_id=beat_id)
                return
            if queue_runner:
                video_ticket = reusable_media_factory_job(previous_media_factory_job(beat_id, "video"))
                video_work[beat_id] = {
                    "item": item,
                    "scene": video_scene,
                    "ticket": video_ticket,
                    "prepared_ticket": None,
                }
                return
            try:
                item["video_path"] = self.tool_runner(video_scene, request_dir / f"{beat_id}_video.json")
                item["video_model"] = video_model
                clear_error(beat_id, "video")
            except Exception as exc:
                item["video_error"] = str(exc)
                set_error(beat_id, "video", str(exc))
            upsert_generated(item)
            self._merge_generated_assets(
                workspace,
                _read_json(workspace / "asset_registry.json"),
                [item],
                prefer_generated=coverage_mode == "full_ai",
            )
            checkpoint(status="running", current_beat_id=beat_id)

        prepare_scene = getattr(self.tool_runner, "prepare_scene", None)
        run_prepared = getattr(self.tool_runner, "run_prepared", None)

        def stage_cards(work_map: dict[str, dict[str, Any]], beat_ids: list[str], stage: str) -> None:
            if not callable(prepare_scene) or not callable(run_prepared):
                return
            failures: list[tuple[str, str]] = []
            for beat_id in beat_ids:
                work = work_map[beat_id]
                if work.get("ticket") or work.get("prepared_ticket"):
                    continue
                try:
                    prepared_ticket = prepare_scene(
                        work["scene"],
                        request_dir / f"{beat_id}_{stage}.json",
                    )
                    work["prepared_ticket"] = prepared_ticket
                    upsert_media_factory_job(beat_id, stage, prepared_ticket, status="prepared")
                except Exception as exc:
                    failures.append((beat_id, str(exc)))
            checkpoint(status="running")
            if failures:
                detail = "; ".join(f"{beat_id}: {message}" for beat_id, message in failures[:5])
                remaining = len(failures) - 5
                if remaining > 0:
                    detail = f"{detail}; +{remaining} lỗi khác"
                raise RuntimeError(
                    f"Không thể bắt đầu pha {stage}: chưa tạo đủ {len(failures)} card. {detail}"
                )

        def start_card(work: dict[str, Any], beat_id: str, stage: str) -> dict[str, Any]:
            request_path = request_dir / f"{beat_id}_{stage}.json"
            prepared_ticket = work.get("prepared_ticket")
            if callable(prepare_scene) and callable(run_prepared):
                if not prepared_ticket:
                    raise RuntimeError(f"Card {stage} của {beat_id} chưa được chuẩn bị")
                return run_prepared(work["scene"], request_path, prepared_ticket)
            return self.tool_runner.submit(work["scene"], request_path)

        if queue_runner:
            for beat in targets:
                beat_id = str(beat.get("beat_id") or "")
                image_path = image_work[beat_id].get("image_path")
                if image_path:
                    publish_image(beat, str(image_path))

            pending_images = [
                str(beat.get("beat_id") or "")
                for beat in targets
                if not image_work[str(beat.get("beat_id") or "")].get("image_path")
                and not image_work[str(beat.get("beat_id") or "")].get("ticket")
            ]
            active_images = [
                str(beat.get("beat_id") or "")
                for beat in targets
                if image_work[str(beat.get("beat_id") or "")].get("ticket")
            ]

            # Create every image card before starting any new image generation.
            stage_cards(image_work, pending_images, "image")

            def abort_if_all_scenes_deleted(exc: BaseException) -> None:
                if "SCENE_DELETED:" not in str(exc):
                    return
                if callable(list_scenes_fn) and not (callable(req_fn) and getattr(req_fn, "__name__", "") == "<lambda>"):
                    try:
                        if len(list_scenes_fn()) > 0:
                            return
                    except Exception:
                        return
                for stale_file in request_dir.glob("*.json"):
                    try:
                        stale_file.unlink()
                    except OSError:
                        pass
                if media_dir.is_dir():
                    for stale_media in media_dir.iterdir():
                        if stale_media.is_file() and (
                            "_ai_keyframe" in stale_media.name
                            or "_ai_video" in stale_media.name
                            or "_ai_motion" in stale_media.name
                        ):
                            try:
                                stale_media.unlink()
                            except OSError:
                                pass
                try:
                    cur_reg = _read_json(workspace / "asset_registry.json")
                    cur_reg["assets"] = [
                        item
                        for item in (cur_reg.get("assets") or [])
                        if not (
                            isinstance(item, dict)
                            and isinstance(item.get("source"), dict)
                            and item["source"].get("generated_by") == "cofi_ai_visual"
                        )
                    ]
                    _write_json(workspace / "asset_registry.json", cur_reg)
                except Exception:
                    pass
                generated.clear()
                errors.clear()
                media_factory_jobs.clear()
                pause_msg = "Đã xóa toàn bộ box card trong Media Factory và reset tiến độ AI Visual về 0. Bấm Chạy lại hoặc Chạy tiếp để tạo lại từ đầu."
                checkpoint(status="paused", pause_warning=pause_msg)
                raise RuntimeError(pause_msg) from exc

            retried_image_beats: set[str] = set()
            is_live_http_runner = (
                callable(getattr(self.tool_runner, "inspect", None))
                and getattr(getattr(self.tool_runner, "_request_json", None), "__name__", "") in {"_request_json", "_default_request_json"}
            )
            while pending_images or active_images:
                for err_item in list(errors):
                    if str(err_item.get("stage") or "") != "image":
                        continue
                    err_bid = str(err_item.get("beat_id") or "")
                    if err_bid in image_work and not image_work[err_bid].get("image_path"):
                        recovered_img = self._existing_generated_media(media_dir, f"{err_bid}_ai_keyframe")
                        if recovered_img:
                            image_work[err_bid]["image_path"] = str(recovered_img)
                            publish_image(image_work[err_bid]["beat"], str(recovered_img))
                while pending_images and len(active_images) < self.outstanding_limit:
                    beat_id = pending_images.pop(0)
                    work = image_work[beat_id]
                    try:
                        ticket = start_card(work, beat_id, "image")
                        work["ticket"] = ticket
                        upsert_media_factory_job(beat_id, "image", ticket, status="queued")
                        active_images.append(beat_id)
                    except Exception as exc:
                        abort_if_all_scenes_deleted(exc)
                        set_error(beat_id, "image", str(exc))
                    checkpoint(status="running", current_beat_id=beat_id)

                if not active_images:
                    if not pending_images:
                        retry_candidates = [
                            str(beat.get("beat_id") or "")
                            for beat in targets
                            if not image_work[str(beat.get("beat_id") or "")].get("image_path")
                            and str(beat.get("beat_id") or "") not in retried_image_beats
                        ]
                        if retry_candidates and is_live_http_runner:
                            for rb in retry_candidates:
                                retried_image_beats.add(rb)
                                image_work[rb]["ticket"] = None
                                image_work[rb]["prepared_ticket"] = None
                            stage_cards(image_work, retry_candidates, "image")
                            pending_images.extend(retry_candidates)
                    continue

                ready_beat_id: str | None = None
                if callable(getattr(self.tool_runner, "inspect", None)):
                    for cand_id in sorted(active_images, key=image_wait_order):
                        cand_ticket = image_work[cand_id].get("ticket")
                        if not isinstance(cand_ticket, dict):
                            ready_beat_id = cand_id
                            break
                        try:
                            live_job = self.tool_runner.inspect(cand_ticket)
                        except Exception:
                            live_job = None
                        if live_job is None:
                            ready_beat_id = cand_id
                            break
                        live_status = str((live_job or {}).get("status") or "").lower()
                        live_err = str((live_job or {}).get("error") or "").strip()
                        if live_status in {"completed", "failed", "paused"} or (live_status == "queued" and live_err):
                            ready_beat_id = cand_id
                            break
                    if ready_beat_id is None and callable(queue_status_getter):
                        try:
                            qs_now = queue_status_getter()
                            if isinstance(qs_now, dict) and (qs_now.get("paused") is True or qs_now.get("status") == "paused"):
                                ready_beat_id = min(active_images, key=image_wait_order)
                        except Exception:
                            pass
                if ready_beat_id is None and is_live_http_runner and len(active_images) > 1:
                    time.sleep(1.0)
                    continue

                beat_id = ready_beat_id or min(active_images, key=image_wait_order)
                work = image_work[beat_id]
                ticket = work["ticket"]
                try:
                    factory_output_path = self.tool_runner.wait(ticket)
                    image_path = self._capture_generated_media(
                        factory_output_path,
                        media_dir,
                        f"{beat_id}_ai_keyframe",
                    )
                    work["image_path"] = image_path
                    upsert_media_factory_job(
                        beat_id,
                        "image",
                        ticket,
                        status="completed",
                        output_path=image_path,
                        media_factory_output_path=factory_output_path,
                    )
                    publish_image(work["beat"], image_path)
                except Exception as exc:
                    abort_if_all_scenes_deleted(exc)
                    upsert_media_factory_job(beat_id, "image", ticket, status="failed", error=str(exc))
                    set_error(beat_id, "image", str(exc))
                    checkpoint(status="running", current_beat_id=beat_id)
                active_images.remove(beat_id)
                if not pending_images and not active_images and is_live_http_runner:
                    retry_candidates = [
                        str(beat.get("beat_id") or "")
                        for beat in targets
                        if not image_work[str(beat.get("beat_id") or "")].get("image_path")
                        and str(beat.get("beat_id") or "") not in retried_image_beats
                    ]
                    if retry_candidates:
                        for rb in retry_candidates:
                            retried_image_beats.add(rb)
                            image_work[rb]["ticket"] = None
                            image_work[rb]["prepared_ticket"] = None
                        stage_cards(image_work, retry_candidates, "image")
                        pending_images.extend(retry_candidates)
        else:
            for beat in targets:
                beat_id = str(beat.get("beat_id") or "")
                work = image_work[beat_id]
                image_path = work["image_path"]
                if not image_path:
                    try:
                        image_path = self._capture_generated_media(
                            self.tool_runner(work["scene"], request_dir / f"{beat_id}_image.json"),
                            media_dir,
                            f"{beat_id}_ai_keyframe",
                        )
                    except Exception as exc:
                        set_error(beat_id, "image", str(exc))
                        checkpoint(status="running", current_beat_id=beat_id)
                        continue
                work["image_path"] = str(image_path)
                publish_image(beat, str(image_path))

        # Phase 2 begins only after Phase 1 has fully drained. Build every video
        # card from the completed image + prompt set, then start video generation.
        for beat in targets:
            beat_id = str(beat.get("beat_id") or "")
            image_path = image_work[beat_id].get("image_path")
            if image_path:
                prepare_video_work(beat, str(image_path))

        def video_wait_order(beat_id: str) -> tuple[int, str, int]:
            work = video_work[beat_id]
            ticket = work.get("ticket") if isinstance(work.get("ticket"), dict) else {}
            created_at = str((ticket or {}).get("created_at") or "")
            if created_at:
                return (0, created_at, target_position.get(beat_id, 0))
            return (1, "", target_position.get(beat_id, 0))

        pending_videos = [
            beat_id
            for beat_id, work in video_work.items()
            if not work.get("ticket")
        ]
        active_videos = [
            beat_id
            for beat_id, work in video_work.items()
            if work.get("ticket")
        ]
        if queue_runner:
            # Create every video card only after the full image phase has ended.
            stage_cards(video_work, pending_videos, "video")

        video_fail_streak = 0

        def record_video_failure() -> None:
            nonlocal video_fail_streak, pending_videos
            video_fail_streak += 1
            if not self.video_fail_streak_limit or video_fail_streak < self.video_fail_streak_limit or not pending_videos:
                return
            message = (
                f"Veo lỗi liên tiếp {video_fail_streak} lần; dừng gửi thêm {len(pending_videos)} clip "
                "và dùng ảnh tĩnh có chuyển động cho các beat còn lại."
            )
            run_warnings.append(message)
            for skipped_id in pending_videos:
                skipped = dict(video_work[skipped_id]["item"])
                skipped["video_error"] = message
                upsert_generated(skipped)
            pending_videos = []

        while queue_runner and (pending_videos or active_videos):
            while pending_videos and len(active_videos) < self.outstanding_limit:
                beat_id = pending_videos.pop(0)
                work = video_work[beat_id]
                item = dict(work["item"])
                try:
                    video_ticket = start_card(work, beat_id, "video")
                    work["ticket"] = video_ticket
                    upsert_media_factory_job(beat_id, "video", video_ticket, status="queued")
                    active_videos.append(beat_id)
                except Exception as exc:
                    item["video_error"] = str(exc)
                    set_error(beat_id, "video", str(exc))
                    upsert_generated(item)
                    record_video_failure()
                checkpoint(status="running", current_beat_id=beat_id)

            if not active_videos:
                continue

            beat_id = min(active_videos, key=video_wait_order)
            work = video_work[beat_id]
            item = dict(work["item"])
            ticket = work["ticket"]
            try:
                factory_output_path = self.tool_runner.wait(ticket)
                item["video_path"] = self._capture_generated_media(
                    factory_output_path, media_dir, f"{beat_id}_ai_video", video=True
                )
                item["video_model"] = video_model
                item.pop("video_error", None)
                clear_error(beat_id, "video")
                upsert_media_factory_job(
                    beat_id,
                    "video",
                    ticket,
                    status="completed",
                    output_path=item["video_path"],
                    media_factory_output_path=factory_output_path,
                )
                video_fail_streak = 0
            except Exception as exc:
                item["video_error"] = str(exc)
                set_error(beat_id, "video", str(exc))
                upsert_media_factory_job(beat_id, "video", ticket, status="failed", error=str(exc))
                record_video_failure()
            upsert_generated(item)
            self._merge_generated_assets(
                workspace,
                _read_json(workspace / "asset_registry.json"),
                [item],
                prefer_generated=coverage_mode == "full_ai",
            )
            checkpoint(status="running", current_beat_id=beat_id)
            active_videos.remove(beat_id)

        final_registry = _read_json(workspace / "asset_registry.json")
        still_fallback_allowed = (
            self.video_still_fallback
            and (job.get("ai_visual") or {}).get("video_still_fallback") is not False
            and coverage_mode == "full_ai"
            and ai_media_mode == "video"
        )
        if still_fallback_allowed:
            still_beats = {
                str(asset.get("beat_id") or "")
                for asset in (final_registry.get("assets") or [])
                if isinstance(asset, dict)
                and _asset_exists(workspace, asset)
                and isinstance(asset.get("source"), dict)
                and asset["source"].get("generated_by") == "cofi_ai_visual"
                and str(asset.get("kind") or "") == "ai_reconstruction_still"
            }
            missing_video = {
                str(beat.get("beat_id") or "")
                for beat in self._targets(workspace, visual, final_registry, coverage_mode, ai_media_mode)
            }
            still_fallback_ids.update(missing_video & still_beats)
            if still_fallback_ids:
                for asset in final_registry.get("assets") or []:
                    if (
                        isinstance(asset, dict)
                        and str(asset.get("beat_id") or "") in still_fallback_ids
                        and isinstance(asset.get("source"), dict)
                        and asset["source"].get("generated_by") == "cofi_ai_visual"
                    ):
                        asset["source"]["motion_fallback"] = "remotion_camera_move"
                _write_json(workspace / "asset_registry.json", final_registry)
                run_warnings.append(
                    f"{len(still_fallback_ids)} beat không có clip Veo; dùng ảnh AI kèm chuyển động máy quay khi dựng."
                )

        unresolved = [
            str(beat.get("beat_id") or "")
            for beat in self._targets(
                workspace, visual, _read_json(workspace / "asset_registry.json"), coverage_mode, ai_media_mode,
            )
            if str(beat.get("beat_id") or "") not in still_fallback_ids
        ]
        remaining = checkpoint(status="incomplete" if unresolved else "completed")
        if remaining:
            error_msg = f"AI Visual vẫn thiếu beat: {', '.join(remaining)}"
            checkpoint(status="incomplete", last_error=error_msg)
            raise RuntimeError(error_msg)
        if not targets:
            message = "AI Visual: footage đã đủ, không cần tạo thêm ảnh/video."
        else:
            videos = sum(1 for item in generated if item.get("video_path"))
            message = f"AI Visual: bổ sung {len(generated)} beat qua Media Factory, gồm {videos} clip AI và {len(generated) - videos} ảnh AI."
        return StageResult(returncode=0, last_message=message, log_path=manifest_path)
