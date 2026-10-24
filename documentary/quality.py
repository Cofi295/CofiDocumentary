from __future__ import annotations

from copy import deepcopy
import json
from math import ceil
from pathlib import Path
import re
from typing import Any

MIN_DURATION_SEC = 120
MAX_DURATION_SEC = 10800
DEFAULT_DURATION_SEC = 300


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def normalize_production_recipe(
    recipe: dict[str, Any] | None,
    *,
    target_duration_minutes: Any = None,
    visual_strategy: str | None = None,
) -> dict[str, Any]:
    result = deepcopy(recipe or {})
    strategy = str(visual_strategy or result.get("visual_strategy") or "full_footage").strip().lower()
    if strategy == "footage_first":
        strategy = "full_footage"
    elif strategy in {"selective_footage", "evidence_first"}:
        strategy = "evidence_footage"
    elif strategy in {"semi_content", "ban_content", "edit_footage"}:
        strategy = "edit_direct_footage"
    if strategy not in {"full_ai", "full_footage", "hybrid", "evidence_footage", "edit_direct_footage"}:
        raise ValueError("visual_strategy must be full_ai, full_footage, hybrid, evidence_footage, or edit_direct_footage")
    explicit_minutes = _number(target_duration_minutes)
    target = round(explicit_minutes * 60) if explicit_minutes is not None else round(_number(result.get("target_duration_sec")) or DEFAULT_DURATION_SEC)
    if target < MIN_DURATION_SEC or target > MAX_DURATION_SEC:
        raise ValueError("target duration must be between 2 and 30 minutes (or up to 180 minutes for long-form)")

    if strategy == "edit_direct_footage":
        beat_target = max(18, ceil(target / 22))
    elif 600 <= target <= 1800:
        beat_target = max(18, ceil(target / 8.5))
    else:
        beat_target = max(18, ceil(target / 7)) if target <= 1800 else max(90, ceil(target / 25))
    default_min_video = max(10, ceil(target / 12)) if target <= 1800 else max(60, ceil(beat_target * 0.7))
    default_target_video = max(default_min_video, ceil(target / 8)) if target <= 1800 else beat_target
    min_video = default_min_video if strategy == "full_footage" else 0
    target_video = default_target_video if strategy == "full_footage" else 0
    min_sources = max(3, min(15, ceil(target / 50)))
    tolerance = min(180, max(12, round(target * 0.12))) if target >= 600 else max(12, round(target * 0.08))
    contract = {
        "version": 7, "enforce": True,
        "reference_style": "cofi_documentary_premium_cinematic_motion_studio",
        "editorial_style_tier": "premium_cinematic_motion_studio",
        "editorial_authority": "production_director_plus_senior_editor_10y",
        "require_second_by_second_attention_review": True,
        "require_sequence_retention_rhythm_review": True,
        "require_proactive_editorial_decisions": True,
        "require_asset_variety_review": True,
        "require_intentional_reuse_review": True,
        "prefer_unused_valid_assets_before_repeat": True,
        "asset_variety_is_soft_editorial_rule": True,
        "max_unintentional_reuse_per_asset": 1,
        "max_contextual_reuse_per_asset": 4,
        "require_native_motion_semantic_coverage": True,
        "require_clause_ordered_motion_storyboard": True,
        "require_native_motion_against_voice_self_check": True,
        "disallow_generic_native_motion_fallback_for_sourced_video": True,
        "disallow_decorative_only_native_motion": True,
        "allow_ai_reconstruction_fallback": strategy != "full_footage",
        "prefer_ai_reconstruction_over_generic_still": True,
        "require_must_real_source_coverage": strategy not in {"full_ai", "edit_direct_footage"},
        "allow_standalone_native_motion": False,
        "require_media_anchored_annotation_motion": True,
        "mobile_annotation_min_font_px": 48,
        "require_authored_visual_system": True,
        "require_layered_compositing_review": True,
        "require_cinematic_typography_review": True,
        "require_motivated_camera_and_depth_review": True,
        "require_scene_specific_transition_review": True,
        "require_sound_design_review": True,
        "disallow_template_primary_treatment": True,
        "visual_strategy": strategy,
        "visual_routing_policy": {
            "full_ai": "ai_only",
            "full_footage": "footage_only",
            "hybrid": "story_driven",
            "evidence_footage": "evidence_first",
            "selective_footage": "evidence_first",
            "edit_direct_footage": "edit_agent_footage_plus_selective_ai",
        }[strategy],
        "flexible_story_driven": strategy in {"hybrid", "evidence_footage", "selective_footage", "edit_direct_footage"},
        "target_duration_sec": target, "duration_tolerance_sec": tolerance,
        "min_scene_count": beat_target, "target_scene_count": beat_target,
        "min_video_clip_uses": min_video, "target_video_clip_uses": target_video,
        "min_sourced_still_uses": 0, "target_sourced_still_uses": 0,
        "require_video_before_still_fallback": strategy != "full_ai",
        "min_video_search_queries_before_still": 2,
        "min_native_motion_treatments": 0,
        "min_unique_video_sources": min_sources if strategy == "full_footage" else 0,
        "typical_shot_duration_sec": [4, 8] if target <= 1800 else [12, 30], "max_routine_shot_duration_sec": 10 if target <= 1800 else 45,
        "require_actual_candidate_visual_inspection": True,
        "require_beat_visual_coverage": True, "require_actual_render_qc": True,
        "min_resolution": {"width": 1920, "height": 1080}, "min_fps": 24,
        "max_blocker_count": 0, "max_unresolved_quality_count": 0,
        "max_blackdetect_over_0_02s": 0, "max_silence_over_0_8s_below_minus48db": 0,
    }
    result.update({
        "visual_strategy": strategy,
        "target_duration_sec": target,
        "target_scene_count": f"{beat_target}-{max(beat_target, ceil(beat_target * 1.2))}",
        "target_video_footage_count": f"{min_video}-{target_video}",
        "target_still_image_count": "0-optional",
        "quality_contract": contract,
    })
    asset_rules = [
        "Use a video-first mix: real sourced video is the normal default; sourced stills are allowed only as a documented fallback after multiple video searches fail to find usable footage.",
        "Visually inspect every sourced candidate before registry acceptance.",
        "Prefer multiple independent sources and reject context-mismatched or redundant filler.",
        "For one beat, prefer complementary candidates with distinct editorial value; do not accumulate near-identical copies merely to increase asset count.",
        "Do not reuse the same exact asset across unrelated beats merely to fill coverage. Reuse one authentic asset across adjacent beats in the same story group when it remains contextually correct, especially for the same person/event/period; vary crop, framing, timestamp or motion treatment when useful. AI is a fallback for missing real coverage, not a penalty for having already used a valid real asset once.",
        "Keep routine visual shots around 4-8 seconds; split long narration beats into multiple purposeful shots instead of holding one visual too long.",
        "If accurate footage cannot cover a beat, route that beat to AI Visual instead of padding with unrelated footage.",
    ]
    if strategy == "hybrid":
        asset_rules.insert(0, "Route each visual unit to authentic Footage or AI Visual according to factual authenticity, story function and visual quality. Do not use a fixed ratio or quota.")
    elif strategy == "full_ai":
        asset_rules.insert(0, "Generate every visual unit through AI Visual and skip Footage sourcing for this project.")
    elif strategy in {"evidence_footage", "selective_footage", "evidence_first"}:
        asset_rules.insert(0, "Strict evidence-first routing: Use authentic Footage ONLY for essential real-world evidence, official records/archives and identified real characters that must be 100% authentic. All reenactments, atmospheric, context, and secondary shots must use AI Visual.")
    elif strategy == "edit_direct_footage":
        asset_rules.insert(0, "Semi-Content (Edit-Direct Footage + Selective AI): Skip the standalone Footage phase. Route 10-20% of key symbolic/anchor beats to AI Visual keyframes, and delegate 80-90% of beats to the Edit AI Agent to search, download, trim, and transform real B-roll video footage directly during the Edit phase.")
    else:
        asset_rules.insert(0, "Cover every visual unit with sourced Footage and skip AI Visual generation for this project.")
    result["asset_rules"] = asset_rules
    result["editorial_rules"] = [
        "Operate with production-director ownership and senior-editor judgment: own the attention curve, emotional arc, pacing, shot priority and polish instead of waiting for micro-instructions.",
        "Treat every second as editorially intentional: reveal, clarify, build tension, reset attention, deliver emotion or provide deliberate stillness; fix dead visual holds and retention valleys without forcing an effect every second.",
        "Review quality at frame, beat and sequence scale so individually attractive shots do not hide repetitive or flat 20-30 second stretches.",
        "Use the approved media pool intelligently: unused accurate assets are preferred when they improve the cut, but asset variety is a soft editorial rule. The same authentic file may cover adjacent beats in one story group when person/event/period context remains correct; never force every downloaded asset into the cut.",
        "Across unrelated story groups, repeated footage still needs a deliberate callback, comparison, motif, geographic anchor, identity reminder or continuity bridge with a recorded editorial reason. Do not prefer AI merely because a contextually valid real asset was already used on a nearby beat.",
        "Use motion only as an annotation overlay anchored to an approved real/AI image or video. No standalone native-motion scene is allowed.",
        "When the narration benefits from annotation, cover the meaningful clauses in spoken order with large mobile-readable text plus direct line/circle/callout, arrow or highlight interaction on the base media.",
        "Never replace a sourced-video beat that has approved media with a generic native graphic merely because a hard-coded media mapping is missing; fix the mapping/data path instead.",
        "Aim for authored premium cinematic motion-studio craft while preserving factual clarity and one clear focal hierarchy.",
        "Use a project-specific visual system across typography, graphic motifs, framing, transitions, color and sound instead of repeating canned templates.",
        "Use layered compositing, 2.5D/3D depth and motivated virtual camera language when the story benefits from spatial treatment; do not force them into every scene.",
        "Treat subtitles as editorial typography with semantic phrase grouping, hierarchy and selective keyword/number emphasis rather than a plain default caption treatment throughout.",
        "Treat repeated default zooms, line/circle/callout graphics, generic cards, one repeated transition preset or repetitive whoosh SFX as quality failures when they become the primary visual language without narrative reason.",
        "Design sound with picture using ambience, impacts, swells, tails, J/L cuts, pre-laps, ducking, beat sync and silence where appropriate.",
    ]
    return result


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{path.name} must contain a JSON object")
    return value


