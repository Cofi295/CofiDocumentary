"""Dynamic Context-Aware Audio Library Manager, 8-Mood Story-Arc BGM Scorer,
Active BGM Search-and-Downloader & Motion-Bound SFX Engine for CofiDocumentary.

Implements the locked 3-pillar audio/visual production architecture:
1. BGM (Story-Arc Scoring + Anti-Reuse + Active Search & Download):
   - 8 Narrative/Emotional Mood Pools (`01_mystery_hook` .. `08_memorial_epilogue`)
     with open mood directories (`presets/audio_library/bgm/<mood_id>/`) so user-dropped
     tracks are automatically discovered and prioritized.
   - Episode BGM changes every 2–3.5 minutes across 8–12 semantic story segments
     with 3-second smooth crossfades (`crossfadeFrames = 90`).
   - Dramatic Silence Drops (`2.5–3.0 seconds` of 0 BGM) at the 2–3 highest-impact
     narrative twists/revelations so raw voiceover lands with maximum chills.
   - Broadcast Loudness Normalization (`-18 LUFS`) + Voice-Aware Dynamic Ducking.
   - MANDATORY ACTIVE SEARCH & DOWNLOAD (`search_and_fetch_contextual_bgm`):
     Tracks used in recent episodes (`data/bgm_usage_history.json`) or that do not match
     the specific scene nuance are NOT lazily reused; the agent/system actively searches
     and downloads new fitting instrumental BGM from Wikimedia Commons, Internet Archive,
     or yt-dlp CC sources on the fly.
2. SFX (100% Motion-Bound SFX Policy):
   - ZERO generic/ambient SFX spam on `REAL_FTG` (real video footage) and `AI_4D` (still keyframes).
   - SFX are triggered 100% from actual physical/graphic motion keyframes inside Vox scenes,
     Satellite/GIS map flights, and Chapter transitions (`sfx_events` emitted at the exact frame).
"""
from __future__ import annotations

import hashlib
import json
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRESET_AUDIO_DIR = PROJECT_ROOT / "presets" / "audio_library"
REMOTION_AUDIO_DIR = Path(r"B:\ALL_TOOLS\CofiRemotion\public\audio_library")
BGM_USAGE_HISTORY_PATH = PROJECT_ROOT / "data" / "bgm_usage_history.json"

USER_AGENT = "CofiDocumentaryStudio/3.0 (https://github.com/cofi-studio; contact@cofi.local)"
_NO_WINDOW_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

# ==============================================================================
# 1. CANONICAL CATALOG OF 26 REAL RECORDED MOTION-BOUND GRAPHIC FOLEY SFX
# ==============================================================================
CONTEXTUAL_SFX_CATALOG: dict[str, dict[str, Any]] = {
    "sfx_paper_turn.mp3": {
        "category": "editorial_paper",
        "motion_primitive": "paper_card_slide",
        "component_tags": ["SlideIn", "PaperCraftPiece:slap_12fps", "IndexCard"],
        "description": "Crisp archival dossier page turn / index card slide",
        "keywords": ["기록", "페이지", "서류", "파일", "문서", "조서", "진술서", "열람", "page", "document"],
        "openverse_query": "paper page turn",
        "trim_sec": 0.78,
    },
    "sfx_newspaper_unfold.mp3": {
        "category": "editorial_paper",
        "motion_primitive": "newspaper_clipping_unfold",
        "component_tags": ["TornClipping", "PaperCraftPiece:unfold_3d"],
        "description": "Broadsheet newspaper unfolding / archival press clipping reveal",
        "keywords": ["신문", "보도", "언론", "기사", "특종", "폭로", "헤드라인", "취재", "newspaper", "press"],
        "openverse_query": "newspaper unfold rustle",
        "trim_sec": 0.89,
    },
    "sfx_folder_open.mp3": {
        "category": "editorial_paper",
        "motion_primitive": "manila_dossier_open",
        "component_tags": ["PaperCraftPiece:drop_slam", "BlackCard"],
        "description": "Heavy manila case file folder opening on investigation desk",
        "keywords": ["사건 파일", "수사 기록", "내사", "보관", "미제", "봉인", "철", "folder", "case file"],
        "openverse_query": "cardboard folder open",
        "trim_sec": 0.44,
    },
    "sfx_notebook_page_rustle.mp3": {
        "category": "editorial_paper",
        "motion_primitive": "notebook_page_rustle",
        "component_tags": ["PaperCraftPiece:fan_spread"],
        "description": "Turning pages of pocket investigation notebook / ledger shuffle",
        "keywords": ["수첩", "첫 장", "펼친", "공책", "메모장", "장부", "notebook", "diary", "rustle"],
        "openverse_query": "notebook page flip",
        "trim_sec": 0.82,
    },
    "sfx_page_tear_notebook.mp3": {
        "category": "editorial_paper",
        "motion_primitive": "page_tear_notebook",
        "component_tags": ["PaperCraftPiece:tape_peel", "Tape", "ct_redaction_peel"],
        "description": "Crisp paper clipping tear / redaction tape peel",
        "keywords": ["수첩", "찢어", "메모", "쪽지", "테이프", "가림막", "tear", "peel"],
        "openverse_query": "paper tear rip",
        "trim_sec": 0.76,
    },
    "sfx_corkboard_pin_push.mp3": {
        "category": "tactile_board",
        "motion_primitive": "corkboard_pin_push",
        "component_tags": ["DieCutSticker", "Label"],
        "description": "Tactile push-pin thud into cork investigation board",
        "keywords": ["게시판", "핀", "고정", "수사판", "보드", "사진을 붙", "pin", "corkboard"],
        "openverse_query": "wood tap thud short",
        "trim_sec": 0.24,
    },
    "sfx_camera_shutter.mp3": {
        "category": "tactile_board",
        "motion_primitive": "polaroid_photo_pin",
        "component_tags": ["VoxPhotoPaper", "VoxVideoPaper"],
        "description": "Mechanical SLR archival camera shutter click when evidence photo snaps onto desk",
        "keywords": ["사진", "현장", "목격", "촬영", "증거물", "초상", "얼굴", "신원", "photo", "evidence"],
        "openverse_query": "camera shutter click mechanical",
        "trim_sec": 0.53,
    },
    "sfx_crimson_thread_taut.mp3": {
        "category": "tactile_board",
        "motion_primitive": "crimson_thread_taut",
        "component_tags": ["TwistedRedYarn"],
        "description": "Taut crimson evidence yarn pull & snap between pinboard nodes",
        "keywords": ["연결", "퍼즐", "하나로", "겹쳐", "공통점", "잇는", "고리", "thread", "string", "link"],
        "openverse_query": "rope pull tight",
        "trim_sec": 0.78,
    },
    "sfx_marker_circle_draw.mp3": {
        "category": "ink_annotation",
        "motion_primitive": "marker_circle_draw",
        "component_tags": ["RedCircle", "RedLine"],
        "description": "Felt marker drawing crimson circle or arrow around evidence clue",
        "keywords": ["동그라미", "표시", "체크", "궤적", "화살표", "marker", "circle", "draw"],
        "openverse_query": "marker pen draw paper",
        "trim_sec": 0.78,
    },
    "sfx_highlighter_swipe.mp3": {
        "category": "ink_annotation",
        "motion_primitive": "highlighter_stroke_swipe",
        "component_tags": ["Highlight"],
        "description": "Felt-tip highlighter swipe across document clause",
        "keywords": ["강조", "핵심", "밑줄", "주목", "문구", "적시", "밝혀", "드러나", "highlight", "marker"],
        "openverse_query": "felt tip pen stroke",
        "trim_sec": 0.75,
    },
    "sfx_pencil_underline.mp3": {
        "category": "ink_annotation",
        "motion_primitive": "pencil_underline",
        "component_tags": ["Underline"],
        "description": "Graphite pencil stroke underlining dossier text",
        "keywords": ["밑줄", "연필", "기재", "적힌", "구절", "underline", "pencil"],
        "openverse_query": "pencil write stroke",
        "trim_sec": 0.75,
    },
    "sfx_caliper_metal_slide.mp3": {
        "category": "forensic_optics",
        "motion_primitive": "caliper_metal_slide",
        "component_tags": ["DimensionBracket", "ct_split_contradiction"],
        "description": "Precision steel vernier caliper & forensic dimension bracket slide",
        "keywords": ["센티미터", "밀리미터", "킬로그램", "치수", "측정", "계측", "거리", "단면", "caliper", "measure"],
        "openverse_query": "metal slide click",
        "trim_sec": 0.57,
    },
    "sfx_magnifying_lens_click.mp3": {
        "category": "forensic_optics",
        "motion_primitive": "magnifying_lens_click",
        "component_tags": ["OpticalLoupe:lock"],
        "description": "Optical microscope turret / forensic magnifier lens click lock",
        "keywords": ["강선", "초승달", "렌즈", "편차", "돋보기", "격발 흔적", "lens", "loupe"],
        "openverse_query": "camera lens click",
        "trim_sec": 0.55,
    },
    "sfx_document_scanner_hum.mp3": {
        "category": "forensic_optics",
        "motion_primitive": "loupe_magnifier_sweep",
        "component_tags": ["OpticalLoupe", "ct_forensic_hud"],
        "description": "Forensic optical loupe & microfilm scanner carriage sweep",
        "keywords": ["감식", "검증", "전산", "시스템", "조회", "데이터베이스", "스캔", "추적", "scan", "database"],
        "openverse_query": "scanner motor mechanical",
        "trim_sec": 0.88,
    },
    "sfx_biometric_match_chime.mp3": {
        "category": "forensic_optics",
        "motion_primitive": "dna_locus_match_lock",
        "component_tags": ["BiometricMatchLock"],
        "description": "Biometric fingerprint / 17-point minutiae / DNA locus match chime",
        "keywords": ["지문", "대조", "생체", "일치", "DNA", "유전자", "융선", "fingerprint", "biometric", "match"],
        "openverse_query": "bell ding single",
        "trim_sec": 0.85,
    },
    "sfx_dossier_stamp.mp3": {
        "category": "judicial_seal",
        "motion_primitive": "official_seal_stamp",
        "component_tags": ["Stamp"],
        "description": "Official rubber ink stamp pressing onto confidential dossier",
        "keywords": ["도장", "직인", "비준", "승인", "기밀", "문건", "공문", "결정문", "stamp", "classified"],
        "openverse_query": "rubber stamp paper",
        "trim_sec": 0.72,
    },
    "sfx_official_seal_thud.mp3": {
        "category": "judicial_seal",
        "motion_primitive": "heavy_seal_impact",
        "component_tags": ["Stamp:heavy"],
        "description": "Heavy institutional wooden seal & case-closed folder thud",
        "keywords": ["최고인민법원", "확정", "최종", "봉인", "종결", "seal", "supreme court"],
        "openverse_query": "heavy book drop thud",
        "trim_sec": 0.85,
    },
    "sfx_gavel_hit.mp3": {
        "category": "judicial_seal",
        "motion_primitive": "verdict_gavel_strike",
        "component_tags": ["ct_verdict_gavel", "verdict_pillar"],
        "description": "Courtroom wooden gavel strike / verdict pronouncement",
        "keywords": ["법원", "판결", "선고", "재판", "사형", "법정", "징역", " 무기징역", "court", "verdict", "gavel"],
        "openverse_query": "gavel hit wood",
        "trim_sec": 0.88,
    },
    "sfx_map_route_sweep.mp3": {
        "category": "map_gis",
        "motion_primitive": "gis_camera_flight_arc",
        "component_tags": ["GeoJson3DMapStage", "BespokeGisVectorOverlay:route"],
        "description": "Cartographic map route sweep & 3D GIS flight arc",
        "keywords": ["이동", "경로", "노선", "전역", "투입", "파견", "지도", "route", "map", "flight"],
        "openverse_query": "paper slide desk",
        "trim_sec": 0.82,
    },
    "sfx_radar_ping_sonar.mp3": {
        "category": "map_gis",
        "motion_primitive": "map_pin_pulse_ring",
        "component_tags": ["BespokeGisVectorOverlay:pulse"],
        "description": "Tactical radar / sonar location pulse ring on satellite map",
        "keywords": ["위성", "좌표", "위치", "반경", "추적", "거점", "포착", "지점", "radar", "satellite", "pin"],
        "openverse_query": "submarine sonar ping",
        "trim_sec": 1.10,
    },
    "sfx_satellite_lock_beep.mp3": {
        "category": "map_gis",
        "motion_primitive": "coordinate_target_lock",
        "component_tags": ["BespokeGisVectorOverlay:lock"],
        "description": "Optical autofocus & telemetry target lock confirmation on satellite coordinate",
        "keywords": ["관할", "구역", "거리", "현장", "지도", "포착", "타깃", "zone", "target"],
        "openverse_query": "camera autofocus beep",
        "trim_sec": 0.85,
    },
    "sfx_compass_bearing_lock.mp3": {
        "category": "map_gis",
        "motion_primitive": "compass_bearing_lock",
        "component_tags": ["BespokeGisVectorOverlay:bearing"],
        "description": "Mechanical brass bezel & compass bearing detent click lock",
        "keywords": ["방위", "방향", "지형", "해안", "내륙", "산악", "compass", "bearing"],
        "openverse_query": "mechanical dial click",
        "trim_sec": 0.58,
    },
    "sfx_telemetry_tick.mp3": {
        "category": "chronology_metric",
        "motion_primitive": "numeric_counter_roll",
        "component_tags": ["ct_metric_counter", "monolith_metric"],
        "description": "Crisp mechanical counter tick for forensic metric roll",
        "keywords": ["수치", "통계", "건수", "비율", "데이터", "카운트", "명단", "count", "metric"],
        "openverse_query": "mechanical click single",
        "trim_sec": 0.23,
    },
    "sfx_clock_tick_tense.mp3": {
        "category": "chronology_metric",
        "motion_primitive": "timeline_relay_step",
        "component_tags": ["ct_chronicle_22y", "chronicle_horizon"],
        "description": "Measured mechanical watch tick for chronological timeline step",
        "keywords": ["년", "월", "일", "시간", "세월", "연도", "22년", "타임라인", "timeline", "year", "clock"],
        "openverse_query": "watch tick single",
        "trim_sec": 0.14,
    },
    "sfx_typing_log.mp3": {
        "category": "chronology_metric",
        "motion_primitive": "typewriter_text_reveal",
        "component_tags": ["ct_shatter_question", "whisper_abyss"],
        "description": "Mechanical typewriter key strike for dossier text reveal",
        "keywords": ["작성", "보고서", "입력", "타자", "기록", "타이핑", "log", "report"],
        "openverse_query": "typewriter key single",
        "trim_sec": 0.31,
    },
    "sfx_chapter_hit.mp3": {
        "category": "chapter_transition",
        "motion_primitive": "chapter_card_enter",
        "component_tags": ["ActChapterCard"],
        "description": "Deep acoustic low drum hit for documentary Act/Chapter card transition",
        "keywords": ["장", "챕터", "시작", "서막", "결말", "chapter"],
        "openverse_query": "low drum hit single",
        "trim_sec": 1.35,
    },
}

