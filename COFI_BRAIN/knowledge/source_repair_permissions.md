# COFI Source Repair Agent Permissions

## Purpose
Enable the COFI repair agent to diagnose and fix application issues instead of only reporting errors.

## Allowed actions
- Read application source code.
- Inspect logs, stack traces, tests and runtime errors.
- Create patches for bugs.
- Refactor broken modules when required.
- Update dependencies when compatibility issues are detected.
- Add regression tests after fixes.
- Run verification checks before marking a repair complete.

## Repair workflow
1. Detect error.
2. Identify affected source files.
3. Create minimal fix.
4. Run tests/smoke checks.
5. Record lesson in COFI_BRAIN memory.

## Safety rules
- Keep backups before destructive changes.
- Do not remove user data.
- Do not change production behaviour without verification.
- Prefer reversible patches.
