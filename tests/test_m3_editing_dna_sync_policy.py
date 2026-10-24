"""
Unit & Integration Tests for Milestone 3:
- EditingDnaService (extraction, presets, versioning, lock-edit-dna, inheritance)
- SyncPolicyService (voice/SRT sync, drift, hold freeze > 8s, Ken Burns auto-repair, YouTube policy)
- Server REST API Endpoints:
  * POST /api/jobs/{job_id}/lock-edit-dna
  * GET /api/jobs/{job_id}/sync-compliance
  * POST /api/jobs/{job_id}/auto-repair-sync
"""

from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient

from server import create_app
from services.editing_dna_service import EditingDnaService, BUILTIN_EDITING_PRESETS, PacingDict
from services.sync_policy_service import SyncPolicyService, parse_srt

ROOT = Path(__file__).resolve().parents[1]


# ==============================================================================
# EDITING DNA SERVICE TESTS
# ==============================================================================

def test_editing_dna_presets_complete_schema():
    """Verify all 4 built-in presets conform to the required schema."""
    service = EditingDnaService()
    presets = service.get_presets()
    expected_keys = [
        "preset_id", "name", "version", "pacing", "visual_mix",
        "editing_archetypes", "subtitle_style", "color_grade", "audio_rules"
    ]
    for pid in ["2.5d_technical", "forensic_noir", "archival_historical", "custom"]:
        assert pid in presets, f"Missing preset {pid}"
        p = presets[pid]
        for k in expected_keys:
            assert k in p, f"Missing key {k} in preset {pid}"
        assert float(p["pacing"]) > 0
        assert p["pacing"]["target_beat_duration_sec"] > 0
        assert len(p["editing_archetypes"]) > 0


def test_editing_dna_extraction_real_workspace():
    """Verify extraction from real workspace '20261018-223750-3aecfbcd'."""
    service = EditingDnaService()
    dna = service.extract_editing_dna_from_job("20261018-223750-3aecfbcd")
    assert dna["preset_id"] in BUILTIN_EDITING_PRESETS
    assert dna["version"] == 1
    assert float(dna["pacing"]) > 0
    assert dna["visual_mix"]["footage_ratio"] + dna["visual_mix"]["ai_visual_ratio"] + dna["visual_mix"]["motion_overlay_ratio"] > 0.95
    assert len(dna["editing_archetypes"]) > 0
    assert "font_family" in dna["subtitle_style"]
    assert "tone_preset" in dna["color_grade"]


def test_editing_dna_extraction_fallback_empty_workspace(tmp_path: Path):
    """Verify graceful fallback to custom preset when workspace is empty."""
    service = EditingDnaService(workspaces_dir=tmp_path / "workspaces", jobs_dir=tmp_path / "jobs")
    dna = service.extract_editing_dna_from_job("nonexistent_job")
    assert dna["preset_id"] == "custom"
    assert dna["version"] == 1
    assert dna["pacing"]["target_beat_duration_sec"] == 5.0


def test_lock_edit_dna_without_channel_profile_error(tmp_path: Path):
    """Verify locking edit DNA on an unassigned job raises ValueError."""
    jobs_dir = tmp_path / "jobs"
    job_id = "test_unassigned_job"
    (jobs_dir / job_id).mkdir(parents=True)
    (jobs_dir / job_id / "job.json").write_text(json.dumps({
        "id": job_id,
        "title": "Unassigned Job",
        "channel_profile_id": None
    }))

    service = EditingDnaService(jobs_dir=jobs_dir, profiles_file=tmp_path / "channel_profiles.json")
    with pytest.raises(ValueError, match="no assigned channel profile"):
        service.lock_job_edit_dna_to_channel(job_id)


