"""
Adversarial Stress Test Suite for Milestone 2: Channel SEO Keyword DNA.
Empirical verification of corner cases, cloning isolation, partial updates, and Step 00 topic discovery.
Authored by challenger_m2_1.
"""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from server import create_app
from services.channel_profile_service import ChannelProfileService
from documentary.service import DocumentaryService, apply_seo_keyword_dna_to_title
from documentary.quality import validate_phase_quality
from services.preflight_service import PreflightService

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROFILES_FILE = DATA_DIR / "channel_profiles.json"


# ==============================================================================
# 1. ADVERSARIAL STRESS: SPECIAL CHARACTERS, QUOTES, AND BRACKETS IN TITLES
# ==============================================================================

class TestTitleFormattingCornerCases:
    """Stress-test apply_seo_keyword_dna_to_title with adversarial inputs."""

    @pytest.fixture
    def default_seo_dna(self):
        return {
            "primary_title_keyword": "중국 실화 사건",
            "primary_title_keyword_meaning_vi": "Vụ Án Có Thật ở Trung Quốc",
            "keyword_placement_rule": "smart_seo_flexible",
        }

    @pytest.mark.parametrize("raw, exp_target_sub, exp_vi_sub", [
        ("'완전범죄'를 꿈꾼 자 (Kẻ mơ tưởng tội ác hoàn hảo)", "'완전범죄'를 꿈꾼 자", "Kẻ mơ tưởng tội ác hoàn hảo"),
        ('"악마의 속삭임" — 10년간의 추적 ("Lời thì thầm của quỷ" — 10 năm truy vết)', '"악마의 속삭임" — 10년간의 추적', '"Lời thì thầm của quỷ" — 10 năm truy vết'),
        ("“사라진 여인” – 비밀의 방 (“Người phụ nữ mất tích” – Căn phòng bí mật)", "“사라진 여인” – 비밀의 방", "“Người phụ nữ mất tích” – Căn phòng bí mật"),
        ("「비밀 수사」: 범인의 정체 («Cuộc điều tra bí mật»)", "「비밀 수사」: 범인의 정체", "«Cuộc điều tra bí mật»"),
    ])
    def test_quotes_single_and_double(self, default_seo_dna, raw, exp_target_sub, exp_vi_sub):
        """Test titles with single, double, curly, and guillemet quotes."""
        full, target, vi = apply_seo_keyword_dna_to_title(raw, default_seo_dna)
        assert "중국 실화 사건" in target, f"Target missing keyword for {raw}"
        assert exp_target_sub in target, f"Target missing original text for {raw}"
        assert exp_vi_sub in vi, f"VI missing original text for {raw}"
        assert "Vụ Án Có Thật ở Trung Quốc" in vi, f"VI missing meaning for {raw}"
        assert full.startswith("[중국 실화 사건]"), f"Full title should start with keyword for {raw}"

    @pytest.mark.parametrize("raw, exp_target_sub", [
        ("[단독] 100억 사기 사건 (Vụ lừa đảo 10 tỷ)", "[단독] 100억 사기 사건"),
        ("사건 파일 #12: 범인 vs 형사 (Hồ sơ #12: Hung thủ vs Cảnh sát)", "사건 파일 #12: 범인 vs 형사"),
        ("🔥 [긴급] 28년 미제 사건 종결! 🚨 (Khép lại đại án 28 năm!)", "28년 미제 사건 종결!"),
    ])
    def test_brackets_and_symbols(self, default_seo_dna, raw, exp_target_sub):
        """Test titles with brackets, pipes, colons, emojis."""
        full, target, vi = apply_seo_keyword_dna_to_title(raw, default_seo_dna)
        assert "중국 실화 사건" in target
        assert exp_target_sub in target
        assert isinstance(full, str) and len(full) > 0
        assert isinstance(target, str) and len(target) > 0
        assert isinstance(vi, str) and len(vi) > 0

    @pytest.mark.parametrize("empty_val", ["", "   ", None])
    def test_empty_and_whitespace_title(self, default_seo_dna, empty_val):
        """Test empty string, whitespace-only, and None titles."""
        full, target, vi = apply_seo_keyword_dna_to_title(empty_val, default_seo_dna)
        assert isinstance(full, str)
        assert isinstance(target, str)
        assert isinstance(vi, str)

    def test_placement_rule_prefix_bracket(self, default_seo_dna):
        """Test explicit prefix_bracket placement."""
        rule_dna = dict(default_seo_dna, keyword_placement_rule="prefix_bracket")
        raw = "단서 없는 살인사건 (Vụ án không manh mối)"
        full, target, vi = apply_seo_keyword_dna_to_title(raw, rule_dna)
        assert target == "[중국 실화 사건] 단서 없는 살인사건"
        assert vi == "[Vụ Án Có Thật ở Trung Quốc] Vụ án không manh mối"
        assert full == "[중국 실화 사건] 단서 없는 살인사건 ([Vụ Án Có Thật ở Trung Quốc] Vụ án không manh mối)"

    def test_placement_rule_suffix_pipe(self, default_seo_dna):
        """Test explicit suffix_pipe placement."""
        rule_dna = dict(default_seo_dna, keyword_placement_rule="suffix_pipe")
        raw = "단서 없는 살인사건 (Vụ án không manh mối)"
        full, target, vi = apply_seo_keyword_dna_to_title(raw, rule_dna)
        assert target == "단서 없는 살인사건 | 중국 실화 사건"
        assert vi == "Vụ án không manh mối | Vụ Án Có Thật ở Trung Quốc"
        assert full == "단서 없는 살인사건 | 중국 실화 사건 (Vụ án không manh mối | Vụ Án Có Thật ở Trung Quốc)"

    def test_placement_rule_natural_hook(self, default_seo_dna):
        """Test natural_hook placement rule."""
        rule_dna = dict(default_seo_dna, keyword_placement_rule="natural_hook")
        raw = "단서 없는 살인사건 (Vụ án không manh mối)"
        full, target, vi = apply_seo_keyword_dna_to_title(raw, rule_dna)
        assert target == "[중국 실화 사건] 단서 없는 살인사건"
        assert vi == "[Vụ Án Có Thật ở Trung Quốc] Vụ án không manh mối"
        assert full == "[중국 실화 사건] 단서 없는 살인사건 ([Vụ Án Có Thật ở Trung Quốc] Vụ án không manh mối)"

    def test_placement_rule_smart_seo_flexible_with_dash(self, default_seo_dna):
        """Test smart_seo_flexible with em-dash hook."""
        raw = "백은 미제사건 — 28년 만의 추적 (Đại án Bạch Ngân — 28 năm truy vết)"
        full, target, vi = apply_seo_keyword_dna_to_title(raw, default_seo_dna)
        assert target == "[중국 실화 사건] 백은 미제사건 — 28년 만의 추적"
        assert vi == "[Vụ Án Có Thật ở Trung Quốc] Đại án Bạch Ngân — 28 năm truy vết"

    def test_already_containing_keyword_idempotent(self, default_seo_dna):
        """Test that re-applying SEO DNA to an already-formatted title does not duplicate keyword."""
        raw = "[중국 실화 사건] 이미 포맷된 제목 ([Vụ Án Có Thật ở Trung Quốc] Tiêu đề đã format)"
        full, target, vi = apply_seo_keyword_dna_to_title(raw, default_seo_dna)
        assert target.count("중국 실화 사건") == 1
        assert target == "[중국 실화 사건] 이미 포맷된 제목"
        assert "Vụ Án Có Thật ở Trung Quốc" in vi

    def test_leading_parenthesis_preserves_korean_title(self, default_seo_dna):
        """
        Verify that when candidate title starts with parentheses, e.g. '(단독 보도) 28년간 숨어 지낸 범인 (Kẻ thủ ác)',
        target_formatted preserves the full Korean title '(단독 보도) 28년간 숨어 지낸 범인'
        and vi_part extracts clean Vietnamese translation 'Kẻ thủ ác' without swallowing Korean text.
        """
        raw = "(단독 보도) 28년간 숨어 지낸 범인 (Kẻ thủ ác)"
        full, target, vi = apply_seo_keyword_dna_to_title(raw, default_seo_dna)
        assert target == "[중국 실화 사건] (단독 보도) 28년간 숨어 지낸 범인"
        assert vi == "[Vụ Án Có Thật ở Trung Quốc] Kẻ thủ ác"
        assert full == "[중국 실화 사건] (단독 보도) 28년간 숨어 지낸 범인 ([Vụ Án Có Thật ở Trung Quốc] Kẻ thủ ác)"

    def test_intermediate_parenthesis_preserved_in_target_title(self, default_seo_dna):
        """
        Verify that intermediate parentheticals (e.g. series or episode label like '(1부)')
        remain part of target_title and are not truncated.
        """
        raw = "사건의 전말 (1부) (Toàn cảnh vụ án)"
        full, target, vi = apply_seo_keyword_dna_to_title(raw, default_seo_dna)
        assert target == "[중국 실화 사건] 사건의 전말 (1부)"
        assert vi == "[Vụ Án Có Thật ở Trung Quốc] Toàn cảnh vụ án"
        assert full == "[중국 실화 사건] 사건의 전말 (1부) ([Vụ Án Có Thật ở Trung Quốc] Toàn cảnh vụ án)"


