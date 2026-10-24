# Empirical Challenger Handoff Report: Milestone 2 Re-Verification

**Agent**: `challenger_m2_3` (EMPIRICAL CHALLENGER / critic, specialist)  
**Parent / Recipient**: `orchestrator_2` (`a13450b0-84a5-4e72-ae6f-8fd9f0ed17c4`)  
**Timestamp**: 2026-10-19T20:52:45Z  
**Verdict**: **APPROVE**  

---

## 1. Observation

Direct empirical observations from executing the test suites, inspecting code diffs, and running standalone stress probes:

1. **Title Trailing Parenthetical Extraction Fix in `documentary/service.py`**:
   - Lines 101-104 and 111-118 in `documentary/service.py`:
     ```python
     match = re.match(r"^(.*)\s*\(([^()]+)\)$", raw_title)
     if match and match.group(1).strip():
         target_part = match.group(1).strip()
         vi_part = match.group(2).strip()
     else:
         target_part = raw_title
         vi_part = ""
     ```
   - Empirical probe with multi-parenthetical and leading parenthetical input:
     ```python
     apply_seo_keyword_dna_to_title("(단독) 28년 미제사건 (1부) (Toàn cảnh vụ án)", seo_dna)
     ```
     Yields:
     - `target_formatted`: `'[중국 실화 사건] (단독) 28년 미제사건 (1부)'` (Full Korean title preserved, including `(단독)` and `(1부)`).
     - `vi_formatted`: `'[Vụ Án Có Thật ở Trung Quốc] Toàn cảnh vụ án'` (Clean Vietnamese translation extracted without Korean contamination or unbalanced parentheses).
     - `full_title`: `'[중국 실화 사건] (단독) 28년 미제사건 (1부) ([Vụ Án Có Thật ở Trung Quốc] Toàn cảnh vụ án)'`.

2. **Step 07 Quality Contract Auto-Wrap Fix in `documentary/quality.py`**:
   - Lines 310-320 in `documentary/quality.py`:
     ```python
     if primary_kw:
         rec_title = str(package.get("recommended_title") or "")
         if primary_kw.lower() not in rec_title.lower():
             placement = seo_dna.get("keyword_placement_rule") or "smart_seo_flexible"
             raw_kw = seo_dna.get("primary_title_keyword") or primary_kw
             if placement == "suffix_pipe":
                 package["recommended_title"] = f"{rec_title} | {raw_kw}"
             else:
                 package["recommended_title"] = f"[{raw_kw}] {rec_title}"
             modified = True
     ```
   - Direct empirical probe when `recommended_title` is missing `primary_title_keyword` but `title_options[0]` contains it:
     - Input `recommended_title`: `'28년간 숨겨진 진실'`.
     - After `validate_phase_quality("seo", ws, job)`: `res["recommended_title"]` is auto-wrapped to `'[중국 실화 사건] 28년간 숨겨진 진실'` (or `'28년간 숨겨진 진실 | 중국 실화 사건'` under `suffix_pipe`).
     - Re-running validation is idempotent and does not duplicate keywords.
     - Passing the resulting package to `PreflightService.check(profile, "seo", updated_pkg)` returned:
       `status: ok`, `details: {'tags_count': 7, 'seo_primary_keyword_matched': True}`.

3. **Empirical Test Suite Execution Results**:
   - `python -m pytest tests/test_adversarial_seo_dna_stress.py -v`:
     - **31 passed in 4.08s** (100% pass rate).
   - `python -m pytest tests/test_channel_seo_keyword_dna.py -v`:
     - **9 passed in 1.55s** (100% pass rate).
   - Combined execution (`python -m pytest tests/test_adversarial_seo_dna_stress.py tests/test_channel_seo_keyword_dna.py -v`):
     - **40 passed in 6.08s** (100% pass rate).

