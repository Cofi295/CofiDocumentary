# Original User Request

## Initial Request — 2026-10-18T19:37:59Z

Upgrade **CofiDocumentary** (`B:\ALL_TOOLS\CofiDocumentary`) into a professional SaaS documentary production studio where both the AI Agent and manual users can seamlessly operate every stage from Step 0 to final delivery, featuring 100% isolated Channel Profiles and Projects, persistent self-learning Editing Style memory ("Lock Approved Edit to Channel"), strict voice-visual synchronization and current YouTube monetization/policy compliance, Channel-DNA pre-flight checks before generating Topics/Titles/Thumbnails/SEO, and a closed-loop Post-Mortem Self-Learning Engine that analyzes why past channel videos won or lost and continuously upgrades each subsequent video until it wins.

Working directory: B:\ALL_TOOLS\CofiDocumentary
Integrity mode: development

## Requirements

### R1. Professional SaaS UI/UX Overhaul & Seamless Dual-Control (AI Agent + Manual User)
Upgrade the entire web/desktop interface into a cohesive, modern, high-usability SaaS studio:
- Eliminate all layout collisions, overlapping docks/headers, clipped dropdowns, and typography inconsistencies across all viewport sizes whether the right-hand AI Chat dock is collapsed or expanded.
- Ensure every workflow stage — **Step 0 (Channel DNA & Strategy Profile)**, **Step 00 (Create Project & Topic Discovery)**, **Step 01 (Script & Outline)**, **Step 02 (Voice & SRT)**, **Step 03 (Visuals & Prompting)**, **Step 04 (Footage)**, **Step 05 (AI Visual)**, **Step 06 (Edit / Remotion)**, **Step 07 (Thumbnail & SEO)**, and **Step 08 (QC & Export)** — provides intuitive, clean manual controls for the human user while remaining 100% operable by the in-app AI Agent with real-time bi-directional UI state synchronization.

### R2. Strict Channel Profile & Project Isolation + Locked Pipeline Execution
Enforce 100% isolation between every Channel Profile (`channel_profiles`) and every Project (`jobs`) across backend persistence and frontend state:
- Switching between Channel Profiles in Step 0 or Step 00 must completely reset and populate 100% of form fields exclusively from the newly selected profile, leaving zero residual data (titles, hooks, narrative angles, visual strategies, or notes) from any previously viewed profile.
- Separate "Create New Channel Profile", "Clone Profile", and "Update Existing Profile" actions so editing or applying presets never accidentally overwrites another profile.
- Disconnect the "Create New Project" draft form from the currently active project (`selectedId`) so modifying draft settings never mutates an existing running or completed project in the background.
- Once a Channel Profile is assigned to a project, lock and execute the entire production pipeline strictly according to that profile's DNA, duration, language, visual strategy (`full_ai`, `hybrid`, `evidence_footage`, `full_footage`), voice, monetization safety policy, and editing recipe from start to finish unless the user explicitly overrides the workflow for that specific project.

### R3. Persistent Editing Style Memory ("Lock Approved Edit") + Voice Sync & Realtime YouTube Policy Guardrails
Equip each Channel Profile and Project with a complete, structured **Editing Style DNA & Remotion Recipe (`editing_dna`)** (shot pacing in seconds/beat, Footage/AI/Motion mix ratio, Remotion visual archetypes such as 2.5D satellite maps, technical HUD telemetry, forensic red-string boards, archival document scanners, subtitle typography, color grading, and chapter transitions):
- Provide built-in channel editing presets (e.g., *2.5D Technical & Infrastructure Investigation*, *Forensic Noir Full-AI True Crime*, *Archival Historical Vault*) plus full custom configuration per profile.
- **Persistent Edit Learning ("Chốt Mẫu Edit Chuẩn Cho Kênh")**: When the user approves a project's edit in Step 06 (`Edit`), provide a one-click action and API that extracts the project's actual finalized editing parameters (beat pacing statistics, visual routing mix, active Remotion archetypes/components, typography, color/audio rules, and editorial rules) and saves/locks them directly into the parent Channel Profile's `editing_dna` (with version history) so all future projects on that channel automatically edit in that exact approved style.
- **Strict Audio-Visual Synchronization**: Guarantee that every visual beat (AI image, AI video, sourced footage clip, or motion overlay) is strictly aligned in both timestamp and semantic meaning with the spoken Voice/SRT narration segments, with automated detection and repair of any unaligned, missing, or frozen holds.
- **Realtime YouTube Policy & Green Monetization Guardrails**: Enforce up-to-date YouTube monetization and policy guidelines (Ad-Friendly Green Monetization, anti-repetitive/reused content compliance, transformative editorial value, and strict filtering of graphic violence/prohibited themes) across script generation, visual prompting, footage selection, and final edit QC.

