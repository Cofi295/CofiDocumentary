"""
Adversarial empirical challenge harness for Milestone 1 - Challenger M1-2.
Tests:
1. REST API endpoint contracts and JSON schema:
   - POST /api/cofi-studio/runtime/accounts/clean-cache
   - POST /api/v1/accounts/google-flow/clean-cache
2. Cache eviction vs session file preservation oracle.
3. Orphan profile and orphan session deletion with read-only files.
4. Idempotency & multi-threaded concurrency stress test.
5. Non-destructive preservation of active job 20261019-185102-31983814 and its workspace.
6. Non-destructive preservation of production Google Flow accounts and secrets.
"""

import concurrent.futures
import hashlib
import json
import os
import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as documentary_app
from documentary.service import DocumentaryService
import server
from vendor.media_factory.backend.app.db import Database
from vendor.media_factory.backend.app.providers.google import (
    BrowserLoginWorker,
    GoogleFlowAccountManager,
    _calc_dir_size_bytes,
    _evict_profile_cache_subdirs,
    _rmtree_robust,
)
from vendor.media_factory.backend.app.secrets import KeyringSecretStore


ROOT = Path(__file__).resolve().parent.parent


def test_endpoint_cofi_studio_clean_cache_schema():
    """Verify POST /api/cofi-studio/runtime/accounts/clean-cache returns 200 and schema."""
    fastapi_app = server.create_app()
    client = TestClient(fastapi_app)

    res = client.post("/api/cofi-studio/runtime/accounts/clean-cache")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    payload = res.json()

    # Schema assertions
    assert isinstance(payload, dict), "Payload must be a JSON object"
    assert "ok" in payload, "Missing 'ok' field"
    assert payload["ok"] is True, f"Expected ok: True, got {payload['ok']}"
    assert "total_size_mb" in payload, "Missing 'total_size_mb' field"
    assert isinstance(payload["total_size_mb"], (int, float)), "total_size_mb must be numeric"
    assert payload["total_size_mb"] >= 0, "total_size_mb must be non-negative"

    assert "freed_mb" in payload, "Missing 'freed_mb' field"
    assert isinstance(payload["freed_mb"], (int, float)), "freed_mb must be numeric"
    assert payload["freed_mb"] >= 0, "freed_mb must be non-negative"

    assert "orphan_profiles_removed" in payload, "Missing 'orphan_profiles_removed' field"
    assert isinstance(payload["orphan_profiles_removed"], int), "orphan_profiles_removed must be int"
    assert payload["orphan_profiles_removed"] >= 0

    assert "cleaned_profiles_count" in payload, "Missing 'cleaned_profiles_count' field"
    assert isinstance(payload["cleaned_profiles_count"], int), "cleaned_profiles_count must be int"
    assert payload["cleaned_profiles_count"] >= 0


def test_endpoint_google_flow_clean_cache_alias_schema():
    """Verify POST /api/v1/accounts/google-flow/clean-cache returns 200 and schema."""
    fastapi_app = server.create_app()
    client = TestClient(fastapi_app)

    res = client.post("/api/v1/accounts/google-flow/clean-cache")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    payload = res.json()

    assert payload.get("ok") is True
    assert isinstance(payload.get("total_size_mb"), (int, float))
    assert isinstance(payload.get("freed_mb"), (int, float))
    assert isinstance(payload.get("orphan_profiles_removed"), int)
    assert isinstance(payload.get("cleaned_profiles_count"), int)


def test_endpoint_clean_cache_on_legacy_app():
    """Verify endpoints also work on app.create_app() instance directly."""
    fastapi_app = documentary_app.create_app()
    client = TestClient(fastapi_app)

    res1 = client.post("/api/cofi-studio/runtime/accounts/clean-cache")
    assert res1.status_code == 200
    assert res1.json().get("ok") is True

    res2 = client.post("/api/v1/accounts/google-flow/clean-cache")
    assert res2.status_code == 200
    assert res2.json().get("ok") is True


