# Handoff Report: Adversarial Stress & Isolation Testing (Milestone 1)

**Agent**: challenger_m1_1 (Critic / Specialist)  
**Parent Orchestrator ID**: `5aa18375-8f2e-479e-b627-f1d6f5283a45`  
**Verdict**: **REQUEST_CHANGES**  
**Date**: 2026-10-18T20:13:00Z  

---

## 1. Observation

A standalone adversarial stress and isolation test suite was authored in `tests/test_adversarial_backend_isolation.py` (18 test cases) and executed against `services/job_service.py`, `services/channel_profile_service.py`, and `server.py` using:
`python -m pytest tests/test_adversarial_backend_isolation.py -v --basetemp=.pytest_tmp3`

### Test Execution Results
- **15 Tests PASSED**:
  - `test_adv_modify_non_existent_job_id_raises_key_error`: Verified direct service calls on non-existent IDs raise `KeyError` without creating files or directories.
  - `test_adv_modify_non_existent_job_via_api`: Verified `PATCH /api/jobs/{fake_id}` returns 404 with `"detail": "Không tìm thấy dự án"`.
  - `test_adv_modify_path_traversal_and_special_job_ids` (5 test variants): Verified traversal strings (`../../etc/passwd`, `..\\..\\data\\channel_profiles.json`, `../another_folder`, `!@#$%^&*()`, `"   "`) are safely rejected and do not touch files outside `data/jobs/`.
  - `test_adv_cross_job_mutation_prevention`: Verified attempting to mutate Job Beta while targeting Job Alpha (via `job_id`, `id`, `selectedId`, or draft mutations) is rejected with `ValueError` and leaves Job Beta completely untouched.
  - `test_adv_cross_job_mutation_via_api`: Verified HTTP cross-mutation attacks return 400 Bad Request and leave target data intact.
  - `test_adv_concurrent_job_updates_same_job`: Verified 25 parallel threads updating the same job write atomically without JSON corruption or race conditions.
  - `test_adv_concurrent_job_updates_distinct_jobs_zero_bleed`: Verified 10 concurrent jobs being updated across 8 worker threads maintain 100% data partition with zero bleed.
  - `test_adv_concurrent_channel_profile_updates_and_clones`: Verified 20 concurrent threads updating and reading `data/channel_profiles.json` maintain valid JSON structure and proper field isolation.
  - `test_adv_empty_and_minimal_payloads`: Verified empty `{}` payloads do not overwrite or destroy existing records.
  - `test_adv_type_confusion_in_profile_creation`: Verified invalid profile types (e.g. non-numeric durations) fall back safely to defaults.
  - `test_adv_job_creation_with_non_existent_channel_profile`: Verified orphaned job creation does not crash.

- **3 Tests FAILED (Confirmed Vulnerabilities)**:

#### Failure 1: HTTP 500 on Malformed Non-Dict Payload
- **Test**: `test_adv_malformed_non_dict_payload_returns_400_not_500`
- **Output**:
  ```
  FAILED tests/test_adversarial_backend_isolation.py::test_adv_malformed_non_dict_payload_returns_400_not_500 - assert (500 == 400 or 500 == 422)
  where 500 = <Response [500 Internal Server Error]>.status_code
  ```
- **Code Location**: `server.py` lines 157–167:
  ```python
  try:
      payload = await request.json()
      if not isinstance(payload, dict):
          raise HTTPException(status_code=400, detail="Payload must be a JSON object")
      return job_service.update_job(job_id, payload)
  except KeyError as exc:
      raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
  except ValueError as exc:
      raise HTTPException(status_code=400, detail=str(exc)) from exc
  except Exception as exc:
      raise HTTPException(status_code=500, detail=str(exc)) from exc
  ```

#### Failure 2: Single Corrupted Job Breaks `list_jobs()` for All Projects (Global DoS)
- **Test**: `test_adv_malformed_phases_payload_isolation_break`
- **Output**:
  ```
  FAILED tests/test_adversarial_backend_isolation.py::test_adv_malformed_phases_payload_isolation_break
  Failed: CRITICAL ISOLATION BREACH: Malformed update to Job 20261019-031147-7e7e2a90 broke list_jobs() for all jobs!
  Exception: dictionary update sequence element #0 has length 1; 2 is required
  ```
- **Code Location**:
  - `services/job_service.py` line 43 (`update_job` does not validate that `phases` is a dict).
  - `documentary/store.py` line 140:
    ```python
    if key == "phases" and isinstance(value, dict):
        ...
    else:
        job[key] = value  # blindly stores non-dict value into job["phases"]
    ```
  - `documentary/store.py` line 44:
    ```python
    @staticmethod
    def _normalize_job(job: dict[str, Any]) -> dict[str, Any]:
        phases = dict(job.get("phases") or {})  # crashes with ValueError if phases is a string
    ```
  - `documentary/store.py` line 191 (`list()` only catches `(OSError, json.JSONDecodeError)`, crashing on `ValueError`).

#### Failure 3: Profile Schema Degradation on Malformed Nested Fields
- **Test**: `test_adv_malformed_nested_profile_structures_corrupts_storage`
- **Output**:
  ```
  FAILED tests/test_adversarial_backend_isolation.py::test_adv_malformed_nested_profile_structures_corrupts_storage
  AssertionError: CRITICAL SCHEMA DEGRADATION: editing_dna in channel-test-1 was overwritten with <class 'str'>: not_a_valid_dict
  assert False where False = isinstance('not_a_valid_dict', dict)
  ```
