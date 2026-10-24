## 2026-10-18T19:53:44Z
From: 5aa18375-8f2e-479e-b627-f1d6f5283a45
Priority: MESSAGE_PRIORITY_HIGH

You are test_writer_e2e.
Your working directory is: B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\test_writer_e2e\
Your parent orchestrator conversation ID: 5aa18375-8f2e-479e-b627-f1d6f5283a45

Read these scope documents immediately before starting:
- B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\ORIGINAL_REQUEST.md
- B:\ALL_TOOLS\CofiDocumentary\PROJECT.md
- B:\ALL_TOOLS\CofiDocumentary\TEST_INFRA.md

Exclusively Owned Files:
- `tests/e2e/runner.py`
- `tests/e2e/test_ac1_ui_ux.py`
- `tests/e2e/test_ac2_isolation_backfill.py`
- `tests/e2e/test_ac3_edit_memory_sync_policy.py`
- `tests/e2e/test_ac4_preflight_self_learning.py`
- `tests/e2e/test_tier3_pairwise.py`
- `tests/e2e/test_tier4_workload.py`
- `TEST_READY.md`

Tasks:
1. Build the complete, independent opaque-box E2E test suite under `tests/e2e/`:
   - `test_ac1_ui_ux.py`:
     - Test DOM/layout structure of `.app-shell.channel-studio-shell`, `#globalProjectSelect`, `#globalCodexDock` across 1280px to 1920px viewports (collapsed vs expanded chat).
     - Test all workflow tabs (Step 0 to Step 08: `radar`, `create`, `script`, `voice`, `visuals`, `footage`, `ai_visual`, `edit`, `seo`, `qc`) for working manual controls and AI agent API accessibility.
   - `test_ac2_isolation_backfill.py`:
     - Test Channel Profile switching in Step 0 and Step 00: 100% field population with zero field bleed from previous profiles (`market`, `language`, `target_duration_minutes`, `visual_strategy`, `ai_media_mode`, `narrative_angle`, `writing_style`, `hook_archetype`, `editing_archetypes`, `opening_hook`, `notes`, `editing_dna`).
     - Test modifying Step 00 `Create Project` draft inputs makes zero PATCH/POST mutations to currently active project (`state.selectedId`).
     - Test Step 0 explicit separation of "Create New Profile", "Clone Profile", and "Update Current Profile".
     - Test storage verification: verify existing profiles (`channel-1e24de3ab5`, `channel-e544a64b7c`, `channel-aa913eb90d`, `channel-f6ec4dfff3`) and jobs (`20261018-223750-3aecfbcd`, `20261017-164519-fd65f7e1`) have complete non-null fields in storage.
   - `test_ac3_edit_memory_sync_policy.py`:
     - Test "Lock Approved Edit Style to Channel" (`POST /api/jobs/{job_id}/lock-edit-dna`): extracts Remotion/editing recipe into profile's `editing_dna` with versioning, and subsequent projects created on that profile automatically inherit that exact recipe.
     - Test Voice-Visual Sync & YouTube Policy compliance scorecard (`GET /api/jobs/{job_id}/sync-compliance`): validates beat-to-SRT timestamp alignment, detects holds >8s, flags graphic content, verifies editorial overlay ratio >=85%.
   - `test_ac4_preflight_self_learning.py`:
     - Test Self-Learning Win/Loss Post-Mortem Report (`GET/POST /api/radar/channel-profiles/{id}/self-learning`): classifies winners vs underperformers, diagnoses failure causes, stores upgrade rules.
     - Test Pre-Flight DNA Check summary alongside Topic/Title Discovery, SEO Generation, and Thumbnail Generation (3+ variants with zoom preview and single/batch download).
   - `test_tier3_pairwise.py`: Pairwise interactions across profile switching, editing lock, pre-flight, and export.
   - `test_tier4_workload.py`: End-to-end full documentary production simulation from Step 0 to Step 08.
   - `runner.py`: Standalone CLI runner with structured summary report output.
2. Ensure minimum test count threshold (>= 82 test cases across Tiers 1-4).
3. Once the test files and runner are created, verify syntax and execution, and author `TEST_READY.md` at project root `B:\ALL_TOOLS\CofiDocumentary\TEST_READY.md` following the template in `PROJECT.md` / `TEST_INFRA.md`.
4. Document all files created and runner command in `handoff.md` and send completion message to parent orchestrator.
