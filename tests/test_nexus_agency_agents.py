"""Comprehensive tests for the NEXUS 13-Specialist Multi-Agent Architecture (`agents/<division>/<id>.md`)."""
from __future__ import annotations

import json
from pathlib import Path
import re

from fastapi.testclient import TestClient

from documentary.agent_manager import AgentManager
from documentary.codex_gateway import StageResult
from documentary.nexus_coordinator import NexusCoordinator
from documentary.prompts import build_phase_prompt
from documentary.service import DocumentaryService
from documentary.store import JobStore
from server import create_app


DOC_ROOT = Path(__file__).resolve().parents[1]
REMOTION_ROOT = DOC_ROOT.parent / "CofiRemotion"


def _make_service(tmp_path: Path) -> DocumentaryService:
    root = tmp_path / "app"
    remotion = tmp_path / "remotion"
    remotion.mkdir(parents=True, exist_ok=True)
    return DocumentaryService(
        root=root,
        store=JobStore(root / "data" / "jobs"),
        remotion_dir=remotion,
    )


def test_standalone_13_agent_corpus_lint_and_distinct_identities():
    manager = AgentManager()
    lint = manager.lint_corpus()
    assert lint["passed"] is True, f"Corpus lint errors: {lint['errors']}"
    assert lint["agent_count"] == 15
    assert lint["division_count"] == 4
    assert lint["runbook_count"] == 4

    roster = manager.list_agents()
    ids = [item["id"] for item in roster]
    assert ids == [
        "orchestrator",
        "radar",
        "research",
        "script",
        "voice",
        "visuals",
        "footage",
        "ai_visual",
        "vox",
        "edit",
        "seo",
        "evidence_qa",
        "qc",
        "dev",
        "debug",
    ]

    vibes = {item["vibe"] for item in roster}
    missions = {item["mission"] for item in roster}
    source_paths = {item["source_path"] for item in roster}
    assert len(vibes) == 15, "Every agent must have a unique personality vibe"
    assert len(missions) == 15, "Every agent must have a unique core mission"
    assert len(source_paths) == 15, "Every agent must live in its own standalone .md file"

    # Phase-to-specialist routing accuracy (including fixed `seo` -> `seo`)
    assert manager.for_phase("plan").id == "script"
    assert manager.for_phase("voice").id == "voice"
    assert manager.for_phase("visuals").id == "visuals"
    assert manager.for_phase("footage").id == "footage"
    assert manager.for_phase("ai_visual").id == "ai_visual"
    assert manager.for_phase("edit").id == "edit"
    assert manager.for_phase("seo").id == "seo"
    assert manager.for_phase("qc").id == "qc"


def test_lazy_router_search_inspect_and_language_safe_bound_skills():
    manager = AgentManager()

    # Compact summary excludes full markdown body to protect Orchestrator context window
    summaries = manager.list_agents()
    assert all("body" not in item and "soul_markdown" not in item for item in summaries)

    # Full inspection loads SOUL + OPERATIONS on demand
    qc_full = manager.inspect_agent("reality_checker", include_body=True)
    assert qc_full["id"] == "qc"
    assert "NEEDS WORK" in qc_full["body"]
    assert len(qc_full["soul_markdown"]) > 100
    assert len(qc_full["operations_markdown"]) > 100

    # Keyword discovery ranks domain specialists accurately
    edit_hits = manager.search_agents("remotion subtitle lufs master timeline", limit=3)
    assert edit_hits and edit_hits[0]["id"] in {"edit", "vox"}

    vox_hits = manager.search_agents("esri satellite gis whisper words 2.5d", limit=3)
    assert vox_hits and vox_hits[0]["id"] == "vox"

    radar_hits = manager.search_agents("outlier topic_memory channel_profile_today", limit=3)
    assert radar_hits and radar_hits[0]["id"] == "radar"

    footage_hits = manager.search_agents("3-frame watermark archival footage", limit=3)
    assert footage_hits and footage_hits[0]["id"] in {"footage", "evidence_qa"}

    # Bound skills strip Hangul & hardcoded channel-* IDs for non-Korean jobs
    en_skills = manager.resolve_bound_skills("script", target_language="en")
    assert len(en_skills) >= 1
    for sk in en_skills:
        assert not re.search(r"[\uac00-\ud7a3]", sk["excerpt"]), f"Hangul leaked in {sk['skill']}"
        assert "channel-" not in sk["excerpt"]


