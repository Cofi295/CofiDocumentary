import os

import pytest

from documentary import engines
from documentary.engines import executable_status


def test_executable_status_reports_resolved_path():
    status = executable_status("python")
    assert status["ok"] is True
    assert status["path"]


@pytest.mark.skipif(os.name != "nt", reason="Windows executable wrapper behavior")
def test_resolve_executable_finds_cmd_wrapper_when_shutil_which_misses(tmp_path, monkeypatch):
    wrapper = tmp_path / "gemini.cmd"
    wrapper.write_text("@echo off\r\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(engines.shutil, "which", lambda _name: None)

    assert engines.resolve_executable("gemini") == str(wrapper)
