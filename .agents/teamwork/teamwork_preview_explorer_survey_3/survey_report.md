# Comprehensive Technical Survey Report: Production Pipeline, Remotion Recipes, Edit Style Memory, Audio-Visual Sync, YouTube Guardrails, Channel-DNA Pre-Flight & Self-Learning Post-Mortem Engine

**Agent**: `teamwork_preview_explorer_survey_3`  
**Date**: 2026-10-18  
**Repository**: `B:\ALL_TOOLS\CofiDocumentary` & `B:\ALL_TOOLS\CofiRemotion`  
**Mission**: Deep investigation of R3, R4, R5, AC3, and AC4 requirements to establish the exact technical architecture, data schemas, endpoints, and code changes required.

---

## 1. Executive Summary

CofiDocumentary is a high-throughput automated documentary production studio producing 15-30+ minute investigative, engineering, and forensic documentaries with Remotion and CofiVoice. While the core rendering (`documentary/remotion.py`), editing coordination (`documentary/edit.py`), TTS synthesis (`documentary/voice.py`), and thumbnail generation (`documentary/thumbnail_studio.py`) exist, the system currently lacks:
1. A structured, versioned **`editing_dna`** schema within `ChannelProfileRequest` and `ProductionRecipe`.
2. The **"Lock Approved Edit Style to Channel"** workflow (`POST /api/jobs/{job_id}/lock-edit-dna`) that extracts empirical editing parameters from completed projects into parent channel profiles.
3. Automated **Audio-Visual Voice & SRT sync validation and repair** (preventing drift, holds > 8-10s, and missing visuals).
4. A dedicated **YouTube Policy & Green Monetization Scorecard** (`GET /api/jobs/{job_id}/sync-compliance`).
5. A **Channel-DNA Pre-Flight Check** for Topics, Titles, Thumbnails, and SEO backed by real YouTube channel history.
6. A **Continuous Self-Learning Post-Mortem Engine** (`/api/radar/channel-profiles/{id}/self-learning`) that classifies channel outliers vs underperformers, diagnoses failure causes, and injects upgrade rules into subsequent productions.

This survey establishes the complete blueprint, exact file citations, schemas, and implementation pathways to achieve 100% compliance with R3, R4, R5, AC3, and AC4.

---

## 2. Requirements R3 & AC3: Remotion Recipes, Edit Style Memory, Sync & Policy Guardrails

### 2.1 Editing Style DNA & Remotion Recipe Schemas & Built-in Presets

#### Current State Analysis
- In `app.py` (lines 80-142), `ChannelProfileRequest` contains `editorial_dna` (lines 104-118: `narrative_angle`, `writing_style`, `hook_archetype`, `editing_archetypes`, `opening_hook`, `forbidden_topics`, `allowed_topics`). However, it has **no structured `editing_dna` object**.
- In `documentary/quality.py` (lines 53-85), `normalize_production_recipe` defines `ProductionRecipe` with `pacing_wpm`, `shot_duration_range_sec`, `visual_density_score`, `max_consecutive_ai_shots`, `b_roll_priority`, and `montage_pacing`. It lacks typography, color grade, audio mix, and explicit Remotion archetype parameters.
- In `B:\ALL_TOOLS\CofiRemotion\src`, four distinct production compositions represent battle-tested visual presets:
  1. `SouthNorthWater20261018.tsx` & `ThreeGorgesDam20261015.tsx`: 2.5D Infrastructure & Technical Engineering.
  2. `LaoRongzhiCase20261017.tsx`: Forensic Noir Full-AI True Crime.
  3. `Wilson20260906.tsx` & `Paperclip20260906.tsx`: Archival Historical Vault.

#### Unified `editing_dna` JSON Schema
The following JSON schema must be added to `ChannelProfileRequest`, `ChannelProfile`, `CreateJobRequest`, and `Job`:

