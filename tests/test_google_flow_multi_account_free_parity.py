import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from vendor.media_factory.backend.app.db import Database
from vendor.media_factory.backend.app.providers.base import ProviderError
from vendor.media_factory.backend.app.providers.google import (
    GOOGLE_FLOW_MODEL_BY_ID,
    GOOGLE_FLOW_MODELS,
    GoogleFlowAccountManager,
    GoogleFlowBrowserClient,
    GoogleFlowHeadlessClient,
)
from vendor.media_factory.backend.app.providers.google_flow_migrated import (
    MigratedFlowImageDriver,
    MigratedFlowVideoDriver,
    _mint_recaptcha_token,
)


class _SecretStore:
    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}

    def get_google_session(self, account_id: str) -> dict | None:
        return self.sessions.get(account_id)

    def set_google_session(self, account_id: str, payload: dict) -> None:
        self.sessions[account_id] = payload

    def delete_google_session(self, account_id: str) -> None:
        self.sessions.pop(account_id, None)


def test_free_tier_enabled_for_models() -> None:
    nano2 = GOOGLE_FLOW_MODEL_BY_ID["nano_banana_2"]
    assert "free" in nano2["tiers"], "nano_banana_2 must include free tier"

    veo_fast = GOOGLE_FLOW_MODEL_BY_ID["veo_31_fast"]
    assert "free" not in veo_fast["tiers"], "veo_31_fast must NOT include free tier (Free is only for images)"


def test_paygate_tier_mapping() -> None:
    client = GoogleFlowBrowserClient(Path("."), session_worker=None)
    assert client._paygate_tier("ultra") == "PAYGATE_TIER_TWO"
    assert client._paygate_tier("pro") == "PAYGATE_TIER_ONE"
    assert client._paygate_tier("free") == "PAYGATE_TIER_NOT_PAID"
    assert client._paygate_tier(None) == "PAYGATE_TIER_NOT_PAID"
    assert client._paygate_tier("") == "PAYGATE_TIER_NOT_PAID"


def test_multi_account_round_robin_with_free_and_ultra(tmp_path: Path) -> None:
    db = Database(tmp_path / "cofi_studio.db")
    secrets = _SecretStore()
    manager = GoogleFlowAccountManager(
        db,
        secrets,  # type: ignore[arg-type]
        profile_root=tmp_path / "profiles",
        login_worker=None,
    )

    # Account 1: Ultra
    acc_ultra = manager.create_account()
    secrets.set_google_session(acc_ultra["id"], {"captured_at": "2026-09-23T00:00:00Z"})
    db.patch_resource(
        "google_flow_account",
        acc_ultra["id"],
        {
            "email": "ultra@example.com",
            "tier": "ultra",
            "status": "ready",
            "enabled": True,
            "credits": 20000,
        },
    )

    # Account 2: Free
    acc_free = manager.create_account()
    secrets.set_google_session(acc_free["id"], {"captured_at": "2026-09-23T00:00:00Z"})
    db.patch_resource(
        "google_flow_account",
        acc_free["id"],
        {
            "email": "free@example.com",
            "tier": "free",
            "status": "ready",
            "enabled": True,
            "credits": 50,
        },
    )

    # Both accounts should be eligible for nano_banana_2
    model = GOOGLE_FLOW_MODEL_BY_ID["nano_banana_2"]
    eligible = manager._eligible_accounts(model, include_busy=True)
    eligible_emails = {a["email"] for a in eligible}
    assert "ultra@example.com" in eligible_emails
    assert "free@example.com" in eligible_emails
    assert len(eligible) == 2

    # Leases should alternate in round-robin order
    lease1 = manager.lease_account("nano_banana_2")
    lease2 = manager.lease_account("nano_banana_2")
    assert {lease1["email"], lease2["email"]} == {"ultra@example.com", "free@example.com"}

    manager.release_account(lease1["id"])
    manager.release_account(lease2["id"])


