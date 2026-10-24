# Adversarial Challenge & Stress Report: Backend Vox & Satellite Engine

**Verdict**: **REQUEST_CHANGES**  
**Working Directory**: `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\challenger_backend`  
**Test Harness**: `B:\ALL_TOOLS\CofiDocumentary\tests\test_vox_engine_stress.py` (23 empirical tests)

---

## 1. Observation

### Area 1: Semantic Router Stress
- Tested inputs: empty string `""`, whitespace only, `None`, numeric types, emoji string (`"🕵️‍♂️💥🚨🔍📍📜⚖️🩸😱🚔"`), numeric coordinates (`"LAT 36°33'03\"N · LON 104°08'52\"E · ALT 1720m · GPS FIX 1988-05-26 14:30:00"`), Korean internet slang (`"ㄹㅇ 갓겜 ㄷㄷ 킹정 존버 쌉파서블 뇌절 ㅋㅋㅋ ㅠㅠ ㄹㅇ 실화냐 대박 레전드"`), Vietnamese slang (`"vl vcl ảo ma canada vcl u là trời khum biết dc chán ghê á trời ơi đỉnh chóp"`), mixed multi-lingual sentences (Korean + Vietnamese + Simplified Chinese + Russian + English), and a 500-word run-on text.
- Tool command: `python -m pytest tests/test_vox_engine_stress.py -k TestArea1SemanticRouterStress -v`
- Result: **7/7 PASSED**. All extreme inputs were safely handled without exceptions, returning valid dictionary objects with registered archetypes (`cinema_full`, `#D2`, `#D4`, `#M2`, etc.) and sub-5ms response times with zero catastrophic regex backtracking.

### Area 2: Anti-Repetition Stress (Vulnerability 1 Confirmed)
- File path: `documentary/vox_engine/semantic_router.py:287-311`
- When feeding 10 consecutive identical sentences where only a single archetype matches (or without a competing sibling):
  - Sentence `"국립과학수사연구원은 Y-염색체 DNA 족보 가계도를 분석했다"` (Y-STR DNA):
    - Produced sequence: `['#D4', '#D4', 'cinema_full', '#D4', '#D4', 'cinema_full', '#D4', '#D4', 'cinema_full', '#D4']`
    - Beat 1 emitted `#D4` (score: 126.0)
    - Beat 2 emitted `#D4` again (score: 21.0)!
  - Sentence `"경찰은 바이인 제4중학교 매점을 급습하여 용의자를 체포했다"` (Rooftop store):
    - Produced sequence: `['#M1', '#M1', 'cinema_full', '#M1', '#M1', 'cinema_full', '#M1', '#M1', 'cinema_full', '#M1']`
    - Beat 1 emitted `#M1` (score: 122.0)
    - Beat 2 emitted `#M1` again (score: 17.0)!
  - Sentence `"해가 지면 야간 통제와 통금이 시작되고 적외선 순찰이 강화되었다"` (Curfew):
    - Produced sequence: `['#M7', '#M7', 'cinema_full', '#M7', '#M7', 'cinema_full', '#M7', '#M7', 'cinema_full', '#M7']`
    - Beat 1 emitted `#M7` (score: 125.0)
    - Beat 2 emitted `#M7` again (score: 20.0)!
  - Sentence `"당시 1990년대 방송 뉴스 특보 화면이다"` (CRT Broadcast):
    - Produced sequence: `['#P3', '#P3', 'cinema_full', '#P3', '#P3', 'cinema_full', '#P3', '#P3', 'cinema_full', '#P3']`
  - Sentence `"공안부는 1급 지명수배령을 내리고 20만 위안의 현상금을 걸었다"` (Wanted Warrant):
    - Produced sequence: `['#D6', '#D6', 'cinema_full', '#D6', '#D6', 'cinema_full', '#D6', '#D6', 'cinema_full', '#D6']`
  - Sentence `"법원은 피고인에게 사형을 선고하고 정치권리를 박탈했다"` (Court Verdict):
    - Produced sequence: `['#P6', '#P6', 'cinema_full', '#P6', 'cinema_full', '#P6', 'cinema_full', '#P6', 'cinema_full', '#P6']`
- Verbatim code causing defect (`semantic_router.py:287-309`):
  ```python
  base_score = float(rule["priority_score"]) # e.g. 96 for #D4
  if match_ko:
      base_score += 30.0                     # base_score = 126.0
  if match_vi:
      base_score += 25.0

  penalty = 0.0
  if history:
      if history[-1] == arch_id:
          penalty += 80.0                    # Immediate predecessor penalty: 80.0
      ...
      if self._same_cluster(history[-1], arch_id):
          penalty += 25.0                    # Cluster penalty: 25.0
  # Total penalty = 105.0
  final_score = max(0.0, base_score - penalty) # 126.0 - 105.0 = 21.0 > 0!
  ```
- Tool command: `python -m pytest tests/test_vox_engine_stress.py -k TestArea2AntiRepetitionStress -v`
- Result: **2/2 PASSED** (Both competing sibling rotation on fingerprint and single-match duplicate defect are empirically captured).