# ==============================================================================
# 2. ADVERSARIAL STRESS: CLONING DEEP ISOLATION
# ==============================================================================

class TestProfileCloningIsolation:
    """Stress-test deep copy isolation when cloning channel profiles."""

    def test_cloned_profile_deep_independence_in_memory(self, tmp_path: Path):
        """Verify mutating clone's seo_keyword_dna lists/dicts in-place does NOT affect parent."""
        storage = tmp_path / "profiles.json"
        storage.write_text(json.dumps({"profiles": []}), encoding="utf-8")
        service = ChannelProfileService(storage_path=storage)

        original_dna = {
            "primary_title_keyword": "원래 키워드",
            "primary_title_keyword_meaning_vi": "Từ Khóa Gốc",
            "keyword_placement_rule": "smart_seo_flexible",
            "secondary_anchor_keywords": ["키워드1", "키워드2"],
            "mandatory_hashtags": ["#태그1", "#태그2"],
            "default_seo_tags": ["태그1", "태그2"],
        }
        parent = service.create_profile({
            "label": "Parent Profile",
            "market": "KR",
            "seo_keyword_dna": original_dna,
        })
        parent_id = parent["id"]

        # Clone profile
        clone = service.clone_profile(parent_id, new_label="Child Clone")
        clone_id = clone["id"]

        # Mutate cloned in-memory structure directly
        clone["seo_keyword_dna"]["secondary_anchor_keywords"].append("MUTATION_LEAK")
        clone["seo_keyword_dna"]["mandatory_hashtags"].append("#leak")
        clone["seo_keyword_dna"]["default_seo_tags"].append("leak_tag")

        # Verify parent profile retrieved fresh from storage
        fresh_parent = service.get_profile(parent_id)
        assert "MUTATION_LEAK" not in fresh_parent["seo_keyword_dna"]["secondary_anchor_keywords"]
        assert "#leak" not in fresh_parent["seo_keyword_dna"]["mandatory_hashtags"]
        assert "leak_tag" not in fresh_parent["seo_keyword_dna"]["default_seo_tags"]
        assert len(fresh_parent["seo_keyword_dna"]["secondary_anchor_keywords"]) == 2

    def test_cloned_profile_mutation_via_service_update(self, tmp_path: Path):
        """Verify service.update_profile on clone does NOT bleed into parent."""
        storage = tmp_path / "profiles.json"
        storage.write_text(json.dumps({"profiles": []}), encoding="utf-8")
        service = ChannelProfileService(storage_path=storage)

        parent = service.create_profile({
            "label": "Original Parent",
            "market": "KR",
            "seo_keyword_dna": {
                "primary_title_keyword": "고유 부모 키워드",
                "primary_title_keyword_meaning_vi": "Từ Khóa Độc Quyền Cha",
                "secondary_anchor_keywords": ["부모앵커"],
                "mandatory_hashtags": ["#부모해시"],
                "default_seo_tags": ["부모태그"],
            },
        })
        parent_id = parent["id"]
        clone = service.clone_profile(parent_id, "Clone 1")
        clone_id = clone["id"]

        # Update clone with completely different SEO DNA
        service.update_profile(clone_id, {
            "seo_keyword_dna": {
                "primary_title_keyword": "자식 클론 키워드",
                "primary_title_keyword_meaning_vi": "Từ Khóa Con",
                "secondary_anchor_keywords": ["자식앵커1", "자식앵커2"],
            }
        })

        parent_after = service.get_profile(parent_id)
        assert parent_after["seo_keyword_dna"]["primary_title_keyword"] == "고유 부모 키워드"
        assert parent_after["seo_keyword_dna"]["primary_title_keyword_meaning_vi"] == "Từ Khóa Độc Quyền Cha"
        assert parent_after["seo_keyword_dna"]["secondary_anchor_keywords"] == ["부모앵커"]

        clone_after = service.get_profile(clone_id)
        assert clone_after["seo_keyword_dna"]["primary_title_keyword"] == "자식 클론 키워드"
        assert clone_after["seo_keyword_dna"]["secondary_anchor_keywords"] == ["자식앵커1", "자식앵커2"]
        # Mandatory hashtags from parent should be preserved on clone because of deep merge
        assert "#부모해시" in clone_after["seo_keyword_dna"]["mandatory_hashtags"]

    def test_cloned_profile_isolation_via_fastapi_rest(self):
        """Verify REST API clone endpoint maintains complete isolation when mutated via PUT/PATCH."""
        app = create_app()
        client = TestClient(app)

        # 1. Clone canonical profile channel-aa913eb90d
        res = client.post("/api/radar/channel-profiles/channel-aa913eb90d/clone", json={"label": "REST Clone Test"})
        assert res.status_code == 200
        clone_data = res.json()
        clone_id = clone_data["id"]
        assert clone_id != "channel-aa913eb90d"

        try:
            # 2. Modify clone's SEO DNA via PUT
            mutated_clone_payload = dict(clone_data)
            mutated_clone_payload["seo_keyword_dna"] = {
                "primary_title_keyword": "REST MUTATED KEYWORD",
                "primary_title_keyword_meaning_vi": "Từ Khóa Bị Đổi",
                "keyword_placement_rule": "suffix_pipe",
                "secondary_anchor_keywords": ["mutated_secondary"],
                "mandatory_hashtags": ["#mutated"],
                "default_seo_tags": ["mutated_tag"],
            }
            put_res = client.put(f"/api/radar/channel-profiles/{clone_id}", json=mutated_clone_payload)
            assert put_res.status_code == 200

            # 3. Fetch original parent and verify 100% untouched
            parent_res = client.get("/api/radar/channel-profiles/channel-aa913eb90d")
            assert parent_res.status_code == 200
            parent_data = parent_res.json()
            assert parent_data["seo_keyword_dna"]["primary_title_keyword"] == "Declassified US Intelligence Files"
            assert parent_data["seo_keyword_dna"]["primary_title_keyword_meaning_vi"] == "Hồ Sơ Giải Mật Tình Báo Hoa Kỳ"
            assert "mutated_secondary" not in parent_data["seo_keyword_dna"]["secondary_anchor_keywords"]
            assert "#mutated" not in parent_data["seo_keyword_dna"]["mandatory_hashtags"]

        finally:
            # Clean up cloned profile
            client.delete(f"/api/radar/channel-profiles/{clone_id}")


