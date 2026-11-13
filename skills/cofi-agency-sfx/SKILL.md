---
name: cofi-agency-sfx
description: "[COFI DOCUMENTARY Official SFX & Acoustic Foley Skill] Integrates elevenlabs/skills (sound-effects) physical motion-to-Foley choreography and freesound-mcp (MuShan-bit/freesound-mcp & jumpifequal/mcp-freesound) real recorded acoustic Foley sourcing. Enforces 0% code-synthesized SFX, 0% SFX on REAL_FTG and AI_4D, and 100% Motion-Bound real Foley at only 2 locations: VOX Editorial Desk / 3D GIS Stage (t1, t2, t3) and Cinema Text / Chapter Curtains (CT_*)."
---

# 🔊 COFI Agency SFX Director (`cofi-agency-sfx`)

> **Methodology Roots**:
> 1. **`elevenlabs/skills` (`sound-effects/SKILL.md`)**: Physical motion-to-Foley mapping, tactile material specificity (paper weight, felt-marker friction, rubber ink stamp compression, cartographic air displacement, deep cinematic sub-pulse), envelope shaping, and strict anti-clutter mix discipline (`-18dB` to `-22dB` below narration).
> 2. **`freesound-mcp` (`MuShan-bit/freesound-mcp` & `jumpifequal/mcp-freesound`)**: Real recorded acoustic Foley sourcing and verification — every sound asset must originate from an authentic microphone recording of a physical material or acoustic instrument (`raw_commons/` / Freesound / Wikimedia Commons CC0 studio recordings), never from mathematical oscillator formulas.

---

## 🚨 THE 3 IRON LAWS OF COFI DOCUMENTARY SFX

### Law 1 — `0%` Code-Synthesized Waveforms (Absolute Ban on Synthetic Audio)
- **STRICTLY FORBIDDEN**:
  - `ffmpeg -f lavfi -i "aevalsrc=..."`
  - `ffmpeg -f lavfi -i "anoisesrc=..."`
  - `ffmpeg -f lavfi -i "sine=..."`
  - Python `numpy` / `scipy` / `math.sin` / white-noise array synthesis written to `.wav` or `.mp3`.
- **MANDATORY**:
  - `100%` of SFX files in `presets/audio_library/sfx/`, `public/audio_library/sfx/`, `public/audio/`, and `<workspace>/audio/` must be **real recorded acoustic Foley or real acoustic instrument recordings** (sourced from verified Freesound / Wikimedia Commons studio recordings in `public/audio_library/sfx/raw_commons/` or fetched via `freesound-mcp` / `audio_library_manager.py`).
  - Every SFX file must have a unique SHA-256 hash (`0` duplicate files masquerading under different filenames) and natural broadband acoustic decay verified by `ffprobe` / spectral inspection.

### Law 2 — `0%` SFX on `REAL_FTG` and `AI_MASCOT` / `AI_4D`
- **NEVER** attach SFX to authentic archival video footage (`REAL_FTG`) or AI reconstruction stills (`AI_MASCOT` / `AI_4D`).
- **NEVER** use literal "story-word" Mickey-Mousing SFX triggered by nouns in the script (e.g., **NO** dog barks `sfx_K9_bark_distant.mp3`, **NO** cash thuds `sfx_cash_bundle_thud.mp3`, **NO** shovel digging `sfx_shovel_earth_dig.mp3`, **NO** handcuffs, **NO** rifle bolts, **NO** calipers, **NO** compass clicks).
- Real documentary authority comes from the narrator's voice, the 8–12 segment Story-Arc BGM, and intentional breathing holds — not cartoon sound effects on video clips.

### Law 3 — `100%` Motion-Bound SFX at ONLY 2 Locations
SFX are permitted **exclusively** where an explicit graphical motion occurs on screen, at **only 2 locations**:

1. **Location A — VOX Editorial Desk & 3D GIS Stage (`VOX_01..VOX_N` — dynamic by video content)**:
   - Bound `100%` to the exact `[t1, t2, t3]` frame offsets of the physical desk / map choreography:
     - **Paper Slide / Card Placement (`<SlideIn>`, `<VoxPhotoPaper>`, `<VoxVideoPaper>`, `<IndexCard>`, `<TornClipping>`)**:
       - `audio/sfx_paper_turn.mp3` (crisp archival dossier card slide & page placement)
       - `audio/sfx_newspaper_unfold.mp3` (broadsheet clipping / document unfold)
       - `audio/sfx_folder_open.mp3` (manila case file open on desk)
     - **Ink / Marker Circle & Line Stroke (`<RedCircle>`, `<RedLine>`, `<Underline>`, `<DimensionBracket>`)**:
       - `audio/sfx_marker_circle_draw.mp3` (real felt-tip marker drawing stroke on paper)
     - **Highlighter Swipe (`<Highlight>`)**:
       - `audio/sfx_highlighter_swipe.mp3` (real soft felt highlighter swipe across text)
     - **Official Rubber Stamp Impact (`<Stamp>`)**:
       - `audio/sfx_dossier_stamp.mp3` (real rubber ink seal thud on paper dossier)
       - `audio/sfx_official_seal_thud.mp3` (deep institutional case-file seal impact)
     - **3D GIS Parabolic Camera Flight (`<GeoJson3DMapStage>`)**:
       - `audio/sfx_map_route_sweep.mp3` (soft aerodynamic cartographic camera fly-to whoosh)
       - `audio/sfx_radar_ping_sonar.mp3` (subtle acoustic target pin lock on 3D map)

