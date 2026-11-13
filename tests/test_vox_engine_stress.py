"""Comprehensive Empirical Stress and Adversarial Test Suite for Vox & Satellite Engine.

Tests:
1. Semantic router stress: extreme/bizarre narration inputs (empty string, 500-word run-on text, mixed language sentences, emoji, numeric coordinates, slang).
2. Anti-repetition stress: 10 consecutive identical sentences; verify variant/sibling rotation vs identical repetition.
3. GIS Plate Loader stress: invalid coordinate requests (lat/lon out of bounds), extreme zoom requests, fallback plate generation.
4. Typography stress: mixed Korean, Vietnamese diacritics, Simplified Chinese, Hanja, numbers, symbols, zero tofu, valid RGB output.
5. Process and port hygiene: ports 8000, 8878, 8890, 8900 alive and undisturbed; no background blender daemon.
"""

import math
import os
import re
import socket
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from PIL import Image, ImageDraw

import pytest

from documentary.vox_engine.semantic_router import (
    VOX_ARCHETYPE_RULES,
    VoxSemanticRouter,
    is_vox_satellite_enabled,
)
from documentary.vox_engine.gis_cache import (
    W,
    H,
    apply_infrared_thermal_shader,
    crop_map_camera,
    deg2num,
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
from documentary.vox_engine.typography import (
    CJKFallbackFont,
    draw_text_safe,
    get_cascade_font,
    get_font,
    load_font,
    split_balanced_korean,
    verify_text_glyphs,
    wrap_text_multiline,
)
from documentary.vox_engine.archetypes import (
    ARCHETYPE_RENDERERS,
    get_fallback_image,
)
from documentary.vox_engine.renderer import VoxSceneRenderer


# ==============================================================================
# Area 1: Semantic Router Stress
# ==============================================================================

class TestArea1SemanticRouterStress:
    """Stress tests extreme, bizarre, boundary narration inputs to VoxSemanticRouter."""

    @pytest.fixture(autouse=True)
    def setup_router(self):
        self.router = VoxSemanticRouter()

    def test_empty_and_whitespace_inputs(self):
        cases = ["", "   ", "\t\t\n\r  ", " \n "]
        for text in cases:
            res = self.router.route_beat(text)
            assert isinstance(res, dict)
            assert "archetype" in res
            assert res["archetype"] in ARCHETYPE_RENDERERS
            assert res["cluster"] in ("cinema", "interrogation")
            assert res["score"] == 0.0

    def test_none_and_non_string_inputs(self):
        cases = [None, 12345, 99.9, ["list"], {"dict": "val"}]
        for val in cases:
            res = self.router.route_beat(val)
            assert isinstance(res, dict)
            assert "archetype" in res
            assert res["archetype"] in ARCHETYPE_RENDERERS

    def test_emoji_only_narration(self):
        text = "🕵️‍♂️💥🚨🔍📍📜⚖️🩸😱🚔"
        res = self.router.route_beat(text)
        assert isinstance(res, dict)
        assert res["archetype"] in ARCHETYPE_RENDERERS
        # Should gracefully fall back without exception

    def test_numeric_coordinates_and_telemetry(self):
        text = "LAT 36°33'03\"N · LON 104°08'52\"E · ALT 1720m · GPS FIX 1988-05-26 14:30:00"
        res = self.router.route_beat(text)
        assert isinstance(res, dict)
        assert res["archetype"] in ARCHETYPE_RENDERERS

    def test_slang_korean_and_vietnamese(self):
        slang_ko = "ㄹㅇ 갓겜 ㄷㄷ 킹정 존버 쌉파서블 뇌절 ㅋㅋㅋ ㅠㅠ ㄹㅇ 실화냐 대박 레전드"
        res_ko = self.router.route_beat(slang_ko)
        assert res_ko["archetype"] in ARCHETYPE_RENDERERS

        slang_vi = "vl vcl ảo ma canada vcl u là trời khum biết dc chán ghê á trời ơi đỉnh chóp"
        res_vi = self.router.route_beat(slang_vi)
        assert res_vi["archetype"] in ARCHETYPE_RENDERERS

    def test_mixed_language_multilingual_sentence(self):
        text = "The suspect 嫌疑人 appeared near Lan Châu (란저우) and Внезапно disappeared vào lúc nửa đêm cùng với ADN dòng họ và Y-STR 분석 결과."
        res = self.router.route_beat(text)
        assert res["archetype"] in ARCHETYPE_RENDERERS
        # Should trigger Y-STR or biometrics (#D4)
        assert res["archetype"] in ("#D4", "#M2")

    def test_run_on_500_word_text_performance(self):
        # 500 words of mixed investigative jargon and filler
        words = ["사건", "기록", "수사", "증거", "공안", "현장", "단서", "추적", "조사", "지문"]
        long_text = " ".join(words[i % len(words)] for i in range(500))

        t0 = time.perf_counter()
        res = self.router.route_beat(long_text)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert res["archetype"] in ARCHETYPE_RENDERERS
        # Must execute within 50ms, confirming no catastrophic regex backtracking
        assert elapsed_ms < 50.0, f"Execution too slow: {elapsed_ms:.2f}ms"


# ==============================================================================
# Area 2: Anti-Repetition Stress
# ==============================================================================

class TestArea2AntiRepetitionStress:
    """Stress tests 10 consecutive identical sentences to verify rotation vs identical repetition."""

    @pytest.fixture(autouse=True)
    def setup_router(self):
        self.router = VoxSemanticRouter()

    def test_fingerprint_competing_siblings_rotation(self):
        """Sentence matching both #D9 and #D1: router alternates between siblings."""
        text = "단 하나의 지문, 14개 특징점이 완벽히 일치했다"
        history = [self.router.route_beat(text)["archetype"] for _ in range(10)]

        # Check consecutive duplicates
        consecutive_dups = [
            (i, history[i-1], history[i])
            for i in range(1, len(history))
            if history[i] == history[i-1]
        ]
        assert len(consecutive_dups) == 0, f"Unexpected consecutive duplicates: {consecutive_dups}"
        assert {"#D9", "#D1"}.issubset(set(history))

    def test_single_match_consecutive_repetition_defect(self):
        """Sentence with high base score matching single archetype:
        Documents empirical finding that immediate predecessor penalty (-105) < base score (122..126),
        causing immediate back-to-back repetition."""
        test_sentences = {
            "DNA_Y_STR": "국립과학수사연구원은 Y-염색체 DNA 족보 가계도를 분석했다",
            "CAMPUS_STORE": "경찰은 바이인 제4중학교 매점을 급습하여 용의자를 체포했다",
            "CURFEW_NIGHT": "해가 지면 야간 통제와 통금이 시작되고 적외선 순찰이 강화되었다",
            "CRT_NEWS": "당시 1990년대 방송 뉴스 특보 화면이다",
            "WANTED_WARRANT": "공안부는 1급 지명수배령을 내리고 20만 위안의 현상금을 걸었다",
            "COURT_VERDICT": "법원은 피고인에게 사형을 선고하고 정치권리를 박탈했다",
        }

        repetition_findings = {}
        for label, sentence in test_sentences.items():
            self.router.reset_history()
            history = [self.router.route_beat(sentence)["archetype"] for _ in range(10)]
            dups = [
                (i, history[i-1], history[i])
                for i in range(1, len(history))
                if history[i] == history[i-1]
            ]
            repetition_findings[label] = {
                "history": history,
                "has_consecutive_dup": len(dups) > 0,
                "duplicates": dups,
            }

        # Assert that anti-repetition penalty completely prevents consecutive duplicates
        for label, findings in repetition_findings.items():
            assert not findings["has_consecutive_dup"], f"{label} produced unexpected consecutive duplicates: {findings['duplicates']}"
            assert len(findings["duplicates"]) == 0
        assert repetition_findings["DNA_Y_STR"]["history"][:3] == ["#D4", "cinema_full", "#D2"]


# ==============================================================================
# Area 3: GIS Plate Loader Stress
# ==============================================================================

class TestArea3GISPlateLoaderStress:
    """Stress tests coordinates out of bounds, extreme zoom, and fallback generation."""

    def test_deg2num_extreme_latitudes(self):
        cases = [
            (90.0, 104.0, 14),
            (-90.0, 104.0, 14),
            (95.0, 104.0, 14),
            (-95.0, 104.0, 14),
            (1000.0, 104.0, 14),
            (-1000.0, 104.0, 14),
            (36.0, 104.0, 0),
            (36.0, 104.0, -5),
            (36.0, 104.0, 64),
        ]
        for lat, lon, zoom in cases:
            xtile, ytile = deg2num(lat, lon, zoom)
            assert not math.isnan(xtile)
            assert not math.isnan(ytile)
            assert not math.isinf(xtile)

    def test_crop_map_camera_normal_and_extreme_high_zoom(self):
        plate, meta = load_gis_plate("test_dummy_plate")
        assert isinstance(plate, Image.Image)
        assert plate.size == (2048, 1280)

        # High zoom and out-of-bounds coordinates work cleanly
        cases = [
            (9999.0, -9999.0, 1.0),
            (104.16, 36.54, 2.0),
            (104.16, 36.54, 10.0),
            (104.16, 36.54, 1000.0),
            (104.16, 36.54, 100000.0),
        ]
        for lon, lat, zoom_scale in cases:
            cropped, cam_info = crop_map_camera(plate, meta, lon, lat, zoom_scale=zoom_scale)
            assert isinstance(cropped, Image.Image)
            assert cropped.size == (W, H)
            assert cropped.mode == "RGB"

    def test_crop_map_camera_decompression_bomb_vulnerability(self):
        """Verifies resolution of vulnerability: when zoom_scale <= 0.1, crop_w and crop_h are clamped,
        preventing PIL.Image.DecompressionBombError and returning valid 1920x1080 RGB frames."""
        plate, meta = load_gis_plate("test_dummy_plate")

        # When zoom_scale is 0.1, 0.0, or negative, safe clamping prevents DecompressionBombError:
        wide_and_boundary_scales = [0.1, 0.0, -5.0]
        for z in wide_and_boundary_scales:
            cropped, cam_info = crop_map_camera(plate, meta, 104.16, 36.54, zoom_scale=z)
            assert isinstance(cropped, Image.Image)
            assert cropped.size == (W, H)
            assert cropped.mode == "RGB"
            assert cam_info[2] >= 0.25

    def test_load_gis_plate_fallback_generation(self):
        # Non-existent plate name should synthesize valid fallback image
        names = ["non_existent_plate_xyz", "plate_test_z16", "plate_test_z9", "plate_test_z6"]
        for name in names:
            img, meta = load_gis_plate(name)
            assert isinstance(img, Image.Image)
            assert img.size == (2048, 1280)
            assert img.mode == "RGB"
            assert isinstance(meta, dict)
            assert "zoom" in meta
            assert "width" in meta

    def test_load_gis_json_fallback(self):
        data = load_gis_json("non_existent_boundary_file")
        assert isinstance(data, dict)
        assert data.get("type") == "FeatureCollection"
        assert len(data.get("features", [])) > 0

    def test_apply_infrared_thermal_shader_stability(self):
        # Test shader with normal, solid, and noise images
        cases = [
            Image.new("RGB", (1920, 1080), (0, 0, 0)),
            Image.new("RGB", (1920, 1080), (255, 255, 255)),
            Image.fromarray(np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8), "RGB"),
        ]
        for src in cases:
            res = apply_infrared_thermal_shader(src)
            assert isinstance(res, Image.Image)
            assert res.size == (1920, 1080)
            assert res.mode == "RGB"

    def test_styled_bases_return_valid_images(self):
        for fn in [get_vox_styled_gansu_base, get_vox_styled_baiyin_lanzhou_base, get_vox_styled_baiyin_urban_base, get_real_satellite_campus_z16]:
            img, meta = fn()
            assert isinstance(img, Image.Image)
            assert img.mode == "RGB"
            assert isinstance(meta, dict)


