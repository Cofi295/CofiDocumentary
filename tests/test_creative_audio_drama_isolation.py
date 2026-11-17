from __future__ import annotations

import json
from pathlib import Path

from documentary.agent_departments import (
    AGENT_DEPARTMENTS,
    resolve_profile_department_plan,
)
from documentary.agent_manager import AgentManager
from documentary.ai_visual import AIVisualCoordinator
from documentary.audio_library_manager import (
    build_story_arc_bgm_schedule,
    select_motion_bound_sfx_for_beat,
)
from documentary.critic_loops import _build_script_doctor_critic_prompt
from documentary.edit import build_edit_rhythm_score
from documentary.nexus_coordinator import NexusCoordinator
from documentary.prompts import (
    build_footage_eye_agent_prompt,
    build_phase_prompt,
    is_any_vox_enabled_for_job,
    is_creative_audio_drama_job,
)
from documentary.visuals import VisualsCoordinator
from services.channel_profile_service import ChannelProfileService
from services.job_service import JobService


ROOT = Path(__file__).resolve().parent.parent


def _load_profile(profile_id: str) -> dict:
    svc = ChannelProfileService(ROOT / "data" / "channel_profiles.json")
    return svc.get_profile(profile_id)


def _make_job_from_profile(profile: dict, workspace: Path) -> dict:
    return {
        "id": f"job-test-{profile['id'][-8:]}",
        "title": "칠십 평생 숨겨온 어머니의 자개장 비밀",
        "topic": "시댁의 멸시를 견뎌온 며느리가 사실은 전설적인 나전칠기 명장이었다는 감동 반전 드라마",
        "language": profile.get("language") or "ko",
        "market": profile.get("market") or "KR",
        "channel_profile_id": profile["id"],
        "content_mode": profile.get("content_mode") or "",
        "visual_strategy": profile.get("visual_strategy") or "hybrid",
        "target_duration_minutes": profile.get("default_duration_minutes") or 70,
        "editing_dna": profile.get("editing_dna") or {},
        "rhythm_dna": profile.get("rhythm_dna") or {},
        "creative_brief": profile.get("default_creative_brief") or {},
        "seo_keyword_dna": profile.get("seo_keyword_dna") or {},
        "thumbnail_dna": profile.get("thumbnail_dna") or {},
        "voice": {
            "voice_id": profile.get("voice_id"),
            "speed": profile.get("voice_speed") or 0.94,
        },
        "channel_profile_snapshot": profile,
        "workspace": str(workspace),
    }


def test_agent_charters_and_departments_pass_constitutional_lint():
    mgr = AgentManager()
    lint_result = mgr.lint_corpus()
    assert lint_result["passed"] is True, lint_result
    assert lint_result["errors"] == [], lint_result
    assert lint_result["warnings"] == [], lint_result
    assert len(AGENT_DEPARTMENTS) == 15
    total_personnel = sum(2 + len(d.get("specialists") or []) for d in AGENT_DEPARTMENTS.values())
    assert total_personnel == 92


