# Handoff Report — Milestone M3: Adversarial Challenge of Thumbnail Studio REST APIs

**Agent**: `challenger_m3_2` (Empirical Challenger, critic, specialist)  
**Parent**: `orchestrator_2` (`a13450b0-84a5-4e72-ae6f-8fd9f0ed17c4`)  
**Verdict**: **FAIL** (3 empirical findings, 2 blocking requirement violations)

---

## 1. Observation

### Observation 1: `ab_test_metadata.json` is missing the `title` field
- In `documentary/thumbnail_studio.py:1782-1796`:
```python
    metadata = {
        "job_id": job_id,
        "exported_at": _now_iso(),
        "format": "YouTube_Studio_Test_And_Compare_Pack",
        "experiment_type": "3_thumbnail_ab_test",
        "recommended_duration_days": 14,
        "instructions": (
            "Hướng dẫn tải lên YouTube Studio:\n"
            "1. Vào YouTube Studio -> Chi tiết video -> Hình thu nhỏ.\n"
            "2. Bấm 'Thử nghiệm và so sánh' (Test & Compare).\n"
            "3. Tải lên 3 ảnh: variant_a.jpg, variant_b.jpg, variant_c.jpg.\n"
            "4. YouTube sẽ tự động phân phối đều lưu lượng và hiển thị biến thể chiến thắng sau 14 ngày."
        ),
        "variants": manifest_variants,
    }
```
- Empirical verification command:
```powershell
& "C:\Users\koing\AppData\Local\python\bin\python.exe" -c "from documentary.thumbnail_studio import export_thumbnail_ab_pack; from pathlib import Path; import json, tempfile; tmp = Path(tempfile.mkdtemp()); job = {'id': 't1', 'title': 'Test Title'}; res = export_thumbnail_ab_pack('t1', tmp, None, job); meta = json.loads(Path(res['metadata_path']).read_text('utf-8')); print('Has title?:', 'title' in meta)"
```
- Verbatim tool output:
```
Has title?: False
```
- Violates explicit mandate: *"Verify that all 3 image files are valid JPEGs (>0 bytes) and ab_test_metadata.json has title, hook types, and predicted CTRs."*

---

