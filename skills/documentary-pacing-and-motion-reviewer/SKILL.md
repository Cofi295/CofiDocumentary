---
name: documentary-pacing-and-motion-reviewer
description: "Documentary Archival Pacing, Breath-Driven Cutting & Multi-Agent Video Motion Reviewer Skill (integrated from calesthio/OpenMontage, poseljacob/agentic-video-editor & appariciojunior/video-editor-skills)."
---

# Documentary Pacing & Video Motion Reviewer (`documentary-pacing-and-motion-reviewer`)

> **Reference Repositories**:
> - `references/github-video-skills/OpenMontage` (`calesthio/OpenMontage`)
> - `references/github-video-skills/agentic-video-editor` (`poseljacob/agentic-video-editor`)
> - `references/github-video-skills/video-editor-skills` (`appariciojunior/video-editor-skills`)
> - `B:/ALL_TOOLS/CofiDocumentary/documentary/critic_loops.py`

## 1. 100% Eye-Verified Archival Footage & Zero Auto-Cut / Zero Auto-Splice Law (`@footage` -> `@edit`)
1. **Mandatory Visual Eye Check & Clean Logo/Running-Text Crop (`read_file` / `vision_inspect_frames`)**:
   - The AI Agent MUST inspect every video/image attached to a spoken sentence with its own eyes (`STORYBOARD_<id>.jpg`, `GRID_<id>.jpg`, and post-crop `15%-50%-85%` contact sheets `*_3frames.jpg`).
   - Calibrate `crop=W:H:X:Y` on the `100px` coordinate grid to guarantee **100% removal of third-party logos/watermarks/QR codes** (`logo bên khác`) and **100% removal of third-party running tickers, chyrons, and burned-in foreign subtitles** (`chữ chạy bên khác`), while stripping out program intros/outros and studio hosts/anchors.
2. **100% Eye-Verified Match With Spoken Sentence Meaning**:
   - The AI Agent MUST verify by eye that the actual image or video footage attached to a beat matches **100% of the content the spoken sentence is talking about** (`narration_text`).
   - Record `eye_verified: true` and `observed_content` describing the actual visual content inspected by eye (`voice_to_visual_semantic_mismatch = 0`). Whenever authentic footage matching 100% of the spoken sentence does not exist, route that beat to **Priority #2 VOX illustration (`@vox`)**, and use **Priority #3 AI Image (`@ai_visual`)** only as the final fallback.
3. **Strict Ban on Automatic Cutting and Automatic Splicing Code (`0%` Auto-Cut / `0%` Auto-Splice)**:
   - **STRICTLY FORBIDDEN**: Never use code or scripts to automatically cut or automatically splice footage (`--auto`, `auto_fetch_missing_beats`, `blind_auto_offset`, `start + i * 28s`, `duration * 0.32`, or automatic cross-beat holding `FT-*-hold-*`), which causes the spoken meaning and the visual image to drift out of sync and frustrates the viewer.

## 2. Transcript-Driven Breath Cutting & Acoustic Mixing (`@edit` & `@sfx`)
1. **Organic Caesura Pacing (Walter Murch Rule of Six)**:
   - Rapid investigative sequences: `0.28s - 0.42s` pause.
   - Standard clause transitions: `0.55s - 0.80s` pause.
   - Paradox questions (`?`), key evidence reveals, and `FramelessCinemaTextBeat`: `1.12s - 1.68s` organic hold (`0%` uniform clamping to `1.40s` or `1.49s`).
   - Act curtain transitions (`ACT01 -> ACT02 -> ... -> ACT05`): `1.48s - 2.15s` hold.
2. **SFX Onset-Lag Compensation & Story-Arc BGM**:
   - Compensate for leading silence in `.mp3/.wav` files: `Sequence.from = max(0, beat_start_frame + motion_peak_frame - sfx_onset_lag_frames)`.
   - Divide BGM organically across `8-12` emotional chapters matching narrative turning points (`0%` equal-length `total_frames / N` division), with `2-3` pre-twist dramatic drops to `-41dBFS` room tone (`2.5s - 4.0s`) before the new chapter theme enters.

## 3. Director -> Trim Refiner -> Video Motion Reviewer Loop (`@evidence_qa` & `@qc`)
Modeled on `poseljacob/agentic-video-editor` and enforced in `critic_loops.py`:
1. **Multi-Frame Optical Motion Energy Verification (`15% != 50% != 85%`)**:
   - Inspect rendered frames at `15%`, `50%`, and `85%` of each beat to verify real optical motion energy (`0%` frozen frames or static `setpts` stretches) and verify that `t1 -> t2 -> t3` VOX cutouts progressively accumulate on screen.
2. **Global Cross-Beat Perceptual Uniqueness (`dHash >= 14`)**:
   - Enforce `max_uses = 1` and perceptual hash distance `dHash >= 14` across all beats in the episode (spanning `REAL_FTG`, `VOX`, and `AI_4D`).
3. **Manifest & AST Anti-Copy-Paste & Motion Text 3-Law Gates**:
   - Block any `vox_scene_manifest.json` with consecutive duplicate `motion_intent` (`consecutive_duplicate_vox_motion_intent`) or duplicated `(t1_action, t2_action, t3_action)` choreography (`duplicate_vox_manifest_choreography`).
   - Enforce the **3 Ironclad Motion Text (`FramelessCinemaTextBeat.tsx` / `CinemaTextSpecs.ts`) Laws** via `validate-vox-newsroom-ast.mjs` (Gate 6) and `critic_loops.py`:
     1. **Zero Monoculture (`[FAIL:MOTION_TEXT_MONOCULTURE]` / `[FAIL:CONSECUTIVE_DUPLICATE_MOTION_TEXT_STYLE]`)**: Never repeat 1 `showroomRenderer`, 1 `fontStyle`, or 1 `layoutVariant` throughout the episode; never repeat the same `showroomRenderer` or `(fontStyle, layoutVariant)` on consecutive Motion Text beats.
     2. **Flexible Narrative Drop-Point Placement (`[FAIL:MECHANICAL_PERIODIC_MOTION_TEXT_SPACING]` / `[FAIL:NON_DROP_POINT_MOTION_TEXT]`)**: Attach Motion Text strictly at genuine narrative drop points (`?` paradox questions, turning-point metrics, dual-identity contradictions, or climax arrest/verdict statements) flexibly per video job (`0%` mechanical spacing every 7–11 beats).
     3. **100% Context-Matched Font, Color, Layout & Entry Motion (`[FAIL:MOTION_TEXT_CONTEXT_MISMATCH]`)**: Match `fontStyle`, `accentColor`, `layoutVariant`, and `showroomRenderer` 100% to sentence meaning (never use blood-red `crimson` on victim mourning; never use `editorial_metric_monolith` without a real spoken number).
