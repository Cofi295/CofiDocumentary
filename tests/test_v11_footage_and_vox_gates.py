from __future__ import annotations

import json
import shutil
from pathlib import Path
import pytest

from documentary.agent_manager import AgentManager
from documentary.critic_loops import audit_edit_timeline_and_screen
from documentary.edit_footage_fetcher import EditDirectFootageFetcher
from documentary.prompts import build_edit_chat_prompt, build_phase_prompt
from documentary.quality import evaluate_ypp_visual_role_mix, normalize_production_recipe
from services.editing_dna_service import EditingDnaService


def _director_v2_job(job_id: str = "20261102-v13-test") -> dict:
    return {
        "id": job_id,
        "language": "ko",
        "market": "KR",
        "channel_profile_id": "channel-kr-truecrime-director-v2",
        "visual_strategy": "edit_direct_footage",
        "editing_dna": {
            "preset_id": "forensic_noir_director_v2",
            "director_mode": "v2",
            "motion_text_engine": "FramelessCinemaTextBeat",
            "motion_text_module": "CofiRemotion/src/components/FramelessCinemaTextBeat.tsx",
            "visual_mix": {
                "footage": 0.54,
                "motion": 0.30,
                "ai": 0.16,
                "min_footage_floor": 0.50,
                "max_vox_scene_ratio": 0.28,
                "max_cinema_text_ratio": 0.16,
                "max_ai_reconstruction_ratio": 0.22,
                "zero_unrelated_broll": True,
            },
        },
    }


def test_director_v2_prompts_skill_and_profile_enforce_v13_composable_lego_dna(tmp_path: Path) -> None:
    job = _director_v2_job()
    plan_p = build_phase_prompt(job, "plan", tmp_path, tmp_path / "remotion")
    edit_p = build_phase_prompt(job, "edit", tmp_path, tmp_path / "remotion")

    for prompt_text in (plan_p, edit_p):
        assert "min_footage_floor = 0.50" in prompt_text
        assert "FramelessCinemaTextBeat" in prompt_text
        assert "CAUSAL_CHAIN" in prompt_text
        assert "SPLIT_PARADOX" in prompt_text
        assert "CRASH_TIMELINE" in prompt_text
        assert "min_footage_floor = 0.0" not in prompt_text
        assert "20%–32%" not in prompt_text
        assert "5-Archetype" not in prompt_text
        assert "5 Họ Toàn Khung" not in prompt_text

    assert "edit_footage_fetcher" in edit_p
    assert "VoxAtomicLegoProps" in edit_p
    assert "VoxVisualVerbGrammar" in edit_p
    assert "GeoJson3DMapStage" in edit_p
    assert "SplitParadoxShutter" in edit_p
    assert "LivePlungingChartCurve" in edit_p
    assert "RoughHandDrawnArrow" in edit_p

    # Verify EditingDnaService preset & normalize_production_recipe match V13 Composable Lego Grammar
    presets = EditingDnaService().get_presets()
    assert "forensic_noir_director_v2" in presets
    p_v2 = presets["forensic_noir_director_v2"]
    assert p_v2["version"] in (13, 23, 24)
    assert p_v2["motion_text_engine"] == "FramelessCinemaTextBeat"
    assert p_v2["visual_mix"]["min_footage_floor"] == 0.50
    assert p_v2["vox_composable_grammar"]["atomic_props_count"] in (25, 32)
    assert p_v2["vox_composable_grammar"]["visual_verbs_count"] == 18
    assert p_v2["vox_composable_grammar"]["camera_topologies_count"] == 8
    assert p_v2["vox_composable_grammar"]["verb_sliding_window"] == 5
    assert p_v2["vox_composable_grammar"]["max_monolithic_page_wrapper_uses"] == 3
    p_v2_dump = json.dumps(p_v2, ensure_ascii=False)
    assert "VoxNewsroomMotionText.tsx xoay vòng" not in p_v2_dump
    assert "5-Archetype" not in p_v2_dump
    assert "VOX_MOTION_JOURNALISM_5_ARCHETYPES" not in p_v2_dump

    edit_chat_p = build_edit_chat_prompt(job, tmp_path, tmp_path / "remotion", "B010 nhịp hơi chậm", [])
    assert any(tag in edit_chat_p for tag in ("Lock 100% to V13 `forensic_noir_director_v2`", "Lock 100% to V23 `forensic_noir_director_v2`", "Lock 100% to V24 `forensic_noir_director_v2`"))
    assert "Lock 100% to V11" not in edit_chat_p
    assert "rotated `VoxNewsroomMotionText.tsx`" not in edit_chat_p
    assert "STRICTLY FORBID paper `VoxNewsroomMotionText.tsx`" in edit_chat_p

    recipe = normalize_production_recipe(
        None,
        visual_strategy="edit_direct_footage",
        editing_dna=job["editing_dna"],
    )
    assert recipe["quality_contract"]["visual_routing_policy"] in (
        "vox_newsroom_v13_composable_lego_50pct_footage",
        "vox_newsroom_v23_vibe_motion_paper_collage_50pct_footage",
        "vox_newsroom_v24_tactile_editorial_desk_50pct_footage",
    )
    assert recipe["quality_contract"]["min_real_footage_ratio"] == 0.50
    assert recipe["quality_contract"]["max_cinema_text_ratio"] == 0.16
    assert recipe["quality_contract"]["max_monolithic_page_wrapper_uses"] == 3
    assert recipe["quality_contract"]["vox_verb_sliding_window"] == 5
    assert "FramelessCinemaTextBeat.tsx" in recipe["asset_rules"][0]

    # Verify AgentManager slices Section 1A cleanly for Director V2 without cross-profile or legacy V12 leaks
    repo_root = Path(__file__).resolve().parents[1]
    mgr = AgentManager(repo_root / "agents", repo_root / "skills")
    bound = mgr.resolve_bound_skills(
        "vox",
        target_language="ko",
        selected_job=job,
    )
    skill_bodies = "\n".join(s.get("excerpt") or "" for s in bound)
    assert "[skill digest truncated" not in skill_bodies
    assert "FramelessCinemaTextBeat.tsx" in skill_bodies
    assert "VoxAtomicLegoProps" in skill_bodies
    assert "VoxVisualVerbGrammar" in skill_bodies
    assert "CAUSAL_CHAIN" in skill_bodies
    assert "GeoJson3DMapStage" in skill_bodies
    assert "VoxTactileNewsPrimitives.tsx" not in skill_bodies
    assert "5-Archetype" not in skill_bodies
    assert "5 Họ Toàn Khung" not in skill_bodies

    # Verify channel_profiles.json Director V2 profile is cleanly upgraded to V13 with zero stale V12 5-Archetype residue
    profiles_path = repo_root / "data" / "channel_profiles.json"
    profiles_data = json.loads(profiles_path.read_text(encoding="utf-8"))
    prof_list = profiles_data["profiles"] if isinstance(profiles_data, dict) and "profiles" in profiles_data else profiles_data
    dir_v2 = next(p for p in prof_list if isinstance(p, dict) and p.get("id") == "channel-kr-truecrime-director-v2")
    assert dir_v2["editorial_dna"]["version"] >= 13
    assert dir_v2["editing_dna"]["version"] >= 13
    assert dir_v2["editing_dna"]["vox_composable_grammar"].get("atomic_props_count", 32) in (25, 32)
    dir_v2_dump = json.dumps(dir_v2, ensure_ascii=False)
    assert "5-Archetype" not in dir_v2_dump
    assert "5 Họ Toàn Khung" not in dir_v2_dump
    assert "5 họ toàn khung" not in dir_v2_dump
    assert "VOX_MOTION_JOURNALISM_5_ARCHETYPES" not in dir_v2_dump
    assert "VOX_CHINA_CRIME_NEWSROOM_5_ARCHETYPES" not in dir_v2_dump


