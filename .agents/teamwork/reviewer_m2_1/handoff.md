# Review & Adversarial Challenge Report: Milestone M2 — Persistent Channel SEO Keyword DNA

**Reviewer**: `reviewer_m2_1` (reviewer, critic)  
**Parent / Caller**: `orchestrator_2` (`a13450b0-84a5-4e72-ae6f-8fd9f0ed17c4`)  
**Target Project**: CofiDocumentary (`B:\ALL_TOOLS\CofiDocumentary`)  
**Timestamp**: 2026-10-19T20:34:00Z  
**Verdict**: **APPROVE**  

---

## 1. Observation

1. **Persistent Canonical Profiles (`data/channel_profiles.json`)**:
   - Inspected all 4 canonical channel profiles via direct execution:
     `python -X utf8 -c "import json; data=json.load(open('data/channel_profiles.json', encoding='utf-8')); [print(p['id'], p['label'], '-->', json.dumps(p.get('seo_keyword_dna'), ensure_ascii=False)) for p in data['profiles']]"`
   - Output confirmed:
     - `channel-1e24de3ab5` (`판세의 이면`): `primary_title_keyword`: `"중국 인프라의 이면"`, `primary_title_keyword_meaning_vi`: `"Mặt Tối & Đại Công Trình Hạ Tầng Trung Quốc"`.
     - `channel-aa913eb90d` (`bí mật US`): `primary_title_keyword`: `"Declassified US Intelligence Files"`, `primary_title_keyword_meaning_vi`: `"Hồ Sơ Giải Mật Tình Báo Hoa Kỳ"`.
     - `channel-e544a64b7c` (`🇰🇷 Hồ sơ Kênh True Crime Hình Sự Trung Quốc`): `primary_title_keyword`: `"중국 실화 사건"`, `primary_title_keyword_meaning_vi`: `"Vụ Án Có Thật ở Trung Quốc"`, `keyword_placement_rule`: `"smart_seo_flexible"`, `secondary_anchor_keywords`: `["중국 미제사건", "실제 사건 파일", "공안 수사 기록", "특급수배록", "중국 강력범죄 실화"]`, `mandatory_hashtags`: `["#중국실화사건", "#특급수배록", "#중국미제사건", "#실화사건"]`, `default_seo_tags`: `["중국실화사건", "특급수배록", "중국미제사건", "실제사건파일", "공안수사기록", "중국강력범죄실화", "그것이알고싶다", "범죄실화"]`.
     - `channel-f6ec4dfff3` (`The First Family Vault`): `primary_title_keyword`: `"Presidential Records & Executive Forensics"`, `primary_title_keyword_meaning_vi`: `"Hồ Sơ Tổng Thống & Mệnh Lệnh Mật"`.

2. **Schema & Model Preservation (`services/channel_profile_service.py` & `app.py`)**:
   - `services/channel_profile_service.py`:
     - Lines 126-133: `SeoKeywordDnaModel` declares all 6 required fields.
     - Lines 161 & 190: `seo_keyword_dna: dict[str, Any] | None = None` included in `ChannelProfileCreateModel` and `ChannelProfileUpdateModel`.
     - Line 459: `if key in {"default_creative_brief", "editing_dna", "self_learning_memory", "seo_keyword_dna"}:` correctly performs deep dictionary merging on updates.
     - Line 426: `cloned["seo_keyword_dna"] = copy.deepcopy(existing.get("seo_keyword_dna") or {})` guarantees clone isolation.
   - `app.py`:
     - Line 68: `seo_keyword_dna: dict[str, Any] | None = None` on `CreateJobRequest`.
     - Line 274: `seo_keyword_dna: dict[str, Any] | None = None` on `ChannelProfileRequest`.

3. **Job Creation & Snapshotting (`services/job_service.py` & `documentary/service.py`)**:
   - `services/job_service.py`:
     - Lines 99-101: `if profile.get("seo_keyword_dna"): job_data["seo_keyword_dna"] = copy.deepcopy(profile["seo_keyword_dna"])`.
     - Lines 116-117: `job_data["channel_profile_snapshot"]["seo_keyword_dna"] = copy.deepcopy(profile.get("seo_keyword_dna") or {})`.
     - Workspace initialization: Lines 123-131 properly establish `workspaces/{job_id}/media/style_reference`.
   - `documentary/service.py`:
     - Lines 443-452: Preserves and snapshots `seo_keyword_dna` on `create_job`.
     - Lines 6053-6084: Preserves `seo_keyword_dna` in `save_channel_profile`.

4. **Step 00 Topic Discovery & Dual-Title Formatting (`documentary/service.py`)**:
   - Lines 89-135: `apply_seo_keyword_dna_to_title(title, seo_dna, rule)` formats target-language titles, preserves Vietnamese translation, prevents duplicate keyword injection, and supports `prefix_bracket`, `suffix_pipe`, and `smart_seo_flexible`.
   - Lines 7215-7222 and 7503-7512: Both `_discover_profile_topics_strict_dna` and `channel_profile_today` enrich every candidate with `title`, `title_target`, `title_vi`, and `seo_keyword_dna`.

5. **Prompt Injection & Packaging Validation (`documentary/prompts.py`, `documentary/quality.py`, `services/preflight_service.py`)**:
   - `documentary/prompts.py`: Lines 369-387 define `_seo_keyword_dna_direction(job)` and inject it into the universal header on line 415.
   - `documentary/quality.py`: Lines 306-346 in `validate_phase_quality("seo")` verify `primary_title_keyword` in titles, wrap `recommended_title` if missing, merge missing `mandatory_hashtags` and `default_seo_tags`, and write back atomically.
   - `services/preflight_service.py`: Lines 315-324 and 350-367 validate topic primary keyword matches and check for missing mandatory hashtags.

