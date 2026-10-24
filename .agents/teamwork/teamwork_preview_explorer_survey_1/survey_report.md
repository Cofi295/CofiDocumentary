# Comprehensive Survey Report: Frontend UI/UX & Client-Side State Architecture

**Target Application**: CofiDocumentary (`B:\ALL_TOOLS\CofiDocumentary`)  
**Survey Agent**: `teamwork_preview_explorer_survey_1`  
**Date**: 2026-10-18 / 2026-10-19  
**Reference Document**: `ORIGINAL_REQUEST.md` (Requirements R1, R2; Acceptance Criteria AC1, AC2)

---

## Executive Summary

This survey provides an exhaustive technical analysis of CofiDocumentary's frontend interface, layout ergonomics, workflow tabs (Step 0 to Step 08), AI Agent synchronization, and client-side state management.

Key discoveries:
1. **Critical State Leakage / Background Mutation Bug**: In Step 00 (`#jobForm`), draft inputs for AI visual settings (`ai_media_mode`, `#createAiStyleMode`, `#createAiStylePreset`, `#createAiCustomStyle`, and `#createStyleReferenceInput`) are wired directly to `syncCreateStyleToActiveJob()`. When a user drafts settings for a new video, `PATCH /api/jobs/{state.selectedId}/ai-visual-settings` is fired automatically, silently mutating the currently running or completed project in the background (`static/app.js:2785-2802`, `3315-3343`).
2. **Channel Profile Field Bleeding Bug**: In Step 00 (`applySelectedProfileToCreateStep` in `static/app.js:2473-2514` and `applyCreativeProposalToCreateForm` in `3036-3110`), form fields (`narrative_angle`, `writing_style`, `hook_archetype`, `editing_archetypes`, `opening_hook`, `notes`) are only updated when the incoming profile contains a truthy value. If a user switches from a profile with a rich brief (e.g., `channel-e544a64b7c`) to a profile lacking a creative brief (e.g., `channel-1e24de3ab5`, `channel-aa913eb90d`, `channel-f6ec4dfff3`), zero fields are reset, causing complete data bleed.
3. **Missing Profile Action Separation**: Step 0 (`#channelProfileForm`) lacks distinct "Create New", "Clone Profile", and "Update Current Profile" operations. Submitting `#channelProfileForm` conditionally executes `PATCH` if `state.selectedChannelProfileId` is non-null (`static/app.js:2656-2674`). When a user applies a preset ("⚡ Chuẩn True Crime TQ" via `#presetTrueCrimeCnBtn`), `state.selectedChannelProfileId` is not cleared, causing the user to accidentally overwrite the previously selected profile upon clicking Save.
4. **Data Discrepancies in Storage**:
   - `data/channel_profiles.json`: Profiles `channel-aa913eb90d`, `channel-f6ec4dfff3`, and `channel-1e24de3ab5` lack `default_creative_brief`, `editorial_dna`, `visual_strategy`, and `editing_dna`.
   - `data/jobs/`: Recent jobs `20261018-223750-3aecfbcd` (Nam Thủy Bắc Điều) and `20261017-164519-fd65f7e1` (Lao Rongzhi) have `channel_profile_id: null` despite explicit channel assignments in their notes and titles. None of the jobs or profiles have `editing_dna`.
5. **Responsive Layout Vulnerabilities (1280px–1920px)**:
   - When the Global AI Chat dock is open at `1280px` viewport width, the available content width shrinks to `~692px` (`1280px - 230px sidebar - 358px dock`).
   - `.seo-clean-hub` only media-collapses at `@media (max-width: 1024px)`, remaining a 2-column grid in a `692px` container (`~339px` per column).
   - `.inline-fields` in `#channelProfileForm` (4 fields) and `#marketScanForm` (5 fields) lack `flex-wrap: wrap`, causing severe squishing.
   - The topbar `#globalProjectSelect` switcher and top-action buttons are forced into `flex-wrap: nowrap`, compressing `.channel-studio-page-copy` to `~135px`.

---

## 1. Frontend Architecture & Inventory

### 1.1 Core Assets & Scripts

| Asset Path | Size | Description & Role |
|---|---|---|
| `static/index.html` | 65.5 KB (768 lines) | Single-page SaaS Studio DOM layout, desktop titlebar, sidebar navigation, 13 workflow panes, AI chat dock, modal dialogs. |
| `static/styles.css` | 240.5 KB (6,781 lines) | Master stylesheet. Contains base styles, studio layout overrides, typography (`Inter`, `Noto Sans KR`, `JetBrains Mono`), responsive rules, and dock styling. |
| `static/app.js` | 452.0 KB (8,280 lines) | Client-side application controller, global state management (`state`), event listeners, pipeline runner, API calls, and workspace renderers. |
| `static/thumbnail_studio.js` | 57.0 KB (1,304 lines) | Fabric.js layer engine, multi-card A/B/C/D test gallery, zoom lightbox, per-card and batch download, Google Labs Flow background generator. |
| `static/desktop_chrome.js` | 1.3 KB (51 lines) | PyWebView titlebar bridge (minimize, maximize, close, drag, reload, shortcuts `Ctrl+Shift+C`, `F5`). |

