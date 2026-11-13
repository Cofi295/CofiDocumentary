from __future__ import annotations

import inspect
import json
from pathlib import Path
import shutil
import subprocess
import wave

import pytest

from documentary.audio_library_manager import (
    build_story_arc_bgm_schedule,
    select_motion_bound_sfx_for_beat,
)
from documentary.critic_loops import (
    analyze_script_spoken_quality,
    audit_edit_timeline_and_screen,
    audit_footage_hygiene,
    audit_voice_hygiene,
    evaluate_voice_proper_noun_asr_gate,
    evaluate_ypp_visual_role_mix,
    sync_vox_manifest_beats_by_text_hash,
    validate_korean_script_grammar_integrity,
)
from documentary.edit_footage_fetcher import EditDirectFootageFetcher
from documentary.editorial_voice_cutter import compute_editorial_pause_plan
from documentary.prompts import (
    _director_v2_mindset_and_screening_law,
    _korean_natural_documentary_prose_direction,
)
from documentary.voice import (
    CofiVoiceEngine,
    direct_korean_emotional_prosody,
    inspect_beat_audio_quality,
    normalize_korean_tts_text,
)
from services.voice_rhythm_specialist import GENRE_RHYTHM_ARCHETYPES


REPO_ROOT = Path(__file__).resolve().parents[1]
REMOTION_ROOT = REPO_ROOT.parent / "CofiRemotion"


def test_package1_five_acts_and_five_narrative_lenses_preserved() -> None:
    script_agent_md = (REPO_ROOT / "agents" / "editorial" / "script.md").read_text(encoding="utf-8")
    story_skill_md = (REPO_ROOT / "skills" / "cofi-broadcast-storytelling-mastery" / "SKILL.md").read_text(encoding="utf-8")
    prose_prompt = _korean_natural_documentary_prose_direction()

    for act_tag in ("ACT01", "ACT02", "ACT03", "ACT04", "ACT05"):
        assert act_tag in script_agent_md
        assert act_tag in story_skill_md

    for lens_name in (
        "Forensic Reverse-Excavation",
        "Dual-Timeline Cat & Mouse",
        "Rashomon / Multi-Witness Contradiction",
        "Systemic Web & Audit Trail",
        "Psychological Interrogation Duel",
    ):
        assert lens_name in script_agent_md
        assert lens_name in story_skill_md
        assert lens_name in prose_prompt


def test_package1_standalone_one_line_noun_paragraph_gate() -> None:
    # Excessive standalone 1-line verbless noun paragraphs (> 4 and < 8 paragraphs apart) must trigger defect
    spammed_paragraphs = [
        "이천삼 년 일월 이십이 일 밤 후난성 신황현의 운동장에는 차가운 겨울비가 내리고 있었습니다. 교사 덩스핑은 공사를 멈추지 않겠다고 버텼습니다.",
        "단 한 구의 백골.",
        "수사관들은 십육 년 동안 그 아래에 무엇이 묻혀 있는지 전혀 알지 못했습니다. 기록은 서랍 속에서 조용히 사라졌습니다.",
        "십육 년의 침묵.",
        "감찰반이 도착했을 때 현장의 서류철은 이미 누군가의 손에 의해 비워져 있었습니다. 결과는 참혹했죠.",
        "조작된 부검 감정서.",
        "그러나 굴착기가 운동장 한가운데를 파 내려가자 마침내 진실이 모습을 드러냈습니다. 답은 하나뿐이었습니다.",
        "완벽한 알리바이의 붕괴.",
        "결국 보호우산 아래 숨어 있던 열아홉 명의 공직자들이 차례로 법정에 서게 되었습니다. 증거는 사라지지 않았습니다.",
        "멈춰버린 시계.",
    ]
    spammed_script = "\n\n".join(spammed_paragraphs)
    metrics = analyze_script_spoken_quality(spammed_script, "ko")
    assert metrics["standalone_one_line_noun_paragraphs"] == 5
    defect_codes = {d["code"] for d in metrics["defects"]}
    assert "standalone_one_line_noun_crutch_excess" in defect_codes

    with pytest.raises(RuntimeError, match="standalone_one_line_noun_crutch_excess"):
        validate_korean_script_grammar_integrity(spammed_script)


