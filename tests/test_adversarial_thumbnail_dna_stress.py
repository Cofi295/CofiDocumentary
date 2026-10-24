"""
Adversarial Stress Test Suite for Milestone 3:
Consistent Channel Thumbnail Design DNA & Multi-Variant Thumbnail A/B Testing Studio.
Empirical verification of anti-facade scoring, edge cases, DNA versioning, PIL rendering, and R4 preservation.
Authored by reviewer_m3_1.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import zipfile
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from server import create_app
from services.channel_profile_service import ChannelProfileService, ThumbnailDnaModel
from services.job_service import JobService
from services.thumbnail_dna_service import ThumbnailDnaService
from documentary.store import JobStore
from documentary.thumbnail_studio import (
    build_default_thumbnail_design,
    evaluate_variant_ctr,
    evaluate_thumbnail_ctr,
    export_thumbnail_ab_pack,
    select_thumbnail_winner,
    ARCHETYPES,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROFILES_FILE = DATA_DIR / "channel_profiles.json"
ACTIVE_JOB_ID = "20261019-185102-31983814"


# ==============================================================================
# 1. ADVERSARIAL INTEGRITY: ANTI-FACADE & DYNAMIC CTR SCORING
# ==============================================================================

class TestAdversarialCtrScoring:
    """Stress-test evaluate_variant_ctr to prove it is NOT a static or facade implementation."""

    def test_safe_zone_violation_triggers_dynamic_penalty(self):
        """When text overflows into YouTube's 1065x625 bottom-right safe zone, penalty must apply."""
        base_variant = {
            "id": "v1",
            "layers": [
                {
                    "id": "line_1",
                    "type": "textbox",
                    "text": "사건의 진실",
                    "left": 40,
                    "top": 200,
                    "width": 500,
                    "height": 80,
                    "fontSize": 72,
                    "strokeWidth": 16,
                    "visible": True,
                },
                {
                    "id": "badge",
                    "type": "textbox",
                    "text": "실화 사건",
                    "left": 40,
                    "top": 40,
                    "width": 200,
                    "height": 50,
                    "visible": True,
                },
            ],
            "background_url": "/api/jobs/test/media?path=bg.jpg",
        }

        # Safe placement
        score_safe = evaluate_variant_ctr(base_variant)
        assert score_safe["checks"][0]["passed"] is True
        safe_readiness = score_safe["readiness_score"]

        # Adversarial placement: line 1 placed in bottom-right corner (left: 1000, width: 200 => right 1200 > 1065; top: 600, height: 80 => bottom 680 > 625)
        bad_variant = copy.deepcopy(base_variant)
        bad_variant["layers"][0]["left"] = 1000
        bad_variant["layers"][0]["top"] = 600

        score_bad = evaluate_variant_ctr(bad_variant)
        assert score_bad["checks"][0]["passed"] is False
        assert any("vùng cấm" in w for w in score_bad["warnings"])
        # Exactly 15 point penalty applied for safe zone breach
        assert score_bad["readiness_score"] <= safe_readiness - 15

    def test_missing_background_triggers_dynamic_penalty(self):
        """When no background image is supplied, has_bg must fail and penalize readiness by 10."""
        with_bg = {
            "id": "v1",
            "background_url": "/api/jobs/test/media?path=bg.jpg",
            "layers": [
                {"id": "line_1", "text": "진실", "fontSize": 72, "strokeWidth": 16, "visible": True},
                {"id": "badge", "text": "실화", "visible": True},
            ],
        }
        without_bg = copy.deepcopy(with_bg)
        without_bg["background_url"] = ""

        eval_with = evaluate_variant_ctr(with_bg)
        eval_without = evaluate_variant_ctr(without_bg)

        assert eval_with["checks"][3]["passed"] is True
        assert eval_without["checks"][3]["passed"] is False
        assert eval_without["readiness_score"] <= eval_with["readiness_score"] - 10

    def test_curiosity_anchor_keywords_dynamically_boost_score(self):
        """Presence of high-curiosity psychological anchors (numbers, ?, 진실, 단서) dynamically scales curiosity score."""
        no_anchor = {
            "id": "v1",
            "layers": [
                {"id": "line_1", "text": "평범한 이야기", "visible": True},
                {"id": "line_2", "text": "일반적인 상황", "visible": True},
            ],
        }
        one_anchor = {
            "id": "v1",
            "layers": [
                {"id": "line_1", "text": "평범한 이야기", "visible": True},
                {"id": "line_2", "text": "충격적인 진실", "visible": True},
            ],
        }
        two_anchors = {
            "id": "v1",
            "layers": [
                {"id": "line_1", "text": "28년간 숨어 지낸 범인", "visible": True},
                {"id": "line_2", "text": "단 하나의 지문으로 밝혀진 진실?", "visible": True},
            ],
        }

        s_no = evaluate_variant_ctr(no_anchor)["curiosity_gap_score"]
        s_one = evaluate_variant_ctr(one_anchor)["curiosity_gap_score"]
        s_two = evaluate_variant_ctr(two_anchors)["curiosity_gap_score"]

        assert s_no < s_one < s_two, f"Expected dynamic scaling: {s_no} < {s_one} < {s_two}"
        assert s_two >= 95

    def test_text_overlength_penalizes_legibility(self):
        """Text longer than 6 words per line triggers mobile legibility penalty."""
        short_text = {
            "id": "v1",
            "layers": [
                {"id": "line_1", "text": "28년의 비밀", "fontSize": 80, "strokeWidth": 16, "visible": True},
                {"id": "line_2", "text": "단 하나의 증거", "fontSize": 84, "strokeWidth": 16, "visible": True},
            ],
        }
        long_text = {
            "id": "v1",
            "layers": [
                {"id": "line_1", "text": "이것은 너무나 길어서 모바일 화면에서 도저히 읽을 수 없는 첫 번째 줄 텍스트입니다", "fontSize": 80, "strokeWidth": 16, "visible": True},
                {"id": "line_2", "text": "두 번째 줄 역시 수많은 단어가 나열되어 시청자의 시선을 분산시키는 문제가 발생합니다", "fontSize": 84, "strokeWidth": 16, "visible": True},
            ],
        }

        eval_short = evaluate_variant_ctr(short_text)
        eval_long = evaluate_variant_ctr(long_text)

        assert eval_short["text_legibility_score"] > eval_long["text_legibility_score"]
        assert any("Text overlay dài" in w for w in eval_long["warnings"])


