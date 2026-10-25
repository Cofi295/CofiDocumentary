---
name: cofi-vox-blender-director
description: Specialist skill for directing True Crime & Investigative Documentary edits for 45–70+ mature Korean audiences using the Flexible Script-Driven Visual Mix (~50% Real Footage + ~30% Senior-Friendly Voice-Synced Editorial Newspaper, Court Dossier, Split-Map & Full-Screen Map Vox Motion + ~20% Scene-Locked AI Keyframes) and Dynamic Context-Matched Real Foley SFX & Multi-Mood BGM.
---

# COFI Senior-Friendly Editorial Vox, Real Satellite GIS & Documentary Director Skill

Use this skill when planning, routing, editing, or rendering **Documentary / True Crime / Investigative** visuals and timelines in **COFI DOCUMENTARY** (`b:\ALL_TOOLS\CofiDocumentary`) or **COFI REMOTION** (`b:\ALL_TOOLS\CofiRemotion`).

---

## 0. Mandatory Core Principle: Lore & DNA Is a Flexible Foundation — NEVER Be Lazy or Repetitive

1. **Lore / Editing DNA Is a Creative Foundation, NOT a Rigid Cookie-Cutter Mold**:
   - Never lazily repeat 1–2 Vox templates across a video or copy-paste a static formula across future episodes.
   - The channel's Editing DNA defines our **quality bar, senior-friendly readability (`45–70+` mature Korean viewers), and voice-sync discipline**, while the actual Vox layouts, map presentations (`Full-Screen 1920x1080 Map Flight` vs. `Split Editorial Map Card`), motion choreography, Foley SFX, and BGM must be **flexibly adapted to each episode's unique subject matter and each beat's spoken voiceover**.
   - Before rendering any episode, analyze the script's specific geography, historical eras, legal/scientific mechanisms, and emotional chapters, and dynamically design/extend the Vox layouts, GIS plates, and audio library (`documentary/audio_library_manager.py`) to fit that story 100%.

---

## 1. Script-Driven Visual Mix & Semantic Routing

1. **Voice-Driven Semantic Routing**:
   - Route each beat according to the meaning of its spoken voiceover (`narration_text`), maintaining an organic episode balance of **~50% Real Footage + ~30% Voice-Synced Editorial Newspaper, Court Dossier & Satellite/GIS Map Vox Motion + ~20% Scene-Locked AI Keyframes** (with `~10%` flexible adaptation to the script):
     - **~50% Real Footage (`footage/S_F*.mp4` + authentic archival stills `archival/S_A*.jpg`)**: Used when the voiceover describes real events, arrests, courtrooms, nightclubs, prisons, investigations, or historical locations. Slice clean B-roll video into brisk `3–6s` cuts with edge-cropping, muted source audio (`-an`), unified color grading, and smooth optical camera movement (`1.005 -> 1.065`). Each real footage clip has `max_uses = 1` in standard full-screen view, and purposeful narrative callbacks use transformative framing (`Split-Screen Comparison A/B`, `Forensic PiP Window`, or `160% Macro Loupe`).
     - **~30% Voice-Synced Editorial Newspaper, Court Dossier & Real Satellite/GIS Map Vox Motion (`vox/VOX_*.mp4`)**: Used when the voiceover discusses newspaper reports, court verdicts, legal documents, patents, chronological timelines, suspect networks, or geographic locations/routes.
     - **~20% Scene-Locked AI Keyframe Illustrations (`<beat_id>_ai_keyframe.jpg`)**: Used when the voiceover describes unwitnessed historical reconstructions, private interactions, or psychological moments.
       * **1-to-1 Scene Lock**: Each `<beat_id>_ai_keyframe.jpg` belongs exclusively to its own `<beat_id>`.
       * **Pure Scene Focus**: AI image prompts describe the physical scene, characters, environment, lighting, and action in a full-bleed 16:9 frame.

---

## 2. Flexible Senior-Friendly (45–70yo) Voice-Synced Editorial & Map Vox (`vox/VOX_*.mp4`)

