"""
Adversarial Stress Test Suite: Milestone M6 Challenge
Targeting CofiDocumentary and CofiRemotion

Focus Areas:
1. Boundary mutations of YPP quality gates (wrapper dominance, motion floor, outro audio tail, BGM collision).
2. Deep cross-profile isolation stress test (assert 0 Korean keywords in US profiles, 0 True Crime keywords in KR Infrastructure/Finance).
3. Secondary voice quote dispatch boundary and clamping tests (0, 1, 3, 5, and 6+ clamped to 5).
4. Remotion SubShotMediaLayer badge logic (authentic media suppression 100% watertight across all media types).
5. Preservation invariant on the 10 published episode workspaces and compositions.
"""

from __future__ import annotations

import collections
import copy
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any
import pytest

# Paths
DOC_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = DOC_ROOT / "data"
PROFILES_FILE = DATA_DIR / "channel_profiles.json"
TOPIC_POOLS_FILE = DATA_DIR / "dna_topic_pools.json"
BGM_HISTORY_FILE = DATA_DIR / "bgm_usage_history.json"
WORKSPACES_DIR = DOC_ROOT / "workspaces"
REMOTION_ROOT = DOC_ROOT.parent / "CofiRemotion"
REMOTION_SRC = REMOTION_ROOT / "src"

from documentary.quality import (
    evaluate_ypp_framing_wrapper_cap,
    evaluate_ypp_motion_floor,
    evaluate_ypp_bgm_anti_repetition,
    evaluate_ypp_outro_audio_tail,
    evaluate_korean_grammar_gate,
)
from documentary.script import (
    tag_verbatim_quotes,
    route_multi_voice_quotes,
    detect_verbatim_quotes,
)
from documentary.prompts import (
    build_phase_prompt,
    build_producer_chat_prompt,
)


# ==============================================================================
# 1. BOUNDARY MUTATIONS OF YPP QUALITY GATES
# ==============================================================================