4. **Preservation of Active Job and Databases (R4 Compliance)**:
   - Job workspace `workspaces/20261019-185102-31983814` exists and contains all required artifacts (`research.md`, `script.md`, `visual_manifest.json`, `media/style_reference/style_reference.png`, plus rendered `.render_cache/public_dir` assets and `.producer` logs).
   - `data/jobs/20261019-185102-31983814/job.json` exists and is valid.
   - SQLite databases `data/radar.db`, `data/media_factory/media_factory.db`, and `data/media_factory/cofi_studio.db` (358 jobs, 316 scenes) are intact.
   - Active Google Flow profile `data/media_factory/google-flow-profiles/210336272f514beda9c76b32aea6daf5` is untouched.
   - All 4 canonical profiles in `data/channel_profiles.json` (`channel-e544a64b7c`, `channel-1e24de3ab5`, `channel-aa913eb90d`, `channel-f6ec4dfff3`) remain intact with complete `seo_keyword_dna`.

---

## 2. Logic Chain

1. **Resolution of Title Parsing Truncation (Defect 1)**:
   - In `documentary/service.py`, replacing `^(.*?)` with `^(.*)` guarantees greedy consumption of any parenthetical phrases that appear before the final translation group.
   - Using `\(([^()]+)\)$` restricts the trailing match strictly to the final closed parenthetical containing no nested delimiters.
   - Verifying `match.group(1).strip()` ensures that titles consisting only of parenthetical expressions are not incorrectly split into empty target text.
   - Direct empirical execution with multi-part and prefixed titles confirms zero title truncation and zero parenthetical leaking.

2. **Resolution of Step 07 Quality Auto-Wrapping Bypass (Defect 2)**:
   - In `documentary/quality.py`, decoupling `primary_kw.lower() not in rec_title.lower()` from `title_options` guarantees that the exported metadata field `recommended_title` unconditionally contains the channel's anchor keyword.
   - Because `PreflightService.check()` directly examines `recommended_title`, aligning `validate_phase_quality("seo")` to wrap `recommended_title` ensures that no SEO package produced by Step 07 can fail preflight validation on primary keyword grounds.
   - Tested empirically under multiple placement rules (`prefix_bracket`, `suffix_pipe`) and verified downstream against `PreflightService`.

3. **Total Test Suite Green Status & Non-Destructive Invariance**:
   - All 40 test cases across adversarial stress and core SEO DNA suites pass cleanly without flakiness or cross-test interference.
   - Workspace directories, active jobs, SQLite databases, and Google profiles were verified on disk and via SQLite connections to be 100% preserved per Requirement R4.

---

## 3. Caveats

- **No Caveats**: The remediation by `worker_m2_fix` was minimal, strictly targeted to the 2 failure modes identified by `challenger_m2_1`, and introduced no extraneous side effects or regressions.

---

## 4. Conclusion

**Verdict: APPROVE**

The title parsing truncation and `recommended_title` auto-wrapping defects have been genuinely and cleanly resolved. The implementation fully satisfies Requirements R2, AC2, and R4 of `ORIGINAL_REQUEST.md`. Milestone 2 is certified ready for final orchestrator sign-off and progression.

---

## 5. Verification Method

To independently verify this approval:

1. **Run Adversarial Stress Test Suite**:
   ```powershell
   python -m pytest tests/test_adversarial_seo_dna_stress.py -v
   ```
   *Expected Output*: `31 passed` (100%).

2. **Run Channel SEO Keyword DNA Suite**:
   ```powershell
   python -m pytest tests/test_channel_seo_keyword_dna.py -v
   ```
   *Expected Output*: `9 passed` (100%).

3. **Run Combined Test Suites**:
   ```powershell
   python -m pytest tests/test_adversarial_seo_dna_stress.py tests/test_channel_seo_keyword_dna.py -q
   ```
   *Expected Output*: `40 passed`.

4. **Verify Active Job and DB Integrity**:
   ```powershell
   python -c "from pathlib import Path; assert (Path('workspaces/20261019-185102-31983814/media/style_reference/style_reference.png')).is_file(); assert Path('data/radar.db').is_file(); assert Path('data/media_factory/media_factory.db').is_file(); print('R4 OK')"
   ```
   *Expected Output*: `R4 OK`.