1. **Calm, High-Contrast, Voice-Synced Newspaper, Dossier & Map Choreography (30fps `.mp4`)**:
   - Design every Vox clip specifically for **mature viewers aged 45–70+**, prioritizing visual clarity, effortless readability, calm motion, and 100% synchronization with the spoken Korean voiceover:
     - **100% Beat-Specific Voice-Synced Korean Typography**: Display the exact clauses of that beat's voice narration in large, bold, high-contrast Korean typography (`32–42px`) on warm editorial newsprint or court dossier cards, accompanied by a 2-sentence context window (`prev_text` in muted ink above, `narration_text` with progressive yellow highlight `0% -> 100%` in the center, and `next_text` below).
     - **Chronological Era & Entity Lock**: Every Vox clip's masthead year, timeline node, document exhibit, and live video inset (`S_F*.mp4`) must strictly match the exact historical year and institution spoken in that beat (never leak future verdicts or later-era evidence into earlier chronological chapters).
     - **Clean, Soft-Torn Live Moving Video & Archival Photo Frames**: Embed live 30fps video footage (`S_F*.mp4`) and authentic court/archival documents inside clean rectangular photo frames with gentle soft-torn paper borders (`roughness <= 2.5`) and soft drop shadows.
     - **Calm 30fps Documentary Camera Glide**: Use gentle, smooth 30fps camera pans and slow pushes (`1.00 -> 1.022`) across **14+ flexible layouts** (`N1..N4` Newspaper Editions, `E1..E6` Court Verdicts, Dossiers, Patents, Networks & Timelines, `S1..S2` Split Satellite/GIS Route Cards, and `S3..S4` Full-Screen `1920x1080` GIS/Satellite Map Flights) with zero flash/flicker transitions.

2. **Flexible Map Presentation: Full-Screen `1920x1080` Map Flight vs. Split Editorial Map Card**:
   - Never force every map into a small card if the narrative calls for a sweeping geographical view. Dynamically choose between **Full-Screen Map Mode** and **Split Editorial Map Mode** based on the beat's content:
     - **Full-Screen `1920x1080` Map Flight & Recon (`S3_FULLSCREEN_GIS_FLIGHT` / `#V_FULLSCREEN_GIS_FLIGHT` & `S4_FULLSCREEN_SATELLITE_RECON` / `#V_FULLSCREEN_SATELLITE_RECON`)**:
       * Use when the voiceover emphasizes macro national/provincial dispatches (e.g., Beijing ↔ Yunnan), inter-prison transfers, or city-wide urban satellite reconnaissance.
       * Renders a full-bleed `1920x1080` regional terrain/GeoJSON map or high-resolution urban satellite map (`z15–z16`) with a top telemetry masthead, a floating Picture-in-Picture live video window (`vid_a`) in the top-right, and a floating bottom Korean voice-synced highlighter bar.
     - **Split Editorial Map Card (`S1_KUNMING_SATELLITE_MAP`, `S2_DUAL_SATELLITE_ROUTE`)**:
       * Use when the voiceover cross-examines a geographic movement directly against a court ruling, prison evaluation record, or newspaper exposé.
   - **Mandatory Voice-Synced Map Motion (Zero Static Maps)**:
     - **Smooth `A → B` Camera Flight**: Continuously pan and zoom the map camera from Origin Point A toward Destination Point B across the beat's duration (`seq_p: 0.0 -> 1.0`).
     - **Progressive Route Drawing & Moving Radar Beacon**: Draw the route line or flight arc progressively from `0% -> 100%` (`route_p`) with a live moving leading-edge beacon (`head_xy`) and expanding radar pulse ring.
     - **Sequential Pin Pop-In & Non-Overlapping Labels**: Pop in numbered location pins (`① 출발 거점` at `t=0.0`, `② 경유/심사 거점` at `t=0.36`, `③ 도착/현장 거점` at `t=0.60`) sequentially as the route reaches each point, alternating pill placement (`①` above, `②` below, `③` above) with expanding radar ripple rings so labels never collide or clip.
   - Encode every `VOX_*.mp4` clip with hardware-friendly fast-decode H.264 (`-c:v libx264 -preset fast -crf 21 -maxrate 6M -bufsize 12M -g 30 -bf 0 -pix_fmt yuv420p -movflags +faststart`) for rock-solid 30fps playback in Remotion Studio via `@remotion/media`.

