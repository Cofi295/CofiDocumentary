"""Official Production Test Suite for Vox & Real Satellite Semantic Scene Router.

Covers:
1. Semantic voice-to-archetype routing for 10+ diverse Korean and Vietnamese True Crime narration sentences:
   - DNA lineage / Y-STR pedigree -> #D4
   - School campus store / rooftop zoom -> #M1 (or #M6)
   - Night curfew / infrared lockdown -> #M7 (or #P2)
   - Fingerprint minutiae comparator -> #D9 (or #D1)
   - Interrogation confession transcript / voiceprint waveform -> #D5
   - Wanted warrant / composite sketch -> #D6
   - Regional river / boundary escape -> #M3 (or #M2)
   - 1990s TV news emergency broadcast -> #P3
   - Multi-year silence / dormant timeline -> #P1
   - Emotional confrontation / raw human grief -> cinema_full
   - 2.5D coordinate terrain slab -> #M5
2. Semantic differentiation: verifying routing is driven by voice semantic meaning, not static defaults or mechanical round-robin.
3. Sliding-window anti-repetition: feeding identical/repeated triggers rotates to sibling variants or cinema_full without emitting back-to-back identical archetypes.
4. Strict channel profile gating: True Crime channel (channel-e544a64b7c) enables the engine; non-crime channels (channel-1e24de3ab5, channel-aa913eb90d, channel-f6ec4dfff3) are 100% disabled.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from documentary.vox_engine.semantic_router import (
    VOX_ARCHETYPE_RULES,
    VoxSemanticRouter,
    build_voice_spec_for_beat,
    is_vox_satellite_enabled,
)


# ==============================================================================
# 1. Semantic Voice-to-Archetype Routing (Korean + Vietnamese)
# ==============================================================================

class TestVoxSemanticRoutingBilingualSentences:
    """Verifies semantic mapping of 10+ diverse True Crime voice narration sentences in Korean and Vietnamese."""

    @pytest.fixture(autouse=True)
    def setup_router(self):
        self.router = VoxSemanticRouter()

    # 1. DNA lineage / Y-STR pedigree -> #D4
    @pytest.mark.parametrize(
        "language,sentence,expected_archetype",
        [
            ("ko", "국립과학수사연구원은 Y-염색체 DNA 족보 가계도를 분석하여 용의자의 부계 혈통을 추적했다", "#D4"),
            ("vi", "Cơ quan điều tra tiến hành xét nghiệm ADN dòng họ và phân tích phả hệ nhiễm sắc thể Y để truy tìm gia tộc hung thủ", "#D4"),
        ],
    )
    def test_dna_lineage_ystr_pedigree(self, language: str, sentence: str, expected_archetype: str):
        self.router.reset_history()
        result = self.router.route_beat(sentence)
        assert result["archetype"] == expected_archetype
        assert result["cluster"] == "biometrics"
        assert result["score"] > 80.0
        assert "Y-STR" in result["label"] or "DNA" in result["label"]

    # 2. School campus store / rooftop zoom -> #M1 (or #M6)
    @pytest.mark.parametrize(
        "language,sentence,expected_candidates",
        [
            ("ko", "경찰 특공대는 바이인 제4중학교 매점을 급습하여 옥상과 건물 주변을 포위했다", {"#M1", "#M6"}),
            ("vi", "Lực lượng cảnh sát bất ngờ đột kích tiệm tạp hóa trường học và bao vây toàn bộ khuôn viên", {"#M1", "#M6"}),
        ],
    )
    def test_school_campus_store_rooftop_zoom(self, language: str, sentence: str, expected_candidates: set[str]):
        self.router.reset_history()
        result = self.router.route_beat(sentence)
        assert result["archetype"] in expected_candidates
        assert result["cluster"] == "satellite_zoom"
        assert result["score"] > 80.0

    # 3. Night curfew / infrared lockdown -> #M7 (or #P2)
    @pytest.mark.parametrize(
        "language,sentence,expected_candidates",
        [
            ("ko", "해가 지면 도시 전역에 야간 통제와 통금이 내려지고 적외선 카메라 순찰이 시작되었다", {"#M7", "#P2"}),
            ("vi", "Khi màn đêm buông xuống, lệnh giới nghiêm phong tỏa toàn thành phố và các đội tuần tra đêm hồng ngoại được triển khai", {"#M7", "#P2"}),
        ],
    )
    def test_night_curfew_infrared_lockdown(self, language: str, sentence: str, expected_candidates: set[str]):
        self.router.reset_history()
        result = self.router.route_beat(sentence)
        assert result["archetype"] in expected_candidates
        assert result["cluster"] == "curfew_surveillance"
        assert result["score"] > 80.0

    # 4. Fingerprint minutiae comparator -> #D9 (or #D1)
    @pytest.mark.parametrize(
        "language,sentence,expected_candidates",
        [
            ("ko", "현미경 아래에서 단 하나의 지문 속 14개 특징점이 완벽히 일치했다", {"#D9", "#D1"}),
            ("vi", "Dưới kính hiển vi, 14 điểm đặc trưng trên dấu vân tay hiện trường đã trùng khớp hoàn hảo với nghi phạm", {"#D9", "#D1"}),
        ],
    )
    def test_fingerprint_minutiae_comparator(self, language: str, sentence: str, expected_candidates: set[str]):
        self.router.reset_history()
        result = self.router.route_beat(sentence)
        assert result["archetype"] in expected_candidates
        assert result["cluster"] == "fingerprint"
        assert result["score"] > 80.0

    # 5. Interrogation confession transcript / voiceprint waveform -> #D5
    @pytest.mark.parametrize(
        "language,sentence,expected_archetype",
        [
            ("ko", "심문실 안에서 용의자는 마침내 범행을 자백하고 자필 진술서를 작성했다", "#D5"),
            ("vi", "Tại phòng thẩm vấn, nghi phạm cuối cùng đã nhận tội, khai nhận toàn bộ tội ác và ký vào bản cung", "#D5"),
        ],
    )
    def test_interrogation_confession_transcript(self, language: str, sentence: str, expected_archetype: str):
        self.router.reset_history()
        result = self.router.route_beat(sentence)
        assert result["archetype"] == expected_archetype
        assert result["cluster"] == "interrogation"
        assert result["score"] > 80.0
        assert "Clipboard" in result["label"] or "Voiceprint" in result["label"] or "Q&A" in result["label"]

    # 6. Wanted warrant / composite sketch -> #D6
    @pytest.mark.parametrize(
        "language,sentence,expected_archetype",
        [
            ("ko", "공안부는 전국에 1급 지명수배령을 내리고 몽타주 스케치와 함께 20만 위안의 현상금을 걸었다", "#D6"),
            ("vi", "Bộ Công an đã phát lệnh truy nã cấp A toàn quốc kèm theo bản phác họa chân dung và 20 vạn tiền thưởng", "#D6"),
        ],
    )
    def test_wanted_warrant_composite_sketch(self, language: str, sentence: str, expected_archetype: str):
        self.router.reset_history()
        result = self.router.route_beat(sentence)
        assert result["archetype"] == expected_archetype
        assert result["cluster"] == "warrant_sketch"
        assert result["score"] > 80.0
        assert "Warrant" in result["label"] or "Sketch" in result["label"]

    # 7. Regional river / boundary escape -> #M3 (or #M2)
    @pytest.mark.parametrize(
        "language,sentence,expected_candidates",
        [
            ("ko", "범인은 황하 강을 건너 행정구역 성 경계를 넘어 도주로를 확보했다", {"#M3", "#M2"}),
            ("vi", "Hung thủ men theo sông Hoàng Hà, vượt qua ranh giới hành chính giữa hai tỉnh để tìm đường trốn chạy", {"#M3", "#M2"}),
        ],
    )
    def test_regional_river_boundary_escape(self, language: str, sentence: str, expected_candidates: set[str]):
        self.router.reset_history()
        result = self.router.route_beat(sentence)
        assert result["archetype"] in expected_candidates
        assert result["cluster"] == "satellite_corridor"
        assert result["score"] > 80.0

    # 8. 1990s TV news emergency broadcast -> #P3
    @pytest.mark.parametrize(
        "language,sentence,expected_archetype",
        [
            ("ko", "1990년대 당시 방송 뉴스 특보 화면에서 앵커가 사건을 긴급 보도했다", "#P3"),
            ("vi", "Bản tin truyền hình thời sự năm 1990 trên màn hình CRT phát đi thông báo khẩn cấp từ đài truyền hình", "#P3"),
        ],
    )
    def test_1990s_tv_news_emergency_broadcast(self, language: str, sentence: str, expected_archetype: str):
        self.router.reset_history()
        result = self.router.route_beat(sentence)
        assert result["archetype"] == expected_archetype
        assert result["cluster"] == "broadcast"
        assert result["score"] > 80.0
        assert "CRT" in result["label"] or "Broadcast" in result["label"]

    # 9. Multi-year silence / dormant timeline -> #P1
    @pytest.mark.parametrize(
        "language,sentence,expected_archetype",
        [
            ("ko", "사건은 28년 동안 차가운 침묵 속에 묻혀 영구 미제로 남은 채 긴 세월이 흘렀다", "#P1"),
            ("vi", "Vụ án chìm trong 28 năm im lặng, trải qua khoảng lặng thời gian đằng đẵng chưa có lời giải", "#P1"),
        ],
    )
    def test_multi_year_silence_dormant_timeline(self, language: str, sentence: str, expected_archetype: str):
        self.router.reset_history()
        result = self.router.route_beat(sentence)
        assert result["archetype"] == expected_archetype
        assert result["cluster"] == "timeline"
        assert result["score"] > 80.0
        assert "Timeline" in result["label"] or "Silent" in result["label"]

    # 10. Emotional confrontation / raw human grief -> cinema_full
    @pytest.mark.parametrize(
        "language,sentence,expected_archetype",
        [
            ("ko", "희생자의 어머니는 차가운 법정 바닥에 주저앉아 비통한 오열과 눈물을 쏟아냈다", "cinema_full"),
            ("vi", "Người mẹ nạn nhân gục ngã trong nước mắt, nghẹn ngào không nói nên lời trước bi kịch quá đỗi đau đớn", "cinema_full"),
        ],
    )
    def test_emotional_confrontation_raw_human_grief(self, language: str, sentence: str, expected_archetype: str):
        self.router.reset_history()
        result = self.router.route_beat(sentence)
        assert result["archetype"] == expected_archetype
        assert result["cluster"] == "cinema"
        assert result["score"] > 80.0
        assert "Cinematic" in result["label"] or "Fullscreen" in result["label"]

    # 11. 2.5D coordinate terrain slab -> #M5
    @pytest.mark.parametrize(
        "language,sentence,expected_archetype",
        [
            ("ko", "연쇄 범행 현장의 GPS 좌표를 입체 3차원 위성 지형 슬랩 위에 연결하자 명확한 동선 패턴이 드러났다", "#M5"),
            ("vi", "Khi kết nối các tọa độ hiện trường trên khối 3D bản đồ lập thể, mô thức địa lý không gian của kẻ thủ ác lộ diện", "#M5"),
        ],
    )
    def test_coordinate_terrain_slab(self, language: str, sentence: str, expected_archetype: str):
        self.router.reset_history()
        result = self.router.route_beat(sentence)
        assert result["archetype"] == expected_archetype
        assert result["cluster"] == "satellite_slab"
        assert result["score"] > 80.0
        assert "Slab" in result["label"] or "2.5D" in result["label"]


# ==============================================================================
# 2. Semantic Differentiation vs Static Default / Round-Robin
# ==============================================================================

class TestVoxSemanticDifferentiation:
    """Verifies routing is driven by semantic tokens and meaning, not mechanical ordering."""

    @pytest.fixture(autouse=True)
    def setup_router(self):
        self.router = VoxSemanticRouter()

    def test_order_independence(self):
        """Routing identical sentences in forward vs reversed order produces identical semantic mapping."""
        sentences = [
            ("DNA", "Y-염색체 DNA 족보 가계도 분석", "#D4"),
            ("STORE", "제4중학교 매점을 급습하여 옥상 포위", "#M1"),
            ("CURFEW", "야간 통제와 통금 및 적외선 순찰", "#M7"),
            ("PRINT", "단 하나의 지문, 14개 특징점 일치", "#D9"),
            ("CONFESS", "심문실 안에서 자백 진술서 작성", "#D5"),
            ("WARRANT", "공안부 1급 지명수배령 및 몽타주", "#D6"),
        ]

        # Forward run
        forward_results = []
        for _, text, _ in sentences:
            self.router.reset_history()
            forward_results.append(self.router.route_beat(text)["archetype"])

        # Reverse run
        reversed_results = []
        for _, text, _ in reversed(sentences):
            self.router.reset_history()
            reversed_results.append(self.router.route_beat(text)["archetype"])
        reversed_results.reverse()

        assert forward_results == reversed_results
        for i, (_, _, expected) in enumerate(sentences):
            assert forward_results[i] == expected

    def test_unrelated_text_fallback_behavior(self):
        """Unrelated non-crime sentences fall back to cinema_full or default without false high-score matches."""
        unrelated_samples = [
            "오늘 저녁 메뉴는 따뜻한 김치찌개와 바삭한 돈까스입니다",
            "Hôm nay trời nắng đẹp, gió mùa đông bắc tràn về thủ đô",
            "Stock indices rose 2.5% following the quarterly earnings report",
        ]
        for text in unrelated_samples:
            self.router.reset_history()
            res = self.router.route_beat(text)
            assert res["archetype"] in ("cinema_full", "#D2")
            assert res["score"] == 0.0


# ==============================================================================
# 3. Sliding-Window Anti-Repetition & Sibling Rotation
# ==============================================================================

class TestVoxSlidingWindowAntiRepetition:
    """Verifies that repeating identical or semantically related sentences rotates cleanly."""

    @pytest.fixture(autouse=True)
    def setup_router(self):
        self.router = VoxSemanticRouter(history_size=4)

    def test_consecutive_identical_trigger_never_repeats_back_to_back(self):
        """Feeding identical trigger 10 times never yields adjacent duplicate archetypes."""
        test_sentences = [
            "국립과학수사연구원은 Y-염색체 DNA 족보 가계도를 분석했다",
            "경찰은 바이인 제4중학교 매점을 급습하여 용의자를 체포했다",
            "해가 지면 야간 통제와 통금이 시작되고 적외선 순찰이 강화되었다",
            "현미경 아래에서 단 하나의 지문 14개 특징점이 완벽히 일치했다",
            "심문실 안에서 용의자는 마침내 자백 진술서를 작성했다",
            "공안부는 1급 지명수배령을 내리고 몽타주를 배포했다",
            "연쇄 범행 현장의 GPS 좌표를 입체 위성 지형 슬랩 위에 연결했다",
        ]

        for sentence in test_sentences:
            self.router.reset_history()
            history = [self.router.route_beat(sentence)["archetype"] for _ in range(10)]

            # Check consecutive duplicates
            dups = [
                (i, history[i - 1], history[i])
                for i in range(1, len(history))
                if history[i] == history[i - 1]
            ]
            assert len(dups) == 0, f"Found consecutive duplicate for '{sentence[:20]}...': {dups}"

    def test_sibling_rotation_on_fingerprint(self):
        """Fingerprint minutiae comparator rotates between #D9 and #D1 sibling variants."""
        text = "단 하나의 지문, 14개 특징점이 완벽히 일치했다"
        self.router.reset_history()
        history = [self.router.route_beat(text)["archetype"] for _ in range(6)]

        assert history[:2] == ["#D9", "#D1"]

    def test_sibling_rotation_on_satellite_store_zoom(self):
        """Dual-match text matching #M1 and #M6 alternates cleanly."""
        text = "도심 광역에서 매점 옥상으로 위성 분할 줌인하여 확대 포착했다"
        self.router.reset_history()
        history = [self.router.route_beat(text)["archetype"] for _ in range(6)]

        assert history[:2] == ["#M1", "#M6"]

    def test_route_timeline_enriches_beats(self):
        """route_timeline assigns scene_archetype, label, and cluster to each timeline beat."""
        beats = [
            {"beat_id": "b01", "narration_text": "Y-염색체 DNA 족보 가계도를 분석했다"},
            {"beat_id": "b02", "narration_text": "매점 옥상과 학교 건물 주변을 급습했다"},
            {"beat_id": "b03", "narration_text": "해가 지면 야간 통제와 적외선 순찰이 강화되었다"},
            {"beat_id": "b04", "narration_text": "단 하나의 지문, 14개 특징점이 일치했다"},
            {"beat_id": "b05", "narration_text": "심문실에서 용의자는 범행을 자백했다"},
        ]
        job = {"channel_profile_id": "channel-e544a64b7c"}
        routed = self.router.route_timeline(beats, job)

        assert len(routed) == 5
        for b in routed:
            assert "scene_archetype" in b
            assert "archetype_label" in b
            assert "archetype_cluster" in b
            assert b["scene_archetype"].startswith("#")

        # Verify no consecutive duplicates in routed timeline
        for i in range(1, len(routed)):
            assert routed[i]["scene_archetype"] != routed[i - 1]["scene_archetype"]


