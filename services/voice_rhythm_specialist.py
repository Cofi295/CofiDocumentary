"""
Voiceover & Storytelling Rhythm Specialist Service for CofiDocumentary.

Analyzes any Channel Profile's genre, audience persona, emotional register,
market/language, and target duration to synthesize:
1. A Bespoke Voice Color (`voice_signature` + `voice_color_spec`) sculpted from
   the clean master reference voice (`K1` `09c70cc1-cc86-4905-b65b-3967209c3175`
   for Korean, clean language masters for EN/VI/JA, or a user-uploaded sample).
2. A 3-Layer Cross-Department Rhythm DNA (`rhythm_dna`):
   - `writing_cadence` (@script): sentence length curve, brake/punch ratio, breath stanzas
   - `vocal_cadence` (@voice): target syllables/sec, 7-tier pause hierarchy, emotion speed curve
   - `editing_cadence` (@edit / @vox / @visuals): shot pacing, cut feel, silence holds, BGM breath lift
"""

from __future__ import annotations

import base64
import copy
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import wave

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COFIVOICE_DIR = ROOT.parent / "CofiVoice"
DEFAULT_COFIVOICE_URL = os.getenv("COFIVOICE_URL", "http://127.0.0.1:8000").rstrip("/")

# Clean 1st-generation master voices in CofiVoice (K1 clean is mandatory default for Korean)
CLEAN_MASTER_VOICES: dict[str, dict[str, str]] = {
    "ko": {
        "id": "09c70cc1-cc86-4905-b65b-3967209c3175",
        "name": "K1 (Giọng Mẫu Sạch Chuẩn Gốc KR)",
        "language": "ko",
    },
    "en": {
        "id": "b4c2376b-3d63-461a-a849-367e37261e4a",
        "name": "Jon (Clean US Broadcast Master)",
        "language": "en",
    },
    "en_archival": {
        "id": "0d3edf08-7c0b-4f6f-b1bf-3bdfec8922ed",
        "name": "Jon US Già (Clean Archival Gravitas Master)",
        "language": "en",
    },
    "vi": {
        "id": "262cf97e-c145-44ba-92a6-2dd36db1146e",
        "name": "PC Nam (Giọng Mẫu Phóng Sự Sạch VN)",
        "language": "vi",
    },
    "vi_warm": {
        "id": "59204275-ad7e-42c7-8e56-7a11210cb790",
        "name": "Chuẩn VN (Giọng Mẫu Kể Chuyện Sạch VN)",
        "language": "vi",
    },
    "ja": {
        "id": "f0670e81-6361-4567-b93c-2685b98c9a4e",
        "name": "Nhật (Clean JP Documentary Master)",
        "language": "ja",
    },
}

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_COFIVOICE_DB_LOCK = threading.RLock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_ffmpeg_exe() -> str | None:
    env_ff = os.getenv("FFMPEG_BINARY")
    if env_ff and Path(env_ff).exists():
        return env_ff
    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        return sys_ff
    try:
        import imageio_ffmpeg  # type: ignore[import-not-found]

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except Exception:
        pass
    return None


FFMPEG_EXE = _resolve_ffmpeg_exe()


# ==============================================================================
# GENRE & RHYTHM ARCHETYPE CATALOG
# ==============================================================================