### 1.2 Layout Hierarchy & Shell Components

```
<body>
 ├── #desktopTitlebar (PyWebView custom titlebar, 34px fixed, .desktop-titlebar)
 ├── .app-shell.channel-studio-shell (CSS Grid: 230px sidebar + minmax(0, 1fr) main)
 │    ├── aside.sidebar.channel-studio-sidebar (230px width, sticky 100vh)
 │    │    ├── .brand (Logo, Title "COFI DOCUMENTARY", Subtitle)
 │    │    ├── nav.side-nav (Workflow navigation items: overview, radar, create, script, voice, visuals, footage, ai_visual, edit, seo, qc, accounts, projects)
 │    │    ├── #sidebarChatToggleBtn (AI Agent toggle button)
 │    │    └── .sidebar-status (#systemPulse, #systemLabel, #systemSub)
 │    └── main.channel-studio-main (flex column, min-width: 0, overflow: hidden)
 │         ├── header.channel-studio-topbar (82px/64px sticky topbar)
 │         │    ├── .channel-studio-page-copy (#studioPageKicker, #studioPageTitle, #studioPageHint)
 │         │    └── .channel-studio-top-actions
 │         │         ├── .global-project-switcher (#globalProjectSelect)
 │         │         ├── .studio-engine-chip ("Codex + Gemini")
 │         │         ├── button[data-open-tab="accounts"] (◈ Tài khoản)
 │         │         ├── button[data-toggle-global-chat="true"] (◆ AI Agent)
 │         │         └── button[data-open-tab="create"] (＋ Video mới)
 │         └── .channel-studio-content (flex: 1, overflow-y: auto, padding: 16px 18px 32px)
 │              └── [data-app-pane="..."] (Tab panes: overview, accounts, radar, create, script, voice, footage, ai_visual, visuals, edit, seo, qc, projects, producerCodexSection)
 ├── aside.global-codex-dock#globalCodexDock (Floating toggle when closed; fixed right drawer when open)
 ├── dialog#chatImageLightbox
 ├── dialog#aiVisualCardsDialog
 ├── dialog#flowAccountsDialog
 └── div#toast.toast
```

---

## 2. Layout Structure, Responsive Ergonomics & Collision Analysis

### 2.1 Viewport Matrix: Collapsed vs. Expanded Chat Dock

The application layout uses CSS grid and fixed dock positioning controlled by `body.global-chat-open` (`static/styles.css:6422-6516`):
- `--chat-dock-width`: `clamp(350px, 28vw, 400px)` (`static/styles.css:6391`).
- Sidebar: Fixed width `230px` (`static/styles.css:2422`).
- Dock Closed: `.global-codex-dock:not(.open)` is positioned at `fixed; right: 18px; bottom: 18px;` (`static/styles.css:6437-6447`). `.channel-studio-shell` has `padding-right: 0 !important;`.
- Dock Open: `.global-codex-dock.open` is `fixed; right: 0; top: 0; bottom: 0; width: var(--chat-dock-width) !important;`. `.channel-studio-shell` has `padding-right: var(--chat-dock-width) !important;`.

| Viewport Width | Chat Dock State | Sidebar Width | Dock Width | Main Content Available Width | Layout Ergonomics Assessment |
|---|---|---|---|---|---|
| **1920px (Desktop Full)** | Collapsed | 230px | 0px (Floating pill) | 1,690px | Spacious; multi-column cards, 2-column forms, comfortable margins. |
| **1920px (Desktop Full)** | Expanded | 230px | 400px (Max clamp) | 1,290px | Well-proportioned; all grids fit, zero collisions. |
| **1520px (Standard Monitor)** | Collapsed | 230px | 0px (Floating pill) | 1,290px | Standard SaaS layout; no collisions. |
| **1520px (Standard Monitor)** | Expanded | 230px | 400px (Max clamp) | 890px | `@media (max-width: 1520px)` collapses `.production-form` and `.overview-hero` to 1 column (`styles.css:6767-6778`). |
| **1280px (Laptop / HD)** | Collapsed | 230px | 0px (Floating pill) | 1,050px | Moderate density; topbar fits, workspace grids fit. |
| **1280px (Laptop / HD)** | Expanded | 230px | 358px (28vw) | **692px** | **High squeeze zone**: Topbar actions compress page title; grids lacking `body.global-chat-open` rules suffer layout clipping. |

### 2.2 Existing Layout Collisions, Overlaps, and Styling Bugs

1. **Topbar Action Squeeze vs. Page Title at 1280px (Dock Open)**:
   - File: `static/styles.css:6519-6575`, `static/index.html:59-77`.
   - Selector: `.channel-studio-topbar`, `.channel-studio-top-actions`, `.global-project-switcher`.
   - Observation: With dock open at 1280px, available width is only 692px. Inside `.channel-studio-top-actions`, `#globalProjectSelect` has `width: clamp(170px, 19vw, 265px) !important;` (243px at 1280px). Three buttons ("◈ Tài khoản" ~90px, "◆ AI Agent" ~95px, "＋ Video mới" ~105px) plus gaps take ~557px total.
   - Consequence: `.channel-studio-page-copy` is squeezed into 135px (`692px - 557px`). While text-overflow ellipsis prevents overflow wrap, page title and kicker become almost illegible.