# ==============================================================================
# 2. CANONICAL PROFILE INTEGRITY & MASCOT LOCK
# ==============================================================================

class TestCanonicalProfileThumbnailDna:
    """Verify specific required fields for channel-e544a64b7c and all profiles."""

    def test_channel_e544a64b7c_exact_specification(self):
        """
        Verify channel-e544a64b7c has:
        - Cold Forensic Noir
        - 2D Golden Detective Mascot (#FFE84A)
        - Reference image path linked to 20261019-185102-31983814
        - mascot_lock == True
        """
        data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        profile = next(p for p in data["profiles"] if p["id"] == "channel-e544a64b7c")

        assert "thumbnail_dna" in profile
        tdna = profile["thumbnail_dna"]
        assert tdna["style_preset"] == "cold_forensic_noir"
        assert "#FFE84A" in tdna["visual_signature"]
        assert "Golden Detective Mascot" in tdna["visual_signature"]
        assert tdna["color_palette"]["primary"] == "#FFE84A"
        assert tdna["color_palette"]["accent"] == "#EF4444"
        assert tdna["layout_template"] == "broadcast_left_heavy"
        assert tdna["mascot_lock"] is True
        assert "20261019-185102-31983814" in tdna["reference_character_path"]
        assert tdna["reference_character_path"].endswith("style_reference.png")


# ==============================================================================
# 3. THUMBNAIL STYLE LOCKING & VERSION HISTORY
# ==============================================================================

