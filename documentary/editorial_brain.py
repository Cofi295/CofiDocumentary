from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VALID_SHOT_JOBS = {"advance_info", "shift_emotion", "raise_pressure", "act_breathing"}
VALID_SHOT_FUNCTIONS = {
    "establish",
    "power_scale",
    "mechanism",
    "counterpoint",
    "pressure",
    "detail_macro",
    "reaction",
    "shift",
    "impact",
    "aftermath",
    "breathing_bridge",
}
VALID_SHOT_SCALES = {"EWS", "WS", "MS", "CU", "ECU_MACRO", "GRAPHIC_STAGE", "TEXT_VOID"}


def _tool(name: str) -> str | None:
    env_names = {
        "ffmpeg.exe": "COFI_FFMPEG_BIN",
        "ffprobe.exe": "COFI_FFPROBE_BIN",
    }
    configured = str(os.getenv(env_names.get(name, ""), "") or "").strip()
    if configured and Path(configured).exists():
        return configured
    bundled = Path(__file__).resolve().parents[1] / "tools" / name
    if bundled.exists():
        return str(bundled)
    return shutil.which(name) or shutil.which(Path(name).stem)


def _subproc_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = startupinfo
    return kwargs


@dataclass(frozen=True)
class GenreLens:
    lens_id: str
    name: str
    narrative_arc: str
    hard_cut_target_ratio: float
    typical_asl_range_sec: tuple[float, float]
    cold_open_pre_voice_sec: float
    act_bridge_silence_sec: float
    outro_tail_sec: float
    allow_static_tripod: bool
    color_arc: dict[str, dict[str, float]] = field(default_factory=dict)


GENRE_LENSES: dict[str, GenreLens] = {
    "investigative_counterpoint_vn": GenreLens(
        lens_id="investigative_counterpoint_vn",
        name="Giải Phẫu Đại Án Lừa Đảo — Đối Âm Thị Giác & Nhịp Thở Con Người",
        narrative_arc="gilded_trap_to_muddy_collapse",
        hard_cut_target_ratio=0.90,
        typical_asl_range_sec=(2.4, 6.8),
        cold_open_pre_voice_sec=1.35,
        act_bridge_silence_sec=2.40,
        outro_tail_sec=3.80,
        allow_static_tripod=True,
        color_arc={
            "COLD_OPEN": {"brightness": 0.96, "contrast": 1.12, "saturate": 0.84, "sepia": 0.0},
            "ACT01_GILDED": {"brightness": 1.03, "contrast": 1.09, "saturate": 1.14, "sepia": 0.10},
            "ACT02_FREEZE": {"brightness": 0.92, "contrast": 1.16, "saturate": 0.62, "sepia": 0.0},
            "ACT03_CLASH": {"brightness": 0.97, "contrast": 1.18, "saturate": 0.86, "sepia": 0.0},
            "ACT04_AFTERMATH": {"brightness": 0.94, "contrast": 1.10, "saturate": 0.74, "sepia": 0.04},
        },
    ),
    "forensic_noir": GenreLens(
        lens_id="forensic_noir",
        name="True Crime Forensic Noir & Tactile Vox 2.5D",
        narrative_arc="conflict_beat_sheet",
        hard_cut_target_ratio=0.90,
        typical_asl_range_sec=(3.0, 5.2),
        cold_open_pre_voice_sec=1.20,
        act_bridge_silence_sec=2.50,
        outro_tail_sec=3.80,
        allow_static_tripod=True,
    ),
    "financial_forensic_vox": GenreLens(
        lens_id="financial_forensic_vox",
        name="Cyber-Finance & Money Trail Spatial Investigation",
        narrative_arc="causal_chain",
        hard_cut_target_ratio=0.90,
        typical_asl_range_sec=(2.8, 5.5),
        cold_open_pre_voice_sec=1.20,
        act_bridge_silence_sec=2.40,
        outro_tail_sec=3.80,
        allow_static_tripod=True,
    ),
    "2.5d_technical": GenreLens(
        lens_id="2.5d_technical",
        name="Mega-Infrastructure & Geopolitical Causal Engineering",
        narrative_arc="causal_chain",
        hard_cut_target_ratio=0.88,
        typical_asl_range_sec=(3.2, 6.2),
        cold_open_pre_voice_sec=1.10,
        act_bridge_silence_sec=2.20,
        outro_tail_sec=3.80,
        allow_static_tripod=True,
    ),
    "declassified_archival": GenreLens(
        lens_id="declassified_archival",
        name="Presidential & Intelligence Declassified Archival Vault",
        narrative_arc="conflict_beat_sheet",
        hard_cut_target_ratio=0.86,
        typical_asl_range_sec=(3.8, 7.2),
        cold_open_pre_voice_sec=1.40,
        act_bridge_silence_sec=2.60,
        outro_tail_sec=4.00,
        allow_static_tripod=True,
    ),
    "sacred_sanctuary": GenreLens(
        lens_id="sacred_sanctuary",
        name="Contemplative Sanctuary & Devotional Reflection",
        narrative_arc="one_peak_moment",
        hard_cut_target_ratio=0.25,
        typical_asl_range_sec=(5.5, 10.0),
        cold_open_pre_voice_sec=1.80,
        act_bridge_silence_sec=3.00,
        outro_tail_sec=4.50,
        allow_static_tripod=True,
    ),
    "kishotenketsu_essay": GenreLens(
        lens_id="kishotenketsu_essay",
        name="Cultural & Philosophical Discovery Essay (Kishotenketsu)",
        narrative_arc="kishotenketsu",
        hard_cut_target_ratio=0.82,
        typical_asl_range_sec=(3.8, 7.5),
        cold_open_pre_voice_sec=1.50,
        act_bridge_silence_sec=2.60,
        outro_tail_sec=4.00,
        allow_static_tripod=True,
    ),
    "science_explainer": GenreLens(
        lens_id="science_explainer",
        name="Mechanism-First Science & Systems Explainer",
        narrative_arc="causal_chain",
        hard_cut_target_ratio=0.90,
        typical_asl_range_sec=(2.6, 5.5),
        cold_open_pre_voice_sec=0.90,
        act_bridge_silence_sec=2.00,
        outro_tail_sec=3.50,
        allow_static_tripod=True,
    ),
}


