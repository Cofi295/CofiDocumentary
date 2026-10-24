# Detailed Architectural Analysis: R3 & AC3 — Channel Thumbnail Design DNA & Thumbnail A/B Testing Studio

**Agent**: `explorer_survey_3`  
**Date**: 2026-10-19  
**Parent**: `orchestrator_2` (`a13450b0-84a5-4e72-ae6f-8fd9f0ed17c4`)  
**Scope**: Requirement R3 & AC3 + R4 in `ORIGINAL_REQUEST.md` (Follow-up 2026-10-19T19:03:29Z)

---

## 1. Executive Summary

This investigation explores the backend services, persistence schemas, UI components, and test suites across `CofiDocumentary` to establish how to implement:
1. **Persistent Channel Thumbnail Design DNA (`thumbnail_dna`)**: A structured visual thumbnail identity stored on each Channel Profile (`data/channel_profiles.json`), inherited by all projects created on that channel, and updatable via a one-click "Lưu & Khóa DNA Thumbnail Kênh" action in Step 0 and Step 07.
2. **Step 07 Thumbnail A/B Testing Studio**: Upgrading Step 07 (`SEO + Thumbnail`) to generate and manage **3 distinct A/B/C test variants** adhering to the channel's DNA while testing 3 proven psychological click angles:
   - **Variant A**: Curiosity / Paradox / Shocking Number Hook
   - **Variant B**: Character / Forensic Evidence Close-Up / Emotion Hook
   - **Variant C**: Confrontation / Dual-Contrast Before-After / Mystery File Hook
3. **A/B CTR Prediction & Readiness Scores**: Evaluating DNA consistency, text legibility / word count, emotional curiosity gap, and keyword alignment.
4. **Feed Preview & Export Pack**: YouTube Home / Sidebar feed preview modes, primary winner selection, and A/B/C Test Pack export for YouTube Studio native *"Test & Compare"*.

---

## 2. Codebase Investigation Findings

### 2.1 Channel Profile Persistence & `thumbnail_dna` Schema

- **Current State in `data/channel_profiles.json`**:
  - The 4 active channel profiles are:
    1. `channel-e544a64b7c`: 특급수배록 · True Crime Hình Sự Trung Quốc (KR · 30 Phút · Full AI)
    2. `channel-1e24de3ab5`: 판세의 이면 · Trung Quốc - Hàn Quốc (Hạ Tầng & Địa Chính Trị)
    3. `channel-aa913eb90d`: bí mật US · Archival Vault & Intelligence Declassification
    4. `channel-f6ec4dfff3`: The First Family Vault · Presidential Records & Executive Forensics
  - Currently, none of the 4 profiles possess a top-level `thumbnail_dna` field.
  - In `channel-e544a64b7c`, `self_learning_memory` has a small nested stub:
    ```json
    "thumbnail_dna": {
      "archetype": "broadcast_left_heavy",
      "max_words": 5,
      "accent_color": "#38BDF8",
      "min_contrast": 4.5
    }
    ```
  - `channel-e544a64b7c` has:
    - `"default_ai_custom_style": "Cold Forensic Noir (Tông màu điện ảnh điều tra sắc lạnh, phòng thẩm vấn, hiện trường phong tỏa)"`
    - `"default_style_reference_image": "B:\\ALL_TOOLS\\CofiDocumentary\\data\\outputs\\channel_branding\\teukgeup_detective_reference.png"`
    - Note: The file `data/outputs/channel_branding/teukgeup_detective_reference.png` was missing on disk, but the actual 533 KB 2D Golden Detective Mascot image exists at `workspaces/20261019-185102-31983814/media/style_reference/style_reference.png`. Linking or copying this file into `data/outputs/channel_branding/` repairs the channel branding reference permanently.

- **`services/channel_profile_service.py`**:
  - Defines Pydantic models: `SubtitleStyleModel`, `AudioRulesModel`, `EditingDnaModel`, `SelfLearningMemoryModel`, `DefaultCreativeBriefModel`, `ChannelProfileCreateModel`, `ChannelProfileUpdateModel`.
  - Currently missing `ThumbnailDnaModel` and top-level field `thumbnail_dna` in create/update/read models.
  - `update_profile` needs to handle `thumbnail_dna` merging and persistence.

- **`services/job_service.py`**:
  - In `create_job(payload)` (lines 78–114):
    - Automatically snapshots parent channel profile data (`editing_dna`, `default_style_reference_image`, `default_creative_brief`).
    - Currently does **not** inherit `thumbnail_dna`.
    - Needs to inherit `job_data["thumbnail_dna"] = copy.deepcopy(profile.get("thumbnail_dna") or {})` and store it in `channel_profile_snapshot["thumbnail_dna"]` and `workspaces/{job_id}/input.json`.

