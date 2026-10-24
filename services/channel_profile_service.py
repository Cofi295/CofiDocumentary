"""
Channel Profile Service for CofiDocumentary (Milestone 1).
Provides complete CRUD, cloning, schema validation, and persistence for Channel Profiles.
"""

from __future__ import annotations

import copy
import json
import os
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


class TopicMemoryEntryModel(BaseModel):
    id: str | None = None
    job_id: str = ""
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
    default_creative_brief: dict[str, Any] | None = None
    editing_dna: dict[str, Any] | None = None
    self_learning_memory: dict[str, Any] | None = None
    editorial_dna: dict[str, Any] | None = None
    topic_memory: list[dict[str, Any]] | None = None
    seo_keyword_dna: dict[str, Any] | None = None
    thumbnail_dna: dict[str, Any] | None = None
    thumbnail_dna_history: list[dict[str, Any]] | None = None


class ChannelProfileUpdateModel(BaseModel):
    label: str | None = None
    market: str | None = None
    default_language: str | None = None
    language: str | None = None
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
    default_creative_brief: dict[str, Any] | None = None
    editing_dna: dict[str, Any] | None = None
    self_learning_memory: dict[str, Any] | None = None
    editorial_dna: dict[str, Any] | None = None
    topic_memory: list[dict[str, Any]] | None = None
    seo_keyword_dna: dict[str, Any] | None = None
    thumbnail_dna: dict[str, Any] | None = None
    thumbnail_dna_history: list[dict[str, Any]] | None = None


class ChannelProfileCloneModel(BaseModel):
    label: str | None = None


# ==============================================================================
# SERVICE CLASS
# ==============================================================================