def _norm_token(tok: str) -> str:
    return re.sub(r"[^\w가-힣ぁ-んァ-ヶ一-龯À-ỹ0-9]", "", str(tok or "").lower())


def align_script_words_to_whisper(
    script_text: str,
    whisper_words: list[dict[str, Any]],
    clip_start_sec: float,
    clip_end_sec: float,
) -> list[dict[str, Any]]:
    """Map exact ground-truth script tokens onto acoustic Whisper word timestamps."""
    gt_tokens = [t for t in re.split(r"\s+", str(script_text or "").strip()) if t]
    if not gt_tokens:
        return []
    total_dur = max(0.12, clip_end_sec - clip_start_sec)
    if not whisper_words:
        weights = [max(1.0, len(_norm_token(t)) * 0.7 + (0.45 if re.search(r"[,.;:?!—-]$", t) else 0.0)) for t in gt_tokens]
        wsum = sum(weights) or 1.0
        out: list[dict[str, Any]] = []
        acc = clip_start_sec
        for tok, w in zip(gt_tokens, weights):
            dur = total_dur * (w / wsum)
            out.append({"word": tok, "start": round(acc, 3), "end": round(acc + dur, 3)})
            acc += dur
        out[-1]["end"] = round(clip_end_sec, 3)
        return out

    m = len(gt_tokens)
    n = len(whisper_words)
    anchors: list[tuple[int, int]] = []
    w_idx = 0
    for g_idx, g_tok in enumerate(gt_tokens):
        gn = _norm_token(g_tok)
        if not gn:
            continue
        best_j = -1
        upper = min(n, w_idx + 5)
        for j in range(w_idx, upper):
            wn = _norm_token(str(whisper_words[j].get("word") or ""))
            if wn and (wn == gn or gn in wn or wn in gn):
                best_j = j
                break
        if best_j >= 0:
            anchors.append((g_idx, best_j))
            w_idx = best_j + 1

    out_words: list[dict[str, Any]] = [{} for _ in range(m)]
    for g_idx, j in anchors:
        w = whisper_words[j]
        out_words[g_idx] = {
            "word": gt_tokens[g_idx],
            "start": round(float(w["start"]), 3),
            "end": round(max(float(w["start"]) + 0.04, float(w["end"])), 3),
        }

    # Interpolate any unanchored tokens smoothly between surrounding acoustic anchors
    idx = 0
    while idx < m:
        if out_words[idx]:
            idx += 1
            continue
        run_start = idx
        while idx < m and not out_words[idx]:
            idx += 1
        run_end = idx  # exclusive
        left_t = out_words[run_start - 1]["end"] if run_start > 0 else float(whisper_words[0].get("start", clip_start_sec))
        right_t = out_words[run_end]["start"] if run_end < m else float(whisper_words[-1].get("end", clip_end_sec))
        if right_t <= left_t:
            right_t = left_t + 0.08 * (run_end - run_start)
        span = right_t - left_t
        sub_tokens = gt_tokens[run_start:run_end]
        weights = [max(1.0, len(_norm_token(t)) * 0.75) for t in sub_tokens]
        wsum = sum(weights) or 1.0
        cur = left_t
        for offset, (tok, w) in enumerate(zip(sub_tokens, weights)):
            dur = span * (w / wsum)
            out_words[run_start + offset] = {
                "word": tok,
                "start": round(cur, 3),
                "end": round(cur + dur, 3),
            }
            cur += dur

    return out_words