def test_role_mix_gate_rejects_zero_footage_and_spoofed_missing_mp4s(tmp_path: Path) -> None:
    # 1. 0% real footage (like the broken Xie Renliang v10 cut) -> MUST RAISE RuntimeError
    with pytest.raises(RuntimeError, match="Real footage ratio"):
        evaluate_ypp_visual_role_mix(
            {
                "total_beats": 216,
                "real_footage_beats_count": 0,
                "vox_beats_count": 92,
                "cinema_text_beats_count": 46,
                "ai_reconstruction_beats_count": 78,
            },
            min_real_footage_ratio=0.50,
            max_vox_ratio=0.28,
            max_cinema_text_ratio=0.16,
            max_ai_reconstruction_ratio=0.22,
        )

    # 2. Over-stuffed VOX (>28%) even if footage passes -> MUST RAISE RuntimeError
    with pytest.raises(RuntimeError, match="VOX scene ratio"):
        evaluate_ypp_visual_role_mix(
            {
                "total_beats": 100,
                "real_footage_beats_count": 54,
                "vox_beats_count": 34,
                "cinema_text_beats_count": 6,
                "ai_reconstruction_beats_count": 6,
            },
            min_real_footage_ratio=0.50,
            max_vox_ratio=0.28,
            max_cinema_text_ratio=0.16,
            max_ai_reconstruction_ratio=0.22,
        )

    # 3. Spoofed manifest claiming 6/10 footage beats when .mp4 files do not exist on disk -> MUST RAISE
    ws = tmp_path / "ws"
    rem_job = tmp_path / "remotion" / "public" / "jobs" / "j1"
    ws.mkdir(parents=True)
    rem_job.mkdir(parents=True)
    with pytest.raises(RuntimeError, match="Real footage ratio"):
        evaluate_ypp_visual_role_mix(
            {
                "total_beats": 10,
                "real_footage_beats_count": 6,
                "vox_beats_count": 2,
                "cinema_text_beats_count": 1,
                "ai_reconstruction_beats_count": 1,
                "beats": [
                    {"beat_id": f"B{i:03d}", "visualRole": "REAL_FTG", "imageFile": f"jobs/j1/footage/S_F{i:03d}.mp4"}
                    for i in range(1, 7)
                ],
            },
            min_real_footage_ratio=0.50,
            max_vox_ratio=0.28,
            max_cinema_text_ratio=0.16,
            max_ai_reconstruction_ratio=0.22,
            workspace=ws,
            remotion_job_dir=rem_job,
        )

    # 4. Valid V13 >=50% real footage with real .mp4 files on disk -> PASSED
    ftg_dir = rem_job / "footage"
    ftg_dir.mkdir(parents=True)
    for i in range(1, 7):
        (ftg_dir / f"S_F{i:03d}.mp4").write_bytes(b"0" * 8192)
    passed = evaluate_ypp_visual_role_mix(
        {
            "total_beats": 10,
            "real_footage_beats_count": 6,
            "vox_beats_count": 2,
            "cinema_text_beats_count": 1,
            "ai_reconstruction_beats_count": 1,
            "beats": [
                {"beat_id": f"B{i:03d}", "visualRole": "REAL_FTG", "imageFile": f"jobs/j1/footage/S_F{i:03d}.mp4"}
                for i in range(1, 7)
            ],
        },
        min_real_footage_ratio=0.50,
        max_vox_ratio=0.28,
        max_cinema_text_ratio=0.16,
        max_ai_reconstruction_ratio=0.22,
        workspace=ws,
        remotion_job_dir=rem_job,
    )
    assert passed["status"] == "PASSED"
    assert passed["real_footage_ratio"] == 0.6


