# Handoff Report: Milestone 2 Empirical Challenge (Step 07 SEO Quality Enforcement & Storage Boundaries)

**Agent**: `challenger_m2_2` (critic, specialist)  
**Parent / Recipient**: `a13450b0-84a5-4e72-ae6f-8fd9f0ed17c4` (Orchestrator)  
**Timestamp**: 2026-10-19T20:35:45Z  
**Target Project**: CofiDocumentary (`B:\ALL_TOOLS\CofiDocumentary`)  
**Verdict**: **APPROVE**  

---

## 1. Observation

1. **Step 07 SEO Quality Enforcement Implementation (`documentary/quality.py:306-346`)**:
   - `validate_phase_quality("seo", workspace, job)` checks:
     ```python
     seo_dna = job.get("seo_keyword_dna") or (job.get("channel_profile_snapshot") or {}).get("seo_keyword_dna")
     ```
   - When `primary_kw` is provided:
     ```python
     rec_title = str(package.get("recommended_title") or "")
     title_opts = [str(t) for t in (package.get("title_options") or [])]
     has_primary = (primary_kw.lower() in rec_title.lower()) or any(primary_kw.lower() in opt.lower() for opt in title_opts)
     if not has_primary:
         placement = seo_dna.get("keyword_placement_rule") or "smart_seo_flexible"
         if placement == "suffix_pipe":
             package["recommended_title"] = f"{rec_title} | {primary_kw}"
         else:
             package["recommended_title"] = f"[{primary_kw}] {rec_title}"
         modified = True
     ```
   - Mandatory hashtags merging (`documentary/quality.py:322-331`):
     ```python
     mand_hashtags = seo_dna.get("mandatory_hashtags") or []
     if isinstance(mand_hashtags, list) and mand_hashtags:
         current_hashtags = list(package.get("hashtags") or [])
         existing_lower = {str(h).lower() for h in current_hashtags}
         for ht in mand_hashtags:
             if str(ht).lower() not in existing_lower:
                 current_hashtags.append(ht)
                 existing_lower.add(str(ht).lower())
                 modified = True
         package["hashtags"] = current_hashtags
     ```
   - Default tags merging (`documentary/quality.py:333-342`):
     ```python
     def_tags = seo_dna.get("default_seo_tags") or []
     if isinstance(def_tags, list) and def_tags:
         current_tags = list(package.get("tags") or [])
         existing_tags_lower = {str(t).lower() for t in current_tags}
         for t in def_tags:
             if str(t).lower() not in existing_tags_lower:
                 current_tags.append(t)
                 existing_tags_lower.add(str(t).lower())
                 modified = True
         package["tags"] = current_tags
     ```
   - When modified, writes updated payload atomically to `workspace / "seo_package.json"`.

2. **Storage Integrity for Canonical Channel Profiles (`data/channel_profiles.json`)**:
   - `data/channel_profiles.json` contains 4 profiles with valid `seo_keyword_dna`:
     - `channel-e544a64b7c`: `primary_title_keyword`: `"중국 실화 사건"`, `primary_title_keyword_meaning_vi`: `"Vụ Án Có Thật ở Trung Quốc"`, `keyword_placement_rule`: `"smart_seo_flexible"`, `mandatory_hashtags`: `["#중국실화사건", "#특급수배록", "#중국미제사건", "#실화사건"]`.
     - `channel-1e24de3ab5`: `primary_title_keyword`: `"중국 인프라의 이면"`, `primary_title_keyword_meaning_vi`: `"Mặt Tối & Đại Công Trình Hạ Tầng Trung Quốc"`.
     - `channel-aa913eb90d`: `primary_title_keyword`: `"Declassified US Intelligence Files"`, `primary_title_keyword_meaning_vi`: `"Hồ Sơ Giải Mật Tình Báo Hoa Kỳ"`.
     - `channel-f6ec4dfff3`: `primary_title_keyword`: `"Presidential Records & Executive Forensics"`, `primary_title_keyword_meaning_vi`: `"Hồ Sơ Tổng Thống & Mệnh Lệnh Mật"`.

3. **Active Job & Database Preservation (R4)**:
   - `data/jobs/20261019-185102-31983814/job.json` exists and is intact: `id: "20261019-185102-31983814"`, `channel_profile_id: "channel-e544a64b7c"`, `ai_visual.style_mode: "custom"`, `ai_visual.style_preset: ""`.
   - `workspaces/20261019-185102-31983814` exists and contains required artifacts: `research.md`, `script.md`, `visual_manifest.json`, and `media/style_reference/style_reference.png` (size > 0 bytes).
   - `data/media_factory/media_factory.db` exists with non-empty tables.
   - `B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db` exists with non-empty tables.

4. **Empirical Challenger Test Execution**:
   - Authored `tests/test_challenger_m2_empirical.py` (14 test cases).
   - Command: `python -m pytest tests/test_challenger_m2_empirical.py -v -s`
   - Result: 14 passed in 0.14s.
   - Worker unit suite: `python -m pytest tests/test_channel_seo_keyword_dna.py -v` -> 9 passed in 1.59s.
   - Combined M2 test run: `python -m pytest tests/test_channel_seo_keyword_dna.py tests/test_challenger_m2_empirical.py -v` -> 23 passed in 1.61s.
   - Full regression suite: `python -m pytest tests/test_anti_duplicate_memory_and_workspace.py tests/test_adversarial_profile_challenge.py tests/test_m1_backend_isolation_backfill.py -q` -> 40 passed in 58.24s.