### R4. Channel-DNA Pre-Flight Intelligence for Topics, Titles, Thumbnails, and SEO
Before suggesting topics or titles, designing thumbnails, or generating SEO metadata, the system must automatically run a **Channel DNA Pre-Flight Check** against the assigned Channel Profile's real YouTube channel data and project history:
- **Topic & Title Pre-Flight**: Inspect the channel's historical video catalog to verify what topics, angles, and title structures/keywords won (high views/VPH/outlier scores) vs. lost, block duplicate topics already published on the channel, and generate titles proven to win on that specific channel.
- **Thumbnail Pre-Flight**: Analyze the channel's existing YouTube thumbnails (visual composition, color palette/contrast, text overlay placement/length, subject framing, and Winning vs. Losing thumbnail patterns) before generating the 3+ testable thumbnail variants, ensuring every generated thumbnail adheres to the channel's winning visual DNA while providing zoom preview, per-card download, and batch download.
- **SEO Pre-Flight**: Cross-check channel keyword winners, tags, description structures, and chapter timestamps against the channel's proven top-performing videos before generating the project's SEO package.

### R5. Continuous Self-Learning Post-Mortem Engine (Win/Loss Diagnosis & Iterative Upgrade)
Build an automated **Channel Self-Learning & Post-Mortem Engine** for each Channel Profile:
- Automatically scan and analyze the channel's real YouTube videos (metadata, views, VPH, outlier ratios, titles, and thumbnail characteristics) alongside internal project history to classify **Winners (Outliers)** vs. **Underperformers (Low-view / Losing videos)**.
- Perform a structured diagnostic post-mortem on underperforming videos to identify concrete failure causes: *Why did it lose? Why did it fail to get views? Where is the weak point?* (e.g., weak/overused title keywords, low-curiosity thumbnail, topic outside core DNA, weak first-30s hook, pacing drop-off, or visual monotony).
- Synthesize actionable **Evolution & Upgrade Rules** (*What to Stop Doing / What to Double Down On / Concrete Hook, Title, Thumbnail, and Edit Upgrades for the Next Video*), persist them into the Channel Profile's learning memory (`self_learning_memory`), display them clearly in the UI, and automatically inject them into every subsequent project's Topic Discovery, Title/Thumbnail Design, Script Hook, and Edit phases so each new video iteratively improves until it wins.

### R6. Non-Destructive Data Preservation & Live Service Stability
- Preserve all existing SQLite databases (`data/radar.db`) and job workspaces/records (`data/jobs/`, `workspaces/`).
- Automatically backfill and repair existing Channel Profiles (`channel-1e24de3ab5`, `channel-e544a64b7c`, `channel-aa913eb90d`, `channel-f6ec4dfff3`) and existing jobs so each has complete, non-null, isolated DNA and editing configurations matching its true channel identity.

## Acceptance Criteria

### AC1. SaaS UI/UX & Dual Manual + AI Control
- [ ] Automated DOM/layout verification confirming zero overlap between `.app-shell.channel-studio-shell`, the topbar `#globalProjectSelect`, and `#globalCodexDock` across desktop and laptop viewport widths (`1280px`–`1920px`) in both collapsed and expanded chat states.
- [ ] All workflow tabs (`radar`, `create`, `script`, `voice`, `visuals`, `footage`, `ai_visual`, `edit`, `seo`, `qc`) render clean SaaS visual hierarchy and expose working manual controls + API endpoints callable by the AI Agent.

### AC2. 100% Profile & Project State Isolation
- [ ] Automated test verifying that switching between all saved Channel Profiles in Step 0 and Step 00 completely resets and populates every form field (`market`, `language`, `target_duration_minutes`, `visual_strategy`, `ai_media_mode`, `narrative_angle`, `writing_style`, `hook_archetype`, `editing_archetypes`, `opening_hook`, `notes`, `editing_dna`) with zero field bleed from previously selected profiles.
- [ ] Automated test verifying that changing inputs in the Step 00 `Create Project` form makes zero `PATCH`/`POST` mutations to the currently active project (`state.selectedId`).
- [ ] Automated test verifying that Step 0 explicitly separates "Create New Profile", "Clone Profile", and "Update Current Profile", preventing accidental overwrites when loading presets or editing channel names.
- [ ] Existing profiles (`channel-1e24de3ab5`, `channel-e544a64b7c`, `channel-aa913eb90d`, `channel-f6ec4dfff3`) and existing jobs (`20261018-223750-3aecfbcd`, `20261017-164519-fd65f7e1`, etc.) are verified in storage with complete, accurate, non-null `channel_profile_id`, `visual_strategy`, `default_creative_brief`, and `editing_dna`.

### AC3. Persistent Edit Style Memory, Voice Sync & YouTube Policy Guardrails
- [ ] Automated test verifying the **"Lock Approved Edit Style to Channel" (`POST /api/jobs/{job_id}/lock-edit-dna` or equivalent)** workflow: locking an edit on a project extracts its Remotion/editing recipe (`pacing`, `visual_mix`, `editing_archetypes`, `subtitle_style`, `color_grade`, `audio_rules`) into the Channel Profile's `editing_dna`, and creating a subsequent project on that profile automatically applies that exact recipe.
- [ ] Automated verification of Voice-Visual Synchronization and YouTube Policy Guardrails: a verification endpoint/checker validates beat-to-SRT timestamp alignment, flags any unaligned or policy-violating beats (graphic content, repetitive holds, reused-content risks), and surfaces a clear compliance & sync scorecard in the Edit/QC workspace.