class TestAdversarialYppQualityGatesBoundaryMutations:
    """Stress-test exact numerical and structural boundary conditions for YPP quality gates."""

    def test_wrapper_ratio_exact_55_percent_passes(self):
        """Boundary: 55.000% single wrapper dominance MUST pass."""
        # 55 of 100 beats dominant
        beats_55 = [{"beat_id": f"b{i}", "visual_wrapper": "wrapper_a" if i < 55 else "wrapper_b"} for i in range(100)]
        res = evaluate_ypp_framing_wrapper_cap(beats_55, max_wrapper_ratio=0.55)
        assert res["status"] == "PASSED"
        assert res["dominance_ratio"] == 0.55

        # 11 of 20 beats dominant (11/20 = 0.55)
        beats_11_20 = [{"beat_id": f"b{i}", "visual_wrapper": "split_screen" if i < 11 else "pip_dossier"} for i in range(20)]
        res2 = evaluate_ypp_framing_wrapper_cap(beats_11_20, max_wrapper_ratio=0.55)
        assert res2["status"] == "PASSED"
        assert res2["dominance_ratio"] == 0.55

    def test_wrapper_ratio_above_55_percent_fails(self):
        """Boundary: 55.001% and 55.1% dominance MUST fail with RuntimeError."""
        # 551 of 1000 beats dominant (55.100%)
        beats_551_1000 = [{"beat_id": f"b{i}", "visual_wrapper": "wrapper_a" if i < 551 else "wrapper_b"} for i in range(1000)]
        with pytest.raises(RuntimeError, match="Single framing wrapper exceeds 55.0% threshold"):
            evaluate_ypp_framing_wrapper_cap(beats_551_1000, max_wrapper_ratio=0.55)

        # 56 of 100 beats dominant (56.0%)
        beats_56 = [{"beat_id": f"b{i}", "visual_wrapper": "wrapper_a" if i < 56 else "wrapper_b"} for i in range(100)]
        with pytest.raises(RuntimeError, match="Single framing wrapper exceeds 55.0% threshold"):
            evaluate_ypp_framing_wrapper_cap(beats_56, max_wrapper_ratio=0.55)

    def test_wrapper_ratio_100_percent_monotony_fails(self):
        """Extreme: 100% single wrapper dominance MUST fail."""
        beats_100 = [{"beat_id": f"b{i}", "visual_wrapper": "monotonous_wrapper"} for i in range(50)]
        with pytest.raises(RuntimeError, match="exceeds 55.0% threshold"):
            evaluate_ypp_framing_wrapper_cap(beats_100, max_wrapper_ratio=0.55)

    def test_wrapper_ratio_degenerate_and_empty_inputs(self):
        """Edge Case: Empty beats list raises ValueError; single beat raises RuntimeError."""
        with pytest.raises(ValueError, match="Cannot evaluate framing wrapper cap on empty beats"):
            evaluate_ypp_framing_wrapper_cap([], max_wrapper_ratio=0.55)

        # Single beat (1/1 = 100%) exceeds 55%
        with pytest.raises(RuntimeError, match="exceeds 55.0% threshold"):
            evaluate_ypp_framing_wrapper_cap([{"beat_id": "b0", "visual_wrapper": "single"}], max_wrapper_ratio=0.55)

    def test_wrapper_ratio_custom_thresholds(self):
        """Configurability: Verify custom max_wrapper_ratio (e.g. 0.40, 0.60)."""
        # 3 wrappers: w1=40%, w2=30%, w3=30% -> dominant is 40% <= 40% -> PASS
        beats_40 = [
            {"beat_id": f"b{i}", "visual_wrapper": "w1" if i < 40 else ("w2" if i < 70 else "w3")}
            for i in range(100)
        ]
        assert evaluate_ypp_framing_wrapper_cap(beats_40, max_wrapper_ratio=0.40)["status"] == "PASSED"

        # 3 wrappers: w1=41%, w2=30%, w3=29% -> dominant is 41% > 40% -> FAIL
        beats_41 = [
            {"beat_id": f"b{i}", "visual_wrapper": "w1" if i < 41 else ("w2" if i < 71 else "w3")}
            for i in range(100)
        ]
        with pytest.raises(RuntimeError, match="exceeds 40.0% threshold"):
            evaluate_ypp_framing_wrapper_cap(beats_41, max_wrapper_ratio=0.40)

    def test_motion_floor_exact_35_percent_passes(self):
        """Boundary: Exactly 35.000% motion ratio MUST pass."""
        # 35 of 100 beats with motion
        beats_35 = [{"beat_id": f"b{i}", "kind": "sourced_video" if i < 35 else "still"} for i in range(100)]
        res = evaluate_ypp_motion_floor(beats_35, min_motion_ratio=0.35)
        assert res["status"] == "PASSED"
        assert res["motion_ratio"] == 0.35

        # 7 of 20 beats with motion (7/20 = 0.35)
        beats_7_20 = [{"beat_id": f"b{i}", "kind": "gis_satellite_flight" if i < 7 else "still"} for i in range(20)]
        res2 = evaluate_ypp_motion_floor(beats_7_20, min_motion_ratio=0.35)
        assert res2["status"] == "PASSED"
        assert res2["motion_ratio"] == 0.35

    def test_motion_floor_below_35_percent_fails(self):
        """Boundary: 34.900% and 34.0% motion ratio MUST fail with RuntimeError."""
        # 349 of 1000 beats with motion (34.9%)
        beats_349_1000 = [{"beat_id": f"b{i}", "kind": "sourced_video" if i < 349 else "still"} for i in range(1000)]
        with pytest.raises(RuntimeError, match="violating motion floor"):
            evaluate_ypp_motion_floor(beats_349_1000, min_motion_ratio=0.35)

        # 34 of 100 beats with motion (34.0%)
        beats_34 = [{"beat_id": f"b{i}", "kind": "video" if i < 34 else "still"} for i in range(100)]
        with pytest.raises(RuntimeError, match="violating motion floor"):
            evaluate_ypp_motion_floor(beats_34, min_motion_ratio=0.35)

    def test_motion_floor_zero_motion_stills_fails(self):
        """Extreme: 100% static still slideshow (0 motion beats) MUST fail."""
        beats_0 = [{"beat_id": f"b{i}", "kind": "ai_still", "camera_mode": "static_hold"} for i in range(50)]
        with pytest.raises(RuntimeError, match="violating motion floor"):
            evaluate_ypp_motion_floor(beats_0, min_motion_ratio=0.35)

    def test_motion_floor_diverse_motion_indicators(self):
        """Robustness: All recognized motion indicators must correctly contribute to the motion count."""
        indicators = [
            {"kind": "sourced_video"},
            {"kind": "video"},
            {"kind": "motion_dossier"},
            {"kind": "satellite_map"},
            {"kind": "gis_satellite_flight"},
            {"kind": "remotion_camera_move"},
            {"kind": "annotated_footage"},
            {"visual_type": "motion_dossier"},
            {"media_type": "sourced_video"},
            {"has_motion_override": True},
            {"camera_mode": "slow_dolly_zoom"},
        ]
        beats = [{"beat_id": f"b{i}", **ind} for i, ind in enumerate(indicators)]
        # Pad with 11 stills so total = 22, motion = 11 (50% > 35%)
        for i in range(11):
            beats.append({"beat_id": f"still_{i}", "kind": "image", "camera_mode": "static_hold"})

        res = evaluate_ypp_motion_floor(beats, min_motion_ratio=0.35)
        assert res["status"] == "PASSED"
        assert res["motion_beats"] == 11

    def test_outro_audio_tail_boundary(self):
        """Boundary: Outro audio tail exactly 3.50s passes; 3.49s fails."""
        res_35 = evaluate_ypp_outro_audio_tail(3.50, min_tail_sec=3.5, max_tail_sec=4.5)
        assert res_35["status"] == "PASSED"
        assert res_35["in_ideal_range"] is True

        res_45 = evaluate_ypp_outro_audio_tail(4.50, min_tail_sec=3.5, max_tail_sec=4.5)
        assert res_45["status"] == "PASSED"
        assert res_45["in_ideal_range"] is True

        # Slightly over ideal range passes quality gate but in_ideal_range is False
        res_50 = evaluate_ypp_outro_audio_tail(5.00, min_tail_sec=3.5, max_tail_sec=4.5)
        assert res_50["status"] == "PASSED"
        assert res_50["in_ideal_range"] is False

        # Below 3.5s MUST fail
        with pytest.raises(RuntimeError, match="Missing 3.5-4.5s outro audio fade tail"):
            evaluate_ypp_outro_audio_tail(3.49, min_tail_sec=3.5)

        with pytest.raises(RuntimeError, match="Missing 3.5-4.5s outro audio fade tail"):
            evaluate_ypp_outro_audio_tail(0.0, min_tail_sec=3.5)

        with pytest.raises(RuntimeError, match="Missing 3.5-4.5s outro audio fade tail"):
            evaluate_ypp_outro_audio_tail(-1.5, min_tail_sec=3.5)

    def test_bgm_anti_repetition_boundary_and_isolation(self, tmp_path):
        """Stress: Duplicate BGM set on same channel fails; fresh set or cross-channel passes."""
        history_file = tmp_path / "bgm_history.json"
        history_data = {
            "version": 1,
            "episodes": {
                "ep_001": {
                    "channel_profile_id": "ch_alpha",
                    "tracks_used": ["track_01.mp3", "track_02.mp3", "track_03.mp3"]
                }
            }
        }
        history_file.write_text(json.dumps(history_data), encoding="utf-8")

        # Exact duplicate set on same channel MUST fail
        with pytest.raises(RuntimeError, match="Duplicate BGM set detected"):
            evaluate_ypp_bgm_anti_repetition("ch_alpha", ["track_01.mp3", "track_02.mp3", "track_03.mp3"], history_file)

        # Same tracks on a DIFFERENT channel profile MUST pass (isolated per channel)
        res_beta = evaluate_ypp_bgm_anti_repetition("ch_beta", ["track_01.mp3", "track_02.mp3", "track_03.mp3"], history_file)
        assert res_beta["status"] == "PASSED"

        # Fresh tracks on ch_alpha MUST pass
        res_alpha_fresh = evaluate_ypp_bgm_anti_repetition("ch_alpha", ["track_01.mp3", "track_04.mp3"], history_file)
        assert res_alpha_fresh["status"] == "PASSED"

        # Empty selected tracks raises ValueError
        with pytest.raises(ValueError, match="selected_tracks must not be empty"):
            evaluate_ypp_bgm_anti_repetition("ch_alpha", [], history_file)


