"""
Channel Profile Service for CofiDocumentary (Milestone 1).
Provides complete CRUD, cloning, schema validation, and persistence for Channel Profiles.
"""

from __future__ import annotations

import copy
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORAGE_FILE = ROOT / "data" / "channel_profiles.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ==============================================================================
# PYDANTIC DATA MODELS
# ==============================================================================

class SubtitleStyleModel(BaseModel):
    font_family: str = "Pretendard, sans-serif"
    color: str = "#ffffff"
    highlight_color: str = "#38bdf8"
    font_size: int = 42


class AudioRulesModel(BaseModel):
    music_ducking_db: float = -18.0
    sfx_hit_on_chapter: bool = True
    tension_drone_under_interrogation: bool = False


class EditingDnaModel(BaseModel):
    version: int = 1
    pacing: float = 5.0
    typical_pacing_sec: float = 5.0
    visual_mix: dict[str, float] = Field(
        default_factory=lambda: {"footage": 0.5, "ai": 0.35, "motion": 0.15}
    )
    editing_archetypes: list[str] = Field(
        default_factory=lambda: [
            "2.5d_satellite_terrain_flyover",
            "technical_hud_telemetry_gauge",
            "cinematic_chapter_card_hit"
        ]
    )
    subtitle_style: dict[str, Any] = Field(
        default_factory=lambda: {
            "font_family": "Pretendard, sans-serif",
            "color": "#ffffff",
            "highlight_color": "#38bdf8",
            "font_size": 42
        }
    )
    color_grade: str = "technical_cool_cyan"
    audio_rules: dict[str, Any] = Field(
        default_factory=lambda: {
            "music_ducking_db": -18.0,
            "sfx_hit_on_chapter": True,
            "tension_drone_under_interrogation": False
        }
    )


class UpgradeRulesModel(BaseModel):
    what_to_stop_doing: list[str] = Field(default_factory=list)
    what_to_double_down_on: list[str] = Field(default_factory=list)
    next_video_upgrades: list[str] = Field(default_factory=list)


class SelfLearningMemoryModel(BaseModel):
    analyzed_videos_count: int = 0
    winners: list[Any] = Field(default_factory=list)
    underperformers: list[Any] = Field(default_factory=list)
    winner_patterns: list[str] = Field(default_factory=list)
    losing_patterns: list[str] = Field(default_factory=list)
    upgrade_rules: dict[str, Any] = Field(
        default_factory=lambda: {
            "what_to_stop_doing": [],
            "what_to_double_down_on": [],
            "next_video_upgrades": []
        }
    )
    next_video_upgrades: list[str] = Field(default_factory=list)


class DefaultCreativeBriefModel(BaseModel):
    market: str = "KR"
    language: str = "ko"
    target_duration_minutes: float = 30.0
    ai_media_mode: str = "image"
    visual_strategy: str = "hybrid"
    narrative_angle: str = "Investigation & Evidence"
    writing_style: str = "Cold investigative documentary"
    hook_archetype: str = "High curiosity opening paradox"
    editing_archetypes: list[str] = Field(
        default_factory=lambda: ["2.5D maps", "document telemetry", "chapter title cards"]
    )
    opening_hook: str = "Opening hook line."
    notes: str = "Channel profile notes."
    custom_rules: str = "Standard DNA compliance"
    cta_strategy: str = ""


class TopicMemoryEntryModel(BaseModel):
    id: str | None = None
    job_id: str = ""
    candidate_id: str = ""
    case_real_name_zh: str = ""
    pipe_case_tag: str = ""
    topic_stream: str = ""
    title: str = ""
    topic: str = ""
    tags: list[str] = Field(default_factory=list)
    anchors: list[str] = Field(default_factory=list)
    created_at: str | None = None
    source: str = "job"


class SeoKeywordDnaModel(BaseModel):
    primary_title_keyword: str = ""
    primary_title_keyword_meaning_vi: str = ""
    keyword_placement_rule: str = "smart_seo_flexible"
    secondary_anchor_keywords: list[str] = Field(default_factory=list)
    mandatory_hashtags: list[str] = Field(default_factory=list)
    default_seo_tags: list[str] = Field(default_factory=list)


class ThumbnailDnaModel(BaseModel):
    style_preset: str = "cold_forensic_noir"
    preset_id: str | None = None
    visual_signature: Any = ""
    color_palette: dict[str, Any] = Field(
        default_factory=lambda: {
            "primary": "#FFE84A",
            "secondary": "#0F172A",
            "accent": "#EF4444",
            "background": "#020617"
        }
    )
    typography_preset: dict[str, Any] = Field(
        default_factory=lambda: {
            "font_family": "Pretendard",
            "title_weight": "900",
            "stroke_color": "#000000",
            "stroke_width": 6,
            "text_transform": "uppercase"
        }
    )
    fonts: dict[str, Any] | None = None
    layout_template: str = "broadcast_left_heavy"
    layout_archetype: str | None = None
    reference_character_path: str = ""
    mascot_lock: bool = False
    version: int = 1

    @model_validator(mode="before")
    @classmethod
    def _map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "preset_id" in data and "style_preset" not in data:
                data["style_preset"] = data["preset_id"]
            if "style_preset" in data and "preset_id" not in data:
                data["preset_id"] = data["style_preset"]
            if "layout_archetype" in data and "layout_template" not in data:
                data["layout_template"] = data["layout_archetype"]
            if "layout_template" in data and "layout_archetype" not in data:
                data["layout_archetype"] = data["layout_template"]
            if "fonts" in data and "typography_preset" not in data:
                data["typography_preset"] = data["fonts"]
            if "typography_preset" in data and "fonts" not in data:
                data["fonts"] = data["typography_preset"]
        return data

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["preset_id"] = d.get("style_preset") or "cold_forensic_noir"
        d["style_preset"] = d["preset_id"]
        d["layout_archetype"] = d.get("layout_template") or "broadcast_left_heavy"
        d["layout_template"] = d["layout_archetype"]
        d["fonts"] = d.get("typography_preset") or {}
        d["typography_preset"] = d["fonts"]
        return d


class ChannelProfileCreateModel(BaseModel):
    label: str | None = None
    market: str = "KR"
    default_language: str | None = None
    language: str | None = None
    voice_id: str = ""
    default_voice_id: str | None = None
    secondary_voice_id: str | None = None
    default_duration_minutes: float | None = Field(default=None, ge=2, le=180)
    target_duration_minutes: float | None = Field(default=None, ge=2, le=180)
    default_visual_strategy: str | None = None
    visual_strategy: str | None = None
    default_ai_media_mode: str | None = None
    ai_media_mode: str | None = None
    default_ai_style_mode: str | None = None
    default_ai_custom_style: str | None = None
    dna_mode: str | None = None
    own_channel_ref: str = ""
    competitor_refs: list[str] = Field(default_factory=list)
    allowed_topics: str | None = None
    forbidden_topics: str | None = None
    monetization_safety_policy: str | None = None
    voice_and_structure: str | None = None
    reference_image_policy: str | None = None
    cta_strategy: str | None = None
    default_creative_brief: dict[str, Any] | None = None
    editing_dna: dict[str, Any] | None = None
    self_learning_memory: dict[str, Any] | None = None
    editorial_dna: dict[str, Any] | None = None
    topic_memory: list[dict[str, Any]] | None = None
    topic_streams: list[dict[str, Any]] | None = None
    suggested_topic_history: list[dict[str, Any]] | None = None
    topic_research_round: int | None = None
    seo_keyword_dna: dict[str, Any] | None = None
    thumbnail_dna: dict[str, Any] | None = None
    thumbnail_dna_history: list[dict[str, Any]] | None = None
    rhythm_dna: dict[str, Any] | None = None
    voice_signature: dict[str, Any] | None = None
    auto_design_voice: bool | None = None
    voice_source_mode: str | None = None
    base_voice_id: str | None = None
    voice_sample_base64: str | None = None
    voice_sample_filename: str | None = None
    voice_sample_ref_text: str | None = None
    voice_custom_direction: str | None = None


class ChannelProfileUpdateModel(BaseModel):
    label: str | None = None
    market: str | None = None
    default_language: str | None = None
    language: str | None = None
    voice_id: str | None = None
    default_voice_id: str | None = None
    secondary_voice_id: str | None = None
    default_duration_minutes: float | None = Field(default=None, ge=2, le=180)
    target_duration_minutes: float | None = Field(default=None, ge=2, le=180)
    default_visual_strategy: str | None = None
    visual_strategy: str | None = None
    default_ai_media_mode: str | None = None
    ai_media_mode: str | None = None
    default_ai_style_mode: str | None = None
    default_ai_custom_style: str | None = None
    dna_mode: str | None = None
    own_channel_ref: str | None = None
    competitor_refs: list[str] | None = None
    allowed_topics: str | None = None
    forbidden_topics: str | None = None
    monetization_safety_policy: str | None = None
    voice_and_structure: str | None = None
    reference_image_policy: str | None = None
    cta_strategy: str | None = None
    default_creative_brief: dict[str, Any] | None = None
    editing_dna: dict[str, Any] | None = None
    self_learning_memory: dict[str, Any] | None = None
    editorial_dna: dict[str, Any] | None = None
    topic_memory: list[dict[str, Any]] | None = None
    topic_streams: list[dict[str, Any]] | None = None
    suggested_topic_history: list[dict[str, Any]] | None = None
    topic_research_round: int | None = None
    seo_keyword_dna: dict[str, Any] | None = None
    thumbnail_dna: dict[str, Any] | None = None
    thumbnail_dna_history: list[dict[str, Any]] | None = None
    rhythm_dna: dict[str, Any] | None = None
    voice_signature: dict[str, Any] | None = None
    auto_design_voice: bool | None = None
    voice_source_mode: str | None = None
    base_voice_id: str | None = None
    voice_sample_base64: str | None = None
    voice_sample_filename: str | None = None
    voice_sample_ref_text: str | None = None
    voice_custom_direction: str | None = None


class ChannelProfileCloneModel(BaseModel):
    label: str | None = None


