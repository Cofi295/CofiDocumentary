from pathlib import Path

import requests

import documentary.radar as radar_module
from documentary.radar import RadarClient


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _RecoveringSession:
    def __init__(self):
        self.post_calls = 0
        self.health_calls = 0
        self.running = False

    def post(self, url, json=None, timeout=None):
        self.post_calls += 1
        if self.post_calls == 1:
            raise requests.ConnectionError("connection refused")
        return _Response({"channel_id": "UC-test"})

    def get(self, url, params=None, timeout=None):
        self.health_calls += 1
        if not self.running:
            raise requests.ConnectionError("radar still offline")
        return _Response({"ok": True})


def test_channel_scan_autostarts_local_radar_after_connection_refused(tmp_path: Path, monkeypatch):
    (tmp_path / "app.py").write_text("# test radar entrypoint\n", encoding="utf-8")
    started = []

    class _Process:
        pid = 12345

    def fake_popen(*args, **kwargs):
        started.append((args, kwargs))
        session.running = True
        return _Process()

    monkeypatch.setattr(radar_module.subprocess, "Popen", fake_popen)
    session = _RecoveringSession()
    client = RadarClient(
        "http://127.0.0.1:8775",
        session=session,
        radar_home=tmp_path,
        startup_wait_seconds=0.05,
        startup_poll_interval=0.0,
    )

    result = client.channel_scan({"channel_ref": "https://youtube.com/@test"})

    assert result["channel_id"] == "UC-test"
    assert session.post_calls == 2
    assert session.health_calls >= 1
    assert len(started) == 1
