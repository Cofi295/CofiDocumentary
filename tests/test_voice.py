import io
import json
from pathlib import Path
import wave

import pytest

from documentary.quality import normalize_production_recipe, validate_phase_quality
from documentary.srt import build_srt, format_srt_time
from documentary.voice import CofiVoiceEngine


def _wav_bytes(duration_sec: float, sample_rate: int = 1000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * round(duration_sec * sample_rate))
    return buffer.getvalue()


class _TtsResponse:
    def __init__(self, content: bytes, seed: str):
        self.content = content
        self.headers = {"X-Seed": seed}

    def raise_for_status(self):
        return None


class _DurationSession:
    def __init__(self, base_duration_sec: float = 25.0):
        self.calls = []
        self.base_duration_sec = float(base_duration_sec)

    def post(self, _url, json, timeout):
        self.calls.append(dict(json))
        speed = float(json["speed"])
        seed = str(json.get("seed") or len(self.calls))
        return _TtsResponse(_wav_bytes(self.base_duration_sec / speed, sample_rate=10_000), seed)


class _HealthResponse:
    def __init__(self, ok: bool, status_code: int = 200):
        self.ok = ok
        self.status_code = status_code


class _DiscoverySession:
    def get(self, url, timeout):
        if url == "http://127.0.0.1:8776/api/health":
            return _HealthResponse(True)
        raise __import__("requests").ConnectionError("offline")


def test_voice_engine_discovers_existing_shared_instance_on_legacy_port():
    engine = CofiVoiceEngine("http://127.0.0.1:8000", session=_DiscoverySession())

    health = engine.discover(["http://127.0.0.1:8000", "http://127.0.0.1:8776"])

    assert health["ok"] is True
    assert health["url"] == "http://127.0.0.1:8776"
    assert engine.base_url == "http://127.0.0.1:8776"


def test_srt_uses_real_voice_timestamps_per_visual_beat():
    beats = [
        {"beat_id": "B001", "text": "Cau mot", "start_sec": 0.0, "end_sec": 3.25},
        {"beat_id": "B002", "text": "Cau hai", "start_sec": 3.25, "end_sec": 7.8},
    ]
    text = build_srt(beats)
    assert "00:00:00,000 --> 00:00:03,250" in text
    assert "00:00:03,250 --> 00:00:07,800" in text
    assert "Cau mot" in text and "Cau hai" in text


def test_format_srt_time_handles_minutes_and_milliseconds():
    assert format_srt_time(65.432) == "00:01:05,432"


def test_voice_quality_gate_accepts_duration_outside_estimated_target(tmp_path: Path):
    recipe = normalize_production_recipe({}, target_duration_minutes=5)
    contract = recipe["quality_contract"]
    beat_ids = [f"B{i + 1:03d}" for i in range(contract["min_scene_count"])]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "target_duration_sec": 300,
        "beats": [{"beat_id": beat_id} for beat_id in beat_ids],
    }), encoding="utf-8")
    narration = tmp_path / "audio" / "narration.wav"
    narration.parent.mkdir(parents=True, exist_ok=True)
    narration.write_bytes(b"wav")
    (tmp_path / "voice_manifest.json").write_text(json.dumps({
        "duration_sec": 270.37,
        "narration_path": str(narration),
        "beats": [{"beat_id": beat_id} for beat_id in beat_ids],
    }), encoding="utf-8")

    validate_phase_quality("voice", tmp_path, {"production_recipe": recipe})


def test_voice_engine_keeps_natural_speed_when_estimated_target_differs(tmp_path: Path):
    recipe = normalize_production_recipe({}, target_duration_minutes=2)
    beat_ids = [f"B{i + 1:03d}" for i in range(recipe["quality_contract"]["min_scene_count"])]
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "target_duration_sec": 120,
        "beats": [
            {"beat_id": beat_id, "narration_text": f"Narration {beat_id}", "target_duration_sec": 30}
            for beat_id in beat_ids
        ],
    }), encoding="utf-8")
    session = _DurationSession(base_duration_sec=100.0 / len(beat_ids))
    engine = CofiVoiceEngine(session=session)
    job = {
        "language": "en",
        "voice": {"speed": 1.0, "mode": "balanced"},
        "production_recipe": recipe,
    }

    engine.run(job, tmp_path)

    manifest = json.loads((tmp_path / "voice_manifest.json").read_text(encoding="utf-8"))
    assert manifest["duration_sec"] == pytest.approx(100.0, abs=0.01)
    assert manifest["speed"] == 1.0
    assert manifest["requested_speed"] == 1.0
    assert manifest["auto_fit_applied"] is False
    assert len(session.calls) == len(beat_ids)