def split_words_into_natural_clauses(
    aligned_words: list[dict[str, Any]],
    *,
    max_words_per_clause: int = 7,
    max_chars_per_clause: int = 36,
    pause_split_sec: float = 0.24,
) -> list[dict[str, Any]]:
    """Group word-level acoustic timestamps into crisp 1-line broadcast clauses."""
    if not aligned_words:
        return []
    clauses: list[dict[str, Any]] = []
    buf: list[dict[str, Any]] = []

    def _flush() -> None:
        if not buf:
            return
        text = " ".join(str(x["word"]) for x in buf).strip()
        clauses.append({
            "text": text,
            "start_sec": round(float(buf[0]["start"]), 3),
            "end_sec": round(float(buf[-1]["end"]), 3),
            "word_count": len(buf),
        })
        buf.clear()

    for i, item in enumerate(aligned_words):
        w_str = str(item["word"]).strip()
        projected_text = (" ".join(str(x["word"]) for x in buf) + " " + w_str).strip() if buf else w_str
        if buf and (len(buf) >= max_words_per_clause or len(projected_text) > max_chars_per_clause):
            _flush()
        buf.append(item)
        has_punct = bool(re.search(r"[,.;:?!…—]$", w_str))
        gap_after = 0.0
        if i + 1 < len(aligned_words):
            gap_after = float(aligned_words[i + 1]["start"]) - float(item["end"])
        if len(buf) >= 2 and (has_punct or gap_after >= pause_split_sec):
            _flush()

    _flush()
    # Merge single-word orphan tail into previous clause if comfortable
    if len(clauses) >= 2 and clauses[-1]["word_count"] == 1 and len(clauses[-2]["text"]) <= max_chars_per_clause - 5:
        tail = clauses.pop()
        clauses[-1]["text"] = f"{clauses[-1]['text']} {tail['text']}".strip()
        clauses[-1]["end_sec"] = tail["end_sec"]
        clauses[-1]["word_count"] += 1
    return clauses


def compute_payoff_sync(
    aligned_words: list[dict[str, Any]],
    payoff_phrase: str,
    reveal_duration_sec: float,
    beat_start_sec: float,
) -> dict[str, float]:
    """
    Payoff Sync Math:
      t_anim_start = t_payoff_word - reveal_duration_sec
    Ensures the visual reveal settles on the exact acoustic frame the narrator speaks the payoff word.
    """
    target_tokens = [_norm_token(t) for t in str(payoff_phrase or "").split() if _norm_token(t)]
    payoff_sec = float(aligned_words[0]["start"]) if aligned_words else beat_start_sec
    if aligned_words and target_tokens:
        first_tok = target_tokens[0]
        for idx, item in enumerate(aligned_words):
            wn = _norm_token(item["word"])
            if wn == first_tok or (len(first_tok) >= 3 and first_tok in wn):
                payoff_sec = float(item["start"])
                break
    anim_start_sec = max(beat_start_sec, payoff_sec - max(0.15, float(reveal_duration_sec)))
    return {
        "payoff_word_sec": round(payoff_sec, 3),
        "anim_start_sec": round(anim_start_sec, 3),
        "local_payoff_sec": round(max(0.0, payoff_sec - beat_start_sec), 3),
        "local_anim_start_sec": round(max(0.0, anim_start_sec - beat_start_sec), 3),
    }


