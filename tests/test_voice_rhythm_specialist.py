from __future__ import annotations

import base64
import io
import json
import re
import wave
from pathlib import Path
from typing import Any

import numpy as np

from documentary.edit import build_edit_rhythm_score
from documentary.prompts import _profile_rhythm_dna_direction
from documentary.voice import direct_korean_emotional_prosody, plan_contextual_beat_pauses
from services.channel_profile_service import ChannelProfileService
from services.voice_rhythm_specialist import (
    CLEAN_MASTER_VOICES,
    VoiceRhythmSpecialistService,
    apply_voice_color_polish_wav_bytes,
)


def _make_sine_wav_bytes(freq_hz: float = 220.0, duration_sec: float = 0.6, sr: int = 24000) -> bytes:
    t = np.linspace(0.0, duration_sec, int(sr * duration_sec), endpoint=False)
    samples = (np.sin(2.0 * np.pi * freq_hz * t) * 12000.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, status_code: int = 200, json_data: dict[str, Any] | None = None, content: bytes = b""):
        self.status_code = status_code
        self._json = json_data or {}
        self.content = content

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> dict[str, Any]:
        return self._json

    def raise_for_status(self) -> None:
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeVoiceSession:
    def __init__(self, cofivoice_dir: Path):
        self.cofivoice_dir = cofivoice_dir
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append((url, kwargs))
        if url.endswith("/api/tts"):
            return _FakeResponse(status_code=200, content=_make_sine_wav_bytes(195.0, 0.8))
        if url.endswith("/api/clone"):
            cloned_id = "cloned-user-sample-voice-001"
            (self.cofivoice_dir / "saved_prompts").mkdir(parents=True, exist_ok=True)
            (self.cofivoice_dir / "saved_prompts" / f"{cloned_id}.pt").write_bytes(b"CLONED_SAMPLE_PT")
            return _FakeResponse(
                status_code=200,
                json_data={
                    "id": cloned_id,
                    "name": kwargs.get("data", {}).get("name", "Cloned Voice"),
                    "type": "clone",
                    "language": kwargs.get("data", {}).get("language", "ko"),
                    "prompt_path": f"saved_prompts\\{cloned_id}.pt",
                    "preview_url": f"/static/previews/{cloned_id}.wav",
                },
            )
        return _FakeResponse(status_code=404)


def _seed_clean_cofivoice_dir(tmp_path: Path) -> Path:
    cv_dir = tmp_path / "cofivoice"
    (cv_dir / "saved_prompts").mkdir(parents=True, exist_ok=True)
    (cv_dir / "static" / "previews").mkdir(parents=True, exist_ok=True)
    db: list[dict[str, Any]] = []
    for meta in CLEAN_MASTER_VOICES.values():
        vid = meta["id"]
        if any(row["id"] == vid for row in db):
            continue
        (cv_dir / "saved_prompts" / f"{vid}.pt").write_bytes(f"CLEAN_1ST_GEN_PT_{vid}".encode("utf-8"))
        (cv_dir / "static" / "previews" / f"{vid}.wav").write_bytes(_make_sine_wav_bytes(210.0, 0.5))
        db.append(
            {
                "id": vid,
                "name": meta["name"],
                "type": "clone",
                "language": meta["language"],
                "prompt_path": f"saved_prompts\\{vid}.pt",
                "preview_url": f"/static/previews/{vid}.wav",
            }
        )
    (cv_dir / "voices_db.json").write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")
    return cv_dir


def test_archetype_analysis_differentiates_genres_and_3_layers() -> None:
    svc = VoiceRhythmSpecialistService()

    noir = svc.analyze_profile_rhythm_dna(
        {
            "label": "Hồ sơ True Crime Hình Sự Trung Quốc V2 · Đạo Diễn AI Có Hồn",
            "market": "KR",
            "default_language": "ko",
            "default_duration_minutes": 30,
            "allowed_topics": "Trọng án hình sự có thật, truy bắt 20 năm",
        }
    )
    grace = svc.analyze_profile_rhythm_dna(
        {
            "label": "Thư Ân Điển & Lời Chúa 60 Phút (은혜의 편지)",
            "market": "KR",
            "default_language": "ko",
            "default_duration_minutes": 60,
        }
    )
    senior = svc.analyze_profile_rhythm_dna(
        {
            "label": "Tội Phạm Công Nghệ Cao & Tài Chính · Khán giả 45–70 tuổi",
            "market": "KR",
            "default_language": "ko",
            "default_duration_minutes": 30,
        }
    )

    assert noir["archetype_id"] == "kr_truecrime_noir_director"
    assert grace["archetype_id"] == "kr_grace_pastoral_letter"
    assert senior["archetype_id"] == "kr_cyber_finance_senior_clarity"

    # All Korean profiles default to clean K1 (`09c70cc1-cc86-4905-b65b-3967209c3175`)
    k1_id = "09c70cc1-cc86-4905-b65b-3967209c3175"
    assert noir["voice_color_spec"]["recommended_base_voice_id"] == k1_id
    assert grace["voice_color_spec"]["recommended_base_voice_id"] == k1_id
    assert senior["voice_color_spec"]["recommended_base_voice_id"] == k1_id

    # Grace 60m must be slower, warmer, forbid fast urgent chains, and hold shots much longer than Noir
    assert grace["voice_color_spec"]["prosody_profile"]["tts_speed"] < noir["voice_color_spec"]["prosody_profile"]["tts_speed"]
    assert grace["vocal_cadence"]["allow_urgent_fast_chain"] is False
    assert noir["vocal_cadence"]["allow_urgent_fast_chain"] is True
    assert (
        grace["editing_cadence"]["shot_pacing_sec"]["standard_avg_sec"]
        > noir["editing_cadence"]["shot_pacing_sec"]["standard_avg_sec"] + 2.0
    )


