# Technical Investigation Report: Requirement R1 & AC1
**Smart Google Flow Profile Cache Cleanup & Complete Disk Removal on Account Deletion**

- **Date**: 2026-10-19T19:17:00Z
- **Author**: `explorer_survey_1`
- **Scope**: Requirement R1, AC1, and R4 (Non-Destructive Preservation)

---

## 1. Executive Summary

A comprehensive investigation of the Google Flow account management, caching, disk storage, and UI lifecycle was conducted across **Media Factory** (`vendor/media_factory/`) and **CofiDocumentary** (`B:\ALL_TOOLS\CofiDocumentary`).

### Key Findings
1. **Incomplete Disk Cleanup on Account Deletion**:
   In `vendor/media_factory/backend/app/providers/google.py` (`GoogleFlowAccountManager.remove(account_id)` lines 2096–2106), deleting an account removes the DB record, calls `login_worker.close_session(account_id)`, and deletes the encrypted secret session file. However, **it never deletes the Chromium profile folder on disk** (`data/media_factory/google-flow-profiles/{account_id}`), nor does it guarantee termination of background Chrome processes if the session was not currently in `_live_sessions`.
2. **Heavy Disk Waste & Orphan Accumulation**:
   - In `data/media_factory/google-flow-profiles/`, there are **7 profile directories consuming ~2.80 GB**.
   - Analysis of `cofi_studio.db` reveals **only 3 active registered accounts** (`210336272f514beda9c76b32aea6daf5`, `4371deaf80ef400b9a039a1a88b3f6dd`, `4bb65253fa694c29ad986dfaad904294`).
   - The remaining **4 directories** (`300ece367ac047f880764d1ca05469dc`, `87e40ab37f064ec799934ca4c29d512e`, `9e11b5a6bd1f40ff9cf44a39edaad36c`, `d64aad4f36854f8c8772a68f3cc808fa`) are **100% orphaned**, wasting **~710 MB**.
   - Furthermore, in the 3 active accounts, Chromium non-essential caches (`Default/Cache`, `Default/Code Cache`, `Default/Service Worker/ScriptCache`, `GrShaderCache`, etc.) account for **over 70% of each profile's size** (e.g. 632 MB of 804 MB in account `4371...`, and 690 MB of 1097 MB in account `2103...`), while essential session and cookie files take **less than 15 MB**.
   - In `data/secrets/google-flow/`, there are **10 orphan `.enc` session files** belonging to accounts long deleted.
3. **No Smart Cache Eviction Utility Currently Exists**:
   Neither `clean_profile_caches` nor `/clean-cache` API endpoints exist in the codebase.
4. **Preservation Status (R4)**:
   The running AI Visual job `20261019-185102-31983814` and existing SQLite databases (`data/radar.db`, `data/media_factory/cofi_studio.db`, `data/media_factory/media_factory.db`) are healthy, active, and must remain untouched.

---

## 2. Detailed Codebase Architecture & Code Examination

### 2.1 Current Implementation of Account Removal & Pruning

#### Location: `vendor/media_factory/backend/app/providers/google.py`
```python
# Lines 2096-2106:
def remove(self, account_id: str) -> bool:
    existing = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
    removed = self.db.delete_resource(ACCOUNT_RESOURCE_TYPE, account_id)
    if removed:
        if existing and existing.get('email'):
            self._mark_deleted_email(str(existing.get('email')))
        close_session = getattr(self.login_worker, 'close_session', None)
        if callable(close_session):
            close_session(account_id)
        self.secret_store.delete_google_session(account_id)
    return removed
```

#### Deficiencies Identified:
1. **No Profile Directory Deletion**:
   Neither `self.profile_root / account_id` nor `existing.get('profile_dir')` is ever unlinked or removed via `shutil.rmtree`.
2. **Process Termination Blind Spot**:
   `close_session(account_id)` checks `with self._live_sessions_lock: session = self._live_sessions.get(account_id)`. If the worker was restarted, or if Chrome was launched externally or lingered from a crashed session, `self._live_sessions.get(account_id)` is `None`. In that case, `close_session` does nothing! It fails to kill lingering `chrome.exe` processes holding locks on profile files.
   Instead, `BrowserLoginWorker._terminate_profile_processes(profile_dir)` (defined at line 640) can and should be called directly on the resolved `profile_dir`.
