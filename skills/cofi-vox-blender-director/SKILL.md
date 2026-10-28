---
name: cofi-vox-blender-director
description: Specialist skill for directing True Crime (`channel-e544a64b7c` · 특급수배록) & Cyber-Financial Investigative (`channel-cn-cyber-finance-kr`) Documentary edits for 45–70+ mature Korean audiences using Full-Script-Driven Visual Direction, strictly separating Approved True Crime Tactile Paper-Craft/Forensic Dossier/Newspaper/Satellite GIS Vox (`#D1..#D10`, `#M1..#M8`, `#P1..#P6`, `N1..N4 / E1..E6 / S1..S4`) from Cyber-Finance Vox.
---

# COFI Full-Script-Driven Documentary, Approved True Crime Tactile Forensic/Newspaper/Satellite Vox & Cyber-Finance Vox Director Skill

Use this skill when planning, routing, editing, or rendering **Documentary / True Crime / Cyber-Financial Investigative** visuals and timelines in **COFI DOCUMENTARY** (`b:\ALL_TOOLS\CofiDocumentary`), **COFI BLENDER STUDIO** (`b:\ALL_TOOLS\CofiBlenderStudio`), or **COFI REMOTION** (`b:\ALL_TOOLS\CofiRemotion`).

---

## 0. Mandatory Core Architecture: Read Full Script First & Strict Profile Separation

1. **Upfront 1-to-1 Full AI Keyframe Generation (Step 5)**:
   - Every beat in `visual_manifest.json` receives its own dedicated 1-to-1 AI keyframe (`<beat_id>_ai_keyframe.jpg`, **4D Faceless Forensic**) generated upfront at Step 5 (`ai_visual`), while Step 4 (`footage`) is automatically skipped so all visual assembly happens holistically at Step 6 (`edit`).
   - Because each AI image is generated specifically for its own beat from the start, **never copy an AI image from one beat onto another beat** (`max_uses = 1`).

2. **Step 6.1 — Read Full Script & Synthesize Master Plan (`Read Full Script First`)**:
   - Read the entire `script.md`, `voice_manifest.json`, and `visual_manifest.json` from start to finish first.
   - Classify every beat across the full episode into 3 harmonious layers:
     - **Priority 1 — Authentic Case Footage + Reasonable Illustrative B-Roll (`footage/S_F*.mp4` + `archival/S_A*.jpg`, ~50% — STRICT 3–6s CUTS, 100% LOGO/CHINESE-TEXT CROPPING, ZERO PRESENTERS/HOSTS)**:
       1. **3–6 Seconds Per Footage Cut (`3–6s/cut`)**: Slice every footage clip strictly to **3–6 seconds** (`scdet=threshold=14`). When a voice beat lasts 7–12 seconds, pair **2 distinct 3–6s footage cuts (`Part A + Part B`)** so no single footage shot holds longer than 6 seconds.
       2. **Mandatory Logo & Chinese/Foreign Text Removal / Aggressive Safe-Crop**: Aggressively crop (`crop` + `scale=1920:1080`) or clean 100% of third-party TV station logos (`CCTV`, `CTI 中天新聞`, `必PO`, `SBS`, `KBS`, YouTube channel watermarks), top news banners, side graphic panels, and bottom burned-in Chinese/foreign subtitles/tickers.
       3. **Zero News Anchors / Zero Channel Hosts**: Strictly reject any shot showing a TV news anchor, studio presenter, commentator, or another channel's host (including split-screen presenter boxes). Every video clip is used once (`max_uses = 1`, `-an`).
     - **Priority 2 — Scene-Locked 1-to-1 AI Keyframes (`<beat_id>_ai_keyframe.jpg`, ~20%)**: Where real case footage is unavailable or the spoken sentence reconstructs unwitnessed actions/psychology, use that beat's pre-generated `<beat_id>_ai_keyframe.jpg` (`max_uses = 1`).
     - **Priority 3 — Profile-Locked Vox & Map Motion (`vox/VOX_01..VOX_N.mp4`, ~30%)**: Route and render Vox strictly according to the active channel profile (`channel-e544a64b7c` True Crime vs `channel-cn-cyber-finance-kr` Cyber-Finance). **NEVER mix Cyber-Finance dark-HUD rules into True Crime (`channel-e544a64b7c`)!**

---

