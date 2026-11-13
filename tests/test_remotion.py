import json
from pathlib import Path

from documentary.remotion import RemotionManager


def test_remotion_session_and_checkpoint_are_persistent(tmp_path: Path):
    project = tmp_path / "CofiRemotion"
    (project / "src").mkdir(parents=True)
    (project / "src" / "Demo.tsx").write_text("export const Demo=()=>null", encoding="utf-8")
    workspace = tmp_path / "job"
    workspace.mkdir()
    manager = RemotionManager(project, studio_port=8890)

    session = manager.ensure_session({"id": "job-1"}, workspace)
    checkpoint = manager.checkpoint({"id": "job-1"}, workspace, note="da dung den day")

    assert session["studio_url"] == "http://127.0.0.1:8890"
    assert session["composition_url"] == "http://127.0.0.1:8890/Documentary-job-1"
    assert session["composition_registered"] is False
    assert (workspace / "edit_session.json").exists()
    assert (workspace / "edit_checkpoint.json").exists()
    assert checkpoint["source_hashes"]
    loaded = json.loads((workspace / "edit_checkpoint.json").read_text(encoding="utf-8"))
    assert loaded["note"] == "da dung den day"


def test_remotion_session_detects_registered_job_composition(tmp_path: Path):
    project = tmp_path / "CofiRemotion"
    (project / "src").mkdir(parents=True)
    (project / "src" / "Composition.tsx").write_text(
        'export const Root=()=> <Composition id="Documentary-job-1" component={Demo} durationInFrames={300} fps={30} width={1920} height={1080}/>;',
        encoding="utf-8",
    )
    workspace = tmp_path / "job"
    workspace.mkdir()
    manager = RemotionManager(project, studio_port=8890)

    session = manager.ensure_session({"id": "job-1"}, workspace)
    checkpoint = manager.checkpoint({"id": "job-1"}, workspace)

    assert session["composition_registered"] is True
    assert checkpoint["composition_registered"] is True


