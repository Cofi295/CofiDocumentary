"""
Editing DNA Service for CofiDocumentary (Milestone 3).
Defines Editing Style DNA schemas, built-in Remotion presets, extraction from completed projects,
and persistence ("Lock Approved Edit Style to Channel Profile").
"""

from __future__ import annotations

import copy
import json
import os
import statistics
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CHANNEL_PROFILES_FILE = DATA_DIR / "channel_profiles.json"
WORKSPACES_DIR = ROOT / "workspaces"
JOBS_DIR = DATA_DIR / "jobs"

_file_lock = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PacingDict(dict):
    """
    Dictionary representing shot pacing parameters that can also be treated as a float
    for backward compatibility with legacy code.
    """
    def __float__(self) -> float:
        val = self.get("target_beat_duration_sec") or self.get("average_beat_duration_sec") or self.get("typical_pacing_sec") or 5.0
        try:
            return float(val)
        except Exception:
            return 5.0

    def __int__(self) -> int:
        return int(float(self))

    def __round__(self, ndigits: int | None = None):
        return round(float(self), ndigits)


BUILTIN_EDITING_PRESETS: dict[str, dict[str, Any]] = {
    "investigative_counterpoint_vn": {
        "preset_id": "investigative_counterpoint_vn",
        "name": "Giải Phẫu Đại Án Lừa Đảo · Tư Duy Dựng Con Người & Vox Lego Động (Đối Âm Thị Giác & Nhịp Thở)",
        "version": 2,
        "skip_step4_footage": False,
        "human_editorial_grammar": True,
        "motion_text_engine": "FramelessCinemaTextBeat",
        "vox_composable_grammar": {
            "architecture": "3_tier_composable_lego_motion_grammar",
            "atomic_props_count": 25,
            "visual_verbs_count": 18,
            "camera_topologies_count": 8,
            "verb_sliding_window": 5,
            "camera_topology_sliding_window": 3,
            "max_monolithic_page_wrapper_uses": 3,
            "max_flat_horizontal_conveyor_scenes": 3,
        },
        "pacing": PacingDict({
            "target_beat_duration_sec": 4.2,
            "typical_pacing_sec": 4.2,
            "shot_range_sec": [2.4, 6.8],
            "average_beat_duration_sec": 4.2,
            "max_routine_shot_sec": 7.5,
            "pacing_curve": "rhythm_staircase_with_pre_impact_silence",
            "pacing_wpm": 148.0,
        }),
        "visual_mix": {
            "footage": 0.60,
            "motion": 0.25,
            "ai": 0.15,
            "footage_ratio": 0.60,
            "motion_overlay_ratio": 0.25,
            "ai_visual_ratio": 0.15,
            "preferred_routing": "edit_direct_footage",
        },
        "editing_archetypes": [
            "GILDED_TRAP_TO_COLD_SLATE_ARC: Hồi 1 mồi nhử ấm vàng sang trọng -> Cú sập sàn ngắt nhạc 0.8s + tụt màu xám lạnh thép",
            "VISUAL_COUNTERPOINT_CUT: Đối âm thị giác (Lời hứa hào nhoáng cắt thẳng 0-frame sang hiện trường mục ruỗng/đóng băng)",
            "EYE_VERIFIED_FOOTAGE_SOURCING: AI Agent dùng mắt thật kiểm duyệt Storyboard, lưới 100px & Contact Sheet 3-frame (15%-50%-85%), crop sạch 100% logo/chữ chạy bên khác, khớp 100% câu voice, 0% cắt ghép tự động",
            "VOX_COMPOSABLE_LEGO_GRAMMAR_V13: Đồ họa giải phẫu cơ chế 3 Tầng Lego (đạo cụ rời theo skin điều tra Việt Nam × 18 Động từ thị giác @voxVerb × 8 Hướng lia máy tự do @voxCamera khớp Whisper words[], 0 lặp động từ trong 5 cảnh, <= 3 khung nguyên trang/tập)",
            "FINCHER_MOTIVATED_CAMERA_AND_SPLIT_EDITS: 90%+ Hard Cut 0-frame + J-Cut / L-Cut + 1.0x Static Tripod ở cảnh nỗi đau nạn nhân + 2.4s Khoảng thở chuyển Hồi",
        ],
        "subtitle_style": {
            "font_family": "Be Vietnam Pro",
            "font_size": 46,
            "font_size_px": 46,
            "font_weight": 800,
            "color": "#F8FAFC",
            "base_color": "#F8FAFC",
            "highlight_color": "#FACC15",
            "stroke_color": "rgba(8, 10, 15, 0.96)",
            "stroke_width": 5.0,
            "background": "transparent",
            "frameless": True,
            "position": "bottom_center",
        },
        "color_grade": {
            "tone_preset": "act_evolving_gilded_to_slate",
            "lut_name": "per_clip_signalstats_normalized",
            "vignette_opacity": 0.68,
            "film_grain": 0.05,
        },
        "audio_rules": {
            "bgm_volume_db": -20.0,
            "ducking_db": -10.0,
            "music_ducking_db": -10.0,
            "room_tone_db": -41.0,
            "act_bridge_silence_sec": 2.4,
            "cold_open_pre_voice_sec": 1.35,
            "outro_tail_sec": 3.8,
            "sfx_hit_on_chapter": True,
            "sfx_motion_bound_vox_map_only": True,
        },
        "editorial_rules": [
            "Every shot must satisfy Murch Three-Jobs Law (advance info, shift emotion, or raise pressure)",
            "Enforce Coverage Scale Ladder (Wide -> Medium -> Close-Up -> Macro) with zero adjacent same-scale/same-subject jump cuts",
            "Choreograph all mechanism/map Vox scenes using the 3-Tier Composable Lego Motion Grammar (18 @voxVerb × 8 @voxCamera synced to Whisper words[], frame(15%) != frame(50%) != frame(85%), 0 verb repeats in 5 scenes, 0 camera repeats in 3 scenes)",
            "Use 90%+ 0-frame Hard Cuts smoothed by J-Cut/L-Cut split edits and 2.4s voiceless Act Breathing Bridges with -41dBFS room-tone floor",
        ],
    },
    "2.5d_technical": {
        "preset_id": "2.5d_technical",
        "name": "2.5D Technical & Infrastructure Investigation (Composable Lego Grammar)",
        "version": 2,
        "motion_text_engine": "FramelessCinemaTextBeat",
        "vox_engine_package": "CofiRemotion/src/vox-studio/VoxComposablePrimitives.tsx",
        "vox_composable_grammar": {
            "architecture": "3_tier_composable_lego_motion_grammar",
            "atomic_props_count": 25,
            "visual_verbs_count": 18,
            "camera_topologies_count": 8,
            "verb_sliding_window": 5,
            "camera_topology_sliding_window": 3,
            "max_monolithic_page_wrapper_uses": 3,
            "max_flat_horizontal_conveyor_scenes": 3,
        },
        "pacing": PacingDict({
            "target_beat_duration_sec": 4.5,
            "typical_pacing_sec": 4.5,
            "shot_range_sec": [3.5, 7.0],
            "average_beat_duration_sec": 4.5,
            "max_routine_shot_sec": 8.0,
            "pacing_curve": "accelerating_towards_act_climax",
            "pacing_wpm": 140.0,
        }),
        "visual_mix": {
            "footage": 0.50,
            "ai": 0.30,
            "motion": 0.20,
            "footage_ratio": 0.50,
            "ai_visual_ratio": 0.30,
            "motion_overlay_ratio": 0.20,
            "preferred_routing": "hybrid",
        },
        "editing_archetypes": [
            "CLEAN_INFRASTRUCTURE_FOOTAGE_BACKBONE: ~50% 3-frame verified engineering, construction, hydrological, and site footage (3.0–5.0s/cut, max_uses=1, 0% logos/foreign subs/hosts)",
            "VOX_COMPOSABLE_LEGO_GRAMMAR_V13 (Technical & Geotechnical Blueprint Skin): ~20% Composable Lego Vox & 3D Esri+OSM GIS stages (#071320 deep blueprint slate, #38BDF8 ice-cyan CAD vectors, cross-section elevation/stress props × 18 @voxVerb × 8 @voxCamera synced to Whisper words[], 0 verb repeats in 5 scenes, 0 camera repeats in 3 scenes, <= 3 full-page wrappers)",
            "SCENE_LOCKED_ENGINEERING_AI_KEYFRAMES: ~30% 1-to-1 structural/geological AI keyframes ({bid}_ai_keyframe.jpg, max_uses=1) with frameless reconstruction disclosure",
        ],
        "subtitle_style": {
            "font_family": "Pretendard",
            "font_size": 52,
            "font_size_px": 52,
            "color": "#FFFFFF",
            "base_color": "#FFFFFF",
            "highlight_color": "#38BDF8",
            "stroke_color": "#000000",
            "stroke_width": 6,
            "background": "transparent",
            "frameless": True,
            "position": "bottom_center",
        },
        "color_grade": {
            "tone_preset": "technical_cool_cyan",
            "lut_name": "clean_broadcast_cool",
            "vignette_opacity": 0.75,
        },
        "audio_rules": {
            "bgm_volume_db": -22.0,
            "ducking_db": -12.0,
            "music_ducking_db": -12.0,
            "target_lufs": -18.0,
            "sfx_chapter_hit": True,
            "sfx_hit_on_chapter": True,
            "telemetry_beeps": True,
            "sfx_motion_bound_vox_map_only": True,
            "tension_drone_under_interrogation": False,
        },
        "editorial_rules": [
            "Lock technical cyan/slate engineering skin (#071320 blueprint slate, #38BDF8 vectors) isolated from True Crime newsprint styles",
            "Choreograph every technical diagram and 3D Esri+OSM GIS stage via the 3-Tier Composable Lego Motion Grammar (loose engineering/geospatial props × 18 @voxVerb × 8 @voxCamera synced to Whisper words[], frame(15%) != frame(50%) != frame(85%), 0 verb repeats in 5 consecutive VOX scenes, 0 camera repeats in 3 consecutive VOX scenes)",
            "Score 8-Mood Story-Arc BGM (-18 LUFS, -41dBFS room-tone floor on pre-twist drops) and emit 100% Motion-Bound SFX on Vox/GIS/Chapter primitives only",
        ],
    },
    "forensic_noir_director_v2": {
        "preset_id": "forensic_noir_director_v2",
        "director_mode": "v2",
        "name": "Tactile Vox Editorial Desk (vox-editorial-desk) + Voice-to-Vox Prompt Compiler + 3D Parabolic Satellite GIS + 50%+ Semantic-Verified Case Archival Footage",
        "version": 24,
        "motion_text_engine": "FramelessCinemaTextBeat",
        "motion_text_module": "CofiRemotion/src/components/FramelessCinemaTextBeat.tsx",
        "vox_engine_package": "CofiRemotion/src/vox-studio/vox-editorial-desk",
        "vox_composable_grammar": {
            "architecture": "voice_to_vox_prompt_x_tactile_editorial_desk_and_3d_gis",
            "pillars": [
                "pillar_1_voice_to_vox_prompt_compiler",
                "pillar_2_tactile_vox_editorial_desk_10_archetypes",
                "pillar_3_pixel_coordinate_100px_grid_calibration",
                "pillar_4_web_mercator_osrm_osm_3d_parabolic_gis",
            ],
            "atomic_props_count": 32,
            "visual_verbs_count": 18,
            "camera_topologies_count": 8,
            "verb_sliding_window": 5,
            "camera_topology_sliding_window": 3,
            "max_monolithic_page_wrapper_uses": 3,
            "max_flat_horizontal_conveyor_scenes": 3,
            "min_camera_travel_px": 180,
            "max_geo_polyline_jump_deg": 0.004,
            "require_die_cut_sticker_props": True,
            "require_torn_blueprint_scraps": True,
            "forbid_cross_project_prop_copy": True,
            "forbid_uniform_3col_script_cloning": True,
            "require_real_camera_travel_and_focus_windows": True,
        },
        "footage_hygiene_contract": {
            "default_crop_mode": "eye_calibrated_per_source_safe_crop",
            "crop_filter": "crop=iw*0.84:ih*0.70:iw*0.08:ih*0.12,scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080",
            "min_intro_skip_sec": 28.0,
            "min_outro_margin_sec": 22.0,
            "forbid_studio_hosts_and_anchors": True,
            "forbid_channel_logos_and_watermarks": True,
            "forbid_burned_in_subtitles_and_tickers": True,
            "forbid_qr_codes_and_endcards": True,
            "require_100px_grid_calibration": True,
            "require_3frame_contact_sheet_audit": True,
            "require_storyboard_probe_before_cut": True,
            "require_eye_verified_observed_content": True,
            "forbid_blind_auto_offset_cut": True,
            "forbid_cross_project_footage_copy": True,
            "require_focal_subject_crop_calibration": True,
        },
        "pacing": PacingDict({
            "target_beat_duration_sec": 5.5,
            "typical_pacing_sec": 5.5,
            "shot_range_sec": [3.0, 5.0],
            "average_beat_duration_sec": 5.5,
            "max_routine_shot_sec": 8.0,
            "pacing_curve": "tense_investigative_newsroom_suspense",
            "pacing_wpm": 135.0,
        }),
        "visual_mix": {
            "footage": 0.54,
            "motion": 0.30,
            "ai": 0.16,
            "footage_ratio": 0.54,
            "motion_overlay_ratio": 0.30,
            "vox_newsroom_ratio": 0.20,
            "cinema_text_ratio": 0.10,
            "ai_visual_ratio": 0.16,
            "min_footage_floor": 0.50,
            "max_vox_scene_ratio": 0.28,
            "max_cinema_text_ratio": 0.16,
            "max_ai_reconstruction_ratio": 0.22,
            "semantic_verified_footage_routing": True,
            "zero_unrelated_broll": True,
            "preferred_routing": "edit_direct_footage",
        },
        "editing_archetypes": [
            "AUTHENTIC_CASE_ARCHIVAL_FOOTAGE_BACKBONE: >=50% (~50%–56% số beat, min_footage_floor = 0.50, semantic_verified_footage_routing: chỉ dùng tư liệu thật khi khớp ngữ nghĩa 100% với voice_text, 0% footage đệm lạc đề; beat thiếu tư liệu khớp nghĩa tự động chuyển sang VOX tối đa 35% hoặc AI_4D tối đa 28%) tư liệu thật của chính vụ án, công an điều tra, pháp y, tòa án & đúng địa danh lịch sử; bắt buộc chạy --probe-storyboard để nhìn bằng mắt thật (read_file) trên bảng STORYBOARD_<id>.jpg + lưới tọa độ 100px (GRID_<id>.jpg), chọn đúng giây start_offset_sec khớp câu thoại, căn chỉnh crop=W:H:X:Y (hoặc focus_top / focus_bottom / focus_left / focus_right / forensic_v2_clean) focus đúng trọng tâm chủ thể & cắt sạch 4 cạnh, ghi rõ --observed-content (eye_verified=true, 0% cắt mù hàng loạt blind_auto_offset, 0% copy clip từ dự án khác), bỏ qua >=28s đầu & >=22s cuối video gốc và kiểm duyệt mắt 3 frame (15%-50%-85% trên VERIFY_FTG_CLIPS_*.jpg) đảm bảo 0% Intro/Outro, 0% người dẫn chương trình/MC trường quay, 0% tên kênh/logo/watermark, 0% phụ đề ngoại ngữ và 0% mã QR (max_uses=1, dHash>=14, 3.0–5.0s/cut, Part A + Part B cho beat >= 6.2s)",
            "TACTILE_VOX_EDITORIAL_DESK_AND_3D_GIS_VOX: 18%–24% (tối đa 28%, hoặc lên tới 35% khi semantic_verified_footage_routing động chuyển beat thiếu footage khớp nghĩa sang VOX, ~38–46 cảnh/tập 27p) Thiết kế VOX Chuẩn Báo Chí Điều Tra (Voice-to-Vox Prompt Compiler × Fixed-Style Tactile Editorial Desk src/vox-studio/vox-editorial-desk/index.tsx + 10 Editorial Desk Archetypes + Bản Đồ Vệ Tinh 3D <GeoJson3DMapStage>): (1) Quy trình 3 bước cho từng câu voice (t1 -> t2 -> t3): phân tích nghĩa câu nói (voice_meaning) -> xác định chi tiết vật lý cần minh họa bổ trợ (illustration_content) -> sinh vox_prompt độc bản 1-to-1; (2) Khóa cố định phong cách bàn biên tập cắt dán thủ công (FIXED_VOX_STYLE: mặt bàn giấy biên tập ấm #E4DDCF + hạt giấy tĩnh #voxGrain opacity: 0.22 + thẻ đen tương phản <BlackCard inset={38}> #1B1B1A cho cú ngoặt kịch tính + 3 màu trung tính #EEEDED/#1B1B1A/#171716 + 2 màu nhấn #B8433F đỏ manh mối & #DACF08 vàng dạ quang multiply + camera 30fps <World cam={camAt(...)}> với dịch chuyển camera thực tế non-static camera delta + đạo cụ cắt dán/nét vẽ tay 12fps step12/p12: <SlideIn>, <VoxVideoPaper>, <VoxPhotoPaper>, <DieCutSticker> tách nền RGBA thật sự, <TornClipping>, <IndexCard>, <Stamp>, <Label>, <Highlight>, <RedLine>, <RedCircle>, <Underline>, <DimensionBracket>, <OpticalLoupe>, <Tape> luân phiên 10 Editorial Desk Archetypes; 0% đóng khung dashboard hộp chữ cứng nhắc như BroadcastCleanSpatialDiagram hay STEP 01/02); (3) Định vị tọa độ chính xác trên lưới 100px (read_file) đảm bảo mọi vòng khoanh đỏ, mũi tên, thước đo và kính lúp khóa trúng 100% chi tiết vật lý mục tiêu (0px lệch, giữ 30%–40% khoảng trống thở trong [60..1860, 40..820]); (4) Bản đồ vệ tinh 3D Quỹ đạo Parabol FlyTo (<GeoJson3DMapStage> khóa Web Mercator 0.00px + đường thực OSRM/OSM >= 12 đỉnh + bóng đổ 3D tuyến đường + kính lúp vệ tinh 4x + mảnh cắt dán tư liệu thật bật lên tại điểm mốc) cho các câu địa lý/lộ trình.",
            "NATURAL_EDITORIAL_CINEMA_TEXT_BEAT: 8%–12% (tối đa 16%, ~18–24 beat/tập 27p) CofiRemotion/src/components/FramelessCinemaTextBeat.tsx Typography biên tập viên tự nhiên (editorial_punch_statement, editorial_metric_monolith, editorial_rhetorical_question) trên nền ảnh tư liệu thật làm tối dịu ở câu hỏi nghịch lý, con số chấn động hoặc điểm gãy chuyển Hồi (không đặt 2 beat liền kề, tự động ẩn <SubtitleOverlay> bên dưới)",
            "CLOSED_ROOM_PROFILE_AI_RECONSTRUCTION: 12%–18% (tối đa 22%, hoặc lên tới 28% khi semantic_verified_footage_routing) Ảnh AI dự phòng 1-to-1 ({bid}_ai_keyframe.jpg, max_uses=1) chỉ dùng cho hành vi/tâm lý góc kín không có máy quay thật kèm nhãn minh bạch không khung '재연 · 이해를 돕기 위한 이미지'",
        ],
        "subtitle_style": {
            "font_family": "Pretendard ExtraBold",
            "font_size": 64,
            "font_size_px": 64,
            "font_weight": 800,
            "color": "#F8F6F0",
            "base_color": "#F8F6F0",
            "highlight_color": "#FDE047",
            "stroke_color": "rgba(8, 8, 10, 0.96)",
            "stroke_width": 6.5,
            "stroke_width_px": 6.5,
            "background": "transparent",
            "frameless": True,
            "clause_max_chars": 16,
            "position": "bottom_center",
            "subtitle_safe_zone_max_y": 785,
        },
        "color_grade": {
            "tone_preset": "warm_newsprint_investigative_noir",
            "lut_name": "newsroom_contrast_clean",
            "vignette_opacity": 0.65,
            "film_grain": 0.06,
        },
        "audio_rules": {
            "bgm_volume_db": -22.0,
            "ducking_db": -12.0,
            "music_ducking_db": -12.0,
            "target_lufs": -14.8,
            "telemetry_beeps": False,
            "sfx_hit_on_chapter": True,
            "sfx_motion_bound_vox_map_only": True,
            "outro_tail_hold_sec": 3.8,
            "outro_bgm_fade_out_sec": 3.5,
            "zero_closing_narration_cutoff": True,
        },
        "editorial_rules": [
            "Curate >= 50% (~50%–56%, min_footage_floor = 0.50) authentic case archival footage when 100% semantically matched to voice_text under semantic_verified_footage_routing (0% filler/mismatched footage; any beat without 100% semantically matching real footage dynamically routes to VOX up to 35% or AI_4D up to 28%), probed via --probe-storyboard (STORYBOARD_*.jpg + 100px GRID_*.jpg), focal-cropped onto the visual subject (crop=W:H:X:Y / focus_top/bottom/left/right) with --observed-content (eye_verified = true, 0% blind_auto_offset, 0% cross-project clip copy) and verified on 15%-50%-85% contact sheets so ZERO third-party intros, studio hosts/anchors, channel logos/watermarks, burned-in foreign subtitles/text, QR codes, or unrelated B-roll appear",
            "Choreograph 18%–24% TACTILE_VOX_EDITORIAL_DESK_AND_3D_GIS_VOX scenes (src/vox-studio/vox-editorial-desk/index.tsx, warm editorial paper desk #E4DDCF + #voxGrain opacity: 0.22 + <BlackCard inset={38}> #1B1B1A + 3 neutrals #EEEDED/#1B1B1A/#171716 + 2 accents #B8433F & #DACF08 + 30fps <World cam={camAt(...)}> with non-static camera delta + 12fps step12 paper/ink props + 10 Editorial Desk Archetypes + <GeoJson3DMapStage>) tailored 1-to-1 to each spoken sentence and verified on the 100px grid via read_file.",
            "Deploy dark FramelessCinemaTextBeat.tsx (~8%–12%) at climax turning points and preserve 100% closing narration + 3.8s BGM fade-out",
        ],
    },
    "forensic_noir": {
        "preset_id": "forensic_noir",
        "name": "Tactile Vox Editorial Desk (vox-editorial-desk) + 3-Tier Composable Lego Vox Motion Grammar (KR 30m)",
        "version": 14,
        "motion_text_engine": "FramelessCinemaTextBeat",
        "motion_text_module": "CofiRemotion/src/components/FramelessCinemaTextBeat.tsx",
        "vox_engine_package": "CofiRemotion/src/vox-studio/vox-editorial-desk",
        "vox_composable_grammar": {
            "architecture": "voice_to_vox_prompt_x_tactile_editorial_desk_and_3d_gis",
            "atomic_props_count": 25,
            "visual_verbs_count": 18,
            "camera_topologies_count": 8,
            "verb_sliding_window": 5,
            "camera_topology_sliding_window": 3,
            "max_monolithic_page_wrapper_uses": 3,
            "max_flat_horizontal_conveyor_scenes": 3,
        },
        "pacing": PacingDict({
            "target_beat_duration_sec": 5.5,
            "typical_pacing_sec": 5.5,
            "shot_range_sec": [3.0, 5.0],
            "average_beat_duration_sec": 5.5,
            "max_routine_shot_sec": 8.0,
            "pacing_curve": "tense_investigative_suspense",
            "pacing_wpm": 135.0,
        }),
        "visual_mix": {
            "footage": 0.55,
            "motion": 0.25,
            "ai": 0.20,
            "footage_ratio": 0.55,
            "motion_overlay_ratio": 0.25,
            "ai_visual_ratio": 0.20,
            "min_footage_floor": 0.50,
            "max_vox_scene_ratio": 0.28,
            "semantic_verified_footage_routing": True,
            "preferred_routing": "edit_direct_footage",
        },
        "editing_archetypes": [
            "CLEAN_CASE_FOOTAGE_BACKBONE (~50%–56%, min_footage_floor = 0.50, semantic_verified_footage_routing): Tư liệu thật của vụ án & bối cảnh cùng quốc gia sạch 3-frame khi khớp ngữ nghĩa 100% với voice_text (0% footage đệm lạc đề; beat thiếu tư liệu khớp nghĩa tự động chuyển sang VOX tối đa 35% hoặc AI_4D tối đa 28%, 12%-50%-85%, 3.0–4.8s/cut, max_uses=1, 0% logo/phụ đề ngoại ngữ/MC)",
            "TACTILE_VOX_EDITORIAL_DESK_AND_3D_GIS_VOX (~18%–24%, tối đa 28% hoặc 35% khi semantic_verified_footage_routing): Bàn Biên Tập Cắt Dán Chuẩn Vox (src/vox-studio/vox-editorial-desk/index.tsx: nền bàn giấy ấm #E4DDCF + #voxGrain opacity: 0.22 + <BlackCard inset={38}> #1B1B1A + 3 màu trung tính #EEEDED/#1B1B1A/#171716 + 2 màu nhấn #B8433F & #DACF08 + camera 30fps <World cam={camAt(...)}> non-static camera delta + đạo cụ cắt dán/nét vẽ 12fps step12 + 10 Editorial Desk Archetypes + <GeoJson3DMapStage> vùng an toàn [60..1860, 40..820])",
            "FRAMELESS_CINEMA_TEXT_BEAT (~8%–12%): Chữ điện ảnh tối không khung ở câu hỏi nghịch lý & điểm chuyển Hồi (0 đặt 2 beat sát nhau, tự ẩn SubtitleOverlay)",
            "CLOSED_ROOM_4D_FACELESS_AI (~12%–18%, tối đa 28% khi semantic_verified_footage_routing): Ảnh AI 4D Faceless Forensic ({bid}_ai_keyframe.jpg, max_uses=1) cho hành vi góc kín kèm nhãn '재연 · 이해를 돕기 위한 이미지'",
            "BROADCAST_SUBTITLE_AND_SOUND_DIRECTOR: Phụ đề 52px Pretendard ExtraBold không đóng hộp (#FDE047 highlight); 8-Mood Story-Arc BGM (-18 LUFS, nền -41dBFS khi hạ nhạc trước twist) + Motion-Bound SFX; câu kết trọn vẹn + 3.8s BGM fade-out",
        ],
        "subtitle_style": {
            "font_family": "Pretendard ExtraBold",
            "font_size": 52,
            "font_size_px": 52,
            "font_weight": 800,
            "color": "#F8F6F0",
            "base_color": "#F8F6F0",
            "highlight_color": "#FDE047",
            "stroke_color": "rgba(8, 8, 10, 0.96)",
            "stroke_width": 5.5,
            "stroke_width_px": 5.5,
            "background": "transparent",
            "frameless": True,
            "clause_max_chars": 16,
            "position": "bottom_center",
            "subtitle_safe_zone_max_y": 835,
        },
        "color_grade": {
            "tone_preset": "warm_newsprint_investigative_noir",
            "lut_name": "newsroom_contrast_clean",
            "vignette_opacity": 0.65,
            "film_grain": 0.06,
        },
        "audio_rules": {
            "bgm_volume_db": -22.0,
            "ducking_db": -12.0,
            "music_ducking_db": -12.0,
            "target_lufs": -18.0,
            "tension_drone": False,
            "tension_drone_under_interrogation": False,
            "heartbeat_riser": False,
            "sfx_hit_on_chapter": True,
            "sfx_motion_bound_vox_map_only": True,
            "outro_tail_hold_sec": 3.8,
            "outro_bgm_fade_out_sec": 3.5,
            "zero_closing_narration_cutoff": True,
        },
        "editorial_rules": [
            "All crime depictions must strictly follow After-the-Storm forensic framing (100% YouTube Green Monetization, zero graphic gore)",
            "Latest Voice Sync Law: Verify mtime, duration, and sha256 of newest narration.wav + voice_manifest.json, sync to public/jobs/<job_id>/audio/narration.wav, rebuild subtitles.srt + clauseWindows, and clear stale .m4a/chunk caches before editing or exporting",
            "Choreograph all Vox scenes via VOX_COMPOSABLE_LEGO_GRAMMAR_DIRECTOR_V13: loose tactile dossier props × 18 Semantic Visual Verbs (@voxVerb) × 8 Free-Space Camera Topologies (@voxCamera) synced to Whisper words[] (0 verb repeats in 5 scenes, 0 camera repeats in 3 scenes, <= 3 full-page wrappers, y <= 835px)",
            "REMOTION_MASTER_EDITOR_ROLE: Curate ~55%-60% 3-frame verified clean case & contextual footage (3.0-4.8s/cut, max_uses=1, 0% logos/foreign subs/TV anchors) and reserve 1-to-1 AI keyframes (10%-15%) strictly for closed-room moments with frameless '재연 · 이해를 돕기 위한 이미지' disclosure",
            "BROADCAST_SUBTITLE_AND_SOUND_DIRECTOR: 52px frameless Pretendard ExtraBold subtitles, 8-Mood Story-Arc BGM (-18 LUFS, 3s crossfades, -41dBFS pre-twist floor), 100% motion-bound SFX on Vox/Satellite Maps/Chapter transitions only, and 100% complete closing narration + 3.8s outro BGM fade-out",
        ],
    },
    "archival_historical": {
        "preset_id": "archival_historical",
        "name": "Archival Historical Vault (Composable Lego Grammar)",
        "version": 2,
        "motion_text_engine": "FramelessCinemaTextBeat",
        "vox_engine_package": "CofiRemotion/src/vox-studio/VoxComposablePrimitives.tsx",
        "vox_composable_grammar": {
            "architecture": "3_tier_composable_lego_motion_grammar",
            "atomic_props_count": 25,
            "visual_verbs_count": 18,
            "camera_topologies_count": 8,
            "verb_sliding_window": 5,
            "camera_topology_sliding_window": 3,
            "max_monolithic_page_wrapper_uses": 3,
            "max_flat_horizontal_conveyor_scenes": 3,
        },
        "pacing": PacingDict({
            "target_beat_duration_sec": 5.0,
            "typical_pacing_sec": 5.0,
            "shot_range_sec": [3.5, 7.5],
            "average_beat_duration_sec": 5.0,
            "max_routine_shot_sec": 8.5,
            "pacing_curve": "measured_documentary_historical",
            "pacing_wpm": 135.0,
        }),
        "visual_mix": {
            "footage": 0.65,
            "ai": 0.20,
            "motion": 0.15,
            "footage_ratio": 0.65,
            "ai_visual_ratio": 0.20,
            "motion_overlay_ratio": 0.15,
            "preferred_routing": "evidence_footage",
        },
        "editing_archetypes": [
            "ARCHIVAL_VAULT_FOOTAGE_AND_STILLS: ~65% verified historical/presidential/intelligence footage & primary archival photographs (3.5–5.0s/cut, max_uses=1)",
            "VOX_COMPOSABLE_LEGO_GRAMMAR_V13 (Declassified Archival Parchment Skin): ~15% loose declassified dossier props, optical loupes (imageSrc=), redaction strips, seals, timelines & 3D Esri+OSM GIS maps choreographed across 18 @voxVerb × 8 @voxCamera synced to Whisper words[] (0 verb repeats in 5 scenes, 0 camera repeats in 3 scenes, <= 3 full-page wrappers)",
            "HISTORICAL_RECONSTRUCTION_AI_KEYFRAMES: ~20% period-accurate AI reconstructions ({bid}_ai_keyframe.jpg, max_uses=1) with frameless archival disclosure",
        ],
        "subtitle_style": {
            "font_family": "Inter",
            "font_size": 44,
            "font_size_px": 44,
            "color": "#F8FAFC",
            "base_color": "#F8FAFC",
            "highlight_color": "#F59E0B",
            "stroke_color": "#000000",
            "stroke_width": 6,
            "background": "transparent",
            "frameless": True,
            "position": "bottom_center",
        },
        "color_grade": {
            "tone_preset": "archival_warm_vintage",
            "lut_name": "kodachrome_warm",
            "vignette_opacity": 0.65,
            "sepia_warmth": 0.15,
        },
        "audio_rules": {
            "bgm_volume_db": -18.0,
            "ducking_db": -10.0,
            "music_ducking_db": -10.0,
            "target_lufs": -18.0,
            "typewriter_sfx": True,
            "film_reel_hum": True,
            "sfx_hit_on_chapter": True,
            "sfx_motion_bound_vox_map_only": True,
            "tension_drone_under_interrogation": False,
        },
        "editorial_rules": [
            "Lock warm archival parchment & declassified vault skin isolated to target market language",
            "Choreograph declassified document autopsies, redaction reveals, and historical maps via the 3-Tier Composable Lego Motion Grammar (18 @voxVerb × 8 @voxCamera, frame(15%) != frame(50%) != frame(85%), 0 verb repeats in 5 scenes, 0 camera repeats in 3 scenes)",
            "Emit Motion-Bound SFX exclusively at graphic/stamp/map frame offsets and score 8-Mood Story-Arc BGM (-18 LUFS)",
        ],
    },
    "custom": {
        "preset_id": "custom",
        "name": "Custom Profile Recipe",
        "version": 1,
        "pacing": PacingDict({
            "target_beat_duration_sec": 5.0,
            "typical_pacing_sec": 5.0,
            "shot_range_sec": [3.0, 8.0],
            "average_beat_duration_sec": 5.0,
            "max_routine_shot_sec": 8.0,
            "pacing_curve": "standard_documentary",
            "pacing_wpm": 135.0,
        }),
        "visual_mix": {
            "footage": 0.33,
            "ai": 0.33,
            "motion": 0.34,
            "footage_ratio": 0.33,
            "ai_visual_ratio": 0.33,
            "motion_overlay_ratio": 0.34,
            "preferred_routing": "hybrid",
        },
        "editing_archetypes": [
            "custom_overlay",
            "chapter_title_card",
        ],
        "subtitle_style": {
            "font_family": "Inter",
            "font_size": 42,
            "font_size_px": 42,
            "color": "#FFFFFF",
            "base_color": "#FFFFFF",
            "highlight_color": "#38BDF8",
            "stroke_color": "#000000",
            "stroke_width": 16,
            "position": "bottom_center",
        },
        "color_grade": {
            "tone_preset": "neutral",
            "lut_name": "clean_natural",
            "vignette_opacity": 0.70,
        },
        "audio_rules": {
            "bgm_volume_db": -20.0,
            "ducking_db": -12.0,
            "music_ducking_db": -12.0,
            "sfx_hit_on_chapter": True,
            "tension_drone_under_interrogation": False,
        },
        "editorial_rules": [
            "Maintain voice-visual alignment within 0.3s tolerance",
            "Anti-repetitive hold limits apply to all beats",
        ],
    },
    "financial_forensic_vox": {
        "preset_id": "financial_forensic_vox",
        "name": "Cyber-Financial Forensic Audit Skin + 3-Tier Composable Lego Vox Motion Grammar (KR 45–70)",
        "version": 13,
        "description": "Cyber-Financial & On-Chain Forensic Documentary Architecture: ~48% 3-Frame Verified Case/Contextual Footage + ~24% 3-Tier Composable Lego Financial/Geo Vox Motion (#040C18 midnight audit slate, #38BDF8 ice-cyan & #FACC15 amber vectors, 18 @voxVerb × 8 @voxCamera) + ~8% FramelessCinemaTextBeat + ~20% 4D Faceless Forensic AI Keyframes.",
        "motion_text_engine": "FramelessCinemaTextBeat",
        "motion_text_module": "CofiRemotion/src/components/FramelessCinemaTextBeat.tsx",
        "vox_engine_package": "CofiRemotion/src/vox-studio/VoxComposablePrimitives.tsx",
        "vox_composable_grammar": {
            "architecture": "3_tier_composable_lego_motion_grammar",
            "atomic_props_count": 25,
            "visual_verbs_count": 18,
            "camera_topologies_count": 8,
            "verb_sliding_window": 5,
            "camera_topology_sliding_window": 3,
            "max_monolithic_page_wrapper_uses": 3,
            "max_flat_horizontal_conveyor_scenes": 3,
        },
        "pacing": PacingDict({
            "target_beat_duration_sec": 5.4,
            "typical_pacing_sec": 5.4,
            "shot_range_sec": [3.2, 6.5],
            "average_beat_duration_sec": 5.4,
            "max_routine_shot_sec": 8.5,
            "pacing_curve": "accelerating_towards_act_climax",
            "pacing_wpm": 135.0,
        }),
        "visual_mix": {
            "footage": 0.45,
            "motion": 0.30,
            "ai": 0.25,
            "footage_ratio": 0.45,
            "motion_overlay_ratio": 0.30,
            "ai_visual_ratio": 0.25,
            "max_vox_scene_ratio": 0.28,
            "preferred_routing": "full_ai",
        },
        "editing_archetypes": [
            "CLEAN_FINANCIAL_CASE_FOOTAGE_BACKBONE (~45%–52%): Tư liệu thật của chính vụ án tài chính/công nghệ cao & bối cảnh ngân hàng/server/tòa án sạch 3-frame (3.0–5.0s/cut, max_uses=1, 0% logo/phụ đề ngoại ngữ/MC)",
            "VOX_COMPOSABLE_LEGO_GRAMMAR_V13 (Cyber-Financial Audit Skin ~20%–26%): Khóa skin kiểm toán tài chính tối sâu (#040C18 / #061A2E midnight audit slate, #38BDF8 ice-cyan, #FACC15 amber, #EF4444 deficit crimson, 0° crisp digital precision — 0% giấy báo xé Polaroid True Crime); lắp ghép tự do đạo cụ kiểm toán rời (nút ví on-chain, sổ cái giao dịch, đường đồ thị sập thanh khoản LivePlungingChartCurve, nhân bản hợp đồng khống EvidenceStackMultiplier, bộ đếm dòng tiền RollingForensicCounter, chẻ đôi quảng cáo vs kiểm toán SplitParadoxShutter, bản đồ dòng tiền xuyên biên giới GeoJson3DMapStage OSM GeoJSON thật) × 18 Động từ thị giác @voxVerb × 8 Hướng lia máy tự do @voxCamera khớp Whisper words[] (0 lặp động từ trong 5 cảnh VOX, 0 lặp hướng lia máy trong 3 cảnh VOX, <= 3 khung nguyên trang/tập, vùng an toàn y <= 835px, vượt qua validate-vox-newsroom-ast.mjs)",
            "FRAMELESS_CINEMA_TEXT_BEAT (~6%–8%): Chữ điện ảnh tối không khung cho con số thiệt hại chấn động, tỷ lệ dự án ma & nút thắt phá án (0 đặt 2 beat sát nhau, tự ẩn SubtitleOverlay)",
            "CLOSED_ROOM_4D_FACELESS_AI (~16%–22%): Ảnh AI 4D Faceless Forensic ({bid}_ai_keyframe.jpg, max_uses=1) cho góc kín phòng giao dịch ngầm/thẩm vấn kèm nhãn '재연 · 이해를 돕기 위한 이미지'",
            "BROADCAST_SUBTITLE_AND_SOUND_DIRECTOR: Phụ đề 52px Pretendard ExtraBold không đóng hộp (#FACC15 highlight); 8-Mood Story-Arc BGM (-18 LUFS, nền -41dBFS khi hạ nhạc trước twist, active fetch search_and_fetch_contextual_bgm) + 100% Motion-Bound SFX; câu kết trọn vẹn + 3.8s BGM fade-out",
        ],
        "subtitle_style": {
            "font_family": "Pretendard ExtraBold",
            "font_size": 52,
            "font_size_px": 52,
            "font_weight": 800,
            "color": "#FFFFFF",
            "base_color": "#FFFFFF",
            "highlight_color": "#FACC15",
            "stroke_color": "rgba(8, 8, 10, 0.96)",
            "stroke_width": 5.5,
            "stroke_width_px": 5.5,
            "background": "transparent",
            "frameless": True,
            "clause_max_chars": 16,
            "position": "bottom_center",
            "subtitle_safe_zone_max_y": 835,
        },
        "color_grade": {
            "tone_preset": "cyber_financial_forensic_noir",
            "lut_name": "warm_cream_ledger_navy_contrast",
            "vignette_opacity": 0.72,
        },
        "audio_rules": {
            "bgm_volume_db": -21.0,
            "ducking_db": -12.0,
            "music_ducking_db": -12.0,
            "target_lufs": -18.0,
            "sfx_chapter_hit": True,
            "sfx_hit_on_chapter": True,
            "telemetry_beeps": True,
            "sfx_motion_bound_vox_map_only": True,
            "outro_tail_hold_sec": 3.8,
            "outro_bgm_fade_out_sec": 3.5,
            "zero_closing_narration_cutoff": True,
            "tension_drone_under_interrogation": False,
        },
        "editorial_rules": [
            "Lock Cyber-Financial Forensic Audit skin (#040C18 midnight slate, #38BDF8 ice-cyan & #FACC15 amber vectors, 100% Hangul 제1막..제5막, y <= 835px) isolated from True Crime torn-paper newsprint",
            "Choreograph all financial/on-chain/GIS Vox scenes via VOX_COMPOSABLE_LEGO_GRAMMAR_DIRECTOR_V13: loose financial & geospatial atomic props × 18 Semantic Visual Verbs (@voxVerb) × 8 Free-Space Camera Topologies (@voxCamera) synced to Whisper words[] (frame(15%) != frame(50%) != frame(85%), 0 verb repeats in 5 consecutive VOX scenes, 0 camera repeats in 3 consecutive VOX scenes, <= 3 full-page wrappers, validate-vox-newsroom-ast.mjs --preset financial_forensic_vox)",
            "Curate 3-frame verified clean case & financial institution footage (~45-52%, max_uses=1, 0% logos/foreign subs/TV anchors), deploy FramelessCinemaTextBeat (~6-8%), and reserve 1-to-1 4D Faceless AI keyframes (~16-22%) for closed-room moments",
            "BROADCAST_SUBTITLE_AND_SOUND_DIRECTOR: 52px frameless Pretendard ExtraBold subtitles, 8-Mood Story-Arc BGM (-18 LUFS, 3s crossfades, -41dBFS room-tone floor on pre-twist drops, active fetch via search_and_fetch_contextual_bgm), 100% motion-bound SFX, and intact closing narration + 3.8s outro fade-out",
        ],
    },
}


