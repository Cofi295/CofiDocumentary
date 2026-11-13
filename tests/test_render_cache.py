import json
import time
from pathlib import Path

from documentary.render_cache import BackgroundRenderCache


def write_project_files(workspace: Path, beat_count: int = 10, beat_seconds: float = 10.0) -> list[dict]:
    beats = [
        {"beat_id": f"B{index + 1:03d}", "target_duration_sec": beat_seconds}
        for index in range(beat_count)
    ]
    voice_beats = []
    cursor = 0.0
    for beat in beats:
        voice_beats.append({
            "beat_id": beat["beat_id"],
            "start_sec": cursor,
            "end_sec": cursor + beat_seconds,
            "duration_sec": beat_seconds,
        })
        cursor += beat_seconds
    (workspace / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    (workspace / "voice_manifest.json").write_text(json.dumps({"duration_sec": cursor, "beats": voice_beats}), encoding="utf-8")
    return beats


def write_progress(workspace: Path, completed: list[str], total: int, status: str = "running") -> None:
    assigned = [f"B{index + 1:03d}" for index in range(total)]
    (workspace / "edit_progress.json").write_text(json.dumps({
        "version": 1,
        "status": status,
        "assigned_beat_ids": assigned,
        "completed_beat_ids": completed,
        "pending_beat_ids": [beat_id for beat_id in assigned if beat_id not in completed],
        "completed_beats": len(completed),
        "total_beats": total,
    }), encoding="utf-8")


class FakeRenderRunner:
    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, command: list[str], cwd: Path, log_path: Path) -> int:
        self.calls.append(list(command))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("ok", encoding="utf-8")
        if "remotion" in command:
            video = Path(command[4])
            audio_arg = next(value for value in command if value.startswith("--separate-audio-to="))
            audio = Path(audio_arg.split("=", 1)[1])
            video.parent.mkdir(parents=True, exist_ok=True)
            audio.parent.mkdir(parents=True, exist_ok=True)
            video.write_bytes(b"video-chunk")
            audio.write_bytes(b"audio-chunk")
        else:
            manifest = json.loads(Path(command[2]).read_text(encoding="utf-8"))
            output = Path(manifest["output_path"])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"combined-video")
        return 0


def make_cache(tmp_path: Path, runner: FakeRenderRunner) -> BackgroundRenderCache:
    remotion_dir = tmp_path / "CofiRemotion"
    (remotion_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (remotion_dir / "src").mkdir(parents=True, exist_ok=True)
    (remotion_dir / "src" / "index.ts").write_text("export {};", encoding="utf-8")
    (remotion_dir / "scripts" / "combine-cofi-cache.mjs").write_text("// fake", encoding="utf-8")
    cache = BackgroundRenderCache(remotion_dir, chunk_seconds=30, concurrency=1, poll_interval=0.02, runner=runner)
    cache._npx = lambda: "npx"  # type: ignore[method-assign]
    return cache


def job() -> dict:
    return {
        "id": "job-1",
        "production_recipe": {
            "quality_contract": {"min_resolution": {"width": 1920, "height": 1080}}
        },
    }


def test_render_cache_only_renders_chunks_behind_completed_edit_frontier(tmp_path: Path):
    beats = write_project_files(tmp_path, beat_count=10, beat_seconds=10)
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)

    write_progress(tmp_path, ["B001", "B002", "B003"], total=10)
    first = cache.render_ready(job(), tmp_path, beats)
    assert first["ready_chunks"] == 1
    assert len([call for call in runner.calls if "remotion" in call]) == 1

    write_progress(tmp_path, [f"B{index:03d}" for index in range(1, 7)], total=10)
    second = cache.render_ready(job(), tmp_path, beats)
    assert second["ready_chunks"] == 2
    render_calls = [call for call in runner.calls if "remotion" in call]
    assert len(render_calls) == 2
    assert "--frames=0-899" in render_calls[0]
    assert "--frames=900-1799" in render_calls[1]


