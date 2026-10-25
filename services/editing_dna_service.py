"""
Editing DNA Service for CofiDocumentary (Milestone 3).
Defines Editing Style DNA schemas, built-in Remotion presets, extraction from completed projects,
and persistence ("Lock Approved Edit Style to Channel Profile").
"""

from __future__ import annotations

import copy
import json
import os
import statistics
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CHANNEL_PROFILES_FILE = DATA_DIR / "channel_profiles.json"
WORKSPACES_DIR = ROOT / "workspaces"
JOBS_DIR = DATA_DIR / "jobs"

_file_lock = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PacingDict(dict):
    """
    Dictionary representing shot pacing parameters that can also be treated as a float
    for backward compatibility with legacy code.
    """
    def __float__(self) -> float:
        val = self.get("target_beat_duration_sec") or self.get("average_beat_duration_sec") or self.get("typical_pacing_sec") or 5.0
        try:
            return float(val)
        except Exception:
            return 5.0

    def __int__(self) -> int:
        return int(float(self))

    def __round__(self, ndigits: int | None = None):
        return round(float(self), ndigits)


BUILTIN_EDITING_PRESETS: dict[str, dict[str, Any]] = {
    "2.5d_technical": {
        "preset_id": "2.5d_technical",
        "name": "2.5D Technical & Infrastructure Investigation",
        "version": 1,
        "pacing": PacingDict({
            "target_beat_duration_sec": 4.5,
            "typical_pacing_sec": 4.5,
            "shot_range_sec": [3.5, 7.0],
            "average_beat_duration_sec": 4.5,
            "max_routine_shot_sec": 8.0,
            "pacing_curve": "accelerating_towards_act_climax",
            "pacing_wpm": 140.0,
        }),
        "visual_mix": {
            "footage": 0.50,
            "ai": 0.35,
            "motion": 0.15,
            "footage_ratio": 0.50,
            "ai_visual_ratio": 0.35,
            "motion_overlay_ratio": 0.15,
            "preferred_routing": "hybrid",
        },
        "editing_archetypes": [
            "2.5d_satellite_map",
            "technical_hud_telemetry",
            "blueprint_vs_reality_split",
            "chapter_hero_banner",
            "media_anchored_annotation",
        ],
        "subtitle_style": {
            "font_family": "Pretendard",
            "font_size": 44,
            "font_size_px": 44,
            "color": "#FFFFFF",
            "base_color": "#FFFFFF",
            "highlight_color": "#38BDF8",
            "stroke_color": "#000000",
            "stroke_width": 16,
            "position": "bottom_center",
        },
        "color_grade": {
            "tone_preset": "technical_cool_cyan",
            "lut_name": "clean_broadcast_cool",
            "vignette_opacity": 0.75,
        },
        "audio_rules": {
            "bgm_volume_db": -22.0,
            "ducking_db": -12.0,
            "music_ducking_db": -12.0,
            "sfx_chapter_hit": True,
            "sfx_hit_on_chapter": True,
            "telemetry_beeps": True,
            "tension_drone_under_interrogation": False,
        },
        "editorial_rules": [
            "Always ground technical claims with KeyMetricCallout telemetry cards",
            "Every new geographical location must introduce a 2.5D MapSatelliteMotionStage",
            "Never hold a static visual longer than 8 seconds without camera push or telemetry scan",
            "Transformative annotations must be placed over key footage elements",
        ],
    },
    "forensic_noir": {
        "preset_id": "forensic_noir",
        "name": "Forensic Noir Full-AI True Crime",
        "version": 1,
        "pacing": PacingDict({
            "target_beat_duration_sec": 5.5,
            "typical_pacing_sec": 5.5,
            "shot_range_sec": [4.0, 8.0],
            "average_beat_duration_sec": 5.5,
            "max_routine_shot_sec": 9.0,
            "pacing_curve": "tense_investigative_suspense",
            "pacing_wpm": 130.0,
        }),
        "visual_mix": {
            "footage": 0.0,
            "ai": 0.85,
            "motion": 0.15,
            "footage_ratio": 0.0,
            "ai_visual_ratio": 0.85,
            "motion_overlay_ratio": 0.15,
            "preferred_routing": "full_ai",
        },
        "editing_archetypes": [
            "#V_FULLSCREEN_GIS_FLIGHT",
            "#V_FULLSCREEN_SATELLITE_RECON",
            "S3_FULLSCREEN_GIS_FLIGHT",
            "S4_FULLSCREEN_SATELLITE_RECON",
            "S1_KUNMING_SATELLITE_MAP",
            "S2_DUAL_SATELLITE_ROUTE",
            "N1_PRESS_FRONT_PAGE",
            "N2_COURT_VERDICT_LEDGER",
            "N3_PRISON_NETWORK_DOSSIER",
            "N4_PATENT_BLUEPRINT_EXPOSE",
            "N5_CHRONOLOGY_TIMELINE_STRIP",
            "N6_EVIDENCE_COLLAGE_BOARD",
            "#M1_sat_rooftop_z16",
            "#M2_sat_corridor_z6_z9",
            "#M3_hukou_boundary_river",
            "#M4_crime_coords_distribution",
            "#M5_25d_tilted_slab",
            "#M6_split_dual_sat",
            "#M7_night_infrared_curfew",
            "#M8_topographic_elevation_corridor",
            "#D1_fingerprint_comparator",
            "#D2_duality_dossier",
            "#D3_three_clues_dossier",
            "#D4_ydna_lightbox",
            "#D5_clipboard_interrogation",
            "#D6_wanted_warrant_sketch",
            "#D7_ballistics_toolmark",
            "#D8_autopsy_pathology_report",
            "#D9_microscope_minutiae",
            "#D10_cold_case_vault",
            "#P1_timeline_silence",
            "#P2_newspaper_curfew",
            "#P3_90s_tv_broadcast",
            "#P4_teletype_dispatch",
            "#P5_radio_frequency_log",
            "#P6_court_verdict",
            "cinema_full",
            "forensic_case_board_red_string",
            "document_scanner_telemetry",
            "noir_chapter_transition",
            "biometric_dna_hud",
            "forensic_map_route_board",
        ],
        "subtitle_style": {
            "font_family": "Pretendard",
            "font_size": 44,
            "font_size_px": 44,
            "color": "#FFFFFF",
            "base_color": "#FFFFFF",
            "highlight_color": "#EAB308",
            "stroke_color": "#000000",
            "stroke_width": 18,
            "position": "bottom_center",
        },
        "color_grade": {
            "tone_preset": "cold_forensic_noir",
            "lut_name": "noir_desaturated",
            "vignette_opacity": 0.88,
            "film_grain": 0.12,
        },
        "audio_rules": {
            "bgm_volume_db": -20.0,
            "ducking_db": -14.0,
            "music_ducking_db": -14.0,
            "tension_drone": True,
            "tension_drone_under_interrogation": True,
            "heartbeat_riser": True,
            "sfx_hit_on_chapter": True,
        },
        "editorial_rules": [
            "All crime depictions must strictly follow After-the-Storm forensic framing (no graphic gore)",
            "Flexible Lore/DNA Principle: Never repeat 1-2 Vox templates lazily; dynamically route across 10+ Newspaper/Dossier/GIS archetypes (N1..N6, S1..S4) based on beat semantics",
            "Deploy Full-Screen 1920x1080 Map Flight (S3_FULLSCREEN_GIS_FLIGHT / S4_FULLSCREEN_SATELLITE_RECON) for cross-province dispatch, prison transfers, and macro territory sweeps; use Split Map Cards (S1/S2) for side-by-side document comparisons",
            "Senior-Friendly 45-70yo Viewability: 1 calm episode intro only (zero strobe/flashing), clean rectangular photo frames (never tear across faces), warm cream paper (#EDE5D2)",
            "Dynamic 28-Track Context-Matched Foley SFX & 5-Mood Chapter BGM via documentary/audio_library_manager.py (with Wikimedia Commons CC0 auto-fetcher for new sounds)",
        ],
    },
    "archival_historical": {
        "preset_id": "archival_historical",
        "name": "Archival Historical Vault",
        "version": 1,
        "pacing": PacingDict({
            "target_beat_duration_sec": 5.0,
            "typical_pacing_sec": 5.0,
            "shot_range_sec": [3.5, 7.5],
            "average_beat_duration_sec": 5.0,
            "max_routine_shot_sec": 8.5,
            "pacing_curve": "measured_documentary_historical",
            "pacing_wpm": 135.0,
        }),
        "visual_mix": {
            "footage": 0.65,
            "ai": 0.20,
            "motion": 0.15,
            "footage_ratio": 0.65,
            "ai_visual_ratio": 0.20,
            "motion_overlay_ratio": 0.15,
            "preferred_routing": "evidence_footage",
        },
        "editing_archetypes": [
            "archival_document_scanner",
            "timeline_hud",
            "cinematic_chapter_card",
            "declassified_stamp_overlay",
            "film_finish_grain",
        ],
        "subtitle_style": {
            "font_family": "Inter",
            "font_size": 40,
            "font_size_px": 40,
            "color": "#F8FAFC",
            "base_color": "#F8FAFC",
            "highlight_color": "#F59E0B",
            "stroke_color": "#000000",
            "stroke_width": 14,
            "position": "bottom_center",
        },
        "color_grade": {
            "tone_preset": "archival_warm_vintage",
            "lut_name": "kodachrome_warm",
            "vignette_opacity": 0.65,
            "sepia_warmth": 0.15,
        },
        "audio_rules": {
            "bgm_volume_db": -18.0,
            "ducking_db": -10.0,
            "music_ducking_db": -10.0,
            "typewriter_sfx": True,
            "film_reel_hum": True,
            "sfx_hit_on_chapter": True,
            "tension_drone_under_interrogation": False,
        },
        "editorial_rules": [
            "Sourced archival clips must have transformative historical annotations",
            "Declassified government files must display stamp animations",
            "Typewriter audio accompanies textual evidence",
        ],
    },
    "custom": {
        "preset_id": "custom",
        "name": "Custom Profile Recipe",
        "version": 1,
        "pacing": PacingDict({
            "target_beat_duration_sec": 5.0,
            "typical_pacing_sec": 5.0,
            "shot_range_sec": [3.0, 8.0],
            "average_beat_duration_sec": 5.0,
            "max_routine_shot_sec": 8.0,
            "pacing_curve": "standard_documentary",
            "pacing_wpm": 135.0,
        }),
        "visual_mix": {
            "footage": 0.33,
            "ai": 0.33,
            "motion": 0.34,
            "footage_ratio": 0.33,
            "ai_visual_ratio": 0.33,
            "motion_overlay_ratio": 0.34,
            "preferred_routing": "hybrid",
        },
        "editing_archetypes": [
            "custom_overlay",
            "chapter_title_card",
        ],
        "subtitle_style": {
            "font_family": "Inter",
            "font_size": 42,
            "font_size_px": 42,
            "color": "#FFFFFF",
            "base_color": "#FFFFFF",
            "highlight_color": "#38BDF8",
            "stroke_color": "#000000",
            "stroke_width": 16,
            "position": "bottom_center",
        },
        "color_grade": {
            "tone_preset": "neutral",
            "lut_name": "clean_natural",
            "vignette_opacity": 0.70,
        },
        "audio_rules": {
            "bgm_volume_db": -20.0,
            "ducking_db": -12.0,
            "music_ducking_db": -12.0,
            "sfx_hit_on_chapter": True,
            "tension_drone_under_interrogation": False,
        },
        "editorial_rules": [
            "Maintain voice-visual alignment within 0.3s tolerance",
            "Anti-repetitive hold limits apply to all beats",
        ],
    },
}


