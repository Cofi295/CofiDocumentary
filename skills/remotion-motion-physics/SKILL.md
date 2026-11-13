---
name: remotion-motion-physics
description: "Remotion Deterministic Spring Physics, 12fps/30fps Staggered Choreography & High-Speed GPU Render Skill (integrated from remotion-dev/skills & haidrrrry/claude-remotion-skill)."
---

# Remotion Motion Physics & High-Speed GPU Architecture (`remotion-motion-physics`)

> **Reference Repositories**:
> - `references/github-video-skills/remotion-dev-skills` (`remotion-dev/skills`)
> - `references/github-video-skills/claude-remotion-skill` (`haidrrrry/claude-remotion-skill`)
> - `B:/ALL_TOOLS/CofiRemotion/src/vox-studio/vox-editorial-desk/index.tsx`

## 1. Deterministic Frame-Driven Physics (`0%` CSS Keyframe Flicker)
All motion in `CofiRemotion` must be a pure, deterministic function of `useCurrentFrame()` and `useVideoConfig()`:
1. **Dual-Framerate Tactile Realism (`30fps` Camera/Video vs `12fps` Paper/Ink)**:
   - World camera pan/zoom (`<World cam={camAt(...)}>`) and embedded `<OffthreadVideo>` play at smooth `30fps`.
   - Paper cutouts, torn clippings, ink strokes, and rubber stamps quantize time to **`12fps` (`q12(f) = Math.floor(f / 2.5) * 2.5`)** via `p12(f, at, dur)` and `voxCutoutSlap12(f, at, dur, opts)`.
2. **Anticipation -> Overshoot -> Settle Curve**:
   - Paper cutouts never slide linearly. `voxCutoutSlap12` enters from an off-axis vector (`fromX`, `fromY`, `fromRot`, `fromScale: 1.22`), overshoots slightly at `p = 0.72` (`scale = 0.985`), and locks flat onto the tabletop at `p = 1.0`.
   - Rubber stamps (`voxStampSlam12`) drop from `scale = 2.05`, compress at impact (`scale = 0.94`), and settle to `1.0`.
3. **Staggered Clause Choreography (`t0 -> t1 -> t2 -> t3`)**:
   - Never reveal all props at `f = 0`. Stagger each layer by `8-16` frames (`0.25s-0.55s`) synchronized to the spoken clauses (`clauses[0..2]`) so the viewer's eye follows one clear visual action at a time.

## 2. High-Speed GPU Render Rules (`0%` Chromium Compositor Bottlenecks)
To guarantee fast render speeds (~40-45 fps, ~3.5 minutes per 5-minute segment):
1. **Forbidden Runtime Filters**:
   - **NEVER** animate CSS `filter: blur(...)` or runtime SVG `<feTurbulence>` / `<feDisplacementMap>` per frame on full-screen containers or moving cutouts (`voxCutoutSlap12` returns `filter: 'none'`).
   - Use pre-baked RGBA `.png` textures and static drop shadows (`boxShadow` or pre-rendered alpha shadows) combined with pure GPU `transform: translate3d(...) rotate(...) scale(...)`.
2. **Hardware-Decoded Video (`<OffthreadVideo>`)**:
   - Always render archival video clips and embedded VOX video cutouts through `<OffthreadVideo>` (`StudioSmoothVideo`) so C++/FFmpeg decodes frames directly without HTML5 `<video>` seek stalls.
3. **Render CLI Concurrency & NVENC**:
   - Use `concurrency=6` and `--gl=angle` alongside `h264_nvenc` hardware encoding in `edit.py`.