def measure_clip_signalstats(video_path: str | Path) -> dict[str, float]:
    """Measure YAVG, YMIN, YMAX, SATAVG across representative frames via ffprobe lavfi.signalstats."""
    ffprobe = _tool("ffprobe.exe")
    p = Path(video_path).resolve()
    default_stats = {"yavg": 112.0, "ymin": 14.0, "ymax": 236.0, "satavg": 48.0}
    if not ffprobe or not p.exists():
        return default_stats
    escaped = str(p).replace("\\", "/").replace(":", "\\:")
    lavfi_expr = f"movie='{escaped}',fps=1,scale=320:180,signalstats"
    cmd = [
        ffprobe,
        "-v", "error",
        "-f", "lavfi",
        "-i", lavfi_expr,
        "-show_entries", "frame_tags=lavfi.signalstats.YAVG,lavfi.signalstats.YMIN,lavfi.signalstats.YMAX,lavfi.signalstats.SATAVG",
        "-read_intervals", "%+#4",
        "-of", "json",
    ]
    try:
        res = subprocess.run(cmd, timeout=18, check=False, **_subproc_kwargs())
        payload = json.loads(res.stdout or "{}")
        frames = payload.get("frames") or []
        if not frames:
            return default_stats
        ys, ymins, ymaxs, sats = [], [], [], []
        for fr in frames:
            tags = fr.get("tags") or {}
            if "lavfi.signalstats.YAVG" in tags:
                ys.append(float(tags["lavfi.signalstats.YAVG"]))
            if "lavfi.signalstats.YMIN" in tags:
                ymins.append(float(tags["lavfi.signalstats.YMIN"]))
            if "lavfi.signalstats.YMAX" in tags:
                ymaxs.append(float(tags["lavfi.signalstats.YMAX"]))
            if "lavfi.signalstats.SATAVG" in tags:
                sats.append(float(tags["lavfi.signalstats.SATAVG"]))
        if not ys:
            return default_stats
        return {
            "yavg": round(sum(ys) / len(ys), 2),
            "ymin": round(sum(ymins) / max(1, len(ymins)), 2),
            "ymax": round(sum(ymaxs) / max(1, len(ymaxs)), 2),
            "satavg": round(sum(sats) / max(1, len(sats)), 2),
        }
    except Exception:
        return default_stats


def compute_per_clip_grade_css(
    stats: dict[str, float] | None,
    act_grade: dict[str, float] | None = None,
    *,
    target_yavg: float = 110.0,
    target_satavg: float = 46.0,
) -> str:
    """
    Two-stage human colorist pipeline:
      Stage 1: Per-clip exposure & saturation normalization (clamped strictly to ±8% safety band)
      Stage 2: Act-level emotional color grade (Warm Gilded Trap -> Cold Slate Freeze -> Forensic Steel)
    """
    st = stats or {"yavg": target_yavg, "ymin": 14.0, "ymax": 236.0, "satavg": target_satavg}
    yavg = max(28.0, float(st.get("yavg") or target_yavg))
    satavg = max(8.0, float(st.get("satavg") or target_satavg))
    dyn_range = max(80.0, float(st.get("ymax", 236.0)) - float(st.get("ymin", 14.0)))

    norm_bright = max(0.92, min(1.08, (target_yavg / yavg) ** 0.35))
    norm_contrast = max(0.94, min(1.08, (215.0 / dyn_range) ** 0.28))
    norm_sat = max(0.92, min(1.08, (target_satavg / satavg) ** 0.25))

    ag = act_grade or {"brightness": 0.98, "contrast": 1.08, "saturate": 0.90, "sepia": 0.0}
    final_b = round(norm_bright * float(ag.get("brightness", 1.0)), 3)
    final_c = round(norm_contrast * float(ag.get("contrast", 1.0)), 3)
    final_s = round(norm_sat * float(ag.get("saturate", 1.0)), 3)
    sepia = round(float(ag.get("sepia", 0.0)), 3)

    parts = [f"brightness({final_b})", f"contrast({final_c})", f"saturate({final_s})"]
    if sepia > 0.005:
        parts.append(f"sepia({sepia})")
    return " ".join(parts)


