# Orchestration Plan: CofiDocumentary Professional SaaS Studio Upgrade

## Objective
Fulfill all requirements R1-R6 to satisfy Acceptance Criteria AC1-AC4 completely in `B:\ALL_TOOLS\CofiDocumentary`, transforming it into an isolated, self-learning SaaS documentary studio with dual manual/AI control.

## Phase 0: Survey & Technical Mapping (Current)
- Launch 3 parallel Explorers to inspect authoritative codebases, APIs, storage schemas, and current behaviors:
  - **Explorer 1**: Frontend UI/UX, DOM architecture, Tab hierarchy (Step 0 to Step 08), AI Chat dock collision/overlap, form reactivity and profile isolation in UI.
  - **Explorer 2**: Backend SQLite schema (`data/radar.db`), job storage (`data/jobs/`, `workspaces/`), channel profile isolation, existing record backfill/repair (`channel-1e24de3ab5`, `channel-e544a64b7c`, `channel-aa913eb90d`, `channel-f6ec4dfff3`, etc.).
  - **Explorer 3**: Pipeline engines, Remotion recipes, Edit Style Memory (`lock-edit-dna`), Audio-Visual Voice/SRT sync, YouTube Policy guardrails, Channel-DNA Pre-Flight, and Self-Learning Post-Mortem engine.
- Synthesize findings into `PROJECT.md` (Feature Inventory, Architecture, Milestones, Interface Contracts, Code Layout).

## Phase 1: Dual Track Decomposition & Dispatch
- **Track 1: Implementation Track**
  - **Milestone 1 (M1)**: Backend Storage, Profile/Project Strict Isolation & Backfill (R2, R6, AC2)
  - **Milestone 2 (M2)**: SaaS UI/UX Overhaul & Dual Manual + AI Control (R1, AC1)
  - **Milestone 3 (M3)**: Persistent Edit Style Memory, Remotion Recipe Lock, Voice-Visual Sync & YouTube Policy Guardrails (R3, AC3)
  - **Milestone 4 (M4)**: Channel-DNA Pre-Flight & Continuous Self-Learning Post-Mortem Engine (R4, R5, AC4)
- **Track 2: E2E Testing Track**
  - Spawn E2E Testing Orchestrator to build opaque-box test suite for AC1-AC4 (Tier 1-4).
  - Produce `TEST_INFRA.md` and publish `TEST_READY.md`.

## Phase 2: Milestone Execution & Quality Gates
- Execute each milestone through Sub-Orchestrators with strict Explorer -> Worker -> Reviewer -> Challenger -> Forensic Auditor cycle.
- Mandatory gate checks: passing tests, all reviewers approve, challengers verify, clean forensic audit.

## Phase 3: Final E2E Pass & Adversarial Hardening
- Run full E2E test suite across all tiers until 100% passing.
- Run white-box adversarial stress testing (Tier 5) with challengers.

## Phase 4: Final Sign-off & Reporting
- Final audit and verification.
- Report completion back to Sentinel.