class ChannelProfile(BaseModel):
    id: str = ""
    channel_profile_id: str | None = None
    label: str | None = None
    market: str = "KR"
    default_language: str | None = None
    language: str | None = None
    voice_id: str = ""
    secondary_voice_id: str | None = None
    default_duration_minutes: float | None = None
    target_duration_minutes: float | None = None
    default_visual_strategy: str | None = None
    visual_strategy: str | None = None
    default_ai_media_mode: str | None = None
    ai_media_mode: str | None = None
    default_ai_style_mode: str | None = None
    default_ai_custom_style: str | None = None
    dna_mode: str | None = None
    own_channel_ref: str = ""
    competitor_refs: list[str] = Field(default_factory=list)
    allowed_topics: str | None = None
    forbidden_topics: str | None = None
    monetization_safety_policy: str | None = None
    voice_and_structure: str | None = None
    reference_image_policy: str | None = None
    cta_strategy: str | None = None
    default_creative_brief: dict[str, Any] | None = None
    editing_dna: dict[str, Any] | None = None
    self_learning_memory: dict[str, Any] | None = None
    editorial_dna: dict[str, Any] | None = None
    topic_memory: list[dict[str, Any]] | None = None
    topic_streams: list[dict[str, Any]] | None = None
    suggested_topic_history: list[dict[str, Any]] | None = None
    topic_research_round: int | None = None
    seo_keyword_dna: dict[str, Any] | None = None
    thumbnail_dna: dict[str, Any] | None = None
    thumbnail_dna_history: list[dict[str, Any]] | None = None

    class Config:
        extra = "allow"


# ==============================================================================
# SERVICE CLASS
# ==============================================================================