def test_least_privilege_directory_action_and_artifact_permission_guards(tmp_path: Path):
    manager = AgentManager()
    app_root = tmp_path / "app_root"
    ws = tmp_path / "ws_ep01"
    app_root.mkdir()
    ws.mkdir()

    # 1. Execution CWD scoping
    assert manager.resolve_execution_cwd("dev", app_root, ws) == (app_root.resolve(), False)
    assert manager.resolve_execution_cwd("debug", app_root, ws) == (app_root.resolve(), False)
    assert manager.resolve_execution_cwd("orchestrator", app_root, ws) == (app_root.resolve(), False)
    assert manager.resolve_execution_cwd("voice", app_root, ws) == (ws.resolve(), False)
    assert manager.resolve_execution_cwd("edit", app_root, ws) == (ws.resolve(), True)

    # 2. Hard action & phase allowlist filtering
    permitted, blocked = manager.filter_proposed_actions(
        "voice",
        [
            {"type": "run_phase", "job_id": "j1", "phase": "voice"},
            {"type": "run_phase", "job_id": "j1", "phase": "qc"},  # wrong phase for voice!
            {"type": "repair_code", "reason": "hack source"},      # dev-only action!
        ],
    )
    assert permitted == [{"type": "run_phase", "job_id": "j1", "phase": "voice"}]
    assert len(blocked) == 2

    # EvidenceQA & QC are read/audit gates — cannot propose mutating pipeline runs
    qa_perm, qa_blocked = manager.filter_proposed_actions(
        "evidence_qa",
        [{"type": "run_phase", "job_id": "j1", "phase": "edit"}],
    )
    assert qa_perm == []
    assert len(qa_blocked) == 1

    # 3. Scoped readable artifacts & post-execution write audit
    (ws / "input.json").write_text("{}", encoding="utf-8")
    (ws / "script.md").write_text("Narration", encoding="utf-8")
    (ws / "seo_package.json").write_text("{}", encoding="utf-8")

    scoped_voice_ctx = manager.build_scoped_context("voice", {"workspace_path": str(ws)}, ws)
    visible = scoped_voice_ctx["scoped_readable_artifacts"]
    assert "script.md" in visible
    assert "input.json" in visible
    assert "seo_package.json" not in visible

    before = manager.snapshot_workspace_files(ws)
    (ws / "voice_manifest.json").write_text('{"beats":[]}', encoding="utf-8")
    audit_ok = manager.verify_artifact_write_permissions("voice", ws, before)
    assert audit_ok["compliant"] is True
    assert audit_ok["authorized_writes"] == ["voice_manifest.json"]

    # Now simulate unauthorized write to final_manifest.json by `voice`
    (ws / "final_manifest.json").write_text('{"forged":true}', encoding="utf-8")
    audit_bad = manager.verify_artifact_write_permissions("voice", ws, before)
    assert audit_bad["compliant"] is False
    assert "final_manifest.json" in audit_bad["unauthorized_writes"]