---

### 2.2 Thumbnail Studio Engine (`documentary/thumbnail_studio.py`)

- **Current Capabilities**:
  - Canvas dimensions: 1280×720 (16:9).
  - 5 Built-in archetypes: `broadcast_left_heavy`, `bottom_cinematic`, `split_duality`, `evidence_spotlight`, `right_heavy_confrontation`.
  - `discover_job_candidate_images`: gathers images from `media/thumbnail`, `media/style_reference`, `media/ai_visual`, and assets.
  - `build_clean_background_prompt`: prompts Google Labs Flow with strict negative prompt (no text, letters, watermarks, leaving 40% negative space).
  - `build_variant_layers`: constructs Fabric.js JSON layers (vignette, inset_photo, circle, arrow, stamp, badge, line_1, line_2).
  - `evaluate_thumbnail_ctr`: evaluates 4 checks (safe_zone, mobile_legibility, contrast_hierarchy, base_image) with a 0-100 score and verdict (`HIGH_CTR`, `GOOD`, `NEEDS_TUNING`).
  - `render_variant_to_pil` & `render_design_thumbnails_to_disk`: renders 1280×720 images with local font fallback (`Pretendard`, `Gmarket Sans`, `Paperlogy`, `Malgun Gothic`).

- **Gaps Against R3 & AC3**:
  1. `build_default_thumbnail_design`:
     - Generates 4 variants cyclically with generic meanings (`Phương án A · Chuẩn Kênh`, `Phương án B · Góc nhìn Điều tra viên`, etc.).
     - Needs to explicitly generate the **3 primary A/B/C Test Variants** following R3's psychological click angles:
       - **Variant A**: Curiosity / Paradox / Shocking Number Hook
       - **Variant B**: Character / Forensic Evidence Close-Up / Emotion Hook
       - **Variant C**: Confrontation / Dual-Contrast Before-After / Mystery File Hook
     - Needs to inject the Channel Profile's `thumbnail_dna` (palette, font, mascot reference, archetype).
  2. **A/B CTR Prediction & Readiness Scorecard**:
     - Currently evaluates only 1 variant (the active one) using a basic 4-check heuristic.
     - Needs a multi-dimensional scorecard per variant:
       - **DNA Consistency** (font, brand color, mascot preservation)
       - **Text Legibility** (word count <= 5, font size >= 74px, mobile clearance)
       - **Emotional Curiosity Gap** (tension, paradox anchor, contrast)
       - **Keyword Alignment** (primary title keyword, series badge, case entity)
       - Readiness score for YouTube Studio "Test & Compare" deployment.

---

### 2.3 Backend API Endpoints (`app.py` / `server.py` / `documentary/service.py`)

- **Current Endpoints in `app.py` & `server.py`**:
  - `GET /api/jobs/{job_id}/thumbnail-studio`
  - `POST /api/jobs/{job_id}/thumbnail-studio/design`
  - `POST /api/jobs/{job_id}/thumbnail-studio/auto-design`
  - `POST /api/jobs/{job_id}/thumbnail-studio/generate-bg`
  - `POST /api/jobs/{job_id}/thumbnail-studio/upload-image`
  - `POST /api/jobs/{job_id}/thumbnail-studio/export`
- **Missing Endpoints for R3 / AC3**:
  1. `POST /api/jobs/{job_id}/lock-thumbnail-dna`:
     - Analogue of `/api/jobs/{job_id}/lock-edit-dna`.
     - Extracts the approved thumbnail design from `thumbnail_design.json` (typography, palette, layout, active archetype, reference character).
     - Locks it into the parent Channel Profile's `thumbnail_dna`.
     - Appends previous version to `thumbnail_dna_history`.
     - Returns `{ "ok": true, "profile_id": ..., "thumbnail_dna": ... }`.
  2. `POST /api/radar/channel-profiles/{profile_id}/lock-thumbnail-dna`:
     - Direct profile lock from Step 0 form.
  3. `POST /api/jobs/{job_id}/thumbnail-studio/export-ab-pack`:
     - Exports all 3 variants (`thumbnail_variant_A.jpg`, `thumbnail_variant_B.jpg`, `thumbnail_variant_C.jpg`) and a structured metadata pack (`test_and_compare_manifest.json`) formatted for YouTube Studio's "Test & Compare" 3-thumbnail experiment.

---

### 2.4 Frontend Implementation (`static/index.html`, `static/app.js`, `static/thumbnail_studio.js`)

