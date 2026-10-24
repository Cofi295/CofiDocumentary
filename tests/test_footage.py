import json
from pathlib import Path
import re

import pytest

from documentary.codex_gateway import StageResult
from documentary.footage import FootageCoordinator, _json_object_from_message, build_preflight, build_worker_prompt, merge_worker_results, partition_beats
from documentary.footage_engine import FootageEngine
from documentary.prompts import build_phase_prompt
from documentary.quality import _native_motion_beat_ids, normalize_production_recipe, validate_phase_quality


def _prompt_beats(prompt: str) -> list[dict]:
    match = re.search(r"Các visual beat được giao: (.*?)\n\nLàm việc", prompt, flags=re.S)
    assert match
    return json.loads(match.group(1))


def _prompt_output(prompt: str) -> Path:
    match = re.search(r"Chỉ ghi output vào `([^`]+)`", prompt)
    assert match
    return Path(match.group(1))


def test_codex_review_parser_accepts_markdown_escaped_json():
    payload = _json_object_from_message(
        r'{"reviews":\[{"beat\_id":"B001","candidate\_id":"VQ-1","decision":"ACCEPT"}\]}'
    )

    assert payload["reviews"][0]["beat_id"] == "B001"


def test_footage_defaults_limit_chatgpt_turn_count(monkeypatch):
    monkeypatch.delenv("COFI_FOOTAGE_BATCH_SIZE", raising=False)
    monkeypatch.delenv("COFI_FOOTAGE_BATCH_RETRIES", raising=False)
    monkeypatch.delenv("COFI_FOOTAGE_ADAPTIVE_BATCHING", raising=False)
    monkeypatch.delenv("COFI_FOOTAGE_BATCH_MAX_SIZE", raising=False)

    coordinator = FootageCoordinator(object(), object())

    assert coordinator.batch_size == 4
    assert coordinator.adaptive_batching is True
    assert coordinator.batch_max_size == 8
    assert coordinator.batch_retries == 3


def test_vision_review_frames_cover_every_candidate_even_when_soft_limit_is_smaller(tmp_path: Path):
    candidates = []
    for index in range(14):
        frame = tmp_path / f"candidate_{index:02d}_frame_01.jpg"
        frame.write_bytes(b"frame")
        candidates.append({
            "candidate_id": f"FT-B001-{index:02d}",
            "kind": "sourced_video",
            "representative_frames": [str(frame)],
        })

    image_paths = FootageCoordinator._review_image_paths(candidates, max_total=12)

    assert len(image_paths) == 14
    assert {Path(path).name for path in image_paths} == {
        f"candidate_{index:02d}_frame_01.jpg" for index in range(14)
    }


def test_vision_review_frames_attach_two_distinct_video_frames_per_candidate(tmp_path: Path):
    candidates = []
    expected = set()
    for index in range(3):
        frames = []
        for frame_index in range(1, 5):
            frame = tmp_path / f"candidate_{index:02d}_frame_{frame_index:02d}.jpg"
            frame.write_bytes(b"frame")
            frames.append(str(frame))
            if frame_index <= 2:
                expected.add(frame.name)
        candidates.append({
            "candidate_id": f"FT-B001-{index:02d}",
            "kind": "sourced_video",
            "representative_frames": frames,
        })

    image_paths = FootageCoordinator._review_image_paths(candidates, max_total=6)

    assert len(image_paths) == 6
    assert {Path(path).name for path in image_paths} == expected


def test_footage_engine_caps_review_candidates_without_local_vision_provider(monkeypatch):
    monkeypatch.delenv("COFI_FOOTAGE_MAX_CANDIDATES_PER_BEAT", raising=False)

    engine = FootageEngine(source_discovery=object(), retriever=object(), vision_provider=None)

    assert engine.max_total_candidates_per_beat == 4


def test_rate_limit_is_retried_as_a_transient_failure():
    coordinator = FootageCoordinator(object(), object())
    result = StageResult(1, "ChatGPT rate limit: too many requests", Path("events.jsonl"))

    assert coordinator._is_transient_failure(result) is True
    assert coordinator._is_rate_limit_failure(result) is True


