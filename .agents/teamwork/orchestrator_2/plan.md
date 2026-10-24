# Plan: CofiDocumentary & Media Factory Upgrades (Follow-up 2026-10-19T19:03:29Z)

## Architecture Overview
- **CofiDocumentary Root**: `B:\ALL_TOOLS\CofiDocumentary`
  - FastAPI server (`app.py`), service layer (`documentary/service.py`, `documentary/radar.py`, `documentary/models.py`), frontend (`static/index.html`, `static/app.js`, `static/css/`)
  - Channel profiles stored in `data/channel_profiles.json` and `data/radar.db`
  - Active jobs in `data/jobs/`, workspaces in `workspaces/` (must be strictly preserved)
- **Media Factory Root**: `B:\ALL_TOOLS\CofiDocumentary\vendor\media_factory`
  - FastAPI backend (`backend/app/providers/google.py`, `backend/app/routes/accounts.py`)
  - Account profiles in `data/media_factory/google-flow-profiles/`
  - Session files in `data/media_factory/secrets/google-flow/`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Account Deletion Complete Disk Removal | Clean session file, browser process termination, and complete deletion of `google-flow-profiles/{account_id}` on account removal or pruning | M1 | R1, AC1 |
| 2 | Smart Chromium Profile Cache Eviction | Clean heavy cache folders (`Default/Cache`, `GPUCache`, etc.) preserving cookies/local storage; delete orphan profile directories; expose disk usage stats | M1 | R1, AC1 |
| 3 | Media Factory Proxy & UI Button in CofiDocumentary | Connect CofiDocumentary server to Media Factory clean cache endpoint and add "Dọn Cache Thông Minh" UI button | M1 | R1, AC1 |
| 4 | Persistent Channel SEO Keyword DNA Schema | Add `primary_title_keyword`, `primary_title_keyword_meaning_vi`, `keyword_placement_rule`, `secondary_anchor_keywords`, `mandatory_hashtags` to Channel Profiles & Jobs | M2 | R2, AC2 |
| 5 | Cross-Pipeline SEO Enforcement | Title suggestions, topic discovery, script hooks, and Step 07 SEO generation enforce channel SEO Keyword DNA (e.g. `channel-e544a64b7c` with "Vụ Án Có Thật ở Trung Quốc") | M2 | R2, AC2 |
| 6 | Persistent Channel Thumbnail Design DNA | Store and lock `style_preset`, `visual_signature`, `color_palette`, `typography_preset`, `layout_template`, `mascot_lock` on Channel Profile | M3 | R3, AC3 |
| 7 | Step 07 Thumbnail A/B Testing Studio | 3 distinct A/B/C test variants (Curiosity hook, Evidence close-up, Confrontation/dual-contrast), CTR prediction scores, YouTube feed preview, export test pack, lock winner to channel | M3 | R3, AC3 |
| 8 | Non-Destructive Active Job & DB Preservation | Preserve job `20261019-185102-31983814`, all existing workspaces, and DBs | M4 | R4, AC1-3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Survey & Architecture Mapping | Map affected files, existing implementations, and test harnesses | None | IN_PROGRESS |
| M1 | Google Flow Profile Cache & Account Deletion Disk Removal | R1, AC1 in Media Factory and CofiDocumentary proxy/UI | M0 | PLANNED |
| M2 | Persistent Channel SEO Keyword DNA Across Profiles & Projects | R2, AC2 in backend models, profile storage, topic/title/SEO pipelines, and UI | M0 | PLANNED |
| M3 | Channel Thumbnail Design DNA & Multi-Variant A/B Testing Studio | R3, AC3 in Step 0 & Step 07, thumbnail generation, CTR scoring, and UI | M2 | PLANNED |
| M4 | Comprehensive Verification, Preservation & Final Audit | Automated test suite execution, integrity audit, regression checks, active job preservation verification | M1, M2, M3 | PLANNED |
