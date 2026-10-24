# Comprehensive Backend Survey Report: Data Models, Storage Persistence, Isolation, and Migration Audit

**Author**: teamwork_preview_explorer_survey_2  
**Date**: 2026-10-18  
**Scope**: `B:\ALL_TOOLS\CofiDocumentary` and related database/storage repositories (`B:\ALL_TOOLS\CofiRadar`)  
**Mission**: In-depth audit of Backend Isolation, Data Model schemas, Storage Persistence, API Route mutations, and Existing Data Backfill/Integrity (Requirements R2, R6, and Acceptance Criteria AC2).

---

## 1. Executive Summary

1. **Storage Subsystems Clarification**:
   - In `B:\ALL_TOOLS\CofiDocumentary`, Channel Profiles are persisted as JSON in `data/channel_profiles.json` and Jobs are persisted in `data/jobs/{job_id}/job.json` with workspaces in `workspaces/{job_id}/`.
   - The SQLite database referenced as `radar.db` exists in the sister service `B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db` (255 MB SQLite database with 15 tables: `scans`, `channels`, `videos`, `video_snapshots`, `niches`, `my_channels`, `launch_plans`, `plan_items`, `today_queue`, etc.). CofiDocumentary interacts with CofiRadar via `RadarClient` HTTP REST endpoints on port 8775.
   - There are currently **4 channel profiles** in `data/channel_profiles.json` and **4 jobs** in `data/jobs/`.

2. **Critical State Bleed & Cross-Job Mutation Bug Uncovered**:
   - In `static/app.js` (lines 2785–2802 and 3314–3343), `#jobForm` (Step 00 Create Project form) contains change listeners for `ai_media_mode`, `createAiStyleMode`, `createAiStylePreset`, `createAiCustomStyle`, and `createStyleReferenceInput`.
   - Every time a user interacts with these inputs in the draft form, `syncCreateStyleToActiveJob()` fires `PATCH /api/jobs/${encodeURIComponent(state.selectedId)}/ai-visual-settings` and `uploadCreateStyleReference(state.selectedId)`.
   - **Impact**: Configuring a new draft project silently mutates whatever active project is currently selected in `state.selectedId` (even completed or in-progress projects), violating Requirement R2 and AC2.

3. **Field Bleed on Channel Profile Switching**:
   - In `static/app.js` (`applySelectedProfileToCreateStep`, lines 2473–2520), switching channel profiles does NOT reset or wipe form fields (`narrative_angle`, `writing_style`, `hook_archetype`, `editing_archetypes`, `custom_rules`, `opening_hook`, `notes`).
   - If the newly selected profile does not define a `default_creative_brief` (e.g., profiles `channel-1e24de3ab5`, `channel-aa913eb90d`, `channel-f6ec4dfff3`), the form retains the old profile's creative brief and DNA, causing cross-profile field bleed.
   - In Step 0, there is no separation between "Create New Profile", "Clone Profile", and "Update Current Profile". Submitting the form while a profile is selected always overwrites it with `PATCH`.

4. **Data Integrity & Backfill Audit Findings**:
   - All 4 existing channel profiles are missing `editing_dna` (shot pacing, visual mix ratios, Remotion archetypes, subtitle styles, color grades, and chapter transitions) and `self_learning_memory`.
   - 3 of the 4 channel profiles (`channel-1e24de3ab5`, `channel-aa913eb90d`, `channel-f6ec4dfff3`) have `null` or missing values for `default_language`, `default_visual_strategy`, `default_ai_media_mode`, `dna_mode`, `voice_and_structure`, `allowed_topics`, `forbidden_topics`, `monetization_safety_policy`, `default_creative_brief`, and `editorial_dna`.
   - 2 of the 4 existing jobs (`20261018-223750-3aecfbcd` and `20261017-164519-fd65f7e1`) have `channel_profile_id: null` and `channel_profile_snapshot: {}`, despite their workspaces containing complete DNA matching `channel-1e24de3ab5` and `channel-e544a64b7c` respectively.
   - All 4 existing jobs lack `editing_dna`.