```json
{
  "editing_dna": {
    "preset_id": "2.5d_technical | forensic_noir | archival_historical | custom",
    "name": "2.5D Technical & Infrastructure Investigation",
    "version": 1,
    "locked_from_job_id": null,
    "locked_at": null,
    "pacing": {
      "target_beat_duration_sec": 5.5,
      "shot_range_sec": [4.0, 8.0],
      "max_routine_shot_sec": 10.0,
      "average_beat_duration_sec": 5.2,
      "pacing_curve": "accelerating_towards_act_climax",
      "pacing_wpm": 138
    },
    "visual_mix": {
      "footage_ratio": 0.40,
      "ai_visual_ratio": 0.35,
      "motion_overlay_ratio": 0.25,
      "preferred_routing": "hybrid",
      "max_consecutive_ai_shots": 3,
      "force_motion_on_static_ai": true
    },
    "editing_archetypes": [
      "2.5d_satellite_map",
      "technical_hud_telemetry",
      "chapter_hero_banner",
      "media_anchored_annotation",
      "hydraulic_simulation_overlay"
    ],
    "subtitle_style": {
      "font_family": "Noto Sans KR, Inter, sans-serif",
      "font_size_px": 48,
      "base_color": "#FFFFFF",
      "highlight_color": "#38BDF8",
      "warning_color": "#FBBF24",
      "stroke_color": "#000000",
      "stroke_width": 16,
      "shadow_blur": 12,
      "position": "bottom_center",
      "bottom_margin_px": 96,
      "max_words_per_line": 6,
      "emphasis_uppercase": false
    },
    "color_grade": {
      "tone_preset": "technical_cool_cyan",
      "lut_name": "clean_broadcast_cool",
      "vignette_style": "subtle_cinematic",
      "vignette_opacity": 0.78,
      "film_grain_opacity": 0.05,
      "contrast_multiplier": 1.08,
      "saturation_multiplier": 0.96
    },
    "audio_rules": {
      "bgm_track": "investigative_tension_subtle.mp3",
      "bgm_volume_db": -22.0,
      "ducking_db": -12.0,
      "ducking_attack_ms": 150,
      "ducking_release_ms": 300,
      "sfx_chapter_hit": true,
      "sfx_hud_click": true,
      "voice_lufs_target": -16.0
    },
    "editorial_rules": [
      "Always ground technical claims with KeyMetricCallout telemetry cards",
      "Every new geographical location must introduce a 2.5D MapSatelliteMotionStage",
      "Never hold a static visual longer than 7.5 seconds without camera push or telemetry scan",
      "Transformative annotations must be placed over key footage elements"
    ]
  }
}
```

#### The 4 Production Editing Presets
1. **Preset 1: `2.5d_technical` (2.5D Technical & Infrastructure Investigation)**
   - **Target Profiles**: Engineering, Mega-projects, Geopolitics (`channel-1e24de3ab5`).
   - **Visual Mix**: 40% Footage / 35% AI Visual / 25% Motion Overlays. Preferred routing: `hybrid`.
   - **Remotion Archetypes**: `MapSatelliteMotionStage`, `InSarRadarOverlay`, `HydraulicSimulationOverlay`, `KeyMetricCallout` (HUD displaying m³, km, %, tons), `ChapterHeroBanner`, `MediaAnchoredAnnotation`.
   - **Subtitle Style**: Noto Sans, 48px, #38BDF8 (electric cyan highlight), 16px black stroke.
   - **Color Grade**: Cool cyan/slate blue tint, subtle vignette (0.75 opacity), clean broadcast contrast.
   - **Audio**: Low drone ambient BGM (-22dB), chapter whoosh hit, telemetry sound cues.

2. **Preset 2: `forensic_noir` (Forensic Noir Full-AI True Crime)**
   - **Target Profiles**: Crime investigation, Missing persons, Unsolved mysteries (`channel-e544a64b7c`).
   - **Visual Mix**: 10% Archival Footage / 65% Dark AI Visual / 25% Forensic Overlays. Preferred routing: `full_ai`.
   - **Remotion Archetypes**: `InvestigationEvidenceBoard` (red string connection, pins, dossier Polaroid cards), `BiometricAndDnaHudBoard` (face scan laser, 97.33% match radar, DNA STR bars), `HandwritingScanBoard` (document scanner laser line), `ForensicMapRouteBoard` (2.5D crime route tracking), `ChapterHeroBanner`.
   - **Subtitle Style**: Noto Sans KR Bold, 50px, #FBBF24 (caution amber) & #EF4444 (crime red), 18px heavy black stroke.
   - **Color Grade**: Cold desaturated noir, dark vignette (0.88 opacity), film grain 0.12.
   - **Audio**: Dark brooding sub-bass BGM (-21dB), heartbeat riser before reveal, camera shutter SFX.

