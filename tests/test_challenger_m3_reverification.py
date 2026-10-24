"""
Adversarial Verification Suite for Milestone M3_3:
Independent empirical challenge of the 3 defect resolutions and R4 integrity.
"""

from __future__ import annotations

import copy
import io
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from server import create_app
from documentary.service import DocumentaryService
from documentary.thumbnail_studio import (
    build_default_thumbnail_design,
    export_thumbnail_ab_pack,
    select_thumbnail_winner,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
JOBS_DIR = DATA_DIR / "jobs"
WORKSPACES_DIR = ROOT / "workspaces"
PROFILES_FILE = DATA_DIR / "channel_profiles.json"
ACTIVE_JOB_ID = "20261019-185102-31983814"


@pytest.fixture(scope="module")
def app_client():
    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def managed_reverification_job():
    """Create an isolated test job and workspace."""
    test_job_id = "job-reverify-m3-3"
    job_dir = JOBS_DIR / test_job_id
    ws_dir = WORKSPACES_DIR / test_job_id

    shutil.rmtree(job_dir, ignore_errors=True)
    shutil.rmtree(ws_dir, ignore_errors=True)

    job_dir.mkdir(parents=True, exist_ok=True)
    ws_dir.mkdir(parents=True, exist_ok=True)

    job_record = {
        "id": test_job_id,
        "job_id": test_job_id,
        "title": "중국 28년 미제사건의 비밀 (Bí mật đại án 28 năm)",
        "topic": "중국 바이인 연쇄살인 사건",
        "channel_profile_id": "channel-e544a64b7c",
        "workspace": str(ws_dir),
        "status": "completed",
    }
    (job_dir / "job.json").write_text(json.dumps(job_record, indent=2, ensure_ascii=False), encoding="utf-8")
    (ws_dir / "input.json").write_text(json.dumps(job_record, indent=2, ensure_ascii=False), encoding="utf-8")

    yield test_job_id, ws_dir, job_dir

    shutil.rmtree(job_dir, ignore_errors=True)
    shutil.rmtree(ws_dir, ignore_errors=True)


# ==============================================================================
# DEFECT 1 RE-VERIFICATION: ab_test_metadata.json TITLE ATTRIBUTE
# ==============================================================================

def test_metadata_contains_title_across_diverse_encodings():
    """Verify that export_thumbnail_ab_pack reliably outputs 'title' into metadata and inside ZIP."""
    titles = [
        "중국 28년 미제사건의 비밀 (Bí mật đại án 28 năm)",
        "Special chars & <tags> 'quotes' \"double\" / \\",
        "Emoji test 🎯 ⚡ 🔍 🔥",
        "",  # Empty title should still produce 'title': ''
    ]

    for title in titles:
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            job = {"id": "t1", "title": title}
            res = export_thumbnail_ab_pack("t1", tmp_dir, design=None, job=job)
            assert res["ok"] is True
            assert "title" in res["metadata"], f"Metadata missing 'title' key for title='{title}'"
            assert res["metadata"]["title"] == title

            meta_file = Path(res["metadata_path"])
            assert meta_file.is_file()
            meta_json = json.loads(meta_file.read_text("utf-8"))
            assert "title" in meta_json
            assert meta_json["title"] == title

            # Check inside ZIP
            with zipfile.ZipFile(res["zip_path"], "r") as zf:
                zip_meta = json.loads(zf.read("ab_test_metadata.json").decode("utf-8"))
                assert "title" in zip_meta
                assert zip_meta["title"] == title
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def test_metadata_title_fallback_to_design_title_when_job_lacks_title():
    """When job has no title, export_thumbnail_ab_pack falls back to design['title']."""
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        job = {"id": "t_no_title"}
        design = {"title": "Design Fallback Title", "variants": []}
        res = export_thumbnail_ab_pack("t_no_title", tmp_dir, design=design, job=job)
        assert res["metadata"]["title"] == "Design Fallback Title"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ==============================================================================
# DEFECT 2 RE-VERIFICATION: select_thumbnail_winner VARIANT ALIAS RESOLUTION
# ==============================================================================

@pytest.mark.parametrize("requested_id, expected_active_id", [
    ("v2", "v2"),
    ("variant_b", "v2"),
    ("variant b", "v2"),
    ("b", "v2"),
    ("B", "v2"),
    ("Variant B", "v2"),
    ("VARIANT_B", "v2"),
    ("  variant_b  ", "v2"),
    ("v1", "v1"),
    ("variant_a", "v1"),
    ("variant a", "v1"),
    ("a", "v1"),
    ("A", "v1"),
    ("Variant A", "v1"),
    ("v3", "v3"),
    ("variant_c", "v3"),
    ("variant c", "v3"),
    ("c", "v3"),
    ("C", "v3"),
    ("Variant C", "v3"),
])
def test_select_thumbnail_winner_alias_matrix(requested_id, expected_active_id):
    """Stress-test alias resolution in select_thumbnail_winner."""
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        job = {"id": "t_alias", "title": "Test Title"}
        res = select_thumbnail_winner("t_alias", tmp_dir, requested_id, design=None, job=job)
        assert res["ok"] is True
        assert res["active_variant_id"] == expected_active_id, (
            f"Requested '{requested_id}' expected '{expected_active_id}' but got '{res['active_variant_id']}'"
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_select_winner_rest_api_variant_b(app_client, managed_reverification_job):
    """Test REST API endpoint POST /api/jobs/{id}/thumbnail-studio/select-winner with variant_b."""
    job_id, ws_dir, _ = managed_reverification_job
    # Default design is missing initially in managed_reverification_job workspace
    resp = app_client.post(f"/api/jobs/{job_id}/thumbnail-studio/select-winner", json={"variant_id": "variant_b"})
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()
    assert data["ok"] is True
    assert data["active_variant_id"] == "v2"

    # Verify exported file is Variant B
    thumb_path = ws_dir / "thumbnail.jpg"
    assert thumb_path.is_file()
    assert thumb_path.stat().st_size > 0

    design_json = json.loads((ws_dir / "thumbnail_design.json").read_text("utf-8"))
    assert design_json["active_variant_id"] == "v2"


# ==============================================================================
# DEFECT 3 RE-VERIFICATION: MISSING / EMPTY THUMBNAIL_DESIGN.JSON
# ==============================================================================

def test_missing_design_in_service_export_ab_pack(managed_reverification_job):
    """Verify DocumentaryService.export_thumbnail_ab_pack when thumbnail_design.json is missing."""
    job_id, ws_dir, _ = managed_reverification_job
    design_file = ws_dir / "thumbnail_design.json"
    if design_file.exists():
        design_file.unlink()

    service = DocumentaryService(ROOT)
    res = service.export_thumbnail_ab_pack(job_id)
    assert res["ok"] is True
    assert res["exported_count"] == 3
    assert len(res["variants"]) == 3
    assert Path(res["zip_path"]).is_file()


def test_empty_dict_design_in_service_export_ab_pack(managed_reverification_job):
    """Verify DocumentaryService.export_thumbnail_ab_pack when thumbnail_design.json is an empty dict {}."""
    job_id, ws_dir, _ = managed_reverification_job
    design_file = ws_dir / "thumbnail_design.json"
    design_file.write_text("{}", encoding="utf-8")

    service = DocumentaryService(ROOT)
    res = service.export_thumbnail_ab_pack(job_id)
    assert res["ok"] is True
    assert res["exported_count"] == 3
    assert len(res["variants"]) == 3


def test_missing_design_in_service_select_winner(managed_reverification_job):
    """Verify DocumentaryService.select_thumbnail_winner when thumbnail_design.json is absent."""
    job_id, ws_dir, _ = managed_reverification_job
    design_file = ws_dir / "thumbnail_design.json"
    if design_file.exists():
        design_file.unlink()

    service = DocumentaryService(ROOT)
    res = service.select_thumbnail_winner(job_id, payload={"variant_id": "variant_b"})
    assert res["ok"] is True
    assert res["active_variant_id"] == "v2"
    assert (ws_dir / "thumbnail.jpg").is_file()


def test_empty_dict_design_in_service_select_winner(managed_reverification_job):
    """Verify DocumentaryService.select_thumbnail_winner when thumbnail_design.json is empty {}."""
    job_id, ws_dir, _ = managed_reverification_job
    design_file = ws_dir / "thumbnail_design.json"
    design_file.write_text("{}", encoding="utf-8")

    service = DocumentaryService(ROOT)
    res = service.select_thumbnail_winner(job_id, payload={"variant_id": "variant_c"})
    assert res["ok"] is True
    assert res["active_variant_id"] == "v3"


# ==============================================================================
# R4 RE-VERIFICATION: ACTIVE JOB AND DATABASES INTACT
# ==============================================================================

def test_r4_active_job_and_sqlite_databases_intact():
    """Verify active running job 20261019-185102-31983814 and SQLite databases remain unharmed."""
    active_ws = WORKSPACES_DIR / ACTIVE_JOB_ID
    assert active_ws.is_dir(), f"Active workspace {active_ws} does not exist!"

    thumb = active_ws / "thumbnail.jpg"
    assert thumb.is_file()
    assert thumb.stat().st_size == 239852, f"Size changed: {thumb.stat().st_size}"

    design = active_ws / "thumbnail_design.json"
    assert design.is_file()
    assert design.stat().st_size == 17365, f"Size changed: {design.stat().st_size}"

    input_json = active_ws / "input.json"
    assert input_json.is_file()
    assert input_json.stat().st_size == 15077, f"Size changed: {input_json.stat().st_size}"

    # Verify SQLite DB
    radar_db = DATA_DIR / "radar.db"
    assert radar_db.exists(), "radar.db missing!"

    media_db = DATA_DIR / "media_factory" / "media_factory.db"
    assert media_db.exists(), "media_factory.db missing!"
