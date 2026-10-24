#!/usr/bin/env python3
"""
Independent Forensic Verification Suite for Milestone 1.
Author: auditor_m1_1
Sole purpose: Independently stress-test and verify persistence, isolation, backfill, and server routing.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data"
PROFILES_FILE = DATA_DIR / "channel_profiles.json"
JOBS_DIR = DATA_DIR / "jobs"
BACKUPS_DIR = DATA_DIR / "backups"
RADAR_DB = Path(r"B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db")


def log(msg: str):
    print(f"[AUDIT] {msg}", flush=True)


def check_radar_db():
    log("Checking Radar SQLite DB preservation...")
    if not RADAR_DB.exists():
        raise AssertionError(f"Radar DB missing at {RADAR_DB}")
    conn = sqlite3.connect(str(RADAR_DB))
    c = conn.cursor()
    c.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
    t_count = c.fetchone()[0]
    c.execute("SELECT count(*) FROM videos")
    v_count = c.fetchone()[0]
    c.execute("SELECT count(*) FROM channels")
    c_count = c.fetchone()[0]
    conn.close()
    log(f"Radar DB intact: {t_count} tables, {c_count} channels, {v_count} videos.")
    assert t_count > 0, "No tables in Radar DB"
    assert v_count > 0, "No videos in Radar DB"


def check_backups():
    log("Checking backup archives...")
    if not BACKUPS_DIR.exists():
        raise AssertionError("Backups dir missing")
    profile_backups = list(BACKUPS_DIR.glob("channel_profiles_*.json"))
    job_backups = [d for d in BACKUPS_DIR.iterdir() if d.is_dir() and "jobs" in d.name]
    log(f"Found {len(profile_backups)} profile backups and {len(job_backups)} job backups.")
    assert len(profile_backups) >= 1, "Missing profile backups"
    assert len(job_backups) >= 1, "Missing job backups"


def check_channel_profiles_storage_and_backfill():
    log("Checking channel_profiles.json schema and real data preservation...")
    assert PROFILES_FILE.exists(), "channel_profiles.json missing"
    raw_text = PROFILES_FILE.read_text(encoding="utf-8")
    data = json.loads(raw_text)
    profiles = {p["id"]: p for p in data.get("profiles", [])}

    expected_ids = ["channel-1e24de3ab5", "channel-e544a64b7c", "channel-aa913eb90d", "channel-f6ec4dfff3"]
    for pid in expected_ids:
        assert pid in profiles, f"Profile {pid} missing from channel_profiles.json"
        p = profiles[pid]

        # Check non-null top-level
        assert p.get("id") == pid, f"Mismatched id for {pid}"
        assert p.get("channel_profile_id") == pid, f"Mismatched channel_profile_id for {pid}"
        assert p.get("visual_strategy") in {"full_ai", "full_footage", "hybrid", "evidence_footage"}
        assert p.get("default_visual_strategy") in {"full_ai", "full_footage", "hybrid", "evidence_footage"}
        assert p.get("default_language") is not None
        assert p.get("language") is not None
        assert p.get("default_duration_minutes") is not None
        assert p.get("target_duration_minutes") is not None
        assert p.get("default_ai_media_mode") is not None
        assert p.get("ai_media_mode") is not None

        # Check brief 10 keys
        brief = p.get("default_creative_brief") or {}
        assert isinstance(brief, dict) and len(brief) >= 10, f"Incomplete brief in {pid}"
        for k in ["market", "language", "target_duration_minutes", "ai_media_mode", "visual_strategy",
                  "narrative_angle", "writing_style", "hook_archetype", "editing_archetypes", "opening_hook", "notes"]:
            assert brief.get(k) is not None, f"Null key {k} in brief of {pid}"

        # Check editing_dna 6 keys
        dna = p.get("editing_dna") or {}
        assert isinstance(dna, dict) and len(dna) >= 6, f"Incomplete editing_dna in {pid}"
        for k in ["pacing", "visual_mix", "editing_archetypes", "subtitle_style", "color_grade", "audio_rules"]:
            assert dna.get(k) is not None, f"Null key {k} in editing_dna of {pid}"

        # Check self_learning_memory
        slm = p.get("self_learning_memory") or {}
        assert isinstance(slm, dict), f"self_learning_memory not dict in {pid}"
        for k in ["winners", "underperformers", "upgrade_rules"]:
            assert slm.get(k) is not None, f"Null key {k} in self_learning_memory of {pid}"

        # Check real YouTube data preservation
        if pid in ["channel-aa913eb90d", "channel-f6ec4dfff3"]:
            assert p.get("own_channel_ref"), f"Profile {pid} lost its YouTube channel ref!"
            assert p.get("competitor_refs"), f"Profile {pid} lost competitor refs!"
            assert p.get("competitors"), f"Profile {pid} lost competitor scan data!"

    log(f"All {len(expected_ids)} channel profiles verified with complete non-null schemas and preserved real YouTube data.")


def check_jobs_storage_and_backfill():
    log("Checking data/jobs/ storage and backfill bindings...")
    assert JOBS_DIR.exists(), "jobs dir missing"
    expected_jobs = {
        "20261018-223750-3aecfbcd": ("channel-1e24de3ab5", "hybrid"),
        "20261017-164519-fd65f7e1": ("channel-e544a64b7c", "full_ai"),
        "20261017-003022-ecb75736": ("channel-e544a64b7c", "full_ai"),
        "20261015-014818-f0fdc122": ("channel-1e24de3ab5", "hybrid"),
    }

    for jid, (exp_pid, exp_strat) in expected_jobs.items():
        jfile = JOBS_DIR / jid / "job.json"
        assert jfile.exists(), f"Job file missing: {jfile}"
        job = json.loads(jfile.read_text(encoding="utf-8"))

        assert job.get("channel_profile_id") == exp_pid, f"Job {jid} expected profile {exp_pid}, got {job.get('channel_profile_id')}"
        assert job.get("visual_strategy") == exp_strat, f"Job {jid} expected visual_strategy {exp_strat}, got {job.get('visual_strategy')}"
        assert isinstance(job.get("default_creative_brief"), dict) and len(job["default_creative_brief"]) >= 10
        assert isinstance(job.get("editing_dna"), dict) and len(job["editing_dna"]) >= 6
        assert isinstance(job.get("channel_profile_snapshot"), dict) and len(job["channel_profile_snapshot"]) >= 5

        # Check phases
        phases = job.get("phases") or {}
        assert len(phases) == 8, f"Job {jid} expected 8 phases, found {len(phases)}"

    log(f"All {len(expected_jobs)} jobs verified with correct profile bindings and preserved phases.")


def check_empirical_persistence_and_crud():
    log("Testing empirical persistence & CRUD via ChannelProfileService...")
    from services.channel_profile_service import ChannelProfileService

    service = ChannelProfileService()
    test_tag = f"audit-{uuid4().hex[:8]}"

    # Step 1: Create
    payload = {
        "label": f"Forensic Audit Test Profile {test_tag}",
        "market": "KR",
        "default_language": "ko",
        "default_duration_minutes": 22,
        "default_visual_strategy": "hybrid",
        "allowed_topics": "Empirical persistence verification",
        "voice_and_structure": "Forensic test voice",
    }
    created = service.create_profile(payload)
    created_id = created["id"]
    log(f"Created profile {created_id}")

    # Verify directly from raw disk read
    raw_disk = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    disk_match = next((p for p in raw_disk.get("profiles", []) if p.get("id") == created_id), None)
    assert disk_match is not None, f"Created profile {created_id} not found in raw disk file!"
    assert disk_match["label"] == payload["label"], "Disk label mismatch"
    assert disk_match["channel_profile_id"] == created_id, "Disk channel_profile_id mismatch"
    assert disk_match["default_creative_brief"]["market"] == "KR"
    assert disk_match["editing_dna"]["pacing"] == 5.0
    log("Direct disk read confirmed authentic persistence.")

    # Step 2: In-place Update preserving unmentioned fields
    update_patch = {
        "notes": f"Updated notes {test_tag}",
        "editing_dna": {"pacing": 7.5}
    }
    updated = service.update_profile(created_id, update_patch)
    assert updated["editing_dna"]["pacing"] == 7.5
    # Verify color_grade preserved
    assert updated["editing_dna"]["color_grade"] == "technical_cool_cyan"

    # Verify disk
    raw_disk = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    disk_match = next((p for p in raw_disk.get("profiles", []) if p.get("id") == created_id), None)
    assert disk_match["editing_dna"]["pacing"] == 7.5, "Disk pacing not updated"
    assert disk_match["editing_dna"]["color_grade"] == "technical_cool_cyan", "Disk color_grade corrupted"
    log("In-place field-preserving update verified on disk.")

    # Step 3: Clone
    cloned = service.clone_profile(created_id)
    cloned_id = cloned["id"]
    assert cloned_id != created_id, "Cloned ID identical to original!"
    assert cloned["label"].endswith("(Clone)"), "Clone label missing suffix"
    assert cloned["editing_dna"]["pacing"] == 7.5, "Clone failed to copy updated pacing"

    # Verify disk has clone
    raw_disk = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    disk_clone = next((p for p in raw_disk.get("profiles", []) if p.get("id") == cloned_id), None)
    assert disk_clone is not None, "Cloned profile not found on disk"
    log("Profile cloning verified on disk.")

    # Step 4: Delete both test profiles
    service.delete_profile(created_id)
    service.delete_profile(cloned_id)

    # Verify removal from disk
    raw_disk = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    remaining_ids = [p["id"] for p in raw_disk.get("profiles", [])]
    assert created_id not in remaining_ids, "Deleted profile still on disk"
    assert cloned_id not in remaining_ids, "Deleted clone still on disk"
    log("Deletions cleanly verified on disk.")


def check_job_mutation_isolation():
    log("Testing strict job mutation isolation via JobService...")
    from services.job_service import JobService

    job_service = JobService()
    target_id = "20261018-223750-3aecfbcd"
    other_id = "20261017-164519-fd65f7e1"

    # Attack 1: Cross-job mutation attempt
    try:
        job_service.update_job(target_id, {"job_id": other_id, "notes": "malicious cross-job mutation"})
        raise AssertionError("Cross-job mutation was NOT rejected!")
    except ValueError as exc:
        assert "Cross-job mutation rejected" in str(exc)
        log("Cross-job mutation successfully blocked with ValueError.")

    # Attack 2: Draft mutation side-effects attempt
    try:
        job_service.update_job(target_id, {"is_draft": True, "notes": "draft mutation bleed"})
        raise AssertionError("Draft mutation was NOT rejected!")
    except ValueError as exc:
        assert "Draft mutation side-effects rejected" in str(exc)
        log("Draft mutation side-effects successfully blocked with ValueError.")

    # Attack 3: Non-existent job
    try:
        job_service.update_job("non-existent-job-id-xyz", {"notes": "test"})
        raise AssertionError("Non-existent job update was NOT rejected!")
    except KeyError as exc:
        assert "not found" in str(exc).lower()
        log("Non-existent job update successfully blocked with KeyError.")

    # Test legitimate isolated update and revert
    orig_target = job_service.get_job(target_id)
    orig_other = job_service.get_job(other_id)

    test_note = f"Auditor note {uuid4().hex[:6]}"
    job_service.update_job(target_id, {"notes": test_note})

    # Read from disk directly
    target_file = JOBS_DIR / target_id / "job.json"
    other_file = JOBS_DIR / other_id / "job.json"

    disk_target = json.loads(target_file.read_text(encoding="utf-8"))
    disk_other = json.loads(other_file.read_text(encoding="utf-8"))

    assert disk_target["notes"] == test_note, "Target job not updated on disk"
    assert disk_other["notes"] == orig_other.get("notes"), "Other job was mutated!"
    log("Designated job updated cleanly on disk with ZERO bleed into other jobs.")

    # Revert target job
    job_service.update_job(target_id, {"notes": orig_target.get("notes") or ""})
    reverted_target = json.loads(target_file.read_text(encoding="utf-8"))
    assert reverted_target["notes"] == (orig_target.get("notes") or ""), "Revert failed"
    log("Target job reverted cleanly.")


def check_fastapi_server_routes():
    log("Checking FastAPI server route declarations and responses...")
    from server import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    routes = [r.path for r in app.router.routes]
    log(f"FastAPI app has {len(routes)} routes.")

    required_routes = [
        "/api/radar/channel-profiles",
        "/api/radar/channel-profiles/{profile_id}",
        "/api/radar/channel-profiles/{profile_id}/clone",
        "/api/jobs/{job_id}",
    ]
    for rr in required_routes:
        assert rr in routes, f"Missing route {rr} in server.py"

    client = TestClient(app)
    # Test GET /api/radar/channel-profiles
    resp = client.get("/api/radar/channel-profiles")
    assert resp.status_code == 200, f"GET channel-profiles failed: {resp.status_code}"
    profiles = resp.json()
    assert len(profiles) >= 4, f"Expected at least 4 profiles, got {len(profiles)}"

    # Test GET single profile
    resp2 = client.get("/api/radar/channel-profiles/channel-1e24de3ab5")
    assert resp2.status_code == 200
    p = resp2.json()
    assert p["id"] == "channel-1e24de3ab5"
    assert p["visual_strategy"] == "hybrid"

    # Test 404
    resp404 = client.get("/api/radar/channel-profiles/channel-non-existent-audit")
    assert resp404.status_code == 404

    log("FastAPI server routes verified successfully.")


def run_all():
    log("============================================================")
    log("STARTING INDEPENDENT FORENSIC AUDIT OF MILESTONE 1")
    log("============================================================")
    check_radar_db()
    check_backups()
    check_channel_profiles_storage_and_backfill()
    check_jobs_storage_and_backfill()
    check_empirical_persistence_and_crud()
    check_job_mutation_isolation()
    check_fastapi_server_routes()
    log("============================================================")
    log("ALL INDEPENDENT FORENSIC AUDIT CHECKS PASSED: VERDICT = CLEAN")
    log("============================================================")


if __name__ == "__main__":
    run_all()
