from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import create_app
from documentary.prompts import build_phase_prompt
from documentary.quality import normalize_production_recipe
from documentary.service import DocumentaryService


def test_normalize_production_recipe_supports_hybrid_visual_strategy():
    default_recipe = normalize_production_recipe(None, target_duration_minutes=5)
    assert default_recipe.get("visual_strategy") == "full_footage"
    assert default_recipe.get("quality_contract", {}).get("visual_strategy") == "full_footage"

    hybrid_recipe = normalize_production_recipe(None, target_duration_minutes=5, visual_strategy="hybrid")
    assert hybrid_recipe.get("visual_strategy") == "hybrid"
    contract = hybrid_recipe.get("quality_contract", {})
    assert contract.get("visual_strategy") == "hybrid"
    assert "target_ai_visual_ratio" not in contract
    assert "target_real_footage_ratio" not in contract
    assert contract.get("visual_routing_policy") == "story_driven"
    assert "fixed ratio" in " ".join(hybrid_recipe.get("asset_rules", [])).lower()


def test_service_create_job_initializes_hybrid_strategy(tmp_path: Path):
    service = DocumentaryService(tmp_path)
    job = service.create_job({
        "title": "Chủ quyền đại dương",
        "visual_strategy": "hybrid",
        "target_duration_minutes": 5,
    })
    assert job["visual_strategy"] == "hybrid"
    assert job["production_recipe"]["visual_strategy"] == "hybrid"
    assert job["production_recipe"]["quality_contract"]["visual_strategy"] == "hybrid"
    assert job["production_recipe"]["quality_contract"]["visual_routing_policy"] == "story_driven"

    workspace = Path(job["workspace"])
    saved_input = json.loads((workspace / "input.json").read_text(encoding="utf-8"))
    assert saved_input["visual_strategy"] == "hybrid"

    fetched = service.get_job(job["id"])
    assert fetched["visual_strategy"] == "hybrid"


def test_service_create_job_defaults_to_full_footage(tmp_path: Path):
    service = DocumentaryService(tmp_path)
    job = service.create_job({"title": "Default Strategy"})
    assert job["visual_strategy"] == "full_footage"
    assert job["production_recipe"]["visual_strategy"] == "full_footage"


def test_service_create_job_rejects_invalid_visual_strategy(tmp_path: Path):
    service = DocumentaryService(tmp_path)
    with pytest.raises(ValueError, match="visual_strategy"):
        service.create_job({"title": "Invalid Strategy", "visual_strategy": "unknown_mode"})


def test_plan_prompt_includes_hybrid_story_guidance(tmp_path: Path):
    job = {
        "id": "job-hybrid-1",
        "title": "Bão cát Sahara",
        "language": "vi",
        "market": "VN",
        "visual_strategy": "hybrid",
        "production_recipe": normalize_production_recipe(None, target_duration_minutes=5, visual_strategy="hybrid"),
    }
    prompt = build_phase_prompt(job, "plan", tmp_path / "workspace", tmp_path / "remotion")
    assert "HYBRID" in prompt
    assert "STORY DRIVEN" in prompt
    assert "no fixed percentage" in prompt.lower()


def test_api_create_job_with_hybrid_strategy(tmp_path: Path):
    service = DocumentaryService(tmp_path)
    app = create_app(service)
    client = TestClient(app)

    response = client.post("/api/jobs", json={
        "title": "Đại hồng thủy Nepal",
        "visual_strategy": "hybrid",
        "target_duration_minutes": 5,
    })
    assert response.status_code == 200, response.text
    created = response.json()
    assert created["visual_strategy"] == "hybrid"

    detail = client.get(f"/api/jobs/{created['id']}").json()
    assert detail["visual_strategy"] == "hybrid"


def test_ui_contains_hybrid_visual_strategy_choice():
    html = Path("static/index.html").read_text(encoding="utf-8")
    assert 'name="visual_strategy"' in html
    assert 'value="full_ai"' in html
    assert 'value="full_footage"' in html
    assert 'value="hybrid"' in html
    assert 'value="evidence_footage"' in html
    assert "80% AI Visual" not in html
    assert "20% Footage thật" not in html

    js = Path("static/app.js").read_text(encoding="utf-8")
    assert "visual_strategy" in js
    assert "evidence_footage" in js


