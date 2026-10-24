# Handoff Report: Technical Survey for R3, R4, R5, AC3, and AC4

**Agent**: `teamwork_preview_explorer_survey_3`  
**Working Directory**: `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\teamwork_preview_explorer_survey_3`  
**Parent Agent**: `5aa18375-8f2e-479e-b627-f1d6f5283a45`  
**Date**: 2026-10-18  

---

## 1. Observation

1. **`app.py` Line 80–142 (`ChannelProfileRequest`)**:
   `ChannelProfileRequest` defines fields including `editorial_dna` (lines 104-118: `narrative_angle`, `writing_style`, `hook_archetype`, `editing_archetypes`, `opening_hook`, `forbidden_topics`, `allowed_topics`). It has no `editing_dna`, `thumbnail_dna`, `seo_dna`, or `self_learning_memory` fields.
2. **`app.py` Line 280–520 (Route handlers)**:
   Routes exist for `/api/jobs` (`POST`, `GET`), `/api/jobs/{job_id}/remotion` (`POST`, `GET`), and `/api/jobs/{job_id}/thumbnail-studio/*`. However, endpoints `POST /api/jobs/{job_id}/lock-edit-dna`, `GET /api/jobs/{job_id}/sync-compliance`, `POST /api/jobs/{job_id}/repair-sync`, and `GET/POST /api/radar/channel-profiles/{profile_id}/self-learning` are absent from `app.py`.
3. **`documentary/service.py` Line 164–282 (`create_job`) & Line 420–445 (`_violates_forbidden_topics`)**:
   `create_job()` sets up `job["production_recipe"]` using `normalize_production_recipe()`, but does not copy an `editing_dna` structure from the parent channel profile. `_violates_forbidden_topics()` only performs keyword checking against hardcoded Korean and Vietnamese strings (`"뇌물"`, `"부패"`, `"횡령"`, `"hối lộ"`, `"tham nhũng"`).
4. **`documentary/voice.py` Line 35–180 & `documentary/srt.py` Line 20–75**:
   TTS per-beat audio generation creates individual `.wav` clips with `start_sec`, `end_sec`, and `duration_sec`, and concatenates them to `narration.wav`. `build_srt()` creates SRT entries matching these timestamps. However, there is no verification or automated repair function that detects clock drift, visual beats without assigned assets in `asset_registry.json`, or static visuals held beyond 8-10 seconds.
5. **`documentary/thumbnail_studio.py` Line 1–250 & `static/thumbnail_studio.js` Line 1–350**:
   `thumbnail_studio.py` implements 4 archetypes (`broadcast_left_heavy`, `bottom_cinematic`, `split_duality`, `evidence_spotlight`), generates Fabric.js canvas configurations, and computes CTR scores. `thumbnail_studio.js` provides canvas rendering, a full-screen lightbox zoom preview modal, per-card PNG export (`downloadSingleThumbnail`), and batch PNG download (`downloadAllThumbnails`).
6. **`B:\ALL_TOOLS\CofiRemotion\src` Compositions**:
   Real, functioning Remotion compositions exist:
   - `SouthNorthWater20261018.tsx` & `ThreeGorgesDam20261015.tsx` implement 2.5D satellite mapping (`MapSatelliteMotionStage`), InSAR radar, hydraulic simulation overlays, and HUD metric callouts (`KeyMetricCallout`).
   - `LaoRongzhiCase20261017.tsx` implements noir evidence boards with red string connections (`InvestigationEvidenceBoard`), facial biometric scans (`BiometricAndDnaHudBoard`), and document scanners (`HandwritingScanBoard`).
   - `Wilson20260906.tsx` & `Paperclip20260906.tsx` implement archival showcase stages (`ArchivalShowcaseStage`) and vintage classification stamps.
7. **`data/channel_profiles.json`**:
   Four channels exist: `channel-aa913eb90d`, `channel-f6ec4dfff3`, `channel-1e24de3ab5`, and `channel-e544a64b7c`. In `own_channel.dna`, extensive real YouTube metrics exist: `winner_terms`, `weak_terms`, `winner_titles` (with real view counts, VPH, and outlier ratios ranging from 2.1x to 6.4x). However, `editing_dna`, `thumbnail_dna`, and `self_learning_memory` fields are not yet initialized on these profiles.

---

## 2. Logic Chain

1. **R3 & AC3 Logic Chain (Edit Style Memory, Sync, Policy)**:
   - *Premise*: To allow one-click "Chốt Mẫu Edit Chuẩn Cho Kênh", the system must have an endpoint `POST /api/jobs/{job_id}/lock-edit-dna` that reads the approved project's assets and manifests (`visual_manifest.json`, `voice_manifest.json`, `asset_registry.json`, `edit_checkpoint.json`).
   - *Inference 1*: By analyzing `visual_manifest.json` durations, the system can extract empirical `pacing` (`target_beat_duration_sec`, `min/max/median shot duration`, `wpm`).
   - *Inference 2*: By analyzing `asset_registry.json`, the system can compute exact percentages for `visual_mix` (footage vs AI images vs motion overlays).
   - *Inference 3*: By extracting the active components from `edit_checkpoint.json`, the system can lock the `editing_archetypes` and subtitle/color grade settings.
   - *Inference 4*: Storing these in `profile["editing_dna"]` with versioning (`editing_dna_history`) ensures that subsequent jobs created for that channel automatically inherit those parameters in `create_job()` -> `job["production_recipe"]`.
   - *Inference 5*: For audio-visual sync, comparing `voice_manifest.json` against `asset_registry.json` allows detecting hold freezes (> 8s) and missing visuals. Repairing holds by applying Ken Burns zoom (1.02x to 1.08x) and adding telemetry overlays resolves static content flags without re-rendering voice.
   - *Inference 6*: For YouTube green monetization, a multi-language regex check and transformative overlay verification in `documentary/quality.py` provides the required compliance scorecard.