class EditingDnaService:
    def __init__(
        self,
        profiles_file: Path | str | None = None,
        jobs_dir: Path | str | None = None,
        workspaces_dir: Path | str | None = None,
    ):
        self.profiles_file = Path(profiles_file) if profiles_file else CHANNEL_PROFILES_FILE
        self.jobs_dir = Path(jobs_dir) if jobs_dir else JOBS_DIR
        self.workspaces_dir = Path(workspaces_dir) if workspaces_dir else WORKSPACES_DIR

    def get_presets(self) -> dict[str, dict[str, Any]]:
        return copy.deepcopy(BUILTIN_EDITING_PRESETS)

    def extract_editing_dna_from_job(self, job_id: str) -> dict[str, Any]:
        """
        Extract empirical editing parameters (pacing, visual mix, archetypes,
        typography, and color grade) from workspace and job manifest files.
        Falls back safely to defaults if files are missing or empty.
        """
        ws_dir = self.workspaces_dir / job_id
        job_dir = self.jobs_dir / job_id

        # Read workspace files if available
        visual_manifest = self._read_json(ws_dir / "visual_manifest.json") or self._read_json(job_dir / "visual_manifest.json")
        voice_manifest = self._read_json(ws_dir / "voice_manifest.json") or self._read_json(job_dir / "voice_manifest.json")
        creative_brief = self._read_json(ws_dir / "creative_brief.json") or self._read_json(job_dir / "creative_brief.json")
        edit_checkpoint = self._read_json(ws_dir / "edit_checkpoint.json") or self._read_json(job_dir / "edit_checkpoint.json")
        job_data = self._read_json(job_dir / "job.json") or {}

        # Fallback to custom preset if empty workspace checkpoint
        if not visual_manifest and not voice_manifest and not creative_brief:
            fallback = copy.deepcopy(BUILTIN_EDITING_PRESETS["custom"])
            fallback["version"] = 1
            return fallback

        # 1. Compute pacing statistics
        raw_durations: list[float] = []
        beats: list[dict[str, Any]] = []

        if isinstance(visual_manifest, dict):
            beats = visual_manifest.get("beats") or []
            if not beats and "scenes" in visual_manifest:
                for scene in visual_manifest.get("scenes", []):
                    if isinstance(scene, dict):
                        beats.extend(scene.get("beats", []))

        if not beats and isinstance(voice_manifest, dict):
            beats = voice_manifest.get("beats") or []

        for b in beats:
            if isinstance(b, dict):
                dur = b.get("duration_sec") or b.get("target_duration_sec")
                if dur is not None:
                    try:
                        d = float(dur)
                        if d > 0:
                            raw_durations.append(d)
                    except (ValueError, TypeError):
                        pass

        # Safely clamp extreme values into [2.0, 15.0]
        if raw_durations:
            clamped = [min(max(d, 2.0), 15.0) for d in raw_durations]
            avg_pacing = round(statistics.mean(clamped), 2)
            min_shot = round(min(clamped), 1)
            max_shot = round(max(clamped), 1)
        else:
            avg_pacing = 5.0
            min_shot, max_shot = 3.5, 7.5

        # 2. Compute visual mix ratios
        footage_count = 0
        ai_count = 0
        motion_count = 0

        for b in beats:
            if not isinstance(b, dict):
                continue
            v_type = str(b.get("visual_type") or "").lower()
            v_route = str(b.get("visual_route") or "").lower()
            if any(k in v_type for k in ("sourced", "footage", "clip", "archival")) or v_route == "footage":
                footage_count += 1
            elif any(k in v_type for k in ("ai", "illustration", "still", "reconstruction")) or v_route == "ai_visual":
                ai_count += 1
            elif any(k in v_type for k in ("motion", "vox", "cinema_text", "hud", "map", "overlay", "telemetry")) or v_route == "vox_motion":
                motion_count += 1
            else:
                footage_count += 1

        total_visual_beats = max(len(beats), 1)
        footage_ratio = round(footage_count / total_visual_beats, 2)
        ai_ratio = round(ai_count / total_visual_beats, 2)
        motion_ratio = round(max(0.0, 1.0 - footage_ratio - ai_ratio), 2)

        # 3. Detect active Remotion archetypes
        archetypes: list[str] = []
        if isinstance(creative_brief, dict):
            brief_archetypes = creative_brief.get("editing_archetypes")
            if isinstance(brief_archetypes, list) and brief_archetypes:
                archetypes.extend(str(a) for a in brief_archetypes if a)

        # Also collect active scene_archetypes stamped on beats (e.g. True Crime Vox archetypes)
        beat_archetypes = [
            str(b.get("scene_archetype")) for b in beats
            if isinstance(b, dict) and b.get("scene_archetype")
        ]
        if beat_archetypes:
            for arch in dict.fromkeys(beat_archetypes):
                if arch not in archetypes:
                    archetypes.append(arch)

        if not archetypes:
            archetypes = [
                "2.5d_satellite_map",
                "technical_hud_telemetry",
                "blueprint_vs_reality_split",
                "chapter_hero_banner",
            ]

        # 4. Subtitle typography & Color grading
        subtitle_style = {
            "font_family": "Pretendard",
            "font_size": 44,
            "font_size_px": 44,
            "color": "#FFFFFF",
            "base_color": "#FFFFFF",
            "highlight_color": "#38BDF8" if ai_ratio < 0.6 else "#EAB308",
            "stroke_color": "#000000",
            "stroke_width": 16,
            "position": "bottom_center",
        }

        color_grade = {
            "tone_preset": "technical_cool_cyan" if footage_ratio >= 0.3 else "cold_forensic_noir",
            "lut_name": "clean_broadcast_cool" if footage_ratio >= 0.3 else "noir_desaturated",
            "vignette_opacity": 0.78,
        }

        # Select closest preset ID
        if ai_ratio >= 0.65:
            preset_id = "forensic_noir"
            name = "Forensic Noir Full-AI True Crime"
        elif footage_ratio >= 0.55:
            preset_id = "archival_historical"
            name = "Archival Historical Vault"
        elif motion_ratio >= 0.20 or "2.5d" in " ".join(archetypes).lower():
            preset_id = "2.5d_technical"
            name = "2.5D Technical & Infrastructure Investigation"
        else:
            preset_id = "custom"
            name = f"Custom Recipe (Job {job_id[:8]})"

        pacing_data = PacingDict({
            "target_beat_duration_sec": avg_pacing,
            "typical_pacing_sec": avg_pacing,
            "shot_range_sec": [min_shot, max_shot],
            "average_beat_duration_sec": avg_pacing,
            "max_routine_shot_sec": min(max_shot + 2.0, 15.0),
            "pacing_curve": "accelerating_towards_act_climax",
            "pacing_wpm": 138.0,
        })

        return {
            "preset_id": preset_id,
            "name": name,
            "version": 1,
            "pacing": pacing_data,
            "visual_mix": {
                "footage": footage_ratio,
                "ai": ai_ratio,
                "motion": motion_ratio,
                "footage_ratio": footage_ratio,
                "ai_visual_ratio": ai_ratio,
                "motion_overlay_ratio": motion_ratio,
                "preferred_routing": "hybrid" if (footage_ratio > 0 and ai_ratio > 0) else ("full_ai" if ai_ratio > 0.5 else "evidence_footage"),
            },
            "editing_archetypes": archetypes,
            "subtitle_style": subtitle_style,
            "color_grade": color_grade,
            "audio_rules": {
                "bgm_volume_db": -22.0,
                "ducking_db": -12.0,
                "music_ducking_db": -12.0,
                "sfx_chapter_hit": True,
                "sfx_hit_on_chapter": True,
                "telemetry_beeps": True,
                "tension_drone_under_interrogation": False,
            },
            "editorial_rules": [
                "Always ground technical claims with KeyMetricCallout telemetry cards",
                "Maintain voice-visual alignment within 0.3s tolerance",
            ],
        }

    def lock_job_edit_dna_to_channel(self, job_id: str, notes: str = "") -> dict[str, Any]:
        """
        Extract editing DNA from project and lock it into the parent Channel Profile.
        Increments the editing_dna version, appends the previous version to editing_dna_history,
        and saves atomically so all future projects inherit this exact recipe.
        """
        # 1. Resolve job
        job_file = self.jobs_dir / job_id / "job.json"
        if not job_file.exists():
            raise KeyError(f"Job {job_id} not found")

        job_data = self._read_json(job_file) or {}
        channel_profile_id = job_data.get("channel_profile_id")
        if not channel_profile_id:
            raise ValueError(f"Job {job_id} has no assigned channel profile to lock DNA into")

        # 2. Extract DNA from job
        extracted_dna = self.extract_editing_dna_from_job(job_id)

        # 3. Read channel profiles atomically
        with _file_lock:
            profiles_raw = self._read_json(self.profiles_file) or {}
            profiles_list = profiles_raw.get("profiles", []) if isinstance(profiles_raw, dict) else []

            profile_idx = next(
                (i for i, p in enumerate(profiles_list) if str(p.get("id")) == str(channel_profile_id) or str(p.get("channel_profile_id")) == str(channel_profile_id)),
                None
            )
            if profile_idx is None:
                raise KeyError(f"Channel profile {channel_profile_id} not found")

            profile = profiles_list[profile_idx]

            # 4. Versioning & History
            prev_dna = profile.get("editing_dna") or {}
            prev_version = int(prev_dna.get("version", 1)) if isinstance(prev_dna, dict) else 1
            new_version = prev_version + 1

            # Prepare history record
            history = list(profile.get("editing_dna_history") or [])
            if prev_dna:
                history_entry = copy.deepcopy(prev_dna)
                # Ensure sequential version records for auditability
                if "version" not in history_entry:
                    history_entry["version"] = prev_version
                history.append(history_entry)

            # Assemble updated DNA
            extracted_dna["version"] = new_version
            extracted_dna["locked_from_job_id"] = job_id
            extracted_dna["locked_at"] = _now()
            if notes:
                extracted_dna["notes"] = notes

            profile["editing_dna"] = extracted_dna
            profile["editing_dna_history"] = history
            profile["updated_at"] = _now()

            # Write back channel profiles
            self._write_json(self.profiles_file, {"profiles": profiles_list})

            # 5. Also update job's local record & snapshot
            job_data["editing_dna"] = copy.deepcopy(extracted_dna)
            snapshot = job_data.setdefault("channel_profile_snapshot", {})
            snapshot["editing_dna"] = copy.deepcopy(extracted_dna)
            self._write_json(job_file, job_data)

        return {
            "status": "success",
            "message": f"Edit style successfully locked to channel profile '{channel_profile_id}' as version {new_version}",
            "profile_id": channel_profile_id,
            "channel_profile_id": channel_profile_id,
            "version": new_version,
            "locked_job_id": job_id,
            "editing_dna": extracted_dna,
            "history_count": len(history),
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
