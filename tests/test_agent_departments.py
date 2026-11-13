from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from documentary.agent_departments import (
    AGENT_DEPARTMENTS,
    DEPARTMENT_ORDER,
    build_live_departments_projection,
    get_all_departments,
    get_department_for_agent,
)
from documentary.quality import (
    REQUIRED_VOX_MANIFEST_MOTION_FIELDS,
    VOX_BESPOKE_MOTION_INTENTS,
    compute_vox_motion_signature,
    validate_vox_scene_manifest_motion_contract,
)
from documentary.service import DocumentaryService
from server import create_app


def test_all_15_departments_have_lead_deputy_and_specialists():
    depts = get_all_departments()
    assert len(depts) == 15
    assert tuple(d["agent_id"] for d in depts) == DEPARTMENT_ORDER

    for dept in depts:
        lead = dept["lead"]
        deputy = dept["deputy"]
        specialists = dept["specialists"]

        assert lead["rank"] == "lead"
        assert lead["handle"].startswith(f"@{dept['agent_id']}_")
        assert lead["title_vi"]
        assert lead["role_vi"]
        assert len(lead["responsibilities_vi"]) >= 2
        assert lead["approval_output_vi"]

        assert deputy["rank"] == "deputy"
        assert deputy["handle"].startswith(f"@{dept['agent_id']}_")
        assert deputy["title_vi"]
        assert deputy["role_vi"]
        assert len(deputy["checklist_vi"]) >= 2

        assert 4 <= len(specialists) <= 6
        for idx, sp in enumerate(specialists, start=1):
            assert sp["step_order"] == idx
            assert sp["handle"].startswith(f"@{dept['agent_id']}_")
            assert sp["title_vi"]
            assert sp["role_vi"]
            assert sp["task_detail_vi"]
            assert sp["input_from"].startswith("@")
            assert sp["output_to"].startswith("@")
            assert sp["artifact_key"]


def test_vox_department_has_exact_8_member_roster_requested():
    vox_dept = get_department_for_agent("vox")
    assert vox_dept is not None
    assert vox_dept["dept_number"] == "08"
    assert vox_dept["lead"]["handle"] == "@vox_lead"
    assert vox_dept["deputy"]["handle"] == "@vox_deputy"

    spec_handles = [sp["handle"] for sp in vox_dept["specialists"]]
    assert spec_handles == [
        "@vox_voice_reader",
        "@vox_desk_designer",
        "@vox_asset_creator",
        "@vox_motion_designer",
        "@vox_choreography_animator",
        "@vox_spatial_locator",
    ]


def test_live_departments_projection_tracks_working_and_done_states():
    mock_agents = [
        {"id": "vox", "live_state": "working", "progress_pct": 55, "speech_vi": "Đang thiết kế chuyển động độc bản"},
        {"id": "research", "live_state": "done", "progress_pct": 100},
        {"id": "evidence_qa", "live_state": "critiquing", "progress_pct": 80},
    ]
    proj = build_live_departments_projection(mock_agents)
    summary = proj["summary"]
    assert summary["total_departments"] == 15
    assert summary["total_leads"] == 15
    assert summary["total_deputies"] == 15
    assert summary["total_specialists"] == 62
    assert summary["total_personnel"] == 92
    assert summary["active_departments"] == 2
    assert summary["completed_departments"] == 1

    by_agent = {d["agent_id"]: d for d in proj["departments"]}
    vox_live = by_agent["vox"]
    assert vox_live["department_state"] == "working"
    assert vox_live["lead"]["live_state"] == "working"
    assert vox_live["deputy"]["live_state"] == "working"
    assert vox_live["active_mini_agent_handle"] == "@vox_motion_designer"
    assert vox_live["headcount"] == 8
    assert len(vox_live["workflow_chain_vi"]) == 9

    res_live = by_agent["research"]
    assert res_live["department_state"] == "done"
    assert all(sp["live_state"] == "done" for sp in res_live["specialists"])


