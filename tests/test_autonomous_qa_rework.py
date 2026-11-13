from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from typing import Any

import pytest

from documentary.agent_office import build_live_office_snapshot
from documentary.codex_gateway import StageResult
from documentary.edit import EditCoordinator
from documentary.prompts import build_phase_prompt, load_phase_qa_rejection_directive
from documentary.service import DocumentaryService
from documentary.store import JobStore


def _build_valid_korean_beats(count: int, target_duration_sec: float) -> tuple[str, list[dict[str, Any]]]:
    """Generate a natural, prosodically balanced Korean documentary script & 1-to-1 beats."""
    lines: list[str] = []
    beats: list[dict[str, Any]] = []
    per_beat = round(target_duration_sec / max(1, count), 2)
    for i in range(1, count + 1):
        mod = i % 10
        if mod == 3:
            txt = f"수사팀은 그날 밤 확보한 현장 기록에서도 결정적 단서를 끝내 놓치지 않았죠."
        elif mod == 6:
            txt = "단 육십 초의 침묵."
        elif mod == 8:
            txt = "도대체 왜 그 시각 폐쇄회로 전원만 정확히 꺼져 있었던 걸까요?"
        elif mod == 9:
            txt = "결국 현장에 남겨진 작은 흔적 하나가 모든 알리바이를 무너뜨렸던 겁니다."
        elif mod == 0:
            txt = "열두 장의 승차권."
        else:
            txt = "당시 감식반은 비에 젖은 골목 끝에서 범인이 버리고 간 장갑 두 켤레를 수거했습니다."
        lines.append(txt)
        beats.append({
            "beat_id": f"B{i:03d}",
            "story_group": f"ACT0{min(5, ((i - 1) * 5) // max(1, count) + 1)}",
            "narration_text": txt,
            "purpose": "forensic progression",
            "target_duration_sec": per_beat,
            "visual_type": "sourced_video",
            "source_priority": "prefer_real",
            "visual_description": f"Investigative archival frame {i}",
            "footage_search_queries": [f"archival police investigation clip {i}"],
            "factual_source_refs": ["court_dossier"],
            "framing_motion_intent": "slow optical push",
            "on_screen_text": "",
            "sound_notes": "low tension drone",
        })
    # Group into asymmetric 1-4 sentence paragraphs so cadence is organic
    paras: list[str] = []
    idx = 0
    pattern = (2, 1, 3, 2, 4, 1, 3)
    p_step = 0
    while idx < len(lines):
        take = pattern[p_step % len(pattern)]
        paras.append("\n".join(lines[idx : idx + take]))
        idx += take
        p_step += 1
    return "\n\n".join(paras) + "\n", beats


