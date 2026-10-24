# Project: CofiDocumentary & Media Factory Upgrades

## Architecture
- **Media Factory (`vendor/media_factory/`)**:
  - `backend/app/providers/google.py`: `GoogleFlowAccountManager`, `BrowserLoginWorker`
  - `backend/app/routes/providers.py` & `backend/app/routes/accounts.py`: REST routes for Google Flow accounts
- **CofiDocumentary Core (`B:\ALL_TOOLS\CofiDocumentary/`)**:
  - `documentary/cofi_studio_embed.py`: Proxy manager between CofiDocumentary and Media Factory
  - `documentary/service.py`: Central documentary orchestration service
  - `services/channel_profile_service.py` & `services/job_service.py`: Channel profile and job models / services
  - `documentary/thumbnail_studio.py`: Thumbnail generation, layout archetypes, CTR scoring
  - `documentary/quality.py` & `services/preflight_service.py`: Quality validation & pre-flight checks
  - `app.py` & `server.py`: FastAPI routes
  - `static/index.html`, `static/app.js`, `static/thumbnail_studio.js`: UI studio

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Account Deletion Complete Disk Removal | Process termination (`_terminate_profile_processes`), secret session file deletion, and profile folder disk removal on account delete/prune | M1 | R1, AC1 |
| 2 | Smart Chromium Profile Cache Eviction | Evict heavy Chromium caches (`Default/Cache`, `GPUCache`, etc.) while preserving auth cookies & session storage; auto-evict on session close; expose disk stats | M1 | R1, AC1 |
| 3 | Orphan Profile and Session Detection | Detect and purge orphan profile folders and orphan `.enc` session files that have no DB account | M1 | R1, AC1 |
| 4 | Clean Cache API Endpoints & Cofi Studio UI | `POST /api/providers/google/accounts/clean-cache` in Media Factory, proxy in CofiDocumentary, and "⚡ Dọn Cache Thông Minh" button in UI | M1 | R1, AC1 |
| 5 | Persistent Channel SEO Keyword DNA Schema | Add structured `seo_keyword_dna` to Channel Profiles (`primary_title_keyword`, `meaning_vi`, `placement_rule`, `secondary_anchors`, `hashtags`, `tags`) | M2 | R2, AC2 |
| 6 | Backfill Canonical Profiles with SEO DNA | Configure all 4 profiles (`channel-e544a64b7c` with "중국 실화 사건" / "Vụ Án Có Thật ở Trung Quốc", `channel-1e24de3ab5`, `channel-aa913eb90d`, `channel-f6ec4dfff3`) | M2 | R2, AC2 |
| 7 | Job Inheritance of SEO Keyword DNA | Snapshot `seo_keyword_dna` into `job["seo_keyword_dna"]` and `channel_profile_snapshot` on job creation | M2 | R2, AC2 |
| 8 | Step 00 Topic Discovery SEO Alignment | Inject `primary_title_keyword` into topic/title generation; display dual target/VI title and SEO DNA badge | M2 | R2, AC2 |
| 9 | Step 01 Script Hook & Step 07 Packaging SEO Enforcement | Enforce primary keyword in thesis/hook and `validate_phase_quality("seo")`; merge mandatory hashtags & default tags | M2 | R2, AC2 |
| 10 | Persistent Channel Thumbnail Design DNA Schema | Store `thumbnail_dna` (palette, typography, layout archetype, mascot lock) on Channel Profile; backfill canonical profiles | M3 | R3, AC3 |
| 11 | Job Inheritance & Lock Thumbnail DNA | Inherit `thumbnail_dna` in job creation; add `POST /api/jobs/{job_id}/lock-thumbnail-dna` to lock project thumbnail style to parent profile | M3 | R3, AC3 |
| 12 | Step 07 Thumbnail A/B Testing Studio | 3 distinct A/B/C variants (Curiosity, Evidence, Confrontation); CTR prediction scorecards; YouTube Home/Sidebar feed preview; export A/B/C Test Pack for YouTube Studio | M3 | R3, AC3 |
| 13 | Step 0 & Step 07 UI Integration for Thumbnail DNA | Step 0 Thumbnail DNA editor card; Step 07 A/B Studio cards, winner selection, lock button | M3 | R3, AC3 |
| 14 | Active Job & DB Non-Destructive Preservation | Preserve job `20261019-185102-31983814`, all existing workspaces, and DBs; run full automated test suite | M4 | R4, AC1-3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Survey & Architecture Mapping | Survey codebases and synthesize findings | None | DONE |
| M1 | Google Flow Profile Cache & Account Deletion Disk Removal | R1, AC1: complete disk removal, smart cache eviction, orphan purge, API & UI button | M0 | **DONE** |
| M2 | Persistent Channel SEO Keyword DNA Across Profiles & Projects | R2, AC2: schema, backfill, job snapshot, Step 00 topic discovery, Step 01 & 07 enforcement, UI | M0 | **DONE** |
| M3 | Channel Thumbnail Design DNA & Multi-Variant A/B Testing Studio | R3, AC3: thumbnail DNA schema, lock endpoint, Step 07 3-variant studio, CTR scorecards, preview, UI | M2 | **DONE** |
| M4 | Comprehensive Verification, Preservation & Final Audit | R4: Full automated test suite verification, active job preservation check, forensic audit | M1, M2, M3 | **DONE** |
