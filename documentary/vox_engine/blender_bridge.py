"""High-End Animated Vox & Real Satellite GIS Bridge for CofiDocumentary.

Connects CofiDocumentary's edit pipeline to `VoxSceneRenderer` with voice-duration matching (`duration_sec = end_sec - start_sec`) and clause synchronization (`voice_spec`).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .composable_scene_graph import (
    LOCKED_VOX_STYLE_DNA,
    build_composable_vox_scene_spec,
)
from .renderer import VoxSceneRenderer
from .semantic_router import VOX_ARCHETYPE_RULES, build_voice_spec_for_beat

BLENDER_3D_SCENE_SPECS: dict[str, dict[str, Any]] = {}

ARCHETYPE_PREVIEW_URLS: dict[str, str] = {
    "#V_POPOUT_HIGHLIGHT": "/static/vox_studio/preview_08_newspaper_panic.jpg",
    "#V_CLAUSE_TIMELINE": "/static/vox_studio/preview_07_six_year_timeline.jpg",
    "#V_FORENSIC_CROSS_SECTION": "/static/vox_studio/preview_05_three_clues_dossier.jpg",
    "#V_SAT_ZONE_DRAW": "/static/vox_studio/preview_09_1998_four_cases_map.jpg",
    "#V_SAT_LOUPE_ZOOM": "/static/vox_studio/preview_02_school_store_map.jpg",
    "#V_DOSSIER_BOARD": "/static/vox_studio/preview_03_duality_collage.jpg",
    "#V_VERDICT_PROCLAMATION": "/static/vox_studio/preview_08_newspaper_panic.jpg",
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


def map_archetype_to_blender_3d_scene(archetype_id: str, beat: dict[str, Any] | None = None) -> dict[str, Any] | None:
    spec = build_composable_vox_scene_spec(beat=beat or {"scene_archetype": archetype_id})
    return spec.get("blender_3d_stage")


class VoxBlenderBridge:
    """Bridges 2D Editorial Vox & Satellite Tactile Dossier compositing into CofiDocumentary."""

    def __init__(self, assets_cache_dir: str | Path | None = None):
        self.renderer = VoxSceneRenderer(assets_cache_dir=assets_cache_dir)

    @staticmethod
    def status() -> dict[str, Any]:
        return {
            "ok": True,
            "engine": "2D Editorial Vox & Real Esri Satellite Motion Engine",
            "archetypes_count": len(VOX_ARCHETYPE_RULES),
        }

    def materialize_job_vox_assets(
        self,
        job: dict[str, Any],
        workspace: str | Path,
        beats: list[dict[str, Any]],
        remotion_dir: str | Path | None = None,
        render_plates: bool = True,
        use_blender_eevee_3d: bool = False,
    ) -> dict[str, Any]:
        """Materializes Voice-Duration-Matched 2D Vox .mp4 clips and plates for a job."""
        ws = Path(workspace).resolve()
        job_id = str(job.get("id") or ws.name).strip()
        vox_renders_dir = ws / "vox_renders"
        vox_renders_dir.mkdir(parents=True, exist_ok=True)

        remotion_pub: Path | None = None
        remotion_job_vox_dir: Path | None = None
        if remotion_dir:
            remotion_pub = Path(remotion_dir) / "public" / "jobs" / job_id
            remotion_pub.mkdir(parents=True, exist_ok=True)
            remotion_job_vox_dir = remotion_pub / "vox_renders"
            remotion_job_vox_dir.mkdir(parents=True, exist_ok=True)

        manifest_beats: list[dict[str, Any]] = []
        rendered_count = 0

        def _find_beat_media(b_id: str, slot_idx: int) -> Path | None:
            if remotion_pub is not None:
                arch_dir = remotion_pub / "archival"
                if arch_dir.is_dir():
                    arch_files = sorted(arch_dir.glob("*.jpg")) + sorted(arch_dir.glob("*.png"))
                    if arch_files:
                        return arch_files[slot_idx % len(arch_files)]
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
            voice_spec = dict(beat.get("voice_spec") or build_voice_spec_for_beat(beat, beat_index=idx))
            voice_spec["beat_id"] = beat_id
            voice_spec["vox_slot_index"] = idx
            composable_spec = build_composable_vox_scene_spec(beat=beat, voice_spec=voice_spec)
            voice_spec["sfx_events"] = composable_spec["sfx_events"]
            voice_spec["semantic"] = composable_spec["semantic"]
            voice_spec["blender_3d_stage"] = composable_spec["blender_3d_stage"]
            beat["vox_sfx_events"] = composable_spec["sfx_events"]
            beat["composable_scene_spec"] = composable_spec
            beat_duration = float(voice_spec.get("duration_sec") or 6.0)
            narration = str(voice_spec.get("narration_text") or "").strip()
            preview_url = ARCHETYPE_PREVIEW_URLS.get(arch, "/static/vox_studio/preview_00_cinema_open.jpg")

            arch_slug = arch.replace("#", "")
            plate_filename = f"vox_{beat_id}_{arch_slug}.jpg"
            motion_filename = f"vox_{beat_id}_{arch_slug}.mp4"
            plate_path = vox_renders_dir / plate_filename
            motion_path = vox_renders_dir / motion_filename
            should_render_vox = bool(beat.get("render_vox_board", True)) and arch != "cinema_full"
            if render_plates and should_render_vox and (not plate_path.exists() or not motion_path.exists()):
                try:
                    media_inputs: dict[str, Any] = {"voice_spec": voice_spec}
                    kf_a = _find_beat_media(beat_id, idx)
                    kf_b = _find_beat_media(beat_id, idx + 1) or kf_a
                    kf_c = _find_beat_media(beat_id, idx + 2) or kf_b or kf_a
                    if kf_a is not None:
                        media_inputs["frame_a"] = str(kf_a)
                        media_inputs["frame_main"] = str(kf_a)
                        media_inputs["frame_left"] = str(kf_a)
                    if kf_b is not None:
                        media_inputs["frame_b"] = str(kf_b)
                        media_inputs["frame_right"] = str(kf_b)
                    if kf_c is not None:
                        media_inputs["frame_c"] = str(kf_c)

                    self.renderer.render_motion_mp4(
                        archetype_id=arch,
                        out_mp4=motion_path,
                        duration_sec=beat_duration,
                        fps=30,
                        media_inputs=media_inputs,
                        subtitle_text="",
                        preview_jpg=plate_path,
                        voice_spec=voice_spec,
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

            rel_plate = (
                (f"vox_renders/{motion_filename}" if motion_path.exists() else (f"vox_renders/{plate_filename}" if plate_path.exists() else None))
                if should_render_vox
                else None
            )
            if rel_plate:
                beat["vox_plate_public_file"] = rel_plate

            beat_entry = {
                "beat_index": idx,
                "beat_id": beat_id,
                "scene_archetype": arch,
                "archetype_label": label,
                "archetype_cluster": cluster,
                "dna_visual_slot": beat.get("dna_visual_slot", "real_footage"),
                "motion_treatment": beat.get("motion_treatment", "optical_camera_drift"),
                "render_vox_board": should_render_vox,
                "duration_sec": beat_duration,
                "clauses": voice_spec.get("clauses", []),
                "clause_windows": voice_spec.get("clause_windows", []),
                "metrics": voice_spec.get("metrics", []),
                "preview_url": preview_url,
                "rendered_plate_file": rel_plate,
                "narration_excerpt": narration[:140],
            }
            manifest_beats.append(beat_entry)

        return {
            "job_id": job_id,
            "enabled": True,
            "engine": "2D Editorial Vox & Real Esri Satellite Motion Engine",
            "status": self.status(),
            "rendered_plates_count": rendered_count,
            "total_beats": len(manifest_beats),
            "beats": manifest_beats,
        }
