---
title: "Fix GeoJson3DMapStage preservation & footage_eye incremental batching"
author: Cofi295
date: 2026-11-16
branch: main
id: l-808b4e3f
scope: repo
status: active
src: agent
touches:
  - documentary/vox_engine/semantic_router.py
  - documentary/prompts.py
  - agents/visual_cinema/footage.md
  - agents/visual_cinema/vox.md
---

Two recurring defects fixed: (1) documentary/vox_engine/semantic_router.py (_GEO_SATELLITE_MAP_NEEDED_RE and _infer_sentence_specific_vox_mechanism) previously ignored planned framing_motion_intent/purpose for <GeoJson3DMapStage> and missed Korean radius/road/dispatch sentences, overwriting 3D satellite maps with <Desk> layouts while duplicating micro_labels_ko; fixed to preserve planned GeoJson3DMapStage + WGS84 anchors and deduplicate micro_labels_ko. (2) build_footage_eye_agent_prompt & agents/visual_cinema/footage.md lacked incremental 3-4 source batching and explicit deletion of cartoon lectern hosts, vertical black-boxed PiP, and static grass-sky slideshows, causing 85+ min download stalls with 0 cut clips; updated to enforce small-batch cut-as-you-go, immediate junk deletion, GRID 100px safe-cropping (w>=960, h>=540), and zero Python source reads. Also agents/visual_cinema/vox.md must stay Hangul-free to pass AgentManager.lint_corpus().
