---
title: "Chinese true-crime scripts must use 100% real historical cases and Chinese surnames"
author: Cofi295
date: 2026-10-27
branch: main
id: l-34a2671f
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
- In `documentary/prompts.py`, `documentary/service.py`, and `data/channel_profiles.json` (`channel-cn-cyber-finance-kr`), every script must be 100% grounded in a single real named historical case (e.g. Ezubao / Qian Zhimin) with real court dates and real recovery rates.
- Chinese citizens and victims in China must use Korean-transliterated Chinese surnames (`천 씨`, `왕 씨`, `린 씨`, `저우 씨`, `장 씨`), never Korean surnames (`김 씨`, `박 씨`, `이 씨`, `최 씨`, `정 씨`).
- Conversational `~죠` (`~었죠`, `~았죠`, `~였죠`, `~하죠`) endings must be capped at 6 to 8 occurrences across a 180-sentence script, never on consecutive sentences.
## Tried and ruled out
- Composite cases stitching multiple scams or using `김 씨` for Chinese victims in Hunan/Changsha: rejected by Korean viewers as AI-generated localization errors and unrealistic 14-day timelines.
