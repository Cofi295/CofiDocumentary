from __future__ import annotations

import io
import json
from pathlib import Path
import re
import wave

import numpy as np
import pytest

from documentary.codex_gateway import StageResult
from documentary.critic_loops import (
    analyze_script_spoken_quality,
    audit_ai_visual_assets,
    audit_and_refine_storyboard_sequence,
    audit_edit_timeline_and_screen,
    audit_seo_and_mobile_thumbnail,
    rebalance_uniform_paragraph_cadence,
    run_plan_closed_loop,
    run_qc_master_screening,
)
from documentary.prompts import _detect_documentary_niche_engine, build_phase_prompt
from documentary.quality import normalize_production_recipe, validate_korean_script_grammar_integrity
from documentary.voice import CofiVoiceEngine


ROOT = Path(__file__).resolve().parents[1]


def _make_voiced_wav(
    duration_sec: float = 1.6,
    *,
    sr: int = 24000,
    internal_silence_sec: float = 0.0,
) -> bytes:
    """Build a genuine non-silent 16-bit mono WAV with optional mid-sentence dead air."""
    if internal_silence_sec > 0.0:
        voice_half = max(0.25, (duration_sec - internal_silence_sec) * 0.5)
        t = np.linspace(0.0, voice_half, int(sr * voice_half), endpoint=False, dtype=np.float32)
        seg = 0.22 * np.sin(2.0 * np.pi * 210.0 * t)
        lead = np.zeros(int(sr * 0.03), dtype=np.float32)
        hole = np.zeros(int(sr * internal_silence_sec), dtype=np.float32)
        trail = np.zeros(int(sr * 0.04), dtype=np.float32)
        arr = np.concatenate([lead, seg, hole, seg, trail])
    else:
        lead = np.zeros(int(sr * 0.03), dtype=np.float32)
        trail = np.zeros(int(sr * 0.04), dtype=np.float32)
        body_sec = max(0.25, duration_sec - 0.07)
        t = np.linspace(0.0, body_sec, int(sr * body_sec), endpoint=False, dtype=np.float32)
        body = 0.22 * np.sin(2.0 * np.pi * 210.0 * t)
        arr = np.concatenate([lead, body, trail])

    pcm = np.clip(np.round(arr * 32767.0), -32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


# ==============================================================================
# STAGE 1: SINGLE SOURCE OF TRUTH & MULTI-COUNTRY / MULTI-NICHE CRAFT
# ==============================================================================


def test_stage1_channel_profiles_and_skill_single_source_of_truth():
    profiles_raw = (ROOT / "data" / "channel_profiles.json").read_text(encoding="utf-8")
    assert "0.875" not in profiles_raw
    assert "sentence_ending_jyo_cap_rule" not in profiles_raw
    assert "라오룽즈가 남긴" not in profiles_raw

    skill_path = ROOT / "skills" / "cofi-broadcast-storytelling-mastery" / "SKILL.md"
    assert skill_path.is_file()
    skill_txt = skill_path.read_text(encoding="utf-8")
    for marker in ("SBS", "PBS", "VTV1", "NHK", "ZDF", "ARTE", "RTVE", "CCTV", "Walter Murch"):
        assert marker in skill_txt


@pytest.mark.parametrize(
    ("lang", "market", "title", "expected_label_substr"),
    [
        ("ko", "KR", "쿤밍 기숙사 실종 수사 기록", "True Crime"),
        ("en", "US", "Declassified Cold War Submarine Crisis", "Declassified Archives"),
        ("vi", "VN", "Sự Sụp Đổ Ngân Hàng Ngầm Và Bẫy Thanh Khoản", "Finance"),
        ("ja", "JP", "三峡ダム地下トンネル崩落の工学調査", "Mega-Infrastructure"),
        ("de", "DE", "Halbleiter-Monopol und EUV-Lithografie", "Tech Monopoly"),
        ("es", "ES", "Biografía oculta y ascenso al poder", "Biography"),
    ],
)
def test_stage1_multi_country_and_six_niche_prompts_stay_clean(
    tmp_path: Path,
    lang: str,
    market: str,
    title: str,
    expected_label_substr: str,
):
    job = {
        "id": f"job-{lang}",
        "title": title,
        "language": lang,
        "market": market,
        "production_recipe": normalize_production_recipe(None, target_duration_minutes=10),
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건" if lang == "ko" else "Investigative Files",
            "keyword_placement_rule": "smart_seo_flexible",
        },
    }
    niche_label, niche_guidance = _detect_documentary_niche_engine(job)
    assert expected_label_substr in niche_label
    assert len(niche_guidance) > 40

    prompt = build_phase_prompt(job, "plan", tmp_path / "ws", tmp_path / "remotion")
    assert "UNIVERSAL BROADCAST" in prompt
    assert "NEVER stuff the literal title tag" in prompt
    if lang != "ko":
        assert not re.search(r"[\uac00-\ud7a3]", prompt), f"Unexpected Hangul leaked into {lang} prompt"


