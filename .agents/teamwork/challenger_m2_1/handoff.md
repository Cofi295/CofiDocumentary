# Adversarial Challenge Handoff: Milestone 2 — SEO Keyword DNA Verification

**Agent**: `challenger_m2_1` (EMPIRICAL CHALLENGER / critic, specialist)  
**Parent / Recipient**: `orchestrator_2` (`a13450b0-84a5-4e72-ae6f-8fd9f0ed17c4`)  
**Timestamp**: 2026-10-19T20:38:00Z  
**Verdict**: **FAIL (Changes Requested)**  

---

## 1. Observation

Direct empirical observations from executing the verification harness (`tests/test_adversarial_seo_dna_stress.py`) and inspecting implementation code:

1. **Title Parsing Truncation Bug in `apply_seo_keyword_dna_to_title`**:
   - In `documentary/service.py:101, 111`:
     ```python
     match = re.match(r"^(.*?)\s*\((.*?)\)$", raw_title)
     ```
   - Running:
     ```python
     apply_seo_keyword_dna_to_title("(단독 보도) 28년간 숨어 지낸 범인 (Kẻ thủ ác)", {"primary_title_keyword": "중국 실화 사건", "primary_title_keyword_meaning_vi": "Vụ Án Có Thật ở Trung Quốc"})
     ```
     Produces:
     - `target_formatted`: `'[중국 실화 사건] '` (**Empty Korean title body; only the bracketed keyword remains**).
     - `vi_formatted`: `'[Vụ Án Có Thật ở Trung Quốc] 단독 보도) 28년간 숨어 지낸 범인 (Kẻ thủ ác'` (**Unmatched closing parenthesis `)` and swallowed Korean text**).
     - `full_title`: `'[중국 실화 사건]  ([Vụ Án Có Thật ở Trung Quốc] 단독 보도) 28년간 숨어 지낸 범인 (Kẻ thủ ác))'`.
   - Running with an intermediate parenthetical (e.g. series or episode label):
     ```python
     apply_seo_keyword_dna_to_title("사건의 전말 (1부) (Toàn cảnh vụ án)", seo_dna)
     ```
     Produces:
     - `target_formatted`: `'[중국 실화 사건] 사건의 전말'` (Truncated; `(1부)` was stripped from the target title).
     - `vi_formatted`: `'[Vụ Án Có Thật ở Trung Quốc] 1부) (Toàn cảnh vụ án'` (Contaminated with Korean text and unmatched parenthesis `)`).

2. **Step 07 Quality Contract Primary Keyword Bypass on `recommended_title`**:
   - In `documentary/quality.py:313`:
     ```python
     has_primary = (primary_kw.lower() in rec_title.lower()) or any(primary_kw.lower() in opt.lower() for opt in title_opts)
     if not has_primary:
         package["recommended_title"] = f"[{primary_kw}] {rec_title}"
     ```
   - When `recommended_title` is `"28년간 숨겨진 진실"` (missing primary keyword), but `title_options[0]` contains `"[중국 실화 사건]"`, `has_primary` evaluates to `True`.
   - `package["recommended_title"]` is left completely un-wrapped and missing the channel's primary keyword anchor.
   - Consequently, when `PreflightService.check(profile, "seo", package)` runs on this output, it generates an error/warning: `"Tiêu đề SEO chưa chứa từ khóa chủ lực của kênh: '중국 실화 사건'"`.

3. **Passing Stress Areas Verified Empirically**:
   - **Profile Cloning Deep Copy Isolation**: Mutating `cloned["seo_keyword_dna"]` in-place, updating clone via `ChannelProfileService.update_profile`, or mutating clone via `PUT /api/radar/channel-profiles/{clone_id}` makes zero modifications to the parent profile in memory or in `data/channel_profiles.json` (`test_cloned_profile_deep_independence_in_memory`, `test_cloned_profile_mutation_via_service_update`, `test_cloned_profile_isolation_via_fastapi_rest` all PASSED).
   - **Partial PATCH/PUT Updates**: Sending partial payloads (e.g. updating only `label`, or updating only `primary_title_keyword`, or updating only `primary_title_keyword_meaning_vi`) deep-merges successfully without dropping `secondary_anchor_keywords`, `mandatory_hashtags`, or `default_seo_tags` (`test_partial_update_without_seo_dna_preserves_all_seo_fields`, `test_partial_seo_dna_update_preserves_sibling_fields`, `test_rest_patch_partial_seo_dna_preservation` all PASSED).
   - **Step 00 Topic Suggestions**: `_discover_profile_topics_strict_dna` and `POST /api/radar/channel-profiles/{id}/today` return valid `title_target` and `title_vi` without throwing `KeyError` across all 4 canonical channel profiles and on mock profiles with empty `seo_keyword_dna` (`test_strict_dna_topic_discovery_returns_valid_dual_titles`, `test_rest_api_profile_today_returns_dual_titles_without_error`, `test_topic_discovery_with_empty_or_none_seo_dna_fallback` all PASSED).

---

## 2. Logic Chain

