from __future__ import annotations

import threading
import time
from pathlib import Path

from documentary.render_cache import BackgroundRenderCache


def _cache(tmp_path: Path, with_script: bool = True) -> BackgroundRenderCache:
    remotion = tmp_path / "CofiRemotion"
    (remotion / "scripts").mkdir(parents=True)
    if with_script:
        (remotion / "scripts" / "turbo-nvenc-export.mjs").write_text("// fake", encoding="utf-8")
    return BackgroundRenderCache(remotion, chunk_seconds=30, concurrency=1, poll_interval=0.02, runner=lambda *a, **k: 0)


def test_prebake_skipped_when_studio_open(tmp_path):
    cache = _cache(tmp_path)
    res = cache.prebake_standalone_async({"id": "j1"}, tmp_path / "ws", studio_running=True)
    assert res == {"started": False, "reason": "studio_running"}


def test_prebake_skipped_without_turbo_script(tmp_path):
    cache = _cache(tmp_path, with_script=False)
    res = cache.prebake_standalone_async({"id": "j1"}, tmp_path / "ws")
    assert res["started"] is False and res["reason"] == "turbo_unavailable"


def test_prebake_skipped_when_render_lock_held(tmp_path):
    cache = _cache(tmp_path)
    lock = cache._render_locks.setdefault(str((tmp_path / "other").resolve()), threading.RLock())
    held = threading.Event()
    release = threading.Event()

    def hold():
        with lock:
            held.set()
            release.wait(5)

    t = threading.Thread(target=hold)
    t.start()
    held.wait(5)
    try:
        res = cache.prebake_standalone_async({"id": "j1"}, tmp_path / "ws")
        assert res == {"started": False, "reason": "render_active"}
    finally:
        release.set()
        t.join()


def test_prebake_runs_low_priority_and_writes_status(tmp_path, monkeypatch):
    cache = _cache(tmp_path)
    monkeypatch.setenv("COFI_NODE_BIN", "node")
    calls = []

    def fake_run(command, cwd, log_path, **kwargs):
        calls.append((command, kwargs))
        return 0

    monkeypatch.setattr(cache, "_run_process", fake_run)
    ws = tmp_path / "ws"
    res = cache.prebake_standalone_async({"id": "j1"}, ws)
    assert res["started"] is True
    cache._prebake_thread.join(5)
    assert calls, "prebake command not launched"
    command, kwargs = calls[0]
    assert "--prepare-plan-only=" in " ".join(command)
    assert kwargs["low_priority"] is True and kwargs["env_overrides"]["COFI_PRIORITY_LOW"] == "1"
    assert kwargs["slot_key"].startswith(BackgroundRenderCache.PREBAKE_PREFIX)
    assert (ws / ".render_cache" / "prebake_status.json").is_file()


def test_resolve_target_lufs_prefers_job_editing_dna(tmp_path, monkeypatch):
    monkeypatch.delenv("COFI_DEFAULT_TARGET_LUFS", raising=False)
    assert BackgroundRenderCache._resolve_target_lufs({"editing_dna": {"audio_rules": {"target_lufs": -14.8}}}) == -14.8
    assert BackgroundRenderCache._resolve_target_lufs(
        {"channel_profile_snapshot": {"editing_dna": {"audio_rules": {"target_lufs": -18}}}}
    ) == -18.0
    assert BackgroundRenderCache._resolve_target_lufs({}) == -16.0