def test_worker_prompt_uses_one_bounded_full_download_fallback_after_section_403(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Pantanal", "market": "VN", "language": "vi"},
        [{"beat_id": "B001", "target_duration_sec": 8, "visual_type": "sourced_video"}],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    lower = prompt.lower()
    assert "403" in lower
    assert "tải full" in lower
    assert "đúng 1 lần" in lower
    assert "ffmpeg" in lower
    assert "cắt" in lower
    assert "nếu lần tải full" in lower
    assert "bỏ url/video id đó" in lower
    assert "cùng host" not in lower


def test_worker_prompt_requires_incremental_batch_progress_after_each_beat(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Pantanal", "market": "VN", "language": "vi"},
        [
            {"beat_id": "B001", "target_duration_sec": 8, "visual_type": "sourced_video"},
            {"beat_id": "B002", "target_duration_sec": 8, "visual_type": "sourced_video"},
        ],
        "codex",
        tmp_path,
        ".producer/footage_codex/batches/batch_0001.json",
    )

    lower = prompt.lower()
    assert "ngay sau khi hoàn tất từng beat" in lower
    assert "status=in_progress" in lower
    assert "temporary file" in lower
    assert "không chờ đến cuối batch" in lower


def test_worker_prompt_allows_ordinary_youtube_as_fallback_with_explicit_rights_risk(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Pantanal", "market": "VN", "language": "vi"},
        [{"beat_id": "B001", "target_duration_sec": 8, "visual_type": "sourced_video"}],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    lower = prompt.lower()
    assert "youtube thông thường" in lower
    assert "không tự coi" in lower
    assert "rights-risk" in lower
    assert "nhà đài" in lower
    assert "review" in lower


def test_worker_prompt_uses_web_embedded_client_before_full_download_fallback(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Pantanal", "market": "VN", "language": "vi"},
        [{"beat_id": "B001", "target_duration_sec": 8, "visual_type": "sourced_video"}],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    lower = prompt.lower()
    assert "youtube:player_client=web_embedded" in lower
    assert "video-only" in lower
    assert "403" in lower


def test_worker_prompt_treats_verified_sources_as_avoid_reuse_hints_and_keeps_media_tool_output_compact(tmp_path: Path):
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "in_progress",
        "candidates": [{
            "candidate_id": "C_B001_01",
            "beat_id": "B001",
            "decision": "ACCEPT",
            "source_url": "https://www.youtube.com/watch?v=verified-source",
            "local_path": str(tmp_path / "media" / "codex" / "B001.mp4"),
            "timestamp_range": "00:00:10-00:00:17",
            "reason": "Verified archival Woodrow Wilson source from the correct period.",
        }],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")

    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Edith Wilson", "market": "US", "language": "en"},
        [{"beat_id": "B009", "target_duration_sec": 7, "visual_type": "sourced_video", "source_priority": "prefer_real"}],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    lower = prompt.lower()
    assert "verified-source" in prompt
    assert "nguồn đã dùng" in lower
    assert "tránh trùng" in lower
    assert "intentional_reuse=true" in lower
    assert "reuse_reason" in lower
    assert "ai_fallback_recommended=true" in lower
    assert "--quiet" in lower
    assert "-hide_banner" in lower
    assert "-loglevel error" in lower
    assert "tối đa 4" in lower
    assert "tối đa 2" in lower


def test_worker_prompt_groups_duplicate_search_queries_once_per_batch(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Edith Wilson", "market": "US", "language": "en"},
        [
            {
                "beat_id": "B113",
                "target_duration_sec": 7,
                "visual_type": "sourced_video",
                "footage_search_queries": [
                    "White House interior corridor archival footage 1919",
                    "Washington government offices 1919 archival film newspapers",
                ],
            },
            {
                "beat_id": "B115",
                "target_duration_sec": 7,
                "visual_type": "sourced_video",
                "footage_search_queries": [
                    "White House interior corridor archival footage 1919",
                    "Washington government offices 1919 archival film newspapers",
                ],
            },
            {
                "beat_id": "B120",
                "target_duration_sec": 7,
                "visual_type": "sourced_video",
                "footage_search_queries": ["Woodrow Wilson papers White House 1919"],
            },
        ],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    beats = _prompt_beats(prompt)
    assert beats[0]["search_group"] == beats[1]["search_group"]
    assert beats[0]["search_group"] != beats[2]["search_group"]
    lower = prompt.lower()
    assert "cùng `search_group`" in lower
    assert "chỉ chạy một lần trong batch" in lower


def test_worker_prompt_includes_prefetched_discovery_candidates_but_keeps_visual_gate(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Versailles", "market": "US", "language": "en"},
        [{
            "beat_id": "B001",
            "target_duration_sec": 7,
            "visual_type": "sourced_video",
            "footage_search_queries": ["Woodrow Wilson Versailles 1919 archival footage"],
        }],
        "codex",
        tmp_path,
        "footage_codex.json",
        discovery_by_beat={
            "B001": [{
                "provider": "nara",
                "source_url": "https://catalog.archives.gov/id/24746",
                "title": "Signing of the Peace Treaty of Versailles, 1919",
                "kind": "video",
                "discovery_score": 72.0,
            }],
        },
    )

    beats = _prompt_beats(prompt)
    assert beats[0]["discovery_candidates"][0]["provider"] == "nara"
    assert "24746" in prompt
    lower = prompt.lower()
    assert "discovery" in lower
    assert "chỉ là candidate" in lower
    assert "tải/preview nội dung thật" in lower


def test_worker_prompt_uses_local_repo_tools_before_codex_research_then_ai(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Versailles", "market": "US", "language": "en"},
        [{
            "beat_id": "B001",
            "target_duration_sec": 7,
            "visual_type": "sourced_video",
            "source_priority": "prefer_real",
            "footage_search_queries": ["Woodrow Wilson Versailles 1919 archival footage"],
        }],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    local_tool = prompt.index("python -m documentary.footage_search_tool")
    codex_research = prompt.index("Codex/Gemini research")
    ai_visual = prompt.index("AI visual")
    assert local_tool < codex_research < ai_visual
    assert "DDGS video + DDGS Images + internetarchive + yt-dlp + Openverse" in prompt


def test_worker_prompt_exposes_on_demand_candidate_inspection_tools(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Versailles", "market": "US", "language": "en"},
        [{
            "beat_id": "B001",
            "target_duration_sec": 7,
            "visual_type": "sourced_video",
            "footage_search_queries": ["Woodrow Wilson Versailles 1919 archival footage"],
        }],
        "codex",
        tmp_path,
        "footage_codex.json",
    )
    lower = prompt.lower()
    assert "footage_inspection_tool scenes" in lower
    assert "footage_inspection_tool dedupe" in lower
    assert "footage_inspection_tool gallery" in lower
    assert "footage_inspection_tool transcribe" in lower
    assert "footage_inspection_tool visual-score" not in lower
    assert "faster-whisper" in lower
    assert "caption/vtt" in lower


def test_worker_prompt_keeps_multiple_verified_clips_from_same_source_when_relevant(tmp_path: Path):
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "in_progress",
        "candidates": [
            {
                "candidate_id": "C_B001_01",
                "beat_id": "B001",
                "decision": "ACCEPT",
                "visually_inspected_actual_content": True,
                "source_url": "https://www.youtube.com/watch?v=nara-source",
                "source_title": "Woodrow Wilson 1917-1921",
                "source_channel": "US National Archives",
                "local_path": str(tmp_path / "media" / "codex" / "wilson-post-stroke.mp4"),
                "timestamp_range": "00:18:40-00:18:46",
                "reason": "Woodrow Wilson after his stroke at the White House.",
                "technical_check": "ffprobe OK",
            },
            {
                "candidate_id": "C_B002_01",
                "beat_id": "B002",
                "decision": "ACCEPT",
                "visually_inspected_actual_content": True,
                "source_url": "https://www.youtube.com/watch?v=nara-source",
                "source_title": "Woodrow Wilson 1917-1921",
                "source_channel": "US National Archives",
                "local_path": str(tmp_path / "media" / "codex" / "edith-papers.mp4"),
                "timestamp_range": "00:03:45-00:03:52",
                "reason": "Edith Wilson handling papers beside officials.",
                "technical_check": "ffprobe OK",
            },
        ],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")

    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Edith Wilson", "market": "US", "language": "en"},
        [{
            "beat_id": "B113",
            "narration_text": "Papers arrived. Edith reviewed them while Wilson remained isolated.",
            "visual_description": "Edith Wilson handling White House papers after Woodrow Wilson's stroke.",
            "target_duration_sec": 7,
            "visual_type": "sourced_video",
        }],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    assert "wilson-post-stroke.mp4" in prompt
    assert "edith-papers.mp4" in prompt
    assert '"prior_visual_verified":true' in prompt


def test_worker_prompt_searches_real_media_thoroughly_before_ai_fallback(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Pantanal", "market": "VN", "language": "vi"},
        [{"beat_id": "B001", "target_duration_sec": 8, "visual_type": "sourced_video", "source_priority": "prefer_real"}],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    lower = prompt.lower()
    assert "source_priority=must_real" in lower
    assert "source_priority=prefer_real" in lower
    assert "source_priority=ai_ok" in lower
    assert "ai_fallback_recommended" in prompt
    assert "ít nhất 3 truy vấn video" in lower
    assert "ảnh thật" in lower
    assert "chỉ" in lower and "ai" in lower and "không tìm được" in lower


def test_worker_prompt_enriches_legacy_native_motion_as_prefer_real_with_real_search(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Edith Wilson", "market": "US", "language": "en"},
        [{"beat_id": "B003", "target_duration_sec": 7, "visual_type": "native_motion", "footage_search_queries": []}],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    beats = _prompt_beats(prompt)
    assert beats[0]["source_priority"] == "prefer_real"
    assert beats[0]["search_budget"]["max_queries"] == 3
    assert beats[0]["search_budget"]["max_candidates"] == 4
    assert beats[0]["search_budget"]["immediate_ai_fallback"] is False
    lower = prompt.lower()
    assert "tự tạo truy vấn" in lower
    assert "footage thật" in lower


def test_worker_prompt_enriches_generic_legacy_sourced_video_as_real_first_prefer_real(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Edith Wilson", "market": "US", "language": "en"},
        [{"beat_id": "B001", "target_duration_sec": 7, "visual_type": "sourced_video"}],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    beats = _prompt_beats(prompt)
    assert beats[0]["source_priority"] == "prefer_real"
    assert beats[0]["search_budget"]["max_queries"] == 3
    assert beats[0]["search_budget"]["max_candidates"] == 4
    assert beats[0]["search_budget"]["immediate_ai_fallback"] is False


@pytest.mark.parametrize("priority", ["must_real", "prefer_real", "ai_ok"])
def test_worker_prompt_preserves_explicit_source_priority(tmp_path: Path, priority: str):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Edith Wilson", "market": "US", "language": "en"},
        [{"beat_id": "B001", "target_duration_sec": 7, "visual_type": "sourced_video", "source_priority": priority}],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    beats = _prompt_beats(prompt)
    assert beats[0]["source_priority"] == priority


def test_worker_prompt_allows_real_still_for_must_real_subject_after_fast_video_attempt(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Edith Wilson", "market": "US", "language": "en"},
        [{"beat_id": "B001", "target_duration_sec": 8, "visual_type": "sourced_video", "source_priority": "must_real"}],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    lower = prompt.lower()
    assert "must_real" in lower
    assert "ảnh thật" in lower
    assert "nhân vật chính" in lower
    assert "bối cảnh chính" in lower


def test_worker_prompt_stages_unreviewed_downloads_outside_visible_media_root(tmp_path: Path):
    prompt = build_worker_prompt(
        {"id": "job-1", "title": "Pantanal", "market": "VN", "language": "vi"},
        [{"beat_id": "B001", "target_duration_sec": 8, "visual_type": "sourced_video"}],
        "codex",
        tmp_path,
        "footage_codex.json",
    )

    lower = prompt.lower()
    assert "_inspection" in lower
    assert "chỉ" in lower
    assert "accept" in lower
    assert "review/reject" in lower
    assert "media/codex" in lower.replace("\\", "/")


def test_plan_prompt_does_not_plan_sourced_still_as_primary_visual(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job-1", "title": "Pantanal", "market": "VN", "language": "vi", "production_recipe": {}},
        "plan",
        tmp_path,
        tmp_path / "CofiRemotion",
    )

    lower = prompt.lower()
    assert "sourced_video" in lower
    assert "sourced_still" in lower
    assert "không" in lower
    assert "fallback" in lower
    assert "source_priority" in lower
    assert "must_real" in lower
    assert "prefer_real" in lower
    assert "ai_ok" in lower
    assert "ai_reconstruction" in lower
    assert "không dùng native_motion làm visual độc lập" in lower
    assert "mobile" in lower


def test_five_minute_recipe_does_not_require_or_target_sourced_stills():
    recipe = normalize_production_recipe(None, target_duration_minutes=5)
    contract = recipe["quality_contract"]

    assert contract["min_sourced_still_uses"] == 0
    assert contract["target_sourced_still_uses"] == 0
    assert contract["allow_ai_reconstruction_fallback"] is True
    assert contract["require_must_real_source_coverage"] is True
    assert contract["allow_standalone_native_motion"] is False
    assert contract["min_native_motion_treatments"] == 0
    assert str(recipe["target_still_image_count"]).startswith("0")


def test_five_minute_recipe_targets_dense_short_visual_cadence():
    recipe = normalize_production_recipe(None, target_duration_minutes=5)
    contract = recipe["quality_contract"]

    assert contract["min_scene_count"] >= 40
    assert contract["target_video_clip_uses"] >= 20
    assert contract["typical_shot_duration_sec"][1] <= 8
    assert contract["max_routine_shot_duration_sec"] <= 10
    assert contract["version"] == 7
    assert contract["editorial_style_tier"] == "premium_cinematic_motion_studio"
    assert contract["editorial_authority"] == "production_director_plus_senior_editor_10y"
    assert contract["require_second_by_second_attention_review"] is True
    assert contract["require_sequence_retention_rhythm_review"] is True
    assert contract["require_proactive_editorial_decisions"] is True
    assert contract["require_authored_visual_system"] is True
    assert contract["require_cinematic_typography_review"] is True
    assert contract["require_sound_design_review"] is True
    assert contract["require_asset_variety_review"] is True
    assert contract["require_intentional_reuse_review"] is True
    assert contract["asset_variety_is_soft_editorial_rule"] is True
    assert contract["max_unintentional_reuse_per_asset"] == 1
    assert contract["max_contextual_reuse_per_asset"] >= 3
    assert contract["require_media_anchored_annotation_motion"] is True
    assert contract["mobile_annotation_min_font_px"] >= 48
    assert contract["disallow_generic_native_motion_fallback_for_sourced_video"] is True
    assert contract["disallow_decorative_only_native_motion"] is True
    assert any("line/circle/callout" in rule for rule in recipe["editorial_rules"])
    assert any("never force every downloaded asset" in rule.lower() for rule in recipe["editorial_rules"])
    assert any("meaningful clauses" in rule.lower() for rule in recipe["editorial_rules"])


def test_coverage_snapshot_marks_standalone_native_motion_as_missing(tmp_path: Path):
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "beats": [{"beat_id": "B001", "visual_type": "native_motion"}],
    }), encoding="utf-8")
    (tmp_path / "voice_manifest.json").write_text(json.dumps({
        "beats": [{"beat_id": "B001"}],
    }), encoding="utf-8")
    (tmp_path / "asset_registry.json").write_text(json.dumps({
        "assets": [],
        "native_treatments": [{"id": "N1", "beat_id": "B001", "kind": "remotion_native_motion"}],
    }), encoding="utf-8")

    report = build_preflight(tmp_path)

    assert report["status"] == "FAIL"
    assert report["missing_beats"] == ["B001"]
    assert (tmp_path / "coverage_matrix.json").exists()
    assert (tmp_path / "preflight_report.json").exists()


def _strict_still_quality_job() -> dict:
    return {
        "production_recipe": {
            "quality_contract": {
                "enforce": True,
                "min_scene_count": 1,
                "min_video_clip_uses": 0,
                "min_native_motion_treatments": 0,
                "min_unique_video_sources": 0,
                "require_video_before_still_fallback": True,
                "min_video_search_queries_before_still": 2,
            }
        }
    }


def _write_single_still_quality_fixture(tmp_path: Path, candidate: dict, *, extra_candidates: list[dict] | None = None) -> None:
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "beats": [{"beat_id": "B001", "visual_type": "sourced_video"}],
    }), encoding="utf-8")
    (tmp_path / "footage_review.json").write_text(json.dumps({
        "candidates": [candidate, *(extra_candidates or [])],
    }), encoding="utf-8")
    (tmp_path / "asset_registry.json").write_text(json.dumps({
        "assets": [{
            "id": "I1",
            "beat_id": "B001",
            "kind": "sourced_still",
            "path": "still.jpg",
            "source": {"candidate_id": candidate["candidate_id"], "url": "https://image.test/1"},
        }],
        "native_treatments": [],
    }), encoding="utf-8")
    (tmp_path / "still.jpg").write_bytes(b"still")


def test_footage_quality_does_not_reapprove_accepted_still(tmp_path: Path):
    candidate = {
        "candidate_id": "I1",
        "beat_id": "B001",
        "decision": "ACCEPT",
        "kind": "sourced_still",
        "visually_inspected_actual_content": True,
    }
    _write_single_still_quality_fixture(tmp_path, candidate)

    validate_phase_quality("footage", tmp_path, _strict_still_quality_job())


def test_footage_quality_allows_still_only_after_documented_video_search_failure(tmp_path: Path):
    candidate = {
        "candidate_id": "I1",
        "beat_id": "B001",
        "decision": "ACCEPT",
        "kind": "sourced_still",
        "visually_inspected_actual_content": True,
        "video_search_queries_tried": ["Pantanal capybara river video", "Pantanal capybara water edge footage"],
        "video_search_no_results": True,
        "still_fallback_reason": "Không tìm được video usable đúng ngữ cảnh sau hai truy vấn độc lập.",
    }
    _write_single_still_quality_fixture(tmp_path, candidate)

    validate_phase_quality("footage", tmp_path, _strict_still_quality_job())


def test_footage_quality_does_not_reapprove_still_when_video_was_also_accepted(tmp_path: Path):
    candidate = {
        "candidate_id": "I1",
        "beat_id": "B001",
        "decision": "ACCEPT",
        "kind": "sourced_still",
        "visually_inspected_actual_content": True,
        "video_search_queries_tried": ["q1 video", "q2 footage"],
        "video_search_no_results": False,
        "still_fallback_reason": "Fallback thử nghiệm.",
    }
    accepted_video = {
        "candidate_id": "V1",
        "beat_id": "B001",
        "decision": "ACCEPT",
        "kind": "sourced_video",
        "visually_inspected_actual_content": True,
    }
    _write_single_still_quality_fixture(tmp_path, candidate, extra_candidates=[accepted_video])

    validate_phase_quality("footage", tmp_path, _strict_still_quality_job())


class FakeBatchGateway:
    available = True

    def __init__(
        self,
        fail_call: int | None = None,
        fail_message: str = "hard failure",
        fail_calls: set[int] | None = None,
        incomplete_calls: set[int] | None = None,
    ):
        self.calls: list[list[str]] = []
        self.fail_call = fail_call
        self.fail_calls = set(fail_calls or [])
        self.incomplete_calls = set(incomplete_calls or [])
        self.fail_message = fail_message
        self.resets = 0

    def run_prompt_reusable(self, prompt, workspace, label):
        beats = _prompt_beats(prompt)
        beat_ids = [beat["beat_id"] for beat in beats]
        self.calls.append(beat_ids)
        call_number = len(self.calls)
        if self.fail_call == call_number or call_number in self.fail_calls:
            return StageResult(1, self.fail_message, Path(workspace) / ".producer" / label)
        if call_number in self.incomplete_calls:
            return StageResult(0, "Chưa hoàn tất batch; cần tiếp tục từ dữ liệu đã tải.", Path(workspace) / ".producer" / label)
        output = _prompt_output(prompt)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({
            "worker": "codex",
            "status": "completed",
            "candidates": [
                {"candidate_id": f"C-{beat_id}", "beat_id": beat_id, "decision": "REVIEW"}
                for beat_id in beat_ids
            ],
            "assets": [],
            "native_treatments": [],
            "presentation_effects": [],
        }), encoding="utf-8")
        return StageResult(0, f"done {','.join(beat_ids)}", output)

    def reset_reusable_session(self, workspace, label, reason="manual_reset"):
        self.resets += 1
        return True


class DisabledGemini:
    available = False


def test_partition_beats_balances_duration_between_codex_and_gemini():
    beats = [
        {"beat_id": "B001", "target_duration_sec": 12},
        {"beat_id": "B002", "target_duration_sec": 10},
        {"beat_id": "B003", "target_duration_sec": 8},
        {"beat_id": "B004", "target_duration_sec": 6},
    ]
    result = partition_beats(beats)
    assert {b["beat_id"] for b in result["codex"] + result["gemini"]} == {"B001", "B002", "B003", "B004"}
    codex_total = sum(float(b["target_duration_sec"]) for b in result["codex"])
    gemini_total = sum(float(b["target_duration_sec"]) for b in result["gemini"])
    assert abs(codex_total - gemini_total) <= 8


def test_native_motion_quality_gate_accepts_composite_visual_type():
    beats = [
        {"beat_id": "B001", "visual_type": "sourced_video+still+native_motion"},
        {"beat_id": "B002", "visual_type": "sourced_video"},
    ]

    assert _native_motion_beat_ids(beats) == {"B001"}


def test_footage_coordinator_splits_codex_work_into_small_checkpointed_batches(tmp_path: Path):
    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 11)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    gateway = FakeBatchGateway()
    coordinator = FootageCoordinator(gateway, DisabledGemini(), batch_size=4, batch_retries=0)

    result = coordinator.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)

    checkpoint = json.loads((tmp_path / "footage_checkpoint.json").read_text(encoding="utf-8"))
    canonical = json.loads((tmp_path / "footage_codex.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert gateway.calls == [
        ["B001", "B002", "B003", "B004"],
        ["B005", "B006", "B007", "B008"],
        ["B009", "B010"],
    ]
    assert checkpoint["status"] == "completed"
    assert checkpoint["completed_beats"] == 10
    assert checkpoint["workers"]["codex"]["total_batches"] == 3
    assert gateway.resets == 0
    assert checkpoint["workers"]["codex"]["session_rotations"] == 0
    assert len(canonical["candidates"]) == 10


def test_vision_codex_mode_uses_semantic_candidates_and_ai_only_for_final_review(tmp_path: Path):
    beat = {
        "beat_id": "B001",
        "narration_text": "SK hynix is expanding its Yongin semiconductor cluster.",
        "visual_description": "SK hynix Yongin semiconductor construction site",
        "target_duration_sec": 8,
        "source_priority": "must_real",
    }
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": [beat]}), encoding="utf-8")
    still = tmp_path / "candidate.jpg"
    still.write_bytes(b"x" * 5000)
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"y" * 100)

    class LocalEngine:
        def prepare(self, job, beats, workspace):
            return {
                "worker": "vision",
                "status": "completed",
                "candidates": [{
                    "candidate_id": "FT-B001-01",
                    "beat_id": "B001",
                    "source_priority": "must_real",
                    "decision": "REVIEW",
                    "verification_provider": "openclip",
                    "visually_inspected_actual_content": False,
                    "source_url": "https://source.test/sk-hynix",
                    "local_path": str(still),
                    "kind": "sourced_still",
                    "timestamp_range": "00:01:10-00:01:18",
                    "representative_frames": [str(frame), str(still)],
                    "transcript_excerpt": "SK hynix Yongin semiconductor cluster",
                    "semantic_prefilter": {"semantic_score": 0.95, "provider": "openclip"},
                    "real_video_search_complete": True,
                    "real_still_search_complete": True,
                }],
                "assets": [],
                "native_treatments": [],
                "presentation_effects": [],
            }

    class ReviewGateway:
        def __init__(self):
            self.calls = []

        def status(self):
            return {"active_provider": "gemini", "preferred_provider": "gemini"}

        def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False, image_paths=None):
            self.calls.append({"prompt": prompt, "label": label, "images": list(image_paths or [])})
            return StageResult(
                0,
                json.dumps({
                    "reviews": [{
                        "beat_id": "B001",
                        "candidate_id": "FT-B001-01",
                        "decision": "ACCEPT",
                        "reason": "Exact visual match.",
                    }]
                }),
                Path(workspace) / ".producer" / label,
            )

    gateway = ReviewGateway()
    coordinator = FootageCoordinator(
        gateway,
        DisabledGemini(),
        footage_engine=LocalEngine(),
        batch_size=4,
        batch_retries=0,
    )

    result = coordinator.run({"id": "job-1", "title": "test", "footage_mode": "vision_codex"}, tmp_path)

    canonical = json.loads((tmp_path / "footage_codex.json").read_text(encoding="utf-8"))
    checkpoint = json.loads((tmp_path / "footage_checkpoint.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert len(gateway.calls) == 1
    assert gateway.calls[0]["label"] == "footage_codex_review"
    assert gateway.calls[0]["images"] == [str(frame.resolve())]
    assert "KHÔNG search web" in gateway.calls[0]["prompt"]
    assert canonical["candidates"][0]["decision"] == "ACCEPT"
    assert canonical["assets"][0]["source"]["candidate_id"] == "FT-B001-01"
    assert checkpoint["completed_beats"] == 1
    assert checkpoint["workers"]["codex"]["attempts"] == 1
    assert checkpoint["search_mode"] == "tools-only"
    assert checkpoint["review_provider"] == "gemini"


def test_vision_codex_reviews_ready_batches_before_engine_finishes_all_beats(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_VISION_REVIEW_BATCH_SIZE", "2")
    beats = [
        {
            "beat_id": f"B{i:03d}",
            "narration_text": f"Voice sentence {i}",
            "visual_description": f"Matching scene {i}",
            "target_duration_sec": 8,
            "source_priority": "must_real",
        }
        for i in range(1, 4)
    ]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    media_paths = {}
    for beat in beats:
        path = tmp_path / f"{beat['beat_id']}.jpg"
        path.write_bytes((beat["beat_id"].encode("utf-8") + b"x" * 5000))
        media_paths[beat["beat_id"]] = path

    class StreamingEngine:
        def __init__(self):
            self.approved_during_prepare = False

        def prepare(
            self,
            job,
            batch_beats,
            workspace,
            *,
            control_callback=None,
            progress_callback=None,
            discovery_progress_callback=None,
            prepared_beat_callback=None,
        ):
            candidates = []
            total = len(batch_beats)
            for index, beat in enumerate(batch_beats, start=1):
                beat_id = beat["beat_id"]
                path = media_paths[beat_id]
                candidate = {
                    "candidate_id": f"FT-{beat_id}-01",
                    "beat_id": beat_id,
                    "source_priority": "must_real",
                    "decision": "REVIEW",
                    "verification_provider": "semantic",
                    "visually_inspected_actual_content": False,
                    "source_url": f"https://source.test/{beat_id}",
                    "local_path": str(path),
                    "kind": "sourced_still",
                    "representative_frames": [str(path)],
                    "real_video_search_complete": True,
                    "real_still_search_complete": True,
                }
                candidates.append(candidate)
                if progress_callback is not None:
                    progress_callback(index, total, beat_id)
                if prepared_beat_callback is not None:
                    prepared_beat_callback(beat, [candidate], index, total)
                if index == 2:
                    approved_path = Path(workspace) / "footage_approved_live.json"
                    approved = json.loads(approved_path.read_text(encoding="utf-8"))
                    self.approved_during_prepare = bool(approved.get("items"))
            return {
                "worker": "vision",
                "status": "completed",
                "candidates": candidates,
                "assets": [],
                "native_treatments": [],
                "presentation_effects": [],
                "failures": [],
            }

    class ReviewGateway:
        def __init__(self):
            self.calls = 0

        def status(self):
            return {"active_provider": "gemini", "preferred_provider": "gemini"}

        def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False, image_paths=None):
            self.calls += 1
            beat_ids = ["B001", "B002"] if self.calls == 1 else ["B003"]
            return StageResult(
                0,
                json.dumps({
                    "reviews": [
                        {
                            "beat_id": beat_id,
                            "candidate_id": f"FT-{beat_id}-01",
                            "decision": "ACCEPT",
                            "reason": "Exact scene match.",
                        }
                        for beat_id in beat_ids
                    ]
                }),
                Path(workspace) / ".producer" / label,
            )

    engine = StreamingEngine()
    gateway = ReviewGateway()
    coordinator = FootageCoordinator(
        gateway,
        DisabledGemini(),
        footage_engine=engine,
        batch_retries=0,
    )

    result = coordinator.run({"id": "job-stream", "title": "stream", "footage_mode": "vision_codex"}, tmp_path)

    assert result.returncode == 0
    assert gateway.calls == 2
    assert engine.approved_during_prepare is True
    approved = json.loads((tmp_path / "footage_approved_live.json").read_text(encoding="utf-8"))
    assert [row["beat_id"] for row in approved["items"]] == ["B001", "B002", "B003"]


def test_vision_codex_resume_prepares_and_reviews_only_missing_beats(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_VISION_REVIEW_BATCH_SIZE", "2")
    beats = [
        {"beat_id": f"B{i:03d}", "narration_text": f"Voice {i}", "visual_description": f"Scene {i}", "source_priority": "must_real"}
        for i in range(1, 5)
    ]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    media = {}
    for beat in beats:
        path = tmp_path / f"{beat['beat_id']}.jpg"
        path.write_bytes(b"x" * 5000)
        media[beat["beat_id"]] = path

    def candidate(beat_id):
        return {
            "candidate_id": f"FT-{beat_id}-01", "beat_id": beat_id, "decision": "REVIEW",
            "source_priority": "must_real", "source_url": f"https://source.test/{beat_id}",
            "local_path": str(media[beat_id]), "kind": "sourced_still",
            "representative_frames": [str(media[beat_id])], "real_video_search_complete": True,
            "real_still_search_complete": True,
        }

    assignments = {"codex": beats, "gemini": []}
    checkpoint = FootageCoordinator(None, DisabledGemini())._new_checkpoint(assignments)
    checkpoint["pipeline"] = "vision_codex"
    checkpoint["workers"]["codex"]["completed_beat_ids"] = ["B001", "B002"]
    checkpoint["workers"]["codex"]["current_batch"] = 1
    (tmp_path / "footage_checkpoint.json").write_text(json.dumps(checkpoint), encoding="utf-8")
    (tmp_path / "footage_candidate_queue.json").write_text(json.dumps({
        "status": "running", "beats": [
            {"beat_id": beat_id, "candidates": [candidate(beat_id)]} for beat_id in ("B001", "B002")
        ],
    }), encoding="utf-8")
    review_root = tmp_path / ".producer" / "footage_codex_review" / "batches"
    review_root.mkdir(parents=True)
    (review_root / "batch_0001.json").write_text(json.dumps({"reviews": [
        {"beat_id": beat_id, "candidate_id": f"FT-{beat_id}-01", "decision": "ACCEPT", "reason": "kept"}
        for beat_id in ("B001", "B002")
    ]}), encoding="utf-8")

    class ResumeEngine:
        def __init__(self):
            self.received = []

        def prepare(self, job, batch_beats, workspace, **kwargs):
            self.received = [beat["beat_id"] for beat in batch_beats]
            rows = [candidate(beat_id) for beat_id in self.received]
            callback = kwargs.get("prepared_beat_callback")
            for index, beat in enumerate(batch_beats, start=1):
                if callback:
                    callback(beat, [rows[index - 1]], index, len(batch_beats))
            return {"status": "completed", "candidates": rows, "failures": []}

    class ResumeGateway:
        def status(self):
            return {"active_provider": "gemini"}

        def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
            return StageResult(0, json.dumps({"reviews": [
                {"beat_id": beat_id, "candidate_id": f"FT-{beat_id}-01", "decision": "ACCEPT", "reason": "new"}
                for beat_id in ("B003", "B004")
            ]}), Path(workspace) / label)

    engine = ResumeEngine()
    coordinator = FootageCoordinator(ResumeGateway(), DisabledGemini(), footage_engine=engine, batch_retries=0)
    result = coordinator.run({"id": "resume", "footage_mode": "vision_codex"}, tmp_path)

    assert result.returncode == 0
    assert engine.received == ["B003", "B004"]
    saved = json.loads((tmp_path / "footage_checkpoint.json").read_text(encoding="utf-8"))
    assert saved["workers"]["codex"]["completed_beat_ids"] == ["B001", "B002", "B003", "B004"]
    canonical = json.loads((tmp_path / "footage_codex.json").read_text(encoding="utf-8"))
    assert {row["beat_id"] for row in canonical["candidates"]} == {"B001", "B002", "B003", "B004"}


def test_vision_codex_retries_local_footage_tools_after_ai_reject(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_FOOTAGE_AI_RETRY_ROUNDS", "2")
    beat = {
        "beat_id": "B001",
        "narration_text": "SK hynix is expanding its Yongin semiconductor cluster.",
        "visual_description": "SK hynix Yongin semiconductor construction site",
        "footage_search_queries": ["SK hynix Yongin semiconductor cluster"],
        "target_duration_sec": 8,
        "source_priority": "must_real",
    }
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": [beat]}), encoding="utf-8")
    rejected = tmp_path / "rejected.jpg"
    accepted = tmp_path / "accepted.jpg"
    rejected.write_bytes(b"r" * 5000)
    accepted.write_bytes(b"a" * 5000)

    class RetryEngine:
        def __init__(self):
            self.calls = []

        def prepare(self, job, beats, workspace):
            current = dict(beats[0])
            self.calls.append(current)
            second_round = len(self.calls) == 2
            candidate_id = "FT-B001-02" if second_round else "FT-B001-01"
            source_url = "https://source.test/right" if second_round else "https://source.test/wrong"
            local_path = accepted if second_round else rejected
            return {
                "worker": "vision",
                "status": "completed",
                "candidates": [{
                    "candidate_id": candidate_id,
                    "beat_id": "B001",
                    "source_priority": "must_real",
                    "decision": "REVIEW",
                    "verification_provider": "openclip",
                    "visually_inspected_actual_content": False,
                    "source_url": source_url,
                    "local_path": str(local_path),
                    "kind": "sourced_still",
                    "representative_frames": [str(local_path)],
                    "semantic_prefilter": {"semantic_score": 0.9, "provider": "openclip"},
                    "real_video_search_complete": True,
                    "real_still_search_complete": True,
                }],
                "assets": [],
                "native_treatments": [],
                "presentation_effects": [],
            }

    class ReviewGateway:
        def __init__(self):
            self.calls = 0

        def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False, image_paths=None):
            self.calls += 1
            if self.calls == 1:
                payload = {
                    "reviews": [{
                        "beat_id": "B001",
                        "candidate_id": "FT-B001-01",
                        "decision": "REJECT",
                        "reason": "The image is generic and does not show the Yongin construction site.",
                    }],
                    "retry_requests": [{
                        "beat_id": "B001",
                        "reason": "Need the actual Yongin construction site.",
                        "search_queries": ["SK hynix Yongin semiconductor construction site aerial"],
                    }],
                }
            else:
                payload = {
                    "reviews": [{
                        "beat_id": "B001",
                        "candidate_id": "FT-B001-02",
                        "decision": "ACCEPT",
                        "reason": "Shows the requested Yongin construction site.",
                    }],
                    "retry_requests": [],
                }
            return StageResult(0, json.dumps(payload), Path(workspace) / ".producer" / label)

    engine = RetryEngine()
    gateway = ReviewGateway()
    coordinator = FootageCoordinator(
        gateway,
        DisabledGemini(),
        footage_engine=engine,
        batch_size=4,
        batch_retries=0,
    )

    result = coordinator.run({"id": "job-1", "title": "test", "footage_mode": "vision_codex"}, tmp_path)

    canonical = json.loads((tmp_path / "footage_codex.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert len(engine.calls) == 2
    assert gateway.calls == 2
    assert "SK hynix Yongin semiconductor construction site aerial" in engine.calls[1]["footage_search_queries"]
    assert "https://source.test/wrong" in engine.calls[1]["footage_excluded_source_urls"]
    assert canonical["assets"][0]["source"]["candidate_id"] == "FT-B001-02"
    rejected_candidate = next(item for item in canonical["candidates"] if item["candidate_id"] == "FT-B001-01")
    assert rejected_candidate["local_media_deleted"] is True
    assert not rejected.exists()
    assert accepted.exists()
    retry_log = json.loads((tmp_path / "footage_ai_retry.json").read_text(encoding="utf-8"))
    assert retry_log["rounds"][0]["beat_id"] == "B001"
    assert retry_log["rounds"][0]["search_queries"] == ["SK hynix Yongin semiconductor construction site aerial"]


def test_vision_codex_stream_reject_retries_before_preparing_next_beat(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_VISION_REVIEW_BATCH_SIZE", "2")
    monkeypatch.setenv("COFI_FOOTAGE_AI_RETRY_ROUNDS", "1")
    beats = [
        {
            "beat_id": beat_id,
            "narration_text": f"Voice {beat_id}",
            "visual_description": f"Scene {beat_id}",
            "footage_search_queries": [f"query {beat_id}"],
            "target_duration_sec": 8,
            "source_priority": "must_real",
        }
        for beat_id in ("B001", "B002", "B003")
    ]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    events = []

    def make_candidate(beat_id: str, suffix: str) -> dict:
        path = tmp_path / f"{beat_id}-{suffix}.jpg"
        path.write_bytes((f"{beat_id}-{suffix}".encode("utf-8") + b"x" * 5000))
        return {
            "candidate_id": f"FT-{beat_id}-{suffix}",
            "beat_id": beat_id,
            "source_priority": "must_real",
            "decision": "REVIEW",
            "verification_provider": "semantic",
            "visually_inspected_actual_content": False,
            "source_url": f"https://source.test/{beat_id}/{suffix}",
            "local_path": str(path),
            "kind": "sourced_still",
            "representative_frames": [str(path)],
            "real_video_search_complete": True,
            "real_still_search_complete": True,
        }

    class StreamingRetryEngine:
        def prepare(
            self,
            job,
            batch_beats,
            workspace,
            *,
            control_callback=None,
            progress_callback=None,
            discovery_progress_callback=None,
            prepared_beat_callback=None,
            reset_live_downloads=True,
            persist_queue=True,
        ):
            if len(batch_beats) == 1 and batch_beats[0].get("footage_ai_retry_reason"):
                beat_id = batch_beats[0]["beat_id"]
                events.append(f"retry_prepare_{beat_id}")
                assert reset_live_downloads is False
                assert persist_queue is False
                return {
                    "worker": "vision",
                    "status": "completed",
                    "candidates": [make_candidate(beat_id, "retry")],
                    "assets": [],
                    "native_treatments": [],
                    "presentation_effects": [],
                    "failures": [],
                }

            candidates = []
            total = len(batch_beats)
            for index, beat in enumerate(batch_beats, start=1):
                beat_id = beat["beat_id"]
                events.append(f"main_prepare_{beat_id}")
                candidate = make_candidate(beat_id, "initial")
                candidates.append(candidate)
                if progress_callback is not None:
                    progress_callback(index, total, beat_id)
                if prepared_beat_callback is not None:
                    prepared_beat_callback(beat, [candidate], index, total)
            return {
                "worker": "vision",
                "status": "completed",
                "candidates": candidates,
                "assets": [],
                "native_treatments": [],
                "presentation_effects": [],
                "failures": [],
            }

    class ReviewGateway:
        def __init__(self):
            self.calls = 0

        def status(self):
            return {"active_provider": "gemini", "preferred_provider": "gemini"}

        def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False, image_paths=None):
            self.calls += 1
            if self.calls == 1:
                payload = {
                    "reviews": [
                        {"beat_id": "B001", "candidate_id": "FT-B001-initial", "decision": "REJECT", "reason": "wrong scene"},
                        {"beat_id": "B002", "candidate_id": "FT-B002-initial", "decision": "ACCEPT", "reason": "correct scene"},
                    ],
                    "retry_requests": [{
                        "beat_id": "B001",
                        "reason": "find exact scene",
                        "search_queries": ["exact B001 archive"],
                    }],
                }
            elif self.calls == 2:
                payload = {
                    "reviews": [{
                        "beat_id": "B001",
                        "candidate_id": "FT-B001-retry",
                        "decision": "ACCEPT",
                        "reason": "retry is exact",
                    }],
                    "retry_requests": [],
                }
            else:
                payload = {
                    "reviews": [{
                        "beat_id": "B003",
                        "candidate_id": "FT-B003-initial",
                        "decision": "ACCEPT",
                        "reason": "correct scene",
                    }],
                    "retry_requests": [],
                }
            return StageResult(0, json.dumps(payload), Path(workspace) / ".producer" / label)

    gateway = ReviewGateway()
    coordinator = FootageCoordinator(
        gateway,
        DisabledGemini(),
        footage_engine=StreamingRetryEngine(),
        batch_retries=0,
    )

    result = coordinator.run({"id": "job-stream-retry", "title": "stream retry", "footage_mode": "vision_codex"}, tmp_path)

    assert result.returncode == 0
    assert gateway.calls == 3
    assert events.index("retry_prepare_B001") < events.index("main_prepare_B003")
    approved = json.loads((tmp_path / "footage_approved_live.json").read_text(encoding="utf-8"))
    assert {row["beat_id"] for row in approved["items"]} == {"B001", "B002", "B003"}
    retry_log = json.loads((tmp_path / "footage_ai_retry.json").read_text(encoding="utf-8"))
    assert retry_log["rounds"][0]["status"] == "accepted"


def test_reject_cleanup_preserves_media_still_referenced_by_pending_candidate(tmp_path: Path):
    shared = tmp_path / "shared.jpg"
    shared.write_bytes(b"x" * 5000)
    manifest = tmp_path / "footage_live_downloads.json"
    manifest.write_text(json.dumps({
        "version": 1,
        "items": [
            {"beat_id": "B001", "source_url": "https://source.test/shared", "path": str(shared)},
            {"beat_id": "B002", "source_url": "https://source.test/shared", "path": str(shared)},
        ],
    }), encoding="utf-8")
    candidates = [
        {
            "candidate_id": "FT-B001-01",
            "beat_id": "B001",
            "source_url": "https://source.test/shared",
            "local_path": str(shared),
            "representative_frames": [str(shared)],
        },
        {
            "candidate_id": "FT-B002-01",
            "beat_id": "B002",
            "source_url": "https://source.test/shared",
            "local_path": str(shared),
            "representative_frames": [str(shared)],
        },
    ]
    coordinator = FootageCoordinator(object(), object(), footage_engine=object())
    first_review = [{
        "candidate_id": "FT-B001-01",
        "beat_id": "B001",
        "decision": "REJECT",
        "reason": "wrong scene",
    }]

    coordinator._discard_rejected_media(tmp_path, candidates, first_review, first_review)

    assert shared.exists()
    live = json.loads(manifest.read_text(encoding="utf-8"))
    assert [item["beat_id"] for item in live["items"]] == ["B002"]

    second_review = [{
        "candidate_id": "FT-B002-01",
        "beat_id": "B002",
        "decision": "REJECT",
        "reason": "wrong scene too",
    }]
    coordinator._discard_rejected_media(tmp_path, candidates, second_review, first_review + second_review)

    assert not shared.exists()
    live = json.loads(manifest.read_text(encoding="utf-8"))
    assert live["items"] == []


def test_review_commit_keeps_one_selected_candidate_per_voice_beat_and_deletes_the_rest(tmp_path: Path):
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"a" * 5000)
    second.write_bytes(b"b" * 5000)
    candidates = [
        {
            "candidate_id": "FT-B001-01",
            "beat_id": "B001",
            "source_url": "https://source.test/first",
            "local_path": str(first),
            "kind": "sourced_still",
            "representative_frames": [str(first)],
        },
        {
            "candidate_id": "FT-B001-02",
            "beat_id": "B001",
            "source_url": "https://source.test/second",
            "local_path": str(second),
            "kind": "sourced_still",
            "representative_frames": [str(second)],
        },
    ]
    reviews = [
        {"candidate_id": "FT-B001-01", "beat_id": "B001", "decision": "ACCEPT", "reason": "best match"},
        {"candidate_id": "FT-B001-02", "beat_id": "B001", "decision": "ACCEPT", "reason": "also usable"},
    ]
    coordinator = FootageCoordinator(object(), object(), footage_engine=object())

    selected_beats = coordinator._commit_reviewed_media(tmp_path, candidates, reviews, reviews)

    assert selected_beats == {"B001"}
    assert candidates[0]["selected_for_beat"] is True
    assert candidates[0]["selection_status"] == "selected"
    assert Path(candidates[0]["local_path"]).exists()
    assert candidates[1]["selected_for_beat"] is False
    assert candidates[1]["selection_status"] == "discarded"
    assert candidates[1]["local_media_deleted"] is True
    assert not second.exists()
    approved = json.loads((tmp_path / "footage_approved_live.json").read_text(encoding="utf-8"))
    assert [row["candidate_id"] for row in approved["items"]] == ["FT-B001-01"]
    assert approved["items"][0]["decision"] == "ACCEPT"


def test_footage_default_adaptive_batches_grow_4_6_8(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("COFI_FOOTAGE_BATCH_SIZE", raising=False)
    monkeypatch.delenv("COFI_FOOTAGE_ADAPTIVE_BATCHING", raising=False)
    monkeypatch.delenv("COFI_FOOTAGE_BATCH_MAX_SIZE", raising=False)
    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 19)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    gateway = FakeBatchGateway()
    coordinator = FootageCoordinator(gateway, DisabledGemini(), batch_retries=0)

    result = coordinator.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)

    checkpoint = json.loads((tmp_path / "footage_checkpoint.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert [len(call) for call in gateway.calls] == [4, 6, 8]
    assert [entry["batch_size"] for entry in checkpoint["workers"]["codex"]["batch_plan"]] == [4, 6, 8]
    assert checkpoint["workers"]["codex"]["adaptive_batch_size"] == 8
    assert checkpoint["completed_beats"] == 18


def test_footage_adaptive_batches_shrink_after_continuation(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("COFI_FOOTAGE_BATCH_SIZE", raising=False)
    monkeypatch.delenv("COFI_FOOTAGE_ADAPTIVE_BATCHING", raising=False)
    monkeypatch.delenv("COFI_FOOTAGE_BATCH_MAX_SIZE", raising=False)
    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 17)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    gateway = FakeBatchGateway(incomplete_calls={2})
    coordinator = FootageCoordinator(gateway, DisabledGemini(), batch_retries=0)

    result = coordinator.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)

    checkpoint = json.loads((tmp_path / "footage_checkpoint.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert [len(call) for call in gateway.calls] == [4, 6, 6, 4, 2]
    assert [entry["batch_size"] for entry in checkpoint["workers"]["codex"]["batch_plan"]] == [4, 6, 4, 2]
    assert checkpoint["workers"]["codex"]["batch_plan"][1]["continuations"] == 1


def test_footage_coordinator_resumes_only_unfinished_batches(tmp_path: Path):
    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 11)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    first_gateway = FakeBatchGateway(fail_call=3, fail_message="invalid response")
    first = FootageCoordinator(first_gateway, DisabledGemini(), batch_size=4, batch_retries=0)

    failed = first.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)
    assert failed.returncode == 1
    assert first_gateway.calls[:2] == [
        ["B001", "B002", "B003", "B004"],
        ["B005", "B006", "B007", "B008"],
    ]

    second_gateway = FakeBatchGateway()
    second = FootageCoordinator(second_gateway, DisabledGemini(), batch_size=4, batch_retries=0)
    resumed = second.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)

    assert resumed.returncode == 0
    assert second_gateway.calls == [["B009", "B010"]]
    canonical = json.loads((tmp_path / "footage_codex.json").read_text(encoding="utf-8"))
    assert {item["beat_id"] for item in canonical["candidates"]} == {beat["beat_id"] for beat in beats}


def test_footage_resume_keeps_checkpoint_batch_size_when_new_default_is_larger(tmp_path: Path):
    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 11)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    first_gateway = FakeBatchGateway(fail_call=2, fail_message="connection reset by peer")
    first = FootageCoordinator(first_gateway, DisabledGemini(), batch_size=4, batch_retries=0)

    failed = first.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)
    assert failed.returncode == 1

    second_gateway = FakeBatchGateway()
    second = FootageCoordinator(second_gateway, DisabledGemini(), batch_size=16, batch_retries=0)
    assert second.batch_size == 16
    resumed = second.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)

    checkpoint = json.loads((tmp_path / "footage_checkpoint.json").read_text(encoding="utf-8"))
    assert resumed.returncode == 0
    assert second_gateway.calls == [
        ["B005", "B006", "B007", "B008"],
        ["B009", "B010"],
    ]
    assert checkpoint["batch_size"] == 4
    assert checkpoint["workers"]["codex"]["total_batches"] == 3


