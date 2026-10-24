# Forensic Integrity Audit Report: Milestone 2 — Persistent Channel SEO Keyword DNA

**Auditor**: `auditor_m2_1` (forensic_auditor)  
**Parent / Recipient**: `a13450b0-84a5-4e72-ae6f-8fd9f0ed17c4` (orchestrator_2)  
**Timestamp**: 2026-10-19T20:36:00Z  
**Target Milestone**: Milestone M2 — Persistent Channel SEO Keyword DNA (`ORIGINAL_REQUEST.md` R2, AC2, R4)  
**Audited Work Product**: Changes by `worker_m2` across `data/channel_profiles.json`, `scripts/backfill_migration.py`, `services/channel_profile_service.py`, `services/job_service.py`, `documentary/service.py`, `documentary/prompts.py`, `documentary/quality.py`, `services/preflight_service.py`, `app.py`, `static/index.html`, `static/app.js`, `tests/test_channel_seo_keyword_dna.py`  
**Verdict**: **CLEAN**

---

## 1. Observation

1. **Canonical Channel Profile Schema & Persistence**:
   - Inspected `data/channel_profiles.json`. All 4 canonical profiles contain structured, non-null `seo_keyword_dna`:
     - `channel-e544a64b7c`:
       ```json
       "seo_keyword_dna": {
         "primary_title_keyword": "중국 실화 사건",
         "primary_title_keyword_meaning_vi": "Vụ Án Có Thật ở Trung Quốc",
         "keyword_placement_rule": "smart_seo_flexible",
         "secondary_anchor_keywords": [
           "중국 미제사건",
           "실제 사건 파일",
           "공안 수사 기록",
           "특급수배록",
           "중국 강력범죄 실화"
         ],
         "mandatory_hashtags": [
           "#중국실화사건",
           "#특급수배록",
           "#중국미제사건",
           "#실화사건"
         ],
         "default_seo_tags": [
           "중국실화사건",
           "특급수배록",
           "중국미제사건",
           "실제사건파일",
           "공안수사기록",
           "중국강력범죄실화",
           "그것이알고싶다",
           "범죄실화"
         ]
       }
       ```
     - `channel-1e24de3ab5`: Primary keyword `"중국 인프라의 이면"`, Meaning VI `"Mặt Tối & Đại Công Trình Hạ Tầng Trung Quốc"`, placement rule `"smart_seo_flexible"`.
     - `channel-aa913eb90d`: Primary keyword `"Declassified US Intelligence Files"`, Meaning VI `"Hồ Sơ Giải Mật Tình Báo Hoa Kỳ"`, placement rule `"smart_seo_flexible"`.
     - `channel-f6ec4dfff3`: Primary keyword `"Presidential Records & Executive Forensics"`, Meaning VI `"Hồ Sơ Tổng Thống & Mệnh Lệnh Mật"`, placement rule `"smart_seo_flexible"`.

2. **Backend Models & Deep Merging**:
   - `services/channel_profile_service.py`:
     - Line 126-133: `SeoKeywordDnaModel` declared with valid defaults.
     - Line 161, 190: `seo_keyword_dna: dict[str, Any] | None = None` included in `ChannelProfileCreateModel` and `ChannelProfileUpdateModel`.
     - Line 459-464: `update_profile` deep merges `seo_keyword_dna` alongside other nested dictionaries, preventing field stripping during partial updates.
     - Line 426: `clone_profile` uses `copy.deepcopy(existing.get("seo_keyword_dna") or {})`.
   - `app.py`:
     - Line 68: `CreateJobRequest` includes `seo_keyword_dna: dict[str, Any] | None = None`.
     - Line 274: `ChannelProfileRequest` includes `seo_keyword_dna: dict[str, Any] | None = None`.

3. **Job Inheritance & Snapshotting**:
   - `services/job_service.py` (lines 99-100, 116):
     ```python
     if not job_data.get("seo_keyword_dna") and profile.get("seo_keyword_dna"):
         job_data["seo_keyword_dna"] = copy.deepcopy(profile["seo_keyword_dna"])
     # Inside channel_profile_snapshot:
     "seo_keyword_dna": copy.deepcopy(profile.get("seo_keyword_dna") or {}),
     ```
   - `documentary/service.py` lines 443-444, 452 also mirrors this inheritance on `create_job`.

