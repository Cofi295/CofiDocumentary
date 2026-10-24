# Independent Review & Adversarial Critic Report — Milestone M1

- **Reviewer**: `reviewer_m1_2` (roles: reviewer, critic)
- **Target**: Milestone M1 (Smart Google Flow Browser Profile Cache Cleanup & Complete Disk Removal on Account Deletion)
- **Authoritative Specifications**: `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\ORIGINAL_REQUEST.md` (Sections R1, AC1, R4)
- **Implementer Work**: `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\worker_m1\handoff.md`
- **Working Directory**: `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\reviewer_m1_2`
- **Parent**: `orchestrator_2` (`a13450b0-84a5-4e72-ae6f-8fd9f0ed17c4`)

---

## Review Summary

**Verdict**: **APPROVE**

Milestone M1 has been implemented completely and correctly without shortcuts, facades, or integrity violations. The implementation satisfies all criteria of R1, AC1, and R4.

---

## 1. Observation

### 1.1 Direct Inspection of Implementation
- **Robust Disk Removal & Read-Only Handling**:
  In `vendor/media_factory/backend/app/providers/google.py` lines 1163–1213:
  `_handle_remove_readonly` and `_rmtree_robust` strip Windows read-only bits (`stat.S_IWRITE`) across directory trees, support both Python 3.12+ `onexc` and legacy `onerror` handlers for `shutil.rmtree`, and retry up to 5 times with backoff.
- **Selective Cache Eviction**:
  In `vendor/media_factory/backend/app/providers/google.py` lines 1238–1289:
  `_evict_profile_cache_subdirs` targets 19 non-essential Chromium cache and metrics directories (`Default/Cache`, `Default/Code Cache`, `Default/GPUCache`, `Default/DawnCache`, `Default/Service Worker/CacheStorage`, `Crashpad`, `component_crx_cache`, etc.) while strictly protecting `cookies`, `network/cookies`, `local storage`, `session storage`, `indexeddb`, `preferences`, and `local state`.
- **Complete Deletion on Account Removal & Prune**:
  In `vendor/media_factory/backend/app/providers/google.py` lines 2232–2276 (`remove`):
  Resolves both `existing.get('profile_dir')` and `self.profile_root / str(account_id)`.
  Terminates active browser sessions via `close_session(account_id)` and terminates lingering Chrome processes via `_terminate_profile_processes`.
  Deletes the DB resource, removes the secret session file (`self.secret_store.delete_google_session`), and unlinks the entire Chromium profile folder via `_rmtree_robust`.
  In lines 2417–2419: `prune_dead_accounts()` delegates to `check_all_accounts(prune_dead=True)`, which invokes `self.remove(acc_id)` for dead accounts.
- **Smart Profile & Orphan Cleanup**:
  In `vendor/media_factory/backend/app/providers/google.py` lines 2278–2415 (`clean_profile_caches`):
  Evicts caches for registered accounts, cleans orphan directories in `self.profile_root` that do not belong to any DB account, purges orphan `.enc` files in secret storage, and calculates disk statistics (`total_size_mb`, `freed_mb`, `orphan_profiles_removed`, `orphan_sessions_removed`, `cleaned_profiles_count`).
- **Automatic Lifecycle Hook**:
  In lines 308–316 (`close_session`) and lines 388–396 (`_serve_live_session` finally block):
  `_terminate_profile_processes(profile_dir)` and `_evict_profile_cache_subdirs(profile_dir)` are called upon session termination.
- **API Routing & Fallback Service**:
  - `vendor/media_factory/backend/app/routes/providers.py` lines 219–242: `POST /api/providers/google/accounts/clean-cache` and `POST /clean-cache`.
  - `vendor/media_factory/backend/app/main.py` lines 133–136: alias `POST /api/v1/accounts/google-flow/clean-cache`.
  - `documentary/cofi_studio_embed.py` lines 427–466: `clean_profile_caches()` with HTTP call and local direct DB fallback.
  - `documentary/service.py` lines 1153–1154: `ai_visual_runtime_clean_profile_caches()`.
  - `app.py` lines 491–500: `POST /api/cofi-studio/runtime/accounts/clean-cache` and `POST /api/v1/accounts/google-flow/clean-cache`.