## 1A. APPROVED TRUE CRIME VOX SYSTEM (`channel-e544a64b7c` · 특급수배록 — `forensic_noir`)

For **True Crime Hình Sự Trung Quốc (`channel-e544a64b7c` · 특급수배록)**, you MUST use the user's **Approved True Crime Tactile Paper-Craft, Manila Forensic Dossier, Archival Newspaper Highlighter & Real Esri Satellite GIS Vox System** built in `b:\ALL_TOOLS\CofiBlenderStudio` (`vox_editorial_artist.py`, `vox_archetype_expansion.py`, `vox_papercraft_artist.py`) and `documentary/vox_engine` (`archetypes.py`, `semantic_router.py`, `renderer.py`):

### Group 1: Tactile Manila Forensic Dossiers, Biometrics & Evidence Boards (`#D1..#D10` & `E1..E6`)
- **`#D1` — Case Dossier Folder & Verification Matrix (`render_vox_scene_01_fingerprint_paradox`)**:
  Open tactile Manila case folder on a dark walnut desk with torn-edge evidence photos pinned by red pushpins, fingerprint/CCTV/trace verification matrix (`확보된 현장 지문 vs 230,000장 전수 대조` / `신분증·은행·숙박 0건`), official circular red Public Security seal (`공안국`), and paperclipped investigator memo.
- **`#D2` — Dual Identity / Suspect-Victim Case Profile Dossier (`render_vox_scene_03_duality_collage` / `E2_DUAL_COMPARE_BOARD`)**:
  Two-column profile comparison dossier (`민간 신상 카드 [A]` vs `극비 수사 기록 [B]`) with brass fasteners, archival newspaper clipping, and red official stamp.
- **`#D3` — Three Physical Clues & Kodak Film Strip Evidence Envelopes (`render_vox_scene_05_three_clues_dossier`)**:
  Three kraft evidence envelopes (`물증 봉투 #01 · #02 · #03`) with 35mm Kodak film strip borders, red forensic seals, and investigator summary box.
- **`#D4` — Forensic Genetics Y-STR DNA Lightbox & Pedigree (`render_archetype_d4_ydna_lightbox`)**:
  Illuminated electrophoresis DNA band comparator + paternal clan pedigree tree (`99.9999% 일치`).
- **`#D5` — Aluminum Clipboard Interrogation Q&A + REC Voiceprint (`render_archetype_d5_clipboard_interrogation` / `E5_INTERROGATION_DOSSIER`)**:
  Brushed aluminum clipboard holding typed Q&A interrogation transcript (`피의자 심문조서 녹취록 발췌`) with live red audio waveform (`REC · 심문실 음성 녹취 파형`).
- **`#D6` — Class-A Red Wanted Warrant & Police Sketch Comparator (`render_archetype_d6_wanted_warrant_sketch`)**:
  Official Ministry of Public Security Class-A Red Wanted Warrant (`중화인민공화국 공안부 A급 특별수배령 · 현상금`) with red seal, witness sketch vs arrest/CCTV photo comparison, and physical traits dossier.
- **`#D7` / `#D9` — Optical Comparator Microscope: Ballistics Striations & 14-Point Fingerprint Minutiae (`render_archetype_d9_microscope_minutiae`)**:
  Split-field optical microscope comparing shell-casing striations (`탄피 강선 흔적`) or 14 fingerprint minutiae points (`14/14 일치`) alongside tactile forensic lab notes.
- **`#D8` / `#D10` / `E1..E6`**:
  Medical examiner autopsy dossier (`#D8`), cold-case archive vault box (`#D10`), official court verdict scroll with red seal (`E1_COURT_VERDICT_SCROLL`), document/blueprint inspector (`E3_PATENT_DOCUMENT_INSPECTOR`), progressive chronological timeline (`E4_TIMELINE_PROGRESSION`), and red-string network board (`E6_OFFICIAL_NETWORK_BOARD`).

### Group 2: Real Esri Satellite & GIS Maps (`#M1..#M8` & `S1..S4`)
- **`#M1` — High-Res Real Esri Satellite + Zoom ×16/×18 Circular Magnifying Loupe (`render_vox_scene_02_school_store_map`)**:
  Real Esri World Imagery satellite plate with animated circular magnifying loupe (`ZOOM ×16`), GPS coordinate crosshair, and pinned crime-scene photos.
