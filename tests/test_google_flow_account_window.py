from __future__ import annotations

import pytest

from vendor.media_factory.backend.app.db import Database
from vendor.media_factory.backend.app.providers.base import ProviderTransientError
from vendor.media_factory.backend.app.providers.google import GoogleFlowAccountManager


class _SecretStore:
    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}

    def get_google_session(self, account_id: str) -> dict | None:
        return self.sessions.get(account_id)


class _LoginWorker:
    @staticmethod
    def has_live_session(_account_id: str) -> bool:
        return True


def test_video_account_runs_five_per_account_while_queue_can_wait(tmp_path):
    db = Database(tmp_path / "media_factory.db")
    secrets = _SecretStore()
    manager = GoogleFlowAccountManager(
        db,
        secrets,  # type: ignore[arg-type]
        profile_root=tmp_path / "profiles",
        login_worker=_LoginWorker(),  # type: ignore[arg-type]
    )

    account = manager.create_account()
    account_id = account["id"]
    db.patch_resource(
        "google_flow_account",
        account_id,
        {
            "email": "test@example.com",
            "tier": "ultra",
            "status": "ready",
            "enabled": True,
            "video_enabled": True,
            "video_quota_state": "available",
            "quota_state": "available",
            "credits": 100000,
        },
    )
    secrets.sessions[account_id] = {"cookies": []}

    for expected_active in range(1, 6):
        leased = manager.lease_account("veo_31_lite_relaxed")
        assert leased["id"] == account_id
        assert leased["active_jobs"] == expected_active

    with pytest.raises(ProviderTransientError):
        manager.lease_account("veo_31_lite_relaxed")

    manager.release_account(account_id)
    assert manager.get_account(account_id)["active_jobs"] == 4
    leased = manager.lease_account("veo_31_lite_relaxed")
    assert leased["active_jobs"] == 5

    with pytest.raises(ProviderTransientError):
        manager.lease_account("veo_31_lite_relaxed")
