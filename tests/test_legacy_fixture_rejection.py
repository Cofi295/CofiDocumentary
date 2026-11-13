"""Feature 27: Legacy Fixture Rejection Test Suite.

Authoritative verification of deterministic YouTube Partner Program (YPP) quality gate
rejections across historical legacy published fixtures:
1. JiSiguangCase20261020Data.ts (94.70% single-wrapper dominance fails evaluate_ypp_framing_wrapper_cap)
2. GaoChengyongCase20261019Data.ts (100% static AI stills fails evaluate_ypp_motion_floor)
3. Duplicate BGM set reuse from data/bgm_usage_history.json fails evaluate_ypp_bgm_anti_repetition
4. Abrupt outro tail < 3.5s (2.0s, 3.49s) fails evaluate_ypp_outro_audio_tail
"""

import collections
import json
from pathlib import Path
import re
import pytest

from documentary.quality import (
    evaluate_ypp_framing_wrapper_cap,
    evaluate_ypp_motion_floor,
    evaluate_ypp_bgm_anti_repetition,
    evaluate_ypp_outro_audio_tail,
)

ROOT = Path(__file__).resolve().parent.parent
REMOTION_SRC = ROOT.parent / "CofiRemotion" / "src"
BGM_HISTORY_FILE = ROOT / "data" / "bgm_usage_history.json"


class TestLegacyFixtureRejection:
    """Explicitly verifies deterministic rejection of hazardous legacy fixtures by YPP quality gates."""

    def test_jisiguang_legacy_fixture_rejected_by_wrapper_cap(self):
        """JiSiguangCase20261020Data.ts (94.70% split_screen_investigation dominance)
        is deterministically rejected by evaluate_ypp_framing_wrapper_cap.
        """
        ji_file = REMOTION_SRC / "JiSiguangCase20261020Data.ts"
        assert ji_file.exists(), f"Legacy fixture missing: {ji_file}"

        content = ji_file.read_text(encoding="utf-8")
        archetypes = re.findall(r'archetype[\'"]?\s*:\s*[\'"]([a-zA-Z0-9_]+)[\'"]', content)
        assert len(archetypes) == 264, f"Expected 264 beats in JiSiguang fixture, found {len(archetypes)}"

        counts = collections.Counter(archetypes)
        dominant, dominant_count = counts.most_common(1)[0]
        dominance_ratio = dominant_count / len(archetypes)

        assert dominant == "split_screen_investigation"
        assert dominant_count == 250
        assert round(dominance_ratio * 100, 2) == 94.70

        beats = [{"beat_id": f"B{i:03d}", "archetype": a} for i, a in enumerate(archetypes)]

        # Must deterministically raise RuntimeError exceeding 55% cap
        with pytest.raises(RuntimeError, match="Single framing wrapper exceeds 55"):
            evaluate_ypp_framing_wrapper_cap(beats, max_wrapper_ratio=0.55)

    def test_gaochengyong_legacy_fixture_rejected_by_motion_floor(self):
        """GaoChengyongCase20261019Data.ts (100% ai_reconstruction_still, 0% motion)
        is deterministically rejected by evaluate_ypp_motion_floor.
        """
        gao_file = REMOTION_SRC / "GaoChengyongCase20261019Data.ts"
        assert gao_file.exists(), f"Legacy fixture missing: {gao_file}"

        content = gao_file.read_text(encoding="utf-8")
        kinds = re.findall(r'"kind":\s*"([^"]+)"', content)
        assert len(kinds) == 316, f"Expected 316 beats in GaoChengyong fixture, found {len(kinds)}"

        counts = collections.Counter(kinds)
        assert counts["ai_reconstruction_still"] == 316, "Expected 100% static AI stills"

        beats = [{"beat_id": f"B{i:03d}", "kind": k, "camera_mode": "static_hold"} for i, k in enumerate(kinds)]

        # Must deterministically raise RuntimeError violating motion floor
        with pytest.raises(RuntimeError, match="static-still slideshow violating motion floor"):
            evaluate_ypp_motion_floor(beats, min_motion_ratio=0.35)

    def test_duplicate_bgm_history_rejected_by_anti_repetition_gate(self):
        """Reusing an identical 10-track BGM set from data/bgm_usage_history.json
        is deterministically rejected by evaluate_ypp_bgm_anti_repetition.
        """
        assert BGM_HISTORY_FILE.exists(), f"BGM history file missing: {BGM_HISTORY_FILE}"
        history = json.loads(BGM_HISTORY_FILE.read_text(encoding="utf-8"))
        episodes = history.get("episodes", {})
        assert "20261028-110639-3b572c1b" in episodes

        duplicate_tracks = episodes["20261028-110639-3b572c1b"]["tracks_used"]
        channel_id = episodes["20261028-110639-3b572c1b"]["channel_profile_id"]

        assert len(duplicate_tracks) >= 8, f"Expected multi-track BGM score, found {len(duplicate_tracks)}"

        # Deterministic rejection of verbatim duplicate BGM set
        with pytest.raises(RuntimeError, match="Duplicate BGM set detected"):
            evaluate_ypp_bgm_anti_repetition(channel_id, duplicate_tracks, BGM_HISTORY_FILE)

        # Confirm non-colliding rotated BGM tracks pass cleanly
        fresh_tracks = [
            "bgm_fresh_noir_01.mp3",
            "bgm_fresh_noir_02.mp3",
            "bgm_fresh_noir_03.mp3",
            "bgm_fresh_noir_04.mp3",
        ]
        result = evaluate_ypp_bgm_anti_repetition(channel_id, fresh_tracks, BGM_HISTORY_FILE)
        assert result["status"] == "PASSED"
        assert result["tracks_count"] == 4

    def test_outro_audio_tail_under_boundary_rejected(self):
        """Outro audio tail < 3.5s (e.g. 2.0s, 3.49s) is deterministically rejected
        while tails >= 3.5s pass.
        """
        # Strictly reject < 3.5s
        with pytest.raises(RuntimeError, match="Missing 3.5-4.5s outro audio fade tail"):
            evaluate_ypp_outro_audio_tail(2.0, min_tail_sec=3.5)

        with pytest.raises(RuntimeError, match="Missing 3.5-4.5s outro audio fade tail"):
            evaluate_ypp_outro_audio_tail(3.49, min_tail_sec=3.5)

        # Accept compliant outro tails
        pass_boundary = evaluate_ypp_outro_audio_tail(3.50, min_tail_sec=3.5)
        assert pass_boundary["status"] == "PASSED"
        assert pass_boundary["outro_tail_sec"] == 3.50
        assert pass_boundary["in_ideal_range"] is True

        pass_ideal = evaluate_ypp_outro_audio_tail(4.0, min_tail_sec=3.5)
        assert pass_ideal["status"] == "PASSED"
        assert pass_ideal["in_ideal_range"] is True
