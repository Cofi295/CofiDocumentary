from __future__ import annotations

import json
import re
from pathlib import Path
import pytest

from documentary.prompts import (
    EPISODE_CTA_RHETORICAL_FORMS,
    build_phase_prompt,
    select_episode_narrative_variant,
)
from documentary.quality import (
    normalize_production_recipe,
    validate_korean_anti_template_diversity,
    validate_phase_quality,
)
from documentary.service import DocumentaryService

ROOT = Path(__file__).resolve().parents[1]


def test_zero_contradictory_cta_rules_across_entire_codebase() -> None:
    """Ensure zero legacy 2-touchpoint or fixed 50% mid-roll rules remain anywhere in active files."""
    checked_files = [
        ROOT / "documentary" / "prompts.py",
        ROOT / "documentary" / "service.py",
        ROOT / "documentary" / "agent_manager.py",
        ROOT / "services" / "self_learning_service.py",
        ROOT / "data" / "channel_profiles.json",
        ROOT / "data" / "channel_playbooks.json",
        ROOT / "static" / "app.js",
        ROOT / "static" / "index.html",
    ]
    banned_contradictions = (
        "2-TOUCHPOINT",
        "2_touchpoints",
        "2 điểm chạm",
        "2 ĐIỂM CHẠM",
        "Điểm chạm 1",
        "ĐIỂM CHẠM 1",
        "Điểm chạm 2",
        "ĐIỂM CHẠM 2",
        "mid_roll_cta_mode",
        "50% số video",
        "50% số tập",
    )
    for fpath in checked_files:
        content = fpath.read_text(encoding="utf-8")
        for token in banned_contradictions:
            assert token not in content, f"Contradictory legacy CTA rule '{token}' still present in {fpath.name}"


def test_episode_cta_rhetorical_forms_rotate_6_distinct_story_driven_forms() -> None:
    assert len(EPISODE_CTA_RHETORICAL_FORMS) == 6
    variants = [
        select_episode_narrative_variant({"id": f"job-{i}", "structural_variant_index": i})
        for i in range(6)
    ]
    cta_forms = [v["cta_rhetorical_form"] for v in variants]
    assert len(set(cta_forms)) == 6
    assert "flexible_mid_pause_or_closing_archive_note" in cta_forms
    assert "interrogative_viewer_perspective" in cta_forms
    assert "declarative_archive_record_note" in cta_forms
    assert "story_breath_companion_or_finale_handoff" in cta_forms
    assert "case_motif_narrative_handoff" in cta_forms
    assert "minimalist_noun_epilogue_nod" in cta_forms

    openings_4 = {variants[i]["opening_mode"] for i in range(4)}
    endings_4 = {variants[i]["ending_mode"] for i in range(4)}
    assert len(openings_4) == 4
    assert len(endings_4) == 4


def test_smart_outline_and_plan_prompt_enforce_zero_repeat_and_keep_en_hangul_free(tmp_path: Path) -> None:
    outlines_tc = [
        DocumentaryService._build_smart_outline(
            title=f"[중국 실화 사건] 사건 파일 #{idx}",
            notes="특급수배록",
            angle_id="forensic_investigative",
            angle_label="Điều tra",
            style_label="Điềm tĩnh",
            hook_label="Nghịch lý",
            chapter_count=5,
            profile_id="channel-e544a64b7c",
            target_duration_minutes=25.0,
            job_id=f"job-tc-{idx}",
            structural_variant_index=idx,
        )
        for idx in range(6)
    ]
    assert len({o[0]["title"] for o in outlines_tc[:4]}) == 4
    assert len({o[4]["title"] for o in outlines_tc[:4]}) == 4
    assert "linh hoạt theo nội dung" in outlines_tc[0][4]["summary"].lower()
    assert "08:00–12:00" in outlines_tc[3][4]["summary"]

    ko_job = {
        "id": "job-kr-new-episode",
        "title": "[중국 실화 사건] 구이저우 2만 4천 기판 미스터리",
        "channel_profile_id": "channel-e544a64b7c",
        "market": "KR",
        "language": "ko",
        "visual_strategy": "edit_direct_footage",
        "target_duration_minutes": 25,
        "structural_variant_index": 2,
    }
    ko_prompt = build_phase_prompt(ko_job, "plan", tmp_path / "ws_ko", ROOT.parent / "CofiRemotion")
    assert "RECENT CHANNEL EPISODE SRT & FULL-SCRIPT CTA FINGERPRINTS" in ko_prompt
    assert "All CTA/Invitation sentences anywhere in script" in ko_prompt
    assert 'cta_rhetorical_form = "declarative_archive_record_note"' in ko_prompt
    assert "mid_roll_soft_cta" not in ko_prompt or "NEVER emit legacy mechanical pop-up tags" in ko_prompt

    en_job = {
        "id": "job-us-clean",
        "title": "Declassified Executive Memo 1974",
        "channel_profile_id": "channel-f6ec4dfff3",
        "market": "US",
        "language": "en",
        "visual_strategy": "hybrid",
        "target_duration_minutes": 20,
        "creative_brief": {"cta_strategy": "At most one organic story-driven closing thought; never repeat CTA."},
    }
    en_prompt = build_phase_prompt(en_job, "plan", tmp_path / "ws_en", ROOT.parent / "CofiRemotion")
    assert "channel-e544a64b7c" not in en_prompt
    assert "channel-cn-cyber-finance-kr" not in en_prompt
    assert not re.search(r"[\uac00-\ud7a3]", en_prompt), "US English prompt must remain 100% Hangul-free"