2. **`.seo-clean-hub` Grid Breakpoint Discrepancy**:
   - File: `static/styles.css:6362-6375`.
   - Selector: `.seo-clean-hub`.
   - Observation: `.seo-clean-hub` is defined as `grid-template-columns: repeat(2, minmax(0, 1fr));` and only switches to 1 column at `@media (max-width: 1024px)`.
   - Bug: When the user is on a 1280px viewport and opens the chat dock, the window width is 1280px (so `@media (max-width: 1024px)` does NOT trigger), but `.channel-studio-content` width is only 692px. This forces `.seo-clean-hub` into two narrow 339px columns containing large SEO cards with multiple copy buttons, title options, and tags.
3. **`.inline-fields` Lacking `flex-wrap: wrap` in Step 0**:
   - File: `static/styles.css:182-184`, `static/index.html:180-186`, `205-210`.
   - Selector: `.inline-fields`, `.radar-filter-fields`.
   - Bug: `.inline-fields { display: flex; gap: 7px; margin-bottom: 10px; }` has no `flex-wrap: wrap;`. In `#marketScanForm`, there are 5 fields (Chế độ, Sub tối đa, Tuổi kênh tối đa, Kênh chứng minh, Video nổ). At 692px width, each input shrinks below its min-width or overflows the card boundary horizontally.
4. **Floating Chat Dock Toggle Collision with Bottom Action Bars**:
   - File: `static/styles.css:6437-6447`.
   - Selector: `.global-codex-dock:not(.open) .global-codex-toggle`.
   - Bug: When closed, the floating toggle is fixed at `bottom: 18px; right: 18px; z-index: 1200;`. In forms with bottom submit buttons (`.submit-row` in `#jobForm`) or wide tables, the pill can hover directly over primary buttons or right-aligned controls if the user scrolls to the bottom.
5. **Multiple Conflicting CSS Layers in `styles.css`**:
   - File: `static/styles.css:1-120`, `1920-2075`, `2420-2550`, `6380-6781`.
   - Observation: There are 3 competing definitions of `.channel-studio-shell` and `.channel-studio-sidebar` in `styles.css`:
     - Line 1925: `grid-template-columns: 240px minmax(0, 1fr); background: radial-gradient...`
     - Line 2422: `grid-template-columns: 230px minmax(0, 1fr); background: ... #09090b !important;`
     - Line 6423: `.channel-studio-shell { width: 100% !important; max-width: 100vw !important; ... }`
   - While the `!important` declarations on line 6423 take precedence, the legacy layers introduce redundant rules and styling fragmentation.

---

## 3. Workflow Tabs & Workspaces Deep-Dive (Step 0 to Step 08)

The application implements a 9-stage documentary pipeline plus management views. Below is the technical breakdown of each tab:

