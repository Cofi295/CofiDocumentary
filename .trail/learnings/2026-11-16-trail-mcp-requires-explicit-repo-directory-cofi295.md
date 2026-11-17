---
title: Trail MCP requires explicit repo directory args and automatic pre-query in workspace_ledger
author: Cofi295
date: 2026-11-16
branch: main
id: l-afebfd47
scope: repo
status: active
src: agent
touches:
  - ".gemini/settings.json"
  - AGENTS.md
  - GEMINI.md
  - agents/direction/orchestrator.md
  - agents/direction/radar.md
  - agents/editorial/research.md
  - agents/editorial/script.md
  - agents/editorial/voice.md
  - agents/quality_and_engineering/evidence_qa.md
  - agents/quality_and_engineering/qc.md
---

## Decided
- In ~/.gemini/config/mcp_config.json and .gemini/settings.json, always pass explicit repo root directory arguments to 	rail.js mcp (	rail -> B:\ALL_TOOLS\CofiDocumentary, 	rail_remotion -> B:\ALL_TOOLS\CofiRemotion), keep global rule ~/.gemini/config/GEMINI.md + B:\AGENTS.md active, and let uild_codebase_surgical_locator in documentary/workspace_ledger.py call TrailCodeManager.query_code_graph (documentary/trail_manager.py) automatically.
## Tried and ruled out
- Registering 	rail.js mcp without [dir] argument: when Antigravity opens B:\ or ~, dvertised() in @trailhq/trail-code/dist/mcp/server.js returns 	ools: [] and wipes cached MCP tool schemas.
