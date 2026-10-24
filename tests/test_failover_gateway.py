from pathlib import Path

from documentary.codex_gateway import StageResult
from documentary.failover_gateway import FailoverGateway


class StubGateway:
    def __init__(self, name: str, results: list[StageResult]):
        self.name = name
        self.results = list(results)
        self.calls: list[dict] = []
        self.available = True
        self.executable = name
        self.reset_calls: list[tuple[Path, str, str]] = []

    def run_prompt(self, prompt, workspace, label, **kwargs):
        self.calls.append({"prompt": prompt, "workspace": Path(workspace), "label": label, "kwargs": kwargs})
        return self.results.pop(0)

    def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
        return self.run_prompt(prompt, workspace, label, **kwargs)

    def reset_reusable_session(self, workspace, label, reason="manual_reset"):
        self.reset_calls.append((Path(workspace), label, reason))
        return True


def result(tmp_path: Path, code: int, message: str) -> StageResult:
    return StageResult(code, message, tmp_path / "events.jsonl")


def test_codex_success_does_not_call_gemini(tmp_path):
    codex = StubGateway("codex", [result(tmp_path, 0, "codex ok")])
    gemini = StubGateway("gemini", [result(tmp_path, 0, "gemini ok")])
    router = FailoverGateway(codex, gemini, remotion_dir=tmp_path)

    actual = router.run_prompt_reusable("continue work", tmp_path, "edit")

    assert actual.returncode == 0
    assert len(codex.calls) == 1
    assert gemini.calls == []
    assert router.status()["active_provider"] == "codex"


def test_codex_failure_hands_off_same_workspace_to_gemini(tmp_path):
    codex = StubGateway("codex", [result(tmp_path, 1, "codex unavailable")])
    gemini = StubGateway("gemini", [result(tmp_path, 0, "gemini continued")])
    router = FailoverGateway(codex, gemini, remotion_dir=tmp_path)

    actual = router.run_prompt_reusable("finish only the remaining beats", tmp_path, "footage")

    assert actual.returncode == 0
    assert gemini.calls[0]["workspace"] == tmp_path
    assert "codex unavailable" in gemini.calls[0]["prompt"]
    assert "finish only the remaining beats" in gemini.calls[0]["prompt"]
    assert "không làm lại" in gemini.calls[0]["prompt"].lower()
    status = router.status()
    assert status["active_provider"] == "gemini"
    assert status["last_switch"]["from"] == "codex"
    assert status["last_switch"]["to"] == "gemini"


def test_active_gemini_failure_rotates_back_to_codex(tmp_path):
    codex = StubGateway(
        "codex",
        [result(tmp_path, 1, "codex first failure"), result(tmp_path, 0, "codex recovered")],
    )
    gemini = StubGateway(
        "gemini",
        [result(tmp_path, 0, "gemini continued"), result(tmp_path, 1, "gemini later failure")],
    )
    router = FailoverGateway(codex, gemini, remotion_dir=tmp_path)

    assert router.run_prompt_reusable("first task", tmp_path, "edit").returncode == 0
    actual = router.run_prompt_reusable("next unfinished task", tmp_path, "edit")

    assert actual.returncode == 0
    assert router.status()["active_provider"] == "codex"
    assert len(gemini.calls) == 2
    assert len(codex.calls) == 2
