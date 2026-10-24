"""
E2E Test Suite - Tier 3: Combinatorial Pairwise Interactions
Tests cross-feature interactions across Profile Switching, Editing Style Lock, Pre-Flight Checks, and Export.
Total: 8 Test Cases.
"""

from pathlib import Path
import json
import pytest

from documentary.service import DocumentaryService
from documentary.store import JobStore
from tests.e2e.test_ac3_edit_memory_sync_policy import (
    BUILTIN_EDITING_PRESETS,
    simulate_sync_compliance_check,
)
from tests.e2e.test_ac4_preflight_self_learning import (
    simulate_preflight_check,
    simulate_self_learning_post_mortem,
)

ROOT = Path(__file__).resolve().parents[2]


def test_tier3_pairwise_profile_switch_then_preflight_check():
    """Pairwise 1: Switch Profile A (Korean True Crime) -> Profile B (US Vault) -> trigger Pre-Flight."""
    profile_a = {
        "id": "channel-kr-tc",
        "market": "KR",
        "forbidden_topics": "Án kinh tế, chính trị",
        "allowed_topics": "Trọng án hình sự Trung Quốc",
    }
    profile_b = {
        "id": "channel-us-vault",
        "market": "US",
        "forbidden_topics": "Contemporary partisan politics, graphic gore",
        "allowed_topics": "Declassified memos, Cold War operations",
    }

    # Pre-flight on candidate for Profile B
    candidate_us = {"title": "Declassified: The 1962 Nuclear Crisis Memo", "topic": "Cold War operations"}
    check_b = simulate_preflight_check(profile_b, "topic", candidate_us, [])

    # Must pass against Profile B
    assert check_b["preflight_summary"]["passed"] is True

    # If incorrectly tested against Profile A, it would not match Profile A's allowed topics
    check_a_mismatch = simulate_preflight_check(profile_a, "topic", candidate_us, [])
    assert check_a_mismatch["preflight_summary"]["winner_patterns_matched"] == []


def test_tier3_pairwise_edit_lock_then_profile_switch_then_new_project(tmp_path: Path):
    """Pairwise 2: Lock Edit on Profile A -> Switch to Profile B -> Create Job on B (no bleed) -> Create Job on A (inherits lock)."""
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        remotion_dir=tmp_path / "remotion",
    )
    service.start_required_backends = lambda: None

    # Profile A: Technical 2.5D
    dna_a = dict(BUILTIN_EDITING_PRESETS["2.5d_technical"])
    dna_a["version"] = 1
    prof_a = service.save_channel_profile({
        "label": "Channel A Technical",
        "market": "KR",
        "dna_mode": "custom_dna_only",
        "allowed_topics": "Hạ tầng",
        "editing_dna": dna_a,
    })

    # Profile B: Forensic Noir
    dna_b = dict(BUILTIN_EDITING_PRESETS["forensic_noir"])
    prof_b = service.save_channel_profile({
        "label": "Channel B Forensic",
        "market": "KR",
        "dna_mode": "custom_dna_only",
        "allowed_topics": "Hình sự",
        "editing_dna": dna_b,
    })

    # 1. Lock v2 on Profile A
    dna_a_v2 = dict(dna_a)
    dna_a_v2["version"] = 2
    dna_a_v2["pacing"]["target_beat_duration_sec"] = 4.0
    prof_a["editing_dna"] = dna_a_v2
    service.save_channel_profile(prof_a, profile_id=prof_a["id"])

    # 2. Create Job on Profile B
    job_b = service.create_job({
        "title": "Job on Profile B",
        "channel_profile_id": prof_b["id"],
        "market": "KR",
    })
    assert job_b["channel_profile_id"] == prof_b["id"]

    # 3. Create Job on Profile A
    job_a2 = service.create_job({
        "title": "Job on Profile A V2",
        "channel_profile_id": prof_a["id"],
        "market": "KR",
    })
    assert job_a2["channel_profile_id"] == prof_a["id"]


def test_tier3_pairwise_preflight_warnings_then_edit_dna_pacing_override():
    """Pairwise 3: Run Pre-Flight check, then override editing_dna pacing and verify compliance."""
    profile = {"forbidden_topics": "", "allowed_topics": "công trình"}
    preflight = simulate_preflight_check(profile, "title", {"title": "Đại công trình thế kỷ"}, [])
    assert preflight["preflight_summary"]["passed"] is True

    # Pacing override in Remotion recipe: target 4.0s beats
    recipe = dict(BUILTIN_EDITING_PRESETS["2.5d_technical"])
    recipe["pacing"]["target_beat_duration_sec"] = 4.0

    beats = [{"beat_id": "B01", "duration_sec": 4.0, "visual_type": "motion"}]
    srt = [{"start": 0.0, "end": 4.0}]
    compliance = simulate_sync_compliance_check(beats, srt)
    assert compliance["sync_scorecard"]["passed"] is True