### AC4. Channel DNA Pre-Flight (Topic, Title, Thumbnail, SEO) & Self-Learning Win/Loss Loop
- [ ] Automated test verifying that each Channel Profile can run/view a **Self-Learning Win/Loss Post-Mortem Report** (`GET/POST /api/radar/channel-profiles/{id}/self-learning` or equivalent) that classifies winning vs. underperforming videos on the channel, diagnoses concrete reasons why losing videos underperformed, and stores structured upgrade rules (`next_video_upgrades`, `thumbnail_dna`, `seo_dna`, `title_winner_patterns`).
- [ ] Automated test verifying that Topic/Title Discovery, SEO Generation, and Thumbnail Generation (3+ variants with zoom & single/batch download) read and apply the channel's `thumbnail_dna`, `seo_dna`, `title_winner_patterns`, and `self_learning_memory` before generating outputs, returning an explicit Pre-Flight DNA Check summary alongside the generated results.


## Follow-up — 2026-10-19T12:06:03Z

This is a single self-contained fix; keep it small and focused. Upgrade **CofiDocumentary** (`B:\ALL_TOOLS\CofiDocumentary`) with: (1) a **2-Layer Anti-Duplicate Topic Memory & Pre-Flight System** (checking both YouTube Channel History and a persistent, user-manageable Profile Produced-Topic Memory Ledger with bilingual case/entity similarity matching), and (2) **True Reference Image Fidelity & Job Workspace Persistence** so uploading a color reference image in Step 00 or Step 05 is saved to the proper job workspace, displayed with a live preview, and faithfully respected (including exact colors, character design, and art style) without ever being overridden by hardcoded "white stickman" prompts or presets.

Working directory: B:\ALL_TOOLS\CofiDocumentary
Integrity mode: development

## Requirements

### R1. Persistent Profile Produced-Topic Memory Ledger (`topic_memory`) & Interactive UI Panel
Equip each Channel Profile (`channel_profiles`) with a persistent, isolated **Produced Topic Memory Ledger (`topic_memory`)** that tracks every topic/case/subject already produced by that profile:
- Automatically backfill `topic_memory` from all existing jobs in `data/jobs/*/job.json` and `workspaces/*/input.json` (including `20261017-164519-fd65f7e1` [Lao Rongzhi 20-year case] and `20261019-185102-31983814` [Baiyin 28-year school store serial killer case / Đại án Bạch Ngân Cao Thừa Dũng] on `channel-e544a64b7c`, and `20261018-223750-3aecfbcd` [South-to-North Water Diversion 1,432km & Danjiangkou Dam expansive soil] on `channel-1e24de3ab5`).
- Automatically append a structured entry (`id`, `job_id`, `title`, `topic`, `core_entities`, `subject_keywords`, `created_at`) to the assigned profile's `topic_memory` whenever a job is created or its topic/title is updated.
- Expose REST endpoints (`GET /api/radar/channel-profiles/{profile_id}/topic-memory`, `POST /api/radar/channel-profiles/{profile_id}/topic-memory`, `DELETE /api/radar/channel-profiles/{profile_id}/topic-memory/{entry_id}`) and an interactive **"Bộ nhớ Đề tài Đã Làm của Hồ sơ"** panel in Step 0 / Step 00 where the user can view all produced topics for the selected profile, manually add a past topic/case to block, or delete an entry.

### R2. Two-Layer Anti-Duplicate Engine (Layer 1: YouTube Channel History + Layer 2: Profile Topic Memory) with Case/Entity Similarity
Upgrade both **Topic Discovery** and **Channel-DNA Pre-Flight Check** to execute two distinct anti-duplicate passes:
- **Pass 1 — YouTube Channel Video Check (`channel_history_check`)**: Compare candidate topics against all published videos on the profile's linked YouTube channel (`own_channel.videos`, `own_channel.dna.winner_titles`, and Radar DB channel history).
- **Pass 2 — Profile Produced-Topic Memory Check (`profile_memory_check`)**: Compare candidate topics against the profile's `topic_memory` ledger and all jobs belonging to `profile_id`.
- **Bilingual Case / Entity / Semantic Matching**: Detect duplicate cases/topics even when phrased differently across Korean, Vietnamese, and English (for example, matching `"28년간 학교 매점 주인으로 숨어 지낸 중국 최악의 연쇄살인범 — 형사들이 끝까지 놓치지 않은 단 하나의 지문 (Kẻ sát nhân nguy hiểm nhất ẩn mình 28 năm làm chủ tiệm tạp hóa trường học — Dấu vân tay duy nhất lật mở đại án Bạch Ngân)"` against `"28년간 학교 매점 아저씨로 숨어 지낸 '바이인시 미제 사건' của 진범..."` via shared case anchors like `28년간` + `학교 매점` / `tiệm tạp hóa trường học` / `Bạch Ngân` / `바이인` / `Cao Thừa Dũng`).
- **Strict Filtering in Topic Discovery & Explicit 2-Layer Pre-Flight UI**: Exclude any already-produced topic from `channel_profile_today` / `_discover_profile_topics_strict_dna` / `discover-topics` (never appending `already_produced` items into returned suggestions, replacing them with unproduced DNA-compliant topics), and display both Pass 1 (`Lượt 1: Check Kênh YouTube`) and Pass 2 (`Lượt 2: Check Bộ nhớ Hồ sơ`) statuses clearly in `#createPreflightSummaryBox`.