1. **Title Parsing Logic Flaw (Finding 1)**:
   - Observation: `re.match(r"^(.*?)\s*\((.*?)\)$", raw_title)` uses a non-greedy wildcard `^(.*?)` followed by `\s*\(`.
   - Deduction: The regex engine matches the *first* opening parenthesis `(` encountered in `raw_title`.
   - Consequence: Any candidate title that contains parentheses prior to the trailing translation (e.g., `(단독)`, `(실화)`, `(1998년)`, `(1부)`) has its target-language title truncated or completely blanked out, and the extracted Vietnamese translation becomes corrupted with Korean text and an unmatched closing bracket.
   - Requirement Violation: Violates Requirement R2 and AC2 (clean dual-language formatting and preservation of candidate title text).

2. **Quality Contract Inconsistency (Finding 2)**:
   - Observation: `validate_phase_quality("seo")` in `documentary/quality.py:313` accepts the package without wrapping `recommended_title` if any item in `title_opts` contains `primary_kw`.
   - Deduction: `recommended_title` is the actual primary title exported and used for YouTube Studio metadata. If `recommended_title` lacks the keyword anchor, the video fails to build channel topical authority.
   - Conflict: `PreflightService.check(profile, "seo", input_data)` strictly tests `primary_kw.lower() in recommended_title.lower()`. The quality contract allows a package through that immediately fails preflight.
   - Requirement Violation: Violates Requirement R2 ("Step 07: Automatically inject and validate the channel's `primary_title_keyword`... so 100% of videos on the channel build unified topical authority").

---

## 3. Caveats

- **No Caveats on Passings**: Profile cloning deep copy isolation and partial update preservation are rock solid and fully verified.
- **Scope of Review**: Did not modify implementation code in accordance with review-only constraints. The bugs were isolated in a standalone test suite (`tests/test_adversarial_seo_dna_stress.py`).

---

## 4. Conclusion

**Verdict: FAIL (Changes Requested)**

The implementation by `worker_m2` successfully addresses schema definitions, canonical backfills, profile cloning isolation, and partial update merging. However, two concrete bugs must be resolved before approval:

1. **Fix `apply_seo_keyword_dna_to_title` in `documentary/service.py`**:
   - Change `r"^(.*?)\s*\((.*?)\)$"` to match the trailing parenthetical (e.g. `r"^(.*)\s*\(([^()]+)\)$"`).
   - Ensure leading parentheses (e.g. `(단독 보도)`) and intermediate parentheses (e.g. `(1부)`) remain part of `target_part` and are never truncated.
2. **Fix `validate_phase_quality("seo")` in `documentary/quality.py`**:
   - Ensure `package["recommended_title"]` specifically is checked and auto-wrapped if it lacks `primary_kw`, independent of whether an alternative in `title_options` contains it.

---

## 5. Verification Method

To independently verify these findings and check subsequent fixes:

1. **Run the Adversarial Stress Suite**:
   ```powershell
   python -m pytest tests/test_adversarial_seo_dna_stress.py -v
   ```
2. **Direct CLI Reproduction of Finding 1**:
   ```powershell
   python -X utf8 -c "from documentary.service import apply_seo_keyword_dna_to_title; res = apply_seo_keyword_dna_to_title('(단독 보도) 28년간 숨어 지낸 범인 (Kẻ thủ ác)', {'primary_title_keyword': '중국 실화 사건', 'primary_title_keyword_meaning_vi': 'Vụ Án'}); print('TARGET:', repr(res[1])); print('VI:', repr(res[2]))"
   ```
   *Current (buggy) output*: `TARGET: '[중국 실화 사건] '` (Empty!) and `VI: '[Vụ Án] 단독 보도) 28년간 숨어 지낸 범인 (Kẻ thủ ác'`.  
   *Expected (fixed) output*: `TARGET: '[중국 실화 사건] (단독 보도) 28년간 숨어 지낸 범인'` and `VI: '[Vụ Án] Kẻ thủ ác'`.

3. **Direct CLI Reproduction of Finding 2**:
   ```powershell
   python -X utf8 -c "from documentary.quality import validate_phase_quality; from pathlib import Path; import json, tempfile;
   with tempfile.TemporaryDirectory() as td:
       ws = Path(td)
       pkg = {'recommended_title': 'Title Without Keyword', 'title_options': ['Alt 1 With 중국 실화 사건'], 'description': 'Desc', 'tags': ['tag1'], 'hashtags': ['#hash1'], 'reference_analysis': {}, 'thumbnail': {'prompt': 'plain minimal background featuring text overlay with real subject', 'overlay_text': 'overlay', 'visual_priority': 'dynamic', 'background_policy': 'minimal_or_none'}}
       (ws / 'seo_package.json').write_text(json.dumps(pkg))
       job = {'quality_contract': {'enforce': True}, 'seo_keyword_dna': {'primary_title_keyword': '중국 실화 사건'}}
       validate_phase_quality('seo', ws, job)
       res = json.loads((ws / 'seo_package.json').read_text())
       print('Recommended Title:', res['recommended_title'])
   "
   ```
   *Current (buggy) output*: `Title Without Keyword` (Bypassed).  
   *Expected (fixed) output*: `[중국 실화 사건] Title Without Keyword`.
