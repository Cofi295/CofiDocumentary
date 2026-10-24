# Multi-source Footage Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a resilient, cached multi-source discovery hub that prefetches ranked footage candidates for Codex/Gemini without replacing their visual-review authority.

**Architecture:** New `documentary/source_discovery.py` owns provider adapters, cache, dedupe and pre-ranking. `documentary/footage.py` asks the hub for compact candidates before each worker prompt and injects them into prepared beats. Existing media download, inspection, validation and merge paths remain authoritative.

**Tech Stack:** Python 3, httpx, optional ddgs, pytest, existing Codex/Gemini/yt-dlp/ffmpeg/ffprobe stack.

## Global Constraints

- Codex/Gemini remain final footage reviewers.
- Discovery results are metadata candidates only; never auto-ACCEPT.
- Provider failure must degrade gracefully.
- No API key may be written to prompt/artifacts/logs.
- Existing footage validation rules stay intact.

---

### Task 1: Discovery core and deterministic ranking

**Files:**
- Create: `documentary/source_discovery.py`
- Create: `tests/test_source_discovery.py`

**Interfaces:**
- Produces: `SourceDiscoveryHub.discover_for_beats(job, beats, workspace) -> dict[str, list[dict]]`
- Produces: `rank_candidates(query_context, candidates, limit) -> list[dict]`

- [ ] Write failing tests for URL dedupe, exact-year boost, year-mismatch penalty, provider failure isolation and cache reuse.
- [ ] Run `pytest tests/test_source_discovery.py -q` and verify RED.
- [ ] Implement provider interface, cache, concurrency, normalization and ranking.
- [ ] Run `pytest tests/test_source_discovery.py -q` and verify GREEN.

### Task 2: Provider adapters

**Files:**
- Modify: `documentary/source_discovery.py`
- Modify: `requirements.txt`
- Test: `tests/test_source_discovery.py`

**Interfaces:**
- Always-on: DDGS, Internet Archive, Library of Congress, Wikimedia Commons.
- Optional: SearXNG, Brave, Europeana, NARA.

- [ ] Add failing normalization tests for each provider response shape.
- [ ] Verify tests fail before implementation.
- [ ] Implement bounded HTTP/provider adapters with compact normalized output.
- [ ] Add `ddgs` dependency while keeping runtime fallback if unavailable.
- [ ] Verify provider tests pass without live network access by injecting fake transports/providers.

### Task 3: Footage prompt integration

**Files:**
- Modify: `documentary/footage.py`
- Modify: `tests/test_footage.py`

**Interfaces:**
- `FootageCoordinator` owns/injects one `SourceDiscoveryHub`.
- `build_worker_prompt(..., discovery_by_beat=None)` embeds compact candidates into prepared beats.

- [ ] Add failing tests proving candidate pools appear in the correct beat, fallback behavior remains available, and visual inspection language remains mandatory.
- [ ] Verify RED.
- [ ] Integrate hub before Codex batch, Gemini run and footage repair prompts.
- [ ] Keep discovery failure non-fatal and bounded.
- [ ] Verify GREEN.

### Task 4: Verification and performance smoke

**Files:**
- No production changes unless tests expose a defect.

- [ ] Run `pytest tests/test_source_discovery.py tests/test_footage.py -q`.
- [ ] Run full `pytest -q`.
- [ ] Run a live read-only discovery smoke on one historical, one wildlife and one non-US query; record provider latency/count without downloading media.
- [ ] Confirm no secret values appear in generated discovery cache or prompts.

