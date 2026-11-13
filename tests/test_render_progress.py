from __future__ import annotations

import os
import time
from pathlib import Path

from documentary import render_progress as rp


def _write_log(path: Path, text: str, age_sec: float = 0.0) -> None:
    path.write_text(text, encoding="utf-8")
    if age_sec:
        t = time.time() - age_sec
        os.utime(path, (t, t))


def test_parse_eta_variants():
    assert rp.parse_eta_seconds("12m 54s") == 774
    assert rp.parse_eta_seconds("45s") == 45
    assert rp.parse_eta_seconds("1h 2m") == 3720
    assert rp.parse_eta_seconds("30") == 30
    assert rp.parse_eta_seconds("") is None


def test_parse_render_log_rendering_line():
    text = "Bundling 100%\nCopying public dir 2.7 GB\nRendered 32787/46469, time remaining: 12m 54s\n"
    st = rp.parse_render_log(text)
    assert st["stage"] == "rendering"
    assert st["done"] == 32787 and st["total"] == 46469
    assert st["eta_seconds"] == 774
    assert 0.69 < st["fraction"] < 0.70


def test_parse_render_log_encoded_after_render():
    st = rp.parse_render_log("Rendered 100/100, time remaining: 0s\nEncoded 50/100\n")
    assert st["stage"] == "encoding"
    assert st["fraction"] > 0.97


def test_pending_status_with_live_log_is_counted(tmp_path):
    """Regression: on-disk status 'pending' while log is live used to show 0.5%."""
    log = tmp_path / "part-0001.log"
    _write_log(log, "Rendered 33160/46469, time remaining: 13m 11s\n")
    chunks = [{"index": 1, "start_frame": 0, "end_frame": 46468, "status": "pending", "log_path": str(log)}]
    agg = rp.aggregate_chunk_progress(chunks)
    assert agg["active"] == 1
    assert agg["frames_total"] == 46469
    assert agg["frames_done"] == 33160
    assert 0.69 < agg["fraction"] < 0.71
    assert rp.eta_fps(agg) is not None


def test_stale_log_from_previous_attempt_ignored(tmp_path):
    log = tmp_path / "part-0001.log"
    _write_log(log, "Rendered 46469/46469, time remaining: 0s\n", age_sec=3600)
    chunks = [{"index": 1, "start_frame": 0, "end_frame": 46468, "status": "pending", "log_path": str(log)}]
    agg = rp.aggregate_chunk_progress(chunks)
    assert agg["active"] == 0
    assert agg["fraction"] == 0.0


def test_parallel_chunks_are_summed(tmp_path):
    a, b = tmp_path / "a.log", tmp_path / "b.log"
    _write_log(a, "Rendered 500/1000, time remaining: 20s\n")
    _write_log(b, "Rendered 250/1000, time remaining: 60s\n")
    chunks = [
        {"index": 1, "start_frame": 0, "end_frame": 999, "status": "ready", "log_path": ""},
        {"index": 2, "start_frame": 1000, "end_frame": 1999, "status": "rendering", "log_path": str(a)},
        {"index": 3, "start_frame": 2000, "end_frame": 2999, "status": "pending", "log_path": str(b)},
    ]
    agg = rp.aggregate_chunk_progress(chunks)
    assert agg["active"] == 2
    assert agg["frames_done"] == 1000 + 500 + 250
    assert agg["frames_total"] == 3000
    assert agg["eta_seconds"] == 60
    assert "2 đoạn song song" in rp.describe_states(agg, 25.0)


def test_fps_tracker_measures_real_rate():
    tr = rp.FpsTracker(window_sec=60)
    assert tr.update("j", 1000, now=0.0) is None
    fps = tr.update("j", 1300, now=10.0)
    assert abs(fps - 30.0) < 1e-6
    # counter reset (new attempt) clears history
    assert tr.update("j", 10, now=11.0) is None