# ==============================================================================
# 3. ADVERSARIAL STRESS: PARTIAL PATCH/PUT UPDATES
# ==============================================================================

class TestPartialUpdatePreservation:
    """Stress-test partial payload updates ensuring no fields are dropped."""

    def test_partial_update_without_seo_dna_preserves_all_seo_fields(self, tmp_path: Path):
        """Updating label or market without sending seo_keyword_dna must preserve existing SEO DNA."""
        storage = tmp_path / "profiles.json"
        storage.write_text(json.dumps({"profiles": []}), encoding="utf-8")
        service = ChannelProfileService(storage_path=storage)

        profile = service.create_profile({
            "label": "Original Profile",
            "market": "KR",
            "seo_keyword_dna": {
                "primary_title_keyword": "보존 대상 키워드",
                "primary_title_keyword_meaning_vi": "Từ Khóa Bảo Tồn",
                "secondary_anchor_keywords": ["보조1", "보조2"],
                "mandatory_hashtags": ["#해시1", "#해시2"],
                "default_seo_tags": ["태그1", "태그2"],
            }
        })
        pid = profile["id"]

        # Partial update with only label
        updated = service.update_profile(pid, {"label": "Updated Label Only"})
        assert updated["label"] == "Updated Label Only"
        assert updated["seo_keyword_dna"]["primary_title_keyword"] == "보존 대상 키워드"
        assert updated["seo_keyword_dna"]["secondary_anchor_keywords"] == ["보조1", "보조2"]
        assert updated["seo_keyword_dna"]["mandatory_hashtags"] == ["#해시1", "#해시2"]
        assert updated["seo_keyword_dna"]["default_seo_tags"] == ["태그1", "태그2"]

    def test_partial_seo_dna_update_preserves_sibling_fields(self, tmp_path: Path):
        """Updating only primary_title_keyword must preserve secondary keywords, hashtags, and tags."""
        storage = tmp_path / "profiles.json"
        storage.write_text(json.dumps({"profiles": []}), encoding="utf-8")
        service = ChannelProfileService(storage_path=storage)

        profile = service.create_profile({
            "label": "Sibling Preservation Test",
            "market": "KR",
            "seo_keyword_dna": {
                "primary_title_keyword": "구 키워드",
                "primary_title_keyword_meaning_vi": "Ý Nghĩa Cũ",
                "secondary_anchor_keywords": ["유지되어야함_1", "유지되어야함_2"],
                "mandatory_hashtags": ["#유지해시"],
                "default_seo_tags": ["유지태그"],
            }
        })
        pid = profile["id"]

        # Update ONLY primary_title_keyword
        updated = service.update_profile(pid, {
            "seo_keyword_dna": {
                "primary_title_keyword": "신규 키워드"
            }
        })

        assert updated["seo_keyword_dna"]["primary_title_keyword"] == "신규 키워드"
        # Siblings MUST NOT be dropped!
        assert updated["seo_keyword_dna"]["primary_title_keyword_meaning_vi"] == "Ý Nghĩa Cũ"
        assert updated["seo_keyword_dna"]["secondary_anchor_keywords"] == ["유지되어야함_1", "유지되어야함_2"]
        assert updated["seo_keyword_dna"]["mandatory_hashtags"] == ["#유지해시"]
        assert updated["seo_keyword_dna"]["default_seo_tags"] == ["유지태그"]

    def test_rest_patch_partial_seo_dna_preservation(self):
        """Test PATCH /api/radar/channel-profiles/{id} with partial seo_keyword_dna."""
        app = create_app()
        client = TestClient(app)

        # Get initial state of channel-1e24de3ab5
        res = client.get("/api/radar/channel-profiles/channel-1e24de3ab5")
        assert res.status_code == 200
        initial_profile = res.json()
        initial_secondary = list(initial_profile["seo_keyword_dna"]["secondary_anchor_keywords"])
        initial_hashtags = list(initial_profile["seo_keyword_dna"]["mandatory_hashtags"])

        try:
            # Send PATCH with only primary_title_keyword_meaning_vi
            patch_res = client.patch(
                "/api/radar/channel-profiles/channel-1e24de3ab5",
                json={"seo_keyword_dna": {"primary_title_keyword_meaning_vi": "Mặt Tối Công Trình (Test PATCH)"}}
            )
            assert patch_res.status_code == 200
            patched_data = patch_res.json()

            assert patched_data["seo_keyword_dna"]["primary_title_keyword_meaning_vi"] == "Mặt Tối Công Trình (Test PATCH)"
            # Ensure primary_title_keyword, secondary, hashtags were NOT dropped
            assert patched_data["seo_keyword_dna"]["primary_title_keyword"] == "중국 인프라의 이면"
            assert patched_data["seo_keyword_dna"]["secondary_anchor_keywords"] == initial_secondary
            assert patched_data["seo_keyword_dna"]["mandatory_hashtags"] == initial_hashtags

        finally:
            # Revert to original
            client.patch(
                "/api/radar/channel-profiles/channel-1e24de3ab5",
                json={"seo_keyword_dna": {"primary_title_keyword_meaning_vi": "Mặt Tối & Đại Công Trình Hạ Tầng Trung Quốc"}}
            )

    def test_invalid_seo_dna_type_rejected_with_bad_request(self, tmp_path: Path):
        """Passing non-dict for seo_keyword_dna should raise ValueError or 400 Bad Request."""
        storage = tmp_path / "profiles.json"
        storage.write_text(json.dumps({"profiles": []}), encoding="utf-8")
        service = ChannelProfileService(storage_path=storage)

        profile = service.create_profile({"label": "Invalid Payload Test", "market": "KR"})
        pid = profile["id"]

        with pytest.raises(ValueError, match="Field 'seo_keyword_dna' must be an object"):
            service.update_profile(pid, {"seo_keyword_dna": "not_a_dictionary"})


