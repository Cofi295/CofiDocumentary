---
name: cofi-thumbnail-designer
description: Specialist skill for designing high-CTR YouTube documentary & True Crime thumbnails (1280x720) in CofiDocumentary using the Fabric.js JSON Layer Canvas engine, Google Labs Flow clean base images, Korean broadcast typography (그것이 알고싶다 / 꼬꼬무), and NanoThumbnail YouTube Safe-Zone & Mobile CTR critique rules.
---

# COFI Thumbnail Designer Skill (Fabric.js Layer Engine + NanoThumbnail Craft)

Use this skill whenever designing, critiquing, or updating YouTube thumbnails in **COFI DOCUMENTARY** (Phase `seo` or via AI Chat requests on Tab `SEO + Thumbnail`).

---

## 1. Core Architectural Rule: Clean Base Image + Vector Layer Composition

Never rely on raw AI image generators to bake long Korean (`중국 실화 사건`), Vietnamese, or English headlines directly into pixels—baked pixel text warps Hangul strokes, breaks channel font consistency, and cannot be dragged or edited by the user.

Instead, COFI DOCUMENTARY uses a **2-Layer Production Architecture**:
1. **Layer 0 — Clean Base Image (`thumbnail_bg.jpg` via Google Labs Flow or Project Scenes)**:
   - Aspect Ratio: `16:9` (`1280×720`).
   - Prompt Rule: **NO TEXT IN BASE IMAGE** (`no text, no letters, no typography, no watermark, no logos`).
   - Composition Rule: Intentionally reserve **35%–50% Negative Space** (darkened shadow area, blurred depth-of-field wall, night sky, or interrogation room shadow) on the left or bottom so the vector typography layers achieve 100% legibility.
2. **Layers 1..N — Programmable JSON Canvas (`thumbnail_design.json`)**:
   - Rendered by the in-app **Fabric.js-compatible Layer Studio** (`static/thumbnail_studio.js`) and exported to `workspace/thumbnail.jpg` (`1280×720`, `< 2MB`).
   - Every visual overlay (`vignette`, `badge`, `line_1`, `line_2`, `forensic_arrow`, `forensic_circle`, `evidence_stamp`, `inset_photo`) is an independent, draggable, resizable JSON object.

---

## 2. Proven YouTube Documentary & True Crime Archetypes (from NanoThumbnail + Korean Broadcast DNA)

Choose one of these 5 high-CTR archetypes for each variant in `thumbnail_design.json`:

### A. `broadcast_left_heavy` (SBS `그것이 알고싶다` Standard — Recommended Default)
- **Subject Placement**: Right third (`x: 680..1240`), close-up or medium-close suspect/investigator/scene.
- **Vignette**: Heavy dark gradient from left (`x: 0..820`, opacity `0.78–0.88`).
- **Typography Placement**: Left-aligned (`left: 64`), vertically centered (`top: 190..540`).
  - **Badge**: `[중국 실화 사건]` or channel series key (`fill: #dc2626`, text `#ffffff`, `top: 185`).
  - **Line 1 (Setup / Context)**: White `#ffffff` with heavy black stroke (`strokeWidth: 14`), `fontSize: 68–76`.
  - **Line 2 (Shock / Curiosity Hook)**: Vivid Yellow `#fbbf24` or Crimson `#ef4444` with heavy black stroke (`strokeWidth: 16`), `fontSize: 78–88`.

### B. `bottom_cinematic` (SBS `꼬꼬무` / Cinematic Scene Standard)
- **Subject Placement**: Upper 65% of frame (`y: 0..480`), dramatic wide or dual-character confrontation.
- **Vignette**: Deep bottom-up gradient (`y: 300..720`, opacity `0.85`).
- **Typography Placement**: Centered or left-aligned in the lower third (`y: 410..635`), strictly keeping `bottom >= 75px` away from the bottom-right YouTube timestamp (`30:15`).