---

## 2. Storage Persistence & Data Model Architecture

### 2.1 File System vs SQLite Architecture

```
B:\ALL_TOOLS\CofiDocumentary\
├── data\
│   ├── channel_profiles.json         # Master storage for Channel Profiles (JSON dict: {"profiles": [...]})
│   ├── channel_playbooks.json        # Reusable playbooks
│   ├── ai_account_settings.json      # LLM provider settings (Codex / Gemini failover)
│   ├── radar_translation_cache.json  # Cached Korean-Vietnamese translations
│   └── jobs\                         # Primary Job persistence directory (managed by JobStore)
│       ├── 20261018-223750-3aecfbcd\job.json
│       ├── 20261017-164519-fd65f7e1\job.json
│       ├── 20261017-003022-ecb75736\job.json
│       └── 20261015-014818-f0fdc122\job.json
├── workspaces\                       # Production workspace artifacts per project
│   ├── 20261018-223750-3aecfbcd\     # 32 artifact files (creative_brief.json, script.md, etc.)
│   ├── 20261017-164519-fd65f7e1\     # 31 artifact files
│   ├── 20261017-003022-ecb75736\     # 30 artifact files
│   └── 20261015-014818-f0fdc122\     # 27 artifact files
└── (external) B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db # 255MB SQLite database
```

### 2.2 CofiRadar SQLite Database (`B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db`)
Inspected via Python `sqlite3`:
- **File size**: 255,623,168 bytes (~255 MB)
- **Tables and row counts**:
  * `scans`: 273 rows (Market and channel search queries)
  * `channels`: 1,895 rows (Tracked YouTube channels)
  * `channel_snapshots`: 5,479 rows (Historical subscriber and view counts)
  * `videos`: 12,286 rows (Discovered YouTube videos)
  * `video_snapshots`: 28,342 rows (Time-series views, likes, comments)
  * `scan_video_map`: 11,648 rows
  * `video_metrics`: 10,075 rows (`vph`, `channel_median_views`, `outlier`, `breakout`)
  * `niches`: 255 rows (Identified micro-niches with YPP risk and demand scores)
  * `niche_video_map`: 2,876 rows
  * `niche_channel_map`: 1,409 rows
  * `my_channels`: 10 rows (Connected own YouTube channels)
  * `launch_plans`: 82 rows (30-day channel content schedules)
  * `plan_items`: 507 rows (Individual scheduled topic anchors)
  * `today_queue`: 68 rows (Daily prioritized video candidates)
  * `evidence`: 1 row

Key Foreign Keys & Schema relations:
- `videos(channel_id)` REFERENCES `channels(id) ON DELETE CASCADE`
- `plan_items(plan_id)` REFERENCES `launch_plans(id) ON DELETE CASCADE`
- `plan_items(evidence_video_id)` REFERENCES `videos(id) ON DELETE CASCADE`
- `today_queue(plan_item_id)` REFERENCES `plan_items(id) ON DELETE CASCADE`

