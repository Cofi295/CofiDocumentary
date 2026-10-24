# Handoff Report — Backend Survey & Isolation Audit

**Agent**: teamwork_preview_explorer_survey_2  
**Recipient**: Orchestrator (5aa18375-8f2e-479e-b627-f1d6f5283a45) / Downstream Implementation Agents  
**Target Directory**: `B:\ALL_TOOLS\CofiDocumentary`  
**Reference File**: `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\teamwork_preview_explorer_survey_2\survey_report.md`

---

## 1. Observation

1. **Storage Persistence**:
   - `B:\ALL_TOOLS\CofiDocumentary\data\channel_profiles.json`: Contains JSON object `{"profiles": [...]}` with exactly 4 profiles (`channel-aa913eb90d`, `channel-f6ec4dfff3`, `channel-1e24de3ab5`, `channel-e544a64b7c`).
   - `B:\ALL_TOOLS\CofiDocumentary\data\jobs/`: Contains exactly 4 job directories with `job.json`:
     * `20261018-223750-3aecfbcd/job.json`
     * `20261017-164519-fd65f7e1/job.json`
     * `20261017-003022-ecb75736/job.json`
     * `20261015-014818-f0fdc122/job.json`
   - `B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db`: 255,623,168 bytes SQLite database with 15 tables (`scans`, `channels`, `videos`, `video_snapshots`, `niches`, `my_channels`, `launch_plans`, `plan_items`, `today_queue`, etc.). CofiDocumentary accesses it via HTTP `RadarClient` (`http://127.0.0.1:8775`).
   - No `radar.db` file exists in `B:\ALL_TOOLS\CofiDocumentary\data/`.

2. **Cross-Job Mutation Bug in Step 00 Draft Form (`static/app.js`)**:
   - Lines 2785–2802:
     ```javascript
     async function syncCreateStyleToActiveJob() {
       if (!state.selectedId) return;
       const mode = String($("#createAiStyleMode")?.value || "auto");
       const preset = String($("#createAiStylePreset")?.value || "");
       const custom = String($("#createAiCustomStyle")?.value || "");
       const mediaMode = String(document.querySelector('#jobForm input[name="ai_media_mode"]:checked')?.value || "mixed");
       try {
         await api(`/api/jobs/${encodeURIComponent(state.selectedId)}/ai-visual-settings`, {
           method: "PATCH",
           body: JSON.stringify({
             style_mode: mode,
             style_preset: preset,
             custom_style: custom,
             ai_media_mode: mediaMode,
           }),
         });
       } catch (_) {}
     }
     ```
   - Lines 3315, 3318, 3326, 3334:
     ```javascript
     $$('#jobForm input[name="ai_media_mode"]').forEach(input => input.addEventListener("change", syncCreateStyleToActiveJob));
     $("#createAiStyleMode")?.addEventListener("change", () => { updateCreateStyleFields(); syncCreateStyleToActiveJob(); });
     $("#createAiStylePreset")?.addEventListener("change", () => { ... syncCreateStyleToActiveJob(); });
     $("#createAiCustomStyle")?.addEventListener("change", () => { ... syncCreateStyleToActiveJob(); });
     ```
   - Lines 3336–3342:
     ```javascript
     $("#createStyleReferenceInput")?.addEventListener("change", async () => {
       if (state.selectedId) {
         try {
           await uploadCreateStyleReference(state.selectedId);
           toast("Đã đồng bộ ảnh tham chiếu phong cách vào dự án hiện tại.");
         } catch (_) {}
       }
     });
     ```

3. **Field Bleed on Profile Switching (`static/app.js`)**:
   - Lines 2503–2514:
     ```javascript
     const defaultBrief = profile.default_creative_brief || edDna.default_creative_brief;
     if (defaultBrief && typeof defaultBrief === "object") {
       applyCreativeProposalToCreateForm(
         {
           market,
           target_duration_minutes: profile.default_duration_minutes || 30,
           visual_strategy: vs || undefined,
           creative_brief: defaultBrief,
         },
         { switchTab: false, silent: true }
       );
     }
     ```
   - When switching to a profile with no `default_creative_brief` (e.g., `channel-1e24de3ab5` or `channel-aa913eb90d`), `applyCreativeProposalToCreateForm` is never invoked, and previous profile brief inputs (`narrative_angle`, `writing_style`, `hook_archetype`, `editing_archetypes`, `custom_rules`, `opening_hook`) remain in `#jobForm`.

4. **Missing Data in Existing Storage**:
   - Profiles `channel-aa913eb90d`, `channel-f6ec4dfff3`, and `channel-1e24de3ab5` have `null` for `default_language`, `default_visual_strategy`, `default_ai_media_mode`, `dna_mode`, `voice_and_structure`, `allowed_topics`, `forbidden_topics`, `monetization_safety_policy`, and `default_creative_brief`.
   - All 4 profiles lack `editing_dna` and `self_learning_memory`.
   - Jobs `20261018-223750-3aecfbcd` and `20261017-164519-fd65f7e1` have `channel_profile_id: null` and `channel_profile_snapshot: {}`.
   - All 4 jobs lack `editing_dna`.

