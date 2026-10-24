import sys
import os
from pathlib import Path

sys.path.insert(0, r"B:\ALL_TOOLS\CofiDocumentary")
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image

from documentary.vox_engine import (
    VoxSemanticRouter,
    VoxSceneRenderer,
    is_vox_satellite_enabled,
    draw_text_safe,
    verify_text_glyphs,
    split_balanced_korean,
    wrap_text_multiline,
    get_cascade_font,
    deg2num,
    lonlat_to_plate_px,
    crop_map_camera,
    apply_infrared_thermal_shader,
    load_gis_plate,
)

print("=== ADVERSARIAL STRESS TEST SUITE ===")

# 1. Semantic Router Adversarial Inputs
router = VoxSemanticRouter()

test_cases = [
    ("", "empty string"),
    ("   ", "whitespace only"),
    (None, "NoneType"),
    ("1234567890", "numbers only"),
    ("!@#$%^&*()_+=-`~[]{}|;:\",./<>?", "symbols only"),
    ("🕵️‍♂️🔎🩸🧬", "emojis only"),
    ("The quick brown fox jumps over the lazy dog.", "english nonsense"),
    ("가나다라마바사 아자차카타파하", "neutral korean"),
    ("Một ngày bình thường tại một ngôi làng nhỏ.", "neutral vietnamese"),
    ("A" * 5000, "5000 char flood"),
]

for text, desc in test_cases:
    try:
        res = router.route_beat(text)
        assert isinstance(res, dict)
        assert "archetype" in res
        assert "label" in res
        assert "cluster" in res
        print(f"[PASS] router on {desc} -> {res['archetype']} ({res['label']})")
    except Exception as e:
        print(f"[FAIL] router crashed on {desc}: {e}")
        raise

# Test timeline routing with malformed beats
malformed_beats = [
    {},
    {"text": None},
    {"narration_text": ""},
    {"beat_id": "b1", "text": "Y-STR 유전자 검사 결과"},
    {"beat_id": "b2", "narration_text": "매점 옥상 특정"},
    {"garbage_key": 999},
]
job_crime = {"channel_profile_id": "channel-e544a64b7c"}
routed = router.route_timeline(malformed_beats, job_crime)
assert len(routed) == len(malformed_beats)
for b in routed:
    assert "scene_archetype" in b
print("[PASS] SemanticRouter survived all edge cases and malformed beats.")

# 2. Typography Stress Testing
print("Testing Typography edge cases...")
w0 = wrap_text_multiline("테스트 문장입니다", max_width_px=0)
w_neg = wrap_text_multiline("테스트 문장입니다", max_width_px=-50)
w_huge = wrap_text_multiline("테스트 문장입니다", max_width_px=100000)
w_empty = wrap_text_multiline("", max_width_px=200)

s_empty = split_balanced_korean("")
s_one = split_balanced_korean("단어")
s_long = split_balanced_korean("매우긴단어하나로만공백없이이루어진경우의테스트문장입니다어떻게될까요", max_chars=10)
assert len(s_long) == 2

assert verify_text_glyphs("한국어 테스트 123 ABC") is True
assert verify_text_glyphs("甘肅省 白銀市 (Hanja)") is True
assert verify_text_glyphs("简体中文测试") is True
print("[PASS] Typography survived all edge cases.")

# 3. GIS Mercator and Plate Math Stress Testing
print("Testing GIS Mercator and plate projection edge cases...")
x1, y1 = deg2num(85.0, 104.0, 14)
x2, y2 = deg2num(-85.0, 104.0, 14)
assert x1 > 0 and y1 > 0

meta_test = {"zoom": 14, "x0": 12927, "y0": 6400}
px, py = lonlat_to_plate_px(-74.006, 40.7128, meta_test)
assert isinstance(px, float) and isinstance(py, float)

black_img = Image.new("RGB", (100, 100), (0, 0, 0))
white_img = Image.new("RGB", (100, 100), (255, 255, 255))
res_b = apply_infrared_thermal_shader(black_img)
res_w = apply_infrared_thermal_shader(white_img)
assert res_b.size == (100, 100) and res_w.size == (100, 100)
print("[PASS] GIS Math and Shaders survived all edge cases.")

# 4. Standalone Renderer Stress Testing
print("Testing Standalone Renderer edge cases...")
renderer = VoxSceneRenderer()

frame_unknown = renderer.render_frame("UNKNOWN_ARCHETYPE_XYZ", progress=0.5, subtitle_text="Unknown test")
assert frame_unknown.size == (1920, 1080)

frame_neg = renderer.render_frame("#M1", progress=-1.5)
frame_over = renderer.render_frame("#M1", progress=2.5)
assert frame_neg.size == (1920, 1080)
assert frame_over.size == (1920, 1080)

frame_empty_inputs = renderer.render_frame("#D4", progress=1.0, media_inputs={})
assert frame_empty_inputs.size == (1920, 1080)

print("[PASS] Standalone Renderer survived all edge cases.")
print("=== ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY! ===")
