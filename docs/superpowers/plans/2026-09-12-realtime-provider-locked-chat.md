# Realtime Provider-Locked Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep each Producer Chat turn attached to its explicitly selected provider, stream real work into one durable UI turn, and emit the final reply only after all requested work reaches a terminal state.

**Architecture:** Add a small durable chat-run controller that owns run state and append-only events. `DocumentaryService` executes a turn with a captured provider, follows any source-repair job to terminal state, and writes final chat history only then. FastAPI exposes create/status/events/cancel endpoints; the existing browser chat uses them and reconnects after reload.

**Tech Stack:** Python 3.14, FastAPI, NDJSON streaming, filesystem JSON/JSONL persistence, vanilla JavaScript, pytest.

## Global Constraints

- Explicit `codex` and `gemini` selections never fail over.
- Both providers run without interactive permission prompts.
- Intermediate work is factual CLI output; private hidden reasoning is not exposed.
- A terminal success requires actual source changes and passing independent verification for source repair.
- Existing chat history remains scoped by selected documentary project.

---

### Task 1: Provider-locked producer execution

**Files:**
- Modify: `documentary/service.py`
- Test: `tests/test_service.py`

**Interfaces:**
- Consumes: persisted `chat_provider`, `CodexGateway`, `GeminiGateway`, `SourceRepairAgent`.
- Produces: `producer_chat(..., locked_provider, event_callback, cancel_event)` and provider-aware `_execute_producer_action(...)`.

- [ ] Add failing tests proving explicit Codex/Gemini use only their selected gateway and override a conflicting provider emitted by `repair_code`.
- [ ] Run the focused tests and confirm provider mismatch failures.
- [ ] Capture and validate the provider at turn start; call the chosen gateway directly for explicit modes and retain the router only for `auto`.
- [ ] Pass the locked provider into action execution and wait for source repair terminal state while forwarding new repair events.
- [ ] Build the final response from persisted repair evidence and append assistant history only after terminal completion.
- [ ] Run focused service tests.

### Task 2: Durable chat runs and reconnectable event stream

**Files:**
- Create: `COFI_BRAIN/chat_run_manager.py`
- Modify: `documentary/service.py`
- Modify: `app.py`
- Test: `tests/test_chat_run_manager.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: `create_run(payload)`, `get_run(run_id)`, `events(run_id, after)`, `cancel(run_id)`, `append_event(run_id, event)`.
- API: `POST /api/producer-chat/runs`, `GET /api/producer-chat/runs/{id}`, `GET /api/producer-chat/runs/{id}/events`, `POST /api/producer-chat/runs/{id}/cancel`.

- [ ] Add failing tests for durable sequencing, terminal state, replay after sequence, and cancellation.
- [ ] Implement atomic run state and append-only JSONL events under `.producer/chat_runs`.
- [ ] Add service methods that start one background worker per run and keep it independent of browser connections.
- [ ] Add NDJSON API endpoints that replay persisted events and wait for new events until terminal state.
- [ ] Keep `/api/producer-chat/stream` compatible by delegating to a durable run.
- [ ] Run manager and API tests.

### Task 3: One live work card in both chat surfaces

**Files:**
- Modify: `static/app.js`
- Modify: `static/styles.css`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: chat-run create/status/event APIs.
- Produces: one reconnectable active card with provider, elapsed time, stage, events, Stop control, and terminal evidence.

- [ ] Add failing UI contract tests for run creation, event replay, reconnect, cancellation, and terminal-only final rendering.
- [ ] Replace immediate stream submission with durable run creation and event consumption.
- [ ] Persist active run IDs by chat scope in browser storage and reconnect during render/boot.
- [ ] Render normalized activity events into one card and replace it with the final response only on success/failure/cancel.
- [ ] Disable duplicate submission while the scope has an active run and wire Stop to cancel.
- [ ] Run JavaScript syntax and UI contract tests.

### Task 4: End-to-end verification and app reload

**Files:**
- Verify: `COFI_BRAIN/chat_run_manager.py`
- Verify: `documentary/service.py`
- Verify: `app.py`
- Verify: `static/app.js`

**Interfaces:**
- Confirms all interfaces above operate together.

- [ ] Run focused manager, service, repair-agent, and API tests with a project-local pytest base directory.
- [ ] Run Python compilation and JavaScript syntax checks.
- [ ] Restart the server only after confirming no documentary phase is running.
- [ ] Verify health, create a controlled run with a stubbed provider in tests, and inspect the browser UI contract.
- [ ] Confirm explicit provider routing and terminal-only responses from persisted evidence.
