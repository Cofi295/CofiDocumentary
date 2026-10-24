"""
Independent Adversarial Verification Test Suite by Victory Auditor.
Tests AC1-AC4 directly without relying on pre-existing test files.
"""

import sys
import io
from pathlib import Path
ROOT = Path("B:/ALL_TOOLS/CofiDocumentary").resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import copy
import json
import shutil
import tempfile

from services.channel_profile_service import ChannelProfileService
from services.job_service import JobService
from services.editing_dna_service import EditingDnaService
from services.sync_policy_service import SyncPolicyService
from services.preflight_service import PreflightService
from services.self_learning_service import SelfLearningService

def run_adversarial_tests():
    print("=" * 70)
    print("RUNNING INDEPENDENT ADVERSARIAL VERIFICATION TESTS")
    print("=" * 70)

    temp_dir = Path(tempfile.mkdtemp(prefix="victory_audit_"))
    try:
        profiles_file = temp_dir / "channel_profiles.json"
        jobs_dir = temp_dir / "jobs"
        workspaces_dir = temp_dir / "workspaces"
        jobs_dir.mkdir(parents=True)
        workspaces_dir.mkdir(parents=True)

        profile_service = ChannelProfileService(storage_path=profiles_file)
        job_service = JobService(profile_service=profile_service)
        # Mock JobStore pointing to temp jobs_dir
        from documentary.store import JobStore
        job_service.store = JobStore(jobs_dir)

        # -------------------------------------------------------------
        # TEST 1: Profile CRUD, Cloning, and Strict Mutation Isolation
        # -------------------------------------------------------------
        p1 = profile_service.create_profile({
            "id": "channel-p1",
            "label": "Profile One Korea",
            "market": "KR",
            "default_language": "ko",
            "target_duration_minutes": 25,
            "visual_strategy": "hybrid",
            "ai_media_mode": "image",
            "voice_and_structure": "Cold Investigative",
            "allowed_topics": "Infrastructure, Megaprojects",
            "forbidden_topics": "Sensational rumors",
            "editing_dna": {"pacing": 4.5, "version": 1}
        })
        assert p1["id"] == "channel-p1"
        assert p1["visual_strategy"] == "hybrid"

        p2 = profile_service.create_profile({
            "id": "channel-p2",
            "label": "Profile Two US",
            "market": "US",
            "default_language": "en",
            "target_duration_minutes": 15,
            "visual_strategy": "full_ai",
            "ai_media_mode": "video",
            "voice_and_structure": "Historical Archival",
            "allowed_topics": "Declassified Vault",
            "forbidden_topics": "Partisan politics",
            "editing_dna": {"pacing": 6.0, "version": 1}
        })
        assert p2["id"] == "channel-p2"

        # Clone p1
        cloned = profile_service.clone_profile("channel-p1", new_label="Cloned Profile")
        assert cloned["id"] != p1["id"]
        assert cloned["label"] == "Cloned Profile"
        assert cloned["editing_dna"]["pacing"] == 4.5

        # Modify clone, verify p1 unchanged
        profile_service.update_profile(cloned["id"], {"label": "Updated Cloned Label", "market": "JP"})
        p1_fresh = profile_service.get_profile("channel-p1")
        assert p1_fresh["label"] == "Profile One Korea"
        assert p1_fresh["market"] == "KR"
        print("PASS: Test 1 - Profile CRUD, Cloning, and State Isolation")

        # -------------------------------------------------------------
        # TEST 2: Job Creation from Profile & Draft Isolation
        # -------------------------------------------------------------
        j1 = job_service.create_job({
            "channel_profile_id": "channel-p1",
            "title": "Dam Failure Investigation"
        })
        assert j1["channel_profile_id"] == "channel-p1"
        assert j1["visual_strategy"] == "hybrid"
        assert j1["editing_dna"]["pacing"] == 4.5
        assert "channel_profile_snapshot" in j1

        # Attempt illegal cross-job mutation
        try:
            job_service.update_job(j1["id"], {"job_id": "different-job-id", "title": "Hacked"})
            assert False, "Should have rejected cross-job mutation"
        except ValueError as e:
            assert "Cross-job mutation rejected" in str(e)

        # Attempt draft mutation side-effect
        try:
            job_service.update_job(j1["id"], {"is_draft": True, "title": "Draft Pollution"})
            assert False, "Should have rejected draft mutation"
        except ValueError as e:
            assert "Draft mutation side-effects rejected" in str(e)
        print("PASS: Test 2 - Job Creation from Profile & Draft Isolation")

        # -------------------------------------------------------------
        # TEST 3: Lock Approved Edit Style to Channel Profile
        # -------------------------------------------------------------
        ws_j1 = workspaces_dir / j1["id"]
        ws_j1.mkdir(parents=True)

        # Write visual manifest with 6 footage, 3 AI, 1 motion
        beats_manifest = {
            "beats": [
                {"beat_id": "b01", "visual_type": "sourced_footage", "duration_sec": 4.0},
                {"beat_id": "b02", "visual_type": "sourced_footage", "duration_sec": 5.0},
                {"beat_id": "b03", "visual_type": "sourced_footage", "duration_sec": 4.5},
                {"beat_id": "b04", "visual_type": "sourced_footage", "duration_sec": 5.0},
                {"beat_id": "b05", "visual_type": "sourced_footage", "duration_sec": 4.0},
                {"beat_id": "b06", "visual_type": "sourced_footage", "duration_sec": 4.5},
                {"beat_id": "b07", "visual_type": "ai_visual", "duration_sec": 4.0},
                {"beat_id": "b08", "visual_type": "ai_visual", "duration_sec": 4.0},
                {"beat_id": "b09", "visual_type": "ai_visual", "duration_sec": 5.0},
                {"beat_id": "b10", "visual_type": "motion_hud", "duration_sec": 4.0},
            ]
        }
        (ws_j1 / "visual_manifest.json").write_text(json.dumps(beats_manifest), encoding="utf-8")

        editing_dna_service = EditingDnaService(
            profiles_file=profiles_file,
            jobs_dir=jobs_dir,
            workspaces_dir=workspaces_dir
        )

        extracted = editing_dna_service.extract_editing_dna_from_job(j1["id"])
        assert extracted["visual_mix"]["footage"] == 0.6
        assert extracted["visual_mix"]["ai"] == 0.3
        assert extracted["visual_mix"]["motion"] == 0.1

        lock_result = editing_dna_service.lock_job_edit_dna_to_channel(j1["id"], notes="Approved by victory auditor")
        assert lock_result["status"] == "success"
        assert lock_result["version"] == 2
        assert lock_result["history_count"] == 1

        # Verify parent profile updated
        p1_locked = profile_service.get_profile("channel-p1")
        assert p1_locked["editing_dna"]["version"] == 2
        assert p1_locked["editing_dna"]["locked_from_job_id"] == j1["id"]
        assert len(p1_locked["editing_dna_history"]) == 1

        # Verify new job created under channel-p1 inherits version 2
        j2 = job_service.create_job({
            "channel_profile_id": "channel-p1",
            "title": "Subsequent Project inheriting DNA"
        })
        assert j2["editing_dna"]["version"] == 2
        assert j2["editing_dna"]["visual_mix"]["footage"] == 0.6
        print("PASS: Test 3 - Lock Approved Edit Style to Channel Profile & Inheritance")

        # -------------------------------------------------------------
        # TEST 4: Voice-Visual Sync Auto-Repair & YouTube Guardrails
        # -------------------------------------------------------------
        sync_policy_service = SyncPolicyService(
            workspaces_dir=workspaces_dir,
            jobs_dir=jobs_dir
        )

        # Unaligned beats with hold > 8s and prohibited term
        unaligned_beats = [
            {"beat_id": "b1", "duration_sec": 9.5, "visual_type": "still_frame"},
            {"beat_id": "b2", "duration_sec": 3.0, "visual_type": "still_frame"},
        ]
        srt_segments = [
            {"start": 0.0, "end": 9.5, "text": "Narrating segment 1"},
            {"start": 9.5, "end": 14.0, "text": "Narrating segment 2"},  # Drift: 14-9.5 = 4.5s vs 3.0s
        ]
        bad_script = "Phóng sự này chứa bạo lực cực đoan và phanh thây kinh hoàng."

        compliance_before = sync_policy_service.check_sync_compliance(
            beats=unaligned_beats,
            srt_segments=srt_segments,
            script_text=bad_script
        )
        assert compliance_before["sync_scorecard"]["passed"] is False
        assert len(compliance_before["sync_scorecard"]["holds_over_8s"]) == 1
        assert len(compliance_before["sync_scorecard"]["misaligned_beats"]) == 1
        assert compliance_before["policy_scorecard"]["green_monetization"] is False
        assert "bạo lực cực đoan" in compliance_before["policy_scorecard"]["flagged_terms"]

        # Test auto-repair on j1
        (ws_j1 / "visual_manifest.json").write_text(json.dumps({
            "beats": [
                {"beat_id": "b1", "duration_sec": 10.0, "has_motion_override": False},
                {"beat_id": "b2", "duration_sec": 2.0, "has_motion_override": False},
            ]
        }), encoding="utf-8")
        (ws_j1 / "voice_manifest.json").write_text(json.dumps({
            "beats": [
                {"start_sec": 0.0, "end_sec": 10.0, "text": "Segment 1"},
                {"start_sec": 10.0, "end_sec": 15.0, "text": "Segment 2"},
            ]
        }), encoding="utf-8")

        repair_result = sync_policy_service.auto_repair_sync(j1["id"])
        assert repair_result["status"] == "success"
        assert repair_result["repaired_holds_count"] == 1
        assert repair_result["realigned_beats_count"] == 1

        repaired_manifest = json.loads((ws_j1 / "visual_manifest.json").read_text(encoding="utf-8"))
        b1_rep = repaired_manifest["beats"][0]
        assert b1_rep["has_motion_override"] is True
        assert b1_rep["telemetry_hud_overlay"] is True
        assert b1_rep["ken_burns_zoom"]["start_scale"] == 1.02
        assert b1_rep["ken_burns_zoom"]["end_scale"] == 1.08
        print("PASS: Test 4 - Voice-Visual Sync Auto-Repair & YouTube Guardrails")

        # -------------------------------------------------------------
        # TEST 5: Pre-Flight Duplicate Check & Self-Learning Engine
        # -------------------------------------------------------------
        preflight_service = PreflightService(
            profiles_file=profiles_file,
            jobs_dir=jobs_dir,
            profile_service=profile_service
        )

        # Check duplicate topic
        check_dup = preflight_service.check(
            profile=p1_fresh,
            stage="title",
            input_data={"title": "Dam Failure Investigation", "topic": "Megaprojects"},
            history_titles=["Dam Failure Investigation", "Earlier Video"]
        )
        assert check_dup["status"] == "warning"
        assert check_dup["preflight_summary"]["duplicate_risk"] is True
        assert check_dup["preflight_summary"]["passed"] is False

        # Check forbidden topic
        check_forbid = preflight_service.check(
            profile=p1_fresh,
            stage="title",
            input_data={"title": "Sensational rumors about government", "topic": "Politics"},
            history_titles=[]
        )
        assert check_forbid["status"] == "warning"
        assert check_forbid["preflight_summary"]["passed"] is False

        # Self-learning engine post-mortem
        self_learning_service = SelfLearningService(
            profiles_file=profiles_file,
            jobs_dir=jobs_dir,
            profile_service=profile_service
        )
        sample_videos = [
            {"id": "v1", "title": "Bóc tách đại án hạ tầng", "views": 100000, "is_breakout": True},
            {"id": "v2", "title": "Khảo sát công trình tiêu chuẩn", "views": 25000},
            {"id": "v3", "title": "Video này có tiêu đề quá dài dòng mơ hồ và không có từ khóa bùng nổ nào cả trên thiết bị di động", "views": 4000},
        ]
        post_mortem = self_learning_service.analyze_post_mortem(sample_videos, p1_fresh)
        assert post_mortem["status"] == "success"
        assert len(post_mortem["winners"]) >= 1
        assert len(post_mortem["underperformers"]) >= 1
        assert "what_to_stop_doing" in post_mortem["upgrade_rules"]
        assert len(post_mortem["upgrade_rules"]["next_video_upgrades"]) > 0
        print("PASS: Test 5 - Pre-Flight Duplicate Check & Self-Learning Engine")

        print("\n" + "=" * 70)
        print("ALL 5 INDEPENDENT ADVERSARIAL VERIFICATION TESTS PASSED UNCONDITIONALLY!")
        print("=" * 70)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    run_adversarial_tests()