def test_footage_repair_only_searches_missing_beats_and_preserves_other_results(tmp_path: Path):
    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 9)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": [
            {"candidate_id": f"OLD-{beat['beat_id']}", "beat_id": beat["beat_id"], "decision": "REVIEW"}
            for beat in beats
        ],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_checkpoint.json").write_text(json.dumps({
        "status": "completed", "completed_beats": 8, "total_beats": 8,
        "status_message": "Đã hoàn tất tìm tư liệu cho 8/8 beat.",
    }), encoding="utf-8")
    gateway = FakeBatchGateway()
    coordinator = FootageCoordinator(gateway, DisabledGemini(), batch_size=2, batch_retries=0)

    result = coordinator.repair(
        {"id": "job-1", "title": "test", "footage_mode": "codex"},
        tmp_path,
        ["B002", "B005", "B008"],
    )

    canonical = json.loads((tmp_path / "footage_codex.json").read_text(encoding="utf-8"))
    checkpoint = json.loads((tmp_path / "footage_checkpoint.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert gateway.calls == [["B002", "B005"], ["B008"]]
    by_beat = {item["beat_id"]: item["candidate_id"] for item in canonical["candidates"]}
    assert by_beat["B001"] == "OLD-B001"
    assert by_beat["B002"] == "C-B002"
    assert by_beat["B005"] == "C-B005"
    assert by_beat["B008"] == "C-B008"
    assert checkpoint["status"] == "completed"
    assert checkpoint["completed_beats"] == 8
    assert checkpoint["total_beats"] == 8
    repair_checkpoint = json.loads((tmp_path / ".producer" / "footage_repair" / "checkpoint.json").read_text(encoding="utf-8"))
    assert gateway.resets == 0
    assert repair_checkpoint["session_rotations"] == 0


def test_footage_repair_continues_same_batch_after_successful_but_incomplete_turn(tmp_path: Path):
    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 5)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": [
            {"candidate_id": f"OLD-{beat['beat_id']}", "beat_id": beat["beat_id"], "decision": "REVIEW"}
            for beat in beats
        ],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")
    gateway = FakeBatchGateway(incomplete_calls={1})
    coordinator = FootageCoordinator(
        gateway,
        DisabledGemini(),
        batch_size=4,
        batch_retries=0,
        batch_continuations=2,
    )

    result = coordinator.repair(
        {"id": "job-1", "title": "test", "footage_mode": "codex"},
        tmp_path,
        ["B001", "B002", "B003", "B004"],
    )

    repair_checkpoint = json.loads(
        (tmp_path / ".producer" / "footage_repair" / "checkpoint.json").read_text(encoding="utf-8")
    )
    assert result.returncode == 0
    assert gateway.calls == [
        ["B001", "B002", "B003", "B004"],
        ["B001", "B002", "B003", "B004"],
    ]
    assert gateway.resets == 0
    assert repair_checkpoint["completed_beat_ids"] == ["B001", "B002", "B003", "B004"]
    assert repair_checkpoint["status"] == "completed"