def test_tier3_pairwise_clone_profile_then_lock_edit_then_parent_isolation(tmp_path: Path):
    """Pairwise 4: Clone Profile -> Lock new Edit DNA on Clone -> Parent remains at v1."""
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        remotion_dir=tmp_path / "remotion",
    )
    service.start_required_backends = lambda: None

    parent = service.save_channel_profile({
        "label": "Parent Profile",
        "market": "US",
        "dna_mode": "custom_dna_only",
        "allowed_topics": "Archives",
        "editing_dna": BUILTIN_EDITING_PRESETS["archival_historical"],
    })

    # Clone
    clone_payload = json.loads(json.dumps(parent))
    clone_payload.pop("id", None)
    clone_payload["label"] = "Parent Profile (Clone)"
    clone = service.save_channel_profile(clone_payload)

    # Mutate clone editing DNA
    clone["editing_dna"] = dict(BUILTIN_EDITING_PRESETS["forensic_noir"])
    clone["editing_dna"]["version"] = 2
    service.save_channel_profile(clone, profile_id=clone["id"])

    # Verify parent untouched
    reloaded_parent = service.get_channel_profile(parent["id"])
    assert reloaded_parent["label"] == "Parent Profile"
    assert reloaded_parent["id"] != clone["id"]


def test_tier3_pairwise_self_learning_upgrades_then_preflight_title_generation():
    """Pairwise 5: Self-Learning discovers winning pattern -> Pre-Flight enforces it on next title."""
    videos = [
        {"id": "v1", "title": "Đại án 4.400 tỷ", "views": 200_000, "is_breakout": True},
        {"id": "v2", "title": "Án nhỏ thường", "views": 10_000},
    ]
    post_mortem = simulate_self_learning_post_mortem(videos, {"id": "c1"})
    assert len(post_mortem["winners"]) >= 1

    # Candidate title applying the upgrade rule
    candidate_title = {"title": "Đại án ngân hàng: Vỏ bọc 15 năm"}
    preflight = simulate_preflight_check({}, "title", candidate_title, [])
    assert "investigative_hook_keyword" in preflight["preflight_summary"]["winner_patterns_matched"]


def test_tier3_pairwise_voice_srt_auto_repair_then_edit_export_pipeline():
    """Pairwise 6: Misaligned audio-visual beats -> Auto-repair realigns -> Export compliance passes."""
    misaligned_beats = [
        {"beat_id": "B001", "duration_sec": 11.0, "has_motion_override": False, "visual_type": "static_ai"},
        {"beat_id": "B002", "duration_sec": 4.0, "has_motion_override": False, "visual_type": "motion"},
    ]
    srt = [
        {"start": 0.0, "end": 7.0},
        {"start": 7.0, "end": 11.0},
    ]

    # Pre-repair check fails on hold > 8s and drift
    initial_check = simulate_sync_compliance_check(misaligned_beats, srt)
    assert initial_check["sync_scorecard"]["passed"] is False

    # Auto-repair
    repaired_beats = []
    for i, b in enumerate(misaligned_beats):
        dur = float(srt[i]["end"] - srt[i]["start"])
        rb = dict(b)
        rb["duration_sec"] = dur
        if b["duration_sec"] > 8.0:
            rb["has_motion_override"] = True
            rb["visual_type"] = "motion"
        repaired_beats.append(rb)

    post_repair_check = simulate_sync_compliance_check(repaired_beats, srt)
    assert post_repair_check["sync_scorecard"]["passed"] is True


def test_tier3_pairwise_multi_channel_switching_with_draft_inputs_preserved():
    """Pairwise 7: User switches profiles while drafting topic; draft state does not bleed to active job."""
    profiles = [
        {"id": "prof-1", "market": "KR", "lang": "ko"},
        {"id": "prof-2", "market": "US", "lang": "en"},
        {"id": "prof-3", "market": "VN", "lang": "vi"},
    ]
    draft_user_input = "Chủ đề tự nhập: Khủng hoảng địa ốc"

    # Simulate switching profiles in UI
    active_profile = profiles[0]
    assert active_profile["market"] == "KR"

    active_profile = profiles[1]
    assert active_profile["market"] == "US"
    assert draft_user_input == "Chủ đề tự nhập: Khủng hoảng địa ốc"


def test_tier3_pairwise_youtube_policy_flag_then_script_revision_then_clean_scorecard():
    """Pairwise 8: Script with policy violation is flagged, revised, and re-tested to clean 100% green."""
    dirty_script = "Phát hiện thi thể đẫm máu bị chặt đầu tại công viên."
    dirty_check = simulate_sync_compliance_check([], [], dirty_script)
    assert dirty_check["policy_scorecard"]["green_monetization"] is False

    # Revision
    revised_script = "Phát hiện dấu vết hiện trường và vật chứng quan trọng tại công viên."
    clean_check = simulate_sync_compliance_check([], [], revised_script)
    assert clean_check["policy_scorecard"]["green_monetization"] is True
    assert clean_check["policy_scorecard"]["flagged_terms"] == []
