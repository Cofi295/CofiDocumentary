# BRIEFING — 2026-10-19T12:10:00Z

## Mission
Upgrade CofiDocumentary with 2-Layer Anti-Duplicate Topic Memory & Pre-Flight System and True Reference Image Fidelity & Job Workspace Persistence.

## 🔒 My Identity
- Archetype: orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\swe_1
- Original parent: sentinel
- Original parent conversation ID: af06c4cf-76b1-4276-94ad-2030e3fb666b

## 🔒 My Workflow
- **Pattern**: SWE Light
- **Scope document**: B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\ORIGINAL_REQUEST.md
1. **Decompose**: Single whole task sequentially refined per SWE Light pattern.
2. **Dispatch & Execute**:
   - Direct (iteration loop): teamwork_preview_implementer -> teamwork_preview_reviewer (min 3 rounds) -> teamwork_preview_victory_auditor
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (sentinel)
4. **Succession**: At spawn count >= 16 and all subagents complete, write handoff.md, spawn successor
- **Work items**:
  1. Implementer Round 1 [in-progress]
  2. Reviewer Round 1 [pending]
  3. Reviewer Round 2 [pending]
  4. Reviewer Round 3 [pending]
  5. Victory Audit [pending]
- **Current phase**: 2
- **Current focus**: Implementer Round 1

## 🔒 Key Constraints
- NEVER write, modify, or create source code files yourself. Delegate all implementation and repair to teamwork_preview_implementer and teamwork_preview_reviewer.
- NEVER explore or debug the codebase in order to solve the task yourself.
- Propagate user task verbatim.
- Sequential refinement, no parallel opinion.
- Maintain an open-issues ledger across ALL rounds.
- Re-run relevant tests independently to verify claims.
- Minimum 3 review rounds required before victory audit.
- Blocking victory audit before reporting completion.
- Never reuse a subagent after it has delivered its handoff — always spawn fresh.

## Current Parent
- Conversation ID: af06c4cf-76b1-4276-94ad-2030e3fb666b
- Updated: not yet

## Key Decisions Made
- Dispatched task using SWE Light protocol with teamwork_preview_implementer first.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| implementer_r1 | teamwork_preview_implementer | Round 1 Implementation | in-progress | 4b11b8cf-69c1-474f-a2d9-dd8cf7f54253 |

## Succession Status
- Succession required: no
- Spawn count: 1 / 16
- Pending subagents: 4b11b8cf-69c1-474f-a2d9-dd8cf7f54253
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: 481d5683-fff0-426f-8bdd-f3786de36395/task-10
- Safety timer: none
- On succession: kill all timers before spawning successor
- On context truncation: run `manage_task(Action="list")` — re-create if missing

## Artifact Index
- B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\swe_1\BRIEFING.md — Working memory
- B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\swe_1\DISPATCH.md — Incoming task log
- B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\swe_1\progress.md — Progress & heartbeat