def test_footage_repair_replaces_active_scope_when_caller_requests_new_subset(tmp_path: Path):
    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 8)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": [
            {"candidate_id": f"OLD-{beat['beat_id']}", "beat_id": beat["beat_id"], "decision": "REVIEW"}
            for beat in beats
        ],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")

    repair_root = tmp_path / ".producer" / "footage_repair"
    batch_dir = repair_root / "batches"
    batch_dir.mkdir(parents=True)
    (batch_dir / "batch_0001.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": [
            {"candidate_id": "C-B001", "beat_id": "B001", "decision": "REVIEW"},
            {"candidate_id": "C-B002", "beat_id": "B002", "decision": "REVIEW"},
        ],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")
    (repair_root / "checkpoint.json").write_text(json.dumps({
        "version": 1,
        "assigned_beat_ids": ["B001", "B002", "B003", "B004", "B005", "B006"],
        "completed_beat_ids": ["B001", "B002"],
        "current_batch": 2,
        "total_batches": 3,
        "attempts": 2,
        "session_rotations": 1,
        "status": "running",
        "status_message": "Đang sửa coverage B003, B004 · batch 2/3",
    }), encoding="utf-8")

    gateway = FakeBatchGateway()
    coordinator = FootageCoordinator(gateway, DisabledGemini(), batch_size=2, batch_retries=0)
    result = coordinator.repair(
        {"id": "job-1", "title": "test", "footage_mode": "codex"},
        tmp_path,
        ["B003", "B004", "B007"],
    )

    repair_checkpoint = json.loads((repair_root / "checkpoint.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert gateway.calls == [
        ["B003", "B004"],
        ["B007"],
    ]
    assert repair_checkpoint["assigned_beat_ids"] == ["B003", "B004", "B007"]
    assert repair_checkpoint["completed_beat_ids"] == ["B003", "B004", "B007"]
    assert (tmp_path / ".producer" / "footage_repair_history").exists()


def test_footage_coordinator_retries_same_batch_in_same_session_after_disconnect(tmp_path: Path):
    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 5)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    gateway = FakeBatchGateway(fail_call=1, fail_message="connection reset by peer")
    coordinator = FootageCoordinator(gateway, DisabledGemini(), batch_size=4, batch_retries=2)

    result = coordinator.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)

    checkpoint = json.loads((tmp_path / "footage_checkpoint.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert gateway.calls == [["B001", "B002", "B003", "B004"], ["B001", "B002", "B003", "B004"]]
    assert gateway.resets == 0
    assert checkpoint["workers"]["codex"]["session_rotations"] == 0


def test_footage_coordinator_marks_fresh_session_as_continuing_before_retry_turn(tmp_path: Path):
    class InspectRetryStatusGateway(FakeBatchGateway):
        def __init__(self):
            super().__init__(fail_call=1, fail_message="connection reset by peer")
            self.retry_status_message = ""

        def run_prompt_reusable(self, prompt, workspace, label):
            if len(self.calls) == 1:
                checkpoint = json.loads((Path(workspace) / "footage_checkpoint.json").read_text(encoding="utf-8"))
                self.retry_status_message = str(checkpoint.get("status_message") or "")
            return super().run_prompt_reusable(prompt, workspace, label)

    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 5)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    gateway = InspectRetryStatusGateway()
    coordinator = FootageCoordinator(gateway, DisabledGemini(), batch_size=4, batch_retries=2)

    result = coordinator.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)

    assert result.returncode == 0
    assert "Đã nối lại Codex" in gateway.retry_status_message
    assert "đang tiếp tục" in gateway.retry_status_message.lower()
    assert "batch 1/1" in gateway.retry_status_message