3. **Pruning Propagation**:
   In `check_all_accounts(prune_dead=True)` (lines 1996–2003):
   ```python
   if prune_dead:
       self.remove(acc_id)
       deleted.append({...})
   ```
   And `prune_dead_accounts()` (lines 2108–2110) delegates directly to `self.check_all_accounts(prune_dead=True)`.
   Therefore, upgrading `remove(account_id)` immediately fixes both individual deletion and bulk pruning!

---

## 3. Chromium Cache vs. Essential Session Anatomy

Through direct inspection of active profiles on disk (`data/media_factory/google-flow-profiles/210336272f514beda9c76b32aea6daf5`), the directory structure breaks down as follows:

### 3.1 Non-Essential Cache Subdirectories (Safe to Evict)
These directories store transient web assets, compiled bytecode, GPU shaders, crash reports, and speculative download blobs. Evicting them does NOT invalidate Google authentication or Flow sessions:
- `Default/Cache` & `Default/Cache/Cache_Data` (~334 MB)
- `Default/Code Cache` & `Default/Code Cache/js` (~297 MB)
- `Default/GPUCache` (~5.6 MB)
- `Default/DawnCache` & `Default/DawnWebGPUCache`
- `Default/GrShaderCache` & `Default/ShaderCache`
- `Default/Service Worker/CacheStorage`
- `Default/Service Worker/ScriptCache` (~58.2 MB)
- Root caches: `ShaderCache`, `GrShaderCache` (~10.5 MB), `GraphiteDawnCache`, `GPUPersistentCache/DawnGraphiteCache`
- Diagnostics & Metrics: `Crashpad`, `BrowserMetrics`
- Extensions update blobs & models: `component_crx_cache` (~37.2 MB), `extensions_crx_cache` (~48.7 MB), `optimization_guide_model_store` (~45.4 MB), `OnDeviceHeadSuggestModel` (~7.6 MB)

### 3.2 Essential Session Files (Strictly Preserved)
These files contain the account credentials, authentication cookies (`SID`, `SSID`, `HSID`, `__Secure-*`), local storage tokens, and browser state checked by `BrowserLoginWorker.has_reusable_profile(profile_dir)`:
- `Default/Cookies`
- `Default/Network/Cookies`
- `Default/Local Storage/` (contains LevelDB auth state)
- `Default/Session Storage/`
- `Default/IndexedDB/` (contains Flow project state & indexed client data)
- `Default/Preferences`
- `Local State` (at profile root; required by Chromium to initialize profile)

---

## 4. Disk Inspection & Orphan Inventory

### 4.1 Database State
Querying `data/media_factory/cofi_studio.db` (`local_resources WHERE resource_type = 'google_flow_account'`):
| Account ID | Email | Status | Profile Dir |
|---|---|---|---|
| `210336272f514beda9c76b32aea6daf5` | `koinguyenbk295@gmail.com` | `ready` | G-Labs profile |
| `4371deaf80ef400b9a039a1a88b3f6dd` | `cofinguyen295@gmail.com` | `ready` | G-Labs profile |
| `4bb65253fa694c29ad986dfaad904294` | `vitalinanovell581@gmail.com` | `ready` | G-Labs profile |

### 4.2 Profiles in `data/media_factory/google-flow-profiles/`
| Folder Name | Size | Status in DB | Notes |
|---|---|---|---|
| `210336272f514beda9c76b32aea6daf5` | 1097.86 MB | **Active** | Caches consume ~700 MB |
| `4371deaf80ef400b9a039a1a88b3f6dd` | 804.54 MB | **Active** | Caches consume ~630 MB |
| `4bb65253fa694c29ad986dfaad904294` | 176.37 MB | **Active** | Active account |
| `300ece367ac047f880764d1ca05469dc` | 178.69 MB | **ORPHAN** | No DB record! Safe to delete |
| `87e40ab37f064ec799934ca4c29d512e` | 178.97 MB | **ORPHAN** | No DB record! Safe to delete |
| `9e11b5a6bd1f40ff9cf44a39edaad36c` | 176.11 MB | **ORPHAN** | No DB record! Safe to delete |
| `d64aad4f36854f8c8772a68f3cc808fa` | 176.36 MB | **ORPHAN** | No DB record! Safe to delete |
| **Total** | **2,788.90 MB (~2.8 GB)** | **4 Orphans (710 MB)** | **Cache savings: ~1.4 GB** |

