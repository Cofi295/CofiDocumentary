"""True Crime Vox & Real Satellite Compositing Archetypes Catalog.

Implements all 24 True Crime investigative visual archetypes in pure Python (Pillow + NumPy)
producing clean 1920x1080 frames with zero external Blender dependencies:
- Real Satellite Maps: #M1..#M8
- Forensic Dossiers & Biometrics: #D1..#D10
- Press, Curfew & Broadcast: #P1..#P6
- Fullscreen Cinema: cinema_full
"""

from __future__ import annotations

import math
import os
from typing import Any, Tuple
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from .typography import (
    draw_text_safe,
    get_font,
    split_balanced_korean,
    verify_text_glyphs,
)
from .gis_cache import (
    W,
    H,
    apply_infrared_thermal_shader,
    crop_map_camera,
    draw_geojson_feature_on_plate,
    draw_satellite_hud_grid,
    get_real_satellite_campus_z16,
    get_vox_styled_baiyin_lanzhou_base,
    get_vox_styled_baiyin_urban_base,
    get_vox_styled_gansu_base,
    load_gis_json,
    load_gis_plate,
    lonlat_to_plate_px,
    map_lonlat_to_screen,
)


# Physical palette
VOX_DESK_DARK = (30, 25, 21)       # #1E1915 Dark walnut
VOX_CORK_DARK = (64, 52, 41)       # #403429 Aged detective cork
VOX_WOOD_FRAME = (46, 35, 27)      # #2E231B Framed pinboard border
VOX_PAPER = (224, 213, 194)        # #E0D5C2 Warm aged manila paper
VOX_PAPER_DARK = (204, 190, 168)   # #CCBEA8 Aged kraft folder tone
VOX_MANILA = (214, 192, 152)       # #D6C098 Physical Manila folder
VOX_NEWSPRINT = (231, 224, 210)    # #E7E0D2 Archival newsprint
VOX_MEMO_YELLOW = (238, 218, 158)  # #EEDA9E Yellow memo pad
VOX_INK = (24, 22, 19)             # #181613 Deep typewriter ink
VOX_INK_MUTED = (84, 76, 66)       # #544C42 Aged charcoal ink
VOX_YELLOW = (182, 118, 36)        # #B67624 Aged brass / forensic amber
VOX_CRIMSON = (176, 30, 26)        # #B01E1A Forensic oxide red
VOX_TEAL = (36, 92, 94)            # #245C5E Archival jurisdiction teal
VOX_CREAM_CARD = (246, 241, 231)   # #F6F1E7 Photo print matte


_CACHE_DESK: Image.Image | None = None
_CACHE_CORK: Image.Image | None = None
_CACHE_TORN: dict[tuple[int, int, tuple[int, int, int], float, int], Image.Image] = {}


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def fit_crop(img: Image.Image, tw: int, th: int) -> Image.Image:
    """Scales and crops an image to fit exactly (tw, th) without black bars."""
    iw, ih = img.size
    overscan = 1.05 if (tw == W and th == H) else 1.02
    scale = max(tw / max(1, iw), th / max(1, ih)) * overscan
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = img.resize((nw, nh), Image.Resampling.BILINEAR)
    x0 = max(0, (nw - tw) // 2)
    y0 = max(0, (nh - th) // 2)
    return resized.crop((x0, y0, x0 + tw, y0 + th))


def get_fallback_image(tw: int, th: int, label: str = "EVIDENCE") -> Image.Image:
    """Creates a high-contrast cinematic placeholder frame when user image is absent."""
    rng = np.random.default_rng(sum(ord(c) for c in label) % 997)
    noise = rng.normal(0, 10.0, (th // 4, tw // 4, 3))
    base = np.clip(np.array([28, 32, 38], dtype=np.float32) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(base, "RGB").resize((tw, th), Image.Resampling.BICUBIC)
    draw = ImageDraw.Draw(img, "RGBA")
    # Cross pattern
    draw.rectangle([0, 0, tw - 1, th - 1], outline=(56, 189, 248, 120), width=2)
    draw.line([(0, 0), (tw, th)], fill=(56, 189, 248, 30), width=1)
    draw.line([(0, th), (tw, 0)], fill=(56, 189, 248, 30), width=1)
    f = get_font(max(14, int(th * 0.08)), bold=True)
    draw_text_safe(draw, (20, th - int(th * 0.15)), label, fill=(240, 245, 250, 235), font_size=max(14, int(th * 0.08)), bold=True)
    return img


def get_dark_investigation_desk() -> Image.Image:
    """Dark walnut homicide detective desk background with subtle vignette."""
    global _CACHE_DESK
    if _CACHE_DESK is not None:
        return _CACHE_DESK.copy()

    rng = np.random.default_rng(19)
    sw, sh = W // 6, H // 6
    yy, xx = np.mgrid[0:sh, 0:sw]
    nx = (xx - sw * 0.5) / (sw * 0.55)
    ny = (yy - sh * 0.48) / (sh * 0.55)
    vignette = (1.0 - np.clip((nx * nx + ny * ny) * 0.22, 0, 0.35))[:, :, None]
    noise = rng.normal(0, 3.0, (sh, sw, 1))
    arr = np.clip((np.array(VOX_DESK_DARK, dtype=np.float32) + noise) * vignette, 0, 255).astype(np.uint8)
    desk = Image.fromarray(arr, "RGB").resize((W, H), Image.Resampling.BICUBIC)
    draw = ImageDraw.Draw(desk, "RGBA")
    for y in range(0, H, 18):
        draw.line([(0, y), (W, y)], fill=(18, 14, 11, 26), width=1)
    _CACHE_DESK = desk
    return desk.copy()


def get_cork_pinboard_shell() -> Image.Image:
    """Aged detective cork pinboard shell with dark timber frame."""
    global _CACHE_CORK
    if _CACHE_CORK is not None:
        return _CACHE_CORK.copy()

    rng = np.random.default_rng(33)
    sw, sh = W // 6, H // 6
    noise = rng.normal(0, 6.0, (sh, sw, 3))
    arr = np.clip(np.array(VOX_CORK_DARK, dtype=np.float32) + noise, 0, 255).astype(np.uint8)
    cork = Image.fromarray(arr, "RGB").resize((W, H), Image.Resampling.BICUBIC)
    draw = ImageDraw.Draw(cork, "RGBA")
    # Outer wood frame
    bw = 36
    draw.rectangle([0, 0, W, bw], fill=VOX_WOOD_FRAME)
    draw.rectangle([0, H - bw, W, H], fill=VOX_WOOD_FRAME)
    draw.rectangle([0, 0, bw, H], fill=VOX_WOOD_FRAME)
    draw.rectangle([W - bw, 0, W, H], fill=VOX_WOOD_FRAME)
    # Inner bevel shadow
    draw.rectangle([bw, bw, W - bw, H - bw], outline=(20, 16, 12, 180), width=4)
    _CACHE_CORK = cork
    return cork.copy()


def _build_torn_polygon(w: int, h: int, roughness: float = 4.0, seed: int = 7) -> list[tuple[float, float]]:
    rng = np.random.default_rng(seed)
    pts = []
    step = 14
    for x in range(0, w, step):
        dy = rng.uniform(-roughness, roughness) if 10 < x < w - 10 else 0
        pts.append((float(x), float(max(0, min(roughness * 1.4, abs(dy))))))
    for y in range(0, h, step):
        dx = rng.uniform(-roughness, roughness) if 10 < y < h - 10 else 0
        pts.append((float(w - max(0, min(roughness * 1.4, abs(dx)))), float(y)))
    for x in range(w, 0, -step):
        dy = rng.uniform(-roughness, roughness) if 10 < x < w - 10 else 0
        pts.append((float(x), float(h - max(0, min(roughness * 1.4, abs(dy))))))
    for y in range(h, 0, -step):
        dx = rng.uniform(-roughness, roughness) if 10 < y < h - 10 else 0
        pts.append((float(max(0, min(roughness * 1.4, abs(dx)))), float(y)))
    return pts


def get_torn_paper_sheet(
    w: int,
    h: int,
    fill_rgb: tuple[int, int, int] = VOX_CREAM_CARD,
    roughness: float = 4.0,
    seed: int = 11,
) -> Image.Image:
    """Generates a tactile torn-edge physical paper sheet with soft drop shadow."""
    key = (w, h, fill_rgb, round(roughness, 1), seed)
    if key in _CACHE_TORN:
        return _CACHE_TORN[key].copy()

    pad = 28
    cw, ch = w + pad * 2, h + pad * 2
    pts = _build_torn_polygon(w, h, roughness=roughness, seed=seed)
    pts_sh = [(x + pad + 6, y + pad + 9) for (x, y) in pts]
    pts_lip = [(x + pad + 2, y + pad + 3) for (x, y) in pts]

    shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow, "RGBA")
    sdraw.polygon(pts_sh, fill=(14, 11, 9, 96))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=9))

    draw = ImageDraw.Draw(shadow, "RGBA")
    draw.polygon(pts_lip, fill=(252, 249, 242, 235))

    rng = np.random.default_rng(seed + 100)
    sw, sh_s = max(8, w // 5), max(8, h // 5)
    noise = rng.normal(0, 3.2, (sh_s, sw, 1))
    base_arr = np.clip(np.array(fill_rgb, dtype=np.float32) + noise, 0, 255).astype(np.uint8)
    paper_tex = Image.fromarray(base_arr, "RGB").resize((w, h), Image.Resampling.BICUBIC).convert("RGBA")

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask, "L").polygon(pts, fill=255)

    sheet_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sheet_layer.paste(paper_tex, (pad, pad), mask)
    out = Image.alpha_composite(shadow, sheet_layer)

    _CACHE_TORN[key] = out
    return out.copy()


def _draw_paperclip(draw: ImageDraw.ImageDraw, x: float, y: float, tall: int = 56) -> None:
    x, y = int(x), int(y)
    draw.rounded_rectangle([x + 2, y + 3, x + 20, y + tall + 3], radius=8, outline=(18, 15, 12, 95), width=3)
    draw.rounded_rectangle([x, y, x + 18, y + tall], radius=8, outline=(196, 200, 204, 245), width=3)
    draw.rounded_rectangle([x + 4, y + 8, x + 14, y + tall - 10], radius=5, outline=(232, 236, 240, 235), width=2)


def _draw_brass_fastener(draw: ImageDraw.ImageDraw, cx: float, cy: float) -> None:
    cx, cy = int(cx), int(cy)
    draw.rectangle([cx - 48, cy - 5, cx + 48, cy + 7], fill=(22, 18, 14, 85))
    draw.rectangle([cx - 50, cy - 7, cx + 50, cy + 5], fill=(178, 136, 62, 255), outline=(92, 68, 28, 230), width=1)
    draw.line([(cx - 46, cy - 4), (cx + 46, cy - 4)], fill=(238, 208, 138, 210), width=2)
    for px in (cx - 28, cx + 28):
        draw.ellipse([px - 5, cy - 5, px + 5, cy + 5], fill=(116, 84, 34, 255), outline=(240, 210, 140, 190), width=1)


def _draw_circular_official_seal(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    dept_ko: str = "바이인시공안국",
    sub_ko: str = "형사과학기술감식전용장",
    r: int = 46,
    alpha: int = 205,
) -> None:
    cx, cy = int(cx), int(cy)
    col = VOX_CRIMSON + (int(alpha),)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=4)
    draw.ellipse([cx - r + 5, cy - r + 5, cx + r - 5, cy + r - 5], outline=VOX_CRIMSON + (int(alpha * 0.65),), width=1)
    # Center star
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = 14 if i % 2 == 0 else 6
        pts.append((cx + rad * math.cos(ang), cy - 4 + rad * math.sin(ang)))
    draw.polygon(pts, fill=col)
    f_top = get_font(13, bold=True)
    f_bot = get_font(11, bold=True)
    w_top = draw.textlength(dept_ko, font=f_top)
    w_bot = draw.textlength(sub_ko[:7], font=f_bot)
    draw_text_safe(draw, (cx - w_top * 0.5, cy - r + 11), dept_ko, fill=col, font_size=13, bold=True)
    draw_text_safe(draw, (cx - w_bot * 0.5, cy + 16), sub_ko[:7], fill=col, font_size=11, bold=True)


def _draw_pushpin(draw: ImageDraw.ImageDraw, cx: float, cy: float, color: tuple[int, int, int] = VOX_CRIMSON) -> None:
    cx, cy = int(cx), int(cy)
    draw.ellipse([cx + 3, cy + 3, cx + 19, cy + 19], fill=(12, 10, 8, 95))
    draw.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=color + (255,), outline=(30, 20, 15, 230), width=2)
    draw.ellipse([cx - 5, cy - 5, cx + 1, cy + 1], fill=(255, 255, 255, 175))


