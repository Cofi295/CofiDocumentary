# Handoff Report: CofiDocumentary Backend & Routing Architecture

**Agent**: Survey Explorer 2 (`teamwork_preview_explorer`)  
**Working Directory**: `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\explorer_survey_2`  
**Deliverable**: `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\explorer_survey_2\survey_backend_routing.md`  
**Type**: Hard Handoff (Investigation Complete)  
**Date**: 2026-10-23  

---

## 1. Observation

1. **Channel Profile Structure (`B:\ALL_TOOLS\CofiDocumentary\data\channel_profiles.json`)**:
   - `channel-e544a64b7c` is defined at lines 4–1787 with `id: "channel-e544a64b7c"`, `label: "🇰🇷 Hồ sơ Kênh True Crime Hình Sự Trung Quốc (KR · 100% Full AI)"`, `market: "KR"`, and `title: "특급수배록"`.
   - `default_creative_brief.editing_archetypes` (lines 894–899, 1113–1118) currently lists:
     `["Hồ sơ điều tra & Sơ đồ mạng lưới", "Phóng to chi tiết & Quét tài liệu", "Chia đôi màn hình đối chiếu", "Bản đồ 2.5D & Camera vệ tinh"]`.
   - Non-crime profiles exist: `channel-1e24de3ab5` (Chinese Megaprojects `판세의 이면`, lines 1851+) and `channel-f6ec4dfff3` (The First Family Vault, lines 1789–1850).

2. **Editing DNA Service (`B:\ALL_TOOLS\CofiDocumentary\services\editing_dna_service.py`)**:
   - Lines 112–172 define `BUILTIN_EDITING_PRESETS["forensic_noir"]` with `preset_id: "forensic_noir"`, target beat duration 5.5s, `visual_mix: {"footage": 0.0, "ai": 0.85, "motion": 0.15, "preferred_routing": "full_ai"}`, and legacy editing archetypes `["forensic_case_board_red_string", "document_scanner_telemetry", "noir_chapter_transition", "biometric_dna_hud", "forensic_map_route_board"]`.
   - Lines 305–478 and 479–555 provide `extract_editing_dna_from_job(job_id)` and `lock_job_edit_dna_to_channel(job_id, notes)`.

3. **Planning & Visual Prompts (`B:\ALL_TOOLS\CofiDocumentary\documentary\prompts.py`)**:
   - Lines 452–545 (`build_phase_prompt(job, "plan", ...)`) instruct the agent to generate `research.md`, `script.md`, and `visual_manifest.json` with beats containing `story_group`, `narration_text`, `purpose`, `visual_type`, `source_priority`, `visual_description`, `framing_motion_intent`, `on_screen_text`, and `sound_notes`.
   - Lines 770–820 (`build_edit_batch_prompt(...)`) build batched edit instructions for Remotion.
   - Neither prompt builder currently defines or assigns granular True Crime scene archetypes.

4. **Visual Refinement / STP (`B:\ALL_TOOLS\CofiDocumentary\documentary\visuals.py`)**:
   - Lines 250–385 (`VisualsCoordinator.run(...)`) split narration into semantic sub-beats (`B001-V01`, `B001-V02`) and route them via `_route_for(...)` to `"ai_visual"` or `"footage"`.
   - It writes `visual_manifest.json` and `visual_prompts.json` without assigning a `scene_archetype`.

5. **Channel Profile Classification (`B:\ALL_TOOLS\CofiDocumentary\documentary\service.py`)**:
   - Lines 7530–7547 define `_is_true_crime_profile(cls, profile)`:
     ```python
     def _is_true_crime_profile(cls, profile: dict[str, Any]) -> bool:
         pid = str(profile.get("id") or "")
         if pid == "channel-e544a64b7c":
             return True
         if pid in {"channel-1e24de3ab5", "channel-aa913eb90d", "channel-f6ec4dfff3"}:
             return False
     ```