class EditingDnaService:
    def __init__(
        self,
        profiles_file: Path | str | None = None,
        jobs_dir: Path | str | None = None,
        workspaces_dir: Path | str | None = None,
    ):
        self.profiles_file = Path(profiles_file) if profiles_file else CHANNEL_PROFILES_FILE
        self.jobs_dir = Path(jobs_dir) if jobs_dir else JOBS_DIR
        self.workspaces_dir = Path(workspaces_dir) if workspaces_dir else WORKSPACES_DIR

    def get_presets(self) -> dict[str, dict[str, Any]]:
        return copy.deepcopy(BUILTIN_EDITING_PRESETS)

    def extract_editing_dna_from_job(self, job_id: str) -> dict[str, Any]:
        """
        Extract empirical editing parameters (pacing, visual mix, archetypes,
        typography, and color grade) from workspace and job manifest files.
        Falls back safely to defaults if files are missing or empty.
        """
        ws_dir = self.workspaces_dir / job_id
        job_dir = self.jobs_dir / job_id

        # Read workspace files if available
        visual_manifest = self._read_json(ws_dir / "visual_manifest.json") or self._read_json(job_dir / "visual_manifest.json")
        voice_manifest = self._read_json(ws_dir / "voice_manifest.json") or self._read_json(job_dir / "voice_manifest.json")
        creative_brief = self._read_json(ws_dir / "creative_brief.json") or self._read_json(job_dir / "creative_brief.json")
        edit_checkpoint = self._read_json(ws_dir / "edit_checkpoint.json") or self._read_json(job_dir / "edit_checkpoint.json")
        job_data = self._read_json(job_dir / "job.json") or {}

        # Fallback to custom preset if empty workspace checkpoint
        if not visual_manifest and not voice_manifest and not creative_brief:
            fallback = copy.deepcopy(BUILTIN_EDITING_PRESETS["custom"])
            fallback["version"] = 1
            return fallback

        # 1. Compute pacing statistics
        raw_durations: list[float] = []
        beats: list[dict[str, Any]] = []

        if isinstance(visual_manifest, dict):
            beats = visual_manifest.get("beats") or []
            if not beats and "scenes" in visual_manifest:
                for scene in visual_manifest.get("scenes", []):
                    if isinstance(scene, dict):
                        beats.extend(scene.get("beats", []))

        if not beats and isinstance(voice_manifest, dict):
            beats = voice_manifest.get("beats") or []

        for b in beats:
            if isinstance(b, dict):
                dur = b.get("duration_sec") or b.get("target_duration_sec")
                if dur is not None:
                    try:
                        d = float(dur)
                        if d > 0:
                            raw_durations.append(d)
                    except (ValueError, TypeError):
                        pass

        # Safely clamp extreme values into [2.0, 15.0]
        if raw_durations:
            clamped = [min(max(d, 2.0), 15.0) for d in raw_durations]
            avg_pacing = round(statistics.mean(clamped), 2)
            min_shot = round(min(clamped), 1)
            max_shot = round(max(clamped), 1)
        else:
            avg_pacing = 5.0
            min_shot, max_shot = 3.5, 7.5

        # 2. Compute visual mix ratios
        footage_count = 0
        ai_count = 0
        motion_count = 0

        for b in beats:
            if not isinstance(b, dict):
                continue
            v_type = str(b.get("visual_type") or "").lower()
            v_route = str(b.get("visual_route") or "").lower()
            if any(k in v_type for k in ("sourced", "footage", "clip", "archival")) or v_route == "footage":
                footage_count += 1
            elif any(k in v_type for k in ("ai", "illustration", "still", "reconstruction")) or v_route == "ai_visual":
                ai_count += 1
            elif any(k in v_type for k in ("motion", "hud", "map", "overlay", "telemetry")):
                motion_count += 1
            else:
                footage_count += 1

        total_visual_beats = max(len(beats), 1)
        footage_ratio = round(footage_count / total_visual_beats, 2)
        ai_ratio = round(ai_count / total_visual_beats, 2)
        motion_ratio = round(max(0.0, 1.0 - footage_ratio - ai_ratio), 2)

        # 3. Detect active Remotion archetypes
        archetypes: list[str] = []
        if isinstance(creative_brief, dict):
            brief_archetypes = creative_brief.get("editing_archetypes")
            if isinstance(brief_archetypes, list) and brief_archetypes:
                archetypes.extend(str(a) for a in brief_archetypes if a)

        # Also collect active scene_archetypes stamped on beats (e.g. True Crime Vox archetypes)
        beat_archetypes = [
            str(b.get("scene_archetype")) for b in beats
            if isinstance(b, dict) and b.get("scene_archetype")
        ]
        if beat_archetypes:
            for arch in dict.fromkeys(beat_archetypes):
                if arch not in archetypes:
                    archetypes.append(arch)

        if not archetypes:
            archetypes = [
                "2.5d_satellite_map",
                "technical_hud_telemetry",
                "blueprint_vs_reality_split",
                "chapter_hero_banner",
            ]

        # 4. Subtitle typography & Color grading
        subtitle_style = {
            "font_family": "Pretendard",
            "font_size": 44,
            "font_size_px": 44,
            "color": "#FFFFFF",
            "base_color": "#FFFFFF",
            "highlight_color": "#38BDF8" if ai_ratio < 0.6 else "#EAB308",
            "stroke_color": "#000000",
            "stroke_width": 16,
            "position": "bottom_center",
        }

        color_grade = {
            "tone_preset": "technical_cool_cyan" if footage_ratio >= 0.3 else "cold_forensic_noir",
            "lut_name": "clean_broadcast_cool" if footage_ratio >= 0.3 else "noir_desaturated",
            "vignette_opacity": 0.78,
        }

        # Select closest preset ID
        if ai_ratio >= 0.65:
            preset_id = "forensic_noir"
            name = "Forensic Noir Full-AI True Crime"
        elif footage_ratio >= 0.55:
            preset_id = "archival_historical"
            name = "Archival Historical Vault"
        elif motion_ratio >= 0.20 or "2.5d" in " ".join(archetypes).lower():
            preset_id = "2.5d_technical"
            name = "2.5D Technical & Infrastructure Investigation"
        else:
            preset_id = "custom"
            name = f"Custom Recipe (Job {job_id[:8]})"

        pacing_data = PacingDict({
            "target_beat_duration_sec": avg_pacing,
            "typical_pacing_sec": avg_pacing,
            "shot_range_sec": [min_shot, max_shot],
            "average_beat_duration_sec": avg_pacing,
            "max_routine_shot_sec": min(max_shot + 2.0, 15.0),
            "pacing_curve": "accelerating_towards_act_climax",
            "pacing_wpm": 138.0,
        })

        return {
            "preset_id": preset_id,
            "name": name,
            "version": 1,
            "pacing": pacing_data,
            "visual_mix": {
                "footage": footage_ratio,
                "ai": ai_ratio,
                "motion": motion_ratio,
                "footage_ratio": footage_ratio,
                "ai_visual_ratio": ai_ratio,
                "motion_overlay_ratio": motion_ratio,
                "preferred_routing": "hybrid" if (footage_ratio > 0 and ai_ratio > 0) else ("full_ai" if ai_ratio > 0.5 else "evidence_footage"),
            },
            "editing_archetypes": archetypes,
            "subtitle_style": subtitle_style,
            "color_grade": color_grade,
            "audio_rules": {
                "bgm_volume_db": -22.0,
                "ducking_db": -12.0,
                "music_ducking_db": -12.0,
                "sfx_chapter_hit": True,
                "sfx_hit_on_chapter": True,
                "telemetry_beeps": True,
                "tension_drone_under_interrogation": False,
            },
            "editorial_rules": [
                "Always ground technical claims with KeyMetricCallout telemetry cards",
                "Maintain voice-visual alignment within 0.3s tolerance",
            ],
        }

    def lock_job_edit_dna_to_channel(self, job_id: str, notes: str = "") -> dict[str, Any]:
        """
        Extract editing DNA from project and lock it into the parent Channel Profile.
        Increments the editing_dna version, appends the previous version to editing_dna_history,
        and saves atomically so all future projects inherit this exact recipe.
        """
        # 1. Resolve job
        job_file = self.jobs_dir / job_id / "job.json"
        if not job_file.exists():
            raise KeyError(f"Job {job_id} not found")

        job_data = self._read_json(job_file) or {}
        channel_profile_id = job_data.get("channel_profile_id")
        if not channel_profile_id:
            raise ValueError(f"Job {job_id} has no assigned channel profile to lock DNA into")

        # 2. Extract DNA from job
        extracted_dna = self.extract_editing_dna_from_job(job_id)

        # 3. Read channel profiles atomically
        with _file_lock:
            profiles_raw = self._read_json(self.profiles_file) or {}
            profiles_list = profiles_raw.get("profiles", []) if isinstance(profiles_raw, dict) else []

            profile_idx = next(
                (i for i, p in enumerate(profiles_list) if str(p.get("id")) == str(channel_profile_id) or str(p.get("channel_profile_id")) == str(channel_profile_id)),
                None
            )
            if profile_idx is None:
                raise KeyError(f"Channel profile {channel_profile_id} not found")

            profile = profiles_list[profile_idx]

            # 4. Versioning & History
            prev_dna = profile.get("editing_dna") or {}
            prev_version = int(prev_dna.get("version", 1)) if isinstance(prev_dna, dict) else 1
            new_version = prev_version + 1

            # Prepare history record
            history = list(profile.get("editing_dna_history") or [])
            if prev_dna:
                history_entry = copy.deepcopy(prev_dna)
                # Ensure sequential version records for auditability
                if "version" not in history_entry:
                    history_entry["version"] = prev_version
                history.append(history_entry)

            # Assemble updated DNA
            extracted_dna["version"] = new_version
            extracted_dna["locked_from_job_id"] = job_id
            extracted_dna["locked_at"] = _now()
            if notes:
                extracted_dna["notes"] = notes

            profile["editing_dna"] = extracted_dna
            profile["editing_dna_history"] = history
            profile["updated_at"] = _now()

            # Write back channel profiles
            self._write_json(self.profiles_file, {"profiles": profiles_list})

            # 5. Also update job's local record & snapshot
            job_data["editing_dna"] = copy.deepcopy(extracted_dna)
            snapshot = job_data.setdefault("channel_profile_snapshot", {})
            snapshot["editing_dna"] = copy.deepcopy(extracted_dna)
            self._write_json(job_file, job_data)

        return {
            "status": "success",
            "message": f"Edit style successfully locked to channel profile '{channel_profile_id}' as version {new_version}",
            "profile_id": channel_profile_id,
            "channel_profile_id": channel_profile_id,
            "version": new_version,
            "locked_job_id": job_id,
            "editing_dna": extracted_dna,
            "history_count": len(history),
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
