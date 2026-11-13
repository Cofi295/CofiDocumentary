"""
Audio-Visual Voice/SRT Sync & YouTube Policy Guardrail Service for CofiDocumentary (Milestone 3).
Provides automated drift checking, anti-repetitive hold detection, Ken Burns auto-repair,
and YouTube Green Monetization & Reused Content compliance validation.
"""

from __future__ import annotations

import copy
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
WORKSPACES_DIR = ROOT / "workspaces"
JOBS_DIR = DATA_DIR / "jobs"

_file_lock = threading.RLock()

# Multi-language prohibited / violent graphic & yellow-dollar tokens
PROHIBITED_TERMS = [
    # Vietnamese
    "máu me",
    "chặt đầu",
    "thi thể đẫm máu",
    "bạo lực cực đoan",
    "vũ khí sát thương",
    "man rợ",
    "phanh thây",
    "phân xác",
    "xác chết phân hủy",
    "hiếp dâm",
    "cưỡng hiếp",
    # Korean
    "참수",
    "토막 살인",
    "토막살인",
    "시신 훼손",
    "시체 훼손",
    "사체 훼손",
    "피투성이 시신",
    "선혈이 낭자",
    "유혈 낭자",
    "성폭행",
    "강간",
    "아동 학대",
    # English
    "decapitation",
    "dismemberment",
    "bloody corpse",
    "mutilated body",
    "extreme gore",
    "graphic murder scene",
]


def _parse_timestamp(time_str: str) -> float:
    """Parse SRT timestamp '00:01:23,456' or '00:01:23.456' into seconds."""
    time_str = time_str.strip().replace(",", ".")
    parts = time_str.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600.0 + float(m) * 60.0 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60.0 + float(s)
    return float(time_str)


def parse_srt(srt_content: str) -> list[dict[str, Any]]:
    """Parse SRT file content into list of {index, start, end, text} segments."""
    segments = []
    blocks = re.split(r"\n\s*\n", srt_content.strip())
    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) >= 2:
            time_line = lines[1] if "-->" in lines[1] else lines[0]
            if "-->" in time_line:
                start_part, end_part = time_line.split("-->")
                start_sec = _parse_timestamp(start_part)
                end_sec = _parse_timestamp(end_part)
                text = " ".join(lines[2:]) if len(lines) > 2 else ""
                segments.append({
                    "start": round(start_sec, 3),
                    "end": round(end_sec, 3),
                    "text": text,
                })
    return segments


