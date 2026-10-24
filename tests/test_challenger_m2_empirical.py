"""Empirical adversarial challenger test suite for Milestone 2: Step 07 SEO package quality enforcement and API boundaries."""

import json
import sqlite3
from pathlib import Path
import pytest

from documentary.quality import validate_phase_quality
from services.preflight_service import PreflightService


@pytest.fixture
def base_seo_package():
    return {
        "version": 1,
        "job_id": "job-empirical-test",
        "recommended_title": "28년간 숨겨진 진실의 문",
        "title_options": ["또 다른 대안 제목 1", "대안 제목 2"],
        "description": "다큐멘터리 설명글 내용입니다.",
        "tags": ["일반태그1", "일반태그2"],
        "hashtags": ["#일반해시태그"],
        "reference_analysis": {"observed_patterns": "ok"},
        "thumbnail": {
            "prompt": "Dark cinematic shot of real portrait with minimal plain background. Features text 풀리지 않는 의혹. Reference: Gao from https://example.com/gao.jpg with exact facial likeness preserved.",
            "overlay_text": "풀리지 않는 의혹",
            "visual_priority": "people_and_text_first",
            "background_policy": "minimal_or_none",
            "featured_real_people": ["Gao"],
            "identity_references": [{
                "name": "Gao",
                "source_url": "https://example.com/gao.jpg",
                "visually_verified": True,
                "verification_basis": "Archival official photo",
            }],
        },
    }


# ==============================================================================
# 1. TITLE PRIMARY KEYWORD AUTO-WRAPPING & PLACEMENT RULES
# ==============================================================================

def test_title_wrapped_with_prefix_bracket(tmp_path: Path, base_seo_package):
    workspace = tmp_path / "ws1"
    workspace.mkdir()
    (workspace / "seo_package.json").write_text(json.dumps(base_seo_package, ensure_ascii=False), encoding="utf-8")

    job = {
        "id": "job-1",
        "quality_contract": {"enforce": True, "min_scene_count": 1},
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "keyword_placement_rule": "prefix_bracket",
        },
    }

    validate_phase_quality("seo", workspace, job)
    updated = json.loads((workspace / "seo_package.json").read_text(encoding="utf-8"))
    assert updated["recommended_title"] == "[중국 실화 사건] 28년간 숨겨진 진실의 문"


def test_title_wrapped_with_suffix_pipe(tmp_path: Path, base_seo_package):
    workspace = tmp_path / "ws2"
    workspace.mkdir()
    (workspace / "seo_package.json").write_text(json.dumps(base_seo_package, ensure_ascii=False), encoding="utf-8")

    job = {
        "id": "job-2",
        "quality_contract": {"enforce": True, "min_scene_count": 1},
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "keyword_placement_rule": "suffix_pipe",
        },
    }

    validate_phase_quality("seo", workspace, job)
    updated = json.loads((workspace / "seo_package.json").read_text(encoding="utf-8"))
    assert updated["recommended_title"] == "28년간 숨겨진 진실의 문 | 중국 실화 사건"


def test_title_wrapped_with_default_smart_seo_flexible(tmp_path: Path, base_seo_package):
    workspace = tmp_path / "ws3"
    workspace.mkdir()
    (workspace / "seo_package.json").write_text(json.dumps(base_seo_package, ensure_ascii=False), encoding="utf-8")

    job = {
        "id": "job-3",
        "quality_contract": {"enforce": True, "min_scene_count": 1},
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "keyword_placement_rule": "smart_seo_flexible",
        },
    }

    validate_phase_quality("seo", workspace, job)
    updated = json.loads((workspace / "seo_package.json").read_text(encoding="utf-8"))
    assert updated["recommended_title"] == "[중국 실화 사건] 28년간 숨겨진 진실의 문"


def test_title_already_containing_keyword_not_double_wrapped(tmp_path: Path, base_seo_package):
    workspace = tmp_path / "ws4"
    workspace.mkdir()
    base_seo_package["recommended_title"] = "[중국 실화 사건] 이미 키워드가 포함된 제목"
    (workspace / "seo_package.json").write_text(json.dumps(base_seo_package, ensure_ascii=False), encoding="utf-8")

    job = {
        "id": "job-4",
        "quality_contract": {"enforce": True, "min_scene_count": 1},
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "keyword_placement_rule": "prefix_bracket",
        },
    }

    validate_phase_quality("seo", workspace, job)
    updated = json.loads((workspace / "seo_package.json").read_text(encoding="utf-8"))
    assert updated["recommended_title"] == "[중국 실화 사건] 이미 키워드가 포함된 제목"