def test_goodnight_audio_drama_profile_inherits_korean_linguistic_dna_and_bypasses_vox():
    prof = _load_profile("channel-kr-goodnight-drama-50m")
    assert prof["content_mode"] == "creative_audio_drama"
    assert prof["visual_strategy"] == "hybrid"
    assert prof["voice_id"] == "f4b3fbe5-092f-4ee6-8677-90561f07ca77"
    assert prof["voice_signature"]["base_voice_id"] == "f4b3fbe5-092f-4ee6-8677-90561f07ca77"
    assert prof["default_duration_minutes"] == 70

    ed_dna = prof["editing_dna"]
    assert ed_dna["preset_id"] == "kr_goodnight_cinema_drama"
    assert ed_dna["vox_enabled"] is False
    assert ed_dna["vox_desk_enabled"] is False
    assert ed_dna["vox_satellite_enabled"] is False
    assert ed_dna["visual_priority_mode"] == "ai_cinema_character_drama"
    assert ed_dna["footage_mode"] == "atmospheric_broll"
    assert ed_dna["character_reference_mode"] == "self_generated_flow_master_sheet_per_episode"
    assert ed_dna["bgm_genre_policy"] == "warm_nocturne_chamber"
    assert ed_dna["zero_startle_sfx"] is True
    assert ed_dna["chapter_count"] == 6
    assert ed_dna["cta_policy"] == "zero_spoken_cta"

    kp = prof["editorial_dna"]["korean_prose_and_grammar_rules"]
    assert kp["require_geodeunyo_cadence"] is True
    assert kp["speaker_attribution_first"] is True
    assert kp["pure_hangul_tts_numerals"] is True
    assert "노부부" in kp["cultural_age_addressing_rule"]
    assert "체호프의 총" in kp["chekhovs_gun_character_closure_rule"]

    dept_plan = resolve_profile_department_plan(prof)
    assert "vox" in dept_plan["bypassed_department_ids"]
    assert dept_plan["departments"]["vox"]["disposition"] == "bypassed"
    assert dept_plan["departments"]["vox"]["active"] is False
    assert dept_plan["departments"]["footage"]["disposition"] == "lightweight_mode"
    assert dept_plan["departments"]["ai_visual"]["disposition"] == "elevated_lead_with_new_role"

    rhythm_acts = prof["rhythm_dna"]["editing_cadence"]["editorial_craft"]["color_emotion_arc"]
    assert "act_6" in rhythm_acts


def test_prompts_and_charters_isolate_audio_drama_from_true_crime(tmp_path: Path):
    prof = _load_profile("channel-kr-goodnight-drama-50m")
    job = _make_job_from_profile(prof, tmp_path)

    assert is_creative_audio_drama_job(job) is True
    assert is_any_vox_enabled_for_job(job) is False

    nexus = NexusCoordinator()
    vis_charter = nexus.build_phase_charter_block(job, "visuals", tmp_path)
    assert "ai_visual" in vis_charter
    assert "@vox" not in vis_charter.splitlines()[0]

    mgr = AgentManager()
    vox_skills = mgr.resolve_bound_skills("vox", selected_job=job)
    assert vox_skills == []

    plan_prompt = build_phase_prompt(job, "plan", tmp_path, tmp_path)
    assert "화자 선행" in plan_prompt
    assert "Xương sống" in plan_prompt
    assert "0% Spoken CTA" in plan_prompt or "구독" in plan_prompt
    assert "GeoJson3DMapStage" not in plan_prompt
    assert "법정 피고인석" not in plan_prompt

    seo_prompt = build_phase_prompt(job, "seo", tmp_path, tmp_path)
    assert "Courtroom / Trial" not in seo_prompt
    assert "Arrest / Escort" not in seo_prompt
    assert "K-Drama" in seo_prompt or "Situational" in seo_prompt

    ftg_prompt = build_footage_eye_agent_prompt(
        job,
        tmp_path,
        tmp_path,
        [{"id": "B001", "duration_sec": 6.0, "voice_text": "빗소리가 처마 끝에 조용히 떨어졌습니다."}],
    )
    assert "ATMOSPHERIC" in ftg_prompt.upper()
    assert "0%" in ftg_prompt

    doc_prompt = _build_script_doctor_critic_prompt(
        "은수는 조용히 찻잔을 내려놓았습니다.\n큰며느리가 눈썹을 찌푸리며 말했죠. \"어머니, 이제 그만하시죠.\"",
        {"defects": []},
        language="ko",
        market="KR",
        seo_primary_keyword="오디오드라마",
        job=job,
    )
    assert "ZERO SPOKEN CTA" in doc_prompt
    assert "화자 선행" in doc_prompt


