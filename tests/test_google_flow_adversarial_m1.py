import hashlib
import json
import os
import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vendor.media_factory.backend.app.db import Database
from vendor.media_factory.backend.app.main import create_app as create_media_factory_app
from vendor.media_factory.backend.app.providers.google import (
    GoogleFlowAccountManager,
    _calc_dir_size_bytes,
    _evict_profile_cache_subdirs,
    _rmtree_robust,
)
from vendor.media_factory.backend.app.secrets import KeyringSecretStore
import server


def test_adversarial_deletion_with_readonly_deep_hierarchies_and_special_chars(tmp_path):
    """Stress-test account removal when profiles contain deeply nested read-only trees and special filenames."""
    db_path = tmp_path / "adv_del.db"
    db = Database(db_path)
    secret_dir = tmp_path / "adv_secrets"
    secret_store = KeyringSecretStore(storage_dir=secret_dir)
    profile_root = tmp_path / "adv_profiles"
    profile_root.mkdir(parents=True, exist_ok=True)

    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)
    acc = manager.create_account()
    acc_id = acc["id"]

    # Provide a custom profile_dir as well
    custom_dir = tmp_path / "custom_profiles" / f"custom_{acc_id}"
    db.patch_resource("google_flow_account", acc_id, {"profile_dir": str(custom_dir)})
    secret_store.set_google_session(acc_id, {"session": {"access_token": "adv-tok"}, "email": "adv@example.com"})

    std_dir = profile_root / acc_id

    for p_dir in [custom_dir, std_dir]:
        p_dir.mkdir(parents=True, exist_ok=True)
        # Deeply nested directory structure (6 levels deep)
        deep_dir = p_dir / "level1" / "level2 [sub]" / "level3 with spaces" / "level4_!@#" / "level5" / "level6"
        deep_dir.mkdir(parents=True, exist_ok=True)

        # Files: read-only, zero-byte, large, special characters
        f1 = deep_dir / "read_only_special_!@#$.dat"
        f1.write_bytes(b"locked binary content" * 100)
        os.chmod(str(f1), stat.S_IREAD)

        f2 = deep_dir / "zero_byte_readonly.tmp"
        f2.touch()
        os.chmod(str(f2), stat.S_IREAD)

        f_root = p_dir / "root_readonly.lock"
        f_root.write_text("root-lock", encoding="utf-8")
        os.chmod(str(f_root), stat.S_IREAD)

        # Make the directories themselves read-only on Windows
        os.chmod(str(deep_dir), stat.S_IREAD | stat.S_IEXEC)
        os.chmod(str(p_dir), stat.S_IREAD | stat.S_IEXEC)

    assert custom_dir.exists()
    assert std_dir.exists()
    assert secret_store._session_path(acc_id).exists()

    # Adversarial action: remove account
    res = manager.remove(acc_id)
    assert res is True

    # Assert complete cleanup
    assert manager.db.get_resource("google_flow_account", acc_id) is None
    assert not secret_store._session_path(acc_id).exists()
    assert not custom_dir.exists(), "Custom profile directory must be deleted even with read-only tree"
    assert not std_dir.exists(), "Standard profile directory must be deleted even with read-only tree"

    # Idempotency check: calling remove on already-deleted account
    res_second = manager.remove(acc_id)
    assert res_second is False, "Repeated removal must return False gracefully without raising"