def test_render_cache_invalidates_only_chunks_touching_edited_beat(tmp_path: Path):
    beats = write_project_files(tmp_path, beat_count=7, beat_seconds=10)
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    write_progress(tmp_path, [f"B{index:03d}" for index in range(1, 8)], total=7, status="completed")
    ready = cache.render_ready(job(), tmp_path, beats, render_all=True)
    assert ready["ready_chunks"] == 3

    invalidated = cache.invalidate(tmp_path, beat_id="B004")
    assert invalidated == [2]
    manifest = json.loads((tmp_path / "render_cache_manifest.json").read_text(encoding="utf-8"))
    assert [chunk["status"] for chunk in manifest["chunks"]] == ["ready", "pending", "ready"]


def test_prepare_invalidates_all_chunks_when_remotion_source_changes(tmp_path: Path):
    beats = write_project_files(tmp_path, beat_count=7, beat_seconds=10)
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    write_progress(tmp_path, [f"B{index:03d}" for index in range(1, 8)], total=7, status="completed")
    ready = cache.render_ready(job(), tmp_path, beats, render_all=True)
    assert ready["ready_chunks"] == 3

    source = cache.remotion_dir / "src" / "index.ts"
    source.write_text("export const revision = 2;", encoding="utf-8")
    refreshed = cache.prepare(job(), tmp_path, beats)

    assert refreshed["ready_chunks"] == 0
    assert all(chunk["status"] == "pending" for chunk in refreshed["chunks"])

    re_rendered = cache.render_ready(job(), tmp_path, beats, render_all=True)
    assert re_rendered["ready_chunks"] == 3
    assert len([call for call in runner.calls if "remotion" in call]) == 6


def test_render_cache_stops_immediately_when_source_changes_between_chunks(tmp_path: Path):
    beats = write_project_files(tmp_path, beat_count=7, beat_seconds=10)
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    write_progress(tmp_path, [f"B{index:03d}" for index in range(1, 8)], total=7, status="completed")
    original_runner = cache.runner
    changed = False

    def changing_runner(command: list[str], cwd: Path, log_path: Path) -> int:
        nonlocal changed
        result = original_runner(command, cwd, log_path)
        if "remotion" in command and not changed:
            changed = True
            (cache.remotion_dir / "src" / "index.ts").write_text("export const revision = 2;", encoding="utf-8")
        return result

    cache.runner = changing_runner
    refreshed = cache.render_ready(job(), tmp_path, beats, render_all=True)

    assert len([call for call in runner.calls if "remotion" in call]) == 1
    assert refreshed["ready_chunks"] == 0
    assert all(chunk["status"] == "pending" for chunk in refreshed["chunks"])


def test_finalize_uses_cached_chunks_and_skips_recombine_when_unchanged(tmp_path: Path, monkeypatch):
    beats = write_project_files(tmp_path, beat_count=7, beat_seconds=10)
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    write_progress(tmp_path, [f"B{index:03d}" for index in range(1, 8)], total=7, status="completed")
    monkeypatch.setenv("COFI_NODE_BIN", "node")

    first = cache.finalize(job(), tmp_path, beats)
    assert first["render_mode"] == "background_chunk_cache"
    assert first["cached_chunks"] == 3
    assert Path(first["video_path"]).exists()
    assert len([call for call in runner.calls if "remotion" in call]) == 3
    assert len([call for call in runner.calls if "remotion" not in call]) == 1

    second = cache.finalize(job(), tmp_path, beats)
    assert second["cache_signature"] == first["cache_signature"]
    assert len([call for call in runner.calls if "remotion" not in call]) == 1


def test_finalize_recombines_legacy_output_that_has_no_validation_marker(tmp_path: Path, monkeypatch):
    beats = write_project_files(tmp_path, beat_count=7, beat_seconds=10)
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    write_progress(tmp_path, [f"B{index:03d}" for index in range(1, 8)], total=7, status="completed")
    monkeypatch.setenv("COFI_NODE_BIN", "node")

    cache.finalize(job(), tmp_path, beats)
    manifest_path = tmp_path / "render_cache_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("finalized_validation_version", None)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    cache.finalize(job(), tmp_path, beats)

    assert len([call for call in runner.calls if "remotion" not in call]) == 2


def test_audio_sync_fix_invalidates_pre_alignment_outputs():
    assert BackgroundRenderCache.FINAL_VALIDATION_VERSION >= 5


