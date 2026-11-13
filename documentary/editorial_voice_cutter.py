"""
Editorial Voice Cutter & Atomic Timeline Re-Sync Engine (`@edit` Soul Layer).

Empowers Step 6 (`@edit`) across ALL documentary niches and languages (`ko`, `en`, `vi`,
`ja`, `zh`, `de`, `fr`, `es`) to cut, space, and hold voice stems like a seasoned human
film editor while keeping 100% channel voice consistency:

1. Non-destructive 1st-generation stem backup (`audio/beats_raw/` + `voice_manifest.raw.json`)
   so re-cuts and CLI overrides are 100% lossless and idempotent (never regenerates TTS).
2. Cold-Open Pre-Voice World-Building Breath (`cold_open_pre_voice_sec`): opens frame 0
   with picture + atmosphere before Word 1 is spoken.
3. Intentional Inter-Beat Breathing Room & Kinetic Action Shaving (`pause_overrides`):
   expands chapter curtains, twists, `CINEMA_TEXT` paradoxes, and human tragedies while
   tightening urgent action streaks (with fatigue-guard recovery breaths).
4. Surgical Mid-Beat Zero-Crossing Caesura Splits (`mid_beat_caesuras`): slices a beat's
   PCM WAV at a Whisper word boundary + acoustic RMS valley + zero-crossing with 10ms
   cosine micro-tapers, inserting a dramatic breath right before a mid-sentence reveal
   without spoiling the twist in `subtitles.srt`.
5. Atomic synchronization across `audio/narration.wav`, `voice_manifest.json`,
   `subtitles.srt`, `visual_manifest.json`, `editorial_voice_plan.json`, and
   `CofiRemotion/public/jobs/<job_id>/`.

CLI Usage for `@edit`:
  python -m documentary.editorial_voice_cutter --workspace <dir> --inspect
  python -m documentary.editorial_voice_cutter --workspace <dir> --auto
  python -m documentary.editorial_voice_cutter --workspace <dir> --set-pause B024=2.25:chapter_curtain
  python -m documentary.editorial_voice_cutter --workspace <dir> --set-caesura B042:before="백지":hold=0.78
  python -m documentary.editorial_voice_cutter --workspace <dir> --pre-voice 1.40
  python -m documentary.editorial_voice_cutter --workspace <dir> --reset
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import shutil
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .srt import build_srt
from .voice import OUTRO_FADE_TAIL_SEC, measure_wav_acoustic_edges, wav_duration

FPS_DEFAULT = 30

# Multi-language mid-sentence pivot phrases where a human editor naturally holds a breath before the reveal
_CAESURA_PIVOT_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Korean
    re.compile(r"(?:,\s*|\s+)(단\s*한\s*|단\s*하나|오직\s+|정작\s+|사실은\s+|진실은\s+|결국\s+|그\s*정체는|발견된\s*것은|남아\s*있던\s*건|드러난\s*것은|전혀\s*다른)"),
    # English
    re.compile(r"(?:,\s+|—\s+|\s+)(turned\s+out\s+to\s+be|nothing\s+at\s+all|only\s+a\s+single|was\s+actually|in\s+reality|never\s+existed|what\s+they\s+found|one\s+fatal)", re.IGNORECASE),
    # Vietnamese
    re.compile(r"(?:,\s+|—\s+|\s+)(thực\s+chất\s+lại\s+là|sự\s+thật\s+lại\s+là|chỉ\s+vỏn\s+vẹn|hoàn\s+toàn\s+trống\s+rỗng|kẻ\s+đứng\s+sau|thứ\s+duy\s+nhất|chưa\s+từng\s+tồn\s+tại)", re.IGNORECASE),
    # Japanese
    re.compile(r"(?:、\s*|\s+)(実は|たった一つ|残されていたのは|真実は|正体は)"),
)

_TWIST_TAIL_MARKERS: tuple[str, ...] = (
    "뿐이었습니다", "없었습니다", "거짓이었습니다", "사라졌습니다", "증발했습니다", "동일인이었습니다",
    "걸까요?", "었을까요?", "무엇이었을까요?",
    "nothing inside", "never existed", "completely empty", "vanished", "same person",
    "trống rỗng", "biến mất", "không hề tồn tại", "cùng một người", "chí mạng",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _beat_id(item: dict[str, Any]) -> str:
    return str(item.get("beat_id") or item.get("id") or "").strip()


def _pause_jitter_for(seed_key: str, spread: float = 0.14) -> float:
    """Return a deterministic signed micro-variation in `[-spread, +spread]` seconds so
    major dramatic pauses breathe organically (`1.12s..1.68s`) rather than clamping to
    an identical `1.40s` or `1.49s` constant across the episode.
    """
    digest = hashlib.md5(str(seed_key or "beat").encode("utf-8")).hexdigest()[:8]
    unit = (int(digest, 16) / float(0xFFFFFFFF)) * 2.0 - 1.0
    return round(unit * float(spread), 3)


def compute_editorial_pause_plan(
    beats: list[dict[str, Any]],
    *,
    craft: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Compute an organic, non-clamped pause plan across `beats` (Sub-Role 3A).

    Ensures major pauses (>= 0.85s) vary naturally across `1.12s..1.68s` based on
    beat identity and sentence character weight rather than collapsing to a single
    `1.40s` / `1.49s` constant.
    """
    craft = craft or {}
    chapter_breath = max(1.60, min(2.20, float(craft.get("chapter_curtain_breath_sec") or 1.85)))
    twist_breath = max(1.18, min(1.60, float(craft.get("twist_reveal_breath_sec") or 1.38)))
    somber_breath = max(1.22, min(1.60, float(craft.get("somber_aftermath_breath_sec") or 1.44)))
    plan: list[dict[str, Any]] = []
    for idx, b in enumerate(beats):
        bid = _beat_id(b) or f"B{idx + 1:03d}"
        txt = str(b.get("text") or b.get("narration_text") or "").strip()
        raw_p = float(b.get("pause_after_sec") or b.get("post_pause_sec") or 0.38)
        emo = str(b.get("emotion_register") or "narrative_flow")
        reason = str(b.get("pause_reason") or "standard_narrative")
        char_weight = min(0.08, max(-0.06, (len(txt) - 32) * 0.002))
        jitter = _pause_jitter_for(f"{bid}:{idx}:{txt[:16]}", spread=0.14)
        if reason in ("act_transition", "editorial_chapter_curtain_breath"):
            p_sec = round(max(1.48, min(2.15, chapter_breath + jitter + char_weight)), 3)
        elif raw_p >= 0.85 or txt.endswith(("?", "？")) or emo in ("twist_reveal", "suspense_question", "somber_tragedy"):
            base_hold = somber_breath if emo == "somber_tragedy" else twist_breath
            p_sec = round(max(1.12, min(1.68, base_hold + jitter + char_weight)), 3)
        elif emo in ("urgent_action", "stark_punch"):
            p_sec = round(max(0.28, min(0.42, 0.33 + _pause_jitter_for(f"fast:{bid}:{idx}", spread=0.04))), 3)
        else:
            p_sec = round(max(0.28, min(0.48, raw_p + _pause_jitter_for(f"std:{bid}:{idx}", spread=0.04))), 3)
        plan.append({"beat_id": bid, "pause_after_sec": p_sec, "pause_reason": reason})
    return plan


def _is_non_silent_speech_wav(path: Path) -> bool:
    """Return True if `path` contains real non-zero PCM signal (false on unit-test zero-byte/zero-PCM fixtures)."""
    if not path.is_file():
        return False
    try:
        with wave.open(str(path), "rb") as wf:
            nframes = wf.getnframes()
            sr = wf.getframerate()
            sw = wf.getsampwidth()
            if nframes <= 0 or sr <= 0 or sw != 2:
                return False
            probe = wf.readframes(min(nframes, sr * 3))
        arr = np.frombuffer(probe, dtype=np.int16)
        return bool(arr.size > 0 and int(np.max(np.abs(arr))) >= 35)
    except Exception:
        return False