def test_adversarial_cache_cleanup_with_unexpected_subdirs_and_corrupt_files(tmp_path):
    """Stress-test cache cleanup with non-standard subdirectories, corrupt cache files, and root noise."""
    db_path = tmp_path / "adv_clean.db"
    db = Database(db_path)
    secret_dir = tmp_path / "adv_secrets_clean"
    secret_store = KeyringSecretStore(storage_dir=secret_dir)
    profile_root = tmp_path / "adv_profiles_clean"
    profile_root.mkdir(parents=True, exist_ok=True)

    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)
    acc = manager.create_account()
    acc_id = acc["id"]
    db.patch_resource("google_flow_account", acc_id, {"status": "ready", "email": "ready@test.com"})
    secret_store.set_google_session(acc_id, {"session": {"tok": 123}})

    p_dir = manager.profile_dir_for_account(acc)
    p_dir.mkdir(parents=True, exist_ok=True)

    # 1. Standard cache subdirectories with read-only nested files
    cache_to_evict = [
        p_dir / "Default" / "Cache" / "Cache_Data",
        p_dir / "Default" / "Code Cache" / "wasm",
        p_dir / "Default" / "GPUCache",
        p_dir / "Default" / "Service Worker" / "CacheStorage",
        p_dir / "ShaderCache",
        p_dir / "BrowserMetrics",
        p_dir / "component_crx_cache",
    ]
    for c_dir in cache_to_evict:
        c_dir.mkdir(parents=True, exist_ok=True)
        dummy = c_dir / "chunk.bin"
        dummy.write_bytes(b"cache-data" * 200)
        os.chmod(str(dummy), stat.S_IREAD)

    # 2. Crashpad is created as a single plain READ-ONLY file instead of a folder
    # On Windows, deleting a read-only file requires resetting S_IWRITE before unlinking.
    crashpad_file = p_dir / "Crashpad"
    crashpad_file.write_text("crashpad-plain-file", encoding="utf-8")
    os.chmod(str(crashpad_file), stat.S_IREAD)

    # 3. Unexpected directories inside profile that MUST NOT be touched
    unexpected_dirs = [
        p_dir / "Default" / "blob_storage",
        p_dir / "Default" / "Extensions" / "cjpalhdlnbpafiamejdnhcphjbkeiagm",
        p_dir / "Default" / "Sync Data",
        p_dir / "CustomExtensionData",
    ]
    for u_dir in unexpected_dirs:
        u_dir.mkdir(parents=True, exist_ok=True)
        (u_dir / "important_data.json").write_text('{"persist": true}', encoding="utf-8")

    # 4. Unexpected files inside profile root and profile_root directory
    unrelated_root_file = profile_root / "unrelated_loose_file.txt"
    unrelated_root_file.write_text("do not delete me", encoding="utf-8")

    profile_note = p_dir / "USER_NOTES.txt"
    profile_note.write_text("My personal notes", encoding="utf-8")

    # Run cache cleanup
    stats = manager.clean_profile_caches()

    assert stats["ok"] is True
    assert stats["status"] == "success"
    assert stats["freed_mb"] > 0

    # Verify evicted
    for c_dir in cache_to_evict:
        assert not c_dir.exists(), f"Cache dir {c_dir} was not evicted"
    
    # EMPIRICAL BUG CHECK: Does Crashpad standalone read-only file get evicted?
    assert not crashpad_file.exists(), (
        "BUG: Standalone cache file with stat.S_IREAD was not removed by _evict_profile_cache_subdirs! "
        "target_sub.unlink() raised PermissionError and was swallowed by except OSError."
    )

    # Verify preserved unexpected content
    for u_dir in unexpected_dirs:
        assert u_dir.is_dir(), f"Unexpected dir {u_dir} was erroneously deleted!"
        assert (u_dir / "important_data.json").read_text(encoding="utf-8") == '{"persist": true}'

    assert profile_note.is_file(), "Profile notes file was erroneously deleted"
    assert unrelated_root_file.is_file(), "Unrelated file in profile_root was erroneously deleted"


