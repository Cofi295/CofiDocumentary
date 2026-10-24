# Handoff Report: Frontend UI/UX & Client-Side State Architecture Survey

**Agent**: `teamwork_preview_explorer_survey_1`  
**Working Directory**: `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\teamwork_preview_explorer_survey_1`  
**Date**: 2026-10-18T19:55:00Z  
**Type**: Hard Handoff (Investigation & Survey Complete)

---

## 1. Observation

### 1.1 State Leakage & Background Mutation in Step 00 (`#jobForm`)
In `static/app.js` (lines 3315–3343):
```javascript
3315: $$('#jobForm input[name="ai_media_mode"]').forEach(input => input.addEventListener("change", syncCreateStyleToActiveJob));
3316: $("#createAiStyleMode")?.addEventListener("change", () => {
3317:   updateCreateStyleFields();
3318:   syncCreateStyleToActiveJob();
3319: });
3320: $("#createAiStylePreset")?.addEventListener("change", () => {
3321:   const modeEl = $("#createAiStyleMode");
3322:   if (modeEl && $("#createAiStylePreset")?.value) {
3323:     modeEl.value = "preset";
3324:   }
3325:   updateCreateStyleFields();
3326:   syncCreateStyleToActiveJob();
3327: });
3328: $("#createAiCustomStyle")?.addEventListener("change", () => {
3329:   const modeEl = $("#createAiStyleMode");
3330:   if (modeEl && String($("#createAiCustomStyle")?.value || "").trim()) {
3331:     modeEl.value = "custom";
3332:   }
3333:   updateCreateStyleFields();
3334:   syncCreateStyleToActiveJob();
3335: });
3336: $("#createStyleReferenceInput")?.addEventListener("change", async () => {
3337:   if (state.selectedId) {
3338:     try {
3339:       await uploadCreateStyleReference(state.selectedId);
3340:       toast("Đã đồng bộ ảnh tham chiếu phong cách vào dự án hiện tại.");
3341:     } catch (_) {}
3342:   }
3343: });
```
And in `static/app.js` (lines 2785–2802):
```javascript
2785: async function syncCreateStyleToActiveJob() {
2786:   if (!state.selectedId) return;
2787:   const mode = String($("#createAiStyleMode")?.value || "auto");
2788:   const preset = String($("#createAiStylePreset")?.value || "");
2789:   const custom = String($("#createAiCustomStyle")?.value || "");
2790:   const mediaMode = String(document.querySelector('#jobForm input[name="ai_media_mode"]:checked')?.value || "mixed");
2791:   try {
2792:     await api(`/api/jobs/${encodeURIComponent(state.selectedId)}/ai-visual-settings`, {
2793:       method: "PATCH",
2794:       body: JSON.stringify({
2795:         style_mode: mode,
2796:         style_preset: preset,
2797:         custom_style: custom,
2798:         ai_media_mode: mediaMode,
2799:       }),
2800:     });
2801:   } catch (_) {}
2802: }
```

### 1.2 Channel Profile Field Bleeding in Step 00
In `static/app.js` (lines 2473–2514):
```javascript
2503:   const defaultBrief = profile.default_creative_brief || edDna.default_creative_brief;
2504:   if (defaultBrief && typeof defaultBrief === "object") {
2505:     applyCreativeProposalToCreateForm(
2506:       {
2507:         market,
2508:         target_duration_minutes: profile.default_duration_minutes || 30,
2509:         visual_strategy: vs || undefined,
2510:         creative_brief: defaultBrief,
2511:       },
2512:       { switchTab: false, silent: true }
2513:     );
2514:   }
```
And in `static/app.js` (lines 3065–3084):
```javascript
3065:   if (brief.narrative_angle && $("#createNarrativeAngle")) {
3066:     $("#createNarrativeAngle").value = humanizeCreativeKey("narrative_angles", brief.narrative_angle);
3067:   }
3068:   if (brief.writing_style && $("#createWritingStyle")) {
3069:     $("#createWritingStyle").value = humanizeCreativeKey("writing_styles", brief.writing_style);
3070:   }
3071:   if (brief.hook_archetype && $("#createHookArchetype")) {
3072:     $("#createHookArchetype").value = humanizeCreativeKey("hook_archetypes", brief.hook_archetype);
3073:   }
...
3078:   if (brief.opening_hook != null && String(brief.opening_hook).trim() && $("#createOpeningHookInput")) {
3079:     $("#createOpeningHookInput").value = String(brief.opening_hook).trim();
3080:   }
3081:   const rulesText = brief.custom_rules || proposal.notes || proposal.why_it_works || "";
3082:   if (rulesText && $("#createNotesTextarea")) {
3083:     $("#createNotesTextarea").value = String(rulesText).trim();
3084:   }
```
If `profile.default_creative_brief` is missing or has empty fields, the fields are never reset; the previously selected profile's values remain in the DOM inputs.

