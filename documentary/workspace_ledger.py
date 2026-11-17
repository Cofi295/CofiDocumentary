"""Deterministic workspace progress ledger & beat-level shard store.

Solves two structural token bottlenecks across long-form documentary runs:
1. Persistent Progress Memory (`.producer/state_ledger.json`):
   Captures exact completed/running/pending phases, artifact inventory, edit batch
   coordinates (`completed_beats / total_beats`, `next_pending_beat_id`), `dirty_beat_ids`,
   and recent surgical mutations in ~2-3 KB so session compactions/restarts resume
   deterministically without re-reading the repository or workspace.
2. Beat-Level Sharding & Surgical Patch (`beats_index.json` + `beats/<beat_id>.json`):
   Splits multi-megabyte `visual_manifest.json` into 1-file-per-beat shards (~2-8 KB)
   plus a lightweight index so editing 1 sentence/scene reads & patches ONLY that beat.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any


LEDGER_SCHEMA_VERSION = 1
BEATS_INDEX_SCHEMA_VERSION = 1
MAX_RECENT_MUTATIONS = 12

KEY_WORKSPACE_ARTIFACTS: tuple[str, ...] = (
    "input.json",
    "outline.json",
    "research.md",
    "script.md",
    "voice_manifest.json",
    "narration.srt",
    "visual_manifest.json",
    "beats_index.json",
    "footage_approved_live.json",
    "ai_visual_manifest.json",
    "vox_scene_manifest.json",
    "edit_progress.json",
    "edit_checkpoint.json",
    "timeline.json",
    "seo_package.json",
    "final_manifest.json",
)

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_BEAT_ID_TOKEN_RE = re.compile(
    r"\b([A-Za-z]{1,6}[-_]?\d{1,4}(?:[-_][A-Za-z0-9]{1,8})?|beat[-_\s]*\d{1,4})\b",
    flags=re.IGNORECASE,
)
_MMSS_TOKEN_RE = re.compile(r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b")
_SEC_TOKEN_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:s|sec|secs|giây)\b", flags=re.IGNORECASE)
_QUOTED_TEXT_RE = re.compile(r"[\"'“”‘’]([^\"'“”‘’]{5,120})[\"'“”‘’]")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_beat_filename(beat_id: str, fallback_idx: int) -> str:
    cleaned = _SAFE_FILENAME_RE.sub("_", str(beat_id or "").strip()).strip("._")
    if not cleaned:
        cleaned = f"beat_{fallback_idx:04d}"
    return f"{cleaned}.json"


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    tmp_path.write_bytes(raw)
    os.replace(tmp_path, path)


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _extract_beats_list(manifest: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    for key in ("beats", "visuals", "segments", "items"):
        val = manifest.get(key)
        if isinstance(val, list):
            return key, [item for item in val if isinstance(item, dict)]
    return "beats", []


def _beat_sha1(beat: dict[str, Any]) -> str:
    canonical = json.dumps(beat, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]


def _beat_text_preview(beat: dict[str, Any], limit: int = 96) -> str:
    for field in ("narration_text", "voice_text", "text", "subtitle_display_text", "visual_description"):
        val = str(beat.get(field) or "").strip()
        if val:
            compact = " ".join(val.split())
            return compact if len(compact) <= limit else compact[: limit - 1] + "…"
    return ""


def _beat_route(beat: dict[str, Any]) -> str:
    for field in ("visual_route", "route", "visual_type", "source_priority"):
        val = str(beat.get(field) or "").strip()
        if val:
            return val
    return "unspecified"


def _beat_timing(beat: dict[str, Any]) -> tuple[float | None, float | None, float | None]:
    start_raw = beat.get("start_sec", beat.get("start"))
    end_raw = beat.get("end_sec", beat.get("end"))
    dur_raw = beat.get("duration_sec", beat.get("target_duration_sec"))
    start_sec = round(float(start_raw), 3) if isinstance(start_raw, (int, float)) else None
    end_sec = round(float(end_raw), 3) if isinstance(end_raw, (int, float)) else None
    if isinstance(dur_raw, (int, float)):
        dur_sec = round(float(dur_raw), 3)
    elif start_sec is not None and end_sec is not None and end_sec >= start_sec:
        dur_sec = round(end_sec - start_sec, 3)
    else:
        dur_sec = None
    return start_sec, end_sec, dur_sec


# ----------------------------------------------------------------------
# 1. Beat-Level Sharding & Surgical Beat Patch (`beats_index.json` + `beats/`)
# ----------------------------------------------------------------------
def sync_beat_shards(
    workspace: str | Path,
    manifest_override: dict[str, Any] | None = None,
    *,
    force: bool = False,
    clear_dirty: bool = False,
    job: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shard `visual_manifest.json` (or fallback `voice_manifest.json`) into per-beat JSON files."""
    ws = Path(workspace).resolve()
    if not ws.is_dir():
        return {"total_beats": 0, "beats": [], "dirty_beat_ids": []}

    vis_path = ws / "visual_manifest.json"
    voice_path = ws / "voice_manifest.json"
    src_path = vis_path if vis_path.is_file() else (voice_path if voice_path.is_file() else None)
    index_path = ws / "beats_index.json"
    beats_dir = ws / "beats"

    existing_index = _read_json_dict(index_path)
    dirty_ids: list[str] = [] if clear_dirty else [
        str(x) for x in (existing_index.get("dirty_beat_ids") or []) if str(x).strip()
    ]

    if src_path is None:
        return existing_index if existing_index else {"total_beats": 0, "beats": [], "dirty_beat_ids": dirty_ids}

    try:
        st = src_path.stat()
    except OSError:
        return existing_index if existing_index else {"total_beats": 0, "beats": [], "dirty_beat_ids": dirty_ids}

    if (
        not force
        and not clear_dirty
        and existing_index.get("source_file") == src_path.name
        and existing_index.get("source_mtime_ns") == st.st_mtime_ns
        and existing_index.get("source_size_bytes") == st.st_size
        and beats_dir.is_dir()
    ):
        return existing_index

    manifest = manifest_override if isinstance(manifest_override, dict) else _read_json_dict(src_path)
    _, beats = _extract_beats_list(manifest)
    beats_dir.mkdir(parents=True, exist_ok=True)

    prev_sha_by_rel: dict[str, str] = {
        str(item.get("shard_relpath")): str(item.get("sha1") or "")
        for item in (existing_index.get("beats") or [])
        if isinstance(item, dict) and item.get("shard_relpath")
    }

    dirty_set = set(dirty_ids)
    route_counts: dict[str, int] = {}
    index_entries: list[dict[str, Any]] = []
    expected_filenames: set[str] = set()

    for idx, beat in enumerate(beats):
        bid = str(beat.get("beat_id") or beat.get("id") or f"B{idx + 1:03d}").strip()
        fname = _safe_beat_filename(bid, idx + 1)
        # Disambiguate rare filename collisions
        if fname in expected_filenames:
            fname = f"{idx + 1:04d}_{fname}"
        expected_filenames.add(fname)
        shard_rel = f"beats/{fname}"
        sha1 = _beat_sha1(beat)
        shard_path = ws / shard_rel
        if force or prev_sha_by_rel.get(shard_rel) != sha1 or not shard_path.is_file():
            _atomic_write_json(shard_path, beat)

        route = _beat_route(beat)
        route_counts[route] = route_counts.get(route, 0) + 1
        start_sec, end_sec, dur_sec = _beat_timing(beat)
        index_entries.append({
            "idx": idx,
            "beat_id": bid,
            "act_id": beat.get("act_id"),
            "chapter_id": beat.get("chapter_id"),
            "story_group": beat.get("story_group"),
            "start_sec": start_sec,
            "end_sec": end_sec,
            "duration_sec": dur_sec,
            "visual_route": route,
            "visual_type": beat.get("visual_type"),
            "text_preview": _beat_text_preview(beat),
            "sha1": sha1,
            "dirty": bid in dirty_set,
            "shard_relpath": shard_rel,
        })

    # Clean up stale shard files removed by a full re-plan
    for old_file in beats_dir.glob("*.json"):
        if old_file.name not in expected_filenames and not old_file.name.startswith("."):
            try:
                old_file.unlink()
            except OSError:
                pass

    valid_ids = {entry["beat_id"] for entry in index_entries}
    dirty_ids = [bid for bid in dirty_ids if bid in valid_ids]

    duration_raw = manifest.get("duration_sec") or manifest.get("target_duration_sec")
    duration_sec = round(float(duration_raw), 3) if isinstance(duration_raw, (int, float)) else (
        index_entries[-1]["end_sec"] if index_entries and index_entries[-1].get("end_sec") is not None else None
    )

    index_payload: dict[str, Any] = {
        "schema_version": BEATS_INDEX_SCHEMA_VERSION,
        "source_file": src_path.name,
        "source_mtime_ns": st.st_mtime_ns,
        "source_size_bytes": st.st_size,
        "synced_at": _utc_now(),
        "total_beats": len(index_entries),
        "duration_sec": duration_sec,
        "route_counts": route_counts,
        "dirty_beat_ids": dirty_ids,
        "beats": index_entries,
    }
    _atomic_write_json(index_path, index_payload)
    return index_payload


def list_workspace_beats(
    workspace: str | Path,
    *,
    query: str | None = None,
    timestamp_sec: float | None = None,
    dirty_only: bool = False,
    limit: int = 250,
) -> dict[str, Any]:
    """Query `beats_index.json` without loading the multi-MB `visual_manifest.json`."""
    index = sync_beat_shards(workspace)
    entries = list(index.get("beats") or [])
    if dirty_only:
        entries = [e for e in entries if e.get("dirty")]
    if timestamp_sec is not None:
        ts = float(timestamp_sec)
        entries = [
            e for e in entries
            if isinstance(e.get("start_sec"), (int, float))
            and isinstance(e.get("end_sec"), (int, float))
            and float(e["start_sec"]) - 0.25 <= ts <= float(e["end_sec"]) + 0.25
        ]
    q = str(query or "").strip().lower()
    if q:
        filtered = []
        for e in entries:
            hay = " ".join(
                str(e.get(k) or "")
                for k in ("beat_id", "story_group", "visual_route", "visual_type", "text_preview", "chapter_id")
            ).lower()
            if q in hay:
                filtered.append(e)
        entries = filtered

    capped = entries[: max(1, min(int(limit), 1000))]
    return {
        "source_file": index.get("source_file"),
        "total_beats": int(index.get("total_beats") or 0),
        "matched_count": len(entries),
        "dirty_beat_ids": list(index.get("dirty_beat_ids") or []),
        "route_counts": dict(index.get("route_counts") or {}),
        "beats": capped,
    }


def load_single_beat(workspace: str | Path, beat_id: str) -> dict[str, Any] | None:
    """Load a single beat shard JSON by `beat_id` (case-insensitive match)."""
    ws = Path(workspace).resolve()
    index = sync_beat_shards(ws)
    needle = str(beat_id or "").strip().lower()
    if not needle:
        return None
    for entry in index.get("beats") or []:
        if str(entry.get("beat_id") or "").strip().lower() == needle:
            shard_path = ws / str(entry.get("shard_relpath") or "")
            data = _read_json_dict(shard_path)
            return data if data else None
    return None


def _extract_ordinal_beat_positions(text: str, total_beats: int) -> list[int]:
    """Resolve Vietnamese/English positional & ordinal scene/beat references (0-based indices)
    such as 'cảnh đầu', 'cảnh đầu tiên', 'câu đầu', 'clip đầu', 'cảnh cuối', 'cảnh 2', 'cảnh thứ 3', 'S_F001'.
    """
    if not text or total_beats <= 0:
        return []
    positions: list[int] = []

    def _push(idx: int) -> None:
        if 0 <= idx < total_beats and idx not in positions:
            positions.append(idx)

    if re.search(
        r"(?i)\b(?:cảnh|canh|câu|cau|đoạn|doan|beat|clip|shot|scene)\s+(?:mở\s+đầu|đầu(?:\s+tiên)?|dau(?:\s+tien)?|số\s*1|so\s*1|thứ\s+nhất|thu\s+nhat)\b",
        text,
    ):
        _push(0)
    if re.search(
        r"(?i)\b(?:cảnh|canh|câu|cau|đoạn|doan|beat|clip|shot|scene)\s+(?:cuối(?:\s+cùng)?|cuoi(?:\s+cung)?|kết(?:\s+thúc)?)\b",
        text,
    ):
        _push(total_beats - 1)
    for m in re.finditer(
        r"(?i)\b(?:cảnh|canh|câu|cau|bit|beat|clip|shot|scene)\s*(?:thứ|thu|số|so|#)?\s*(\d{1,3})\b",
        text,
    ):
        val = int(m.group(1))
        if 1 <= val <= total_beats:
            _push(val - 1)
    for m in re.finditer(r"(?i)\bS_F0*(\d{1,3})\b", text):
        val = int(m.group(1))
        if 1 <= val <= total_beats:
            _push(val - 1)
    return positions