| Step / Tab | Pane Selector & App Tab | Main JS Renderer | Manual Controls Implemented | AI Agent Synchronization & Endpoints |
|---|---|---|---|---|
| **Step 0: Channel DNA & Radar** | `#chu-de`<br>`data-app-pane="radar"`<br>`tab: "radar"` | `loadChannelProfiles()`<br>`renderChannelProfileCards()`<br>`fillChannelProfileForm()` | - Form `#channelProfileForm` (DNA rulebook inputs: label, market, duration, visual strategy, DNA mode, own YouTube ref, allowed/forbidden topics, green monetization policy).<br>- Market scan form `#marketScanForm`.<br>- Preset button `#presetTrueCrimeCnBtn`.<br>- Create profile button `#newChannelProfileBtn`.<br>- Profile cards library & dialog. | - `POST /api/radar/channel-profiles` (Create).<br>- `PATCH /api/radar/channel-profiles/{id}` (Update).<br>- `POST /api/radar/channel-profiles/{id}/refresh` (YouTube scan sync).<br>- `POST /api/radar/channel-profiles/{id}/today` (DNA topic proposals).<br>- `POST /api/radar/channel-profiles/{id}/plan-30-days` (30-day schedule).<br>- AI Chat action `radar_results` renders candidate items directly. |
| **Step 00: Create Project** | `#tao-video`<br>`data-app-pane="create"`<br>`tab: "create"` | `applySelectedProfileToCreateStep()`<br>`collectCreateCreativeBrief()`<br>`#jobForm.submit` | - Form `#jobForm`.<br>- Channel profile selector `#createChannelProfileSelect`.<br>- Discovery mode switch (DNA Strict vs Radar Trend).<br>- Manual title input `#createManualTitleInput`.<br>- Market, language, target duration dropdowns.<br>- Creative Brief Studio (Tầng 1A draft: Narrative Angle, Writing Style, Hook Archetype, Editing Archetypes, Opening Hook, Outline Banner).<br>- Engine selector (`codex` vs `gemini`).<br>- Visual strategy radio group (`full_ai`, `full_footage`, `hybrid`, `evidence_footage`).<br>- AI visual config (media mode, style mode, style preset, custom style, reference image upload).<br>- Voice selector and speed slider.<br>- Submit buttons: "Tạo & Chạy tự động Full" vs "Tạo dự án (chạy từng bước)". | - `POST /api/jobs` (Create job).<br>- `POST /api/jobs/from-radar` (Create from radar candidate).<br>- `PATCH /api/jobs/{id}/ai-visual-settings` (**Bug**: triggered on draft input changes).<br>- AI Chat action `fill_create_form` and proposal card button "Đẩy vào Form Tạo" (`applyCreativeProposalToCreateForm`).<br>- Chat button "Tạo ngay" calls `POST /api/jobs` directly with draft + proposal values. |
| **Step 01: Script & Outline** | `#scriptWorkspace`<br>`data-app-pane="script"`<br>`tab: "script"` | `renderScriptWorkspace(job)` | - Phase control panel (Run/Rerun Plan, Next step: Voice).<br>- Summary pill bar.<br>- Tầng 1A (Creative Brief & Playbook Drawer): Select playbook, edit angle, style, hook, editing archetypes, opening hook, notes; "💾 Lưu Định hướng", "🧬 Đúc kết thành Playbook".<br>- Tầng 1B (Outline Drawer): Add chapter, delete, move up/down, edit title, summary, evidence anchor, target duration; "💾 Lưu Dàn ý", "⚡ Sinh lại kịch bản từ dàn ý".<br>- Tầng 2: Direct Markdown Script Editor (`#scriptDirectEditor`) with auto-save / manual save.<br>- Tầng 3: Visual Storyboard table.<br>- Research report viewer (`research.md`). | - `POST /api/jobs/{id}/plan` (Run plan).<br>- `GET /api/jobs/{id}/outline` & `PATCH /api/jobs/{id}/outline`.<br>- `PATCH /api/jobs/{id}/creative-brief`.<br>- `PATCH /api/jobs/{id}/script-direct` (Direct script save).<br>- `POST /api/jobs/{id}/extract-playbook`.<br>- AI Chat actions `update_script`, `update_creative_brief`, `update_outline` invalidate cached signatures and trigger re-render. |
| **Step 02: Voice & SRT** | `#voiceWorkspace`<br>`data-app-pane="voice"`<br>`tab: "voice"` | `renderVoiceWorkspace(job)` | - Phase control panel (Run/Rerun Voice, Next: Visuals).<br>- Voice Clone subtab (upload audio file 5-25s, clone name, language).<br>- Voice Design subtab (instruct prompt, age/tone presets, language).<br>- Quick TTS Preview subtab.<br>- Country / language filter pills (`countryCodes`).<br>- Voice cards grid with audio preview player (play/pause/waveform).<br>- Voice speed slider and "Áp dụng giọng cho dự án" button.<br>- Manifest (`voice_manifest.json`) and subtitle (`subtitles.srt`) viewers. | - `POST /api/jobs/{id}/voice` (Run voice generation).<br>- `PATCH /api/jobs/{id}/voice` (Update voice selection & speed).<br>- `POST /api/voice/clone` & `POST /api/voice/design`.<br>- `POST /api/voice/preview`.<br>- `POST /api/voice/start` (Auto-start headless CofiVoice engine). |
| **Step 03: Visuals & Prompting** | `#visualsWorkspace`<br>`data-app-pane="visuals"`<br>`tab: "visuals"` | `renderVisualsWorkspace(job)` | - Phase control panel (Run/Rerun Visuals, dynamic Next button routing to `ai_visual` if `full_ai`, else `footage`).<br>- Visual routing strategy toolbar.<br>- Storyboard table mapping 100% voice lines to visual prompts.<br>- Code viewers for `visual_prompts.json` and `visual_manifest.json`. | - `POST /api/jobs/{id}/visuals` (Generate visual manifest & STP prompts).<br>- AI Agent inspects `visual_prompts.json` via artifact endpoint. |
| **Step 04: Footage** | `#footageWorkspace`<br>`data-app-pane="footage"`<br>`tab: "footage"` | `renderFootageWorkspace(job)` | - Phase control panel (Run/Rerun Footage, Next: `ai_visual` or `edit`).<br>- Footage controls (Pause / Resume / Retry / Stop).<br>- Live progress bar (completed beats vs total beats, stage percentage).<br>- Tool stage indicators (searching, ranking, preparing, reviewing, slicing).<br>- Candidate cards with video preview, poster image, decision badges (`APPROVED`, `REVIEW`, `REJECT`), visual match, context match, rights risk.<br>- "Hiển thị thêm" pagination controls.<br>- Coverage matrix, asset registry, preflight report viewers. | - `POST /api/jobs/{id}/footage` (Run footage pipeline).<br>- `GET /api/jobs/{id}/footage-live` (Live polling stream).<br>- `POST /api/jobs/{id}/footage-control` (Pause/Resume/Cancel).<br>- Multi-agent review loop (DDGS, yt-dlp, Archive.org, Library of Congress, Wikimedia, Openverse -> semantic ranking -> AI review). |
| **Step 05: AI Visual** | `#aiVisualWorkspace`<br>`data-app-pane="ai_visual"`<br>`tab: "ai_visual"` | `renderAIVisualWorkspace(job)` | - Phase control panel (Run/Rerun AI Visual, Next: Edit).<br>- Embedded Cofi Studio iframe (`#cofiStudioFrame`).<br>- AI media cards summary (target beats, created clips, fallback images, errors).<br>- Card gallery dialog `#aiVisualCardsDialog`. | - `POST /api/jobs/{id}/ai-visual` (Execute AI visual generation).<br>- `GET/PATCH /api/jobs/{id}/ai-visual-settings`.<br>- PostMessage communication with embedded Cofi Studio iframe. |
| **Step 06: Edit / Remotion** | `#editWorkspace`<br>`data-app-pane="edit"`<br>`tab: "edit"` | `renderEditWorkspace(job)` | - Persistent editor shell (`.persistent-editor-shell`).<br>- Remotion Studio session status (`data-edit-status`).<br>- "Bật Remotion Studio" / "Mở đúng preview" button (`#startWorkspaceStudioBtn`).<br>- Embedded Remotion Studio iframe or composition preview shell.<br>- Live render cache progress bar (`editProgressHtml`).<br>- Edit checkpoint viewer (`edit_checkpoint.json`).<br>- **Missing**: "Lock Approved Edit Style to Channel" action & YouTube Policy/Sync scorecard. | - `POST /api/jobs/{id}/remotion/start` (Launch Remotion studio).<br>- `GET /api/jobs/{id}/remotion` (Session status).<br>- `POST /api/jobs/{id}/edit` (Run automated editing pass). |
| **Step 07: SEO & Thumbnail** | `#seoWorkspace`<br>`data-app-pane="seo"`<br>`tab: "seo"` | `renderSeoWorkspace(job)`<br>`thumbnail_studio.js` | - Phase control panel (Run/Rerun SEO, Next: QC).<br>- Cofi Thumbnail Studio host (`#cofiThumbnailStudioHost`):<br>  - Multi-card test gallery (3+ variants: A, B, C, D).<br>  - Lightbox zoom preview modal (`#chatImageLightbox`).<br>  - Per-card download button (`downloadSingleVariant`).<br>  - Batch download button (`#thumbDownloadAllBtn`).<br>  - "Vẽ 3 ảnh nền Flow mới" button (`#thumbBatchFlowBtn`).<br>  - Fabric.js layer editor (canvas text, badge, repositioning).<br>- SEO Copy Hub (clean 2-column layout):<br>  - Recommended title card with prominent 1-click copy.<br>  - Title alternative options with per-option copy.<br>  - Description + hashtags copy card.<br>  - Video tags (comma-separated for YouTube Studio) copy card.<br>  - Core SEO keywords copy card.<br>  - Thumbnail text hook cards with Korean + Vietnamese meaning.<br>- Channel framework card (`channel_framework`). | - `POST /api/jobs/{id}/seo` (Generate SEO package & prompts).<br>- `GET /api/jobs/{id}/thumbnail-studio` (Studio state).<br>- `POST /api/jobs/{id}/thumbnail-studio/auto-design`.<br>- `POST /api/jobs/{id}/thumbnail-studio/generate-bg` (Google Labs Flow integration).<br>- `POST /api/jobs/{id}/thumbnail-studio/export`. |
| **Step 08: QC & Export** | `#qcWorkspace`<br>`data-app-pane="qc"`<br>`tab: "qc"` | `renderQcWorkspace(job)` | - Phase control panel (Run/Rerun QC / Xuất video).<br>- Export progress meter (hardware profile, percent, stage, ETA).<br>- Final MP4 video player (`video.final-video`) with direct HTML5 controls.<br>- Direct "Tải video" download link.<br>- Technical Director report (`director_report.md`).<br>- Final and render manifest technical viewers. | - `POST /api/jobs/{id}/qc` (Execute final render).<br>- `GET /api/jobs/{id}/export-progress` (Real-time render progress).<br>- Artifact streaming (`/api/jobs/{id}/artifacts/...`). |

