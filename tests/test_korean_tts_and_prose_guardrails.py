# -*- coding: utf-8 -*-
"""Comprehensive regression suite locking all 11 Korean TTS & broadcast prose defects."""
from __future__ import annotations

import io
import wave
import numpy as np
import pytest

from documentary.critic_loops import (
    analyze_script_spoken_quality,
    normalize_korean_script_orthography,
)
from documentary.quality import validate_korean_script_grammar_integrity
from documentary.voice import (
    normalize_korean_tts_text,
    sculpt_wav_bytes_for_korean_broadcast,
)


def _build_clean_80_sentence_episode() -> list[dict[str, str]]:
    """Construct a realistic 80-sentence Korean investigative episode passing all 11 guardrails."""
    # Pattern per 10-sentence block:
    # - 6 active ~습니다 (max 3 consecutive, ~60% total)
    # - 1 observational ~었죠 (10%, never adjacent)
    # - 1 investigative question ? (10%)
    # - 1 causal ~던 겁니다 (10%)
    # - 1 crisp <=16 non-space char dramatic brake / 체언 종결 (10%)
    templates = [
        "1995년 12월 22일 오전, 판위 지점 현금 수송차의 철문이 굳게 닫혔습니다.",
        "무장 경비원이 열쇠를 돌리는 순간 골목 어귀에서 검은 그림자가 튀어나왔습니다.",
        "단 육십 초.",
        "총성이 좁은 은행 앞마당의 공기를 날카롭게 찢어 놓았죠.",
        "현장에 남겨진 탄피 아홉 점은 대체 무엇을 말해주고 있었을까요?",
        "범인들이 노린 표적은 철제 금고 속 현금 상자 여덟 개였습니다.",
        "방폭총 열 정과 오사식 권총 두 정까지 트럭 짐칸으로 순식간에 옮겨졌습니다.",
        "치밀하게 분담된 군사 작전이나 다름없었던 겁니다.",
        "수사본부는 양산 공구오 호 선박의 이동 경로를 밤새 추적했습니다.",
        "웨 에이알 공칠사칠 호 번호판은 이미 강물 아래로 사라진 뒤였습니다.",
    ]
    beats: list[dict[str, str]] = []
    for idx in range(80):
        line = templates[idx % len(templates)]
        if idx % 10 == 2 and idx in {12, 32, 52, 72}:
            line = "모든 것이 정지된 순간이었거든요."
        beats.append({
            "beat_id": f"B{idx + 1:03d}",
            "narration_text": line,
        })
    return beats


def test_normalize_korean_tts_text_locks_all_user_reported_traps():
    raw = (
        "방폭총 10정과 54식 권총 2정, 현금 상자 8개, 현장 탄피 9점, "
        "웨AR0747호, 0747호, 양산 095호, A급 수배령, 100여만 위안, 4대 보험, 단속 건수 0건."
    )
    out = normalize_korean_tts_text(raw)
    assert "열 정" in out
    assert "두 정" in out
    assert "여덟 개" in out
    assert "탄피 아홉 점" in out
    assert "웨 에이알 공칠사칠 호" in out
    assert "양산 공구오 호" in out
    assert "에이급 수배령" in out
    assert "백여만 위안" in out
    assert "사대 보험" in out and "네대" not in out
    assert "영 건" in out and "0건" not in out


def test_normalize_korean_script_orthography_cleans_script_and_preserves_sino_units():
    raw_script = "\n".join([
        "범인들은 방폭총 10정과 권총 2정, 현금 상자 8개를 챙겼습니다.",
        "바닥에는 현장 탄피 9점이 흩어져 있었죠.",
        "웨AR0747호 차량 2대와 양산 095호 선박에 A급 수배령이 내려졌습니다.",
        "장물 100여만 위안과 4대 보험 가입 기록은 0건이었습니다.",
        "이후 19년 동안 50대 후반이 될 때까지 숨어 지냈습니다.",
    ]) + "\n"
    cleaned, pairs = normalize_korean_script_orthography(raw_script)
    assert len(pairs) == 4
    assert "방폭총 열 정과 권총 두 정, 현금 상자 여덟 개" in cleaned
    assert "현장 탄피 아홉 점" in cleaned
    assert "웨 에이알 공칠사칠 호 차량 두 대와 양산 공구오 호 선박에 에이급 수배령" in cleaned
    assert "백여만 위안과 사대 보험 가입 기록은 영 건" in cleaned
    # Sino-Korean units (19년, 50대) stay untouched
    assert "19년 동안 50대 후반" in cleaned


