from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field

PHASES = ("plan", "voice", "visuals", "ai_visual", "edit", "seo", "qc")

REQUIRED_ARTIFACTS = {
    "plan": ("research.md", "script.md", "visual_manifest.json"),
    "voice": ("voice_manifest.json", "subtitles.srt", "audio/narration.wav"),
    "visuals": ("visual_manifest.json", "visual_prompts.json"),
    "ai_visual": ("ai_visual_manifest.json", "asset_registry.json"),
    "edit": ("edit_session.json", "edit_checkpoint.json"),
    "seo": ("seo_package.json",),
    "qc": ("render_manifest.json", "director_report.md", "final_manifest.json"),
}


class ChannelProfile(BaseModel):
    id: str = ""
    channel_profile_id: Optional[str] = None
    label: Optional[str] = None
    market: str = "KR"
    default_language: Optional[str] = None
    language: Optional[str] = None
    voice_id: str = ""
    secondary_voice_id: Optional[str] = None
    default_duration_minutes: Optional[float] = None
    target_duration_minutes: Optional[float] = None
    default_visual_strategy: Optional[str] = None
    visual_strategy: Optional[str] = None
    default_ai_media_mode: Optional[str] = None
    ai_media_mode: Optional[str] = None
    default_ai_style_mode: Optional[str] = None
    default_ai_custom_style: Optional[str] = None
    dna_mode: Optional[str] = None
    own_channel_ref: str = ""
    competitor_refs: list[str] = Field(default_factory=list)
    allowed_topics: Optional[str] = None
    forbidden_topics: Optional[str] = None
    monetization_safety_policy: Optional[str] = None
    voice_and_structure: Optional[str] = None
    reference_image_policy: Optional[str] = None
    cta_strategy: Optional[str] = None
    default_creative_brief: Optional[dict[str, Any]] = None
    editing_dna: Optional[dict[str, Any]] = None
    self_learning_memory: Optional[dict[str, Any]] = None
    editorial_dna: Optional[dict[str, Any]] = None
    topic_memory: Optional[list[dict[str, Any]]] = None
    seo_keyword_dna: Optional[dict[str, Any]] = None
    thumbnail_dna: Optional[dict[str, Any]] = None
    thumbnail_dna_history: Optional[list[dict[str, Any]]] = None

    class Config:
        extra = "allow"


def effective_phases(job: dict[str, object] | None = None) -> tuple[str, ...]:
    payload = job or {}
    strategy = str(payload.get("visual_strategy") or "full_footage").strip().lower()
    if strategy == "footage_first":
        strategy = "full_footage"
    elif strategy in {"semi_content", "ban_content", "edit_footage"}:
        strategy = "edit_direct_footage"
    if strategy == "full_footage":
        return tuple(phase for phase in PHASES if phase != "ai_visual")
    return PHASES


def phase_state() -> dict[str, object]:
    return {
        "status": "pending",
        "started_at": None,
        "finished_at": None,
        "error": None,
        "last_message": None,
    }
