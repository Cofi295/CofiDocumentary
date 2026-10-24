"""
Adversarial Stress and Isolation Test Suite for Backend Implementation.
Empirically tests:
1. Modifying non-existent Job IDs (HTTP 404, KeyError, path traversal, injection).
2. Cross-job mutation prevention (ID spoofing, payload ID conflicts, cross-contamination, draft side-effects).
3. Concurrency stress (Race conditions, thread-safety in JobStore and ChannelProfileService).
4. Malformed and incomplete payloads (Non-dict payloads, type confusion, schema degradation).
"""

from __future__ import annotations

import concurrent.futures
import copy
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from documentary.store import JobStore
from server import create_app
from services.channel_profile_service import ChannelProfileService
from services.job_service import JobService


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def app_client():
    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def isolated_env(tmp_path: Path):
    """Creates a temporary isolated filesystem for jobs and channel profiles."""
    test_jobs_dir = tmp_path / "jobs"
    test_jobs_dir.mkdir(parents=True, exist_ok=True)
    test_profiles_file = tmp_path / "channel_profiles.json"

    # Seed with initial profile
    initial_profiles = {
        "profiles": [
            {
                "id": "channel-test-1",
                "channel_profile_id": "channel-test-1",
                "label": "Test Channel Alpha",
                "market": "KR",
                "language": "ko",
                "default_language": "ko",
                "default_duration_minutes": 30,
                "target_duration_minutes": 30,
                "visual_strategy": "hybrid",
                "default_visual_strategy": "hybrid",
                "default_ai_media_mode": "image",
                "ai_media_mode": "image",
                "default_creative_brief": {
                    "market": "KR",
                    "language": "ko",
                    "target_duration_minutes": 30,
                    "ai_media_mode": "image",
                    "visual_strategy": "hybrid",
                    "narrative_angle": "Alpha Angle",
                    "writing_style": "Alpha Style",
                    "hook_archetype": "Alpha Hook",
                    "editing_archetypes": ["2.5D maps"],
                    "opening_hook": "Alpha Opening Hook",
                    "notes": "Alpha Notes",
                    "custom_rules": "Alpha Rules",
                },
                "editing_dna": {
                    "version": 1,
                    "pacing": 5.0,
                    "typical_pacing_sec": 5.0,
                    "visual_mix": {"footage": 0.5, "ai": 0.35, "motion": 0.15},
                    "editing_archetypes": ["2.5d_satellite_terrain_flyover"],
                    "subtitle_style": {
                        "font_family": "Pretendard",
                        "color": "#ffffff",
                        "highlight_color": "#38bdf8",
                        "font_size": 42,
                    },
                    "color_grade": "technical_cool_cyan",
                    "audio_rules": {
                        "music_ducking_db": -18.0,
                        "sfx_hit_on_chapter": True,
                        "tension_drone_under_interrogation": False,
                    },
                },
                "self_learning_memory": {
                    "analyzed_videos_count": 5,
                    "winners": ["v1"],
                    "underperformers": ["v2"],
                    "winner_patterns": ["Pattern A"],
                    "losing_patterns": ["Pattern B"],
                    "upgrade_rules": {
                        "what_to_stop_doing": ["stop A"],
                        "what_to_double_down_on": ["double A"],
                        "next_video_upgrades": ["upgrade A"],
                    },
                    "next_video_upgrades": ["upgrade A"],
                },
                "editing_dna_history": [],
            },
            {
                "id": "channel-test-2",
                "channel_profile_id": "channel-test-2",
                "label": "Test Channel Beta",
                "market": "US",
                "language": "en",
                "default_language": "en",
                "default_duration_minutes": 15,
                "target_duration_minutes": 15,
                "visual_strategy": "full_ai",
                "default_visual_strategy": "full_ai",
                "default_ai_media_mode": "mixed",
                "ai_media_mode": "mixed",
                "default_creative_brief": {
                    "market": "US",
                    "language": "en",
                    "target_duration_minutes": 15,
                    "ai_media_mode": "mixed",
                    "visual_strategy": "full_ai",
                    "narrative_angle": "Beta Angle",
                    "writing_style": "Beta Style",
                    "hook_archetype": "Beta Hook",
                    "editing_archetypes": ["document telemetry"],
                    "opening_hook": "Beta Opening Hook",
                    "notes": "Beta Notes",
                    "custom_rules": "Beta Rules",
                },
                "editing_dna": {
                    "version": 1,
                    "pacing": 4.0,
                    "typical_pacing_sec": 4.0,
                    "visual_mix": {"footage": 0.2, "ai": 0.7, "motion": 0.1},
                    "editing_archetypes": ["technical_hud_telemetry_gauge"],
                    "subtitle_style": {
                        "font_family": "Arial",
                        "color": "#ffff00",
                        "highlight_color": "#ff0000",
                        "font_size": 36,
                    },
                    "color_grade": "archival_warm",
                    "audio_rules": {
                        "music_ducking_db": -12.0,
                        "sfx_hit_on_chapter": False,
                        "tension_drone_under_interrogation": True,
                    },
                },
                "self_learning_memory": {
                    "analyzed_videos_count": 2,
                    "winners": ["vB1"],
                    "underperformers": [],
                    "winner_patterns": ["Pattern Beta"],
                    "losing_patterns": [],
                    "upgrade_rules": {
                        "what_to_stop_doing": [],
                        "what_to_double_down_on": ["double Beta"],
                        "next_video_upgrades": [],
                    },
                    "next_video_upgrades": [],
                },
                "editing_dna_history": [],
            },
        ]
    }
    test_profiles_file.write_text(json.dumps(initial_profiles, indent=2), encoding="utf-8")

    job_store = JobStore(test_jobs_dir)
    profile_service = ChannelProfileService(storage_path=test_profiles_file)
    job_service = JobService(store=job_store, profile_service=profile_service)

    return {
        "tmp_path": tmp_path,
        "jobs_dir": test_jobs_dir,
        "profiles_file": test_profiles_file,
        "job_store": job_store,
        "profile_service": profile_service,
        "job_service": job_service,
    }


