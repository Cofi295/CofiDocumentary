"""Comprehensive verification suite for the Clean-Slate Token Diet, Deterministic State Ledger, and Surgical Beat Sharding."""
from __future__ import annotations

import json
from pathlib import Path
import re

from fastapi.testclient import TestClient

from documentary.agent_manager import AgentManager
from documentary.gemini_gateway import GeminiGateway
from documentary.goal_session import AntigravityGoalSession
from documentary.prompts import (
    _job_context,
    _profile_editorial_dna_direction,
    build_edit_chat_prompt,
    build_footage_eye_agent_prompt,
    build_phase_prompt,
    build_producer_chat_prompt,
    build_producer_goal_prompt,
)
from documentary.service import DocumentaryService
from documentary.store import JobStore
from documentary.workspace_ledger import (
    clear_dirty_beats,
    format_compact_ledger_brief,
    get_beat_context_slice,
    list_workspace_beats,
    load_single_beat,
    load_workspace_ledger,
    patch_workspace_beats,
    sync_beat_shards,
    sync_workspace_ledger,
)
from server import create_app


DOC_ROOT = Path(__file__).resolve().parents[1]
REMOTION_ROOT = DOC_ROOT.parent / "CofiRemotion"
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


def _make_service(tmp_path: Path) -> DocumentaryService:
    root = tmp_path / "app"
    remotion = tmp_path / "remotion"
    remotion.mkdir(parents=True, exist_ok=True)
    return DocumentaryService(
        root=root,
        store=JobStore(root / "data" / "jobs"),
        remotion_dir=remotion,
    )