class ChannelProfileService:
    _BACKFILLED_STORAGE_MTIMES: dict[str, float] = {}

    def __init__(self, storage_path: Path | str | None = None, documentary_service: Any = None):
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_STORAGE_FILE
        self.documentary_service = documentary_service
        self._lock = threading.RLock()
        try:
            resolved_key = str(self.storage_path.resolve())
            cur_mtime = self.storage_path.stat().st_mtime if self.storage_path.exists() else -1.0
            if self._BACKFILLED_STORAGE_MTIMES.get(resolved_key) != cur_mtime:
                self.backfill_topic_memory()
                new_mtime = self.storage_path.stat().st_mtime if self.storage_path.exists() else cur_mtime
                self._BACKFILLED_STORAGE_MTIMES[resolved_key] = new_mtime
        except Exception:
            pass

    def _read_profiles_raw(self) -> list[dict[str, Any]]:
        with self._lock:
            if not self.storage_path.exists():
                return []
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                profiles = [dict(p) for p in data.get("profiles", []) if isinstance(p, dict)]
                for p in profiles:
                    if "topic_memory" not in p or not isinstance(p["topic_memory"], list):
                        p["topic_memory"] = []
                    if "seo_keyword_dna" not in p or not isinstance(p["seo_keyword_dna"], dict):
                        p["seo_keyword_dna"] = {}
                    if "thumbnail_dna" not in p or not isinstance(p["thumbnail_dna"], dict):
                        p["thumbnail_dna"] = {}
                    if "thumbnail_dna_history" not in p or not isinstance(p["thumbnail_dna_history"], list):
                        p["thumbnail_dna_history"] = []
                    vid_top = str(p.get("voice_id") or p.get("default_voice_id") or "").strip()
                    if vid_top:
                        p["voice_id"] = vid_top
                        p["default_voice_id"] = vid_top
                        if isinstance(p.get("voice_signature"), dict):
                            p["voice_signature"] = {**p["voice_signature"], "voice_id": vid_top}
                            src_mode = str(p["voice_signature"].get("source_mode") or "").strip().lower()
                            if not p["voice_signature"].get("base_voice_id") or (
                                src_mode != "user_sample"
                                and str(p.get("default_language") or p.get("language") or "").startswith("ko")
                            ):
                                p["voice_signature"]["base_voice_id"] = "09c70cc1-cc86-4905-b65b-3967209c3175"
                return profiles
            except Exception:
                return []

    def _write_profiles_raw(self, profiles: list[dict[str, Any]]) -> None:
        with self._lock:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.storage_path.with_suffix(".tmp")
            payload = {"profiles": profiles}
            tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp_path, self.storage_path)

            # Sync in-memory if documentary_service is attached
            if self.documentary_service is not None:
                try:
                    with getattr(self.documentary_service, "_channel_profile_lock", threading.RLock()):
                        self.documentary_service._channel_profiles = [dict(p) for p in profiles]
                except Exception:
                    pass

    def list_profiles(self) -> list[dict[str, Any]]:
        profiles = self._read_profiles_raw()
        return sorted(
            profiles,
            key=lambda p: str(p.get("updated_at") or p.get("created_at") or ""),
            reverse=True,
        )

    def get_profile(self, profile_id: str) -> dict[str, Any]:
        profiles = self._read_profiles_raw()
        target = next(
            (p for p in profiles if str(p.get("id")) == str(profile_id) or str(p.get("channel_profile_id")) == str(profile_id)),
            None
        )
        if target is None:
            raise KeyError(f"Channel profile {profile_id} not found")
        return dict(target)

    def create_profile(self, payload: dict[str, Any] | ChannelProfileCreateModel) -> dict[str, Any]:
        if isinstance(payload, BaseModel):
            raw_data = payload.model_dump(exclude_unset=True)
        else:
            raw_data = dict(payload)

        profile_id = str(raw_data.get("id") or f"channel-{uuid4().hex[:10]}")
        stamp = _now()

        market = str(raw_data.get("market") or "KR").upper().strip() or "KR"
        lang_map = {"KR": "ko", "JP": "ja", "US": "en", "VN": "vi"}
        default_lang = str(
            raw_data.get("default_language")
            or raw_data.get("language")
            or lang_map.get(market, "ko")
        ).strip() or "ko"

        duration = raw_data.get("default_duration_minutes") or raw_data.get("target_duration_minutes") or 30
        try:
            duration = float(duration)
            if duration.is_integer():
                duration = int(duration)
        except Exception:
            duration = 30

        visual_strategy = str(
            raw_data.get("visual_strategy")
            or raw_data.get("default_visual_strategy")
            or "hybrid"
        ).strip().lower()
        if visual_strategy in {"semi_content", "ban_content", "edit_footage"}:
            visual_strategy = "edit_direct_footage"
        if visual_strategy not in {"full_ai", "full_footage", "hybrid", "evidence_footage", "edit_direct_footage"}:
            visual_strategy = "hybrid"

        ai_media_mode = str(
            raw_data.get("ai_media_mode")
            or raw_data.get("default_ai_media_mode")
            or "image"
        ).strip().lower()
        if ai_media_mode not in {"image", "video", "mixed"}:
            ai_media_mode = "image"

        label = str(raw_data.get("label") or "").strip() or f"Channel Profile {profile_id}"

        # Initialize Default Creative Brief
        brief_data = dict(raw_data.get("default_creative_brief") or {})
        brief = {
            "market": str(brief_data.get("market") or market),
            "language": str(brief_data.get("language") or default_lang),
            "target_duration_minutes": float(brief_data.get("target_duration_minutes") or duration),
            "ai_media_mode": str(brief_data.get("ai_media_mode") or ai_media_mode),
            "visual_strategy": str(brief_data.get("visual_strategy") or visual_strategy),
            "narrative_angle": str(brief_data.get("narrative_angle") or raw_data.get("voice_and_structure") or "Investigation & Fact-finding"),
            "writing_style": str(brief_data.get("writing_style") or raw_data.get("voice_and_structure") or "Cold investigative documentary"),
            "hook_archetype": str(brief_data.get("hook_archetype") or "High curiosity opening paradox"),
            "editing_archetypes": list(brief_data.get("editing_archetypes") or ["2.5D maps", "document telemetry", "chapter title cards"]),
            "opening_hook": str(brief_data.get("opening_hook") or "Opening hook statement."),
            "notes": str(brief_data.get("notes") or raw_data.get("notes") or label),
            "custom_rules": str(brief_data.get("custom_rules") or raw_data.get("custom_rules") or "Standard DNA compliance"),
            "cta_strategy": str(brief_data.get("cta_strategy") or raw_data.get("cta_strategy") or "")
        }

        # Initialize Editing DNA (preserve custom capability flags alongside normalized defaults)
        dna_data = dict(raw_data.get("editing_dna") or {})
        editing_dna = {
            **dna_data,
            "version": int(dna_data.get("version") or 1),
            "pacing": float(dna_data.get("pacing") or dna_data.get("typical_pacing_sec") or 5.0),
            "typical_pacing_sec": float(dna_data.get("typical_pacing_sec") or dna_data.get("pacing") or 5.0),
            "visual_mix": dict(dna_data.get("visual_mix") or {"footage": 0.5, "ai": 0.35, "motion": 0.15}),
            "editing_archetypes": list(dna_data.get("editing_archetypes") or [
                "2.5d_satellite_terrain_flyover",
                "technical_hud_telemetry_gauge",
                "cinematic_chapter_card_hit"
            ]),
            "subtitle_style": dict(dna_data.get("subtitle_style") or {
                "font_family": "Pretendard, sans-serif",
                "color": "#ffffff",
                "highlight_color": "#38bdf8",
                "font_size": 42
            }),
            "color_grade": dna_data.get("color_grade") or "technical_cool_cyan",
            "audio_rules": dict(dna_data.get("audio_rules") or {
                "music_ducking_db": -18.0,
                "sfx_hit_on_chapter": True,
                "tension_drone_under_interrogation": False
            })
        }

        # Initialize Self Learning Memory
        slm_data = dict(raw_data.get("self_learning_memory") or {})
        self_learning_memory = {
            "analyzed_videos_count": int(slm_data.get("analyzed_videos_count") or 0),
            "winners": list(slm_data.get("winners") or []),
            "underperformers": list(slm_data.get("underperformers") or []),
            "winner_patterns": list(slm_data.get("winner_patterns") or slm_data.get("winners") or []),
            "losing_patterns": list(slm_data.get("losing_patterns") or slm_data.get("underperformers") or []),
            "upgrade_rules": dict(slm_data.get("upgrade_rules") or {
                "what_to_stop_doing": [],
                "what_to_double_down_on": [],
                "next_video_upgrades": []
            }),
            "next_video_upgrades": list(slm_data.get("next_video_upgrades") or [])
        }

        profile = {
            "id": profile_id,
            "channel_profile_id": profile_id,
            "label": label,
            "market": market,
            "default_language": default_lang,
            "language": default_lang,
            "voice_id": str(raw_data.get("voice_id") or raw_data.get("default_voice_id") or ""),
            "default_voice_id": str(raw_data.get("default_voice_id") or raw_data.get("voice_id") or "") or None,
            "secondary_voice_id": str(raw_data.get("secondary_voice_id")) if raw_data.get("secondary_voice_id") else None,
            "default_duration_minutes": duration,
            "target_duration_minutes": duration,
            "default_visual_strategy": visual_strategy,
            "visual_strategy": visual_strategy,
            "default_ai_media_mode": ai_media_mode,
            "ai_media_mode": ai_media_mode,
            "default_ai_style_mode": str(raw_data.get("default_ai_style_mode") or "custom"),
            "default_ai_custom_style": str(raw_data.get("default_ai_custom_style") or ""),
            "dna_mode": str(raw_data.get("dna_mode") or "radar_hybrid"),
            "own_channel_ref": str(raw_data.get("own_channel_ref") or ""),
            "own_channel": dict(raw_data.get("own_channel") or {}),
            "competitor_refs": list(raw_data.get("competitor_refs") or []),
            "competitors": list(raw_data.get("competitors") or []),
            "allowed_topics": str(raw_data.get("allowed_topics") or ""),
            "forbidden_topics": str(raw_data.get("forbidden_topics") or ""),
            "monetization_safety_policy": str(raw_data.get("monetization_safety_policy") or ""),
            "voice_and_structure": str(raw_data.get("voice_and_structure") or ""),
            "reference_image_policy": str(raw_data.get("reference_image_policy") or ""),
            "cta_strategy": str(raw_data.get("cta_strategy") or brief.get("cta_strategy") or ""),
            "default_creative_brief": brief,
            "editing_dna": editing_dna,
            "self_learning_memory": self_learning_memory,
            "editing_dna_history": [],
            "editorial_dna": dict(raw_data.get("editorial_dna") or {}),
            "topic_memory": list(raw_data.get("topic_memory") or []),
            "seo_keyword_dna": {
                "primary_title_keyword": str((raw_data.get("seo_keyword_dna") or {}).get("primary_title_keyword") or ""),
                "primary_title_keyword_meaning_vi": str((raw_data.get("seo_keyword_dna") or {}).get("primary_title_keyword_meaning_vi") or ""),
                "keyword_placement_rule": str((raw_data.get("seo_keyword_dna") or {}).get("keyword_placement_rule") or "smart_seo_flexible"),
                "secondary_anchor_keywords": list((raw_data.get("seo_keyword_dna") or {}).get("secondary_anchor_keywords") or []),
                "mandatory_hashtags": list((raw_data.get("seo_keyword_dna") or {}).get("mandatory_hashtags") or []),
                "default_seo_tags": list((raw_data.get("seo_keyword_dna") or {}).get("default_seo_tags") or []),
            },
            "thumbnail_dna": dict(raw_data.get("thumbnail_dna") or {
                "style_preset": "cold_forensic_noir",
                "visual_signature": "",
                "color_palette": {"primary": "#FFE84A", "secondary": "#0F172A", "accent": "#EF4444", "background": "#020617"},
                "typography_preset": {"font_family": "Pretendard", "title_weight": "900", "stroke_color": "#000000", "stroke_width": 6, "text_transform": "uppercase"},
                "layout_template": "broadcast_left_heavy",
                "reference_character_path": "",
                "mascot_lock": False,
                "version": 1,
            }),
            "thumbnail_dna_history": [],
            "rhythm_dna": dict(raw_data.get("rhythm_dna") or {}),
            "voice_signature": dict(raw_data.get("voice_signature") or {}),
            "created_at": stamp,
            "updated_at": stamp,
        }

        voice_custom_dir = str(raw_data.get("voice_custom_direction") or "").strip()
        pref_base_vid = str(raw_data.get("base_voice_id") or "").strip() or None
        if not profile["rhythm_dna"]:
            try:
                from services.voice_rhythm_specialist import VoiceRhythmSpecialistService

                profile["rhythm_dna"] = VoiceRhythmSpecialistService().analyze_profile_rhythm_dna(
                    profile,
                    custom_direction=voice_custom_dir,
                    preferred_base_voice_id=pref_base_vid,
                )
            except Exception:
                profile["rhythm_dna"] = {}

        with self._lock:
            profiles = self._read_profiles_raw()
            profiles.append(profile)
            self._write_profiles_raw(profiles)

        sample_b64 = str(raw_data.get("voice_sample_base64") or "").strip() or None
        should_auto_design = bool(raw_data.get("auto_design_voice") is True or sample_b64)
        if should_auto_design:
            try:
                from services.voice_rhythm_specialist import VoiceRhythmSpecialistService

                designed = VoiceRhythmSpecialistService().design_and_bind_profile_voice(
                    profile,
                    profile_service=self,
                    source_mode=str(raw_data.get("voice_source_mode") or ("user_sample" if sample_b64 else "base_voice")),
                    base_voice_id=pref_base_vid,
                    sample_audio_base64=sample_b64,
                    sample_filename=str(raw_data.get("voice_sample_filename") or "sample.wav"),
                    ref_text=str(raw_data.get("voice_sample_ref_text") or "") or None,
                    custom_direction=voice_custom_dir,
                    persist_to_profile=True,
                )
                if isinstance(designed.get("profile"), dict):
                    profile = designed["profile"]
            except Exception as exc:
                profile["voice_specialist_warning"] = str(exc)

        return profile

    def clone_profile(self, profile_id: str, new_label: str | None = None) -> dict[str, Any]:
        existing = self.get_profile(profile_id)

        cloned = copy.deepcopy(existing)
        new_id = f"channel-{uuid4().hex[:10]}"
        stamp = _now()

        cloned["id"] = new_id
        cloned["channel_profile_id"] = new_id
        original_label = str(existing.get("label") or "Channel Profile")
        cloned["label"] = str(new_label or f"{original_label} (Clone)").strip()
        cloned["editing_dna_history"] = []
        cloned["thumbnail_dna"] = copy.deepcopy(existing.get("thumbnail_dna") or {})
        cloned["thumbnail_dna_history"] = []
        cloned["topic_memory"] = [copy.deepcopy(m) for m in (existing.get("topic_memory") or [])]
        cloned["seo_keyword_dna"] = copy.deepcopy(existing.get("seo_keyword_dna") or {})
        cloned["created_at"] = stamp
        cloned["updated_at"] = stamp

        with self._lock:
            profiles = self._read_profiles_raw()
            profiles.append(cloned)
            self._write_profiles_raw(profiles)

        return cloned

    def update_profile(self, profile_id: str, payload: dict[str, Any] | ChannelProfileUpdateModel) -> dict[str, Any]:
        if isinstance(payload, BaseModel):
            patch = payload.model_dump(exclude_unset=True)
        else:
            patch = dict(payload)

        auto_design_voice = patch.pop("auto_design_voice", None)
        voice_source_mode = patch.pop("voice_source_mode", None)
        base_voice_id = patch.pop("base_voice_id", None)
        voice_sample_base64 = patch.pop("voice_sample_base64", None)
        voice_sample_filename = patch.pop("voice_sample_filename", None)
        voice_sample_ref_text = patch.pop("voice_sample_ref_text", None)
        voice_custom_direction = patch.pop("voice_custom_direction", None)

        with self._lock:
            profiles = self._read_profiles_raw()
            index = next(
                (i for i, p in enumerate(profiles) if str(p.get("id")) == str(profile_id) or str(p.get("channel_profile_id")) == str(profile_id)),
                None
            )
            if index is None:
                raise KeyError(f"Channel profile {profile_id} not found")

            existing = profiles[index]
            updated = dict(existing)

            # In-place update preserving non-provided fields
            for key, value in patch.items():
                if value is None:
                    continue
                if key in {"default_creative_brief", "editing_dna", "self_learning_memory", "seo_keyword_dna", "rhythm_dna", "voice_signature"}:
                    if not isinstance(value, dict):
                        raise ValueError(f"Field '{key}' must be an object")
                    merged_dict = dict(existing.get(key) or {})
                    merged_dict.update(value)
                    updated[key] = merged_dict
                elif key == "thumbnail_dna":
                    if not isinstance(value, dict):
                        raise ValueError("Field 'thumbnail_dna' must be an object")
                    existing_tdna = copy.deepcopy(existing.get("thumbnail_dna") or {})
                    for subk, subv in value.items():
                        if isinstance(subv, dict) and isinstance(existing_tdna.get(subk), dict):
                            sub_merged = dict(existing_tdna[subk])
                            sub_merged.update(subv)
                            existing_tdna[subk] = sub_merged
                        else:
                            existing_tdna[subk] = subv
                    updated["thumbnail_dna"] = existing_tdna
                elif key == "topic_memory":
                    if not isinstance(value, list):
                        raise ValueError("Field 'topic_memory' must be a list")
                    updated["topic_memory"] = list(value)
                elif key in {"topic_streams", "suggested_topic_history"}:
                    if not isinstance(value, list):
                        raise ValueError(f"Field '{key}' must be a list")
                    updated[key] = list(value)
                else:
                    updated[key] = value

            # Enforce identity consistency
            updated["id"] = str(existing.get("id") or profile_id)
            updated["channel_profile_id"] = updated["id"]
            if "visual_strategy" in patch:
                updated["default_visual_strategy"] = patch["visual_strategy"]
            if "default_visual_strategy" in patch:
                updated["visual_strategy"] = patch["default_visual_strategy"]
            if "language" in patch:
                updated["default_language"] = patch["language"]
            if "default_language" in patch:
                updated["language"] = patch["default_language"]
            if "voice_id" in patch and patch["voice_id"]:
                updated["default_voice_id"] = patch["voice_id"]
            elif "default_voice_id" in patch and patch["default_voice_id"] and not patch.get("voice_id"):
                updated["voice_id"] = patch["default_voice_id"]

            updated["updated_at"] = _now()
            profiles[index] = updated
            self._write_profiles_raw(profiles)

        if auto_design_voice is True or voice_sample_base64:
            try:
                from services.voice_rhythm_specialist import VoiceRhythmSpecialistService

                designed = VoiceRhythmSpecialistService().design_and_bind_profile_voice(
                    updated,
                    profile_service=self,
                    source_mode=str(voice_source_mode or ("user_sample" if voice_sample_base64 else "base_voice")),
                    base_voice_id=str(base_voice_id or "").strip() or None,
                    sample_audio_base64=str(voice_sample_base64 or "").strip() or None,
                    sample_filename=str(voice_sample_filename or "sample.wav"),
                    ref_text=str(voice_sample_ref_text or "") or None,
                    custom_direction=str(voice_custom_direction or ""),
                    persist_to_profile=True,
                )
                if isinstance(designed.get("profile"), dict):
                    updated = designed["profile"]
            except Exception as exc:
                updated["voice_specialist_warning"] = str(exc)

        return updated

    def delete_profile(self, profile_id: str) -> dict[str, Any]:
        with self._lock:
            profiles = self._read_profiles_raw()
            index = next(
                (i for i, p in enumerate(profiles) if str(p.get("id")) == str(profile_id) or str(p.get("channel_profile_id")) == str(profile_id)),
                None
            )
            if index is None:
                raise KeyError(f"Channel profile {profile_id} not found")

            removed = profiles.pop(index)
            self._write_profiles_raw(profiles)

        return dict(removed)

    @staticmethod
    def _is_synthetic_test_topic(title: str, topic: str = "", job_id: str = "") -> bool:
        t = str(title or "").strip().lower()
        tp = str(topic or "").strip().lower()
        jid = str(job_id or "").strip().lower()
        if jid.startswith("job-reverify") or jid.startswith("test-"):
            return True
        synthetic_exact = {
            "test",
            "test job",
            "test job with seo dna",
            "연쇄살인의 진실",
            "연쇄살인의 진실 (chân tướng tội phạm)",
            "사건 파일",
            "댐 붕괴의 진실",
            "댐 붕괴의 진실 (sự thật vỡ đập)",
            "automated dna inheritance test project",
            "untitled project",
        }
        if t in synthetic_exact or any(t.startswith(p) for p in ("연쇄살인의 진실 (", "댐 붕괴의 진실 (", "test job")):
            return True
        return False

    @staticmethod
    def _sibling_profile_ids(profile_id: str) -> set[str]:
        pid = str(profile_id or "").strip()
        true_crime_kr_family = {
            "channel-e544a64b7c",
            "channel-kr-truecrime-director-v2",
            "channel-kr-financial-fugitive-director-v2",
        }
        if pid in true_crime_kr_family:
            return set(true_crime_kr_family)
        return {pid} if pid else set()

    @classmethod
    def extract_rich_topic_memory_payload(
        cls,
        source_obj: dict[str, Any],
        *,
        candidate_pools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Extract rich anti-duplicate identity anchors (`candidate_id`, `case_real_name_zh`,
        `pipe_case_tag`, `topic_stream`, `tags`, `anchors`) from a job payload, memory entry,
        or matching pre-prune curated candidate.
        """
        from services.case_similarity import (
            check_case_similarity,
            extract_case_anchors_and_entities,
            extract_pipe_case_tag,
            normalize_candidate_core_slug,
        )

        data = dict(source_obj or {})
        td = data.get("topic_discovery") if isinstance(data.get("topic_discovery"), dict) else {}
        sel = td.get("selected_candidate") if isinstance(td.get("selected_candidate"), dict) else {}
        brief = data.get("creative_brief") if isinstance(data.get("creative_brief"), dict) else {}

        title = str(data.get("title") or sel.get("title") or "").strip()
        topic = str(data.get("topic") or title).strip()
        job_id = str(data.get("job_id") or data.get("id") if data.get("phases") or data.get("workspace") else data.get("job_id") or "").strip()
        candidate_id = str(data.get("candidate_id") or sel.get("id") or "").strip()
        case_real_name_zh = str(data.get("case_real_name_zh") or sel.get("case_real_name_zh") or "").strip()
        topic_stream = str(data.get("topic_stream") or sel.get("topic_stream") or "").strip()
        notes_blob = " ".join(
            filter(
                None,
                [
                    str(data.get("notes") or ""),
                    str(sel.get("note") or ""),
                    str(brief.get("custom_rules") or ""),
                ],
            )
        ).strip()

        if not case_real_name_zh and notes_blob:
            m_zh = re.search(
                r"Hồ sơ vụ án gốc xác thực:\s*([^\n\r\.]+)",
                notes_blob,
                flags=re.IGNORECASE,
            )
            if m_zh:
                case_real_name_zh = m_zh.group(1).strip()
            else:
                m_paren = re.search(r"([\u4e00-\u9fff][^\)\n\r]{4,60})", notes_blob)
                if m_paren:
                    case_real_name_zh = m_paren.group(1).strip()

        # Match against active curated candidates / reserve pools before pruning to capture exact candidate_id & case_real_name_zh
        probe_text = f"{title} {topic} {case_real_name_zh} {notes_blob}".strip()
        if candidate_pools and (not candidate_id or not case_real_name_zh or not topic_stream):
            for cand in candidate_pools:
                if not isinstance(cand, dict):
                    continue
                c_id = str(cand.get("id") or "").strip()
                c_title = str(cand.get("title") or cand.get("suggested_title") or cand.get("topic_anchor") or "").strip()
                c_zh = str(cand.get("case_real_name_zh") or "").strip()
                c_note = str(cand.get("note") or cand.get("topic_summary") or "").strip()
                if candidate_id and c_id and (
                    candidate_id == c_id
                    or (
                        normalize_candidate_core_slug(candidate_id)
                        and normalize_candidate_core_slug(candidate_id) == normalize_candidate_core_slug(c_id)
                    )
                ):
                    matched_cand = cand
                else:
                    is_match, _, _ = check_case_similarity(
                        probe_text,
                        c_title,
                        target_topic=f"{c_zh} {c_note}".strip(),
                        candidate_id=candidate_id,
                        target_candidate_id=c_id,
                    )
                    matched_cand = cand if is_match else None
                if matched_cand is not None:
                    if not candidate_id and c_id:
                        candidate_id = c_id
                    if not case_real_name_zh and c_zh:
                        case_real_name_zh = c_zh
                    if not topic_stream and matched_cand.get("topic_stream"):
                        topic_stream = str(matched_cand.get("topic_stream") or "").strip()
                    break

        pipe_case_tag = str(data.get("pipe_case_tag") or "").strip()
        if not pipe_case_tag:
            pipe_case_tag = extract_pipe_case_tag(title) or extract_pipe_case_tag(topic)

        entities, keywords = extract_case_anchors_and_entities(
            title,
            f"{topic} {case_real_name_zh}".strip(),
            notes_blob,
        )
        extra_identity_tags: list[str] = []
        core_slug = normalize_candidate_core_slug(candidate_id)
        if core_slug:
            extra_identity_tags.append(f"slug:{core_slug}")
        if pipe_case_tag:
            extra_identity_tags.append(f"pipe:{pipe_case_tag}")
        if case_real_name_zh:
            extra_identity_tags.append(case_real_name_zh)

        tags = list(dict.fromkeys(list(data.get("tags") or []) + extra_identity_tags + entities))
        anchors = list(dict.fromkeys(list(data.get("anchors") or []) + extra_identity_tags + entities + keywords))

        return {
            "id": str(data.get("id") or "") if not (data.get("phases") or data.get("workspace")) else "",
            "job_id": job_id,
            "candidate_id": candidate_id,
            "case_real_name_zh": case_real_name_zh,
            "pipe_case_tag": pipe_case_tag,
            "topic_stream": topic_stream,
            "title": title,
            "topic": topic,
            "tags": tags,
            "anchors": anchors,
            "created_at": str(data.get("created_at") or _now()),
            "source": str(data.get("source") or ("job" if job_id else "manual")),
        }

    @staticmethod
    def _deduplicate_topic_memory_list(mem_list: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
        from services.case_similarity import (
            check_case_similarity,
            extract_case_anchors_and_entities,
            extract_pipe_case_tag,
            normalize_candidate_core_slug,
        )

        if not isinstance(mem_list, list) or len(mem_list) == 0:
            return list(mem_list or []), False

        deduped: list[dict[str, Any]] = []
        changed = False
        for raw_m in mem_list:
            if not isinstance(raw_m, dict):
                changed = True
                continue
            m = dict(raw_m)
            m_title = str(m.get("title") or "").strip()
            m_topic = str(m.get("topic") or m_title).strip()
            if not m_title and not m_topic:
                changed = True
                continue
            m_id = str(m.get("id") or "")
            m_job = str(m.get("job_id") or "")
            m_cid = str(m.get("candidate_id") or "").strip()
            m_zh = str(m.get("case_real_name_zh") or "").strip()
            m_pipe = str(m.get("pipe_case_tag") or "").strip() or extract_pipe_case_tag(m_title) or extract_pipe_case_tag(m_topic)
            if m_pipe and not m.get("pipe_case_tag"):
                m["pipe_case_tag"] = m_pipe

            entities, keywords = extract_case_anchors_and_entities(m_title, f"{m_topic} {m_zh}".strip())
            extra_tags: list[str] = []
            c_slug = normalize_candidate_core_slug(m_cid)
            if c_slug:
                extra_tags.append(f"slug:{c_slug}")
            if m_pipe:
                extra_tags.append(f"pipe:{m_pipe}")
            if m_zh:
                extra_tags.append(m_zh)

            m_tags = list(dict.fromkeys(list(m.get("tags") or []) + extra_tags + entities))
            m_anchors = list(dict.fromkeys(list(m.get("anchors") or []) + extra_tags + entities + keywords))
            m["tags"] = m_tags
            m["anchors"] = m_anchors

            match_idx: int | None = None
            for idx, prev in enumerate(deduped):
                p_id = str(prev.get("id") or "")
                p_job = str(prev.get("job_id") or "")
                p_cid = str(prev.get("candidate_id") or "")
                p_zh = str(prev.get("case_real_name_zh") or "")
                p_title = str(prev.get("title") or "").strip()
                p_topic = str(prev.get("topic") or p_title).strip()
                if (m_id and m_id == p_id) or (m_job and p_job and m_job == p_job):
                    match_idx = idx
                    break
                if m_title.lower() == p_title.lower():
                    match_idx = idx
                    break
                is_dup, _, _ = check_case_similarity(
                    f"{m_title} {m_topic} {m_zh}".strip(),
                    p_title,
                    target_topic=f"{p_topic} {p_zh}".strip(),
                    target_entities=list(prev.get("tags") or []),
                    target_keywords=list(prev.get("anchors") or []),
                    candidate_id=m_cid,
                    target_candidate_id=p_cid,
                )
                if is_dup:
                    match_idx = idx
                    break

            if match_idx is not None:
                changed = True
                prev = deduped[match_idx]
                p_title = str(prev.get("title") or "").strip()
                p_is_test_prefix = p_title.upper().startswith("[VOX") or p_title.upper().startswith("[TEST")
                m_is_test_prefix = m_title.upper().startswith("[VOX") or m_title.upper().startswith("[TEST")
                if (p_is_test_prefix and not m_is_test_prefix) or (
                    not m_is_test_prefix and "([" in m_title and "([" not in p_title
                ):
                    prev["title"] = m_title
                if len(m_topic) > len(str(prev.get("topic") or "")) and not m_is_test_prefix:
                    prev["topic"] = m_topic
                if not prev.get("job_id") and m_job:
                    prev["job_id"] = m_job
                    prev["source"] = str(m.get("source") or "job")
                elif prev.get("job_id") and m_job and str(prev.get("job_id")) != m_job:
                    rel_jobs = list(dict.fromkeys(list(prev.get("related_job_ids") or []) + [m_job]))
                    prev["related_job_ids"] = rel_jobs
                if not prev.get("candidate_id") and m_cid:
                    prev["candidate_id"] = m_cid
                if not prev.get("case_real_name_zh") and m_zh:
                    prev["case_real_name_zh"] = m_zh
                if not prev.get("pipe_case_tag") and m_pipe:
                    prev["pipe_case_tag"] = m_pipe
                if not prev.get("topic_stream") and m.get("topic_stream"):
                    prev["topic_stream"] = str(m.get("topic_stream"))
                prev["tags"] = list(dict.fromkeys(list(prev.get("tags") or []) + m_tags))
                prev["anchors"] = list(dict.fromkeys(list(prev.get("anchors") or []) + m_anchors))
            else:
                deduped.append(m)

        return deduped, changed

    @classmethod
    def _collect_family_produced_records(
        cls,
        profile: dict[str, Any],
        all_profiles: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        family_ids = cls._sibling_profile_ids(str(profile.get("id") or ""))
        source_profiles = [profile]
        if all_profiles:
            for sp in all_profiles:
                if isinstance(sp, dict) and str(sp.get("id") or "") in family_ids and sp is not profile:
                    source_profiles.append(sp)

        produced_records: list[dict[str, Any]] = []
        for src_prof in source_profiles:
            for m in (src_prof.get("topic_memory") or []):
                if isinstance(m, dict) and (m.get("title") or m.get("topic")):
                    produced_records.append({
                        "candidate_id": str(m.get("candidate_id") or ""),
                        "case_real_name_zh": str(m.get("case_real_name_zh") or ""),
                        "title": str(m.get("title") or ""),
                        "topic": str(m.get("topic") or m.get("title") or ""),
                        "tags": list(m.get("tags") or []),
                        "anchors": list(m.get("anchors") or []),
                    })

            own_ch = src_prof.get("own_channel") or {}
            for wt in ((own_ch.get("dna") or {}).get("winner_titles") or []):
                wt_str = str(wt.get("title") if isinstance(wt, dict) else wt or "").strip()
                if wt_str:
                    produced_records.append({
                        "candidate_id": "",
                        "case_real_name_zh": "",
                        "title": wt_str,
                        "topic": wt_str,
                        "tags": [],
                        "anchors": [],
                    })
            for v in (own_ch.get("videos") or []):
                if isinstance(v, dict) and v.get("title"):
                    vt_str = str(v["title"]).strip()
                    produced_records.append({
                        "candidate_id": "",
                        "case_real_name_zh": "",
                        "title": vt_str,
                        "topic": vt_str,
                        "tags": [],
                        "anchors": [],
                    })
        return produced_records

    @classmethod
    def _prune_candidate_list_against_produced(
        cls,
        candidates: list[dict[str, Any]],
        produced_records: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
        from services.case_similarity import check_case_similarity

        def _cand_blob(c: dict[str, Any]) -> str:
            return " ".join([
                str(c.get("suggested_title") or c.get("title") or c.get("topic_anchor") or ""),
                str(c.get("title_vi") or ""),
                str(c.get("case_real_name_zh") or ""),
                str(c.get("topic_summary") or c.get("summary_vi") or c.get("why_now") or c.get("note") or ""),
                str(c.get("winner_cluster") or c.get("cluster_label") or ""),
                str(c.get("codex_angle") or ""),
            ]).strip()

        kept: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        changed = False
        for cand in candidates:
            if not isinstance(cand, dict):
                changed = True
                continue
            if cand.get("already_produced") is True:
                changed = True
                removed.append(cand)
                continue
            c_id = str(cand.get("id") or "")
            c_title = str(cand.get("suggested_title") or cand.get("title") or cand.get("topic_anchor") or "").strip()
            combined_cand = _cand_blob(cand)
            if not c_title:
                changed = True
                continue

            dup_found = False
            for rec in produced_records:
                rec_topic = f"{rec.get('topic') or ''} {rec.get('case_real_name_zh') or ''}".strip()
                is_dup, _, _ = check_case_similarity(
                    combined_cand,
                    str(rec.get("title") or ""),
                    target_topic=rec_topic,
                    target_entities=list(rec.get("tags") or []),
                    target_keywords=list(rec.get("anchors") or []),
                    candidate_id=c_id,
                    target_candidate_id=str(rec.get("candidate_id") or ""),
                )
                if is_dup:
                    dup_found = True
                    break
            if dup_found:
                changed = True
                removed.append(cand)
                continue

            for prev in kept:
                p_id = str(prev.get("id") or "")
                p_title = str(prev.get("suggested_title") or prev.get("title") or prev.get("topic_anchor") or "").strip()
                p_sum = _cand_blob(prev)
                is_dup_internal, _, _ = check_case_similarity(
                    combined_cand,
                    p_title,
                    target_topic=p_sum,
                    candidate_id=c_id,
                    target_candidate_id=p_id,
                )
                if is_dup_internal:
                    dup_found = True
                    break
            if dup_found:
                changed = True
                removed.append(cand)
                continue

            kept.append(cand)

        return kept, removed, (changed or len(kept) != len(candidates))

    @classmethod
    def _prune_profile_curated_candidates(
        cls,
        profile: dict[str, Any],
        all_profiles: list[dict[str, Any]] | None = None,
    ) -> bool:
        produced_records = cls._collect_family_produced_records(profile, all_profiles=all_profiles)
        mutated = False

        curated = profile.get("curated_today_candidates")
        if isinstance(curated, list) and curated:
            kept, _, chg = cls._prune_candidate_list_against_produced(curated, produced_records)
            if chg:
                profile["curated_today_candidates"] = kept
                mutated = True

        edna = profile.get("editorial_dna")
        if isinstance(edna, dict) and isinstance(edna.get("curated_today_candidates"), list) and edna.get("curated_today_candidates"):
            kept_edna, _, chg_edna = cls._prune_candidate_list_against_produced(
                list(edna.get("curated_today_candidates") or []),
                produced_records,
            )
            if chg_edna:
                edna["curated_today_candidates"] = kept_edna
                mutated = True

        latest_today = profile.get("latest_today")
        if isinstance(latest_today, dict) and isinstance(latest_today.get("plan_items"), list) and latest_today.get("plan_items"):
            kept_plan, _, chg_plan = cls._prune_candidate_list_against_produced(
                list(latest_today.get("plan_items") or []),
                produced_records,
            )
            if chg_plan:
                latest_today["plan_items"] = kept_plan
                mutated = True

        return mutated

    @classmethod
    def _auto_replenish_profile_dna_vault(
        cls,
        profile: dict[str, Any],
        all_profiles: list[dict[str, Any]] | None = None,
        vault_path: Path | None = None,
        pools_path: Path | None = None,
        min_target_count: int | None = None,
    ) -> dict[str, Any]:
        """
        Universal Auto-Replenish Engine across ALL 9 channel profiles:
        - For 2-Stream / Single-Stream True Crime profiles: tops up from `VERIFIED_TWO_STREAM_RESERVE_CASES` + `dna_replenished_vault.json`.
        - For non-True-Crime profiles (Cyber-Finance, Infrastructure, VN Fraud Lab, US Archival, KR Grace):
          tops up from `data/dna_topic_pools.json` + `DocumentaryService._default_candidates_for_profile`,
          guaranteeing at least `+1` clean replacement topic whenever a final topic is chosen for production.
        """
        try:
            from documentary.topic_research import (
                auto_replenish_dna_case_vault,
                is_two_stream_true_crime_profile,
                load_dna_replenished_vault,
                save_dna_replenished_vault,
            )
            from services.case_similarity import check_case_similarity

            pid = str(profile.get("id") or "")
            family_ids = cls._sibling_profile_ids(pid)
            produced_records = cls._collect_family_produced_records(profile, all_profiles=all_profiles)

            is_pytest_prod_guard = bool(
                os.environ.get("PYTEST_CURRENT_TEST")
                and (vault_path is None or Path(vault_path).resolve() == (Path(__file__).resolve().parents[1] / "data" / "dna_replenished_vault.json").resolve())
            )

            if is_two_stream_true_crime_profile(profile):
                sibling_curated: list[dict[str, Any]] = []
                for p in (all_profiles or []):
                    spid = str(p.get("id") or "")
                    if spid in family_ids and spid != pid:
                        for c in list(p.get("curated_today_candidates") or []):
                            if isinstance(c, dict):
                                sibling_curated.append(c)

                eff_vault_path = vault_path
                if is_pytest_prod_guard:
                    import tempfile
                    eff_vault_path = Path(tempfile.gettempdir()) / f"pytest_dna_vault_{pid}.json"

                locked_single = str(profile.get("locked_single_stream") or "").strip().lower()
                s_quota = max(10, int(min_target_count or 10)) if locked_single else 10
                m_per_stream = max(6, (int(min_target_count or 12) + 1) // 2) if not locked_single else 6
                res = auto_replenish_dna_case_vault(
                    profile,
                    produced_records=produced_records,
                    sibling_curated_candidates=sibling_curated,
                    min_curated_per_stream=m_per_stream,
                    single_stream_quota=s_quota,
                    vault_path=eff_vault_path,
                )
                return res

            # Non-True-Crime profiles: replenish from dna_topic_pools.json + DocumentaryService defaults
            repo_root = Path(__file__).resolve().parents[1]
            eff_pools_path = Path(pools_path) if pools_path is not None else (repo_root / "data" / "dna_topic_pools.json")
            pool_candidates: list[dict[str, Any]] = []
            if eff_pools_path.exists():
                try:
                    raw_pools = json.loads(eff_pools_path.read_text(encoding="utf-8"))
                    if isinstance(raw_pools, dict) and isinstance(raw_pools.get(pid), list):
                        pool_candidates.extend([dict(x) for x in raw_pools[pid] if isinstance(x, dict)])
                except Exception:
                    pass
            try:
                from documentary.service import DocumentaryService, apply_seo_keyword_dna_to_title
                for dc in DocumentaryService._default_candidates_for_profile(profile):
                    if isinstance(dc, dict):
                        pool_candidates.append(dict(dc))
            except Exception:
                apply_seo_keyword_dna_to_title = None  # type: ignore[assignment]

            curated_now = [dict(x) for x in list(profile.get("curated_today_candidates") or []) if isinstance(x, dict)]
            default_min_map = {
                "channel-cn-cyber-finance-kr": 8,
                "channel-1e24de3ab5": 6,
                "channel-vn-cn-fraud-lab": 6,
                "channel-kr-grace-letter-60m": 6,
                "channel-f6ec4dfff3": 5,
                "channel-aa913eb90d": 5,
            }
            target_len = max(int(min_target_count or 0), default_min_map.get(pid, 5), len(curated_now))
            seo_dna = profile.get("seo_keyword_dna") or {}

            # Rotate pool by produced_records count so replenishment cycles through fresh items
            rot = len(produced_records) % max(1, len(pool_candidates))
            rotated_pool = pool_candidates[rot:] + pool_candidates[:rot]

            newly_added: list[dict[str, Any]] = []
            for cand in rotated_pool:
                if len(curated_now) >= target_len:
                    break
                c_id = str(cand.get("id") or "")
                c_title = str(cand.get("title") or cand.get("suggested_title") or cand.get("topic_anchor") or "").strip()
                if not c_title:
                    continue
                c_blob = " ".join([
                    c_title,
                    str(cand.get("title_vi") or ""),
                    str(cand.get("case_real_name_zh") or ""),
                    str(cand.get("note") or cand.get("topic_summary") or ""),
                    str(cand.get("winner_cluster") or ""),
                ]).strip()
                if any(
                    check_case_similarity(
                        c_blob,
                        str(pr.get("title") or ""),
                        target_topic=f"{pr.get('topic') or ''} {pr.get('case_real_name_zh') or ''}".strip(),
                        target_entities=list(pr.get("tags") or []),
                        target_keywords=list(pr.get("anchors") or []),
                        candidate_id=c_id,
                        target_candidate_id=str(pr.get("candidate_id") or ""),
                    )[0]
                    for pr in produced_records
                ):
                    continue
                if any(
                    check_case_similarity(
                        c_blob,
                        str(ex.get("title") or ex.get("suggested_title") or ""),
                        target_topic=f"{ex.get('case_real_name_zh') or ''} {ex.get('note') or ''}".strip(),
                        candidate_id=c_id,
                        target_candidate_id=str(ex.get("id") or ""),
                    )[0]
                    for ex in curated_now
                ):
                    continue

                item_copy = dict(cand)
                if callable(apply_seo_keyword_dna_to_title) and seo_dna:
                    full_t, t_target, t_vi = apply_seo_keyword_dna_to_title(c_title, seo_dna)
                    item_copy["title"] = full_t
                    item_copy["title_target"] = t_target
                    if t_vi:
                        item_copy["title_vi"] = t_vi
                item_copy["profile_id"] = pid
                item_copy["already_produced"] = False
                item_copy["research_origin"] = "auto_replenished_dna_pool"
                curated_now.append(item_copy)
                newly_added.append(item_copy)

            profile["curated_today_candidates"] = curated_now
            if isinstance(profile.get("editorial_dna"), dict):
                profile["editorial_dna"]["curated_today_candidates"] = [dict(x) for x in curated_now]

            if not is_pytest_prod_guard:
                try:
                    vdata = load_dna_replenished_vault(vault_path)
                    pledger = dict((vdata.get("profiles") or {}).get(pid) or {})
                    prev_rep = int(pledger.get("replenished_total") or 0)
                    pledger.update({
                        "profile_id": pid,
                        "last_synced_produced_count": len(profile.get("topic_memory") or []),
                        "replenished_total": prev_rep + len(newly_added),
                        "last_newly_replenished_count": len(newly_added),
                        "curated_active_count": len(curated_now),
                        "updated_at": _now(),
                    })
                    vdata.setdefault("profiles", {})[pid] = pledger
                    save_dna_replenished_vault(vdata, vault_path)
                except Exception:
                    pass

            return {
                "enabled": True,
                "profile_id": pid,
                "produced_count": len(profile.get("topic_memory") or []),
                "newly_replenished_count": len(newly_added),
                "curated_active_count": len(curated_now),
                "replenished_candidates": [dict(x) for x in newly_added],
            }
        except Exception:
            return {}

    @classmethod
    def apply_topic_memory_and_replenish(
        cls,
        profiles: list[dict[str, Any]],
        profile_id: str,
        entry_or_job: dict[str, Any],
        *,
        vault_path: Path | None = None,
        pools_path: Path | None = None,
    ) -> dict[str, Any]:
        """
        Core atomic workflow when a final topic is chosen for production:
        1) Harvest rich anti-duplicate identity (`candidate_id`, `case_real_name_zh`, `pipe_case_tag`, `tags`, `anchors`)
           from the entry/job AND pre-prune active `curated_today_candidates` / reserve pools.
        2) Save & deduplicate `topic_memory` on `profile_id` AND all sibling profiles in the same channel family.
        3) Immediately remove the produced topic from `curated_today_candidates`, `editorial_dna.curated_today_candidates`,
           `latest_today.plan_items`, and `data/dna_topic_pools.json`.
        4) Immediately replenish at least `+1` brand-new unproduced DNA-matched topic to restore full list capacity.
        """
        from services.case_similarity import check_case_similarity

        index = next(
            (
                i
                for i, p in enumerate(profiles)
                if str(p.get("id")) == str(profile_id) or str(p.get("channel_profile_id")) == str(profile_id)
            ),
            None,
        )
        if index is None:
            raise KeyError(f"Channel profile {profile_id} not found")

        target_profile = profiles[index]
        canonical_pid = str(target_profile.get("id") or profile_id)
        family_ids = cls._sibling_profile_ids(canonical_pid)

        # Gather pre-prune candidate pools across family + reserve vault + dna_topic_pools.json
        candidate_lookup_pool: list[dict[str, Any]] = []
        for p in profiles:
            if isinstance(p, dict) and str(p.get("id") or "") in family_ids:
                for c in list(p.get("curated_today_candidates") or []):
                    if isinstance(c, dict):
                        candidate_lookup_pool.append(c)
        try:
            from documentary.topic_research import VERIFIED_TWO_STREAM_RESERVE_CASES
            candidate_lookup_pool.extend(VERIFIED_TWO_STREAM_RESERVE_CASES)
        except Exception:
            pass
        repo_root = Path(__file__).resolve().parents[1]
        eff_pools_path = Path(pools_path) if pools_path is not None else (repo_root / "data" / "dna_topic_pools.json")
        if eff_pools_path.exists():
            try:
                raw_pools = json.loads(eff_pools_path.read_text(encoding="utf-8"))
                if isinstance(raw_pools, dict):
                    for fid in family_ids:
                        for c in list(raw_pools.get(fid) or []):
                            if isinstance(c, dict):
                                candidate_lookup_pool.append(c)
            except Exception:
                pass

        rich = cls.extract_rich_topic_memory_payload(entry_or_job, candidate_pools=candidate_lookup_pool)
        title = rich["title"]
        topic = rich["topic"]
        if not title and not topic:
            raise ValueError("Đề tài hoặc tiêu đề không được để trống")

        primary_entry_id = str(rich.get("id") or f"topic-{uuid4().hex[:8]}")
        rich["id"] = primary_entry_id

        def _upsert_into_profile_memory(prof: dict[str, Any], is_primary_target: bool) -> dict[str, Any]:
            mem = list(prof.get("topic_memory") or [])
            entry_copy = dict(rich)
            if not is_primary_target:
                entry_copy["id"] = f"topic-{uuid4().hex[:8]}"
                entry_copy["synced_from_profile_id"] = canonical_pid
            existing_idx = next(
                (
                    i
                    for i, m in enumerate(mem)
                    if (is_primary_target and str(m.get("id")) == primary_entry_id)
                    or (entry_copy.get("job_id") and str(m.get("job_id")) == str(entry_copy.get("job_id")))
                    or str(m.get("title") or "").strip().lower() == title.lower()
                    or check_case_similarity(
                        f"{title} {topic} {entry_copy.get('case_real_name_zh') or ''}".strip(),
                        str(m.get("title") or ""),
                        target_topic=f"{m.get('topic') or m.get('title') or ''} {m.get('case_real_name_zh') or ''}".strip(),
                        target_entities=list(m.get("tags") or []),
                        target_keywords=list(m.get("anchors") or []),
                        candidate_id=str(entry_copy.get("candidate_id") or ""),
                        target_candidate_id=str(m.get("candidate_id") or ""),
                    )[0]
                ),
                None,
            )
            if existing_idx is not None:
                prev_entry = mem[existing_idx]
                entry_copy["id"] = str(prev_entry.get("id") or entry_copy["id"])
                if not entry_copy.get("job_id") and prev_entry.get("job_id"):
                    entry_copy["job_id"] = str(prev_entry["job_id"])
                elif entry_copy.get("job_id") and prev_entry.get("job_id") and str(prev_entry.get("job_id")) != str(entry_copy.get("job_id")):
                    entry_copy["related_job_ids"] = list(
                        dict.fromkeys(list(prev_entry.get("related_job_ids") or []) + [str(prev_entry["job_id"])])
                    )
                if not entry_copy.get("candidate_id") and prev_entry.get("candidate_id"):
                    entry_copy["candidate_id"] = str(prev_entry["candidate_id"])
                if not entry_copy.get("case_real_name_zh") and prev_entry.get("case_real_name_zh"):
                    entry_copy["case_real_name_zh"] = str(prev_entry["case_real_name_zh"])
                if not entry_copy.get("pipe_case_tag") and prev_entry.get("pipe_case_tag"):
                    entry_copy["pipe_case_tag"] = str(prev_entry["pipe_case_tag"])
                entry_copy["tags"] = list(dict.fromkeys(list(prev_entry.get("tags") or []) + list(entry_copy.get("tags") or [])))
                entry_copy["anchors"] = list(dict.fromkeys(list(prev_entry.get("anchors") or []) + list(entry_copy.get("anchors") or [])))
                mem[existing_idx] = entry_copy
            else:
                mem.append(entry_copy)
            mem, _ = cls._deduplicate_topic_memory_list(mem)
            prof["topic_memory"] = mem
            return entry_copy

        # 1) Upsert memory on primary profile + all sibling profiles
        saved_entry = _upsert_into_profile_memory(target_profile, is_primary_target=True)
        for p in profiles:
            if isinstance(p, dict) and str(p.get("id") or "") in family_ids and p is not target_profile:
                _upsert_into_profile_memory(p, is_primary_target=False)
                p["updated_at"] = _now()

        # 2) Prune curated candidates across primary profile + sibling profiles, recording pre-prune count
        pre_counts: dict[str, int] = {}
        removed_counts: dict[str, int] = {}
        for p in profiles:
            spid = str(p.get("id") or "")
            if spid in family_ids:
                before_len = len(list(p.get("curated_today_candidates") or []))
                pre_counts[spid] = before_len
                cls._prune_profile_curated_candidates(p, all_profiles=profiles)
                after_len = len(list(p.get("curated_today_candidates") or []))
                removed_counts[spid] = max(0, before_len - after_len)

        # Also prune matching produced item from data/dna_topic_pools.json (unless running pytest against prod file)
        is_pytest_prod_pools = bool(
            os.environ.get("PYTEST_CURRENT_TEST")
            and eff_pools_path.resolve() == (repo_root / "data" / "dna_topic_pools.json").resolve()
        )
        if eff_pools_path.exists() and not is_pytest_prod_pools:
            try:
                raw_pools = json.loads(eff_pools_path.read_text(encoding="utf-8"))
                if isinstance(raw_pools, dict):
                    pools_mutated = False
                    fam_produced = cls._collect_family_produced_records(target_profile, all_profiles=profiles)
                    for fid in family_ids:
                        if isinstance(raw_pools.get(fid), list) and raw_pools[fid]:
                            kept_pool, _, chg_pool = cls._prune_candidate_list_against_produced(raw_pools[fid], fam_produced)
                            if chg_pool:
                                raw_pools[fid] = kept_pool
                                pools_mutated = True
                    if pools_mutated:
                        eff_pools_path.write_text(json.dumps(raw_pools, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

        # 3) Immediately replenish +1 new topic on primary profile (and any sibling profile whose candidate was pruned)
        primary_min_target = max(pre_counts.get(canonical_pid, 0), len(list(target_profile.get("curated_today_candidates") or [])) + 1 if removed_counts.get(canonical_pid, 0) > 0 else 0)
        vault_stats = cls._auto_replenish_profile_dna_vault(
            target_profile,
            all_profiles=profiles,
            vault_path=vault_path,
            pools_path=eff_pools_path,
            min_target_count=primary_min_target if primary_min_target > 0 else None,
        )
        for p in profiles:
            spid = str(p.get("id") or "")
            if spid in family_ids and p is not target_profile and removed_counts.get(spid, 0) > 0:
                cls._auto_replenish_profile_dna_vault(
                    p,
                    all_profiles=profiles,
                    vault_path=vault_path,
                    pools_path=eff_pools_path,
                    min_target_count=pre_counts.get(spid, 0) or None,
                )

        target_profile["updated_at"] = _now()
        profiles[index] = target_profile

        if vault_stats:
            saved_entry["dna_vault_status"] = {
                k: v for k, v in vault_stats.items() if k != "replenished_candidates"
            }
            saved_entry["removed_from_curated_count"] = removed_counts.get(canonical_pid, 0)
            rep_cands = list(vault_stats.get("replenished_candidates") or [])
            saved_entry["replenished_count"] = len(rep_cands)
            saved_entry["replenished_candidates"] = [
                {
                    "id": str(c.get("id") or ""),
                    "title": str(c.get("title") or ""),
                    "topic_stream": str(c.get("topic_stream") or ""),
                    "case_real_name_zh": str(c.get("case_real_name_zh") or ""),
                }
                for c in rep_cands
            ]
        return saved_entry

    def get_topic_memory(self, profile_id: str) -> list[dict[str, Any]]:
        profile = self.get_profile(profile_id)
        return list(profile.get("topic_memory") or [])

    def add_topic_memory(self, profile_id: str, entry: dict[str, Any] | TopicMemoryEntryModel) -> dict[str, Any]:
        if isinstance(entry, BaseModel):
            data = entry.model_dump(exclude_unset=True)
        else:
            data = dict(entry)

        title = str(data.get("title") or "").strip()
        topic = str(data.get("topic") or title).strip()
        if not title and not topic:
            raise ValueError("Đề tài hoặc tiêu đề không được để trống")

        with self._lock:
            # Avoid polluting production channel_profiles.json with dummy test titles during pytest runs
            if (
                os.environ.get("PYTEST_CURRENT_TEST")
                and self.storage_path.resolve() == DEFAULT_STORAGE_FILE.resolve()
                and self._is_synthetic_test_topic(title, topic, str(data.get("job_id") or ""))
            ):
                return self.extract_rich_topic_memory_payload(data)

            profiles = self._read_profiles_raw()
            saved_entry = self.apply_topic_memory_and_replenish(profiles, profile_id, data)
            self._write_profiles_raw(profiles)
            return saved_entry

    def delete_topic_memory(self, profile_id: str, entry_id: str) -> dict[str, Any]:
        with self._lock:
            profiles = self._read_profiles_raw()
            index = next(
                (i for i, p in enumerate(profiles) if str(p.get("id")) == str(profile_id) or str(p.get("channel_profile_id")) == str(profile_id)),
                None
            )
            if index is None:
                raise KeyError(f"Channel profile {profile_id} not found")

            profile = profiles[index]
            mem = list(profile.get("topic_memory") or [])
            init_len = len(mem)
            mem = [m for m in mem if str(m.get("id")) != str(entry_id)]
            if len(mem) == init_len:
                raise KeyError(f"Topic memory entry {entry_id} not found in profile {profile_id}")

            profile["topic_memory"] = mem
            profile["updated_at"] = _now()
            profiles[index] = profile
            self._write_profiles_raw(profiles)

        return {"status": "ok", "deleted_entry_id": entry_id}

    def backfill_topic_memory(self) -> int:
        from services.case_similarity import check_case_similarity, extract_case_anchors_and_entities, is_duplicate_case

        with self._lock:
            profiles = self._read_profiles_raw()
            if not profiles:
                return 0

            added_count = 0
            mutated = False
            profiles_by_id = {str(p.get("id")): p for p in profiles}

            # Clean synthetic test pollution from production storage file
            if self.storage_path.resolve() == DEFAULT_STORAGE_FILE.resolve():
                for p in profiles:
                    orig_mem = list(p.get("topic_memory") or [])
                    cleaned_mem = [
                        m for m in orig_mem
                        if isinstance(m, dict)
                        and not self._is_synthetic_test_topic(
                            str(m.get("title") or ""),
                            str(m.get("topic") or ""),
                            str(m.get("job_id") or ""),
                        )
                    ]
                    if len(cleaned_mem) != len(orig_mem):
                        p["topic_memory"] = cleaned_mem
                        mutated = True

            historical_anchors = [
                {
                    "profile_id": "channel-e544a64b7c",
                    "job_id": "20261017-164519-fd65f7e1",
                    "title": "20년간 신분을 세탁한 '미소의 악마' — 라오룽즈 사건",
                    "topic": "라오룽즈(劳荣枝) & 파즈잉(法子英) 20년 신분 세탁 도피 및 97.33% AI 안면인식 검거 실화 (Lao Vinh Chi)",
                    "source": "backfill",
                },
                {
                    "profile_id": "channel-e544a64b7c",
                    "job_id": "20261019-185102-31983814",
                    "title": "중국에서 붉은 옷 입은 여성 11명을 노린 악마 | 28년간 고등학교 매점에 숨어 웃고 있었다",
                    "topic": "바이인시(白银市) 고승용(高承勇) 28년 학교 매점 은신 및 Y-STR 유전자 족보 검거 실화 (Cao Thừa Dũng)",
                    "source": "backfill",
                },
                {
                    "profile_id": "channel-e544a64b7c",
                    "job_id": "20261020-121755-bab8347e",
                    "title": "[중국 실화 사건] 13년 잠적한 1급 수배범이 인기 드라마 배우였다니 | 길광 도주 사건",
                    "topic": "길광(吉思光 / Cát Quang) 13년 신분 세탁 도피 및 30여 편 인기 드라마 배우 활동 검거 실화",
                    "source": "backfill",
                },
                {
                    "profile_id": "channel-e544a64b7c",
                    "job_id": "20261021-000107-bd5f8a44",
                    "title": "[중국 실화 사건] 22년 전 미제사건 범인이 베스트셀러 작가가 된 사연 | 호주 여관 사건",
                    "topic": "호주 여관 미제 사건 진범 유영표(刘永彪 / Lưu Vĩnh Bưu) 22년 은신 및 유명 작가 변신 검거 실화",
                    "source": "backfill",
                },
                {
                    "profile_id": "channel-e544a64b7c",
                    "job_id": "20261022-051728-e577844b",
                    "title": "[중국 실화 사건] 17년간 벙어리 거지로 위장해 살아온 수배범이 말을 잃어버린 이유 | 소기강 신분세탁 사건",
                    "topic": "소기강(萧奇强 / Tiêu Kỳ Cường) 17년 벙어리 거지 위장 신분세탁 도피 및 성대 퇴화 실화",
                    "source": "backfill",
                },
                {
                    "profile_id": "channel-e544a64b7c",
                    "job_id": "20261023-052625-743151f0",
                    "title": "[중국 실화 사건] 12년 동안 수백만 위안 자산가로 변신한 수배범의 치밀한 연극 | 행남방 도주 사건",
                    "topic": "행남방(向南方 / Hướng Nam Phương) 12년 유령 호적 세탁 백만장자 왕 빈 변신 및 72시간 심문실 심리전 실화",
                    "source": "job",
                },
                {
                    "profile_id": "channel-1e24de3ab5",
                    "job_id": "20261018-223750-3aecfbcd",
                    "title": "남수북조 공정 1,432km & 팽창토 지반 침하의 미스터리",
                    "topic": "단장커우 댐에서 베이징까지 1,432km 수로와 팽창토 지반 침하 및 청수세굴 위기",
                    "source": "backfill",
                },
            ]

            for item in historical_anchors:
                pid = item["profile_id"]
                if pid in profiles_by_id:
                    target_profile = profiles_by_id[pid]
                    mem_list = target_profile.setdefault("topic_memory", [])
                    has_job = any(str(m.get("job_id")) == item["job_id"] for m in mem_list)
                    has_anchor = any(
                        is_duplicate_case(str(m.get("title", "")), item["title"])
                        for m in mem_list
                    )
                    if not has_job and not has_anchor:
                        entities, keywords = extract_case_anchors_and_entities(item["title"], item["topic"])
                        entry = {
                            "id": f"topic-{uuid4().hex[:8]}",
                            "job_id": item["job_id"],
                            "title": item["title"],
                            "topic": item["topic"],
                            "tags": entities,
                            "anchors": entities + keywords,
                            "created_at": _now(),
                            "source": item["source"],
                        }
                        mem_list.append(entry)
                        added_count += 1
                        mutated = True

            # Sync own_channel.dna.winner_titles into topic_memory if missing
            for p in profiles:
                mem_list = p.setdefault("topic_memory", [])
                own_dna = (p.get("own_channel") or {}).get("dna") or {}
                for wt in (own_dna.get("winner_titles") or []):
                    wt_str = str(wt.get("title") if isinstance(wt, dict) else wt or "").strip()
                    if not wt_str or self._is_synthetic_test_topic(wt_str):
                        continue
                    if not any(is_duplicate_case(str(m.get("title", "")), wt_str) for m in mem_list):
                        entities, keywords = extract_case_anchors_and_entities(wt_str, wt_str)
                        mem_list.append({
                            "id": f"topic-{uuid4().hex[:8]}",
                            "job_id": "",
                            "title": wt_str,
                            "topic": wt_str,
                            "tags": entities,
                            "anchors": entities + keywords,
                            "created_at": _now(),
                            "source": "own_channel_youtube",
                        })
                        added_count += 1
                        mutated = True

            known_job_ids = {
                str(m.get("job_id"))
                for p in profiles
                for m in (p.get("topic_memory") or [])
                if isinstance(m, dict) and m.get("job_id")
            }

            for job_root in (ROOT / "data" / "jobs", ROOT / "workspaces"):
                if not job_root.is_dir():
                    continue
                for jdir in job_root.iterdir():
                    if not jdir.is_dir():
                        continue
                    if jdir.name in known_job_ids or self._is_synthetic_test_topic("", "", jdir.name):
                        continue
                    jfile = jdir / "job.json"
                    if not jfile.is_file():
                        continue
                    try:
                        jdata = json.loads(jfile.read_text(encoding="utf-8"))
                        pid = str(jdata.get("channel_profile_id") or jdata.get("channel_profile_snapshot", {}).get("id") or "")
                        if pid and pid in profiles_by_id:
                            target_profile = profiles_by_id[pid]
                            mem_list = target_profile.setdefault("topic_memory", [])
                            jid = str(jdata.get("id") or jdir.name)
                            jtitle = str(jdata.get("title") or "")
                            jtopic = str(jdata.get("topic") or jtitle)
                            if not jtitle and not jtopic:
                                continue
                            if self._is_synthetic_test_topic(jtitle, jtopic, jid):
                                continue
                            has_job = any(str(m.get("job_id")) == jid for m in mem_list)
                            has_anchor = any(
                                check_case_similarity(
                                    f"{jtitle} {jtopic}",
                                    str(m.get("title", "")),
                                    target_topic=str(m.get("topic", "")),
                                    target_entities=list(m.get("tags") or []),
                                    target_keywords=list(m.get("anchors") or []),
                                )[0]
                                for m in mem_list
                            )
                            if not has_job and not has_anchor:
                                entities, keywords = extract_case_anchors_and_entities(jtitle, jtopic)
                                entry = {
                                    "id": f"topic-{uuid4().hex[:8]}",
                                    "job_id": jid,
                                    "title": jtitle,
                                    "topic": jtopic,
                                    "tags": entities,
                                    "anchors": entities + keywords,
                                    "created_at": str(jdata.get("created_at") or _now()),
                                    "source": "job",
                                }
                                mem_list.append(entry)
                                added_count += 1
                                mutated = True
                    except Exception:
                        continue

            # Sync produced topic_memory across sibling profiles of the same channel family
            for p in profiles:
                pid = str(p.get("id") or "")
                sib_ids = self._sibling_profile_ids(pid) - {pid}
                if not sib_ids:
                    continue
                mem_list = p.setdefault("topic_memory", [])
                for sid in sib_ids:
                    sib_p = profiles_by_id.get(sid)
                    if not sib_p:
                        continue
                    for sm in list(sib_p.get("topic_memory") or []):
                        if not isinstance(sm, dict):
                            continue
                        sm_title = str(sm.get("title") or "").strip()
                        sm_topic = str(sm.get("topic") or sm_title).strip()
                        if not sm_title or self._is_synthetic_test_topic(sm_title, sm_topic, str(sm.get("job_id") or "")):
                            continue
                        if not any(
                            check_case_similarity(
                                f"{sm_title} {sm_topic}",
                                str(m.get("title", "")),
                                target_topic=str(m.get("topic", "")),
                                target_entities=list(m.get("tags") or []),
                                target_keywords=list(m.get("anchors") or []),
                            )[0]
                            for m in mem_list
                        ):
                            mem_list.append(dict(sm, id=f"topic-{uuid4().hex[:8]}"))
                            added_count += 1
                            mutated = True

            for p in profiles:
                deduped_mem, mem_changed = self._deduplicate_topic_memory_list(list(p.get("topic_memory") or []))
                if mem_changed:
                    p["topic_memory"] = deduped_mem
                    mutated = True
                before_cur = len(list(p.get("curated_today_candidates") or []))
                if self._prune_profile_curated_candidates(p, all_profiles=profiles):
                    mutated = True
                    self._auto_replenish_profile_dna_vault(
                        p,
                        all_profiles=profiles,
                        min_target_count=before_cur or None,
                    )

            if mutated or added_count > 0:
                self._write_profiles_raw(profiles)

            return added_count

    def sync_job_to_topic_memory(self, job: dict[str, Any]) -> dict[str, Any] | None:
        profile_id = str(job.get("channel_profile_id") or (job.get("channel_profile_snapshot") or {}).get("id") or "").strip()
        if not profile_id:
            return None

        title = str(job.get("title") or "").strip()
        topic = str(job.get("topic") or title).strip()
        if not title and not topic:
            return None

        sel = ((job.get("topic_discovery") or {}).get("selected_candidate") or {}) if isinstance(job.get("topic_discovery"), dict) else {}
        entry = {
            "job_id": str(job.get("id") or ""),
            "candidate_id": str(job.get("candidate_id") or sel.get("id") or ""),
            "case_real_name_zh": str(job.get("case_real_name_zh") or sel.get("case_real_name_zh") or ""),
            "topic_stream": str(job.get("topic_stream") or sel.get("topic_stream") or ""),
            "title": title,
            "topic": topic,
            "notes": str(job.get("notes") or sel.get("note") or ""),
            "topic_discovery": job.get("topic_discovery") if isinstance(job.get("topic_discovery"), dict) else {},
            "creative_brief": job.get("creative_brief") if isinstance(job.get("creative_brief"), dict) else {},
            "source": "job",
        }
        try:
            return self.add_topic_memory(profile_id, entry)
        except Exception:
            return None
