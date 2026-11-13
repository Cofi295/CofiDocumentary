import io
import json
from pathlib import Path
import wave

import pytest

from documentary.quality import normalize_production_recipe, validate_phase_quality
from documentary.srt import build_srt, format_srt_time
from documentary.voice import CofiVoiceEngine, INTER_BEAT_PAUSE_SEC, OUTRO_FADE_TAIL_SEC, wav_duration


def _wav_bytes(duration_sec: float, sample_rate: int = 1000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * round(duration_sec * sample_rate))
    return buffer.getvalue()


class _TtsResponse:
    def __init__(self, content: bytes, seed: str):
        self.content = content
        self.headers = {"X-Seed": seed}

    def raise_for_status(self):
        return None


class _DurationSession:
    def __init__(self, base_duration_sec: float = 25.0):
        self.calls = []
        self.base_duration_sec = float(base_duration_sec)

    def post(self, _url, json, timeout):
        self.calls.append(dict(json))
        speed = float(json["speed"])
        seed = str(json.get("seed") or len(self.calls))
        return _TtsResponse(_wav_bytes(self.base_duration_sec / speed, sample_rate=10_000), seed)


class _HealthResponse:
    def __init__(self, ok: bool, status_code: int = 200):
        self.ok = ok
        self.status_code = status_code


class _DiscoverySession:
    def get(self, url, timeout):
        if url == "http://127.0.0.1:8776/api/health":
            return _HealthResponse(True)
        raise __import__("requests").ConnectionError("offline")


def test_voice_engine_discovers_existing_shared_instance_on_legacy_port():
    engine = CofiVoiceEngine("http://127.0.0.1:8000", session=_DiscoverySession())

    health = engine.discover(["http://127.0.0.1:8000", "http://127.0.0.1:8776"])

    assert health["ok"] is True
    assert health["url"] == "http://127.0.0.1:8776"
    assert engine.base_url == "http://127.0.0.1:8776"


def test_srt_uses_real_voice_timestamps_per_visual_beat():
    beats = [
        {"beat_id": "B001", "text": "Cau mot", "start_sec": 0.0, "end_sec": 3.25},
        {"beat_id": "B002", "text": "Cau hai", "start_sec": 3.25, "end_sec": 7.8},
    ]
    text = build_srt(beats)
    assert "00:00:00,000 --> 00:00:03,250" in text
    assert "00:00:03,250 --> 00:00:07,800" in text
    assert "Cau mot" in text and "Cau hai" in text


def test_format_srt_time_handles_minutes_and_milliseconds():
    assert format_srt_time(65.432) == "00:01:05,432"


def test_voice_quality_gate_accepts_duration_outside_estimated_target(tmp_path: Path):
    recipe = normalize_production_recipe({}, target_duration_minutes=5)
    contract = recipe["quality_contract"]
    beat_ids = [f"B{i + 1:03d}" for i in range(contract["min_scene_count"])]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "target_duration_sec": 300,
        "beats": [{"beat_id": beat_id} for beat_id in beat_ids],
    }), encoding="utf-8")
    narration = tmp_path / "audio" / "narration.wav"
    narration.parent.mkdir(parents=True, exist_ok=True)
    narration.write_bytes(b"wav")
    (tmp_path / "voice_manifest.json").write_text(json.dumps({
        "duration_sec": 270.37,
        "narration_path": str(narration),
        "beats": [{"beat_id": beat_id} for beat_id in beat_ids],
    }), encoding="utf-8")

    validate_phase_quality("voice", tmp_path, {"production_recipe": recipe})