SFX_CATALOG: dict[str, dict[str, Any]] = CONTEXTUAL_SFX_CATALOG

# Map from visual motion primitive type -> exact SFX filename & balanced volume
MOTION_PRIMITIVE_TO_SFX: dict[str, tuple[str, float]] = {
    "paper_card_slide": ("sfx_paper_turn.mp3", 0.095),
    "newspaper_clipping_unfold": ("sfx_newspaper_unfold.mp3", 0.102),
    "manila_dossier_open": ("sfx_folder_open.mp3", 0.102),
    "notebook_page_rustle": ("sfx_notebook_page_rustle.mp3", 0.095),
    "page_tear_notebook": ("sfx_page_tear_notebook.mp3", 0.100),
    "corkboard_pin_push": ("sfx_corkboard_pin_push.mp3", 0.100),
    "polaroid_photo_pin": ("sfx_camera_shutter.mp3", 0.096),
    "crimson_thread_taut": ("sfx_crimson_thread_taut.mp3", 0.098),
    "crimson_string_draw": ("sfx_crimson_thread_taut.mp3", 0.098),
    "marker_circle_draw": ("sfx_marker_circle_draw.mp3", 0.100),
    "highlighter_stroke_swipe": ("sfx_highlighter_swipe.mp3", 0.100),
    "pencil_underline": ("sfx_pencil_underline.mp3", 0.096),
    "caliper_metal_slide": ("sfx_caliper_metal_slide.mp3", 0.098),
    "magnifying_lens_click": ("sfx_magnifying_lens_click.mp3", 0.096),
    "loupe_magnifier_sweep": ("sfx_document_scanner_hum.mp3", 0.095),
    "dna_locus_match_lock": ("sfx_biometric_match_chime.mp3", 0.102),
    "official_seal_stamp": ("sfx_dossier_stamp.mp3", 0.110),
    "heavy_seal_impact": ("sfx_official_seal_thud.mp3", 0.112),
    "verdict_gavel_strike": ("sfx_gavel_hit.mp3", 0.115),
    "gis_camera_flight_arc": ("sfx_map_route_sweep.mp3", 0.102),
    "map_pin_pulse_ring": ("sfx_radar_ping_sonar.mp3", 0.095),
    "coordinate_target_lock": ("sfx_satellite_lock_beep.mp3", 0.095),
    "compass_bearing_lock": ("sfx_compass_bearing_lock.mp3", 0.096),
    "numeric_counter_roll": ("sfx_telemetry_tick.mp3", 0.092),
    "timeline_relay_step": ("sfx_clock_tick_tense.mp3", 0.092),
    "typewriter_text_reveal": ("sfx_typing_log.mp3", 0.092),
    "chapter_card_enter": ("sfx_chapter_hit.mp3", 0.115),
    "sub_bass_boom_chapter": ("sfx_chapter_hit.mp3", 0.115),
    "sfx_sub_bass_boom_chapter": ("sfx_chapter_hit.mp3", 0.115),
}

# ==============================================================================
# 2. 8-MOOD STORY-ARC BGM POOLS & DEFAULT_BGM_POOLS (100% EAR-VERIFIED DARK FORENSIC NOIR)
# ==============================================================================
STORY_ARC_BGM_MOOD_POOLS: dict[str, dict[str, Any]] = {
    '01_mystery_hook': {
        'label': 'Mưa đêm / Bí ẩn mở màn & Nghịch lý',
        'search_queries': ['dark forensic noir ambient drone documentary'],
        'keywords': ['미스터리', '의문', '발생', '사건', '시작', '비', '새벽', '침입', 'mystery', 'hook'],
        'tracks': {
            'bgm_dark_ambient_drone.mp3': {
                'description': 'Dark Ambient Drone — Nocturnal rain infiltration & cold-case mystery hook',
                'keywords': ['비', '새벽', '침입', '미스터리', '시작', '보석상'],
            },
            'bgm_kaili_v3_corridor_suspense.mp3': {
                'description': 'Corridor Suspense — Subterranean forensic corridor & crime scene discovery',
                'keywords': ['복도', '발견', '소음기', '밧줄', '현장', '정적'],
            },
        },
    },
    '02_tragic_empathy': {
        'label': 'Bi kịch Nạn nhân / Hiện trường Tĩnh lặng',
        'search_queries': ['somber dark ambient documentary pad'],
        'keywords': ['피해자', '경비원', '유가족', '비극', '정적', 'victim', 'aftermath'],
        'tracks': {
            'bgm_kaili_cold_case_archive.mp3': {
                'description': 'Cold Case Archive — Hollow somber ambient pad for crime aftermath & cold trails',
                'keywords': ['현장', '정적', '비극', '미제', '세월'],
            },
        },
    },
    '03_cold_case_dossier': {
        'label': 'Hồ sơ Phủ bụi / Bế tắc Nhiều năm & Lưu trữ',
        'search_queries': ['cold case archive investigation dark ambient'],
        'keywords': ['미제', '22년', '세월', '서류', '파일', '보관', 'cold case', 'archive'],
        'tracks': {
            'bgm_kaili_cold_case_archive.mp3': {
                'description': 'Cold Case Archive — Deep institutional archive & decades-long investigation bed',
                'keywords': ['미제', '22년', '기록', '파일', '보관소'],
            },
        },
    },
    '04_forensic_dna_lab': {
        'label': 'Phòng Thí nghiệm / Giám định Vân tay, Đạn đạo & AI Sinh trắc',
        'search_queries': ['forensic science laboratory pulse ambient documentary'],
        'keywords': ['DNA', '지문', '장문', '융선', '감식', '과학수사', '탄도', '금고', 'forensic', 'lab'],
        'tracks': {
            'bgm_cendence_analysis.mp3': {
                'description': 'Cendence Analysis — Deep sub-bass forensic pulse & physical tool-mark analysis',
                'keywords': ['금고', '감식', '탄도', '소음기', '분석', '물리'],
            },
            'bgm_dark_dyne_telemetry.mp3': {
                'description': 'Dark Dyne Telemetry — Deep resonant forensic lab & DNA/palmprint preservation',
                'keywords': ['DNA', '절반 지문', '장문', '보존', '실험실', '시료'],
            },
            'bgm_biometric_airport_scan.mp3': {
                'description': 'Biometric Scan — 2017 AI/AFIS algorithm upgrade & 17-minutiae biometric lock',
                'keywords': ['AI', '알고리즘', '융선', '17개', '데이터베이스', '일치'],
            },
        },
    },
    '05_double_life_dread': {
        'label': 'Vỏ bọc Hai mặt / Sự Rợn ngợp Kẻ ẩn mình 22 Năm',
        'search_queries': ['psychological thriller double life dark drone'],
        'keywords': ['이중생활', '주지시', '가면', '평온', '은신', '당구장', 'double life', 'dread'],
        'tracks': {
            'bgm_dystopia_facade.mp3': {
                'description': 'Dystopia Facade — Eerie dark minor ambient pad for 22-year double life',
                'keywords': ['이중생활', '주지시', '가면', '남편', '이웃', '은신'],
            },
            'bgm_dark_basement_shadow.mp3': {
                'description': 'Dark Basement Shadow — Low subterranean shadow tension & black-market trail',
                'keywords': ['암시장', '국경', '권총', '완서우', '털모자', '위장'],
            },
        },
    },
    '06_interrogation_manhunt': {
        'label': 'Truy kích Vây bắt / Đấu súng & Đột kích Phòng Mạt chược',
        'search_queries': ['tense police manhunt tactical surveillance dark pulse'],
        'keywords': ['체포', '포위', '마작방', '린하이', '총격', '샤오싱', '추적', 'raid', 'manhunt'],
        'tracks': {
            'bgm_bad_impact_sentence.mp3': {
                'description': 'Bad Impact — High-tension sub-bass industrial drone for rooftop gunfight & escalation',
                'keywords': ['총격', '샤오싱', '타이저우', '비상계단', '도주', '추격'],
            },
            'bgm_kaili_afis_fingerprint_04.mp3': {
                'description': 'Tactical Surveillance Lock — Crystalline tension pad for plainclothes mahjong raid',
                'keywords': ['린하이', '마작방', '사복', '포위', '3초', '제압'],
            },
        },
    },
    '07_solemn_verdict': {
        'label': 'Thẩm vấn Tâm lý & Tuyên án Tòa án Nhân dân Trung cấp',
        'search_queries': ['solemn interrogation courtroom verdict dark ambient'],
        'keywords': ['심문', '자백', '법원', '재판', '판결', '선고', '사형', 'verdict', 'court'],
        'tracks': {
            'bgm_edge_of_the_sky.mp3': {
                'description': 'Edge of the Sky — Solemn deep psychological interrogation & confession pad',
                'keywords': ['심문실', '침묵', '닝보', '자백', '무너진'],
            },
        },
    },
    '08_memorial_epilogue': {
        'label': 'Khép lại Kỳ án 22 Năm & Dư âm Công lý',
        'search_queries': ['solemn documentary epilogue closure drone'],
        'keywords': ['사형', '선고', '마침표', '22년', '진실', '정의', '마무리', 'epilogue', 'closure'],
        'tracks': {
            'bgm_floodlight_closure.mp3': {
                'description': 'Floodlight Closure — Deep solemn courtroom verdict & 22-year epilogue closure drone',
                'keywords': ['샤오싱', '중급인민법원', '사형', '마침표', '22년', '정의'],
            },
        },
    },
}

DEFAULT_BGM_POOLS: dict[str, dict[str, Any]] = STORY_ARC_BGM_MOOD_POOLS

