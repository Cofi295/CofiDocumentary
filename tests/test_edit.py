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
