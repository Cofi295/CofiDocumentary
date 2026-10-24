# Project: CofiDocumentary True Crime Vox & Satellite Engine + UI/UX Overhaul

## Architecture
- **Vox & Real Satellite Engine Subpackage (`documentary/vox_engine/`)**:
  - `archetypes.py`: Definitions and compositing functions for 24 True Crime investigative archetypes (#M1..#M8 Real Satellite Maps, #D1..#D10 Forensic Dossiers & Biometrics, #P1..#P6 1990s Press & Curfew, and `cinema_full`).
  - `gis_cache.py`: Watermark-free Esri World Imagery (Z6, Z9, Z14, Z16) multi-scale tile loader, Web Mercator projection math (`deg2num`, `lonlat_to_plate_px`, `crop_map_camera`), and NumPy shaders (thermal/infrared inversion). Reads from `b:\ALL_TOOLS\CofiBlenderStudio\vox_gis_cache\`.
  - `typography.py`: Multi-tier CJK/Hangul/Vietnamese font cascade (`Malgun Gothic` -> `Microsoft YaHei` -> `Arial Unicode`) with bounding-box collision prevention and zero tofu (`□`) guarantee.
  - `renderer.py`: Pure Python Pillow + NumPy 1920x1080 frame compositor and rawvideo RGB pipeline.
  - `semantic_router.py`: Voice narration / SRT semantic intent analyzer with bilingual (Korean/Vietnamese) trigger lexicons, regex intent parsers, and a 3-beat sliding window anti-repetition mechanism.
- **Backend Pipeline Integration**:
  - `documentary/edit.py` & `documentary/visuals.py`: Intercept beat planning to assign granular `scene_archetype`.
  - `documentary/prompts.py`: Incorporate archetype guidance for AI agent planning.
  - `services/editing_dna_service.py`: Update `forensic_noir` editing preset to reference the 24 archetypes.
  - Gated strictly to `channel-e544a64b7c` (`특급수배록` / `true_crime_noir_ai` / `forensic_noir`).
- **Frontend & Tab 07 UI/UX**:
  - `static/index.html`: Restructure `#seoWorkspace` with maximized 16:9 Thumbnail Canvas workbench at the top and 5 collapsible Accordion drawers (`<details class="saas-seo-accordion">`) below for SEO packaging.
  - `static/styles.css`: 3-layer design tokens (Primitive -> Semantic -> Component), high-usability dark SaaS theme, button states, spacing scales, copy feedback animations.
  - `static/thumbnail_studio.js` & `static/app.js`: Connect accordion toggles, maintain all DOM selector contracts, add robust 1-click clipboard copy handlers with visual confirmation.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 24 True Crime Archetype Catalog | Implement #M1..#M8, #D1..#D10, #P1..#P6, cinema_full compositors | M1 | Survey 1 |
| 2 | Multi-Scale Satellite GIS Loader | Z6/Z9/Z14/Z16 Esri World Imagery loading and Web Mercator coordinate projections | M1 | Survey 1 |
| 3 | Tofu-Proof Font Cascade | Malgun Gothic + Microsoft YaHei + Arial Unicode font fallback cascade | M1 | Survey 1 |
| 4 | Semantic Voice-Narration Router | Bilingual Korean/Vietnamese regex intent parser matching voice/SRT to archetypes | M1 | Survey 2 |
| 5 | Anti-Repetition Sliding Window | 3-beat history tracking with recency penalty and sibling variant rotation | M1 | Survey 2 |
| 6 | True Crime Channel Profile Isolation | Strict gating to channel-e544a64b7c, zero bleed to non-crime profiles | M1 | Survey 2 |
| 7 | Tab 07 Top Maximized Thumbnail Canvas | Interactive 16:9 canvas at top of Tab 07 with variant switcher, safe zones, inspector | M2 | Survey 3 |
| 8 | Tab 07 Bottom Collapsible SEO Accordions | <details> collapsible drawers for Titles, Description, Tags, Hashtags | M2 | Survey 3 |
| 9 | 1-Click Clipboard Copy Actions | Streamlined copy buttons with visual copied confirmation badges | M2 | Survey 3 |
| 10 | App-Wide SaaS Design Tokens & Polish | Unified colors, surfaces, typography, spacing, badge pills in styles.css | M2 | Survey 3 |
| 11 | Semantic Router Programmatic Test | Test suite with 10+ diverse Korean/Vietnamese voice narration test cases | M3 | Original Request AC |
| 12 | 1920x1080 Frame Test-Rendering | Programmatic verification test generating valid frames with real tiles & zero tofu | M3 | Original Request AC |
| 13 | Syntax & Process Safety Checks | node --check, python -m py_compile, verification of ports 8000, 8878, 8890, 8900 | M3 | Original Request AC |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Voice-Driven Vox & Satellite Engine Integration | `documentary/vox_engine/`, `services/editing_dna_service.py`, `documentary/edit.py`, `documentary/visuals.py`, `documentary/prompts.py` | none | IN_PROGRESS |
| M2 | Tab 07 Redesign & App-Wide UI/UX Polish | `static/index.html`, `static/styles.css`, `static/thumbnail_studio.js`, `static/app.js` | none | IN_PROGRESS |
| M3 | Comprehensive E2E Verification & Test Suite | `tests/test_vox_semantic_router.py`, `tests/test_vox_scene_renderer.py`, non-destructive validation | M1, M2 | PLANNED |

## Code Layout
- `documentary/vox_engine/`: Dedicated engine subpackage
  - `__init__.py`
  - `archetypes.py`: Compositing and rendering functions for archetypes
  - `gis_cache.py`: Satellite plate loader and coordinate projections
  - `typography.py`: Font manager and fallback cascade
  - `renderer.py`: Standalone 1920x1080 frame renderer
  - `semantic_router.py`: Bilingual voice intent parser and anti-repetition router
- `services/editing_dna_service.py`: Channel editing DNA and True Crime preset mapping
- `documentary/visuals.py` & `documentary/edit.py`: Scene archetype assignment
- `static/index.html`: Tab 07 markup restructure
- `static/styles.css`: Design tokens and accordion styling
- `static/thumbnail_studio.js`: Canvas studio layout and 1-click copy logic
- `tests/`: Automated verification test suites
  - `tests/test_vox_semantic_router.py`
  - `tests/test_vox_scene_renderer.py`

## Interface Contracts
### `VoxSemanticRouter` ↔ `VisualsCoordinator` / `EditCoordinator`
- `VoxSemanticRouter.select_archetype(beat_text: str, language: str = "ko", context: Optional[dict] = None) -> ArchetypeSelectionResult`
  - Returns: `ArchetypeSelectionResult(archetype_id: str, label: str, confidence: float, trigger_keywords: list[str], visual_shell: str)`
- `VoxSceneRenderer.render_frame(archetype_id: str, data: dict, output_path: str) -> bool`
  - Inputs: `archetype_id` (e.g. `"#M1"`, `"#D4"`), `data` (title, subtitle, coordinates, plates, evidence items), `output_path` (PNG/JPEG)
  - Guarantees: 1920x1080 RGB, zero missing glyphs, valid file output.