def test_voice_engine_keeps_natural_speed_when_estimated_target_differs(tmp_path: Path):
    recipe = normalize_production_recipe({}, target_duration_minutes=2)
    beat_ids = [f"B{i + 1:03d}" for i in range(recipe["quality_contract"]["min_scene_count"])]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "target_duration_sec": 120,
        "beats": [
            {"beat_id": beat_id, "narration_text": f"Narration {beat_id}", "target_duration_sec": 30}
            for beat_id in beat_ids
        ],
    }), encoding="utf-8")
    session = _DurationSession(base_duration_sec=100.0 / len(beat_ids))
    engine = CofiVoiceEngine(session=session)
    job = {
        "language": "en",
        "voice": {"speed": 1.0, "mode": "balanced"},
        "production_recipe": recipe,
    }

    engine.run(job, tmp_path)

    manifest = json.loads((tmp_path / "voice_manifest.json").read_text(encoding="utf-8"))
    expected_total = 100.0 + (len(beat_ids) - 1) * INTER_BEAT_PAUSE_SEC + OUTRO_FADE_TAIL_SEC
    assert manifest["duration_sec"] == pytest.approx(expected_total, abs=0.05)
    assert wav_duration(tmp_path / "audio" / "narration.wav") == pytest.approx(expected_total, abs=0.05)
    last_beat = manifest["beats"][-1]
    assert last_beat["outro_tail_sec"] == pytest.approx(OUTRO_FADE_TAIL_SEC, abs=0.01)
    assert last_beat["end_sec"] - last_beat["speech_end_sec"] == pytest.approx(OUTRO_FADE_TAIL_SEC, abs=0.01)
    srt_text = (tmp_path / "subtitles.srt").read_text(encoding="utf-8")
    assert format_srt_time(last_beat["speech_end_sec"]) in srt_text
    assert manifest["speed"] == 1.0
    assert manifest["requested_speed"] == 1.0
    assert manifest["auto_fit_applied"] is False
    assert len(session.calls) == len(beat_ids)


def test_normalize_korean_tts_text_converts_comma_numbers_and_counters():
    from documentary.voice import normalize_korean_tts_text

    raw = (
        "5살 아이의 기억으로 2,000킬로미터 떨어진 고향에서 5,000위안과 26년 동안 "
        "50대 후반 부부를 찾았습니다. 연 14.6% 수익과 십사점육 퍼센트, 백구십육 개, "
        "베이징-안후이성 제1중급인민법원 1,200자루."
    )
    norm = normalize_korean_tts_text(raw)
    assert "이천 킬로미터" in norm
    assert "오천 위안" in norm
    assert "이십육년 동안" in norm
    assert "오십대 후반" in norm
    assert norm.count("십사점육 퍼센트") == 2
    assert "백구십육개" in norm
    assert "베이징 안후이성" in norm
    assert "제일중급인민법원" in norm
    assert "천이백자루" in norm
    assert "2,000" not in norm
    assert "5,000" not in norm


