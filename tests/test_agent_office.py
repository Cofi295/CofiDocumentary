from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from documentary.agent_manager import AgentManager
from documentary.agent_office import build_live_office_snapshot
from documentary.critic_loops import analyze_script_spoken_quality
from documentary.nexus_coordinator import NexusCoordinator
import server


ROOT = Path(__file__).resolve().parents[1]


def _make_mock_service(tmp_path: Path, job: dict) -> MagicMock:
    svc = MagicMock()
    svc.root = tmp_path
    svc.agent_manager = AgentManager(ROOT / "agents")
    svc.nexus_coordinator = NexusCoordinator(svc.agent_manager)
    svc.list_jobs.return_value = [job]
    svc.get_job.side_effect = lambda jid: job if jid == job["id"] else None
    svc.find_active_producer_chat_run.return_value = {"active": False}
    svc.list_source_repairs.return_value = []
    return svc


def test_agent_office_core_files_are_100_percent_channel_neutral() -> None:
    files = [
        ROOT / "documentary" / "agent_office.py",
        ROOT / "static" / "agent_office.js",
        ROOT / "static" / "agent_office.css",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "channel-kr-" not in text, f"Hardcoded channel ID leaked into {path.name}"
        has_hangul = any("\uac00" <= ch <= "\ud7a3" for ch in text)
        assert not has_hangul, f"Language-specific Hangul leaked into universal App Core file {path.name}"


def test_office_live_rework_and_handoff_telemetry(tmp_path: Path) -> None:
    ws = tmp_path / "workspaces" / "job-rework-01"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "research.md").write_text("# Verified Dossier\nFact A.\n", encoding="utf-8")
    (ws / "script.md").write_text("Line 1.\n\nLine 2.\n", encoding="utf-8")
    (ws / "visual_manifest.json").write_text(
        json.dumps({"beats": [{"beat_id": "b01", "narration_text": "Line 1."}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (ws / "plan_critic_report.json").write_text(
        json.dumps(
            {
                "phase": "plan",
                "qa_agent": "evidence_qa",
                "paragraph_cadence_rebalanced": True,
                "total_surgical_rewrites": 9,
                "final_sensor": {"status": "PASS", "score": 100, "defects": []},
                "rounds": [
                    {"round": 1, "verdict": "NEEDS_FIX", "applied_rewrites": 9, "summary": "Rewrote monotonous endings"},
                    {"round": 2, "verdict": "PASS", "applied_rewrites": 0, "summary": "Natural broadcast cadence"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    job = {
        "id": "job-rework-01",
        "title": "Test Case Rework Telemetry",
        "status": "running",
        "workspace": str(ws),
        "visual_strategy": "full_ai",
        "phases": {
            "plan": {"status": "succeeded", "error": None},
            "voice": {"status": "running", "error": None},
            "visuals": {"status": "pending", "error": None},
            "footage": {"status": "pending", "error": None},
            "ai_visual": {"status": "pending", "error": None},
            "edit": {"status": "pending", "error": None},
            "seo": {"status": "pending", "error": None},
            "qc": {"status": "pending", "error": None},
        },
    }
    svc = _make_mock_service(tmp_path, job)
    svc.nexus_coordinator.emit_phase_handoff(job, "plan", "voice", ws)

    snap = build_live_office_snapshot(svc, "job-rework-01")
    assert snap["status"] == "ok"
    assert snap["summary"]["total_agents"] == 15
    assert len(snap["divisions"]) == 4
    assert snap["summary"]["reworked_gates"] == 1
    assert snap["summary"]["total_rewrites_or_rerolls"] >= 9
    assert "voice" in snap["summary"]["active_agent_ids"]

    plan_gate = next(g for g in snap["critique_gates"] if g["phase"] == "plan")
    assert plan_gate["gate_state"] == "reworked_and_passed"
    assert plan_gate["rework_triggered"] is True


def test_office_live_rejected_gate_surfaces_blocker(tmp_path: Path) -> None:
    ws = tmp_path / "workspaces" / "job-blocked-01"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "script.md").write_text("Draft\n", encoding="utf-8")

    job = {
        "id": "job-blocked-01",
        "title": "Blocked Case",
        "status": "failed",
        "workspace": str(ws),
        "visual_strategy": "full_ai",
        "phases": {
            "plan": {"status": "failed", "error": "Prosody monotony gate exceeded threshold"},
            "voice": {"status": "pending", "error": None},
        },
    }
    svc = _make_mock_service(tmp_path, job)
    snap = build_live_office_snapshot(svc, "job-blocked-01")

    plan_gate = next(g for g in snap["critique_gates"] if g["phase"] == "plan")
    assert plan_gate["gate_state"] == "rejected"
    assert "Prosody monotony gate" in plan_gate["summary_vi"]

    agents_by_id = {a["id"]: a for a in snap["agents"]}
    assert agents_by_id["evidence_qa"]["live_state"] == "critiquing"
    assert agents_by_id["script"]["live_state"] == "blocked"
    assert any(l["from"] == "evidence_qa" and l["to"] == "script" for l in snap["links"])


def test_live_fastapi_endpoint_and_index_button_wiring(tmp_path: Path) -> None:
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="openAgentOfficeBtn"' in html
    assert 'id="desktopAgentOfficeBtn"' in html
    assert 'id="agentOfficeDialog"' in html
    assert "/static/agent_office.js" in html

    ws = tmp_path / "workspaces" / "job-api-01"
    ws.mkdir(parents=True)
    svc = _make_mock_service(tmp_path, {
        "id": "job-api-01",
        "title": "API Office Test",
        "status": "ready",
        "current_phase": None,
        "workspace": str(ws),
        "visual_strategy": "full_ai",
        "phases": {},
    })
    client = TestClient(server.create_app(svc))
    resp = client.get("/api/agency/office-live")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["summary"]["total_agents"] == 15
    assert len(payload["critique_gates"]) == 8


def test_korean_prosody_sensor_catches_seumnida_monotony() -> None:
    monotonous_lines = [f"{i}번째 수사 기록을 확인했습니다." for i in range(1, 45)]
    text = "\n\n".join(monotonous_lines)
    rep = analyze_script_spoken_quality(text, language="ko")
    assert rep["status"] == "NEEDS_POLISH"
    defect_types = {d["type"] for d in rep["defects"]}
    assert "formal_seumnida_prosody_monotony" in defect_types
    assert "consecutive_formal_seumnida_run" in defect_types
