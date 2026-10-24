import threading
import time
from pathlib import Path

from COFI_BRAIN.chat_run_manager import ChatRunManager
from COFI_BRAIN import chat_run_manager


def test_chat_run_events_are_durable_and_replay_after_sequence(tmp_path: Path):
    manager = ChatRunManager(tmp_path / "chat_runs")
    run = manager.create({"message": "fix it", "selected_job_id": "job-1"}, "codex")

    first = manager.append_event(run["id"], {"type": "stage", "stage": "chatting"})
    second = manager.append_event(run["id"], {"type": "cli_event", "message": "reading app.py"})

    assert first["seq"] == 1
    assert second["seq"] == 2
    reloaded = ChatRunManager(tmp_path / "chat_runs", recover=False)
    assert [event["seq"] for event in reloaded.events(run["id"], after=1)] == [2]
    assert reloaded.get(run["id"])["provider"] == "codex"


def test_run_state_survives_transient_windows_replace_denial(tmp_path: Path, monkeypatch):
    manager = ChatRunManager(tmp_path / "chat_runs")
    run = manager.create({"message": "hello"}, "gemini")
    original_replace = chat_run_manager.os.replace
    attempts = 0

    def intermittently_locked(source, target):
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise PermissionError(5, "Access is denied", str(target))
        return original_replace(source, target)

    monkeypatch.setattr(chat_run_manager.os, "replace", intermittently_locked)
    monkeypatch.setattr(chat_run_manager.time, "sleep", lambda _: None)
    event = manager.append_event(run["id"], {"type": "cli_event", "line": "working"})

    assert attempts == 3
    assert manager.get(run["id"])["last_seq"] == event["seq"] == 1


def test_chat_run_stays_active_until_worker_returns_terminal_result(tmp_path: Path):
    manager = ChatRunManager(tmp_path / "chat_runs")
    entered = threading.Event()
    release = threading.Event()

    def worker(run, emit, cancel_event):
        emit({"type": "stage", "stage": "repairing", "message": "editing"})
        entered.set()
        release.wait(timeout=2)
        return {"reply": "done", "history": []}

    run = manager.start({"message": "fix"}, "gemini", worker)
    assert entered.wait(timeout=1)
    assert manager.get(run["id"])["status"] == "running"
    release.set()
    terminal = manager.wait(run["id"], timeout=2)

    assert terminal["status"] == "succeeded"
    assert terminal["result"]["reply"] == "done"
    assert manager.events(run["id"])[-1]["type"] == "result"


def test_cancel_is_visible_to_worker_and_finishes_cancelled(tmp_path: Path):
    manager = ChatRunManager(tmp_path / "chat_runs")
    entered = threading.Event()

    def worker(run, emit, cancel_event):
        entered.set()
        while not cancel_event.wait(0.01):
            pass
        return {"reply": "should not be published"}

    run = manager.start({"message": "long task"}, "codex", worker)
    assert entered.wait(timeout=1)
    manager.cancel(run["id"])
    terminal = manager.wait(run["id"], timeout=2)

    assert terminal["status"] == "cancelled"
    assert terminal["result"] is None
    assert manager.events(run["id"])[-1]["type"] == "cancelled"


def test_terminal_status_is_not_published_before_final_event(tmp_path: Path, monkeypatch):
    manager = ChatRunManager(tmp_path / "chat_runs")
    final_event_entered = threading.Event()
    release_final_event = threading.Event()
    original_append = manager.append_event

    def delayed_append(run_id, event):
        if event.get("type") == "result":
            final_event_entered.set()
            release_final_event.wait(timeout=2)
        return original_append(run_id, event)

    monkeypatch.setattr(manager, "append_event", delayed_append)
    run = manager.start({"message": "finish"}, "codex", lambda *_: {"reply": "done"})

    assert final_event_entered.wait(timeout=1)
    assert manager.get(run["id"])["status"] == "running"
    release_final_event.set()
    assert manager.wait(run["id"], timeout=2)["status"] == "succeeded"


def test_latest_active_run_can_be_discovered_by_project_scope(tmp_path: Path):
    manager = ChatRunManager(tmp_path / "chat_runs")
    first = manager.create({"message": "old", "selected_job_id": "job-a"}, "codex")
    manager._update(first["id"], status="failed")
    active = manager.create({"message": "current", "selected_job_id": "job-a"}, "gemini")
    manager.create({"message": "other", "selected_job_id": "job-b"}, "codex")

    found = manager.latest_active(selected_job_id="job-a")

    assert found["id"] == active["id"]
    assert found["provider"] == "gemini"