3. **Preset 3: `archival_historical` (Archival Historical Vault)**
   - **Target Profiles**: Historical declassified files, Cold War, Presidential secrets (`channel-aa913eb90d`, `channel-f6ec4dfff3`).
   - **Visual Mix**: 60% Sourced Archival Footage / 25% AI Visual / 15% Document Scans. Preferred routing: `evidence_footage`.
   - **Remotion Archetypes**: `ArchivalShowcaseStage`, `HandwritingScanBoard`, `BanqiaoArchiveStamp` (TOP SECRET / DECLASSIFIED stamps), `FilmFinish` (16mm gate weave & jitter, sepia vignette), `EvidenceTag`.
   - **Subtitle Style**: Serif / Merriweather, 46px, #F5F5F0 (vintage newsprint cream), #E2B340 highlight, 14px shadow.
   - **Color Grade**: Warm sepia tint, Kodak 2383 emulation, subtle paper texture overlay.
   - **Audio**: Vintage film projector hum ambient (-28dB), typewriter clicks, vinyl crackle under archival voice.

4. **Preset 4: `custom`**
   - User-customized parameters allowing granular override of pacing, mix, archetypes, and fonts.

---

### 2.2 "Lock Approved Edit Style to Channel" Workflow

#### Architectural Architecture Flowchart
```
+----------------------------------------------------------------------------------------------------+
|                                    PROJECT STEP 06: EDIT                                           |
| User previews and approves finalized documentary edit in Remotion Studio                           |
+-------------------------------------------------+--------------------------------------------------+
                                                  |
                                                  | Click "Lock Approved Edit Style to Channel"
                                                  v
                     POST /api/jobs/{job_id}/lock-edit-dna  (app.py -> service.py)
                                                  |
                                                  +---> Load Workspace Files:
                                                  |     - visual_manifest.json (beats, durations, visual types)
                                                  |     - voice_manifest.json (TTS audio lengths, words, wpm)
                                                  |     - asset_registry.json (media sources: AI, footage, motion)
                                                  |     - edit_checkpoint.json (active Remotion archetypes, config)
                                                  |
                                                  +---> Parameter Extraction & Empirical Calculation:
                                                  |     * pacing: target_beat_duration, min/max/median shot, wpm
                                                  |     * visual_mix: calculate actual ratio of footage/ai/motion
                                                  |     * editing_archetypes: detect active components from scenes
                                                  |     * subtitle_style & color_grade: parse from edit config
                                                  |
                                                  +---> Channel Profile Resolution & Versioning:
                                                  |     * Resolve profile_id from job["channel_profile_id"]
                                                  |     * Archive existing editing_dna into editing_dna_history[]
                                                  |     * Save new editing_dna with version = prev_version + 1
                                                  |     * Set locked_from_job_id = job_id, locked_at = ISO timestamp
                                                  |     * Persist to data/channel_profiles.json
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
|                                      NEW PROJECT INHERITANCE                                        |
| When POST /api/jobs is called for this channel_profile_id:                                          |
| - Automatically populate production_recipe with channel_profile.editing_dna                         |
| - Apply exact shot pacing, visual mix, Remotion archetypes, subtitles, and color grading            |
+----------------------------------------------------------------------------------------------------+
```

#### Detailed API Specification
- **Endpoint**: `POST /api/jobs/{job_id}/lock-edit-dna`
- **Controller File**: `app.py`
- **Service Implementation**: `documentary/service.py:lock_job_edit_dna_to_profile(job_id: str) -> dict`
- **Request Body**: Empty or optional `{ "override_name": "Optional custom name for preset" }`
- **Response**:
```json
{
  "status": "success",
  "message": "Edit style successfully locked to channel profile 'channel-1e24de3ab5' as version 2",
  "channel_profile_id": "channel-1e24de3ab5",
  "locked_job_id": "20261018-223750-3aecfbcd",
  "editing_dna": {
    "preset_id": "custom_locked",
    "name": "Locked from South-North Water Transfer (Job 3aecfbcd)",
    "version": 2,
    "locked_from_job_id": "20261018-223750-3aecfbcd",
    "locked_at": "2026-10-18T19:50:00Z",
    "pacing": {
      "target_beat_duration_sec": 5.8,
      "shot_range_sec": [4.0, 7.8],
      "max_routine_shot_sec": 9.5,
      "average_beat_duration_sec": 5.6,
      "pacing_wpm": 142
    },
    "visual_mix": {
      "footage_ratio": 0.45,
      "ai_visual_ratio": 0.30,
      "motion_overlay_ratio": 0.25,
      "preferred_routing": "hybrid"
    },
    "editing_archetypes": [
      "2.5d_satellite_map",
      "technical_hud_telemetry",
      "chapter_hero_banner",
      "media_anchored_annotation"
    ],
    "subtitle_style": {
      "font_family": "Noto Sans KR",
      "font_size_px": 48,
      "highlight_color": "#38BDF8",
      "stroke_width": 16
    },
    "color_grade": {
      "tone_preset": "technical_cool_cyan",
      "vignette_opacity": 0.78
    },
    "audio_rules": {
      "bgm_track": "investigative_tension_subtle.mp3",
      "bgm_volume_db": -22.0,
      "ducking_db": -12.0
    }
  },
  "history_count": 1
}
```

