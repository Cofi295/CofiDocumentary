from __future__ import annotations

import base64
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from vendor.media_factory.backend.app.db import Database
from vendor.media_factory.backend.app.providers.base import ProviderError
from vendor.media_factory.backend.app.providers.google import (
    FLOW_API_ROOT,
    FLOW_AUTH_SESSION_URL,
    GoogleFlowAccountManager,
    GoogleFlowBrowserClient,
)
from vendor.media_factory.backend.app.providers.google_flow_migrated import (
    MigratedFlowImageDriver,
    MigratedFlowVideoDriver,
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


def test_glabs_upload_image_payload_and_media_id_extraction(tmp_path: Path) -> None:
    client = GoogleFlowBrowserClient(tmp_path, session_worker=None)
    dummy_img = tmp_path / "ref.jpg"
    dummy_img.write_bytes(b"\xff\xd8\xff\xe0testjpeg")

    recorded_posts: list[dict] = []

    def fake_post_json(_page, url, access_token, body):
        recorded_posts.append({"url": url, "access_token": access_token, "body": body})
        return {"mediaId": "mid-from-mediaId-field"}

    client._browser_post_json = fake_post_json
    fake_page = SimpleNamespace()

    media_id = client._upload_reference_image_direct(
        fake_page,
        access_token="test-access-token",
        project_id="proj-123",
        reference_image=str(dummy_img),
    )

    assert media_id == "mid-from-mediaId-field"
    assert len(recorded_posts) == 1
    call = recorded_posts[0]
    assert call["url"] == f"{FLOW_API_ROOT}/flow/uploadImage"
    assert call["access_token"] == "test-access-token"
    body = call["body"]
    assert body["clientContext"] == {"projectId": "proj-123", "tool": "PINHOLE"}
    assert body["isUserUploaded"] is True
    assert body["isHidden"] is False
    assert body["fileName"] == "ref.jpg"
    assert "image/jpeg" in body["mimeType"]
    assert base64.b64decode(body["imageBytes"]) == b"\xff\xd8\xff\xe0testjpeg"


def test_glabs_upload_image_media_id_fallback_extraction(tmp_path: Path) -> None:
    client = GoogleFlowBrowserClient(tmp_path, session_worker=None)
    dummy_img = tmp_path / "ref.png"
    dummy_img.write_bytes(b"dummy-png")

    client._browser_post_json = lambda *_args, **_kwargs: {"media": {"name": "mid-from-nested-media-name"}}
    media_id = client._upload_reference_image_direct(
        SimpleNamespace(),
        access_token="tok",
        project_id="p1",
        reference_image=str(dummy_img),
    )
    assert media_id == "mid-from-nested-media-name"

    client._browser_post_json = lambda *_args, **_kwargs: {"name": "mid-from-top-name"}
    media_id = client._upload_reference_image_direct(
        SimpleNamespace(),
        access_token="tok",
        project_id="p1",
        reference_image=str(dummy_img),
    )
    assert media_id == "mid-from-top-name"


def test_glabs_batch_generate_images_payload_structure(tmp_path: Path) -> None:
    client = GoogleFlowBrowserClient(tmp_path, session_worker=None)

    scene = {
        "model": "nano_banana_pro",
        "aspect_ratio": "16:9",
        "prompt": "Documentary shot of ancient library",
    }
    payload = client._build_direct_image_payload(
        scene,
        project_id="proj-1",
        recaptcha_token="recaptcha-tok-123",
        paygate_tier="PAYGATE_TIER_TWO",
        reference_media_ids=["mid-ref-1", "mid-ref-2"],
        seed=42,
        batch_id="batch-uuid-1",
        session_id="session-id-1",
    )

    assert payload["clientContext"]["projectId"] == "proj-1"
    assert payload["clientContext"]["sessionId"] == "session-id-1"
    assert payload["clientContext"]["tool"] == "PINHOLE"
    assert payload["clientContext"]["userPaygateTier"] == "PAYGATE_TIER_TWO"
    assert payload["clientContext"]["recaptchaContext"]["token"] == "recaptcha-tok-123"

    assert payload["useNewMedia"] is True

    req = payload["requests"][0]
    assert req["imageModelName"] == "GEM_PIX_2"
    assert req["imageAspectRatio"] == "IMAGE_ASPECT_RATIO_LANDSCAPE"
    assert req["structuredPrompt"] == {"parts": [{"text": "Documentary shot of ancient library"}]}
    assert req["seed"] == 42
    assert len(req["imageInputs"]) == 2
    assert req["imageInputs"][0] == {
        "name": "mid-ref-1",
        "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE",
    }
    assert req["imageInputs"][1] == {
        "name": "mid-ref-2",
        "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE",
    }


def test_glabs_image_model_name_mappings(tmp_path: Path) -> None:
    client = GoogleFlowBrowserClient(tmp_path, session_worker=None)

    for model_id, expected_wire in [
        ("nano_banana_2_lite", "HARBOR_SEAL"),
        ("nano_banana_2", "NARWHAL"),
        ("nano_banana_pro", "GEM_PIX_2"),
        ("unknown_fallback", "NARWHAL"),
    ]:
        p = client._build_direct_image_payload(
            {"model": model_id, "prompt": "test"},
            project_id="p",
            recaptcha_token="r",
            paygate_tier="t",
            reference_media_ids=[],
            seed=1,
            batch_id="b",
            session_id="s",
        )
        assert p["requests"][0]["imageModelName"] == expected_wire


def test_glabs_video_worker_payload_and_resolution(tmp_path: Path) -> None:
    client = GoogleFlowBrowserClient(tmp_path, session_worker=None)

    scene = {
        "model": "veo_31_fast",
        "aspect_ratio": "16:9",
        "duration_seconds": 8,
        "prompt": "Camera pushes slowly toward the documents",
        "_flow_account_tier": "ultra",
        "_video_resolution": "720p",
    }
    payload = client._build_direct_video_payload(
        scene,
        project_id="proj-vid",
        recaptcha_token="recaptcha-vid-tok",
        paygate_tier="PAYGATE_TIER_TWO",
        start_media_id="start-mid-1",
        end_media_id=None,
        seed=100,
        batch_id="vid-batch-uuid",
        session_id="vid-session-id",
    )

    assert "videoRequests" in payload
    assert "requests" in payload
    assert payload["outputSpec"] == {"resolution": "VIDEO_RESOLUTION_720P"}
    assert payload["useV2ModelConfig"] is True

    vreq = payload["videoRequests"][0]
    assert vreq["aspectRatio"] == "VIDEO_ASPECT_RATIO_LANDSCAPE"
    assert vreq["videoModelKey"] == "veo_3_1_i2v_s_fast_ultra"
    assert vreq["textInput"] == {"structuredPrompt": {"parts": [{"text": "Camera pushes slowly toward the documents"}]}}
    assert vreq["startImage"] == {"mediaId": "start-mid-1"}
    assert "endImage" not in vreq
    assert vreq["mediaGenerationContext"] == {"batchId": "vid-batch-uuid"}


def test_glabs_video_routes_start_and_end(tmp_path: Path) -> None:
    client = GoogleFlowBrowserClient(tmp_path, session_worker=None)
    ref1 = tmp_path / "f1.png"
    ref1.write_bytes(b"f1")
    ref2 = tmp_path / "f2.png"
    ref2.write_bytes(b"f2")

    posted_urls: list[str] = []
    client._flow_page = lambda _ctx: SimpleNamespace(url="https://flow.google.com/project/p1")
    client._access_token = lambda _ctx: "tok"
    client._upload_reference_image_direct = lambda _page, **kw: f"mid-{kw['reference_image'][-6:-4]}"
    client._mint_flow_recaptcha = lambda _page, _action: "recaptcha"
    client._browser_post_json = lambda _page, url=None, access_token=None, body=None, **kw: posted_urls.append(url) or {"media": [{"name": "vid-out"}]}

    # 1. Start and end frame
    client._start_video_generation_in_context(
        SimpleNamespace(),
        {"_flow_project_id": "p1", "model": "veo_31_fast", "reference_images": [str(ref1), str(ref2)]},
    )
    assert posted_urls[-1] == f"{FLOW_API_ROOT}/video:batchAsyncGenerateVideoStartAndEndImage"

    # 2. Start frame only
    client._start_video_generation_in_context(
        SimpleNamespace(),
        {"_flow_project_id": "p1", "model": "veo_31_fast", "reference_images": [str(ref1)]},
    )
    assert posted_urls[-1] == f"{FLOW_API_ROOT}/video:batchAsyncGenerateVideoStartImage"

    # 3. Text to video
    client._start_video_generation_in_context(
        SimpleNamespace(),
        {"_flow_project_id": "p1", "model": "veo_31_fast", "reference_images": [], "task_type": "text_to_video"},
    )
    assert posted_urls[-1] == f"{FLOW_API_ROOT}/video:batchAsyncGenerateVideoText"


def test_glabs_video_polling_submitted_status_continues(tmp_path: Path) -> None:
    client = GoogleFlowBrowserClient(tmp_path, session_worker=None)
    context = SimpleNamespace(pages=[SimpleNamespace(url="https://flow.google.com/project/p1")])
    client._access_token = lambda _context: "token"
    client._browser_post_json = lambda *_args, **_kwargs: {
        "media": [
            {
                "mediaMetadata": {
                    "mediaStatus": {
                        "mediaGenerationStatus": "MEDIA_GENERATION_STATUS_SUBMITTED",
                    }
                }
            }
        ]
    }

    result = client._poll_video_media_once(
        context,
        "submitted-job-1",
        {"_flow_project_id": "p1"},
    )
    assert result is None


def test_glabs_api_only_session_refresh_success(tmp_path: Path) -> None:
    db = Database(tmp_path / "media_factory.db")
    secrets = _SecretStore()
    manager = GoogleFlowAccountManager(
        db,
        secrets,  # type: ignore[arg-type]
        profile_root=tmp_path / "profiles",
        login_worker=None,
    )
    account = manager.create_account()
    account_id = account["id"]
    secrets.sessions[account_id] = {
        "cookies": [
            {"name": "__Secure-next-auth.session-token", "value": "test-session-cookie-val"},
            {"name": "SID", "value": "test-sid-val"},
        ],
        "session": {"accessToken": "old-token"},
    }

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({
        "access_token": "new-fresh-access-token",
        "expires": "2026-10-01T12:00:00.000Z",
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        refreshed = manager.try_refresh_session_api(account_id)
        assert refreshed is True
        # Verify request headers
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == FLOW_AUTH_SESSION_URL
        assert "__Secure-next-auth.session-token=test-session-cookie-val" in req.headers["Cookie"]
        assert req.headers["Origin"] == "https://labs.google"

    # Verify updated session and db
    saved = secrets.get_google_session(account_id)
    assert saved["session"]["access_token"] == "new-fresh-access-token"
    acc = manager.get_account(account_id)
    assert acc["status"] == "ready"
    assert acc["session_expires_at"] == "2026-10-01T12:00:00+00:00"


def test_migrated_flow_image_driver_direct_execution(tmp_path: Path) -> None:
    driver = MigratedFlowImageDriver(tmp_path)
    ref = tmp_path / "input.png"
    ref.write_bytes(b"fake-image-bytes")

    uploaded_calls: list[dict] = []
    batch_calls: list[dict] = []

    class FakePage:
        def evaluate(self, script, args=None):
            if isinstance(args, dict) and "uploadImage" in args.get("url", ""):
                uploaded_calls.append(args)
                return {"ok": True, "status": 200, "payload": {"mediaId": "uploaded-media-1"}}
            if isinstance(args, dict) and "flowMedia:batchGenerateImages" in args.get("url", ""):
                batch_calls.append(args)
                return {
                    "ok": True,
                    "status": 200,
                    "payload": {
                        "media": [
                            {
                                "name": "generated-media-id-1",
                                "image": {
                                    "generatedImage": {
                                        "fifeUrl": "https://lh3.googleusercontent.com/direct-gen-img",
                                    }
                                },
                            }
                        ]
                    },
                }
            if "auth/session" in script:
                return "direct-page-token"
            if "enterprise.execute" in script:
                return {"token": "page-recaptcha-tok"}
            return None

    page = FakePage()
    scene = {
        "model": "nano_banana_2",
        "aspect_ratio": "16:9",
        "prompt": "Aerial view of mountain range",
        "reference_images": [str(ref)],
    }

    img_record = driver.submit(page, "proj-migrated-1", scene)
    assert img_record.media_id == "generated-media-id-1"
    assert img_record.image_url == "https://lh3.googleusercontent.com/direct-gen-img"
    assert img_record.prompt == "Aerial view of mountain range"

    assert len(uploaded_calls) == 1
    assert uploaded_calls[0]["body"]["clientContext"] == {"projectId": "proj-migrated-1", "tool": "PINHOLE"}
    assert len(batch_calls) == 1
    batch_req = batch_calls[0]["body"]
    assert batch_req["useNewMedia"] is True


def test_migrated_flow_video_driver_direct_execution(tmp_path: Path) -> None:
    driver = MigratedFlowVideoDriver(tmp_path)
    ref = tmp_path / "start.png"
    ref.write_bytes(b"start-frame-bytes")

    video_submit_calls: list[dict] = []
    status_check_calls: list[dict] = []

    class FakePage:
        def evaluate(self, script, args=None):
            if isinstance(args, dict) and "uploadImage" in args.get("url", ""):
                return {"ok": True, "status": 200, "payload": {"mediaId": "uploaded-vid-start"}}
            if isinstance(args, dict) and "batchAsyncGenerateVideoStartImage" in args.get("url", ""):
                video_submit_calls.append(args)
                return {"ok": True, "status": 200, "payload": {"media": [{"name": "vid-gen-mid-99"}]}}
            if isinstance(args, dict) and "batchCheckAsyncVideoGenerationStatus" in args.get("url", ""):
                status_check_calls.append(args)
                return {
                    "ok": True,
                    "status": 200,
                    "payload": {
                        "media": [
                            {
                                "mediaMetadata": {
                                    "mediaStatus": {
                                        "mediaGenerationStatus": "MEDIA_GENERATION_STATUS_SUCCESSFUL",
                                    }
                                },
                                "video": {
                                    "generatedVideo": {
                                        "fifeUrl": "https://lh3.googleusercontent.com/direct-gen-video.mp4",
                                    }
                                },
                            }
                        ]
                    },
                }
            if "auth/session" in script:
                return "direct-page-token"
            if "enterprise.execute" in script:
                return {"token": "page-recaptcha-tok"}
            return None

    page = FakePage()
    scene = {
        "model": "veo_31_lite",
        "aspect_ratio": "16:9",
        "prompt": "Tracking shot through rainforest",
        "reference_image": str(ref),
    }

    # 1. Submit
    gen_record = driver.submit(page, "proj-vid-1", scene)
    assert gen_record.workflow_id == "vid-gen-mid-99"
    assert gen_record.media_id == "vid-gen-mid-99"
    assert gen_record.is_running is True
    assert len(video_submit_calls) == 1
    vbody = video_submit_calls[0]["body"]
    assert "videoRequests" in vbody
    assert vbody["videoRequests"][0]["videoModelKey"] == "veo_3_1_i2v_lite"

    # 2. Poll
    polled = driver.poll(page, "vid-gen-mid-99")
    assert polled is not None
    assert polled.is_done is True
    assert polled.video_url == "https://lh3.googleusercontent.com/direct-gen-video.mp4"
    assert len(status_check_calls) == 1
    assert status_check_calls[0]["body"]["media"] == [{"name": "vid-gen-mid-99", "projectId": "proj-vid-1"}]