def test_adversarial_absolute_protection_of_critical_session_and_credential_files(tmp_path):
    """Stress-test absolute byte-for-byte preservation of cookies, local storage, preferences, and local state."""
    db_path = tmp_path / "adv_prot.db"
    db = Database(db_path)
    secret_dir = tmp_path / "adv_secrets_prot"
    secret_store = KeyringSecretStore(storage_dir=secret_dir)
    profile_root = tmp_path / "adv_profiles_prot"
    profile_root.mkdir(parents=True, exist_ok=True)

    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)
    acc = manager.create_account()
    acc_id = acc["id"]
    db.patch_resource("google_flow_account", acc_id, {"status": "ready", "email": "secure@test.com"})
    secret_store.set_google_session(acc_id, {"session": {"tok": "supersecret"}})

    p_dir = manager.profile_dir_for_account(acc)
    p_dir.mkdir(parents=True, exist_ok=True)

    # Critical files to protect with binary contents
    protected_files = {
        p_dir / "Local State": b'{"os_crypt":{"encrypted_key":"RFBBUEkBAAAA..."}}',
        p_dir / "Default" / "Preferences": b'{"profile":{"name":"Default","avatar_icon":"chrome://..."}}',
        p_dir / "Default" / "Cookies": b"SQLite format 3\x00\x10\x00\x01\x01\x00@  \x00\x00\x00\x01cookie_data",
        p_dir / "Default" / "Network" / "Cookies": b"SQLite format 3\x00\x10\x00\x01\x01\x00@  \x00\x00\x00\x01net_cookie",
        p_dir / "Default" / "Local Storage" / "leveldb" / "000003.log": b"leveldb_log_data_payload_12345",
        p_dir / "Default" / "Local Storage" / "leveldb" / "CURRENT": b"MANIFEST-000002\n",
        p_dir / "Default" / "Session Storage" / "000003.log": b"session_storage_payload_67890",
        p_dir / "Default" / "IndexedDB" / "https_flow.google.com_0.indexeddb.leveldb" / "000003.log": b"idx_payload",
    }

    original_hashes = {}
    for p_path, content in protected_files.items():
        p_path.parent.mkdir(parents=True, exist_ok=True)
        p_path.write_bytes(content)
        original_hashes[p_path] = hashlib.sha256(content).hexdigest()

    # Also add standard cache to clean
    cache_dir = p_dir / "Default" / "Cache" / "Cache_Data"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "cache_001.bin").write_bytes(b"cache" * 500)

    # Run clean_profile_caches 3 times consecutively (idempotence + stress)
    for run_i in range(3):
        stats = manager.clean_profile_caches()
        assert stats["ok"] is True

        # Verify bit-for-bit match on every run
        for p_path, orig_hash in original_hashes.items():
            assert p_path.is_file(), f"Run {run_i}: Protected file missing: {p_path}"
            current_bytes = p_path.read_bytes()
            current_hash = hashlib.sha256(current_bytes).hexdigest()
            assert current_hash == orig_hash, (
                f"Run {run_i}: Protected file corrupted or modified! {p_path}"
            )


def test_adversarial_nonexistent_and_orphan_profiles_and_missing_roots(tmp_path):
    """Stress-test non-existent profile_root, missing profile_dir, and multiple orphan profiles."""
    db_path = tmp_path / "adv_orphan.db"
    db = Database(db_path)
    secret_dir = tmp_path / "adv_orphan_secrets"
    secret_store = KeyringSecretStore(storage_dir=secret_dir)

    # 1. Non-existent profile_root
    nonexistent_root = tmp_path / "does_not_exist_profiles"
    manager = GoogleFlowAccountManager(db, secret_store, profile_root=nonexistent_root)
    # Must not raise FileNotFoundError
    stats = manager.clean_profile_caches()
    assert stats["ok"] is True
    assert stats["cleaned_profiles_count"] == 0

    # 2. Account pointing to non-existent profile_dir
    acc = manager.create_account()
    acc_id = acc["id"]
    ghost_p_dir = tmp_path / "ghost_profile"
    db.patch_resource("google_flow_account", acc_id, {"profile_dir": str(ghost_p_dir)})
    # Clean cache with ghost profile dir
    stats2 = manager.clean_profile_caches()
    assert stats2["ok"] is True

    # 3. Multiple orphan profiles with unicode, spaces, read-only files
    real_root = tmp_path / "real_profiles"
    real_root.mkdir(parents=True, exist_ok=True)
    manager.profile_root = real_root

    orphan_1 = real_root / "orphan_basic"
    orphan_1.mkdir()
    (orphan_1 / "data.txt").write_text("orph1", encoding="utf-8")

    orphan_2 = real_root / "orphan [Hồ Sơ Cũ 2026] #!&"
    orphan_2.mkdir()
    (orphan_2 / "data.txt").write_text("orph2", encoding="utf-8")

    orphan_3_readonly = real_root / "orphan_readonly_tree"
    orphan_3_readonly.mkdir()
    ro_sub = orphan_3_readonly / "sub"
    ro_sub.mkdir()
    ro_f = ro_sub / "locked.bin"
    ro_f.write_bytes(b"locked" * 10)
    os.chmod(str(ro_f), stat.S_IREAD)
    os.chmod(str(ro_sub), stat.S_IREAD | stat.S_IEXEC)
    os.chmod(str(orphan_3_readonly), stat.S_IREAD | stat.S_IEXEC)

    # Orphan secret files: one normal, one READ-ONLY
    orphan_hash_1 = hashlib.sha256(b"unknown_orphan_1").hexdigest()
    enc_1 = secret_dir / f"{orphan_hash_1}.enc"
    enc_1.write_bytes(b"orphan1")

    orphan_hash_2 = hashlib.sha256(b"unknown_orphan_2").hexdigest()
    enc_2 = secret_dir / f"{orphan_hash_2}.enc"
    enc_2.write_bytes(b"orphan2")
    os.chmod(str(enc_2), stat.S_IREAD)

    # Loose file in profile_root (should not be treated as a profile or crash)
    loose_file = real_root / "profile_root_summary.txt"
    loose_file.write_text("summary", encoding="utf-8")

    stats3 = manager.clean_profile_caches()
    assert stats3["ok"] is True
    assert stats3["orphan_profiles_removed"] == 3

    assert not orphan_1.exists()
    assert not orphan_2.exists()
    assert not orphan_3_readonly.exists()
    assert not enc_1.exists(), "Standard orphan session file should be deleted"
    
    # EMPIRICAL BUG CHECK: Does read-only orphan session file get deleted?
    assert not enc_2.exists(), (
        "BUG: Orphan session file with stat.S_IREAD was not removed by clean_profile_caches! "
        "enc_file.unlink() raised PermissionError and was swallowed by except OSError."
    )
    assert stats3["orphan_sessions_removed"] == 2
    assert loose_file.is_file(), "Loose file in profile_root must not be deleted"


