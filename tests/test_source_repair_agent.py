import json
from pathlib import Path
from types import SimpleNamespace

from COFI_BRAIN.source_repair_agent import SourceRepairAgent


class RecordingRunner:
    def __init__(self, returncodes):
        self.returncodes = list(returncodes)
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        returncode = self.returncodes.pop(0)
        return SimpleNamespace(returncode=returncode, stdout=f"stdout-{len(self.calls)}", stderr=f"stderr-{len(self.calls)}")


class SourceChangingRunner(RecordingRunner):
    def __init__(self, returncodes, project_root: Path, change_on_call: int = 1):
        super().__init__(returncodes)
        self.project_root = project_root
        self.change_on_call = change_on_call

    def __call__(self, command, **kwargs):
        result = super().__call__(command, **kwargs)
        if len(self.calls) == self.change_on_call:
            target = self.project_root / "app.py"
            target.write_text(target.read_text(encoding="utf-8") + "# repaired\n", encoding="utf-8")
        return result


def test_execute_job_runs_codex_with_full_access_then_verifies_and_persists_fixed(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('before')\n", encoding="utf-8")
    runner = SourceChangingRunner([0, 0], tmp_path)
    agent = SourceRepairAgent(
        str(tmp_path),
        runner=runner,
        executable_finder=lambda name: f"C:/tools/{name}.exe",
        test_command=["python", "-m", "pytest", "-q"],
    )
    queued = agent.create_job("ImportError in app.py", "runtime", provider="codex")

    fixed = agent.execute_job(queued["id"])

    codex_command, codex_kwargs = runner.calls[0]
    assert codex_command[:2] == ["C:/tools/codex.exe", "exec"]
    assert "--dangerously-bypass-approvals-and-sandbox" in codex_command
    assert "--skip-git-repo-check" in codex_command
    assert codex_command[-1] == "-"
    assert str(tmp_path.resolve()) in codex_kwargs["input"]
    assert runner.calls[1][0] == ["python", "-m", "pytest", "-q"]
    assert fixed["status"] == "fixed"
    assert fixed["provider_used"] == "codex"
    stored = json.loads((tmp_path / ".producer" / "source_repairs" / queued["id"] / "job.json").read_text(encoding="utf-8"))
    assert stored["status"] == "fixed"


def test_auto_provider_falls_back_to_gemini_when_codex_fails(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('before')\n", encoding="utf-8")
    runner = SourceChangingRunner([1, 0, 0], tmp_path, change_on_call=2)
    agent = SourceRepairAgent(
        str(tmp_path), runner=runner,
        executable_finder=lambda name: f"C:/tools/{name}.cmd",
        test_command=["python", "-m", "pytest", "-q"],
    )
    job = agent.create_job("broken endpoint", provider="auto")

    result = agent.execute_job(job["id"])

    assert result["status"] == "fixed"
    assert result["provider_used"] == "gemini"
    gemini_command = runner.calls[1][0]
    assert gemini_command[0] == "C:/tools/agy.cmd"
    assert gemini_command[gemini_command.index("--output-format") + 1] == "stream-json"
    assert "--dangerously-skip-permissions" in gemini_command
    assert [item["provider"] for item in result["attempts"]] == ["codex", "gemini"]


def test_failed_independent_verification_never_marks_job_fixed(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('before')\n", encoding="utf-8")
    runner = SourceChangingRunner([0, 2], tmp_path)
    agent = SourceRepairAgent(
        str(tmp_path), runner=runner,
        executable_finder=lambda name: name,
        test_command=["python", "-m", "pytest", "-q"],
    )
    job = agent.create_job("failing behavior", provider="gemini")

    result = agent.execute_job(job["id"])

    assert result["status"] == "failed"
    assert result["verification"]["returncode"] == 2
    assert "Kiểm thử độc lập thất bại" in result["error"]


def test_successful_cli_without_source_change_is_not_marked_fixed(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('unchanged')\n", encoding="utf-8")
    runner = RecordingRunner([0])
    agent = SourceRepairAgent(
        str(tmp_path), runner=runner,
        executable_finder=lambda name: name,
        test_command=["python", "-m", "pytest", "-q"],
    )
    job = agent.create_job("fix the application", provider="codex")

    result = agent.execute_job(job["id"])

    assert result["status"] == "failed"
    assert result["verification"] is None
    assert result["source_changes"] == []
    assert "không thay đổi file mã nguồn" in result["error"].lower()


def test_gemini_repair_prefers_antigravity_stream_transport(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('before')\n", encoding="utf-8")
    runner = SourceChangingRunner([0, 0], tmp_path)

    def find(name: str):
        if name == "agy":
            return "C:/tools/agy.exe"
        if name == "gemini":
            return "C:/tools/gemini.cmd"
        return None

    agent = SourceRepairAgent(
        str(tmp_path), runner=runner, executable_finder=find,
        test_command=["python", "-m", "pytest", "-q"],
    )
    job = agent.create_job("upgrade chat", provider="gemini")

    result = agent.execute_job(job["id"])

    command, kwargs = runner.calls[0]
    assert command[0] == "C:/tools/agy.exe"
    assert command[command.index("--output-format") + 1] == "stream-json"
    assert command[command.index("--input-format") + 1] == "text"
    assert "upgrade chat" in kwargs["input"]
    assert result["provider_used"] == "gemini"


def test_repair_job_exposes_normalized_live_stream_events(tmp_path: Path):
    agent = SourceRepairAgent(str(tmp_path), runner=RecordingRunner([0, 0]), executable_finder=lambda name: name)
    job = agent.create_job("broken", provider="codex")
    directory = tmp_path / ".producer" / "source_repairs" / job["id"]
    event_log = directory / "attempt-1-codex.events.jsonl"
    event_log.write_text(
        '{"type":"item.started","item":{"type":"command_execution","command":"pytest -q"}}\n'
        '{"event":"step_update","step_update":{"state":"ACTIVE","step_type":"tool","tool_name":"view_file"}}\n',
        encoding="utf-8",
    )
    stored = agent.get_job(job["id"])
    stored["attempts"] = [{"provider": "codex", "status": "running", "event_log": str(event_log)}]
    agent._save(stored)

    live = agent.get_job(job["id"])

    assert live["stream_events"][-2]["kind"] == "command"
    assert "pytest -q" in live["stream_events"][-2]["message"]
    assert live["stream_events"][-1]["kind"] == "tool"
    assert "view_file" in live["stream_events"][-1]["message"]
