# Review & Adversarial Challenge Report: Milestone 1 (Backend Data Models, Strict Isolation & Backfill)

**Reviewer**: reviewer_m1_1 (Roles: reviewer, critic)  
**Target Milestone**: Milestone 1 (Backend Data Models, Strict Isolation & Backfill)  
**Timestamp**: 2026-10-18T20:15:00Z  
**Verdict**: **REQUEST_CHANGES**

---

## Review Summary

**Verdict**: **REQUEST_CHANGES**  
While the backfill migration script (`scripts/backfill_migration.py`), Channel Profile service (`services/channel_profile_service.py`), and `PATCH /api/jobs/{job_id}` isolation logic in `services/job_service.py` are robust, high-quality, and pass all existing tests, **an essential contract requirement from PROJECT.md is broken in production job creation**:
1. `server.py` does not route `POST /api/jobs` to `job_service.create_job()`, leaving it delegated to the legacy endpoint in `app.py`.
2. When creating a new project via `POST /api/jobs` with a designated `channel_profile_id`, the created job record **does NOT persist `editing_dna` or `default_creative_brief`** (they are completely omitted from the job record and its `job.json` on disk).
3. Even when `job_service.create_job()` is invoked directly in Python, `self.store.create()` in `documentary/store.py` discards `editing_dna` and `default_creative_brief` because its hardcoded dictionary template drops them.
4. `tests/test_m1_backend_isolation_backfill.py` only checked the 4 existing backfilled jobs and completely omitted a test for `POST /api/jobs`, allowing this contract gap to escape detection.

This directly violates PROJECT.md §Interface Contracts ("`POST /api/jobs`: creates a new project initialized from the assigned channel profile's locked DNA and creative brief") and Requirement R2 ("Once a Channel Profile is assigned to a project, lock and execute the entire production pipeline strictly according to that profile's DNA... and editing recipe").

---

## 1. Observation

1. **Test Suite Execution**:
   - `python -m pytest tests/test_m1_backend_isolation_backfill.py --basetemp=.pytest_tmp -v`:
     All 12 tests PASSED in 0.93s (`test_backups_exist`, `test_channel_profiles_storage_integrity`, `test_jobs_storage_integrity`, `test_get_channel_profiles_list`, `test_get_single_channel_profile`, `test_create_channel_profile_endpoint`, `test_clone_channel_profile_endpoint`, `test_update_channel_profile_put_preserves_unmentioned_fields`, `test_patch_job_strictly_mutates_only_target_job`, `test_patch_job_returns_404_for_non_existent_job`, `test_patch_job_rejects_cross_job_mutation_attempt`, `test_patch_job_rejects_draft_mutation_side_effects`).
   - `python -m pytest tests/e2e/test_ac2_isolation_backfill.py --basetemp=.pytest_tmp -v`:
     All 20 tests PASSED in 0.97s.
   - `python scripts/backfill_migration.py`:
     Successfully executed idempotently, created backups in `data/backups/`, and output `[VALIDATION PASSED] All 4 channel profiles and all 4 jobs verified with non-null complete schemas. MIGRATION COMPLETED SUCCESSFULLY.`

2. **Storage Inspection**:
   - `data/channel_profiles.json`: All 4 profiles (`channel-1e24de3ab5`, `channel-e544a64b7c`, `channel-aa913eb90d`, `channel-f6ec4dfff3`) contain valid, non-null `channel_profile_id`, `visual_strategy`, `default_creative_brief` (10 required keys), `editing_dna` (6 required keys), and `self_learning_memory`.
   - `data/jobs/`: All 4 existing jobs (`20261018-223750-3aecfbcd`, `20261017-164519-fd65f7e1`, `20261017-003022-ecb75736`, `20261015-014818-f0fdc122`) contain valid `channel_profile_id`, `visual_strategy`, `default_creative_brief`, `editing_dna`, and `channel_profile_snapshot`.
   - `data/backups/`: Contains timestamped JSON and folder backups as well as latest pointer copies.