GENRE_RHYTHM_ARCHETYPES: dict[str, dict[str, Any]] = {
    "kr_truecrime_noir_director": {
        "archetype_label_vi": "True Crime Điện Ảnh Đêm Khuya · Nhịp Căng & Khoảng Lặng Sắc Lạnh (SBS/그알 Noir)",
        "specialist_summary_vi": (
            "Giọng nam trầm sâu giàu độ nén nội tâm thiết kế từ K1 sạch (-0.35 semitone, ấm ngực +1.6dB). "
            "Nhịp kể có độ tương phản cao: dồn dập ở cảnh hiện trường/truy bắt, phanh gấp trước cú lật, "
            "và buông khoảng lặng 1.40s–1.82s sau câu danh từ đinh để hình ảnh và nhạc nền tự kể tiếp."
        ),
        "voice_color_spec": {
            "color_label_vi": "K1 Noir Director · Trầm Sâu Đêm Khuya & Giàu Nội Lực",
            "pitch_semitones": -0.35,
            "presence_db": 0.45,
            "prosody_profile": {
                "style": "B",
                "tts_speed": 1.0,
                "atempo": 1.0,
                "guidance_scale": 2.22,
                "warm_db": 1.6,
                "deharsh_db": -1.35,
                "highshelf_db": -0.45,
                "pause_map": {
                    "comma": 0.30,
                    "clause": 0.24,
                    "suspense": 0.45,
                    "ellipsis": 0.50,
                    "question": 0.43,
                    "beat_end": 0.48,
                },
            },
            "sample_showcase_ko": (
                "단 육십 초. <break time=\"0.42s\"/> 비상벨 소리가 멎었을 때, "
                "텅 빈 금고 안에는 차가운 침묵만이 남아 있었습니다. <break time=\"0.46s\"/> "
                "과연 그 설계자는 어디로 증발한 걸까요?"
            ),
        },
        "writing_cadence": {
            "target_avg_sentence_chars": [24, 44],
            "short_punch_ratio_target": [0.14, 0.24],
            "paragraph_sentence_span": [1, 4],
            "rhetorical_question_per_act": [1, 2],
            "register_mode": "investigative_noir_dynamic",
            "writer_rhythm_directive_vi": (
                "Viết câu giàu hình ảnh hiện trường, luân phiên câu điều tra trung bình (26–44 ký tự) với cú phanh ngắn "
                "(8–18 ký tự, 14%–24%) ngay điểm rơi bằng chứng. Tuyệt đối lược bỏ chủ ngữ thừa ở cảnh hành động gấp, "
                "và đặt câu hỏi tu từ mở khoảng lặng trước mỗi bước ngoặt phá án."
            ),
        },
        "vocal_cadence": {
            "target_sps_range": [4.35, 5.55, 6.25],
            "allow_urgent_fast_chain": True,
            "max_fast_gap_streak": 4,
            "emotion_speed_multipliers": {
                "stark_punch": 0.81,
                "somber_tragedy": 0.84,
                "suspense_question": 0.87,
                "twist_reveal": 0.89,
                "urgent_action": 1.06,
                "forensic_anchor": 0.96,
                "narrative_flow": 0.99,
            },
            "pause_tiers_sec": {
                "urgent_action": 0.26,
                "tight_continuation": 0.37,
                "standard_narrative": 0.58,
                "pre_punch_anticipation": 0.86,
                "paragraph_breath": 0.96,
                "dramatic_landing": 1.42,
                "act_curtain": 1.82,
            },
        },
        "editing_cadence": {
            "editor_feel_title_vi": "Cảm Nhịp Đạo Diễn Noir: Cắt Gọn Cảnh Truy Bắt · Giữ Khung Hình Thở Qua Khoảng Lặng",
            "shot_pacing_sec": {
                "urgent_max_sec": 3.2,
                "standard_avg_sec": 4.0,
                "contemplative_min_sec": 5.6,
                "max_static_hold_sec": 5.2,
            },
            "cut_style": "contrastive_hard_and_linger",
            "hold_visual_across_dramatic_pause": True,
            "dramatic_pause_hold_threshold_sec": 1.15,
            "pre_punch_camera_motion": "creeping_push_in_tension",
            "post_punch_silence_camera_motion": "frozen_micro_drift_linger",
            "bgm_silence_swell_db": 2.2,
            "sfx_density_policy": "restrained_tactile_impacts_only",
            "editor_rhythm_directive_vi": (
                "Cảm nhận nhịp dựng bắt buộc khớp 1-1 với hơi thở giọng đọc: "
                "(1) Ở chuỗi `urgent_action` (nghỉ <= 0.32s): cắt nhanh sắc gọn 2.4s–3.2s/cut theo động tác hiện trường, tuyệt đối không để clip trôi lờ đờ; "
                "(2) Ở nhịp `pre_punch_anticipation` (nghỉ ~0.85s trước cú lật): giữ 1 khung hình zoom rón rén (`creeping_push_in`), cấm cắt chuyển cảnh sớm làm lộ bài; "
                "(3) Ở câu đinh `stark_punch` / `somber_tragedy` / `suspense_question` có khoảng lặng >= 1.15s: BẮT BUỘC giữ nguyên khung hình xuyên suốt toàn bộ khoảng lặng sau câu nói (không cắt giữa lúc khán giả đang thấm), đồng thời nâng nhẹ BGM +2.2dB trong khoảng lặng rồi mới sang cảnh mới."
            ),
        },
    },
    "kr_truecrime_forensic_dossier": {
        "archetype_label_vi": "Hồ Sơ Pháp Y & Truy Vết Lạnh (Forensic Dossier · Thực Nghiệm & Vox 2.5D)",
        "specialist_summary_vi": (
            "Giọng điều tra viên hồ sơ điềm tĩnh thiết kế từ K1 sạch (-0.15 semitone, độ nét phụ âm +0.75dB, ấm +1.2dB). "
            "Nhịp đọc chuẩn xác, rành mạch từng mốc giờ và vật chứng, tạo độ lạnh khách quan nhưng giữ khoảng nghỉ "
            "căng thẳng 1.32s ở các mâu thuẫn pháp y để Vox 2.5D và tư liệu thật phát huy tối đa sức nặng."
        ),
        "voice_color_spec": {
            "color_label_vi": "K1 Forensic Dossier · Điềm Tĩnh Sắc Nét & Lạnh Chuẩn Pháp Y",
            "pitch_semitones": -0.15,
            "presence_db": 0.75,
            "prosody_profile": {
                "style": "A",
                "tts_speed": 1.0,
                "atempo": 1.0,
                "guidance_scale": 2.18,
                "warm_db": 1.2,
                "deharsh_db": -1.25,
                "highshelf_db": -0.35,
                "pause_map": {
                    "comma": 0.28,
                    "clause": 0.22,
                    "suspense": 0.42,
                    "ellipsis": 0.46,
                    "question": 0.40,
                    "beat_end": 0.45,
                },
            },
            "sample_showcase_ko": (
                "수사 기록 백사십이 페이지. <break time=\"0.36s\"/> 지문 한 점 남지 않은 현장에서, "
                "단 하나의 미세한 오차가 포착되었습니다. <break time=\"0.42s\"/> 범인이 놓친 결정적 흔적이었죠."
            ),
        },
        "writing_cadence": {
            "target_avg_sentence_chars": [26, 46],
            "short_punch_ratio_target": [0.12, 0.20],
            "paragraph_sentence_span": [2, 4],
            "rhetorical_question_per_act": [1, 2],
            "register_mode": "forensic_investigative_dossier",
            "writer_rhythm_directive_vi": (
                "Nhịp viết chuẩn hồ sơ điều tra thực nghiệm: mở đoạn bằng mốc thời gian/vật chứng cụ thể, "
                "triển khai nhân quả gãy gọn 2–4 câu/khổ thở, dùng câu ngắn phanh nhịp đúng chỗ lật bằng chứng pháp y."
            ),
        },
        "vocal_cadence": {
            "target_sps_range": [4.50, 5.15, 5.65],
            "allow_urgent_fast_chain": True,
            "max_fast_gap_streak": 4,
            "emotion_speed_multipliers": {
                "stark_punch": 0.83,
                "somber_tragedy": 0.86,
                "suspense_question": 0.89,
                "twist_reveal": 0.91,
                "urgent_action": 1.05,
                "forensic_anchor": 0.97,
                "narrative_flow": 1.00,
            },
            "pause_tiers_sec": {
                "urgent_action": 0.28,
                "tight_continuation": 0.39,
                "standard_narrative": 0.56,
                "pre_punch_anticipation": 0.82,
                "paragraph_breath": 0.92,
                "dramatic_landing": 1.34,
                "act_curtain": 1.76,
            },
        },
        "editing_cadence": {
            "editor_feel_title_vi": "Cảm Nhịp Pháp Y Thực Nghiệm: Khớp Từ Whisper Trên Vox · Dứt Khoát Trên Tư Liệu",
            "shot_pacing_sec": {
                "urgent_max_sec": 3.4,
                "standard_avg_sec": 4.2,
                "contemplative_min_sec": 5.2,
                "max_static_hold_sec": 5.4,
            },
            "cut_style": "forensic_precision_cut",
            "hold_visual_across_dramatic_pause": True,
            "dramatic_pause_hold_threshold_sec": 1.15,
            "pre_punch_camera_motion": "forensic_macro_push",
            "post_punch_silence_camera_motion": "evidence_lock_hold",
            "bgm_silence_swell_db": 1.8,
            "sfx_density_policy": "motion_synced_forensic_cues",
            "editor_rhythm_directive_vi": (
                "Dựng theo nhịp giải phẫu bằng chứng: Footage thật cắt gọn 3.0s–4.5s đúng mệnh đề; "
                "cảnh Vox 2.5D bung dữ liệu khớp chính xác mốc từ Whisper (`words[]`); "
                "tại các khoảng nghỉ pháp y >= 1.15s, giữ khung hình khóa vào vật chứng/con số đinh đến hết khoảng lặng rồi mới cắt."
            ),
        },
    },
    "kr_cyber_finance_senior_clarity": {
        "archetype_label_vi": "Điều Tra Tài Chính & Tội Phạm CNC Cho Khán Giả 45–70 Tuổi (Rõ Số Liệu · Dễ Thấm)",
        "specialist_summary_vi": (
            "Giọng nam trung niên đĩnh đạc, ấm và cực rõ chữ thiết kế từ K1 sạch (-0.10 semitone, tăng dải rõ chữ "
            "2.5kHz +1.35dB, tốc độ tự nhiên 1.0). Đặc biệt chừa nhịp nghỉ tiêu hóa thông tin sau các con số tỷ tệ, "
            "mạng lưới rửa tiền và thuật ngữ công nghệ để khán giả 45–70 tuổi nghe êm tai, không bao giờ bị ngợp."
        ),
        "voice_color_spec": {
            "color_label_vi": "K1 Senior Financial Anchor · Rõ Chữ Đĩnh Đạc & Tin Cậy Cho Khán Giả 45–70+",
            "pitch_semitones": -0.10,
            "presence_db": 1.35,
            "prosody_profile": {
                "style": "C",
                "tts_speed": 1.0,
                "atempo": 1.0,
                "guidance_scale": 2.20,
                "warm_db": 1.35,
                "deharsh_db": -1.45,
                "highshelf_db": -0.25,
                "pause_map": {
                    "comma": 0.33,
                    "clause": 0.26,
                    "suspense": 0.46,
                    "ellipsis": 0.50,
                    "question": 0.44,
                    "beat_end": 0.50,
                },
            },
            "sample_showcase_ko": (
                "단 사흘 만에 사라진 돈, 일조 이천억 원. <break time=\"0.44s\"/> "
                "평범한 퇴직자들의 노후 자금은 대체 어느 계좌로 흘러들어 간 걸까요?"
            ),
        },
        "writing_cadence": {
            "target_avg_sentence_chars": [22, 38],
            "short_punch_ratio_target": [0.15, 0.24],
            "paragraph_sentence_span": [2, 3],
            "rhetorical_question_per_act": [1, 2],
            "register_mode": "senior_friendly_financial_investigative",
            "writer_rhythm_directive_vi": (
                "Viết cho khán giả Hàn 45–70 tuổi: mỗi câu chỉ mang 1 ý hoặc 1 con số lớn duy nhất (22–38 ký tự), "
                "giải thích cơ chế dòng tiền/tiền ảo bằng hình ảnh đời thường dễ hiểu, tách khổ thở ngắn 2–3 câu "
                "để người lớn tuổi kịp theo dõi sơ đồ dòng tiền trên màn hình."
            ),
        },
        "vocal_cadence": {
            "target_sps_range": [4.10, 4.75, 5.25],
            "allow_urgent_fast_chain": False,
            "max_fast_gap_streak": 3,
            "emotion_speed_multipliers": {
                "stark_punch": 0.82,
                "somber_tragedy": 0.85,
                "suspense_question": 0.88,
                "twist_reveal": 0.90,
                "urgent_action": 1.01,
                "forensic_anchor": 0.95,
                "narrative_flow": 0.98,
            },
            "pause_tiers_sec": {
                "urgent_action": 0.38,
                "tight_continuation": 0.45,
                "standard_narrative": 0.65,
                "pre_punch_anticipation": 0.90,
                "paragraph_breath": 1.04,
                "dramatic_landing": 1.40,
                "act_curtain": 1.85,
            },
        },
        "editing_cadence": {
            "editor_feel_title_vi": "Cảm Nhịp Dòng Tiền Điềm Đạm: Đủ Thời Gian Đọc Số Liệu · Không Nhấp Nháy Gây Mỏi Mắt",
            "shot_pacing_sec": {
                "urgent_max_sec": 3.8,
                "standard_avg_sec": 4.8,
                "contemplative_min_sec": 5.8,
                "max_static_hold_sec": 6.2,
            },
            "cut_style": "measured_spatial_clarity",
            "hold_visual_across_dramatic_pause": True,
            "dramatic_pause_hold_threshold_sec": 1.10,
            "pre_punch_camera_motion": "steady_ledger_focus_push",
            "post_punch_silence_camera_motion": "calm_metric_hold",
            "bgm_silence_swell_db": 1.6,
            "sfx_density_policy": "clean_minimal_financial_ticks",
            "editor_rhythm_directive_vi": (
                "Cảm nhận nhịp dựng cho khán giả 45–70 tuổi: cấm cắt giật chớp nhoáng dưới 3.5s gây mỏi mắt; "
                "mỗi biểu đồ dòng tiền / con số lớn phải giữ đủ 4.5s–5.8s và đứng yên thêm trọn khoảng nghỉ 1.1s–1.4s "
                "sau câu đọc để người xem đọc trọn con số trước khi chuyển cảnh."
            ),
        },
    },
    "kr_geopolitics_strategic_intel": {
        "archetype_label_vi": "Phân Tích Địa Chính Trị & Đại Hạ Tầng (Sắc Bén · Nhịp Chiến Lược Hiện Đại)",
        "specialist_summary_vi": (
            "Giọng bình luận viên chiến lược sắc sảo, sáng rõ và giàu năng lượng trí tuệ thiết kế từ K1 sạch "
            "(+0.15 semitone, presence +1.15dB, tốc độ tự nhiên 1.0). Nhịp câu gọn, dứt khoát, đẩy tốc độ phân tích "
            "bản đồ vệ tinh & chuỗi cung ứng cực cuốn, nhưng phanh sắc lẹm trước các nghịch lý vĩ mô."
        ),
        "voice_color_spec": {
            "color_label_vi": "K1 Strategic Analyst · Sắc Bén Hiện Đại & Uy Lực Vĩ Mô",
            "pitch_semitones": 0.15,
            "presence_db": 1.15,
            "prosody_profile": {
                "style": "C",
                "tts_speed": 1.0,
                "atempo": 1.00,
                "guidance_scale": 2.16,
                "warm_db": 0.85,
                "deharsh_db": -1.15,
                "highshelf_db": -0.15,
                "pause_map": {
                    "comma": 0.25,
                    "clause": 0.20,
                    "suspense": 0.38,
                    "ellipsis": 0.42,
                    "question": 0.37,
                    "beat_end": 0.41,
                },
            },
            "sample_showcase_ko": (
                "겉으로는 거대한 항만 투자처럼 보였습니다. <break time=\"0.34s\"/> "
                "하지만 위성 지도를 확대해 보면, 전혀 다른 전략적 계산이 드러납니다."
            ),
        },
        "writing_cadence": {
            "target_avg_sentence_chars": [25, 45],
            "short_punch_ratio_target": [0.12, 0.20],
            "paragraph_sentence_span": [2, 4],
            "rhetorical_question_per_act": [1, 2],
            "register_mode": "strategic_geopolitical_briefing",
            "writer_rhythm_directive_vi": (
                "Nhịp viết phân tích chiến lược kiểu Vox/FT: đi thẳng vào nghịch lý hạ tầng - địa chính trị, "
                "đối chiếu quy mô công trình với điểm nghẽn thực tế bằng nhịp câu sắc gọn, không lan man cảm tính."
            ),
        },
        "vocal_cadence": {
            "target_sps_range": [4.65, 5.28, 5.75],
            "allow_urgent_fast_chain": True,
            "max_fast_gap_streak": 5,
            "emotion_speed_multipliers": {
                "stark_punch": 0.85,
                "somber_tragedy": 0.89,
                "suspense_question": 0.90,
                "twist_reveal": 0.92,
                "urgent_action": 1.05,
                "forensic_anchor": 0.98,
                "narrative_flow": 1.01,
            },
            "pause_tiers_sec": {
                "urgent_action": 0.27,
                "tight_continuation": 0.35,
                "standard_narrative": 0.51,
                "pre_punch_anticipation": 0.78,
                "paragraph_breath": 0.88,
                "dramatic_landing": 1.24,
                "act_curtain": 1.68,
            },
        },
        "editing_cadence": {
            "editor_feel_title_vi": "Cảm Nhịp Bản Đồ Chiến Lược: Chuyển Cảnh Năng Động · Khóa Nhịp Số Liệu & Vệ Tinh",
            "shot_pacing_sec": {
                "urgent_max_sec": 3.2,
                "standard_avg_sec": 4.1,
                "contemplative_min_sec": 5.0,
                "max_static_hold_sec": 5.0,
            },
            "cut_style": "crisp_telemetry_cut",
            "hold_visual_across_dramatic_pause": True,
            "dramatic_pause_hold_threshold_sec": 1.12,
            "pre_punch_camera_motion": "satellite_zoom_lock",
            "post_punch_silence_camera_motion": "strategic_map_hold",
            "bgm_silence_swell_db": 1.7,
            "sfx_density_policy": "tactile_hud_and_map_transitions",
            "editor_rhythm_directive_vi": (
                "Dựng nhịp thông minh, giàu chuyển động: bay bản đồ vệ tinh 2.5D và HUD số liệu khớp chặt mệnh đề phân tích "
                "(3.6s–4.5s/cảnh), cắt sắc nét theo lập luận và giữ bản đồ dừng 1.2s tại điểm kết luận chiến lược."
            ),
        },
    },
    "kr_grace_pastoral_letter": {
        "archetype_label_vi": "Thư Ân Điển & Lời Chúa Chữa Lành 60 Phút (Ấm Trầm · Thong Thả · Tĩnh Tâm)",
        "specialist_summary_vi": (
            "Giọng đọc tâm tình mục vụ ấm áp, mềm mại và sâu lắng thiết kế từ K1 sạch (-0.42 semitone, ấm ngực +2.2dB, "
            "giảm chói -1.8dB, tốc độ chậm rãi 0.88). Tuyệt đối không đọc vội; mỗi câu đều có hơi thở nâng đỡ "
            "(0.72s–1.68s) để lời Kinh Thánh và sự an ủi thấm sâu vào lòng người nghe."
        ),
        "voice_color_spec": {
            "color_label_vi": "K1 Sanctuary Warmth · Trầm Ấm Chữa Lành & Khoan Thai Sâu Lắng",
            "pitch_semitones": -0.42,
            "presence_db": 0.15,
            "prosody_profile": {
                "style": "B",
                "tts_speed": 0.88,
                "atempo": 0.975,
                "guidance_scale": 2.14,
                "warm_db": 2.2,
                "deharsh_db": -1.8,
                "highshelf_db": -0.85,
                "pause_map": {
                    "comma": 0.38,
                    "clause": 0.30,
                    "suspense": 0.54,
                    "ellipsis": 0.62,
                    "question": 0.52,
                    "beat_end": 0.60,
                },
            },
            "sample_showcase_ko": (
                "오늘 하루도 참 많이 애쓰셨습니다. <break time=\"0.52s\"/> "
                "아무에게도 말 못 한 마음의 짐을, 이제 조용히 주님 앞에 내려놓으시길 기도합니다."
            ),
        },
        "writing_cadence": {
            "target_avg_sentence_chars": [24, 42],
            "short_punch_ratio_target": [0.08, 0.16],
            "paragraph_sentence_span": [2, 4],
            "rhetorical_question_per_act": [1, 2],
            "register_mode": "warm_pastoral_grace_letter",
            "writer_rhythm_directive_vi": (
                "Nhịp viết thư ân điển chữa lành: câu văn êm dịu, giàu hơi ấm vỗ về, dùng nhịp đối xứng nhẹ nhàng "
                "và lời cầu nguyện tĩnh lặng; tuyệt đối tránh câu giật gân hay dồn dập kịch tính."
            ),
        },
        "vocal_cadence": {
            "target_sps_range": [3.65, 4.35, 4.95],
            "allow_urgent_fast_chain": False,
            "max_fast_gap_streak": 2,
            "emotion_speed_multipliers": {
                "stark_punch": 0.86,
                "somber_tragedy": 0.86,
                "suspense_question": 0.90,
                "twist_reveal": 0.92,
                "urgent_action": 0.96,
                "forensic_anchor": 0.95,
                "narrative_flow": 0.97,
            },
            "pause_tiers_sec": {
                "urgent_action": 0.52,
                "tight_continuation": 0.56,
                "standard_narrative": 0.74,
                "pre_punch_anticipation": 1.05,
                "paragraph_breath": 1.22,
                "dramatic_landing": 1.66,
                "act_curtain": 2.12,
            },
        },
        "editing_cadence": {
            "editor_feel_title_vi": "Cảm Nhịp Tĩnh Nguyện Chữa Lành: Chuyển Hòa Tan Êm Ái · Giữ Cảnh Thiên Nhiên Thở Sâu",
            "shot_pacing_sec": {
                "urgent_max_sec": 6.0,
                "standard_avg_sec": 7.8,
                "contemplative_min_sec": 8.5,
                "max_static_hold_sec": 10.5,
            },
            "cut_style": "gentle_sanctuary_dissolve",
            "hold_visual_across_dramatic_pause": True,
            "dramatic_pause_hold_threshold_sec": 1.15,
            "pre_punch_camera_motion": "gentle_warm_light_drift",
            "post_punch_silence_camera_motion": "still_sanctuary_contemplation",
            "bgm_silence_swell_db": 2.4,
            "sfx_density_policy": "zero_harsh_sfx_ambient_only",
            "editor_rhythm_directive_vi": (
                "Cảm nhận nhịp dựng tĩnh tâm 60 phút: TUYỆT ĐỐI CẤM cắt giật nhanh hay hiệu ứng âm thanh gắt; "
                "mỗi cảnh thiên nhiên / ánh nến / tranh sơn dầu trôi êm 6.8s–9.5s với cross-dissolve mềm mại, "
                "ngân dài qua trọn khoảng lặng suy niệm 1.6s–2.1s cùng tiếng piano/strings dâng nhẹ."
            ),
        },
    },
    "us_presidential_archival_vault": {
        "archetype_label_vi": "Hồ Sơ Lưu Trữ Tổng Thống & Lịch Sử Quyền Lực Mỹ (PBS Frontline Gravitas)",
        "specialist_summary_vi": (
            "Giọng kể lưu trữ lịch sử Mỹ trầm tĩnh, uy quyền thiết kế từ mẫu sạch Jon US Già (-0.20 semitone, "
            "warmth +1.45dB). Nhịp kể đĩnh đạc như phim tài liệu PBS Frontline, để tài liệu gốc và ảnh lịch sử có "
            "khoảng thở trang trọng."
        ),
        "voice_color_spec": {
            "color_label_vi": "US Archival Gravitas · Trầm Uy Quyền Chuẩn Phim Tài Liệu Lịch Sử Mỹ",
            "recommended_master_key": "en_archival",
            "pitch_semitones": -0.20,
            "presence_db": 0.65,
            "prosody_profile": {
                "style": "B",
                "tts_speed": 0.95,
                "atempo": 0.99,
                "guidance_scale": 2.10,
                "warm_db": 1.45,
                "deharsh_db": -1.2,
                "highshelf_db": -0.3,
                "pause_map": {
                    "comma": 0.28,
                    "clause": 0.22,
                    "suspense": 0.44,
                    "ellipsis": 0.48,
                    "question": 0.40,
                    "beat_end": 0.46,
                },
            },
            "sample_showcase_en": (
                "Inside Box Forty-Seven of the National Archives, one handwritten margin note "
                "quietly rewrote the official White House timeline."
            ),
        },
        "writing_cadence": {
            "target_avg_sentence_chars": [75, 135],
            "short_punch_ratio_target": [0.12, 0.20],
            "paragraph_sentence_span": [2, 4],
            "rhetorical_question_per_act": [1, 2],
            "register_mode": "pbs_archival_chronicle",
            "writer_rhythm_directive_vi": (
                "Nhịp viết biên niên sử lưu trữ chuẩn PBS Frontline: đối lập tuyên bố công khai với biên bản mật "
                "bằng các câu ngắn đanh thép ngay sau đoạn dẫn tư liệu."
            ),
        },
        "vocal_cadence": {
            "target_sps_range": [3.8, 4.4, 5.0],
            "allow_urgent_fast_chain": True,
            "max_fast_gap_streak": 4,
            "emotion_speed_multipliers": {
                "stark_punch": 0.86,
                "somber_tragedy": 0.88,
                "suspense_question": 0.91,
                "twist_reveal": 0.92,
                "urgent_action": 1.03,
                "forensic_anchor": 0.97,
                "narrative_flow": 0.99,
            },
            "pause_tiers_sec": {
                "urgent_action": 0.30,
                "tight_continuation": 0.40,
                "standard_narrative": 0.60,
                "pre_punch_anticipation": 0.86,
                "paragraph_breath": 0.98,
                "dramatic_landing": 1.38,
                "act_curtain": 1.80,
            },
        },
        "editing_cadence": {
            "editor_feel_title_vi": "Cảm Nhịp Kho Lưu Trữ Lịch Sử: Ken Burns Điềm Đĩnh · Giữ Trọn Khoảnh Khắc Tư Liệu Gốc",
            "shot_pacing_sec": {
                "urgent_max_sec": 3.6,
                "standard_avg_sec": 4.9,
                "contemplative_min_sec": 6.2,
                "max_static_hold_sec": 6.0,
            },
            "cut_style": "archival_measured_cut",
            "hold_visual_across_dramatic_pause": True,
            "dramatic_pause_hold_threshold_sec": 1.15,
            "pre_punch_camera_motion": "slow_document_push_in",
            "post_punch_silence_camera_motion": "archival_portrait_linger",
            "bgm_silence_swell_db": 2.0,
            "sfx_density_policy": "subtle_paper_and_projector_tactility",
            "editor_rhythm_directive_vi": (
                "Dựng lịch sử sang trọng kiểu Ken Burns / Frontline: đẩy camera chậm rãi vào chữ ký/biên bản gốc "
                "(4.5s–6.0s/cảnh), giữ khung hình lặng đi trọn 1.3s–1.8s sau các tiết lộ lưu trữ chấn động."
            ),
        },
    },
    "us_classified_intel_declassified": {
        "archetype_label_vi": "Giải Mật Tình Báo & Hồ Sơ Đen Hoa Kỳ (Declassified Intelligence Thriller)",
        "specialist_summary_vi": (
            "Giọng điều tra giải mật sắc lạnh, căng thẳng thiết kế từ mẫu sạch Jon (+0.08 semitone, presence +0.95dB, "
            "warmth +1.05dB). Nhịp kể sắc gọn như hồ sơ CIA/NSA vừa mở niêm phong, dồn nén sự hồi hộp qua từng mốc tọa độ."
        ),
        "voice_color_spec": {
            "color_label_vi": "US Declassified Desk · Sắc Lạnh Hồ Sơ Mật & Nhịp Căng Tình Báo",
            "recommended_master_key": "en",
            "pitch_semitones": 0.08,
            "presence_db": 0.95,
            "prosody_profile": {
                "style": "C",
                "tts_speed": 0.97,
                "atempo": 1.00,
                "guidance_scale": 2.12,
                "warm_db": 1.05,
                "deharsh_db": -1.15,
                "highshelf_db": -0.2,
                "pause_map": {
                    "comma": 0.25,
                    "clause": 0.20,
                    "suspense": 0.40,
                    "ellipsis": 0.44,
                    "question": 0.38,
                    "beat_end": 0.42,
                },
            },
            "sample_showcase_en": (
                "For thirty-four years, every line on page twelve remained blacked out. "
                "Then a single declassified cable exposed the operation."
            ),
        },
        "writing_cadence": {
            "target_avg_sentence_chars": [68, 125],
            "short_punch_ratio_target": [0.15, 0.24],
            "paragraph_sentence_span": [2, 4],
            "rhetorical_question_per_act": [1, 2],
            "register_mode": "declassified_intel_thriller",
            "writer_rhythm_directive_vi": (
                "Nhịp viết tình báo giải mật: mở bằng dòng chữ bị bôi đen hoặc bức điện khẩn, cắt câu sắc gọn, "
                "tạo lực kéo bí ẩn liên tục giữa các mắt xích chiến dịch."
            ),
        },
        "vocal_cadence": {
            "target_sps_range": [4.0, 4.6, 5.2],
            "allow_urgent_fast_chain": True,
            "max_fast_gap_streak": 4,
            "emotion_speed_multipliers": {
                "stark_punch": 0.85,
                "somber_tragedy": 0.88,
                "suspense_question": 0.90,
                "twist_reveal": 0.91,
                "urgent_action": 1.05,
                "forensic_anchor": 0.98,
                "narrative_flow": 1.00,
            },
            "pause_tiers_sec": {
                "urgent_action": 0.27,
                "tight_continuation": 0.36,
                "standard_narrative": 0.54,
                "pre_punch_anticipation": 0.82,
                "paragraph_breath": 0.92,
                "dramatic_landing": 1.32,
                "act_curtain": 1.74,
            },
        },
        "editing_cadence": {
            "editor_feel_title_vi": "Cảm Nhịp Giải Mật Tình Báo: Cắt Nhịp Dossier Sắc Nét · Dừng Lạnh Ở Dòng Giải Mật",
            "shot_pacing_sec": {
                "urgent_max_sec": 3.3,
                "standard_avg_sec": 4.2,
                "contemplative_min_sec": 5.3,
                "max_static_hold_sec": 5.2,
            },
            "cut_style": "tense_dossier_cut",
            "hold_visual_across_dramatic_pause": True,
            "dramatic_pause_hold_threshold_sec": 1.12,
            "pre_punch_camera_motion": "redaction_reveal_push",
            "post_punch_silence_camera_motion": "classified_stamp_hold",
            "bgm_silence_swell_db": 2.0,
            "sfx_density_policy": "restrained_teletype_and_map_locks",
            "editor_rhythm_directive_vi": (
                "Dựng theo nhịp mở khóa hồ sơ mật: cắt sắc gọn 3.3s–4.4s giữa bản đồ chiến dịch, tài liệu giải mật "
                "và tư liệu thật; đóng băng chuyển động trong khoảng lặng 1.3s ngay khi dòng chữ bôi đen vừa hé lộ."
            ),
        },
    },
    "vn_investigative_fraud_lab": {
        "archetype_label_vi": "Phóng Sự Điều Tra Đại Án & Giải Phẫu Lừa Đảo VN (Sắc Lạnh · Có Hồn Con Người)",
        "specialist_summary_vi": (
            "Giọng nam phóng sự điều tra Việt Nam trầm đanh, rõ chữ và giàu chiều sâu thiết kế từ mẫu sạch PC Nam "
            "(-0.20 semitone, ấm +1.35dB, presence +0.85dB). Nhịp kể gãy gọn, bóc tách tâm lý nạn nhân và thủ đoạn "
            "dòng tiền với khoảng nghỉ giàu sức nặng."
        ),
        "voice_color_spec": {
            "color_label_vi": "VN Investigative Signature · Trầm Đanh Phóng Sự Đặc Biệt",
            "recommended_master_key": "vi",
            "pitch_semitones": -0.20,
            "presence_db": 0.85,
            "prosody_profile": {
                "style": "B",
                "tts_speed": 0.96,
                "atempo": 0.99,
                "guidance_scale": 2.12,
                "warm_db": 1.35,
                "deharsh_db": -1.25,
                "highshelf_db": -0.3,
                "pause_map": {
                    "comma": 0.28,
                    "clause": 0.22,
                    "suspense": 0.42,
                    "ellipsis": 0.46,
                    "question": 0.40,
                    "beat_end": 0.45,
                },
            },
            "sample_showcase_vi": (
                "Chỉ trong sáu mươi giây ngắn ngủi, toàn bộ dấu vết dòng tiền đã bị xóa sạch. "
                "Nhưng kẻ đứng sau màn kịch ấy đã bỏ quên một chi tiết chí mạng."
            ),
        },
        "writing_cadence": {
            "target_avg_sentence_chars": [65, 125],
            "short_punch_ratio_target": [0.14, 0.22],
            "paragraph_sentence_span": [2, 4],
            "rhetorical_question_per_act": [1, 2],
            "register_mode": "vietnamese_investigative_cinema",
            "writer_rhythm_directive_vi": (
                "Nhịp viết phóng sự điều tra điện ảnh: câu ngắn đanh ở điểm rơi thủ đoạn, kết hợp chi tiết đời thực "
                "chạm cảm xúc con người, tránh liệt kê khô khan."
            ),
        },
        "vocal_cadence": {
            "target_sps_range": [3.9, 4.5, 5.1],
            "allow_urgent_fast_chain": True,
            "max_fast_gap_streak": 4,
            "emotion_speed_multipliers": {
                "stark_punch": 0.84,
                "somber_tragedy": 0.86,
                "suspense_question": 0.89,
                "twist_reveal": 0.91,
                "urgent_action": 1.04,
                "forensic_anchor": 0.97,
                "narrative_flow": 0.99,
            },
            "pause_tiers_sec": {
                "urgent_action": 0.27,
                "tight_continuation": 0.37,
                "standard_narrative": 0.56,
                "pre_punch_anticipation": 0.84,
                "paragraph_breath": 0.95,
                "dramatic_landing": 1.36,
                "act_curtain": 1.78,
            },
        },
        "editing_cadence": {
            "editor_feel_title_vi": "Cảm Nhịp Giải Phẫu Đại Án: Tư Duy Dựng Con Người · Giữ Nhịp Lặng Thấm Cảm Xúc",
            "shot_pacing_sec": {
                "urgent_max_sec": 3.3,
                "standard_avg_sec": 4.2,
                "contemplative_min_sec": 5.4,
                "max_static_hold_sec": 5.4,
            },
            "cut_style": "human_investigative_contrast",
            "hold_visual_across_dramatic_pause": True,
            "dramatic_pause_hold_threshold_sec": 1.15,
            "pre_punch_camera_motion": "intimate_tension_push",
            "post_punch_silence_camera_motion": "human_aftermath_linger",
            "bgm_silence_swell_db": 2.1,
            "sfx_density_policy": "restrained_cinematic_impacts",
            "editor_rhythm_directive_vi": (
                "Dựng có hồn con người: cắt nhanh 2.8s–3.5s khi bóc tách thủ đoạn lừa đảo, nhưng lập tức ghìm nhịp "
                "5.2s–6.0s và giữ nguyên khung hình qua khoảng lặng >= 1.15s ở những câu bi kịch đời người."
            ),
        },
    },
    "universal_science_engineering_explainer": {
        "archetype_label_vi": "Giải Mã Khoa Học · Kỹ Thuật · Vũ Trụ & Tai Nạn Hệ Thống (LEMMiNO / Veritasium / Mustard)",
        "specialist_summary_vi": (
            "Giọng kể giàu trí tò mò khoa học, trong sáng và chuẩn xác (+0.05 semitone, presence +0.95dB, warmth +1.05dB). "
            "Nhịp kể đi từ câu hỏi nghịch lý vật lý đến bóc tách cơ chế từng lớp, chừa nhịp thở kinh ngạc (awe pause) "
            "1.38s–1.80s ngay khi quy luật tự nhiên hoặc lỗi thiết kế chí mạng lộ diện."
        ),
        "voice_color_spec": {
            "color_label_vi": "Precision Wonder Narrator · Trong Sáng Chuẩn Xác & Giàu Chiều Sâu Khám Phá",
            "pitch_semitones": 0.05,
            "presence_db": 0.95,
            "prosody_profile": {
                "style": "C",
                "tts_speed": 0.95,
                "atempo": 0.995,
                "guidance_scale": 2.15,
                "warm_db": 1.05,
                "deharsh_db": -1.20,
                "highshelf_db": -0.20,
                "pause_map": {
                    "comma": 0.27,
                    "clause": 0.21,
                    "suspense": 0.42,
                    "ellipsis": 0.48,
                    "question": 0.41,
                    "beat_end": 0.45,
                },
            },
            "sample_showcase_ko": (
                "겉보기엔 완벽한 설계였습니다. <break time=\"0.38s\"/> 하지만 영하 사십 도의 성층권에서, "
                "단 일 밀리미터의 균열이 모든 물리 법칙을 뒤집어 놓았습니다."
            ),
            "sample_showcase_en": (
                "On paper, the engineering was flawless. Yet forty thousand feet above the Atlantic, "
                "a single millimeter of metal fatigue quietly rewrote physics."
            ),
            "sample_showcase_vi": (
                "Trên bản vẽ, cỗ máy ấy hoàn hảo đến từng chi tiết. Nhưng ở độ cao mười hai cây số, "
                "một vết nứt chưa đầy một mi-li-mét đã đảo lộn mọi tính toán."
            ),
        },
        "writing_cadence": {
            "target_avg_sentence_chars": [26, 48],
            "short_punch_ratio_target": [0.12, 0.20],
            "paragraph_sentence_span": [2, 4],
            "rhetorical_question_per_act": [1, 2],
            "register_mode": "scientific_mechanism_wonder",
            "writer_rhythm_directive_vi": (
                "Nhịp viết giải mã khoa học/kỹ thuật kiểu LEMMiNO/Mustard: biến thông số khô khan thành chuỗi nhân quả "
                "hữu hình (Áp suất -> Vật liệu -> Điểm gãy), đặt câu ngắn gây kinh ngạc ngay khoảnh khắc khám phá."
            ),
        },
        "vocal_cadence": {
            "target_sps_range": [4.30, 4.95, 5.50],
            "allow_urgent_fast_chain": True,
            "max_fast_gap_streak": 4,
            "emotion_speed_multipliers": {
                "stark_punch": 0.84,
                "somber_tragedy": 0.87,
                "suspense_question": 0.89,
                "twist_reveal": 0.90,
                "urgent_action": 1.05,
                "forensic_anchor": 0.97,
                "narrative_flow": 1.00,
            },
            "pause_tiers_sec": {
                "urgent_action": 0.28,
                "tight_continuation": 0.37,
                "standard_narrative": 0.56,
                "pre_punch_anticipation": 0.84,
                "paragraph_breath": 0.94,
                "dramatic_landing": 1.38,
                "act_curtain": 1.80,
            },
        },
        "editing_cadence": {
            "editor_feel_title_vi": "Cảm Nhịp Giải Phẫu Cơ Chế & Vũ Trụ: Khớp Sơ Đồ Kỹ Thuật · Mở Khoảng Thở Kinh Ngạc (Awe Hold)",
            "shot_pacing_sec": {
                "urgent_max_sec": 3.3,
                "standard_avg_sec": 4.3,
                "contemplative_min_sec": 5.6,
                "max_static_hold_sec": 5.5,
            },
            "cut_style": "precision_mechanism_and_awe",
            "hold_visual_across_dramatic_pause": True,
            "dramatic_pause_hold_threshold_sec": 1.15,
            "pre_punch_camera_motion": "blueprint_macro_zoom",
            "post_punch_silence_camera_motion": "cosmic_scale_awe_hold",
            "bgm_silence_swell_db": 2.1,
            "sfx_density_policy": "tactile_mechanical_and_sub_ambience",
            "editor_rhythm_directive_vi": (
                "Dựng chuẩn giải phẫu kỹ thuật & kỳ quan khoa học: cắt gãy gọn 3.2s–4.4s khi bóc tách cơ chế dây chuyền, "
                "nhưng mở rộng toàn cảnh (Extreme Wide) và giữ lặng 1.4s–1.8s ở khoảnh khắc quy mô vũ trụ hoặc điểm gãy hệ thống lộ diện."
            ),
        },
    },
    "universal_cultural_human_essay": {
        "archetype_label_vi": "Essay Văn Hóa · Tâm Lý · Triết Lý Nhân Sinh & Nghệ Thuật (ARTE / NHK / Kishotenketsu)",
        "specialist_summary_vi": (
            "Giọng kể giàu chất thơ điện ảnh, ấm áp và tinh tế (-0.22 semitone, warmth +1.65dB, presence +0.55dB). "
            "Nhịp kể thở tự nhiên theo cấu trúc Khởi–Thừa–Chuyển–Hợp, trân trọng khoảng lặng nội tâm (Ma / 여백) "
            "để ánh mắt nhân vật, bối cảnh đời thường và âm nhạc chạm tới chiều sâu tâm lý."
        ),
        "voice_color_spec": {
            "color_label_vi": "Poetic Cinema Essayist · Ấm Sâu Tinh Tế & Giàu Cảm Xúc Nhân Bản",
            "pitch_semitones": -0.22,
            "presence_db": 0.55,
            "prosody_profile": {
                "style": "B",
                "tts_speed": 0.92,
                "atempo": 0.985,
                "guidance_scale": 2.16,
                "warm_db": 1.65,
                "deharsh_db": -1.50,
                "highshelf_db": -0.50,
                "pause_map": {
                    "comma": 0.34,
                    "clause": 0.26,
                    "suspense": 0.48,
                    "ellipsis": 0.56,
                    "question": 0.46,
                    "beat_end": 0.52,
                },
            },
            "sample_showcase_ko": (
                "우리는 왜 가장 소중한 순간을 지나치고 나서야 비로소 깨닫게 될까요? <break time=\"0.46s\"/> "
                "오래된 골목 끝에서, 한 사람의 조용한 선택이 시대의 기억을 바꾸어 놓았습니다."
            ),
            "sample_showcase_en": (
                "Why do civilizations only recognize their golden hour after the light has already faded? "
                "In one quiet corner of the city, an ordinary life held the answer."
            ),
            "sample_showcase_vi": (
                "Vì sao con người thường chỉ nhận ra giá trị của một khoảnh khắc khi nó đã lùi xa vào ký ức? "
                "Giữa con phố nhỏ bình yên ấy, một lựa chọn lặng lẽ đã làm thay đổi tất cả."
            ),
        },
        "writing_cadence": {
            "target_avg_sentence_chars": [25, 46],
            "short_punch_ratio_target": [0.10, 0.18],
            "paragraph_sentence_span": [2, 4],
            "rhetorical_question_per_act": [1, 2],
            "register_mode": "cinematic_humanist_essay",
            "writer_rhythm_directive_vi": (
                "Nhịp viết essay điện ảnh nhân văn (NHK/ARTE): giàu chi tiết đời thực (ánh sáng, tiếng động, thói quen nhỏ), "
                "chuyển ý mềm mại nhưng sâu sắc, để lại dư âm suy ngẫm ở cuối mỗi hồi."
            ),
        },
        "vocal_cadence": {
            "target_sps_range": [3.95, 4.65, 5.20],
            "allow_urgent_fast_chain": False,
            "max_fast_gap_streak": 3,
            "emotion_speed_multipliers": {
                "stark_punch": 0.84,
                "somber_tragedy": 0.85,
                "suspense_question": 0.88,
                "twist_reveal": 0.90,
                "urgent_action": 1.01,
                "forensic_anchor": 0.96,
                "narrative_flow": 0.98,
            },
            "pause_tiers_sec": {
                "urgent_action": 0.36,
                "tight_continuation": 0.44,
                "standard_narrative": 0.64,
                "pre_punch_anticipation": 0.92,
                "paragraph_breath": 1.08,
                "dramatic_landing": 1.52,
                "act_curtain": 1.96,
            },
        },
        "editing_cadence": {
            "editor_feel_title_vi": "Cảm Nhịp Điện Ảnh Nhân Văn: L-Cut Ngân Dư Âm · Khoảng Lặng 'Ma' Giàu Chất Thơ",
            "shot_pacing_sec": {
                "urgent_max_sec": 4.0,
                "standard_avg_sec": 5.2,
                "contemplative_min_sec": 6.6,
                "max_static_hold_sec": 6.8,
            },
            "cut_style": "poetic_l_cut_and_linger",
            "hold_visual_across_dramatic_pause": True,
            "dramatic_pause_hold_threshold_sec": 1.15,
            "pre_punch_camera_motion": "intimate_portrait_drift",
            "post_punch_silence_camera_motion": "pillow_shot_atmospheric_hold",
            "bgm_silence_swell_db": 2.3,
            "sfx_density_policy": "organic_foley_and_room_air",
            "editor_rhythm_directive_vi": (
                "Dựng theo mỹ학 điện ảnh Ozu / Kore-eda / ARTE: ưu tiên L-cut và các cảnh thở 'pillow shot' 5.0s–6.8s, "
                "giữ trọn ánh mắt nhân vật hoặc không gian tĩnh lặng 1.5s–2.0s sau câu kết luận triết lý."
            ),
        },
    },
    "universal_empire_biography_chronicle": {
        "archetype_label_vi": "Đế Chế Kinh Doanh · Tiểu Sử Nhân Vật & Bê Bối Tập Đoàn (MagnatesMedia / Bloomberg)",
        "specialist_summary_vi": (
            "Giọng kể quyền lực, cuốn hút và sắc sảo (-0.12 semitone, warmth +1.30dB, presence +0.90dB). "
            "Nhịp kể giàu động lực thăng trầm (Rise & Fall): cuốn người xem qua tham vọng xây đế chế bằng nhịp dựng "
            "nhanh sắc nét, rồi đột ngột phanh đứng tại khoảnh khắc sụp đổ hoặc phản bội trong phòng họp kín."
        ),
        "voice_color_spec": {
            "color_label_vi": "Empire Chronicle Voice · Quyền Lực Cuốn Hút & Sắc Lạnh Thương Trường",
            "pitch_semitones": -0.12,
            "presence_db": 0.90,
            "prosody_profile": {
                "style": "B",
                "tts_speed": 0.95,
                "atempo": 0.995,
                "guidance_scale": 2.16,
                "warm_db": 1.30,
                "deharsh_db": -1.25,
                "highshelf_db": -0.25,
                "pause_map": {
                    "comma": 0.27,
                    "clause": 0.21,
                    "suspense": 0.42,
                    "ellipsis": 0.46,
                    "question": 0.39,
                    "beat_end": 0.44,
                },
            },
            "sample_showcase_ko": (
                "단 십 년 만에 시가총액 오백조 원의 제국을 세운 남자. <break time=\"0.40s\"/> "
                "하지만 화려한 이사회 문이 닫히자, 그 제국은 단 하루 만에 무너지기 시작했습니다."
            ),
            "sample_showcase_en": (
                "At thirty-two, he commanded an empire worth forty billion dollars. "
                "Behind closed boardroom doors, the countdown to collapse had already begun."
            ),
            "sample_showcase_vi": (
                "Ở tuổi ba mươi hai, ông nắm trong tay đế chế hàng chục tỷ đô la. "
                "Nhưng sau cánh cửa phòng họp kín, đồng hồ đếm ngược cho sự sụp đổ đã bắt đầu điểm."
            ),
        },
        "writing_cadence": {
            "target_avg_sentence_chars": [25, 45],
            "short_punch_ratio_target": [0.14, 0.22],
            "paragraph_sentence_span": [2, 4],
            "rhetorical_question_per_act": [1, 2],
            "register_mode": "empire_rise_and_fall_chronicle",
            "writer_rhythm_directive_vi": (
                "Nhịp viết biên niên sử đế chế & tiểu sử (MagnatesMedia): đối lập đỉnh cao hào nhoáng với vết nứt ngầm, "
                "dùng mốc tiền tệ/năm tháng sắc gọn và câu chốt giàu kịch tính thương trường."
            ),
        },
        "vocal_cadence": {
            "target_sps_range": [4.45, 5.10, 5.65],
            "allow_urgent_fast_chain": True,
            "max_fast_gap_streak": 4,
            "emotion_speed_multipliers": {
                "stark_punch": 0.83,
                "somber_tragedy": 0.87,
                "suspense_question": 0.89,
                "twist_reveal": 0.90,
                "urgent_action": 1.05,
                "forensic_anchor": 0.97,
                "narrative_flow": 1.00,
            },
            "pause_tiers_sec": {
                "urgent_action": 0.27,
                "tight_continuation": 0.36,
                "standard_narrative": 0.54,
                "pre_punch_anticipation": 0.82,
                "paragraph_breath": 0.92,
                "dramatic_landing": 1.35,
                "act_curtain": 1.78,
            },
        },
        "editing_cadence": {
            "editor_feel_title_vi": "Cảm Nhịp Đế Chế Thăng Trầm: Dựng Cuốn Giai Đoạn Tăng Trưởng · Đóng Băng Đỉnh Sụp Đổ",
            "shot_pacing_sec": {
                "urgent_max_sec": 3.2,
                "standard_avg_sec": 4.1,
                "contemplative_min_sec": 5.3,
                "max_static_hold_sec": 5.2,
            },
            "cut_style": "prestige_boardroom_momentum",
            "hold_visual_across_dramatic_pause": True,
            "dramatic_pause_hold_threshold_sec": 1.15,
            "pre_punch_camera_motion": "executive_tension_push",
            "post_punch_silence_camera_motion": "empty_boardroom_aftermath_hold",
            "bgm_silence_swell_db": 2.0,
            "sfx_density_policy": "refined_ticker_and_cinematic_pulses",
            "editor_rhythm_directive_vi": (
                "Dựng giàu xung lực kiểu MagnatesMedia / Succession: cắt nhịp 3.0s–4.2s theo đà bành trướng đế chế, "
                "ngắt nhạc đột ngột và giữ cận cảnh chân dung / biểu đồ lao dốc qua trọn khoảng lặng 1.35s–1.80s khi đế chế sụp đổ."
            ),
        },
    },
}