### 1.3 Step 0 Profile Mutation & Lack of Action Separation
In `static/app.js` (lines 2656–2665):
```javascript
2656:   const profileId = state.selectedChannelProfileId;
2657:   const url = profileId ? `/api/radar/channel-profiles/${encodeURIComponent(profileId)}` : "/api/radar/channel-profiles";
2658:   try {
...
2663:     const saved = await api(url, { method: profileId ? "PATCH" : "POST", body: JSON.stringify(payload) });
2664:     state.selectedChannelProfileId = saved.id;
```
And in `static/app.js` (lines 2127–2143):
```javascript
2127: $("#presetTrueCrimeCnBtn")?.addEventListener("click", () => {
2128:   const form = $("#channelProfileForm");
2129:   if (!form) return;
2130:   form.elements.label.value = TRUE_CRIME_CN_KR_PRESET.label;
...
2141:   updateChannelProfileFormMode(currentChannelProfile());
2142:   toast("Đã nạp bộ quy chuẩn: Hồ sơ Kênh True Crime Hình Sự Trung Quốc (KR - 30 Phút - Full AI). Bấm Lưu Hồ sơ DNA Kênh để áp dụng!");
2143: });
```
Notice `$("#presetTrueCrimeCnBtn")` writes into form elements but does NOT clear `state.selectedChannelProfileId`. Therefore, clicking Save sends a `PATCH` request to whatever profile was selected, silently overwriting it.

### 1.4 Data Inconsistencies in Storage
- File `data/channel_profiles.json`:
  - `channel-aa913eb90d` (line 4): missing `default_creative_brief`, `editorial_dna`, `editing_dna`.
  - `channel-f6ec4dfff3` (line 399): missing `default_creative_brief`, `editorial_dna`, `editing_dna`.
  - `channel-1e24de3ab5` (line 653): missing `default_creative_brief`, `editorial_dna`, `editing_dna`.
  - `channel-e544a64b7c` (line 1170): has `editorial_dna` and `default_creative_brief`, but lacks structured `editing_dna`.
- File `data/jobs/*/job.json`:
  - `20261018-223750-3aecfbcd/job.json:179`: `"channel_profile_id": null` (notes state `@판세의이면` -> `channel-1e24de3ab5`).
  - `20261017-164519-fd65f7e1/job.json:179`: `"channel_profile_id": null` (Lao Rongzhi -> `channel-e544a64b7c`).
  - None of the 4 jobs contain `editing_dna`.

### 1.5 Layout Ergonomics at 1280px (Chat Dock Open)
- File `static/styles.css:6362-6375`: `.seo-clean-hub` only collapses to 1 column at `@media (max-width: 1024px)`. At 1280px with chat open (content width = 692px), `.seo-clean-hub` remains a 2-column grid (`~339px` per column).
- File `static/styles.css:182-184`: `.inline-fields { display: flex; gap: 7px; margin-bottom: 10px; }` has no `flex-wrap: wrap;`. In `#marketScanForm` (5 fields) and `#channelProfileForm` (4 fields), inputs squish or overflow horizontally at 692px.
- File `static/styles.css:6519-6575`: `.channel-studio-top-actions` has `flex-wrap: nowrap !important;`. The switcher `#globalProjectSelect` (`clamp(170px, 19vw, 265px)`) plus 3 action buttons take ~557px, squeezing `.channel-studio-page-copy` to 135px.

---

## 2. Logic Chain

1. **Step 00 to Active Job Mutation**:
   - `Observation 1.1`: `$$('#jobForm input[name="ai_media_mode"]').forEach(...)` and `#createAiStyleMode`, `#createAiStylePreset`, `#createAiCustomStyle`, `#createStyleReferenceInput` are directly hooked to `syncCreateStyleToActiveJob()`.
   - `Observation 1.1`: `syncCreateStyleToActiveJob()` performs an unprompted `PATCH /api/jobs/{state.selectedId}/ai-visual-settings`.
   - *Inference*: Modifying draft settings in Step 00 silently mutates the currently selected active project in the background, directly violating Requirement R2 & AC2.