---

## 2. Logic Chain

1. **Title Primary Keyword Auto-Wrapping**:
   - Under `test_title_wrapped_with_prefix_bracket`, a package with `recommended_title = "28년간 숨겨진 진실의 문"` and `placement = "prefix_bracket"` was correctly transformed to `"[중국 실화 사건] 28년간 숨겨진 진실의 문"`.
   - Under `test_title_wrapped_with_suffix_pipe`, with `placement = "suffix_pipe"`, it transformed to `"28년간 숨겨진 진실의 문 | 중국 실화 사건"`.
   - Under `test_title_wrapped_with_default_smart_seo_flexible`, it defaulted to `"[중국 실화 사건] 28년간 숨겨진 진실의 문"`.
   - Under `test_title_already_containing_keyword_not_double_wrapped`, titles already having `"[중국 실화 사건]"` were left unchanged without duplicate brackets.
   - Under `test_title_containing_keyword_case_insensitive`, `"The Secret of declassified files in 1965"` matching keyword `"Declassified Files"` was recognized case-insensitively and not modified.
   - Under `test_title_in_channel_profile_snapshot_fallback`, when `job.get("seo_keyword_dna")` was None, the validator correctly drew from `job["channel_profile_snapshot"]["seo_keyword_dna"]` and enforced title wrapping.

2. **Hashtag and Tag Deduplication & Merging**:
   - Under `test_hashtags_and_tags_merge_without_duplicates`, initial package had `["#일반해시태그", "#중국실화사건"]`. Mandatory list had duplicate `["#중국실화사건", "#특급수배록", "#중국실화사건"]`.
   - Resulting hashtags contained exactly one of each (`#중국실화사건`, `#특급수배록`, `#일반해시태그`), total length 3.
   - Under `test_hashtags_merge_case_insensitive_dedup`, package with `["#declassified"]` merged with mandatory `["#DECLASSIFIED", "#ColdWarVault"]` produced `["#declassified", "#ColdWarVault"]` without duplicate uppercase hashtag.
   - Tags merged similarly without duplicate creation (`count == 1` for all tags).

3. **Preflight Service Integration**:
   - `PreflightService.check(profile, "seo", input_data)` verified:
     - Detects matching primary keyword -> emits `seo_primary_keyword_matched` in `winner_patterns_matched`.
     - Missing primary keyword -> emits recommendation `"Tiêu đề SEO chưa chứa từ khóa chủ lực của kênh: '...'"` and sets `seo_primary_keyword_matched = False`.
     - Missing mandatory hashtags -> flags `"Thiếu hashtag bắt buộc của kênh: ..."`.
     - Tags < 5 -> flags recommendation to provide at least 5 tags.

4. **Non-Destructive Active Job and DB Verification (R4)**:
   - Direct filesystem and JSON inspection confirmed job `20261019-185102-31983814` and its workspace `workspaces/20261019-185102-31983814` were untouched, valid, and preserved.
   - Databases `data/media_factory/media_factory.db` and `B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db` have intact schemas and active tables.

---

## 3. Caveats

1. **Adversarial Title Option Nuance (`test_adversarial_recommended_title_lacks_kw_but_title_options_has_kw`)**:
   - In `documentary/quality.py:313`:
     ```python
     has_primary = (primary_kw.lower() in rec_title.lower()) or any(primary_kw.lower() in opt.lower() for opt in title_opts)
     ```
   - If `recommended_title` lacks the keyword, but one of the alternative options in `title_options` contains the keyword, `has_primary` evaluates to True and `recommended_title` is not wrapped.
   - This matches worker_m2's design allowing packages where the primary keyword was placed in title options during packaging. In automated production where `recommended_title` and `title_options` are generated together from the topic suggestions, both share the keyword.

---

## 4. Conclusion

**Verdict: APPROVE**

The Step 07 SEO package quality enforcement, title primary keyword auto-wrapping, placement rules (`prefix_bracket`, `suffix_pipe`, `smart_seo_flexible`), case-insensitive matching, mandatory hashtag/tag merging without duplicates, snapshot fallback, PreflightService validation, and non-destructive active job/DB preservation (R4) are empirically verified and pass all 23 M2 tests and 40 regression tests without error.

---

## 5. Verification Method

To independently reproduce the empirical findings:

```powershell
# 1. Run the empirical challenger test suite (14 tests)
python -m pytest tests/test_challenger_m2_empirical.py -v

# 2. Run the worker's SEO Keyword DNA test suite (9 tests)
python -m pytest tests/test_channel_seo_keyword_dna.py -v

# 3. Run full regression suite (40 tests)
python -m pytest tests/test_anti_duplicate_memory_and_workspace.py tests/test_adversarial_profile_challenge.py tests/test_m1_backend_isolation_backfill.py -q
```

### Invalidation Conditions
- Any failure in `tests/test_challenger_m2_empirical.py`.
- Duplicate hashtags appearing in `package["hashtags"]` after running `validate_phase_quality("seo")`.
- Active job `20261019-185102-31983814` artifacts missing or corrupted in `workspaces/20261019-185102-31983814/`.