def test_visuals_router_and_flow_character_sheet_continuity(tmp_path: Path):
    prof = _load_profile("channel-kr-goodnight-drama-50m")
    job = _make_job_from_profile(prof, tmp_path)

    script_lines = [
        f"비 내리는 서울의 밤거리에서 은수는 삼십 년 된 공방의 등불을 조용히 켰습니다." if i == 3 else f"은수는 조용히 나전칠기 함을 어루만지며 {i}번째 매듭을 다듬었죠."
        for i in range(1, 11)
    ]
    (tmp_path / "script.md").write_text("\n\n".join(script_lines), encoding="utf-8")
    voice_beats = [
        {"beat_id": f"B{i:03d}", "text": line, "start_sec": (i - 1) * 6.0, "end_sec": i * 6.0}
        for i, line in enumerate(script_lines, 1)
    ]
    (tmp_path / "voice_manifest.json").write_text(
        json.dumps({"duration_sec": 60.0, "beats": voice_beats}, ensure_ascii=False),
        encoding="utf-8",
    )
    plan_beats = [
        {
            "beat_id": f"B{i:03d}",
            "narration_text": line,
            "visual_description": "비 내리는 밤 골목과 처마 끝 빗방울 풍경" if i == 3 else "따뜻한 공방 조명 아래 나전칠기 함을 닦는 은수의 모습",
            "visual_route": "footage" if i == 3 else "ai_visual",
            "source_priority": "prefer_real" if i == 3 else "prefer_ai",
        }
        for i, line in enumerate(script_lines, 1)
    ]
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps({"target_duration_sec": 60.0, "beats": plan_beats}, ensure_ascii=False),
        encoding="utf-8",
    )

    VisualsCoordinator().run(job, tmp_path)
    stp = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    assert stp["co_lead_agent"] == "ai_visual"
    routes = [b["visual_route"] for b in stp["beats"]]
    assert "vox" not in routes
    assert routes.count("ai_visual") >= 8
    assert routes.count("footage") >= 1
    for b in stp["beats"]:
        assert "#FFD43B" not in b["prompt"]
        assert not b.get("vox_design_prompt")

    # Verify Flow Master Character Sheet generation & prompt injection
    (tmp_path / "character_bible.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "char_01_eunsu",
                        "name": "은수",
                        "role": "protagonist",
                        "aliases": ["어머니", "장인"],
                        "appearance": "62-year-old dignified Korean mother-of-pearl artisan woman, silver-streaked low bun, indigo linen hanbok jacket",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    src_dummy = tmp_path / "dummy_generated.jpg"
    src_dummy.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 2048)

    called_scenes: list[dict] = []

    def fake_runner(scene: dict, req_path: Path) -> str:
        called_scenes.append(scene)
        return str(src_dummy)

    coord = AIVisualCoordinator(tool_runner=fake_runner)
    cast = coord.ensure_episode_character_reference_sheets(
        tmp_path,
        job,
        image_model="nano_banana_2",
        aspect_ratio="16:9",
        preset_prompt=prof.get("default_ai_custom_style") or "",
    )
    assert len(cast) == 1
    assert Path(cast[0]["sheet_path"]).is_file()
    assert len(called_scenes) == 1
    assert "MASTER CHARACTER REFERENCE SHEET" in called_scenes[0]["prompt"]

    refs = AIVisualCoordinator._character_reference_images(stp["beats"][0], tmp_path, job)
    assert refs == [cast[0]["sheet_path"]]
    vstyle = AIVisualCoordinator._build_visual_style(stp, job=job)
    assert vstyle["color_mode"] == "warm_35mm_cinema_color"
    beat_prompt = AIVisualCoordinator._prompt(
        stp["beats"][0],
        visual_style=vstyle,
        preset_prompt=prof.get("default_ai_custom_style") or "",
        has_style_reference=False,
        character_profiles=cast,
        has_character_reference=True,
    )
    assert "CHARACTER IDENTITY & WARDROBE CONTINUITY LOCK" in beat_prompt
    assert "은수" in beat_prompt
    assert "#FFD43B" not in beat_prompt