def _load_overrides(workspace: Path) -> dict[str, Any]:
    ov_path = workspace / "editorial_voice_overrides.json"
    if not ov_path.is_file():
        return {"pre_voice_sec": None, "pauses": {}, "caesuras": {}, "disabled_caesuras": []}
    try:
        data = json.loads(ov_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("pre_voice_sec", None)
            data.setdefault("pauses", {})
            data.setdefault("caesuras", {})
            data.setdefault("disabled_caesuras", [])
            return data
    except Exception:
        pass
    return {"pre_voice_sec": None, "pauses": {}, "caesuras": {}, "disabled_caesuras": []}


def _save_overrides(workspace: Path, overrides: dict[str, Any]) -> Path:
    ov_path = workspace / "editorial_voice_overrides.json"
    ov_path.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")
    return ov_path


def _ensure_raw_stem_backup(workspace: Path, current_manifest: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    """Ensure clean 1st-generation stems & manifest exist in `audio/beats_raw/` + `voice_manifest.raw.json`."""
    raw_dir = workspace / "audio" / "beats_raw"
    raw_manifest_path = workspace / "voice_manifest.raw.json"
    already_sculpted = bool(current_manifest.get("editorial_voice_sculpted"))

    if already_sculpted and raw_manifest_path.is_file() and raw_dir.is_dir():
        raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
        return raw_manifest, raw_dir

    # Fresh output from Step 2 (@voice) -> snapshot 1st-gen stems cleanly
    raw_dir.mkdir(parents=True, exist_ok=True)
    snap = copy.deepcopy(current_manifest)
    snap.pop("editorial_voice_sculpted", None)
    snap.pop("editorial_summary", None)
    snap.pop("pre_voice_breath_sec", None)

    beats_dir = workspace / "audio" / "beats"
    for b in snap.get("beats") or []:
        if not isinstance(b, dict):
            continue
        bid = _beat_id(b)
        src_p = Path(str(b.get("audio_path") or (beats_dir / f"{bid}.wav")))
        if not src_p.is_file():
            alt = beats_dir / f"{bid}.wav"
            if alt.is_file():
                src_p = alt
        if src_p.is_file():
            dst_p = raw_dir / f"{bid}.wav"
            shutil.copy2(src_p, dst_p)
            b["raw_audio_path"] = str(dst_p)
        b.pop("editorial_caesuras", None)
        b.pop("editorial_speech_segments", None)

    raw_manifest_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    return snap, raw_dir


def find_zero_crossing_split_sample(
    pcm_mono: np.ndarray,
    sr: int,
    target_sec: float,
    *,
    search_radius_sec: float = 0.14,
    require_quiet_valley: bool = True,
) -> tuple[int | None, float]:
    """Locate the cleanest acoustic valley + zero-crossing sample near `target_sec`.

    Returns `(sample_index_or_None, valley_ratio_vs_p85)`.
    """
    n = int(pcm_mono.shape[0])
    if n < int(sr * 0.5) or sr <= 0:
        return None, 1.0

    abs_f = np.abs(pcm_mono.astype(np.float32))
    hop = max(1, int(sr * 0.010))  # 10ms RMS frames
    n_hops = n // hop
    if n_hops < 10:
        return None, 1.0

    framed = pcm_mono[: n_hops * hop].astype(np.float32).reshape(n_hops, hop)
    rms = np.sqrt(np.mean(framed * framed, axis=1) + 1e-9)
    p85 = float(np.percentile(rms, 85)) if rms.size else 0.0
    if p85 < 15.0:
        # Silent synthetic buffer -> split right on target_sec sample
        idx = max(int(sr * 0.15), min(n - int(sr * 0.15), int(round(target_sec * sr))))
        return idx, 0.0

    lo_sec = max(0.20, target_sec - search_radius_sec)
    hi_sec = min((n / float(sr)) - 0.20, target_sec + search_radius_sec)
    if hi_sec <= lo_sec:
        return None, 1.0

    lo_h = max(1, int(lo_sec / 0.010))
    hi_h = min(n_hops - 2, int(hi_sec / 0.010))
    if hi_h <= lo_h:
        return None, 1.0

    # Smooth over 30ms so micro-clicks don't fool the valley detector
    kernel = np.array([0.25, 0.50, 0.25], dtype=np.float32)
    smooth_rms = np.convolve(rms, kernel, mode="same")
    sub = smooth_rms[lo_h : hi_h + 1]
    best_rel = int(np.argmin(sub))
    valley_rms = float(sub[best_rel])
    valley_ratio = valley_rms / max(1.0, p85)

    if require_quiet_valley and valley_ratio > 0.42:
        return None, valley_ratio

    center_sample = int((lo_h + best_rel + 0.5) * hop)
    zc_radius = max(4, int(sr * 0.004))
    s0 = max(1, center_sample - zc_radius)
    s1 = min(n - 2, center_sample + zc_radius)

    best_zc = center_sample
    best_amp = float(abs_f[center_sample])
    for s in range(s0, s1):
        v_cur = int(pcm_mono[s])
        v_nxt = int(pcm_mono[s + 1])
        if v_cur == 0 or (v_cur < 0 <= v_nxt) or (v_cur > 0 >= v_nxt):
            cand_amp = abs(v_cur) + abs(v_nxt)
            if cand_amp <= best_amp:
                best_amp = cand_amp
                best_zc = s
                if cand_amp == 0:
                    break
    return best_zc, round(valley_ratio, 4)


def render_caesura_split_wav(
    src_wav: Path,
    dst_wav: Path,
    *,
    split_sample: int,
    hold_sec: float,
) -> tuple[float, float]:
    """Insert `hold_sec` clean breath at `split_sample` with 10ms cosine micro-tapers (zero click/pop).

    Returns `(split_sec, new_duration_sec)`.
    """
    with wave.open(str(src_wav), "rb") as wf:
        nch = wf.getnchannels()
        sw = wf.getsampwidth()
        sr = wf.getframerate()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)

    if sw != 2 or sr <= 0 or nframes <= 0:
        shutil.copy2(src_wav, dst_wav)
        return 0.0, wav_duration(src_wav)

    arr = np.frombuffer(raw, dtype=np.int16).copy()
    frames = arr.reshape(-1, nch)
    split_f = max(1, min(frames.shape[0] - 1, int(split_sample)))
    fade_len = min(int(sr * 0.010), split_f, frames.shape[0] - split_f)

    left = frames[:split_f].astype(np.float32)
    right = frames[split_f:].astype(np.float32)

    if fade_len >= 4:
        fade_out = (0.5 * (1.0 + np.cos(np.linspace(0.0, math.pi, fade_len, dtype=np.float32)))).reshape(-1, 1)
        fade_in = (0.5 * (1.0 - np.cos(np.linspace(0.0, math.pi, fade_len, dtype=np.float32)))).reshape(-1, 1)
        left[-fade_len:] *= fade_out
        right[:fade_len] *= fade_in

    hold_frames = max(1, int(round(max(0.05, hold_sec) * sr)))
    silence = np.zeros((hold_frames, nch), dtype=np.int16)
    out_frames = np.vstack(
        [
            np.clip(np.round(left), -32768, 32767).astype(np.int16),
            silence,
            np.clip(np.round(right), -32768, 32767).astype(np.int16),
        ]
    )

    dst_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst_wav), "wb") as out_wf:
        out_wf.setnchannels(nch)
        out_wf.setsampwidth(2)
        out_wf.setframerate(sr)
        out_wf.writeframes(out_frames.reshape(-1).tobytes())

    split_sec = round(split_f / float(sr), 4)
    new_dur = round(out_frames.shape[0] / float(sr), 4)
    return split_sec, new_dur


def _normalize_token(tok: str) -> str:
    return re.sub(r"[^\w\uac00-\ud7a3\u3040-\u30ff\u4e00-\u9fff]+", "", str(tok or "").lower())