### R3. Fix Reference Image Color/Character Fidelity & Remove Hardcoded "White Stickman" Overrides
Ensure that when the user provides a Reference Image (`style_reference_image`) in Step 00 (`Create Project`) or Step 05 (`AI Visual`), the generated prompts and AI Visual pipeline faithfully follow the actual uploaded image's colors, character design, and art style:
- Remove all hardcoded `"white rounded full-body stickman/mascot character with black outlines"` / `"white marshmallow mascot"` text from `documentary/ai_visual.py` (`_prompt`) and `documentary/visuals.py` (`_prompt_for`) when a reference image is used, replacing it with an accurate, color-faithful instruction that preserves the exact character colors, clothing/body colors, proportions, linework, lighting, and visual style of the attached reference image.
- Prevent `documentary/ai_visual.py` (`settings`), `documentary/service.py` (`create_job`), and `static/app.js` from silently forcing `style_mode = "preset"` and `style_preset = "Người que (Stickman)"` when `style_mode` is `"auto"` or `"custom"` or when a Reference Image is uploaded; only apply the `"Người que (Stickman)"` preset when the user explicitly selects `style_mode == "preset"` and chooses that preset.
- Add a live Reference Image preview thumbnail, filename/hash badge, and "Xóa / Đổi ảnh tham chiếu" button in Step 00 (`#jobForm`) and Step 05 (`AI Visual`) so the user can see the exact color reference image currently attached and replace it at any time without being locked to a single cached image.

### R4. Fix `POST /api/jobs` Workspace Creation & Repair Job `20261019-185102-31983814`
- Ensure `POST /api/jobs` in `server.py` / `services/job_service.py` properly creates and initializes the isolated project workspace directory `workspaces/{job_id}` (with `input.json`, `ai_visual_settings.json`, `creative_brief.json`, `outline.json`, and `media/style_reference/`) and sets `job["workspace"]` and `job["workspace_root"]` to non-empty resolved paths so uploaded reference images and PLAN/VOICE/VISUALS artifacts are always written inside `workspaces/{job_id}` and never leaked into the repository root.
- Repair existing job `20261019-185102-31983814` by moving its root-leaked artifacts (`research.md`, `script.md`, `visual_manifest.json`, `plan_visual_manifest.json`, and `media/style_reference/style_reference.png`) into `workspaces/20261019-185102-31983814/`, updating `data/jobs/20261019-185102-31983814/job.json` with the valid `workspace` path and `custom` style mode (removing the unintended `"Người que (Stickman)"` white-character preset override), and ensuring its yellow/color reference image (`media/style_reference/style_reference.png`) is properly linked.

## Acceptance Criteria

### AC1. Two-Layer Topic Memory & Pre-Flight Deduplication
- [ ] Automated test verifying that `GET /api/radar/channel-profiles/channel-e544a64b7c/topic-memory` includes both `20261017-164519-fd65f7e1` (Lao Rongzhi 20-year case) and `20261019-185102-31983814` (Baiyin 28-year school store case), and supports `POST` (adding manual topic memory) and `DELETE` (removing an entry).
- [ ] Automated test verifying that `GET/POST /api/radar/channel-profiles/channel-e544a64b7c/preflight-check` on `"28년간 학교 매점 주인으로 숨어 지낸 중국 최악의 연쇄살인범 — 형사들이 끝까지 놓치지 않은 단 하나의 지문 (Kẻ sát nhân nguy hiểm nhất ẩn mình 28 năm làm chủ tiệm tạp hóa trường học — Dấu vân tay duy nhất lật mở đại án Bạch Ngân)"` returns `passed: false`, `duplicate_risk: true`, and structured `channel_history_check` (Layer 1) + `profile_memory_check` (Layer 2) showing the match with `20261019-185102-31983814`.
- [ ] Automated test verifying that topic discovery (`POST /api/radar/channel-profiles/channel-e544a64b7c/today`) returns zero candidates matching the already-produced Baiyin (`28년간 학교 매점` / `Bạch Ngân`) or Lao Rongzhi (`20년간 신분을 세탁` / `Lao Vinh Chi`) cases.

