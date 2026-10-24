from __future__ import annotations

from typing import Iterable


def format_srt_time(seconds: float) -> str:
    total_ms = max(0, round(float(seconds) * 1000))
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt(beats: Iterable[dict]) -> str:
    blocks: list[str] = []
    for index, beat in enumerate(beats, start=1):
        text = str(beat.get("text") or beat.get("narration_text") or "").strip()
        if not text:
            continue
        start = format_srt_time(float(beat.get("start_sec") or 0.0))
        end = format_srt_time(float(beat.get("end_sec") or beat.get("start_sec") or 0.0))
        blocks.append(f"{index}\n{start} --> {end}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")