#### Extraction Logic Details
1. Read `workspaces/{job_id}/visual_manifest.json`:
   - Iterate over all scenes and beats.
   - Collect beat durations: `durations = [beat["duration_sec"] for scene in scenes for beat in scene["beats"]]`.
   - Calculate `min(durations)`, `max(durations)`, `statistics.mean(durations)`, and `statistics.median(durations)`.
2. Read `workspaces/{job_id}/asset_registry.json`:
   - Group assets by origin: `ai_image`, `ai_video`, `footage`, `motion_graphic`.
   - Calculate percentages against total visual beats.
3. Read `workspaces/{job_id}/edit_checkpoint.json` and `creative_brief`:
   - Extract active `editing_archetypes` and component references.
   - Extract typography, colors, and audio ducking levels.
4. Load `data/channel_profiles.json`:
   - Locate channel profile matching `job["channel_profile_id"]`.
   - If profile has existing `editing_dna`, append to `editing_dna_history`:
     ```python
     if "editing_dna" in profile and profile["editing_dna"]:
         profile.setdefault("editing_dna_history", []).append(profile["editing_dna"])
     new_version = (profile.get("editing_dna", {}).get("version", 0) + 1)
     ```
   - Set `profile["editing_dna"] = extracted_editing_dna`.
   - Save back atomically to `data/channel_profiles.json`.
5. Future project inheritance in `create_job()` (`documentary/service.py:164-282`):
   - When creating a job, check if `profile["editing_dna"]` exists.
   - Merge `profile["editing_dna"]` directly into `job["production_recipe"]` and `job["channel_profile_snapshot"]["editing_dna"]`.

---

### 2.3 Audio-Visual Voice & SRT Synchronization

#### Current Pipeline Analysis
- **Voice Synthesis**: In `documentary/voice.py` (lines 35-180), `CofiVoiceEngine.generate_job_audio()` iterates through script scenes and beats, synthesizing TTS audio for each beat using `cofivoice.tts` or mock fallback. Each beat record receives:
  - `start_sec`, `end_sec`, `duration_sec`, `audio_file`.
- **SRT Generation**: In `documentary/srt.py` (lines 20-75), `build_srt()` formats timestamps into `00:00:00,000 --> 00:00:00,000` based on the beat's voice duration.
- **Remotion Composition Timeline**: In `B:\ALL_TOOLS\CofiRemotion\src`, scenes use `<Sequence from={Math.round(beat.start_sec * 30)} durationInFrames={Math.round(beat.duration_sec * 30)}>` with 30fps timebase.

#### Sync Drift, Hold Freezes & Missing Visuals Problem Analysis
During rapid production, three common desynchronization flaws occur:
1. **Timestamp Drift**: Fractional second accumulation between beat audio files and subtitle cues, resulting in subtitles lagging behind voice by 0.5s–1.5s after 15 minutes.
2. **Hold Freezes**: Narrator speaks for 12–18 seconds on a single beat, but the assigned AI visual is a static 1920x1080 still image with zero motion, causing severe visual fatigue and YouTube "repetitive/static content" flags.
3. **Missing Visuals**: Beat audio exists, but visual asset generation timed out or failed in Step 05/04, resulting in a black frame or skipped asset.

#### Automated Detection & Repair Mechanism
Implement `documentary/sync_repair.py` and expose via API `POST /api/jobs/{job_id}/repair-sync`:

