"""
Backend API Server for CofiDocumentary (Milestones 1-4).
Serving REST endpoints for Channel Profiles, Jobs, Radar integration, Remotion rendering,
Voice/SRT synchronization, Editing Style DNA, Channel-DNA Pre-Flight, and Continuous Self-Learning analysis.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request

from app import create_app as legacy_create_app
from documentary.service import DocumentaryService
from services.channel_profile_service import ChannelProfileService
from services.editing_dna_service import EditingDnaService
from services.job_service import JobService
from services.sync_policy_service import SyncPolicyService
from services.preflight_service import PreflightService
from services.self_learning_service import SelfLearningService
from services.thumbnail_dna_service import ThumbnailDnaService

ROOT = Path(__file__).resolve().parent


def create_app(service: DocumentaryService | None = None) -> FastAPI:
    """
    Construct FastAPI server with strict isolation, modular services,
    and separated REST endpoints for Channel Profiles, Jobs, Editing DNA, Sync Policy,
    Channel-DNA Pre-Flight, Continuous Self-Learning, and Thumbnail Style DNA Studio.
    """
    # Initialize base application with legacy pipelines and static assets
    api = legacy_create_app(service)

    # Initialize modular domain services
    doc_service = getattr(api.state, "service", service)
    storage_path = ROOT / "data" / "channel_profiles.json"
    profile_service = ChannelProfileService(storage_path=storage_path, documentary_service=doc_service)
    job_store = getattr(doc_service, "store", None)
    job_service = JobService(store=job_store, profile_service=profile_service)
    editing_dna_service = EditingDnaService(profiles_file=storage_path, jobs_dir=ROOT / "data" / "jobs", workspaces_dir=ROOT / "workspaces")
    sync_policy_service = SyncPolicyService(workspaces_dir=ROOT / "workspaces", jobs_dir=ROOT / "data" / "jobs")
    preflight_service = PreflightService(profiles_file=storage_path, jobs_dir=ROOT / "data" / "jobs", profile_service=profile_service)
    self_learning_service = SelfLearningService(profiles_file=storage_path, jobs_dir=ROOT / "data" / "jobs", profile_service=profile_service)
    thumbnail_dna_service = ThumbnailDnaService(profiles_file=storage_path, jobs_dir=ROOT / "data" / "jobs", workspaces_dir=ROOT / "workspaces")

    # Attach services to application state
    api.state.channel_profile_service = profile_service
    api.state.job_service = job_service
    api.state.editing_dna_service = editing_dna_service
    api.state.sync_policy_service = sync_policy_service
    api.state.preflight_service = preflight_service
    api.state.self_learning_service = self_learning_service
    api.state.thumbnail_dna_service = thumbnail_dna_service

    # Filter out legacy routes so modular handlers take precedence
    filtered_routes = []
    for route in api.router.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set())
        if path == "/api/radar/channel-profiles" and methods.intersection({"GET", "POST"}):
            continue
        if path == "/api/radar/channel-profiles/{profile_id}" and methods.intersection({"GET", "PATCH", "PUT", "DELETE"}):
            continue
        if path == "/api/jobs" and methods.intersection({"POST"}):
            continue
        if "preflight-check" in path:
            continue
        if "self-learning" in path:
            continue
        if "topic-memory" in path:
            continue
        if path == "/api/creative/pitch-angles" and methods.intersection({"POST"}):
            continue
        if path == "/api/jobs/{job_id}/thumbnail-studio" and methods.intersection({"GET"}):
            continue
        if path == "/api/jobs/{job_id}/thumbnail-studio/auto-design" and methods.intersection({"POST"}):
            continue
        filtered_routes.append(route)
    api.router.routes = filtered_routes

    # Build separated router
    router = APIRouter()

    # ==========================================================================
    # CHANNEL PROFILE ENDPOINTS
    # ==========================================================================

    @router.get("/api/radar/channel-profiles")
    def list_channel_profiles():
        """List all channel profiles sorted by updated_at descending."""
        return profile_service.list_profiles()

    @router.get("/api/radar/channel-profiles/{profile_id}")
    def get_channel_profile(profile_id: str):
        """Get single channel profile by ID."""
        try:
            return profile_service.get_profile(profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc

    @router.post("/api/radar/channel-profiles")
    async def create_channel_profile(request: Request):
        """Create a new channel profile with generated ID and complete schema."""
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Payload must be a JSON object")
            return profile_service.create_profile(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tạo được hồ sơ kênh: {exc}") from exc

    @router.post("/api/radar/channel-profiles/{profile_id}/clone")
    async def clone_channel_profile(profile_id: str, request: Request):
        """Clone an existing profile with a new ID and ' (Clone)' suffix on name."""
        try:
            body = {}
            try:
                body = await request.json()
            except Exception:
                body = {}
            new_label = body.get("label") if isinstance(body, dict) else None
            return profile_service.clone_profile(profile_id, new_label=new_label)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không nhân bản được hồ sơ kênh: {exc}") from exc

    @router.put("/api/radar/channel-profiles/{profile_id}")
    async def update_channel_profile_put(profile_id: str, request: Request):
        """Update an existing profile in-place preserving fields."""
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Payload must be a JSON object")
            return profile_service.update_profile(profile_id, body)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không cập nhật được hồ sơ kênh: {exc}") from exc

    @router.patch("/api/radar/channel-profiles/{profile_id}")
    async def update_channel_profile_patch(profile_id: str, request: Request):
        """Update an existing profile in-place (PATCH compatibility)."""
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Payload must be a JSON object")
            return profile_service.update_profile(profile_id, body)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không cập nhật được hồ sơ kênh: {exc}") from exc

    @router.delete("/api/radar/channel-profiles/{profile_id}")
    def delete_channel_profile(profile_id: str):
        """Delete profile safely."""
        try:
            return profile_service.delete_profile(profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không xóa được hồ sơ kênh: {exc}") from exc

    # --------------------------------------------------------------------------
    # TOPIC MEMORY ENDPOINTS
    # --------------------------------------------------------------------------

    @router.get("/api/radar/channel-profiles/{profile_id}/topic-memory")
    def get_channel_profile_topic_memory(profile_id: str):
        """Retrieve topic memory for a specific channel profile."""
        try:
            items = profile_service.get_topic_memory(profile_id)
            return {"profile_id": profile_id, "topic_memory": items, "items": items, "count": len(items)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được bộ nhớ đề tài: {exc}") from exc

    @router.post("/api/radar/channel-profiles/{profile_id}/topic-memory")
    async def add_channel_profile_topic_memory(profile_id: str, request: Request):
        """Add a new produced topic memory entry to the channel profile ledger."""
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Payload must be a JSON object")
            entry = profile_service.add_topic_memory(profile_id, body)
            items = profile_service.get_topic_memory(profile_id)
            return {"status": "ok", "entry": entry, "items": items, "count": len(items)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không thêm được đề tài vào bộ nhớ: {exc}") from exc

    @router.delete("/api/radar/channel-profiles/{profile_id}/topic-memory/{entry_id}")
    def delete_channel_profile_topic_memory(profile_id: str, entry_id: str):
        """Delete a topic memory entry from the channel profile ledger."""
        try:
            res = profile_service.delete_topic_memory(profile_id, entry_id)
            items = profile_service.get_topic_memory(profile_id)
            return {"status": "ok", "deleted_entry_id": entry_id, "items": items, "count": len(items)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy đề tài trong bộ nhớ") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không xóa được đề tài khỏi bộ nhớ: {exc}") from exc

    # ==========================================================================
    # JOB STRICT MUTATION ISOLATION & CREATION ENDPOINTS
    # ==========================================================================

    @router.post("/api/jobs")
    async def create_job(request: Request):
        """Create a new documentary job initialized from assigned channel profile DNA & self-learning rules."""
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a JSON object")

            # Auto-inject self-learning upgrade rules from parent profile into creative brief
            profile_id = payload.get("channel_profile_id")
            if profile_id:
                try:
                    prof = profile_service.get_profile(str(profile_id))
                    sl_rules = (prof.get("self_learning_memory") or {}).get("upgrade_rules", {}).get("next_video_upgrades", [])
                    if sl_rules:
                        if not payload.get("creative_brief"):
                            payload["creative_brief"] = copy.deepcopy(prof.get("default_creative_brief") or {})
                        payload["creative_brief"]["self_learning_injected_rules"] = copy.deepcopy(sl_rules)
                except Exception:
                    pass

            created = job_service.create_job(payload)
            try:
                if hasattr(doc_service, "_record_ui_action"):
                    doc_service._record_ui_action({"type": "select_job", "job_id": created["id"]})
                    doc_service._record_ui_action({"type": "navigate", "tab": "script"})
            except Exception:
                pass
            return created
        except HTTPException:
            raise
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.patch("/api/jobs/{job_id}")
    async def patch_job(job_id: str, request: Request):
        """
        Enforce strict mutation isolation:
        Ensure PATCH /api/jobs/{job_id} only mutates the designated {job_id}
        and rejects any draft mutation side-effects or cross-job mutations.
        """
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a JSON object")
            return job_service.update_job(job_id, payload)
        except HTTPException:
            raise
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ==========================================================================
    # MILESTONE 3: EDITING STYLE DNA & VOICE SYNC / POLICY GUARDRAILS
    # ==========================================================================

    @router.post("/api/jobs/{job_id}/lock-edit-dna")
    async def lock_edit_dna(job_id: str, request: Request):
        """
        Extract approved Remotion/editing parameters from project and lock them
        into the parent Channel Profile as a new version in editing_dna_history.
        """
        try:
            notes = ""
            try:
                body = await request.json()
                if isinstance(body, dict):
                    notes = str(body.get("notes") or body.get("override_name") or "")
            except Exception:
                pass
            return editing_dna_service.lock_job_edit_dna_to_channel(job_id, notes=notes)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/api/jobs/{job_id}/lock-thumbnail-dna")
    async def lock_job_thumbnail_dna(job_id: str, request: Request):
        """
        Extract approved Thumbnail Style DNA parameters from project and lock them
        into the parent Channel Profile as a new version in thumbnail_dna_history.
        """
        try:
            notes = ""
            try:
                body = await request.json()
                if isinstance(body, dict):
                    notes = str(body.get("notes") or body.get("override_name") or "")
            except Exception:
                pass
            return thumbnail_dna_service.lock_job_thumbnail_dna_to_channel(job_id, notes=notes)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/api/radar/channel-profiles/{profile_id}/lock-thumbnail-dna")
    async def lock_channel_profile_thumbnail_dna(profile_id: str, request: Request):
        """
        Directly update and lock Thumbnail DNA on a Channel Profile from Step 0 form.
        """
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            return thumbnail_dna_service.lock_channel_profile_thumbnail_dna(profile_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


    @router.get("/api/jobs/{job_id}/sync-compliance")
    def get_sync_compliance(job_id: str):
        """
        Retrieve structured Audio-Visual Voice/SRT synchronization and
        YouTube Green Monetization Policy compliance scorecard.
        """
        try:
            return sync_policy_service.check_sync_compliance(job_id=job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/api/jobs/{job_id}/auto-repair-sync")
    @router.post("/api/jobs/{job_id}/repair-sync")
    def auto_repair_sync(job_id: str):
        """
        Auto-repair audio-visual synchronization: realign beat boundaries with SRT cues,
        inject Ken Burns zoom-in (1.02x to 1.08x) and HUD telemetry overlays on holds > 8.0s.
        """
        try:
            return sync_policy_service.auto_repair_sync(job_id=job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ==========================================================================
    # MILESTONE 4: CHANNEL-DNA PRE-FLIGHT & CONTINUOUS SELF-LEARNING ENDPOINTS
    # ==========================================================================

    @router.get("/api/radar/channel-profiles/{profile_id}/preflight-check")
    def get_preflight_check(
        profile_id: str,
        stage: str = "topic",
        topic: str | None = None,
        title: str | None = None,
        text_overlay: str | None = None,
        variants: str | None = None,
        tags: str | None = None,
        input_data: str | None = None,
    ):
        """
        Execute Channel DNA Pre-Flight Check against real YouTube DNA and job catalog.
        """
        try:
            data: dict[str, Any] = {}
            if input_data:
                try:
                    parsed = json.loads(input_data)
                    if isinstance(parsed, dict):
                        data.update(parsed)
                except Exception:
                    pass
            if topic is not None:
                data["topic"] = topic
            if title is not None:
                data["title"] = title
            if text_overlay is not None:
                data["text_overlay"] = text_overlay
            if variants is not None:
                try:
                    data["variants"] = json.loads(variants)
                except Exception:
                    data["variants"] = [v.strip() for v in variants.split(",") if v.strip()]
            if tags is not None:
                try:
                    data["tags"] = json.loads(tags)
                except Exception:
                    data["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

            return preflight_service.run_preflight_check(profile_id, stage=stage, input_data=data)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/api/radar/channel-profiles/{profile_id}/preflight-check")
    async def post_preflight_check(profile_id: str, request: Request):
        """
        Execute Channel DNA Pre-Flight Check via POST JSON payload.
        """
        try:
            body = await request.json()
            if not isinstance(body, dict):
                body = {}
            stage = body.get("stage") or "topic"
            input_data = body.get("input_data") if isinstance(body.get("input_data"), dict) else body
            return preflight_service.run_preflight_check(profile_id, stage=stage, input_data=input_data)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/api/radar/channel-profiles/{profile_id}/self-learning")
    def get_self_learning(profile_id: str):
        """
        Retrieve Win/Loss Post-Mortem Report and Evolutionary Upgrade Rules for Channel Profile.
        """
        try:
            return self_learning_service.get_self_learning(profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/api/radar/channel-profiles/{profile_id}/self-learning/run")
    @router.post("/api/radar/channel-profiles/{profile_id}/self-learning")
    def run_self_learning(profile_id: str):
        """
        Trigger fresh Win/Loss classification, diagnostic post-mortem, and upgrade rule synthesis.
        """
        try:
            return self_learning_service.run_self_learning(profile_id, save_to_profile=True)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    # --------------------------------------------------------------------------
    # PIPELINE STAGE INTEGRATION WITH PRE-FLIGHT SUMMARIES
    # --------------------------------------------------------------------------

    @router.post("/api/creative/pitch-angles")
    async def pitch_creative_angles_with_preflight(request: Request):
        """Pitch creative angles with Channel-DNA Pre-Flight validation summary."""
        try:
            body = await request.json()
            if not isinstance(body, dict):
                body = {}
            res = doc_service.pitch_creative_angles(body)
            profile_id = body.get("channel_profile_id")
            topic = body.get("topic") or body.get("title") or ""
            if profile_id and isinstance(res, dict):
                try:
                    preflight = preflight_service.run_preflight_check(
                        profile_id,
                        stage="topic",
                        input_data={"topic": topic, "title": topic},
                    )
                    res["preflight_summary"] = preflight.get("preflight_summary")
                except Exception:
                    pass
            return res
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/api/jobs/{job_id}/thumbnail-studio")
    def get_thumbnail_studio_with_preflight(job_id: str):
        """Retrieve thumbnail studio state ensuring 3+ variants and visual preflight summary."""
        try:
            state_data = doc_service.thumbnail_studio_state(job_id)
            design = state_data.get("design") or {}
            variants = design.get("variants") or []
            job = job_service.get_job(job_id)
            profile_id = job.get("channel_profile_id")
            if profile_id and isinstance(state_data, dict):
                try:
                    active_var = next((v for v in variants if v.get("id") == design.get("active_variant_id")), variants[0] if variants else {})
                    overlay = f"{active_var.get('badge_text', '')} {active_var.get('line_1', '')} {active_var.get('line_2', '')}".strip()
                    preflight = preflight_service.run_preflight_check(
                        profile_id,
                        stage="thumbnail",
                        input_data={"variants": variants, "text_overlay": overlay},
                    )
                    state_data["preflight_summary"] = preflight.get("preflight_summary")
                except Exception:
                    pass
            return state_data
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/api/jobs/{job_id}/thumbnail-studio/auto-design")
    async def auto_design_thumbnail_with_preflight(job_id: str, request: Request):
        """Auto-design thumbnail studio variants with Channel Visual DNA Pre-Flight validation."""
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            state_data = doc_service.auto_design_thumbnail(job_id, payload)
            design = state_data.get("design") or {}
            variants = design.get("variants") or []
            job = job_service.get_job(job_id)
            profile_id = job.get("channel_profile_id")
            if profile_id and isinstance(state_data, dict):
                try:
                    active_var = next((v for v in variants if v.get("id") == design.get("active_variant_id")), variants[0] if variants else {})
                    overlay = f"{active_var.get('badge_text', '')} {active_var.get('line_1', '')} {active_var.get('line_2', '')}".strip()
                    preflight = preflight_service.run_preflight_check(
                        profile_id,
                        stage="thumbnail",
                        input_data={"variants": variants, "text_overlay": overlay},
                    )
                    state_data["preflight_summary"] = preflight.get("preflight_summary")
                except Exception:
                    pass
            return state_data
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/api/jobs/{job_id}/thumbnail-studio/export-ab-pack")
    async def export_thumbnail_ab_pack_endpoint(job_id: str, request: Request):
        """Export all 3 A/B/C variants and metadata pack for YouTube Studio Test & Compare."""
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            return doc_service.export_thumbnail_ab_pack(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/api/jobs/{job_id}/thumbnail-studio/select-winner")
    async def select_thumbnail_winner_endpoint(job_id: str, request: Request):
        """Select a primary winning thumbnail variant and set as active thumbnail.jpg."""
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            return doc_service.select_thumbnail_winner(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


    @router.get("/api/jobs/{job_id}/seo-preflight")
    def get_job_seo_preflight(job_id: str):
        """Retrieve SEO Pre-Flight check comparing job SEO against channel winner keyword DNA."""
        try:
            job = job_service.get_job(job_id)
            workspace = ROOT / "workspaces" / job_id
            seo_pack_file = workspace / "seo_package.json"
            seo_data = {}
            if seo_pack_file.exists():
                try:
                    seo_data = json.loads(seo_pack_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            profile_id = job.get("channel_profile_id")
            tags = seo_data.get("tags") or []
            title = seo_data.get("recommended_title") or job.get("title") or ""
            return preflight_service.run_preflight_check(
                profile_id or "default",
                stage="seo",
                input_data={"tags": tags, "title": title, "description": seo_data.get("description", "")},
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/api/agency/roster")
    def get_agency_roster():
        """Return the full 15-Specialist CofiDocumentary Studio Multi-Agent Roster, Divisions, Runbooks, Departments, and Lint Report."""
        from documentary.agent_departments import build_live_departments_projection, get_department_for_agent

        am = doc_service.agent_manager
        raw_agents = am.list_agents()
        enriched_roster = []
        for ag in raw_agents:
            dept_info = get_department_for_agent(ag.get("id", ""))
            enriched_roster.append({
                **ag,
                "department_hierarchy": dept_info,
            })
        dept_proj = build_live_departments_projection(raw_agents)
        return {
            "status": "ok",
            "architecture": "cofi_single_model_multi_agent",
            "agent_count": len(enriched_roster),
            "divisions": am.list_divisions(),
            "runbooks": am.list_runbooks(),
            "agents": enriched_roster,
            "departments": dept_proj["departments"],
            "departments_summary": dept_proj["summary"],
            "lint": am.lint_corpus(),
        }

    @router.get("/api/agent-departments")
    @router.get("/api/agency/departments")
    @router.get("/api/agents/departments")
    def get_agent_departments_endpoint(job_id: str | None = None):
        """Return the 15 Agent Departments hierarchy with Lead, Deputy, and Specialist Mini-Agents live status."""
        return doc_service.get_agent_departments(job_id=job_id)

    @router.post("/api/agent-departments/dispatch-parallel")
    @router.post("/api/agency/dispatch-parallel")
    @router.post("/api/agents/dispatch-parallel")
    async def dispatch_department_parallel_endpoint(request: Request):
        """Execute parallel specialist batches for one or all 15 departments using ThreadPoolExecutor."""
        from documentary.agent_departments import execute_department_parallel_batches
        from documentary.agent_office import build_live_office_snapshot

        try:
            try:
                body = await request.json()
            except Exception:
                body = {}
            if not isinstance(body, dict):
                body = {}
            dept_id = body.get("dept_id") or body.get("department_id") or body.get("agent_id") or "all"
            req_job_id = str(body.get("job_id") or "").strip() or None

            all_jobs = doc_service.list_jobs()
            selected_job = None
            if req_job_id:
                try:
                    selected_job = doc_service.get_job(req_job_id)
                except Exception:
                    selected_job = next((j for j in all_jobs if j.get("id") == req_job_id), None)
            if selected_job is None:
                selected_job = next(
                    (j for j in all_jobs if str(j.get("status") or "").lower() in {"running", "queued"}),
                    all_jobs[0] if all_jobs else None,
                )

            workspace_dir: Path | None = None
            if selected_job and selected_job.get("workspace"):
                workspace_dir = Path(str(selected_job["workspace"]))
            elif selected_job and selected_job.get("id"):
                workspace_dir = ROOT / "workspaces" / str(selected_job["id"])

            exec_state = execute_department_parallel_batches(
                workspace_dir=workspace_dir,
                dept_id=dept_id,
                job_snapshot=selected_job,
            )
            office_snap = build_live_office_snapshot(
                doc_service,
                job_id=selected_job.get("id") if selected_job else req_job_id,
            )
            return {
                "status": "ok",
                "ok": True,
                "job_id": selected_job.get("id") if selected_job else req_job_id,
                "dept_id": dept_id,
                "parallel_execution": exec_state,
                "departments": office_snap.get("departments", []),
                "summary": office_snap.get("departments_summary", {}),
                "active_parallel_workers": office_snap.get("active_parallel_workers", []),
                "agent_office": office_snap,
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Không chạy được luồng song song phòng ban: {exc}") from exc

    @router.get("/api/state")
    def get_studio_state_endpoint(job_id: str | None = None):
        """Return live studio state including jobs and the 15 Agent Departments hierarchy."""
        from documentary.agent_office import build_live_office_snapshot

        office_snap = build_live_office_snapshot(doc_service, job_id=job_id)
        return {
            "status": "ok",
            "selected_job": office_snap.get("selected_job"),
            "jobs": office_snap.get("jobs_list", []),
            "agent_office": office_snap,
            "agent_departments": office_snap.get("departments", []),
            "agent_departments_summary": office_snap.get("departments_summary", {}),
        }

    @router.get("/api/agency/search")
    def search_agency_specialists(q: str = "", division: str | None = None, limit: int = 8):
        """Lazy-discovery keyword search across the standalone `agents/<division>/<id>.md` corpus."""
        results = doc_service.agent_manager.search_agents(q, division=division, limit=limit)
        return {"query": q, "division": division, "count": len(results), "results": results}

    @router.get("/api/agency/agents/{agent_id}")
    def inspect_agency_specialist(agent_id: str, include_body: bool = True):
        """Inspect one specialist's standalone source charter (`SOUL` + `OPERATIONS` + permission contract + Department Hierarchy)."""
        from documentary.agent_departments import get_department_for_agent

        try:
            spec = doc_service.agent_manager.inspect_agent(agent_id, include_body=include_body)
            dept_info = get_department_for_agent(agent_id)
            if isinstance(spec, dict) and dept_info:
                spec = {**spec, "department_hierarchy": dept_info}
            return spec
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/api/agency/delegate")
    async def delegate_agency_specialist(request: Request):
        """Invoke one CofiDocumentary specialist in an isolated permission-scoped session (with `evidence_qa` gate by default)."""
        try:
            body = await request.json()
            if not isinstance(body, dict):
                body = {}
            return doc_service.delegate_specialist(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/api/agency/delegate-squad")
    async def delegate_agency_squad(request: Request):
        """Invoke an ordered 2..6 specialist handoff squad with structured Handoff Packets between hops."""
        try:
            body = await request.json()
            if not isinstance(body, dict):
                body = {}
            return doc_service.delegate_specialist_squad(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/api/jobs/{job_id}/nexus-ledger")
    def get_job_nexus_ledger(job_id: str):
        """Retrieve the NEXUS Inter-Agent Handoff Ledger, EvidenceQA phase gates, and trace spans for a project."""
        try:
            job = doc_service.get_job(job_id)
            return doc_service.nexus_coordinator.get_project_nexus_state(job["workspace"])
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy dự án: {job_id}") from exc

    @router.get("/api/agency/office-live")
    @router.get("/api/studio/office-live")
    def get_agency_office_live(job_id: str | None = None, pinned: bool = False):
        """Return 100% truth-grounded real-time Studio Agent Office state, active desks, critique/rework gates, and live tool stream."""
        from documentary.agent_office import build_live_office_snapshot

        return build_live_office_snapshot(doc_service, job_id=job_id, pinned=bool(pinned))

    # ==========================================================================
    # VOICEOVER & STORYTELLING RHYTHM SPECIALIST ENDPOINTS
    # ==========================================================================

    @router.get("/api/voice-specialist/masters")
    def get_voice_specialist_masters():
        """List clean 1st-generation master voices (including K1 clean for KR) for bespoke profile voice sculpting."""
        from services.voice_rhythm_specialist import VoiceRhythmSpecialistService

        svc = VoiceRhythmSpecialistService()
        return {
            "status": "ok",
            "default_kr_master_id": "09c70cc1-cc86-4905-b65b-3967209c3175",
            "masters": svc.list_clean_master_voices(),
        }

    @router.post("/api/voice-specialist/analyze")
    async def analyze_profile_voice_rhythm(request: Request):
        """Analyze draft or saved Channel Profile attributes and return 3-Layer Storytelling Rhythm DNA + Voice Color Spec."""
        from services.voice_rhythm_specialist import VoiceRhythmSpecialistService

        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Payload must be a JSON object")
            profile_payload = body.get("profile") if isinstance(body.get("profile"), dict) else body
            custom_dir = str(body.get("custom_direction") or profile_payload.get("voice_custom_direction") or "").strip()
            pref_base = str(body.get("base_voice_id") or profile_payload.get("base_voice_id") or "").strip() or None
            svc = VoiceRhythmSpecialistService()
            rhythm_dna = svc.analyze_profile_rhythm_dna(
                profile_payload,
                custom_direction=custom_dir,
                preferred_base_voice_id=pref_base,
            )
            return {
                "status": "ok",
                "rhythm_dna": rhythm_dna,
                "masters": svc.list_clean_master_voices(),
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Không phân tích được nhịp kể hồ sơ: {exc}") from exc

    @router.post("/api/radar/channel-profiles/{profile_id}/design-voice-rhythm")
    async def design_channel_profile_voice_rhythm(profile_id: str, request: Request):
        """Sculpt or clone a dedicated 1-of-1 voice color + 3-layer Rhythm DNA for `profile_id` and bind it live."""
        from services.voice_rhythm_specialist import VoiceRhythmSpecialistService

        try:
            existing = profile_service.get_profile(profile_id)
            body = await request.json()
            if not isinstance(body, dict):
                body = {}
            draft_overrides = body.get("profile_overrides") if isinstance(body.get("profile_overrides"), dict) else {}
            merged_profile = {**existing, **draft_overrides, "id": existing.get("id") or profile_id}

            source_mode = str(body.get("source_mode") or body.get("voice_source_mode") or "base_voice").strip()
            base_voice_id = str(body.get("base_voice_id") or "").strip() or None
            sample_b64 = str(body.get("sample_audio_base64") or body.get("audio_base64") or "").strip() or None
            sample_fname = str(body.get("sample_filename") or body.get("filename") or "sample.wav").strip()
            ref_text = str(body.get("ref_text") or "").strip() or None
            custom_dir = str(body.get("custom_direction") or "").strip()
            synthesize_preview = bool(body.get("synthesize_preview", True))

            svc = VoiceRhythmSpecialistService()
            result = svc.design_and_bind_profile_voice(
                merged_profile,
                profile_service=profile_service,
                source_mode=source_mode,
                base_voice_id=base_voice_id,
                sample_audio_base64=sample_b64,
                sample_filename=sample_fname,
                ref_text=ref_text,
                custom_direction=custom_dir,
                persist_to_profile=True,
                synthesize_preview=synthesize_preview,
            )
            return {"status": "ok", **result}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không thiết kế được màu giọng cho hồ sơ: {exc}") from exc

    api.include_router(router)
    return api


_default_app: FastAPI | None = None


async def app(scope, receive, send):
    """Lazy ASGI entrypoint."""
    global _default_app
    if _default_app is None:
        _default_app = create_app()
    await _default_app(scope, receive, send)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("COFI_DOCUMENTARY_PORT", "8878")), reload=False)