### Area 3: GIS Plate Loader Stress (Vulnerability 2 Confirmed)
- File path: `documentary/vox_engine/gis_cache.py:71-78`
- Tested:
  - Latitudes out of bounds: `lat=90.0`, `-90.0`, `95.0`, `-95.0`, `1000.0`, `-1000.0` -> `deg2num` returned non-NaN, non-inf floats.
  - Non-existent plate files: `_generate_fallback_plate` synthesized valid 2048x1280 RGB images with road/river procedural grids.
  - Non-existent GeoJSON files: `load_gis_json` returned valid fallback `FeatureCollection`.
  - NumPy thermal shader: `apply_infrared_thermal_shader` cleanly transformed all image inputs to 1920x1080 RGB slate-blue composites.
  - **Extreme zoom out / wide camera requests (`zoom_scale <= 0.1`)**:
    - Tool command: `python -c "from documentary.vox_engine.gis_cache import load_gis_plate, crop_map_camera; plate, meta = load_gis_plate('test'); crop_map_camera(plate, meta, 104.16, 36.54, zoom_scale=0.1)"`
    - Verbatim exception:
      ```
      PIL.Image.DecompressionBombError: Image size (207360000 pixels) exceeds limit of 178956970 pixels, could be decompression bomb DOS attack.
      ```
    - Cause: `crop_w = target_w / max(0.1, zoom_scale) = 1920 / 0.1 = 19200`, `crop_h = 1080 / 0.1 = 10800`.
      `plate_img.crop((int(x0), int(y0), int(x0 + crop_w), int(y0 + crop_h)))` allocates a `19200 x 10800` (207,360,000 pixel) crop buffer because `crop_w` and `crop_h` are never clamped to `plate_img.width` (2048) or `plate_img.height` (1280).

### Area 4: Typography Stress
- File paths: `documentary/vox_engine/typography.py` & `documentary/vox_engine/renderer.py`
- Tested glyph verification, CJK fallback cascade (`Malgun Gothic -> Microsoft YaHei -> Arial`), line balancing, and text drawing across:
  - Korean Hangul syllables (e.g. `백은시`, `연쇄살인사건`, `국립과학수사연구원`)
  - Vietnamese with full tone diacritics (e.g. `Đại án Bạch Ngân: Bắt giữ khẩn cấp nghi phạm số một Cao Thừa Dũng tại tiệm tạp hóa`)
  - Simplified Chinese ideographs (e.g. `白银市连环杀人案 嫌疑人 高承勇 公安 现场 勘查 提取指纹`)
  - Traditional Hanja ideographs (e.g. `白銀市 連環殺人案 嫌疑人 高承勇 現場 檢證 司法 審判`)
  - Numbers and special symbols: `№ 1988-1994-2002-2016 · 14-Point · 99.98% · [STR-DNA] · ★★★ §42`
- All 25 archetypes (`#M1..#M8`, `#D1..#D10`, `#P1..#P6`, `cinema_full`) were rendered with multilingual subtitles using `VoxSceneRenderer`.
- Tool command: `python -m pytest tests/test_vox_engine_stress.py -k TestArea4TypographyStress -v`
- Result: **5/5 PASSED**. Zero tofu boxes (`□`), zero text collisions, and all frames produced valid `1920x1080` RGB PIL images in pure Python under 250ms per frame.

### Area 5: Process and Port Hygiene
- Verified active listening TCP ports:
  - Port `8000`: PID `2988` (CofiDub) — `Listen`
  - Port `8878`: PID `28296` (CofiDocumentary) — `Listen`
  - Port `8890`: PID `10256` (CofiRemotion) — `Listen`
  - Port `8900`: PID `30768` (CofiBlenderStudio Python server) — `Listen`
- Background Blender daemon check:
  - Executed `Get-Process *blender*` -> 0 active blender processes found.
- Tool command: `python -m pytest tests/test_vox_engine_stress.py -k TestArea5ProcessAndPortHygiene -v`
- Result: **2/2 PASSED**.

---

## 2. Logic Chain

1. **Anti-Repetition Defect (Logic)**:
   - Observation 2 demonstrates that `VOX_ARCHETYPE_RULES` defines `priority_score` between 81 and 97.
   - When a Korean narration beat matches, `match_ko` adds `+30.0`, resulting in a `base_score` between `111.0` and `127.0`. (If Vietnamese matches too, `base_score` reaches `136.0` to `152.0`).
   - The anti-repetition mechanism in `semantic_router.py:297-308` subtracts `80.0` for `history[-1] == arch_id` and `25.0` for `self._same_cluster(history[-1], arch_id)`.
   - The total deduction on the immediate subsequent beat is strictly capped at `105.0`.
   - Therefore, `base_score - penalty` is strictly positive: `final_score = base_score - 105.0 >= +6.0` (up to `+47.0`).
   - When the narration does not match any other archetype rule (which occurs across `#D4`, `#M1`, `#M7`, `#P3`, `#D6`, `#P6`), the candidate list contains only the previous archetype with a positive score (`final_score > 0`).
   - Line 320 sorts candidates by score and picks `candidates[0]`, re-selecting the exact same archetype consecutively.
   - **Conclusion**: The router violates Requirement 2 and R1 of the specification by repeating identical visual archetypes back-to-back whenever single-match narration beats occur.

