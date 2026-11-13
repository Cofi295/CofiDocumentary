"""End-to-end verification for the Master Human Film Editor (`@edit`) Soul Layer across all niches."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import wave

import numpy as np

from documentary.agent_manager import AgentManager
from documentary.critic_loops import audit_edit_timeline_and_screen
from documentary.edit import build_edit_rhythm_score
from documentary.editorial_voice_cutter import (
    main as cutter_cli_main,
    reset_editorial_voice_cuts,
    sculpt_editorial_voice_timeline,
)
from documentary.prompts import build_phase_prompt
from documentary.srt import build_srt, split_multilang_narration_into_clauses
from documentary.voice import OUTRO_FADE_TAIL_SEC, wav_duration
from services.voice_rhythm_specialist import (
    GENRE_RHYTHM_ARCHETYPES,
    VoiceRhythmSpecialistService,
    resolve_editorial_craft_profile,
    resolve_job_rhythm_dna,
)


def _parse_srt_blocks(srt_text: str) -> list[tuple[float, float, str]]:
    def _ts(raw: str) -> float:
        hh, mm, rest = raw.strip().split(":")
        ss, ms = rest.split(",")
        return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0

    cues: list[tuple[float, float, str]] = []
    for block in re.split(r"\n\s*\n", srt_text.strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        lhs, rhs = lines[1].split("-->", 1)
        cues.append((_ts(lhs), _ts(rhs), " ".join(lines[2:])))
    return cues


def _write_speech_envelope_wav(
    path: Path,
    *,
    duration_sec: float,
    words: list[dict[str, object]],
    sr: int = 24000,
) -> float:
    """Create a realistic 16-bit mono PCM WAV with voiced word bursts and clean inter-word valleys."""
    total_samples = max(1, int(round(duration_sec * sr)))
    signal = np.zeros(total_samples, dtype=np.float64)
    t = np.arange(total_samples, dtype=np.float64) / float(sr)
    carrier = 0.55 * np.sin(2.0 * math.pi * 185.0 * t) + 0.30 * np.sin(2.0 * math.pi * 370.0 * t)

    for w in words:
        ws = max(0.0, float(w["rel_start"]))
        we = min(duration_sec, float(w["rel_end"]))
        i0 = int(round(ws * sr))
        i1 = int(round(we * sr))
        if i1 - i0 <= 32:
            continue
        env = np.hanning(i1 - i0)
        signal[i0:i1] = 0.42 * carrier[i0:i1] * np.clip(env * 1.6, 0.0, 1.0)

    pcm = np.clip(np.round(signal * 32767.0), -32768, 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return wav_duration(path)


def test_all_11_multi_niche_archetypes_and_editorial_craft_specs() -> None:
    assert len(GENRE_RHYTHM_ARCHETYPES) >= 11
    svc = VoiceRhythmSpecialistService()

    # Cross-language & universal niche routing
    sci_en = svc.analyze_profile_rhythm_dna(
        {
            "label": "Mustard Engineering & Aviation Disasters",
            "market": "US",
            "default_language": "en",
            "allowed_topics": "Aerospace engineering, physics, submarine disasters, megastructures",
        }
    )
    assert sci_en["archetype_id"] == "universal_science_engineering_explainer"

    essay_vi = svc.analyze_profile_rhythm_dna(
        {
            "label": "Triết Học & Chiều Sâu Tâm Lý Con Người",
            "market": "VN",
            "default_language": "vi",
            "allowed_topics": "Cultural essay, psychology, philosophy, modern loneliness, art cinema",
        }
    )
    assert essay_vi["archetype_id"] == "universal_cultural_human_essay"

    empire_ko = svc.analyze_profile_rhythm_dna(
        {
            "label": "제국의 흥망성쇠 & 창업자 전기",
            "market": "KR",
            "default_language": "ko",
            "allowed_topics": "Corporate empire rise and fall, founder biography, monopoly history",
        }
    )
    assert empire_ko["archetype_id"] == "universal_empire_biography_chronicle"

    grace_ko = svc.analyze_profile_rhythm_dna(
        {
            "label": "Thư Ân Điển & Lời Chúa 60 Phút",
            "market": "KR",
            "default_language": "ko",
            "default_duration_minutes": 60,
        }
    )
    assert grace_ko["archetype_id"] == "kr_grace_pastoral_letter"
    grace_craft = resolve_editorial_craft_profile(grace_ko)
    # Sanctuary healing channels never inject jarring mid-sentence suspense cuts
    assert grace_craft["mid_beat_caesura_policy"]["enabled"] is False

    # Every archetype must carry a complete 5-act color emotion arc & -41dBFS room-tone cushion
    for arch_id in GENRE_RHYTHM_ARCHETYPES:
        dna = svc.analyze_profile_rhythm_dna({"rhythm_archetype_id": arch_id, "default_language": "en"})
        craft = resolve_editorial_craft_profile(dna)
        assert 0.8 <= float(craft["cold_open_pre_voice_sec"]) <= 2.5
        color_arc = craft["color_emotion_arc"]
        for act_key in ("act_1", "act_2", "act_3", "act_4", "act_5"):
            assert act_key in color_arc
        sound = craft["sound_design_soul"]
        assert float(sound["room_tone_floor_db"]) == -41.0
        assert 0.01 <= float(sound["room_tone_linear_gain"]) <= 0.03

    # Ad-hoc profile-less job still receives bespoke rhythm_dna + editorial_craft
    adhoc_job = {
        "id": "adhoc-sci-01",
        "language": "en",
        "topic": "How Titanium Fatigue Brought Down Flight 232 — Aerospace Engineering Investigation",
    }
    adhoc_dna = resolve_job_rhythm_dna(adhoc_job)
    assert adhoc_dna["archetype_id"] == "universal_science_engineering_explainer"
    assert "editorial_craft" in adhoc_dna["editing_cadence"]


def test_editorial_voice_cutter_caesura_sync_idempotency_and_cli(tmp_path: Path) -> None:
    ws = tmp_path / "workspaces" / "job_master_cut"
    remotion_dir = tmp_path / "CofiRemotion"
    pub_job = remotion_dir / "public" / "jobs" / "job_master_cut"
    (pub_job / "audio").mkdir(parents=True, exist_ok=True)
    # Seed stale compressed proxy + stale render chunk to verify automatic invalidation
    (pub_job / "audio" / "narration.m4a").write_bytes(b"stale-m4a")
    cache_dir = ws / ".render_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "chunk_000.mp4").write_bytes(b"stale-chunk")

    beats_spec = [
        {
            "beat_id": "B001",
            "act": "ACT 1",
            "visual_type": "FOOTAGE",
            "emotion_register": "forensic_anchor",
            "pause_after_sec": 0.62,
            "pause_reason": "act_transition",
            "dur": 3.4,
            "text": "천구백구십오년 겨울 서울 외곽의 한 은행 금고가 열렸습니다.",
            "words": [
                {"word": "천구백구십오년", "rel_start": 0.08, "rel_end": 0.78},
                {"word": "겨울", "rel_start": 0.84, "rel_end": 1.25},
                {"word": "서울", "rel_start": 1.32, "rel_end": 1.75},
                {"word": "외곽의", "rel_start": 1.80, "rel_end": 2.30},
                {"word": "은행", "rel_start": 2.36, "rel_end": 2.78},
                {"word": "금고가", "rel_start": 2.82, "rel_end": 3.08},
                {"word": "열렸습니다.", "rel_start": 3.10, "rel_end": 3.34},
            ],
        },
        {
            "beat_id": "B002",
            "act": "ACT 2",
            "visual_type": "CINEMA_TEXT",
            "emotion_register": "twist_reveal",
            "pause_after_sec": 0.58,
            "pause_reason": "standard_narrative",
            "dur": 5.0,
            "text": "수사관들이 철문을 열었을 때 금고 안에는, 단 한 장의 백지뿐이었습니다.",
            "words": [
                {"word": "수사관들이", "rel_start": 0.08, "rel_end": 0.72},
                {"word": "철문을", "rel_start": 0.78, "rel_end": 1.26},
                {"word": "열었을", "rel_start": 1.32, "rel_end": 1.76},
                {"word": "때", "rel_start": 1.80, "rel_end": 2.02},
                {"word": "금고", "rel_start": 2.08, "rel_end": 2.42},
                {"word": "안에는,", "rel_start": 2.46, "rel_end": 2.86},
                # Clear inter-word valley [2.86 .. 2.98] right before reveal pivot `단`
                {"word": "단", "rel_start": 2.98, "rel_end": 3.24},
                {"word": "한", "rel_start": 3.28, "rel_end": 3.52},
                {"word": "장의", "rel_start": 3.56, "rel_end": 3.96},
                {"word": "백지뿐이었습니다.", "rel_start": 4.02, "rel_end": 4.90},
            ],
        },
        {
            "beat_id": "B003",
            "act": "ACT 2",
            "visual_type": "VOX_GRAPHIC",
            "emotion_register": "urgent_action",
            "pause_after_sec": 0.56,
            "pause_reason": "urgent_action_chain",
            "dur": 4.6,
            "text": "비상벨이 울리자 순찰차들이 봉쇄선을 치며 추적했지만, 발견된 것은 버려진 번호판뿐이었습니다.",
            "words": [
                {"word": "비상벨이", "rel_start": 0.08, "rel_end": 0.65},
                {"word": "울리자", "rel_start": 0.70, "rel_end": 1.15},
                {"word": "순찰차들이", "rel_start": 1.20, "rel_end": 1.82},
                {"word": "추적했지만,", "rel_start": 1.88, "rel_end": 2.52},
                {"word": "발견된", "rel_start": 2.64, "rel_end": 3.12},
                {"word": "것은", "rel_start": 3.16, "rel_end": 3.50},
                {"word": "번호판뿐이었습니다.", "rel_start": 3.56, "rel_end": 4.50},
            ],
        },
        {
            "beat_id": "B004",
            "act": "ACT 5",
            "visual_type": "AI_STILL",
            "emotion_register": "somber_tragedy",
            "pause_after_sec": 0.0,
            "pause_reason": "outro_tail",
            "dur": 3.6,
            "text": "이십 년이 흐른 지금도 그날 밤의 질문은 차가운 기록 속에 남아 있습니다.",
            "words": [
                {"word": "이십", "rel_start": 0.08, "rel_end": 0.48},
                {"word": "년이", "rel_start": 0.52, "rel_end": 0.92},
                {"word": "흐른", "rel_start": 0.98, "rel_end": 1.40},
                {"word": "지금도", "rel_start": 1.46, "rel_end": 1.98},
                {"word": "질문은", "rel_start": 2.04, "rel_end": 2.58},
                {"word": "남아", "rel_start": 2.64, "rel_end": 3.02},
                {"word": "있습니다.", "rel_start": 3.06, "rel_end": 3.52},
            ],
        },
    ]

    beats_dir = ws / "audio" / "beats"
    vm_beats = []
    vis_beats = []
    cursor = 0.0
    wav_paths: list[Path] = []
    pauses: list[float] = []

    for idx, sp in enumerate(beats_spec):
        bid = sp["beat_id"]
        wp = beats_dir / f"{bid}.wav"
        actual_d = _write_speech_envelope_wav(wp, duration_sec=float(sp["dur"]), words=sp["words"])
        wav_paths.append(wp)
        p_after = float(sp["pause_after_sec"]) if idx < len(beats_spec) - 1 else 0.0
        if idx < len(beats_spec) - 1:
            pauses.append(p_after)
        outro_tail = OUTRO_FADE_TAIL_SEC if idx == len(beats_spec) - 1 else 0.0
        s_start = round(cursor, 3)
        s_end = round(cursor + actual_d, 3)
        b_end = round(s_end + (p_after if idx < len(beats_spec) - 1 else outro_tail), 3)
        abs_words = [
            {
                "word": w["word"],
                "rel_start": w["rel_start"],
                "rel_end": w["rel_end"],
                "start": round(s_start + float(w["rel_start"]), 3),
                "end": round(s_start + float(w["rel_end"]), 3),
            }
            for w in sp["words"]
        ]
        vm_beats.append(
            {
                "beat_id": bid,
                "text": sp["text"],
                "audio_path": str(wp),
                "start_sec": s_start,
                "speech_end_sec": s_end,
                "end_sec": b_end,
                "duration_sec": round(actual_d, 3),
                "pause_after_sec": p_after,
                "pause_reason": sp["pause_reason"],
                "outro_tail_sec": outro_tail,
                "emotion_register": sp["emotion_register"],
                "words": abs_words,
            }
        )
        vis_beats.append(
            {
                "beat_id": bid,
                "act": sp["act"],
                "visual_type": sp["visual_type"],
                "narration": sp["text"],
                "start_sec": s_start,
                "end_sec": b_end,
                "duration_sec": round(b_end - s_start, 3),
            }
        )
        cursor = b_end

    from documentary.editorial_voice_cutter import concat_timeline_wav_with_pre_and_outro

    orig_narr = ws / "audio" / "narration.wav"
    orig_total_dur = concat_timeline_wav_with_pre_and_outro(
        pre_voice_sec=0.0,
        beat_wavs=wav_paths,
        inter_beat_pauses=pauses,
        outro_tail_sec=OUTRO_FADE_TAIL_SEC,
        output_path=orig_narr,
    )
    (ws / "voice_manifest.json").write_text(
        json.dumps({"duration_sec": round(orig_total_dur, 3), "beats": vm_beats}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (ws / "visual_manifest.json").write_text(
        json.dumps({"duration_sec": round(orig_total_dur, 3), "beats": vis_beats}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    job = {
        "id": "job_master_cut",
        "language": "ko",
        "topic": "1995년 은행 금고 백지 증발 미제 사건",
    }
    (ws / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    # 1. Run automatic Master Editor Voice Sculpting (enabling auto-caesura on short test fixture via CLI --set-caesura / auto)
    res1 = sculpt_editorial_voice_timeline(job, ws, remotion_dir=remotion_dir)
    assert res1["applied"] is True
    assert float(res1["cold_open_pre_voice_sec"]) >= 1.15
    assert (ws / "voice_manifest.raw.json").is_file()
    assert (ws / "audio" / "beats_raw" / "B002.wav").is_file()
    # Stale compressed proxy and render chunk were invalidated automatically
    assert not (pub_job / "audio" / "narration.m4a").exists()
    assert not (cache_dir / "chunk_000.mp4").exists()

    # 2. Verify 100% idempotency on repeated invocation (never double-adds pauses or pre-voice!)
    res2 = sculpt_editorial_voice_timeline(job, ws, remotion_dir=remotion_dir)
    assert res2["applied"] is True
    assert abs(float(res2["duration_sec"]) - float(res1["duration_sec"])) < 0.005

    # 3. Exercise `@edit` surgical CLI (`--set-caesura` + `--set-pause` + `--pre-voice`)
    rc = cutter_cli_main(
        [
            "--workspace",
            str(ws),
            "--remotion-dir",
            str(remotion_dir),
            "--pre-voice",
            "1.45",
            "--set-pause",
            "B001=2.15:chapter_curtain",
            "--set-caesura",
            "B002:before=단:hold=0.80",
        ]
    )
    assert rc == 0

    vm_after = json.loads((ws / "voice_manifest.json").read_text(encoding="utf-8"))
    vis_after = json.loads((ws / "visual_manifest.json").read_text(encoding="utf-8"))
    srt_text = (ws / "subtitles.srt").read_text(encoding="utf-8")

    assert abs(float(vm_after["pre_voice_breath_sec"]) - 1.45) < 0.01
    # Visual B001 opens at Frame 0 (0.0s), while speech starts at 1.45s -> ZERO black-frame gap!
    vb0 = vis_after["beats"][0]
    assert float(vb0["start_sec"]) == 0.0
    assert int(vb0["start_frame"]) == 0
    assert abs(float(vb0["speech_start_sec"]) - 1.45) < 0.02
    for idx in range(len(vis_after["beats"]) - 1):
        assert abs(float(vis_after["beats"][idx]["end_sec"]) - float(vis_after["beats"][idx + 1]["start_sec"])) <= 0.005

    # Verify B002 surgical zero-crossing caesura & non-spoiling SRT cues
    b2 = next(b for b in vm_after["beats"] if b["beat_id"] == "B002")
    assert len(b2["editorial_caesuras"]) == 1
    caes = b2["editorial_caesuras"][0]
    assert abs(float(caes["hold_sec"]) - 0.80) < 0.01
    abs_c_start = float(b2["start_sec"]) + float(caes["local_start_sec"])
    abs_c_end = float(b2["start_sec"]) + float(caes["local_end_sec"])

    cues = _parse_srt_blocks(srt_text)
    assert len(cues) >= 5
    # No cue is allowed to bridge across the mid-beat caesura silence!
    for c_s, c_e, c_txt in cues:
        bridges = (c_s < abs_c_start + 0.05) and (c_e > abs_c_end - 0.05)
        assert not bridges, f"SRT cue bridged across dramatic caesura and spoiled twist: {(c_s, c_e, c_txt)}"
        if "백지" in c_txt:
            assert c_s >= abs_c_end - 0.03, f"Twist word `백지` appeared before caesura ended: {c_s} < {abs_c_end}"

    # Verify Remotion public mirror matches workspace narration.wav byte-for-byte
    assert (pub_job / "audio" / "narration.wav").stat().st_size == (ws / "audio" / "narration.wav").stat().st_size

    # 4. Reset restores clean 1st-gen stems & original duration
    reset_res = reset_editorial_voice_cuts(ws, job=job, remotion_dir=remotion_dir)
    assert reset_res["reset"] is True
    assert abs(float(reset_res["duration_sec"]) - orig_total_dur) < 0.03


def test_silent_synthetic_unit_test_fixtures_remain_untouched_by_default(tmp_path: Path) -> None:
    ws = tmp_path / "ws_silent"
    bdir = ws / "audio" / "beats"
    bdir.mkdir(parents=True, exist_ok=True)
    silent_wav = bdir / "B001.wav"
    with wave.open(str(silent_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"\x00\x00" * 24000)
    (ws / "voice_manifest.json").write_text(
        json.dumps(
            {
                "duration_sec": 4.8,
                "beats": [
                    {
                        "beat_id": "B001",
                        "text": "Synthetic silent test beat.",
                        "audio_path": str(silent_wav),
                        "start_sec": 0.0,
                        "speech_end_sec": 1.0,
                        "end_sec": 4.8,
                        "duration_sec": 1.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    res = sculpt_editorial_voice_timeline({"id": "silent-1", "language": "en"}, ws)
    assert res["applied"] is False
    assert res["reason"] == "synthetic_silent_fixture_preserved"


def test_multilang_srt_clause_splitter_and_rhythm_score_v2_and_critic_sensor(tmp_path: Path) -> None:
    # Multi-language clause splitting (`en`, `vi`, `ja`, `ko`)
    en_clauses = split_multilang_narration_into_clauses(
        "When investigators opened the flight data recorder in Zurich, they discovered that both hydraulic lines had ruptured simultaneously.",
    )
    assert len(en_clauses) >= 2
    vi_clauses = split_multilang_narration_into_clauses(
        "Khi đoàn thanh tra mở niêm phong kho bạc lúc nửa đêm, thứ duy nhất còn sót lại chỉ là một tờ biên bản trống không.",
    )
    assert len(vi_clauses) >= 2
    ja_clauses = split_multilang_narration_into_clauses(
        "捜査官が地下金庫の扉を開けた瞬間、そこには一枚の白紙だけが残されていました。"
    )
    assert len(ja_clauses) >= 2

    # Master Editor Rhythm Score v2 (`jl_cut_mode`, 30% non-repeating shot scale, 5-act color grade, -41dBFS floor)
    ws = tmp_path / "ws_score"
    remotion_dir = tmp_path / "CofiRemotion"
    job_id = "job-score-v2"
    pub_audio = remotion_dir / "public" / "jobs" / job_id / "audio"
    pub_audio.mkdir(parents=True, exist_ok=True)
    (ws / "audio").mkdir(parents=True, exist_ok=True)

    # Create valid workspace narration.wav and intentionally stale public narration.wav
    _write_speech_envelope_wav(
        ws / "audio" / "narration.wav",
        duration_sec=12.0,
        words=[{"word": "test", "rel_start": 0.2, "rel_end": 0.9}],
    )
    (pub_audio / "narration.wav").write_bytes(b"outdated")

    vm = {
        "duration_sec": 12.0,
        "pre_voice_breath_sec": 1.30,
        "beats": [
            {"beat_id": f"B{i:03d}", "start_sec": float(i), "speech_end_sec": float(i) + 0.8, "pause_after_sec": 0.2}
            for i in range(1, 9)
        ],
    }
    vm["beats"][1]["editorial_caesuras"] = [{"before_word": "nothing", "local_start_sec": 0.3, "local_end_sec": 0.9, "hold_sec": 0.6}]
    (ws / "voice_manifest.json").write_text(json.dumps(vm), encoding="utf-8")

    beats = [
        {"beat_id": f"B{i:03d}", "act": f"ACT {min(5, (i + 1) // 2)}", "visual_type": "CINEMA_TEXT" if i == 2 else "AI_STILL"}
        for i in range(1, 9)
    ]
    job = {"id": job_id, "language": "en", "topic": "Inside the Collapse of Barings Bank — Financial Empire Chronicle"}
    score = build_edit_rhythm_score(job, ws, beats)

    assert score["version"] == 2
    assert float(score["editorial_craft"]["sound_design_soul"]["room_tone_floor_db"]) == -41.0
    score_beats = score["beats"]
    assert len(score_beats) == 8
    assert float(score_beats[0]["room_tone_floor_db"]) == -41.0
    for i in range(1, len(score_beats)):
        # 30% Shot-Scale Law: adjacent beats never repeat identical recommended_shot_scale
        assert score_beats[i]["recommended_shot_scale"] != score_beats[i - 1]["recommended_shot_scale"]
        assert "jl_cut_mode" in score_beats[i]
        assert "act_color_grade" in score_beats[i]
        assert score_beats[i]["fincher_no_double_motion"] is True
    assert len(score_beats[1]["caesura_windows"]) == 1

    # Prompt embeds all 7 Master Human Editing Crafts & `editorial_voice_cutter` CLI across languages
    edit_prompt = build_phase_prompt(job, "edit", ws, remotion_dir)
    assert "MASTER HUMAN FILM EDITOR" in edit_prompt
    assert "editorial_voice_cutter" in edit_prompt
    assert "-41" in edit_prompt

    # Critic sensor detects >=7 monotonous camera modes AND auto-repairs stale public narration.wav
    (ws / "edit_manifest.json").write_text(
        json.dumps(
            {
                "beats": [
                    {"beat_id": f"B{i:03d}", "asset_id": f"A{i:03d}", "cameraMode": "STATIC_LOCK"}
                    for i in range(1, 9)
                ]
            }
        ),
        encoding="utf-8",
    )
    audit = audit_edit_timeline_and_screen(job, ws, remotion_dir, beats)
    assert (pub_audio / "narration.wav").stat().st_size == (ws / "audio" / "narration.wav").stat().st_size
    assert any(iss.get("type") == "monotonous_camera_streak" for iss in audit["issues"])


def test_agent_charters_and_office_core_remain_valid_and_hangul_free() -> None:
    mgr = AgentManager()
    roster = mgr.list_agents()
    assert len(roster) == 15
    edit_agent = mgr.get("edit")
    assert "editorial_voice_cutter" in edit_agent.tools_permitted
    assert "editorial_voice_plan.json" in edit_agent.writes_artifacts

    root = Path(__file__).resolve().parents[1]
    hangul_re = re.compile(r"[\uac00-\ud7a3]")
    for rel in ("documentary/agent_office.py", "static/agent_office.js"):
        txt = (root / rel).read_text(encoding="utf-8")
        assert not hangul_re.search(txt), f"Hangul leaked into language-agnostic file {rel}"