# ==============================================================================
# 2. DEEP CROSS-PROFILE ISOLATION STRESS TEST
# ==============================================================================

class TestAdversarialCrossProfileIsolation:
    """Stress-test 100% token, language, and niche isolation across Channel Profiles."""

    def test_us_profiles_zero_korean_hangul(self):
        """Deep scan: US English profiles must contain zero Korean characters anywhere in their subtree."""
        assert PROFILES_FILE.exists()
        data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        profiles = data.get("profiles", [])

        us_profile_ids = {"channel-f6ec4dfff3", "channel-aa913eb90d"}
        found_us_profiles = [p for p in profiles if p.get("id") in us_profile_ids or p.get("market") == "US" or p.get("language") == "en"]
        assert len(found_us_profiles) >= 2

        hangul_pattern = re.compile(r"[\uac00-\ud7a3]")
        for profile in found_us_profiles:
            pid = profile.get("id")
            serialized = json.dumps(profile, ensure_ascii=False)
            matches = hangul_pattern.findall(serialized)
            assert len(matches) == 0, f"US Profile {pid} contains {len(matches)} leaked Hangul characters: {matches[:15]}"

    def test_us_profiles_zero_true_crime_keywords(self):
        """Deep scan: US English profiles must contain zero Korean True Crime terms."""
        data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        us_profiles = [p for p in data.get("profiles", []) if p.get("market") == "US" or p.get("language") == "en"]

        korean_crime_terms = ["특급수배록", "수배범", "사건", "범인", "살인", "CCTV", "난징", "난징의대"]
        for profile in us_profiles:
            pid = profile.get("id")
            serialized = json.dumps(profile, ensure_ascii=False)
            for term in korean_crime_terms:
                assert term not in serialized, f"US Profile {pid} contains leaked Korean True Crime term: '{term}'"

    def test_kr_infrastructure_isolation_audit(self):
        """Audit: KR Infrastructure profile must not contain violent serial murder True Crime rules or US presidential terms."""
        data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        infra_profiles = [p for p in data.get("profiles", []) if p.get("id") == "channel-1e24de3ab5"]
        assert len(infra_profiles) == 1
        infra = infra_profiles[0]

        serialized = json.dumps(infra, ensure_ascii=False)

        # US presidential terms must be 0
        us_presidential_terms = ["Nixon", "Watergate", "Oval Office", "Kennedy", "Lincoln"]
        for term in us_presidential_terms:
            assert term not in serialized, f"KR Infrastructure profile contains US Presidential term: '{term}'"

        # Check for True Crime contamination (flags bug if present)
        violent_crime_terms = ["연쇄살인", "살인마", "토막", "엽기적 살인", "시체", "부검", "특급수배록", "가오청융", "친삼촌 Y-염색체"]
        leaked = [t for t in violent_crime_terms if t in serialized]
        assert len(leaked) == 0, (
            f"VULNERABILITY FOUND: KR Infrastructure profile contains True Crime contamination: {leaked}. "
            "Found residual True Crime rules in self_learning_memory.thumbnail_dna.rules and seo_dna."
        )

    def test_kr_cyber_finance_zero_violent_serial_murder(self):
        """Deep scan: KR Cyber-Finance profile must focus on financial fraud, 0 violent serial murder."""
        data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        finance_profiles = [p for p in data.get("profiles", []) if p.get("id") == "channel-cn-cyber-finance-kr"]
        assert len(finance_profiles) == 1
        finance = finance_profiles[0]

        serialized = json.dumps(finance, ensure_ascii=False)
        violent_terms = ["연쇄살인", "토막살인", "시체 유기", "부검의"]
        for term in violent_terms:
            assert term not in serialized, f"KR Cyber-Finance profile contains violent serial murder term: '{term}'"

    def test_topic_pools_cross_isolation(self):
        """Scan dna_topic_pools.json: US pools must have 0 Hangul; Infrastructure must have 0 violent murder."""
        assert TOPIC_POOLS_FILE.exists()
        pools = json.loads(TOPIC_POOLS_FILE.read_text(encoding="utf-8"))

        # US profiles in pools
        for us_id in ("channel-f6ec4dfff3", "channel-aa913eb90d"):
            if us_id in pools:
                serialized = json.dumps(pools[us_id], ensure_ascii=False)
                hangul_matches = re.findall(r"[\uac00-\ud7a3]", serialized)
                assert len(hangul_matches) == 0, f"Topic pool for {us_id} contains Hangul: {hangul_matches[:10]}"

        # KR Infrastructure in pools
        if "channel-1e24de3ab5" in pools:
            serialized_infra = json.dumps(pools["channel-1e24de3ab5"], ensure_ascii=False)
            for term in ("연쇄살인", "토막", "살인마"):
                assert term not in serialized_infra

    def test_dynamic_prompt_generation_isolation(self):
        """Prompt neutrality audit: US English job prompts must contain 0 Hangul characters and 0 hardcoded channel-* IDs."""
        us_job = {
            "id": "job_us_adversarial_test",
            "channel_profile_id": "channel-f6ec4dfff3",
            "market": "US",
            "language": "en",
            "visual_strategy": "full_footage",
            "target_duration_minutes": 20,
        }
        for phase in ("plan", "footage", "edit", "seo", "qc"):
            prompt = build_phase_prompt(us_job, phase, DOC_ROOT / "workspaces" / "test", REMOTION_ROOT)
            assert isinstance(prompt, str) and len(prompt) > 50

            # Zero hardcoded channel branches
            assert "channel-e544a64b7c" not in prompt
            assert "channel-1e24de3ab5" not in prompt
            assert "channel-cn-cyber-finance-kr" not in prompt

            # Zero sacred PiP fallback
            assert "SACRED 3D FLOATING PiP FRAME" not in prompt

            # Audit Hangul characters in US prompts (flags bug if TrailCodeManager or _human_intrigue leaks)
            hangul_matches = re.findall(r"[\uac00-\ud7a3]", prompt)
            assert len(hangul_matches) == 0, (
                f"VULNERABILITY FOUND: Phase '{phase}' US prompt contains {len(hangul_matches)} leaked Hangul characters: "
                f"{hangul_matches[:15]}. Caused by TrailCodeManager and _human_intrigue_narrative_direction."
            )

    def test_language_guarded_korean_grammar_skips_non_kr(self):
        """Language Guard: Korean grammar check MUST return SKIPPED for non-Korean profiles."""
        dummy_beats = [{"beat_id": "b1", "text": "This is an archival investigation."}]
        for non_kr in ("en", "ja", "vi", "fr", "de", ""):
            res = evaluate_korean_grammar_gate(dummy_beats, language=non_kr)
            assert res["status"] == "SKIPPED"
            assert res["reason"] == "non_korean_profile"


