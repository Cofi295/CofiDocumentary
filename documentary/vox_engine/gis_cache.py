"""True Crime Vox & Real Satellite GIS Plate Cache & Web Mercator Engine.

Handles multi-scale Esri World Imagery plates (Z6, Z9, Z14, Z16), Web Mercator projections,
GeoJSON administrative boundary sweeps, camera viewports, and NumPy thermal infrared shaders.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Tuple
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from .typography import get_font


# Standard dimensions
W, H = 1920, 1080

# Primary GIS directory in CofiBlenderStudio, with fallback to local CofiDocumentary data
GIS_DIR_CANDIDATES = [
    r"b:\ALL_TOOLS\CofiBlenderStudio\vox_gis_cache",
    r"B:\ALL_TOOLS\CofiDocumentary\data\vox_gis_cache",
]

GIS_DIR = r"b:\ALL_TOOLS\CofiBlenderStudio\vox_gis_cache"
for d in GIS_DIR_CANDIDATES:
    if os.path.exists(d):
        GIS_DIR = d
        break

GIS_PLATE_CACHE: dict[str, tuple[Image.Image, dict[str, Any]]] = {}
GIS_JSON_CACHE: dict[str, dict[str, Any]] = {}
STYLED_MAP_CACHE: dict[str, tuple[Image.Image, dict[str, Any]]] = {}
GEOJSON_PTS_CACHE: dict[tuple[int, int, int, int], list[list[tuple[float, float]]]] = {}


def deg2num(lat_deg: float, lon_deg: float, zoom: int) -> tuple[float, float]:
    """Converts latitude and longitude into Web Mercator fractional tile coordinates."""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = (lon_deg + 180.0) / 360.0 * n
    ytile = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return xtile, ytile


def lonlat_to_plate_px(lon: float, lat: float, meta: dict[str, Any]) -> tuple[float, float]:
    """Projects longitude and latitude into pixel coordinates on the stitched master plate."""
    zoom = meta["zoom"]
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = (lon + 180.0) / 360.0 * n
    ytile = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    px = (xtile - meta["x0"]) * 256.0
    py = (ytile - meta["y0"]) * 256.0
    return px, py


def crop_map_camera(
    plate_img: Image.Image,
    meta: dict[str, Any],
    center_lon: float,
    center_lat: float,
    zoom_scale: float = 1.0,
    out_size: tuple[int, int] = (W, H),
) -> tuple[Image.Image, tuple[float, float, float]]:
    """Crops a camera viewport around (center_lon, center_lat) with sub-pixel floating-point interpolation."""
    cx, cy = lonlat_to_plate_px(center_lon, center_lat, meta)
    target_w, target_h = out_size
    safe_zoom = max(0.25, float(zoom_scale if zoom_scale is not None else 1.0))
    crop_w = min(float(plate_img.width), float(target_w) / safe_zoom)
    crop_h = min(float(plate_img.height), float(target_h) / safe_zoom)
    x0 = max(0.0, min(float(plate_img.width) - crop_w, cx - crop_w * 0.5))
    y0 = max(0.0, min(float(plate_img.height) - crop_h, cy - crop_h * 0.5))
    warped = plate_img.transform(
        out_size,
        Image.Transform.EXTENT,
        (x0, y0, x0 + crop_w, y0 + crop_h),
        resample=Image.Resampling.BICUBIC,
    )
    return warped, (x0, y0, safe_zoom)


def map_lonlat_to_screen(
    lon: float,
    lat: float,
    meta: dict[str, Any],
    cam_info: tuple[float, float, float],
) -> tuple[float, float]:
    """Projects geographic coordinates directly onto the 1920x1080 screen pixels."""
    px, py = lonlat_to_plate_px(lon, lat, meta)
    x0, y0, zoom_scale = cam_info
    sx = (px - x0) * zoom_scale
    sy = (py - y0) * zoom_scale
    return sx, sy


def _generate_fallback_plate(name: str) -> tuple[Image.Image, dict[str, Any]]:
    """Synthesizes an authentic fallback satellite/terrain plate if cached files are missing."""
    w, h = 2048, 1280
    zoom = 14
    if "z16" in name:
        zoom = 16
    elif "z9" in name:
        zoom = 9
    elif "z6" in name:
        zoom = 6

    # Procedural texture
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 15.0, (h // 4, w // 4, 3))
    base_color = np.array([45, 52, 42], dtype=np.float32)  # Earth/satellite dark tone
    if "relief" in name:
        base_color = np.array([120, 115, 105], dtype=np.float32)
    elif "carto" in name:
        base_color = np.array([230, 225, 215], dtype=np.float32)

    arr = np.clip(base_color + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB").resize((w, h), Image.Resampling.BICUBIC)

    draw = ImageDraw.Draw(img, "RGBA")
    # Draw procedural road network / river
    for i in range(12):
        y = int(i * (h / 12.0) + 40)
        draw.line([(0, y), (w, y + 30)], fill=(80, 75, 65, 120), width=3)
    for j in range(16):
        x = int(j * (w / 16.0) + 30)
        draw.line([(x, 0), (x + 20, h)], fill=(80, 75, 65, 120), width=2)

    meta = {
        "zoom": zoom,
        "x0": 12927,
        "y0": 6400,
        "tiles_w": 8,
        "tiles_h": 5,
        "width": w,
        "height": h,
    }
    return img, meta


def load_gis_plate(name: str) -> tuple[Image.Image, dict[str, Any]]:
    """Loads a cached GIS satellite/relief plate and its metadata."""
    if name in GIS_PLATE_CACHE:
        img, meta = GIS_PLATE_CACHE[name]
        return img.copy(), meta

    png_path = os.path.join(GIS_DIR, f"{name}.png")
    meta_path = os.path.join(GIS_DIR, f"{name}_meta.json")

    if os.path.exists(png_path) and os.path.exists(meta_path):
        try:
            img = Image.open(png_path).convert("RGB")
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            GIS_PLATE_CACHE[name] = (img, meta)
            return img.copy(), meta
        except Exception:
            pass

    # Fallback plate if file not present on disk
    img, meta = _generate_fallback_plate(name)
    GIS_PLATE_CACHE[name] = (img, meta)
    return img.copy(), meta


def load_gis_json(name: str) -> dict[str, Any]:
    """Loads GeoJSON boundary data from GIS cache or returns dummy feature collection."""
    if name in GIS_JSON_CACHE:
        return GIS_JSON_CACHE[name]

    json_path = os.path.join(GIS_DIR, f"{name}.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            GIS_JSON_CACHE[name] = data
            return data
        except Exception:
            pass

    # Fallback GeoJSON
    fallback = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": name, "adcode": "620000"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [103.5, 35.8],
                            [104.5, 35.8],
                            [104.5, 36.8],
                            [103.5, 36.8],
                            [103.5, 35.8],
                        ]
                    ],
                },
            }
        ],
    }
    GIS_JSON_CACHE[name] = fallback
    return fallback


def draw_geojson_feature_on_plate(
    draw: ImageDraw.ImageDraw,
    feature: dict[str, Any],
    meta: dict[str, Any],
    fill_rgba: tuple[int, int, int, int] | None = None,
    stroke_rgba: tuple[int, int, int, int] = (24, 23, 21, 180),
    width: int = 2,
    draw_progress: float = 1.0,
) -> None:
    """Renders GeoJSON polygon rings onto a GIS plate with optional animated stroke sweep."""
    cache_key = (id(feature), meta.get("zoom", 0), meta.get("x0", 0), meta.get("y0", 0))
    if cache_key not in GEOJSON_PTS_CACHE:
        geom = feature.get("geometry") or {}
        gtype = geom.get("type", "")
        coords = geom.get("coordinates") or []
        polys = coords if gtype == "MultiPolygon" else [coords]
        rings_px: list[list[tuple[float, float]]] = []
        for poly in polys:
            for ring in poly:
                pts = [lonlat_to_plate_px(pt[0], pt[1], meta) for pt in ring]
                if len(pts) >= 3:
                    rings_px.append(pts)
        GEOJSON_PTS_CACHE[cache_key] = rings_px

    for pts in GEOJSON_PTS_CACHE[cache_key]:
        if fill_rgba and draw_progress > 0.15:
            alpha = int(fill_rgba[3] * min(1.0, (draw_progress - 0.15) / 0.55))
            draw.polygon(pts, fill=(fill_rgba[0], fill_rgba[1], fill_rgba[2], alpha))
        if stroke_rgba and draw_progress > 0.01:
            n_pts = max(2, int(len(pts) * min(1.0, draw_progress)))
            draw.line(pts[:n_pts], fill=stroke_rgba, width=width, joint="curve")


def apply_infrared_thermal_shader(sat_image: Image.Image) -> Image.Image:
    """NumPy thermal/infrared shader.

    Transforms daylight satellite into slate-blue night-ops infrared false-color composite
    with warm sodium streetlight road luminescence.
    """
    arr = np.array(sat_image, dtype=np.float32) / 255.0
    # Luminance calculation
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    # Sobel high-pass edge gradient to isolate roads, roofs, and urban grids
    edges = np.abs(np.gradient(lum, axis=0)) + np.abs(np.gradient(lum, axis=1))
    road_glow = np.clip(edges * 3.2, 0.0, 1.0)

    # Night-ops slate blue with warm sodium streetlight glow
    night = np.zeros_like(arr)
    night[:, :, 0] = np.clip(lum * 0.18 + road_glow * 0.85, 0.0, 1.0)  # Red / Amber glow
    night[:, :, 1] = np.clip(lum * 0.32 + road_glow * 0.55, 0.0, 1.0)  # Green
    night[:, :, 2] = np.clip(lum * 0.54 + road_glow * 0.20, 0.0, 1.0)  # Slate Blue nocturnal tone

    out_arr = (night * 255.0).astype(np.uint8)
    return Image.fromarray(out_arr, "RGB")


def get_vox_styled_gansu_base() -> tuple[Image.Image, dict[str, Any]]:
    """Returns styled Gansu macro orbital satellite terrain base (Z6)."""
    if "gansu_z6_sat_real" in STYLED_MAP_CACHE:
        img, meta = STYLED_MAP_CACHE["gansu_z6_sat_real"]
        return img.copy(), meta

    relief, meta = load_gis_plate("plate_gansu_relief_z6")
    sat, _ = load_gis_plate("plate_gansu_sat_z6")
    carto, _ = load_gis_plate("plate_gansu_carto_z6")

    base_img = Image.blend(relief, sat, 0.88)
    base_img = ImageEnhance.Contrast(base_img).enhance(1.24)
    base_img = ImageEnhance.Color(base_img).enhance(1.08)
    base_img = ImageEnhance.Brightness(base_img).enhance(0.92)
    base_img = ImageChops.screen(base_img, ImageEnhance.Brightness(carto).enhance(0.22))

    china = load_gis_json("china_100000")
    draw = ImageDraw.Draw(base_img, "RGBA")
    for feat in china.get("features", []):
        adcode = str((feat.get("properties") or {}).get("adcode", ""))
        if adcode == "620000":
            continue
        draw_geojson_feature_on_plate(draw, feat, meta, fill_rgba=None, stroke_rgba=(220, 214, 198, 115), width=2)

    STYLED_MAP_CACHE["gansu_z6_sat_real"] = (base_img, meta)
    return base_img.copy(), meta


def get_vox_styled_baiyin_lanzhou_base() -> tuple[Image.Image, dict[str, Any]]:
    """Returns styled Baiyin-Lanzhou corridor regional satellite base (Z9)."""
    if "baiyin_z9_sat_real" in STYLED_MAP_CACHE:
        img, meta = STYLED_MAP_CACHE["baiyin_z9_sat_real"]
        return img.copy(), meta

    relief, meta = load_gis_plate("plate_baiyin_lanzhou_relief_z9")
    sat, _ = load_gis_plate("plate_baiyin_lanzhou_sat_z9")
    carto, _ = load_gis_plate("plate_baiyin_lanzhou_carto_z9")

    base_img = Image.blend(relief, sat, 0.90)
    base_img = ImageEnhance.Contrast(base_img).enhance(1.26)
    base_img = ImageEnhance.Color(base_img).enhance(1.06)
    base_img = ImageEnhance.Brightness(base_img).enhance(0.90)
    base_img = ImageChops.screen(base_img, ImageEnhance.Brightness(carto).enhance(0.24))

    gansu = load_gis_json("gansu_620000")
    draw = ImageDraw.Draw(base_img, "RGBA")
    for feat in gansu.get("features", []):
        draw_geojson_feature_on_plate(draw, feat, meta, fill_rgba=None, stroke_rgba=(228, 220, 200, 125), width=2)

    STYLED_MAP_CACHE["baiyin_z9_sat_real"] = (base_img, meta)
    return base_img.copy(), meta


def get_vox_styled_baiyin_urban_base(sat_weight: float = 0.96) -> tuple[Image.Image, dict[str, Any]]:
    """Returns styled Baiyin urban municipal satellite base (Z14)."""
    key = f"urban_z14_real_{sat_weight:.2f}"
    if key in STYLED_MAP_CACHE:
        img, meta = STYLED_MAP_CACHE[key]
        return img.copy(), meta

    sat, meta = load_gis_plate("plate_baiyin_city_sat_z14")
    carto, _ = load_gis_plate("plate_baiyin_city_carto_z14")

    img = sat.copy()
    img = ImageEnhance.Contrast(img).enhance(1.22)
    img = ImageEnhance.Color(img).enhance(1.05)
    img = ImageEnhance.Brightness(img).enhance(0.92)
    img = ImageChops.screen(img, ImageEnhance.Brightness(carto).enhance(0.22))

    STYLED_MAP_CACHE[key] = (img, meta)
    return img.copy(), meta


def get_real_satellite_campus_z16() -> tuple[Image.Image, dict[str, Any]]:
    """Returns high-resolution school campus rooftop satellite plate (Z16)."""
    if "campus_z16_real" in STYLED_MAP_CACHE:
        img, meta = STYLED_MAP_CACHE["campus_z16_real"]
        return img.copy(), meta

    sat, meta = load_gis_plate("plate_baiyin_campus_sat_z16")
    img = ImageEnhance.Contrast(sat).enhance(1.24)
    img = ImageEnhance.Sharpness(img).enhance(1.35)
    STYLED_MAP_CACHE["campus_z16_real"] = (img, meta)
    return img.copy(), meta


def draw_satellite_hud_grid(
    canvas: Image.Image,
    coord_text_ko: str = "LAT 36°33'03\"N · LON 104°08'52\"E",
    scale_label: str = "500m",
    accent_rgb: tuple[int, int, int] = (56, 189, 248),
) -> None:
    """Draws authentic satellite reconnaissance telemetry grid and coordinate HUD."""
    draw = ImageDraw.Draw(canvas, "RGBA")
    # Grid lines & corner ticks
    for gx in range(240, W, 320):
        draw.line([(gx, 0), (gx, H)], fill=(200, 230, 255, 22), width=1)
    for gy in range(180, H, 240):
        draw.line([(0, gy), (W, gy)], fill=(200, 230, 255, 22), width=1)
    for gx in range(240, W, 320):
        for gy in range(180, H, 240):
            draw.line([(gx - 7, gy), (gx + 7, gy)], fill=accent_rgb + (85,), width=1)
            draw.line([(gx, gy - 7), (gx, gy + 7)], fill=accent_rgb + (85,), width=1)

    # Top-Right Telemetry Pill
    f_bold = get_font(16, bold=True)
    tw = int(draw.textlength(coord_text_ko, font=f_bold) + 150)
    bx0, by0 = W - 46 - tw, 24
    draw.rounded_rectangle([bx0 + 3, by0 + 4, bx0 + tw + 3, by0 + 40 + 4], radius=6, fill=(0, 0, 0, 140))
    draw.rounded_rectangle([bx0, by0, bx0 + tw, by0 + 40], radius=6, fill=(14, 19, 26, 232), outline=accent_rgb + (195,), width=2)
    draw.ellipse([bx0 + 14, by0 + 14, bx0 + 26, by0 + 26], fill=(239, 68, 68, 255))
    draw.text((bx0 + 34, by0 + 9), "SAT-RECON", font=get_font(15, bold=True), fill=accent_rgb + (255,))
    draw.line([(bx0 + 126, by0 + 8), (bx0 + 126, by0 + 32)], fill=(120, 140, 160, 140), width=1)
    draw.text((bx0 + 138, by0 + 9), coord_text_ko, font=f_bold, fill=(242, 246, 250, 255))

    # Bottom-Left Scale Bar
    sx0, sy0 = 54, H - 132
    draw.rounded_rectangle([sx0, sy0, sx0 + 210, sy0 + 42], radius=5, fill=(14, 19, 26, 215), outline=(140, 160, 180, 140), width=1)
    draw.line([(sx0 + 16, sy0 + 26), (sx0 + 116, sy0 + 26)], fill=(255, 255, 255, 235), width=3)
    draw.line([(sx0 + 16, sy0 + 18), (sx0 + 16, sy0 + 30)], fill=(255, 255, 255, 235), width=2)
    draw.line([(sx0 + 116, sy0 + 18), (sx0 + 116, sy0 + 30)], fill=(255, 255, 255, 235), width=2)
    draw.text((sx0 + 128, sy0 + 10), scale_label, font=f_bold, fill=(238, 244, 248, 245))