```
+-----------------------------------------------------------------------------------+
|                        SYNC INSPECTION & REPAIR ENGINE                            |
+-----------------------------------------------------------------------------------+
                                          |
            +-----------------------------+-----------------------------+
            |                                                           |
            v                                                           v
  [1. Beat-to-SRT Drift Check]                                [2. Hold Freeze Check]
  - Compare voice beat start_sec vs SRT cue start_sec.        - Any visual beat > 8.0s on
  - If drift > 0.05s: Re-snap SRT cue to exact voice audio       a static still image?
    timeline (start_sec = beat_audio.offset).                 - REPAIR:
                                                                * Split beat or apply Remotion
                                                                  Camera Motion (scale 1.02x->1.08x
                                                                  + 2.5D pan + Ken Burns).
                                                                * Inject secondary annotation overlay
                                                                  at timestamp + 4.0s.
                                          |
                                          v
                              [3. Missing Visual Check]
                              - Check asset_registry.json for valid media_path per beat.
                              - If missing:
                                * Fallback 1: Route to AI Visual prompt fallback.
                                * Fallback 2: Clone adjacent contextual asset from same
                                  story_group with mirrored horizontal flip and zoom-in crop.
```

#### Verification Scorecard Output
Expose `GET /api/jobs/{job_id}/sync-compliance`:
```json
{
  "job_id": "20261018-223750-3aecfbcd",
  "sync_score": 98.5,
  "sync_status": "PASSED",
  "checks": {
    "audio_srt_drift": {
      "status": "PASSED",
      "max_drift_ms": 12,
      "threshold_ms": 50,
      "repaired_cues": 0
    },
    "static_hold_freezes": {
      "status": "PASSED",
      "holds_exceeding_8s": 0,
      "repaired_holds": 2,
      "repair_actions": [
        "Beat 14: Applied Ken Burns push-in (1.02x to 1.07x) and telemetry HUD overlay",
        "Beat 38: Applied 2.5D parallax split at 5.5s"
      ]
    },
    "missing_visuals": {
      "status": "PASSED",
      "total_beats": 124,
      "missing_beats": 0,
      "fallbacks_applied": 0
    }
  }
}
```

---

### 2.4 YouTube Policy & Green Monetization Guardrails

#### Current Policy Enforcement
- `documentary/service.py` currently has `_violates_forbidden_topics` (lines 420-435) checking hardcoded Korean/Vietnamese tokens (`"뇌물"`, `"부패"`, `"횡령"`, `"hối lộ"`, `"tham nhũng"`).
- It also injects prompt instructions ("100% Green Monetization", "After-the-Storm forensic investigation").
- However, there is no verification scorecard validating script text, visual prompts, footage selections, and final edit for compliance with YouTube's 2026 Advertiser-Friendly Content Guidelines (APAC/US/KR).

#### Full-Spectrum Policy Guardrail Matrix
1. **Ad-Friendly Green Monetization (Advertiser-Friendly Guidelines)**:
   - **Gore & Graphic Violence**: Zero blood splatter, dismemberment, corpse close-ups, or real-life assault in AI visual prompts or footage metadata. All crime depictions must use "After-the-Storm forensic investigation" (police tape, evidence markers, declassified files, courtroom sketches, silhouette reconstructions).
   - **Prohibited Tokens Lexicon**: Expand forbidden checks to multi-language lexicons (EN, KR, VN, ZH) including hate speech, graphic violence, self-harm, weapons manufacturing, and defamatory claims.
2. **Anti-Repetitive / Reused Content Compliance**:
   - YouTube flags mass-produced AI documentaries that hold a single image for extended periods or loop the exact same stock footage clip.
   - **Rule**: Max static image hold <= 8.0s; identical footage clip cannot appear more than 1 time across the entire documentary; consecutive AI images cannot exceed 3 without a motion graphic, map, or footage intercut.
3. **Transformative Editorial Value (Fair Use / Monetization Requirement)**:
   - Sourced archival footage or public-domain clips must have transformative value added.
   - **Rule**: Every footage segment must have at least one media-anchored annotation (e.g. `MediaAnchoredAnnotation`, document highlight, or satellite overlay), and must not exceed 15s of raw untransformed playback.

#### Edit/QC Compliance Scorecard Implementation
Integrate into `documentary/quality.py:validate_phase_quality("qc", workspace_dir)`:
- Run regex and semantic scan across `script.json`, `visual_manifest.json`, and `asset_registry.json`.
- Output `compliance_scorecard.json` in workspace containing:
  - `monetization_status`: `"GREEN" | "YELLOW" | "RED"`.
  - `graphic_violence_flags`: list of flagged beats/prompts.
  - `repetitive_content_flags`: list of static holds > 8s or duplicated footage.
  - `transformative_score`: percentage of footage clips with editorial overlays (must be >= 85%).

---

## 3. Requirements R4, R5 & AC4: Channel-DNA Pre-Flight & Self-Learning Engine

### 3.1 Real YouTube Channel Data in Storage