def test_edit_screening_blocks_monolithic_page_spam_verb_window_repeat_and_passes_v13_composable_lego(tmp_path: Path) -> None:
    job_id = "20261102-v13-test"
    job = _director_v2_job(job_id)
    ws = tmp_path / "ws"
    rem = tmp_path / "remotion"
    vox_dir = rem / "src" / "vox-studio" / "case-v13"
    vox_dir.mkdir(parents=True)
    ws.mkdir(parents=True)

    # Phase 1: Root composition importing forbidden VoxNewsroomMotionText + cookie-cutter scenes + fake 3-vertex GeoJSON
    (rem / "src" / "CaseComp.tsx").write_text(
        f"""// {job_id}
import {{ VoxRouter }} from './vox-studio/case-v13';
import {{ VoxNewsroomMotionText }} from './vox-studio/china-crime-newsroom/VoxNewsroomMotionText';
const DURATION_FRAMES = 300;
const outroBlackOpacity = 1;
export const CaseComp = () => <div style={{ background: '#000000' }}><VoxRouter /><VoxNewsroomMotionText /></div>;
""",
        encoding="utf-8",
    )

    cookie_scenes = "\n".join(
        f"""export const VoxScene{i:02d} = () => (
  <VoxCopyStandCameraRig>
    <EditorialFinancialLedger />
    <LivingArchive25DPlate plateAsset="jobs/{job_id}/ai/same_plate.jpg" />
    <OpticalGlassLoupe imageSrc="jobs/{job_id}/ai/same_plate.jpg" x={{1400}} y={{980}} />
    <FramelessEditorialCallout anchorX={{1160}} anchorY={{520}} />
  </VoxCopyStandCameraRig>
);"""
        for i in range(1, 9)
    )
    (vox_dir / "VoxScenes01to08.tsx").write_text(cookie_scenes, encoding="utf-8")

    (vox_dir / "voxGeoData.ts").write_text(
        """export const ROUTE = {
  type: 'LineString',
  coordinates: [[121.55, 29.87], [121.50, 30.50], [121.47, 31.23]],
};
""",
        encoding="utf-8",
    )

    (ws / "edit_manifest.json").write_text(
        json.dumps(
            {
                "total_beats": 10,
                "real_footage_beats_count": 0,
                "vox_beats_count": 6,
                "cinema_text_beats_count": 2,
                "ai_reconstruction_beats_count": 2,
                "beats": [{"beat_id": f"B{i:03d}", "visualRole": "VOX"} for i in range(1, 11)],
            }
        ),
        encoding="utf-8",
    )
    beats = [{"beat_id": f"B{i:03d}"} for i in range(1, 11)]
    rep = audit_edit_timeline_and_screen(job, ws, rem, beats)
    assert rep["status"] == "FAILED"
    assert rep["has_blocker"] is True
    issue_types = {iss["type"] for iss in rep["issues"]}
    assert "legacy_vox_primitive_leak" in issue_types
    assert "real_footage_floor_violation" in issue_types
    assert "vox_ratio_cap_exceeded" in issue_types
    assert "vox_template_monoculture" in issue_types
    assert "vox_callout_loupe_collision" in issue_types
    assert "vox_fake_geojson_polyline" in issue_types

    # Phase 2: Fix footage & GeoJSON & motion text, BUT repeat @voxVerb CAUSAL_CHAIN inside a 5-scene window -> MUST BLOCK
    (rem / "src" / "CaseComp.tsx").write_text(
        f"""// {job_id}
import {{ VoxRouter }} from './vox-studio/case-v13';
import {{ FramelessCinemaTextBeat }} from './components/FramelessCinemaTextBeat';
const DURATION_FRAMES = 300;
const outroBlackOpacity = 1;
export const CaseComp = () => <div style={{ background: '#000000' }}><VoxRouter /><FramelessCinemaTextBeat mode="stat_impact" headline="99.99%" /></div>;
""",
        encoding="utf-8",
    )
    pub_ftg = rem / "public" / "jobs" / job_id / "footage"
    pub_ftg.mkdir(parents=True)
    for i in range(1, 7):
        (pub_ftg / f"S_F{i:03d}.mp4").write_bytes(b"0" * 8192)
    coords_16 = ", ".join(f"[{121.55 - k * 0.01:.4f}, {29.87 + k * 0.08:.4f}]" for k in range(16))
    (vox_dir / "voxGeoData.ts").write_text(
        f"export const ROUTE = {{ type: 'LineString', coordinates: [{coords_16}] }};\n",
        encoding="utf-8",
    )
    (ws / "edit_manifest.json").write_text(
        json.dumps(
            {
                "total_beats": 10,
                "real_footage_beats_count": 6,
                "vox_beats_count": 2,
                "cinema_text_beats_count": 1,
                "ai_reconstruction_beats_count": 1,
                "beats": [
                    {"beat_id": f"B{i:03d}", "visualRole": "REAL_FTG", "imageFile": f"jobs/{job_id}/footage/S_F{i:03d}.mp4"}
                    for i in range(1, 7)
                ]
                + [
                    {"beat_id": "B007", "visualRole": "VOX", "voxSceneId": "VOX_01"},
                    {"beat_id": "B008", "visualRole": "VOX", "voxSceneId": "VOX_02"},
                    {"beat_id": "B009", "visualRole": "CINEMA_TEXT", "cinemaTextId": "CT_01"},
                    {"beat_id": "B010", "visualRole": "AI_4D", "imageFile": f"jobs/{job_id}/ai/B010_ai_keyframe.jpg"},
                ],
            }
        ),
        encoding="utf-8",
    )

    repeated_verb_scenes = """
/** @voxVerb CAUSAL_CHAIN */
export const VoxScene01 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('diagonal_pursuit', [{x:1200,y:800},{x:1900,y:1200}]) as any}><PinnedCutoutPhoto src="p1.jpg" /><RoughHandDrawnArrow /></VoxCopyStandCameraRig>);
/** @voxVerb SPLIT_PARADOX */
export const VoxScene02 = () => (<SplitParadoxShutter leftLabel="허위 진술" rightLabel="실제 항로" />);
/** @voxVerb CRASH_TIMELINE */
export const VoxScene03 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('timeline_axis_track', [{x:1100,y:900},{x:2200,y:1050}]) as any}><LivePlungingChartCurve /></VoxCopyStandCameraRig>);
/** @voxVerb CAUSAL_CHAIN */
export const VoxScene04 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('vertical_cascade', [{x:1800,y:700},{x:1820,y:1500}]) as any}><ForensicEvidenceTag /><RoughHandDrawnArrow /></VoxCopyStandCameraRig>);
/** @voxVerb NETWORK_GRAPH */
export const VoxScene05 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('orbital_3d_glide', [{x:1500,y:900},{x:2100,y:1300}]) as any}><NetworkPortraitNode /><NetworkGraphLink /></VoxCopyStandCameraRig>);
"""
    (vox_dir / "VoxScenes01to08.tsx").write_text(repeated_verb_scenes, encoding="utf-8")
    rep_dup_verb = audit_edit_timeline_and_screen(job, ws, rem, beats)
    assert rep_dup_verb["status"] == "FAILED"
    assert any(
        iss["type"] == "vox_template_monoculture" and "CAUSAL_CHAIN" in iss["detail"]
        for iss in rep_dup_verb["issues"]
    )

    # Phase 2b: Unique @voxVerb, BUT repeat camera topology `diagonal_pursuit` within 3 consecutive VOX scenes (01 & 03) OR omit @voxVerb -> MUST BLOCK
    repeated_cam_and_missing_verb_scenes = """
/** @voxVerb CAUSAL_CHAIN */
export const VoxScene01 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('diagonal_pursuit', [{x:1200,y:800},{x:1900,y:1200}]) as any}><PinnedCutoutPhoto src="p1.jpg" /><RoughHandDrawnArrow /></VoxCopyStandCameraRig>);
/** @voxVerb SPLIT_PARADOX */
export const VoxScene02 = () => (<SplitParadoxShutter leftLabel="허위 진술" rightLabel="실제 항로" />);
/** @voxVerb CRASH_TIMELINE */
export const VoxScene03 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('diagonal_pursuit', [{x:1100,y:900},{x:2200,y:1250}]) as any}><LivePlungingChartCurve /></VoxCopyStandCameraRig>);
/** @voxVerb SCALE_MULTIPLICATION */
export const VoxScene04 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('pullback_scale_shock', [{x:1800,y:700},{x:1820,y:1500}]) as any}><EvidenceStackMultiplier /></VoxCopyStandCameraRig>);
export const VoxScene05 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('orbital_3d_glide', [{x:1500,y:900},{x:2100,y:1300}]) as any}><NetworkPortraitNode /><NetworkGraphLink /></VoxCopyStandCameraRig>);
"""
    (vox_dir / "VoxScenes01to08.tsx").write_text(repeated_cam_and_missing_verb_scenes, encoding="utf-8")
    rep_cam_dup = audit_edit_timeline_and_screen(job, ws, rem, beats)
    assert rep_cam_dup["status"] == "FAILED"
    assert any(
        iss["type"] == "vox_template_monoculture"
        and "Camera Topology repeated within 3 consecutive VOX scenes" in iss["detail"]
        and "missing mandatory @voxVerb" in iss["detail"]
        for iss in rep_cam_dup["issues"]
    )

    # Phase 3: Clean V13 Composable Lego 8-scene suite -> MUST PASS 100% with zero blockers
    clean_v13_scenes = """
/** @voxVerb CAUSAL_CHAIN */
export const VoxScene01 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('diagonal_pursuit', [{x:1200,y:800},{x:1950,y:1240}]) as any}><PinnedCutoutPhoto src="p1.jpg" /><RoughHandDrawnArrow /><ForensicEvidenceTag /></VoxCopyStandCameraRig>);
/** @voxVerb SPLIT_PARADOX */
export const VoxScene02 = () => (<SplitParadoxShutter leftLabel="하이난 도주 진술" rightLabel="항저우 직항 기록" />);
/** @voxVerb SINGLE_EVIDENCE_AUTOPSY */
export const VoxScene03 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('center_autopsy_dive', [{x:1920,y:1200}]) as any}><LivingArchive25DPlate plateAsset="a1.jpg" /><OpticalGlassLoupe imageSrc="a1.jpg" /><FramelessEditorialCallout anchorX={anchorSx} anchorY={anchorSy} /></VoxCopyStandCameraRig>);
/** @voxVerb CRASH_TIMELINE */
export const VoxScene04 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('timeline_axis_track', [{x:1200,y:960},{x:2400,y:1120}]) as any}><LivePlungingChartCurve /><CountdownDeadlineClock /></VoxCopyStandCameraRig>);
/** @voxVerb SCALE_MULTIPLICATION */
export const VoxScene05 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('pullback_scale_shock', [{x:1920,y:1200}]) as any}><EvidenceStackMultiplier /><RollingForensicCounter /></VoxCopyStandCameraRig>);
/** @voxVerb NETWORK_GRAPH */
export const VoxScene06 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('z_zigzag', [{x:1250,y:820},{x:2250,y:960},{x:1350,y:1460}]) as any}><NetworkPortraitNode /><NetworkGraphLink /></VoxCopyStandCameraRig>);
/** @voxVerb DUAL_ERA_LOCK */
export const VoxScene07 = () => (<VoxCopyStandCameraRig waypoints={buildTopologyWaypoints('orbital_3d_glide', [{x:1600,y:980},{x:2180,y:1320}]) as any}><BiometricDualEraLock leftSrc="e1997.jpg" rightSrc="e2015.jpg" /></VoxCopyStandCameraRig>);
/** @voxVerb GEO_VECTOR_PURSUIT */
export const VoxScene08 = () => (<GeoJson3DMapStage plateSrc={jobAsset('gis1.jpg')} />);
"""
    (vox_dir / "VoxScenes01to08.tsx").write_text(clean_v13_scenes, encoding="utf-8")
    rep_ok = audit_edit_timeline_and_screen(job, ws, rem, beats)
    assert rep_ok["status"] == "PASSED", f"Unexpected issues: {rep_ok['issues']}"
    assert rep_ok["has_blocker"] is False