class _DefectiveThenFixedPlanGateway:
    """Fails QA on Attempt 1 (raw '%' + ~습니다 monotony), then reads the @evidence_qa ticket on Attempt 2 and fixes it."""

    def __init__(self, remotion_dir: Path):
        self.remotion_dir = remotion_dir
        self.prompts_seen: list[str] = []
        self.intermediate_job_statuses: list[str] = []
        self.service_ref: DocumentaryService | None = None

    def run(self, job: dict[str, Any], phase: str, workspace: str | Path, log_callback: Any = None) -> StageResult:
        ws = Path(workspace)
        ws.mkdir(parents=True, exist_ok=True)
        built_prompt = build_phase_prompt(job, phase, ws, self.remotion_dir)
        self.prompts_seen.append(built_prompt)
        if self.service_ref is not None:
            live_job = self.service_ref.get_job(job["id"])
            self.intermediate_job_statuses.append(str(live_job.get("status")))

        contract = job["production_recipe"]["quality_contract"]
        target = float(contract["target_duration_sec"])
        min_scenes = max(20, int(contract["min_scene_count"]))

        if phase == "plan":
            if len(self.prompts_seen) == 1:
                # Attempt 1: Write valid research.md & outline.json, but write defective script.md (raw '%' hazard + 100% ~습니다)
                (ws / "research.md").write_text("# Verified Dossier\n- Primary court record verified.\n" * 30, encoding="utf-8")
                (ws / "outline.json").write_text(
                    json.dumps(
                        {
                            "opening_hook": "Cold night evidence",
                            "chapters": [
                                {"chapter": c, "chapter_id": f"ACT0{c}", "title": f"Act {c}", "summary": "Verified act"}
                                for c in range(1, 6)
                            ],
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                bad_lines = [
                    '용의자는 취조실에서 "맞소, 내가 처음이오."라며 범행을 시인했습니다.'
                    if idx_line == 0
                    else "수사팀은 현장에서 결정적 지문 증거와 사건 기록을 확보했습니다."
                    for idx_line in range(min_scenes)
                ]
                (ws / "script.md").write_text("\n\n".join(bad_lines) + "\n", encoding="utf-8")
                bad_beats = [
                    {
                        "beat_id": f"B{i + 1:03d}",
                        "narration_text": bad_lines[i],
                        "target_duration_sec": round(target / min_scenes, 2),
                    }
                    for i in range(min_scenes)
                ]
                (ws / "visual_manifest.json").write_text(
                    json.dumps({"target_duration_sec": target, "beats": bad_beats}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return StageResult(0, "Draft 1 written", ws / "plan.log")

            # Attempt 2: Must have received @evidence_qa rejection ticket in prompt AND research.md preserved!
            assert "MANDATORY @evidence_qa REJECTION REWORK DIRECTIVE" in built_prompt
            assert (ws / "research.md").is_file()
            assert (ws / "outline.json").is_file()
            good_script, good_beats = _build_valid_korean_beats(min_scenes, target)
            (ws / "script.md").write_text(good_script, encoding="utf-8")
            mf = {"target_duration_sec": target, "beats": good_beats}
            (ws / "visual_manifest.json").write_text(json.dumps(mf, ensure_ascii=False, indent=2), encoding="utf-8")
            (ws / "plan_visual_manifest.json").write_text(json.dumps(mf, ensure_ascii=False, indent=2), encoding="utf-8")
            return StageResult(0, "Reworked clean script after QA feedback", ws / "plan.log")

        return StageResult(0, "ok", ws / f"{phase}.log")


class _SimpleVoice:
    def run(self, job: dict[str, Any], workspace: str | Path) -> StageResult:
        ws = Path(workspace)
        visual = json.loads((ws / "visual_manifest.json").read_text(encoding="utf-8"))
        beats = []
        cursor = 0.0
        for beat in visual["beats"]:
            dur = float(beat.get("target_duration_sec") or 4.0)
            beats.append({"beat_id": beat["beat_id"], "text": beat["narration_text"], "start_sec": cursor, "end_sec": cursor + dur})
            cursor += dur
        (ws / "audio").mkdir(parents=True, exist_ok=True)
        narration = ws / "audio" / "narration.wav"
        narration.write_bytes(b"RIFF-fake-wav")
        (ws / "voice_manifest.json").write_text(
            json.dumps({"narration_path": str(narration), "duration_sec": cursor, "beats": beats}, ensure_ascii=False),
            encoding="utf-8",
        )
        (ws / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\ntest\n", encoding="utf-8")
        return StageResult(0, "voice done", ws / "voice_manifest.json")

    def health(self) -> dict[str, Any]:
        return {"ok": True, "url": "http://127.0.0.1:8792"}

    def voices(self) -> list[Any]:
        return []


def test_plan_qa_rejection_triggers_autonomous_rework_with_injected_ticket_and_never_fails_prematurely(tmp_path: Path):
    remotion_dir = tmp_path / "CofiRemotion"
    gw = _DefectiveThenFixedPlanGateway(remotion_dir)
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=gw,
        voice_engine=_SimpleVoice(),
        remotion_dir=remotion_dir,
    )
    gw.service_ref = service

    job = service.create_job({
        "title": "Autonomous QA Rework Episode",
        "language": "ko",
        "market": "KR",
        "target_duration_minutes": 3,
    })

    service.start(job["id"], "plan")
    service.wait(job["id"], timeout=10)

    final_job = service.get_job(job["id"])
    ws = Path(final_job["workspace"])

    # 1. Must have automatically executed 2 attempts without ever dropping job status to 'failed'
    assert len(gw.prompts_seen) == 2
    assert all(st == "running" for st in gw.intermediate_job_statuses)
    assert final_job["status"] == "ready"
    assert final_job["phases"]["plan"]["status"] == "succeeded"
    assert final_job["phases"]["plan"]["error"] is None
    assert "Đã tự động sửa & vượt kiểm duyệt ở lần 2/3" in final_job["phases"]["plan"]["last_message"]

    # 2. Rework ledger must record the exact Attempt 1 QA rejection and Attempt 2 pass
    ledger_path = ws / ".producer" / "qa_rework_ledger" / "plan.json"
    assert ledger_path.is_file()
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["status"] == "reworked_and_passed"
    assert ledger["passed_on_attempt"] == 2
    assert len(ledger["rejections"]) == 1
    assert ledger["rejections"][0]["critic_agent"] == "evidence_qa"
    assert ledger["rejections"][0]["maker_agent"] == "script"
    assert not (ws / ".producer" / "qa_rejection_feedback" / "plan.md").exists()


def test_chairman_defect_rejection_rework_phase_auto_reruns_and_advances_pipeline(tmp_path: Path, monkeypatch):
    remotion_dir = tmp_path / "CofiRemotion"
    gw = _DefectiveThenFixedPlanGateway(remotion_dir)
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=gw,
        voice_engine=_SimpleVoice(),
        remotion_dir=remotion_dir,
    )
    job = service.create_job({"title": "Chairman Defect Rework", "language": "en", "market": "US"})

    phase_runs: list[str] = []

    def fake_run_phase(current_job: dict[str, Any], phase: str, workspace: Path) -> StageResult:
        phase_runs.append(phase)
        return StageResult(0, f"{phase} completed (run #{len(phase_runs)})", workspace / f"{phase}.log")

    monkeypatch.setattr(service, "_run_phase", fake_run_phase)
    monkeypatch.setattr(service, "_validate_artifacts", lambda *args: None)

    chat_responses = [
        json.dumps(
            {
                "approve_next": False,
                "rework_phase": True,
                "reason": "Phát hiện đoạn mở đầu lặp cấu trúc, yêu cầu @script viết lại ngay.",
            },
            ensure_ascii=False,
        ),
        json.dumps(
            {
                "approve_next": True,
                "rework_phase": False,
                "reason": "Bản sửa lần 2 đã đạt chuẩn xuất sắc, cho phép sang bước Voice.",
            },
            ensure_ascii=False,
        ),
    ]

    monkeypatch.setattr(
        service,
        "_run_chat_prompt",
        lambda *args, **kwargs: StageResult(0, chat_responses.pop(0), tmp_path / "chairman.log"),
    )

    service._run_sequence(job["id"], ["plan", "voice"], chairman_provider="gemini")

    updated = service.get_job(job["id"])
    assert phase_runs == ["plan", "plan", "voice"]
    assert updated["phases"]["plan"]["status"] == "succeeded"
    assert updated["phases"]["voice"]["status"] == "succeeded"
    assert updated["chairman_hold_reason"] is None


def test_edit_coordinator_runs_surgical_qa_rework_even_when_all_batches_marked_completed(tmp_path: Path):
    ws = tmp_path / "ws"
    remotion_dir = tmp_path / "CofiRemotion"
    ws.mkdir(parents=True, exist_ok=True)
    remotion_dir.mkdir(parents=True, exist_ok=True)

    beats = [
        {"beat_id": "B001", "narration_text": "First beat.", "target_duration_sec": 5.0},
        {"beat_id": "B002", "narration_text": "Second beat.", "target_duration_sec": 5.0},
    ]
    (ws / "visual_manifest.json").write_text(
        json.dumps({"target_duration_sec": 10.0, "beats": beats}, ensure_ascii=False),
        encoding="utf-8",
    )
    # Mark all beats already completed from Attempt 1
    (ws / "edit_progress.json").write_text(
        json.dumps(
            {
                "version": 1,
                "assigned_beat_ids": ["B001", "B002"],
                "completed_beat_ids": ["B001", "B002"],
                "pending_beat_ids": [],
                "status": "completed",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # Simulate @evidence_qa rejecting Attempt 1 with a concrete rework ticket
    fb_dir = ws / ".producer" / "qa_rejection_feedback"
    fb_dir.mkdir(parents=True, exist_ok=True)
    (fb_dir / "edit.md").write_text(
        "- Exact Rejection Blocker: Composition Documentary-job1 missing registration in src/Composition.tsx\n",
        encoding="utf-8",
    )

    prompts_captured: list[str] = []

    class _FakeEditGateway:
        def run_prompt_reusable(self, prompt: str, workspace: Path, label: str, use_remotion_root: bool = False) -> StageResult:
            prompts_captured.append(prompt)
            return StageResult(0, "Registered composition & fixed QA defect", Path(workspace) / ".producer" / label)

    class _FakeRemotionManager:
        def status(self) -> dict[str, Any]:
            return {"ok": False}

        def ensure_session(self, job: dict[str, Any], workspace: Path) -> None:
            return None

        def checkpoint(self, job: dict[str, Any], workspace: Path, note: str = "") -> dict[str, Any]:
            cp = {"saved_at": "2026-10-31T09:00:00Z", "note": note}
            (Path(workspace) / "edit_checkpoint.json").write_text(json.dumps(cp), encoding="utf-8")
            return cp

    coord = EditCoordinator(_FakeEditGateway(), _FakeRemotionManager(), remotion_dir)
    job = {"id": "job1", "language": "en", "market": "US", "visual_strategy": "full_ai"}
    res = coord.run(job, ws)

    assert res.returncode == 0
    assert len(prompts_captured) == 1
    assert "MANDATORY @evidence_qa REJECTION REWORK DIRECTIVE" in prompts_captured[0]
    assert "Composition Documentary-job1 missing registration" in prompts_captured[0]
    assert "SURGICAL QA REWORK EXECUTION" in prompts_captured[0]


def test_non_retriable_missing_binary_fails_fast_without_useless_loops(tmp_path: Path, monkeypatch):
    remotion_dir = tmp_path / "CofiRemotion"
    gw = _DefectiveThenFixedPlanGateway(remotion_dir)
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=gw,
        voice_engine=_SimpleVoice(),
        remotion_dir=remotion_dir,
    )
    job = service.create_job({"title": "Missing ffprobe infra failure"})
    calls = 0

    def fail_infra(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("Không tìm thấy ffprobe để kiểm tra file xuất")

    monkeypatch.setattr(service, "_run_phase", fail_infra)
    service._run_sequence(job["id"], ["plan"])

    state = service.get_job(job["id"])
    assert calls == 1
    assert state["status"] == "failed"
    assert "Không tìm thấy ffprobe" in state["phases"]["plan"]["error"]


def test_agent_office_renders_live_reworking_and_reworked_passed_telemetry(tmp_path: Path):
    remotion_dir = tmp_path / "CofiRemotion"
    gw = _DefectiveThenFixedPlanGateway(remotion_dir)
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=gw,
        voice_engine=_SimpleVoice(),
        remotion_dir=remotion_dir,
    )
    job = service.create_job({"title": "Live Office Rework View", "language": "en", "market": "US"})
    ws = Path(job["workspace"])
    ws.mkdir(parents=True, exist_ok=True)

    # Simulate live Attempt 2/3 rework in progress
    service._prepare_autonomous_phase_rework(
        job["id"],
        job,
        "plan",
        ws,
        attempt=1,
        max_attempts=3,
        reason="Script sentence cadence failed spoken rhythm check",
        source="validate_phase_quality",
    )

    snap_live = build_live_office_snapshot(service, job_id=job["id"])
    plan_gate_live = next(g for g in snap_live["critique_gates"] if g["phase"] == "plan")
    assert plan_gate_live["gate_state"] == "reworking_live"
    assert "2/3" in plan_gate_live["badge_vi"]

    agents_by_id = {a["id"]: a for a in snap_live["agents"]}
    assert agents_by_id["evidence_qa"]["live_state"] == "critiquing"
    assert agents_by_id["script"]["live_state"] == "reworking"
    assert any(
        lnk["from"] == "evidence_qa" and lnk["to"] == "script" and lnk["kind"] == "active_critique"
        for lnk in snap_live["links"]
    )

    # Simulate Attempt 2 succeeding -> gate_state transitions cleanly to 'reworked_and_passed'
    ledger_file = ws / ".producer" / "qa_rework_ledger" / "plan.json"
    ledger_data = json.loads(ledger_file.read_text(encoding="utf-8"))
    ledger_data["status"] = "reworked_and_passed"
    ledger_data["passed_on_attempt"] = 2
    ledger_file.write_text(json.dumps(ledger_data, ensure_ascii=False, indent=2), encoding="utf-8")
    service.store.update(
        job["id"],
        {"status": "ready", "phases": {"plan": {"status": "succeeded"}}},
    )

    snap_done = build_live_office_snapshot(service, job_id=job["id"])
    plan_gate_done = next(g for g in snap_done["critique_gates"] if g["phase"] == "plan")
    assert plan_gate_done["gate_state"] == "reworked_and_passed"

    # Verify App Core neutrality: 0 Hangul characters inside agent_office.py and all autonomous rework engines
    root_src = Path(__file__).resolve().parents[1] / "documentary"
    office_txt = (root_src / "agent_office.py").read_text(encoding="utf-8")
    assert not re.search(r"[\uac00-\ud7a3]", office_txt), "Hangul leaked into App Core agent_office.py!"
    for fn in (
        load_phase_qa_rejection_directive,
        DocumentaryService._phase_agent_pair,
        DocumentaryService._is_non_retriable_phase_error,
        DocumentaryService._prepare_autonomous_phase_rework,
        DocumentaryService._run_sequence,
    ):
        fn_src = inspect.getsource(fn)
        assert not re.search(r"[\uac00-\ud7a3]", fn_src), f"Hangul leaked into App Core {fn.__qualname__}!"
