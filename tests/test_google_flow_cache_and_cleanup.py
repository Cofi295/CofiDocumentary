import hashlib
import json
import os
import stat
from pathlib import Path

from fastapi.testclient import TestClient

from vendor.media_factory.backend.app.db import Database
from vendor.media_factory.backend.app.main import create_app as create_media_factory_app
from vendor.media_factory.backend.app.providers.google import (
    BrowserLoginWorker,
    GoogleFlowAccountManager,
    _calc_dir_size_bytes,
    _evict_profile_cache_subdirs,
    _rmtree_robust,
)
from vendor.media_factory.backend.app.secrets import KeyringSecretStore
import server


def test_rmtree_robust_handles_read_only_files(tmp_path):
    target_dir = tmp_path / "protected_profile"
    target_dir.mkdir(parents=True)
    ro_file = target_dir / "readonly.dat"
    ro_file.write_text("locked-content", encoding="utf-8")
    os.chmod(str(ro_file), stat.S_IREAD)
    os.chmod(str(target_dir), stat.S_IREAD | stat.S_IEXEC)

    assert _rmtree_robust(target_dir) is True
    assert not target_dir.exists()


def test_account_deletion_removes_db_record_secret_session_and_disk_profile(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    secret_dir = tmp_path / "secrets"
    secret_store = KeyringSecretStore(storage_dir=secret_dir)
    profile_root = tmp_path / "profiles"
    profile_root.mkdir(parents=True, exist_ok=True)

    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)
    acc = manager.create_account()
    acc_id = acc["id"]

    # Save session secret
    secret_store.set_google_session(acc_id, {"session": {"access_token": "token-123"}, "email": "test@example.com"})
    enc_path = secret_store._session_path(acc_id)
    assert enc_path.is_file(), "Secret session file must be created on disk"

    # Create profile on disk with files and read-only attributes
    p_dir = manager.profile_dir_for_account(acc)
    p_dir.mkdir(parents=True, exist_ok=True)
    test_file = p_dir / "state.json"
    test_file.write_text('{"user":"test"}', encoding="utf-8")
    os.chmod(str(test_file), stat.S_IREAD)
    assert p_dir.is_dir()

    # Perform removal
    removed = manager.remove(acc_id)
    assert removed is True

    # Verification: DB record deleted
    assert manager.db.get_resource("google_flow_account", acc_id) is None

    # Verification: secret session file deleted from disk
    assert not enc_path.exists(), "Encrypted session file must be deleted from disk"

    # Verification: profile directory deleted from disk
    assert not p_dir.exists(), "Chromium profile folder must be completely deleted from disk"


def test_prune_dead_accounts_completely_removes_disk_profile(tmp_path, monkeypatch):
    db_path = tmp_path / "test_prune.db"
    db = Database(db_path)
    secret_dir = tmp_path / "secrets_prune"
    secret_store = KeyringSecretStore(storage_dir=secret_dir)
    profile_root = tmp_path / "profiles_prune"
    profile_root.mkdir(parents=True, exist_ok=True)

    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)

    # Account 1: Live / ready
    acc_live = manager.create_account()
    db.patch_resource("google_flow_account", acc_live["id"], {"status": "ready", "email": "live@example.com"})
    secret_store.set_google_session(acc_live["id"], {"session": {"access_token": "live-tok"}})
    live_p_dir = manager.profile_dir_for_account(acc_live)
    live_p_dir.mkdir(parents=True, exist_ok=True)
    (live_p_dir / "user_data.txt").write_text("live_user", encoding="utf-8")

    # Account 2: Dead / expired
    acc_dead = manager.create_account()
    db.patch_resource("google_flow_account", acc_dead["id"], {"status": "login_required", "email": "dead@example.com"})
    dead_p_dir = manager.profile_dir_for_account(acc_dead)
    dead_p_dir.mkdir(parents=True, exist_ok=True)
    (dead_p_dir / "dead_data.txt").write_text("dead_user", encoding="utf-8")

    # Mock check_account to report live as ok and dead as expired
    def mock_check_account(acc_id: str):
        if acc_id == acc_live["id"]:
            return {
                "id": acc_live["id"],
                "ok": True,
                "status": "ready",
                "enabled": True,
                "session_present": True,
                "email": "live@example.com",
            }
        return {
            "id": acc_dead["id"],
            "ok": False,
            "status": "login_required",
            "enabled": True,
            "session_present": False,
            "error": "expired",
        }

    monkeypatch.setattr(manager, "check_account", mock_check_account)

    result = manager.prune_dead_accounts()
    assert result.get("ok") is True

    # Live account remains
    assert manager.db.get_resource("google_flow_account", acc_live["id"]) is not None
    assert live_p_dir.exists()

    # Dead account deleted completely
    assert manager.db.get_resource("google_flow_account", acc_dead["id"]) is None
    assert not dead_p_dir.exists(), "Dead account profile directory must be deleted on prune"


