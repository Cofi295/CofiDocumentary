# Handoff Report — Challenger M1.1

**Mission**: Adversarially challenge and stress-test the Google Flow cleanup implementation (R1 & AC1, R4).
**Agent**: `challenger_m1_1` (roles: critic, specialist)
**Working Directory**: `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\challenger_m1_1`
**Parent**: `orchestrator_2` (`a13450b0-84a5-4e72-ae6f-8fd9f0ed17c4`)
**Verdict**: **FAIL** (Vulnerabilities found under Windows read-only file handling and empty account ID edge cases, with reproducible empirical tests and exact remediation provided below)

---

## 1. Observation

1. **Adversarial Pytest Execution Results**:
   Running `python -m pytest tests/test_google_flow_adversarial_m1.py -v`:
   ```
   tests/test_google_flow_adversarial_m1.py::test_adversarial_deletion_with_readonly_deep_hierarchies_and_special_chars PASSED [ 14%]
   tests/test_google_flow_adversarial_m1.py::test_adversarial_cache_cleanup_with_unexpected_subdirs_and_corrupt_files FAILED [ 28%]
   tests/test_google_flow_adversarial_m1.py::test_adversarial_absolute_protection_of_critical_session_and_credential_files PASSED [ 42%]
   tests/test_google_flow_adversarial_m1.py::test_adversarial_nonexistent_and_orphan_profiles_and_missing_roots FAILED [ 57%]
   tests/test_google_flow_adversarial_m1.py::test_adversarial_active_accounts_never_deleted_by_cache_cleaning_or_prune PASSED [ 71%]
   tests/test_google_flow_adversarial_m1.py::test_adversarial_rapid_sequential_clean_cache_api PASSED [ 85%]
   tests/test_google_flow_adversarial_m1.py::test_adversarial_empty_account_id_does_not_target_profile_root PASSED [100%]
   =========================== 2 failed, 5 passed in 11.77s ===========================
   ```

2. **Verbatim Failure 1 — Standalone Cache Files with Read-Only Attribute Left Unremoved**:
   In `test_adversarial_cache_cleanup_with_unexpected_subdirs_and_corrupt_files`:
   ```
   AssertionError: BUG: Standalone cache file with stat.S_IREAD was not removed by _evict_profile_cache_subdirs! target_sub.unlink() raised PermissionError and was swallowed by except OSError.
   assert not True
    +  where True = exists()
    +    where exists = WindowsPath('.../Crashpad').exists
   ```
   Observed in `vendor/media_factory/backend/app/providers/google.py` lines 1281–1288:
   ```python
   elif target_sub.is_file():
       try:
           f_size = target_sub.stat().st_size
           target_sub.unlink(missing_ok=True)
           freed += f_size
       except OSError:
           pass
   ```
   When `target_sub` is a standalone file marked read-only on Windows (`stat.S_IREAD`), `target_sub.unlink()` throws `PermissionError: [WinError 5] Access is denied`. This is swallowed by `except OSError: pass`, leaving the cache file permanently on disk.

3. **Verbatim Failure 2 — Orphan Session Files with Read-Only Attribute Left Unremoved**:
   In `test_adversarial_nonexistent_and_orphan_profiles_and_missing_roots`:
   ```
   AssertionError: BUG: Orphan session file with stat.S_IREAD was not removed by clean_profile_caches! enc_file.unlink() raised PermissionError and was swallowed by except OSError.
   assert not True
    +  where True = exists()
    +    where exists = WindowsPath('.../adv_orphan_secrets/a134f112a37dab9092b56b2d73c2082f7f266cab9f1787cd8ac4ce22a8f9c2a3.enc').exists
   ```
   Observed in `vendor/media_factory/backend/app/providers/google.py` lines 2381–2389:
   ```python
   for enc_file in list(s_dir.glob('*.enc')):
       if enc_file.name not in registered_session_hashes:
           try:
               f_size = enc_file.stat().st_size
               enc_file.unlink(missing_ok=True)
               orphan_sessions_removed += 1
               freed_bytes += f_size
           except OSError:
               pass
   ```
   When an orphan `.enc` session file has `stat.S_IREAD`, `enc_file.unlink()` raises `PermissionError` [WinError 5] and is silently swallowed by `except OSError: pass`, abandoning the orphan session file on disk.