def test_nexus_phase_handoff_ledger_and_us_english_prompt_neutrality(tmp_path: Path):
    coord = NexusCoordinator()
    ws = tmp_path / "us_ep_ws"
    ws.mkdir(parents=True)
    (ws / "outline.json").write_text(json.dumps({"chapters": [{"chapter": 1}, {"chapter": 2}]}), encoding="utf-8")
    (ws / "research.md").write_text("Verified US engineering archive.", encoding="utf-8")
    (ws / "script.md").write_text("In nineteen seventy-six, the dam wall shifted.", encoding="utf-8")
    (ws / "visual_manifest.json").write_text(
        json.dumps({"beats": [{"beat_id": "B001", "is_verbatim_quote": True}]}),
        encoding="utf-8",
    )

    us_job = {
        "id": "job_us_nexus_01",
        "channel_profile_id": "channel-us-clean",
        "market": "US",
        "language": "en",
        "visual_strategy": "full_footage",
        "target_duration_minutes": 15,
    }
    pkt = coord.emit_phase_handoff(us_job, "plan", "voice", ws)
    assert pkt["from_agent"] == "script"
    assert pkt["to_agent"] == "voice"
    assert pkt["upstream_metrics"]["chapter_count"] == 2
    assert pkt["upstream_metrics"]["tagged_verbatim_quotes"] == 1
    assert (ws / ".producer" / "nexus_handoffs" / "plan_to_voice.json").is_file()
    assert (ws / ".producer" / "nexus_handoffs" / "plan_to_voice.md").is_file()
    assert (ws / ".producer" / "qa_verdicts" / "phase_plan.json").is_file()
    assert (ws / ".producer" / "nexus_ledger.json").is_file()

    # Now emit voice -> footage handoff and verify `build_phase_prompt` for `footage`
    # injects the Specialist Charter + Upstream Handoff with ZERO Hangul and ZERO channel-* leaks!
    (ws / "voice_manifest.json").write_text(
        json.dumps({"beats": [{"beat_id": "B001", "end_sec": 12.4}]}),
        encoding="utf-8",
    )
    (ws / "narration.srt").write_text("1\n00:00:00,000 --> 00:00:12,400\nLine\n", encoding="utf-8")
    coord.emit_phase_handoff(us_job, "voice", "footage", ws)

    footage_prompt = build_phase_prompt(us_job, "footage", ws, REMOTION_ROOT)
    assert "NEXUS SPECIALIST OPERATING CHARTER (agents/visual_cinema/footage.md)" in footage_prompt
    assert "UPSTREAM NEXUS HANDOFF INTO `FOOTAGE`:" in footage_prompt
    assert "12.4" in footage_prompt
    assert not re.search(r"[\uac00-\ud7a3]", footage_prompt)
    assert "channel-us-clean" not in footage_prompt


def test_single_model_maker_evidence_qa_closed_retry_loop(tmp_path: Path):
    """Verify 1 single LLM model operates as Maker + EvidenceQA in a closed retry loop (FAIL -> fix -> PASS)."""
    service = _make_service(tmp_path)
    job = service.create_job({"title": "NEXUS Closed Loop Test", "market": "US", "language": "en"})

    class SingleModelCollectiveGateway:
        def __init__(self) -> None:
            self.maker_attempts = 0
            self.qa_attempts = 0
            self.maker_prompts: list[str] = []

        def run_prompt_reusable(self, prompt: str, workspace: Path, label: str, **kwargs) -> StageResult:
            if label.startswith("agent-"):
                self.maker_attempts += 1
                self.maker_prompts.append(prompt)
                if self.maker_attempts == 1:
                    payload = {
                        "status": "completed",
                        "report": "Bản nháp lần 1 còn sót số chưa chuẩn hóa.",
                        "deliverables": ["script.md"],
                        "handoff_notes": "Draft 1",
                        "proposed_actions": [
                            {"type": "run_phase", "job_id": job["id"], "phase": "plan"},
                            {"type": "repair_code", "reason": "out_of_scope_for_script"},
                        ],
                    }
                else:
                    payload = {
                        "status": "completed",
                        "report": "Bản nháp lần 2 đã sửa sạch lỗi số đếm theo phản biện của EvidenceQA.",
                        "deliverables": ["script.md", "outline.json"],
                        "handoff_notes": "100% ear-ready prose verified for Voice synthesis.",
                        "proposed_actions": [{"type": "run_phase", "job_id": job["id"], "phase": "plan"}],
                    }
                return StageResult(0, json.dumps(payload, ensure_ascii=False), Path(workspace) / label)

            if label.startswith("qa-verify-"):
                self.qa_attempts += 1
                if self.qa_attempts == 1:
                    verdict = {
                        "verdict": "FAIL",
                        "summary": "Còn sót ký hiệu % chưa bung thành chữ đọc tự nhiên ở đoạn 2.",
                        "issues": [{"severity": "high", "target": "script.md:L14", "fix_instruction": "Expand % into spoken words."}],
                    }
                else:
                    verdict = {"verdict": "PASS", "summary": "Đã kiểm tra thực tế: 100% đạt chuẩn.", "issues": []}
                return StageResult(0, json.dumps(verdict, ensure_ascii=False), Path(workspace) / label)

            if "reviewing a specialist's report" in prompt:
                return StageResult(0, json.dumps({"actions": []}), Path(workspace) / label)

            if "VERIFIED EXECUTION EVIDENCE" in prompt:
                return StageResult(0, "Kịch bản đã qua vòng phản biện EvidenceQA và hoàn tất.", Path(workspace) / label)

            return StageResult(
                0,
                json.dumps({
                    "reply": "Giao Lead Showrunner xử lý kèm cổng kiểm định EvidenceQA.",
                    "actions": [{
                        "type": "delegate_agent",
                        "agent_id": "script",
                        "task": "Rà soát và chuẩn hóa kịch bản trước thu âm",
                        "job_id": job["id"],
                        "verify_with_qa": True,
                    }],
                }, ensure_ascii=False),
                Path(workspace) / label,
            )

    gw = SingleModelCollectiveGateway()
    service.gemini_gateway = gw

    res = service.producer_chat("Rà soát kịch bản kỹ lưỡng trước khi thu âm", selected_job_id=job["id"], locked_provider="gemini")
    delegated = res["actions"][0]

    assert gw.maker_attempts == 2
    assert gw.qa_attempts == 2
    assert "NEXUS MAKER-QA RETRY FEEDBACK (ATTEMPT 2 OF 3)" in gw.maker_prompts[1]
    assert "Expand % into spoken words." in gw.maker_prompts[1]
    assert delegated["status"] == "reported"
    assert delegated["qa_verdict"] == "PASS"
    assert delegated["attempts"] == 2
    # Out-of-scope `repair_code` proposed on attempt 1 was filtered; attempt 2 had 0 blocked actions
    assert delegated["blocked_actions"] == []

    # Check distributed trace log recorded in project workspace
    ledger_state = service.nexus_coordinator.get_project_nexus_state(job["workspace"])
    trace_agents = [t["agent_id"] for t in ledger_state["traces"]]
    assert "script" in trace_agents
    assert "evidence_qa" in trace_agents


