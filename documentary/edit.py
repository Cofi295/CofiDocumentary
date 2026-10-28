from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from .codex_gateway import StageResult
from .edit_footage_fetcher import EditDirectFootageFetcher
from .prompts import build_edit_batch_prompt


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _positive_int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _nonnegative_int_env(name: str, default: int = 0) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _beat_id(beat: dict[str, Any]) -> str:
    return str(beat.get("beat_id") or "").strip()


def _chunks(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def _beat_duration(beat: dict[str, Any]) -> float:
    for key in ("duration_sec", "target_duration_sec", "estimated_duration_sec"):
        try:
            value = float(beat.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    return 0.0


def _duration_target_chunks(
    items: list[dict[str, Any]],
    max_items: int,
    target_duration_sec: int,
    max_duration_sec: int,
) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_duration = 0.0
    for item in items:
        duration = _beat_duration(item)
        would_exceed_items = bool(max_items > 0 and len(current) >= max_items)
        would_exceed_hard_max = bool(
            current
            and max_duration_sec > 0
            and current_duration + duration > max_duration_sec
        )
        if current and (would_exceed_items or would_exceed_hard_max):
            batches.append(current)
            current = []
            current_duration = 0.0
        current.append(item)
        current_duration += duration
        # The default duration is a soft target, not a hard cut. Finish the
        # batch only after a complete beat crosses the target so a long shot /
        # narration beat is never split merely to land exactly on five minutes.
        if target_duration_sec > 0 and current_duration >= target_duration_sec:
            batches.append(current)
            current = []
            current_duration = 0.0
    if current:
        batches.append(current)
    return batches


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class EditCoordinator:
    TRANSIENT_FAILURE_MARKERS = (
        "connection",
        "disconnected",
        "network",
        "transport",
        "timeout",
        "timed out",
        "socket",
        "connection reset",
        "stream closed",
        "unexpected eof",
        "broken pipe",
        "temporarily unavailable",
        "context window",
        "context length",
        "maximum context",
        "conversation too long",
        "token limit",
    )

    def __init__(
        self,
        codex_gateway: Any,
        remotion_manager: Any,
        remotion_dir: str | Path,
        *,
        render_cache: Any | None = None,
        batch_size: int | None = None,
        batch_target_duration_sec: int | None = None,
        batch_max_duration_sec: int | None = None,
        batch_retries: int | None = None,
    ):
        self.codex_gateway = codex_gateway
        self.remotion_manager = remotion_manager
        self.remotion_dir = Path(remotion_dir).resolve()
        self.render_cache = render_cache
        self.batch_size = (
            max(0, int(batch_size))
            if batch_size is not None
            else _nonnegative_int_env("COFI_EDIT_BATCH_SIZE", 0)
        )
        self.batch_target_duration_sec = max(
            0,
            int(
                batch_target_duration_sec
                if batch_target_duration_sec is not None
                else _nonnegative_int_env("COFI_EDIT_BATCH_TARGET_DURATION_SEC", 0)
            ),
        )
        self.batch_max_duration_sec = (
            max(0, int(batch_max_duration_sec))
            if batch_max_duration_sec is not None
            else _nonnegative_int_env("COFI_EDIT_BATCH_MAX_DURATION_SEC", 0)
        )
        self.batch_retries = max(0, int(batch_retries if batch_retries is not None else _positive_int_env("COFI_EDIT_BATCH_RETRIES", 2, minimum=0)))

    def _batches(self, beats: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        return _duration_target_chunks(
            beats,
            self.batch_size,
            self.batch_target_duration_sec,
            self.batch_max_duration_sec,
        )

    @staticmethod
    def _progress_path(workspace: Path) -> Path:
        return workspace / "edit_progress.json"

    def _new_progress(self, beats: list[dict[str, Any]]) -> dict[str, Any]:
        assigned = [_beat_id(beat) for beat in beats if _beat_id(beat)]
        continuous = not any((self.batch_size, self.batch_target_duration_sec, self.batch_max_duration_sec))
        return {
            "version": 1,
            "status": "running" if assigned else "completed",
            "batch_size": self.batch_size,
            "batch_target_duration_sec": self.batch_target_duration_sec,
            "batch_max_duration_sec": self.batch_max_duration_sec,
            "assigned_beat_ids": assigned,
            "completed_beat_ids": [],
            "pending_beat_ids": assigned,
            "total_beats": len(assigned),
            "completed_beats": 0,
            "current_batch": 0,
            "total_batches": len(self._batches(beats)),
            "attempts": 0,
            "session_rotations": 0,
            "last_error": "",
            "last_checkpoint_at": None,
            "status_message": (
                "Chuẩn bị dựng liên tục đến hết video; tiến trình được lưu theo từng beat."
                if continuous
                else "Chuẩn bị dựng video theo các giới hạn batch đã cấu hình."
            ),
            "updated_at": _now(),
        }

    def _load_or_initialize_progress(self, workspace: Path, beats: list[dict[str, Any]]) -> dict[str, Any]:
        current = self._new_progress(beats)
        path = self._progress_path(workspace)
        previous: dict[str, Any] = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    previous = loaded
            except (OSError, json.JSONDecodeError):
                previous = {}
        if previous.get("version") == 1 and previous.get("assigned_beat_ids") == current["assigned_beat_ids"]:
            completed = [
                str(value)
                for value in (previous.get("completed_beat_ids") or [])
                if str(value) in current["assigned_beat_ids"]
            ]
            current["completed_beat_ids"] = list(dict.fromkeys(completed))
            for key in ("attempts", "session_rotations", "last_error", "last_checkpoint_at"):
                if key in previous:
                    current[key] = previous[key]
        self._save_progress(workspace, current)
        return current

    def _save_progress(self, workspace: Path, progress: dict[str, Any]) -> None:
        assigned = [str(value) for value in (progress.get("assigned_beat_ids") or [])]
        completed = [str(value) for value in (progress.get("completed_beat_ids") or []) if str(value) in assigned]
        progress["completed_beat_ids"] = list(dict.fromkeys(completed))
        progress["pending_beat_ids"] = [beat_id for beat_id in assigned if beat_id not in progress["completed_beat_ids"]]
        progress["completed_beats"] = len(progress["completed_beat_ids"])
        progress["total_beats"] = len(assigned)
        progress["updated_at"] = _now()
        if not progress["pending_beat_ids"]:
            progress["status"] = "completed"
        _write_json_atomic(self._progress_path(workspace), progress)

    def _sync_completed_from_disk(self, workspace: Path, progress: dict[str, Any]) -> None:
        """Merge beat-level progress written by the live editor into coordinator state."""
        path = self._progress_path(workspace)
        try:
            latest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(latest, dict):
            return
        assigned = [str(value) for value in (progress.get("assigned_beat_ids") or [])]
        if latest.get("version") != 1 or latest.get("assigned_beat_ids") != assigned:
            return
        completed = [str(value) for value in (progress.get("completed_beat_ids") or []) if str(value) in assigned]
        completed.extend(
            str(value)
            for value in (latest.get("completed_beat_ids") or [])
            if str(value) in assigned
        )
        progress["completed_beat_ids"] = list(dict.fromkeys(completed))
        latest_checkpoint = latest.get("last_checkpoint_at")
        if latest_checkpoint:
            progress["last_checkpoint_at"] = latest_checkpoint
        self._save_progress(workspace, progress)

    def _is_transient_failure(self, result: StageResult) -> bool:
        message = str(result.last_message or "").strip().lower()
        if not message:
            return True
        return any(marker in message for marker in self.TRANSIENT_FAILURE_MARKERS)

    def _run_batch_prompt(self, job: dict[str, Any], workspace: Path, prompt: str) -> StageResult:
        reusable = getattr(self.codex_gateway, "run_prompt_reusable", None)
        if callable(reusable):
            return reusable(prompt, workspace, "edit", use_remotion_root=True)
        runner = getattr(self.codex_gateway, "run_prompt", None)
        if callable(runner):
            return runner(prompt, workspace, "edit", use_remotion_root=True)
        return self.codex_gateway.run(job, "edit", workspace)

    def _checkpoint(self, job: dict[str, Any], workspace: Path, progress: dict[str, Any], note: str) -> None:
        checkpoint = self.remotion_manager.checkpoint(job, workspace, note=note)
        progress["last_checkpoint_at"] = checkpoint.get("saved_at") if isinstance(checkpoint, dict) else _now()
        self._save_progress(workspace, progress)

    def run(self, job: dict[str, Any], workspace: str | Path) -> StageResult:
        workspace = Path(workspace).resolve()
        visual_path = workspace / "visual_manifest.json"
        try:
            visual = json.loads(visual_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Không đọc được visual_manifest.json để dựng theo batch: {exc}") from exc
        beats = [item for item in (visual.get("beats") or []) if isinstance(item, dict) and _beat_id(item)]
        if not beats:
            raise RuntimeError("visual_manifest.json không có beat hợp lệ để dựng")

        from .vox_engine import VoxBlenderBridge, VoxSemanticRouter, is_vox_satellite_enabled
        from .financial_vox_engine import FinancialVoxSemanticRouter, is_financial_vox_enabled
        vox_enabled = is_vox_satellite_enabled(job)
        fin_vox_enabled = is_financial_vox_enabled(job)
        if vox_enabled and any(not b.get("scene_archetype") or not b.get("dna_visual_slot") for b in beats):
            router = VoxSemanticRouter()
            beats = router.route_timeline(beats, job)
            visual["beats"] = beats
            _write_json_atomic(visual_path, visual)
        elif fin_vox_enabled and any(not b.get("scene_archetype") or not b.get("dna_visual_slot") for b in beats):
            fin_router = FinancialVoxSemanticRouter()
            beats = fin_router.route_timeline(beats, job)
            visual["beats"] = beats
            _write_json_atomic(visual_path, visual)

        strategy = str(
            job.get("visual_strategy")
            or (job.get("production_recipe") or {}).get("visual_strategy")
            or ""
        ).strip().lower()
        profile_id = str(
            job.get("channel_profile_id")
            or ((job.get("channel_profile_snapshot") or {}).get("id") if isinstance(job.get("channel_profile_snapshot"), dict) else "")
            or ""
        ).strip()
        if (
            strategy in {"edit_direct_footage", "semi_content", "ban_content", "edit_footage"}
            and profile_id != "channel-cn-cyber-finance-kr"
            and os.getenv("COFI_EDIT_AUTO_FETCH_FOOTAGE", "1") != "0"
            and (self.remotion_dir / "package.json").exists()
        ):
            try:
                fetcher = EditDirectFootageFetcher(
                    workspace=workspace,
                    remotion_dir=self.remotion_dir,
                    job_id=str(job.get("id") or workspace.name),
                )
                fetcher.auto_fetch_missing_beats(job, max_unique_clips=48)
            except Exception:
                pass

        prepare_media = getattr(self.remotion_manager, "prepare_job_media", None)
        if callable(prepare_media):
            prepare_media(job, workspace)

        # Strict profile isolation: True Crime (channel-e544a64b7c) uses its finalized True Crime CofiBlenderStudio Vox & Satellite Engine;
        # never merge or share editing/Vox style across different channel profiles.
        if vox_enabled or fin_vox_enabled:
            job_id = str(job.get("id") or workspace.name).strip()
            bridge = VoxBlenderBridge()
            vox_context = bridge.materialize_job_vox_assets(
                job=job,
                workspace=workspace,
                beats=beats,
                remotion_dir=self.remotion_dir,
                render_plates=os.getenv("COFI_VOX_RENDER_PLATES", "1") != "0",
            )
            visual["beats"] = beats
            _write_json_atomic(visual_path, visual)
            _write_json_atomic(workspace / "vox_scene_manifest.json", vox_context)
            if self.remotion_dir:
                remotion_pub = Path(self.remotion_dir) / "public" / "jobs" / job_id
                if remotion_pub.exists():
                    _write_json_atomic(remotion_pub / "vox_scene_manifest.json", vox_context)

        status = self.remotion_manager.status()
        if status.get("ok"):
            self.remotion_manager.start_studio(job, workspace)
        else:
            self.remotion_manager.ensure_session(job, workspace)

        progress = self._load_or_initialize_progress(workspace, beats)
        completed = list(progress.get("completed_beat_ids") or [])
        completed_set = set(completed)
        batches = self._batches(beats)
        messages: list[str] = []
        self._checkpoint(job, workspace, progress, "Checkpoint trước khi Codex tiếp tục edit theo batch")
        if self.render_cache is not None:
            if getattr(self.render_cache, "render_during_edit", False):
                starter = getattr(self.render_cache, "start", None)
                if callable(starter):
                    starter(job, workspace, beats)
            else:
                preparer = getattr(self.render_cache, "prepare", None)
                if callable(preparer):
                    try:
                        preparer(job, workspace, beats)
                    except Exception:
                        pass

        for batch_index, batch in enumerate(batches, start=1):
            batch_ids = [_beat_id(beat) for beat in batch if _beat_id(beat)]
            if not any(beat_id not in completed_set for beat_id in batch_ids):
                continue

            result: StageResult | None = None
            expected_ids: list[str] = []
            for attempt in range(self.batch_retries + 1):
                # The editor saves completed beat IDs while it works. If a long
                # continuous turn disconnects, reload that durable progress before
                # reconnecting so the new Codex session skips already-finished work.
                self._sync_completed_from_disk(workspace, progress)
                completed = list(progress.get("completed_beat_ids") or [])
                completed_set = set(completed)
                pending_batch = [beat for beat in batch if _beat_id(beat) not in completed_set]
                expected_ids = [_beat_id(beat) for beat in pending_batch if _beat_id(beat)]
                if not expected_ids:
                    result = StageResult(0, "Beat-level checkpoint đã hoàn tất phần việc còn lại.", workspace / ".producer" / "edit")
                    break

                progress["current_batch"] = batch_index
                progress["status"] = "running"
                progress["last_error"] = ""
                progress["status_message"] = (
                    f"Đang dựng liên tục từ {expected_ids[0]} đến {expected_ids[-1]}"
                    if len(batches) == 1
                    else f"Đang dựng {', '.join(expected_ids)} · batch {batch_index}/{len(batches)}"
                )
                progress["attempts"] = int(progress.get("attempts") or 0) + 1
                self._save_progress(workspace, progress)
                prompt = build_edit_batch_prompt(
                    job,
                    workspace,
                    self.remotion_dir,
                    pending_batch,
                    completed_beat_ids=completed,
                    batch_index=batch_index,
                    total_batches=len(batches),
                )
                result = self._run_batch_prompt(job, workspace, prompt)
                if result.last_message:
                    messages.append(result.last_message)
                if result.returncode == 0:
                    completed.extend(beat_id for beat_id in expected_ids if beat_id not in completed_set)
                    completed_set.update(expected_ids)
                    progress["completed_beat_ids"] = completed
                    self._save_progress(workspace, progress)
                    break
                self._sync_completed_from_disk(workspace, progress)
                completed = list(progress.get("completed_beat_ids") or [])
                completed_set = set(completed)
                progress["last_error"] = result.last_message or "Codex bị ngắt trước khi hoàn tất batch Edit."
                progress["status_message"] = "Edit bị ngắt; đang kết nối lại từ beat chưa hoàn tất."
                self._save_progress(workspace, progress)
                if attempt >= self.batch_retries or not self._is_transient_failure(result):
                    progress["status"] = "failed"
                    self._save_progress(workspace, progress)
                    return result
                remaining_ids = [beat_id for beat_id in batch_ids if beat_id not in completed_set]
                progress["status_message"] = f"Đang tiếp tục từ {remaining_ids[0] if remaining_ids else 'checkpoint'} trong cùng phiên Codex."
                self._save_progress(workspace, progress)

            if result is None or result.returncode != 0:
                progress["status"] = "failed"
                self._save_progress(workspace, progress)
                return result or StageResult(1, "Edit batch failed", workspace / ".producer" / "edit")

            self._sync_completed_from_disk(workspace, progress)
            completed = list(progress.get("completed_beat_ids") or [])
            completed_set = set(completed)
            progress["last_error"] = ""
            progress["status_message"] = f"Đã dựng xong {len(completed)}/{len(beats)} beat · batch {batch_index}/{len(batches)}"
            self._checkpoint(
                job,
                workspace,
                progress,
                f"Đã hoàn tất Edit batch {batch_index}/{len(batches)}: {', '.join(batch_ids)}",
            )

            if batch_index < len(batches):
                progress["status_message"] = (
                    f"Đã chốt batch {batch_index}/{len(batches)}; "
                    "Codex sẽ tiếp tục batch kế tiếp trong cùng phiên từ checkpoint."
                )
                self._save_progress(workspace, progress)

        progress["current_batch"] = len(batches)
        progress["status"] = "completed"
        progress["status_message"] = f"Đã dựng xong {len(beats)}/{len(beats)} beat; preview sẵn sàng để duyệt."
        self._checkpoint(job, workspace, progress, "Bản dựng preview đã cập nhật; chờ người dùng duyệt trước khi xuất")
        if self.render_cache is not None and not getattr(self.render_cache, "render_during_edit", False):
            preparer = getattr(self.render_cache, "prepare", None)
            if callable(preparer):
                try:
                    preparer(job, workspace, beats)
                except Exception:
                    pass
        return StageResult(
            returncode=0,
            last_message="\n".join(message for message in messages if message)[-12000:],
            log_path=workspace / ".producer" / "edit",
        )