def test_design_from_clean_k1_and_user_sample_clone(tmp_path: Path) -> None:
    cv_dir = _seed_clean_cofivoice_dir(tmp_path)
    fake_session = _FakeVoiceSession(cv_dir)
    specialist = VoiceRhythmSpecialistService(
        cofivoice_dir=cv_dir,
        cofivoice_url="http://127.0.0.1:8000",
        session=fake_session,
    )
    profiles_file = tmp_path / "channel_profiles.json"
    profile_service = ChannelProfileService(storage_path=profiles_file)

    # 1. Design from clean K1 (`base_voice`) via ChannelProfileService.create_profile(auto_design_voice=True)
    # Temporarily point specialist creation inside test by calling design_and_bind_profile_voice directly too
    created = profile_service.create_profile(
        {
            "label": "KR Crime Noir Test Channel",
            "market": "KR",
            "default_language": "ko",
            "default_duration_minutes": 25,
            "allowed_topics": "Trọng án hình sự có thật",
            "auto_design_voice": False,
        }
    )
    res_k1 = specialist.design_and_bind_profile_voice(
        created,
        profile_service=profile_service,
        source_mode="base_voice",
        base_voice_id="09c70cc1-cc86-4905-b65b-3967209c3175",
        custom_direction="Trầm hơn, nghỉ sâu ở cú lật hồ sơ",
        synthesize_preview=True,
    )
    vid_1 = res_k1["voice_signature"]["voice_id"]
    assert vid_1 != "09c70cc1-cc86-4905-b65b-3967209c3175"
    assert res_k1["voice_signature"]["base_voice_id"] == "09c70cc1-cc86-4905-b65b-3967209c3175"
    # Lossless 1st-gen `.pt` copied directly from clean K1!
    assert (cv_dir / "saved_prompts" / f"{vid_1}.pt").read_bytes() == (
        cv_dir / "saved_prompts" / "09c70cc1-cc86-4905-b65b-3967209c3175.pt"
    ).read_bytes()
    assert (cv_dir / "static" / "previews" / f"{vid_1}.wav").exists()

    # Re-designing the same profile reuses `vid_1` (zero DB bloat!)
    res_k1_again = specialist.design_and_bind_profile_voice(
        profile_service.get_profile(created["id"]),
        profile_service=profile_service,
        source_mode="base_voice",
        synthesize_preview=False,
    )
    assert res_k1_again["voice_signature"]["voice_id"] == vid_1

    # 2. Design from uploaded user voice sample (`user_sample` -> `/api/clone`)
    sample_wav = _make_sine_wav_bytes(180.0, 0.7)
    data_url = "data:audio/wav;base64," + base64.b64encode(sample_wav).decode("ascii")
    res_clone = specialist.design_and_bind_profile_voice(
        profile_service.get_profile(created["id"]),
        profile_service=profile_service,
        source_mode="user_sample",
        sample_audio_base64=data_url,
        sample_filename="narrator_take1.wav",
        ref_text="사건 발생 이십일 년 만에 진실이 드러났습니다.",
        synthesize_preview=True,
    )
    assert res_clone["voice_signature"]["voice_id"] == "cloned-user-sample-voice-001"
    assert res_clone["voice_signature"]["source_mode"] == "user_sample"
    updated_prof = profile_service.get_profile(created["id"])
    assert updated_prof["voice_id"] == "cloned-user-sample-voice-001"
    assert updated_prof["default_voice_id"] == "cloned-user-sample-voice-001"


