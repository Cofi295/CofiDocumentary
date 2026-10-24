# E2E Test Infra: CofiDocumentary Professional SaaS Studio

## Test Philosophy
- **Opaque-box & Requirement-Driven**: Tests derive directly from `ORIGINAL_REQUEST.md` (R1-R6, AC1-AC4). They interact via public HTTP endpoints, API contracts, DOM layout assertions, and persisted file state without depending on internal implementation details.
- **Methodology**: Systematic 4-Tier test strategy combining Category-Partition, Boundary Value Analysis, Pairwise Combinatorial Testing, and Real-World Application Workloads.

## Feature Inventory & Test Mapping
| # | Feature | Requirement | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Real-World) |
|---|---------|-------------|:-----------------:|:-----------------:|:-----------------:|:-------------------:|
| F1 | SaaS UI/UX Overhaul & Dual Manual + AI Control | R1, AC1 | 5 tests | 5 tests | ✓ | ✓ |
| F2 | Channel Profile & Project State Isolation | R2, AC2 | 5 tests | 5 tests | ✓ | ✓ |
| F3 | Non-Destructive Data Preservation & Backfill | R6, AC2 | 5 tests | 5 tests | ✓ | ✓ |
| F4 | Persistent Editing Style Memory ("Lock Approved Edit") | R3, AC3 | 5 tests | 5 tests | ✓ | ✓ |
| F5 | Audio-Visual Voice/SRT Sync & Policy Guardrails | R3, AC3 | 5 tests | 5 tests | ✓ | ✓ |
| F6 | Channel-DNA Pre-Flight Intelligence | R4, AC4 | 5 tests | 5 tests | ✓ | ✓ |
| F7 | Continuous Self-Learning Post-Mortem Engine | R5, AC4 | 5 tests | 5 tests | ✓ | ✓ |

## Test Architecture
- **Test Runner**: Python pytest-based test runner executing automated DOM / layout assertions, API integration tests, and data persistence validation.
- **Invocation**: `pytest tests/e2e/test_all_e2e.py -v` or `python tests/e2e/runner.py`.
- **Pass / Fail Semantics**: Zero failures, zero errors, exit code 0.
- **Directory Layout**:
  - `tests/e2e/`:
    - `tests/e2e/runner.py`: Main test suite orchestrator and summary reporter.
    - `tests/e2e/test_ac1_ui_ux.py`: DOM layout verification (1280px-1920px), zero overlap, dual manual/AI controls.
    - `tests/e2e/test_ac2_isolation_backfill.py`: Profile switching zero bleed, draft isolation from `selectedId`, backfill verification of legacy profiles and jobs.
    - `tests/e2e/test_ac3_edit_memory_sync_policy.py`: "Lock Approved Edit Style to Channel" workflow, beat-to-SRT sync auto-repair, and YouTube policy scorecard.
    - `tests/e2e/test_ac4_preflight_self_learning.py`: Channel-DNA Pre-Flight checks, Win/Loss diagnostic post-mortem, and upgrade rule injection.
    - `tests/e2e/test_tier3_pairwise.py`: Cross-feature combinatorial workflows.
    - `tests/e2e/test_tier4_workload.py`: Real-world end-to-end documentary production scenarios.

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: ≥5 test cases per feature (≥35 test cases total).
- **Tier 2 (Boundary & Corner Cases)**: ≥5 test cases per feature (≥35 test cases total).
- **Tier 3 (Cross-Feature Combinations)**: ≥7 test cases testing pairwise interactions.
- **Tier 4 (Real-World Application Scenarios)**: ≥5 realistic documentary production workflows.
- **Target Suite Total**: ≥82 rigorous test cases.
