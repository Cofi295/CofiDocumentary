from pathlib import Path

import json
import os
import threading
import pytest

from documentary.codex_gateway import CodexGateway, StageResult
from documentary.gemini_gateway import GeminiGateway
from documentary.prompts import build_edit_batch_prompt, build_edit_chat_prompt, build_phase_prompt


@pytest.fixture(autouse=True)
def disable_web_turn_gap_by_default(monkeypatch):
    monkeypatch.setenv("COFI_CODEX_MIN_TURN_GAP_SEC", "0")


def shared_session_meta(root: Path) -> Path:
    return root / ".producer" / CodexGateway.SHARED_SESSION_LABEL


def test_gateway_keeps_user_model_and_uses_no_retry_bridge_provider(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_CODEX_BASE_URL", "http://127.0.0.1:17841/v1")
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")

    command = gateway.command_for("plan", tmp_path / "job")
    text = " ".join(command)

    assert "exec" in command
    assert "--json" in command
    assert "--search" in command
    assert "--model" not in command
    assert "--ignore-user-config" not in command
    assert 'model_provider="cofi_chatgpt_web"' in text
    assert "http://127.0.0.1:17841/v1" in text


def test_search_flag_is_global_and_precedes_exec(tmp_path: Path):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")

    command = gateway.command_for("plan", tmp_path / "job")

    assert command[0:2] == ["codex", "--search"]
    assert command.index("exec") > command.index("--search")


def test_gateway_disables_codex_transport_retries_for_new_and_resumed_commands(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_CODEX_BASE_URL", "http://127.0.0.1:17841/v1")
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")

    command = gateway.command_for("plan", tmp_path / "job")
    resume = gateway._resume_command(tmp_path / "job", "thread-1", tmp_path / "last.txt", False)

    for candidate in (command, resume):
        text = " ".join(candidate)
        assert "model_providers.openai." not in text
        assert "model_providers.cofi_chatgpt_web=" in text
        assert "request_max_retries=0" in text
        assert "stream_max_retries=0" in text
        assert "requires_openai_auth=true" in text


def test_gateway_extracts_terminal_error_message_from_jsonl():
    output = '\n'.join([
        '{"type":"thread.started","thread_id":"thread-1"}',
        '{"type":"turn.failed","error":{"message":"Too many requests: thao tác quá nhanh"}}',
    ])

    assert CodexGateway._terminal_error_message(output) == "Too many requests: thao tác quá nhanh"


def test_edit_gateway_uses_remotion_as_root_and_job_as_additional_dir(tmp_path: Path):
    remotion = tmp_path / "CofiRemotion"
    workspace = tmp_path / "job"
    gateway = CodexGateway(remotion_dir=remotion, executable="codex")

    command = gateway.command_for("edit", workspace)

    assert command[command.index("-C") + 1] == str(remotion)
    assert command[command.index("--add-dir") + 1] == str(workspace)


def test_gateway_attaches_images_to_new_and_resumed_chat_commands(tmp_path: Path):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    first = tmp_path / "first.png"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"png")
    second.write_bytes(b"jpg")

    command = gateway.command_for("plan", tmp_path / "job", image_paths=[first, second])
    resume = gateway._resume_command(
        tmp_path / "job",
        "thread-1",
        tmp_path / "last.txt",
        False,
        image_paths=[first],
    )

    assert command.count("-i") == 2
    assert str(first.resolve()) in command
    assert str(second.resolve()) in command
    assert "resume" in resume
    assert "-i" in resume
    assert str(first.resolve()) in resume


def test_gateway_prepends_bundled_media_tools_to_worker_environment(tmp_path: Path):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")

    env = gateway._subprocess_env()

    assert env["PATH"].split(os.pathsep)[0] == str(gateway.tools_dir)
    assert env["COFI_YTDLP_BIN"] == str(gateway.tools_dir / "yt-dlp.exe")
    assert env["COFI_FFMPEG_BIN"] == str(gateway.tools_dir / "ffmpeg.exe")
    assert env["COFI_FFPROBE_BIN"] == str(gateway.tools_dir / "ffprobe.exe")
    assert env["COFI_NODE_BIN"] == str(gateway.tools_dir / "node.exe")


def test_edit_chat_prompt_requires_absolute_tool_paths_before_reporting_missing_access(tmp_path: Path):
    workspace = tmp_path / "workspace"
    remotion = tmp_path / "CofiRemotion"

    prompt = build_edit_chat_prompt(
        {"id": "job-1", "title": "Demo"},
        workspace,
        remotion,
        "kiểm tra project",
    )

    assert "Local workspace and command tools are attached with write access" in prompt
    assert "exact absolute workspace or CofiRemotion path" in prompt


def test_codex_gateway_does_not_expose_footage_source_api_keys(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_SOURCE_BRAVE_API_KEY", "brave-secret")
    monkeypatch.setenv("COFI_SOURCE_EUROPEANA_API_KEY", "eu-secret")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "legacy-brave-secret")
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")

    env = gateway._subprocess_env()

    assert "COFI_SOURCE_BRAVE_API_KEY" not in env
    assert "COFI_SOURCE_EUROPEANA_API_KEY" not in env
    assert "BRAVE_SEARCH_API_KEY" not in env


def test_gemini_gateway_hides_source_keys_but_keeps_gemini_auth(monkeypatch):
    monkeypatch.setenv("COFI_SOURCE_NARA_API_KEY", "nara-secret")
    monkeypatch.setenv("NARA_API_KEY", "legacy-nara-secret")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    gateway = GeminiGateway(executable="gemini")

    env = gateway._subprocess_env()

    assert "COFI_SOURCE_NARA_API_KEY" not in env
    assert "NARA_API_KEY" not in env
    assert env["GEMINI_API_KEY"] == "gemini-secret"


def test_reusable_chat_resumes_same_codex_session(tmp_path: Path, monkeypatch):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    calls = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append(thread_id)
        active = thread_id or "thread-1"
        return StageResult(0, "ok", log_path), active, ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    gateway.run_prompt_reusable("first", tmp_path, "producer_chat")
    gateway.run_prompt_reusable("second", tmp_path, "producer_chat")

    session = json.loads((shared_session_meta(tmp_path) / "session.json").read_text(encoding="utf-8"))
    assert calls == [None, "thread-1"]
    assert session["thread_id"] == "thread-1"
    assert session["turn_count"] == 2


def test_reusable_chat_retries_same_thread_once_after_transient_stream_disconnect(tmp_path: Path, monkeypatch):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    meta = shared_session_meta(tmp_path)
    meta.mkdir(parents=True)
    (meta / "session.json").write_text(
        json.dumps({"thread_id": "thread-old", "turn_count": 4, "prompt_chars_total": 12000}),
        encoding="utf-8",
    )
    calls = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append(thread_id)
        if len(calls) == 1:
            return StageResult(1, "stream disconnected before completion", log_path), thread_id, ""
        return StageResult(0, "continued", log_path), thread_id, ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    result = gateway.run_prompt_reusable("continue batch", tmp_path, "footage_codex")

    session = json.loads((meta / "session.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert calls == ["thread-old", "thread-old"]
    assert session["thread_id"] == "thread-old"
    assert session["turn_count"] == 5
    assert not (meta / "retired_sessions.jsonl").exists()


def test_reusable_chat_preserves_new_thread_id_when_first_stream_disconnects(tmp_path: Path, monkeypatch):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    calls = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append(thread_id)
        if len(calls) == 1:
            return StageResult(1, "connection reset by peer", log_path), "thread-new", ""
        return StageResult(0, "continued", log_path), thread_id, ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    result = gateway.run_prompt_reusable("first batch", tmp_path, "footage_codex")

    session = json.loads((shared_session_meta(tmp_path) / "session.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert calls == [None, "thread-new"]
    assert session["thread_id"] == "thread-new"
    assert session["turn_count"] == 1


def test_reusable_chat_retries_windows_process_init_crash_on_same_thread(tmp_path: Path, monkeypatch):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    meta = shared_session_meta(tmp_path)
    meta.mkdir(parents=True)
    (meta / "session.json").write_text(
        json.dumps({"thread_id": "thread-old", "turn_count": 4, "prompt_chars_total": 12000}),
        encoding="utf-8",
    )
    calls = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append(thread_id)
        if len(calls) == 1:
            return StageResult(3221225794, "", log_path), thread_id, ""
        return StageResult(0, "continued", log_path), thread_id or "thread-fresh", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    result = gateway.run_prompt_reusable("continue batch", tmp_path, "footage_codex")

    assert result.returncode == 0
    assert calls == ["thread-old", "thread-old"]
    assert json.loads((meta / "session.json").read_text(encoding="utf-8"))["thread_id"] == "thread-old"
    assert not (meta / "retired_sessions.jsonl").exists()


def test_reusable_chat_retires_resume_session_when_bridge_loses_trusted_cwd(tmp_path: Path, monkeypatch):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    meta = shared_session_meta(tmp_path)
    meta.mkdir(parents=True)
    (meta / "session.json").write_text(
        json.dumps({"thread_id": "thread-stale", "turn_count": 4, "prompt_chars_total": 12000}),
        encoding="utf-8",
    )
    calls = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append(thread_id)
        if thread_id == "thread-stale":
            message = "stream disconnected before completion: ChatGPT web turn is missing cwd in trusted Codex environment context"
            return StageResult(1, message, log_path), thread_id, message
        return StageResult(0, "continued", log_path), "thread-fresh", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    result = gateway.run_prompt_reusable("continue batch", tmp_path, "footage_codex")

    session = json.loads((meta / "session.json").read_text(encoding="utf-8"))
    retired = [json.loads(line) for line in (meta / "retired_sessions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert result.returncode == 0
    assert calls == ["thread-stale", None]
    assert session["thread_id"] == "thread-fresh"
    assert retired[-1]["thread_id"] == "thread-stale"
    assert retired[-1]["reason"] == "broken_resume_environment_context"


def test_reusable_chat_retires_missing_rollout_session_and_restarts_fresh(tmp_path: Path, monkeypatch):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    meta = shared_session_meta(tmp_path)
    meta.mkdir(parents=True)
    (meta / "session.json").write_text(
        json.dumps({"thread_id": "thread-from-previous-account", "turn_count": 2, "prompt_chars_total": 35000}),
        encoding="utf-8",
    )
    calls = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append(thread_id)
        if thread_id == "thread-from-previous-account":
            message = "thread/resume failed: no rollout found for thread id thread-from-previous-account (code -32600)"
            return StageResult(1, message, log_path), thread_id, message
        return StageResult(0, "continued", log_path), "thread-current-account", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    result = gateway.run_prompt_reusable("continue edit", tmp_path, "edit_chat")

    session = json.loads((meta / "session.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert calls == ["thread-from-previous-account", None]
    assert session["thread_id"] == "thread-current-account"


def test_reusable_chat_rotates_session_when_codex_account_changes(tmp_path: Path, monkeypatch):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    meta = shared_session_meta(tmp_path)
    meta.mkdir(parents=True)
    (meta / "session.json").write_text(
        json.dumps({
            "thread_id": "thread-old-account",
            "turn_count": 2,
            "prompt_chars_total": 35000,
            "auth_fingerprint": "old-account",
        }),
        encoding="utf-8",
    )
    calls = []

    monkeypatch.setattr(gateway, "_codex_auth_fingerprint", lambda: "current-account", raising=False)

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append(thread_id)
        return StageResult(0, "continued", log_path), "thread-current-account", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    result = gateway.run_prompt_reusable("continue edit", tmp_path, "edit_chat")

    session = json.loads((meta / "session.json").read_text(encoding="utf-8"))
    retired = [json.loads(line) for line in (meta / "retired_sessions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert result.returncode == 0
    assert calls == [None]
    assert session["thread_id"] == "thread-current-account"
    assert session["auth_fingerprint"] == "current-account"
    assert retired[-1]["thread_id"] == "thread-old-account"
    assert retired[-1]["reason"] == "codex_account_changed"


def test_reusable_chat_proactively_rotates_before_safe_turn_limit(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_CODEX_SESSION_MAX_TURNS", "3")
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    meta = shared_session_meta(tmp_path)
    meta.mkdir(parents=True)
    (meta / "session.json").write_text(
        json.dumps({"thread_id": "thread-near-limit", "turn_count": 3, "prompt_chars_total": 90000}),
        encoding="utf-8",
    )
    calls = []

    prompts = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append(thread_id)
        prompts.append(prompt)
        if thread_id == "thread-near-limit":
            return StageResult(0, "Đã xong B001-B008; tiếp theo làm B009.", log_path), thread_id, ""
        return StageResult(0, "fresh", log_path), "thread-fresh", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    result = gateway.run_prompt_reusable("next batch", tmp_path, "footage_codex")

    session = json.loads((meta / "session.json").read_text(encoding="utf-8"))
    retired = [json.loads(line) for line in (meta / "retired_sessions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert result.returncode == 0
    assert calls == ["thread-near-limit", None]
    assert "Đã xong B001-B008; tiếp theo làm B009." in prompts[-1]
    assert session["thread_id"] == "thread-fresh"
    assert session["turn_count"] == 1
    assert retired[-1]["thread_id"] == "thread-near-limit"
    assert retired[-1]["reason"] == "proactive_context_guard"


def test_reusable_chat_reuses_one_shared_thread_across_labels(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_CODEX_MIN_TURN_GAP_SEC", "0")
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    calls = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append((thread_id, prompt))
        return StageResult(0, "ok", log_path), thread_id or "thread-shared", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    first = gateway.run_prompt_reusable("chat first", tmp_path, "producer_chat")
    second = gateway.run_prompt_reusable("footage next", tmp_path, "footage_codex")
    third = gateway.run_prompt_reusable("chat again", tmp_path, "producer_chat")

    assert first.returncode == second.returncode == third.returncode == 0
    assert [item[0] for item in calls] == [None, "thread-shared", "thread-shared"]
    assert not (tmp_path / ".producer" / "producer_chat" / "handoff_summary.txt").exists()
    assert not (tmp_path / ".producer" / "footage_codex" / "handoff_summary.txt").exists()


def test_reusable_chat_reuses_one_shared_thread_across_workspaces(tmp_path: Path, monkeypatch):
    gateway = CodexGateway(
        remotion_dir=tmp_path / "CofiRemotion",
        executable="codex",
        session_root=tmp_path,
    )
    job_workspace = tmp_path / "workspaces" / "job-1"
    calls = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append((Path(workspace), thread_id))
        return StageResult(0, "ok", log_path), thread_id or "thread-shared", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    gateway.run_prompt_reusable("producer", tmp_path, "producer_chat_global")
    gateway.run_prompt_reusable("footage", job_workspace, "footage_codex")
    gateway.run_prompt_reusable("edit", job_workspace, "edit", use_remotion_root=True)

    assert [thread_id for _workspace, thread_id in calls] == [None, "thread-shared", "thread-shared"]
    session = json.loads((shared_session_meta(tmp_path) / "session.json").read_text(encoding="utf-8"))
    assert session["thread_id"] == "thread-shared"
    assert session["turn_count"] == 3
    assert session["last_label"] == "edit"


def test_reusable_chat_migrates_latest_legacy_session_once_and_cannot_resurrect_old_threads(tmp_path: Path, monkeypatch):
    root_meta = tmp_path / ".producer" / "producer_chat_global"
    job_meta = tmp_path / "workspaces" / "job-1" / ".producer" / "edit"
    root_meta.mkdir(parents=True)
    job_meta.mkdir(parents=True)
    (root_meta / "session.json").write_text(json.dumps({
        "thread_id": "thread-older",
        "last_used_at": "2026-09-09T10:00:00+00:00",
        "turn_count": 2,
    }), encoding="utf-8")
    (job_meta / "session.json").write_text(json.dumps({
        "thread_id": "thread-latest",
        "last_used_at": "2026-09-09T11:00:00+00:00",
        "turn_count": 5,
    }), encoding="utf-8")

    gateway = CodexGateway(
        remotion_dir=tmp_path / "CofiRemotion",
        executable="codex",
        session_root=tmp_path,
    )
    calls = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append(thread_id)
        return StageResult(0, "ok", log_path), thread_id or "thread-new", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    gateway.run_prompt_reusable("continue", tmp_path, "producer_chat_global")
    assert calls == ["thread-latest"]
    assert not (root_meta / "session.json").exists()
    assert not (job_meta / "session.json").exists()
    assert (shared_session_meta(tmp_path) / "legacy_sessions.jsonl").exists()

    assert gateway.reset_reusable_session(tmp_path, "producer_chat_global", reason="test_rotation") is True
    gateway.run_prompt_reusable("fresh after reset", tmp_path, "producer_chat_global")
    assert calls == ["thread-latest", None]


def test_reusable_chat_serializes_concurrent_sends_for_same_session(tmp_path: Path, monkeypatch):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    first_entered = threading.Event()
    release_first = threading.Event()
    second_entered = threading.Event()
    calls = []
    calls_lock = threading.Lock()

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        with calls_lock:
            calls.append(thread_id)
            call_number = len(calls)
        if call_number == 1:
            first_entered.set()
            assert release_first.wait(timeout=2)
            return StageResult(0, "first", log_path), "thread-1", ""
        second_entered.set()
        return StageResult(0, "second", log_path), thread_id or "thread-2", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)
    first = threading.Thread(target=gateway.run_prompt_reusable, args=("first", tmp_path, "producer_chat"))
    second = threading.Thread(target=gateway.run_prompt_reusable, args=("second", tmp_path, "producer_chat"))

    first.start()
    assert first_entered.wait(timeout=2)
    second.start()
    assert second_entered.wait(timeout=0.2) is False
    release_first.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert calls == [None, "thread-1"]


def test_gateway_queues_chatgpt_web_turns_across_different_sessions(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_CODEX_MIN_TURN_GAP_SEC", "0")
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    first_entered = threading.Event()
    release_first = threading.Event()
    second_entered = threading.Event()

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        if not first_entered.is_set():
            first_entered.set()
            assert release_first.wait(timeout=2)
        else:
            second_entered.set()
        return StageResult(0, "ok", log_path), thread_id or "thread-new", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)
    first = threading.Thread(target=gateway.run_prompt, args=("first", tmp_path, "producer_chat"))
    second = threading.Thread(target=gateway.run_prompt, args=("second", tmp_path, "footage_codex"))

    first.start()
    assert first_entered.wait(timeout=2)
    second.start()
    assert second_entered.wait(timeout=0.2) is False
    release_first.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert second_entered.is_set()


def test_gateway_waits_between_consecutive_chatgpt_web_turns(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_CODEX_MIN_TURN_GAP_SEC", "15")
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    gateway._last_web_turn_finished_at = 100.0
    sleeps = []
    clock = iter((106.0, 121.0))

    monkeypatch.setattr("documentary.codex_gateway.time.monotonic", lambda: next(clock))
    monkeypatch.setattr("documentary.codex_gateway.time.sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(
        gateway,
        "_execute_prompt",
        lambda prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log: (
            StageResult(0, "ok", log_path),
            "thread-new",
            "",
        ),
    )

    result = gateway.run_prompt("next", tmp_path, "footage_codex")

    assert result.returncode == 0
    assert sleeps == [9.0]
    assert gateway._last_web_turn_finished_at == 121.0


def test_reusable_chat_rotates_only_after_context_limit(tmp_path: Path, monkeypatch):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    meta = shared_session_meta(tmp_path)
    meta.mkdir(parents=True)
    (meta / "session.json").write_text(json.dumps({"thread_id": "thread-old", "turn_count": 8}), encoding="utf-8")
    calls = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log):
        calls.append(thread_id)
        if thread_id == "thread-old":
            return StageResult(1, "", log_path), thread_id, "maximum context window reached"
        return StageResult(0, "continued", log_path), "thread-new", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)

    result = gateway.run_prompt_reusable("continue", tmp_path, "edit_chat", use_remotion_root=True)

    session = json.loads((meta / "session.json").read_text(encoding="utf-8"))
    retired = [json.loads(line) for line in (meta / "retired_sessions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert result.returncode == 0
    assert calls == ["thread-old", None]
    assert session["thread_id"] == "thread-new"
    assert retired[-1]["thread_id"] == "thread-old"
    assert retired[-1]["reason"] == "context_limit"


def test_reusable_chat_rotates_after_encoded_request_body_limit(tmp_path: Path, monkeypatch):
    gateway = CodexGateway(tmp_path)
    calls: list[str | None] = []

    def fake_execute(prompt, workspace, log_path, last_path, log_callback, use_remotion_root, thread_id, append_log, image_paths=None):
        calls.append(thread_id)
        if thread_id:
            message = '{"error":{"message":"Encoded request body exceeds 67108864 bytes","code":"invalid_request_error"}}'
            return StageResult(1, message, log_path), thread_id, message
        return StageResult(0, "fresh session ok", log_path), "fresh-thread", ""

    monkeypatch.setattr(gateway, "_execute_prompt", fake_execute)
    meta = shared_session_meta(tmp_path)
    meta.mkdir(parents=True)
    (meta / "session.json").write_text(json.dumps({"thread_id": "bloated-thread", "turn_count": 9}), encoding="utf-8")

    result = gateway.run_prompt_reusable("continue", tmp_path, "edit_chat", use_remotion_root=True)

    assert result.returncode == 0
    assert calls == ["bloated-thread", None]
    retired = [json.loads(line) for line in (meta / "retired_sessions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert retired[-1]["reason"] == "context_limit"


def test_reset_reusable_session_retires_active_thread(tmp_path: Path):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    meta = shared_session_meta(tmp_path)
    meta.mkdir(parents=True)
    (meta / "session.json").write_text(json.dumps({"thread_id": "thread-footage", "turn_count": 3}), encoding="utf-8")

    changed = gateway.reset_reusable_session(tmp_path, "footage_codex", reason="transient_footage_failure")

    retired = [json.loads(line) for line in (meta / "retired_sessions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert changed is True
    assert not (meta / "session.json").exists()
    assert retired[-1]["thread_id"] == "thread-footage"
    assert retired[-1]["reason"] == "transient_footage_failure"


def test_gateway_redacts_large_binary_payload_from_persistent_event_line(tmp_path: Path):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")
    event = {
        "type": "item.completed",
        "item": {
            "result": {
                "content": [
                    {"type": "image", "data": "A" * 12000, "mimeType": "image/png"},
                    {"type": "text", "data": "small-value"},
                ]
            }
        },
    }

    sanitized = gateway._sanitize_event_line(json.dumps(event) + "\n")
    payload = json.loads(sanitized)
    image_data = payload["item"]["result"]["content"][0]["data"]
    text_data = payload["item"]["result"]["content"][1]["data"]

    assert image_data == "<redacted binary payload: 12000 chars>"
    assert text_data == "small-value"
    assert len(sanitized) < 2000


def test_footage_prompt_requires_actual_visual_inspection(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job1", "title": "Flood analysis", "language": "ko", "production_recipe": {}},
        "footage",
        tmp_path,
        tmp_path / "CofiRemotion",
    )

    lower = prompt.lower()
    assert "metadata alone" in lower
    assert "visually inspect" in lower
    assert "accept" in lower and "reject" in lower
    assert "footage_review.json" in prompt


def test_plan_prompt_uses_duration_scaled_soft_narration_range(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job1", "title": "Short report", "language": "vi", "production_recipe": {"target_duration_sec": 120}},
        "plan",
        tmp_path,
        tmp_path / "CofiRemotion",
    )

    assert "about 240-330 spoken words" in prompt
    assert "planning estimate, not an exact runtime lock" in prompt
    assert "8500 and 11000 characters" not in prompt


def test_plan_prompt_encodes_human_intrigue_documentary_narrative_dna(tmp_path: Path):
    prompt = build_phase_prompt(
        {
            "id": "job1",
            "title": "A first-family marriage story",
            "language": "en",
            "market": "US",
            "production_recipe": {"target_duration_sec": 1800},
        },
        "plan",
        tmp_path,
        tmp_path / "CofiRemotion",
    ).lower()

    assert "third-person documentary narration" in prompt
    assert "sparse direct-address pivots" in prompt
    assert "cold open" in prompt and "concrete scene" in prompt
    assert "contradiction or reversal" in prompt
    assert "human relationship mystery" in prompt
    assert "betrayal" in prompt and "secret romance" in prompt
    assert "institutional history" in prompt and "subordinate" in prompt
    assert "reopen curiosity gaps" in prompt
    assert "consequence or reversal" in prompt
    assert "story_group" in prompt


def test_profile_editorial_dna_drives_plan_footage_and_edit_prompts(tmp_path: Path):
    job = {
        "id": "job-profile",
        "title": "A first-family relationship story",
        "language": "en",
        "market": "US",
        "production_recipe": {"target_duration_sec": 1800},
        "channel_profile_snapshot": {
            "id": "channel-us",
            "label": "US secrets",
            "editorial_dna": {
                "narrative": {
                    "hook": "concrete scene, then contradiction/reversal",
                    "section_rhythm": "evidence -> implication -> complication -> reveal",
                },
                "footage": {
                    "priority": "archival evidence first",
                    "typical_shot_seconds": [4, 8],
                    "rules": [
                        "Match footage to the named person, event, document, place, and period.",
                        "Reuse authentic archival material contextually instead of forcing one new asset per sentence.",
                        "Use documents, photographs, headlines and archival clips as evidence at the narration moment they matter.",
                    ],
                    "avoid": ["generic unrelated stock", "slideshow pacing"],
                },
            },
        },
    }

    plan = build_phase_prompt(job, "plan", tmp_path, tmp_path / "CofiRemotion").lower()
    footage = build_phase_prompt(job, "footage", tmp_path, tmp_path / "CofiRemotion").lower()
    edit = build_phase_prompt(job, "edit", tmp_path, tmp_path / "CofiRemotion").lower()

    for prompt in (plan, footage, edit):
        assert "profile-specific editorial dna" in prompt
        assert "archival evidence first" in prompt
        assert "generic unrelated stock" in prompt
    assert "named person, event, document, place, and period" in plan
    assert "reuse authentic archival material contextually" in footage
    assert "documents, photographs, headlines and archival clips" in edit


def test_qc_prompt_requires_official_remotion_skills_and_real_render_inspection(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job1", "title": "Flood analysis", "language": "ko", "production_recipe": {}},
        "qc",
        tmp_path,
        tmp_path / "CofiRemotion",
    )

    lower = prompt.lower()
    assert "official remotion agent skills" in lower
    assert "remotion-dev/skills" in lower
    assert "remotion-render" in lower
    assert "cofi-video-director" not in lower
    assert "actual rendered" in prompt.lower()
    assert "final_manifest.json" in prompt


def test_edit_prompt_defaults_to_premium_cinematic_motion_studio(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job1", "title": "Flood analysis", "language": "ko", "production_recipe": {}},
        "edit",
        tmp_path,
        tmp_path / "CofiRemotion",
    )

    lower = prompt.lower()
    assert "premium cinematic editing direction" in lower
    assert "production director plus a senior editor" in lower
    assert "second-by-second editorial responsibility" in lower
    assert "does not mean adding an effect every second" in lower
    assert "frame-level polish" in lower and "sequence-level rhythm" in lower
    assert "authored motion-design" in lower
    assert "2.5d" in lower and "true 3d" in lower
    assert "typography and subtitles as editorial design" in lower
    assert "design sound with picture" in lower
    assert "restrained presentation effects" not in lower
    assert "asset variety and intentional reuse" in lower
    assert "prefer unused or less-used valid assets" in lower
    assert "do not force every downloaded/approved asset" in lower
    assert "native motion semantic coverage" in lower
    assert "meaningful clauses" in lower
    assert "generic native graphic" in lower


def test_edit_prompt_requires_official_remotion_agent_skills(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job1", "title": "Flood analysis", "language": "ko", "production_recipe": {}},
        "edit",
        tmp_path,
        tmp_path / "CofiRemotion",
    ).lower()

    assert "official remotion agent skills" in prompt
    assert "remotion-dev/skills" in prompt
    assert "remotion-best-practices" in prompt
    assert "remotion-markup" in prompt
    assert "remotion-docs" in prompt
    assert "do not invent remotion apis" in prompt


def test_edit_chat_and_batch_inherit_premium_editorial_direction(tmp_path: Path):
    job = {"id": "job1", "title": "Flood analysis", "language": "ko", "production_recipe": {}}
    remotion_dir = tmp_path / "CofiRemotion"
    chat = build_edit_chat_prompt(job, tmp_path, remotion_dir, "làm cảnh này điện ảnh hơn")
    batch = build_edit_batch_prompt(job, tmp_path, remotion_dir, [{"beat_id": "B001"}])

    for prompt in (chat, batch):
        lower = prompt.lower()
        assert "premium cinematic editing direction" in lower
        assert "project-specific visual system" in lower
        assert "plain static default captions" in lower
        assert "restrained presentation effects" not in lower


def test_qc_prompt_flags_template_like_primary_treatments(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job1", "title": "Flood analysis", "language": "ko", "production_recipe": {}},
        "qc",
        tmp_path,
        tmp_path / "CofiRemotion",
    ).lower()

    assert "repeated line/circle/callout" in prompt
    assert "plain default captions" in prompt
    assert "review the attention curve second by second" in prompt
    assert "flat 20-30 second runs" in prompt
    assert "quality defects" in prompt
    assert "exact same file, crop, or source time range" in prompt
    assert "deliberate callback" in prompt
    assert "native motion semantic coverage" in prompt
    assert "self-check each native beat" in prompt


def test_prompt_is_owned_by_documentary_tool(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job1", "title": "Flood analysis", "language": "ko", "production_recipe": {}},
        "plan",
        tmp_path,
        tmp_path / "CofiRemotion",
    )
    assert "COFI DOCUMENTARY" in prompt
    assert "COFI PRODUCER" not in prompt


def test_plan_prompt_forbids_interactive_software_workflows(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job1", "title": "Flood analysis", "language": "ko", "production_recipe": {}},
        "plan",
        tmp_path,
        tmp_path / "CofiRemotion",
    )
    lower = prompt.lower()
    assert "do not ask the user for approval" in lower
    assert "do not invoke brainstorming" in lower
    assert "writing-plans" in lower


def test_plan_prompt_forbids_stdin_waiting_shell_writes_on_windows(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job1", "title": "Flood analysis", "language": "ko", "production_recipe": {}},
        "plan",
        tmp_path,
        tmp_path / "CofiRemotion",
    ).lower()

    assert "never start `python -`" in prompt
    assert "waiting for stdin" in prompt
    assert "bounded chunks" in prompt
    assert "set-content" in prompt and "add-content" in prompt


def test_plan_prompt_requires_visual_manifest_with_stable_beat_ids(tmp_path: Path):
    prompt = build_phase_prompt(
        {"id": "job1", "title": "Flood analysis", "language": "ko", "production_recipe": {}},
        "plan",
        tmp_path,
        tmp_path / "CofiRemotion",
    )
    lower = prompt.lower()
    assert "visual_manifest.json" in prompt
    assert "beat_id" in lower
    assert "stable" in lower
    assert "5-8" in lower
    assert "short and dense" in lower
    assert "more varied footage" in lower


def test_gemini_gateway_uses_headless_stream_json_and_workspace(tmp_path: Path):
    gateway = GeminiGateway(executable="gemini")
    command = gateway.command_for(tmp_path)
    assert Path(command[0]).stem.lower() == "gemini"
    assert "--output-format" in command
    assert "stream-json" in command
    assert "--approval-mode" in command
    assert "yolo" in command


def test_gemini_gateway_plan_availability_does_not_require_cli(monkeypatch):
    gateway = GeminiGateway(executable="definitely-missing-gemini-cli")
    monkeypatch.setattr(gateway, "web2api_status", lambda timeout=0.35: {"ok": True})

    assert gateway.available is False
    assert gateway.plan_available is True


def test_gemini_gateway_plan_availability_falls_back_to_antigravity(monkeypatch, tmp_path: Path):
    agy = tmp_path / "agy.exe"
    agy.write_text("stub", encoding="utf-8")
    gateway = GeminiGateway(executable="gemini", antigravity_executable=str(agy))
    monkeypatch.setattr(gateway, "web2api_status", lambda timeout=0.35: {"ok": False})
    monkeypatch.setattr(
        gateway,
        "_antigravity_auth_status",
        lambda: {"ready": True, "auth_method": "antigravity-cli", "action": ""},
    )

    assert gateway.plan_available is True


def test_gemini_gateway_routes_plan_directly_through_web2api(monkeypatch, tmp_path: Path):
    gateway = GeminiGateway(executable="definitely-missing-gemini-cli")
    monkeypatch.setenv("COFI_GEMINI_WEB2API_URL", "http://127.0.0.1:18081")
    monkeypatch.setenv("COFI_GEMINI_WEB2API_MODEL", "gemini-test-thinking")
    monkeypatch.setattr(gateway, "web2api_status", lambda timeout=0.35: {"ok": True})
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "research_md": "# Research\nEvidence and sources",
                            "script_md": "Finished narration.",
                            "visual_manifest": {
                                "target_duration_sec": 300,
                                "beats": [{
                                    "beat_id": "B001",
                                    "narration_text": "Finished narration.",
                                    "purpose": "hook",
                                    "target_duration_sec": 6,
                                    "visual_type": "sourced_video",
                                    "source_priority": "prefer_real",
                                    "visual_description": "Relevant real footage",
                                    "footage_search_queries": ["relevant footage"],
                                    "factual_source_refs": [],
                                    "framing_motion_intent": "slow push",
                                    "on_screen_text": "",
                                    "sound_notes": "",
                                }],
                            },
                        })
                    }
                }]
            }

    def fake_post(url, json=None, timeout=None):
        captured.update({"url": url, "payload": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("documentary.gemini_gateway.requests.post", fake_post)
    monkeypatch.setattr(gateway, "run_prompt", lambda *args, **kwargs: pytest.fail("PLAN must not invoke Gemini CLI"))

    result = gateway.run(
        {"title": "Test", "topic": "Test", "market": "US", "language": "en"},
        "plan",
        tmp_path,
    )

    assert result.returncode == 0
    assert captured["url"] == "http://127.0.0.1:18081/v1/chat/completions"
    assert captured["payload"]["model"] == "gemini-test-thinking"
    assert (tmp_path / "research.md").read_text(encoding="utf-8").startswith("# Research")
    assert (tmp_path / "script.md").read_text(encoding="utf-8").startswith("Finished narration")
    manifest = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["beats"][0]["beat_id"] == "B001"


def test_gemini_gateway_prefers_cli_over_web2api_for_plan(monkeypatch, tmp_path: Path):
    gateway = GeminiGateway(executable="gemini")
    monkeypatch.setattr(gateway, "web2api_status", lambda timeout=0.35: {"ok": True})
    web2api_called = []
    monkeypatch.setattr(gateway, "run_plan_web2api", lambda *args, **kwargs: web2api_called.append(True))
    monkeypatch.setattr(gateway, "auth_status", lambda: {"ready": True, "auth_method": "antigravity-cli", "action": ""})
    captured = {}

    def fake_run_prompt(prompt, workspace, phase, log_callback=None):
        captured.update({"prompt": prompt, "workspace": workspace, "phase": phase})
        return StageResult(returncode=0, last_message="CLI completed", log_path=workspace / "events.jsonl")

    monkeypatch.setattr(gateway, "run_prompt", fake_run_prompt)

    result = gateway.run(
        {"title": "Test", "topic": "Test", "market": "US", "language": "en"},
        "plan",
        tmp_path,
    )

    assert result.returncode == 0
    assert result.last_message == "CLI completed"
    assert captured["phase"] == "plan"
    assert not web2api_called, "Gemini CLI must be preferred over web2api by default"


def test_gemini_gateway_plan_falls_back_to_web2api_when_cli_unavailable(monkeypatch, tmp_path: Path):
    gateway = GeminiGateway(executable="definitely-missing-gemini-cli")
    monkeypatch.setattr(gateway, "web2api_status", lambda timeout=0.35: {"ok": True})
    monkeypatch.setattr(gateway, "auth_status", lambda: {"ready": False, "auth_method": "antigravity-cli", "action": ""})
    web2api_called = []

    def fake_run_plan_web2api(job, workspace, log_callback=None):
        web2api_called.append(True)
        return StageResult(returncode=0, last_message="web2api completed", log_path=workspace / "events.jsonl")

    monkeypatch.setattr(gateway, "run_plan_web2api", fake_run_plan_web2api)

    result = gateway.run(
        {"title": "Test", "topic": "Test", "market": "US", "language": "en"},
        "plan",
        tmp_path,
    )

    assert result.returncode == 0
    assert result.last_message == "web2api completed"
    assert web2api_called == [True]


def test_gemini_gateway_command_accepts_explicit_model(tmp_path: Path):
    gateway = GeminiGateway(executable="gemini")
    command = gateway.command_for(tmp_path, model="gemini-test")
    assert "-m" in command
    assert command[command.index("-m") + 1] == "gemini-test"


def test_gemini_auth_status_detects_api_key_without_returning_secret(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret-value")
    gateway = GeminiGateway(executable="gemini")

    status = gateway.auth_status()

    assert status["ready"] is True
    assert status["auth_method"] == "gemini-api-key"
    assert "test-secret-value" not in str(status)


def test_gemini_auth_status_marks_personal_oauth_as_unsupported(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_GCA", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    settings = tmp_path / ".gemini" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text('{"security":{"auth":{"selectedType":"oauth-personal"}}}', encoding="utf-8")
    gateway = GeminiGateway(executable="gemini")

    status = gateway.auth_status()

    assert status["ready"] is False
    assert status["reason_code"] == "UNSUPPORTED_CLIENT"
    assert "Antigravity" in str(status["action"])


def test_gemini_gateway_prefers_authenticated_antigravity(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_GCA", raising=False)
    agy = tmp_path / "agy.exe"
    agy.write_text("stub", encoding="utf-8")

    class ProbeResult:
        returncode = 0
        stdout = "gemini-3.1-pro-high\tGemini 3.1 Pro (High)\n"
        stderr = ""

    def fake_run(command, **kwargs):
        assert command == [str(agy), "models"]
        return ProbeResult()

    monkeypatch.setattr("documentary.gemini_gateway.subprocess.run", fake_run)
    gateway = GeminiGateway(executable="gemini", antigravity_executable=str(agy))

    status = gateway.auth_status()

    assert status["ready"] is True
    assert status["auth_method"] == "antigravity-cli"
    assert gateway.available is True


def test_gemini_gateway_antigravity_command_uses_stdin_stream_mode(tmp_path: Path):
    agy = tmp_path / "agy.exe"
    agy.write_text("stub", encoding="utf-8")
    gateway = GeminiGateway(executable="gemini", antigravity_executable=str(agy))

    command = gateway.command_for(tmp_path, model="gemini-3.1-pro-high")

    assert command[0] == str(agy)
    assert "--dangerously-skip-permissions" in command
    assert command[command.index("--input-format") + 1] == "text"
    assert command[command.index("--output-format") + 1] == "stream-json"
    assert command[command.index("--model") + 1] == "gemini-3.1-pro-high"
    assert "-p" not in command


def test_gemini_gateway_prefers_console_host_binary_for_hidden_child_terminals(tmp_path: Path):
    agy = tmp_path / "agy.exe"
    agy_real = tmp_path / "agy_real.exe"
    agy.write_text("gui stub", encoding="utf-8")
    agy_real.write_text("console stub", encoding="utf-8")
    gateway = GeminiGateway(executable="gemini", antigravity_executable=str(agy))

    command = gateway.command_for(tmp_path)

    assert command[0] == str(agy_real)


@pytest.mark.skipif(os.name != "nt", reason="Windows process-window behavior")
def test_gemini_gateway_hidden_console_tree_keeps_terminal_children_off_desktop(tmp_path: Path):
    agy = tmp_path / "agy.exe"
    agy_real = tmp_path / "agy_real.exe"
    agy.write_text("gui stub", encoding="utf-8")
    agy_real.write_text("console stub", encoding="utf-8")
    gateway = GeminiGateway(executable="gemini", antigravity_executable=str(agy))

    creationflags, startupinfo = gateway._launch_window_options(str(agy_real))

    assert creationflags & getattr(__import__("subprocess"), "CREATE_NEW_CONSOLE", 0)
    assert not (creationflags & getattr(__import__("subprocess"), "CREATE_NO_WINDOW", 0))
    assert startupinfo is not None
    assert startupinfo.dwFlags & getattr(__import__("subprocess"), "STARTF_USESHOWWINDOW", 1)
    assert startupinfo.wShowWindow == getattr(__import__("subprocess"), "SW_HIDE", 0)


def test_codex_chat_command_grants_native_full_access(tmp_path: Path):
    gateway = CodexGateway(remotion_dir=tmp_path / "CofiRemotion", executable="codex")

    command = gateway.command_for("plan", tmp_path)

    assert "--dangerously-bypass-approvals-and-sandbox" in command


def test_gemini_gateway_antigravity_command_resumes_exact_conversation(tmp_path: Path):
    agy = tmp_path / "agy.exe"
    agy.write_text("stub", encoding="utf-8")
    gateway = GeminiGateway(executable="gemini", antigravity_executable=str(agy))

    command = gateway.command_for(tmp_path, conversation_id="conversation-123")

    assert command[command.index("--conversation") + 1] == "conversation-123"


def test_gemini_gateway_fast_control_uses_low_effort_and_json_schema(tmp_path: Path):
    agy = tmp_path / "agy.exe"
    agy.write_text("stub", encoding="utf-8")
    gateway = GeminiGateway(executable="gemini", antigravity_executable=str(agy))

    command = gateway.command_for(
        tmp_path, model="", effort="low", json_schema={"type": "object"}, print_timeout="40s",
    )

    assert command[command.index("--effort") + 1] == "low"
    assert json.loads(command[command.index("--json-schema") + 1]) == {"type": "object"}
    assert command[command.index("--print-timeout") + 1] == "40s"
    assert "--model" not in command


def test_gemini_reusable_chat_persists_and_resumes_same_conversation(tmp_path: Path, monkeypatch):
    gateway = GeminiGateway(executable="gemini")
    seen = []

    def fake_run(prompt, workspace, label, **kwargs):
        seen.append(kwargs.get("conversation_id"))
        log_path = Path(workspace) / ".producer" / label / "events.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        conversation_id = kwargs.get("conversation_id") or "conversation-123"
        log_path.write_text(json.dumps({"event": "init", "conversation_id": conversation_id}) + "\n", encoding="utf-8")
        return StageResult(0, "ok", log_path)

    monkeypatch.setattr(gateway, "run_prompt", fake_run)

    gateway.run_prompt_reusable("first", tmp_path, "producer_chat_global")
    gateway.run_prompt_reusable("second", tmp_path, "producer_chat_global")

    session_path = tmp_path / ".producer" / "producer_chat_global" / "gemini_session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    assert seen == [None, "conversation-123"]
    assert session["conversation_id"] == "conversation-123"
    assert session["turn_count"] == 2


def test_gemini_reusable_chat_summarizes_before_rotating(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_GEMINI_SESSION_MAX_TURNS", "2")
    gateway = GeminiGateway(executable="gemini")
    seen = []

    def fake_run(prompt, workspace, label, **kwargs):
        seen.append((prompt, label, kwargs.get("conversation_id")))
        log_path = Path(workspace) / ".producer" / label / "events.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if label.endswith("_handoff"):
            log_path.write_text("", encoding="utf-8")
            return StageResult(0, "HANDOFF: đang sửa tab Edit, video đã xuất xong.", log_path)
        conversation_id = kwargs.get("conversation_id") or ("conversation-1" if len([item for item in seen if item[2] is None and not item[1].endswith("_handoff")]) == 1 else "conversation-2")
        log_path.write_text(json.dumps({"event": "init", "conversation_id": conversation_id}) + "\n", encoding="utf-8")
        return StageResult(0, "ok", log_path)

    monkeypatch.setattr(gateway, "run_prompt", fake_run)

    gateway.run_prompt_reusable("full first", tmp_path, "producer_chat_global", continuation_prompt="short first")
    gateway.run_prompt_reusable("full second", tmp_path, "producer_chat_global", continuation_prompt="short second")
    gateway.run_prompt_reusable("full third", tmp_path, "producer_chat_global", continuation_prompt="short third")

    assert seen[0][0] == "full first" and seen[0][2] is None
    assert seen[1][0] == "short second" and seen[1][2] == "conversation-1"
    assert seen[2][1] == "producer_chat_global_handoff" and seen[2][2] == "conversation-1"
    assert "HANDOFF: đang sửa tab Edit, video đã xuất xong." in seen[3][0]
    assert "full third" in seen[3][0]
    assert seen[3][2] is None
    session = json.loads((tmp_path / ".producer" / "producer_chat_global" / "gemini_session.json").read_text(encoding="utf-8"))
    assert session["conversation_id"] == "conversation-2"
    assert session["turn_count"] == 1


def test_gemini_reusable_chat_does_not_rotate_for_turn_count_alone(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("COFI_GEMINI_SESSION_MAX_TURNS", raising=False)
    gateway = GeminiGateway(executable="gemini")
    seen = []

    def fake_run(prompt, workspace, label, **kwargs):
        seen.append((label, kwargs.get("conversation_id")))
        log_path = Path(workspace) / ".producer" / label / "events.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps({"event": "init", "conversation_id": "conversation-123"}) + "\n", encoding="utf-8")
        return StageResult(0, "ok", log_path)

    monkeypatch.setattr(gateway, "run_prompt", fake_run)
    gateway.run_prompt_reusable("first", tmp_path, "producer_chat_global")
    session_path = tmp_path / ".producer" / "producer_chat_global" / "gemini_session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    session["turn_count"] = 50
    session_path.write_text(json.dumps(session), encoding="utf-8")

    gateway.run_prompt_reusable("second", tmp_path, "producer_chat_global", continuation_prompt="short second")

    assert seen == [("producer_chat_global", None), ("producer_chat_global", "conversation-123")]


def test_gemini_gateway_stream_last_message_returns_only_antigravity_result_response():
    lines = [
        json.dumps({"event": "init", "conversation_id": "abc", "init": {"model": "gemini-test"}}),
        json.dumps({
            "event": "step_update",
            "step_update": {
                "state": "ACTIVE",
                "step_type": "agent_response",
                "text_delta": '{"reply":"Xin chào',
            },
        }),
        json.dumps({
            "event": "result",
            "result": {
                "status": "SUCCESS",
                "response": '{"reply":"Xin chào! Tôi có thể hỗ trợ gì?","actions":[]}\n',
                "duration_seconds": 2.8,
                "usage": {"total_tokens": 22449},
            },
        }),
    ]

    assert GeminiGateway._stream_last_message(lines) == '{"reply":"Xin chào! Tôi có thể hỗ trợ gì?","actions":[]}'


def test_gemini_gateway_stream_last_message_keeps_unknown_plain_output():
    lines = ["plain response line 1", "plain response line 2"]

    assert GeminiGateway._stream_last_message(lines) == "plain response line 1\nplain response line 2"


def test_gemini_gateway_uses_configured_default_model_for_antigravity(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_GEMINI_MODEL", "gemini-3.1-pro-low")
    agy = tmp_path / "agy.exe"
    agy.write_text("stub", encoding="utf-8")
    gateway = GeminiGateway(executable="gemini", antigravity_executable=str(agy))

    command = gateway.command_for(tmp_path)

    assert command[command.index("--model") + 1] == "gemini-3.1-pro-low"


def test_gemini_gateway_exposes_antigravity_model_choices(monkeypatch, tmp_path: Path):
    agy = tmp_path / "agy.exe"
    agy.write_text("stub", encoding="utf-8")

    class ProbeResult:
        returncode = 0
        stdout = (
            "gemini-3.8-flash-high\tGemini 3.8 Flash (High)\n"
            "gemini-3.1-pro-high\tGemini 3.1 Pro (High)\n"
        )
        stderr = ""

    monkeypatch.setattr("documentary.gemini_gateway.subprocess.run", lambda *args, **kwargs: ProbeResult())
    gateway = GeminiGateway(executable="gemini", antigravity_executable=str(agy))

    status = gateway.auth_status()

    assert status["models"] == [
        {"id": "gemini-3.8-flash-high", "label": "Gemini 3.8 Flash (High)"},
        {"id": "gemini-3.1-pro-high", "label": "Gemini 3.1 Pro (High)"},
    ]


def test_gemini_reusable_chat_falls_back_to_local_handoff_when_summary_call_fails(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_GEMINI_SESSION_MAX_TURNS", "1")
    gateway = GeminiGateway(executable="gemini")
    seen = []

    def fake_run(prompt, workspace, label, **kwargs):
        seen.append((prompt, label, kwargs.get("conversation_id")))
        log_path = Path(workspace) / ".producer" / label / "events.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if label.endswith("_handoff"):
            log_path.write_text("", encoding="utf-8")
            return StageResult(1, "context window exceeded", log_path)
        cid = "conv-1" if len(seen) == 1 else "conv-2"
        log_path.write_text(json.dumps({"event": "init", "conversation_id": cid}) + "\n", encoding="utf-8")
        return StageResult(0, f"reply from {cid}", log_path)

    monkeypatch.setattr(gateway, "run_prompt", fake_run)

    first = gateway.run_prompt_reusable("first prompt", tmp_path, "producer_chat_global")
    second = gateway.run_prompt_reusable("second prompt", tmp_path, "producer_chat_global")

    assert first.returncode == 0
    assert second.returncode == 0
    assert seen[-1][2] is None
    assert "BẢN BÀN GIAO TỪ SESSION GEMINI TRƯỚC" in seen[-1][0]
    assert "reply from conv-1" in seen[-1][0]


def test_goal_session_compacts_and_rotates_when_token_budget_exceeded(tmp_path: Path, monkeypatch):
    from documentary.goal_session import AntigravityGoalSession

    monkeypatch.setenv("COFI_GOAL_MAX_CONTEXT_TOKENS", "50000")
    gateway = GeminiGateway(executable="gemini")
    session = AntigravityGoalSession(gateway, tmp_path, "producer_chat_global_goal")
    session.conversation_id = "conv-old-full"
    session.input_tokens = 20_000
    session.cache_read_tokens = 35_000
    session.step_index = 42
    session.turn_count = 3
    session._save_session_state(last_response_excerpt="Đã hoàn thành bước Script và Voice.")

    assert session.should_compact() is True
    handoff = session.compact_and_rotate(reason="proactive_context_guard")

    assert session.conversation_id == ""
    assert session.total_context_tokens == 0
    assert (tmp_path / ".producer" / "producer_chat_global_goal" / "handoff_summary.txt").exists()
    assert (tmp_path / ".producer" / "producer_chat_global" / "handoff_summary.txt").exists()
    injected = session._inject_handoff("/goal Tiếp tục dựng bước Edit", handoff)
    assert injected.startswith("/goal [BẢN BÀN GIAO NGỮ CẢNH TỰ ĐỘNG")
    assert "Tiếp tục dựng bước Edit" in injected

