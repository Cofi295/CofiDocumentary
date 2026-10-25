"""Thumbnail Studio Engine: Fabric.js JSON Layer Composition + NanoThumbnail Safe-Zone & CTR Critique."""
from __future__ import annotations

import base64
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import quote
from uuid import uuid4
import zipfile


CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720

ARCHETYPES: dict[str, dict[str, Any]] = {
    "broadcast_left_heavy": {
        "id": "broadcast_left_heavy",
        "name": "Đài SBS Trái (그것이 알고싶다)",
        "description": "Chủ thể bên phải 1/3, nền tối bên trái 2/3 chứa Badge đỏ + 2 dòng Hook cỡ lớn (Chuẩn True Crime Hàn Quốc).",
        "vignette_style": "left_heavy",
        "vignette_opacity": 0.84,
    },
    "bottom_cinematic": {
        "id": "bottom_cinematic",
        "name": "Điện ảnh Đáy (꼬꼬무 Style)",
        "description": "Chủ thể phía trên, phủ tối 1/3 dưới cùng với chữ căn giữa/trái cực nổi, né hoàn toàn góc 30:15.",
        "vignette_style": "bottom_heavy",
        "vignette_opacity": 0.86,
    },
    "split_duality": {
        "id": "split_duality",
        "name": "Hai Bộ Mặt / Khung Ảnh Phụ (PiP)",
        "description": "Bối cảnh chính + Khung ảnh đối chứng góc phải trên + Mũi tên đỏ chỉ điểm mâu thuẫn.",
        "vignette_style": "left_heavy",
        "vignette_opacity": 0.82,
    },
    "evidence_spotlight": {
        "id": "evidence_spotlight",
        "name": "Khoanh Vùng Pháp Y (Spotlight)",
        "description": "Làm tối hiện trường, dùng Vòng tròn đỏ + Mũi tên 3D chỉ thẳng vào vật chứng quyết định + Con dấu Hồ sơ mật.",
        "vignette_style": "radial_spotlight",
        "vignette_opacity": 0.78,
    },
    "right_heavy_confrontation": {
        "id": "right_heavy_confrontation",
        "name": "Đối Diện Bên Phải",
        "description": "Chủ thể bên trái nhìn sang phải, cụm chữ đặt bên phải phía trên vùng cấm thời lượng YouTube.",
        "vignette_style": "right_heavy",
        "vignette_opacity": 0.84,
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _media_url(job_id: str, workspace: Path, file_path: Path) -> str:
    try:
        rel = file_path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        rel = str(file_path)
    mtime = int(file_path.stat().st_mtime) if file_path.exists() else 0
    return f"/api/jobs/{quote(str(job_id))}/media?path={quote(rel)}&v={mtime}"


def discover_job_candidate_images(job_id: str, workspace: Path, job: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Find available clean backgrounds, style references, and AI visual scenes in the project workspace."""
    workspace = workspace.resolve()
    candidates: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}

    def add_candidate(path: Path, label: str, category: str, priority: int = 50) -> None:
        if not path.is_file() or path.suffix.lower() not in allowed_exts:
            return
        try:
            resolved = path.resolve()
            if resolved.stat().st_size < 1024:
                return
            rel = resolved.relative_to(workspace).as_posix()
        except (OSError, ValueError):
            return
        key = str(resolved).lower()
        if key in seen_paths:
            return
        seen_paths.add(key)
        candidates.append({
            "id": f"img_{len(candidates) + 1}",
            "label": label,
            "category": category,
            "path": str(resolved),
            "rel_path": rel,
            "url": _media_url(job_id, workspace, resolved),
            "priority": priority,
            "mtime": resolved.stat().st_mtime,
        })

    # 1. Dedicated thumbnail background images (exclude exported composite thumbnail_*.jpg files!)
    if (workspace / "media" / "thumbnail").is_dir():
        for bg_file in sorted(
            (workspace / "media" / "thumbnail").glob("*"),
            key=lambda p: (0 if p.stem.lower().startswith("thumb_bg_v") else 1, p.name.lower()),
        ):
            stem_lower = bg_file.stem.lower()
            if stem_lower == "thumbnail" or stem_lower.startswith("thumbnail_"):
                continue
            if stem_lower.startswith("thumb_inset"):
                add_candidate(bg_file, f"Ảnh phụ PiP ({bg_file.name})", "thumbnail_inset", priority=96)
            else:
                v_match = re.search(r"thumb_bg_v(\d+)", stem_lower)
                prio = 105 - int(v_match.group(1)) if v_match else 100
                add_candidate(bg_file, f"Ảnh nền sạch ({bg_file.name})", "thumbnail_bg", priority=prio)

    for root_bg in ("thumbnail_bg.jpg", "thumbnail_bg.png", "thumbnail_bg.webp"):
        if (workspace / root_bg).is_file():
            add_candidate(workspace / root_bg, "Ảnh nền Thumbnail chính", "thumbnail_bg", priority=99)

    # 2. AI Visual generated scenes (check both media/ai and media/ai_visual)
    scene_files: list[Path] = []
    for ai_dir_name in ("ai", "ai_visual"):
        ai_dir = workspace / "media" / ai_dir_name
        if ai_dir.is_dir():
            for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
                scene_files.extend(ai_dir.rglob(ext))
    if scene_files:
        scene_files.sort(key=lambda p: (p.name, p.stat().st_mtime if p.exists() else 0))
        # Pick up to 36 evenly distributed scenes across the narrative arc so A/B/C/D variants get distinct contextual frames
        total_scenes = len(scene_files)
        if total_scenes > 36:
            step = total_scenes / 36.0
            selected_scenes = [scene_files[min(total_scenes - 1, int(i * step))] for i in range(36)]
        else:
            selected_scenes = scene_files[:36]
        for idx, sfile in enumerate(selected_scenes):
            stem = sfile.stem.replace("_ai_keyframe", "").upper()
            add_candidate(sfile, f"Phân cảnh AI · {stem}", "ai_scene", priority=92 - min(idx, 30))

    # 3. Footage / Asset stills if any (excluding style_reference and composite thumbnails)
    for folder_name in ("assets", "footage", "media"):
        folder = workspace / folder_name
        if not folder.is_dir():
            continue
        found = 0
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            for fpath in folder.rglob(ext):
                if any(part in fpath.parts for part in (".producer", "posters", "thumbnail", "thumbnails", "style_reference", "ai", "ai_visual")):
                    continue
                if fpath.stem.lower().startswith("thumbnail"):
                    continue
                add_candidate(fpath, f"Tư liệu · {fpath.stem[:28]}", "asset", priority=45)
                found += 1
                if found >= 16:
                    break
            if found >= 16:
                break

    # 4. Style reference image (lowest priority — character sheet on plain background, never default thumbnail background)
    style_ref_dir = workspace / "media" / "style_reference"
    if style_ref_dir.is_dir():
        for ref_file in sorted(style_ref_dir.glob("*"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
            add_candidate(ref_file, "Ảnh tham chiếu nhân vật (Style Lock - Không làm nền)", "style_reference", priority=12)

    candidates.sort(key=lambda item: (int(item.get("priority") or 0), float(item.get("mtime") or 0)), reverse=True)
    return candidates


def build_clean_background_prompt(seo_pack: dict[str, Any], job: dict[str, Any]) -> str:
    """Create a 100% clean (text-free, arrow-free, circle-free) base image prompt for Google Labs Flow."""
    thumb = seo_pack.get("thumbnail") if isinstance(seo_pack.get("thumbnail"), dict) else {}
    raw_prompt = str(thumb.get("clean_bg_prompt") or thumb.get("prompt") or "").strip()
    concept = str(thumb.get("concept") or "").strip()
    subject = str(thumb.get("subject") or "").strip()
    composition = str(thumb.get("composition") or "").strip()
    title = str(job.get("title") or job.get("topic") or "True Crime Documentary").strip()

    # Strip any "TEXT ON THUMBNAIL: ..." or instructions to bake in text, typography, circles, arrows, or inset boxes
    cleaned = re.sub(r"TEXT ON THUMBNAIL\s*:[\s\S]*$", "", raw_prompt, flags=re.IGNORECASE).strip()
    cleaned = re.sub(
        r"(?:render|include|write|add)\s+(?:the\s+)?(?:exact\s+)?(?:korean\s+|vietnamese\s+)?(?:overlay\s+)?(?:text|typography)[^.]*\.",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(
        r"[^.]*(?:dashed\s+white\s+circle|red\s+indicator\s+arrow|top-right\s+inset\s+box|inset\s+box\s+framed|line\s+1\s*['\"]|line\s+2\s*['\"])[^.]*\.",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    if not cleaned:
        parts = [
            f"High-impact 16:9 YouTube documentary thumbnail base image for: {title}.",
            f"Concept: {concept}." if concept else "",
            f"Main subject: {subject}." if subject else "Dramatic investigation atmosphere, high-contrast cinematic lighting, cold forensic color grading.",
            f"Composition: {composition}." if composition else "Place the primary focal subject on the right third of the frame with intense dramatic rim lighting, leaving dark shadowy negative space on the left two-thirds or bottom third for broadcast typography.",
        ]
        cleaned = " ".join(p for p in parts if p)

    clean_suffix = (
        " IMPORTANT: Clean base image only — DO NOT render any text, letters, words, hangul, numbers, watermarks, logos, arrows, circles, or inset frames anywhere in the image. "
        "Keep 35-40% intentional dark negative space on the bottom third or left side so external vector typography, arrows, and circles pop with maximum contrast."
    )
    if "do not render any text" not in cleaned.lower():
        cleaned = f"{cleaned}\n\n{clean_suffix}".strip()
    return cleaned


def build_variant_layers(
    archetype: str,
    *,
    badge_text: str,
    line_1: str,
    line_2: str,
    line_1_color: str = "#ffffff",
    line_2_color: str = "#fbbf24",
    badge_bg: str = "#dc2626",
    badge_color: str = "#ffffff",
    stamp_text: str = "극비 수사 파일",
    inset_image_url: str = "",
    font_family: str = "",
) -> list[dict[str, Any]]:
    """Generate Fabric.js-compatible JSON layers for a given thumbnail archetype."""
    arch = ARCHETYPES.get(archetype) or ARCHETYPES["broadcast_left_heavy"]
    arch_id = arch["id"]

    # Local static Korean broadcast font stack (zero contour-overlap or subset missing bugs)
    font_family = (
        str(font_family or "").strip()
        or "'Paperlogy Black', 'Gmarket Sans Bold', 'SB Aggro Bold', 'GongGothic Bold', 'Pretendard Black', 'SCoreDream Black', 'Malgun Gothic', sans-serif"
    )

    layers: list[dict[str, Any]] = [
        {
            "id": "vignette",
            "type": "vignette",
            "name": "Lớp phủ tối Điện ảnh (Vignette)",
            "style": arch["vignette_style"],
            "opacity": arch["vignette_opacity"],
            "color": "#04070d",
            "visible": True,
            "locked": True,
        }
    ]

    badge_label = str(badge_text or "중국 실화 사건").strip()
    badge_auto_w = max(340, min(680, int(len(badge_label) * 34 + 68)))

    if arch_id == "broadcast_left_heavy":
        layers.extend([
            {
                "id": "forensic_circle",
                "type": "circle",
                "name": "Vòng tròn đỏ khoanh vùng",
                "left": 860,
                "top": 120,
                "width": 260,
                "height": 260,
                "stroke": "#ef4444",
                "strokeWidth": 10,
                "dashed": False,
                "angle": 0,
                "visible": False,
                "opacity": 0.95,
            },
            {
                "id": "forensic_arrow",
                "type": "arrow",
                "name": "Mũi tên đỏ chỉ điểm",
                "left": 650,
                "top": 195,
                "width": 175,
                "height": 66,
                "fill": "#ef4444",
                "stroke": "#ffffff",
                "strokeWidth": 4,
                "angle": -8,
                "visible": True,
                "opacity": 0.96,
            },
            {
                "id": "stamp",
                "type": "stamp",
                "name": "Con dấu Hồ sơ (Stamp)",
                "text": stamp_text or "실화 사건 파일",
                "left": 64,
                "top": 44,
                "width": 250,
                "height": 58,
                "fontSize": 28,
                "fontFamily": font_family,
                "fill": "#f87171",
                "stroke": "#ef4444",
                "strokeWidth": 4,
                "angle": -4,
                "visible": False,
                "opacity": 0.92,
            },
            {
                "id": "inset_photo",
                "type": "inset_image",
                "name": "Khung ảnh phụ (PiP)",
                "src": inset_image_url,
                "left": 850,
                "top": 42,
                "width": 360,
                "height": 290,
                "borderColor": "#ef4444",
                "borderWidth": 6,
                "angle": 2,
                "visible": False,
                "opacity": 1.0,
            },
            {
                "id": "badge",
                "type": "badge",
                "name": "Nhãn Chuyên mục (Badge)",
                "text": badge_label,
                "left": 64,
                "top": 362,
                "width": badge_auto_w,
                "height": 68,
                "fontSize": 38,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": badge_color,
                "bgColor": badge_bg,
                "borderColor": "#ffffff",
                "borderWidth": 3,
                "borderRadius": 10,
                "angle": 0,
                "visible": bool(badge_text),
                "opacity": 1.0,
            },
            {
                "id": "line_1",
                "type": "textbox",
                "name": "Dòng 1 · Dẫn chuyện (Line 1)",
                "text": line_1 or "28년 숨어 지낸 매점 아저씨",
                "left": 64,
                "top": 452,
                "width": 1080,
                "height": 108,
                "fontSize": 78,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": line_1_color,
                "stroke": "#000000",
                "strokeWidth": 18,
                "shadowColor": "rgba(0,0,0,0.92)",
                "shadowBlur": 18,
                "textAlign": "left",
                "angle": 0,
                "visible": True,
                "opacity": 1.0,
            },
            {
                "id": "line_2",
                "type": "textbox",
                "name": "Dòng 2 · Từ khóa Sốc (Line 2)",
                "text": line_2 or "단 하나의 지문이 밝힌 진실",
                "left": 64,
                "top": 564,
                "width": 1140,
                "height": 118,
                "fontSize": 86,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": line_2_color,
                "stroke": "#000000",
                "strokeWidth": 20,
                "shadowColor": "rgba(0,0,0,0.95)",
                "shadowBlur": 22,
                "textAlign": "left",
                "angle": 0,
                "visible": True,
                "opacity": 1.0,
            },
        ])
    elif arch_id == "bottom_cinematic":
        layers.extend([
            {
                "id": "forensic_circle",
                "type": "circle",
                "name": "Vòng tròn đỏ khoanh vùng",
                "left": 510,
                "top": 95,
                "width": 260,
                "height": 260,
                "stroke": "#ef4444",
                "strokeWidth": 10,
                "dashed": False,
                "angle": 0,
                "visible": False,
                "opacity": 0.95,
            },
            {
                "id": "forensic_arrow",
                "type": "arrow",
                "name": "Mũi tên đỏ chỉ điểm",
                "left": 935,
                "top": 155,
                "width": 185,
                "height": 74,
                "fill": "#ff1f1f",
                "stroke": "#ffffff",
                "strokeWidth": 5,
                "angle": -16,
                "flipX": True,
                "visible": True,
                "opacity": 0.98,
            },
            {
                "id": "stamp",
                "type": "stamp",
                "name": "Con dấu Hồ sơ (Stamp)",
                "text": stamp_text or "충격 실화",
                "left": 56,
                "top": 44,
                "width": 230,
                "height": 56,
                "fontSize": 28,
                "fontFamily": font_family,
                "fill": "#fbbf24",
                "stroke": "#f59e0b",
                "strokeWidth": 4,
                "angle": -5,
                "visible": False,
                "opacity": 0.95,
            },
            {
                "id": "inset_photo",
                "type": "inset_image",
                "name": "Khung ảnh phụ (PiP)",
                "src": inset_image_url,
                "left": 880,
                "top": 40,
                "width": 340,
                "height": 280,
                "borderColor": "#ffffff",
                "borderWidth": 5,
                "angle": 0,
                "visible": False,
                "opacity": 1.0,
            },
            {
                "id": "badge",
                "type": "textbox",
                "name": "Tag góc trái trên (Xanh lá @판세의이면)",
                "text": badge_label,
                "left": 44,
                "top": 36,
                "width": max(440, badge_auto_w),
                "height": 68,
                "fontSize": 50,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": badge_color if badge_color and badge_color.lower() != "#ffffff" else "#39ff14",
                "bgColor": "transparent",
                "stroke": "#000000",
                "strokeWidth": 16,
                "shadowColor": "rgba(0,0,0,0.95)",
                "shadowBlur": 16,
                "textAlign": "left",
                "angle": 0,
                "visible": bool(badge_text),
                "opacity": 0.98,
            },
            {
                "id": "line_1",
                "type": "textbox",
                "name": "Dòng 1 · Hook Vàng Cỡ Lớn (Line 1)",
                "text": line_1 or "\"아들 대학 보내려 멈췄다\"",
                "left": 68,
                "top": 452,
                "width": 1100,
                "height": 105,
                "fontSize": 80,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": line_1_color if line_1_color and line_1_color.lower() != "#ffffff" else "#ffe600",
                "stroke": "#000000",
                "strokeWidth": 22,
                "shadowColor": "rgba(0,0,0,0.94)",
                "shadowBlur": 18,
                "textAlign": "left",
                "angle": 0,
                "visible": True,
                "opacity": 1.0,
            },
            {
                "id": "line_2",
                "type": "textbox",
                "name": "Dòng 2 · Từ khóa Đỏ Cực Đại (Line 2)",
                "text": line_2 or "학교 매점 주인의 소름 돋는 정체!",
                "left": 68,
                "top": 562,
                "width": 1144,
                "height": 115,
                "fontSize": 88,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": line_2_color if line_2_color else "#ff2424",
                "stroke": "#000000",
                "strokeWidth": 24,
                "shadowColor": "rgba(0,0,0,0.96)",
                "shadowBlur": 22,
                "textAlign": "left",
                "angle": 0,
                "visible": True,
                "opacity": 1.0,
            },
        ])
    elif arch_id == "split_duality":
        layers.extend([
            {
                "id": "inset_photo",
                "type": "inset_image",
                "name": "Khung ảnh phụ đối chứng (PiP)",
                "src": inset_image_url,
                "left": 836,
                "top": 44,
                "width": 384,
                "height": 330,
                "borderColor": "#ef4444",
                "borderWidth": 6,
                "angle": 2,
                "visible": True,
                "opacity": 1.0,
            },
            {
                "id": "forensic_circle",
                "type": "circle",
                "name": "Vòng tròn đỏ khoanh vùng",
                "left": 890,
                "top": 80,
                "width": 250,
                "height": 250,
                "stroke": "#ef4444",
                "strokeWidth": 9,
                "dashed": False,
                "angle": 0,
                "visible": False,
                "opacity": 0.95,
            },
            {
                "id": "forensic_arrow",
                "type": "arrow",
                "name": "Mũi tên đỏ đối chiếu",
                "left": 665,
                "top": 195,
                "width": 165,
                "height": 60,
                "fill": "#fbbf24",
                "stroke": "#000000",
                "strokeWidth": 4,
                "angle": -6,
                "visible": True,
                "opacity": 0.98,
            },
            {
                "id": "stamp",
                "type": "stamp",
                "name": "Con dấu Hồ sơ (Stamp)",
                "text": stamp_text or "두 얼굴의 범인",
                "left": 64,
                "top": 56,
                "width": 250,
                "height": 58,
                "fontSize": 28,
                "fontFamily": font_family,
                "fill": "#f87171",
                "stroke": "#ef4444",
                "strokeWidth": 4,
                "angle": -3,
                "visible": True,
                "opacity": 0.95,
            },
            {
                "id": "badge",
                "type": "badge",
                "name": "Nhãn Chuyên mục (Badge)",
                "text": badge_label,
                "left": 64,
                "top": 340,
                "width": badge_auto_w,
                "height": 66,
                "fontSize": 37,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": badge_color,
                "bgColor": badge_bg,
                "borderColor": "#ffffff",
                "borderWidth": 3,
                "borderRadius": 10,
                "angle": 0,
                "visible": bool(badge_text),
                "opacity": 1.0,
            },
            {
                "id": "line_1",
                "type": "textbox",
                "name": "Dòng 1 · Dẫn chuyện (Line 1)",
                "text": line_1 or "낮에는 친절한 이웃",
                "left": 64,
                "top": 430,
                "width": 960,
                "height": 108,
                "fontSize": 76,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": line_1_color,
                "stroke": "#000000",
                "strokeWidth": 16,
                "shadowColor": "rgba(0,0,0,0.94)",
                "shadowBlur": 18,
                "textAlign": "left",
                "angle": 0,
                "visible": True,
                "opacity": 1.0,
            },
            {
                "id": "line_2",
                "type": "textbox",
                "name": "Dòng 2 · Từ khóa Sốc (Line 2)",
                "text": line_2 or "밤에는 일급 수배범?",
                "left": 64,
                "top": 550,
                "width": 1060,
                "height": 120,
                "fontSize": 86,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": "#ef4444" if line_2_color == "#ffffff" else line_2_color,
                "stroke": "#000000",
                "strokeWidth": 18,
                "shadowColor": "rgba(0,0,0,0.96)",
                "shadowBlur": 22,
                "textAlign": "left",
                "angle": 0,
                "visible": True,
                "opacity": 1.0,
            },
        ])
    elif arch_id == "evidence_spotlight":
        layers.extend([
            {
                "id": "forensic_circle",
                "type": "circle",
                "name": "Vòng tròn đỏ khoanh vật chứng",
                "left": 790,
                "top": 120,
                "width": 310,
                "height": 310,
                "stroke": "#ef4444",
                "strokeWidth": 12,
                "dashed": True,
                "angle": 0,
                "visible": True,
                "opacity": 0.98,
            },
            {
                "id": "forensic_arrow",
                "type": "arrow",
                "name": "Mũi tên đỏ chỉ vật chứng",
                "left": 605,
                "top": 240,
                "width": 175,
                "height": 66,
                "fill": "#ef4444",
                "stroke": "#ffffff",
                "strokeWidth": 4,
                "angle": 4,
                "visible": True,
                "opacity": 0.98,
            },
            {
                "id": "stamp",
                "type": "stamp",
                "name": "Con dấu Hồ sơ mật (Stamp)",
                "text": stamp_text or "극비 수사 기록",
                "left": 64,
                "top": 54,
                "width": 260,
                "height": 60,
                "fontSize": 30,
                "fontFamily": font_family,
                "fill": "#ef4444",
                "stroke": "#ef4444",
                "strokeWidth": 4,
                "angle": -6,
                "visible": True,
                "opacity": 0.96,
            },
            {
                "id": "inset_photo",
                "type": "inset_image",
                "name": "Khung ảnh phụ (PiP)",
                "src": inset_image_url,
                "left": 860,
                "top": 48,
                "width": 350,
                "height": 290,
                "borderColor": "#fbbf24",
                "borderWidth": 5,
                "angle": 0,
                "visible": False,
                "opacity": 1.0,
            },
            {
                "id": "badge",
                "type": "badge",
                "name": "Nhãn Chuyên mục (Badge)",
                "text": badge_label,
                "left": 64,
                "top": 340,
                "width": badge_auto_w,
                "height": 64,
                "fontSize": 36,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": badge_color,
                "bgColor": badge_bg,
                "borderColor": "#ffffff",
                "borderWidth": 3,
                "borderRadius": 10,
                "angle": 0,
                "visible": bool(badge_text),
                "opacity": 1.0,
            },
            {
                "id": "line_1",
                "type": "textbox",
                "name": "Dòng 1 · Dẫn chuyện (Line 1)",
                "text": line_1 or "현장에 남겨진 단서",
                "left": 64,
                "top": 424,
                "width": 840,
                "height": 108,
                "fontSize": 74,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": line_1_color,
                "stroke": "#000000",
                "strokeWidth": 16,
                "shadowColor": "rgba(0,0,0,0.94)",
                "shadowBlur": 18,
                "textAlign": "left",
                "angle": 0,
                "visible": True,
                "opacity": 1.0,
            },
            {
                "id": "line_2",
                "type": "textbox",
                "name": "Dòng 2 · Từ khóa Sốc (Line 2)",
                "text": line_2 or "형사들이 찾은 결정적 증거",
                "left": 64,
                "top": 540,
                "width": 920,
                "height": 116,
                "fontSize": 84,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": line_2_color,
                "stroke": "#000000",
                "strokeWidth": 18,
                "shadowColor": "rgba(0,0,0,0.96)",
                "shadowBlur": 22,
                "textAlign": "left",
                "angle": 0,
                "visible": True,
                "opacity": 1.0,
            },
        ])
    else:  # right_heavy_confrontation
        layers.extend([
            {
                "id": "forensic_circle",
                "type": "circle",
                "name": "Vòng tròn đỏ khoanh vùng",
                "left": 110,
                "top": 140,
                "width": 260,
                "height": 260,
                "stroke": "#ef4444",
                "strokeWidth": 10,
                "dashed": False,
                "angle": 0,
                "visible": False,
                "opacity": 0.95,
            },
            {
                "id": "forensic_arrow",
                "type": "arrow",
                "name": "Mũi tên đỏ chỉ điểm",
                "left": 380,
                "top": 270,
                "width": 160,
                "height": 60,
                "fill": "#ef4444",
                "stroke": "#ffffff",
                "strokeWidth": 4,
                "angle": 185,
                "visible": True,
                "opacity": 0.96,
            },
            {
                "id": "stamp",
                "type": "stamp",
                "name": "Con dấu Hồ sơ (Stamp)",
                "text": stamp_text or "실화 사건 파일",
                "left": 920,
                "top": 52,
                "width": 250,
                "height": 58,
                "fontSize": 28,
                "fontFamily": font_family,
                "fill": "#fbbf24",
                "stroke": "#f59e0b",
                "strokeWidth": 4,
                "angle": 4,
                "visible": False,
                "opacity": 0.92,
            },
            {
                "id": "inset_photo",
                "type": "inset_image",
                "name": "Khung ảnh phụ (PiP)",
                "src": inset_image_url,
                "left": 56,
                "top": 48,
                "width": 350,
                "height": 290,
                "borderColor": "#ef4444",
                "borderWidth": 6,
                "angle": -2,
                "visible": False,
                "opacity": 1.0,
            },
            {
                "id": "badge",
                "type": "badge",
                "name": "Nhãn Chuyên mục (Badge)",
                "text": badge_text or "중국 실화 사건",
                "left": 860,
                "top": 170,
                "width": 340,
                "height": 66,
                "fontSize": 37,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": badge_color,
                "bgColor": badge_bg,
                "borderColor": "#ffffff",
                "borderWidth": 3,
                "borderRadius": 10,
                "angle": 0,
                "visible": bool(badge_text),
                "opacity": 1.0,
            },
            {
                "id": "line_1",
                "type": "textbox",
                "name": "Dòng 1 · Dẫn chuyện (Line 1)",
                "text": line_1 or "28년 숨어 지낸 매점 아저씨",
                "left": 450,
                "top": 265,
                "width": 750,
                "height": 108,
                "fontSize": 74,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": line_1_color,
                "stroke": "#000000",
                "strokeWidth": 16,
                "shadowColor": "rgba(0,0,0,0.94)",
                "shadowBlur": 18,
                "textAlign": "right",
                "angle": 0,
                "visible": True,
                "opacity": 1.0,
            },
            {
                "id": "line_2",
                "type": "textbox",
                "name": "Dòng 2 · Từ khóa Sốc (Line 2)",
                "text": line_2 or "단 하나의 지문이 밝힌 진실",
                "left": 420,
                "top": 388,
                "width": 780,
                "height": 120,
                "fontSize": 84,
                "fontFamily": font_family,
                "fontWeight": "900",
                "fill": line_2_color,
                "stroke": "#000000",
                "strokeWidth": 18,
                "shadowColor": "rgba(0,0,0,0.96)",
                "shadowBlur": 22,
                "textAlign": "right",
                "angle": 0,
                "visible": True,
                "opacity": 1.0,
            },
        ])

    return layers


def evaluate_variant_ctr(
    variant: dict[str, Any],
    design: dict[str, Any] | None = None,
    channel_dna: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute multi-dimensional CTR prediction & A/B test readiness scorecard for a single variant."""
    design = design or {}
    layers = variant.get("layers") if isinstance(variant.get("layers"), list) else []
    by_id = {str(layer.get("id") or ""): layer for layer in layers if isinstance(layer, dict)}
    line_1 = by_id.get("line_1") or {}
    line_2 = by_id.get("line_2") or {}
    badge = by_id.get("badge") or {}
    vignette = by_id.get("vignette") or {}

    checks: list[dict[str, Any]] = []
    strengths: list[str] = []
    warnings: list[str] = []

    # Check 1: YouTube Bottom-Right Timestamp Safe Zone (x: 1050..1280, y: 620..720)
    safe_zone_ok = True
    for text_layer in (line_1, line_2, badge):
        if not text_layer.get("visible", True):
            continue
        left = float(text_layer.get("left") or 0)
        top = float(text_layer.get("top") or 0)
        box_width = float(text_layer.get("width") or 600)
        height = float(text_layer.get("height") or 100)
        txt_str = str(text_layer.get("text") or "").strip()
        fs_val = float(text_layer.get("fontSize") or 72)
        est_w = min(box_width, max(180.0, len(txt_str) * fs_val * 0.68)) if txt_str else box_width
        align = str(text_layer.get("textAlign") or "left").strip().lower()
        if align == "center":
            right = left + (box_width + est_w) / 2.0
        elif align == "right":
            right = left + box_width
        else:
            right = left + est_w
        bottom = top + height
        if right > 1065 and bottom > 625:
            safe_zone_ok = False
            break
    checks.append({
        "id": "safe_zone",
        "label": "An toàn Vùng cấm YouTube (Né nhãn 30:15 góc dưới phải)",
        "passed": safe_zone_ok,
        "detail": "Chữ hoàn toàn nằm ngoài vùng đồng hồ thời lượng YouTube (1060×625)." if safe_zone_ok else "Cảnh báo: Chữ đang lấn vào góc dưới phải — dễ bị nhãn thời lượng 30:15 đè lên.",
    })
    if safe_zone_ok:
        strengths.append("Né 100% vùng đồng hồ thời lượng YouTube 30:15")
    else:
        warnings.append("Chữ bị lấn vào vùng cấm YouTube timestamp (1065x625)")

    # Check 2: Mobile 120px Readability (Font size, stroke, word count)
    t1 = str(line_1.get("text") or "").strip()
    t2 = str(line_2.get("text") or "").strip()
    fs1 = float(line_1.get("fontSize") or 72)
    fs2 = float(line_2.get("fontSize") or 80)
    sw1 = float(line_1.get("strokeWidth") or 14)
    mobile_ok = bool((t1 or t2) and max(fs1, fs2) >= 64 and sw1 >= 10 and len(t1) <= 22 and len(t2) <= 22)

    text_legibility_score = 100
    if not (t1 or t2):
        text_legibility_score -= 40
    if max(fs1, fs2) < 68:
        text_legibility_score -= 15
    if sw1 < 12:
        text_legibility_score -= 10
    w1_count = len(t1.split())
    w2_count = len(t2.split())
    if w1_count > 6 or w2_count > 6:
        text_legibility_score -= 15
        warnings.append("Text overlay dài (> 6 từ/dòng), nên rút gọn để tối ưu di động")
    elif t1 and t2:
        strengths.append(f"Cỡ chữ lớn ({int(max(fs1, fs2))}px) & viền ({int(sw1)}px) nổi bật trên mobile feed 120px")
    text_legibility_score = max(35, min(100, text_legibility_score))

    checks.append({
        "id": "mobile_legibility",
        "label": "Độ nổi bật trên Mobile Feed (Kích thước thu nhỏ 120px)",
        "passed": mobile_ok,
        "detail": f"Cỡ chữ {int(max(fs1, fs2))}px, viền đen {int(sw1)}px, độ dài gọn ({len(t1)}/{len(t2)} ký tự)." if mobile_ok else "Nên rút gọn chữ (≤ 18 ký tự/dòng) và giữ cỡ chữ ≥ 68px kèm viền đen dày.",
    })

    # Check 3: Contrast & Vignette Depth
    vig_ok = bool((vignette.get("visible", True) and float(vignette.get("opacity") or 0) >= 0.55) or float(line_1.get("strokeWidth") or 14) >= 14)
    c1 = str(line_1.get("fill") or "#ffffff").lower()
    c2 = str(line_2.get("fill") or "#fbbf24").lower()
    color_contrast_ok = c1 != c2 or bool(badge.get("visible", True))
    contrast_passed = vig_ok and color_contrast_ok
    checks.append({
        "id": "contrast_hierarchy",
        "label": "Tương phản thị giác & Phân tầng màu chữ (Trắng / Vàng-Đỏ)",
        "passed": contrast_passed,
        "detail": "Tương phản 2 tầng màu chữ trên lớp nền Vignette tối sâu chuẩn Broadcast." if contrast_passed else "Nên bật lớp tối Vignette ≥ 60% và dùng 2 màu tương phản (Trắng + Vàng/Đỏ) cho 2 dòng chữ.",
    })

    # Check 4: Base Background Image Presence
    has_bg = bool(
        str(
            variant.get("background_url")
            or variant.get("background_path")
            or design.get("background_url")
            or design.get("background_path")
            or ""
        ).strip()
    )
    checks.append({
        "id": "base_image",
        "label": "Ảnh nền Điện ảnh (Flow AI / Phân cảnh dự án)",
        "passed": has_bg,
        "detail": "Đã nạp ảnh nền 16:9 kết hợp lớp Typography Vector sắc nét." if has_bg else "Chưa chọn ảnh nền — hãy bấm 'Vẽ ảnh nền bằng Flow' hoặc chọn nhanh 1 cảnh bên dưới.",
    })
    if has_bg:
        strengths.append("Ảnh nền điện ảnh 16:9 sắc nét kết hợp lớp Typography chuẩn")
    else:
        warnings.append("Chưa nạp ảnh nền sạch 16:9")

    # Check 5: Channel DNA Consistency (0 - 100)
    dna_consistency_score = 92
    if channel_dna and isinstance(channel_dna, dict):
        palette = channel_dna.get("color_palette") or {}
        typography = channel_dna.get("typography_preset") or {}
        primary_accent = str(palette.get("primary") or palette.get("accent_highlight") or "").lower()
        if primary_accent and (primary_accent in c1 or primary_accent in c2):
            dna_consistency_score += 4
            strengths.append("Màu sắc chữ tuân thủ bảng màu DNA nhận diện của Kênh")
        font_req = str(typography.get("font_family") or "").lower()
        var_font = str(line_1.get("fontFamily") or "").lower()
        if font_req and any(f in var_font for f in ("pretendard", "gmarket", "paperlogy")):
            dna_consistency_score += 3
        if channel_dna.get("mascot_lock"):
            strengths.append("Duy trì cấu hình linh vật / character lock kênh")
            dna_consistency_score += 3
    else:
        dna_consistency_score = 90
    dna_consistency_score = max(50, min(100, dna_consistency_score))

    # Check 6: Curiosity Gap Score (0 - 100)
    hook_type = str(variant.get("hook_type") or "curiosity_paradox")
    curiosity_gap_score = 88
    combined_text = f"{t1} {t2} {badge.get('text', '')}".lower()
    hook_anchors = [
        "13", "28", "30", "23", "20", "93", "17", "89", "1", "2", "3",
        "đại án", "truy nã", "hung thủ", "vỏ bọc", "dấu vân tay", "bí mật", "hồ sơ",
        "경악", "진실", "범인", "수배범", "조연", "배우", "정체", "비밀", "단서", "지문", "숨어",
        "?", "!", "\"",
    ]
    found_anchors = [a for a in hook_anchors if a in combined_text]
    if len(found_anchors) >= 2:
        curiosity_gap_score = 96
        strengths.append(f"Móc câu tâm lý mạnh với {len(found_anchors)} điểm kích thích tò mò")
    elif len(found_anchors) == 1:
        curiosity_gap_score = 91
    else:
        curiosity_gap_score = 84
    if hook_type in ("curiosity_paradox", "character_evidence", "confrontation_contrast"):
        curiosity_gap_score = min(100, curiosity_gap_score + 3)

    # Check 7: Keyword Alignment Score (0 - 100)
    keyword_alignment_score = 88
    b_text = str(badge.get("text") or variant.get("badge_text") or "").strip()
    if b_text:
        keyword_alignment_score = 95
        strengths.append(f"Nhãn series SEO rõ ràng: '{b_text}'")
    else:
        keyword_alignment_score = 75
        warnings.append("Thiếu nhãn chuyên mục / series SEO của kênh")

    # Check 8: YouTube Policy & Green Monetization Safety
    paired_title = str(variant.get("paired_title") or "").strip()
    _, policy_hits = sanitize_youtube_policy_text(f"{b_text} {t1} {t2} {paired_title}")
    policy_ok = len(policy_hits) == 0
    checks.append({
        "id": "policy_safety",
        "label": "Chuẩn Chính sách YouTube & Bật kiếm tiền Xanh (Green Monetization)",
        "passed": policy_ok,
        "detail": "100% từ ngữ trên Thumbnail & Tiêu đề an toàn chính sách YouTube (0 từ nhạy cảm/vàng tiền)." if policy_ok else f"Cảnh báo từ nhạy cảm cần thay thế: {', '.join(policy_hits)}",
    })
    if policy_ok:
        strengths.append("An toàn 100% chính sách YouTube (Green Dollar Safe)")
    else:
        warnings.append(f"Phát hiện từ nhạy cảm YouTube: {', '.join(policy_hits)}")

    # Check 9: 3-Way Synergy (Visual Context + Thumbnail Hook Text + Video Title)
    bg_rel = str(variant.get("background_path") or design.get("background_path") or "").lower()
    is_contextual_bg = bool(has_bg and "style_reference" not in bg_rel)
    overlap_violation = False
    if paired_title and t1 and t2:
        norm_t = re.sub(r"\s+", "", f"{t1}{t2}").lower()
        norm_title = re.sub(r"\s+", "", paired_title).lower()
        if len(norm_t) >= 8 and norm_t in norm_title:
            overlap_violation = True
    synergy_ok = bool(is_contextual_bg and (t1 or t2) and not overlap_violation)
    checks.append({
        "id": "title_thumb_synergy",
        "label": "Tam giác Bổ trợ 3 chiều (Bối cảnh Ảnh + Text Thumb + Tiêu đề SEO)",
        "passed": synergy_ok,
        "detail": "Ảnh bối cảnh câu chuyện + Text Hook + Tiêu đề bổ trợ hoàn hảo (0% lặp nguyên văn)." if synergy_ok else "Nên dùng ảnh bối cảnh thật của câu chuyện (không dùng ảnh nhân vật nền trắng) và không lặp nguyên văn tiêu đề.",
    })
    if synergy_ok:
        strengths.append("Tam giác bổ trợ Bối cảnh + Text Hook + Tiêu đề chuẩn chuyên gia 10 năm")
    elif not is_contextual_bg:
        warnings.append("Ảnh nền đang dùng ảnh tham chiếu nhân vật thay vì bối cảnh câu chuyện")

    # Composite Readiness Score (0 - 100)
    readiness_score = int(round(
        0.30 * dna_consistency_score +
        0.25 * text_legibility_score +
        0.25 * curiosity_gap_score +
        0.20 * keyword_alignment_score
    ))
    if not safe_zone_ok:
        readiness_score = max(40, readiness_score - 15)
    if not has_bg or not is_contextual_bg:
        readiness_score = max(40, readiness_score - 10)
    if not policy_ok:
        readiness_score = max(40, readiness_score - 20)

    # Predicted CTR Percentage (typical high-performing benchmark: 8.0% - 14.5%)
    predicted_ctr_pct = round(4.5 + (readiness_score / 100.0) * 8.8, 1)

    legacy_score = max(40, min(100, readiness_score))
    verdict = "HIGH_CTR" if legacy_score >= 88 else ("GOOD" if legacy_score >= 75 else "NEEDS_TUNING")

    return {
        "score": legacy_score,
        "verdict": verdict,
        "dna_consistency_score": dna_consistency_score,
        "text_legibility_score": text_legibility_score,
        "curiosity_gap_score": curiosity_gap_score,
        "keyword_alignment_score": keyword_alignment_score,
        "policy_safe": policy_ok,
        "synergy_passed": synergy_ok,
        "predicted_ctr_pct": predicted_ctr_pct,
        "readiness_score": readiness_score,
        "strengths": strengths,
        "warnings": warnings,
        "checks": checks,
        "hook_type": hook_type,
        "hook_badge": str(variant.get("hook_badge") or ""),
    }


def evaluate_thumbnail_ctr(design: dict[str, Any], channel_dna: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate the active thumbnail variant against the NanoThumbnail CTR & Safe-Zone rubric, attaching predictions to all variants."""
    if isinstance(design, dict):
        sanitize_and_repair_thumbnail_design(design)
    variants = design.get("variants") if isinstance(design.get("variants"), list) else []
    active_id = str(design.get("active_variant_id") or "v1")
    active = next((v for v in variants if isinstance(v, dict) and v.get("id") == active_id), variants[0] if variants else {})

    dna = channel_dna or design.get("channel_thumbnail_dna")

    # Attach per-variant CTR scorecard to each variant
    for v in variants:
        if isinstance(v, dict):
            v_scorecard = evaluate_variant_ctr(v, design, channel_dna=dna)
            v["ctr_prediction"] = v_scorecard

    # Return critique for active variant (preserving legacy score, verdict, checks)
    return evaluate_variant_ctr(active, design, channel_dna=dna)


YOUTUBE_POLICY_REPLACEMENTS_ALL: list[tuple[str, str]] = [
    # Korean YouTube policy-sensitive / yellow-dollar terms -> High-CTR Broadcast Forensic terms
    ("연쇄살인사건", "최악의 미제사건"),
    ("연쇄 살인 사건", "최악의 미제사건"),
    ("연쇄살인마", "극악의 1급 수배범"),
    ("연쇄살인범", "극악의 1급 수배범"),
    ("연쇄살인", "연쇄 미제사건"),
    ("토막살인", "엽기 미제사건"),
    ("살인사건", "강력 사건"),
    ("살해사건", "강력 사건"),
    ("살인마", "1급 수배범"),
    ("살인범", "핵심 용의자"),
    ("살인극", "강력 범죄"),
    ("살인", "강력 범죄"),
    ("살해", "범행"),
    ("백골 시신", "백골 흔적"),
    ("머리 없는 시신", "훼손된 현장 흔적"),
    ("시체", "현장 흔적"),
    ("사체", "수습된 흔적"),
    ("토막", "훼손"),
    ("참수", "극단적 범행"),
    ("피투성이", "처참한 현장"),
    ("선혈", "현장 혈흔"),
    ("자살", "극단적 선택"),
    ("성폭행", "중대 범죄"),
    ("강간", "중대 범죄"),
    ("고문", "가혹 행위"),
    ("학살", "대규모 참사"),
    ("마약", "금지 약물"),
    # Vietnamese YouTube policy-sensitive terms -> Safe investigative terms
    ("giết người hàng loạt", "đại án chấn động"),
    ("sát nhân hàng loạt", "hung thủ truy nã đặc biệt"),
    ("vụ án giết người", "kỳ án hình sự"),
    ("kẻ giết người", "kẻ thủ ác"),
    ("sát nhân", "hung thủ"),
    ("giết người", "gây án"),
    ("thi thể không đầu", "dấu vết hiện trường"),
    ("xác chết", "hiện trường"),
    ("phân xác", "phi tang"),
    ("chặt đầu", "ra tay tàn độc"),
    ("máu me", "ám ảnh"),
    ("đẫm máu", "chấn động"),
    ("tự tử", "kết cục bi kịch"),
    ("tự sát", "kết cục bi kịch"),
    ("hiếp dâm", "xâm hại"),
    ("cưỡng hiếp", "xâm hại"),
    ("tra tấn", "bạo hành"),
    ("thảm sát", "bi kịch chấn động"),
    # English YouTube policy-sensitive terms -> Safe investigative terms
    ("serial killer", "most wanted fugitive"),
    ("mass murder", "shocking cold case"),
    ("murder case", "criminal investigation"),
    ("murderer", "prime suspect"),
    ("decapitated", "mutilated"),
    ("dismembered", "concealed"),
    ("dead body", "crime scene evidence"),
    ("corpse", "forensic remains"),
    ("suicide", "tragic end"),
    ("sexual assault", "felony offense"),
    ("rape", "felony offense"),
    ("torture", "brutal interrogation"),
    ("gore", "graphic evidence"),
]

STALE_FALLBACK_TEXT_MARKERS: set[str] = {
    "28년 숨어 지낸 범인",
    "단 하나의 결정적 단서",
    "23만 명 중 찾아낸 1명",
    "낮에는 모범적인 이웃",
    "밤에는 일급 수배범?",
    "28 NĂM ẨN MÌNH",
    "DẤU VÂN TAY TỐ CÁO",
    "1 GIỌT MÁU VẠCH TRẦN",
}


def sanitize_youtube_policy_text(text: str) -> tuple[str, list[str]]:
    """Replace YouTube policy-violating / yellow-dollar words with high-CTR policy-safe investigative expressions."""
    raw = str(text or "")
    if not raw:
        return "", []
    cleaned = raw
    replaced: list[str] = []
    for bad, good in YOUTUBE_POLICY_REPLACEMENTS_ALL:
        pattern = re.compile(re.escape(bad), flags=re.IGNORECASE)
        if pattern.search(cleaned):
            replaced.append(bad)
            cleaned = pattern.sub(good, cleaned)
    return cleaned, replaced


def _enforce_title_primary_keyword(title: str, primary_kw: str, placement_rule: str) -> str:
    t = str(title or "").strip()
    kw = str(primary_kw or "").strip()
    if not t or not kw:
        return t
    if kw.lower() in t.lower():
        return t
    rule = str(placement_rule or "smart_seo_flexible").strip().lower()
    if rule == "prefix_entity_location":
        if not t.startswith(kw):
            return f"{kw} {t}"
        return t
    if rule == "suffix_pipe":
        return f"{t} | {kw}"
    if kw == "중국 실화 사건" or rule in ("prefix_bracket", "smart_seo_flexible"):
        # Replace generic brackets like [중국에서 있었던 실제 사례] if present
        t = re.sub(r"^\[[^\]]*중국[^\]]*\]\s*", "", t).strip()
        if kw not in t:
            return f"[{kw}] {t}"
    return t


def enforce_seo_package_expert_rules(
    seo_pack: dict[str, Any],
    job: dict[str, Any],
    ref_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Enforce 10-year YouTube SEO & Thumbnail Design Expert rules, Profile Primary Keyword Lock, and YouTube Policy safety."""
    if not isinstance(seo_pack, dict) or not seo_pack:
        return seo_pack, False
    changed = False
    ref_context = ref_context if isinstance(ref_context, dict) else {}
    seo_dna = (
        (ref_context.get("seo_keyword_dna") if isinstance(ref_context.get("seo_keyword_dna"), dict) else None)
        or (job.get("seo_keyword_dna") if isinstance(job.get("seo_keyword_dna"), dict) else None)
        or {}
    )
    framework = seo_pack.get("channel_framework") if isinstance(seo_pack.get("channel_framework"), dict) else {}
    primary_kw = str(
        seo_dna.get("primary_title_keyword")
        or framework.get("series_key")
        or ""
    ).strip()
    placement_rule = str(seo_dna.get("keyword_placement_rule") or "smart_seo_flexible").strip()
    replaced_log: list[str] = []

    # 1. Sanitize & enforce primary keyword on recommended_title
    rec_title = str(seo_pack.get("recommended_title") or "").strip()
    if rec_title:
        clean_t, hits = sanitize_youtube_policy_text(rec_title)
        replaced_log.extend(hits)
        clean_t = _enforce_title_primary_keyword(clean_t, primary_kw, placement_rule)
        if clean_t != rec_title:
            seo_pack["recommended_title"] = clean_t
            changed = True

    rec_title_vi = str(seo_pack.get("recommended_title_vi") or "").strip()
    if rec_title_vi:
        clean_t_vi, hits = sanitize_youtube_policy_text(rec_title_vi)
        replaced_log.extend(hits)
        if clean_t_vi != rec_title_vi:
            seo_pack["recommended_title_vi"] = clean_t_vi
            changed = True

    # 2. Sanitize & enforce primary keyword on title_options and title_options_vi
    if isinstance(seo_pack.get("title_options"), list):
        new_titles: list[str] = []
        for t in seo_pack["title_options"]:
            clean_t, hits = sanitize_youtube_policy_text(str(t or "").strip())
            replaced_log.extend(hits)
            clean_t = _enforce_title_primary_keyword(clean_t, primary_kw, placement_rule)
            new_titles.append(clean_t)
        if new_titles != seo_pack["title_options"]:
            seo_pack["title_options"] = new_titles
            changed = True

    if isinstance(seo_pack.get("title_options_vi"), list):
        new_titles_vi: list[str] = []
        for t in seo_pack["title_options_vi"]:
            clean_t, hits = sanitize_youtube_policy_text(str(t or "").strip())
            replaced_log.extend(hits)
            new_titles_vi.append(clean_t)
        if new_titles_vi != seo_pack["title_options_vi"]:
            seo_pack["title_options_vi"] = new_titles_vi
            changed = True

    # 3. Sanitize description, keywords, tags, and title_options_details
    desc = str(seo_pack.get("description") or "")
    if desc:
        clean_desc, hits = sanitize_youtube_policy_text(desc)
        replaced_log.extend(hits)
        if clean_desc != desc:
            seo_pack["description"] = clean_desc
            changed = True

    for list_key in ("keywords", "tags"):
        if isinstance(seo_pack.get(list_key), list):
            cleaned_list: list[str] = []
            for item in seo_pack[list_key]:
                c_item, hits = sanitize_youtube_policy_text(str(item or "").strip())
                replaced_log.extend(hits)
                if c_item and c_item not in cleaned_list:
                    cleaned_list.append(c_item)
            if primary_kw and primary_kw not in cleaned_list:
                cleaned_list.insert(0, primary_kw)
            if cleaned_list != seo_pack[list_key]:
                seo_pack[list_key] = cleaned_list
                changed = True

    # Ensure mandatory hashtags from profile DNA
    mandatory_tags = seo_dna.get("mandatory_hashtags") if isinstance(seo_dna.get("mandatory_hashtags"), list) else []
    if mandatory_tags:
        cur_hashtags = [str(h).strip() for h in (seo_pack.get("hashtags") or []) if str(h).strip()]
        for mh in mandatory_tags:
            mh_str = str(mh).strip()
            if mh_str and mh_str not in cur_hashtags:
                cur_hashtags.append(mh_str)
                changed = True
        seo_pack["hashtags"] = cur_hashtags

    if isinstance(seo_pack.get("title_options_details"), list):
        for detail in seo_pack["title_options_details"]:
            if not isinstance(detail, dict):
                continue
            for k in ("title_ko", "title_vi", "thumb_text_ko", "thumb_text_vi", "synergy_vi"):
                val = str(detail.get(k) or "")
                if val:
                    c_val, hits = sanitize_youtube_policy_text(val)
                    replaced_log.extend(hits)
                    if k == "title_ko":
                        c_val = _enforce_title_primary_keyword(c_val, primary_kw, placement_rule)
                    if c_val != val:
                        detail[k] = c_val
                        changed = True

    # 4. Sanitize thumbnail & overlay_text_options
    thumb = seo_pack.get("thumbnail") if isinstance(seo_pack.get("thumbnail"), dict) else {}
    if thumb:
        ov_txt = str(thumb.get("overlay_text") or "")
        if ov_txt:
            c_ov, hits = sanitize_youtube_policy_text(ov_txt)
            replaced_log.extend(hits)
            if c_ov != ov_txt:
                thumb["overlay_text"] = c_ov
                changed = True
        if isinstance(thumb.get("overlay_text_options"), list):
            titles_list = seo_pack.get("title_options") if isinstance(seo_pack.get("title_options"), list) else []
            titles_vi_list = seo_pack.get("title_options_vi") if isinstance(seo_pack.get("title_options_vi"), list) else []
            for idx, opt in enumerate(thumb["overlay_text_options"]):
                if not isinstance(opt, dict):
                    continue
                for k in ("badge", "line_1", "line_2", "meaning_vi", "paired_title", "paired_title_vi", "synergy_vi"):
                    val = str(opt.get(k) or "")
                    if val:
                        c_val, hits = sanitize_youtube_policy_text(val)
                        replaced_log.extend(hits)
                        if k == "paired_title":
                            c_val = _enforce_title_primary_keyword(c_val, primary_kw, placement_rule)
                        if c_val != val:
                            opt[k] = c_val
                            changed = True
                if not opt.get("paired_title") and titles_list:
                    opt["paired_title"] = titles_list[idx % len(titles_list)]
                    changed = True
                if not opt.get("paired_title_vi") and titles_vi_list:
                    opt["paired_title_vi"] = titles_vi_list[idx % len(titles_vi_list)]
                    changed = True
                if not opt.get("keyword_anchor_vi") and primary_kw:
                    meaning_vi = str(seo_dna.get("primary_title_keyword_meaning_vi") or "").strip()
                    opt["keyword_anchor_vi"] = f"{primary_kw} ({meaning_vi})" if meaning_vi else primary_kw
                    changed = True
                if not opt.get("synergy_vi"):
                    opt["synergy_vi"] = (
                        "Tam giác bổ trợ 3 chiều: [Bối cảnh ảnh hiện trường/nhân vật] + [Text Hook trên Thumb kích thích nghịch lý] "
                        "+ [Tiêu đề chứa từ khóa chính của hồ sơ kênh] bổ trợ chặt chẽ với 0% lặp từ."
                    )
                    changed = True

    guardrail = {
        "expert_persona": "10-Year YouTube SEO Strategist & 10-Year Broadcast Thumbnail Art Director",
        "status": "GREEN_SAFE",
        "zero_policy_violations": True,
        "primary_title_keyword_locked": primary_kw,
        "keyword_placement_rule": placement_rule,
        "sanitized_terms": sorted(set(replaced_log)),
    }
    if seo_pack.get("youtube_policy_guardrail") != guardrail:
        seo_pack["youtube_policy_guardrail"] = guardrail
        changed = True

    return seo_pack, changed


def _extract_overlay_options(seo_pack: dict[str, Any], job: dict[str, Any]) -> list[dict[str, Any]]:
    thumb = seo_pack.get("thumbnail") if isinstance(seo_pack.get("thumbnail"), dict) else {}
    framework = seo_pack.get("channel_framework") if isinstance(seo_pack.get("channel_framework"), dict) else {}
    seo_dna = job.get("seo_keyword_dna") if isinstance(job.get("seo_keyword_dna"), dict) else {}
    default_badge = str(
        framework.get("series_key")
        or seo_dna.get("primary_title_keyword")
        or "중국 실화 사건"
    ).strip()
    lang = str(job.get("language") or "ko").lower()
    if lang == "vi" and default_badge == "중국 실화 사건":
        default_badge = "HỒ SƠ TRỌNG ÁN"
    elif lang == "en" and default_badge == "중국 실화 사건":
        default_badge = "TRUE CRIME FILE"

    hooks_meta = [
        {
            "hook_type": "curiosity_paradox",
            "hook_badge": "🎯 Variant A: Tò mò / Nghịch lý",
            "psychological_hook": "Variant A: Tò mò / Nghịch lý (Curiosity & Paradox Hook)",
            "meaning_vi": "Variant A · Tò mò / Nghịch lý (Số liệu sốc & Nghịch lý)",
        },
        {
            "hook_type": "character_evidence",
            "hook_badge": "🔍 Variant B: Nhân vật / Bằng chứng độc quyền",
            "psychological_hook": "Variant B: Nhân vật / Bằng chứng độc quyền (Evidence & Emotion Hook)",
            "meaning_vi": "Variant B · Nhân vật & Vật chứng (Cận cảnh & Cảm xúc)",
        },
        {
            "hook_type": "confrontation_contrast",
            "hook_badge": "⚡ Variant C: Đối đầu / Hồ sơ mật",
            "psychological_hook": "Variant C: Đối đầu / Hồ sơ mật (Dual Contrast & Dossier Hook)",
            "meaning_vi": "Variant C · Đối đầu / Hai mặt (Trước - Sau / Hồ sơ mật)",
        },
        {
            "hook_type": "evidence_spotlight",
            "hook_badge": "🔬 Variant D: Tiêu điểm Pháp y",
            "psychological_hook": "Variant D: Tiêu điểm Pháp y & Dấu vết (Forensic Spotlight Hook)",
            "meaning_vi": "Variant D · Tiêu điểm Pháp y (Khoanh vùng & Vật chứng)",
        },
    ]

    raw_options = thumb.get("overlay_text_options") if isinstance(thumb.get("overlay_text_options"), list) else []
    if not raw_options and isinstance(seo_pack.get("thumbnail_variants"), list):
        raw_options = seo_pack.get("thumbnail_variants") or []
    titles_list = seo_pack.get("title_options") if isinstance(seo_pack.get("title_options"), list) else []
    titles_vi_list = seo_pack.get("title_options_vi") if isinstance(seo_pack.get("title_options_vi"), list) else []
    rec_title = str(seo_pack.get("recommended_title") or job.get("title") or job.get("topic") or "").strip()
    rec_title_vi = str(seo_pack.get("recommended_title_vi") or "").strip()

    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_options):
        if not isinstance(item, dict):
            continue
        b, _ = sanitize_youtube_policy_text(str(item.get("badge") or default_badge).strip())
        l1, _ = sanitize_youtube_policy_text(str(item.get("line_1") or "").strip())
        l2, _ = sanitize_youtube_policy_text(str(item.get("line_2") or "").strip())
        mv = str(item.get("meaning_vi") or "").strip()
        paired_t, _ = sanitize_youtube_policy_text(
            str(item.get("paired_title") or (titles_list[idx] if idx < len(titles_list) else rec_title)).strip()
        )
        paired_t_vi, _ = sanitize_youtube_policy_text(
            str(item.get("paired_title_vi") or (titles_vi_list[idx] if idx < len(titles_vi_list) else rec_title_vi)).strip()
        )
        meta = hooks_meta[idx % len(hooks_meta)]
        if l1 or l2:
            entry = {
                "badge": b or default_badge,
                "badge_vi": str(item.get("badge_vi") or "").strip(),
                "line_1": l1,
                "line_1_vi": str(item.get("line_1_vi") or "").strip(),
                "line_2": l2,
                "line_2_vi": str(item.get("line_2_vi") or "").strip(),
                "meaning_vi": mv or meta["meaning_vi"],
                "paired_title": paired_t,
                "paired_title_vi": paired_t_vi,
                "keyword_anchor_vi": str(item.get("keyword_anchor_vi") or default_badge).strip(),
                "synergy_vi": str(
                    item.get("synergy_vi")
                    or "Bối cảnh hiện trường + Text Hook nghịch lý + Tiêu đề SEO bổ trợ hoàn hảo (0% lặp từ)."
                ).strip(),
                "hook_type": meta["hook_type"],
                "hook_badge": meta["hook_badge"],
                "psychological_hook": meta["psychological_hook"],
            }
            normalized.append(entry)

    if not normalized:
        overlay_text, _ = sanitize_youtube_policy_text(str(thumb.get("overlay_text") or "").strip())
        lines = [ln.strip() for ln in overlay_text.splitlines() if ln.strip()]
        if len(lines) >= 2:
            l1, l2 = lines[0], lines[1]
        elif len(lines) == 1:
            words = lines[0].split()
            mid = max(1, len(words) // 2)
            l1 = " ".join(words[:mid])
            l2 = " ".join(words[mid:]) or "소름 돋는 진짜 정체!"
        else:
            # Derive contextual hook dynamically from job title/topic instead of hardcoded unrelated case text
            clean_topic, _ = sanitize_youtube_policy_text(rec_title)
            clean_topic = re.sub(r"^\[[^\]]+\]\s*", "", clean_topic).strip()
            parts = [p.strip() for p in clean_topic.split("|") if p.strip()]
            main_clause = parts[0] if parts else clean_topic
            if lang == "vi":
                l1 = main_clause[:22].upper() if main_clause else "HỒ SƠ BÍ MẬT"
                l2 = "SỰ THẬT CHẤN ĐỘNG!"
            elif lang == "en":
                l1 = main_clause[:22].upper() if main_clause else "CLASSIFIED FILE"
                l2 = "THE SHOCKING TRUTH!"
            else:
                words = main_clause.split()
                if len(words) >= 4:
                    l1 = " ".join(words[:3])[:16]
                    l2 = " ".join(words[3:6])[:16] + "!"
                else:
                    l1 = main_clause[:16] or "베일에 싸인 사건"
                    l2 = "소름 돋는 진짜 정체!"

        normalized = [
            {
                "badge": default_badge,
                "line_1": l1,
                "line_2": l2,
                "meaning_vi": "Variant A · Tò mò / Nghịch lý (Curiosity & Paradox Hook)",
                "paired_title": rec_title,
                "paired_title_vi": rec_title_vi,
                "keyword_anchor_vi": default_badge,
                "synergy_vi": "Bối cảnh câu chuyện + Text Hook nghịch lý + Tiêu đề SEO bổ trợ hoàn hảo.",
                "hook_type": "curiosity_paradox",
                "hook_badge": "🎯 Variant A: Tò mò / Nghịch lý",
                "psychological_hook": "Variant A: Tò mò / Nghịch lý (Curiosity & Paradox Hook)",
            },
            {
                "badge": default_badge,
                "line_1": "모두를 속인 완벽한 위장" if lang == "ko" else "VỎ BỌC HOÀN HẢO",
                "line_2": "소름 돋는 진짜 정체!" if lang == "ko" else "THÂN PHẬN THẬT LỘ DIỆN!",
                "meaning_vi": "Variant B · Nhân vật & Vật chứng (Evidence & Emotion Hook)",
                "paired_title": titles_list[1] if len(titles_list) > 1 else rec_title,
                "paired_title_vi": titles_vi_list[1] if len(titles_vi_list) > 1 else rec_title_vi,
                "keyword_anchor_vi": default_badge,
                "synergy_vi": "Cận cảnh nhân vật/bằng chứng + Text lật tẩy vỏ bọc + Tiêu đề SEO bổ trợ.",
                "hook_type": "character_evidence",
                "hook_badge": "🔍 Variant B: Nhân vật / Bằng chứng độc quyền",
                "psychological_hook": "Variant B: Nhân vật / Bằng chứng độc quyền (Evidence & Emotion Hook)",
            },
            {
                "badge": default_badge,
                "line_1": "형사들도 경악한 단서" if lang == "ko" else "MANH MỐI ĐỊNH MỆNH",
                "line_2": "가짜 신분 뒤에 숨은 진실!" if lang == "ko" else "BÍ MẬT ĐẰNG SAU HỒ SƠ!",
                "meaning_vi": "Variant C · Đối đầu / Hồ sơ mật (Dual Contrast & Dossier Hook)",
                "paired_title": titles_list[2] if len(titles_list) > 2 else rec_title,
                "paired_title_vi": titles_vi_list[2] if len(titles_vi_list) > 2 else rec_title_vi,
                "keyword_anchor_vi": default_badge,
                "synergy_vi": "Đối lập 2 mặt trước/sau + Text Hook căng thẳng + Tiêu đề SEO chuẩn DNA kênh.",
                "hook_type": "confrontation_contrast",
                "hook_badge": "⚡ Variant C: Đối đầu / Hồ sơ mật",
                "psychological_hook": "Variant C: Đối đầu / Hồ sơ mật (Dual Contrast & Dossier Hook)",
            },
            {
                "badge": default_badge,
                "line_1": "극비 수사 기록 공개" if lang == "ko" else "GIẢI MẬT HỒ SƠ ĐIỀU TRA",
                "line_2": l2 or ("결정적 단서 포착!" if lang == "ko" else "TIÊU ĐIỂM VẬT CHỨNG!"),
                "meaning_vi": "Variant D · Tiêu điểm Pháp y (Forensic Spotlight)",
                "paired_title": titles_list[3] if len(titles_list) > 3 else rec_title,
                "paired_title_vi": titles_vi_list[3] if len(titles_vi_list) > 3 else rec_title_vi,
                "keyword_anchor_vi": default_badge,
                "synergy_vi": "Khoanh vùng tiêu điểm vật chứng + Text Hook pháp y + Tiêu đề SEO kênh.",
                "hook_type": "evidence_spotlight",
                "hook_badge": "🔬 Variant D: Tiêu điểm Pháp y",
                "psychological_hook": "Variant D: Tiêu điểm Pháp y & Dấu vết (Forensic Spotlight Hook)",
            },
        ]

    while len(normalized) < 4:
        meta = hooks_meta[len(normalized) % len(hooks_meta)]
        base = dict(normalized[len(normalized) % max(1, len(normalized))])
        base.update(meta)
        normalized.append(base)

    return normalized[:4]


def sync_thumbnail_design_with_seo_pack(
    design: dict[str, Any],
    seo_pack: dict[str, Any] | None,
    job: dict[str, Any],
    candidates: list[dict[str, Any]] | None = None,
) -> bool:
    """Synchronize an existing thumbnail_design.json with seo_package.json and contextual scene backgrounds whenever stale placeholders or style_reference backgrounds are detected."""
    if not isinstance(design, dict):
        return False
    variants = design.get("variants")
    if not isinstance(variants, list) or not variants:
        return False

    seo_pack = seo_pack if isinstance(seo_pack, dict) else {}
    candidates = candidates if isinstance(candidates, list) else []
    contextual_cands = [
        c for c in candidates
        if c.get("category") not in ("thumbnail_inset", "style_reference")
    ] or [c for c in candidates if c.get("category") != "thumbnail_inset"] or candidates

    has_seo_overlay_options = bool(
        isinstance(seo_pack.get("thumbnail"), dict)
        and isinstance(seo_pack["thumbnail"].get("overlay_text_options"), list)
        and len(seo_pack["thumbnail"]["overlay_text_options"]) > 0
    )
    options = _extract_overlay_options(seo_pack, job)
    seo_generated_at = str(seo_pack.get("generated_at") or "").strip()
    needs_seo_sync = bool(has_seo_overlay_options and seo_generated_at and design.get("seo_pack_synced_at") != seo_generated_at)

    changed = False

    # Replace root style_reference background if real contextual candidates exist
    root_bg_path = str(design.get("background_path") or "")
    if contextual_cands and (not root_bg_path or "style_reference" in root_bg_path) and contextual_cands[0].get("category") != "style_reference":
        design["background_url"] = str(contextual_cands[0].get("url") or "")
        design["background_path"] = str(contextual_cands[0].get("rel_path") or "")
        changed = True

    root_inset_path = str(design.get("inset_image_path") or "")
    if contextual_cands and (not root_inset_path or "style_reference" in root_inset_path) and contextual_cands[0].get("category") != "style_reference":
        inset_c = contextual_cands[min(1, len(contextual_cands) - 1)]
        design["inset_image_url"] = str(inset_c.get("url") or "")
        design["inset_image_path"] = str(inset_c.get("rel_path") or "")
        changed = True

    for idx, v in enumerate(variants):
        if not isinstance(v, dict):
            continue
        if not v.get("id"):
            v["id"] = str(v.get("variant_id") or f"v{idx + 1}")
            changed = True
        opt = options[idx % len(options)]
        cur_l1 = str(v.get("line_1") or v.get("text_line1") or "").strip()
        cur_l2 = str(v.get("line_2") or v.get("text_line2") or "").strip()
        cur_badge = str(v.get("badge_text") or v.get("sub_text") or "").strip()
        if not v.get("line_1") and cur_l1:
            v["line_1"] = cur_l1
            changed = True
        if not v.get("line_2") and cur_l2:
            v["line_2"] = cur_l2
            changed = True
        if not v.get("badge_text") and cur_badge:
            v["badge_text"] = cur_badge
            changed = True
        if not isinstance(v.get("layers"), list) or not v.get("layers"):
            arch_key = str(v.get("archetype") or v.get("layout_mode") or "split_duality")
            if arch_key not in ARCHETYPES:
                arch_key = "split_duality"
            v["archetype"] = arch_key
            v["layers"] = build_variant_layers(
                arch_key,
                badge_text=v.get("badge_text") or opt["badge"],
                line_1=v.get("line_1") or opt["line_1"],
                line_2=v.get("line_2") or opt["line_2"],
                line_1_color="#ffffff",
                line_2_color="#ffe600" if idx % 2 == 0 else "#ff2424",
                badge_bg="#dc2626",
                badge_color="#ffffff",
                inset_image_url=str(v.get("inset_image_url") or design.get("inset_image_url") or ""),
            )
            changed = True

        is_stale_placeholder = (
            cur_l1 in STALE_FALLBACK_TEXT_MARKERS
            or cur_l2 in STALE_FALLBACK_TEXT_MARKERS
            or not (cur_l1 or cur_l2)
        )
        _, policy_hits = sanitize_youtube_policy_text(f"{cur_badge} {cur_l1} {cur_l2} {v.get('paired_title') or ''}")

        if is_stale_placeholder or needs_seo_sync or policy_hits:
            new_badge, _ = sanitize_youtube_policy_text(opt["badge"] if (is_stale_placeholder or needs_seo_sync) else (cur_badge or opt["badge"]))
            new_l1, _ = sanitize_youtube_policy_text(opt["line_1"] if (is_stale_placeholder or needs_seo_sync) else cur_l1)
            new_l2, _ = sanitize_youtube_policy_text(opt["line_2"] if (is_stale_placeholder or needs_seo_sync) else cur_l2)
            v["badge_text"] = new_badge
            v["line_1"] = new_l1
            v["line_2"] = new_l2
            v["meaning_vi"] = opt.get("meaning_vi") or v.get("meaning_vi") or ""
            v["paired_title"] = opt.get("paired_title") or v.get("paired_title") or ""
            v["paired_title_vi"] = opt.get("paired_title_vi") or v.get("paired_title_vi") or ""
            v["keyword_anchor_vi"] = opt.get("keyword_anchor_vi") or v.get("keyword_anchor_vi") or ""
            v["synergy_vi"] = opt.get("synergy_vi") or v.get("synergy_vi") or ""
            for layer in v.get("layers") or []:
                if not isinstance(layer, dict):
                    continue
                lid = str(layer.get("id") or "")
                if lid == "badge":
                    layer["text"] = new_badge
                    layer["width"] = max(340, min(680, int(len(new_badge) * 34 + 68)))
                elif lid == "line_1":
                    layer["text"] = new_l1
                elif lid == "line_2":
                    layer["text"] = new_l2
            changed = True
        else:
            # Ensure paired_title / synergy_vi metadata are populated from seo_pack if missing
            for meta_key in ("paired_title", "paired_title_vi", "keyword_anchor_vi", "synergy_vi", "meaning_vi"):
                if not v.get(meta_key) and opt.get(meta_key):
                    v[meta_key] = opt[meta_key]
                    changed = True

        # Replace variant style_reference background with contextual background if available
        v_bg_path = str(v.get("background_path") or "")
        if contextual_cands and (not v_bg_path or "style_reference" in v_bg_path) and contextual_cands[0].get("category") != "style_reference":
            vid_num = idx + 1
            matched_cand = next(
                (c for c in contextual_cands if f"thumb_bg_v{vid_num}" in str(c.get("rel_path") or "")),
                contextual_cands[idx % len(contextual_cands)],
            )
            v["background_url"] = str(matched_cand.get("url") or "")
            v["background_path"] = str(matched_cand.get("rel_path") or "")
            changed = True

        v_inset_url = str(v.get("inset_image_url") or "")
        if contextual_cands and ("style_reference" in v_inset_url or not v_inset_url) and contextual_cands[0].get("category") != "style_reference":
            inset_c = contextual_cands[(idx + 1) % len(contextual_cands)]
            v["inset_image_url"] = str(inset_c.get("url") or "")
            for layer in v.get("layers") or []:
                if isinstance(layer, dict) and layer.get("type") == "inset_image":
                    layer["src"] = str(inset_c.get("url") or "")
            changed = True

    if seo_generated_at and design.get("seo_pack_synced_at") != seo_generated_at:
        design["seo_pack_synced_at"] = seo_generated_at
        changed = True

    return changed


def build_default_thumbnail_design(
    job_id: str,
    workspace: Path,
    job: dict[str, Any],
    seo_pack: dict[str, Any] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    preferred_archetype: str | None = None,
    thumbnail_dna: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synthesize a complete Fabric.js-compatible thumbnail_design.json with 3 distinct A/B/C variants adhering to channel thumbnail DNA."""
    seo_pack = seo_pack if isinstance(seo_pack, dict) else {}
    if candidates is None:
        candidates = discover_job_candidate_images(job_id, workspace, job)

    contextual_cands = [
        c for c in candidates
        if c.get("category") not in ("thumbnail_inset", "style_reference")
    ] or [c for c in candidates if c.get("category") != "thumbnail_inset"] or candidates
    inset_cands = [c for c in candidates if c.get("category") == "thumbnail_inset"]

    primary_bg = contextual_cands[0] if contextual_cands else None
    secondary_bg = inset_cands[0] if inset_cands else (contextual_cands[1] if len(contextual_cands) > 1 else primary_bg)
    base_clean_prompt = build_clean_background_prompt(seo_pack, job)

    # Read Channel Inspection & Channel Profile Thumbnail DNA if available
    ref_ctx_file = workspace / "seo_reference_context.json"
    ref_ctx: dict[str, Any] = {}
    if ref_ctx_file.is_file():
        try:
            ref_ctx = json.loads(ref_ctx_file.read_text(encoding="utf-8"))
        except Exception:
            ref_ctx = {}

    channel_dna: dict[str, Any] = (
        thumbnail_dna
        or job.get("thumbnail_dna")
        or (ref_ctx.get("thumbnail_dna") if isinstance(ref_ctx.get("thumbnail_dna"), dict) else {})
        or {}
    )
    if not channel_dna and job.get("channel_profile_id"):
        try:
            from services.channel_profile_service import ChannelProfileService
            cps = ChannelProfileService()
            prof = cps.get_profile(job["channel_profile_id"])
            if prof and prof.get("thumbnail_dna"):
                channel_dna = prof["thumbnail_dna"]
        except Exception:
            pass

    palette = channel_dna.get("color_palette") if isinstance(channel_dna.get("color_palette"), dict) else {}
    primary_accent = str(palette.get("primary") or palette.get("accent_highlight") or "#FFE84A")
    danger_accent = str(palette.get("accent") or palette.get("danger_badge") or "#ef4444")
    text_primary = str(
        palette.get("text_primary")
        or (palette.get("line_1_color") if palette.get("line_1_color") else None)
        or ("#ffe600" if str(channel_dna.get("layout_template") or "") == "bottom_cinematic" else "#ffffff")
    )

    dna_layout = str(channel_dna.get("layout_template") or "").strip()
    dna_preset = str(channel_dna.get("style_preset") or "").strip()
    is_bottom_cinematic_dna = (
        dna_layout == "bottom_cinematic"
        or dna_preset == "infrastructure_crisis_broadcast"
    )
    first_arch = (
        preferred_archetype
        if preferred_archetype in ARCHETYPES
        else (dna_layout if dna_layout in ARCHETYPES else "broadcast_left_heavy")
    )
    remaining_archs = [a for a in ("broadcast_left_heavy", "split_duality", "bottom_cinematic", "evidence_spotlight") if a != first_arch]
    archetype_cycle = [first_arch, *remaining_archs]

    options = _extract_overlay_options(seo_pack, job)
    if is_bottom_cinematic_dna:
        accent_colors = ["#ff1f1f", primary_accent, "#ff2424", "#ffe600"]
        badge_colors = ["transparent", "#dc2626", "transparent", "#b91c1c"]
    else:
        accent_colors = [primary_accent, danger_accent, primary_accent, "#38bdf8"]
        badge_colors = [
            "transparent" if first_arch == "bottom_cinematic" else danger_accent,
            "#dc2626",
            "#b91c1c",
            "#ea580c",
        ]
    variant_fonts = [
        "'Gmarket Sans Bold', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
        "'Gmarket Sans Bold', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
        "'Gmarket Sans Bold', 'Pretendard Black', 'Malgun Gothic', sans-serif",
        "'Gmarket Sans Bold', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
    ] if is_bottom_cinematic_dna else [
        "'Pretendard ExtraBold', 'Gmarket Sans Bold', 'Malgun Gothic', sans-serif",
        "'Gmarket Sans Bold', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
        "'Pretendard Black', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
        "'Pretendard ExtraBold', 'Pretendard Black', 'Malgun Gothic', sans-serif",
    ]
    short_labels = ["BẢN A", "BẢN B", "BẢN C", "BẢN D"]
    camera_angles = [
        "High-angle photorealistic aerial disaster/engineering view of the megaproject in muddy brown churning water under dark storm clouds, keeping the bottom 35% dark for giant broadcast typography.",
        "Dramatic photorealistic on-site catastrophe shot in the upper two-thirds with towering fire/water impact, dark shadowy negative space across the bottom 35%.",
        "Photorealistic split/confrontation engineering view showing extreme physical forces hitting the structure, dark bottom third for two-line yellow/red impact text.",
        "Macro photorealistic forensic engineering close-up on the corroded/damaged structural foundation on the right/upper frame, deep dark shadows below.",
    ] if is_bottom_cinematic_dna else [
        "Close-up dramatic portrait of the main subject on the right third of the frame, dark negative space on the left 60%.",
        "Wide cinematic crime-scene / investigative atmosphere in the upper two-thirds, dark shadowy negative space across the bottom 35%.",
        "High-tension forensic confrontation shot on the left/center with cold rim lighting and dark atmospheric background.",
        "Macro spotlight on key forensic clue / dossier evidence on the right side, deep dark shadows on the left side.",
    ]

    variants: list[dict[str, Any]] = []
    for idx, opt in enumerate(options[:4]):
        arch_key = archetype_cycle[idx % len(archetype_cycle)]
        arch_info = ARCHETYPES.get(arch_key, ARCHETYPES["broadcast_left_heavy"])
        vid = f"v{idx + 1}"
        line2_color = accent_colors[idx % len(accent_colors)]
        v_badge_bg = badge_colors[idx % len(badge_colors)]
        v_badge_color = "#39ff14" if arch_key == "bottom_cinematic" else "#ffffff"
        v_font = variant_fonts[idx % len(variant_fonts)]
        vid_num = idx + 1
        cand_bg = (
            next((c for c in contextual_cands if f"thumb_bg_v{vid_num}" in str(c.get("rel_path") or "").lower()), None)
            or (contextual_cands[idx % len(contextual_cands)] if contextual_cands else None)
        )
        cand_inset = (
            inset_cands[idx % len(inset_cands)]
            if inset_cands
            else (contextual_cands[(idx + 1) % len(contextual_cands)] if len(contextual_cands) > 1 else cand_bg)
        )
        v_bg_url = str(cand_bg.get("url") or "") if cand_bg else ""
        v_bg_path = str(cand_bg.get("rel_path") or "") if cand_bg else ""
        v_inset_url = str(cand_inset.get("url") or "") if cand_inset else ""
        v_line1_color = "#ffe600" if is_bottom_cinematic_dna else (
            text_primary if (arch_key == "bottom_cinematic" and line2_color.lower() not in ("#ffe84a", "#ffe600", "#fbbf24")) else "#ffffff"
        )
        layers = build_variant_layers(
            arch_key,
            badge_text=opt["badge"],
            line_1=opt["line_1"],
            line_2=opt["line_2"],
            line_1_color=v_line1_color,
            line_2_color=line2_color,
            badge_bg=v_badge_bg,
            badge_color=v_badge_color,
            inset_image_url=v_inset_url,
            font_family=v_font,
        )
        if is_bottom_cinematic_dna:
            for lyr in layers:
                if not isinstance(lyr, dict):
                    continue
                if lyr.get("id") == "forensic_circle" and idx in (0, 3):
                    lyr["visible"] = True
                    lyr["dashed"] = True
                    lyr["stroke"] = "#ffffff" if idx == 0 else "#ff1f1f"
                    lyr["strokeWidth"] = 8 if idx == 0 else 10
                elif lyr.get("id") == "inset_photo" and idx == 2:
                    lyr["visible"] = True
                    lyr["borderColor"] = "#ffffff"
                    lyr["borderWidth"] = 6
        variant_dict: dict[str, Any] = {
            "id": vid,
            "short_label": short_labels[idx % len(short_labels)],
            "name": f"{short_labels[idx % len(short_labels)]} · {opt.get('hook_badge', arch_info['name'])}",
            "archetype": arch_key,
            "hook_type": opt.get("hook_type", "curiosity_paradox"),
            "hook_badge": opt.get("hook_badge", f"Variant {short_labels[idx % len(short_labels)]}"),
            "psychological_hook": opt.get("psychological_hook", ""),
            "background_url": v_bg_url,
            "background_path": v_bg_path,
            "inset_image_url": v_inset_url,
            "clean_bg_prompt": f"{base_clean_prompt}\nCamera & Framing ({short_labels[idx % len(short_labels)]}): {camera_angles[idx % len(camera_angles)]}",
            "badge_text": opt["badge"],
            "badge_vi": opt.get("badge_vi") or "",
            "line_1": opt["line_1"],
            "line_1_vi": opt.get("line_1_vi") or "",
            "line_2": opt["line_2"],
            "line_2_vi": opt.get("line_2_vi") or "",
            "meaning_vi": opt.get("meaning_vi") or "",
            "paired_title": opt.get("paired_title") or "",
            "paired_title_vi": opt.get("paired_title_vi") or "",
            "keyword_anchor_vi": opt.get("keyword_anchor_vi") or "",
            "synergy_vi": opt.get("synergy_vi") or "",
            "layers": layers,
        }
        variants.append(variant_dict)

    design: dict[str, Any] = {
        "version": 2,
        "job_id": job_id,
        "updated_at": _now_iso(),
        "seo_pack_synced_at": str(seo_pack.get("generated_at") or ""),
        "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
        "active_variant_id": "v1",
        "background_url": str(primary_bg.get("url") or "") if primary_bg else "",
        "background_path": str(primary_bg.get("rel_path") or "") if primary_bg else "",
        "inset_image_url": str(secondary_bg.get("url") or "") if secondary_bg else "",
        "inset_image_path": str(secondary_bg.get("rel_path") or "") if secondary_bg else "",
        "clean_bg_prompt": base_clean_prompt,
        "safe_zone_visible": False,
        "mobile_preview_visible": True,
        "channel_thumbnail_dna": channel_dna,
        "channel_inspection": ref_ctx.get("channel_inspection_report") if isinstance(ref_ctx.get("channel_inspection_report"), dict) else {},
        "variants": variants,
    }
    design["ctr_critique"] = evaluate_thumbnail_ctr(design, channel_dna=channel_dna)
    return design


DEFAULT_KR_BROADCAST_STACKS = [
    "'Pretendard ExtraBold', 'Gmarket Sans Bold', 'Malgun Gothic', sans-serif",
    "'Gmarket Sans Bold', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
    "'Pretendard Black', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
    "'Pretendard ExtraBold', 'Pretendard Black', 'Malgun Gothic', sans-serif",
]


def _parse_inline_highlight_segments(text: str) -> tuple[str, list[tuple[str, bool]]]:
    """Parse inline highlight markers *word* or [word] into (plain_text, [(segment, is_highlighted), ...])."""
    raw = str(text or "")
    if ("*" not in raw and "[" not in raw) or len(raw) < 3:
        return raw, [(raw, False)]
    pattern = re.compile(r"\*([^*\n]+)\*|\[([^\[\]\n]+)\]")
    segments: list[tuple[str, bool]] = []
    last_idx = 0
    for m in pattern.finditer(raw):
        if m.start() > last_idx:
            segments.append((raw[last_idx:m.start()], False))
        hl_txt = m.group(1) if m.group(1) is not None else m.group(2)
        if hl_txt:
            segments.append((hl_txt, True))
        last_idx = m.end()
    if last_idx < len(raw):
        segments.append((raw[last_idx:], False))
    if not segments:
        return raw, [(raw, False)]
    plain = "".join(seg for seg, _ in segments)
    return plain, segments


def sanitize_and_repair_thumbnail_design(
    design: dict[str, Any],
    job_id: str | None = None,
    workspace: Path | None = None,
) -> bool:
    """Repair missing layer IDs, invisible badge text (fill == bgColor), relative inset_image URLs, and legacy fonts."""
    if not isinstance(design, dict):
        return False
    changed = False
    resolved_job_id = str(job_id or design.get("job_id") or "").strip()
    variants = design.get("variants")
    if not isinstance(variants, list):
        return False

    for idx, v in enumerate(variants):
        if not isinstance(v, dict):
            continue
        if not v.get("id"):
            v["id"] = str(v.get("variant_id") or f"v{idx + 1}")
            changed = True
        default_stack = DEFAULT_KR_BROADCAST_STACKS[idx % len(DEFAULT_KR_BROADCAST_STACKS)]
        layers = v.get("layers")
        if not isinstance(layers, list):
            continue

        used_ids: set[str] = set()
        textbox_order = 0
        for l_idx, layer in enumerate(layers):
            if not isinstance(layer, dict):
                continue
            ltype = str(layer.get("type") or "").strip()
            lid = str(layer.get("id") or "").strip()

            # 1. Assign canonical IDs when missing so UI Inspector & CTR evaluator work 100%
            if not lid:
                if ltype == "vignette":
                    lid = "vignette"
                elif ltype == "badge":
                    lid = "badge"
                elif ltype == "stamp":
                    lid = "stamp"
                elif ltype == "circle":
                    lid = "forensic_circle"
                elif ltype == "arrow":
                    lid = "forensic_arrow"
                elif ltype == "inset_image":
                    lid = "inset_photo"
                elif ltype == "textbox":
                    textbox_order += 1
                    if textbox_order == 1 and "line_1" not in used_ids:
                        lid = "line_1"
                    elif textbox_order == 2 and "line_2" not in used_ids:
                        lid = "line_2"
                    else:
                        lid = f"textbox_{l_idx + 1}"
                else:
                    lid = f"layer_{l_idx + 1}"
                while lid in used_ids:
                    lid = f"{lid}_{l_idx + 1}"
                layer["id"] = lid
                changed = True
            else:
                if lid in ("line_1", "line_2"):
                    textbox_order += 1
            used_ids.add(lid)

            # 2. Fix badge invisible text bug (legacy textColor + fill without bgColor, or fill == bgColor)
            if ltype == "badge":
                raw_bg = str(layer.get("bgColor") or layer.get("backgroundColor") or layer.get("badge_bg") or "").strip()
                raw_fill = str(layer.get("fill") or "").strip()
                raw_tc = str(layer.get("textColor") or "").strip()
                if not raw_bg:
                    if raw_tc and raw_fill and raw_fill.lower() != raw_tc.lower():
                        layer["bgColor"] = raw_fill
                        layer["fill"] = raw_tc
                    else:
                        layer["bgColor"] = "#dc2626"
                        if not raw_fill or raw_fill.lower() == "#dc2626":
                            layer["fill"] = "#ffffff"
                    changed = True
                elif raw_fill and raw_bg.lower() not in ("transparent", "none") and raw_fill.lower() == raw_bg.lower():
                    layer["fill"] = raw_tc if (raw_tc and raw_tc.lower() != raw_bg.lower()) else "#ffffff"
                    changed = True

            # 3. Repair inset_image relative path or missing file fallback
            if ltype == "inset_image":
                src = str(layer.get("src") or v.get("inset_image_url") or design.get("inset_image_url") or "").strip()
                if src and not src.startswith(("/api/", "http://", "https://", "data:")):
                    rel_clean = src.replace("\\", "/").lstrip("/")
                    if workspace is not None:
                        cand_p = (workspace / rel_clean).resolve()
                        if not cand_p.is_file():
                            fallback_p = workspace / "media" / "thumbnail" / "thumb_inset_v1.jpg"
                            if fallback_p.is_file():
                                rel_clean = "media/thumbnail/thumb_inset_v1.jpg"
                    if resolved_job_id:
                        src = f"/api/jobs/{resolved_job_id}/media?path={rel_clean}"
                        layer["src"] = src
                        if layer.get("id") == "inset_photo" or not v.get("inset_image_url"):
                            v["inset_image_url"] = src
                        changed = True
                elif src and "path=" in src and workspace is not None:
                    from urllib.parse import unquote
                    rel_q = unquote(src.split("path=", 1)[1].split("&", 1)[0]).replace("\\", "/").lstrip("/")
                    if not (workspace / rel_q).is_file():
                        fallback_p = workspace / "media" / "thumbnail" / "thumb_inset_v1.jpg"
                        if fallback_p.is_file() and resolved_job_id:
                            fixed_url = f"/api/jobs/{resolved_job_id}/media?path=media/thumbnail/thumb_inset_v1.jpg"
                            layer["src"] = fixed_url
                            if layer.get("id") == "inset_photo" or not v.get("inset_image_url"):
                                v["inset_image_url"] = fixed_url
                            changed = True

            # 4. Upgrade legacy fonts & ensure highlightFill default on textboxes
            if ltype in ("textbox", "badge", "stamp"):
                cur = str(layer.get("fontFamily") or "").strip()
                if not cur or "Black Han Sans" in cur or cur.startswith("'Paperlogy Black'") or cur.startswith("'SB Aggro"):
                    layer["fontFamily"] = default_stack
                    changed = True
                if ltype == "textbox" and not layer.get("highlightFill"):
                    main_f = str(layer.get("fill") or "#ffffff").lower()
                    layer["highlightFill"] = "#ff2424" if main_f in ("#ffe600", "#ffe84a", "#fbbf24", "#facc15") else "#ffe600"

        # Sync top-level variant text fields from repaired layers if needed
        by_id = {str(l.get("id") or ""): l for l in layers if isinstance(l, dict)}
        if by_id.get("line_1") and not v.get("line_1"):
            v["line_1"] = str(by_id["line_1"].get("text") or "")
        if by_id.get("line_2") and not v.get("line_2"):
            v["line_2"] = str(by_id["line_2"].get("text") or "")
        if by_id.get("badge") and not v.get("badge_text"):
            v["badge_text"] = str(by_id["badge"].get("text") or "")

    return changed


def sanitize_thumbnail_design_fonts(design: dict[str, Any]) -> bool:
    """Upgrade any legacy fonts and auto-repair missing layer IDs / badge colors / inset paths."""
    return sanitize_and_repair_thumbnail_design(design)


def _hex_to_rgba(color_str: str, alpha: int = 255) -> tuple[int, int, int, int]:
    raw = str(color_str or "#ffffff").strip().lower()
    if raw in ("transparent", "none", ""):
        return (0, 0, 0, 0)
    s = raw.lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) >= 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), alpha)
        except ValueError:
            pass
    return (255, 255, 255, alpha)


def _resolve_pil_font_path(font_family: str, text: str = "") -> Path:
    fonts_dir = Path(__file__).resolve().parent.parent / "static" / "fonts"
    has_vn = bool(re.search(r"[ăâđêôơưĂÂĐÊÔƠƯảãạấầẩẫậắằẳẵặẻẽẹếềểễệỉĩịỏõọốồổỗộớờởỡợủũụứừửữựỳỷỹỵ]", text))
    fam = str(font_family or "").lower()
    if has_vn:
        cand = fonts_dir / ("Pretendard-Black.otf" if "black" in fam else "Pretendard-ExtraBold.otf")
        if cand.is_file():
            return cand
    mapping = [
        ("pretendard extrabold", "Pretendard-ExtraBold.otf"),
        ("pretendard black", "Pretendard-Black.otf"),
        ("pretendard bold", "Pretendard-Bold.otf"),
        ("pretendard", "Pretendard-ExtraBold.otf"),
        ("gmarket", "GmarketSansBold.ttf"),
        ("paperlogy extrabold", "Paperlogy-8ExtraBold.ttf"),
        ("paperlogy black", "Paperlogy-9Black.ttf"),
        ("paperlogy", "Paperlogy-8ExtraBold.ttf"),
        ("scoredream", "SCoreDream-9Black.woff"),
        ("gonggothic", "GongGothicBold.woff"),
        ("kbo", "KBO-Dia-Gothic_bold.woff"),
        ("aggro", "SBAggroB.woff"),
    ]
    # Check each font token in priority order (left-to-right in the CSS font-family stack)
    tokens = [t.strip().strip("'\"").lower() for t in fam.split(",") if t.strip()]
    for tok in tokens:
        for key, fname in mapping:
            if key in tok and (fonts_dir / fname).is_file():
                return fonts_dir / fname
    for fallback in ("Pretendard-ExtraBold.otf", "GmarketSansBold.ttf", "Pretendard-Black.otf"):
        if (fonts_dir / fallback).is_file():
            return fonts_dir / fallback
    return Path("C:/Windows/Fonts/malgunbd.ttf")


def render_variant_to_pil(workspace: Path, design: dict[str, Any], variant: dict[str, Any]):
    """Render a thumbnail variant to a 1280x720 PIL Image with broadcast-grade Korean/VN typography."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    import math

    cw, ch = CANVAS_WIDTH, CANVAS_HEIGHT
    base = Image.new("RGBA", (cw, ch), (9, 13, 22, 255))

    def _resolve_local_image(rel_or_url: str) -> Path | None:
        raw = str(rel_or_url or "").strip()
        if not raw:
            return None
        if "path=" in raw:
            from urllib.parse import unquote
            raw = unquote(raw.split("path=", 1)[1].split("&", 1)[0])
        raw = raw.replace("\\", "/").lstrip("/")
        if "thumbnail_v" in raw:
            raw = re.sub(r"thumbnail_v([1-4])", r"thumb_bg_v\1", raw, flags=re.IGNORECASE)
        cand = (workspace / raw).resolve()
        if cand.is_file():
            return cand
        return None

    bg_file = (
        _resolve_local_image(variant.get("background_path") or "")
        or _resolve_local_image(variant.get("background_url") or "")
        or _resolve_local_image(design.get("background_path") or "")
        or _resolve_local_image(design.get("background_url") or "")
    )
    if bg_file and bg_file.is_file():
        try:
            with Image.open(bg_file) as im:
                im_rgba = im.convert("RGBA")
                iw, ih = im_rgba.size
                scale = max(cw / max(1, iw), ch / max(1, ih))
                nw, nh = max(cw, int(round(iw * scale))), max(ch, int(round(ih * scale)))
                resized = im_rgba.resize((nw, nh), Image.Resampling.LANCZOS)
                sx, sy = (nw - cw) // 2, (nh - ch) // 2
                base = resized.crop((sx, sy, sx + cw, sy + ch))
        except Exception:
            pass

    for layer in (variant.get("layers") or design.get("layers") or []):
        if not isinstance(layer, dict) or layer.get("visible") is False:
            continue
        ltype = str(layer.get("type") or "")
        opacity = max(0.0, min(1.0, float(layer.get("opacity", 1.0))))
        if opacity <= 0.01:
            continue

        if ltype == "vignette":
            style = str(layer.get("style") or "left_heavy")
            vig = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            vdraw = ImageDraw.Draw(vig)
            if style == "left_heavy":
                max_x = int(cw * 0.82)
                for x in range(max_x):
                    t = x / max(1, max_x)
                    a = int(255 * opacity * max(0.05, (1.0 - t) ** 1.35))
                    vdraw.line([(x, 0), (x, ch)], fill=(4, 7, 14, min(245, a)))
            elif style == "right_heavy":
                start_x = int(cw * 0.18)
                for x in range(start_x, cw):
                    t = (x - start_x) / max(1, cw - start_x)
                    a = int(255 * opacity * max(0.05, t ** 1.35))
                    vdraw.line([(x, 0), (x, ch)], fill=(4, 7, 14, min(245, a)))
            elif style == "bottom_heavy":
                start_y = int(ch * 0.54)
                for y in range(start_y, ch):
                    t = (y - start_y) / max(1, ch - start_y)
                    smooth_t = t * t * (3.0 - 2.0 * t)
                    a = int(255 * opacity * (smooth_t ** 1.35))
                    vdraw.line([(0, y), (cw, y)], fill=(4, 7, 14, min(240, a)))
            else:
                for y in range(ch):
                    t = y / max(1, ch)
                    a = int(255 * opacity * (0.28 + 0.68 * (t ** 1.4)))
                    vdraw.line([(0, y), (cw, y)], fill=(4, 7, 14, min(242, a)))
            if style != "bottom_heavy":
                vig_bot = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
                vbdraw = ImageDraw.Draw(vig_bot)
                for y in range(ch - 150, ch):
                    t = (y - (ch - 150)) / 150.0
                    smooth_t = t * t * (3.0 - 2.0 * t)
                    a = int(125 * (smooth_t ** 1.4))
                    vbdraw.line([(0, y), (cw, y)], fill=(2, 4, 9, a))
                vig = Image.alpha_composite(vig, vig_bot)
            base = Image.alpha_composite(base, vig)

        elif ltype == "inset_image":
            inset_file = (
                _resolve_local_image(layer.get("src") or "")
                or _resolve_local_image(variant.get("inset_image_url") or "")
                or _resolve_local_image(design.get("inset_image_url") or "")
                or _resolve_local_image(design.get("inset_image_path") or "")
                or _resolve_local_image("media/thumbnail/thumb_inset_v1.jpg")
            )
            if inset_file and inset_file.is_file():
                try:
                    ix, iy = int(float(layer.get("left") or 840)), int(float(layer.get("top") or 44))
                    iw, ih = max(40, int(float(layer.get("width") or 360))), max(40, int(float(layer.get("height") or 300)))
                    angle = float(layer.get("angle") or 0.0)
                    frame_style = str(layer.get("frameStyle") or "").strip().lower()
                    border_hex = str(layer.get("borderColor") or "#ef4444").strip().lower()
                    is_vintage = frame_style in ("vintage_paper", "polaroid") or (
                        not frame_style and border_hex in ("#f4ebd9", "#f3ead8", "#e8dcc8", "#efe5d1", "#fdf8ee")
                    )

                    pad = 48
                    card_w, card_h = iw + pad * 2, ih + pad * 2
                    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
                    cdraw = ImageDraw.Draw(card)
                    bw = max(3, int(float(layer.get("borderWidth") or 6)))
                    b_rgba = _hex_to_rgba(layer.get("borderColor") or "#fbbf24", 255)

                    def _crop_pip_rgba(w_t: int, h_t: int, rad: int = 12) -> tuple[Image.Image, Image.Image]:
                        with Image.open(inset_file) as pim:
                            pim_rgba = pim.convert("RGBA")
                            pw, ph = pim_rgba.size
                            sc = max(w_t / max(1, pw), h_t / max(1, ph))
                            rw, rh = max(w_t, int(round(pw * sc))), max(h_t, int(round(ph * sc)))
                            resized_p = pim_rgba.resize((rw, rh), Image.Resampling.LANCZOS)
                            cx0, cy0 = (rw - w_t) // 2, (rh - h_t) // 2
                            cropped = resized_p.crop((cx0, cy0, cx0 + w_t, cy0 + h_t))
                        mask_im = Image.new("L", (w_t, h_t), 0)
                        if rad > 0:
                            ImageDraw.Draw(mask_im).rounded_rectangle([0, 0, w_t - 1, h_t - 1], radius=rad, fill=255)
                        else:
                            mask_im.paste(255, [0, 0, w_t, h_t])
                        return cropped, mask_im

                    if frame_style in ("torn_newspaper", "torn_paper"):
                        # Realistic hand-ripped newspaper clipping contour (slow paper-grain drift + irregular fiber notches, never a regular sawtooth)
                        def _torn_poly(x0_p: float, y0_p: float, w_p: float, h_p: float, amp: float = 4.6, seed_off: float = 0.0, deckle_bias: float = 0.0) -> list[tuple[float, float]]:
                            def _tear_disp(pos: float, length: float, phase: float) -> float:
                                # Low-frequency tear path + localized irregular notch
                                drift = math.sin(pos * 0.031 + phase) * 0.52 + math.cos(pos * 0.074 + phase * 1.7) * 0.34
                                micro = math.sin(pos * 0.33 + phase * 2.3) * math.cos(pos * 0.79 + phase * 0.9) * 0.38
                                notch_wave = math.sin(pos * 0.089 + phase * 1.3)
                                notch = (notch_wave ** 5) * 0.65
                                fiber = deckle_bias * (0.4 + 0.6 * max(0.0, math.sin(pos * 0.053 + phase * 2.1)))
                                return (drift + micro + notch) * amp + fiber

                            pts: list[tuple[float, float]] = []
                            step = 5
                            for s_x in range(0, int(w_p) + 1, step):
                                d = _tear_disp(s_x, w_p, 1.1 + seed_off)
                                pts.append((x0_p + s_x, y0_p + d - deckle_bias))
                            for s_y in range(step, int(h_p) + 1, step):
                                d = _tear_disp(s_y, h_p, 2.7 + seed_off)
                                pts.append((x0_p + w_p + d + deckle_bias, y0_p + s_y))
                            for s_x in range(int(w_p) - step, -1, -step):
                                d = _tear_disp(s_x, w_p, 4.3 + seed_off)
                                pts.append((x0_p + max(0, s_x), y0_p + h_p + d + deckle_bias * 1.15))
                            for s_y in range(int(h_p) - step, 0, -step):
                                d = _tear_disp(s_y, h_p, 5.8 + seed_off)
                                pts.append((x0_p + d - deckle_bias, y0_p + max(0, s_y)))
                            return pts

                        seed_val = float((ix * 13 + iy * 7) % 97) * 0.1
                        shadow_poly = [(px + 6, py + 11) for (px, py) in _torn_poly(pad, pad, iw, ih, amp=4.8, seed_off=seed_val, deckle_bias=3.2)]
                        cdraw.polygon(shadow_poly, fill=(0, 0, 0, 236))
                        card = card.filter(ImageFilter.GaussianBlur(radius=9))
                        cdraw = ImageDraw.Draw(card)

                        # 1. Outer exposed white paper pulp deckle edge (where newspaper fibers tore)
                        outer_tear_poly = _torn_poly(pad, pad, iw, ih, amp=4.8, seed_off=seed_val, deckle_bias=3.0)
                        cdraw.polygon(outer_tear_poly, fill=(252, 249, 242, 255), outline=(194, 182, 162, 240))

                        # 2. Inner aged newsprint paper body (100% opaque RGB colors on paper_im so zero alpha holes occur)
                        inner_tear_poly = _torn_poly(pad, pad, iw, ih, amp=4.2, seed_off=seed_val + 0.18, deckle_bias=0.0)
                        paper_mask = Image.new("L", (card_w, card_h), 0)
                        ImageDraw.Draw(paper_mask).polygon(inner_tear_poly, fill=255)

                        paper_im = Image.new("RGBA", (card_w, card_h), (238, 229, 210, 255))
                        pdraw = ImageDraw.Draw(paper_im)
                        for py in range(ih + 24):
                            t = py / max(1, ih + 23)
                            r_c = int(243 - 20 * t)
                            g_c = int(235 - 24 * t)
                            b_c = int(218 - 30 * t)
                            pdraw.line([(pad - 12, pad - 12 + py), (pad + iw + 12, pad - 12 + py)], fill=(r_c, g_c, b_c, 255))

                        pad_side = max(13, int(float(layer.get("borderWidth") or 15)))
                        pad_top = max(16, int(round(pad_side * 1.12)))
                        pad_bot = max(23, int(round(pad_side * 1.52)))

                        # Subtle newspaper column rule lines & printed text blocks in top/bottom torn margins (solid RGB -> alpha=255)
                        pdraw.line([(pad + 6, pad + 6), (pad + iw - 6, pad + 6)], fill=(158, 146, 128, 255), width=1)
                        pdraw.line([(pad + 8, pad + 10), (pad + int(iw * 0.42), pad + 10)], fill=(172, 160, 142, 255), width=2)
                        pdraw.line([(pad + int(iw * 0.66), pad + 10), (pad + iw - 8, pad + 10)], fill=(176, 164, 146, 255), width=2)

                        bot_y0 = pad + ih - pad_bot + 5
                        pdraw.line([(pad + pad_side, bot_y0), (pad + iw - pad_side, bot_y0)], fill=(152, 140, 122, 255), width=1)
                        for r_idx, w_frac in enumerate([0.88, 0.62]):
                            ly = bot_y0 + 5 + r_idx * 5
                            if ly < pad + ih - 3:
                                pdraw.line(
                                    [(pad + pad_side, ly), (pad + pad_side + int((iw - pad_side * 2) * w_frac), ly)],
                                    fill=(166, 154, 136, 255),
                                    width=2,
                                )

                        card.paste(paper_im, (0, 0), paper_mask)
                        cdraw = ImageDraw.Draw(card)
                        cdraw.line(inner_tear_poly + [inner_tear_poly[0]], fill=(162, 148, 126, 235), width=1)

                        # 3. Inner newspaper photograph with editorial ink border
                        ph_w = max(24, iw - pad_side * 2)
                        ph_h = max(24, ih - pad_top - pad_bot)
                        cropped_p, _ = _crop_pip_rgba(ph_w, ph_h, rad=0)
                        px0, py0 = pad + pad_side, pad + pad_top
                        card.paste(cropped_p, (px0, py0))
                        cdraw.rectangle([px0 - 1, py0 - 1, px0 + ph_w, py0 + ph_h], outline=(42, 36, 30, 255), width=2)

                    elif is_vintage:
                        # Deep realistic drop shadow under old photograph
                        cdraw.rounded_rectangle([pad + 6, pad + 10, pad + iw + 6, pad + ih + 10], radius=3, fill=(0, 0, 0, 228))
                        card = card.filter(ImageFilter.GaussianBlur(radius=9))
                        cdraw = ImageDraw.Draw(card)

                        # Vintage aged cream photographic paper mat
                        pad_side = max(11, int(float(layer.get("borderWidth") or 14)))
                        pad_bot = max(pad_side + 5, int(round(pad_side * 1.32)))
                        for py in range(ih):
                            t = py / max(1, ih - 1)
                            r_c = int(246 - 20 * t)
                            g_c = int(238 - 25 * t)
                            b_c = int(220 - 34 * t)
                            cdraw.line([(pad, pad + py), (pad + iw - 1, pad + py)], fill=(r_c, g_c, b_c, 255))
                        cdraw.rounded_rectangle([pad, pad, pad + iw, pad + ih], radius=3, outline=(168, 146, 112, 255), width=2)
                        cdraw.rounded_rectangle([pad + 2, pad + 2, pad + iw - 2, pad + ih - 2], radius=2, outline=(252, 247, 236, 220), width=2)

                        ph_w = max(24, iw - pad_side * 2)
                        ph_h = max(24, ih - pad_side - pad_bot)
                        cropped_p, _ = _crop_pip_rgba(ph_w, ph_h, rad=0)
                        card.paste(cropped_p, (pad + pad_side, pad + pad_side))
                        cdraw.rectangle([pad + pad_side - 1, pad + pad_side - 1, pad + pad_side + ph_w, pad + pad_side + ph_h], outline=(58, 48, 38, 255), width=2)

                    elif frame_style == "caution_tape":
                        rad = 14
                        # Outer shadow + colored rim glow
                        cdraw.rounded_rectangle([pad + 4, pad + 9, pad + iw + 4, pad + ih + 9], radius=rad, fill=(0, 0, 0, 225))
                        cdraw.rounded_rectangle([pad - 2, pad - 2, pad + iw + 2, pad + ih + 2], radius=rad + 2, outline=(b_rgba[0], b_rgba[1], b_rgba[2], 145), width=bw + 6)
                        card = card.filter(ImageFilter.GaussianBlur(radius=8))
                        cdraw = ImageDraw.Draw(card)

                        pip_im, pip_mask = _crop_pip_rgba(iw, ih, rad=rad)
                        # Draw caution tape bar at bottom of pip_im before masking
                        tape_h = max(20, min(30, int(round(ih * 0.105))))
                        ty0 = ih - tape_h
                        pdraw = ImageDraw.Draw(pip_im)
                        pdraw.rectangle([0, ty0, iw, ih], fill=(250, 204, 21, 255))
                        stripe_step = 24
                        for sx_pos in range(-tape_h, iw + tape_h, stripe_step):
                            pdraw.polygon(
                                [
                                    (sx_pos, ih),
                                    (sx_pos + 12, ih),
                                    (sx_pos + 12 + int(tape_h * 0.75), ty0),
                                    (sx_pos + int(tape_h * 0.75), ty0),
                                ],
                                fill=(10, 14, 23, 255),
                            )
                        pdraw.line([(0, ty0), (iw, ty0)], fill=(10, 14, 23, 255), width=3)
                        pdraw.line([(0, ty0 + 2), (iw, ty0 + 2)], fill=(255, 255, 255, 190), width=1)

                        card.paste(pip_im, (pad, pad), pip_mask)
                        cdraw.rounded_rectangle([pad - 2, pad - 2, pad + iw + 2, pad + ih + 2], radius=rad + 2, outline=(5, 8, 15, 235), width=bw + 4)
                        cdraw.rounded_rectangle([pad, pad, pad + iw, pad + ih], radius=rad, outline=b_rgba, width=max(5, bw))
                        cdraw.rounded_rectangle([pad + bw, pad + bw, pad + iw - bw, pad + ih - bw], radius=max(4, rad - bw), outline=(255, 255, 255, 165), width=2)

                    elif frame_style in ("amber_glow_double", "double_neon", "neon_cyber"):
                        rad = 15
                        # Strong outer luminous halo glow + deep drop shadow
                        cdraw.rounded_rectangle([pad + 4, pad + 8, pad + iw + 4, pad + ih + 8], radius=rad, fill=(0, 0, 0, 220))
                        cdraw.rounded_rectangle([pad - 4, pad - 4, pad + iw + 4, pad + ih + 4], radius=rad + 4, outline=(b_rgba[0], b_rgba[1], b_rgba[2], 195), width=bw + 10)
                        card = card.filter(ImageFilter.GaussianBlur(radius=10))
                        cdraw = ImageDraw.Draw(card)

                        pip_im, pip_mask = _crop_pip_rgba(iw, ih, rad=rad)
                        card.paste(pip_im, (pad, pad), pip_mask)
                        # Outer dark contrast guard + main neon border + dark trench + inner bright core rim
                        use_bw = max(6, bw)
                        cdraw.rounded_rectangle([pad - 2, pad - 2, pad + iw + 2, pad + ih + 2], radius=rad + 2, outline=(5, 8, 15, 220), width=use_bw + 4)
                        cdraw.rounded_rectangle([pad, pad, pad + iw, pad + ih], radius=rad, outline=b_rgba, width=use_bw)
                        in_off = use_bw
                        cdraw.rounded_rectangle([pad + in_off, pad + in_off, pad + iw - in_off, pad + ih - in_off], radius=max(4, rad - in_off), outline=(9, 13, 22, 245), width=4)
                        in_off2 = in_off + 3
                        inner_rim_col = (255, 251, 235, 240) if frame_style == "amber_glow_double" else (255, 255, 255, 240)
                        cdraw.rounded_rectangle([pad + in_off2, pad + in_off2, pad + iw - in_off2, pad + ih - in_off2], radius=max(3, rad - in_off2), outline=inner_rim_col, width=2)

                    elif frame_style == "cctv_hud":
                        rad = 10
                        cdraw.rounded_rectangle([pad + 4, pad + 8, pad + iw + 4, pad + ih + 8], radius=rad, fill=(0, 0, 0, 225))
                        cdraw.rounded_rectangle([pad - 2, pad - 2, pad + iw + 2, pad + ih + 2], radius=rad + 2, outline=(b_rgba[0], b_rgba[1], b_rgba[2], 150), width=bw + 6)
                        card = card.filter(ImageFilter.GaussianBlur(radius=8))
                        cdraw = ImageDraw.Draw(card)

                        pip_im, pip_mask = _crop_pip_rgba(iw, ih, rad=rad)
                        pdraw = ImageDraw.Draw(pip_im, "RGBA")
                        # Top HUD bar & REC badge inside CCTV monitor
                        pdraw.rectangle([0, 0, iw, 34], fill=(6, 10, 18, 145))
                        pdraw.rounded_rectangle([12, 8, 96, 30], radius=6, fill=(9, 13, 22, 215), outline=(255, 255, 255, 90), width=1)
                        pdraw.ellipse([20, 13, 32, 25], fill=(255, 36, 36, 255))
                        try:
                            hud_fnt = ImageFont.truetype(str(_resolve_pil_font_path("Pretendard ExtraBold", "REC")), 13)
                            pdraw.text((38, 11), "REC", font=hud_fnt, fill=(255, 255, 255, 245))
                        except Exception:
                            pass
                        # Center edge crosshair ticks
                        mx, my = iw // 2, ih // 2
                        for l_pts in [
                            [(mx, 4), (mx, 14)],
                            [(mx, ih - 14), (mx, ih - 4)],
                            [(4, my), (14, my)],
                            [(iw - 14, my), (iw - 4, my)],
                        ]:
                            pdraw.line(l_pts, fill=(255, 255, 255, 160), width=2)

                        card.paste(pip_im, (pad, pad), pip_mask)
                        cdraw.rounded_rectangle([pad, pad, pad + iw, pad + ih], radius=rad, outline=(9, 13, 22, 240), width=4)
                        cdraw.rounded_rectangle([pad + 2, pad + 2, pad + iw - 2, pad + ih - 2], radius=max(4, rad - 2), outline=(b_rgba[0], b_rgba[1], b_rgba[2], 185), width=2)

                        # 4 Tactical Corner Viewfinder Brackets
                        c_len = max(26, int(min(iw, ih) * 0.22))
                        c_w = max(6, bw + 2)
                        x0, y0, x1, y1 = pad - 2, pad - 2, pad + iw + 2, pad + ih + 2
                        corner_polys = [
                            [(x0, y0 + c_len), (x0, y0), (x0 + c_len, y0)],
                            [(x1 - c_len, y0), (x1, y0), (x1, y0 + c_len)],
                            [(x1, y1 - c_len), (x1, y1), (x1 - c_len, y1)],
                            [(x0 + c_len, y1), (x0, y1), (x0, y1 - c_len)],
                        ]
                        for c_pts in corner_polys:
                            cdraw.line(c_pts, fill=(0, 0, 0, 235), width=c_w + 4, joint="curve")
                            cdraw.line(c_pts, fill=b_rgba, width=c_w, joint="curve")

                    elif frame_style == "dossier_tab":
                        rad = 12
                        cdraw.rounded_rectangle([pad + 4, pad + 9, pad + iw + 4, pad + ih + 9], radius=rad, fill=(0, 0, 0, 225))
                        card = card.filter(ImageFilter.GaussianBlur(radius=8))
                        cdraw = ImageDraw.Draw(card)

                        pip_im, pip_mask = _crop_pip_rgba(iw, ih, rad=rad)
                        pdraw = ImageDraw.Draw(pip_im, "RGBA")
                        bar_h = 26
                        pdraw.rectangle([0, 0, iw, bar_h], fill=(15, 23, 42, 242))
                        pdraw.rectangle([0, 0, 74, bar_h], fill=b_rgba)
                        pdraw.line([(0, bar_h), (iw, bar_h)], fill=b_rgba, width=2)
                        for d_idx, d_col in enumerate([(255, 255, 255, 240), (255, 255, 255, 175), (255, 255, 255, 110)]):
                            dx0 = 14 + d_idx * 16
                            pdraw.ellipse([dx0, 9, dx0 + 8, 17], fill=d_col)

                        card.paste(pip_im, (pad, pad), pip_mask)
                        cdraw.rounded_rectangle([pad - 2, pad - 2, pad + iw + 2, pad + ih + 2], radius=rad + 2, outline=(5, 8, 15, 235), width=bw + 4)
                        cdraw.rounded_rectangle([pad, pad, pad + iw, pad + ih], radius=rad, outline=b_rgba, width=max(5, bw))
                        cdraw.rounded_rectangle([pad + bw, pad + bw, pad + iw - bw, pad + ih - bw], radius=max(4, rad - bw), outline=(255, 255, 255, 150), width=2)

                    else:
                        rad = 14
                        cdraw.rounded_rectangle([pad + 4, pad + 8, pad + iw + 4, pad + ih + 8], radius=rad, fill=(0, 0, 0, 215))
                        cdraw.rounded_rectangle([pad - 2, pad - 2, pad + iw + 2, pad + ih + 2], radius=rad + 2, outline=(b_rgba[0], b_rgba[1], b_rgba[2], 125), width=bw + 4)
                        card = card.filter(ImageFilter.GaussianBlur(radius=7))
                        cdraw = ImageDraw.Draw(card)
                        pip_im, pip_mask = _crop_pip_rgba(iw, ih, rad=rad)
                        card.paste(pip_im, (pad, pad), pip_mask)
                        cdraw.rounded_rectangle([pad - 1, pad - 1, pad + iw + 1, pad + ih + 1], radius=rad + 1, outline=(5, 8, 15, 220), width=bw + 3)
                        cdraw.rounded_rectangle([pad, pad, pad + iw, pad + ih], radius=rad, outline=b_rgba, width=bw)
                        cdraw.rounded_rectangle([pad + bw, pad + bw, pad + iw - bw, pad + ih - bw], radius=max(4, rad - bw), outline=(255, 255, 255, 140), width=1)

                    if abs(angle) > 0.3:
                        card = card.rotate(-angle, resample=Image.Resampling.BICUBIC, expand=True)
                    pip_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
                    paste_x = int(round(ix + iw / 2.0 - card.width / 2.0))
                    paste_y = int(round(iy + ih / 2.0 - card.height / 2.0))
                    pip_layer.paste(card, (paste_x, paste_y), card)
                    base = Image.alpha_composite(base, pip_layer)
                except Exception:
                    pass

        elif ltype == "circle":
            cx = float(layer.get("left") or 0)
            cy = float(layer.get("top") or 0)
            w = max(20.0, float(layer.get("width") or 240))
            h = max(20.0, float(layer.get("height") or 240))
            sw = max(3, int(float(layer.get("strokeWidth") or 10)))
            circle_style = str(layer.get("circleStyle") or ("dashed_forensic" if layer.get("dashed") else "solid_ring")).strip().lower()
            color = _hex_to_rgba(layer.get("stroke") or "#ef4444", int(255 * opacity))
            outer_c = _hex_to_rgba(layer.get("outerStroke") or "#000000", int(195 * opacity))
            c_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            cdraw = ImageDraw.Draw(c_layer)
            rx, ry = w / 2.0, h / 2.0
            center_x, center_y = cx + rx, cy + ry

            def _draw_arc_segments(r_x: float, r_y: float, segs: int, duty: float, width_px: int, col: tuple[int, int, int, int], out_col: tuple[int, int, int, int] | None = None, rot_offset: float = 0.0) -> None:
                for s_idx in range(segs):
                    a0 = rot_offset + (2 * math.pi * s_idx) / segs
                    a1 = a0 + (2 * math.pi * duty) / segs
                    pts = [
                        (center_x + r_x * math.cos(a0 + (a1 - a0) * k / 8.0), center_y + r_y * math.sin(a0 + (a1 - a0) * k / 8.0))
                        for k in range(9)
                    ]
                    if out_col is not None:
                        cdraw.line(pts, fill=out_col, width=width_px + 6, joint="curve")
                    cdraw.line(pts, fill=col, width=width_px, joint="curve")

            if circle_style == "spotlight_glow":
                fill_tint = _hex_to_rgba(layer.get("fill") or layer.get("stroke") or "#ffe600", int(48 * opacity))
                cdraw.ellipse([cx, cy, cx + w, cy + h], fill=fill_tint, outline=outer_c, width=sw + 8)
                cdraw.ellipse([cx, cy, cx + w, cy + h], outline=color, width=sw)
            elif circle_style in ("dashed_forensic", "dashed") or (layer.get("dashed") and circle_style == "solid_ring"):
                _draw_arc_segments(rx, ry, 20, 0.62, sw, color, outer_c)
            elif circle_style == "dotted_orbit":
                _draw_arc_segments(rx, ry, 28, 0.22, max(6, sw + 2), color, outer_c)
            elif circle_style == "double_ring":
                cdraw.ellipse([cx, cy, cx + w, cy + h], outline=outer_c, width=sw + 6)
                cdraw.ellipse([cx, cy, cx + w, cy + h], outline=color, width=sw)
                in_x, in_y = max(12.0, rx * 0.18), max(12.0, ry * 0.18)
                cdraw.ellipse([cx + in_x, cy + in_y, cx + w - in_x, cy + h - in_y], outline=outer_c, width=max(2, sw // 2) + 4)
                cdraw.ellipse([cx + in_x, cy + in_y, cx + w - in_x, cy + h - in_y], outline=color, width=max(2, sw // 2))
            elif circle_style == "crosshair_sniper":
                cdraw.ellipse([cx, cy, cx + w, cy + h], outline=outer_c, width=sw + 6)
                cdraw.ellipse([cx, cy, cx + w, cy + h], outline=color, width=sw)
                tk_x, tk_y = max(16.0, rx * 0.28), max(16.0, ry * 0.28)
                ticks = [
                    [(center_x, cy - tk_y * 0.45), (center_x, cy + tk_y * 0.85)],
                    [(center_x, cy + h - tk_y * 0.85), (center_x, cy + h + tk_y * 0.45)],
                    [(cx - tk_x * 0.45, center_y), (cx + tk_x * 0.85, center_y)],
                    [(cx + w - tk_x * 0.85, center_y), (cx + w + tk_x * 0.45, center_y)],
                ]
                for t_pts in ticks:
                    cdraw.line(t_pts, fill=outer_c, width=max(3, int(sw * 0.8)) + 4)
                    cdraw.line(t_pts, fill=color, width=max(3, int(sw * 0.8)))
                dot_r = max(4.0, sw * 0.65)
                cdraw.ellipse([center_x - dot_r, center_y - dot_r, center_x + dot_r, center_y + dot_r], fill=color, outline=outer_c, width=2)
            elif circle_style == "hand_drawn_double":
                for pass_idx, (sx_m, sy_m, dx_m, dy_m) in enumerate([(1.0, 0.96, -3.0, -2.0), (0.96, 1.02, 3.0, 2.0)]):
                    p_w = max(2, int(sw * (0.85 if pass_idx == 0 else 0.68)))
                    cdraw.ellipse(
                        [center_x - rx * sx_m + dx_m, center_y - ry * sy_m + dy_m, center_x + rx * sx_m + dx_m, center_y + ry * sy_m + dy_m],
                        outline=outer_c if pass_idx == 0 else color,
                        width=p_w + (4 if pass_idx == 0 else 0),
                    )
                    cdraw.ellipse(
                        [center_x - rx * sx_m + dx_m, center_y - ry * sy_m + dy_m, center_x + rx * sx_m + dx_m, center_y + ry * sy_m + dy_m],
                        outline=color,
                        width=p_w,
                    )
            elif circle_style == "cctv_brackets":
                bx, by = max(22.0, w * 0.26), max(22.0, h * 0.26)
                corners = [
                    [(cx, cy + by), (cx, cy), (cx + bx, cy)],
                    [(cx + w - bx, cy), (cx + w, cy), (cx + w, cy + by)],
                    [(cx + w, cy + h - by), (cx + w, cy + h), (cx + w - bx, cy + h)],
                    [(cx + bx, cy + h), (cx, cy + h), (cx, cy + h - by)],
                ]
                for c_pts in corners:
                    cdraw.line(c_pts, fill=outer_c, width=sw + 6, joint="curve")
                    cdraw.line(c_pts, fill=color, width=sw, joint="curve")
                _draw_arc_segments(rx * 0.72, ry * 0.72, 16, 0.5, max(2, sw // 2), color, None)
            elif circle_style == "hazard_segments":
                _draw_arc_segments(rx, ry, 6, 0.62, sw + 2, color, outer_c, rot_offset=0.2)
                in_x, in_y = max(10.0, rx * 0.14), max(10.0, ry * 0.14)
                cdraw.ellipse([cx + in_x, cy + in_y, cx + w - in_x, cy + h - in_y], outline=color, width=max(2, sw // 3))
            elif circle_style == "magnifying_loupe":
                fill_glass = (255, 255, 255, int(28 * opacity))
                cdraw.ellipse([cx, cy, cx + w, cy + h], fill=fill_glass, outline=outer_c, width=sw + 6)
                cdraw.ellipse([cx, cy, cx + w, cy + h], outline=color, width=sw)
                hx0 = center_x + rx * 0.68
                hy0 = center_y + ry * 0.68
                hx1 = center_x + rx * 1.18
                hy1 = center_y + ry * 1.18
                cdraw.line([(hx0, hy0), (hx1, hy1)], fill=outer_c, width=sw * 2 + 6)
                cdraw.line([(hx0, hy0), (hx1, hy1)], fill=color, width=sw * 2)
            else:
                cdraw.ellipse([cx, cy, cx + w, cy + h], outline=outer_c, width=sw + 6)
                cdraw.ellipse([cx, cy, cx + w, cy + h], outline=color, width=sw)
            base = Image.alpha_composite(base, c_layer)

        elif ltype == "arrow":
            ax = float(layer.get("left") or 0)
            ay = float(layer.get("top") or 0)
            aw = max(40, int(float(layer.get("width") or 170)))
            ah = max(24, int(float(layer.get("height") or 64)))
            angle = float(layer.get("angle") or 0)
            flip_x = bool(layer.get("flipX"))
            flip_y = bool(layer.get("flipY"))
            arrow_style = str(layer.get("arrowStyle") or "curved_pointer").strip().lower()

            ar_im = Image.new("RGBA", (aw + 56, ah + 56), (0, 0, 0, 0))
            adraw = ImageDraw.Draw(ar_im)
            sx, sy = aw / 170.0, ah / 64.0
            ox, oy = 28.0, 28.0
            stroke_c = _hex_to_rgba(layer.get("stroke") or "#000000", int(255 * opacity))
            fill_c = _hex_to_rgba(layer.get("fill") or "#ff0000", int(255 * opacity))
            sw_val = max(2, int(float(layer.get("strokeWidth") if layer.get("strokeWidth") is not None else 4)))

            polygons_list: list[list[tuple[float, float]]] = []
            if arrow_style == "block_3d":
                polygons_list = [[
                    (10, 16), (98, 16), (98, 2), (164, 32),
                    (98, 62), (98, 48), (10, 48),
                ]]
            elif arrow_style == "sharp_tactical":
                polygons_list = [[
                    (6, 12), (106, 20), (98, 2), (166, 32),
                    (98, 62), (106, 44), (6, 52), (30, 32),
                ]]
            elif arrow_style == "double_chevron":
                polygons_list = [
                    [(6, 8), (46, 8), (82, 32), (46, 56), (6, 56), (38, 32)],
                    [(72, 8), (114, 8), (166, 32), (114, 56), (72, 56), (104, 32)],
                ]
            elif arrow_style == "curved_steep":
                polygons_list = [[
                    (8, 58), (18, 28), (42, 10), (78, 6), (118, 18),
                    (134, 4), (164, 48), (106, 52), (118, 36),
                    (82, 24), (48, 28), (24, 62),
                ]]
            elif arrow_style == "zigzag_shock":
                polygons_list = [[
                    (4, 48), (52, 10), (76, 28), (114, 10),
                    (108, 0), (166, 26), (120, 62), (122, 44),
                    (68, 52), (48, 32), (16, 60),
                ]]
            elif arrow_style == "dashed_stem":
                polygons_list = [
                    [(6, 20), (30, 20), (30, 44), (6, 44)],
                    [(40, 20), (66, 20), (66, 44), (40, 44)],
                    [(76, 20), (108, 20), (108, 3), (166, 32), (108, 61), (108, 44), (76, 44)],
                ]
            elif arrow_style == "double_ended":
                polygons_list = [[
                    (4, 32), (48, 4), (48, 20), (122, 20), (122, 4),
                    (166, 32), (122, 60), (122, 44), (48, 44), (48, 60),
                ]]
            elif arrow_style == "hand_drawn_sketch":
                polygons_list = [[
                    (8, 46), (48, 20), (92, 14), (128, 22),
                    (114, 4), (164, 32), (114, 60), (126, 38),
                    (90, 28), (52, 34), (14, 58),
                ]]
            else:
                polygons_list = [[
                    (6, 38), (38, 16), (76, 8), (110, 14),
                    (104, 0), (166, 34), (108, 64), (114, 46),
                    (78, 38), (44, 44), (16, 60),
                ]]

            scaled_polys = [
                [(ox + px * sx, oy + py * sy) for px, py in raw_pts]
                for raw_pts in polygons_list
            ]
            for poly in scaled_polys:
                sh_poly = [(px + 4, py + 7) for px, py in poly]
                adraw.polygon(sh_poly, fill=(0, 0, 0, 215))
            ar_im = ar_im.filter(ImageFilter.GaussianBlur(radius=4))
            adraw = ImageDraw.Draw(ar_im)
            for poly in scaled_polys:
                if arrow_style == "neon_hollow":
                    hollow_fill = (fill_c[0], fill_c[1], fill_c[2], int(42 * opacity))
                    adraw.polygon(poly, fill=hollow_fill, outline=fill_c, width=max(5, sw_val + 4))
                    adraw.polygon(poly, fill=None, outline=stroke_c, width=max(2, sw_val // 2))
                else:
                    adraw.polygon(poly, fill=fill_c, outline=stroke_c, width=sw_val)
            if flip_x:
                ar_im = ar_im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if flip_y:
                ar_im = ar_im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            if abs(angle) > 0.5:
                ar_im = ar_im.rotate(-angle, resample=Image.Resampling.BICUBIC, expand=True)
            ar_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            paste_x = int(round(ax + aw / 2.0 - ar_im.width / 2.0))
            paste_y = int(round(ay + ah / 2.0 - ar_im.height / 2.0))
            ar_layer.paste(ar_im, (paste_x, paste_y), ar_im)
            base = Image.alpha_composite(base, ar_layer)

        elif ltype in ("badge", "stamp"):
            text = str(layer.get("text") or "").strip()
            if not text:
                continue
            fs = max(20, int(float(layer.get("fontSize") or (38 if ltype == "badge" else 28))))
            fpath = _resolve_pil_font_path(layer.get("fontFamily") or "", text)
            fnt = ImageFont.truetype(str(fpath), fs)
            dummy = ImageDraw.Draw(base)
            bbox = dummy.textbbox((0, 0), text, font=fnt)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            pad_x = 28 if ltype == "badge" else 20
            bw = max(int(float(layer.get("width") or 180)), tw + pad_x * 2)
            bh = max(int(float(layer.get("height") or 58)), fs + 26)
            lx, ly = int(float(layer.get("left") or 54)), int(float(layer.get("top") or 42))
            rad = int(float(layer.get("borderRadius") or 10))
            raw_bg = str(layer.get("bgColor") or "").strip().lower()
            is_transparent_bg = raw_bg in ("transparent", "none")

            if is_transparent_bg:
                tx = lx - bbox[0]
                ty = ly + (bh - th) // 2 - bbox[1]
                pil_sw = max(6, int(round(fs * 0.135)))
                sh_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
                sdraw = ImageDraw.Draw(sh_layer)
                sdraw.text((tx, ty + 5), text, font=fnt, fill=(0, 0, 0, 235), stroke_width=pil_sw + 4, stroke_fill=(0, 0, 0, 235))
                sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(radius=6))
                b_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
                bdraw = ImageDraw.Draw(b_layer)
                bdraw.text((tx + 2, ty + 3), text, font=fnt, fill=(0, 0, 0, 255), stroke_width=pil_sw, stroke_fill=(0, 0, 0, 255))
                bdraw.text((tx, ty), text, font=fnt, fill=_hex_to_rgba(layer.get("fill") or "#1aff00"), stroke_width=pil_sw, stroke_fill=(0, 0, 0, 255))
                base = Image.alpha_composite(Image.alpha_composite(base, sh_layer), b_layer)
            else:
                if ltype == "badge":
                    b_sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
                    bsh_draw = ImageDraw.Draw(b_sh)
                    bsh_draw.rounded_rectangle([lx, ly + 4, lx + bw, ly + bh + 4], radius=rad, fill=(0, 0, 0, 200))
                    b_sh = b_sh.filter(ImageFilter.GaussianBlur(radius=6))
                    base = Image.alpha_composite(base, b_sh)

                b_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
                bdraw = ImageDraw.Draw(b_layer)
                bg_c = _hex_to_rgba(layer.get("bgColor") or "#dc2626", 245 if ltype == "badge" else 45)
                bd_c = _hex_to_rgba(layer.get("borderColor") or layer.get("stroke") or "#ffffff", 255)
                bdraw.rounded_rectangle([lx, ly, lx + bw, ly + bh], radius=rad, fill=bg_c, outline=bd_c, width=max(2, int(float(layer.get("borderWidth") or 3))))
                tx = lx + (bw - tw) // 2 - bbox[0]
                ty = ly + (bh - th) // 2 - bbox[1]
                if ltype == "badge":
                    bdraw.text((tx, ty), text, font=fnt, fill=_hex_to_rgba(layer.get("fill") or "#ffffff"), stroke_width=3, stroke_fill=(0, 0, 0, 230))
                else:
                    bdraw.text((tx, ty), text, font=fnt, fill=_hex_to_rgba(layer.get("fill") or "#ffffff"))
                base = Image.alpha_composite(base, b_layer)

        elif ltype == "textbox":
            raw_text = str(layer.get("text") or "").strip()
            if not raw_text:
                continue
            plain_text, segments = _parse_inline_highlight_segments(raw_text)
            if not plain_text:
                continue
            fs = max(28, int(float(layer.get("fontSize") or 76)))
            fpath = _resolve_pil_font_path(layer.get("fontFamily") or "", plain_text)
            fnt = ImageFont.truetype(str(fpath), fs)
            dummy = ImageDraw.Draw(base)
            bbox = dummy.textbbox((0, 0), plain_text, font=fnt)
            tw = bbox[2] - bbox[0]
            max_allowed = cw - 72
            while tw > max_allowed and fs > 40:
                fs -= 2
                fnt = ImageFont.truetype(str(fpath), fs)
                bbox = dummy.textbbox((0, 0), plain_text, font=fnt)
                tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            lx = int(float(layer.get("left") or 54))
            ly = int(float(layer.get("top") or 400))
            lh = max(70, int(fs * 1.25))
            t_align = str(layer.get("textAlign") or "left").strip().lower()
            l_w = float(layer.get("width") or 0)
            if t_align == "center":
                if l_w > 100:
                    tx = int(round(lx + (l_w - tw) / 2.0)) - bbox[0]
                else:
                    tx = (cw - tw) // 2 - bbox[0]
            elif t_align == "right" and l_w > 100:
                tx = int(round(lx + l_w - tw)) - bbox[0]
            else:
                tx = lx - bbox[0]
            ty = ly + (lh - th) // 2 - bbox[1]

            # Note: In PIL, stroke_width is radius (1/2 of HTML5 canvas lineWidth)
            canvas_sw = float(layer.get("strokeWidth") if layer.get("strokeWidth") is not None else 16)
            pil_sw = max(4, min(int(round(canvas_sw * 0.55)), max(5, int(round(fs * 0.135)))))
            stroke_c = _hex_to_rgba(layer.get("stroke") or "#000000", 255)
            fill_c = _hex_to_rgba(layer.get("fill") or "#ffffff", 255)
            main_hex = str(layer.get("fill") or "#ffffff").lower()
            default_hl = "#ff2424" if main_hex in ("#ffe600", "#ffe84a", "#fbbf24", "#facc15") else "#ffe600"
            hl_c = _hex_to_rgba(layer.get("highlightFill") or default_hl, 255)

            sh_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            sdraw = ImageDraw.Draw(sh_layer)
            sdraw.text((tx, ty + 6), plain_text, font=fnt, fill=(0, 0, 0, 235), stroke_width=pil_sw + 5, stroke_fill=(0, 0, 0, 235))
            sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(radius=7))

            txt_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            tdraw = ImageDraw.Draw(txt_layer)
            tdraw.text((tx + 2, ty + 4), plain_text, font=fnt, fill=stroke_c, stroke_width=pil_sw, stroke_fill=stroke_c)
            if len(segments) <= 1 and not segments[0][1]:
                tdraw.text((tx, ty), plain_text, font=fnt, fill=fill_c, stroke_width=pil_sw, stroke_fill=stroke_c)
            else:
                # First pass: full stroke outline so inter-character joins remain seamless
                tdraw.text((tx, ty), plain_text, font=fnt, fill=stroke_c, stroke_width=pil_sw, stroke_fill=stroke_c)
                # Second pass: per-segment fill with exact prefix advance width
                prefix = ""
                for seg_txt, is_hl in segments:
                    adv = int(round(dummy.textlength(prefix, font=fnt))) if prefix else 0
                    seg_color = hl_c if is_hl else fill_c
                    tdraw.text((tx + adv, ty), seg_txt, font=fnt, fill=seg_color, stroke_width=max(2, pil_sw // 2), stroke_fill=stroke_c)
                    prefix += seg_txt

            base = Image.alpha_composite(Image.alpha_composite(base, sh_layer), txt_layer)

    return base.convert("RGB")


def render_design_thumbnails_to_disk(workspace: Path, design: dict[str, Any]) -> dict[str, str]:
    """Render all variants in design to workspace/media/thumbnail/ and workspace/thumbnail.jpg."""
    workspace = workspace.resolve()
    thumb_dir = workspace / "media" / "thumbnail"
    exports_dir = thumb_dir / "exports"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    sanitize_thumbnail_design_fonts(design)
    variants = design.get("variants") if isinstance(design.get("variants"), list) else []
    active_id = str(design.get("active_variant_id") or "v1")
    written: dict[str, str] = {}

    for idx, v in enumerate(variants):
        if not isinstance(v, dict):
            continue
        vid = str(v.get("id") or f"v{idx + 1}").strip()
        img = render_variant_to_pil(workspace, design, v)
        p1 = thumb_dir / f"thumbnail_{vid}.jpg"
        p2 = exports_dir / f"thumbnail_{vid}.jpg"
        img.save(p1, format="JPEG", quality=93, optimize=True)
        img.save(p2, format="JPEG", quality=93, optimize=True)
        written[vid] = str(p2)
        if vid == active_id or (idx == 0 and not (workspace / "thumbnail.jpg").is_file()):
            root_thumb = workspace / "thumbnail.jpg"
            img.save(root_thumb, format="JPEG", quality=93, optimize=True)
            written["primary"] = str(root_thumb)

    return written


def decode_data_url_image(data_url: str) -> tuple[bytes, str]:
    """Decode a base64 data URL into raw image bytes and file extension."""
    raw = str(data_url or "").strip()
    if "," not in raw or not raw.startswith("data:image/"):
        raise ValueError("Dữ liệu ảnh gửi lên không đúng định dạng data:image/...")
    header, encoded = raw.split(",", 1)
    mime = header.split(";", 1)[0].removeprefix("data:").lower()
    ext_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    ext = ext_map.get(mime, ".jpg")
    try:
        image_bytes = base64.b64decode(encoded)
    except Exception as exc:
        raise ValueError("Không thể giải mã dữ liệu ảnh base64.") from exc
    if not image_bytes:
        raise ValueError("Dữ liệu ảnh rỗng.")
    return image_bytes, ext


def export_thumbnail_ab_pack(
    job_id: str,
    workspace: Path,
    design: dict[str, Any] | None = None,
    job: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render all 3 A/B/C variants to disk, write ab_test_metadata.json, and package into ab_test_pack.zip for YouTube Studio."""
    workspace = workspace.resolve()
    if design is None:
        design_file = workspace / "thumbnail_design.json"
        if design_file.is_file():
            try:
                design = json.loads(design_file.read_text(encoding="utf-8"))
            except Exception:
                design = {}
        if not design:
            design = build_default_thumbnail_design(job_id, workspace, job or {})

    sanitize_thumbnail_design_fonts(design)
    variants = design.get("variants") if isinstance(design.get("variants"), list) else []

    ab_dir = workspace / "media" / "thumbnails"
    ab_dir.mkdir(parents=True, exist_ok=True)
    exports_dir = workspace / "media" / "thumbnail" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    variant_letters = ["A", "B", "C", "D"]
    manifest_variants: list[dict[str, Any]] = []

    target_variants = variants[:3] if len(variants) >= 3 else variants
    for idx, v in enumerate(target_variants):
        if not isinstance(v, dict):
            continue
        let = variant_letters[idx]
        vid = str(v.get("id") or f"v{idx + 1}")
        img = render_variant_to_pil(workspace, design, v)

        out_name = f"variant_{let.lower()}.jpg"
        out_path = ab_dir / out_name
        img.save(out_path, format="JPEG", quality=95, optimize=True)

        exp_path = exports_dir / f"thumbnail_{vid}.jpg"
        img.save(exp_path, format="JPEG", quality=95, optimize=True)

        ctr = v.get("ctr_prediction") or evaluate_variant_ctr(v, design)
        manifest_variants.append({
            "variant_id": vid,
            "letter": let,
            "name": str(v.get("name") or f"Variant {let}"),
            "file_name": out_name,
            "relative_path": f"media/thumbnails/{out_name}",
            "url": f"/api/jobs/{job_id}/media?path=media/thumbnails/{out_name}&v={int(out_path.stat().st_mtime)}",
            "hook_type": str(v.get("hook_type") or "curiosity_paradox"),
            "hook_badge": str(v.get("hook_badge") or f"Variant {let}"),
            "psychological_hook": str(v.get("psychological_hook") or ""),
            "archetype": str(v.get("archetype") or "broadcast_left_heavy"),
            "headline_line_1": str(v.get("line_1") or ""),
            "headline_line_2": str(v.get("line_2") or ""),
            "badge_text": str(v.get("badge_text") or ""),
            "meaning_vi": str(v.get("meaning_vi") or ""),
            "paired_title": str(v.get("paired_title") or ""),
            "paired_title_vi": str(v.get("paired_title_vi") or ""),
            "keyword_anchor_vi": str(v.get("keyword_anchor_vi") or ""),
            "synergy_vi": str(v.get("synergy_vi") or ""),
            "ctr_prediction": ctr,
            "file_size_bytes": out_path.stat().st_size,
        })

    metadata = {
        "job_id": job_id,
        "title": str((job or {}).get("title") or (design or {}).get("title") or ""),
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
    meta_path = ab_dir / "ab_test_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    zip_path = ab_dir / "ab_test_pack.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for mv in manifest_variants:
            f_path = ab_dir / mv["file_name"]
            if f_path.is_file():
                zf.write(f_path, arcname=mv["file_name"])
        if meta_path.is_file():
            zf.write(meta_path, arcname="ab_test_metadata.json")

    mtime = int(zip_path.stat().st_mtime) if zip_path.is_file() else int(time.time())
    zip_url = f"/api/jobs/{job_id}/media?path=media/thumbnails/ab_test_pack.zip&v={mtime}"

    return {
        "ok": True,
        "job_id": job_id,
        "zip_path": str(zip_path),
        "zip_url": zip_url,
        "metadata_path": str(meta_path),
        "metadata": metadata,
        "variants": manifest_variants,
        "exported_count": len(manifest_variants),
    }


def select_thumbnail_winner(
    job_id: str,
    workspace: Path,
    variant_id: str,
    design: dict[str, Any] | None = None,
    job: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select the primary winning thumbnail variant and set as active thumbnail for publishing."""
    workspace = workspace.resolve()
    design_file = workspace / "thumbnail_design.json"
    if design is None:
        if design_file.is_file():
            try:
                design = json.loads(design_file.read_text(encoding="utf-8"))
            except Exception:
                design = {}
        if not design:
            design = build_default_thumbnail_design(job_id, workspace, job or {})

    sanitize_thumbnail_design_fonts(design)
    variants = design.get("variants") if isinstance(design.get("variants"), list) else []
    variant_id_clean = str(variant_id or "").strip().lower()
    alias_map = {
        "variant_a": "v1", "a": "v1", "variant a": "v1",
        "variant_b": "v2", "b": "v2", "variant b": "v2",
        "variant_c": "v3", "c": "v3", "variant c": "v3",
        "variant_d": "v4", "d": "v4", "variant d": "v4",
    }
    normalized_id = alias_map.get(variant_id_clean, variant_id)
    target_variant = next(
        (v for v in variants if isinstance(v, dict) and (
            v.get("id") == normalized_id or
            v.get("id") == variant_id or
            str(v.get("letter", "")).strip().lower() == variant_id_clean or
            str(v.get("id", "")).strip().lower() == variant_id_clean
        )),
        None,
    )
    if not target_variant and variants:
        target_variant = variants[0]
        variant_id = str(target_variant.get("id") or "v1")
    else:
        variant_id = str(target_variant.get("id") or normalized_id)

    if not target_variant:
        raise ValueError(f"Không tìm thấy biến thể {variant_id} trong thiết kế.")

    design["active_variant_id"] = variant_id
    design["updated_at"] = _now_iso()
    design["ctr_critique"] = evaluate_thumbnail_ctr(design)

    img = render_variant_to_pil(workspace, design, target_variant)

    root_thumb = workspace / "thumbnail.jpg"
    img.save(root_thumb, format="JPEG", quality=95, optimize=True)

    thumb_media_dir = workspace / "media" / "thumbnails"
    thumb_media_dir.mkdir(parents=True, exist_ok=True)
    media_thumb = thumb_media_dir / "thumbnail.jpg"
    img.save(media_thumb, format="JPEG", quality=95, optimize=True)

    exports_dir = workspace / "media" / "thumbnail" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    v_export = exports_dir / f"thumbnail_{variant_id}.jpg"
    img.save(v_export, format="JPEG", quality=95, optimize=True)

    design_file.write_text(json.dumps(design, indent=2, ensure_ascii=False), encoding="utf-8")

    mtime = int(root_thumb.stat().st_mtime) if root_thumb.is_file() else int(time.time())
    return {
        "ok": True,
        "job_id": job_id,
        "active_variant_id": variant_id,
        "variant_name": target_variant.get("name"),
        "hook_type": target_variant.get("hook_type"),
        "thumbnail_path": str(root_thumb),
        "thumbnail_url": f"/api/jobs/{job_id}/media?path=thumbnail.jpg&v={mtime}",
        "bytes": root_thumb.stat().st_size,
    }