In `data/channel_profiles.json`, real YouTube channel metadata is already captured in the `own_channel.dna` and `competitors` structures for active channels:
- `channel-aa913eb90d` ("The First Family Vault", US market):
  - `winner_terms`: `"white house"`, `"kennedy"`, `"secret service"`, `"oval office"`, `"classified"`, `"presidential bunker"`.
  - `weak_terms`: `"inauguration speech"`, `"policy debate"`, `"diplomatic treaty"`.
  - `winner_titles`: Videos with 250k–1.8M views, VPH 120–450, outlier ratio 2.8x–6.4x.
- `channel-1e24de3ab5` ("판세 của 이면", KR market, Mega-Infrastructure & Geopolitics):
  - `winner_terms`: `"남수북조"`, `"싼샤댐"`, `"초대형 프로젝트"`, `"수자원"`, `"지하 수로"`, `"붕괴 위기"`.
  - `weak_terms`: `"정치인 연설"`, `"외교 회담"`, `"학술 토론"`.
  - `winner_titles`: Videos with 180k–920k views, VPH 85–380, outlier ratio 2.1x–5.2x.

---

### 3.2 Channel DNA Pre-Flight Checks (Topics, Titles, Thumbnails, SEO)

Before Step 00/01 topic generation, Step 07 thumbnail design, or SEO export, the system runs a **Pre-Flight DNA Audit**:

```
+------------------------------------------------------------------------------------+
|                         CHANNEL DNA PRE-FLIGHT AUDIT ENGINE                        |
+------------------------------------------------------------------------------------+
                                          |
            +-----------------------------+-----------------------------+
            |                             |                             |
            v                             v                             v
[Topic & Title Pre-Flight]      [Thumbnail Pre-Flight]          [SEO Pre-Flight]
- Cross-checks channel video    - Inspects channel's top        - Checks top keyword
  catalog & internal jobs.        CTR & winning thumbnails.       winners & core tags.
- Blocks duplicate topics       - Extracts color contrast,      - Generates high-intent
  already published.              subject focal size (>45%),      descriptions with
- Generates 3 title formulas      and left-heavy layout.          chapters and searchable
  using proven winner terms.    - Feeds Thumbnail Studio          long-tail phrases.
                                  for 3+ testable variants.
                                          |
                                          v
+------------------------------------------------------------------------------------+
|                        OUTPUT: preflight_summary OBJECT                            |
| {                                                                                  |
|   "channel_profile_id": "channel-1e24de3ab5",                                     |
|   "preflight_status": "PASSED",                                                    |
|   "duplicate_check": { "is_duplicate": false, "closest_match": null },            |
|   "title_dna_match": { "score": 96.0, "winner_formula_used": "Entity+Metric+Crisis" },|
|   "thumbnail_dna_match": { "score": 94.0, "archetype": "broadcast_left_heavy" }, |
|   "seo_dna_match": { "score": 98.0, "core_terms_covered": ["남수북조", "싼샤댐"] } |
| }                                                                                  |
+------------------------------------------------------------------------------------+
```

#### Thumbnail Studio Integration (3+ Variants, Zoom Preview & Downloads)
- **Backend Architecture**: `documentary/thumbnail_studio.py` exposes `build_thumbnail_concepts()`, `render_thumbnail_variant()`, and `evaluate_thumbnail_ctr()`.
- **4 Built-in Archetypes**:
  1. `broadcast_left_heavy`: Hero character / entity on left (45% canvas width), giant bold typography right, dark gradient backdrop.
  2. `bottom_cinematic`: Wide cinematic focal subject centered, heavy bottom third dark vignette, massive yellow/cyan title text across lower third.
  3. `split_duality`: Vertical split comparison (Before vs After / Official Story vs Hidden Truth), bold central divider with high-contrast badge.
  4. `evidence_spotlight`: Dark noir background, glowing evidence document / satellite radar spotlight with red arrow callout.
- **Frontend Architecture**: In `static/thumbnail_studio.js`:
  - Renders 4 interactive Fabric.js canvas cards.
  - Features **Lightbox Zoom Preview Modal**: Clicking any card opens a full-screen zoom preview with simulated YouTube UI overlay (mobile feed & desktop search view).
  - Features **Single Card Download** (`downloadSingleThumbnail(index)`) and **Batch Download** (`downloadAllThumbnails()`) exporting 1280x720 PNGs.

---

### 3.3 Continuous Self-Learning Post-Mortem Engine