### 4.3 Secret Session Files in `data/secrets/google-flow/`
`KeyringSecretStore` maps `account_id` to `hashlib.sha256(account_id.encode('utf-8')).hexdigest() + '.enc'`.
- `data/media_factory/secrets/google-flow/`: Contains 3 `.enc` files matching the 3 active DB accounts.
- `data/secrets/google-flow/`: Contains 13 `.enc` files, of which **10 are orphans** (`11e593...`, `12f6e5...`, `620b1b...`, `70ff60...`, `75cac2...`, `778127...`, `7a4541...`, `a9622d...`, `e31c13...`, `f9fd88...`).

---

## 5. Required Implementation Plan for R1 & AC1

### 5.1 Media Factory Provider Layer (`vendor/media_factory/backend/app/providers/google.py`)

#### Robust Windows Directory Removal Helper:
```python
def _handle_remove_readonly(func, path, exc_info):
    import stat
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def _rmtree_robust(target: Path | str, retries: int = 4, delay: float = 0.15) -> bool:
    target_path = Path(target)
    if not target_path.exists():
        return True
    import stat
    for i in range(retries):
        try:
            for root, dirs, files in os.walk(str(target_path)):
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), stat.S_IWRITE)
                    except OSError:
                        pass
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), stat.S_IWRITE)
                    except OSError:
                        pass
            try:
                os.chmod(str(target_path), stat.S_IWRITE)
            except OSError:
                pass
            shutil.rmtree(target_path, onexc=_handle_remove_readonly)
            return True
        except TypeError:
            try:
                shutil.rmtree(target_path, onerror=_handle_remove_readonly)
                return True
            except Exception:
                pass
        except Exception:
            if i < retries - 1:
                time.sleep(delay * (i + 1))
    return not target_path.exists()
```

#### Update `remove(self, account_id: str) -> bool`:
1. Retrieve `existing = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)` and resolve `profile_dir = self.profile_dir_for_account(existing or account_id)`.
2. Close live session: `self.login_worker.close_session(account_id)`.
3. Terminate lingering processes bound to profile: `BrowserLoginWorker._terminate_profile_processes(profile_dir)`.
4. Delete secret session: `self.secret_store.delete_google_session(account_id)`.
5. Remove persistent profile folder on disk using `_rmtree_robust(profile_dir)`. Also check `self.profile_root / str(account_id)` and remove if separate.
6. Delete database record: `self.db.delete_resource(ACCOUNT_RESOURCE_TYPE, account_id)`.

#### Add `clean_profile_caches(self) -> dict[str, Any]`:
1. **Calculate Pre-clean Stats**: Measure size of all profile folders and secret directories.
2. **Evict Caches from Active Profiles**:
   For each registered account, inspect `profile_dir`. Evict all listed cache directories while strictly skipping essential session files.
3. **Detect & Delete Orphan Profile Directories**:
   Compare directories in `self.profile_root` against registered account IDs and resolved profile paths. Terminate processes on orphan directories and remove via `_rmtree_robust`.
4. **Detect & Delete Orphan Secret Session Files**:
   Compare `.enc` files in `self.secret_store._storage_dir` (and `data/secrets/google-flow/`) against `sha256(acc_id)`. Remove any non-matching `.enc` files.
5. **Return Structured Metrics**:
   ```python
   {
       "ok": True,
       "total_size_mb": round(total_size_mb, 2),
       "freed_mb": round(freed_mb, 2),
       "orphan_profiles_removed": orphan_profiles_count,
       "orphan_sessions_removed": orphan_sessions_count,
       "cleaned_profiles_count": cleaned_profiles_count,
   }
   ```
