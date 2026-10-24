# COFI DOCUMENTARY Production OS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biến COFI DOCUMENTARY thành một pipeline Radar -> Script/Visuals -> Voice/SRT -> Codex+Gemini Footage -> Preflight -> Remotion Edit/Preview -> QC có resume/checkpoint và UI tiếng Việt.

**Architecture:** FastAPI Documentary giữ orchestration/state bền vững; các engine ngoài được bọc bằng client/gateway nhỏ (Radar, CofiVoice, Codex, Gemini, Remotion). Mỗi phase giao tiếp qua artifact theo `beat_id`, để tiến trình có thể phục hồi sau khi process/bridge chết.

**Tech Stack:** Python 3.14, FastAPI, requests, subprocess, Codex CLI, Gemini CLI, CofiVoice FastAPI, Remotion 4.0.520, vanilla HTML/CSS/JS.

## Global Constraints

- UI hiển thị 100% tiếng Việt.
- Giữ dữ liệu job/workspace cũ; không xóa sản phẩm đã tạo.
- Gemini CLI là engine tùy chọn khi offline nhưng phải được cài trên máy trong lần triển khai này.
- Visual timeline dùng `beat_id` ổn định xuyên suốt PLAN/VOICE/FOOTAGE/EDIT.
- Không cho EDIT chạy khi PREFLIGHT chưa đạt coverage.
- Edit state phải nằm trên disk, không phụ thuộc phiên chat/bridge.

---

### Task 1: Pipeline model và resume state

**Files:**
- Modify: `documentary/models.py`
- Modify: `documentary/store.py`
- Modify: `documentary/service.py`
- Modify: `tests/test_store.py`
- Modify: `tests/test_service.py`

**Interfaces:**
- Produces: `PHASES = ("plan","voice","footage","preflight","edit","qc")`, persistent recovery of interrupted phases, rerunnable phase API.

- [ ] Viết test cho phase mới, restart recovery và resume từ phase chưa thành công.
- [ ] Chạy test để thấy fail.
- [ ] Implement state/recovery/required-artifact mapping.
- [ ] Chạy test xanh.

### Task 2: Engine clients + health + Radar import

**Files:**
- Create: `documentary/engines.py`
- Create: `documentary/radar.py`
- Modify: `documentary/service.py`
- Modify: `app.py`
- Modify: `tests/test_api.py`
- Create: `tests/test_engines.py`

**Interfaces:**
- Produces: health records `cofi_radar`, `codex_cli`, `gemini_cli`, `cofi_voice`, `cofi_remotion`; Radar proxy/import methods.

- [ ] Test engine discovery and Radar endpoints with fake HTTP clients.
- [ ] Implement process/path detection and Radar client.
- [ ] Add `/api/radar/*` and job-from-radar endpoints.
- [ ] Verify API tests.

### Task 3: PLAN visual beat contract và Gemini/Codex selection

**Files:**
- Create: `documentary/gemini_gateway.py`
- Modify: `documentary/codex_gateway.py`
- Modify: `documentary/prompts.py`
- Modify: `documentary/service.py`
- Modify: `tests/test_gateway.py`

**Interfaces:**
- Produces: `visual_manifest.json` with stable `beat_id`; engine selectable via job `plan_engine` (`codex`/`gemini`).

- [ ] Test prompt/output contract and Gemini command construction.
- [ ] Implement Gemini gateway compatible with StageResult.
- [ ] Route PLAN to configured engine and validate `visual_manifest.json`.
- [ ] Verify tests.

### Task 4: CofiVoice + SRT phase

**Files:**
- Create: `documentary/voice.py`
- Create: `documentary/srt.py`
- Modify: `documentary/service.py`
- Create: `tests/test_voice.py`

**Interfaces:**
- Consumes: `script.md`, `visual_manifest.json`.
- Produces: `audio/narration.wav`, per-beat audio files, `voice_manifest.json`, `subtitles.srt`.

- [ ] Test SRT timestamps built from measured beat duration.
- [ ] Test voice client with mocked CofiVoice `/api/job` responses.
- [ ] Implement async polling/copy plus durable manifest.
- [ ] Verify phase artifact validation.

### Task 5: Dual footage workers + coverage preflight

**Files:**
- Create: `documentary/footage.py`
- Modify: `documentary/prompts.py`
- Modify: `documentary/service.py`
- Create: `tests/test_footage.py`
- Modify: `documentary/quality.py`

**Interfaces:**
- Produces: `footage_codex.json`, `footage_gemini.json`, `footage_review.json`, `asset_registry.json`, `coverage_matrix.json`, `preflight_report.json`.

- [ ] Test deterministic beat partitioning and merge/dedup.
- [ ] Test preflight rejects missing beat coverage.
- [ ] Implement worker prompts and parallel coordinator.
- [ ] Implement preflight gate tied to actual files/beat IDs.
- [ ] Verify tests.

### Task 6: Remotion session/preview/checkpoint

**Files:**
- Create: `documentary/remotion.py`
- Modify: `documentary/service.py`
- Modify: `app.py`
- Create: `tests/test_remotion.py`

**Interfaces:**
- Produces: `edit_session.json`, `edit_checkpoint.json`, Studio URL/status API, persistent resume context for edit prompts.

- [ ] Test session state creation/recovery without launching Studio.
- [ ] Implement Studio discovery/start command and checkpoint hashing.
- [ ] Add preview/session endpoints.
- [ ] Update EDIT prompt to read checkpoint/source state before editing.
- [ ] Verify tests.

### Task 7: Full Vietnamese UI

**Files:**
- Modify: `static/index.html`
- Modify: `static/app.js`
- Modify: `static/styles.css`

**Interfaces:**
- Consumes all new API endpoints.
- Produces Vietnamese dashboard, Radar topic picker, job wizard, 6-phase pipeline, preview iframe/panel and resume controls.

- [ ] Replace all visible English copy with Vietnamese labels.
- [ ] Add engine health cards and Radar topic flow.
- [ ] Add phase tabs/artifact summaries and Remotion preview panel.
- [ ] Add responsive desktop layout and clear status hierarchy.
- [ ] Smoke-load `/` and static assets.

### Task 8: Gemini CLI install + final verification

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Verifies `gemini --version`, full pytest, compileall, API routes, health, and existing benchmark hash.

- [ ] Install `@google/gemini-cli@0.58.0` globally with npm.
- [ ] Verify `gemini --version`.
- [ ] Run `python -m pytest -q --basetemp=.pytest_production_os`.
- [ ] Run compile/import/API smoke checks.
- [ ] Verify Nepal benchmark hash remains unchanged.
- [ ] Update docs with run/usage/resume flow.
