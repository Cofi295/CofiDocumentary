import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import create_app
from documentary.service import DocumentaryService


@pytest.fixture
def mock_documentary_env():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        service = DocumentaryService(root)
        app = create_app(service)
        client = TestClient(app)

        workspaces_dir = root / "workspaces"
        workspaces_dir.mkdir(parents=True, exist_ok=True)

        job = service.store.create({
            "title": "Chuyên Án Thử Nghiệm",
            "workspace": str(workspaces_dir / "test-job-media-action"),
            "status": "completed",
            "phases": {"qc": {"status": "succeeded"}},
        })
        job_id = job["id"]

        ws = Path(job["workspace"])
        release_dir = ws / "release"
        release_dir.mkdir(parents=True, exist_ok=True)
        video_file = release_dir / "video.mp4"
        video_content = b"TEST_VIDEO_BYTES_12345"
        video_file.write_bytes(video_content)

        yield {
            "root": root,
            "job_id": job_id,
            "video_file": video_file,
            "video_content": video_content,
            "service": service,
            "client": client,
        }


import json


def test_reveal_media_in_explorer(mock_documentary_env):
    service = mock_documentary_env["service"]
    job_id = mock_documentary_env["job_id"]
    res = service.reveal_media_in_explorer(job_id, "release/video.mp4")
    assert res["ok"] is True
    assert res["action"] == "reveal"
    assert Path(res["path"]).name == "video.mp4"
    assert res["size_bytes"] == len(mock_documentary_env["video_content"])


def test_save_local_media_copy_to_file(mock_documentary_env):
    service = mock_documentary_env["service"]
    job_id = mock_documentary_env["job_id"]
    target_file = mock_documentary_env["root"] / "export_test.mp4"

    res = service.save_local_media_copy(
        job_id,
        "release/video.mp4",
        destination_path=str(target_file),
        open_folder_after=False,
    )
    assert res["ok"] is True
    assert res["action"] == "save_copy"
    assert target_file.exists()
    assert target_file.read_bytes() == mock_documentary_env["video_content"]
    assert mock_documentary_env["video_file"].exists()  # Original preserved on copy


def test_save_local_media_copy_to_directory(mock_documentary_env):
    service = mock_documentary_env["service"]
    job_id = mock_documentary_env["job_id"]
    target_dir = mock_documentary_env["root"] / "target_folder"
    target_dir.mkdir(parents=True, exist_ok=True)

    res = service.save_local_media_copy(
        job_id,
        "release/video.mp4",
        suggested_filename="final_render.mp4",
        destination_path=str(target_dir),
        open_folder_after=False,
    )
    assert res["ok"] is True
    assert (target_dir / "final_render.mp4").exists()
    assert (target_dir / "final_render.mp4").read_bytes() == mock_documentary_env["video_content"]


def test_save_local_media_copy_same_file(mock_documentary_env):
    service = mock_documentary_env["service"]
    job_id = mock_documentary_env["job_id"]
    res = service.save_local_media_copy(
        job_id,
        "release/video.mp4",
        destination_path=str(mock_documentary_env["video_file"]),
        open_folder_after=False,
    )
    assert res["ok"] is True
    assert res.get("same_file") is True


def test_save_local_media_move(mock_documentary_env):
    service = mock_documentary_env["service"]
    job_id = mock_documentary_env["job_id"]
    target_file = mock_documentary_env["root"] / "moved_video.mp4"

    res = service.save_local_media_copy(
        job_id,
        "release/video.mp4",
        destination_path=str(target_file),
        open_folder_after=False,
        move=True,
    )
    assert res["ok"] is True
    assert res["action"] == "move"
    assert target_file.exists()
    assert not mock_documentary_env["video_file"].exists()  # Original moved


def test_api_job_media_local_action_endpoint(mock_documentary_env):
    client = mock_documentary_env["client"]
    job_id = mock_documentary_env["job_id"]
    target_file = mock_documentary_env["root"] / "api_save_copy.mp4"

    # 1. Test save_copy via API
    resp = client.post(
        f"/api/jobs/{job_id}/media/local-action",
        json={
            "path": "release/video.mp4",
            "action": "save_copy",
            "destination_path": str(target_file),
            "open_folder_after": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert Path(data["saved_path"]).name == "api_save_copy.mp4"
    assert target_file.exists()

    # 2. Test reveal via API
    resp_reveal = client.post(
        f"/api/jobs/{job_id}/media/local-action",
        json={"path": "release/video.mp4", "action": "reveal"},
    )
    assert resp_reveal.status_code == 200
    assert resp_reveal.json()["ok"] is True

    # 3. Test invalid action
    resp_bad = client.post(
        f"/api/jobs/{job_id}/media/local-action",
        json={"path": "release/video.mp4", "action": "unknown_action"},
    )
    assert resp_bad.status_code == 400

    # 4. Test missing path
    resp_missing = client.post(
        f"/api/jobs/{job_id}/media/local-action",
        json={"action": "save_copy"},
    )
    assert resp_missing.status_code == 400

    # 5. Test nonexistent job
    resp_404 = client.post(
        "/api/jobs/nonexistent-job-xyz/media/local-action",
        json={"path": "release/video.mp4", "action": "save_copy"},
    )
    assert resp_404.status_code == 404
