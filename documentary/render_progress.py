"""Live render-progress parsing for the final export phase.

Pure helpers (no service state) so they can be unit-tested against real
Remotion / UniversalMasterRender logs. The export progress endpoint must never
depend on the on-disk chunk ``status`` alone: older render launchers (and
``prepare()`` calls made while a render is in flight) can leave a chunk marked
``pending`` while its log is actively growing. Log activity is therefore the
source of truth for "this chunk is rendering right now".
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Iterable

_FRAME_RE = re.compile(
    r"(Rendered|Encoded)\s+(\d+)/(\d+)(?:,\s*time remaining:\s*([^\r\n\x1b]+))?"
)
_BAKE_RE = re.compile(r"\[AutoBakeStandalone\]\s+\[(\d+)/(\d+)\]\s+Baked\s+([^\r\n]+)")
_BAKE_INIT_RE = re.compile(r"\[AutoBakeStandalone\]\s+Bundling\s+(\d+)\s+live")
_COPY_RE = re.compile(r"Copying public dir\s+([0-9.]+\s*[A-Za-z]+)")
_BUNDLE_RE = re.compile(r"Bundling\s+(\d+)%")
_ETA_PART_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(h|m|s|ms)\b")

# A log that has not been written for this long is not considered "live"
# unless the manifest explicitly says the chunk is rendering.
LIVE_LOG_WINDOW_SEC = 180.0


def parse_eta_seconds(text: str | None) -> float | None:
    """Parse Remotion ETA strings such as ``"12m 54s"``, ``"45s"``, ``"1h 2m"``."""
    raw = str(text or "").strip()
    if not raw:
        return None
    total = 0.0
    found = False
    for value, unit in _ETA_PART_RE.findall(raw):
        found = True
        v = float(value)
        if unit == "h":
            total += v * 3600
        elif unit == "m":
            total += v * 60
        elif unit == "s":
            total += v
        elif unit == "ms":
            total += v / 1000.0
    if not found:
        try:
            return max(0.0, float(raw))
        except ValueError:
            return None
    return max(0.0, total)


def format_eta(seconds: float | None) -> str:
    if seconds is None:
        return ""
    s = max(0, int(round(seconds)))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m}m {sec:02d}s"
    return f"{sec}s"


def read_log_tail(path: str | Path, max_bytes: int = 65_536) -> str:
    """Read the tail of a log that another process is still writing to."""
    try:
        with open(path, "rb") as fh:  # CRT open shares read/write on Windows
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - max_bytes), os.SEEK_SET)
            return fh.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def parse_render_log(text: str) -> dict[str, Any]:
    """Return the latest render state visible in a log tail.

    Keys: ``stage`` (rendering|encoding|baking|bake_init|composition|copying|
    bundling|unknown), ``done``/``total`` frames (when known), ``eta_seconds``,
    ``fraction`` (0..1 of this chunk's work) and a short Vietnamese ``detail``.
    """
    text = text or ""
    frames = _FRAME_RE.findall(text)
    bakes = _BAKE_RE.findall(text)
    bake_init = _BAKE_INIT_RE.findall(text)
    if frames:
        kind, done_s, total_s, eta_s = frames[-1]
        done, total = int(done_s), max(1, int(total_s))
        done = min(done, total)
        eta = parse_eta_seconds(eta_s)
        ratio = done / total
        has_bake = bool(bakes or bake_init)
        if kind == "Encoded":
            # Encoded lines come after all frames were rendered.
            fraction = 0.97 + 0.025 * ratio
            stage = "encoding"
        else:
            base, span = (0.55, 0.42) if has_bake else (0.03, 0.94)
            fraction = base + span * ratio
            stage = "rendering"
        return {
            "stage": stage,
            "done": done,
            "total": total,
            "eta_seconds": eta,
            "fraction": max(0.0, min(0.995, fraction)),
        }
    if bakes:
        b_done, b_total, label = bakes[-1]
        bd, bt = int(b_done), max(1, int(b_total))
        return {
            "stage": "baking",
            "bake_done": bd,
            "bake_total": bt,
            "bake_label": label.strip(),
            "fraction": max(0.03, min(0.55, 0.03 + 0.52 * bd / bt)),
        }
    if bake_init:
        return {"stage": "bake_init", "bake_total": int(bake_init[-1]), "fraction": 0.02}
    if "Getting composition" in text:
        return {"stage": "composition", "fraction": 0.025}
    if "[UniversalMasterExport] Subtitles ready" in text:
        return {"stage": "turbo_plan", "detail": "subtitles", "fraction": 0.028}
    if "[UniversalMasterExport]" in text:
        return {"stage": "turbo_plan", "detail": "plan", "fraction": 0.024}
    copies = _COPY_RE.findall(text)
    if copies:
        return {"stage": "copying", "copied": copies[-1], "fraction": 0.02}
    bundles = _BUNDLE_RE.findall(text)
    if bundles:
        pct = max(0, min(100, int(bundles[-1])))
        return {"stage": "bundling", "bundle_pct": pct, "fraction": 0.005 + 0.01 * pct / 100.0}
    return {"stage": "unknown", "fraction": 0.0}


def _chunk_frames(chunk: dict[str, Any]) -> int:
    try:
        return max(1, int(chunk.get("end_frame")) - int(chunk.get("start_frame")) + 1)
    except (TypeError, ValueError):
        return 1


def aggregate_chunk_progress(
    chunks: Iterable[dict[str, Any]],
    *,
    now: float | None = None,
    live_window_sec: float = LIVE_LOG_WINDOW_SEC,
) -> dict[str, Any]:
    """Sum live progress over every chunk (parallel chunks supported).

    Returns ``frames_done``/``frames_total`` (over all chunks, ready chunks
    count fully), ``fraction`` (0..1 overall render work), ``eta_seconds``
    (max over live chunks, i.e. wall-clock until the slowest finishes),
    ``active`` (number of live chunks) and ``states`` per live chunk.
    """
    now = time.time() if now is None else now
    frames_total = 0
    work_done = 0.0
    frames_done = 0
    active = 0
    etas: list[float] = []
    states: list[dict[str, Any]] = []
    for chunk in chunks or []:
        if not isinstance(chunk, dict):
            continue
        n = _chunk_frames(chunk)
        frames_total += n
        status = str(chunk.get("status") or "").lower()
        if status == "ready":
            work_done += n
            frames_done += n
            continue
        log_file = Path(str(chunk.get("log_path") or ""))
        if not str(chunk.get("log_path") or "") or not log_file.is_file():
            continue
        try:
            age = now - log_file.stat().st_mtime
        except OSError:
            continue
        if status != "rendering" and age > live_window_sec:
            continue  # stale log from an earlier attempt
        state = parse_render_log(read_log_tail(log_file))
        if state.get("stage") == "rendering" and state.get("done") and state.get("done") >= state.get("total", 0):
            # All frames drawn; concat + audio mix/loudnorm still running with no
            # frame counter. Creep 0.97 -> 0.995 over ~2 min so the bar keeps moving.
            state["fraction"] = 0.97 + 0.025 * min(1.0, max(0.0, age) / 120.0)
        state["index"] = chunk.get("index")
        state["log_age_sec"] = round(max(0.0, age), 1)
        active += 1
        work_done += n * float(state.get("fraction") or 0.0)
        if state.get("done") is not None and state.get("total"):
            # Map the log's own frame counter onto this chunk's frame span.
            frames_done += int(round(n * state["done"] / max(1, state["total"])))
        if state.get("eta_seconds") is not None:
            etas.append(float(state["eta_seconds"]))
        states.append(state)
    frames_total = max(0, frames_total)
    return {
        "frames_done": frames_done,
        "frames_total": frames_total,
        "fraction": (work_done / frames_total) if frames_total else 0.0,
        "eta_seconds": max(etas) if etas else None,
        "active": active,
        "states": states,
    }


def describe_states(agg: dict[str, Any], fps: float | None = None) -> str:
    """Short human detail for the UI message (Vietnamese)."""
    states = agg.get("states") or []
    if not states:
        return ""
    lead = states[0]
    stage = lead.get("stage")
    multi = f" · {len(states)} đoạn song song" if len(states) > 1 else ""
    if stage in {"rendering", "encoding"}:
        done, total = int(agg.get("frames_done") or 0), max(1, int(agg.get("frames_total") or 1))
        verb = "Đã nén" if stage == "encoding" else "Đã dựng"
        parts = [f" · {verb} {done:,}/{total:,} frame ({done * 100.0 / total:.1f}%)"]
        if fps and fps > 0 and done < total:
            parts.append(f" · {fps:.1f} fps")
        eta = agg.get("eta_seconds")
        if eta is not None:
            parts.append(f" · còn khoảng {format_eta(eta)}")
        if stage == "rendering" and done >= total:
            parts.append(" · đang ghép tiếng & đóng gói đoạn")
        return "".join(parts) + multi
    if stage == "baking":
        return f" · Đang bake đồ họa Vox/CinemaText {lead.get('bake_done')}/{lead.get('bake_total')} ({lead.get('bake_label')})" + multi
    if stage == "bake_init":
        return f" · Đang đóng gói {lead.get('bake_total')} cảnh đồ họa Vox/CinemaText..." + multi
    if stage == "composition":
        return " · Đang khởi tạo bố cục video trong trình duyệt..." + multi
    if stage == "turbo_plan":
        if lead.get("detail") == "subtitles":
            return " · Turbo: phụ đề sẵn sàng · đang khởi động dựng shot NVENC..." + multi
        return " · Turbo: đang lập kế hoạch shot & kiểm tra cache VOX/CinemaText..." + multi
    if stage == "copying":
        return f" · Đang nạp tài nguyên dự án ({lead.get('copied')})..." + multi
    if stage == "bundling":
        return f" · Đang đóng gói Remotion bundle ({lead.get('bundle_pct')}%)..." + multi
    return " · Đang khởi động tiến trình render..." + multi


class FpsTracker:
    """Measure real frames/sec from successive progress polls (per job)."""

    def __init__(self, window_sec: float = 45.0) -> None:
        self.window_sec = window_sec
        self._samples: dict[str, list[tuple[float, int]]] = {}

    def update(self, key: str, frames_done: int, now: float | None = None) -> float | None:
        now = time.monotonic() if now is None else now
        samples = self._samples.setdefault(key, [])
        if samples and frames_done < samples[-1][1]:
            samples.clear()  # new attempt restarted the counter
        samples.append((now, int(frames_done)))
        while len(samples) > 2 and now - samples[0][0] > self.window_sec:
            samples.pop(0)
        if len(samples) < 2:
            return None
        dt = samples[-1][0] - samples[0][0]
        df = samples[-1][1] - samples[0][1]
        if dt < 2.0 or df <= 0:
            return None
        return df / dt

    def reset(self, key: str) -> None:
        self._samples.pop(key, None)


def eta_fps(agg: dict[str, Any]) -> float | None:
    """Fallback fps derived from the renderer's own ETA estimate."""
    eta = agg.get("eta_seconds")
    total = int(agg.get("frames_total") or 0)
    done = int(agg.get("frames_done") or 0)
    if not eta or eta <= 0 or total <= done:
        return None
    return (total - done) / float(eta)