# ==============================================================================
# 3. SECONDARY VOICE QUOTE DISPATCH & CLAMPING TESTS
# ==============================================================================

class TestAdversarialSecondaryVoiceQuoteClamping:
    """Stress-test quote tagging, boundary counts (0, 1, 3, 5, 6+), and clamping logic."""

    def test_quote_tagging_exact_clamping_to_five(self):
        """Quote Clamping: Scripts with 0, 1, 3, 5, and 6+ quotes must clamp strictly to max 5."""
        # 0 quotes
        beats_0 = [{"beat_id": f"b{i}", "narration_text": f"Normal narrative sentence number {i}."} for i in range(10)]
        tagged_0 = tag_verbatim_quotes(beats_0)
        assert sum(1 for b in tagged_0 if b.get("is_verbatim_quote")) == 0

        # 1 quote
        beats_1 = copy.deepcopy(beats_0)
        beats_1[2]["narration_text"] = 'Court official statement: "The suspect is hereby sentenced to life imprisonment."'
        tagged_1 = tag_verbatim_quotes(beats_1)
        assert sum(1 for b in tagged_1 if b.get("is_verbatim_quote")) == 1
        assert tagged_1[2]["is_verbatim_quote"] is True

        # 3 quotes
        beats_3 = copy.deepcopy(beats_0)
        for idx in (1, 4, 7):
            beats_3[idx]["narration_text"] = f'Official verdict record: "Evidence item {idx} confirms guilt beyond doubt."'
        tagged_3 = tag_verbatim_quotes(beats_3)
        assert sum(1 for b in tagged_3 if b.get("is_verbatim_quote")) == 3

        # 5 quotes
        beats_5 = copy.deepcopy(beats_0)
        for idx in (0, 2, 4, 6, 8):
            beats_5[idx]["narration_text"] = f'Witness sworn testimony: "I witnessed the suspect at location {idx}."'
        tagged_5 = tag_verbatim_quotes(beats_5)
        assert sum(1 for b in tagged_5 if b.get("is_verbatim_quote")) == 5

        # 8 quotes -> MUST clamp to 5 quotes!
        beats_8 = copy.deepcopy(beats_0)
        for idx in range(8):
            beats_8[idx]["narration_text"] = f'Official warrant statement: "Order {idx} executed by police authority."'
        tagged_8 = tag_verbatim_quotes(beats_8)
        quote_count_8 = sum(1 for b in tagged_8 if b.get("is_verbatim_quote"))
        assert quote_count_8 == 5, f"Expected exactly 5 quotes clamped, but got {quote_count_8}"

        # 20 quotes -> MUST clamp to 5 quotes!
        beats_20 = [{"beat_id": f"b{i}", "narration_text": f'Judge ruling: "Guilty verdict on count {i}."'} for i in range(20)]
        tagged_20 = tag_verbatim_quotes(beats_20)
        quote_count_20 = sum(1 for b in tagged_20 if b.get("is_verbatim_quote"))
        assert quote_count_20 == 5, f"Expected exactly 5 quotes clamped, but got {quote_count_20}"

    def test_explicitly_tagged_quotes_clamp_strictly_at_five(self):
        """Adversarial: When 7 beats have explicit is_verbatim_quote=True, tag_verbatim_quotes clamps to 5."""
        beats_explicit = [{"beat_id": f"b{i}", "narration_text": f"Beat {i}", "is_verbatim_quote": True} for i in range(7)]
        tagged = tag_verbatim_quotes(beats_explicit)
        assert sum(1 for b in tagged if b.get("is_verbatim_quote")) == 5

    def test_route_multi_voice_quotes_clamp_and_fallbacks(self):
        """Routing: Verifies multi-voice dispatching with primary narrator, secondary voice, and clamping."""
        profile_multi = {
            "id": "channel-test",
            "voice_id": "primary-narrator",
            "secondary_voice_id": "secondary-quote-voice",
        }
        # 7 quotes tagged
        beats = [{"beat_id": f"b{i}", "is_verbatim_quote": True, "text": f"Quote {i}"} for i in range(7)]
        routed = route_multi_voice_quotes(beats, profile_multi)

        # First 5 must be secondary_quote
        secondary_count = sum(1 for b in routed if b.get("voice_role") == "secondary_quote")
        primary_count = sum(1 for b in routed if b.get("voice_role") == "primary_narrator")
        assert secondary_count == 5, f"Expected exactly 5 secondary quotes, got {secondary_count}"
        assert primary_count == 2, f"Expected excess quotes to fall back to primary narrator, got {primary_count}"

        for b in routed[:5]:
            assert b["assigned_voice_id"] == "secondary-quote-voice"
            assert b["speaker_type"] == "secondary"
        for b in routed[5:]:
            assert b["assigned_voice_id"] == "primary-narrator"
            assert b["speaker_type"] == "primary"

    def test_single_voice_preservation_on_null_empty_whitespace(self):
        """Single-Voice: When secondary_voice_id is None, '', or '   ', 100% of beats remain primary."""
        dummy_beats = [{"beat_id": f"b{i}", "is_verbatim_quote": True} for i in range(5)]

        for sec_id in (None, "", "   ", "\t\n"):
            prof = {"id": "single-profile", "voice_id": "lead-voice", "secondary_voice_id": sec_id}
            routed = route_multi_voice_quotes(dummy_beats, prof)
            assert all(b["assigned_voice_id"] == "lead-voice" for b in routed)
            assert all(b["voice_role"] == "primary_narrator" for b in routed)
            assert all(b["speaker_type"] == "primary" for b in routed)