def test_evidence_footage_strategy(tmp_path: Path):
    from documentary.visuals import _route_for
    service = DocumentaryService(tmp_path)
    job = service.create_job({
        "title": "Chuyên án 1996",
        "visual_strategy": "evidence_footage",
        "target_duration_minutes": 5,
    })
    assert job["visual_strategy"] == "evidence_footage"
    assert job["production_recipe"]["visual_strategy"] == "evidence_footage"
    assert "Strict evidence-first routing" in job["production_recipe"]["asset_rules"][0]

    # Alias evidence_first normalizes to evidence_footage
    job_alias = service.create_job({
        "title": "Chuyên án Alias",
        "visual_strategy": "evidence_first",
        "target_duration_minutes": 5,
    })
    assert job_alias["visual_strategy"] == "evidence_footage"

    # Korean: Must real with real person ID / authentic portrait routes to footage
    route_ev_kr = _route_for("evidence_footage", "must_real", metadata={"source_priority": "must_real", "visual_description": "피해자 댜오아이칭의 생전 유일한 증명사진"})
    assert route_ev_kr == "footage"

    # Korean: Must real with interview of parents / court video routes to footage
    route_interview_kr = _route_for("evidence_footage", "must_real", metadata={"source_priority": "must_real", "visual_description": "눈물을 훔치는 노부모의 인터뷰 아카이브 영상"})
    assert route_interview_kr == "footage"

    # Korean: Generic atmospheric scene routes to ai_visual
    route_atmo_kr = _route_for("evidence_footage", "must_real", metadata={"source_priority": "must_real", "visual_description": "눈 덮인 겨울 거리 풍경과 자전거"})
    assert route_atmo_kr == "ai_visual"

    # Korean: Generic investigation actions / diagrams / monitors route to ai_visual
    route_diag_kr = _route_for("evidence_footage", "must_real", metadata={"source_priority": "must_real", "visual_description": "수사 기록용 도해와 법의학 스케치 분석 그래픽"})
    assert route_diag_kr == "ai_visual"
    route_board_kr = _route_for("evidence_footage", "must_real", metadata={"source_priority": "must_real", "visual_description": "형사들이 상황판 앞에서 회의하는 모습"})
    assert route_board_kr == "ai_visual"

    # Vietnamese: Authentic ID / interview routes to footage
    route_ev_vi = _route_for("evidence_footage", "must_real", metadata={"source_priority": "must_real", "visual_description": "Ảnh thẻ căn cước và chân dung thật của nạn nhân"})
    assert route_ev_vi == "footage"

    # Vietnamese: Generic atmospheric street / props route to ai_visual
    route_atmo_vi = _route_for("evidence_footage", "must_real", metadata={"source_priority": "must_real", "visual_description": "Đoạn đường ngõ tối dưới ánh đèn đường mùa đông xe đạp"})
    assert route_atmo_vi == "ai_visual"

    # English: Mugshot / official court filing routes to footage
    route_ev_en = _route_for("evidence_footage", "must_real", metadata={"source_priority": "must_real", "visual_description": "Official victim ID photo and court filing with official seal"})
    assert route_ev_en == "footage"

    # English: Dark alley / boiler steam routes to ai_visual
    route_atmo_en = _route_for("evidence_footage", "must_real", metadata={"source_priority": "must_real", "visual_description": "Dark alley in winter night with steam rising from boiler"})
    assert route_atmo_en == "ai_visual"

    # Prefer real always routes to ai_visual in evidence_footage mode
    route_prefer = _route_for("evidence_footage", "prefer_real", metadata={"source_priority": "prefer_real", "visual_description": "자전거를 탄 남성의 그림자"})
    assert route_prefer == "ai_visual"

    # Plan prompt contains dedicated instructions
    plan_prompt = build_phase_prompt(job, "plan", tmp_path / "workspace", tmp_path / "remotion")
    assert "EVIDENCE + AI VISUAL STRATEGY" in plan_prompt
    assert "STRICT EVIDENCE-FIRST" in plan_prompt