def test_cross_department_voice_and_edit_rhythm_synchronization(tmp_path: Path) -> None:
    svc = VoiceRhythmSpecialistService()
    noir_dna = svc.analyze_profile_rhythm_dna(
        {"label": "True Crime Noir", "market": "KR", "default_language": "ko", "allowed_topics": "Trọng án hình sự"}
    )
    grace_dna = svc.analyze_profile_rhythm_dna(
        {"label": "Thư Ân Điển & Lời Chúa 60 Phút", "market": "KR", "default_language": "ko", "default_duration_minutes": 60}
    )

    sample_beats = [
        {"beat_id": "B001", "act": 1, "narration": "그날 밤 은행 앞에는 아홉 발의 총성이 울려 퍼졌고 현장은 순식간에 아수라장이 되었습니다."},
        {"beat_id": "B002", "act": 1, "narration": "수송차 문이 열렸고 무장 강도들은 일점오 톤 현금 상자를 거칠게 쓸어 담았습니다."},
        {"beat_id": "B003", "act": 1, "narration": "그런데 이상한 점이 발견되었습니다."},
        {"beat_id": "B004", "act": 1, "narration": "단 육십 초."},
        {"beat_id": "B005", "act": 2, "narration": "이십일 년 뒤 작은 철물점에서 그의 진짜 얼굴이 드러납니다."},
    ]

    pauses_noir = plan_contextual_beat_pauses(sample_beats, vocal_cadence=noir_dna["vocal_cadence"])
    pauses_grace = plan_contextual_beat_pauses(sample_beats, vocal_cadence=grace_dna["vocal_cadence"])

    # Grace contemplative pauses are consistently calmer/longer than Noir action pauses
    assert min(p[0] for p in pauses_grace) >= 0.48
    assert pauses_noir[3][0] >= 1.25  # stark punch `단 육십 초.` gets a deep dramatic landing!

    dir_punch = direct_korean_emotional_prosody({"text": "단 육십 초."}, vocal_cadence=noir_dna["vocal_cadence"])
    assert dir_punch["emotion_register"] == "stark_punch"
    assert dir_punch["beat_speed"] < 0.92

    # Verify `@edit` `build_edit_rhythm_score` locks visual cutting onto `@voice` pauses & registers
    ws = tmp_path / "ws_sync"
    ws.mkdir(parents=True, exist_ok=True)
    voice_manifest = {
        "beats": [
            {"beat_id": "B001", "emotion_register": "urgent_action", "pause_after_sec": 0.26, "pause_reason": "urgent_action_chain"},
            {"beat_id": "B003", "emotion_register": "twist_reveal", "pause_after_sec": 0.90, "pause_reason": "pre_punch_anticipation"},
            {"beat_id": "B004", "emotion_register": "stark_punch", "pause_after_sec": 1.50, "pause_reason": "dramatic_landing"},
            {"beat_id": "B005", "emotion_register": "narrative_flow", "pause_after_sec": 1.92, "pause_reason": "act_transition"},
        ]
    }
    (ws / "voice_manifest.json").write_text(json.dumps(voice_manifest, ensure_ascii=False), encoding="utf-8")

    edit_beats = [{"beat_id": "B001"}, {"beat_id": "B003"}, {"beat_id": "B004"}, {"beat_id": "B005"}]
    job = {"id": "job-sync-1", "rhythm_dna": noir_dna}
    score = build_edit_rhythm_score(job, ws, edit_beats)

    by_id = {b["beat_id"]: b for b in score["beats"]}
    assert by_id["B001"]["cut_feel"] == "rapid_kinetic_cut"
    assert by_id["B001"]["recommended_max_subclip_sec"] <= 3.5

    assert by_id["B003"]["cut_feel"] == "tension_creep_hold"
    assert by_id["B003"]["forbid_mid_silence_cut"] is True

    assert by_id["B004"]["cut_feel"] == "breath_synced_emotional_hold"
    assert by_id["B004"]["hold_through_silence_sec"] == 1.50
    assert by_id["B004"]["forbid_mid_silence_cut"] is True
    assert by_id["B004"]["bgm_breath_lift_db"] > 0.0

    assert by_id["B005"]["cut_feel"] == "chapter_curtain_breath"

    # Prompt injection check across `@script` (`plan`) and `@edit` (`edit`)
    plan_prompt_dir = _profile_rhythm_dna_direction(job, "plan", ws)
    edit_prompt_dir = _profile_rhythm_dna_direction(job, "edit", ws)
    assert "LUẬT NHỊP VIẾT CHO `@script`" in plan_prompt_dir
    assert "BESPOKE CHANNEL EDITING RHYTHM" in edit_prompt_dir
    assert "rapid_kinetic_cut" in edit_prompt_dir
    assert "breath_synced_emotional_hold" in edit_prompt_dir