### 2.3 Channel Profiles Storage (`data/channel_profiles.json`)
Structure:
```json
{
  "profiles": [
    {
      "id": "channel-e544a64b7c",
      "label": "Hồ sơ Kênh True Crime Hình Sự Trung Quốc (KR - 30 Phút - Full AI)",
      "market": "KR",
      "default_language": "ko",
      "default_duration_minutes": 30,
      "default_visual_strategy": "full_ai",
      "default_ai_media_mode": "image",
      "default_ai_style_mode": "custom",
      "default_ai_custom_style": "Cold Forensic Noir...",
      "dna_mode": "custom_dna_only",
      "voice_and_structure": "Hàn Quốc (KR) — Giọng kể điều tra sắc lạnh...",
      "allowed_topics": "Trọng án hình sự có thật tại Trung Quốc...",
      "forbidden_topics": "Án kinh tế, tham nhũng quan chức, hối lộ...",
      "monetization_safety_policy": "Ngôi thứ 3 theo góc nhìn Hồ sơ Điều tra viên Hình sự...",
      "reference_image_policy": "100% Full AI (full_ai)...",
      "own_channel_ref": "",
      "own_channel": {},
      "competitor_refs": [],
      "competitors": [],
      "default_creative_brief": { ... },
      "editorial_dna": { ... },
      "plan": { ... },
      "latest_today": { ... },
      "latest_codex_analysis": { ... },
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### 2.4 Job Storage (`data/jobs/{job_id}/job.json`)
Managed by `JobStore` (`documentary/store.py`):
- Atomic writes: `_write(path, payload)` writes to `NamedTemporaryFile` in `path.parent` and performs atomic rename via `os.replace`.
- Thread safety: Guarded by `threading.RLock()`.
- Normalization: `_normalize_job(job)` ensures all `PHASES` (`plan`, `voice`, `visuals`, `footage`, `ai_visual`, `edit`, `seo`, `qc`) have explicit phase state objects (`status`, `started_at`, `finished_at`, `error`, `last_message`), normalizes `visual_strategy` to `{full_ai, full_footage, hybrid, evidence_footage}`, and sets defaults.
- Job recovery: `recover_interrupted()` detects any jobs or phases left in `running` or `queued` state upon server restart and transitions them safely to `interrupted`.

---

## 3. Backend API Endpoints & Mutation Analysis

### 3.1 Channel Profile Routes (`app.py`)
| Endpoint | Method | Handler | Description & Mutation Validation |
|---|---|---|---|
| `/api/radar/channel-profiles` | `GET` | `channel_profiles()` | Calls `service.list_channel_profiles()`. Returns list sorted by `updated_at`. |
| `/api/radar/channel-profiles` | `POST` | `create_channel_profile(body)` | Calls `service.save_channel_profile(body.model_dump())`. Generates `channel-{uuid4()[:10]}`. |
| `/api/radar/channel-profiles/{profile_id}` | `PATCH` | `update_channel_profile(profile_id, body)` | Calls `service.save_channel_profile(body.model_dump(), profile_id=profile_id)`. Replaces profile in memory and writes to disk. |
| `/api/radar/channel-profiles/{profile_id}` | `DELETE` | `delete_channel_profile(profile_id)` | Removes profile from `_channel_profiles` and writes disk. |
| `/api/radar/channel-profiles/{profile_id}/refresh` | `POST` | `refresh_channel_profile(profile_id)` | Rescans YouTube channels/competitors. |
| `/api/radar/channel-profiles/{profile_id}/today` | `GET` / `POST` | `channel_profile_today(...)` | Discovers/ranks daily topic candidates. |
| `/api/radar/channel-profiles/{profile_id}/plan` | `GET` | `channel_profile_plan(profile_id)` | Gets 30-day launch plan. |
| `/api/radar/channel-profiles/{profile_id}/plan-items/{item_id}` | `PATCH` | `update_channel_plan_item(...)` | Updates plan item status. |

**Missing Routes in `app.py`**:
1. `GET /api/radar/channel-profiles/{profile_id}`: Currently returns 404 or falls through; only list endpoint exists.
2. `POST /api/radar/channel-profiles/{profile_id}/clone`: No endpoint exists for cleanly cloning a profile into a new profile ID.
3. `POST /api/jobs/{job_id}/lock-edit-dna`: No endpoint exists to lock project editing parameters into channel profile `editing_dna`.
4. `GET/POST /api/radar/channel-profiles/{profile_id}/self-learning`: No endpoint exists for post-mortem analysis and win/loss diagnosis.

### 3.2 Job Routes (`app.py`)
| Endpoint | Method | Handler | Description & Mutation Validation |
|---|---|---|---|
| `/api/jobs` | `GET` | `jobs()` | Lists all jobs from `service.list_jobs()`. |
| `/api/jobs` | `POST` | `create_job(body)` | Validates via `CreateJobRequest` Pydantic model. Calls `service.create_job()`. |
| `/api/jobs/from-radar` | `POST` | `create_job_from_radar(body)` | Imports candidate from Radar scan. |
| `/api/jobs/{job_id}` | `GET` | `job_detail(job_id)` | Returns job JSON and workspace storage info. |
| `/api/jobs/{job_id}` | `DELETE` | `delete_job(job_id)` | Deletes `data/jobs/{job_id}` and `workspaces/{job_id}`. |
| `/api/jobs/{job_id}/voice` | `PATCH` | `update_job_voice(...)` | Patches voice configuration. |
| `/api/jobs/{job_id}/ai-visual-settings` | `PATCH` | `update_ai_visual_settings(...)` | Patches AI visual model, aspect ratio, style preset, custom style. |
| `/api/jobs/{job_id}/production-settings` | `PATCH` | `update_production_settings(...)` | Patches visual strategy and media mode. |
| `/api/jobs/{job_id}/creative-brief` | `PATCH` | `update_creative_brief(...)` | Patches creative brief and syncs to workspace `creative_brief.json`. |
| `/api/jobs/{job_id}/outline` | `GET` / `PATCH` | `get_outline()` / `update_outline()` | Manages script chapters outline. |
| `/api/jobs/{job_id}/script` | `PUT` | `update_script(...)` | Overwrites `workspace/script.md`. |
| `/api/jobs/{job_id}/run/{phase}` | `POST` | `run_phase(job_id, phase)` | Starts executor thread for phase. |
| `/api/jobs/{job_id}/pipeline/{from}/{to}` | `POST` | `run_pipeline(...)` | Runs sequential pipeline phases. |

### 3.3 Root-Cause Analysis: Draft Mutation of Active Project
In `static/app.js`:
```javascript
// Line 2785
async function syncCreateStyleToActiveJob() {
  if (!state.selectedId) return;
  const mode = String($("#createAiStyleMode")?.value || "auto");
  const preset = String($("#createAiStylePreset")?.value || "");
  const custom = String($("#createAiCustomStyle")?.value || "");
  const mediaMode = String(document.querySelector('#jobForm input[name="ai_media_mode"]:checked')?.value || "mixed");
  try {
    await api(`/api/jobs/${encodeURIComponent(state.selectedId)}/ai-visual-settings`, {
      method: "PATCH",
      body: JSON.stringify({
        style_mode: mode,
        style_preset: preset,
        custom_style: custom,
        ai_media_mode: mediaMode,
      }),
    });
  } catch (_) {}
}