### Observation 2: Choosing `variant_b` in `select_thumbnail_winner` silently falls back to Variant A (`v1`)
- In `documentary/thumbnail_studio.py:1845-1849`:
```python
    target_variant = next((v for v in variants if isinstance(v, dict) and v.get("id") == variant_id), None)
    if not target_variant and variants:
        target_variant = variants[0]
        variant_id = str(target_variant.get("id") or "v1")
```
- When a client or user sends `{"variant_id": "variant_b"}` (as named in `ab_test_pack.zip`'s `variant_b.jpg` and explicitly cited in the user dispatch prompt: *"Choosing a variant (e.g. variant_b) sets active_variant_id and copies/exports thumbnail.jpg and media/thumbnails/thumbnail.jpg"*), `variant_id == "variant_b"` fails to match internal IDs (`['v1', 'v2', 'v3']`).
- Because of `if not target_variant and variants: target_variant = variants[0]`, it silently selects `v1` (Variant A) instead of Variant B (`v2`).
- Empirical test output in `tests/test_adversarial_thumbnail_ab_studio.py::test_select_winner_variant_id_alias_reveals_silent_fallback_to_v1`:
```python
resp = app_client.post(f"/api/jobs/{job_id}/thumbnail-studio/select-winner", json={"variant_id": "variant_b"})
# Returns 200 with active_variant_id == 'v1' instead of 'v2' / 'variant_b'
```

---

### Observation 3: Missing `thumbnail_design.json` causes `export-ab-pack` to export 0 variants and `select-winner` to crash
- In `documentary/service.py:9289`:
```python
    def export_thumbnail_ab_pack(self, job_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        job = self.get_job(job_id)
        workspace = Path(job["workspace"]).resolve()
        design = self._read_json_dict(workspace / "thumbnail_design.json")
        return export_thumbnail_ab_pack(job_id, workspace, design=design, job=job)
```
- When `thumbnail_design.json` does not exist on disk, `_read_json_dict` returns `{}`.
- In `documentary/thumbnail_studio.py:1727`:
```python
    if design is None:
        ...
        if not design:
            design = build_default_thumbnail_design(job_id, workspace, job or {})
```
- Because `design` is `{}` (not `None`), `if design is None:` evaluates to `False`. The fallback to `build_default_thumbnail_design` is completely skipped.
- `export_thumbnail_ab_pack` proceeds with `variants = []`, generating an empty ZIP with 0 image variants (`exported_count: 0`).
- `select_thumbnail_winner` proceeds with `variants = []` and crashes with HTTP 400: `ValueError: Không tìm thấy biến thể v1 trong thiết kế.`

---

### Observation 4: Working Features Verified Empirically
- `POST /api/jobs/{job_id}/thumbnail-studio/export-ab-pack` (when design exists):
  * Returns HTTP 200, valid `zip_path`, `zip_url`.
  * Archive unpacks into `variant_a.jpg`, `variant_b.jpg`, `variant_c.jpg`, `ab_test_metadata.json`.
  * Images verified with PIL: valid JPEG format, RGB mode, 1280x720 resolution, >0 bytes.
  * Verified hook types (`curiosity_paradox`, `character_evidence`, `confrontation_contrast`) and predicted CTR metrics.
- `POST /api/jobs/{job_id}/thumbnail-studio/select-winner` (when internal ID `v2` is passed):
  * Returns HTTP 200 with `active_variant_id: "v2"`.
  * Exports `thumbnail.jpg`, `media/thumbnails/thumbnail.jpg`, `media/thumbnail/exports/thumbnail_v2.jpg`.
  * Updates `thumbnail_design.json` with `active_variant_id: "v2"`.
- `POST /api/jobs/{job_id}/lock-thumbnail-dna`:
  * Returns HTTP 200 with `ok: True`.
  * Extracts palette, typography, layout archetype from active design.
  * Increments channel profile version $V \rightarrow V+1$.
  * Appends previous version $V$ to `thumbnail_dna_history` with `archived_at` and `locked_from_job_id`.
  * Updates `job.json` and `input.json` snapshots.
- R4 Non-Destructive Preservation:
  * Active job `20261019-185102-31983814` verified: all 35 workspace files intact, identical byte lengths (`thumbnail.jpg` 239,852 bytes, `thumbnail_design.json` 17,365 bytes, `input.json` 15,077 bytes).
  * `data/radar.db` verified: 0 bytes, untouched.

---

## 2. Logic Chain

1. **Step 1 (From Observation 1)**: The prompt mandate explicitly requires: *"Verify that all 3 image files are valid JPEGs (>0 bytes) and ab_test_metadata.json has title, hook types, and predicted CTRs."*
   - Inspection of `metadata` in `documentary/thumbnail_studio.py:1782` shows keys: `['job_id', 'exported_at', 'format', 'experiment_type', 'recommended_duration_days', 'instructions', 'variants']`. Neither the root dictionary nor the variant list contains the video/job `title`.
   - Inference: The YouTube Studio export pack metadata is missing required identifying context for the video title.

2. **Step 2 (From Observation 2)**: The prompt mandate states: *"Choosing a variant (e.g. variant_b) sets active_variant_id and copies/exports thumbnail.jpg and media/thumbnails/thumbnail.jpg"*.
   - In `documentary/thumbnail_studio.py:1845`, the code only tests `v.get("id") == variant_id`. It does not recognize letter aliases like `"variant_b"`, `"B"`, or `"b"`.
   - When a caller sends `"variant_b"`, `next(...)` returns `None`. The fallback `target_variant = variants[0]` executes, setting `active_variant_id = "v1"`.
   - Inference: A client attempting to choose Variant B unintentionally causes Variant A to be locked in as the winning thumbnail.

3. **Step 3 (From Observation 3)**: In `documentary/service.py:9289` & `9297`, `_read_json_dict` returns `{}` if `thumbnail_design.json` is missing.
   - Passing `{}` into `export_thumbnail_ab_pack` and `select_thumbnail_winner` bypasses the `if design is None:` check in `thumbnail_studio.py`.
   - Inference: New jobs or jobs where Step 07 has not yet been opened fail silently with 0-variant exports or 400 errors instead of auto-synthesizing the channel's default variants.

4. **Step 4 (Conclusion)**: Although happy-path execution with internal IDs passes unit tests, the missing `title` in metadata and the silent wrong-variant selection when using variant names violate core requirements.
   - Therefore, the verdict is **FAIL**.

---

## 3. Caveats

- When using internal IDs (e.g. `{"variant_id": "v2"}`), `select_thumbnail_winner` works correctly.
- Active running job `20261019-185102-31983814` was protected and remained 100% unharmed throughout all tests.
- Channel profiles and database integrity were fully preserved.

---

## 4. Conclusion

**Verdict**: **FAIL**

### Summary of Blocking Deficiencies:
1. **Missing `title` in `ab_test_metadata.json`** (`documentary/thumbnail_studio.py:1782`).
2. **Silent Wrong-Variant Selection on `variant_b` alias** (`documentary/thumbnail_studio.py:1845`): Caller requesting `"variant_b"` gets Variant A (`"v1"`) selected instead of Variant B (`"v2"`).
3. **Empty Design Bypass** (`documentary/service.py:9289, 9297`): Missing `thumbnail_design.json` results in 0 variants exported.

### Recommended Fixes for Worker:
1. In `documentary/thumbnail_studio.py:1782`:
   Add `"title": str((job or {}).get("title") or (design or {}).get("title") or "")` to `metadata`.
2. In `documentary/thumbnail_studio.py:1845`:
   Add alias normalization in `select_thumbnail_winner`:
   ```python
   variant_id_clean = variant_id.strip().lower()
   # Map variant_a/b/c/d or a/b/c/d to v1/v2/v3/v4 if not matched directly
   alias_map = {"variant_a": "v1", "a": "v1", "variant_b": "v2", "b": "v2", "variant_c": "v3", "c": "v3", "variant_d": "v4", "d": "v4"}
   normalized_id = alias_map.get(variant_id_clean, variant_id)
   target_variant = next((v for v in variants if isinstance(v, dict) and (v.get("id") == normalized_id or v.get("id") == variant_id or str(v.get("letter", "")).lower() == variant_id_clean)), None)
   ```
3. In `documentary/service.py:9289` & `9297`:
   Pass `design = self._read_json_dict(workspace / "thumbnail_design.json") or None` so that an empty/missing file triggers `build_default_thumbnail_design`.

---

## 5. Verification Method

To verify these findings empirically:

1. Run the challenger adversarial test suite:
```powershell
& "C:\Users\koing\AppData\Local\python\bin\python.exe" -m pytest tests/test_adversarial_thumbnail_ab_studio.py -v
```
Expected: 9 passed, confirming the exact reproduction of Findings 1, 2, and 3, plus passing tests for valid ZIP unpack, PIL JPEG validation, and lock-thumbnail-dna versioning.

2. Run one-line proof of missing title in `ab_test_metadata.json`:
```powershell
& "C:\Users\koing\AppData\Local\python\bin\python.exe" -c "from documentary.thumbnail_studio import export_thumbnail_ab_pack; from pathlib import Path; import json, tempfile; tmp = Path(tempfile.mkdtemp()); job = {'id': 't1', 'title': 'Test Title'}; res = export_thumbnail_ab_pack('t1', tmp, None, job); meta = json.loads(Path(res['metadata_path']).read_text('utf-8')); print('title key in metadata:', 'title' in meta)"
```
Expected: Prints `False`.

3. Run one-line proof of silent wrong-variant selection on `"variant_b"`:
```powershell
& "C:\Users\koing\AppData\Local\python\bin\python.exe" -c "from documentary.thumbnail_studio import build_default_thumbnail_design, select_thumbnail_winner; from pathlib import Path; import tempfile; tmp = Path(tempfile.mkdtemp()); res = select_thumbnail_winner('t1', tmp, 'variant_b', None, {'id': 't1'}); print('Requested: variant_b -> Selected:', res['active_variant_id'])"
```
Expected: Prints `Requested: variant_b -> Selected: v1`.

4. Check R4 preservation:
```powershell
powershell -Command "Get-Item 'workspaces/20261019-185102-31983814/thumbnail.jpg', 'data/radar.db' | Select-Object Name, Length, LastWriteTime"
```
Expected: Both files intact (`thumbnail.jpg` 239,852 bytes, `radar.db` 0 bytes).
