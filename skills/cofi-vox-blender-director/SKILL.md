---
name: cofi-vox-blender-director
description: Specialist skill for directing True Crime & Investigative Documentary edits in CofiDocumentary using the Universal 4-Tier Semantic Visual Priority Rule (1. Video Footage -> 2. Photo Footage -> 3. Approved Vox -> 4. AI Image) and the 24 Approved Vox Archetypes (8 Real Esri Satellite Maps #M1-#M8, 10 Tactile Forensic & Lab Dossiers #D1-#D10, 6 Archival Press & CRT Broadcasts #P1-#P6) implemented in vox_editorial_artist.py and vox_archetype_expansion.py.
---

# COFI Vox Satellite & Tactile Dossier 24-Archetype Director Skill

Use this skill whenever planning, routing, editing, or rendering **Documentary / True Crime / Investigative** visuals and timelines in **COFI DOCUMENTARY** (`b:\ALL_TOOLS\CofiDocumentary`), **COFI BLENDER STUDIO** (`b:\ALL_TOOLS\CofiBlenderStudio`), or **COFI REMOTION** (`b:\ALL_TOOLS\CofiRemotion`).

---

## 1. Universal 4-Tier Semantic Visual Priority Law (Applies to ALL Content & Niches)

1. **ZERO MECHANICAL FORMULAS OR CYCLING**:
   - **Never** use modulo loops (`if i % 3 == 0`), fixed percentage quotas, or round-robin cycling (`1 -> 2 -> 3 -> 4 -> 5 -> 6`) to place visuals, maps, or Vox clips.
   - **100% Semantic Voice-to-Visual Match**: Every single visual appearing on screen MUST clearly illustrate and match the exact meaning of the spoken voiceover (`narration_text`) at that beat.

2. **STRICT 4-TIER VISUAL PRIORITY ORDER FOR EVERY BEAT**:
   Evaluate every spoken beat against this exact hierarchy:
   - **Priority #1 — Video Footage (`sourced_video`)**: Authentic documentary/archival/B-roll video footage that directly illustrates the person, place, action, or event in the spoken voice line.
   - **Priority #2 — Photo / Archival Still Footage (`sourced_still`)**: Authentic archival photographs or documentary stills when no video clip directly illustrates that specific spoken line.
   - **Priority #3 — Tactile Vox Graphic / Satellite Map (`vox_dossier` / `#M1..#M8`, `#D1..#D10`, `#P1..#P6`)**: Used **ONLY** when the spoken voice line specifically talks about content that a Vox graphic clarifies (e.g. a geographic location/route/perimeter, a quantitative timeline, a forensic/DNA/fingerprint comparison, an interrogation transcript, an official warrant/verdict, or a broadcast record) AND you must select the single specific Vox style that fits that exact voice line. Never repeat the same map or Vox clip across unrelated dialogue.
   - **Priority #4 — AI Reconstructed Image (`ai_reconstruction` / `_ai_keyframe.jpg`)**: **LAST RESORT** — used **ONLY** when Video Footage (Priority #1), Photo Footage (Priority #2), and Semantic Vox (Priority #3) cannot clearly illustrate the spoken voice line.

3. **ALWAYS BUTTER-SMOOTH 30 FPS SUB-PIXEL MOTION & ZERO STATIC `.PNG` VOX/MAPS**:
   - **Never** create or use static `.png` images (`MAP01..08.png`) for Vox graphics or satellite maps! Every single Vox graphic and satellite map MUST be an **animated 30 fps `.mp4` motion video** (`motion_*.mp4`).
   - All Vox motion clips (`motion_*.mp4`) and map zooms/pans MUST be rendered at **true 30 fps (`steps = 180, repeats = 1`, zero frame-stepping)** using **sub-pixel floating-point camera sampling (`Image.Transform.EXTENT` with `Image.Resampling.BICUBIC`)** in `crop_map_camera`, with progressive perimeter/trajectory tracing, expanding sonar radar rings, progressive callout leader lines, and staggered entrance physics for all Polaroids, newspaper clippings, highlighter sweeps, and stamps. Never use integer pixel crop truncation (`int(x0)`) or multi-frame repeats (`repeats > 1`).

4. **STRICTLY FORBIDDEN LEGACY PROTOTYPES**:
   - **Never** use the deprecated raw 3D primitive prototypes (`blender_scene_builder.py`, `scene_01_case_board_final.mp4`, `scene_02_map_25d_final.mp4`, `scene_03_ystr_scanner_final.mp4`, `scene_04_fingerprint_verdict_final.mp4`, `#B1..#B4`).
   - **Never** build raw HTML/CSS `<div>` chapter banners (`<ChapterHeroBanner>`), `<SceneTransitionStamp>`, or dark `rounded_rectangle` HUD boxes in Remotion.
   - **Never** bake bottom narration subtitles into the Vox plate/motion video (`subtitle_text=""` when rendering plates for Remotion so Remotion's `<SubtitleOverlay>` renders clean single-layer Korean subtitles).

---

## 2. The 24 Approved Vox Documentary Archetypes Catalog (`vox_editorial_artist.py` + `vox_archetype_expansion.py`)

### Cluster A — 8 Real Satellite GIS & Motion Map Archetypes (`#M1` – `#M8`)
- **`#M1` (`render_vox_scene_02_school_store_map` — Urban Satellite + Rooftop Loupe)**: Full-screen real Esri satellite map + animated GPS trajectory + circular `ZOOM ×16/×18` rooftop magnifier loupe on the left + 2 torn-edge photo cutouts on the right + hand-drawn double-circle map pin.
- **`#M2` (`render_vox_scene_04_gansu_baiyin_gis` — Macro Satellite Terrain + Press + Memo)**: High-altitude satellite terrain with glowing zone highlight + 2 left torn-edge photo cutouts + right pinned newspaper clipping + yellow paperclip memo card + map pin.
- **`#M3` (`render_vox_scene_06_hukou_blindspot_gis` — Dual-Zone Radar Sweep & Trajectory)**: Full-screen satellite dual-zone radar sweep & vector trajectory + 2 left torn-edge photo cutouts + right pinned newspaper clipping + paperclip memo card + 2 map pins.
- **`#M4` (`render_vox_scene_08_1998_four_cases_map` — Framed Detective Cork Pinboard + Satellite Cluster)**: Wooden-framed cork pinboard (`wrap_on_detective_pinboard`) + real urban satellite map + 4 numbered map pins linked by taut red detective string (`draw_red_string_link`) to 2 left photo cutouts, right newspaper clipping, and memo card.
- **`#M5` (`render_archetype_m5_25d_tilted_satellite` — 2.5D Perspective Tilted Satellite Slab + Beacons)**: 2.5D perspective-warped trapezoid satellite slab with 3D stone depth edge + 3 vertical laser beacons with floating callout pills + parabolic red arcs + 2 right torn-edge photo cutouts.
- **`#M6` (`render_archetype_m6_split_dual_satellite` — Split-Screen Dual Satellite Macro ↔ Micro)**: Vertical split-screen pairing macro regional satellite on the left with high-res rooftop satellite on the right + center zoom bridge pill + bottom-left telemetry card + top-right photo cutout.
- **`#M7` (`render_archetype_m7_night_ops_satellite` — Night-Ops Thermal/Sodium-Glow Lockdown Grid)**: Night-Ops deep slate-blue & sodium-glow satellite shader + crimson lockdown perimeter circle + 4 checkpoint pills + left & right photo cutouts.
- **`#M8` (`map_gps_trajectory` — Chronological Multi-Stop GPS Trajectory)**: Multi-waypoint chronological GPS route animating across real Esri satellite tiles.

### Cluster B — 10 Tactile Forensic Dossier & Lab Archetypes (`#D1` – `#D10`)
- **`#D1` (`render_vox_scene_01_fingerprint_paradox` — Open Manila Police Case Folder + 84-Cell Matrix)**: Open Manila dossier folder (`get_manila_dossier_folder_canvas`) with red-ink forensic header table, binder holes, brass fasteners + right torn-paper 84-cell matrix & giant counter (`일치자 0명` / `이탈 흔적 0건` red stamp box + circular official seal) + left 2 photo cutouts + paperclip memo card.
- **`#D2` (`render_vox_scene_03_duality_collage` — Twin Angled Civilian Card `[A]` vs. Secret Dossier `[B]`)**: Two angled physical dossier boards on dark desk — left cream card `[A]` with teal header & 4-row table vs. right dark charcoal secret dossier `[B]` with crimson header, 4-row table & yellow rubber stamp + center `동일인 100%` badge.
- **`#D3` (`render_vox_scene_05_three_clues_dossier` — 35mm Kodak Film Strip + 3 Kraft Evidence Envelopes)**: Top `KODAK TRI-X PAN 400` 35mm film strip header with sprocket holes + 3 angled Kraft sealed evidence envelopes (`#01..#03`) with brass grommet tie holes, 16:9 photo windows & chain-of-custody cards + bottom metal-clipped summary bar.
- **`#D4` (`render_archetype_d4_ydna_lightbox` — Forensic Genetics Medical Lightbox + Pedigree)**: Backlit medical lightbox with millimeter grid + left dark panel showing 10-locus STR fluorescent cyan/red gel bands (`MATCH`) & `99.9999%` verdict box + right panel with lineage/verification diagram & 2 photo cutouts.
- **`#D5` (`render_archetype_d5_clipboard_interrogation` — Brushed Aluminum Clipboard Q&A + Voiceprint)**: Left brushed-aluminum clipboard with heavy metallic spring clip & 6-block Q&A confession transcript (with yellow highlighter sweeps) + right interrogation photo cutout & `REC` audio voiceprint waveform card.
- **`#D6` (`render_archetype_d6_wanted_warrant_sketch` — Red-Bordered Official Warrant / Indictment + Biometric Grid)**: Left-center red-bordered official warrant/indictment sheet with dual anthropometric grid photos, 4-row profile table & circular official seal + right paperclip memo card & photo cutout.
- **`#D7` (`crime_scene_blueprint` — Architectural Floorplan & Evidence Vectors)**: Forensic floorplan dossier with entry/exit vectors and evidence tags.
- **`#D8` (`age_progression_strip` — Chronological Suspect Comparison Strip)**: Multi-stage suspect profile comparison dossier on dark desk.
- **`#D9` (`render_archetype_d9_microscope_minutiae` — Dual-Ocular Circular Microscope Comparator)**: Dual circular microscope ocular viewports (`시료 [A]` vs. `시료 [B]`) linked by 6 red feature lines + center green `100.0% 일치` plaque.
- **`#D10` (`cold_case_cabinet` — Archival Case File Ledger)**: Open archival case folder ledger with official seals and evidence tags.

### Cluster C — 6 Archival Press & CRT Broadcast Archetypes (`#P1` – `#P6`)
- **`#P1` (`render_vox_scene_07_six_year_timeline` — Unfolded Newspaper Broadsheet + 7-Node Timeline)**: Unfolded newspaper broadsheet with fold creases, masthead, 7-node chronology timeline bar, highlighter headline, 2 embedded 16:9 photo boxes, and 2-column article with yellow/red highlighter sweeps.
- **`#P2` (`render_vox_scene_08_newspaper_panic` — Official Red Notice + 3 Angled Press Clippings)**: Left red-bordered official police/court notice + 3 overlapping angled newspaper clippings (`paste_pinned_newspaper_clipping`) + center-bottom photo cutout + paperclip memo card.
- **`#P3` (`render_archetype_p3_90s_tv_broadcast` — CRT TV Broadcast Monitor + VHS Log)**: Left `SONY TRINITRON` CRT monitor with scanlines, live station bug & breaking news chyron + right VHS capture photo cutout, paperclip broadcast log memo card, and red rubber stamp.
- **`#P4`..`#P6`**: Archival press, chronology montage, and court verdict notice variations built from `#P1`/`#P2`/`#P3`.