#### Architecture & Win/Loss Classification
- **Controller File**: `app.py`
- **Endpoints**:
  - `GET /api/radar/channel-profiles/{profile_id}/self-learning`: Fetches current post-mortem report and evolution rules.
  - `POST /api/radar/channel-profiles/{profile_id}/self-learning`: Runs a fresh self-learning post-mortem analysis over channel YouTube history and internal project logs.
- **Classification Formula**:
  - Let $M_v$ be channel median views, $M_o$ be median outlier multiplier (default 1.0x).
  - **Winner (Outlier)**: $\text{Outlier Ratio} \ge 2.5\times$ OR $\text{Views} \ge 2.0 \times M_v$.
  - **Neutral**: $1.0\times \le \text{Outlier Ratio} < 2.5\times$.
  - **Underperformer (Losing Video)**: $\text{Outlier Ratio} < 1.0\times$ AND $\text{Views} < 0.5 \times M_v$.

#### Diagnostic Post-Mortem Failure Analysis for Underperformers
For each classified underperformer, the engine executes 5 diagnostic evaluations:
1. **Title Keyword Fatigue**: Title contains terms from `profile["weak_terms"]` or lacks high-tension quantitative metrics.
2. **Thumbnail Weakness**: Lacks clear focal subject contrast (< 40% canvas coverage), text unreadable on mobile (< 48px equivalent), or generic color palette.
3. **Topic Drift**: Topic is outside channel's core niche (e.g. political interview on an engineering documentary channel).
4. **Weak First 30s Hook**: Script opening lacks immediate high-stakes crisis or quantitative hook.
5. **Pacing Drop-off / Visual Monotony**: Visual beats hold static images > 8s or lack dynamic motion overlays.

#### Synthesis of Upgrade Rules & Persistence
The engine synthesizes three concrete evolution sets and stores them in `profile["self_learning_memory"]`:
```json
{
  "self_learning_memory": {
    "last_analyzed_at": "2026-10-18T19:55:00Z",
    "total_videos_analyzed": 48,
    "winners_count": 12,
    "underperformers_count": 9,
    "what_to_stop_doing": [
      "STOP generating passive academic titles without concrete quantitative numbers",
      "STOP using low-contrast dark gray text on documentary thumbnails",
      "STOP holding static AI landscape visuals longer than 7 seconds",
      "STOP selecting abstract geopolitical policy topics without tangible physical structures"
    ],
    "what_to_double_down_on": [
      "DOUBLE DOWN on mega-structure crisis titles: [Structure] + [Cost/Metric] + [Crisis Verbatim]",
      "DOUBLE DOWN on Broadcast Left-Heavy thumbnails with electric cyan (#38BDF8) text accents",
      "DOUBLE DOWN on 2.5D Satellite Map route flyovers in Chapter 1",
      "DOUBLE DOWN on opening scripts with an immediate 5-second disaster threshold"
    ],
    "next_video_upgrades": {
      "topic_rule": "Must feature a physical mega-engineering project exceeding $10B or 1,000km",
      "title_rule": "Formula: [Project Name] + [Extreme Quantitative Number] + [Hidden Crisis Status]",
      "thumbnail_rule": "Archetype: broadcast_left_heavy, 48% subject scale, #38BDF8 highlight, max 4 words",
      "hook_rule": "Deliver immediate catastrophic failure metric in first 15 seconds before title card",
      "edit_rule": "Enforce target_beat_duration_sec: 5.5s, 25% motion HUD overlay ratio, zero holds > 7s"
    }
  }
}
```

---

## 4. Existing Codebase Inventory & Gap Analysis

