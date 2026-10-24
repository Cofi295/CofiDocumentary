from __future__ import annotations

import json
from pathlib import Path
import wave
from typing import Any

import requests

from .codex_gateway import StageResult
from .srt import build_srt
from .visuals import load_plan_manifest


def wav_duration(path: str | Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def concat_wavs(paths: list[Path], output: Path) -> None:
    if not paths:
        raise RuntimeError("Không có voice segment để ghép")
    params = None
    frames: list[bytes] = []
    for path in paths:
        with wave.open(str(path), "rb") as handle:
            current = (handle.getnchannels(), handle.getsampwidth(), handle.getframerate(), handle.getcomptype(), handle.getcompname())
            if params is None:
                params = current
            elif current != params:
                raise RuntimeError("Các voice segment có WAV format không đồng nhất")
            frames.append(handle.readframes(handle.getnframes()))
    assert params is not None
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as handle:
        handle.setnchannels(params[0])
        handle.setsampwidth(params[1])
        handle.setframerate(params[2])
        handle.setcomptype(params[3], params[4])
        for chunk in frames:
            handle.writeframes(chunk)


def pad_wav_to_duration(path: Path, target_duration: float) -> None:
    """Pad narration tail when the generated script is shorter than the timeline.

    Voice quality gate requires the audio timeline to match the production
    contract.  We only add silence at the end; we never stretch or alter the
    generated speech.
    """
    if target_duration <= 0:
        return
    with wave.open(str(path), "rb") as handle:
        params = handle.getparams()
        frames = handle.readframes(handle.getnframes())
        current = len(frames) / float(params.framerate * params.sampwidth * params.nchannels)
    missing = target_duration - current
    if missing <= 0:
        return
    with wave.open(str(path), "wb") as handle:
        handle.setparams(params)
        handle.writeframes(frames)
        silence_frames = int(missing * params.framerate)
        handle.writeframes(b"\x00" * silence_frames * params.sampwidth * params.nchannels)


VOICE_LANGUAGE_META: dict[str, dict[str, str]] = {
    "vi": {"country_code": "VN", "country_label": "Việt Nam", "language_label": "Tiếng Việt", "flag": "🇻🇳"},
    "en": {"country_code": "US", "country_label": "Mỹ / Anh", "language_label": "English", "flag": "🇺🇸"},
    "ko": {"country_code": "KR", "country_label": "Hàn Quốc", "language_label": "한국어", "flag": "🇰🇷"},
    "ja": {"country_code": "JP", "country_label": "Nhật Bản", "language_label": "日本語", "flag": "🇯🇵"},
    "zh": {"country_code": "CN", "country_label": "Trung Quốc", "language_label": "中文", "flag": "🇨🇳"},
    "fr": {"country_code": "FR", "country_label": "Pháp", "language_label": "Français", "flag": "🇫🇷"},
    "de": {"country_code": "DE", "country_label": "Đức", "language_label": "Deutsch", "flag": "🇩🇪"},
    "es": {"country_code": "ES", "country_label": "Tây Ban Nha", "language_label": "Español", "flag": "🇪🇸"},
    "pt": {"country_code": "BR", "country_label": "Bồ Đào Nha / Brazil", "language_label": "Português", "flag": "🇧🇷"},
    "ru": {"country_code": "RU", "country_label": "Nga", "language_label": "Русский", "flag": "🇷🇺"},
    "th": {"country_code": "TH", "country_label": "Thái Lan", "language_label": "ไทย", "flag": "🇹🇭"},
    "id": {"country_code": "ID", "country_label": "Indonesia", "language_label": "Bahasa Indonesia", "flag": "🇮🇩"},
    "hi": {"country_code": "IN", "country_label": "Ấn Độ", "language_label": "हिन्दी", "flag": "🇮🇳"},
    "it": {"country_code": "IT", "country_label": "Ý", "language_label": "Italiano", "flag": "🇮🇹"},
}


def enrich_voice_entry(entry: dict[str, Any]) -> dict[str, Any]:
    lang = str(entry.get("language") or "en").strip().lower()
    meta = VOICE_LANGUAGE_META.get(
        lang,
        {"country_code": lang.upper(), "country_label": lang.upper(), "language_label": lang.upper(), "flag": "🌐"},
    )
    voice_id = str(entry.get("id") or "").strip()
    raw_preview = entry.get("preview_url")
    return {
        **entry,
        "language": lang,
        "country_code": meta["country_code"],
        "country_label": meta["country_label"],
        "language_label": meta["language_label"],
        "flag": meta["flag"],
        "proxy_preview_url": f"/api/voice/preview-audio/{voice_id}" if (voice_id and raw_preview) else None,
    }


class CofiVoiceEngine:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", session: Any | None = None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def health(self) -> dict[str, Any]:
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=1.0)
            payload: dict[str, Any] = {}
            if response.ok and hasattr(response, "json"):
                try:
                    raw = response.json()
                    if isinstance(raw, dict):
                        payload = raw
                except ValueError:
                    payload = {}
            return {**payload, "ok": response.ok, "url": self.base_url, "status_code": response.status_code}
        except requests.RequestException as exc:
            return {"ok": False, "url": self.base_url, "error": str(exc)}

    def discover(self, candidates: list[str] | None = None) -> dict[str, Any]:
        original = self.base_url
        urls = [original, *(candidates or ["http://127.0.0.1:8000", "http://127.0.0.1:8776"])]
        seen: set[str] = set()
        last: dict[str, Any] | None = None
        for value in urls:
            base_url = str(value or "").strip().rstrip("/")
            if not base_url or base_url in seen:
                continue
            seen.add(base_url)
            self.base_url = base_url
            last = self.health()
            if last.get("ok"):
                return last
        self.base_url = original
        return last or self.health()

    def voices(self) -> list[dict[str, Any]]:
        response = self.session.get(f"{self.base_url}/api/voices", timeout=4.0)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            return []
        return [enrich_voice_entry(item) for item in data if isinstance(item, dict)]

    def clone_voice(
        self,
        *,
        name: str,
        language: str,
        audio_bytes: bytes,
        filename: str = "sample.wav",
        ref_text: str | None = None,
        recorded: bool = False,
        auto_preview: bool = True,
    ) -> dict[str, Any]:
        form_data: dict[str, Any] = {
            "name": str(name or "").strip(),
            "language": str(language or "en").strip().lower(),
            "recorded": "true" if recorded else "false",
        }
        if ref_text and str(ref_text).strip():
            form_data["ref_text"] = str(ref_text).strip()
        files = {
            "ref_audio": (filename or "sample.wav", audio_bytes, "application/octet-stream"),
        }
        response = self.session.post(
            f"{self.base_url}/api/clone",
            data=form_data,
            files=files,
            timeout=240.0,
        )
        response.raise_for_status()
        created = response.json()
        if not isinstance(created, dict):
            raise RuntimeError("CofiVoice không trả về thông tin giọng clone hợp lệ")
        if auto_preview and created.get("id"):
            try:
                prev = self.generate_preview(str(created["id"]))
                if prev.get("preview_url"):
                    created["preview_url"] = prev["preview_url"]
            except Exception:
                pass
        return enrich_voice_entry(created)

    def design_voice(
        self,
        *,
        name: str,
        language: str,
        instruct: str,
        auto_preview: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "name": str(name or "").strip(),
            "language": str(language or "en").strip().lower(),
            "instruct": str(instruct or "").strip(),
        }
        response = self.session.post(
            f"{self.base_url}/api/design",
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        created = response.json()
        if not isinstance(created, dict):
            raise RuntimeError("CofiVoice không trả về thông tin giọng thiết kế hợp lệ")
        if auto_preview and created.get("id"):
            try:
                prev = self.generate_preview(str(created["id"]))
                if prev.get("preview_url"):
                    created["preview_url"] = prev["preview_url"]
            except Exception:
                pass
        return enrich_voice_entry(created)

    def generate_preview(self, voice_id: str) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/api/voices/{voice_id}/preview",
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        raw_url = data.get("preview_url") if isinstance(data, dict) else None
        return {
            "voice_id": voice_id,
            "preview_url": raw_url,
            "proxy_preview_url": f"/api/voice/preview-audio/{voice_id}",
        }

    def synthesize_preview(
        self,
        *,
        text: str,
        voice_id: str | None = None,
        language: str | None = None,
        speed: float = 1.0,
        mode: str = "balanced",
    ) -> bytes:
        payload: dict[str, Any] = {
            "text": str(text or "").strip(),
            "voice_id": voice_id or None,
            "speed": float(speed or 1.0),
            "mode": str(mode or "balanced"),
        }
        if language:
            payload["language"] = str(language).strip().lower()
        response = self.session.post(
            f"{self.base_url}/api/tts",
            json=payload,
            timeout=180.0,
        )
        response.raise_for_status()
        return response.content

    def delete_voice(self, voice_id: str) -> dict[str, Any]:
        response = self.session.delete(
            f"{self.base_url}/api/voices/{voice_id}",
            timeout=15.0,
        )
        response.raise_for_status()
        return {"deleted": True, "voice_id": voice_id}

    def run(self, job: dict[str, Any], workspace: str | Path) -> StageResult:
        workspace = Path(workspace)
        visual = load_plan_manifest(workspace)
        beats = [item for item in (visual.get("beats") or []) if isinstance(item, dict)]
        voice_cfg = job.get("voice") if isinstance(job.get("voice"), dict) else {}
        voice_id = voice_cfg.get("voice_id") or None
        speed = float(voice_cfg.get("speed") or 1.0)
        mode = str(voice_cfg.get("mode") or "balanced")
        language = str(job.get("language") or "ko")
        beat_dir = workspace / "audio" / "beats"
        beat_dir.mkdir(parents=True, exist_ok=True)
        requested_speed = speed

        def render_pass(pass_speed: float, seeds: list[str | None] | None = None):
            rendered: list[dict[str, Any]] = []
            wavs: list[Path] = []
            cursor = 0.0
            for index, beat in enumerate(beats, start=1):
                stop_sentinel = workspace / "audio" / ".stop_voice"
                if stop_sentinel.exists():
                    try:
                        stop_sentinel.unlink()
                    except OSError:
                        pass
                    raise RuntimeError("Đã dừng tạo voice theo yêu cầu để đổi giọng đọc.")
                beat_id = str(beat.get("beat_id") or f"B{index:03d}")
                text = str(beat.get("narration_text") or beat.get("text") or "").strip()
                if not text:
                    raise RuntimeError(f"Beat {beat_id} không có narration_text")
                payload = {"text": text, "voice_id": voice_id, "speed": pass_speed, "language": language, "mode": mode}
                if seeds and index <= len(seeds) and seeds[index - 1] is not None:
                    try:
                        payload["seed"] = int(str(seeds[index - 1]))
                    except ValueError:
                        pass
                response = None
                last_exc: Exception | None = None
                for attempt in range(3):
                    try:
                        response = self.session.post(
                            f"{self.base_url}/api/tts",
                            json=payload,
                            timeout=300,
                        )
                        response.raise_for_status()
                        break
                    except requests.RequestException as exc:
                        last_exc = exc
                        if attempt >= 2:
                            raise
                        import time as _time
                        self.discover()
                        _time.sleep(2.0 * (attempt + 1))
                assert response is not None
                path = beat_dir / f"{beat_id}.wav"
                path.write_bytes(response.content)
                duration = wav_duration(path)
                item = {
                    "beat_id": beat_id,
                    "text": text,
                    "audio_path": str(path),
                    "start_sec": round(cursor, 3),
                    "end_sec": round(cursor + duration, 3),
                    "duration_sec": round(duration, 3),
                    "seed": response.headers.get("X-Seed"),
                }
                rendered.append(item)
                wavs.append(path)
                cursor += duration
            return rendered, wavs, cursor

        rendered, wavs, cursor = render_pass(speed)
        contract = ((job.get("production_recipe") or {}).get("quality_contract") or {})
        target = float(contract.get("target_duration_sec") or visual.get("target_duration_sec") or 0)
        auto_fit_applied = False
        # Không ép TTS kéo giãn để khớp đúng target_duration. Target chỉ là mốc
        # tham khảo cho production; nếu script ngắn thì phải sửa script trước,
        # không được làm giọng đọc chậm/méo để biến 43s thành 120s.
        # Giữ lại metadata để UI biết mức lệch và xử lý ở bước script.
        narration = workspace / "audio" / "narration.wav"
        concat_wavs(wavs, narration)
        # target_duration_sec is an estimate for planning. Keep the real TTS
        # length so subtitles, edit timeline and footage follow the generated
        # narration instead of forcing silence padding to hit a preset number.
        manifest = {
            "engine": "CofiVoice",
            "voice_id": voice_id,
            "language": language,
            "speed": speed,
            "requested_speed": requested_speed,
            "auto_fit_applied": auto_fit_applied,
            "target_duration_sec": target,
            "duration_delta_sec": round(cursor - target, 3) if target else None,
            "duration_sec": round(cursor, 3),
            "narration_path": str(narration),
            "beats": rendered,
        }
        (workspace / "voice_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (workspace / "subtitles.srt").write_text(build_srt(rendered), encoding="utf-8")
        return StageResult(returncode=0, last_message=f"Đã tạo voice cho {len(rendered)} visual beat, tổng {cursor:.1f}s", log_path=workspace / "voice_manifest.json")