6. **Frontend UI Components (`static/index.html` & `static/app.js`)**:
   - `static/index.html`: Lines 305-337 render `#channelSeoKeywordDnaBox` inside `#channelProfileForm` with inputs for all SEO DNA fields.
   - `static/app.js`:
     - Lines 2936-2941: `resetChannelProfileForm` resets SEO DNA fields.
     - Lines 3058-3069: `fillChannelProfileForm` populates SEO DNA fields.
     - Lines 3518-3543: Form submission serializes `payload.seo_keyword_dna`.
     - Lines 1198-1200: `normalizeTopic` returns `titleTarget`, `titleVi`, `seoKeywordDna`.
     - Lines 2406-2435: `renderCreateTopicSuggestions` renders the `🔑 SEO DNA: [Keyword] · [Meaning VI]` badge and displays both native and Vietnamese titles.
   - Syntax verification: `node -c static/app.js` executed with exit code 0.

7. **Non-Destructive Job Preservation (R4)**:
   - Verified active job `20261019-185102-31983814`: `data/jobs/20261019-185102-31983814/job.json` exists, status is `completed`, and its workspace path is intact.
   - Verified `data/radar.db` exists and was untouched.

8. **Automated Test Results**:
   - Dedicated M2 Test Suite:
     `python -m pytest tests/test_channel_seo_keyword_dna.py -v`
     Result: **9 passed, 170 warnings in 1.67s** (exit code 0).
   - Full Regression Test Suite:
     `python -m pytest tests/test_anti_duplicate_memory_and_workspace.py tests/test_adversarial_profile_challenge.py tests/test_m1_backend_isolation_backfill.py -q`
     Result: **40 passed, 510 warnings in 58.11s** (exit code 0).

---

## 2. Logic Chain

1. **Requirement R2 & AC2 Mapping**:
   - R2 mandates persisting structured `seo_keyword_dna` across Channel Profiles and Projects, pre-configuring `channel-e544a64b7c` with `중국 실화 사건` and `"Vụ Án Có Thật ở Trung Quốc"`, enforcing keyword placement in Step 00 topic suggestions, injecting SEO direction in Step 01 prompts, and auto-validating primary keywords/merging hashtags in Step 07 packaging.
   - Observations 1, 2, 3, 4, 5, 6 confirm all schema definitions, service logic, prompt builders, validators, and UI bindings are implemented.
   - Observation 8 confirms that all 9 dedicated unit and integration tests covering each of these capabilities pass.

2. **Integrity Audit**:
   - Checked for hardcoded expected strings in production code: None found. `apply_seo_keyword_dna_to_title` uses regex decomposition and generic string templates; `validate_phase_quality` uses case-insensitive string containment and set operations.
   - Checked for facade or dummy implementations: None found. The methods actively mutate data structures and write verified files to disk atomically.
   - Checked for bypassed workflows: None found.
   - Checked for fabricated test outputs: None found. Commands were executed directly and yielded verifiable zero exit codes.

3. **Regression Safety (R4)**:
   - Observation 7 proves that existing job `20261019-185102-31983814` and SQLite databases remain completely preserved.
   - Observation 8 proves that all 40 prior tests across anti-duplicate topic memory, adversarial cloning, and M1 backend isolation continue to pass without regression.

---

## 3. Caveats

- **No Caveats**: All criteria outlined in `ORIGINAL_REQUEST.md` (R2, AC2, R4) are fully satisfied and independently verified with automated tests.
- Minor design note: In `apply_seo_keyword_dna_to_title`, `smart_seo_flexible` currently prepends `[primary_title_keyword]` to the title as a sensible default when dashes or quotes are present or when falling back from natural hook parsing. This satisfies the requirement and prevents keyword duplication.

---

## 4. Conclusion

**Verdict: APPROVE**

Milestone M2 (Persistent Channel SEO Keyword DNA) is implemented cleanly, robustly, and without integrity violations. Canonical profiles persist valid SEO DNA, REST endpoints and UI forms preserve and deep merge fields, Step 00 topic discovery formats dual-language titles with SEO badges, Step 01 prompts guide script generation, Step 07 auto-enforces primary keywords and merges mandatory hashtags, and all 49 automated tests pass.

---

## 5. Verification Method

To independently reproduce this verification:

```powershell
# 1. Run dedicated M2 SEO Keyword DNA test suite
python -m pytest tests/test_channel_seo_keyword_dna.py -v

# 2. Run full regression test suite
python -m pytest tests/test_anti_duplicate_memory_and_workspace.py tests/test_adversarial_profile_challenge.py tests/test_m1_backend_isolation_backfill.py -q

# 3. Validate frontend JavaScript syntax
node -c static/app.js

# 4. Verify canonical profiles integrity
python -X utf8 -c "import json; data=json.load(open('data/channel_profiles.json', encoding='utf-8')); assert all(p.get('seo_keyword_dna', {}).get('primary_title_keyword') for p in data['profiles']); print('All profiles verified with valid primary_title_keyword')"
```

### Invalidation Conditions
- Any profile in `data/channel_profiles.json` missing `seo_keyword_dna`.
- Topic discovery in Step 00 emitting titles without `primary_title_keyword`.
- PUT /api/radar/channel-profiles stripping `seo_keyword_dna`.
- Step 07 `validate_phase_quality("seo")` failing to enforce the primary keyword or failing to merge mandatory hashtags.
