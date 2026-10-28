---
title: Edit and SEO subagents should use exact quality.py and thumbnail_studio.py schemas without re-reading service.py
author: Cofi295
date: 2026-10-27
branch: main
id: l-e518b6df
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
- In `documentary/quality.py` and `documentary/service.py`, `edit` phase requires `edit_manifest.json`, `remotion_media_manifest.json`, `asset_registry.json`, and `edit_progress.json` (`status: completed`, `completed_beats == total_beats`).
- `seo` phase in `documentary/quality.py` and `documentary/thumbnail_studio.py` requires `seo_package.json` (with `primary_title`, `title_variants`, `description`, `chapters`, `tags`, `hashtags`, `pinned_comment`, `thumbnail_text_variants`) and `thumbnail_design.json` rendered via `render_design_thumbnails_to_disk(workspace, design)`.
## Tried and ruled out
- Subagents grepping and reading 10,000+ lines of `documentary/service.py` and `documentary/quality.py` on every job run: wastes 30-45% of uncached input tokens when the schema is fixed.