def test_real_cxm_voxtest_10m_passes_v13_vox_screening_without_false_positives(tmp_path: Path) -> None:
    cxm_dir = Path(r"B:\ALL_TOOLS\CofiRemotion\src\vox-studio\cxm-voxtest-10m")
    if not cxm_dir.is_dir():
        pytest.skip("cxm-voxtest-10m reference directory not present")

    job_id = "20261102-cxm-check"
    job = _director_v2_job(job_id)
    ws = tmp_path / "ws"
    rem = tmp_path / "remotion"
    vox_dst = rem / "src" / "vox-studio" / "cxm-voxtest-10m"
    vox_dst.parent.mkdir(parents=True)
    ws.mkdir(parents=True)
    shutil.copytree(cxm_dir, vox_dst)

    (rem / "src" / "CxmComp.tsx").write_text(
        f"""// {job_id}
import {{ VoxTestSceneRouter }} from './vox-studio/cxm-voxtest-10m';
import {{ FramelessCinemaTextBeat }} from './components/FramelessCinemaTextBeat';
const DURATION_FRAMES = 300;
const outroBlackOpacity = 1;
export const CxmComp = () => <div style={{ background: '#000000' }}><VoxTestSceneRouter /><FramelessCinemaTextBeat mode="editorial_statement" headline="천쉰민" /></div>;
""",
        encoding="utf-8",
    )
    pub_ftg = rem / "public" / "jobs" / job_id / "footage"
    pub_ftg.mkdir(parents=True)
    for i in range(1, 7):
        (pub_ftg / f"S_F{i:03d}.mp4").write_bytes(b"0" * 8192)
    (ws / "edit_manifest.json").write_text(
        json.dumps(
            {
                "total_beats": 10,
                "real_footage_beats_count": 6,
                "vox_beats_count": 2,
                "cinema_text_beats_count": 1,
                "ai_reconstruction_beats_count": 1,
                "beats": [
                    {"beat_id": f"B{i:03d}", "visualRole": "REAL_FTG", "imageFile": f"jobs/{job_id}/footage/S_F{i:03d}.mp4"}
                    for i in range(1, 7)
                ],
            }
        ),
        encoding="utf-8",
    )
    beats = [{"beat_id": f"B{i:03d}"} for i in range(1, 11)]
    rep = audit_edit_timeline_and_screen(job, ws, rem, beats)
    assert rep["status"] == "PASSED", f"cxm-voxtest-10m failed V13 critic gate: {rep['issues']}"
    assert rep["has_blocker"] is False


