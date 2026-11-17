import json
from pathlib import Path

from documentary.codex_gateway import StageResult
from documentary.edit import EditCoordinator
from documentary.remotion import RemotionManager


class FakeGateway:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.prompts = []
        self.reset_calls = []

    def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False):
        self.prompts.append(prompt)
        if self.results:
            return self.results.pop(0)
        return StageResult(0, "ok", Path(workspace) / ".producer" / label)

    def reset_reusable_session(self, workspace, label, reason="manual_reset"):
        self.reset_calls.append((label, reason))
        return True


def write_visual_manifest(workspace: Path, count: int) -> None:
    beats = [
        {
            "beat_id": f"B{index + 1:03d}",
            "narration_text": f"Beat {index + 1}",
            "target_duration_sec": 5,
        }
        for index in range(count)
    ]
    (workspace / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")


def make_coordinator(
    tmp_path: Path,
    gateway: FakeGateway,
    *,
    batch_size=4,
    batch_max_duration_sec=90,
    batch_retries=2,
) -> EditCoordinator:
    remotion_dir = tmp_path / "CofiRemotion"
    manager = RemotionManager(remotion_dir)
    return EditCoordinator(
        gateway,
        manager,
        remotion_dir,
        batch_size=batch_size,
        batch_max_duration_sec=batch_max_duration_sec,
        batch_retries=batch_retries,
    )


def test_edit_splits_ten_beats_into_four_four_two_and_checkpoints(tmp_path: Path):
    write_visual_manifest(tmp_path, 10)
    gateway = FakeGateway()
    coordinator = make_coordinator(tmp_path, gateway, batch_size=4)

    result = coordinator.run({"id": "job-1", "title": "Demo"}, tmp_path)

    progress = json.loads((tmp_path / "edit_progress.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert len(gateway.prompts) == 3
    assert '"B001"' in gateway.prompts[0] and '"B004"' in gateway.prompts[0]
    assert '"B005"' in gateway.prompts[1] and '"B008"' in gateway.prompts[1]
    assert '"B009"' in gateway.prompts[2] and '"B010"' in gateway.prompts[2]
    assert progress["completed_beats"] == 10
    assert progress["pending_beat_ids"] == []
    assert progress["status"] == "completed"
    assert (tmp_path / "edit_checkpoint.json").exists()
    assert (tmp_path / "remotion_media_manifest.json").exists()
    assert gateway.reset_calls == []
    assert progress["session_rotations"] == 0


def test_edit_rerun_skips_batches_already_checkpointed(tmp_path: Path):
    write_visual_manifest(tmp_path, 10)
    first_gateway = FakeGateway([
        StageResult(0, "one", tmp_path / "one"),
        StageResult(0, "two", tmp_path / "two"),
        StageResult(1, "validation error", tmp_path / "three"),
    ])
    first = make_coordinator(tmp_path, first_gateway, batch_size=4, batch_retries=0)

    failed = first.run({"id": "job-1", "title": "Demo"}, tmp_path)
    mid = json.loads((tmp_path / "edit_progress.json").read_text(encoding="utf-8"))

    assert failed.returncode == 1
    assert mid["completed_beats"] == 8
    assert mid["pending_beat_ids"] == ["B009", "B010"]

    second_gateway = FakeGateway()
    second = make_coordinator(tmp_path, second_gateway, batch_size=4, batch_retries=0)
    resumed = second.run({"id": "job-1", "title": "Demo"}, tmp_path)

    final = json.loads((tmp_path / "edit_progress.json").read_text(encoding="utf-8"))
    assert resumed.returncode == 0
    assert len(second_gateway.prompts) == 1
    assert '"B009"' in second_gateway.prompts[0] and '"B010"' in second_gateway.prompts[0]
    assert 'Edit ONLY these beat IDs:\n["B009", "B010"]' in second_gateway.prompts[0]
    assert 'Already completed in earlier batches:\n["B001", "B002", "B003", "B004", "B005", "B006", "B007", "B008"]' in second_gateway.prompts[0]
    assert final["completed_beats"] == 10


def test_edit_transient_disconnect_retries_same_batch_in_same_session(tmp_path: Path):
    write_visual_manifest(tmp_path, 4)
    gateway = FakeGateway([
        StageResult(0, "first done", tmp_path / "one"),
        StageResult(1, "connection reset by peer", tmp_path / "two"),
        StageResult(0, "second recovered", tmp_path / "three"),
    ])
    coordinator = make_coordinator(tmp_path, gateway, batch_size=2, batch_retries=1)

    result = coordinator.run({"id": "job-1", "title": "Demo"}, tmp_path)

    progress = json.loads((tmp_path / "edit_progress.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert len(gateway.prompts) == 3
    assert '"B003"' in gateway.prompts[1] and '"B004"' in gateway.prompts[1]
    assert '"B003"' in gateway.prompts[2] and '"B004"' in gateway.prompts[2]
    assert gateway.reset_calls == []
    assert progress["session_rotations"] == 0
    assert progress["completed_beats"] == 4


def test_edit_caps_batch_by_duration_and_keeps_resume_to_pending_beats(tmp_path: Path):
    beats = [
        {"beat_id": f"B{index:03d}", "narration_text": f"Beat {index}", "target_duration_sec": 40}
        for index in range(1, 6)
    ]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    (tmp_path / "edit_progress.json").write_text(
        json.dumps(
            {
                "version": 1,
                "assigned_beat_ids": [f"B{index:03d}" for index in range(1, 6)],
                "completed_beat_ids": ["B001", "B002", "B003"],
                "attempts": 1,
                "session_rotations": 0,
            }
        ),
        encoding="utf-8",
    )
    gateway = FakeGateway()
    coordinator = make_coordinator(
        tmp_path,
        gateway,
        batch_size=4,
        batch_max_duration_sec=90,
        batch_retries=0,
    )

    result = coordinator.run({"id": "job-1", "title": "Demo"}, tmp_path)

    assert result.returncode == 0
    assert len(gateway.prompts) == 2
    assert 'Edit ONLY these beat IDs:\n["B004"]' in gateway.prompts[0]
    assert 'Edit ONLY these beat IDs:\n["B005"]' in gateway.prompts[1]


def test_edit_default_runs_long_form_in_one_continuous_context(tmp_path: Path):
    beats = [
        {
            "beat_id": f"B{index:03d}",
            "narration_text": f"Beat {index}",
            "target_duration_sec": 10,
        }
        for index in range(1, 181)
    ]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    gateway = FakeGateway()
    remotion_dir = tmp_path / "CofiRemotion"
    coordinator = EditCoordinator(
        gateway,
        RemotionManager(remotion_dir),
        remotion_dir,
        batch_retries=0,
    )

    result = coordinator.run({"id": "job-1", "title": "30 minute demo"}, tmp_path)

    progress = json.loads((tmp_path / "edit_progress.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert len(gateway.prompts) == 1
    assert progress["batch_target_duration_sec"] == 0
    assert progress["batch_max_duration_sec"] == 0
    assert progress["total_batches"] == 1
    assert '"B001"' in gateway.prompts[0] and '"B180"' in gateway.prompts[0]


def test_edit_default_keeps_a_five_minute_project_in_one_context(tmp_path: Path):
    beats = [
        {
            "beat_id": f"B{index:03d}",
            "narration_text": f"Beat {index}",
            "target_duration_sec": 8,
        }
        for index in range(1, 37)
    ]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    gateway = FakeGateway()
    remotion_dir = tmp_path / "CofiRemotion"
    coordinator = EditCoordinator(
        gateway,
        RemotionManager(remotion_dir),
        remotion_dir,
        batch_retries=0,
    )

    result = coordinator.run({"id": "job-1", "title": "5 minute demo"}, tmp_path)

    assert result.returncode == 0
    assert len(gateway.prompts) == 1
    assert '"B001"' in gateway.prompts[0] and '"B036"' in gateway.prompts[0]


def test_edit_default_has_no_duration_cutoff(tmp_path: Path):
    beats = [
        {"beat_id": "B001", "narration_text": "A", "target_duration_sec": 145},
        {"beat_id": "B002", "narration_text": "B", "target_duration_sec": 145},
        {"beat_id": "B003", "narration_text": "C", "target_duration_sec": 30},
    ]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    gateway = FakeGateway()
    remotion_dir = tmp_path / "CofiRemotion"
    coordinator = EditCoordinator(
        gateway,
        RemotionManager(remotion_dir),
        remotion_dir,
        batch_retries=0,
    )

    result = coordinator.run({"id": "job-1", "title": "Soft five minute target"}, tmp_path)

    assert result.returncode == 0
    assert len(gateway.prompts) == 1
    assert 'Edit ONLY these beat IDs:\n["B001", "B002", "B003"]' in gateway.prompts[0]


def test_edit_disconnect_reloads_per_beat_progress_before_retry(tmp_path: Path):
    write_visual_manifest(tmp_path, 4)

    class ProgressingGateway(FakeGateway):
        def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False):
            self.prompts.append(prompt)
            if len(self.prompts) == 1:
                progress_path = Path(workspace) / "edit_progress.json"
                progress = json.loads(progress_path.read_text(encoding="utf-8"))
                progress["completed_beat_ids"] = ["B001", "B002"]
                progress["pending_beat_ids"] = ["B003", "B004"]
                progress["completed_beats"] = 2
                progress_path.write_text(json.dumps(progress), encoding="utf-8")
                return StageResult(1, "connection reset by peer", Path(workspace) / ".producer" / label)
            return StageResult(0, "recovered", Path(workspace) / ".producer" / label)

    gateway = ProgressingGateway()
    remotion_dir = tmp_path / "CofiRemotion"
    coordinator = EditCoordinator(
        gateway,
        RemotionManager(remotion_dir),
        remotion_dir,
        batch_retries=1,
    )

    result = coordinator.run({"id": "job-1", "title": "Continuous resume"}, tmp_path)

    progress = json.loads((tmp_path / "edit_progress.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert len(gateway.prompts) == 2
    assert 'Edit ONLY these beat IDs:\n["B001", "B002", "B003", "B004"]' in gateway.prompts[0]
    assert "After EACH beat is fully finished" in gateway.prompts[0]
    assert 'Edit ONLY these beat IDs:\n["B003", "B004"]' in gateway.prompts[1]
    assert 'Already completed in earlier batches:\n["B001", "B002"]' in gateway.prompts[1]
    assert progress["completed_beats"] == 4
    assert progress["pending_beat_ids"] == []


def test_footage_batch_manifest_slices_commits_and_builds_contact_sheet(tmp_path: Path, monkeypatch):
    from PIL import Image
    from documentary.edit_footage_fetcher import EditDirectFootageFetcher, _ytdlp_format_selector

    assert "height<=720" in _ytdlp_format_selector()
    monkeypatch.setenv("COFI_FOOTAGE_MAX_HEIGHT", "1080")
    assert "height<=1080" in _ytdlp_format_selector()
    monkeypatch.delenv("COFI_FOOTAGE_MAX_HEIGHT", raising=False)

    remotion_dir = tmp_path / "CofiRemotion"
    (remotion_dir / "public" / "jobs" / "job-batch" / "footage").mkdir(parents=True, exist_ok=True)
    ws = tmp_path / "ws"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "visual_manifest.json").write_text(
        json.dumps(
            {
                "beats": [
                    {"id": "B001", "voice_text": "첫 번째 장면 테스트"},
                    {"id": "B002", "voice_text": "두 번째 장면 테스트"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    fetcher = EditDirectFootageFetcher(ws, remotion_dir, job_id="job-batch")

    def fake_slice(self, url, output_stem, **kwargs):
        out = self.media_dir / f"{output_stem}.mp4"
        out.write_bytes(b"0" * 16384)
        sheet = self.media_dir / f"{output_stem}_3frames.jpg"
        Image.new("RGB", (480, 90), (40, 80, 120)).save(sheet)
        return out

    monkeypatch.setattr(EditDirectFootageFetcher, "download_and_slice_clip", fake_slice)
    monkeypatch.setattr("documentary.edit_footage_fetcher.measure_clip_signalstats", lambda p: {"yavg": 110.0, "motion": 5.0})

    res = fetcher.fetch_batch_manifest(
        "job-batch",
        [
            {
                "beat_id": "B001",
                "url": "src01.mp4",
                "start_offset": 12.5,
                "duration": 5.0,
                "crop_mode": "crop=1140:640:60:40",
                "observed_content": "Two boys walking outside Pingyu netcafe entrance at dusk",
            },
            {
                "beat_id": "B002",
                "url": "src01.mp4",
                "start_offset": 44.0,
                "duration": 5.0,
                "crop_mode": "crop=1140:640:60:40",
                "observed_content": "Police cruiser parked outside rural brick farmhouse courtyard",
            },
            {
                "beat_id": "B003",
                "url": "src01.mp4",
                "start_offset": -1,
                "crop_mode": "none",
                "observed_content": "bad",
            },
        ],
    )

    assert res["sliced_count"] == 2
    assert res["rejected_count"] == 1
    assert res["sliced_beats"] == ["B001", "B002"]
    sheet_path = ws / res["batch_verify_sheet"]
    assert sheet_path.is_file()
    reg = json.loads((ws / "asset_registry.json").read_text(encoding="utf-8"))
    assert {a["beat_id"] for a in reg["assets"]} == {"B001", "B002"}
    rev = json.loads((ws / "footage_review.json").read_text(encoding="utf-8"))
    assert {c["beat_id"] for c in rev["selected_candidates"]} == {"B001", "B002"}


def test_dedicated_footage_eye_runs_parallel_act_workers_and_skips_completed(tmp_path: Path, monkeypatch):
    remotion_dir = tmp_path / "CofiRemotion"
    ws = tmp_path / "ws"
    (ws / "media" / "edit_footage").mkdir(parents=True, exist_ok=True)
    (ws / "media" / "footage" / "sources").mkdir(parents=True, exist_ok=True)
    (ws / "media" / "footage" / "sources" / "src_clean_01.mp4").write_bytes(b"0" * 150_000)

    # Mark B001 as already eye-verified on disk
    (ws / "media" / "edit_footage" / "edit_broll_B001.mp4").write_bytes(b"0" * 16384)
    (ws / "asset_registry.json").write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "id": "edit_broll_B001",
                        "beat_id": "B001",
                        "kind": "sourced_video",
                        "path": "media/edit_footage/edit_broll_B001.mp4",
                        "eye_verified": True,
                        "observed_content": "Already verified entrance clip for B001",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    beats = []
    for i in range(1, 21):
        act = "ACT01" if i <= 7 else ("ACT02" if i <= 14 else "ACT03")
        beats.append({"id": f"B{i:03d}", "act": act, "voice_text": f"Sentence {i}", "duration_sec": 5.0})

    calls: list[tuple[str, str]] = []

    class ParallelFootageGateway:
        def available(self) -> bool:
            return True

        def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False):
            calls.append((label, prompt))
            return StageResult(0, f"done {label}", Path(workspace) / ".producer" / label)

    monkeypatch.setattr("documentary.critic_loops.is_live_critic_gateway_available", lambda gw: True)
    audit_calls = {"n": 0}

    def fake_audit(workspace, job):
        audit_calls["n"] += 1
        return {"status": "FAILED" if audit_calls["n"] == 1 else "PASSED", "assets_inspected": 20, "failures": []}

    monkeypatch.setattr("documentary.critic_loops.audit_footage_hygiene", fake_audit)
    monkeypatch.setattr(
        "documentary.edit_footage_fetcher.EditDirectFootageFetcher.build_verify_ftg_clips_sheets",
        lambda self, job: {"ok": True},
    )

    coordinator = EditCoordinator(ParallelFootageGateway(), RemotionManager(remotion_dir), remotion_dir)
    res = coordinator._run_dedicated_footage_eye_agent({"id": "job-par"}, ws, beats)

    assert res is not None and res.returncode == 0
    labels = {lbl for lbl, _ in calls}
    assert labels == {"footage_eye_act01", "footage_eye_act02", "footage_eye_act03"}
    for lbl, prompt in calls:
        assert "src_clean_01.mp4" in prompt
        assert "--batch-manifest" in prompt
        if lbl == "footage_eye_act01":
            assert '"beat_id": "B001"' not in prompt
            assert '"beat_id": "B002"' in prompt


def test_dedicated_footage_eye_filters_non_footage_routes_and_focuses_rework(tmp_path: Path, monkeypatch):
    remotion_dir = tmp_path / "CofiRemotion"
    ws = tmp_path / "ws"
    (ws / "media" / "edit_footage").mkdir(parents=True, exist_ok=True)
    (ws / "media" / "footage" / "sources").mkdir(parents=True, exist_ok=True)

    # 8 REAL_FTG beats (6 completed >= 50%, 1 failed, 1 intentionally skipped for fallback)
    # + VOX_NEWSROOM, CINEMA_TEXT, AI_4D beats that must NEVER be passed to @footage.
    beats = []
    assets = []
    for i in range(1, 9):
        bid = f"B{i:03d}-V01"
        beats.append({
            "beat_id": bid,
            "act": "ACT01" if i <= 4 else "ACT02",
            "route": "REAL_FTG",
            "visual_route": "footage",
            "visual_type": "sourced_video",
            "voice_text": f"Real footage line {i}",
            "duration_sec": 4.5,
        })
        if i <= 6:
            clip_p = ws / "media" / "edit_footage" / f"{bid}_edit_broll.mp4"
            clip_p.write_bytes(b"0" * 16384)
            assets.append({
                "beat_id": bid,
                "path": f"media/edit_footage/{bid}_edit_broll.mp4",
                "source_video": "src42_bad.mp4" if i == 2 else "src01_clean.mp4",
                "eye_verified": True,
                "observed_content": f"Observed clean frame {i} for documentary",
            })

    beats.extend([
        {"beat_id": "B090-V01", "act": "ACT01", "route": "VOX_NEWSROOM", "visual_route": "vox", "visual_type": "vox", "voice_text": "Vox line", "duration_sec": 5.0},
        {"beat_id": "B091-V01", "act": "ACT01", "route": "CINEMA_TEXT", "visual_route": "footage", "visual_type": "cinema_text", "voice_text": "Text beat", "duration_sec": 3.5},
        {"beat_id": "B092-V01", "act": "ACT02", "route": "AI_4D", "visual_route": "footage", "visual_type": "sourced_video", "voice_text": "AI line", "duration_sec": 5.0},
    ])
    (ws / "asset_registry.json").write_text(json.dumps({"assets": assets}), encoding="utf-8")

    calls: list[tuple[str, str]] = []

    class FocusedReworkGateway:
        def available(self) -> bool:
            return True

        def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False):
            calls.append((label, prompt))
            return StageResult(0, f"done {label}", Path(workspace) / ".producer" / label)

    monkeypatch.setattr("documentary.critic_loops.is_live_critic_gateway_available", lambda gw: True)
    audit_calls = {"n": 0}

    def fake_audit(workspace, job):
        audit_calls["n"] += 1
        if audit_calls["n"] <= 2:
            return {
                "status": "NEEDS_ATTENTION",
                "assets_inspected": 6,
                "failures": [
                    {"beat_id": "B003-V01", "reason": "internal_hard_cut_detected"},
                    {"beat_id": "GLOBAL_FOOTAGE", "reason": "progressive_monotonic_slicing_detected on src42_bad.mp4"},
                ],
            }
        return {"status": "PASSED", "assets_inspected": 6, "failures": []}

    monkeypatch.setattr("documentary.critic_loops.audit_footage_hygiene", fake_audit)
    monkeypatch.setattr(
        "documentary.edit_footage_fetcher.EditDirectFootageFetcher.build_verify_ftg_clips_sheets",
        lambda self, job: {"ok": True},
    )

    coordinator = EditCoordinator(FocusedReworkGateway(), RemotionManager(remotion_dir), remotion_dir)
    res = coordinator._run_dedicated_footage_eye_agent({"id": "job-focused"}, ws, beats)

    assert res is not None and res.returncode == 0
    labels = [lbl for lbl, _ in calls]
    assert labels == ["footage_eye", "footage_eye_rework"]
    for _, prompt in calls:
        assert "B090-V01" not in prompt
        assert "B091-V01" not in prompt
        assert "B092-V01" not in prompt
    rework_prompt = calls[1][1]
    assert "B002-V01" in rework_prompt  # from flagged GLOBAL_FOOTAGE source src42_bad.mp4
    assert "B003-V01" in rework_prompt  # explicit beat failure
    assert "B008-V01" not in rework_prompt  # intentionally skipped beat is NOT re-dumped into rework


def test_dedicated_footage_eye_parallelizes_large_rework(tmp_path: Path, monkeypatch):
    remotion_dir = tmp_path / "CofiRemotion"
    ws = tmp_path / "ws"
    (ws / "media" / "edit_footage").mkdir(parents=True, exist_ok=True)
    (ws / "media" / "footage" / "sources").mkdir(parents=True, exist_ok=True)

    beats = []
    failures = []
    for i in range(1, 21):
        bid = f"B{i:03d}-V01"
        beats.append({
            "beat_id": bid,
            "act": "ACT01" if i <= 10 else "ACT02",
            "route": "REAL_FTG",
            "visual_type": "sourced_video",
            "voice_text": f"Sentence {i}",
            "duration_sec": 4.0,
        })
        failures.append({"beat_id": bid, "reason": "unverified_blind_auto_cut"})

    calls: list[str] = []

    class ParallelReworkGateway:
        def available(self) -> bool:
            return True

        def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False):
            calls.append(label)
            return StageResult(0, f"done {label}", Path(workspace) / ".producer" / label)

    monkeypatch.setattr("documentary.critic_loops.is_live_critic_gateway_available", lambda gw: True)
    audit_calls = {"n": 0}

    def fake_audit(workspace, job):
        audit_calls["n"] += 1
        if audit_calls["n"] <= 2:
            return {"status": "NEEDS_ATTENTION", "assets_inspected": 20, "failures": failures}
        return {"status": "PASSED", "assets_inspected": 20, "failures": []}

    monkeypatch.setattr("documentary.critic_loops.audit_footage_hygiene", fake_audit)
    monkeypatch.setattr(
        "documentary.edit_footage_fetcher.EditDirectFootageFetcher.build_verify_ftg_clips_sheets",
        lambda self, job: {"ok": True},
    )

    coordinator = EditCoordinator(ParallelReworkGateway(), RemotionManager(remotion_dir), remotion_dir)
    res = coordinator._run_dedicated_footage_eye_agent({"id": "job-par-rw"}, ws, beats)

    assert res is not None and res.returncode == 0
    assert "footage_eye_rework_act01" in calls
    assert "footage_eye_rework_act02" in calls
    assert "footage_eye_rework" not in calls
