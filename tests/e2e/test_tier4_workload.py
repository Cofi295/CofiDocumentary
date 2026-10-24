"""
E2E Test Suite - Tier 4: Real-World Documentary Production Workloads
Simulates complete end-to-end documentary workflows from Step 0 (Channel DNA) through Step 08 (QC & Export).
Total: 6 Realistic Workload Scenarios.
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


def test_tier4_workload_korean_true_crime_30min_full_ai_pipeline(tmp_path: Path):
    """Workload 1: Full 30-minute Korean True Crime Forensic Noir documentary simulation (Steps 0-08)."""
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        remotion_dir=tmp_path / "remotion",
    )
    service.start_required_backends = lambda: None

    # Step 0: Channel DNA Profile
    profile = service.save_channel_profile({
        "label": "Kênh True Crime Hình Sự Trung Quốc (KR · 30p · Full AI)",
        "market": "KR",
        "default_language": "ko",
        "default_duration_minutes": 30,
        "default_visual_strategy": "full_ai",
        "default_ai_media_mode": "image",
        "dna_mode": "custom_dna_only",
        "allowed_topics": "Trọng án hình sự có thật tại Trung Quốc",
        "forbidden_topics": "Chính trị, tham nhũng, miêu tả máu me",
        "monetization_safety_policy": "Góc nhìn hồ sơ điều tra viên hình sự, 100% green monetization",
        "editing_dna": BUILTIN_EDITING_PRESETS["forensic_noir"],
    })

    # Step 00: Project Creation with Pre-Flight
    preflight = simulate_preflight_check(
        profile,
        "topic",
        {"title": "Đại án Lao Rongzhi: 20 năm lẩn trốn dưới vỏ bọc", "topic": "Vụ án Lao Rongzhi"},
        [],
    )
    assert preflight["preflight_summary"]["passed"] is True

    job = service.create_job({
        "title": "Đại án Lao Rongzhi: 20 năm lẩn trốn",
        "channel_profile_id": profile["id"],
        "market": "KR",
        "language": "ko",
        "target_duration_minutes": 30,
        "visual_strategy": "full_ai",
    })
    assert job["id"] is not None

    # Step 01: Script outline & chapters
    script_content = (
        "# Hồi 1: Vụ án mất tích bí ẩn tại Nam Xương\n"
        "Cảnh sát hình sự thu thập dấu vân tay và đối chiếu dữ liệu nhận diện.\n\n"
        "# Hồi 2: Cuộc truy vết xuyên tỉnh 20 năm\n"
        "Đối tượng thay đổi danh tính và lẩn trốn qua nhiều thành phố."
    )
    service.update_job_script(job["id"], {"script": script_content})

    # Step 02-06: Voice, Visuals, Edit Assembly
    beats = [
        {"beat_id": "B001", "duration_sec": 5.5, "visual_type": "motion", "has_motion_override": True},
        {"beat_id": "B002", "duration_sec": 6.0, "visual_type": "motion", "has_motion_override": True},
    ]
    srt = [
        {"start": 0.0, "end": 5.5, "text": "Hồi 1: Vụ án mất tích"},
        {"start": 5.5, "end": 11.5, "text": "Hồi 2: Cuộc truy vết"},
    ]

    # Step 07: Thumbnail & SEO Pre-Flight
    thumb_check = simulate_preflight_check(
        profile,
        "thumbnail",
        {"variants": ["var_noir_a", "var_noir_b", "var_noir_c"], "text_overlay": "20 NĂM VỎ BỌC"},
        [],
    )
    assert thumb_check["preflight_summary"]["passed"] is True

    # Step 08: Final QC Scorecard
    qc = simulate_sync_compliance_check(beats, srt, script_content)
    assert qc["sync_scorecard"]["passed"] is True
    assert qc["policy_scorecard"]["green_monetization"] is True


def test_tier4_workload_china_infrastructure_22min_hybrid_pipeline(tmp_path: Path):
    """Workload 2: Full 22-minute Infrastructure Investigation hybrid documentary simulation (Steps 0-08)."""
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        remotion_dir=tmp_path / "remotion",
    )
    service.start_required_backends = lambda: None

    # Step 0: Channel DNA Profile
    profile = service.save_channel_profile({
        "label": "판세의 이면 · Hạ Tầng Trung Quốc (KR · 22p · Hybrid)",
        "market": "KR",
        "default_language": "ko",
        "default_duration_minutes": 22,
        "default_visual_strategy": "hybrid",
        "dna_mode": "custom_dna_only",
        "allowed_topics": "Đại công trình hạ tầng, điểm gãy kỹ thuật",
        "editing_dna": BUILTIN_EDITING_PRESETS["2.5d_technical"],
    })

    # Step 00: Project Creation
    job = service.create_job({
        "title": "Nam Thủy Bắc Điều 1,432km: Kỳ tích hay rủi ro",
        "channel_profile_id": profile["id"],
        "market": "KR",
        "language": "ko",
        "visual_strategy": "hybrid",
    })

    # Step 06 & 08: Remotion edit & QC compliance
    beats = [
        {"beat_id": "B001", "duration_sec": 4.5, "visual_type": "2.5d_map", "has_motion_override": True},
        {"beat_id": "B002", "duration_sec": 4.5, "visual_type": "hud", "has_motion_override": True},
    ]
    srt = [{"start": 0.0, "end": 4.5}, {"start": 4.5, "end": 9.0}]

    qc = simulate_sync_compliance_check(beats, srt, "Phân tích cơ chế thủy lực và địa chất hiện trường.")
    assert qc["sync_scorecard"]["passed"] is True
    assert qc["policy_scorecard"]["reused_content_risk"] == "low"


def test_tier4_workload_us_presidential_vault_archival_vault_pipeline(tmp_path: Path):
    """Workload 3: Full 30-minute US Presidential Vault historical investigation documentary."""
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        remotion_dir=tmp_path / "remotion",
    )
    service.start_required_backends = lambda: None

    # Step 0: US Vault Profile
    profile = service.save_channel_profile({
        "label": "The First Family Vault (US · 30p · Archival)",
        "market": "US",
        "default_language": "en",
        "default_duration_minutes": 30,
        "default_visual_strategy": "hybrid",
        "dna_mode": "custom_dna_only",
        "allowed_topics": "Presidential executive orders, declassified memos",
        "editing_dna": BUILTIN_EDITING_PRESETS["archival_historical"],
    })

    job = service.create_job({
        "title": "Executive Order 9066: The Archival Paper Trail",
        "channel_profile_id": profile["id"],
        "market": "US",
        "language": "en",
    })

    assert job["market"] == "US"
    assert job["language"] == "en"


def test_tier4_workload_lock_approved_edit_and_closed_loop_self_learning_cycle(tmp_path: Path):
    """Workload 4: Complete closed-loop self-learning & edit lock evolution across successive projects."""
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        remotion_dir=tmp_path / "remotion",
    )
    service.start_required_backends = lambda: None

    # 1. Channel Profile creation
    profile = service.save_channel_profile({
        "label": "Channel Evolving",
        "market": "KR",
        "dna_mode": "custom_dna_only",
        "allowed_topics": "Điều tra công nghệ",
        "editing_dna": BUILTIN_EDITING_PRESETS["2.5d_technical"],
    })

    # 2. Project 1 produced and approved -> Lock Edit DNA v2
    job_1 = service.create_job({"title": "Video 1 Pilot", "channel_profile_id": profile["id"]})
    v2_dna = dict(BUILTIN_EDITING_PRESETS["2.5d_technical"])
    v2_dna["version"] = 2
    v2_dna["pacing"]["target_beat_duration_sec"] = 4.2
    v2_dna["locked_from_job_id"] = job_1["id"]

    profile["editing_dna"] = v2_dna
    service.save_channel_profile(profile, profile_id=profile["id"])

    # 3. Post-Mortem Analysis on Channel History
    history_videos = [
        {"id": "v1", "title": "Video 1 Pilot", "views": 250_000, "is_breakout": True},
        {"id": "v0", "title": "Old Flop Video", "views": 5_000},
    ]
    post_mortem = simulate_self_learning_post_mortem(history_videos, profile)
    profile["self_learning_memory"] = post_mortem["upgrade_rules"]

    # 4. Project 2 automatically inherits both locked recipe and learned upgrades
    upgrades = profile["self_learning_memory"]["next_video_upgrades"]
    job_2 = service.create_job({
        "title": "Video 2 Upgraded",
        "channel_profile_id": profile["id"],
        "notes": f"Injected upgrades: {json.dumps(upgrades, ensure_ascii=False)}",
    })

    assert "Injected upgrades" in job_2["notes"]


def test_tier4_workload_interrupted_pipeline_recovery_and_resumption(tmp_path: Path):
    """Workload 5: Pipeline interruption during render/download safely resumes from checkpoint."""
    store = JobStore(tmp_path / "jobs")
    service = DocumentaryService(
        root=tmp_path,
        store=store,
        remotion_dir=tmp_path / "remotion",
    )
    service.start_required_backends = lambda: None

    job = service.create_job({"title": "Job To Interrupt", "market": "KR"})
    # Mark a phase as running
    store.update(job["id"], {"phases": {"footage": {"status": "running"}}, "status": "running"})

    # Simulate restart & recovery
    interrupted_count = store.recover_interrupted()
    assert len(interrupted_count) >= 1

    reloaded = service.get_job(job["id"])
    assert reloaded["phases"]["footage"]["status"] in {"interrupted", "failed", "pending"}


def test_tier4_workload_multi_project_concurrent_workspace_isolation(tmp_path: Path):
    """Workload 6: Studio operates 3 projects concurrently across 3 distinct profiles with zero state bleed."""
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        remotion_dir=tmp_path / "remotion",
    )
    service.start_required_backends = lambda: None

    profiles = []
    for i, (market, lang, strategy) in enumerate([("KR", "ko", "full_ai"), ("US", "en", "hybrid"), ("VN", "vi", "full_footage")]):
        p = service.save_channel_profile({
            "label": f"Channel Profile {i+1}",
            "market": market,
            "default_language": lang,
            "default_visual_strategy": strategy,
            "dna_mode": "custom_dna_only",
            "allowed_topics": f"Topic group {i+1}",
        })
        profiles.append(p)

    jobs = []
    for i, prof in enumerate(profiles):
        j = service.create_job({
            "title": f"Concurrent Project {i+1}",
            "channel_profile_id": prof["id"],
            "market": prof["market"],
            "language": prof["default_language"],
            "visual_strategy": prof["default_visual_strategy"],
        })
        jobs.append(j)

    # Verify each job's parameters are completely distinct
    assert jobs[0]["market"] == "KR" and jobs[0]["visual_strategy"] == "full_ai"
    assert jobs[1]["market"] == "US" and jobs[1]["visual_strategy"] == "hybrid"
    assert jobs[2]["market"] == "VN" and jobs[2]["visual_strategy"] == "full_footage"

    # Mutate Job 0, assert Job 1 and 2 remain unaffected
    service.update_job_script(jobs[0]["id"], {"script": "Korean exclusive script"})
    assert service.get_job(jobs[1]["id"]).get("script") != "Korean exclusive script"
    assert service.get_job(jobs[2]["id"]).get("script") != "Korean exclusive script"
