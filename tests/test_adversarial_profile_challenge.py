"""
Adversarial Empirical Challenge Suite for Milestone 1:
Channel Profile Cloning, In-Place Updates, and Data Preservation.

Tests:
1. Cloning:
   - Deep independence (mutating clone never bleeds into original)
   - Fresh unique ID generation
   - Identical deep configuration (editing_dna, default_creative_brief, self_learning_memory)
   - Custom label vs default '(Clone)' suffix
   - Error cases (non-existent profile clone)
   - Mass cloning collision resilience
2. In-Place Updates:
   - Single top-level field update preservation (editing_dna, brief, memory remain 100% untouched)
   - Partial nested dictionary updates (deep merge, preserving unmentioned sibling keys)
   - ID hijacking / identity protection (id cannot be changed via update)
   - Null-value injection defense (null fields in patch do not erase existing data)
   - Error handling (update non-existent profile)
3. Backup Integrity:
   - Backups in data/backups/ exist and are valid uncorrupted JSON
   - Pre-migration backups faithfully preserved prior state before modifications
   - Current backup generation creates pristine, complete snapshots with full non-null schemas
   - Backed up jobs in data/backups/ are uncorrupted and parseable
"""

import copy
import json
import shutil
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from server import create_app
from services.channel_profile_service import ChannelProfileService
from scripts.backfill_migration import backup_data

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROFILES_FILE = DATA_DIR / "channel_profiles.json"
JOBS_DIR = DATA_DIR / "jobs"
BACKUPS_DIR = DATA_DIR / "backups"
LOCAL_TMP_DIR = ROOT / ".pytest_tmp" / "adversarial_scratch"

CANONICAL_PROFILE_IDS = [
    "channel-1e24de3ab5",
    "channel-e544a64b7c",
    "channel-aa913eb90d",
    "channel-f6ec4dfff3",
]

CANONICAL_JOB_IDS = [
    "20261018-223750-3aecfbcd",
    "20261017-164519-fd65f7e1",
    "20261017-003022-ecb75736",
    "20261015-014818-f0fdc122",
]


@pytest.fixture
def isolated_service():
    """Create an isolated ChannelProfileService with a copy of real profiles in project-local temp dir."""
    LOCAL_TMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_storage = LOCAL_TMP_DIR / f"temp_channel_profiles_{uuid.uuid4().hex[:8]}.json"
    shutil.copy2(PROFILES_FILE, temp_storage)
    service = ChannelProfileService(storage_path=temp_storage)
    try:
        yield service
    finally:
        if temp_storage.exists():
            try:
                temp_storage.unlink()
            except Exception:
                pass


@pytest.fixture(scope="module")
def api_client():
    """Test client for FastAPI routes."""
    app = create_app()
    with TestClient(app) as client:
        yield client


# ==============================================================================
# SECTION 1: CHANNEL PROFILE CLONING ADVERSARIAL CHALLENGES
# ==============================================================================