def test_agent_departments_endpoints_and_ui_wiring(tmp_path: Path):
    svc = DocumentaryService(tmp_path)
    app = create_app(svc)
    client = TestClient(app)

    r1 = client.get("/api/agent-departments")
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["status"] == "ok"
    assert len(d1["departments"]) == 15
    assert d1["summary"]["total_personnel"] == 92

    r1_alias = client.get("/api/agents/departments")
    assert r1_alias.status_code == 200
    assert len(r1_alias.json()["departments"]) == 15

    r2 = client.get("/api/agency/office-live")
    assert r2.status_code == 200
    d2 = r2.json()
    assert len(d2["departments"]) == 15
    assert d2["summary"]["total_departments"] == 15
    vox_ag = next(a for a in d2["agents"] if a["id"] == "vox")
    assert vox_ag["dept_code"] == "DEPT-08"
    assert vox_ag["headcount"] == 8
    assert len(vox_ag["workflow_chain_vi"]) == 9
    assert vox_ag["lead"]["handle"] == "@vox_lead"
    assert vox_ag["deputy"]["handle"] == "@vox_deputy"
    assert len(vox_ag["specialists"]) == 6

    r2_alias = client.get("/api/studio/office-live")
    assert r2_alias.status_code == 200
    assert len(r2_alias.json()["departments"]) == 15

    r3 = client.get("/api/agency/agents/vox")
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["department_hierarchy"]["lead"]["handle"] == "@vox_lead"

    r4 = client.get("/api/state")
    assert r4.status_code == 200
    d4 = r4.json()
    assert len(d4["agent_departments"]) == 15

    root = Path(__file__).resolve().parents[1]
    idx_html = (root / "static" / "index.html").read_text(encoding="utf-8")
    ao_js = (root / "static" / "agent_office.js").read_text(encoding="utf-8")
    ao_css = (root / "static" / "agent_office.css").read_text(encoding="utf-8")

    assert "🏛️ 15 Phòng Ban Chuyên Môn (15 Tổ trưởng · 15 Tổ phó · 62 Chuyên viên Mini-Agents)" in idx_html
    assert 'data-ao-view="departments"' in idx_html
    assert 'data-ao-tab="departments"' in idx_html
    assert "renderDepartmentOrgCard" in ao_js
    assert "dispatchMentionToChat" in ao_js
    assert "data-ao-dispatch-handle" in ao_js
    assert "LUỒNG BÀN GIAO NỘI BỘ" in ao_js
    assert "TẦNG 1 · TỔ TRƯỞNG (LEAD)" in ao_js
    assert "TẦNG 2 · TỔ PHÓ (DEPUTY)" in ao_js
    assert "TẦNG 3 · DÂY CHUYỀN CHUYÊN VIÊN MINI-AGENTS" in ao_js
    assert ".ao-dept-card" in ao_css
    assert ".ao-dept-workflow-box" in ao_css
    assert ".ao-dispatch-btn" in ao_css

    # Neutrality check on agent_departments.py
    dept_py = (root / "documentary" / "agent_departments.py").read_text(encoding="utf-8")
    assert "channel-kr-" not in dept_py
    assert not re.search(r"[\uac00-\ud7a3]", dept_py)


def test_vox_bespoke_motion_contract_blocks_copy_paste_and_passes_unique():
    assert len(VOX_BESPOKE_MOTION_INTENTS) == 12
    assert len(REQUIRED_VOX_MANIFEST_MOTION_FIELDS) == 7

    valid_scenes = [
        {
            "beat_id": "beat_01",
            "voice_meaning": "Hai lời khai về thời điểm rời khỏi hiện trường mâu thuẫn nhau 45 phút.",
            "motion_intent": "EVIDENCE_COLLISION_COMPARE",
            "motion_purpose_for_sentence": "Đẩy 2 bản lời khai va vào nhau để lộ khoảng lệch 45 phút dưới kính lúp.",
            "t1_action": "Trượt 2 biên bản từ trái và phải vào tâm bàn",
            "t2_action": "Quét kính lúp qua dòng giờ giấc và nối chỉ đỏ",
            "t3_action": "Đóng dấu mâu thuẫn đỏ lên khoảng vênh",
            "spatial_lock_targets": [{"target": "timestamp_row", "x": 640, "y": 420}],
            "camera_waypoints": [{"x": 910, "y": 540, "z": 1.0}, {"x": 960, "y": 510, "z": 1.16}, {"x": 1020, "y": 485, "z": 1.24}],
        },
        {
            "beat_id": "beat_02",
            "voice_meaning": "Lớp vỏ bọc doanh nhân từ thiện bị bóc trần, lộ hồ sơ truy nã năm 1998.",
            "motion_intent": "LAYER_PEEL_UNMASK",
            "motion_purpose_for_sentence": "Gạch chéo và lật tấm thẻ tên giả sang bên để lộ lệnh truy nã gốc bên dưới.",
            "t1_action": "Hiển thị hồ sơ vỏ bọc phía trên",
            "t2_action": "Gạch chéo đỏ và trượt tách lớp vỏ bọc sang phải",
            "t3_action": "Lộ ảnh truy nã gốc và đóng dấu xác nhận",
            "spatial_lock_targets": [{"target": "mugshot_seal", "x": 880, "y": 460}],
            "camera_waypoints": [{"x": 960, "y": 530, "z": 1.02}, {"x": 920, "y": 495, "z": 1.18}, {"x": 880, "y": 465, "z": 1.28}],
        },
    ]
    res_ok = validate_vox_scene_manifest_motion_contract({"scenes": valid_scenes})
    assert res_ok["passed"] is True
    assert res_ok["scene_count"] == 2
    assert res_ok["issues"] == []

    # Now test consecutive duplicate motion_intent and copy-pasted camera trajectory
    bad_scenes = [
        dict(valid_scenes[0]),
        {
            **valid_scenes[1],
            "beat_id": "beat_02",
            "motion_intent": "EVIDENCE_COLLISION_COMPARE",  # Duplicate consecutive intent!
            "camera_waypoints": list(valid_scenes[0]["camera_waypoints"]),  # Copy-pasted camera!
            "t1_action": valid_scenes[0]["t1_action"],
            "t2_action": valid_scenes[0]["t2_action"],
            "t3_action": valid_scenes[0]["t3_action"],
        },
    ]
    res_bad = validate_vox_scene_manifest_motion_contract({"scenes": bad_scenes})
    assert res_bad["passed"] is False
    issue_types = {iss["type"] for iss in res_bad["issues"]}
    assert "vox_consecutive_duplicate_motion_intent" in issue_types
    assert "vox_copy_pasted_camera_trajectory" in issue_types
    assert "vox_copy_pasted_motion_signature" in issue_types
