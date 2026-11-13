from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from documentary import service as svc_mod
from documentary.service import DocumentaryService, _post_render_qc_gate_enabled


def test_post_render_qc_gate_default_off(monkeypatch):
    monkeypatch.delenv("COFI_POST_RENDER_QC_GATE", raising=False)
    assert _post_render_qc_gate_enabled({}) is False
    assert _post_render_qc_gate_enabled(None) is False
    assert _post_render_qc_gate_enabled({"post_render_qc_gate": True}) is True
    assert _post_render_qc_gate_enabled({"production_recipe": {"post_render_qc_gate": "on"}}) is True
    monkeypatch.setenv("COFI_POST_RENDER_QC_GATE", "1")
    assert _post_render_qc_gate_enabled({}) is True
    assert _post_render_qc_gate_enabled({"post_render_qc_gate": False}) is False


class _Store:
    def __init__(self):
        self.updates = []

    def update(self, job_id, patch):
        self.updates.append((job_id, patch))
        return patch


def _fake_service(probe):
    fake = SimpleNamespace(store=_Store())
    fake._read_json_dict = DocumentaryService._read_json_dict
    fake._probe_export_video = probe
    fake._locate_export_video = lambda ws: DocumentaryService._locate_export_video(fake, ws)
    fake._finalize_export_minimal = lambda job, ws: DocumentaryService._finalize_export_minimal(fake, job, ws)
    return fake


def test_minimal_finalize_accepts_with_warnings(tmp_path, monkeypatch):
    monkeypatch.delenv("COFI_POST_RENDER_QC_GATE", raising=False)
    (tmp_path / "release").mkdir()
    video = tmp_path / "release" / "video.mp4"
    video.write_bytes(b"\x00" * 1024)

    def probe(_v):
        return {"duration_seconds": 12.0, "fps": 30.0, "width": 1920, "height": 1080,
                "video_frames": 360, "audio_duration_seconds": 0.0, "has_audio": False}

    fake = _fake_service(probe)
    res = DocumentaryService._finalize_export_minimal(fake, {"id": "j1"}, tmp_path)
    assert res.returncode == 0
    fm = json.loads((tmp_path / "final_manifest.json").read_text(encoding="utf-8"))
    assert fm["final_qc_status"] == "TECHNICAL_ACCEPT"
    assert fm["post_render_qc_gate"] is False
    assert any("audio" in w for w in fm["qc_warnings"])
    assert (tmp_path / "render_manifest.json").is_file()
    assert (tmp_path / "director_report.md").is_file()
    # _validate_artifacts must not run the quality gate
    DocumentaryService._validate_artifacts(fake, "qc", tmp_path, {"id": "j1"})


def test_minimal_finalize_probe_failure_is_non_blocking(tmp_path, monkeypatch):
    monkeypatch.delenv("COFI_POST_RENDER_QC_GATE", raising=False)
    (tmp_path / "release").mkdir()
    (tmp_path / "release" / "video.mp4").write_bytes(b"\x00" * 10)

    def probe(_v):
        raise RuntimeError("boom")

    fake = _fake_service(probe)
    res = DocumentaryService._finalize_export_minimal(fake, {"id": "j1"}, tmp_path)
    assert res.returncode == 0
    fm = json.loads((tmp_path / "final_manifest.json").read_text(encoding="utf-8"))
    assert fm["qc_warnings"]


def test_minimal_finalize_without_mp4_raises(tmp_path):
    fake = _fake_service(lambda v: {})
    with pytest.raises(RuntimeError):
        DocumentaryService._finalize_export_minimal(fake, {"id": "j1"}, tmp_path)
