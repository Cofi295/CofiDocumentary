import json
from pathlib import Path

from documentary.ai_visual import AIVisualCoordinator


class CaptureRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, scene, request_path):
        self.calls.append(dict(scene))
        output_dir = Path(scene["_output_directory"])
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"{scene['_output_stem']}.jpg"
        output.write_bytes(b"generated")
        return str(output)


def write_workspace(workspace: Path, beats: list[dict], *, assets=None, fallback=None):
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    fallback = fallback or []
    (workspace / "asset_registry.json").write_text(json.dumps({
        "assets": assets or [],
        "native_treatments": [],
        "presentation_effects": [],
        "beat_coverage": {},
        "ai_fallback_beats": fallback,
        "ai_usage_notes": [
            {
                "beat_id": beat_id,
                "requires_ai": True,
                "reason": "No verified real media available.",
                "visual_language": {},
            }
            for beat_id in fallback
        ],
    }), encoding="utf-8")


def test_ai_visual_settings_exposes_copied_style_presets_and_defaults(tmp_path: Path):
    settings = AIVisualCoordinator(tool_runner=CaptureRunner()).settings(tmp_path, {})

    names = {item["name"] for item in settings["style_presets"]}
    assert len(names) == 16
    assert "Siêu thực 4D Người vô diện (4D Faceless Forensic)" in names
    assert "Người que (Stickman)" in names
    assert "Sơn dầu (Oil painting)" in names
    assert "Video 2D (US Animation)" in names
    assert "3D Hoạt hình (Pixar/Disney)" in names
    assert "Anime Nhật Bản" in names
    assert "Hiện thực điện ảnh (Cinematic Realism)" in names
    assert "Dark Fantasy (Ma mị/Kinh dị)" in names
    assert "Màu nước (Watercolor)" in names
    assert "Cyberpunk (Viễn tưởng)" in names
    assert "Thủy mặc (Cổ trang/Kiếm hiệp)" in names
    assert "Người Que US" in names
    assert "cinematic 2D editorial cartoon / American comic explainer illustration" in names
    assert settings["style_mode"] == "auto"
    assert settings["coverage_mode"] == "fallback_only"


def test_ai_visual_preset_prompt_is_applied_to_generated_scene(tmp_path: Path):
    write_workspace(
        tmp_path,
        [{"beat_id": "B001", "narration_text": "A scientist studies the brain."}],
        fallback=["B001"],
    )
    runner = CaptureRunner()

    AIVisualCoordinator(tool_runner=runner).run({
        "ai_visual": {
            "style_mode": "preset",
            "style_preset": "Người Que US",
        }
    }, tmp_path)

    assert len(runner.calls) == 1
    prompt = runner.calls[0]["prompt"]
    assert "Hand-drawn doodle documentary /" in prompt
    assert "A scientist studies the brain." in prompt

    ws2 = tmp_path / "ws2"
    write_workspace(
        ws2,
        [{"beat_id": "B001", "narration_text": "An elderly retiree checks a bank passbook."}],
        fallback=["B001"],
    )
    runner_4d = CaptureRunner()
    AIVisualCoordinator(tool_runner=runner_4d).run({
        "ai_visual": {
            "style_mode": "preset",
            "style_preset": "Siêu thực 4D Người vô diện (4D Faceless Forensic)",
        }
    }, ws2)
    assert len(runner_4d.calls) == 1
    assert "Hyper-realistic 4D forensic documentary reconstruction" in runner_4d.calls[0]["prompt"]


def test_ai_visual_style_reference_is_forwarded_to_every_image_scene(tmp_path: Path):
    write_workspace(
        tmp_path,
        [{"beat_id": "B001", "narration_text": "A quiet office scene."}],
        fallback=["B001"],
    )
    reference = tmp_path / "media" / "style_reference" / "reference.png"
    reference.parent.mkdir(parents=True)
    reference.write_bytes(b"png")
    runner = CaptureRunner()

    AIVisualCoordinator(tool_runner=runner).run({
        "ai_visual": {
            "style_reference_image": str(reference),
        }
    }, tmp_path)

    assert runner.calls[0]["reference_image"] == str(reference)
    assert str(reference) in runner.calls[0]["reference_images"]
    assert "visual style reference" in runner.calls[0]["prompt"].lower()


def test_ai_visual_full_ai_targets_all_beats_even_when_real_media_exists(tmp_path: Path):
    real = tmp_path / "media" / "real.jpg"
    real.parent.mkdir(parents=True)
    real.write_bytes(b"real")
    write_workspace(
        tmp_path,
        [
            {"beat_id": "B001", "narration_text": "Already covered."},
            {"beat_id": "B002", "narration_text": "Also generate this."},
        ],
        assets=[{"id": "real-1", "beat_id": "B001", "kind": "sourced_still", "path": str(real)}],
    )
    runner = CaptureRunner()

    result = AIVisualCoordinator(tool_runner=runner).run({
        "ai_visual": {"coverage_mode": "full_ai"}
    }, tmp_path)

    assert result.returncode == 0
    assert [call["id"] for call in runner.calls] == ["B001_ai_image", "B002_ai_image"]
    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["coverage_mode"] == "full_ai"
    assert manifest["target_beat_ids"] == ["B001", "B002"]


def test_ai_visual_workspace_ui_has_style_reference_and_full_ai_controls():
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "static" / "app.js").read_text(encoding="utf-8")

    assert "Phong cách vẽ ảnh" in app_js
    assert "Ảnh tham chiếu phong cách" in app_js
    assert 'value="full_ai"' in app_js
    assert "aiVisualStylePreset" in app_js
    assert "aiVisualStyleReferenceInput" in app_js