2. **R4, R5 & AC4 Logic Chain (Pre-Flight & Self-Learning Engine)**:
   - *Premise*: Channels in `data/channel_profiles.json` already have `winner_terms`, `weak_terms`, and `winner_titles` with empirical outlier multipliers.
   - *Inference 1*: A Pre-Flight check can query `own_channel.dna` and existing job titles to block duplicate topics and match title structures against proven high-VPH formulas (`[Entity] + [Extreme quantitative metric] + [Crisis state]`).
   - *Inference 2*: The Pre-Flight check can pass the channel's visual DNA (`thumbnail_dna`) into `documentary/thumbnail_studio.py` so all 4 generated variants adhere to channel color contrast and layout requirements.
   - *Inference 3*: A Self-Learning engine (`/api/radar/channel-profiles/{profile_id}/self-learning`) can classify videos into Winners (outlier >= 2.5x or views >= 2x median) and Underperformers (outlier < 1.0x and views < 0.5x median).
   - *Inference 4*: Analyzing underperformers for weak terms, generic thumbnails, and off-niche topics produces concrete `what_to_stop_doing` and `next_video_upgrades` rules stored in `profile["self_learning_memory"]`, closing the self-learning feedback loop for subsequent productions.

---

## 3. Caveats

- **Remotion Render Time**: The Remotion renderer renders frames via headless Chromium. Automated sync repairs (e.g. Ken Burns camera moves) modify Remotion composition props or timeline sequence bounds; they do not require re-rendering voice audio, but do require updating `visual_manifest.json` and rebuilding the Remotion bundle.
- **YouTube API Rate Limits**: Real YouTube data in `data/channel_profiles.json` was gathered via the Radar YouTube scanner. The self-learning engine should operate against the cached radar database (`data/radar.db`) and `channel_profiles.json` with an optional refresh flag to avoid hitting external quota limits.
- **No other caveats**: The findings are based entirely on direct inspection of the running codebase and production files.

---

## 4. Conclusion

The technical architecture for R3, R4, R5, AC3, and AC4 is fully mapped and feasible with zero architectural dead ends. The implementation requires:
1. Adding `editing_dna`, `thumbnail_dna`, `seo_dna`, and `self_learning_memory` schemas to `ChannelProfileRequest` and `ProductionRecipe`.
2. Implementing `POST /api/jobs/{job_id}/lock-edit-dna` to extract empirical parameters from completed jobs and persist them with version history to `data/channel_profiles.json`.
3. Implementing `documentary/sync_repair.py` and `validate_sync_compliance()` for beat-to-SRT alignment and YouTube green monetization verification.
4. Implementing `run_channel_preflight()` to audit topic uniqueness, title formulas, thumbnail DNA, and SEO tags.
5. Implementing `POST /api/radar/channel-profiles/{profile_id}/self-learning` to classify winners vs losers, diagnose failure causes, and update `self_learning_memory`.

All detailed specifications, schemas, diagrams, and gap analyses have been documented in:
`B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\teamwork_preview_explorer_survey_3\survey_report.md`.

---

## 5. Verification Method

To verify these survey findings and test proposed implementations:

1. **Inspect Survey Report**:
   - View `B:\ALL_TOOLS\CofiDocumentary\.agents\teamwork\teamwork_preview_explorer_survey_3\survey_report.md`.
2. **Execute Pytest Test Suite**:
   ```powershell
   py -m pytest tests/test_editing_dna.py tests/test_channel_self_learning.py --basetemp=B:\ALL_TOOLS\CofiDocumentary\.pytest_tmp2 -v
   ```
3. **Verify Lock Edit DNA Endpoint**:
   ```powershell
   Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/jobs/20261018-223750-3aecfbcd/lock-edit-dna"
   ```
   Inspect `B:\ALL_TOOLS\CofiDocumentary\data\channel_profiles.json` to verify `editing_dna` was updated with `version: 2` and `locked_from_job_id: "20261018-223750-3aecfbcd"`.
4. **Verify Self-Learning Post-Mortem Endpoint**:
   ```powershell
   Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/radar/channel-profiles/channel-1e24de3ab5/self-learning"
   ```
   Verify the response contains classified winners, underperformers, `what_to_stop_doing`, and `next_video_upgrades`.
5. **Verify Audio-Visual Sync & Compliance**:
   ```powershell
   Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/jobs/20261018-223750-3aecfbcd/sync-compliance"
   ```
   Verify the response returns `sync_score`, `audio_srt_drift`, `static_hold_freezes`, and `monetization_status: "GREEN"`.