# ==============================================================================
# SECTION 1: NON-EXISTENT JOB ID MODIFICATIONS
# ==============================================================================

def test_adv_modify_non_existent_job_id_raises_key_error(isolated_env):
    """JobService.update_job directly with non-existent IDs raises KeyError without creating files."""
    job_service: JobService = isolated_env["job_service"]
    jobs_dir: Path = isolated_env["jobs_dir"]

    with pytest.raises(KeyError, match="Job non-existent-id-999 not found"):
        job_service.update_job("non-existent-id-999", {"notes": "test"})

    # Verify no phantom folder/file was created
    assert not (jobs_dir / "non-existent-id-999").exists()


def test_adv_modify_non_existent_job_via_api(app_client):
    """PATCH /api/jobs/{job_id} on non-existent IDs returns 404."""
    resp = app_client.patch("/api/jobs/job-completely-bogus-404", json={"notes": "hack"})
    assert resp.status_code == 404
    assert "Không tìm thấy dự án" in resp.json()["detail"]


@pytest.mark.parametrize("malicious_id", [
    "../../etc/passwd",
    "..\\..\\data\\channel_profiles.json",
    "../another_folder",
    "job-id-with-special!@#$%^&*()",
    "   job-id-with-spaces   ",
])
def test_adv_modify_path_traversal_and_special_job_ids(isolated_env, malicious_id):
    """Attempt path traversal or injection via job_id."""
    job_service: JobService = isolated_env["job_service"]

    with pytest.raises(KeyError):
        job_service.update_job(malicious_id, {"notes": "pwned"})

    # Ensure no file was created outside jobs_dir
    assert not (isolated_env["tmp_path"] / "etc" / "passwd").exists()
    assert not (isolated_env["tmp_path"] / "another_folder").exists()


# ==============================================================================
# SECTION 2: CROSS-JOB MUTATION ATTEMPTS
# ==============================================================================