2. **Step 00 Channel Profile Field Bleeding**:
   - `Observation 1.2`: `applySelectedProfileToCreateStep()` only invokes `applyCreativeProposalToCreateForm()` if `profile.default_creative_brief` is present.
   - `Observation 1.2`: `applyCreativeProposalToCreateForm()` only overwrites DOM inputs if the incoming brief field is truthy.
   - `Observation 1.4`: Profiles `channel-1e24de3ab5`, `channel-aa913eb90d`, and `channel-f6ec4dfff3` lack `default_creative_brief`.
   - *Inference*: When switching from `channel-e544a64b7c` to any of these profiles, the fields (`narrative_angle`, `writing_style`, `hook_archetype`, `editing_archetypes`, `opening_hook`, `notes`) are never cleared, causing complete data bleed between profiles.

3. **Step 0 Overwriting Channel Profiles**:
   - `Observation 1.3`: `#saveChannelProfileBtn` sends `PATCH` if `state.selectedChannelProfileId` is set.
   - `Observation 1.3`: Clicking `#presetTrueCrimeCnBtn` writes preset strings into the form but preserves `state.selectedChannelProfileId`.
   - `Observation 1.3`: There is no "Clone Profile" or "Update Current Profile" button separation.
   - *Inference*: Users who load presets or edit profile fields while an existing profile is selected accidentally overwrite that profile on save.

4. **Storage Disconnections**:
   - `Observation 1.4`: Jobs `20261018-223750-3aecfbcd` and `20261017-164519-fd65f7e1` have `channel_profile_id: null`.
   - `Observation 1.4`: No profiles or jobs possess an `editing_dna` object.
   - *Inference*: Requirement AC2 and AC3 mandate backfilling these records with complete, accurate, non-null `channel_profile_id`, `visual_strategy`, `default_creative_brief`, and `editing_dna`.

5. **Layout Breakpoints under Chat Expansion**:
   - `Observation 1.5`: At 1280px viewport width with chat dock open, available content width is 692px.
   - `Observation 1.5`: `.seo-clean-hub` and `.inline-fields` do not adapt to `body.global-chat-open`.
   - *Inference*: Adding `body.global-chat-open` responsive rules and `flex-wrap: wrap` is required to eliminate layout collisions and squishing at 1280px.

---

## 3. Caveats

- **No Source Code Mutations Made**: In strict adherence to Explorer read-only rules, no production source files (`app.py`, `service.py`, `static/*.js`, `static/styles.css`) were edited. All proposals are documented in `survey_report.md` and this handoff.
- **Backend Schema Constraints**: Adding `editing_dna` and `self_learning_memory` to channel profiles and jobs will require updating Pydantic models (`ChannelProfileRequest`, `CreateJobRequest`) in `app.py` and `service.py`.

---

## 4. Conclusion

The frontend survey is complete. The exact mechanisms causing project mutation (`syncCreateStyleToActiveJob`), profile field bleeding (`applyCreativeProposalToCreateForm`), and profile overwriting (`#saveChannelProfileBtn` with `#presetTrueCrimeCnBtn`) have been pinpointed with exact file lines and DOM selectors. Layout collisions at 1280px have been mapped. Storage records requiring backfilling have been identified.

All findings, DOM selectors, state variables, and actionable recommendations are compiled in:
`B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\teamwork_preview_explorer_survey_1\survey_report.md`

---

## 5. Verification Method

To independently verify these findings:
1. **Verify State Leak in Step 00**:
   - Inspect `static/app.js:2785-2802` and `static/app.js:3315-3343`.
   - Notice `input[name="ai_media_mode"]`, `#createAiStyleMode`, `#createAiStylePreset`, `#createAiCustomStyle` trigger `PATCH /api/jobs/${state.selectedId}/ai-visual-settings`.
2. **Verify Field Bleed in Step 00**:
   - Inspect `static/app.js:2473-2514` and `3065-3084`.
   - Notice `applyCreativeProposalToCreateForm` contains no `reset` calls.
3. **Verify Profile Overwrite in Step 0**:
   - Inspect `static/app.js:2127-2143` and `2656-2674`.
   - Notice `#presetTrueCrimeCnBtn` does not clear `state.selectedChannelProfileId`.
4. **Verify Storage Inconsistencies**:
   - Inspect `data/jobs/20261018-223750-3aecfbcd/job.json` and `data/jobs/20261017-164519-fd65f7e1/job.json`. Verify line 179 has `"channel_profile_id": null`.
   - Inspect `data/channel_profiles.json`. Verify `channel-aa913eb90d`, `channel-f6ec4dfff3`, and `channel-1e24de3ab5` lack `default_creative_brief`.
5. **Verify Layout Rules**:
   - Inspect `static/styles.css:6362-6375`. Verify `.seo-clean-hub` only media-queries `@media (max-width: 1024px)`.
   - Inspect `static/styles.css:182-184`. Verify `.inline-fields` lacks `flex-wrap: wrap`.
