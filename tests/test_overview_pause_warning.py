from __future__ import annotations

import json
from pathlib import Path

from documentary.service import DocumentaryService
from documentary.store import JobStore
from tests.test_service import FakeGateway, FakeVoice, FakeFootage


def make_service(tmp_path: Path):
    store = JobStore(tmp_path / "jobs")
    return DocumentaryService(
        root=tmp_path,
        store=store,
        gateway=FakeGateway(),
        voice_engine=FakeVoice(),
        footage_coordinator=FakeFootage(),
        remotion_dir=tmp_path / "CofiRemotion",
    )


def test_overview_pipeline_and_selected_job_exposes_interrupted_pause_and_error(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Interrupted test"})
    workspace = Path(job["workspace"])
    service.store.update(job["id"], {
        "status": "interrupted",
        "current_phase": "ai_visual",
        "phases": {
            "plan": {"status": "succeeded"},
            "voice": {"status": "succeeded"},
            "visuals": {"status": "succeeded"},
            "footage": {"status": "succeeded"},
            "ai_visual": {
                "status": "interrupted",
                "error": "Phiên trước bị ngắt. Có thể tiếp tục từ checkpoint hiện có.",
            },
        },
    })
    (workspace / "ai_visual_manifest.json").write_text(json.dumps({
        "status": "paused",
        "pause_warning": "Hàng đợi Media Factory đang ở trạng thái tạm dừng (paused).",
        "target_beat_ids": ["B001", "B002"],
        "remaining_missing_beats": ["B001", "B002"],
        "generated": [],
        "errors": [{"beat_id": "B001", "stage": "image", "error": "No Google Flow project is available."}],
    }), encoding="utf-8")

    enriched_job = service.get_job(job["id"])
    ai_phase = enriched_job["phases"]["ai_visual"]
    assert ai_phase["is_paused"] is True
    assert "Hàng đợi Media Factory đang ở trạng thái tạm dừng" in ai_phase["pause_warning"]
    assert "⚠️ [TẠM DỪNG]" in ai_phase["error"]
    assert "No Google Flow project is available" in ai_phase["error"]

    context = service.producer_chat_context(job["id"], "overview")
    selected = context["selected_job"]
    assert selected["is_paused"] is True
    assert "Hàng đợi Media Factory" in selected["pause_warning"]
    assert "No Google Flow project is available" in selected["last_error"]
    assert "⚠️ [TẠM DỪNG]" in context["live_progress"]["status_message"]
    assert "No Google Flow project is available" in context["live_progress"]["status_message"]