def _seed_sample_manifest(ws: Path) -> list[dict]:
    ws.mkdir(parents=True, exist_ok=True)
    beats = [
        {
            "beat_id": "B001",
            "act_id": "ACT01",
            "story_group": "cold_open",
            "start_sec": 0.0,
            "end_sec": 8.5,
            "visual_route": "footage",
            "visual_type": "sourced_video",
            "narration_text": "At midnight in Shenyang, the patrol car stopped outside the shuttered branch.",
            "unique_payload_marker": "MARKER_BEAT_ONE_UNTOUCHED",
        },
        {
            "beat_id": "B002",
            "act_id": "ACT01",
            "story_group": "vault_anomaly",
            "start_sec": 8.5,
            "end_sec": 18.0,
            "visual_route": "vox",
            "visual_type": "vox_editorial_desk",
            "narration_text": "Inside the bank vault ledger, three serial numbers vanished from the overnight audit.",
            "vox_layout": "direct_50_50_collision_seam",
            "vox_entrance": "scissors_slide_left",
            "unique_payload_marker": "MARKER_BEAT_TWO_TARGET",
        },
        {
            "beat_id": "B003",
            "act_id": "ACT01",
            "story_group": "vault_anomaly",
            "start_sec": 18.0,
            "end_sec": 26.4,
            "visual_route": "footage",
            "visual_type": "sourced_video",
            "narration_text": "Detectives sealed the corridor before dawn.",
            "unique_payload_marker": "MARKER_BEAT_THREE_NEIGHBOR",
        },
        {
            "beat_id": "B004",
            "act_id": "ACT02",
            "story_group": "archive_trace",
            "start_sec": 72.0,
            "end_sec": 82.0,
            "visual_route": "ai_visual",
            "visual_type": "ai_reconstruction",
            "narration_text": "At seventy five seconds, a clerk opened a dusty wooden cabinet in the archive basement.",
            "unique_payload_marker": "MARKER_BEAT_FOUR_DISTANT_UNRELATED",
        },
    ]
    (ws / "visual_manifest.json").write_text(
        json.dumps({"duration_sec": 82.0, "beats": beats}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return beats


def test_real_heavy_workspace_token_diet_and_zero_legacy_bloat(tmp_path: Path):
    """Verify >65% prompt payload reduction on the heaviest real 28-min job and zero legacy bloat."""
    real_input = DOC_ROOT / "workspaces" / "20261114-094247-238a65cb" / "input.json"
    if real_input.is_file():
        job = json.loads(real_input.read_text(encoding="utf-8"))
    else:
        profiles = json.loads((DOC_ROOT / "data" / "channel_profiles.json").read_text(encoding="utf-8"))["profiles"]
        heaviest = max(profiles, key=lambda p: len(json.dumps(p, ensure_ascii=False)))
        job = {
            "id": "synthetic-heavy",
            "title": "Heavy Profile Token Diet Check",
            "market": heaviest.get("market", "KR"),
            "language": heaviest.get("language", "ko"),
            "target_duration_minutes": 28,
            "production_recipe": {"target_duration_sec": 1680},
            "editing_dna": heaviest.get("editing_dna") or {},
            "channel_profile_snapshot": heaviest,
        }

    ctx = _job_context(job)
    assert len(ctx) < 15_000, f"_job_context bloated to {len(ctx)} chars (was 155.2K before diet)"
    assert "curated_today_candidates" not in ctx
    assert "dna_case_vault" not in ctx
    assert "topic_memory" not in ctx

    ed_plan = _profile_editorial_dna_direction(job, "plan")
    assert len(ed_plan) < 25_000, f"_profile_editorial_dna_direction bloated to {len(ed_plan)} chars (was 94.6K)"
    assert "curated_today_candidates" not in ed_plan

    clean_ws = tmp_path / "clean_heavy_ws"
    clean_ws.mkdir(parents=True, exist_ok=True)
    plan_bytes = len(build_phase_prompt(job, "plan", clean_ws, REMOTION_ROOT).encode("utf-8"))
    edit_bytes = len(build_phase_prompt(job, "edit", clean_ws, REMOTION_ROOT).encode("utf-8"))
    seo_bytes = len(build_phase_prompt(job, "seo", clean_ws, REMOTION_ROOT).encode("utf-8"))

    assert plan_bytes < 160_000, f"plan prompt too heavy: {plan_bytes} bytes (was 498 KB)"
    assert edit_bytes < 165_000, f"edit prompt too heavy: {edit_bytes} bytes (was 406 KB)"
    assert seo_bytes < 95_000, f"seo prompt too heavy: {seo_bytes} bytes"


def test_zero_hardcoded_channel_ids_and_zero_hangul_on_english_prompts(tmp_path: Path):
    """Verify zero hardcoded `channel-*` IDs in core constitution/code and zero Hangul leaks on US English jobs."""
    lint = AgentManager().lint_corpus()
    assert lint["passed"] is True, lint["errors"]

    clean_files = [
        DOC_ROOT / "AGENTS.md",
        DOC_ROOT / "documentary" / "prompts.py",
        DOC_ROOT / "documentary" / "agent_manager.py",
        DOC_ROOT / "services" / "editing_dna_service.py",
        *sorted((DOC_ROOT / "agents").rglob("*.md")),
    ]
    channel_id_re = re.compile(r"channel-(?:[0-9a-f]{6,}|(?:kr|us|cn|vn|jp|de|fr|es)-[a-z0-9_-]+)")
    for path in clean_files:
        text = path.read_text(encoding="utf-8")
        assert not channel_id_re.search(text), f"Hardcoded channel-* ID leaked in {path}"

    us_job = {
        "id": "us-clean-check",
        "title": "The Missing Vault Ledger of 1998",
        "market": "US",
        "language": "en",
        "visual_strategy": "evidence_footage",
        "production_recipe": {"target_duration_sec": 1200},
        "editing_dna": {"preset_id": "forensic_noir_director_v2", "director_mode": "v2"},
        "seo_keyword_dna": {"primary_title_keyword": "Declassified Case File"},
    }
    ws = tmp_path / "us_ws"
    beats = _seed_sample_manifest(ws)

    for phase in ("plan", "footage", "edit", "seo", "qc"):
        p_text = build_phase_prompt(us_job, phase, ws, REMOTION_ROOT)
        leaks = HANGUL_RE.findall(p_text)
        assert not leaks, f"Hangul leaked into US English `{phase}` prompt: {''.join(leaks[:30])}"

    ftg_prompt = build_footage_eye_agent_prompt(us_job, ws, REMOTION_ROOT, beats)
    assert not HANGUL_RE.search(ftg_prompt), "Hangul leaked into US English footage prompt"

    chat_prompt = build_edit_chat_prompt(us_job, ws, REMOTION_ROOT, "Tighten the cut on beat B002")
    assert not HANGUL_RE.search(chat_prompt), "Hangul leaked into US English edit_chat prompt"


def test_zero_contradictions_and_zero_polling_loop_in_producer_prompts():
    """Verify Producer Chat & Goal prompts have zero self-contradictions and zero HTTP polling loops."""
    chat_prompt = build_producer_chat_prompt(
        [{"id": "job-1", "title": "Test", "status": "idle", "current_phase": None}],
        "Chạy bước tiếp theo cho dự án này",
        selected_job_id="job-1",
    )
    goal_prompt = build_producer_goal_prompt(
        "Chạy full pipeline cho dự án này",
        {"selected_job": {"id": "job-1", "title": "Test", "status": "idle"}},
        api_base_url="http://127.0.0.1:8878",
        first_turn=True,
        goal_mode=True,
    )

    for label, text in (("producer_chat", chat_prompt), ("producer_goal", goal_prompt)):
        low = text.lower()
        assert "poll get /api/jobs" not in low, f"Forbidden HTTP polling instruction remained in {label}"
        assert "mỗi 30–90 giây" not in low and "mỗi 30-90 giây" not in low, f"Polling timer loop remained in {label}"
        assert "làm ngay trực tiếp" not in low, f"Contradictory 'LÀM NGAY TRỰC TIẾP' remained in {label}"
        assert "/api/jobs/{id}/beats/{beat_id}" in text or "beats" in low


def test_beat_sharding_surgical_patch_and_state_ledger_lifecycle(tmp_path: Path):
    """Verify sharding, targeted beat slicing, surgical single-beat patching, and dirty-beat tracking."""
    ws = tmp_path / "ledger_ws"
    _seed_sample_manifest(ws)

    idx = sync_beat_shards(ws)
    assert idx["total_beats"] == 4
    assert (ws / "beats_index.json").is_file()
    assert (ws / "beats" / "B002.json").is_file()

    # Match by beat_id, mm:ss timestamp, and quoted narration phrase
    by_id = get_beat_context_slice(ws, message="Đổi bố cục ở beat B002 sang poker_fan_3_cards_hand")
    assert by_id["matched"] is True
    assert by_id["target_beat_ids"] == ["B002"]
    assert [n["beat_id"] for n in by_id["neighbor_summaries"]] == ["B001", "B003"]

    by_ts = get_beat_context_slice(ws, message="Chỉnh lại đoạn 01:15 cho mượt hơn")
    assert by_ts["target_beat_ids"] == ["B004"]

    by_quote = get_beat_context_slice(ws, message='Sửa câu "bank vault ledger" sang hiệu ứng slap_drop_top')
    assert by_quote["target_beat_ids"] == ["B002"]

    b1_before = (ws / "beats" / "B001.json").read_bytes()
    b4_before = (ws / "beats" / "B004.json").read_bytes()

    patch_res = patch_workspace_beats(
        ws,
        {"B002": {"vox_layout": "poker_fan_3_cards_hand", "vox_entrance": "slap_drop_top"}},
        reason="Switch B002 layout to poker fan",
    )
    assert patch_res["updated_beat_ids"] == ["B002"]
    assert patch_res["dirty_beat_ids"] == ["B002"]

    # Unrelated shards remain 100% byte-identical
    assert (ws / "beats" / "B001.json").read_bytes() == b1_before
    assert (ws / "beats" / "B004.json").read_bytes() == b4_before

    # Target shard AND canonical visual_manifest.json are both updated in sync
    b2_shard = load_single_beat(ws, "B002")
    assert b2_shard is not None
    assert b2_shard["vox_layout"] == "poker_fan_3_cards_hand"
    manifest_after = json.loads((ws / "visual_manifest.json").read_text(encoding="utf-8"))
    b2_manifest = next(b for b in manifest_after["beats"] if b["beat_id"] == "B002")
    assert b2_manifest["vox_layout"] == "poker_fan_3_cards_hand"

    dirty_list = list_workspace_beats(ws, dirty_only=True)
    assert [b["beat_id"] for b in dirty_list["beats"]] == ["B002"]

    ledger = load_workspace_ledger(ws)
    assert ledger["beat_progress"]["dirty_beat_ids"] == ["B002"]
    assert any("Switch B002 layout" in m["summary"] for m in ledger["recent_mutations"])

    clear_dirty_beats(ws, reason="edit_phase_completed")
    assert load_workspace_ledger(ws)["beat_progress"]["dirty_beat_ids"] == []


def test_fastapi_beat_endpoints_surgical_edit_prompt_compact_jobs_and_handoff(tmp_path: Path):
    """Verify REST beat endpoints, surgical edit prompt slicing, summary=True chat payloads, and handoff memory."""
    service = _make_service(tmp_path)
    bloated_snapshot = {
        "id": "custom-profile",
        "label": "Investigative Desk",
        "curated_today_candidates": [{"title": f"Candidate {i}", "notes": "x" * 400} for i in range(40)],
    }
    job = service.create_job(
        {
            "title": "Surgical Beat API Test",
            "market": "US",
            "language": "en",
            "channel_profile_snapshot": bloated_snapshot,
        }
    )
    ws = Path(job["workspace"])
    _seed_sample_manifest(ws)
    sync_workspace_ledger(ws, service.get_job(job["id"]), last_action="seeded_manifest")

    client = TestClient(create_app(service))

    list_resp = client.get(f"/api/jobs/{job['id']}/beats")
    assert list_resp.status_code == 200
    assert list_resp.json()["total_beats"] == 4

    get_resp = client.get(f"/api/jobs/{job['id']}/beats/B002")
    assert get_resp.status_code == 200
    assert get_resp.json()["beat"]["unique_payload_marker"] == "MARKER_BEAT_TWO_TARGET"

    patch_resp = client.patch(
        f"/api/jobs/{job['id']}/beats/B002",
        json={"updates": {"vox_layout": "stepped_seesaw_balance"}, "reason": "API surgical test"},
    )
    assert patch_resp.status_code == 200
    patched_json = patch_resp.json()
    assert patched_json["beat"]["vox_layout"] == "stepped_seesaw_balance"
    assert "B002" in patched_json["dirty_beat_ids"]

    # Surgical edit_chat prompt includes ONLY target beat shard payload, NOT distant B004 payload
    surgical_prompt = build_edit_chat_prompt(
        service.get_job(job["id"]),
        ws,
        REMOTION_ROOT,
        "Change cut-and-paste entrance on beat B002",
    )
    assert "SURGICAL TARGET BEAT SHARDS" in surgical_prompt
    assert "MARKER_BEAT_TWO_TARGET" in surgical_prompt
    assert "MARKER_BEAT_FOUR_DISTANT_UNRELATED" not in surgical_prompt

    # Producer chat context includes compact state_ledger
    ctx = service.producer_chat_context(job["id"], "edit")
    assert ctx["selected_job"]["state_ledger"]["dirty_beat_ids"] == ["B002"]
    assert ctx["selected_job"]["state_ledger"]["sharded_beats_ready"] is True

    # Producer goal chat /new returns compact jobs (summary=True, zero bloated channel_profile_snapshot)
    reset_resp = service.producer_goal_chat("/new", selected_job_id=job["id"])
    assert len(reset_resp["jobs"]) == 1
    assert "channel_profile_snapshot" not in reset_resp["jobs"][0]
    assert len(json.dumps(reset_resp["jobs"], ensure_ascii=False)) < 4_000

    # Session compaction handoff preserves state_ledger deterministically in both AntigravityGoalSession & GeminiGateway
    goal_sess = AntigravityGoalSession(service.gemini_gateway, service.root, f"producer_chat_{job['id']}_goal")
    goal_handoff = goal_sess._build_local_handoff_summary()
    assert "state_ledger.json" in goal_handoff
    assert "B002" in goal_handoff

    gw_handoff = GeminiGateway._build_local_fallback_handoff(
        ws,
        ws / ".producer" / "edit-chat",
        {"conversation_id": "conv-1", "turn_count": 5},
    )
    assert "state_ledger.json" in gw_handoff
    assert "B002" in gw_handoff
    assert len(format_compact_ledger_brief(ws)) < 1_800


def test_live_app_diagnostic_routing_hot_reload_and_edit_batch_diet(tmp_path: Path):
    """Verify diagnostic questions without '?' route to answer_first, summary=True strips heavy fields, and edit prompts inject state_ledger."""
    from documentary import hot_reload
    from documentary.prompts import build_edit_batch_prompt

    assert "documentary.workspace_ledger" in hot_reload._RELOAD_ORDER
    assert AntigravityGoalSession.DEFAULT_MAX_CONTEXT_TOKENS == 115_000
    assert AntigravityGoalSession.DEFAULT_MAX_STEPS == 600

    # Diagnostic/status questions without '?' must route to answer_first (Route 1)
    assert DocumentaryService._is_answer_first_or_question_turn("bước edit lỗi gì rồi kìa") is True
    assert DocumentaryService._is_answer_first_or_question_turn("giờ check app xem nào. xem nó đã làm đúng đã fix chưa hay vẫn đọc lại") is True
    assert DocumentaryService._is_answer_first_or_question_turn("sao dừng rồi") is True
    # Explicit execution commands must NOT be held back by answer_first
    assert DocumentaryService._is_answer_first_or_question_turn("bước edit lỗi gì thế, fix đi rồi chạy tiếp") is False
    assert DocumentaryService._is_answer_first_or_question_turn("tiếp cho đến khi hoàn thành video. giao agent làm") is False

    service = _make_service(tmp_path)
    job = service.create_job(
        {
            "title": "Summary Diet Test",
            "market": "KR",
            "language": "ko",
            "default_creative_brief": {"huge": "x" * 15_000},
            "thumbnail_dna": {"huge": "y" * 10_000},
            "seo_keyword_dna": {"huge": "z" * 8_000},
        }
    )
    service.store.update(
        job["id"],
        {
            "input": {"raw": "w" * 12_000},
            "phases": {"plan": {"status": "succeeded", "last_message": "m" * 10_000}},
        },
    )
    summary_row = service.list_jobs(summary=True)[0]
    for stripped_key in ("default_creative_brief", "input", "thumbnail_dna", "seo_keyword_dna"):
        assert stripped_key not in summary_row
    assert len(summary_row["phases"]["plan"]["last_message"]) <= 240

    # Compact steps in producer_chat_history
    service._append_producer_chat_history(
        "assistant",
        "Đã kiểm tra xong.",
        selected_job_id=job["id"],
        steps=[{"step_index": 1, "step_type": "tool", "tool_name": "run_command", "output": "o" * 20_000, "target": "t" * 500}],
    )
    compact_hist = service.producer_chat_history(limit=10, selected_job_id=job["id"], compact_steps=True)
    assert "output" not in compact_hist[-1]["steps"][0]
    assert len(compact_hist[-1]["steps"][0]["target"]) <= 200

    # Edit batch prompt injects state_ledger & points to beats_index.json / beats/<beat_id>.json shards
    ws = Path(job["workspace"])
    beats = _seed_sample_manifest(ws)
    sync_beat_shards(ws, job=job)
    sync_workspace_ledger(ws, service.get_job(job["id"]), last_action="edit_batch_test")
    batch_prompt = build_edit_batch_prompt(service.get_job(job["id"]), ws, REMOTION_ROOT, beats)
    assert "WORKSPACE STATE LEDGER & BEAT SHARD INVENTORY" in batch_prompt
    assert "ZERO EXPLORATORY DIRECTORY/HISTORY SWEEP LAW" in batch_prompt
    assert "beats_index.json" in batch_prompt


def test_stop_compact_new_chat_preserve_handoff_and_surgical_script_locator(tmp_path: Path) -> None:
    """Verify Stop / `/compact` / `/new` never lose progress and `build_surgical_work_locator` pinpoints exact `script.md` lines + beat shards."""
    from documentary.prompts import build_producer_goal_prompt
    from documentary.workspace_ledger import build_surgical_work_locator

    service = _make_service(tmp_path)
    job = service.create_job(
        {
            "title": "윈난 양칭페이 사건",
            "market": "KR",
            "language": "ko",
            "visual_strategy": "hybrid",
        }
    )
    ws = Path(job["workspace"])
    (ws / "script.md").write_text(
        "첫 번째 문단입니다.\n\n"
        "두 번째 문단입니다.\n\n"
        "2016년 9월 29일 새벽이 밝아 오자 양칭페이는 여섯 가구의 문을 밖에서 걸어 닫은 뒤 흔적을 지우기 시작했습니다. "
        "밤새 입었던 옷과 신발을 갈아입고, 손전등과 벗어 둔 장갑 등을 챙겨 마을 뒤편 리쯔거우 산길로 빠져나갔죠.\n",
        encoding="utf-8",
    )
    vm = {
        "beats": [
            {
                "beat_id": "B001-V01",
                "narration_text": "첫 번째 문단입니다.",
                "start_sec": 0.0,
                "end_sec": 4.0,
                "duration_sec": 4.0,
                "visual_route": "REAL_FTG",
                "paragraph_index": 1,
            },
            {
                "beat_id": "B135-V01",
                "narration_text": "밤새 입었던 옷과 신발을 갈아입고, 손전등과 벗어 둔 장갑 등을 챙겨 마을 뒤편 리쯔거우 산길로 빠져나갔죠.",
                "start_sec": 889.8,
                "end_sec": 898.5,
                "duration_sec": 8.7,
                "visual_route": "VOX_NEWSROOM",
                "paragraph_index": 54,
            },
        ]
    }
    (ws / "visual_manifest.json").write_text(json.dumps(vm, ensure_ascii=False, indent=2), encoding="utf-8")
    (ws / "audio" / "beats_raw").mkdir(parents=True, exist_ok=True)
    (ws / "audio" / "beats_raw" / "B135.wav").write_bytes(b"RIFF0000WAVE")
    sync_beat_shards(ws, job=job)
    # Persist paragraph_index in B135-V01 shard
    b135_shard = json.loads((ws / "beats" / "B135-V01.json").read_text(encoding="utf-8"))
    b135_shard["paragraph_index"] = 54
    (ws / "beats" / "B135-V01.json").write_text(json.dumps(b135_shard, ensure_ascii=False, indent=2), encoding="utf-8")
    sync_workspace_ledger(ws, service.get_job(job["id"]), last_action="seed_test")

    # 1. Verify should_compact() does NOT wipe an active session at step_index=125 when tokens are low (<75K)
    _, label = service._producer_chat_scope(job["id"])
    session = service.goal_sessions.get(service.gemini_gateway, service.root, f"{label}_goal")
    session._save_conversation_id("cid-keep-alive-123")
    session.step_index = 150
    session.input_tokens = 38_000
    session.cache_read_tokens = 5_000
    assert session.should_compact() is False

    # 2. Verify concrete tool step formatting & handoff summary (after Stop or /compact or /new)
    service._append_producer_chat_history(
        "user",
        "Đoạn 54: sửa câu 밤새 입었던 옷과 신발을 갈아입고 trong script.md và thu lại voice",
        selected_job_id=job["id"],
    )
    service._append_producer_chat_history(
        "assistant",
        "Đã dừng lượt làm việc theo yêu cầu.",
        selected_job_id=job["id"],
        steps=[
            {
                "step_index": 121,
                "step_type": "tool",
                "tool_name": "edit_file",
                "target": f"{ws}/script.md#L5-L5",
                "tool_summary": "Fix Đoạn 54 sentence in script.md",
            },
            {
                "step_index": 122,
                "step_type": "tool",
                "tool_name": "call_mcp_tool",
                "target": "cofivoice/tts -> B135.wav",
            },
        ],
    )
    compacted = service.compact_producer_chat_session(job["id"])
    handoff_text = session.load_handoff_summary()
    assert "Sổ cái tiến độ dự án (`state_ledger.json`):" in handoff_text
    assert handoff_text.count("Sổ cái tiến độ dự án (`state_ledger.json`):") == 1
    assert "Lịch sử trao đổi & yêu cầu gần nhất trong dự án:" in handoff_text
    assert "Đoạn 54" in handoff_text
    assert "script.md#L5-L5" in handoff_text
    assert "B135.wav" in handoff_text
    assert compacted["ok"] is True

    # 3. Verify /new resets gemini_session.json (fresh 0-token window) while keeping project handoff_summary.txt
    session._save_conversation_id("cid-before-new")
    new_res = service.new_producer_chat_session(job["id"])
    assert new_res["ok"] is True
    assert not (service.root / ".producer" / f"{label}_goal" / "gemini_session.json").exists()
    handoff_after_new = (service.root / ".producer" / f"{label}_goal" / "handoff_summary.txt").read_text(encoding="utf-8")
    assert "Sổ cái tiến độ dự án (`state_ledger.json`):" in handoff_after_new
    assert "script.md#L5-L5" in handoff_after_new

    # 4. Verify surgical locator finds exact script.md line AND beat shard B135-V01 even when follow-up message is just "làm đi"
    history = service.producer_chat_history(limit=10, selected_job_id=job["id"])
    locator = build_surgical_work_locator(ws, "làm đi", history)
    assert "ĐỊNH VỊ PHẪU THUẬT TỰ ĐỘNG TRÊN ĐĨA" in locator
    assert "script.md` dòng 5..5" in locator
    assert "B135-V01" in locator
    assert "beats/B135-V01.json" in locator
    assert "audio/beats_raw/B135.wav" in locator

    app_ctx = service.producer_chat_context(job["id"], "script")
    full_prompt = build_producer_goal_prompt(
        "làm đi",
        app_ctx,
        api_base_url="http://127.0.0.1:8878",
        first_turn=True,
        history=history,
        goal_mode=True,
    )
    assert "ĐỊNH VỊ PHẪU THUẬT TỰ ĐỘNG TRÊN ĐĨA" in full_prompt
    assert "beats/B135-V01.json" in full_prompt


def test_two_mode_separation_turn0_speed_diet_and_stop_compact_memory(tmp_path: Path) -> None:
    """Verify strict separation between Production Troubleshooting vs App Code Fix, Turn-0 diet (<16K chars),
    instant stage root-cause log extraction, pre-mounted screenshot upload dir, and Stop/compact memory retention.
    """
    from documentary.workspace_ledger import classify_producer_chat_intent

    service = _make_service(tmp_path)
    remotion_src = service.remotion_dir / "src"
    (remotion_src / "vox-studio" / "case-20261115").mkdir(parents=True, exist_ok=True)
    (remotion_src / "Case20261115.tsx").write_text(
        "import { VoxScene07 } from './vox-studio/case-20261115';\nexport const Case20261115 = () => null;\n",
        encoding="utf-8",
    )
    (remotion_src / "OtherCase20260901.tsx").write_text(
        "export const OtherCase20260901 = () => null;\n",
        encoding="utf-8",
    )

    job = service.create_job(
        {
            "title": "Hồ sơ Vụ Án 20261115",
            "market": "KR",
            "language": "ko",
            "visual_strategy": "hybrid",
        }
    )
    # Rename or simulate date-prefixed job composition lookup via job id prefix if needed:
    job_date_prefix = job["id"].split("-")[0]
    (remotion_src / f"Doc{job_date_prefix}.tsx").write_text(
        "import { VoxScene07 } from './vox-studio/case-20261115';\nexport const DocMain = () => null;\n",
        encoding="utf-8",
    )

    ws = Path(job["workspace"])
    _seed_sample_manifest(ws)
    (ws / "edit_progress.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "completed_beats": 0,
                "total_beats": 4,
                "unsynced_beat_ids": ["B002"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (ws / "export_progress.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "percent": 0,
                "ready_chunks": 0,
                "total_chunks": 8,
                "message": "Background render cache chưa thể hoàn tất tất cả chunk",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rc_logs = ws / ".render_cache" / "logs"
    rc_logs.mkdir(parents=True, exist_ok=True)
    (rc_logs / "part-0001.log").write_text(
        '{"event":"init","conversation_id":"noise-123"}\n'
        "Bundling Remotion project...\n"
        "Error: ModuleNotFoundError: Cannot resolve './missing_evidence_cutout.png' in VoxScene07.tsx:48\n",
        encoding="utf-8",
    )

    service.store.update(
        job["id"],
        {
            "status": "failed",
            "current_phase": "qc",
            "last_error": '{"event": "init", "conversation_id": "raw-cli-stdout-noise"}',
            "phases": {
                "plan": {"status": "succeeded"},
                "voice": {"status": "succeeded"},
                "visuals": {"status": "succeeded"},
                "footage": {"status": "succeeded"},
                "ai_visual": {"status": "succeeded"},
                "edit": {"status": "succeeded"},
                "seo": {"status": "succeeded"},
                "qc": {
                    "status": "failed",
                    "error": "Background render cache chưa thể hoàn tất tất cả chunk",
                },
            },
        },
    )

    # 1. Ledger sanitizes raw CLI JSON stdout noise and reconciles stale edit_progress when edit succeeded
    ledger = sync_workspace_ledger(ws, service.get_job(job["id"]), last_action="qc_failed")
    assert "conversation_id" not in str(ledger.get("last_error") or "")
    assert "Background render cache" in str(ledger.get("last_error") or "")
    assert ledger["beat_progress"]["edit_status"] == "succeeded"
    assert ledger["beat_progress"]["completed_edit_beats"] == 4

    # 2. Mode 1 (Production Pipeline Troubleshooting): instant log diagnosis, 0% codebase locator, Turn-0 < 16K chars
    msg_prod = "preview edit không thấy gì. xuất video thì lỗi"
    assert classify_producer_chat_intent(msg_prod, selected_job_id=job["id"]) == "production_pipeline"

    app_ctx = service.producer_chat_context(job["id"], "qc")
    app_ctx["channel_profiles"] = [{"id": f"prof-{i}", "blob": "p" * 600} for i in range(30)]
    app_ctx["playbooks"] = [{"id": f"pb-{i}", "blob": "b" * 500} for i in range(20)]

    assert "Background render cache" in str(app_ctx["selected_job"]["last_error"])
    assert "live_diagnostics" in app_ctx["selected_job"]

    prod_turn0 = build_producer_goal_prompt(
        msg_prod,
        app_ctx,
        api_base_url="http://127.0.0.1:8878",
        first_turn=True,
        goal_mode=True,
        has_handoff=True,
    )
    assert len(prod_turn0) < 16_000, f"Turn-0 prompt still bloated: {len(prod_turn0)} chars"
    assert "prof-29" not in prod_turn0, "Bloated channel_profiles leaked into Turn-0 active-job snapshot"
    assert "🎬 BỘ NHỚ LUỒNG SẢN XUẤT & CHẨN ĐOÁN TỨC THÌ" in prod_turn0
    assert ".render_cache/logs/part-0001.log" in prod_turn0
    assert "missing_evidence_cutout.png" in prod_turn0
    assert f"Doc{job_date_prefix}.tsx" in prod_turn0
    assert "OtherCase20260901.tsx" not in prod_turn0
    assert "repo_code_index.json" not in prod_turn0
    assert "documentary/render_cache.py" not in prod_turn0
    assert "turbo-nvenc-export.mjs" not in prod_turn0

    # 3. Mode 2 (App Code Fix): injects Architecture Memory Tree + surgical StartLine..EndLine slices
    msg_code = "fix code nút bấm giao diện ở static/app.js và kiểm tra hàm producer_chat_context trong service.py"
    assert classify_producer_chat_intent(msg_code, selected_job_id=job["id"]) == "app_code_fix"
    code_prompt = build_producer_goal_prompt(
        msg_code,
        app_ctx,
        api_base_url="http://127.0.0.1:8878",
        first_turn=False,
        goal_mode=True,
    )
    assert "repo_code_index.json" in code_prompt
    assert "Cây thư mục Bộ nhớ Mã nguồn Hệ thống" in code_prompt
    assert "documentary/service.py" in code_prompt
    assert "producer_chat_context" in code_prompt

    # 4. Pre-mounted chat_uploads + answer_first routing + Stop/compact memory preservation (including last_thinking)
    assert DocumentaryService._is_answer_first_or_question_turn("trả lời đi") is True
    assert DocumentaryService._is_answer_first_or_question_turn("nó đang làm đến đâu, đang nói cái gì thế") is True

    _, label = service._producer_chat_scope(job["id"])
    goal_sess = AntigravityGoalSession(service.gemini_gateway, service.root, f"{label}_goal")
    assert any("chat_uploads" in d for d in goal_sess._extra_dirs), "chat_uploads must be pre-mounted so screenshots never restart agy"

    service._append_producer_chat_history("user", msg_prod, selected_job_id=job["id"])
    for _ in range(4):
        service._append_producer_chat_history("assistant", "Đã dừng lượt làm việc theo yêu cầu.", selected_job_id=job["id"])
    service._append_producer_chat_history("user", "trả lời đi", selected_job_id=job["id"])

    goal_sess.log_path.parent.mkdir(parents=True, exist_ok=True)
    goal_sess.log_path.write_text(
        "\n".join(
            [
                json.dumps({"event": "result", "result": {"response": "Bước qc trước đó đang ở 3.6%."}}),
                json.dumps(
                    {
                        "event": "step_update",
                        "step_update": {
                            "step_type": "agent_response",
                            "thinking": "Đã tìm ra nguyên nhân gốc: VoxScene07.tsx thiếu file missing_evidence_cutout.png làm esbuild gãy.",
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    handoff = goal_sess._build_local_handoff_summary()
    assert msg_prod in handoff, "Substantive user complaint was evicted by repeated Stop clicks!"
    assert "Bước qc trước đó đang ở 3.6%." in handoff
    assert "missing_evidence_cutout.png" in handoff, "Interrupted turn root-cause thinking was discarded!"
    assert "repo_code_index.json" not in handoff, "Project handoff must not leak app source code file modifications!"

    # 5. Every assistant turn in producer_chat_history includes live Trail + Surgical Memory token report & footer
    hist = service.producer_chat_history(limit=10, selected_job_id=job["id"], compact_steps=True)
    asst_items = [row for row in hist if row.get("role") == "assistant"]
    assert asst_items, "Expected assistant rows in producer_chat_history"
    tr = asst_items[-1].get("token_report")
    assert isinstance(tr, dict) and tr.get("trail_enabled") is True
    assert int(tr.get("trail_nodes") or 0) > 0
    assert int(tr.get("saved_tokens") or 0) >= 40_000
    assert "🌱 **trail + Bộ nhớ Phẫu thuật" in str(asst_items[-1].get("content") or "")


