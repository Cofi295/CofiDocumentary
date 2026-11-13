---
title: App core is strictly technical engine while all creative and country DNA lives isolated per channel profile
author: Cofi295
date: 2026-10-31
branch: main
id: l-ac4707eb
scope: repo
status: active
src: agent
touches:
  - ".gemini/settings.json"
  - AGENTS.md
  - app.py
  - data/channel_playbooks.json
  - data/channel_profiles.json
  - data/producer_chat_history.jsonl
  - desktop_app.py
  - documentary/agent_manager.py
  - documentary/ai_visual.py
  - documentary/audio_library_manager.py
---

## Decided
- `documentary/*.py` acts strictly as a pure technical core (closed-loop `Maker -> Sensor -> Critic -> Fixer -> Final` execution, acoustic/ASR/pixel/loudness/outro sensors, TTS symbol normalization, and schema validation).
- Every channel profile in `data/channel_profiles.json` (`channel_profile_snapshot`, `editorial_dna`, `voice_and_structure`, `editing_dna`, `seo_keyword_dna`, `creative_brief`) owns 100% isolated creative tone, speech register, narrative structure, and country/domain rules with zero cross-channel leakage.
## Tried and ruled out
- Hardcoding a single channel's genre, case names, surname rules, or speech register globally across all profiles in Python code: blocks AI Agent creative freedom on other channels and countries.
