import os
import sys
import io
import json
import zipfile
import tempfile
import shutil
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

def test_stress_ctr_evaluation_dynamism():
    """Verify evaluate_variant_ctr computes real dynamic values and is not a static facade."""
    from documentary.thumbnail_studio import evaluate_variant_ctr

    base_variant = {
        "id": "v1",
        "hook_type": "curiosity_paradox",
        "layers": [
            {
                "id": "line_1",
                "visible": True,
                "text": "충격 실화 28년 미제",
                "left": 100,
                "top": 100,
                "width": 400,
                "height": 80,
                "fontSize": 72,
                "strokeWidth": 14,
                "fill": "#ffffff",
                "fontFamily": "Pretendard",
            },
            {
                "id": "line_2",
                "visible": True,
                "text": "단 하나의 지문",
                "left": 100,
                "top": 200,
                "width": 400,
                "height": 80,
                "fontSize": 80,
                "strokeWidth": 14,
                "fill": "#FFE84A",
                "fontFamily": "Pretendard",
            },
            {
                "id": "badge",
                "visible": True,
                "text": "특급수배록",
                "left": 100,
                "top": 40,
                "width": 150,
                "height": 40,
                "backgroundColor": "#EF4444",
            },
            {
                "id": "vignette",
                "visible": True,
                "opacity": 0.7,
            }
        ],
        "background_url": "mock://bg.png",
    }

    dna = {
        "color_palette": {"primary": "#FFE84A", "accent": "#EF4444"},
        "typography_preset": {"font_family": "Pretendard"},
        "mascot_lock": True,
    }

    # Baseline evaluation
    score_baseline = evaluate_variant_ctr(base_variant, channel_dna=dna)
    print("Baseline Readiness Score:", score_baseline["readiness_score"])
    print("Baseline Predicted CTR %:", score_baseline["predicted_ctr_pct"])
    assert score_baseline["checks"][0]["passed"] is True  # Safe zone check

    # Scenario A: Move text into the YouTube bottom-right safe-zone forbidden box (x: 1070..1280, y: 630..720)
    variant_violating_safe_zone = json.loads(json.dumps(base_variant))
    variant_violating_safe_zone["layers"][0]["left"] = 1080
    variant_violating_safe_zone["layers"][0]["top"] = 630
    score_safe_zone = evaluate_variant_ctr(variant_violating_safe_zone, channel_dna=dna)
    print("Violating Safe Zone Score:", score_safe_zone["readiness_score"])
    assert score_safe_zone["checks"][0]["passed"] is False
    assert score_safe_zone["readiness_score"] < score_baseline["readiness_score"], "Score must drop when safe zone is violated!"

    # Scenario B: Remove background image
    variant_no_bg = json.loads(json.dumps(base_variant))
    variant_no_bg["background_url"] = ""
    score_no_bg = evaluate_variant_ctr(variant_no_bg, channel_dna=dna)
    print("No Background Score:", score_no_bg["readiness_score"])
    assert score_no_bg["checks"][3]["passed"] is False
    assert score_no_bg["readiness_score"] < score_baseline["readiness_score"], "Score must drop when background is missing!"

    # Scenario C: Make text long (> 6 words) and small fontSize (< 60px)
    variant_small_text = json.loads(json.dumps(base_variant))
    variant_small_text["layers"][0]["text"] = "Đây là một câu rất dài có nhiều từ và chữ nhỏ"
    variant_small_text["layers"][0]["fontSize"] = 40
    variant_small_text["layers"][1]["fontSize"] = 40
    score_small_text = evaluate_variant_ctr(variant_small_text, channel_dna=dna)
    print("Small/Long Text Score:", score_small_text["readiness_score"])
    assert score_small_text["text_legibility_score"] < score_baseline["text_legibility_score"], "Text legibility must drop for small/long text!"

    print("=> Stress Test CTR Dynamism: PASSED!")