def test_sculpt_wav_bytes_for_korean_broadcast_trims_and_compresses_long_internal_pauses():
    import numpy as np
    from documentary.voice import sculpt_wav_bytes_for_korean_broadcast, wav_duration

    sr = 24000
    t_voice = np.linspace(0.0, 0.5, int(sr * 0.5), endpoint=False, dtype=np.float32)
    voiced = 0.25 * np.sin(2.0 * np.pi * 220.0 * t_voice)
    lead_sil = np.zeros(int(sr * 0.25), dtype=np.float32)
    mid_sil = np.zeros(int(sr * 0.85), dtype=np.float32)
    trail_sil = np.zeros(int(sr * 0.30), dtype=np.float32)
    full = np.concatenate([lead_sil, voiced, mid_sil, voiced, trail_sil])
    pcm = np.clip(np.round(full * 32767.0), -32768, 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    raw_bytes = buf.getvalue()

    sculpted_bytes = sculpt_wav_bytes_for_korean_broadcast(raw_bytes)
    with wave.open(io.BytesIO(sculpted_bytes), "rb") as r:
        sculpted_dur = r.getnframes() / float(r.getframerate())

    # 0.5s + 0.5s voiced + ~0.285s mid pause + 0.025s lead + 0.035s trail ≈ 1.345s (down from 1.90s)
    assert 1.25 <= sculpted_dur <= 1.45


def test_validate_korean_script_grammar_integrity_catches_dangling_modifiers_and_duplicate_subjects():
    from documentary.quality import validate_korean_script_grammar_integrity

    valid_beats = [
        {"beat_id": "B001", "narration_text": "서른한 살이 된 양뉴화는 동영상 플랫폼 더우인에 영상을 올렸습니다."},
        {"beat_id": "B002", "narration_text": "무덤 앞에 무릎을 꿇은 자매는 판결문 복사본을 불태웠습니다."},
    ]
    validate_korean_script_grammar_integrity(valid_beats)

    with pytest.raises(RuntimeError, match="dangling human modifier"):
        validate_korean_script_grammar_integrity([
            {"beat_id": "B068", "narration_text": "서른한 살이 된 동영상 플랫폼 더우인에 자신의 사연을 올렸습니다."},
        ])

    with pytest.raises(RuntimeError, match="duplicate topic subject"):
        validate_korean_script_grammar_integrity([
            {"beat_id": "B095", "narration_text": "양뉴화는 그토록 그리워하던 양뉴화는 마침내 고향 집에 도착했습니다."},
        ])


def test_compute_contextual_beat_pause_adapts_to_narrative_situations():
    from documentary.voice import compute_contextual_beat_pause, plan_contextual_beat_pauses
    from documentary.quality import evaluate_ypp_visual_role_mix

    b_base = {
        "beat_id": "B001",
        "text": "2016년 2월 6일 저녁, 푸저우 남역 맞이방은 귀성객들로 붐볐습니다.",
        "duration_sec": 7.2,
        "story_group": "ACT01_SG01",
    }
    p_tight, r_tight = compute_contextual_beat_pause(
        b_base,
        {"beat_id": "B002", "text": "그 인파 속에서 외삼촌 셰 씨는 전광판을 올려다봤습니다.", "story_group": "ACT01_SG01"},
    )
    assert r_tight == "tight_continuation"
    assert 0.28 <= p_tight <= 0.38

    # Different scene_id or VOX visual_type alone must NOT falsely inflate standard narrative breath
    p_std, r_std = compute_contextual_beat_pause(
        {**b_base, "scene_id": "S001", "visual_type": "REAL_FTG", "story_group": ""},
        {"beat_id": "B002", "text": "외삼촌 셰 씨는 도착 열차를 기다리고 있었습니다.", "scene_id": "S002", "visual_type": "VOX", "story_group": ""},
    )
    assert r_std == "standard_narrative"
    assert 0.41 <= p_std <= 0.54

    # Mid-scene contrast ('하지만') stays crisp in Tier 2 unless accompanied by a structural paragraph shift
    p_mid_con, r_mid_con = compute_contextual_beat_pause(
        b_base,
        {"beat_id": "B002", "text": "하지만 열차는 아직 플랫폼에 들어오지 않았습니다.", "story_group": "ACT01_SG01"},
    )
    assert r_mid_con == "standard_narrative"
    assert 0.45 <= p_mid_con <= 0.54

    # Tier 3: Genuine temporal/paragraph shift & heavy emotional confession
    p_shift, r_shift = compute_contextual_beat_pause(
        b_base,
        {"beat_id": "B017", "text": "2016년 2월 14일, 신고를 받은 경찰이 숙소 앞에 도착했습니다."},
    )
    assert r_shift == "topic_or_scene_shift"
    assert 0.68 <= p_shift <= 0.80

    p_quote, r_quote = compute_contextual_beat_pause(
        {"beat_id": "B010", "text": "그는 재판정에서 “어머니의 고통을 끝내고 싶었다”고 털어놓았습니다.", "duration_sec": 7.2},
        {"beat_id": "B011", "text": "방청석에서는 낮은 탄식이 새어 나왔습니다."},
    )
    assert r_quote == "emotional_quote_or_reflection"
    assert 0.70 <= p_quote <= 0.82

    # Tier 4: Intentional dramatic landings (rhetorical question, cliffhanger silence, twist/CINEMA_TEXT, Act boundary)
    p_q, r_q = compute_contextual_beat_pause(
        {"beat_id": "B016", "text": "미국에 있다던 두 사람이 출국조차 하지 않았다면 대체 어디로 사라진 걸까요?", "duration_sec": 7.2},
        b_base,
    )
    assert r_q == "rhetorical_question_suspense"
    assert 1.15 <= p_q <= 1.30

    p_sil, r_sil = compute_contextual_beat_pause(
        {"beat_id": "B151", "text": "고향이 푸저우가 아니냐고 묻는 순간 정적이 흘렀습니다.", "duration_sec": 7.8},
        b_base,
    )
    assert r_sil == "suspense_cliffhanger"
    assert 1.25 <= p_sil <= 1.40

    p_ct, r_ct = compute_contextual_beat_pause(
        {"beat_id": "B048", "text": "편취한 금액은 약 2억 7,000만 원에 달했습니다.", "visualType": "CINEMA_TEXT", "duration_sec": 7.5},
        b_base,
    )
    assert r_ct == "cinema_text_punctuation"
    assert 1.12 <= p_ct <= 1.26

    p_act, r_act = compute_contextual_beat_pause(
        {**b_base, "act": "ACT_01"},
        {**b_base, "beat_id": "B027", "act": "ACT_02"},
    )
    assert r_act == "act_transition"
    assert 1.50 <= p_act <= 1.62

    # Sequence-level orchestration: single-sided CINEMA_TEXT + 3-beat dramatic cooldown + acoustic edge compensation
    seq_beats = [
        {"beat_id": "B182", "text": "사형이 집행되면서 비극은 가짜였습니다.", "visualType": "REAL_FTG", "duration_sec": 6.8},
        {"beat_id": "B183", "text": "사형 집행 전, 우셰위는 끝내 유족 접견을 신청하지 않았습니다.", "visualType": "CINEMA_TEXT", "duration_sec": 7.4},
        {"beat_id": "B184", "text": "또 다른 충격적인 현장이 드러났습니다.", "visualType": "AI_4D", "duration_sec": 7.0},
        {"beat_id": "B185", "text": "그 자리에서 모든 기록이 확인됐습니다.", "visualType": "REAL_FTG", "duration_sec": 6.5},
    ]
    seq_edges = [(0.02, 0.03), (0.02, 0.03), (0.02, 0.03), (0.02, 0.03)]
    seq_planned = plan_contextual_beat_pauses(seq_beats, edge_silences=seq_edges)
    # B182->B183 yields to B183->B184 (single-sided CINEMA_TEXT), and B184->B185 is suppressed by cooldown
    assert seq_planned[0][0] < 0.55
    assert seq_planned[1][1] == "cinema_text_punctuation" and seq_planned[1][0] >= 1.05
    assert seq_planned[2][0] < 0.55

    # Role DNA gate catches AI-still flood / real-footage starvation and accepts balanced 4-layer mix
    with pytest.raises(RuntimeError, match="Real footage ratio"):
        evaluate_ypp_visual_role_mix({
            "total_beats": 188,
            "real_footage_beats_count": 48,
            "vox_beats_count": 32,
            "ai_reconstruction_beats_count": 108,
        })
    res = evaluate_ypp_visual_role_mix({
        "total_beats": 188,
        "real_footage_beats_count": 96,
        "vox_beats_count": 42,
        "cinema_text_beats_count": 15,
        "ai_reconstruction_beats_count": 35,
    })
    assert res["status"] == "PASSED"


def test_normalize_korean_tts_text_handles_integer_percent_and_sino_counters():
    from documentary.voice import normalize_korean_tts_text

    raw = "상위 1% 성적과 상위 5퍼센트, 유사도 98% 이상, 90퍼센트 기준, 48세 역사 교사, 102호 숙소, 불과 3초 남짓, 219일 동안."
    norm = normalize_korean_tts_text(raw)
    assert "일 퍼센트" in norm
    assert "오 퍼센트" in norm
    assert "구십팔 퍼센트" in norm
    assert "구십 퍼센트" in norm
    assert "사십팔세" in norm
    assert "백이호" in norm
    assert "삼초 남짓" in norm
    assert "이백십구일 동안" in norm
    assert "%" not in norm


def test_korean_script_prosody_gate_catches_unquoted_speech_monotony_and_uniform_length():
    from documentary.quality import validate_korean_script_grammar_integrity

    with pytest.raises(RuntimeError, match="unquoted direct speech"):
        validate_korean_script_grammar_integrity([
            {"beat_id": "B162", "narration_text": "그리고 더 말씀하지 마십시오, 따라가겠습니다라는 짧은 한마디와 함께 두 손을 내밀었습니다."},
        ])

    # Quoted speech passes cleanly
    validate_korean_script_grammar_integrity([
        {"beat_id": "B162", "narration_text": '"더 말씀하지 마십시오. 따라가겠습니다." 짧은 한마디와 함께, 스스로 두 손을 내밀었습니다.'},
    ])

    # Monotonous >70% ~습니다 wall across 36 sentences is rejected
    monotonous = [
        {"beat_id": f"B{i:03d}", "narration_text": "2016년 2월 14일 신고를 받은 푸저우시 진안 공안분국 형사들이 학교 관사로 즉시 출동했습니다."}
        for i in range(1, 37)
    ]
    with pytest.raises(RuntimeError, match="prosody monotony error"):
        validate_korean_script_grammar_integrity(monotonous)

    # Raw '%' in a full-length Korean episode is rejected
    mixed_with_raw_pct = []
    for i in range(1, 37):
        if i == 1:
            txt = "상위 1% 성적을 유지하던 수재였습니다."
        elif i % 3 == 0:
            txt = "수사관들은 멈춰 섰죠."
        elif i % 4 == 0:
            txt = "그리고, 그 밀봉된 방 안."
        else:
            txt = "학교 행정실 금고에서 사직서 한 장이 나오며 비밀이 풀렸습니다."
        mixed_with_raw_pct.append({"beat_id": f"B{i:03d}", "narration_text": txt})
    with pytest.raises(RuntimeError, match="raw '%' symbol"):
        validate_korean_script_grammar_integrity(mixed_with_raw_pct)


def test_korean_script_prosody_gate_rejects_deogunyo_and_excessive_hanging_neundeyo():
    from documentary.quality import validate_korean_script_grammar_integrity

    def _base_episode():
        rows = []
        for i in range(1, 37):
            if i % 6 == 0:
                txt = "수사관들은 멈춰 섰죠."
            elif i % 4 == 0:
                txt = "그리고, 그 밀봉된 방 안."
            else:
                txt = "학교 행정실 금고에서 사직서 한 장이 나오며 비밀이 풀렸습니다."
            rows.append({"beat_id": f"B{i:03d}", "narration_text": txt})
        return rows

    ep_ok = _base_episode()
    validate_korean_script_grammar_integrity(ep_ok)

    ep_deogunyo = _base_episode()
    ep_deogunyo[2]["narration_text"] = "작은 유리 렌즈 위에 하얀 치약이 두껍게 발라져 있었더군요."
    with pytest.raises(RuntimeError, match="narrator POV error"):
        validate_korean_script_grammar_integrity(ep_deogunyo)

    ep_neundeyo = _base_episode()
    for idx in (1, 5, 9):
        ep_neundeyo[idx]["narration_text"] = "주방의 액화석유가스 통 고무호스는 예리하게 잘려 있었는데요."
    with pytest.raises(RuntimeError, match="hanging-intonation error"):
        validate_korean_script_grammar_integrity(ep_neundeyo)


def test_normalize_korean_tts_text_prevents_kaili_particle_misparse_and_expands_acronyms():
    from documentary.voice import normalize_korean_tts_text

    # Exact problem sentences from yesterday's Kaili episode (20261030-081721-2a473306)
    s1 = "2018년 7월 30일, 구이저우성 첸둥난주 중급인민법원에서 준엄한 1심 판결이 내려졌습니다."
    s2 = "17동 5층 501호 창문 너머로 502호 주민의 동향을 지켜보며 16년간 1급 수배범으로 숨어 살았습니다."
    s3 = '418병원 인근 1.5km 지점 CCTV와 Y-STR DNA 감식 결과, 64식 권총 1정과 실탄 6발이 <break time="0.28s"/> 확인됐습니다.'

    n1 = normalize_korean_tts_text(s1)
    n2 = normalize_korean_tts_text(s2)
    n3 = normalize_korean_tts_text(s3)

    assert "이천십팔년 칠월 삼십일," in n1
    assert "준엄한 일심 판결이" in n1
    assert "일 심" not in n1
    assert "삼십 일" not in n1

    assert "십칠동 오층 오백일호 창문" in n2
    assert "오백이호 주민의" in n2
    assert "십육년간 일급 수배범으로" in n2
    assert "오백일 호" not in n2
    assert "오백이 호" not in n2

    assert "사일팔병원 인근 일점오 킬로미터 지점 씨씨티비와 와이에스티알 디엔에이" in n3
    assert "육사식 권총 한정과 실탄 여섯발이" in n3
    assert '<break time="0.28s"/>' in n3


def test_korean_emotional_prosody_contrastive_pauses_and_qa_gate(tmp_path: Path):
    from documentary.voice import (
        direct_korean_emotional_prosody,
        enrich_beats_with_script_structure,
        evaluate_episode_voice_cadence,
        plan_contextual_beat_pauses,
    )

    p_act = direct_korean_emotional_prosody(
        {"beat_id": "B033", "text": "길 건너편 어둠 속에 매복해 있던 괴한 다섯 명이 일제히 수송차로 덮쳐 들었습니다."},
        base_speed=1.0,
        index=32,
        total_beats=199,
    )
    assert p_act["emotion_register"] == "urgent_action"
    assert p_act["beat_speed"] > 1.01
    assert p_act["gain_db"] > 0.0

    p_punch = direct_korean_emotional_prosody(
        {"beat_id": "B036", "text": "아홉 발의 총성."},
        base_speed=1.0,
        index=35,
        total_beats=199,
    )
    assert p_punch["emotion_register"] == "stark_punch"
    assert p_punch["beat_speed"] <= 0.89
    assert p_punch["tts_text"].endswith("…")

    p_somber = direct_korean_emotional_prosody(
        {"beat_id": "B038", "text": "조수석에 탑승해 있던 무장 대원 궈진창이 첫 집중 사격을 피하지 못한 채 현장에서 순직하고 말았습니다."},
        base_speed=1.0,
        index=37,
        total_beats=199,
    )
    assert p_somber["emotion_register"] == "somber_tragedy"
    assert p_somber["beat_speed"] <= 0.88
    assert '<break time="0.38s"/>' in p_somber["tts_text"]
    assert p_somber["gain_db"] < -0.5

    p_q = direct_korean_emotional_prosody(
        {"beat_id": "B050", "text": "무게 일점오 톤이 넘는 현금수송차가 어떻게 대낮 도로 위에서 감쪽같이 증발해 버린 걸까요?"},
        base_speed=1.0,
        index=49,
        total_beats=199,
    )
    assert p_q["emotion_register"] == "suspense_question"
    assert p_q["beat_speed"] <= 0.90
    assert '<break time="0.34s"/>' in p_q["tts_text"]

    script_md = (
        "1995년 12월 22일 동짓날 오전, 판위시 거리에는 안개가 깔려 있었습니다. "
        "흰색 수송차가 은행 철문 앞에 멈춰 섰습니다.\n\n"
        "길 건너편 어둠 속에 매복해 있던 괴한들이 수송차로 덮쳐 들었습니다. "
        "다섯 명의 손에는 권총이 차갑게 들려 있었습니다. "
        "경고 사격조차 없었습니다. 아홉 발의 총성. "
        "운전석 앞유리가 거미줄처럼 하얗게 갈라졌습니다. "
        "조수석 대원이 집중 사격을 피하지 못한 채 현장에서 순직하고 말았습니다.\n\n"
        "수백 곳의 검문망 어디에서도 수송차는 포착되지 않았습니다. "
        "현금수송차가 어떻게 대낮 도로 위에서 증발해 버린 걸까요?\n\n"
        "수사팀은 단서를 추적했습니다. 현장 탄피를 대조했습니다. "
        "기록을 전수 조사했습니다. 용의선상을 압축했습니다. "
        "총기 번호를 확인했습니다. 마침내 진범의 이름이 떠올랐습니다."
    )
    sents = [
        "1995년 12월 22일 동짓날 오전, 판위시 거리에는 안개가 깔려 있었습니다.",
        "흰색 수송차가 은행 철문 앞에 멈춰 섰습니다.",
        "길 건너편 어둠 속에 매복해 있던 괴한들이 수송차로 덮쳐 들었습니다.",
        "다섯 명의 손에는 권총이 차갑게 들려 있었습니다.",
        "경고 사격조차 없었습니다.",
        "아홉 발의 총성.",
        "운전석 앞유리가 거미줄처럼 하얗게 갈라졌습니다.",
        "조수석 대원이 집중 사격을 피하지 못한 채 현장에서 순직하고 말았습니다.",
        "수백 곳의 검문망 어디에서도 수송차는 포착되지 않았습니다.",
        "현금수송차가 어떻게 대낮 도로 위에서 증발해 버린 걸까요?",
        "수사팀은 단서를 추적했습니다.",
        "현장 탄피를 대조했습니다.",
        "기록을 전수 조사했습니다.",
        "용의선상을 압축했습니다.",
        "총기 번호를 확인했습니다.",
        "마침내 진범의 이름이 떠올랐습니다.",
    ]
    beats = [{"beat_id": f"B{i+1:03d}", "text": s, "duration_sec": 5.2} for i, s in enumerate(sents)]
    enrich_beats_with_script_structure(beats, script_md)
    assert beats[1].get("is_paragraph_end") is True

    planned = plan_contextual_beat_pauses(beats, is_director_v2=True)
    # Paragraph end B002 -> paragraph_breath (>= 0.85s)
    assert planned[1][1] == "paragraph_breath" and planned[1][0] >= 0.85
    # Urgent action chain B003->B004 BEFORE pre-punch hold on B004->B005 ("경고 사격조차 없었습니다.")
    assert planned[2][1] == "urgent_action_chain" and planned[2][0] <= 0.32
    assert planned[3][1] == "pre_punch_anticipation" and planned[3][0] >= 0.78
    # Back-to-back punches B005 ("경고 사격조차 없었습니다.") -> B006 ("아홉 발의 총성.") NEVER crushed!
    assert planned[4][1] == "dramatic_noun_punch" and planned[4][0] >= 0.90
    assert planned[5][1] == "dramatic_noun_punch" and planned[5][0] >= 1.32
    # Somber tragedy B008 ("...순직하고 말았습니다.") -> >= 1.24s
    assert planned[7][1] == "somber_tragedy_linger" and planned[7][0] >= 1.24

    # Episode-level @evidence_qa rejects flat uniform pauses + rushed cadence
    recipe = normalize_production_recipe({}, target_duration_minutes=5)
    min_cnt = recipe["quality_contract"]["min_scene_count"]
    flat_rendered = [
        {
            "beat_id": f"B{i+1:03d}",
            "text": "중국농업은행 베이자오 저축소 철문 앞으로 흰색 현금수송차가 미끄러지듯 멈춰 섰습니다.",
            "start_sec": i * 5.0,
            "speech_end_sec": i * 5.0 + 4.6,
            "pause_after_sec": 0.38 if i < min_cnt - 1 else 0.0,
            "pause_reason": "standard_narrative",
            "emotion_register": "narrative_flow",
        }
        for i in range(min_cnt)
    ]
    flat_audit = evaluate_episode_voice_cadence(flat_rendered, [{"synthetic_fixture": False}], language="ko")
    assert flat_audit["passed"] is False
    assert any("flat_uniform_pauses_lacking_intent" in x for x in flat_audit["issues"])

    (tmp_path / "visual_manifest.json").write_text(
        json.dumps({"target_duration_sec": 300, "beats": [{"beat_id": b["beat_id"]} for b in flat_rendered]}),
        encoding="utf-8",
    )
    narration = tmp_path / "audio" / "narration.wav"
    narration.parent.mkdir(parents=True, exist_ok=True)
    narration.write_bytes(b"wav")
    (tmp_path / "voice_manifest.json").write_text(
        json.dumps({
            "duration_sec": 80.0,
            "narration_path": str(narration),
            "qc_summary": {"cadence_audit": flat_audit},
            "beats": flat_rendered,
        }),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="VOICE cadence & emotional pacing rejected by @evidence_qa"):
        validate_phase_quality("voice", tmp_path, {"production_recipe": recipe, "language": "ko"})


def test_reuse_existing_beats_rejects_mismatched_voice_id_and_reuses_matching_voice(tmp_path: Path):
    beats = [
        {"beat_id": "B001", "narration_text": "첫 번째 문장입니다."},
        {"beat_id": "B002", "narration_text": "두 번째 문장입니다."},
    ]
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps({"beats": beats}, ensure_ascii=False),
        encoding="utf-8",
    )
    beat_dir = tmp_path / "audio" / "beats"
    beat_dir.mkdir(parents=True, exist_ok=True)
    # Pre-populate B001 with old voice K1 and B002 with new voice Gale
    (beat_dir / "B001.wav").write_bytes(_wav_bytes(3.0, sample_rate=10_000))
    (beat_dir / "B002.wav").write_bytes(_wav_bytes(4.0, sample_rate=10_000))
    (beat_dir / ".beat_voice_ids.json").write_text(
        json.dumps({"B001": "voice-old-k1", "B002": "voice-new-gale"}),
        encoding="utf-8",
    )
    (tmp_path / "audio" / ".reuse_existing_beats").touch()

    sess = _DurationSession(base_duration_sec=5.0)
    engine = CofiVoiceEngine("http://127.0.0.1:8000", session=sess)
    job = {"language": "ko", "voice": {"voice_id": "voice-new-gale", "speed": 1.0}}
    engine.run(job, tmp_path)

    # B001 had voice-old-k1 so it MUST be re-synthesized; B002 already matched voice-new-gale so it is reused!
    assert len(sess.calls) == 1
    assert sess.calls[0]["voice_id"] == "voice-new-gale"
    updated_map = json.loads((beat_dir / ".beat_voice_ids.json").read_text(encoding="utf-8"))
    assert updated_map == {"B001": "voice-new-gale", "B002": "voice-new-gale"}