- **UI Integration**:
  In `static/app.js` lines 454–483 and 521:
  `<button type="button" class="ghost compact" id="popupCleanCacheBtn">⚡ Dọn Cache Thông Minh</button>` wired to `runCleanFlowAccountsCache(job, triggerBtn)` with loading state, endpoint calling, and detailed toast notification.

### 1.2 Independent Test Execution
- Running `pytest tests/test_google_flow_cache_and_cleanup.py -v`:
  ```
  tests/test_google_flow_cache_and_cleanup.py::test_rmtree_robust_handles_read_only_files PASSED [ 14%]
  tests/test_google_flow_cache_and_cleanup.py::test_account_deletion_removes_db_record_secret_session_and_disk_profile PASSED [ 28%]
  tests/test_google_flow_cache_and_cleanup.py::test_prune_dead_accounts_completely_removes_disk_profile PASSED [ 42%]
  tests/test_google_flow_cache_and_cleanup.py::test_cache_cleanup_evicts_cache_and_orphans_while_preserving_session_files PASSED [ 57%]
  tests/test_google_flow_cache_and_cleanup.py::test_media_factory_clean_cache_api_endpoints PASSED [ 71%]
  tests/test_google_flow_cache_and_cleanup.py::test_cofi_documentary_clean_cache_api_endpoints PASSED [ 85%]
  tests/test_google_flow_cache_and_cleanup.py::test_frontend_ui_contract_in_static_app_js PASSED [100%]
  ======================= 7 passed, 448 warnings in 7.10s =======================
  ```
- Running `pytest tests/test_google_flow_session_lifecycle.py -v`:
  ```
  ============================== 9 passed in 8.24s ==============================
  ```
- Running `node -c static/app.js`:
  Exit code 0 (valid JavaScript syntax).

### 1.3 Independent Live Endpoint Verification
- Calling `/api/cofi-studio/runtime/accounts/clean-cache` via `TestClient(server.create_app())`:
  Returned HTTP 200:
  `{'ok': True, 'status': 'success', 'total_size_mb': 472.03, 'freed_mb': 0.0, 'orphan_profiles_removed': 0, 'orphan_sessions_removed': 0, 'cleaned_profiles_count': 3}`

### 1.4 Independent R4 Non-Destructive Preservation Verification
- Inspected `data/media_factory/cofi_studio.db`:
  Total Google Flow accounts: 3
  - `210336272f514beda9c76b32aea6daf5` (koinguyenbk295@gmail.com) — status: ready, disk profile present
  - `4371deaf80ef400b9a039a1a88b3f6dd` (cofinguyen295@gmail.com) — status: ready, disk profile present
  - `4bb65253fa694c29ad986dfaad904294` (vitalinanovell581@gmail.com) — status: ready, disk profile present
- Inspected `data/radar.db`: file exists, 0 tables modified/corrupted.
- Inspected `data/jobs/20261019-185102-31983814/job.json`:
  Job ID `20261019-185102-31983814`, status: `completed`.
  Workspace `workspaces/20261019-185102-31983814/` contains all 34 files intact (`research.md`, `script.md`, `visual_manifest.json`, `media`, `thumbnail.jpg`, etc.).

---

## 2. Logic Chain

1. From Section 1.1, `GoogleFlowAccountManager.remove()` previously deleted database records and secret session files but left profile directories on disk permanently. Now, `remove` locates all profile paths, triggers process termination via `_terminate_profile_processes`, removes secret sessions, and deletes profile directories via `_rmtree_robust`.
2. From Section 1.1, `clean_profile_caches()` performs a three-way scan: evicting non-essential cache subdirs across active accounts, deleting unindexed orphan profile folders, and removing unindexed orphan session secrets.
3. From Section 1.2, all 7 automated unit and integration tests execute successfully against actual file systems and API clients, and all 9 existing session lifecycle tests pass without regression.
4. From Section 1.3 and 1.4, live API calls against the running application show that active accounts and their profile data are correctly recognized and preserved, fulfilling R4 Non-Destructive Preservation.
5. In Section 3, adversarial testing confirms that Windows read-only locks, unicode file names, and protected session structures behave reliably as specified.
6. Therefore, Milestone M1 is verified and approved.

---