# ==============================================================================
# 4. Strict Channel Profile Gating
# ==============================================================================

class TestVoxChannelProfileGating:
    """Verifies strict isolation: True Crime channel enabled, non-crime channels 100% disabled."""

    def test_crime_channel_profile_enabled(self):
        job = {"channel_profile_id": "channel-e544a64b7c"}
        assert is_vox_satellite_enabled(job) is True

        # Profile snapshot format
        job_snap = {"channel_profile_snapshot": {"id": "channel-e544a64b7c"}}
        assert is_vox_satellite_enabled(job_snap) is True

    def test_non_crime_channels_strictly_disabled(self):
        non_crime_channels = [
            "channel-1e24de3ab5",  # Chinese Megaprojects
            "channel-aa913eb90d",  # Global Geopolitics
            "channel-f6ec4dfff3",  # General Documentary
        ]
        for ch_id in non_crime_channels:
            job = {"channel_profile_id": ch_id}
            assert is_vox_satellite_enabled(job) is False, f"Channel {ch_id} must be disabled"

    def test_non_crime_channel_cannot_be_overridden_by_preset_or_strategy(self):
        """Even if editing preset or visual strategy is set to forensic_noir, non-crime ID remains disabled."""
        job = {
            "channel_profile_id": "channel-1e24de3ab5",
            "visual_strategy": "forensic_noir",
            "editing_dna": {"preset_id": "forensic_noir"},
        }
        assert is_vox_satellite_enabled(job) is False

    def test_generic_job_with_forensic_preset_enabled(self):
        """Jobs without a blacklisted channel ID that explicitly use forensic_noir preset are enabled."""
        job_preset = {"editing_dna": {"preset_id": "forensic_noir"}}
        assert is_vox_satellite_enabled(job_preset) is True

        job_strategy = {"visual_strategy": "true_crime_noir_ai"}
        assert is_vox_satellite_enabled(job_strategy) is True

    def test_route_timeline_bypasses_disabled_channels(self):
        """Disabled channel timelines return beats untouched without scene_archetype annotations."""
        router = VoxSemanticRouter()
        raw_beats = [
            {"beat_id": "b01", "narration_text": "Y-염색체 DNA 족보 가계도를 분석했다"},
            {"beat_id": "b02", "narration_text": "매점 옥상 주변을 급습했다"},
        ]
        job = {"channel_profile_id": "channel-1e24de3ab5"}  # Non-crime channel

        routed = router.route_timeline(raw_beats, job)
        assert len(routed) == 2
        for b in routed:
            assert "scene_archetype" not in b