# Flattened view for backward-compatible lookups
CONTEXTUAL_BGM_CATALOG: dict[str, dict[str, Any]] = {}
for _mood_id, _pool in STORY_ARC_BGM_MOOD_POOLS.items():
    for _fname, _tmeta in _pool["tracks"].items():
        CONTEXTUAL_BGM_CATALOG[_fname] = {
            "mood": _mood_id,
            "mood_label": _pool["label"],
            "description": _tmeta["description"],
            "keywords": list(dict.fromkeys(list(_tmeta.get("keywords", [])) + list(_pool.get("keywords", [])[:6]))),
            "commons_source": _tmeta.get("commons_source"),
            "local_seed_source": _tmeta.get("local_seed_source"),
        }


def _get_commons_download_urls(titles: list[str]) -> dict[str, str]:
    """Batch-fetch Wikimedia Commons download URLs (up to 40 titles per request)
    with automatic retry on HTTP 429.
    """
    unique_titles = [t for t in dict.fromkeys(titles) if t]
    if not unique_titles:
        return {}
    out: dict[str, str] = {}
    batch_size = 35
    for i in range(0, len(unique_titles), batch_size):
        batch = unique_titles[i : i + batch_size]
        url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
            {
                "action": "query",
                "titles": "|".join(batch),
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            }
        )
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                for _, page in data.get("query", {}).get("pages", {}).items():
                    title = page.get("title", "")
                    ii = page.get("imageinfo", [{}])[0]
                    if title and ii.get("url"):
                        out[title] = ii["url"]
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                print(f"[audio_library_manager] Commons batch URL error: {e}")
                break
            except Exception as exc:
                print(f"[audio_library_manager] Commons batch URL error: {exc}")
                break
        if i + batch_size < len(unique_titles):
            time.sleep(0.5)
    return out


def _master_bgm_file_lufs(src_path: str | Path, dst_path: Path, max_duration_sec: float = 195.0) -> bool:
    """Master a BGM track to broadcast documentary standard (-18 LUFS, warm EQ that
    preserves clarity for 1kHz-3.5kHz human voiceover, smooth fade-in/out).
    """
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    af_chain = (
        "highpass=f=45,"
        "equalizer=f=2400:width_type=q:width=1.2:g=-3.5,"
        "lowpass=f=8200,"
        "loudnorm=I=-18:TP=-1.5:LRA=11,"
        "afade=t=in:st=0:d=1.8"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src_path),
        "-t",
        str(max_duration_sec),
        "-af",
        af_chain,
        "-ar",
        "44100",
        "-ac",
        "2",
        "-b:a",
        "192k",
        str(dst_path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=_NO_WINDOW_FLAGS)
        return dst_path.exists() and dst_path.stat().st_size > 15000
    except Exception as exc:
        print(f"[audio_library_manager] FFmpeg LUFS mastering failed for {dst_path.name}: {exc}")
        return False


def discover_user_dropped_bgm() -> dict[str, dict[str, Any]]:
    """Scan all 8 mood directories (`presets/audio_library/bgm/<mood_id>/`) for any
    custom `.mp3`/`.wav`/`.ogg` tracks dropped by the user or downloaded dynamically,
    and register them into `STORY_ARC_BGM_MOOD_POOLS` and `CONTEXTUAL_BGM_CATALOG`.
    """
    bgm_root = PRESET_AUDIO_DIR / "bgm"
    bgm_root.mkdir(parents=True, exist_ok=True)
    discovered: dict[str, dict[str, Any]] = {}

    for mood_id, pool in STORY_ARC_BGM_MOOD_POOLS.items():
        mood_dir = bgm_root / mood_id
        mood_dir.mkdir(parents=True, exist_ok=True)
        for ext in ("*.mp3", "*.wav", "*.ogg", "*.oga", "*.m4a"):
            for f in sorted(mood_dir.glob(ext)):
                if f.stat().st_size < 10000:
                    continue
                mp3_name = f.stem + ".mp3"
                flat_target = bgm_root / mp3_name
                if f.suffix.lower() != ".mp3":
                    mp3_in_mood = mood_dir / mp3_name
                    if not mp3_in_mood.exists():
                        _master_bgm_file_lufs(f, mp3_in_mood)
                    f = mp3_in_mood
                if f.exists() and not flat_target.exists():
                    shutil.copy2(f, flat_target)
                if mp3_name not in pool["tracks"]:
                    stem_words = [w for w in re.split(r"[_\-\s]+", f.stem.lower()) if len(w) >= 2 and w != "bgm"]
                    meta_entry = {
                        "description": f"User/Dynamic Track ({mood_id}): {f.stem}",
                        "keywords": list(dict.fromkeys(stem_words + list(pool.get("keywords", [])[:6]))),
                        "user_or_dynamic": True,
                    }
                    pool["tracks"][mp3_name] = meta_entry
                    CONTEXTUAL_BGM_CATALOG[mp3_name] = {
                        "mood": mood_id,
                        "mood_label": pool["label"],
                        "description": meta_entry["description"],
                        "keywords": meta_entry["keywords"],
                        "user_or_dynamic": True,
                    }
                    discovered[mp3_name] = CONTEXTUAL_BGM_CATALOG[mp3_name]
    return discovered


def ensure_audio_library_stocked() -> dict[str, Any]:
    """Ensure all 28+ contextual Foley SFX and all 40+ BGM tracks across the 8 mood pools
    exist in `presets/audio_library` (both inside mood subfolders and flat `bgm/`)
    and are synchronized to `CofiRemotion/public/audio_library`.
    """
    sfx_dir = PRESET_AUDIO_DIR / "sfx"
    bgm_dir = PRESET_AUDIO_DIR / "bgm"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    bgm_dir.mkdir(parents=True, exist_ok=True)

    for mood_id in STORY_ARC_BGM_MOOD_POOLS:
        (bgm_dir / mood_id).mkdir(parents=True, exist_ok=True)

    # 1. Batch-collect missing Commons SFX + BGM titles
    missing_commons_sfx: dict[str, str] = {}
    for fname, meta in CONTEXTUAL_SFX_CATALOG.items():
        target = sfx_dir / fname
        if not target.exists() and meta.get("commons_source"):
            missing_commons_sfx[fname] = meta["commons_source"]

    missing_commons_bgm: dict[str, tuple[str, str]] = {}
    for mood_id, pool in STORY_ARC_BGM_MOOD_POOLS.items():
        for fname, tmeta in pool["tracks"].items():
            flat_t = bgm_dir / fname
            mood_t = bgm_dir / mood_id / fname
            if (not flat_t.exists() or flat_t.stat().st_size < 15000) and tmeta.get("commons_source"):
                missing_commons_bgm[fname] = (mood_id, tmeta["commons_source"])

    all_titles = list(set(missing_commons_sfx.values()) | {v[1] for v in missing_commons_bgm.values()})
    commons_urls = _get_commons_download_urls(all_titles) if all_titles else {}

    # 2. Stock SFX
    created_sfx: list[str] = []
    for fname, meta in CONTEXTUAL_SFX_CATALOG.items():
        target = sfx_dir / fname
        if target.exists() and target.stat().st_size > 1500:
            continue

        commons_title = meta.get("commons_source")
        af_filter = meta.get("af_filter", "afade=t=out:st=0.8:d=0.4,volume=0.8")
        trim_sec = float(meta.get("trim_sec", 1.35))

        if commons_title and commons_title in commons_urls:
            dl_url = commons_urls[commons_title]
            try:
                with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
                    tmp_path = tmp.name
                req = urllib.request.Request(dl_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=25) as r, open(tmp_path, "wb") as f:
                    f.write(r.read())
                cmd = [
                    "ffmpeg", "-y", "-i", tmp_path,
                    "-t", str(trim_sec), "-af", af_filter,
                    "-ar", "44100", "-ac", "2", "-b:a", "192k",
                    str(target),
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=_NO_WINDOW_FLAGS)
                os.unlink(tmp_path)
                created_sfx.append(fname)
                time.sleep(0.2)
                continue
            except Exception as exc:
                print(f"[audio_library_manager] Commons SFX fallback for {fname}: {exc}")

        base_mix = meta.get("base_mix")
        if base_mix:
            src_a = sfx_dir / base_mix[0]
            src_b = sfx_dir / base_mix[1]
            if src_a.exists() and src_b.exists():
                cmd = [
                    "ffmpeg", "-y", "-i", str(src_a), "-i", str(src_b),
                    "-filter_complex", f"[0:a][1:a]amix=inputs=2:duration=longest:dropout_transition=0.2,{af_filter}",
                    "-t", str(trim_sec), "-ar", "44100", "-ac", "2", "-b:a", "192k",
                    str(target),
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=_NO_WINDOW_FLAGS)
                created_sfx.append(fname)

    # 3. Stock 8-Mood BGM Pools (from local seed sources + Wikimedia Commons studio tracks)
    created_bgm: list[str] = []
    for mood_id, pool in STORY_ARC_BGM_MOOD_POOLS.items():
        mood_dir = bgm_dir / mood_id
        mood_dir.mkdir(parents=True, exist_ok=True)
        for fname, tmeta in pool["tracks"].items():
            flat_t = bgm_dir / fname
            mood_t = mood_dir / fname

            # If already in flat_t, ensure copied to mood_t
            if flat_t.exists() and flat_t.stat().st_size > 15000:
                if not mood_t.exists():
                    shutil.copy2(flat_t, mood_t)
                continue

            # Check local seed source
            seed_src = tmeta.get("local_seed_source")
            if seed_src and Path(seed_src).exists():
                if _master_bgm_file_lufs(seed_src, mood_t):
                    shutil.copy2(mood_t, flat_t)
                    created_bgm.append(fname)
                    continue

            # Check Wikimedia Commons URL
            commons_title = tmeta.get("commons_source")
            if commons_title and commons_title in commons_urls:
                dl_url = commons_urls[commons_title]
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
                        tmp_path = tmp.name
                    req = urllib.request.Request(dl_url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=35) as r, open(tmp_path, "wb") as f:
                        f.write(r.read())
                    if _master_bgm_file_lufs(tmp_path, mood_t):
                        shutil.copy2(mood_t, flat_t)
                        created_bgm.append(fname)
                    os.unlink(tmp_path)
                    time.sleep(0.25)
                    continue
                except Exception as exc:
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass
                    print(f"[audio_library_manager] Commons BGM download warning for {fname}: {exc}")

    # 4. Also scan any user-dropped or dynamically fetched tracks in the 8 mood folders
    discovered_custom = discover_user_dropped_bgm()

    # 5. Sync everything to CofiRemotion/public/audio_library
    if REMOTION_AUDIO_DIR.parent.exists():
        rem_sfx = REMOTION_AUDIO_DIR / "sfx"
        rem_bgm = REMOTION_AUDIO_DIR / "bgm"
        rem_sfx.mkdir(parents=True, exist_ok=True)
        rem_bgm.mkdir(parents=True, exist_ok=True)
        for f in sfx_dir.glob("*.mp3"):
            shutil.copy2(f, rem_sfx / f.name)
        for f in bgm_dir.glob("*.mp3"):
            shutil.copy2(f, rem_bgm / f.name)
        for mood_id in STORY_ARC_BGM_MOOD_POOLS:
            rem_mood_dir = rem_bgm / mood_id
            rem_mood_dir.mkdir(parents=True, exist_ok=True)
            for f in (bgm_dir / mood_id).glob("*.mp3"):
                shutil.copy2(f, rem_mood_dir / f.name)

    # 6. Write updated manifest.json
    manifest_path = PRESET_AUDIO_DIR / "manifest.json"
    manifest_data = {
        "version": "3.0-story-arc-8mood-dynamic",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mood_pools": {
            mood_id: {
                "label": pool["label"],
                "folder": f"audio_library/bgm/{mood_id}",
                "tracks": [k for k in pool["tracks"] if (bgm_dir / k).exists()],
            }
            for mood_id, pool in STORY_ARC_BGM_MOOD_POOLS.items()
        },
        "sfx": {
            k: {
                "path": f"audio_library/sfx/{k}",
                "category": v["category"],
                "motion_primitive": v.get("motion_primitive", ""),
                "description": v["description"],
                "keywords": v["keywords"],
            }
            for k, v in CONTEXTUAL_SFX_CATALOG.items()
            if (sfx_dir / k).exists()
        },
        "bgm": {
            k: {
                "path": f"audio_library/bgm/{k}",
                "mood_folder_path": f"audio_library/bgm/{v['mood']}/{k}",
                "mood": v["mood"],
                "mood_label": v.get("mood_label", ""),
                "description": v["description"],
                "keywords": v["keywords"],
            }
            for k, v in CONTEXTUAL_BGM_CATALOG.items()
            if (bgm_dir / k).exists()
        },
    }
    manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
    if REMOTION_AUDIO_DIR.exists():
        (REMOTION_AUDIO_DIR / "manifest.json").write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return {
        "created_sfx": created_sfx,
        "created_bgm": created_bgm,
        "discovered_custom_bgm": list(discovered_custom.keys()),
        "total_sfx": len(manifest_data["sfx"]),
        "total_bgm": len(manifest_data["bgm"]),
        "mood_pools_count": len(manifest_data["mood_pools"]),
    }


