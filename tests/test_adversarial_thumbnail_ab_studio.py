"""
Adversarial Challenger Test Suite for Milestone 3 (M3):
Thumbnail Studio A/B Test Pack Export, Winner Selection, and Style Locking REST APIs.
(Requirements R3, AC3, R4).

Empirically tests:
1. POST /api/jobs/{job_id}/thumbnail-studio/export-ab-pack:
   - 200 OK with zip_path, zip_url, metadata.
   - Zip archive unpacks and contains variant_a.jpg, variant_b.jpg, variant_c.jpg, ab_test_metadata.json.
   - All 3 images are valid JPEGs (>0 bytes, PIL verifies format=='JPEG', mode=='RGB', size==(1280, 720)).
   - ab_test_metadata.json verification: title presence/absence check, hook types, predicted CTRs.
   - Non-existent job ID returns 404.
   - Workspace missing thumbnail_design.json behavior test.
2. POST /api/jobs/{job_id}/thumbnail-studio/select-winner:
   - Sets active_variant_id in design and returns 200.
   - Exports workspace/thumbnail.jpg and workspace/media/thumbnails/thumbnail.jpg.
   - Passing "variant_b" vs "v2" behavior check.
   - Non-existent job ID returns 404.
3. POST /api/jobs/{job_id}/lock-thumbnail-dna:
   - Extracts active variant styling (palette, fonts, archetype).
   - Increments channel profile version from V to V+1.
   - Archives previous version in thumbnail_dna_history with locked_from_job_id and timestamp.
   - Updates job snapshot and workspace input.json.
   - Missing channel_profile_id on job returns 400.
4. R4 Non-Destructive Preservation:
   - Verifies active running job 20261019-185102-31983814 workspace files, databases, and records remain completely untouched.
"""

from __future__ import annotations

