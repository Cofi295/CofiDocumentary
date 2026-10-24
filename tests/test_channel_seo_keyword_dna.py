"""
Automated Verification Suite for Milestone 2:
Persistent Channel SEO Keyword DNA (Requirement R2, AC2, R4).

Verifies:
1. Canonical Channel Profiles in data/channel_profiles.json contain valid seo_keyword_dna.
2. ChannelProfileService preserves seo_keyword_dna across CRUD and clone operations.
3. FastApi ChannelProfileRequest and CreateJobRequest models do not strip seo_keyword_dna.
4. Job creation inherits and snapshots seo_keyword_dna.
5. Step 00 apply_seo_keyword_dna_to_title formats titles with primary keyword and dual languages.
6. Step 00 topic discovery enriches candidates with SEO keyword DNA.
7. Step 01 prompts inject SEO keyword DNA topical authority direction.
8. Step 07 validate_phase_quality("seo") enforces primary keyword and merges mandatory hashtags and default tags.
9. PreflightService validates SEO keyword DNA compliance.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from server import create_app
from services.channel_profile_service import ChannelProfileService
from services.job_service import JobService
from services.preflight_service import PreflightService
from documentary.store import JobStore
from documentary.service import DocumentaryService, apply_seo_keyword_dna_to_title
from documentary.prompts import _seo_keyword_dna_direction, build_phase_prompt
from documentary.quality import validate_phase_quality

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROFILES_FILE = DATA_DIR / "channel_profiles.json"


# ==============================================================================
# 1. CANONICAL CHANNEL PROFILES SEO DNA INTEGRITY
# ==============================================================================

def test_canonical_channel_profiles_contain_seo_dna():
    """Verify all 4 canonical channel profiles contain valid, non-empty seo_keyword_dna."""
    assert PROFILES_FILE.exists(), "channel_profiles.json must exist"
    data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profiles = {p["id"]: p for p in data.get("profiles", [])}

    expected_channels = {
        "channel-e544a64b7c": {
            "primary": "중국 실화 사건",
            "meaning_vi": "Vụ Án Có Thật ở Trung Quốc",
            "rule": "smart_seo_flexible",
        },
        "channel-1e24de3ab5": {
            "primary": "중국 인프라의 이면",
            "meaning_vi": "Mặt Tối & Đại Công Trình Hạ Tầng Trung Quốc",
            "rule": "smart_seo_flexible",
        },
        "channel-aa913eb90d": {
            "primary": "Declassified US Intelligence Files",
            "meaning_vi": "Hồ Sơ Giải Mật Tình Báo Hoa Kỳ",
            "rule": "smart_seo_flexible",
        },
        "channel-f6ec4dfff3": {
            "primary": "Presidential Records & Executive Forensics",
            "meaning_vi": "Hồ Sơ Tổng Thống & Mệnh Lệnh Mật",
            "rule": "smart_seo_flexible",
        },
    }

    for pid, exp in expected_channels.items():
        assert pid in profiles, f"Profile {pid} missing from channel_profiles.json"
        p = profiles[pid]
        assert "seo_keyword_dna" in p, f"seo_keyword_dna missing from profile {pid}"
        dna = p["seo_keyword_dna"]
        assert isinstance(dna, dict), f"seo_keyword_dna must be dict in {pid}"

        assert dna.get("primary_title_keyword") == exp["primary"], f"Mismatch primary keyword in {pid}"
        assert dna.get("primary_title_keyword_meaning_vi") == exp["meaning_vi"], f"Mismatch meaning_vi in {pid}"
        assert dna.get("keyword_placement_rule") == exp["rule"], f"Mismatch placement rule in {pid}"
        assert isinstance(dna.get("secondary_anchor_keywords"), list) and len(dna["secondary_anchor_keywords"]) > 0
        assert isinstance(dna.get("mandatory_hashtags"), list) and len(dna["mandatory_hashtags"]) > 0
        assert isinstance(dna.get("default_seo_tags"), list) and len(dna["default_seo_tags"]) > 0


# ==============================================================================
# 2. CHANNEL PROFILE SERVICE CRUD & CLONE INDEPENDENCE
# ==============================================================================

def test_channel_profile_crud_and_clone_preserves_seo_dna(tmp_path: Path):
    """Verify ChannelProfileService preserves seo_keyword_dna on create, update, and clone."""
    temp_profiles_file = tmp_path / "profiles.json"
    temp_profiles_file.write_text(json.dumps({"profiles": []}, ensure_ascii=False), encoding="utf-8")

    service = ChannelProfileService(storage_path=temp_profiles_file)

    sample_seo_dna = {
        "primary_title_keyword": "테스트 키워드",
        "primary_title_keyword_meaning_vi": "Từ Khóa Test",
        "keyword_placement_rule": "prefix_bracket",
        "secondary_anchor_keywords": ["보조 키워드 1", "보조 키워드 2"],
        "mandatory_hashtags": ["#테스트", "#사건"],
        "default_seo_tags": ["테스트", "다큐멘터리"],
    }

    # 1. Create Profile
    created = service.create_profile({
        "label": "Test Channel Profile",
        "market": "KR",
        "language": "ko",
        "seo_keyword_dna": sample_seo_dna,
    })
    created_id = created["id"]
    assert created["seo_keyword_dna"]["primary_title_keyword"] == "테스트 키워드"

    # Verify persisted read
    fetched = service.get_profile(created_id)
    assert fetched["seo_keyword_dna"]["primary_title_keyword"] == "테스트 키워드"
    assert fetched["seo_keyword_dna"]["primary_title_keyword_meaning_vi"] == "Từ Khóa Test"

    # 2. Partial Update Profile (deep merge)
    updated = service.update_profile(created_id, {
        "seo_keyword_dna": {
            "primary_title_keyword_meaning_vi": "Từ Khóa Đã Cập Nhật",
        }
    })
    # Existing keys must remain intact
    assert updated["seo_keyword_dna"]["primary_title_keyword"] == "테스트 키워드"
    assert updated["seo_keyword_dna"]["primary_title_keyword_meaning_vi"] == "Từ Khóa Đã Cập Nhật"
    assert len(updated["seo_keyword_dna"]["mandatory_hashtags"]) == 2

    # 3. Clone Profile (deep independence)
    cloned = service.clone_profile(created_id)
    cloned_id = cloned["id"]
    assert cloned_id != created_id
    assert cloned["seo_keyword_dna"]["primary_title_keyword"] == "테스트 키워드"

    # Mutate cloned profile's seo_keyword_dna
    service.update_profile(cloned_id, {
        "seo_keyword_dna": {
            "primary_title_keyword": "클론 키워드",
        }
    })

    # Verify original was NOT modified
    original_after = service.get_profile(created_id)
    assert original_after["seo_keyword_dna"]["primary_title_keyword"] == "테스트 키워드"
    cloned_after = service.get_profile(cloned_id)
    assert cloned_after["seo_keyword_dna"]["primary_title_keyword"] == "클론 키워드"


# ==============================================================================
# 3. FASTAPI ENDPOINT PAYLOAD INTEGRITY
# ==============================================================================

def test_fastapi_channel_profile_preserves_seo_keyword_dna(tmp_path: Path):
    """Verify PUT /api/radar/channel-profiles/{id} does not strip seo_keyword_dna via FastAPI."""
    app = create_app()
    client = TestClient(app)

    # Use canonical profile channel-e544a64b7c
    res = client.get("/api/radar/channel-profiles/channel-e544a64b7c")
    assert res.status_code == 200
    profile_data = res.json()
    assert "seo_keyword_dna" in profile_data
    assert profile_data["seo_keyword_dna"]["primary_title_keyword"] == "중국 실화 사건"

    # Update through REST endpoint
    update_payload = dict(profile_data)
    update_payload["notes"] = "SEO DNA update test verification"
    update_payload["seo_keyword_dna"]["keyword_placement_rule"] = "smart_seo_flexible"

    put_res = client.put("/api/radar/channel-profiles/channel-e544a64b7c", json=update_payload)
    assert put_res.status_code == 200
    saved = put_res.json()
    assert "seo_keyword_dna" in saved
    assert saved["seo_keyword_dna"]["primary_title_keyword"] == "중국 실화 사건"
    assert saved["seo_keyword_dna"]["primary_title_keyword_meaning_vi"] == "Vụ Án Có Thật ở Trung Quốc"


# ==============================================================================
# 4. JOB SERVICE INHERITANCE & SNAPSHOTTING
# ==============================================================================

def test_job_creation_inherits_and_snapshots_seo_keyword_dna(tmp_path: Path):
    """Verify JobService.create_job snapshots seo_keyword_dna from profile into job."""
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    job_service = JobService(store=JobStore(jobs_dir))
    doc_service = DocumentaryService(root=ROOT)

    # Fetch canonical profile
    profile = doc_service.get_channel_profile("channel-e544a64b7c")
    assert profile is not None

    job = job_service.create_job({
        "title": "Test Job with SEO DNA",
        "channel_profile_id": "channel-e544a64b7c",
        "market": "KR",
        "language": "ko",
    })

    assert "seo_keyword_dna" in job
    assert job["seo_keyword_dna"]["primary_title_keyword"] == "중국 실화 사건"
    assert "channel_profile_snapshot" in job
    assert "seo_keyword_dna" in job["channel_profile_snapshot"]
    assert job["channel_profile_snapshot"]["seo_keyword_dna"]["primary_title_keyword"] == "중국 실화 사건"


# ==============================================================================
# 5. STEP 00 TITLE FORMATTING ALGORITHM
# ==============================================================================

def test_apply_seo_keyword_dna_to_title_formatting():
    """Verify apply_seo_keyword_dna_to_title formats titles correctly across all placement rules."""
    seo_dna = {
        "primary_title_keyword": "중국 실화 사건",
        "primary_title_keyword_meaning_vi": "Vụ Án Có Thật ở Trung Quốc",
        "keyword_placement_rule": "smart_seo_flexible",
    }

    # 1. Plain Korean title with Vietnamese translation in parentheses
    raw_1 = "그녀는 왜 20년간 지하실에 갇혔나 (Người đàn bà 20 năm dưới hầm ngục)"
    full_t, t_target, t_vi = apply_seo_keyword_dna_to_title(raw_1, seo_dna)
    assert t_target == "[중국 실화 사건] 그녀는 왜 20년간 지하실에 갇혔나"
    assert t_vi == "[Vụ Án Có Thật ở Trung Quốc] Người đàn bà 20 năm dưới hầm ngục"
    assert full_t == "[중국 실화 사건] 그녀는 왜 20년간 지하실에 갇혔나 ([Vụ Án Có Thật ở Trung Quốc] Người đàn bà 20 năm dưới hầm ngục)"

    # 2. Title with dash / quote under smart_seo_flexible
    raw_2 = "백은 연쇄살인 — 28년 만의 추적 (Đại án Bạch Ngân — 28 năm truy vết)"
    full_t, t_target, t_vi = apply_seo_keyword_dna_to_title(raw_2, seo_dna)
    assert t_target.startswith("[중국 실화 사건]")
    assert t_vi.startswith("[Vụ Án Có Thật ở Trung Quốc]")

    # 3. Rule suffix_pipe
    pipe_dna = dict(seo_dna)
    pipe_dna["keyword_placement_rule"] = "suffix_pipe"
    raw_3 = "비밀의 호수 (Hồ Nước Bí Mật)"
    full_t, t_target, t_vi = apply_seo_keyword_dna_to_title(raw_3, pipe_dna)
    assert t_target == "비밀의 호수 | 중국 실화 사건"
    assert t_vi == "Hồ Nước Bí Mật | Vụ Án Có Thật ở Trung Quốc"
    assert full_t == "비밀의 호수 | 중국 실화 사건 (Hồ Nước Bí Mật | Vụ Án Có Thật ở Trung Quốc)"

    # 4. Title already containing primary keyword
    raw_4 = "[중국 실화 사건] 미제사건 파일 01 (Vụ Án Có Thật ở Trung Quốc - Hồ Sơ 01)"
    full_t, t_target, t_vi = apply_seo_keyword_dna_to_title(raw_4, seo_dna)
    # Must not duplicate the keyword!
    assert t_target.count("중국 실화 사건") == 1
    assert t_target == "[중국 실화 사건] 미제사건 파일 01"

    # 5. Title without Vietnamese parentheses
    raw_5 = "사라진 비행기 370편"
    full_t, t_target, t_vi = apply_seo_keyword_dna_to_title(raw_5, seo_dna)
    assert t_target == "[중국 실화 사건] 사라진 비행기 370편"
    assert t_vi == "Vụ Án Có Thật ở Trung Quốc"
    assert full_t == "[중국 실화 사건] 사라진 비행기 370편 (Vụ Án Có Thật ở Trung Quốc)"

    # 6. Null / empty seo_dna fallback
    full_t, t_target, t_vi = apply_seo_keyword_dna_to_title("테스트 제목 (Tiêu đề test)", None)
    assert t_target == "테스트 제목"
    assert t_vi == "Tiêu đề test"
    assert full_t == "테스트 제목 (Tiêu đề test)"


# ==============================================================================
# 6. STEP 00 TOPIC DISCOVERY ENRICHMENT
# ==============================================================================

def test_topic_discovery_strict_dna_applies_keyword_dna(tmp_path: Path):
    """Verify _discover_profile_topics_strict_dna attaches formatted title and SEO DNA."""
    doc_service = DocumentaryService(root=ROOT)
    profile = doc_service.get_channel_profile("channel-e544a64b7c")

    result = doc_service._discover_profile_topics_strict_dna(profile, requested_duration=30, force_refresh=False)
    assert "today" in result
    candidates = result["today"]
    assert len(candidates) > 0

    for cand in candidates:
        assert "title" in cand
        assert "title_target" in cand
        assert "title_vi" in cand
        assert "seo_keyword_dna" in cand
        assert cand["seo_keyword_dna"]["primary_title_keyword"] == "중국 실화 사건"
        # Verify primary keyword is present in target title
        assert "중국 실화 사건" in cand["title_target"]


# ==============================================================================
# 7. STEP 01 PROMPT INJECTION
# ==============================================================================

def test_step_01_prompt_injects_seo_keyword_dna():
    """Verify _seo_keyword_dna_direction and build_phase_prompt inject SEO DNA."""
    job = {
        "id": "test-job-001",
        "market": "KR",
        "language": "ko",
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "primary_title_keyword_meaning_vi": "Vụ Án Có Thật ở Trung Quốc",
            "keyword_placement_rule": "smart_seo_flexible",
            "secondary_anchor_keywords": ["특급수배록", "실제 사건"],
            "mandatory_hashtags": ["#중국실화사건"],
            "default_seo_tags": ["중국실화사건", "특급수배록"],
        }
    }

    direction = _seo_keyword_dna_direction(job)
    assert "CHANNEL SEO KEYWORD DNA — TOPICAL AUTHORITY REQUIREMENTS" in direction
    assert 'Primary Title / Channel Anchor Keyword: "중국 실화 사건"' in direction
    assert "Vụ Án Có Thật ở Trung Quốc" in direction
    assert "#중국실화사건" in direction

    # Test full build_phase_prompt
    prompt = build_phase_prompt(job, "plan", Path("workspace"), Path("remotion"))
    assert 'Primary Title / Channel Anchor Keyword: "중국 실화 사건"' in prompt
    assert "smart_seo_flexible" in prompt


# ==============================================================================
# 8. STEP 07 SEO QUALITY VALIDATOR
# ==============================================================================

def test_seo_quality_validator_enforces_primary_keyword_and_merges_tags(tmp_path: Path):
    """Verify validate_phase_quality('seo') wraps title with primary keyword and merges mandatory tags."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    seo_dna = {
        "primary_title_keyword": "중국 실화 사건",
        "primary_title_keyword_meaning_vi": "Vụ Án Có Thật ở Trung Quốc",
        "keyword_placement_rule": "prefix_bracket",
        "mandatory_hashtags": ["#중국실화사건", "#특급수배록"],
        "default_seo_tags": ["중국실화사건", "공안수사기록"],
    }

    job = {
        "id": "job-test-seo",
        "quality_contract": {"enforce": True, "min_scene_count": 1},
        "seo_keyword_dna": seo_dna,
    }

    initial_package = {
        "version": 1,
        "job_id": "job-test-seo",
        "recommended_title": "28년간 숨겨진 진실의 문",  # Missing primary keyword!
        "title_options": ["또 다른 대안 제목 1", "대안 제목 2"],  # Also missing primary keyword!
        "description": "다큐멘터리 설명글 내용입니다.",
        "tags": ["일반태그1", "일반태그2"],  # Missing mandatory tags
        "hashtags": ["#일반해시태그"],  # Missing mandatory hashtags
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

    (workspace / "seo_package.json").write_text(json.dumps(initial_package, ensure_ascii=False, indent=2), encoding="utf-8")

    # Run quality validation
    validate_phase_quality("seo", workspace, job)

    # Read back package
    updated_package = json.loads((workspace / "seo_package.json").read_text(encoding="utf-8"))

    # Assert primary keyword was auto-wrapped into recommended_title
    assert "[중국 실화 사건] 28년간 숨겨진 진실의 문" == updated_package["recommended_title"]

    # Assert mandatory hashtags were merged
    assert "#중국실화사건" in updated_package["hashtags"]
    assert "#특급수배록" in updated_package["hashtags"]
    assert "#일반해시태그" in updated_package["hashtags"]

    # Assert default tags were merged
    assert "중국실화사건" in updated_package["tags"]
    assert "공안수사기록" in updated_package["tags"]
    assert "일반태그1" in updated_package["tags"]


# ==============================================================================
# 9. PREFLIGHT SERVICE VALIDATION
# ==============================================================================

def test_preflight_service_validates_seo_keyword_dna():
    """Verify PreflightService flags missing primary keywords and mandatory hashtags."""
    preflight = PreflightService()
    profile = {
        "id": "channel-e544a64b7c",
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "mandatory_hashtags": ["#중국실화사건", "#특급수배록"],
        }
    }

    # 1. Topic stage - Title WITH primary keyword
    res_pass = preflight.check(profile, "topic", {"title": "[중국 실화 사건] 백은 미제사건"})
    summary_pass = res_pass["preflight_summary"]
    assert "primary_seo_keyword_dna_match" in summary_pass["winner_patterns_matched"]

    # 2. Topic stage - Title WITHOUT primary keyword
    res_warn = preflight.check(profile, "topic", {"title": "백은 미제사건 28년"})
    summary_warn = res_warn["preflight_summary"]
    assert any("Khuyến nghị chèn từ khóa SEO chủ lực" in rec for rec in summary_warn["recommendations"])

    # 3. SEO stage - Missing mandatory hashtags
    res_seo = preflight.check(profile, "seo", {
        "recommended_title": "[중국 실화 사건] 타이틀",
        "hashtags": ["#기타"],
        "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    })
    summary_seo = res_seo["preflight_summary"]
    assert "seo_primary_keyword_matched" in summary_seo["winner_patterns_matched"]
    assert any("Thiếu hashtag bắt buộc" in rec for rec in summary_seo["recommendations"])