def test_adv_cross_job_mutation_prevention(isolated_env):
    """
    Attempt to mutate Job Beta while sending update request targeted at Job Alpha.
    Must be strictly rejected, and Job Beta must remain entirely untouched.
    """
    job_service: JobService = isolated_env["job_service"]

    # Create Job Alpha and Job Beta
    job_a = job_service.create_job({
        "title": "Documentary Project Alpha",
        "notes": "Alpha Original Notes",
        "channel_profile_id": "channel-test-1",
    })
    job_b = job_service.create_job({
        "title": "Documentary Project Beta",
        "notes": "Beta Original Notes",
        "channel_profile_id": "channel-test-2",
    })

    id_a = job_a["id"]
    id_b = job_b["id"]

    # 1. Pretend to update Job A, but payload specifies job_id=id_b
    with pytest.raises(ValueError, match="Cross-job mutation rejected"):
        job_service.update_job(id_a, {
            "job_id": id_b,
            "title": "Hacked Title on Beta",
            "notes": "Maliciously attempting to overwrite Beta",
        })

    # Verify Job A and Job B are completely unchanged
    fresh_a = job_service.get_job(id_a)
    fresh_b = job_service.get_job(id_b)
    assert fresh_a["title"] == "Documentary Project Alpha"
    assert fresh_a["notes"] == "Alpha Original Notes"
    assert fresh_b["title"] == "Documentary Project Beta"
    assert fresh_b["notes"] == "Beta Original Notes"

    # 2. Pretend to update Job A, but payload specifies id=id_b
    with pytest.raises(ValueError, match="Cross-job mutation rejected"):
        job_service.update_job(id_a, {
            "id": id_b,
            "notes": "Malicious overwrite via 'id'",
        })

    # 3. Pretend to update Job A, but payload specifies selectedId=id_b
    with pytest.raises(ValueError, match="Cross-job mutation rejected"):
        job_service.update_job(id_a, {
            "selectedId": id_b,
            "notes": "Malicious overwrite via 'selectedId'",
        })

    # 4. Attempt draft mutation side-effects on Job A
    with pytest.raises(ValueError, match="Draft mutation side-effects rejected"):
        job_service.update_job(id_a, {
            "is_draft": True,
            "title": "Draft Title Override",
        })

    with pytest.raises(ValueError, match="Draft mutation side-effects rejected"):
        job_service.update_job(id_a, {
            "draft_mutation": True,
            "title": "Draft Mutation Override",
        })

    # Verify Job A remains untouched
    fresh_a2 = job_service.get_job(id_a)
    assert fresh_a2["title"] == "Documentary Project Alpha"


def test_adv_cross_job_mutation_via_api(app_client):
    """Test cross-job mutation rejection and non-contamination through FastAPI endpoint."""
    jobs_resp = app_client.get("/api/jobs")
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    assert len(jobs) >= 2

    job1_id = jobs[0]["id"]
    job2_id = jobs[1]["id"]
    job2_orig_notes = jobs[1].get("notes")

    # Send cross-job attack
    attack_payload = {
        "job_id": job2_id,
        "notes": "ATTACKER_OVERWRITE_NOTES",
    }
    resp = app_client.patch(f"/api/jobs/{job1_id}", json=attack_payload)
    assert resp.status_code == 400
    assert "Cross-job mutation rejected" in resp.json()["detail"]

    # Verify job 2 notes were not altered
    job2_after = app_client.get(f"/api/jobs/{job2_id}").json()
    assert job2_after.get("notes") == job2_orig_notes


# ==============================================================================
# SECTION 3: CONCURRENCY STRESS (RACE CONDITIONS & THREAD-SAFETY)
# ==============================================================================

def test_adv_concurrent_job_updates_same_job(isolated_env):
    """
    Stress-test high concurrency on the SAME job:
    Spawn 25 parallel threads updating distinct fields of the same Job.
    Verify that JobStore RLock and atomic replace guarantee consistency without corruption.
    """
    job_service: JobService = isolated_env["job_service"]
    created_job = job_service.create_job({
        "title": "Concurrent Stress Job",
        "channel_profile_id": "channel-test-1",
    })
    job_id = created_job["id"]

    num_threads = 25

    def worker_update(idx: int):
        try:
            patch = {
                f"worker_field_{idx}": f"worker_val_{idx}",
                "latest_worker": idx,
            }
            job_service.update_job(job_id, patch)
            return True
        except Exception as e:
            return e

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_update, i) for i in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    for r in results:
        assert r is True, f"Worker failed with exception: {r}"

    # Read back job and verify file integrity
    final_job = job_service.get_job(job_id)
    assert final_job["title"] == "Concurrent Stress Job"
    for i in range(num_threads):
        assert final_job.get(f"worker_field_{i}") == f"worker_val_{i}"


