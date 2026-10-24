from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import pytest

from documentary import models
from documentary.ai_visual import AIVisualCoordinator
from documentary.codex_gateway import StageResult
from documentary.prompts import build_phase_prompt, build_producer_chat_prompt
from documentary.quality import normalize_production_recipe
from documentary.service import DocumentaryService


def test_pipeline_contract_adds_visuals_after_voice_and_filters_by_strategy():
    assert models.PHASES == (
        "plan",
        "voice",
        "visuals",
        "footage",
        "ai_visual",
        "edit",
        "seo",
        "qc",
    )
    assert models.REQUIRED_ARTIFACTS["visuals"] == ("visual_manifest.json", "visual_prompts.json")
    effective = getattr(models, "effective_phases", None)
    assert callable(effective)
    assert effective({"visual_strategy": "full_ai"}) == (
        "plan", "voice", "visuals", "ai_visual", "edit", "seo", "qc"
    )
    assert effective({"visual_strategy": "full_footage"}) == (
        "plan", "voice", "visuals", "footage", "edit", "seo", "qc"
    )
    assert effective({"visual_strategy": "hybrid"}) == models.PHASES
    assert effective({"visual_strategy": "footage_first"}) == (
        "plan", "voice", "visuals", "footage", "edit", "seo", "qc"
    )


def test_quality_recipe_uses_three_strategies_without_fixed_hybrid_ratio():
    hybrid = normalize_production_recipe({}, target_duration_minutes=5, visual_strategy="hybrid")
    contract = hybrid["quality_contract"]
    assert hybrid["visual_strategy"] == "hybrid"
    assert contract["visual_strategy"] == "hybrid"
    assert contract["visual_routing_policy"] == "story_driven"
    assert "target_ai_visual_ratio" not in contract
    assert "target_real_footage_ratio" not in contract
    assert not any("80%" in rule or "20%" in rule for rule in hybrid["asset_rules"])

    full_ai = normalize_production_recipe({}, target_duration_minutes=5, visual_strategy="full_ai")
    assert full_ai["quality_contract"]["min_video_clip_uses"] == 0
    assert full_ai["quality_contract"]["visual_routing_policy"] == "ai_only"

    full_footage = normalize_production_recipe({}, target_duration_minutes=5, visual_strategy="full_footage")
    assert full_footage["quality_contract"]["visual_routing_policy"] == "footage_only"


def test_visuals_module_is_local_and_available_for_stp_phase():
    assert importlib.util.find_spec("documentary.visuals") is not None


def test_general_ai_prompt_is_not_locked_to_producer_role_and_knows_visuals_phase():
    prompt = build_producer_chat_prompt([], "hãy sửa app và viết lại nội dung nếu cần")
    assert "Your scope is the application itself" not in prompt
    assert "COFI PRODUCER CODEX" not in prompt
    assert "general-purpose" in prompt.lower() or "mọi yêu cầu" in prompt.lower()
    assert "KHÔNG ÉP ROLE, KHÔNG GIỚI HẠN CHỦ ĐỀ" in prompt
    assert "persona cố định" in prompt
    assert "browser/web" in prompt
    assert "không phải role bắt buộc" in prompt
    assert "plan|voice|visuals|footage|ai_visual|edit|seo|qc" in prompt


def _compact(text: str) -> str:
    return "".join(str(text).split())


def test_visual_split_preserves_all_script_text_and_uses_short_semantic_clauses():
    from documentary.visuals import split_visual_text

    source = "Năm 1919, cánh cửa đóng lại, nhưng câu chuyện vẫn tiếp tục. Đây là câu thứ hai rất ngắn!"
    parts = split_visual_text(source, max_chars=72)
    assert len(parts) >= 4
    assert _compact("".join(parts)) == _compact(source)
    assert all(part.strip() for part in parts)
    assert max(len(part) for part in parts) <= 90