### C. `split_duality` (Two Faces / 28-Year Disguise vs. Arrest)
- **Visual Structure**: Main background shows crime scene or interrogation room; a **Picture-in-Picture (`inset_photo`)** frame at top-right (`left: 830, top: 48, width: 380, height: 340`) with a white/red border shows the contrasting disguise or evidence photo.
- **Typography**: Left-heavy hook highlighting the contradiction (e.g., `"낮에는 학교 매점 주인"` / `"밤에는 연쇄살인범"`).

### D. `evidence_spotlight` (Forensic Clue & Red Circle/Arrow)
- **Visual Structure**: Darker overall vignette (`0.65`) with a **Forensic Red Circle (`forensic_circle`)** and **3D Red Arrow (`forensic_arrow`)** pointing directly at the decisive clue (fingerprint, hidden drawer, CCTV silhouette, or structural flaw).
- **Stamp**: Optional top-left or top-right slanted stamp `[극비 수사]` / `[미제 사건]` / `[HỒ SƠ MẬT]`.

### E. `right_heavy_confrontation` (Left Subject Looking Right)
- **Subject Placement**: Left third (`x: 40..540`), subject facing right toward the text.
- **Typography Placement**: Right two-thirds (`left: 480..1210, top: 150..500`), positioned high enough (`bottom <= 610`) to completely clear the YouTube duration badge (`x: 1060..1260, y: 630..705`).

---

## 3. YouTube Safe Zones & Mobile 120px Critique Rubric (NanoThumbnail Standard)

Before finalizing `thumbnail_design.json`, verify all 4 checks:

1. **YouTube Timestamp Safe Zone (`x: 1060..1260, y: 630..705`)**:
   - Never place the end of `line_2` or key facial features inside the bottom-right corner where YouTube renders `30:12`.
2. **Watch Later / Hover Safe Zone (`x: 1180..1265, y: 15..110`)**:
   - Keep top-right badges/stamps at least `60px` inset or place stamps on the top-left/center-right.
3. **3-Element Limit**:
   - Maximum 3 visual groups: (1) Main Subject/Scene, (2) Hook Text Stack (Badge + 2 Lines), (3) At most 1–2 Forensic Accents (Arrow/Circle/Inset). Never clutter with 5+ small boxes.
4. **Mobile Feed Legibility (120px–160px width test)**:
   - Keep `line_1` + `line_2` concise (ideally 2–5 Korean words per line, ≤ 14 characters per line).
   - Contrast: White (`#ffffff`) + Yellow (`#fbbf24`) or Red-Orange (`#f97316` / `#ef4444`) over `#000000` stroke (`14–16px`) and dark vignette (`>= 0.72` opacity).

---

## 4. API & Workspace Operations for AI Agent

When working inside COFI DOCUMENTARY, you can inspect and control the Thumbnail Studio via HTTP API (`http://127.0.0.1:8878`):

- `GET /api/jobs/{job_id}/thumbnail-studio` — Read current `thumbnail_design.json`, candidate background images from the project, and CTR critique.
- `POST /api/jobs/{job_id}/thumbnail-studio/auto-design` — Automatically build/refresh the 4 layer variants from `seo_package.json` (`{"archetype": "broadcast_left_heavy", "instruction": "..."}`).
- `POST /api/jobs/{job_id}/thumbnail-studio/generate-bg` — Generate a clean 16:9 base image (`thumbnail_bg.jpg`) using the app's integrated Google Labs Flow engine (`{"prompt": "..."}`).
- `POST /api/jobs/{job_id}/thumbnail-studio/design` — Save custom edits to `thumbnail_design.json` (layers, text, colors, positions, forensic arrows/circles).
- Or use host action `{"type": "design_thumbnail", "job_id": "...", "variant_index": 0, "archetype": "broadcast_left_heavy", "generate_bg": false}` in Producer Chat.