def test_lock_edit_dna_persists_to_channel_profile_and_increments_version(tmp_path: Path):
    """Verify locking edit DNA updates channel profile and increments version with history."""
    profiles_file = tmp_path / "channel_profiles.json"
    jobs_dir = tmp_path / "jobs"
    ws_dir = tmp_path / "workspaces"

    profile_id = "channel-test-lock-1"
    initial_dna = dict(BUILTIN_EDITING_PRESETS["forensic_noir"])
    initial_dna["version"] = 1

    profiles_file.write_text(json.dumps({
        "profiles": [{
            "id": profile_id,
            "label": "Test Channel",
            "market": "KR",
            "allowed_topics": "True Crime",
            "competitor_refs": ["https://youtube.com/@crime"],
            "editing_dna": initial_dna,
            "editing_dna_history": []
        }]
    }, indent=2))

    job_id = "job-lock-1"
    (jobs_dir / job_id).mkdir(parents=True)
    (jobs_dir / job_id / "job.json").write_text(json.dumps({
        "id": job_id,
        "title": "Test Murder Mystery",
        "channel_profile_id": profile_id,
    }))
    (ws_dir / job_id).mkdir(parents=True)
    (ws_dir / job_id / "visual_manifest.json").write_text(json.dumps({
        "beats": [
            {"beat_id": "B01", "duration_sec": 4.5, "visual_type": "ai_visual"},
            {"beat_id": "B02", "duration_sec": 5.5, "visual_type": "ai_visual"},
        ]
    }))

    service = EditingDnaService(profiles_file=profiles_file, jobs_dir=jobs_dir, workspaces_dir=ws_dir)
    res = service.lock_job_edit_dna_to_channel(job_id, notes="Approved edit lock v2")

    assert res["status"] == "success"
    assert res["version"] == 2
    assert res["editing_dna"]["version"] == 2
    assert res["locked_job_id"] == job_id
    assert res["history_count"] == 1

    # Verify channel profile on disk
    saved = json.loads(profiles_file.read_text())["profiles"][0]
    assert saved["editing_dna"]["version"] == 2
    assert saved["editing_dna"]["locked_from_job_id"] == job_id
    assert saved["allowed_topics"] == "True Crime"  # Preserved
    assert len(saved["editing_dna_history"]) == 1
    assert saved["editing_dna_history"][0]["version"] == 1


# ==============================================================================
# SYNC POLICY SERVICE TESTS
# ==============================================================================

def test_sync_policy_drift_and_hold_detection():
    """Verify drift > 0.5s and holds > 8.0s are detected correctly."""
    service = SyncPolicyService()
    beats = [
        {"beat_id": "B001", "duration_sec": 9.5, "has_motion_override": False},
        {"beat_id": "B002", "duration_sec": 4.0, "has_motion_override": False},
    ]
    srt = [
        {"start": 0.0, "end": 9.5, "text": "Segment 1"},
        {"start": 9.5, "end": 15.0, "text": "Segment 2"},  # 1.5s drift
    ]
    scorecard = service.check_sync_compliance(beats=beats, srt_segments=srt, script_text="Clean documentary text")

    sync = scorecard["sync_scorecard"]
    assert len(sync["holds_over_8s"]) == 1
    assert sync["holds_over_8s"][0]["beat_id"] == "B001"
    assert len(sync["misaligned_beats"]) == 1
    assert sync["misaligned_beats"][0]["drift_sec"] == 1.5
    assert sync["passed"] is False


def test_sync_policy_youtube_graphic_content_filtering():
    """Verify violent and prohibited terms are caught across languages."""
    service = SyncPolicyService()
    dirty_vn = "Hiện trường vụ việc có thi thể đẫm máu bị chặt đầu man rợ."
    clean_vn = "Các kỹ sư tiến hành kiểm tra địa chất và độ lún của nền móng."

    rep_dirty = service.check_sync_compliance(beats=[], srt_segments=[], script_text=dirty_vn)
    rep_clean = service.check_sync_compliance(beats=[], srt_segments=[], script_text=clean_vn)

    assert rep_dirty["policy_scorecard"]["green_monetization"] is False
    assert len(rep_dirty["policy_scorecard"]["flagged_terms"]) >= 1
    assert rep_clean["policy_scorecard"]["green_monetization"] is True
    assert len(rep_clean["policy_scorecard"]["flagged_terms"]) == 0