def test_stress_export_ab_pack_structure():
    """Verify export_thumbnail_ab_pack generates valid images and zip archives."""
    from documentary.thumbnail_studio import export_thumbnail_ab_pack, build_default_thumbnail_design

    tmp_ws = Path(tempfile.mkdtemp(prefix="test_ab_pack_"))
    try:
        # Create a mock base background image
        bg_dir = tmp_ws / "media" / "candidates"
        bg_dir.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1280, 720), color=(20, 30, 50))
        bg_path = bg_dir / "candidate_01.png"
        img.save(bg_path, format="PNG")

        job_data = {
            "id": "test_job_ab_123",
            "title": "Vụ Án Bí Ẩn 28 Năm [중국 실화 사건]",
            "channel_profile_id": "channel-e544a64b7c",
            "thumbnail_dna": {
                "color_palette": {"primary": "#FFE84A", "accent": "#EF4444"},
                "typography_preset": {"font_family": "Pretendard"},
            }
        }

        design = build_default_thumbnail_design(
            job_id="test_job_ab_123",
            workspace=tmp_ws,
            job=job_data,
            candidates=[{"url": "/media/candidate_01.png", "rel_path": "media/candidates/candidate_01.png"}],
        )

        res = export_thumbnail_ab_pack(
            job_id="test_job_ab_123",
            workspace=tmp_ws,
            design=design,
            job=job_data,
        )

        assert res["ok"] is True
        assert res["exported_count"] == 3
        zip_path = Path(res["zip_path"])
        assert zip_path.is_file(), f"ZIP pack missing at {zip_path}"
        assert zip_path.stat().st_size > 1000, f"ZIP pack too small: {zip_path.stat().st_size} bytes"

        # Inspect ZIP contents
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            print("ZIP file contents:", namelist)
            assert "variant_a.jpg" in namelist
            assert "variant_b.jpg" in namelist
            assert "variant_c.jpg" in namelist
            assert "ab_test_metadata.json" in namelist

            # Verify image is valid PIL JPEG
            a_bytes = zf.read("variant_a.jpg")
            img_a = Image.open(io.BytesIO(a_bytes))
            assert img_a.format == "JPEG"
            assert img_a.size == (1280, 720)
            print("Variant A image size & format:", img_a.size, img_a.format)

            # Verify metadata JSON
            meta = json.loads(zf.read("ab_test_metadata.json").decode("utf-8"))
            assert meta["job_id"] == "test_job_ab_123"
            assert len(meta["variants"]) == 3
            for v in meta["variants"]:
                assert "predicted_ctr_pct" in v["ctr_prediction"]
                assert "readiness_score" in v["ctr_prediction"]
                assert v["file_name"] in ("variant_a.jpg", "variant_b.jpg", "variant_c.jpg")
            print("Metadata title & variants verified:", meta["title"], [v["file_name"] for v in meta["variants"]])

        print("=> Stress Test Export A/B Pack: PASSED!")
    finally:
        shutil.rmtree(tmp_ws, ignore_errors=True)


def test_stress_seo_keyword_title_formatting():
    """Verify apply_seo_keyword_dna_to_title handles edge cases and arbitrary inputs."""
    from documentary.service import apply_seo_keyword_dna_to_title

    # Test 1: Arbitrary non-project inputs
    t, target, vi = apply_seo_keyword_dna_to_title(
        "Secrets of Quantum Computing (Bi Mat Dien Toan Luong Tu)",
        {
            "primary_title_keyword": "QUANTUM_REVOLUTION",
            "primary_title_keyword_meaning_vi": "Kỷ Nguyên Lượng Tử",
            "keyword_placement_rule": "prefix_bracket",
        }
    )
    assert "[QUANTUM_REVOLUTION]" in t
    assert "[Kỷ Nguyên Lượng Tử]" in vi
    print("Formatted Arbitrary 1:", t)

    # Test 2: Input already has keyword
    t2, target2, vi2 = apply_seo_keyword_dna_to_title(
        "[중국 실화 사건] 28년 미제사건 (Vụ Án Có Thật 28 Năm)",
        {
            "primary_title_keyword": "중국 실화 사건",
            "primary_title_keyword_meaning_vi": "Vụ Án Có Thật ở Trung Quốc",
            "keyword_placement_rule": "prefix_bracket",
        }
    )
    # Ensure keyword is NOT duplicated
    assert t2.count("중국 실화 사건") == 1
    print("No duplication verified:", t2)

    # Test 3: Suffix pipe rule
    t3, target3, vi3 = apply_seo_keyword_dna_to_title(
        "The Collapse of the Bridge (Su Sup Do Cau)",
        {
            "primary_title_keyword": "MEGA_FAILURE",
            "primary_title_keyword_meaning_vi": "Thảm Họa Công Trình",
            "keyword_placement_rule": "suffix_pipe",
        }
    )
    assert "| MEGA_FAILURE" in target3
    assert "| Thảm Họa Công Trình" in vi3
    print("Suffix pipe verified:", t3)

    print("=> Stress Test SEO Keyword Title Formatting: PASSED!")


def main():
    print("=== RUNNING AUDITOR M4 FORENSIC STRESS TESTS ===")
    test_stress_ctr_evaluation_dynamism()
    test_stress_export_ab_pack_structure()
    test_stress_seo_keyword_title_formatting()
    print("ALL ADVERSARIAL FORENSIC STRESS TESTS PASSED CLEANLY!")

if __name__ == "__main__":
    main()