def test_adversarial_active_accounts_never_deleted_by_cache_cleaning_or_prune(tmp_path, monkeypatch):
    """Stress-test that active accounts in DB are NEVER deleted by clean_profile_caches or prune_dead_accounts."""
    db_path = tmp_path / "adv_active.db"
    db = Database(db_path)
    secret_dir = tmp_path / "adv_active_secrets"
    secret_store = KeyringSecretStore(storage_dir=secret_dir)
    profile_root = tmp_path / "adv_active_profiles"
    profile_root.mkdir(parents=True, exist_ok=True)

    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)

    # 1. Setup 5 distinct accounts with different statuses
    acc_ready_1 = manager.create_account()
    db.patch_resource("google_flow_account", acc_ready_1["id"], {
        "status": "ready", "enabled": True, "email": "ready1@test.com", "session_present": True
    })
    secret_store.set_google_session(acc_ready_1["id"], {"session": {"tok": "1"}})
    p1 = manager.profile_dir_for_account(acc_ready_1)
    p1.mkdir(parents=True, exist_ok=True)
    (p1 / "account_data.txt").write_text("acc1", encoding="utf-8")

    acc_ready_2 = manager.create_account()
    db.patch_resource("google_flow_account", acc_ready_2["id"], {
        "status": "ready", "enabled": True, "email": "ready2@test.com", "session_present": True
    })
    secret_store.set_google_session(acc_ready_2["id"], {"session": {"tok": "2"}})
    p2 = manager.profile_dir_for_account(acc_ready_2)
    p2.mkdir(parents=True, exist_ok=True)
    (p2 / "account_data.txt").write_text("acc2", encoding="utf-8")

    acc_connecting = manager.create_account()
    db.patch_resource("google_flow_account", acc_connecting["id"], {
        "status": "connecting", "enabled": True, "email": "connecting@test.com", "session_present": True
    })
    secret_store.set_google_session(acc_connecting["id"], {"session": {"tok": "3"}})
    p3 = manager.profile_dir_for_account(acc_connecting)
    p3.mkdir(parents=True, exist_ok=True)

    acc_expired = manager.create_account()
    db.patch_resource("google_flow_account", acc_expired["id"], {
        "status": "auth_expired", "enabled": True, "email": "expired@test.com", "session_present": True
    })
    secret_store.set_google_session(acc_expired["id"], {"session": {"tok": "4"}})
    p4 = manager.profile_dir_for_account(acc_expired)
    p4.mkdir(parents=True, exist_ok=True)

    acc_dead = manager.create_account()
    db.patch_resource("google_flow_account", acc_dead["id"], {
        "status": "login_required", "enabled": False, "email": "dead@test.com", "session_present": False
    })
    secret_store.set_google_session(acc_dead["id"], {"session": {"tok": "5"}})
    p5 = manager.profile_dir_for_account(acc_dead)
    p5.mkdir(parents=True, exist_ok=True)

    all_ids = [acc_ready_1["id"], acc_ready_2["id"], acc_connecting["id"], acc_expired["id"], acc_dead["id"]]

    # Phase 1: Run clean_profile_caches
    stats = manager.clean_profile_caches()
    assert stats["ok"] is True

    # Assert 100% of accounts remain in DB! Not a single registered account touched!
    for aid in all_ids:
        assert manager.db.get_resource("google_flow_account", aid) is not None, (
            f"Account {aid} was erroneously deleted by clean_profile_caches!"
        )
        assert secret_store._session_path(aid).is_file(), f"Session for {aid} was deleted by clean_profile_caches!"

    # Phase 2: Run prune_dead_accounts
    def mock_check_account(aid: str):
        if aid in (acc_ready_1["id"], acc_ready_2["id"]):
            return {
                "id": aid, "ok": True, "status": "ready", "enabled": True, "session_present": True
            }
        return {
            "id": aid, "ok": False, "status": "login_required", "enabled": False, "session_present": False
        }

    monkeypatch.setattr(manager, "check_account", mock_check_account)

    prune_res = manager.prune_dead_accounts()
    assert prune_res["ok"] is True
    assert prune_res["active_count"] == 2

    # Active accounts MUST be preserved
    assert manager.db.get_resource("google_flow_account", acc_ready_1["id"]) is not None
    assert manager.db.get_resource("google_flow_account", acc_ready_2["id"]) is not None
    assert p1.exists()
    assert p2.exists()
    assert (p1 / "account_data.txt").is_file()
    assert (p2 / "account_data.txt").is_file()

    # Dead accounts MUST be deleted from DB and disk
    for dead_id, dead_p in [(acc_connecting["id"], p3), (acc_expired["id"], p4), (acc_dead["id"], p5)]:
        assert manager.db.get_resource("google_flow_account", dead_id) is None
        assert not dead_p.exists()
        assert not secret_store._session_path(dead_id).exists()