def test_sync_policy_auto_repair(tmp_path: Path):
    """Verify auto-repair realigns timestamps and injects Ken Burns into holds > 8s."""
    ws_dir = tmp_path / "workspaces"
    jobs_dir = tmp_path / "jobs"
    job_id = "test_repair_job"
    (ws_dir / job_id).mkdir(parents=True)
    (jobs_dir / job_id).mkdir(parents=True)

    unrepaired_manifest = {
        "version": 1,
        "beats": [
            {"beat_id": "B001", "duration_sec": 10.0, "has_motion_override": False},
            {"beat_id": "B002", "duration_sec": 3.0, "has_motion_override": False},
        ]
    }
    (ws_dir / job_id / "visual_manifest.json").write_text(json.dumps(unrepaired_manifest))
    (ws_dir / job_id / "subtitles.srt").write_text(
        "1\n00:00:00,000 --> 00:00:09,000\nCau 1\n\n2\n00:00:09,000 --> 00:00:14,000\nCau 2\n"
    )

    service = SyncPolicyService(workspaces_dir=ws_dir, jobs_dir=jobs_dir)
    res = service.auto_repair_sync(job_id)

    assert res["status"] == "success"
    assert res["realigned_beats_count"] >= 1
    assert res["repaired_holds_count"] == 1

    # Verify updated manifest
    repaired = json.loads((ws_dir / job_id / "visual_manifest.json").read_text())
    b1 = repaired["beats"][0]
    assert b1["duration_sec"] == 9.0
    assert b1["has_motion_override"] is True
    assert b1["ken_burns_zoom"]["start_scale"] == 1.02
    assert b1["ken_burns_zoom"]["end_scale"] == 1.08
    assert b1["telemetry_hud_overlay"] is True

    b2 = repaired["beats"][1]
    assert b2["duration_sec"] == 5.0


def test_parse_srt_utility():
    """Verify parse_srt parses comma and dot timestamps accurately."""
    srt = "1\n00:00:01,250 --> 00:00:04,500\nText line 1\n\n2\n00:00:04.500 --> 00:00:08.000\nText line 2\n"
    segs = parse_srt(srt)
    assert len(segs) == 2
    assert segs[0]["start"] == 1.25
    assert segs[0]["end"] == 4.5
    assert segs[0]["text"] == "Text line 1"


# ==============================================================================
# SERVER REST API ENDPOINT TESTS
# ==============================================================================

def test_server_api_lock_edit_dna_and_sync_compliance():
    """Verify REST API routes in server.py."""
    app = create_app()
    client = TestClient(app)

    # 1. GET /api/jobs/{job_id}/sync-compliance
    res_sync = client.get("/api/jobs/20261018-223750-3aecfbcd/sync-compliance")
    assert res_sync.status_code == 200
    sync_data = res_sync.json()
    assert "sync_scorecard" in sync_data
    assert "policy_scorecard" in sync_data
    assert "overall_status" in sync_data

    # 2. POST /api/jobs/{job_id}/lock-edit-dna
    res_lock = client.post(
        "/api/jobs/20261018-223750-3aecfbcd/lock-edit-dna",
        json={"notes": "E2E REST API lock test"}
    )
    assert res_lock.status_code == 200
    lock_data = res_lock.json()
    assert lock_data["status"] == "success"
    assert "version" in lock_data
    assert lock_data["version"] >= 2
    assert lock_data["channel_profile_id"] == "channel-1e24de3ab5"

    # 3. POST /api/jobs/{job_id}/auto-repair-sync
    res_repair = client.post("/api/jobs/20261018-223750-3aecfbcd/auto-repair-sync")
    assert res_repair.status_code == 200
    repair_data = res_repair.json()
    assert repair_data["status"] == "success"
    assert "realigned_beats_count" in repair_data
    assert "scorecard" in repair_data