### AC2. Reference Image Color Fidelity & Workspace Isolation
- [ ] Automated test verifying that when a job has `style_reference_image` set (with `style_mode="custom"` or `"auto"`), `AIVisualCoordinator._prompt()` and `visuals._prompt_for()` do NOT contain `"white rounded full-body stickman"` or `"white marshmallow mascot"`, and instead instruct the generator to preserve the exact colors, character appearance, and art style of the attached reference image.
- [ ] Automated test verifying that creating a job via `POST /api/jobs` creates `workspaces/{job_id}` with non-empty `workspace` path, and uploading a `reference_image_data_url` via `PATCH /api/jobs/{job_id}/ai-visual-settings` saves the exact image bytes into `workspaces/{job_id}/media/style_reference/` without forcing `style_preset = "Người que (Stickman)"`.
- [ ] Automated verification that job `20261019-185102-31983814` has a valid `workspaces/20261019-185102-31983814` directory containing its `research.md`, `script.md`, `visual_manifest.json`, and its color reference image `media/style_reference/style_reference.png`, with `style_mode: "custom"` (not `"Người que (Stickman)"`).


## Follow-up — 2026-10-19T19:03:29Z

Upgrade **CofiDocumentary** (`B:\ALL_TOOLS\CofiDocumentary`) and its integrated **Media Factory** (`B:\ALL_TOOLS\CofiDocumentary\vendor\media_factory`) with three core production upgrades:
1. **Smart Google Flow Browser Profile Cache Cleanup & Complete Disk Removal on Account Deletion**
2. **Persistent Channel SEO Keyword DNA Across Channel Profiles & Linked Projects** (e.g., locking core title/SEO keyword anchors such as *"Vụ Án Có Thật ở Trung Quốc"* / `중국 실화 사건` for the Chinese True Crime channel)
3. **Consistent Channel Thumbnail Design DNA & Multi-Variant Thumbnail A/B Testing Studio**

Working directory: B:\ALL_TOOLS\CofiDocumentary
Integrity mode: development

## Requirements

### R1. Smart Google Flow Profile Cache Cleanup & Complete Disk Removal on Account Deletion
In `vendor/media_factory/backend/app/providers/google.py`, `vendor/media_factory/backend/app/routes/accounts.py`, `documentary/service.py`, `app.py`, and `static/app.js`:
- **Complete Disk Cleanup on Account Deletion**:
  - When any Google Flow account is deleted (`GoogleFlowAccountManager.remove(account_id)`) or pruned (`prune_dead_accounts` / `check_all_accounts(prune_dead=True)`):
    1. Immediately close any active browser session (`login_worker.close_session(account_id)`) and terminate any lingering Chrome/Playwright processes bound to that profile path (`_terminate_profile_processes(profile_dir)`).
    2. Delete the account's secret session file (`secret_store.delete_google_session(account_id)` in `data/media_factory/secrets/google-flow/`).
    3. Completely remove the account's persistent Chromium profile folder on disk (`data/media_factory/google-flow-profiles/{account_id}` and any custom `profile_dir` recorded on the account resource) with retry/read-only file handling on Windows (`shutil.rmtree(..., onerror=...)`).
- **Smart Profile Cache Eviction & Orphan Profile Cleanup**:
  - Implement a smart cache cleanup utility (`clean_profile_caches` / `POST /api/v1/accounts/google-flow/clean-cache` in Media Factory + proxy endpoint in CofiDocumentary + UI button "Dọn Cache Thông Minh" in the Flow Account Manager modal) that:
    1. Evicts heavy, non-essential Chromium cache & crash directories inside each profile (`Default/Cache`, `Default/Code Cache`, `Default/GPUCache`, `Default/DawnCache`, `Default/DawnWebGPUCache`, `Default/GrShaderCache`, `Default/ShaderCache`, `Default/Service Worker/CacheStorage`, `Default/Service Worker/ScriptCache`, `ShaderCache`, `GrShaderCache`, `GraphiteDawnCache`, `Crashpad`, `BrowserMetrics`, `component_crx_cache`) **without** touching authentication/session files (`Default/Cookies`, `Default/Network/Cookies`, `Default/Local Storage`, `Default/Session Storage`, `Default/IndexedDB`, `Default/Preferences`, `Local State`).
    2. Detects and deletes **orphan profile folders** in `data/media_factory/google-flow-profiles/` and orphan session files in `data/media_factory/secrets/google-flow/` whose account IDs no longer exist in the database.
    3. Automatically runs lightweight cache eviction whenever a browser session closes (`close_session` / `_evict_oldest_session_locked`) and exposes disk usage stats (`total_size_mb`, `freed_mb`, `orphan_profiles_removed`, `cleaned_profiles_count`) in the UI.