- **`#M2` — Regional Satellite Corridor & Torn Newspaper Clipping (`render_vox_scene_04_gansu_baiyin_gis`)**:
  Regional satellite/terrain corridor (`Z6/Z9/Z14`) with progressive perimeter drawing and torn archival newspaper card.
- **`#M3` — Administrative Boundary & Surveillance Blindspot GIS (`render_vox_scene_06_hukou_blindspot_gis`)**:
  Jurisdiction/Hukou blindspot or CCTV perimeter ring comparison on real satellite imagery.
- **`#M4` — Detective Cork Pinboard & Red-String Crime Cluster Map (`render_vox_scene_08_1998_four_cases_map`)**:
  Multi-incident satellite map with numbered pins (`① -> ② -> ③ -> ④`), red string connections, and pinned case log.
- **`#M5` — 2.5D Tilted Satellite Geo-Profiling Slab (`render_archetype_m5_25d_tilted_satellite`)**.
- **`#M6` — Split Dual Satellite Macro vs Micro (`render_archetype_m6_split_dual_satellite`)**.
- **`#M7` — Night-Ops Infrared Satellite Perimeter (`render_archetype_m7_night_ops_satellite`)**.
- **`#M8` — Topographic Elevation Profile & Escape Corridor**.
- **`S1_KUNMING_SATELLITE_MAP` / `S2_DUAL_SATELLITE_ROUTE` / `S3_FULLSCREEN_GIS_FLIGHT` / `S4_FULLSCREEN_SATELLITE_RECON`**:
  Smooth `A -> B` camera flight across real satellite/terrain plates, progressive yellow route drawing (`0% -> 100%`) with moving radar beacon, sequential pin pop-in (`① -> ② -> ③`), live video PiP in torn paper frame, and bottom clause-synced highlighter card.

### Group 3: Tactile Archival Newspaper & Broadcast Press (`#P1..#P6` & `N1..N4`)
- **`#P1` / `#P2` / `N1_FRONT_PAGE_SPECIAL` / `N2_INVESTIGATIVE_SPREAD` / `N3_EDITORIAL_CHRONICLE` / `N4_BROADCAST_PRESS_ARCHIVE`**:
  Warm, senior-friendly (45–70yo) aged newsprint backdrop (`NEWSPRINT_LIGHT #F5EFE2`) with Korean masthead, torn-edge live video/archival photo cards (`paste_soft_torn_photo_card`), and **voice-synced yellow felt-pen highlighter sweep (`HIGHLIGHT_YELLOW #FDE047`)** across each spoken clause + window gobo shadow (`apply_window_gobo_and_vignette`).
- **`#P3` — 1990s/2020s TV Broadcast Monitor & Behavioral Analysis (`render_archetype_p3_90s_tv_broadcast`)**.

> **CRITICAL BAN FOR TRUE CRIME (`channel-e544a64b7c`)**: NEVER use dark-navy neon Cyber-Finance HUD boxes (`#090e1c` cards) for True Crime! Always use the tactile paper-craft, Manila forensic dossier, archival newspaper, and real Esri satellite GIS styles above.

---

## 1B. CYBER-FINANCE VOX SYSTEM (`channel-cn-cyber-finance-kr` — `financial_forensic_vox` ONLY)

For **Tội phạm Công nghệ cao & Tài chính Trung Quốc (`channel-cn-cyber-finance-kr`) ONLY**, design bespoke financial ledgers, crypto wallet graphs, Ponzi flow diagrams, and cross-border money trail maps matched 1-to-1 to each spoken financial sentence.

---

## 2. Dynamic Context-Matched 28+ Real Foley SFX & Multi-Mood BGM (`documentary/audio_library_manager.py`)

1. **Context-Driven, Non-Repetitive Foley SFX Selection (`presets/audio_library/sfx/` & `public/audio_library/sfx/`)**:
   - Every beat selects context-accurate real Foley SFX matched to the exact physical action, environment, and emotional tone of that beat (`select_contextual_sfx_for_beat()` in `documentary/audio_library_manager.py`).
2. **Multi-Mood Chapter BGM Switching & 3.8s Outro Tail**:
   - Schedule 5+ distinct mood-matched BGM beds across the episode's 5 narrative acts (`ACT01..ACT05`) and preserve a 3.5–4.0s BGM fade-out after the final spoken sentence.
