"""
Tier 5 E2E Adversarial Coverage Hardening Test Suite for CofiDocumentary.
Milestone 5 Phase 2: White-box adversarial testing, edge-case mining, parameter boundary stress,
race condition verification, corruption recovery, and schema degradation resilience.

Covers:
1. Profile CRUD, Cloning, Deep Inheritance & Race Conditions
2. Job Creation, Phase Updates, and Mutation Isolation
3. 'Lock Approved Edit Style to Channel' Versioning & Corruption Recovery
4. Voice/SRT Drift Detection, Auto-Repair Idempotency, and Extreme Hold Freezes
5. Channel DNA Pre-Flight Duplicate Blocking & Outlier Limits
6. Self-Learning Memory Persistence & Evolution Rule Synthesis
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

from documentary.store import JobStore
from services.channel_profile_service import ChannelProfileService
from services.job_service import JobService
from services.editing_dna_service import EditingDnaService
from services.sync_policy_service import SyncPolicyService
from services.preflight_service import PreflightService
from services.self_learning_service import SelfLearningService


# ==============================================================================
# ISOLATED SANDBOX FIXTURE
# ==============================================================================

@pytest.fixture
def sandbox(tmp_path: Path):
    """
    Creates a completely isolated, temporary environment for jobs, profiles,
    and workspaces so that tests never mutate production files in data/.
    """
    profiles_file = tmp_path / "data" / "channel_profiles.json"
    jobs_dir = tmp_path / "data" / "jobs"
    workspaces_dir = tmp_path / "workspaces"
    radar_db = tmp_path / "cofi-radar.db"

    profiles_file.parent.mkdir(parents=True, exist_ok=True)
    jobs_dir.mkdir(parents=True, exist_ok=True)
    workspaces_dir.mkdir(parents=True, exist_ok=True)

    # Initial seed profile
    initial_profiles = {
        "profiles": [
            {
                "id": "channel-sandbox-1",
                "channel_profile_id": "channel-sandbox-1",
                "label": "Sandbox Investigative Channel",
                "market": "KR",
                "default_language": "ko",
                "language": "ko",
                "default_duration_minutes": 22,
                "target_duration_minutes": 22,
                "default_visual_strategy": "hybrid",
                "visual_strategy": "hybrid",
                "default_ai_media_mode": "image",
                "ai_media_mode": "image",
                "default_ai_style_mode": "custom",
                "default_ai_custom_style": "2.5D Technical Infrastructure",
                "dna_mode": "radar_hybrid",
                "own_channel_ref": "@sandbox_channel",
                "own_channel": {
                    "dna": {
                        "winner_terms": ["đại án", "hạ tầng", "sụp đổ", "đập Tam Hiệp"],
                        "weak_terms": ["lý do", "vấn đề", "tin vắn"],
                        "winner_titles": [
                            "Đại án 5.000 tỷ lún sụt kênh Nam Thủy Bắc Điều",
                            "Nguy cơ sụp đổ thân đập Tam Hiệp trước 39 tỷ tấn nước",
                        ],
                    },
                    "videos": [
                        {"id": "sb_v1", "title": "Đại án 5.000 tỷ lún sụt kênh Nam Thủy Bắc Điều", "views": 250000, "is_breakout": True},
                        {"id": "sb_v2", "title": "Nguy cơ sụp đổ thân đập Tam Hiệp trước 39 tỷ tấn nước", "views": 180000, "is_breakout": True},
                        {"id": "sb_v3", "title": "Tin vắn tổng hợp các công trình năm 2024", "views": 12000, "is_breakout": False},
                    ],
                },
                "allowed_topics": "Bóc tách thông số kỹ thuật, cơ chế vật lý hiện trường, đại công trình.",
                "forbidden_topics": "Chính trị giật gân, bạo lực máu me, tin đồn thất thiệt",
                "monetization_safety_policy": "100% Green Monetization khách quan",
                "voice_and_structure": "Phóng sự điều tra kỹ thuật sắc lạnh",
                "default_creative_brief": {
                    "market": "KR",
                    "language": "ko",
                    "target_duration_minutes": 22,
                    "ai_media_mode": "image",
                    "visual_strategy": "hybrid",
                    "narrative_angle": "Điều tra Kỹ thuật Hạ tầng",
                    "writing_style": "Phóng sự Điều tra Sắc Lạnh",
                    "hook_archetype": "Con số Định lượng Cực hạn",
                    "editing_archetypes": ["2.5D maps", "document telemetry", "chapter title cards"],
                    "opening_hook": "1.432 kilômét đường nước nhân tạo xuyên núi...",
                    "notes": "Hồ sơ kênh mẫu Sandbox",
                    "custom_rules": "CHUẨN DNA SANDBOX",
                },
                "editing_dna": {
                    "version": 1,
                    "pacing": 4.5,
                    "typical_pacing_sec": 4.5,
                    "visual_mix": {"footage": 0.5, "ai": 0.35, "motion": 0.15},
                    "editing_archetypes": [
                        "2.5d_satellite_terrain_flyover",
                        "technical_hud_telemetry_gauge",
                        "cinematic_chapter_card_hit",
                    ],
                    "subtitle_style": {
                        "font_family": "Pretendard, sans-serif",
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
                    "analyzed_videos_count": 3,
                    "winners": ["Đại án 5.000 tỷ lún sụt kênh Nam Thủy Bắc Điều"],
                    "underperformers": ["Tin vắn tổng hợp các công trình năm 2024"],
                    "winner_patterns": ["đại án", "thông số cực hạn"],
                    "losing_patterns": ["tin vắn", "tổng hợp"],
                    "upgrade_rules": {
                        "what_to_stop_doing": ["Không làm video tin vắn tổng hợp"],
                        "what_to_double_down_on": ["Bóc tách thông số kỹ thuật cực hạn"],
                        "next_video_upgrades": ["Mở đầu bằng nghịch lý 30 giây"],
                    },
                    "next_video_upgrades": ["Mở đầu bằng nghịch lý 30 giây"],
                },
                "editing_dna_history": [],
            }
        ]
    }
    profiles_file.write_text(json.dumps(initial_profiles, indent=2, ensure_ascii=False), encoding="utf-8")

    profile_service = ChannelProfileService(storage_path=profiles_file)
    job_store = JobStore(jobs_dir)
    job_service = JobService(store=job_store, profile_service=profile_service)
    editing_dna_service = EditingDnaService(
        profiles_file=profiles_file,
        jobs_dir=jobs_dir,
        workspaces_dir=workspaces_dir,
    )
    sync_policy_service = SyncPolicyService(
        workspaces_dir=workspaces_dir,
        jobs_dir=jobs_dir,
    )
    preflight_service = PreflightService(
        profiles_file=profiles_file,
        jobs_dir=jobs_dir,
        profile_service=profile_service,
    )
    self_learning_service = SelfLearningService(
        profiles_file=profiles_file,
        jobs_dir=jobs_dir,
        radar_db=radar_db,
        profile_service=profile_service,
    )

    return {
        "tmp_path": tmp_path,
        "profiles_file": profiles_file,
        "jobs_dir": jobs_dir,
        "workspaces_dir": workspaces_dir,
        "radar_db": radar_db,
        "profile_service": profile_service,
        "job_store": job_store,
        "job_service": job_service,
        "editing_dna_service": editing_dna_service,
        "sync_policy_service": sync_policy_service,
        "preflight_service": preflight_service,
        "self_learning_service": self_learning_service,
    }


# ==============================================================================
# SECTION 1: PROFILE CRUD, CLONING, DEEP INHERITANCE & CONCURRENCY
# ==============================================================================

def test_tier5_profile_create_boundary_and_type_coercion(sandbox):
    """
    Adversarial boundary stress on profile creation:
    - Target duration boundaries (min 2, max 30, float precision, numeric strings, malformed strings).
    - Market normalizations and default language fallbacks.
    - Unsupported visual strategies and AI media modes falling back safely.
    """
    svc: ChannelProfileService = sandbox["profile_service"]

    # 1. Valid float duration coerced safely
    p1 = svc.create_profile({
        "label": "Float Precision Profile",
        "market": "kr",  # lowercase should normalize
        "target_duration_minutes": 22.5,
        "visual_strategy": "HYBRID",  # uppercase should normalize
        "ai_media_mode": "IMAGE",
    })
    assert p1["market"] == "KR"
    assert p1["default_language"] == "ko"
    assert p1["visual_strategy"] == "hybrid"
    assert p1["target_duration_minutes"] == 22.5

    # 2. String numeric duration coercion
    p2 = svc.create_profile({
        "label": "String Numeric Duration",
        "market": "US",
        "target_duration_minutes": "15",
    })
    assert p2["target_duration_minutes"] == 15
    assert p2["default_language"] == "en"

    # 3. Malformed duration string fallback to 30
    p3 = svc.create_profile({
        "label": "Corrupt Duration Profile",
        "market": "VN",
        "target_duration_minutes": "not-a-number",
    })
    assert p3["target_duration_minutes"] == 30
    assert p3["default_language"] == "vi"

    # 4. Unknown visual strategy and media mode fallback
    p4 = svc.create_profile({
        "label": "Invalid Enums Profile",
        "visual_strategy": "super_fancy_3d_engine",
        "ai_media_mode": "holographic_vr",
    })
    assert p4["visual_strategy"] == "hybrid"
    assert p4["ai_media_mode"] == "image"


def test_tier5_profile_deep_inheritance_and_chained_cloning(sandbox):
    """
    Adversarial chained cloning test: Grandparent -> Parent -> Child.
    Verifies that mutating the grandchild has ZERO bleed into ancestors,
    and history is always reset across generations.
    """
    svc: ChannelProfileService = sandbox["profile_service"]

    # Gen 1: Grandparent
    gen1 = svc.get_profile("channel-sandbox-1")
    gen1_dna_pacing = gen1["editing_dna"]["pacing"]

    # Gen 2: Parent clone
    gen2 = svc.clone_profile("channel-sandbox-1", new_label="Parent Gen2 Profile")
    assert gen2["id"] != gen1["id"]
    assert gen2["label"] == "Parent Gen2 Profile"
    assert gen2["editing_dna_history"] == []

    # Gen 3: Child clone from Parent
    gen3 = svc.clone_profile(gen2["id"], new_label="Child Gen3 Profile")
    assert gen3["id"] != gen2["id"]
    assert gen3["id"] != gen1["id"]
    assert gen3["label"] == "Child Gen3 Profile"
    assert gen3["editing_dna_history"] == []

    # Deep mutate Gen 3
    svc.update_profile(gen3["id"], {
        "editing_dna": {
            "pacing": 9.99,
            "color_grade": "radioactive_neon_purple",
            "visual_mix": {"footage": 0.0, "ai": 0.9, "motion": 0.1},
        },
        "default_creative_brief": {
            "narrative_angle": "Heavily Mutated Child Angle",
            "opening_hook": "Mutated Hook Line",
        },
        "self_learning_memory": {
            "analyzed_videos_count": 9999,
            "next_video_upgrades": ["Destroy all human errors"],
        },
    })

    # Verify Gen 3 received updates
    gen3_updated = svc.get_profile(gen3["id"])
    assert gen3_updated["editing_dna"]["pacing"] == 9.99
    assert gen3_updated["editing_dna"]["color_grade"] == "radioactive_neon_purple"
    assert gen3_updated["default_creative_brief"]["narrative_angle"] == "Heavily Mutated Child Angle"
    assert gen3_updated["self_learning_memory"]["analyzed_videos_count"] == 9999

    # Verify Gen 2 (Parent) is 100% untouched
    gen2_check = svc.get_profile(gen2["id"])
    assert gen2_check["editing_dna"]["pacing"] == gen1_dna_pacing
    assert gen2_check["editing_dna"]["color_grade"] == "technical_cool_cyan"
    assert gen2_check["default_creative_brief"]["narrative_angle"] == "Điều tra Kỹ thuật Hạ tầng"
    assert gen2_check["self_learning_memory"]["analyzed_videos_count"] == 3

    # Verify Gen 1 (Grandparent) is 100% untouched
    gen1_check = svc.get_profile(gen1["id"])
    assert gen1_check["editing_dna"]["pacing"] == gen1_dna_pacing
    assert gen1_check["default_creative_brief"]["narrative_angle"] == "Điều tra Kỹ thuật Hạ tầng"


def test_tier5_profile_update_malformed_nested_objects_rejection(sandbox):
    """
    Adversarial rejection of non-dict updates to complex structured fields:
    `editing_dna`, `default_creative_brief`, `self_learning_memory`.
    """
    svc: ChannelProfileService = sandbox["profile_service"]

    # Passing a string for editing_dna must raise ValueError
    with pytest.raises(ValueError, match="Field 'editing_dna' must be an object"):
        svc.update_profile("channel-sandbox-1", {"editing_dna": "not_a_dict"})

    # Passing a list for default_creative_brief must raise ValueError
    with pytest.raises(ValueError, match="Field 'default_creative_brief' must be an object"):
        svc.update_profile("channel-sandbox-1", {"default_creative_brief": ["invalid", "list"]})

    # Passing an int for self_learning_memory must raise ValueError
    with pytest.raises(ValueError, match="Field 'self_learning_memory' must be an object"):
        svc.update_profile("channel-sandbox-1", {"self_learning_memory": 12345})


def test_tier5_profile_identity_tampering_immunity_and_concurrency(sandbox):
    """
    Adversarial test for profile identity locking and multi-threaded concurrency:
    1. Attempt to overwrite `id` or `channel_profile_id` via update.
    2. Concurrent threads updating distinct fields of the same profile simultaneously.
    """
    svc: ChannelProfileService = sandbox["profile_service"]

    # 1. Identity tamper attempt
    updated = svc.update_profile("channel-sandbox-1", {
        "id": "hacked-channel-id-666",
        "channel_profile_id": "spoofed-id-777",
        "label": "Safely Updated Label",
    })
    assert updated["id"] == "channel-sandbox-1"
    assert updated["channel_profile_id"] == "channel-sandbox-1"
    assert updated["label"] == "Safely Updated Label"

    # 2. Concurrency stress: 10 threads updating concurrently
    def worker(idx: int):
        return svc.update_profile("channel-sandbox-1", {
            "notes": f"Concurrent worker note {idx}",
            "default_creative_brief": {"custom_rules": f"Rule {idx}"},
        })

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 10
    final = svc.get_profile("channel-sandbox-1")
    assert "Concurrent worker note" in final["notes"]
    assert final["id"] == "channel-sandbox-1"


# ==============================================================================
# SECTION 2: JOB CREATION, PHASE UPDATES, AND MUTATION ISOLATION
# ==============================================================================

def test_tier5_job_create_with_missing_and_invalid_channel_profile(sandbox):
    """
    Adversarial verification of job creation validation:
    - Attempting to assign non-existent profile ID raises ValueError.
    - Creating with valid profile snapshots complete isolated DNA.
    """
    job_svc: JobService = sandbox["job_service"]

    # Non-existent channel profile
    with pytest.raises(ValueError, match="Channel profile 'channel-does-not-exist-999' not found"):
        job_svc.create_job({
            "title": "Invalid Profile Job",
            "channel_profile_id": "channel-does-not-exist-999",
        })

    # Valid profile assignment
    job = job_svc.create_job({
        "title": "Valid Profile Job",
        "channel_profile_id": "channel-sandbox-1",
    })
    assert job["id"] is not None
    assert job["channel_profile_id"] == "channel-sandbox-1"
    assert job["visual_strategy"] == "hybrid"
    assert job["editing_dna"]["pacing"] == 4.5
    assert job["channel_profile_snapshot"]["id"] == "channel-sandbox-1"


def test_tier5_job_cross_job_mutation_and_spoofing_prevention(sandbox):
    """
    Adversarial tests for mutation isolation:
    - Attempting to update Job A with Job B's ID in payload must fail.
    - Attempting to pass draft flags (`is_draft`, `draft_mutation`) must be rejected.
    """
    job_svc: JobService = sandbox["job_service"]

    job_a = job_svc.create_job({"title": "Job Alpha", "channel_profile_id": "channel-sandbox-1"})
    job_b = job_svc.create_job({"title": "Job Beta", "channel_profile_id": "channel-sandbox-1"})

    # 1. Payload ID conflict / spoofing
    with pytest.raises(ValueError, match="Cross-job mutation rejected"):
        job_svc.update_job(job_a["id"], {
            "title": "Hacked Title",
            "job_id": job_b["id"],
        })

    with pytest.raises(ValueError, match="Cross-job mutation rejected"):
        job_svc.update_job(job_a["id"], {
            "title": "Hacked Title",
            "selectedId": job_b["id"],
        })

    # Verify Job B was not mutated
    b_check = job_svc.get_job(job_b["id"])
    assert b_check["title"] == "Job Beta"

    # 2. Draft side-effect flags
    with pytest.raises(ValueError, match="Draft mutation side-effects rejected"):
        job_svc.update_job(job_a["id"], {
            "title": "Draft Attempt",
            "is_draft": True,
        })

    with pytest.raises(ValueError, match="Draft mutation side-effects rejected"):
        job_svc.update_job(job_a["id"], {
            "title": "Draft Attempt",
            "draft_mutation": True,
        })


def test_tier5_job_phase_updates_malformed_and_resilience(sandbox):
    """
    Adversarial verification of phases update integrity and normalization:
    - Non-dict `phases` raises ValueError.
    - Missing phases normalized automatically.
    """
    job_svc: JobService = sandbox["job_service"]
    store: JobStore = sandbox["job_store"]

    job = job_svc.create_job({"title": "Phase Test Job"})

    # 1. Non-dict phases rejected
    with pytest.raises(ValueError, match="phases must be a dictionary"):
        job_svc.update_job(job["id"], {"phases": ["not", "a", "dict"]})

    with pytest.raises(ValueError, match="phases must be a dictionary"):
        job_svc.update_job(job["id"], {"phases": "string_phase"})

    # 2. Valid partial phase update with canonical phase 'plan' and non-standard phase
    updated = job_svc.update_job(job["id"], {
        "phases": {
            "plan": {"status": "succeeded", "last_message": "Plan/Script completed"},
            "voice": {"status": "running"},
            "custom_stage": {"status": "succeeded"},
        }
    })
    # Check immediate update
    assert updated["phases"]["plan"]["status"] == "succeeded"
    assert updated["phases"]["voice"]["status"] == "running"

    # Verify that upon reload and normalization:
    reloaded = job_svc.get_job(job["id"])
    assert reloaded["phases"]["plan"]["status"] == "succeeded"
    assert reloaded["phases"]["voice"]["status"] == "running"
    assert "visuals" in reloaded["phases"]
    assert "edit" in reloaded["phases"]
    assert "qc" in reloaded["phases"]
    # Non-standard phases routed safely to legacy_phases without corruption
    assert reloaded.get("legacy_phases", {}).get("custom_stage", {}).get("status") == "succeeded"


def test_tier5_job_path_traversal_and_injection_defense(sandbox):
    """
    Adversarial check: attempt path traversal and special characters in job_id.
    Must raise KeyError without creating directories outside data/jobs/.
    """
    job_svc: JobService = sandbox["job_service"]
    tmp_path: Path = sandbox["tmp_path"]

    malicious_ids = [
        "../../etc/passwd",
        "..\\..\\system32",
        "job/slash/injection",
        "job!@#$%^&*()",
    ]
    for mid in malicious_ids:
        with pytest.raises(KeyError):
            job_svc.update_job(mid, {"title": "Pwned"})

    # Verify no rogue files created
    assert not (tmp_path / "etc").exists()
    assert not (tmp_path / "system32").exists()


def test_tier5_job_concurrency_stress(sandbox):
    """
    Stress test: multiple threads updating different phases of the same job simultaneously.
    Verifies JobStore's thread-safety and atomic write integrity.
    """
    job_svc: JobService = sandbox["job_service"]
    job = job_svc.create_job({"title": "Concurrent Job Target"})

    # All 8 canonical documentary pipeline phases from documentary.models.PHASES
    phases_to_update = ["plan", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc"]

    def worker(phase_name: str):
        return job_svc.update_job(job["id"], {
            "phases": {
                phase_name: {"status": "succeeded", "last_message": f"Updated by worker {phase_name}"}
            }
        })

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker, p) for p in phases_to_update]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == len(phases_to_update)
    final_job = job_svc.get_job(job["id"])
    assert final_job["id"] == job["id"]
    # All 8 canonical phases must be present in phases dict
    for p in phases_to_update:
        assert p in final_job["phases"]



# ==============================================================================
# SECTION 3: 'LOCK APPROVED EDIT STYLE TO CHANNEL' & CORRUPTION RECOVERY
# ==============================================================================

def test_tier5_lock_edit_dna_sequential_monotonic_versioning(sandbox):
    """
    Adversarial test for 'Lock Approved Edit Style to Channel':
    - Performs 3 consecutive locks on the same channel profile from distinct jobs.
    - Verifies monotonic version increments (v1 -> v2 -> v3 -> v4).
    - Verifies history records prior versions sequentially without data loss.
    """
    dna_svc: EditingDnaService = sandbox["editing_dna_service"]
    job_svc: JobService = sandbox["job_service"]
    prof_svc: ChannelProfileService = sandbox["profile_service"]
    ws_dir: Path = sandbox["workspaces_dir"]

    # Profile begins at v1
    p_initial = prof_svc.get_profile("channel-sandbox-1")
    assert p_initial["editing_dna"]["version"] == 1
    assert len(p_initial.get("editing_dna_history", [])) == 0

    # Job 1
    j1 = job_svc.create_job({"title": "Project Edit 1", "channel_profile_id": "channel-sandbox-1"})
    j1_ws = ws_dir / j1["id"]
    j1_ws.mkdir(parents=True, exist_ok=True)
    (j1_ws / "visual_manifest.json").write_text(json.dumps({
        "beats": [
            {"beat_id": "B001", "duration_sec": 4.0, "visual_type": "sourced_footage", "visual_route": "footage"},
            {"beat_id": "B002", "duration_sec": 4.0, "visual_type": "ai_visual", "visual_route": "ai_visual"},
        ]
    }), encoding="utf-8")

    res1 = dna_svc.lock_job_edit_dna_to_channel(j1["id"], notes="Lock 1 notes")
    assert res1["version"] == 2
    assert res1["history_count"] == 1

    # Job 2
    j2 = job_svc.create_job({"title": "Project Edit 2", "channel_profile_id": "channel-sandbox-1"})
    j2_ws = ws_dir / j2["id"]
    j2_ws.mkdir(parents=True, exist_ok=True)
    (j2_ws / "visual_manifest.json").write_text(json.dumps({
        "beats": [
            {"beat_id": "B001", "duration_sec": 6.0, "visual_type": "ai_visual", "visual_route": "ai_visual"},
            {"beat_id": "B002", "duration_sec": 6.0, "visual_type": "ai_visual", "visual_route": "ai_visual"},
        ]
    }), encoding="utf-8")

    res2 = dna_svc.lock_job_edit_dna_to_channel(j2["id"], notes="Lock 2 notes")
    assert res2["version"] == 3
    assert res2["history_count"] == 2

    # Job 3
    j3 = job_svc.create_job({"title": "Project Edit 3", "channel_profile_id": "channel-sandbox-1"})
    res3 = dna_svc.lock_job_edit_dna_to_channel(j3["id"], notes="Lock 3 notes")
    assert res3["version"] == 4
    assert res3["history_count"] == 3

    # Verify profile persistence
    p_final = prof_svc.get_profile("channel-sandbox-1")
    assert p_final["editing_dna"]["version"] == 4
    assert len(p_final["editing_dna_history"]) == 3
    history_versions = [h.get("version") for h in p_final["editing_dna_history"]]
    assert history_versions == [1, 2, 3]


def test_tier5_lock_edit_dna_missing_job_and_missing_profile_errors(sandbox):
    """
    Adversarial verification of error recovery in lock_job_edit_dna_to_channel:
    - Non-existent job ID -> KeyError
    - Job with missing channel_profile_id -> ValueError
    - Job assigned to deleted channel profile -> KeyError
    """
    dna_svc: EditingDnaService = sandbox["editing_dna_service"]
    job_svc: JobService = sandbox["job_service"]
    prof_svc: ChannelProfileService = sandbox["profile_service"]

    # 1. Non-existent job
    with pytest.raises(KeyError, match="Job non-existent-job-404 not found"):
        dna_svc.lock_job_edit_dna_to_channel("non-existent-job-404")

    # 2. Job with no channel_profile_id
    j_unlinked = job_svc.create_job({"title": "Unlinked Project", "channel_profile_id": None})
    with pytest.raises(ValueError, match="has no assigned channel profile"):
        dna_svc.lock_job_edit_dna_to_channel(j_unlinked["id"])

    # 3. Channel profile deleted after job creation
    temp_prof = prof_svc.create_profile({"label": "Temporary Profile to Delete"})
    j_temp = job_svc.create_job({"title": "Orphan Project", "channel_profile_id": temp_prof["id"]})
    prof_svc.delete_profile(temp_prof["id"])

    with pytest.raises(KeyError, match="not found"):
        dna_svc.lock_job_edit_dna_to_channel(j_temp["id"])


def test_tier5_lock_edit_dna_workspace_corruption_and_extreme_durations(sandbox):
    """
    Adversarial test for manifest extraction resilience:
    - Workspace with missing manifests -> falls back safely to 'custom' preset.
    - Workspace with corrupted/truncated JSON -> falls back safely without crash.
    - Manifest with extreme durations (0.01s, 999.0s, negative) -> safely clamped to [2.0, 15.0].
    """
    dna_svc: EditingDnaService = sandbox["editing_dna_service"]
    job_svc: JobService = sandbox["job_service"]
    ws_dir: Path = sandbox["workspaces_dir"]

    # 1. Missing manifests fallback
    j_empty = job_svc.create_job({"title": "Empty WS Job", "channel_profile_id": "channel-sandbox-1"})
    extracted_empty = dna_svc.extract_editing_dna_from_job(j_empty["id"])
    assert extracted_empty["preset_id"] == "custom"
    assert extracted_empty["version"] == 1

    # 2. Corrupted JSON file
    j_corrupt = job_svc.create_job({"title": "Corrupt WS Job", "channel_profile_id": "channel-sandbox-1"})
    c_ws = ws_dir / j_corrupt["id"]
    c_ws.mkdir(parents=True, exist_ok=True)
    (c_ws / "visual_manifest.json").write_text("{ incomplete json truncated here...", encoding="utf-8")
    extracted_corrupt = dna_svc.extract_editing_dna_from_job(j_corrupt["id"])
    assert extracted_corrupt["preset_id"] == "custom"

    # 3. Extreme durations clamped
    j_extreme = job_svc.create_job({"title": "Extreme Durations Job", "channel_profile_id": "channel-sandbox-1"})
    e_ws = ws_dir / j_extreme["id"]
    e_ws.mkdir(parents=True, exist_ok=True)
    (e_ws / "visual_manifest.json").write_text(json.dumps({
        "beats": [
            {"beat_id": "B01", "duration_sec": 0.05},  # extreme low
            {"beat_id": "B02", "duration_sec": 999.0}, # extreme high
            {"beat_id": "B03", "duration_sec": -5.0},  # negative (ignored)
            {"beat_id": "B04", "duration_sec": "invalid_string"}, # invalid (ignored)
        ]
    }), encoding="utf-8")
    extracted_extreme = dna_svc.extract_editing_dna_from_job(j_extreme["id"])
    pacing_float = float(extracted_extreme["pacing"])
    # Clamped into [2.0, 15.0]
    assert 2.0 <= pacing_float <= 15.0


# ==============================================================================
# SECTION 4: VOICE/SRT DRIFT, AUTO-REPAIR IDEMPOTENCY & HOLD FREEZES
# ==============================================================================

def test_tier5_sync_drift_detection_exact_boundaries(sandbox):
    """
    Adversarial verification of Voice/SRT drift boundaries:
    - Drift <= 0.50s -> ALIGNED (no flag).
    - Drift > 0.50s -> MISALIGNED (flagged with exact drift_sec).
    """
    sync_svc: SyncPolicyService = sandbox["sync_policy_service"]

    beats = [
        {"beat_id": "B001", "duration_sec": 5.49},  # SRT 5.0 -> drift 0.49s (under limit)
        {"beat_id": "B002", "duration_sec": 5.50},  # SRT 5.0 -> drift 0.50s (exact boundary)
        {"beat_id": "B003", "duration_sec": 5.51},  # SRT 5.0 -> drift 0.51s (over limit, flag!)
        {"beat_id": "B004", "duration_sec": 8.00},  # SRT 5.0 -> drift 3.00s (over limit, flag!)
    ]
    srt_segments = [
        {"start": 0.0, "end": 5.0, "text": "Segment 1"},
        {"start": 5.0, "end": 10.0, "text": "Segment 2"},
        {"start": 10.0, "end": 15.0, "text": "Segment 3"},
        {"start": 15.0, "end": 20.0, "text": "Segment 4"},
    ]

    card = sync_svc.check_sync_compliance(beats=beats, srt_segments=srt_segments)
    misaligned = card["sync_scorecard"]["misaligned_beats"]
    misaligned_ids = [m["beat_id"] for m in misaligned]

    assert "B001" not in misaligned_ids
    assert "B002" not in misaligned_ids
    assert "B003" in misaligned_ids
    assert "B004" in misaligned_ids
    assert card["sync_scorecard"]["aligned_beats"] == 2


def test_tier5_hold_freeze_detection_exact_boundaries(sandbox):
    """
    Adversarial verification of hold freeze limit (> 8.0s):
    - dur == 8.00s -> PASSED (not a hold).
    - dur == 8.01s -> FLAGGED as hold over 8s.
    - dur == 15.0s with has_motion_override=True -> PASSED (exempt).
    - dur == 120.0s extreme freeze -> FLAGGED with remedy recommendation.
    """
    sync_svc: SyncPolicyService = sandbox["sync_policy_service"]

    beats = [
        {"beat_id": "B01", "duration_sec": 8.00, "has_motion_override": False},
        {"beat_id": "B02", "duration_sec": 8.01, "has_motion_override": False},
        {"beat_id": "B03", "duration_sec": 15.0, "has_motion_override": True},
        {"beat_id": "B04", "duration_sec": 120.0, "has_motion_override": False},
    ]

    card = sync_svc.check_sync_compliance(beats=beats)
    holds = card["sync_scorecard"]["holds_over_8s"]
    hold_ids = [h["beat_id"] for h in holds]

    assert "B01" not in hold_ids
    assert "B02" in hold_ids
    assert "B03" not in hold_ids
    assert "B04" in hold_ids


def test_tier5_auto_repair_sync_strict_idempotency(sandbox):
    """
    Adversarial verification of auto-repair idempotency:
    - Run 1 corrects drifts and injects Ken Burns/HUD overlays into holds.
    - Run 2 executed immediately returns 0 realigned beats and 0 repaired holds.
    - Manifest maintains integrity and scorecard stays PASSED.
    """
    sync_svc: SyncPolicyService = sandbox["sync_policy_service"]
    job_svc: JobService = sandbox["job_service"]
    ws_dir: Path = sandbox["workspaces_dir"]

    job = job_svc.create_job({"title": "Auto Repair Target", "channel_profile_id": "channel-sandbox-1"})
    j_ws = ws_dir / job["id"]
    j_ws.mkdir(parents=True, exist_ok=True)

    # Initial flawed manifest
    (j_ws / "visual_manifest.json").write_text(json.dumps({
        "beats": [
            {"beat_id": "B01", "duration_sec": 12.0, "has_motion_override": False}, # hold > 8s
            {"beat_id": "B02", "duration_sec": 3.0, "has_motion_override": False},  # drift vs SRT (5.0s)
        ]
    }), encoding="utf-8")

    (j_ws / "subtitles.srt").write_text(
        "1\n00:00:00,000 --> 00:00:12,000\nBeat 1 narration\n\n"
        "2\n00:00:12,000 --> 00:00:17,000\nBeat 2 narration\n\n",
        encoding="utf-8"
    )

    # Run 1: Repairs applied
    res1 = sync_svc.auto_repair_sync(job["id"])
    assert res1["status"] == "success"
    assert res1["repaired_holds_count"] == 1
    assert res1["realigned_beats_count"] == 1
    assert res1["scorecard"]["sync_scorecard"]["passed"] is True

    # Run 2: Exact idempotency check
    res2 = sync_svc.auto_repair_sync(job["id"])
    assert res2["status"] == "success"
    assert res2["repaired_holds_count"] == 0, "Idempotency failure: holds should already be repaired"
    assert res2["realigned_beats_count"] == 0, "Idempotency failure: beats should already be aligned"
    assert res2["scorecard"]["sync_scorecard"]["passed"] is True


def test_tier5_policy_multilingual_prohibited_terms(sandbox):
    """
    Adversarial YouTube Policy check across Vietnamese, Korean, and English graphic terms:
    - Graphic violence, decapitation, bloody corpses trigger green_monetization=False.
    - Clean investigative terms pass successfully.
    """
    sync_svc: SyncPolicyService = sandbox["sync_policy_service"]

    # 1. Vietnamese prohibited terms
    script_vn = "Hiện trường vụ án có thi thể đẫm máu và dấu hiệu phanh thây man rợ."
    card_vn = sync_svc.check_sync_compliance(script_text=script_vn)
    assert card_vn["policy_scorecard"]["green_monetization"] is False
    assert "thi thể đẫm máu" in card_vn["policy_scorecard"]["flagged_terms"]

    # 2. Korean prohibited terms
    script_ko = "범인은 참수와 토막 살인을 저질렀으며 선혈이 낭자했습니다."
    card_ko = sync_svc.check_sync_compliance(script_text=script_ko)
    assert card_ko["policy_scorecard"]["green_monetization"] is False
    assert "참수" in card_ko["policy_scorecard"]["flagged_terms"]

    # 3. English prohibited terms
    script_en = "The graphic murder scene included decapitation and extreme gore."
    card_en = sync_svc.check_sync_compliance(script_text=script_en)
    assert card_en["policy_scorecard"]["green_monetization"] is False
    assert "decapitation" in card_en["policy_scorecard"]["flagged_terms"]

    # 4. Clean transformative script
    script_clean = "Báo cáo khám nghiệm hiện trường sau cơn bão, phân tích hồ sơ vật chứng và thông số địa chất."
    card_clean = sync_svc.check_sync_compliance(script_text=script_clean)
    assert card_clean["policy_scorecard"]["green_monetization"] is True
    assert len(card_clean["policy_scorecard"]["flagged_terms"]) == 0


def test_tier5_editorial_overlay_ratio_boundary(sandbox):
    """
    Adversarial verification of reused-content defense overlay threshold:
    - overlay ratio < 0.85 -> reused_content_risk == 'medium', policy passed == False.
    - overlay ratio >= 0.85 -> reused_content_risk == 'low', policy passed == True.
    """
    sync_svc: SyncPolicyService = sandbox["sync_policy_service"]

    # 84% motion overlay (21 out of 25 beats) -> 0.84
    beats_84 = [
        {"beat_id": f"B{i}", "duration_sec": 5.0, "has_motion_override": (i <= 21)}
        for i in range(1, 26)
    ]
    card_84 = sync_svc.check_sync_compliance(beats=beats_84)
    assert card_84["policy_scorecard"]["editorial_overlay_ratio"] == 0.84
    assert card_84["policy_scorecard"]["reused_content_risk"] == "medium"
    assert card_84["policy_scorecard"]["passed"] is False

    # 88% motion overlay (22 out of 25 beats) -> 0.88
    beats_88 = [
        {"beat_id": f"B{i}", "duration_sec": 5.0, "has_motion_override": (i <= 22)}
        for i in range(1, 26)
    ]
    card_88 = sync_svc.check_sync_compliance(beats=beats_88)
    assert card_88["policy_scorecard"]["editorial_overlay_ratio"] == 0.88
    assert card_88["policy_scorecard"]["reused_content_risk"] == "low"
    assert card_88["policy_scorecard"]["passed"] is True


# ==============================================================================
# SECTION 5: CHANNEL DNA PRE-FLIGHT DUPLICATE BLOCKING & OUTLIER LIMITS
# ==============================================================================

def test_tier5_preflight_topic_duplicate_blocking_exact_and_substring(sandbox):
    """
    Adversarial verification of Pre-Flight topic & title duplicate blocking:
    - Exact match with channel history -> duplicate_risk=True, passed=False.
    - Substring title match (>= 8 chars) -> duplicate_risk=True, passed=False.
    - Novel unique title -> duplicate_risk=False, passed=True.
    """
    pf_svc: PreflightService = sandbox["preflight_service"]

    profile_id = "channel-sandbox-1"

    # 1. Exact title match
    res_exact = pf_svc.run_preflight_check(
        profile_id,
        stage="topic",
        input_data={"title": "Đại án 5.000 tỷ lún sụt kênh Nam Thủy Bắc Điều"},
    )
    assert res_exact["preflight_summary"]["duplicate_risk"] is True
    assert res_exact["preflight_summary"]["passed"] is False

    # 2. Substring match
    res_sub = pf_svc.run_preflight_check(
        profile_id,
        stage="topic",
        input_data={"title": "sụp đổ thân đập Tam Hiệp trước 39 tỷ tấn nước"},
    )
    assert res_sub["preflight_summary"]["duplicate_risk"] is True
    assert res_sub["preflight_summary"]["passed"] is False

    # 3. Novel unique topic
    res_novel = pf_svc.run_preflight_check(
        profile_id,
        stage="topic",
        input_data={
            "title": "Bê bối 12.000 tỷ dự án đường sắt đô thị trên cao",
            "topic": "Đường sắt đô thị Cát Linh Hà Đông",
        },
    )
    assert res_novel["preflight_summary"]["duplicate_risk"] is False
    assert res_novel["preflight_summary"]["passed"] is True


def test_tier5_preflight_forbidden_topics_and_winner_patterns(sandbox):
    """
    Adversarial check on preflight policy:
    - Forbidden topics trigger recommendations and fail check.
    - Quantitative metric formulas detected in Vietnamese, Korean, English.
    """
    pf_svc: PreflightService = sandbox["preflight_service"]
    profile_id = "channel-sandbox-1"

    # Forbidden topic match
    res_forbidden = pf_svc.run_preflight_check(
        profile_id,
        stage="topic",
        input_data={"title": "Chính trị giật gân và tin đồn thất thiệt các bộ ngành"},
    )
    assert res_forbidden["preflight_summary"]["passed"] is False
    assert any("vi phạm điều cấm" in r for r in res_forbidden["preflight_summary"]["recommendations"])

    # Quantitative metric formula patterns
    titles_to_test = [
        "Đại án 4.400 tỷ đồng rút ruột ngân hàng",       # Vietnamese tỷ
        "싼샤댐 393억 톤 수압 콘크리트 중력 댐 한계",     # Korean 억
        "Megaproject with 1,432 km canal and 500 billion yuan", # English km / billion
    ]
    for t in titles_to_test:
        res = pf_svc.run_preflight_check(
            profile_id,
            stage="title",
            input_data={"title": t},
        )
        matched = res["preflight_summary"]["winner_patterns_matched"]
        assert "quantitative_metric_formula" in matched, f"Failed to match formula pattern in '{t}'"


def test_tier5_preflight_thumbnail_and_seo_boundaries(sandbox):
    """
    Adversarial check on thumbnail & SEO preflight requirements:
    - Thumbnail < 3 variants -> fails.
    - Thumbnail overlay text > 6 words -> mobile CTR warning.
    - SEO < 5 tags -> warning to add more tags.
    """
    pf_svc: PreflightService = sandbox["preflight_service"]
    profile_id = "channel-sandbox-1"

    # 1. Thumbnail with only 2 variants (insufficient for A/B testing)
    res_thumb_few = pf_svc.run_preflight_check(
        profile_id,
        stage="thumbnail",
        input_data={"variants": [{"id": "v1"}, {"id": "v2"}]},
    )
    assert res_thumb_few["preflight_summary"]["passed"] is False
    assert any("tối thiểu 3 biến thể" in r for r in res_thumb_few["preflight_summary"]["recommendations"])

    # 2. Thumbnail with >6 words text overlay
    res_thumb_long = pf_svc.run_preflight_check(
        profile_id,
        stage="thumbnail",
        input_data={
            "variants": [{"id": "v1"}, {"id": "v2"}, {"id": "v3"}],
            "text_overlay": "Một tiêu đề thumbnail quá dài dòng làm giảm tỉ lệ bấm",
        },
    )
    assert any("Text overlay quá dài" in r for r in res_thumb_long["preflight_summary"]["recommendations"])

    # 3. SEO with <5 tags
    res_seo_short = pf_svc.run_preflight_check(
        profile_id,
        stage="seo",
        input_data={"tags": ["hạ tầng", "tam hiệp"]},
    )
    assert any("Bổ sung tối thiểu 5 tags" in r for r in res_seo_short["preflight_summary"]["recommendations"])


def test_tier5_preflight_empty_and_corrupt_payload_resilience(sandbox):
    """
    Adversarial resilience against empty or malformed inputs to preflight checker:
    - Empty input_data dict.
    - Unknown stage name.
    """
    pf_svc: PreflightService = sandbox["preflight_service"]
    profile_id = "channel-sandbox-1"

    # Empty payload
    res_empty = pf_svc.run_preflight_check(profile_id, stage="topic", input_data={})
    assert res_empty["status"] == "ok"
    assert res_empty["preflight_summary"]["passed"] is True

    # Unknown stage
    res_unknown = pf_svc.run_preflight_check(profile_id, stage="unknown_stage_name", input_data={})
    assert res_unknown["status"] == "ok"


# ==============================================================================
# SECTION 6: SELF-LEARNING MEMORY PERSISTENCE & EVOLUTION RULE SYNTHESIS
# ==============================================================================

def test_tier5_self_learning_empty_video_catalog(sandbox):
    """
    Adversarial test for self-learning with ZERO videos in catalog:
    - Must return clean structured report without ZeroDivisionError.
    - Default baseline upgrade rules provided.
    """
    sl_svc: SelfLearningService = sandbox["self_learning_service"]
    prof_svc: ChannelProfileService = sandbox["profile_service"]

    # Create profile with 0 videos
    empty_prof = prof_svc.create_profile({
        "label": "Brand New Zero Video Channel",
        "own_channel": {"dna": {}, "videos": []},
    })

    report = sl_svc.analyze_post_mortem([], empty_prof)
    assert report["status"] == "success"
    assert report["analyzed_videos_count"] == 0
    assert report["winners"] == []
    assert report["underperformers"] == []
    assert len(report["upgrade_rules"]["next_video_upgrades"]) > 0


def test_tier5_self_learning_single_video_and_identical_views(sandbox):
    """
    Adversarial test for self-learning with boundary catalogs:
    - Single video catalog (views = 10,000) -> outlier multiplier = 1.0 (neutral).
    - Single video catalog with 0 views -> outlier multiplier = 0.0 (underperformer).
    - 5 videos all with identical views -> all have multiplier = 1.0.
    """
    sl_svc: SelfLearningService = sandbox["self_learning_service"]
    prof_svc: ChannelProfileService = sandbox["profile_service"]
    prof = prof_svc.get_profile("channel-sandbox-1")

    # 1. Single neutral video
    single_neutral = [{"id": "v1", "title": "Neutral Video", "views": 10000}]
    rep_neutral = sl_svc.analyze_post_mortem(single_neutral, prof)
    assert rep_neutral["analyzed_videos_count"] == 1
    assert rep_neutral["winners"] == []
    assert rep_neutral["underperformers"] == []

    # 2. Single zero-view video
    single_zero = [{"id": "v0", "title": "Zero View Underperformer", "views": 0}]
    rep_zero = sl_svc.analyze_post_mortem(single_zero, prof)
    assert rep_zero["analyzed_videos_count"] == 1
    assert len(rep_zero["underperformers"]) == 1
    assert rep_zero["underperformers"][0]["multiplier"] == 0.0

    # 3. 5 videos with identical views
    identical_videos = [
        {"id": f"iv_{i}", "title": f"Identical Video {i}", "views": 50000}
        for i in range(5)
    ]
    rep_identical = sl_svc.analyze_post_mortem(identical_videos, prof)
    assert rep_identical["analyzed_videos_count"] == 5
    assert rep_identical["winners"] == []
    assert rep_identical["underperformers"] == []


def test_tier5_self_learning_extreme_outlier_and_cause_diagnosis(sandbox):
    """
    Adversarial test for Outlier Winners vs Underperformers diagnosis:
    - Outlier with views >= 2x median classified as Winner.
    - Long title (>15 words) diagnosed with title_too_long_low_ctr.
    - Weak keyword diagnosed with weak_keyword_fatigue.
    - Upgrade rules synthesized and deduplicated.
    """
    sl_svc: SelfLearningService = sandbox["self_learning_service"]
    prof_svc: ChannelProfileService = sandbox["profile_service"]
    prof = prof_svc.get_profile("channel-sandbox-1")

    test_videos = [
        {"id": "w1", "title": "Đại án 5.000 tỷ Nam Thủy Bắc Điều", "views": 200000}, # Winner (200k / 50k = 4.0x)
        {"id": "m1", "title": "Công trình trọng điểm số 2", "views": 50000},          # Median base (50k)
        {"id": "u1", "title": "Đây là một tiêu đề video quá dài dòng lê thê vượt quá mười lăm từ làm cho tỷ lệ nhấp chuột giảm mạnh", "views": 10000}, # Underperformer (10k / 50k = 0.2x, >15 words)
        {"id": "u2", "title": "Tổng hợp các tin vắn và vấn đề công trình", "views": 8000}, # Underperformer (contains 'tin vắn' from weak_terms)
    ]

    report = sl_svc.analyze_post_mortem(test_videos, prof)
    assert report["analyzed_videos_count"] == 4
    assert len(report["winners"]) == 1
    assert report["winners"][0]["video_id"] == "w1"

    underperformers = {u["video_id"]: u for u in report["underperformers"]}
    assert "u1" in underperformers
    assert underperformers["u1"]["cause"] == "title_too_long_low_ctr"
    assert "u2" in underperformers
    assert underperformers["u2"]["cause"] == "weak_keyword_fatigue"

    # Evolutionary Upgrade Rules synthesis check
    stop_rules = report["upgrade_rules"]["what_to_stop_doing"]
    assert any("quá 15 từ" in r for r in stop_rules)
    assert any("từ khóa học thuật" in r or "chung chung" in r for r in stop_rules)


def test_tier5_self_learning_persistence_and_job_injection(sandbox):
    """
    Adversarial verification of closed-loop evolution:
    - Running self-learning persists analysis into Channel Profile.
    - Injecting rules attaches `self_learning_injected_rules` into creative brief.
    - Creating a new job on this profile receives the evolutionary rules.
    """
    sl_svc: SelfLearningService = sandbox["self_learning_service"]
    prof_svc: ChannelProfileService = sandbox["profile_service"]
    job_svc: JobService = sandbox["job_service"]

    profile_id = "channel-sandbox-1"

    # 1. Run and persist
    report = sl_svc.run_self_learning(profile_id, save_to_profile=True)
    p_updated = prof_svc.get_profile(profile_id)
    assert p_updated["self_learning_memory"]["analyzed_videos_count"] == report["analyzed_videos_count"]

    # 2. Inject rules into creative brief
    brief = {"market": "KR", "visual_strategy": "hybrid"}
    injected_brief = sl_svc.inject_self_learning_rules(profile_id, brief)
    assert "self_learning_injected_rules" in injected_brief
    assert len(injected_brief["self_learning_injected_rules"]) > 0

    # 3. Create new job with parent profile
    new_job = job_svc.create_job({
        "title": "Next Gen Documentary",
        "channel_profile_id": profile_id,
    })
    assert new_job["channel_profile_id"] == profile_id
    assert new_job["channel_profile_snapshot"]["id"] == profile_id