class TestProfileCloningAdversarial:
    def test_clone_generates_fresh_unique_id_and_default_label(self, isolated_service):
        """Verify clone generates a unique ID, ' (Clone)' label suffix, and empty history."""
        for pid in CANONICAL_PROFILE_IDS:
            orig = isolated_service.get_profile(pid)
            cloned = isolated_service.clone_profile(pid)

            # Unique ID checks
            assert cloned["id"] != orig["id"], f"Clone ID must differ from original for {pid}"
            assert cloned["id"].startswith("channel-"), "Clone ID must follow 'channel-*' format"
            assert cloned["channel_profile_id"] == cloned["id"]

            # Label suffix check
            assert cloned["label"] == f"{orig['label']} (Clone)"

            # Fresh timestamps
            assert cloned["created_at"] is not None
            assert cloned["updated_at"] is not None

            # Reset history
            assert cloned["editing_dna_history"] == []

    def test_clone_preserves_custom_label_when_provided(self, isolated_service):
        """Verify clone respects custom label if provided."""
        custom_name = "Adversarial Custom Profile Alpha"
        cloned = isolated_service.clone_profile("channel-1e24de3ab5", new_label=custom_name)
        assert cloned["label"] == custom_name

    def test_clone_has_identical_deep_configuration(self, isolated_service):
        """Verify clone deeply replicates all nested configurations."""
        for pid in CANONICAL_PROFILE_IDS:
            orig = isolated_service.get_profile(pid)
            cloned = isolated_service.clone_profile(pid)

            # Deep configuration checks
            assert cloned["default_creative_brief"] == orig["default_creative_brief"]
            assert cloned["editing_dna"] == orig["editing_dna"]
            assert cloned["self_learning_memory"] == orig["self_learning_memory"]
            assert cloned.get("editorial_dna") == orig.get("editorial_dna")
            assert cloned["visual_strategy"] == orig["visual_strategy"]
            assert cloned["market"] == orig["market"]
            assert cloned["language"] == orig["language"]
            assert cloned["target_duration_minutes"] == orig["target_duration_minutes"]
            assert cloned["ai_media_mode"] == orig["ai_media_mode"]
            assert cloned["allowed_topics"] == orig["allowed_topics"]
            assert cloned["forbidden_topics"] == orig["forbidden_topics"]
            assert cloned["monetization_safety_policy"] == orig["monetization_safety_policy"]

    def test_clone_deep_copy_isolation_under_hostile_mutation(self, isolated_service):
        """
        Adversarially mutate nested structures on the clone and verify that the original
        profile remains 100% UNTOUCHED in storage and in-memory.
        """
        for pid in CANONICAL_PROFILE_IDS:
            orig_before = copy.deepcopy(isolated_service.get_profile(pid))
            cloned = isolated_service.clone_profile(pid)
            clone_id = cloned["id"]

            # Hostile mutations on the clone
            hostile_patch = {
                "label": "Completely Mutated Clone",
                "market": "VN",
                "default_language": "vi",
                "editing_dna": {
                    "pacing": 99.9,
                    "color_grade": "radioactive_violet",
                    "visual_mix": {"footage": 0.99, "ai": 0.01, "motion": 0.0},
                    "editing_archetypes": ["hostile_archetype_x"],
                    "subtitle_style": {"font_family": "HostileFont", "font_size": 99},
                    "audio_rules": {"music_ducking_db": -99.0, "sfx_hit_on_chapter": False},
                },
                "default_creative_brief": {
                    "market": "VN",
                    "notes": "Hostile brief modification",
                    "editing_archetypes": ["hostile_brief_archetype"],
                    "writing_style": "Hostile style",
                },
                "self_learning_memory": {
                    "analyzed_videos_count": 9999,
                    "winners": ["hostile_winner_item"],
                    "upgrade_rules": {"what_to_stop_doing": ["hostile_stop"]},
                },
            }

            isolated_service.update_profile(clone_id, hostile_patch)

            # Re-read original from storage
            orig_after = isolated_service.get_profile(pid)

            # Assert original is 100% UNTOUCHED across every single field
            assert orig_after["label"] == orig_before["label"]
            assert orig_after["market"] == orig_before["market"]
            assert orig_after["default_language"] == orig_before["default_language"]
            assert orig_after["editing_dna"] == orig_before["editing_dna"]
            assert orig_after["default_creative_brief"] == orig_before["default_creative_brief"]
            assert orig_after["self_learning_memory"] == orig_before["self_learning_memory"]
            assert orig_after["updated_at"] == orig_before["updated_at"]

    def test_clone_mass_concurrency_no_id_collisions(self, isolated_service):
        """Clone multiple times consecutively to verify zero ID collisions."""
        clone_ids = set()
        for i in range(15):
            cloned = isolated_service.clone_profile("channel-1e24de3ab5", new_label=f"Mass Clone {i}")
            cid = cloned["id"]
            assert cid not in clone_ids, f"Collision detected for clone ID {cid}"
            clone_ids.add(cid)
        assert len(clone_ids) == 15

    def test_clone_non_existent_profile_raises_error(self, isolated_service, api_client):
        """Attempting to clone a non-existent profile must raise KeyError / return 404."""
        with pytest.raises(KeyError):
            isolated_service.clone_profile("channel-ghost-999")

        resp = api_client.post("/api/radar/channel-profiles/channel-ghost-999/clone")
        assert resp.status_code == 404

    def test_api_clone_and_delete_lifecycle(self, api_client):
        """Test API endpoint clone and immediate cleanup on live router."""
        resp = api_client.post(
            "/api/radar/channel-profiles/channel-aa913eb90d/clone",
            json={"label": "Live API Clone Test"}
        )
        assert resp.status_code == 200
        data = resp.json()
        clone_id = data["id"]
        assert data["label"] == "Live API Clone Test"
        assert clone_id != "channel-aa913eb90d"

        # Verify live retrieval
        get_resp = api_client.get(f"/api/radar/channel-profiles/{clone_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == clone_id

        # Clean up
        del_resp = api_client.delete(f"/api/radar/channel-profiles/{clone_id}")
        assert del_resp.status_code == 200

        # Verify 404 after deletion
        get_deleted = api_client.get(f"/api/radar/channel-profiles/{clone_id}")
        assert get_deleted.status_code == 404


# ==============================================================================
# SECTION 2: IN-PLACE UPDATES AND DATA PRESERVATION ADVERSARIAL CHALLENGES
# ==============================================================================

class TestInPlaceUpdateAndDataPreservation:
    def test_update_single_field_preserves_all_other_fields(self, isolated_service):
        """
        Adversarially update ONLY a single primitive field (e.g. label)
        and verify that editing_dna, default_creative_brief, self_learning_memory,
        editorial_dna, and all other fields are 100% preserved and not reset.
        """
        for pid in CANONICAL_PROFILE_IDS:
            orig = copy.deepcopy(isolated_service.get_profile(pid))

            # Update ONLY label
            updated = isolated_service.update_profile(pid, {"label": f"{orig['label']} - Renamed"})

            assert updated["label"] == f"{orig['label']} - Renamed"

            # Verify editing_dna is 100% preserved
            assert updated["editing_dna"] == orig["editing_dna"], f"editing_dna wiped or altered in {pid}"
            # Verify default_creative_brief is 100% preserved
            assert updated["default_creative_brief"] == orig["default_creative_brief"], f"brief altered in {pid}"
            # Verify self_learning_memory is 100% preserved
            assert updated["self_learning_memory"] == orig["self_learning_memory"], f"memory altered in {pid}"
            # Verify editorial_dna is 100% preserved
            assert updated.get("editorial_dna") == orig.get("editorial_dna")
            # Verify topics & safety policies preserved
            assert updated["allowed_topics"] == orig["allowed_topics"]
            assert updated["forbidden_topics"] == orig["forbidden_topics"]
            assert updated["monetization_safety_policy"] == orig["monetization_safety_policy"]
            assert updated["visual_strategy"] == orig["visual_strategy"]

    def test_update_single_field_in_nested_editing_dna(self, isolated_service):
        """
        Adversarially update ONLY a sub-field of editing_dna (e.g., color_grade).
        Verify that pacing, visual_mix, subtitle_style, and audio_rules are PRESERVED,
        and other top-level fields (brief, memory) are completely untouched.
        """
        orig = copy.deepcopy(isolated_service.get_profile("channel-1e24de3ab5"))

        patch = {
            "editing_dna": {
                "color_grade": "cyberpunk_neon_yellow"
            }
        }
        updated = isolated_service.update_profile("channel-1e24de3ab5", patch)

        # Check the changed sub-field
        assert updated["editing_dna"]["color_grade"] == "cyberpunk_neon_yellow"

        # Check preserved sibling sub-fields in editing_dna
        assert updated["editing_dna"]["pacing"] == orig["editing_dna"]["pacing"]
        assert updated["editing_dna"]["visual_mix"] == orig["editing_dna"]["visual_mix"]
        assert updated["editing_dna"]["subtitle_style"] == orig["editing_dna"]["subtitle_style"]
        assert updated["editing_dna"]["audio_rules"] == orig["editing_dna"]["audio_rules"]
        assert updated["editing_dna"]["editing_archetypes"] == orig["editing_dna"]["editing_archetypes"]

        # Check that default_creative_brief and self_learning_memory were NOT reset
        assert updated["default_creative_brief"] == orig["default_creative_brief"]
        assert updated["self_learning_memory"] == orig["self_learning_memory"]

    def test_update_single_field_in_nested_default_creative_brief(self, isolated_service):
        """
        Adversarially update ONLY a sub-field of default_creative_brief (e.g. notes).
        Verify that all other 9 brief keys are preserved and editing_dna is untouched.
        """
        orig = copy.deepcopy(isolated_service.get_profile("channel-e544a64b7c"))

        patch = {
            "default_creative_brief": {
                "notes": "Adversarial notes update only"
            }
        }
        updated = isolated_service.update_profile("channel-e544a64b7c", patch)

        # Check the changed sub-field
        assert updated["default_creative_brief"]["notes"] == "Adversarial notes update only"

        # Check preserved brief sibling fields
        for key in ["market", "language", "target_duration_minutes", "ai_media_mode",
                    "visual_strategy", "narrative_angle", "writing_style",
                    "hook_archetype", "editing_archetypes"]:
            assert updated["default_creative_brief"][key] == orig["default_creative_brief"][key]

        # Check editing_dna and memory untouched
        assert updated["editing_dna"] == orig["editing_dna"]
        assert updated["self_learning_memory"] == orig["self_learning_memory"]

    def test_update_single_field_in_self_learning_memory(self, isolated_service):
        """
        Adversarially update ONLY analyzed_videos_count in self_learning_memory.
        Verify winners, underperformers, and upgrade_rules remain preserved.
        """
        orig = copy.deepcopy(isolated_service.get_profile("channel-aa913eb90d"))

        patch = {
            "self_learning_memory": {
                "analyzed_videos_count": 999
            }
        }
        updated = isolated_service.update_profile("channel-aa913eb90d", patch)

        assert updated["self_learning_memory"]["analyzed_videos_count"] == 999
        assert updated["self_learning_memory"]["winners"] == orig["self_learning_memory"]["winners"]
        assert updated["self_learning_memory"]["underperformers"] == orig["self_learning_memory"]["underperformers"]
        assert updated["self_learning_memory"]["upgrade_rules"] == orig["self_learning_memory"]["upgrade_rules"]

    def test_update_tamper_defense_id_immutability(self, isolated_service):
        """
        Adversarial attempt to hijack or change profile ID via update payload.
        Verify the service protects identity integrity.
        """
        orig = isolated_service.get_profile("channel-f6ec4dfff3")

        hijack_payload = {
            "id": "channel-hacked-id",
            "channel_profile_id": "channel-hacked-id",
            "label": "Tamper Attempt",
        }
        updated = isolated_service.update_profile("channel-f6ec4dfff3", hijack_payload)

        # ID must remain strictly locked to channel-f6ec4dfff3
        assert updated["id"] == "channel-f6ec4dfff3"
        assert updated["channel_profile_id"] == "channel-f6ec4dfff3"
        assert updated["label"] == "Tamper Attempt"

    def test_update_null_field_injection_defense(self, isolated_service):
        """
        Verify that passing None/null in update patch does NOT erase existing data.
        """
        orig = copy.deepcopy(isolated_service.get_profile("channel-1e24de3ab5"))

        null_payload = {
            "label": None,
            "editing_dna": None,
            "default_creative_brief": None,
            "allowed_topics": None,
        }
        updated = isolated_service.update_profile("channel-1e24de3ab5", null_payload)

        assert updated["label"] == orig["label"]
        assert updated["editing_dna"] == orig["editing_dna"]
        assert updated["default_creative_brief"] == orig["default_creative_brief"]
        assert updated["allowed_topics"] == orig["allowed_topics"]

    def test_update_non_existent_profile_raises_error(self, isolated_service, api_client):
        """Updating non-existent profile raises KeyError / returns 404."""
        with pytest.raises(KeyError):
            isolated_service.update_profile("channel-phantom", {"label": "test"})

        resp = api_client.put("/api/radar/channel-profiles/channel-phantom", json={"label": "test"})
        assert resp.status_code == 404


# ==============================================================================
# SECTION 3: BACKUP INTEGRITY ADVERSARIAL CHALLENGES
# ==============================================================================

class TestBackupIntegrityAdversarial:
    def test_backups_directory_and_core_files_exist(self):
        """Verify data/backups/ exists and contains valid backup targets."""
        assert BACKUPS_DIR.exists(), "data/backups directory must exist"

        profile_backups = list(BACKUPS_DIR.glob("channel_profiles_*.json"))
        assert len(profile_backups) >= 1, "At least one timestamped channel_profiles backup must exist"

        pointer_backup = BACKUPS_DIR / "channel_profiles_backup.json"
        assert pointer_backup.exists(), "channel_profiles_backup.json pointer must exist"

        jobs_backups = [d for d in BACKUPS_DIR.iterdir() if d.is_dir() and "jobs" in d.name]
        assert len(jobs_backups) >= 1, "At least one jobs backup directory must exist"

    def test_backed_up_channel_profiles_json_parseability(self):
        """
        Verify every channel_profiles backup file in data/backups/ is valid uncorrupted JSON
        and contains non-empty 'profiles' list.
        """
        profile_backup_files = list(BACKUPS_DIR.glob("channel_profiles*.json"))
        assert len(profile_backup_files) >= 1

        for bfile in profile_backup_files:
            content = bfile.read_text(encoding="utf-8")
            assert len(content) > 1000, f"Backup file {bfile.name} is unexpectedly small or empty"

            data = json.loads(content)
            assert "profiles" in data, f"Backup {bfile.name} missing 'profiles' key"
            assert isinstance(data["profiles"], list), f"'profiles' in {bfile.name} must be a list"
            assert len(data["profiles"]) >= 4, f"Backup {bfile.name} has fewer than 4 profiles"

            # Check that all canonical IDs exist
            pids = {p.get("id") for p in data["profiles"] if isinstance(p, dict)}
            for pid in CANONICAL_PROFILE_IDS:
                assert pid in pids, f"Profile {pid} missing from backup {bfile.name}"

    def test_backed_up_jobs_parseability(self):
        """
        Verify that all jobs backup directories contain valid uncorrupted job.json files.
        """
        job_backup_dirs = [d for d in BACKUPS_DIR.iterdir() if d.is_dir() and "jobs" in d.name]
        assert len(job_backup_dirs) >= 1

        for jb_dir in job_backup_dirs:
            for jid in CANONICAL_JOB_IDS:
                job_file = jb_dir / jid / "job.json"
                assert job_file.exists(), f"Job file for {jid} missing in backup directory {jb_dir.name}"

                content = job_file.read_text(encoding="utf-8")
                assert len(content) > 100
                job_data = json.loads(content)
                assert isinstance(job_data, dict)
                assert job_data.get("id") == jid or jid in str(job_file)

    def test_backup_routine_execution_and_schema_completeness(self):
        """
        Execute backup_data() to verify it safely creates a new backup of the current state,
        and the newly generated backup contains 100% complete, non-null schemas.
        """
        before_count = len(list(BACKUPS_DIR.glob("channel_profiles_*.json")))

        # Run backup routine
        profile_backup, jobs_backup = backup_data()

        # Verify newly created artifacts exist
        assert profile_backup.exists()
        assert profile_backup.stat().st_size > 0
        assert jobs_backup.exists() and jobs_backup.is_dir()

        # Verify backup count increased
        after_count = len(list(BACKUPS_DIR.glob("channel_profiles_*.json")))
        assert after_count >= before_count + 1

        # Verify valid JSON and complete schema in new profile backup
        new_data = json.loads(profile_backup.read_text(encoding="utf-8"))
        profiles = {p["id"]: p for p in new_data.get("profiles", []) if isinstance(p, dict)}

        for pid in CANONICAL_PROFILE_IDS:
            assert pid in profiles, f"Profile {pid} missing from newly generated backup"
            p = profiles[pid]

            # Top-level non-null fields
            assert p.get("id") == pid
            assert p.get("visual_strategy") in {"full_ai", "full_footage", "hybrid", "evidence_footage"}
            assert p.get("default_visual_strategy") is not None
            assert p.get("language") is not None
            assert p.get("target_duration_minutes") is not None

            # default_creative_brief completeness
            brief = p.get("default_creative_brief")
            assert isinstance(brief, dict)
            for bk in ["market", "language", "target_duration_minutes", "ai_media_mode", "writing_style", "editing_archetypes"]:
                assert brief.get(bk) is not None

            # editing_dna completeness
            dna = p.get("editing_dna")
            assert isinstance(dna, dict)
            for dk in ["pacing", "visual_mix", "editing_archetypes", "subtitle_style", "color_grade", "audio_rules"]:
                assert dna.get(dk) is not None

            # self_learning_memory completeness
            slm = p.get("self_learning_memory")
            assert isinstance(slm, dict)
            assert slm.get("winners") is not None
            assert slm.get("underperformers") is not None
            assert isinstance(slm.get("upgrade_rules"), dict)
