# Realtime Provider-Locked Producer Chat Design

## Goal

Make Cofi Producer Chat behave like the selected provider's desktop chat: one visible turn remains active while the provider reads files, edits code, runs commands, and verifies the result; the final assistant reply appears only after terminal success or failure.

## Provider contract

- Capture `chat_provider` when a user turn starts and persist it on the run.
- `codex` always invokes Codex CLI for chat and source repair.
- `gemini` always invokes Antigravity/Gemini for chat and source repair.
- `auto` is the only mode allowed to fail over between providers.
- Ignore a provider emitted inside a model-generated `repair_code` action when the UI selection is explicit; the server-side selection is authoritative.
- Provider changes made in the UI affect the next turn, never a turn already running.

## Autonomous execution contract

- Codex runs with full project access and no approval prompts.
- Antigravity runs with always-proceed permissions and no approval prompts.
- Both providers must inspect, edit, execute relevant tests, and iterate until tests pass or a terminal blocker is reached.
- A successful CLI exit is insufficient. Success requires at least one source-file content change and an independent verification command returning zero.
- A no-change response, permission refusal, timeout, failed verification, or provider mismatch is terminal failure and must be reported honestly.

## Chat run lifecycle

Each submitted message creates a durable `chat_run` with:

- run ID, selected provider, scope/job ID, original message, timestamps;
- status: `queued`, `chatting`, `repairing`, `verifying`, `succeeded`, `failed`, or `cancelled`;
- append-only normalized events and raw provider logs;
- repair job ID and final evidence when source repair is requested;
- final assistant response written only at terminal state.

The initial HTTP stream stays open while the run executes. If the browser disconnects or reloads, it reconnects by run ID and replays events after the last received sequence number. Execution continues independently of the browser connection.

## Realtime events

The backend emits normalized events for provider selection, analysis/status text, file reads, file edits, commands, test output, repair transition, verification, completion, failure, heartbeat, and cancellation. Events contain factual summaries from native CLI output. Hidden reasoning is not fabricated or exposed.

For `repair_code`, the producer-chat stream does not finish after queuing the repair. It follows the repair job, forwards its live events into the same run, waits for `fixed` or `failed`, and then builds the terminal response from persisted evidence.

## User interface

- The user message appears immediately.
- One assistant work card remains active for the turn.
- The card shows the locked provider, elapsed time, current stage, latest activity, progress log, and Stop control.
- Intermediate events update the same card and do not create premature assistant replies.
- On terminal success, the card becomes the final response with changed files and verification results.
- On failure, it becomes a truthful error report with the failed stage and reason.
- Reloading the page restores and reconnects active runs automatically.
- While a run is active, duplicate submission is disabled for that chat scope.

## API boundaries

- `POST /api/producer-chat/runs`: create and start a durable run.
- `GET /api/producer-chat/runs/{run_id}`: inspect authoritative state and final evidence.
- `GET /api/producer-chat/runs/{run_id}/events`: stream/replay NDJSON events using an `after` sequence.
- `POST /api/producer-chat/runs/{run_id}/cancel`: request cancellation.
- Existing `/api/producer-chat/stream` remains temporarily compatible and delegates to the run implementation.

## Persistence and recovery

Runs live under `.producer/chat_runs/<run_id>/` with `run.json`, `events.jsonl`, and provider logs. Writes use atomic replacement. Startup scans nonterminal runs: it marks runs whose process disappeared as interrupted/failed with an actionable message, while a still-running in-process job remains attachable.

## Verification

Tests must prove:

- explicit Codex never calls Gemini;
- explicit Gemini never calls Codex;
- `repair_code` uses the server-locked provider even if model output requests another provider;
- no terminal chat result is emitted while repair is nonterminal;
- live events are streamed and replayed in sequence;
- source changes and independent tests are required for success;
- no-change and permission-refusal outputs become failures;
- reload/reconnect obtains the final result;
- frontend keeps one active work card and renders terminal evidence.

## Scope

This change covers Producer Chat and source-repair execution. It does not redesign unrelated documentary phases or expose private model reasoning.