def test_package1_sino_korean_admin_hierarchy_pause_and_1x_voice_speed(tmp_path: Path) -> None:
    raw = "2003년 후난성 화이화시 신황현 제1중학교 운동장에서 사건이 시작되었습니다."
    normalized = normalize_korean_tts_text(raw)
    assert "후난성, 화이화시, 신황현" in normalized

    # Investigative archetypes must default to natural 1.0x speed
    assert GENRE_RHYTHM_ARCHETYPES["kr_truecrime_noir_director"]["voice_color_spec"]["prosody_profile"]["tts_speed"] == 1.0
    assert GENRE_RHYTHM_ARCHETYPES["kr_truecrime_forensic_dossier"]["voice_color_spec"]["prosody_profile"]["tts_speed"] == 1.0

    # Dual-field subtitle_display_text vs tts_spoken_text and lock_natural_1x_speed
    prosody_locked = direct_korean_emotional_prosody(
        sentence="단 육십 초.",
        index=3,
        total_sentences=20,
        base_speed=0.88,
        vocal_cadence={"lock_natural_1x_speed": True},
    )
    assert prosody_locked["beat_speed"] == 1.0
    assert prosody_locked["subtitle_display_text"] == "단 육십 초."
    assert prosody_locked["tts_spoken_text"]

    # Runtime CofiVoiceEngine.run must lock speed = 1.0 on retry and skip calibrated_speed drop when lock_natural_1x_speed / is_director_v2
    voice_run_src = inspect.getsource(CofiVoiceEngine.run)
    assert "if lock_natural_1x_speed or is_director_v2:" in voice_run_src
    assert 'retry_payload["speed"] = 1.0' in voice_run_src
    assert "_inject_gentle_breath_comma" in voice_run_src

    # Runtime inspect_beat_audio_quality proper-noun ASR check (< 0.92 triggers asr_proper_noun_mismatch)
    wav_path = tmp_path / "B001.wav"
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes((b"\x10\x02" * 8000) + (b"\x00\x00" * 1600))
    qual = inspect_beat_audio_quality(
        wav_path,
        "2003년 후난성 화이화시 신황현에서 두사오핑과 덩스핑 사건이 벌어졌습니다.",
        language="ko",
        asr_transcriber=lambda _p, _l: "2003년 후난성 화이화씨 신왕현에서 두샤오핑과 덩스핑 사건이 벌어졌습니다.",
        min_proper_noun_asr_similarity=0.92,
    )
    assert qual["asr_proper_noun_similarity"] is not None
    assert qual["asr_proper_noun_similarity"] < 0.92
    assert len(qual["asr_proper_noun_mismatches"]) >= 2
    assert "asr_proper_noun_mismatch" in qual["issues"]

    # Gate 6: Proper-Noun ASR Similarity & Artificial Slowdown Gate
    bad_vm = {
        "speed": 0.85,
        "beats": [
            {
                "beat_id": "B001",
                "speed": 0.78,
                "asr_proper_noun_similarity": 0.81,
                "asr_proper_noun_mismatches": ["신황현 -> 신왕현"],
            }
        ],
    }
    gate_res = evaluate_voice_proper_noun_asr_gate(bad_vm, min_proper_noun_similarity=0.92)
    assert gate_res["passed"] is False
    failure_types = {f["type"] for f in gate_res["failures"]}
    assert "voice_artificial_slowdown_violation" in failure_types
    assert "voice_proper_noun_asr_mismatch" in failure_types