def test_gate_blocks_intra_episode_duplicate_cta_early_cta_and_formulaic_cta_syntax() -> None:
    base_beats = [
        {"beat_id": f"B{i:03d}", "narration_text": f"{i}번째 현장 감식 기록에서 낯선 지문 하나가 드러났습니다."}
        for i in range(1, 25)
    ]

    # 0. Pure zero-CTA script passes cleanly
    res_pure = validate_korean_anti_template_diversity(
        base_beats, recent_scripts=[], cta_rhetorical_form="pure_story_zero_explicit_cta"
    )
    assert res_pure["status"] == "PASSED"
    assert res_pure["cta_count"] == 0

    # 1. Diverse, organic single-moment CTAs with varied sentence structures PASS
    organic_q = [dict(b) for b in base_beats]
    organic_q[-2] = {
        "beat_id": "B023",
        "narration_text": "그날 밤 역 대합실에 서 있던 사람이 여러분이었다면 어떤 선택을 하셨을까요? 이 사건이 남긴 생각을 댓글로 조용히 나눠 주셔도 좋겠습니다.",
    }
    assert (
        validate_korean_anti_template_diversity(
            organic_q, recent_scripts=[], cta_rhetorical_form="interrogative_viewer_perspective"
        )["cta_count"]
        == 1
    )

    organic_decl = [dict(b) for b in base_beats]
    organic_decl[-2] = {
        "beat_id": "B023",
        "narration_text": "저희 채널은 서류 행간에 묻힌 실제 기록들을 하나씩 복원해 두고 있으니 구독으로 발자취를 남겨 두셔도 좋겠습니다.",
    }
    assert (
        validate_korean_anti_template_diversity(
            organic_decl, recent_scripts=[], cta_rhetorical_form="declarative_archive_record_note"
        )["cta_count"]
        == 1
    )

    organic_mid_breath = [dict(b) for b in base_beats]
    organic_mid_breath[10] = {
        "beat_id": "B011",
        "narration_text": "십칠 년의 공백을 메워 가는 이 추적을 저희 채널을 구독해 둔 채 차분히 지켜봐 주셔도 좋겠습니다.",
    }
    assert (
        validate_korean_anti_template_diversity(
            organic_mid_breath, recent_scripts=[], cta_rhetorical_form="story_breath_single_companion_aside"
        )["cta_count"]
        == 1
    )

    # 2. Intra-episode CTA repetition (2 CTAs in the same script) -> REJECTED
    dup_cta = [dict(b) for b in base_beats]
    dup_cta[9] = {
        "beat_id": "B010",
        "narration_text": "긴 공백을 메워 가는 이 기록을 저희 채널과 함께 차분히 따라가 보겠습니다.",
    }
    dup_cta[22] = {
        "beat_id": "B023",
        "narration_text": "잊힌 진실을 복원하는 이 공간에 구독으로 발자취를 남겨 두셔도 좋겠습니다.",
    }
    with pytest.raises(RuntimeError, match="multiple times in the same script"):
        validate_korean_anti_template_diversity(dup_cta, recent_scripts=[])

    # 3. Early hook CTA (in first 15% of beats) -> REJECTED
    early_cta = [dict(b) for b in base_beats]
    early_cta[1] = {
        "beat_id": "B002",
        "narration_text": "저희 채널에 구독으로 발자취를 남겨 두셔도 좋겠습니다.",
    }
    with pytest.raises(RuntimeError, match="opening hook window"):
        validate_korean_anti_template_diversity(early_cta, recent_scripts=[])

    # 4. Formulaic conditional/imperative CTA syntax -> REJECTED
    for robotic_cta in (
        "26년 전 유괴범을 역추적하는 이 실화 수사를 응원하신다면, 지금 구독과 좋아요를 눌러 끝까지 함께해 주시기 바랍니다.",
        "소중한 노후 자금을 지키는 금융 수사 기록을 놓치지 않으시려면 구독과 알림을 눌러주십시오.",
        "지금 채널 구독과 알림 설정을 꼭 부탁드립니다.",
        "철통같은 감시망을 뚫고 증발한 수배범의 행적을 지금 구독과 좋아요로 함께 추적해 보시기 바랍니다.",
    ):
        bad_syntax = [dict(b) for b in base_beats]
        bad_syntax[12] = {"beat_id": "B013", "narration_text": robotic_cta}
        with pytest.raises(RuntimeError, match="formulaic conditional/imperative CTA skeleton"):
            validate_korean_anti_template_diversity(bad_syntax, recent_scripts=[])

    # 5. Legacy mechanical CTA purpose tags -> REJECTED
    for legacy_purpose in ("mid_roll_soft_cta", "end_screen_cta_bridge"):
        bad_tag = [dict(b) for b in base_beats]
        bad_tag[12] = {"beat_id": "B013", "purpose": legacy_purpose, "narration_text": base_beats[12]["narration_text"]}
        with pytest.raises(RuntimeError, match="legacy mechanical CTA purpose"):
            validate_korean_anti_template_diversity(bad_tag, recent_scripts=[])

    # 6. Role form violations -> REJECTED
    with pytest.raises(RuntimeError, match="pure_story_zero_explicit_cta"):
        validate_korean_anti_template_diversity(
            organic_decl, recent_scripts=[], cta_rhetorical_form="pure_story_zero_explicit_cta"
        )
    with pytest.raises(RuntimeError, match="story_breath_single_companion_aside"):
        validate_korean_anti_template_diversity(
            organic_decl, recent_scripts=[], cta_rhetorical_form="story_breath_single_companion_aside"
        )

    # 7. Time-rewind, moralizing, and stock SRT outro lines -> REJECTED
    bad_rewind = [dict(b) for b in base_beats]
    bad_rewind[2] = {"beat_id": "B003", "narration_text": "시계를 1998년 12월 1일 오후로 되돌려 봅니다."}
    with pytest.raises(RuntimeError, match="stock flashback transition"):
        validate_korean_anti_template_diversity(bad_rewind, recent_scripts=[])

    bad_moral = [dict(b) for b in base_beats]
    bad_moral[-2] = {"beat_id": "B023", "narration_text": "아무리 치밀한 위장도 완전범죄는 존재할 수 없습니다."}
    with pytest.raises(RuntimeError, match="stock moralizing cliché"):
        validate_korean_anti_template_diversity(bad_moral, recent_scripts=[])

    for outro_cliche in (
        "관련된 또 다른 미제 사건 기록이 지금 화면에 표시되고 있습니다.",
        "바로 지금 화면에 준비돼 있습니다.",
        "끝까지 시청해 주셔서 감사합니다.",
    ):
        bad_outro = [dict(b) for b in base_beats]
        bad_outro[-1] = {"beat_id": "B024", "narration_text": outro_cliche}
        with pytest.raises(RuntimeError, match="copy-pasted outro/end-screen phrase"):
            validate_korean_anti_template_diversity(bad_outro, recent_scripts=[])