def _locate_caesura_candidate(
    text: str,
    words: list[dict[str, Any]],
    dur_sec: float,
    *,
    explicit_spec: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Locate `(split_word_index, target_sec, pre_text, post_text, before_word, reason)` for a mid-beat caesura."""
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return None

    # Synthesize proportional words if `words[]` wasn't populated yet
    eff_words = list(words or [])
    if len(eff_words) < 3:
        toks = [t for t in cleaned.split(" ") if t]
        if len(toks) < 4:
            return None
        eff_words = [
            {
                "word": tok,
                "rel_start": round(dur_sec * (i / len(toks)), 3),
                "rel_end": round(dur_sec * ((i + 1) / len(toks)), 3),
            }
            for i, tok in enumerate(toks)
        ]

    # Case A: Explicit CLI / override specification (`before_word` or `split_word_index`)
    if isinstance(explicit_spec, dict):
        before_kw = str(explicit_spec.get("before_word") or explicit_spec.get("before") or "").strip()
        exp_idx = explicit_spec.get("split_word_index")
        reason = str(explicit_spec.get("reason") or "editor_manual_caesura")

        chosen_idx: int | None = None
        if exp_idx is not None:
            idx_val = int(exp_idx)
            if 1 <= idx_val < len(eff_words):
                chosen_idx = idx_val
        elif before_kw:
            norm_kw = _normalize_token(before_kw.split()[0])
            for wi in range(1, len(eff_words)):
                w_norm = _normalize_token(str(eff_words[wi].get("word") or ""))
                if norm_kw and (w_norm.startswith(norm_kw) or norm_kw in w_norm):
                    chosen_idx = wi
                    break

        if chosen_idx is not None:
            prev_end = float(eff_words[chosen_idx - 1].get("rel_end") or 0.0)
            next_start = float(eff_words[chosen_idx].get("rel_start") or prev_end)
            target_sec = 0.5 * (prev_end + next_start)
            char_pos = cleaned.find(before_kw) if before_kw else -1
            if char_pos > 2:
                pre_text = cleaned[:char_pos].strip()
                post_text = cleaned[char_pos:].strip()
            else:
                pre_text = " ".join(str(w.get("word") or "").strip() for w in eff_words[:chosen_idx]).strip()
                post_text = " ".join(str(w.get("word") or "").strip() for w in eff_words[chosen_idx:]).strip()
            if pre_text and post_text:
                return {
                    "split_word_index": chosen_idx,
                    "target_sec": round(target_sec, 3),
                    "pre_text": pre_text,
                    "post_text": post_text,
                    "before_word": str(eff_words[chosen_idx].get("word") or before_kw).strip(),
                    "reason": reason,
                    "explicit": True,
                }

    # Case B: Automatic high-selectivity narrative pivot detection
    for pat in _CAESURA_PIVOT_PATTERNS:
        m = pat.search(cleaned)
        if not m:
            continue
        pivot_start_char = m.start(1)
        pre_text = cleaned[:pivot_start_char].strip()
        post_text = cleaned[pivot_start_char:].strip()
        if len(pre_text) < 8 or len(post_text) < 6:
            continue

        pivot_first_tok = _normalize_token(post_text.split()[0])
        if not pivot_first_tok:
            continue

        approx_ratio = len(pre_text) / float(max(1, len(cleaned)))
        if not (0.24 <= approx_ratio <= 0.78):
            continue

        best_wi: int | None = None
        best_dist = 999.0
        for wi in range(1, len(eff_words)):
            w_norm = _normalize_token(str(eff_words[wi].get("word") or ""))
            if not w_norm:
                continue
            if w_norm.startswith(pivot_first_tok) or pivot_first_tok.startswith(w_norm):
                w_ratio = wi / float(len(eff_words))
                dist = abs(w_ratio - approx_ratio)
                if dist < best_dist:
                    best_dist = dist
                    best_wi = wi

        if best_wi is None:
            continue
        prev_end = float(eff_words[best_wi - 1].get("rel_end") or (dur_sec * approx_ratio))
        next_start = float(eff_words[best_wi].get("rel_start") or prev_end)
        target_sec = 0.5 * (prev_end + next_start)
        if target_sec < 1.15 or (dur_sec - target_sec) < 0.85:
            continue

        return {
            "split_word_index": best_wi,
            "target_sec": round(target_sec, 3),
            "pre_text": pre_text,
            "post_text": post_text,
            "before_word": str(eff_words[best_wi].get("word") or "").strip(),
            "reason": "mid_sentence_twist_reveal_caesura",
            "explicit": False,
        }

    return None


def concat_timeline_wav_with_pre_and_outro(
    *,
    pre_voice_sec: float,
    beat_wavs: list[Path],
    inter_beat_pauses: list[float],
    outro_tail_sec: float,
    output_path: Path,
) -> float:
    """Losslessly assemble `[pre_voice_silence] + B001 + pause_0 + B002 + ... + B_N + [outro_tail]`."""
    if not beat_wavs:
        raise ValueError("Không có beat WAV nào để dựng timeline narration.wav")

    params = None
    chunks: list[bytes] = []

    for idx, wav_path in enumerate(beat_wavs):
        with wave.open(str(wav_path), "rb") as wf:
            cur_params = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getcomptype(), wf.getcompname())
            frames = wf.readframes(wf.getnframes())
        if params is None:
            params = cur_params
            nch, sw, sr = params[0], params[1], params[2]
            if pre_voice_sec > 0.001:
                pre_frames = int(round(pre_voice_sec * sr))
                chunks.append(b"\x00" * (pre_frames * nch * sw))
        elif cur_params[:3] != params[:3]:
            raise RuntimeError(f"WAV format mismatch tại {wav_path}: {cur_params[:3]} != {params[:3]}")

        chunks.append(frames)
        nch, sw, sr = params[0], params[1], params[2]
        if idx < len(beat_wavs) - 1:
            gap = max(0.0, float(inter_beat_pauses[idx]) if idx < len(inter_beat_pauses) else 0.0)
            if gap > 0.001:
                gap_frames = int(round(gap * sr))
                chunks.append(b"\x00" * (gap_frames * nch * sw))
        elif outro_tail_sec > 0.001:
            tail_frames = int(round(outro_tail_sec * sr))
            chunks.append(b"\x00" * (tail_frames * nch * sw))

    assert params is not None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as out_wf:
        out_wf.setnchannels(params[0])
        out_wf.setsampwidth(params[1])
        out_wf.setframerate(params[2])
        out_wf.setcomptype(params[3], params[4])
        for chunk in chunks:
            out_wf.writeframes(chunk)

    return wav_duration(output_path)


def sync_remotion_public_audio_and_srt(
    *,
    job: dict[str, Any],
    workspace: Path,
    remotion_dir: Path | None,
    invalidate_render_cache: bool = False,
) -> dict[str, Any]:
    """Mirror updated `narration.wav`, `subtitles.srt`, and `editorial_voice_plan.json` into `CofiRemotion/public/jobs/<job_id>/`."""
    job_id = str(job.get("id") or workspace.name).strip()
    if not remotion_dir:
        cand = workspace.parents[1] / "CofiRemotion" if len(workspace.parents) >= 2 else None
        if cand and cand.is_dir():
            remotion_dir = cand
    if not remotion_dir or not Path(remotion_dir).is_dir():
        return {"synced": False, "reason": "remotion_dir_not_found"}

    pub_job = Path(remotion_dir) / "public" / "jobs" / job_id
    if not pub_job.is_dir():
        return {"synced": False, "reason": "public_job_dir_not_initialized_yet", "target": str(pub_job)}

    pub_audio = pub_job / "audio"
    pub_audio.mkdir(parents=True, exist_ok=True)

    narration_src = workspace / "audio" / "narration.wav"
    if narration_src.is_file():
        shutil.copy2(narration_src, pub_job / "narration.wav")
        shutil.copy2(narration_src, pub_audio / "narration.wav")
        # Remove any stale compressed proxy (`narration.m4a`, `narration_48k.m4a`) in both locations
        for proxy_dir in (pub_job, pub_audio):
            for stale_proxy in proxy_dir.glob("narration*.m4a"):
                try:
                    stale_proxy.unlink()
                except OSError:
                    pass

    for fname in ("subtitles.srt", "editorial_voice_plan.json", "edit_rhythm_score.json"):
        src_f = workspace / fname
        if src_f.is_file():
            shutil.copy2(src_f, pub_job / fname)

    invalidated_chunks = 0
    if invalidate_render_cache:
        cache_dir = workspace / ".render_cache"
        if cache_dir.is_dir():
            for mp4_chunk in cache_dir.glob("chunk_*.mp4"):
                try:
                    mp4_chunk.unlink()
                    invalidated_chunks += 1
                except OSError:
                    pass

    return {
        "synced": True,
        "public_job_dir": str(pub_job),
        "invalidated_render_chunks": invalidated_chunks,
    }


def sculpt_editorial_voice_timeline(
    job: dict[str, Any],
    workspace: str | Path,
    *,
    remotion_dir: str | Path | None = None,
    force_on_synthetic: bool = False,
    fps: int = FPS_DEFAULT,
) -> dict[str, Any]:
    """Master Human Editor Voice Cutting & Timeline Re-Sync Pass.

    Idempotently sculpts `audio/narration.wav`, `voice_manifest.json`, `subtitles.srt`,
    and `visual_manifest.json` from clean 1st-generation channel voice stems (`audio/beats_raw/`).
    """
    workspace = Path(workspace).resolve()
    voice_manifest_path = workspace / "voice_manifest.json"
    visual_manifest_path = workspace / "visual_manifest.json"

    if not voice_manifest_path.is_file():
        return {"applied": False, "reason": "missing_voice_manifest"}

    current_voice_manifest = json.loads(voice_manifest_path.read_text(encoding="utf-8"))
    prev_total_dur = float(current_voice_manifest.get("duration_sec") or 0.0)
    raw_manifest, raw_dir = _ensure_raw_stem_backup(workspace, current_voice_manifest)
    raw_beats = [copy.deepcopy(b) for b in (raw_manifest.get("beats") or []) if isinstance(b, dict) and _beat_id(b)]
    if not raw_beats:
        return {"applied": False, "reason": "empty_voice_beats"}

    # Load visual_manifest beats to enrich semantic awareness (`act`, `visual_type`, `story_group`)
    vis_data: dict[str, Any] = {}
    vis_by_id: dict[str, dict[str, Any]] = {}
    if visual_manifest_path.is_file():
        try:
            vis_data = json.loads(visual_manifest_path.read_text(encoding="utf-8"))
            for vb in vis_data.get("beats") or []:
                if isinstance(vb, dict) and _beat_id(vb):
                    vbid = _beat_id(vb)
                    vis_by_id[vbid] = vb
                    pid = str(vb.get("parent_beat_id") or vbid.split("-")[0]).strip()
                    if pid and pid not in vis_by_id:
                        vis_by_id[pid] = vb
        except Exception:
            vis_data = {}

    # Load timeline.json beats (if already generated) to align 5-Act curtain boundaries & CINEMA_TEXT beats
    tl_data: dict[str, Any] = {}
    tl_by_id: dict[str, dict[str, Any]] = {}
    timeline_path = workspace / "timeline.json"
    if timeline_path.is_file():
        try:
            tl_data = json.loads(timeline_path.read_text(encoding="utf-8"))
            for tb in tl_data.get("beats") or []:
                if isinstance(tb, dict):
                    tbid = str(tb.get("beatId") or tb.get("beat_id") or "").strip()
                    rbid = str(tb.get("rawBeatId") or tbid.split("-")[0]).strip()
                    if tbid:
                        tl_by_id[tbid] = tb
                    if rbid and rbid not in tl_by_id:
                        tl_by_id[rbid] = tb
        except Exception:
            tl_data = {}

    overrides = _load_overrides(workspace)
    has_explicit_overrides = bool(
        overrides.get("pre_voice_sec") is not None
        or overrides.get("pauses")
        or overrides.get("caesuras")
    )

    # Check if stems contain real speech (vs silent synthetic unit-test fixtures)
    sample_wav = Path(str(raw_beats[0].get("raw_audio_path") or raw_beats[0].get("audio_path") or (raw_dir / f"{_beat_id(raw_beats[0])}.wav")))
    is_real_audio = _is_non_silent_speech_wav(sample_wav)
    if not is_real_audio and not force_on_synthetic and not has_explicit_overrides:
        return {
            "applied": False,
            "reason": "synthetic_silent_fixture_preserved",
            "total_beats": len(raw_beats),
        }

    from services.voice_rhythm_specialist import resolve_editorial_craft_profile, resolve_job_rhythm_dna

    rhythm_dna = resolve_job_rhythm_dna(job)
    craft = resolve_editorial_craft_profile(rhythm_dna)
    vocal_cad = rhythm_dna.get("vocal_cadence") if isinstance(rhythm_dna.get("vocal_cadence"), dict) else {}
    allow_fast_chain = bool(vocal_cad.get("allow_urgent_fast_chain", True))
    max_fast_streak = int(vocal_cad.get("max_fast_gap_streak") or 4)

    # 1. Cold-open pre-voice world-building breath
    if overrides.get("pre_voice_sec") is not None:
        pre_voice_sec = round(max(0.0, min(4.0, float(overrides["pre_voice_sec"]))), 3)
    else:
        pre_voice_sec = round(max(0.65, min(2.5, float(craft.get("cold_open_pre_voice_sec") or 1.25))), 3)

    # 2. Mid-beat Zero-Crossing Caesura Splits (DISABLED by default per V17 Continuous Uncut Voice Rule:
    # never slice or chop mid-sentence speech WAVs automatically; only apply if explicitly passed via overrides)
    caesura_policy = craft.get("mid_beat_caesura_policy") if isinstance(craft.get("mid_beat_caesura_policy"), dict) else {}
    auto_caesura_enabled = bool(os.getenv("COFI_ENABLE_AUTO_CAESURA_SPLIT", "0") == "1" and caesura_policy.get("enabled", False))
    raw_total_speech_sec = sum(max(0.2, float(b.get("speech_end_sec") or b.get("duration_sec") or 0.0) - float(b.get("start_sec") or 0.0)) for b in raw_beats)
    max_auto_caesuras = max(
        1 if raw_total_speech_sec >= 90.0 else 0,
        int(round((raw_total_speech_sec / 600.0) * float(caesura_policy.get("max_per_10min") or 2))),
    )
    min_beat_spacing = int(caesura_policy.get("min_beat_spacing") or 12)
    min_caesura_beat_dur = float(caesura_policy.get("min_beat_dur_sec") or 4.2)
    default_caesura_hold = float(caesura_policy.get("hold_sec") or 0.74)

    edited_dir = workspace / "audio" / "beats_edited"
    edited_dir.mkdir(parents=True, exist_ok=True)
    disabled_caesuras = set(str(x) for x in (overrides.get("disabled_caesuras") or []))
    explicit_caesuras: dict[str, Any] = overrides.get("caesuras") if isinstance(overrides.get("caesuras"), dict) else {}

    auto_caesura_count = 0
    last_caesura_idx = -999
    active_wavs: list[Path] = []
    edge_silences: list[tuple[float, float]] = []
    caesura_events: list[dict[str, Any]] = []

    for idx, b in enumerate(raw_beats):
        bid = _beat_id(b)
        src_wav = raw_dir / f"{bid}.wav"
        if not src_wav.is_file():
            src_wav = Path(str(b.get("audio_path") or (workspace / "audio" / "beats" / f"{bid}.wav")))
        if not src_wav.is_file():
            raise FileNotFoundError(f"Không tìm thấy WAV gốc cho beat {bid}: {src_wav}")

        orig_dur = wav_duration(src_wav)
        orig_words = copy.deepcopy(b.get("words") or [])
        # Normalize `rel_start` / `rel_end` on raw words
        b_orig_start = float(b.get("start_sec") or 0.0)
        norm_words: list[dict[str, Any]] = []
        for w in orig_words:
            if not isinstance(w, dict):
                continue
            rs = float(w.get("rel_start") if w.get("rel_start") is not None else max(0.0, float(w.get("start") or b_orig_start) - b_orig_start))
            re_ = float(w.get("rel_end") if w.get("rel_end") is not None else max(rs + 0.04, float(w.get("end") or (b_orig_start + rs + 0.08)) - b_orig_start))
            norm_words.append({"word": str(w.get("word") or "").strip(), "rel_start": round(rs, 3), "rel_end": round(re_, 3)})

        exp_c = explicit_caesuras.get(bid) if isinstance(explicit_caesuras.get(bid), dict) else None
        can_try_auto = (
            auto_caesura_enabled
            and bid not in disabled_caesuras
            and exp_c is None
            and idx > 0
            and idx < len(raw_beats) - 1
            and orig_dur >= min_caesura_beat_dur
            and auto_caesura_count < max_auto_caesuras
            and (idx - last_caesura_idx) >= min_beat_spacing
        )

        chosen_wav = src_wav
        effective_dur = orig_dur
        caesura_applied = None

        if exp_c is not None or can_try_auto:
            cand = _locate_caesura_candidate(
                str(b.get("text") or ""),
                norm_words,
                orig_dur,
                explicit_spec=exp_c,
            )
            if cand is not None:
                try:
                    with wave.open(str(src_wav), "rb") as wf:
                        nch = wf.getnchannels()
                        sr = wf.getframerate()
                        pcm_raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
                    pcm_mono = pcm_raw.reshape(-1, nch)[:, 0] if nch > 1 else pcm_raw
                    split_sample, valley_ratio = find_zero_crossing_split_sample(
                        pcm_mono,
                        sr,
                        float(cand["target_sec"]),
                        search_radius_sec=0.18 if cand.get("explicit") else 0.14,
                        require_quiet_valley=not bool(cand.get("explicit")),
                    )
                    if split_sample is not None:
                        hold_sec = round(
                            max(0.25, min(2.0, float((exp_c or {}).get("hold_sec") or default_caesura_hold))),
                            3,
                        )
                        out_edited_wav = edited_dir / f"{bid}.wav"
                        split_sec, new_dur = render_caesura_split_wav(
                            src_wav,
                            out_edited_wav,
                            split_sample=split_sample,
                            hold_sec=hold_sec,
                        )
                        if new_dur > orig_dur + 0.10:
                            chosen_wav = out_edited_wav
                            effective_dur = new_dur
                            split_wi = int(cand["split_word_index"])
                            for wi, wd in enumerate(norm_words):
                                if wi >= split_wi:
                                    wd["rel_start"] = round(float(wd["rel_start"]) + hold_sec, 3)
                                    wd["rel_end"] = round(float(wd["rel_end"]) + hold_sec, 3)
                                else:
                                    wd["rel_end"] = round(min(split_sec, float(wd["rel_end"])), 3)
                                    wd["rel_start"] = round(min(wd["rel_end"], float(wd["rel_start"])), 3)

                            caesura_applied = {
                                "beat_id": bid,
                                "split_word_index": split_wi,
                                "before_word": cand["before_word"],
                                "local_start_sec": round(split_sec, 3),
                                "local_end_sec": round(split_sec + hold_sec, 3),
                                "hold_sec": hold_sec,
                                "valley_rms_ratio": valley_ratio,
                                "reason": cand["reason"],
                                "explicit": bool(cand.get("explicit")),
                            }
                            b["editorial_caesuras"] = [caesura_applied]
                            b["editorial_speech_segments"] = [
                                {
                                    "text": cand["pre_text"],
                                    "rel_start": 0.0,
                                    "rel_end": round(split_sec, 3),
                                },
                                {
                                    "text": cand["post_text"],
                                    "rel_start": round(split_sec + hold_sec, 3),
                                    "rel_end": round(new_dur, 3),
                                },
                            ]
                            caesura_events.append(caesura_applied)
                            last_caesura_idx = idx
                            if not cand.get("explicit"):
                                auto_caesura_count += 1
                except Exception:
                    pass

        b["_active_wav_path"] = chosen_wav
        b["_effective_speech_dur"] = effective_dur
        b["_rel_words"] = norm_words
        active_wavs.append(chosen_wav)
        ac_lead, ac_trail = measure_wav_acoustic_edges(chosen_wav)
        w_lead = float(norm_words[0]["rel_start"]) if norm_words else 0.0
        w_trail = max(0.0, effective_dur - float(norm_words[-1]["rel_end"])) if norm_words else 0.0
        edge_silences.append((max(ac_lead, min(0.60, w_lead)), max(ac_trail, min(0.85, w_trail))))

    # 3. Intentional Inter-Beat Breathing Room & Kinetic Action Shaving (3-Tier Breathing Architecture)
    pause_overrides: dict[str, Any] = overrides.get("pauses") if isinstance(overrides.get("pauses"), dict) else {}
    chapter_breath = max(1.60, min(2.20, float(craft.get("chapter_curtain_breath_sec") or 1.85)))
    twist_breath = max(1.18, min(1.60, float(craft.get("twist_reveal_breath_sec") or 1.38)))
    somber_breath = max(1.22, min(1.60, float(craft.get("somber_aftermath_breath_sec") or 1.44)))
    urgent_shave_gap = min(0.32, max(0.24, float(craft.get("urgent_shave_gap_sec") or 0.28)))
    para_breath = min(0.48, max(0.36, float((vocal_cad.get("pause_tiers_sec") or {}).get("paragraph_breath") or 0.44)))

    sculpted_pauses: list[float] = []
    sculpted_reasons: list[str] = []
    pause_adjustments: list[dict[str, Any]] = []
    act_transition_holds: list[dict[str, Any]] = []
    fast_streak = 0

    for idx in range(len(raw_beats) - 1):
        cur_b = raw_beats[idx]
        nxt_b = raw_beats[idx + 1]
        bid = _beat_id(cur_b)
        nxt_id = _beat_id(nxt_b)
        v_cur = vis_by_id.get(bid, {})
        v_nxt = vis_by_id.get(nxt_id, {})
        t_cur = tl_by_id.get(bid, {})
        t_nxt = tl_by_id.get(nxt_id, {})

        raw_base_pause = float(cur_b.get("pause_after_sec") or 0.38)
        base_pause = min(0.48, max(0.28, raw_base_pause))
        base_reason = str(cur_b.get("pause_reason") or "standard_narrative")
        emo = str(cur_b.get("emotion_register") or "narrative_flow")
        text_cur = str(cur_b.get("text") or "").strip()
        text_low = text_cur.lower()

        if t_cur:
            vtype_cur = str(t_cur.get("visualType") or "").upper()
            if t_cur.get("ctId") or t_cur.get("cinemaTextSpec"):
                vtype_cur = "CINEMA_TEXT"
        else:
            vtype_cur = str(v_cur.get("visual_type") or cur_b.get("visual_type") or "").upper()
            if "CINEMA_TEXT" in vtype_cur:
                vtype_cur = "CINEMA_TEXT"

        tl_act_cur = str(t_cur.get("actId") or t_cur.get("act") or "").strip()
        tl_act_nxt = str(t_nxt.get("actId") or t_nxt.get("act") or "").strip()
        vis_act_cur = str(
            v_cur.get("act")
            or v_cur.get("act_id")
            or v_cur.get("chapter_id")
            or cur_b.get("act")
            or cur_b.get("act_id")
            or cur_b.get("chapter_id")
            or ""
        ).strip()
        vis_act_nxt = str(
            v_nxt.get("act")
            or v_nxt.get("act_id")
            or v_nxt.get("chapter_id")
            or nxt_b.get("act")
            or nxt_b.get("act_id")
            or nxt_b.get("chapter_id")
            or ""
        ).strip()

        if tl_act_cur and tl_act_nxt:
            act_cur, act_nxt = tl_act_cur, tl_act_nxt
            is_act_curtain = act_cur != act_nxt
            is_subchapter_pivot = (not is_act_curtain) and bool(vis_act_cur and vis_act_nxt and vis_act_cur != vis_act_nxt)
        else:
            act_cur, act_nxt = vis_act_cur, vis_act_nxt
            is_act_curtain = bool(
                (act_cur and act_nxt and act_cur != act_nxt)
                or base_reason in ("act_transition", "editorial_chapter_curtain_breath")
            )
            is_subchapter_pivot = False

        trail_sil = float(edge_silences[idx][1]) if idx < len(edge_silences) else 0.0
        lead_sil_nxt = float(edge_silences[idx + 1][0]) if (idx + 1) < len(edge_silences) else 0.0
        natural_edge = min(0.85, max(0.0, trail_sil + lead_sil_nxt))

        # Priority A: Explicit `@edit` override
        if bid in pause_overrides:
            ov_entry = pause_overrides[bid]
            if isinstance(ov_entry, dict):
                p_val = round(max(0.08, min(4.5, float(ov_entry.get("pause_sec") or base_pause))), 3)
                p_reason = str(ov_entry.get("reason") or "editor_manual_pause")
            else:
                p_val = round(max(0.08, min(4.5, float(ov_entry))), 3)
                p_reason = "editor_manual_pause"
            fast_streak = fast_streak + 1 if p_val <= 0.36 else 0
            sculpted_pauses.append(p_val)
            sculpted_reasons.append(p_reason)
            pause_adjustments.append({"beat_id": bid, "from_sec": round(raw_base_pause, 3), "to_sec": p_val, "reason": p_reason})
            if is_act_curtain:
                act_transition_holds.append({"beat_id": bid, "from_act": act_cur, "to_act": act_nxt, "pause_after_sec": p_val, "reason": p_reason})
            continue

        target_perceived: float | None = None
        min_hold_floor = 1.04
        max_hold_ceil = 1.58
        new_reason = base_reason

        # Priority B: Chapter / Act curtain transition (`ACT01 -> ACT05`) -> 1.4s – 2.2s editorial curtain breath
        if is_act_curtain:
            target_perceived = max(chapter_breath, min(2.15, raw_base_pause if raw_base_pause >= 1.4 else chapter_breath))
            min_hold_floor = 1.48
            max_hold_ceil = 2.15
            new_reason = "editorial_chapter_curtain_breath"
        # Priority C: `CINEMA_TEXT` (`FramelessCinemaTextBeat`), paradox question (`?`), or key evidence twist reveal -> 1.0s – 1.6s hold
        elif (
            vtype_cur == "CINEMA_TEXT"
            or text_cur.endswith(("?", "？"))
            or emo in ("twist_reveal", "suspense_question")
            or base_reason in (
                "rhetorical_question_suspense",
                "suspense_cliffhanger",
                "dramatic_landing",
                "editorial_twist_reveal_hold",
                "editorial_paradox_question_hold",
                "editorial_cinema_text_breath",
            )
            or is_subchapter_pivot
            or (emo == "stark_punch" and raw_base_pause >= 1.0)
        ):
            if vtype_cur == "CINEMA_TEXT" and text_cur.endswith(("?", "？")):
                target_perceived = max(twist_breath, 1.46)
                new_reason = "editorial_paradox_question_hold"
            elif text_cur.endswith(("?", "？")) or base_reason == "rhetorical_question_suspense":
                target_perceived = max(twist_breath, 1.38)
                new_reason = "editorial_paradox_question_hold"
            elif vtype_cur == "CINEMA_TEXT":
                target_perceived = max(1.18, min(1.48, twist_breath - 0.08))
                new_reason = "editorial_cinema_text_breath"
            else:
                target_perceived = max(1.24, min(1.56, max(twist_breath, raw_base_pause if raw_base_pause <= 1.6 else 1.48)))
                new_reason = "editorial_twist_reveal_hold"
            min_hold_floor = 1.05
            max_hold_ceil = 1.58
        # Priority D: Human tragedy / emotional aftermath -> 1.0s – 1.6s empathetic linger
        elif emo == "somber_tragedy" or base_reason in ("somber_tragedy_linger", "editorial_somber_empathy_hold"):
            target_perceived = max(1.26, min(1.58, somber_breath))
            min_hold_floor = 1.08
            max_hold_ceil = 1.58
            new_reason = "editorial_somber_empathy_hold"
        # Priority E: Kinetic action streak -> crisp shave within [0.28s, 0.38s] (with listener recovery guard!)
        elif emo in ("urgent_action", "stark_punch") and allow_fast_chain:
            if fast_streak >= max_fast_streak:
                rec_gap = round(max(0.38, min(0.48, para_breath - natural_edge * 0.25)), 3)
                fast_streak = 0
                sculpted_pauses.append(rec_gap)
                sculpted_reasons.append("editorial_fatigue_recovery_breath")
                pause_adjustments.append(
                    {"beat_id": bid, "from_sec": round(raw_base_pause, 3), "to_sec": rec_gap, "reason": "editorial_fatigue_recovery_breath"}
                )
                continue
            else:
                p_shaved = round(max(0.28, min(0.38, max(0.28, urgent_shave_gap - 0.20 * natural_edge))), 3)
                fast_streak += 1
                sculpted_pauses.append(p_shaved)
                sculpted_reasons.append("editorial_kinetic_shave")
                if abs(p_shaved - raw_base_pause) >= 0.05:
                    pause_adjustments.append(
                        {"beat_id": bid, "from_sec": round(raw_base_pause, 3), "to_sec": p_shaved, "reason": "editorial_kinetic_shave"}
                    )
                continue

        if target_perceived is not None:
            char_weight = min(0.08, max(-0.06, (len(text_cur) - 32) * 0.002))
            organic_jitter = _pause_jitter_for(f"{bid}:{idx}:{text_cur[:16]}", spread=0.14 if not is_act_curtain else 0.12)
            eff_max_ceil = max(max_hold_ceil, 1.68 if not is_act_curtain else 2.15)
            eff_min_floor = min(min_hold_floor, 1.12 if not is_act_curtain else 1.48)
            computed_gap = round(
                max(eff_min_floor, min(eff_max_ceil, target_perceived + organic_jitter + char_weight - natural_edge * 0.35)),
                3,
            )
            fast_streak = 0
            sculpted_pauses.append(computed_gap)
            sculpted_reasons.append(new_reason)
            pause_adjustments.append(
                {"beat_id": bid, "from_sec": round(raw_base_pause, 3), "to_sec": computed_gap, "reason": new_reason}
            )
            if is_act_curtain:
                act_transition_holds.append(
                    {"beat_id": bid, "from_act": act_cur, "to_act": act_nxt, "pause_after_sec": computed_gap, "reason": new_reason}
                )
        else:
            # Standard continuous narrative sentences in the same paragraph: keep crisp [0.28s .. 0.48s] with subtle jitter
            std_jitter = _pause_jitter_for(f"std:{bid}:{idx}", spread=0.03)
            eff_std_gap = round(max(0.28, min(0.48, base_pause + std_jitter - max(0.0, natural_edge - 0.18) * 0.45)), 3)
            if eff_std_gap <= 0.31:
                fast_streak += 1
                if fast_streak > max_fast_streak:
                    rec_gap = round(max(0.38, min(0.48, para_breath - natural_edge * 0.25)), 3)
                    sculpted_pauses.append(rec_gap)
                    sculpted_reasons.append("editorial_fatigue_recovery_breath")
                    pause_adjustments.append(
                        {"beat_id": bid, "from_sec": round(raw_base_pause, 3), "to_sec": rec_gap, "reason": "editorial_fatigue_recovery_breath"}
                    )
                    fast_streak = 0
                    continue
            else:
                fast_streak = 0
            sculpted_pauses.append(eff_std_gap)
            sculpted_reasons.append(base_reason)

    # 4. Concatenate lossless `audio/narration.wav` & recompute exact frame/sample timestamps
    narration_out = workspace / "audio" / "narration.wav"
    outro_tail = float(craft.get("sound_design_soul", {}).get("outro_tail_sec") or OUTRO_FADE_TAIL_SEC)
    actual_total_dur = concat_timeline_wav_with_pre_and_outro(
        pre_voice_sec=pre_voice_sec,
        beat_wavs=active_wavs,
        inter_beat_pauses=sculpted_pauses,
        outro_tail_sec=outro_tail,
        output_path=narration_out,
    )

    cursor = pre_voice_sec
    updated_voice_beats: list[dict[str, Any]] = []
    timing_by_id: dict[str, dict[str, Any]] = {}

    for idx, b in enumerate(raw_beats):
        is_first = idx == 0
        is_last = idx == len(raw_beats) - 1
        bid = _beat_id(b)
        active_wav: Path = b.pop("_active_wav_path")
        eff_dur: float = float(b.pop("_effective_speech_dur"))
        rel_words: list[dict[str, Any]] = b.pop("_rel_words", [])

        speech_start = round(cursor, 3)
        speech_end = round(cursor + eff_dur, 3)
        pause_after = round(sculpted_pauses[idx], 3) if not is_last else 0.0
        pause_reason = sculpted_reasons[idx] if not is_last else "outro_end"
        tail_hold = round(outro_tail, 3) if is_last else 0.0

        # Visual window is 100% contiguous [0.0 .. actual_total_dur] with zero black gaps:
        # - Beat 1 opens visually at 0.0s (covering the cold-open pre-voice world-building breath!)
        # - Every beat holds visually through its post-speech intentional pause right up to the next beat's speech start!
        visual_open = 0.0 if is_first else speech_start
        visual_close = round(actual_total_dur, 3) if is_last else round(speech_end + pause_after, 3)

        abs_words = [
            {
                "word": w["word"],
                "rel_start": round(float(w["rel_start"]), 3),
                "rel_end": round(float(w["rel_end"]), 3),
                "start": round(speech_start + float(w["rel_start"]), 3),
                "end": round(speech_start + float(w["rel_end"]), 3),
            }
            for w in rel_words
            if w.get("word")
        ]

        out_b = copy.deepcopy(b)
        out_b["audio_path"] = str(active_wav)
        out_b["visual_open_sec"] = visual_open
        out_b["visual_close_sec"] = visual_close
        out_b["start_sec"] = speech_start
        out_b["speech_end_sec"] = speech_end
        out_b["end_sec"] = round(speech_end + tail_hold, 3)
        out_b["duration_sec"] = round(eff_dur + tail_hold, 3)
        out_b["pause_after_sec"] = pause_after
        out_b["pause_reason"] = pause_reason
        out_b["outro_tail_sec"] = tail_hold
        out_b["words"] = abs_words
        if is_first and pre_voice_sec > 0:
            out_b["pre_voice_breath_sec"] = pre_voice_sec

        updated_voice_beats.append(out_b)
        timing_by_id[bid] = {
            "visual_open_sec": visual_open,
            "visual_close_sec": visual_close,
            "speech_start_sec": speech_start,
            "speech_end_sec": speech_end,
            "pause_after_sec": pause_after,
            "pause_reason": pause_reason,
            "editorial_caesuras": out_b.get("editorial_caesuras") or [],
            "words": abs_words,
            "text": str(out_b.get("text") or "").strip(),
        }
        cursor = speech_end + (pause_after if not is_last else tail_hold)

    normal_pauses = [p for p in sculpted_pauses if p < 1.0]
    dramatic_pauses = [p for p in sculpted_pauses if p >= 1.0]
    editorial_summary = {
        "version": 2,
        "sculpted_by": "edit",
        "archetype_id": rhythm_dna.get("archetype_id") or craft.get("archetype_id"),
        "cold_open_pre_voice_sec": pre_voice_sec,
        "outro_tail_sec": round(outro_tail, 3),
        "total_beats": len(updated_voice_beats),
        "pause_adjustments_count": len(pause_adjustments),
        "mid_beat_caesuras_count": len(caesura_events),
        "dramatic_holds_over_1_0s": len(dramatic_pauses),
        "dramatic_holds_over_1_2s": sum(1 for p in sculpted_pauses if p >= 1.20),
        "act_curtain_holds_count": len(act_transition_holds),
        "act_transitions": act_transition_holds,
        "pause_stats": {
            "min_sec": round(min(sculpted_pauses), 3) if sculpted_pauses else 0.0,
            "max_sec": round(max(sculpted_pauses), 3) if sculpted_pauses else 0.0,
            "avg_all_sec": round(sum(sculpted_pauses) / len(sculpted_pauses), 3) if sculpted_pauses else 0.0,
            "avg_normal_narrative_sec": round(sum(normal_pauses) / len(normal_pauses), 3) if normal_pauses else 0.0,
            "avg_dramatic_hold_sec": round(sum(dramatic_pauses) / len(dramatic_pauses), 3) if dramatic_pauses else 0.0,
        },
        "kinetic_shaves_count": sum(1 for r in sculpted_reasons if r == "editorial_kinetic_shave"),
        "duration_sec": round(actual_total_dur, 3),
        "sculpted_at": _now_iso(),
    }

    # Write `voice_manifest.json`
    new_voice_manifest = copy.deepcopy(raw_manifest)
    new_voice_manifest["duration_sec"] = round(actual_total_dur, 3)
    new_voice_manifest["narration_path"] = str(narration_out)
    new_voice_manifest["pre_voice_breath_sec"] = pre_voice_sec
    new_voice_manifest["editorial_voice_sculpted"] = True
    new_voice_manifest["editorial_summary"] = editorial_summary
    if new_voice_manifest.get("target_duration_sec"):
        new_voice_manifest["duration_delta_sec"] = round(
            actual_total_dur - float(new_voice_manifest["target_duration_sec"]), 3
        )
    new_voice_manifest["beats"] = updated_voice_beats
    voice_manifest_path.write_text(json.dumps(new_voice_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write `subtitles.srt` (non-spoiling across caesuras, cold-open breath, and pauses!)
    srt_text = build_srt(updated_voice_beats)
    (workspace / "subtitles.srt").write_text(srt_text, encoding="utf-8")

    raw_total_frames = actual_total_dur * fps
    near_total_frames = round(raw_total_frames)
    total_frames = max(
        1,
        int(near_total_frames if abs(raw_total_frames - near_total_frames) <= 0.25 else math.ceil(raw_total_frames)),
    )

    # Synchronize `visual_manifest.json` so Remotion beats cover `[0.0 .. actual_total_dur]` gaplessly
    # (supports both direct `B001` beat_ids and split/visual `B001-V01` units via `parent_beat_id`).
    if vis_data and isinstance(vis_data.get("beats"), list):
        vis_beats = vis_data["beats"]
        parent_groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for v_idx, vb in enumerate(vis_beats):
            if not isinstance(vb, dict):
                continue
            bid = _beat_id(vb)
            if not bid:
                continue
            if bid in timing_by_id:
                parent_groups.setdefault(bid, []).append((v_idx, vb))
            else:
                pid = str(vb.get("parent_beat_id") or bid.split("-")[0]).strip()
                parent_groups.setdefault(pid, []).append((v_idx, vb))

        for pid, group in parent_groups.items():
            tm = timing_by_id.get(pid)
            if not tm:
                continue
            p_open = float(tm["visual_open_sec"])
            p_close = float(tm["visual_close_sec"])
            s_start = float(tm["speech_start_sec"])
            s_end = float(tm["speech_end_sec"])
            weights = [
                max(0.2, float(item.get("duration_sec") or item.get("target_duration_sec") or 1.0))
                for _, item in group
            ]
            total_w = sum(weights) or float(len(group))
            span = max(0.001, p_close - p_open)
            acc = p_open
            for g_i, ((v_idx, vb), w) in enumerate(zip(group, weights)):
                v_open = acc
                v_close = p_close if g_i == len(group) - 1 else acc + span * (w / total_w)
                acc = v_close
                start_frame = 0 if v_idx == 0 else int(round(v_open * fps))
                end_frame = total_frames if v_idx == len(vis_beats) - 1 else max(start_frame + 1, int(round(v_close * fps)))

                vb["start_sec"] = round(v_open, 3)
                vb["end_sec"] = round(v_close, 3)
                vb["duration_sec"] = round(max(0.2, v_close - v_open), 3)
                vb["speech_start_sec"] = round(max(v_open, s_start), 3)
                vb["speech_end_sec"] = round(min(v_close, s_end), 3)
                vb["pause_after_sec"] = tm["pause_after_sec"] if g_i == len(group) - 1 else 0.0
                vb["pause_reason"] = tm["pause_reason"] if g_i == len(group) - 1 else "visual_sub_unit"
                vb["start_frame"] = start_frame
                vb["end_frame"] = end_frame
                vb["duration_frames"] = max(1, end_frame - start_frame)
                vb["speech_start_frame"] = int(round(max(v_open, s_start) * fps))
                vb["speech_end_frame"] = int(round(min(v_close, s_end) * fps))
                if tm["editorial_caesuras"] and g_i == len(group) - 1:
                    vb["editorial_caesuras"] = tm["editorial_caesuras"]
                else:
                    vb.pop("editorial_caesuras", None)

        vis_data["duration_sec"] = round(actual_total_dur, 3)
        vis_data["duration_frames"] = total_frames
        vis_data["fps"] = fps
        vis_data["pre_voice_breath_sec"] = pre_voice_sec
        vis_data["editorial_voice_sculpted"] = True
        visual_manifest_path.write_text(json.dumps(vis_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Synchronize `timeline.json`, `edit_manifest.json`, and `scenes.json` if present
    if tl_data and isinstance(tl_data.get("beats"), list):
        tl_beats = tl_data["beats"]
        tl_groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for t_idx, tb in enumerate(tl_beats):
            if not isinstance(tb, dict):
                continue
            tbid = str(tb.get("beatId") or tb.get("beat_id") or "").strip()
            pid = str(tb.get("rawBeatId") or tbid.split("-")[0]).strip()
            key = tbid if tbid in timing_by_id else pid
            if key:
                tl_groups.setdefault(key, []).append((t_idx, tb))

        sfx_alias_map = {
            "audio/sfx_sub_bass_boom_chapter.mp3": "audio/sfx_chapter_hit.mp3",
            "sfx_sub_bass_boom_chapter.mp3": "audio/sfx_chapter_hit.mp3",
        }
        new_breath_lifts: list[dict[str, Any]] = []

        for pid, group in tl_groups.items():
            tm = timing_by_id.get(pid)
            if not tm:
                continue
            p_open = float(tm["visual_open_sec"])
            p_close = float(tm["visual_close_sec"])
            s_start = float(tm["speech_start_sec"])
            s_end = float(tm["speech_end_sec"])
            weights = [
                max(0.2, float(item.get("durationSec") or item.get("duration_sec") or 1.0))
                for _, item in group
            ]
            total_w = sum(weights) or float(len(group))
            span = max(0.001, p_close - p_open)
            acc = p_open
            for g_i, ((t_idx, tb), w) in enumerate(zip(group, weights)):
                v_open = acc
                v_close = p_close if g_i == len(group) - 1 else acc + span * (w / total_w)
                acc = v_close
                start_frame = 0 if t_idx == 0 else int(round(v_open * fps))
                end_frame = total_frames if t_idx == len(tl_beats) - 1 else max(start_frame + 1, int(round(v_close * fps)))
                dur_frames = max(1, end_frame - start_frame)
                sp_open = max(v_open, s_start)
                sp_close = max(sp_open + 0.05, min(v_close, s_end))
                sp_offset_frames = max(0, int(round((sp_open - v_open) * fps)))
                sp_frames = max(1, min(dur_frames - sp_offset_frames, int(round((sp_close - sp_open) * fps))))
                pause_sec = float(tm["pause_after_sec"]) if g_i == len(group) - 1 else 0.0
                pause_rsn = str(tm["pause_reason"]) if g_i == len(group) - 1 else "visual_sub_unit"

                tb["startSec"] = round(v_open, 3)
                tb["endSec"] = round(v_close, 3)
                tb["durationSec"] = round(max(0.2, v_close - v_open), 3)
                tb["pauseAfterSec"] = pause_sec
                tb["pause_after_sec"] = pause_sec
                tb["pauseReason"] = pause_rsn
                tb["pause_reason"] = pause_rsn
                tb["startFrame"] = start_frame
                tb["endFrame"] = end_frame
                tb["durationInFrames"] = dur_frames
                tb["speechOffsetFrames"] = sp_offset_frames
                tb["speechFrames"] = sp_frames
                tb["partAFrames"] = dur_frames // 2
                tb["partBFrames"] = dur_frames - (dur_frames // 2)

                if not str(tb.get("narrationText") or "").strip() and tm.get("text"):
                    tb["narrationText"] = tm["text"]
                    tb["narration_text"] = tm["text"]

                if isinstance(tb.get("subShots"), list) and len(tb["subShots"]) >= 2:
                    subs = tb["subShots"]
                    old_durs = [max(1, int(s.get("durationInFrames") or 1)) for s in subs]
                    old_sum = sum(old_durs) or len(subs)
                    rem = dur_frames
                    for s_i, s_obj in enumerate(subs):
                        if s_i == len(subs) - 1:
                            s_obj["durationInFrames"] = max(1, rem)
                        else:
                            alloc = max(1, int(round(dur_frames * (old_durs[s_i] / old_sum))))
                            alloc = min(alloc, max(1, rem - (len(subs) - 1 - s_i)))
                            s_obj["durationInFrames"] = alloc
                            rem -= alloc

                if isinstance(tb.get("cinemaTextSpec"), dict):
                    tb["cinemaTextSpec"]["speechFrames"] = sp_frames

                existing_clauses = tb.get("clauses")
                c_wins = tb.get("clauseWindows")
                narr_str = str(tb.get("narrationText") or tb.get("narration_text") or tm.get("text") or "").strip()
                if narr_str and (
                    not isinstance(existing_clauses, list)
                    or not existing_clauses
                    or any(len(str(c or "")) > 24 for c in existing_clauses)
                    or not isinstance(c_wins, list)
                    or len(c_wins) != len(existing_clauses)
                ):
                    cw_tuples = split_multilang_narration_into_clauses(
                        narr_str,
                        max_chars=21,
                        words=tm.get("words") if len(group) == 1 else None,
                        voice_dur_sec=max(0.12, sp_close - sp_open),
                    )
                    if cw_tuples:
                        tb["clauses"] = [ct for ct, _, _ in cw_tuples]
                        c_wins = [[round(w0, 4), round(w1, 4)] for _, w0, w1 in cw_tuples]
                        tb["clauseWindows"] = c_wins

                if isinstance(c_wins, list) and c_wins:
                    new_cfw: list[list[int]] = []
                    new_sub_segs: list[dict] = []
                    clauses_list = tb.get("clauses") if isinstance(tb.get("clauses"), list) else []
                    sp_dur_sec = max(0.05, sp_close - sp_open)
                    for cw_i, cw in enumerate(c_wins):
                        if isinstance(cw, (list, tuple)) and len(cw) >= 2:
                            r0 = max(0.0, min(1.0, float(cw[0])))
                            r1 = max(r0, min(1.0, float(cw[1])))
                            cf0 = sp_offset_frames + (0 if cw_i == 0 else int(round(r0 * sp_frames)))
                            cf1 = (sp_offset_frames + sp_frames) if cw_i == len(c_wins) - 1 else max(cf0 + 1, sp_offset_frames + int(round(r1 * sp_frames)))
                            new_cfw.append([cf0, cf1])
                            if cw_i < len(clauses_list):
                                new_sub_segs.append(
                                    {
                                        "text": str(clauses_list[cw_i]),
                                        "startSec": round(sp_open + r0 * sp_dur_sec, 3),
                                        "endSec": round(sp_open + r1 * sp_dur_sec, 3),
                                    }
                                )
                    if new_cfw:
                        tb["clauseFrameWindows"] = new_cfw
                    if new_sub_segs:
                        tb["subSegments"] = new_sub_segs

                # Normalize any invalid SFX filenames
                sfx_f = str(tb.get("sfxFile") or "").strip()
                if sfx_f in sfx_alias_map:
                    tb["sfxFile"] = sfx_alias_map[sfx_f]
                if isinstance(tb.get("sfxEvents"), list):
                    for ev in tb["sfxEvents"]:
                        if isinstance(ev, dict):
                            ev_f = str(ev.get("file") or "").strip()
                            if ev_f in sfx_alias_map:
                                ev["file"] = sfx_alias_map[ev_f]

                if pause_sec >= 1.0 and (end_frame - (start_frame + sp_offset_frames + sp_frames)) >= 24:
                    hold_start = start_frame + sp_offset_frames + sp_frames
                    new_breath_lifts.append(
                        {
                            "beatId": str(tb.get("beatId") or tb.get("beat_id") or pid),
                            "startFrame": hold_start,
                            "endFrame": end_frame,
                            "peakVolume": 0.104 if pause_sec >= 1.45 else 0.094,
                        }
                    )

        # Update silence_windows to match updated beat frame boundaries
        tl_by_beat_id = {str(b.get("beatId") or b.get("beat_id") or ""): b for b in tl_beats if isinstance(b, dict)}
        if isinstance(tl_data.get("silence_windows"), list):
            for sw in tl_data["silence_windows"]:
                if isinstance(sw, dict):
                    sw_bid = str(sw.get("beatId") or "")
                    ref_b = tl_by_beat_id.get(sw_bid)
                    if ref_b:
                        b_sf = int(ref_b.get("startFrame") or 0)
                        b_ef = int(ref_b.get("endFrame") or (b_sf + 68))
                        sw_dur = max(48, min(90, int(sw.get("endFrame", 68)) - int(sw.get("startFrame", 0))))
                        sw["startFrame"] = b_sf
                        sw["endFrame"] = min(b_ef, b_sf + sw_dur)

        # Rescale BGM segments organically across [0 .. total_frames] (0% uniform equal-frame division)
        if isinstance(tl_data.get("bgm_segments"), list) and tl_data["bgm_segments"]:
            bgm_segs = tl_data["bgm_segments"]
            n_seg = len(bgm_segs)
            cf = 90
            base_arc_weights = [0.11, 0.14, 0.09, 0.13, 0.10, 0.15, 0.08, 0.11, 0.09, 0.12, 0.10, 0.13]
            raw_weights = [base_arc_weights[i % len(base_arc_weights)] for i in range(n_seg)]
            weight_sum = sum(raw_weights) or float(n_seg)
            usable_span = max(n_seg, total_frames - cf)
            cursor_f = 0
            for s_idx, seg in enumerate(bgm_segs):
                if not isinstance(seg, dict):
                    continue
                seg_span = int(round(usable_span * (raw_weights[s_idx] / weight_sum)))
                s_from = 0 if s_idx == 0 else max(0, cursor_f - cf)
                s_end = total_frames if s_idx == n_seg - 1 else min(total_frames, cursor_f + max(90, seg_span))
                cursor_f = min(total_frames, cursor_f + max(90, seg_span))
                seg["from"] = s_from
                seg["startFrame"] = s_from
                seg["endFrame"] = s_end
                seg["durationInFrames"] = max(90, s_end - s_from)

        if new_breath_lifts:
            tl_data["breath_lifts"] = new_breath_lifts

        if isinstance(tl_data.get("timeline"), list):
            tl_data["timeline"] = copy.deepcopy(tl_beats)
        if isinstance(tl_data.get("scenes"), list):
            tl_data["scenes"] = copy.deepcopy(tl_beats)

        tl_data["duration_sec"] = round(actual_total_dur, 3)
        tl_data["duration_frames"] = total_frames
        tl_data["editorial_voice_sculpted"] = True
        tl_data["editorial_summary"] = editorial_summary
        for target_name in ("timeline.json", "edit_manifest.json", "scenes.json"):
            t_path = workspace / target_name
            if t_path.is_file() or target_name == "timeline.json":
                t_path.write_text(json.dumps(tl_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Rebuild `edit_rhythm_score.json` if `documentary.edit.build_edit_rhythm_score` is available and visual_manifest exists
    if vis_data and isinstance(vis_data.get("beats"), list):
        try:
            from .edit import build_edit_rhythm_score

            build_edit_rhythm_score(job, workspace, vis_data["beats"])
        except Exception:
            pass

    timeline_changed = abs(actual_total_dur - prev_total_dur) > 0.015 or has_explicit_overrides
    remotion_sync = sync_remotion_public_audio_and_srt(
        job=job,
        workspace=workspace,
        remotion_dir=Path(remotion_dir) if remotion_dir else None,
        invalidate_render_cache=timeline_changed,
    )

    plan_payload = {
        **editorial_summary,
        "pause_adjustments": pause_adjustments,
        "mid_beat_caesuras": caesura_events,
        "overrides_active": overrides,
        "remotion_sync": remotion_sync,
    }
    plan_path = workspace / "editorial_voice_plan.json"
    plan_path.write_text(json.dumps(plan_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Re-mirror `editorial_voice_plan.json` and `timeline.json` after writing
    if remotion_sync.get("synced") and remotion_sync.get("public_job_dir"):
        pub_dir = Path(remotion_sync["public_job_dir"])
        shutil.copy2(plan_path, pub_dir / "editorial_voice_plan.json")
        for extra_f in ("timeline.json", "edit_manifest.json", "scenes.json", "voice_manifest.json", "visual_manifest.json"):
            src_extra = workspace / extra_f
            if src_extra.is_file() and (pub_dir / extra_f).is_file():
                shutil.copy2(src_extra, pub_dir / extra_f)

    return {
        "applied": True,
        "plan_path": str(plan_path),
        **plan_payload,
    }


def reset_editorial_voice_cuts(workspace: str | Path, *, job: dict[str, Any] | None = None, remotion_dir: Path | None = None) -> dict[str, Any]:
    """Restore untouched 1st-generation `voice_manifest.raw.json` & `audio/beats_raw/` stems."""
    workspace = Path(workspace).resolve()
    raw_manifest_path = workspace / "voice_manifest.raw.json"
    ov_path = workspace / "editorial_voice_overrides.json"
    if ov_path.exists():
        ov_path.unlink()
    if not raw_manifest_path.is_file():
        return {"reset": False, "reason": "no_raw_backup_present"}

    raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    beats = raw_manifest.get("beats") or []
    wavs: list[Path] = []
    pauses: list[float] = []
    for idx, b in enumerate(beats):
        bid = _beat_id(b)
        p = Path(str(b.get("raw_audio_path") or (workspace / "audio" / "beats_raw" / f"{bid}.wav")))
        if not p.is_file():
            p = workspace / "audio" / "beats" / f"{bid}.wav"
        b["audio_path"] = str(p)
        wavs.append(p)
        if idx < len(beats) - 1:
            pauses.append(float(b.get("pause_after_sec") or 0.0))

    narration_out = workspace / "audio" / "narration.wav"
    outro_tail = float(beats[-1].get("outro_tail_sec") or OUTRO_FADE_TAIL_SEC) if beats else OUTRO_FADE_TAIL_SEC
    dur = concat_timeline_wav_with_pre_and_outro(
        pre_voice_sec=0.0,
        beat_wavs=wavs,
        inter_beat_pauses=pauses,
        outro_tail_sec=outro_tail,
        output_path=narration_out,
    )
    raw_manifest["duration_sec"] = round(dur, 3)
    (workspace / "voice_manifest.json").write_text(json.dumps(raw_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (workspace / "subtitles.srt").write_text(build_srt(beats), encoding="utf-8")
    sync_remotion_public_audio_and_srt(job=job or {"id": workspace.name}, workspace=workspace, remotion_dir=remotion_dir, invalidate_render_cache=True)
    return {"reset": True, "duration_sec": round(dur, 3)}


def _parse_set_pause_arg(spec: str) -> tuple[str, float, str]:
    # Format: `B024=2.25` or `B024=2.25:chapter_curtain`
    if "=" not in spec:
        raise ValueError(f"Định dạng --set-pause không hợp lệ (cần Bxxx=giây[:lý_do]): {spec}")
    bid, rhs = spec.split("=", 1)
    if ":" in rhs:
        sec_s, reason = rhs.split(":", 1)
    else:
        sec_s, reason = rhs, "editor_manual_pause"
    return bid.strip(), float(sec_s.strip()), reason.strip() or "editor_manual_pause"


def _parse_set_caesura_arg(spec: str) -> tuple[str, dict[str, Any]]:
    # Format: `B042:before=백지:hold=0.78` or `B042:word_index=4:hold=0.75`
    parts = [p.strip() for p in spec.split(":") if p.strip()]
    if len(parts) < 2:
        raise ValueError(f"Định dạng --set-caesura không hợp lệ (cần Bxxx:before=<từ>:hold=<giây>): {spec}")
    bid = parts[0]
    cfg: dict[str, Any] = {"hold_sec": 0.76, "reason": "editor_manual_caesura"}
    for kv in parts[1:]:
        if "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        k = k.strip().lower()
        v = v.strip().strip('"').strip("'")
        if k in ("before", "before_word"):
            cfg["before_word"] = v
        elif k in ("word_index", "split_word_index", "index"):
            cfg["split_word_index"] = int(v)
        elif k in ("hold", "hold_sec"):
            cfg["hold_sec"] = float(v)
        elif k == "reason":
            cfg["reason"] = v
    return bid, cfg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Master Human Film Editor Voice Cutter & Timeline Sync CLI")
    parser.add_argument("--workspace", required=True, help="Path to episode workspace directory")
    parser.add_argument("--remotion-dir", default=None, help="Optional path to CofiRemotion directory")
    parser.add_argument("--inspect", action="store_true", help="Inspect current voice rhythm, pauses, and caesuras")
    parser.add_argument("--auto", action="store_true", help="Run automatic genre-calibrated editorial voice sculpting")
    parser.add_argument("--force", action="store_true", help="Force sculpting even on synthetic silent test WAVs")
    parser.add_argument("--pre-voice", type=float, default=None, help="Set cold-open pre-voice breath seconds (e.g. 1.35)")
    parser.add_argument("--set-pause", action="append", default=[], help="Override pause after beat: B024=2.20[:reason]")
    parser.add_argument("--set-caesura", action="append", default=[], help="Insert mid-beat split: B042:before=백지:hold=0.78")
    parser.add_argument("--disable-caesura", action="append", default=[], help="Disable mid-beat split on beat ID (e.g. B042)")
    parser.add_argument("--reset", action="store_true", help="Restore untouched 1st-gen voice stems")
    args = parser.parse_args(argv)

    ws = Path(args.workspace).resolve()
    job_json_path = ws / "job.json"
    job: dict[str, Any] = {"id": ws.name}
    if job_json_path.is_file():
        try:
            job = json.loads(job_json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    if args.reset:
        res = reset_editorial_voice_cuts(ws, job=job, remotion_dir=Path(args.remotion_dir) if args.remotion_dir else None)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    if args.inspect and not (args.auto or args.set_pause or args.set_caesura or args.pre_voice is not None or args.disable_caesura):
        vm_path = ws / "voice_manifest.json"
        if not vm_path.is_file():
            print(json.dumps({"error": "voice_manifest.json not found"}, ensure_ascii=False))
            return 1
        vm = json.loads(vm_path.read_text(encoding="utf-8"))
        beats = vm.get("beats") or []
        long_holds = [
            {"beat_id": _beat_id(b), "pause_after_sec": b.get("pause_after_sec"), "reason": b.get("pause_reason")}
            for b in beats
            if float(b.get("pause_after_sec") or 0.0) >= 1.15
        ]
        caesuras = [
            {"beat_id": _beat_id(b), "caesuras": b.get("editorial_caesuras")}
            for b in beats
            if b.get("editorial_caesuras")
        ]
        print(
            json.dumps(
                {
                    "workspace": str(ws),
                    "duration_sec": vm.get("duration_sec"),
                    "editorial_voice_sculpted": bool(vm.get("editorial_voice_sculpted")),
                    "pre_voice_breath_sec": vm.get("pre_voice_breath_sec", 0.0),
                    "total_beats": len(beats),
                    "dramatic_holds_over_1_15s": long_holds[:25],
                    "mid_beat_caesuras": caesuras,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    overrides = _load_overrides(ws)
    changed_ov = False
    if args.pre_voice is not None:
        overrides["pre_voice_sec"] = round(max(0.0, min(4.0, float(args.pre_voice))), 3)
        changed_ov = True
    for p_spec in args.set_pause:
        bid, p_sec, reason = _parse_set_pause_arg(p_spec)
        overrides.setdefault("pauses", {})[bid] = {"pause_sec": p_sec, "reason": reason}
        changed_ov = True
    for c_spec in args.set_caesura:
        bid, cfg = _parse_set_caesura_arg(c_spec)
        overrides.setdefault("caesuras", {})[bid] = cfg
        if bid in overrides.get("disabled_caesuras", []):
            overrides["disabled_caesuras"].remove(bid)
        changed_ov = True
    for d_bid in args.disable_caesura:
        clean_id = d_bid.strip()
        overrides.setdefault("caesuras", {}).pop(clean_id, None)
        if clean_id not in overrides.setdefault("disabled_caesuras", []):
            overrides["disabled_caesuras"].append(clean_id)
        changed_ov = True
    if changed_ov:
        _save_overrides(ws, overrides)

    res = sculpt_editorial_voice_timeline(
        job,
        ws,
        remotion_dir=args.remotion_dir,
        force_on_synthetic=bool(args.force or changed_ov),
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


def run_editorial_voice_cutter(
    job: dict[str, Any],
    workspace: str | Path,
    remotion_dir: str | Path | None = None,
    *,
    auto_detect: bool = True,
    force: bool = False,
    fps: int = FPS_DEFAULT,
) -> dict[str, Any]:
    return sculpt_editorial_voice_timeline(
        job=job,
        workspace=workspace,
        remotion_dir=remotion_dir,
        force_on_synthetic=force,
        fps=fps,
    )


if __name__ == "__main__":
    sys.exit(main())