---

## 4. Frontend State Architecture & Isolation Survey (R2 & AC2)

### 4.1 Global State Map (`state` Object)

The entire application runs off a single global mutable JavaScript object `state` declared at `static/app.js:1-34`:

```javascript
const state = {
  jobs: [],                          // All jobs returned by /api/jobs
  selectedId: null,                  // Currently selected/active project ID (string)
  selectedRadar: null,               // Currently selected radar item
  selectedChannelPlan: null,         // Currently selected 30-day plan item
  selectedCreateTopic: null,         // Currently selected topic proposal
  createTopicSuggestions: [],        // Topic suggestions in Step 00
  channelProfiles: [],               // All channel profiles returned by /api/radar/channel-profiles
  selectedChannelProfileId: null,    // Currently selected channel profile in Step 0
  radarItems: [],                    // Market radar feed items
  voices: [],                        // CofiVoice voice list
  health: null,                      // System health & AI engine routing status
  appTab: "overview",                // Active navigation tab
  detailTab: "tongquan",             // Active detail subtab in projects view
  logPhase: "plan",                  // Active log viewer phase
  editJobId: null,                   // Job ID attached to Remotion iframe
  editStudioUrl: null,               // URL of running Remotion studio
  editChatOpen: true,                // Legacy edit chat flag
  producerChatAttachments: [],       // Attachments for inline producer chat
  globalCodexOpen: ...,              // Global chat dock open/closed (persisted in localStorage)
  globalCodexAttachments: [],        // Attachments for global chat dock
  globalCodexContext: null,          // Synced context payload sent to AI agent
  ...
  workspaceRenderKeys: {},           // Cache keys preventing redundant DOM rewrites
  chatRunConnections: {},            // Active SSE/stream connections
};
```