def test_prepare_job_media_publishes_canonical_assets_voice_and_subtitles(tmp_path: Path):
    project = tmp_path / "CofiRemotion"
    workspace = tmp_path / "job"
    media = workspace / "media" / "codex"
    audio = workspace / "audio"
    media.mkdir(parents=True)
    audio.mkdir(parents=True)
    clip = media / "B001_clip.mp4"
    still = media / "B001_still.jpg"
    narration = audio / "narration.wav"
    clip.write_bytes(b"clip")
    still.write_bytes(b"still")
    narration.write_bytes(b"voice")
    (workspace / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")
    (workspace / "voice_manifest.json").write_text(
        json.dumps({"narration_path": str(narration)}), encoding="utf-8"
    )
    (workspace / "asset_registry.json").write_text(
        json.dumps({
            "assets": [
                {"id": "A1", "beat_id": "B001", "kind": "sourced_video", "path": str(clip)},
                {"id": "A2", "beat_id": "B001", "kind": "sourced_still", "path": str(still)},
            ]
        }),
        encoding="utf-8",
    )
    manager = RemotionManager(project)

    manifest = manager.prepare_job_media({"id": "job-1"}, workspace)

    public_job = project / "public" / "jobs" / "job-1"
    assert manifest["asset_count"] == 2
    assert {item["public_file"] for item in manifest["assets"]} == {"B001_clip.mp4", "B001_still.jpg"}
    assert (public_job / "B001_clip.mp4").read_bytes() == b"clip"
    assert (public_job / "B001_still.jpg").read_bytes() == b"still"
    assert (public_job / "narration.wav").read_bytes() == b"voice"
    assert (public_job / "subtitles.srt").exists()
    assert (workspace / "remotion_media_manifest.json").exists()


def test_prepare_job_media_records_lightweight_studio_proxy_without_replacing_original(tmp_path: Path, monkeypatch):
    project = tmp_path / "CofiRemotion"
    workspace = tmp_path / "job"
    media = workspace / "media" / "codex"
    media.mkdir(parents=True)
    clip = media / "B001_clip.webm"
    clip.write_bytes(b"full-quality-original")
    (workspace / "asset_registry.json").write_text(
        json.dumps({
            "assets": [
                {"id": "A1", "beat_id": "B001", "kind": "sourced_video", "path": str(clip)},
            ]
        }),
        encoding="utf-8",
    )
    manager = RemotionManager(project, tools_dir=tmp_path / "tools")

    def fake_proxy(source: Path, preview_dir: Path):
        target = preview_dir / "B001_clip.preview.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"lightweight-preview")
        return target

    monkeypatch.setattr(manager, "_ensure_preview_proxy", fake_proxy)

    manifest = manager.prepare_job_media({"id": "job-1"}, workspace)

    public_job = project / "public" / "jobs" / "job-1"
    asset = manifest["assets"][0]
    assert asset["public_file"] == "B001_clip.webm"
    assert asset["preview_file"] == "_preview/B001_clip.preview.mp4"
    assert (public_job / "B001_clip.webm").read_bytes() == b"full-quality-original"
    assert (public_job / "_preview" / "B001_clip.preview.mp4").read_bytes() == b"lightweight-preview"


def test_start_studio_runs_auto_update_before_launch(tmp_path: Path, monkeypatch):
    project = tmp_path / "CofiRemotion"
    project.mkdir()
    workspace = tmp_path / "job"
    workspace.mkdir()
    manager = RemotionManager(project, studio_port=8890)
    calls = []
    running = iter([False, False, True, True])

    monkeypatch.setattr(manager, "is_running", lambda: next(running))
    monkeypatch.setattr(manager, "_run_auto_update", lambda: calls.append("update"))
    monkeypatch.setattr("documentary.remotion.shutil.which", lambda name: "npx.cmd" if name == "npx" else None)

    def fake_popen(*args, **kwargs):
        calls.append("studio")
        return object()

    monkeypatch.setattr("documentary.remotion.subprocess.Popen", fake_popen)

    session = manager.start_studio({"id": "job-1"}, workspace)

    assert calls == ["update", "studio"]
    assert session["studio_running"] is True


def test_prepare_job_media_accepts_job_scoped_remotion_vox_plates_and_blocks_outside(tmp_path: Path):
    import pytest

    project = tmp_path / "CofiRemotion"
    workspace = tmp_path / "job"
    media = workspace / "media" / "ai"
    media.mkdir(parents=True)
    ai_img = media / "B001-V01_ai_keyframe.jpg"
    ai_img.write_bytes(b"ai-keyframe")

    vox_plate = project / "public" / "jobs" / "job-1" / "vox_plates" / "arch_anhui_village.jpg"
    vox_plate.parent.mkdir(parents=True)
    vox_plate.write_bytes(b"curated-plate")
    geo_meta = project / "public" / "jobs" / "job-1" / "vox_plates" / "geo_meta.json"
    geo_meta.write_text('{"crs":"EPSG:4326"}', encoding="utf-8")

    (workspace / "asset_registry.json").write_text(
        json.dumps({
            "assets": [
                {"id": "A1", "beat_id": "B001-V01", "kind": "ai_keyframe", "path": str(ai_img)},
                {"id": "P1", "kind": "vox_editorial_plate", "path": str(vox_plate)},
                {"id": "G1", "kind": "vox_editorial_plate", "path": str(geo_meta)},
            ]
        }),
        encoding="utf-8",
    )
    manager = RemotionManager(project)
    manifest = manager.prepare_job_media({"id": "job-1"}, workspace)

    assert manifest["asset_count"] == 3
    assert {item["public_file"] for item in manifest["assets"]} == {
        "B001-V01_ai_keyframe.jpg",
        "vox_plates/arch_anhui_village.jpg",
        "vox_plates/geo_meta.json",
    }
    assert (workspace / "media" / "edit_plates" / "vox_plates" / "arch_anhui_village.jpg").read_bytes() == b"curated-plate"
    assert vox_plate.read_bytes() == b"curated-plate"

    # Paths in another job's folder or outside both roots must still be blocked
    other_job_plate = project / "public" / "jobs" / "other-job" / "vox_plates" / "leak.jpg"
    other_job_plate.parent.mkdir(parents=True)
    other_job_plate.write_bytes(b"leak")
    (workspace / "asset_registry.json").write_text(
        json.dumps({"assets": [{"id": "LEAK", "kind": "vox_editorial_plate", "path": str(other_job_plate)}]}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="Media Edit nằm ngoài workspace"):
        manager.prepare_job_media({"id": "job-1"}, workspace)