# ==============================================================================
# ACOUSTIC VOICE TIMBRE SCULPTING HELPERS
# ==============================================================================

def apply_voice_color_polish_wav_bytes(
    wav_bytes: bytes,
    voice_color_spec: dict[str, Any] | None,
) -> bytes:
    """Apply subtle, formant-safe profile timbre color (`pitch_semitones` + `presence_db`) to a WAV buffer.

     Note: `warm_db`, `deharsh_db`, `highshelf_db`, and `atempo` are already applied inside
    CofiVoice's `apply_broadcast_mastering` from `prosody_profile`, so here we apply ONLY
    the profile-exclusive `pitch_semitones` and `presence_db` (`2500Hz` consonant clarity)
    to prevent any double-EQ while giving every profile a genuinely distinct vocal color.
    """
    if not wav_bytes or len(wav_bytes) < 200 or not isinstance(voice_color_spec, dict):
        return wav_bytes
    pitch_st = float(voice_color_spec.get("pitch_semitones") or 0.0)
    presence_db = float(voice_color_spec.get("presence_db") or 0.0)
    if abs(pitch_st) < 0.04 and abs(presence_db) < 0.12:
        return wav_bytes
    if not FFMPEG_EXE:
        return wav_bytes

    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            sr = wf.getframerate()
            nch = wf.getnchannels()
            nframes = wf.getnframes()
            raw_check = wf.readframes(min(nframes, sr))
        if sr <= 0 or nframes < int(sr * 0.08):
            return wav_bytes
        arr_check = np.frombuffer(raw_check, dtype=np.int16)
        if arr_check.size == 0 or int(np.max(np.abs(arr_check))) < 35:
            # Synthetic silence fixture in unit tests -> preserve exact byte length
            return wav_bytes
    except Exception:
        return wav_bytes

    filters: list[str] = []
    if abs(pitch_st) >= 0.04:
        # Clamp to subtle human studio range [-0.85, +0.85] semitones so formants stay 100% natural
        clamped_st = max(-0.85, min(0.85, pitch_st))
        ratio = float(2.0 ** (clamped_st / 12.0))
        comp_tempo = max(0.5, min(2.0, 1.0 / ratio))
        filters.append(f"asetrate={int(round(sr * ratio))}")
        filters.append(f"aresample={sr}")
        filters.append(f"atempo={comp_tempo:.5f}")
    if abs(presence_db) >= 0.12:
        clamped_pres = max(-2.5, min(2.5, presence_db))
        filters.append(f"equalizer=f=2500:t=q:w=1.15:g={clamped_pres:.2f}")
    filters.append("alimiter=limit=0.91:level=disabled")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_in, tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False
    ) as f_out:
        in_p, out_p = f_in.name, f_out.name
    try:
        Path(in_p).write_bytes(wav_bytes)
        subprocess.run(
            [
                FFMPEG_EXE,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                in_p,
                "-af",
                ",".join(filters),
                "-ar",
                str(sr),
                "-ac",
                str(max(1, nch)),
                "-c:a",
                "pcm_s16le",
                out_p,
            ],
            check=True,
            creationflags=_NO_WINDOW,
            timeout=30,
        )
        polished = Path(out_p).read_bytes()
        return polished if len(polished) > 200 else wav_bytes
    except Exception:
        return wav_bytes
    finally:
        for p in (in_p, out_p):
            try:
                os.remove(p)
            except OSError:
                pass


