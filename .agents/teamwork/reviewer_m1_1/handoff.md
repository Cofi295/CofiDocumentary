# Review & Adversarial Challenge Report — Milestone M1

**Milestone**: M1 (Requirement R1 & AC1: Smart Google Flow Browser Profile Cache Cleanup & Complete Disk Removal on Account Deletion)
**Agent**: `reviewer_m1_1` (roles: reviewer, critic)
**Working Directory**: `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\reviewer_m1_1`
**Parent**: `orchestrator_2` (`a13450b0-84a5-4e72-ae6f-8fd9f0ed17c4`)
**Verdict**: **APPROVE**

---

## 1. Observation

1. **Codebase Inspection — Complete Account Deletion on Disk**:
   - In `vendor/media_factory/backend/app/providers/google.py` lines 2232–2276, `remove(account_id)` was inspected:
     - Identifies both registered custom `profile_dir` and default `self.profile_root / str(account_id)`.
     - Calls `self.login_worker.close_session(account_id)` to shut down live session queues.
     - Calls `BrowserLoginWorker._terminate_profile_processes(p_dir)` (using Windows PowerShell CIM query matching `chrome.exe` with command line containing `p_dir` and `taskkill /PID <pid> /T /F`).
     - Deletes account resource from SQLite database via `self.db.delete_resource(...)`.
     - Deletes encrypted secret session file via `self.secret_store.delete_google_session(account_id)`.
     - Recursively deletes the profile directory on disk using `_rmtree_robust(p_dir)` with `stat.S_IWRITE` permission adjustments, retry backoff, and `onexc`/`onerror` handling.
   - In lines 2417–2420, `prune_dead_accounts()` delegates to `self.check_all_accounts(prune_dead=True)`, which invokes `self.remove(acc_id)` for dead/expired accounts, ensuring complete disk profile removal on prune.

2. **Codebase Inspection — Smart Cache Eviction and Orphan Purging**:
   - In `vendor/media_factory/backend/app/providers/google.py` lines 1238–1289, `_evict_profile_cache_subdirs(profile_dir)` purges 20 non-essential Chromium cache directories (`Default/Cache`, `Default/Code Cache`, `Default/GPUCache`, `Default/DawnCache`, `Default/Service Worker/CacheStorage`, `ShaderCache`, `Crashpad`, `BrowserMetrics`, `component_crx_cache`, etc.).
   - Explicit safeguard in line 1267–1275:
     ```python
     protected_lower = {
         "cookies", "network/cookies", "local storage", "session storage",
         "indexeddb", "preferences", "local state"
     }
     ```
     Guarantees authentication, cookies, local storage, and profile preferences are never touched.
   - In lines 2278–2415, `clean_profile_caches()`:
     - Iterates registered accounts and clears non-essential cache subdirs.
     - Scans `self.profile_root` for orphan folders whose folder names and resolved paths are not registered in DB, terminates any lingering processes bound to them, and deletes them via `_rmtree_robust`.
     - Scans `secrets/google-flow/` for orphan `.enc` files whose SHA-256 hash does not match any registered account in DB, and unlinks them.
     - Computes pre- and post-cleanup disk sizes and returns structured metrics:
       `{'ok': True, 'status': 'success', 'total_size_mb': ..., 'freed_mb': ..., 'orphan_profiles_removed': ..., 'orphan_sessions_removed': ..., 'cleaned_profiles_count': ...}`.

3. **Codebase Inspection — Endpoints & UI Integration**:
   - In `vendor/media_factory/backend/app/routes/providers.py` lines 219–242: exposed `POST /api/providers/google/accounts/clean-cache` and `POST /clean-cache`.
   - In `vendor/media_factory/backend/app/main.py` line 133: exposed alias `POST /api/v1/accounts/google-flow/clean-cache`.
   - In `documentary/cofi_studio_embed.py` lines 427–466: implemented `clean_profile_caches()` with HTTP proxy to Media Factory and direct fallback to `GoogleFlowAccountManager`.
   - In `documentary/service.py` lines 1153–1155: implemented `ai_visual_runtime_clean_profile_caches()`.
   - In `app.py` lines 491–501: exposed `POST /api/cofi-studio/runtime/accounts/clean-cache` and `POST /api/v1/accounts/google-flow/clean-cache`.
   - In `static/app.js` lines 454–483 and 521: added `<button type="button" class="ghost compact" id="popupCleanCacheBtn">⚡ Dọn Cache Thông Minh</button>` to `renderFlowAccountsDialogContent`, and wired `runCleanFlowAccountsCache(job, triggerBtn)` with loading states, error handling, toast notification, and silent runtime refresh. `node -c static/app.js` passed with code 0.