- **Code Location**: `services/channel_profile_service.py` lines 414–427:
  ```python
  if key == "default_creative_brief" and isinstance(value, dict):
      merged_brief = dict(existing.get("default_creative_brief") or {})
      merged_brief.update(value)
      updated["default_creative_brief"] = merged_brief
  elif key == "editing_dna" and isinstance(value, dict):
      merged_dna = dict(existing.get("editing_dna") or {})
      merged_dna.update(value)
      updated["editing_dna"] = merged_dna
  elif key == "self_learning_memory" and isinstance(value, dict):
      merged_mem = dict(existing.get("self_learning_memory") or {})
      merged_mem.update(value)
      updated["self_learning_memory"] = merged_mem
  else:
      updated[key] = value  # Non-dict value overwrites structured dict with string!
  ```

---

## 2. Logic Chain

1. **Regarding Failure 1 (`server.py`)**:
   - `HTTPException` in Starlette/FastAPI inherits from `Exception`.
   - In `server.py` line 159, raising `HTTPException(status_code=400, ...)` inside the `try:` block triggers the enclosing `except Exception as exc:` block on line 165.
   - Line 166 executes `raise HTTPException(status_code=500, detail=str(exc)) from exc`.
   - Therefore, any non-dict JSON body sent to `PATCH /api/jobs/{job_id}` causes an unexpected `500 Internal Server Error` instead of a standard `400 Bad Request`.

2. **Regarding Failure 2 (Isolation Breach in `JobStore` / `JobService`)**:
   - When a user sends a payload containing `{"phases": "corrupted"}` to `JobService.update_job`, `sanitized_patch` retains `"phases": "corrupted"` because `JobService` only filters ID fields and draft flags.
   - `JobStore.update` checks `if key == "phases" and isinstance(value, dict):`. Because `value` is a string, it executes the fallback `else: job[key] = value`, persisting `"phases": "corrupted"` into `job.json`.
   - Subsequent calls to `JobStore.get` or `JobStore.list` invoke `_normalize_job(job)`.
   - Line 44 executes `phases = dict(job.get("phases") or {})`. In Python, `dict("corrupted")` raises `ValueError: dictionary update sequence element #0 has length 1; 2 is required`.
   - Because `JobStore.list()` scans all jobs in `data/jobs/` and only catches `(OSError, json.JSONDecodeError)`, one corrupted job causes `JobStore.list()` to fail unconditionally with `ValueError`.
   - Consequently, `GET /api/jobs` crashes with 500 for **every user and project**, violating backend isolation.

3. **Regarding Failure 3 (Storage Degradation in `ChannelProfileService`)**:
   - When `update_profile` receives an update for `editing_dna`, `default_creative_brief`, or `self_learning_memory` that is not a dictionary (e.g. `{"editing_dna": "invalid"}`), the condition `isinstance(value, dict)` evaluates to False.
   - Execution falls into `else: updated[key] = value`.
   - The method writes the string `"invalid"` to `data/channel_profiles.json`.
   - Downstream consumers expecting a dictionary (e.g., `JobService.create_job`, `test_channel_profiles_storage_integrity`, Remotion rendering) crash with `TypeError: string indices must be integers`.

---

## 3. Caveats

- **Operating System File Locking**: Concurrency tests ran within a single multi-threaded process. Inter-process file locking was not tested across multiple distinct OS processes simultaneously mutating `data/channel_profiles.json`, though `os.replace` provides atomic filesystem replacement on Windows and POSIX.
- **Network Interruptions**: Simulating broken HTTP sockets mid-transmission was not tested at the TCP socket layer; however, `tempfile` + `os.replace` pattern protects against partial file writes.

---

## 4. Conclusion & Required Actions

### Verdict
**REQUEST_CHANGES**

The core isolation mechanics (ID cross-mutation prevention, draft decoupling, path traversal rejection, and thread-safe locking) are robust and passed all adversarial attacks. However, three critical defect areas must be resolved before Milestone 1 can be certified:

### Required Fixes for `worker_m1_1`:
1. **Fix `server.py` (`patch_job`)**:
   - Either change line 159 to `raise ValueError("Payload must be a JSON object")` (matching lines 80 and 111), OR add `except HTTPException: raise` before `except Exception as exc:`.
2. **Fix `services/job_service.py` & `documentary/store.py`**:
   - In `services/job_service.py` (`update_job`), validate:
     ```python
     if "phases" in sanitized_patch and not isinstance(sanitized_patch["phases"], dict):
         raise ValueError("Field 'phases' must be an object")
     ```
   - In `documentary/store.py` (`_normalize_job` line 44), harden the phase normalization defensively:
     ```python
     raw_phases = job.get("phases")
     phases = dict(raw_phases) if isinstance(raw_phases, dict) else {}
     ```
   - In `documentary/store.py` (`list`), catch `ValueError` in the try block so a corrupted file never halts listing other valid jobs:
     ```python
     except (OSError, json.JSONDecodeError, ValueError):
         continue
     ```
3. **Fix `services/channel_profile_service.py` (`update_profile`)**:
   - In `update_profile`, reject or ignore non-dict values for structured schema fields:
     ```python
     for key, value in patch.items():
         if value is None:
             continue
         if key in {"default_creative_brief", "editing_dna", "self_learning_memory"}:
             if not isinstance(value, dict):
                 raise ValueError(f"Field '{key}' must be an object")
     ```

---

## 5. Verification Method

To verify these findings and confirm subsequent fixes:
1. Run the standalone adversarial stress test suite:
   ```powershell
   python -m pytest tests/test_adversarial_backend_isolation.py -v --basetemp=.pytest_tmp3
   ```
2. Verify that all 18 test cases pass (currently 15 pass, 3 fail on the exact bugs documented above).
3. Run the baseline suite to guarantee zero regression:
   ```powershell
   python -m pytest tests/test_m1_backend_isolation_backfill.py --basetemp=.pytest_tmp3
   ```