def test_background_watcher_renders_while_edit_progress_advances(tmp_path: Path):
    beats = write_project_files(tmp_path, beat_count=7, beat_seconds=10)
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    write_progress(tmp_path, [], total=7)

    assert cache.start(job(), tmp_path, beats) is True
    write_progress(tmp_path, ["B001", "B002", "B003"], total=7)
    deadline = time.time() + 2
    while time.time() < deadline:
        status = cache.status(tmp_path) or {}
        if status.get("ready_chunks") == 1:
            break
        time.sleep(0.02)
    assert (cache.status(tmp_path) or {}).get("ready_chunks") == 1

    write_progress(tmp_path, [f"B{index:03d}" for index in range(1, 8)], total=7, status="completed")
    deadline = time.time() + 2
    while time.time() < deadline:
        status = cache.status(tmp_path) or {}
        if status.get("ready_chunks") == 3:
            break
        time.sleep(0.02)
    assert (cache.status(tmp_path) or {}).get("ready_chunks") == 3


def test_hardware_auto_tuning_and_single_pass_export_defaults(tmp_path: Path):
    beats = write_project_files(tmp_path, beat_count=12, beat_seconds=10)
    runner = FakeRenderRunner()
    remotion_dir = tmp_path / "CofiRemotion"
    (remotion_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (remotion_dir / "src").mkdir(parents=True, exist_ok=True)
    (remotion_dir / "src" / "index.ts").write_text("export {};", encoding="utf-8")
    (remotion_dir / "scripts" / "combine-cofi-cache.mjs").write_text("// fake", encoding="utf-8")
    cache = BackgroundRenderCache(remotion_dir, runner=runner)
    cache._npx = lambda: "npx"  # type: ignore[method-assign]

    assert cache.render_during_edit is False
    assert cache.chunk_seconds == 10800
    assert cache.hardware_profile["export_concurrency"] >= 2
    assert cache.hardware_profile["x264_preset"] in {"fast", "veryfast"}

    # A 120s project fits inside a single pass and is not rendered until export (render_all=True)
    prepared = cache.prepare(job(), tmp_path, beats)
    assert prepared["total_chunks"] == 1
    assert prepared["ready_chunks"] == 0
    assert prepared["render_during_edit"] is False
    assert runner.calls == []

    exported = cache.render_ready(job(), tmp_path, beats, render_all=True)
    assert exported["ready_chunks"] == 1
    render_calls = [call for call in runner.calls if "remotion" in call]
    assert len(render_calls) == 1
    cmd = render_calls[0]
    assert any(arg.startswith("--x264-preset=") for arg in cmd)
    assert "--bundle-cache" in cmd
    assert any(arg.startswith("--concurrency=") for arg in cmd)
    assert any(arg.startswith("--offthreadvideo-video-threads=") for arg in cmd)
    assert any(arg.startswith("--gl=") for arg in cmd)
    assert any(arg.startswith("--hardware-acceleration=") for arg in cmd)


def test_subbeat_timings_use_explicit_start_end_and_avoid_frame_mismatch(tmp_path: Path):
    beats = [
        {"beat_id": "B001-V01", "start_sec": 0.0, "end_sec": 12.5, "target_duration_sec": 20.0},
        {"beat_id": "B001-V02", "start_sec": 12.5, "end_sec": 25.0, "target_duration_sec": 20.0},
    ]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    (tmp_path / "voice_manifest.json").write_text(
        json.dumps({"beats": [{"beat_id": "B001", "start_sec": 0.0, "end_sec": 25.0, "duration_sec": 25.0}]}),
        encoding="utf-8",
    )
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    prepared = cache.prepare(job(), tmp_path, beats)
    assert abs(prepared["duration_seconds"] - 25.0) < 0.01
    assert prepared["duration_in_frames"] == 750


def test_completed_chunk_on_disk_is_recovered_without_rerender(tmp_path: Path):
    beats = write_project_files(tmp_path, beat_count=3, beat_seconds=10)
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    prepared = cache.prepare(job(), tmp_path, beats)
    chunk = prepared["chunks"][0]
    video = Path(chunk["video_path"])
    audio = Path(chunk["audio_path"])
    log = Path(chunk["log_path"])
    video.parent.mkdir(parents=True, exist_ok=True)
    audio.parent.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"rendered-mp4-bytes")
    audio.write_bytes(b"rendered-aac-bytes")
    log.write_text("Rendered 900/900\nEncoded 900/900\n", encoding="utf-8")

    # Even if manifest had status="rendering" from an interrupted session, prepare/status/render_ready recovers it
    manifest_path = tmp_path / "render_cache_manifest.json"
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw["chunks"][0]["status"] = "rendering"
    manifest_path.write_text(json.dumps(raw), encoding="utf-8")

    status = cache.status(tmp_path)
    assert status is not None
    assert status["ready_chunks"] == 1
    assert status["status"] == "ready"

    rendered = cache.render_ready(job(), tmp_path, beats, render_all=True)
    assert rendered["ready_chunks"] == 1
    assert runner.calls == []