def test_cache_cleanup_evicts_cache_and_orphans_while_preserving_session_files(tmp_path):
    db_path = tmp_path / "test_cleanup.db"
    db = Database(db_path)
    secret_dir = tmp_path / "secrets_cleanup"
    secret_store = KeyringSecretStore(storage_dir=secret_dir)
    profile_root = tmp_path / "profiles_cleanup"
    profile_root.mkdir(parents=True, exist_ok=True)

    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)
    acc = manager.create_account()
    acc_id = acc["id"]
    db.patch_resource("google_flow_account", acc_id, {"status": "ready", "email": "active@example.com"})
    secret_store.set_google_session(acc_id, {"session": {"access_token": "active-tok"}})
    active_enc = secret_store._session_path(acc_id)
    assert active_enc.is_file()

    p_dir = manager.profile_dir_for_account(acc)
    p_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create essential session files that MUST be preserved
    essential_files = [
        p_dir / "Local State",
        p_dir / "Default" / "Preferences",
        p_dir / "Default" / "Cookies",
        p_dir / "Default" / "Network" / "Cookies",
        p_dir / "Default" / "Local Storage" / "leveldb" / "000001.log",
        p_dir / "Default" / "Session Storage" / "000001.log",
        p_dir / "Default" / "IndexedDB" / "flow.indexeddb.leveldb" / "000001.log",
    ]
    for ef in essential_files:
        ef.parent.mkdir(parents=True, exist_ok=True)
        ef.write_text(f"essential_content_for_{ef.name}", encoding="utf-8")

    # 2. Create non-essential cache subdirectories that MUST be evicted
    cache_dirs = [
        p_dir / "Default" / "Cache" / "Cache_Data",
        p_dir / "Default" / "Code Cache" / "js",
        p_dir / "Default" / "GPUCache",
        p_dir / "Default" / "DawnCache",
        p_dir / "Default" / "Service Worker" / "CacheStorage",
        p_dir / "Default" / "Service Worker" / "ScriptCache",
        p_dir / "ShaderCache",
        p_dir / "GrShaderCache",
        p_dir / "GraphiteDawnCache",
        p_dir / "Crashpad" / "reports",
        p_dir / "BrowserMetrics",
        p_dir / "component_crx_cache",
        p_dir / "extensions_crx_cache",
    ]
    for cd in cache_dirs:
        cd.mkdir(parents=True, exist_ok=True)
        (cd / "data.bin").write_bytes(b"x" * 1024 * 50)  # 50 KB dummy cache each

    # 3. Create an ORPHAN profile folder in profile_root (no DB record)
    orphan_id = "orphan_folder_dead_account_123"
    orphan_dir = profile_root / orphan_id
    orphan_dir.mkdir(parents=True, exist_ok=True)
    (orphan_dir / "Default" / "Cache").mkdir(parents=True, exist_ok=True)
    (orphan_dir / "Default" / "Cache" / "orphan_blob.bin").write_bytes(b"o" * 1024 * 100)

    # 4. Create an ORPHAN secret session file in secret_dir
    orphan_secret_hash = hashlib.sha256(b"orphan_account_456").hexdigest()
    orphan_enc = secret_dir / f"{orphan_secret_hash}.enc"
    orphan_enc.write_bytes(b"orphan-encrypted-session-blob")

    # Run clean_profile_caches
    stats = manager.clean_profile_caches()

    assert stats.get("ok") is True
    assert stats.get("status") == "success"
    assert stats.get("freed_mb") > 0
    assert stats.get("orphan_profiles_removed") == 1
    assert stats.get("orphan_sessions_removed") == 1
    assert stats.get("cleaned_profiles_count") == 1

    # Verify essential session files are STILL INTACT
    for ef in essential_files:
        assert ef.is_file(), f"Essential file {ef} was incorrectly removed!"
        assert ef.read_text(encoding="utf-8") == f"essential_content_for_{ef.name}"

    # Verify active secret file is STILL INTACT
    assert active_enc.is_file(), "Active session file must not be removed"

    # Verify cache directories are REMOVED
    for cd in cache_dirs:
        assert not cd.exists(), f"Cache directory {cd} should have been evicted!"

    # Verify orphan profile folder and orphan secret are REMOVED
    assert not orphan_dir.exists(), "Orphan profile directory must be deleted!"
    assert not orphan_enc.exists(), "Orphan secret session file must be deleted!"


def test_media_factory_clean_cache_api_endpoints(tmp_path):
    db_path = tmp_path / "mf_api.db"
    out_dir = tmp_path / "mf_out"
    secret_dir = tmp_path / "mf_secrets"
    profile_root = tmp_path / "mf_profiles"
    profile_root.mkdir(parents=True, exist_ok=True)

    db = Database(db_path)
    secret_store = KeyringSecretStore(storage_dir=secret_dir)
    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)

    app = create_media_factory_app(
        db_path=db_path,
        output_dir=out_dir,
        secret_store=secret_store,
        google_account_manager=manager,
    )
    client = TestClient(app)

    # Test /api/providers/google/accounts/clean-cache
    resp1 = client.post("/api/providers/google/accounts/clean-cache")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1.get("ok") is True
    assert "freed_mb" in data1
    assert "total_size_mb" in data1
    assert "orphan_profiles_removed" in data1

    # Test alias /api/v1/accounts/google-flow/clean-cache
    resp2 = client.post("/api/v1/accounts/google-flow/clean-cache")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2.get("ok") is True
    assert "freed_mb" in data2


def test_cofi_documentary_clean_cache_api_endpoints():
    app = server.create_app()
    client = TestClient(app)

    resp1 = client.post("/api/cofi-studio/runtime/accounts/clean-cache")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1.get("ok") is True
    assert "freed_mb" in data1

    resp2 = client.post("/api/v1/accounts/google-flow/clean-cache")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2.get("ok") is True


def test_frontend_ui_contract_in_static_app_js():
    js_content = Path("static/app.js").read_text(encoding="utf-8")
    assert "popupCleanCacheBtn" in js_content, "Missing popupCleanCacheBtn in static/app.js"
    assert "runCleanFlowAccountsCache" in js_content, "Missing runCleanFlowAccountsCache in static/app.js"
    assert "/api/cofi-studio/runtime/accounts/clean-cache" in js_content
    assert "⚡ Dọn Cache Thông Minh" in js_content