def test_stage1_korean_grammar_gate_accepts_natural_76pct_seumnida_and_rejects_haoche_or_noun_flood():
    # 90-sentence broadcast script with ~77% natural ~습니다, max 4 consecutive ~습니다, varied sentence lengths
    beats = []
    for i in range(1, 91):
        if i % 5 == 0:
            txt = f"{i}번째 단서 앞에서도 형사들은 멈춰 섰죠."
        elif i % 13 == 0:
            txt = f"과연 {i}번째 통화 기록은 왜 통째로 사라진 걸까요?"
        elif i == 44:
            txt = "단 한 장의 열차표."
        elif i % 2 == 0:
            txt = f"수사팀은 {i}번째 현장 감식과 교차 대조 끝에 결정적인 열차 탑승 흔적과 계좌 흐름을 마침내 확보했습니다."
        else:
            txt = f"현장 문고리에서 지문이 나왔습니다."
        beats.append({"beat_id": f"B{i:03d}", "narration_text": txt})

    validate_korean_script_grammar_integrity(beats)

    # Archaic 하오체 ('맞소' / '처음이오') must fail immediately
    bad_haoche = [dict(b) for b in beats]
    bad_haoche[4] = {"beat_id": "B005", "narration_text": '그는 취조실에서 "맞소, 내가 처음이오."라고 답했습니다.'}
    with pytest.raises(RuntimeError, match="하오체"):
        validate_korean_script_grammar_integrity(bad_haoche)

    # Noun-fragment flood (>12% across >=80 sentences) must fail
    bad_nouns = [dict(b) for b in beats]
    for idx in range(0, 16):
        bad_nouns[idx] = {"beat_id": f"B{idx + 1:03d}", "narration_text": f"차가운 철제 캐비닛 속 {idx + 1}번째 봉투."}
    with pytest.raises(RuntimeError, match="noun-fragment flood"):
        validate_korean_script_grammar_integrity(bad_nouns)


# ==============================================================================
# STAGE 2: PLAN CLOSED-LOOP (SENSOR -> SCRIPT DOCTOR CRITIC -> SURGICAL FIXER)
# ==============================================================================


class _MockScriptDoctorGateway:
    supports_critic_loop = True

    def __init__(self, response_payload: dict):
        self.response_payload = response_payload
        self.calls: list[tuple[str, str]] = []

    def run_prompt(self, prompt: str, workspace: Path, label: str, **_kwargs) -> StageResult:
        self.calls.append((label, prompt))
        return StageResult(0, json.dumps(self.response_payload, ensure_ascii=False), workspace / f"{label}.log")