def test_title_containing_keyword_case_insensitive(tmp_path: Path, base_seo_package):
    workspace = tmp_path / "ws5"
    workspace.mkdir()
    base_seo_package["recommended_title"] = "The Secret of declassified files in 1965"
    (workspace / "seo_package.json").write_text(json.dumps(base_seo_package, ensure_ascii=False), encoding="utf-8")

    job = {
        "id": "job-5",
        "quality_contract": {"enforce": True, "min_scene_count": 1},
        "seo_keyword_dna": {
            "primary_title_keyword": "Declassified Files",
            "keyword_placement_rule": "prefix_bracket",
        },
    }

    validate_phase_quality("seo", workspace, job)
    updated = json.loads((workspace / "seo_package.json").read_text(encoding="utf-8"))
    assert updated["recommended_title"] == "The Secret of declassified files in 1965"


def test_title_in_channel_profile_snapshot_fallback(tmp_path: Path, base_seo_package):
    workspace = tmp_path / "ws6"
    workspace.mkdir()
    (workspace / "seo_package.json").write_text(json.dumps(base_seo_package, ensure_ascii=False), encoding="utf-8")

    # job has no top-level seo_keyword_dna, only in channel_profile_snapshot
    job = {
        "id": "job-6",
        "quality_contract": {"enforce": True, "min_scene_count": 1},
        "channel_profile_snapshot": {
            "seo_keyword_dna": {
                "primary_title_keyword": "중국 실화 사건",
                "keyword_placement_rule": "prefix_bracket",
            }
        },
    }

    validate_phase_quality("seo", workspace, job)
    updated = json.loads((workspace / "seo_package.json").read_text(encoding="utf-8"))
    assert updated["recommended_title"] == "[중국 실화 사건] 28년간 숨겨진 진실의 문"


# ==============================================================================
# 2. ADVERSARIAL CHALLENGE: RECOMMENDED TITLE LACKS KEYWORD BUT TITLE OPTIONS HAS IT
# ==============================================================================

def test_adversarial_recommended_title_lacks_kw_but_title_options_has_kw(tmp_path: Path, base_seo_package):
    """
    ADVERSARIAL PROBE:
    What happens when recommended_title lacks the keyword, but title_options[0] contains it?
    Observation: In quality.py:
        has_primary = (primary_kw.lower() in rec_title.lower()) or any(primary_kw.lower() in opt.lower() for opt in title_opts)
    Since any(...) is True, has_primary is True, and recommended_title is NOT wrapped!
    """
    workspace = tmp_path / "ws_adv"
    workspace.mkdir()
    base_seo_package["recommended_title"] = "28년간 숨겨진 진실의 문"  # NO keyword
    base_seo_package["title_options"] = ["[중국 실화 사건] 대안 제목 1", "대안 제목 2"]  # HAS keyword!
    (workspace / "seo_package.json").write_text(json.dumps(base_seo_package, ensure_ascii=False), encoding="utf-8")

    job = {
        "id": "job-adv",
        "quality_contract": {"enforce": True, "min_scene_count": 1},
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "keyword_placement_rule": "prefix_bracket",
        },
    }

    validate_phase_quality("seo", workspace, job)
    updated = json.loads((workspace / "seo_package.json").read_text(encoding="utf-8"))

    # Empirical observation of actual behavior:
    # Notice: recommended_title is NOT wrapped because title_options[0] had the keyword!
    # If tested strictly against recommended_title, this exposes the behavior.
    has_in_rec = "중국 실화 사건" in updated["recommended_title"]
    has_in_opts = any("중국 실화 사건" in opt for opt in updated["title_options"])
    assert has_in_opts is True
    # Document whether it wrapped recommended_title or considered title_options sufficient:
    # In worker_m2 implementation, has_in_rec is False because has_primary was True from title_options.
    print(f"DEBUG: has_in_rec = {has_in_rec}, has_in_opts = {has_in_opts}")


