from pathlib import Path

from documentary.cofi_studio_embed import CofiStudioEmbedManager


def test_default_embed_uses_bundled_media_factory_and_documentary_state(monkeypatch):
    monkeypatch.delenv("COFI_STUDIO_DIR", raising=False)
    monkeypatch.delenv("COFI_MEDIA_FACTORY_STATE_DIR", raising=False)

    manager = CofiStudioEmbedManager()
    documentary_root = Path(__file__).resolve().parents[1]

    assert manager.studio_root == (documentary_root / "vendor" / "media_factory").resolve()
    assert manager.state_dir == (documentary_root / "data" / "media_factory").resolve()


def test_embed_runtime_env_points_vendor_runtime_at_documentary_state(tmp_path):
    studio_root = tmp_path / "vendor" / "media_factory"
    state_dir = tmp_path / "data" / "media_factory"
    manager = CofiStudioEmbedManager(studio_root=studio_root, state_dir=state_dir)

    env = manager._runtime_env()

    assert Path(env["COFI_MEDIA_FACTORY_STATE_DIR"]) == state_dir.resolve()
    assert Path(env["COFI_MEDIA_FACTORY_FRONTEND_DIST"]) == (studio_root / "frontend" / "dist").resolve()


def test_runtime_status_combines_accounts_and_queue(tmp_path, monkeypatch):
    manager = CofiStudioEmbedManager(studio_root=tmp_path / "factory", state_dir=tmp_path / "state")
    replies = {
        "/api/providers/google/accounts": [{"id": "acc-1", "status": "ready", "live_session": True}],
        "/api/queue/status": {"paused": True, "concurrency": 10},
    }
    monkeypatch.setattr(manager, "_request_json", lambda path, **_kwargs: replies[path])

    status = manager.runtime_status()

    assert status["accounts"][0]["id"] == "acc-1"
    assert status["queue"] == {"paused": True, "concurrency": 10}


def test_runtime_controls_use_media_factory_api(tmp_path, monkeypatch):
    manager = CofiStudioEmbedManager(studio_root=tmp_path / "factory", state_dir=tmp_path / "state")
    calls = []
    monkeypatch.setattr(
        manager,
        "_request_json",
        lambda path, **kwargs: calls.append((path, kwargs)) or {"ok": True},
    )

    manager.queue_action("resume")
    manager.account_action("acc-1", "verify")
    manager.generate({"id": "ui-test"})

    assert calls == [
        ("/api/queue/resume", {"method": "POST"}),
        ("/api/providers/google/accounts/acc-1/verify", {"method": "POST"}),
        ("/api/providers/google/generate", {"method": "POST", "payload": {"scene": {"id": "ui-test"}}, "timeout": 330.0}),
    ]