def test_migrated_image_direct_rest_called_without_ui_modal(tmp_path: Path) -> None:
    class FakeWorker:
        def execute_in_session(self, _account_id, callback, **_kwargs):
            context = SimpleNamespace(pages=[SimpleNamespace(url="https://flow.google.com/project/p1")])
            return callback(context)

    manager = SimpleNamespace(login_worker=FakeWorker())
    client = GoogleFlowHeadlessClient(tmp_path, account_manager=manager)

    client._open_project = lambda _page, _account: "proj-abc"
    client._persist_refreshed_session = lambda *_args, **_kwargs: None

    gen_calls: list[dict] = []
    fake_driver = SimpleNamespace(
        generate=lambda page, context, project_id, scene: gen_calls.append({
            "project_id": project_id,
            "paygate_tier": scene.get("_flow_paygate_tier"),
            "model": scene.get("model"),
        }) or (tmp_path / "img.png")
    )
    client._migrated_image = fake_driver  # type: ignore[assignment]

    # Test with Free account
    result = client._generate_image_migrated_split(
        {"model": "nano_banana_2", "prompt": "ancient ruins", "aspect_ratio": "16:9"},
        {"id": "acc-free", "tier": "free"},
        {"migrated_host": True},
    )

    assert len(gen_calls) == 1
    assert gen_calls[0]["project_id"] == "proj-abc"
    assert gen_calls[0]["paygate_tier"] == "PAYGATE_TIER_NOT_PAID"
    assert gen_calls[0]["model"] == "nano_banana_2"


def test_migrated_video_direct_rest_called_without_ui_modal(tmp_path: Path) -> None:
    class FakeWorker:
        def execute_in_session(self, _account_id, callback, **_kwargs):
            context = SimpleNamespace(pages=[SimpleNamespace(url="https://flow.google.com/project/p1")])
            return callback(context)

    ref_img = tmp_path / "frame.png"
    ref_img.write_bytes(b"frame-png-bytes")

    manager = SimpleNamespace(login_worker=FakeWorker())
    client = GoogleFlowHeadlessClient(tmp_path, account_manager=manager)

    client._open_project = lambda _page, _account: "proj-vid"
    client._persist_refreshed_session = lambda *_args, **_kwargs: None

    submit_calls: list[dict] = []
    fake_vid_driver = SimpleNamespace(
        submit=lambda page, project_id, scene: submit_calls.append({
            "project_id": project_id,
            "paygate_tier": scene.get("_flow_paygate_tier"),
            "model": scene.get("model"),
        }) or SimpleNamespace(workflow_id="wf-1", is_running=False, is_failed=False, is_done=True),
        poll=lambda page, workflow_id: SimpleNamespace(is_running=False, is_failed=False, is_done=True),
        download=lambda context, record, scene: tmp_path / "out.mp4",
    )
    client._migrated_video = fake_vid_driver  # type: ignore[assignment]

    result = client._generate_video_migrated_split(
        {
            "model": "veo_31_fast",
            "prompt": "slow pan over mountains",
            "aspect_ratio": "16:9",
            "reference_images": [str(ref_img)],
        },
        {"id": "acc-free", "tier": "free"},
        {"migrated_host": True},
    )

    assert len(submit_calls) == 1
    assert submit_calls[0]["project_id"] == "proj-vid"
    assert submit_calls[0]["paygate_tier"] == "PAYGATE_TIER_NOT_PAID"
    assert submit_calls[0]["model"] == "veo_31_fast"
    assert str(tmp_path / "out.mp4") in result


def test_recaptcha_minting_inspects_grecaptcha_cfg() -> None:
    class FakePageWithGrecaptchaCfg:
        def evaluate(self, script, action=None):
            assert "___grecaptcha_cfg" in script, "Script must inspect ___grecaptcha_cfg"
            return {"token": "minted-enterprise-token-via-cfg"}

    page = FakePageWithGrecaptchaCfg()
    token = _mint_recaptcha_token(page, "PINHOLE_GENERATE_IMAGE")
    assert token == "minted-enterprise-token-via-cfg"