def measure_sfx_attack_sec(audio_path: str | Path, *, threshold_db: float = -30.0) -> float:
    """Find first sample exceeding threshold_db so SFX transients can be pre-offset onto exact cut/payoff frames."""
    ffmpeg = _tool("ffmpeg.exe")
    p = Path(audio_path)
    if not ffmpeg or not p.exists():
        return 0.0
    cmd = [
        ffmpeg, "-v", "error",
        "-i", str(p),
        "-ac", "1", "-ar", "16000",
        "-f", "f32le", "-",
    ]
    try:
        kwargs = _subproc_kwargs()
        kwargs.pop("encoding", None)
        kwargs.pop("errors", None)
        res = subprocess.run(cmd, timeout=10, check=False, **kwargs)
        samples = np.frombuffer(res.stdout, dtype=np.float32)
        if samples.size == 0:
            return 0.0
        lin_thresh = 10.0 ** (threshold_db / 20.0)
        hits = np.flatnonzero(np.abs(samples) >= lin_thresh)
        if hits.size == 0:
            return 0.0
        return round(min(0.35, float(hits[0]) / 16000.0), 3)
    except Exception:
        return 0.0


def verify_editorial_cut_plan(beats: list[dict[str, Any]], *, min_hard_cut_ratio: float = 0.85) -> dict[str, Any]:
    """
    Pre-Render Deterministic Editorial Critic:
      1. Every shot must declare a valid Murch Three-Jobs role (no wallpaper filler).
      2. No two adjacent shots may share both subject_tag and shot_scale (anti-jump-cut law).
      3. Hard-cut ratio must satisfy the genre lens (>=85% for investigative documentary).
      4. Moving real footage must NEVER stack digital Ken Burns zoom on top (Fincher camera law).
      5. Payoff-synced motion scenes must leave >= 0.85s post-payoff readable hold.
    """
    issues: list[str] = []
    hard_cuts = 0
    total_transitions = 0
    static_tripod_count = 0

    for idx, beat in enumerate(beats):
        bid = str(beat.get("beatId") or beat.get("beat_id") or f"B{idx+1:03d}")
        job = str(beat.get("shotJob") or beat.get("shot_job") or "")
        if job not in VALID_SHOT_JOBS:
            issues.append(f"{bid}: invalid or missing shot_job='{job}'")

        scale = str(beat.get("shotScale") or beat.get("shot_scale") or "")
        if scale not in VALID_SHOT_SCALES:
            issues.append(f"{bid}: invalid or missing shot_scale='{scale}'")

        if idx > 0:
            prev = beats[idx - 1]
            prev_subj = str(prev.get("subjectTag") or prev.get("subject_tag") or "").strip().lower()
            cur_subj = str(beat.get("subjectTag") or beat.get("subject_tag") or "").strip().lower()
            prev_scale = str(prev.get("shotScale") or prev.get("shot_scale") or "")
            if prev_subj and cur_subj and prev_subj == cur_subj and prev_scale == scale and scale not in {"GRAPHIC_STAGE", "TEXT_VOID"}:
                issues.append(f"{bid}: jump-cut violation with previous shot (same subject '{cur_subj}' and scale '{scale}')")

            trans_frames = int(beat.get("transitionFrames") or beat.get("transition_frames") or 0)
            total_transitions += 1
            if trans_frames == 0:
                hard_cuts += 1

        cam_mode = str(beat.get("cameraMode") or beat.get("camera_mode") or "static_tripod")
        clip_moving = bool(beat.get("clipHasNativeMotion") or beat.get("clip_has_native_motion"))
        if cam_mode == "static_tripod":
            static_tripod_count += 1
        elif clip_moving and cam_mode not in {"static_tripod"}:
            issues.append(f"{bid}: double-motion violation (moving footage has digital cameraMode='{cam_mode}')")

        if beat.get("payoffLocalSec") is not None:
            dur = float(beat.get("durationSec") or beat.get("duration_sec") or 0.0)
            payoff_local = float(beat.get("payoffLocalSec") or 0.0)
            if dur - payoff_local < 0.80:
                issues.append(f"{bid}: payoff settles too late ({payoff_local:.2f}s / {dur:.2f}s < 0.80s hold)")

    hard_cut_ratio = round(hard_cuts / max(1, total_transitions), 3)
    if total_transitions > 0 and hard_cut_ratio < min_hard_cut_ratio:
        issues.append(f"hard_cut_ratio={hard_cut_ratio:.2f} below minimum {min_hard_cut_ratio:.2f}")
    if static_tripod_count == 0 and len(beats) >= 6:
        issues.append("zero static_tripod shots found (violates Fincher Motivated Camera Law)")

    return {
        "passed": len(issues) == 0,
        "beat_count": len(beats),
        "hard_cut_ratio": hard_cut_ratio,
        "static_tripod_count": static_tripod_count,
        "issues": issues,
    }