class SyncPolicyService:
    def __init__(
        self,
        workspaces_dir: Path | str | None = None,
        jobs_dir: Path | str | None = None,
    ):
        self.workspaces_dir = Path(workspaces_dir) if workspaces_dir else WORKSPACES_DIR
        self.jobs_dir = Path(jobs_dir) if jobs_dir else JOBS_DIR

    def _get_workspace_path(self, job_id: str) -> Path:
        ws = self.workspaces_dir / job_id
        if ws.exists():
            return ws
        return self.jobs_dir / job_id

    def check_sync_compliance(
        self,
        job_id: str | None = None,
        beats: list[dict[str, Any]] | None = None,
        srt_segments: list[dict[str, Any]] | None = None,
        script_text: str = "",
    ) -> dict[str, Any]:
        """
        Evaluate Audio-Visual Voice/SRT synchronization and YouTube Policy guardrails.
        Can run against an existing job or directly against in-memory parameters.
        """
        workspace_dir = None
        if job_id and beats is None:
            workspace_dir = self._get_workspace_path(job_id)
            beats, srt_segments, script_text = self._load_job_data(workspace_dir, job_id)

        beats = beats or []
        srt_segments = srt_segments or []

        misaligned = []
        holds_over_8s = []
        missing_visuals = []
        total_duration = 0.0

        # 1. Beat duration, hold freezes (>8.0s), and asset presence
        for i, beat in enumerate(beats):
            dur = float(beat.get("duration_sec", beat.get("target_duration_sec", 5.0)))
            total_duration += dur

            # Hold freeze check (> 8.0s without motion override or motivated static_tripod)
            motivated_static = beat.get("camera_mode") == "static_tripod" or beat.get("motivated_static_tripod")
            if dur > 8.0 and not beat.get("has_motion_override", False) and not motivated_static:
                holds_over_8s.append({
                    "beat_id": beat.get("beat_id", f"B{i+1:03d}"),
                    "duration_sec": dur,
                    "remedy": "inject_ken_burns_or_hud_overlay",
                })

            # Missing visual check
            selected_asset = beat.get("selected_asset") or beat.get("media_path") or beat.get("asset_path")
            if not selected_asset and beat.get("visual_source") == "missing":
                missing_visuals.append({
                    "beat_id": beat.get("beat_id", f"B{i+1:03d}"),
                    "visual_type": beat.get("visual_type", "unknown"),
                    "remedy": "assign_contextual_fallback_asset",
                })

        # 2. Beat to SRT timestamp alignment (honoring intentional J-Cut / L-Cut split-edits & voiceless bridges)
        for i, beat in enumerate(beats):
            if beat.get("voiceless_bridge") or beat.get("split_edit"):
                continue
            if i < len(srt_segments):
                srt_dur = float(srt_segments[i].get("end", 0) - srt_segments[i].get("start", 0))
                beat_dur = float(beat.get("duration_sec", beat.get("target_duration_sec", 5.0)))
                split_allowance = float(beat.get("audio_lead_sec") or 0.0) + float(beat.get("visual_linger_sec") or 0.0)
                drift = abs(beat_dur - srt_dur)
                if drift > (0.5 + split_allowance):
                    misaligned.append({
                        "beat_id": beat.get("beat_id", f"B{i+1:03d}"),
                        "beat_duration": round(beat_dur, 2),
                        "srt_duration": round(srt_dur, 2),
                        "drift_sec": round(drift, 2),
                    })

        # 3. Policy checks (Monetization safety, graphic violence)
        flagged_terms = []
        lower_script = script_text.lower()
        for term in PROHIBITED_TERMS:
            if term.lower() in lower_script:
                flagged_terms.append(term)

        # 4. Editorial overlay ratio
        motion_beats = sum(
            1 for b in beats
            if b.get("visual_type") in {
                "motion",
                "hud",
                "2.5d_map",
                "annotated_footage",
                "vox_25d_scene",
                "vox_newsroom_motion_text",
                "cinema_text",
                "remotion_motion",
            }
            or b.get("has_motion_override")
            or b.get("telemetry_hud_overlay")
        )
        total_beats_count = max(len(beats), 1)
        editorial_overlay_ratio = round(motion_beats / total_beats_count, 2)

        sync_passed = (len(misaligned) == 0 and len(holds_over_8s) == 0)
        policy_passed = (len(flagged_terms) == 0 and editorial_overlay_ratio >= 0.85)

        scorecard = {
            "sync_scorecard": {
                "total_beats": len(beats),
                "aligned_beats": len(beats) - len(misaligned),
                "misaligned_beats": misaligned,
                "holds_over_8s": holds_over_8s,
                "missing_visuals": missing_visuals,
                "passed": sync_passed,
            },
            "policy_scorecard": {
                "green_monetization": len(flagged_terms) == 0,
                "reused_content_risk": "low" if editorial_overlay_ratio >= 0.85 else "medium",
                "editorial_overlay_ratio": editorial_overlay_ratio,
                "flagged_terms": flagged_terms,
                "passed": policy_passed,
            },
            "overall_status": "PASSED" if (sync_passed and policy_passed) else "NEEDS_ATTENTION",
            "compliance_score": round(
                ((len(beats) - len(misaligned)) / max(len(beats), 1) * 50) +
                ((1.0 if len(flagged_terms) == 0 else 0.0) * 30) +
                (min(editorial_overlay_ratio, 1.0) * 20),
                1
            ),
        }

        # Cache scorecard in workspace if workspace directory exists
        if workspace_dir and workspace_dir.exists():
            try:
                (workspace_dir / "compliance_scorecard.json").write_text(
                    json.dumps(scorecard, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
            except Exception:
                pass

        return scorecard

    def auto_repair_sync(self, job_id: str) -> dict[str, Any]:
        """
        Auto-repair audio-visual synchronization:
        1. Realign beat durations and timestamps to exact SRT narration segments.
        2. Apply Ken Burns zoom (1.02x to 1.08x) and telemetry HUD overlays to holds > 8.0s.
        3. Save repaired manifest back idempotently.
        """
        workspace_dir = self._get_workspace_path(job_id)
        if not workspace_dir.exists():
            raise KeyError(f"Workspace for job {job_id} not found")

        manifest_path = workspace_dir / "visual_manifest.json"
        if not manifest_path.exists():
            manifest_path = self.jobs_dir / job_id / "visual_manifest.json"

        beats, srt_segments, script_text = self._load_job_data(workspace_dir, job_id)

        realigned_beats_count = 0
        repaired_holds_count = 0

        repaired_beats = []
        for i, beat in enumerate(beats):
            b = dict(beat)
            # 1. Realign timestamps
            if i < len(srt_segments):
                srt_start = float(srt_segments[i]["start"])
                srt_end = float(srt_segments[i]["end"])
                target_dur = round(srt_end - srt_start, 2)

                if abs(float(b.get("duration_sec", 0)) - target_dur) > 0.05:
                    realigned_beats_count += 1
                b["duration_sec"] = target_dur
                b["target_duration_sec"] = target_dur
                b["start_sec"] = srt_start
                b["end_sec"] = srt_end
            else:
                target_dur = float(b.get("duration_sec", b.get("target_duration_sec", 5.0)))

            # 2. Repair holds > 8.0s (Ken Burns + HUD telemetry injection)
            if target_dur > 8.0 and not b.get("has_motion_override", False):
                b["has_motion_override"] = True
                b["camera_motion"] = "slow_zoom_in_with_telemetry"
                b["ken_burns_zoom"] = {
                    "start_scale": 1.02,
                    "end_scale": 1.08,
                    "direction": "push_in",
                }
                b["telemetry_hud_overlay"] = True
                b["motion_effect"] = "ken_burns_push_and_hud"
                repaired_holds_count += 1

            repaired_beats.append(b)

        # Save repaired manifest atomically
        with _file_lock:
            manifest_data = self._read_json(manifest_path) or {}
            manifest_data["beats"] = repaired_beats
            manifest_data["sync_repaired_at"] = datetime.now(timezone.utc).isoformat()
            manifest_data["version"] = int(manifest_data.get("version", 1)) + 1
            self._write_json(manifest_path, manifest_data)

            # Mirror to jobs dir if distinct
            alt_job_manifest = self.jobs_dir / job_id / "visual_manifest.json"
            if alt_job_manifest != manifest_path and self.jobs_dir.exists():
                self._write_json(alt_job_manifest, manifest_data)

        # Re-check scorecard
        scorecard = self.check_sync_compliance(
            job_id=job_id,
            beats=repaired_beats,
            srt_segments=srt_segments,
            script_text=script_text,
        )

        return {
            "status": "success",
            "message": f"Successfully auto-repaired sync and hold guardrails for job {job_id}",
            "job_id": job_id,
            "realigned_beats_count": realigned_beats_count,
            "repaired_holds_count": repaired_holds_count,
            "scorecard": scorecard,
        }

    def _load_job_data(
        self, workspace_dir: Path, job_id: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
        """Load beats, srt_segments, and script_text from workspace or job directory."""
        beats: list[dict[str, Any]] = []
        srt_segments: list[dict[str, Any]] = []
        script_text = ""

        # Load Visual Manifest
        manifest = self._read_json(workspace_dir / "visual_manifest.json") or self._read_json(self.jobs_dir / job_id / "visual_manifest.json")
        if isinstance(manifest, dict):
            beats = manifest.get("beats") or []
            if not beats and "scenes" in manifest:
                for s in manifest.get("scenes", []):
                    if isinstance(s, dict):
                        beats.extend(s.get("beats", []))

        # Load SRT or Voice Manifest
        srt_path = workspace_dir / "subtitles.srt"
        if srt_path.exists():
            try:
                srt_content = srt_path.read_text(encoding="utf-8")
                srt_segments = parse_srt(srt_content)
            except Exception:
                pass

        if not srt_segments:
            voice_manifest = self._read_json(workspace_dir / "voice_manifest.json") or self._read_json(self.jobs_dir / job_id / "voice_manifest.json")
            if isinstance(voice_manifest, dict):
                for vb in voice_manifest.get("beats", []):
                    if isinstance(vb, dict):
                        srt_segments.append({
                            "start": float(vb.get("start_sec", 0)),
                            "end": float(vb.get("end_sec", 0)),
                            "text": str(vb.get("text", "")),
                        })

        # Load Script Text
        script_file = workspace_dir / "script.md"
        if script_file.exists():
            try:
                script_text = script_file.read_text(encoding="utf-8")
            except Exception:
                pass
        if not script_text:
            job_file = self.jobs_dir / job_id / "job.json"
            if job_file.exists():
                job_data = self._read_json(job_file) or {}
                script_text = str(job_data.get("script") or job_data.get("topic") or job_data.get("title") or "")

        return beats, srt_segments, script_text

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