def test_footage_coordinator_continues_same_batch_after_successful_but_incomplete_turn(tmp_path: Path):
    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 5)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    gateway = FakeBatchGateway(incomplete_calls={1})
    coordinator = FootageCoordinator(gateway, DisabledGemini(), batch_size=4, batch_retries=0)

    result = coordinator.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)

    checkpoint = json.loads((tmp_path / "footage_checkpoint.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert gateway.calls == [["B001", "B002", "B003", "B004"], ["B001", "B002", "B003", "B004"]]
    assert gateway.resets == 0
    assert checkpoint["completed_beats"] == 4
    assert checkpoint["status"] == "completed"


def test_footage_coordinator_reports_error_after_three_reconnects(tmp_path: Path):
    beats = [{"beat_id": f"B{i:03d}", "target_duration_sec": 5} for i in range(1, 5)]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    gateway = FakeBatchGateway(
        fail_calls={1, 2, 3, 4},
        fail_message="connection reset by peer",
    )
    coordinator = FootageCoordinator(gateway, DisabledGemini(), batch_size=4, batch_retries=3)

    result = coordinator.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)

    checkpoint = json.loads((tmp_path / "footage_checkpoint.json").read_text(encoding="utf-8"))
    assert result.returncode == 1
    assert len(gateway.calls) == 4
    assert gateway.resets == 0
    assert checkpoint["workers"]["codex"]["session_rotations"] == 0
    assert "3/3" in checkpoint["status_message"]


def test_coverage_snapshot_reports_visual_beat_without_approved_asset(tmp_path: Path):
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": [
        {"beat_id": "B001", "narration_text": "a"},
        {"beat_id": "B002", "narration_text": "b"},
    ]}), encoding="utf-8")
    (tmp_path / "voice_manifest.json").write_text(json.dumps({"beats": [
        {"beat_id": "B001", "start_sec": 0, "end_sec": 2},
        {"beat_id": "B002", "start_sec": 2, "end_sec": 4},
    ]}), encoding="utf-8")
    (tmp_path / "asset_registry.json").write_text(json.dumps({"assets": [
        {"id": "A1", "beat_id": "B001", "kind": "sourced_video", "path": "a.mp4"},
    ]}), encoding="utf-8")
    (tmp_path / "a.mp4").write_bytes(b"x")

    report = build_preflight(tmp_path)

    assert report["status"] == "FAIL"
    assert report["missing_beats"] == ["B002"]
    assert report["coverage_percent"] == 50.0