def test_voice_color_polish_modifies_real_audio_but_skips_silent_fixtures() -> None:
    # Real sine wave gets polished cleanly and remains valid WAV
    sine_wav = _make_sine_wav_bytes(220.0, 0.5)
    polished = apply_voice_color_polish_wav_bytes(sine_wav, {"pitch_semitones": -0.35, "presence_db": 1.1})
    assert polished[:4] == b"RIFF"
    assert len(polished) > 1000

    # Zero-amplitude unit test fixture stays byte-identical
    silent_buf = io.BytesIO()
    with wave.open(silent_buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"\x00\x00" * 12000)
    silent_bytes = silent_buf.getvalue()
    assert apply_voice_color_polish_wav_bytes(silent_bytes, {"pitch_semitones": -0.4, "presence_db": 1.2}) == silent_bytes


def test_all_8_production_profiles_have_unique_1_of_1_voices_and_rhythm_dna() -> None:
    root = Path(__file__).resolve().parents[1]
    profile_service = ChannelProfileService(storage_path=root / "data" / "channel_profiles.json")
    profiles = profile_service.list_profiles()
    assert len(profiles) >= 8

    voice_owner_by_id: dict[str, str] = {}
    archetypes_seen: set[str] = set()
    for p in profiles:
        pid = str(p.get("id") or "").strip()
        vid = str(p.get("voice_id") or "").strip()
        assert vid, f"Profile {pid} is missing voice_id!"
        assert vid == str(p.get("default_voice_id") or "").strip()
        if vid in voice_owner_by_id:
            prev_pid = voice_owner_by_id[vid]
            assert prev_pid in profile_service._sibling_profile_ids(pid), (
                f"Duplicate voice_id {vid} across unrelated profiles {prev_pid} and {pid}!"
            )
        else:
            voice_owner_by_id[vid] = pid

        sig = p.get("voice_signature") or {}
        rhythm = p.get("rhythm_dna") or {}
        assert sig.get("voice_id") == vid
        assert rhythm.get("writing_cadence") and rhythm.get("vocal_cadence") and rhythm.get("editing_cadence")
        archetypes_seen.add(str(rhythm.get("archetype_id")))

        if str(p.get("default_language") or p.get("language") or "").startswith("ko"):
            if str(sig.get("source_mode") or "").strip().lower() == "user_sample":
                assert sig.get("base_voice_id") in {vid, "09c70cc1-cc86-4905-b65b-3967209c3175"}
            else:
                assert sig.get("base_voice_id") == "09c70cc1-cc86-4905-b65b-3967209c3175"

    # All 8 distinct archetypes are represented across the 8 profiles!
    assert len(archetypes_seen) >= 8


def test_core_agent_office_files_remain_100_percent_hangul_free() -> None:
    root = Path(__file__).resolve().parents[1]
    hangul_re = re.compile(r"[\uac00-\ud7a3]")
    for rel in ("documentary/agent_office.py", "static/agent_office.js"):
        text = (root / rel).read_text(encoding="utf-8")
        assert not hangul_re.search(text), f"Hangul leaked into language-agnostic core file {rel}!"


def test_fastapi_voice_specialist_endpoints_and_studio_ui_wiring(tmp_path: Path) -> None:
    from documentary.service import DocumentaryService
    from fastapi.testclient import TestClient
    from server import create_app

    isolated_service = DocumentaryService(tmp_path)
    client = TestClient(create_app(isolated_service))
    r_masters = client.get("/api/voice-specialist/masters")
    assert r_masters.status_code == 200
    masters = r_masters.json()["masters"]
    assert any(m["id"] == "09c70cc1-cc86-4905-b65b-3967209c3175" and m["is_k1_clean_master"] for m in masters)

    r_analyze = client.post(
        "/api/voice-specialist/analyze",
        json={
            "profile": {
                "label": "KR Crime Noir Test",
                "market": "KR",
                "default_language": "ko",
                "allowed_topics": "Trọng án hình sự",
            },
            "custom_direction": "Trầm ấm đêm khuya",
        },
    )
    assert r_analyze.status_code == 200
    body = r_analyze.json()
    rhythm = body.get("rhythm_dna") or body
    assert rhythm["archetype_id"] in {"kr_truecrime_noir_director", "kr_truecrime_forensic_dossier"}
    assert "writing_cadence" in rhythm and "vocal_cadence" in rhythm and "editing_cadence" in rhythm

    r_index = client.get("/")
    assert r_index.status_code == 200
    html = r_index.text
    assert 'id="channelVoiceRhythmStudioBox"' in html
    assert 'id="channelAutoDesignVoiceToggle"' in html
    assert 'id="channelVoiceSourceMode"' in html
    assert 'id="channelBaseMasterVoiceSelect"' in html
    assert 'id="channelVoiceSampleFile"' in html
    assert 'id="designChannelVoiceNowBtn"' in html