def test_visuals_phase_refines_voice_timing_and_writes_one_prompt_per_unit(tmp_path: Path):
    from documentary.visuals import VisualsCoordinator

    narration = "Năm 1919, cánh cửa đóng lại, nhưng câu chuyện vẫn tiếp tục. Một bí mật khác xuất hiện."
    (tmp_path / "script.md").write_text(narration, encoding="utf-8")
    (tmp_path / "voice_manifest.json").write_text(json.dumps({
        "duration_sec": 12.0,
        "beats": [{
            "beat_id": "B001",
            "text": narration,
            "start_sec": 0.0,
            "end_sec": 12.0,
            "duration_sec": 12.0,
        }],
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "target_duration_sec": 12,
        "beats": [{
            "beat_id": "B001",
            "story_group": "G01",
            "narration_text": narration,
            "source_priority": "ai_ok",
            "visual_description": "Căn phòng lịch sử căng thẳng",
            "framing_motion_intent": "slow push in",
        }],
    }, ensure_ascii=False), encoding="utf-8")

    result = VisualsCoordinator().run({
        "visual_strategy": "full_ai",
        "ai_media_mode": "mixed",
        "ai_visual": {"style_mode": "custom", "custom_style": "ink editorial sketch"},
    }, tmp_path)

    assert result.returncode == 0
    visual = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    prompts = json.loads((tmp_path / "visual_prompts.json").read_text(encoding="utf-8"))
    beats = visual["beats"]
    assert len(beats) >= 4
    assert _compact("".join(item["narration_text"] for item in beats)) == _compact(narration)
    assert beats[0]["start_sec"] == 0.0
    assert beats[-1]["end_sec"] == 12.0
    assert all(beats[i]["end_sec"] <= beats[i + 1]["start_sec"] for i in range(len(beats) - 1))
    assert all(item["parent_beat_id"] == "B001" for item in beats)
    assert all(item["visual_route"] == "ai_visual" for item in beats)
    assert all(item["story_group"] == "G01" for item in beats)
    assert len(prompts["prompts"]) == len(beats)
    assert [item["beat_id"] for item in prompts["prompts"]] == [item["beat_id"] for item in beats]
    assert all(item["prompt"].strip() for item in prompts["prompts"])


def test_visuals_rerun_recovers_parent_metadata_from_previous_refined_manifest(tmp_path: Path):
    from documentary.visuals import VisualsCoordinator

    narration = "Một hồ sơ được mở ra, rồi căn phòng im lặng."
    (tmp_path / "script.md").write_text(narration, encoding="utf-8")
    (tmp_path / "voice_manifest.json").write_text(json.dumps({
        "duration_sec": 8.0,
        "beats": [{"beat_id": "B001", "text": narration, "start_sec": 0.0, "end_sec": 8.0}],
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "beats": [{
            "beat_id": "B001",
            "source_priority": "ai_ok",
            "story_group": "G01",
            "visual_description": "Hồ sơ mật trên bàn",
        }],
    }, ensure_ascii=False), encoding="utf-8")
    coordinator = VisualsCoordinator()
    job = {"visual_strategy": "hybrid", "ai_media_mode": "mixed"}

    coordinator.run(job, tmp_path)
    coordinator.run(job, tmp_path)

    rerun = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    assert rerun["beats"]
    assert all(item["source_priority"] == "ai_ok" for item in rerun["beats"])
    assert all(item["story_group"] == "G01" for item in rerun["beats"])
    assert all(item["visual_description"] == "Hồ sơ mật trên bàn" for item in rerun["beats"])


def test_create_job_persists_full_ai_media_and_custom_style_settings(tmp_path: Path):
    service = DocumentaryService(tmp_path)
    job = service.create_job({
        "title": "Full AI project",
        "visual_strategy": "full_ai",
        "ai_media_mode": "video",
        "ai_visual": {
            "style_mode": "custom",
            "custom_style": "paper cut collage",
        },
    })

    assert job["visual_strategy"] == "full_ai"
    assert job["ai_media_mode"] == "video"
    assert job["ai_visual"]["coverage_mode"] == "full_ai"
    assert job["ai_visual"]["style_mode"] == "custom"
    assert job["ai_visual"]["custom_style"] == "paper cut collage"


def test_existing_project_can_switch_to_full_ai_and_skip_footage(tmp_path: Path):
    service = DocumentaryService(tmp_path)
    job = service.create_job({"title": "Switch branch", "visual_strategy": "full_footage", "ai_media_mode": "mixed"})
    service.store.update(job["id"], {"phases": {
        "plan": {"status": "succeeded"},
        "voice": {"status": "succeeded"},
        "visuals": {"status": "succeeded"},
        "footage": {"status": "interrupted"},
        "edit": {"status": "succeeded"},
    }})

    switched = service.update_production_settings(job["id"], {
        "visual_strategy": "full_ai",
        "ai_media_mode": "image",
    })

    assert switched["visual_strategy"] == "full_ai"
    assert switched["ai_media_mode"] == "image"
    assert switched["ai_visual"]["coverage_mode"] == "full_ai"
    assert switched["ai_visual"]["ai_media_mode"] == "image"
    assert switched["production_recipe"]["quality_contract"]["visual_routing_policy"] == "ai_only"
    assert switched["production_recipe"]["quality_contract"]["require_must_real_source_coverage"] is False
    assert switched["phases"]["footage"]["status"] == "interrupted"
    assert switched["phases"]["ai_visual"]["status"] == "pending"
    assert switched["phases"]["edit"]["status"] == "pending"
    assert service.next_phase(job["id"]) == "ai_visual"