---

## 3. Dynamic Context-Matched 28+ Real Foley SFX & Multi-Mood BGM (`documentary/audio_library_manager.py`)

1. **Context-Driven, Non-Repetitive Foley SFX Selection (`presets/audio_library/sfx/` & `public/audio_library/sfx/`)**:
   - Never repeat the same 1–2 SFX mechanically across a video. Every beat must select context-accurate real Foley SFX matched to the exact physical action, environment, and emotional tone of that beat (`select_contextual_sfx_for_beat()` in `documentary/audio_library_manager.py`):
     - **Judicial, Verdict & Execution**: Courtroom wooden gavel strike (`sfx_gavel_hit.mp3`), official ink stamp (`sfx_dossier_stamp.mp3`), heavy institutional seal thud (`sfx_official_seal_thud.mp3`), solemn bronze bell toll (`sfx_court_bell_toll.mp3`).
     - **Prison, Custody & Secret Transfer**: Heavy prison iron gate (`sfx_cell_door.mp3`), metallic lock latch / handcuff click (`sfx_iron_lock_latch.mp3`), stone corridor footsteps (`sfx_footsteps_corridor.mp3`).
     - **Press, Newspaper & Archival Dossier**: Broadsheet newspaper unfold (`sfx_newspaper_unfold.mp3`), crisp archival page turn (`sfx_paper_turn.mp3`), felt-pen marker highlighter swipe (`sfx_highlighter_swipe.mp3`), case folder open (`sfx_folder_open.mp3`).
     - **Satellite, GIS Map & Trajectory Flight**: Tactical radar/sonar ping (`sfx_radar_ping_sonar.mp3`), cartographic camera route sweep (`sfx_map_route_sweep.mp3`), orbital pin lock beep (`sfx_satellite_lock_beep.mp3`), telemetry counter tick (`sfx_telemetry_tick.mp3`).
     - **Forensics, Biometrics & Police Taskforce**: Biometric fingerprint/DNA match chime (`sfx_biometric_match_chime.mp3`), optical document scanner hum (`sfx_document_scanner_hum.mp3`), police radio dispatch chirp (`sfx_police_radio_chirp.mp3`), evidence camera shutter (`sfx_camera_shutter.mp3`), mechanical investigation log typing (`sfx_typing_log.mp3`), analytical node ping (`sfx_data_ping.mp3`).
     - **Chronology & Emotional Transitions**: Tense analog clock ticking (`sfx_clock_tick_tense.mp3`), warm somber chime (`sfx_somber_chime.mp3`), gentle card whoosh (`sfx_soft_whoosh.mp3`), chapter transition hit (`sfx_chapter_hit.mp3`).

2. **Multi-Mood Chapter BGM Switching & Dynamic Online Audio Stocking**:
   - Never loop a single static BGM track for an entire documentary. Schedule 5+ distinct mood-matched BGM beds across the episode's narrative acts (`select_chapter_bgm_schedule()`):
     - **Act I (Mystery Hook & Paradox)**: `bgm_emerging_mysteries.mp3`
     - **Act II (Dark Crime, Victims & Fear)**: `bgm_gathering_darkness.mp3`
     - **Act III (Institutional Collusion, Bribery & Paper Trails)**: `bgm_investigative_bed.mp3`
     - **Act IV (Forensic Pursuit, Biometric Match & Central Taskforce)**: `bgm_forensic_pulse.mp3`
     - **Act V (Supreme Court Reckoning, Execution & Epilogue)**: `bgm_dark_ambient_drone.mp3`
   - When a future documentary episode introduces a new setting or emotional atmosphere that requires additional specialized SFX or BGM, automatically invoke `fetch_missing_audio_asset(query, target_filename, category)` in `documentary/audio_library_manager.py` to download, normalize, and stock new CC0/open-licensed audio into `presets/audio_library/` and `public/audio_library/`.
