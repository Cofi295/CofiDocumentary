from __future__ import annotations

import os
import sys

if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    except Exception:
        pass

import json
from queue import Empty, Queue
from pathlib import Path
from threading import Thread
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from documentary.service import DocumentaryService
from COFI_BRAIN.source_repair_agent import SourceRepairAgent

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
REPAIR_AGENT = SourceRepairAgent(str(ROOT))
REPAIR_AGENT.save_capabilities()
FALLBACK_POSTER_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" width="100%" height="100%">'
    b'<rect width="320" height="180" fill="#08131d"/>'
    b'<circle cx="160" cy="90" r="26" fill="#0e2337" stroke="#2a4d6f" stroke-width="1.5"/>'
    b'<polygon points="153,77 173,90 153,103" fill="#83dbf7"/>'
    b'</svg>'
)


class CreateJobRequest(BaseModel):
    title: str | None = None
    topic: str | None = None
    source_url: str | None = None
    market: str = "KR"
    language: str = "ko"
    notes: str = ""
    target_duration_minutes: float = Field(default=5, ge=2, le=180)
    plan_engine: str = "codex"
    footage_mode: str = "vision_codex"
    visual_strategy: str = "full_footage"
    ai_media_mode: str = "mixed"
    ai_visual: dict[str, Any] = Field(default_factory=dict)
    voice: dict[str, Any] = Field(default_factory=dict)
    production_recipe: dict[str, Any] = Field(default_factory=dict)
    topic_discovery: dict[str, Any] = Field(default_factory=dict)
    channel_profile_id: str | None = None
    channel_plan_item_id: int | None = None
    playbook_id: str | None = None
    creative_brief: dict[str, Any] = Field(default_factory=dict)
    narrative_angle: str | None = None
    writing_style: str | None = None
    hook_archetype: str | None = None
    editing_archetypes: list[str] | str | None = None
    opening_hook: str | None = None
    custom_rules: str | None = None
    outline: dict[str, Any] | list[dict[str, Any]] | None = None
    workspace_root: str | None = None
    seo_keyword_dna: dict[str, Any] | None = None
    thumbnail_dna: dict[str, Any] | None = None
    start_plan: bool = False
    run_plan: bool = False


class RadarImportRequest(BaseModel):
    scan_id: int
    video_id: str
    target_duration_minutes: float = Field(default=5, ge=2, le=180)
    plan_engine: str = "codex"
    visual_strategy: str = "full_footage"
    ai_media_mode: str = "mixed"
    ai_visual: dict[str, Any] = Field(default_factory=dict)
    language: str | None = None
    market: str | None = None
    notes: str = ""
    voice: dict[str, Any] = Field(default_factory=dict)
    channel_profile_id: str | None = None
    playbook_id: str | None = None
    creative_brief: dict[str, Any] = Field(default_factory=dict)
    outline: dict[str, Any] | list[dict[str, Any]] | None = None
    workspace_root: str | None = None


class CreativeBriefRequest(BaseModel):
    playbook_id: str | None = None
    creative_brief: dict[str, Any] | None = None
    narrative_angle: str | None = None
    writing_style: str | None = None
    hook_archetype: str | None = None
    editing_archetypes: list[str] | str | None = None
    editing_grammar: list[str] | str | None = None
    opening_hook: str | None = None
    custom_rules: str | None = None
    notes: str | None = None


class OutlineUpdateRequest(BaseModel):
    outline: dict[str, Any] | list[dict[str, Any]] | None = None
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    opening_hook: str | None = None
    thesis: str | None = None


class OutlineGenerateRequest(BaseModel):
    creative_brief: dict[str, Any] | None = None
    notes: str | None = None
    instruction: str | None = None
    chapter_count: int | None = None


class ScriptUpdateRequest(BaseModel):
    script: str | None = None
    research: str | None = None


class PlaybookRequest(BaseModel):
    id: str | None = None
    name: str
    description: str = ""
    market: str = "KR"
    language: str = "ko"
    visual_strategy: str = "hybrid"
    ai_media_mode: str = "mixed"
    creative_brief: dict[str, Any] = Field(default_factory=dict)


class ExtractPlaybookRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    custom_rules: str | None = None


class PitchAnglesRequest(BaseModel):
    topic: str | None = None
    title: str | None = None
    market: str = "KR"
    language: str = "ko"
    notes: str = ""
    channel_profile_id: str | None = None


class VoiceSettingsRequest(BaseModel):
    voice_id: str | None = None
    speed: float = Field(default=1.0, ge=0.8, le=1.2)
    mode: str = "balanced"


class VoiceDesignRequest(BaseModel):
    name: str
    language: str = "vi"
    instruct: str
    auto_preview: bool = True