// Lines 3315-3335: Fired on every input change in the Create Project form!
$$('#jobForm input[name="ai_media_mode"]').forEach(input => input.addEventListener("change", syncCreateStyleToActiveJob));
$("#createAiStyleMode")?.addEventListener("change", () => {
  updateCreateStyleFields();
  syncCreateStyleToActiveJob();
});
$("#createAiStylePreset")?.addEventListener("change", () => {
  ...
  syncCreateStyleToActiveJob();
});
$("#createAiCustomStyle")?.addEventListener("change", () => {
  ...
  syncCreateStyleToActiveJob();
});
$("#createStyleReferenceInput")?.addEventListener("change", async () => {
  if (state.selectedId) {
    await uploadCreateStyleReference(state.selectedId);
  }
});
```
**Mechanism of the Bug**:
1. When user navigates to Step 00 (`Create Project`), `state.selectedId` remains set to whatever project was previously selected or active in the global dropdown.
2. When the user interacts with the `#jobForm` fields (selecting "Full AI" or changing the style preset for their *new* project), `syncCreateStyleToActiveJob()` executes an unprompted HTTP `PATCH` against `state.selectedId`.
3. Consequently, the active project's `ai-visual-settings` and style configuration are silently overwritten with the draft form's values.

---

## 4. Existing Data Backfill & Integrity Audit (R6 & AC2)

### 4.1 Audit of Existing Channel Profiles