def test_service_next_phase_uses_effective_branch_instead_of_global_phase_order(tmp_path: Path):
    service = DocumentaryService(tmp_path)
    job = service.create_job({"title": "AI branch", "visual_strategy": "full_ai"})
    service.store.update(job["id"], {"phases": {
        "plan": {"status": "succeeded"},
        "voice": {"status": "succeeded"},
        "visuals": {"status": "succeeded"},
    }})
    current = service.get_job(job["id"])
    assert service.next_phase(job["id"]) == "ai_visual"
    assert service._previous_phases_succeeded(current, "ai_visual") is True


class _SimpleMediaRunner:
    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, scene, request_path):
        self.calls.append(dict(scene))
        output = Path(scene["_output_directory"])
        output.mkdir(parents=True, exist_ok=True)
        if scene["task_type"] == "image_to_video":
            path = output / f"{scene['_output_stem']}.mp4"
        else:
            path = output / f"{scene['_output_stem']}.jpg"
        path.write_bytes(b"generated")
        return str(path)


def test_full_ai_video_mode_needs_no_footage_registry_and_generates_video_for_every_beat(tmp_path: Path):
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "target_duration_sec": 8,
        "beats": [{
            "beat_id": "B001-V01",
            "narration_text": "A reconstruction moves through the room.",
            "visual_description": "historical room reconstruction",
            "visual_route": "ai_visual",
            "source_priority": "ai_ok",
        }],
    }), encoding="utf-8")
    runner = _SimpleMediaRunner()
    result = AIVisualCoordinator(tool_runner=runner).run({
        "visual_strategy": "full_ai",
        "ai_media_mode": "video",
        "ai_visual": {"coverage_mode": "full_ai", "ai_media_mode": "video", "veo_enabled": True},
    }, tmp_path)

    assert result.returncode == 0
    assert (tmp_path / "asset_registry.json").exists()
    assert [item["task_type"] for item in runner.calls] == ["image_generation", "image_to_video"]
    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["generated"][0]["video_path"]


class _FakeVisualsCoordinator:
    def __init__(self):
        self.calls = []

    def run(self, job, workspace):
        self.calls.append((job["id"], Path(workspace)))
        return StageResult(0, "visuals ok", Path(workspace) / "visual_prompts.json")


def test_service_run_phase_dispatches_visuals_to_local_coordinator(tmp_path: Path):
    visuals = _FakeVisualsCoordinator()
    service = DocumentaryService(tmp_path, visuals_coordinator=visuals)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    result = service._run_phase({"id": "J1"}, "visuals", workspace)
    assert result.last_message == "visuals ok"
    assert visuals.calls == [("J1", workspace)]


def test_start_rejects_phase_disabled_by_visual_strategy(tmp_path: Path):
    service = DocumentaryService(tmp_path)
    job = service.create_job({"title": "AI only", "visual_strategy": "full_ai"})
    service.store.update(job["id"], {"phases": {
        "plan": {"status": "succeeded"},
        "voice": {"status": "succeeded"},
        "visuals": {"status": "succeeded"},
    }})
    with pytest.raises(ValueError, match="disabled"):
        service.start(job["id"], "footage")


def test_run_pipeline_filters_disabled_branch_phases(tmp_path: Path):
    service = DocumentaryService(tmp_path)
    job = service.create_job({"title": "AI branch", "visual_strategy": "full_ai"})
    service.store.update(job["id"], {"phases": {
        "plan": {"status": "succeeded"},
        "voice": {"status": "succeeded"},
    }})
    queued = []
    service._queue_phase_sequence = lambda job_id, phases: queued.extend(phases) or service.get_job(job_id)
    service.run_pipeline(job["id"], "visuals", "edit")
    assert queued == ["visuals", "ai_visual", "edit"]


def test_run_sequence_completion_ignores_disabled_branch_phase(tmp_path: Path):
    service = DocumentaryService(tmp_path)
    job = service.create_job({"title": "AI complete", "visual_strategy": "full_ai"})
    service.store.update(job["id"], {"phases": {
        phase: {"status": "succeeded"}
        for phase in models.effective_phases(job)
    }})
    service._run_sequence(job["id"], [])
    assert service.get_job(job["id"])["status"] == "completed"


def test_rerun_voice_invalidates_visuals_and_active_visual_branch(tmp_path: Path):
    service = DocumentaryService(tmp_path)
    job = service.create_job({"title": "AI rerun", "visual_strategy": "full_ai"})
    service.store.update(job["id"], {"phases": {
        phase: {"status": "succeeded"}
        for phase in models.effective_phases(job)
    }})
    reset = service._reset_from_phase(job["id"], "voice")
    assert reset["phases"]["voice"]["status"] == "pending"
    assert reset["phases"]["visuals"]["status"] == "pending"
    assert reset["phases"]["ai_visual"]["status"] == "pending"


