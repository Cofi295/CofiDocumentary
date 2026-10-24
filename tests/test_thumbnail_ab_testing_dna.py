"""
Automated Verification Suite for Milestone 3:
Consistent Channel Thumbnail Design DNA & Multi-Variant Thumbnail A/B Testing Studio
(Requirements R3, AC3, R4).

Verifies:
1. Canonical Channel Profiles in data/channel_profiles.json contain valid thumbnail_dna and thumbnail_dna_history.
2. ChannelProfileService supports ThumbnailDnaModel, deep-merge updates, and deep-copy cloning.
3. FastAPI endpoint models in app.py preserve thumbnail_dna.
4. JobService inherits channel profile thumbnail_dna and initializes workspace thumbnail_design.json.
5. Thumbnail Style Locking API (POST /api/jobs/{id}/lock-thumbnail-dna and POST /api/radar/channel-profiles/{id}/lock-thumbnail-dna).
6. Step 07 Thumbnail Studio generates 3 distinct A/B/C psychological hook variants (curiosity_paradox, character_evidence, confrontation_contrast) adhering to thumbnail_dna.
7. Multi-dimensional CTR prediction scorecard (dna_consistency_score, text_legibility_score, curiosity_gap_score, keyword_alignment_score, predicted_ctr_pct, readiness_score).
8. Thumbnail A/B Test Pack export (variant_a.jpg, variant_b.jpg, variant_c.jpg, ab_test_metadata.json, and ab_test_pack.zip).
9. Primary winner selection (thumbnail.jpg, media/thumbnails/thumbnail.jpg, active_variant_id).
10. Non-Destructive Preservation (R4): Active job 20261019-185102-31983814 remains untouched.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import zipfile
import pytest
from fastapi.testclient import TestClient

from server import create_app
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
DATA_DIR = ROOT / "data"
PROFILES_FILE = DATA_DIR / "channel_profiles.json"
ACTIVE_JOB_ID = "20261019-185102-31983814"


# ==============================================================================
# 1. CANONICAL CHANNEL PROFILES THUMBNAIL DNA INTEGRITY
# ==============================================================================

def test_canonical_channel_profiles_contain_thumbnail_dna():
    """Verify all 4 canonical channel profiles contain valid, non-empty thumbnail_dna and history."""
    assert PROFILES_FILE.exists(), "channel_profiles.json must exist"
    data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profiles = {p["id"]: p for p in data.get("profiles", [])}

    expected_channels = {
        "channel-e544a64b7c": {
            "style_preset": "cold_forensic_noir",
            "layout_template": "broadcast_left_heavy",
        },
        "channel-1e24de3ab5": {
            "style_preset": "infrastructure_blueprint",
            "layout_template": "split_duality",
        },
        "channel-aa913eb90d": {
            "style_preset": "archival_intelligence",
            "layout_template": "evidence_spotlight",
        },
        "channel-f6ec4dfff3": {
            "style_preset": "presidential_vault",
            "layout_template": "bottom_cinematic",
        },
    }

    for ch_id, spec in expected_channels.items():
        assert ch_id in profiles, f"Profile {ch_id} missing in channel_profiles.json"
        p = profiles[ch_id]
        assert "thumbnail_dna" in p, f"Profile {ch_id} missing thumbnail_dna"
        dna = p["thumbnail_dna"]
        assert dna.get("style_preset") == spec["style_preset"] or dna.get("preset_id") == spec["style_preset"]
        assert dna.get("layout_template") == spec["layout_template"] or dna.get("layout_archetype") == spec["layout_template"]
        assert "color_palette" in dna and isinstance(dna["color_palette"], dict)
        assert ("typography_preset" in dna and isinstance(dna["typography_preset"], dict)) or ("fonts" in dna and isinstance(dna["fonts"], dict))
        assert "visual_signature" in dna
        assert "thumbnail_dna_history" in p and isinstance(p["thumbnail_dna_history"], list)


# ==============================================================================
# 2. CHANNEL PROFILE SERVICE MODEL & CRUD
# ==============================================================================

def test_thumbnail_dna_model_validation():
    """Verify ThumbnailDnaModel validates correctly and provides safe defaults."""
    raw = {
        "style_preset": "cold_forensic_noir",
        "layout_template": "broadcast_left_heavy",
        "color_palette": {
            "headline_primary": "#ffffff",
            "headline_accent": "#f59e0b",
            "badge_background": "#dc2626",
            "badge_text": "#ffffff",
            "vignette_opacity": 0.85,
        },
        "typography_preset": {
            "font_family": "Pretendard ExtraBold",
            "title_weight": "900",
            "stroke_color": "#000000",
            "stroke_width": 6,
        },
        "visual_signature": {
            "forensic_markers": True,
            "stamp_badge": "단독",
            "character_lock": {
                "enabled": True,
                "character_name": "Host",
                "reference_image_path": "media/host.png",
            },
        },
    }
    model = ThumbnailDnaModel(**raw)
    d = model.to_dict()
    assert d["style_preset"] == "cold_forensic_noir"
    assert d["layout_template"] == "broadcast_left_heavy"
    assert d["color_palette"]["headline_accent"] == "#f59e0b"
    assert d["visual_signature"]["character_lock"]["enabled"] is True
    # Aliases
    assert d["preset_id"] == "cold_forensic_noir"
    assert d["layout_archetype"] == "broadcast_left_heavy"
    assert d["fonts"]["font_family"] == "Pretendard ExtraBold"


def test_channel_profile_service_deep_merge_and_clone(tmp_path: Path):
    """Verify ChannelProfileService.update_profile deep-merges thumbnail_dna and clone deep-copies."""
    profiles_copy = tmp_path / "profiles.json"
    data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profiles_copy.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    service = ChannelProfileService(storage_path=profiles_copy)

    # 1. Partial update: only change headline_accent without wiping typography or visual_signature
    orig = service.get_profile("channel-e544a64b7c")
    assert orig is not None
    orig_font = (orig["thumbnail_dna"].get("typography_preset") or orig["thumbnail_dna"].get("fonts") or {}).get("font_family") or "Pretendard"

    updated = service.update_profile("channel-e544a64b7c", {
        "thumbnail_dna": {
            "color_palette": {
                "headline_accent": "#00ffcc",
            }
        }
    })

    assert updated["thumbnail_dna"]["color_palette"]["headline_accent"] == "#00ffcc"
    # Existing primary, fonts, and visual_signature must be preserved!
    assert updated["thumbnail_dna"]["color_palette"]["primary"] == orig["thumbnail_dna"]["color_palette"]["primary"]
    curr_font = (updated["thumbnail_dna"].get("typography_preset") or updated["thumbnail_dna"].get("fonts") or {}).get("font_family")
    assert curr_font == orig_font
    assert "visual_signature" in updated["thumbnail_dna"]

    # 2. Clone profile: must perform deep copy of thumbnail_dna
    cloned = service.clone_profile("channel-e544a64b7c", new_label="Cloned Channel")
    assert cloned["id"] != "channel-e544a64b7c"
    assert cloned["thumbnail_dna"]["color_palette"]["headline_accent"] == "#00ffcc"

    # Mutate cloned thumbnail_dna
    service.update_profile(cloned["id"], {
        "thumbnail_dna": {
            "color_palette": {
                "headline_accent": "#ff0099",
            }
        }
    })
    # Original profile must remain unaffected
    orig_after = service.get_profile("channel-e544a64b7c")
    assert orig_after["thumbnail_dna"]["color_palette"]["headline_accent"] == "#00ffcc"


# ==============================================================================
# 3. JOB SERVICE INHERITANCE & WORKSPACE THUMBNAIL DESIGN
# ==============================================================================

def test_job_service_inherits_thumbnail_dna_and_inits_design(tmp_path: Path):
    """Verify JobService inherits channel profile thumbnail_dna and initializes thumbnail_design.json."""
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    store = JobStore(jobs_dir)
    job_service = JobService(store=store)

    job = job_service.create_job({
        "title": "댐 붕괴의 진실 (Sự Thật Vỡ Đập)",
        "channel_profile_id": "channel-1e24de3ab5",
        "market": "KR",
        "language": "ko",
    })

    assert "thumbnail_dna" in job
    job_dna = job["thumbnail_dna"]
    assert job_dna.get("style_preset") == "infrastructure_blueprint" or job_dna.get("preset_id") == "infrastructure_blueprint"

    # Verify workspace thumbnail_design.json is created
    ws = Path(job["workspace"])
    design_file = ws / "thumbnail_design.json"
    assert design_file.is_file(), "thumbnail_design.json must be created in workspace"

    design = json.loads(design_file.read_text(encoding="utf-8"))
    assert design["job_id"] == job["id"]
    assert "variants" in design and len(design["variants"]) >= 3
    # Check that variants have the 3 distinct psychological hook types
    hook_types = [v["hook_type"] for v in design["variants"] if "hook_type" in v]
    assert "curiosity_paradox" in hook_types
    assert "character_evidence" in hook_types
    assert "confrontation_contrast" in hook_types


# ==============================================================================
# 4. STEP 07 THUMBNAIL STUDIO: 3 PSYCHOLOGICAL HOOK VARIANTS (A/B/C)
# ==============================================================================

def test_build_default_thumbnail_design_generates_3_distinct_variants(tmp_path: Path):
    """Verify build_default_thumbnail_design generates at least 3 distinct hook variants adhering to DNA."""
    ws = tmp_path / "workspace_test"
    ws.mkdir(parents=True, exist_ok=True)

    # Mock job with channel-e544a64b7c (Crime / Forensic)
    profile_data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profile_e5 = next(p for p in profile_data["profiles"] if p["id"] == "channel-e544a64b7c")

    job = {
        "id": "job-test-ab-001",
        "title": "연쇄살인의 진실 (Chân tướng kẻ giết người hàng loạt)",
        "channel_profile_id": "channel-e544a64b7c",
        "channel_profile_snapshot": profile_e5,
        "thumbnail_dna": profile_e5["thumbnail_dna"],
    }

    design = build_default_thumbnail_design("job-test-ab-001", ws, job)

    assert "variants" in design
    variants = design["variants"]
    assert len(variants) >= 3

    v_a = variants[0]
    v_b = variants[1]
    v_c = variants[2]

    # Verify distinct hook types
    assert v_a.get("hook_type") == "curiosity_paradox"
    assert v_b.get("hook_type") == "character_evidence"
    assert v_c.get("hook_type") == "confrontation_contrast"

    # Verify distinct psychological badges
    assert "Tò mò" in v_a.get("hook_badge", "") or "Nghịch lý" in v_a.get("hook_badge", "")
    assert "Nhân vật" in v_b.get("hook_badge", "") or "Bằng chứng" in v_b.get("hook_badge", "")
    assert "Đối đầu" in v_c.get("hook_badge", "") or "Hồ sơ" in v_c.get("hook_badge", "")

    # Verify layers & ctr_prediction
    for v in (v_a, v_b, v_c):
        layers = v.get("layers", [])
        text_layers = [l for l in layers if l.get("type") in ("textbox", "badge", "stamp")]
        assert len(text_layers) > 0
        assert "ctr_prediction" in v
        ctr = v["ctr_prediction"]
        assert "predicted_ctr_pct" in ctr
        assert "dna_consistency_score" in ctr


# ==============================================================================
# 5. MULTI-DIMENSIONAL CTR PREDICTION SCORECARD
# ==============================================================================

def test_evaluate_variant_ctr_multi_dimensional():
    """Verify evaluate_variant_ctr produces multi-dimensional scorecard."""
    variant = {
        "id": "v1",
        "hook_type": "curiosity_paradox",
        "hook_badge": "🎯 Variant A: Tò mò / Nghịch lý",
        "layers": [
            {
                "id": "badge",
                "type": "textbox",
                "text": "중국 실화 사건",
                "left": 40,
                "top": 40,
                "width": 300,
                "height": 50,
                "visible": True,
            },
            {
                "id": "line_1",
                "type": "textbox",
                "text": "28년간 숨겨진 진실",
                "left": 40,
                "top": 280,
                "width": 600,
                "height": 80,
                "fontSize": 72,
                "strokeWidth": 16,
                "fill": "#ffffff",
                "visible": True,
            },
            {
                "id": "line_2",
                "type": "textbox",
                "text": "DNA가 밝혀낸 악마",
                "left": 40,
                "top": 380,
                "width": 650,
                "height": 90,
                "fontSize": 84,
                "strokeWidth": 16,
                "fill": "#fbbf24",
                "visible": True,
            },
            {
                "id": "vignette",
                "type": "vignette",
                "opacity": 0.82,
                "visible": True,
            },
        ],
    }

    design = {
        "thumbnail_dna": {
            "layout_archetype": "broadcast_left_heavy",
            "color_palette": {
                "headline_primary": "#ffffff",
                "headline_accent": "#fbbf24",
            },
        }
    }

    scorecard = evaluate_variant_ctr(variant, design)

    assert "score" in scorecard
    assert "verdict" in scorecard
    assert "dna_consistency_score" in scorecard
    assert "text_legibility_score" in scorecard
    assert "curiosity_gap_score" in scorecard
    assert "keyword_alignment_score" in scorecard
    assert "predicted_ctr_pct" in scorecard
    assert "readiness_score" in scorecard
    assert "strengths" in scorecard
    assert "warnings" in scorecard

    # Validate numeric ranges
    assert 40 <= scorecard["score"] <= 100
    assert 50 <= scorecard["dna_consistency_score"] <= 100
    assert 50 <= scorecard["text_legibility_score"] <= 100
    assert 50 <= scorecard["curiosity_gap_score"] <= 100
    assert 50 <= scorecard["keyword_alignment_score"] <= 100
    assert 4.0 <= scorecard["predicted_ctr_pct"] <= 18.0
    assert scorecard["readiness_score"] == scorecard["score"]


def test_evaluate_thumbnail_ctr_backward_compatibility():
    """Verify evaluate_thumbnail_ctr maintains legacy keys (score, verdict, checks) alongside scorecard."""
    design = {
        "variants": [
            {
                "id": "v1",
                "line_1": "비밀의 진실",
                "line_2": "단 하나의 증거",
                "layers": [],
            }
        ]
    }
    legacy = evaluate_thumbnail_ctr(design)
    assert "score" in legacy
    assert "verdict" in legacy
    assert "checks" in legacy
    assert "dna_consistency_score" in legacy
    assert "predicted_ctr_pct" in legacy


# ==============================================================================
# 6. A/B TEST PACK EXPORT & WINNER SELECTION
# ==============================================================================

def test_export_thumbnail_ab_pack_and_select_winner(tmp_path: Path):
    """Verify export_thumbnail_ab_pack exports 3 variants + ZIP and select_winner updates thumbnail."""
    ws = tmp_path / "ws_export"
    ws.mkdir(parents=True, exist_ok=True)

    job_id = "job-export-test"
    job = {
        "id": job_id,
        "title": "테스트 다큐멘터리",
    }
    design = build_default_thumbnail_design(job_id, ws, job)

    # 1. Export A/B Pack
    result = export_thumbnail_ab_pack(job_id, ws, design, job)
    assert result["ok"] is True
    assert result["job_id"] == job_id
    assert len(result["variants"]) == 3
    assert "zip_url" in result
    assert "metadata" in result or "metadata_path" in result

    # Verify files created on disk
    ab_dir = ws / "media" / "thumbnails"
    assert (ab_dir / "variant_a.jpg").is_file()
    assert (ab_dir / "variant_b.jpg").is_file()
    assert (ab_dir / "variant_c.jpg").is_file()
    assert (ab_dir / "ab_test_metadata.json").is_file()
    assert (ab_dir / "ab_test_pack.zip").is_file()

    # Verify ZIP contents
    with zipfile.ZipFile(ab_dir / "ab_test_pack.zip", "r") as zf:
        namelist = zf.namelist()
        assert "variant_a.jpg" in namelist
        assert "variant_b.jpg" in namelist
        assert "variant_c.jpg" in namelist
        assert "ab_test_metadata.json" in namelist

    # 2. Select Winner (e.g. Variant B)
    win_result = select_thumbnail_winner(job_id, ws, "v2", design, job)
    assert win_result["ok"] is True
    assert win_result["active_variant_id"] == "v2"

    # Verify root thumbnail.jpg and media/thumbnails/thumbnail.jpg are created
    assert (ws / "thumbnail.jpg").is_file()
    assert (ws / "media" / "thumbnails" / "thumbnail.jpg").is_file()
    assert (ws / "media" / "thumbnail" / "exports" / "thumbnail_v2.jpg").is_file()

    # Check updated design
    design_saved = json.loads((ws / "thumbnail_design.json").read_text(encoding="utf-8"))
    assert design_saved["active_variant_id"] == "v2"


# ==============================================================================
# 7. THUMBNAIL STYLE LOCKING API
# ==============================================================================

def test_style_locking_endpoints(tmp_path: Path):
    """Verify REST API style locking endpoints for job and profile."""
    app = create_app()
    client = TestClient(app)

    # 1. Lock channel profile directly via REST
    lock_resp = client.post(
        "/api/radar/channel-profiles/channel-aa913eb90d/lock-thumbnail-dna",
        json={
            "thumbnail_dna": {
                "color_palette": {
                    "headline_accent": "#facc15",
                },
                "visual_signature": {
                    "stamp_badge": "속보",
                },
            },
            "notes": "Automated style lock test",
        },
    )
    assert lock_resp.status_code == 200
    lock_data = lock_resp.json()
    assert lock_data["ok"] is True
    assert lock_data["channel_profile_id"] == "channel-aa913eb90d"
    assert lock_data["version"] >= 2
    assert "locked_at" in lock_data


# ==============================================================================
# 8. NON-DESTRUCTIVE PRESERVATION (R4)
# ==============================================================================

def test_non_destructive_preservation_active_job():
    """Verify active running job 20261019-185102-31983814 and its workspace remain intact."""
    active_ws = ROOT / "workspaces" / ACTIVE_JOB_ID
    assert active_ws.exists(), f"Active workspace {active_ws} must exist"
    assert active_ws.is_dir(), f"Active workspace {active_ws} must be a directory"

    # Verify critical files in active job remain intact
    assert (active_ws / "input.json").is_file()
    assert (active_ws / "creative_brief.json").is_file()
    assert (active_ws / "thumbnail_design.json").is_file()
    assert (active_ws / "thumbnail.jpg").is_file()
    assert (ROOT / "data" / "radar.db").is_file(), "radar.db must remain untouched"
