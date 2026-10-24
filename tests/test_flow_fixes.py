"""Regression tests for the pipeline fixes from the flow audit (2026-10-04)."""
from __future__ import annotations

import json
from pathlib import Path

from documentary.ai_visual import AIVisualCoordinator
from documentary.visuals import PLAN_MANIFEST_NAME, VisualsCoordinator, load_plan_manifest
from documentary.voice import CofiVoiceEngine
from tests.test_ai_visual import FakeFlowRunner, WindowTrackingQueueRunner, write_workspace


# --- 1.1 Voice rerun after Visuals keeps plan-level beat IDs -----------------

PLAN = {
    "target_duration_sec": 10,
    "beats": [
        {"beat_id": "B001", "narration_text": "First clause, second clause.", "source_priority": "prefer_real"},
        {"beat_id": "B002", "narration_text": "Third sentence here.", "source_priority": "ai_ok"},
    ],
}
SCRIPT = "First clause, second clause. Third sentence here."


def _write_voice_manifest(workspace: Path) -> None:
    (workspace / "voice_manifest.json").write_text(json.dumps({
        "duration_sec": 6.0,
        "beats": [
            {"beat_id": "B001", "text": "First clause, second clause.", "start_sec": 0.0, "end_sec": 3.0},
            {"beat_id": "B002", "text": "Third sentence here.", "start_sec": 3.0, "end_sec": 6.0},
        ],
    }), encoding="utf-8")


def _prepare(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "script.md").write_text(SCRIPT, encoding="utf-8")
    (workspace / "visual_manifest.json").write_text(json.dumps(PLAN), encoding="utf-8")
    _write_voice_manifest(workspace)


def test_visuals_snapshots_plan_and_rerun_does_not_resplit_units(tmp_path: Path):
    _prepare(tmp_path)
    coordinator = VisualsCoordinator()
    coordinator.run({"visual_strategy": "hybrid"}, tmp_path)

    assert json.loads((tmp_path / PLAN_MANIFEST_NAME).read_text(encoding="utf-8")) == PLAN
    first_ids = [b["beat_id"] for b in json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))["beats"]]
    assert first_ids == ["B001-V01", "B001-V02", "B002-V01"]

    coordinator.run({"visual_strategy": "hybrid"}, tmp_path)
    second_ids = [b["beat_id"] for b in json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))["beats"]]
    assert second_ids == first_ids
    assert json.loads((tmp_path / PLAN_MANIFEST_NAME).read_text(encoding="utf-8")) == PLAN


def test_load_plan_manifest_rebuilds_legacy_workspace_without_snapshot(tmp_path: Path):
    _prepare(tmp_path)
    VisualsCoordinator().run({"visual_strategy": "hybrid"}, tmp_path)
    (tmp_path / PLAN_MANIFEST_NAME).unlink()

    plan = load_plan_manifest(tmp_path)

    assert [b["beat_id"] for b in plan["beats"]] == ["B001", "B002"]
    assert plan["beats"][0]["narration_text"] == "First clause, second clause."
    assert "parent_beat_id" not in plan["beats"][0]
    assert plan["beats"][1]["source_priority"] == "ai_ok"


class _FakeResponse:
    def __init__(self, content: bytes):
        self.content = content
        self.headers = {}

    def raise_for_status(self):
        return None


class _FakeTTSSession:
    def __init__(self):
        self.texts: list[str] = []

    def post(self, url, json=None, timeout=None):
        import io
        import wave

        self.texts.append(json["text"])
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(8000)
            handle.writeframes(b"\x00\x00" * 8000)
        return _FakeResponse(buffer.getvalue())


def test_voice_rerun_after_visuals_uses_plan_beats(tmp_path: Path):
    _prepare(tmp_path)
    VisualsCoordinator().run({"visual_strategy": "hybrid"}, tmp_path)
    session = _FakeTTSSession()

    CofiVoiceEngine(session=session).run({"language": "en"}, tmp_path)

    voice = json.loads((tmp_path / "voice_manifest.json").read_text(encoding="utf-8"))
    assert [b["beat_id"] for b in voice["beats"]] == ["B001", "B002"]
    assert session.texts == ["First clause, second clause.", "Third sentence here."]


# --- AI Visual: keep keyframes when media mode changes ----------------------

def test_switching_media_mode_reuses_existing_keyframes(tmp_path: Path):
    write_workspace(tmp_path, [{"beat_id": "B001", "visual_type": "sourced_still", "narration_text": "x"}])
    job_image = {"ai_visual": {"coverage_mode": "full_ai", "ai_media_mode": "image"}}
    AIVisualCoordinator(tool_runner=FakeFlowRunner()).run(job_image, tmp_path)

    runner = FakeFlowRunner()
    job_mixed = {"ai_visual": {"coverage_mode": "full_ai", "ai_media_mode": "mixed"}}
    result = AIVisualCoordinator(tool_runner=runner).run(job_mixed, tmp_path)

    assert result.returncode == 0
    assert runner.calls == []


# --- AI Visual: Veo failure streak falls back to animated stills ------------

class _VideoAlwaysFailsQueueRunner(WindowTrackingQueueRunner):
    def wait(self, ticket):
        scene = self.scenes.get(str(ticket.get("job_id") or ""), {})
        if scene.get("task_type") == "image_to_video":
            self.outstanding -= 1
            self.events.append(("wait-failed", scene["id"]))
            raise RuntimeError("unusual activity")
        return super().wait(ticket)


