from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .codex_gateway import StageResult


_CLAUSE_END = re.compile(r"(?<=[,;:，；：.!?…。！？])\s+")

PLAN_MANIFEST_NAME = "plan_visual_manifest.json"
STP_MANIFEST_SOURCE = "visuals_stp_after_voice"
_STP_UNIT_FIELDS = (
    "parent_beat_id", "narration_text", "start_sec", "end_sec", "target_duration_sec",
    "visual_route", "prompt", "ai_media_mode", "ai_motion_required",
)


def _read_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"{path.name} must contain a JSON object")
    return data


def _collapse_stp_units(manifest: dict[str, Any]) -> dict[str, Any]:
    """Rebuild plan-level beats from Visuals/STP units (legacy workspaces without a snapshot)."""
    order: list[str] = []
    grouped: dict[str, dict[str, Any]] = {}
    texts: dict[str, list[str]] = {}
    for item in manifest.get("beats") or []:
        if not isinstance(item, dict):
            continue
        parent_id = str(item.get("parent_beat_id") or item.get("beat_id") or "").strip()
        if not parent_id:
            continue
        if parent_id not in grouped:
            order.append(parent_id)
            base = {key: value for key, value in item.items() if key not in _STP_UNIT_FIELDS}
            base["beat_id"] = parent_id
            grouped[parent_id] = base
            texts[parent_id] = []
        text = str(item.get("narration_text") or "").strip()
        if text:
            texts[parent_id].append(text)
    beats = []
    for parent_id in order:
        beat = grouped[parent_id]
        beat["narration_text"] = " ".join(texts[parent_id])
        beats.append(beat)
    rebuilt = {key: value for key, value in manifest.items() if key not in {"beats", "source", "version"}}
    rebuilt["source"] = "plan_reconstructed_from_visuals"
    rebuilt["beats"] = beats
    return rebuilt


def load_plan_manifest(workspace: str | Path) -> dict[str, Any]:
    """Return plan-level beats even after Visuals/STP has rewritten visual_manifest.json."""
    workspace = Path(workspace)
    current = _read_manifest(workspace / "visual_manifest.json")
    if str(current.get("source") or "") != STP_MANIFEST_SOURCE:
        return current
    snapshot = workspace / PLAN_MANIFEST_NAME
    if snapshot.exists():
        return _read_manifest(snapshot)
    return _collapse_stp_units(current)


def _compact(text: str) -> str:
    return "".join(str(text or "").split())


def _split_long_clause(text: str, max_chars: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    if len(words) <= 1:
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]
    result: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if current and len(candidate) > max_chars:
            result.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        result.append(" ".join(current))
    return result


def split_visual_text(text: str, max_chars: int = 110) -> list[str]:
    """Split narration into concise semantic visual units without dropping text."""
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return []
    raw_parts = [part.strip() for part in _CLAUSE_END.split(cleaned) if part.strip()]
    result: list[str] = []
    for part in raw_parts:
        result.extend(_split_long_clause(part, max_chars))
    if _compact("".join(result)) != _compact(cleaned):
        raise RuntimeError("Visual segmentation changed narration text")
    return result