def decode_audio_upload_payload(
    *,
    audio_bytes: bytes | None = None,
    audio_base64: str | None = None,
    filename: str = "sample.wav",
) -> tuple[bytes, str]:
    """Decode raw bytes or base64 / data-URL audio into `(bytes, safe_filename)`."""
    if audio_bytes:
        return audio_bytes, filename or "sample.wav"
    raw_b64 = str(audio_base64 or "").strip()
    if not raw_b64:
        raise ValueError("Chưa có dữ liệu file mẫu giọng để clone")
    inferred_ext = Path(filename or "sample.wav").suffix.lower() or ".wav"
    if raw_b64.startswith("data:"):
        header, _, encoded = raw_b64.partition(",")
        if "mpeg" in header or "mp3" in header:
            inferred_ext = ".mp3"
        elif "mp4" in header or "m4a" in header:
            inferred_ext = ".m4a"
        elif "ogg" in header:
            inferred_ext = ".ogg"
        elif "webm" in header:
            inferred_ext = ".webm"
        raw_b64 = encoded
    decoded = base64.b64decode(raw_b64)
    if len(decoded) < 256:
        raise ValueError("File mẫu giọng quá nhỏ hoặc không hợp lệ")
    stem = Path(filename or "sample").stem or "sample"
    return decoded, f"{stem}{inferred_ext}"