def test_cache_eviction_oracle_adversarial(tmp_path):
    """
    Adversarial Oracle:
    Create a registered account with extensive cache directories and critical session files.
    Also create 2 orphan profiles (one with read-only locked files) and orphan session files.
    Verify clean_profile_caches() removes ALL caches and orphans while preserving 100% of session files.
    """
    db_path = tmp_path / "test_adv.db"
    db = Database(db_path)
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir(parents=True, exist_ok=True)
    secret_store = KeyringSecretStore(storage_dir=secret_dir)
    profile_root = tmp_path / "profiles"
    profile_root.mkdir(parents=True, exist_ok=True)

    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)

    # 1. Registered Account
    acc = manager.create_account()
    acc_id = acc["id"]
    secret_store.set_google_session(acc_id, {"session": {"access_token": "valid_token"}, "email": "valid@gmail.com"})
    active_enc_file = secret_store._session_path(acc_id)
    assert active_enc_file.is_file()

    p_dir = manager.profile_dir_for_account(acc)
    p_dir.mkdir(parents=True, exist_ok=True)

    # Session files that MUST NEVER be deleted
    protected_files = {
        p_dir / "Default" / "Cookies": b"binary_cookies_data",
        p_dir / "Default" / "Network" / "Cookies": b"binary_network_cookies_data",
        p_dir / "Default" / "Local Storage" / "leveldb" / "000001.log": b"local_storage_db",
        p_dir / "Default" / "Session Storage" / "000001.log": b"session_storage_db",
        p_dir / "Default" / "IndexedDB" / "https_flow.google_0.indexeddb.leveldb" / "000001.ldb": b"indexeddb_db",
        p_dir / "Default" / "Preferences": b'{"profile":{"name":"User"}}',
        p_dir / "Local State": b'{"os_crypt":{"encrypted_key":"base64key"}}',
    }
    for pf, data in protected_files.items():
        pf.parent.mkdir(parents=True, exist_ok=True)
        pf.write_bytes(data)

    # Cache directories that MUST be purged
    cache_dirs_to_purge = [
        p_dir / "Default" / "Cache" / "Cache_Data",
        p_dir / "Default" / "Code Cache" / "js",
        p_dir / "Default" / "Code Cache" / "wasm",
        p_dir / "Default" / "GPUCache",
        p_dir / "Default" / "DawnCache",
        p_dir / "Default" / "DawnWebGPUCache",
        p_dir / "Default" / "GrShaderCache",
        p_dir / "Default" / "ShaderCache",
        p_dir / "Default" / "Service Worker" / "CacheStorage",
        p_dir / "Default" / "Service Worker" / "ScriptCache",
        p_dir / "ShaderCache",
        p_dir / "GrShaderCache",
        p_dir / "GraphiteDawnCache",
        p_dir / "Crashpad" / "reports",
        p_dir / "BrowserMetrics",
        p_dir / "component_crx_cache",
    ]
    for cd in cache_dirs_to_purge:
        cd.mkdir(parents=True, exist_ok=True)
        (cd / "data_blob.bin").write_bytes(b"A" * 1024 * 64)

    # 2. Orphan Profile 1 (standard)
    orphan1 = profile_root / "orphan_profile_normal_123"
    orphan1.mkdir(parents=True, exist_ok=True)
    (orphan1 / "junk.dat").write_bytes(b"JUNK1" * 1024)

    # 3. Orphan Profile 2 (with Windows read-only lock attribute)
    orphan2 = profile_root / "orphan_profile_readonly_456"
    orphan2.mkdir(parents=True, exist_ok=True)
    ro_sub = orphan2 / "locked_dir"
    ro_sub.mkdir(parents=True, exist_ok=True)
    ro_file = ro_sub / "locked_file.dat"
    ro_file.write_bytes(b"LOCKED" * 1024)
    os.chmod(str(ro_file), stat.S_IREAD)
    os.chmod(str(ro_sub), stat.S_IREAD | stat.S_IEXEC)

    # 4. Orphan Session Encrypted File
    orphan_enc = secret_dir / "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff.enc"
    orphan_enc.write_bytes(b"DEAD_SESSION")

    # Run cleanup
    stats = manager.clean_profile_caches()

    # Assert metrics
    assert stats["ok"] is True
    assert stats["orphan_profiles_removed"] == 2, f"Expected 2 orphan profiles removed, got {stats['orphan_profiles_removed']}"
    assert stats["orphan_sessions_removed"] == 1, f"Expected 1 orphan session removed, got {stats['orphan_sessions_removed']}"
    assert stats["cleaned_profiles_count"] == 1
    assert stats["freed_mb"] > 0

    # Verify ALL protected files are 100% intact with exact byte content
    for pf, expected_bytes in protected_files.items():
        assert pf.exists(), f"VIOLATION: Protected session file {pf} was deleted!"
        assert pf.read_bytes() == expected_bytes, f"VIOLATION: Protected session file {pf} was mutated!"

    # Verify active secret file is intact
    assert active_enc_file.is_file(), "Active session file was deleted!"

    # Verify all cache directories are evicted
    for cd in cache_dirs_to_purge:
        assert not cd.exists(), f"VIOLATION: Cache dir {cd} should have been evicted!"

    # Verify orphan profiles are gone
    assert not orphan1.exists(), "Orphan profile 1 still exists!"
    assert not orphan2.exists(), "Orphan profile 2 (read-only) still exists!"
    assert not orphan_enc.exists(), "Orphan session file still exists!"


