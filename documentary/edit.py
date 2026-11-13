from __future__ import annotations

from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from .codex_gateway import StageResult
from .edit_footage_fetcher import EditDirectFootageFetcher
from .prompts import _is_true_crime_vox25d_job, build_edit_batch_prompt, build_footage_eye_agent_prompt, build_phase_prompt
from .visuals import resolve_visual_strategy


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _positive_int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _nonnegative_int_env(name: str, default: int = 0) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _beat_id(beat: dict[str, Any]) -> str:
    return str(beat.get("beat_id") or "").strip()


def _chunks(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def _beat_duration(beat: dict[str, Any]) -> float:
    for key in ("duration_sec", "target_duration_sec", "estimated_duration_sec"):
        try:
            value = float(beat.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    return 0.0


def _duration_target_chunks(
    items: list[dict[str, Any]],
    max_items: int,
    target_duration_sec: int,
    max_duration_sec: int,
) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_duration = 0.0
    for item in items:
        duration = _beat_duration(item)
        would_exceed_items = bool(max_items > 0 and len(current) >= max_items)
        would_exceed_hard_max = bool(
            current
            and max_duration_sec > 0
            and current_duration + duration > max_duration_sec
        )
        if current and (would_exceed_items or would_exceed_hard_max):
            batches.append(current)
            current = []
            current_duration = 0.0
        current.append(item)
        current_duration += duration
        # The default duration is a soft target, not a hard cut. Finish the
        # batch only after a complete beat crosses the target so a long shot /
        # narration beat is never split merely to land exactly on five minutes.
        if target_duration_sec > 0 and current_duration >= target_duration_sec:
            batches.append(current)
            current = []
            current_duration = 0.0
    if current:
        batches.append(current)
    return batches


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    import os
    import time
    from uuid import uuid4

    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, indent=2)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp")
    temporary.write_text(raw, encoding="utf-8")
    for attempt in range(6):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt < 5:
                time.sleep(0.05 * (attempt + 1))
            else:
                try:
                    path.write_text(raw, encoding="utf-8")
                finally:
                    temporary.unlink(missing_ok=True)
                return


_SHOT_SCALE_CYCLE = (
    "WIDE_ESTABLISHING",
    "MEDIUM_SUBJECT",
    "CLOSE_UP_DETAIL",
    "MACRO_EVIDENCE_OR_FACE",
)


def _infer_act_index(beat: dict[str, Any], idx: int, total: int) -> int:
    raw_act = str(
        beat.get("act")
        or beat.get("act_id")
        or beat.get("actId")
        or beat.get("chapter_id")
        or ""
    ).strip().upper()
    m = re.search(r"(\d+)", raw_act)
    if m:
        return max(1, min(5, int(m.group(1))))
    if total <= 1:
        return 1
    ratio = idx / float(total)
    if ratio < 0.16:
        return 1
    if ratio < 0.42:
        return 2
    if ratio < 0.68:
        return 3
    if ratio < 0.86:
        return 4
    return 5


def _normalize_text_for_hash(text: str) -> str:
    cleaned = re.sub(r"<break[^>]*/>", " ", str(text or ""))
    cleaned = re.sub(r"[^\w\uac00-\ud7a3\u4e00-\u9fff]+", "", cleaned, flags=re.UNICODE)
    return cleaned.strip().lower()


def compute_beat_text_hash(text: str) -> str:
    norm = _normalize_text_for_hash(text)
    if not norm:
        return ""
    return hashlib.md5(norm.encode("utf-8")).hexdigest()[:12]


def sync_vox_manifest_beats_by_text_hash(
    vox_manifest: dict[str, Any] | list[dict[str, Any]],
    beats: list[dict[str, Any]],
) -> dict[str, Any]:
    """Synchronize `beat_id` foreign keys between `vox_scene_manifest.json` and `beats`
    using deterministic `text_hash` / `voice_text` matching so re-segmentation never shifts VOX bindings.
    """
    vox_entries: list[dict[str, Any]] = []
    if isinstance(vox_manifest, list):
        vox_entries = [x for x in vox_manifest if isinstance(x, dict)]
    elif isinstance(vox_manifest, dict):
        for k_list in ("scenes", "beats", "vox_scenes", "items"):
            if isinstance(vox_manifest.get(k_list), list):
                vox_entries = [x for x in vox_manifest[k_list] if isinstance(x, dict)]
                break

    beat_by_id: dict[str, dict[str, Any]] = {}
    beat_by_hash: dict[str, dict[str, Any]] = {}
    beat_norm_rows: list[tuple[str, str, dict[str, Any]]] = []

    for b in beats or []:
        if not isinstance(b, dict):
            continue
        bid = str(b.get("beat_id") or b.get("beatId") or b.get("id") or "").strip()
        btxt = str(
            b.get("narration_text")
            or b.get("voice_text")
            or b.get("subtitle_display_text")
            or b.get("narrationText")
            or b.get("text")
            or ""
        ).strip()
        bhash = compute_beat_text_hash(btxt)
        if bhash:
            b["text_hash"] = bhash
            beat_by_hash.setdefault(bhash, b)
        if bid:
            beat_by_id[bid] = b
            beat_norm_rows.append((bid, _normalize_text_for_hash(btxt), b))

    repaired: list[dict[str, str]] = []
    for ve in vox_entries:
        sc_id = str(
            ve.get("scene_id")
            or ve.get("vox_scene_id")
            or ve.get("voxSceneId")
            or ve.get("vox_id")
            or ve.get("id")
            or ""
        ).strip().upper()
        vtxt = str(
            ve.get("narration_text")
            or ve.get("voice_text")
            or ve.get("narrationText")
            or ve.get("text")
            or ve.get("voice_meaning")
            or ""
        ).strip()
        vhash = str(ve.get("text_hash") or "").strip() or compute_beat_text_hash(vtxt)
        if vhash:
            ve["text_hash"] = vhash
        old_bid = str(ve.get("beat_id") or ve.get("beatId") or "").strip()

        matched_beat: dict[str, Any] | None = None
        if vhash and vhash in beat_by_hash:
            matched_beat = beat_by_hash[vhash]
        elif vtxt:
            vnorm = _normalize_text_for_hash(vtxt)
            best_sim = 0.0
            for cand_bid, cand_norm, cand_b in beat_norm_rows:
                if not cand_norm:
                    continue
                if vnorm in cand_norm or cand_norm in vnorm:
                    sim = 0.92
                else:
                    sim = difflib.SequenceMatcher(None, vnorm, cand_norm).ratio()
                if sim > best_sim:
                    best_sim = sim
                    if sim >= 0.58:
                        matched_beat = cand_b

        if matched_beat is not None:
            new_bid = str(matched_beat.get("beat_id") or matched_beat.get("beatId") or "").strip()
            if new_bid and new_bid != old_bid:
                ve["beat_id"] = new_bid
                repaired.append({"scene_id": sc_id, "from_beat_id": old_bid, "to_beat_id": new_bid})
                for b_other in beats or []:
                    if isinstance(b_other, dict) and b_other is not matched_beat:
                        for k_sc in ("voxSceneId", "vox_scene_id", "vox_id", "voxId"):
                            if str(b_other.get(k_sc) or "").strip().upper() == sc_id:
                                b_other.pop(k_sc, None)
            if sc_id:
                matched_beat["voxSceneId"] = sc_id
                matched_beat["vox_scene_id"] = sc_id

    if isinstance(vox_manifest, dict):
        vox_manifest["text_hash_synced"] = True
        vox_manifest["repaired_beat_bindings"] = repaired
        return vox_manifest
    return {"scenes": vox_entries, "text_hash_synced": True, "repaired_beat_bindings": repaired}


def build_edit_rhythm_score(
    job: dict[str, Any],
    workspace: Path,
    beats: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the Master Human Film Editor Score (`version: 2`) across ALL niches & languages.

    Synchronizes `@edit` shot pacing, voice breathing holds, mid-beat caesuras, J/L-cuts,
    30% shot-scale progression, Fincher camera discipline, 5-act emotional color grading,
    and broadcast sound architecture (`-41dBFS` room-tone floor + BGM breath swells) with `@voice`.
    """
    try:
        from services.voice_rhythm_specialist import (
            resolve_editorial_craft_profile,
            resolve_job_rhythm_dna,
        )

        rhythm_dna = resolve_job_rhythm_dna(job)
        craft = resolve_editorial_craft_profile(rhythm_dna)
    except Exception:
        rhythm_dna = {}
        craft = {}

    editing_cad = rhythm_dna.get("editing_cadence") if isinstance(rhythm_dna.get("editing_cadence"), dict) else {}
    shot_pacing = editing_cad.get("shot_pacing_sec") if isinstance(editing_cad.get("shot_pacing_sec"), dict) else {}
    urgent_max = float(shot_pacing.get("urgent_max_sec") or 3.3)
    standard_avg = float(shot_pacing.get("standard_avg_sec") or 4.2)
    contemplative_min = float(shot_pacing.get("contemplative_min_sec") or 5.5)
    hold_threshold = float(editing_cad.get("dramatic_pause_hold_threshold_sec") or 1.15)
    hold_across_pause = bool(editing_cad.get("hold_visual_across_dramatic_pause", True))
    cut_style = str(editing_cad.get("cut_style") or "contrastive_hard_and_linger")
    pre_punch_cam = str(editing_cad.get("pre_punch_camera_motion") or "creeping_push_in_tension")
    post_punch_cam = str(editing_cad.get("post_punch_silence_camera_motion") or "frozen_micro_drift_linger")
    bgm_swell = float(editing_cad.get("bgm_silence_swell_db") or 2.0)

    jl_policy = craft.get("jl_cut_policy") if isinstance(craft.get("jl_cut_policy"), dict) else {}
    j_prelap_frames = int(jl_policy.get("j_cut_prelap_frames") or 9)
    l_linger_frames = int(jl_policy.get("l_cut_linger_frames") or 15)
    dissolve_frames = int(jl_policy.get("dissolve_frames") or 18)
    color_arc = craft.get("color_emotion_arc") if isinstance(craft.get("color_emotion_arc"), dict) else {}
    sound_soul = craft.get("sound_design_soul") if isinstance(craft.get("sound_design_soul"), dict) else {}
    pre_twist_drop_allowed = bool(sound_soul.get("pre_twist_bgm_drop_enabled", True))
    room_tone_floor_db = float(sound_soul.get("room_tone_floor_db") or -41.0)
    room_tone_gain = float(sound_soul.get("room_tone_linear_gain") or 0.015)

    voice_by_id: dict[str, dict[str, Any]] = {}
    pre_voice_breath_sec = 0.0
    vm_path = workspace / "voice_manifest.json"
    if vm_path.is_file():
        try:
            vm_data = json.loads(vm_path.read_text(encoding="utf-8"))
            pre_voice_breath_sec = float(vm_data.get("pre_voice_breath_sec") or 0.0)
            for vb in vm_data.get("beats") or []:
                if isinstance(vb, dict) and vb.get("beat_id"):
                    voice_by_id[str(vb["beat_id"]).strip()] = vb
        except Exception:
            pass

    fps = 30
    total_beats = len(beats)
    score_beats: list[dict[str, Any]] = []
    feel_counts: dict[str, int] = {}
    jl_counts: dict[str, int] = {}
    prev_scale = ""
    twist_drops_used = 0
    max_twist_drops = max(1, total_beats // 25)

    for idx, beat in enumerate(beats):
        bid = _beat_id(beat) or str(beat.get("id") or "").strip()
        parent_bid = str(beat.get("parent_beat_id") or bid).strip()
        vb = voice_by_id.get(bid) or voice_by_id.get(parent_bid) or {}
        nxt_beat = beats[idx + 1] if idx + 1 < total_beats else {}

        emo_reg = str(vb.get("emotion_register") or beat.get("emotion_register") or "narrative_flow")
        pause_sec = float(vb.get("pause_after_sec") if vb.get("pause_after_sec") is not None else (beat.get("pause_after_sec") or 0.0))
        pause_reason = str(vb.get("pause_reason") or beat.get("pause_reason") or "standard_narrative")
        caesuras = list(vb.get("editorial_caesuras") or beat.get("editorial_caesuras") or [])
        vtype = str(beat.get("visual_type") or "").upper()

        act_num = _infer_act_index(beat, idx, total_beats)
        nxt_act_num = _infer_act_index(nxt_beat, idx + 1, total_beats) if nxt_beat else act_num
        is_act_opening = idx == 0 or (idx > 0 and act_num != _infer_act_index(beats[idx - 1], idx - 1, total_beats))
        is_act_closing = bool(nxt_beat and act_num != nxt_act_num)

        if emo_reg == "urgent_action" or pause_reason in ("urgent_action_chain", "editorial_kinetic_shave"):
            cut_feel = "rapid_kinetic_cut"
            max_subclip_sec = urgent_max
            hold_silence_sec = 0.0
            forbid_mid_silence_cut = False
            camera_energy = "dynamic_urgent_push"
            bgm_lift_db = 0.0
        elif pause_reason == "pre_punch_anticipation":
            cut_feel = "tension_creep_hold"
            max_subclip_sec = round(standard_avg * 1.15, 2)
            hold_silence_sec = round(pause_sec, 3) if hold_across_pause else 0.0
            forbid_mid_silence_cut = True
            camera_energy = pre_punch_cam
            bgm_lift_db = round(bgm_swell * 0.5, 2)
        elif pause_reason in ("act_transition", "editorial_chapter_curtain_breath") or (
            is_act_closing and bool(beat.get("act") or beat.get("act_id"))
        ):
            cut_feel = "chapter_curtain_breath"
            max_subclip_sec = contemplative_min
            hold_silence_sec = round(pause_sec, 3) if hold_across_pause else 0.0
            forbid_mid_silence_cut = hold_across_pause
            camera_energy = "chapter_curtain_settle"
            bgm_lift_db = round(bgm_swell + 0.4, 2)
        elif (hold_across_pause and pause_sec >= hold_threshold) or emo_reg in {
            "stark_punch",
            "somber_tragedy",
            "suspense_question",
        } or pause_reason in ("editorial_twist_reveal_hold", "editorial_somber_empathy_hold"):
            cut_feel = "breath_synced_emotional_hold"
            max_subclip_sec = contemplative_min
            hold_silence_sec = round(pause_sec, 3) if hold_across_pause else 0.0
            forbid_mid_silence_cut = hold_across_pause and pause_sec >= 0.85
            camera_energy = post_punch_cam
            bgm_lift_db = round(bgm_swell if pause_sec >= hold_threshold else bgm_swell * 0.65, 2)
        else:
            cut_feel = "profile_signature_flow"
            max_subclip_sec = standard_avg
            hold_silence_sec = 0.0
            forbid_mid_silence_cut = False
            camera_energy = "gentle_sanctuary_drift" if "sanctuary" in cut_style else "steady_editorial_motion"
            bgm_lift_db = 0.0

        # J-Cut / L-Cut & Dissolve Choreography
        if "sanctuary" in cut_style:
            jl_cut_mode = "gentle_sanctuary_dissolve"
            visual_lead_frames = 0
            visual_trail_frames = dissolve_frames
        elif cut_feel == "chapter_curtain_breath":
            jl_cut_mode = "chapter_dissolve_and_j_prelap"
            visual_lead_frames = j_prelap_frames
            visual_trail_frames = dissolve_frames
        elif cut_feel == "breath_synced_emotional_hold":
            jl_cut_mode = "l_cut_emotional_linger"
            visual_lead_frames = 0
            visual_trail_frames = l_linger_frames
        elif cut_feel == "rapid_kinetic_cut":
            jl_cut_mode = "smash_cut_kinetic"
            visual_lead_frames = 0
            visual_trail_frames = 0
        elif is_act_opening and idx > 0:
            jl_cut_mode = "j_cut_prelap_pivot"
            visual_lead_frames = j_prelap_frames
            visual_trail_frames = 0
        else:
            jl_cut_mode = "hard_cut_on_breath"
            visual_lead_frames = 0
            visual_trail_frames = 0

        # 30% Shot-Scale Progression (never repeat identical shot scale on adjacent beats)
        if is_act_opening:
            rec_scale = "WIDE_ESTABLISHING"
        elif vtype == "CINEMA_TEXT" or emo_reg in ("stark_punch", "twist_reveal") or caesuras:
            rec_scale = "MACRO_EVIDENCE_OR_FACE"
        elif emo_reg == "somber_tragedy":
            rec_scale = "CLOSE_UP_DETAIL"
        else:
            rec_scale = _SHOT_SCALE_CYCLE[idx % len(_SHOT_SCALE_CYCLE)]
        if rec_scale == prev_scale:
            alt_idx = (_SHOT_SCALE_CYCLE.index(rec_scale) + 1) % len(_SHOT_SCALE_CYCLE)
            rec_scale = _SHOT_SCALE_CYCLE[alt_idx]
        prev_scale = rec_scale

        # Walter Murch's Three Jobs of Every Shot
        if is_act_opening:
            shot_job = "ESTABLISH_WORLD_AND_ATMOSPHERE"
        elif vtype == "CINEMA_TEXT" or emo_reg in ("stark_punch", "twist_reveal", "suspense_question") or caesuras:
            shot_job = "REVEAL_CONTRADICTION_OR_TWIST"
        elif emo_reg == "somber_tragedy" or idx == total_beats - 1:
            shot_job = "HUMAN_EMOTIONAL_AFTERMATH"
        else:
            shot_job = "ADVANCE_CAUSAL_MECHANISM"

        # Frame-accurate speech & caesura windows
        v_open = float(vb.get("visual_open_sec") if vb.get("visual_open_sec") is not None else (beat.get("start_sec") or 0.0))
        s_start = float(vb.get("start_sec") if vb.get("start_sec") is not None else (beat.get("speech_start_sec") or v_open))
        s_end = float(vb.get("speech_end_sec") if vb.get("speech_end_sec") is not None else (beat.get("speech_end_sec") or beat.get("end_sec") or s_start))
        v_close = float(vb.get("visual_close_sec") if vb.get("visual_close_sec") is not None else (beat.get("end_sec") or (s_end + pause_sec)))

        caesura_windows = [
            {
                "before_word": c.get("before_word"),
                "start_sec": round(s_start + float(c.get("local_start_sec") or 0.0), 3),
                "end_sec": round(s_start + float(c.get("local_end_sec") or 0.0), 3),
                "start_frame": int(round((s_start + float(c.get("local_start_sec") or 0.0)) * fps)),
                "end_frame": int(round((s_start + float(c.get("local_end_sec") or 0.0)) * fps)),
                "hold_sec": c.get("hold_sec"),
                "choreography": "freeze_macro_focus_drop_bgm_to_room_tone_then_punch_reveal",
            }
            for c in caesuras
            if isinstance(c, dict)
        ]

        use_pre_twist_drop = bool(
            pre_twist_drop_allowed
            and twist_drops_used < max_twist_drops
            and (caesura_windows or (emo_reg in ("stark_punch", "twist_reveal") and pause_sec >= 1.35))
        )
        if use_pre_twist_drop:
            twist_drops_used += 1

        act_grade = color_arc.get(f"act_{act_num}") or {
            "mood": "cinematic_documentary_neutral",
            "temp_shift": 0,
            "sat_pct": 92,
            "contrast_pct": 106,
            "vignette": 0.26,
        }

        feel_counts[cut_feel] = feel_counts.get(cut_feel, 0) + 1
        jl_counts[jl_cut_mode] = jl_counts.get(jl_cut_mode, 0) + 1

        _snap_e = job.get("channel_profile_snapshot") if isinstance(job, dict) and isinstance(job.get("channel_profile_snapshot"), dict) else {}
        _is_dv2_e = str((job or {}).get("channel_profile_id") or _snap_e.get("id") or "").strip() in {"channel-e544a64b7c", "channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2"}
        directive = {
            "cut_feel": cut_feel,
            "jl_cut_mode": jl_cut_mode,
            "visual_lead_frames": visual_lead_frames,
            "visual_trail_frames": visual_trail_frames,
            "shot_job": shot_job,
            "recommended_shot_scale": rec_scale,
            "eye_trace_focus_zone": "upper_center_safe_above_785px" if _is_dv2_e else "upper_center_safe_above_820px",
            "fincher_no_double_motion": True,
            "emotion_register": emo_reg,
            "act_index": act_num,
            "act_color_grade": act_grade,
            "start_frame": int(round(v_open * fps)),
            "speech_start_frame": int(round(s_start * fps)),
            "speech_end_frame": int(round(s_end * fps)),
            "end_frame": int(round(v_close * fps)),
            "pre_voice_breath_sec": round(pre_voice_breath_sec, 3) if idx == 0 else 0.0,
            "pause_after_sec": round(pause_sec, 3),
            "pause_reason": pause_reason,
            "has_mid_beat_caesura": bool(caesura_windows),
            "caesura_windows": caesura_windows,
            "recommended_max_subclip_sec": round(max_subclip_sec, 2),
            "hold_through_silence_sec": hold_silence_sec,
            "forbid_mid_silence_cut": forbid_mid_silence_cut,
            "camera_energy": camera_energy,
            "bgm_breath_lift_db": bgm_lift_db,
            "pre_twist_bgm_drop": use_pre_twist_drop,
            "room_tone_floor_db": room_tone_floor_db,
            "room_tone_linear_gain": room_tone_gain,
            "cut_style": cut_style,
        }
        beat["edit_rhythm"] = directive
        score_beats.append({"beat_id": bid, **directive})

    return {
        "version": 2,
        "generated_at": _now(),
        "archetype_id": rhythm_dna.get("archetype_id") or "default_documentary",
        "archetype_label_vi": rhythm_dna.get("archetype_label_vi") or "",
        "editor_feel_title_vi": editing_cad.get("editor_feel_title_vi") or "",
        "editor_rhythm_directive_vi": editing_cad.get("editor_rhythm_directive_vi") or "",
        "pre_voice_breath_sec": round(pre_voice_breath_sec, 3),
        "editorial_craft": craft,
        "shot_pacing_sec": {
            "urgent_max_sec": urgent_max,
            "standard_avg_sec": standard_avg,
            "contemplative_min_sec": contemplative_min,
        },
        "cut_style": cut_style,
        "feel_summary": feel_counts,
        "jl_cut_summary": jl_counts,
        "beats": score_beats,
    }


class EditCoordinator:
    TRANSIENT_FAILURE_MARKERS = (
        "connection",
        "disconnected",
        "network",
        "transport",
        "timeout",
        "timed out",
        "socket",
        "connection reset",
        "stream closed",
        "unexpected eof",
        "broken pipe",
        "temporarily unavailable",
        "context window",
        "context length",
        "maximum context",
        "conversation too long",
        "token limit",
    )

    def __init__(
        self,
        codex_gateway: Any,
        remotion_manager: Any,
        remotion_dir: str | Path,
        *,
        render_cache: Any | None = None,
        batch_size: int | None = None,
        batch_target_duration_sec: int | None = None,
        batch_max_duration_sec: int | None = None,
        batch_retries: int | None = None,
    ):
        self.codex_gateway = codex_gateway
        self.remotion_manager = remotion_manager
        self.remotion_dir = Path(remotion_dir).resolve()
        self.render_cache = render_cache
        self.batch_size = (
            max(0, int(batch_size))
            if batch_size is not None
            else _nonnegative_int_env("COFI_EDIT_BATCH_SIZE", 0)
        )
        self.batch_target_duration_sec = max(
            0,
            int(
                batch_target_duration_sec
                if batch_target_duration_sec is not None
                else _nonnegative_int_env("COFI_EDIT_BATCH_TARGET_DURATION_SEC", 0)
            ),
        )
        self.batch_max_duration_sec = (
            max(0, int(batch_max_duration_sec))
            if batch_max_duration_sec is not None
            else _nonnegative_int_env("COFI_EDIT_BATCH_MAX_DURATION_SEC", 0)
        )
        self.batch_retries = max(0, int(batch_retries if batch_retries is not None else _positive_int_env("COFI_EDIT_BATCH_RETRIES", 2, minimum=0)))

    def _batches(self, beats: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        return _duration_target_chunks(
            beats,
            self.batch_size,
            self.batch_target_duration_sec,
            self.batch_max_duration_sec,
        )

    @staticmethod
    def _progress_path(workspace: Path) -> Path:
        return workspace / "edit_progress.json"

    def _new_progress(self, beats: list[dict[str, Any]]) -> dict[str, Any]:
        assigned = [_beat_id(beat) for beat in beats if _beat_id(beat)]
        continuous = not any((self.batch_size, self.batch_target_duration_sec, self.batch_max_duration_sec))
        return {
            "version": 1,
            "status": "running" if assigned else "completed",
            "batch_size": self.batch_size,
            "batch_target_duration_sec": self.batch_target_duration_sec,
            "batch_max_duration_sec": self.batch_max_duration_sec,
            "assigned_beat_ids": assigned,
            "completed_beat_ids": [],
            "pending_beat_ids": assigned,
            "total_beats": len(assigned),
            "completed_beats": 0,
            "current_batch": 0,
            "total_batches": len(self._batches(beats)),
            "attempts": 0,
            "session_rotations": 0,
            "last_error": "",
            "last_checkpoint_at": None,
            "status_message": (
                "Chuẩn bị dựng liên tục đến hết video; tiến trình được lưu theo từng beat."
                if continuous
                else "Chuẩn bị dựng video theo các giới hạn batch đã cấu hình."
            ),
            "updated_at": _now(),
        }

    def _load_or_initialize_progress(self, workspace: Path, beats: list[dict[str, Any]]) -> dict[str, Any]:
        current = self._new_progress(beats)
        path = self._progress_path(workspace)
        previous: dict[str, Any] = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    previous = loaded
            except (OSError, json.JSONDecodeError):
                previous = {}
        if previous.get("version") == 1 and previous.get("assigned_beat_ids") == current["assigned_beat_ids"]:
            completed = [
                str(value)
                for value in (previous.get("completed_beat_ids") or [])
                if str(value) in current["assigned_beat_ids"]
            ]
            current["completed_beat_ids"] = list(dict.fromkeys(completed))
            for key in ("attempts", "session_rotations", "last_error", "last_checkpoint_at"):
                if key in previous:
                    current[key] = previous[key]
        self._save_progress(workspace, current)
        return current

    def _save_progress(self, workspace: Path, progress: dict[str, Any]) -> None:
        assigned = [str(value) for value in (progress.get("assigned_beat_ids") or [])]
        completed = [str(value) for value in (progress.get("completed_beat_ids") or []) if str(value) in assigned]
        progress["completed_beat_ids"] = list(dict.fromkeys(completed))
        progress["pending_beat_ids"] = [beat_id for beat_id in assigned if beat_id not in progress["completed_beat_ids"]]
        progress["completed_beats"] = len(progress["completed_beat_ids"])
        progress["total_beats"] = len(assigned)
        progress["updated_at"] = _now()
        if not progress["pending_beat_ids"]:
            progress["status"] = "completed"
        _write_json_atomic(self._progress_path(workspace), progress)

    def _sync_completed_from_disk(self, workspace: Path, progress: dict[str, Any]) -> None:
        """Merge beat-level progress written by the live editor into coordinator state."""
        path = self._progress_path(workspace)
        try:
            latest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(latest, dict):
            return
        assigned = [str(value) for value in (progress.get("assigned_beat_ids") or [])]
        if latest.get("version") != 1 or latest.get("assigned_beat_ids") != assigned:
            return
        completed = [str(value) for value in (progress.get("completed_beat_ids") or []) if str(value) in assigned]
        completed.extend(
            str(value)
            for value in (latest.get("completed_beat_ids") or [])
            if str(value) in assigned
        )
        progress["completed_beat_ids"] = list(dict.fromkeys(completed))
        latest_checkpoint = latest.get("last_checkpoint_at")
        if latest_checkpoint:
            progress["last_checkpoint_at"] = latest_checkpoint
        self._save_progress(workspace, progress)

    def _is_transient_failure(self, result: StageResult) -> bool:
        message = str(result.last_message or "").strip().lower()
        if not message:
            return True
        return any(marker in message for marker in self.TRANSIENT_FAILURE_MARKERS)

    def _run_dedicated_footage_eye_agent(
        self,
        job: dict[str, Any],
        workspace: Path,
        beats: list[dict[str, Any]],
    ) -> StageResult | None:
        """Run the dedicated @footage AI Agent to hunt, cut, and eye-verify archival footage
        before @edit begins timeline construction."""
        from .critic_loops import audit_footage_hygiene, is_live_critic_gateway_available

        hygiene = audit_footage_hygiene(workspace, job)
        if str(hygiene.get("status") or "").upper() == "PASSED" and int(hygiene.get("assets_inspected") or 0) > 0:
            return None
        if not is_live_critic_gateway_available(self.codex_gateway):
            return None

        max_rounds = 2
        last_res: StageResult | None = None
        for attempt in range(1, max_rounds + 1):
            ftg_prompt = build_footage_eye_agent_prompt(
                job,
                workspace,
                self.remotion_dir,
                beats,
                failed_report=hygiene if (hygiene.get("failures") or hygiene.get("failed_assets")) else None,
            )
            last_res = self._run_batch_prompt(job, workspace, ftg_prompt)
            hygiene = audit_footage_hygiene(workspace, job)
            if str(hygiene.get("status") or "").upper() == "PASSED" and int(hygiene.get("assets_inspected") or 0) > 0:
                return StageResult(0, f"@footage AI Agent đã duyệt bằng mắt {hygiene.get('assets_inspected', 0)} clip (PASSED).", workspace / ".producer" / "edit")
        return last_res

    def _run_batch_prompt(self, job: dict[str, Any], workspace: Path, prompt: str) -> StageResult:
        reusable = getattr(self.codex_gateway, "run_prompt_reusable", None)
        if callable(reusable):
            return reusable(prompt, workspace, "edit", use_remotion_root=True)
        runner = getattr(self.codex_gateway, "run_prompt", None)
        if callable(runner):
            return runner(prompt, workspace, "edit", use_remotion_root=True)
        return self.codex_gateway.run(job, "edit", workspace)

    def _checkpoint(self, job: dict[str, Any], workspace: Path, progress: dict[str, Any], note: str) -> None:
        checkpoint = self.remotion_manager.checkpoint(job, workspace, note=note)
        progress["last_checkpoint_at"] = checkpoint.get("saved_at") if isinstance(checkpoint, dict) else _now()
        self._save_progress(workspace, progress)

    def run(self, job: dict[str, Any], workspace: str | Path) -> StageResult:
        workspace = Path(workspace).resolve()
        visual_path = workspace / "visual_manifest.json"
        try:
            visual = json.loads(visual_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Không đọc được visual_manifest.json để dựng theo batch: {exc}") from exc
        beats = [item for item in (visual.get("beats") or []) if isinstance(item, dict) and _beat_id(item)]
        if not beats:
            raise RuntimeError("visual_manifest.json không có beat hợp lệ để dựng")

        from .vox_engine import VoxBlenderBridge, VoxSemanticRouter, is_vox_satellite_enabled
        from .financial_vox_engine import FinancialVoxSemanticRouter, is_financial_vox_enabled
        is_true_crime_vox25d = _is_true_crime_vox25d_job(job)
        vox_enabled = False if is_true_crime_vox25d else is_vox_satellite_enabled(job)
        fin_vox_enabled = is_financial_vox_enabled(job)
        if is_true_crime_vox25d:
            legacy_keys = (
                "scene_archetype",
                "archetype_label",
                "archetype_cluster",
                "composable_scene_spec",
                "vox_sfx_events",
                "vox_plate_url",
                "vox_motion_url",
                "vox_preview_url",
                "render_vox_board",
                "dna_visual_slot",
                "motion_treatment",
            )
            cleaned_any = False
            for beat_item in beats:
                for lk in legacy_keys:
                    if lk in beat_item:
                        beat_item.pop(lk, None)
                        cleaned_any = True
            if cleaned_any:
                visual["beats"] = beats
                _write_json_atomic(visual_path, visual)
            _vox_manifest_p = workspace / "vox_scene_manifest.json"
            if _vox_manifest_p.is_file():
                try:
                    _vm = json.loads(_vox_manifest_p.read_text(encoding="utf-8"))
                    if str(_vm.get("job_id") or "").strip() not in {"", str(job.get("id") or workspace.name).strip()} or not _vm.get("scenes"):
                        _vox_manifest_p.unlink(missing_ok=True)
                except Exception:
                    _vox_manifest_p.unlink(missing_ok=True)
        elif vox_enabled and any(not b.get("scene_archetype") or not b.get("dna_visual_slot") for b in beats):
            router = VoxSemanticRouter()
            beats = router.route_timeline(beats, job)
            visual["beats"] = beats
            _write_json_atomic(visual_path, visual)
        elif fin_vox_enabled and any(not b.get("scene_archetype") or not b.get("dna_visual_slot") for b in beats):
            fin_router = FinancialVoxSemanticRouter()
            beats = fin_router.route_timeline(beats, job)
            visual["beats"] = beats
            _write_json_atomic(visual_path, visual)

        strategy, visual_mix = resolve_visual_strategy(job, workspace)
        if not strategy:
            strategy = str(visual.get("visual_strategy") or "full_footage").strip().lower()
        visual["visual_strategy"] = strategy
        if visual_mix:
            visual["visual_mix"] = visual_mix
        _write_json_atomic(visual_path, visual)

        # Master Human Film Editor Voice Sculpting Pass:
        # Actively sculpts cold-open pre-voice breath, chapter/twist breathing room, kinetic action
        # shaves, and zero-crossing mid-beat caesuras from 1st-gen stems while keeping 100% channel voice consistency.
        from .editorial_voice_cutter import (
            sculpt_editorial_voice_timeline,
            sync_remotion_public_audio_and_srt,
        )

        try:
            voice_cut_res = sculpt_editorial_voice_timeline(
                job,
                workspace,
                remotion_dir=self.remotion_dir,
            )
            if voice_cut_res.get("applied") and visual_path.is_file():
                visual = json.loads(visual_path.read_text(encoding="utf-8"))
                beats = [item for item in (visual.get("beats") or []) if isinstance(item, dict) and _beat_id(item)]
        except Exception:
            pass

        rhythm_score = build_edit_rhythm_score(job, workspace, beats)
        visual["rhythm_archetype_id"] = rhythm_score.get("archetype_id")
        _write_json_atomic(visual_path, visual)
        _write_json_atomic(workspace / "edit_rhythm_score.json", rhythm_score)
        if self.remotion_dir:
            _jid_rhythm = str(job.get("id") or workspace.name).strip()
            _rem_pub_rhythm = Path(self.remotion_dir) / "public" / "jobs" / _jid_rhythm
            if _rem_pub_rhythm.exists():
                _write_json_atomic(_rem_pub_rhythm / "edit_rhythm_score.json", rhythm_score)

        preset_id = str(((job.get("editing_dna") or {}).get("preset_id") if isinstance(job.get("editing_dna"), dict) else "") or "").strip()
        # DEDICATED @footage AI AGENT STAGE (STEP 4 TOOLS REMOVED):
        # Before @edit builds the timeline, delegate 100% of finding footage, inspecting STORYBOARD/GRID by eye
        # (`read_file`), cutting clips with calibrated safe crops, and verifying VERIFY_FTG_CLIPS_*.jpg to @footage.
        if strategy != "full_ai":
            ftg_agent_res = self._run_dedicated_footage_eye_agent(job, workspace, beats)
            if ftg_agent_res is not None and ftg_agent_res.returncode != 0:
                return ftg_agent_res

        prepare_media = getattr(self.remotion_manager, "prepare_job_media", None)
        if callable(prepare_media):
            prepare_media(job, workspace)
        if self.remotion_dir:
            _jid_rhythm2 = str(job.get("id") or workspace.name).strip()
            _rem_pub_rhythm2 = Path(self.remotion_dir) / "public" / "jobs" / _jid_rhythm2
            if _rem_pub_rhythm2.exists():
                _write_json_atomic(_rem_pub_rhythm2 / "edit_rhythm_score.json", rhythm_score)

        if is_true_crime_vox25d and self.remotion_dir:
            job_id_clean = str(job.get("id") or workspace.name).strip()
            _pub_vm_path = Path(self.remotion_dir) / "public" / "jobs" / job_id_clean / "vox_scene_manifest.json"
            if _pub_vm_path.is_file():
                try:
                    _pvm = json.loads(_pub_vm_path.read_text(encoding="utf-8"))
                    if str(_pvm.get("job_id") or "").strip() not in {"", job_id_clean} or not _pvm.get("scenes"):
                        _pub_vm_path.unlink(missing_ok=True)
                except Exception:
                    _pub_vm_path.unlink(missing_ok=True)

        # Strict profile isolation: True Crime profiles build bespoke Remotion Vox directly from their own locked
        # toolkit (`china-crime-newsroom` V13 Composable Lego Grammar + `FramelessCinemaTextBeat.tsx` on `channel-kr-truecrime-director-v2`;
        # `VoxTactileNewsPrimitives.tsx` on `channel-e544a64b7c`) without pre-baked template plates;
        # never merge or share editing/Vox style across different channel profiles.
        if vox_enabled or fin_vox_enabled:
            job_id = str(job.get("id") or workspace.name).strip()
            bridge = VoxBlenderBridge()
            vox_context = bridge.materialize_job_vox_assets(
                job=job,
                workspace=workspace,
                beats=beats,
                remotion_dir=self.remotion_dir,
                render_plates=os.getenv("COFI_VOX_RENDER_PLATES", "1") != "0",
            )
            visual["beats"] = beats
            _write_json_atomic(visual_path, visual)
            _write_json_atomic(workspace / "vox_scene_manifest.json", vox_context)
            if self.remotion_dir:
                remotion_pub = Path(self.remotion_dir) / "public" / "jobs" / job_id
                if remotion_pub.exists():
                    _write_json_atomic(remotion_pub / "vox_scene_manifest.json", vox_context)

        status = self.remotion_manager.status()
        if status.get("ok") and os.getenv("COFI_AUTO_START_REMOTION_STUDIO", "0") == "1":
            self.remotion_manager.start_studio(job, workspace)
        else:
            self.remotion_manager.ensure_session(job, workspace)

        progress = self._load_or_initialize_progress(workspace, beats)
        completed = list(progress.get("completed_beat_ids") or [])
        completed_set = set(completed)
        batches = self._batches(beats)
        messages: list[str] = []
        self._checkpoint(job, workspace, progress, "Checkpoint trước khi Codex tiếp tục edit theo batch")
        if self.render_cache is not None:
            if getattr(self.render_cache, "render_during_edit", False):
                starter = getattr(self.render_cache, "start", None)
                if callable(starter):
                    starter(job, workspace, beats)
            else:
                preparer = getattr(self.render_cache, "prepare", None)
                if callable(preparer):
                    try:
                        preparer(job, workspace, beats)
                    except Exception:
                        pass

        ran_any_batch = False
        for batch_index, batch in enumerate(batches, start=1):
            batch_ids = [_beat_id(beat) for beat in batch if _beat_id(beat)]
            if not any(beat_id not in completed_set for beat_id in batch_ids):
                continue
            ran_any_batch = True

            result: StageResult | None = None
            expected_ids: list[str] = []
            for attempt in range(self.batch_retries + 1):
                # The editor saves completed beat IDs while it works. If a long
                # continuous turn disconnects, reload that durable progress before
                # reconnecting so the new Codex session skips already-finished work.
                self._sync_completed_from_disk(workspace, progress)
                completed = list(progress.get("completed_beat_ids") or [])
                completed_set = set(completed)
                pending_batch = [beat for beat in batch if _beat_id(beat) not in completed_set]
                expected_ids = [_beat_id(beat) for beat in pending_batch if _beat_id(beat)]
                if not expected_ids:
                    result = StageResult(0, "Beat-level checkpoint đã hoàn tất phần việc còn lại.", workspace / ".producer" / "edit")
                    break

                progress["current_batch"] = batch_index
                progress["status"] = "running"
                progress["last_error"] = ""
                progress["status_message"] = (
                    f"Đang dựng liên tục từ {expected_ids[0]} đến {expected_ids[-1]}"
                    if len(batches) == 1
                    else f"Đang dựng {', '.join(expected_ids)} · batch {batch_index}/{len(batches)}"
                )
                progress["attempts"] = int(progress.get("attempts") or 0) + 1
                self._save_progress(workspace, progress)
                prompt = build_edit_batch_prompt(
                    job,
                    workspace,
                    self.remotion_dir,
                    pending_batch,
                    completed_beat_ids=completed,
                    batch_index=batch_index,
                    total_batches=len(batches),
                )
                result = self._run_batch_prompt(job, workspace, prompt)
                if result.last_message:
                    messages.append(result.last_message)
                if result.returncode == 0:
                    completed.extend(beat_id for beat_id in expected_ids if beat_id not in completed_set)
                    completed_set.update(expected_ids)
                    progress["completed_beat_ids"] = completed
                    self._save_progress(workspace, progress)
                    break
                self._sync_completed_from_disk(workspace, progress)
                completed = list(progress.get("completed_beat_ids") or [])
                completed_set = set(completed)
                progress["last_error"] = result.last_message or "Codex bị ngắt trước khi hoàn tất batch Edit."
                progress["status_message"] = "Edit bị ngắt; đang kết nối lại từ beat chưa hoàn tất."
                self._save_progress(workspace, progress)
                if attempt >= self.batch_retries or not self._is_transient_failure(result):
                    progress["status"] = "failed"
                    self._save_progress(workspace, progress)
                    return result
                remaining_ids = [beat_id for beat_id in batch_ids if beat_id not in completed_set]
                progress["status_message"] = f"Đang tiếp tục từ {remaining_ids[0] if remaining_ids else 'checkpoint'} trong cùng phiên Codex."
                self._save_progress(workspace, progress)

            if result is None or result.returncode != 0:
                progress["status"] = "failed"
                self._save_progress(workspace, progress)
                return result or StageResult(1, "Edit batch failed", workspace / ".producer" / "edit")

            self._sync_completed_from_disk(workspace, progress)
            completed = list(progress.get("completed_beat_ids") or [])
            completed_set = set(completed)
            progress["last_error"] = ""
            progress["status_message"] = f"Đã dựng xong {len(completed)}/{len(beats)} beat · batch {batch_index}/{len(batches)}"
            self._checkpoint(
                job,
                workspace,
                progress,
                f"Đã hoàn tất Edit batch {batch_index}/{len(batches)}: {', '.join(batch_ids)}",
            )

            if batch_index < len(batches):
                progress["status_message"] = (
                    f"Đã chốt batch {batch_index}/{len(batches)}; "
                    "Codex sẽ tiếp tục batch kế tiếp trong cùng phiên từ checkpoint."
                )
                self._save_progress(workspace, progress)

        qa_rework_ticket = workspace / ".producer" / "qa_rejection_feedback" / "edit.md"
        if not ran_any_batch and qa_rework_ticket.is_file():
            progress["status"] = "running"
            progress["status_message"] = "🔄 Đang tự động sửa lỗi dựng theo yêu cầu kiểm duyệt QA (@evidence_qa)..."
            self._save_progress(workspace, progress)
            rework_prompt = (
                build_phase_prompt(job, "edit", workspace, self.remotion_dir)
                + "\n\nSURGICAL QA REWORK EXECUTION:\n"
                + "All beat batches were previously built, so do NOT rebuild unaffected completed beats from scratch. "
                + "Inspect the existing Remotion composition, manifest files, and `edit_checkpoint.json`, resolve every exact defect listed in the MANDATORY @evidence_qa REJECTION REWORK DIRECTIVE above, validate ESLint + `npx remotion compositions src/index.ts --log=error`, and update `edit_checkpoint.json`."
            )
            rework_res = self._run_batch_prompt(job, workspace, rework_prompt)
            if rework_res and rework_res.last_message:
                messages.append(rework_res.last_message)
            if rework_res is not None and rework_res.returncode != 0:
                progress["status"] = "failed"
                progress["last_error"] = rework_res.last_message or "QA rework turn failed"
                self._save_progress(workspace, progress)
                return rework_res
            if callable(prepare_media):
                try:
                    prepare_media(job, workspace)
                except Exception:
                    pass
            self._checkpoint(job, workspace, progress, "Đã tự động sửa lỗi Edit theo phiếu phản biện QA")

        # Ensure any mid-session CLI voice cuts (`editorial_voice_cutter`) made by `@edit`
        # are mirrored to `CofiRemotion/public/jobs/<job_id>/` and reflected in `beats` before screening.
        try:
            if visual_path.is_file():
                latest_vis = json.loads(visual_path.read_text(encoding="utf-8"))
                latest_beats = [item for item in (latest_vis.get("beats") or []) if isinstance(item, dict) and _beat_id(item)]
                if latest_beats:
                    beats = latest_beats
            sync_remotion_public_audio_and_srt(
                job=job,
                workspace=workspace,
                remotion_dir=self.remotion_dir,
            )
        except Exception:
            pass

        from .critic_loops import audit_edit_timeline_and_screen, is_live_critic_gateway_available

        screening = audit_edit_timeline_and_screen(job, workspace, self.remotion_dir, beats)
        if screening.get("issues") and is_live_critic_gateway_available(self.codex_gateway):
            from .nexus_coordinator import NexusCoordinator
            from .prompts import _is_director_v2_true_crime_job

            is_dir_v2 = _is_director_v2_true_crime_job(job)
            safe_zone_fix_rule = (
                "2. If any footage hygiene / semantic match / auto-cut violation (`real_footage_floor_violation`, `unverified_blind_auto_cut`, `observed_content_voice_semantic_mismatch`, `edge_banner_or_text_overlay_detected`, `internal_hard_cut_detected`) is listed, NEVER run automatic cutting/splicing (`--auto`): either run `python -m documentary.edit_footage_fetcher --probe-storyboard <URL> --probe-id <ID>`, inspect `STORYBOARD_<ID>.jpg` and `GRID_<ID>.jpg` by eye (`read_file`), and slice the exact timestamp with calibrated `--crop-mode \"crop=W:H:X:Y\"` (stripping 100% of third-party logos and running text) + `--observed-content` matching 100% of the spoken sentence, OR if no authentic footage matches 100% of that sentence, route that beat to Priority #2 bespoke VOX illustration (`<Desk>` / `<GeoJson3DMapStage>`).\n"
                "3. If `vox_template_monoculture`, `vox_callout_loupe_collision`, `vox_fake_geojson_polyline`, `vox_subtitle_safe_zone_warning`, `legacy_vox_primitive_leak`, or `vox_newsroom_ast_violation` is listed, "
                "choreograph VOX scenes dynamically by video content (`VOX_01..VOX_N`) using the bound `cofi-vox-blender-director` skill and `src/vox-studio/vox-editorial-desk/index.tsx` (`<Desk>`, `<World>`, `<BlackCard>`, `voxCutoutSlap12`, `<PaperPeelSheetReveal>`, `<TornRedBackingPhotoFrame>`, `<HalftoneArchivalVideoCutout>`, `<HalftoneDieCutSubject>`, `<SerratedPostageLabel>`, `<GrommetedLuggageTag>`, `<BraidedRedYarnLink>`, `<SlideIn>`, `<VoxVideoPaper>`, `<VoxPhotoPaper>`, `<DieCutSticker>`, `<TornClipping>`, `<IndexCard>`, `<RedCircle>`, `<RedLine>`, `<Highlight>`, `<DimensionBracket>`, `<OpticalLoupe>`) + 3D Satellite Map `<GeoJson3DMapStage>` and 2.5D Map `<ArchitecturalCrimePlan>` (with `max_uses = 1` dedicated prop/cutout per VOX scene, `30%–40%` breathing room, and `read_file` eye verification), "
                "use exclusively `src/components/FramelessCinemaTextBeat.tsx` for dark cinema motion text (`0%` `VoxNewsroomMotionText` paper cards), "
                "keep every Vox/graphic element inside `[60 <= x <= 1860, 40 <= y <= 785]` so the `62px–66px` bottom subtitle zone (`800px–1040px`) stays 100% clear, "
                "and verify `node scripts/validate-vox-newsroom-ast.mjs` passes with 0 violations.\n"
                if is_dir_v2
                else "2. If `vox_subtitle_safe_zone_warning` is listed, lift any lower graphic/card above `top: 835px` so the bottom subtitle zone (`860px-1040px`) stays 100% clear.\n"
            )
            qa_charter = NexusCoordinator().build_specialist_soul_header(
                "evidence_qa",
                "Stage 6 Edit Timeline Continuity & Safe-Zone Surgical Critic",
            )
            fix_prompt = (
                qa_charter
                + "\nEDIT SCREENING CRITIC PASS — Surgical Timeline Polish:\n"
                "The Edit Screening Sensor detected the following continuity / safe-zone / role-mix issues:\n"
                f"{json.dumps(screening['issues'], ensure_ascii=False, indent=2)}\n\n"
                "Apply surgical fixes to resolve ALL listed issues (especially any `severity: \"blocker\"` items):\n"
                "1. If `adjacent_asset_reuse` is listed, vary camera framing/crop/overlay or alternate approved beat assets so back-to-back beats do not look frozen on identical framing.\n"
                + safe_zone_fix_rule
                + "4. Do NOT alter beat durations, narration sync, or composition registration."
            )
            fix_res = self._run_batch_prompt(job, workspace, fix_prompt)
            if fix_res and fix_res.last_message:
                messages.append(fix_res.last_message)
            screening = audit_edit_timeline_and_screen(job, workspace, self.remotion_dir, beats)

        if screening.get("status") == "FAILED":
            blocker_summaries = [
                f"{iss.get('type')}: {iss.get('detail') or iss.get('details')}"
                for iss in (screening.get("issues") or [])
                if isinstance(iss, dict) and iss.get("severity") == "blocker"
            ]
            raise RuntimeError(
                "EDIT Screening Gate FAILED with unresolved blocker(s): " + " | ".join(blocker_summaries)
            )

        progress["current_batch"] = len(batches)
        progress["status"] = "completed"
        progress["status_message"] = f"Đã dựng xong {len(beats)}/{len(beats)} beat; preview sẵn sàng để duyệt."
        self._checkpoint(job, workspace, progress, "Bản dựng preview đã cập nhật; chờ người dùng duyệt trước khi xuất")
        if self.render_cache is not None and not getattr(self.render_cache, "render_during_edit", False):
            preparer = getattr(self.render_cache, "prepare", None)
            if callable(preparer):
                try:
                    preparer(job, workspace, beats)
                except Exception:
                    pass
        return StageResult(
            returncode=0,
            last_message="\n".join(message for message in messages if message)[-12000:],
            log_path=workspace / ".producer" / "edit",
        )