def test_delegate_squad_chains_handoff_packets_across_specialists(tmp_path: Path):
    """Verify `delegate_squad` chains `research -> script -> seo` over 1 model with structured handoff continuity."""
    service = _make_service(tmp_path)
    job = service.create_job({"title": "NEXUS Squad Chain", "market": "US", "language": "en"})

    captured_worker_prompts: dict[str, str] = {}

    class SquadGateway:
        def run_prompt_reusable(self, prompt: str, workspace: Path, label: str, **kwargs) -> StageResult:
            if label.startswith("agent-"):
                if "Agent ID: `research`" in prompt:
                    captured_worker_prompts["research"] = prompt
                    out = {
                        "status": "completed",
                        "report": "Đã khóa 4 mốc thời gian và nguồn tòa án xác thực.",
                        "deliverables": ["research.md"],
                        "handoff_notes": "Lock exact dates 1998-04-12 and 2003-11-09; do not invent witness dialogue.",
                        "proposed_actions": [],
                    }
                elif "Agent ID: `script`" in prompt:
                    captured_worker_prompts["script"] = prompt
                    out = {
                        "status": "completed",
                        "report": "Đã lên khung 5 hồi khớp 100% hồ sơ nghiên cứu.",
                        "deliverables": ["outline.json", "script.md"],
                        "handoff_notes": "Central paradox: inspector lived next door for 5 years; never spoil final verdict on thumbnail.",
                        "proposed_actions": [],
                    }
                else:
                    captured_worker_prompts["seo"] = prompt
                    out = {
                        "status": "completed",
                        "report": "Đã thiết kế gói Tiêu đề + Thumbnail bất đối xứng không lộ kết cục.",
                        "deliverables": ["seo_package.json"],
                        "handoff_notes": "Ready for packaging review.",
                        "proposed_actions": [],
                    }
                return StageResult(0, json.dumps(out, ensure_ascii=False), Path(workspace) / label)

            if "VERIFIED EXECUTION EVIDENCE" in prompt:
                return StageResult(0, "Tổ 3 chuyên gia Research -> Script -> SEO đã phối hợp hoàn tất.", Path(workspace) / label)

            return StageResult(
                0,
                json.dumps({
                    "reply": "Kích hoạt tổ chuyên gia Research -> Script -> SEO.",
                    "actions": [{
                        "type": "delegate_squad",
                        "agents": ["research", "script", "seo"],
                        "task": "Xây dựng hồ sơ, kịch bản và phương án đóng gói đồng bộ",
                        "job_id": job["id"],
                        "verify_with_qa": False,
                    }],
                }, ensure_ascii=False),
                Path(workspace) / label,
            )

    service.gemini_gateway = SquadGateway()
    res = service.producer_chat("Phối hợp tổ Research, Script và SEO cho dự án này", selected_job_id=job["id"], locked_provider="gemini")

    squad_action = res["actions"][0]
    assert squad_action["type"] == "delegate_squad"
    assert squad_action["status"] == "reported"
    assert squad_action["agents"] == ["research", "script", "seo"]
    assert len(squad_action["hops"]) == 3

    # Verify upstream handoff notes propagated tightly from Research -> Script -> SEO!
    assert "Lock exact dates 1998-04-12 and 2003-11-09" in captured_worker_prompts["script"]
    assert "Central paradox: inspector lived next door for 5 years" in captured_worker_prompts["seo"]

    ws = Path(job["workspace"])
    assert (ws / ".producer" / "nexus_handoffs" / "squad_research_to_script.json").is_file()
    assert (ws / ".producer" / "nexus_handoffs" / "squad_script_to_seo.json").is_file()