def test_visuals_quality_gate_accepts_structurally_complete_refined_prompts(tmp_path: Path):
    from documentary.quality import normalize_production_recipe, validate_phase_quality

    recipe = normalize_production_recipe(None, target_duration_minutes=2, visual_strategy="full_ai")
    min_scenes = int(recipe["quality_contract"]["min_scene_count"])
    beats = []
    prompts = []
    for index in range(min_scenes):
        beat_id = f"B{index + 1:03d}-V01"
        beats.append({
            "beat_id": beat_id,
            "parent_beat_id": f"B{index + 1:03d}",
            "narration_text": f"Narration {index + 1}",
            "prompt": f"Prompt {index + 1}",
            "start_sec": float(index),
            "end_sec": float(index + 1),
            "visual_route": "ai_visual",
        })
        prompts.append({
            "beat_id": beat_id,
            "parent_beat_id": f"B{index + 1:03d}",
            "text": f"Narration {index + 1}",
            "prompt": f"Prompt {index + 1}",
        })
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    (tmp_path / "visual_prompts.json").write_text(json.dumps({"prompts": prompts}), encoding="utf-8")

    validate_phase_quality("visuals", tmp_path, {"production_recipe": recipe})


def test_plan_prompt_describes_story_driven_hybrid_without_ratio(tmp_path: Path):
    prompt = build_phase_prompt(
        {"title": "Hybrid", "visual_strategy": "hybrid", "production_recipe": {"visual_strategy": "hybrid"}},
        "plan",
        tmp_path,
        tmp_path / "remotion",
    )
    assert "80%" not in prompt
    assert "20%" not in prompt
    assert "fixed ratio" in prompt.lower() or "story" in prompt.lower()
    assert "Visuals/STP" in prompt


def test_create_api_schema_and_ai_visual_settings_expose_new_project_controls():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'visual_strategy: str = "full_footage"' in source
    assert 'ai_media_mode: str = "mixed"' in source
    assert 'ai_visual: dict[str, Any] = Field(default_factory=dict)' in source
    assert "custom_style: str | None = None" in source
    assert '@api.get("/api/ai-visual/style-presets")' in source


def test_create_ui_has_three_visual_branches_ai_modes_styles_reference_and_visuals_workspace():
    html = Path("static/index.html").read_text(encoding="utf-8")
    assert 'value="full_ai"' in html
    assert 'value="full_footage"' in html
    assert 'value="hybrid"' in html
    assert 'name="ai_media_mode" value="image"' in html
    assert 'name="ai_media_mode" value="video"' in html
    assert 'name="ai_media_mode" value="mixed"' in html
    assert 'id="createAiStylePreset"' in html
    assert 'id="discoverCreateTopicsBtn"' in html
    assert 'id="createTopicSuggestions"' in html
    assert 'id="createTitleInput"' in html
    assert 'name="title" required' not in html
    assert "AI phân tích kênh mình + đối thủ" in html
    assert 'id="createAiCustomStyle"' in html
    assert 'id="createStyleReferenceInput"' in html
    assert 'id="createPipelineFlow"' in html
    assert 'data-app-tab="visuals"' in html
    assert 'data-app-pane="visuals"' in html
    assert "80% AI Visual" not in html
    assert "COFI PRODUCER AI" not in html


def test_ui_routes_only_effective_phases_and_uploads_reference_after_creation():
    js = Path("static/app.js").read_text(encoding="utf-8")
    assert 'const phases = ["plan", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc"]' in js
    assert "function effectivePhases(job)" in js
    assert "function updateCreatePipelineFlow()" in js
    assert "ai_media_mode: raw.ai_media_mode" in js
    assert "custom_style: raw.ai_custom_style" in js
    assert "reference_image_data_url" in js
    assert "async function discoverCreateTopics" in js
    assert "/today?target_duration_minutes=" in js
    assert "state.selectedCreateTopic" in js
    assert 'visuals: "visuals"' in js
    assert "/production-settings" in js
    assert "Full AI · bỏ qua Footage" in js


def test_ui_keeps_original_sidebar_flow_without_copied_eight_step_journey():
    html = Path("static/index.html").read_text(encoding="utf-8")
    js = Path("static/app.js").read_text(encoding="utf-8")

    assert "channel-studio-journey" not in html
    assert "data-journey-tab" not in html
    assert "studioJourneyOrder" not in js
    for tab in ("script", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc"):
        assert f'data-app-tab="{tab}"' in html


def test_pipeline_polling_does_not_switch_away_from_preview():
    js = Path("static/app.js").read_text(encoding="utf-8")
    assert "followPipelineJob(externalActive, { switchTab: false })" in js
    assert "followPipelineJob(current, { switchTab: false })" in js