class TestUnlockedVoiceFlexibleModesAndDurationSync:
    """Verifies unlocked bespoke Vox modes (#V_*) and full voice duration/clause synchronization."""

    def test_bespoke_modes_routing(self):
        router = VoxSemanticRouter()
        r_cross = router.route_beat("지하 정화조 배관 단면도와 흡입차 38대 수거 과정을 정밀 추적했다")
        assert r_cross["archetype"] == "#V_FORENSIC_CROSS_SECTION"

        router.reset_history()
        r_pop = router.route_beat("수사 보고서 구절에 형광펜 하이라이트를 치며 진술 모순을 발췌했다")
        assert r_pop["archetype"] == "#V_POPOUT_HIGHLIGHT"

        router.reset_history()
        r_tl = router.route_beat("시간대별 분 단위 동선 추적과 17시 04분 행적 재구성을 진행했다")
        assert r_tl["archetype"] == "#V_CLAUSE_TIMELINE"

        router.reset_history()
        r_3d = router.route_beat("입체 재구성과 다층 수사망 3D 분석으로 증거 네트워크를 검증했다")
        assert r_3d["archetype"] == "#V_BLENDER_3D_STAGE"

    def test_build_voice_spec_full_duration_and_clauses(self):
        beat = {
            "beat_id": "beat_042",
            "start_sec": 120.0,
            "end_sec": 130.8,
            "narration_text": "엘리베이터와 아파트 입구를 비추던 6,000개의 카메라, 그러나 아내가 빠져나간 흔적은 없었고, 결국 38도 폭염 속 정화조에서 20그램의 단서가 발견되었습니다.",
        }
        spec = build_voice_spec_for_beat(beat, beat_index=41)
        assert spec["duration_sec"] == 10.8
        assert len(spec["clauses"]) >= 2
        assert len(spec["clause_windows"]) == len(spec["clauses"])
        assert spec["clause_windows"][0][0] == 0.0
        assert spec["clause_windows"][-1][1] == 1.0
        assert "6,000개" in spec["metrics"]
        assert "38도" in spec["metrics"]
        assert "20그램" in spec["metrics"]
        assert "contextual_sfx" in spec
        assert len(spec["contextual_sfx"]) == 2

    def test_fullscreen_map_flight_and_contextual_sfx(self):
        router = VoxSemanticRouter()
        r_gis = router.route_beat("베이징 중앙 독도조가 2,100km 떨어진 운남성 쿤밍으로 전격 파견되었다")
        assert r_gis["archetype"] == "#V_FULLSCREEN_GIS_FLIGHT"
        router.reset_history()
        r_sat = router.route_beat("관두구 노래방과 도심 유흥가 나이트클럽 확장 거점을 전면 위성으로 추적했다")
        assert r_sat["archetype"] == "#V_FULLSCREEN_SATELLITE_RECON"