def test_stage2_plan_closed_loop_detects_defects_rebalances_stanzas_and_syncs_manifest(tmp_path: Path):
    stanzas = []
    beats = []
    beat_idx = 1
    for s_idx in range(10):
        lines = []
        for l_idx in range(4):
            if s_idx == 0 and l_idx == 0:
                line = "기묘한 반전으로 기록된 이 중국 실화 사건은 기숙사 복도에서 시작됐습니다."
            elif s_idx == 1 and l_idx == 1:
                line = '남자는 담담하게 "맞소, 그런 일은 처음이오."라고 말했습니다.'
            else:
                line = f"{s_idx + 1}번째 단서를 추적하던 수사팀은 역 광장 폐쇄회로를 확인했습니다."
            lines.append(line)
            beats.append({"beat_id": f"B{beat_idx:03d}", "narration_text": line})
            beat_idx += 1
        stanzas.append("\n".join(lines))

    raw_script = "\n\n".join(stanzas) + "\n"
    (tmp_path / "script.md").write_text(raw_script, encoding="utf-8")
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps({"target_duration_sec": 300, "beats": beats}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    sensor = analyze_script_spoken_quality(
        raw_script,
        language="ko",
        seo_primary_keyword="중국 실화 사건",
    )
    defect_types = {d["type"] for d in sensor["defects"]}
    assert "uniform_paragraph_stanzas" in defect_types
    assert "seo_keyword_stuffed_in_hook" in defect_types
    assert "archaic_haoche_translationese" in defect_types

    rebalanced, changed = rebalance_uniform_paragraph_cadence(raw_script)
    assert changed is True
    assert re.sub(r"\s+", "", rebalanced) == re.sub(r"\s+", "", raw_script)

    mock_gw = _MockScriptDoctorGateway({
        "verdict": "NEEDS_FIX",
        "summary": "Removed stuffed SEO tag in hook and converted archaic 하오체 to modern indirect speech.",
        "line_rewrites": [
            {
                "line": 1,
                "original": "기묘한 반전으로 기록된 이 중국 실화 사건은 기숙사 복도에서 시작됐습니다.",
                "rewrite": "수사 기록에서도 손꼽히는 이 기묘한 비극은 조용한 기숙사 복도에서 시작됐습니다.",
                "reason": "Remove literal SEO tag",
            },
            {
                "line": 6,
                "original": '남자는 담담하게 "맞소, 그런 일은 처음이오."라고 말했습니다.',
                "rewrite": "남자는 수사관 앞에서 자신이 맞다며 그런 일은 처음 겪는다고 짧게 시인했습니다.",
                "reason": "Replace archaic 하오체",
            },
        ],
    })

    job = {
        "id": "job-plan-loop",
        "language": "ko",
        "market": "KR",
        "seo_keyword_dna": {"primary_title_keyword": "중국 실화 사건"},
    }
    report = run_plan_closed_loop(job, tmp_path, mock_gw)
    assert report["paragraph_cadence_rebalanced"] is True
    assert report["total_surgical_rewrites"] == 2
    assert (tmp_path / "plan_critic_report.json").is_file()

    updated_script = (tmp_path / "script.md").read_text(encoding="utf-8")
    assert "이 중국 실화 사건은" not in updated_script
    assert "처음이오" not in updated_script
    updated_mf = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    assert updated_mf["beats"][0]["narration_text"].startswith("수사 기록에서도 손꼽히는")
    assert "짧게 시인했습니다" in updated_mf["beats"][5]["narration_text"]


# ==============================================================================
# STAGE 3: VOICE CLOSED-LOOP (ACOUSTIC + WHISPER ASR LISTEN-BACK -> REROLL)
# ==============================================================================


class _RerollVoiceSession:
    def __init__(self, bad_wav: bytes, good_wav: bytes):
        self.bad_wav = bad_wav
        self.good_wav = good_wav
        self.calls: list[dict] = []

    def post(self, _url: str, json: dict, timeout: int):
        self.calls.append(dict(json))
        seed = json.get("seed")
        # First call for B001 (no explicit retry seed yet) returns defective audio; retry returns clean audio
        is_b001_first_take = len(self.calls) == 1 and seed is None
        wav_payload = self.bad_wav if is_b001_first_take else self.good_wav

        class _Resp:
            def __init__(self, content: bytes, s_val: str):
                self.content = content
                self.headers = {"X-Seed": s_val}

            def raise_for_status(self):
                return None

        return _Resp(wav_payload, str(seed or 500))


def test_stage3_voice_engine_listen_back_sensor_surgically_rerolls_defective_beat(tmp_path: Path):
    b1_text = "On February fourteenth investigators opened the sealed apartment door."
    b2_text = "Inside the hallway every forensic trace pointed to a single suspect."
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps(
            {
                "target_duration_sec": 120,
                "beats": [
                    {"beat_id": "B001", "narration_text": b1_text, "target_duration_sec": 6},
                    {"beat_id": "B002", "narration_text": b2_text, "target_duration_sec": 6},
                ],
            }
        ),
        encoding="utf-8",
    )

    bad_wav = _make_voiced_wav(duration_sec=2.6, internal_silence_sec=0.95)
    good_wav = _make_voiced_wav(duration_sec=3.8, internal_silence_sec=0.0)
    session = _RerollVoiceSession(bad_wav=bad_wav, good_wav=good_wav)

    asr_calls = []

    def fake_asr(wav_path: Path, _lang: str):
        asr_calls.append(wav_path.name)
        if ".qc_cand." not in wav_path.name and len(asr_calls) == 1:
            return {"text": "garbled noise", "words": []}
        txt = b1_text if "B001" in wav_path.name else b2_text
        return {
            "text": txt,
            "words": [
                {"word": "On", "rel_start": 0.05, "rel_end": 0.25},
                {"word": "February", "rel_start": 0.26, "rel_end": 0.75},
            ],
        }

    engine = CofiVoiceEngine(session=session, asr_transcriber=fake_asr, max_qc_retries=2)
    job = {
        "language": "en",
        "channel_profile_id": "channel-kr-truecrime-director-v2",
        "voice": {"speed": 1.0, "mode": "balanced"},
        "production_recipe": normalize_production_recipe(None, target_duration_minutes=2),
    }

    res = engine.run(job, tmp_path)
    assert res.returncode == 0
    # B001 took 1 initial + 1 surgical retry = 2 calls; B002 passed on 1st take = 3 total calls
    assert len(session.calls) == 3

    qc_report = json.loads((tmp_path / "voice_qc_report.json").read_text(encoding="utf-8"))
    assert qc_report["total_beats_inspected"] == 2
    assert qc_report["rerolled_beat_ids"] == ["B001"]
    assert qc_report["passed_beats"] == 2

    vm = json.loads((tmp_path / "voice_manifest.json").read_text(encoding="utf-8"))
    assert vm["beats"][0]["words"][0]["word"] == "On"


