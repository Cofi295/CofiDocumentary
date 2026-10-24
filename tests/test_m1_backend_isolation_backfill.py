"""
Automated Verification Suite for Milestone 1:
Backend Data Models, Strict Isolation & Data Backfill.
Verifies:
- Storage data integrity for all 4 channel profiles and all 4 jobs
- Backup preservation in data/backups/
- Separated Channel Profile endpoints (POST, POST .../clone, PUT, DELETE, GET)
- Strict Job Mutation Isolation (PATCH /api/jobs/{job_id})
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from server import create_app
from services.channel_profile_service import ChannelProfileService
from services.job_service import JobService

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROFILES_FILE = DATA_DIR / "channel_profiles.json"
JOBS_DIR = DATA_DIR / "jobs"
BACKUPS_DIR = DATA_DIR / "backups"


# ==============================================================================
# 1. STORAGE DATA INTEGRITY & BACKFILL VERIFICATION
# ==============================================================================

def test_backups_exist():
    """Verify non-destructive backups were created in data/backups/."""
    assert BACKUPS_DIR.exists(), "Backups directory must exist"
    backup_profiles = list(BACKUPS_DIR.glob("channel_profiles_*.json"))
    backup_jobs = [d for d in BACKUPS_DIR.iterdir() if d.is_dir() and "jobs" in d.name]
    assert len(backup_profiles) > 0, "At least one channel_profiles backup file must exist"
    assert len(backup_jobs) > 0, "At least one jobs backup directory must exist"


def test_channel_profiles_storage_integrity():
    """Verify all 4 channel profiles in storage have non-null required fields."""
    assert PROFILES_FILE.exists(), "channel_profiles.json must exist"
    data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profiles = {p["id"]: p for p in data.get("profiles", [])}

    required_ids = [
        "channel-1e24de3ab5",
        "channel-e544a64b7c",
        "channel-aa913eb90d",
        "channel-f6ec4dfff3",
    ]

    for pid in required_ids:
        assert pid in profiles, f"Profile {pid} must exist in storage"
        p = profiles[pid]

        # Top-level non-null fields
        assert p.get("id") == pid, f"Profile id must match {pid}"
        assert p.get("channel_profile_id") == pid, f"channel_profile_id must match {pid}"
        assert p.get("visual_strategy") in {"full_ai", "full_footage", "hybrid", "evidence_footage"}
        assert p.get("default_visual_strategy") in {"full_ai", "full_footage", "hybrid", "evidence_footage"}
        assert p.get("default_language") is not None
        assert p.get("default_duration_minutes") is not None

        # default_creative_brief schema completeness
        brief = p.get("default_creative_brief")
        assert isinstance(brief, dict), f"default_creative_brief in {pid} must be a dict"
        required_brief_keys = [
            "market", "language", "target_duration_minutes", "ai_media_mode",
            "narrative_angle", "writing_style", "hook_archetype", "editing_archetypes",
            "opening_hook", "notes"
        ]
        for key in required_brief_keys:
            assert brief.get(key) is not None, f"Field '{key}' in default_creative_brief of {pid} must not be null"
        assert isinstance(brief["editing_archetypes"], list)
        assert len(brief["editing_archetypes"]) > 0

        # editing_dna schema completeness
        dna = p.get("editing_dna")
        assert isinstance(dna, dict), f"editing_dna in {pid} must be a dict"
        required_dna_keys = [
            "pacing", "visual_mix", "editing_archetypes", "subtitle_style",
            "color_grade", "audio_rules"
        ]
        for key in required_dna_keys:
            assert dna.get(key) is not None, f"Field '{key}' in editing_dna of {pid} must not be null"
        assert isinstance(dna["visual_mix"], dict)
        assert "footage" in dna["visual_mix"] and "ai" in dna["visual_mix"] and "motion" in dna["visual_mix"]
        assert isinstance(dna["subtitle_style"], dict)
        assert dna["subtitle_style"].get("font_family") is not None
        assert isinstance(dna["audio_rules"], dict)
        assert dna["audio_rules"].get("music_ducking_db") is not None

        # self_learning_memory schema completeness
        slm = p.get("self_learning_memory")
        assert isinstance(slm, dict), f"self_learning_memory in {pid} must be a dict"
        for key in ["winners", "underperformers", "upgrade_rules"]:
            assert slm.get(key) is not None, f"Field '{key}' in self_learning_memory of {pid} must not be null"
        assert isinstance(slm["upgrade_rules"], dict)

        # editing_dna_history is list
        assert isinstance(p.get("editing_dna_history"), list)


def test_jobs_storage_integrity():
    """Verify all 4 existing jobs in storage have non-null required fields."""
    required_job_ids = [
        "20261018-223750-3aecfbcd",
        "20261017-164519-fd65f7e1",
        "20261017-003022-ecb75736",
        "20261015-014818-f0fdc122"
    ]

    for jid in required_job_ids:
        job_file = JOBS_DIR / jid / "job.json"
        assert job_file.exists(), f"Job file {job_file} must exist"
        job = json.loads(job_file.read_text(encoding="utf-8"))

        assert job.get("channel_profile_id") is not None, f"Job {jid} channel_profile_id must not be null"
        assert job.get("channel_profile_id") in {"channel-1e24de3ab5", "channel-e544a64b7c"}

        assert job.get("visual_strategy") in {"full_ai", "full_footage", "hybrid", "evidence_footage"}, (
            f"Job {jid} visual_strategy must be valid"
        )

        assert isinstance(job.get("default_creative_brief"), dict), f"Job {jid} default_creative_brief must be dict"
        assert len(job["default_creative_brief"]) > 0

        assert isinstance(job.get("editing_dna"), dict), f"Job {jid} editing_dna must be dict"
        assert len(job["editing_dna"]) > 0

        assert isinstance(job.get("channel_profile_snapshot"), dict), f"Job {jid} snapshot must be dict"
        assert len(job["channel_profile_snapshot"]) > 0


# ==============================================================================
# 2. SERVER ENDPOINTS & CHANNEL PROFILE SEPARATION VERIFICATION
# ==============================================================================

@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_get_channel_profiles_list(client):
    """GET /api/radar/channel-profiles returns all profiles with full schemas."""
    response = client.get("/api/radar/channel-profiles")
    assert response.status_code == 200
    profiles = response.json()
    assert isinstance(profiles, list)
    assert len(profiles) >= 4
    profile_ids = [p["id"] for p in profiles]
    assert "channel-1e24de3ab5" in profile_ids
    assert "channel-e544a64b7c" in profile_ids


def test_get_single_channel_profile(client):
    """GET /api/radar/channel-profiles/{profile_id} returns the specific profile or 404."""
    response = client.get("/api/radar/channel-profiles/channel-e544a64b7c")
    assert response.status_code == 200
    p = response.json()
    assert p["id"] == "channel-e544a64b7c"
    assert p["channel_profile_id"] == "channel-e544a64b7c"
    assert p["visual_strategy"] == "full_ai"

    not_found = client.get("/api/radar/channel-profiles/channel-non-existent")
    assert not_found.status_code == 404


def test_create_channel_profile_endpoint(client):
    """POST /api/radar/channel-profiles generates a new ID and populates full schema."""
    new_profile_payload = {
        "label": "Test Channel Architecture",
        "market": "US",
        "default_language": "en",
        "default_duration_minutes": 25,
        "default_visual_strategy": "hybrid",
        "allowed_topics": "Modern architecture failures",
        "forbidden_topics": "Celebrity gossip",
        "monetization_safety_policy": "Objective engineering review",
        "voice_and_structure": "Analytical narrative",
    }
    response = client.post("/api/radar/channel-profiles", json=new_profile_payload)
    assert response.status_code == 200
    created = response.json()
    created_id = created["id"]
    assert created_id.startswith("channel-")
    assert created["channel_profile_id"] == created_id
    assert created["label"] == "Test Channel Architecture"
    assert created["visual_strategy"] == "hybrid"
    assert isinstance(created["default_creative_brief"], dict)
    assert isinstance(created["editing_dna"], dict)
    assert isinstance(created["self_learning_memory"], dict)
    assert created["editing_dna_history"] == []

    # Clean up created test profile
    del_resp = client.delete(f"/api/radar/channel-profiles/{created_id}")
    assert del_resp.status_code == 200


def test_clone_channel_profile_endpoint(client):
    """POST /api/radar/channel-profiles/{profile_id}/clone creates new ID with ' (Clone)' suffix."""
    clone_resp = client.post("/api/radar/channel-profiles/channel-1e24de3ab5/clone")
    assert clone_resp.status_code == 200
    cloned = clone_resp.json()
    cloned_id = cloned["id"]

    assert cloned_id != "channel-1e24de3ab5"
    assert cloned_id.startswith("channel-")
    assert cloned["label"].endswith("(Clone)")
    assert cloned["visual_strategy"] == "hybrid"
    assert cloned["editing_dna_history"] == []

    # Clean up cloned profile
    del_resp = client.delete(f"/api/radar/channel-profiles/{cloned_id}")
    assert del_resp.status_code == 200


def test_update_channel_profile_put_preserves_unmentioned_fields(client):
    """PUT /api/radar/channel-profiles/{profile_id} updates in-place while preserving editing_dna & memory."""
    # First get original profile
    orig = client.get("/api/radar/channel-profiles/channel-aa913eb90d").json()
    orig_dna = orig["editing_dna"]
    orig_memory = orig["self_learning_memory"]

    # Update only label and notes
    patch = {
        "label": "bí mật US · Archival Vault (Updated Test)",
        "allowed_topics": "Updated allowed topics list",
    }
    put_resp = client.put("/api/radar/channel-profiles/channel-aa913eb90d", json=patch)
    assert put_resp.status_code == 200
    updated = put_resp.json()

    assert updated["label"] == "bí mật US · Archival Vault (Updated Test)"
    assert updated["allowed_topics"] == "Updated allowed topics list"
    # Unmentioned fields must be strictly preserved
    assert updated["editing_dna"]["color_grade"] == orig_dna["color_grade"]
    assert updated["editing_dna"]["pacing"] == orig_dna["pacing"]
    assert updated["self_learning_memory"]["analyzed_videos_count"] == orig_memory["analyzed_videos_count"]

    # Revert label back
    revert_patch = {"label": orig["label"], "allowed_topics": orig["allowed_topics"]}
    client.put("/api/radar/channel-profiles/channel-aa913eb90d", json=revert_patch)


# ==============================================================================
# 3. STRICT JOB MUTATION ISOLATION VERIFICATION
# ==============================================================================

def test_patch_job_strictly_mutates_only_target_job(client):
    """PATCH /api/jobs/{job_id} only mutates {job_id} and leaves other jobs intact."""
    target_job_id = "20261018-223750-3aecfbcd"
    other_job_id = "20261017-164519-fd65f7e1"

    # Read original states
    other_job_orig = client.get(f"/api/jobs/{other_job_id}").json()
    target_job_orig = client.get(f"/api/jobs/{target_job_id}").json()

    # Apply patch to target_job_id
    patch_payload = {
        "notes": "Verified isolation patch test",
        "market": "KR",
    }
    patch_resp = client.patch(f"/api/jobs/{target_job_id}", json=patch_payload)
    assert patch_resp.status_code == 200
    target_updated = patch_resp.json()
    assert target_updated["notes"] == "Verified isolation patch test"

    # Verify other job was completely untouched
    other_job_after = client.get(f"/api/jobs/{other_job_id}").json()
    assert other_job_after["notes"] == other_job_orig["notes"]
    assert other_job_after["title"] == other_job_orig["title"]
    assert other_job_after["channel_profile_id"] == other_job_orig["channel_profile_id"]

    # Revert target job notes back
    client.patch(f"/api/jobs/{target_job_id}", json={"notes": target_job_orig["notes"]})


def test_patch_job_returns_404_for_non_existent_job(client):
    """PATCH /api/jobs/{job_id} returns 404 if job does not exist."""
    resp = client.patch("/api/jobs/job-does-not-exist-9999", json={"notes": "test"})
    assert resp.status_code == 404


def test_patch_job_rejects_cross_job_mutation_attempt(client):
    """PATCH /api/jobs/{job_id} rejects payload if payload attempts to target another job ID."""
    resp = client.patch(
        "/api/jobs/20261018-223750-3aecfbcd",
        json={"job_id": "20261017-164519-fd65f7e1", "notes": "sneaky mutation"}
    )
    assert resp.status_code == 400
    assert "Cross-job mutation rejected" in resp.json()["detail"]


def test_patch_job_rejects_draft_mutation_side_effects(client):
    """PATCH /api/jobs/{job_id} rejects draft mutation side-effects."""
    resp = client.patch(
        "/api/jobs/20261018-223750-3aecfbcd",
        json={"is_draft": True, "notes": "draft override"}
    )
    assert resp.status_code == 400
    assert "Draft mutation side-effects rejected" in resp.json()["detail"]


# ==============================================================================
# 4. JOB CREATION & PROFILE INHERITANCE VERIFICATION (M1 Iteration 2)
# ==============================================================================

def test_create_job_inherits_channel_profile_dna(client):
    """
    POST /api/jobs creates a project that inherits locked editing_dna and
    creative brief from the designated channel profile, persisting to disk.
    """
    payload = {
        "title": "Automated DNA Inheritance Test Project",
        "channel_profile_id": "channel-1e24de3ab5",
        "market": "KR",
    }
    resp = client.post("/api/jobs", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    job_id = data["id"]

    try:
        # 1. API Response Verification
        assert data.get("channel_profile_id") == "channel-1e24de3ab5"
        assert data.get("visual_strategy") == "hybrid"

        editing_dna = data.get("editing_dna")
        assert isinstance(editing_dna, dict), "editing_dna must be returned as a dictionary"
        for key in ["pacing", "visual_mix", "editing_archetypes", "subtitle_style", "color_grade", "audio_rules"]:
            assert key in editing_dna, f"Field '{key}' missing from inherited editing_dna"

        default_brief = data.get("default_creative_brief")
        assert isinstance(default_brief, dict), "default_creative_brief must be returned as a dictionary"
        for key in ["market", "language", "target_duration_minutes", "ai_media_mode", "writing_style", "editing_archetypes"]:
            assert key in default_brief, f"Field '{key}' missing from inherited default_creative_brief"

        snapshot = data.get("channel_profile_snapshot")
        assert isinstance(snapshot, dict)
        assert snapshot.get("id") == "channel-1e24de3ab5"

        # 2. Disk Persistence Verification
        disk_file = JOBS_DIR / job_id / "job.json"
        assert disk_file.exists(), f"Job file on disk {disk_file} must exist"
        disk_data = json.loads(disk_file.read_text(encoding="utf-8"))

        assert disk_data.get("editing_dna"), "editing_dna must be persisted in job.json on disk"
        assert disk_data.get("default_creative_brief"), "default_creative_brief must be persisted on disk"
        assert disk_data.get("channel_profile_id") == "channel-1e24de3ab5"
        assert disk_data["editing_dna"]["color_grade"] == editing_dna["color_grade"]

    finally:
        # Cleanup
        client.delete(f"/api/jobs/{job_id}")


def test_create_job_rejects_non_existent_channel_profile(client):
    """
    POST /api/jobs with invalid channel_profile_id returns HTTP 400 or 404
    instead of silently creating an unlinked project with fallback defaults.
    """
    resp = client.post("/api/jobs", json={
        "title": "Invalid Profile Project",
        "channel_profile_id": "channel-ghost-99999",
    })
    assert resp.status_code in {400, 404}
    assert "channel-ghost-99999" in resp.json().get("detail", "") or "not found" in resp.json().get("detail", "").lower()


def test_patch_job_rejects_non_dict_payload_with_400(client):
    """
    PATCH /api/jobs/{job_id} with non-dict payload cleanly returns HTTP 400 Bad Request,
    not HTTP 500 Internal Server Error.
    """
    resp = client.patch("/api/jobs/20261018-223750-3aecfbcd", json=["invalid", "array"])
    assert resp.status_code == 400
    assert "JSON object" in resp.json().get("detail", "")