def test_edit_direct_footage_semi_content_skips_step4_and_delegates_broll_to_edit(tmp_path):
    from documentary.footage import build_preflight
    from documentary.models import effective_phases
    from documentary.visuals import VisualsCoordinator

    service = DocumentaryService(tmp_path)
    job = service.create_job({
        "title": "은혜의 편지 60분",
        "market": "KR",
        "language": "ko",
        "visual_strategy": "edit_direct_footage",
        "target_duration_minutes": 60,
        "ai_media_mode": "image",
    })
    assert job["visual_strategy"] == "edit_direct_footage"
    assert effective_phases(job) == ("plan", "voice", "visuals", "ai_visual", "edit", "seo", "qc")

    workspace = Path(job["workspace"])
    beats = []
    voice_beats = []
    for idx in range(1, 15):
        bid = f"B{idx:03d}"
        text = f"내 사랑하는 아이야, 오늘 하루도 참 고생 많았구나. 구절 {idx}의 위로와 평안이 함께하리라."
        beats.append({
            "beat_id": bid,
            "story_group": f"G{(idx - 1) // 3 + 1:02d}",
            "narration_text": text,
            "target_duration_sec": 16,
            "visual_type": "sourced_video",
            "source_priority": "prefer_real",
            "visual_description": f"Cinematic Korean sunrise over misty pine mountains scene {idx}",
            "footage_search_queries": [f"Korean misty pine mountain sunrise 4k {idx}"],
        })
        voice_beats.append({
            "beat_id": bid,
            "text": text,
            "start_sec": float((idx - 1) * 16),
            "end_sec": float(idx * 16),
            "duration_sec": 16.0,
        })
    (workspace / "script.md").write_text(
        "\n\n".join(b["narration_text"] for b in beats),
        encoding="utf-8",
    )
    (workspace / "visual_manifest.json").write_text(
        json.dumps({"target_duration_sec": 3600, "beats": beats}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (workspace / "voice_manifest.json").write_text(
        json.dumps({"status": "ready", "beats": voice_beats}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    VisualsCoordinator().run(job, workspace)
    manifest = json.loads((workspace / "visual_manifest.json").read_text(encoding="utf-8"))
    routes = [item["visual_route"] for item in manifest["beats"]]
    ai_beats = [item for item in manifest["beats"] if item["visual_route"] == "ai_visual"]
    footage_beats = [item for item in manifest["beats"] if item["visual_route"] == "footage"]
    assert len(ai_beats) >= 2
    assert len(footage_beats) > len(ai_beats)
    assert len(ai_beats) <= len(manifest["beats"]) // 3

    preflight = build_preflight(workspace)
    assert preflight["missing_beats"] == [b["beat_id"] for b in ai_beats]
    matrix = json.loads((workspace / "coverage_matrix.json").read_text(encoding="utf-8"))
    delegated = [row for row in matrix["beats"] if row.get("delegated_to_edit_agent")]
    assert len(delegated) == len(footage_beats)
    assert all(row["covered"] for row in delegated)

    edit_prompt = build_phase_prompt(job, "edit", workspace, tmp_path / "remotion")
    assert "SEMI-CONTENT / EDIT-DIRECT FOOTAGE MODE" in edit_prompt
    assert "documentary.edit_footage_fetcher" in edit_prompt


def test_one_collapsible_right_chat_panel_is_shared_by_the_whole_app():
    html = Path("static/index.html").read_text(encoding="utf-8")
    css = Path("static/styles.css").read_text(encoding="utf-8")
    js = Path("static/app.js").read_text(encoding="utf-8")

    assert html.count('id="globalCodexDock"') == 1
    assert 'data-app-tab="codex"' not in html
    assert 'data-app-pane="codex"' not in html
    assert 'id="editChatForm"' not in js
    assert "body.global-chat-open .app-shell" in css
    assert 'localStorage.setItem("cofi-global-chat-open"' in js