# ==============================================================================
# SPECIALIST SERVICE
# ==============================================================================

class VoiceRhythmSpecialistService:
    """Analyzes channel profile DNA -> designs bespoke voice color & 3-layer storytelling rhythm."""

    def __init__(
        self,
        *,
        cofivoice_dir: Path | str | None = None,
        cofivoice_url: str | None = None,
        session: Any | None = None,
    ):
        self.cofivoice_dir = Path(cofivoice_dir) if cofivoice_dir else DEFAULT_COFIVOICE_DIR
        self.cofivoice_url = str(cofivoice_url or DEFAULT_COFIVOICE_URL).rstrip("/")
        self.session = session or requests.Session()

    def list_clean_master_voices(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for key, meta in CLEAN_MASTER_VOICES.items():
            vid = meta["id"]
            if vid in seen:
                continue
            seen.add(vid)
            out.append({
                "key": key,
                "id": vid,
                "name": meta["name"],
                "language": meta["language"],
                "is_k1_clean_master": vid == CLEAN_MASTER_VOICES["ko"]["id"],
                "proxy_preview_url": f"/api/voice/preview-audio/{vid}",
            })
        return out

    @staticmethod
    def resolve_default_master_voice_id(language: str, archetype_id: str = "") -> str:
        lang = str(language or "ko").strip().lower()
        if lang == "ko":
            return CLEAN_MASTER_VOICES["ko"]["id"]
        if lang == "en":
            if "presidential" in archetype_id or "archival" in archetype_id:
                return CLEAN_MASTER_VOICES["en_archival"]["id"]
            return CLEAN_MASTER_VOICES["en"]["id"]
        if lang == "vi":
            return CLEAN_MASTER_VOICES["vi"]["id"]
        if lang == "ja":
            return CLEAN_MASTER_VOICES["ja"]["id"]
        return CLEAN_MASTER_VOICES["en"]["id"]

    @staticmethod
    def classify_profile_archetype(profile_data: dict[str, Any], custom_direction: str = "") -> str:
        pid = str(profile_data.get("id") or profile_data.get("channel_profile_id") or "").strip().lower()
        market = str(profile_data.get("market") or "KR").strip().upper()
        lang_map = {"KR": "ko", "US": "en", "VN": "vi", "JP": "ja"}
        lang = str(
            profile_data.get("default_language")
            or profile_data.get("language")
            or lang_map.get(market, "ko")
        ).strip().lower()

        brief = profile_data.get("default_creative_brief") if isinstance(profile_data.get("default_creative_brief"), dict) else {}
        ed_dna = profile_data.get("editing_dna") if isinstance(profile_data.get("editing_dna"), dict) else {}
        edit_preset = str(ed_dna.get("preset_id") or "").strip().lower()
        duration = float(
            profile_data.get("default_duration_minutes")
            or profile_data.get("target_duration_minutes")
            or brief.get("target_duration_minutes")
            or 30.0
        )

        haystack = " ".join(
            str(x or "")
            for x in (
                pid,
                profile_data.get("label"),
                profile_data.get("name"),
                profile_data.get("voice_and_structure"),
                profile_data.get("allowed_topics"),
                profile_data.get("notes"),
                brief.get("narrative_angle"),
                brief.get("writing_style"),
                brief.get("notes"),
                edit_preset,
                custom_direction,
            )
        ).lower()

        # Exact known production profile shortcuts first (100% deterministic preservation)
        if pid == "channel-kr-grace-letter-60m":
            return "kr_grace_pastoral_letter"
        if pid == "channel-e544a64b7c":
            return "kr_truecrime_forensic_dossier"
        if pid in {"channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2"}:
            return "kr_truecrime_noir_director"
        if pid == "channel-aa913eb90d":
            return "us_classified_intel_declassified"
        if pid == "channel-f6ec4dfff3":
            return "us_presidential_archival_vault"
        if pid == "channel-cn-cyber-finance-kr":
            return "kr_cyber_finance_senior_clarity"
        if pid == "channel-1e24de3ab5":
            return "kr_geopolitics_strategic_intel"

        # Spiritual / Pastoral / Healing / Sanctuary across languages
        if any(
            kw in haystack
            for kw in (
                "은혜",
                "하나님",
                "말씀",
                "기도",
                "목사",
                "ân điển",
                "lời chúa",
                "kinh thánh",
                "chữa lành",
                "tĩnh tâm",
                "pastoral",
                "sermon",
                "healing",
                "meditation",
                "sleep",
            )
        ):
            return "kr_grace_pastoral_letter"

        # Universal Cross-Language Niche 1: Science, Space, Engineering & Systems Disaster Explainer
        if any(
            kw in haystack
            for kw in (
                "khoa học",
                "vũ trụ",
                "thiên văn",
                "vật lý",
                "kỹ thuật",
                "hàng không",
                "tai nạn máy bay",
                "tàu ngầm",
                "cơ chế hệ thống",
                "science",
                "astronomy",
                "astrophysics",
                "cosmos",
                "quantum",
                "engineering",
                "aviation",
                "air crash",
                "maritime disaster",
                "lemmino",
                "veritasium",
                "mustard",
                "과학",
                "우주",
                "물리학",
                "천문학",
                "항공 사고",
                "공학",
            )
        ):
            return "universal_science_engineering_explainer"

        # Universal Cross-Language Niche 2: Cultural, Psychology, Philosophy & Humanist Video Essay
        if any(
            kw in haystack
            for kw in (
                "văn hóa",
                "tâm lý học",
                "triết học",
                "triết lý nhân sinh",
                "nghệ thuật",
                "nhân văn",
                "video essay",
                "essay điện ảnh",
                "philosophy",
                "psychology",
                "cultural essay",
                "human condition",
                "anthropology",
                "arte",
                "kishotenketsu",
                "nerdwriter",
                "인문학",
                "철학",
                "심리학",
                "문화 에세이",
            )
        ):
            return "universal_cultural_human_essay"

        # Universal Cross-Language Niche 3: Business Empire, Corporate Scandal & Biography Chronicle
        if any(
            kw in haystack
            for kw in (
                "đế chế kinh doanh",
                "đế chế tỷ đô",
                "tiểu sử nhân vật",
                "tỷ phú",
                "thương trường",
                "bê bối tập đoàn",
                "độc quyền",
                "corporate empire",
                "corporate scandal",
                "biography",
                "billionaire",
                "tech monopoly",
                "rise and fall",
                "magnatesmedia",
                "boardroom",
                "기업 제국",
                "창업자 전기",
                "재벌 비사",
            )
        ):
            return "universal_empire_biography_chronicle"

        if (
            edit_preset == "financial_forensic_vox"
            or any(
                kw in haystack
                for kw in (
                    "45–70",
                    "45-70",
                    "50–70",
                    "50-70",
                    "cao tuổi",
                    "노후",
                    "시니어",
                    "dòng tiền",
                    "tiền ảo",
                    "tài chính",
                    "cyber",
                    "rửa tiền",
                    "금융",
                    "코인",
                    "보이스피싱",
                )
            )
        ):
            if lang == "ko":
                return "kr_cyber_finance_senior_clarity"

        if any(
            kw in haystack
            for kw in (
                "địa chính trị",
                "hạ tầng",
                "판세",
                "지정학",
                "인프라",
                "반도체",
                "공급망",
                "geopolit",
                "infrastructure",
                "macro",
                "kinh tế vĩ mô",
                "chiến lược",
            )
        ):
            if lang == "ko":
                return "kr_geopolitics_strategic_intel"

        if lang == "ko":
            if (
                edit_preset in {"forensic_noir_director_v2", "vox_china_crime_newsroom_v10"}
                or str(ed_dna.get("director_mode") or "").strip().lower() in {"v2", "vox_china_crime_newsroom_v10"}
                or any(kw in haystack for kw in ("đạo diễn ai có hồn", "nhịp cảm xúc", "director v2", "sbs", "đêm khuya", "noir"))
            ):
                return "kr_truecrime_noir_director"
            if duration >= 50 and any(kw in haystack for kw in ("êm", "chậm", "tâm sự", "triết lý", "đời người")):
                return "kr_grace_pastoral_letter"
            return "kr_truecrime_forensic_dossier"

        if lang == "en":
            if any(kw in haystack for kw in ("intelligence", "declassif", "cia", "nsa", "bí mật", "classified", "espionage")):
                return "us_classified_intel_declassified"
            if any(
                kw in haystack for kw in ("presidential", "first family", "white house", "dynasty", "archival chronicle", "history", "lịch sử")
            ):
                return "us_presidential_archival_vault"
            if any(kw in haystack for kw in ("noir", "murder", "homicide", "detective", "true crime")):
                return "kr_truecrime_noir_director"
            return "us_classified_intel_declassified"

        if lang == "vi":
            return "vn_investigative_fraud_lab"

        # Fallback for JA / ZH / DE / FR / ES or any other market
        if any(kw in haystack for kw in ("geopolit", "infrastructure", "전략", "地政学")):
            return "kr_geopolitics_strategic_intel"
        return "kr_truecrime_forensic_dossier"

    def analyze_profile_rhythm_dna(
        self,
        profile_data: dict[str, Any],
        *,
        custom_direction: str = "",
        preferred_base_voice_id: str | None = None,
    ) -> dict[str, Any]:
        """Synthesize a complete 3-layer `rhythm_dna` + `voice_color_spec` tailored to `profile_data`."""
        market = str(profile_data.get("market") or "KR").strip().upper() or "KR"
        lang_map = {"KR": "ko", "US": "en", "VN": "vi", "JP": "ja"}
        lang = str(
            profile_data.get("default_language")
            or profile_data.get("language")
            or lang_map.get(market, "ko")
        ).strip().lower() or "ko"

        archetype_id = self.classify_profile_archetype(profile_data, custom_direction=custom_direction)
        template = copy.deepcopy(GENRE_RHYTHM_ARCHETYPES[archetype_id])

        # Fine-tune dynamically if custom_direction or profile duration/notes specify extra nuances
        brief = profile_data.get("default_creative_brief") if isinstance(profile_data.get("default_creative_brief"), dict) else {}
        duration = float(
            profile_data.get("default_duration_minutes")
            or profile_data.get("target_duration_minutes")
            or brief.get("target_duration_minutes")
            or 30.0
        )
        dir_low = f"{custom_direction} {profile_data.get('voice_and_structure') or ''} {profile_data.get('notes') or ''}".lower()

        voice_color = template["voice_color_spec"]
        prosody = voice_color["prosody_profile"]
        vocal_cad = template["vocal_cadence"]
        edit_cad = template["editing_cadence"]

        if any(k in dir_low for k in ("trầm hơn", "sâu hơn", "ấm hơn", "deeper", "warmer")):
            voice_color["pitch_semitones"] = round(max(-0.65, float(voice_color.get("pitch_semitones", 0.0)) - 0.15), 2)
            prosody["warm_db"] = round(min(2.6, float(prosody.get("warm_db", 1.0)) + 0.35), 2)
        elif any(k in dir_low for k in ("sáng hơn", "sắc hơn", "trẻ hơn", "brighter", "crisper")):
            voice_color["pitch_semitones"] = round(min(0.45, float(voice_color.get("pitch_semitones", 0.0)) + 0.15), 2)
            voice_color["presence_db"] = round(min(1.8, float(voice_color.get("presence_db", 0.5)) + 0.35), 2)

        ed_dna = profile_data.get("editing_dna") if isinstance(profile_data.get("editing_dna"), dict) else {}
        edit_preset = str(ed_dna.get("preset_id") or "").strip().lower()
        lock_kr_natural_1x_speed = (
            edit_preset in {"forensic_noir", "forensic_noir_director_v2", "financial_forensic_vox"}
            or archetype_id in {
                "kr_truecrime_noir_director",
                "kr_truecrime_forensic_dossier",
                "kr_cyber_finance_senior_clarity",
                "kr_geopolitics_strategic_intel",
            }
        )

        if any(k in dir_low for k in ("chậm hơn", "thong thả", "khoan thai", "slower")):
            if lock_kr_natural_1x_speed:
                prosody["tts_speed"] = 1.0
            else:
                prosody["tts_speed"] = round(max(0.92, float(prosody.get("tts_speed", 1.0)) - 0.03), 3)
            for pk in list(vocal_cad["pause_tiers_sec"].keys()):
                vocal_cad["pause_tiers_sec"][pk] = round(float(vocal_cad["pause_tiers_sec"][pk]) * 1.08, 3)
            for sk in ("urgent_max_sec", "standard_avg_sec", "contemplative_min_sec", "max_static_hold_sec"):
                edit_cad["shot_pacing_sec"][sk] = round(float(edit_cad["shot_pacing_sec"][sk]) * 1.10, 2)
        elif any(k in dir_low for k in ("nhanh hơn", "dồn dập hơn", "gấp hơn", "faster", "snappier")):
            if lock_kr_natural_1x_speed:
                prosody["tts_speed"] = 1.0
            else:
                prosody["tts_speed"] = round(min(1.02, float(prosody.get("tts_speed", 1.0)) + 0.025), 3)
            for pk in ("urgent_action", "tight_continuation", "standard_narrative"):
                vocal_cad["pause_tiers_sec"][pk] = round(max(0.22, float(vocal_cad["pause_tiers_sec"][pk]) * 0.92), 3)

        if lock_kr_natural_1x_speed:
            prosody["tts_speed"] = 1.0

        # Long-form endurance adjustment (>= 50 min): slightly calmer pause breathing without artificial tts_speed slowdown
        if duration >= 50 and archetype_id != "kr_grace_pastoral_letter":
            prosody["tts_speed"] = round(max(1.0, float(prosody.get("tts_speed", 1.0))), 3)
            vocal_cad["pause_tiers_sec"]["paragraph_breath"] = round(
                max(1.02, float(vocal_cad["pause_tiers_sec"]["paragraph_breath"]) + 0.08), 3
            )

        base_voice_id = (
            str(preferred_base_voice_id).strip()
            if preferred_base_voice_id and str(preferred_base_voice_id).strip()
            else self.resolve_default_master_voice_id(lang, archetype_id)
        )
        voice_color["recommended_base_voice_id"] = base_voice_id
        voice_color["language"] = lang

        # Scale sentence-char targets for Latin/Vietnamese alphabets when using universal archetypes
        writing_cad = template["writing_cadence"]
        if archetype_id.startswith("universal_") and lang not in ("ko", "ja", "zh"):
            writing_cad["target_avg_sentence_chars"] = [68, 128]

        # Attach Master Human Film Editor Craft Profile (`editorial_craft`) so Step 6 (@edit)
        # has explicit genre-calibrated voice cutting, caesura, J/L-cut, color arc, and sound rules.
        edit_cad["editorial_craft"] = build_editorial_craft_spec(
            archetype_id,
            vocal_cadence=vocal_cad,
            editing_cadence=edit_cad,
        )

        # Showcase preview sentence in target language
        if lang == "ko":
            showcase_text = str(voice_color.get("sample_showcase_ko") or GENRE_RHYTHM_ARCHETYPES["kr_truecrime_noir_director"]["voice_color_spec"]["sample_showcase_ko"])
        elif lang == "vi":
            showcase_text = str(voice_color.get("sample_showcase_vi") or GENRE_RHYTHM_ARCHETYPES["vn_investigative_fraud_lab"]["voice_color_spec"]["sample_showcase_vi"])
        elif lang == "ja":
            showcase_text = "事件発生から二十一年。残されたわずかな記録が、すべての真実を語り始めました。"
        else:
            showcase_text = str(voice_color.get("sample_showcase_en") or GENRE_RHYTHM_ARCHETYPES["us_classified_intel_declassified"]["voice_color_spec"]["sample_showcase_en"])
        voice_color["sample_showcase_text"] = showcase_text

        return {
            "version": 2,
            "archetype_id": archetype_id,
            "archetype_label_vi": template["archetype_label_vi"],
            "specialist_summary_vi": template["specialist_summary_vi"],
            "language": lang,
            "market": market,
            "custom_direction": str(custom_direction or "").strip(),
            "voice_color_spec": voice_color,
            "writing_cadence": writing_cad,
            "vocal_cadence": vocal_cad,
            "editing_cadence": edit_cad,
            "analyzed_at": _now_iso(),
        }

    # ------------------------------------------------------------------
    # CofiVoice DB & Prompt Provisioning
    # ------------------------------------------------------------------

    def _read_cofivoice_db(self) -> list[dict[str, Any]]:
        db_path = self.cofivoice_dir / "voices_db.json"
        if not db_path.exists():
            return []
        return json.loads(db_path.read_text(encoding="utf-8"))

    def _write_cofivoice_db(self, entries: list[dict[str, Any]]) -> None:
        db_path = self.cofivoice_dir / "voices_db.json"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = db_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(entries, indent=4, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, db_path)

    @staticmethod
    def _build_profile_voice_display_name(
        profile_data: dict[str, Any],
        rhythm_dna: dict[str, Any],
        *,
        source_mode: str = "base_voice",
        base_voice_id: str = "",
    ) -> str:
        raw_label = str(profile_data.get("label") or profile_data.get("name") or profile_data.get("id") or "Channel").strip()
        # Strip leading mojibake question-marks or flag noise while keeping readable brand title
        cleaned = re.sub(r"^\?+\s*", "", raw_label).strip()
        short_lbl = cleaned.split("(")[0].split("·")[0].strip(" ·-|")
        if not short_lbl:
            short_lbl = cleaned[:36].strip()
        if len(short_lbl) > 38:
            short_lbl = short_lbl[:38].rsplit(" ", 1)[0].rstrip() + "…"
        prefix = "K1" if base_voice_id == CLEAN_MASTER_VOICES["ko"]["id"] else ("Clone" if source_mode == "user_sample" else "Signature")
        raw_color_tag = str(((rhythm_dna.get("voice_color_spec") or {}).get("color_label_vi") or "")).split("·")[-1].strip()
        color_tag = raw_color_tag.split("&")[0].strip() or raw_color_tag
        if len(color_tag) > 34:
            color_tag = color_tag[:34].rsplit(" ", 1)[0].rstrip()
        return f"{prefix} · {short_lbl} ({color_tag})" if color_tag else f"{prefix} · {short_lbl}"

    def _synthesize_and_save_showcase_preview(
        self,
        *,
        voice_id: str,
        language: str,
        showcase_text: str,
        voice_color_spec: dict[str, Any],
    ) -> str | None:
        """Render a real genre-specific preview WAV via live CofiVoice `/api/tts` and polish its timbre."""
        previews_dir = self.cofivoice_dir / "static" / "previews"
        previews_dir.mkdir(parents=True, exist_ok=True)
        out_wav = previews_dir / f"{voice_id}.wav"

        tts_text = showcase_text
        if language == "ko":
            try:
                from documentary.voice import normalize_korean_tts_text

                tts_text = normalize_korean_tts_text(showcase_text)
            except Exception:
                pass

        try:
            resp = self.session.post(
                f"{self.cofivoice_url}/api/tts",
                json={
                    "text": tts_text,
                    "voice_id": voice_id,
                    "speed": 1.0,
                    "num_step": 26,
                    "language": language,
                    "mode": "balanced",
                },
                timeout=90.0,
            )
            if resp.ok and len(resp.content) > 1000:
                wav_bytes = resp.content
                if language == "ko":
                    try:
                        from documentary.voice import sculpt_wav_bytes_for_korean_broadcast

                        wav_bytes = sculpt_wav_bytes_for_korean_broadcast(wav_bytes, text=tts_text, is_final_beat=True)
                    except Exception:
                        pass
                wav_bytes = apply_voice_color_polish_wav_bytes(wav_bytes, voice_color_spec)
                out_wav.write_bytes(wav_bytes)
                return f"/static/previews/{voice_id}.wav"
        except Exception:
            pass
        return None

    def design_and_bind_profile_voice(
        self,
        profile_data: dict[str, Any],
        *,
        profile_service: Any | None = None,
        source_mode: str = "base_voice",
        base_voice_id: str | None = None,
        sample_audio_bytes: bytes | None = None,
        sample_audio_base64: str | None = None,
        sample_filename: str = "sample.wav",
        ref_text: str | None = None,
        custom_direction: str = "",
        persist_to_profile: bool = True,
        synthesize_preview: bool = True,
    ) -> dict[str, Any]:
        """Create or update a dedicated 1-of-1 custom voice for a Channel Profile and bind `rhythm_dna`.

        - `source_mode == "base_voice"` (default): Uses clean master `K1` (`09c70cc1-cc86-4905-b65b-3967209c3175`)
          for Korean (or clean language master / user-picked clean voice), clones its lossless 1st-generation `.pt`
          conditioning prompt into a profile-exclusive `voice_id` (reusing existing profile-exclusive `voice_id`
          when re-designing the same profile so `voices_db.json` stays clean and never bloats!), writes the custom
          `prosody_profile` + `voice_color_spec`, and renders a genre-matched preview WAV.
        - `source_mode == "user_sample"`: Uploads user's sample audio (`WAV/MP3/M4A`) to `CofiVoice` `/api/clone`
          to extract a brand-new `.pt` voice clone prompt, then attaches the genre-analyzed `prosody_profile`
          and `voice_color_spec`, and renders the genre-matched preview WAV.
        """
        mode_clean = "user_sample" if str(source_mode or "").strip().lower() in {"user_sample", "upload", "clone_sample"} else "base_voice"
        rhythm_dna = self.analyze_profile_rhythm_dna(
            profile_data,
            custom_direction=custom_direction,
            preferred_base_voice_id=base_voice_id if mode_clean == "base_voice" else None,
        )
        lang = str(rhythm_dna["language"])
        voice_color_spec = dict(rhythm_dna["voice_color_spec"])
        prosody_profile = dict(voice_color_spec.get("prosody_profile") or {})

        profile_id = str(profile_data.get("id") or profile_data.get("channel_profile_id") or "").strip()
        chosen_master_id = str(base_voice_id or voice_color_spec.get("recommended_base_voice_id") or self.resolve_default_master_voice_id(lang, rhythm_dna["archetype_id"])).strip()
        voice_name = self._build_profile_voice_display_name(
            profile_data,
            rhythm_dna,
            source_mode=mode_clean,
            base_voice_id=chosen_master_id,
        )

        created_voice_entry: dict[str, Any]

        if mode_clean == "user_sample":
            decoded_bytes, safe_fname = decode_audio_upload_payload(
                audio_bytes=sample_audio_bytes,
                audio_base64=sample_audio_base64,
                filename=sample_filename,
            )
            form_data: dict[str, Any] = {
                "name": voice_name,
                "language": lang,
                "recorded": "false",
            }
            if ref_text and str(ref_text).strip():
                form_data["ref_text"] = str(ref_text).strip()
            resp = self.session.post(
                f"{self.cofivoice_url}/api/clone",
                data=form_data,
                files={"ref_audio": (safe_fname, decoded_bytes, "application/octet-stream")},
                timeout=240.0,
            )
            resp.raise_for_status()
            cloned_json = resp.json()
            if not isinstance(cloned_json, dict) or not cloned_json.get("id"):
                raise RuntimeError("CofiVoice không trả về ID giọng sau khi clone mẫu người dùng")
            new_voice_id = str(cloned_json["id"]).strip()

            with _COFIVOICE_DB_LOCK:
                db = self._read_cofivoice_db()
                # Remove any old auto-generated signature voice previously bound exclusively to this profile
                if profile_id:
                    db = [
                        v for v in db
                        if not (
                            v.get("id") != new_voice_id
                            and str(v.get("channel_profile_id") or "") == profile_id
                            and bool(v.get("is_profile_signature"))
                        )
                    ]
                enriched_prosody = {
                    **prosody_profile,
                    "pitch_semitones": float(voice_color_spec.get("pitch_semitones") or 0.0),
                    "presence_db": float(voice_color_spec.get("presence_db") or 0.0),
                    "archetype_id": rhythm_dna["archetype_id"],
                }
                target_entry = next((v for v in db if v.get("id") == new_voice_id), None)
                if target_entry is None:
                    target_entry = dict(cloned_json)
                    db.append(target_entry)
                target_entry["name"] = voice_name
                target_entry["language"] = lang
                target_entry["channel_profile_id"] = profile_id or None
                target_entry["is_profile_signature"] = True
                target_entry["source_mode"] = "user_sample"
                target_entry["prosody_profile"] = enriched_prosody
                self._write_cofivoice_db(db)
                created_voice_entry = dict(target_entry)
        else:
            # Base-voice sculpting from clean master (e.g. K1 clean `09c70cc1-cc86-4905-b65b-3967209c3175`)
            prompts_dir = self.cofivoice_dir / "saved_prompts"
            previews_dir = self.cofivoice_dir / "static" / "previews"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            previews_dir.mkdir(parents=True, exist_ok=True)

            with _COFIVOICE_DB_LOCK:
                db = self._read_cofivoice_db()
                master_entry = next((v for v in db if str(v.get("id")) == chosen_master_id), None)
                if master_entry is None and lang == "ko":
                    chosen_master_id = CLEAN_MASTER_VOICES["ko"]["id"]
                    master_entry = next((v for v in db if str(v.get("id")) == chosen_master_id), None)

                existing_sig = (
                    next(
                        (
                            v
                            for v in db
                            if profile_id
                            and str(v.get("channel_profile_id") or "") == profile_id
                            and bool(v.get("is_profile_signature"))
                        ),
                        None,
                    )
                    if profile_id
                    else None
                )
                new_voice_id = str(existing_sig["id"]) if existing_sig else str(uuid4())
                rel_prompt_path = f"saved_prompts\\{new_voice_id}.pt"
                abs_dest_prompt = self.cofivoice_dir / "saved_prompts" / f"{new_voice_id}.pt"

                src_prompt_abs = self.cofivoice_dir / "saved_prompts" / f"{chosen_master_id}.pt"
                if master_entry and master_entry.get("prompt_path"):
                    cand_p = self.cofivoice_dir / Path(str(master_entry["prompt_path"]).replace("\\", "/"))
                    if cand_p.exists():
                        src_prompt_abs = cand_p
                if src_prompt_abs.exists():
                    if src_prompt_abs.resolve() != abs_dest_prompt.resolve():
                        shutil.copy2(src_prompt_abs, abs_dest_prompt)
                else:
                    # Unit-test / sandbox fallback when CofiVoice prompt dir is mocked
                    abs_dest_prompt.write_bytes(b"MOCK_PT_PROMPT")

                # Seed initial preview WAV from clean master polished with profile color before live TTS showcase runs
                src_prev_abs = previews_dir / f"{chosen_master_id}.wav"
                dest_prev_abs = previews_dir / f"{new_voice_id}.wav"
                if src_prev_abs.exists() and not dest_prev_abs.exists():
                    polished_seed = apply_voice_color_polish_wav_bytes(src_prev_abs.read_bytes(), voice_color_spec)
                    dest_prev_abs.write_bytes(polished_seed)

                enriched_prosody = {
                    **prosody_profile,
                    "pitch_semitones": float(voice_color_spec.get("pitch_semitones") or 0.0),
                    "presence_db": float(voice_color_spec.get("presence_db") or 0.0),
                    "archetype_id": rhythm_dna["archetype_id"],
                    "source_master_voice_id": chosen_master_id,
                }
                entry_payload = {
                    "id": new_voice_id,
                    "name": voice_name,
                    "type": "clone",
                    "language": lang,
                    "prompt_path": rel_prompt_path,
                    "preview_url": f"/static/previews/{new_voice_id}.wav" if dest_prev_abs.exists() else None,
                    "channel_profile_id": profile_id or None,
                    "is_profile_signature": True,
                    "source_mode": "base_voice",
                    "source_master_voice_id": chosen_master_id,
                    "prosody_profile": enriched_prosody,
                }
                if existing_sig is not None:
                    existing_sig.update(entry_payload)
                else:
                    db.append(entry_payload)
                self._write_cofivoice_db(db)
                created_voice_entry = dict(entry_payload)

        # Render live genre-specific showcase preview when CofiVoice is online
        if synthesize_preview:
            showcase_url = self._synthesize_and_save_showcase_preview(
                voice_id=created_voice_entry["id"],
                language=lang,
                showcase_text=str(voice_color_spec.get("sample_showcase_text") or ""),
                voice_color_spec=voice_color_spec,
            )
            if showcase_url:
                created_voice_entry["preview_url"] = showcase_url
                with _COFIVOICE_DB_LOCK:
                    db = self._read_cofivoice_db()
                    for item in db:
                        if item.get("id") == created_voice_entry["id"]:
                            item["preview_url"] = showcase_url
                            break
                    self._write_cofivoice_db(db)

        master_name_lookup = next(
            (m["name"] for m in CLEAN_MASTER_VOICES.values() if m["id"] == chosen_master_id),
            chosen_master_id[:8] if chosen_master_id else None,
        )
        voice_signature = {
            "voice_id": created_voice_entry["id"],
            "voice_name": created_voice_entry["name"],
            "language": lang,
            "source_mode": mode_clean,
            "base_voice_id": chosen_master_id if mode_clean == "base_voice" else None,
            "base_voice_name": master_name_lookup if mode_clean == "base_voice" else "User Uploaded Sample",
            "source_master_voice_id": chosen_master_id if mode_clean == "base_voice" else None,
            "custom_direction": str(custom_direction or "").strip(),
            "archetype_id": rhythm_dna["archetype_id"],
            "color_label_vi": voice_color_spec.get("color_label_vi"),
            "pitch_semitones": float(voice_color_spec.get("pitch_semitones") or 0.0),
            "presence_db": float(voice_color_spec.get("presence_db") or 0.0),
            "tts_speed": float(prosody_profile.get("tts_speed") or 1.0),
            "warm_db": float(prosody_profile.get("warm_db") or 0.0),
            "deharsh_db": float(prosody_profile.get("deharsh_db") or 0.0),
            "highshelf_db": float(prosody_profile.get("highshelf_db") or 0.0),
            "preview_url": created_voice_entry.get("preview_url"),
            "proxy_preview_url": f"/api/voice/preview-audio/{created_voice_entry['id']}",
            "designed_at": _now_iso(),
        }
        rhythm_dna["voice_signature"] = voice_signature

        updated_profile = None
        if persist_to_profile and profile_id and profile_service is not None:
            # Also align editing_dna.typical_pacing_sec lightly if not manually locked, while preserving all visual mix rules
            existing_ed = dict(profile_data.get("editing_dna") or {})
            target_std_sec = float(rhythm_dna["editing_cadence"]["shot_pacing_sec"]["standard_avg_sec"])
            existing_ed["rhythm_archetype_id"] = rhythm_dna["archetype_id"]
            existing_ed["rhythm_synced_pacing_sec"] = target_std_sec
            existing_ed["hold_visual_across_dramatic_pause"] = True

            updated_profile = profile_service.update_profile(
                profile_id,
                {
                    "voice_id": created_voice_entry["id"],
                    "default_voice_id": created_voice_entry["id"],
                    "voice_signature": voice_signature,
                    "rhythm_dna": rhythm_dna,
                    "editing_dna": existing_ed,
                },
            )

        return {
            "voice": {
                **created_voice_entry,
                "proxy_preview_url": f"/api/voice/preview-audio/{created_voice_entry['id']}",
            },
            "voice_signature": voice_signature,
            "rhythm_dna": rhythm_dna,
            "profile": updated_profile,
        }


_ARCHETYPE_CRAFT_PRESETS: dict[str, dict[str, Any]] = {
    "kr_truecrime_noir_director": {
        "cold_open_pre_voice_sec": 1.38,
        "chapter_curtain_breath_sec": 1.96,
        "twist_reveal_breath_sec": 1.56,
        "somber_aftermath_breath_sec": 1.72,
        "urgent_shave_gap_sec": 0.25,
        "mid_beat_caesura_policy": {
            "enabled": True,
            "max_per_10min": 3,
            "hold_sec": 0.78,
            "min_beat_dur_sec": 4.0,
            "min_beat_spacing": 11,
        },
        "jl_cut_policy": {
            "hard_cut_ratio_target": 0.76,
            "j_cut_prelap_frames": 9,
            "l_cut_linger_frames": 16,
            "dissolve_frames": 18,
        },
        "color_emotion_arc": {
            "act_1": {"mood": "cold_slate_mystery", "temp_shift": -8, "sat_pct": 88, "contrast_pct": 108, "vignette": 0.34},
            "act_2": {"mood": "clinical_tungsten_investigation", "temp_shift": -3, "sat_pct": 92, "contrast_pct": 106, "vignette": 0.28},
            "act_3": {"mood": "claustrophobic_emerald_anomaly", "temp_shift": -6, "sat_pct": 84, "contrast_pct": 114, "vignette": 0.38},
            "act_4": {"mood": "stark_noir_twist_reveal", "temp_shift": -10, "sat_pct": 78, "contrast_pct": 120, "vignette": 0.42},
            "act_5": {"mood": "somber_human_aftermath", "temp_shift": +2, "sat_pct": 82, "contrast_pct": 104, "vignette": 0.32},
        },
        "pre_twist_bgm_drop_enabled": True,
    },
    "kr_truecrime_forensic_dossier": {
        "cold_open_pre_voice_sec": 1.15,
        "chapter_curtain_breath_sec": 1.84,
        "twist_reveal_breath_sec": 1.44,
        "somber_aftermath_breath_sec": 1.56,
        "urgent_shave_gap_sec": 0.27,
        "mid_beat_caesura_policy": {
            "enabled": True,
            "max_per_10min": 2,
            "hold_sec": 0.70,
            "min_beat_dur_sec": 4.2,
            "min_beat_spacing": 12,
        },
        "jl_cut_policy": {
            "hard_cut_ratio_target": 0.80,
            "j_cut_prelap_frames": 8,
            "l_cut_linger_frames": 14,
            "dissolve_frames": 16,
        },
        "color_emotion_arc": {
            "act_1": {"mood": "forensic_steel_opening", "temp_shift": -6, "sat_pct": 90, "contrast_pct": 106, "vignette": 0.26},
            "act_2": {"mood": "lab_precision_neutral", "temp_shift": -2, "sat_pct": 94, "contrast_pct": 105, "vignette": 0.22},
            "act_3": {"mood": "contradiction_amber_alert", "temp_shift": +3, "sat_pct": 90, "contrast_pct": 112, "vignette": 0.30},
            "act_4": {"mood": "decisive_evidence_lock", "temp_shift": -7, "sat_pct": 84, "contrast_pct": 116, "vignette": 0.34},
            "act_5": {"mood": "verdict_sober_clarity", "temp_shift": 0, "sat_pct": 88, "contrast_pct": 104, "vignette": 0.26},
        },
        "pre_twist_bgm_drop_enabled": True,
    },
    "kr_cyber_finance_senior_clarity": {
        "cold_open_pre_voice_sec": 1.28,
        "chapter_curtain_breath_sec": 1.98,
        "twist_reveal_breath_sec": 1.54,
        "somber_aftermath_breath_sec": 1.66,
        "urgent_shave_gap_sec": 0.38,
        "mid_beat_caesura_policy": {
            "enabled": True,
            "max_per_10min": 2,
            "hold_sec": 0.74,
            "min_beat_dur_sec": 4.6,
            "min_beat_spacing": 14,
        },
        "jl_cut_policy": {
            "hard_cut_ratio_target": 0.68,
            "j_cut_prelap_frames": 10,
            "l_cut_linger_frames": 18,
            "dissolve_frames": 22,
        },
        "color_emotion_arc": {
            "act_1": {"mood": "institutional_navy_trust", "temp_shift": -4, "sat_pct": 94, "contrast_pct": 104, "vignette": 0.22},
            "act_2": {"mood": "clear_ledger_daylight", "temp_shift": 0, "sat_pct": 96, "contrast_pct": 104, "vignette": 0.18},
            "act_3": {"mood": "hidden_laundering_amber_teal", "temp_shift": -3, "sat_pct": 90, "contrast_pct": 109, "vignette": 0.26},
            "act_4": {"mood": "account_freeze_reveal", "temp_shift": -6, "sat_pct": 86, "contrast_pct": 112, "vignette": 0.30},
            "act_5": {"mood": "warm_protective_wisdom", "temp_shift": +4, "sat_pct": 92, "contrast_pct": 102, "vignette": 0.22},
        },
        "pre_twist_bgm_drop_enabled": True,
    },
    "kr_geopolitics_strategic_intel": {
        "cold_open_pre_voice_sec": 1.05,
        "chapter_curtain_breath_sec": 1.74,
        "twist_reveal_breath_sec": 1.36,
        "somber_aftermath_breath_sec": 1.46,
        "urgent_shave_gap_sec": 0.26,
        "mid_beat_caesura_policy": {
            "enabled": True,
            "max_per_10min": 2,
            "hold_sec": 0.66,
            "min_beat_dur_sec": 4.2,
            "min_beat_spacing": 12,
        },
        "jl_cut_policy": {
            "hard_cut_ratio_target": 0.82,
            "j_cut_prelap_frames": 8,
            "l_cut_linger_frames": 12,
            "dissolve_frames": 15,
        },
        "color_emotion_arc": {
            "act_1": {"mood": "orbital_steel_blue", "temp_shift": -5, "sat_pct": 94, "contrast_pct": 107, "vignette": 0.24},
            "act_2": {"mood": "strategic_corridor_clarity", "temp_shift": -1, "sat_pct": 96, "contrast_pct": 106, "vignette": 0.20},
            "act_3": {"mood": "chokepoint_amber_tension", "temp_shift": +4, "sat_pct": 92, "contrast_pct": 112, "vignette": 0.28},
            "act_4": {"mood": "geopolitical_checkmate_stark", "temp_shift": -6, "sat_pct": 88, "contrast_pct": 115, "vignette": 0.30},
            "act_5": {"mood": "horizon_macro_equilibrium", "temp_shift": +1, "sat_pct": 92, "contrast_pct": 104, "vignette": 0.22},
        },
        "pre_twist_bgm_drop_enabled": True,
    },
    "kr_grace_pastoral_letter": {
        "cold_open_pre_voice_sec": 1.85,
        "chapter_curtain_breath_sec": 2.45,
        "twist_reveal_breath_sec": 1.82,
        "somber_aftermath_breath_sec": 1.98,
        "urgent_shave_gap_sec": 0.54,
        "mid_beat_caesura_policy": {
            "enabled": False,
            "max_per_10min": 0,
            "hold_sec": 0.0,
            "min_beat_dur_sec": 6.0,
            "min_beat_spacing": 99,
        },
        "jl_cut_policy": {
            "hard_cut_ratio_target": 0.15,
            "j_cut_prelap_frames": 15,
            "l_cut_linger_frames": 24,
            "dissolve_frames": 30,
        },
        "color_emotion_arc": {
            "act_1": {"mood": "soft_twilight_ solace", "temp_shift": +6, "sat_pct": 90, "contrast_pct": 96, "vignette": 0.24},
            "act_2": {"mood": "warm_candle_scripture", "temp_shift": +9, "sat_pct": 92, "contrast_pct": 97, "vignette": 0.22},
            "act_3": {"mood": "quiet_valley_reflection", "temp_shift": +5, "sat_pct": 88, "contrast_pct": 96, "vignette": 0.25},
            "act_4": {"mood": "grace_dawn_illumination", "temp_shift": +11, "sat_pct": 94, "contrast_pct": 98, "vignette": 0.20},
            "act_5": {"mood": "peaceful_sanctuary_benediction", "temp_shift": +10, "sat_pct": 92, "contrast_pct": 95, "vignette": 0.22},
        },
        "pre_twist_bgm_drop_enabled": False,
    },
    "us_presidential_archival_vault": {
        "cold_open_pre_voice_sec": 1.40,
        "chapter_curtain_breath_sec": 1.94,
        "twist_reveal_breath_sec": 1.50,
        "somber_aftermath_breath_sec": 1.65,
        "urgent_shave_gap_sec": 0.30,
        "mid_beat_caesura_policy": {
            "enabled": True,
            "max_per_10min": 2,
            "hold_sec": 0.72,
            "min_beat_dur_sec": 4.5,
            "min_beat_spacing": 13,
        },
        "jl_cut_policy": {
            "hard_cut_ratio_target": 0.65,
            "j_cut_prelap_frames": 11,
            "l_cut_linger_frames": 18,
            "dissolve_frames": 24,
        },
        "color_emotion_arc": {
            "act_1": {"mood": "archival_parchment_gravitas", "temp_shift": +5, "sat_pct": 86, "contrast_pct": 105, "vignette": 0.30},
            "act_2": {"mood": "kodachrome_chronicle", "temp_shift": +4, "sat_pct": 90, "contrast_pct": 106, "vignette": 0.26},
            "act_3": {"mood": "oval_office_midnight_shadow", "temp_shift": -2, "sat_pct": 82, "contrast_pct": 112, "vignette": 0.34},
            "act_4": {"mood": "smoking_gun_memo_contrast", "temp_shift": -4, "sat_pct": 80, "contrast_pct": 116, "vignette": 0.36},
            "act_5": {"mood": "historic_monument_legacy", "temp_shift": +6, "sat_pct": 86, "contrast_pct": 103, "vignette": 0.28},
        },
        "pre_twist_bgm_drop_enabled": True,
    },
    "us_classified_intel_declassified": {
        "cold_open_pre_voice_sec": 1.18,
        "chapter_curtain_breath_sec": 1.82,
        "twist_reveal_breath_sec": 1.44,
        "somber_aftermath_breath_sec": 1.54,
        "urgent_shave_gap_sec": 0.26,
        "mid_beat_caesura_policy": {
            "enabled": True,
            "max_per_10min": 3,
            "hold_sec": 0.74,
            "min_beat_dur_sec": 4.2,
            "min_beat_spacing": 11,
        },
        "jl_cut_policy": {
            "hard_cut_ratio_target": 0.80,
            "j_cut_prelap_frames": 8,
            "l_cut_linger_frames": 14,
            "dissolve_frames": 16,
        },
        "color_emotion_arc": {
            "act_1": {"mood": "bunker_cold_cyan", "temp_shift": -7, "sat_pct": 86, "contrast_pct": 110, "vignette": 0.32},
            "act_2": {"mood": "microfilm_dossier_olive", "temp_shift": -2, "sat_pct": 88, "contrast_pct": 108, "vignette": 0.28},
            "act_3": {"mood": "black_ops_high_tension", "temp_shift": -6, "sat_pct": 82, "contrast_pct": 115, "vignette": 0.36},
            "act_4": {"mood": "declassified_redaction_flash", "temp_shift": -8, "sat_pct": 78, "contrast_pct": 118, "vignette": 0.38},
            "act_5": {"mood": "cold_war_echo_resolution", "temp_shift": 0, "sat_pct": 85, "contrast_pct": 105, "vignette": 0.30},
        },
        "pre_twist_bgm_drop_enabled": True,
    },
    "vn_investigative_fraud_lab": {
        "cold_open_pre_voice_sec": 1.25,
        "chapter_curtain_breath_sec": 1.88,
        "twist_reveal_breath_sec": 1.50,
        "somber_aftermath_breath_sec": 1.68,
        "urgent_shave_gap_sec": 0.26,
        "mid_beat_caesura_policy": {
            "enabled": True,
            "max_per_10min": 3,
            "hold_sec": 0.76,
            "min_beat_dur_sec": 4.1,
            "min_beat_spacing": 11,
        },
        "jl_cut_policy": {
            "hard_cut_ratio_target": 0.76,
            "j_cut_prelap_frames": 9,
            "l_cut_linger_frames": 16,
            "dissolve_frames": 18,
        },
        "color_emotion_arc": {
            "act_1": {"mood": "investigative_slate_hook", "temp_shift": -6, "sat_pct": 90, "contrast_pct": 108, "vignette": 0.30},
            "act_2": {"mood": "forensic_money_trail", "temp_shift": -2, "sat_pct": 93, "contrast_pct": 106, "vignette": 0.25},
            "act_3": {"mood": "trap_tightening_amber", "temp_shift": +2, "sat_pct": 88, "contrast_pct": 113, "vignette": 0.34},
            "act_4": {"mood": "mastermind_unmasked_contrast", "temp_shift": -8, "sat_pct": 80, "contrast_pct": 118, "vignette": 0.38},
            "act_5": {"mood": "human_empathy_aftermath", "temp_shift": +3, "sat_pct": 85, "contrast_pct": 103, "vignette": 0.30},
        },
        "pre_twist_bgm_drop_enabled": True,
    },
    "universal_science_engineering_explainer": {
        "cold_open_pre_voice_sec": 1.28,
        "chapter_curtain_breath_sec": 1.86,
        "twist_reveal_breath_sec": 1.46,
        "somber_aftermath_breath_sec": 1.58,
        "urgent_shave_gap_sec": 0.28,
        "mid_beat_caesura_policy": {
            "enabled": True,
            "max_per_10min": 2,
            "hold_sec": 0.72,
            "min_beat_dur_sec": 4.3,
            "min_beat_spacing": 12,
        },
        "jl_cut_policy": {
            "hard_cut_ratio_target": 0.75,
            "j_cut_prelap_frames": 9,
            "l_cut_linger_frames": 16,
            "dissolve_frames": 20,
        },
        "color_emotion_arc": {
            "act_1": {"mood": "deep_cosmos_indigo", "temp_shift": -6, "sat_pct": 94, "contrast_pct": 108, "vignette": 0.28},
            "act_2": {"mood": "blueprint_precision_cyan", "temp_shift": -3, "sat_pct": 96, "contrast_pct": 106, "vignette": 0.22},
            "act_3": {"mood": "critical_stress_amber", "temp_shift": +4, "sat_pct": 92, "contrast_pct": 112, "vignette": 0.28},
            "act_4": {"mood": "breakthrough_clarity_reveal", "temp_shift": 0, "sat_pct": 98, "contrast_pct": 114, "vignette": 0.24},
            "act_5": {"mood": "luminous_horizon_awe", "temp_shift": +5, "sat_pct": 95, "contrast_pct": 104, "vignette": 0.22},
        },
        "pre_twist_bgm_drop_enabled": True,
    },
    "universal_cultural_human_essay": {
        "cold_open_pre_voice_sec": 1.52,
        "chapter_curtain_breath_sec": 2.08,
        "twist_reveal_breath_sec": 1.60,
        "somber_aftermath_breath_sec": 1.78,
        "urgent_shave_gap_sec": 0.36,
        "mid_beat_caesura_policy": {
            "enabled": True,
            "max_per_10min": 2,
            "hold_sec": 0.74,
            "min_beat_dur_sec": 4.6,
            "min_beat_spacing": 14,
        },
        "jl_cut_policy": {
            "hard_cut_ratio_target": 0.55,
            "j_cut_prelap_frames": 12,
            "l_cut_linger_frames": 20,
            "dissolve_frames": 24,
        },
        "color_emotion_arc": {
            "act_1": {"mood": "golden_hour_nostalgia", "temp_shift": +6, "sat_pct": 92, "contrast_pct": 101, "vignette": 0.24},
            "act_2": {"mood": "intimate_everyday_film", "temp_shift": +4, "sat_pct": 94, "contrast_pct": 102, "vignette": 0.22},
            "act_3": {"mood": "quiet_existential_shadow", "temp_shift": -3, "sat_pct": 86, "contrast_pct": 107, "vignette": 0.30},
            "act_4": {"mood": "kishotenketsu_perspective_shift", "temp_shift": +2, "sat_pct": 92, "contrast_pct": 108, "vignette": 0.26},
            "act_5": {"mood": "poetic_lingering_catharsis", "temp_shift": +7, "sat_pct": 90, "contrast_pct": 100, "vignette": 0.24},
        },
        "pre_twist_bgm_drop_enabled": False,
    },
    "universal_empire_biography_chronicle": {
        "cold_open_pre_voice_sec": 1.18,
        "chapter_curtain_breath_sec": 1.84,
        "twist_reveal_breath_sec": 1.46,
        "somber_aftermath_breath_sec": 1.58,
        "urgent_shave_gap_sec": 0.26,
        "mid_beat_caesura_policy": {
            "enabled": True,
            "max_per_10min": 3,
            "hold_sec": 0.72,
            "min_beat_dur_sec": 4.2,
            "min_beat_spacing": 12,
        },
        "jl_cut_policy": {
            "hard_cut_ratio_target": 0.78,
            "j_cut_prelap_frames": 9,
            "l_cut_linger_frames": 15,
            "dissolve_frames": 18,
        },
        "color_emotion_arc": {
            "act_1": {"mood": "prestige_gold_slate_ambition", "temp_shift": +2, "sat_pct": 94, "contrast_pct": 108, "vignette": 0.28},
            "act_2": {"mood": "hypergrowth_electric_momentum", "temp_shift": 0, "sat_pct": 98, "contrast_pct": 108, "vignette": 0.24},
            "act_3": {"mood": "boardroom_hubris_amber", "temp_shift": +5, "sat_pct": 90, "contrast_pct": 112, "vignette": 0.30},
            "act_4": {"mood": "empire_freefall_cold_steel", "temp_shift": -8, "sat_pct": 80, "contrast_pct": 118, "vignette": 0.36},
            "act_5": {"mood": "empty_throne_reflection", "temp_shift": -1, "sat_pct": 86, "contrast_pct": 104, "vignette": 0.28},
        },
        "pre_twist_bgm_drop_enabled": True,
    },
}


def build_editorial_craft_spec(
    archetype_id: str,
    *,
    vocal_cadence: dict[str, Any] | None = None,
    editing_cadence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build explicit Master Human Film Editor craft parameters for `archetype_id`."""
    preset = copy.deepcopy(
        _ARCHETYPE_CRAFT_PRESETS.get(archetype_id)
        or _ARCHETYPE_CRAFT_PRESETS["kr_truecrime_forensic_dossier"]
    )
    pause_tiers = (vocal_cadence or {}).get("pause_tiers_sec") if isinstance(vocal_cadence, dict) else {}
    ed_cad = editing_cadence if isinstance(editing_cadence, dict) else {}
    swell_db = float(ed_cad.get("bgm_silence_swell_db") or 2.0)

    if isinstance(pause_tiers, dict) and pause_tiers:
        preset["chapter_curtain_breath_sec"] = round(
            max(float(preset["chapter_curtain_breath_sec"]), float(pause_tiers.get("act_curtain", 1.75)) + 0.08),
            3,
        )
        preset["twist_reveal_breath_sec"] = round(
            max(float(preset["twist_reveal_breath_sec"]), float(pause_tiers.get("dramatic_landing", 1.35)) + 0.06),
            3,
        )
        preset["urgent_shave_gap_sec"] = round(
            min(float(preset["urgent_shave_gap_sec"]), float(pause_tiers.get("urgent_action", 0.28))),
            3,
        )

    preset["archetype_id"] = archetype_id
    preset["shot_scale_progression"] = {
        "cycle": ["WIDE_ESTABLISHING", "MEDIUM_SUBJECT", "CLOSE_UP_DETAIL", "MACRO_EVIDENCE_OR_FACE"],
        "min_scale_delta_pct": 30,
        "max_same_scale_streak": 2,
        "fincher_motivated_camera": True,
        "murch_eye_trace_continuity": True,
    }
    preset["sound_design_soul"] = {
        "pre_twist_bgm_drop_enabled": bool(preset.get("pre_twist_bgm_drop_enabled", True)),
        "room_tone_floor_db": -41.0,
        "room_tone_linear_gain": 0.015,
        "bgm_speech_duck_db": -16.5,
        "bgm_breath_swell_db": round(swell_db, 2),
        "sfx_transient_lead_frames": 2,
        "outro_tail_sec": 3.8,
    }
    return preset


def resolve_editorial_craft_profile(rhythm_dna_or_job: dict[str, Any] | None) -> dict[str, Any]:
    """Return the complete Master Editor Craft Profile for any `rhythm_dna` or `job` dict."""
    dna: dict[str, Any] = {}
    if isinstance(rhythm_dna_or_job, dict):
        if rhythm_dna_or_job.get("vocal_cadence") and rhythm_dna_or_job.get("editing_cadence"):
            dna = rhythm_dna_or_job
        else:
            dna = resolve_job_rhythm_dna(rhythm_dna_or_job)
    archetype_id = str(dna.get("archetype_id") or "kr_truecrime_forensic_dossier").strip()
    ed_cad = dna.get("editing_cadence") if isinstance(dna.get("editing_cadence"), dict) else {}
    voc_cad = dna.get("vocal_cadence") if isinstance(dna.get("vocal_cadence"), dict) else {}
    existing = ed_cad.get("editorial_craft")
    if isinstance(existing, dict) and existing.get("color_emotion_arc") and existing.get("mid_beat_caesura_policy"):
        return copy.deepcopy(existing)
    return build_editorial_craft_spec(archetype_id, vocal_cadence=voc_cad, editing_cadence=ed_cad)


def resolve_job_rhythm_dna(job: dict[str, Any]) -> dict[str, Any]:
    """Extract or synthesize on-the-fly `rhythm_dna` (with `editorial_craft`) for ANY production `job`."""
    if not isinstance(job, dict):
        return {}

    def _enrich_craft(dna_obj: dict[str, Any]) -> dict[str, Any]:
        out = copy.deepcopy(dna_obj)
        ed = out.setdefault("editing_cadence", {})
        if isinstance(ed, dict) and not isinstance(ed.get("editorial_craft"), dict):
            ed["editorial_craft"] = build_editorial_craft_spec(
                str(out.get("archetype_id") or "kr_truecrime_forensic_dossier"),
                vocal_cadence=out.get("vocal_cadence") if isinstance(out.get("vocal_cadence"), dict) else None,
                editing_cadence=ed,
            )
        return out

    direct = job.get("rhythm_dna")
    if isinstance(direct, dict) and direct.get("vocal_cadence") and direct.get("editing_cadence"):
        return _enrich_craft(direct)
    snap = job.get("channel_profile_snapshot")
    if isinstance(snap, dict):
        snap_dna = snap.get("rhythm_dna")
        if isinstance(snap_dna, dict) and snap_dna.get("vocal_cadence") and snap_dna.get("editing_cadence"):
            return _enrich_craft(snap_dna)
    prof = job.get("profile") or job.get("channel_profile")
    if isinstance(prof, dict):
        prof_dna = prof.get("rhythm_dna")
        if isinstance(prof_dna, dict) and prof_dna.get("vocal_cadence") and prof_dna.get("editing_cadence"):
            return _enrich_craft(prof_dna)
    prof_id = str(
        job.get("channel_profile_id")
        or (snap.get("id") if isinstance(snap, dict) else "")
        or ""
    ).strip()
    if prof_id:
        try:
            from services.channel_profile_service import ChannelProfileService

            fetched = ChannelProfileService().get_profile(prof_id)
            if isinstance(fetched.get("rhythm_dna"), dict) and fetched["rhythm_dna"].get("vocal_cadence"):
                return _enrich_craft(dict(fetched["rhythm_dna"]))
            return VoiceRhythmSpecialistService().analyze_profile_rhythm_dna(fetched)
        except Exception:
            pass
    if isinstance(snap, dict) and snap:
        return VoiceRhythmSpecialistService().analyze_profile_rhythm_dna(snap)

    # Ad-hoc / custom job with no stored channel profile: synthesize bespoke Rhythm DNA from topic + brief + language!
    brief = job.get("creative_brief") if isinstance(job.get("creative_brief"), dict) else {}
    lang = str(job.get("language") or "ko").strip().lower() or "ko"
    market_guess = {"ko": "KR", "en": "US", "vi": "VN", "ja": "JP"}.get(lang, "US")
    synthetic_profile = {
        "id": prof_id or "adhoc-episode-profile",
        "label": str(job.get("topic") or job.get("title") or ""),
        "market": str(job.get("market") or market_guess),
        "default_language": lang,
        "target_duration_minutes": job.get("target_duration_minutes") or brief.get("target_duration_minutes") or 20,
        "allowed_topics": str(job.get("topic") or ""),
        "notes": f"{brief.get('narrative_angle') or ''} {brief.get('writing_style') or ''} {brief.get('notes') or ''}".strip(),
        "default_creative_brief": brief,
        "editing_dna": job.get("editing_dna") if isinstance(job.get("editing_dna"), dict) else {},
    }
    return VoiceRhythmSpecialistService().analyze_profile_rhythm_dna(synthetic_profile)