2. **Location B — Cinema Text Beats (`CT_01..CT_M` / `FramelessCinemaTextBeat.tsx`) & Chapter Curtains**:
   - Triggered at the main kinetic text entrance (`t1` / `t2`) or Chapter Curtain reveal:
     - **Main Text Entrance Subtle Air Whoosh (`t1`)**:
       - `audio/sfx_soft_whoosh.mp3` or `audio/sfx_transition_whoosh.mp3` (subtle warm air movement as main centered typography enters)
     - **Climax Line / Metric Reveal Editorial Pulse (`t2`) & Chapter Curtain Hit**:
       - `audio/sfx_chapter_hit.mp3` (real muffled concert timpani / acoustic editorial pulse)
       - `audio/sfx_soft_impact.mp3` (warm cushioned low-end acoustic pulse for key text reveal)

---

## 🎛️ CANONICAL REAL FOLEY SFX TABLE & MIX LEVELS

All SFX cues must sit **`-18dB` to `-22dB` below the narration track** (`volume: 0.085` – `0.115` in Remotion `<Audio>`) so they provide tactile physical presence without ever masking a single spoken syllable:

| Motion Context | Motion Primitive | Verified Real Audio File | Source Recording Lineage | Recommended `volume` | Trigger Frame |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **VOX Paper / Card Slide** | `paper_card_slide` | `audio/sfx_paper_turn.mp3` | Real page turn recording (`turning_page.wav`) | `0.095` | `t1` (`offsetFrames: trig[0]`) |
| **VOX Newspaper / Clipping** | `newspaper_clipping_unfold` | `audio/sfx_newspaper_unfold.mp3` | Real archival paper unfold (`book_pages_assorted.wav`) | `0.100` | `t1` (`offsetFrames: trig[0]`) |
| **VOX Dossier Folder Open** | `manila_dossier_open` | `audio/sfx_folder_open.mp3` | Real heavy paper folder open (`book_pages_assorted.wav`) | `0.100` | `t1` (`offsetFrames: trig[0]`) |
| **VOX Marker Circle / Line** | `marker_circle_draw` | `audio/sfx_marker_circle_draw.mp3` | Real felt marker stroke (`377124 tubbsmedia marker-lines.wav`) | `0.105` | `t2` / `t3` (`offsetFrames: trig[1..2]`) |
| **VOX Highlighter Swipe** | `highlighter_stroke_swipe` | `audio/sfx_highlighter_swipe.mp3` | Real felt pen / pencil stroke (`pencil_scratch.wav` / `marker_lines.wav`) | `0.100` | `t2` / `t3` (`offsetFrames: trig[1..2]`) |
| **VOX Rubber Stamp Impact** | `official_seal_stamp` | `audio/sfx_dossier_stamp.mp3` | Real rubber ink stamp on desk (`rubber_seal.wav`) | `0.112` | `t3` (`offsetFrames: trig[2]`) |
| **VOX Heavy Seal Thud** | `heavy_seal_impact` | `audio/sfx_official_seal_thud.mp3` | Real wooden/rubber desk seal thud (`wood_knock.wav` + `rubber_seal.wav`) | `0.112` | `t3` (`offsetFrames: trig[2]`) |
| **VOX 3D Map Camera Fly-To** | `gis_camera_flight_arc` | `audio/sfx_map_route_sweep.mp3` | Real acoustic air/foliage sweep recording (`book_pages_assorted.wav` air contour) | `0.102` | `t1` / `t2` |
| **VOX Photo / Polaroid Snap** | `polaroid_photo_pin` | `audio/sfx_camera_shutter.mp3` | Real mechanical SLR shutter (`canon_shutter.wav`) | `0.092` | `t1` / `t2` |
| **VOX Typewriter / Log** | `typewriter_text_reveal` | `audio/sfx_typing_log.mp3` | Real Smith-Corona mechanical keystroke (`smith_corona_typing.wav`) | `0.088` | `t2` |
| **Cinema Text Entrance Whoosh** | `card_fly_in` | `audio/sfx_soft_whoosh.mp3` | Real warm acoustic air brush (`sfx_cinema_bowed_cello_swell` / air pass) | `0.092` | `t1` (`offsetFrames: 4..6`) |
| **Cinema Text Climax Pulse** | `funnel_node_lock` | `audio/sfx_soft_impact.mp3` | Real muffled acoustic timpani cushion (`sfx_cinema_muffled_timpani.mp3`) | `0.102` | `t2` (`offsetFrames: 18..28`) |
| **Chapter Curtain / CT Deep Hit** | `chapter_card_enter` | `audio/sfx_chapter_hit.mp3` | Real acoustic concert timpani & sub-drop (`timpani_hit1.wav` / `sfx_cinema_sub_drop.mp3`) | `0.115` | Chapter start / `t2` |

---

## 🔍 VERIFICATION CHECKLIST BEFORE HANDOFF

1. **Zero Synthetic Audio Gate**:
   - Run SHA-256 and `ffprobe` audit across `presets/audio_library/sfx/`, `public/audio_library/sfx/`, `public/audio/`, and `<workspace>/audio/`.
   - Confirm `0` duplicate SHA-256 hashes among the canonical VOX and Cinema Text SFX files.
2. **Beat-Type Purity Gate**:
   - Every `REAL_FTG` beat has `sfxEvents: []` (`0` SFX).
   - Every `AI_MASCOT` / `AI_4D` beat has `sfxEvents: []` (`0` SFX).
   - Only `VOX_*` beats (`t1, t2, t3` desk/map motions) and `CT_*` / Chapter beats carry `sfxEvents`.
3. **Physical File Existence Gate**:
   - Every `ev.file` referenced in `edit_manifest.json` and `*Data.ts` exists physically in `<workspace>/audio/`, `public/jobs/<job_id>/audio/`, and `public/audio/`.