def test_final_beat_audio_sculpting_preserves_quiet_trailing_syllable():
    sr = 24000
    # Loud main clause (0.6s @ 0.35 amp) + quiet final '-습니다.' murmur (0.28s @ 0.010 amp, -31 dB below peak!) + 0.6s silence
    main_v = 0.35 * np.sin(2.0 * np.pi * 190.0 * np.linspace(0, 0.6, int(sr * 0.6), endpoint=False, dtype=np.float32))
    quiet_tail = 0.010 * np.sin(2.0 * np.pi * 140.0 * np.linspace(0, 0.28, int(sr * 0.28), endpoint=False, dtype=np.float32))
    trail_sil = np.zeros(int(sr * 0.60), dtype=np.float32)
    full = np.concatenate([np.zeros(int(sr * 0.1), dtype=np.float32), main_v, quiet_tail, trail_sil])
    pcm = np.clip(np.round(full * 32767.0), -32768, 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    raw_bytes = buf.getvalue()

    final_sculpted = sculpt_wav_bytes_for_korean_broadcast(raw_bytes, is_final_beat=True)
    with wave.open(io.BytesIO(final_sculpted), "rb") as r:
        final_dur = r.getnframes() / float(r.getframerate())

    # 0.60s main + 0.28s quiet tail + >=0.35s breath release >= 1.20s (zero cutoff of quiet final syllable!)
    assert final_dur >= 1.20


def test_spoken_sensor_catches_all_eleven_recurring_and_episode_defects():
    defective_lines = [
        "스물여섯 살 청년 천쉰민은 마흔여덟 살의 모 사장과 함께 현장에 나타났습니다.",
        "스물두 살이던 천쉰민은 방폭총 10정과 권총 2정, 탄피 9점을 챙겼습니다.",
        "웨AR0747호와 양산 095호에는 A급 수배령과 100여만 위안 현상금이 걸렸습니다.",
        "호송 대원 린 씨는 총성을 듣고 운전석 문을 열었습니다.",
        "운전기사 천 씨는 핸들을 꺾으며 급히 후진을 시도했습니다.",
        "호송 대원 왕 씨는 조수석 바닥으로 몸을 낮추며 대응했습니다.",
        "운전기사 천 씨는 앞유리가 깨지자 브레이크를 밟았습니다.",
        "호송 대원 린 씨는 무전기를 집어 들고 지원을 요청했습니다.",
        "첫째는 가족과 연락을 완전히 끊는 것이었습니다.",
        "둘째는 신분증을 절대 쓰지 않는 것이었습니다.",
        "셋째는 사진에 찍히지 않는 것이었습니다.",
        "불과 0.05초의 망설임도 없이 0.1초 만에 방아쇠를 당겼습니다.",
        "전과 기록은 0건이었는데요.",
        "현장 상황은 생각보다 훨씬 처참했더군요.",
        "결국 0.2초 만에 모든 상황이 종료됐는데요.",
    ]
    # Pad with 40 uniform ~습니다 sentences to trigger ~습니다 monotony + uniform 40-50 char wall
    for i in range(40):
        defective_lines.append(
            f"수사본부는 {1996 + (i % 15)}년 겨울 광둥성 일대의 모든 검문소 기록을 정밀하게 대조했습니다."
        )
    script_text = "\n\n".join(
        "\n".join(defective_lines[i : i + 3]) for i in range(0, len(defective_lines), 3)
    )
    report = analyze_script_spoken_quality(script_text, language="ko")
    defect_types = {d["type"] for d in report["defects"]}

    assert report["status"] == "NEEDS_POLISH"
    assert "formal_seumnida_prosody_monotony" in defect_types
    assert "consecutive_formal_seumnida_run" in defect_types
    assert "uniform_sentence_length_lack_of_short_brakes" in defect_types
    assert "formulaic_blotter_person_labels" in defect_types
    assert "korean_tts_orthography_hazard" in defect_types
    assert "repetitive_action_subject_tags" in defect_types
    assert "mechanical_ordinal_listicle" in defect_types
    assert "micro_decimal_seconds_spam" in defect_types
    assert "hanging_deyo_endings" in defect_types
    assert "narrator_pov_deogunyo" in defect_types


def test_quality_hard_gate_passes_clean_episode_and_rejects_regressions():
    clean_beats = _build_clean_80_sentence_episode()
    # Clean 80-sentence episode with 60% ~습니다, 10% ~었죠, 10% crisp 체언 종결 brakes, and Hangul counters passes!
    validate_korean_script_grammar_integrity(clean_beats)

    # 1. Mixed alphanumeric plate code in full episode -> rejected
    bad_plate = [dict(b) for b in clean_beats]
    bad_plate[9]["narration_text"] = "웨AR0747호 번호판은 이미 강물 아래로 사라진 뒤였습니다."
    with pytest.raises(RuntimeError, match="mixed-alphanumeric error"):
        validate_korean_script_grammar_integrity(bad_plate)

    # 2. Raw digit + native counter in full episode -> rejected
    bad_counter = [dict(b) for b in clean_beats]
    bad_counter[6]["narration_text"] = "방폭총 10정과 권총 2정이 트럭 짐칸으로 옮겨졌습니다."
    with pytest.raises(RuntimeError, match="native-counter digit error"):
        validate_korean_script_grammar_integrity(bad_counter)

    # 3. Mechanical ordinal listicle -> rejected
    bad_listicle = [dict(b) for b in clean_beats]
    bad_listicle[20]["narration_text"] = "첫째는 연락을 끊는 것이었습니다."
    bad_listicle[21]["narration_text"] = "둘째는 신분증을 버리는 것이었습니다."
    bad_listicle[22]["narration_text"] = "셋째는 사진을 피하는 것이었습니다."
    with pytest.raises(RuntimeError, match="mechanical listicle error"):
        validate_korean_script_grammar_integrity(bad_listicle)

    # 4. Action-scene '... 씨는' subject wall -> rejected
    bad_action = [dict(b) for b in clean_beats]
    for k in range(30, 35):
        ending = "몸을 낮추었죠." if k == 32 else "몸을 낮추었습니다."
        bad_action[k]["narration_text"] = f"호송 대원 린 씨는 총성을 듣고 급히 {ending}"
    with pytest.raises(RuntimeError, match="action-scene subject repetition error"):
        validate_korean_script_grammar_integrity(bad_action)


def test_custom_register_profile_isolation_preserves_grace_letter_haeyoche():
    grace_job = {
        "language": "ko",
        "speech_register": "해요체",
        "channel_profile_snapshot": {
            "id": "channel-kr-grace-letter-60m",
            "label": "은혜의 편지",
            "voice_and_structure": "따뜻한 해요체 편지 낭독",
        },
    }
    haeyo_lines = [
        "오늘 하루도 참 많이 애쓰셨어요.",
        "마음이 무거울 때는 잠시 걸음을 멈추어도 괜찮아요.",
        "조용히 눈을 감고 깊은 숨을 내쉬어 보세요.",
    ] * 30
    beats = [{"beat_id": f"B{i+1:03d}", "narration_text": s} for i, s in enumerate(haeyo_lines)]
    validate_korean_script_grammar_integrity(beats, job=grace_job)
    rep = analyze_script_spoken_quality("\n".join(haeyo_lines), language="ko", job=grace_job)
    assert rep["status"] == "PASS"


def test_truncated_geolkkayo_question_and_mandatory_post_rewrite_semantic_signoff(tmp_path):
    import json
    from documentary.codex_gateway import StageResult
    from documentary.critic_loops import run_plan_closed_loop

    clean_beats = _build_clean_80_sentence_episode()
    # Inject exact B007 missing-'왜' defect reported by user
    bad_beats = [dict(b) for b in clean_beats]
    bad_beats[6]["narration_text"] = "평생 자기 이름으로 된 신분증 한 장을 만들지 않았던 걸까요?"

    with pytest.raises(RuntimeError, match="incomplete interrogative error"):
        validate_korean_script_grammar_integrity(bad_beats)

    rep_bad = analyze_script_spoken_quality(
        "\n".join(b["narration_text"] for b in bad_beats),
        language="ko",
    )
    assert any(d["type"] == "truncated_interrogative_missing_wh_cue" for d in rep_bad["defects"])

    # With '왜' added at the front, both hard gate and sensor pass 100%
    fixed_beats = [dict(b) for b in clean_beats]
    fixed_beats[6]["narration_text"] = "왜 평생 자기 이름으로 된 신분증 한 장을 만들지 않았던 걸까요?"
    validate_korean_script_grammar_integrity(fixed_beats)
    rep_ok = analyze_script_spoken_quality(
        "\n".join(b["narration_text"] for b in fixed_beats),
        language="ko",
    )
    assert rep_ok["status"] == "PASS"

    # Also verify run_plan_closed_loop NEVER skips post-rewrite @evidence_qa semantic sign-off
    (tmp_path / "script.md").write_text(
        "\n".join(b["narration_text"] for b in clean_beats) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps({"target_duration_sec": 300, "beats": clean_beats}, ensure_ascii=False),
        encoding="utf-8",
    )

    calls: list[int] = []

    class _TwoPassSemanticCriticGateway:
        supports_critic_loop = True

        def run_prompt(self, prompt: str, workspace, label: str, **_kwargs) -> StageResult:
            calls.append(len(calls) + 1)
            if len(calls) == 1:
                # Even though regex sensor defects == [], @evidence_qa MUST still be called and can rewrite a nuance
                payload = {
                    "verdict": "NEEDS_FIX",
                    "summary": "Polished opening nuance",
                    "line_rewrites": [
                        {
                            "line": 1,
                            "original": clean_beats[0]["narration_text"],
                            "rewrite": "1995년 12월 22일 동짓날 아침, 판위 지점 현금 수송차의 철문이 굳게 닫혔습니다.",
                            "reason": "Nuance",
                        }
                    ],
                }
            else:
                # Mandatory Round 2 semantic verification of the rewritten draft before approving PASS
                payload = {"verdict": "PASS", "summary": "Verified rewritten draft semantically clean", "line_rewrites": []}
            return StageResult(0, json.dumps(payload, ensure_ascii=False), tmp_path / f"{label}.log")

    loop_res = run_plan_closed_loop({"language": "ko", "market": "KR"}, tmp_path, _TwoPassSemanticCriticGateway())
    assert len(calls) == 2
    assert loop_res["rounds"][-1]["verdict"] == "PASS"
    assert loop_res["total_surgical_rewrites"] == 1


def test_year_counter_hae_to_nyeon_with_particle_harmony_and_decimal_cohesion():
    raw_script = "\n".join([
        "열아홉 해의 시간을 건너뛰어 묶인 물증 두 점이 나란이 들어 있죠.",
        "이천십오 년 겨울과 천구백구십칠 년 봄 사이엔 열여덟 해의 공백이 가로놓여 있었죠.",
        "열 해가 넘도록, 열여덟 해라는 세월과 열여덟 해하고도 하루, 열일곱 해를 버티다 열아홉 해가 채워지던 해였습니다.",
        "수환 조키로 소문난 장부는 시커먹게 타 들어가고 비극이 연달라 터졌습니다.",
        "모든 위조극이 단수 메탈로 날 외통수였어낼.",
        "당황한 기색이 영역했죠. 두 얼굴이 하나로 포개해졌습니다.",
        "친아버지일 확률이 구십구 점 구구 퍼센트를 넘어선 겁니다.",
        "딩보시와 닉보시에서 시혜런양과 시언양의 흔적이 닝보시 공안에 포착됐습니다.",
        "닝보시 수사팀과 닝보시 검찰은 시에런량을 압송했습니다.",
    ]) + "\n"

    cleaned, pairs = normalize_korean_script_orthography(raw_script)
    assert len(pairs) == 8
    assert "19년의 시간을 건너뛰어 묶인 물증 두 점이 나란히 들어 있죠." in cleaned
    assert "2015년 겨울과 1997년 봄 사이엔 18년의 공백이 가로놓여 있었죠." in cleaned
    assert "10년이 넘도록, 18년이라는 세월과 18년하고도 하루, 17년을 버티다 19년이 채워지던 해였습니다." in cleaned
    assert "수완 좋기로 소문난 장부는 새까맣게 타 들어가고 비극이 연달아 터졌습니다." in cleaned
    assert "모든 위조극이 단숨에 탄로 날 외통수였습니다." in cleaned
    assert "당황한 기색이 역력했죠. 두 얼굴이 하나로 포개졌습니다." in cleaned
    assert "구십구점구구 퍼센트를 넘어선 겁니다." in cleaned
    assert "닝보시와 닝보시에서 시에런량과 시에런량의 흔적이 닝보시 공안에 포착됐습니다." in cleaned

    # Verify TTS normalizer also handles raw inputs directly
    tts_out = normalize_korean_tts_text(
        "열아홉 해의 시간, 열 해가 넘도록, 열일곱 해를 버티며 구십구 점 구구 퍼센트를 넘긴 이천십오 년 기록."
    )
    assert "십구년의 시간" in tts_out
    assert "십년이 넘도록" in tts_out
    assert "십칠년을 버티며" in tts_out
    assert "구십구점구구 퍼센트를" in tts_out
    assert "이천십오년 기록" in tts_out
    assert "해의" not in tts_out and "해가" not in tts_out and "해를" not in tts_out


def test_asr_predicate_tail_stutter_and_year_hoe_gates_in_inspect_beat_audio_quality(tmp_path):
    from documentary.voice import inspect_beat_audio_quality

    sr = 24000
    t = np.linspace(0.0, 2.5, int(sr * 2.5), endpoint=False, dtype=np.float32)
    voiced = 0.25 * np.sin(2.0 * np.pi * 200.0 * t)
    pcm = np.clip(np.round(voiced * 32767.0), -32768, 32767).astype(np.int16)
    wav_p = tmp_path / "beat.wav"
    with wave.open(str(wav_p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())

    # 1. Garbled predicate tail (B053 '단숨에 탄로 날 외통수였죠.' -> '단숨의 달로 날 외통수육.')
    res_tail = inspect_beat_audio_quality(
        wav_p,
        "공안의 신원 조회가 한 번이라도 들어가면 모든 위조극이 단숨에 탄로 날 외통수였죠.",
        language="ko",
        asr_transcriber=lambda _p, _l: "공안의 신원조회가 한번이라도 들어가면 모든 위조극이 단숨의 달로 날 외통수육.",
    )
    assert res_tail["passed"] is False
    assert "asr_predicate_tail_garbled" in res_tail["issues"]

    # 2. Percentage stutter ('구십구점구구 퍼센트를 넘어선 겁니다.' -> '99.99%를 99%를 넘어선 겁니다.')
    res_stutter = inspect_beat_audio_quality(
        wav_p,
        "친아버지일 확률이 구십구점구구 퍼센트를 넘어선 겁니다.",
        language="ko",
        asr_transcriber=lambda _p, _l: "친아버지일 확률이 구십구퍼센트를 구십구퍼센트를 넘어선 겁니다.",
    )
    assert res_stutter["passed"] is False
    assert "asr_stutter_repetition" in res_stutter["issues"]

    # 3. Year '년' mispronounced as '회' ('18년의 공백' -> '18회의 공백')
    res_hoe = inspect_beat_audio_quality(
        wav_p,
        "두 서류 사이엔 18년의 공백이 가로놓여 있었죠.",
        language="ko",
        asr_transcriber=lambda _p, _l: "두 서류 사이엔 18회의 공백이 가로놓여 있었죠.",
    )
    assert res_hoe["passed"] is False
    assert "asr_year_counter_hoe_drift" in res_hoe["issues"]


def test_channel_profiles_json_has_zero_conflicting_legacy_korean_rules():
    from pathlib import Path

    raw = Path("B:/ALL_TOOLS/CofiDocumentary/data/channel_profiles.json").read_text(encoding="utf-8")
    for forbidden in ("dual_layer_", "십사쩜육", "체언 종결은 전편 2~5회", "셰 씨는 첫 소개 후", "<= 6–8"):
        assert forbidden not in raw


def test_hancheung_adverb_and_drone_nine_units_never_corrupted_to_digits():
    raw_script = "\n".join([
        "밤하늘에는 체온을 잡아내는 열화상 드론 9대가 떠올랐고, 상공에는 열화상 드론 아홉 대가 선회했죠.",
        "밤이 찾아오면 포위망의 압박은 한층 더 집요해졌습니다.",
    ]) + "\n"
    cleaned, _ = normalize_korean_script_orthography(raw_script)
    assert "열화상 드론 아홉 대가 떠올랐고, 상공에는 열화상 드론 아홉 대가 선회했죠." in cleaned
    assert "포위망의 압박은 한층 더 집요해졌습니다." in cleaned
    assert "1층 더" not in cleaned
    assert "9대" not in cleaned

    tts_out = normalize_korean_tts_text(cleaned)
    assert "한층 더" in tts_out
    assert "일층 더" not in tts_out
    assert "열화상 드론 아홉 대가" in tts_out
    assert "구대가" not in tts_out


