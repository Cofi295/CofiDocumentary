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

        assert history[:4] == ["#D9", "#D1", "#D9", "#D1"]

    def test_sibling_rotation_on_satellite_store_zoom(self):
        """Dual-match text matching #M1 and #M6 alternates cleanly."""
        text = "도심 광역에서 매점 옥상으로 위성 분할 줌인하여 확대 포착했다"
        self.router.reset_history()
        history = [self.router.route_beat(text)["archetype"] for _ in range(6)]

        assert history[:4] == ["#M1", "#M6", "#M1", "#M6"]

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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