def test_veo_failure_streak_stops_submitting_and_completes_with_stills(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_AI_VISUAL_VIDEO_FAIL_STREAK", "2")
    monkeypatch.setenv("COFI_AI_VISUAL_OUTSTANDING_LIMIT", "1")
    beats = [
        {"beat_id": f"B{index:03d}", "visual_type": "sourced_video", "narration_text": f"beat {index}"}
        for index in range(1, 7)
    ]
    write_workspace(tmp_path, beats)
    runner = _VideoAlwaysFailsQueueRunner(tmp_path)

    result = AIVisualCoordinator(tool_runner=runner).run(
        {"ai_visual": {"veo_enabled": True, "coverage_mode": "full_ai", "ai_media_mode": "video"}},
        tmp_path,
    )

    assert result.returncode == 0
    video_submits = [event for event in runner.events if event[0] == "submit" and event[1].endswith("_ai_video")]
    assert len(video_submits) == 2
    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert manifest["remaining_missing_beats"] == []
    assert manifest["still_fallback_beats"] == [beat["beat_id"] for beat in beats]
    assert "dừng gửi thêm" in (manifest["warning"] or "")
    registry = json.loads((tmp_path / "asset_registry.json").read_text(encoding="utf-8"))
    assert all(
        asset["source"].get("motion_fallback") == "remotion_camera_move"
        for asset in registry["assets"]
        if asset["source"].get("generated_by") == "cofi_ai_visual"
    )


def test_still_fallback_can_be_disabled_per_job(tmp_path: Path):
    write_workspace(tmp_path, [{"beat_id": "B001", "visual_type": "sourced_video", "narration_text": "x"}])
    runner = _VideoAlwaysFailsQueueRunner(tmp_path)

    try:
        AIVisualCoordinator(tool_runner=runner).run(
            {"ai_visual": {
                "veo_enabled": True, "coverage_mode": "full_ai", "ai_media_mode": "video",
                "video_still_fallback": False,
            }},
            tmp_path,
        )
    except RuntimeError as exc:
        assert "vẫn thiếu beat" in str(exc)
    else:
        raise AssertionError("expected AI Visual to stay incomplete when still fallback is disabled")


# --- 1.5 Full Footage cannot hand gaps to a non-existent AI phase -------------

def _footage_gate_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "visual_manifest.json").write_text(json.dumps({"beats": [
        {"beat_id": "B001"}, {"beat_id": "B002"},
    ]}), encoding="utf-8")
    (workspace / "asset_registry.json").write_text(json.dumps({
        "assets": [{"id": "A1", "beat_id": "B001", "source": {"url": "https://example.org"}}],
        "ai_fallback_beats": ["B002"],
    }), encoding="utf-8")


def _gate_job(strategy: str) -> dict:
    return {"visual_strategy": strategy, "production_recipe": {"quality_contract": {
        "enforce": True, "min_scene_count": 1, "require_must_real_source_coverage": False,
        "visual_strategy": strategy,
    }}}


def test_full_footage_gate_rejects_ai_fallback_beats(tmp_path: Path):
    from documentary.quality import validate_phase_quality

    _footage_gate_workspace(tmp_path)
    try:
        validate_phase_quality("footage", tmp_path, _gate_job("full_footage"))
    except RuntimeError as exc:
        assert "B002" in str(exc) and "thiếu tư liệu" in str(exc)
    else:
        raise AssertionError("Full Footage must not accept AI fallback beats as coverage")


def test_hybrid_gate_still_accepts_ai_fallback_beats(tmp_path: Path):
    from documentary.quality import validate_phase_quality

    _footage_gate_workspace(tmp_path)
    validate_phase_quality("footage", tmp_path, _gate_job("hybrid"))


# --- 1.2 Hybrid beats routed to AI are not searched ---------------------------

def _hybrid_manifest(workspace: Path, routes: dict[str, str]) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "visual_manifest.json").write_text(json.dumps({
        "visual_strategy": "hybrid",
        "beats": [
            {"beat_id": beat_id, "target_duration_sec": 5, "visual_route": route}
            for beat_id, route in routes.items()
        ],
    }), encoding="utf-8")


def test_hybrid_footage_skips_search_for_ai_routed_beats(tmp_path: Path):
    from documentary.footage import FootageCoordinator
    from tests.test_footage import DisabledGemini, FakeBatchGateway

    _hybrid_manifest(tmp_path, {"B001": "footage", "B002": "ai_visual"})
    gateway = FakeBatchGateway()
    result = FootageCoordinator(gateway, DisabledGemini(), batch_size=4, batch_retries=0).run(
        {"id": "job-h", "title": "t", "footage_mode": "codex", "visual_strategy": "hybrid"}, tmp_path,
    )

    assert result.returncode == 0
    assert gateway.calls == [["B001"]]
    registry = json.loads((tmp_path / "asset_registry.json").read_text(encoding="utf-8"))
    assert "B002" in registry.get("ai_fallback_beats", [])


def test_hybrid_footage_all_ai_routed_needs_no_worker(tmp_path: Path):
    from documentary.footage import FootageCoordinator
    from tests.test_footage import DisabledGemini, FakeBatchGateway

    _hybrid_manifest(tmp_path, {"B001": "ai_visual", "B002": "ai_visual"})
    gateway = FakeBatchGateway()
    result = FootageCoordinator(gateway, DisabledGemini(), batch_size=4, batch_retries=0).run(
        {"id": "job-h", "title": "t", "footage_mode": "codex", "visual_strategy": "hybrid"}, tmp_path,
    )

    assert result.returncode == 0
    assert gateway.calls == []
    registry = json.loads((tmp_path / "asset_registry.json").read_text(encoding="utf-8"))
    assert set(registry.get("ai_fallback_beats", [])) == {"B001", "B002"}