4. **Verbatim Failure 3 — Unhandled PermissionError in Secret Store Session Deletion**:
   Observed in `vendor/media_factory/backend/app/secrets.py` lines 131–136:
   ```python
   def delete_google_session(self, account_id: str) -> None:
       session_path = self._session_path(account_id)
       try:
           session_path.unlink()
       except FileNotFoundError:
           pass
   ```
   Empirical test command:
   ```bash
   python -c "import tempfile, os, stat; from vendor.media_factory.backend.app.secrets import KeyringSecretStore; t = tempfile.mkdtemp(); s = KeyringSecretStore(storage_dir=t); p = s._session_path('test'); p.write_bytes(b'x'); os.chmod(str(p), stat.S_IREAD); s.delete_google_session('test')"
   ```
   Output:
   ```
   PermissionError: [WinError 5] Access is denied: '.../test.enc'
   ```
   If a session file has read-only permissions on Windows, `delete_google_session` crashes with `PermissionError`. In `GoogleFlowAccountManager.remove(account_id)`, line 2267 `except Exception: pass` suppresses the crash, but the secret file is abandoned on disk.

5. **Safety Observation — Path Resolution with Empty Account ID**:
   In `vendor/media_factory/backend/app/providers/google.py` lines 2239 and 2297:
   ```python
   std_p = self.profile_root / str(account_id)
   ```
   In Python `Path('C:/profiles') / ""` evaluates to `Path('C:/profiles')` (identical path). If `account_id` is empty string or whitespace, `std_p` evaluates to `self.profile_root`. While `remove("")` currently returns `False` if not in DB, in `clean_profile_caches()`, an account with an empty ID in DB causes `self.profile_root` to be passed into `_evict_profile_cache_subdirs(self.profile_root)`.

6. **Active Accounts and Job State (R4 Non-Destructive Preservation)**:
   Verification command:
   ```bash
   python -c "import sqlite3, json; conn = sqlite3.connect('data/media_factory/cofi_studio.db'); rows = conn.execute('SELECT id, payload FROM local_resources WHERE resource_type = ?', ('google_flow_account',)).fetchall(); print('Active count:', len(rows)); assert len(rows) == 3; job = json.load(open('data/jobs/20261019-185102-31983814/job.json', encoding='utf-8')); assert job.get('status') == 'completed'; print('Job OK:', job.get('id'))"
   ```
   Output:
   ```
   Active count: 3
   Job OK: 20261019-185102-31983814
   ```
   All 3 production accounts and the active job remain 100% intact.

---

## 2. Logic Chain

1. Requirement R1 and AC1 mandate:
   *"Completely remove the account's persistent Chromium profile folder on disk ... with retry/read-only file handling on Windows (`shutil.rmtree(..., onerror=...)`)."*
   *"Detects and deletes orphan profile folders ... and orphan session files ... whose account IDs no longer exist in the database."*
2. While `worker_m1` implemented `_rmtree_robust` for directories (handling `stat.S_IWRITE` and retry loops), when handling individual files in `_evict_profile_cache_subdirs` (line 1284), `clean_profile_caches` (line 2385), and `KeyringSecretStore.delete_google_session` (line 134), standard `unlink()` was used without stripping read-only attributes.
3. On Windows (NTFS), `os.unlink()` or `Path.unlink()` on a file with `stat.S_IREAD` raises `PermissionError: [WinError 5] Access is denied`.
4. As directly verified in Observations 2, 3, and 4, this causes:
   - Standalone read-only cache files to be skipped during cache eviction.
   - Read-only orphan session files to be skipped during clean-cache runs.
   - Account deletion to leave read-only `.enc` secret files behind on disk.
5. In addition, `_rmtree_robust` at line 1179 already contains code to handle single files and reset `stat.S_IWRITE`:
   ```python
   if target_path.is_file() or target_path.is_symlink():
       try:
           os.chmod(str(target_path), stat.S_IWRITE)
       except OSError:
           pass
       target_path.unlink(missing_ok=True)
       return True
   ```
   Therefore, simply delegating file removal to `_rmtree_robust` or resetting `stat.S_IWRITE` before unlinking completely fixes these failure modes.