# ==============================================================================
# 4. ADVERSARIAL STRESS: STEP 00 TOPIC DISCOVERY & SUGGESTIONS
# ==============================================================================

class TestStep00TopicDiscoveryRobustness:
    """Stress-test Step 00 topic suggestions returning valid title_target and title_vi."""

    @pytest.mark.parametrize("channel_id", [
        "channel-e544a64b7c",
        "channel-1e24de3ab5",
        "channel-aa913eb90d",
        "channel-f6ec4dfff3",
    ])
    def test_strict_dna_topic_discovery_returns_valid_dual_titles(self, channel_id: str):
        """All 4 canonical profiles must generate topic suggestions with valid title_target and title_vi without KeyError."""
        doc_service = DocumentaryService(root=ROOT)
        profile = doc_service.get_channel_profile(channel_id)
        assert profile is not None, f"Profile {channel_id} not found"

        result = doc_service._discover_profile_topics_strict_dna(profile, requested_duration=30, force_refresh=False)
        assert "today" in result
        candidates = result["today"]
        assert len(candidates) > 0, f"Expected candidates for {channel_id}"

        exp_primary_kw = profile.get("seo_keyword_dna", {}).get("primary_title_keyword", "")

        for idx, cand in enumerate(candidates):
            # Assert all required keys exist and don't throw KeyError
            assert "title" in cand, f"Candidate {idx} missing title"
            assert "title_target" in cand, f"Candidate {idx} missing title_target"
            assert "title_vi" in cand, f"Candidate {idx} missing title_vi"
            assert "seo_keyword_dna" in cand, f"Candidate {idx} missing seo_keyword_dna"

            # Assert non-empty string types
            assert isinstance(cand["title"], str) and len(cand["title"].strip()) > 0
            assert isinstance(cand["title_target"], str) and len(cand["title_target"].strip()) > 0
            assert isinstance(cand["title_vi"], str) and len(cand["title_vi"].strip()) > 0

            # Assert primary keyword is incorporated in target title
            if exp_primary_kw:
                assert exp_primary_kw in cand["title_target"], f"Primary keyword '{exp_primary_kw}' not in candidate target title '{cand['title_target']}'"

    def test_rest_api_profile_today_returns_dual_titles_without_error(self):
        """Verify POST /api/radar/channel-profiles/{profile_id}/today returns 200 with dual titles."""
        app = create_app()
        client = TestClient(app)

        res = client.post(
            "/api/radar/channel-profiles/channel-e544a64b7c/today?target_duration_minutes=30&discovery_mode=dna_strict"
        )
        assert res.status_code == 200
        data = res.json()
        assert "today" in data
        assert len(data["today"]) > 0

        for item in data["today"]:
            assert "title" in item
            assert "title_target" in item
            assert "title_vi" in item
            assert "중국 실화 사건" in item["title_target"]

    def test_topic_discovery_with_empty_or_none_seo_dna_fallback(self):
        """Topic discovery on a profile with no seo_keyword_dna must gracefully fallback without throwing KeyError."""
        doc_service = DocumentaryService(root=ROOT)
        mock_profile = {
            "id": "mock-channel-no-seo",
            "market": "KR",
            "default_language": "ko",
            "default_duration_minutes": 30,
            "visual_strategy": "hybrid",
            "dna_mode": "custom_dna_only",
            "allowed_topics": "자연 재해 다큐멘터리",
            "forbidden_topics": "정치",
            "monetization_safety_policy": "교육 목적",
            "voice_and_structure": "차분한 해설",
            "seo_keyword_dna": {},  # Empty!
            "default_creative_brief": {},
            "editing_dna": {},
            "self_learning_memory": {},
        }

        # Should not raise any exception
        result = doc_service._discover_profile_topics_strict_dna(mock_profile, requested_duration=30, force_refresh=False)
        assert "today" in result
        for item in result["today"]:
            assert "title" in item
            assert "title_target" in item
            assert "title_vi" in item
            # Target title should still be valid even without primary keyword
            assert isinstance(item["title_target"], str) and len(item["title_target"]) > 0


