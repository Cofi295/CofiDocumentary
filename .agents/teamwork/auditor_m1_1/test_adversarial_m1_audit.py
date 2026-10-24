import os
import stat
import shutil
import hashlib
from pathlib import Path

from vendor.media_factory.backend.app.db import Database
from vendor.media_factory.backend.app.secrets import KeyringSecretStore
from vendor.media_factory.backend.app.providers.google import (
    GoogleFlowAccountManager,
    BrowserLoginWorker,
    _rmtree_robust,
    _evict_profile_cache_subdirs,
    _calc_dir_size_bytes,
)


def test_adversarial_nested_readonly_and_locked_files(tmp_path):
    """Stress-test _rmtree_robust against deeply nested read-only files and folders."""
    deep_dir = tmp_path / "deep" / "level1" / "level2" / "level3"
    deep_dir.mkdir(parents=True)
    f1 = deep_dir / "readonly_1.bin"
    f2 = deep_dir / "readonly_2.dat"
    f1.write_bytes(b"A" * 1024)
    f2.write_bytes(b"B" * 2048)
    os.chmod(str(f1), stat.S_IREAD)
    os.chmod(str(f2), stat.S_IREAD)
    os.chmod(str(deep_dir), stat.S_IREAD | stat.S_IEXEC)
    os.chmod(str(deep_dir.parent), stat.S_IREAD | stat.S_IEXEC)

    res = _rmtree_robust(tmp_path / "deep")
    assert res is True
    assert not (tmp_path / "deep").exists()


def test_adversarial_protected_session_files_inviolability(tmp_path):
    """Stress-test _evict_profile_cache_subdirs to ensure NO protected session files are EVER deleted."""
    p_dir = tmp_path / "adversarial_profile"
    p_dir.mkdir(parents=True)

    # Protected paths in various casings and sub-locations
    prot_files = [
        p_dir / "Local State",
        p_dir / "Default" / "Preferences",
        p_dir / "Default" / "Cookies",
        p_dir / "Default" / "Network" / "Cookies",
        p_dir / "Default" / "Cookies-journal",
        p_dir / "Default" / "Local Storage" / "leveldb" / "000001.log",
        p_dir / "Default" / "Local Storage" / "leveldb" / "CURRENT",
        p_dir / "Default" / "Local Storage" / "leveldb" / "MANIFEST-000001",
        p_dir / "Default" / "Session Storage" / "000001.log",
        p_dir / "Default" / "IndexedDB" / "flow_blob.indexeddb.leveldb" / "000001.log",
    ]
    for pf in prot_files:
        pf.parent.mkdir(parents=True, exist_ok=True)
        pf.write_text(f"precious-credential-{pf.name}", encoding="utf-8")
        os.chmod(str(pf), stat.S_IREAD)  # Make read-only as well

    # Non-essential cache directories
    cache_dirs = [
        p_dir / "Default" / "Cache",
        p_dir / "Default" / "Code Cache",
        p_dir / "Default" / "GPUCache",
        p_dir / "Default" / "DawnCache",
        p_dir / "Default" / "Service Worker" / "CacheStorage",
        p_dir / "ShaderCache",
        p_dir / "Crashpad",
        p_dir / "BrowserMetrics",
    ]
    for cd in cache_dirs:
        cd.mkdir(parents=True, exist_ok=True)
        (cd / "junk.tmp").write_bytes(b"JUNK" * 1000)

    freed = _evict_profile_cache_subdirs(p_dir)
    assert freed > 0

    # Ensure EVERY protected file is intact with unmodified content
    for pf in prot_files:
        assert pf.is_file(), f"Protected file {pf} was VIOLATED!"
        assert pf.read_text(encoding="utf-8") == f"precious-credential-{pf.name}"

    # Ensure all cache dirs are wiped
    for cd in cache_dirs:
        assert not cd.exists(), f"Cache dir {cd} was not removed!"


def test_adversarial_custom_and_standard_profile_dirs_cleanup(tmp_path):
    """Test that remove() cleans both custom profile_dir and standard profile_root dir."""
    db = Database(tmp_path / "custom.db")
    secret_store = KeyringSecretStore(storage_dir=tmp_path / "secrets")
    profile_root = tmp_path / "std_profiles"
    profile_root.mkdir()

    custom_dir = tmp_path / "external_profiles" / "custom_acc_1"
    custom_dir.mkdir(parents=True)
    (custom_dir / "data.txt").write_text("custom", encoding="utf-8")

    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)
    acc = manager.create_account()
    acc_id = acc["id"]

    # Point account to custom profile dir
    db.patch_resource("google_flow_account", acc_id, {"profile_dir": str(custom_dir)})

    # Also create standard profile dir (e.g. created previously)
    std_dir = profile_root / acc_id
    std_dir.mkdir(parents=True)
    (std_dir / "std.txt").write_text("std", encoding="utf-8")

    secret_store.set_google_session(acc_id, {"session": {"tok": "123"}})

    removed = manager.remove(acc_id)
    assert removed is True
    assert not custom_dir.exists(), "Custom profile dir must be removed"
    assert not std_dir.exists(), "Standard profile dir must be removed"
    assert db.get_resource("google_flow_account", acc_id) is None


def test_adversarial_clean_profile_caches_edge_cases(tmp_path):
    """Test edge cases: corrupt files in profile_root, accounts with strange characters."""
    db = Database(tmp_path / "edge.db")
    secret_store = KeyringSecretStore(storage_dir=tmp_path / "secrets")
    profile_root = tmp_path / "profiles"
    profile_root.mkdir()

    # Plain file in profile_root (should not be deleted as an orphan profile directory)
    junk_file = profile_root / "junk_file.txt"
    junk_file.write_text("not_a_dir", encoding="utf-8")

    # Account created normally
    manager = GoogleFlowAccountManager(db, secret_store, profile_root=profile_root)
    manager.create_account()

    # Run clean_profile_caches
    stats = manager.clean_profile_caches()
    assert stats["ok"] is True
    assert junk_file.exists(), "Plain file in profile_root should not be mistakenly removed"
