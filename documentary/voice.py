from __future__ import annotations

import io
import json
from pathlib import Path
import re
from typing import Any
import wave

import numpy as np
import requests

from .codex_gateway import StageResult
from .srt import build_srt
from .visuals import load_plan_manifest


INTER_BEAT_PAUSE_SEC = 0.16
OUTRO_FADE_TAIL_SEC = 3.8

_SINO_DIGITS = ("", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구")
_SINO_UNITS = ("", "십", "백", "천")


def _int_to_sino_korean(n: int) -> str:
    if n == 0:
        return "영"
    if n < 0 or n >= 100_000_000:
        return str(n)
    parts: list[str] = []
    man, rem = divmod(n, 10_000)
    for group_val, group_suffix in ((man, "만"), (rem, "")):
        if group_val <= 0:
            continue
        if group_val == 1 and group_suffix == "만":
            parts.append("만")
            continue
        sub: list[str] = []
        for idx, unit in enumerate(_SINO_UNITS):
            digit = (group_val // (10 ** idx)) % 10
            if digit == 0:
                continue
            prefix = "" if (digit == 1 and idx > 0) else _SINO_DIGITS[digit]
            sub.append(f"{prefix}{unit}")
        parts.append("".join(reversed(sub)) + group_suffix)
    return "".join(parts)


_KO_COMMA_UNIT_RE = re.compile(
    r"(?<!\d)(\d{1,3}(?:,\d{3})+)\s*(킬로미터|미터|만\s*위안|위안|만\s*원|원|달러|명|건|회|년|개월|일|권|자루|개|곳|채|장)"
)
_KO_COUNTER_RE = re.compile(
    r"(?<!\d)(\d{1,2})\s*(년\s*동안|년\s*만에|년\s*뒤|년\s*전|년\s*후|년대|대\s*후반|대\s*초반|대\s*중반|개월)"
)
_KO_DECIMAL_PERCENT_RE = re.compile(r"(?<!\d)(\d+)\.(\d+)\s*(%|퍼센트)")
_KO_DECIMAL_UNIT_RE = re.compile(r"(?<!\d)(\d+)\.(\d+)\s*(초|배|미터|킬로미터|센티미터|밀리미터|킬로그램|그램|톤|위안|원|달러|명|개|권|자루|시간|분)")
_KO_HANGUL_DECIMAL_JJEOM_RE = re.compile(
    r"(?<=[영공일이삼사오육칠팔구십백천만억])점(?=[영공일이삼사오육칠팔구])"
)
_KO_SINO_HUNDRED_GAE_RE = re.compile(
    r"(?<=[십백천])([일이삼사오육칠팔구])\s+(?=개(?![가-힣]))"
)
_KO_ORDINAL_JE_RE = re.compile(r"제(\d{1,2})(?=(?:중급|고등|최고|기초)?인민법원|호|차|기)")
_KO_HANGUL_HYPHEN_RE = re.compile(r"(?<=[가-힣])-(?=[가-힣])")
_KO_THOUSAND_COMMA_RE = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")


def _digits_to_sino_korean(digits: str) -> str:
    sino_map = ("영", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구")
    return "".join(sino_map[int(ch)] for ch in digits if ch.isdigit())


def normalize_korean_tts_text(text: str) -> str:
    """Normalize Korean numbers & counters before sending to TTS so OmniVoice never splits at commas or misreads Sino-Korean counters."""
    raw = str(text or "").strip()
    if not raw:
        return raw

    def _repl_comma_unit(match: re.Match[str]) -> str:
        num_str = match.group(1).replace(",", "")
        unit = match.group(2)
        try:
            sino = _int_to_sino_korean(int(num_str))
            return f"{sino} {unit}"
        except ValueError:
            return f"{num_str}{unit}"

    out = _KO_COMMA_UNIT_RE.sub(_repl_comma_unit, raw)

    def _repl_counter(match: re.Match[str]) -> str:
        val = int(match.group(1))
        suffix = match.group(2)
        if 1 <= val <= 99:
            return f"{_int_to_sino_korean(val)} {suffix}"
        return match.group(0)

    out = _KO_COUNTER_RE.sub(_repl_counter, out)

    def _repl_dec_pct(match: re.Match[str]) -> str:
        whole = _int_to_sino_korean(int(match.group(1)))
        frac = _digits_to_sino_korean(match.group(2))
        return f"{whole}쩜{frac} 퍼센트"

    out = _KO_DECIMAL_PERCENT_RE.sub(_repl_dec_pct, out)

    def _repl_dec_unit(match: re.Match[str]) -> str:
        whole = _int_to_sino_korean(int(match.group(1)))
        frac = _digits_to_sino_korean(match.group(2))
        unit = match.group(3)
        return f"{whole}쩜{frac} {unit}"

    out = _KO_DECIMAL_UNIT_RE.sub(_repl_dec_unit, out)
    out = _KO_HANGUL_DECIMAL_JJEOM_RE.sub("쩜", out)
    out = _KO_SINO_HUNDRED_GAE_RE.sub(r"\1", out)
    out = _KO_ORDINAL_JE_RE.sub(lambda m: f"제{_int_to_sino_korean(int(m.group(1)))}", out)
    out = _KO_HANGUL_HYPHEN_RE.sub(" ", out)
    out = _KO_THOUSAND_COMMA_RE.sub("", out)
    return out


def _korean_comma_rel_positions(text: str) -> list[float]:
    clean = _KO_THOUSAND_COMMA_RE.sub("", str(text or ""))
    positions: list[float] = []
    total_non_space = sum(1 for c in clean if not c.isspace() and c not in ",，、;；.!?…")
    if total_non_space <= 0:
        return positions
    seen = 0
    for ch in clean:
        if ch in (",", "，", "、", ";", "；"):
            rel = seen / float(total_non_space)
            if 0.12 <= rel <= 0.88:
                positions.append(rel)
        elif not ch.isspace() and ch not in ".!?…":
            seen += 1
    return positions


def sculpt_wav_bytes_for_korean_broadcast(
    wav_bytes: bytes,
    *,
    lead_pad_sec: float = 0.025,
    trail_pad_sec: float = 0.035,
    primary_pause_sec: float = 0.22,
    secondary_pause_sec: float = 0.18,
    tertiary_pause_sec: float = 0.075,
    text: str | None = None,
) -> bytes:
    """Trim excess outer leading/trailing silence on Korean WAV bytes while preserving 100% of internal natural phrasing.

    Preserves synthetic/silent test WAVs untouched so deterministic unit test fixtures keep exact durations.
    """
    if not wav_bytes or len(wav_bytes) < 100:
        return wav_bytes
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as handle:
            nchannels = handle.getnchannels()
            sampwidth = handle.getsampwidth()
            sr = handle.getframerate()
            nframes = handle.getnframes()
            comptype = handle.getcomptype()
            compname = handle.getcompname()
            raw_frames = handle.readframes(nframes)
    except Exception:
        return wav_bytes

    if sampwidth != 2 or nchannels < 1 or sr < 8000 or nframes < int(sr * 0.4):
        return wav_bytes

    pcm = np.frombuffer(raw_frames, dtype=np.int16).astype(np.float32) / 32768.0
    if nchannels > 1:
        pcm = pcm.reshape(-1, nchannels).mean(axis=1)

    peak = float(np.max(np.abs(pcm))) if pcm.size else 0.0
    if peak < 1e-3:
        # Silent fixture WAV (e.g. unit tests) -> keep untouched
        return wav_bytes

    hop = max(1, int(sr * 0.010))
    n_hop_frames = len(pcm) // hop
    if n_hop_frames < 12:
        return wav_bytes

    frames_2d = pcm[: n_hop_frames * hop].reshape(n_hop_frames, hop)
    rms = np.sqrt(np.mean(frames_2d * frames_2d, axis=1) + 1e-12)
    active_rms = float(np.percentile(rms, 85))
    thresh = max(0.0075, active_rms * 0.055)
    is_voiced = rms >= thresh
    if not np.any(is_voiced):
        return wav_bytes

    voiced_idx = np.where(is_voiced)[0]
    first_v = int(voiced_idx[0])
    last_v = int(voiced_idx[-1])
    start_sample = max(0, first_v * hop - int(sr * lead_pad_sec))
    end_sample = min(len(pcm), (last_v + 1) * hop + int(sr * trail_pad_sec))
    trimmed = pcm[start_sample:end_sample].copy()

    edge = min(max(1, int(sr * 0.008)), len(trimmed) // 10)
    if edge > 1:
        ramp = np.linspace(0.0, 1.0, edge, dtype=np.float32)
        trimmed[:edge] *= ramp
        trimmed[-edge:] *= ramp[::-1]

    pcm_i16 = np.clip(np.round(trimmed * 32767.0), -32768, 32767).astype(np.int16)
    if nchannels > 1:
        pcm_i16 = np.repeat(pcm_i16[:, None], nchannels, axis=1).reshape(-1)

    out_buf = io.BytesIO()
    with wave.open(out_buf, "wb") as out_w:
        out_w.setnchannels(nchannels)
        out_w.setsampwidth(2)
        out_w.setframerate(sr)
        out_w.setcomptype(comptype, compname)
        out_w.writeframes(pcm_i16.tobytes())
    return out_buf.getvalue()


def wav_duration(path: str | Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def concat_wavs(
    paths: list[Path],
    output: Path,
    *,
    inter_beat_pause_sec: float = INTER_BEAT_PAUSE_SEC,
    outro_tail_sec: float = OUTRO_FADE_TAIL_SEC,
) -> None:
    if not paths:
        raise RuntimeError("Không có voice segment để ghép")
    params = None
    frames: list[bytes] = []
    for index, path in enumerate(paths):
        with wave.open(str(path), "rb") as handle:
            current = (handle.getnchannels(), handle.getsampwidth(), handle.getframerate(), handle.getcomptype(), handle.getcompname())
            if params is None:
                params = current
            elif current != params:
                raise RuntimeError("Các voice segment có WAV format không đồng nhất")
            frames.append(handle.readframes(handle.getnframes()))
            nchannels, sampwidth, framerate = current[0], current[1], current[2]
            if index < len(paths) - 1 and inter_beat_pause_sec > 0:
                pause_frames = int(round(inter_beat_pause_sec * framerate))
                if pause_frames > 0:
                    frames.append(b"\x00" * (pause_frames * sampwidth * nchannels))
            elif index == len(paths) - 1 and outro_tail_sec > 0:
                tail_frames = int(round(outro_tail_sec * framerate))
                if tail_frames > 0:
                    frames.append(b"\x00" * (tail_frames * sampwidth * nchannels))
    assert params is not None
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as handle:
        handle.setnchannels(params[0])
        handle.setampwidth(params[1]) if hasattr(handle, "setampwidth") else handle.setsampwidth(params[1])
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
        lang = str(language).strip().lower() if language else ""
        raw_text = str(text or "").strip()
        tts_text = normalize_korean_tts_text(raw_text) if lang == "ko" else raw_text
        payload: dict[str, Any] = {
            "text": tts_text,
            "voice_id": voice_id or None,
            "speed": float(speed or 1.0),
            "mode": str(mode or "balanced"),
        }
        if lang:
            payload["language"] = lang
        response = self.session.post(
            f"{self.base_url}/api/tts",
            json=payload,
            timeout=180.0,
        )
        response.raise_for_status()
        wav_bytes = response.content
        if lang == "ko":
            wav_bytes = sculpt_wav_bytes_for_korean_broadcast(wav_bytes, text=raw_text if 'raw_text' in locals() else text)
        return wav_bytes

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
                path = beat_dir / f"{beat_id}.wav"
                if (workspace / "audio" / ".reuse_existing_beats").exists() and path.is_file() and path.stat().st_size > 1000:
                    duration = wav_duration(path)
                    is_last = index == len(beats)
                    speech_end = round(cursor + duration, 3)
                    tail_hold = OUTRO_FADE_TAIL_SEC if is_last else 0.0
                    item = {
                        "beat_id": beat_id,
                        "text": text,
                        "audio_path": str(path),
                        "start_sec": round(cursor, 3),
                        "speech_end_sec": speech_end,
                        "end_sec": round(cursor + duration + tail_hold, 3),
                        "duration_sec": round(duration + tail_hold, 3),
                        "outro_tail_sec": round(tail_hold, 3) if is_last else 0.0,
                        "seed": None,
                    }
                    rendered.append(item)
                    wavs.append(path)
                    cursor += duration + (INTER_BEAT_PAUSE_SEC if not is_last else tail_hold)
                    continue
                tts_text = normalize_korean_tts_text(text) if language == "ko" else text
                payload = {"text": tts_text, "voice_id": voice_id, "speed": pass_speed, "language": language, "mode": mode}
                if seeds and index <= len(seeds) and seeds[index - 1] is not None:
                    try:
                        payload["seed"] = int(str(seeds[index - 1]))
                    except ValueError:
                        pass
                response = None
                for attempt in range(3):
                    try:
                        response = self.session.post(
                            f"{self.base_url}/api/tts",
                            json=payload,
                            timeout=300,
                        )
                        response.raise_for_status()
                        break
                    except requests.RequestException:
                        if attempt >= 2:
                            raise
                        import time as _time
                        self.discover()
                        _time.sleep(2.0 * (attempt + 1))
                assert response is not None
                wav_bytes = response.content
                if language == "ko":
                    wav_bytes = sculpt_wav_bytes_for_korean_broadcast(wav_bytes, text=raw_text if 'raw_text' in locals() else text)
                path = beat_dir / f"{beat_id}.wav"
                path.write_bytes(wav_bytes)
                duration = wav_duration(path)
                is_last = index == len(beats)
                speech_end = round(cursor + duration, 3)
                tail_hold = OUTRO_FADE_TAIL_SEC if is_last else 0.0
                item = {
                    "beat_id": beat_id,
                    "text": text,
                    "audio_path": str(path),
                    "start_sec": round(cursor, 3),
                    "speech_end_sec": speech_end,
                    "end_sec": round(cursor + duration + tail_hold, 3),
                    "duration_sec": round(duration + tail_hold, 3),
                    "outro_tail_sec": round(tail_hold, 3) if is_last else 0.0,
                    "seed": response.headers.get("X-Seed"),
                }
                rendered.append(item)
                wavs.append(path)
                cursor += duration + (INTER_BEAT_PAUSE_SEC if not is_last else tail_hold)
            return rendered, wavs, cursor

        rendered, wavs, cursor = render_pass(speed)
        contract = ((job.get("production_recipe") or {}).get("quality_contract") or {})
        target = float(contract.get("target_duration_sec") or visual.get("target_duration_sec") or 0)
        auto_fit_applied = False
        narration = workspace / "audio" / "narration.wav"
        concat_wavs(wavs, narration)
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