def test_agency_rest_api_endpoints(tmp_path: Path):
    service = _make_service(tmp_path)
    job = service.create_job({"title": "API Ledger Test"})
    service.nexus_coordinator.emit_phase_handoff(job, "plan", "voice", job["workspace"])

    client = TestClient(create_app(service))

    roster_resp = client.get("/api/agency/roster")
    assert roster_resp.status_code == 200
    roster_data = roster_resp.json()
    assert roster_data["agent_count"] == 15
    assert roster_data["lint"]["passed"] is True
    assert set(roster_data["divisions"].keys()) == {"direction", "editorial", "visual_cinema", "quality_and_engineering"}

    search_resp = client.get("/api/agency/search", params={"q": "loudness lufs mp4"})
    assert search_resp.status_code == 200
    assert search_resp.json()["results"][0]["id"] == "qc"

    inspect_resp = client.get("/api/agency/agents/qc")
    assert inspect_resp.status_code == 200
    assert inspect_resp.json()["id"] == "qc"
    assert "Broadcast Master Screening Director" in inspect_resp.json()["name"]

    missing_resp = client.get("/api/agency/agents/nonexistent_agent")
    assert missing_resp.status_code == 404

    ledger_resp = client.get(f"/api/jobs/{job['id']}/nexus-ledger")
    assert ledger_resp.status_code == 200
    ledger_json = ledger_resp.json()
    assert ledger_json["ledger"]["handoff_count"] == 1
    assert any(v.get("phase") == "plan" and v.get("verdict") == "PASS" for v in ledger_json["qa_verdicts"])


def test_unauthorized_workspace_write_triggers_qa_rejection(tmp_path: Path):
    """If a specialist modifies a file outside `writes_artifacts`, `write_audit` forces QA FAIL."""
    service = _make_service(tmp_path)
    job = service.create_job({"title": "Write Guardrail Test"})
    ws = Path(job["workspace"])

    class RogueWriterGateway:
        def run_prompt_reusable(self, prompt: str, workspace: Path, label: str, **kwargs) -> StageResult:
            if label.startswith("agent-"):
                # `voice` tries to forge `final_manifest.json` (which only `qc` may write!)
                (ws / "final_manifest.json").write_text('{"forged_qc": true}', encoding="utf-8")
                return StageResult(
                    0,
                    json.dumps({"status": "completed", "report": "Đã xong.", "proposed_actions": []}, ensure_ascii=False),
                    Path(workspace) / label,
                )
            if label.startswith("qa-verify-"):
                # Even if the LLM QA mistakenly returned PASS, the hard write_audit guard overrides to FAIL!
                return StageResult(
                    0,
                    json.dumps({"verdict": "PASS", "summary": "Looks fine", "issues": []}),
                    Path(workspace) / label,
                )
            if "VERIFIED EXECUTION EVIDENCE" in prompt:
                return StageResult(0, "Đã chặn hành vi ghi trái phép.", Path(workspace) / label)
            return StageResult(
                0,
                json.dumps({
                    "reply": "Giao Voice kiểm tra.",
                    "actions": [{
                        "type": "delegate_agent",
                        "agent_id": "voice",
                        "task": "Kiểm tra file âm thanh",
                        "job_id": job["id"],
                        "verify_with_qa": True,
                    }],
                }, ensure_ascii=False),
                Path(workspace) / label,
            )

    service.gemini_gateway = RogueWriterGateway()
    res = service.producer_chat("Kiểm tra âm thanh", selected_job_id=job["id"], locked_provider="gemini")
    delegated = res["actions"][0]
    assert delegated["status"] == "failed"
    assert delegated["qa_verdict"] == "FAIL"
    assert delegated["attempts"] == 3