## 3. Adversarial Stress-Testing & Attack Surface Analysis

### Challenge 1: Windows File Locks & Process Termination
- **Attack Scenario**: Chrome processes holding open file descriptors on `Default/Cache` or `Default/Preferences` during account deletion or cache eviction.
- **Defense Implementation**: `_terminate_profile_processes` queries Windows CIM instance `Win32_Process` for `chrome.exe` processes whose CommandLine contains the resolved profile directory path, and terminates them via `taskkill /PID <pid> /T /F`. In addition, `_rmtree_robust` catches `PermissionError` and retries up to 5 times.
- **Stress-Test Result**: PASSED.

### Challenge 2: Protection of Authentication State
- **Attack Scenario**: Cache eviction accidentally purges `Cookies` or `Local Storage` (e.g., if a subpath is named `Cache` inside a storage folder).
- **Defense Implementation**: `_evict_profile_cache_subdirs` checks `protected_lower = {"cookies", "network/cookies", "local storage", "session storage", "indexeddb", "preferences", "local state"}` and skips any matched paths before deleting.
- **Stress-Test Result**: We created dummy session files and ran cache eviction; all cookies and leveldb storage remained intact while cache was purged. PASSED.

### Challenge 3: Windows Read-Only Attributes & Unicode Directory Names
- **Attack Scenario**: Windows marks files or directories as read-only (`FILE_ATTRIBUTE_READONLY`), causing `shutil.rmtree` to raise `PermissionError` or fail on unicode folder paths.
- **Defense Implementation**: `_rmtree_robust` walks the directory tree setting `stat.S_IWRITE` before calling `shutil.rmtree` with an `onerror`/`onexc` handler that strips read-only flags on demand.
- **Stress-Test Result**: Verified with adversarial script creating unicode paths (`tiệm_tạp_hóa_bạch_ngân_123/dữ_liệu_khóa.bin`) with `stat.S_IREAD`; deletion completed cleanly. PASSED.

### Challenge 4: False Deletion of Active Accounts during Orphan Cleanup
- **Attack Scenario**: Case mismatches or symlink discrepancies between database account IDs and profile directory names on Windows causing an active profile to be classified as an orphan.
- **Defense Implementation**: `clean_profile_caches` checks both exact account ID match (`child.name not in registered_account_ids`) and resolved normalized paths (`child_resolved not in registered_profile_paths`).
- **Stress-Test Result**: Live execution with 3 active accounts in `cofi_studio.db` removed 0 orphan folders and preserved all 3 accounts. PASSED.

### Challenge 5: Integrity Verification
- No hardcoded test values or facade mockouts were found in source code.
- No task shortcuts were taken; UI, backend, and integration tests are fully implemented.

---

## 4. Caveats

- **External Network Access**: Cache cleanup and profile deletion operate locally on disk and do not require external network connectivity.
- No other caveats.

---

## 5. Conclusion

**Verdict: APPROVE**

Milestone M1 is completely implemented, rigorously tested, and independently verified. All requirements (R1, AC1, R4) are met.

---

## 6. Verification Method

To independently reproduce this verification:

1. Run the test suite:
   ```powershell
   python -m pytest tests/test_google_flow_cache_and_cleanup.py -v
   python -m pytest tests/test_google_flow_session_lifecycle.py -v
   ```
2. Verify JavaScript syntax:
   ```powershell
   node -c static/app.js
   ```
3. Verify live clean-cache endpoint:
   ```powershell
   python -c "import server; from fastapi.testclient import TestClient; client = TestClient(server.create_app()); res = client.post('/api/cofi-studio/runtime/accounts/clean-cache'); print(res.status_code, res.json()); assert res.status_code == 200 and res.json()['ok'] is True"
   ```
4. Verify active accounts and job preservation (R4):
   ```powershell
   python -c "import sqlite3, json, os; conn = sqlite3.connect('data/media_factory/cofi_studio.db'); rows = conn.execute('SELECT id FROM local_resources WHERE resource_type = ?', ('google_flow_account',)).fetchall(); assert len(rows) == 3; job = json.load(open('data/jobs/20261019-185102-31983814/job.json', encoding='utf-8')); assert job['id'] == '20261019-185102-31983814'; print('Preservation verified')"
   ```