### R2. Persistent Channel SEO Keyword DNA Across Channel Profiles & Projects
In `documentary/radar.py`, `documentary/service.py`, `documentary/models.py`, `app.py`, `static/index.html`, and `static/app.js`:
- **Channel SEO Keyword DNA Schema (`seo_keyword_dna` / `seo_dna`)**:
  - Extend each Channel Profile (`data/channel_profiles.json`) and Project (`jobs`) with a structured **SEO Keyword DNA** configuration:
    - `primary_title_keyword`: Core mandatory keyword phrase in the channel's target broadcast language (e.g., `중국 실화 사건` / `중국 강력범죄 실화` for the Korean-market Chinese True Crime channel `channel-e544a64b7c` `특급수배록`).
    - `primary_title_keyword_meaning_vi`: Vietnamese meaning/label for the creator (e.g., `"Vụ Án Có Thật ở Trung Quốc"`).
    - `keyword_placement_rule`: Flexible smart SEO placement by default (`smart_seo_flexible` — prioritizing `[중국 실화 사건]` prefix bracket or `Title | 중국 실화 사건` depending on hook structure, while allowing per-channel lock to `prefix_bracket`, `suffix_pipe`, or `natural_hook`).
    - `secondary_anchor_keywords`: List of recurring niche SEO keywords (e.g., `["중국 미제사건", "실제 사건 파일", "공안 수사 기록", "특급수배록"]`).
    - `mandatory_hashtags` & `default_seo_tags`: Persistent channel-wide tags and hashtags automatically merged into every video's YouTube SEO package.
- **Cross-Pipeline SEO Keyword Enforcement**:
  - Pre-configure existing Channel Profiles (`channel-e544a64b7c` Chinese True Crime `특급수배록` with `"Vụ Án Có Thật ở Trung Quốc"` / `중국 실화 사건`, `channel-1e24de3ab5` Chinese Megaprojects & Geopolitics `판세의 이면`, `channel-aa913eb90d`, `channel-f6ec4dfff3`) with accurate, non-empty `seo_keyword_dna`.
  - When a project is linked to a Channel Profile:
    1. **Step 00 (Topic & Title Suggestions / Idea Generation)**: Every generated/suggested video title must incorporate or align with the channel's `primary_title_keyword` and `secondary_anchor_keywords` (displaying both the target-language title and Vietnamese translation + SEO Keyword DNA badge).
    2. **Step 01 (Script & Hook)** & **Step 07 (Thumbnail & SEO Package)**: Automatically inject and validate the channel's `primary_title_keyword`, `secondary_anchor_keywords`, description keyword hooks, and `mandatory_hashtags` so 100% of videos on the channel build unified topical authority on YouTube.