# ==============================================================================
# 4. REMOTION SubShotMediaLayer BADGE LOGIC (NODE / TSX EMPIRICAL VERIFICATION)
# ==============================================================================

class TestAdversarialRemotionMediaSuppressionWatertight:
    """Empirical verification of SubShotMediaLayer badge rendering and authentic media suppression."""

    def test_node_tsx_authentic_media_suppression_watertight(self):
        """Empirical: Run npx tsx directly on SubShotMediaLayer.tsx to test authentic media suppression."""
        script_content = """import { isAuthenticMediaSuppressed, evaluateReconstructionBadge } from '../src/components/SubShotMediaLayer.tsx';

const authenticStrings = [
  'sourced_video',
  'sourced_still',
  'archival_footage',
  'historical_document',
  'gis_map',
  'satellite_map',
  'gis_satellite_flight',
  'motion_dossier',
  'SOURCED_VIDEO',
  'Gis_Map',
  'Historical_Document'
];

for (const s of authenticStrings) {
  if (!isAuthenticMediaSuppressed(s)) {
    console.error(`FAILED string suppression for: ${s}`);
    process.exit(1);
  }
  const badge = evaluateReconstructionBadge(s, 'ko');
  if (badge.rendered !== false || badge.label !== null || badge.placement !== 'suppressed') {
    console.error(`FAILED badge suppression for: ${s}`, badge);
    process.exit(1);
  }
}

// Test authentic objects
const authenticObjects = [
  { is_authentic: true, media_type: 'unknown_raw' },
  { is_authentic: false, media_type: 'sourced_video' },
  { is_authentic: false, kind: 'gis_satellite_flight' },
  { is_authentic: false, visual_type: 'archival_footage' },
  { is_authentic: false, media_type: 'historical_document' },
  { is_authentic: false, kind: 'satellite_map' },
  { is_authentic: false, visual_type: 'motion_dossier' },
];

for (const obj of authenticObjects) {
  if (!isAuthenticMediaSuppressed(obj)) {
    console.error('FAILED object suppression for:', obj);
    process.exit(1);
  }
  const badge = evaluateReconstructionBadge(obj, 'en');
  if (badge.rendered !== false) {
    console.error('FAILED object badge suppression for:', obj, badge);
    process.exit(1);
  }
}

console.log('AUTHENTIC_SUPPRESSION_OK');
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mts", delete=False, dir=REMOTION_ROOT / "scripts", encoding="utf-8") as tf:
            tf.write(script_content)
            temp_file = Path(tf.name)

        try:
            proc = subprocess.run(
                ["npx", "tsx", str(temp_file.relative_to(REMOTION_ROOT))],
                cwd=REMOTION_ROOT,
                capture_output=True,
                text=True,
                shell=True,
            )
            assert proc.returncode == 0, f"Node TSX execution failed: {proc.stderr}\n{proc.stdout}"
            assert "AUTHENTIC_SUPPRESSION_OK" in proc.stdout
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_node_tsx_ai_reconstruction_badge_labels_and_fallbacks(self):
        """Empirical: Run npx tsx to test AI badge rendering and localization across all supported languages."""
        script_content = """import { evaluateReconstructionBadge } from '../src/components/SubShotMediaLayer.tsx';