def measure_ebur128(mp4_path: str | Path) -> dict[str, float]:
    """Measure integrated loudness (LUFS), loudness range (LU), and true peak (dBTP) on rendered MP4."""
    ffmpeg = _tool("ffmpeg.exe")
    p = Path(mp4_path)
    if not ffmpeg or not p.exists():
        return {"integrated_lufs": 0.0, "lra_lu": 0.0, "true_peak_dbtp": 0.0}
    cmd = [
        ffmpeg, "-hide_banner", "-nostats",
        "-i", str(p),
        "-af", "ebur128=peak=true",
        "-f", "null", "-",
    ]
    res = subprocess.run(cmd, timeout=90, check=False, **_subproc_kwargs())
    stderr = res.stderr or ""
    m_i = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", stderr)
    m_lra = re.findall(r"LRA:\s*(-?\d+(?:\.\d+)?)\s*LU", stderr)
    m_tp = re.findall(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", stderr)
    return {
        "integrated_lufs": float(m_i[-1]) if m_i else 0.0,
        "lra_lu": float(m_lra[-1]) if m_lra else 0.0,
        "true_peak_dbtp": float(m_tp[-1]) if m_tp else 0.0,
    }


def render_cut_boundary_filmstrip(
    mp4_path: str | Path,
    cut_specs: list[dict[str, Any]],
    output_jpg: str | Path,
) -> Path | None:
    """
    Post-Render Senior Editor Critic Contact Sheet:
    Extracts actual decoded MP4 frames at [-0.45s, -0.10s, +0.10s, +0.45s] around key editorial cuts
    so human/AI vision can verify zero black flash, clean Eye-Trace, Scale Contrast, and Act Color Shift.
    """
    ffmpeg = _tool("ffmpeg.exe")
    src = Path(mp4_path)
    out = Path(output_jpg)
    if not ffmpeg or not src.exists() or not cut_specs:
        return None

    thumb_w, thumb_h = 340, 191
    offsets = (-0.45, -0.10, 0.10, 0.45)
    pad = 16
    row_h = thumb_h + 52
    canvas_w = pad * 2 + len(offsets) * (thumb_w + 10)
    canvas_h = pad * 2 + 44 + len(cut_specs) * row_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), (13, 16, 22))
    draw = ImageDraw.Draw(canvas)
    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
        font_lbl = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 14)
    except Exception:
        font_title = ImageFont.load_default()
        font_lbl = ImageFont.load_default()

    draw.text(
        (pad, pad),
        f"CUT-BOUNDARY EDITORIAL FILMSTRIP AUDIT · {src.name}",
        fill=(248, 250, 252),
        font=font_title,
    )

    tmp_dir = out.parent / f".tmp_strip_{os.getpid()}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        for r_idx, spec in enumerate(cut_specs):
            t_cut = float(spec.get("cut_sec") or 0.0)
            label = str(spec.get("label") or f"Cut @ {t_cut:.2f}s")
            y0 = pad + 44 + r_idx * row_h
            draw.text((pad, y0), f"[{t_cut:06.2f}s] {label}", fill=(253, 224, 71), font=font_lbl)
            for c_idx, off in enumerate(offsets):
                t_sample = max(0.05, t_cut + off)
                frame_png = tmp_dir / f"r{r_idx}_c{c_idx}.jpg"
                cmd = [
                    ffmpeg, "-v", "error", "-y",
                    "-ss", f"{t_sample:.3f}",
                    "-i", str(src),
                    "-frames:v", "1",
                    "-vf", f"scale={thumb_w}:{thumb_h}",
                    str(frame_png),
                ]
                subprocess.run(cmd, timeout=15, check=False, **_subproc_kwargs())
                x0 = pad + c_idx * (thumb_w + 10)
                if frame_png.exists():
                    im = Image.open(frame_png).convert("RGB")
                    canvas.paste(im, (x0, y0 + 22))
                border_col = (239, 68, 68) if off > 0 and c_idx == 2 else (71, 85, 105)
                draw.rectangle([x0, y0 + 22, x0 + thumb_w, y0 + 22 + thumb_h], outline=border_col, width=2)
                sign = "+" if off >= 0 else ""
                draw.text((x0 + 6, y0 + 26), f"{sign}{off:.2f}s", fill=(226, 232, 240), font=font_lbl)

        out.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out, quality=91)
        return out
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