def _contract(job: dict[str, Any]) -> dict[str, Any]:
    recipe = job.get("production_recipe") or {}
    contract = recipe.get("quality_contract") or job.get("quality_contract") or {}
    if not isinstance(contract, dict) or not contract:
        if job.get("target_duration_minutes") not in (None, ""):
            try:
                normalized = normalize_production_recipe(
                    recipe if isinstance(recipe, dict) else None,
                    target_duration_minutes=job.get("target_duration_minutes"),
                    visual_strategy=job.get("visual_strategy"),
                )
                contract = normalized.get("quality_contract") or {}
            except Exception:
                return {}
        else:
            return {}
    elif job.get("target_duration_minutes") not in (None, ""):
        try:
            expected_sec = round(float(job["target_duration_minutes"]) * 60)
            if abs(float(contract.get("target_duration_sec") or 0) - expected_sec) > 1:
                normalized = normalize_production_recipe(
                    recipe if isinstance(recipe, dict) else None,
                    target_duration_minutes=job.get("target_duration_minutes"),
                    visual_strategy=job.get("visual_strategy"),
                )
                contract = normalized.get("quality_contract") or contract
        except Exception:
            pass
    effective = deepcopy(contract)
    # Motion policy is a current hard rule, including for jobs created with
    # older quality-contract versions. Historical jobs may still persist a
    # native-motion quota, but standalone motion is no longer valid coverage.
    effective["min_native_motion_treatments"] = 0
    effective["allow_standalone_native_motion"] = False
    effective["require_media_anchored_annotation_motion"] = True
    return effective