6. **True Crime Reference Engine in `CofiBlenderStudio`**:
   - `B:\ALL_TOOLS\CofiBlenderStudio\vox_editorial_artist.py` defines core archetypes: `#D1` (Scene 01), `#M1` (Scene 02), `#D2` (Scene 03), `#M2` (Scene 04), `#D3` (Scene 05), `#M3` (Scene 06), `#P1` (Scene 07), `#P2` (Scene 08), `#M4` (Scene 09), and `render_fullscreen_cinema_shot` (`cinema_full`).
   - `B:\ALL_TOOLS\CofiBlenderStudio\vox_archetype_expansion.py` defines expanded archetypes: `#M5` (2.5D tilted satellite slab), `#M6` (split dual satellite), `#M7` (night-ops infrared satellite), `#D4` (Y-STR DNA lightbox), `#D5` (aluminum clipboard interrogation), `#D6` (wanted warrant & sketch), `#D9` (microscope 14-point minutiae), `#P3` (1990s TV broadcast).
   - `B:\ALL_TOOLS\CofiBlenderStudio\vox_gis_cache\` contains 9 satellite and carto plates: `plate_baiyin_campus_sat_z16.png` (2048x1280), `plate_baiyin_city_sat_z14.png`, `plate_baiyin_lanzhou_sat_z9.png`, `plate_gansu_sat_z6.png`, etc.
   - All renderers are standalone 2D/2.5D PIL/NumPy compositors that output 1920x1080 frames without requiring Blender execution.

7. **System Fonts & Python Environment**:
   - `C:\Windows\Fonts\malgunbd.ttf` and `malgun.ttf` exist and are functional.
   - Python 3.14.6 with pytest 8.4.2 is verified at `C:\Users\koing\AppData\Local\python\bin\python.exe`.

---

## 2. Logic Chain

1. **Premise 1**: From Observation 1 & 5, `channel-e544a64b7c` is explicitly identified as the sole True Crime profile, while `channel-1e24de3ab5` and `channel-f6ec4dfff3` are non-crime profiles.
2. **Premise 2**: From Observation 3 & 4, `visual_manifest.json` currently assigns only high-level routes (`ai_visual`, `footage`) but lacks granular archetype tags (`#M1..#M8`, `#D1..#D10`, `#P1..#P6`, `cinema_full`).
3. **Premise 3**: From Observation 6, the 17+ tactical True Crime archetypes in `CofiBlenderStudio` are fully decoupled from 3D DCC software and execute purely via PIL/NumPy compositing using cached Esri satellite plates.
4. **Deduction 1**: Introducing a standalone `VoxSemanticRouter` inside `documentary/vox_router.py` can parse spoken narration (both Korean and Vietnamese) during Step 03 (`visuals.py`) and tag each refined beat with its matching archetype.
5. **Deduction 2**: To prevent repetitive visual shells when consecutive beats address the same evidence (e.g. multiple fingerprint or satellite mentions), the router must maintain a sliding history window (last 3-4 beats) and apply recency penalties (-80 pts on beat `i-1`, -40 pts on beat `i-2`) while rotating between sibling variants in the same semantic cluster.
6. **Deduction 3**: By checking `job.channel_profile_id == "channel-e544a64b7c"` or `_is_true_crime_profile(profile)`, non-crime channels are guaranteed to bypass the Vox True Crime router and retain their existing engineering/archival behaviors.
7. **Deduction 4**: Test coverage in `tests/test_vox_semantic_router.py` and `tests/test_vox_scene_renderer.py` will programmatically certify semantic routing across 11 diverse test sentences, anti-repetition rules, channel isolation, and 1920x1080 satellite frame rendering.

---

## 3. Caveats

1. **Live Processes**: The running services on port 8000, 8878, 8890, and 8900 must remain running undisturbed. All test commands and proposed modules run non-destructively.
2. **GIS Cache Pathing**: `B:\ALL_TOOLS\CofiBlenderStudio\vox_gis_cache` contains plates for Baiyin/Gansu. Future cases set in other provinces will reuse these plates as regional archetype templates or pull additional Esri World Imagery tiles if coordinates change.
3. **Read-Only Investigation**: As an explorer subagent, no application source code was modified during this survey. Complete specifications and blueprints are provided for implementers.

---

## 4. Conclusion

The CofiDocumentary backend is fully capable of supporting voice-driven semantic archetype routing and tactile satellite rendering for `channel-e544a64b7c`. The integration requires:
1. `documentary/vox_router.py`: Implements `VoxSemanticRouter` with bilingual trigger lexicons, scoring, anti-repetition sliding window, and channel gating.
2. `documentary/vox_renderer.py`: Bridges PIL/NumPy rendering logic and the satellite tile cache from `CofiBlenderStudio`.
3. Interception in `documentary/visuals.py`: Stamps `scene_archetype` into `visual_manifest.json`.
4. Preset update in `services/editing_dna_service.py`: Expands `forensic_noir` editing archetypes.
5. Two new test suites: `tests/test_vox_semantic_router.py` and `tests/test_vox_scene_renderer.py`.

---

## 5. Verification Method

1. **Inspect Deliverable**:
   View `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\explorer_survey_2\survey_backend_routing.md` to verify all required sections and architectural analyses are present.
2. **Verify Python & Pytest Accessibility**:
   Run:
   ```powershell
   C:\Users\koing\AppData\Local\python\bin\python.exe -m pytest --version
   ```
   Expect: `pytest 8.4.2`.
3. **Verify GIS Plate Integrity**:
   Run:
   ```powershell
   C:\Users\koing\AppData\Local\python\bin\python.exe -c "from PIL import Image; img = Image.open(r'B:\ALL_TOOLS\CofiBlenderStudio\vox_gis_cache\plate_baiyin_campus_sat_z16.png'); assert img.size == (2048, 1280); print('GIS plate check passed!')"
   ```
   Expect: `GIS plate check passed!`.
4. **Invalidation Conditions**:
   - If non-crime channels (`channel-1e24de3ab5`) are routed to `#D1..#D10` or `#M1..#M8`.
   - If consecutive beats with identical keywords produce the exact same archetype without variant swapping.
   - If rendered frames fail to match `1920x1080` or drop Korean characters (`□`).