def paste_photo_polaroid(
    canvas: Image.Image,
    photo_img: Image.Image,
    center_xy: tuple[int, int],
    caption: str = "",
    angle_deg: float = 0.0,
    accent_badge: str = "",
) -> None:
    """Pastes an evidence photograph mounted on heavy cream card with optional rotation."""
    pw, ph = photo_img.size
    pad_side = 16
    pad_top = 16
    pad_bot = 48 if caption else 18
    cw, ch = pw + pad_side * 2, ph + pad_top + pad_bot

    card = Image.new("RGBA", (cw, ch), VOX_CREAM_CARD + (255,))
    cdraw = ImageDraw.Draw(card, "RGBA")
    cdraw.rectangle([0, 0, cw - 1, ch - 1], outline=(180, 170, 155, 255), width=1)
    card.paste(photo_img.convert("RGBA"), (pad_side, pad_top))

    if caption:
        f = get_font(15, bold=True)
        cdraw.text((pad_side + 4, ph + pad_top + 12), caption, font=f, fill=VOX_INK + (255,))
    if accent_badge:
        f_b = get_font(12, bold=True)
        bw = int(cdraw.textlength(accent_badge, font=f_b) + 16)
        cdraw.rectangle([cw - pad_side - bw, pad_top + 6, cw - pad_side, pad_top + 28], fill=VOX_CRIMSON + (235,))
        cdraw.text((cw - pad_side - bw + 8, pad_top + 9), accent_badge, font=f_b, fill=(255, 255, 255, 255))

    if abs(angle_deg) > 0.01:
        card = card.rotate(angle_deg, resample=Image.Resampling.BICUBIC, expand=True)

    cx, cy = center_xy
    bx = cx - card.width // 2
    by = cy - card.height // 2

    # Drop shadow
    shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow, "RGBA")
    sdraw.rectangle([6, 6, card.width - 6, card.height - 6], fill=(12, 10, 8, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))

    canvas.paste(shadow, (bx + 4, by + 4), shadow)
    canvas.paste(card, (bx, by), card)


def draw_vox_footage_lower_third(
    canvas: Image.Image,
    title_ko: str,
    sub_ko: str,
    wipe_p: float = 1.0,
    accent: tuple[int, int, int] = VOX_YELLOW,
) -> None:
    """Draws sleek tactile True Crime lower-third banner at the bottom of the frame."""
    if wipe_p <= 0.01:
        return
    p = ease_out_cubic(wipe_p)
    draw = ImageDraw.Draw(canvas, "RGBA")

    y0 = H - 188
    h_bar = 72
    w_target = 820
    w_curr = int(w_target * p)

    # Black semi-transparent banner
    draw.rectangle([48, y0, 48 + w_curr, y0 + h_bar], fill=(16, 20, 26, 225))
    # Accent stripe
    draw.rectangle([48, y0, 56, y0 + h_bar], fill=accent + (255,))

    if p > 0.35:
        text_p = min(1.0, (p - 0.35) / 0.65)
        alpha = int(255 * text_p)
        draw_text_safe(draw, (72, y0 + 10), title_ko, fill=(245, 248, 252, alpha), font_size=23, bold=True)
        draw_text_safe(draw, (72, y0 + 40), sub_ko, fill=(180, 195, 210, alpha), font_size=15, bold=True)


def draw_cinema_subtitle(
    canvas: Image.Image,
    subtitle_text: str,
    on_light_paper: bool = False,
) -> None:
    """Renders prominent, broadcast-grade subtitle typography with zero tofu."""
    if not subtitle_text or not subtitle_text.strip():
        return

    text = subtitle_text.strip()
    draw = ImageDraw.Draw(canvas, "RGBA")
    lines = split_balanced_korean(text, max_chars=34)

    if on_light_paper:
        # Dark protective badge on light paper backgrounds
        line_height = 42
        box_h = len(lines) * line_height + 24
        widths = [get_font(25, bold=True).getlength(l) for l in lines]
        box_w = int(max(widths) + 54)
        bx0 = (W - box_w) // 2
        by0 = H - box_h - 40

        draw.rounded_rectangle([bx0 + 3, by0 + 4, bx0 + box_w + 3, by0 + box_h + 4], radius=8, fill=(0, 0, 0, 110))
        draw.rounded_rectangle([bx0, by0, bx0 + box_w, by0 + box_h], radius=8, fill=(20, 18, 16, 240), outline=(50, 44, 38, 255), width=1)
        draw.rectangle([bx0 + 12, by0 + 12, bx0 + 16, by0 + box_h - 12], fill=VOX_CRIMSON + (255,))

        for i, line in enumerate(lines):
            ly = by0 + 14 + i * line_height
            draw_text_safe(draw, (bx0 + 32, ly), line, fill=(248, 246, 242, 255), font_size=25, bold=True)
    else:
        # White text with dual black stroke and soft drop shadow
        line_height = 48
        by0 = H - len(lines) * line_height - 52
        for i, line in enumerate(lines):
            cascade = get_font(32, bold=True)
            w = draw.textlength(line, font=cascade)
            lx = (W - w) / 2.0
            ly = by0 + i * line_height
            # Shadow
            draw_text_safe(draw, (lx + 2, ly + 2), line, fill=(0, 0, 0, 210), font_size=32, bold=True)
            # Double stroke
            draw_text_safe(draw, (lx, ly), line, fill=(255, 255, 255, 255), font_size=32, bold=True, stroke_width=4, stroke_fill=(12, 16, 22, 245))


# ==============================================================================
# SATELLITE MAP ARCHETYPES (#M1..#M8)
# ==============================================================================