### 4.2 Step 0 Channel Profile Selection, Loading & Population

- **Loading (`loadChannelProfiles`, `static/app.js:2522-2562`)**:
  - Fetches `GET /api/radar/channel-profiles`.
  - Sets `state.channelProfiles = profiles`.
  - Populates `<select id="channelProfileSelect">` in Step 0 and `<select id="createChannelProfileSelect">` in Step 00.
  - If no profile is selected, it defaults to `channel-e544a64b7c` or the first profile.
  - Calls `fillChannelProfileForm(currentChannelProfile())`.
- **Population (`fillChannelProfileForm`, `static/app.js:2395-2428`)**:
  - Populates: `label`, `market`, `default_language`, `default_duration_minutes`, `default_visual_strategy`, `dna_mode`, `own_channel_ref`, `voice_and_structure`, `reference_image_policy`, `allowed_topics`, `forbidden_topics`, `monetization_safety_policy`, `competitor_refs`.
  - **Omissions**:
    - Does NOT populate or inspect `editing_dna` (shot pacing, Remotion archetypes, color grading, subtitle typography).
    - Does NOT populate or inspect `default_creative_brief`.
    - Does NOT populate or inspect `notes` or `custom_rules`.

### 4.3 Step 00 (Create Project) Draft Inputs vs. Active Project (`state.selectedId`)

- **The Leakage Mechanism (`syncCreateStyleToActiveJob`, `static/app.js:2785-2802`)**:
  ```javascript
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
  ```
- **Event Listeners Triggering the Leak (`static/app.js:3315-3343`)**:
  - `$$('#jobForm input[name="ai_media_mode"]').forEach(input => input.addEventListener("change", syncCreateStyleToActiveJob));`
  - `$("#createAiStyleMode")?.addEventListener("change", ... syncCreateStyleToActiveJob);`
  - `$("#createAiStylePreset")?.addEventListener("change", ... syncCreateStyleToActiveJob);`
  - `$("#createAiCustomStyle")?.addEventListener("change", ... syncCreateStyleToActiveJob);`
  - `$("#createStyleReferenceInput")?.addEventListener("change", ... uploadCreateStyleReference(state.selectedId));`
- **Impact**:
  Whenever a user clicks "＋ Tạo video mới" or switches to the Create Project tab and adjusts any AI media option (e.g., selecting "Chỉ ảnh", picking a different art preset, typing a custom style, or attaching a reference photo) for their upcoming project, the code immediately dispatches `PATCH /api/jobs/{state.selectedId}/ai-visual-settings`.
  If `state.selectedId` holds a currently running or completed project, its database and workspace settings are modified in real time without the user's intent or awareness.

### 4.4 Profile Bleeding Between Channel Profiles in Step 00

- **The Bleeding Mechanism (`applySelectedProfileToCreateStep`, `static/app.js:2473-2514`)**:
  When `#createChannelProfileSelect` changes:
  ```javascript
  const defaultBrief = profile.default_creative_brief || edDna.default_creative_brief;
  if (defaultBrief && typeof defaultBrief === "object") {
    applyCreativeProposalToCreateForm({
      market,
      target_duration_minutes: profile.default_duration_minutes || 30,
      visual_strategy: vs || undefined,
      creative_brief: defaultBrief,
    }, { switchTab: false, silent: true });
  }
  ```
- **The Target Function (`applyCreativeProposalToCreateForm`, `static/app.js:3036-3094`)**:
  ```javascript
  if (brief.narrative_angle && $("#createNarrativeAngle")) {
    $("#createNarrativeAngle").value = humanizeCreativeKey("narrative_angles", brief.narrative_angle);
  }
  if (brief.writing_style && $("#createWritingStyle")) {
    $("#createWritingStyle").value = humanizeCreativeKey("writing_styles", brief.writing_style);
  }
  if (brief.hook_archetype && $("#createHookArchetype")) {
    $("#createHookArchetype").value = humanizeCreativeKey("hook_archetypes", brief.hook_archetype);
  }
  const archetypesRaw = brief.editing_archetypes || brief.editing_grammar;
  if (archetypesRaw && (Array.isArray(archetypesRaw) ? archetypesRaw.length : String(archetypesRaw).trim())) {
    setCheckedEditingArchetypes(archetypesRaw, "#createEditingArchetypesInput");
  }
  if (brief.opening_hook != null && String(brief.opening_hook).trim() && $("#createOpeningHookInput")) {
    $("#createOpeningHookInput").value = String(brief.opening_hook).trim();
  }
  const rulesText = brief.custom_rules || proposal.notes || proposal.why_it_works || "";
  if (rulesText && $("#createNotesTextarea")) {
    $("#createNotesTextarea").value = String(rulesText).trim();
  }
  ```