def test_live_hardware_governor_reserves_cpu_ram_and_vram_headroom():
    from documentary.render_cache import detect_hardware_profile

    hw = detect_hardware_profile(force_refresh=True)
    assert hw["logical_cores"] >= 1
    assert hw["reserved_ui_threads"] >= 1
    assert 1 <= hw["still_concurrency"] <= 6
    assert 1 <= hw["nvenc_concurrency"] <= 6
    assert 1 <= hw["ffmpeg_threads"] <= 4
    assert 2 <= hw["edit_worker_concurrency"] <= 4
    assert 1 <= hw["edit_ffmpeg_threads"] <= 3
    assert "foreground_gpu_active" in hw
    assert hw["governor_mode"] in {"eco_smooth", "balanced_smooth", "turbo_max"}
    assert "CPU trống" in hw["summary"]
    assert "RAM trống" in hw["summary"]


def test_smart_edit_vram_governor_yields_to_foreground_games(monkeypatch):
    import documentary.render_cache as rc

    monkeypatch.setattr(rc, "_detect_foreground_gpu_workload", lambda: ["League of Legends.exe"])
    monkeypatch.setattr(
        rc,
        "_detect_nvidia_gpu_telemetry",
        lambda: {"busy_pct": 42.0, "vram_free_mb": 2600, "vram_total_mb": 8188, "temp_c": 61},
    )
    hw = rc.detect_hardware_profile(force_refresh=True)
    assert hw["foreground_gpu_active"] is True
    assert hw["governor_mode"] == "eco_smooth"
    assert hw["edit_worker_concurrency"] == 2
    assert hw["edit_ffmpeg_threads"] == 2
    assert hw["prefer_edit_hwaccel"] is False
    assert hw["nvenc_concurrency"] == 1
    contract = rc.format_smart_hardware_contract("edit")
    assert "max_workers=2" in contract
    assert "-threads 2" in contract


def test_selective_beat_edit_preserves_unedited_chunks_even_when_remotion_source_changes(tmp_path: Path):
    beats = write_project_files(tmp_path, beat_count=7, beat_seconds=10)
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    write_progress(tmp_path, [f"B{index:03d}" for index in range(1, 8)], total=7, status="completed")
    ready = cache.render_ready(job(), tmp_path, beats, render_all=True)
    assert ready["ready_chunks"] == 3
    assert len([call for call in runner.calls if "remotion" in call]) == 3

    # Simulate edit_chat modifying Remotion source for beat B004 and calling selective invalidate
    source = cache.remotion_dir / "src" / "index.ts"
    source.write_text("export const editedBeat = 'B004';", encoding="utf-8")
    invalidated = cache.invalidate(tmp_path, beat_id="B004")
    assert invalidated == [2]

    manifest_after_inv = json.loads((tmp_path / "render_cache_manifest.json").read_text(encoding="utf-8"))
    assert manifest_after_inv["selective_invalidation"] is True
    assert manifest_after_inv["dirty_beat_ids"] == ["B004"]
    assert [c["status"] for c in manifest_after_inv["chunks"]] == ["ready", "pending", "ready"]

    # Re-exporting must ONLY re-render chunk 2 (frames 900-1799), not chunks 1 or 3
    re_rendered = cache.render_ready(job(), tmp_path, beats, render_all=True)
    assert re_rendered["ready_chunks"] == 3
    render_calls = [call for call in runner.calls if "remotion" in call]
    assert len(render_calls) == 4
    assert "--frames=900-1799" in render_calls[-1]