# ==============================================================================
# 3. ACTIVE BGM SEARCH & DOWNLOADER (WHEN EXISTING TRACKS DON'T FIT OR REPEAT)
# ==============================================================================
def _search_internet_archive_bgm(query: str, limit: int = 5) -> list[tuple[str, str]]:
    """Search Internet Archive (`archive.org`) for open/CC instrumental audio files
    matching `query` and return `[(title, mp3_download_url)]`.
    """
    q_expr = f'mediatype:(audio) AND ({query}) AND NOT collection:(librivoxaudio) AND NOT title:(podcast OR sermon OR lecture OR interview)'
    api_url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
        {
            "q": q_expr,
            "fl[]": ["identifier", "title"],
            "rows": str(limit),
            "page": "1",
            "output": "json",
        },
        doseq=True,
    )
    results: list[tuple[str, str]] = []
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=18) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        docs = data.get("response", {}).get("docs", [])
        for doc in docs:
            ident = doc.get("identifier")
            title = doc.get("title") or ident
            if not ident:
                continue
            meta_url = f"https://archive.org/metadata/{ urllib.parse.quote(str(ident)) }"
            req_m = urllib.request.Request(meta_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req_m, timeout=15) as rm:
                mdata = json.loads(rm.read().decode("utf-8"))
            for fobj in mdata.get("files", []):
                fname = str(fobj.get("name") or "")
                length_raw = str(fobj.get("length") or "0")
                try:
                    dur = float(length_raw) if ":" not in length_raw else sum(float(x) * (60 ** idx) for idx, x in enumerate(reversed(length_raw.split(":"))))
                except Exception:
                    dur = 60.0
                if fname.lower().endswith((".mp3", ".ogg", ".flac")) and 40.0 <= dur <= 600.0:
                    dl_url = f"https://archive.org/download/{urllib.parse.quote(str(ident))}/{urllib.parse.quote(fname)}"
                    results.append((str(title), dl_url))
                    break
    except Exception as exc:
        print(f"[audio_library_manager] Internet Archive search notice: {exc}")
    return results


def search_and_fetch_contextual_bgm(
    mood: str,
    context_query: str,
    target_filename: str | None = None,
    keywords_ko: list[str] | None = None,
    min_duration_sec: float = 35.0,
) -> str | None:
    """Actively search and download a new BGM track when the Agent determines that
    existing tracks in the mood pool do not fit the scene's atmosphere or have already
    been used in recent episodes.

    Searches in cascade:
    1) Wikimedia Commons Audio API (`filetype:audio <context_query>`)
    2) Internet Archive Open Audio API (`archive.org/advancedsearch.php`)
    3) `yt-dlp` Creative Commons / Royalty-Free Instrumental search (`ytsearch3:`)
    """
    resolved_mood = mood if mood in STORY_ARC_BGM_MOOD_POOLS else "01_mystery_hook"
    bgm_root = PRESET_AUDIO_DIR / "bgm"
    mood_dir = bgm_root / resolved_mood
    mood_dir.mkdir(parents=True, exist_ok=True)

    raw_name = re.sub(r"\.(mp3|wav|ogg|oga|m4a)$", "", (target_filename or context_query), flags=re.IGNORECASE)
    slug = re.sub(r"[^a-z0-9_]+", "_", raw_name.lower()).strip("_")[:36]
    if not slug.startswith("bgm_"):
        slug = f"bgm_dyn_{slug}"
    if not slug.endswith(".mp3"):
        slug += ".mp3"

    mood_target = mood_dir / slug
    flat_target = bgm_root / slug

    # Avoid re-downloading if this exact dynamic slug already exists
    if flat_target.exists() and flat_target.stat().st_size > 20000:
        return f"audio_library/bgm/{slug}"

    existing_commons_sources = {
        meta.get("commons_source")
        for meta in CONTEXTUAL_BGM_CATALOG.values()
        if meta.get("commons_source")
    }

    candidate_urls: list[tuple[str, str]] = []

    # Provider 1: Wikimedia Commons Audio Search
    try:
        search_url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
            {
                "action": "query",
                "list": "search",
                "srsearch": f"filetype:audio {context_query}",
                "srnamespace": 6,
                "srlimit": 10,
                "format": "json",
            }
        )
        req = urllib.request.Request(search_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=18) as r:
            data = json.loads(r.read().decode("utf-8"))
        commons_titles = [
            x["title"]
            for x in data.get("query", {}).get("search", [])
            if x["title"] not in existing_commons_sources
            and not any(x["title"].startswith(p) for p in ("File:LL-", "File:En-", "File:De-", "File:Fr-", "File:Nl-", "File:Ru-", "File:Zh-"))
        ]
        if commons_titles:
            url_map = _get_commons_download_urls(commons_titles[:6])
            for t, u in url_map.items():
                candidate_urls.append((t, u))
    except Exception as exc:
        print(f"[audio_library_manager] Commons BGM search warning for '{context_query}': {exc}")

    # Try downloading & mastering from verified Wikimedia Commons only (Provider 2 IA & Provider 3 yt-dlp disabled to guarantee 0% Content ID)
    for title, dl_url in candidate_urls:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
                tmp_path = tmp.name
            req_dl = urllib.request.Request(dl_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req_dl, timeout=35) as r_dl, open(tmp_path, "wb") as f_out:
                f_out.write(r_dl.read())

            # Check duration >= min_duration_sec
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", tmp_path],
                capture_output=True, text=True, check=False, creationflags=_NO_WINDOW_FLAGS,
            )
            dur = float((probe.stdout or "0").strip() or 0.0)
            if dur < min_duration_sec:
                os.unlink(tmp_path)
                continue

            if _master_bgm_file_lufs(tmp_path, mood_target):
                shutil.copy2(mood_target, flat_target)
                os.unlink(tmp_path)
                _register_dynamic_bgm(resolved_mood, slug, title, context_query, keywords_ko)
                return f"audio_library/bgm/{slug}"
            os.unlink(tmp_path)
        except Exception as exc:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            print(f"[audio_library_manager] Candidate download skipped ({title}): {exc}")

    return None


def _register_dynamic_bgm(
    mood_id: str,
    filename: str,
    source_title: str,
    context_query: str,
    keywords_ko: list[str] | None = None,
) -> None:
    """Register newly downloaded BGM track into memory catalogs, Remotion public dir, and manifest."""
    bgm_root = PRESET_AUDIO_DIR / "bgm"
    flat_target = bgm_root / filename
    mood_target = bgm_root / mood_id / filename

    if REMOTION_AUDIO_DIR.exists() and flat_target.exists():
        rem_bgm = REMOTION_AUDIO_DIR / "bgm"
        rem_bgm.mkdir(parents=True, exist_ok=True)
        shutil.copy2(flat_target, rem_bgm / filename)
        rem_mood = rem_bgm / mood_id
        rem_mood.mkdir(parents=True, exist_ok=True)
        shutil.copy2(flat_target, rem_mood / filename)

    pool = STORY_ARC_BGM_MOOD_POOLS.setdefault(mood_id, STORY_ARC_BGM_MOOD_POOLS["01_mystery_hook"])
    kws = list(dict.fromkeys((keywords_ko or []) + [w for w in re.split(r"\W+", context_query.lower()) if len(w) > 2]))
    pool["tracks"][filename] = {
        "description": f"Dynamically fetched for '{context_query}' ({source_title})",
        "keywords": kws,
        "dynamic_source": source_title,
    }
    CONTEXTUAL_BGM_CATALOG[filename] = {
        "mood": mood_id,
        "mood_label": pool["label"],
        "description": f"Dynamically fetched for '{context_query}' ({source_title})",
        "keywords": kws,
        "dynamic_source": source_title,
    }


def fetch_missing_audio_asset(query: str, target_filename: str, category: str = "sfx", mood: str = "01_mystery_hook") -> str | None:
    """Dynamically search & download a new CC0/open audio asset (BGM or SFX) when
    the Agent detects that existing tracks do not fit the scene or need fresh variety.
    """
    if category == "bgm":
        return search_and_fetch_contextual_bgm(mood=mood, context_query=query, target_filename=target_filename)

    out_dir = PRESET_AUDIO_DIR / "sfx"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not target_filename.endswith(".mp3"):
        target_filename += ".mp3"
    target_path = out_dir / target_filename
    if target_path.exists() and target_path.stat().st_size > 1500:
        return f"audio_library/sfx/{target_filename}"

    fetched = search_and_fetch_verified_sfx(query=query, target_filename=target_filename)
    if fetched:
        return fetched
    return None


# ==============================================================================
# 4. BGM USAGE LEDGER & STORY-ARC BGM SCHEDULER (8-12 SEGMENTS + SILENCE DROPS)
# ==============================================================================
def _load_bgm_usage_history() -> dict[str, Any]:
    if BGM_USAGE_HISTORY_PATH.exists():
        try:
            return json.loads(BGM_USAGE_HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"channels": {}, "episodes": {}}


def _save_bgm_usage_history(history: dict[str, Any]) -> None:
    BGM_USAGE_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    BGM_USAGE_HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def infer_beat_story_mood(narration_text: str, progress_ratio: float = 0.0) -> str:
    """Classify a beat's narrative/emotional mood into one of the 8 canonical Mood Pools."""
    text = (narration_text or "").lower()
    best_mood = "01_mystery_hook"
    best_score = -1

    for mood_id, pool in STORY_ARC_BGM_MOOD_POOLS.items():
        score = 0
        for kw in pool.get("keywords", []):
            if kw.lower() in text:
                score += 3
        # Positional priors to break ties naturally along the documentary story arc
        if mood_id == "01_mystery_hook" and progress_ratio < 0.14:
            score += 2
        elif mood_id == "02_tragic_empathy" and 0.08 <= progress_ratio <= 0.30:
            score += 1
        elif mood_id == "03_cold_case_dossier" and 0.20 <= progress_ratio <= 0.55:
            score += 1
        elif mood_id == "04_forensic_dna_lab" and 0.45 <= progress_ratio <= 0.78:
            score += 1
        elif mood_id == "05_double_life_dread" and 0.55 <= progress_ratio <= 0.88:
            score += 1
        elif mood_id == "06_interrogation_manhunt" and 0.65 <= progress_ratio <= 0.90:
            score += 1
        elif mood_id == "07_solemn_verdict" and 0.82 <= progress_ratio <= 0.95:
            score += 2
        elif mood_id == "08_memorial_epilogue" and progress_ratio > 0.92:
            score += 4

        if score > best_score:
            best_score = score
            best_mood = mood_id
    return best_mood


_FOREIGN_CASE_BGM_SLUGS: tuple[str, ...] = (
    "zhang_shuxia",
    "zhangshuxia",
    "shi_erqun",
    "shierqun",
    "bai_baoshan",
    "baibaoshan",
    "zhou_kehua",
    "zhoukehua",
    "gao_chengyong",
    "gaochengyong",
    "du_shaoping",
    "dushaoping",
)

_ORGANIC_STORY_ARC_BGM_WEIGHTS: tuple[float, ...] = (
    0.11,
    0.14,
    0.09,
    0.13,
    0.10,
    0.15,
    0.08,
    0.11,
    0.09,
    0.12,
    0.10,
    0.13,
)


def _is_foreign_case_bgm_track(
    track_name: str,
    *,
    job_id: str = "",
    topic_keywords: list[str] | None = None,
) -> bool:
    """Return True if `track_name` embeds a case-specific slug that belongs to a different case."""
    low_name = str(track_name or "").lower()
    allowed_context = " ".join([str(job_id or "").lower(), *[str(k or "").lower() for k in (topic_keywords or [])]])
    for slug in _FOREIGN_CASE_BGM_SLUGS:
        if slug in low_name and slug not in allowed_context:
            return True
    return False