class VoiceTtsPreviewRequest(BaseModel):
    text: str
    voice_id: str | None = None
    language: str | None = None
    speed: float = Field(default=1.0, ge=0.7, le=1.5)
    mode: str = "balanced"


class AIVisualSettingsRequest(BaseModel):
    task_type: str | None = None
    model: str | None = None
    image_model: str | None = None
    video_model: str | None = None
    aspect_ratio: str | None = None
    veo_enabled: bool | None = None
    style_mode: str | None = None
    style_preset: str | None = None
    custom_style: str | None = None
    ai_media_mode: str | None = None
    coverage_mode: str | None = None
    reference_image_name: str | None = None
    reference_image_data_url: str | None = None
    clear_style_reference: bool | None = None


class ProductionSettingsRequest(BaseModel):
    visual_strategy: str | None = None
    ai_media_mode: str | None = None


class AIAccountSettingsRequest(BaseModel):
    model: str | None = None


class ChatProviderRequest(BaseModel):
    provider: str


class EditChatRequest(BaseModel):
    message: str = ""
    selected_beat_id: str | None = None
    selected_timestamp_sec: float | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=4)


class ProducerChatRequest(BaseModel):
    message: str = ""
    selected_job_id: str | None = None
    app_tab: str | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=4)
    goal_mode: bool = False
    model: str | None = None
    provider: str | None = None


class RadarMarketScanRequest(BaseModel):
    market: str = "KR"
    seeds: list[str] = Field(default_factory=list)
    days: int = Field(default=7, ge=1, le=365)
    max_videos: int = Field(default=60, ge=10, le=500)
    max_channel_subscribers: int = Field(default=100_000, ge=100, le=10_000_000)
    max_channel_age_days: int = Field(default=90, ge=1, le=3650)
    min_proof_channels: int = Field(default=3, ge=1, le=10)
    min_breakout_videos: int = Field(default=4, ge=1, le=20)
    niche_granularity: str = "micro"
    content_type: str = "factual_documentary"
    production_mode: str | None = None


class RadarChannelScanRequest(BaseModel):
    channel_ref: str
    label: str | None = None
    content_type: str = "factual_documentary"


class RadarChannelDiscoveryRequest(BaseModel):
    channel_id: str
    market: str = "KR"
    days: int = Field(default=30, ge=1, le=365)
    max_videos: int = Field(default=80, ge=10, le=500)


class RadarTranslateRequest(BaseModel):
    texts: list[str] = Field(default_factory=list, max_length=80)


class RadarSaveNicheRequest(BaseModel):
    note: str | None = None


class ChannelProfileRequest(BaseModel):
    label: str | None = None
    own_channel_ref: str = ""
    competitor_refs: list[str] = Field(default_factory=list)
    market: str = "KR"
    default_language: str | None = None
    default_duration_minutes: float | None = Field(default=None, ge=2, le=180)
    default_visual_strategy: str | None = None
    default_ai_media_mode: str | None = None
    default_ai_style_mode: str | None = None
    default_ai_custom_style: str | None = None
    dna_mode: str | None = None
    voice_and_structure: str | None = None
    allowed_topics: str | None = None
    forbidden_topics: str | None = None
    monetization_safety_policy: str | None = None
    reference_image_policy: str | None = None
    default_creative_brief: dict[str, Any] | None = None
    editorial_dna: dict[str, Any] | None = None
    editing_dna: dict[str, Any] | None = None
    self_learning_memory: dict[str, Any] | None = None
    seo_keyword_dna: dict[str, Any] | None = None
    thumbnail_dna: dict[str, Any] | None = None


class ChannelPlanStatusRequest(BaseModel):
    status: str


