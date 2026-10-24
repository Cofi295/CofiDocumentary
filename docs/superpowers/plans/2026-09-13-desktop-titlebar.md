# Desktop Title Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven-development to implement this plan task-by-task.

**Goal:** Replace the white Windows title bar with dark app controls in the desktop window only.

**Architecture:** `desktop_app.py` owns native window operations through a bridge. Static HTML/CSS/JS shows and styles controls only after PyWebView is ready.

**Tech Stack:** Python, PyWebView, HTML, CSS, JavaScript, pytest.

## Global Constraints

- Do not restart the running backend or Footage worker.
- Browser UI must not show window controls.
- Retain native minimize, maximize/restore, close and drag behavior.

### Task 1: Desktop bridge and frameless window

- [ ] Write tests for native action dispatch and frameless creation.
- [ ] Run tests and confirm failure.
- [ ] Implement bridge and launch settings.
- [ ] Run tests and confirm pass.

### Task 2: Desktop-only title bar

- [ ] Write a test for conditional controls and bindings.
- [ ] Run test and confirm failure.
- [ ] Add HTML, CSS, and JS using PyWebView bridge.
- [ ] Run tests and confirm pass.

### Task 3: Runtime verification

- [ ] Open a separate new desktop window using the existing backend.
- [ ] Verify a single backend listener, visible dark title bar, and window controls.