# ==============================================================================
# STAGE 4: VISUALS / AI VISUAL / EDIT / SEO / QC SENSORS & CRITICS
# ==============================================================================


def test_stage4_visuals_ai_visual_edit_seo_and_qc_closed_loops(tmp_path: Path):
    import cv2  # type: ignore[import-not-found]

    # 4A. Visuals streak diversification + terse prompt enrichment
    refined = [
        {
            "beat_id": f"B00{i}",
            "narration_text": f"Sentence {i}.",
            "scene_archetype": "ARCHIVAL_DOC",
            "framing_motion_intent": "",
            "prompt": "Short prompt",
            "visual_description": f"Detailed forensic close-up of evidence exhibit {i} under tungsten light",
        }
        for i in range(1, 6)
    ]
    prompt_rows = [{"beat_id": f"B00{i}", "prompt": "Short prompt"} for i in range(1, 6)]
    vis_rep = audit_and_refine_storyboard_sequence(refined, prompt_rows, {}, tmp_path)
    assert vis_rep["diversified_framing_streaks"] >= 2
    assert vis_rep["enriched_terse_prompts"] == 5
    assert "Detailed forensic close-up" in prompt_rows[0]["prompt"]

    # 4B. AI Visual real pixel sensor rejects solid black 128x128 PNG
    blank_png = tmp_path / "blank.png"
    ok_b, buf_b = cv2.imencode(".png", np.zeros((128, 128, 3), dtype=np.uint8))
    assert ok_b
    blank_png.write_bytes(buf_b.tobytes())
    (tmp_path / "ai_visual_manifest.json").write_text(
        json.dumps({"generated": [{"beat_id": "B001", "image_path": "blank.png"}]}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="AI Visual QC Sensor rejected"):
        audit_ai_visual_assets(tmp_path, {})

    # Replace with textured image -> passes cleanly
    grad = np.tile(np.linspace(10, 240, 128, dtype=np.uint8), (128, 1))
    textured = np.stack([grad, np.flipud(grad), grad], axis=-1)
    ok_t, buf_t = cv2.imencode(".png", textured)
    assert ok_t
    blank_png.write_bytes(buf_t.tobytes())
    ai_rep = audit_ai_visual_assets(tmp_path, {})
    assert ai_rep["status"] == "PASSED"

    # 4C. Edit screening sensor catches adjacent asset reuse & bottom subtitle-zone card
    remotion_dir = tmp_path / "remotion"
    (remotion_dir / "src").mkdir(parents=True)
    (remotion_dir / "src" / "JobScene.tsx").write_text(
        '// job-edit-1\nexport const Card = () => <div style={{ position: "absolute", top: 910 }}>Info</div>;\n',
        encoding="utf-8",
    )
    (tmp_path / "edit_manifest.json").write_text(
        json.dumps({"beats": [{"beat_id": "B001", "asset_id": "A1"}, {"beat_id": "B002", "asset_id": "A1"}]}),
        encoding="utf-8",
    )
    edit_rep = audit_edit_timeline_and_screen({"id": "job-edit-1"}, tmp_path, remotion_dir, refined[:2])
    issue_types = {x["type"] for x in edit_rep["issues"]}
    assert "adjacent_asset_reuse" in issue_types
    assert "vox_subtitle_safe_zone_warning" in issue_types

    # 4D. SEO 320x180 mobile preview + verbatim title/overlay overlap auto-fix
    thumbs = tmp_path / "thumbnails"
    thumbs.mkdir()
    hi_contrast = np.zeros((720, 1280, 3), dtype=np.uint8)
    hi_contrast[:, 640:] = 245
    cv2.putText(hi_contrast, "EVIDENCE", (80, 360), cv2.FONT_HERSHEY_SIMPLEX, 4.0, (0, 220, 255), 10)
    ok_th, buf_th = cv2.imencode(".jpg", hi_contrast)
    assert ok_th
    (thumbs / "variant_a.jpg").write_bytes(buf_th.tobytes())

    seo_pack = {
        "recommended_title": "[중국 실화 사건] 기숙사 벽장 속 4개의 상자",
        "thumbnail": {
            "overlay_text": "기숙사 벽장 속 4개의 상자",
            "prompt": 'Investigative portrait with bold text "기숙사 벽장 속 4개의 상자"',
            "overlay_text_options": [
                {"line_1": "열리지 않던 벽장", "line_2": "단 한 장의 열차표"},
            ],
        },
    }
    seo_rep = audit_seo_and_mobile_thumbnail(tmp_path, {}, seo_pack)
    assert "auto_replaced_overlapping_overlay_text_from_options" in seo_rep["issues"]
    assert seo_pack["thumbnail"]["overlay_text"] == "열리지 않던 벽장 단 한 장의 열차표"
    assert "열리지 않던 벽장 단 한 장의 열차표" in seo_pack["thumbnail"]["prompt"]
    assert seo_rep["mobile_320x180"]["generated"] is True
    assert (thumbs / "mobile_preview_320x180.jpg").is_file()

    # 4E. QC Master Screening rejects clipped final narration and accepts full tail
    dummy_mp4 = tmp_path / "final.mp4"
    dummy_mp4.write_bytes(b"0" * 4096)
    (tmp_path / "voice_manifest.json").write_text(
        json.dumps({"beats": [{"beat_id": "B010", "speech_end_sec": 58.5, "end_sec": 62.3}]}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="QC Outro Completeness Sensor failed"):
        run_qc_master_screening(
            dummy_mp4,
            {"duration_seconds": 56.0, "audio_duration_seconds": 56.0, "has_audio": False},
            {},
            tmp_path,
            {},
        )

    qc_ok = run_qc_master_screening(
        dummy_mp4,
        {"duration_seconds": 62.3, "audio_duration_seconds": 62.3, "has_audio": False},
        {},
        tmp_path,
        {},
    )
    assert qc_ok["outro_completeness"]["closing_speech_unclipped"] is True
    assert (tmp_path / "qc_screening_report.json").is_file()


# ==============================================================================
# STAGE 5: ARCHITECTURAL SEPARATION — APP CORE VS. ISOLATED CHANNEL/COUNTRY DNA
# ==============================================================================


def test_stage5_custom_korean_haeyo_and_pastoral_profiles_isolated_from_true_crime_and_china_rules(tmp_path: Path):
    from documentary.critic_loops import _build_script_doctor_critic_prompt
    from documentary.quality import validate_phase_quality

    # 1. Verify Grace Letter profile on disk has zero motel-murder / True Crime contamination
    profiles_data = json.loads((ROOT / "data" / "channel_profiles.json").read_text(encoding="utf-8"))
    grace_prof = next(p for p in profiles_data["profiles"] if p["id"] == "channel-kr-grace-letter-60m")
    grace_serialized = json.dumps(grace_prof, ensure_ascii=False)
    for leaked_term in ("여관 주인 부부", "Ngụy", "특급수배록", "저우커화"):
        assert leaked_term not in grace_serialized, f"Leaked crime term '{leaked_term}' in grace-letter profile"

    # 2. Brand-new Korean creative essay / Hanok architecture profile using 해요체 (zero China, zero crime)
    custom_ko_job = {
        "id": "job-custom-healing-hanok-01",
        "channel_profile_id": "channel-custom-healing-kr",
        "title": "비 오는 날 한옥 처마 밑에서 듣는 나무의 시간",
        "topic": "한국 전통 목조 한옥과 다도 에세이",
        "language": "ko",
        "market": "KR",
        "speech_register": "haeyo",
        "production_recipe": normalize_production_recipe(None, target_duration_minutes=4),
        "channel_profile_snapshot": {
            "id": "channel-custom-healing-kr",
            "label": "고요한 한옥 산책",
            "language": "ko",
            "market": "KR",
            "voice_and_structure": "따뜻하고 나직한 해요체 에세이 내레이션으로 공간과 계절의 숨결을 전합니다.",
            "editorial_dna": {
                "speech_register": "haeyo",
                "narrative_genre": "poetic_essay",
            },
            "seo_keyword_dna": {
                "primary_title_keyword": "한옥 에세이",
                "keyword_placement_rule": "smart_seo_flexible",
            },
            "thumbnail_dna": {
                "badge_text_default": "공간 사색",
            },
        },
        "creative_brief": {
            "speech_register": "haeyo",
            "writing_style": "poetic_essay",
        },
    }

    plan_prompt = build_phase_prompt(custom_ko_job, "plan", tmp_path / "ws_healing", tmp_path / "remotion")
    seo_prompt = build_phase_prompt(custom_ko_job, "seo", tmp_path / "ws_healing", tmp_path / "remotion")

    for forbidden_cross_channel in (
        "특급수배록",
        "판세의이면",
        "teukgeup_detective_reference",
        "저우커화",
        "천 씨",
        "왕 씨",
        "여관 주인 부부",
        "20261030-081721-2a473306",
    ):
        assert forbidden_cross_channel not in plan_prompt, f"Leaked '{forbidden_cross_channel}' into custom KR PLAN prompt"
        assert forbidden_cross_channel not in seo_prompt, f"Leaked '{forbidden_cross_channel}' into custom KR SEO prompt"

    assert "채널 프로필 고유 화법·어미 100% 자율 존중" in plan_prompt
    assert "공간 사색" in seo_prompt

    # 3. 42-sentence Korean 해요체 script (0% '~습니다') MUST pass technical & prosody validation!
    haeyo_beats = []
    haeyo_lines = []
    for i in range(1, 43):
        if i % 6 == 0:
            line = "처마 끝에 빗방울이 맺혀요."
        elif i % 4 == 0:
            line = f"{i}번째 마루 결마다 오래된 소나무 향기가 조용히 배어 나오죠."
        else:
            line = f"비 개인 아침이면 열린 창호 사이로 맑은 바람이 천천히 스며들어요."
        haeyo_beats.append({"beat_id": f"B{i:03d}", "narration_text": line})
        haeyo_lines.append(line)

    ws_haeyo = tmp_path / "ws_haeyo_gate"
    ws_haeyo.mkdir(parents=True, exist_ok=True)
    (ws_haeyo / "visual_manifest.json").write_text(
        json.dumps({"target_duration_sec": 480, "beats": haeyo_beats}, ensure_ascii=False),
        encoding="utf-8",
    )
    validate_korean_script_grammar_integrity(haeyo_beats, job=custom_ko_job)
    validate_phase_quality("plan", ws_haeyo, custom_ko_job)

    haeyo_script = "\n\n".join(
        ["\n".join(haeyo_lines[0:2]), "\n".join(haeyo_lines[2:7]), "\n".join(haeyo_lines[7:10])]
        + ["\n".join(haeyo_lines[10:15]), "\n".join(haeyo_lines[15:18]), "\n".join(haeyo_lines[18:24])]
        + ["\n".join(haeyo_lines[24:26]), "\n".join(haeyo_lines[26:32]), "\n".join(haeyo_lines[32:37]), "\n".join(haeyo_lines[37:42])]
    )
    spoken_rep = analyze_script_spoken_quality(
        haeyo_script,
        language="ko",
        seo_primary_keyword="한옥 에세이",
        job=custom_ko_job,
    )
    assert spoken_rep["metrics"]["formal_seumnida_ratio"] == 0.0
    assert spoken_rep["status"] == "PASS"
    assert spoken_rep["defects"] == []

    # Technical TTS raw '%' symbol rule MUST still protect custom profiles!
    bad_pct_beats = [dict(b) for b in haeyo_beats]
    bad_pct_beats[3] = {"beat_id": "B004", "narration_text": "습도가 85%를 넘어가면 대청마루 나무 결이 숨을 쉬어요."}
    with pytest.raises(RuntimeError, match="퍼센트"):
        validate_korean_script_grammar_integrity(bad_pct_beats, job=custom_ko_job)

    # 4. Script Doctor Critic adopts custom profile DNA instead of hardcoded SBS crime persona
    critic_prompt = _build_script_doctor_critic_prompt(
        haeyo_script,
        spoken_rep,
        language="ko",
        market="KR",
        seo_primary_keyword="한옥 에세이",
        job=custom_ko_job,
    )
    assert "고요한 한옥 산책" in critic_prompt
    assert "SBS 그것이 알고 싶다" not in critic_prompt


def test_stage5_cross_country_workspace_ngram_thumbnail_and_self_learning_isolation(tmp_path: Path):
    import shutil
    from documentary.quality import validate_korean_anti_template_diversity
    from documentary.thumbnail_studio import _extract_overlay_options
    from services.self_learning_service import SelfLearningService

    # 1. Cross-workspace N-gram scan strictly isolates channel_profile_id
    fake_ws_root = tmp_path / "workspaces"
    ep_alpha_1 = fake_ws_root / "20261030-010000-alpha1"
    ep_alpha_2 = fake_ws_root / "20261030-020000-alpha2"
    ep_beta_1 = fake_ws_root / "20261030-030000-beta1"
    for p in (ep_alpha_1, ep_alpha_2, ep_beta_1):
        p.mkdir(parents=True, exist_ok=True)

    shared_8gram = "오래된 소나무 기둥 사이로 새벽 안개가 조용히 내려앉고 있었습니다."
    alpha_script = "\n".join(
        [shared_8gram]
        + [f"산사의 {i}번째 풍경 소리가 바람을 타고 은은하게 번져 나갔습니다." for i in range(1, 14)]
    )
    (ep_alpha_1 / "input.json").write_text(json.dumps({"channel_profile_id": "channel-alpha-kr"}), encoding="utf-8")
    (ep_alpha_1 / "script.md").write_text(alpha_script, encoding="utf-8")

    candidate_beats = [
        {"beat_id": "B001", "narration_text": shared_8gram},
        *[
            {"beat_id": f"B{i + 1:03d}", "narration_text": f"정원의 {i}번째 돌계단 위로 가을 낙엽이 차분하게 쌓여 갔습니다."}
            for i in range(1, 15)
        ],
    ]

    # Same channel ('channel-alpha-kr') -> MUST block 6-gram / 8-gram self-plagiarism from ep_alpha_1
    with pytest.raises(RuntimeError, match="6-grams|8-gram"):
        validate_korean_anti_template_diversity(
            candidate_beats,
            workspace=ep_alpha_2,
            job={"channel_profile_id": "channel-alpha-kr", "language": "ko"},
        )

    # Different channel ('channel-beta-kr') -> MUST NOT leak or block against channel-alpha-kr's workspace!
    res_beta = validate_korean_anti_template_diversity(
        candidate_beats,
        workspace=ep_beta_1,
        job={"channel_profile_id": "channel-beta-kr", "language": "ko"},
    )
    assert res_beta["status"] == "PASSED"

    # 2. Thumbnail default badge never leaks '중국 실화 사건' onto non-Chinese KR / US / VN profiles
    for lang, expected_badge in (("ko", "다큐멘터리"), ("en", "DOCUMENTARY"), ("vi", "PHÓNG SỰ")):
        opts = _extract_overlay_options(
            {"thumbnail": {}},
            {"id": f"job-{lang}", "language": lang, "channel_profile_id": f"channel-custom-{lang}"},
        )
        assert len(opts) >= 1
        assert opts[0]["badge"] == expected_badge
        assert "중국 실화 사건" not in json.dumps(opts, ensure_ascii=False)

    # 3. Vox engine seal stamp is neutral (zero '특급수배록분석')
    arch_src = (ROOT / "documentary" / "vox_engine" / "archetypes.py").read_text(encoding="utf-8")
    assert "특급수배록" not in arch_src

    # 4. SelfLearningService keeps US/EN Hangul-free and non-crime profiles free of motel-murder leaks
    temp_profiles = tmp_path / "isolated_profiles.json"
    shutil.copy2(ROOT / "data" / "channel_profiles.json", temp_profiles)
    sl_svc = SelfLearningService(profiles_file=temp_profiles)
    raw_profiles = json.loads(temp_profiles.read_text(encoding="utf-8"))["profiles"]
    us_prof = next(p for p in raw_profiles if p["id"] == "channel-f6ec4dfff3")
    grace_prof_2 = next(p for p in raw_profiles if p["id"] == "channel-kr-grace-letter-60m")
    sample_videos = [
        {"id": "v1", "title": "Breakout Episode 1", "views": 180000, "is_breakout": True},
        {"id": "v2", "title": "Underperforming Episode 2", "views": 3200, "is_breakout": False},
    ]

    us_pm = sl_svc.analyze_post_mortem(sample_videos, us_prof)
    us_dump = json.dumps(us_pm, ensure_ascii=False)
    assert not re.search(r"[\uac00-\ud7a3]", us_dump)
    assert "여관 주인 부부" not in us_dump

    grace_pm = sl_svc.analyze_post_mortem(sample_videos, grace_prof_2)
    grace_dump = json.dumps(grace_pm, ensure_ascii=False)
    assert "여관 주인 부부" not in grace_dump
    assert "Ngụy" not in grace_dump
    assert "특급수배록" not in grace_dump

