## 2026-10-19T12:08:14Z

You are the SWE Light orchestrator for CofiDocumentary located at B:\ALL_TOOLS\CofiDocumentary.
Your working directory is B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\swe_1.
Your task is defined in the latest follow-up request in B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\ORIGINAL_REQUEST.md.

Specifically:
This is a single self-contained fix; keep it small and focused. Upgrade CofiDocumentary (B:\ALL_TOOLS\CofiDocumentary) with:
(1) A 2-Layer Anti-Duplicate Topic Memory & Pre-Flight System (checking both YouTube Channel History and a persistent, user-manageable Profile Produced-Topic Memory Ledger with bilingual case/entity similarity matching across Korean, Vietnamese, and English).
- Equip each Channel Profile with a persistent Produced Topic Memory Ledger (topic_memory).
- Automatically backfill topic_memory from existing jobs in data/jobs/*/job.json and workspaces/*/input.json (including 20261017-164519-fd65f7e1, 20261019-185102-31983814 on channel-e544a64b7c, and 20261018-223750-3aecfbcd on channel-1e24de3ab5).
- Auto-append structured entries on job create or topic/title update.
- Expose REST endpoints (GET, POST, DELETE /api/radar/channel-profiles/{profile_id}/topic-memory) and an interactive UI panel in Step 0 / Step 00.
- Upgrade Topic Discovery and Channel-DNA Pre-Flight Check to execute two distinct anti-duplicate passes: Pass 1 (YouTube Channel History) + Pass 2 (Profile Topic Memory), with bilingual case/entity similarity matching.
- Strict filtering in Topic Discovery (exclude produced topics from channel_profile_today / discover-topics, replacing them with unproduced DNA-compliant topics) and explicit 2-Layer Pre-Flight UI in #createPreflightSummaryBox.

(2) True Reference Image Fidelity & Job Workspace Persistence:
- When a reference image is provided in Step 00 or Step 05, remove hardcoded "white rounded full-body stickman/mascot character with black outlines" / "white marshmallow mascot" text from documentary/ai_visual.py (_prompt) and documentary/visuals.py (_prompt_for), replacing it with color-faithful instructions preserving exact character colors, clothing/body colors, proportions, linework, and visual style.
- Prevent silently forcing style_mode = "preset" and style_preset = "Người que (Stickman)" when style_mode is "auto" or "custom" or when a reference image is uploaded.
- Add live Reference Image preview thumbnail, filename/hash badge, and "Xóa / Đổi ảnh tham chiếu" button in Step 00 and Step 05.
- Fix POST /api/jobs workspace creation so workspaces/{job_id} is created with resolved non-empty paths and no leaked files in repo root.
- Repair existing job 20261019-185102-31983814: move root-leaked artifacts into workspaces/20261019-185102-31983814/, update job.json with valid workspace path and custom style mode, and link yellow/color reference image.

Verify all acceptance criteria AC1 and AC2 with automated tests.
Maintain your progress in B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\swe_1\progress.md.
When you finish and all tests pass, report your completion and results back to sentinel.