def test_merge_worker_results_keeps_presentation_effects_separate_from_native_motion(tmp_path: Path):
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": [],
        "assets": [],
        "native_treatments": [
            {"id": "N1", "beat_id": "B003", "kind": "remotion_native_motion", "description": "storm track map"},
        ],
        "presentation_effects": [
            {"id": "P1", "beat_id": "B001", "kind": "presentation_effect", "description": "slow push-in"},
        ],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini",
        "status": "unavailable",
        "candidates": [],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")

    registry = merge_worker_results(tmp_path)

    assert [item["id"] for item in registry["native_treatments"]] == ["N1"]
    assert [item["id"] for item in registry["presentation_effects"]] == ["P1"]


def test_merge_worker_results_downgrades_tiny_corrupt_accepted_media(tmp_path: Path):
    broken = tmp_path / "media" / "codex" / "broken.mp4"
    broken.parent.mkdir(parents=True)
    broken.write_bytes(b"broken")
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": [{
            "candidate_id": "C1",
            "beat_id": "B001",
            "decision": "ACCEPT",
            "kind": "sourced_video",
            "local_path": str(broken),
        }],
        "assets": [{
            "id": "A1",
            "beat_id": "B001",
            "kind": "sourced_video",
            "path": str(broken),
            "source": {"candidate_id": "C1"},
        }],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")

    registry = merge_worker_results(tmp_path)
    review = json.loads((tmp_path / "footage_review.json").read_text(encoding="utf-8"))

    assert review["candidates"][0]["decision"] == "REVIEW"
    assert "quá nhỏ" in review["candidates"][0]["validation_error"]
    assert registry["assets"] == []


