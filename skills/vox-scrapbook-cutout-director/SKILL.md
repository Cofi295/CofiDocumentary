---
name: vox-scrapbook-cutout-director
description: "Flow-First RGBA Evidence Cutouts, Center Real-Footage Hero (Video Prioritized or Photo) & Surrounding Cutout Collage Skill (CofiStudioMediaFactoryRunner + rembg -> src/vox-studio/vox-editorial-desk/index.tsx + <GeoJson3DMapStage> — Priority #2 After Real Footage, 0% Camera Zoom, Context-Adaptive Entrance & Vocal Emphasis Motions)."
---

# Vox Scrapbook Cut-and-Paste & Precision Satellite Cartography Director (`vox-scrapbook-cutout-director`)

## 1. Strict 3-Tier Visual Priority (`0%` Fixed Template Count, `0%` Periodic Spacing)
1. **Priority #1 (`REAL_FTG`)**: Authentic archival case footage wherever verified real footage of the spoken sentence exists.
2. **Priority #2 (`VOX` — Mandatory When Real Footage Is Absent)**: Whenever a segment lacks authentic archival footage, it **MUST** use VOX illustration (`<Desk>` or `<GeoJson3DMapStage>`) as Priority #2 before considering AI imagery.
3. **Priority #3 (`AI_IMAGE` — Last Resort Only)**: AI-generated imagery is used strictly as the final fallback when neither real footage nor VOX illustration applies.

## 2. Mandatory 4-Step Flow-First + Center-Footage Tabletop Law (`src/vox-studio/vox-editorial-desk/index.tsx`)
1. **Step 1 — Read Sentence & Identify Exact Evidence (`100% Sentence-Specific`)**:
   - Read the spoken sentence (`voice_text`) and its clauses (`t1 -> t2 -> t3`) to identify the exact physical evidence, props, and archival scene described. Never reuse evidence from another sentence (`0%` mismatched props, `0%` decorative filler).
2. **Step 2 — Draw Evidence With Google Flow FIRST (`CofiStudioMediaFactoryRunner`) & Cut Out RGBA (`rembg`)**:
   - Before writing any VOX scene code, generate high-detail studio forensic macro images of the sentence's specific physical evidence via Google Flow (`CofiStudioMediaFactoryRunner`, isolated on a clean solid light warm cream background, zero text/watermarks), segment them into crisp RGBA cutouts (`rembg` -> `prop_XX.png`, `cutout_XX.png`), and inspect every PNG cutout via `read_file`.
   - Prepare clean archival case media (a clean cropped video clip `video_XX.mp4` when available, or a clean archival case frame `plate_XX.jpg`) cropped 100% free of logos/subtitles.
   - **STRICTLY FORBID** fake PIL geometric drawings, repeated SVG diagram boxes (`<BespokeSentenceDiagramByIndex>` / `renderSentenceIllustrationSvg`), or 4-corner curls (`<PaperCurlCorners>`).
3. **Step 3 — Canonical 1920x1080 Tabletop Layout: Real Footage Video or Photo in Center (Priority to Video) + Cutout Evidence Around**:
   - **Dead-Center Real Footage Hero (`Center Hero Video or Photo — Priority to Video`)**: Keep the exact current style and layout — place 1 large real archival case media hero in the center (`w = 620..660, h = 395..420`, centered at `left = 620..665, top = 200..235`). **This center hero can be EITHER a Real Footage Video OR a Real Footage Photo, with PRIORITY given to Real Footage Video (`<VoxVideoPaper>`, `<VoxPhotoPaper videoSrc={...}>`, or `<RedBackedTornPhoto videoSrc={...}>`) whenever a clean video clip is available**, falling back to a photo (`<VoxPhotoPaper>` or `<RedBackedTornPhoto>`) when only still media exists.
   - **Surrounding 4-Corner Flow Cutouts & Notes (`Surrounding Cutout Evidence`)**: Arrange cleanly around the center hero (top-left `left: 64..106, top: 38..60`, bottom-left `left: 64..106, top: 505..545`, top-right `left: 1350..1360, top: 38..60`, bottom-right `left: 1350..1385, top: 505..565`) consisting of:
     * **2 large RGBA Flow cutout props** (`<DieCutSticker src={propAsset('prop_XX.png')} w={450..465} h={330..335} />` and `<DieCutSticker src={propAsset('cutout_XX.png')} w={445..460} h={325..335} />`).
     * **1 concise target-language note card / clipping / tag** (`<IndexCard>`, `<TornClipping>`, `<TornPostageStrip>`, `<EyeletArchiveTag>`, `<Label>`, `fontSize: 20..24`, `0%` English boilerplate).
     * **1 classification stamp** (`<Stamp text="..." size={36} />`).
   - **Zero Overlap & Safe Bounds**: Never overlap the center video/photo, faces, or text; keep all elements inside `[60..1860, 38..845]`.
4. **Step 4 — `0%` Camera Zoom & Context-Adaptive 12fps Entrance / Vocal Emphasis Choreography (`t1 -> t2 -> t3`)**:
   - Keep `<Desk>` (`#E4DDCF` + `#voxGrain` `opacity: 0.22`, optional `<ManilaKraftBoard inset={42} />` or `<BlackCard inset={38} />` `#1B1B1A`) and `<World>` 100% locked overhead (`z = 1.0`, `transform: 'none'`, `0%` camera zoom-in or zoom-out).
   - **Context-Adaptive Entrance Motions & Vocal Emphasis**: Customize the entrance order/timing (`at={0}`, `t1`, `t2`, `t3`), 12fps `<SlideIn from="...">` cut-and-paste directions (`left`, `right`, `top`, `bottom`, `scale`, `scissors_slide_left`, `scissors_slide_right`, `slap_drop_top`, `sticker_peel_up`, `unroll_scroll_down`, `accordion_fold_left`, `accordion_fold_right`, `diagonal_toss_spin`, `fan_deal_bottom`), and focal emphasis tools (`<RedCircle>` when pointing out a target, `<OpticalLoupe>`, `<TwistedRedYarn>`, `<RedLine>`, `<DimensionBracket>`, `<Highlight>`, `<Underline>`, `<Stamp>`) flexibly according to the context and how each spoken voice sentence emphasizes different points.

## 3. Precision 3D Satellite Cartography Law (`<GeoJson3DMapStage>`)
- Attach `<GeoJson3DMapStage>` **ONLY** to sentences describing a physical movement/escape/infiltration route of the suspect OR a dispatch/dragnet/stakeout/extradition route of the police (`0%` periodic placement).
- Lock every pin and `satLoupe` to exact real-world `[lon, lat]` WGS84 coordinates (`0.00px` drift) on verified 0%-black-tile Esri satellite plates (`>= 3072x2048`), with authentic `>= 12..40`-vertex road/rail polylines, clear directional arrows, and frameless labels.