- **Consequence**:
  Form inputs are updated **strictly via truthy guards** (`if (brief.field)`). If Profile A has `narrative_angle = "Điều tra Hồ sơ Mật & Pháp y"` and Profile B has no `default_creative_brief` or `narrative_angle = null`, Profile B never resets `#createNarrativeAngle`.
  The value from Profile A remains in the input field! The same bug affects `writing_style`, `hook_archetype`, `editing_archetypes`, `opening_hook`, `notes`, and attached outlines.

### 4.5 Separation of Profile Actions ("Create New", "Clone", "Update")

- **Form Wiring (`#channelProfileForm`, `static/app.js:2620-2674`)**:
  - There is only one save button: `#saveChannelProfileBtn`.
  - The submit handler checks:
    ```javascript
    const profileId = state.selectedChannelProfileId;
    const url = profileId ? `/api/radar/channel-profiles/${encodeURIComponent(profileId)}` : "/api/radar/channel-profiles";
    const saved = await api(url, { method: profileId ? "PATCH" : "POST", body: JSON.stringify(payload) });
    ```
  - **No "Clone Profile" Button**: The UI has no action to duplicate an existing profile into a new record with a unique ID and `(Clone)` title.
  - **Accidental Overwrite on Preset Load**:
    When the user clicks "⚡ Chuẩn True Crime TQ" (`#presetTrueCrimeCnBtn`, `static/app.js:2127-2143`), the handler writes the preset strings into form elements (`label.value = ...`, `market.value = ...`, etc.), but **does NOT clear `state.selectedChannelProfileId`**.
    If the user previously had `channel-1e24de3ab5` selected, clicking the preset and then clicking "Lưu Hồ sơ DNA Kênh" dispatches `PATCH /api/radar/channel-profiles/channel-1e24de3ab5`, completely destroying and overwriting `channel-1e24de3ab5`'s original identity!
  - **Only `+ Tạo profile mới` resets `state.selectedChannelProfileId`**:
    `$("#newChannelProfileBtn")` calls `await selectChannelProfile(null)` (`static/app.js:2607-2613`), but this leaves all form fields blank; there is no option to clone or fork existing DNA.

---

## 5. Storage Integrity Audit: Existing Channel Profiles & Jobs

An inspection of `data/channel_profiles.json` and `data/jobs/*/job.json` reveals the following concrete data states:

### 5.1 Existing Channel Profiles in `data/channel_profiles.json`

| Profile ID | Profile Label | Market | Own YouTube Ref | Has `default_creative_brief`? | Has `editorial_dna`? | Has `editing_dna`? | Visual Strategy | Status / Required Remediation |
|---|---|---|---|---|---|---|---|---|
| `channel-aa913eb90d` | bí mật US | US | `https://www.youtube.com/@TheFirstFamilyVault` | **NO** (`null`) | **NO** (`null`) | **NO** (`null`) | Missing | Incomplete; needs backfill of US political/secret vault brief and editing DNA recipe. |
| `channel-f6ec4dfff3` | The First Family Vault | US | `https://www.youtube.com/@TheFirstFamilyVault` | **NO** (`null`) | **NO** (`null`) | **NO** (`null`) | Missing | Incomplete; duplicate handle to `aa913eb90d`; needs dedicated profile identity and editing DNA. |
| `channel-1e24de3ab5` | Trung Quốc -Hàn Quốc | KR | `https://www.youtube.com/@판세의이면` | **NO** (`null`) | **NO** (`null`) | **NO** (`null`) | Missing | Incomplete; high-value channel with 26 videos on geopolitics/infrastructure; needs Korean geopolitical brief and 2.5D map/satellite editing DNA. |
| `channel-e544a64b7c` | Hồ sơ Kênh True Crime Hình Sự Trung Quốc (KR - 30 Phút - Full AI) | KR | `""` (Standalone) | **YES** (5-act true crime brief) | **YES** (v2 forensic noir) | **NO** (`null`) | `full_ai` | Partial; has detailed narrative and footage rules in `editorial_dna`, but lacks structured `editing_dna` object (pacing, Remotion archetypes, subtitle rules). |

### 5.2 Existing Jobs in `data/jobs/`