def _normalize_beat_token_to_index_id(token: str, by_lower_id: dict[str, str], entries: list[dict[str, Any]]) -> str | None:
    low = token.strip().lower()
    if low in by_lower_id:
        return by_lower_id[low]
    compact = re.sub(r"[-_\s]+", "", low)
    for k_low, orig_id in by_lower_id.items():
        if re.sub(r"[-_\s]+", "", k_low) == compact:
            return orig_id
    m_num = re.match(r"^(?:beat|b)[-_\s]*(\d{1,4})$", low)
    if m_num:
        num = int(m_num.group(1))
        for cand in (f"b{num:03d}", f"b{num:04d}", f"beat_{num:03d}", f"beat_{num:04d}", f"b{num}"):
            if cand in by_lower_id:
                return by_lower_id[cand]
        if 1 <= num <= len(entries):
            return str(entries[num - 1]["beat_id"])
    return None


def get_beat_context_slice(
    workspace: str | Path,
    *,
    beat_id: str | None = None,
    message: str | None = None,
    timestamp_sec: float | None = None,
    neighbors: int = 1,
    neighbor_radius: int | None = None,
    max_targets: int = 4,
) -> dict[str, Any]:
    """Extract ONLY the relevant beat shard(s) + compact neighbor summaries for surgical editing."""
    if neighbor_radius is not None:
        neighbors = int(neighbor_radius)
    ws = Path(workspace).resolve()
    index = sync_beat_shards(ws)
    entries: list[dict[str, Any]] = list(index.get("beats") or [])
    if not entries:
        return {"matched": False, "total_beats": 0, "target_beat_ids": [], "target_beats": [], "neighbor_summaries": []}

    by_lower_id = {str(e["beat_id"]).lower(): str(e["beat_id"]) for e in entries}
    pos_by_id = {str(e["beat_id"]): int(e["idx"]) for e in entries}
    matched_ids: list[str] = []

    def _add(bid: str | None) -> None:
        if bid and bid in pos_by_id and bid not in matched_ids and len(matched_ids) < max_targets:
            matched_ids.append(bid)

    if beat_id:
        _add(_normalize_beat_token_to_index_id(beat_id, by_lower_id, entries))

    if timestamp_sec is not None:
        for e in entries:
            s_sec, e_sec = e.get("start_sec"), e.get("end_sec")
            if isinstance(s_sec, (int, float)) and isinstance(e_sec, (int, float)):
                if float(s_sec) - 0.25 <= float(timestamp_sec) <= float(e_sec) + 0.25:
                    _add(str(e["beat_id"]))

    msg = str(message or "").strip()
    if msg and len(matched_ids) < max_targets:
        for raw_tok in _BEAT_ID_TOKEN_RE.findall(msg):
            _add(_normalize_beat_token_to_index_id(raw_tok, by_lower_id, entries))
        for mm, ss, hh_opt in _MMSS_TOKEN_RE.findall(msg):
            if hh_opt:
                ts_val = int(mm) * 3600 + int(ss) * 60 + int(hh_opt)
            else:
                ts_val = int(mm) * 60 + int(ss)
            for e in entries:
                s_sec, e_sec = e.get("start_sec"), e.get("end_sec")
                if isinstance(s_sec, (int, float)) and isinstance(e_sec, (int, float)) and s_sec <= ts_val <= e_sec:
                    _add(str(e["beat_id"]))
        for sec_str in _SEC_TOKEN_RE.findall(msg):
            ts_val = float(sec_str)
            for e in entries:
                s_sec, e_sec = e.get("start_sec"), e.get("end_sec")
                if isinstance(s_sec, (int, float)) and isinstance(e_sec, (int, float)) and s_sec <= ts_val <= e_sec:
                    _add(str(e["beat_id"]))
        for phrase in _QUOTED_TEXT_RE.findall(msg):
            p_low = phrase.strip().lower()
            for e in entries:
                if p_low and p_low in str(e.get("text_preview") or "").lower():
                    _add(str(e["beat_id"]))
        for pos_idx in _extract_ordinal_beat_positions(msg, len(entries)):
            _add(str(entries[pos_idx]["beat_id"]))

    target_beats: list[dict[str, Any]] = []
    neighbor_indices: set[int] = set()
    target_indices = {pos_by_id[bid] for bid in matched_ids}

    for bid in matched_ids:
        idx = pos_by_id[bid]
        entry = entries[idx]
        shard = _read_json_dict(ws / str(entry["shard_relpath"]))
        if shard:
            target_beats.append(shard)
        for delta in range(-max(0, neighbors), max(0, neighbors) + 1):
            n_idx = idx + delta
            if 0 <= n_idx < len(entries) and n_idx not in target_indices:
                neighbor_indices.add(n_idx)

    neighbor_summaries = [entries[i] for i in sorted(neighbor_indices)]
    return {
        "matched": len(target_beats) > 0,
        "total_beats": len(entries),
        "dirty_beat_ids": list(index.get("dirty_beat_ids") or []),
        "target_beat_ids": matched_ids,
        "target_beats": target_beats,
        "neighbor_summaries": neighbor_summaries,
    }


