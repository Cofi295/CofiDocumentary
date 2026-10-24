# Source Repair Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the existing producer chatbot repair action to real Codex CLI and Gemini CLI code repair with durable status and independent verification.

**Architecture:** Extend the focused `SourceRepairAgent` module with a persisted background job runner and provider adapters. Keep `DocumentaryService` as the action/API facade and expose repair polling through FastAPI.

**Tech Stack:** Python 3, subprocess, threading, FastAPI, pytest.

## Global Constraints

- Full CLI permissions apply only inside the CofiDocumentary root.
- A job is fixed only after the independent test command exits zero.
- Provider output and test output are durable JSON/text artifacts.

---

### Task 1: Durable provider runner

**Files:**
- Modify: `COFI_BRAIN/source_repair_agent.py`
- Test: `tests/test_source_repair_agent.py`

- [ ] Write failing tests for Codex full-access arguments, Gemini fallback, persisted status, and failed verification.
- [ ] Run the focused tests and confirm the missing runner behavior fails.
- [ ] Implement job persistence, provider command construction, execution, fallback, verification, and background start.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Service and API integration

**Files:**
- Modify: `documentary/service.py`
- Modify: `documentary/prompts.py`
- Modify: `app.py`
- Test: `tests/test_service.py`
- Test: `tests/test_api.py`

- [ ] Write failing tests for queuing a real repair and polling repair status.
- [ ] Run the focused tests and confirm the missing integration fails.
- [ ] Replace the placeholder patch-plan action with `start_job`, add service facade methods, and add API routes.
- [ ] Run focused and full test suites.

