from __future__ import annotations

import collections
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
    editing_dna: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = deepcopy(recipe or {})
    edna = editing_dna if isinstance(editing_dna, dict) else {}
    vox_preset = str(edna.get("preset_id") or edna.get("editing_dna_preset") or "").strip()
    edna_vm = edna.get("visual_mix") if isinstance(edna.get("visual_mix"), dict) else {}
    is_non_vox_cinema = (
        edna.get("vox_enabled") is False
        or (edna.get("vox_desk_enabled") is False and edna.get("vox_satellite_enabled") is False)
        or str(edna.get("visual_priority_mode") or "").strip().lower() == "ai_cinema_character_drama"
        or str(edna.get("content_mode") or "").strip().lower() in {"creative_audio_drama", "devotional_essay"}
        or vox_preset in {"kr_goodnight_cinema_drama", "cinema_character_drama", "sacred_devotional", "grace_letter"}
    )
    is_vox_newsroom = (
        not is_non_vox_cinema
        and (
            vox_preset in {"forensic_noir_director_v2", "vox_china_crime_newsroom_v10"}
            or str(edna.get("director_mode") or "").strip().lower() in {"v2", "vox_china_crime_newsroom_v10"}
            or (_number(edna.get("min_real_footage_ratio")) or _number(edna_vm.get("min_footage_floor")) or 0.0) >= 0.45
        )
    )
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

    if strategy == "edit_direct_footage" or is_vox_newsroom:
        beat_target = max(18, ceil(target / 8.5)) if target <= 1800 else max(18, ceil(target / 22))
    elif 600 <= target <= 1800:
        beat_target = max(18, ceil(target / 8.5))
    else:
        beat_target = max(18, ceil(target / 7)) if target <= 1800 else max(90, ceil(target / 25))
    default_min_video = max(10, ceil(target / 12)) if target <= 1800 else max(60, ceil(beat_target * 0.7))
    default_target_video = max(default_min_video, ceil(target / 8)) if target <= 1800 else beat_target
    ftg_floor = max(0.50, float(_number(edna.get("min_real_footage_ratio")) or 0.50)) if is_vox_newsroom else 0.0
    if is_vox_newsroom:
        min_video = ceil(beat_target * ftg_floor)
        target_video = max(min_video, ceil(beat_target * max(ftg_floor, 0.55)))
    else:
        min_video = default_min_video if strategy == "full_footage" else 0
        target_video = default_target_video if strategy == "full_footage" else 0
    min_sources = max(3, min(15, ceil(target / 50)))
    tolerance = max(480, round(target * 0.35)) if target >= 600 else max(45, round(target * 0.25))
    routing_policy = (
        "ai_cinema_character_drama_80_15_5"
        if is_non_vox_cinema and str(edna.get("visual_priority_mode") or "").strip().lower() == "ai_cinema_character_drama"
        else (
            "vox_newsroom_v13_composable_lego_50pct_footage"
            if is_vox_newsroom
            else {
                "full_ai": "ai_only",
                "full_footage": "footage_only",
                "hybrid": "story_driven",
                "evidence_footage": "evidence_first",
                "selective_footage": "evidence_first",
                "edit_direct_footage": "edit_agent_footage_plus_selective_ai",
            }[strategy]
        )
    )
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
        "asset_variety_is_soft_editorial_rule": False,
        "max_unintentional_reuse_per_asset": 1,
        "max_contextual_reuse_per_asset": 1,
        "require_eye_verified_footage_crop_and_semantic_match": True,
        "forbid_auto_cut_and_auto_splice": True,
        "require_contextual_motion_text_diversity": True,
        "forbid_periodic_motion_text_spacing": True,
        "require_context_matched_motion_text_style": True,
        "require_native_motion_semantic_coverage": not is_non_vox_cinema,
        "require_clause_ordered_motion_storyboard": not is_non_vox_cinema,
        "require_native_motion_against_voice_self_check": not is_non_vox_cinema,
        "disallow_generic_native_motion_fallback_for_sourced_video": True,
        "disallow_decorative_only_native_motion": True,
        "allow_ai_reconstruction_fallback": strategy != "full_footage",
        "prefer_ai_reconstruction_over_generic_still": True,
        "require_must_real_source_coverage": (not is_non_vox_cinema) and (strategy not in {"full_ai", "edit_direct_footage"}),
        "allow_standalone_native_motion": bool(is_vox_newsroom),
        "require_media_anchored_annotation_motion": (not is_vox_newsroom) and (not is_non_vox_cinema),
        "mobile_annotation_min_font_px": 48,
        "require_authored_visual_system": True,
        "require_layered_compositing_review": True,
        "require_cinematic_typography_review": True,
        "require_motivated_camera_and_depth_review": True,
        "require_scene_specific_transition_review": True,
        "require_sound_design_review": True,
        "disallow_template_primary_treatment": True,
        "visual_strategy": strategy,
        "visual_routing_policy": routing_policy,
        "flexible_story_driven": is_vox_newsroom or (strategy in {"hybrid", "evidence_footage", "selective_footage", "edit_direct_footage"}),
        "target_duration_sec": target, "duration_tolerance_sec": tolerance,
        "min_scene_count": beat_target, "target_scene_count": beat_target,
        "min_video_clip_uses": min_video, "target_video_clip_uses": target_video,
        "min_sourced_still_uses": 0, "target_sourced_still_uses": 0,
        "require_video_before_still_fallback": (not is_non_vox_cinema) and (is_vox_newsroom or (strategy != "full_ai")),
        "min_video_search_queries_before_still": 2,
        "min_native_motion_treatments": ceil(beat_target * 0.18) if is_vox_newsroom else 0,
        "min_unique_video_sources": min_sources if (strategy == "full_footage" or is_vox_newsroom) else 0,
        "typical_shot_duration_sec": [3, 6] if is_vox_newsroom else ([4, 8] if target <= 1800 else [12, 30]),
        "max_routine_shot_duration_sec": 8 if is_vox_newsroom else (10 if target <= 1800 else 45),
        "require_actual_candidate_visual_inspection": True,
        "require_beat_visual_coverage": True, "require_actual_render_qc": True,
        "min_resolution": {"width": 1920, "height": 1080}, "min_fps": 24,
        "max_blocker_count": 0, "max_unresolved_quality_count": 0,
        "max_blackdetect_over_0_02s": 0, "max_silence_over_0_8s_below_minus48db": 0,
    }
    if is_vox_newsroom:
        contract["min_real_footage_ratio"] = ftg_floor
        contract["max_vox_scene_ratio"] = float(_number(edna.get("max_vox_scene_ratio") or edna_vm.get("max_vox_scene_ratio")) or 1.0)
        contract["max_cinema_text_ratio"] = float(_number(edna.get("max_cinema_text_ratio") or edna_vm.get("max_cinema_text_ratio")) or 0.16)
        contract["max_ai_reconstruction_ratio"] = float(_number(edna.get("max_ai_reconstruction_ratio") or edna_vm.get("max_ai_reconstruction_ratio")) or 0.22)
        contract["max_monolithic_page_wrapper_uses"] = 3
        contract["vox_verb_sliding_window"] = 5
        contract["vox_camera_topology_sliding_window"] = 3
    result.update({
        "visual_strategy": strategy,
        "target_duration_sec": target,
        "target_scene_count": f"{beat_target}-{max(beat_target, ceil(beat_target * 1.2))}",
        "target_video_footage_count": f"{min_video}-{target_video}",
        "target_still_image_count": "0-optional",
        "quality_contract": contract,
    })
    asset_rules = [
        "100% EYE-VERIFIED CLEAN CROP & 100% VOICE MATCH LAW: Every video or image footage attached to a spoken sentence must be visually inspected by the AI Agent's eyes (`read_file` / `vision_inspect_frames` on `STORYBOARD_<id>.jpg`, `GRID_<id>.jpg`, and `*_3frames.jpg`) to guarantee: (1) 100% of third-party logos/watermarks/QR codes and 100% of third-party running text/tickers/burned-in foreign subtitles are cleanly cropped out (`crop=W:H:X:Y`), and (2) the visual content matches 100% of what the spoken sentence is talking about.",
        "STRICT BAN ON AUTOMATIC CUTTING AND AUTOMATIC SPLICING (`0%` `--auto`, `0%` blind offset math, `0%` cross-beat clip holding): Never use code to automatically cut or automatically splice footage onto beats, which causes image and voice meaning to drift apart.",
    ]
    if is_non_vox_cinema:
        asset_rules.append(
            "WARM 35MM CINEMA & ATMOSPHERIC B-ROLL PRIORITY (`~80% Character-Sheet-Locked 35mm AI Cinema + ~15% Clean 4K Atmospheric B-Roll + ~5% Warm Chapter Cards`, `0%` VOX graphics): `@vox` is completely bypassed (`vox_enabled = false`). Lock every recurring character's face, age, hair, and wardrobe to the episode's Flow Character Reference Sheet (`media/character_sheet/`), keep Highlight Luma <= 215 for night-safe viewing, and restrict sourced B-roll strictly to clean atmospheric scenery/craft hands (`0%` news broadcasts or stranger faces, `max_uses = 1`)."
        )
    else:
        asset_rules.append(
            "3-TIER VISUAL PRIORITY (`#1 Real Footage -> #2 Bespoke VOX Illustration -> #3 AI Image Last Resort`): Each footage clip may be used at most once (`max_uses = 1`). Whenever a sentence has no authentic footage matching 100% of its meaning, route that sentence to Priority #2 VOX illustration (`<Desk>` or `<GeoJson3DMapStage>`) first, and Priority #3 AI Image only as the final fallback."
        )
    if is_vox_newsroom:
        asset_rules.insert(
            0,
            "Director V2 Canonical 3-Tier Visual Priority (`forensic_noir_director_v2` — `#1 Real Footage -> #2 Bespoke VOX Illustration -> #3 AI Image Last Resort`): (1) Priority #1 `REAL_FTG`: 100% eye-verified authentic case/investigation/courtroom/forensic archival footage (`footage/S_F*.mp4`, calibrated `crop=W:H:X:Y` on `100px` grid stripping 100% of third-party logos & running text, `15%-50%-85%` contact-sheet verified 100% semantic match with the spoken sentence, `0%` automatic cutting/splicing, `max_uses = 1`); (2) Priority #2 `VOX_NEWSROOM` (`src/vox-studio/vox-editorial-desk/index.tsx` & `<GeoJson3DMapStage>`): mandatory whenever a sentence lacks 100%-matching real footage, with 0% fixed template count, 0% fixed spacing, and 100% independent per-sentence meaning, motion, layout, entry, cut-and-paste, and purposeful `<RedCircle>` (only when needed) + `<GeoJson3DMapStage>` strictly for suspect/police movement routes with exact real-world WGS84 coordinates; (3) Priority #3 `AI_MASCOT` (`<beat_id>_ai_keyframe.jpg`) + dark `FramelessCinemaTextBeat.tsx` (`8%–12%`) only as the final fallback.",
        )
    elif is_non_vox_cinema:
        asset_rules.insert(
            0,
            "Non-VOX Cinema Character & Atmospheric Priority (`vox_enabled = false`): Route ~80% character/dialogue beats to Character-Sheet-locked Warm 35mm AI Cinema (`@ai_visual`), ~15% transitional scenery/craft beats to eye-verified clean 4K Atmospheric B-Roll (`@footage`), and ~5% chapter/quote beats to warm serif `FramelessCinemaTextBeat.tsx` (`0%` VOX boards or 3D pursuit maps).",
        )
    elif strategy == "hybrid":
        asset_rules.insert(0, "Route each visual unit to 100% eye-verified authentic Footage, bespoke VOX, or AI Visual according to 100% spoken-sentence semantic match. Never use automatic cutting/splicing or fixed quotas.")
    elif strategy == "full_ai":
        asset_rules.insert(0, "Generate every visual unit through AI Visual and skip Footage sourcing for this project.")
    elif strategy in {"evidence_footage", "selective_footage", "evidence_first"}:
        asset_rules.insert(0, "Strict evidence-first routing: Use 100% eye-verified authentic Footage ONLY when it matches 100% of the spoken sentence and is cleanly cropped of all third-party logos and running text.")
    elif strategy == "edit_direct_footage":
        asset_rules.insert(0, "Edit-Direct Eye-Verified Footage: Every footage cut in Edit must use `--probe-storyboard`, eye inspection of `STORYBOARD_<id>.jpg` + `GRID_<id>.jpg`, explicit `--start-offset`, calibrated `--crop-mode`, and `--observed-content` matching 100% of the spoken sentence (`0%` `--auto` blind cutting).")
    else:
        asset_rules.insert(0, "Cover every visual unit with 100% eye-verified sourced Footage matching 100% of the spoken sentence.")
    result["asset_rules"] = asset_rules
    motion_rule = (
        "Author 100% independent per-sentence VOX scenes (`src/vox-studio/vox-editorial-desk/index.tsx` & `<GeoJson3DMapStage>`) as Priority #2 whenever a spoken sentence lacks 100%-matching real footage (`0%` template copy-paste, `0%` decorative clutter, `max_uses = 1` per prop/cutout, verified via `read_file`) + dark `FramelessCinemaTextBeat.tsx` alongside 100% eye-verified clean-cropped real archival case footage."
        if is_vox_newsroom
        else (
            "Bypass `@vox` completely (`0%` VOX tabletop boards, `0%` 3D GIS maps). Use slow, soothing Ken Burns (`1.00 -> 1.035`), `26-frame` warm cross-dissolves, and warm serif `FramelessCinemaTextBeat.tsx` chapter curtains (`제1장`..`제6장`) with Warm Nocturne Piano/Cello BGM and `0%` startle SFX."
            if is_non_vox_cinema
            else "Use motion only as an annotation overlay anchored to an approved real/AI image or video. No standalone native-motion scene is allowed."
        )
    )
    priority_editorial_rule = (
        "Route character & emotional beats to Priority #1 Warm 35mm AI Cinema locked to the episode's Flow Character Reference Sheet, transitional atmosphere beats to clean 4K B-Roll (`max_uses = 1`), and chapter openings to warm serif `FramelessCinemaTextBeat.tsx` (`0%` VOX graphics)."
        if is_non_vox_cinema
        else "Whenever a spoken sentence has no authentic footage matching 100% of its meaning, route it to Priority #2 VOX illustration first, and Priority #3 AI Image only as the last resort."
    )
    result["editorial_rules"] = [
        "Operate with production-director ownership and senior-editor judgment: own the attention curve, emotional arc, pacing, shot priority and polish instead of waiting for micro-instructions.",
        "Treat every second as editorially intentional: reveal, clarify, build tension, reset attention, deliver emotion or provide deliberate stillness; fix dead visual holds and retention valleys without forcing an effect every second.",
        "100% EYE-VERIFIED FOOTAGE & ZERO AUTO-CUT/AUTO-SPLICE: Visually inspect every video/image attached to a spoken sentence by eye (`read_file` / `vision_inspect_frames`). Guarantee 100% of third-party logos and running text are cropped out, and guarantee 100% semantic match between the visual and the spoken sentence. Never run automatic cutting or automatic splicing code, and never hold/repeat a clip across sentences (`max_uses = 1`).",
        priority_editorial_rule,
        motion_rule,
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
    edna = job.get("editing_dna") if isinstance(job.get("editing_dna"), dict) else {}
    snap_edna = (
        (job.get("channel_profile_snapshot") or {}).get("editing_dna")
        if isinstance(job.get("channel_profile_snapshot"), dict)
        else {}
    )
    active_edna = edna or (snap_edna if isinstance(snap_edna, dict) else {})
    vox_preset = str(active_edna.get("preset_id") or active_edna.get("editing_dna_preset") or "").strip()
    is_vox_newsroom = (
        vox_preset in {"forensic_noir_director_v2", "vox_china_crime_newsroom_v10"}
        or str(active_edna.get("director_mode") or "").strip().lower() in {"v2", "vox_china_crime_newsroom_v10"}
        or str(job.get("channel_profile_id") or "").strip() in {"channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2"}
    )
    contract = recipe.get("quality_contract") or job.get("quality_contract") or {}
    if not isinstance(contract, dict) or not contract:
        if job.get("target_duration_minutes") not in (None, ""):
            try:
                normalized = normalize_production_recipe(
                    recipe if isinstance(recipe, dict) else None,
                    target_duration_minutes=job.get("target_duration_minutes"),
                    visual_strategy=job.get("visual_strategy"),
                    editing_dna=active_edna,
                )
                contract = normalized.get("quality_contract") or {}
            except Exception:
                return {}
        else:
            return {}
    elif job.get("target_duration_minutes") not in (None, ""):
        try:
            expected_sec = round(float(job["target_duration_minutes"]) * 60)
            if abs(float(contract.get("target_duration_sec") or 0) - expected_sec) > 1 or (
                is_vox_newsroom and str(contract.get("visual_routing_policy") or "") != "vox_newsroom_v13_composable_lego_50pct_footage"
            ):
                normalized = normalize_production_recipe(
                    recipe if isinstance(recipe, dict) else None,
                    target_duration_minutes=job.get("target_duration_minutes"),
                    visual_strategy=job.get("visual_strategy"),
                    editing_dna=active_edna,
                )
                contract = normalized.get("quality_contract") or contract
        except Exception:
            pass
    effective = deepcopy(contract)
    if is_vox_newsroom:
        effective["allow_standalone_native_motion"] = True
        effective["require_media_anchored_annotation_motion"] = False
        effective.setdefault("min_real_footage_ratio", 0.50)
        effective.setdefault("max_vox_scene_ratio", 0.28)
        effective.setdefault("max_cinema_text_ratio", 0.16)
    else:
        # Non-Vox profiles forbid standalone native-motion filler scenes.
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



_DANGLING_HUMAN_MODIFIER_RE = re.compile(
    r"(?:(?:(?:스물|서른|마흔|쉰|예순|일흔)[한두세네다섯여섯일곱여덟아홉]?|다섯|여섯|일곱|여덟|아홉|열[한두세네다섯여섯일곱여덟아홉]?|[0-9]+)\s*살(?:이\s*된|의)?\s+(?:동영상\s*플랫폼|판결문|수사\s*기록|법원|공안국|증거물|서류\s*뭉치|골목길|기차역|중국\s*전체))"
    r"|(?:무릎을\s*꿇은\s+(?:판결문|수사\s*기록|서류|공소장|증거물))"
    r"|(?:다섯\s*살\s+엄마)"
)
_DUPLICATE_TOPIC_SUBJECT_RE = re.compile(
    r"(?<![가-힣])([가-힣]{2,4}(?:은|는))\s+[^.!?,]{1,50}(?<!다른\s)(?<!다른\s한\s)(?<![가-힣])\1(?![가-힣])"
)
_UNQUOTED_DIRECT_SPEECH_RANEUN_RE = re.compile(
    r'(?<!["\u201d\u2019\'])(?:십시오|십쇼|겠습니다|세요|마십시오|마라|어라)라는\s*(?:짧은\s*|마지막\s*|단\s*)?(?:한마디|말|외침|유언|대답)'
)
_RAW_KO_PERCENT_SYMBOL_RE = re.compile(r"\d+\s*%")
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.?!])["”’]?\s+')
_PURE_FORMAL_SEUMNIDA_END_RE = re.compile(r'(?:습니다|입니다|입니까|습니까)[.?!]?["\'\u201d\u2019]?$')
_CONVERSATIONAL_EXPLANATORY_END_RE = re.compile(
    r'(?:겁니다|것입니다|셈입니다|터였습니다|뿐입니다|뿐이었습니다|따름입니다)[.?!]?["\'\u201d\u2019]?$'
)
_ARCHAIC_KO_HAOCHE_RE = re.compile(
    r'(?:^|[\s"\'\u201c\u2018])(?:맞소|아시오|모르오|그리하오)[,.?!\s]'
    r'|(?:처음이오|것\s*같소|수\s*없소|수\s*있소|말해\s*보시오|들어\s*보시오)[.?!]?["\'\u201d\u2019]?$'
)
_FINITE_KO_PREDICATE_END_RE = re.compile(
    r'(?:다|요|죠|까|네|군|지|라|자|마|소|오)[.?!…]*["\'\u201d\u2019]?$'
)
_TRUNCATED_KO_GEOLKKAYO_END_RE = re.compile(
    r'(?:던|는|은|[가-힣]+)\s*걸까요\?["\'\u201d\u2019]?$'
)
_KO_INTERROGATIVE_CUE_RE = re.compile(
    r"(?<![가-힣])(?:왜(?=[\s,.?!\"'\u201d\u2019])|어째서|어떻게|어디|언제|누구|누가|무엇|무슨|뭐가|뭐를|어떤|어느|얼마나|얼마|몇(?!몇)|도대체|대체(?=[\s,?!])|과연|혹시|설마|정말|진짜)"
)


def resolve_korean_profile_style_flags(job: dict[str, Any] | None) -> dict[str, bool]:
    """Inspect active job/profile DNA so technical quality gates never override a profile's custom creative register."""
    if not isinstance(job, dict) or not job:
        return {"custom_register": False, "allow_archaic_speech": False}
    snapshot = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    ed = snapshot.get("editorial_dna") if isinstance(snapshot.get("editorial_dna"), dict) else {}
    brief = job.get("creative_brief") if isinstance(job.get("creative_brief"), dict) else {}
    def_brief = snapshot.get("default_creative_brief") if isinstance(snapshot.get("default_creative_brief"), dict) else {}

    reg_raw = str(
        job.get("speech_register")
        or brief.get("speech_register")
        or brief.get("tone_register")
        or ed.get("speech_register")
        or snapshot.get("speech_register")
        or ""
    ).strip().lower()

    custom_register_tokens = {
        "haeyo", "해요", "해요체", "pastoral", "pastoral_warm", "devotional",
        "poetic", "essay", "banmal", "반말", "conversational", "custom", "free",
    }
    custom_register = bool(
        reg_raw in custom_register_tokens
        or job.get("allow_custom_register") is True
        or ed.get("allow_custom_register") is True
        or brief.get("allow_custom_register") is True
    )

    profile_blob = " ".join([
        str(snapshot.get("label") or ""),
        str(snapshot.get("voice_and_structure") or ""),
        str(ed.get("voice_and_structure") or ""),
        str(ed.get("narrative_genre") or ""),
        str(brief.get("writing_style") or def_brief.get("writing_style") or ""),
        str(brief.get("custom_rules") or def_brief.get("custom_rules") or ""),
        str(job.get("topic") or ""),
        str(job.get("title") or ""),
    ]).lower()

    if not custom_register and any(
        tok in profile_blob
        for tok in ("해요체", "편지체", "은혜의 편지", "하나님의 말씀", "기도문", "묵상", "에세이", "수필", "동화", "반말")
    ):
        custom_register = True

    allow_archaic = bool(
        job.get("allow_haoche") is True
        or ed.get("allow_archaic_or_scriptural_korean") is True
        or brief.get("allow_haoche") is True
        or any(
            tok in profile_blob
            for tok in ("사극", "조선", "고려", "왕조", "삼국시대", "고전", "성경", "하나님의 말씀", "은혜의 편지")
        )
    )
    return {
        "custom_register": custom_register,
        "allow_archaic_speech": allow_archaic,
    }


def validate_korean_script_grammar_integrity(
    beats: list[dict[str, Any]] | str,
    *,
    enforce_prosody: bool = True,
    job: dict[str, Any] | None = None,
) -> None:
    """Validate Korean technical syntax integrity & '%' TTS safety, adapting prosody checks to the profile's register."""
    style_flags = resolve_korean_profile_style_flags(job)
    custom_register = style_flags["custom_register"]
    allow_archaic = style_flags["allow_archaic_speech"]

    raw_script_text: str | None = None
    if isinstance(beats, str):
        raw_script_text = beats
        parsed_beats: list[dict[str, Any]] = []
        for idx_ln, raw_ln in enumerate(beats.splitlines()):
            s_ln = raw_ln.strip()
            if s_ln and not s_ln.startswith("#"):
                parsed_beats.append({"beat_id": f"B{len(parsed_beats) + 1:03d}", "narration_text": s_ln, "line": idx_ln + 1})
        beats = parsed_beats

    sentences: list[tuple[str, str]] = []
    for item in beats:
        if not isinstance(item, dict):
            continue
        bid = str(item.get("beat_id") or "unknown")
        narration = str(item.get("narration_text") or item.get("text") or "").strip()
        if not narration:
            continue
        m_dangling = _DANGLING_HUMAN_MODIFIER_RE.search(narration)
        if m_dangling:
            raise RuntimeError(
                f"PLAN Korean grammar integrity error in {bid}: dangling human modifier attached to inanimate noun ('{m_dangling.group(0)}')"
            )
        m_dup = _DUPLICATE_TOPIC_SUBJECT_RE.search(narration)
        if m_dup:
            raise RuntimeError(
                f"PLAN Korean grammar integrity error in {bid}: duplicate topic subject '{m_dup.group(1)}' in same clause ('{m_dup.group(0)}')"
            )
        m_unquoted = _UNQUOTED_DIRECT_SPEECH_RANEUN_RE.search(narration)
        if m_unquoted:
            raise RuntimeError(
                f"PLAN Korean direct-speech error in {bid}: unquoted direct speech glued onto '~라는' ('{m_unquoted.group(0)}'); use attribution-first indirect speech or clean quotes"
            )
        if not allow_archaic:
            m_haoche = _ARCHAIC_KO_HAOCHE_RE.search(narration)
            if m_haoche:
                raise RuntimeError(
                    f"PLAN Korean archaic translationese 하오체 error in {bid}: '{m_haoche.group(0).strip()}' sounds like period-drama translationese; use modern Korean indirect narration or contemporary spoken Korean"
                )
        for raw_sent in _SENTENCE_SPLIT_RE.split(narration):
            s = raw_sent.strip()
            if s and any("\uac00" <= ch <= "\ud7a3" for ch in s):
                if _TRUNCATED_KO_GEOLKKAYO_END_RE.search(s) and not _KO_INTERROGATIVE_CUE_RE.search(s):
                    raise RuntimeError(
                        f"PLAN Korean incomplete interrogative error in {bid}: '{s}' ends in '~걸까요?' without an interrogative/modal cue "
                        "('왜', '어떻게', '무엇이', '과연', '혹시', '대체'); add the missing question word at the front so meaning is complete"
                    )
                if not (s.startswith(('"', "“", "'", "‘")) and s.endswith(('"', "”", "'", "’", '."', '.”'))):
                    from .critic_loops import find_chinese_sye_traps
                    from .voice import (
                        _KO_HANGUL_SPACED_DECIMAL_RE,
                        _KO_ORTHOGRAPHY_TTS_FIX_RULES,
                        _KO_YEAR_HAE_TO_NYEON_RE,
                    )

                    sye_traps_any = find_chinese_sye_traps(s)
                    if sye_traps_any:
                        m_sye_any = sye_traps_any[0]
                        win_sye_any = s[max(0, m_sye_any.start() - 3) : min(len(s), m_sye_any.end() + 6)]
                        raise RuntimeError(
                            f"PLAN Korean TTS '셰' phonetic trap in {bid}: Chinese '셰' syllable in '{win_sye_any.strip()}' wobbles to '쉐/쉬/쇠'; "
                            "write '시에' instead ('시에런량', '시에윈', '시에쭝펀', '우시에위', '시에 씨')"
                        )
                    m_hae_any = _KO_YEAR_HAE_TO_NYEON_RE.search(s)
                    if m_hae_any:
                        raise RuntimeError(
                            f"PLAN Korean TTS year-counter '해' phonetic trap in {bid}: '{m_hae_any.group(0)}' is mispronounced as '회' ('times') by TTS; "
                            "write Sino-Korean '년' with matching batchim particles ('19년의', '18년 전', '10년이 넘도록')"
                        )
                    m_dec_any = _KO_HANGUL_SPACED_DECIMAL_RE.search(s)
                    if m_dec_any and (re.search(r"\s", m_dec_any.group(0)) or "쩜" in m_dec_any.group(0)):
                        raise RuntimeError(
                            f"PLAN Korean TTS spaced-decimal stutter trap in {bid}: '{m_dec_any.group(0)}' leaves spaces around '점'; "
                            "join tightly without spaces around '점' (e.g. '구십구점구구 퍼센트', '99.99퍼센트')"
                        )
                    for ort_pat, ort_repl in _KO_ORTHOGRAPHY_TTS_FIX_RULES:
                        m_ort_any = ort_pat.search(s)
                        if m_ort_any:
                            fixed_tok = ort_pat.sub(ort_repl, m_ort_any.group(0))
                            raise RuntimeError(
                                f"PLAN Korean orthography/morphology error in {bid}: '{m_ort_any.group(0)}' must be written as '{fixed_tok}'"
                            )
                    m_mil_any = re.search(
                        r"(?<!\d)(\d{2,3})\s*식(?=\s*(?:반자동|자동|군용|제식|권총|소총|기관총|기관단총|화기|무기|장비|총기|탄피|탄환|실탄)|(?:이|가|을|를|은|는|의|에|도|만|으로|로|과|와)(?![가-힣])|[,\s.?!]|$)"
                        r"(?!\s*(?:사|당|품|구|물|민|량|수|탁|장|전))",
                        s,
                    ) or re.search(
                        r"(?<!\d)(\d{2,3})\s*(?:연대|사단|여단)(?!\s*(?:장학|세브란스|병원|대학교))",
                        s,
                    )
                    if m_mil_any:
                        raise RuntimeError(
                            f"PLAN Korean TTS military code error in {bid}: '{m_mil_any.group(0)}' must be spelled in Hangul ('오륙식', '팔일식', '오사식', '백사십칠 연대')"
                        )
                sentences.append((bid, s))

    if enforce_prosody and not custom_register and (
        raw_script_text is not None
        or any(isinstance(it, dict) and it.get("is_standalone_paragraph") is not None for it in beats)
    ):
        paras_to_check: list[list[str]] = []
        if raw_script_text is not None:
            cur_p: list[str] = []
            for raw_ln in raw_script_text.splitlines():
                s_ln = raw_ln.strip()
                if not s_ln or s_ln.startswith("#"):
                    if cur_p:
                        paras_to_check.append(cur_p)
                        cur_p = []
                else:
                    cur_p.append(s_ln)
            if cur_p:
                paras_to_check.append(cur_p)
        else:
            for it in beats:
                if not isinstance(it, dict):
                    continue
                txt_it = str(it.get("narration_text") or it.get("text") or "").strip()
                if not txt_it:
                    continue
                if it.get("is_standalone_paragraph") is True:
                    paras_to_check.append([txt_it])
                else:
                    paras_to_check.append([txt_it, "context_sentence"])
        standalone_noun_p_indices: list[int] = []
        for p_i, p_lines in enumerate(paras_to_check):
            if len(p_lines) != 1:
                continue
            p_sents = [
                s_part.strip()
                for s_part in _SENTENCE_SPLIT_RE.split(p_lines[0])
                if s_part.strip() and any("\uac00" <= ch <= "\ud7a3" for ch in s_part)
            ]
            if len(p_sents) == 1 and not _FINITE_KO_PREDICATE_END_RE.search(p_sents[0]):
                standalone_noun_p_indices.append(p_i)
        close_noun_p = any(
            (standalone_noun_p_indices[k] - standalone_noun_p_indices[k - 1]) < 8
            for k in range(1, len(standalone_noun_p_indices))
        )
        if len(standalone_noun_p_indices) > 4 or (len(standalone_noun_p_indices) >= 2 and close_noun_p):
            raise RuntimeError(
                "PLAN Korean standalone_one_line_noun_crutch_excess error: "
                f"standalone_one_line_noun_paragraphs={len(standalone_noun_p_indices)} "
                "(max allowed <= 4 across episode and >= 8 paragraphs apart)"
            )

    # Full-script prosody & rhythm gate (activates on real episodes with >= 35 sentences)
    if not enforce_prosody or len(sentences) < 35:
        return

    for item in beats:
        if not isinstance(item, dict):
            continue
        bid = str(item.get("beat_id") or "unknown")
        narration = str(item.get("narration_text") or item.get("text") or "").strip()
        m_pct = _RAW_KO_PERCENT_SYMBOL_RE.search(narration)
        if m_pct:
            raise RuntimeError(
                f"PLAN Korean TTS symbol error in {bid}: raw '%' symbol found ('{m_pct.group(0)}'); write '퍼센트' in Korean scripts"
            )

    # Exclude verbatim quoted sentences from narrator ending monotony calculation
    narrator_sents = [
        (bid, s)
        for bid, s in sentences
        if not (s.startswith(('"', "“", "'", "‘")) and s.endswith(('"', "”", "'", "’", '."', '.”')))
    ]
    total_narr = len(narrator_sents)

    # When a profile opts into a custom creative register (해요체, pastoral letter, poetic essay, etc.),
    # do NOT force standard news '~습니다' ratios—only guard against extreme verbless noun-list floods.
    if custom_register:
        if total_narr >= 80:
            noun_end_count = sum(
                1 for _, s in narrator_sents if not _FINITE_KO_PREDICATE_END_RE.search(s)
            )
            noun_end_ratio = noun_end_count / float(total_narr)
            if noun_end_ratio > 0.22:
                raise RuntimeError(
                    f"PLAN Korean noun-fragment flood error: verbless noun endings occupy {noun_end_ratio * 100:.1f}% "
                    f"({noun_end_count}/{total_narr}); restore natural predicates for smooth TTS delivery"
                )
        return

    if total_narr >= 30:
        pure_formal_count = 0
        consec_formal = 0
        max_consec_formal = 0
        max_consec_span = ""
        for bid, s in narrator_sents:
            is_pure_formal = bool(
                _PURE_FORMAL_SEUMNIDA_END_RE.search(s)
                and not _CONVERSATIONAL_EXPLANATORY_END_RE.search(s)
            )
            if is_pure_formal:
                pure_formal_count += 1
                consec_formal += 1
                if consec_formal > max_consec_formal:
                    max_consec_formal = consec_formal
                    max_consec_span = bid
            else:
                consec_formal = 0

        jyo_count = sum(1 for _, s in narrator_sents if re.search(r'죠[.?!]?["\'\u201d\u2019]?$', s))
        jyo_ratio = jyo_count / float(total_narr)
        deogunyo_hits = [bid for bid, s in narrator_sents if re.search(r"""더군요[.?!]?["'”’]?$""", s)]
        if deogunyo_hits:
            raise RuntimeError(
                f"PLAN Korean narrator POV error near {deogunyo_hits[0]}: '~더군요' ({len(deogunyo_hits)}x) carries 1st-person eyewitness recollection tone; "
                "use objective 3rd-person documentary endings ('~었죠', '~습니다', '~겁니다') instead"
            )
        hanging_deyo_count = sum(
            1 for _, s in narrator_sents if re.search(r"(?:는데요|건데요|셈인데요)[.?!]?[\x22\x27”’]?$", s)
        )
        hanging_deyo_ratio = hanging_deyo_count / float(total_narr)
        if hanging_deyo_ratio > 0.025 or (total_narr >= 75 and hanging_deyo_count > 2):
            raise RuntimeError(
                f"PLAN Korean TTS hanging-intonation error: standalone '~는데요/~건데요' endings occupy {hanging_deyo_ratio * 100:.1f}% "
                f"({hanging_deyo_count}/{total_narr}) of narrator sentences (maximum allowed is 2.5% / <=2 sentences to prevent rising/hanging TTS prosody; "
                "convert to '~었죠', '~습니다', '~겁니다', or crisp short brakes)"
            )
        formal_ratio = pure_formal_count / float(total_narr)
        if formal_ratio > 0.78 or formal_ratio < 0.42:
            raise RuntimeError(
                f"PLAN Korean prosody monotony error: pure '~습니다/입니다' endings occupy {formal_ratio * 100:.1f}% "
                f"({pure_formal_count}/{total_narr}) of narrator sentences (target broadcast range is 42.0%–78.0%, ideal 58%–73%; weave organic '~었죠', questions, and crisp 2–5 word 체언 종결 brakes)"
            )
        if jyo_ratio > 0.22:
            raise RuntimeError(
                f"PLAN Korean prosody pendulum error: '~죠' endings occupy {jyo_ratio * 100:.1f}% "
                f"({jyo_count}/{total_narr}) of narrator sentences (maximum allowed is 22.0% to prevent mechanical '~습니다/~죠' alternation)"
            )
        if max_consec_formal >= 6:
            raise RuntimeError(
                f"PLAN Korean prosody monotony error near {max_consec_span}: {max_consec_formal} consecutive pure '~습니다/입니다' sentences "
                "(maximum allowed consecutive run is 5, ideal <=4; vary cadence naturally with '~었죠', questions, or crisp short brakes)"
            )
        if total_narr >= 75:
            if jyo_ratio < 0.06:
                raise RuntimeError(
                    f"PLAN Korean prosody flatness error: '~죠' endings are only {jyo_ratio * 100:.1f}% ({jyo_count}/{total_narr}, minimum 6.0%); "
                    "weave natural observational '~었죠 / ~였죠' landings so long-form narration does not sound flat"
                )
            noun_end_count = sum(
                1 for _, s in narrator_sents if not _FINITE_KO_PREDICATE_END_RE.search(s)
            )
            noun_end_ratio = noun_end_count / float(total_narr)
            if noun_end_ratio > 0.18:
                raise RuntimeError(
                    f"PLAN Korean noun-fragment flood error: verbless noun endings (체언 종결) occupy {noun_end_ratio * 100:.1f}% "
                    f"({noun_end_count}/{total_narr}) of narrator sentences (maximum allowed is 18.0%, ideal 5%–10%)"
                )
            if raw_script_text is not None or any(
                isinstance(it, dict) and it.get("is_standalone_paragraph") is not None for it in beats
            ):
                paras_to_check: list[list[str]] = []
                if raw_script_text is not None:
                    cur_p: list[str] = []
                    for raw_ln in raw_script_text.splitlines():
                        s_ln = raw_ln.strip()
                        if not s_ln or s_ln.startswith("#"):
                            if cur_p:
                                paras_to_check.append(cur_p)
                                cur_p = []
                        else:
                            cur_p.append(s_ln)
                    if cur_p:
                        paras_to_check.append(cur_p)
                else:
                    for it in beats:
                        if not isinstance(it, dict):
                            continue
                        txt_it = str(it.get("narration_text") or it.get("text") or "").strip()
                        if not txt_it:
                            continue
                        if it.get("is_standalone_paragraph") is True:
                            paras_to_check.append([txt_it])
                        else:
                            paras_to_check.append([txt_it, "context_sentence"])
                standalone_noun_p_indices: list[int] = []
                for p_i, p_lines in enumerate(paras_to_check):
                    if len(p_lines) != 1:
                        continue
                    p_sents = [
                        s_part.strip()
                        for s_part in _SENTENCE_SPLIT_RE.split(p_lines[0])
                        if s_part.strip() and any("\uac00" <= ch <= "\ud7a3" for ch in s_part)
                    ]
                    if len(p_sents) == 1 and not _FINITE_KO_PREDICATE_END_RE.search(p_sents[0]):
                        standalone_noun_p_indices.append(p_i)
                close_noun_p = any(
                    (standalone_noun_p_indices[k] - standalone_noun_p_indices[k - 1]) < 8
                    for k in range(1, len(standalone_noun_p_indices))
                )
                if len(standalone_noun_p_indices) > 4 or close_noun_p:
                    raise RuntimeError(
                        "PLAN Korean standalone_one_line_noun_crutch_excess error: "
                        f"standalone_one_line_noun_paragraphs={len(standalone_noun_p_indices)} "
                        "(max allowed <= 4 across episode and >= 8 paragraphs apart)"
                    )
            crisp_punch_count = sum(
                1
                for _, s in narrator_sents
                if len(re.sub(r"[\s\x22\x27\u201c\u201d\u2018\u2019,.?!\u2026]", "", s)) <= 16
            )
            crisp_punch_ratio = crisp_punch_count / float(total_narr)
            if crisp_punch_ratio < 0.05:
                raise RuntimeError(
                    f"PLAN Korean uniform-length monotony error: crisp short brake sentences (<=16 non-space chars, e.g. '단 육십 초.', '완벽한 증발.') "
                    f"are only {crisp_punch_ratio * 100:.1f}% ({crisp_punch_count}/{total_narr}); minimum required is 5.0% to break 40-50 char uniform walls"
                )
            geomnida_count = sum(
                1 for _, s in narrator_sents if re.search(r"(?:겁니다|셈입니다)[.?!]?[\x22\x27\u201d\u2019]?$", s)
            )
            geomnida_ratio = geomnida_count / float(total_narr)
            if geomnida_ratio > 0.14:
                raise RuntimeError(
                    f"PLAN Korean explanatory-copula repetition error: '~겁니다/~셈입니다' endings occupy {geomnida_ratio * 100:.1f}% "
                    f"({geomnida_count}/{total_narr}) of narrator sentences (maximum allowed is 14.0%; replace repetitive '~던 겁니다' with concrete active verbs)"
                )
            blotter_hits: list[str] = []
            ordinal_hits: list[str] = []
            micro_sec_hits: list[str] = []
            blotter_re = re.compile(
                r"(?:(?:스물|서른|마흔|쉰|예순|일흔|여든|아흔)[가-힣]{0,3}|\d{2})\s*(?:살|세)(?:의|이던|인)?\s+"
                r"(?:[가-힣]{1,6}\s+){1,2}(?:[가-힣]{2,4}|[가-힣]\s*씨|[가-힣]\s*사장)"
            )
            raw_native_re = re.compile(
                r"(?<![\d.,])([1-9]|1\d|20)\s*"
                r"(?:정(?!도|밀|보|부|식|확|기|거장|체)|개(?!월|소|국|년|인|편|\s*(?:성|도|시|군|현|구|국|부처|기관|은행|성급)(?![가-힣]))|발(?!생|견|표|사|전|자국)|자루|켤레|마리)"
                r"(?=(?:이|가|을|를|은|는|에|의|도|만|와|과|씩|뿐|이나|나|으로|로|이고|였|입)[가-힣]*|(?![가-힣]))"
            )
            artifact_jum_re = re.compile(
                r"(?:탄피|유류품|증거물|증거품|단서|흔적|혈흔|조각|총기|장물|유물)\s*(?:[1-9]|1\d|20)\s*점(?![가-힣])"
            )
            from .critic_loops import find_chinese_sye_traps, find_foreign_place_phonetic_drifts

            place_drifts = find_foreign_place_phonetic_drifts("\n".join(s for _, s in narrator_sents))
            mil_sik_re = re.compile(
                r"(?<!\d)(\d{2,3})\s*식(?=\s*(?:반자동|자동|군용|제식|권총|소총|기관총|기관단총|화기|무기|장비|총기|탄피|탄환|실탄)|(?:이|가|을|를|은|는|의|에|도|만|으로|로|과|와)(?![가-힣])|[,\s.?!]|$)"
                r"(?!\s*(?:사|당|품|구|물|민|량|수|탁|장|전))"
            )
            mil_unit_re = re.compile(r"(?<!\d)(\d{2,3})\s*(?:연대|사단|여단)(?!\s*(?:장학|세브란스|병원|대학교))")
            for bid, s in narrator_sents:
                for bad_p, canon_p in place_drifts.items():
                    if re.search(rf"(?<![가-힣]){re.escape(bad_p)}", s):
                        raise RuntimeError(
                            f"PLAN Korean proper-noun phonetic drift error in {bid}: '{bad_p}' conflicts with canonical '{canon_p}'; unify place/person spelling across the entire episode"
                        )
                m_alpha = re.search(r"[A-Za-z]+", s)
                if m_alpha:
                    raise RuntimeError(
                        f"PLAN Korean TTS mixed-alphanumeric error in {bid}: raw Latin characters '{m_alpha.group(0)}' found in Korean narration; "
                        "transliterate plates, grades, and acronyms into pure Hangul (e.g. '웨 에이알 공칠사칠 호', '에이급', '씨씨티비')"
                    )
                sye_traps = find_chinese_sye_traps(s)
                if sye_traps:
                    m_sye = sye_traps[0]
                    win_sye = s[max(0, m_sye.start() - 3) : min(len(s), m_sye.end() + 6)]
                    raise RuntimeError(
                        f"PLAN Korean TTS '셰' phonetic trap in {bid}: Chinese '셰' syllable in '{win_sye.strip()}' wobbles to '쉐/쉬/쇠'; "
                        "write '시에' instead ('시에런량', '시에윈', '시에쭝펀', '우시에위', '시에 씨')"
                    )
                m_mil = mil_sik_re.search(s) or mil_unit_re.search(s)
                if m_mil:
                    raise RuntimeError(
                        f"PLAN Korean TTS military code error in {bid}: '{m_mil.group(0)}' must be spelled in Hangul ('오륙식', '팔일식', '오사식', '백사십칠 연대')"
                    )
                m_zero_ho = re.search(r"(?<!\d)0\d{2,4}\s*호", s)
                if m_zero_ho:
                    raise RuntimeError(
                        f"PLAN Korean TTS leading-zero code error in {bid}: '{m_zero_ho.group(0)}' must be spelled digit-by-digit in Hangul (e.g. '공칠사칠 호', '공구오 호')"
                    )
                m_yeo = re.search(r"\d[\d,]*여\s*(?:만|억|위안|원|년|명)", s)
                if m_yeo:
                    raise RuntimeError(
                        f"PLAN Korean TTS numeral-yeo error in {bid}: '{m_yeo.group(0)}' must be written in Hangul (e.g. '백여만 위안', '십여 년')"
                    )
                m_zgeon = re.search(r"(?<![\d.,])0\s*건(?!물|설|조|강)", s)
                if m_zgeon:
                    raise RuntimeError(
                        f"PLAN Korean TTS '0건' phonetic trap in {bid}: raw '0건' is misread as '연건'; write '단 한 건도 없었습니다' or '영 건'"
                    )
                m_nat = raw_native_re.search(s) or artifact_jum_re.search(s)
                if m_nat:
                    raise RuntimeError(
                        f"PLAN Korean TTS native-counter digit error in {bid}: '{m_nat.group(0)}' leaves Arabic digits attached to a native-Korean counter; "
                        "write spaced Hangul ('서류 두 장', '열쇠 세 개', '여덟 개', '단서 아홉 점')"
                    )
                m_gore = re.search(
                    r"(?:토막\s*살인|토막\s*내|참수|시신\s*훼손|시체\s*훼손|사체\s*훼손|피투성이\s*시신|성폭행|강간|아동\s*학대)",
                    s,
                )
                if m_gore:
                    raise RuntimeError(
                        f"PLAN Korean Broadcast Green-Dollar violation in {bid}: '{m_gore.group(0)}' violates YouTube monetization safety; "
                        "refract into calm, indirect investigative/forensic broadcast prose"
                    )
                if blotter_re.search(s):
                    blotter_hits.append(bid)
                if re.search(r"(?:^|[\s,\x22\x27“‘])(?:첫째|둘째|셋째|첫\s*번째|두\s*번째|세\s*번째)(?:는|가|로|,)", s):
                    ordinal_hits.append(bid)
                if re.search(r"(?:0\.\d+\s*초|영점[가-힣]{1,4}\s*초)", s):
                    micro_sec_hits.append(bid)
            if isinstance(job, dict) and total_narr >= 80:
                _snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
                _ed = _snap.get("editorial_dna") if isinstance(_snap.get("editorial_dna"), dict) else {}
                _kp = _ed.get("korean_prose_and_grammar_rules") if isinstance(_ed.get("korean_prose_and_grammar_rules"), dict) else {}
                _prof_id = str(job.get("channel_profile_id") or _snap.get("id") or "").strip()
                if (
                    _ed.get("require_geodeunyo_cadence") is True
                    or _kp.get("require_geodeunyo_cadence") is True
                    or _prof_id in {"channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2"}
                ):
                    geodeunyo_cnt = sum(
                        1 for _, s in narrator_sents if re.search(r'거든요[.?!]?["\'\u201d\u2019]?$', s)
                    )
                    if geodeunyo_cnt < 3:
                        raise RuntimeError(
                            f"PLAN Korean spoken cadence error: '~거든요' endings appear only {geodeunyo_cnt} times across {total_narr} sentences "
                            "(minimum 3–8 required for this profile alongside '~었죠' and '~던 겁니다')"
                        )
            if len(blotter_hits) >= 3:
                raise RuntimeError(
                    f"PLAN Korean formulaic character-label error near {blotter_hits[:4]}: '[Age] + [Occupation] + [Name]' blotter introductions repeated {len(blotter_hits)} times"
                )
            if len(ordinal_hits) >= 3:
                raise RuntimeError(
                    f"PLAN Korean mechanical listicle error near {ordinal_hits[:4]}: '첫째는... 둘째는... 셋째는...' textbook enumeration is forbidden in documentary narration"
                )
            if len(micro_sec_hits) >= 3:
                raise RuntimeError(
                    f"PLAN Korean micro-stopwatch padding error near {micro_sec_hits[:4]}: repeated '0.05초/0.1초' sub-second figures undermine forensic realism"
                )
            ssi_subj_re = re.compile(r"[가-힣]{1,5}\s*씨(?:는|가|도)")
            for w_i in range(0, len(narrator_sents) - 6):
                win = narrator_sents[w_i : w_i + 7]
                if sum(1 for _, ws in win if ssi_subj_re.search(ws)) >= 5:
                    raise RuntimeError(
                        f"PLAN Korean action-scene subject repetition error near {win[0][0]}: >=5 sentences in a 7-sentence span repeat '... 씨는/씨가'; "
                        "shift subjects across physical scene details ('비상벨이', '잠금장치가', '차량 불빛이')"
                    )

            # Profile-Isolated Factual & Anti-AI Smell Gates (ONLY when `editorial_dna.profile_script_gates.enabled` is True on active profile)
            from .critic_loops import (
                _KO_AI_GWAYEON_RHETORICAL_RE,
                _KO_AI_SPOONFED_EXCLAMATION_RE,
                _KO_POST2024_HERITAGE_RULES,
                _KO_PRE2024_HISTORICAL_LINE_RE,
                audit_korean_chronology_consistency,
                resolve_profile_script_gates,
                script_has_post2024_modern_anchor,
                verify_and_fix_korean_char_count_claims,
            )

            prof_gates_q = resolve_profile_script_gates(job)
            if prof_gates_q.get("enabled") is True:
                full_ko_blob = "\n".join(s for _, s in sentences)
                is_modern_post2024 = bool(
                    prof_gates_q.get("enforce_post2024_korean_heritage_names") is True
                    and script_has_post2024_modern_anchor(full_ko_blob)
                )
                check_char_math = bool(prof_gates_q.get("verify_korean_char_count_claims") is True)
                for bid, s in sentences:
                    if check_char_math:
                        _, mm_claims = verify_and_fix_korean_char_count_claims(s)
                        if mm_claims:
                            mm0 = mm_claims[0]
                            raise RuntimeError(
                                f"PLAN Korean character-count math error in {bid}: '{mm0['phrase']}' has {mm0['actual']} Hangul syllables "
                                f"('{mm0['fixed_token']}'), NOT '{mm0['claimed_token']}'"
                            )
                    if is_modern_post2024 and not _KO_PRE2024_HISTORICAL_LINE_RE.search(s):
                        for h_pat, h_repl in _KO_POST2024_HERITAGE_RULES:
                            m_h = h_pat.search(s)
                            if m_h:
                                raise RuntimeError(
                                    f"PLAN Korean post-2024 institutional naming error in {bid}: outdated '{m_h.group(0)}' in modern timeline; "
                                    f"use official '{h_repl}' (effective May 17, 2024)"
                                )

                if prof_gates_q.get("enforce_chronology_year_span_math") is True:
                    chrono_res = audit_korean_chronology_consistency(
                        [(i + 1, s) for i, (_, s) in enumerate(sentences)]
                    )
                    if chrono_res.get("contradictions"):
                        c0 = chrono_res["contradictions"][0]
                        raise RuntimeError(
                            f"PLAN Korean chronology math contradiction: present year {c0['present_year']} vs flashback year {c0['past_year']} "
                            f"equals {c0['expected_span']}년, contradicting '{c0['claimed_span']}년' ({c0['excerpt']})"
                        )

                spoonfed_hits = [bid for bid, s in narrator_sents if _KO_AI_SPOONFED_EXCLAMATION_RE.search(s)]
                gwayeon_hits = [bid for bid, s in narrator_sents if _KO_AI_GWAYEON_RHETORICAL_RE.search(s)]
                max_gwayeon_gate = 5 if total_narr > 180 else 4
                if len(spoonfed_hits) >= 3 or len(gwayeon_hits) > max_gwayeon_gate:
                    raise RuntimeError(
                        f"PLAN Korean AI spoon-fed commentary excess: exclamation judgements={len(spoonfed_hits)} (near {spoonfed_hits[:4]}), "
                        f"'과연 ...?' rhetorical commentary={len(gwayeon_hits)} (near {gwayeon_hits[:5]}, max {max_gwayeon_gate}); "
                        "cut narrator emotional spoon-feeding and let character actions speak"
                    )

    short_brake_count = sum(
        1
        for _, s in sentences
        if len(re.sub(r'[\s"\'\u201c\u201d\u2018\u2019,.?!\u2026]', "", s)) <= 24
    )
    short_ratio = short_brake_count / float(len(sentences))
    if short_ratio < 0.10:
        raise RuntimeError(
            f"PLAN Korean sentence-length uniformity error: short brake sentences (<=24 non-space chars) are only "
            f"{short_ratio * 100:.1f}% ({short_brake_count}/{len(sentences)}); minimum required is 10.0% to prevent uniform 40-50 char pacing"
        )

_BANNED_KO_TIME_REWIND_RE = re.compile(
    r"(?:시계를|시침을)\s*[^.?!]{1,45}(?:되돌려|돌려)"
    r"|(?:시간을)\s*[^.?!]{1,45}(?:되돌려|돌려\s*봅|돌려보)"
    r"|(?:시간은)\s*[^.?!]{1,45}거슬러\s*올라"
)
_BANNED_KO_STOCK_MIDROLL_CTA_RE = re.compile(
    r"집요한\s*실제\s*과학수사\s*기록을\s*함께\s*추적"
    r"|실제\s*사건\s*추적\s*기록을\s*놓치지\s*않으시려면"
)
_BANNED_KO_STOCK_MORAL_RE = re.compile(
    r"완전범죄(?:는|가|란)\s*(?:결코\s*|절대\s*)?(?:존재할\s*수\s*없|될\s*수\s*없|성립할\s*수\s*없|존재하지\s*않)"
)
_BANNED_KO_STOCK_OUTRO_SRT_RE = re.compile(
    r"매주\s*실제\s*수사\s*기록과"
    r"|지금\s*화면에\s*표시되고\s*있습니다"
    r"|(?:지금\s*)?(?:바로\s*)?화면에\s*(?:나타나는|나타난|준비된|준비돼|띄워진)\s*(?:다음\s*)?(?:사건\s*파일|수사\s*기록|영상|있습)"
    r"|오늘\s*사건처럼\s*평범한\s*(?:일상\s*속에서|이웃의\s*얼굴)"
    r"|(?:오늘도\s*)?(?:긴\s*시간\s*)?끝까지\s*(?:함께해\s*주신\s*여러분\s*,?\s*)?(?:시청해|함께해)\s*주셔서\s*(?:진심으로\s*)?(?:감사합니다|고맙습니다)"
    r"|다음\s*시간에도\s+[^.?!]{0,50}찾아뵙겠습니다"
)
_BANNED_KO_FORMULAIC_CTA_SYNTAX_RE = re.compile(
    r"(?:하시려면|싶으시다면|궁금하시다면|응원하신다면|놓치지\s*않으시려면|놓치지\s*않도록|받아\s*보시려면|추적하고\s*계신다면|파헤치기\s*위해|지키기\s*위해|추적할\s*수\s*있도록)\s*,?\s*[^.?!]{0,45}(?:구독|좋아요|알림)"
    r"|(?:구독과\s*(?:좋아요|알림\s*설정|알림)|좋아요와\s*구독)[^.?!]{0,35}(?:눌러|부탁|바랍니다|주십시오|주시죠|주세요)"
    r"|(?:지금\s*)?(?:채널\s*)?구독(?:을|과)[^.?!]{0,20}눌러"
)
_KO_EXPLICIT_BUTTON_CTA_RE = re.compile(
    r"(?<!신문\s)(?<!잡지\s)(?<!정기\s)구독"
    r"|알림\s*설정"
    r"|좋아요(?:를|도|로|\s*버튼|\s*한\s*번)"
)
_KO_VIEWER_CTA_SIGNAL_RE = re.compile(
    r"(?<!신문\s)(?<!잡지\s)(?<!정기\s)구독"
    r"|알림\s*설정"
    r"|좋아요(?:를|도|로|\s*버튼|\s*한\s*번)"
    r"|댓글(?:로|에|란에)[^.?!]{0,35}(?:남겨|나눠|적어|들려|공유)"
    r"|(?:저희\s*채널|채널\s*보관함|이\s*채널)"
    r"|시청해\s*주셔서"
    r"|다음\s*(?:기록에서도|이야기에서도|시간에도)[^.?!]{0,35}(?:찾아오|짚어|만나|전해)"
)


def _hangul_ngrams(text: str, n: int = 6) -> set[str]:
    cleaned = re.sub(r"[^가-힣]", "", text or "")
    if len(cleaned) < n:
        return set()
    return {cleaned[i : i + n] for i in range(len(cleaned) - n + 1)}


def _hangul_6grams(text: str) -> set[str]:
    return _hangul_ngrams(text, 6)


def validate_korean_anti_template_diversity(
    beats: list[dict[str, Any]],
    *,
    workspace: Path | None = None,
    job: dict[str, Any] | None = None,
    recent_scripts: list[str] | None = None,
    cta_rhetorical_form: str | None = None,
    max_shared_6grams: int = 14,
    max_shared_cta_5grams: int = 4,
) -> dict[str, Any]:
    """Enforce zero-repeat story-driven CTA, syntactic CTA diversity, and anti-template SRT originality."""
    sentences: list[tuple[str, str]] = []
    cta_sentences: list[tuple[int, str, str]] = []
    cta_beat_indices: list[tuple[int, str]] = []
    explicit_button_hits: list[tuple[int, str, str]] = []

    resolved_cta_form = cta_rhetorical_form
    if resolved_cta_form is None and isinstance(job, dict) and job:
        try:
            from .prompts import select_episode_narrative_variant

            resolved_cta_form = select_episode_narrative_variant(job).get("cta_rhetorical_form")
        except Exception:
            resolved_cta_form = None

    total_beats = len(beats)
    _snap_cta = (job or {}).get("channel_profile_snapshot") if isinstance((job or {}).get("channel_profile_snapshot"), dict) else {}
    _ed_cta = _snap_cta.get("editorial_dna") if isinstance(_snap_cta.get("editorial_dna"), dict) else {}
    _prof_id_cta = str((job or {}).get("channel_profile_id") or _snap_cta.get("id") or "").strip()
    _allow_dual_sub_cta = bool(
        _prof_id_cta in {
            "channel-kr-financial-fugitive-director-v2",
            "channel-kr-truecrime-director-v2",
            "channel-e544a64b7c",
        }
        or _ed_cta.get("outro_mode") == "standalone_case_closure"
        or _ed_cta.get("allow_dual_subscriber_cta") is True
    )
    early_hook_cutoff = 2 if _allow_dual_sub_cta else (max(2, int(total_beats * 0.15)) if total_beats >= 12 else 0)
    closing_zone_start = int(total_beats * 0.85) if total_beats >= 15 else total_beats

    for idx, item in enumerate(beats):
        if not isinstance(item, dict):
            continue
        bid = str(item.get("beat_id") or f"B{idx + 1:03d}")
        narration = str(item.get("narration_text") or item.get("text") or "").strip()
        purpose = str(item.get("purpose") or "").strip().lower()

        if purpose in {"mid_roll_soft_cta", "end_screen_cta_bridge"}:
            raise RuntimeError(
                f"PLAN Zero-Repeat CTA error in {bid}: legacy mechanical CTA purpose='{purpose}' is forbidden; "
                "CTA must flow organically inside story narration without fixed pop-up or End-Screen badge slots"
            )

        if not narration:
            continue

        m_rewind = _BANNED_KO_TIME_REWIND_RE.search(narration)
        if m_rewind:
            raise RuntimeError(
                f"PLAN Anti-Template SRT error in {bid}: stock flashback transition '{m_rewind.group(0)}' is forbidden; "
                "cut directly into the date/place/action without '시계를/시간을 ... 되돌려 봅니다'"
            )

        m_mid_cliche = _BANNED_KO_STOCK_MIDROLL_CTA_RE.search(narration)
        if m_mid_cliche:
            raise RuntimeError(
                f"PLAN Anti-Template SRT error in {bid}: stock mid-roll CTA phrase '{m_mid_cliche.group(0)}' is forbidden"
            )

        m_moral = _BANNED_KO_STOCK_MORAL_RE.search(narration)
        if m_moral:
            raise RuntimeError(
                f"PLAN Anti-Template SRT error in {bid}: stock moralizing cliché '{m_moral.group(0)}' is forbidden; "
                "close with case-specific human aftermath, forensic irony, or institutional reality instead"
            )

        m_outro = _BANNED_KO_STOCK_OUTRO_SRT_RE.search(narration)
        if m_outro:
            raise RuntimeError(
                f"PLAN Anti-Template SRT error in {bid}: copy-pasted outro/end-screen phrase '{m_outro.group(0)}' is forbidden; "
                "write the final 5 lines freshly from scratch for this episode"
            )

        if not _allow_dual_sub_cta:
            m_formula_cta = _BANNED_KO_FORMULAIC_CTA_SYNTAX_RE.search(narration)
            if m_formula_cta:
                raise RuntimeError(
                    f"PLAN Zero-Repeat CTA syntax error in {bid}: formulaic conditional/imperative CTA skeleton "
                    f"'{m_formula_cta.group(0)}' is forbidden; craft a fresh, story-woven sentence structure instead"
                )

        beat_has_cta = False
        for raw_sent in _SENTENCE_SPLIT_RE.split(narration):
            s = raw_sent.strip()
            if not s or not any("\uac00" <= ch <= "\ud7a3" for ch in s):
                continue
            sentences.append((bid, s))
            if _KO_VIEWER_CTA_SIGNAL_RE.search(s):
                beat_has_cta = True
                cta_sentences.append((idx, bid, s))
            if _KO_EXPLICIT_BUTTON_CTA_RE.search(s):
                explicit_button_hits.append((idx, bid, s))

        if beat_has_cta:
            if total_beats >= 12 and idx < early_hook_cutoff:
                raise RuntimeError(
                    f"PLAN Zero-Repeat CTA placement error in {bid}: viewer CTA is forbidden in the opening hook window"
                )
            cta_beat_indices.append((idx, bid))

    max_allowed_cta = 2 if _allow_dual_sub_cta else 1
    if len(cta_beat_indices) > max_allowed_cta or len(explicit_button_hits) > max_allowed_cta:
        dup_bids = ", ".join(b for _, b in cta_beat_indices) or ", ".join(b for _, b, _ in explicit_button_hits)
        raise RuntimeError(
            f"PLAN Zero-Repeat CTA error: CTA/viewer solicitation appears multiple times in the same script ({dup_bids}); "
            "place at most 1 natural context-matched CTA across the entire episode"
        )

    if resolved_cta_form == "pure_story_zero_explicit_cta" and (cta_beat_indices or explicit_button_hits):
        first_bid = (cta_beat_indices[0][1] if cta_beat_indices else explicit_button_hits[0][1])
        raise RuntimeError(
            f"PLAN Zero-Repeat CTA role error in {first_bid}: episode uses cta_rhetorical_form='pure_story_zero_explicit_cta' "
            "(100% pure broadcast storytelling with 0 explicit CTA), so viewer solicitation must be omitted"
        )

    if resolved_cta_form == "interrogative_viewer_perspective" and explicit_button_hits:
        first_bid = explicit_button_hits[0][1]
        raise RuntimeError(
            f"PLAN Zero-Repeat CTA role error in {first_bid}: cta_rhetorical_form='interrogative_viewer_perspective' "
            "must pose an open case-driven question without explicit '구독/좋아요/알림 설정' button calls"
        )

    if (
        resolved_cta_form == "story_breath_single_companion_aside"
        and total_beats >= 15
        and any(idx >= closing_zone_start for idx, _ in cta_beat_indices)
    ):
        closing_bid = next(b for idx, b in cta_beat_indices if idx >= closing_zone_start)
        raise RuntimeError(
            f"PLAN Zero-Repeat CTA role error in {closing_bid}: cta_rhetorical_form='story_breath_single_companion_aside' "
            "places its single companion breath inside a mid-story passage of time and keeps the ending 100% CTA-free"
        )

    reference_texts: list[tuple[str, str]] = []
    if recent_scripts is not None:
        for r_idx, txt in enumerate(recent_scripts):
            if str(txt or "").strip():
                reference_texts.append((f"recent_{r_idx + 1}", str(txt)))
    elif workspace is not None and workspace.parent.name == "workspaces" and workspace.parent.is_dir():
        active_prof_id = str(
            (job or {}).get("channel_profile_id")
            or (((job or {}).get("channel_profile_snapshot") or {}).get("id") if isinstance((job or {}).get("channel_profile_snapshot"), dict) else "")
            or ""
        ).strip()
        try:
            resolved_ws = workspace.resolve()
        except Exception:
            resolved_ws = workspace
        for cand in sorted((p for p in workspace.parent.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True):
            if len(reference_texts) >= 6:
                break
            try:
                if cand.resolve() == resolved_ws:
                    continue
            except Exception:
                if cand.name == workspace.name:
                    continue
            if active_prof_id:
                inp_file = cand / "input.json"
                cand_prof_id = ""
                if inp_file.is_file():
                    try:
                        inp_data = json.loads(inp_file.read_text(encoding="utf-8", errors="ignore"))
                        if isinstance(inp_data, dict):
                            cand_prof_id = str(
                                inp_data.get("channel_profile_id")
                                or ((inp_data.get("channel_profile_snapshot") or {}).get("id") if isinstance(inp_data.get("channel_profile_snapshot"), dict) else "")
                                or ""
                            ).strip()
                    except Exception:
                        cand_prof_id = ""
                if cand_prof_id != active_prof_id:
                    continue
            s_file = cand / "script.md"
            if not s_file.is_file():
                continue
            try:
                raw_txt = s_file.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception:
                continue
            if len(raw_txt) >= 400 and re.search(r"[\uac00-\ud7a3]", raw_txt):
                reference_texts.append((cand.name, raw_txt))

    if reference_texts:
        for ref_label, ref_raw in reference_texts:
            ref_lines = [
                ln.strip()
                for ln in ref_raw.splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]
            ref_sents: list[str] = []
            ref_cta_sents: list[str] = []
            for ln in ref_lines:
                for rs in _SENTENCE_SPLIT_RE.split(ln):
                    clean_rs = rs.strip()
                    if clean_rs and any("\uac00" <= ch <= "\ud7a3" for ch in clean_rs):
                        ref_sents.append(clean_rs)
                        if (
                            _KO_VIEWER_CTA_SIGNAL_RE.search(clean_rs)
                            or _BANNED_KO_FORMULAIC_CTA_SYNTAX_RE.search(clean_rs)
                            or _BANNED_KO_STOCK_OUTRO_SRT_RE.search(clean_rs)
                        ):
                            ref_cta_sents.append(clean_rs)

            if cta_sentences and ref_cta_sents:
                for _, cur_bid, cur_cta in cta_sentences:
                    cur_5g = _hangul_ngrams(cur_cta, 5)
                    if not cur_5g:
                        continue
                    for prior_cta in ref_cta_sents:
                        shared_cta_5g = cur_5g & _hangul_ngrams(prior_cta, 5)
                        if len(shared_cta_5g) > max_shared_cta_5grams:
                            sample_cta = ", ".join(sorted(shared_cta_5g)[:4])
                            raise RuntimeError(
                                f"PLAN Zero-Repeat CTA cross-episode error in {cur_bid}: CTA sentence shares "
                                f"{len(shared_cta_5g)} Korean 5-grams (max {max_shared_cta_5grams}) with a prior CTA "
                                f"in '{ref_label}' (e.g. {sample_cta}); never repeat CTA wording or structure across episodes"
                            )

            if len(sentences) >= 12 and len(ref_sents) >= 10:
                cur_head_6g = _hangul_6grams(" ".join(s for _, s in sentences[:5]))
                cur_tail_6g = _hangul_6grams(" ".join(s for _, s in sentences[-5:]))
                ref_tail_6g = _hangul_6grams(" ".join(ref_sents[-5:]))
                shared_tail = cur_tail_6g & ref_tail_6g
                if len(shared_tail) > max_shared_6grams:
                    sample_overlap = ", ".join(sorted(shared_tail)[:4])
                    raise RuntimeError(
                        f"PLAN Anti-Template SRT clone error: final 5 sentences share {len(shared_tail)} Korean 6-grams "
                        f"(max {max_shared_6grams}) with recent episode '{ref_label}' (e.g. {sample_overlap}); "
                        "rewrite the ending and last 5 lines from scratch"
                    )
                ref_head_6g = _hangul_6grams(" ".join(ref_sents[:5]))
                shared_head = cur_head_6g & ref_head_6g
                if len(shared_head) > max_shared_6grams:
                    sample_overlap = ", ".join(sorted(shared_head)[:4])
                    raise RuntimeError(
                        f"PLAN Anti-Template SRT clone error: opening 5 sentences share {len(shared_head)} Korean 6-grams "
                        f"(max {max_shared_6grams}) with recent episode '{ref_label}' (e.g. {sample_overlap}); "
                        "rotate the opening structure and rewrite fresh lines"
                    )

    return {
        "status": "PASSED",
        "sentences_checked": len(sentences),
        "cta_count": len(cta_beat_indices),
        "cta_rhetorical_form": resolved_cta_form or "unspecified",
        "recent_episodes_compared": len(reference_texts),
    }


def evaluate_ypp_framing_wrapper_cap(
    beats: list[dict[str, Any]],
    max_wrapper_ratio: float = 0.55,
) -> dict[str, Any]:
    """YPP Quality Gate: Block single framing-wrapper monotony (>55%)."""
    if not beats:
        raise ValueError("Cannot evaluate framing wrapper cap on empty beats")
    wrapper_counts = collections.Counter(
        b.get("framingMode")
        or b.get("framing_mode")
        or b.get("archetype")
        or b.get("visual_wrapper")
        or b.get("scene_archetype")
        or b.get("visual_route")
        or "unspecified"
        for b in beats
    )
    total_beats = len(beats)
    dominant_wrapper, count = wrapper_counts.most_common(1)[0]
    ratio = count / total_beats
    if ratio > max_wrapper_ratio:
        raise RuntimeError(
            f"YPP Quality Gate Failure: Single framing wrapper exceeds {max_wrapper_ratio * 100:.1f}% threshold "
            f"('{dominant_wrapper}' used in {count}/{total_beats} beats, {ratio * 100:.2f}%)"
        )
    return {
        "status": "PASSED",
        "dominant_wrapper": dominant_wrapper,
        "wrapper_count": count,
        "total_beats": total_beats,
        "dominance_ratio": round(ratio, 4),
    }


def evaluate_ypp_motion_floor(
    beats: list[dict[str, Any]],
    min_motion_ratio: float = 0.35,
) -> dict[str, Any]:
    """YPP Quality Gate: Block static-still slideshow output falling below motion floor (100% stills rejected)."""
    if not beats:
        raise ValueError("Cannot evaluate motion floor on empty beats")
    motion_kinds = {
        "sourced_video", "video", "motion_dossier", "satellite_map",
        "gis_satellite_flight", "remotion_camera_move", "annotated_footage",
        "REAL_FTG", "VOX", "CINEMA_TEXT", "cinema_text", "vox_motion", "real_footage",
    }
    motion_beats = sum(
        1 for b in beats
        if (b.get("kind") in motion_kinds)
        or (b.get("visual_type") in motion_kinds)
        or (b.get("visualType") in motion_kinds)
        or (b.get("media_type") in motion_kinds)
        or b.get("has_motion_override")
        or (b.get("camera_mode") and b.get("camera_mode") != "static_hold")
        or (b.get("cameraMotion") and b.get("cameraMotion") != "static_hold")
    )
    total_beats = len(beats)
    motion_ratio = motion_beats / total_beats
    if motion_ratio < min_motion_ratio or motion_beats == 0:
        raise RuntimeError(
            f"YPP Quality Gate Failure: Video is a static-still slideshow violating motion floor "
            f"(motion beats: {motion_beats}/{total_beats}, motion ratio: {motion_ratio * 100:.2f}% < {min_motion_ratio * 100:.1f}%)"
        )
    return {
        "status": "PASSED",
        "motion_beats": motion_beats,
        "total_beats": total_beats,
        "motion_ratio": round(motion_ratio, 4),
    }


def evaluate_ypp_visual_role_mix(
    edit_manifest: dict[str, Any],
    *,
    min_real_footage_ratio: float = 0.45,
    max_vox_ratio: float | None = None,
    max_ai_reconstruction_ratio: float = 0.28,
    max_ai_ratio: float | None = None,
    max_cinema_text_ratio: float = 0.12,
    semantic_verified_routing: bool = False,
    workspace: Path | None = None,
    remotion_job_dir: Path | None = None,
) -> dict[str, Any]:
    """Enforce profile visual-role DNA on edit_manifest (and physical .mp4 presence when paths are given) so True Crime cuts cannot starve real footage or flood repetitive VOX/AI."""
    if max_ai_ratio is not None:
        max_ai_reconstruction_ratio = float(max_ai_ratio)
    sem_verified = bool(
        semantic_verified_routing
        or edit_manifest.get("semantic_verified_footage_routing")
        or edit_manifest.get("semantic_verified_routing")
    ) and int(edit_manifest.get("boilerplate_or_filler_footage_count") or 0) == 0
    if sem_verified:
        min_real_footage_ratio = min(float(min_real_footage_ratio), 0.38)
        if max_vox_ratio is not None:
            max_vox_ratio = max(float(max_vox_ratio), 0.35)
        max_ai_reconstruction_ratio = max(float(max_ai_reconstruction_ratio), 0.28)

    rows = edit_manifest.get("beats") or edit_manifest.get("timeline") or []
    rows = [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
    total = int(edit_manifest.get("total_beats") or len(rows) or 0)
    if total <= 0:
        return {"status": "SKIPPED", "reason": "no_total_beats"}

    if (
        edit_manifest.get("real_footage_beats_count") is None
        and rows
    ):
        ftg = sum(
            1
            for r in rows
            if str(r.get("visualRole") or r.get("visual_role") or r.get("role") or "").upper() in {"REAL_FTG", "REAL_FOOTAGE", "FOOTAGE"}
            or str(r.get("imageFile") or r.get("asset_id") or r.get("public_file") or "").lower().endswith(".mp4")
        )
        vox = sum(
            1
            for r in rows
            if str(r.get("visualRole") or r.get("visual_role") or r.get("role") or "").upper() in {"VOX", "VOX_NEWSROOM", "VOX_25D"}
            or bool(r.get("voxSceneId") or r.get("vox_scene_id"))
        )
        ct = sum(
            1
            for r in rows
            if str(r.get("visualRole") or r.get("visual_role") or r.get("role") or "").upper() in {"CINEMA_TEXT", "VOX_MOTION_TEXT", "MOTION_TEXT"}
            or bool(r.get("cinemaTextId") or r.get("cinema_text_id"))
        )
        ai = sum(
            1
            for r in rows
            if str(r.get("visualRole") or r.get("visual_role") or r.get("role") or "").upper() in {"AI_4D", "AI_MASCOT", "AI_VISUAL", "AI"}
        )
    else:
        ftg = int(edit_manifest.get("real_footage_beats_count") or 0)
        vox = int(edit_manifest.get("vox_beats_count") or 0)
        ai = int(edit_manifest.get("ai_reconstruction_beats_count") or 0)
        ct = int(edit_manifest.get("cinema_text_beats_count") or 0)

    # Anti-spoof check: verify physical .mp4 video clips exist on disk when workspace/remotion_job_dir is provided
    if ftg > 0 and rows and (workspace is not None or remotion_job_dir is not None):
        mp4_rows = [
            r for r in rows
            if str(r.get("imageFile") or r.get("public_file") or r.get("asset_path") or "").lower().endswith(".mp4")
        ]
        if mp4_rows:
            verified_mp4_rows = 0
            for r in mp4_rows:
                rel = str(r.get("imageFile") or r.get("public_file") or r.get("asset_path") or "").strip()
                candidates: list[Path] = []
                if remotion_job_dir is not None:
                    # rel may look like 'jobs/<id>/footage/S_F001.mp4' or 'footage/S_F001.mp4'
                    sub_rel = re.sub(r"^jobs/[^/]+/", "", rel.replace("\\", "/"))
                    candidates.append(remotion_job_dir / sub_rel)
                    candidates.append(remotion_job_dir.parent.parent / rel)
                if workspace is not None:
                    candidates.append(workspace / rel)
                    candidates.append(workspace / "media" / "edit_footage" / Path(rel).name)
                    candidates.append(workspace / "media" / "footage" / Path(rel).name)
                if any(p.is_file() and p.stat().st_size > 4096 for p in candidates):
                    verified_mp4_rows += 1
            ftg = min(ftg, verified_mp4_rows)

    # Anti-filler check: block generic nature/waterfall B-roll padding on court/hospital/interrogation beats
    for r in rows:
        role_u = str(r.get("visualRole") or r.get("visual_role") or r.get("role") or "").upper()
        if role_u in {"REAL_FTG", "REAL_FOOTAGE", "FOOTAGE"}:
            obs_u = str(r.get("observed_content") or r.get("source_video") or r.get("imageFile") or "")
            v_u = str(r.get("narration_text") or r.get("voice_text") or "")
            if (
                re.search(r"(폭포수|폭포\s*전경|계곡\s*물줄기|단순\s*산림\s*풍경|자연\s*풍경\s*인서트|waterfall|f27_raw)", obs_u, re.IGNORECASE)
                and re.search(r"(법원|법정|재판|판결|사형|선고|중환자실|수술실|병원|부검|심문|취조|구치소|교도소|감옥)", v_u)
            ):
                raise RuntimeError(
                    f"Role DNA Violation: Beat {r.get('beat_id') or r.get('beatId')} uses generic nature/waterfall B-roll filler "
                    f"('{obs_u[:45]}') on an institutional/court/hospital sentence ('{v_u[:50]}'). Route to bespoke VOX (<Desk>) instead of padding B-roll!"
                )

    ftg_ratio = ftg / total
    vox_ratio = vox / total
    ai_ratio = ai / total
    ct_ratio = ct / total

    if ftg_ratio < min_real_footage_ratio:
        raise RuntimeError(
            f"Role DNA Violation: Real footage ratio is {ftg}/{total} ({ftg_ratio * 100:.1f}%), "
            f"below required minimum {min_real_footage_ratio * 100:.1f}%"
        )
    if max_vox_ratio is not None and vox_ratio > max_vox_ratio:
        raise RuntimeError(
            f"Role DNA Violation: VOX scene ratio is {vox}/{total} ({vox_ratio * 100:.1f}%), "
            f"exceeding maximum cap {max_vox_ratio * 100:.1f}% (curate >=50% authentic case footage instead of over-filling VOX)"
        )
    if ai_ratio > max_ai_reconstruction_ratio:
        raise RuntimeError(
            f"Role DNA Violation: AI reconstruction still ratio is {ai}/{total} ({ai_ratio * 100:.1f}%), "
            f"exceeding maximum cap {max_ai_reconstruction_ratio * 100:.1f}%"
        )
    if ct_ratio > max_cinema_text_ratio:
        raise RuntimeError(
            f"Role DNA Violation: Situational CINEMA_TEXT ratio is {ct}/{total} ({ct_ratio * 100:.1f}%), "
            f"exceeding punctuation cap {max_cinema_text_ratio * 100:.1f}%"
        )
    return {
        "status": "PASSED",
        "passed": True,
        "total_beats": total,
        "real_footage_ratio": round(ftg_ratio, 4),
        "vox_ratio": round(vox_ratio, 4),
        "cinema_text_ratio": round(ct_ratio, 4),
        "ai_reconstruction_ratio": round(ai_ratio, 4),
    }


def evaluate_ypp_bgm_anti_repetition(
    channel_profile_id: str,
    selected_tracks: list[str],
    bgm_history_path: Path | None = None,
) -> dict[str, Any]:
    """YPP Quality Gate: Reject duplicate BGM set repetition against bgm_usage_history.json."""
    if not selected_tracks:
        raise ValueError("selected_tracks must not be empty")
    if bgm_history_path is None:
        bgm_history_path = Path(__file__).resolve().parents[1] / "data" / "bgm_usage_history.json"
    if not bgm_history_path.exists():
        return {"status": "PASSED", "reason": "no_history_file"}

    history = json.loads(bgm_history_path.read_text(encoding="utf-8"))
    episodes = history.get("episodes", {})
    selected_set = set(selected_tracks)

    for ep_id, ep_data in episodes.items():
        if ep_data.get("channel_profile_id") == channel_profile_id:
            prior_tracks = ep_data.get("tracks_used", [])
            prior_set = set(prior_tracks)
            if prior_set and selected_set == prior_set:
                raise RuntimeError(
                    f"YPP Quality Gate Failure: Duplicate BGM set detected against bgm_usage_history.json "
                    f"(matches episode {ep_id} exactly with {len(selected_set)} identical tracks)"
                )

    return {"status": "PASSED", "tracks_count": len(selected_tracks)}


def evaluate_ypp_outro_audio_tail(
    outro_tail_sec: float,
    min_tail_sec: float = 3.5,
    max_tail_sec: float = 4.5,
) -> dict[str, Any]:
    """YPP Quality Gate: Reject abrupt endings missing a 3.5-4.5s audio fade-out tail."""
    if outro_tail_sec < min_tail_sec:
        raise RuntimeError(
            f"YPP Quality Gate Failure: Missing 3.5-4.5s outro audio fade tail "
            f"(provided {outro_tail_sec:.2f}s < minimum {min_tail_sec:.2f}s)"
        )
    return {
        "status": "PASSED",
        "outro_tail_sec": round(outro_tail_sec, 2),
        "in_ideal_range": min_tail_sec <= outro_tail_sec <= max_tail_sec,
    }


def evaluate_korean_grammar_gate(
    beats: list[dict[str, Any]],
    language: str,
) -> dict[str, Any]:
    """Language-Guarded Grammar Gate: Korean grammar checks run exclusively on Korean profiles."""
    if (language or "").strip().lower() != "ko":
        return {"status": "SKIPPED", "language": language, "reason": "non_korean_profile"}

    validate_korean_script_grammar_integrity(beats, job=job)
    return {"status": "PASSED", "language": "ko"}


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
        _seo_title_policy_re = re.compile(
            r"(?:생명을\s*앗아|목숨을\s*앗아|운명을\s*앗아|생명을\s*빼앗|연쇄살인사건|살인마|살인사건|살해|시신|시체|사체|백골|토막|참수|피투성이|혈흔|총살|사형|자살|극단적\s*선택|성폭행|강간|아동\s*학대|고문|엽기|đoạt\s+mạng|tước\s+đoạt\s+(?:\d+\s+|hàng\s+loạt\s+|nhiều\s+)?sinh\s+mạng|sát\s+hại|giết\s+người|sát\s+nhân|thi\s+thể|xác\s+chết|hài\s+cốt)",
            re.IGNORECASE,
        )
        rec_t_str = str(package.get("recommended_title") or "").strip()
        m_pol_t = _seo_title_policy_re.search(rec_t_str)
        if m_pol_t:
            raise RuntimeError(
                f"SEO recommended_title violates YouTube Policy & Green-Dollar Monetization Guard (15/07/2025–present): "
                f"found '{m_pol_t.group(0)}' in '{rec_t_str}'. Use 100% clean investigative hooks ('공안부 A급 수배범', '1급 수배범', '특급 미제사건', '두 얼굴', '사라진 흔적') with 0% life-taking/fatal-violence phrases."
            )
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
        # Clean 2-layer architecture: overlay_text is rendered programmatically by documentary/thumbnail_studio.py
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
        # Ensure Thumbnail Studio Engine (thumbnail_design.json + rendered JPGs) is always synced
        if not isinstance(package.get("reference_analysis"), dict):
            raise RuntimeError("SEO package requires reference_analysis")

        _snap_q = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
        _tdna_q = job.get("thumbnail_dna") or _snap_q.get("thumbnail_dna") or {}
        _tdna_q = _tdna_q if isinstance(_tdna_q, dict) else {}
        _is_teukgeup_q = (
            str(_tdna_q.get("style_preset") or "") in ("teukgeup_archival_polaroid", "forensic_noir", "forensic_noir_director_v2")
            or str(job.get("channel_profile_id") or "") in ("channel-e544a64b7c", "channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2")
        )
        if _is_teukgeup_q:
            design_file = workspace / "thumbnail_design.json"
            thumb_jpg = workspace / "thumbnail.jpg"
            if not design_file.is_file() or not thumb_jpg.is_file():
                raise RuntimeError("SEO requires thumbnail_design.json and rendered thumbnail.jpg")
            design_q = _read_json(design_file)
            variants_q = design_q.get("variants") if isinstance(design_q.get("variants"), list) else []
            if not variants_q:
                raise RuntimeError("thumbnail_design.json requires non-empty variants")
            active_vid_q = str(design_q.get("active_variant_id") or "v1")
            active_var_q = next((v for v in variants_q if isinstance(v, dict) and str(v.get("id")) == active_vid_q), variants_q[0])
            bg_path_q = str(active_var_q.get("background_path") or design_q.get("background_path") or "")
            if not bg_path_q or "_ai_keyframe" in bg_path_q:
                raise RuntimeError(
                    "teukgeup_archival_polaroid thumbnail must use a dedicated culprit portrait base background (media/thumbnail/thumb_bg_v*.jpg), not an _ai_keyframe scene"
                )
            layers_q = active_var_q.get("layers") if isinstance(active_var_q.get("layers"), list) else []
            pip1_q = next((l for l in layers_q if isinstance(l, dict) and l.get("id") == "inset_photo" and l.get("visible") is not False), None)
            pip2_q = next((l for l in layers_q if isinstance(l, dict) and l.get("id") == "inset_photo_2" and l.get("visible") is not False), None)
            if not pip1_q or not pip2_q:
                raise RuntimeError(
                    "teukgeup_archival_polaroid thumbnail requires BOTH visible inset_photo (arrest PiP) and inset_photo_2 (evidence/scene/court PiP)"
                )
            if "_ai_keyframe" in str(pip1_q.get("src") or "") or "_ai_keyframe" in str(pip2_q.get("src") or ""):
                raise RuntimeError(
                    "teukgeup_archival_polaroid PiP insets (inset_photo & inset_photo_2) must use real archival arrest & evidence/court/scene frames (media/thumbnail/pip_*.jpg), not _ai_keyframe scenes"
                )

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

        try:
            from .seo import apply_synthetic_media_disclosure, detect_ai_usage_in_project
            uses_ai_vis, uses_ai_tts = detect_ai_usage_in_project(job, workspace)
            profile = job.get("profile") if isinstance(job.get("profile"), dict) else {}
            snapshot = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
            lang = str(job.get("language") or profile.get("language") or snapshot.get("language") or "ko").strip().lower()
            if uses_ai_vis or uses_ai_tts:
                package, disc_changed = apply_synthetic_media_disclosure(package, uses_ai_visuals=uses_ai_vis, uses_ai_tts=uses_ai_tts, language=lang)
                if disc_changed:
                    (workspace / "seo_package.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return
    beats = _beats(workspace) if phase in {"plan", "visuals", "footage", "ai_visual", "edit", "qc"} else []
    if phase == "voice":
        from .visuals import load_plan_manifest

        beats = [item for item in (load_plan_manifest(workspace).get("beats") or []) if isinstance(item, dict)]
    beat_ids = {str(item.get("beat_id") or "") for item in beats if item.get("beat_id")}
    effective_min_scenes = int(contract["min_scene_count"])
    if float(contract.get("target_duration_sec") or 0) >= 600 and effective_min_scenes > 1:
        effective_min_scenes = min(effective_min_scenes, max(18, ceil(float(contract["target_duration_sec"]) / 12.0)))
    if len(beats) < effective_min_scenes:
        raise RuntimeError(f"visual manifest has {len(beats)} beats; minimum is {effective_min_scenes}")

    if phase == "plan":
        visual = _read_json(workspace / "visual_manifest.json")
        target = _number(visual.get("target_duration_sec"))
        if target is None or target <= 0:
            raise RuntimeError("visual manifest target duration does not match the quality contract")
        if len(beat_ids) != len(beats):
            raise RuntimeError("visual manifest requires one unique beat_id per beat")
        profile = job.get("profile") if isinstance(job.get("profile"), dict) else {}
        snapshot = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
        lang = str(job.get("language") or profile.get("language") or snapshot.get("language") or "").strip().lower()
        if lang == "ko":
            validate_korean_script_grammar_integrity(beats, job=job)
            validate_korean_anti_template_diversity(beats, workspace=workspace, job=job)
            prof_id_plan = str(job.get("channel_profile_id") or snapshot.get("id") or "").strip()
            ed_dna_plan = snapshot.get("editorial_dna") if isinstance(snapshot.get("editorial_dna"), dict) else {}
            kp_plan = ed_dna_plan.get("korean_prose_and_grammar_rules") if isinstance(ed_dna_plan.get("korean_prose_and_grammar_rules"), dict) else {}
            snap_kp = snapshot.get("korean_prose_and_grammar_rules") if isinstance(snapshot.get("korean_prose_and_grammar_rules"), dict) else {}
            target_range_30m = kp_plan.get("target_spoken_chars_range_30m") or snap_kp.get("target_spoken_chars_range_30m")
            target_mins = _number(job.get("target_duration_minutes")) or ((_number(target) or 0.0) / 60.0)
            if (
                target_mins
                and target_mins >= 22.0
                and len(beats) >= 60
                and (target_range_30m or prof_id_plan in {"channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2"})
            ):
                spoken_from_beats = sum(
                    len(str(b.get("narration_text") or b.get("text") or "").strip())
                    for b in beats
                )
                script_file = workspace / "script.md"
                spoken_from_md = 0
                if script_file.is_file():
                    spoken_from_md = sum(
                        len(ln.strip())
                        for ln in script_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                        if ln.strip() and not ln.strip().startswith("#")
                    )
                effective_spoken_chars = max(spoken_from_beats, spoken_from_md)
                is_drama_plan = (
                    str(job.get("content_mode") or snapshot.get("content_mode") or ed_dna_plan.get("content_mode") or "").strip().lower() == "creative_audio_drama"
                )
                chars_per_min_floor = 255 if is_drama_plan else 350
                min_spoken_floor = int(round(max(7500 if is_drama_plan else 8500, target_mins * chars_per_min_floor)))
                if effective_spoken_chars < min_spoken_floor:
                    if is_drama_plan:
                        raise RuntimeError(
                            f"PLAN Korean Audio-Drama duration error: script has only {effective_spoken_chars} spoken chars "
                            f"for a {target_mins:.0f}-minute episode (minimum required >= {min_spoken_floor} chars at 0.94x bedtime cadence); "
                            "deepen interpersonal scenes, craft sensory details, and dual-reversal dialogue across ACT01..ACT06"
                        )
                    raise RuntimeError(
                        f"PLAN Korean long-form duration error: script has only {effective_spoken_chars} spoken chars "
                        f"for a {target_mins:.0f}-minute episode (minimum required >= {min_spoken_floor} chars, target 9,500–11,500 chars); "
                        "deepen forensic dragnet and psychological interrogation acts instead of skimming"
                    )
        return

    if phase == "voice":
        voice = _read_json(workspace / "voice_manifest.json")
        duration = _number(voice.get("duration_sec"))
        if duration is None or duration <= 0:
            raise RuntimeError("VOICE duration is missing or invalid")
        # Không gán cứng số giây bắt buộc cho VOICE: thời lượng chọn trên UI chỉ là
        # khoảng ước tính (Khoảng X phút), giọng đọc tự nhiên có độ chênh lệch hợp lý.
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
        qc_summary = voice.get("qc_summary") if isinstance(voice.get("qc_summary"), dict) else {}
        cadence_audit = qc_summary.get("cadence_audit") if isinstance(qc_summary.get("cadence_audit"), dict) else {}
        raw_issues = [str(x) for x in (cadence_audit.get("issues") or []) if str(x)]
        med_sps_val = _number(cadence_audit.get("median_syllables_per_sec"))
        if med_sps_val is not None and med_sps_val <= 6.25:
            raw_issues = [x for x in raw_issues if not x.startswith("episode_speech_too_rushed")]
        if cadence_audit and not cadence_audit.get("synthetic_fixture") and raw_issues:
            issues_str = "; ".join(raw_issues)
            raise RuntimeError(
                f"VOICE cadence & emotional pacing rejected by @evidence_qa: {issues_str}"
            )
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

        # YPP Quality Gate Validations
        tl_for_ypp = _read_json(workspace / "timeline.json") if (workspace / "timeline.json").exists() else {}
        em_for_ypp = _read_json(workspace / "edit_manifest.json") if (workspace / "edit_manifest.json").exists() else {}
        candidate_beats = (
            (tl_for_ypp.get("beats") if isinstance(tl_for_ypp.get("beats"), list) and tl_for_ypp["beats"] else None)
            or (em_for_ypp.get("beats") if isinstance(em_for_ypp.get("beats"), list) and em_for_ypp["beats"] else None)
            or beats
        )
        if not candidate_beats and isinstance(checkpoint.get("beats"), list) and checkpoint["beats"]:
            candidate_beats = checkpoint["beats"]
        if not candidate_beats and isinstance(job.get("beats"), list) and job["beats"]:
            candidate_beats = job["beats"]

        if candidate_beats:
            policy = contract.get("monetization_policy") if isinstance(contract.get("monetization_policy"), dict) else {}
            ed_dna_ypp = job.get("editing_dna") if isinstance(job.get("editing_dna"), dict) else {}
            snap_ypp = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
            is_ai_cinema_ypp = (
                str(ed_dna_ypp.get("visual_priority_mode") or "").strip().lower() == "ai_cinema_character_drama"
                or str(job.get("content_mode") or snap_ypp.get("content_mode") or "").strip().lower() == "creative_audio_drama"
            )
            default_max_wrapper = (
                max(0.55, min(0.88, float(((ed_dna_ypp.get("visual_mix") or {}).get("ai") or 0.80)) + 0.08))
                if is_ai_cinema_ypp
                else 0.55
            )
            max_wrapper = float(job.get("max_single_wrapper_ratio") or policy.get("max_single_wrapper_ratio") or default_max_wrapper)
            evaluate_ypp_framing_wrapper_cap(candidate_beats, max_wrapper_ratio=max_wrapper)

            default_min_motion = 0.14 if is_ai_cinema_ypp else 0.35
            min_motion = float(job.get("min_motion_ratio") or policy.get("min_motion_ratio") or default_min_motion)
            evaluate_ypp_motion_floor(candidate_beats, min_motion_ratio=min_motion)

        edit_manifest_path = workspace / "edit_manifest.json"
        editing_dna = job.get("editing_dna") if isinstance(job.get("editing_dna"), dict) else {}
        vis_mix = editing_dna.get("visual_mix") if isinstance(editing_dna.get("visual_mix"), dict) else {}
        preset_id = str(editing_dna.get("preset_id") or "").strip()
        prof_id_edit = str(
            job.get("channel_profile_id")
            or job.get("profile_id")
            or (job.get("channel_profile_snapshot") or {}).get("id")
            or ""
        ).strip()
        is_newsroom_v2 = (
            prof_id_edit in {"channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2"}
            or preset_id in {"forensic_noir_director_v2", "vox_china_crime_newsroom_v10"}
            or str(editing_dna.get("director_mode") or "").strip().lower() in {"v2", "vox_china_crime_newsroom_v10"}
        )
        if is_newsroom_v2:
            if not edit_manifest_path.exists():
                raise RuntimeError(
                    "Role DNA Violation: Director V2 EDIT requires edit_manifest.json recording >=50% verified real case footage, multi-layer VOX, Motion Text, and closed-room AI counts"
                )
            edit_manifest_data = _read_json(edit_manifest_path)
            _min_ftg_v2 = float(
                job["min_real_footage_ratio"]
                if job.get("min_real_footage_ratio") is not None
                else max(0.48, float(vis_mix.get("min_footage_floor") if vis_mix.get("min_footage_floor") is not None else 0.50))
            )
            _max_vox_v2 = float(
                job["max_vox_scene_ratio"]
                if job.get("max_vox_scene_ratio") is not None
                else float(vis_mix.get("max_vox_scene_ratio") or 0.35)
            )
            _max_ai_v2 = float(
                job["max_ai_reconstruction_ratio"]
                if job.get("max_ai_reconstruction_ratio") is not None
                else float(vis_mix.get("max_ai_reconstruction_ratio") or 0.22)
            )
            _max_ct_v2 = float(
                job["max_cinema_text_ratio"]
                if job.get("max_cinema_text_ratio") is not None
                else float(vis_mix.get("max_cinema_text_ratio") or 0.16)
            )
            _job_id_str = str(job.get("id") or workspace.name).strip()
            _remotion_job_dir = Path(__file__).resolve().parents[2] / "CofiRemotion" / "public" / "jobs" / _job_id_str
            evaluate_ypp_visual_role_mix(
                edit_manifest_data,
                min_real_footage_ratio=_min_ftg_v2,
                max_vox_ratio=_max_vox_v2,
                max_ai_reconstruction_ratio=_max_ai_v2,
                max_cinema_text_ratio=_max_ct_v2,
                workspace=workspace,
                remotion_job_dir=_remotion_job_dir if _remotion_job_dir.is_dir() else None,
            )
        elif edit_manifest_path.exists() and (preset_id == "forensic_noir" or float(vis_mix.get("footage") or 0.0) >= 0.45):
            edit_manifest_data = _read_json(edit_manifest_path)
            evaluate_ypp_visual_role_mix(
                edit_manifest_data,
                min_real_footage_ratio=float(job.get("min_real_footage_ratio") or 0.45),
                max_ai_reconstruction_ratio=float(job.get("max_ai_reconstruction_ratio") or 0.28),
                max_cinema_text_ratio=float(job.get("max_cinema_text_ratio") or 0.12),
                workspace=workspace,
            )

        selected_bgm = (
            job.get("selected_bgm_tracks")
            or job.get("bgm_tracks")
            or checkpoint.get("selected_bgm_tracks")
            or checkpoint.get("bgm_tracks")
        )
        channel_profile_id = str(
            job.get("channel_profile_id")
            or job.get("profile_id")
            or (job.get("channel_profile_snapshot") or {}).get("id")
            or ""
        ).strip()
        if selected_bgm and channel_profile_id:
            bgm_history_path = Path(__file__).resolve().parents[1] / "data" / "bgm_usage_history.json"
            evaluate_ypp_bgm_anti_repetition(channel_profile_id, selected_bgm, bgm_history_path)

        outro_tail = (
            job.get("outro_tail_sec")
            or job.get("outro_audio_fade_tail_sec")
            or checkpoint.get("outro_tail_sec")
            or checkpoint.get("outro_audio_fade_tail_sec")
        )
        if outro_tail is not None:
            tail_val = _number(outro_tail)
            if tail_val is not None:
                evaluate_ypp_outro_audio_tail(tail_val, min_tail_sec=3.5)
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

    # YPP Quality Gate Validations in QC
    tl_qc_ypp = _read_json(workspace / "timeline.json") if (workspace / "timeline.json").exists() else {}
    em_qc_ypp = _read_json(workspace / "edit_manifest.json") if (workspace / "edit_manifest.json").exists() else {}
    candidate_beats = (
        (tl_qc_ypp.get("beats") if isinstance(tl_qc_ypp.get("beats"), list) and tl_qc_ypp["beats"] else None)
        or (em_qc_ypp.get("beats") if isinstance(em_qc_ypp.get("beats"), list) and em_qc_ypp["beats"] else None)
        or beats
        or (manifest.get("beats") if isinstance(manifest.get("beats"), list) else None)
        or (job.get("beats") if isinstance(job.get("beats") , list) else None)
    )
    if candidate_beats and isinstance(candidate_beats, list):
        policy = contract.get("monetization_policy") if isinstance(contract.get("monetization_policy"), dict) else {}
        max_wrapper = float(job.get("max_single_wrapper_ratio") or policy.get("max_single_wrapper_ratio") or 0.55)
        evaluate_ypp_framing_wrapper_cap(candidate_beats, max_wrapper_ratio=max_wrapper)

        min_motion = float(job.get("min_motion_ratio") or policy.get("min_motion_ratio") or 0.35)
        evaluate_ypp_motion_floor(candidate_beats, min_motion_ratio=min_motion)

    selected_bgm = (
        job.get("selected_bgm_tracks")
        or job.get("bgm_tracks")
        or manifest.get("selected_bgm_tracks")
        or manifest.get("bgm_tracks")
    )
    channel_profile_id = str(
        job.get("channel_profile_id")
        or job.get("profile_id")
        or (job.get("channel_profile_snapshot") or {}).get("id")
        or ""
    ).strip()
    if selected_bgm and channel_profile_id:
        bgm_history_path = Path(__file__).resolve().parents[1] / "data" / "bgm_usage_history.json"
        evaluate_ypp_bgm_anti_repetition(channel_profile_id, selected_bgm, bgm_history_path)

    outro_tail = (
        job.get("outro_tail_sec")
        or job.get("outro_audio_fade_tail_sec")
        or manifest.get("outro_tail_sec")
        or manifest.get("outro_audio_fade_tail_sec")
    )
    if outro_tail is not None:
        tail_val = _number(outro_tail)
        if tail_val is not None:
            evaluate_ypp_outro_audio_tail(tail_val, min_tail_sec=3.5)

    if not manifest.get("sha256"):
        raise RuntimeError("QC requires final video SHA-256")


# ==============================================================================
# VOICE-INTENT BESPOKE VOX MOTION SYSTEM (12 PHYSICAL MOTION VERBS · ZERO COPY-PASTE)
# ==============================================================================

VOX_BESPOKE_MOTION_INTENTS: tuple[str, ...] = (
    "EVIDENCE_COLLISION_COMPARE",
    "LAYER_PEEL_UNMASK",
    "CHRONO_SCRUB_RULER",
    "FORENSIC_LOUPE_SCAN",
    "NETWORK_THREAD_WEAVE",
    "CONTRADICTION_SCALE_DROP",
    "DOSSIER_STACK_SPREAD",
    "BLUEPRINT_CROSS_SECTION_REVEAL",
    "LEDGER_ANOMALY_ISOLATE",
    "PARABOLIC_GIS_PURSUIT",
    "RADIAL_PINBOARD_LOCK",
    "TORN_HEADLINE_SHATTER",
)

REQUIRED_VOX_MANIFEST_MOTION_FIELDS: tuple[str, ...] = (
    "voice_meaning",
    "motion_intent",
    "motion_purpose_for_sentence",
    "t1_action",
    "t2_action",
    "t3_action",
    "spatial_lock_targets",
)


def compute_vox_motion_signature(entry: dict[str, Any]) -> str:
    """Compute a deterministic motion signature for a VOX beat/scene entry."""
    intent = str(entry.get("motion_intent") or entry.get("voxVerb") or "").strip().upper()
    cam_vec = str(entry.get("camera_trajectory") or entry.get("cam_pose_sig") or "").strip()
    slide_dirs = str(entry.get("slide_directions") or "").strip()
    t1_act = str(entry.get("t1_action") or "").strip()[:48]
    t2_act = str(entry.get("t2_action") or "").strip()[:48]
    t3_act = str(entry.get("t3_action") or "").strip()[:48]
    return f"{intent}|cam:{cam_vec}|slide:{slide_dirs}|t1:{t1_act}|t2:{t2_act}|t3:{t3_act}"


def validate_vox_scene_manifest_motion_contract(
    manifest_or_path: dict[str, Any] | list[dict[str, Any]] | Path,
) -> dict[str, Any]:
    """Validate that every VOX beat in `vox_scene_manifest.json` declares bespoke Voice-Intent
    motion fields (`voice_meaning`, `motion_intent`, `motion_purpose_for_sentence`,
    `t1_action`, `t2_action`, `t3_action`, `spatial_lock_targets`) and has zero consecutive
    duplicate `motion_intent` or copy-pasted `motion_signature`."""
    raw: Any = manifest_or_path
    if isinstance(manifest_or_path, Path):
        if not manifest_or_path.is_file():
            return {"passed": False, "violations": [f"vox_scene_manifest.json not found: {manifest_or_path}"]}
        raw = json.loads(manifest_or_path.read_text(encoding="utf-8"))

    if isinstance(raw, list):
        entries = [x for x in raw if isinstance(x, dict)]
    elif isinstance(raw, dict):
        entries = []
        for key in ("scenes", "beats", "vox_scenes", "items"):
            if isinstance(raw.get(key), list):
                entries = [x for x in raw[key] if isinstance(x, dict)]
                break
    else:
        entries = []

    violations: list[str] = []
    issues: list[dict[str, str]] = []
    signatures: dict[str, str] = {}
    cam_trajectories: dict[str, str] = {}
    prev_intent: str | None = None
    prev_label: str | None = None

    for idx, item in enumerate(entries):
        label = str(
            item.get("beat_id")
            or item.get("vox_scene_id")
            or item.get("voxSceneId")
            or f"entry_{idx + 1}"
        )
        missing: list[str] = []
        for field in REQUIRED_VOX_MANIFEST_MOTION_FIELDS:
            val = item.get(field)
            if val is None:
                missing.append(field)
            elif isinstance(val, str) and not val.strip():
                missing.append(field)
            elif isinstance(val, (list, dict)) and len(val) == 0:
                missing.append(field)
        if missing:
            msg = f"[FAIL:VOX_MANIFEST_MISSING_MOTION_INTENT_FIELDS] {label} missing mandatory fields: {', '.join(missing)}"
            violations.append(msg)
            issues.append({"type": "vox_manifest_missing_motion_intent_fields", "beat_id": label, "detail": msg})

        intent = str(item.get("motion_intent") or "").strip().upper()
        if intent and prev_intent and intent == prev_intent:
            msg = f"[FAIL:CONSECUTIVE_DUPLICATE_MOTION_INTENT] {prev_label} -> {label} repeat motion_intent '{intent}'"
            violations.append(msg)
            issues.append({"type": "vox_consecutive_duplicate_motion_intent", "beat_id": label, "detail": msg})
        if intent:
            prev_intent = intent
            prev_label = label

        wps = item.get("camera_waypoints") or item.get("cam_poses")
        if isinstance(wps, list) and len(wps) >= 2:
            cam_sig = "->".join(
                f"{round(float(w.get('x', 960)) / 30) * 30}:{round(float(w.get('y', 540)) / 30) * 30}:{float(w.get('z', w.get('zoom', 1.0))):.2f}"
                for w in wps
                if isinstance(w, dict)
            )
            if cam_sig and cam_sig in cam_trajectories:
                msg = f"[FAIL:COPY_PASTED_CAMERA_TRAJECTORY] {label} duplicates camera trajectory of {cam_trajectories[cam_sig]} ({cam_sig})"
                violations.append(msg)
                issues.append({"type": "vox_copy_pasted_camera_trajectory", "beat_id": label, "detail": msg})
            elif cam_sig:
                cam_trajectories[cam_sig] = label

        sig = compute_vox_motion_signature(item)
        if intent and item.get("t1_action") and item.get("t2_action") and item.get("t3_action"):
            if sig in signatures:
                msg = f"[FAIL:COPY_PASTED_MOTION_SIGNATURE] {label} duplicates motion_signature of {signatures[sig]}"
                violations.append(msg)
                issues.append({"type": "vox_copy_pasted_motion_signature", "beat_id": label, "detail": msg})
            else:
                signatures[sig] = label

    return {
        "passed": len(violations) == 0,
        "total_entries": len(entries),
        "scene_count": len(entries),
        "violations": violations,
        "issues": issues,
    }