def _beats(workspace: Path) -> list[dict[str, Any]]:
    manifest = _read_json(workspace / "visual_manifest.json")
    beats = manifest.get("beats")
    return [item for item in beats if isinstance(item, dict)] if isinstance(beats, list) else []


def _native_motion_beat_ids(beats: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for beat in beats:
        visual_type = str(beat.get("visual_type") or "").strip().lower().replace("-", "_").replace(" ", "_")
        beat_id = str(beat.get("beat_id") or "")
        visual_tokens = {token.strip() for token in visual_type.replace(",", "+").split("+") if token.strip()}
        if beat_id and "native_motion" in visual_tokens:
            result.add(beat_id)
    return result


def _resolution(manifest: dict[str, Any]) -> tuple[int, int]:
    value = manifest.get("resolution") or {}
    return (int(value.get("width") or 0), int(value.get("height") or 0)) if isinstance(value, dict) else (0, 0)


def _require_render_metrics(manifest: dict[str, Any], contract: dict[str, Any]) -> None:
    duration = _number(manifest.get("duration_seconds"))
    if duration is None or duration <= 0:
        raise RuntimeError("render duration is missing or invalid")
    fps = _number(manifest.get("fps"))
    if fps is None or fps < float(contract["min_fps"]):
        raise RuntimeError(f"render fps {fps!r} is below required {contract['min_fps']}")
    width, height = _resolution(manifest)
    minimum = contract["min_resolution"]
    if width < int(minimum["width"]) or height < int(minimum["height"]):
        raise RuntimeError(f"render resolution {width}x{height} is below required {minimum['width']}x{minimum['height']}")


def validate_phase_quality(phase: str, workspace: Path, job: dict[str, Any]) -> None:
    contract = _contract(job)
    if not contract.get("enforce"):
        return
    if phase == "seo":
        package = _read_json(workspace / "seo_package.json")
        required_text = ("recommended_title", "description")
        missing_text = [field for field in required_text if not str(package.get(field) or "").strip()]
        if missing_text:
            raise RuntimeError(f"SEO package missing required fields: {', '.join(missing_text)}")
        title_options = package.get("title_options")
        if not isinstance(title_options, list) or not any(str(value or "").strip() for value in title_options):
            raise RuntimeError("SEO package requires at least one title option")
        for field in ("tags", "hashtags"):
            values = package.get(field)
            if not isinstance(values, list) or not any(str(value or "").strip() for value in values):
                raise RuntimeError(f"SEO package requires non-empty {field}")
        thumbnail = package.get("thumbnail") if isinstance(package.get("thumbnail"), dict) else {}
        thumbnail_prompt = str(thumbnail.get("prompt") or "").strip()
        overlay_text = str(thumbnail.get("overlay_text") or "").strip()
        featured_real_people = thumbnail.get("featured_real_people")
        identity_references = thumbnail.get("identity_references")
        visual_priority = str(thumbnail.get("visual_priority") or "").strip()
        background_policy = str(thumbnail.get("background_policy") or "").strip()
        if not thumbnail_prompt:
            raise RuntimeError("SEO package requires a production-ready thumbnail prompt")
        if not overlay_text:
            raise RuntimeError("SEO package requires thumbnail overlay_text")
        prompt_lower = thumbnail_prompt.lower()
        overlay_lower = overlay_text.lower()
        if overlay_lower not in prompt_lower:
            prompt_norm = re.sub(r"[^\w\s]", "", prompt_lower)
            words = [w for w in re.sub(r"[^\w\s]", "", overlay_lower).split() if w]
            if not (words and all(w in prompt_Lower_or_norm for w in words for prompt_Lower_or_norm in [prompt_lower + " " + prompt_norm])):
                raise RuntimeError("SEO thumbnail prompt must explicitly include overlay_text")
        valid_priorities = {
            "people_and_text_first",
            "context_and_crisis_first",
            "hybrid_context_and_person",
            "hybrid_person_and_engineering_crisis",
            "engineering_first",
            "scene_first",
            "topic_first",
            "dynamic",
        }
        if visual_priority not in valid_priorities:
            raise RuntimeError(f"SEO thumbnail visual_priority must be one of: {', '.join(sorted(valid_priorities))}")
        valid_background_policies = {
            "minimal_or_none",
            "rich_context_environment",
            "infrastructure_crisis_environment",
            "scene_first",
            "dramatic_environment",
            "cinematic_environment",
        }
        if background_policy not in valid_background_policies:
            raise RuntimeError(f"SEO thumbnail background_policy must be one of: {', '.join(sorted(valid_background_policies))}")
        has_featured_people = isinstance(featured_real_people, list) and any(str(value or "").strip() for value in featured_real_people)
        if not has_featured_people and contract.get("visual_strategy") != "edit_direct_footage" and visual_priority in {"people_and_text_first", "hybrid_context_and_person", "hybrid_person_and_engineering_crisis"}:
            raise RuntimeError("SEO thumbnail requires featured_real_people when person is featured")
        if has_featured_people:
            if not isinstance(identity_references, list) or not identity_references:
                raise RuntimeError("SEO thumbnail requires verified identity_references")
            reference_by_name: dict[str, dict[str, Any]] = {}
            for item in identity_references:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if name:
                    reference_by_name[name.lower()] = item
            for person in featured_real_people:
                person_name = str(person or "").strip()
                if not person_name:
                    continue
                ref = reference_by_name.get(person_name.lower())
                if not ref:
                    raise RuntimeError(f"SEO thumbnail missing identity reference for {person_name}")
                source_url = str(ref.get("source_url") or "").strip()
                verification_basis = str(ref.get("verification_basis") or "").strip()
                if not source_url or ref.get("visually_verified") is not True or not verification_basis:
                    raise RuntimeError(f"SEO thumbnail identity reference for {person_name} must be visually verified and include source_url + verification_basis")
                if person_name.lower() not in thumbnail_prompt.lower() or source_url.lower() not in thumbnail_prompt.lower():
                    raise RuntimeError(f"SEO thumbnail prompt must include the verified identity reference for {person_name}")
            identity_language = thumbnail_prompt.lower()
            if "exact facial identity" not in identity_language and "exact facial likeness" not in identity_language:
                raise RuntimeError("SEO thumbnail prompt must require exact facial identity/likeness")
        if background_policy == "minimal_or_none":
            identity_language = thumbnail_prompt.lower()
            if "background" not in identity_language or ("minimal" not in identity_language and "plain" not in identity_language):
                raise RuntimeError("SEO thumbnail prompt must keep background minimal/plain")
        if not isinstance(package.get("reference_analysis"), dict):
            raise RuntimeError("SEO package requires reference_analysis")

        seo_dna = job.get("seo_keyword_dna") or (job.get("channel_profile_snapshot") or {}).get("seo_keyword_dna")
        if seo_dna and isinstance(seo_dna, dict):
            primary_kw = str(seo_dna.get("primary_title_keyword") or "").strip()
            modified = False
            if primary_kw:
                rec_title = str(package.get("recommended_title") or "")
                if primary_kw.lower() not in rec_title.lower():
                    # Auto-wrap recommended_title per placement rule so it never fails PreflightService
                    placement = seo_dna.get("keyword_placement_rule") or "smart_seo_flexible"
                    raw_kw = seo_dna.get("primary_title_keyword") or primary_kw
                    if placement == "suffix_pipe":
                        package["recommended_title"] = f"{rec_title} | {raw_kw}"
                    else:
                        package["recommended_title"] = f"[{raw_kw}] {rec_title}"
                    modified = True

            mand_hashtags = seo_dna.get("mandatory_hashtags") or []
            if isinstance(mand_hashtags, list) and mand_hashtags:
                current_hashtags = list(package.get("hashtags") or [])
                existing_lower = {str(h).lower() for h in current_hashtags}
                for ht in mand_hashtags:
                    if str(ht).lower() not in existing_lower:
                        current_hashtags.append(ht)
                        existing_lower.add(str(ht).lower())
                        modified = True
                package["hashtags"] = current_hashtags

            def_tags = seo_dna.get("default_seo_tags") or []
            if isinstance(def_tags, list) and def_tags:
                current_tags = list(package.get("tags") or [])
                existing_tags_lower = {str(t).lower() for t in current_tags}
                for t in def_tags:
                    if str(t).lower() not in existing_tags_lower:
                        current_tags.append(t)
                        existing_tags_lower.add(str(t).lower())
                        modified = True
                package["tags"] = current_tags

            if modified:
                (workspace / "seo_package.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    beats = _beats(workspace) if phase in {"plan", "visuals", "footage", "ai_visual", "edit", "qc"} else []
    if phase == "voice":
        from .visuals import load_plan_manifest

        beats = [item for item in (load_plan_manifest(workspace).get("beats") or []) if isinstance(item, dict)]
    beat_ids = {str(item.get("beat_id") or "") for item in beats if item.get("beat_id")}
    if len(beats) < int(contract["min_scene_count"]):
        raise RuntimeError(f"visual manifest has {len(beats)} beats; minimum is {contract['min_scene_count']}")

    if phase == "plan":
        visual = _read_json(workspace / "visual_manifest.json")
        target = _number(visual.get("target_duration_sec"))
        if target is None or abs(target - float(contract["target_duration_sec"])) > float(contract["duration_tolerance_sec"]):
            raise RuntimeError("visual manifest target duration does not match the quality contract")
        if len(beat_ids) != len(beats):
            raise RuntimeError("visual manifest requires one unique beat_id per beat")
        script_path = workspace / "script.md"
        if script_path.exists() and float(contract["target_duration_sec"]) >= 600:
            script_text = script_path.read_text(encoding="utf-8").strip()
            if len(script_text) >= 100 and str(job.get("language") or "ko").lower() == "ko":
                non_space_chars = len(re.sub(r"\s+", "", script_text))
                target_mins = float(contract["target_duration_sec"]) / 60.0
                min_chars = int(max(1.5, target_mins - 2.8) * 285)
                max_chars = int((target_mins + 2.8) * 330)
                if non_space_chars < min_chars or non_space_chars > max_chars:
                    raise RuntimeError(
                        f"PLAN script length ({non_space_chars} non-space chars, ~{non_space_chars / 308.5:.1f}m) "
                        f"violates locked duration {target_mins:g}m ± 2.8m (required {min_chars}–{max_chars} non-space chars)"
                    )
        return

    if phase == "voice":
        voice = _read_json(workspace / "voice_manifest.json")
        duration = _number(voice.get("duration_sec"))
        target = float(contract["target_duration_sec"])
        tolerance = float(contract["duration_tolerance_sec"])
        if duration is None or duration <= 0:
            raise RuntimeError("VOICE duration is missing or invalid")
        if target >= 600:
            max_voice_drift = min(180.0, max(120.0, round(target * 0.136)))
            if abs(duration - target) > max_voice_drift:
                raise RuntimeError(
                    f"VOICE duration {duration:.1f}s ({duration / 60.0:.1f}m) violates locked target duration "
                    f"{target:.0f}s ({target / 60.0:.1f}m ± {max_voice_drift / 60.0:.1f}m)"
                )
        voice_beats = [item for item in (voice.get("beats") or []) if isinstance(item, dict)]
        voice_ids = {str(item.get("beat_id") or "") for item in voice_beats}
        missing = sorted(beat_ids - voice_ids)
        if missing:
            raise RuntimeError(f"VOICE missing beat IDs: {', '.join(missing)}")
        narration = Path(str(voice.get("narration_path") or workspace / "audio" / "narration.wav"))
        if not narration.is_absolute():
            narration = workspace / narration
        if not narration.exists():
            raise RuntimeError("VOICE narration.wav does not exist")
        return

    if phase == "visuals":
        if len(beat_ids) != len(beats):
            raise RuntimeError("VISUALS requires one unique beat_id per visual unit")
        invalid_beats = [
            str(item.get("beat_id") or "unknown")
            for item in beats
            if not str(item.get("parent_beat_id") or "").strip()
            or not str(item.get("narration_text") or "").strip()
            or not str(item.get("prompt") or "").strip()
            or not str(item.get("visual_route") or "").strip()
        ]
        if invalid_beats:
            raise RuntimeError(f"VISUALS has incomplete visual units: {', '.join(invalid_beats)}")
        prompt_manifest = _read_json(workspace / "visual_prompts.json")
        prompt_rows = [item for item in (prompt_manifest.get("prompts") or []) if isinstance(item, dict)]
        prompt_ids = {str(item.get("beat_id") or "") for item in prompt_rows if item.get("beat_id")}
        if prompt_ids != beat_ids or len(prompt_rows) != len(beats):
            raise RuntimeError("VISUALS visual_prompts.json must contain exactly one prompt for every visual unit")
        if any(not str(item.get("prompt") or "").strip() for item in prompt_rows):
            raise RuntimeError("VISUALS contains an empty prompt")
        return

    if phase == "footage":
        registry = _read_json(workspace / "asset_registry.json")
        assets = [item for item in (registry.get("assets") or []) if isinstance(item, dict)]
        native = [item for item in (registry.get("native_treatments") or []) if isinstance(item, dict)]
        if native:
            raise RuntimeError(
                "FOOTAGE standalone native_treatments are not allowed; "
                "use presentation_effects anchored to approved media"
            )
        asset_beat_ids = {
            str(item.get("beat_id") or "")
            for item in assets
            if str(item.get("beat_id") or "")
        }
        fallback_ids = {
            str(value).strip()
            for value in (registry.get("ai_fallback_beats") or [])
            if str(value).strip()
        }
        presentation = [item for item in (registry.get("presentation_effects") or []) if isinstance(item, dict)]
        unanchored_effects = sorted(
            str(item.get("id") or item.get("beat_id") or "unknown")
            for item in presentation
            if str(item.get("beat_id") or "") not in asset_beat_ids
            and str(item.get("beat_id") or "") not in fallback_ids
        )
        if unanchored_effects:
            raise RuntimeError(
                "FOOTAGE presentation_effects require approved base media: "
                + ", ".join(unanchored_effects)
            )
        covered_or_routed = asset_beat_ids | fallback_ids
        unclassified = sorted(
            str(beat.get("beat_id") or "")
            for beat in beats
            if str(beat.get("beat_id") or "")
            and str(beat.get("beat_id") or "") not in covered_or_routed
        )
        if unclassified:
            raise RuntimeError(f"FOOTAGE has unclassified beats: {', '.join(unclassified)}")
        if contract.get("require_must_real_source_coverage"):
            covered_real_beats = {
                str(item.get("beat_id") or "")
                for item in assets
                if str(item.get("beat_id") or "")
                and not (
                    isinstance(item.get("source"), dict)
                    and item["source"].get("generated_by") == "cofi_ai_visual"
                )
            }
            missing_must_real = sorted(
                str(beat.get("beat_id") or "")
                for beat in beats
                if str(beat.get("source_priority") or "").strip().lower() == "must_real"
                and str(beat.get("beat_id") or "") not in covered_real_beats
            )
            if missing_must_real:
                raise RuntimeError(f"FOOTAGE missing must_real source coverage: {', '.join(missing_must_real)}")
        strategy = str(job.get("visual_strategy") or "").strip().lower()
        if strategy == "full_footage":
            # Full Footage has no AI Visual phase after Footage: an AI fallback
            # beat would reach Edit with no media at all.
            uncovered = sorted(
                str(beat.get("beat_id") or "")
                for beat in beats
                if str(beat.get("beat_id") or "")
                and str(beat.get("beat_id") or "") not in asset_beat_ids
            )
            if uncovered:
                raise RuntimeError(
                    "FOOTAGE thiếu tư liệu (Full Footage không có AI Visual để bù): "
                    + ", ".join(uncovered)
                )
        return

    if phase == "ai_visual":
        manifest = _read_json(workspace / "ai_visual_manifest.json")
        if str(manifest.get("status") or "").lower() != "completed":
            missing = manifest.get("remaining_missing_beats") or []
            raise RuntimeError(f"AI VISUAL chưa phủ đủ beat: {', '.join(str(x) for x in missing)}")
        registry = _read_json(workspace / "asset_registry.json")
        generated_assets = [
            item for item in (registry.get("assets") or [])
            if isinstance(item, dict)
            and isinstance(item.get("source"), dict)
            and item["source"].get("generated_by") == "cofi_ai_visual"
        ]
        for asset in generated_assets:
            path = Path(str(asset.get("path") or ""))
            if not path.is_absolute():
                path = workspace / path
            if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
                raise RuntimeError(f"AI VISUAL asset không tồn tại: {asset.get('id')}")
            if str((asset.get("source") or {}).get("truth_status") or "") != "illustrative_reconstruction":
                raise RuntimeError(f"AI VISUAL asset thiếu nhãn reconstruction: {asset.get('id')}")
        return

    if phase == "edit":
        session = _read_json(workspace / "edit_session.json")
        checkpoint = _read_json(workspace / "edit_checkpoint.json")
        composition_id = str(session.get("composition_id") or "").strip()
        if not composition_id:
            raise RuntimeError("EDIT requires a job-specific Remotion composition_id")
        if session.get("composition_registered") is not True:
            raise RuntimeError("EDIT requires the job-specific Remotion composition to be registered")
        if str(checkpoint.get("composition_id") or "").strip() != composition_id:
            raise RuntimeError("EDIT checkpoint composition_id does not match the active preview composition")
        if not isinstance(checkpoint.get("source_hashes"), list) or not checkpoint.get("source_hashes"):
            raise RuntimeError("EDIT checkpoint requires source hashes for the preview cut")
        return

    manifest_name = "final_manifest.json"
    manifest = _read_json(workspace / manifest_name)
    video_value = manifest.get("video_path") or manifest.get("output_path") or manifest.get("rendered_video")
    if not video_value:
        raise RuntimeError(f"{manifest_name} is missing video_path")
    video = Path(str(video_value))
    if not video.is_absolute():
        video = workspace / video
    if not video.exists():
        raise RuntimeError(f"rendered video does not exist: {video}")
    _require_render_metrics(manifest, contract)

    if str(manifest.get("export_validation_mode") or "").lower() == "technical_auto":
        if str(manifest.get("final_qc_status") or "").upper() != "TECHNICAL_ACCEPT":
            raise RuntimeError("EXPORT technical validation did not ACCEPT the rendered MP4")
        if manifest.get("inspected_actual_render") is not True:
            raise RuntimeError("EXPORT technical validation must inspect the actual rendered MP4")
        if str(manifest.get("viewer_qc_source") or "") != "edit_phase":
            raise RuntimeError("EXPORT technical mode requires viewer quality approval from the Edit phase")
        checks = manifest.get("technical_checks") if isinstance(manifest.get("technical_checks"), dict) else {}
        required_checks = (
            "video_stream", "audio_stream", "resolution_ok", "fps_ok",
            "duration_ok", "frame_count_ok", "av_sync_ok",
        )
        missing_checks = [name for name in required_checks if checks.get(name) is not True]
        if missing_checks:
            raise RuntimeError(f"EXPORT technical checks failed: {', '.join(missing_checks)}")
        if not manifest.get("sha256"):
            raise RuntimeError("EXPORT requires final video SHA-256")
        return

    if str(manifest.get("final_qc_status") or "").upper() != "ACCEPT" or manifest.get("inspected_actual_render") is not True:
        raise RuntimeError("QC requires ACCEPT after inspection of the actual rendered MP4")
    qc = manifest.get("qc") if isinstance(manifest.get("qc"), dict) else {}
    for field, limit_field in [
        ("blocker_count", "max_blocker_count"),
        ("unresolved_quality_count", "max_unresolved_quality_count"),
        ("blackdetect_over_0_02s", "max_blackdetect_over_0_02s"),
        ("silence_over_0_8s_below_minus48db", "max_silence_over_0_8s_below_minus48db"),
    ]:
        value = _number(qc.get(field))
        if value is None or value > float(contract[limit_field]):
            raise RuntimeError(f"QC quality gate: {field}={value!r} exceeds {contract[limit_field]}")
    if not manifest.get("sha256"):
        raise RuntimeError("QC requires final video SHA-256")