4. **Independent Automated Test Execution**:
   - Command: `python -m pytest tests/test_google_flow_cache_and_cleanup.py -v`
     Result:
     ```
     tests/test_google_flow_cache_and_cleanup.py::test_rmtree_robust_handles_read_only_files PASSED
     tests/test_google_flow_cache_and_cleanup.py::test_account_deletion_removes_db_record_secret_session_and_disk_profile PASSED
     tests/test_google_flow_cache_and_cleanup.py::test_prune_dead_accounts_completely_removes_disk_profile PASSED
     tests/test_google_flow_cache_and_cleanup.py::test_cache_cleanup_evicts_cache_and_orphans_while_preserving_session_files PASSED
     tests/test_google_flow_cache_and_cleanup.py::test_media_factory_clean_cache_api_endpoints PASSED
     tests/test_google_flow_cache_and_cleanup.py::test_cofi_documentary_clean_cache_api_endpoints PASSED
     tests/test_google_flow_cache_and_cleanup.py::test_frontend_ui_contract_in_static_app_js PASSED
     ======================= 7 passed, 448 warnings in 7.42s =======================
     ```
   - Command: `python -m pytest tests/test_google_flow_session_lifecycle.py -v`
     Result:
     ```
     ============================== 9 passed in 8.49s ==============================
     ```

5. **Live Verification Against Real Project State & R4 Non-Destructive Preservation**:
   - Calling `POST /api/cofi-studio/runtime/accounts/clean-cache` returned:
     `{'ok': True, 'status': 'success', 'total_size_mb': 472.03, 'freed_mb': 0.0, 'orphan_profiles_removed': 0, 'orphan_sessions_removed': 0, 'cleaned_profiles_count': 3}`.
   - Calling `GET /api/jobs/20261019-185102-31983814/ai-visual-runtime` returned HTTP 200 with all 3 registered accounts fully healthy:
     - `210336272f514beda9c76b32aea6daf5` (`koinguyenbk295@gmail.com`): status `ready`, tier `ultra`, credits `598`.
     - `4371deaf80ef400b9a039a1a88b3f6dd` (`cofinguyen295@gmail.com`): status `ready`, tier `pro`, credits `1010`.
     - `4bb65253fa694c29ad986dfaad904294` (`vitalinanovell581@gmail.com`): status `ready`, tier `free`, credits `50`.
   - Verified active job `20261019-185102-31983814` (`completed`, 316/316 targets) and database `data/radar.db` are 100% intact.

---

## 2. Logic Chain

1. From Observation 1, the code directly fulfills Requirement R1: removing an account or pruning dead accounts closes sessions, terminates Chrome processes holding the profile lock, deletes the secret session file, and completely deletes the directory on disk.
2. From Observation 2, `_evict_profile_cache_subdirs` targets only volatile Chromium caches while strictly guarding `Cookies`, `Local Storage`, `IndexedDB`, `Preferences`, and `Local State`. Orphan profile directories and orphan encrypted sessions are accurately identified and cleaned without affecting registered accounts.
3. From Observation 3, the entire stack—Media Factory backend, CofiDocumentary embed bridge, service layer, FastAPI routes, and vanilla JS UI—is properly wired with appropriate error handling and user feedback.
4. From Observation 4, all 7 newly created tests and all 9 legacy lifecycle tests pass cleanly without errors, demonstrating zero regressions.
5. From Observation 5, live execution of the cleanup endpoint against actual production data safely reports accurate profile sizes and leaves all real accounts and active jobs fully operational, fulfilling Requirement R4.
6. No integrity violations (such as hardcoded test results, facade mocks, or bypassed requirements) were detected.

---

## 3. Caveats

- **Active Chrome In-Flight Locks**: As documented by worker_m1, if an account's Chrome browser is actively writing to a specific cache block at the exact moment cleanup runs, `_rmtree_robust` retries up to 5 times and safely skips permanently locked files without breaking the cleanup routine or aborting the HTTP request. This is the correct Windows filesystem design.
- No other caveats.

---

## 4. Conclusion

The implementation of Milestone M1 (Requirement R1, AC1, and R4) is robust, strictly compliant with specification, safe for Windows file-locking semantics, preserves active accounts/jobs, and is verified by comprehensive automated tests.

**Verdict**: **APPROVE**

---

## 5. Verification Method

1. Run automated test suite:
   ```powershell
   python -m pytest tests/test_google_flow_cache_and_cleanup.py -v
   python -m pytest tests/test_google_flow_session_lifecycle.py -v
   ```
2. Verify live clean-cache endpoint:
   ```powershell
   python -c "import server; from fastapi.testclient import TestClient; client = TestClient(server.create_app()); res = client.post('/api/cofi-studio/runtime/accounts/clean-cache'); assert res.status_code == 200 and res.json()['ok'] is True; print('Clean cache verified:', res.json())"
   ```
3. Verify preserved accounts and job:
   ```powershell
   python -c "import sqlite3, json; conn = sqlite3.connect('data/media_factory/cofi_studio.db'); rows = conn.execute('SELECT id FROM local_resources WHERE resource_type = ?', ('google_flow_account',)).fetchall(); assert len(rows) == 3; print('Active accounts preserved:', len(rows))"
   ```
