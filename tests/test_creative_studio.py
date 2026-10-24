from __future__ import annotations

from pathlib import Path
from fastapi.testclient import TestClient

import app as app_module
from documentary.prompts import build_phase_prompt
from documentary.service import DocumentaryService


def _make_client(tmp_path: Path) -> TestClient:
    service = DocumentaryService(tmp_path / "data")
    return TestClient(app_module.create_app(service))


def test_creative_catalog_and_playbooks_crud(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    cat_res = client.get("/api/creative/catalog")
    assert cat_res.status_code == 200
    cat = cat_res.json()
    assert "narrative_angles" in cat
    assert "writing_styles" in cat
    assert "hook_archetypes" in cat
    assert "editing_archetypes" in cat

    pb_res = client.get("/api/playbooks")
    assert pb_res.status_code == 200
    items = pb_res.json()["items"]
    assert len(items) >= 4

    save_res = client.post(
        "/api/playbooks",
        json={
            "name": "Hồ sơ Đế chế Ngầm KR",
            "description": "Phong cách điều tra tài chính Hàn Quốc nhịp nhanh",
            "creative_brief": {
                "narrative_angle": "financial_autopsy",
                "writing_style": "cold_dossier",
                "hook_archetype": "shocking_anomaly",
                "editing_archetypes": ["forensic_red_string", "kinetic_financial_ticker"],
                "custom_rules": "Mỗi chương phải bắt đầu bằng 1 con số tài chính thật.",
            },
        },
    )
    assert save_res.status_code == 200
    saved = save_res.json()
    assert saved["name"] == "Hồ sơ Đế chế Ngầm KR"
    assert saved["built_in"] is False

    del_res = client.delete(f"/api/playbooks/{saved['id']}")
    assert del_res.status_code == 200


def test_pitch_angles_and_two_stage_outline_script_workflow(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    pitch_res = client.post(
        "/api/creative/pitch-angles",
        json={
            "title": "Sự sụp đổ bí ẩn của Tập đoàn Hanjin Shipping",
            "market": "KR",
            "language": "ko",
            "notes": "Tập trung vào các khoản nợ ngầm và chuỗi cung ứng toàn cầu bị đóng băng.",
        },
    )
    assert pitch_res.status_code == 200
    pitches = pitch_res.json()["pitches"]
    assert len(pitches) == 3
    chosen = pitches[0]
    assert chosen["opening_hook"]
    assert len(chosen["chapters"]) >= 3

    create_res = client.post(
        "/api/jobs",
        json={
            "title": chosen["title"],
            "market": "KR",
            "language": "ko",
            "notes": chosen.get("custom_rules", ""),
            "target_duration_minutes": 18,
            "playbook_id": chosen.get("playbook_id") or "kr_forensic_dossier",
            "creative_brief": {
                "narrative_angle": chosen["narrative_angle"],
                "writing_style": chosen["writing_style"],
                "hook_archetype": chosen["hook_archetype"],
                "editing_archetypes": chosen["editing_archetypes"],
                "opening_hook": chosen["opening_hook"],
                "custom_rules": "Cấm mở bài kiểu Wikipedia.",
            },
            "outline": {
                "thesis": chosen.get("why_it_works", ""),
                "opening_hook": chosen["opening_hook"],
                "chapters": chosen["chapters"],
            },
        },
    )
    assert create_res.status_code == 200
    job = create_res.json()
    job_id = job["id"]
    assert job["creative_brief"]["narrative_angle"] == chosen["narrative_angle"]
    assert len(job["outline"]["chapters"]) == len(chosen["chapters"])

    outline_get = client.get(f"/api/jobs/{job_id}/outline")
    assert outline_get.status_code == 200
    assert len(outline_get.json()["outline"]["chapters"]) == len(chosen["chapters"])

    # Update creative brief
    patch_brief = client.patch(
        f"/api/jobs/{job_id}/creative-brief",
        json={
            "playbook_id": "magnates_financial_thriller",
            "creative_brief": {
                "narrative_angle": "financial_autopsy",
                "writing_style": "cinematic_thriller",
                "hook_archetype": "in_media_res",
                "editing_archetypes": ["kinetic_financial_ticker"],
                "opening_hook": "03:00 sáng tại cảng Busan, 90 siêu tàu container bị từ chối cập cảng.",
                "custom_rules": "Giữ nhịp căng thẳng như phim điện ảnh.",
            },
        },
    )
    assert patch_brief.status_code == 200
    assert patch_brief.json()["creative_brief"]["writing_style"] == "cinematic_thriller"

    # Regenerate outline via AI helper
    gen_outline = client.post(
        f"/api/jobs/{job_id}/outline/generate",
        json={"instruction": "Thêm chương về hệ lụy chuỗi cung ứng", "chapter_count": 5},
    )
    assert gen_outline.status_code == 200
    assert len(gen_outline.json()["outline"]["chapters"]) == 5

    # Verify prompt injection includes Creative Brief & Outline Blueprint
    updated_job = client.get(f"/api/jobs/{job_id}").json()
    plan_prompt = build_phase_prompt(updated_job, "plan", updated_job["workspace"], tmp_path)
    assert "CREATIVE BRIEF & DIRECTORIAL BLUEPRINT" in plan_prompt
    assert "APPROVED CHAPTER OUTLINE BLUEPRINT" in plan_prompt
    assert "03:00 sáng tại cảng Busan" in plan_prompt

    # Save direct script.md edit
    script_put = client.put(
        f"/api/jobs/{job_id}/script",
        json={"script": "# Chương 1: Đêm đóng băng tại cảng Busan\n\n90 con tàu khổng lồ bỗng chốc trở thành nhà tù nổi..."},
    )
    assert script_put.status_code == 200
    art_res = client.get(f"/api/jobs/{job_id}/artifact/script.md")
    assert art_res.status_code == 200
    assert "Đêm đóng băng tại cảng Busan" in art_res.text

    # Extract playbook from job
    ext_res = client.post(
        f"/api/jobs/{job_id}/extract-playbook",
        json={"name": "Playbook Hanjin Thriller"},
    )
    assert ext_res.status_code == 200
    assert ext_res.json()["name"] == "Playbook Hanjin Thriller"


def test_live_draft_sync_and_open_ended_creative_workflow(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    # 1. Live sync draft from AI chat while brainstorming (zero-button live sync)
    draft_res = client.post(
        "/api/creative/draft",
        json={
            "title": "Bí mật mạng lưới cáp ngầm Thái Bình Dương",
            "narrative_angle": "Giải phẫu địa chính trị kết hợp nhật ký kỹ sư tàu cáp ngầm",
            "writing_style": "Điện ảnh điều tra kết hợp sơ đồ 3D kiểu Lemmino × Vox",
            "hook_archetype": "Tín hiệu đứt gãy lúc 02:14 sáng ở độ sâu 4.000m",
            "editing_archetypes": "Bản đồ sonar 3D, Sơ đồ kỹ thuật giải phẫu, Hồ sơ giải mật",
            "opening_hook": "Ở độ sâu 4.000 mét dưới đáy biển Luzon, một sợi ống mảnh bằng ngón tay cái đang gánh 95% dòng tiền liên lục địa.",
            "custom_rules": "Mỗi chương mở đầu bằng tọa độ hải lý thật.",
            "chapters": [
                {
                    "title": "Chương 1: Sợi chỉ mảnh dưới vực sâu Luzon",
                    "estimated_minutes": 4,
                    "summary": "Giải thích điểm nghẽn địa lý nơi 14 tuyến cáp đi qua.",
                    "evidence_anchor": "Bản đồ TeleGeography 2025",
                    "visual_note": "Bản đồ 3D đáy biển + Zoom điểm nghẽn",
                }
            ],
        },
    )
    assert draft_res.status_code == 200
    draft = draft_res.json()
    assert draft["title"] == "Bí mật mạng lưới cáp ngầm Thái Bình Dương"
    assert "Lemmino" in draft["writing_style"]

    get_draft = client.get("/api/creative/draft")
    assert get_draft.status_code == 200
    assert get_draft.json()["opening_hook"].startswith("Ở độ sâu 4.000 mét")

    # 2. Create job directly from agreed chat parameters (open-ended fields)
    create_res = client.post(
        "/api/jobs",
        json={
            "title": draft["title"],
            "market": "US",
            "language": "en",
            "narrative_angle": draft["narrative_angle"],
            "writing_style": draft["writing_style"],
            "hook_archetype": draft["hook_archetype"],
            "editing_archetypes": draft["editing_archetypes"],
            "opening_hook": draft["opening_hook"],
            "custom_rules": draft["custom_rules"],
            "outline": {"chapters": draft["chapters"]},
            "start_plan": False,
        },
    )
    assert create_res.status_code == 200
    job = create_res.json()
    assert job["creative_brief"]["narrative_angle"] == draft["narrative_angle"]
    assert job["creative_brief"]["writing_style"] == draft["writing_style"]
    assert "Bản đồ sonar 3D" in job["creative_brief"]["editing_archetypes"]
    assert len(job["outline"]["chapters"]) == 1