def test_package2_semantic_verified_routing_and_anti_boilerplate_footage_gate(tmp_path: Path) -> None:
    prompt_law = _director_v2_mindset_and_screening_law()
    assert "min_footage_floor = 0.50" in prompt_law
    assert "semantic_verified_footage_routing" in prompt_law

    # 3-frame contact sheet must extract at (0.15, 0.50, 0.85) (15% - 50% - 85%)
    contact_sheet_src = inspect.getsource(EditDirectFootageFetcher.extract_3frame_contact_sheet)
    assert "(0.15, 0.50, 0.85)" in contact_sheet_src

    # When semantic_verified_routing=True, 40% real footage + 33% VOX + 10% cinema text + 17% AI_4D passes cleanly
    beats = (
        [{"beat_id": f"B{i:03d}", "visual_role": "REAL_FTG"} for i in range(1, 41)]
        + [{"beat_id": f"B{i:03d}", "visual_role": "VOX"} for i in range(41, 74)]
        + [{"beat_id": f"B{i:03d}", "visual_role": "CINEMA_TEXT"} for i in range(74, 84)]
        + [{"beat_id": f"B{i:03d}", "visual_role": "AI_4D"} for i in range(84, 101)]
    )
    with pytest.raises(RuntimeError, match="Role DNA Violation"):
        evaluate_ypp_visual_role_mix({"beats": beats}, min_real_footage_ratio=0.50, max_vox_ratio=0.28)

    mix_semantic = evaluate_ypp_visual_role_mix(
        {"beats": beats, "semantic_verified_footage_routing": True},
        min_real_footage_ratio=0.50,
        max_vox_ratio=0.28,
    )
    assert mix_semantic["passed"] is True
    assert mix_semantic["status"] == "PASSED"

    # Gate 2: Anti-boilerplate observed_content, duplicate observed_content, internal hard cut, edge banner, and semantic mismatch
    ftg_dir = tmp_path / "media" / "footage"
    ftg_dir.mkdir(parents=True, exist_ok=True)
    for idx in (1, 2, 3, 4):
        p = ftg_dir / f"S_F0{idx}.mp4"
        p.write_bytes(b"\x00" * 24576 + f"clip-{idx}".encode("utf-8"))

    (tmp_path / "visual_manifest.json").write_text(
        json.dumps(
            {
                "beats": [
                    {
                        "beat_id": "B004",
                        "voice_text": "덩스핑 교사의 가족이 운동장 공사 비리 탄원서를 제출했습니다.",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    registry = {
        "assets": [
            {
                "id": "S_F01",
                "type": "footage",
                "path": str(ftg_dir / "S_F01.mp4"),
                "eye_verified": True,
                "observed_content": "[후난성 신황현 실제 기록 영상 S_F01.mp4] 신황현 제1중학교 현장 수사 기록.",
            },
            {
                "id": "S_F02",
                "type": "footage",
                "path": str(ftg_dir / "S_F02.mp4"),
                "eye_verified": True,
                "observed_content": "법정에서 피고인 두사오핑이 판결문을 듣고 있는 클로즈업 장면",
                "has_internal_hard_cut": True,
            },
            {
                "id": "S_F03",
                "type": "footage",
                "path": str(ftg_dir / "S_F03.mp4"),
                "eye_verified": True,
                "observed_content": "법정에서 피고인 두사오핑이 판결문을 듣고 있는 클로즈업 장면",
            },
            {
                "id": "S_F04",
                "beat_id": "B004",
                "type": "footage",
                "path": str(ftg_dir / "S_F04.mp4"),
                "eye_verified": True,
                "has_edge_banner": True,
                "observed_content": "교도소 감방 안에서 수감자 양쥔이 인터뷰하는 우측 세로 자막 화면",
            },
        ]
    }
    (tmp_path / "asset_registry.json").write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    hyg = audit_footage_hygiene(tmp_path, {"id": "job-test-dushaoping"})
    assert hyg["status"] in {"FAILED", "NEEDS_ATTENTION"}
    reasons = [str(f.get("reason") or "") for f in hyg["failures"]]
    assert any("unverified_boilerplate_observed_content" in r for r in reasons)
    assert any("internal_hard_cut_detected" in r for r in reasons)
    assert any("duplicate_observed_content_across_clips" in r for r in reasons)
    assert any("edge_banner_or_text_overlay_detected" in r for r in reasons)
    assert any("observed_content_voice_semantic_mismatch" in r for r in reasons)


def test_package3_and_package5_pause_variation_organic_bgm_and_edit_gates(tmp_path: Path) -> None:
    # Sub-Role 3A: Organic pause micro-variation (never clamping all dramatic holds to a single 1.40s/1.49s value)
    sample_beats = [
        {"beat_id": f"B{i:03d}", "text": f"과연 그날 밤 운동장 아래에서는 무슨 일이 벌어졌던 걸까요? ({i})", "emotion_register": "suspense_question", "pause_after_sec": 1.40}
        for i in range(1, 10)
    ]
    pause_plan = compute_editorial_pause_plan(sample_beats)
    pause_values = [row["pause_after_sec"] for row in pause_plan]
    assert all(1.12 <= p <= 1.68 for p in pause_values)
    assert len(set(pause_values)) >= 5

    # Sub-Role 3B: Motion-bound SFX onset lag compensation + CINEMA_TEXT support + Anti-Machine-Gun 8s A/B/C rotation
    assert select_motion_bound_sfx_for_beat({"beat_id": "B001", "visualRole": "REAL_FTG", "durationInFrames": 120}) == []
    assert select_motion_bound_sfx_for_beat({"beat_id": "B002", "visualRole": "AI_4D", "durationInFrames": 120}) == []

    cinema_sfx = select_motion_bound_sfx_for_beat(
        {"beat_id": "B003", "visualRole": "CINEMA_TEXT", "durationInFrames": 120, "narration_text": "16년의 침묵"}
    )
    assert len(cinema_sfx) >= 1
    for item in cinema_sfx:
        assert item["sfx_onset_lag_frames"] >= 2
        assert item["sequence_from_frame"] == max(0, item["motion_peak_frame"] - item["sfx_onset_lag_frames"])
        assert item["offsetFrames"] == item["sequence_from_frame"]

    shared_sfx_history: list[tuple[int, str]] = []
    chosen_first_files: list[str] = []
    for idx, start_f in enumerate((0, 60, 120), start=1):
        vox_sfx = select_motion_bound_sfx_for_beat(
            {
                "beat_id": f"B01{idx}",
                "visualRole": "VOX",
                "voxArchetype": "TACTILE_EVIDENCE_DOSSIER_BOARD",
                "durationInFrames": 55,
                "narration_text": "수사 기록 카드가 책상 위로 배치됩니다.",
            },
            fps=30,
            beat_start_frame=start_f,
            sfx_history=shared_sfx_history,
        )
        assert len(vox_sfx) >= 1
        chosen_first_files.append(vox_sfx[0]["file"])
    # Within 120 frames (< 240f / 8s), A/B/C rotation must avoid repeating the same SFX file
    assert len(set(chosen_first_files)) == 3

    # Sub-Role 3C: Organic BGM segmentation (0% equal-length chunks), start_beat_id/end_beat_id/narrative_chapter_reason, & -41dBFS silence drop
    bgm_beats = [
        {
            "beat_id": f"B{i:03d}",
            "start_sec": (i - 1) * 20.0,
            "end_sec": i * 20.0,
            "startFrame": (i - 1) * 600,
            "endFrame": i * 600,
            "narration_text": (
                "굴착기가 4.5m 트랙 아래에서 마침내 백골 유골과 진실을 발굴해 체포가 이루어졌습니다."
                if i == 42
                else "신황현 운동장 발굴과 감찰 수사 기록입니다."
            ),
        }
        for i in range(1, 85)
    ]
    bgm_sched = build_story_arc_bgm_schedule(
        bgm_beats,
        fps=30,
        job_id="ep-bd449eaf-dushaoping",
        target_segments=9,
        auto_fetch_if_unfit=False,
    )
    segs = bgm_sched["segments"]
    assert len(segs) == 9
    durs = [int(s["durationInFrames"]) for s in segs]
    # Verify no >= 3 segments share identical duration within <= 15 frames
    for d_ref in durs:
        assert sum(1 for d_o in durs if abs(d_o - d_ref) <= 15) < 3
    for s in segs:
        assert "zhang_shuxia" not in s["file"].lower()
        assert s.get("start_beat_id")
        assert s.get("end_beat_id")
        assert s.get("narrative_chapter_reason")

    silence_drops = bgm_sched.get("silence_drop_windows", [])
    assert len(silence_drops) >= 1
    assert silence_drops[0]["beatId"] == "B042"
    assert silence_drops[0]["room_tone_floor_db"] == -41.0
    assert silence_drops[0]["room_tone_linear_gain"] == 0.015

    # Sub-Role 1: sync_vox_manifest_beats_by_text_hash re-binds drifted beat_id by voice_text hash
    drifted_vox = {
        "scenes": [
            {"scene_id": "VOX_03", "beat_id": "B009", "narration_text": "신황현 제1중학교 운동장 배수구 단면도 분석입니다."}
        ]
    }
    target_beats = [
        {"beat_id": "B017", "visualRole": "VOX", "voxSceneId": "VOX_03", "narration_text": "신황현 제1중학교 운동장 배수구 단면도 분석입니다."}
    ]
    sync_res = sync_vox_manifest_beats_by_text_hash(drifted_vox, target_beats)
    assert len(sync_res["repaired_beat_bindings"]) == 1
    assert drifted_vox["scenes"][0]["beat_id"] == "B017"
    assert drifted_vox["scenes"][0]["text_hash"]

    # Gate 3, Gate 4, Gate 6 inside audit_edit_timeline_and_screen
    ws = tmp_path / "ws_edit_gate"
    ws.mkdir(parents=True, exist_ok=True)
    remotion_dummy = tmp_path / "remotion_dummy"
    (remotion_dummy / "src").mkdir(parents=True, exist_ok=True)

    vox_manifest = {
        "scenes": [
            {"scene_id": "VOX_03", "beat_id": "B009", "narration_text": "완전히 다른 사건의 엉뚱한 설명 텍스트입니다."},
        ]
    }
    (ws / "vox_scene_manifest.json").write_text(json.dumps(vox_manifest, ensure_ascii=False), encoding="utf-8")

    edit_manifest = {
        "total_beats": 4,
        "semantic_verified_footage_routing": True,
        "beats": [
            {"beat_id": "B001", "visualRole": "REAL_FTG", "imageFile": "footage/S_F01.mp4"},
            {"beat_id": "B002", "visualRole": "REAL_FTG", "imageFile": "footage/S_F02.mp4"},
            {"beat_id": "B017", "visualRole": "VOX", "voxSceneId": "VOX_03", "narration_text": "신황현 운동장 4.5m 아래 매립 단면도를 보여줍니다."},
            {"beat_id": "B018", "visualRole": "AI_4D", "imageFile": "ai/B018.jpg"},
        ],
        "bgm_segments": [
            {"id": "bgm-01", "file": "audio/bgm_zhang_shuxia_1.mp3", "durationInFrames": 5400},
            {"id": "bgm-02", "file": "audio/bgm_emerging_mysteries.mp3", "durationInFrames": 5400},
            {"id": "bgm-03", "file": "audio/bgm_shadow_trail.mp3", "durationInFrames": 5400},
            {"id": "bgm-04", "file": "audio/bgm_cold_verdict.mp3", "durationInFrames": 5400},
        ],
    }
    (ws / "edit_manifest.json").write_text(json.dumps(edit_manifest, ensure_ascii=False), encoding="utf-8")
    (ws / "voice_manifest.json").write_text(
        json.dumps(
            {
                "speed": 1.0,
                "beats": [
                    {
                        "beat_id": "B001",
                        "speed": 1.0,
                        "asr_proper_noun_similarity": 0.80,
                        "asr_proper_noun_mismatches": ["화이화시 -> 화이화씨"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    voice_hyg = audit_voice_hygiene(ws)
    assert voice_hyg["passed"] is False

    screen_rep = audit_edit_timeline_and_screen(
        job={"id": "ep-bd449eaf-dushaoping", "channel_profile_id": "channel-kr-truecrime-director-v2"},
        workspace=ws,
        remotion_dir=remotion_dummy,
        beats=edit_manifest["beats"],
    )
    issue_types = {i["type"] for i in screen_rep["issues"] if isinstance(i, dict)}
    assert "vox_manifest_beat_id_mismatch" in issue_types
    assert "voice_to_visual_semantic_mismatch" in issue_types
    assert "equal_length_bgm_division_violation" in issue_types
    assert "bgm_cross_episode_reuse_violation" in issue_types
    assert "voice_proper_noun_asr_mismatch" in issue_types


def test_package4_vox_ast_validator_passes_cxm_and_catches_dushaoping_shortcuts(tmp_path: Path) -> None:
    node_bin = shutil.which("node")
    ast_script = REMOTION_ROOT / "scripts" / "validate-vox-newsroom-ast.mjs"
    assert node_bin is not None
    assert ast_script.is_file()

    cxm_dir = REMOTION_ROOT / "src" / "vox-studio" / "cxm-voxtest-10m"
    res_cxm = subprocess.run(
        [node_bin, str(ast_script), str(cxm_dir)],
        cwd=str(REMOTION_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert res_cxm.returncode == 0, f"Expected cxm-voxtest-10m to pass AST gate, got: {res_cxm.stderr}\n{res_cxm.stdout}"

    dsp_file = REMOTION_ROOT / "src" / "vox-studio" / "ep-bd449eaf-dushaoping" / "VoxScenes21to40.tsx"
    res_dsp = subprocess.run(
        [node_bin, str(ast_script), str(dsp_file)],
        cwd=str(REMOTION_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    combined_out = (res_dsp.stderr or "") + "\n" + (res_dsp.stdout or "")
    assert res_dsp.returncode != 0
    assert "[FAIL:NO_STATIC_PLACEHOLDER_CAMERA]" in combined_out
    assert "[FAIL:BOILERPLATE_NUMBERED_EVIDENCE_LABEL]" in combined_out
    assert "[FAIL:CLONED_DESK_PROP_FORMULA]" in combined_out

    # Verify Regression Guard blocks cloned SVG primitive templates (e.g. 3 rect + 3 circle across >= 4 Desk scenes even with +2px width/radius jitter)
    cloned_svg_tsx = tmp_path / "VoxScenes01to06.tsx"
    scenes_code = []
    for idx in range(1, 7):
        bw = 175 + idx * 2
        r_val = 16 + idx
        scenes_code.append(
            f"""
/**
 * @voxVerb ARCHIVAL_DOCUMENT_SYNTHESIS
 */
export const VoxScene0{idx}: React.FC<any> = ({{beat}}) => {{
  const f = 10;
  const [t1, t2, t3] = [12, 48, 96];
  const cam = camAt(f, [
    {{at: 0, pose: {{x: 960, y: 540, z: 0.96, r: 0}}}},
    {{at: t2, pose: {{x: {820 + idx * 15}, y: {430 + idx * 12}, z: 1.15, r: -0.4}}}},
    {{at: t3, pose: {{x: 960, y: 540, z: 1.02, r: 0.2}}}},
  ]);
  return (
    <Desk>
      <BlackCard inset={{38}}>
        <World cam={{cam}}>
          <SlideIn f={{f}} at={{t1}} from="top" style={{{{position: 'absolute', left: {80 + idx * 45}, top: {70 + idx * 35}}}}}>
            <svg width={{680}} height={{220}}>
              <rect x={{14}} y={{18}} width={{{bw}}} height={{64}} rx={{6}} />
              <rect x={{228}} y={{18}} width={{{bw + 10}}} height={{64}} rx={{6}} />
              <rect x={{448}} y={{18}} width={{{bw + 18}}} height={{64}} rx={{6}} />
              <circle cx={{48}} cy={{140}} r={{{r_val}}} />
              <circle cx={{268}} cy={{140}} r={{{r_val + 2}}} />
              <circle cx={{498}} cy={{140}} r={{{r_val + 4}}} />
              <path d="M 70 140 Q 160 96 244 140" />
              <line x1={{292}} y1={{140}} x2={{472}} y2={{140}} />
              <text x={{30}} y={{54}}>STEP 01 · VERIFIED</text>
              <text x={{502}} y={{54}}>STEP 03 · CRITICAL LOCK</text>
              <text x={{30}} y={{96}}>TARGET LOCK · 테스트</text>
            </svg>
          </SlideIn>
        </World>
      </BlackCard>
    </Desk>
  );
}};
"""
        )
    cloned_svg_tsx.write_text("\n".join(scenes_code), encoding="utf-8")
    res_cloned_svg = subprocess.run(
        [node_bin, str(ast_script), str(cloned_svg_tsx)],
        cwd=str(REMOTION_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    cloned_svg_out = (res_cloned_svg.stderr or "") + "\n" + (res_cloned_svg.stdout or "")
    assert res_cloned_svg.returncode != 0
    assert "[FAIL:CLONED_SVG_DIAGRAM_TEMPLATE]" in cloned_svg_out
    assert "[FAIL:BANNED_LEGACY_STEP_BOX_LABEL]" in cloned_svg_out
    assert "[FAIL:CAMERA_ZOOM_OUT_SHRINKS_DESK]" in cloned_svg_out


def test_zero_legacy_config_contradictions_across_profiles_and_services() -> None:
    profiles_path = REPO_ROOT / "data" / "channel_profiles.json"
    editing_dna_path = REPO_ROOT / "services" / "editing_dna_service.py"
    agents_md_path = REPO_ROOT / "AGENTS.md"

    profiles_raw = profiles_path.read_text(encoding="utf-8")
    editing_dna_raw = editing_dna_path.read_text(encoding="utf-8")
    agents_md_raw = agents_md_path.read_text(encoding="utf-8")

    forbidden_legacy_tokens = [
        "#1D1814",
        "BlueprintPaperSurface",
        "vibe_motion_x_vox_director",
        "unfocusedBlur",
        "unfocusedBrightness",
        "BESPOKE_DIE_CUT_COLLAGE_AND_3D_GIS_VOX",
    ]
    for token in forbidden_legacy_tokens:
        assert token not in profiles_raw, f"Legacy token {token!r} found in data/channel_profiles.json"
        assert token not in editing_dna_raw, f"Legacy token {token!r} found in services/editing_dna_service.py"

    assert "TACTILE_VOX_EDITORIAL_DESK_AND_3D_GIS_VOX" in profiles_raw
    assert "TACTILE_VOX_EDITORIAL_DESK_AND_3D_GIS_VOX" in editing_dna_raw
    assert "semantic_verified_footage_routing" in profiles_raw
    assert "semantic_verified_footage_routing" in editing_dna_raw

    profiles_data = json.loads(profiles_raw)
    profiles_by_id = {
        (p.get("id") or p.get("profile_id")): p
        for p in profiles_data.get("profiles", [])
        if isinstance(p, dict) and (p.get("id") or p.get("profile_id"))
    }
    for pid in (
        "channel-kr-truecrime-director-v2",
        "channel-e544a64b7c",
        "channel-cn-cyber-finance-kr",
        "channel-1e24de3ab5",
    ):
        assert pid in profiles_by_id, f"Missing profile {pid}"
        prof = profiles_by_id[pid]
        assert prof.get("tts_speed") == 1.0, f"{pid} top-level tts_speed != 1.0"
        assert prof.get("voice_signature", {}).get("tts_speed") == 1.0, f"{pid} voice_signature.tts_speed != 1.0"
        prosody_speed = (
            prof.get("rhythm_dna", {})
            .get("voice_color_spec", {})
            .get("prosody_profile", {})
            .get("tts_speed")
        )
        assert prosody_speed == 1.0, f"{pid} rhythm_dna prosody_profile.tts_speed != 1.0"

    assert "semantic_verified_footage_routing" in agents_md_raw
    assert "10 Editorial Desk Archetypes" in agents_md_raw