def test_auto_beat_diff_invalidates_only_modified_beat_chunk(tmp_path: Path):
    beats = write_project_files(tmp_path, beat_count=7, beat_seconds=10)
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    write_progress(tmp_path, [f"B{index:03d}" for index in range(1, 8)], total=7, status="completed")
    ready = cache.render_ready(job(), tmp_path, beats, render_all=True)
    assert ready["ready_chunks"] == 3

    # Modify only beat B007 in visual_manifest.json and call invalidate() without arguments
    beats[-1]["visual_note"] = "Updated graphic overlay for B007"
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")

    invalidated = cache.invalidate(tmp_path)
    assert invalidated == [3]
    manifest = json.loads((tmp_path / "render_cache_manifest.json").read_text(encoding="utf-8"))
    assert manifest["dirty_beat_ids"] == ["B007"]
    assert [c["status"] for c in manifest["chunks"]] == ["ready", "ready", "pending"]

    re_rendered = cache.render_ready(job(), tmp_path, beats, render_all=True)
    assert re_rendered["ready_chunks"] == 3
    render_calls = [call for call in runner.calls if "remotion" in call]
    assert len(render_calls) == 4
    assert "--frames=1800-2099" in render_calls[-1]





def test_sculpted_voice_manifest_and_edit_manifest_prevent_outro_clipping_on_subbeats(tmp_path: Path):
    """Regression: when voice_manifest has B001..B002 sculpted to 1642.07s (49263f) while
    visual_manifest still holds pre-sculpted B001-V01..B002-V01 (1621.218s), render_cache must
    map via parent_beat_id and honor voice_manifest + edit_manifest so the outro is never clipped."""
    beats = [
        {"beat_id": "B001-V01", "parent_beat_id": "B001", "start_sec": 0.0, "end_sec": 800.0},
        {"beat_id": "B002-V01", "parent_beat_id": "B002", "start_sec": 800.0, "end_sec": 1621.218},
    ]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    (tmp_path / "voice_manifest.json").write_text(
        json.dumps({
            "duration_sec": 1642.07,
            "beats": [
                {"beat_id": "B001", "start_sec": 1.2, "end_sec": 810.0, "visual_open_sec": 0.0, "visual_close_sec": 810.0},
                {"beat_id": "B002", "start_sec": 810.0, "end_sec": 1642.071, "visual_open_sec": 810.0, "visual_close_sec": 1642.071},
            ],
        }),
        encoding="utf-8",
    )
    (tmp_path / "edit_manifest.json").write_text(
        json.dumps({"duration_in_frames": 49263, "duration_sec": 1642.07}),
        encoding="utf-8",
    )
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    prepared = cache.prepare(job(), tmp_path, beats)
    assert prepared["duration_in_frames"] == 49263
    assert abs(prepared["duration_seconds"] - 1642.1) < 0.1


def test_outro_speech_tail_guard_and_desktop_gpu_not_falsely_throttled(tmp_path: Path, monkeypatch):
    import documentary.render_cache as rc

    monkeypatch.setattr(rc, "_detect_foreground_gpu_workload", lambda: [])
    monkeypatch.setattr(
        rc,
        "_detect_nvidia_gpu_telemetry",
        lambda: {"busy_pct": 38.0, "vram_free_mb": 4600, "vram_total_mb": 8188, "temp_c": 55},
    )
    hw = rc.detect_hardware_profile(force_refresh=True)
    assert hw["foreground_gpu_active"] is False
    assert hw["still_concurrency"] >= 3
    assert hw["nvenc_concurrency"] >= 5

    beats = [{"beat_id": "B001", "start_sec": 0.0, "end_sec": 100.0}]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    (tmp_path / "voice_manifest.json").write_text(
        json.dumps({
            "duration_sec": 100.5,
            "beats": [{"beat_id": "B001", "start_sec": 0.0, "end_sec": 100.5, "speech_end_sec": 100.2}],
        }),
        encoding="utf-8",
    )
    runner = FakeRenderRunner()
    cache = make_cache(tmp_path, runner)
    prepared = cache.prepare(job(), tmp_path, beats)
    # Must guarantee >= 100.2 + 3.8 = 104.0s (3120 frames @ 30fps) so closing speech + BGM fade tail are never clipped
    assert prepared["duration_in_frames"] >= 3120