def test_gate_blocks_cross_episode_cta_repeat_anywhere_in_script_and_cloned_srt_ends(tmp_path: Path) -> None:
    # Episode 1 has an organic CTA in the MIDDLE of the script (line 6 of 16)
    prior_episode_script = "\n".join(
        [f"초반 수사 단서 {i}번째 항목이 공안국 기록실로 이관되었습니다." for i in range(1, 6)]
        + ["서류 행간에 묻힌 실제 기록들을 복원하는 저희 채널에 구독으로 발자취를 남겨 두셔도 좋겠습니다."]
        + [f"후반 법정 심리 {i}일차에 새로운 회계 장부가 공개되었습니다." for i in range(6, 12)]
        + [
            "수사관의 책상 위에는 아직 닫히지 않은 낡은 수첩 한 권이 놓여 있었습니다.",
            "피해자 가족은 십팔 년 만에 처음으로 고향 기차역 플랫폼을 다시 찾았죠.",
            "남겨진 사진 속 시계 바늘만 그날 오후 네 시에 멈춰 서 있었습니다.",
            "창고 바닥 아래에서 건져 올린 진실은 그렇게 기록으로 남았습니다.",
            "겨울바람만 빈 승강장을 조용히 스쳐 지나갔습니다.",
        ]
    )

    # Episode 2 uses a COMPLETELY DIFFERENT CTA sentence structure -> PASSES
    fresh_ep2_beats = [
        {
            "beat_id": f"B{i:03d}",
            "narration_text": (
                f"새로운 회계 감사 자료 {i}호가 법정에 제출되었죠."
                if i % 3 == 0
                else f"검찰 수사관은 {i}번째 계좌 내역을 대조했습니다."
            ),
        }
        for i in range(1, 16)
    ] + [
        {"beat_id": "B016", "narration_text": "압수된 서버실 문이 닫히던 날 바깥에는 첫눈이 내리고 있었습니다."},
        {"beat_id": "B017", "narration_text": "환수된 자금 일부가 마침내 피해 농가 계좌로 돌아갔죠."},
        {
            "beat_id": "B018",
            "narration_text": "만약 그날 은행 창구 직원이 서류 한 장을 그냥 넘겼다면 결과는 어땠을까요? 여러분의 생각을 댓글로 들려주셔도 좋겠습니다.",
        },
        {"beat_id": "B019", "narration_text": "그날의 통장 사본 한 장이 남긴 질문은 여전히 무겁습니다."},
        {"beat_id": "B020", "narration_text": "텅 빈 전산실 불빛만 밤늦도록 꺼지지 않았습니다."},
    ]
    res_ok = validate_korean_anti_template_diversity(fresh_ep2_beats, recent_scripts=[prior_episode_script])
    assert res_ok["status"] == "PASSED"
    assert res_ok["cta_count"] == 1

    # Episode 2 tries to reuse Episode 1's mid-script CTA at the END of Episode 2 (even with tweaked nouns!) -> REJECTED!
    reused_cta_beats = [dict(b) for b in fresh_ep2_beats]
    reused_cta_beats[17] = {
        "beat_id": "B018",
        "narration_text": "금융 장부 뒤에 숨은 사건들을 복원하는 저희 채널에 구독으로 발자취를 남겨 두셔도 좋겠습니다.",
    }
    with pytest.raises(RuntimeError, match="Zero-Repeat CTA cross-episode error"):
        validate_korean_anti_template_diversity(reused_cta_beats, recent_scripts=[prior_episode_script])

    # Cloned final 5 lines (even with 0 CTA) -> REJECTED!
    cloned_tail_beats = fresh_ep2_beats[:15] + [
        {"beat_id": "B016", "narration_text": "수사관의 책상 위에는 아직 닫히지 않은 낡은 수첩 한 권이 놓여 있었습니다."},
        {"beat_id": "B017", "narration_text": "피해자 가족은 십팔 년 만에 처음으로 고향 기차역 플랫폼을 다시 찾았죠."},
        {"beat_id": "B018", "narration_text": "남겨진 사진 속 시계 바늘만 그날 오후 네 시에 멈춰 서 있었습니다."},
        {"beat_id": "B019", "narration_text": "창고 바닥 아래에서 건져 올린 진실은 그렇게 기록으로 남았습니다."},
        {"beat_id": "B020", "narration_text": "겨울바람만 빈 승강장을 조용히 스쳐 지나갔습니다."},
    ]
    with pytest.raises(RuntimeError, match="final 5 sentences share"):
        validate_korean_anti_template_diversity(cloned_tail_beats, recent_scripts=[prior_episode_script])

    # End-to-end validate_phase_quality('plan') rejects duplicate CTAs inside one episode
    ws = tmp_path / "plan_ws"
    ws.mkdir(parents=True, exist_ok=True)
    recipe = normalize_production_recipe(
        {"quality_contract": {"min_scene_count": 10}},
        target_duration_minutes=2,
        visual_strategy="full_ai",
    )
    dup_plan_beats = [
        {
            "beat_id": f"B{i:03d}",
            "narration_text": (
                "이 긴 추적 기록을 저희 채널과 함께 따라가 보겠습니다."
                if i == 8
                else (
                    "잊힌 사건을 기록하는 저희 채널에 구독으로 발자취를 남겨 두셔도 좋겠습니다."
                    if i == 18
                    else ("짧은 정적." if i % 4 == 0 else (f"수사팀은 단서 {i}호를 다시 열었죠." if i % 3 == 0 else f"검찰 기록에서 단서 {i}호가 확인되었습니다."))
                )
            ),
        }
        for i in range(1, 20)
    ]
    (ws / "visual_manifest.json").write_text(
        json.dumps({"target_duration_sec": 120, "beats": dup_plan_beats}, ensure_ascii=False),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="multiple times in the same script"):
        validate_phase_quality("plan", ws, {"id": "job-plan-gate", "language": "ko", "production_recipe": recipe})