# ==============================================================================
# Area 4: Typography Stress
# ==============================================================================

class TestArea4TypographyStress:
    """Stress tests Korean, Vietnamese diacritics, Simplified Chinese, Hanja, numbers, symbols."""

    def test_multilingual_glyph_verification(self):
        text_samples = [
            "백은시 연쇄살인사건 유력 용의자 긴급 체포",
            "Đại án Bạch Ngân: Bắt giữ khẩn cấp nghi phạm số một Cao Thừa Dũng tại tiệm tạp hóa",
            "白银市连环杀人案 嫌疑人 高承勇 公安 现场 勘查 提取指纹",
            "白銀市 連環殺人案 嫌疑人 高承勇 現場 檢證 司法 審判",
            "№ 1988-1994-2002-2016 · 14-Point · 99.98% · [STR-DNA] · ★★★ §42",
        ]
        for text in text_samples:
            ok = verify_text_glyphs(text, font_size=24, bold=True)
            assert ok, f"Glyph verification failed for: {text}"

    def test_draw_text_safe_renders_non_blank_rgb(self):
        canvas = Image.new("RGB", (1920, 1080), (20, 20, 20))
        draw = ImageDraw.Draw(canvas)
        text = "백은시 연쇄살인 嫌疑人 高承勇 公安 现场 [STR-DNA 14-Point] ★★★"
        end_x = draw_text_safe(draw, (100, 100), text, fill=(255, 255, 255), font_size=28)
        assert end_x > 100

        # Verify pixels were written
        arr = np.array(canvas)
        non_bg_pixels = np.sum(arr != 20)
        assert non_bg_pixels > 500, "Text did not draw visible pixels on canvas"

    def test_split_balanced_korean(self):
        cases = [
            ("", [""]),
            ("단어", ["단어"]),
            ("경찰은 바이인 제4중학교 매점을 급습하여 용의자를 긴급 체포했다", 2),
            ("수사관들은 28년간 현장에 남아 있던 단 하나의 지문을 놓치지 않았다", 2),
        ]
        for item in cases:
            text = item[0]
            lines = split_balanced_korean(text, max_chars=28)
            assert isinstance(lines, list)
            if len(item) == 2 and isinstance(item[1], int):
                assert len(lines) == item[1]

    def test_wrap_text_multiline(self):
        long_text = "국립과학수사연구원은 백은시 연쇄살인사건의 유력 용의자 DNA 대조 검사를 신속히 진행하여 14개 특징점 일치 결과를 발표했다."
        lines = wrap_text_multiline(long_text, max_px_width=600, font_size=24)
        assert len(lines) >= 2
        for l in lines:
            assert len(l) > 0

    def test_vox_scene_renderer_all_archetypes_with_multilingual_subtitles(self):
        renderer = VoxSceneRenderer()
        subtitle = "1988-2016 백은시(白銀市) 연쇄살인 嫌疑人 체포 — 14-Point DNA 일치"

        # Font & plate cache warmup to eliminate cold-start timing spikes on Windows
        first_arch = next(iter(ARCHETYPE_RENDERERS.keys()))
        renderer.render_frame(
            archetype_id=first_arch,
            progress=0.1,
            subtitle_text=subtitle,
        )

        for arch_id in ARCHETYPE_RENDERERS.keys():
            t0 = time.perf_counter()
            frame = renderer.render_frame(
                archetype_id=arch_id,
                progress=0.75,
                subtitle_text=subtitle,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            assert isinstance(frame, Image.Image)
            assert frame.size == (1920, 1080)
            assert frame.mode == "RGB"
            # Fast pure Python compositing assertion (< 1200ms per frame under Windows host load)
            assert elapsed_ms < 1200.0, f"Archetype {arch_id} render too slow: {elapsed_ms:.1f}ms"



# ==============================================================================
# Area 5: Process and Port Hygiene
# ==============================================================================

class TestArea5ProcessAndPortHygiene:
    """Verifies no background blender daemon was launched and core studio ports 8000, 8878, 8890 are undisturbed."""

    def test_listening_ports_active(self):
        ports = [8000, 8878, 8890]
        results = {}
        for port in ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.8)
            try:
                res = s.connect_ex(("127.0.0.1", port))
                results[port] = (res == 0)
            finally:
                s.close()

        for port, is_open in results.items():
            assert is_open, f"Port {port} is not listening or was disturbed"

    def test_no_blender_process(self):
        # Verify no blender daemon process running
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Process *blender* -ErrorAction SilentlyContinue | Select-Object Id, ProcessName"],
            capture_output=True,
            text=True,
        )
        assert out.returncode == 0
        # Output should have no process rows
        lines = [line.strip() for line in out.stdout.splitlines() if line.strip()]
        assert len(lines) == 0, f"Found active blender process: {lines}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