### R3. Consistent Channel Thumbnail Design DNA & Multi-Variant Thumbnail A/B Testing Studio
In `documentary/radar.py`, `documentary/service.py`, `app.py`, `static/index.html`, and `static/app.js`:
- **Persistent Channel Thumbnail Design DNA (`thumbnail_dna`)**:
  - Store and lock the channel's visual thumbnail identity on the Channel Profile and inherit it across all projects on that channel:
    - `style_preset` & `visual_signature` (e.g., Cold Forensic Noir + 2D Golden Detective Mascot `#FFE84A` for `channel-e544a64b7c`).
    - `reference_character_path` / `mascot_lock` (automatically linking the channel's reference character image so thumbnails and visual prompts stay consistent across the entire channel).
    - `color_palette` (primary background, accent highlight, danger/alert badge color), `typography_preset` (font family, stroke/shadow style, max words/line, color contrast rule), and `layout_template` (subject placement, evidence badge, top/side hook text layout).
  - Provide a **"Lưu & Khóa DNA Thumbnail Kênh" (Lock Thumbnail DNA to Channel)** action in Step 0 and Step 07 so any adjustments to thumbnail style, font, color palette, or reference character are saved persistently to the Channel Profile.
- **Thumbnail A/B Testing Studio (Step 07)**:
  - Upgrade Step 07 (`Thumb & SEO`) with a dedicated **Thumbnail A/B Test Studio**:
    1. Generate and manage **3 distinct A/B/C Test Variants** per project that strictly preserve 100% of the Channel's Thumbnail Design DNA (same brand palette, typography style, and mascot/visual aesthetic) while testing 3 distinct psychological click angles:
       - **Variant A (Curiosity / Paradox / Shocking Number Hook)**
       - **Variant B (Character / Forensic Evidence Close-Up / Emotion Hook)**
       - **Variant C (Confrontation / Dual-Contrast Before-After / Mystery File Hook)**
    2. Compute and display **A/B Test Readiness & CTR Prediction Scores** for each variant (measuring DNA consistency, text legibility/word count, emotional curiosity gap, and keyword alignment).
    3. Allow the user to compare Variants A, B, and C side-by-side (including YouTube Home/Sidebar feed preview), select a **Primary Winner** or export the **A/B/C Test Pack** for YouTube Studio's native *"Test & Compare"* feature, and feed winning variant patterns back into the Channel Profile's `thumbnail_dna`.

### R4. Non-Destructive Preservation of Active Jobs & Databases
- Do **not** interrupt, reset, or delete the currently running AI Visual job (`20261019-185102-31983814`) or any existing project workspaces (`workspaces/`, `data/jobs/`) or SQLite databases (`data/radar.db`, `data/media_factory/media_factory.db`).
- Only delete Google Flow profile folders for accounts that are explicitly deleted or orphan folders that do not belong to any registered account in `media_factory.db`.

## Acceptance Criteria

### AC1. Smart Google Flow Profile Cache & Account Deletion Cleanup
- [ ] Automated test verifying that deleting a Google Flow account (`DELETE /api/v1/accounts/google-flow/{account_id}` / `GoogleFlowAccountManager.remove`) removes the DB record, deletes the secret session file, and completely deletes the profile directory on disk (`google-flow-profiles/{account_id}`).
- [ ] Automated test verifying that the Smart Cache Cleanup (`clean_profile_caches` / `POST /api/v1/accounts/google-flow/clean-cache`) removes Chromium cache subdirectories (`Default/Cache`, `Default/Code Cache`, `Default/GPUCache`, `Default/Service Worker/CacheStorage`, etc.) and orphan profile directories while preserving `Default/Cookies`, `Default/Network/Cookies`, `Default/Local Storage`, and `Local State` of active accounts.

### AC2. Channel SEO Keyword DNA Enforcement
- [ ] Automated test verifying that Channel Profiles persist `seo_keyword_dna` (including `primary_title_keyword`, `primary_title_keyword_meaning_vi`, `secondary_anchor_keywords`, `keyword_placement_rule`, and `mandatory_hashtags`) and that `channel-e544a64b7c` is configured with the core keyword meaning `"Vụ Án Có Thật ở Trung Quốc"` (`중국 실화 사건` / `중국 강력범죄 실화`).
- [ ] Automated test verifying that Topic/Title generation and Step 07 SEO generation for a project linked to a Channel Profile automatically enforce the channel's `primary_title_keyword` and `secondary_anchor_keywords` in generated titles, descriptions, and tags.

### AC3. Channel Thumbnail Design DNA & A/B Testing Studio
- [ ] Automated test verifying that Channel Profiles persist `thumbnail_dna` (palette, typography, layout rules, reference character lock) and that updating/locking Thumbnail DNA on a project updates the parent Channel Profile.
- [ ] Automated test verifying that Step 07 generates 3 distinct A/B/C thumbnail test variants adhering to the channel's `thumbnail_dna`, returns per-variant A/B CTR scorecards + psychological hook labels, and supports selecting a primary variant or exporting the A/B/C test pack.


## Follow-up — 2026-10-23T17:41:06Z

Integrate the **True Crime Vox & Real Satellite Multi-Archetype Engine** (from `b:\ALL_TOOLS\CofiBlenderStudio\vox_editorial_artist.py` and `b:\ALL_TOOLS\CofiBlenderStudio\vox_archetype_expansion.py`) into **CofiDocumentary** (`b:\ALL_TOOLS\CofiDocumentary`) with **AI Agent semantic voice-driven archetype selection**, and upgrade the **CofiDocumentary UI/UX** (`static/index.html`, `static/styles.css`, `static/app.js`, `static/thumbnail_studio.js`) guided by the workspace UI skills (`C:\Users\koing\.gemini\config\skills\agency-ui-designer\SKILL.md` and `b:\.agents\skills\design-system\SKILL.md`), featuring a **maximized Thumbnail Canvas workbench at the top of Tab 07 (`SEO + Thumbnail`)** and **collapsible Accordion drawers below for SEO packaging**.

Working directory: `b:\ALL_TOOLS\CofiDocumentary`
Integrity mode: `development`

## Reference Resources & Skills
- **True Crime Vox & Real Satellite Reference Engine**:
  - `b:\ALL_TOOLS\CofiBlenderStudio\vox_editorial_artist.py` (Core 9 archetypes `#D1..#D3`, `#M1..#M4`, `#P1..#P2` + Esri World Imagery `Z6/Z9/Z14/Z16` tile cache & HUD helpers)
  - `b:\ALL_TOOLS\CofiBlenderStudio\vox_archetype_expansion.py` (Expanded 8 archetypes `#M5..#M7`, `#D4..#D6`, `#D9`, `#P3`)
  - `b:\ALL_TOOLS\CofiBlenderStudio\vox_gis_cache\` (Real satellite imagery plates & metadata)
- **UI/UX Design Skills (MUST read and apply)**:
  - `C:\Users\koing\.gemini\config\skills\agency-ui-designer\SKILL.md`
  - `b:\.agents\skills\design-system\SKILL.md`

## Requirements

### R1. Voice-Driven Semantic Integration of the True Crime Vox & Real Satellite Engine
- Integrate the 17–24 True Crime investigative archetypes (`#M1..#M8` Real Satellite Maps at Zoom 6–16 with animated motion HUD, `#D1..#D10` Forensic Dossiers & Biometric Labs, `#P1..#P6` 1990s Press, Police Curfew & CRT Broadcast) into `CofiDocumentary` (`documentary/edit.py`, `documentary/prompts.py`, `services/editing_dna_service.py`, and a dedicated True Crime rendering/compositing module).
- **Semantic Voice-Content Matching (No Fixed Default or Blind Round-Robin)**: The AI Agent / scene planner must analyze the actual **voice narration / SRT transcript meaning** of each beat and select the specific archetype that genuinely matches the spoken content (e.g., Y-chromosome / familial lineage narration → `#D4` Y-STR DNA Lightbox & Pedigree Tree; zooming into a school campus store / building rooftop → `#M1` or `#M6` Zoom ×16 Satellite Rooftop; regional administrative boundary / Yellow River escape route → `#M2` or `#M3` Regional Satellite Radar/Vector; 3D geographic pattern across crime coordinates → `#M5` 2.5D Tilted Satellite Slab; city-wide night curfew / lockdown → `#M7` Night-Ops Infrared Satellite or `#P2` Police Curfew Notice; interrogation confession / audio recording → `#D5` Aluminum Clipboard Q&A + Voiceprint Waveform; wanted reward / composite sketch → `#D6` Class-A Red Wanted Warrant; fingerprint ridge match → `#D1` or `#D9` Microscope 14-Point Comparator; 1990s TV news report → `#P3` CRT Broadcast Monitor; dramatic human emotion → full-frame AI/Footage cinema without forcing a document frame). Track recent selections only to avoid repeating the exact same visual shell on back-to-back beats when multiple semantic fits exist.
- Scope this True Crime Vox & Satellite pipeline to the True Crime channel profile (`channel-e544a64b7c` / `특급수배록` / `true_crime_noir_ai` / `forensic_noir`) so other channel profiles remain untouched.

### R2. Tab 07 (`SEO + Thumbnail`) Redesign — Maximized Top Thumbnail Canvas + Collapsible SEO Accordion
- Redesign **Tab 07: SEO + Thumbnail** (`#seoWorkspace` in `static/index.html`, `static/thumbnail_studio.js`, `static/styles.css`) following the UI skills (`agency-ui-designer` & `design-system`):
  - **Top Priority — Expanded Thumbnail Canvas Studio**: Maximize the interactive 16:9 Thumbnail Canvas area at the top so the user can clearly see and edit the thumbnail at large scale, with streamlined, easy-to-use controls for A/B/C/D candidate switching, Korean/Vietnamese bilingual text lines, broadcast font & color swatches, mascot/reference lock, and 1-click full-resolution download/save.
  - **Bottom — Collapsible SEO Packaging Accordion**: Place the SEO section (Title variants with CTR analysis & bilingual translation, Video Description & Timestamps, YouTube Tags, Mandatory Hashtags, and 1-click Copy buttons) inside clean, well-styled **Accordion drawers** (`<details>` / expandable cards) underneath the Thumbnail Canvas so it never crowds or pushes down the thumbnail workspace.

### R3. App-Wide UI/UX Polish & Ergonomics
- Upgrade the overall visual hierarchy, design tokens (spacing, typography, card borders, surface contrast, button states, badge pills), and form ergonomics across `static/index.html`, `static/styles.css`, and `static/app.js` so dense panels (Overview, Channel DNA, Create Video, Edit) feel clean, friendly, cohesive, and effortless to navigate.

### R4. Live Process Safety & Zero Disruption Constraint
- Do **NOT** kill, stop, or restart any currently running external user processes (`CofiDub` on port `8000`, `CofiDocumentary` desktop app `PID 28296` on port `8878`, `CofiRemotion` on port `8890`, or `CofiBlenderStudio` on port `8900`). All code changes and verification tests must run non-destructively alongside the live environment.

## Acceptance Criteria

### Semantic Voice-to-Archetype Routing & Satellite Rendering
- [ ] A programmatic verification test passes 10+ diverse Korean/Vietnamese True Crime voice narration sentences (covering DNA lineage, rooftop store raid, night curfew, fingerprint minutiae, confession transcript, wanted sketch, regional escape, 1990s TV news, multi-year silence, and emotional confrontation) into the CofiDocumentary scene router and verifies that each sentence maps semantically to the matching archetype (`#M1..#M8`, `#D1..#D10`, `#P1..#P6`, or `cinema_full`) rather than a static default or mechanical round-robin.
- [ ] Test-rendering sample scenes from CofiDocumentary produces valid `1920x1080` frames using real cached satellite imagery (`Z6`, `Z9`, `Z14`, `Z16`) and forensic layouts with zero missing Korean glyphs (`□`) or overlapping text boxes.

### Tab 07 (`SEO + Thumbnail`) & App UI Verification
- [ ] In Tab 07 (`#seoWorkspace`), the Thumbnail Canvas workbench is positioned at the top with a maximized viewport allocation, and the SEO packaging blocks (Titles, Description, Tags/Hashtags) are housed inside collapsible Accordion sections below the canvas with working 1-click Copy actions.
- [ ] All JavaScript files (`static/app.js`, `static/thumbnail_studio.js`, `static/desktop_chrome.js`) pass syntax validation (`node --check`) with zero errors, and Python backend modules (`documentary/edit.py`, `documentary/prompts.py`, `services/editing_dna_service.py`) pass `python -m py_compile` and unit tests with zero regressions.
- [ ] Running processes on ports `8000`, `8878`, `8890`, and `8900` remain alive and undisturbed throughout execution.
