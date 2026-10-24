"""
Thumbnail DNA Service for CofiDocumentary (Milestone 3).
Defines Thumbnail Style DNA schemas, extraction from active projects,
and persistence ("Lock Approved Thumbnail DNA to Channel Profile").
"""

from __future__ import annotations

import copy
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CHANNEL_PROFILES_FILE = DATA_DIR / "channel_profiles.json"
WORKSPACES_DIR = ROOT / "workspaces"
JOBS_DIR = DATA_DIR / "jobs"

_file_lock = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ThumbnailDnaService:
    def __init__(
        self,
        profiles_file: Path | str | None = None,
        jobs_dir: Path | str | None = None,
        workspaces_dir: Path | str | None = None,
    ):
        self.profiles_file = Path(profiles_file) if profiles_file else CHANNEL_PROFILES_FILE
        self.jobs_dir = Path(jobs_dir) if jobs_dir else JOBS_DIR
        self.workspaces_dir = Path(workspaces_dir) if workspaces_dir else WORKSPACES_DIR

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def extract_thumbnail_dna_from_job(self, job_id: str) -> dict[str, Any]:
        """Extract active thumbnail parameters from a project's thumbnail_design.json and workspace."""
        job_file = self.jobs_dir / job_id / "job.json"
        job_data = self._read_json(job_file) if job_file.is_file() else {}

        ws_dir = self.workspaces_dir / job_id
        design_file = ws_dir / "thumbnail_design.json"
        design = self._read_json(design_file) if design_file.is_file() else {}

        active_vid = str(design.get("active_variant_id") or "v1")
        variants = design.get("variants") or []
        active_var = next((v for v in variants if isinstance(v, dict) and v.get("id") == active_vid), variants[0] if variants else {})

        # Read parent profile's existing thumbnail_dna for fallback defaults
        parent_profile_id = str(job_data.get("channel_profile_id") or "")
        parent_tdna: dict[str, Any] = {}
        if parent_profile_id and self.profiles_file.is_file():
            profiles_raw = self._read_json(self.profiles_file)
            for p in profiles_raw.get("profiles", []):
                if str(p.get("id")) == parent_profile_id or str(p.get("channel_profile_id")) == parent_profile_id:
                    parent_tdna = copy.deepcopy(p.get("thumbnail_dna") or {})
                    break

        # Extract archetype
        layout_template = str(
            active_var.get("archetype")
            or design.get("layout_template")
            or parent_tdna.get("layout_template")
            or "broadcast_left_heavy"
        )

        # Extract layers styling
        layers = active_var.get("layers") or []
        by_id = {str(layer.get("id") or ""): layer for layer in layers if isinstance(layer, dict)}
        l1 = by_id.get("line_1") or {}
        l2 = by_id.get("line_2") or {}
        b = by_id.get("badge") or {}

        # Typography preset
        raw_font = str(l1.get("fontFamily") or l2.get("fontFamily") or "").strip()
        font_family = "Pretendard"
        if "gmarket" in raw_font.lower():
            font_family = "Gmarket Sans"
        elif "paperlogy" in raw_font.lower():
            font_family = "Paperlogy"
        elif "scoredream" in raw_font.lower():
            font_family = "SCoreDream"
        elif "inter" in raw_font.lower():
            font_family = "Inter"

        title_weight = str(parent_tdna.get("typography_preset", {}).get("title_weight") or "900")
        stroke_color = str(l1.get("stroke") or parent_tdna.get("typography_preset", {}).get("stroke_color") or "#000000")
        stroke_width = int(l1.get("strokeWidth") or parent_tdna.get("typography_preset", {}).get("stroke_width") or 6)

        typography_preset = {
            "font_family": font_family,
            "title_weight": title_weight,
            "stroke_color": stroke_color,
            "stroke_width": stroke_width,
            "text_transform": parent_tdna.get("typography_preset", {}).get("text_transform", "uppercase"),
        }

        # Color palette
        primary_accent = str(l2.get("fill") or parent_tdna.get("color_palette", {}).get("primary") or "#FFE84A")
        raw_badge_bg = str(b.get("bgColor") or b.get("backgroundColor") or b.get("badge_bg") or "").strip()
        badge_accent = raw_badge_bg if raw_badge_bg and raw_badge_bg.lower() not in ("transparent", "none") else str(parent_tdna.get("color_palette", {}).get("accent") or "#EF4444")
        sec_color = str(parent_tdna.get("color_palette", {}).get("secondary") or "#0F172A")
        bg_color = str(parent_tdna.get("color_palette", {}).get("background") or "#020617")
        text_primary = str(l1.get("fill") or parent_tdna.get("color_palette", {}).get("text_primary") or "#ffffff")
        highlight_fill = str(l2.get("highlightFill") or l1.get("highlightFill") or parent_tdna.get("color_palette", {}).get("highlight") or "#ffe600")

        color_palette = {
            "primary": primary_accent,
            "secondary": sec_color,
            "accent": badge_accent,
            "background": bg_color,
            "text_primary": text_primary,
            "highlight": highlight_fill,
        }

        # Reference character & mascot lock
        style_ref_candidate = ws_dir / "media" / "style_reference" / "style_reference.png"
        ref_char_path = str(parent_tdna.get("reference_character_path") or "")
        if style_ref_candidate.is_file():
            ref_char_path = f"workspaces/{job_id}/media/style_reference/style_reference.png"
        elif not ref_char_path and job_data.get("style_reference_image"):
            ref_char_path = str(job_data["style_reference_image"])

        mascot_lock = bool(
            parent_tdna.get("mascot_lock")
            or (ref_char_path and parent_profile_id == "channel-e544a64b7c")
        )

        style_preset = str(
            active_var.get("style_preset")
            or design.get("style_preset")
            or parent_tdna.get("style_preset")
            or "cold_forensic_noir"
        )
        visual_sig = str(
            active_var.get("visual_signature")
            or design.get("visual_signature")
            or parent_tdna.get("visual_signature")
            or f"{style_preset.replace('_', ' ').title()} Preset"
        )

        return {
            "style_preset": style_preset,
            "visual_signature": visual_sig,
            "color_palette": color_palette,
            "typography_preset": typography_preset,
            "layout_template": layout_template,
            "reference_character_path": ref_char_path,
            "mascot_lock": mascot_lock,
            "version": int(parent_tdna.get("version", 1)),
        }

    def lock_job_thumbnail_dna_to_channel(
        self,
        job_id: str,
        notes: str = "",
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Extract approved thumbnail design parameters from project and lock them
        into the parent Channel Profile as a new version in thumbnail_dna_history.
        """
        job_file = self.jobs_dir / job_id / "job.json"
        if not job_file.is_file():
            raise KeyError(f"Job {job_id} not found")

        job_data = self._read_json(job_file) or {}
        channel_profile_id = job_data.get("channel_profile_id")
        if not channel_profile_id:
            raise ValueError(f"Job {job_id} has no assigned channel profile to lock Thumbnail DNA into")

        extracted_dna = self.extract_thumbnail_dna_from_job(job_id)
        if isinstance(overrides, dict):
            for k in ("style_preset", "visual_signature", "layout_template"):
                if overrides.get(k):
                    extracted_dna[k] = str(overrides[k])
            if isinstance(overrides.get("color_palette"), dict):
                extracted_dna.setdefault("color_palette", {}).update(overrides["color_palette"])
            if isinstance(overrides.get("typography_preset"), dict):
                extracted_dna.setdefault("typography_preset", {}).update(overrides["typography_preset"])

        with _file_lock:
            profiles_raw = self._read_json(self.profiles_file) or {}
            profiles_list = profiles_raw.get("profiles", []) if isinstance(profiles_raw, dict) else []

            profile_idx = next(
                (i for i, p in enumerate(profiles_list) if str(p.get("id")) == str(channel_profile_id) or str(p.get("channel_profile_id")) == str(channel_profile_id)),
                None
            )
            if profile_idx is None:
                raise KeyError(f"Channel profile {channel_profile_id} not found")

            profile = profiles_list[profile_idx]

            # Versioning & History
            prev_dna = profile.get("thumbnail_dna") or {}
            prev_version = int(prev_dna.get("version", 1)) if isinstance(prev_dna, dict) else 1
            new_version = prev_version + 1

            history = list(profile.get("thumbnail_dna_history") or [])
            if prev_dna:
                history_entry = copy.deepcopy(prev_dna)
                if "version" not in history_entry:
                    history_entry["version"] = prev_version
                history_entry["archived_at"] = _now()
                history_entry["locked_from_job_id"] = job_id
                history.append(history_entry)

            extracted_dna["version"] = new_version
            extracted_dna["locked_from_job_id"] = job_id
            extracted_dna["locked_at"] = _now()
            if notes:
                extracted_dna["notes"] = notes

            profile["thumbnail_dna"] = extracted_dna
            profile["thumbnail_dna_history"] = history
            profile["updated_at"] = _now()

            self._write_json(self.profiles_file, {"profiles": profiles_list})

            # Update job's local record & snapshot
            job_data["thumbnail_dna"] = copy.deepcopy(extracted_dna)
            snapshot = job_data.setdefault("channel_profile_snapshot", {})
            snapshot["thumbnail_dna"] = copy.deepcopy(extracted_dna)
            self._write_json(job_file, job_data)

            # Also update workspaces/{job_id}/input.json if present
            ws_input = self.workspaces_dir / job_id / "input.json"
            if ws_input.is_file():
                try:
                    inp = self._read_json(ws_input)
                    inp["thumbnail_dna"] = copy.deepcopy(extracted_dna)
                    if "channel_profile_snapshot" in inp and isinstance(inp["channel_profile_snapshot"], dict):
                        inp["channel_profile_snapshot"]["thumbnail_dna"] = copy.deepcopy(extracted_dna)
                    self._write_json(ws_input, inp)
                except Exception:
                    pass

        return {
            "ok": True,
            "status": "success",
            "message": f"Thumbnail DNA successfully locked to channel profile '{channel_profile_id}' as version {new_version}",
            "channel_profile_id": channel_profile_id,
            "thumbnail_dna": extracted_dna,
            "version": new_version,
        }

    def lock_channel_profile_thumbnail_dna(self, profile_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Direct profile update locking thumbnail DNA from Step 0 form."""
        with _file_lock:
            profiles_raw = self._read_json(self.profiles_file) or {}
            profiles_list = profiles_raw.get("profiles", []) if isinstance(profiles_raw, dict) else []

            profile_idx = next(
                (i for i, p in enumerate(profiles_list) if str(p.get("id")) == str(profile_id) or str(p.get("channel_profile_id")) == str(profile_id)),
                None
            )
            if profile_idx is None:
                raise KeyError(f"Channel profile {profile_id} not found")

            profile = profiles_list[profile_idx]
            prev_dna = dict(profile.get("thumbnail_dna") or {})
            prev_version = int(prev_dna.get("version", 1))
            new_version = prev_version + 1

            history = list(profile.get("thumbnail_dna_history") or [])
            if prev_dna:
                entry = copy.deepcopy(prev_dna)
                entry.setdefault("version", prev_version)
                entry["archived_at"] = _now()
                history.append(entry)

            # Deep-merge payload into prev_dna
            updated_dna = copy.deepcopy(prev_dna)
            incoming = payload.get("thumbnail_dna") if isinstance(payload.get("thumbnail_dna"), dict) else payload
            for k, v in incoming.items():
                if isinstance(v, dict) and isinstance(updated_dna.get(k), dict):
                    m = dict(updated_dna[k])
                    m.update(v)
                    updated_dna[k] = m
                else:
                    updated_dna[k] = v

            updated_dna["version"] = new_version
            updated_dna["locked_at"] = _now()

            profile["thumbnail_dna"] = updated_dna
            profile["thumbnail_dna_history"] = history
            profile["updated_at"] = _now()

            self._write_json(self.profiles_file, {"profiles": profiles_list})

        return {
            "ok": True,
            "status": "success",
            "message": f"Thumbnail DNA updated for profile '{profile_id}' as version {new_version}",
            "channel_profile_id": profile_id,
            "thumbnail_dna": updated_dna,
            "version": new_version,
            "locked_at": updated_dna.get("locked_at"),
        }