def test_adversarial_rapid_sequential_clean_cache_api():
    """Stress-test sequential API clean-cache invocations against production server app."""
    app = server.create_app()
    client = TestClient(app)

    # 5 sequential clean-cache calls
    for i in range(5):
        resp = client.post("/api/cofi-studio/runtime/accounts/clean-cache")
        assert resp.status_code == 200, f"Call {i} failed with status {resp.status_code}"
        body = resp.json()
        assert body.get("ok") is True
        assert "freed_mb" in body
        assert "total_size_mb" in body


def test_adversarial_empty_account_id_does_not_target_profile_root(tmp_path):
    """Stress-test that empty or whitespace account_id does not resolve to profile_root or delete it."""
    db_path = tmp_path / "adv_safety.db"
    db = Database(db_path)
    secret_dir = tmp_path / "adv_safety_secrets"
    secret_store = KeyringSecretStore(storage_dir=secret_dir)
    profile_root = tmp_path / "adv_safety_profiles"
    profile_root.mkdir(parents=True, exist_ok=True)

    # Put a canary file in profile_root
    canary = profile_root / "canary.txt"
    canary.write_text("critical_profile_root_content", encoding="utf-8")

    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)

    # Calling remove with empty/blank account_id
    res1 = manager.remove("")
    assert res1 is False
    assert profile_root.exists(), "profile_root must never be deleted by remove('')"
    assert canary.is_file(), "canary file in profile_root was destroyed by remove('')"

    res2 = manager.remove("   ")
    assert res2 is False
    assert profile_root.exists(), "profile_root must never be deleted by remove('   ')"
    assert canary.is_file()