3. **Defect in New Project Creation (`POST /api/jobs`)**:
   - In `server.py` lines 42–52:
     ```python
     filtered_routes = []
     for route in api.router.routes:
         path = getattr(route, "path", "")
         methods = getattr(route, "methods", set())
         if path == "/api/radar/channel-profiles" and methods.intersection({"GET", "POST"}):
             continue
         if path == "/api/radar/channel-profiles/{profile_id}" and methods.intersection({"GET", "PATCH", "PUT", "DELETE"}):
             continue
         filtered_routes.append(route)
     api.router.routes = filtered_routes
     ```
     Notice that `POST /api/jobs` is **NOT** filtered or overridden in `server.py`. It falls through to legacy `app.py::create_job()` calling `DocumentaryService.create_job()`.
   - Running verification:
     ```python
     client = TestClient(create_app())
     resp = client.post('/api/jobs', json={'title': 'Test New Job', 'channel_profile_id': 'channel-1e24de3ab5', 'market': 'KR'})
     data = resp.json()
     print('Has editing_dna?', 'editing_dna' in data) # -> Output: False
     print('Has default_creative_brief?', 'default_creative_brief' in data) # -> Output: False
     ```
   - In `services/job_service.py` lines 65–99:
     `JobService.create_job()` prepares `job_data["editing_dna"]` and `job_data["default_creative_brief"]`, but then delegates directly to `self.store.create(job_data)`.
   - In `documentary/store.py` lines 92–125:
     `JobStore.create()` constructs a static dictionary literal that omits `"editing_dna"` and `"default_creative_brief"`:
     ```python
     job = {
         "id": job_id,
         "title": str(payload.get("title") or "").strip(),
         ...
         "channel_profile_id": payload.get("channel_profile_id"),
         "channel_profile_snapshot": payload.get("channel_profile_snapshot") or {},
         # "editing_dna" and "default_creative_brief" ARE MISSING HERE
     }
     self._write(self._path(job_id), job)
     return self._normalize_job(job)
     ```
     Consequently, calling `JobService().create_job()` directly also fails to persist `editing_dna`:
     ```python
     job = JobService().create_job({'title': 'Test', 'channel_profile_id': 'channel-1e24de3ab5'})
     # job['editing_dna'] raises KeyError
     ```

4. **Error Handling & Adversarial Edge Cases Tested**:
   - `GET /api/radar/channel-profiles/{non_existent}` -> HTTP 404.
   - `PUT /api/radar/channel-profiles/{non_existent}` -> HTTP 404.
   - `POST /api/radar/channel-profiles/{non_existent}/clone` -> HTTP 404.
   - `DELETE /api/radar/channel-profiles/{non_existent}` -> HTTP 404.
   - `POST /api/radar/channel-profiles` with non-dict -> HTTP 400.
   - `PUT /api/radar/channel-profiles/{id}` with non-dict -> HTTP 400.
   - `PUT /api/radar/channel-profiles/{id}` with payload `{'id': 'tampered'}` -> ID immutable, correctly preserved.
   - `PATCH /api/jobs/{non_existent}` -> HTTP 404.
   - `PATCH /api/jobs/{job_id}` with mismatched `job_id` or `selectedId` -> HTTP 400 ("Cross-job mutation rejected").
   - `PATCH /api/jobs/{job_id}` with `is_draft: True` or `draft_mutation: True` -> HTTP 400 ("Draft mutation side-effects rejected").

---

## 2. Logic Chain

1. **PROJECT.md Interface Contract stipulates**:
   "`POST /api/jobs`: creates a new project initialized from the assigned channel profile's locked DNA and creative brief."
2. **Current Implementation**:
   - `scripts/backfill_migration.py` backfilled the 4 historical jobs in `data/jobs/*/job.json`.
   - However, when any new job is created via `POST /api/jobs`, the server route executes legacy `app.py::create_job` which does not bind or persist `editing_dna` or `default_creative_brief`.
   - Even if `server.py` were routed to `job_service.create_job()`, `JobStore.create()` in `documentary/store.py` explicitly drops any payload keys not in its hardcoded template, so `editing_dna` and `default_creative_brief` are discarded and never written to `job.json`.
3. **Failure Impact**:
   Any new documentary project created by the AI Agent or manual user in Step 00 will lack `editing_dna` and `default_creative_brief`. Downstream milestones (M3 "Lock Approved Edit to Channel Profile" and M3 "Voice-Visual Sync") depend directly on `job["editing_dna"]` being present on active jobs.
4. **Verification Gap**:
   `tests/test_m1_backend_isolation_backfill.py` asserted storage validity only for pre-existing backfilled jobs (`test_jobs_storage_integrity`), completely omitting an integration test that creates a new job via `POST /api/jobs` and verifies that `editing_dna` and `default_creative_brief` are persisted in the returned JSON and saved to disk.

---

## 3. Findings

### [Critical] Finding 1: `POST /api/jobs` Does Not Initialize or Persist `editing_dna` and `default_creative_brief`

- **What**: Creating a new project via `POST /api/jobs` or `job_service.create_job()` fails to save `editing_dna` and `default_creative_brief` into the new job record.
- **Where**:
  - `server.py`: Missing route override for `POST /api/jobs`.
  - `services/job_service.py`: `create_job()` delegates to `self.store.create(job_data)` without ensuring `editing_dna` and `default_creative_brief` are retained.
  - `documentary/store.py`: `JobStore.create()` drops `editing_dna` and `default_creative_brief` when writing the initial `job.json`.
