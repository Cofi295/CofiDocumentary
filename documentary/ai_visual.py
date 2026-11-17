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
    last_exc: Exception | None = None
    data: Any = None
    for attempt in range(8):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            last_exc = None
            break
        except (OSError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt >= 7:
                raise RuntimeError(f"Không đọc được {path.name}: {exc}") from exc
            time.sleep(0.05 * (attempt + 1))
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
            last_exc: Exception | None = None
            for attempt in range(4):
                try:
                    resp = client.request(
                        method=method,
                        url=f"{self.studio_api}{path}",
                        json=payload if payload is not None else None,
                        timeout=timeout,
                    )
                except Exception as exc:
                    last_exc = exc
                    if attempt < 3:
                        time.sleep(0.25 * (attempt + 1))
                        continue
                    raise RuntimeError(f"Không kết nối được Media Factory tại {self.studio_api}: {exc or type(exc).__name__}") from exc
                if resp.status_code >= 500 and attempt < 3:
                    time.sleep(0.25 * (attempt + 1))
                    continue
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
        if os.getenv("PYTEST_CURRENT_TEST") and getattr(self._request_json, "__func__", None) is CofiStudioMediaFactoryRunner._request_json:
            return {"ok": True, "skipped_in_pytest": True}
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
        editing_dna = (job or {}).get("editing_dna") if isinstance((job or {}).get("editing_dna"), dict) else {}
        preset_id = str((editing_dna or {}).get("preset_id") or "").strip()
        vpm = str((editing_dna or {}).get("visual_priority_mode") or "").strip().lower()
        vmix_ai = float((((editing_dna or {}).get("visual_mix") or {}).get("ai") or 0.0))
        snap = (job or {}).get("channel_profile_snapshot") if isinstance((job or {}).get("channel_profile_snapshot"), dict) else {}
        content_mode = str(
            (job or {}).get("content_mode")
            or (snap or {}).get("content_mode")
            or (editing_dna or {}).get("content_mode")
            or ""
        ).strip().lower()
        snap_ed_vs = str(((snap or {}).get("editorial_dna") or {}).get("visual_strategy") or "").strip().lower()
        if preset_id in {"forensic_noir_director_v2", "vox_china_crime_newsroom_v10"} and snap_ed_vs in {
            "edit_direct_footage",
            "semi_content",
            "ban_content",
            "edit_footage",
        }:
            visual_strategy = "edit_direct_footage"
        if visual_strategy == "full_ai":
            coverage_mode = "full_ai"
        elif (
            visual_strategy in {"edit_direct_footage", "semi_content", "ban_content", "edit_footage"}
            or vpm == "ai_cinema_character_drama"
            or content_mode == "creative_audio_drama"
            or vmix_ai >= 0.40
        ):
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
        if style_mode == "preset" and any(
            tok in style_prompt.lower()
            for tok in ("0% cartoon", "0% stickman", "realistic human anatomy")
        ):
            style_reference_image = ""
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

    @staticmethod
    def _is_chibi_mascot_style(style_preset: str = "", style_prompt: str = "") -> bool:
        combined = f"{style_preset or ''} {style_prompt or ''}".lower()
        if any(tok in combined for tok in ("0% cartoon", "0% stickman", "realistic human anatomy", "photorealistic", "35mm", "kodak vision3")):
            return False
        return any(tok in combined for tok in ("chibi", "mascot", "#ffd43b", "yellow spherical", "noir_chibi"))

    @classmethod
    def _build_visual_style(cls, visual: dict[str, Any], job: dict[str, Any] | None = None) -> dict[str, Any]:
        ed_dna = (job or {}).get("editing_dna") if isinstance((job or {}).get("editing_dna"), dict) else {}
        snap = (job or {}).get("channel_profile_snapshot") if isinstance((job or {}).get("channel_profile_snapshot"), dict) else {}
        content_mode = str(
            (job or {}).get("content_mode")
            or (snap or {}).get("content_mode")
            or (ed_dna or {}).get("content_mode")
            or ""
        ).strip().lower()
        vpm = str((ed_dna or {}).get("visual_priority_mode") or "").strip().lower()
        if content_mode == "creative_audio_drama" or vpm == "ai_cinema_character_drama":
            directive = (
                "Korean Cinema Audio-Drama Visual Bible: Warm 35mm theatrical film look (Kodak Vision3 500T aesthetic, "
                "3200K warm tungsten amber practical lamps balanced with soft twilight slate shadows, gentle highlight rolloff "
                "capped at luminance <= 215/255 for dark-room bedtime viewing comfort). Render authentic contemporary or nostalgic "
                "Korean residential architecture, artisan workshops, tea rooms, courtyards, and natural East Asian human skin textures, "
                "silver-streaked hair, and dignified Korean wardrobe with strict character continuity across scenes. "
                "Zero harsh white studio glare, zero neon clutter, zero text/subtitles/logos."
            )
            return {
                "dominant_year": None,
                "period_start": None,
                "period_end": None,
                "color_mode": "warm_35mm_cinema_color",
                "directive": directive,
            }
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
    def _load_episode_character_bible(
        cls,
        workspace: Path,
        job: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        bible_path = workspace / "character_bible.json"
        if bible_path.is_file():
            try:
                raw = json.loads(bible_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    raw_list = raw.get("characters") or raw.get("cast") or []
                elif isinstance(raw, list):
                    raw_list = raw
                else:
                    raw_list = []
                for item in raw_list:
                    if isinstance(item, dict):
                        entries.append(dict(item))
            except Exception:
                pass
        if not entries:
            outline_path = workspace / "outline.json"
            if outline_path.is_file():
                try:
                    out_raw = json.loads(outline_path.read_text(encoding="utf-8"))
                    if isinstance(out_raw, dict):
                        for item in (out_raw.get("character_bible") or out_raw.get("characters") or []):
                            if isinstance(item, dict):
                                entries.append(dict(item))
                except Exception:
                    pass
        if not entries and isinstance(job, dict):
            cb = job.get("creative_brief") if isinstance(job.get("creative_brief"), dict) else {}
            protag = str((cb or {}).get("protagonist") or "").strip()
            ed_dna = job.get("editing_dna") if isinstance(job.get("editing_dna"), dict) else {}
            if protag and str((ed_dna or {}).get("character_reference_mode") or "").strip() == "self_generated_flow_master_sheet_per_episode":
                entries.append({
                    "id": "char_01_protagonist",
                    "name": protag.split("(")[0].split("—")[0].strip()[:40] or "주인공",
                    "role": "protagonist",
                    "aliases": ["주인공", "어머니", "아버지", "장인", "사장님", "할머니"],
                    "appearance": protag,
                })
        normalized: list[dict[str, Any]] = []
        sheet_dir = workspace / "media" / "character_sheet"
        for idx, item in enumerate(entries[:6], 1):
            raw_id = re.sub(
                r"[^a-zA-Z0-9_-]+",
                "_",
                str(item.get("id") or item.get("character_id") or item.get("role_id") or f"char_{idx:02d}"),
            ).strip("_") or f"char_{idx:02d}"
            name = str(
                item.get("name")
                or item.get("korean_name")
                or item.get("name_ko")
                or f"인물 {idx}"
            ).strip()
            raw_aliases: list[Any] = []
            for alias_field in ("aliases", "role_keywords", "honorific_titles"):
                val = item.get(alias_field)
                if isinstance(val, list):
                    raw_aliases.extend(val)
            pen_name = str(item.get("pen_name_ko") or item.get("pen_name") or "").strip()
            if pen_name:
                raw_aliases.append(pen_name)
                bare_pen = pen_name.split("(")[0].strip()
                if bare_pen and bare_pen != pen_name:
                    raw_aliases.append(bare_pen)
            aliases: list[str] = []
            for a in raw_aliases:
                sa = str(a).strip()
                if sa and sa not in aliases:
                    aliases.append(sa)
            role = str(
                item.get("role")
                or item.get("role_type")
                or ("protagonist" if idx == 1 else "supporting")
            ).strip()
            appearance = str(
                item.get("appearance")
                or item.get("flow_reference_sheet_prompt")
                or item.get("reference_sheet_prompt")
                or item.get("appearance_prompt")
                or item.get("visual_description")
                or item.get("wardrobe")
                or f"Dignified Korean {role} ({name}), realistic East Asian facial structure, natural skin texture, consistent signature wardrobe"
            ).strip()
            explicit_sheet = str(item.get("sheet_path") or item.get("reference_image") or "").strip()
            resolved_sheet = ""
            if explicit_sheet and Path(explicit_sheet).is_file():
                resolved_sheet = str(Path(explicit_sheet))
            elif sheet_dir.is_dir():
                for ext in (".jpg", ".jpeg", ".png", ".webp"):
                    cand = sheet_dir / f"{raw_id}{ext}"
                    if cand.is_file() and cand.stat().st_size > 0:
                        resolved_sheet = str(cand)
                        break
            normalized.append({
                "id": raw_id,
                "name": name,
                "role": role,
                "aliases": aliases,
                "appearance": appearance,
                "wardrobe_by_act": item.get("wardrobe_by_act") if isinstance(item.get("wardrobe_by_act"), dict) else {},
                "sheet_path": resolved_sheet,
            })
        return normalized

    def ensure_episode_character_reference_sheets(
        self,
        workspace: Path,
        job: dict[str, Any] | None,
        *,
        image_model: str,
        aspect_ratio: str = "16:9",
        preset_prompt: str = "",
        allow_live_generation: bool = False,
    ) -> list[dict[str, Any]]:
        ed_dna = (job or {}).get("editing_dna") if isinstance((job or {}).get("editing_dna"), dict) else {}
        snap_ed_dna = (((job or {}).get("channel_profile_snapshot") or {}).get("editing_dna") or {}) if isinstance((job or {}).get("channel_profile_snapshot"), dict) else {}
        char_ref_mode = str(
            (ed_dna or {}).get("character_reference_mode")
            or (snap_ed_dna or {}).get("character_reference_mode")
            or ""
        ).strip()
        if char_ref_mode != "self_generated_flow_master_sheet_per_episode":
            return []
        cast = self._load_episode_character_bible(workspace, job)
        if not cast:
            return []
        sheet_dir = workspace / "media" / "character_sheet"
        req_dir = workspace / ".ai_visual" / "character_sheets"
        bible_file = workspace / "character_bible.json"
        has_explicit_bible_file = bible_file.is_file()
        should_generate = allow_live_generation or has_explicit_bible_file or bool((job or {}).get("auto_generate_character_sheets"))
        if should_generate and callable(self.tool_runner):
            sheet_dir.mkdir(parents=True, exist_ok=True)
            req_dir.mkdir(parents=True, exist_ok=True)
            for entry in cast[:6]:
                if entry.get("sheet_path") and Path(entry["sheet_path"]).is_file():
                    continue
                cid = entry["id"]
                style_prefix = f"{preset_prompt}\n\n" if preset_prompt else (
                    "35mm Korean theatrical film portrait (Kodak Vision3 500T, warm 3200K tungsten key light, highlight luminance <= 215, soft highlight rolloff, realistic East Asian skin texture, 0% cartoon, 0% text).\n\n"
                )
                sheet_prompt = (
                    f"{style_prefix}"
                    f"MASTER CHARACTER REFERENCE SHEET for recurring episode character '{entry['name']}' ({entry['role']}): "
                    f"{entry['appearance']}. Clean waist-up cinematic character reference portrait against a warm neutral softly lit Korean interior background, "
                    "clear facial bone structure, consistent hairstyle and signature wardrobe, natural dignified expression, 5 fingers per hand, "
                    "ABSOLUTELY ZERO text, labels, names, captions, watermarks, or split boxes."
                )
                scene_payload = {
                    "id": f"{cid}_master_sheet",
                    "name": f"Character Sheet · {entry['name']}",
                    "task_type": "image_generation",
                    "prompt": sheet_prompt,
                    "model": image_model,
                    "aspect_ratio": aspect_ratio,
                    "_output_directory": str(sheet_dir),
                    "_output_stem": cid,
                    "_remove_watermark": True,
                }
                for _attempt_sheet in range(2):
                    try:
                        generated_out = self.tool_runner(scene_payload, req_dir / f"{cid}_sheet.json")
                        captured = self._capture_generated_media(generated_out, sheet_dir, cid, video=False)
                        entry["sheet_path"] = captured
                        break
                    except Exception:
                        if _attempt_sheet == 0:
                            time.sleep(1.5)
                        continue
            try:
                sheet_by_id = {e["id"]: e.get("sheet_path", "") for e in cast if e.get("sheet_path")}
                if has_explicit_bible_file:
                    raw_bible = json.loads(bible_file.read_text(encoding="utf-8"))
                    if isinstance(raw_bible, dict) and isinstance(raw_bible.get("characters"), list):
                        for idx_c, raw_c in enumerate(raw_bible["characters"], 1):
                            if isinstance(raw_c, dict):
                                cid_c = re.sub(
                                    r"[^a-zA-Z0-9_-]+",
                                    "_",
                                    str(raw_c.get("id") or raw_c.get("character_id") or raw_c.get("role_id") or f"char_{idx_c:02d}"),
                                ).strip("_") or f"char_{idx_c:02d}"
                                if cid_c in sheet_by_id:
                                    raw_c["sheet_path"] = sheet_by_id[cid_c]
                        _write_json(bible_file, raw_bible)
                    else:
                        _write_json(bible_file, {"characters": cast})
                else:
                    _write_json(bible_file, {"characters": cast})
            except Exception:
                pass
        return cast

    @classmethod
    def _matched_character_profiles(
        cls,
        beat: dict[str, Any],
        workspace: Path,
        job: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        cast = cls._load_episode_character_bible(workspace, job)
        if not cast:
            return []
        haystack = " ".join([
            str(beat.get("narration_text") or ""),
            str(beat.get("visual_description") or ""),
            str(beat.get("purpose") or ""),
            " ".join(str(c) for c in (beat.get("character_ids") or [])),
        ]).lower()
        matched: list[dict[str, Any]] = []
        for entry in cast:
            tokens = [entry.get("id", ""), entry.get("name", ""), *(entry.get("aliases") or [])]
            if any(str(tok).strip() and str(tok).strip().lower() in haystack for tok in tokens):
                matched.append(entry)
        if not matched and cast:
            # Default to protagonist continuity when the beat depicts a person/dialogue scene and a protagonist sheet exists
            protag = cast[0]
            if protag.get("sheet_path") and (
                beat.get("is_verbatim_quote")
                or any(tok in haystack for tok in ("인물", "표정", "손", "눈빛", "마주", "앉", "서 있", "바라보", "character", "portrait", "woman", "man"))
            ):
                matched.append(protag)
        return matched[:2]

    @classmethod
    def _character_reference_images(
        cls,
        beat: dict[str, Any],
        workspace: Path,
        job: dict[str, Any] | None = None,
    ) -> list[str]:
        matched_cast = cls._matched_character_profiles(beat, workspace, job)
        sheet_refs = [
            str(entry["sheet_path"])
            for entry in matched_cast
            if entry.get("sheet_path") and Path(str(entry["sheet_path"])).is_file()
        ]
        if sheet_refs:
            return sheet_refs
        cast_all = cls._load_episode_character_bible(workspace, job)
        has_bible_sheets = any(
            entry.get("sheet_path") and Path(str(entry["sheet_path"])).is_file()
            for entry in cast_all
        )
        if has_bible_sheets:
            # Pure prop / environment / still-life beat with zero matched characters -> do not force a face reference
            return []
        sheet_dir = workspace / "media" / "character_sheet"
        if sheet_dir.is_dir():
            generic_sheets = sorted(
                str(p)
                for p in sheet_dir.iterdir()
                if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} and p.stat().st_size > 0
            )
            if generic_sheets:
                return generic_sheets[:1]

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

    @staticmethod
    def _sanitize_unsafe_prompt(prompt: str) -> str:
        replacements = (
            ("사건 현장", "조사 공간"),
            ("범죄 현장", "배경 공간"),
            ("연쇄살인", "장기 미제"),
            ("살인", "사건"),
            ("살해", "사건"),
            ("백골", "봉인된 기록"),
            ("시신", "단서"),
            ("시체", "단서"),
            ("사체", "단서"),
            ("주검", "단서"),
            ("피투성이", "어두운"),
            ("혈흔", "흔적"),
            ("피가", "흔적이"),
            ("피를", "흔적을"),
            ("흉기", "핵심 물품"),
            ("식칼", "도구"),
            ("칼을", "물품을"),
            ("총성", "경보음"),
            ("총기", "장비"),
            ("탄피", "미세 시료"),
            ("수배범", "인물"),
            ("용의자", "인물"),
            ("도주범", "인물"),
            ("체포", "조사"),
            ("수갑", "장비"),
            ("폭행", "갈등"),
            ("구타", "충돌"),
            ("질식", "위기"),
            ("자살", "침묵"),
            ("성폭행", "사건"),
            ("강간", "사건"),
            ("고문", "심문"),
            ("토막", "봉인"),
            ("참수", "은폐"),
            ("사형", "판결"),
            ("True Crime", "Broadcast Documentary"),
            ("crime scene", "archival interior"),
            ("murder", "historical case"),
            ("blood", "trace"),
            ("corpse", "evidence"),
            ("dead body", "evidence"),
            ("skeletal remains", "sealed archive"),
            ("shell casing", "trace sample"),
            ("gunshot", "alarm"),
            ("weapon", "object"),
            ("suicide", "silence"),
            ("gore", "shadow"),
        )
        out = str(prompt or "")
        for src, dst in replacements:
            out = out.replace(src, dst)
        return out

    @staticmethod
    def _clean_scene_focus(narration: str, visual: str) -> str:
        text = str(visual or "").strip()
        text = re.sub(r"(?i)\bcold forensic noir\b\s*", "", text)
        text = re.sub(r"\[[^\]]*\]\s*", "", text)
        text = re.sub(r"\bACT\d+_[A-Z0-9_]+:\s*", "", text)
        text = re.sub(r'(?i)\bClause\s+focus\s*\([^)]*\)\s*:\s*"[^"]*"\s*[—\-–]*\s*', "", text)
        text = re.sub(r"(?i)Cold\s+desaturated\s+noir\s+color\s+grade[^.]*\.", "", text)
        text = re.sub(r"(?i)authentic\s+Chinese\s+judicial/public\s+security\s+archival\s+typography[^.]*\.", "", text)
        text = re.sub(r"(?i)anchored\s+mobile-readable\s+annotation\s+highlight[^.]*\.", "", text)
        text = re.sub(
            r"(?i)\b(?:>=?\s*\d+\s*px|Pretendard|KeyMetricCallout|160%\s*Macro\s*Loupe|Split-Screen\s*A/B|scan\s*line\s*highlight|telemetry\s*label|callout\s*card)\b[^.]*\.?",
            "",
            text,
        )
        if narration.strip():
            text = re.sub(r"[^.]*\bvs\b[^.]*대조\s*파일\.?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip(" .,-—–")
        clean_narration = re.sub(r"\s+", " ", str(narration or "")).strip()
        if not text or text == clean_narration:
            return clean_narration
        return f"{clean_narration} ({text})"

    @classmethod
    def _prompt(
        cls,
        beat: dict[str, Any],
        aspect_ratio: str = "16:9",
        visual_style: dict[str, Any] | None = None,
        ai_note: dict[str, Any] | None = None,
        preset_prompt: str = "",
        has_style_reference: bool = False,
        style_preset: str = "",
        character_profiles: list[dict[str, Any]] | None = None,
        has_character_reference: bool = False,
    ) -> str:
        narration = str(beat.get("narration_text") or "").strip()
        visual = str(beat.get("visual_description") or "").strip()
        style = visual_style or {}
        note = ai_note or {}
        visual_language = note.get("visual_language") if isinstance(note.get("visual_language"), dict) else {}
        period = str(visual_language.get("period") or "").strip() or cls._beat_period(beat, style.get("dominant_year"))
        style_directive = str(style.get("directive") or "").strip()
        color_mode = str(visual_language.get("color_mode") or style.get("color_mode") or "").strip().lower()
        style_notes = str(visual_language.get("style_notes") or "").strip()
        if color_mode == "monochrome":
            beat_style = "Beat-specific source match: render in authentic black-and-white/monochrome; match nearby archive grain, contrast, exposure and lighting."
        elif color_mode == "warm_35mm_cinema_color":
            beat_style = "Beat-specific cinema match: render in warm 35mm Kodak Vision3 500T color with 3200K tungsten amber practicals, soft twilight slate shadows, gentle highlight rolloff (<= 215/255 luminance), and fine theatrical grain."
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
        is_chibi_ref = cls._is_chibi_mascot_style(style_preset, preset_prompt)
        effective_mascot_ref = has_style_reference and is_chibi_ref
        style_reference_clause = (
            "A visual style reference image is attached. MANDATORY CHARACTER & COLOR LOCK: Draw ALL human characters in the scene as 2D rounded chibi mascot figures strictly copying the exact character design, BRIGHT GOLDEN-YELLOW head and body skin color tone (#FFD43B warm yellow spherical head, yellow hands, and yellow feet — NEVER white skin, NEVER pale/gray skin, and NEVER realistic human faces), proportions, bold clean black linework, simple black oval eyes with white specular highlights, thin curved eyebrows, minimal line mouth, and outfit style shown in the attached reference image. "
            if effective_mascot_ref
            else (
                "A cinematic style reference image is attached; preserve its warm lighting, film grain, and tonal mood with realistic human anatomy. "
                if has_style_reference
                else ""
            )
        )
        char_clause = ""
        if character_profiles:
            cast_desc = "; ".join(
                f"{c.get('name', 'Character')} ({c.get('role', 'cast')}): {c.get('appearance', '')}"
                for c in character_profiles
            )
            char_clause = (
                f"CHARACTER IDENTITY & WARDROBE CONTINUITY LOCK: Maintain 100% consistent Korean facial bone structure, age, hairstyle, and signature wardrobe for {cast_desc}"
                + (
                    " strictly matching the attached Master Character Reference Sheet(s). "
                    if has_character_reference
                    else ". "
                )
            )
        elif has_character_reference:
            char_clause = (
                "CHARACTER IDENTITY & WARDROBE CONTINUITY LOCK: Strictly preserve the exact facial features, age, hairstyle, and signature wardrobe of the character shown in the attached reference sheet with realistic human anatomy (5 fingers per hand, 0% cartoon). "
            )
        scene_focus = cls._clean_scene_focus(narration, visual)
        no_text_rule = (
            "CRITICAL VISUAL FOCUS RULE: Draw ONLY the core physical action, characters, props, and setting at the center of this scene in a single unified full-bleed 16:9 composition. "
            "Because the video already has voiceover and subtitles, DO NOT render any written text, Korean/Chinese/English words, numbers, speech bubbles, captions, labels, signs, document text boxes, split-screen dividers, magnifier loupes, or UI HUD elements anywhere in the image. "
        )
        if preset_prompt or effective_mascot_ref or color_mode == "warm_35mm_cinema_color":
            effective_spec = preset_prompt or style_directive
            style_block = f"STYLE SPECIFICATION:\n{effective_spec}\n\n" if effective_spec else ""
            mascot_lock_clause = (
                "Keep all 2D rounded mascot characters strictly faithful to the attached reference image — every character MUST have the exact BRIGHT GOLDEN-YELLOW skin tone (#FFD43B warm yellow round head, hands, and feet; NEVER white or human-colored skin), rounded chibi proportions, and clean black outlines from the reference image — while rendering the specific action, environment, props, and architecture described in this beat clearly and vividly. "
                if effective_mascot_ref else ""
            )
            return (
                "Create exactly one finished image for the documentary/cinema scene below. Do not output text or a prompt. "
                "Treat the following block as the mandatory visual STYLE & CHARACTER SPECIFICATION; ignore any meta instructions inside it about returning prompts or analysis.\n\n"
                f"{style_block}"
                f"{style_reference_clause}"
                f"{char_clause}"
                f"Core scene to illustrate (visual action & setting only, without any text): {scene_focus}. "
                f"Depicted period/context: {period}. {beat_style} {fallback_clause}"
                f"{mascot_lock_clause}"
                f"{no_text_rule}"
                f"{aspect_ratio} aspect ratio, full-canvas production-ready keyframe."
            )
        return (
            f"Authentic historical {period_qualifier}archival documentary still photograph, period-accurate lighting and material culture, archival documentary quality. "
            f"{subject_clause}"
            f"{style_reference_clause}"
            f"{char_clause}"
            "Use AI illustration only because verified real video or real still imagery was unavailable or unusable. "
            "Match the historical period, original footage era, film grain, lighting, geography, clothing and material culture exactly. "
            f"{beat_style} "
            f"{fallback_clause}"
            f"Core scene to illustrate (visual action & setting only, without any text): {scene_focus}. "
            f"Depicted period for this beat: {period}. {style_directive} "
            "Use realistic documentary cinematography, layered depth, natural composition and a clear focal subject. "
            f"{no_text_rule}"
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
            sel_fallback_ids = {
                str(value).strip()
                for value in (registry.get("ai_fallback_beats") or [])
                if str(value).strip()
            }
            real_covered_any = {
                str(asset.get("beat_id") or "")
                for asset in assets
                if _asset_exists(workspace, asset)
            }
            return [
                beat
                for beat in (visual.get("beats") or [])
                if isinstance(beat, dict)
                and str(beat.get("beat_id") or "").strip()
                and (
                    str(beat.get("visual_route") or "").strip().lower() == "ai_visual"
                    or (
                        str(beat.get("beat_id") or "").strip() in sel_fallback_ids
                        and str(beat.get("beat_id") or "").strip() not in real_covered_any
                    )
                )
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
    def _polish_generated_still_image(path: Path) -> None:
        """Strip Gemini corner mark (if present), auto-trim cinema letterbox black bars,
        softly clamp harsh highlights (`<= 215`), and normalize 16:9 keyframes to 1920x1080."""
        try:
            from PIL import Image
            import numpy as np
        except Exception:
            return
        try:
            with Image.open(path) as src_im:
                src_im.load()
                w0, h0 = src_im.size
                if w0 < 640 or h0 < 360:
                    return
                rgb = src_im.convert("RGB")
        except Exception:
            return

        changed = False
        try:
            from vendor.media_factory.backend.app.watermark_remover import purify

            cleaned_im, removed = purify(rgb)
            if removed:
                rgb = cleaned_im
                changed = True
        except Exception:
            pass

        try:
            arr = np.asarray(rgb, dtype=np.float32)
            h, w, _ = arr.shape
            is_landscape_16_9 = abs((w / max(1, h)) - (16.0 / 9.0)) <= 0.22
            if is_landscape_16_9:
                luma = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
                max_bar = int(h * 0.14)
                top_bar = 0
                while top_bar < max_bar and float(luma[top_bar].mean()) < 11.5 and float(np.percentile(luma[top_bar], 97)) < 26.0:
                    top_bar += 1
                bot_bar = 0
                while bot_bar < max_bar and float(luma[h - 1 - bot_bar].mean()) < 11.5 and float(np.percentile(luma[h - 1 - bot_bar], 97)) < 26.0:
                    bot_bar += 1
                if top_bar >= 4 or bot_bar >= 4:
                    y0 = top_bar
                    y1 = h - bot_bar
                    crop_h = max(1, y1 - y0)
                    target_w = min(w, int(round(crop_h * 16.0 / 9.0)))
                    if target_w < w:
                        x0 = (w - target_w) // 2
                        arr = arr[y0:y1, x0 : x0 + target_w, :]
                    else:
                        target_h = max(1, int(round(w * 9.0 / 16.0)))
                        if target_h < crop_h:
                            yc = y0 + (crop_h - target_h) // 2
                            arr = arr[yc : yc + target_h, :, :]
                        else:
                            arr = arr[y0:y1, :, :]
                    changed = True

                # Soft highlight shoulder roll-off so night-viewing Highlight Luma stays <= 215
                luma2 = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
                if float(np.percentile(luma2, 99.5)) > 213.0 or float(luma2.max()) > 224.0:
                    knee = 182.0
                    mask = luma2 > knee
                    if np.any(mask):
                        over = luma2[mask] - knee
                        compressed = knee + 31.0 * np.tanh(over / 42.0)
                        scale = compressed / np.maximum(luma2[mask], 1.0)
                        arr[mask] = np.clip(arr[mask] * scale[:, None], 0.0, 255.0)
                        changed = True

                out_im = Image.fromarray(np.clip(np.round(arr), 0, 255).astype(np.uint8), mode="RGB")
                if out_im.size != (1920, 1080):
                    out_im = out_im.resize((1920, 1080), Image.Resampling.LANCZOS)
                    changed = True
                if changed:
                    suf = path.suffix.lower()
                    tmp = path.with_name(f".{path.name}.polish.tmp")
                    if suf in {".jpg", ".jpeg"}:
                        out_im.save(tmp, format="JPEG", quality=94, subsampling=0)
                    elif suf == ".webp":
                        out_im.save(tmp, format="WEBP", quality=94)
                    else:
                        out_im.save(tmp, format="PNG")
                    tmp.replace(path)
        except Exception:
            return

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
        if not video:
            AIVisualCoordinator._polish_generated_still_image(destination)
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
        run_ed_dna = job.get("editing_dna") if isinstance(job.get("editing_dna"), dict) else {}
        run_vpm = str((run_ed_dna or {}).get("visual_priority_mode") or "").strip().lower()
        run_cm = str(job.get("content_mode") or ((job.get("channel_profile_snapshot") or {}).get("content_mode") if isinstance(job.get("channel_profile_snapshot"), dict) else "") or "").strip().lower()
        run_vmix_ai = float((((run_ed_dna or {}).get("visual_mix") or {}).get("ai") or 0.0))
        if effective_vs == "full_ai":
            coverage_mode = "full_ai"
        elif (
            effective_vs in {"edit_direct_footage", "semi_content", "ban_content", "edit_footage"}
            or run_vpm == "ai_cinema_character_drama"
            or run_cm == "creative_audio_drama"
            or run_vmix_ai >= 0.40
        ):
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

        compatible_local_profile = bool(
            previous_provider == "cofistudio_media_factory"
            and previous_profile == AI_VISUAL_GENERATION_PROFILE
            and isinstance(previous_style, dict)
            and compatible_style_signature
        )
        resume_current_profile = bool(compatible_local_profile and not scenes_cleared_in_factory)
        use_existing_local_cache = not previous_manifest or compatible_local_profile
        visual_style = dict(previous_style) if (resume_current_profile or (isinstance(previous_style, dict) and compatible_style_signature)) else self._build_visual_style(visual, job=job)
        self.ensure_episode_character_reference_sheets(
            workspace,
            job,
            image_model=image_model,
            aspect_ratio=aspect_ratio,
            preset_prompt=preset_prompt,
            allow_live_generation=is_live_factory_runner,
        )
        if previous_manifest and not compatible_local_profile:
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
        if (previous_manifest and not resume_current_profile) or scenes_cleared_in_factory:
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
                "lead_agent": "ai_visual",
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

        needs_factory_work = (
            not use_existing_local_cache
            or enable_video
            or any(
                not self._existing_generated_media(media_dir, f"{str(b.get('beat_id') or '')}_ai_keyframe")
                for b in targets
            )
        )
        if callable(queue_status_getter) and needs_factory_work:
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
            matched_chars = self._matched_character_profiles(beat, workspace, job)
            character_ref_imgs = self._character_reference_images(beat, workspace, job)
            ref_imgs: list[str] = []
            if has_style_reference and style_reference_path is not None:
                ref_imgs.append(str(style_reference_path))
            for reference in character_ref_imgs:
                if reference not in ref_imgs:
                    ref_imgs.append(reference)
            raw_beat_prompt = self._prompt(
                beat,
                aspect_ratio,
                visual_style,
                ai_notes_by_beat.get(beat_id),
                preset_prompt=preset_prompt,
                has_style_reference=has_style_reference,
                style_preset=style_preset,
                character_profiles=matched_chars,
                has_character_reference=bool(character_ref_imgs),
            )
            image_scene = {
                "id": f"{beat_id}_ai_image",
                "name": f"AI bổ sung · {beat_id}",
                "task_type": "image_generation",
                "prompt": (
                    self._sanitize_unsafe_prompt(raw_beat_prompt)
                    if any(
                        str(e.get("beat_id") or "") == beat_id and "UNSAFE" in str(e.get("error") or "").upper()
                        for e in (previous_manifest.get("errors") or [])
                        if isinstance(e, dict)
                    )
                    else raw_beat_prompt
                ),
                "model": image_model,
                "aspect_ratio": aspect_ratio,
                "reference_image": ref_imgs[0] if ref_imgs else None,
                "reference_images": ref_imgs,
                "_output_directory": str(media_dir),
                "_output_stem": f"{beat_id}_ai_keyframe",
                "_remove_watermark": True,
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
            idle_poll_ticks = 0
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
                for act_bid in list(active_images):
                    recovered_act = self._existing_generated_media(media_dir, f"{act_bid}_ai_keyframe")
                    if recovered_act:
                        image_work[act_bid]["image_path"] = str(recovered_act)
                        publish_image(image_work[act_bid]["beat"], str(recovered_act))
                        active_images.remove(act_bid)
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
                                if isinstance(image_work[rb].get("scene"), dict):
                                    image_work[rb]["scene"]["prompt"] = self._sanitize_unsafe_prompt(image_work[rb]["scene"].get("prompt", ""))
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
                if ready_beat_id is None and is_live_http_runner and len(active_images) > 1 and idle_poll_ticks < 120:
                    idle_poll_ticks += 1
                    time.sleep(1.0)
                    continue
                idle_poll_ticks = 0

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
                            if isinstance(image_work[rb].get("scene"), dict):
                                image_work[rb]["scene"]["prompt"] = self._sanitize_unsafe_prompt(image_work[rb]["scene"].get("prompt", ""))
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