| Field | `channel-aa913eb90d` | `channel-f6ec4dfff3` | `channel-1e24de3ab5` | `channel-e544a64b7c` |
|---|---|---|---|---|
| **Label** | bí mật US | The First Family Vault | Trung Quốc -Hàn Quốc | Hồ sơ Kênh True Crime Hình Sự Trung Quốc |
| **Market** | `US` | `US` | `KR` | `KR` |
| **Default Language** | ❌ `null` | ❌ `null` | ❌ `null` | ✅ `ko` |
| **Duration (min)** | 30 | ❌ `null` | ❌ `null` | ✅ 30 |
| **Visual Strategy** | ❌ `null` | ❌ `null` | ❌ `null` | ✅ `full_ai` |
| **AI Media Mode** | ❌ `null` | ❌ `null` | ❌ `null` | ✅ `image` |
| **DNA Mode** | ❌ `null` | ❌ `null` | ❌ `null` | ✅ `custom_dna_only` |
| **Own Channel Ref** | `@TheFirstFamilyVault` | `@TheFirstFamilyVault` | `@%ED%8C%90%EC%84%B8%EC%9D%98%EC%9D%B4%EB%A9%B4` | `""` |
| **Competitor Refs** | `['@AmericanSecrets-hxdk']` | `['@AmericanSecrets-hxdk']` | `['@세계경제돋보기']` | `[]` |
| **Allowed Topics** | ❌ `null` | ❌ `null` | ❌ `null` | ✅ 225 chars |
| **Forbidden Topics** | ❌ `null` | ❌ `null` | ❌ `null` | ✅ 61 chars |
| **Monetization Policy**| ❌ `null` | ❌ `null` | ❌ `null` | ✅ Complete |
| **Voice & Structure** | ❌ `null` | ❌ `null` | ❌ `null` | ✅ Complete |
| **Creative Brief** | ❌ `null` | ❌ `null` | ❌ `null` | ✅ Complete |
| **Editorial DNA** | Partial (v1) | ❌ `null` | ❌ `null` | ✅ Complete (v2) |
| **Editing DNA** | ❌ Missing | ❌ Missing | ❌ Missing | ❌ Missing |
| **Self-Learning Memory**| ❌ Missing | ❌ Missing | ❌ Missing | ❌ Missing |

### 4.2 Audit of Existing Jobs

| Field | `20261018-223750-3aecfbcd` | `20261017-164519-fd65f7e1` | `20261017-003022-ecb75736` | `20261015-014818-f0fdc122` |
|---|---|---|---|---|
| **Title** | Nam Thủy Bắc Điều 1,432km | Lao Rongzhi 20 năm tẩy trắng | Đại án 4.400 tỷ quan thanh liêm | Đập Tam Hiệp 393 tỷ tấn #shorts |
| **Status** | `ready` | `completed` | `succeeded` | `completed` |
| **Market / Lang** | `KR` / `ko` | `KR` / `ko` | `KR` / `ko` | `KR` / `ko` |
| **Visual Strategy**| `full_ai` | `full_ai` | `full_ai` | `full_ai` |
| **Channel Profile ID**| ❌ `None` | ❌ `None` | ✅ `channel-e544a64b7c` | ✅ `channel-1e24de3ab5` |
| **Snapshot Attached**| ❌ `{}` | ❌ `{}` | ✅ Attached | Partial (empty dna) |
| **True Identity** | `@판세의이면` (`channel-1e24de3ab5`) | True Crime CN (`channel-e544a64b7c`) | True Crime CN (`channel-e544a64b7c`) | `@판세의이면` (`channel-1e24de3ab5`) |
| **Workspace Brief** | ✅ Has complete brief | ✅ Has complete brief | ✅ Has complete brief | ❌ Missing brief |
| **Editing DNA** | ❌ Missing | ❌ Missing | ❌ Missing | ❌ Missing |

---

## 5. Non-Destructive Data Migration & Backfill Specification

To fulfill Requirement R6 and Acceptance Criteria AC2, an automated, non-destructive migration and backfill script must be implemented:

### 5.1 Backup Strategy
Before executing mutations:
1. `data/channel_profiles.json` -> `backups/channel_profiles.backup_{timestamp}.json`
2. `data/jobs/*/job.json` -> `backups/jobs/{job_id}_job.backup_{timestamp}.json`