---

## 2. Logic Chain

1. **Premise**: Requirement R2 mandates strict isolation between Channel Profiles and Projects:
   - "Disconnect the 'Create New Project' draft form from the currently active project (`selectedId`) so modifying draft settings never mutates an existing running or completed project in the background."
   - "Switching between Channel Profiles in Step 0 or Step 00 must completely reset and populate 100% of form fields exclusively from the newly selected profile, leaving zero residual data."
2. **Deduction from Observations**:
   - As observed in `static/app.js:3315-3342`, changing style mode, preset, media mode, or reference image in `#jobForm` triggers `syncCreateStyleToActiveJob` and `uploadCreateStyleReference` which call `PATCH /api/jobs/{selectedId}/ai-visual-settings`. This directly causes background mutation of the active project.
   - In `static/app.js:2503-2514`, profile switching only writes fields if `defaultBrief` exists on the target profile. When switching to profiles without a creative brief, `#jobForm` elements retain the previous profile's values, directly causing residual field bleed.
   - In `app.py:1041-1050`, updating a profile always uses `PATCH /api/radar/channel-profiles/{profile_id}`. There is no `clone` route or distinction between "Save as New" and "Update", meaning preset application or editing an existing profile risks overwriting it.
   - In `data/channel_profiles.json` and `data/jobs/`, orphaned jobs (`20261018-223750-3aecfbcd`, `20261017-164519-fd65f7e1`) and incomplete channel profiles (`channel-1e24de3ab5`, `channel-f6ec4dfff3`, `channel-aa913eb90d`) lack required metadata (`channel_profile_id`, `editing_dna`, `default_creative_brief`, `self_learning_memory`), directly failing AC2 and R6.

---

## 3. Caveats

1. `B:\ALL_TOOLS\CofiRadar` runs as an external microservice; its SQLite database `cofi-radar.db` stores raw crawler scans, public YouTube metrics, and launch plans. CofiDocumentary consumes it through REST API calls. We must NOT modify `cofi-radar.db` schema directly unless required by CofiRadar's own contract.
2. In `data/jobs/20261015-014818-f0fdc122`, this was a YouTube Short (`#shorts` in title) with 27 workspace files; its `creative_brief` was omitted at creation time and must be backfilled based on its Three Gorges Dam disaster topic.
3. Tests run with `python -m pytest tests/...` on Windows should use `--basetemp=.pytest_tmp` to avoid temp directory access issues in `%TEMP%`.

---

## 4. Conclusion

1. **Isolation Architecture**:
   - Cross-project mutation must be severed by removing `syncCreateStyleToActiveJob` and `uploadCreateStyleReference(state.selectedId)` from `#jobForm` event handlers in `static/app.js`.
   - Profile switching must reset all brief fields prior to populating new values.
   - Step 0 must provide explicit actions: "Tạo Hồ Sơ Mới" (`POST /api/radar/channel-profiles`), "Nhân Bản Hồ Sơ" (`POST /api/radar/channel-profiles/{id}/clone`), and "Cập Nhật Hồ Sơ Hiện Tại" (`PATCH /api/radar/channel-profiles/{id}`).
2. **Data Model Extensions**:
   - Add `editing_dna` and `self_learning_memory` to `ChannelProfileRequest`, `CreateJobRequest`, `channel_profiles.json`, and `job.json`.
   - Add endpoints: `POST /api/jobs/{job_id}/lock-edit-dna`, `GET/POST /api/radar/channel-profiles/{profile_id}/self-learning`, `GET /api/radar/channel-profiles/{profile_id}`, `POST /api/radar/channel-profiles/{profile_id}/clone`, and `GET /api/jobs/{job_id}/policy-guardrails`.
3. **Data Backfill**:
   - Execute an idempotent migration script `backfill_profiles_and_jobs.py` that backs up files, backfills all 4 channel profiles with complete DNA/editing_dna/briefs, links orphaned jobs to their authentic profile IDs, and attaches non-null snapshots and editing DNA.

---

## 5. Verification Method

1. **Inspect Survey Report**:
   - Verify comprehensive findings in `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\teamwork_preview_explorer_survey_2\survey_report.md`.
2. **Verify Storage Persistence**:
   - Run: `python -c "import json; data=json.load(open('data/channel_profiles.json', encoding='utf-8')); print(len(data.get('profiles', [])))"` -> Outputs `4`.
   - Run: `python -c "import glob; print(len(glob.glob('data/jobs/*/job.json')))"` -> Outputs `4`.
3. **Run Regression Tests**:
   - Run: `python -m pytest tests/test_store.py --basetemp=.pytest_tmp` -> 4 passed.
   - Run: `python -m pytest tests/test_channel_profiles.py --basetemp=.pytest_tmp` -> 19 passed, 2 existing assertion differences documented.