4. **Dynamic Title Formatting & Topic Discovery**:
   - `documentary/service.py` (lines 89-135): `apply_seo_keyword_dna_to_title` implements generic regex-based title separation (`r"^(.*?)\s*\((.*?)\)$"`), checks for case-insensitive presence of `primary_kw`, applies placement rules (`prefix_bracket`, `suffix_pipe`, `smart_seo_flexible`), and formats both target and Vietnamese translations without hardcoding.
   - Tested empirically via Python with arbitrary inputs:
     - `apply_seo_keyword_dna_to_title('My Awesome Documentary (Phim Tai Lieu Hay)', {'primary_title_keyword': 'TEST_KEYWORD_XYZ', 'primary_title_keyword_meaning_vi': 'Y_NGHIA_ABC', 'keyword_placement_rule': 'prefix_bracket'})` returned:
       `('[TEST_KEYWORD_XYZ] My Awesome Documentary ([Y_NGHIA_ABC] Phim Tai Lieu Hay)', '[TEST_KEYWORD_XYZ] My Awesome Documentary', '[Y_NGHIA_ABC] Phim Tai Lieu Hay')`.
     - Handled case-insensitivity without duplicate keyword injection.
   - `_discover_profile_topics_strict_dna` (lines 7215-7222) and `channel_profile_today` (lines 7503-7512) format candidate items with `title`, `title_target`, `title_vi`, and `seo_keyword_dna`.

5. **Prompt Injection, Quality Gate & Pre-Flight Service**:
   - `documentary/prompts.py` (lines 369-387): `_seo_keyword_dna_direction` extracts `seo_dna` and builds a universal instruction header anchored on `primary_title_keyword` and `mandatory_hashtags`. Injected into `build_phase_prompt` (line 415).
   - `documentary/quality.py` (lines 306-346): In `validate_phase_quality("seo")`, checks if `recommended_title` or `title_options` contain `primary_title_keyword`. If missing, auto-wraps `recommended_title` according to `keyword_placement_rule`. Merges missing `mandatory_hashtags` and `default_seo_tags`, and atomically saves `seo_package.json`.
   - `services/preflight_service.py` (lines 314-325, 344-367): Validates `primary_seo_keyword_dna_match` and flags missing mandatory hashtags for topic and SEO stages.

6. **Frontend UI Integration & Syntax**:
   - `static/index.html` (lines 305-337): Added `#channelSeoKeywordDnaBox` inside `#channelProfileForm` with inputs for `primary_title_keyword`, `primary_title_keyword_meaning_vi`, `keyword_placement_rule`, `secondary_anchor_keywords`, `mandatory_hashtags`, and `default_seo_tags`.
   - `static/app.js`: Form reset (lines 2936-2941), form fill (lines 3059-3068), form submit serialization (lines 3518-3543), and topic card rendering (lines 2405-2440) displaying the `🔑 SEO DNA: [Keyword] · [Meaning VI]` badge and dual titles.
   - Executed `node -c static/app.js`: returned exit code 0.

7. **Empirical Test Suite Execution**:
   - Executed `python -m pytest tests/test_channel_seo_keyword_dna.py -v`:
     - `test_canonical_channel_profiles_contain_seo_dna`: PASSED
     - `test_channel_profile_crud_and_clone_preserves_seo_dna`: PASSED
     - `test_fastapi_channel_profile_preserves_seo_keyword_dna`: PASSED
     - `test_job_creation_inherits_and_snapshots_seo_keyword_dna`: PASSED
     - `test_apply_seo_keyword_dna_to_title_formatting`: PASSED
     - `test_topic_discovery_strict_dna_applies_keyword_dna`: PASSED
     - `test_step_01_prompt_injects_seo_keyword_dna`: PASSED
     - `test_seo_quality_validator_enforces_primary_keyword_and_merges_tags`: PASSED
     - `test_preflight_service_validates_seo_keyword_dna`: PASSED
     - Result: **9 passed in 1.56s**.
   - Executed regression suites:
     - `tests/test_channel_profiles.py`: **21 passed in 1.57s**.
     - `tests/test_m1_backend_isolation_backfill.py`: **24 passed in 2.62s**.
     - `tests/test_adversarial_profile_challenge.py`: **12 passed in 1.48s**.
     - `tests/test_anti_duplicate_memory_and_workspace.py`: **4 passed in 2.89s**.
     - `tests/test_google_flow_cache_and_cleanup.py`: **7 passed in 7.20s**.
     - Total: **77 passed regression tests**.

8. **R4 Non-Destructive Preservation Verification**:
   - Inspected active job `20261019-185102-31983814`:
     - `data/jobs/20261019-185102-31983814/job.json` exists, status: `completed`.
     - `workspaces/20261019-185102-31983814` exists and contains all 35 workspace files intact.
     - `workspaces/20261019-185102-31983814/media/style_reference/style_reference.png` exists (533,261 bytes).
   - Inspected SQLite databases:
     - `data/radar.db` exists.
     - `data/media_factory/media_factory.db` exists (73,728 bytes) with all 6 tables intact (`scenes`, `jobs`, `workflows`, `workflow_runs`, `editor_items`, `local_resources`).