6. **Automatic Lightweight Hook in `close_session`**:
   In `BrowserLoginWorker.close_session`, after processes are terminated, trigger a lightweight cache purge on `session.profile_dir`.

### 5.2 Media Factory Route Layer (`vendor/media_factory/backend/app/routes/providers.py` & `main.py`)
- In `routes/providers.py`:
  Add `@router.post('/accounts/clean-cache')` and `@router.post('/clean-cache')`:
  ```python
  @router.post('/accounts/clean-cache')
  def google_accounts_clean_cache(request: Request):
      manager = get_account_manager(request)
      if hasattr(manager, 'clean_profile_caches'):
          return manager.clean_profile_caches()
      return {'ok': True, 'total_size_mb': 0.0, 'freed_mb': 0.0, 'orphan_profiles_removed': 0, 'cleaned_profiles_count': 0}
  ```
- In `main.py`:
  Register route `/api/v1/accounts/google-flow/clean-cache` pointing to the same handler to satisfy both endpoint conventions.

### 5.3 CofiDocumentary Embed & Service Integration
- In `documentary/cofi_studio_embed.py`:
  Implement `clean_profile_caches()`:
  Sends `POST /api/providers/google/accounts/clean-cache` to Media Factory embedded server.
  If server is not running, falls back to direct execution via `GoogleFlowAccountManager`.
- In `documentary/service.py`:
  Add `ai_visual_runtime_clean_profile_caches()` delegating to `cofi_studio_embed_manager.clean_profile_caches()`.
- In `app.py`:
  Add:
  - `@api.post("/api/cofi-studio/runtime/accounts/clean-cache")`
  - `@api.post("/api/v1/accounts/google-flow/clean-cache")`

### 5.4 CofiDocumentary Frontend UI (`static/app.js` & `static/index.html`)
- In `static/app.js` -> `renderFlowAccountsDialogContent(job, runtime)`:
  Inside `.flow-popup-actions`:
  ```html
  <button type="button" class="ghost compact" id="popupCleanCacheBtn">⚡ Dọn Cache Thông Minh</button>
  ```
- Implement `runCleanFlowAccountsCache(job, triggerBtn)`:
  Disables trigger button, sets label `⏳ Đang dọn cache…`, calls `api("/api/cofi-studio/runtime/accounts/clean-cache", { method: "POST" })`.
  Shows user toast:
  `"Đã dọn dẹp ${res.freed_mb} MB cache · Xóa ${res.orphan_profiles_removed} profile rác · Tối ưu ${res.cleaned_profiles_count} tài khoản. Dung lượng hiện tại: ${res.total_size_mb} MB."`
  Refreshes runtime snapshot.

---

## 6. Verification and Test Suite Strategy

Tests should be written using `pytest` (executed via `python -m pytest <test_file>`):
1. **Unit Test for Deletion**:
   Create a test account with mock profile directory containing files, read-only files, and secret session file. Call `manager.remove(account_id)`. Assert:
   - Resource deleted from database.
   - Secret file deleted.
   - Profile folder deleted completely from disk (`assert not profile_dir.exists()`).
2. **Unit Test for Smart Cache Eviction & Preservation**:
   Create active account with essential session files (`Default/Cookies`, `Default/Network/Cookies`, `Default/Local Storage/`, `Local State`) AND cache subdirectories (`Default/Cache/`, `Default/Code Cache/`, `Default/GPUCache/`, `Crashpad/`). Also create an orphan profile directory not in DB.
   Call `manager.clean_profile_caches()`. Assert:
   - Essential session files exist and are untouched.
   - Cache subdirectories are removed.
   - Orphan profile directory is completely deleted.
   - Returned dict contains `freed_mb > 0`, `orphan_profiles_removed == 1`, `cleaned_profiles_count == 1`.
3. **Integration Test for Endpoints**:
   Test `POST /api/cofi-studio/runtime/accounts/clean-cache` and `POST /api/v1/accounts/google-flow/clean-cache`.
4. **UI Contract Test**:
   Assert `"popupCleanCacheBtn"` and `"/api/cofi-studio/runtime/accounts/clean-cache"` exist in `static/app.js`.