- **Step 0 (`Channel Profile Form`)**:
  - Needs a dedicated UI block in `static/index.html`: `channelThumbnailDnaStudio`.
  - Controls:
    - Style preset dropdown (`cold_forensic_noir`, `infra_25d_technical`, `archival_vault_us`, `custom`)
    - Visual signature text input
    - Mascot lock toggle + reference image path / preview
    - Color palette inputs (primary background, accent highlight, danger badge)
    - Typography preset (font family, max words per line)
    - Action button: "Lưu & Khóa DNA Thumbnail Kênh"
  - In `static/app.js`:
    - `fillChannelProfileForm(profile)`: populates thumbnail DNA fields with zero bleed.
    - `resetChannelProfileForm()`: clears thumbnail DNA fields with zero bleed.

- **Step 07 (`Thumbnail Studio` / `static/thumbnail_studio.js`)**:
  - Currently renders a 4-card grid and full-screen editor.
  - Needs to add:
    1. **Psychological Angle Badges** on each card:
       - `Variant A: Curiosity / Paradox Hook`
       - `Variant B: Character / Evidence Close-Up`
       - `Variant C: Confrontation / Dual-Contrast`
    2. **A/B CTR Prediction Breakdown**:
       - DNA Consistency, Text Legibility, Curiosity Gap, Keyword Alignment.
    3. **View Mode Switcher**:
       - `[⊞ Grid So Sánh (A/B/C)]`
       - `[📱 YouTube Home Feed Preview]` (renders YouTube home feed card with avatar, title, channel name, views, timestamp)
       - `[📑 YouTube Sidebar Feed Preview]` (renders compact 168×94 sidebar layout)
    4. **Top Actions**:
       - `[🔒 Lưu & Khóa DNA Thumbnail Kênh]` -> calls `/api/jobs/{job_id}/lock-thumbnail-dna`
       - `[📦 Xuất Gói A/B/C Test Pack (YouTube Test & Compare)]` -> exports the 3 variants pack
    5. **Per-Card Action**:
       - `[★ Chọn Bản Thắng & Đặt Làm Chính]` -> sets active variant and updates primary thumbnail.

---

### 2.5 Pre-Flight Service Integration (`services/preflight_service.py`)

- `preflight_service.py` lines 316–332 already contains basic validation for stage == "thumbnail":
  ```python
  elif stage == "thumbnail":
      variants = input_data.get("variants") or []
      if len(variants) < 3:
          passed = False
          recommendations.append("Cần tạo tối thiểu 3 biến thể thumbnail để A/B test.")
  ```
- Needs expansion to:
  - Validate that the 3 variants cover the distinct psychological hooks (Variant A, B, C).
  - Verify that variant typography and palette match the Channel Profile's `thumbnail_dna`.
  - Validate mobile text overlay word count (<= 5 words).

---

## 3. Data Schema Specifications

### 3.1 Proposed `thumbnail_dna` Schema

```json
{
  "version": 1,
  "style_preset": "cold_forensic_noir",
  "visual_signature": "Cold Forensic Noir + 2D Golden Detective Mascot #FFE84A",
  "reference_character_path": "B:\\ALL_TOOLS\\CofiDocumentary\\data\\outputs\\channel_branding\\teukgeup_detective_reference.png",
  "mascot_lock": {
    "enabled": true,
    "name": "Golden Detective Mascot",
    "color": "#FFE84A",
    "style": "2D forensic line art on dark noir background"
  },
  "color_palette": {
    "primary_bg": "#04070d",
    "accent_highlight": "#FFE84A",
    "danger_badge": "#dc2626",
    "text_primary": "#ffffff",
    "text_secondary": "#FFE84A",
    "stroke_color": "#000000"
  },
  "typography_preset": {
    "font_family": "'Pretendard ExtraBold', 'Gmarket Sans Bold', 'Malgun Gothic', sans-serif",
    "font_size_line1": 76,
    "font_size_line2": 86,
    "stroke_width": 16,
    "shadow_blur": 20,
    "max_words_per_line": 5,
    "min_contrast": 4.5
  },
  "layout_template": {
    "archetype": "broadcast_left_heavy",
    "subject_placement": "right_third",
    "badge_position": "top_left",
    "text_alignment": "left",
    "safe_zone_margin_px": 80
  },
  "psychological_hooks": {
    "variant_a": "curiosity_paradox",
    "variant_b": "character_evidence_closeup",
    "variant_c": "confrontation_dual_contrast"
  },
  "locked_from_job_id": "20261019-185102-31983814",
  "locked_at": "2026-10-19T19:00:00Z"
}
```

### 3.2 4-Channel Profile Backfill Specifications