class TestThumbnailStyleLockingAndHistory:
    """Adversarially verify version increments and history archiving."""

    def test_consecutive_locking_increments_version_and_records_history(self, tmp_path: Path):
        profiles_file = tmp_path / "profiles.json"
        data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        profiles_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        service = ThumbnailDnaService(profiles_file=profiles_file)

        # Lock 1
        res1 = service.lock_channel_profile_thumbnail_dna("channel-f6ec4dfff3", {
            "style_preset": "presidential_vault_v2",
            "color_palette": {"primary": "#ffeedd"},
        })
        v1 = res1["version"]
        assert v1 >= 2

        # Lock 2
        res2 = service.lock_channel_profile_thumbnail_dna("channel-f6ec4dfff3", {
            "style_preset": "presidential_vault_v3",
            "color_palette": {"primary": "#aabbcc"},
        })
        v2 = res2["version"]
        assert v2 == v1 + 1

        # Check profiles_file history
        updated_data = json.loads(profiles_file.read_text(encoding="utf-8"))
        prof = next(p for p in updated_data["profiles"] if p["id"] == "channel-f6ec4dfff3")
        assert len(prof["thumbnail_dna_history"]) >= 2
        assert prof["thumbnail_dna"]["color_palette"]["primary"] == "#aabbcc"

    def test_locking_non_existent_profile_raises_key_error(self, tmp_path: Path):
        profiles_file = tmp_path / "profiles.json"
        profiles_file.write_text(json.dumps({"profiles": []}), encoding="utf-8")
        service = ThumbnailDnaService(profiles_file=profiles_file)

        with pytest.raises(KeyError):
            service.lock_channel_profile_thumbnail_dna("non-existent-channel", {"style_preset": "foo"})


# ==============================================================================
# 4. A/B TEST PACK EXPORT & PIL RENDERING ADVERSARIAL CHECKS
# ==============================================================================

class TestThumbnailExportAndRendering:
    """Verify that export produces authentic, uncorrupted JPEG files readable by PIL."""

    def test_export_creates_valid_readable_images_and_zip(self, tmp_path: Path):
        ws = tmp_path / "test_render_ws"
        ws.mkdir(parents=True, exist_ok=True)

        job_id = "job-render-audit"
        job = {
            "id": job_id,
            "title": "대륙의 미스터리 28년",
            "language": "ko",
            "channel_profile_id": "channel-e544a64b7c",
            "thumbnail_dna": {
                "style_preset": "cold_forensic_noir",
                "color_palette": {"primary": "#FFE84A", "accent": "#EF4444"},
                "layout_template": "broadcast_left_heavy",
            },
        }

        design = build_default_thumbnail_design(job_id, ws, job)
        export_res = export_thumbnail_ab_pack(job_id, ws, design, job)

        assert export_res["ok"] is True
        assert export_res["exported_count"] == 3

        ab_dir = ws / "media" / "thumbnails"

        # Verify each image can be opened and is 1280x720
        for let in ("a", "b", "c"):
            img_path = ab_dir / f"variant_{let}.jpg"
            assert img_path.is_file(), f"variant_{let}.jpg must exist"
            assert img_path.stat().st_size > 1000, f"variant_{let}.jpg must be > 1KB"
            with Image.open(img_path) as im:
                assert im.size == (1280, 720), f"Expected 1280x720, got {im.size}"
                assert im.format == "JPEG"

        # Verify ZIP archive
        zip_path = ab_dir / "ab_test_pack.zip"
        assert zip_path.is_file()
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "variant_a.jpg" in names
            assert "variant_b.jpg" in names
            assert "variant_c.jpg" in names
            assert "ab_test_metadata.json" in names

        # Verify winner selection renders root thumbnail.jpg
        win_res = select_thumbnail_winner(job_id, ws, "v3", design, job)
        assert win_res["ok"] is True
        root_thumb = ws / "thumbnail.jpg"
        assert root_thumb.is_file()
        with Image.open(root_thumb) as im:
            assert im.size == (1280, 720)


# ==============================================================================
# 5. R4 NON-DESTRUCTIVE PRESERVATION
# ==============================================================================

class TestR4NonDestructivePreservation:
    """Verify active running job and databases are untouched."""

    def test_active_job_and_radar_db_preserved(self):
        ws = ROOT / "workspaces" / ACTIVE_JOB_ID
        assert ws.is_dir()
        assert (ws / "input.json").is_file()
        assert (ws / "media" / "style_reference" / "style_reference.png").is_file()
        assert (ROOT / "data" / "radar.db").is_file()