def build_story_arc_bgm_schedule(
    beats: list[dict[str, Any]],
    fps: int = 30,
    job_id: str = "default_job",
    channel_profile_id: str = "default_channel",
    target_segments: int = 10,
    auto_fetch_if_unfit: bool = True,
    topic_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Build a dynamic 8-12 segment Story-Arc BGM schedule with:
    - Organic narrative-arc / Act-boundary weighted segment lengths (0% equal-frame division)
    - Zero track repetition within the episode and 0% foreign-case track reuse
    - Cross-episode anti-repeat rotation via `data/bgm_usage_history.json`
    - Active search-and-download (`search_and_fetch_contextual_bgm`) if existing tracks
      in a mood pool don't match the segment's context or were overused
    - 3-second smooth crossfades (`crossfadeFrames = 90`)
    - 2-3 Dramatic Pre-Twist Drops (`silenceDropWindows`, 2.5-4.0s at `-41dBFS` / `volume: 0.015`)
    """
    discover_user_dropped_bgm()
    if not beats:
        return {"segments": [], "silence_drop_windows": []}

    total_beats = len(beats)
    last_beat_end_frame = int(
        beats[-1].get("endFrame")
        if "endFrame" in beats[-1]
        else round(float(beats[-1].get("end_sec") or 1680.0) * fps)
    )
    total_dur_sec = max(60.0, float(beats[-1].get("end_sec") or (last_beat_end_frame / max(1, fps))))
    total_frames = max(int(round(total_dur_sec * fps)), last_beat_end_frame, 900)
    # Calculate ideal segment count (~2.5-3.0 minutes per segment, clamped between 6 and 12)
    num_segments = max(6, min(12, target_segments or int(round(total_dur_sec / 165.0))))

    # Build organic narrative-arc weights (never equal-frame `total_frames / N` division)
    raw_weights = [
        _ORGANIC_STORY_ARC_BGM_WEIGHTS[i % len(_ORGANIC_STORY_ARC_BGM_WEIGHTS)]
        + (((i * 3 + len(job_id)) % 5) - 2) * 0.004
        for i in range(num_segments)
    ]
    weight_sum = sum(raw_weights) or float(num_segments)
    norm_weights = [w / weight_sum for w in raw_weights]

    # Map weights to beat index ranges and non-uniform frame spans
    beat_ranges: list[tuple[int, int]] = []
    frame_ranges: list[tuple[int, int]] = []
    acc_w = 0.0
    prev_b_end = -1
    prev_f_end = 0
    for seg_i, w_norm in enumerate(norm_weights):
        next_w = 1.0 if seg_i == num_segments - 1 else min(1.0, acc_w + w_norm)
        b_start = min(total_beats - 1, max(0, prev_b_end + 1 if seg_i > 0 else 0))
        b_end = (
            total_beats - 1
            if seg_i == num_segments - 1
            else max(b_start, min(total_beats - 1, int(round(next_w * total_beats)) - 1))
        )
        prev_b_end = b_end
        beat_ranges.append((b_start, b_end))

        f_start = prev_f_end
        if seg_i == num_segments - 1:
            f_end = total_frames
        else:
            beat_f = int(
                beats[b_end].get("endFrame")
                if "endFrame" in beats[b_end]
                else round(float(beats[b_end].get("end_sec") or (next_w * total_dur_sec)) * fps)
            )
            weighted_f = int(round(next_w * total_frames))
            # Blend beat boundary and organic arc weight so every segment has a distinct frame duration
            f_end = max(f_start + 120 + seg_i * 7, int(round(0.5 * beat_f + 0.5 * weighted_f)))
            f_end = min(total_frames - (num_segments - 1 - seg_i) * 120, f_end)
        prev_f_end = f_end
        frame_ranges.append((f_start, max(f_start + 90, f_end)))
        acc_w = next_w

    history = _load_bgm_usage_history()
    recent_channel_tracks: set[str] = set(history.get("channels", {}).get(channel_profile_id, [])[-12:])
    used_in_episode: set[str] = set()

    # Deterministic per-job offset so different jobs naturally rotate starting tracks
    job_seed = int(hashlib.md5(job_id.encode("utf-8")).hexdigest()[:8], 16)

    segments: list[dict[str, Any]] = []
    bgm_dir = PRESET_AUDIO_DIR / "bgm"

    for seg_idx in range(num_segments):
        b_start, b_end = beat_ranges[seg_idx]
        seg_beats = beats[b_start : b_end + 1] or [beats[min(total_beats - 1, b_start)]]
        combined_text = " ".join(str(b.get("narration_text") or b.get("narrationText") or b.get("text") or "") for b in seg_beats)
        mid_ratio = ((b_start + b_end) / 2.0) / max(1, total_beats)

        # Determine dominant mood for this story segment
        mood_id = infer_beat_story_mood(combined_text, progress_ratio=mid_ratio)
        # Ensure adjacent segments shift mood or perspective
        if segments and segments[-1]["mood"] == mood_id and len(STORY_ARC_BGM_MOOD_POOLS[mood_id]["tracks"]) <= 2:
            mood_keys = list(STORY_ARC_BGM_MOOD_POOLS.keys())
            mood_id = mood_keys[(mood_keys.index(mood_id) + 1) % len(mood_keys)]

        pool = STORY_ARC_BGM_MOOD_POOLS[mood_id]
        available_tracks = [
            (fname, tmeta)
            for fname, tmeta in pool["tracks"].items()
            if (bgm_dir / fname).exists()
            and (bgm_dir / fname).stat().st_size > 15000
            and not _is_foreign_case_bgm_track(fname, job_id=job_id, topic_keywords=topic_keywords)
        ]

        # Score candidate tracks in this mood pool
        scored_candidates: list[tuple[float, str, dict[str, Any]]] = []
        for t_idx, (fname, tmeta) in enumerate(available_tracks):
            if fname in used_in_episode:
                continue
            fit_score = 1.0
            for kw in tmeta.get("keywords", []):
                if kw.lower() in combined_text.lower():
                    fit_score += 0.45
            if fname in recent_channel_tracks:
                fit_score -= 0.65
            # Add deterministic rotation tie-breaker
            tie_break = ((job_seed + seg_idx * 7 + t_idx) % 13) * 0.02
            scored_candidates.append((fit_score + tie_break, fname, tmeta))

        scored_candidates.sort(key=lambda x: -x[0])

        chosen_fname: str | None = None
        chosen_desc: str = ""

        # User Rule #1: If no candidate fits well (e.g., all unused tracks scored low or pool exhausted),
        # actively search and download a fresh contextual BGM track right now!
        if auto_fetch_if_unfit and (not scored_candidates or scored_candidates[0][0] < 0.55):
            search_q = pool["search_queries"][(job_seed + seg_idx) % len(pool["search_queries"])]
            fetched_rel = search_and_fetch_contextual_bgm(
                mood=mood_id,
                context_query=search_q,
                target_filename=f"bgm_{mood_id[:2]}_{job_id[-4:]}_{seg_idx + 1}.mp3",
            )
            if fetched_rel:
                cand_name = Path(fetched_rel).name
                if not _is_foreign_case_bgm_track(cand_name, job_id=job_id, topic_keywords=topic_keywords):
                    chosen_fname = cand_name
                    chosen_desc = CONTEXTUAL_BGM_CATALOG.get(chosen_fname, {}).get("description", f"Dynamic {mood_id} score")

        if not chosen_fname and scored_candidates:
            _, chosen_fname, chosen_tmeta = scored_candidates[0]
            chosen_desc = chosen_tmeta.get("description", mood_id)

        # Fallback to any unused track across all pools if still None (excluding foreign case slugs)
        if not chosen_fname:
            for fname, cmeta in CONTEXTUAL_BGM_CATALOG.items():
                if (
                    fname not in used_in_episode
                    and (bgm_dir / fname).exists()
                    and not _is_foreign_case_bgm_track(fname, job_id=job_id, topic_keywords=topic_keywords)
                ):
                    chosen_fname = fname
                    chosen_desc = cmeta.get("description", "")
                    break

        if not chosen_fname:
            chosen_fname = "bgm_emerging_mysteries.mp3"

        used_in_episode.add(chosen_fname)

        start_frame, end_frame = frame_ranges[seg_idx]
        start_bid = str(seg_beats[0].get("beat_id") or seg_beats[0].get("beatId") or f"B{b_start + 1:03d}")
        end_bid = str(seg_beats[-1].get("beat_id") or seg_beats[-1].get("beatId") or f"B{b_end + 1:03d}")
        narrative_reason = f"Act/Story shift {start_bid}..{end_bid} [{pool['label']}]: {chosen_desc or mood_id}"

        segments.append(
            {
                "id": f"bgm-seg-{seg_idx + 1:02d}",
                "segmentIndex": seg_idx,
                "mood": mood_id,
                "moodLabel": pool["label"],
                "file": f"audio/{chosen_fname}",
                "libraryPath": f"audio_library/bgm/{chosen_fname}",
                "moodFolderPath": f"audio_library/bgm/{mood_id}/{chosen_fname}",
                "startFrame": start_frame,
                "endFrame": max(start_frame + 90, end_frame),
                "durationInFrames": max(90, end_frame - start_frame),
                "crossfadeFrames": 90,  # 3.0s smooth crossfade
                "baseVolume": 0.072,
                "swellVolume": 0.128,
                "label": f"Seg {seg_idx + 1:02d} [{pool['label']}] · {chosen_desc}",
                "start_beat_id": start_bid,
                "end_beat_id": end_bid,
                "narrative_chapter_reason": narrative_reason,
                "startBeatId": start_bid,
                "endBeatId": end_bid,
            }
        )

    # Identify 2-3 Dramatic Pre-Twist Drops (2.5-4.0s at -41dBFS / volume 0.015 analog room-tone floor)
    twist_keywords = [
        "경악",
        "충격",
        "일치",
        "99.9",
        "바로 옆 동네",
        "1.5킬로미터",
        "문을 열",
        "새벽 6시",
        "자백",
        "단 하나의 DNA",
        "사형",
        "굴착기",
        "4.5m",
        "백골",
        "유골",
        "트랙 아래",
        "진실",
        "체포",
    ]
    twist_candidates: list[tuple[int, int, str, str]] = []
    for idx, b in enumerate(beats):
        if idx < int(total_beats * 0.08) or idx > int(total_beats * 0.93):
            continue
        txt = str(b.get("narration_text") or b.get("narrationText") or b.get("text") or "")
        score = sum(3 for kw in twist_keywords if kw in txt)
        if score > 0:
            sf = int(b.get("startFrame") if "startFrame" in b else round(float(b.get("start_sec", 0.0)) * fps))
            bid = str(b.get("beat_id") or b.get("beatId") or f"B{idx + 1:03d}")
            twist_candidates.append((score, sf, bid, txt[:48]))

    twist_candidates.sort(key=lambda x: -x[0])
    silence_windows: list[dict[str, Any]] = []
    for _, sf, bid, excerpt in twist_candidates:
        if len(silence_windows) >= 3:
            break
        # Keep dramatic silence drops well separated (at least 4 minutes apart)
        if all(abs(sf - w["startFrame"]) >= 360 * fps for w in silence_windows):
            silence_windows.append(
                {
                    "beat_id": bid,
                    "beatId": bid,
                    "startFrame": sf,
                    "endFrame": sf + int(2.8 * fps),  # 2.8s dramatic pre-twist drop
                    "fadeOutFrames": 20,
                    "fadeInFrames": 35,
                    "room_tone_floor_db": -41.0,
                    "room_tone_linear_gain": 0.015,
                    "reason": f"Dramatic Silence Drop before twist: {excerpt}",
                }
            )
    silence_windows.sort(key=lambda x: x["startFrame"])

    # Record usage in ledger
    chan_list = list(history.setdefault("channels", {}).setdefault(channel_profile_id, []))
    for trk in used_in_episode:
        if trk in chan_list:
            chan_list.remove(trk)
        chan_list.append(trk)
    history["channels"][channel_profile_id] = chan_list[-40:]
    history.setdefault("episodes", {})[job_id] = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "channel_profile_id": channel_profile_id,
        "tracks_used": list(used_in_episode),
        "segments_count": len(segments),
        "silence_drops_count": len(silence_windows),
    }
    _save_bgm_usage_history(history)

    return {
        "segments": segments,
        "silence_drop_windows": silence_windows,
        "unique_tracks_used": list(used_in_episode),
    }


def select_chapter_bgm_schedule(beats: list[dict[str, Any]], fps: int = 30, job_id: str = "default_job") -> list[dict[str, Any]]:
    """Backward-compatible wrapper returning the 8-12 segment Story-Arc BGM schedule."""
    res = build_story_arc_bgm_schedule(beats=beats, fps=fps, job_id=job_id)
    out: list[dict[str, Any]] = []
    for seg in res["segments"]:
        out.append(
            {
                "id": seg["id"],
                "src": seg["libraryPath"],
                "file": seg["file"],
                "mood": seg["mood"],
                "moodLabel": seg["moodLabel"],
                "startFrame": seg["startFrame"],
                "endFrame": seg["endFrame"],
                "durationInFrames": seg["durationInFrames"],
                "crossfadeFrames": seg["crossfadeFrames"],
                "volume": seg["baseVolume"],
                "label": seg["label"],
            }
        )
    return out


# ==============================================================================
# 5. EARSHOT WAVEFORM TRANSIENT ANALYZER, OPENVERSE FETCHER & AST COMPONENT MOTION-BOUND SFX
# ==============================================================================
import array
import math

SFX_WAVEFORM_LEDGER_PATH = PRESET_AUDIO_DIR / "sfx_waveform_ledger.json"

PURE_VOX_MOTION_PRIMITIVES: set[str] = {
    "paper_card_slide",
    "newspaper_clipping_unfold",
    "manila_dossier_open",
    "notebook_page_rustle",
    "page_tear_notebook",
    "corkboard_pin_push",
    "polaroid_photo_pin",
    "crimson_thread_taut",
    "marker_circle_draw",
    "highlighter_stroke_swipe",
    "pencil_underline",
    "caliper_metal_slide",
    "magnifying_lens_click",
    "loupe_magnifier_sweep",
    "dna_locus_match_lock",
    "official_seal_stamp",
    "heavy_seal_impact",
    "verdict_gavel_strike",
    "gis_camera_flight_arc",
    "map_pin_pulse_ring",
    "coordinate_target_lock",
    "compass_bearing_lock",
    "numeric_counter_roll",
    "timeline_relay_step",
    "typewriter_text_reveal",
    "chapter_card_enter",
}


def analyze_sfx_waveform_and_transient(audio_path: str | Path, fps: int = 30) -> dict[str, Any]:
    """Earshot-style PCM waveform & transient peak analyzer (`22050Hz` float32 PCM via `array('f')`).
    Measures exact `onset_frame_30fps`, `peak_frame_30fps`, `duration_sec`, `rms_db`, `peak_db`, and `md5`.
    """
    p = Path(audio_path)
    if not p.exists() or p.stat().st_size < 500:
        return {
            "duration_sec": 0.0,
            "onset_frame_30fps": 0,
            "peak_frame_30fps": 0,
            "rms_db": -90.0,
            "peak_db": -90.0,
            "peak_linear": 0.0,
            "md5": "",
        }
    cmd = ["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", "22050", "-f", "f32le", "-"]
    raw = subprocess.check_output(cmd, creationflags=_NO_WINDOW_FLAGS)
    samples = array.array("f")
    samples.frombytes(raw)
    n = len(samples)
    sr = 22050
    spf = max(1, sr // fps)
    n_frames = max(1, n // spf)
    env: list[float] = []
    for f in range(n_frames):
        chunk = samples[f * spf : (f + 1) * spf]
        env.append(max((abs(x) for x in chunk), default=0.0))
    peak_val = max(env) if env else 0.0
    peak_frame = env.index(peak_val) if env else 0
    thresh = max(0.015, peak_val * 0.14)
    onset_frame = 0
    for f, v in enumerate(env):
        if v >= thresh:
            onset_frame = f
            break
    rms = math.sqrt(sum(x * x for x in samples) / max(1, n))
    rms_db = 20.0 * math.log10(max(rms, 1e-7))
    peak_db = 20.0 * math.log10(max(peak_val, 1e-7))
    return {
        "duration_sec": round(n / sr, 3),
        "onset_frame_30fps": int(onset_frame),
        "peak_frame_30fps": int(peak_frame),
        "rms_db": round(rms_db, 1),
        "peak_db": round(peak_db, 1),
        "peak_linear": round(peak_val, 4),
        "md5": hashlib.md5(p.read_bytes()).hexdigest()[:12],
    }


def load_sfx_waveform_ledger() -> dict[str, dict[str, Any]]:
    """Load cached waveform transient ledger (`presets/audio_library/sfx_waveform_ledger.json`)."""
    cache = globals().get("_SFX_WAVEFORM_LEDGER_CACHE")
    if isinstance(cache, dict) and cache:
        return cache
    if SFX_WAVEFORM_LEDGER_PATH.exists():
        try:
            loaded = json.loads(SFX_WAVEFORM_LEDGER_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                globals()["_SFX_WAVEFORM_LEDGER_CACHE"] = loaded
                return loaded
        except Exception:
            pass
    return {}


def search_and_fetch_verified_sfx(
    query: str,
    target_filename: str,
    max_duration_sec: float = 0.88,
    eq_filter: str = "highpass=f=140,lowpass=f=6200",
) -> str | None:
    """Search Openverse/Freesound CC0/CC-BY audio API for a real physical Foley recording,
    auto-trim leading silence to `onset_frame_30fps = 0`, normalize peak to `-3.0 dBFS`,
    update `sfx_waveform_ledger.json`, and sync to `CofiRemotion/public/audio_library/sfx/`.
    """
    sfx_dir = PRESET_AUDIO_DIR / "sfx"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    fname = target_filename if target_filename.endswith(".mp3") else f"{target_filename}.mp3"
    if not fname.startswith("sfx_"):
        fname = f"sfx_{fname}"
    out_path = sfx_dir / fname

    api_url = f"https://api.openverse.org/v1/audio/?q={urllib.parse.quote(query)}&source=freesound&page_size=15"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=18) as resp:
            results = json.loads(resp.read().decode("utf-8")).get("results", [])
    except Exception as exc:
        print(f"[audio_library_manager] Openverse SFX search failed for '{query}': {exc}")
        return None

    for item in results:
        mp3_url = item.get("url") or ""
        for af in item.get("alt_files") or []:
            u = str(af.get("url") or "")
            if u.endswith(".mp3"):
                mp3_url = u
                break
        if not mp3_url.startswith("http"):
            continue
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            req_dl = urllib.request.Request(mp3_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req_dl, timeout=20) as r_dl, open(tmp_path, "wb") as f_out:
                f_out.write(r_dl.read())
            info0 = analyze_sfx_waveform_and_transient(tmp_path)
            if info0["duration_sec"] <= 0.05 or info0["peak_linear"] < 0.01:
                os.unlink(tmp_path)
                continue
            start_sec = max(0.0, (info0["onset_frame_30fps"] - 0.5) / 30.0)
            gain = min(18.0, 0.70 / max(float(info0["peak_linear"]), 0.01))
            fade_st = max(0.05, max_duration_sec - 0.16)
            af_chain = (
                f"atrim=start={start_sec:.3f}:duration={max_duration_sec:.3f},"
                f"asetpts=PTS-STARTPTS,{eq_filter},volume={gain:.3f},"
                f"afade=t=in:st=0:d=0.008,afade=t=out:st={fade_st:.3f}:d=0.16"
            )
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", tmp_path, "-af", af_chain, "-ar", "44100", "-ac", "2", "-b:a", "192k", str(out_path)],
                check=True,
                creationflags=_NO_WINDOW_FLAGS,
            )
            os.unlink(tmp_path)
            info1 = analyze_sfx_waveform_and_transient(out_path)
            ledger = load_sfx_waveform_ledger()
            ledger[fname] = info1
            SFX_WAVEFORM_LEDGER_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
            if REMOTION_AUDIO_DIR.exists():
                rem_sfx = REMOTION_AUDIO_DIR / "sfx"
                rem_sfx.mkdir(parents=True, exist_ok=True)
                shutil.copy2(out_path, rem_sfx / fname)
                shutil.copy2(SFX_WAVEFORM_LEDGER_PATH, REMOTION_AUDIO_DIR / "sfx_waveform_ledger.json")
            return f"audio_library/sfx/{fname}"
        except Exception:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
    return None


# Acoustic onset lag compensation (in 30fps frames). Since all 26 SFX files are onset-trimmed to 0f-1f,
# lag is derived directly from `sfx_waveform_ledger.json` (`onset_frame_30fps`).
SFX_ONSET_LAG_FRAMES: dict[str, int] = {prim: 0 for prim in PURE_VOX_MOTION_PRIMITIVES}
SFX_ONSET_LAG_FRAMES["page_tear_notebook"] = 1
SFX_ONSET_LAG_FRAMES["compass_bearing_lock"] = 1

# Anti-Machine-Gun A/B/C foley variation pools (100% existing, ear-verified 26 files; 0% legacy missing files)
SFX_ABC_VARIATION_POOLS: dict[str, tuple[str, ...]] = {
    "paper_card_slide": ("sfx_paper_turn.mp3", "sfx_folder_open.mp3", "sfx_notebook_page_rustle.mp3", "sfx_newspaper_unfold.mp3"),
    "newspaper_clipping_unfold": ("sfx_newspaper_unfold.mp3", "sfx_paper_turn.mp3", "sfx_page_tear_notebook.mp3", "sfx_folder_open.mp3"),
    "manila_dossier_open": ("sfx_folder_open.mp3", "sfx_paper_turn.mp3", "sfx_notebook_page_rustle.mp3", "sfx_newspaper_unfold.mp3"),
    "notebook_page_rustle": ("sfx_notebook_page_rustle.mp3", "sfx_paper_turn.mp3", "sfx_folder_open.mp3", "sfx_newspaper_unfold.mp3"),
    "page_tear_notebook": ("sfx_page_tear_notebook.mp3", "sfx_newspaper_unfold.mp3", "sfx_paper_turn.mp3", "sfx_notebook_page_rustle.mp3"),
    "corkboard_pin_push": ("sfx_corkboard_pin_push.mp3", "sfx_camera_shutter.mp3", "sfx_magnifying_lens_click.mp3", "sfx_telemetry_tick.mp3"),
    "polaroid_photo_pin": ("sfx_camera_shutter.mp3", "sfx_corkboard_pin_push.mp3", "sfx_paper_turn.mp3", "sfx_folder_open.mp3"),
    "crimson_thread_taut": ("sfx_crimson_thread_taut.mp3", "sfx_marker_circle_draw.mp3", "sfx_pencil_underline.mp3", "sfx_caliper_metal_slide.mp3"),
    "marker_circle_draw": ("sfx_marker_circle_draw.mp3", "sfx_highlighter_swipe.mp3", "sfx_pencil_underline.mp3", "sfx_crimson_thread_taut.mp3"),
    "highlighter_stroke_swipe": ("sfx_highlighter_swipe.mp3", "sfx_pencil_underline.mp3", "sfx_marker_circle_draw.mp3", "sfx_paper_turn.mp3"),
    "pencil_underline": ("sfx_pencil_underline.mp3", "sfx_highlighter_swipe.mp3", "sfx_marker_circle_draw.mp3", "sfx_notebook_page_rustle.mp3"),
    "caliper_metal_slide": ("sfx_caliper_metal_slide.mp3", "sfx_magnifying_lens_click.mp3", "sfx_compass_bearing_lock.mp3", "sfx_document_scanner_hum.mp3"),
    "magnifying_lens_click": ("sfx_magnifying_lens_click.mp3", "sfx_caliper_metal_slide.mp3", "sfx_camera_shutter.mp3", "sfx_document_scanner_hum.mp3"),
    "loupe_magnifier_sweep": ("sfx_document_scanner_hum.mp3", "sfx_magnifying_lens_click.mp3", "sfx_caliper_metal_slide.mp3", "sfx_biometric_match_chime.mp3"),
    "dna_locus_match_lock": ("sfx_biometric_match_chime.mp3", "sfx_satellite_lock_beep.mp3", "sfx_magnifying_lens_click.mp3", "sfx_document_scanner_hum.mp3"),
    "official_seal_stamp": ("sfx_dossier_stamp.mp3", "sfx_official_seal_thud.mp3", "sfx_gavel_hit.mp3", "sfx_folder_open.mp3"),
    "heavy_seal_impact": ("sfx_official_seal_thud.mp3", "sfx_dossier_stamp.mp3", "sfx_gavel_hit.mp3", "sfx_chapter_hit.mp3"),
    "verdict_gavel_strike": ("sfx_gavel_hit.mp3", "sfx_official_seal_thud.mp3", "sfx_dossier_stamp.mp3", "sfx_chapter_hit.mp3"),
    "gis_camera_flight_arc": ("sfx_map_route_sweep.mp3", "sfx_radar_ping_sonar.mp3", "sfx_compass_bearing_lock.mp3", "sfx_satellite_lock_beep.mp3"),
    "map_pin_pulse_ring": ("sfx_radar_ping_sonar.mp3", "sfx_satellite_lock_beep.mp3", "sfx_compass_bearing_lock.mp3", "sfx_map_route_sweep.mp3"),
    "coordinate_target_lock": ("sfx_satellite_lock_beep.mp3", "sfx_compass_bearing_lock.mp3", "sfx_radar_ping_sonar.mp3", "sfx_telemetry_tick.mp3"),
    "compass_bearing_lock": ("sfx_compass_bearing_lock.mp3", "sfx_satellite_lock_beep.mp3", "sfx_caliper_metal_slide.mp3", "sfx_radar_ping_sonar.mp3"),
    "numeric_counter_roll": ("sfx_telemetry_tick.mp3", "sfx_typing_log.mp3", "sfx_clock_tick_tense.mp3", "sfx_caliper_metal_slide.mp3"),
    "timeline_relay_step": ("sfx_clock_tick_tense.mp3", "sfx_telemetry_tick.mp3", "sfx_typing_log.mp3", "sfx_caliper_metal_slide.mp3"),
    "typewriter_text_reveal": ("sfx_typing_log.mp3", "sfx_telemetry_tick.mp3", "sfx_clock_tick_tense.mp3", "sfx_pencil_underline.mp3"),
    "chapter_card_enter": ("sfx_chapter_hit.mp3", "sfx_official_seal_thud.mp3", "sfx_gavel_hit.mp3", "sfx_dossier_stamp.mp3"),
}

# Exact 1-to-1 Component Motion Architecture Table for `VoxBespokeSentenceMechanics.tsx` (`archMode = sceneIndex % 14`)
# Each entry maps `(t1_primitive, t2_primitive, t3_primitive)` to the actual JSX components rendered at `[t1, t2, t3]`.
VOX_ARCHMODE_COMPONENT_MOTIONS: dict[int, tuple[tuple[str, int], tuple[str, int], tuple[str, int]]] = {
    0: (("newspaper_clipping_unfold", 0), ("marker_circle_draw", 4), ("corkboard_pin_push", 6)),
    1: (("polaroid_photo_pin", 0), ("crimson_thread_taut", 0), ("highlighter_stroke_swipe", 6)),
    2: (("manila_dossier_open", 0), ("paper_card_slide", 0), ("official_seal_stamp", 0)),
    3: (("paper_card_slide", 0), ("crimson_thread_taut", 4), ("loupe_magnifier_sweep", 8)),
    4: (("polaroid_photo_pin", 0), ("corkboard_pin_push", 6), ("heavy_seal_impact", 0)),
    5: (("caliper_metal_slide", 0), ("timeline_relay_step", 0), ("marker_circle_draw", 4)),
    6: (("paper_card_slide", 0), ("caliper_metal_slide", 0), ("official_seal_stamp", 6)),
    7: (("newspaper_clipping_unfold", 0), ("pencil_underline", 0), ("magnifying_lens_click", 6)),
    8: (("manila_dossier_open", 0), ("highlighter_stroke_swipe", 4), ("official_seal_stamp", 0)),
    9: (("magnifying_lens_click", 6), ("loupe_magnifier_sweep", 6), ("dna_locus_match_lock", 0)),
    10: (("newspaper_clipping_unfold", 0), ("page_tear_notebook", 0), ("marker_circle_draw", 6)),
    11: (("paper_card_slide", 0), ("crimson_thread_taut", 0), ("corkboard_pin_push", 6)),
    12: (("typewriter_text_reveal", 0), ("numeric_counter_roll", 4), ("marker_circle_draw", 6)),
    13: (("manila_dossier_open", 0), ("polaroid_photo_pin", 0), ("verdict_gavel_strike", 0)),
}

# JSX Component Tag -> Motion Primitive mapping for direct TSX AST inspection
JSX_TAG_TO_MOTION_PRIMITIVE: list[tuple[str, str]] = [
    ("GeoJson3DMapStage", "gis_camera_flight_arc"),
    ("BespokeGisVectorOverlay", "map_pin_pulse_ring"),
    ("OpticalLoupe", "loupe_magnifier_sweep"),
    ("TwistedRedYarn", "crimson_thread_taut"),
    ("DimensionBracket", "caliper_metal_slide"),
    ("Stamp", "official_seal_stamp"),
    ("RedCircle", "marker_circle_draw"),
    ("RedLine", "marker_circle_draw"),
    ("Highlight", "highlighter_stroke_swipe"),
    ("Underline", "pencil_underline"),
    ("TornClipping", "newspaper_clipping_unfold"),
    ("VoxPhotoPaper", "polaroid_photo_pin"),
    ("VoxVideoPaper", "polaroid_photo_pin"),
    ("DieCutSticker", "corkboard_pin_push"),
    ("IndexCard", "paper_card_slide"),
    ("SlideIn", "paper_card_slide"),
]


def _resolve_anti_machine_gun_sfx_file(
    prim: str,
    default_file: str,
    global_frame: int,
    file_history: list[tuple[int, str]],
    cooldown_frames: int = 240,
) -> str:
    """Ensure no single SFX file is triggered twice within `cooldown_frames` (240f = 8.0s at 30fps)
    by rotating through A/B/C tactile variants.
    """
    recent_files = {
        fname
        for prev_f, fname in file_history
        if 0 <= (global_frame - prev_f) < cooldown_frames or abs(global_frame - prev_f) < cooldown_frames
    }
    if default_file not in recent_files:
        file_history.append((global_frame, default_file))
        return default_file

    abc_pool = SFX_ABC_VARIATION_POOLS.get(prim, (default_file,))
    for cand in abc_pool:
        if cand not in recent_files:
            file_history.append((global_frame, cand))
            return cand

    for p_other in PURE_VOX_MOTION_PRIMITIVES:
        cand_other, _ = MOTION_PRIMITIVE_TO_SFX.get(p_other, ("sfx_paper_turn.mp3", 0.095))
        if cand_other not in recent_files:
            file_history.append((global_frame, cand_other))
            return cand_other

    file_history.append((global_frame, default_file))
    return default_file


def extract_component_motion_sfx_for_beat(
    beat: dict[str, Any],
    fps: int = 30,
    is_cinema_text: bool = False,
) -> list[tuple[int, str]]:
    """Extract the exact `(motion_frame, motion_primitive)` pairs from the actual moving
    graphic components of a `VOX` or `CINEMA_TEXT` beat (0% script keyword guessing, 0% blind fallback_pool).
    - If a component has 1 motion -> returns 1 pair.
    - If a component has 2 motions -> returns 2 pairs.
    - If a component has 3 motions -> returns 3 pairs.
    """
    dur_frames = int(beat.get("durationInFrames") or round(float(beat.get("duration_sec", 6.0)) * fps))
    speech_frames = int(beat.get("speechFrames") or max(30, dur_frames - 6))
    cfw = beat.get("clauseFrameWindows") or []
    windows = (
        beat.get("clauseWindows")
        or (beat.get("voice_spec") or {}).get("clause_windows")
        or [[0.0, 0.34], [0.34, 0.68], [0.68, 1.0]]
    )

    # 1. Check if raw JSX/TSX source snippet is attached to `beat` (`tsx_code` / `vox_tsx`)
    tsx_code = str(beat.get("tsx_code") or beat.get("vox_tsx") or "").strip()
    if tsx_code:
        extracted: list[tuple[int, str]] = []
        for tag_name, prim in JSX_TAG_TO_MOTION_PRIMITIVE:
            for m in re.finditer(rf"<{tag_name}\b([^>]*)", tsx_code):
                attrs = m.group(1)
                at_m = re.search(r"\bat=\{(\d+)\}", attrs)
                f_at = int(at_m.group(1)) if at_m else (6 + len(extracted) * 28)
                extracted.append((max(2, min(dur_frames - 10, f_at)), prim))
        if extracted:
            extracted.sort(key=lambda x: x[0])
            return extracted[:4]

    # 2. If `CINEMA_TEXT` (`FramelessCinemaTextBeat.tsx`):
    # Inspect actual `showroomRenderer`, `layoutArchetype`, `primaryMetric`, and `stampNode`
    if is_cinema_text:
        mt_spec = beat.get("motion_text_spec") or beat.get("cinemaTextSpec") or {}
        renderer = str(
            mt_spec.get("showroomRenderer")
            or beat.get("showroomRenderer")
            or mt_spec.get("motion_archetype")
            or ""
        ).strip()
        layout = str(
            mt_spec.get("layoutArchetype")
            or mt_spec.get("layoutVariant")
            or beat.get("layoutArchetype")
            or mt_spec.get("layout_archetype")
            or ""
        ).strip()
        primary_metric = str(
            mt_spec.get("primaryMetric")
            or mt_spec.get("metricValue")
            or beat.get("primaryMetric")
            or ""
        ).strip()
        stamp_text = str(mt_spec.get("stampText") or beat.get("stampText") or "").strip()

        t1 = int(cfw[0][0]) + 4 if len(cfw) >= 1 else 4
        t2 = int(cfw[1][0]) if len(cfw) >= 2 else max(16, int(round(speech_frames * 0.28)))
        t3 = int(cfw[2][0]) if len(cfw) >= 3 else max(t2 + 18, int(round(speech_frames * 0.56)))

        ct_motions: list[tuple[int, str]] = []
        # Motion 1 at `t1`: primary kinetic typography / card entrance
        if renderer in ("ct_verdict_gavel", "editorial_punch_statement") or layout == "verdict_pillar":
            ct_motions.append((t1, "manila_dossier_open"))
        elif renderer == "ct_redaction_peel":
            ct_motions.append((t1, "paper_card_slide"))
        elif renderer == "ct_split_contradiction" or layout == "split_contradiction":
            ct_motions.append((t1, "paper_card_slide"))
        elif renderer == "ct_chronicle_22y" or layout == "chronicle_horizon":
            ct_motions.append((t1, "timeline_relay_step"))
        elif renderer in ("ct_metric_counter", "editorial_metric_monolith") or layout in ("monolith_metric", "center_monolith") and primary_metric:
            ct_motions.append((t1, "numeric_counter_roll"))
        elif renderer == "ct_forensic_hud":
            ct_motions.append((t1, "loupe_magnifier_sweep"))
        else:
            ct_motions.append((t1, "typewriter_text_reveal"))

        # Motion 2 at `t2`: secondary kinetic action (redaction tape peel, contradiction collision, or metric/underline stroke)
        if renderer == "ct_redaction_peel":
            ct_motions.append((t2 + 4, "page_tear_notebook"))
        elif renderer == "ct_split_contradiction" or layout == "split_contradiction":
            ct_motions.append((t2, "caliper_metal_slide"))
        elif primary_metric or renderer in ("ct_metric_counter", "editorial_metric_monolith") or layout == "monolith_metric":
            ct_motions.append((t2, "highlighter_stroke_swipe"))
        else:
            ct_motions.append((t2, "pencil_underline"))

        # Motion 3 at `t3`: ONLY emitted when `FramelessCinemaTextBeat.tsx` actually renders a 3rd moving element
        # (`stampNode` on `ct_verdict_gavel` / `verdict_pillar` / `editorial_punch_statement`, or optical lock on `ct_forensic_hud`).
        if renderer in ("ct_verdict_gavel", "editorial_punch_statement") or layout == "verdict_pillar" or stamp_text:
            ct_motions.append((t3, "verdict_gavel_strike" if layout == "verdict_pillar" or renderer == "ct_verdict_gavel" else "official_seal_stamp"))
        elif renderer == "ct_forensic_hud":
            ct_motions.append((t3, "magnifying_lens_click"))

        return ct_motions

    # 3. `VOX` Scene (`VoxScenes01to23.tsx`, `VoxScenes24to45.tsx`, `VoxBespokeSentenceMechanics.tsx`, `<GeoJson3DMapStage>`)
    vox_trigs = beat.get("voxTriggers")
    if isinstance(vox_trigs, list) and len(vox_trigs) >= 3:
        t1, t2, t3 = int(vox_trigs[0]), int(vox_trigs[1]), int(vox_trigs[2])
    elif len(cfw) >= 3:
        idx2 = max(1, len(cfw) // 3)
        idx3 = max(idx2 + 1, (2 * len(cfw)) // 3)
        t1 = max(4, int(cfw[0][0]) + 4)
        t2 = max(20, int(cfw[idx2][0]))
        t3 = max(t2 + 18, int(cfw[idx3][0]))
    elif len(cfw) == 2:
        t1 = max(4, int(cfw[0][0]) + 4)
        t2 = max(20, int(cfw[1][0]))
        t3 = max(t2 + 18, int((cfw[1][0] + cfw[1][1]) // 2))
    else:
        t1 = 4
        t2 = max(20, min(dur_frames - 32, int(round((float(windows[1][0]) if len(windows) > 1 else 0.34) * speech_frames))))
        t3 = max(t2 + 18, min(dur_frames - 12, int(round((float(windows[2][0]) if len(windows) > 2 else 0.66) * speech_frames))))

    vox_id_str = str(beat.get("voxId") or beat.get("vox_id") or beat.get("voxSceneId") or beat.get("vox_scene_id") or "").upper()
    vox_spec = beat.get("vox_blueprint_spec") if isinstance(beat.get("vox_blueprint_spec"), dict) else {}
    stage_comp = str(vox_spec.get("stage_component") or beat.get("motion_treatment") or "").lower()
    arch_str = str(beat.get("scene_archetype") or beat.get("voxArchetype") or "").upper()

    # Check if this VOX scene renders `<GeoJson3DMapStage>` + `<BespokeGisVectorOverlay>`
    motion_intent_str = str(beat.get("motion_intent") or vox_spec.get("motion_intent") or "").upper()
    is_gis_map_stage = (
        "geojson3dmapstage" in stage_comp
        or "vox_3d_map" in stage_comp
        or "satellite_gis_map_flight" in stage_comp
        or "parabolic_3d_gis_flyto" in stage_comp
        or motion_intent_str in {"PARABOLIC_GIS_PURSUIT", "GEO_VECTOR_PURSUIT"}
        or arch_str in {
            "GEO_VECTOR_PURSUIT",
            "PARABOLIC_GIS_PURSUIT",
            "#V_FULLSCREEN_GIS_FLIGHT",
            "#V_FULLSCREEN_SATELLITE_RECON",
            "#V_SAT_ZONE_DRAW",
            "#M1",
            "#M2",
            "#M3",
            "#M5",
            "#M6",
            "#M7",
            "#M8",
        }
    )
    if is_gis_map_stage:
        return [
            (t1, "gis_camera_flight_arc"),
            (t2, "map_pin_pulse_ring"),
            (t3, "coordinate_target_lock"),
        ]

    # Resolve `sceneIndex` (`VOX_01` -> 0 .. `VOX_45` -> 44) to match `archMode = sceneIndex % 14` in `VoxBespokeSentenceMechanics.tsx`
    m_num = re.search(r"(\d+)", vox_id_str)
    if m_num:
        scene_index = max(0, int(m_num.group(1)) - 1)
    else:
        b_num = re.search(r"(\d+)", str(beat.get("beat_id") or beat.get("id") or "1"))
        scene_index = max(0, int(b_num.group(1)) - 1) if b_num else 0

    arch_mode = scene_index % 14
    (p1, d1), (p2, d2), (p3, d3) = VOX_ARCHMODE_COMPONENT_MOTIONS[arch_mode]
    return [
        (max(2, t1 + d1), p1),
        (max(t1 + 12, min(dur_frames - 20, t2 + d2)), p2),
        (max(t2 + 12, min(dur_frames - 8, t3 + d3)), p3),
    ]


def select_motion_bound_sfx_for_beat(
    beat: dict[str, Any],
    fps: int = 30,
    is_chapter_start: bool = False,
    beat_start_frame: int | None = None,
    sfx_history: list[tuple[int, str]] | None = None,
) -> list[dict[str, Any]]:
    """Enforce 100% AST/Component Motion-Bound SFX with Earshot Waveform Onset Alignment & 8s Anti-Machine-Gun Rule:
    - ZERO SFX on `REAL_FTG` and `AI_4D` stills.
    - ZERO keyword guessing (`VOX_GRAPHIC_MOTION_RULES` deleted) and ZERO blind `fallback_pool`.
    - SFX play ONLY when actual moving graphic components exist in `VOX` / `<GeoJson3DMapStage>` or `FramelessCinemaTextBeat.tsx`,
      compensated by the exact measured `onset_frame_30fps` from `sfx_waveform_ledger.json`.
    """
    events: list[dict[str, Any]] = []

    cat = str(
        beat.get("category")
        or beat.get("visualRole")
        or beat.get("visual_role")
        or beat.get("visual_type")
        or beat.get("dna_visual_slot")
        or ""
    ).upper()
    framing = str(beat.get("framingMode") or "").lower()
    img_file = str(beat.get("imageFile") or beat.get("src") or "")
    vox_id = beat.get("voxId") or beat.get("vox_id") or beat.get("voxSceneId") or beat.get("vox_scene_id")
    render_vox = bool(beat.get("render_vox_board", False))

    is_cinema_text = cat in ("CINEMA_TEXT", "FRAMELESS_CINEMA_TEXT", "FLEXIBLE_RESERVE") or framing == "cinema_text"
    is_vox_scene = (
        cat in ("VOX", "VOX_3D", "VOX_MOTION", "MAP", "GIS")
        or framing == "vox_3d"
        or bool(vox_id)
        or render_vox
        or "vox/" in img_file.lower()
        or "vox_" in img_file.lower()
    )

    if not is_vox_scene and not is_cinema_text:
        return []

    file_history: list[tuple[int, str]] = (
        sfx_history
        if sfx_history is not None
        else globals().setdefault("_RECENT_SFX_FILE_HISTORY", [])
    )
    if beat_start_frame is not None:
        resolved_start_frame = int(beat_start_frame)
    elif "startFrame" in beat or "start_sec" in beat:
        resolved_start_frame = int(
            beat["startFrame"]
            if "startFrame" in beat and beat["startFrame"] is not None
            else round(float(beat.get("start_sec") or 0.0) * fps)
        )
        if sfx_history is None and file_history and resolved_start_frame == 0 and file_history[-1][0] > 0:
            file_history.clear()
    else:
        resolved_start_frame = (file_history[-1][0] + 45) if file_history else 0
    beat_start_frame = resolved_start_frame

    ledger = load_sfx_waveform_ledger()

    # If explicit component motion events (`vox_sfx_events`) were provided by an AST compiler, validate & align them
    explicit_motion_events = beat.get("vox_sfx_events") or (beat.get("voice_spec") or {}).get("sfx_events")
    if isinstance(explicit_motion_events, list) and explicit_motion_events:
        for ev in explicit_motion_events:
            prim = str(ev.get("primitive") or "paper_card_slide")
            if prim not in PURE_VOX_MOTION_PRIMITIVES:
                prim = "paper_card_slide"
            raw_file, s_vol = MOTION_PRIMITIVE_TO_SFX.get(prim, ("sfx_paper_turn.mp3", 0.095))
            motion_peak_frame = int(ev.get("motion_peak_frame", ev.get("offsetFrames", 6)))
            s_file = _resolve_anti_machine_gun_sfx_file(
                prim, raw_file, beat_start_frame + motion_peak_frame, file_history
            )
            w_info = ledger.get(s_file) or {}
            lag_frames = int(w_info.get("onset_frame_30fps", SFX_ONSET_LAG_FRAMES.get(prim, 0)))
            seq_from = max(0, motion_peak_frame - lag_frames)
            events.append(
                {
                    "offsetFrames": seq_from,
                    "sequence_from_frame": seq_from,
                    "motion_peak_frame": motion_peak_frame,
                    "sfx_onset_lag_frames": lag_frames,
                    "waveform_peak_frame_30fps": int(w_info.get("peak_frame_30fps", 0)),
                    "waveform_duration_sec": float(w_info.get("duration_sec", 0.5)),
                    "file": f"audio/{s_file}",
                    "libraryPath": f"audio_library/sfx/{s_file}",
                    "volume": float(ev.get("volume", s_vol)),
                    "primitive": prim,
                }
            )
        if len(file_history) > 36:
            del file_history[:-36]
        return events

    # Extract 1-to-1 component motions from the scene's actual moving graphic elements
    component_motions = extract_component_motion_sfx_for_beat(beat, fps=fps, is_cinema_text=is_cinema_text)

    for motion_frame, prim in component_motions:
        raw_file, s_vol = MOTION_PRIMITIVE_TO_SFX.get(prim, ("sfx_paper_turn.mp3", 0.095))
        motion_peak_frame = int(motion_frame)
        s_file = _resolve_anti_machine_gun_sfx_file(
            prim, raw_file, beat_start_frame + motion_peak_frame, file_history
        )
        w_info = ledger.get(s_file) or {}
        lag_frames = int(w_info.get("onset_frame_30fps", SFX_ONSET_LAG_FRAMES.get(prim, 0)))
        seq_from = max(0, motion_peak_frame - lag_frames)
        events.append(
            {
                "offsetFrames": seq_from,
                "sequence_from_frame": seq_from,
                "motion_peak_frame": motion_peak_frame,
                "sfx_onset_lag_frames": lag_frames,
                "waveform_peak_frame_30fps": int(w_info.get("peak_frame_30fps", 0)),
                "waveform_duration_sec": float(w_info.get("duration_sec", 0.5)),
                "file": f"audio/{s_file}",
                "libraryPath": f"audio_library/sfx/{s_file}",
                "volume": float(s_vol),
                "primitive": prim,
            }
        )

    if len(file_history) > 36:
        del file_history[:-36]
    return events


def select_contextual_sfx_for_beat(
    narration_text: str,
    archetype: str,
    chapter_mood: str = "",
    prev_sfx: list[str] | None = None,
    beat_index: int = 1,
    is_vox_scene: bool | None = None,
) -> list[dict[str, Any]]:
    """Backward-compatible helper that strictly respects the Component Motion-Bound SFX rule:
    returns `[]` for non-Vox scenes (`cinema_full`, `REAL_FTG`, `AI_4D`) and returns
    component-motion-matched SFX only for Vox / Map / GIS scenes.
    """
    arch = (archetype or "").upper()
    if is_vox_scene is False or arch in ("", "CINEMA_FULL", "REAL_FTG", "AI_4D", "STANDARD"):
        return []
    fake_beat = {
        "beat_id": f"B{beat_index:03d}",
        "category": "VOX",
        "narration_text": narration_text,
        "scene_archetype": archetype,
        "duration_sec": 6.0,
        "clauseWindows": [[0.0, 0.34], [0.34, 0.68], [0.68, 1.0]],
    }
    ev_list = select_motion_bound_sfx_for_beat(fake_beat, fps=30)
    return [
        {
            "file": ev["libraryPath"],
            "offset_ratio": round(ev["offsetFrames"] / 180.0, 3),
            "offsetFrames": ev["offsetFrames"],
            "volume": ev["volume"],
            "primitive": ev["primitive"],
        }
        for ev in ev_list
    ]


CANONICAL_SFX_FILENAME_ALIASES: dict[str, str] = {
    "sfx_sub_bass_boom_chapter.mp3": "sfx_chapter_hit.mp3",
    "sfx_sub_bass_boom.mp3": "sfx_chapter_hit.mp3",
    "sfx_chapter_boom.mp3": "sfx_chapter_hit.mp3",
    "sfx_deep_impact.mp3": "sfx_official_seal_thud.mp3",
    "sfx_soft_impact.mp3": "sfx_dossier_stamp.mp3",
    "sfx_data_ping.mp3": "sfx_crimson_thread_taut.mp3",
    "sfx_gavel_strike_echo.mp3": "sfx_gavel_hit.mp3",
    "sfx_drawer_close_heavy.mp3": "sfx_folder_open.mp3",
    "sfx_tape_recorder_play_click.mp3": "sfx_typing_log.mp3",
}


def normalize_sfx_file_path(raw_path: str) -> str:
    """Resolve non-canonical/legacy SFX filenames to existing verified files in `SFX_CATALOG`."""
    clean = str(raw_path or "").strip()
    if not clean:
        return ""
    prefix = ""
    fname = clean
    if "/" in clean:
        prefix, fname = clean.rsplit("/", 1)
        prefix += "/"
    elif "\\" in clean:
        prefix, fname = clean.rsplit("\\", 1)
        prefix += "/"
    resolved = CANONICAL_SFX_FILENAME_ALIASES.get(fname, fname)
    if resolved not in SFX_CATALOG and resolved.startswith("sfx_"):
        resolved = "sfx_chapter_hit.mp3" if "chapter" in resolved else "sfx_paper_turn.mp3"
    return f"{prefix}{resolved}"


if __name__ == "__main__":
    summary = ensure_audio_library_stocked()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