| Component / File | Current State | Required Modification / Gap |
| :--- | :--- | :--- |
| `app.py` | Defines `ChannelProfileRequest` & job endpoints. | **MISSING**: `editing_dna` in `ChannelProfileRequest`, `POST /api/jobs/{id}/lock-edit-dna`, `GET /api/jobs/{id}/sync-compliance`, `POST /api/jobs/{id}/repair-sync`, `GET/POST /api/radar/channel-profiles/{id}/self-learning`. |
| `documentary/service.py` | Manages jobs, channel profiles, discovery, topic extraction. | **MISSING**: Implementation of `lock_job_edit_dna_to_profile()`, `run_channel_preflight()`, `run_channel_self_learning()`, and `editing_dna` inheritance in `create_job()`. |
| `documentary/quality.py` | `normalize_production_recipe()`, `validate_phase_quality()`. | **MISSING**: Schema validation for `editing_dna`, policy scorecard validation in `validate_phase_quality("qc")`. |
| `documentary/voice.py` & `srt.py` | Generates per-beat audio and SRT cues. | **MISSING**: Automated drift detection and timestamp synchronization repair function. |
| `documentary/thumbnail_studio.py` | Generates 4 thumbnail archetypes, Fabric.js JSON, CTR scoring. | Needs direct wiring to channel profile's `thumbnail_dna` and pre-flight summary integration. |
| `static/thumbnail_studio.js` | UI rendering for thumbnail studio cards, zoom preview modal, single/batch downloads. | Verify lightbox zoom modal, single-card PNG download, and batch ZIP/PNG download against DOM requirements. |
| `data/channel_profiles.json` | Stores 4 channel profiles with `own_channel.dna`. | Needs schema migration: add `editing_dna`, `editing_dna_history`, `self_learning_memory`, `thumbnail_dna`, and `seo_dna` to all 4 profiles. |
| `B:\ALL_TOOLS\CofiRemotion\src` | Contains active compositions (`SouthNorthWater`, `LaoRongzhi`, `ThreeGorgesDam`, `Wilson`). | Verify that preset parameters match the exact component props used in these files. |

---

## 5. Concrete Implementation Roadmap

1. **Step 1: Data Model & Schema Migration**
   - Update `app.py` Pydantic models: `EditingDnaModel`, `ChannelProfileRequest`, `ChannelProfileResponse`, `SelfLearningResponse`.
   - Migrate existing channel profiles in `data/channel_profiles.json` to include default `editing_dna` matching their niche (e.g. `channel-1e24de3ab5` -> `2.5d_technical`, `channel-e544a64b7c` -> `forensic_noir`, `channel-aa913eb90d` -> `archival_historical`).
2. **Step 2: "Lock Approved Edit Style" Backend & Service**
   - Implement `lock_job_edit_dna_to_profile()` in `documentary/service.py`.
   - Wire `POST /api/jobs/{job_id}/lock-edit-dna` in `app.py`.
   - Update `create_job()` to automatically inherit `editing_dna` from the selected channel profile into `production_recipe`.
3. **Step 3: Audio-Visual Sync & YouTube Policy Scorecard**
   - Implement `documentary/sync_repair.py` for drift detection, hold repair, and visual fallback routing.
   - Wire `GET /api/jobs/{job_id}/sync-compliance` and `POST /api/jobs/{job_id}/repair-sync`.
   - Extend `documentary/quality.py` with the Green Monetization Policy verification scorecard.
4. **Step 4: Channel DNA Pre-Flight Check Engine**
   - Implement `run_channel_preflight(channel_profile_id, topic, title)` in `documentary/service.py`.
   - Wire pre-flight checks into topic/title generation and Step 07 thumbnail/SEO workflows.
5. **Step 5: Self-Learning Post-Mortem Engine**
   - Implement `analyze_channel_post_mortem(channel_profile_id)` in `documentary/service.py`.
   - Wire `GET/POST /api/radar/channel-profiles/{profile_id}/self-learning` in `app.py`.
   - Persist upgrade rules in `profile["self_learning_memory"]` and inject into Step 00/01/06/07.

---

## 6. Verification Methods

1. **Unit & Integration Tests**:
   - Run: `py -m pytest tests/test_editing_dna.py tests/test_channel_self_learning.py --basetemp=B:\ALL_TOOLS\CofiDocumentary\.pytest_tmp2 -v`.
2. **Lock Edit Style Verification**:
   - Execute: `curl -X POST http://localhost:8000/api/jobs/20261018-223750-3aecfbcd/lock-edit-dna`.
   - Inspect: Verify `data/channel_profiles.json` contains updated `editing_dna` with `version: 2` and `locked_from_job_id: "20261018-223750-3aecfbcd"`.
   - Create a new job on that profile and verify `production_recipe` has inherited the locked edit DNA.
3. **Self-Learning Post-Mortem Verification**:
   - Execute: `curl -X POST http://localhost:8000/api/radar/channel-profiles/channel-1e24de3ab5/self-learning`.
   - Verify: Response contains `winners_count`, `underperformers_count`, `what_to_stop_doing`, and `next_video_upgrades`.
4. **Sync & Policy Scorecard Verification**:
   - Execute: `curl http://localhost:8000/api/jobs/20261018-223750-3aecfbcd/sync-compliance`.
   - Verify: Returns JSON scorecard with `audio_srt_drift`, `static_hold_freezes`, and `monetization_status: "GREEN"`.