def test_default_in_app_chatbot_goal_and_agent_modes_auto_invoke_orchestrator_and_15_roster():
    """Verify both default Antigravity chatbot modes (Agent + Goal) and Codex chat auto-load orchestrator.md & 15 agents."""
    from documentary.prompts import build_producer_chat_prompt, build_producer_goal_prompt

    app_ctx = {"app_tab": "overview", "selected_job": None, "live_progress": None}

    # 1. Default interactive Agent Mode (`goal_mode=False`, `first_turn=True`)
    agent_mode_prompt = build_producer_goal_prompt(
        "Kiểm tra trạng thái dự án",
        app_ctx,
        api_base_url="http://127.0.0.1:8878",
        first_turn=True,
        goal_mode=False,
    )
    assert "NEXUS SPECIALIST OPERATING CHARTER (agents/direction/orchestrator.md)" in agent_mode_prompt
    assert "Cofi Executive Producer" in agent_mode_prompt
    assert "/api/agency/delegate" in agent_mode_prompt
    assert "/api/agency/delegate-squad" in agent_mode_prompt
    for aid in ("radar", "research", "script", "voice", "visuals", "footage", "ai_visual", "vox", "edit", "seo", "evidence_qa", "qc", "dev", "debug"):
        assert f'"{aid}"' in agent_mode_prompt

    # 2. Persistent Goal Mode (`goal_mode=True`, `first_turn=True`)
    goal_mode_prompt = build_producer_goal_prompt(
        "Làm trọn gói 1 tập phim tài liệu mới",
        app_ctx,
        api_base_url="http://127.0.0.1:8878",
        first_turn=True,
        goal_mode=True,
    )
    assert "NEXUS SPECIALIST OPERATING CHARTER (agents/direction/orchestrator.md)" in goal_mode_prompt
    assert "/api/agency/delegate" in goal_mode_prompt

    # 3. Follow-up turn (`first_turn=False`) with explicit specialist assignment locks onto that specialist's charter
    followup_explicit = build_producer_goal_prompt(
        "Giao biên kịch viết lại mở bài cuốn hơn",
        app_ctx,
        api_base_url="http://127.0.0.1:8878",
        first_turn=False,
        goal_mode=False,
        explicit_agent_id="script",
    )
    assert "agents/editorial/script.md" in followup_explicit
    assert "Lead Broadcast Showrunner" in followup_explicit

    # 4. Codex / fallback JSON mode (`build_producer_chat_prompt`) also loads orchestrator.md
    codex_chat_prompt = build_producer_chat_prompt(
        [],
        "Xin chào",
        agents=AgentManager().list_agents(),
    )
    assert "NEXUS SPECIALIST OPERATING CHARTER (agents/direction/orchestrator.md)" in codex_chat_prompt


