import json
from pathlib import Path

from documentary.models import PHASES, REQUIRED_ARTIFACTS
from documentary.prompts import build_edit_chat_prompt, build_phase_prompt, build_producer_chat_prompt
from documentary.quality import normalize_production_recipe, validate_phase_quality


ROOT = Path(__file__).resolve().parents[1]


def test_producer_prompt_bounds_old_chat_without_truncating_current_request():
    history = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"OLD_{index} " + ("x" * 5000)}
        for index in range(12)
    ]
    current_request = "CURRENT_REQUEST_" + ("y" * 7000)
    baseline = build_producer_chat_prompt([], current_request)

    prompt = build_producer_chat_prompt([], current_request, history=history)

    assert current_request in prompt
    assert "OLD_11" in prompt
    assert "OLD_0" not in prompt
    assert len(prompt) - len(baseline) < 16_000


def test_seo_is_explicit_pipeline_phase_before_qc():
    assert PHASES == ("plan", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc")
    assert REQUIRED_ARTIFACTS["seo"] == ("seo_package.json",)


def test_codex_session_permissions_include_reference_research_and_packaging():
    permissions = json.loads(
        (ROOT / "COFI_BRAIN" / "knowledge" / "codex_session_permissions.json").read_text(encoding="utf-8")
    )

    for capability in (
        "radar_read",
        "channel_profile_read",
        "competitor_reference_research",
        "web_research",
        "seo_packaging",
        "thumbnail_reference_inspection",
        "thumbnail_prompt_generation",
        "production_phase_control",
    ):
        assert permissions.get(capability) is True


def test_seo_prompt_requires_competitor_evidence_and_original_thumbnail_prompt(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job-1", "title": "American Secrets", "market": "US", "language": "en", "production_recipe": {}},
        "seo",
        tmp_path,
        tmp_path / "CofiRemotion",
    ).lower()

    assert "seo_reference_context.json" in prompt
    assert "attached reference thumbnails" in prompt
    assert "seo_package.json" in prompt
    assert "recommended_title" in prompt
    assert "thumbnail" in prompt
    assert "prompt" in prompt
    assert "tags" in prompt
    assert "hashtags" in prompt
    assert "overlay_text" in prompt
    assert "featured_real_people" in prompt
    assert "identity_references" in prompt
    assert "people_and_text_first" in prompt
    assert "minimal_or_none" in prompt
    assert "85-95%" in prompt
    assert "0-10%" in prompt
    assert "if the video is mainly about one person" in prompt
    assert "curiosity hook" in prompt
    assert "exact facial identity" in prompt
    assert ("competitor thumbnails are never identity references" in prompt or "competitor thumbnail as an identity anchor" in prompt)
    assert "must explicitly instruct" in prompt
    assert "do not copy" in prompt
    assert "do not load or invoke optional skills" in prompt
    assert "workspace files and attached reference thumbnails are sufficient" in prompt


def test_in_app_codex_prompts_allow_current_project_seo_and_profile_refresh(tmp_path: Path):
    producer = build_producer_chat_prompt(
        [],
        "soi kênh mẫu rồi tạo seo và prompt thumbnail",
        selected_job_id="job-1",
        app_context={"app_tab": "seo", "selected_job_id": "job-1"},
    ).lower()
    editor = build_edit_chat_prompt(
        {"id": "job-1", "title": "American Secrets"},
        tmp_path,
        tmp_path / "CofiRemotion",
        "tạo seo và prompt thumbnail cho video này",
    ).lower()

    assert '"phase":"plan|voice|visuals|footage|ai_visual|edit|seo|qc"' in producer
    assert '"type":"refresh_channel_profile"' in producer
    assert '"tab":"overview|radar|create|script|voice|visuals|footage|ai_visual|edit|seo|qc|projects|codex"' in producer
    assert "competitor" in producer or "kênh" in producer
    assert "seo" in editor and "thumbnail" in editor
    assert "unrelated programming, seo" not in editor


def test_seo_quality_validation_accepts_complete_package_without_visual_beat_gate(tmp_path: Path):
    recipe = normalize_production_recipe({}, target_duration_minutes=5)
    package = {
        "version": 1,
        "job_id": "job-1",
        "recommended_title": "A strong original title",
        "title_options": ["A strong original title", "Alternative title"],
        "description": "Original factual description grounded in the documentary.",
        "keywords": ["history", "documentary"],
        "tags": ["history", "documentary"],
        "hashtags": ["#History"],
        "thumbnail": {
            "concept": "A clear single-subject historical composition",
            "prompt": "Create an original people + text documentary thumbnail with one focal subject. Preserve exact facial identity for Jane Example from verified reference https://example.com/jane.jpg. Render exact overlay text THE HIDDEN STORY in large mobile-readable serif type. Keep the background minimal and plain dark green-black.",
            "negative_prompt": "No copied logos, no clutter, no misleading text.",
            "overlay_text": "THE HIDDEN STORY",
            "visual_priority": "people_and_text_first",
            "background_policy": "minimal_or_none",
            "featured_real_people": ["Jane Example"],
            "identity_references": [
                {
                    "name": "Jane Example",
                    "source_url": "https://example.com/jane.jpg",
                    "local_path": "",
                    "visually_verified": True,
                    "verification_basis": "Verified real archival portrait used only for identity fidelity.",
                }
            ],
        },
        "reference_analysis": {"channels": [], "evidence_videos": []},
    }
    (tmp_path / "seo_package.json").write_text(json.dumps(package), encoding="utf-8")

    validate_phase_quality("seo", tmp_path, {"id": "job-1", "production_recipe": recipe})


def test_ui_exposes_seo_thumbnail_step():
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

    assert 'data-app-tab="seo"' in html
    assert 'data-app-pane="seo"' in html
    assert '"plan", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc"' in js
    assert "renderSeoWorkspace" in js
    assert 'seo: "SEO + Thumbnail"' in js
    assert "MÔ TẢ YOUTUBE + HASHTAGS" in js
    assert "VIDEO TAGS · DÁN THẲNG VÀO YOUTUBE" in js
    assert "PROMPT VẼ THUMBNAIL + TEXT" in js
    assert "data-seo-copy" in js
