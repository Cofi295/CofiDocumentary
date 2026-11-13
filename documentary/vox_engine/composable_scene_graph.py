"""Composable Voice-Meaning Scene Graph & Context-Adaptive Physics Engine
for CofiDocumentary (Python/Pillow + Blender 3D Stage + Frame-Locked SFX).

Implements User Rule #3 across both Python/Blender (`vox_engine` / `CofiBlenderStudio`) and Remotion:
- LOCKED AESTHETIC STYLE DNA:
  Warm tactile archival materials (dark walnut desk `#1E1915`, aged Manila folder `#D6C098`,
  warm newsprint `#E7E0D2`, cream card `#F6F1E7`, deep charcoal ink `#181613`,
  forensic crimson `#B01E1A`, amber highlighter `#EAB308`), senior-friendly contrast (45-70yo).
- 100% FLEXIBLE LAYOUT, TYPOGRAPHY & PHYSICAL MOTION:
  Every Vox scene is composed dynamically from atomic primitives (`PaperSheet`, `PolaroidPin`,
  `NewspaperClipping`, `SatelliteFlightStage`, `FunnelEliminationTree`, `RelayChronologyChain`,
  `MacroForensicLoupe`, `DualFacadeCollision`, `HighlighterSwipe`, `CrimsonStringLink`,
  `OfficialSealStamp`, `MetricCounter`) driven by the spoken sentence's meaning and `clauseWindows`.
- 100% MOTION-BOUND SFX EMISSION:
  Every animated primitive emits its exact frame offset (`offsetFrames`) and Foley SFX file
  so sound effects trigger at the exact frame the visual movement happens.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .archetypes import (
    W,
    H,
    VOX_CREAM_CARD,
    VOX_CRIMSON,
    VOX_DESK_DARK,
    VOX_INK,
    VOX_INK_MUTED,
    VOX_MANILA,
    VOX_MEMO_YELLOW,
    VOX_NEWSPRINT,
    VOX_PAPER,
    VOX_TEAL,
    VOX_YELLOW,
    _draw_brass_fastener,
    _draw_circular_official_seal,
    _draw_paperclip,
    _draw_pushpin,
    _extract_voice_clauses_and_windows,
    draw_cinema_subtitle,
    ease_in_out_cubic,
    ease_out_cubic,
    fit_crop,
    get_cork_pinboard_shell,
    get_dark_investigation_desk,
    get_fallback_image,
    get_torn_paper_sheet,
    paste_photo_polaroid,
)
from .gis_cache import (
    crop_map_camera,
    draw_satellite_hud_grid,
    get_real_satellite_campus_z16,
    get_vox_styled_baiyin_urban_base,
)
from .typography import (
    draw_text_safe,
    get_cascade_font,
    resolve_contextual_font_style,
    wrap_text_to_width,
)
from documentary.audio_library_manager import MOTION_PRIMITIVE_TO_SFX


LOCKED_VOX_STYLE_DNA: dict[str, Any] = {
    "style_id": "korean_investigative_tactile_vox_v3",
    "locked_palette": {
        "walnut_desk": "#1E1915",
        "detective_cork": "#403429",
        "manila_folder": "#D6C098",
        "archival_newsprint": "#E7E0D2",
        "cream_card": "#F6F1E7",
        "charcoal_ink": "#181613",
        "forensic_crimson": "#B01E1A",
        "amber_highlighter": "#EAB308",
        "jurisdiction_teal": "#245C5E",
    },
    "senior_readability_rules": {
        "target_audience_age": "45-70",
        "max_clusters_per_screen": 4,
        "min_body_font_px": 28,
        "hero_metric_font_px": 64,
        "forbid_neon_strobe": True,
    },
}


def calculate_proportional_vox_scenes(duration_minutes: float) -> int:
    """Calculate script-proportional Vox scene count based on duration (replaces 31 fixed quota).
    Naturally scales with episode duration:
      - 12 min -> 8 to 15 scenes (typically ~10-12)
      - 20 min -> 16 to 24 scenes (typically ~18-20)
      - 30 min -> 25 to 38 scenes (typically ~28-32)
    """
    mins = max(1.0, float(duration_minutes))
    scenes = int(round(mins * 1.0))
    if mins <= 15.0:
        return max(8, min(15, scenes))
    elif mins <= 25.0:
        return max(16, min(24, scenes))
    else:
        return max(25, min(38, scenes))


GRAMMAR_PHYSICS_VARIANTS: dict[str, list[str]] = {
    "funnel_elimination_tree": [
        "camera_funnel_zoom",
        "cascading_tree_collapse",
        "radial_dossier_sieve",
        "hierarchical_layer_pull",
    ],
    "archival_press_scatter": [
        "damped_paper_drop",
        "press_clipping_unfold",
        "multi_article_carousel",
        "editorial_headline_slam",
    ],
    "spatial_proximity_paradox": [
        "gis_camera_flight_arc",
        "satellite_orbital_drift",
        "tactical_vector_zoom",
        "topographic_contour_sweep",
    ],
    "relay_chronology_chain": [
        "camera_tracking_pan",
        "horizontal_scrub_glide",
        "kinetic_milestone_hop",
        "stacked_decade_slide",
    ],
    "dual_facade_collision": [
        "opposing_spring_collision",
        "split_axial_wipe",
        "contrast_shutter_revolve",
        "duality_cross_dissolve",
    ],
    "macro_forensic_loupe": [
        "optical_focus_pull",
        "microscopic_iris_zoom",
        "polarizing_filter_sweep",
        "fluorescent_luminescence_scan",
    ],
    "monumental_verdict_scroll": [
        "heavy_stamp_recoil",
        "parchment_gravity_unroll",
        "verdict_pillar_elevation",
        "judicial_seal_impact",
    ],
}


def resolve_style_tokens_for_profile(
    profile_or_dna: dict[str, Any] | None = None,
    preset_id: str = "",
) -> dict[str, Any]:
    """Resolve style-locked material tokens based on active channel profile, editing DNA, or preset."""
    profile_or_dna = profile_or_dna or {}
    resolved_id = str(
        preset_id
        or profile_or_dna.get("preset_id")
        or profile_or_dna.get("editing_preset")
        or profile_or_dna.get("visual_style")
        or profile_or_dna.get("tone_preset")
        or ""
    ).lower()

    if "technical" in resolved_id or "2.5d" in resolved_id or "infrastructure" in resolved_id:
        return {
            "style_id": "technical_25d_infrastructure",
            "locked_palette": {
                "walnut_desk": "#0B1120",
                "detective_cork": "#1E293B",
                "manila_folder": "#334155",
                "archival_newsprint": "#E2E8F0",
                "cream_card": "#F1F5F9",
                "charcoal_ink": "#0F172A",
                "forensic_crimson": "#EF4444",
                "amber_highlighter": "#38BDF8",  # Technical cyan highlight
                "jurisdiction_teal": "#0EA5E9",
            },
            "senior_readability_rules": {
                "target_audience_age": "45-70",
                "max_clusters_per_screen": 4,
                "min_body_font_px": 28,
                "hero_metric_font_px": 64,
                "forbid_neon_strobe": True,
            },
            "material_textures": {
                "base_surface": "technical_matte_grid",
                "paper_grain": "fine_bond_vector",
                "lighting_tone": "cool_ambient_telemetry",
            },
        }
    elif "cyber" in resolved_id or "finance" in resolved_id or "crypto" in resolved_id:
        return {
            "style_id": "financial_forensic_onchain",
            "locked_palette": {
                "walnut_desk": "#111827",
                "detective_cork": "#1F2937",
                "manila_folder": "#374151",
                "archival_newsprint": "#F3F4F6",
                "cream_card": "#F9FAFB",
                "charcoal_ink": "#111827",
                "forensic_crimson": "#DC2626",
                "amber_highlighter": "#10B981",  # On-chain ledger emerald
                "jurisdiction_teal": "#06B6D4",
            },
            "senior_readability_rules": {
                "target_audience_age": "45-70",
                "max_clusters_per_screen": 4,
                "min_body_font_px": 28,
                "hero_metric_font_px": 64,
                "forbid_neon_strobe": True,
            },
            "material_textures": {
                "base_surface": "dark_slate_ledger",
                "paper_grain": "bank_statement_parchment",
                "lighting_tone": "forensic_blue_contrast",
            },
        }
    elif "archival" in resolved_id or "historical" in resolved_id or "vintage" in resolved_id:
        return {
            "style_id": "archival_historical_vault",
            "locked_palette": {
                "walnut_desk": "#2B2119",
                "detective_cork": "#4A3B2C",
                "manila_folder": "#D4BA94",
                "archival_newsprint": "#EDE5D2",
                "cream_card": "#FAF6EE",
                "charcoal_ink": "#231810",
                "forensic_crimson": "#881337",
                "amber_highlighter": "#D97706",
                "jurisdiction_teal": "#1E3A8A",
            },
            "senior_readability_rules": {
                "target_audience_age": "45-70",
                "max_clusters_per_screen": 4,
                "min_body_font_px": 28,
                "hero_metric_font_px": 64,
                "forbid_neon_strobe": True,
            },
            "material_textures": {
                "base_surface": "aged_library_wood",
                "paper_grain": "vintage_rag_paper",
                "lighting_tone": "warm_tungsten_desk_lamp",
            },
        }
    else:
        return LOCKED_VOX_STYLE_DNA


def classify_voice_semantic_intent(narration_text: str, arch_hint: str = "", beat_index: int = 0) -> dict[str, str]:
    """Analyze the spoken Korean/Vietnamese/English sentence to determine:
    1) `layout_grammar`: which spatial composition grammar best expresses the meaning of this sentence
    2) `physics_mode`: how objects and camera move physically (rotating variants to guarantee 0% template clones)
    3) `headline_font_style` & `body_font_style`: context-adaptive typography
    """
    txt = f"{narration_text} {arch_hint}".lower()

    # 1. Funnel / Narrowing / Elimination ("1만 5,000명 -> 마씨 가문 -> 용의자 특정")
    if any(k in txt for k in ("압축", "좁혀", "가계도", "1만", "수만", "전수", "추려", "소거", "성씨", "funnel", "tree", "y-str", "narrow", "suspects", "elimination", "thu hẹp", "sàng lọc", "loại trừ")):
        layout_grammar = "funnel_elimination_tree"
    # 2. Press / Broadsheet Chronicle ("신문", "보도", "언론", "기사", "특종", "대서특필")
    elif any(k in txt for k in ("신문", "보도", "언론", "기사", "특종", "헤드라인", "대서특필", "press", "newspaper", "#p", "headline", "broadsheet", "báo chí", "truyền thông", "tiêu điểm", "trang nhất")):
        layout_grammar = "archival_press_scatter"
    # 3. Spatial Proximity / Trajectory / Map ("1.5킬로미터", "옆 동네", "캠퍼스", "이동", "쉬저우", "페이현")
    elif any(k in txt for k in ("킬로미터", "km", "옆 동네", "거리", "위치", "반경", "캠퍼스", "지도", "위성", "이동", "도주", "고향", "gis", "sat", "#m", "s3_", "s4_", "miles", "kilometer", "distance", "fled", "escape", "route", "flight", "satellite", "map", "border", "đường đi", "bỏ trốn", "khoảng cách", "tọa độ", "vệ tinh", "bản đồ", "hành trình")):
        layout_grammar = "spatial_proximity_paradox"
    # 4. Generational Relay / Chronology ("3대", "선배", "후배", "물려", "28년 동안", "흐르", "연도")
    elif any(k in txt for k in ("3대", "선배", "후배", "물려", "세 번", "28년 동안", "흐르", "세월", "일지", "계승", "timeline", "relay", "years", "decade", "chronology", "generations", "thập kỷ", "dòng thời gian", "tiếp nối", "năm tháng")):
        layout_grammar = "relay_chronology_chain"
    # 5. Dual Identity / Paradox / Contrast ("모범 시민", "이중생활", "유령처럼", "반면", "두 얼굴", "가면")
    elif any(k in txt for k in ("모범 시민", "이중생활", "두 얼굴", "가면", "반면", "평온", "대조", "역설", "충격", "경악", "duality", "double life", "paradox", "contrast", "facade", "hai mặt", "vỏ bọc", "ngụy trang", "đối lập")):
        layout_grammar = "dual_facade_collision"
    # 6. Forensic Micro-Specimen / Lab / Cryo ("단 하나의 dna", "냉동고", "영하", "현미경", "99.9", "감식", "혈흔", "지문")
    elif any(k in txt for k in ("단 하나의 dna", "냉동고", "영하", "현미경", "99.9", "감식", "시료", "검출", "혈흔", "지문", "loupe", "micro", "specimen", "forensic", "biometric", "dna", "fingerprint", "giám định", "dấu vân tay", "mẫu phẩm", "kính hiển vi")):
        layout_grammar = "macro_forensic_loupe"
    # 7. Court Verdict / Judicial Reckoning ("사형", "선고", "법원", "판결", "최고인민법원", "집행", "심판")
    elif any(k in txt for k in ("사형", "선고", "법원", "판결", "최고인민법원", "집행", "심판", "기각", "verdict", "court", "sentence", "execution", "trial", "tòa án", "bản án", "tử hình", "phán quyết")):
        layout_grammar = "monumental_verdict_scroll"
    else:
        # Rotate organically among the grammars based on beat hash so two beats never share identical layout
        grammars = [
            "relay_chronology_chain",
            "dual_facade_collision",
            "macro_forensic_loupe",
            "archival_press_scatter",
            "funnel_elimination_tree",
        ]
        layout_grammar = grammars[beat_index % len(grammars)]

    # Cycle physics mode variants per grammar to ensure 0% identical template clones across the episode
    variants = GRAMMAR_PHYSICS_VARIANTS.get(layout_grammar, ["damped_paper_drop"])
    physics_mode = variants[beat_index % len(variants)]

    headline_font = resolve_contextual_font_style(narration_text, role="headline", scene_intent=layout_grammar)
    body_font = resolve_contextual_font_style(narration_text, role="body", scene_intent=layout_grammar)
    metric_font = resolve_contextual_font_style(narration_text, role="metric", scene_intent=layout_grammar)
    telemetry_font = resolve_contextual_font_style(narration_text, role="telemetry", scene_intent=layout_grammar)

    return {
        "layout_grammar": layout_grammar,
        "physics_mode": physics_mode,
        "headline_font_style": headline_font,
        "body_font_style": body_font,
        "metric_font_style": metric_font,
        "telemetry_font_style": telemetry_font,
    }


def build_composable_vox_scene_spec(
    beat: dict[str, Any],
    voice_spec: dict[str, Any] | None = None,
    fps: int = 30,
) -> dict[str, Any]:
    """Build a complete, voice-meaning-driven Composable Vox Scene Graph (`ComposableVoxSceneSpec`)
    for both Python/Blender (`VoxSceneRenderer` / `CofiBlenderStudio`) and Remotion (`VoxComposablePrimitives`),
    including frame-accurate `sfx_events` emitted directly by the animated primitives.
    """
    vspec = dict(voice_spec or beat.get("voice_spec") or {})
    beat_id = str(beat.get("beat_id") or beat.get("beatId") or vspec.get("beat_id") or "B001").strip()
    beat_idx = int(vspec.get("vox_slot_index") or beat.get("beat_index") or 0)
    narration = str(
        vspec.get("narration_text")
        or beat.get("narration_text")
        or beat.get("narrationText")
        or beat.get("text")
        or ""
    ).strip()
    arch_hint = str(
        vspec.get("scene_archetype")
        or vspec.get("arch")
        or beat.get("scene_archetype")
        or beat.get("voxArchetype")
        or ""
    ).strip()
    dur_sec = float(vspec.get("duration_sec") or beat.get("duration_sec") or (beat.get("durationInFrames", 180) / fps))
    dur_frames = max(60, int(round(dur_sec * fps)))
    speech_frames = int(beat.get("speechFrames") or max(45, dur_frames - 6))
    lang = str(vspec.get("language") or beat.get("language") or "ko").lower()

    # Style-locked material tokens: resolve strictly from active channel profile or editing DNA
    profile_ctx = beat.get("profile") or vspec.get("profile") or beat.get("editing_dna") or vspec.get("editing_dna")
    preset_ctx = str(beat.get("preset_id") or vspec.get("preset_id") or "")
    style_dna = resolve_style_tokens_for_profile(profile_ctx, preset_id=preset_ctx)

    default_headers = (
        ["핵심 수사 기록 분석", "결정적 증거 교차 검증", "수사 본부 최종 확인"]
        if lang == "ko"
        else ["Forensic Evidence Analysis", "Cross-Verification Record", "Official Finding Confirmation"]
    )
    clauses, windows, metrics, header_text, sub_text = _extract_voice_clauses_and_windows(
        vspec,
        [narration[:28] or default_headers[0], narration[28:56] or default_headers[1], default_headers[2]],
    )
    explicit_metrics = [
        str(m).strip()
        for m in (vspec.get("metrics") or vspec.get("key_metrics") or [])
        if str(m).strip() and not str(m).strip().startswith("EVIDENCE")
    ]
    if explicit_metrics:
        metrics = explicit_metrics + [m for m in metrics if not str(m).startswith("EVIDENCE")]
    clue_prefix = "핵심 단서" if lang == "ko" else "Key Clue"
    metrics = [
        (f"{clue_prefix} #{i+1:02d}" if str(m).startswith("EVIDENCE") else str(m))
        for i, m in enumerate(metrics or [f"{clue_prefix} #01", f"{clue_prefix} #02", f"{clue_prefix} #03"])
    ]
    semantic = classify_voice_semantic_intent(narration, arch_hint=arch_hint, beat_index=beat_idx)
    if vspec.get("layout_grammar"):
        semantic["layout_grammar"] = str(vspec["layout_grammar"])
    grammar = semantic["layout_grammar"]

    # Build atomic primitives list with exact clause-synced animation windows and motion primitives
    primitives: list[dict[str, Any]] = []
    sfx_events: list[dict[str, Any]] = []

    def _add_primitive(
        prim_id: str,
        prim_type: str,
        motion_primitive: str,
        w0: float,
        w1: float,
        props: dict[str, Any],
        emit_sfx: bool = True,
    ) -> None:
        primitives.append(
            {
                "id": prim_id,
                "type": prim_type,
                "motion_primitive": motion_primitive,
                "window": [round(w0, 4), round(w1, 4)],
                "props": props,
            }
        )
        if emit_sfx and motion_primitive in MOTION_PRIMITIVE_TO_SFX:
            sfx_file, sfx_vol = MOTION_PRIMITIVE_TO_SFX[motion_primitive]
            offset_f = max(4, min(dur_frames - 15, int(round(w0 * speech_frames))))
            # Prevent two SFX from colliding on the exact same frame
            if sfx_events and abs(sfx_events[-1]["offsetFrames"] - offset_f) < 12:
                offset_f = min(dur_frames - 12, sfx_events[-1]["offsetFrames"] + 15)
            sfx_events.append(
                {
                    "offsetFrames": offset_f,
                    "timestamp_sec": round(offset_f / fps, 3),
                    "file": f"audio/{sfx_file}",
                    "libraryPath": f"audio_library/sfx/{sfx_file}",
                    "volume": sfx_vol,
                    "primitive": motion_primitive,
                    "primitive_id": prim_id,
                }
            )

    w_c0 = windows[0] if windows else (0.0, 0.34)
    w_c1 = windows[1] if len(windows) > 1 else (0.34, 0.68)
    w_c2 = windows[2] if len(windows) > 2 else (0.68, 1.0)

    if grammar == "spatial_proximity_paradox":
        _add_primitive(
            "map_stage",
            "SatelliteFlightStage",
            "gis_camera_flight_arc",
            0.02,
            0.85,
            {"header": header_text, "subhead": sub_text, "distance_label": metrics[0] if metrics else ("1.5 km" if lang == "ko" else "1.5 miles")},
        )
        _add_primitive(
            "pin_origin",
            "MapPinNode",
            "map_pin_pulse_ring",
            max(0.18, w_c1[0]),
            w_c1[1],
            {"label": clauses[0][:24], "tag": metrics[0] if metrics else ("지점 ①" if lang == "ko" else "Waypoint 1")},
        )
        _add_primitive(
            "pin_target_paradox",
            "MapTargetLockCard",
            "coordinate_target_lock",
            max(0.48, w_c2[0]),
            w_c2[1],
            {"label": (clauses[1] if len(clauses) > 1 else clauses[0])[:26], "tag": metrics[1] if len(metrics) > 1 else ("지점 ②" if lang == "ko" else "Waypoint 2")},
        )
    elif grammar == "funnel_elimination_tree":
        _add_primitive(
            "funnel_root",
            "PaperDossierStage",
            "paper_card_slide",
            0.02,
            0.30,
            {"title": header_text, "metric": metrics[0] if metrics else "15,000+"},
        )
        _add_primitive(
            "funnel_filter",
            "FunnelBranchFilter",
            "numeric_counter_roll",
            max(0.24, w_c1[0]),
            w_c1[1],
            {"clause": clauses[1] if len(clauses) > 1 else clauses[0], "metric": metrics[1] if len(metrics) > 1 else ("Y-STR 압축" if lang == "ko" else "Biometric Filter")},
        )
        _add_primitive(
            "funnel_target_lock",
            "SuspectTargetLock",
            "dna_locus_match_lock",
            max(0.55, w_c2[0]),
            w_c2[1],
            {"clause": clauses[-1], "metric": metrics[-1] if metrics else ("최종 특정" if lang == "ko" else "Target Verified")},
        )
    elif grammar == "relay_chronology_chain":
        _add_primitive(
            "relay_base",
            "ManilaTimelineTrack",
            "manila_dossier_open",
            0.02,
            0.28,
            {"title": header_text},
        )
        _add_primitive(
            "relay_step_1",
            "RelayEvidenceCard",
            "timeline_relay_step",
            max(0.22, w_c1[0]),
            w_c1[1],
            {"clause": clauses[1] if len(clauses) > 1 else clauses[0]},
        )
        _add_primitive(
            "relay_step_2",
            "HighlighterVerdictBar",
            "highlighter_stroke_swipe",
            max(0.56, w_c2[0]),
            w_c2[1],
            {"clause": clauses[-1]},
        )
    elif grammar == "dual_facade_collision":
        _add_primitive(
            "left_facade_card",
            "PolaroidEvidenceCard",
            "polaroid_photo_pin",
            0.03,
            0.32,
            {"side": "left", "caption": clauses[0][:26]},
        )
        _add_primitive(
            "right_reality_card",
            "CrimsonStringComparison",
            "crimson_string_draw",
            max(0.26, w_c1[0]),
            w_c1[1],
            {"side": "right", "caption": (clauses[1] if len(clauses) > 1 else clauses[0])[:26]},
        )
        _add_primitive(
            "collision_highlight",
            "HighlighterConclusion",
            "highlighter_stroke_swipe",
            max(0.58, w_c2[0]),
            w_c2[1],
            {"clause": clauses[-1]},
        )
    elif grammar == "macro_forensic_loupe":
        _add_primitive(
            "specimen_plate",
            "ForensicSpecimenPlate",
            "loupe_magnifier_sweep",
            0.02,
            0.40,
            {"title": header_text},
        )
        _add_primitive(
            "locus_match",
            "BiometricMatchReadout",
            "dna_locus_match_lock",
            max(0.30, w_c1[0]),
            w_c1[1],
            {"clause": clauses[1] if len(clauses) > 1 else clauses[0], "metric": metrics[0] if metrics else "99.9999%"},
        )
        _add_primitive(
            "seal_confirm",
            "OfficialForensicSeal",
            "official_seal_stamp",
            max(0.62, w_c2[0]),
            w_c2[1],
            {"clause": clauses[-1]},
        )
    elif grammar == "monumental_verdict_scroll":
        _add_primitive(
            "verdict_dossier",
            "CourtJudgmentScroll",
            "manila_dossier_open",
            0.02,
            0.30,
            {"title": header_text},
        )
        _add_primitive(
            "gavel_pronouncement",
            "VerdictClauseBanner",
            "verdict_gavel_strike",
            max(0.26, w_c1[0]),
            w_c1[1],
            {"clause": clauses[1] if len(clauses) > 1 else clauses[0]},
        )
        _add_primitive(
            "supreme_seal",
            "SupremeCourtSealStamp",
            "heavy_seal_impact",
            max(0.60, w_c2[0]),
            w_c2[1],
            {"clause": clauses[-1]},
        )
    else:  # archival_press_scatter
        _add_primitive(
            "newsprint_sheet",
            "BroadsheetNewspaperClipping",
            "newspaper_clipping_unfold",
            0.02,
            0.32,
            {"headline": header_text},
        )
        _add_primitive(
            "press_photo_pin",
            "PolaroidEvidenceCard",
            "polaroid_photo_pin",
            max(0.25, w_c1[0]),
            w_c1[1],
            {"caption": clauses[0][:26]},
        )
        _add_primitive(
            "marker_swipe",
            "FeltpenHighlighterStroke",
            "highlighter_stroke_swipe",
            max(0.55, w_c2[0]),
            w_c2[1],
            {"clause": clauses[-1]},
        )

    # Also build 3D stage spec for Blender (`CofiBlenderStudio`) so Blender camera & 3D planes follow the exact same voice meaning
    blender_3d_stage = {
        "style_dna": style_dna.get("style_id", LOCKED_VOX_STYLE_DNA["style_id"]),
        "layout_grammar": grammar,
        "physics_mode": semantic["physics_mode"],
        "camera_rig": {
            "lens_mm": 35.0 if grammar == "spatial_proximity_paradox" else (85.0 if grammar == "macro_forensic_loupe" else 50.0),
            "dof_fstop": 2.8 if grammar == "macro_forensic_loupe" else 5.6,
            "start_pos": [-0.35, -2.4, 1.45] if semantic["physics_mode"] == "camera_tracking_pan" else [0.0, -2.6, 1.65],
            "end_pos": [0.35, -2.2, 1.35] if semantic["physics_mode"] == "camera_tracking_pan" else [0.0, -2.15, 1.28],
        },
        "planes_z_layers": [
            {"id": p["id"], "type": p["type"], "z_height_m": round(0.02 + idx * 0.035, 3), "window": p["window"]}
            for idx, p in enumerate(primitives)
        ],
    }

    return {
        "beat_id": beat_id,
        "duration_sec": dur_sec,
        "duration_frames": dur_frames,
        "speech_frames": speech_frames,
        "narration_text": narration,
        "header_ko": header_text,
        "header_text": header_text,
        "sub_ko": sub_text,
        "sub_text": sub_text,
        "language": lang,
        "clauses": clauses,
        "clause_windows": [list(w) for w in windows],
        "metrics": metrics,
        "style_dna": style_dna,
        "material_tokens": style_dna,
        "semantic": semantic,
        "primitives": primitives,
        "sfx_events": sfx_events,
        "blender_3d_stage": blender_3d_stage,
    }


def render_composable_vox_frame(
    seq_p: float = 0.5,
    frame_a: Image.Image | None = None,
    frame_b: Image.Image | None = None,
    subtitle_text: str = "",
    voice_spec: dict[str, Any] | None = None,
) -> Image.Image:
    """Renders a 1920x1080 frame from the dynamic `ComposableVoxSceneSpec` where:
    - Material/Palette style is locked (`LOCKED_VOX_STYLE_DNA`)
    - Spatial layout, font family (`editorial_serif`, `monumental_verdict`, `forensic_mono`,
      `dossier_typewriter`, `broadcast_sans`), and physical motion adapt 100% to the spoken sentence!
    """
    spec = build_composable_vox_scene_spec(beat={}, voice_spec=voice_spec)
    grammar = spec["semantic"]["layout_grammar"]
    h_font = spec["semantic"]["headline_font_style"]
    b_font = spec["semantic"]["body_font_style"]
    m_font = spec["semantic"]["metric_font_style"]
    t_font = spec["semantic"]["telemetry_font_style"]

    clauses = spec["clauses"]
    windows = spec["clause_windows"]
    metrics = spec["metrics"]
    header_ko = spec["header_ko"]
    sub_ko = spec["sub_ko"]
    seed = int((voice_spec or {}).get("variation_seed") or sum(ord(c) for c in spec["beat_id"]) % 97)

    def _clause_p(idx: int) -> float:
        w0, w1 = windows[idx] if idx < len(windows) else (idx / 3.0, (idx + 1) / 3.0)
        return ease_out_cubic(max(0.0, min(1.0, (seq_p - max(0.0, w0 - 0.03)) / max(0.08, w1 - w0))))

    p0, p1, p2 = _clause_p(0), _clause_p(1), _clause_p(2)

    img_a = fit_crop(frame_a or get_fallback_image(1280, 840, "EVIDENCE A"), 1280, 840)
    img_b = fit_crop(frame_b or frame_a or get_fallback_image(1280, 840, "EVIDENCE B"), 1280, 840)

    # ==========================================================================
    # GRAMMAR 1: SPATIAL PROXIMITY PARADOX (Real Satellite Flight + Distance + Duality Card)
    # ==========================================================================
    if grammar == "spatial_proximity_paradox":
        sat_img, _sat_meta = get_real_satellite_campus_z16() if (seed % 2 == 0) else get_vox_styled_baiyin_urban_base()
        # Smooth camera flight across satellite plate
        cam_cx = 0.44 + 0.14 * ease_in_out_cubic(seq_p)
        cam_cy = 0.48 - 0.08 * ease_in_out_cubic(seq_p)
        cam_zoom = 1.08 + 0.24 * ease_in_out_cubic(seq_p)
        crop_w = min(float(sat_img.width), float(W) / cam_zoom)
        crop_h = min(float(sat_img.height), float(H) / cam_zoom)
        x0 = max(0.0, min(float(sat_img.width) - crop_w, cam_cx * sat_img.width - crop_w * 0.5))
        y0 = max(0.0, min(float(sat_img.height) - crop_h, cam_cy * sat_img.height - crop_h * 0.5))
        canvas = sat_img.transform(
            (W, H),
            Image.Transform.EXTENT,
            (x0, y0, x0 + crop_w, y0 + crop_h),
            resample=Image.Resampling.BICUBIC,
        ).convert("RGBA")
        draw_satellite_hud_grid(canvas)
        draw = ImageDraw.Draw(canvas, "RGBA")

        # Top Archival Map Header Banner
        draw.rounded_rectangle([54, 34, 1180, 114], radius=10, fill=(24, 21, 18, 236), outline=VOX_YELLOW + (225,), width=2)
        draw_text_safe(draw, (82, 48), f"위성 지리 추적 // {header_ko}", fill=(250, 204, 21, 255), font_size=28, font_style=h_font)
        draw_text_safe(draw, (82, 82), sub_ko[:58], fill=(224, 213, 194, 235), font_size=19, font_style=t_font)

        # Animated A -> B Trajectory Curve & Distance Ruler
        ax, ay = 390, 620
        bx, by = 1120, 390
        route_p = ease_in_out_cubic(min(1.0, seq_p * 1.45))
        if route_p > 0.02:
            cur_x = int(ax + (bx - ax) * route_p)
            cur_y = int(ay + (by - ay) * route_p)
            draw.line([(ax, ay), (cur_x, cur_y)], fill=VOX_CRIMSON + (245,), width=7)
            draw.ellipse([cur_x - 10, cur_y - 10, cur_x + 10, cur_y + 10], fill=(250, 204, 21, 255))

        # Pin A (Crime Scene / Origin)
        if p0 > 0.05:
            r_pulse = int(22 + 16 * math.sin(seq_p * math.pi * 3))
            draw.ellipse([ax - r_pulse, ay - r_pulse, ax + r_pulse, ay + r_pulse], outline=VOX_CRIMSON + (190,), width=3)
            draw.ellipse([ax - 14, ay - 14, ax + 14, ay + 14], fill=VOX_CRIMSON + (255,), outline=(255, 255, 255, 255), width=3)
            draw.rounded_rectangle([ax - 150, ay + 24, ax + 240, ay + 108], radius=8, fill=VOX_CREAM_CARD + (245,), outline=VOX_INK + (210,), width=2)
            draw_text_safe(draw, (ax - 132, ay + 34), f"① {metrics[0] if metrics else '사건 현장'}", fill=VOX_CRIMSON + (255,), font_size=21, font_style=m_font)
            draw_text_safe(draw, (ax - 132, ay + 64), clauses[0][:24], fill=VOX_INK + (255,), font_size=23, font_style=b_font)

        # Pin B (Suspect Hideout / Target) + Tactile Polaroid Card on Right
        if p1 > 0.05:
            draw.ellipse([bx - 15, by - 15, bx + 15, by + 15], fill=(250, 204, 21, 255), outline=VOX_CRIMSON + (255,), width=4)
            mid_x, mid_y = (ax + bx) // 2 - 90, (ay + by) // 2 - 58
            draw.rounded_rectangle([mid_x, mid_y, mid_x + 220, mid_y + 52], radius=24, fill=VOX_CRIMSON + (245,), outline=(255, 255, 255, 230), width=2)
            dist_txt = metrics[1] if len(metrics) > 1 else (metrics[0] if metrics else "반경 1.5km")
            draw_text_safe(draw, (mid_x + 24, mid_y + 11), f"거리: {dist_txt}", fill=(255, 255, 255, 255), font_size=24, font_style=t_font)

            paste_photo_polaroid(
                canvas,
                img_b,
                (1560, int(410 - (1.0 - p1) * 45)),
                caption=(clauses[1] if len(clauses) > 1 else clauses[0])[:26],
                angle_deg=1.8,
                accent_badge="추적 지점 ②",
            )

        # Clause 3 Bottom Manila Summary Strip (strictly inside y <= 880 subtitle safe zone)
        if p2 > 0.04:
            draw = ImageDraw.Draw(canvas, "RGBA")
            bar_w = int(1640 * p2)
            draw.rounded_rectangle([140, 792, 140 + bar_w, 876], radius=10, fill=VOX_MANILA + (248,), outline=VOX_CRIMSON + (240,), width=3)
            if p2 > 0.35:
                draw_text_safe(draw, (172, 818), f"▶ {clauses[-1][:54]}", fill=VOX_INK + (255,), font_size=28, font_style=h_font)

        draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
        return canvas

    # ==========================================================================
    # GRAMMAR 2: FUNNEL ELIMINATION TREE (15,000 -> Clan -> 1 Suspect)
    # ==========================================================================
    if grammar == "funnel_elimination_tree":
        canvas = get_dark_investigation_desk()
        sheet = get_torn_paper_sheet(1740, 910, fill_rgb=VOX_PAPER, roughness=2.5, seed=seed)
        sdraw = ImageDraw.Draw(sheet, "RGBA")

        # Header
        sdraw.rectangle([48, 36, 1692, 108], fill=VOX_INK + (248,))
        draw_text_safe(sdraw, (76, 52), f"포렌식 수사망 압축 프로파일 // {header_ko}", fill=(250, 204, 21, 255), font_size=30, font_style=h_font)

        # 3-Tier Narrowing Funnel Nodes (Left -> Center -> Right)
        tiers = [
            (90, 170, 460, 660, metrics[0] if metrics else "1단계: 광역 대상", clauses[0], p0, VOX_CREAM_CARD),
            (640, 220, 460, 560, metrics[1] if len(metrics) > 1 else "2단계: 유전자 압축", clauses[1] if len(clauses) > 1 else clauses[0], p1, VOX_MANILA),
            (1190, 270, 460, 460, metrics[2] if len(metrics) > 2 else "최종 특정", clauses[-1], p2, VOX_MEMO_YELLOW),
        ]
        for idx, (tx, ty, tw, th, m_str, c_str, tp, bg_col) in enumerate(tiers):
            if tp <= 0.02:
                continue
            y_off = int((1.0 - tp) * 38)
            bx0, by0, bx1, by1 = tx, ty + y_off, tx + tw, ty + th + y_off
            sdraw.rounded_rectangle([bx0 + 8, by0 + 10, bx1 + 8, by1 + 10], radius=12, fill=(15, 12, 10, 130))
            sdraw.rounded_rectangle([bx0, by0, bx1, by1], radius=12, fill=bg_col + (255,), outline=(VOX_CRIMSON if idx == 2 else VOX_INK) + (240,), width=4 if idx == 2 else 2)
            sdraw.rectangle([bx0, by0, bx1, by0 + 62], fill=(VOX_CRIMSON if idx == 2 else VOX_INK) + (245,))
            draw_text_safe(sdraw, (bx0 + 24, by0 + 14), f"STEP 0{idx + 1} · {m_str[:18]}", fill=(255, 255, 255, 255), font_size=24, font_style=t_font)

            # Thumbnail cutout inside each funnel tier
            thumb = fit_crop(img_a if idx == 0 else img_b, tw - 48, 210)
            sheet.paste(thumb, (bx0 + 24, by0 + 84))
            sdraw = ImageDraw.Draw(sheet, "RGBA")

            wrapped = wrap_text_to_width(c_str, tw - 56, font_size=26, font_style=b_font, max_lines=3)
            for l_i, line in enumerate(wrapped):
                if idx == 2 and l_i == 0:
                    hl_w = int((tw - 56) * tp)
                    sdraw.rectangle([bx0 + 24, by0 + 316 + l_i * 40, bx0 + 24 + hl_w, by0 + 354 + l_i * 40], fill=(250, 204, 21, 165))
                draw_text_safe(sdraw, (bx0 + 28, by0 + 318 + l_i * 40), line, fill=VOX_INK + (255,), font_size=26, font_style=b_font)

            # Funnel narrowing arrows between tiers
            if idx < 2 and tp > 0.5:
                ax0 = bx1 + 12
                ax1 = bx1 + 88
                acy = (by0 + by1) // 2
                sdraw.line([(ax0, acy - 70), (ax1, acy)], fill=VOX_CRIMSON + (230,), width=5)
                sdraw.line([(ax0, acy + 70), (ax1, acy)], fill=VOX_CRIMSON + (230,), width=5)
                sdraw.line([(ax0, acy), (ax1, acy)], fill=VOX_CRIMSON + (255,), width=6)

        if p2 > 0.45:
            _draw_circular_official_seal(sdraw, 1560, 185, dept_ko="과학수사감식", sub_ko="최종일치확정", r=52, alpha=215)

        canvas.paste(sheet, (90, 82), sheet)
        draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=True)
        return canvas

    # ==========================================================================
    # GRAMMAR 3: RELAY CHRONOLOGY CHAIN (Horizontal Camera Pan Across 3 Generations/Eras)
    # ==========================================================================
    if grammar == "relay_chronology_chain":
        canvas = get_cork_pinboard_shell()
        draw = ImageDraw.Draw(canvas, "RGBA")

        # Top Manila Header Strip
        draw.rounded_rectangle([84, 42, 1836, 122], radius=10, fill=VOX_MANILA + (248,), outline=VOX_INK + (220,), width=3)
        _draw_brass_fastener(draw, 130, 82)
        timeline_prefix = "연대기 수사 릴레이 기록 // " if any('\uac00' <= ch <= '\ud7a3' for ch in str(header_ko or "")) else "CHRONOLOGICAL TIMELINE RECORD // "
        draw_text_safe(draw, (170, 62), f"{timeline_prefix}{header_ko}", fill=VOX_INK + (255,), font_size=31, font_style=h_font)

        # Horizontal Crimson Relay Timeline Track across Center
        track_y = 205
        track_w = int(1560 * ease_in_out_cubic(min(1.0, seq_p * 1.25)))
        draw.line([(180, track_y), (180 + track_w, track_y)], fill=VOX_CRIMSON + (245,), width=7)

        for idx in range(3):
            cp = [p0, p1, p2][idx]
            cx = 340 + idx * 620
            draw.ellipse([cx - 18, track_y - 18, cx + 18, track_y + 18], fill=(VOX_CRIMSON if cp > 0.1 else VOX_INK_MUTED) + (255,), outline=VOX_CREAM_CARD + (255,), width=4)
            if cp <= 0.02:
                continue

            card_w, card_h = 540, 640
            card = get_torn_paper_sheet(card_w, card_h, fill_rgb=VOX_CREAM_CARD if idx != 1 else VOX_NEWSPRINT, roughness=2.6, seed=seed + idx * 13)
            cdraw = ImageDraw.Draw(card, "RGBA")
            m_tag = metrics[idx] if idx < len(metrics) else f"기록 0{idx + 1}"
            cdraw.rectangle([28, 24, card_w - 28, 82], fill=(VOX_CRIMSON if idx == 2 else VOX_INK) + (245,))
            draw_text_safe(cdraw, (46, 36), m_tag[:22], fill=(250, 204, 21, 255), font_size=26, font_style=m_font)

            sub_img = fit_crop(img_a if idx % 2 == 0 else img_b, card_w - 56, 260)
            card.paste(sub_img, (28, 102))
            cdraw = ImageDraw.Draw(card, "RGBA")
            _draw_paperclip(cdraw, card_w - 64, 18, tall=52)

            c_str = clauses[idx] if idx < len(clauses) else clauses[-1]
            lines = wrap_text_to_width(c_str, card_w - 68, font_size=27, font_style=b_font, max_lines=4)
            for l_i, line in enumerate(lines):
                ry = 392 + l_i * 46
                if idx == 2 and l_i == 0:
                    cdraw.rectangle([28, ry - 4, 28 + int((card_w - 64) * cp), ry + 36], fill=(250, 204, 21, 160))
                draw_text_safe(cdraw, (34, ry), line, fill=VOX_INK + (255,), font_size=27, font_style=b_font)

            cy_drop = int(248 + (1.0 - cp) * 42)
            canvas.paste(card, (cx - card_w // 2, cy_drop), card)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_pushpin(draw, cx, cy_drop + 16, VOX_CRIMSON if idx == 2 else VOX_YELLOW)

        draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
        return canvas

    # ==========================================================================
    # GRAMMAR 4: DUAL FACADE COLLISION (Opposing Split Comparison + String Link)
    # ==========================================================================
    if grammar == "dual_facade_collision":
        canvas = get_dark_investigation_desk()
        draw = ImageDraw.Draw(canvas, "RGBA")

        # Left Dossier Sheet (Slides in from Left)
        lx = int(76 - (1.0 - p0) * 90)
        left_sheet = get_torn_paper_sheet(820, 696, fill_rgb=VOX_NEWSPRINT, roughness=3.0, seed=seed + 3)
        ldraw = ImageDraw.Draw(left_sheet, "RGBA")
        ldraw.rectangle([32, 24, 788, 82], fill=VOX_INK + (245,))
        draw_text_safe(ldraw, (52, 36), f"[표면 기록] {metrics[0] if metrics else '수사 기록 A'}", fill=(250, 204, 21, 255), font_size=26, font_style=h_font)
        left_sheet.paste(fit_crop(img_a, 756, 360), (32, 102))
        ldraw = ImageDraw.Draw(left_sheet, "RGBA")
        for i, line in enumerate(wrap_text_to_width(clauses[0], 730, font_size=28, font_style=b_font, max_lines=3)):
            draw_text_safe(ldraw, (42, 488 + i * 46), line, fill=VOX_INK + (255,), font_size=28, font_style=b_font)
        canvas.paste(left_sheet, (lx, 68), left_sheet)

        # Right Dossier Sheet (Slides in from Right on Clause 2)
        if p1 > 0.02:
            rx = int(1024 + (1.0 - p1) * 90)
            right_sheet = get_torn_paper_sheet(820, 696, fill_rgb=VOX_MANILA, roughness=3.0, seed=seed + 17)
            rdraw = ImageDraw.Draw(right_sheet, "RGBA")
            rdraw.rectangle([32, 24, 788, 82], fill=VOX_CRIMSON + (248,))
            draw_text_safe(rdraw, (52, 36), f"[실체 대조] {metrics[1] if len(metrics) > 1 else '숨겨진 진실'}", fill=(255, 255, 255, 255), font_size=26, font_style=h_font)
            right_sheet.paste(fit_crop(img_b, 756, 360), (32, 102))
            rdraw = ImageDraw.Draw(right_sheet, "RGBA")
            c1_txt = clauses[1] if len(clauses) > 1 else clauses[0]
            for i, line in enumerate(wrap_text_to_width(c1_txt, 730, font_size=28, font_style=b_font, max_lines=3)):
                rdraw.rectangle([36, 484 + i * 46, 36 + int(730 * p1), 524 + i * 46], fill=(250, 204, 21, 130))
                draw_text_safe(rdraw, (42, 488 + i * 46), line, fill=VOX_INK + (255,), font_size=28, font_style=b_font)
            canvas.paste(right_sheet, (rx, 68), right_sheet)

            # Crimson Tension Connector across Center
            draw = ImageDraw.Draw(canvas, "RGBA")
            draw.line([(486, 96), (1434, 96)], fill=VOX_CRIMSON + (240,), width=6)
            _draw_pushpin(draw, 486, 96, VOX_YELLOW)
            _draw_pushpin(draw, 1434, 96, VOX_CRIMSON)
            draw.rounded_rectangle([845, 376, 1075, 454], radius=12, fill=VOX_INK + (250,), outline=VOX_CRIMSON + (255,), width=4)
            draw_text_safe(draw, (876, 398), "정면 모순 포착", fill=(250, 204, 21, 255), font_size=27, font_style=m_font)

        # Clause 3 Bottom Verdict Banner (strictly inside y <= 880 subtitle safe zone)
        if p2 > 0.04:
            draw = ImageDraw.Draw(canvas, "RGBA")
            draw.rounded_rectangle([76, 788, 1844, 878], radius=12, fill=VOX_CREAM_CARD + (250,), outline=VOX_CRIMSON + (245,), width=3)
            draw.rectangle([76, 788, 96, 878], fill=VOX_CRIMSON + (255,))
            draw_text_safe(draw, (124, 816), clauses[-1][:58], fill=VOX_INK + (255,), font_size=31, font_style=h_font)

        draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
        return canvas

    # ==========================================================================
    # GRAMMAR 5: MACRO FORENSIC LOUPE (Optical Microscope / Specimen / DNA Table)
    # ==========================================================================
    if grammar == "macro_forensic_loupe":
        canvas = get_dark_investigation_desk()
        # Left Forensic Specimen Lightbox
        plate = get_torn_paper_sheet(1740, 890, fill_rgb=VOX_CREAM_CARD, roughness=2.2, seed=seed + 9)
        pdraw = ImageDraw.Draw(plate, "RGBA")
        pdraw.rectangle([40, 32, 1700, 98], fill=VOX_INK + (248,))
        draw_text_safe(pdraw, (68, 46), f"과학수사 정밀 감식 감정서 // {header_ko}", fill=(250, 204, 21, 255), font_size=29, font_style=t_font)

        # Specimen Photo + Animated Magnifying Loupe Sweep
        spec_img = fit_crop(img_a, 780, 680)
        plate.paste(spec_img, (56, 134))
        pdraw = ImageDraw.Draw(plate, "RGBA")
        loupe_cx = int(340 + 210 * math.sin(seq_p * math.pi))
        loupe_cy = int(430 - 90 * math.cos(seq_p * math.pi))
        loupe_r = 165
        zoom_crop = fit_crop(img_a, 1100, 960).crop((loupe_cx, loupe_cy, loupe_cx + loupe_r * 2, loupe_cy + loupe_r * 2))
        mask = Image.new("L", (loupe_r * 2, loupe_r * 2), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, loupe_r * 2, loupe_r * 2], fill=255)
        plate.paste(zoom_crop, (loupe_cx - loupe_r, loupe_cy - loupe_r), mask)
        pdraw = ImageDraw.Draw(plate, "RGBA")
        pdraw.ellipse([loupe_cx - loupe_r, loupe_cy - loupe_r, loupe_cx + loupe_r, loupe_cy + loupe_r], outline=VOX_CRIMSON + (255,), width=6)
        pdraw.line([(loupe_cx - 35, loupe_cy), (loupe_cx + 35, loupe_cy)], fill=(250, 204, 21, 220), width=2)
        pdraw.line([(loupe_cx, loupe_cy - 35), (loupe_cx, loupe_cy + 35)], fill=(250, 204, 21, 220), width=2)

        # Right Telemetry Readout & Clause Rows
        rx0 = 880
        hero_metric = metrics[0] if metrics else "DNA 99.9999%"
        pdraw.rounded_rectangle([rx0, 134, 1684, 294], radius=12, fill=VOX_INK + (248,), outline=VOX_YELLOW + (240,), width=3)
        draw_text_safe(pdraw, (rx0 + 34, 154), "FORENSIC TELEMETRY READOUT", fill=(250, 204, 21, 255), font_size=21, font_style=t_font)
        draw_text_safe(pdraw, (rx0 + 34, 194), hero_metric[:22], fill=(255, 255, 255, 255), font_size=56, font_style=m_font)

        for idx, c_str in enumerate(clauses[:3]):
            cp = [p0, p1, p2][idx]
            if cp <= 0.02:
                continue
            ry = 330 + idx * 155
            pdraw.rounded_rectangle([rx0, ry, 1684, ry + 132], radius=10, fill=VOX_MANILA + (255,), outline=VOX_INK + (210,), width=2)
            hl_w = int(760 * cp)
            pdraw.rectangle([rx0 + 20, ry + 18, rx0 + 20 + hl_w, ry + 56], fill=(250, 204, 21, 155 if idx == 2 else 95))
            m_lbl = metrics[idx] if idx < len(metrics) else f"LOCUS 0{idx + 1}"
            draw_text_safe(pdraw, (rx0 + 28, ry + 22), f"[{m_lbl}]", fill=VOX_CRIMSON + (255,), font_size=23, font_style=t_font)
            for l_i, line in enumerate(wrap_text_to_width(c_str, 740, font_size=26, font_style=b_font, max_lines=2)):
                draw_text_safe(pdraw, (rx0 + 28, ry + 62 + l_i * 32), line, fill=VOX_INK + (255,), font_size=26, font_style=b_font)

        if p2 > 0.35:
            _draw_circular_official_seal(pdraw, 1580, 740, dept_ko="국립과학수사", sub_ko="유전자감식확정", r=54, alpha=220)

        canvas.paste(plate, (90, 88), plate)
        draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=True)
        return canvas

    # ==========================================================================
    # GRAMMAR 6 & 7: MONUMENTAL VERDICT SCROLL / ARCHIVAL PRESS SCATTER
    # ==========================================================================
    canvas = get_dark_investigation_desk()
    is_verdict = grammar == "monumental_verdict_scroll"
    paper_col = VOX_CREAM_CARD if is_verdict else VOX_NEWSPRINT
    sheet = get_torn_paper_sheet(1740, 896, fill_rgb=paper_col, roughness=3.2, seed=seed + 31)
    sdraw = ImageDraw.Draw(sheet, "RGBA")

    # Masthead / Court Header
    banner_col = VOX_CRIMSON if is_verdict else VOX_INK
    sdraw.rectangle([48, 34, 1692, 126], fill=banner_col + (248,))
    title_prefix = "형사 재판부 최종 판결문" if is_verdict else "특종 보도 아카이브"
    draw_text_safe(sdraw, (78, 54), f"{title_prefix} // {header_ko}", fill=(255, 255, 255, 255), font_size=36, font_style=h_font)

    # Left Column: Dual Stacked Evidence Photos
    paste_photo_polaroid(sheet, img_a, (360, 340), caption=metrics[0] if metrics else "기록 자료 #01", angle_deg=-1.6, accent_badge="증거 A")
    if p1 > 0.10:
        paste_photo_polaroid(sheet, img_b, (380, 670), caption=metrics[1] if len(metrics) > 1 else "기록 자료 #02", angle_deg=1.4, accent_badge="증거 B")

    sdraw = ImageDraw.Draw(sheet, "RGBA")
    # Right Column: Editorial Headline + Progressive Highlighter Clauses
    rx0 = 720
    sdraw.line([(680, 154), (680, 840)], fill=VOX_INK_MUTED + (180,), width=3)
    draw_text_safe(sdraw, (rx0, 158), sub_ko[:44], fill=VOX_CRIMSON + (255,), font_size=32, font_style=h_font)

    for idx, c_str in enumerate(clauses[:3]):
        cp = [p0, p1, p2][idx]
        if cp <= 0.02:
            continue
        ry = 236 + idx * 190
        sdraw.rounded_rectangle([rx0, ry, 1676, ry + 162], radius=10, fill=VOX_PAPER + (255,), outline=VOX_INK + (210,), width=2)
        hl_w = int(910 * cp)
        sdraw.rounded_rectangle([rx0 + 22, ry + 20, rx0 + 22 + hl_w, ry + 64], radius=6, fill=(250, 204, 21, 175 if idx == 2 else 110))
        tag_str = metrics[idx] if idx < len(metrics) else f"핵심 요지 0{idx + 1}"
        draw_text_safe(sdraw, (rx0 + 34, ry + 26), f"■ {tag_str}", fill=VOX_INK + (255,), font_size=25, font_style=m_font)
        for l_i, line in enumerate(wrap_text_to_width(c_str, 890, font_size=29, font_style=b_font, max_lines=2)):
            draw_text_safe(sdraw, (rx0 + 34, ry + 76 + l_i * 38), line, fill=VOX_INK + (255,), font_size=29, font_style=b_font)

    if p2 > 0.30:
        _draw_circular_official_seal(
            sdraw,
            1555,
            195,
            dept_ko="최고인민법원" if is_verdict else "사건보존기록",
            sub_ko="집행확정필" if is_verdict else "원본대조필",
            r=56,
            alpha=225,
        )

    canvas.paste(sheet, (90, 86), sheet)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=True)
    return canvas
