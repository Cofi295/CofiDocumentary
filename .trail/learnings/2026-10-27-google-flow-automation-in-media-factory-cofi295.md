---
title: Google Flow automation in media_factory must use Agent Mode URL and live browser cookies
author: Cofi295
date: 2026-10-27
branch: main
id: l-1bbc97e0
scope: repo
status: active
src: agent
touches:
  - AGENTS.md
  - data/channel_profiles.json
  - documentary/agent_manager.py
  - documentary/audio_library_manager.py
  - documentary/edit.py
  - documentary/edit_footage_fetcher.py
  - documentary/models.py
  - documentary/prompts.py
  - documentary/quality.py
  - documentary/render_cache.py
---

## Decided
- In `vendor/media_factory/backend/app/providers/google.py` and `vendor/media_factory/extension/content.js`, launch `/fx/vi/tools/flow` directly, support both Slate `[data-slate-editor='true']` and Agent Mode `textarea`/`contenteditable` inputs, convert `.webp` downloads to `.jpg`, and hide `#glabs-overlay.visible` pointer-events during submission.
## Tried and ruled out
- Importing stale `session` tokens from `G-Labs Automation` SQLite DB into `KeyringSecretStore`: overrides live Chrome profile cookies and causes HTTP 401/307 redirects on Labs trpc endpoints.
