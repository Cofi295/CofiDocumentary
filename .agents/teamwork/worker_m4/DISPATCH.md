## 2026-10-18T21:22:49Z
You are worker_m4.
Your working directory is: B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\worker_m4\
Your parent orchestrator conversation ID: 5aa18375-8f2e-479e-b627-f1d6f5283a45

Read these scope documents immediately before starting:
- B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\ORIGINAL_REQUEST.md
- B:\ALL_TOOLS\CofiDocumentary\PROJECT.md
- Survey report findings in B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\teamwork_preview_explorer_survey_3\survey_report.md
- E2E Test Suite for AC4: B:\ALL_TOOLS\CofiDocumentary\tests\e2e\test_ac4_preflight_self_learning.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope: Milestone 4 - Channel-DNA Pre-Flight & Continuous Self-Learning Engine (Features F6, F7; Requirements R4, R5; Acceptance Criteria AC4)
Exclusively Owned Files:
- `services/preflight_service.py`
- `services/self_learning_service.py`
- `server.py`
- `static/app.js` (Step 00 Topic/Title Pre-Flight UI, Step 07 Thumbnail zoom lightbox & single/batch download, Step 0 Self-Learning Post-Mortem UI)
- `templates/index.html` and `static/index.html`

Specific Tasks:
1. Implement `services/preflight_service.py`:
   - Channel DNA Pre-Flight Engine: queries real YouTube data in `profile.own_channel.dna` (`winner_terms`, `weak_terms`, `winner_titles` with VPH/outlier multipliers) and internal job catalog.
   - Topic/Title Pre-Flight: checks winner vs losing topics/angles, blocks duplicate topics already published on the channel, generates winner titles.
   - Thumbnail Pre-Flight: analyzes channel visual DNA (composition, contrast, text placement), guides generation of 3+ testable variants.
   - SEO Pre-Flight: cross-checks keyword winners, tags, description structures, and chapter timestamps against top-performing videos.
   - Returns explicit `preflight_summary` object alongside generated outputs.
2. Implement `services/self_learning_service.py`:
   - Automated Channel Self-Learning & Post-Mortem Engine:
     - Scans channel YouTube catalog and project history.
     - Classifies **Winners (Outliers)** vs **Underperformers (Losing videos)** based on view thresholds, VPH, and outlier ratios.
     - Performs diagnostic post-mortem on underperformers across failure dimensions (*Why did it lose?* e.g., weak title keywords, low-curiosity thumbnail, topic outside core DNA, hook drop-off).
     - Synthesizes actionable **Evolution & Upgrade Rules**:
       - `what_to_stop_doing`
       - `what_to_double_down_on`
       - `next_video_upgrades`
       - `thumbnail_dna`
       - `seo_dna`
       - `title_winner_patterns`
     - Persists them into `profile.self_learning_memory` in `data/channel_profiles.json`.
     - Injects them automatically into subsequent project generation phases (Topic Discovery, Title/Thumbnail Design, Script Hook, Edit).
3. Wire REST API endpoints in `server.py`:
   - `GET /api/radar/channel-profiles/{profile_id}/preflight-check`
   - `GET /api/radar/channel-profiles/{profile_id}/self-learning`
   - `POST /api/radar/channel-profiles/{profile_id}/self-learning/run`
   - Integrate preflight check into Topic/Title, Thumbnail (ensuring 3+ variants), and SEO generation endpoints so each includes an explicit `preflight_summary`.
4. Wire Frontend UI:
   - In Step 00 (`create` tab): Render Channel DNA Pre-Flight Check summary for topics and titles.
   - In Step 07 (`seo` / thumbnail tab): Ensure 3+ thumbnail variants render with zoom lightbox preview, single-card download, and batch download.
   - In Step 0 (`radar` / channel profile tab): Display Self-Learning Win/Loss Post-Mortem Report with concrete upgrade rules.
   - Mirror all markup in `templates/index.html` and `static/index.html`.
5. Verification:
   - Run `python -m pytest tests/e2e/test_ac4_preflight_self_learning.py -v`.
   - Run `python tests/e2e/runner.py`.
   - Ensure 100% pass rate.
   - Document all changes and test outputs in `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\worker_m4\handoff.md`.
   - Send completion message to parent when done.