def test_idempotency_and_concurrency_stress(tmp_path):
    """Stress test: rapid consecutive calls and multi-threaded calls do not fail or corrupt state."""
    db_path = tmp_path / "test_stress.db"
    db = Database(db_path)
    secret_dir = tmp_path / "secrets_stress"
    secret_dir.mkdir(parents=True, exist_ok=True)
    secret_store = KeyringSecretStore(storage_dir=secret_dir)
    profile_root = tmp_path / "profiles_stress"
    profile_root.mkdir(parents=True, exist_ok=True)

    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)
    acc = manager.create_account()
    p_dir = manager.profile_dir_for_account(acc)
    cache_dir = p_dir / "Default" / "Cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "f.bin").write_bytes(b"X" * 10000)

    # Call 1: cleans cache
    res1 = manager.clean_profile_caches()
    assert res1["ok"] is True
    assert res1["freed_mb"] >= 0

    # Call 2: already clean, must succeed idempotently
    res2 = manager.clean_profile_caches()
    assert res2["ok"] is True
    assert res2["freed_mb"] == 0.0

    # Concurrent multi-threaded stress: 4 threads calling simultaneously
    def call_clean():
        return manager.clean_profile_caches()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(call_clean) for _ in range(8)]
        results = [f.result() for f in futures]

    for r in results:
        assert r["ok"] is True


def test_active_job_preservation_20261019_185102_31983814():
    """
    R4 Non-Destructive Verification:
    Verify that job 20261019-185102-31983814 and its workspace remain completely undamaged.
    """
    job_file = ROOT / "data" / "jobs" / "20261019-185102-31983814" / "job.json"
    assert job_file.exists(), f"Job file {job_file} missing!"

    raw_job = job_file.read_text(encoding="utf-8")
    job = json.loads(raw_job)

    assert job.get("id") == "20261019-185102-31983814"
    assert job.get("status") in ("completed", "in_progress", "ready")

    # Workspace directory check
    ws_path = Path(job.get("workspace") or (ROOT / "workspaces" / "20261019-185102-31983814"))
    assert ws_path.is_dir(), f"Workspace directory {ws_path} does not exist!"

    required_ws_artifacts = [
        "input.json",
        "outline.json",
        "creative_brief.json",
        "research.md",
        "script.md",
        "visual_manifest.json",
        "media/style_reference/style_reference.png",
    ]
    for rel in required_ws_artifacts:
        art_path = ws_path / rel
        assert art_path.exists(), f"Critical job artifact {art_path} missing from workspace!"
        assert art_path.stat().st_size > 0, f"Critical job artifact {art_path} is empty!"

    # Verify style mode is custom, not stickman
    ai_settings_file = ws_path / "ai_visual_settings.json"
    if ai_settings_file.exists():
        ai_settings = json.loads(ai_settings_file.read_text(encoding="utf-8"))
        assert ai_settings.get("style_preset") != "Người que (Stickman)" or ai_settings.get("style_mode") == "custom"


def test_active_accounts_preservation_in_production_db():
    """
    R4 Non-Destructive Verification:
    Verify that running the clean-cache endpoint on the real Documentary service
    preserves all 3 production Google Flow accounts, their secret files, and their profile folders.
    """
    # 1. Inspect production DB
    db_file = ROOT / "data" / "media_factory" / "cofi_studio.db"
    assert db_file.exists(), f"DB {db_file} missing!"
    db = Database(db_file)
    accounts = db.list_resources("google_flow_account")
    assert len(accounts) >= 3, f"Expected at least 3 active accounts, found {len(accounts)}"

    acc_ids = [acc["id"] for acc in accounts]

    # 2. Check secret files
    secrets_dir = ROOT / "data" / "media_factory" / "secrets" / "google-flow"
    assert secrets_dir.is_dir()
    for acc_id in acc_ids:
        acc_hash = hashlib.sha256(acc_id.encode("utf-8")).hexdigest() + ".enc"
        secret_file = secrets_dir / acc_hash
        assert secret_file.exists(), f"Secret file for active account {acc_id} ({acc_hash}) is missing!"

    # 3. Check profile folders
    profiles_dir = ROOT / "data" / "media_factory" / "google-flow-profiles"
    assert profiles_dir.is_dir()
    for acc_id in acc_ids:
        p_dir = profiles_dir / acc_id
        assert p_dir.is_dir(), f"Profile directory for active account {acc_id} is missing!"

    # 4. Invoke clean-cache endpoint on the actual application server
    fastapi_app = server.create_app()
    client = TestClient(fastapi_app)
    res = client.post("/api/cofi-studio/runtime/accounts/clean-cache")
    assert res.status_code == 200
    data = res.json()
    assert data.get("ok") is True

    # 5. Re-verify active accounts, secrets, and profile directories
    accounts_post = db.list_resources("google_flow_account")
    assert len(accounts_post) == len(accounts), "Active accounts count changed after clean-cache!"
    for acc_id in acc_ids:
        acc_hash = hashlib.sha256(acc_id.encode("utf-8")).hexdigest() + ".enc"
        assert (secrets_dir / acc_hash).exists(), f"Secret file for {acc_id} deleted after clean-cache!"
        assert (profiles_dir / acc_id).is_dir(), f"Profile dir for {acc_id} deleted after clean-cache!"