class ChannelProfileService:
    def __init__(self, storage_path: Path | str | None = None, documentary_service: Any = None):
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_STORAGE_FILE
        self.documentary_service = documentary_service
        self._lock = threading.RLock()
        try:
            self.backfill_topic_memory()
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
            "custom_rules": str(brief_data.get("custom_rules") or raw_data.get("custom_rules") or "Standard DNA compliance")
        }

        # Initialize Editing DNA
        dna_data = dict(raw_data.get("editing_dna") or {})
        editing_dna = {
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
            "color_grade": str(dna_data.get("color_grade") or "technical_cool_cyan"),
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
            "created_at": stamp,
            "updated_at": stamp,
        }

        with self._lock:
            profiles = self._read_profiles_raw()
            profiles.append(profile)
            self._write_profiles_raw(profiles)

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
                if key in {"default_creative_brief", "editing_dna", "self_learning_memory", "seo_keyword_dna"}:
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

            updated["updated_at"] = _now()
            profiles[index] = updated
            self._write_profiles_raw(profiles)

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
    def _prune_profile_curated_candidates(profile: dict[str, Any]) -> bool:
        from services.case_similarity import check_case_similarity

        curated = profile.get("curated_today_candidates")
        if not isinstance(curated, list) or not curated:
            return False

        produced_records: list[dict[str, Any]] = []
        for m in (profile.get("topic_memory") or []):
            if isinstance(m, dict) and (m.get("title") or m.get("topic")):
                produced_records.append({
                    "title": str(m.get("title") or ""),
                    "topic": str(m.get("topic") or m.get("title") or ""),
                    "tags": list(m.get("tags") or []),
                    "anchors": list(m.get("anchors") or []),
                })

        own_ch = profile.get("own_channel") or {}
        for wt in ((own_ch.get("dna") or {}).get("winner_titles") or []):
            wt_str = str(wt.get("title") if isinstance(wt, dict) else wt or "").strip()
            if wt_str:
                produced_records.append({
                    "title": wt_str,
                    "topic": wt_str,
                    "tags": [],
                    "anchors": [],
                })
        for v in (own_ch.get("videos") or []):
            if isinstance(v, dict) and v.get("title"):
                vt_str = str(v["title"]).strip()
                produced_records.append({
                    "title": vt_str,
                    "topic": vt_str,
                    "tags": [],
                    "anchors": [],
                })

        kept: list[dict[str, Any]] = []
        changed = False
        for cand in curated:
            if not isinstance(cand, dict):
                changed = True
                continue
            if cand.get("already_produced") is True:
                changed = True
                continue
            c_title = str(cand.get("suggested_title") or cand.get("title") or "").strip()
            c_vi = str(cand.get("title_vi") or "").strip()
            c_sum = str(cand.get("topic_summary") or cand.get("summary_vi") or cand.get("why_now") or "").strip()
            c_cluster = str(cand.get("cluster_label") or "").strip()
            combined_cand = f"{c_title} {c_vi} {c_sum} {c_cluster}".strip()
            if not c_title:
                changed = True
                continue

            dup_found = False
            for rec in produced_records:
                is_dup, _, _ = check_case_similarity(
                    combined_cand,
                    rec["title"],
                    target_topic=rec["topic"],
                    target_entities=rec["tags"],
                    target_keywords=rec["anchors"],
                )
                if is_dup:
                    dup_found = True
                    break
            if dup_found:
                changed = True
                continue

            # Also deduplicate against already-kept candidates in the same list
            for prev in kept:
                p_title = str(prev.get("suggested_title") or prev.get("title") or "").strip()
                p_sum = f"{prev.get('title_vi') or ''} {prev.get('topic_summary') or ''}".strip()
                is_dup_internal, _, _ = check_case_similarity(
                    combined_cand,
                    p_title,
                    target_topic=p_sum,
                )
                if is_dup_internal:
                    dup_found = True
                    break
            if dup_found:
                changed = True
                continue

            kept.append(cand)

        if changed or len(kept) != len(curated):
            profile["curated_today_candidates"] = kept
            return True
        return False

    def get_topic_memory(self, profile_id: str) -> list[dict[str, Any]]:
        profile = self.get_profile(profile_id)
        return list(profile.get("topic_memory") or [])

    def add_topic_memory(self, profile_id: str, entry: dict[str, Any] | TopicMemoryEntryModel) -> dict[str, Any]:
        from services.case_similarity import check_case_similarity, extract_case_anchors_and_entities

        if isinstance(entry, BaseModel):
            data = entry.model_dump(exclude_unset=True)
        else:
            data = dict(entry)

        title = str(data.get("title") or "").strip()
        topic = str(data.get("topic") or title).strip()
        if not title and not topic:
            raise ValueError("Đề tài hoặc tiêu đề không được để trống")

        entry_id = str(data.get("id") or f"topic-{uuid4().hex[:8]}")
        entities, keywords = extract_case_anchors_and_entities(title, topic)
        anchors = list(dict.fromkeys(list(data.get("anchors") or []) + entities + keywords))
        tags = list(dict.fromkeys(list(data.get("tags") or []) + entities))

        new_entry = {
            "id": entry_id,
            "job_id": str(data.get("job_id") or ""),
            "title": title,
            "topic": topic,
            "tags": tags,
            "anchors": anchors,
            "created_at": str(data.get("created_at") or _now()),
            "source": str(data.get("source") or "manual"),
        }

        with self._lock:
            # Avoid polluting production channel_profiles.json with dummy test titles during pytest runs
            if (
                os.environ.get("PYTEST_CURRENT_TEST")
                and self.storage_path.resolve() == DEFAULT_STORAGE_FILE.resolve()
                and self._is_synthetic_test_topic(title, topic, str(data.get("job_id") or ""))
            ):
                return new_entry

            profiles = self._read_profiles_raw()
            index = next(
                (i for i, p in enumerate(profiles) if str(p.get("id")) == str(profile_id) or str(p.get("channel_profile_id")) == str(profile_id)),
                None
            )
            if index is None:
                raise KeyError(f"Channel profile {profile_id} not found")

            profile = profiles[index]
            mem = list(profile.get("topic_memory") or [])
            existing_idx = next(
                (
                    i
                    for i, m in enumerate(mem)
                    if str(m.get("id")) == entry_id
                    or (data.get("job_id") and str(m.get("job_id")) == str(data.get("job_id")))
                    or str(m.get("title") or "").strip().lower() == title.lower()
                ),
                None,
            )
            if existing_idx is not None:
                prev_entry = mem[existing_idx]
                new_entry["id"] = str(prev_entry.get("id") or entry_id)
                if not new_entry["job_id"] and prev_entry.get("job_id"):
                    new_entry["job_id"] = str(prev_entry["job_id"])
                new_entry["tags"] = list(dict.fromkeys(list(prev_entry.get("tags") or []) + tags))
                new_entry["anchors"] = list(dict.fromkeys(list(prev_entry.get("anchors") or []) + anchors))
                mem[existing_idx] = new_entry
            else:
                mem.append(new_entry)

            profile["topic_memory"] = mem
            self._prune_profile_curated_candidates(profile)
            profile["updated_at"] = _now()
            profiles[index] = profile
            self._write_profiles_raw(profiles)

        return new_entry

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
        from services.case_similarity import extract_case_anchors_and_entities, is_duplicate_case

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

            jobs_dir = ROOT / "data" / "jobs"
            if jobs_dir.is_dir():
                for jdir in jobs_dir.iterdir():
                    if not jdir.is_dir():
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
                                is_duplicate_case(str(m.get("title", "")), jtitle)
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

            for p in profiles:
                if self._prune_profile_curated_candidates(p):
                    mutated = True

            if mutated or added_count > 0:
                self._write_profiles_raw(profiles)

            return added_count

    def sync_job_to_topic_memory(self, job: dict[str, Any]) -> dict[str, Any] | None:
        profile_id = str(job.get("channel_profile_id") or job.get("channel_profile_snapshot", {}).get("id") or "").strip()
        if not profile_id:
            return None

        title = str(job.get("title") or "").strip()
        topic = str(job.get("topic") or title).strip()
        if not title and not topic:
            return None

        job_id = str(job.get("id") or "")
        entry = {
            "job_id": job_id,
            "title": title,
            "topic": topic,
            "source": "job",
        }
        try:
            return self.add_topic_memory(profile_id, entry)
        except Exception:
            return None