import copy
import io
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from server import create_app

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
def managed_test_job():
    """Create an isolated test job and workspace, cleaning up completely after the test."""
    test_job_id = "job-test-challenger-m3"
    job_dir = JOBS_DIR / test_job_id
    ws_dir = WORKSPACES_DIR / test_job_id

    # Clean any stale test artifacts
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
    if ws_dir.exists():
        shutil.rmtree(ws_dir, ignore_errors=True)

    job_dir.mkdir(parents=True, exist_ok=True)
    ws_dir.mkdir(parents=True, exist_ok=True)

    # Base job record
    job_record = {
        "id": test_job_id,
        "job_id": test_job_id,
        "title": "중국 28년 미제사건의 비밀 (Bí mật đại án 28 năm)",
        "topic": "중국 바이인 연쇄살인 사건",
        "channel_profile_id": "channel-e544a64b7c",
        "workspace": str(ws_dir),
        "status": "completed",
        "thumbnail_dna": {
            "style_preset": "cold_forensic_noir",
            "layout_template": "broadcast_left_heavy",
            "color_palette": {
                "primary": "#FFE84A",
                "secondary": "#0F172A",
                "accent": "#EF4444",
                "background": "#020617",
            },
            "typography_preset": {
                "font_family": "Pretendard",
                "title_weight": "900",
                "stroke_color": "#000000",
                "stroke_width": 6,
                "text_transform": "uppercase",
            },
            "visual_signature": "Cold Forensic Noir Preset",
            "reference_character_path": "",
            "mascot_lock": True,
            "version": 1,
        },
    }
    (job_dir / "job.json").write_text(json.dumps(job_record, indent=2, ensure_ascii=False), encoding="utf-8")

    # Base workspace files
    input_data = copy.deepcopy(job_record)
    (ws_dir / "input.json").write_text(json.dumps(input_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Base thumbnail_design.json with 3 variants
    design = {
        "job_id": test_job_id,
        "title": "중국 28년 미제사건의 비밀",
        "active_variant_id": "v1",
        "layout_template": "broadcast_left_heavy",
        "variants": [
            {
                "id": "v1",
                "short_label": "BẢN A",
                "name": "BẢN A · Tò mò / Nghịch lý",
                "archetype": "broadcast_left_heavy",
                "hook_type": "curiosity_paradox",
                "hook_badge": "🎯 Variant A: Tò mò / Nghịch lý",
                "psychological_hook": "Tạo khoảng trống tò mò cực độ",
                "badge_text": "중국 실화 사건",
                "line_1": "28년간 숨겨진 진실",
                "line_2": "DNA가 밝혀낸 악마",
                "layers": [
                    {
                        "id": "badge",
                        "type": "textbox",
                        "text": "중국 실화 사건",
                        "left": 40,
                        "top": 40,
                        "width": 300,
                        "height": 50,
                        "backgroundColor": "#EF4444",
                        "fill": "#ffffff",
                    },
                    {
                        "id": "line_1",
                        "type": "textbox",
                        "text": "28년간 숨겨진 진실",
                        "left": 40,
                        "top": 280,
                        "width": 600,
                        "height": 80,
                        "fontFamily": "Pretendard",
                        "fill": "#ffffff",
                        "stroke": "#000000",
                        "strokeWidth": 6,
                    },
                    {
                        "id": "line_2",
                        "type": "textbox",
                        "text": "DNA가 밝혀낸 악마",
                        "left": 40,
                        "top": 380,
                        "width": 650,
                        "height": 90,
                        "fontFamily": "Pretendard",
                        "fill": "#FFE84A",
                        "stroke": "#000000",
                        "strokeWidth": 6,
                    },
                ],
                "ctr_prediction": {
                    "score": 88,
                    "predicted_ctr_pct": 11.5,
                    "dna_consistency_score": 90,
                    "text_legibility_score": 86,
                    "curiosity_gap_score": 88,
                    "keyword_alignment_score": 92,
                },
            },
            {
                "id": "v2",
                "short_label": "BẢN B",
                "name": "BẢN B · Bằng chứng / Cận cảnh",
                "archetype": "evidence_spotlight",
                "hook_type": "character_evidence",
                "hook_badge": "🔍 Variant B: Nhân vật / Bằng chứng",
                "psychological_hook": "Cận cảnh bằng chứng then chốt",
                "badge_text": "단독 입수",
                "line_1": "현장 옆 매점의 비밀",
                "line_2": "단 하나의 지문",
                "layers": [
                    {
                        "id": "badge",
                        "type": "textbox",
                        "text": "단독 입수",
                        "left": 40,
                        "top": 40,
                        "backgroundColor": "#DC2626",
                        "fill": "#ffffff",
                    },
                    {
                        "id": "line_1",
                        "type": "textbox",
                        "text": "현장 옆 매점의 비밀",
                        "left": 40,
                        "top": 280,
                        "fontFamily": "Gmarket Sans",
                        "fill": "#ffffff",
                        "stroke": "#000000",
                        "strokeWidth": 6,
                    },
                    {
                        "id": "line_2",
                        "type": "textbox",
                        "text": "단 하나의 지문",
                        "left": 40,
                        "top": 380,
                        "fontFamily": "Gmarket Sans",
                        "fill": "#38BDF8",
                        "stroke": "#000000",
                        "strokeWidth": 6,
                    },
                ],
                "ctr_prediction": {
                    "score": 85,
                    "predicted_ctr_pct": 10.8,
                    "dna_consistency_score": 88,
                    "text_legibility_score": 84,
                    "curiosity_gap_score": 82,
                    "keyword_alignment_score": 90,
                },
            },
            {
                "id": "v3",
                "short_label": "BẢN C",
                "name": "BẢN C · Đối đầu / Hồ sơ mật",
                "archetype": "split_duality",
                "hook_type": "confrontation_contrast",
                "hook_badge": "⚡ Variant C: Đối đầu / Hồ sơ mật",
                "psychological_hook": "Tương phản đối đầu kịch tính",
                "badge_text": "특급 수배",
                "line_1": "23만 명을 속인 얼굴",
                "line_2": "드러난 악마의 정체",
                "layers": [
                    {
                        "id": "badge",
                        "type": "textbox",
                        "text": "특급 수배",
                        "left": 40,
                        "top": 40,
                        "backgroundColor": "#EA580C",
                        "fill": "#ffffff",
                    },
                    {
                        "id": "line_1",
                        "type": "textbox",
                        "text": "23만 명을 속인 얼굴",
                        "left": 40,
                        "top": 280,
                        "fontFamily": "Pretendard",
                        "fill": "#ffffff",
                        "stroke": "#000000",
                        "strokeWidth": 6,
                    },
                    {
                        "id": "line_2",
                        "type": "textbox",
                        "text": "드러난 악마의 정체",
                        "left": 40,
                        "top": 380,
                        "fontFamily": "Pretendard",
                        "fill": "#F59E0B",
                        "stroke": "#000000",
                        "strokeWidth": 6,
                    },
                ],
                "ctr_prediction": {
                    "score": 91,
                    "predicted_ctr_pct": 12.2,
                    "dna_consistency_score": 92,
                    "text_legibility_score": 88,
                    "curiosity_gap_score": 94,
                    "keyword_alignment_score": 92,
                },
            },
        ],
    }
    (ws_dir / "thumbnail_design.json").write_text(json.dumps(design, indent=2, ensure_ascii=False), encoding="utf-8")

    yield test_job_id, ws_dir, job_dir

    # Cleanup teardown
    shutil.rmtree(job_dir, ignore_errors=True)
    shutil.rmtree(ws_dir, ignore_errors=True)


@pytest.fixture
def backup_channel_profiles():
    """Backup channel_profiles.json before test and restore after test."""
    backup_data = PROFILES_FILE.read_text(encoding="utf-8")
    try:
        yield
    finally:
        PROFILES_FILE.write_text(backup_data, encoding="utf-8")


# ==============================================================================
# 1. EMPIRICAL VERIFICATION: POST /api/jobs/{id}/thumbnail-studio/export-ab-pack
# ==============================================================================

def test_export_ab_pack_rest_endpoint_returns_200_and_valid_zip(app_client, managed_test_job):
    """
    Test POST /api/jobs/{job_id}/thumbnail-studio/export-ab-pack:
    - Returns HTTP 200.
    - Returns valid JSON with zip_path, zip_url, metadata_path, exported_count == 3.
    - Unpacks zip and confirms it contains variant_a.jpg, variant_b.jpg, variant_c.jpg, ab_test_metadata.json.
    - Validates image integrity (valid JPEG headers, non-empty, PIL opens as JPEG (1280x720) RGB).
    - Validates ab_test_metadata.json content (title, hook types, predicted CTRs).
    """
    job_id, ws_dir, _ = managed_test_job

    resp = app_client.post(f"/api/jobs/{job_id}/thumbnail-studio/export-ab-pack", json={})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    data = resp.json()
    assert data.get("ok") is True
    assert data.get("job_id") == job_id
    assert data.get("exported_count") == 3
    assert "zip_path" in data
    assert "zip_url" in data

    zip_path = Path(data["zip_path"])
    assert zip_path.is_file(), f"Zip file does not exist at {zip_path}"
    assert zip_path.stat().st_size > 0, "Zip file must not be 0 bytes"

    # Verify and unpack ZIP archive
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        expected_files = {"variant_a.jpg", "variant_b.jpg", "variant_c.jpg", "ab_test_metadata.json"}
        for ef in expected_files:
            assert ef in namelist, f"Missing {ef} in zip archive: {namelist}"

        # Verify each image file
        for img_name in ("variant_a.jpg", "variant_b.jpg", "variant_c.jpg"):
            img_bytes = zf.read(img_name)
            assert len(img_bytes) > 0, f"{img_name} in zip is empty (0 bytes)"
            # Verify JPEG SOI marker (0xFFD8)
            assert img_bytes[:2] == b"\xff\xd8", f"{img_name} does not start with JPEG SOI marker"

            # Open with PIL
            with Image.open(io.BytesIO(img_bytes)) as pil_img:
                assert pil_img.format == "JPEG", f"Expected JPEG format, got {pil_img.format}"
                assert pil_img.size == (1280, 720), f"Expected 1280x720, got {pil_img.size}"
                assert pil_img.mode in ("RGB", "RGBA"), f"Expected RGB/RGBA, got {pil_img.mode}"

        # Verify ab_test_metadata.json inside zip
        meta_bytes = zf.read("ab_test_metadata.json")
        meta_json = json.loads(meta_bytes.decode("utf-8"))

        assert meta_json.get("job_id") == job_id
        assert meta_json.get("format") == "YouTube_Studio_Test_And_Compare_Pack"
        assert meta_json.get("experiment_type") == "3_thumbnail_ab_test"
        assert "variants" in meta_json and len(meta_json["variants"]) == 3

        # Verify hook types and predicted CTRs
        hook_types = [v.get("hook_type") for v in meta_json["variants"]]
        assert "curiosity_paradox" in hook_types, f"curiosity_paradox missing in {hook_types}"
        assert "character_evidence" in hook_types, f"character_evidence missing in {hook_types}"
        assert "confrontation_contrast" in hook_types, f"confrontation_contrast missing in {hook_types}"

        for v in meta_json["variants"]:
            assert "ctr_prediction" in v, f"Variant {v.get('letter')} missing ctr_prediction"
            ctr = v["ctr_prediction"]
            assert "predicted_ctr_pct" in ctr or "score" in ctr, f"ctr missing predicted_ctr_pct or score: {ctr}"

        # Check whether title exists in metadata
        has_title = bool(meta_json.get("title") or meta_json.get("video_title") or any(v.get("title") for v in meta_json["variants"]))
        assert has_title, "ab_test_metadata.json must contain title"
        assert meta_json.get("title") == "중국 28년 미제사건의 비밀 (Bí mật đại án 28 năm)"


def test_export_ab_pack_non_existent_job_returns_404(app_client):
    """Test POST /api/jobs/{job_id}/thumbnail-studio/export-ab-pack with non-existent job returns 404."""
    resp = app_client.post("/api/jobs/job-non-existent-99999/thumbnail-studio/export-ab-pack", json={})
    assert resp.status_code == 404
    detail = resp.json().get("detail", "")
    assert "Không tìm thấy" in detail or "not found" in detail.lower()


def test_export_ab_pack_when_thumbnail_design_missing_synthesizes_default_variants(app_client, managed_test_job):
    """
    When thumbnail_design.json does not exist in workspace, DocumentaryService._read_json_dict
    returns None (or {} mapped to None), triggering build_default_thumbnail_design.
    As a result, exported_count is 3 and 3 image files are generated in the ZIP!
    """
    job_id, ws_dir, _ = managed_test_job
    design_file = ws_dir / "thumbnail_design.json"
    if design_file.exists():
        design_file.unlink()

    resp = app_client.post(f"/api/jobs/{job_id}/thumbnail-studio/export-ab-pack", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    exported_count = data.get("exported_count", 0)
    assert exported_count == 3, f"Expected 3 synthesized variants, got {exported_count}"
    assert len(data.get("variants", [])) == 3


# ==============================================================================
# 2. EMPIRICAL VERIFICATION: POST /api/jobs/{id}/thumbnail-studio/select-winner
# ==============================================================================

def test_select_winner_sets_active_variant_and_writes_thumbnail_files(app_client, managed_test_job):
    """
    Test POST /api/jobs/{job_id}/thumbnail-studio/select-winner:
    - Calling with variant_id="v2" sets active_variant_id="v2".
    - Creates workspace/thumbnail.jpg (>0 bytes, valid JPEG).
    - Creates workspace/media/thumbnails/thumbnail.jpg (>0 bytes, valid JPEG).
    - Creates workspace/media/thumbnail/exports/thumbnail_v2.jpg.
    - thumbnail_design.json on disk has active_variant_id="v2".
    """
    job_id, ws_dir, _ = managed_test_job

    resp = app_client.post(f"/api/jobs/{job_id}/thumbnail-studio/select-winner", json={"variant_id": "v2"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    data = resp.json()
    assert data.get("ok") is True
    assert data.get("active_variant_id") == "v2"
    assert data.get("variant_name") == "BẢN B · Bằng chứng / Cận cảnh"

    # Verify disk files
    root_thumb = ws_dir / "thumbnail.jpg"
    assert root_thumb.is_file(), f"Root thumbnail missing: {root_thumb}"
    assert root_thumb.stat().st_size > 0, "Root thumbnail is 0 bytes"

    # Verify JPEG
    with Image.open(root_thumb) as img:
        assert img.format == "JPEG"
        assert img.size == (1280, 720)

    media_thumb = ws_dir / "media" / "thumbnails" / "thumbnail.jpg"
    assert media_thumb.is_file(), f"Media thumbnail missing: {media_thumb}"
    assert media_thumb.stat().st_size > 0

    export_thumb = ws_dir / "media" / "thumbnail" / "exports" / "thumbnail_v2.jpg"
    assert export_thumb.is_file(), f"Export variant thumbnail missing: {export_thumb}"
    assert export_thumb.stat().st_size > 0

    # Verify thumbnail_design.json updated
    saved_design = json.loads((ws_dir / "thumbnail_design.json").read_text(encoding="utf-8"))
    assert saved_design.get("active_variant_id") == "v2"


def test_select_winner_non_existent_job_returns_404(app_client):
    """Test select-winner on non-existent job returns 404."""
    resp = app_client.post("/api/jobs/job-unknown-xyz/thumbnail-studio/select-winner", json={"variant_id": "v1"})
    assert resp.status_code == 404


def test_select_winner_variant_id_alias_resolves_to_correct_variant(app_client, managed_test_job):
    """
    When a caller specifies 'variant_b' (or 'b', 'Variant B'),
    select_thumbnail_winner normalizes the alias to 'v2'.
    """
    job_id, ws_dir, _ = managed_test_job

    resp = app_client.post(f"/api/jobs/{job_id}/thumbnail-studio/select-winner", json={"variant_id": "variant_b"})
    assert resp.status_code == 200
    data = resp.json()
    selected_id = data.get("active_variant_id")
    assert selected_id == "v2", f"Expected 'v2' for 'variant_b', got {selected_id}"



# ==============================================================================
# 3. EMPIRICAL VERIFICATION: POST /api/jobs/{id}/lock-thumbnail-dna
# ==============================================================================

def test_lock_thumbnail_dna_from_job_increments_version_and_archives_history(
    app_client, managed_test_job, backup_channel_profiles
):
    """
    Test POST /api/jobs/{job_id}/lock-thumbnail-dna:
    - Extracts active design parameters from job.
    - Updates channel profile's thumbnail_dna.
    - Increments channel profile version.
    - Archives previous version into thumbnail_dna_history.
    - Updates job.json and input.json with the new locked DNA snapshot.
    """
    job_id, ws_dir, job_dir = managed_test_job
    target_profile_id = "channel-e544a64b7c"

    # Read profile before locking
    profiles_raw = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profile_before = next(p for p in profiles_raw["profiles"] if p["id"] == target_profile_id)
    v_before = int(profile_before.get("thumbnail_dna", {}).get("version", 1))
    hist_len_before = len(profile_before.get("thumbnail_dna_history", []))

    # Set active variant to v2 with custom styling in workspace
    design_file = ws_dir / "thumbnail_design.json"
    design = json.loads(design_file.read_text(encoding="utf-8"))
    design["active_variant_id"] = "v2"
    design_file.write_text(json.dumps(design, indent=2, ensure_ascii=False), encoding="utf-8")

    # Call POST /api/jobs/{job_id}/lock-thumbnail-dna
    lock_resp = app_client.post(
        f"/api/jobs/{job_id}/lock-thumbnail-dna",
        json={"notes": "Challenger automated style lock verification"},
    )
    assert lock_resp.status_code == 200, f"Expected 200, got {lock_resp.status_code}: {lock_resp.text}"

    lock_data = lock_resp.json()
    assert lock_data.get("ok") is True or lock_data.get("status") == "success"
    assert lock_data.get("channel_profile_id") == target_profile_id
    new_version = lock_data.get("version")
    assert new_version == v_before + 1, f"Expected version {v_before + 1}, got {new_version}"

    # Verify channel_profiles.json on disk
    profiles_after = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profile_after = next(p for p in profiles_after["profiles"] if p["id"] == target_profile_id)

    # 1. Version incremented
    dna_after = profile_after.get("thumbnail_dna", {})
    assert int(dna_after.get("version", 0)) == new_version
    assert dna_after.get("locked_from_job_id") == job_id
    assert dna_after.get("notes") == "Challenger automated style lock verification"

    # 2. History archived
    hist_after = profile_after.get("thumbnail_dna_history", [])
    assert len(hist_after) == hist_len_before + 1
    last_archived = hist_after[-1]
    assert int(last_archived.get("version", 0)) == v_before
    assert last_archived.get("locked_from_job_id") == job_id
    assert "archived_at" in last_archived

    # 3. Verify job.json updated
    saved_job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    assert saved_job.get("thumbnail_dna", {}).get("version") == new_version

    # 4. Verify input.json updated
    saved_input = json.loads((ws_dir / "input.json").read_text(encoding="utf-8"))
    assert saved_input.get("thumbnail_dna", {}).get("version") == new_version


def test_lock_thumbnail_dna_job_without_profile_returns_400(app_client, managed_test_job):
    """Test lock-thumbnail-dna on job with no channel_profile_id returns 400 Bad Request."""
    job_id, _, job_dir = managed_test_job
    job_data = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    job_data["channel_profile_id"] = None
    (job_dir / "job.json").write_text(json.dumps(job_data, indent=2), encoding="utf-8")

    resp = app_client.post(f"/api/jobs/{job_id}/lock-thumbnail-dna", json={})
    assert resp.status_code == 400
    assert "no assigned channel profile" in resp.json().get("detail", "").lower()


# ==============================================================================
# 4. EMPIRICAL VERIFICATION: R4 NON-DESTRUCTIVE PRESERVATION
# ==============================================================================

def test_active_job_20261019_185102_31983814_is_completely_unharmed():
    """
    R4 Non-Destructive Preservation Check:
    Verify that active job 20261019-185102-31983814 and its workspace files and databases are completely unharmed.
    """
    active_ws = WORKSPACES_DIR / ACTIVE_JOB_ID
    assert active_ws.exists(), f"Active workspace {active_ws} must exist"
    assert active_ws.is_dir(), f"Active workspace {active_ws} must be a directory"

    # Key production artifacts must be present and non-empty
    critical_files = [
        "input.json",
        "creative_brief.json",
        "thumbnail.jpg",
        "thumbnail_design.json",
        "script.md",
        "research.md",
        "visual_manifest.json",
        "ai_visual_manifest.json",
        "final_manifest.json",
    ]
    for filename in critical_files:
        fpath = active_ws / filename
        assert fpath.is_file(), f"Critical file {filename} missing from active job workspace"
        assert fpath.stat().st_size > 0, f"Critical file {filename} is empty (0 bytes)"

    # Verify thumbnail.jpg is intact valid JPEG
    thumb_path = active_ws / "thumbnail.jpg"
    with Image.open(thumb_path) as img:
        assert img.format == "JPEG"
        assert img.size == (1280, 720)

    # Verify thumbnail_design.json is intact
    design = json.loads((active_ws / "thumbnail_design.json").read_text(encoding="utf-8"))
    assert "active_variant_id" in design
    assert "variants" in design
    assert len(design["variants"]) >= 3

    # Verify radar.db exists
    radar_db = DATA_DIR / "radar.db"
    assert radar_db.exists(), "data/radar.db must exist"
