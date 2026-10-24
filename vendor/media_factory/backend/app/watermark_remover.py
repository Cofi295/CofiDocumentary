from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFilter


_MIN_ALPHA = 8
_MIN_GAIN = 0.35
_MAX_GAIN = 1.20
_MIN_NCC = 0.80


@lru_cache(maxsize=1)
def _cached_alpha_map() -> Image.Image:
    # G-Labs' remover reveals a 48x48 translucent four-point mark. Cofi Studio
    # generates an equivalent mask geometrically so it does not depend on any
    # asset extracted from the packaged application.
    scale = 4
    side = 48
    canvas_side = side * scale
    center = (canvas_side - 1) / 2.0
    radius = 24.0 * scale
    shape_power = 0.725
    alpha = Image.new('L', (canvas_side, canvas_side), 0)
    pixels = alpha.load()
    for y in range(canvas_side):
        dy = abs((y - center) / radius)
        for x in range(canvas_side):
            dx = abs((x - center) / radius)
            if dx**shape_power + dy**shape_power <= 1.0:
                pixels[x, y] = 129
    return alpha.resize((side, side), Image.Resampling.LANCZOS)


def gemini_alpha_map() -> Image.Image:
    return _cached_alpha_map().copy()


def _auto_margin(image_size: tuple[int, int]) -> int:
    shortest = max(1, min(image_size))
    return max(8, min(32, round(shortest * 0.02)))


def gemini_watermark_box(image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = image_size
    mark_width, mark_height = _cached_alpha_map().size
    margin = _auto_margin(image_size)
    return width - mark_width - margin, height - mark_height - margin, mark_width, mark_height


def _edge_sample(image: Image.Image, x: int, y: int) -> tuple[float, float, float]:
    width, height = image.size
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))
    pixel = image.getpixel((x, y))
    return float(pixel[0]), float(pixel[1]), float(pixel[2])


def _estimated_background(
    image: Image.Image,
    x: int,
    y: int,
    px: int,
    py: int,
    width: int,
    height: int,
) -> tuple[float, float, float]:
    # Reconstruct a smooth local background from the four sides around the
    # known 48x48 mark. This follows G-Labs' diffuse-fill intent without adding
    # a NumPy/OpenCV dependency to the desktop app.
    left = _edge_sample(image, x - 2, y + py)
    right = _edge_sample(image, x + width + 1, y + py)
    top = _edge_sample(image, x + px, y - 2)
    bottom = _edge_sample(image, x + px, y + height + 1)
    tx = (px + 0.5) / width
    ty = (py + 0.5) / height
    return tuple(
        (
            (left[channel] * (1.0 - tx) + right[channel] * tx)
            + (top[channel] * (1.0 - ty) + bottom[channel] * ty)
        )
        * 0.5
        for channel in range(3)
    )


def _measure_candidate(
    image: Image.Image,
    x: int,
    y: int,
    alpha: Image.Image,
) -> tuple[float, float, tuple[float, float, float]]:
    mark_width, mark_height = alpha.size
    dot = 0.0
    actual_energy = 0.0
    predicted_energy = 0.0
    channel_dot = [0.0, 0.0, 0.0]
    channel_predicted = [0.0, 0.0, 0.0]

    for py in range(mark_height):
        for px in range(mark_width):
            alpha_value = alpha.getpixel((px, py))
            if alpha_value < _MIN_ALPHA:
                continue
            opacity = alpha_value / 255.0
            observed = image.getpixel((x + px, y + py))
            background = _estimated_background(image, x, y, px, py, mark_width, mark_height)
            for channel in range(3):
                predicted = (255.0 - background[channel]) * opacity
                if predicted < 0.75:
                    continue
                actual = float(observed[channel]) - background[channel]
                dot += actual * predicted
                actual_energy += actual * actual
                predicted_energy += predicted * predicted
                channel_dot[channel] += actual * predicted
                channel_predicted[channel] += predicted * predicted

    if predicted_energy < 1.0 or actual_energy < 1.0:
        return 0.0, 0.0, (0.0, 0.0, 0.0)
    gain = dot / predicted_energy
    ncc = dot / math.sqrt(actual_energy * predicted_energy)
    channel_gains = tuple(
        channel_dot[index] / channel_predicted[index] if channel_predicted[index] >= 1.0 else 0.0
        for index in range(3)
    )
    return gain, ncc, channel_gains


def _find_mark(image: Image.Image, alpha: Image.Image) -> tuple[int, int, float] | None:
    width, height = image.size
    mark_width, mark_height = alpha.size
    if width < mark_width + 16 or height < mark_height + 16:
        return None

    auto = _auto_margin(image.size)
    max_margin = min(128, max(48, round(min(image.size) * 0.12)))
    margins = sorted({auto, *range(6, max_margin + 1)})
    best: tuple[float, int, int, float, float, tuple[float, float, float]] | None = None
    for margin in margins:
        x = width - mark_width - margin
        y = height - mark_height - margin
        if x < 2 or y < 2 or x + mark_width + 2 >= width or y + mark_height + 2 >= height:
            continue
        gain, ncc, channel_gains = _measure_candidate(image, x, y, alpha)
        score = max(0.0, gain) * max(0.0, ncc)
        candidate = (score, x, y, gain, ncc, channel_gains)
        if best is None or candidate[0] > best[0]:
            best = candidate

    if best is None:
        return None
    _, x, y, gain, ncc, channel_gains = best
    if gain < _MIN_GAIN or gain > _MAX_GAIN or ncc < _MIN_NCC or min(channel_gains) < 0.20:
        return None
    if max(channel_gains) - min(channel_gains) > 0.80:
        return None
    return x, y, min(1.5, max(0.0, gain))


def purify(image: Image.Image, *, verbose: bool = False) -> tuple[Image.Image, bool]:
    del verbose  # API parity with the G-Labs helper; Cofi Studio keeps logs at provider level.
    rgb = image.convert('RGB')
    alpha = _cached_alpha_map()
    match = _find_mark(rgb, alpha)
    if match is None:
        return rgb.copy(), False

    x, y, _gain = match
    result = rgb.copy()
    mark_width, mark_height = alpha.size
    cleanup_mask = alpha.filter(ImageFilter.MaxFilter(7))
    for py in range(mark_height):
        for px in range(mark_width):
            if cleanup_mask.getpixel((px, py)) < _MIN_ALPHA:
                continue
            background = _estimated_background(rgb, x, y, px, py, mark_width, mark_height)
            clean = tuple(max(0, min(255, round(channel))) for channel in background)
            result.putpixel((x + px, y + py), clean)
    return result, True


def strip_gemini_watermark(path: str | Path) -> bool:
    target = Path(path)
    with Image.open(target) as source:
        source.load()
        cleaned, removed = purify(source)
    if not removed:
        return False

    suffix = target.suffix.lower()
    temp = target.with_name(f'.{target.name}.watermark.tmp')
    try:
        if suffix in {'.jpg', '.jpeg'}:
            cleaned.save(temp, format='JPEG', quality=95, subsampling=0)
        elif suffix == '.webp':
            cleaned.save(temp, format='WEBP', quality=95)
        else:
            cleaned.save(temp, format='PNG')
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink()
    return True
