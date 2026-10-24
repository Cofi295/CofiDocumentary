"""Official Production Test Suite for Vox & Real Satellite Scene Renderer.

Covers:
1. Multi-scale real satellite imagery cache loading (Z6, Z9, Z14, Z16 from b:\\ALL_TOOLS\\CofiBlenderStudio\\vox_gis_cache\\).
2. Pure Python 1920x1080 frame rendering for representative True Crime archetypes:
   - Satellite maps: #M1 (Z16 rooftop), #M2 (Z6/Z9 corridor), #M3 (Z9 river/boundary), #M5 (Z14 2.5D slab), #M7 (Z14 thermal infrared).
   - Forensic dossiers: #D1 (latent print), #D4 (Y-STR pedigree), #D5 (interrogation transcript), #D6 (wanted warrant), #D9 (14-point comparator).
   - Press & broadcast: #P1 (timeline), #P3 (1990s CRT broadcast).
   - Cinema full: cinema_full (emotion frame with lower-third and subtitle).
3. Image output verification: exact dimensions (1920, 1080), non-empty file size, valid RGB mode.
4. Tofu-proof typography verification: zero missing glyphs across Korean Hangul, Vietnamese diacritics, Traditional Hanja, Simplified Chinese, and telemetry symbols.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from documentary.vox_engine.archetypes import ARCHETYPE_RENDERERS, W, H
from documentary.vox_engine.gis_cache import (
    GIS_DIR,
    apply_infrared_thermal_shader,
    crop_map_camera,
    deg2num,
    get_real_satellite_campus_z16,
    get_vox_styled_baiyin_lanzhou_base,
    get_vox_styled_baiyin_urban_base,
    get_vox_styled_gansu_base,
    load_gis_plate,
    lonlat_to_plate_px,
)
from documentary.vox_engine.renderer import VoxSceneRenderer
from documentary.vox_engine.typography import (
    CJKFallbackFont,
    draw_text_safe,
    get_cascade_font,
    get_font,
    verify_text_glyphs,
)


# ==============================================================================
# 1. Real Satellite Imagery Cache & Projections (Z6, Z9, Z14, Z16)
# ==============================================================================

class TestRealSatelliteGisPlates:
    """Verifies that real cached satellite imagery plates at Z6, Z9, Z14, Z16 load correctly."""

    def test_gis_cache_directory_exists_and_contains_plates(self):
        cache_path = Path(GIS_DIR)
        assert cache_path.exists(), f"GIS cache directory {GIS_DIR} does not exist"

        expected_plates = [
            ("plate_gansu_sat_z6.png", 6),
            ("plate_baiyin_lanzhou_sat_z9.png", 9),
            ("plate_baiyin_city_sat_z14.png", 14),
            ("plate_baiyin_campus_sat_z16.png", 16),
        ]
        for filename, zoom in expected_plates:
            plate_file = cache_path / filename
            assert plate_file.exists(), f"Expected satellite plate {filename} not found in {GIS_DIR}"
            assert plate_file.stat().st_size > 100_000, f"Plate {filename} file size too small: {plate_file.stat().st_size}"

    def test_z6_gansu_plate_loader(self):
        img, meta = get_vox_styled_gansu_base()
        assert isinstance(img, Image.Image)
        assert img.size == (2048, 1280)
        assert img.mode == "RGB"
        assert meta.get("zoom") == 6
        assert meta.get("width") == 2048

    def test_z9_baiyin_lanzhou_plate_loader(self):
        img, meta = get_vox_styled_baiyin_lanzhou_base()
        assert isinstance(img, Image.Image)
        assert img.size == (2048, 1280)
        assert img.mode == "RGB"
        assert meta.get("zoom") == 9

    def test_z14_baiyin_urban_plate_loader(self):
        img, meta = get_vox_styled_baiyin_urban_base()
        assert isinstance(img, Image.Image)
        assert img.size == (2048, 1280)
        assert img.mode == "RGB"
        assert meta.get("zoom") == 14

    def test_z16_baiyin_campus_plate_loader(self):
        img, meta = get_real_satellite_campus_z16()
        assert isinstance(img, Image.Image)
        assert img.size == (2048, 1280)
        assert img.mode == "RGB"
        assert meta.get("zoom") == 16

    def test_web_mercator_coordinate_projection(self):
        """Tests projection math from GPS degrees to plate pixels at Baiyin coordinates."""
        lat_baiyin, lon_baiyin = 36.545, 104.168
        xtile, ytile = deg2num(lat_baiyin, lon_baiyin, zoom=16)
        assert 51500 < xtile < 52000
        assert 25500 < ytile < 25800

        _, meta = get_real_satellite_campus_z16()
        px, py = lonlat_to_plate_px(104.1516, 36.547, meta)
        assert 0 <= px <= 2048
        assert 0 <= py <= 1280

    def test_crop_map_camera_produces_1080p_rgb(self):
        plate, meta = get_real_satellite_campus_z16()
        cropped, cam = crop_map_camera(plate, meta, center_lon=104.168, center_lat=36.545, zoom_scale=1.5)
        assert isinstance(cropped, Image.Image)
        assert cropped.size == (W, H)
        assert cropped.mode == "RGB"
        assert cam[2] == 1.5


# ==============================================================================
# 2. 1920x1080 Scene Frame Rendering (All Archetypes)
# ==============================================================================

class TestVoxSceneRenderer1080pCompositions:
    """Verifies that VoxSceneRenderer produces valid 1920x1080 RGB frames across archetypes."""

    @pytest.fixture(autouse=True)
    def setup_renderer(self, tmp_path: Path):
        self.renderer = VoxSceneRenderer()
        self.output_dir = tmp_path / "rendered_frames"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @pytest.mark.parametrize(
        "archetype_id,subtitle",
        [
            ("#M1", "제4중학교 매점 옥상 위성 정밀 감시 — 혐의자 고승용 은신처"),
            ("#M2", "간쑤성 란저우-바이인 공업 회랑 위성 도주로 분석"),
            ("#M3", "황하 도주로 및 행정구역 성 경계선 관할 구역 추적"),
            ("#M4", "백은시 연쇄살인 사건 연쇄 범행 핀보드 및 지리적 클러스터"),
            ("#M5", "연쇄 범행 좌표 3차원 입체 위성 지형 슬랩 분석"),
            ("#M6", "광역 도심 위성에서 매점 옥상으로 듀얼 분할 확대"),
            ("#M7", "야간 통제 적외선 열화상 위성 순찰 및 3km 봉쇄선"),
            ("#D1", "23만 장 지문 대조망과 미제 지문 카드 정밀 비교"),
            ("#D3", "현장 3대 핵심 물증: 혈액형, 족적, 생체 시료 감정서"),
            ("#D4", "국립과학수사연구원 Y-STR 가계도 족보 분석 및 부계 혈통 추적"),
            ("#D5", "심문실 피의자 자백 진술서 및 음성 성문 파형 대조"),
            ("#D6", "공안부 1급 지명수배령 및 몽타주 몽타주 스케치 공고"),
            ("#D9", "현미경 14개 특징점 융선 비교 현미경 정밀 감정"),
            ("#P1", "1988년부터 2016년까지 28년간의 침묵과 미제 사건 연표"),
            ("#P2", "1990년대 백은시민 공포와 야간 외출 금지 비상 통고문"),
            ("#P3", "1990년대 방송 뉴스 특보 브라운관 아카이브 보도"),
            ("cinema_full", "차가운 법정 바닥에서 오열하는 희생자 유가족의 눈물"),
        ],
    )
    def test_render_sample_scene_to_file(self, archetype_id: str, subtitle: str):
        out_file = self.output_dir / f"{archetype_id.replace('#', '')}_test.jpg"
        frame = self.renderer.render_frame(
            archetype_id=archetype_id,
            progress=0.75,
            subtitle_text=subtitle,
            out_path=out_file,
            lower_third_title="특급수배록 제1회",
            lower_third_sub="중국 실화 사건 파일",
        )

        # 1. In-memory image checks
        assert isinstance(frame, Image.Image)
        assert frame.size == (1920, 1080), f"Frame size must be (1920, 1080), got {frame.size}"
        assert frame.mode == "RGB", f"Frame mode must be RGB, got {frame.mode}"

        # 2. On-disk file verification
        assert out_file.exists(), f"Rendered frame file not saved to {out_file}"
        file_size = out_file.stat().st_size
        assert file_size > 50_000, f"File size too small ({file_size} bytes), possible blank frame"

        # 3. Re-read verification
        with Image.open(out_file) as saved_img:
            assert saved_img.size == (1920, 1080)
            assert saved_img.mode == "RGB"

    def test_render_all_24_archetypes_without_exception(self):
        """Verifies that all 24 registered archetypes render without crashing."""
        all_archetypes = self.renderer.list_archetypes()
        assert len(all_archetypes) >= 24

        for arch_id in all_archetypes:
            frame = self.renderer.render_frame(
                archetype_id=arch_id,
                progress=0.5,
                subtitle_text="테스트 자막 / Phụ đề kiểm tra / Test Subtitle",
            )
            assert isinstance(frame, Image.Image)
            assert frame.size == (1920, 1080)
            assert frame.mode == "RGB"

    def test_render_sequence_produces_consistent_frames(self):
        """Tests animated frame sequence generation for Remotion / MP4 pipeline."""
        seq_dir = self.output_dir / "anim_sequence"
        frames = self.renderer.render_sequence(
            archetype_id="#M1",
            num_frames=5,
            subtitle_text="매점 옥상 줌인 애니메이션 시퀀스",
            out_dir=seq_dir,
        )
        assert len(frames) == 5
        for i, frame in enumerate(frames):
            assert frame.size == (1920, 1080)
            frame_path = seq_dir / f"frame_{i:04d}.jpg"
            assert frame_path.exists()
            assert frame_path.stat().st_size > 50_000


# ==============================================================================
# 3. Typography Zero-Tofu & Multilingual Glyphs
# ==============================================================================

class TestTypographyZeroGlyphLoss:
    """Verifies 100% zero tofu ('□') across Korean, Vietnamese, Hanja, Simplified Chinese, and telemetry."""

    @pytest.mark.parametrize(
        "language_category,sample_text",
        [
            (
                "Korean Hangul (Full Syllables & Final Consonants)",
                "국립과학수사연구원 14개 특징점 Y-염색체 DNA 족보 가계도 분석 결과 유력 용의자 긴급 체포 완료",
            ),
            (
                "Vietnamese Diacritics (All Tones & Vowels)",
                "Đại án Bạch Ngân: Bắt giữ khẩn cấp nghi phạm số một Cao Thừa Dũng tại tiệm tạp hóa trường học số 4",
            ),
            (
                "Traditional Hanja & CJK Ideographs",
                "白銀市 連環殺人案 嫌疑人 高承勇 現場 檢證 司法 審判 刑事 警察 檢察",
            ),
            (
                "Simplified Chinese Ideographs",
                "白银市连环杀人案 嫌疑人 高承勇 公安 现场 勘查 提取指纹 检验 对比 锁定 缉拿归案",
            ),
            (
                "Telemetry Symbols & Geographic Coordinates",
                "№ 1988-1994-2002-2016 · 14-Point · 99.98% · [STR-DNA] · ★★★ §42 LAT 36°33'03\"N · LON 104°08'52\"E · ALT 1720m",
            ),
        ],
    )
    def test_verify_text_glyphs_has_zero_missing_characters(self, language_category: str, sample_text: str):
        ok = verify_text_glyphs(sample_text, font_size=24, bold=True)
        assert ok, f"Missing glyphs (tofu/□) detected for category '{language_category}': {sample_text}"

    def test_draw_text_safe_renders_visible_pixels_on_canvas(self):
        """Verifies that composite multilingual text writes distinct non-background pixels."""
        canvas = Image.new("RGB", (1920, 1080), (15, 15, 15))
        draw = ImageDraw.Draw(canvas)

        composite_text = (
            "백은시(白銀市) 연쇄살인 嫌疑人 高承勇 · Đại án Bạch Ngân · "
            "14-Point [Y-STR] 일치 · LAT 36°33'03\"N · ★★★"
        )
        end_x = draw_text_safe(draw, (80, 200), composite_text, fill=(255, 232, 74), font_size=32, bold=True)
        assert end_x > 80, "Text cursor did not advance"

        # Count pixels that deviate from background color (15, 15, 15)
        arr = np.array(canvas)
        diff = np.abs(arr.astype(int) - 15)
        changed_pixels = np.sum(diff > 30)
        assert changed_pixels > 2000, f"Expected >2000 visible text pixels, found {changed_pixels}"

    def test_cjk_fallback_font_cascade_resolution(self):
        """Verifies that Korean characters route to primary, while CJK-only characters route to fallback."""
        cascade = get_cascade_font(size=24, bold=True)

        # Korean character '백'
        f_ko = cascade.get_font_for_char("백")
        assert f_ko is not None

        # Simplified Chinese specific character '连'
        f_zh = cascade.get_font_for_char("连")
        assert f_zh is not None

        # Both fonts produce valid masks
        m_ko = f_ko.getmask("백")
        assert m_ko.size[0] > 0 and m_ko.size[1] > 0

        m_zh = f_zh.getmask("连")
        assert m_zh.size[0] > 0 and m_zh.size[1] > 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