### 5.2 Channel Profiles Backfill Matrix
```json
{
  "channel-1e24de3ab5": {
    "label": "판세의 이면 · Trung Quốc - Hàn Quốc (Hạ Tầng & Địa Chính Trị)",
    "market": "KR",
    "default_language": "ko",
    "default_duration_minutes": 22,
    "default_visual_strategy": "hybrid",
    "default_ai_media_mode": "image",
    "default_ai_style_mode": "custom",
    "default_ai_custom_style": "2.5D Technical & Infrastructure Investigation (Bản đồ địa hình 2.5D, mặt cắt địa chất, HUD telemetry thông số kỹ thuật)",
    "dna_mode": "radar_hybrid",
    "voice_and_structure": "Phóng sự Điều tra Kỹ thuật Hàn Quốc Sắc Lạnh — Dẫn chứng Số liệu & Cơ chế Vật lý (판세의 이면 스타일 · 22 Phút)",
    "allowed_topics": "Bóc tách sâu cơ chế vật lý, địa chất, thông số kỹ thuật các đại công trình hạ tầng Trung Quốc, điểm gãy hệ thống, đập thủy điện, giao thông vận tải, kênh dẫn nước đại quy mô.",
    "forbidden_topics": "Chủ đề chính trị tranh cãi không có cơ sở kỹ thuật, tin tức giật gân nông cạn, từ khóa yếu ('이유', '역설', '문제' đứng đơn lẻ).",
    "monetization_safety_policy": "Phóng sự khoa học kỹ thuật khách quan — 100% Green Monetization, giải mã cơ chế vật lý hiện trường, không kích động.",
    "reference_image_policy": "Kết hợp Footage thực tế (công trường, đập, bản đồ vệ tinh) và AI Visual giải phẫu mặt cắt địa chất.",
    "default_creative_brief": {
      "narrative_angle": "Điều tra Kỹ thuật Hạ tầng & Giải phẫu Điểm gãy Hệ thống (중국 초대형 인프라 설계 한계 & 지질 공학 분석)",
      "writing_style": "Phóng sự Điều tra Kỹ thuật Hàn Quốc Sắc Lạnh — Dẫn chứng Số liệu & Cơ chế Vật lý (판세의 이면 스타일 · 22 Phút)",
      "hook_archetype": "Con số Định lượng Cực hạn & Nghịch lý Vật lý Hiện trường (00:00–02:30)",
      "editing_archetypes": [
        "Bản đồ Địa hình 2.5D & Đường tuyến Vệ tinh",
        "HUD Số liệu Kỹ thuật & Đồ thị Độ lún",
        "Đối chiếu Bản vẽ Thiết kế vs. Hiện trường Thực tế",
        "Chapter Title Card Điện ảnh + Sound Hit"
      ],
      "custom_rules": "CHUẨN DNA KÊNH @판세의이면..."
    },
    "editing_dna": {
      "version": 1,
      "typical_pacing_sec": 4.5,
      "visual_mix": { "footage": 0.5, "ai": 0.35, "motion": 0.15 },
      "editing_archetypes": [
        "2.5d_satellite_terrain_flyover",
        "technical_hud_telemetry_gauge",
        "blueprint_vs_reality_split",
        "cinematic_chapter_card_hit"
      ],
      "subtitle_style": {
        "font_family": "Pretendard, sans-serif",
        "color": "#ffffff",
        "highlight_color": "#38bdf8",
        "font_size": 42
      },
      "color_grade": "technical_cool_cyan",
      "audio_rules": { "music_ducking_db": -18, "sfx_hit_on_chapter": true }
    },
    "self_learning_memory": {
      "analyzed_videos_count": 26,
      "winner_patterns": ["cơ chế vật lý điểm gãy", "đất trương nở", "đập Tam Hiệp"],
      "losing_patterns": ["tin vắn chính trị", "từ khóa chung chung"],
      "next_video_upgrades": ["Mở đầu bằng số liệu chênh lệch cực hạn", "Tăng mật độ HUD 2.5D"]
    }
  },
  "channel-e544a64b7c": {
    "editing_dna": {
      "version": 1,
      "typical_pacing_sec": 5.5,
      "visual_mix": { "footage": 0.0, "ai": 0.85, "motion": 0.15 },
      "editing_archetypes": [
        "forensic_case_board_red_string",
        "document_scanner_telemetry",
        "split_screen_investigation",
        "noir_chapter_transition"
      ],
      "subtitle_style": {
        "font_family": "Pretendard, sans-serif",
        "color": "#ffffff",
        "highlight_color": "#eab308",
        "font_size": 44
      },
      "color_grade": "cold_forensic_noir",
      "audio_rules": { "music_ducking_db": -20, "tension_drone_under_interrogation": true }
    },
    "self_learning_memory": {
      "analyzed_videos_count": 15,
      "winner_patterns": ["vỏ bọc hai mặt 20 năm", "giám định ADN Big Data", "phòng thẩm vấn"],
      "losing_patterns": ["mô tả bạo lực trực diện", "vụ án tài sản nhỏ"],
      "next_video_upgrades": ["Khóa chặt góc nhìn Điều tra viên", "Không hiển thị vũ khí sát thương"]
    }
  },
  "channel-aa913eb90d": {
    "default_language": "en",
    "default_visual_strategy": "hybrid",
    "default_ai_media_mode": "mixed",
    "dna_mode": "radar_hybrid",
    "voice_and_structure": "US Historical Documentary — Archival Vault & Intelligence Declassification · 30 Minutes",
    "allowed_topics": "US historical declassifications, Cold War covert operations, presidential executive orders, forensic institutional investigations.",
    "forbidden_topics": "Contemporary partisan politics, defamatory claims, graphic gore.",
    "monetization_safety_policy": "Third-person historical investigative documentary — 100% YouTube Green Monetization.",
    "reference_image_policy": "Archival document and evidence footage mixed with 2.5D historical maps.",
    "default_creative_brief": {
      "narrative_angle": "Declassified Historical Investigation & Archival Forensics",
      "writing_style": "Cold US Investigative Documentary (Frontline / PBS style · 30 Min)",
      "hook_archetype": "Declassified Memo Paradox & Institutional Concealment",
      "editing_archetypes": [
        "Archival Document Scanner & Redaction Reveal",
        "Historical Timeline Telemetry",
        "Archival Photo Zoom & Parallax",
        "Chapter Title Card + Sound Hit"
      ],
      "custom_rules": "STRICT US ARCHIVAL VAULT DNA..."
    },
    "editing_dna": {
      "version": 1,
      "typical_pacing_sec": 5.0,
      "visual_mix": { "footage": 0.6, "ai": 0.25, "motion": 0.15 },
      "editing_archetypes": ["archival_document_scanner", "historical_map_parallax", "split_screen_memo"],
      "subtitle_style": { "font_family": "Inter, sans-serif", "color": "#f8fafc", "highlight_color": "#38bdf8", "font_size": 40 },
      "color_grade": "archival_warm_vintage",
      "audio_rules": { "music_ducking_db": -16, "typewriter_sound_on_memo": true }
    },
    "self_learning_memory": { "analyzed_videos_count": 0, "winner_patterns": [], "losing_patterns": [], "next_video_upgrades": [] }
  },
  "channel-f6ec4dfff3": {
    "default_language": "en",
    "default_duration_minutes": 30,
    "default_visual_strategy": "hybrid",
    "default_ai_media_mode": "mixed",
    "dna_mode": "radar_hybrid",
    "voice_and_structure": "US Presidential Vault Documentary — Executive Power & Archival Records · 30 Minutes",
    "allowed_topics": "Presidential archives, White House historic decisions, executive orders, national security records.",
    "forbidden_topics": "Modern partisan election attacks, unverified hearsay, violent graphic imagery.",
    "monetization_safety_policy": "Third-person presidential history documentary — 100% Green Monetization.",
    "reference_image_policy": "Presidential photography & authentic footage paired with 2.5D archival document scans.",
    "default_creative_brief": {
      "narrative_angle": "Presidential Vault Records & Executive Decision Forensics",
      "writing_style": "American Presidential History Documentary (30 Minutes)",
      "hook_archetype": "Presidential Order & Secret Clause Paradox",
      "editing_archetypes": [
        "Executive Order Scanner & Signature Zoom",
        "Oval Office Timeline Reconstruction",
        "Split-Screen Audio-Visual Match",
        "Chapter Card Cinematic Hit"
      ],
      "custom_rules": "STRICT PRESIDENTIAL VAULT DNA..."
    },
    "editorial_dna": {
      "version": 2,
      "source": "presidential_vault_profile",
      "visual_strategy": "hybrid",
      "reference_channels": ["https://www.youtube.com/@AmericanSecrets-hxdk"]
    },
    "editing_dna": {
      "version": 1,
      "typical_pacing_sec": 5.0,
      "visual_mix": { "footage": 0.65, "ai": 0.2, "motion": 0.15 },
      "editing_archetypes": ["executive_order_scanner", "timeline_hud", "cinematic_chapter_card"],
      "subtitle_style": { "font_family": "Inter, sans-serif", "color": "#f8fafc", "highlight_color": "#f59e0b", "font_size": 40 },
      "color_grade": "presidential_amber_kodachrome",
      "audio_rules": { "music_ducking_db": -18, "orchestral_swells": true }
    },
    "self_learning_memory": { "analyzed_videos_count": 0, "winner_patterns": [], "losing_patterns": [], "next_video_upgrades": [] }
  }
}
```