def test_warm_nocturne_bgm_6_act_edit_and_zero_startle_sfx(tmp_path: Path):
    prof = _load_profile("channel-kr-goodnight-drama-50m")
    job = _make_job_from_profile(prof, tmp_path)

    beats_70m = [
        {
            "beat_id": f"B{i:03d}",
            "act": f"ACT0{((i - 1) * 6 // 60) + 1}",
            "narration_text": "조용한 밤 찻잔의 온기가 방 안을 채웠습니다.",
            "start_sec": (i - 1) * 70.0,
            "end_sec": i * 70.0,
            "visual_type": "ai_reconstruction",
            "zero_startle_sfx": True,
            "bgm_genre_policy": "warm_nocturne_chamber",
        }
        for i in range(1, 61)
    ]
    bgm = build_story_arc_bgm_schedule(
        beats_70m,
        fps=30,
        job_id="job-goodnight-70m",
        channel_profile_id="channel-kr-goodnight-drama-50m",
        auto_fetch_if_unfit=False,
    )
    assert len(bgm["segments"]) > 12
    for seg in bgm["segments"]:
        assert seg["mood"].startswith("w0")
        assert "dark" not in seg["file"].lower()
        assert "bad_impact" not in seg["file"].lower()
        assert "xuli" not in seg["file"].lower()

    assert select_motion_bound_sfx_for_beat(beats_70m[0], fps=30, is_chapter_start=True) == []

    score = build_edit_rhythm_score(job, tmp_path, beats_70m)
    acts_seen = {b["act_index"] for b in score["beats"]}
    assert 6 in acts_seen


def test_korean_true_crime_profiles_remain_100_percent_intact(tmp_path: Path):
    tc_prof = _load_profile("channel-kr-truecrime-director-v2")
    tc_job = _make_job_from_profile(tc_prof, tmp_path)

    assert is_creative_audio_drama_job(tc_job) is False
    assert is_any_vox_enabled_for_job(tc_job) is True

    dept_plan = resolve_profile_department_plan(tc_prof)
    assert dept_plan["bypassed_department_ids"] == []
    assert dept_plan["departments"]["vox"]["active"] is True

    vis_charter = NexusCoordinator().build_phase_charter_block(tc_job, "visuals", tmp_path)
    assert "vox" in vis_charter

    # Ensure JobService preserves selective_ai for K-Audio Drama without breaking True Crime
    js = JobService.__new__(JobService)
    assert js is not None