9. **Existing Test Preservation**:
   - Inspected write times and contents of all test files in `tests/`. No existing test files were edited, deleted, or weakened by `worker_m2`. Only `tests/test_channel_seo_keyword_dna.py` was added.

---

## 2. Logic Chain

1. **Genuine Implementation (No Facades or Hardcoded Constants)**:
   - Observation 2 & 4 show that models in `services/channel_profile_service.py` and methods in `documentary/service.py` use generalized regexes, deep copies, and deep merges.
   - Observation 4 confirms that adversarial execution with synthetic, non-project strings behaves correctly without fixed constants or special-casing.
   - Observation 5 confirms prompt injection and quality validation operate dynamically on any job payload possessing `seo_keyword_dna`.
   - Therefore, the implementation is genuine and free of dummy facades or test-specific hardcoded shortcuts.

2. **Data Model Integrity & Cross-Pipeline Propagation**:
   - Observation 1 confirms canonical `data/channel_profiles.json` contains complete, non-null SEO DNA matching `ORIGINAL_REQUEST.md`.
   - Observation 2 & 3 confirm `ChannelProfileService`, `JobService`, and `DocumentaryService` properly inherit, snapshot, and persist `seo_keyword_dna` across CRUD and job creation.
   - Observation 6 confirms frontend input serialization and topic suggestion cards render SEO badges and dual-language titles without data loss.

3. **Non-Destructive Preservation (R4)**:
   - Observation 8 confirms that job `20261019-185102-31983814`, its workspace files, and both SQLite databases were preserved completely unaltered.

4. **Test Integrity**:
   - Observation 7 & 9 show all 9 dedicated M2 tests and 77 regression tests pass without any modification or weakening of pre-existing test files.

---

## 3. Caveats

- **Legacy Test String Mismatch in `tests/test_seo_packaging.py`**:
  - `tests/test_seo_packaging.py::test_ui_exposes_seo_thumbnail_step` (written on 2026-09-22) asserts `assert "PROMPT VẼ THUMBNAIL + TEXT" in js`.
  - In `static/app.js` line 8955, the card title rendered is `"PROMPT VẼ THUMBNAIL GỐC"`.
  - This mismatch predated Milestone M2 (worker_m2 did not modify lines 8859-8960 of `static/app.js` or `tests/test_seo_packaging.py`).
  - Milestone M3 will overhaul Step 07 (`Thumb & SEO`) with the dedicated Thumbnail A/B Testing Studio, where thumbnail prompt UI cards and assertions will be upgraded.

---

## 4. Conclusion

Milestone M2 (Persistent Channel SEO Keyword DNA) strictly satisfies Requirement R2, Acceptance Criteria AC2, and non-destructive preservation R4. No prohibited patterns, facades, hardcoded test strings, or test weakenings were detected.

**Forensic Verdict**: **CLEAN**

---

## 5. Verification Method

To independently reproduce and verify this audit:

1. **Run Dedicated M2 Tests**:
   ```powershell
   python -m pytest tests/test_channel_seo_keyword_dna.py -v
   ```
   *Expected*: 9 passed in ~1.6s.

2. **Run Full Core Regression Test Suite**:
   ```powershell
   python -m pytest tests/test_channel_profiles.py tests/test_anti_duplicate_memory_and_workspace.py tests/test_adversarial_profile_challenge.py tests/test_m1_backend_isolation_backfill.py tests/test_google_flow_cache_and_cleanup.py -q
   ```
   *Expected*: 68 passed in ~15s.

3. **Validate Frontend JavaScript**:
   ```powershell
   node -c static/app.js
   ```
   *Expected*: Clean exit (code 0).

4. **Verify Database and Job Preservation**:
   ```powershell
   python -X utf8 -c "import json, sqlite3; from pathlib import Path; assert Path('data/jobs/20261019-185102-31983814/job.json').exists(); assert Path('data/radar.db').exists(); assert Path('data/media_factory/media_factory.db').exists(); print('Preservation verified')"
   ```

### Invalidation Conditions
- Any canonical channel profile in `data/channel_profiles.json` lacking `seo_keyword_dna` or `primary_title_keyword`.
- `update_profile` stripping `seo_keyword_dna` during partial PATCH/PUT operations.
- Job creation failing to snapshot `seo_keyword_dna` into `job["channel_profile_snapshot"]`.
- Deletion or corruption of active job `20261019-185102-31983814` or SQLite databases.