def patch_workspace_beats(
    workspace: str | Path,
    patches: dict[str, dict[str, Any]],
    *,
    reason: str = "",
    clear_dirty: bool = False,
    job: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Surgically patch specific beats in `visual_manifest.json` + `beats/<id>.json` and mark dirty."""
    ws = Path(workspace).resolve()
    vis_path = ws / "visual_manifest.json"
    if not vis_path.is_file():
        raise FileNotFoundError(f"visual_manifest.json not found in {ws}")

    manifest = _read_json_dict(vis_path)
    list_key, beats = _extract_beats_list(manifest)
    if not beats:
        raise ValueError("visual_manifest.json contains no beats to patch.")

    norm_patches: dict[str, dict[str, Any]] = {
        str(k).strip().lower(): dict(v)
        for k, v in (patches or {}).items()
        if str(k).strip() and isinstance(v, dict)
    }
    if not norm_patches:
        raise ValueError("No valid beat patches provided.")

    updated_ids: list[str] = []
    matched_keys: set[str] = set()

    for idx, beat in enumerate(beats):
        orig_id = str(beat.get("beat_id") or beat.get("id") or f"B{idx + 1:03d}").strip()
        key_low = orig_id.lower()
        if key_low not in norm_patches:
            continue
        matched_keys.add(key_low)
        delta = dict(norm_patches[key_low])
        # Preserve canonical beat_id identity
        delta.pop("beat_id", None)
        for k, v in delta.items():
            if isinstance(v, dict) and isinstance(beat.get(k), dict):
                merged_sub = dict(beat[k])
                merged_sub.update(v)
                beat[k] = merged_sub
            else:
                beat[k] = v
        beat["beat_id"] = orig_id
        beats[idx] = beat
        updated_ids.append(orig_id)

    missing_ids = [k for k in norm_patches.keys() if k not in matched_keys]
    if updated_ids:
        manifest[list_key] = beats
        _atomic_write_json(vis_path, manifest)

        index_path = ws / "beats_index.json"
        existing_index = _read_json_dict(index_path)
        prev_dirty = [] if clear_dirty else [
            str(x) for x in (existing_index.get("dirty_beat_ids") or []) if str(x).strip()
        ]
        merged_dirty = list(dict.fromkeys([*prev_dirty, *updated_ids])) if not clear_dirty else []
        if index_path.is_file():
            existing_index["dirty_beat_ids"] = merged_dirty
            _atomic_write_json(index_path, existing_index)

        refreshed = sync_beat_shards(ws, force=True, clear_dirty=clear_dirty)
        # Ensure merged_dirty persists after force sync
        if not clear_dirty and merged_dirty != refreshed.get("dirty_beat_ids"):
            refreshed["dirty_beat_ids"] = merged_dirty
            for entry in refreshed.get("beats") or []:
                entry["dirty"] = entry.get("beat_id") in set(merged_dirty)
            _atomic_write_json(index_path, refreshed)

        # Invalidate beat-scoped render cache entries if present
        cache_manifest_path = ws / ".render_cache" / "cache_manifest.json"
        if cache_manifest_path.is_file():
            cache_data = _read_json_dict(cache_manifest_path)
            segs = cache_data.get("segments")
            if isinstance(segs, dict):
                removed = False
                for bid in updated_ids:
                    if segs.pop(bid, None) is not None:
                        removed = True
                if removed:
                    _atomic_write_json(cache_manifest_path, cache_data)

        sync_workspace_ledger(
            ws,
            job=job,
            mutation={
                "kind": "beat_patch",
                "summary": reason or f"Surgically patched {len(updated_ids)} beat(s)",
                "beat_ids": updated_ids,
            },
        )

    index_after = _read_json_dict(ws / "beats_index.json")
    return {
        "updated_beat_ids": updated_ids,
        "missing_beat_ids": missing_ids,
        "dirty_beat_ids": list(index_after.get("dirty_beat_ids") or []),
        "total_beats": int(index_after.get("total_beats") or len(beats)),
        "synced_at": _utc_now(),
    }


def clear_dirty_beats(
    workspace: str | Path,
    beat_ids: list[str] | None = None,
    *,
    reason: str = "",
) -> list[str]:
    """Clear all or specified `dirty_beat_ids` after Remotion timeline / segment render catches up."""
    ws = Path(workspace).resolve()
    index_path = ws / "beats_index.json"
    if not index_path.is_file():
        return []
    index = _read_json_dict(index_path)
    cur_dirty = [str(x) for x in (index.get("dirty_beat_ids") or []) if str(x).strip()]
    if beat_ids is None:
        remaining: list[str] = []
    else:
        clear_set = {str(x).strip() for x in beat_ids}
        remaining = [x for x in cur_dirty if x not in clear_set]
    index["dirty_beat_ids"] = remaining
    rem_set = set(remaining)
    for entry in index.get("beats") or []:
        if isinstance(entry, dict):
            entry["dirty"] = entry.get("beat_id") in rem_set
    _atomic_write_json(index_path, index)
    mut = {"kind": "clear_dirty", "summary": reason} if reason else None
    sync_workspace_ledger(ws, mutation=mut)
    return remaining


# ----------------------------------------------------------------------
# 2. Persistent Progress Memory (`.producer/state_ledger.json`)
# ----------------------------------------------------------------------
def load_workspace_ledger(workspace: str | Path) -> dict[str, Any]:
    ws = Path(workspace).resolve()
    ledger_path = ws / ".producer" / "state_ledger.json"
    if ledger_path.is_file():
        data = _read_json_dict(ledger_path)
        if data:
            return data
    return sync_workspace_ledger(ws)


def sync_workspace_ledger(
    workspace: str | Path,
    job: dict[str, Any] | None = None,
    *,
    mutation: dict[str, Any] | None = None,
    mutated_beats: list[str] | None = None,
    last_action: str = "",
) -> dict[str, Any]:
    """Deterministically build and persist `.producer/state_ledger.json` (~2-3 KB)."""
    ws = Path(workspace).resolve()
    if not ws.is_dir():
        return {}

    ledger_path = ws / ".producer" / "state_ledger.json"
    prev_ledger = _read_json_dict(ledger_path)
    input_meta = _read_json_dict(ws / "input.json")
    store_job_meta = (
        _read_json_dict(ws.parent.parent / "data" / "jobs" / ws.name / "job.json")
        if ws.parent.name == "workspaces"
        else {}
    )
    src_job = job if isinstance(job, dict) and job else (store_job_meta or input_meta)

    # Ensure beat index stays fresh if visual_manifest.json exists
    beats_index = sync_beat_shards(ws) if (ws / "visual_manifest.json").is_file() else _read_json_dict(ws / "beats_index.json")
    if mutated_beats and isinstance(beats_index, dict) and beats_index.get("beats"):
        index_path = ws / "beats_index.json"
        cur_dirty = [str(x) for x in (beats_index.get("dirty_beat_ids") or []) if str(x).strip()]
        merged_dirty = list(dict.fromkeys(cur_dirty + [str(b).strip() for b in mutated_beats if str(b).strip()]))
        beats_index["dirty_beat_ids"] = merged_dirty
        dirty_set = set(merged_dirty)
        for entry in beats_index.get("beats") or []:
            if isinstance(entry, dict):
                entry["dirty"] = entry.get("beat_id") in dirty_set
        if index_path.parent.is_dir():
            _atomic_write_json(index_path, beats_index)

    edit_prog = _read_json_dict(ws / "edit_progress.json")
    edit_ckpt = _read_json_dict(ws / "edit_checkpoint.json")

    phases_summary: dict[str, dict[str, Any]] = {}
    raw_phases = src_job.get("phases")
    active_phase: str | None = None
    completed_phases: list[str] = []
    pending_phases: list[str] = []
    failed_phases: list[str] = []

    if isinstance(raw_phases, dict):
        for p_name, p_info in raw_phases.items():
            if isinstance(p_info, dict):
                st_val = str(p_info.get("status") or "pending")
                phases_summary[str(p_name)] = {
                    "status": st_val,
                    "updated_at": p_info.get("finished_at") or p_info.get("updated_at") or p_info.get("completed_at") or p_info.get("started_at"),
                }
                if st_val == "running":
                    active_phase = str(p_name)
                elif st_val in {"succeeded", "completed", "approved"}:
                    completed_phases.append(str(p_name))
                elif st_val == "failed":
                    failed_phases.append(str(p_name))
                elif st_val in {"idle", "pending", "interrupted"}:
                    pending_phases.append(str(p_name))

    artifacts_meta: dict[str, dict[str, Any]] = {}
    for rel_name in KEY_WORKSPACE_ARTIFACTS:
        f_path = ws / rel_name
        if f_path.is_file():
            try:
                st = f_path.stat()
                artifacts_meta[rel_name] = {
                    "exists": True,
                    "size_bytes": st.st_size,
                }
            except OSError:
                continue

    total_beats = int(beats_index.get("total_beats") or edit_prog.get("total_beats") or 0)
    completed_beat_ids = [str(x) for x in (edit_prog.get("completed_beat_ids") or []) if str(x).strip()]
    pending_beat_ids = [str(x) for x in (edit_prog.get("pending_beat_ids") or []) if str(x).strip()]
    completed_edit_beats = int(edit_prog.get("completed_beats") or len(completed_beat_ids))
    pending_edit_beats = len(pending_beat_ids) if pending_beat_ids else max(0, total_beats - completed_edit_beats)
    next_pending_beat_id = pending_beat_ids[0] if pending_beat_ids else None

    recent_mutations = [
        item for item in (prev_ledger.get("recent_mutations") or [])
        if isinstance(item, dict)
    ]
    if mutation is None and (last_action or mutated_beats):
        mutation = {
            "kind": "edit_chat" if mutated_beats else "lifecycle",
            "summary": last_action or f"Mutated {len(mutated_beats or [])} beat(s)",
            "beat_ids": list(mutated_beats or []),
        }
    if isinstance(mutation, dict) and mutation.get("summary"):
        entry = {
            "at": _utc_now(),
            "kind": str(mutation.get("kind") or "update"),
            "summary": str(mutation.get("summary"))[:240],
        }
        if mutation.get("beat_ids"):
            entry["beat_ids"] = [str(x) for x in list(mutation["beat_ids"])[:20]]
        recent_mutations.append(entry)
        recent_mutations = recent_mutations[-MAX_RECENT_MUTATIONS:]

    def _clean_ledger_error(val: Any) -> str | None:
        raw = str(val or "").strip()
        if not raw:
            return None
        # Strip raw Antigravity/Gemini stream-json event envelopes mistakenly stored as errors
        cleaned_lines: list[str] = []
        for ln in raw.splitlines():
            s = ln.strip()
            if not s:
                continue
            if s.startswith("{") and ('"event":"init"' in s.replace(" ", "") or '"event":"step_update"' in s.replace(" ", "") or '"conversation_id"' in s):
                continue
            cleaned_lines.append(s)
        out = " | ".join(cleaned_lines[-3:]).strip()
        return out[:360] if out else None

    phase_err: str | None = None
    if isinstance(raw_phases, dict):
        for p_check in ("qc", "edit", "seo", "ai_visual", "footage", "visuals", "voice", "plan"):
            p_obj = raw_phases.get(p_check)
            if isinstance(p_obj, dict) and str(p_obj.get("status") or "").lower() == "failed":
                cand_err = _clean_ledger_error(p_obj.get("error") or p_obj.get("last_error") or p_obj.get("last_message"))
                if cand_err:
                    phase_err = f"[{p_check}] {cand_err}"
                    break
    exp_prog = _read_json_dict(ws / "export_progress.json")
    if not phase_err and str(exp_prog.get("status") or "").lower() == "failed":
        exp_msg = _clean_ledger_error(exp_prog.get("message") or exp_prog.get("error"))
        if exp_msg:
            phase_err = f"[qc] {exp_msg}"

    edit_succeeded = "edit" in completed_phases
    resolved_edit_status = (
        "succeeded"
        if edit_succeeded
        else (edit_prog.get("status") or ("checkpointed" if edit_ckpt else "not_started"))
    )
    if edit_succeeded and total_beats > 0:
        completed_edit_beats = total_beats
        pending_edit_beats = 0
        next_pending_beat_id = None

    resolved_last_error = (
        phase_err
        or _clean_ledger_error(src_job.get("error") or src_job.get("last_error"))
        or (None if edit_succeeded else _clean_ledger_error(edit_prog.get("last_error")))
    )

    ledger: dict[str, Any] = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "updated_at": _utc_now(),
        "job_id": src_job.get("id") or ws.name,
        "title": src_job.get("title") or input_meta.get("title") or "",
        "language": src_job.get("language") or input_meta.get("language") or "",
        "market": src_job.get("market") or input_meta.get("market") or "",
        "visual_strategy": src_job.get("visual_strategy") or input_meta.get("visual_strategy") or "",
        "target_duration_minutes": src_job.get("target_duration_minutes") or input_meta.get("target_duration_minutes"),
        "status": src_job.get("status") or prev_ledger.get("status") or "idle",
        "active_phase": active_phase,
        "completed_phases": completed_phases,
        "pending_phases": pending_phases,
        "failed_phases": failed_phases,
        "last_action": last_action or prev_ledger.get("last_action") or "",
        "last_error": resolved_last_error,
        "phases": phases_summary,
        "beat_progress": {
            "total_beats": total_beats,
            "duration_sec": beats_index.get("duration_sec"),
            "route_counts": dict(beats_index.get("route_counts") or {}),
            "dirty_beat_ids": list(beats_index.get("dirty_beat_ids") or []),
            "edit_status": resolved_edit_status,
            "completed_edit_beats": completed_edit_beats,
            "pending_edit_beats": pending_edit_beats,
            "current_batch": edit_prog.get("current_batch"),
            "total_batches": edit_prog.get("total_batches"),
            "next_pending_beat_id": next_pending_beat_id,
            "remotion_composition_id": edit_ckpt.get("composition_id"),
        },
        "artifacts": artifacts_meta,
        "recent_mutations": recent_mutations,
    }
    _atomic_write_json(ledger_path, ledger)
    return ledger


def resolve_job_workspace_for_meta(cwd: str | Path, meta_dir: str | Path | None = None) -> Path | None:
    """Resolve the active job workspace from either a direct job directory or a `.producer/<label>` meta folder."""
    base = Path(cwd).resolve()
    if (base / "input.json").is_file() or (base / ".producer" / "state_ledger.json").is_file() or (base / "visual_manifest.json").is_file():
        return base
    if meta_dir is not None:
        mpath = Path(meta_dir).resolve()
        if mpath.parent.name == ".producer":
            parent_ws = mpath.parent.parent
            if (parent_ws / "input.json").is_file() or (parent_ws / ".producer" / "state_ledger.json").is_file() or (parent_ws / "visual_manifest.json").is_file():
                return parent_ws
        label = mpath.name
        if label.endswith("_goal"):
            label = label[:-5]
        for prefix in ("producer_chat_", "job_", "edit_chat_"):
            if label.startswith(prefix):
                cand_id = label[len(prefix):].strip()
                if cand_id and cand_id != "global":
                    ws_root = base / "workspaces"
                    if ws_root.is_dir():
                        exact = ws_root / cand_id
                        if exact.is_dir():
                            return exact
                        matches = sorted(ws_root.glob(f"*-{cand_id}"))
                        if matches:
                            return matches[-1]
    return None


def _collect_recently_modified_files(workspace: Path, *, max_age_sec: float = 7200.0, limit: int = 10) -> list[str]:
    """Return compact relative paths (with age) of workspace files modified within `max_age_sec`."""
    now_ts = datetime.now(timezone.utc).timestamp()
    candidates: list[tuple[float, str]] = []
    scan_Targets: list[Path] = []
    for name in KEY_WORKSPACE_ARTIFACTS:
        p = workspace / name
        if p.is_file():
            scan_Targets.append(p)
    for extra_name in ("voice_manifest.raw.json", "thumbnail_design.json"):
        p = workspace / extra_name
        if p.is_file():
            scan_Targets.append(p)
    for sub in ("beats", "audio/beats_raw", "audio/beats", "media/thumbnail"):
        sub_dir = workspace / sub
        if sub_dir.is_dir():
            try:
                for child in sub_dir.iterdir():
                    if child.is_file():
                        scan_Targets.append(child)
            except OSError:
                pass
    seen: set[str] = set()
    for path in scan_Targets:
        try:
            rel = path.relative_to(workspace).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            mtime = path.stat().st_mtime
            age = max(0.0, now_ts - mtime)
            if age <= max_age_sec:
                candidates.append((mtime, f"{rel} ({int(age)}s ago)" if age < 120 else f"{rel} ({int(age // 60)}m ago)"))
        except OSError:
            continue
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [label for _, label in candidates[:limit]]


def format_compact_ledger_brief(workspace: str | Path, *, max_chars: int = 2200) -> str:
    """Format a deterministic `<2.2 KB` progress brief for session rotation/resume prompts."""
    ws = Path(workspace).resolve()
    if not ws.is_dir():
        return ""
    ledger = load_workspace_ledger(ws)
    if not ledger and ((ws / "input.json").is_file() or (ws / "visual_manifest.json").is_file()):
        ledger = sync_workspace_ledger(ws)
    if not ledger:
        return ""

    bp = ledger.get("beat_progress") or {}
    lines = [
        f"- Job `{ledger.get('job_id')}` ({ledger.get('language')}/{ledger.get('market')}, strategy=`{ledger.get('visual_strategy')}`): status=`{ledger.get('status')}`"
        + (f", active_phase=`{ledger.get('active_phase')}`" if ledger.get("active_phase") else ""),
        f"- Completed phases: {', '.join(ledger.get('completed_phases') or []) or 'none'}"
        + (f" | Failed phases: {', '.join(ledger.get('failed_phases'))}" if ledger.get("failed_phases") else ""),
        f"- Beat shards (`beats_index.json`): total_beats={bp.get('total_beats', 0)}, routes={json.dumps(bp.get('route_counts') or {}, ensure_ascii=False)}"
        + (f", dirty_beat_ids={bp.get('dirty_beat_ids')}" if bp.get("dirty_beat_ids") else ", dirty_beat_ids=[]"),
        f"- Edit progress: status=`{bp.get('edit_status')}`, completed={bp.get('completed_edit_beats', 0)}/{bp.get('total_beats', 0)}"
        + (f", next_pending_beat=`{bp.get('next_pending_beat_id')}`" if bp.get("next_pending_beat_id") else "")
        + (f", composition=`{bp.get('remotion_composition_id')}`" if bp.get("remotion_composition_id") else ""),
    ]
    if ledger.get("last_error"):
        lines.append(f"- Last error: {str(ledger['last_error'])[:220]}")
    present_arts = sorted((ledger.get("artifacts") or {}).keys())
    if present_arts:
        lines.append(f"- Present artifacts: {', '.join(present_arts)}")
    recent_files = _collect_recently_modified_files(ws, max_age_sec=7200.0, limit=10)
    if recent_files:
        lines.append(f"- Recently modified files on disk (last 2h): {', '.join(recent_files)}")
    mutations = ledger.get("recent_mutations") or []
    if mutations:
        recent_str = "; ".join(
            f"[{m.get('kind')}] {m.get('summary')}" + (f" ({','.join(m['beat_ids'][:5])})" if m.get("beat_ids") else "")
            for m in mutations[-4:]
        )
        lines.append(f"- Recent surgical mutations: {recent_str}")

    out = "\n".join(lines)
    if len(out) > max_chars:
        out = out[: max_chars - 3].rstrip() + "..."
    return out


def _locate_remotion_job_targets(
    workspace: Path,
    matched_beat_ids: list[str],
    combined_text: str,
    remotion_dir: str | Path | None = None,
) -> list[str]:
    """Find exact CofiRemotion `.tsx` / `*Data.ts` / `vox-studio/*` files and `StartLine..EndLine` for a job & its beats."""
    rem_root = (
        Path(remotion_dir).resolve()
        if remotion_dir
        else (workspace.parent.parent.parent / "CofiRemotion")
    )
    src_dir = rem_root / "src"
    if not src_dir.is_dir():
        return []

    job_id = workspace.name
    date_prefix = job_id.split("-")[0] if "-" in job_id else job_id[:8]
    data_ts_files: list[Path] = []
    main_tsx_files: list[Path] = []

    # 1. Match *Data.ts and *.tsx by job_id content or date_prefix filename
    try:
        for cand in sorted(src_dir.glob(f"*{date_prefix}*")):
            if cand.is_file():
                if cand.name.endswith("Data.ts"):
                    data_ts_files.append(cand)
                elif cand.name.endswith(".tsx"):
                    main_tsx_files.append(cand)
        if not data_ts_files:
            for cand in sorted(src_dir.glob("*Data.ts"), key=lambda p: p.stat().st_mtime, reverse=True)[:8]:
                try:
                    head_txt = cand.read_text(encoding="utf-8", errors="replace")[:4000]
                    if job_id in head_txt:
                        data_ts_files.append(cand)
                        stem_base = cand.name[:-len("Data.ts")]
                        tsx_cand = src_dir / f"{stem_base}.tsx"
                        if tsx_cand.is_file():
                            main_tsx_files.append(tsx_cand)
                        break
                except OSError:
                    continue
    except OSError:
        return []

    if not data_ts_files and not main_tsx_files:
        return []

    # Discover linked vox-studio/<subdir> from main_tsx_files
    vox_subdirs: list[Path] = []
    for tsx_f in main_tsx_files[:2]:
        try:
            tsx_txt = tsx_f.read_text(encoding="utf-8", errors="replace")[:3500]
            for m in re.finditer(r"from\s+['\"]\./vox-studio/([a-zA-Z0-9_-]+)['\"]", tsx_txt):
                sub_p = src_dir / "vox-studio" / m.group(1)
                if sub_p.is_dir() and sub_p not in vox_subdirs:
                    vox_subdirs.append(sub_p)
        except OSError:
            continue

    lines_out: list[str] = []
    file_summary_parts: list[str] = []
    for f in main_tsx_files[:2] + data_ts_files[:2]:
        try:
            lc = len(f.read_bytes().splitlines())
            file_summary_parts.append(f"`src/{f.name}` ({lc} dòng)")
        except OSError:
            pass
    for vdir in vox_subdirs[:1]:
        try:
            for vf in sorted(vdir.glob("*")):
                if vf.is_file() and vf.suffix in {".tsx", ".ts", ".json"}:
                    lc = len(vf.read_bytes().splitlines())
                    file_summary_parts.append(f"`src/vox-studio/{vdir.name}/{vf.name}` ({lc} dòng)")
        except OSError:
            pass
    if file_summary_parts:
        lines_out.append("   - File Remotion của dự án: " + ", ".join(file_summary_parts[:7]))

    # Extract explicit VOX_XX / CT_XX IDs from combined_text
    vox_ct_ids: list[str] = []
    for m in re.finditer(r"\b((?:VOX|CT)_[A-Z0-9_]{1,12})\b", combined_text.upper()):
        vid = m.group(1)
        if vid not in vox_ct_ids:
            vox_ct_ids.append(vid)
    has_act_card_mention = bool(
        re.search(r"(?i)\b(?:act|thẻ\s*act|the\s*act|chương|chuong|hồi|hoi|cinema\s*text|제\d+장)\b", combined_text)
    )
    if has_act_card_mention and "CT_ACT1" not in vox_ct_ids:
        vox_ct_ids.extend(["CT_ACT1", "CT_ACT2"])

    if matched_beat_ids:
        lines_out.append(
            f"   - ⛔ LUẬT KHOANH VÙNG ĐÚNG CẢNH CHỈ ĐỊNH (BẮT BUỘC): Người dùng CHỈ yêu cầu sửa đích danh cảnh/beat `{', '.join(matched_beat_ids[:4])}`. **TUYỆT ĐỐI CẤM** tự ý trích xuất 12–40 clip khác, cấm quét lại toàn bộ 23 nguồn video (`all_sources`), và cấm re-encode hàng loạt 40+ clip không được yêu cầu! Chỉ trích xuất & xử lý đúng clip của cảnh được nhắc tới (`< 10 giây`), cập nhật đúng dòng `StartLine..EndLine` bên dưới!"
        )

    # Scan Data.ts for exact line ranges of matched_beat_ids (or VOX_XX / CT_XX / S_F001)
    base_beat_prefixes = [b.split("-")[0] for b in matched_beat_ids[:8]]
    sf_tokens: list[str] = []
    for b_pref in base_beat_prefixes:
        m_num = re.match(r"^B0*(\d+)$", b_pref.upper())
        if m_num:
            sf_tokens.append(f"S_F{int(m_num.group(1)):03d}")
    for dfile in data_ts_files[:1]:
        try:
            dlines = dfile.read_text(encoding="utf-8", errors="replace").splitlines()
            found_for_beat: set[str] = set()
            for idx, dline in enumerate(dlines, 1):
                for b_idx, (b_id, b_pref) in enumerate(zip(matched_beat_ids[:8], base_beat_prefixes)):
                    if b_id in found_for_beat:
                        continue
                    sf_tok = sf_tokens[b_idx] if b_idx < len(sf_tokens) else ""
                    hit_beat = (
                        f'"{b_id}"' in dline
                        or f"'{b_id}'" in dline
                        or f'"{b_pref}-' in dline
                        or f'"{b_pref}"' in dline
                    ) and ("beat_id" in dline or "beatId" in dline or '"id"' in dline)
                    hit_sf = bool(sf_tok and (f"{sf_tok}.mp4" in dline or f'"{sf_tok}"' in dline or f"'{sf_tok}'" in dline))
                    if hit_beat or hit_sf:
                        start_l = max(1, idx - 3)
                        end_l = min(len(dlines), idx + 32)
                        for k in range(idx, min(len(dlines), idx + 40)):
                            if dlines[k].strip().startswith("}"):
                                end_l = k + 1
                                break
                        block_str = "\n".join(dlines[start_l - 1 : end_l])
                        if hit_beat and "durationInFrames" not in block_str and "start_sec" not in block_str and "src" not in block_str:
                            continue
                        found_for_beat.add(b_id)
                        for vm in re.finditer(r"\b((?:VOX|CT)_\d{1,3})\b", block_str):
                            if vm.group(1) not in vox_ct_ids:
                                vox_ct_ids.append(vm.group(1))
                        clip_hint = f" (`{sf_tok}.mp4`)" if sf_tok and sf_tok in block_str else ""
                        lines_out.append(
                            f"   - Beat `{b_id}`{clip_hint} trong `src/{dfile.name}`: dòng {start_l}..{end_l}"
                        )
                        break
        except OSError:
            pass

    # Scan vox-studio/<subdir>/*.tsx and CinemaTextSpecs.ts for VOX_XX / VoxSceneXX / (Bxxx-V01) / CT_XX line ranges
    if (vox_ct_ids or matched_beat_ids) and vox_subdirs:
        vox_search_tokens: list[tuple[str, str]] = []
        for vid in vox_ct_ids[:8]:
            vox_search_tokens.append((vid, vid))
            if vid.startswith("VOX_"):
                num_part = vid.split("_", 1)[1]
                vox_search_tokens.append((vid, f"VoxScene{num_part}"))
        for b_id in matched_beat_ids[:6]:
            vox_search_tokens.append((b_id, f"({b_id})"))
        seen_vox_hits: set[tuple[str, str]] = set()
        for vdir in vox_subdirs[:1]:
            for vf in sorted(vdir.glob("*")):
                if not vf.is_file() or vf.suffix not in {".tsx", ".ts"}:
                    continue
                try:
                    vlines = vf.read_text(encoding="utf-8", errors="replace").splitlines()
                    for idx, vline in enumerate(vlines, 1):
                        for canonical_id, tok in vox_search_tokens:
                            if (vf.name, canonical_id) in seen_vox_hits:
                                continue
                            if tok in vline and (
                                "export const " in vline
                                or "const " in vline
                                or "function " in vline
                                or "* VOX_" in vline
                                or f"'{tok}'" in vline
                                or f'"{tok}"' in vline
                                or f"{tok}:" in vline
                            ):
                                seen_vox_hits.add((vf.name, canonical_id))
                                start_l = max(1, idx - 4 if "export const " in vline else idx - 1)
                                end_l = min(len(vlines), idx + 45)
                                for k in range(idx, min(len(vlines), idx + 65)):
                                    if vlines[k].startswith("};"):
                                        end_l = k + 1
                                        break
                                lines_out.append(
                                    f"   - Cảnh `{canonical_id}` trong `src/vox-studio/{vdir.name}/{vf.name}`: dòng {start_l}..{end_l}"
                                )
                                break
                except OSError:
                    continue

    return lines_out


def _locate_thumbnail_and_dna_targets(ws: Path) -> list[str]:
    """Pre-extract Channel Thumbnail DNA (`thumbnail_dna`), `seo_package.json` titles, and current `thumbnail_design.json` variants (`v1..v4`)
    so thumbnail/SEO turns NEVER read full `input.json`, `research.md`, `seo_package.json` (528 lines), `thumbnail_design.json` (1,919 lines),
    or 40+ individual raw footage/background/reference images.
    """
    inp = _read_json_dict(ws / "input.json")
    snap = inp.get("channel_profile_snapshot") if isinstance(inp.get("channel_profile_snapshot"), dict) else {}
    tdna = inp.get("thumbnail_dna") if isinstance(inp.get("thumbnail_dna"), dict) else (
        snap.get("thumbnail_dna") if isinstance(snap.get("thumbnail_dna"), dict) else {}
    )
    td = _read_json_dict(ws / "thumbnail_design.json")
    seo = _read_json_dict(ws / "seo_package.json")
    if not tdna and not td and not seo:
        return []

    lines: list[str] = [
        "   - ⛔ LUẬT TIẾT KIỆM TOKEN THUMBNAIL & TIÊU ĐỀ SEO (BẮT BUỘC): **TUYỆT ĐỐI CẤM** gọi `read_file` đọc cả file `thumbnail_design.json` (1.900+ dòng) hay `seo_package.json` (500+ dòng), và **CẤM** gọi `read_file` lẻ tẻ trên hàng chục ảnh `seo_reference_thumbnails/*`, `media/footage/clips/*_3frames.jpg`, hay `media/thumbnail/thumb-bg-*` cũ! Toàn bộ tiêu đề SEO hiện tại, 4 phương án text thumb và `thumbnail_dna` đã trích xuất sẵn ngay bên dưới. Khi cần sửa text tiêu đề / text thumb, dùng lệnh Python ngắn cập nhật trực tiếp field JSON."
    ]
    if seo:
        rec_title = str(seo.get("recommended_title") or seo.get("title") or "").strip()
        tvs = [v for v in (seo.get("title_variants") or []) if isinstance(v, dict)]
        tv_parts = [
            f"`{v.get('id') or idx}`: title=`{v.get('title') or ''}` (thumb=`{v.get('thumbnail_line_1') or ''} / {v.get('thumbnail_line_2') or ''}`)"
            for idx, v in enumerate(tvs[:4], 1)
        ]
        if rec_title or tv_parts:
            lines.append(
                f"   - Tiêu đề hiện tại trong `seo_package.json`: recommended=`{rec_title}` | variants: " + " ; ".join(tv_parts)
            )
    if tdna:
        vis_sig = str(tdna.get("visual_signature") or "").strip()
        bg_rule = str(tdna.get("background_rule") or "").strip()
        precheck = str(tdna.get("dna_precheck_rule") or "").strip()
        palette = tdna.get("color_palette") if isinstance(tdna.get("color_palette"), dict) else {}
        typo = tdna.get("typography_preset") if isinstance(tdna.get("typography_preset"), dict) else {}
        if vis_sig:
            lines.append(f"   - Chuẩn `visual_signature` DNA Kênh: {vis_sig[:340]}")
        if bg_rule:
            lines.append(f"   - Quy tắc Bố cục & Viền sáng (`background_rule`): {bg_rule[:280]}")
        if palette or typo:
            lines.append(
                f"   - Bảng màu & Chữ chuẩn DNA: palette={json.dumps(palette, ensure_ascii=False)} | font_size(badge={typo.get('badge_font_size')}, L1={typo.get('line_1_font_size')}, L2={typo.get('line_2_font_size')}, stroke={typo.get('stroke_width')})"
            )
        if precheck:
            lines.append(f"   - Công thức Text & Hook (`dna_precheck_rule`): {precheck[:340]}")

    variants = [v for v in (td.get("variants") or []) if isinstance(v, dict)]
    if variants:
        v_summaries: list[str] = []
        for v in variants[:4]:
            vid = v.get("id") or ""
            badge = v.get("badge_text") or ""
            l1 = v.get("line_1") or v.get("top_line") or ""
            l2 = v.get("line_2") or v.get("bottom_line") or ""
            bg = v.get("background_path") or ""
            pip = v.get("inset_image_path") or ""
            v_summaries.append(f"`{vid}` (badge=`{badge}` / L1=`{l1}` / L2=`{l2}`, bg=`{bg}`, pip=`{pip}` -> `media/thumbnail/thumbnail_{vid}.jpg`)")
        lines.append("   - 4 phương án hiện tại trong `thumbnail_design.json`: " + " | ".join(v_summaries))
    return lines


def build_surgical_work_locator(
    workspace: str | Path,
    message: str = "",
    history: list[dict[str, Any]] | None = None,
    *,
    remotion_dir: str | Path | None = None,
    max_chars: int = 3000,
) -> str:
    """Pre-locate exact `script.md` line numbers, paragraph numbers, beat shards (`beats/<id>.json` + WAV),
    and CofiRemotion `.tsx` / `*Data.ts` line numbers referenced in `message` or the recent conversation history
    so the agent NEVER has to read full `script.md`, `voice_manifest.json`, or `6,900`-line `*Data.ts` files.
    """
    ws = Path(workspace).resolve()
    if not ws.is_dir():
        return ""

    # Combine current user message with up to 3 recent substantive messages from history
    search_blobs: list[str] = []
    if str(message or "").strip():
        search_blobs.append(str(message).strip())
    for item in reversed(list(history or [])[-8:]):
        if not isinstance(item, dict):
            continue
        txt = str(item.get("content") or "").strip()
        low = txt.lower()
        if not txt or low in {"/compact", "/nen", "/new", "/reset"}:
            continue
        if txt.startswith("Đã dừng lượt làm việc theo yêu cầu") or txt.startswith("Đã nén ngữ cảnh") or txt.startswith("Đã khởi tạo phiên"):
            steps = item.get("steps") if isinstance(item.get("steps"), list) else []
            step_targets = [
                str(s.get("target") or s.get("tool_summary") or "")
                for s in steps[-10:]
                if isinstance(s, dict) and (s.get("target") or s.get("tool_summary"))
            ]
            if step_targets:
                search_blobs.append(" ".join(step_targets))
            continue
        search_blobs.append(txt[:2000])
        if len(search_blobs) >= 4:
            break

    combined_text = "\n".join(search_blobs)
    if not combined_text.strip():
        return ""

    # 1. Extract explicit paragraph numbers (e.g., "Đoạn 54", "đoạn 4", "Paragraph 54", "P54")
    para_nums: list[int] = []
    for m in re.finditer(r"(?i)\b(?:đoạn|doan|paragraph|para)\s*#?\s*(\d{1,3})\b", combined_text):
        val = int(m.group(1))
        if 1 <= val <= 400 and val not in para_nums:
            para_nums.append(val)

    # 2. Extract explicit beat IDs (e.g., B135, B135-V01, B010) and VOX/CT IDs
    explicit_beats: list[str] = []
    for m in re.finditer(r"\b(B\d{2,4}(?:-V\d{2})?)\b", combined_text.upper()):
        bid = m.group(1)
        if bid not in explicit_beats:
            explicit_beats.append(bid)
    has_remotion_or_edit_mention = bool(
        re.search(r"(?i)\b(?:VOX_\d+|CT_\d+|edit|remotion|preview|scene|cảnh|canh|clip|act|phụ đề|subtitle|vox|timeline)\b", combined_text)
    )
    has_thumbnail_or_dna_mention = bool(
        re.search(r"(?i)\b(?:thumb|thumbnail|ảnh thu nhỏ|tiêu\s*đề|tieu\s*de|title|seo|dna\s*kênh|dna\s*kenh|viền\s*sáng|vien\s*sang|text\s*thumb|seo_package)\b", combined_text)
    )

    # 3. Extract Hangul / CJK phrases (>= 5 chars) or quoted phrases
    cjk_phrases: list[str] = []
    for m in re.finditer(r"[가-힣\u4e00-\u9fff]{3,}(?:[\s,.\u00b70-9]+[가-힣\u4e00-\u9fff0-9]{2,})+", combined_text):
        phrase = re.sub(r"\s+", " ", m.group(0)).strip()
        if len(phrase) >= 6 and phrase not in cjk_phrases:
            cjk_phrases.append(phrase)
    for m in re.finditer(r"[가-힣]{4,}", combined_text):
        word = m.group(0).strip()
        if len(word) >= 4 and word not in cjk_phrases:
            cjk_phrases.append(word)

    if not para_nums and not explicit_beats and not cjk_phrases and not has_remotion_or_edit_mention and not has_thumbnail_or_dna_mention:
        return ""

    # Parse script.md into numbered non-empty paragraphs with exact 1-based line numbers
    script_path = ws / "script.md"
    paragraphs: list[dict[str, Any]] = []
    if script_path.is_file():
        try:
            raw_lines = script_path.read_text(encoding="utf-8", errors="replace").splitlines()
            cur_lines: list[str] = []
            cur_start = 1
            for line_no, raw_line in enumerate(raw_lines, 1):
                if raw_line.strip():
                    if not cur_lines:
                        cur_start = line_no
                    cur_lines.append(raw_line.strip())
                else:
                    if cur_lines:
                        paragraphs.append({
                            "para_no": len(paragraphs) + 1,
                            "start_line": cur_start,
                            "end_line": line_no - 1,
                            "text": " ".join(cur_lines),
                        })
                        cur_lines = []
            if cur_lines:
                paragraphs.append({
                    "para_no": len(paragraphs) + 1,
                    "start_line": cur_start,
                    "end_line": len(raw_lines),
                    "text": " ".join(cur_lines),
                })
        except OSError:
            pass

    # Load beats_index.json for fast beat cross-referencing
    beats_idx_data = _read_json_dict(ws / "beats_index.json")
    if not beats_idx_data and (ws / "visual_manifest.json").is_file():
        beats_idx_data = sync_beat_shards(ws)
    idx_beats: list[dict[str, Any]] = [b for b in (beats_idx_data.get("beats") or []) if isinstance(b, dict)]

    matched_paras: dict[int, dict[str, Any]] = {}
    matched_beats: dict[str, dict[str, Any]] = {}

    # Match explicit beat IDs and ordinal/positional scene references (e.g., "cảnh đầu", "cảnh cuối", "cảnh 2")
    for pos_idx in _extract_ordinal_beat_positions(str(message or "") or combined_text, len(idx_beats)):
        b_entry = idx_beats[pos_idx]
        b_id = str(b_entry.get("beat_id") or "")
        if b_id:
            matched_beats[b_id] = b_entry
            if b_id not in explicit_beats:
                explicit_beats.append(b_id)

    for bid in explicit_beats[:8]:
        base_prefix = bid.split("-")[0]
        for b in idx_beats:
            b_id = str(b.get("beat_id") or "")
            if b_id == bid or b_id.startswith(base_prefix + "-") or b_id == base_prefix:
                matched_beats[b_id] = b

    # Match explicit paragraph numbers in script.md AND check beat shards with paragraph_index
    for pno in para_nums[:4]:
        if 1 <= pno <= len(paragraphs):
            matched_paras[pno] = paragraphs[pno - 1]
        beats_dir = ws / "beats"
        if beats_dir.is_dir():
            for b in idx_beats:
                b_id = str(b.get("beat_id") or "")
                shard = _read_json_dict(beats_dir / f"{b_id}.json")
                p_idx = shard.get("paragraph_index")
                if p_idx in {pno, pno - 1} and b_id:
                    matched_beats[b_id] = b
                    nt = str(shard.get("narration_text") or "").strip()
                    if nt and len(nt) >= 8:
                        probe = nt[:18]
                        for para in paragraphs:
                            if probe in para["text"]:
                                matched_paras[para["para_no"]] = para

    # Match CJK/Korean phrases in script.md and beats_index.json
    for phrase in cjk_phrases[:8]:
        probe = phrase[:24]
        for para in paragraphs:
            if probe in para["text"] or phrase in para["text"]:
                matched_paras[para["para_no"]] = para
        for b in idx_beats:
            preview = str(b.get("text_preview") or b.get("narration_preview") or "")
            if probe in preview or phrase in preview:
                b_id = str(b.get("beat_id") or "")
                if b_id:
                    matched_beats[b_id] = b

    # Cross-link: for every matched paragraph, find its beat(s); for every matched beat, find its script.md paragraph
    for para in list(matched_paras.values())[:6]:
        ptext = para["text"]
        for b in idx_beats:
            b_id = str(b.get("beat_id") or "")
            preview = str(b.get("text_preview") or b.get("narration_preview") or "").strip()
            if preview and len(preview) >= 8 and preview[:16] in ptext:
                matched_beats[b_id] = b

    for b in list(matched_beats.values())[:8]:
        preview = str(b.get("text_preview") or b.get("narration_preview") or "").strip()
        if preview and len(preview) >= 8:
            probe = preview[:16]
            for para in paragraphs:
                if probe in para["text"]:
                    matched_paras[para["para_no"]] = para

    ordered_beat_ids = sorted(
        matched_beats.keys(),
        key=lambda bid: (0 if any(bid.startswith(eb.split("-")[0]) for eb in explicit_beats) else 1, bid),
    )

    remotion_lines: list[str] = []
    if ordered_beat_ids or has_remotion_or_edit_mention:
        remotion_lines = _locate_remotion_job_targets(
            ws,
            ordered_beat_ids,
            combined_text,
            remotion_dir=remotion_dir,
        )

    thumbnail_lines: list[str] = []
    if has_thumbnail_or_dna_mention:
        thumbnail_lines = _locate_thumbnail_and_dna_targets(ws)

    if not matched_paras and not matched_beats and not remotion_lines and not thumbnail_lines:
        return ""

    out_lines: list[str] = [
        "🎯 ĐỊNH VỊ PHẪU THUẬT TỰ ĐỘNG TRÊN ĐĨA (ĐÃ TÌM SẴN DÒNG `script.md`, MẢNH BEAT, DÒNG REMOTION & THUMBNAIL DNA — SỬA TRỰC TIẾP, CẤM ĐỌC LẠI CẢ FILE LỚN):"
    ]
    if matched_paras:
        out_lines.append("1. Vị trí chính xác trong `script.md` (dùng ngay `edit_file` hoặc `read_file` với đúng `StartLine..EndLine` dưới đây):")
        for pno in sorted(matched_paras.keys())[:5]:
            p = matched_paras[pno]
            out_lines.append(
                f"   - Đoạn #{p['para_no']} (`script.md` dòng {p['start_line']}..{p['end_line']}): \"{p['text'][:240]}\""
            )
    if ordered_beat_ids:
        out_lines.append("2. Mảnh Beat & Voice tương ứng (chỉ đọc/sửa đúng file `beats/<beat_id>.json` và `audio/beats_raw/<base_id>.wav`):")
        for b_id in ordered_beat_ids[:6]:
            b = matched_beats[b_id]
            base_id = b_id.split("-")[0]
            wav_rel = f"audio/beats_raw/{base_id}.wav" if (ws / "audio" / "beats_raw" / f"{base_id}.wav").is_file() else f"audio/beats/{base_id}.wav"
            route_lbl = b.get("visual_route") or b.get("route") or "footage"
            prev_lbl = str(b.get("text_preview") or b.get("narration_preview") or "")[:160]
            out_lines.append(
                f"   - `{b_id}` ({b.get('start_sec')}s..{b.get('end_sec')}s, route=`{route_lbl}`, shard=`beats/{b_id}.json`, wav=`{wav_rel}`): \"{prev_lbl}\""
            )
    if remotion_lines:
        out_lines.append("3. Vị trí chính xác trong `CofiRemotion` (chỉ đọc/sửa đúng `StartLine..EndLine` này, cấm đọc cả file `*Data.ts` 6.900 dòng):")
        out_lines.extend(remotion_lines[:12])
    if thumbnail_lines:
        out_lines.append("4. Chuẩn `thumbnail_dna` của Kênh & 4 Phương án `thumbnail_design.json` hiện tại (đã trích xuất sẵn — cấm đọc lại `input.json`, `research.md` hay đọc lẻ tẻ hàng chục ảnh):")
        out_lines.extend(thumbnail_lines)

    text_out = "\n".join(out_lines)
    if len(text_out) > max_chars:
        text_out = text_out[: max_chars - 3].rstrip() + "..."
    return text_out


# ----------------------------------------------------------------------
# 2B. Universal Codebase Memory & Surgical Code Locator (`fix code dự án`)
# ----------------------------------------------------------------------
SUBSYSTEM_KEYWORD_MAP: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "Bộ nhớ ngữ cảnh, Nén chat (/compact), Đổi chat (/new), Dừng (Stop) & Handoff",
        ("nén chat", "compact", "đổi chat", "/new", "dừng", "stop", "cancelled", "handoff", "mất hết", "đọc lại", "bộ nhớ", "tocken", "token", "state_ledger", "sổ cái", "xoay phiên"),
        (
            "documentary/goal_session.py::should_compact",
            "documentary/goal_session.py::_build_local_handoff_summary",
            "documentary/goal_session.py::save_checkpoint_handoff",
            "documentary/goal_session.py::compact_and_rotate",
            "documentary/goal_session.py::_execute_single_turn",
            "documentary/service.py::compact_producer_chat_session",
            "documentary/service.py::new_producer_chat_session",
            "documentary/service.py::producer_goal_chat",
            "documentary/workspace_ledger.py::sync_workspace_ledger",
            "documentary/workspace_ledger.py::build_surgical_work_locator",
        ),
    ),
    (
        "Đề tài Radar, Lọc trùng Topic Memory, Cấm chữ 某 & Hồ sơ Kênh DNA",
        ("radar", "topic_memory", "trùng đề tài", "lọc trùng", "某", "tên thật", "luồng 1", "luồng 2", "channel_profiles", "hồ sơ kênh", "dna kênh", "gợi ý chủ đề", "case_similarity"),
        (
            "documentary/topic_research.py::_has_real_case_anchor",
            "documentary/topic_research.py::replenish_profile_topic_candidates",
            "services/channel_profile_service.py::ChannelProfileService",
            "services/case_similarity.py::check_topic_similarity",
        ),
    ),
    (
        "Kịch bản (script.md), Dàn ý 5 Hồi (outline.json), Xanh tiền & Tab Kịch bản UI",
        ("kịch bản", "script.md", "dàn ý", "outline", "vàng tiền", "xanh tiền", "hook", "mở đầu", "câu kết", "tab kịch bản", "renderscriptworkspace"),
        (
            "documentary/prompts.py::build_phase_prompt",
            "documentary/critic_loops.py::analyze_script_spoken_quality",
            "static/app.js::renderScriptWorkspace",
            "documentary/service.py::update_job_script",
            "documentary/service.py::update_job_outline",
        ),
    ),
    (
        "Giọng đọc (Voice / TTS), Cắt nhịp thở & Đồng bộ voice_manifest",
        ("voice", "giọng đọc", "tts", "cofivoice", "cắt nhịp", "narration.wav", "voice_manifest", "asr", "thu lại", "lặp từ"),
        (
            "documentary/editorial_voice_cutter.py::cut_editorial_voice_beats",
            "documentary/service.py::_run_voice_phase",
            "documentary/critic_loops.py::verify_voice_manifest_and_audio",
        ),
    ),
    (
        "Tư liệu thật (@footage), Soi lưới 100px Crop Logo/Watermark & Kiểm định mắt",
        ("footage", "tư liệu", "crop", "logo", "watermark", "chữ chạy", "grid", "storyboard", "motion energy", "dhash", "setpts"),
        (
            "documentary/edit_footage_fetcher.py::main",
            "documentary/edit.py::run_footage_eye_stage",
            "documentary/critic_loops.py::verify_footage_hygiene",
            "documentary/prompts.py::build_footage_eye_agent_prompt",
        ),
    ),
    (
        "Đồ họa VOX (@vox), Bàn biên tập cắt dán 12fps, Vật chứng Flow & Bản đồ 3D GIS",
        ("vox", "bàn biên tập", "desk", "cutout", "rembg", "vật chứng", "bản đồ", "geojson", "map", "loupe", "kính lúp", "12fps", "validate-vox"),
        (
            "CofiRemotion/src/vox-studio/vox-editorial-desk/index.tsx::Desk",
            "CofiRemotion/src/components/GeoJson3DMapStage.tsx::GeoJson3DMapStage",
            "CofiRemotion/scripts/validate-vox-newsroom-ast.mjs",
        ),
    ),
    (
        "Dựng phim (@edit), Remotion Timeline, Phụ đề, Cinema Text, BGM & SFX",
        ("edit", "dựng phim", "remotion", "timeline", "phụ đề", "subtitle", "cinema text", "sfx", "bgm", "lufs", "composition", "preview"),
        (
            "documentary/edit.py::run_edit_phase",
            "documentary/edit.py::run_edit_chat",
            "documentary/prompts.py::build_edit_batch_prompt",
            "documentary/prompts.py::build_edit_chat_prompt",
            "CofiRemotion/src/components/SubtitleOverlay.tsx::SubtitleOverlay",
            "CofiRemotion/src/components/FramelessCinemaTextBeat.tsx::FramelessCinemaTextBeat",
        ),
    ),
    (
        "SEO & Thiết kế Thumbnail Phân lớp (Thumbnail Studio)",
        ("seo", "thumbnail", "ảnh thu nhỏ", "chữ xanh", "polaroid", "fabric", "auto-design", "ctr"),
        (
            "documentary/thumbnail_studio.py::auto_design_thumbnail_studio",
            "documentary/thumbnail_studio.py::render_thumbnail_variant_pil",
            "static/thumbnail_studio.js",
        ),
    ),
    (
        "Xuất MP4 Cuối (@qc), Render NVENC & Kiểm định Chất lượng",
        ("qc", "xuất video", "export", "render", "mp4", "nvenc", "kiểm định", "release/video.mp4"),
        (
            "documentary/render_cache.py::BackgroundRenderCache",
            "documentary/critic_loops.py::verify_final_mp4_qc",
            "CofiRemotion/scripts/turbo-nvenc-export.mjs",
        ),
    ),
    (
        "Điều phối 15 Agent Studio, Ủy nhiệm (/api/agency/delegate) & Hot-Reload",
        ("agent", "ủy nhiệm", "delegate", "nexus", "hot_reload", "nạp nóng", "phòng ban", "orchestrator"),
        (
            "documentary/agent_manager.py::AgentManager",
            "documentary/agent_manager.py::worker_prompt",
            "documentary/nexus_coordinator.py::NexusCoordinator",
            "documentary/hot_reload.py::ensure_runtime_modules_synced",
        ),
    ),
)


def _extract_file_symbols(file_path: Path, rel_posix: str) -> list[dict[str, Any]]:
    """Fast line-accurate regex/indentation symbol extractor for Python, JS, and TSX files."""
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    total = len(lines)
    symbols: list[dict[str, Any]] = []
    suffix = file_path.suffix.lower()

    if suffix == ".py":
        py_pat = re.compile(r"^(\s*)(?:async\s+)?(def|class)\s+([A-Za-z_][A-Za-z0-9_]*)\s*[\(:]")
        route_pat = re.compile(r'^\s*@(?:api|app)\.(get|post|put|patch|delete)\(\s*[\'"]([^\'"]+)[\'"]')
        pending_route = ""
        raw_hits: list[tuple[int, int, str, str]] = []
        for idx, line in enumerate(lines, 1):
            rm = route_pat.match(line)
            if rm:
                pending_route = f"{rm.group(1).upper()} {rm.group(2)}"
                continue
            m = py_pat.match(line)
            if m:
                indent = len(m.group(1).expandtabs(4))
                if indent <= 8:
                    kind = m.group(2)
                    name = m.group(3)
                    label = f"{name} ({pending_route})" if pending_route else name
                    pending_route = ""
                    raw_hits.append((idx, indent, kind, label))
        for i, (start_l, indent, kind, label) in enumerate(raw_hits):
            end_l = total
            for next_start, next_indent, _, _ in raw_hits[i + 1 :]:
                if next_indent <= indent:
                    end_l = next_start - 1
                    break
            symbols.append({
                "file": rel_posix,
                "symbol": label.split(" ")[0],
                "display": label,
                "kind": kind,
                "start_line": start_l,
                "end_line": max(start_l, end_l),
            })
    elif suffix in {".js", ".ts", ".tsx", ".mjs"}:
        js_pat = re.compile(
            r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s+([A-Za-z_][A-Za-z0-9_]*)|const\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*[^=]+)?=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_][A-Za-z0-9_]*)\s*=>)"
        )
        raw_js: list[tuple[int, str]] = []
        for idx, line in enumerate(lines, 1):
            m = js_pat.match(line)
            if m:
                name = m.group(1) or m.group(2) or ""
                if name:
                    raw_js.append((idx, name))
        for i, (start_l, name) in enumerate(raw_js):
            end_l = raw_js[i + 1][0] - 1 if i + 1 < len(raw_js) else total
            symbols.append({
                "file": rel_posix,
                "symbol": name,
                "display": name,
                "kind": "fn",
                "start_line": start_l,
                "end_line": min(end_l, start_l + 140),
            })
    return symbols


APP_ARCHITECTURE_MEMORY_TREE = (
    "Cây thư mục Bộ nhớ Mã nguồn Hệ thống (chỉ mở đúng 1–2 file phụ trách tính năng cần sửa):\n"
    "- `app.py` / `server.py` / `desktop_app.py`: FastAPI routes (`/api/*`) & cửa sổ PyWebView.\n"
    "- `documentary/service.py`: Vòng đời dự án, API handlers, context chat (`producer_chat_context`), finalize export.\n"
    "- `documentary/goal_session.py` + `COFI_BRAIN/chat_run_manager.py`: Phiên Antigravity liên tục, `/compact`, `/new`, `handoff_summary.txt`, SSE chat.\n"
    "- `documentary/workspace_ledger.py`: Sổ cái `state_ledger.json`, beat shards `beats/<id>.json`, chẩn đoán lỗi & định vị code.\n"
    "- `documentary/prompts.py`: Prompt 8 khâu sản xuất & điều phối chat (`build_producer_goal_prompt`).\n"
    "- `documentary/radar.py` / `topic_research.py` / `services/channel_profile_service.py`: Radar, Topic Memory, DNA kênh.\n"
    "- `documentary/script.py` / `voice.py` / `editorial_voice_cutter.py` / `visuals.py`: Kịch bản, TTS CofiVoice, cắt nhịp thở, chia beat.\n"
    "- `documentary/footage.py` / `edit_footage_fetcher.py` / `ai_visual.py`: Săn tư liệu, lưới 100px crop logo, Google Flow.\n"
    "- `documentary/edit.py` / `remotion.py` / `render_cache.py` / `vox_engine/*`: Dựng Remotion, Preview port `8890`, render cache.\n"
    "- `documentary/thumbnail_studio.py` / `seo.py` / `critic_loops.py` / `quality.py`: Thumbnail Studio, SEO, cảm biến QC.\n"
    "- `static/app.js` / `static/thumbnail_studio.js` / `static/styles.css`: Giao diện các Tab & Canvas Thumbnail.\n"
    "- `CofiRemotion/src/vox-studio/vox-editorial-desk/index.tsx`, `src/components/*`, `scripts/turbo-nvenc-export.mjs`, `scripts/validate-vox-newsroom-ast.mjs`."
)

_ANTI_CODE_READ_COMPLAINT_RE = re.compile(
    r"(?i)(?:đừng|cấm|không được|sao\s+(?:lại|cứ)|lại\s+đọc|cứ\s+đọc|đéo\s+gì\s+cứ\s+đọc)\s+[^.!?\n]{0,30}\b(?:code|mã nguồn)\b"
)

_EXPLICIT_APP_CODE_FIX_RE = re.compile(
    r"(?i)(?:"
    r"\b(?:fix|sửa|vá|chỉnh|cập nhật|thêm|xóa|đổi|tối ưu)\s+(?:lỗi\s+)?(?:code|mã nguồn|source|app|ứng dụng|phần mềm|hệ thống|ui|ux|giao diện|nút|tab|form|modal|api|endpoint|backend|frontend|router|prompt|skill)\b"
    r"|\bcây thư mục\b|\brepo_code_index\b|\bhot[_ -]?reload\b"
    r"|\b(?:app|server|desktop_app|service|goal_session|workspace_ledger|prompts|render_cache|thumbnail_studio|critic_loops|agent_manager|nexus_coordinator|editorial_voice_cutter|edit_footage_fetcher|chat_run_manager)\.py\b"
    r"|\b(?:app|thumbnail_studio)\.js\b|\bstyles\.css\b|\bturbo-nvenc-export\.mjs\b|\bvalidate-vox-newsroom-ast\.mjs\b"
    r")"
)

_SHORT_FOLLOWUP_TRIGGER_RE = re.compile(
    r"(?i)^\s*(?:ok|oke|okay|ừ|ừa|đồng ý|chốt|làm đi|fix đi|sửa đi|chạy đi|tiếp tục|làm luôn|sửa luôn|1|2)\s*[.!?\s]*$"
)


def classify_producer_chat_intent(
    message: str,
    history: list[dict[str, Any]] | None = None,
    *,
    selected_job_id: str | None = None,
    explicit_agent_id: str | None = None,
) -> str:
    """Deterministically route between:
    - `'app_code_fix'`: modifying/debugging CofiDocumentary or CofiRemotion engine/UI code.
    - `'production_pipeline'`: executing or troubleshooting a video job's stages (`plan`..`qc`, preview, export, sync, script, voice, footage, vox, thumbnail).
    """
    if explicit_agent_id in {"dev", "debug"}:
        return "app_code_fix"
    if explicit_agent_id and explicit_agent_id not in {"dev", "debug"}:
        return "production_pipeline"

    msg = str(message or "").strip()
    if selected_job_id and _ANTI_CODE_READ_COMPLAINT_RE.search(msg) and not re.search(r"(?i)\b(?:fix|sửa|vá)\s+(?:code|mã nguồn)\b", msg):
        return "production_pipeline"
    if _EXPLICIT_APP_CODE_FIX_RE.search(msg):
        return "app_code_fix"

    # If the user sends a short confirmation ("fix đi", "làm đi", "1"), inherit intent from the last substantive user message ONLY
    if _SHORT_FOLLOWUP_TRIGGER_RE.match(msg) and history:
        for item in reversed(list(history)[-8:]):
            if not isinstance(item, dict) or str(item.get("role") or "") != "user":
                continue
            prev_u = str(item.get("content") or "").strip()
            if not prev_u or _SHORT_FOLLOWUP_TRIGGER_RE.match(prev_u) or prev_u.lower() in {"/compact", "/nen", "/new", "/reset"}:
                continue
            if _EXPLICIT_APP_CODE_FIX_RE.search(prev_u):
                return "app_code_fix"
            break

    if selected_job_id:
        return "production_pipeline"

    # Global chat with no selected job: if discussing radar/topic/new project, stay in production_pipeline; if discussing bugs/features, use app_code_fix
    low = msg.lower()
    if any(k in low for k in ("nén chat", "compact", "handoff", "bộ nhớ", "nút", "giao diện", "lỗi app", "sửa lỗi hệ thống")):
        return "app_code_fix"
    return "production_pipeline"


def _tail_meaningful_error_lines(log_path: Path, *, max_lines: int = 8, max_chars: int = 900) -> list[str]:
    """Extract concise root-cause error lines from the tail of a log file without loading multi-MB logs."""
    if not log_path.is_file():
        return []
    try:
        with log_path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 24_576), os.SEEK_SET)
            tail_text = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return []

    raw_lines = [ln.strip() for ln in tail_text.splitlines() if ln.strip()]
    if not raw_lines:
        return []

    err_kw = (
        "error", "exception", "traceback", "failed", "cannot find", "not found",
        "syntaxerror", "typeerror", "referenceerror", "bundling", "esbuild",
        "enoent", "cuda", "nvenc", "invalid", "lỗi", "thiếu",
    )
    hits: list[str] = []
    for idx, ln in enumerate(raw_lines):
        if ln.startswith("{") and ('"event":"init"' in ln.replace(" ", "") or '"event":"step_update"' in ln.replace(" ", "")):
            continue
        low_ln = ln.lower()
        if any(k in low_ln for k in err_kw):
            window = raw_lines[max(0, idx - 1) : min(len(raw_lines), idx + 3)]
            for w in window:
                if w not in hits and not (w.startswith("{") and '"conversation_id"' in w):
                    hits.append(w[:240])
    chosen = hits[-max_lines:] if hits else raw_lines[-min(4, max_lines) :]
    out: list[str] = []
    used = 0
    for c in chosen:
        if used + len(c) > max_chars:
            break
        out.append(c)
        used += len(c) + 1
    return out


def collect_job_live_diagnostics(
    workspace: str | Path,
    job: dict[str, Any] | None = None,
    *,
    remotion_dir: str | Path | None = None,
    remotion_mgr_status: dict[str, Any] | None = None,
    render_cache_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect instant (<15ms, zero subprocesses) stage-level diagnostics for an active video job so the chat agent
    IMMEDIATELY knows what failed, why it failed, and which exact workspace/Remotion file of THIS job owns it.
    """
    ws = Path(workspace).resolve()
    if not ws.is_dir():
        return {}
    store_job_meta = (
        _read_json_dict(ws.parent.parent / "data" / "jobs" / ws.name / "job.json")
        if ws.parent.name == "workspaces"
        else {}
    )
    src_job = job if isinstance(job, dict) and job else (store_job_meta or _read_json_dict(ws / "input.json"))
    job_id = str(src_job.get("id") or ws.name).strip()
    rem_root = Path(remotion_dir).resolve() if remotion_dir else (ws.parent.parent.parent / "CofiRemotion")

    phases_raw = src_job.get("phases") if isinstance(src_job.get("phases"), dict) else {}
    failed_phases: dict[str, str] = {}
    for p_name, p_info in phases_raw.items():
        if isinstance(p_info, dict) and str(p_info.get("status") or "").lower() == "failed":
            msg = str(p_info.get("error") or p_info.get("last_error") or p_info.get("last_message") or "failed").strip()
            if msg.startswith("{") and '"conversation_id"' in msg:
                msg = "Worker exited unexpectedly (check stage log)"
            failed_phases[str(p_name)] = msg[:300]

    # Check export_progress.json & .render_cache/logs/part-*.log & logs/qc.log
    # Always inspect the newest part-*.log even when job.status == 'running' if its tail contains an actual crash/error!
    exp_prog = _read_json_dict(ws / "export_progress.json")
    root_cause_logs: dict[str, list[str]] = {}
    rc_logs_dir = ws / ".render_cache" / "logs"
    is_qc_explicitly_failed = (
        "qc" in failed_phases
        or str(exp_prog.get("status") or "").lower() == "failed"
        or str((render_cache_status or {}).get("status") or "").lower() == "failed"
    )
    if rc_logs_dir.is_dir():
        part_logs = sorted(rc_logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        for plog in part_logs[:2]:
            excerpts = _tail_meaningful_error_lines(plog, max_lines=8)
            if not excerpts:
                continue
            joined_low = "\n".join(excerpts).lower()
            has_hard_err = any(
                tok in joined_low
                for tok in ("an error occurred", "typeerror", "referenceerror", "syntaxerror", "modulenotfound", "cannot resolve", "cannot read properties", "bundling failed", "error:")
            )
            if is_qc_explicitly_failed or has_hard_err:
                root_cause_logs[f".render_cache/logs/{plog.name}"] = excerpts
                break

    logs_dir = ws / "logs"
    if logs_dir.is_dir():
        for failed_p in list(failed_phases.keys())[:2]:
            cand_log = logs_dir / f"{failed_p}.log"
            if cand_log.is_file():
                excerpts = _tail_meaningful_error_lines(cand_log, max_lines=6)
                if excerpts:
                    root_cause_logs[f"logs/{cand_log.name}"] = excerpts

    # Identify ONLY this job's Remotion composition files (never touch another case's directory!)
    job_remotion_files: list[str] = []
    src_dir = rem_root / "src"
    date_prefix = job_id.split("-")[0] if "-" in job_id else job_id[:8]
    if src_dir.is_dir() and len(date_prefix) >= 8:
        try:
            matched_tsx: list[Path] = []
            for cand in sorted(src_dir.glob(f"*{date_prefix}*")):
                if cand.is_file() and cand.suffix in {".tsx", ".ts"}:
                    job_remotion_files.append(f"CofiRemotion/src/{cand.name}")
                    if cand.suffix == ".tsx":
                        matched_tsx.append(cand)
            for tsx_f in matched_tsx[:2]:
                head_txt = tsx_f.read_text(encoding="utf-8", errors="replace")[:3500]
                for m in re.finditer(r"from\s+['\"]\./vox-studio/([a-zA-Z0-9_-]+)['\"]", head_txt):
                    vsub = f"CofiRemotion/src/vox-studio/{m.group(1)}/"
                    if (src_dir / "vox-studio" / m.group(1)).is_dir() and vsub not in job_remotion_files:
                        job_remotion_files.append(vsub)
        except OSError:
            pass

    beats_idx = _read_json_dict(ws / "beats_index.json")
    dirty_beats = [str(x) for x in (beats_idx.get("dirty_beat_ids") or []) if str(x).strip()]
    edit_prog = _read_json_dict(ws / "edit_progress.json")
    unsynced_beats = [str(x) for x in (edit_prog.get("unsynced_beat_ids") or edit_prog.get("dirty_beat_ids") or []) if str(x).strip()]

    diag: dict[str, Any] = {
        "workspace_dir": str(ws),
        "failed_phases": failed_phases,
        "job_remotion_files": job_remotion_files,
        "dirty_or_unsynced_beats": list(dict.fromkeys(dirty_beats + unsynced_beats))[:25],
    }
    if isinstance(remotion_mgr_status, dict) and remotion_mgr_status:
        diag["remotion_preview"] = {
            "studio_running": bool(remotion_mgr_status.get("studio_running")),
            "port": remotion_mgr_status.get("port"),
            "studio_url": remotion_mgr_status.get("studio_url"),
            "last_error": remotion_mgr_status.get("last_error") or remotion_mgr_status.get("error"),
        }
    if exp_prog:
        diag["export_status"] = {
            "status": exp_prog.get("status"),
            "percent": exp_prog.get("percent"),
            "message": str(exp_prog.get("message") or "")[:240],
            "ready_chunks": exp_prog.get("ready_chunks"),
            "total_chunks": exp_prog.get("total_chunks"),
        }
    if root_cause_logs:
        diag["root_cause_log_excerpts"] = root_cause_logs
    return diag


def build_production_pipeline_memory_block(
    workspace: str | Path,
    job: dict[str, Any] | None = None,
    live_diagnostics: dict[str, Any] | None = None,
) -> str:
    """Build the instant Stage & File Routing Memory block injected into `production_pipeline` chat turns
    so the agent NEVER scans app code (`documentary/*.py`) to figure out where a production step lives or why it failed.
    """
    ws = Path(workspace).resolve()
    diag = live_diagnostics if isinstance(live_diagnostics, dict) and live_diagnostics else collect_job_live_diagnostics(ws, job)
    job_id = str((job or {}).get("id") or ws.name).strip()
    lines: list[str] = [
        f"🎬 BỘ NHỚ LUỒNG SẢN XUẤT & CHẨN ĐOÁN TỨC THÌ CỦA DỰ ÁN `{job_id}` (CHẾ ĐỘ SẢN XUẤT VIDEO — CẤM ĐỌC CODE APP):",
        f"- Thư mục dự án đang làm: `{ws}`",
        "- ⛔ LUẬT CẤM QUÉT MÃ NGUỒN APP & THƯ VIỆN LÕI REMOTION: Đây là tác vụ trên dự án video, **TUYỆT ĐỐI CẤM** đọc/quét `documentary/*.py`, `services/*.py`, `static/*.js`, `CofiRemotion/scripts/*`, thư mục của vụ án khác, hoặc đọc dò hàng nghìn dòng thư viện lõi `CofiRemotion/src/vox-studio/vox-editorial-desk/index.tsx` / `VoxGeoJson3DCartography.tsx` / `src/components/*`! Nếu lỗi render/TSX ở file của dự án này: chỉ mở lát cắt 25 dòng đúng tọa độ dòng báo lỗi trong log và chạy 1 lệnh `npx tsc --noEmit` tại `CofiRemotion` để bắt hết lỗi prop ngay trong 3 giây!",
        "  * `plan` (Kịch bản) -> `outline.json`, `research.md`, `script.md` | API: `PUT /api/jobs/{id}/script`, `POST .../rerun/plan`",
        "  * `voice` (Giọng đọc) -> `voice_manifest.json`, `narration.srt`, `audio/beats_raw/<Bxxx>.wav`, `audio/beats/<Bxxx>.wav` | API: `POST .../rerun/voice`",
        "  * `visuals` (Phân cảnh) -> `beats_index.json` + mảnh lẻ `beats/<beat_id>.json` (cấm đọc cả `visual_manifest.json` khi sửa lẻ) | API: `GET/PATCH /api/jobs/{id}/beats/{beat_id}`",
        "  * `footage` / `ai_visual` -> `footage_approved_live.json`, `footage_hygiene_report.json`, `ai_visual_manifest.json`, `media/footage/`",
        "  * `edit` / `vox` / Preview -> `edit_progress.json`, `timeline.json` | Bật Preview: `POST /api/jobs/{id}/remotion/start`",
        "  * `seo` / Thumbnail -> `seo_package.json`, `thumbnail_design.json`, `media/thumbnail/thumbnail_v1..v4.jpg` | API: `/thumbnail-studio/auto-design`",
        "  * `qc` / Xuất MP4 -> `export_progress.json`, `.render_cache/logs/part-0001.log`, `logs/qc.log`, `release/video.mp4` | API: `POST .../rerun/qc`",
    ]
    if diag.get("job_remotion_files"):
        lines.append("- File Remotion RIÊNG của đúng dự án này (cấm mở file dự án khác): " + ", ".join(f"`{x}`" for x in diag["job_remotion_files"]))
    rem_prev = diag.get("remotion_preview")
    if isinstance(rem_prev, dict):
        lines.append(
            f"- Trạng thái Remotion Preview hiện tại: studio_running=`{rem_prev.get('studio_running')}`, port=`{rem_prev.get('port')}`"
            + (f", error=`{rem_prev.get('last_error')}`" if rem_prev.get("last_error") else "")
        )
    if diag.get("dirty_or_unsynced_beats"):
        lines.append("- Các beat đang đánh dấu lệch / mới sửa (`dirty_or_unsynced_beats`): " + ", ".join(f"`{b}`" for b in diag["dirty_or_unsynced_beats"]))
    if diag.get("failed_phases"):
        lines.append("- Khâu đang báo lỗi (`failed_phases`): " + json.dumps(diag["failed_phases"], ensure_ascii=False))
    rc_logs = diag.get("root_cause_log_excerpts")
    if isinstance(rc_logs, dict) and rc_logs:
        lines.append("- 🚨 TRÍCH XUẤT NGUYÊN NHÂN LỖI GỐC TỪ LOG (đã đọc sẵn — dùng ngay, không cần chạy script dò tìm file log):")
        for log_rel, ex_lines in rc_logs.items():
            lines.append(f"  * `{log_rel}`:")
            for ex in ex_lines[:6]:
                lines.append(f"    > {ex}")
    return "\n".join(lines)


def sync_repo_code_index(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Maintain an mtime-cached symbol & line-range index at `.producer/repo_code_index.json` across CofiDocumentary & CofiRemotion."""
    root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parent.parent
    if (root / "input.json").is_file() and root.parent.name == "workspaces":
        root = root.parent.parent
    index_path = root / ".producer" / "repo_code_index.json"
    existing = _read_json_dict(index_path)
    old_files: dict[str, Any] = dict(existing.get("files") or {})

    rem_root = root.parent / "CofiRemotion"
    target_files: list[tuple[Path, str]] = []
    for top_py in ("app.py", "server.py", "desktop_app.py"):
        p = root / top_py
        if p.is_file():
            target_files.append((p, top_py))
    for sub in ("documentary", "services", "COFI_BRAIN"):
        sdir = root / sub
        if sdir.is_dir():
            for p in sorted(sdir.glob("*.py")):
                if p.is_file():
                    target_files.append((p, f"{sub}/{p.name}"))
    static_dir = root / "static"
    if static_dir.is_dir():
        for p in sorted(static_dir.glob("*.js")):
            if p.is_file():
                target_files.append((p, f"static/{p.name}"))
    if rem_root.is_dir():
        for rem_rel in (
            "src/vox-studio/vox-editorial-desk/index.tsx",
            "src/components/GeoJson3DMapStage.tsx",
            "src/components/SubtitleOverlay.tsx",
            "src/components/FramelessCinemaTextBeat.tsx",
            "src/Composition.tsx",
            "src/Root.tsx",
            "scripts/validate-vox-newsroom-ast.mjs",
            "scripts/turbo-nvenc-export.mjs",
            "scripts/universal_master_render.py",
        ):
            p = rem_root / rem_rel
            if p.is_file():
                target_files.append((p, f"CofiRemotion/{rem_rel}"))

    new_files: dict[str, Any] = {}
    changed = False
    for fpath, rel_key in target_files:
        try:
            st = fpath.stat()
            mtime = round(st.st_mtime, 2)
            size = st.st_size
        except OSError:
            continue
        prev = old_files.get(rel_key)
        if isinstance(prev, dict) and prev.get("mtime") == mtime and prev.get("size") == size:
            new_files[rel_key] = prev
        else:
            changed = True
            syms = _extract_file_symbols(fpath, rel_key)
            new_files[rel_key] = {
                "mtime": mtime,
                "size": size,
                "symbols": syms,
            }

    if changed or not existing:
        payload = {
            "schema_version": 1,
            "updated_at": _utc_now(),
            "files": new_files,
        }
        try:
            _atomic_write_json(index_path, payload)
        except OSError:
            pass
        return payload
    return existing


def format_compact_repo_code_brief(repo_root: str | Path | None = None, *, max_age_sec: float = 21600.0, limit: int = 10) -> str:
    """Return a compact summary of recently modified source files across CofiDocumentary & CofiRemotion."""
    idx = sync_repo_code_index(repo_root)
    files_map: dict[str, Any] = idx.get("files") or {}
    now_ts = datetime.now(timezone.utc).timestamp()
    recent: list[tuple[float, str]] = []
    for rel_key, meta in files_map.items():
        if not isinstance(meta, dict):
            continue
        mtime = float(meta.get("mtime") or 0.0)
        age = max(0.0, now_ts - mtime)
        if age <= max_age_sec:
            age_lbl = f"{int(age)}s ago" if age < 120 else f"{int(age // 60)}m ago"
            recent.append((mtime, f"`{rel_key}` ({age_lbl})"))
    recent.sort(key=lambda item: item[0], reverse=True)
    if not recent:
        return ""
    return "Recently modified code files in repo (last 6h): " + ", ".join(lbl for _, lbl in recent[:limit])


def build_codebase_surgical_locator(
    repo_root: str | Path | None = None,
    message: str = "",
    history: list[dict[str, Any]] | None = None,
    *,
    always_include_recent_code: bool = False,
    include_architecture_tree: bool = True,
    max_chars: int = 4200,
) -> str:
    """Pre-locate exact source files and `StartLine..EndLine` for any code feature, UI element, API endpoint,
    or function mentioned in `message` (and at most 1 prior user turn if `message` is a short confirmation)
    so fixing code (`fix code dự án`) reads ONLY the 1-2 responsible files with ZERO full-repo scanning.
    """
    if isinstance(repo_root, str) and not str(message or "").strip() and not Path(repo_root).is_dir():
        message = repo_root
        repo_root = None
    blobs: list[str] = []
    clean_msg = str(message or "").strip()
    if clean_msg:
        blobs.append(clean_msg)
    if (not clean_msg or _SHORT_FOLLOWUP_TRIGGER_RE.match(clean_msg)) and history:
        for item in reversed(list(history)[-6:]):
            if not isinstance(item, dict) or str(item.get("role") or "") != "user":
                continue
            txt = str(item.get("content") or "").strip()
            if not txt or _SHORT_FOLLOWUP_TRIGGER_RE.match(txt) or txt.lower() in {"/compact", "/nen", "/new", "/reset"}:
                continue
            blobs.append(txt[:1200])
            break
    combined = "\n".join(blobs)
    low = combined.lower()
    if not low and not always_include_recent_code:
        return ""

    idx = sync_repo_code_index(repo_root)
    files_map: dict[str, Any] = idx.get("files") or {}

    # Build fast lookup maps: file::symbol -> entry, symbol_lower -> list[entry]
    by_qualified: dict[str, dict[str, Any]] = {}
    by_sym_lower: dict[str, list[dict[str, Any]]] = {}
    for rel_key, meta in files_map.items():
        for sym_entry in (meta.get("symbols") or []):
            sname = str(sym_entry.get("symbol") or "")
            if sname:
                by_qualified[f"{rel_key}::{sname}"] = sym_entry
                by_sym_lower.setdefault(sname.lower(), []).append(sym_entry)

    matched_entries: list[dict[str, Any]] = []
    matched_subsystems: list[str] = []
    seen_keys: set[str] = set()

    def _add_entry(entry: dict[str, Any]) -> None:
        k = f"{entry.get('file')}::{entry.get('symbol')}::{entry.get('start_line')}"
        if k not in seen_keys:
            seen_keys.add(k)
            matched_entries.append(entry)

    # 1. Check explicit file names, module stems (>= 5 chars), or symbol names (>= 5 chars) mentioned in text first
    for rel_key, meta in files_map.items():
        base_name = Path(rel_key).name.lower()
        stem_name = Path(rel_key).stem.lower()
        stem_hit = len(stem_name) >= 5 and re.search(rf"\b{re.escape(stem_name)}\b", low) is not None
        if base_name in low or rel_key.lower() in low or stem_hit:
            for s in (meta.get("symbols") or [])[:5]:
                _add_entry(s)

    for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{5,}\b", combined):
        tlow = token.lower()
        if tlow in by_sym_lower:
            for s in by_sym_lower[tlow][:3]:
                _add_entry(s)

    # 2. Check semantic subsystem keyword map
    for sub_title, keywords, targets in SUBSYSTEM_KEYWORD_MAP:
        if any(kw in low for kw in keywords):
            matched_subsystems.append(sub_title)
            for targ in targets:
                if "::" in targ:
                    if targ in by_qualified:
                        _add_entry(by_qualified[targ])
                elif targ in files_map:
                    syms = (files_map[targ].get("symbols") or [])[:3]
                    for s in syms:
                        _add_entry(s)

    # Deterministic $0 pre-query against @trailhq/trail-code so EVERY code/debug chat turn
    # automatically uses Trail even before the LLM takes step 1.
    trail_block = ""
    if combined.strip() and len(combined.strip()) >= 4:
        try:
            from documentary.trail_manager import TrailCodeManager

            root_p = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[1]
            rem_p = root_p.parent / "CofiRemotion"
            tm = TrailCodeManager(root_p, rem_p)
            wants_remotion = any(
                kw in low
                for kw in ("remotion", ".tsx", "vox-", "vox_", "geojson3d", "cinematext", "turbo-nvenc", "subtitleoverlay")
            )
            trail_hit = tm.query_code_graph(combined[:220], include_remotion=wants_remotion, limit=3, max_chars=900)
            if trail_hit.get("ok") and trail_hit.get("snippet"):
                saved_lbl = f" (~{trail_hit['tokens_saved']:,} tokens tiết kiệm)" if trail_hit.get("tokens_saved") else ""
                trail_block = f"- 🌱 Kết quả tra trước tự động từ đồ thị `trail` (`{trail_hit.get('repo')}`{saved_lbl}):\n{trail_hit['snippet']}"
        except Exception:
            trail_block = ""

    recent_code_line = format_compact_repo_code_brief(repo_root, max_age_sec=21600.0, limit=8)
    if not matched_entries and not trail_block and not (always_include_recent_code and recent_code_line):
        return ""

    out_lines: list[str] = [
        "🛠️ BẢN ĐỒ ĐỊNH VỊ MÃ NGUỒN PHẪU THUẬT (`repo_code_index.json` + `.trail/cache` — CHẾ ĐỘ SỬA CODE APP: CHỈ ĐỌC/SỬA ĐÚNG 1–2 FILE CÓ TỌA ĐỘ DÒNG `StartLine..EndLine` DƯỚI ĐÂY, CẤM ĐỌC QUÉT REPO):",
        "- Đồ thị mã nguồn `trail` (`@trailhq/trail-code` MCP `trail` cho CofiDocumentary & `trail_remotion` cho CofiRemotion) ĐANG BẬT: nếu cần tra thêm hàm/luồng gọi chưa có dưới đây, BẮT BUỘC gọi thẳng `call_mcp_tool(ServerName=\"trail\" | \"trail_remotion\", ToolName=\"trail_file_api\" | \"trail_find_code\" | \"trail_trace_calls\", Arguments=...)` trước tiên thay vì `rg`/`Select-String`/đọc cả file.",
    ]
    if include_architecture_tree:
        out_lines.append(APP_ARCHITECTURE_MEMORY_TREE)
    if matched_subsystems:
        out_lines.append("- Phân hệ liên quan: " + " | ".join(matched_subsystems[:2]))
    if recent_code_line:
        out_lines.append(f"- {recent_code_line}")
    if matched_entries:
        out_lines.append("- Tọa độ hàm / lớp / route chính xác (dùng `read_file(Path, StartLine, EndLine)` hoặc `edit_file` trực tiếp):")
        for entry in matched_entries[:12]:
            out_lines.append(
                f"  * `{entry['file']}` dòng {entry['start_line']}..{entry['end_line']}: `{entry.get('display') or entry['symbol']}`"
            )
    if trail_block:
        out_lines.append(trail_block)

    res_text = "\n".join(out_lines)
    if len(res_text) > max_chars:
        res_text = res_text[: max_chars - 3].rstrip() + "..."
    return res_text


# ----------------------------------------------------------------------
# 3. Lightweight CLI Entrypoint (`python -m documentary.workspace_ledger`)
# ----------------------------------------------------------------------
def _cli_main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or surgically patch workspace beat shards & state ledger.")
    parser.add_argument("workspace", help="Path to job workspace directory")
    parser.add_argument("--summary", action="store_true", help="Print compact state ledger summary")
    parser.add_argument("--find", default=None, help="Search beats_index.json by keyword or beat_id")
    parser.add_argument("--timestamp", type=float, default=None, help="Find beat covering timestamp (seconds)")
    parser.add_argument("--get-beat", default=None, help="Print full JSON shard for a single beat_id")
    parser.add_argument("--patch-beat", default=None, help="Surgically patch a single beat_id with --json")
    parser.add_argument("--json", default=None, help="JSON object string for --patch-beat")
    parser.add_argument("--reason", default="", help="Optional mutation summary recorded in state_ledger.json")
    args = parser.parse_args()

    ws = Path(args.workspace).resolve()
    if args.patch_beat:
        if not args.json:
            raise SystemExit("--json is required with --patch-beat")
        patch_obj = json.loads(args.json)
        res = patch_workspace_beats(ws, {args.patch_beat: patch_obj}, reason=args.reason)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if args.get_beat:
        beat = load_single_beat(ws, args.get_beat)
        if beat is None:
            raise SystemExit(f"Beat not found: {args.get_beat}")
        print(json.dumps(beat, ensure_ascii=False, indent=2))
        return 0
    if args.find is not None or args.timestamp is not None:
        res = list_workspace_beats(ws, query=args.find, timestamp_sec=args.timestamp, limit=50)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    sync_workspace_ledger(ws)
    print(format_compact_ledger_brief(ws))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