1. **`channel-e544a64b7c`** (특급수배록 · True Crime Hình Sự Trung Quốc · KR · 30 Phút · Full AI):
   - `style_preset`: `"cold_forensic_noir"`
   - `visual_signature`: `"Cold Forensic Noir + 2D Golden Detective Mascot #FFE84A"`
   - `reference_character_path`: `"B:\\ALL_TOOLS\\CofiDocumentary\\data\\outputs\\channel_branding\\teukgeup_detective_reference.png"`
   - `mascot_lock`: `{"enabled": true, "name": "Golden Detective Mascot", "color": "#FFE84A"}`
   - `color_palette`: `{"primary_bg": "#04070d", "accent_highlight": "#FFE84A", "danger_badge": "#dc2626", "text_primary": "#ffffff", "text_secondary": "#FFE84A", "stroke_color": "#000000"}`
   - `layout_template`: `{"archetype": "broadcast_left_heavy", "subject_placement": "right_third"}`

2. **`channel-1e24de3ab5`** (판세의 이면 · Trung Quốc - Hàn Quốc · Hạ Tầng & Địa Chính Trị):
   - `style_preset`: `"infra_25d_technical"`
   - `visual_signature`: `"2.5D Technical & Infrastructure Satellite HUD Telemetry"`
   - `reference_character_path`: `""`
   - `mascot_lock`: `{"enabled": false}`
   - `color_palette`: `{"primary_bg": "#061325", "accent_highlight": "#38bdf8", "danger_badge": "#ea580c", "text_primary": "#ffffff", "text_secondary": "#38bdf8", "stroke_color": "#000000"}`
   - `layout_template`: `{"archetype": "bottom_cinematic", "subject_placement": "top_center"}`

3. **`channel-aa913eb90d`** (bí mật US · Archival Vault & Intelligence Declassification):
   - `style_preset`: `"archival_vault_us"`
   - `visual_signature`: `"Archival Historical Vault & Classified Intelligence Dossier"`
   - `reference_character_path`: `""`
   - `mascot_lock`: `{"enabled": false}`
   - `color_palette`: `{"primary_bg": "#0c0a09", "accent_highlight": "#f59e0b", "danger_badge": "#b91c1c", "text_primary": "#f5f5f4", "text_secondary": "#f59e0b", "stroke_color": "#000000"}`
   - `layout_template`: `{"archetype": "split_duality", "subject_placement": "left_half"}`

4. **`channel-f6ec4dfff3`** (The First Family Vault · Presidential Records & Executive Forensics):
   - `style_preset`: `"archival_vault_us"`
   - `visual_signature`: `"Archival Historical Vault & Classified Intelligence Dossier"`
   - `reference_character_path`: `""`
   - `mascot_lock`: `{"enabled": false}`
   - `color_palette`: `{"primary_bg": "#0c0a09", "accent_highlight": "#fbbf24", "danger_badge": "#dc2626", "text_primary": "#ffffff", "text_secondary": "#fbbf24", "stroke_color": "#000000"}`
   - `layout_template`: `{"archetype": "evidence_spotlight", "subject_placement": "center_spotlight"}`

---

## 4. Existing Test Analysis & Test Strategy for AC3

- **Existing Tests**:
  - `tests/e2e/test_ac4_preflight_self_learning.py` tests that thumbnail pre-flight requires >= 3 variants and overlay text <= 6 words. Passes 100%.
  - `tests/test_m3_editing_dna_sync_policy.py` tests `EditingDnaService` locking and versioning.
  - `tests/test_anti_duplicate_memory_and_workspace.py` tests topic memory and workspace persistence.
- **Recommended Test Implementation (`tests/test_thumbnail_ab_testing_dna.py`)**:
  1. `test_channel_profiles_persist_thumbnail_dna_schema`: Verifies all 4 channel profiles in `channel_profiles.json` have non-null, valid `thumbnail_dna` matching their niche and mascot locks.
  2. `test_job_inherits_channel_thumbnail_dna`: Verifies `JobService.create_job` copies `thumbnail_dna` into the job record, snapshot, and workspace.
  3. `test_lock_thumbnail_dna_api_endpoint`: Verifies `POST /api/jobs/{job_id}/lock-thumbnail-dna` extracts active design parameters, updates parent channel profile `thumbnail_dna`, increments version, and records history.
  4. `test_step07_generates_three_distinct_ab_variants`: Verifies `thumbnail_studio_state` / `build_default_thumbnail_design` creates 3 variants with the distinct psychological hooks (Variant A, B, C) preserving channel DNA.
  5. `test_thumbnail_ab_ctr_prediction_scorecard`: Verifies `evaluate_thumbnail_ctr` / `evaluate_ab_test_variant` returns scorecards with DNA consistency, text legibility, curiosity gap, and keyword alignment.
  6. `test_export_ab_pack_and_feed_preview`: Verifies the export pack endpoint returns all 3 variant paths and manifest formatted for YouTube Studio Test & Compare.
