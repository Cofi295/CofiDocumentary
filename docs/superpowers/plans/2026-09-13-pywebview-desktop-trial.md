# PyWebView Desktop Trial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open CofiDocumentary as a resizable native Windows PyWebView application while preserving the existing UI and backend state.

**Architecture:** A focused launcher detects or starts the FastAPI backend, waits for health, opens PyWebView, and shuts down only an owned backend. Existing static assets and service code remain untouched.

**Tech Stack:** Python 3.14, FastAPI, Uvicorn, PyWebView, Edge WebView2, pytest.

## Global Constraints

- Do not package an executable in this trial.
- Do not rewrite the HTML/CSS/JavaScript UI.
- Do not interrupt or duplicate the currently active Footage worker.
- Bind only to localhost.

---

### Task 1: Desktop launcher lifecycle

**Files:**
- Create: `desktop_app.py`
- Create: `tests/test_desktop_app.py`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: `app:app`, `GET /api/health`
- Produces: `probe_backend(port)`, `resolve_backend_port()`, `BackendController`, `main()`

- [ ] Write tests for own-backend detection, busy-port fallback, and owned shutdown.
- [ ] Run the tests and confirm they fail because the launcher does not exist.
- [ ] Implement the minimal launcher and dependency declaration.
- [ ] Run the launcher tests and focused API smoke test.

### Task 2: Live Windows trial

**Files:**
- Use: `desktop_app.py`

**Interfaces:**
- Consumes: an existing or launcher-owned CofiDocumentary backend
- Produces: a visible resizable desktop window rendering the current UI

- [ ] Start `desktop_app.py` without a console window.
- [ ] Confirm the process and backend health.
- [ ] Visually confirm the current UI is rendered in the desktop window.