def _is_core_evidence_or_character(metadata: dict[str, Any] | None, unit: str = "") -> bool:
    if not metadata or not isinstance(metadata, dict):
        return False
    p = str(metadata.get("source_priority") or "").strip().lower()
    if p != "must_real":
        return False
    combined = " ".join([
        str(unit or ""),
        str(metadata.get("visual_description") or ""),
        str(metadata.get("purpose") or ""),
        " ".join(str(r) for r in (metadata.get("factual_source_refs") or [])),
        " ".join(str(q) for q in (metadata.get("footage_search_queries") or [])),
    ]).lower()

    # Generic atmospheric scenes, weather, reenactments, and secondary props that must NOT use footage
    generic_patterns = [
        # Weather & atmospheric environment
        r"눈\s*덮인", r"함박눈", r"겨울\s*거리", r"폭설", r"눈\s*내리는", r"밤거리", r"어두운\s*골목",
        r"가로등", r"자전거", r"거리\s*풍경", r"교차로", r"전신주", r"청소부", r"환경미화원",
        r"snow", r"winter\s*street", r"dark\s*alley", r"streetlamp", r"bicycle", r"street\s*view",
        r"tuyết", r"ngõ\s*tối", r"đèn\s*đường", r"xe\s*đạp", r"phố\s*xá", r"lao\s*công",
        # Generic objects / rooms / reenactment props
        r"보일러", r"굴뚝", r"대형\s*솥", r"수증기", r"도해", r"스케치", r"골격도", r"칼날", r"숫돌",
        r"포르말린", r"해부학\s*실습", r"정육점", r"책상", r"물음표", r"달력\s*그래픽",
        r"모니터\s*화면", r"타이핑", r"스마트폰\s*뉴스", r"웨이보\s*화면", r"뉴스\s*피드",
        r"boiler", r"steam", r"diagram", r"sketch", r"pathology", r"anatomy", r"crt\s*monitor",
        r"smartphone\s*news", r"scrolling\s*weibo", r"calendar\s*graphic",
        r"nồi\s*nước", r"hơi\s*nước", r"sơ\s*đồ", r"giải\s*phẫu", r"máy\s*tính", r"điện\s*thoại",
        # Generic police / investigation actions without primary documents
        r"호구부", r"가가호호", r"방문\s*조사", r"전수조사", r"상황판\s*앞에서\s*회의", r"형사들이\s*상황판",
        r"incident\s*board", r"door\s*to\s*door", r"census\s*investigation",
    ]

    # Specific authentic evidence & real identifiable character patterns
    positive_evidence_patterns = [
        # Real person identification / portraits / authentic archives
        r"증명사진", r"신분증", r"생전\s*유일한", r"흑백\s*사진", r"흑백\s*단발머리", r"피해자\s*사진", r"용의자\s*사진",
        r"실제\s*사진", r"실제\s*인물", r"인터뷰\s*아카이브", r"노부모의\s*인터뷰", r"아버지.*인터뷰",
        r"취재진\s*앞에\s*서\s*있는\s*실제", r"실제\s*보도\s*영상", r"언니.*변호사.*소장",
        r"mugshot", r"id\s*photo", r"passport\s*photo", r"actual\s*photo", r"victim\s*portrait",
        r"real\s*interview", r"lawsuit\s*footage", r"court\s*footage", r"cctv\s*footage",
        r"ảnh\s*thẻ", r"chân\s*dung\s*thật", r"căn\s*cước", r"ảnh\s*gốc", r"phỏng\s*vấn\s*thật",
        r"video\s*hiện\s*trường\s*thật", r"báo\s*chí\s*phỏng\s*vấn\s*thật",
        # Primary official documents / government records / legal filings
        r"공식\s*성명문", r"도장\s*찍힌\s*공식", r"공안부.*공식\s*발표", r"인민법원.*소장",
        r"official\s*seal\s*document", r"official\s*statement", r"court\s*filing",
        r"văn\s*bản\s*chính\s*thức", r"con\s*dấu", r"đơn\s*kiện.*toà",
    ]

    has_positive = any(re.search(pat, combined) for pat in positive_evidence_patterns)
    has_generic = any(re.search(pat, combined) for pat in generic_patterns)

    if has_generic and not has_positive:
        return False
    return has_positive


def _route_for(
    strategy: str,
    source_priority: str,
    metadata: dict[str, Any] | None = None,
    unit: str = "",
) -> str:
    if strategy == "full_ai":
        return "ai_visual"
    if strategy in {"full_footage", "footage_first"}:
        return "footage"
    if strategy in {"semi_content", "ban_content", "edit_footage", "edit_direct_footage"}:
        vtype = str((metadata or {}).get("visual_type") or "").strip().lower()
        if str(source_priority or "").strip().lower() == "ai_ok" or vtype == "ai_reconstruction":
            return "ai_visual"
        return "footage"
    if strategy in {"evidence_footage", "selective_footage", "evidence_first"}:
        return "footage" if _is_core_evidence_or_character(metadata, unit) else "ai_visual"
    return "ai_visual" if str(source_priority or "").strip().lower() == "ai_ok" else "footage"