def create_app(service: DocumentaryService | None = None) -> FastAPI:
    service = service or DocumentaryService(
        ROOT,
        remotion_dir=os.getenv("COFI_REMOTION_DIR", r"B:\ALL_TOOLS\CofiRemotion"),
        radar_url=os.getenv("COFI_RADAR_URL", "http://127.0.0.1:8775"),
        voice_url=os.getenv("COFI_VOICE_URL", "http://127.0.0.1:8000"),
        remotion_studio_port=int(os.getenv("COFI_REMOTION_STUDIO_PORT", "8890")),
        cofi_studio_embed_port=int(os.getenv("COFI_STUDIO_EMBED_PORT", "8894")),
    )
    api = FastAPI(title="COFI DOCUMENTARY", version="0.2.0")
    api.state.service = service
    if STATIC_DIR.exists():
        api.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @api.middleware("http")
    async def disable_static_cache(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path or ""
        if path == "/" or path.startswith("/static/") or (path.startswith("/api/") and not path.endswith("/media")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @api.get("/api/health")
    def health():
        return service.health()

    @api.post("/api/ai-accounts/{provider}/login")
    def ai_account_login(provider: str):
        try:
            return service.ai_account_login(provider)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @api.patch("/api/ai-accounts/{provider}/settings")
    def ai_account_settings(provider: str, body: AIAccountSettingsRequest):
        try:
            return service.update_ai_account_settings(provider, body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @api.patch("/api/chat-provider")
    def chat_provider(body: ChatProviderRequest):
        try:
            return service.update_chat_provider(body.provider)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/jobs")
    def jobs():
        return service.list_jobs()

    @api.post("/api/storage/select-folder")
    def select_storage_folder():
        try:
            return service.select_workspace_root()
        except (OSError, RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs")
    def create_job(body: CreateJobRequest):
        try:
            return service.create_job(body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/from-radar")
    def create_job_from_radar(body: RadarImportRequest):
        overrides = body.model_dump(exclude={"scan_id", "video_id"}, exclude_none=True)
        try:
            return service.create_job_from_radar(body.scan_id, body.video_id, overrides)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không thể lấy chủ đề từ Radar: {exc}") from exc

    @api.get("/api/jobs/{job_id}")
    def job_detail(job_id: str):
        try:
            return service.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.delete("/api/jobs/{job_id}")
    def delete_job(job_id: str):
        try:
            return service.delete_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.patch("/api/jobs/{job_id}/voice")
    def update_voice(job_id: str, body: VoiceSettingsRequest):
        try:
            return service.update_voice_settings(job_id, body.model_dump())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/ai-visual-settings")
    def ai_visual_settings(job_id: str):
        try:
            return service.ai_visual_settings(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.get("/api/ai-visual/style-presets")
    def ai_visual_style_presets():
        return service.ai_visual_style_presets()

    @api.patch("/api/jobs/{job_id}/ai-visual-settings")
    def update_ai_visual_settings(job_id: str, body: AIVisualSettingsRequest):
        try:
            return service.update_ai_visual_settings(job_id, body.model_dump(exclude_none=True))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.patch("/api/jobs/{job_id}/production-settings")
    def update_production_settings(job_id: str, body: ProductionSettingsRequest):
        try:
            return service.update_production_settings(job_id, body.model_dump(exclude_none=True))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/cofi-studio/embed")
    def cofi_studio_embed_status():
        return service.cofi_studio_embed_status()

    @api.post("/api/cofi-studio/embed/start")
    def cofi_studio_embed_start():
        try:
            return service.cofi_studio_embed_status(start=True)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/ai-visual-runtime")
    def ai_visual_runtime(job_id: str):
        try:
            return service.ai_visual_runtime(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/ai-visual-reset")
    def ai_visual_reset(job_id: str):
        try:
            return service.ai_visual_reset(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/ai-visual-test")
    def ai_visual_test(job_id: str):
        try:
            return service.ai_visual_test(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/ai-visual-video-test")
    def ai_visual_video_test(job_id: str):
        try:
            return service.ai_visual_video_test(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/queue/{action}")
    def ai_visual_runtime_queue(action: str):
        try:
            return service.ai_visual_runtime_queue(action)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/accounts/login")
    def ai_visual_runtime_account_login():
        try:
            return service.ai_visual_runtime_account_login()
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/accounts/prune-dead")
    def ai_visual_runtime_prune_dead_accounts():
        try:
            return service.ai_visual_runtime_prune_dead_accounts()
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/accounts/check-all")
    def ai_visual_runtime_check_all_accounts():
        try:
            return service.ai_visual_runtime_check_all_accounts()
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/accounts/clean-cache")
    def ai_visual_runtime_clean_cache():
        try:
            return service.ai_visual_runtime_clean_profile_caches()
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/v1/accounts/google-flow/clean-cache")
    def ai_visual_runtime_clean_cache_v1_alias():
        return ai_visual_runtime_clean_cache()

    @api.delete("/api/cofi-studio/runtime/accounts/{account_id}")
    def ai_visual_runtime_account_delete(account_id: str):
        try:
            return service.ai_visual_runtime_account(account_id, "delete")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/accounts/{account_id}/{action}")
    def ai_visual_runtime_account(account_id: str, action: str):
        try:
            return service.ai_visual_runtime_account(account_id, action)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/run/{phase}")
    def run_phase(job_id: str, phase: str):
        try:
            return service.start(job_id, phase)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/resume")
    def resume_job(job_id: str):
        try:
            return service.start(job_id, "all")
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/rerun/{phase}")
    def rerun_phase(job_id: str, phase: str):
        try:
            return service.rerun(job_id, phase)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/pipeline/{from_phase}/{through_phase}")
    def run_pipeline(job_id: str, from_phase: str, through_phase: str):
        try:
            return service.run_pipeline(job_id, from_phase, through_phase)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/logs/{phase}", response_class=PlainTextResponse)
    def logs(job_id: str, phase: str):
        try:
            return service.phase_log(job_id, phase)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/artifact/{name}", response_class=PlainTextResponse)
    def artifact(job_id: str, name: str):
        try:
            return service.read_artifact(job_id, name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"Chưa có artifact {name}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/media")
    def job_media(job_id: str, path: str = Query(..., min_length=1), poster: bool = Query(default=False)):
        try:
            if poster:
                resolved = service.resolve_poster_path(job_id, path)
                if resolved.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                    return FileResponse(resolved, media_type="image/jpeg")
                return Response(content=FALLBACK_POSTER_SVG, media_type="image/svg+xml")
            return FileResponse(service.resolve_media_path(job_id, path))
        except KeyError as exc:
            if poster:
                return Response(content=FALLBACK_POSTER_SVG, media_type="image/svg+xml")
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except FileNotFoundError as exc:
            if poster:
                return Response(content=FALLBACK_POSTER_SVG, media_type="image/svg+xml")
            raise HTTPException(status_code=404, detail="Không tìm thấy media") from exc
        except ValueError as exc:
            if poster:
                return Response(content=FALLBACK_POSTER_SVG, media_type="image/svg+xml")
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/live-footage")
    def live_footage(job_id: str):
        try:
            return service.list_live_footage(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.post("/api/jobs/{job_id}/footage/pause")
    def pause_footage(job_id: str):
        try:
            return service.footage_control(job_id, "pause")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/footage/resume")
    def resume_footage(job_id: str):
        try:
            return service.footage_control(job_id, "resume")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/footage/stop")
    def stop_footage(job_id: str):
        try:
            return service.footage_control(job_id, "stop")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/remotion")
    def remotion_status(job_id: str):
        try:
            return service.remotion_status(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.get("/api/jobs/{job_id}/export-progress")
    def export_progress(job_id: str):
        try:
            return service.export_progress(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.post("/api/jobs/{job_id}/remotion/start")
    def remotion_start(job_id: str):
        try:
            return service.start_remotion(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/edit-chat")
    def edit_chat_history(job_id: str):
        try:
            return service.edit_chat_history(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.post("/api/jobs/{job_id}/edit-chat")
    def edit_chat(job_id: str, body: EditChatRequest):
        try:
            return service.edit_chat(
                job_id,
                body.message,
                selected_beat_id=body.selected_beat_id,
                selected_timestamp_sec=body.selected_timestamp_sec,
                attachment_ids=body.attachment_ids,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/producer-chat")
    def producer_chat_history(selected_job_id: str | None = Query(default=None)):
        try:
            return service.producer_chat_history(selected_job_id=selected_job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.delete("/api/producer-chat")
    def clear_producer_chat_history(selected_job_id: str | None = Query(default=None)):
        try:
            return service.clear_producer_chat_history(selected_job_id=selected_job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.post("/api/producer-chat/compact")
    def compact_producer_chat_session(selected_job_id: str | None = Query(default=None)):
        try:
            return service.compact_producer_chat_session(selected_job_id=selected_job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/producer-chat/new")
    def new_producer_chat_session(selected_job_id: str | None = Query(default=None)):
        try:
            return service.new_producer_chat_session(selected_job_id=selected_job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/producer-chat/context")
    def producer_chat_context(
        selected_job_id: str | None = Query(default=None),
        app_tab: str | None = Query(default=None),
    ):
        try:
            return service.producer_chat_context(selected_job_id, app_tab)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.post("/api/producer-chat")
    def producer_chat(body: ProducerChatRequest):
        try:
            return service.producer_chat(
                body.message,
                selected_job_id=body.selected_job_id,
                app_tab=body.app_tab,
                attachment_ids=body.attachment_ids,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/producer-chat/runs")
    def start_producer_chat_run(body: ProducerChatRequest, request: Request):
        try:
            payload = body.model_dump()
            payload["api_base_url"] = str(request.base_url).rstrip("/")
            return service.start_producer_chat_run(payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/producer-chat/runs/active")
    def find_active_producer_chat_run(selected_job_id: str | None = Query(default=None)):
        return service.find_active_producer_chat_run(selected_job_id=selected_job_id)

    @api.get("/api/producer-chat/runs/{run_id}")
    def get_producer_chat_run(run_id: str):
        try:
            return service.get_producer_chat_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat") from exc

    @api.get("/api/producer-chat/runs/{run_id}/events")
    def producer_chat_run_events(run_id: str, after: int = Query(default=0, ge=0)):
        try:
            service.get_producer_chat_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat") from exc

        def event_stream():
            for event in service.producer_chat_run_events(run_id, after=after):
                yield json.dumps(event, ensure_ascii=False) + "\n"

        return StreamingResponse(event_stream(), media_type="application/x-ndjson")

    @api.post("/api/producer-chat/runs/{run_id}/cancel")
    def cancel_producer_chat_run(run_id: str):
        try:
            return service.cancel_producer_chat_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat") from exc

    @api.post("/api/producer-chat/stream")
    def producer_chat_stream(body: ProducerChatRequest):
        def event_stream():
            queue: Queue[dict[str, Any]] = Queue()

            def emit(line: str) -> None:
                queue.put({"type": "cli_event", "line": str(line or "")[:12000]})

            def worker() -> None:
                try:
                    result = service.producer_chat(
                        body.message,
                        selected_job_id=body.selected_job_id,
                        app_tab=body.app_tab,
                        attachment_ids=body.attachment_ids,
                        log_callback=emit,
                    )
                    queue.put({"type": "result", "result": result})
                except Exception as exc:
                    queue.put({"type": "error", "message": str(exc)})

            Thread(target=worker, daemon=True, name="producer-chat-stream").start()
            yield json.dumps({"type": "started"}, ensure_ascii=False) + "\n"
            while True:
                try:
                    event = queue.get(timeout=10)
                except Empty:
                    yield json.dumps({"type": "heartbeat"}) + "\n"
                    continue
                yield json.dumps(event, ensure_ascii=False) + "\n"
                if event.get("type") in {"result", "error"}:
                    break

        return StreamingResponse(event_stream(), media_type="application/x-ndjson")

    @api.get("/api/source-repairs")
    def source_repairs():
        return service.list_source_repairs()

    @api.get("/api/source-repairs/{repair_id}")
    def source_repair(repair_id: str):
        try:
            return service.get_source_repair(repair_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy repair job") from exc

    @api.post("/api/chat-attachments")
    async def upload_chat_attachment(request: Request, filename: str = Query(default="image", max_length=240)):
        try:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > service.CHAT_IMAGE_MAX_BYTES:
                raise ValueError("Ảnh vượt quá 10 MB.")
            data = await request.body()
            return service.save_chat_attachment(data, filename, request.headers.get("content-type"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/chat-attachments/{attachment_id}")
    def chat_attachment_file(attachment_id: str):
        try:
            attachment = service.chat_attachment(attachment_id)
            return FileResponse(
                service.resolve_chat_attachment_path(attachment_id),
                media_type=attachment.get("mime_type"),
                filename=attachment.get("name"),
                content_disposition_type="inline",
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy ảnh đính kèm") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/voice/voices")
    def voice_options():
        try:
            return service.voice_options()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"CofiVoice chưa sẵn sàng: {exc}") from exc

    @api.post("/api/voice/start")
    def voice_start():
        try:
            return service.start_voice_backend()
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api.post("/api/voice/clone")
    async def voice_clone(
        request: Request,
        name: str = Query(default="", max_length=160),
        language: str = Query(default="vi", max_length=16),
        ref_text: str = Query(default="", max_length=2000),
        filename: str = Query(default="sample.wav", max_length=240),
        recorded: bool = Query(default=False),
    ):
        try:
            content_type = (request.headers.get("content-type") or "").lower()
            if "application/json" in content_type:
                import base64 as _b64
                payload = await request.json()
                name = str(payload.get("name") or name).strip()
                language = str(payload.get("language") or language or "vi").strip()
                ref_text = str(payload.get("ref_text") or ref_text or "").strip()
                filename = str(payload.get("filename") or filename or "sample.wav").strip()
                recorded = bool(payload.get("recorded", recorded))
                raw_b64 = str(payload.get("audio_base64") or payload.get("data_url") or "").strip()
                if "," in raw_b64 and raw_b64.startswith("data:"):
                    raw_b64 = raw_b64.split(",", 1)[1]
                audio_bytes = _b64.b64decode(raw_b64) if raw_b64 else b""
            else:
                audio_bytes = await request.body()
            return service.clone_voice(
                name=name,
                language=language,
                audio_bytes=audio_bytes,
                filename=filename,
                ref_text=ref_text or None,
                recorded=recorded,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không thể clone giọng nói: {exc}") from exc

    @api.post("/api/voice/design")
    def voice_design(body: VoiceDesignRequest):
        try:
            return service.design_voice(
                name=body.name,
                language=body.language,
                instruct=body.instruct,
                auto_preview=body.auto_preview,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không thể thiết kế giọng nói: {exc}") from exc

    @api.post("/api/voice/voices/{voice_id}/preview")
    def voice_generate_preview(voice_id: str):
        try:
            return service.preview_voice(voice_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tạo được mẫu nghe thử: {exc}") from exc

    @api.get("/api/voice/preview-audio/{voice_id}")
    def voice_preview_audio(voice_id: str):
        try:
            path = service.resolve_voice_preview_path(voice_id)
            return FileResponse(path, media_type="audio/wav", filename=f"{voice_id}.wav")
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được mẫu nghe thử: {exc}") from exc

    @api.post("/api/voice/tts-preview")
    def voice_tts_preview(body: VoiceTtsPreviewRequest):
        try:
            wav_bytes = service.synthesize_voice_sample(
                text=body.text,
                voice_id=body.voice_id,
                language=body.language,
                speed=body.speed,
                mode=body.mode,
            )
            return Response(content=wav_bytes, media_type="audio/wav")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không đọc thử được câu mẫu: {exc}") from exc

    @api.delete("/api/voice/voices/{voice_id}")
    def voice_delete(voice_id: str):
        try:
            return service.delete_voice(voice_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không xóa được giọng nói: {exc}") from exc

    @api.get("/api/radar/scans")
    def radar_scans(limit: int = Query(default=20, ge=1, le=100)):
        try:
            return service.radar_scans(limit)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"COFI RADAR chưa sẵn sàng: {exc}") from exc

    @api.get("/api/radar/scans/{scan_id}/videos")
    def radar_videos(scan_id: int):
        try:
            return service.radar_videos(scan_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được video Radar: {exc}") from exc

    @api.get("/api/radar/scans/{scan_id}/feed")
    def radar_market_feed(scan_id: int):
        try:
            return service.radar_market_feed(scan_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được feed Radar: {exc}") from exc

    @api.post("/api/radar/translate")
    def radar_translate(body: RadarTranslateRequest):
        try:
            return service.radar_translate(body.texts)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không dịch được dữ liệu Radar: {exc}") from exc

    @api.get("/api/radar/scans/{scan_id}")
    def radar_scan(scan_id: int):
        try:
            return service.radar_scan(scan_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được lượt quét Radar: {exc}") from exc

    @api.post("/api/radar/scans/market")
    def radar_market_scan(body: RadarMarketScanRequest):
        try:
            return service.radar_market_scan(body.model_dump())
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Quét thị trường thất bại: {exc}") from exc

    @api.post("/api/radar/scans/channel")
    def radar_channel_scan(body: RadarChannelScanRequest):
        try:
            return service.radar_channel_scan(body.model_dump())
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Quét kênh thất bại: {exc}") from exc

    @api.post("/api/radar/channels/discover")
    def radar_channel_discover(body: RadarChannelDiscoveryRequest):
        try:
            return service.radar_channel_discover(body.model_dump())
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Quét chủ đề theo DNA kênh thất bại: {exc}") from exc

    @api.get("/api/radar/niches")
    def radar_niches(scan_id: int | None = None):
        try:
            return service.radar_niches(scan_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được ngách: {exc}") from exc

    @api.get("/api/radar/niches/{niche_id}")
    def radar_niche_detail(niche_id: int):
        try:
            return service.radar_niche_detail(niche_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được bằng chứng ngách: {exc}") from exc

    @api.post("/api/radar/niches/{niche_id}/save")
    def radar_save_niche(niche_id: int, body: RadarSaveNicheRequest):
        try:
            return service.radar_save_niche(niche_id, note=body.note)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không lưu được ngách Radar: {exc}") from exc

    @api.get("/api/radar/my-channels")
    def radar_my_channels():
        try:
            return service.radar_my_channels()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được kênh: {exc}") from exc

    @api.get("/api/radar/today")
    def radar_today():
        try:
            return service.radar_today()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được hàng đợi hôm nay: {exc}") from exc

    @api.get("/api/radar/channel-profiles")
    def channel_profiles():
        return service.list_channel_profiles()

    @api.post("/api/radar/channel-profiles")
    def create_channel_profile(body: ChannelProfileRequest):
        try:
            return service.save_channel_profile(body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tạo được hồ sơ kênh: {exc}") from exc

    @api.patch("/api/radar/channel-profiles/{profile_id}")
    def update_channel_profile(profile_id: str, body: ChannelProfileRequest):
        try:
            return service.save_channel_profile(body.model_dump(), profile_id=profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không cập nhật được hồ sơ kênh: {exc}") from exc

    @api.delete("/api/radar/channel-profiles/{profile_id}")
    def delete_channel_profile(profile_id: str):
        try:
            return service.delete_channel_profile(profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không xóa được hồ sơ kênh: {exc}") from exc

    @api.get("/api/radar/channel-profiles/{profile_id}/topic-memory")
    def get_channel_profile_topic_memory(profile_id: str):
        try:
            items = service.get_channel_profile_topic_memory(profile_id)
            return {"profile_id": profile_id, "topic_memory": items, "items": items, "count": len(items)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được bộ nhớ đề tài: {exc}") from exc

    @api.post("/api/radar/channel-profiles/{profile_id}/topic-memory")
    async def add_channel_profile_topic_memory(profile_id: str, request: Request):
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Payload must be a JSON object")
            entry = service.add_channel_profile_topic_memory(profile_id, body)
            items = service.get_channel_profile_topic_memory(profile_id)
            return {"status": "ok", "entry": entry, "items": items, "count": len(items)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không thêm được đề tài vào bộ nhớ: {exc}") from exc

    @api.delete("/api/radar/channel-profiles/{profile_id}/topic-memory/{entry_id}")
    def delete_channel_profile_topic_memory(profile_id: str, entry_id: str):
        try:
            res = service.delete_channel_profile_topic_memory(profile_id, entry_id)
            items = service.get_channel_profile_topic_memory(profile_id)
            return {"status": "ok", "deleted_entry_id": entry_id, "items": items, "count": len(items)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy đề tài trong bộ nhớ") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không xóa được đề tài khỏi bộ nhớ: {exc}") from exc

    @api.post("/api/radar/channel-profiles/{profile_id}/refresh")
    def refresh_channel_profile(profile_id: str):
        try:
            return service.refresh_channel_profile(profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không quét lại được hồ sơ kênh: {exc}") from exc

    @api.post("/api/radar/channel-profiles/{profile_id}/today")
    def channel_profile_today(
        profile_id: str,
        target_duration_minutes: float | None = Query(default=None, ge=2, le=180),
        discovery_mode: str | None = Query(default=None),
        force_refresh: bool = Query(default=False),
    ):
        try:
            return service.channel_profile_today(
                profile_id,
                target_duration_minutes=target_duration_minutes,
                discovery_mode=discovery_mode,
                force_refresh=force_refresh,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            service.mark_channel_profile_activity_error(profile_id, exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            service.mark_channel_profile_activity_error(profile_id, exc)
            raise HTTPException(status_code=502, detail=f"Không gợi ý được video hôm nay: {exc}") from exc

    @api.get("/api/radar/channel-profiles/{profile_id}/activity")
    def channel_profile_activity(profile_id: str):
        try:
            return service.channel_profile_activity(profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc

    @api.post("/api/radar/channel-profiles/{profile_id}/plan-30-days")
    def create_channel_profile_plan(
        profile_id: str,
        rebuild: bool = Query(default=False),
        refresh_codex: bool = Query(default=True),
    ):
        try:
            return service.channel_profile_plan(profile_id, rebuild=rebuild, refresh_codex=refresh_codex)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            service.mark_channel_profile_activity_error(profile_id, exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            service.mark_channel_profile_activity_error(profile_id, exc)
            raise HTTPException(status_code=502, detail=f"Không tạo được kế hoạch 30 ngày: {exc}") from exc

    @api.get("/api/radar/channel-profiles/{profile_id}/plan")
    def get_channel_profile_plan(profile_id: str):
        try:
            return service.channel_profile_plan(profile_id, rebuild=False, refresh_profile=False)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được kế hoạch kênh: {exc}") from exc

    @api.patch("/api/radar/channel-profiles/{profile_id}/plan-items/{item_id}")
    def update_channel_profile_plan_item(profile_id: str, item_id: int, body: ChannelPlanStatusRequest):
        try:
            return service.update_channel_profile_plan_item(profile_id, item_id, body.status)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không cập nhật được tiến độ kế hoạch: {exc}") from exc

    # ------------------------------------------------------------------
    # CREATIVE STUDIO, PLAYBOOKS, OUTLINES & PITCHING ROUTES
    # ------------------------------------------------------------------

    @api.get("/api/creative/catalog")
    def get_creative_catalog():
        return service.creative_catalog()

    @api.get("/api/creative/draft")
    def get_creative_draft():
        return service.get_ui_draft()

    @api.post("/api/creative/draft")
    async def update_creative_draft(request: Request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        return service.update_ui_draft(payload)

    @api.post("/api/jobs/{job_id}/approve-next")
    def approve_next_phase(job_id: str):
        try:
            return service.approve_next_phase(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/creative/pitch-angles")
    def pitch_creative_angles(body: PitchAnglesRequest):
        try:
            return service.pitch_creative_angles(body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Không tạo được đề xuất góc nhìn: {exc}") from exc

    @api.get("/api/playbooks")
    def list_playbooks():
        items = service.list_playbooks()
        return {"items": items, "playbooks": items}

    @api.post("/api/playbooks")
    def save_playbook(body: PlaybookRequest):
        try:
            return service.save_playbook(body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.delete("/api/playbooks/{playbook_id}")
    def delete_playbook(playbook_id: str):
        try:
            return service.delete_playbook(playbook_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/extract-playbook")
    def extract_playbook_from_job(job_id: str, body: ExtractPlaybookRequest | None = None):
        try:
            return service.extract_playbook_from_job(job_id, body.model_dump(exclude_none=True) if body else None)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.patch("/api/jobs/{job_id}/creative-brief")
    def update_job_creative_brief(job_id: str, body: CreativeBriefRequest):
        try:
            return service.update_creative_brief(job_id, body.model_dump(exclude_none=True))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/outline")
    def get_job_outline(job_id: str):
        try:
            return service.get_job_outline(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc

    @api.patch("/api/jobs/{job_id}/outline")
    def update_job_outline(job_id: str, body: OutlineUpdateRequest):
        try:
            return service.update_job_outline(job_id, body.model_dump())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/outline/generate")
    def generate_job_outline(job_id: str, body: OutlineGenerateRequest | None = None):
        try:
            return service.generate_job_outline(job_id, body.model_dump(exclude_none=True) if body else None)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.put("/api/jobs/{job_id}/script")
    def update_job_script(job_id: str, body: ScriptUpdateRequest):
        try:
            return service.update_job_script(job_id, body.model_dump(exclude_none=True))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # ------------------------------------------------------------------
    # THUMBNAIL STUDIO ROUTES (FABRIC.JS LAYER ENGINE + NANOTHUMBNAIL)
    # ------------------------------------------------------------------

    @api.get("/api/jobs/{job_id}/thumbnail-studio")
    def get_thumbnail_studio(job_id: str):
        try:
            return service.thumbnail_studio_state(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/design")
    async def save_thumbnail_studio_design(job_id: str, request: Request):
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                payload = {}
            return service.save_thumbnail_design(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/auto-design")
    async def auto_design_thumbnail_studio(job_id: str, request: Request):
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            return service.auto_design_thumbnail(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/generate-bg")
    async def generate_thumbnail_studio_bg(job_id: str, request: Request):
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            return service.generate_thumbnail_background(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/upload-image")
    async def upload_thumbnail_studio_image(job_id: str, request: Request):
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("Payload không hợp lệ")
            return service.upload_thumbnail_image(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/export")
    async def export_thumbnail_studio_image(job_id: str, request: Request):
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("Payload không hợp lệ")
            return service.export_thumbnail_image(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/export-ab-pack")
    async def export_thumbnail_ab_pack_route(job_id: str, request: Request):
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            return service.export_thumbnail_ab_pack(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/select-winner")
    async def select_thumbnail_winner_route(job_id: str, request: Request):
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            return service.select_thumbnail_winner(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/lock-thumbnail-dna")
    async def lock_job_thumbnail_dna_route(job_id: str, request: Request):
        try:
            notes = ""
            overrides: dict = {}
            try:
                body = await request.json()
                if isinstance(body, dict):
                    notes = str(body.get("notes") or body.get("override_name") or "")
                    overrides = body
            except Exception:
                pass
            from services.thumbnail_dna_service import ThumbnailDnaService
            tds = ThumbnailDnaService()
            return tds.lock_job_thumbnail_dna_to_channel(job_id, notes=notes, overrides=overrides)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/radar/channel-profiles/{profile_id}/lock-thumbnail-dna")
    async def lock_channel_profile_thumbnail_dna_route(profile_id: str, request: Request):
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            from services.thumbnail_dna_service import ThumbnailDnaService
            tds = ThumbnailDnaService()
            return tds.lock_channel_profile_thumbnail_dna(profile_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @api.get("/")
    def index():
        path = STATIC_DIR / "index.html"
        if path.exists():
            return FileResponse(path)
        return {"app": "COFI DOCUMENTARY", "api": "/api/health"}

    @api.on_event("startup")
    def startup_required_backends():
        starter = getattr(service, "start_required_backends", None)
        if callable(starter):
            api.state.required_backends = starter()

    @api.on_event("shutdown")
    def shutdown_embedded_tools():
        service.stop_cofi_studio_embed()

    return api


_default_app: FastAPI | None = None


async def app(scope, receive, send):
    """Lazy ASGI entrypoint so importing this module never mutates production job state."""
    global _default_app
    if _default_app is None:
        from server import create_app as create_modular_app
        _default_app = create_modular_app()
    await _default_app(scope, receive, send)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("COFI_DOCUMENTARY_PORT", "8878")), reload=False)