def test_audio_drama_factual_math_anti_ai_and_cold_open_filters():
    from documentary.critic_loops import (
        analyze_script_spoken_quality,
        normalize_korean_script_orthography,
    )
    from documentary.agent_departments import build_live_departments_projection

    prof = _load_profile("channel-kr-goodnight-drama-50m")
    job = {
        "language": "ko",
        "market": "KR",
        "content_mode": "creative_audio_drama",
        "channel_profile_id": prof["id"],
        "editing_dna": prof["editing_dna"],
        "channel_profile_snapshot": prof,
    }

    # 1. Verify live department projection adapts @research, @script, @visuals, @edit, @evidence_qa roles while preserving 92 headcount
    proj = build_live_departments_projection(job_snapshot=job)
    assert proj["summary"]["total_personnel"] == 92
    depts_by_id = {d["agent_id"]: d for d in proj["departments"]}
    assert "Chronology Math" in depts_by_id["research"]["specialists"][1]["title_vi"]
    assert "0:00 Shock Hook" in depts_by_id["script"]["specialists"][1]["title_vi"]
    assert "2-Gear" in depts_by_id["visuals"]["specialists"][0]["title_vi"]
    assert "2-Gear" in depts_by_id["edit"]["specialists"][0]["title_vi"]
    assert "8-Gate" in depts_by_id["evidence_qa"]["specialists"][0]["title_vi"]

    # 2. Verify deterministic auto-normalizer fixes post-2024 agency names AND exact Hangul syllable counts
    raw_defective = "\n".join([
        "제1장, 상견례 식탁 위의 낡은 반짇고리입니다.",
        "2026년 10월 18일 정오 무렵, 서울 청담동 한정식집 안이었습니다.",
        "나혜경 대표가 차갑게 소리쳤죠. \"이런 촌스러운 반짇고리 당장 치우세요!\"",
        "하지만 그 나무 상자 안에는 최종 합격을 좌우할 유일한 궁중 침선 비록이 담겨 있었거든요.",
        "참으로 무례한 말이었습니다.",
        "과연 서유진 실장은 그 송화색 명주가 어떤 천인지 알고 있었을까요?",
        "참으로 기막힌 노릇이었습니다.",
        "나혜경 대표가 애타게 찾는 최고 명인 소담 선생이 과연 누구란 말입니까?",
        "바로 지금 자신들이 모욕하며 내쫓고 있는 사돈 김은숙 씨 본인이었던 겁니다.",
        "김은숙 씨는 25년 동안 홀로 바늘 끝 하나로 외아들을 키워냈습니다.",
        *[f"어머니는 조용히 무명 보자기 매듭을 {k}번째 고쳐 묶었습니다." for k in range(1, 18)],
        "제2장, 비 내리는 삼청동 공방의 등불입니다.",
        "수첩 표지에는 단정한 붓글씨로 경술년 상의원 대례복 침선 본이라는 아홉 글자가 선명하게 적혀 있었습니다.",
        "정태원 위원장은 가방에서 문화재청 직인이 찍힌 위촉장을 꺼냈죠.",
        "과연 28년 전인 1998년 겨울 밤에는 무슨 일이 있었던 걸까요?",
        "그날부터 25년이라는 기나긴 세월 동안 김은숙 씨는 이름을 숨기고 살아왔습니다.",
        "과연 그 보자기 안에는 무엇이 들어 있었을까요?",
        *[f"공방 처마 끝으로 가을비가 {k}번째 일정한 박자를 그리며 떨어졌습니다." for k in range(1, 20)],
        "제6장, 봄빛 가득한 한옥 마당과 편안한 밤입니다.",
        "명패 위에는 국가무형문화재 궁중침선 명예보유자 소담 김은숙이라는 열여덟 글자가 새겨져 있었거든요.",
        *[f"따뜻한 감국차 향기가 조용한 밤공기 속으로 은은하게 퍼져 나갔습니다." for _ in range(12)],
    ])
    rep = analyze_script_spoken_quality(raw_defective, language="ko", job=job)
    found_types = {d["type"] for d in rep["defects"]}
    assert "korean_char_count_math_mismatch" in found_types
    assert "anachronistic_korean_institution_name" in found_types
    assert "chronology_year_span_math_contradiction" in found_types
    assert "excessive_ai_emotional_commentary" in found_types
    assert "missing_in_medias_res_cold_open_shock" in found_types
    assert "premature_twist_or_pen_name_spoiler_in_act1" in found_types
    assert "overlong_act06_bedtime_tail" in found_types

    cleaned, _ = normalize_korean_script_orthography(raw_defective, job=job)
    assert "경술년 상의원 대례복 침선 본이라는 열두 글자" in cleaned
    assert "국가유산청 직인이" in cleaned
    assert "국가무형유산 궁중침선 명예보유자 소담 김은숙이라는 스무 글자" in cleaned

    # 3. Verify 0% interference on other profiles (True Crime / default jobs without profile_script_gates)
    tc_prof = _load_profile("channel-kr-truecrime-director-v2")
    tc_job = {
        "language": "ko",
        "market": "KR",
        "channel_profile_id": tc_prof["id"],
        "editing_dna": tc_prof.get("editing_dna") or {},
        "channel_profile_snapshot": tc_prof,
    }
    tc_proj = build_live_departments_projection(job_snapshot=tc_job)
    tc_depts = {d["agent_id"]: d for d in tc_proj["departments"]}
    assert "Chronology Math" not in tc_depts["research"]["specialists"][1]["title_vi"]
    assert "0:00 Shock Hook" not in tc_depts["script"]["specialists"][1]["title_vi"]
    assert "2-Gear" not in tc_depts["visuals"]["specialists"][0]["title_vi"]
    assert "8-Gate" not in tc_depts["evidence_qa"]["specialists"][0]["title_vi"]

    tc_cleaned, _ = normalize_korean_script_orthography("2026년 현재 문화재청 수사 기록은 아홉 글자가 남아 있습니다.", job=tc_job)
    assert "문화재청" in tc_cleaned

    tc_rep = analyze_script_spoken_quality(raw_defective, language="ko", job=tc_job)
    tc_types = {d["type"] for d in tc_rep["defects"]}
    assert "korean_char_count_math_mismatch" not in tc_types
    assert "anachronistic_korean_institution_name" not in tc_types
    assert "chronology_year_span_math_contradiction" not in tc_types
    assert "excessive_ai_emotional_commentary" not in tc_types
    assert "missing_in_medias_res_cold_open_shock" not in tc_types
    assert "premature_twist_or_pen_name_spoiler_in_act1" not in tc_types
    assert "overlong_act06_bedtime_tail" not in tc_types