6. Because these failures represent unfulfilled edge cases of Requirement R1 and AC1 on the user's Windows OS, the empirical challenger verdict is **FAIL** until remediated.

---

## 3. Caveats

- **Scope of Failures**: The failures are strictly confined to file-level read-only handling on Windows (`_evict_profile_cache_subdirs` for standalone files, orphan `.enc` session files, and `KeyringSecretStore.delete_google_session`).
- The directory-level removal, credential protection (`Default/Cookies`, `Default/Preferences`, `Local State`, `Local Storage`), active account preservation, API contracts, and UI button wiring are already fully functioning and verified.
- The remediation is minimal and isolated (under 15 lines of code total across 2 files).

---

## 4. Conclusion

**Verdict: FAIL**

The implementation is very close to complete, but fails under Windows read-only stress on individual files and orphan sessions.

### Concrete Remediation Instructions for Worker:

1. **In `vendor/media_factory/backend/app/providers/google.py`**:
   - In `_evict_profile_cache_subdirs(profile_dir)` (around lines 1277–1288):
     Change:
     ```python
     if target_sub.is_dir():
         sub_size = _calc_dir_size_bytes(target_sub)
         if _rmtree_robust(target_sub):
             freed += sub_size
     elif target_sub.is_file():
         try:
             f_size = target_sub.stat().st_size
             target_sub.unlink(missing_ok=True)
             freed += f_size
         except OSError:
             pass
     ```
     To:
     ```python
     if target_sub.is_dir() or target_sub.is_file():
         sub_size = _calc_dir_size_bytes(target_sub)
         if _rmtree_robust(target_sub):
             freed += sub_size
     ```
   - In `clean_profile_caches(self)` (around lines 2381–2389):
     Change:
     ```python
     if enc_file.name not in registered_session_hashes:
         try:
             f_size = enc_file.stat().st_size
             enc_file.unlink(missing_ok=True)
             orphan_sessions_removed += 1
             freed_bytes += f_size
         except OSError:
             pass
     ```
     To:
     ```python
     if enc_file.name not in registered_session_hashes:
         f_size = _calc_dir_size_bytes(enc_file)
         if _rmtree_robust(enc_file):
             orphan_sessions_removed += 1
             freed_bytes += f_size
     ```
   - In `remove(self, account_id: str)`:
     Add guard:
     ```python
     acc_id = str(account_id or '').strip()
     if not acc_id:
         return False
     ```
     and ensure `std_p = self.profile_root / acc_id` is only added if `acc_id` is truthy.

2. **In `vendor/media_factory/backend/app/secrets.py`**:
   - In `delete_google_session(self, account_id: str)` (around lines 131–136):
     ```python
     def delete_google_session(self, account_id: str) -> None:
         session_path = self._session_path(account_id)
         try:
             import stat
             try:
                 os.chmod(str(session_path), stat.S_IWRITE)
             except OSError:
                 pass
             session_path.unlink()
         except (FileNotFoundError, PermissionError):
             pass
         self._delete_keyring_entry(f'{GOOGLE_FLOW_KEY_PREFIX}{account_id}')
         self._delete_keyring_entry(f'{GOOGLE_FLOW_SESSION_PREFIX}{account_id}')
     ```

---

## 5. Verification Method

To reproduce and verify the fix:
1. Run the challenger's adversarial test suite:
   ```powershell
   python -m pytest tests/test_google_flow_adversarial_m1.py -v
   ```
   Currently: 2 failed (`test_adversarial_cache_cleanup_with_unexpected_subdirs_and_corrupt_files`, `test_adversarial_nonexistent_and_orphan_profiles_and_missing_roots`).
   After applying the remediation above: All 7 tests in `tests/test_google_flow_adversarial_m1.py` must pass with 100%.

2. Re-run worker's original test suite:
   ```powershell
   python -m pytest tests/test_google_flow_cache_and_cleanup.py -v
   ```
   Expected: 7 passed.

3. Verify production preservation:
   ```powershell
   python -c "import sqlite3; conn = sqlite3.connect('data/media_factory/cofi_studio.db'); rows = conn.execute('SELECT id FROM local_resources WHERE resource_type = ?', ('google_flow_account',)).fetchall(); assert len(rows) == 3; print('3 accounts preserved')"
   ```