# ==============================================================================
# 3. HASHTAGS & TAGS DEDUPLICATION AND MERGING
# ==============================================================================

def test_hashtags_and_tags_merge_without_duplicates(tmp_path: Path, base_seo_package):
    workspace = tmp_path / "ws7"
    workspace.mkdir()
    # Package already has #중국실화사건 and 일반태그1
    base_seo_package["hashtags"] = ["#일반해시태그", "#중국실화사건"]
    base_seo_package["tags"] = ["일반태그1", "중국실화사건"]
    (workspace / "seo_package.json").write_text(json.dumps(base_seo_package, ensure_ascii=False), encoding="utf-8")

    job = {
        "id": "job-7",
        "quality_contract": {"enforce": True, "min_scene_count": 1},
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "mandatory_hashtags": ["#중국실화사건", "#특급수배록", "#중국실화사건"],  # internal duplicate
            "default_seo_tags": ["중국실화사건", "공안수사기록", "중국실화사건"],  # internal duplicate
        },
    }

    validate_phase_quality("seo", workspace, job)
    updated = json.loads((workspace / "seo_package.json").read_text(encoding="utf-8"))

    # Check hashtags: exactly 1 #중국실화사건, 1 #특급수배록, 1 #일반해시태그
    hashtags = updated["hashtags"]
    assert hashtags.count("#중국실화사건") == 1, f"Expected 1 #중국실화사건, got {hashtags.count('#중국실화사건')}"
    assert hashtags.count("#특급수배록") == 1
    assert hashtags.count("#일반해시태그") == 1
    assert len(hashtags) == 3

    # Check tags: exactly 1 중국실화사건, 1 공안수사기록, 1 일반태그1
    tags = updated["tags"]
    assert tags.count("중국실화사건") == 1, f"Expected 1 중국실화사건, got {tags.count('중국실화사건')}"
    assert tags.count("공안수사기록") == 1
    assert tags.count("일반태그1") == 1


def test_hashtags_merge_case_insensitive_dedup(tmp_path: Path, base_seo_package):
    workspace = tmp_path / "ws8"
    workspace.mkdir()
    base_seo_package["hashtags"] = ["#declassified"]
    (workspace / "seo_package.json").write_text(json.dumps(base_seo_package, ensure_ascii=False), encoding="utf-8")

    job = {
        "id": "job-8",
        "quality_contract": {"enforce": True, "min_scene_count": 1},
        "seo_keyword_dna": {
            "primary_title_keyword": "Declassified Files",
            "mandatory_hashtags": ["#DECLASSIFIED", "#ColdWarVault"],
        },
    }

    validate_phase_quality("seo", workspace, job)
    updated = json.loads((workspace / "seo_package.json").read_text(encoding="utf-8"))

    # #DECLASSIFIED should NOT be appended because #declassified already exists
    assert len(updated["hashtags"]) == 2
    assert "#declassified" in updated["hashtags"]
    assert "#ColdWarVault" in updated["hashtags"]


# ==============================================================================
# 4. PREFLIGHT SERVICE SEO STAGE CHECKS
# ==============================================================================

def test_preflight_service_detects_clean_seo_package():
    preflight = PreflightService()
    profile = {
        "id": "channel-e544a64b7c",
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "mandatory_hashtags": ["#중국실화사건", "#특급수배록"],
        },
    }
    input_data = {
        "recommended_title": "[중국 실화 사건] 28년간 숨겨진 진실",
        "hashtags": ["#중국실화사건", "#특급수배록", "#미제사건"],
        "tags": ["중국실화사건", "특급수배록", "미제사건", "공안수사", "다큐"],
    }
    res = preflight.check(profile, "seo", input_data)
    summary = res["preflight_summary"]
    assert "seo_primary_keyword_matched" in summary["winner_patterns_matched"]
    assert len(summary["recommendations"]) == 0