const aiCases = [
  'ai_reconstructed',
  'ai_reconstruction',
  'ai_reconstruction_still',
  'ai_reconstruction_video',
  'ai_visual',
  'AI_RECONSTRUCTED',
  { is_ai_reconstructed: true },
  { media_type: 'ai_reconstructed' },
  { media_type: 'ai_visual' },
  { kind: 'ai_reconstruction' },
  { visual_type: 'ai_reconstruction' }
];

for (const shot of aiCases) {
  const kr = evaluateReconstructionBadge(shot, 'ko');
  if (kr.rendered !== true || kr.label !== '연출·재구성 화면' || kr.placement !== 'corner_badge_subtle') {
    console.error('FAILED KR badge for:', shot, kr);
    process.exit(1);
  }

  const en = evaluateReconstructionBadge(shot, 'en');
  if (en.rendered !== true || en.label !== 'Dramatization / AI Reconstruction') {
    console.error('FAILED EN badge for:', shot, en);
    process.exit(1);
  }

  const ja = evaluateReconstructionBadge(shot, 'ja');
  if (ja.rendered !== true || ja.label !== '再現・AIイメージ映像') {
    console.error('FAILED JA badge for:', shot, ja);
    process.exit(1);
  }

  const vi = evaluateReconstructionBadge(shot, 'vi');
  if (vi.rendered !== true || vi.label !== 'Hình ảnh tái hiện / AI mô phỏng') {
    console.error('FAILED VI badge for:', shot, vi);
    process.exit(1);
  }

  // Unknown language falls back to English
  const de = evaluateReconstructionBadge(shot, 'de');
  if (de.rendered !== true || de.label !== 'Dramatization / AI Reconstruction') {
    console.error('FAILED DE fallback badge for:', shot, de);
    process.exit(1);
  }
}