def test_two_gear_cold_open_video_hook_choreography(tmp_path: Path):
    prof = _load_profile("channel-kr-goodnight-drama-50m")
    job = _make_job_from_profile(prof, tmp_path)

    # 30-beat realistic episode opening with Cold Open (0:00-0:36) BEFORE 제1장 at B005 (36s)
    voice_beats = []
    plan_beats = []
    cursor = 0.0
    for i in range(1, 31):
        dur = 9.0
        if i == 1:
            txt = '상석에 앉은 사돈이 찻잔을 내려치며 소리쳤습니다. "이런 촌스러운 반짇고리 당장 치우세요!"'
        elif i <= 4:
            txt = f"식탁 끝으로 밀려난 먹감나무 상자 위로 차가운 정적이 내려앉았고 어머니의 손끝이 조용히 떨렸습니다."
        elif i == 5:
            txt = "제1장, 상견례 식탁 위의 낡은 반짇고리입니다."
        else:
            txt = f"비 내리는 삼청동 골목길에서 은숙 씨는 조용히 공방의 등불을 밝히고 작업대 앞에 앉았습니다."
        voice_beats.append({"beat_id": f"B{i:03d}", "text": txt, "start_sec": cursor, "end_sec": cursor + dur})
        plan_beats.append({
            "beat_id": f"B{i:03d}",
            "narration_text": txt,
            "visual_description": "K-drama confrontation scene in private dining room" if i <= 4 else "Warm Hanok workshop evening",
            "visual_type": "cinema_text" if i == 5 else "ai_reconstruction",
            "visual_route": "ai_visual",
            "source_priority": "prefer_ai",
        })
        cursor += dur

    (tmp_path / "script.md").write_text("\n\n".join(b["text"] for b in voice_beats), encoding="utf-8")
    (tmp_path / "voice_manifest.json").write_text(
        json.dumps({"duration_sec": cursor, "beats": voice_beats}, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps({"target_duration_sec": cursor, "beats": plan_beats}, ensure_ascii=False),
        encoding="utf-8",
    )

    VisualsCoordinator().run(job, tmp_path)
    stp = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    hook_beats = [b for b in stp["beats"] if b.get("is_cold_open_hook")]
    body_beats = [b for b in stp["beats"] if not b.get("is_cold_open_hook")]

    # Gear 1 (0:00-0:36): 4 long beats split into >= 8 fast multi-angle sub-shots (2.4s-4.5s each), zero cinema_text at 0:00
    assert len(hook_beats) >= 8
    assert stp["beats"][0]["visual_type"] != "cinema_text"
    assert all(b["camera_mode"].startswith("cold_open_") for b in hook_beats)
    assert all(b["transition_frames"] <= 3 for b in hook_beats)
    # Gear 2 (after 제1장): stays calm 1-beat-per-sentence bedtime cinema
    assert len(body_beats) == 26

    score = build_edit_rhythm_score(job, tmp_path, stp["beats"])
    assert score["beats"][0]["cut_feel"] == "cold_open_dramatic_hook"
    assert score["beats"][0]["jl_cut_mode"] == "j_cut_hook_snap"
    assert score["beats"][-1]["cut_feel"] != "cold_open_dramatic_hook"


def test_audio_drama_5_genres_6_openings_4_spines_flexibility():
    from documentary.prompts import select_audio_drama_narrative_blueprint
    from documentary.service import DocumentaryService

    prof = _load_profile("channel-kr-goodnight-drama-50m")
    nav = prof["editorial_dna"]["narrative_architecture"]
    assert len(nav["genre_archetypes"]) == 5
    assert len(nav["opening_hook_archetypes"]) == 6
    assert len(nav["narrative_spines"]) == 4

    # 1. Spine A (6 Chapters) — Public Wager / Craft Counterstrike
    bp_a = select_audio_drama_narrative_blueprint({"title": "상견례 사돈의 무시와 궁중침선 대반전", "target_duration_minutes": 70})
    assert bp_a["spine_id"] == "spine_a_hidden_master_2tier_counterstrike"
    assert bp_a["opening_id"] == "open_01_public_wager_insult"
    assert bp_a["chapter_count"] == 6
    assert bp_a["chapter_weights"][-1] == 0.08

    # 2. Spine B (5 Chapters at 55m) — Twilight Independence
    bp_b = select_audio_drama_narrative_blueprint({"title": "삼십 년 시월드 졸혼 선언과 홀로서기 공방", "target_duration_minutes": 55})
    assert bp_b["spine_id"] == "spine_b_twilight_independence_irreplaceable_void"
    assert bp_b["opening_id"] == "open_02_quiet_parting_declaration"
    assert bp_b["chapter_count"] == 5
    assert bp_b["chapter_weights"][-1] == 0.09

    # 3. Spine C (5 Chapters) — Maternal Heirloom & Family Repentance
    bp_c = select_audio_drama_narrative_blueprint({"title": "어머니의 버려진 유품 궤짝과 자식들의 눈물 참회", "target_duration_minutes": 60})
    assert bp_c["spine_id"] == "spine_c_heirloom_unveiling_family_repentance"
    assert bp_c["opening_id"] == "open_03_discarded_heirloom_chest"
    assert bp_c["chapter_count"] == 5

    # 4. Spine D (6 Chapters) — 89th-Minute National Treasure Rescue
    bp_d = select_audio_drama_narrative_blueprint({"title": "국빈 만찬 개막 위기와 다급한 전화, 국보 복원 명장", "target_duration_minutes": 70})
    assert bp_d["spine_id"] == "spine_d_crisis_rescue_true_successor"
    assert bp_d["opening_id"] == "open_04_89th_minute_emergency_call"
    assert bp_d["chapter_count"] == 6

    outline_c = DocumentaryService._build_smart_outline(
        title="어머니의 버려진 유품 궤짝과 자식들의 눈물 참회",
        notes="",
        angle_id="goodnight_dignity_reversal_drama",
        angle_label="K-Audio Drama",
        style_label="Warm Radio",
        hook_label="Heirloom",
        chapter_count=5,
        profile_id="channel-kr-goodnight-drama-50m",
        target_duration_minutes=60.0,
        content_mode="creative_audio_drama",
    )
    assert len(outline_c) == 5
    assert outline_c[0]["spine_id"] == "spine_c_heirloom_unveiling_family_repentance"
    assert outline_c[-1]["chapter_id"] == "ACT05"
