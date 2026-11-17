from __future__ import annotations

import gc
import importlib
import os
from pathlib import Path
import sys
import threading
from threading import RLock
import time
from typing import Any

_LOCK = RLock()
_RELOADING = False
_INITIAL_SYNC_DONE = False
_WATCHER_STARTED = False
_MODULE_MTIMES: dict[str, float] = {}

_RELOAD_ORDER: tuple[str, ...] = (
    "COFI_BRAIN.chat_run_manager",
    "documentary.models",
    "documentary.store",
    "documentary.workspace_ledger",
    "documentary.srt",
    "documentary.cache_manager",
    "documentary.render_cache",
    "documentary.render_progress",
    "documentary.agent_manager",
    "documentary.nexus_coordinator",
    "documentary.agent_departments",
    "documentary.agent_office",
    "documentary.audio_library_manager",
    "documentary.vox_engine.typography",
    "documentary.vox_engine.archetypes",
    "documentary.vox_engine.composable_scene_graph",
    "documentary.vox_engine.semantic_router",
    "documentary.vox_engine",
    "documentary.financial_vox_engine",
    "services.voice_rhythm_specialist",
    "services.case_similarity",
    "documentary.topic_research",
    "services.editing_dna_service",
    "services.channel_profile_service",
    "documentary.editorial_voice_cutter",
    "documentary.visuals",
    "documentary.ai_visual",
    "documentary.footage",
    "documentary.thumbnail_studio",
    "documentary.prompts",
    "documentary.goal_session",
    "documentary.codex_gateway",
    "documentary.gemini_gateway",
    "documentary.failover_gateway",
    "documentary.edit_footage_fetcher",
    "documentary.edit",
    "documentary.voice",
    "documentary.quality",
    "services.job_service",
    "documentary.service",
    "documentary.critic_loops",
)


def _get_module_mtime(mod: Any) -> float | None:
    mod_file = getattr(mod, "__file__", None)
    if not mod_file:
        return None
    try:
        return Path(mod_file).stat().st_mtime
    except OSError:
        return None