### 5.3 Jobs Backfill Matrix
1. `20261018-223750-3aecfbcd`:
   - `channel_profile_id`: `"channel-1e24de3ab5"`
   - `channel_profile_snapshot`: Extract from backfilled `channel-1e24de3ab5`
   - `editing_dna`: Inherit from `channel-1e24de3ab5`
2. `20261017-164519-fd65f7e1`:
   - `channel_profile_id`: `"channel-e544a64b7c"`
   - `channel_profile_snapshot`: Extract from backfilled `channel-e544a64b7c`
   - `editing_dna`: Inherit from `channel-e544a64b7c`
3. `20261017-003022-ecb75736`:
   - `editing_dna`: Inherit from `channel-e544a64b7c`
4. `20261015-014818-f0fdc122`:
   - `creative_brief`: Backfill brief for Three Gorges Dam engineering disaster analysis
   - `editing_dna`: Inherit from `channel-1e24de3ab5`

---

## 6. Implementation Action Plan for Downstream Agents

1. **Backend Data Model & Schemas (`app.py`, `documentary/models.py`, `documentary/service.py`)**:
   - Add `editing_dna` and `self_learning_memory` fields to `ChannelProfileRequest` and `CreateJobRequest`.
   - Update `DocumentaryService.save_channel_profile` to preserve and persist `editing_dna` and `self_learning_memory`.
   - Implement `GET /api/radar/channel-profiles/{profile_id}`.
   - Implement `POST /api/radar/channel-profiles/{profile_id}/clone`.
   - Implement `POST /api/jobs/{job_id}/lock-edit-dna`.
   - Implement `GET/POST /api/radar/channel-profiles/{profile_id}/self-learning`.
   - Implement `GET /api/jobs/{job_id}/policy-guardrails` (Voice-visual sync & YouTube compliance check).

2. **Frontend Isolation Enforcement (`static/app.js`)**:
   - In Step 00 (`#jobForm`): Remove all calls to `syncCreateStyleToActiveJob()` and `uploadCreateStyleReference(state.selectedId)`.
   - In `applySelectedProfileToCreateStep`: Always call a complete form wipe/reset before loading profile fields, ensuring zero field residual.
   - In Step 0: Add explicit buttons for "Tạo Hồ Sơ Mới", "Nhân Bản Hồ Sơ (Clone)", and "Lưu Cập Nhật".

3. **Data Backfill Execution (`documentary/migrations/backfill_profiles_and_jobs.py`)**:
   - Create idempotent script that performs backup and applies Section 5 backfill matrices non-destructively.