- **Why**: Violates PROJECT.md §Interface Contracts (`POST /api/jobs`: creates a new project initialized from assigned channel profile's locked DNA and creative brief) and Requirement R2. New projects will fail in Milestone 3 when reading `job["editing_dna"]`.
- **Suggestion**:
  1. In `server.py`: Add `POST /api/jobs` to `router` (and remove from filtered legacy routes if needed) calling `job_service.create_job(payload)`.
  2. In `services/job_service.py::create_job`:
     After calling `created = self.store.create(job_data)`, immediately persist `editing_dna` and `default_creative_brief` via `self.store.update(created["id"], {"editing_dna": job_data["editing_dna"], "default_creative_brief": job_data["default_creative_brief"], "creative_brief": job_data["creative_brief"]})` (or update `JobStore.create` to include them directly).
  3. In `tests/test_m1_backend_isolation_backfill.py`:
     Add `test_create_job_inherits_channel_profile_dna` that calls `client.post("/api/jobs", ...)` and verifies non-null `editing_dna`, `default_creative_brief`, and `channel_profile_snapshot` in response and in `job.json`.

---

### [Major] Finding 2: `job_service.create_job` Silently Swallows Non-Existent `channel_profile_id`

- **What**: When creating a job with an invalid or non-existent `channel_profile_id` (e.g., `"channel-fake-999"`), `job_service.create_job()` catches `KeyError` with `pass`, silently creating an unlinked job with default values instead of reporting an error.
- **Where**: `services/job_service.py` line 95 (`except KeyError: pass`).
- **Why**: Silent degradation makes debugging difficult for both frontend client and AI Agent, and can cause projects to silently lose their intended profile DNA without any error signal.
- **Suggestion**: Raise `ValueError(f"Hồ sơ kênh '{profile_id}' không tồn tại")` so the endpoint returns HTTP 400 Bad Request or HTTP 404 Not Found.

---

### [Minor] Finding 3: Legacy Unit Tests Contain Unrelated Outdated DOM String Assertions

- **What**: 2 tests in `tests/test_channel_profiles.py` and 2 tests in `tests/test_api.py` failed when running broader test suites.
- **Where**: `tests/test_channel_profiles.py:249`, `tests/test_channel_profiles.py:639`, `tests/test_api.py:796`, `tests/test_api.py:891`.
- **Why**: Legacy tests assert outdated HTML/JS strings (`chat-activity-timeline`, `tùy chọn nếu chưa có kênh`) in `static/index.html` and `static/app.js`.
- **Suggestion**: Informational only; these will be addressed when updating client UI in Milestone 2.

---

## 4. Verified Claims

- `scripts/backfill_migration.py` creates non-destructive backups in `data/backups/` → **Verified (PASS)**.
- All 4 channel profiles in `data/channel_profiles.json` contain non-null required fields → **Verified (PASS)**.
- All 4 existing jobs in `data/jobs/` contain non-null required fields → **Verified (PASS)**.
- `GET /api/radar/channel-profiles` returns all profiles sorted → **Verified (PASS)**.
- `GET /api/radar/channel-profiles/{id}` returns specific profile or 404 → **Verified (PASS)**.
- `POST /api/radar/channel-profiles` creates new profile with generated `channel-` ID and complete schema → **Verified (PASS)**.
- `POST /api/radar/channel-profiles/{id}/clone` clones profile with ` (Clone)` label and independent ID → **Verified (PASS)**.
- `PUT /api/radar/channel-profiles/{id}` updates in-place while preserving unmentioned fields → **Verified (PASS)**.
- `PATCH /api/jobs/{job_id}` strictly mutates only the target job → **Verified (PASS)**.
- `PATCH /api/jobs/{job_id}` rejects cross-job mutation attempts with HTTP 400 → **Verified (PASS)**.
- `PATCH /api/jobs/{job_id}` rejects draft mutation side-effects with HTTP 400 → **Verified (PASS)**.
- `POST /api/jobs` creates job with inherited `editing_dna` and `default_creative_brief` → **Refuted (FAIL: Finding 1)**.

---

## 5. Coverage Gaps

- **Integration test for `POST /api/jobs` contract**:
  `tests/test_m1_backend_isolation_backfill.py` only verifies pre-existing jobs, but has no test verifying that `POST /api/jobs` creates a new project with locked `editing_dna` and `default_creative_brief`.
  *Risk Level: HIGH*. *Recommendation: Worker must add `test_create_job_inherits_channel_profile_dna`*.

---

## 6. Unverified Items

- Client-side Step 0 UI form reset and Step 00 draft decoupling: Scoped to Milestone 2 (M2).

---

## 7. Challenge Summary (Adversarial Critic)

**Overall Risk Assessment**: **HIGH**  
The core persistence models for profiles and historical jobs were successfully backfilled, but new project creation is broken with respect to the `editing_dna` interface contract. Without fixing this in M1, all downstream features in M3 ("Lock Approved Edit") and M4 ("Channel Pre-Flight") that operate on active jobs will fail.

### Challenge 1: New Project DNA Disconnect
- **Assumption Challenged**: Upstream claimed that `services/job_service.py` provides job creation with automatic profile DNA inheritance.
- **Attack Scenario**: Send `POST /api/jobs` with `{"channel_profile_id": "channel-1e24de3ab5", "title": "New Test Project"}`. Inspect the returned job object and `data/jobs/{new_id}/job.json`.
- **Blast Radius**: `editing_dna` and `default_creative_brief` are completely missing. Any project created from this point forward will fail to edit according to channel profile DNA.
- **Mitigation**: Route `POST /api/jobs` in `server.py` to `job_service.create_job()`, ensure `JobStore` persists `editing_dna` and `default_creative_brief`, and add a regression test.

### Challenge 2: Invalid Profile ID Injection
- **Assumption Challenged**: System gracefully handles invalid profile IDs on job creation.
- **Attack Scenario**: Send `POST /api/jobs` with `{"channel_profile_id": "non-existent-channel-id"}`.
- **Blast Radius**: The system silently creates an unlinked project with fallback defaults, obscuring user error.
- **Mitigation**: Validate `profile_id` existence and return HTTP 400 / 404 if not found.

---

## 8. Stress Test Results

| Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|
| Non-existent profile GET | HTTP 404 | HTTP 404 | **PASS** |
| Non-existent profile PUT | HTTP 404 | HTTP 404 | **PASS** |
| Non-existent profile CLONE | HTTP 404 | HTTP 404 | **PASS** |
| Non-existent profile DELETE | HTTP 404 | HTTP 404 | **PASS** |
| Non-dict payload to profile POST/PUT | HTTP 400 | HTTP 400 | **PASS** |
| Profile PUT payload attempting ID overwrite | ID immutable | ID unchanged | **PASS** |
| Non-existent job PATCH | HTTP 404 | HTTP 404 | **PASS** |
| Job PATCH payload targeting mismatched ID | HTTP 400 | HTTP 400 | **PASS** |
| Job PATCH payload with `is_draft: True` | HTTP 400 | HTTP 400 | **PASS** |
| Create new job via `POST /api/jobs` with profile ID | Returns job with `editing_dna` & `default_creative_brief` | Returns job with `editing_dna: null/missing` | **FAIL (Finding 1)** |
| Create new job via `job_service.create_job()` directly | Saves `editing_dna` to `job.json` | `editing_dna` stripped by `JobStore.create` | **FAIL (Finding 1)** |

---

## 9. Conclusion

Milestone 1 has delivered solid work on the data backfill and profile management services, but it cannot be approved in its current state because **new job creation does not satisfy the PROJECT.md interface contract**: `POST /api/jobs` does not persist the assigned profile's `editing_dna` or `default_creative_brief`.

**Verdict**: **REQUEST_CHANGES**

---

## 10. Verification Method for Rework

Once the fixes are implemented by `worker_m1`:

1. **Verify `POST /api/jobs` DNA Inheritance in Server**:
   ```bash
   python -c "from fastapi.testclient import TestClient; from server import create_app; client = TestClient(create_app()); resp = client.post('/api/jobs', json={'title': 'Test DNA Lock', 'channel_profile_id': 'channel-1e24de3ab5', 'market': 'KR'}); assert resp.status_code == 200; data = resp.json(); assert data.get('editing_dna'), 'editing_dna must not be null'; assert data.get('default_creative_brief'), 'default_creative_brief must not be null'; assert data.get('visual_strategy') == 'hybrid'; client.delete('/api/jobs/' + data['id']); print('POST /api/jobs DNA inheritance verified!')"
   ```

2. **Verify JobStore Disk Persistence for New Jobs**:
   ```bash
   python -c "from services.job_service import JobService; js = JobService(); job = js.create_job({'title': 'Disk Verify', 'channel_profile_id': 'channel-e544a64b7c'}); stored = js.get_job(job['id']); assert stored.get('editing_dna'), 'editing_dna missing from disk'; assert stored.get('default_creative_brief'), 'default_creative_brief missing from disk'; js.delete_job(job['id']); print('JobStore persistence verified!')"
   ```

3. **Run Full Milestone 1 Automated Test Suite**:
   ```bash
   python -m pytest tests/test_m1_backend_isolation_backfill.py --basetemp=.pytest_tmp -v
   ```
   *Expected*: All tests pass (including new test for `POST /api/jobs` DNA inheritance).
