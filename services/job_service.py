"""
Job Service for CofiDocumentary (Milestone 1).
Provides Job lifecycle operations and enforces strict mutation isolation.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
from typing import Any
from uuid import uuid4

from documentary.quality import normalize_production_recipe
from documentary.store import JobStore
from services.channel_profile_service import ChannelProfileService

ROOT = Path(__file__).resolve().parents[1]


def _sync_creative_brief_duration(brief: dict[str, Any] | None, target_minutes: Any) -> dict[str, Any]:
    if not isinstance(brief, dict):
        return {}
    out = copy.deepcopy(brief)
    try:
        mins = float(target_minutes)
    except (TypeError, ValueError):
        return out
    if mins <= 0:
        return out
    mins_val: int | float = int(mins) if mins.is_integer() else round(mins, 1)
    out["target_duration_minutes"] = mins_val
    for field in ("writing_style", "custom_rules", "notes"):
        val = out.get(field)
        if isinstance(val, str) and val.strip():
            val = re.sub(r"\b(?:20|25|30)\s*Phút\b", f"{mins_val} Phút", val)
            val = re.sub(r"\b(?:20|25|30)\s*phút\b", f"{mins_val} phút", val)
            val = re.sub(r"\b(?:20|25|30)\s*PHÚT\b", f"{mins_val} PHÚT", val)
            out[field] = val
    return out


class JobService:
    def __init__(self, store: JobStore | None = None, profile_service: ChannelProfileService | None = None):
        self.store = store or JobStore(ROOT / "data" / "jobs")
        self.profile_service = profile_service or ChannelProfileService()

    def list_jobs(self) -> list[dict[str, Any]]:
        return self.store.list()

    def get_job(self, job_id: str) -> dict[str, Any]:
        job = self.store.get(job_id)
        if job is None:
            raise KeyError(f"Job {job_id} not found")
        return job

    def update_job(self, job_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        """
        Strictly mutate only the designated {job_id}.
        Rejects cross-job mutation attempts and draft side-effects.
        """
        # Verify job existence
        existing = self.store.get(job_id)
        if existing is None:
            raise KeyError(f"Job {job_id} not found")

        sanitized_patch = dict(patch)

        # Reject any cross-job mutation attempt
        target_id_in_patch = sanitized_patch.get("job_id") or sanitized_patch.get("id") or sanitized_patch.get("selectedId")
        if target_id_in_patch is not None and str(target_id_in_patch).strip() != str(job_id).strip():
            raise ValueError(
                f"Cross-job mutation rejected: target job '{job_id}' does not match payload ID '{target_id_in_patch}'"
            )

        # Strip identity alteration fields
        sanitized_patch.pop("id", None)
        sanitized_patch.pop("job_id", None)
        sanitized_patch.pop("selectedId", None)

        # Reject draft mutation side-effects
        if sanitized_patch.get("is_draft") or sanitized_patch.get("draft_mutation"):
            raise ValueError("Draft mutation side-effects rejected: draft settings must not mutate active project")

        # Validate phases dictionary if provided
        if "phases" in sanitized_patch and not isinstance(sanitized_patch["phases"], dict):
            raise ValueError("phases must be a dictionary")

        # Re-normalize production_recipe & creative_brief whenever target_duration_minutes or visual_strategy changes
        effective_duration = sanitized_patch.get("target_duration_minutes", existing.get("target_duration_minutes"))
        effective_strategy = sanitized_patch.get("visual_strategy", existing.get("visual_strategy"))
        effective_editing_dna = sanitized_patch.get("editing_dna") or existing.get("editing_dna")
        if (
            "target_duration_minutes" in sanitized_patch
            or "visual_strategy" in sanitized_patch
            or "editing_dna" in sanitized_patch
            or (effective_duration not in (None, "") and not (existing.get("production_recipe") or {}).get("quality_contract"))
        ):
            if effective_duration not in (None, ""):
                sanitized_patch["production_recipe"] = normalize_production_recipe(
                    sanitized_patch.get("production_recipe") or existing.get("production_recipe"),
                    target_duration_minutes=effective_duration,
                    visual_strategy=effective_strategy,
                    editing_dna=effective_editing_dna if isinstance(effective_editing_dna, dict) else None,
                )
                brief_to_sync = sanitized_patch.get("creative_brief") or existing.get("creative_brief")
                if isinstance(brief_to_sync, dict):
                    sanitized_patch["creative_brief"] = _sync_creative_brief_duration(brief_to_sync, effective_duration)
        if "visual_strategy" in sanitized_patch:
            vs_norm = str(effective_strategy or "").strip().lower()
            merged_ai_vis = copy.deepcopy(sanitized_patch.get("ai_visual") or existing.get("ai_visual") or {})
            if isinstance(merged_ai_vis, dict):
                merged_ai_vis["coverage_mode"] = (
                    "full_ai"
                    if vs_norm == "full_ai"
                    else ("selective_ai" if vs_norm == "edit_direct_footage" else "fallback_only")
                )
                sanitized_patch["ai_visual"] = merged_ai_vis
            snap = copy.deepcopy(sanitized_patch.get("channel_profile_snapshot") or existing.get("channel_profile_snapshot") or {})
            if isinstance(snap, dict) and snap:
                snap["visual_strategy"] = effective_strategy
                sanitized_patch["channel_profile_snapshot"] = snap

        # Perform atomic update on designated job only
        updated = self.store.update(job_id, sanitized_patch)
        try:
            ws_str = str(updated.get("workspace") or "").strip()
            if ws_str:
                ws_dir = Path(ws_str)
                if ws_dir.is_dir():
                    (ws_dir / "input.json").write_text(
                        json.dumps({k: v for k, v in updated.items() if k != "phases"}, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    if isinstance(updated.get("ai_visual"), dict):
                        (ws_dir / "ai_visual_settings.json").write_text(
                            json.dumps(updated["ai_visual"], ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
        except Exception:
            pass
        if updated.get("channel_profile_id") and ("title" in sanitized_patch or "topic" in sanitized_patch):
            try:
                self.profile_service.sync_job_to_topic_memory(updated)
            except Exception:
                pass
        return updated

    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        job_data = dict(payload)
        profile_id = job_data.get("channel_profile_id")

        if profile_id:
            try:
                profile = self.profile_service.get_profile(str(profile_id))
            except KeyError as exc:
                raise ValueError(f"Channel profile '{profile_id}' not found") from exc

            # Lock channel profile configuration into job if not explicitly specified (or if profile enforces edit_direct_footage)
            prof_vs = str(
                profile.get("visual_strategy")
                or profile.get("default_visual_strategy")
                or (profile.get("editorial_dna") or {}).get("visual_strategy")
                or ""
            ).strip().lower()
            if prof_vs in {"semi_content", "ban_content", "edit_footage"}:
                prof_vs = "edit_direct_footage"
            prof_preset = str(
                ((profile.get("editing_dna") or {}).get("preset_id") if isinstance(profile.get("editing_dna"), dict) else "")
                or ""
            ).strip()
            if not job_data.get("visual_strategy") or (
                prof_vs == "edit_direct_footage" and prof_preset in {"forensic_noir_director_v2", "vox_china_crime_newsroom_v10"}
            ):
                job_data["visual_strategy"] = prof_vs or "hybrid"
            if job_data.get("target_duration_minutes") in (None, "") and profile.get("default_duration_minutes") not in (None, ""):
                job_data["target_duration_minutes"] = profile.get("default_duration_minutes")

            if not job_data.get("default_creative_brief") and profile.get("default_creative_brief"):
                job_data["default_creative_brief"] = copy.deepcopy(profile["default_creative_brief"])
            if not job_data.get("creative_brief") and job_data.get("default_creative_brief"):
                job_data["creative_brief"] = copy.deepcopy(job_data["default_creative_brief"])

            if not job_data.get("editing_dna") and profile.get("editing_dna"):
                job_data["editing_dna"] = copy.deepcopy(profile["editing_dna"])

            if not job_data.get("seo_keyword_dna") and profile.get("seo_keyword_dna"):
                job_data["seo_keyword_dna"] = copy.deepcopy(profile["seo_keyword_dna"])

            if not job_data.get("thumbnail_dna") and profile.get("thumbnail_dna"):
                job_data["thumbnail_dna"] = copy.deepcopy(profile["thumbnail_dna"])

            prof_rhythm_dna = copy.deepcopy(profile.get("rhythm_dna") or {})
            if not prof_rhythm_dna:
                try:
                    from services.voice_rhythm_specialist import VoiceRhythmSpecialistService

                    prof_rhythm_dna = VoiceRhythmSpecialistService().analyze_profile_rhythm_dna(profile)
                except Exception:
                    prof_rhythm_dna = {}
            if not job_data.get("rhythm_dna") and prof_rhythm_dna:
                job_data["rhythm_dna"] = copy.deepcopy(prof_rhythm_dna)
            if not job_data.get("voice_signature") and profile.get("voice_signature"):
                job_data["voice_signature"] = copy.deepcopy(profile["voice_signature"])

            if not job_data.get("ai_media_mode") and profile.get("default_ai_media_mode"):
                job_data["ai_media_mode"] = str(profile["default_ai_media_mode"])

            ai_vis = dict(job_data.get("ai_visual") or {})
            if not ai_vis.get("style_mode") and profile.get("default_ai_style_mode"):
                ai_vis["style_mode"] = str(profile["default_ai_style_mode"])
            if not ai_vis.get("style_preset") and profile.get("default_ai_style_preset"):
                ai_vis["style_preset"] = str(profile["default_ai_style_preset"])
            if not ai_vis.get("custom_style") and profile.get("default_ai_custom_style"):
                ai_vis["custom_style"] = str(profile["default_ai_custom_style"])
            if not ai_vis.get("ai_media_mode") and job_data.get("ai_media_mode"):
                ai_vis["ai_media_mode"] = str(job_data["ai_media_mode"])
            if not ai_vis.get("coverage_mode"):
                vs_val = str(job_data.get("visual_strategy") or "").strip().lower()
                ai_vis["coverage_mode"] = (
                    "full_ai" if vs_val == "full_ai"
                    else ("selective_ai" if vs_val == "edit_direct_footage" else "fallback_only")
                )
            if ai_vis.get("style_mode") == "preset" and ai_vis.get("style_preset") and not ai_vis.get("style_prompt"):
                try:
                    presets_dir = ROOT / "presets" / "ai_visual_styles"
                    for pfile in sorted(presets_dir.glob("*.json")):
                        pdata = json.loads(pfile.read_text(encoding="utf-8"))
                        if str(pdata.get("name") or "").strip() == str(ai_vis["style_preset"]).strip():
                            ai_vis["style_prompt"] = str(pdata.get("prompt") or "").strip()
                            break
                except Exception:
                    pass
            resolved_style_prompt_lower = str(ai_vis.get("style_prompt") or "").lower()
            forbids_cartoon_ref = any(
                tok in resolved_style_prompt_lower
                for tok in ("0% cartoon", "0% stickman", "realistic human anatomy")
            )
            if (
                not job_data.get("style_reference_image")
                and profile.get("default_style_reference_image")
                and not forbids_cartoon_ref
            ):
                job_data["style_reference_image"] = str(profile["default_style_reference_image"])
            if ai_vis:
                job_data["ai_visual"] = ai_vis

            voice_cfg = dict(job_data.get("voice") or {}) if isinstance(job_data.get("voice"), dict) else {}
            prof_voice_id = str(profile.get("voice_id") or profile.get("default_voice_id") or "").strip()
            if prof_voice_id and not voice_cfg.get("voice_id"):
                voice_cfg["voice_id"] = prof_voice_id
            if profile.get("secondary_voice_id") and "secondary_voice_id" not in voice_cfg:
                voice_cfg["secondary_voice_id"] = str(profile["secondary_voice_id"]).strip()
            if profile.get("voice_speed") not in (None, "") and not voice_cfg.get("speed"):
                voice_cfg["speed"] = float(profile["voice_speed"])
            if voice_cfg:
                job_data["voice"] = voice_cfg

            # Snapshot
            job_data["channel_profile_snapshot"] = {
                "id": profile.get("id") or profile_id,
                "channel_profile_id": profile.get("id") or profile_id,
                "label": profile.get("label"),
                "market": profile.get("market"),
                "language": profile.get("default_language") or profile.get("language"),
                "visual_strategy": job_data["visual_strategy"],
                "voice_id": prof_voice_id or None,
                "default_voice_id": prof_voice_id or None,
                "secondary_voice_id": profile.get("secondary_voice_id"),
                "voice_speed": profile.get("voice_speed"),
                "default_style_reference_image": profile.get("default_style_reference_image"),
                "default_creative_brief": copy.deepcopy(profile.get("default_creative_brief") or {}),
                "editorial_dna": copy.deepcopy(profile.get("editorial_dna") or {}),
                "editing_dna": copy.deepcopy(profile.get("editing_dna") or {}),
                "seo_keyword_dna": copy.deepcopy(profile.get("seo_keyword_dna") or {}),
                "thumbnail_dna": copy.deepcopy(profile.get("thumbnail_dna") or {}),
                "rhythm_dna": copy.deepcopy(prof_rhythm_dna),
                "voice_signature": copy.deepcopy(profile.get("voice_signature") or {}),
            }

        # Generate unique Job ID and initialize workspaces/{job_id}
        job_id = str(job_data.get("id") or f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}")
        job_data["id"] = job_id

        workspace_root = ROOT / "workspaces"
        workspace_dir = workspace_root / job_id
        workspace_dir.mkdir(parents=True, exist_ok=True)
        ref_dir = workspace_dir / "media" / "style_reference"
        ref_dir.mkdir(parents=True, exist_ok=True)

        job_data["workspace"] = str(workspace_dir)
        job_data["workspace_root"] = str(workspace_root)

        # Handle reference image if provided as file path or data url
        ref_img = job_data.get("style_reference_image") or (job_data.get("ai_visual") or {}).get("style_reference_image")
        if ref_img:
            src_path = Path(str(ref_img))
            if src_path.is_file():
                dst_path = ref_dir / "style_reference.png"
                if src_path.resolve() != dst_path.resolve():
                    shutil.copy2(src_path, dst_path)
                job_data["style_reference_image"] = str(dst_path)
                if not isinstance(job_data.get("ai_visual"), dict):
                    job_data["ai_visual"] = {}
                job_data["ai_visual"]["style_reference_image"] = str(dst_path)

        data_url = job_data.pop("reference_image_data_url", None)
        if data_url and isinstance(data_url, str) and "," in data_url:
            import base64
            img_name = str(job_data.pop("reference_image_name", None) or "style_reference.png")
            _, encoded = data_url.split(",", 1)
            target_file = ref_dir / img_name
            target_file.write_bytes(base64.b64decode(encoded))
            job_data["style_reference_image"] = str(target_file)
            if "ai_visual" in job_data and isinstance(job_data["ai_visual"], dict):
                job_data["ai_visual"]["style_reference_image"] = str(target_file)

        job_data["production_recipe"] = normalize_production_recipe(
            job_data.get("production_recipe") if isinstance(job_data.get("production_recipe"), dict) else None,
            target_duration_minutes=job_data.get("target_duration_minutes"),
            visual_strategy=job_data.get("visual_strategy"),
            editing_dna=job_data.get("editing_dna") if isinstance(job_data.get("editing_dna"), dict) else None,
        )

        # Keep creative_brief duration strictly aligned with job target_duration_minutes
        target_mins = job_data.get("target_duration_minutes")
        if isinstance(job_data.get("creative_brief"), dict):
            job_data["creative_brief"] = _sync_creative_brief_duration(job_data["creative_brief"], target_mins)
        if isinstance(job_data.get("default_creative_brief"), dict):
            job_data["default_creative_brief"] = _sync_creative_brief_duration(job_data["default_creative_brief"], target_mins)

        # Initialize workspace artifacts
        (workspace_dir / "input.json").write_text(json.dumps(job_data, ensure_ascii=False, indent=2), encoding="utf-8")
        brief_content = _sync_creative_brief_duration(
            job_data.get("creative_brief") or job_data.get("default_creative_brief") or {},
            target_mins,
        )
        (workspace_dir / "creative_brief.json").write_text(json.dumps(brief_content, ensure_ascii=False, indent=2), encoding="utf-8")
        outline_content = job_data.get("outline") or {"chapters": []}
        (workspace_dir / "outline.json").write_text(json.dumps(outline_content, ensure_ascii=False, indent=2), encoding="utf-8")
        ai_visual_content = dict(job_data.get("ai_visual") or {})
        (workspace_dir / "ai_visual_settings.json").write_text(json.dumps(ai_visual_content, ensure_ascii=False, indent=2), encoding="utf-8")

        # Initialize thumbnail_design.json inheriting channel's thumbnail_dna
        try:
            tdna = job_data.get("thumbnail_dna") or {}
            from documentary.thumbnail_studio import build_default_thumbnail_design
            initial_design = build_default_thumbnail_design(
                job_id,
                workspace_dir,
                job_data,
                preferred_archetype=tdna.get("layout_template"),
                thumbnail_dna=tdna,
            )
            (workspace_dir / "thumbnail_design.json").write_text(
                json.dumps(initial_design, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

        created = self.store.create(job_data)

        # Sync to profile produced-topic memory
        if created.get("channel_profile_id"):
            try:
                self.profile_service.sync_job_to_topic_memory(created)
            except Exception:
                pass

        return created

    def delete_job(self, job_id: str) -> dict[str, Any]:
        existing = self.store.get(job_id)
        if existing is None:
            raise KeyError(f"Job {job_id} not found")
        self.store.delete(job_id)
        return {"status": "success", "deleted_job_id": job_id}