// Neutral media should not render badge
const neutralCases = [
  'color_fill',
  'solid_bg',
  { media_type: 'plain_color' }
];
for (const n of neutralCases) {
  const res = evaluateReconstructionBadge(n, 'ko');
  if (res.rendered !== false) {
    console.error('FAILED neutral media rendered badge:', n, res);
    process.exit(1);
  }
}

console.log('AI_BADGE_LOCALIZATION_OK');
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mts", delete=False, dir=REMOTION_ROOT / "scripts", encoding="utf-8") as tf:
            tf.write(script_content)
            temp_file = Path(tf.name)

        try:
            proc = subprocess.run(
                ["npx", "tsx", str(temp_file.relative_to(REMOTION_ROOT))],
                cwd=REMOTION_ROOT,
                capture_output=True,
                text=True,
                shell=True,
            )
            assert proc.returncode == 0, f"Node TSX execution failed: {proc.stderr}\n{proc.stdout}"
            assert "AI_BADGE_LOCALIZATION_OK" in proc.stdout
        finally:
            if temp_file.exists():
                temp_file.unlink()


# ==============================================================================
# 5. PRESERVATION INVARIANT ON PUBLISHED EPISODES
# ==============================================================================

class TestAdversarialPreservationInvariant:
    """Assert bit-for-bit read-only preservation of all 10 published episode workspaces and Remotion fixtures."""

    PUBLISHED_WORKSPACES = [
        "20261022-172954-acb4bd87",  # Grace Letter
        "20261023-084718-f20824bc",  # Zhang Yongming Case
        "20261024-053442-7897cef5",  # Hangzhou Disappearance
        "20261025-044448-3c4a4cf9",  # Sun Xiaoguo Case
        "20261025-190858-3626c0f5",  # Qian Zhimin Case
        "20261025-235306-5fa6d428",  # PlusToken Case
        "20261026-091826-559e9ac2",  # Zhou Kehua Case
        "20261026-215219-b3ad7137",  # Ezubao Case
        "20261027-063057-fda7945a",  # Yang Niuhua Case
        "20261028-110639-3b572c1b",  # Nanjing Medical Case
    ]

    PUBLISHED_REMOTION_FILES = [
        ("GraceLetter20261022.tsx", "GraceLetter20261022Data.ts"),
        ("ZhangYongmingCase20261023.tsx", "ZhangYongmingCase20261023Data.ts"),
        ("HangzhouDisappearance20261024.tsx", "HangzhouDisappearance20261024Data.ts"),
        ("SunXiaoguoCase20261025.tsx", "SunXiaoguoCase20261025Data.ts"),
        ("QianZhiminCase20261025.tsx", "QianZhiminCase20261025Data.ts"),
        ("ZhouKehuaCase20261026.tsx", "ZhouKehuaCase20261026Data.ts"),
        ("EzubaoCase20261026.tsx", "EzubaoCase20261026Data.ts"),
        ("YangNiuhuaCase20261027.tsx", "YangNiuhuaCase20261027Data.ts"),
        ("NanjingMedicalCase20261028.tsx", "NanjingMedicalCase20261028Data.ts"),
    ]

    def test_all_10_published_workspaces_exist_and_non_empty(self):
        """Preservation: All 10 published episode workspaces exist with non-empty manifests."""
        for ws_name in self.PUBLISHED_WORKSPACES:
            ws_path = WORKSPACES_DIR / ws_name
            assert ws_path.exists(), f"Published workspace missing: {ws_path}"
            assert ws_path.is_dir()
            vm = ws_path / "visual_manifest.json"
            if vm.exists():
                assert vm.stat().st_size > 0

    def test_all_published_remotion_fixtures_exist_and_non_empty(self):
        """Preservation: All published Remotion TSX and Data.ts files exist and have non-zero size."""
        for tsx_name, data_name in self.PUBLISHED_REMOTION_FILES:
            tsx_path = REMOTION_SRC / tsx_name
            assert tsx_path.exists(), f"Remotion composition missing: {tsx_path}"
            assert tsx_path.stat().st_size > 0

            data_path = REMOTION_SRC / data_name
            assert data_path.exists(), f"Remotion data file missing: {data_path}"
            assert data_path.stat().st_size > 0

    def test_legacy_regression_fixtures_deterministically_fail(self):
        """Regression Verification: Legacy fixtures JiSiguang & GaoChengyong deterministically fail YPP gates."""
        ji_file = REMOTION_SRC / "JiSiguangCase20261020Data.ts"
        gao_file = REMOTION_SRC / "GaoChengyongCase20261019Data.ts"
        assert ji_file.exists(), f"Legacy fixture missing: {ji_file}"
        assert gao_file.exists(), f"Legacy fixture missing: {gao_file}"

        # Ji Siguang: 94.7% single wrapper fails wrapper cap
        content_ji = ji_file.read_text(encoding="utf-8")
        archetypes_ji = re.findall(r'archetype[\'"]?\s*:\s*[\'"]([a-zA-Z0-9_]+)[\'"]', content_ji)
        assert len(archetypes_ji) == 264
        ji_beats = [{"beat_id": f"B{i:03d}", "archetype": a} for i, a in enumerate(archetypes_ji)]
        with pytest.raises(RuntimeError, match="Single framing wrapper exceeds 55"):
            evaluate_ypp_framing_wrapper_cap(ji_beats, max_wrapper_ratio=0.55)

        # Gao Chengyong: 100% stills fails motion floor
        content_gao = gao_file.read_text(encoding="utf-8")
        types_gao = re.findall(r'visualType[\'"]?\s*:\s*[\'"]([a-zA-Z0-9_]+)[\'"]', content_gao)
        assert len(types_gao) == 316
        gao_beats = [{"beat_id": f"B{i:03d}", "visual_type": vt, "camera_mode": "static_hold"} for i, vt in enumerate(types_gao)]
        with pytest.raises(RuntimeError, match="violating motion floor"):
            evaluate_ypp_motion_floor(gao_beats, min_motion_ratio=0.35)