2. **GIS DecompressionBombError Defect (Logic)**:
   - Observation 3 demonstrates that `crop_map_camera` in `gis_cache.py:73-77` calculates `crop_w = target_w / max(0.1, zoom_scale)` and `crop_h = target_h / max(0.1, zoom_scale)`.
   - For any wide-angle or extreme zoom request where `zoom_scale <= 0.1` (or clamped to 0.1 when negative or 0.0), `crop_w = 19200` and `crop_h = 10800`.
   - The image is cropped using `plate_img.crop((int(x0), int(y0), int(x0 + crop_w), int(y0 + crop_h)))`.
   - Because `crop_w` and `crop_h` are not clamped to `plate_img.width` (2048) and `plate_img.height` (1280), Pillow allocates an uncompressed image of `19200 x 10800 = 207,360,000` pixels.
   - Pillow enforces `Image.MAX_IMAGE_PIXELS = 89,478,485`, and aborts with `PIL.Image.DecompressionBombError` whenever an operation requests `> 2 * MAX_IMAGE_PIXELS` (178,956,970 pixels).
   - `207,360,000 > 178,956,970`, causing an unhandled `DecompressionBombError` that crashes the server process.
   - **Conclusion**: The GIS Plate Loader fails on wide-angle/extreme zoom requests instead of producing valid images.

---

## 3. Caveats

- **No Code Modifications Made**: In accordance with the Review-Only constraint, no implementation files in `documentary/vox_engine/` were modified by this agent.
- **Test Harness Location**: The test harness was placed in `tests/test_vox_engine_stress.py` to conform to repository layout rules (`.agents/teamwork/` contains only metadata).
- **GPU Hardware Acceleration**: The engine's thermal and satellite compositing pipelines execute in pure Python (`PIL` + `numpy`), which was verified to run in ~50-250ms per 1080p frame without GPU or Blender daemons.

---

## 4. Conclusion & Required Changes

**Verdict**: **REQUEST_CHANGES**

The Vox & Satellite engine has excellent typography multi-script rendering, fast pure-Python compositing, zero external Blender dependencies, and clean process isolation. However, two concrete bugs must be addressed before approval:

### Concrete Actionable Fixes Required:

1. **Fix Anti-Repetition Immediate Suppression in `documentary/vox_engine/semantic_router.py`**:
   - The immediate predecessor penalty must fully suppress the previous archetype or rotate to a cluster sibling or fallback when `history[-1] == arch_id`.
   - Specifically, in `semantic_router.py:297-298`:
     Increase the immediate predecessor penalty from `80.0` to at least `160.0` (or `penalty += 200.0` or unconditionally disqualify `history[-1] == arch_id` if another valid choice or `cinema_full` is available), guaranteeing that `base_score - penalty <= 0.0`.
   - When all candidate scores drop to `<= 0.0`, the fallback logic (`line 315`) will cleanly fall back to `cinema_full` (or `#D2`), guaranteeing that the exact same archetype is NEVER emitted consecutively on back-to-back beats.

2. **Fix Crop Bounds Clamping in `documentary/vox_engine/gis_cache.py`**:
   - In `crop_map_camera` (`gis_cache.py:73-77`), clamp `crop_w` and `crop_h` to the plate dimensions:
     ```python
     target_w, target_h = out_size
     # Clamp zoom_scale minimum to prevent exceeding master plate dimensions
     min_zoom_w = target_w / float(plate_img.width)
     min_zoom_h = target_h / float(plate_img.height)
     safe_min_zoom = max(0.1, max(min_zoom_w, min_zoom_h))
     effective_zoom = max(safe_min_zoom, float(zoom_scale or 1.0))

     crop_w = min(float(plate_img.width), target_w / effective_zoom)
     crop_h = min(float(plate_img.height), target_h / effective_zoom)
     x0 = max(0.0, min(float(plate_img.width) - crop_w, cx - crop_w * 0.5))
     y0 = max(0.0, min(float(plate_img.height) - crop_h, cy - crop_h * 0.5))
     ```
   - This eliminates `DecompressionBombError` completely and guarantees that the crop box never exceeds the plate's physical dimensions.

---

## 5. Verification Method

To independently verify these findings, run the automated test suite in PowerShell:

```powershell
python -m pytest tests/test_vox_engine_stress.py -v
```

### Invalidation Conditions:
1. `test_single_match_consecutive_repetition_defect` passes only because it asserts the current duplicate behavior (`#D4 -> #D4`). Once the builder increases the penalty or rotates to siblings/fallback, that test will fail if updated to assert zero consecutive duplicates (`assert history[i] != history[i-1]`).
2. `test_crop_map_camera_decompression_bomb_vulnerability` asserts that `DecompressionBombError` is currently raised on `zoom_scale <= 0.1`. Once the builder clamps `crop_w` and `crop_h`, `crop_map_camera(plate, meta, 104.16, 36.54, zoom_scale=0.1)` will succeed and return a valid 1920x1080 RGB image.