def test_merge_worker_results_quarantines_downloaded_review_file_out_of_visible_media_root(tmp_path: Path):
    reviewed = tmp_path / "media" / "codex" / "B004_candidate_review.jpg"
    reviewed.parent.mkdir(parents=True)
    reviewed.write_bytes(b"x" * 5000)
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": [{
            "candidate_id": "C-REVIEW",
            "beat_id": "B004",
            "decision": "REVIEW",
            "kind": "sourced_still",
            "local_path": str(reviewed),
            "reason": "Đúng địa điểm nhưng bố cục không đủ tốt để dùng.",
        }],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")

    merge_worker_results(tmp_path)
    review = json.loads((tmp_path / "footage_review.json").read_text(encoding="utf-8"))
    candidate = review["candidates"][0]

    assert not reviewed.exists()
    quarantined = Path(candidate["local_path"])
    assert quarantined.exists()
    assert "_inspection" in quarantined.parts
    assert candidate["decision"] == "REVIEW"


def test_merge_worker_results_promotes_inspected_review_file_in_main_media_to_accepted_asset(tmp_path: Path):
    reviewed = tmp_path / "media" / "codex" / "B004_ready_to_use.jpg"
    reviewed.parent.mkdir(parents=True)
    reviewed.write_bytes(b"x" * 5000)
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": [{
            "candidate_id": "C-READY",
            "beat_id": "B004",
            "decision": "REVIEW",
            "kind": "sourced_still",
            "local_path": str(reviewed),
            "source_url": "https://example.test/ready.jpg",
            "visually_inspected_actual_content": True,
            "rights_risk": "LOW",
            "reason": "Đã xem nội dung thật và file đang nằm trong media chính.",
        }],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")

    registry = merge_worker_results(tmp_path)
    review = json.loads((tmp_path / "footage_review.json").read_text(encoding="utf-8"))

    candidate = review["candidates"][0]
    assert candidate["decision"] == "ACCEPT"
    assert candidate["auto_promoted_from_review"] is True
    assert candidate["local_path"] == str(reviewed)
    assert len(registry["assets"]) == 1
    assert registry["assets"][0]["beat_id"] == "B004"
    assert registry["assets"][0]["source"]["candidate_id"] == "C-READY"


def test_merge_worker_results_materializes_valid_accepted_candidate_without_worker_asset(tmp_path: Path):
    accepted = tmp_path / "media" / "codex" / "B005_ready_to_use.jpg"
    accepted.parent.mkdir(parents=True)
    accepted.write_bytes(b"x" * 5000)
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": [{
            "candidate_id": "C-ACCEPTED",
            "beat_id": "B005",
            "decision": "ACCEPT",
            "kind": "sourced_still",
            "local_path": str(accepted),
            "source_url": "https://example.test/accepted.jpg",
            "visually_inspected_actual_content": True,
            "rights_risk": "LOW",
        }],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")

    registry = merge_worker_results(tmp_path)

    assert len(registry["assets"]) == 1
    assert registry["assets"][0]["beat_id"] == "B005"
    assert registry["assets"][0]["source"]["candidate_id"] == "C-ACCEPTED"


def test_merge_worker_results_rejects_oversized_media_before_registry(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_FOOTAGE_MAX_MEDIA_MB", "1")
    large = tmp_path / "media" / "codex" / "large.jpg"
    large.parent.mkdir(parents=True)
    with large.open("wb") as handle:
        handle.seek(2 * 1024 * 1024)
        handle.write(b"x")
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": [{
            "candidate_id": "C1",
            "beat_id": "B001",
            "decision": "ACCEPT",
            "kind": "sourced_still",
            "local_path": str(large),
        }],
        "assets": [{
            "id": "A1",
            "beat_id": "B001",
            "kind": "sourced_still",
            "path": str(large),
            "source": {"candidate_id": "C1"},
        }],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")

    registry = merge_worker_results(tmp_path)
    review = json.loads((tmp_path / "footage_review.json").read_text(encoding="utf-8"))

    assert review["candidates"][0]["decision"] == "REVIEW"
    assert "giới hạn 1 MB" in review["candidates"][0]["validation_error"]
    assert registry["assets"] == []


def test_merge_worker_results_allows_adjacent_same_story_reuse_without_ai_fallback(tmp_path: Path):
    shared = tmp_path / "media" / "codex" / "shared.jpg"
    shared.parent.mkdir(parents=True)
    shared.write_bytes(b"x" * 5000)
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "beats": [
            {
                "beat_id": "B001",
                "story_group": "marriage-discovery",
                "narration_text": "Eleanor discovers Franklin's affair with Lucy Mercer.",
                "visual_description": "Eleanor Roosevelt and Franklin Roosevelt during the marriage crisis.",
                "footage_search_queries": ["Eleanor Franklin Roosevelt Lucy Mercer affair 1918"],
                "source_priority": "prefer_real",
            },
            {
                "beat_id": "B002",
                "story_group": "marriage-discovery",
                "narration_text": "The discovery forced the couple to confront the future of their marriage.",
                "visual_description": "Eleanor and Franklin Roosevelt in the same 1918 marriage crisis.",
                "footage_search_queries": ["Eleanor Franklin Roosevelt marriage 1918"],
                "source_priority": "prefer_real",
            },
            {
                "beat_id": "B003",
                "story_group": "marriage-discovery",
                "narration_text": "They stayed married, but the relationship changed permanently.",
                "visual_description": "Eleanor and Franklin Roosevelt archival portrait around the crisis period.",
                "footage_search_queries": ["Eleanor Franklin Roosevelt archival portrait 1918"],
                "source_priority": "prefer_real",
            },
        ]
    }), encoding="utf-8")
    candidates = []
    assets = []
    for index, beat_id in enumerate(("B001", "B002", "B003"), start=1):
        candidate_id = f"C{index}"
        candidates.append({
            "candidate_id": candidate_id,
            "beat_id": beat_id,
            "decision": "ACCEPT",
            "kind": "sourced_still",
            "local_path": str(shared),
            "source_priority": "prefer_real",
            "source_url": "https://archive.test/shared.jpg",
            "real_video_search_complete": True,
            "real_still_search_complete": True,
        })
        assets.append({
            "id": f"A{index}",
            "beat_id": beat_id,
            "kind": "sourced_still",
            "path": str(shared),
            "source": {"candidate_id": candidate_id},
        })

    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": candidates,
        "assets": assets,
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")

    registry = merge_worker_results(tmp_path)
    review = json.loads((tmp_path / "footage_review.json").read_text(encoding="utf-8"))

    assert [asset["beat_id"] for asset in registry["assets"]] == ["B001", "B002", "B003"]
    assert [candidate["decision"] for candidate in review["candidates"]] == ["ACCEPT", "ACCEPT", "ACCEPT"]
    assert review["candidates"][1]["contextual_reuse"] is True
    assert review["candidates"][2]["contextual_reuse"] is True
    assert review["candidates"][1]["reuse_reason"]
    assert registry["ai_fallback_beats"] == []


def test_merge_worker_results_rejects_unrelated_cross_story_reuse_without_reason(tmp_path: Path):
    shared = tmp_path / "media" / "codex" / "unrelated.jpg"
    shared.parent.mkdir(parents=True)
    shared.write_bytes(b"x" * 5000)
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "beats": [
            {
                "beat_id": "B001",
                "story_group": "marriage-discovery",
                "narration_text": "A marriage crisis in 1918.",
                "visual_description": "Eleanor and Franklin Roosevelt.",
                "source_priority": "prefer_real",
            },
            {
                "beat_id": "B010",
                "story_group": "united-nations",
                "narration_text": "Decades later Eleanor worked at the United Nations.",
                "visual_description": "Eleanor Roosevelt at the United Nations.",
                "source_priority": "prefer_real",
            },
        ]
    }), encoding="utf-8")
    candidates = [
        {
            "candidate_id": "C1", "beat_id": "B001", "decision": "ACCEPT", "kind": "sourced_still",
            "local_path": str(shared), "source_priority": "prefer_real", "source_url": "https://archive.test/shared.jpg",
            "real_video_search_complete": True, "real_still_search_complete": True,
        },
        {
            "candidate_id": "C2", "beat_id": "B010", "decision": "ACCEPT", "kind": "sourced_still",
            "local_path": str(shared), "source_priority": "prefer_real", "source_url": "https://archive.test/shared.jpg",
            "real_video_search_complete": True, "real_still_search_complete": True,
        },
    ]
    assets = [
        {"id": "A1", "beat_id": "B001", "kind": "sourced_still", "path": str(shared), "source": {"candidate_id": "C1"}},
        {"id": "A2", "beat_id": "B010", "kind": "sourced_still", "path": str(shared), "source": {"candidate_id": "C2"}},
    ]
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex", "status": "completed", "candidates": candidates, "assets": assets,
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")

    registry = merge_worker_results(tmp_path)
    review = json.loads((tmp_path / "footage_review.json").read_text(encoding="utf-8"))

    assert [asset["beat_id"] for asset in registry["assets"]] == ["B001"]
    assert review["candidates"][1]["decision"] == "REVIEW"
    assert review["candidates"][1]["rejected_unintentional_reuse"] is True
    assert registry["ai_fallback_beats"] == ["B010"]


def test_merge_worker_results_allows_explicit_intentional_reuse_with_reason(tmp_path: Path):
    shared = tmp_path / "media" / "codex" / "callback.jpg"
    shared.parent.mkdir(parents=True)
    shared.write_bytes(b"x" * 5000)
    candidates = [
        {
            "candidate_id": "C1",
            "beat_id": "B001",
            "decision": "ACCEPT",
            "kind": "sourced_still",
            "local_path": str(shared),
            "source_url": "https://archive.test/callback.jpg",
        },
        {
            "candidate_id": "C2",
            "beat_id": "B010",
            "decision": "ACCEPT",
            "kind": "sourced_still",
            "local_path": str(shared),
            "source_url": "https://archive.test/callback.jpg",
            "intentional_reuse": True,
            "reuse_reason": "Deliberate visual callback to the opening portrait.",
        },
    ]
    assets = [
        {"id": "A1", "beat_id": "B001", "kind": "sourced_still", "path": str(shared), "source": {"candidate_id": "C1"}},
        {"id": "A2", "beat_id": "B010", "kind": "sourced_still", "path": str(shared), "source": {"candidate_id": "C2"}},
    ]
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex",
        "status": "completed",
        "candidates": candidates,
        "assets": assets,
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")

    registry = merge_worker_results(tmp_path)
    review = json.loads((tmp_path / "footage_review.json").read_text(encoding="utf-8"))

    assert [asset["beat_id"] for asset in registry["assets"]] == ["B001", "B010"]
    assert [candidate["decision"] for candidate in review["candidates"]] == ["ACCEPT", "ACCEPT"]
    assert review["candidates"][1]["intentional_reuse"] is True
    assert review["candidates"][1]["reuse_reason"]
    assert registry["ai_fallback_beats"] == []