def test_adv_concurrent_job_updates_distinct_jobs_zero_bleed(isolated_env):
    """
    Stress-test concurrency across 10 distinct jobs being updated simultaneously:
    Verify zero bleed between jobs (no cross-contamination of worker data).
    """
    job_service: JobService = isolated_env["job_service"]
    jobs = []
    for i in range(10):
        j = job_service.create_job({
            "title": f"Distinct Job {i}",
            "channel_profile_id": "channel-test-1",
        })
        jobs.append(j)

    def worker_distinct(job_info):
        idx, jid = job_info
        for k in range(5):
            job_service.update_job(jid, {
                f"private_key_job_{idx}_{k}": f"secret_{idx}_{k}"
            })

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker_distinct, (i, jobs[i]["id"])) for i in range(10)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    # Verify zero bleed
    for i in range(10):
        jid = jobs[i]["id"]
        job_data = job_service.get_job(jid)
        for k in range(5):
            assert job_data.get(f"private_key_job_{i}_{k}") == f"secret_{i}_{k}"
        for other in range(10):
            if other == i:
                continue
            for k in range(5):
                assert f"private_key_job_{other}_{k}" not in job_data


def test_adv_concurrent_channel_profile_updates_and_clones(isolated_env):
    """
    Stress-test concurrent updates to Channel Profiles stored in single JSON file.
    Tests atomic tempfile replacement and RLock synchronization under load.
    """
    profile_service: ChannelProfileService = isolated_env["profile_service"]
    profiles_file: Path = isolated_env["profiles_file"]

    num_workers = 20

    def profile_worker(idx: int):
        try:
            target_id = "channel-test-1" if idx % 2 == 0 else "channel-test-2"
            profile_service.update_profile(target_id, {
                f"worker_prop_{idx}": f"value_{idx}",
            })
            p = profile_service.get_profile(target_id)
            assert p[f"worker_prop_{idx}"] == f"value_{idx}"
            return True
        except Exception as e:
            return e

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(profile_worker, i) for i in range(num_workers)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    for r in results:
        assert r is True, f"Profile worker failed: {r}"

    # Verify profiles file is valid JSON and partitioned accurately
    raw = json.loads(profiles_file.read_text(encoding="utf-8"))
    assert "profiles" in raw
    p1 = profile_service.get_profile("channel-test-1")
    p2 = profile_service.get_profile("channel-test-2")
    for i in range(num_workers):
        if i % 2 == 0:
            assert p1.get(f"worker_prop_{i}") == f"value_{i}"
            assert f"worker_prop_{i}" not in p2
        else:
            assert p2.get(f"worker_prop_{i}") == f"value_{i}"
            assert f"worker_prop_{i}" not in p1


# ==============================================================================
# SECTION 4: INCOMPLETE OR MALFORMED PAYLOADS & STRESS VULNERABILITIES
# ==============================================================================

def test_adv_malformed_non_dict_payload_returns_400_not_500(app_client):
    """
    [VULNERABILITY PROBE 1]:
    Sending a non-dict payload (e.g. list, string) to PATCH /api/jobs/{id}.
    Expectation: API should return HTTP 400 Bad Request.
    Vulnerability: server.py raises HTTPException(400) inside try block, which is caught
    by except Exception as exc and re-raised as HTTPException(500), returning HTTP 500!
    """
    resp = app_client.patch("/api/jobs/20261018-223750-3aecfbcd", json=["invalid", "array"])
    # If the bug exists, this will return 500 instead of 400
    assert resp.status_code == 400, (
        f"Expected 400 Bad Request for non-dict payload, but got {resp.status_code} "
        f"with detail: {resp.json().get('detail')}"
    )


def test_adv_malformed_phases_payload_isolation_break(isolated_env):
    """
    [VULNERABILITY PROBE 2]:
    Sending a malformed non-dict 'phases' payload (e.g. phases='corrupted') to update_job.
    Expectation: JobService should reject non-dict phases payload or JobStore._normalize_job
    should handle it gracefully without crashing list_jobs().
    Vulnerability: JobStore.update writes 'corrupted' to job.json. Next call to
    JobStore.get or JobStore.list crashes with unhandled ValueError:
    'dictionary update sequence element #0 has length 1; 2 is required',
    bringing down the entire /api/jobs listing for ALL users and ALL jobs!
    """
    job_service: JobService = isolated_env["job_service"]
    j1 = job_service.create_job({"title": "Victim Job", "channel_profile_id": "channel-test-1"})
    j2 = job_service.create_job({"title": "Innocent Bystander Job", "channel_profile_id": "channel-test-2"})

    # Attempt malformed phases update
    try:
        job_service.update_job(j1["id"], {"phases": "corrupted_string"})
    except ValueError:
        # If rejected gracefully, test passes
        return

    # If it was accepted, verify if list_jobs() survives or crashes
    try:
        all_jobs = job_service.list_jobs()
        assert len(all_jobs) >= 2
    except ValueError as exc:
        pytest.fail(
            f"CRITICAL ISOLATION BREACH: Malformed update to Job {j1['id']} broke list_jobs() "
            f"for all jobs! Exception: {exc}"
        )