def test_edit_chat_and_all_phase_prompts_auto_bind_dedicated_agents_with_co_leads(tmp_path: Path):
    """Verify plan loads script+research, edit & edit_chat load edit+vox, and footage vision review loads footage.md."""
    from documentary.footage import build_codex_vision_review_prompt
    from documentary.prompts import build_edit_chat_prompt

    ws = tmp_path / "ep_us"
    ws.mkdir(parents=True)
    us_job = {
        "id": "job_us_auto_bind",
        "title": "The Tacoma Bridge Collapse",
        "market": "US",
        "language": "en",
        "visual_strategy": "hybrid",
        "target_duration_minutes": 15,
    }

    plan_prompt = build_phase_prompt(us_job, "plan", ws, REMOTION_ROOT)
    assert "agents/editorial/script.md" in plan_prompt
    assert "CO-LEAD CHARTER (agents/editorial/research.md)" in plan_prompt
    assert not re.search(r"[\uac00-\ud7a3]", plan_prompt)

    edit_phase_prompt = build_phase_prompt(us_job, "edit", ws, REMOTION_ROOT)
    assert "agents/visual_cinema/edit.md" in edit_phase_prompt
    assert "CO-LEAD CHARTER (agents/visual_cinema/vox.md)" in edit_phase_prompt
    assert not re.search(r"[\uac00-\ud7a3]", edit_phase_prompt)

    edit_chat_prompt = build_edit_chat_prompt(us_job, ws, REMOTION_ROOT, "Tăng nhịp cắt ở beat B002")
    assert "agents/visual_cinema/edit.md" in edit_chat_prompt
    assert "CO-LEAD CHARTER (agents/visual_cinema/vox.md)" in edit_chat_prompt
    assert not re.search(r"[\uac00-\ud7a3]", edit_chat_prompt)

    ftg_review_prompt = build_codex_vision_review_prompt(
        us_job,
        [{"beat_id": "B001", "narration_text": "Bridge cables vibrated violently.", "source_priority": "must_real"}],
        [{"candidate_id": "C1", "beat_id": "B001", "title": "1940 archival reel"}],
    )
    assert "agents/visual_cinema/footage.md" in ftg_review_prompt
    assert "Archival Footage Hunter" in ftg_review_prompt


def test_agency_delegate_http_endpoint_defaults_to_qa_loop_and_phase_traces_record_all_agents(tmp_path: Path):
    """Verify POST /api/agency/delegate runs Maker <-> evidence_qa by default and phase handoffs log all agent spans."""
    service = _make_service(tmp_path)
    job = service.create_job({"title": "HTTP Delegate & Trace Test", "market": "US", "language": "en"})
    ws = Path(job["workspace"])

    class HttpDelegateGateway:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def run_prompt_reusable(self, prompt: str, workspace: Path, label: str, **kwargs) -> StageResult:
            self.calls.append(label)
            if label.startswith("agent-"):
                return StageResult(
                    0,
                    json.dumps({
                        "status": "completed",
                        "report": "Đã kiểm chứng xong hồ sơ lịch sử.",
                        "deliverables": ["research.md"],
                        "handoff_notes": "All dates verified.",
                        "proposed_actions": [],
                    }, ensure_ascii=False),
                    Path(workspace) / label,
                )
            if label.startswith("qa-verify-"):
                return StageResult(
                    0,
                    json.dumps({"verdict": "PASS", "summary": "Hồ sơ khớp nguồn gốc.", "issues": []}, ensure_ascii=False),
                    Path(workspace) / label,
                )
            return StageResult(0, json.dumps({"actions": []}), Path(workspace) / label)

    gw = HttpDelegateGateway()
    service.gemini_gateway = gw
    service.update_chat_provider("gemini")

    client = TestClient(create_app(service))
    resp = client.post(
        "/api/agency/delegate",
        json={
            "agent_id": "research",
            "task": "Kiểm chứng niên biểu vụ sập cầu",
            "job_id": job["id"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "reported"
    assert body["agent_id"] == "research"
    assert body["qa_verdict"] == "PASS"
    assert any(c.startswith("qa-verify-") for c in gw.calls), "POST /api/agency/delegate must run evidence_qa gate by default"

    # Emit phase handoffs across plan -> voice -> visuals -> edit -> qc and check automatic trace spans
    coord = service.nexus_coordinator
    coord.emit_phase_handoff(job, "plan", "voice", ws)
    coord.emit_phase_handoff(job, "voice", "visuals", ws)
    coord.emit_phase_handoff(job, "visuals", "edit", ws)
    coord.emit_phase_handoff(job, "edit", "qc", ws)
    coord.emit_phase_handoff(job, "qc", None, ws)

    nexus_state = coord.get_project_nexus_state(ws)
    recorded_ids = {t["agent_id"] for t in nexus_state["traces"]}
    for expected_agent in ("research", "script", "voice", "visuals", "vox", "edit", "evidence_qa", "qc"):
        assert expected_agent in recorded_ids, f"Missing automatic trace span for {expected_agent}"