def render_archetype_m1(seq_p: float, frame_store: Image.Image | None, frame_gao: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#M1: Urban Satellite Rooftop Loupe (Z14 Urban Sat + Z16 Rooftop Loupe)."""
    p = ease_in_out_cubic(seq_p)
    plate_img, meta = get_vox_styled_baiyin_urban_base(sat_weight=0.96)
    school_lon, school_lat = 104.148, 36.551
    cam_zoom = 1.0 + 0.35 * p
    canvas, cam_info = crop_map_camera(plate_img, meta, school_lon, school_lat, zoom_scale=cam_zoom)

    # Loupe magnifying Z16 campus rooftop
    plate_z16, meta_z16 = get_real_satellite_campus_z16()
    loupe_crop, _ = crop_map_camera(plate_z16, meta_z16, school_lon, school_lat, zoom_scale=1.45, out_size=(540, 540))

    loupe_mask = Image.new("L", (540, 540), 0)
    ImageDraw.Draw(loupe_mask).ellipse([0, 0, 540, 540], fill=255)
    loupe_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lx, ly = 1260, 240
    loupe_layer.paste(loupe_crop, (lx, ly), loupe_mask)

    draw_l = ImageDraw.Draw(loupe_layer, "RGBA")
    draw_l.ellipse([lx, ly, lx + 540, ly + 540], outline=(56, 189, 248, 255), width=5)
    draw_l.ellipse([lx + 12, ly + 12, lx + 528, ly + 528], outline=(239, 68, 68, 220), width=2)
    # Caliper crosshair
    draw_l.line([(lx + 270, ly + 40), (lx + 270, ly + 500)], fill=(56, 189, 248, 140), width=1)
    draw_l.line([(lx + 40, ly + 270), (lx + 500, ly + 270)], fill=(56, 189, 248, 140), width=1)

    canvas = Image.alpha_composite(canvas.convert("RGBA"), loupe_layer).convert("RGB")

    # Suspect photo
    gao_img = fit_crop(frame_gao or get_fallback_image(320, 380, "SUSPECT GAO"), 320, 380)
    paste_photo_polaroid(canvas, gao_img, (340, 480), caption="바이인 산업학교 매점 검거 현장", angle_deg=-1.5, accent_badge="특급체포")

    draw_satellite_hud_grid(canvas, coord_text_ko="Z16 루페 위성 정찰 · 바이인 공업학교 구내매점 옥상 특정", scale_label="250m")
    draw_vox_footage_lower_third(canvas, "초근접 위성 수색 정찰 (Z16 TACTICAL RECON)", "은신처 매점 옥상 좌표 특정 및 포위망 압축", wipe_p=1.0, accent=VOX_YELLOW)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_m2(seq_p: float, frame_city: Image.Image | None, frame_alley: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#M2: Orbital Regional Satellite Sweep (Z6 Gansu/Yellow River Orbital Sweep)."""
    p = ease_in_out_cubic(seq_p)
    plate_img, meta = get_vox_styled_gansu_base()
    center_lon, center_lat = 104.05, 36.35
    canvas, cam_info = crop_map_camera(plate_img, meta, center_lon, center_lat, zoom_scale=1.0 + 0.20 * p)

    # Dynamic GeoJSON boundary sweep
    draw = ImageDraw.Draw(canvas, "RGBA")
    gansu = load_gis_json("gansu_620000")
    for feat in gansu.get("features", []):
        draw_geojson_feature_on_plate(draw, feat, meta, fill_rgba=(56, 189, 248, 30), stroke_rgba=(56, 189, 248, 220), width=3, draw_progress=p)

    c1 = fit_crop(frame_city or get_fallback_image(420, 240, "LANZHOU HIGHWAY"), 420, 240)
    paste_photo_polaroid(canvas, c1, (1580, 360), caption="간쑤성 란저우-바이인 공업회랑", angle_deg=1.2, accent_badge="도주경로")

    draw_satellite_hud_grid(canvas, coord_text_ko="광역 궤도 위성 지형 스캔 · 간쑤성 황하 유역", scale_label="50km")
    draw_vox_footage_lower_third(canvas, "광역 궤도 지형 분석 (ORBITAL GIS CORRIDOR)", "황하 상류 협곡과 행정경계를 넘나든 120km 추적망", wipe_p=1.0, accent=VOX_TEAL)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_m3(seq_p: float, frame_detective: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#M3: Dual-Zone Radar & Yellow River Escape Vector (Z9 Corridor & Boundary)."""
    p = ease_out_cubic(seq_p)
    plate_img, meta = get_vox_styled_baiyin_lanzhou_base()
    canvas, cam_info = crop_map_camera(plate_img, meta, 104.14, 36.45, zoom_scale=1.15)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Coordinates
    bx, by = map_lonlat_to_screen(104.138, 36.545, meta, cam_info)
    qx, qy = map_lonlat_to_screen(104.152, 36.352, meta, cam_info)

    # Parabolic escape vector
    pts = []
    for s in range(36):
        t = s / 35.0
        cur_x = bx + (qx - bx) * t
        cur_y = by + (qy - by) * t - math.sin(t * math.pi) * 60
        pts.append((cur_x, cur_y))
    draw.line(pts, fill=VOX_CRIMSON + (235,), width=4, joint="curve")

    # Radar reticles
    for x, y, label in [(bx, by, "바이인 범행 지구"), (qx, qy, "칭청진 호적 은신처")]:
        draw.ellipse([x - 28, y - 28, x + 28, y + 28], outline=(239, 68, 68, 220), width=2)
        draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(239, 68, 68, 255))
        draw_text_safe(draw, (x + 36, y - 10), label, fill=(255, 255, 255, 240), font_size=18, bold=True)

    det_img = fit_crop(frame_detective or get_fallback_image(440, 280, "BORDER CONTROL"), 440, 280)
    paste_photo_polaroid(canvas, det_img, (1560, 420), caption="황하 협곡 경계 검문소 기록", angle_deg=-1.0, accent_badge="호적사각")

    draw_satellite_hud_grid(canvas, coord_text_ko="행정관할 경계 및 황하 도주 벡터 추적", scale_label="10km")
    draw_vox_footage_lower_third(canvas, "관할 사각지대 및 황하 도주로 (ESCAPE VECTOR)", "호적 등록지와 거주지가 분리된 수사망의 맹점", wipe_p=1.0, accent=VOX_CRIMSON)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_m4(seq_p: float, frame_c1: Image.Image | None, frame_c2: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#M4: Detective Cork Pinboard + Real Urban Satellite Crime Cluster."""
    canvas = get_cork_pinboard_shell()
    plate_img, meta = get_vox_styled_baiyin_urban_base(sat_weight=0.92)
    sat_map, cam_info = crop_map_camera(plate_img, meta, 104.142, 36.548, zoom_scale=1.12, out_size=(1160, 780))

    # Paste satellite map onto cork board with drop shadow
    map_layer = Image.new("RGBA", (1160, 780), (0, 0, 0, 0))
    map_layer.paste(sat_map)
    mdraw = ImageDraw.Draw(map_layer, "RGBA")
    mdraw.rectangle([0, 0, 1159, 779], outline=(20, 16, 12, 220), width=3)
    canvas.paste(map_layer, (120, 150))

    draw = ImageDraw.Draw(canvas, "RGBA")
    # Red string links between crime scenes
    crime_pins = [
        (320, 280, "1988 융펑가"),
        (640, 360, "1994 전력국"),
        (820, 520, "1998 4연속 범행"),
        (960, 680, "2016 검거 매점"),
    ]
    for i in range(len(crime_pins) - 1):
        x1, y1, _ = crime_pins[i]
        x2, y2, _ = crime_pins[i + 1]
        draw.line([(x1, y1), (x2, y2)], fill=(220, 38, 38, 225), width=3)

    for x, y, lbl in crime_pins:
        _draw_pushpin(draw, x, y, color=VOX_CRIMSON)
        draw_text_safe(draw, (x + 14, y - 8), lbl, fill=(255, 255, 255, 240), font_size=15, bold=True)

    p1 = fit_crop(frame_c1 or get_fallback_image(420, 260, "CRIME SCENE #1"), 420, 260)
    p2 = fit_crop(frame_c2 or get_fallback_image(420, 260, "CRIME SCENE #2"), 420, 260)
    paste_photo_polaroid(canvas, p1, (1560, 320), caption="1998년 집중 발생 지구", angle_deg=1.8, accent_badge="연쇄단서")
    paste_photo_polaroid(canvas, p2, (1560, 680), caption="범인 이동 반경 분석표", angle_deg=-1.5, accent_badge="프로파일링")

    draw_vox_footage_lower_third(canvas, "연쇄 강력범죄 분포 핀보드 (CRIME CLUSTER)", "1988~2002 바이인 도심 붉은 실 연결망", wipe_p=1.0, accent=VOX_CRIMSON)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_m5(seq_p: float, frame_a: Image.Image | None, frame_b: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#M5: 2.5D Perspective Tilted Satellite Slab + 3D Elevation Beacons."""
    canvas = Image.new("RGB", (W, H), (11, 15, 22))
    draw = ImageDraw.Draw(canvas, "RGBA")
    for gy in range(0, H, 40):
        draw.line([(0, gy), (W, gy)], fill=(30, 41, 59, 65), width=1)
    for gx in range(0, W, 60):
        draw.line([(gx, 0), (gx, H)], fill=(30, 41, 59, 45), width=1)

    plate_img, meta = get_vox_styled_baiyin_urban_base(sat_weight=0.96)
    sat_crop, _ = crop_map_camera(plate_img, meta, 104.142, 36.548, zoom_scale=1.22)

    slab_w, slab_h = 1280, 620
    slab_x0, slab_y0 = 76, 260
    sat_src = sat_crop.resize((slab_w, slab_h), Image.Resampling.BILINEAR)
    sat_arr = np.array(sat_src)

    top_indent = 135
    poly_top = [
        (slab_x0 + top_indent, slab_y0),
        (slab_x0 + slab_w - top_indent, slab_y0),
        (slab_x0 + slab_w, slab_y0 + slab_h),
        (slab_x0, slab_y0 + slab_h),
    ]

    # Warp scanlines into trapezoid
    warped = np.zeros((H, W, 4), dtype=np.uint8)
    for row in range(slab_h):
        v = row / float(slab_h - 1)
        x_left = int(slab_x0 + top_indent * (1.0 - v))
        x_right = int(slab_x0 + slab_w - top_indent * (1.0 - v))
        cur_w = max(2, x_right - x_left)
        row_img = Image.fromarray(sat_arr[row : row + 1, :, :]).resize((cur_w, 1), Image.Resampling.BILINEAR)
        warped[slab_y0 + row, x_left : x_left + cur_w, :3] = np.array(row_img)[0]
        warped[slab_y0 + row, x_left : x_left + cur_w, 3] = 255

    canvas = Image.alpha_composite(canvas.convert("RGBA"), Image.fromarray(warped, "RGBA")).convert("RGB")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.polygon(poly_top, outline=(56, 189, 248, 230), width=3)

    beacons = [
        (395, 655, 185, "제1차 융펑가 현장 (1988)", "최초 지문·DNA 확보", (250, 204, 21)),
        (695, 520, 215, "바이인 전력국 숙소 (1994)", "6년 공백 후 재출현", (239, 68, 68)),
        (985, 595, 195, "공업학교 매점 (2016)", "28년 만의 최종 검거", (56, 189, 248)),
    ]

    for bx, by, bh, b_title, b_sub, b_col in beacons:
        draw.ellipse([bx - 36, by - 16, bx + 36, by + 16], outline=b_col + (235,), width=3)
        top_y = by - bh
        draw.line([(bx, by), (bx, top_y)], fill=b_col + (245,), width=4)
        draw.ellipse([bx - 8, top_y - 8, bx + 8, top_y + 8], fill=(255, 255, 255, 255), outline=b_col + (255,), width=3)
        # Floating callout
        cw_b = int(max(draw.textlength(b_title, font=get_font(18, bold=True)), draw.textlength(b_sub, font=get_font(14, bold=True))) + 28)
        cx0, cy0 = bx - cw_b // 2, top_y - 68
        draw.rounded_rectangle([cx0, cy0, cx0 + cw_b, cy0 + 58], radius=6, fill=(15, 23, 34, 242), outline=b_col + (235,), width=2)
        draw_text_safe(draw, (cx0 + 14, cy0 + 6), b_title, fill=b_col + (255,), font_size=18, bold=True)
        draw_text_safe(draw, (cx0 + 14, cy0 + 32), b_sub, fill=(241, 245, 249, 245), font_size=14, bold=True)

    p1 = fit_crop(frame_a or get_fallback_image(420, 240, "ELEVATION 01"), 420, 240)
    p2 = fit_crop(frame_b or get_fallback_image(420, 240, "ELEVATION 02"), 420, 240)
    paste_photo_polaroid(canvas, p1, (1615, 330), caption="2.5D 위성 궤적 #01 · 숙소 밀집구역", angle_deg=-1.0, accent_badge="위성A")
    paste_photo_polaroid(canvas, p2, (1615, 695), caption="2.5D 위성 궤적 #02 · 매점 은신처", angle_deg=1.0, accent_badge="위성B")

    draw_satellite_hud_grid(canvas, coord_text_ko="2.5D 입체 위성 지형 프로파일링 · 고도 분석", scale_label="500m")
    draw_vox_footage_lower_third(canvas, "2.5D 입체 위성 지리 프로파일링 (GEO-PROFILING)", "1988~2016 주요 범행 좌표와 검거 지점의 3차원 동선", wipe_p=1.0, accent=VOX_YELLOW)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_m6(seq_p: float, frame_a: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#M6: Split-Screen Dual Satellite Comparison (Macro Z9 vs. Micro Z16)."""
    plate_l, meta_l = get_vox_styled_baiyin_lanzhou_base()
    crop_l, _ = crop_map_camera(plate_l, meta_l, 104.15, 36.46, zoom_scale=1.25)
    left_half = crop_l.crop((480, 0, 480 + W // 2, H))

    plate_r, meta_r = get_real_satellite_campus_z16()
    crop_r, _ = crop_map_camera(plate_r, meta_r, 104.148, 36.551, zoom_scale=1.15)
    right_half = crop_r.crop((480, 0, 480 + W // 2, H))

    canvas = Image.new("RGB", (W, H))
    canvas.paste(left_half, (0, 0))
    canvas.paste(right_half, (W // 2, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Amber divider line
    draw.line([(W // 2, 0), (W // 2, H)], fill=(245, 158, 11, 255), width=4)

    # 16x zoom-in bridge badge
    draw.rounded_rectangle([W // 2 - 120, 60, W // 2 + 120, 110], radius=8, fill=(15, 23, 42, 245), outline=(245, 158, 11, 255), width=2)
    draw_text_safe(draw, (W // 2 - 96, 72), "16× OPTICAL ZOOM ▶", fill=(245, 158, 11, 255), font_size=18, bold=True)

    draw_text_safe(draw, (48, 48), "[MACRO Z9] 황하 공업벨트 광역 수색구역", fill=(255, 255, 255, 240), font_size=20, bold=True)
    draw_text_safe(draw, (W // 2 + 48, 48), "[MICRO Z16] 학교 구내매점 옥상 타겟 특정", fill=(56, 189, 248, 255), font_size=20, bold=True)

    draw_vox_footage_lower_third(canvas, "광역-정밀 이중 위성 대조 (SPLIT DUAL SAT)", "도시 전체에서 단 하나의 건물 옥상으로 압축된 수사망", wipe_p=1.0, accent=VOX_YELLOW)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_m7(seq_p: float, frame_a: Image.Image | None, frame_b: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#M7: Night-Ops Thermal/Infrared Satellite Lockdown Grid."""
    plate_img, meta = get_vox_styled_baiyin_urban_base(sat_weight=0.96)
    sat_crop, _ = crop_map_camera(plate_img, meta, 104.142, 36.548, zoom_scale=1.20)
    canvas = apply_infrared_thermal_shader(sat_crop)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # 3km perimeter crimson circle
    cx, cy = W // 2, H // 2
    r_perim = 340
    draw.ellipse([cx - r_perim, cy - r_perim, cx + r_perim, cy + r_perim], outline=(239, 68, 68, 240), width=4)
    draw.ellipse([cx - r_perim - 6, cy - r_perim - 6, cx + r_perim + 6, cy + r_perim + 6], outline=(239, 68, 68, 110), width=2)

    # 4 Checkpoints
    checkpoints = [
        (cx - 240, cy - 140, "제1검문소"),
        (cx + 220, cy - 160, "제2검문소"),
        (cx + 200, cy + 180, "제3검문소"),
        (cx - 220, cy + 190, "제4검문소"),
    ]
    for x, y, name in checkpoints:
        draw.ellipse([x - 12, y - 12, x + 12, y + 12], fill=(239, 68, 68, 255), outline=(255, 255, 255, 255), width=2)
        draw_text_safe(draw, (x + 18, y - 8), name, fill=(245, 248, 252, 245), font_size=16, bold=True)

    draw_satellite_hud_grid(canvas, coord_text_ko="적외선 야간 작전 그리드 · 도심 반경 3km 통제", scale_label="1km", accent_rgb=(239, 68, 68))
    draw_vox_footage_lower_third(canvas, "야간 통제 적외선 위성 그리드 (INFRARED CURFEW)", "해 질 녘 시작된 도심 봉쇄와 검문소 24시간 감시망", wipe_p=1.0, accent=VOX_CRIMSON)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_m8(seq_p: float, frame_route: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#M8: Topographic Elevation Profile & Interstate Highway Corridor."""
    plate_img, meta = get_vox_styled_gansu_base()
    canvas, cam_info = crop_map_camera(plate_img, meta, 103.95, 36.20, zoom_scale=1.10)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Bottom Elevation Profile Graph Slab (3D cross-section)
    gx0, gy0, gx1, gy1 = 120, H - 360, W - 120, H - 140
    draw.rounded_rectangle([gx0, gy0, gx1, gy1], radius=8, fill=(15, 23, 42, 235), outline=(56, 189, 248, 180), width=2)
    draw_text_safe(draw, (gx0 + 24, gy0 + 16), "고도 단면 프로파일 (ELEVATION PROFILE: 1,520m ~ 2,180m ASL)", fill=(56, 189, 248, 255), font_size=18, bold=True)

    # Elevation wave
    pts = []
    w_span = gx1 - gx0 - 60
    for s in range(50):
        t = s / 49.0
        px = gx0 + 30 + t * w_span
        py = gy1 - 30 - math.sin(t * math.pi * 2.2) * 55 - (t * 40)
        pts.append((px, py))
    draw.line(pts, fill=(234, 179, 8, 245), width=3)
    # Area fill under curve
    poly_pts = [(gx0 + 30, gy1 - 20)] + pts + [(gx1 - 30, gy1 - 20)]
    draw.polygon(poly_pts, fill=(234, 179, 8, 45))

    draw_satellite_hud_grid(canvas, coord_text_ko="산악 지형 등고선 및 성간 고속도로 추적", scale_label="20km")
    draw_vox_footage_lower_third(canvas, "지형 등고선 및 탈출 고도 프로파일 (TOPOGRAPHIC PROFILE)", "해발 2,000m 협곡과 험준한 산악을 통과한 도주로", wipe_p=1.0, accent=VOX_YELLOW)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


# ==============================================================================
# FORENSIC DOSSIER ARCHETYPES (#D1..#D10)
# ==============================================================================

def render_archetype_d1(seq_p: float, frame_a: Image.Image | None, frame_b: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#D1: Layered Manila Police Case Folder & AFIS Fingerprint Paradox."""
    canvas = get_dark_investigation_desk()
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Manila Folder
    fx0, fy0, fx1, fy1 = 48, 54, W - 48, H - 42
    draw.rounded_rectangle([fx0 + 8, fy0 + 10, fx1 + 8, fy1 + 10], radius=14, fill=(8, 6, 5, 165))
    draw.rounded_rectangle([fx0, fy0, fx1, fy1], radius=14, fill=VOX_MANILA + (255,), outline=(142, 120, 88, 255), width=2)
    # Tab
    draw.rounded_rectangle([84, 16, 780, 60], radius=10, fill=VOX_MANILA + (255,), outline=(142, 120, 88, 255), width=2)
    draw_text_safe(draw, (110, 24), "사건기록철 #8·05專案 · 바이인시 공안국", fill=VOX_INK + (255,), font_size=20, bold=True)

    _draw_brass_fastener(draw, W // 2, 72)
    _draw_circular_official_seal(draw, W - 220, 160)

    # AFIS counter card
    draw.rounded_rectangle([120, 140, 520, 240], radius=8, fill=VOX_MEMO_YELLOW + (255,), outline=(180, 150, 90, 255), width=2)
    draw_text_safe(draw, (140, 155), "AFIS 지문 대조 데이터베이스", fill=VOX_INK_MUTED + (255,), font_size=16, bold=True)
    draw_text_safe(draw, (140, 185), "230,000건 대조 불일치", fill=VOX_CRIMSON + (255,), font_size=28, bold=True)
    _draw_paperclip(draw, 140, 124)

    # Photos
    p1 = fit_crop(frame_a or get_fallback_image(460, 360, "LATENT PRINT"), 460, 360)
    p2 = fit_crop(frame_b or get_fallback_image(460, 360, "FINGERPRINT ARCHIVE"), 460, 360)
    paste_photo_polaroid(canvas, p1, (780, 560), caption="현장 감식 채취 지문 원본", angle_deg=-1.2, accent_badge="증거#01")
    paste_photo_polaroid(canvas, p2, (1360, 560), caption="수사 지문 카드 전수 대조", angle_deg=1.5, accent_badge="전수조사")

    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=True)
    return canvas


def render_archetype_d2(seq_p: float, frame_left: Image.Image | None, frame_right: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#D2: Twin Angled Personnel ID Card vs. Black Interrogation Record."""
    canvas = get_dark_investigation_desk()

    # Left board: Normal citizen ID
    card_l = get_torn_paper_sheet(680, 780, fill_rgb=VOX_CREAM_CARD, seed=22)
    cdraw_l = ImageDraw.Draw(card_l, "RGBA")
    draw_text_safe(cdraw_l, (48, 48), "호적 및 주민등록 조사카드", fill=VOX_INK + (255,), font_size=24, bold=True)
    draw_text_safe(cdraw_l, (48, 86), "신분: 평범한 구내매점 운영자 / 두 아들의 가장", fill=VOX_INK_MUTED + (255,), font_size=17, bold=True)
    p_left = fit_crop(frame_left or get_fallback_image(560, 420, "CITIZEN DISGUISE"), 560, 420)
    card_l.paste(p_left, (48, 140))
    canvas.paste(card_l, (180, 140), card_l)

    # Right board: Interrogation record
    card_r = Image.new("RGBA", (680, 780), (22, 20, 18, 255))
    cdraw_r = ImageDraw.Draw(card_r, "RGBA")
    cdraw_r.rectangle([0, 0, 679, 779], outline=(176, 30, 26, 220), width=4)
    draw_text_safe(cdraw_r, (48, 48), "공안국 비밀 취조 심문록 [극비]", fill=VOX_CRIMSON + (255,), font_size=24, bold=True)
    draw_text_safe(cdraw_r, (48, 86), "진술: 11건 연쇄 강력 범행 자필 시인", fill=(220, 225, 230, 245), font_size=17, bold=True)
    p_right = fit_crop(frame_right or get_fallback_image(560, 420, "INTERROGATION"), 560, 420)
    card_r.paste(p_right, (48, 140))
    _draw_circular_official_seal(cdraw_r, 580, 680, r=42)
    canvas.paste(card_r, (1040, 140), card_r)

    draw_vox_footage_lower_third(canvas, "이중생활과 가면의 분열 (DUALITY DOSSIER)", "28년 동안 이웃을 속인 평범한 매점 주인의 두 얼굴", wipe_p=1.0, accent=VOX_CRIMSON)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_d3(seq_p: float, frame_fp: Image.Image | None, frame_bio: Image.Image | None, frame_foot: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#D3: Forensic Lightbox & 35mm Film Strip + 3 Sealed Evidence Bags."""
    canvas = get_dark_investigation_desk()
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Light table
    draw.rounded_rectangle([80, 100, W - 80, H - 120], radius=12, fill=(240, 248, 255, 240), outline=(120, 150, 180, 255), width=3)
    # Millimeter grid
    for gx in range(120, W - 80, 60):
        draw.line([(gx, 120), (gx, H - 140)], fill=(180, 210, 235, 120), width=1)
    for gy in range(140, H - 120, 60):
        draw.line([(100, gy), (W - 100, gy)], fill=(180, 210, 235, 120), width=1)

    p_fp = fit_crop(frame_fp or get_fallback_image(460, 320, "LATENT PRINTS"), 460, 320)
    p_bio = fit_crop(frame_bio or get_fallback_image(460, 320, "DNA SAMPLE"), 460, 320)
    p_foot = fit_crop(frame_foot or get_fallback_image(460, 320, "FOOTPRINT IMPRESSION"), 460, 320)

    paste_photo_polaroid(canvas, p_fp, (360, 480), caption="단서 1: 현장 잠재 지문", angle_deg=-1.5, accent_badge="지문")
    paste_photo_polaroid(canvas, p_bio, (960, 480), caption="단서 2: 생체 DNA 시료", angle_deg=0.5, accent_badge="DNA")
    paste_photo_polaroid(canvas, p_foot, (1560, 480), caption="단서 3: 군화 족적 흔적", angle_deg=1.8, accent_badge="족적")

    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=True)
    return canvas


def render_archetype_d4(seq_p: float, frame_lab: Image.Image | None, frame_arrest: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#D4: Forensic Medical Lightbox — Y-STR DNA Gel & Pedigree Family Tree."""
    canvas = Image.new("RGB", (W, H), (14, 20, 28))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Backlit lightbox surface
    draw.rounded_rectangle([72, 72, W - 72, H - 90], radius=14, fill=(18, 28, 42, 255), outline=(56, 189, 248, 220), width=3)

    # Left panel: Y-STR Electrophoresis gel
    draw.rounded_rectangle([110, 110, 780, H - 130], radius=8, fill=(10, 16, 24, 255), outline=(56, 189, 248, 140), width=2)
    draw_text_safe(draw, (130, 130), "Y-STR 염색체 전기영동 젤 분석 [10개 Loci]", fill=(56, 189, 248, 255), font_size=20, bold=True)

    loci = ["DYS19", "DYS389I", "DYS389II", "DYS390", "DYS391", "DYS392", "DYS393", "DYS438", "DYS439", "DYS456"]
    for i, loc in enumerate(loci):
        ly = 180 + i * 48
        draw_text_safe(draw, (140, ly), loc, fill=(148, 163, 184, 255), font_size=15, bold=True)
        # Gel band
        draw.rounded_rectangle([260, ly + 2, 480, ly + 18], radius=3, fill=(15, 23, 42, 255))
        draw.rounded_rectangle([320, ly + 4, 380, ly + 16], radius=2, fill=(34, 211, 238, 235))
        draw.rounded_rectangle([520, ly + 2, 740, ly + 18], radius=3, fill=(15, 23, 42, 255))
        draw.rounded_rectangle([580, ly + 4, 640, ly + 16], radius=2, fill=(239, 68, 68, 235))

    # Right panel: Gao Pedigree family tree
    tree_x = 840
    draw.rounded_rectangle([tree_x, 110, W - 110, H - 130], radius=8, fill=(10, 16, 24, 255), outline=(56, 189, 248, 140), width=2)
    draw_text_safe(draw, (tree_x + 24, 130), "칭청진 가오씨 가문 부계 족보 계통도", fill=(245, 158, 11, 255), font_size=20, bold=True)

    # Pedigree nodes
    nodes = [
        (tree_x + 460, 220, "시조 가오씨"),
        (tree_x + 320, 320, "칭청 분파 1"),
        (tree_x + 600, 320, "칭청 분파 2"),
        (tree_x + 320, 440, "가오청융 부친"),
        (tree_x + 320, 560, "용의자 가오청융 [일치]"),
    ]
    for x, y, lbl in nodes:
        col = (239, 68, 68) if "일치" in lbl else (56, 189, 248)
        draw.rounded_rectangle([x - 110, y - 20, x + 110, y + 20], radius=6, fill=(15, 23, 42, 255), outline=col + (235,), width=2)
        draw_text_safe(draw, (x - 90, y - 10), lbl, fill=(255, 255, 255, 245), font_size=15, bold=True)

    draw_vox_footage_lower_third(canvas, "Y-STR 유전자 계통도 감식 (Y-STR DNA PEDIGREE)", "단 하나의 남성 염색체 표지가 특정 가문의 족보를 정조준", wipe_p=1.0, accent=(34, 211, 238))
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_d5(seq_p: float, frame_interrog: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#D5: Brushed Aluminum Clipboard Q&A + Audio Voiceprint Waveform."""
    canvas = get_dark_investigation_desk()

    # Brushed aluminum clipboard
    clip_w, clip_h = 920, 840
    rng = np.random.default_rng(55)
    noise = rng.normal(0, 4.0, (clip_h // 4, clip_w // 4, 3))
    arr = np.clip(np.array([170, 175, 180], dtype=np.float32) + noise, 0, 255).astype(np.uint8)
    board = Image.fromarray(arr, "RGB").resize((clip_w, clip_h), Image.Resampling.BICUBIC)
    bdraw = ImageDraw.Draw(board, "RGBA")
    bdraw.rectangle([0, 0, clip_w - 1, clip_h - 1], outline=(100, 105, 110, 255), width=3)
    # Lined sheet inside
    pad = 32
    bdraw.rectangle([pad, pad + 40, clip_w - pad, clip_h - pad], fill=VOX_CREAM_CARD + (255,), outline=(140, 130, 120, 255), width=1)
    # Clipboard clip
    _draw_brass_fastener(bdraw, clip_w // 2, 28)

    draw_text_safe(bdraw, (pad + 24, pad + 60), "피의자 신문조서 (진술 녹취)", fill=VOX_CRIMSON + (255,), font_size=24, bold=True)
    draw_text_safe(bdraw, (pad + 24, pad + 110), "문: 1988년 융펑가 첫 사건을 기억합니까?", fill=VOX_INK + (255,), font_size=18, bold=True)
    draw_text_safe(bdraw, (pad + 24, pad + 145), "답: 기억합니다. 전부 내가 한 일입니다.", fill=VOX_CRIMSON + (255,), font_size=19, bold=True)
    draw_text_safe(bdraw, (pad + 24, pad + 195), "문: 왜 28년 동안 입을 열지 않았습니까?", fill=VOX_INK + (255,), font_size=18, bold=True)
    draw_text_safe(bdraw, (pad + 24, pad + 230), "답: 때가 되면 잡힐 줄 알고 있었습니다.", fill=VOX_INK + (255,), font_size=18, bold=True)
    _draw_circular_official_seal(bdraw, clip_w - 160, clip_h - 140)

    canvas.paste(board, (80, 120))

    # Right side: Interrogation frame + Voiceprint
    it_img = fit_crop(frame_interrog or get_fallback_image(780, 440, "INTERROGATION ROOM"), 780, 440)
    canvas.paste(it_img, (1060, 160))

    # Voiceprint oscilloscope card
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle([1060, 640, W - 80, H - 120], radius=8, fill=(15, 23, 42, 245), outline=(56, 189, 248, 200), width=2)
    draw_text_safe(draw, (1084, 656), "VOICEPRINT OSCILLOSCOPE · 음성 주파수 지문", fill=(56, 189, 248, 255), font_size=18, bold=True)
    for bx in range(1090, W - 100, 14):
        bh = int(15 + math.sin(bx * 0.08) * 35 + math.cos(bx * 0.15) * 20)
        draw.line([(bx, 760 - bh), (bx, 760 + bh)], fill=(34, 211, 238, 230), width=4)

    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_d6(seq_p: float, frame_sketch: Image.Image | None, frame_real: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#D6: Class-A Red Wanted Warrant & Composite Sketch Evolution Grid."""
    canvas = get_dark_investigation_desk()
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Aged Wanted Warrant Sheet
    sheet = get_torn_paper_sheet(1120, 860, fill_rgb=(238, 228, 210), seed=47)
    sdraw = ImageDraw.Draw(sheet, "RGBA")
    sdraw.rectangle([24, 24, 1120 - 24, 860 - 24], outline=VOX_CRIMSON + (255,), width=6)
    sdraw.rectangle([34, 34, 1120 - 34, 860 - 34], outline=VOX_CRIMSON + (180,), width=2)

    draw_text_safe(sdraw, (1120 // 2 - 240, 54), "중화인민공화국 공안부 A급 특별수배령", fill=VOX_CRIMSON + (255,), font_size=28, bold=True)
    draw_text_safe(sdraw, (1120 // 2 - 140, 96), "[공안부 공고 2004 제8호 · 현상금 20만 위안]", fill=VOX_INK + (255,), font_size=17, bold=True)

    sk_img = fit_crop(frame_sketch or get_fallback_image(420, 500, "COMPOSITE SKETCH"), 420, 500)
    sheet.paste(sk_img, (80, 160))
    sdraw.text((80, 680), "2004 목격자 진술 몽타주", font=get_font(18, bold=True), fill=VOX_INK + (255,))

    rl_img = fit_crop(frame_real or get_fallback_image(420, 500, "2016 ARREST MUGSHOT"), 420, 500)
    sheet.paste(rl_img, (580, 160))
    sdraw.text((580, 680), "2016 검거 당시 실제 인상착의", font=get_font(18, bold=True), fill=VOX_CRIMSON + (255,))

    _draw_circular_official_seal(sdraw, 1120 - 180, 860 - 180, r=54)
    canvas.paste(sheet, (W // 2 - sheet.width // 2, 70), sheet)

    draw_vox_footage_lower_third(canvas, "공안부 A급 지명수배령 (CLASS-A WANTED WARRANT)", "20만 위안 현상금과 12년 간격의 몽타주-실제 인물 대조", wipe_p=1.0, accent=VOX_CRIMSON)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_d7(seq_p: float, frame_tool: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#D7: Ballistics & Toolmark Comparator."""
    canvas = Image.new("RGB", (W, H), (18, 22, 28))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Split comparator circle
    cx, cy, r = W // 2, H // 2, 380
    draw.ellipse([cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8], outline=(100, 116, 139, 255), width=8)

    t_img = fit_crop(frame_tool or get_fallback_image(r * 2, r * 2, "TOOLMARK STRIATION"), r * 2, r * 2)
    mask = Image.new("L", (r * 2, r * 2), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, r * 2, r * 2], fill=255)
    canvas.paste(t_img, (cx - r, cy - r), mask)

    draw.line([(cx, cy - r), (cx, cy + r)], fill=(245, 158, 11, 255), width=3)
    draw_text_safe(draw, (cx - 260, cy - 320), "[현장 절단 흔적]", fill=(245, 158, 11, 255), font_size=20, bold=True)
    draw_text_safe(draw, (cx + 80, cy - 320), "[압수 흉기 미세조흔 일치]", fill=(56, 189, 248, 255), font_size=20, bold=True)

    draw_vox_footage_lower_third(canvas, "미세조흔 공구흔 비교감식 (TOOLMARK COMPARATOR)", "현장 절단면과 압수 도구의 미세 조흔선 광학 일치", wipe_p=1.0, accent=VOX_YELLOW)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_d8(seq_p: float, frame_autopsy: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#D8: Forensic Autopsy Pathology Protocol & Anatomical Silhouette Diagram."""
    canvas = get_dark_investigation_desk()
    sheet = get_torn_paper_sheet(1240, 860, fill_rgb=VOX_CREAM_CARD, seed=88)
    sdraw = ImageDraw.Draw(sheet, "RGBA")

    draw_text_safe(sdraw, (64, 48), "법의학 검시 프로토콜 및 부검 감정서", fill=VOX_INK + (255,), font_size=26, bold=True)
    draw_text_safe(sdraw, (64, 88), "사망원인: 과다출혈 및 경부 압박 질식사 (방어흔 다수 발견)", fill=VOX_CRIMSON + (255,), font_size=18, bold=True)

    # Human silhouette schematic
    bx, by = 260, 460
    sdraw.ellipse([bx - 30, by - 240, bx + 30, by - 180], fill=(70, 75, 82, 255))
    sdraw.rectangle([bx - 45, by - 170, bx + 45, by + 40], fill=(70, 75, 82, 255))
    sdraw.rectangle([bx - 40, by + 40, bx - 10, by + 240], fill=(70, 75, 82, 255))
    sdraw.rectangle([bx + 10, by + 40, bx + 40, by + 240], fill=(70, 75, 82, 255))

    # Trauma pointers
    for ty, txt in [(by - 160, "경부 손상점 #1"), (by - 60, "흉부 방어흔 #2"), (by + 20, "완관절 결박흔 #3")]:
        sdraw.line([(bx + 20, ty), (bx + 140, ty)], fill=VOX_CRIMSON + (255,), width=2)
        sdraw.ellipse([bx + 16, ty - 4, bx + 24, ty + 4], fill=VOX_CRIMSON + (255,))
        draw_text_safe(sdraw, (bx + 150, ty - 8), txt, fill=VOX_CRIMSON + (255,), font_size=16, bold=True)

    at_img = fit_crop(frame_autopsy or get_fallback_image(480, 460, "PATHOLOGY LAB REPORT"), 480, 460)
    sheet.paste(at_img, (660, 160))
    _draw_circular_official_seal(sdraw, 1100, 740, r=50)

    canvas.paste(sheet, (W // 2 - sheet.width // 2, 70), sheet)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=True)
    return canvas


def render_archetype_d9(seq_p: float, frame_fp1: Image.Image | None, frame_fp2: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#D9: Dual-Ocular Microscope Minutiae Comparison View (14-Point AFIS Comparator)."""
    canvas = Image.new("RGB", (W, H), (10, 12, 16))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Twin circular ocular viewports
    r = 310
    c1_x, c1_y = 520, H // 2
    c2_x, c2_y = 1400, H // 2

    for cx in (c1_x, c2_x):
        draw.ellipse([cx - r - 10, c1_y - r - 10, cx + r + 10, c1_y + r + 10], outline=(71, 85, 105, 255), width=10)
        draw.ellipse([cx - r - 2, c1_y - r - 2, cx + r + 2, c1_y + r + 2], outline=(56, 189, 248, 200), width=3)

    img1 = fit_crop(frame_fp1 or get_fallback_image(r * 2, r * 2, "1988 LATENT PRINT"), r * 2, r * 2)
    img2 = fit_crop(frame_fp2 or get_fallback_image(r * 2, r * 2, "2016 INKED PRINT"), r * 2, r * 2)

    mask = Image.new("L", (r * 2, r * 2), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, r * 2, r * 2], fill=255)
    canvas.paste(img1, (c1_x - r, c1_y - r), mask)
    canvas.paste(img2, (c2_x - r, c2_y - r), mask)

    # 14 Minutiae lines linking oculars
    draw_lines = ImageDraw.Draw(canvas, "RGBA")
    for i in range(14):
        y_offset = (i - 7) * 36
        draw_lines.line([(c1_x + r - 20, c1_y + y_offset), (c2_x - r + 20, c2_y + y_offset)], fill=(239, 68, 68, 220), width=2)

    # Central match confirmation plaque
    draw.rounded_rectangle([W // 2 - 130, H // 2 - 40, W // 2 + 130, H // 2 + 40], radius=8, fill=(15, 23, 42, 245), outline=(34, 197, 94, 255), width=3)
    draw_text_safe(draw, (W // 2 - 110, H // 2 - 24), "14 / 14 (100.0% MATCH)", fill=(34, 197, 94, 255), font_size=18, bold=True)
    draw_text_safe(draw, (c1_x - 140, c1_y + r + 24), "1988 사건현장 잠재 지문", fill=(255, 255, 255, 240), font_size=18, bold=True)
    draw_text_safe(draw, (c2_x - 140, c2_y + r + 24), "2016 가오청융 압날 지문", fill=(56, 189, 248, 255), font_size=18, bold=True)

    draw_vox_footage_lower_third(canvas, "광학 융선 특징점 비교감식 (14-POINT AFIS COMPARATOR)", "28년 만에 지문 14개 특징점 완전 일치 확정", wipe_p=1.0, accent=(34, 197, 94))
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_d10(seq_p: float, frame_vault: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#D10: Cold Case Archive Vault Box & Physical Manila Drawer."""
    canvas = Image.new("RGB", (W, H), (24, 26, 30))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Metal cabinet drawer texture
    for y in range(0, H, 140):
        draw.rectangle([60, y, W - 60, y + 130], fill=(36, 40, 46), outline=(60, 66, 76), width=2)
        # Metal drawer handle
        draw.rectangle([W // 2 - 120, y + 45, W // 2 + 120, y + 85], fill=(120, 130, 140), outline=(180, 190, 200), width=2)

    # Manila drawer pulled out
    sheet = get_torn_paper_sheet(920, 520, fill_rgb=VOX_MANILA, seed=61)
    sdraw = ImageDraw.Draw(sheet, "RGBA")
    draw_text_safe(sdraw, (48, 48), "간쑤성 바이인 미제사건 특별보존서고 [1988-2016]", fill=VOX_INK + (255,), font_size=24, bold=True)
    for i, yr in enumerate(["1988 융펑가", "1994 전력국", "1998 4건", "2002 미제종결"]):
        sdraw.rectangle([48 + i * 200, 120, 228 + i * 200, 160], fill=VOX_PAPER_DARK, outline=VOX_INK_MUTED, width=1)
        draw_text_safe(sdraw, (64 + i * 200, 130), yr, fill=VOX_INK, font_size=16, bold=True)

    vt_img = fit_crop(frame_vault or get_fallback_image(480, 260, "COLD CASE ARCHIVE BOX"), 480, 260)
    sheet.paste(vt_img, (48, 200))
    _draw_circular_official_seal(sdraw, 800, 400, r=46)

    canvas.paste(sheet, (W // 2 - sheet.width // 2, 280), sheet)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


# ==============================================================================
# PRESS, CURFEW & BROADCAST ARCHETYPES (#P1..#P6)
# ==============================================================================

def render_archetype_p1(seq_p: float, frame_1988: Image.Image | None, frame_1994: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#P1: Archival Broadsheet Newspaper + 6-Year Gap Timeline."""
    canvas = get_dark_investigation_desk()

    # Broadsheet
    paper = get_torn_paper_sheet(1320, 880, fill_rgb=VOX_NEWSPRINT, seed=12)
    pdraw = ImageDraw.Draw(paper, "RGBA")
    # Masthead
    pdraw.line([(40, 90), (1280, 90)], fill=VOX_INK, width=3)
    pdraw.line([(40, 96), (1280, 96)], fill=VOX_INK, width=1)
    draw_text_safe(pdraw, (48, 44), "백은일보 (白銀日報) · 특별호외", fill=VOX_INK, font_size=32, bold=True)
    draw_text_safe(pdraw, (1080, 60), "1994년 10월 28일", fill=VOX_INK_MUTED, font_size=16, bold=True)

    draw_text_safe(pdraw, (48, 120), "6년 만의 동일 수법 재출현… 도심 공포 확산", fill=VOX_CRIMSON, font_size=30, bold=True)
    # Animated yellow highlighter wipe
    pdraw.rectangle([44, 160, 820, 172], fill=(250, 204, 21, 140))

    # Timeline bar
    ty = 740
    pdraw.line([(80, ty), (1240, ty)], fill=VOX_INK, width=4)
    for x, yr, desc in [(140, "1988", "제1차 사건"), (660, "1988~1994", "6년간의 의문의 침묵"), (1180, "1994", "동일범 재발")]:
        pdraw.ellipse([x - 10, ty - 10, x + 10, ty + 10], fill=VOX_CRIMSON if "1994" in yr else VOX_INK)
        draw_text_safe(pdraw, (x - 30, ty + 18), yr, fill=VOX_INK, font_size=18, bold=True)
        draw_text_safe(pdraw, (x - 60, ty + 46), desc, fill=VOX_INK_MUTED, font_size=14, bold=True)

    canvas.paste(paper, (W // 2 - paper.width // 2, 60), paper)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=True)
    return canvas


def render_archetype_p2(seq_p: float, frame_alley: Image.Image | None, frame_ai_scene: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#P2: Multi-Layer Angled Press Clippings + Police Red Curfew Notice."""
    canvas = get_dark_investigation_desk()

    # Red curfew notice
    curfew = Image.new("RGBA", (840, 780), (250, 245, 235, 255))
    cdraw = ImageDraw.Draw(curfew, "RGBA")
    cdraw.rectangle([16, 16, 823, 763], outline=VOX_CRIMSON + (255,), width=6)
    cdraw.rectangle([24, 24, 815, 755], outline=VOX_CRIMSON + (180,), width=2)
    draw_text_safe(cdraw, (840 // 2 - 200, 50), "긴급 야간 통행 제한 공고", fill=VOX_CRIMSON + (255,), font_size=32, bold=True)
    draw_text_safe(cdraw, (840 // 2 - 160, 100), "바이인시 공안국 방범지휘부", fill=VOX_INK + (255,), font_size=20, bold=True)

    draw_text_safe(cdraw, (60, 170), "1. 일몰 후 여성 단독 외출 전면 금지", fill=VOX_CRIMSON + (255,), font_size=22, bold=True)
    draw_text_safe(cdraw, (60, 220), "2. 야간 근무자 2인 1조 호송 이동 필수", fill=VOX_INK + (255,), font_size=20, bold=True)
    draw_text_safe(cdraw, (60, 270), "3. 수상한 외지인 발견 즉시 110 신고", fill=VOX_INK + (255,), font_size=20, bold=True)

    _draw_circular_official_seal(cdraw, 840 - 180, 780 - 180, r=54)
    canvas.paste(curfew, (120, 140))

    al_img = fit_crop(frame_alley or get_fallback_image(680, 480, "CURFEW STREET"), 680, 480)
    paste_photo_polaroid(canvas, al_img, (1400, 460), caption="야간 통제 구역 경찰 순찰", angle_deg=2.0, accent_badge="통금령")

    draw_vox_footage_lower_third(canvas, "비상 계엄 방범 통고 (POLICE CURFEW NOTICE)", "도시를 뒤흔든 야간 외출 금지와 붉은 옷 공포", wipe_p=1.0, accent=VOX_CRIMSON)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_p3(seq_p: float, frame_tv: Image.Image | None, frame_vhs: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#P3: 1990s CRT TV Broadcast Monitor + VHS Archive Tape."""
    canvas = Image.new("RGB", (W, H), (12, 14, 18))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # CRT Monitor housing
    mx0, my0, mx1, my1 = 120, 80, 1380, H - 100
    draw.rounded_rectangle([mx0 - 20, my0 - 20, mx1 + 20, my1 + 20], radius=24, fill=(35, 38, 44), outline=(70, 75, 84), width=6)

    tv_img = fit_crop(frame_tv or get_fallback_image(mx1 - mx0, my1 - my0, "1998 TV NEWS SPECIAL"), mx1 - mx0, my1 - my0)
    # Add scanlines
    tv_arr = np.array(tv_img)
    for r in range(0, tv_arr.shape[0], 4):
        tv_arr[r : r + 2, :, :] = (tv_arr[r : r + 2, :, :] * 0.75).astype(np.uint8)
    tv_scanned = Image.fromarray(tv_arr, "RGB")
    canvas.paste(tv_scanned, (mx0, my0))

    tdraw = ImageDraw.Draw(canvas, "RGBA")
    # TV Station Bug
    tdraw.rectangle([mx0 + 24, my0 + 24, mx0 + 160, my0 + 64], fill=(220, 38, 38, 220))
    draw_text_safe(tdraw, (mx0 + 36, my0 + 32), "뉴스특보", fill=(255, 255, 255, 255), font_size=20, bold=True)
    # Breaking News Chyron
    tdraw.rectangle([mx0, my1 - 70, mx1, my1], fill=(15, 23, 42, 235))
    draw_text_safe(tdraw, (mx0 + 32, my1 - 54), "[속보] 바이인 연쇄 강력사건 합동수사본부 공개 브리핑 진행", fill=(250, 204, 21, 255), font_size=22, bold=True)

    # Right side: VHS Archive Cassette Card
    vhs_card = Image.new("RGBA", (420, 520), (28, 32, 38, 255))
    vdraw = ImageDraw.Draw(vhs_card, "RGBA")
    vdraw.rectangle([0, 0, 419, 519], outline=(80, 90, 105), width=2)
    draw_text_safe(vdraw, (24, 24), "VHS ARCHIVE TAPE #1998", fill=(56, 189, 248, 255), font_size=18, bold=True)
    draw_text_safe(vdraw, (24, 60), "REC: 1998-11-30 SP-MODE", fill=(148, 163, 184, 255), font_size=14, bold=True)
    vh_img = fit_crop(frame_vhs or get_fallback_image(372, 360, "VHS LOG STILL"), 372, 360)
    vhs_card.paste(vh_img, (24, 100))
    canvas.paste(vhs_card, (1440, 140), vhs_card)

    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_p4(seq_p: float, frame_teletype: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#P4: Police Bulletin Teletype / Telex Dispatch Wire."""
    canvas = get_dark_investigation_desk()

    # Continuous tractor-feed teletype paper
    paper = get_torn_paper_sheet(1160, 840, fill_rgb=(242, 246, 240), seed=99)
    pdraw = ImageDraw.Draw(paper, "RGBA")
    # Perforated sprocket holes on sides
    for y in range(40, 800, 36):
        pdraw.ellipse([14, y, 26, y + 12], fill=(20, 25, 20, 180))
        pdraw.ellipse([1160 - 26, y, 1160 - 14, y + 12], fill=(20, 25, 20, 180))

    draw_text_safe(pdraw, (64, 48), "URGENT BOLO DISPATCH · 전국 공안 전신 급보", fill=VOX_CRIMSON, font_size=24, bold=True)
    draw_text_safe(pdraw, (64, 96), "PRIORITY: 1-A FLASH · 발신: 간쑤성 공안청 형사과", fill=VOX_INK_MUTED, font_size=16, bold=True)
    for i, line in enumerate([
        "수신: 전국 각 성·시·자치구 공안국 및 철도·교통 검문소",
        "내용: 바이인 연쇄 강력사건 용의자 이동 동선 긴급 전파",
        "인상착의: 40~50대 남성, 키 170~176cm, 칭청 방언 구사",
        "지시: 각 관할 기차역, 시외버스터미널 검문 강화 및 즉시 보고",
    ]):
        draw_text_safe(pdraw, (64, 160 + i * 44), line, fill=VOX_INK, font_size=18, bold=True)

    tt_img = fit_crop(frame_teletype or get_fallback_image(480, 360, "POLICE DISPATCH WIRE"), 480, 360)
    paper.paste(tt_img, (600, 380))

    canvas.paste(paper, (W // 2 - paper.width // 2, 80), paper)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=True)
    return canvas


def render_archetype_p5(seq_p: float, frame_radio: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#P5: Emergency Radio Dispatch Frequency Log & Audio Waveform."""
    canvas = Image.new("RGB", (W, H), (15, 18, 24))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Radio panel
    draw.rounded_rectangle([120, 100, W - 120, H - 120], radius=16, fill=(24, 30, 40), outline=(71, 85, 105), width=4)
    draw_text_safe(draw, (160, 140), "POLICE CRUISER RADIO TERMINAL · 무전 교신 일지", fill=(56, 189, 248, 255), font_size=24, bold=True)

    # Frequency dial
    draw.rounded_rectangle([160, 200, 560, 320], radius=8, fill=(10, 14, 20), outline=(245, 158, 11), width=2)
    draw_text_safe(draw, (200, 240), "FREQ: 154.825 MHz [CH-04]", fill=(245, 158, 11, 255), font_size=26, bold=True)

    rd_img = fit_crop(frame_radio or get_fallback_image(780, 460, "RADIO PATROL UNIT"), 780, 460)
    canvas.paste(rd_img, (640, 200))

    # Radio Log text
    for i, line in enumerate([
        "21:14 순찰 02호: 현장 500m 부근 용의차량 검문 완료, 이상 무.",
        "21:28 본부 지휘센터: 골목길 차단조 증원 요청 접수, 3조 급파.",
        "21:45 수사 1개: 용의자 신원 대조 진행 중, 전 대원 대기.",
    ]):
        draw_text_safe(draw, (160, 380 + i * 42), line, fill=(203, 213, 225, 255), font_size=16, bold=True)

    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


def render_archetype_p6(seq_p: float, frame_court: Image.Image | None, subtitle_text: str = "") -> Image.Image:
    """#P6: Declassified Supreme Court Verdict & Sentence Proclamation."""
    canvas = get_dark_investigation_desk()

    # Parchment document
    sheet = get_torn_paper_sheet(1160, 860, fill_rgb=(248, 244, 234), seed=77)
    sdraw = ImageDraw.Draw(sheet, "RGBA")
    # Black mourning ribbon on top-left corner
    sdraw.polygon([(0, 0), (120, 0), (0, 120)], fill=(18, 16, 14, 255))

    draw_text_safe(sdraw, (1160 // 2 - 160, 60), "형 사 판 결 문", fill=VOX_INK, font_size=36, bold=True)
    draw_text_safe(sdraw, (1160 // 2 - 180, 120), "간쑤성 바이인시 중급인민법원", fill=VOX_INK_MUTED, font_size=20, bold=True)

    verdict_lines = [
        "사건번호: (2017) 감04형초 제18호",
        "피고인: 가오청융 (高承勇)",
        "판결주문: 피고인 가오청융을 고의살인죄, 강간죄, 강도죄로",
        "사형(死刑)에 처하며, 정치권리를 종신 박탈한다.",
        "압수된 범죄수익 및 흉기 일체를 몰수한다.",
    ]
    for i, vl in enumerate(verdict_lines):
        fill_c = VOX_CRIMSON if "사형" in vl else VOX_INK
        draw_text_safe(sdraw, (120, 220 + i * 50), vl, fill=fill_c, font_size=22, bold=True)

    _draw_circular_official_seal(sdraw, 1160 - 220, 860 - 200, r=64)
    canvas.paste(sheet, (W // 2 - sheet.width // 2, 70), sheet)

    draw_vox_footage_lower_third(canvas, "사법 정의와 최종 판결 (FINAL VERDICT)", "28년 만에 내려진 사형 판결과 억울한 희생자들의 넋", wipe_p=1.0, accent=VOX_CRIMSON)
    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=True)
    return canvas


# ==============================================================================
# FULLSCREEN CINEMA ARCHETYPE (cinema_full)
# ==============================================================================

def render_cinema_full(seq_p: float, frame_img: Image.Image | None, subtitle_text: str = "", lower_third_title: str = "", lower_third_sub: str = "") -> Image.Image:
    """cinema_full: Fullscreen Cinematic Documentary Frame with lower-third."""
    p = ease_in_out_cubic(seq_p)
    base = fit_crop(frame_img or get_fallback_image(W, H, "CINEMATIC FOOTAGE"), W, H)

    # Subtle contrast and documentary grading
    canvas = ImageEnhance.Contrast(base).enhance(1.06)
    canvas = ImageEnhance.Color(canvas).enhance(0.94)

    if lower_third_title:
        draw_vox_footage_lower_third(canvas, lower_third_title, lower_third_sub, wipe_p=1.0, accent=VOX_YELLOW)

    draw_cinema_subtitle(canvas, subtitle_text, on_light_paper=False)
    return canvas


# Registry of all 24 archetypes
ARCHETYPE_RENDERERS = {
    "#M1": render_archetype_m1,
    "#M2": render_archetype_m2,
    "#M3": render_archetype_m3,
    "#M4": render_archetype_m4,
    "#M5": render_archetype_m5,
    "#M6": render_archetype_m6,
    "#M7": render_archetype_m7,
    "#M8": render_archetype_m8,
    "#D1": render_archetype_d1,
    "#D2": render_archetype_d2,
    "#D3": render_archetype_d3,
    "#D4": render_archetype_d4,
    "#D5": render_archetype_d5,
    "#D6": render_archetype_d6,
    "#D7": render_archetype_d7,
    "#D8": render_archetype_d8,
    "#D9": render_archetype_d9,
    "#D10": render_archetype_d10,
    "#P1": render_archetype_p1,
    "#P2": render_archetype_p2,
    "#P3": render_archetype_p3,
    "#P4": render_archetype_p4,
    "#P5": render_archetype_p5,
    "#P6": render_archetype_p6,
    "cinema_full": render_cinema_full,
}