def test_fetcher_true_crime_auto_mode_never_skips_ai_backup_beats_or_injects_bible_broll(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = tmp_path / "ws"
    rem = tmp_path / "remotion"
    (ws / "media" / "ai").mkdir(parents=True)
    rem.mkdir(parents=True)

    (ws / "media" / "ai" / "B001_ai_keyframe.jpg").write_bytes(b"jpg")
    (ws / "visual_manifest.json").write_text(
        json.dumps(
            {
                "beats": [
                    {
                        "beat_id": "B001",
                        "visual_route": "ai_visual",
                        "footage_search_queries": ["谢仁良 宁波 警方 抓捕", "上海 猎狐行动 押解"],
                    },
                    {
                        "beat_id": "B002",
                        "visual_route": "ai_visual",
                        "footage_search_queries": [],
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (ws / "asset_registry.json").write_text(
        json.dumps({"assets": [{"beat_id": "B001", "kind": "ai_image", "path": "media/ai/B001_ai_keyframe.jpg"}]}),
        encoding="utf-8",
    )

    fetcher = EditDirectFootageFetcher(ws, rem, job_id="j-tc")
    seen_queries: list[str] = []

    def fake_fetch(job_id: str, beat_ids: list[str], query: str, **kwargs):
        seen_queries.append(query)
        return {"ok": False, "beat_ids": beat_ids, "query": query}

    monkeypatch.setattr(fetcher, "fetch_for_beats", fake_fetch)
    monkeypatch.setattr("documentary.edit_footage_fetcher.RemotionManager.prepare_job_media", lambda self, j, w: {"asset_count": 0})

    summary = fetcher.auto_fetch_missing_beats(_director_v2_job("j-tc"))
    assert summary["total_groups"] == 1
    assert seen_queries == ["谢仁良 宁波 警方 抓捕", "上海 猎狐行动 押解"]
    assert not any("bible" in q.lower() or "sunrise" in q.lower() for q in seen_queries)


def test_multi_channel_skin_isolation_and_system_wide_lego_vox_grammar(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    rem = tmp_path / "remotion"
    ws.mkdir()
    rem.mkdir()

    # 1. Classic Forensic Noir (`channel-e544a64b7c`): isolated `VoxTactileNewsPrimitives.tsx` skin + V13 Lego Grammar
    noir_job = {
        "id": "job-noir-v13",
        "title": "칭다오 실종 사건",
        "language": "ko",
        "market": "KR",
        "visual_strategy": "full_ai",
        "channel_profile_id": "channel-e544a64b7c",
        "editing_dna": {"preset_id": "forensic_noir"},
    }
    noir_edit = build_phase_prompt(noir_job, "edit", ws, rem)
    assert "VoxTactileNewsPrimitives.tsx" in noir_edit
    assert "VOX_COMPOSABLE_LEGO_GRAMMAR_DIRECTOR_V13" in noir_edit
    assert "--preset forensic_noir" in noir_edit
    assert "#040C18" not in noir_edit
    assert "VOX_25D_MOTION_JOURNALISM_DIRECTOR" not in noir_edit

    # 2. Cyber-Financial Audit (`channel-cn-cyber-finance-kr`): isolated `#040C18 / #38BDF8` skin + V13 Lego Grammar + Critic Gate
    fin_job_id = "job-fin-v13"
    fin_job = {
        "id": fin_job_id,
        "title": "항저우 P2P 400억 증발",
        "language": "ko",
        "market": "KR",
        "visual_strategy": "full_ai",
        "channel_profile_id": "channel-cn-cyber-finance-kr",
        "editing_dna": {"preset_id": "financial_forensic_vox"},
    }
    fin_edit = build_phase_prompt(fin_job, "edit", ws, rem)
    assert "#040C18" in fin_edit and "#38BDF8" in fin_edit
    assert "VOX_COMPOSABLE_LEGO_GRAMMAR_DIRECTOR_V13" in fin_edit
    assert "--preset financial_forensic_vox" in fin_edit
    assert "VoxTactileNewsPrimitives.tsx" not in fin_edit
    assert "SPATIAL_DARK_CINEMA_DIRECTOR" not in fin_edit

    vox_dir = rem / "src" / "vox-studio" / "fin-audit"
    vox_dir.mkdir(parents=True)
    # Copy real validate-vox-newsroom-ast.mjs so subprocess AST gate runs against financial_forensic_vox too
    real_ast = Path(r"B:\ALL_TOOLS\CofiRemotion\scripts\validate-vox-newsroom-ast.mjs")
    if real_ast.is_file():
        (rem / "scripts").mkdir(parents=True, exist_ok=True)
        shutil.copy2(real_ast, rem / "scripts" / "validate-vox-newsroom-ast.mjs")

    (rem / "src" / "FinComp.tsx").write_text(
        f"""// {fin_job_id}
import {{ VoxScene01 }} from './vox-studio/fin-audit/VoxScenes01to05';
const DURATION_FRAMES = 300;
const outroBlackOpacity = 1;
export const FinComp = () => <div style={{ background: '#000000' }}><VoxScene01 /></div>;
""",
        encoding="utf-8",
    )
    beats = [{"beat_id": f"B{i:03d}"} for i in range(1, 6)]

    # Repeat @voxVerb CRASH_TIMELINE inside 5 scenes on financial_forensic_vox -> MUST BLOCK!
    (vox_dir / "VoxScenes01to05.tsx").write_text(
        """
/** @voxVerb CRASH_TIMELINE @voxCamera timeline_axis_track */
export const VoxScene01 = () => (<div style={{ background: '#141921' }}><LivePlungingChartCurve /></div>);
/** @voxVerb SPLIT_PARADOX @voxCamera split_duel_shutter */
export const VoxScene02 = () => (<SplitParadoxShutter leftLabel="약정 수익" rightLabel="실제 잔고" />);
/** @voxVerb NETWORK_GRAPH @voxCamera orbital_3d_glide */
export const VoxScene03 = () => (<div style={{ background: '#141921' }}><NetworkPortraitNode /><NetworkGraphLink /></div>);
/** @voxVerb CRASH_TIMELINE @voxCamera vertical_cascade */
export const VoxScene04 = () => (<div style={{ background: '#141921' }}><CountdownDeadlineClock /></div>);
/** @voxVerb SCALE_MULTIPLICATION @voxCamera pullback_scale_shock */
export const VoxScene05 = () => (<div style={{ background: '#141921' }}><EvidenceStackMultiplier /></div>);
""",
        encoding="utf-8",
    )
    rep_fin_fail = audit_edit_timeline_and_screen(fin_job, ws, rem, beats)
    assert rep_fin_fail["status"] == "FAILED"
    assert any(iss["type"] == "vox_template_monoculture" and "CRASH_TIMELINE" in iss["detail"] for iss in rep_fin_fail["issues"])

    # Distinct 5 @voxVerb + 3-window @voxCamera + dark cyber hex `#141921` allowed on financial_forensic_vox -> MUST PASS!
    (vox_dir / "VoxScenes01to05.tsx").write_text(
        """
/** @voxVerb CRASH_TIMELINE @voxCamera timeline_axis_track */
export const VoxScene01 = () => (<div style={{ background: '#141921' }}><LivePlungingChartCurve /></div>);
/** @voxVerb SPLIT_PARADOX @voxCamera split_duel_shutter */
export const VoxScene02 = () => (<SplitParadoxShutter leftLabel="약정 수익" rightLabel="실제 잔고" />);
/** @voxVerb NETWORK_GRAPH @voxCamera orbital_3d_glide */
export const VoxScene03 = () => (<div style={{ background: '#141921' }}><NetworkPortraitNode /><NetworkGraphLink /></div>);
/** @voxVerb COUNTDOWN_PRESSURE @voxCamera vertical_cascade */
export const VoxScene04 = () => (<div style={{ background: '#141921' }}><CountdownDeadlineClock /></div>);
/** @voxVerb SCALE_MULTIPLICATION @voxCamera pullback_scale_shock */
export const VoxScene05 = () => (<div style={{ background: '#141921' }}><EvidenceStackMultiplier /></div>);
""",
        encoding="utf-8",
    )
    rep_fin_ok = audit_edit_timeline_and_screen(fin_job, ws, rem, beats)
    assert rep_fin_ok["status"] == "PASSED", f"Unexpected issues on financial_forensic_vox: {rep_fin_ok['issues']}"

    # 3. Devotional Sanctuary (`channel-kr-grace-letter-60m`): 0% Vox rules/grammar
    dev_job = {
        "id": "job-grace-v13",
        "title": "은혜의 편지",
        "language": "ko",
        "market": "KR",
        "visual_strategy": "edit_direct_footage",
        "channel_profile_id": "channel-kr-grace-letter-60m",
        "editing_dna": {"preset_id": "sacred_devotional"},
    }
    dev_edit = build_phase_prompt(dev_job, "edit", ws, rem)
    dev_chat = build_edit_chat_prompt(dev_job, ws, rem, "자막 다듬어줘")
    assert "VOX_COMPOSABLE_LEGO_GRAMMAR_DIRECTOR_V13" not in dev_edit
    assert "VOX_COMPOSABLE_LEGO_GRAMMAR_DIRECTOR_V13" not in dev_chat
    assert "VoxTactileNewsPrimitives.tsx" not in dev_edit
    assert "sacred_devotional" in dev_chat


def test_all_15_agent_charters_and_orchestrator_delegation_and_full_stage_vox_rules(tmp_path: Path) -> None:
    from documentary.agent_manager import AgentManager
    from documentary.prompts import build_producer_chat_prompt, build_producer_goal_prompt

    am = AgentManager()
    lint = am.lint_corpus()
    assert lint["passed"] is True, f"Corpus errors: {lint['errors']}"
    assert lint["agent_count"] == 15
    assert lint["warnings"] == []

    # Orchestrator charter & chat/goal prompts must enforce fast direct execution in chat
    # ("ZERO STANDING STILL") and restrict QA gates to video production only.
    orch = am.get("orchestrator")
    assert "ZERO STANDING STILL" in orch.soul_markdown
    assert "QUALITY GATES ONLY WHEN PRODUCING A VIDEO" in orch.soul_markdown

    chat_prompt = build_producer_chat_prompt([], "Sửa cảnh VOX và cắt lại tư liệu thật")
    assert "ZERO STANDING STILL" in chat_prompt
    assert "QA GATES ONLY FOR VIDEO PRODUCTION" in chat_prompt

    goal_prompt = build_producer_goal_prompt(
        "Chỉnh lại VOX và kiểm định",
        {"app_tab": "edit"},
        api_base_url="http://127.0.0.1:8878",
        first_turn=True,
        goal_mode=True,
    )
    assert "ZERO STANDING STILL" in goal_prompt
    assert "QA GATES ONLY FOR VIDEO PRODUCTION" in goal_prompt
    assert "CẤM GỌI `invoke_subagent`" in goal_prompt

    # Phase prompts must not instruct skipping Step 4 or writing lazy batch scripts
    v2_job = _director_v2_job("20261105-v2-clean")
    plan_p = build_phase_prompt(v2_job, "plan", tmp_path, tmp_path / "remotion")
    edit_p = build_phase_prompt(v2_job, "edit", tmp_path, tmp_path / "remotion")
    assert "Bước 4 (Footage) được TỰ ĐỘNG BỎ QUA hoàn toàn" not in plan_p
    assert "TỰ ĐỘNG BỎ QUA Bước 4" not in edit_p
    assert "FULL-STAGE VISUAL MECHANISM" in edit_p
    assert "10–15" in edit_p
    assert "dHash >= 14" in edit_p