| Job ID | Job Title | Market | `channel_profile_id` in `job.json` | Actual Channel Affiliation | Has `editing_dna`? | Production Recipe Strategy | Status / Required Remediation |
|---|---|---|---|---|---|---|---|
| `20261018-223750-3aecfbcd` | 중국 남수북조 1,432km 수로가 지반 침하로 뒤틀리기 시작했습니다... | KR | **`null`** (Line 179) | `channel-1e24de3ab5` (Notes explicitly state `@판세의이면`) | **NO** | `full_ai` | Disconnected profile ID; must be backfilled to `channel-1e24de3ab5` with non-null `editing_dna`. |
| `20261017-164519-fd65f7e1` | 20년간 신분을 세탁한 '미소 của 악마'... (Lao Rongzhi) | KR | **`null`** (Line 179) | `channel-e544a64b7c` (True Crime KR 30m Full AI) | **NO** | `full_ai` | Disconnected profile ID; must be backfilled to `channel-e544a64b7c` with non-null `editing_dna`. |
| `20261017-003022-ecb75736` | 30년간 4,400억을 숨긴 '청렴 공무원'... | KR | `channel-e544a64b7c` (Line 179) | `channel-e544a64b7c` | **NO** | `hybrid` | Valid profile link; needs `editing_dna` backfilled. |
| `20261015-014818-f0fdc122` | 393억 톤의 괴물.. 만약 중국 싼샤댐이 무너지면... | KR | `channel-1e24de3ab5` (Line 179) | `channel-1e24de3ab5` | **NO** | `full_ai` | Valid profile link; needs `editing_dna` backfilled. |

---

## 6. Actionable Implementation Recommendations

Based on the survey findings, the following concrete modifications should be prioritized by the team:

### 6.1 State Isolation & Disconnection (Requirement R2, AC2)
1. **Sever Draft Inputs from `state.selectedId`**:
   - In `static/app.js`, completely remove the automatic `syncCreateStyleToActiveJob()` invocations from `#jobForm` draft input listeners (lines 3315–3343).
   - Changing inputs in `#jobForm` must only mutate local draft state intended for `POST /api/jobs`. Never fire `PATCH /api/jobs/{selectedId}` from Step 00 inputs.
   - If in-place modification of an active project's visual settings is needed, it must be located exclusively in Step 05 (`ai_visual` workspace) or via an explicit "Cập nhật dự án đang chọn" button.
2. **Implement Explicit Reset in Profile Switching**:
   - In `applySelectedProfileToCreateStep` (`static/app.js:2473`) and `applyCreativeProposalToCreateForm` (`static/app.js:3036`), implement a clean reset of all brief and draft fields prior to populating:
     ```javascript
     function resetCreateDraftBriefFields() {
       $("#createNarrativeAngle").value = "";
       $("#createWritingStyle").value = "";
       $("#createHookArchetype").value = "";
       $("#createEditingArchetypesInput").value = "";
       $("#createOpeningHookInput").value = "";
       $("#createNotesTextarea").value = "";
       setCreateAttachedOutline(null);
       syncCreativeQuickChipsState();
     }
     ```
   - When switching `#createChannelProfileSelect`, call `resetCreateDraftBriefFields()` first, then populate strictly from the newly selected profile.
3. **Explicit Profile Action Buttons in Step 0**:
   - Add three explicit buttons to `#channelProfileForm`:
     - `Cập nhật Hồ sơ hiện tại` (Updates `state.selectedChannelProfileId` via `PATCH`).
     - `Nhân bản thành Hồ sơ mới (Clone)` (POSTs current values as a new record with a unique ID and `(Bản sao)` label, selecting the new ID).
     - `Tạo Hồ sơ mới (Trống)` (Resets all fields and clears `state.selectedChannelProfileId`).
   - Clicking `presetTrueCrimeCnBtn` must prompt or automatically trigger "Tạo mới / Clone" mode (`state.selectedChannelProfileId = null`) to prevent overwriting existing profiles.

### 6.2 Layout Ergonomics & CSS Optimization (Requirement R1, AC1)
1. **Responsive Rule for `.seo-clean-hub` with Chat Open**:
   - Add CSS rule:
     ```css
     body.global-chat-open .seo-clean-hub {
       grid-template-columns: 1fr !important;
     }
     ```
   - This ensures the SEO cards display in a clean single column whenever the chat dock is open on screens below `1600px`.
2. **Add `flex-wrap: wrap` to `.inline-fields`**:
   - In `static/styles.css:182`, add `flex-wrap: wrap;` so that multi-field rows in `#marketScanForm` and `#channelProfileForm` wrap gracefully into 2 rows when available width is restricted to `~692px`.
3. **Topbar Compact Mode**:
   - In `.channel-studio-topbar`, below 1400px when chat is open, collapse button labels to icons or compact pills (`◈`, `◆`, `＋`) to leave at least `220px` for `.channel-studio-page-copy`.

### 6.3 Missing Features to Add (Requirement R3, R4)
1. **"Chốt Mẫu Edit Chuẩn Cho Kênh" UI**:
   - In Step 06 (`renderEditWorkspace`), add a prominent button:
     `<button class="primary compact" id="lockApprovedEditBtn">🔒 Chốt Mẫu Edit Chuẩn Cho Kênh</button>`
   - Wire this button to call `POST /api/jobs/{job_id}/lock-edit-dna`, updating the parent Channel Profile's `editing_dna`.
2. **Compliance & Sync Scorecard**:
   - Surface a real-time scorecard in Step 06/Step 08 displaying:
     - Voice-visual beat alignment status (timestamp & semantic sync).
     - YouTube policy guardrail status (Green monetization, violence filtering, transformation score).

---

*Report prepared and submitted to `.agents/teamwork/teamwork_preview_explorer_survey_1/survey_report.md`.*