# ==============================================================================
# 5. ADVERSARIAL STRESS: STEP 07 SEO QUALITY ENFORCEMENT ON RECOMMENDED_TITLE
# ==============================================================================

class TestStep07QualityEnforcementCornerCases:
    """Stress-test validate_phase_quality('seo') enforcement on recommended_title."""

    def test_recommended_title_enforced_even_if_alternative_option_has_keyword(self, tmp_path: Path):
        """
        Verify that recommended_title is auto-wrapped with primary keyword if missing,
        even if an entry in title_options already contains the keyword.
        """
        workspace = tmp_path / "ws_seo"
        workspace.mkdir(parents=True, exist_ok=True)

        package = {
            "version": 1,
            "job_id": "test-bypass",
            "recommended_title": "28년간 숨겨진 진실",  # Missing primary keyword!
            "title_options": ["[중국 실화 사건] 28년간 숨겨진 진실", "대안 제목 2"],  # Option 0 HAS the keyword!
            "description": "설명 내용",
            "tags": ["태그1", "태그2"],
            "hashtags": ["#해시1"],
            "reference_analysis": {},
            "thumbnail": {
                "prompt": "plain minimal background featuring text overlay with real subject",
                "overlay_text": "overlay",
                "visual_priority": "dynamic",
                "background_policy": "minimal_or_none",
            }
        }
        (workspace / "seo_package.json").write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")

        job = {
            "id": "test-bypass",
            "quality_contract": {"enforce": True},
            "seo_keyword_dna": {
                "primary_title_keyword": "중국 실화 사건",
                "keyword_placement_rule": "prefix_bracket",
            }
        }

        validate_phase_quality("seo", workspace, job)

        res = json.loads((workspace / "seo_package.json").read_text(encoding="utf-8"))
        assert res["recommended_title"] == "[중국 실화 사건] 28년간 숨겨진 진실"