def _hot_patch_live_webview_windows() -> int:
    patched = 0
    try:
        wv = sys.modules.get("webview")
        wins = list(getattr(wv, "windows", []) or []) if wv is not None else []
        if not wins:
            return 0
        js_patch = r"""
(function() {
  try {
    if (window.__cofiThumbNoFlickerPatchedV3) {
      const h = document.querySelector("#cofiThumbnailStudioHost");
      return "already_v3:" + (h ? h.children.length : 0) + ":" + Boolean(h && h.querySelector(".thumb-studio-card"));
    }
    window.__cofiThumbNoFlickerPatchedV3 = true;

    let activeMountPromise = null;
    let activeMountJobId = null;

    const origMount = window.mountCofiThumbnailStudio?.__origFn || window.mountCofiThumbnailStudio;
    if (typeof origMount === "function") {
      const wrappedMount = async function(jobId, hostElement, options = {}) {
        if (!jobId || !hostElement) return;
        const force = Boolean(options && options.force);
        hostElement.dataset.mountedJobId = String(jobId);
        if (!force && hostElement.querySelector(".thumb-studio-card") && activeMountJobId === String(jobId)) {
          return;
        }
        if (!force && activeMountPromise && activeMountJobId === String(jobId)) {
          return activeMountPromise;
        }
        activeMountJobId = String(jobId);
        activeMountPromise = (async () => {
          try {
            return await origMount.call(this, jobId, hostElement, options);
          } finally {
            activeMountPromise = null;
          }
        })();
        return activeMountPromise;
      };
      wrappedMount.__origFn = origMount;
      window.mountCofiThumbnailStudio = wrappedMount;
    }

    const origRenderSeo = window.renderSeoWorkspace?.__origFn || window.renderSeoWorkspace;
    if (typeof origRenderSeo === "function") {
      let seoInFlight = false;
      const wrappedRenderSeo = async function(job, opts = {}) {
        const root = document.querySelector("#seoWorkspace");
        if (!job || !root) return origRenderSeo.call(this, job, opts);
        const seoStatus = String(job.phases?.seo?.status || "pending");
        const prevSeoStatus = String(root.dataset.seoStatus || "");
        const justFinishedSeo = ["running", "queued"].includes(prevSeoStatus) && seoStatus === "succeeded";
        const existingHost = root.querySelector("#cofiThumbnailStudioHost");
        const alreadyMountedOrMounting = Boolean(
          existingHost
          && (
            existingHost.dataset.mountedJobId === String(job.id)
            || existingHost.querySelector(".thumb-studio-card")
            || activeMountJobId === String(job.id)
          )
          && existingHost.children.length > 0
        );
        if (!opts?.forceRemount && !justFinishedSeo && alreadyMountedOrMounting) {
          existingHost.dataset.mountedJobId = String(job.id);
          if (prevSeoStatus !== seoStatus && typeof window.phaseStepPanelHtml === "function") {
            const stepCard = root.querySelector(".step-status-card");
            if (stepCard) {
              stepCard.outerHTML = window.phaseStepPanelHtml(job, "seo", "qc");
              if (typeof window.bindWorkspacePhaseButtons === "function") {
                window.bindWorkspacePhaseButtons(job, root);
              }
            }
            root.dataset.seoStatus = seoStatus;
          }
          return;
        }
        if (seoInFlight || activeMountPromise) return;
        seoInFlight = true;
        try {
          root.dataset.seoStatus = seoStatus;
          await origRenderSeo.call(this, job, opts);
          const hostAfter = root.querySelector("#cofiThumbnailStudioHost");
          if (hostAfter) hostAfter.dataset.mountedJobId = String(job.id);
          if (activeMountPromise) await activeMountPromise;
        } finally {
          seoInFlight = false;
        }
      };
      wrappedRenderSeo.__origFn = origRenderSeo;
      window.renderSeoWorkspace = wrappedRenderSeo;
    }

    const curHost = document.querySelector("#cofiThumbnailStudioHost");
    if (curHost && typeof state === "object" && state?.selectedId) {
      curHost.dataset.mountedJobId = String(state.selectedId);
      activeMountJobId = String(state.selectedId);
    }
    return "patched_v3_ok";
  } catch (e) {
    return "err:" + String(e);
  }
})();
"""
        results = []
        for w in wins:
            try:
                res = w.evaluate_js(js_patch)
                results.append(str(res))
                patched += 1
            except Exception as exc:
                results.append(f"exc:{exc}")
        try:
            import json as _json
            status_file = Path(__file__).resolve().parent.parent / ".producer" / "webview_hotpatch.json"
            status_file.parent.mkdir(parents=True, exist_ok=True)
            status_file.write_text(
                _json.dumps({"patched": patched, "results": results, "timestamp": time.time()}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass
    except Exception:
        pass
    return patched


def _rebind_live_instances(reloaded_modules: dict[str, Any]) -> int:
    _hot_patch_live_webview_windows()
    if not reloaded_modules:
        return 0
    rebound = 0
    try:
        # Also refresh top-level imported functions in documentary.service / services.job_service
        qual_mod = sys.modules.get("documentary.quality")
        rc_mod = sys.modules.get("documentary.render_cache")
        svc_mod = sys.modules.get("documentary.service")
        job_svc_mod = sys.modules.get("services.job_service")
        if qual_mod is not None:
            for target_mod in (svc_mod, job_svc_mod):
                if target_mod is not None:
                    for sym in ("validate_phase_quality", "normalize_production_recipe"):
                        if hasattr(qual_mod, sym) and hasattr(target_mod, sym):
                            setattr(target_mod, sym, getattr(qual_mod, sym))
        if rc_mod is not None and svc_mod is not None:
            for sym in ("detect_hardware_profile", "BackgroundRenderCache"):
                if hasattr(rc_mod, sym) and hasattr(svc_mod, sym):
                    setattr(svc_mod, sym, getattr(rc_mod, sym))
        ts_mod = sys.modules.get("documentary.thumbnail_studio")
        if ts_mod is not None and svc_mod is not None:
            for sym in (
                "build_default_thumbnail_design",
                "discover_job_candidate_images",
                "render_design_thumbnails_to_disk",
                "enforce_seo_package_expert_rules",
                "evaluate_thumbnail_ctr",
                "sanitize_thumbnail_design_fonts",
            ):
                if hasattr(ts_mod, sym) and hasattr(svc_mod, sym):
                    setattr(svc_mod, sym, getattr(ts_mod, sym))
        prompts_mod = sys.modules.get("documentary.prompts")
        if prompts_mod is not None:
            prompt_targets = [
                svc_mod,
                sys.modules.get("documentary.codex_gateway"),
                sys.modules.get("documentary.gemini_gateway"),
                sys.modules.get("documentary.failover_gateway"),
                sys.modules.get("documentary.edit"),
            ]
            for target_mod in prompt_targets:
                if target_mod is None:
                    continue
                for sym in (
                    "build_phase_prompt",
                    "build_edit_chat_prompt",
                    "build_edit_batch_prompt",
                    "build_footage_eye_agent_prompt",
                    "build_goal_resume_prompt",
                    "build_producer_goal_prompt",
                    "build_producer_chat_prompt",
                    "build_producer_chat_continuation_prompt",
                    "build_producer_fast_control_prompt",
                    "build_producer_terminal_report_prompt",
                ):
                    if hasattr(prompts_mod, sym) and hasattr(target_mod, sym):
                        setattr(target_mod, sym, getattr(prompts_mod, sym))
        gs_mod = sys.modules.get("documentary.goal_session")
        if gs_mod is not None and svc_mod is not None:
            for sym in ("AntigravityGoalSession", "GoalTurnResult"):
                if hasattr(gs_mod, sym) and hasattr(svc_mod, sym):
                    setattr(svc_mod, sym, getattr(gs_mod, sym))

        # Ensure agent_departments and agent_office are loaded & fresh
        try:
            dept_mod = importlib.import_module("documentary.agent_departments")
            importlib.reload(dept_mod)
            ao_mod = importlib.import_module("documentary.agent_office")
            importlib.reload(ao_mod)
        except Exception:
            pass

        for obj in gc.get_objects():
            try:
                cls = getattr(obj, "__class__", None)
                if cls is None:
                    continue
                # Hot-register /api/agent-departments, /api/agency/departments, /api/state, /beats on live FastAPI app instances
                if getattr(cls, "__name__", "") == "FastAPI" and hasattr(obj, "routes") and hasattr(obj, "state"):
                    doc_svc = getattr(obj.state, "service", None)
                    if doc_svc is not None:
                        target_paths = {
                            "/api/agent-departments",
                            "/api/agency/departments",
                            "/api/state",
                            "/api/jobs/{job_id}/stop",
                            "/api/jobs/{job_id}/beats",
                            "/api/jobs/{job_id}/beats/{beat_id}",
                        }
                        if hasattr(obj, "router") and hasattr(obj.router, "routes"):
                            obj.router.routes = [
                                r for r in obj.router.routes
                                if getattr(r, "path", "") not in target_paths
                            ]

                        def _make_stop_job_handler(svc_ref: Any):
                            def _live_stop_job(job_id: str):
                                return svc_ref.stop_job(job_id)
                            return _live_stop_job

                        def _make_list_beats_handler(svc_ref: Any):
                            from fastapi import HTTPException

                            def _live_list_beats(
                                job_id: str,
                                q: str | None = None,
                                timestamp: float | None = None,
                                dirty_only: bool = False,
                                limit: int = 250,
                            ):
                                try:
                                    return svc_ref.list_job_beats(
                                        job_id,
                                        query=q,
                                        timestamp_sec=timestamp,
                                        dirty_only=dirty_only,
                                        limit=max(1, min(int(limit), 1000)),
                                    )
                                except KeyError as exc:
                                    raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

                            return _live_list_beats

                        def _make_get_beat_handler(svc_ref: Any):
                            from fastapi import HTTPException

                            def _live_get_beat(job_id: str, beat_id: str):
                                try:
                                    return svc_ref.get_job_beat(job_id, beat_id)
                                except KeyError as exc:
                                    raise HTTPException(status_code=404, detail=str(exc)) from exc

                            return _live_get_beat

                        def _make_patch_beat_handler(svc_ref: Any):
                            from fastapi import Body, HTTPException

                            def _live_patch_beat(job_id: str, beat_id: str, body: dict[str, Any] = Body(...)):
                                try:
                                    if isinstance(body.get("updates"), dict):
                                        updates = dict(body["updates"])
                                        reason = str(body.get("reason") or "").strip()
                                    else:
                                        updates = {k: v for k, v in body.items() if k != "_reason"}
                                        reason = str(body.get("_reason") or "").strip()
                                    return svc_ref.patch_job_beat(job_id, beat_id, updates, reason=reason)
                                except KeyError as exc:
                                    raise HTTPException(status_code=404, detail=str(exc)) from exc
                                except ValueError as exc:
                                    raise HTTPException(status_code=400, detail=str(exc)) from exc

                            return _live_patch_beat

                        def _make_agent_depts_handler(svc_ref: Any):
                            def _live_agent_depts(job_id: str | None = None):
                                from documentary.agent_office import build_live_office_snapshot
                                snap = build_live_office_snapshot(svc_ref, job_id=job_id)
                                return {
                                    "status": "ok",
                                    "timestamp": snap.get("timestamp"),
                                    "selected_job": snap.get("selected_job"),
                                    "departments": snap.get("departments", []),
                                    "summary": snap.get("departments_summary", {}),
                                }
                            return _live_agent_depts

                        def _make_studio_state_handler(svc_ref: Any):
                            def _live_studio_state(job_id: str | None = None):
                                from documentary.agent_office import build_live_office_snapshot
                                office_snap = build_live_office_snapshot(svc_ref, job_id=job_id)
                                return {
                                    "status": "ok",
                                    "selected_job": office_snap.get("selected_job"),
                                    "jobs": office_snap.get("jobs_list", []),
                                    "agent_office": office_snap,
                                    "agent_departments": office_snap.get("departments", []),
                                    "agent_departments_summary": office_snap.get("departments_summary", {}),
                                }
                            return _live_studio_state

                        depts_fn = _make_agent_depts_handler(doc_svc)
                        state_fn = _make_studio_state_handler(doc_svc)
                        stop_fn = _make_stop_job_handler(doc_svc)
                        list_beats_fn = _make_list_beats_handler(doc_svc)
                        get_beat_fn = _make_get_beat_handler(doc_svc)
                        patch_beat_fn = _make_patch_beat_handler(doc_svc)
                        obj.add_api_route("/api/agent-departments", depts_fn, methods=["GET"])
                        obj.add_api_route("/api/agency/departments", depts_fn, methods=["GET"])
                        obj.add_api_route("/api/state", state_fn, methods=["GET"])
                        obj.add_api_route("/api/jobs/{job_id}/stop", stop_fn, methods=["POST"])
                        obj.add_api_route("/api/jobs/{job_id}/beats", list_beats_fn, methods=["GET"])
                        obj.add_api_route("/api/jobs/{job_id}/beats/{beat_id}", get_beat_fn, methods=["GET"])
                        obj.add_api_route("/api/jobs/{job_id}/beats/{beat_id}", patch_beat_fn, methods=["PATCH"])
                        obj.openapi_schema = None
                if getattr(cls, "__name__", "") == "AntigravityGoalSession":
                    try:
                        obj.max_context_tokens = 115_000
                        obj.max_steps = 600
                        ws_root = getattr(obj, "workspace", None)
                        if isinstance(ws_root, Path):
                            extra = list(getattr(obj, "_extra_dirs", []) or [])
                            uploads_p = ws_root / "data" / "chat_uploads"
                            uploads_p.mkdir(parents=True, exist_ok=True)
                            for cand_p in (uploads_p, ws_root.parent / "CofiRemotion"):
                                if cand_p.is_dir():
                                    s_cand = str(cand_p.resolve())
                                    if s_cand not in extra:
                                        extra.append(s_cand)
                            obj._extra_dirs = extra
                    except Exception:
                        pass
                mod_name = getattr(cls, "__module__", None)
                if mod_name not in reloaded_modules:
                    continue
                new_mod = reloaded_modules[mod_name]
                new_cls = getattr(new_mod, getattr(cls, "__name__", ""), None)
                if isinstance(new_cls, type) and new_cls is not cls:
                    obj.__class__ = new_cls
                    if getattr(new_cls, "__name__", "") == "BackgroundRenderCache":
                        try:
                            obj.runner = obj._run_process
                            obj.hardware_profile = rc_mod.detect_hardware_profile()
                        except Exception:
                            pass
                    elif getattr(new_cls, "__name__", "") == "DocumentaryService":
                        try:
                            if hasattr(obj, "_load_channel_profiles"):
                                obj._channel_profiles = obj._load_channel_profiles()
                        except Exception:
                            pass
                    elif getattr(new_cls, "__name__", "") == "AntigravityGoalSession":
                        try:
                            obj.max_context_tokens = 115_000
                            obj.max_steps = 600
                        except Exception:
                            pass
                    rebound += 1
            except Exception:
                continue
    except Exception:
        pass
    return rebound


def ensure_runtime_modules_synced(
    *,
    force: bool = False,
    caller_module: str | None = None,
) -> dict[str, Any]:
    """Synchronize in-memory modules in long-running server processes (`desktop_app.py` / `uvicorn`)
    with updated source files on disk without dropping active state or closing GUI windows.
    """
    global _RELOADING, _INITIAL_SYNC_DONE
    edit_mod = sys.modules.get("documentary.edit")
    missing_edit_symbol = edit_mod is not None and not hasattr(edit_mod, "compute_beat_text_hash")

    if os.environ.get("PYTEST_CURRENT_TEST") and not force and not missing_edit_symbol:
        return {"reloaded": [], "rebound_instances": 0, "skipped": "pytest"}

    _start_watcher_if_needed()

    with _LOCK:
        if _RELOADING:
            return {"reloaded": [], "rebound_instances": 0, "skipped": "reentrant"}
        _RELOADING = True
        reloaded_names: list[str] = []
        reloaded_map: dict[str, Any] = {}
        try:
            first_sync = not _INITIAL_SYNC_DONE
            for mod_name in _RELOAD_ORDER:
                if mod_name == caller_module:
                    continue
                mod = sys.modules.get(mod_name)
                if mod is None:
                    continue
                spec = getattr(mod, "__spec__", None)
                if getattr(spec, "_initializing", False):
                    continue
                mtime = _get_module_mtime(mod)
                prev_mtime = _MODULE_MTIMES.get(mod_name)
                needs_reload = (
                    force
                    or first_sync
                    or (mod_name == "documentary.edit" and not hasattr(mod, "compute_beat_text_hash"))
                    or (mtime is not None and prev_mtime is not None and mtime != prev_mtime)
                )
                if needs_reload:
                    try:
                        reloaded_mod = importlib.reload(mod)
                        reloaded_names.append(mod_name)
                        reloaded_map[mod_name] = reloaded_mod
                        new_mt = _get_module_mtime(reloaded_mod)
                        if new_mt is not None:
                            _MODULE_MTIMES[mod_name] = new_mt
                    except Exception:
                        if mtime is not None:
                            _MODULE_MTIMES[mod_name] = mtime
                elif mtime is not None and prev_mtime is None:
                    _MODULE_MTIMES[mod_name] = mtime

            rebound_count = _rebind_live_instances(reloaded_map)
            _INITIAL_SYNC_DONE = True
            return {
                "reloaded": reloaded_names,
                "rebound_instances": rebound_count,
            }
        finally:
            _RELOADING = False


def _watcher_loop() -> None:
    while True:
        time.sleep(2.0)
        if os.environ.get("PYTEST_CURRENT_TEST"):
            continue
        try:
            ensure_runtime_modules_synced()
        except Exception:
            pass


def _start_watcher_if_needed() -> None:
    global _WATCHER_STARTED
    if _WATCHER_STARTED or os.environ.get("PYTEST_CURRENT_TEST"):
        return
    _WATCHER_STARTED = True
    try:
        t = threading.Thread(target=_watcher_loop, name="cofi-hot-reload-watcher", daemon=True)
        t.start()
    except Exception:
        pass