class TestFinancialForensicVoxAndProfileIntegration:
    """Verifies the Chinese High-Tech & Financial/Crypto Crime KR channel profile and FIN-1..FIN-6 Vox boards."""

    def test_new_channel_profile_loaded_with_5_pillars(self):
        import json
        from services.editing_dna_service import EditingDnaService

        profiles_file = PROJECT_ROOT / "data" / "channel_profiles.json"
        data = json.loads(profiles_file.read_text(encoding="utf-8"))
        profiles = data.get("profiles", [])
        cyber_prof = next((p for p in profiles if p.get("id") == "channel-cn-cyber-finance-kr"), None)
        assert cyber_prof is not None
        assert cyber_prof["market"] == "KR"
        assert cyber_prof["language"] == "ko"
        assert cyber_prof["visual_strategy"] == "full_ai"
        assert cyber_prof["default_visual_strategy"] == "full_ai"
        assert cyber_prof["editing_dna"]["preset_id"] == "financial_forensic_vox"
        assert cyber_prof["editing_dna"]["visual_mix"]["preferred_routing"] == "full_ai"
        assert cyber_prof["editing_dna"]["visual_mix"]["footage"] == 0.45
        assert cyber_prof["editing_dna"]["visual_mix"]["motion"] == 0.30
        assert cyber_prof["editing_dna"]["visual_mix"]["ai"] == 0.25
        assert len(cyber_prof["editorial_dna"]["narrative"]["structure_30m"]) == 5
        assert cyber_prof["editorial_dna"]["narrative"]["cta_architecture"]["mode"] == "story_driven_zero_repeat_organic_cta"

        svc = EditingDnaService()
        presets = svc.get_presets()
        assert "financial_forensic_vox" in presets

    def test_financial_vox_routing_and_renderers_strictly_isolated_from_true_crime(self):
        from documentary.vox_engine.archetypes import ARCHETYPE_RENDERERS
        from documentary.financial_vox_engine import (
            FINANCIAL_ARCHETYPE_RENDERERS,
            FinancialVoxSemanticRouter,
            is_financial_vox_enabled,
        )

        # True Crime vox_engine MUST reject financial profile and MUST NOT contain #FIN* archetypes
        assert is_vox_satellite_enabled({"channel_profile_id": "channel-e544a64b7c"}) is True
        assert is_vox_satellite_enabled({"channel_profile_id": "channel-cn-cyber-finance-kr"}) is False
        assert is_vox_satellite_enabled({"editing_dna": {"preset_id": "financial_forensic_vox"}}) is False
        assert not any(k.startswith("#FIN") for k in ARCHETYPE_RENDERERS)
        assert not any(k.startswith("#FIN") for k in VOX_ARCHETYPE_RULES)

        # Dedicated Financial Vox engine activates ONLY for channel-cn-cyber-finance-kr
        assert is_financial_vox_enabled({"channel_profile_id": "channel-cn-cyber-finance-kr"}) is True
        assert is_financial_vox_enabled({"channel_profile_id": "channel-e544a64b7c"}) is False

        fin_router = FinancialVoxSemanticRouter()
        cases = [
            ('앱 화면의 가짜 수익률 곡선과 달리 입금 0.3초 만에 통장 잔고 0원이 되었다', '#FIN01_SPLINE_CLIFF_DIVERGENCE'),
            ('14,280개 대포통장 쪼개기와 테더 비트코인 환치기 자금 세탁 흐름표를 추적했다', '#FIN02_SANKEY_LAUNDERING_FLOW'),
            ('영국 경찰은 콜드월렛 속 61,000 BTC와 런던 대저택 등 동결 자산 포트폴리오를 압수했다', '#FIN17_BLOCKCHAIN_TUMBLER_SPLITTER'),
            ('톈진에서 미얀마와 두바이를 거쳐 런던까지 이어진 대륙 횡단 자금 루트를 지도에서 추적했다', '#FIN04_GIS_25D_CROSSBORDER_ARC'),
            ('84명 단체방 속 83명 바람잡이의 실체는 24,000대 휴대폰 농장의 자동 매크로 기판이었다', '#FIN03_WAFFLE_DOT_PROPORTION'),
            ('국경 범죄단지 지하 서버실은 일반 상가 대비 40배 전력 소비량 폭증으로 덜미가 잡혔다', '#FIN05_GIS_OPTICAL_LOUPE_RECON'),
        ]
        for sentence, expected_arch in cases:
            fin_router.reset_history()
            res = fin_router.route_beat(sentence)
            assert res["archetype"] == expected_arch
            assert expected_arch in FINANCIAL_ARCHETYPE_RENDERERS
            img = FINANCIAL_ARCHETYPE_RENDERERS[expected_arch](0.75, None, None, subtitle_text=sentence[:28])
            assert img.size == (1920, 1080)


    def test_cyber_finance_profile_auto_skips_step4_footage_and_delegates_to_edit_agent(self, tmp_path):
        import shutil
        from documentary.models import effective_phases
        from documentary.prompts import build_phase_prompt
        from documentary.service import DocumentaryService

        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "data" / "channel_profiles.json", data_dir / "channel_profiles.json")

        service = DocumentaryService(tmp_path)
        job = service.create_job({
            "channel_profile_id": "channel-cn-cyber-finance-kr",
            "title": "[중국 실화 사건] 12만 명의 노후 자금 8조 원을 USB 하나에 담아 런던으로 사라진 여인 | 6만 비트코인 세탁 사건",
            "target_duration_minutes": 25,
        })
        assert job["visual_strategy"] == "full_ai"
        phases = effective_phases(job)
        assert "footage" not in phases
        assert phases == ("plan", "voice", "visuals", "ai_visual", "edit", "seo", "qc")

        workspace = Path(job["workspace"])
        plan_prompt = build_phase_prompt(job, "plan", workspace, tmp_path / "remotion")
        assert "CYBER-FINANCIAL AUDIT + 3-TIER COMPOSABLE LEGO VOX MOTION GRAMMAR STRATEGY" in plan_prompt
        assert "edit_footage_fetcher" in plan_prompt
        assert "VOX_COMPOSABLE_LEGO_GRAMMAR_DIRECTOR_V13" in plan_prompt

        edit_prompt = build_phase_prompt(job, "edit", workspace, tmp_path / "remotion")
        assert "CYBER-FINANCIAL AUDIT + 3-TIER COMPOSABLE LEGO VOX EDIT MODE" in edit_prompt
        assert "VOX_COMPOSABLE_LEGO_GRAMMAR_DIRECTOR_V13" in edit_prompt
        assert "#040C18" in edit_prompt
        assert "validate-vox-newsroom-ast.mjs --preset financial_forensic_vox" in edit_prompt
        assert "SPATIAL_DARK_CINEMA_DIRECTOR" not in edit_prompt

    def test_dna_mix_50_footage_30_vox_10_ai_10_flexible_strictly_enforced(self):
        from collections import Counter
        from documentary.financial_vox_engine import FinancialVoxSemanticRouter

        fin_router = FinancialVoxSemanticRouter()
        sample_sentences = [
            "앱 화면의 가짜 수익률 곡선과 달리 입금 0.3초 만에 통장 잔고 0원이 되었다",
            "14,280개 대포통장 쪼개기와 테더 비트코인 환치기 자금 세탁 흐름표를 추적했다",
            "경찰 수사관이 새벽 4시 비 내리는 골목길 CCTV 현장을 직접 탐문하며 용의자의 뒤를 쫓았다",
            "영국 경찰은 콜드월렛 속 61,000 BTC와 런던 대저택 등 동결 자산 포트폴리오를 압수했다",
            "어두운 방 안 홀로 남은 피해자는 내면의 공포와 불안 속에 밤새 기억을 되짚었다",
            "톈진에서 미얀마와 두바이를 거쳐 런던까지 이어진 대륙 횡단 자금 루트를 지도에서 추적했다",
            "한편 앞서 살펴본 현장 단서와 반대로 또 다른 계좌 이체 내역이 발견되었다",
            "84명 단체방 속 83명 바람잡이의 실체는 24,000대 휴대폰 농장의 자동 매크로 기판이었다",
            "수사대는 항구 컨테이너 터미널과 물류 창고 현장을 급습해 하드디스크를 확보했다",
            "국경 범죄단지 지하 서버실은 일반 상가 대비 40배 전력 소비량 폭증으로 덜미가 잡혔다",
        ]
        beats_40 = [
            {"beat_id": f"B{i + 1:03d}", "narration_text": sample_sentences[i % len(sample_sentences)]}
            for i in range(40)
        ]
        job_fin = {"channel_profile_id": "channel-cn-cyber-finance-kr"}
        routed_fin = fin_router.route_timeline(beats_40, job_fin)
        assert len(routed_fin) == 40

        slot_counts_fin = Counter(b["dna_visual_slot"] for b in routed_fin)
        assert slot_counts_fin["real_footage"] == 20      # 50%
        assert slot_counts_fin["vox_motion"] == 12        # 30%
        assert slot_counts_fin["ai_visual"] == 4          # 10%
        assert slot_counts_fin["flexible_reserve"] == 4   # 10%

        vox_archs_fin = [b["scene_archetype"] for b in routed_fin if b["dna_visual_slot"] == "vox_motion"]
        assert len(vox_archs_fin) == 12
        assert len(set(vox_archs_fin)) == 12  # 0% duplicate Vox archetypes (max_uses = 1)

        # Option B verification: non-map beats in 30% slot use direct scene motion (render_vox_board == False);
        # ONLY geographic route/map beats enable render_vox_board == True
        for b in routed_fin:
            if b["dna_visual_slot"] == "vox_motion":
                if b["motion_treatment"] == "satellite_gis_map_flight":
                    assert b["render_vox_board"] is True
                else:
                    assert b["render_vox_board"] is False
                    assert b["motion_treatment"] in {
                        "kinetic_metric_overlay",
                        "split_screen_ab",
                        "forensic_macro_loupe",
                        "multi_cut_clause_montage",
                        "optical_depth_push",
                    }
            else:
                assert b["render_vox_board"] is False

        tc_router = VoxSemanticRouter()
        job_tc = {"channel_profile_id": "channel-e544a64b7c"}
        routed_tc = tc_router.route_timeline(beats_40, job_tc)
        slot_counts_tc = Counter(b["dna_visual_slot"] for b in routed_tc)
        assert slot_counts_tc["real_footage"] == 20       # 50%
        assert slot_counts_tc["vox_motion"] == 12         # 30%
        assert slot_counts_tc["ai_visual"] == 4           # 10%
        assert slot_counts_tc["flexible_reserve"] == 4    # 10%

    def test_two_layer_visual_prompts_and_real_footage_vox_binding(self):
        from documentary.vox_engine import VoxSemanticRouter, is_vox_satellite_enabled

        assert is_vox_satellite_enabled({"channel_profile_id": "channel-kr-truecrime-director-v2"}) is True
        router = VoxSemanticRouter()
        beats = [
            {
                "beat_id": "B001-V01",
                "narration_text": "이 집은 산비탈을 깎아 지은 구조여서 창문 바로 아래가 평지가 아니라 사 미터가 넘는 절벽이었습니다.",
                "prompt": "AI keyframe prompt for B001",
            },
            {
                "beat_id": "B002-V01",
                "narration_text": "진흙 위에 찍힌 운동화 자국은 삼십팔 호 크기였고, 오른쪽 뒤꿈치 바깥쪽이 유독 심하게 닳아 있었습니다.",
                "prompt": "AI keyframe prompt for B002",
            },
            {
                "beat_id": "B003-V01",
                "narration_text": "다리가 부러진 채 붙잡힌 사내의 낡은 배낭 바닥에서는, 작은 검은색 비닐 수첩 하나가 나왔습니다.",
                "prompt": "AI keyframe prompt for B003",
            },
        ]
        routed = router.route_timeline(beats, {"channel_profile_id": "channel-kr-truecrime-director-v2"})
        seen_vox_prompts = set()
        seen_sigs = set()
        for idx, b in enumerate(routed):
            assert "visual_layers" in b
            assert "layer_1_ai_visual" in b["visual_layers"]
            assert "layer_2_vox_design" in b["visual_layers"]
            assert b["vox_design_prompt"]
            assert b["ai_cutout_prop_prompt"]
            spec = b["vox_blueprint_spec"]
            assert spec["evidence_media_mode"] == "real_footage_broadcast_motion"
            assert spec["real_footage_binding"]["clip_id"] == f"S_F{idx + 1:03d}"
            assert spec["real_footage_binding"]["forbid_synthetic_pil_drawing"] is True
            assert spec["real_footage_binding"]["forbid_blind_svg_scribble"] is True
            assert len(spec["clauses_t1_t2_t3"]) == 3
            assert b["vox_design_prompt"] not in seen_vox_prompts
            assert spec["vox_scene_signature"] not in seen_sigs
            seen_vox_prompts.add(b["vox_design_prompt"])
            seen_sigs.add(spec["vox_scene_signature"])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