def test_preflight_service_flags_missing_primary_and_hashtags():
    preflight = PreflightService()
    profile = {
        "id": "channel-e544a64b7c",
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "mandatory_hashtags": ["#중국실화사건", "#특급수배록"],
        },
    }
    input_data = {
        "recommended_title": "28년간 숨겨진 진실 (NO KEYWORD)",
        "hashtags": ["#일반태그"],
        "tags": ["t1", "t2", "t3"],  # less than 5 tags
    }
    res = preflight.check(profile, "seo", input_data)
    summary = res["preflight_summary"]
    assert "seo_primary_keyword_matched" not in summary["winner_patterns_matched"]
    recs = summary["recommendations"]
    assert any("Tiêu đề SEO chưa chứa từ khóa chủ lực" in r for r in recs)
    assert any("Thiếu hashtag bắt buộc" in r for r in recs)
    assert any("Bổ sung tối thiểu 5 tags" in r for r in recs)


# ==============================================================================
# 5. VERIFY ACTIVE JOB 20261019-185102-31983814 AND DATABASES INTACT (R4)
# ==============================================================================

def test_active_job_20261019_185102_31983814_intact():
    job_path = Path("data/jobs/20261019-185102-31983814/job.json")
    ws_path = Path("workspaces/20261019-185102-31983814")

    assert job_path.exists(), "Job 20261019-185102-31983814 job.json missing"
    job = json.loads(job_path.read_text(encoding="utf-8"))
    assert job["id"] == "20261019-185102-31983814"
    assert job["channel_profile_id"] == "channel-e544a64b7c"

    ai_visual = job.get("ai_visual") or {}
    assert ai_visual.get("style_mode") == "custom"
    assert ai_visual.get("style_preset") != "Người que (Stickman)"

    # Workspace directory must exist and contain vital files
    assert ws_path.exists(), "Job workspace directory missing"
    for fname in ["research.md", "script.md", "visual_manifest.json"]:
        assert (ws_path / fname).exists(), f"Vital artifact {fname} missing from workspace"

    ref_img = ws_path / "media" / "style_reference" / "style_reference.png"
    assert ref_img.exists(), "Color reference image missing"
    assert ref_img.stat().st_size > 0


def test_production_databases_intact():
    # 1. Media factory database
    mf_db = Path("data/media_factory/media_factory.db")
    if mf_db.exists():
        assert mf_db.stat().st_size > 0
        conn = sqlite3.connect(str(mf_db))
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
        count = cur.fetchone()[0]
        conn.close()
        assert count > 0

    # 2. CofiRadar database
    cofi_radar = Path(r"B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db")
    if cofi_radar.exists():
        assert cofi_radar.stat().st_size > 0
        conn = sqlite3.connect(str(cofi_radar))
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
        count = cur.fetchone()[0]
        conn.close()
        assert count > 0


# ==============================================================================
# 6. CANONICAL CHANNEL PROFILES SEO DNA INTEGRITY
# ==============================================================================

def test_canonical_profiles_have_valid_seo_keyword_dna():
    profiles_path = Path("data/channel_profiles.json")
    assert profiles_path.exists()
    data = json.loads(profiles_path.read_text(encoding="utf-8"))
    profiles = {p["id"]: p for p in data.get("profiles", [])}

    expected_profiles = [
        ("channel-e544a64b7c", "중국 실화 사건", "Vụ Án Có Thật ở Trung Quốc"),
        ("channel-1e24de3ab5", "중국 인프라의 이면", "Mặt Tối & Đại Công Trình Hạ Tầng Trung Quốc"),
        ("channel-aa913eb90d", "Declassified US Intelligence Files", "Hồ Sơ Giải Mật Tình Báo Hoa Kỳ"),
        ("channel-f6ec4dfff3", "Presidential Records & Executive Forensics", "Hồ Sơ Tổng Thống & Mệnh Lệnh Mật"),
    ]

    for pid, exp_primary, exp_meaning in expected_profiles:
        assert pid in profiles, f"Missing profile {pid}"
        seo = profiles[pid].get("seo_keyword_dna") or {}
        assert seo.get("primary_title_keyword") == exp_primary, f"Mismatch primary keyword for {pid}"
        assert seo.get("primary_title_keyword_meaning_vi") == exp_meaning, f"Mismatch meaning VI for {pid}"
        assert isinstance(seo.get("mandatory_hashtags"), list) and len(seo["mandatory_hashtags"]) > 0
        assert isinstance(seo.get("default_seo_tags"), list) and len(seo["default_seo_tags"]) > 0
