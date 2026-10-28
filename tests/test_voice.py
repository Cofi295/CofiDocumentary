import io
import json
from pathlib import Path
import wave

import pytest

from documentary.quality import normalize_production_recipe, validate_phase_quality
from documentary.srt import build_srt, format_srt_time
from documentary.voice import CofiVoiceEngine, INTER_BEAT_PAUSE_SEC, OUTRO_FADE_TAIL_SEC, wav_duration


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
    expected_total = 100.0 + (len(beat_ids) - 1) * INTER_BEAT_PAUSE_SEC + OUTRO_FADE_TAIL_SEC
    assert manifest["duration_sec"] == pytest.approx(expected_total, abs=0.05)
    assert wav_duration(tmp_path / "audio" / "narration.wav") == pytest.approx(expected_total, abs=0.05)
    last_beat = manifest["beats"][-1]
    assert last_beat["outro_tail_sec"] == pytest.approx(OUTRO_FADE_TAIL_SEC, abs=0.01)
    assert last_beat["end_sec"] - last_beat["speech_end_sec"] == pytest.approx(OUTRO_FADE_TAIL_SEC, abs=0.01)
    srt_text = (tmp_path / "subtitles.srt").read_text(encoding="utf-8")
    assert format_srt_time(last_beat["speech_end_sec"]) in srt_text
    assert manifest["speed"] == 1.0
    assert manifest["requested_speed"] == 1.0
    assert manifest["auto_fit_applied"] is False
    assert len(session.calls) == len(beat_ids)


def test_normalize_korean_tts_text_converts_comma_numbers_and_counters():
    from documentary.voice import normalize_korean_tts_text

    raw = (
        "5살 아이의 기억으로 2,000킬로미터 떨어진 고향에서 5,000위안과 26년 동안 "
        "50대 후반 부부를 찾았습니다. 연 14.6% 수익과 십사점육 퍼센트, 백구십육 개, "
        "베이징-안후이성 제1중급인민법원 1,200자루."
    )
    norm = normalize_korean_tts_text(raw)
    assert "이천 킬로미터" in norm
    assert "오천 위안" in norm
    assert "이십육 년 동안" in norm
    assert "오십 대 후반" in norm
    assert norm.count("십사쩜육 퍼센트") == 2
    assert "백구십육개" in norm
    assert "베이징 안후이성" in norm
    assert "제일중급인민법원" in norm
    assert "천이백 자루" in norm
    assert "2,000" not in norm
    assert "5,000" not in norm


def test_sculpt_wav_bytes_for_korean_broadcast_trims_and_compresses_long_internal_pauses():
    import numpy as np
    from documentary.voice import sculpt_wav_bytes_for_korean_broadcast, wav_duration

    sr = 24000
    t_voice = np.linspace(0.0, 0.5, int(sr * 0.5), endpoint=False, dtype=np.float32)
    voiced = 0.25 * np.sin(2.0 * np.pi * 220.0 * t_voice)
    lead_sil = np.zeros(int(sr * 0.25), dtype=np.float32)
    mid_sil = np.zeros(int(sr * 0.85), dtype=np.float32)
    trail_sil = np.zeros(int(sr * 0.30), dtype=np.float32)
    full = np.concatenate([lead_sil, voiced, mid_sil, voiced, trail_sil])
    pcm = np.clip(np.round(full * 32767.0), -32768, 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    raw_bytes = buf.getvalue()

    sculpted_bytes = sculpt_wav_bytes_for_korean_broadcast(raw_bytes)
    with wave.open(io.BytesIO(sculpted_bytes), "rb") as r:
        sculpted_dur = r.getnframes() / float(r.getframerate())

    # 0.5s + 0.5s voiced + ~0.285s mid pause + 0.025s lead + 0.035s trail ≈ 1.345s (down from 1.90s)
    assert 1.25 <= sculpted_dur <= 1.45


def test_validate_korean_script_grammar_integrity_catches_dangling_modifiers_and_duplicate_subjects():
    from documentary.quality import validate_korean_script_grammar_integrity

    valid_beats = [
        {"beat_id": "B001", "narration_text": "서른한 살이 된 양뉴화는 동영상 플랫폼 더우인에 영상을 올렸습니다."},
        {"beat_id": "B002", "narration_text": "무덤 앞에 무릎을 꿇은 자매는 판결문 복사본을 불태웠습니다."},
    ]
    validate_korean_script_grammar_integrity(valid_beats)

    with pytest.raises(RuntimeError, match="dangling human modifier"):
        validate_korean_script_grammar_integrity([
            {"beat_id": "B068", "narration_text": "서른한 살이 된 동영상 플랫폼 더우인에 자신의 사연을 올렸습니다."},
        ])

    with pytest.raises(RuntimeError, match="duplicate topic subject"):
        validate_korean_script_grammar_integrity([
            {"beat_id": "B095", "narration_text": "양뉴화는 그토록 그리워하던 양뉴화는 마침내 고향 집에 도착했습니다."},
        ])
