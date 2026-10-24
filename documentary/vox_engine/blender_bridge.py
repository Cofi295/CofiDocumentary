"""Vox Satellite & Tactile Dossier 24-Archetype Bridge for CofiDocumentary.

Connects CofiDocumentary's edit pipeline to VoxSceneRenderer (`24 Approved True Crime Archetypes`:
`#M1..#M8` Real Satellite GIS, `#D1..#D10` Tactile Forensic Dossiers & Labs,
`#P1..#P6` Archival Press & CRT Broadcast) rendered via `vox_editorial_artist.py` and `vox_archetype_expansion.py`.
All deprecated raw 3D primitive prototypes are permanently disabled and removed.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from .renderer import VoxSceneRenderer
from .semantic_router import VOX_ARCHETYPE_RULES

BLENDER_STUDIO_DIR = Path(os.getenv("COFI_BLENDER_STUDIO_DIR", r"b:\ALL_TOOLS\CofiBlenderStudio"))
BLENDER_OUTPUTS_DIR = BLENDER_STUDIO_DIR / "outputs"

# Permanently empty: raw 3D primitive prototypes are prohibited by user rule.
BLENDER_3D_SCENE_SPECS: dict[str, dict[str, Any]] = {}

ARCHETYPE_PREVIEW_URLS: dict[str, str] = {
    "#M1": "/static/vox_studio/preview_02_school_store_map.jpg",
    "#M2": "/static/vox_studio/preview_04_gansu_baiyin_gis.jpg",
    "#M3": "/static/vox_studio/preview_06_hukou_blindspot_gis.jpg",
    "#M4": "/static/vox_studio/preview_09_1998_four_cases_map.jpg",
    "#M5": "/static/vox_studio/exp_m5_25d_tilted_satellite.jpg",
    "#M6": "/static/vox_studio/exp_m6_split_dual_satellite.jpg",
    "#M7": "/static/vox_studio/exp_m7_night_ops_satellite.jpg",
    "#M8": "/static/vox_studio/preview_08_1998_four_cases_map.jpg",
    "#D1": "/static/vox_studio/preview_01_fingerprint_paradox.jpg",
    "#D2": "/static/vox_studio/preview_03_duality_collage.jpg",
    "#D3": "/static/vox_studio/preview_05_three_clues_dossier.jpg",
    "#D4": "/static/vox_studio/exp_d4_ydna_lightbox.jpg",
    "#D5": "/static/vox_studio/exp_d5_clipboard_interrogation.jpg",
    "#D6": "/static/vox_studio/exp_d6_wanted_warrant_sketch.jpg",
    "#D7": "/static/vox_studio/preview_05_three_clues_dossier.jpg",
    "#D8": "/static/vox_studio/preview_03_duality_collage.jpg",
    "#D9": "/static/vox_studio/exp_d9_microscope_minutiae.jpg",
    "#D10": "/static/vox_studio/preview_01_fingerprint_paradox.jpg",
    "#P1": "/static/vox_studio/preview_07_six_year_timeline.jpg",
    "#P2": "/static/vox_studio/preview_08_newspaper_panic.jpg",
    "#P3": "/static/vox_studio/exp_p3_90s_tv_broadcast.jpg",
    "#P4": "/static/vox_studio/preview_07_six_year_timeline.jpg",
    "#P5": "/static/vox_studio/preview_08_newspaper_panic.jpg",
    "#P6": "/static/vox_studio/exp_p3_90s_tv_broadcast.jpg",
    "cinema_full": "/static/vox_studio/preview_00_cinema_open.jpg",
}


def map_archetype_to_blender_3d_scene(archetype_id: str) -> dict[str, Any] | None:
    """Deprecated raw 3D primitive scenes — all 24 Vox archetypes use the approved Vox editorial & satellite engine."""
    return None


class VoxBlenderBridge:
    """Bridges 24-Archetype Vox Satellite & Tactile Dossier compositing into CofiDocumentary."""

    def __init__(self, assets_cache_dir: str | Path | None = None):
        self.renderer = VoxSceneRenderer(assets_cache_dir=assets_cache_dir)

    @staticmethod
    def status() -> dict[str, Any]:
        master_5min = BLENDER_OUTPUTS_DIR / "vox_5min_studio_master.mp4"
        return {
            "ok": True,
            "master_5min_ready": master_5min.exists(),
            "master_5min_url": "/static/vox_studio/vox_5min_studio_master.mp4",
            "archetypes_count": len(VOX_ARCHETYPE_RULES),
            "blender_3d_scenes": [],
        }

    def render_blender_3d_scene(
        self,
        scene_id: str,
        out_mp4: str | Path,
        width: int = 1920,
        height: int = 1080,
        frames: int = 180,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Deprecated: Raw 3D primitive scenes are disabled. Use VoxSceneRenderer 30fps sequence rendering."""
        raise RuntimeError("Deprecated raw 3D primitive scenes are disabled by rule. Use the 24 Approved Vox Archetypes.")

    def materialize_job_vox_assets(
        self,
        job: dict[str, Any],
        workspace: str | Path,
        beats: list[dict[str, Any]],
        remotion_dir: str | Path | None = None,
        render_plates: bool = True,
    ) -> dict[str, Any]:
        """Materializes Vox 24-Archetype plates and Blender 3D scene references for a job."""
        ws = Path(workspace).resolve()
        job_id = str(job.get("id") or ws.name).strip()
        vox_renders_dir = ws / "vox_renders"
        vox_renders_dir.mkdir(parents=True, exist_ok=True)

        remotion_pub: Path | None = None
        remotion_job_vox_dir: Path | None = None
        remotion_footage_dir: Path | None = None
        if remotion_dir:
            remotion_pub = Path(remotion_dir) / "public" / "jobs" / job_id
            remotion_pub.mkdir(parents=True, exist_ok=True)
            remotion_job_vox_dir = remotion_pub / "vox_renders"
            remotion_job_vox_dir.mkdir(parents=True, exist_ok=True)
            remotion_footage_dir = remotion_pub / "footage"
            remotion_footage_dir.mkdir(parents=True, exist_ok=True)

        manifest_beats: list[dict[str, Any]] = []
        rendered_count = 0

        def _find_beat_keyframe(b_id: str) -> Path | None:
            if remotion_pub is not None:
                cand = remotion_pub / f"{b_id}_ai_keyframe.jpg"
                if cand.exists():
                    return cand
            cand_ws = ws / "media" / f"{b_id}_ai_keyframe.jpg"
            if cand_ws.exists():
                return cand_ws
            return None

        for idx, beat in enumerate(beats):
            beat_id = str(beat.get("beat_id") or beat.get("id") or f"B{idx + 1:03d}").strip()
            arch = str(beat.get("scene_archetype") or "cinema_full").strip()
            label = str(beat.get("archetype_label") or arch).strip()
            cluster = str(beat.get("archetype_cluster") or "cinema").strip()
            narration = str(
                beat.get("narration_text")
                or beat.get("narration")
                or beat.get("voice_text")
                or beat.get("text")
                or beat.get("script_text")
                or ""
            ).strip()
            preview_url = ARCHETYPE_PREVIEW_URLS.get(arch, "/static/vox_studio/preview_00_cinema_open.jpg")
            blender_spec = map_archetype_to_blender_3d_scene(arch)

            plate_filename = f"vox_{beat_id}_{arch.replace('#', '')}.jpg"
            motion_filename = f"vox_{beat_id}_{arch.replace('#', '')}.mp4"
            plate_path = vox_renders_dir / plate_filename
            motion_path = vox_renders_dir / motion_filename
            if render_plates and arch != "cinema_full" and (not plate_path.exists() or not motion_path.exists()):
                try:
                    kf_a = _find_beat_keyframe(beat_id)
                    next_id = str(beats[min(idx + 1, len(beats) - 1)].get("beat_id") or "").strip()
                    kf_b = _find_beat_keyframe(next_id) or kf_a
                    media_inputs: dict[str, Any] = {}
                    if kf_a is not None:
                        media_inputs["frame_a"] = str(kf_a)
                        media_inputs["frame_main"] = str(kf_a)
                        media_inputs["frame_left"] = str(kf_a)
                    if kf_b is not None:
                        media_inputs["frame_b"] = str(kf_b)
                        media_inputs["frame_right"] = str(kf_b)
                    self.renderer.render_motion_mp4(
                        archetype_id=arch,
                        out_mp4=motion_path,
                        duration_sec=6.0,
                        fps=30,
                        media_inputs=media_inputs,
                        subtitle_text="",
                        preview_jpg=plate_path,
                    )
                    rendered_count += 1
                except Exception:
                    pass

            if remotion_job_vox_dir is not None:
                for src_f, dst_name in ((plate_path, plate_filename), (motion_path, motion_filename)):
                    if src_f.exists():
                        dst_f = remotion_job_vox_dir / dst_name
                        if not dst_f.exists():
                            try:
                                shutil.copy2(src_f, dst_f)
                            except Exception:
                                pass

            rel_plate = f"vox_renders/{motion_filename}" if motion_path.exists() else (f"vox_renders/{plate_filename}" if plate_path.exists() else None)
            rel_blender = f"footage/{blender_spec['cached_mp4']}" if blender_spec else None
            if rel_plate:
                beat["vox_plate_public_file"] = rel_plate
            if rel_blender:
                beat["blender_3d_public_file"] = rel_blender

            beat_entry = {
                "beat_index": idx,
                "beat_id": beat_id,
                "scene_archetype": arch,
                "archetype_label": label,
                "archetype_cluster": cluster,
                "preview_url": preview_url,
                "rendered_plate_file": rel_plate,
                "blender_3d_scene": blender_spec["id"] if blender_spec else None,
                "blender_3d_title": blender_spec["title"] if blender_spec else None,
                "blender_3d_public_file": rel_blender,
                "blender_3d_video_url": blender_spec["video_url"] if blender_spec else None,
                "narration_excerpt": narration[:140],
            }
            manifest_beats.append(beat_entry)

        return {
            "job_id": job_id,
            "enabled": True,
            "engine": "Vox & Real Satellite 24-Archetype + Blender 4.2 EEVEE",
            "blender_status": self.status(),
            "rendered_plates_count": rendered_count,
            "total_beats": len(manifest_beats),
            "beats": manifest_beats,
        }