def test_merge_worker_results_detects_same_still_copied_to_different_paths(tmp_path: Path):
    first = tmp_path / "media" / "codex" / "first.jpg"
    second = tmp_path / "media" / "codex" / "renamed-copy.jpg"
    first.parent.mkdir(parents=True)
    payload = b"same-image-bytes" * 400
    first.write_bytes(payload)
    second.write_bytes(payload)
    candidates = [
        {
            "candidate_id": "C1", "beat_id": "B001", "decision": "ACCEPT", "kind": "sourced_still",
            "local_path": str(first), "source_priority": "prefer_real", "source_url": "https://source-a.test/a.jpg",
            "real_video_search_complete": True, "real_still_search_complete": True,
        },
        {
            "candidate_id": "C2", "beat_id": "B002", "decision": "ACCEPT", "kind": "sourced_still",
            "local_path": str(second), "source_priority": "prefer_real", "source_url": "https://mirror.test/renamed.jpg",
            "real_video_search_complete": True, "real_still_search_complete": True,
        },
    ]
    assets = [
        {"id": "A1", "beat_id": "B001", "kind": "sourced_still", "path": str(first), "source": {"candidate_id": "C1"}},
        {"id": "A2", "beat_id": "B002", "kind": "sourced_still", "path": str(second), "source": {"candidate_id": "C2"}},
    ]
    (tmp_path / "footage_codex.json").write_text(json.dumps({
        "worker": "codex", "status": "completed", "candidates": candidates, "assets": assets,
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")
    (tmp_path / "footage_gemini.json").write_text(json.dumps({
        "worker": "gemini", "status": "unavailable", "candidates": [], "assets": [],
        "native_treatments": [], "presentation_effects": [],
    }), encoding="utf-8")

    registry = merge_worker_results(tmp_path)
    review = json.loads((tmp_path / "footage_review.json").read_text(encoding="utf-8"))

    assert [asset["beat_id"] for asset in registry["assets"]] == ["B001"]
    assert review["candidates"][1]["decision"] == "REVIEW"
    assert review["candidates"][1]["rejected_unintentional_reuse"] is True
    assert registry["ai_fallback_beats"] == ["B002"]


def test_completed_footage_run_is_archived_before_a_fresh_rerun(tmp_path: Path):
    beats = [{"beat_id": "B001", "target_duration_sec": 5}]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    (tmp_path / "footage_checkpoint.json").write_text(json.dumps({
        "version": 1,
        "status": "completed",
        "workers": {
            "codex": {"assigned_beat_ids": ["B001"]},
            "gemini": {"assigned_beat_ids": []},
        },
    }), encoding="utf-8")
    (tmp_path / "footage_review.json").write_text(json.dumps({"marker": "old-run", "candidates": []}), encoding="utf-8")
    old_batches = tmp_path / ".producer" / "footage_codex" / "batches"
    old_batches.mkdir(parents=True)
    (old_batches / "batch_0001.json").write_text("{}", encoding="utf-8")
    gateway = FakeBatchGateway()
    coordinator = FootageCoordinator(gateway, DisabledGemini(), batch_size=4, batch_retries=0)

    result = coordinator.run({"id": "job-1", "title": "test", "footage_mode": "codex"}, tmp_path)

    history = list((tmp_path / ".producer" / "footage_history").iterdir())
    assert result.returncode == 0
    assert len(history) == 1
    archived_review = json.loads((history[0] / "footage_review.json").read_text(encoding="utf-8"))
    assert archived_review["marker"] == "old-run"
    assert (history[0] / "codex_batches" / "batch_0001.json").exists()
    checkpoint = json.loads((tmp_path / "footage_checkpoint.json").read_text(encoding="utf-8"))
    assert checkpoint["status"] == "completed"
    assert checkpoint.get("run_id")


def test_footage_quality_gate_does_not_require_native_motion_quota(tmp_path: Path):
    recipe = normalize_production_recipe(None, target_duration_minutes=5)
    contract = recipe["quality_contract"]
    beat_ids = [f"B{i + 1:03d}" for i in range(contract["min_scene_count"])]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "target_duration_sec": 300,
        "beats": [
            {"beat_id": beat_id, "visual_type": "sourced_video"}
            for beat_id in beat_ids
        ],
    }), encoding="utf-8")

    candidates = []
    assets = []
    for i in range(contract["min_video_clip_uses"]):
        candidate_id = f"video-{i}"
        candidates.append({"candidate_id": candidate_id, "decision": "ACCEPT", "visually_inspected_actual_content": True})
        assets.append({
            "id": f"V{i}",
            "beat_id": beat_ids[i % len(beat_ids)],
            "kind": "sourced_video",
            "source": {"candidate_id": candidate_id, "url": f"https://video.test/{i % contract['min_unique_video_sources']}"},
        })
    for i in range(contract["min_sourced_still_uses"]):
        candidate_id = f"still-{i}"
        candidates.append({"candidate_id": candidate_id, "decision": "ACCEPT", "visually_inspected_actual_content": True})
        assets.append({
            "id": f"I{i}",
            "beat_id": beat_ids[i % len(beat_ids)],
            "kind": "sourced_still",
            "source": {"candidate_id": candidate_id, "url": f"https://still.test/{i}"},
        })

    (tmp_path / "footage_review.json").write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
    covered_ids = {str(item["beat_id"]) for item in assets}
    (tmp_path / "asset_registry.json").write_text(json.dumps({
        "assets": assets,
        "ai_fallback_beats": [beat_id for beat_id in beat_ids if beat_id not in covered_ids],
        "native_treatments": [
            {
                "id": f"fake-native-{i}",
                "beat_id": beat_ids[i % len(beat_ids)],
                "kind": "remotion_native_motion",
                "description": "slow zoom / pan / highlight on sourced footage",
            }
            for i in range(contract["min_native_motion_treatments"])
        ],
    }), encoding="utf-8")

    job = {"production_recipe": recipe}
    assert contract["min_native_motion_treatments"] == 0
    validate_phase_quality("footage", tmp_path, job)


def test_footage_quality_gate_rejects_standalone_native_motion_as_coverage(tmp_path: Path):
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "beats": [{"beat_id": "B001", "visual_type": "native_motion"}],
    }), encoding="utf-8")
    (tmp_path / "asset_registry.json").write_text(json.dumps({
        "assets": [],
        "native_treatments": [{
            "id": "N1",
            "beat_id": "B001",
            "kind": "remotion_native_motion",
        }],
        "ai_fallback_beats": [],
    }), encoding="utf-8")
    legacy_job = {
        "production_recipe": {
            "quality_contract": {
                "version": 6,
                "enforce": True,
                "min_scene_count": 1,
                "min_native_motion_treatments": 52,
            }
        }
    }

    with pytest.raises(RuntimeError, match="standalone native_treatments are not allowed"):
        validate_phase_quality("footage", tmp_path, legacy_job)


def test_footage_quality_gate_rejects_presentation_effect_without_base_media_or_ai_route(tmp_path: Path):
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "beats": [{"beat_id": "B001", "visual_type": "sourced_video"}],
    }), encoding="utf-8")
    (tmp_path / "asset_registry.json").write_text(json.dumps({
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [{
            "id": "P1",
            "beat_id": "B001",
            "kind": "media_annotation_overlay",
        }],
        "ai_fallback_beats": [],
    }), encoding="utf-8")
    job = {
        "production_recipe": {
            "quality_contract": {
                "enforce": True,
                "min_scene_count": 1,
            }
        }
    }

    with pytest.raises(RuntimeError, match="presentation_effects require approved base media: P1"):
        validate_phase_quality("footage", tmp_path, job)


def test_footage_quality_gate_allows_presentation_effect_for_ai_routed_beat(tmp_path: Path):
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "beats": [{"beat_id": "B001", "visual_type": "sourced_video"}],
    }), encoding="utf-8")
    (tmp_path / "asset_registry.json").write_text(json.dumps({
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [{
            "id": "P1",
            "beat_id": "B001",
            "kind": "media_annotation_overlay",
        }],
        "ai_fallback_beats": ["B001"],
    }), encoding="utf-8")
    job = {
        "production_recipe": {
            "quality_contract": {
                "enforce": True,
                "min_scene_count": 1,
            }
        }
    }

    validate_phase_quality("footage", tmp_path, job)


def test_footage_quality_gate_passes_video_first_mix_with_zero_stills(tmp_path: Path):
    recipe = normalize_production_recipe(None, target_duration_minutes=5)
    contract = recipe["quality_contract"]
    beat_ids = [f"B{i + 1:03d}" for i in range(contract["min_scene_count"])]
    native_ids = set(beat_ids[:contract["min_native_motion_treatments"]])
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "target_duration_sec": 300,
        "beats": [
            {
                "beat_id": beat_id,
                "visual_type": "sourced_video+native_motion" if beat_id in native_ids else "sourced_video",
            }
            for beat_id in beat_ids
        ],
    }), encoding="utf-8")

    candidates = []
    assets = []
    for i in range(contract["min_video_clip_uses"]):
        candidate_id = f"video-{i}"
        candidates.append({
            "candidate_id": candidate_id,
            "decision": "ACCEPT",
            "visually_inspected_actual_content": True,
        })
        assets.append({
            "id": f"V{i}",
            "beat_id": beat_ids[i % len(beat_ids)],
            "kind": "sourced_video",
            "source": {
                "candidate_id": candidate_id,
                "url": f"https://video.test/{i % contract['min_unique_video_sources']}",
            },
        })

    (tmp_path / "footage_review.json").write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
    covered_ids = {str(item["beat_id"]) for item in assets}
    (tmp_path / "asset_registry.json").write_text(json.dumps({
        "assets": assets,
        "ai_fallback_beats": [beat_id for beat_id in beat_ids if beat_id not in covered_ids],
        "native_treatments": [
            {
                "id": f"native-{i}",
                "beat_id": beat_id,
                "kind": "remotion_native_motion",
                "description": "explanatory map or diagram",
            }
            for i, beat_id in enumerate(sorted(native_ids))
        ],
    }), encoding="utf-8")

    validate_phase_quality("footage", tmp_path, {"production_recipe": recipe})
