"""True Crime Vox & Real Satellite Standalone Scene Renderer.

Renders 1080p frames and frame sequences for all 24 True Crime baseline archetypes
plus the 4 unlocked bespoke voice-clause modes (#V_POPOUT_HIGHLIGHT, #V_CLAUSE_TIMELINE,
#V_FORENSIC_CROSS_SECTION, #V_BLENDER_3D_STAGE) to file or memory.
Supports full voice-duration (`duration_sec = end_sec - start_sec`) and progressive
clause synchronization (`voice_spec`).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Union
from PIL import Image

from .archetypes import (
    ARCHETYPE_RENDERERS,
    W,
    H,
    apply_voice_spec_clause_sync_overlay,
    fit_crop,
    get_fallback_image,
)


class VoxSceneRenderer:
    """Production standalone renderer for True Crime Vox & Satellite visual compositions."""

    def __init__(self, assets_cache_dir: str | Path | None = None):
        self.assets_cache_dir = Path(assets_cache_dir) if assets_cache_dir else None
        if self.assets_cache_dir:
            self.assets_cache_dir.mkdir(parents=True, exist_ok=True)
        self._image_cache: dict[str, Image.Image] = {}

    def _resolve_image(self, input_val: Any, default_label: str = "EVIDENCE") -> Image.Image:
        """Resolves an image input from either PIL Image, file path, or creates a procedural fallback."""
        if isinstance(input_val, Image.Image):
            return input_val.convert("RGB")

        if isinstance(input_val, (str, Path)):
            path_str = str(input_val).strip()
            if path_str in self._image_cache:
                return self._image_cache[path_str].copy()
            if os.path.exists(path_str):
                try:
                    img = Image.open(path_str).convert("RGB")
                    self._image_cache[path_str] = img
                    return img.copy()
                except Exception:
                    pass

        return get_fallback_image(640, 480, default_label)

    def render_frame(
        self,
        archetype_id: str,
        progress: float = 1.0,
        media_inputs: dict[str, Any] | None = None,
        subtitle_text: str = "",
        out_path: str | Path | None = None,
        voice_spec: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Image.Image:
        """Renders one 1920x1080 frame for the specified archetype and voice_spec."""
        arch = str(archetype_id or "").strip()
        renderer_fn = ARCHETYPE_RENDERERS.get(arch)
        if not renderer_fn:
            renderer_fn = ARCHETYPE_RENDERERS["cinema_full"]

        inputs = dict(media_inputs or {})
        effective_voice_spec = voice_spec or inputs.get("voice_spec")

        if arch in {"#V_POPOUT_HIGHLIGHT", "#V_CLAUSE_TIMELINE", "#V_FORENSIC_CROSS_SECTION", "#V_SAT_ZONE_DRAW", "#V_BLENDER_3D_STAGE", "#V_SAT_LOUPE_ZOOM", "#V_DOSSIER_BOARD", "#V_VERDICT_PROCLAMATION"}:
            fa = self._resolve_image(inputs.get("frame_a") or inputs.get("frame_main") or inputs.get("frame_left"), "EVIDENCE A")
            fb = self._resolve_image(inputs.get("frame_b") or inputs.get("frame_right") or inputs.get("frame_a"), "EVIDENCE B")
            canvas = renderer_fn(progress, fa, fb, subtitle_text=subtitle_text, voice_spec=effective_voice_spec)

        elif arch == "#M1":
            frame_store = self._resolve_image(inputs.get("frame_store") or inputs.get("frame_a"), "SCHOOL STORE")
            frame_gao = self._resolve_image(inputs.get("frame_gao") or inputs.get("frame_b"), "SUSPECT GAO")
            canvas = renderer_fn(progress, frame_store, frame_gao, subtitle_text=subtitle_text)

        elif arch in {"#M2", "#M4", "#M5", "#M7", "#D1", "#D2", "#D6", "#P1", "#P2", "#P3"}:
            fa = self._resolve_image(inputs.get("frame_a") or inputs.get("frame_left") or inputs.get("frame_city"), "EVIDENCE A")
            fb = self._resolve_image(inputs.get("frame_b") or inputs.get("frame_right") or inputs.get("frame_alley"), "EVIDENCE B")
            canvas = renderer_fn(progress, fa, fb, subtitle_text=subtitle_text)

        elif arch == "#D3":
            fp = self._resolve_image(inputs.get("frame_fp") or inputs.get("frame_a"), "LATENT FINGERPRINT")
            bio = self._resolve_image(inputs.get("frame_bio") or inputs.get("frame_b"), "BIOLOGICAL DNA")
            foot = self._resolve_image(inputs.get("frame_foot") or inputs.get("frame_c"), "FOOTWEAR TREAD")
            canvas = renderer_fn(progress, fp, bio, foot, subtitle_text=subtitle_text)

        elif arch == "#D4":
            flab = self._resolve_image(inputs.get("frame_lab") or inputs.get("frame_a"), "Y-STR LAB GEL")
            farrest = self._resolve_image(inputs.get("frame_arrest") or inputs.get("frame_b"), "GAO CLAN RECORD")
            canvas = renderer_fn(progress, flab, farrest, subtitle_text=subtitle_text)

        elif arch == "#D9":
            fp1 = self._resolve_image(inputs.get("frame_fp1") or inputs.get("frame_a"), "1988 CRIME SCENE PRINT")
            fp2 = self._resolve_image(inputs.get("frame_fp2") or inputs.get("frame_b"), "2016 SUSPECT INKED PRINT")
            canvas = renderer_fn(progress, fp1, fp2, subtitle_text=subtitle_text)

        elif arch in {"#M3", "#M6", "#M8", "#D5", "#D7", "#D8", "#D10", "#P4", "#P5", "#P6"}:
            fa = self._resolve_image(inputs.get("frame_a") or inputs.get("frame_main") or inputs.get("frame_detective"), "PRIMARY EVIDENCE")
            canvas = renderer_fn(progress, fa, subtitle_text=subtitle_text)

        else:  # cinema_full
            f_cinema = self._resolve_image(inputs.get("frame_img") or inputs.get("frame_a"), "CINEMA ARCHIVE")
            title_lt = kwargs.get("lower_third_title") or inputs.get("lower_third_title", "")
            sub_lt = kwargs.get("lower_third_sub") or inputs.get("lower_third_sub", "")
            canvas = renderer_fn(progress, f_cinema, subtitle_text=subtitle_text, lower_third_title=title_lt, lower_third_sub=sub_lt)

        if effective_voice_spec and arch not in {"cinema_full", "#V_POPOUT_HIGHLIGHT", "#V_CLAUSE_TIMELINE", "#V_FORENSIC_CROSS_SECTION", "#V_SAT_ZONE_DRAW", "#V_BLENDER_3D_STAGE", "#V_SAT_LOUPE_ZOOM", "#V_DOSSIER_BOARD", "#V_VERDICT_PROCLAMATION"}:
            canvas = apply_voice_spec_clause_sync_overlay(canvas, progress, voice_spec=effective_voice_spec, arch_id=arch)

        if out_path:
            p = Path(out_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(p, quality=95)

        return canvas

    def render_sequence(
        self,
        archetype_id: str,
        num_frames: int = 30,
        media_inputs: dict[str, Any] | None = None,
        subtitle_text: str = "",
        out_dir: str | Path | None = None,
        voice_spec: dict[str, Any] | None = None,
    ) -> list[Image.Image]:
        """Renders an animated sequence of frames with ease curve progression."""
        frames: list[Image.Image] = []
        out_path_dir = Path(out_dir) if out_dir else None
        if out_path_dir:
            out_path_dir.mkdir(parents=True, exist_ok=True)

        n = max(1, int(num_frames))
        for i in range(n):
            p = i / float(n - 1) if n > 1 else 1.0
            frame_path = out_path_dir / f"frame_{i:04d}.jpg" if out_path_dir else None
            frame = self.render_frame(
                archetype_id=archetype_id,
                progress=p,
                media_inputs=media_inputs,
                subtitle_text=subtitle_text,
                out_path=frame_path,
                voice_spec=voice_spec,
            )
            frames.append(frame)

        return frames

    def render_motion_mp4(
        self,
        archetype_id: str,
        out_mp4: str | Path,
        duration_sec: float | None = None,
        fps: int = 30,
        media_inputs: dict[str, Any] | None = None,
        subtitle_text: str = "",
        preview_jpg: str | Path | None = None,
        voice_spec: dict[str, Any] | None = None,
    ) -> Path:
        """Renders a true 30fps animated .mp4 video matching the full voice beat duration."""
        import subprocess

        out_path = Path(out_mp4)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        effective_voice_spec = voice_spec or (media_inputs or {}).get("voice_spec")
        resolved_dur = float(duration_sec or (effective_voice_spec or {}).get("duration_sec") or 6.0)
        resolved_dur = max(3.0, min(18.0, resolved_dur))
        steps = max(30, int(round(resolved_dur * fps)))

        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(fps),
            "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "ultrafast", "-crf", "18", str(out_path),
        ]
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert proc.stdin is not None
        preview_step = int(steps * 0.78)
        for s in range(steps):
            seq_p = s / float(max(1, steps - 1))
            frame = self.render_frame(
                archetype_id=archetype_id,
                progress=seq_p,
                media_inputs=media_inputs,
                subtitle_text=subtitle_text,
                voice_spec=effective_voice_spec,
            ).convert("RGB")
            if preview_jpg and s == preview_step:
                Path(preview_jpg).parent.mkdir(parents=True, exist_ok=True)
                frame.save(preview_jpg, quality=92)
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        proc.wait()
        return out_path

    @staticmethod
    def list_archetypes() -> list[str]:
        """Returns all registered archetype IDs."""
        return list(ARCHETYPE_RENDERERS.keys())
