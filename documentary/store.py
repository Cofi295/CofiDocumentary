from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
from threading import RLock
from typing import Any
from uuid import uuid4

from .models import PHASES, phase_state


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._cache: dict[str, tuple[int, int, dict[str, Any]]] = {}

    def _path(self, job_id: str) -> Path:
        return self.root / job_id / "job.json"

    def _read_cached(self, path: Path) -> dict[str, Any]:
        key = str(path)
        st = path.stat()
        sig_mtime = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
        sig_size = int(st.st_size)
        cached = self._cache.get(key)
        if cached is not None and cached[0] == sig_mtime and cached[1] == sig_size:
            return copy.deepcopy(cached[2])
        normalized = self._normalize_job(json.loads(path.read_text(encoding="utf-8")))
        self._cache[key] = (sig_mtime, sig_size, copy.deepcopy(normalized))
        return normalized

    def _write(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=path.parent,
            suffix=".tmp",
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            temp_name = handle.name
        os.replace(temp_name, path)
        try:
            st = path.stat()
            sig_mtime = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))
            sig_size = int(st.st_size)
            normalized = self._normalize_job(copy.deepcopy(payload))
            self._cache[str(path)] = (sig_mtime, sig_size, copy.deepcopy(normalized))
        except OSError:
            self._cache.pop(str(path), None)

    @staticmethod
    def _normalize_job(job: dict[str, Any]) -> dict[str, Any]:
        raw_phases = job.get("phases")
        phases = dict(raw_phases) if isinstance(raw_phases, dict) else {}
        normalized: dict[str, Any] = {}
        for phase in PHASES:
            current = dict(phase_state())
            if isinstance(phases.get(phase), dict):
                current.update(phases[phase])
            elif phase == "visuals" and any(
                isinstance(phases.get(later), dict)
                and str(phases[later].get("status") or "") in {"succeeded", "running", "interrupted", "failed", "queued"}
                for later in ("footage", "ai_visual", "edit", "seo", "qc")
            ):
                current.update({
                    "status": "succeeded",
                    "last_message": "Legacy project: Visuals/STP was introduced after this project had already reached visual production.",
                })
            elif phase == "seo" and isinstance(phases.get("qc"), dict) and phases["qc"].get("status") == "succeeded":
                current.update({
                    "status": "succeeded",
                    "last_message": "Legacy project: SEO + Thumbnail was introduced after this project had already completed.",
                })
            elif phase == "ai_visual" and any(
                isinstance(phases.get(later), dict) and phases[later].get("status") == "succeeded"
                for later in ("edit", "qc")
            ):
                current.update({
                    "status": "succeeded",
                    "last_message": "Legacy project: AI Visual step was introduced after this phase had already passed.",
                })
            normalized[phase] = current
        legacy = {key: value for key, value in phases.items() if key not in PHASES}
        job["phases"] = normalized
        if legacy:
            job.setdefault("legacy_phases", {}).update(legacy)
        job.setdefault("plan_engine", "codex")
        job.setdefault("footage_mode", "vision_codex")
        strategy = str(job.get("visual_strategy") or "full_footage").strip().lower()
        if strategy == "footage_first":
            strategy = "full_footage"
        elif strategy in {"selective_footage", "evidence_first"}:
            strategy = "evidence_footage"
        elif strategy in {"semi_content", "ban_content", "edit_footage"}:
            strategy = "edit_direct_footage"
        if strategy not in {"full_ai", "full_footage", "hybrid", "evidence_footage", "edit_direct_footage"}:
            strategy = "full_footage"
        job["visual_strategy"] = strategy
        if str(job.get("current_phase") or "") == "footage":
            job["current_phase"] = "edit" if strategy == "full_footage" else "ai_visual"
        job.setdefault("ai_media_mode", "mixed")
        job.setdefault("ai_visual", {})
        job.setdefault("voice", {})
        job.setdefault("editing_dna", {})
        job.setdefault("default_creative_brief", {})
        job.setdefault("creative_brief", {})
        target_mins = job.get("target_duration_minutes")
        if target_mins not in (None, ""):
            try:
                expected_sec = round(float(target_mins) * 60)
                recipe = job.get("production_recipe")
                edna = job.get("editing_dna") if isinstance(job.get("editing_dna"), dict) else {}
                vox_preset = str(edna.get("preset_id") or edna.get("editing_dna_preset") or "").strip()
                is_vox = vox_preset in {"forensic_noir_director_v2", "vox_china_crime_newsroom_v10"} or (
                    str(edna.get("director_mode") or "").strip().lower() in {"v2", "vox_china_crime_newsroom_v10"}
                )
                vox_mismatch = is_vox and isinstance(recipe, dict) and (
                    str((recipe.get("quality_contract") or {}).get("visual_routing_policy") or "") != "vox_newsroom_v13_composable_lego_50pct_footage"
                )
                if not isinstance(recipe, dict) or not recipe.get("quality_contract") or abs(float(recipe.get("target_duration_sec") or 0) - expected_sec) > 1 or vox_mismatch:
                    from .quality import normalize_production_recipe
                    job["production_recipe"] = normalize_production_recipe(
                        recipe if isinstance(recipe, dict) else None,
                        target_duration_minutes=target_mins,
                        visual_strategy=strategy,
                        editing_dna=edna,
                    )
            except Exception:
                pass
        return job

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            job_id = str(payload.get("id") or f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}")
            stamp = _now()
            job = {
                "id": job_id,
                "title": str(payload.get("title") or "").strip(),
                "topic": str(payload.get("topic") or payload.get("title") or "").strip(),
                "source_url": payload.get("source_url"),
                "market": payload.get("market") or "KR",
                "language": payload.get("language") or "ko",
                "notes": payload.get("notes") or "",
                "production_recipe": payload.get("production_recipe") or {},
                "plan_engine": payload.get("plan_engine") or "codex",
                "footage_mode": payload.get("footage_mode") or "vision_codex",
                "visual_strategy": payload.get("visual_strategy") or "full_footage",
                "ai_media_mode": payload.get("ai_media_mode") or "mixed",
                "ai_visual": payload.get("ai_visual") or {},
                "voice": payload.get("voice") or {},
                "radar": payload.get("radar"),
                "topic_discovery": payload.get("topic_discovery") or {},
                "channel_profile_id": payload.get("channel_profile_id"),
                "channel_profile_snapshot": payload.get("channel_profile_snapshot") or {},
                "channel_plan_item_id": payload.get("channel_plan_item_id"),
                "editing_dna": payload.get("editing_dna") or {},
                "default_creative_brief": payload.get("default_creative_brief") or {},
                "creative_brief": payload.get("creative_brief") or payload.get("default_creative_brief") or {},
                "editorial_dna": payload.get("editorial_dna") or {},
                "self_learning_memory": payload.get("self_learning_memory") or {},
                "workspace": str(payload.get("workspace") or ""),
                "workspace_root": str(payload.get("workspace_root") or ""),
                "status": "ready",
                "current_phase": None,
                "created_at": stamp,
                "updated_at": stamp,
                "phases": {phase: phase_state() for phase in PHASES},
            }
            for k, v in payload.items():
                if k not in job:
                    job[k] = v
            self._write(self._path(job_id), job)
            return self._normalize_job(job)

    def get(self, job_id: str) -> dict[str, Any] | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        with self._lock:
            try:
                return self._read_cached(path)
            except (OSError, json.JSONDecodeError, ValueError):
                return None

    def update(self, job_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            job = self.get(job_id)
            if job is None:
                raise KeyError(job_id)
            for key, value in patch.items():
                if key == "phases":
                    if isinstance(value, dict):
                        phases = dict(job.get("phases") or {})
                        for phase, phase_patch in value.items():
                            current = dict(phases.get(phase) or phase_state())
                            if isinstance(phase_patch, dict):
                                current.update(phase_patch)
                            else:
                                current = phase_patch
                            phases[phase] = current
                        job["phases"] = phases
                    else:
                        raise ValueError("phases must be a dictionary")
                else:
                    job[key] = value
            if job.get("status") in {"running", "queued"} or any(
                isinstance(st, dict) and st.get("status") in {"running", "queued"}
                for st in (job.get("phases") or {}).values()
            ):
                job["owner_pid"] = os.getpid()
            job["updated_at"] = _now()
            self._write(self._path(job_id), job)
            return job

    def delete(self, job_id: str) -> bool:
        with self._lock:
            path = self._path(job_id)
            self._cache.pop(str(path), None)
            job_dir = path.parent
            if not job_dir.exists():
                return False
            shutil.rmtree(job_dir)
            return True

    @staticmethod
    def _is_job_worker_still_active(job: dict[str, Any], root_dir: Path) -> bool:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return False
        owner_pid = job.get("owner_pid")
        if owner_pid and int(owner_pid) > 0 and int(owner_pid) != os.getpid():
            try:
                from COFI_BRAIN.chat_run_manager import _pid_is_alive
                if _pid_is_alive(int(owner_pid)):
                    return True
            except Exception:
                pass
        ws_raw = str(job.get("workspace") or "").strip()
        ws = Path(ws_raw) if ws_raw else (root_dir.parent.parent / "workspaces" / str(job.get("id") or ""))
        prod_dir = ws / ".producer"
        if prod_dir.is_dir():
            import time as _time
            now_ts = _time.time()
            try:
                for ev_file in prod_dir.glob("*/events.jsonl"):
                    if now_ts - ev_file.stat().st_mtime < 300:
                        return True
            except OSError:
                pass
        return False

    def recover_interrupted(self) -> list[str]:
        recovered: list[str] = []
        for path in self.root.glob("*/job.json"):
            try:
                job = self._read_cached(path)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            has_running = job.get("status") in {"running", "queued"} or any(
                isinstance(state, dict) and state.get("status") in {"running", "queued"}
                for state in (job.get("phases") or {}).values()
            )
            if has_running and self._is_job_worker_still_active(job, self.root):
                continue
            changed = False
            for phase, state in job["phases"].items():
                if state.get("status") in {"running", "queued"}:
                    state["status"] = "interrupted"
                    state["error"] = "Phiên trước bị ngắt. Có thể tiếp tục từ checkpoint hiện có."
                    changed = True
            if job.get("status") in {"running", "queued"}:
                job["status"] = "interrupted"
                changed = True
            if changed:
                job["updated_at"] = _now()
                self._write(path, job)
                recovered.append(str(job.get("id") or path.parent.name))
        return recovered

    def list(self) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        with self._lock:
            for path in self.root.glob("*/job.json"):
                try:
                    jobs.append(self._read_cached(path))
                except (OSError, json.JSONDecodeError, ValueError):
                    continue
        jobs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return jobs