def test_adv_malformed_nested_profile_structures_corrupts_storage(isolated_env):
    """
    [VULNERABILITY PROBE 3]:
    Sending non-dict structures to update_profile (e.g. default_creative_brief='corrupted').
    Expectation: Service should reject or ignore non-dict values for dict fields.
    Vulnerability: ChannelProfileService.update_profile falls through to 'updated[key] = value',
    storing string instead of dict and corrupting the profile schema in channel_profiles.json.
    """
    profile_service: ChannelProfileService = isolated_env["profile_service"]
    job_service: JobService = isolated_env["job_service"]

    # Update with non-dict editing_dna - must be rejected with ValueError
    try:
        profile_service.update_profile("channel-test-1", {
            "editing_dna": "not_a_valid_dict"
        })
    except ValueError:
        pass

    updated_profile = profile_service.get_profile("channel-test-1")
    # Verify whether editing_dna was corrupted to string
    assert isinstance(updated_profile.get("editing_dna"), dict), (
        f"CRITICAL SCHEMA DEGRADATION: editing_dna in channel-test-1 was overwritten with "
        f"{type(updated_profile.get('editing_dna'))}: {updated_profile.get('editing_dna')}"
    )


def test_adv_empty_and_minimal_payloads(isolated_env):
    """Empty payload {} to update_job and update_profile must not corrupt or wipe data."""
    job_service: JobService = isolated_env["job_service"]
    profile_service: ChannelProfileService = isolated_env["profile_service"]

    # 1. Empty patch to Job
    job = job_service.create_job({"title": "Original Title", "channel_profile_id": "channel-test-1"})
    jid = job["id"]
    updated_job = job_service.update_job(jid, {})
    assert updated_job["title"] == "Original Title"
    assert updated_job["channel_profile_id"] == "channel-test-1"

    # 2. Empty patch to Profile
    p_orig = profile_service.get_profile("channel-test-1")
    updated_profile = profile_service.update_profile("channel-test-1", {})
    assert updated_profile["label"] == p_orig["label"]
    assert updated_profile["editing_dna"] == p_orig["editing_dna"]
    assert updated_profile["default_creative_brief"] == p_orig["default_creative_brief"]


def test_adv_type_confusion_in_profile_creation(isolated_env):
    """
    Channel profile creation with unexpected types (e.g. non-numeric durations,
    invalid visual strategies, bad media modes).
    Service must sanitize and fall back to safe schema defaults.
    """
    profile_service: ChannelProfileService = isolated_env["profile_service"]

    weird_payload = {
        "label": "Weird Types Profile",
        "market": "ZZ_UNKNOWN",
        "default_duration_minutes": "not-a-number",
        "visual_strategy": "EXTREMELY_INVALID_STRATEGY",
        "ai_media_mode": "hologram_4d",
    }
    created = profile_service.create_profile(weird_payload)

    assert created["default_duration_minutes"] == 30
    assert created["visual_strategy"] == "hybrid"
    assert created["ai_media_mode"] == "image"
    assert isinstance(created["default_creative_brief"], dict)
    assert isinstance(created["editing_dna"], dict)
    assert isinstance(created["self_learning_memory"], dict)


def test_adv_job_creation_with_non_existent_channel_profile(isolated_env):
    """
    Creating a Job pointing to a non-existent channel profile ID must be validated
    and rejected with ValueError or HTTPException instead of silently creating an unlinked project.
    """
    job_service: JobService = isolated_env["job_service"]
    with pytest.raises((ValueError, HTTPException)):
        job_service.create_job({
            "title": "Orphan Project",
            "channel_profile_id": "channel-ghost-99999",
        })
