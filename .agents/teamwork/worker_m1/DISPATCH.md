## 2026-10-23T17:57:52Z
You are teamwork_preview_worker (Worker M1: Voice-Driven True Crime Vox & Satellite Engine Integration).
Your working directory is: B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\worker_m1

MANDATORY FIRST STEP: Read the authoritative user request at B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\ORIGINAL_REQUEST.md (especially under header ## Follow-up — 2026-10-23T17:41:06Z).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Reference Documents to read:
- `B:\ALL_TOOLS\CofiDocumentary\PROJECT.md`
- `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\explorer_survey_1\survey_vox_engine.md`
- `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\explorer_survey_2\survey_backend_routing.md`
- Source references: `b:\ALL_TOOLS\CofiBlenderStudio\vox_editorial_artist.py`, `b:\ALL_TOOLS\CofiBlenderStudio\vox_archetype_expansion.py`, `b:\ALL_TOOLS\CofiBlenderStudio\vox_gis_cache\`

FILE WRITE BOUNDARIES (You exclusively own these files; do not edit other files):
- `documentary/vox_engine/__init__.py`
- `documentary/vox_engine/typography.py`
- `documentary/vox_engine/gis_cache.py`
- `documentary/vox_engine/archetypes.py`
- `documentary/vox_engine/renderer.py`
- `documentary/vox_engine/semantic_router.py`
- `services/editing_dna_service.py`
- `documentary/visuals.py`
- `documentary/edit.py`
- `documentary/prompts.py`

IMPLEMENTATION TASKS:
1. Build `documentary/vox_engine/`:
   - `typography.py`: Font manager with robust multi-tier fallback cascade (`Malgun Gothic` -> `Microsoft YaHei` / `msyh.ttc` -> `Arial Unicode` / system sans-serif), text bounding box calculation, text wrapping, and zero missing glyphs / tofu (`□`) verification.
   - `gis_cache.py`: Watermark-free Esri World Imagery multi-scale plate loader (Z6, Z9, Z14, Z16) reading directly from `b:\ALL_TOOLS\CofiBlenderStudio\vox_gis_cache\`, Web Mercator projections (`deg2num`, `lonlat_to_plate_px`, `crop_map_camera`, `map_lonlat_to_screen`), and NumPy thermal/infrared shader.
   - `archetypes.py`: Compositing implementation for all 24 True Crime investigative archetypes (#M1..#M8 Real Satellite Maps, #D1..#D10 Forensic Dossiers & Biometrics, #P1..#P6 1990s Press & Curfew, and `cinema_full`) in pure Python (Pillow + NumPy) producing clean 1920x1080 frames.
   - `renderer.py`: Standalone scene renderer capable of rendering frames and sequences to file or memory.
   - `semantic_router.py`: `VoxSemanticRouter` with comprehensive bilingual (Korean / Vietnamese) regex patterns, keyword scoring, and priority scoring for all 24 archetypes. Implement sliding window anti-repetition mechanism (tracks last 3 beats with recency penalty and sibling variant rotation within semantic clusters).
2. Connect `VoxSemanticRouter` to:
   - `documentary/visuals.py`: Tag each visual beat on `channel-e544a64b7c` with its resolved `scene_archetype`.
   - `documentary/edit.py`: Pass `scene_archetype` into Remotion / scene render context.
   - `documentary/prompts.py`: Incorporate True Crime archetype guidance for AI agent planning.
   - `services/editing_dna_service.py`: Update `forensic_noir` editing preset to include the complete 24-archetype catalog and preserve strict isolation to `channel-e544a64b7c`.
3. Verification:
   - Run `python -m py_compile` on all modified Python files to ensure zero syntax errors.
   - Run a quick test script to confirm imports and basic routing functionality.
   - Do NOT kill, stop, or restart any running processes on ports 8000, 8878, 8890, 8900.

Write your complete handoff report to:
`B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\worker_m1\handoff.md`
Update your `progress.md` with timestamps and send a completion message when done.
