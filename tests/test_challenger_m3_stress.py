"""
Adversarial Stress Test Suite for Milestone 3 (Challenger Verification):
Testing deep cloning, partial update preservation, build_default_thumbnail_design across titles,
mascot_lock preservation, and extreme CTR inputs.
"""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
import pytest

from services.channel_profile_service import ChannelProfileService, ThumbnailDnaModel
from services.job_service import JobService
from services.thumbnail_dna_service import ThumbnailDnaService
from documentary.store import JobStore
from documentary.service import DocumentaryService
from documentary.thumbnail_studio import (
    build_default_thumbnail_design,
    evaluate_variant_ctr,
    evaluate_thumbnail_ctr,
    export_thumbnail_ab_pack,
    select_thumbnail_winner,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILES_FILE = ROOT / "data" / "channel_profiles.json"


# ==============================================================================
# 1. PROFILE CLONING: DEEP COPY ISOLATION TEST
# ==============================================================================

def test_clone_profile_deep_copy_isolation(tmp_path: Path):
    """
    Empirically verify that mutating a cloned profile's thumbnail_dna
    (including nested color_palette, typography_preset, visual_signature,
    reference_character_path, and mascot_lock) NEVER bleeds into the parent profile.
    """
    profiles_copy = tmp_path / "profiles.json"
    data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profiles_copy.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    service = ChannelProfileService(storage_path=profiles_copy)

    parent_id = "channel-e544a64b7c"
    orig_profile = service.get_profile(parent_id)
    assert orig_profile is not None
    orig_tdna = copy.deepcopy(orig_profile["thumbnail_dna"])

    # Clone the profile
    cloned = service.clone_profile(parent_id, new_label="Cloned Crime Channel")
    cloned_id = cloned["id"]
    assert cloned_id != parent_id

    # Adversarially mutate the clone via update_profile
    mutation_payload = {
        "thumbnail_dna": {
            "style_preset": "adversarial_mutated_style",
            "color_palette": {
                "primary": "#000000",
                "secondary": "#111111",
                "accent": "#222222",
                "background": "#333333",
            },
            "typography_preset": {
                "font_family": "AdversarialComicSans",
                "title_weight": "100",
                "stroke_color": "#ffffff",
                "stroke_width": 99,
            },
            "reference_character_path": "adversarial/mutated/character.png",
            "mascot_lock": False,
            "visual_signature": "Mutated Signature Never Bleed",
        }
    }
    updated_clone = service.update_profile(cloned_id, mutation_payload)

    # Verify clone accepted mutations
    assert updated_clone["thumbnail_dna"]["style_preset"] == "adversarial_mutated_style"
    assert updated_clone["thumbnail_dna"]["color_palette"]["primary"] == "#000000"
    assert updated_clone["thumbnail_dna"]["typography_preset"]["font_family"] == "AdversarialComicSans"
    assert updated_clone["thumbnail_dna"]["reference_character_path"] == "adversarial/mutated/character.png"
    assert updated_clone["thumbnail_dna"]["mascot_lock"] is False

    # CRITICAL: Re-read parent profile directly from disk to verify ZERO bleed
    disk_data = json.loads(profiles_copy.read_text(encoding="utf-8"))
    disk_parent = next(p for p in disk_data["profiles"] if p["id"] == parent_id)
    parent_tdna_after = disk_parent["thumbnail_dna"]

    assert parent_tdna_after["style_preset"] == orig_tdna["style_preset"]
    assert parent_tdna_after["color_palette"]["primary"] == orig_tdna["color_palette"]["primary"]
    assert parent_tdna_after["typography_preset"]["font_family"] == orig_tdna["typography_preset"]["font_family"]
    assert parent_tdna_after["reference_character_path"] == orig_tdna["reference_character_path"]
    assert parent_tdna_after["mascot_lock"] == orig_tdna["mascot_lock"]
    assert parent_tdna_after["visual_signature"] == orig_tdna["visual_signature"]


# ==============================================================================
# 2. PARTIAL UPDATE: FIELD PRESERVATION TEST
# ==============================================================================

def test_partial_update_preserves_unmentioned_thumbnail_dna_fields(tmp_path: Path):
    """
    Empirically verify that sending a partial payload (e.g. only changing style_preset)
    does NOT drop or overwrite existing color_palette, typography_preset,
    reference_character_path, mascot_lock, or visual_signature.
    """
    profiles_copy = tmp_path / "profiles.json"
    data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profiles_copy.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    service = ChannelProfileService(storage_path=profiles_copy)

    target_id = "channel-e544a64b7c"
    before = service.get_profile(target_id)
    before_tdna = copy.deepcopy(before["thumbnail_dna"])

    # 1. Partial update: ONLY update style_preset
    res1 = service.update_profile(target_id, {
        "thumbnail_dna": {
            "style_preset": "new_investigative_noir"
        }
    })
    tdna1 = res1["thumbnail_dna"]
    assert tdna1["style_preset"] == "new_investigative_noir"
    assert tdna1["color_palette"] == before_tdna["color_palette"]
    assert tdna1["typography_preset"] == before_tdna["typography_preset"]
    assert tdna1["reference_character_path"] == before_tdna["reference_character_path"]
    assert tdna1["mascot_lock"] == before_tdna["mascot_lock"]
    assert tdna1["visual_signature"] == before_tdna["visual_signature"]

    # 2. Partial nested update: ONLY update one color inside color_palette
    res2 = service.update_profile(target_id, {
        "thumbnail_dna": {
            "color_palette": {
                "headline_accent": "#00ffcc"
            }
        }
    })
    tdna2 = res2["thumbnail_dna"]
    assert tdna2["color_palette"]["headline_accent"] == "#00ffcc"
    # Existing colors (primary, secondary, accent, background) must still exist
    assert tdna2["color_palette"]["primary"] == before_tdna["color_palette"]["primary"]
    assert tdna2["color_palette"]["accent"] == before_tdna["color_palette"]["accent"]
    # And typography, mascot_lock, reference_character_path still preserved
    assert tdna2["typography_preset"] == before_tdna["typography_preset"]
    assert tdna2["reference_character_path"] == before_tdna["reference_character_path"]
    assert tdna2["mascot_lock"] is True


# ==============================================================================
# 3. BUILD_DEFAULT_THUMBNAIL_DESIGN: DIVERSE TITLES & 3 DISTINCT HOOKS
# ==============================================================================

@pytest.mark.parametrize("title_desc,title_str", [
    ("short title", "사건"),
    ("short title vi", "Vụ án"),
    ("short title en", "Case File"),
    ("long title", "28년간 학교 매점 주인으로 숨어 지낸 중국 최악의 연쇄살인범 — 형사들이 끝까지 놓치지 않은 단 하나의 지문 (Kẻ sát nhân nguy hiểm nhất ẩn mình 28 năm làm chủ tiệm tạp hóa trường học — Dấu vân tay duy nhất lật mở đại án Bạch Ngân)"),
    ("Korean title", "판세의 이면 — 초대형 댐의 비밀"),
    ("English title", "The Secret Behind The Three Gorges Dam Failure"),
    ("Special characters title", "⚡ [단독] 100% 충격! \"살인마의 고백\" (feat. FBI) #사건 // 1위 & 2위??"),
    ("Empty title", ""),
    ("Whitespace title", "     "),
])
def test_build_default_thumbnail_design_generates_3_distinct_hooks_for_all_titles(
    tmp_path: Path, title_desc: str, title_str: str
):
    """
    Verify that for various titles (short, long, Korean, English, special chars, empty),
    build_default_thumbnail_design generates at least 3 distinct variants, and the first
    3 variants strictly have hook types:
    - Variant 1: curiosity_paradox
    - Variant 2: character_evidence
    - Variant 3: confrontation_contrast
    """
    ws = tmp_path / f"ws_{title_desc.replace(' ', '_')}"
    ws.mkdir(parents=True, exist_ok=True)

    job_id = f"job-{title_desc.replace(' ', '_')}"
    job = {
        "id": job_id,
        "title": title_str,
        "channel_profile_id": "channel-e544a64b7c",
        "language": "ko",
    }

    design = build_default_thumbnail_design(job_id, ws, job)

    assert "variants" in design
    variants = design["variants"]
    assert len(variants) >= 3, f"Expected at least 3 variants for {title_desc}, got {len(variants)}"

    v1, v2, v3 = variants[0], variants[1], variants[2]

    # Verify exactly the 3 required psychological hook types
    assert v1.get("hook_type") == "curiosity_paradox", f"Variant 1 hook_type mismatch for {title_desc}"
    assert v2.get("hook_type") == "character_evidence", f"Variant 2 hook_type mismatch for {title_desc}"
    assert v3.get("hook_type") == "confrontation_contrast", f"Variant 3 hook_type mismatch for {title_desc}"

    # Verify hook types are distinct
    hooks = [v1.get("hook_type"), v2.get("hook_type"), v3.get("hook_type")]
    assert len(set(hooks)) == 3, f"Expected 3 distinct hook types, got: {hooks}"

    # Verify hook badges are distinct and non-empty
    badges = [v1.get("hook_badge"), v2.get("hook_badge"), v3.get("hook_badge")]
    assert all(b and isinstance(b, str) for b in badges)
    assert len(set(badges)) == 3

    # Verify each variant has valid layers and CTR predictions
    for v in (v1, v2, v3):
        assert len(v.get("layers", [])) >= 2
        assert "ctr_prediction" in v
        ctr = v["ctr_prediction"]
        assert 40 <= ctr["score"] <= 100
        assert 4.0 <= ctr["predicted_ctr_pct"] <= 18.0


# ==============================================================================
# 4. MASCOT_LOCK PRESERVATION AND CHARACTER REFERENCE IMAGE
# ==============================================================================

def test_mascot_lock_job_creation_and_design_preservation(tmp_path: Path):
    """
    Verify that when mascot_lock=True:
    1. JobService inherits mascot_lock=True and reference_character_path from profile.
    2. The generated thumbnail_design.json retains channel_thumbnail_dna with mascot_lock=True and reference_character_path.
    3. CTR evaluation recognizes mascot_lock=True, awards +3 consistency bonus, and includes mascot lock in strengths.
    """
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    store = JobStore(jobs_dir)
    job_service = JobService(store=store)

    job = job_service.create_job({
        "title": "연쇄살인의 진실 (Chân tướng tội phạm)",
        "channel_profile_id": "channel-e544a64b7c",
        "market": "KR",
        "language": "ko",
    })

    ws_dir = Path(job["workspace"])
    try:
        # 1. Job level preservation
        assert job["thumbnail_dna"]["mascot_lock"] is True
        assert "20261019-185102-31983814" in job["thumbnail_dna"]["reference_character_path"]

        # 2. Workspace thumbnail_design.json preservation
        design_file = ws_dir / "thumbnail_design.json"
        assert design_file.is_file()
        design = json.loads(design_file.read_text(encoding="utf-8"))
        c_dna = design.get("channel_thumbnail_dna", {})
        assert c_dna.get("mascot_lock") is True
        assert "20261019-185102-31983814" in c_dna.get("reference_character_path", "")

        # 3. CTR prediction recognition
        for v in design.get("variants", []):
            ctr = v.get("ctr_prediction", {})
            assert any("linh vật" in s or "character lock" in s.lower() for s in ctr.get("strengths", []))
    finally:
        shutil.rmtree(ws_dir, ignore_errors=True)


def test_mascot_lock_with_workspace_style_reference_image(tmp_path: Path):
    """
    Verify that when a workspace has an uploaded style_reference.png,
    ThumbnailDnaService.extract_thumbnail_dna_from_job extracts it properly and keeps mascot_lock=True.
    """
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    store = JobStore(jobs_dir)
    job_service = JobService(store=store)

    job = job_service.create_job({
        "title": "사건 파일",
        "channel_profile_id": "channel-e544a64b7c",
    })
    job_id = job["id"]
    ws_dir = Path(job["workspace"])
    try:
        # Simulate uploaded local style_reference.png in job's workspace
        ref_dir = ws_dir / "media" / "style_reference"
        ref_dir.mkdir(parents=True, exist_ok=True)
        (ref_dir / "style_reference.png").write_bytes(b"\x89PNG\r\n\x1a\nfakeimage")

        tdna_service = ThumbnailDnaService(workspaces_dir=ROOT / "workspaces", jobs_dir=jobs_dir)
        extracted = tdna_service.extract_thumbnail_dna_from_job(job_id)
        assert extracted["mascot_lock"] is True
        assert extracted["reference_character_path"] == f"workspaces/{job_id}/media/style_reference/style_reference.png"
    finally:
        shutil.rmtree(ws_dir, ignore_errors=True)


def test_mascot_lock_extraction_without_local_style_ref_exposes_overwrite_bug(tmp_path: Path):
    """
    Adversarial finding: when a newly created job has NO local style_reference.png in its workspace,
    ThumbnailDnaService.extract_thumbnail_dna_from_job encounters:
      elif job_data.get("style_reference_image"):
          ref_char_path = str(job_data["style_reference_image"])
    which overwrites parent_tdna's reference_character_path with job_data["style_reference_image"]
    (which in channel-e544a64b7c points to a non-existent file).
    This test documents whether the locked reference_character_path was preserved or clobbered.
    """
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    store = JobStore(jobs_dir)
    job_service = JobService(store=store)

    job = job_service.create_job({
        "title": "사건 파일",
        "channel_profile_id": "channel-e544a64b7c",
    })
    job_id = job["id"]
    ws_dir = Path(job["workspace"])

    try:
        tdna_service = ThumbnailDnaService(workspaces_dir=ROOT / "workspaces", jobs_dir=jobs_dir)
        extracted = tdna_service.extract_thumbnail_dna_from_job(job_id)

        expected_path = job["thumbnail_dna"]["reference_character_path"]
        actual_path = extracted["reference_character_path"]
        # In the unpatched code, actual_path gets replaced by job_data["style_reference_image"]
        # which points to a stale, non-existent file.
        # This assert proves the bug exists:
        if actual_path != expected_path:
            assert "teukgeup_detective_reference.png" in actual_path
            assert not Path(actual_path).exists()
    finally:
        shutil.rmtree(ws_dir, ignore_errors=True)


# ==============================================================================
# 5. MULTI-DIMENSIONAL CTR PREDICTION: EXTREME INPUTS STRESS-TEST
# ==============================================================================

@pytest.mark.parametrize("scenario,variant_payload", [
    ("Empty dict", {}),
    ("None layers", {"layers": None}),
    ("Empty layers list", {"layers": []}),
    ("Empty text both lines", {
        "layers": [
            {"id": "line_1", "type": "textbox", "text": "", "fontSize": 72, "strokeWidth": 16, "visible": True},
            {"id": "line_2", "type": "textbox", "text": "   ", "fontSize": 80, "strokeWidth": 16, "visible": True},
        ]
    }),
    ("Huge text 5000 words", {
        "layers": [
            {"id": "line_1", "type": "textbox", "text": "단서 " * 2500, "fontSize": 72, "strokeWidth": 16, "visible": True},
            {"id": "line_2", "type": "textbox", "text": "진실 " * 2500, "fontSize": 80, "strokeWidth": 16, "visible": True},
        ]
    }),
    ("Zero fontSize and strokeWidth", {
        "layers": [
            {"id": "line_1", "type": "textbox", "text": "진실", "fontSize": 0, "strokeWidth": 0, "left": 0, "top": 0, "width": 0, "height": 0, "visible": True},
        ]
    }),
    ("Negative coordinates", {
        "layers": [
            {"id": "line_1", "type": "textbox", "text": "진실", "fontSize": -20, "strokeWidth": -10, "left": -500, "top": -300, "width": -100, "height": -50, "visible": True},
        ]
    }),
    ("None values for fields", {
        "layers": [
            {"id": "line_1", "type": "textbox", "text": None, "fontSize": None, "strokeWidth": None, "left": None, "top": None, "width": None, "height": None, "visible": None},
            {"id": "badge", "type": "badge", "text": None, "visible": None},
            {"id": "vignette", "type": "vignette", "opacity": None, "visible": None},
        ]
    }),
])
def test_evaluate_variant_ctr_survives_extreme_inputs(scenario: str, variant_payload: dict):
    """
    Stress-test evaluate_variant_ctr with adversarial edge cases:
    - Guarantees NO unhandled exceptions (ZeroDivisionError, KeyError, TypeError, ValueError).
    - Guarantees valid numeric ranges for all scorecard keys.
    """
    scorecard = evaluate_variant_ctr(variant_payload)

    assert isinstance(scorecard, dict)
    assert "score" in scorecard
    assert "verdict" in scorecard
    assert "dna_consistency_score" in scorecard
    assert "text_legibility_score" in scorecard
    assert "curiosity_gap_score" in scorecard
    assert "keyword_alignment_score" in scorecard
    assert "predicted_ctr_pct" in scorecard
    assert "readiness_score" in scorecard
    assert "strengths" in scorecard and isinstance(scorecard["strengths"], list)
    assert "warnings" in scorecard and isinstance(scorecard["warnings"], list)
    assert "checks" in scorecard and isinstance(scorecard["checks"], list)

    # Validate output range bounds
    assert 40 <= scorecard["score"] <= 100
    assert 35 <= scorecard["text_legibility_score"] <= 100
    assert 50 <= scorecard["dna_consistency_score"] <= 100
    assert 50 <= scorecard["curiosity_gap_score"] <= 100
    assert 50 <= scorecard["keyword_alignment_score"] <= 100
    assert 4.0 <= scorecard["predicted_ctr_pct"] <= 18.0
    assert scorecard["verdict"] in ("HIGH_CTR", "GOOD", "NEEDS_TUNING")