def _clean_ai_scene_focus(unit: str, visual: str) -> str:
    """Strip UI/HUD/typography/caption pollution so AI image prompts focus strictly on pure scene action."""
    text = str(visual or "").strip()
    # Remove bracketed tags like [Forensic Noir Full-AI | Chia đôi màn hình đối chiếu | ...]
    text = re.sub(r"\[[^\]]*\]\s*", "", text)
    # Remove Clause focus (...) quotes and trailing typography/annotation directives
    text = re.sub(r'(?i)\bClause\s+focus\s*\([^)]*\)\s*:\s*"[^"]*"\s*[—\-–]*\s*', "", text)
    text = re.sub(r"(?i)Cold\s+desaturated\s+noir\s+color\s+grade[^.]*\.", "", text)
    text = re.sub(r"(?i)authentic\s+Chinese\s+judicial/public\s+security\s+archival\s+typography[^.]*\.", "", text)
    text = re.sub(r"(?i)anchored\s+mobile-readable\s+annotation\s+highlight[^.]*\.", "", text)
    text = re.sub(r"(?i)\b(?:>=?\s*\d+\s*px|Pretendard|KeyMetricCallout|160%\s*Macro\s*Loupe|Split-Screen\s*A/B|scan\s*line\s*highlight|telemetry\s*label|callout\s*card)\b[^.]*\.?", "", text)
    # Remove generic story-group comparison file headers ("... vs ... 대조 파일.") when a concrete unit exists
    if unit.strip():
        text = re.sub(r"[^.]*\bvs\b[^.]*대조\s*파일\.?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" .,-—–")
    clean_unit = re.sub(r"\s+", " ", str(unit or "")).strip()
    if not text or text == clean_unit:
        return clean_unit
    return f"{clean_unit} ({text})"


def _prompt_for(
    unit: str,
    metadata: dict[str, Any],
    route: str,
    style_settings: dict[str, Any] | None = None,
) -> str:
    visual = str(metadata.get("visual_description") or "").strip()
    purpose = str(metadata.get("purpose") or "").strip()
    base = visual or unit
    if route == "footage":
        if purpose and purpose.lower() not in base.lower():
            base = f"{base}. {purpose}"
        return f"Authentic documentary footage matching: {base}"[:520]

    scene_focus = _clean_ai_scene_focus(unit, visual)
    style = style_settings or {}
    style_mode = str(style.get("style_mode") or "auto").strip().lower()
    style_preset = str(style.get("style_preset") or "").strip()
    style_prompt = str(style.get("style_prompt") or "").strip()
    style_ref = str(style.get("style_reference_image") or "").strip()
    has_ref = bool(style_ref and Path(style_ref).is_file())
    no_text_rule = (
        "SCENE FOCUS RULE: Depict the physical scene, characters, environment, lighting, and action of this moment in a unified full-bleed 16:9 frame."
    )
    if style_prompt or has_ref:
        parts: list[str] = []
        if style_mode == "preset" and style_preset and style_prompt:
            parts.append(f"[Preset: {style_preset}] {style_prompt}")
        elif style_prompt:
            parts.append(style_prompt)
        if has_ref:
            parts.append(
                "A visual style reference image is attached. MANDATORY CHARACTER & COLOR LOCK: Draw ALL human characters as 2D rounded chibi mascot figures strictly copying the exact character design, BRIGHT GOLDEN-YELLOW head and body skin color tone (#FFD43B warm yellow spherical head, yellow hands, and yellow feet — NEVER white skin and NEVER realistic human faces), proportions, bold clean black linework, simple black oval eyes with white specular highlights, thin curved eyebrows, minimal line mouth, and outfit style from the attached reference image."
            )
        parts.append(f"Core scene to illustrate (visual action & setting only, without any text): {scene_focus}.")
        parts.append(no_text_rule)
        return " ".join(parts)[:2400]
    return f"Documentary visual scene: {scene_focus}. {no_text_rule}"[:900]


class VisualsCoordinator:
    def __init__(self, max_chars: int = 110):
        self.max_chars = max(40, int(max_chars))

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError(f"{path.name} must contain a JSON object")
        return data

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _load_style_settings(workspace: Path, job: dict[str, Any]) -> dict[str, Any]:
        try:
            from .ai_visual import AIVisualCoordinator
            return AIVisualCoordinator().settings(workspace, job)
        except Exception:
            return dict(job.get("ai_visual") or {})

    def run(self, job: dict[str, Any], workspace: str | Path) -> StageResult:
        workspace = Path(workspace)
        script = (workspace / "script.md").read_text(encoding="utf-8").strip()
        voice = self._read_json(workspace / "voice_manifest.json")
        current_manifest = self._read_json(workspace / "visual_manifest.json")
        if str(current_manifest.get("source") or "") != STP_MANIFEST_SOURCE:
            # Fresh Plan output: keep an immutable copy before Visuals rewrites it.
            self._write_json(workspace / PLAN_MANIFEST_NAME, current_manifest)
        broad = load_plan_manifest(workspace)
        voice_beats = [item for item in (voice.get("beats") or []) if isinstance(item, dict)]
        if not voice_beats:
            raise RuntimeError("voice_manifest.json has no beats for Visuals/STP")
        voice_text = " ".join(str(item.get("text") or "").strip() for item in voice_beats).strip()
        if _compact(voice_text) != _compact(script):
            raise RuntimeError("Voice text does not cover 100% of script.md; rerun Voice before Visuals/STP")

        plan_by_id: dict[str, dict[str, Any]] = {}
        for item in (broad.get("beats") or []):
            if not isinstance(item, dict):
                continue
            parent_id = str(item.get("parent_beat_id") or item.get("beat_id") or "").strip()
            if parent_id and parent_id not in plan_by_id:
                plan_by_id[parent_id] = item
        strategy = str(job.get("visual_strategy") or "full_footage").strip().lower()
        if strategy == "footage_first":
            strategy = "full_footage"
        elif strategy in {"selective_footage", "evidence_first"}:
            strategy = "evidence_footage"
        elif strategy in {"semi_content", "ban_content", "edit_footage"}:
            strategy = "edit_direct_footage"
        style_settings = self._load_style_settings(workspace, job)
        ai_media_mode = str(
            style_settings.get("ai_media_mode")
            or job.get("ai_media_mode")
            or (job.get("ai_visual") or {}).get("ai_media_mode")
            or ("image" if strategy == "edit_direct_footage" else "mixed")
        ).strip().lower()
        if ai_media_mode not in {"image", "video", "mixed"}:
            ai_media_mode = "image" if strategy == "edit_direct_footage" else "mixed"

        max_selective_ai_beats = max(4, min(20, max(1, len(voice_beats) // 7))) if strategy == "edit_direct_footage" else 0
        selective_ai_count = 0

        refined: list[dict[str, Any]] = []
        prompt_rows: list[dict[str, Any]] = []
        for parent_index, voice_beat in enumerate(voice_beats, 1):
            parent_id = str(voice_beat.get("beat_id") or f"B{parent_index:03d}").strip()
            text = str(voice_beat.get("text") or "").strip()
            units = split_visual_text(text, self.max_chars)
            if not units:
                continue
            metadata = dict(plan_by_id.get(parent_id) or {})
            start = float(voice_beat.get("start_sec") or 0.0)
            end = float(voice_beat.get("end_sec") or start)
            total_duration = max(0.001, end - start)
            weights = [max(1, len(_compact(unit))) for unit in units]
            total_weight = max(1, sum(weights))
            cursor = start
            for unit_index, (unit, weight) in enumerate(zip(units, weights), 1):
                beat_id = f"{parent_id}-V{unit_index:02d}"
                unit_end = end if unit_index == len(units) else cursor + total_duration * weight / total_weight
                source_priority = str(metadata.get("source_priority") or "prefer_real")
                route = _route_for(strategy, source_priority, metadata=metadata, unit=unit)
                if strategy == "edit_direct_footage":
                    if route == "ai_visual":
                        if unit_index > 1 or selective_ai_count >= max_selective_ai_beats:
                            route = "footage"
                        else:
                            selective_ai_count += 1
                    elif unit_index == 1 and selective_ai_count < max_selective_ai_beats and (parent_index == 1 or parent_index % 8 == 0):
                        route = "ai_visual"
                        selective_ai_count += 1
                prompt = _prompt_for(unit, metadata, route, style_settings=style_settings)
                beat = {
                    **metadata,
                    "beat_id": beat_id,
                    "parent_beat_id": parent_id,
                    "narration_text": unit,
                    "start_sec": round(cursor, 3),
                    "end_sec": round(unit_end, 3),
                    "target_duration_sec": round(max(0.001, unit_end - cursor), 3),
                    "source_priority": source_priority,
                    "visual_route": route,
                    "visual_type": "ai_reconstruction" if route == "ai_visual" else "sourced_video",
                    "visual_description": str(metadata.get("visual_description") or unit).strip(),
                    "footage_search_queries": metadata.get("footage_search_queries") or [unit],
                    "framing_motion_intent": str(metadata.get("framing_motion_intent") or "").strip(),
                    "ai_media_mode": ai_media_mode,
                    "ai_motion_required": route == "ai_visual" and ai_media_mode == "video",
                    "prompt": prompt,
                }
                refined.append(beat)
                prompt_rows.append({
                    "beat_id": beat_id,
                    "parent_beat_id": parent_id,
                    "start_sec": beat["start_sec"],
                    "end_sec": beat["end_sec"],
                    "text": unit,
                    "visual_route": route,
                    "ai_media_mode": ai_media_mode,
                    "prompt": prompt,
                })
                cursor = unit_end

        from .vox_engine import VoxSemanticRouter, is_vox_satellite_enabled
        if is_vox_satellite_enabled(job):
            router = VoxSemanticRouter()
            refined = router.route_timeline(refined, job)
            for row in prompt_rows:
                bid = row.get("beat_id")
                matching = next((b for b in refined if b.get("beat_id") == bid), None)
                if matching and matching.get("scene_archetype"):
                    row["scene_archetype"] = matching["scene_archetype"]
                    row["archetype_label"] = matching.get("archetype_label")

        if _compact("".join(item["narration_text"] for item in refined)) != _compact(script):
            raise RuntimeError("Visuals/STP did not preserve 100% of script.md")

        duration = float(voice.get("duration_sec") or (refined[-1]["end_sec"] if refined else 0.0))
        self._write_json(workspace / "visual_manifest.json", {
            "version": 2,
            "source": "visuals_stp_after_voice",
            "target_duration_sec": round(duration, 3),
            "visual_strategy": strategy,
            "ai_media_mode": ai_media_mode,
            "beats": refined,
        })
        self._write_json(workspace / "visual_prompts.json", {
            "version": 1,
            "visual_strategy": strategy,
            "ai_media_mode": ai_media_mode,
            "style": {k: v for k, v in style_settings.items() if k != "style_presets"},
            "prompts": prompt_rows,
        })
        style_tag = ""
        if style_settings.get("style_mode") == "preset" and style_settings.get("style_preset"):
            style_tag = f" · Preset: {style_settings['style_preset']}"
        elif style_settings.get("style_mode") == "custom" and style_settings.get("custom_style"):
            style_tag = " · Phong cách tự nhập"
        if style_settings.get("style_reference_image"):
            style_tag += " + Ảnh tham chiếu"
        return StageResult(
            returncode=0,
            last_message=f"Visuals/STP đã chia {len(refined)} prompt{style_tag} và phủ 100% script",
            log_path=workspace / "visual_prompts.json",
        )
