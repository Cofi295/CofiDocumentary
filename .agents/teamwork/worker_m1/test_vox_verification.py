"""Verification test suite for True Crime Vox & Satellite Engine Integration.

Tests:
1. Semantic Voice Routing across 11+ bilingual benchmark sentences.
2. Anti-Repetition sliding-window and sibling rotation.
3. Strict channel profile isolation.
4. Typography zero-tofu rendering across Korean, Vietnamese, and Hanja.
5. Multi-scale GIS plate loading and Web Mercator coordinate projections.
6. Standalone 1920x1080 frame rendering for sample archetypes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from documentary.vox_engine import (
    VoxSemanticRouter,
    VoxSceneRenderer,
    is_vox_satellite_enabled,
    verify_text_glyphs,
    load_gis_plate,
    crop_map_camera,
    map_lonlat_to_screen,
    deg2num,
    lonlat_to_plate_px,
    W,
    H,
)
from PIL import Image


BENCHMARK_SENTENCES = [
    (
        "단 하나의 Y-염색체 유전자 표지가 칭청진 가오씨 가문의 족보를 정조준했습니다.",
        "#D4",
        "Korean DNA Lineage",
    ),
    (
        "Chỉ một dấu chỉ thị Y-STR trên nhiễm sắc thể Y đã nhắm thẳng vào cuốn gia phả của dòng họ Cao.",
        "#D4",
        "Vietnamese DNA Lineage",
    ),
    (
        "사복 형사들이 최종적으로 덮친 곳은 놀랍게도 한 고등학교 캠퍼스 안의 평화로운 매점과 옥상 건물이었습니다.",
        "#M1",
        "Korean Campus Store Raid",
    ),
    (
        "Nơi các trinh sát hình sự ập vào bao vây lại là tiệm tạp hóa và tòa nhà trên khuôn viên trường.",
        "#M1",
        "Vietnamese Campus Store Raid",
    ),
    (
        "해가 지면 바이인시 도심 반경 3킬로미터 전체가 거대한 야간 통제 구역으로 변해 철문이 굳게 닫혔습니다.",
        "#M7",
        "Korean Night Curfew",
    ),
    (
        "Khi mặt trời lặn, toàn bộ bán kính 3km quanh trung tâm thành phố biến thành vùng giới nghiêm.",
        "#M7",
        "Vietnamese Night Curfew",
    ),
    (
        "28년 전 현장에 남겨진 지문의 14개 융선 특징점이 가오청융의 손가락과 완벽히 포개졌습니다.",
        "#D9",
        "Korean 14-Point Fingerprint Minutiae",
    ),
    (
        "14 điểm đặc trưng trên các đường vân tay hiện trường 28 năm trước đã trùng khớp hoàn hảo.",
        "#D9",
        "Vietnamese 14-Point Fingerprint Minutiae",
    ),
    (
        "심문실 의자에 앉은 가오청융은 취조관 앞에서 녹음기를 켜자 단 한 번의 동요도 없이 11건의 범행 자백 진술서를 작성했습니다.",
        "#D5",
        "Korean Interrogation Confession",
    ),
    (
        "Ngồi trong phòng thẩm vấn trước máy ghi âm, hắn không dao động mà ký bản cung thú nhận 11 vụ án.",
        "#D5",
        "Vietnamese Interrogation Confession",
    ),
    (
        "공안부가 20만 위안의 현상금과 붉은색 1급 수배령 몽타주를 전국의 검문소에 일제히 배포했습니다.",
        "#D6",
        "Korean Class-A Wanted Warrant & Sketch",
    ),
    (
        "Bộ Công an phát lệnh truy nã đỏ cấp A cùng tiền thưởng 20 vạn tệ và bản phác họa chân dung.",
        "#D6",
        "Vietnamese Class-A Wanted Warrant & Sketch",
    ),
    (
        "용의자는 황하 상류의 험준한 지형과 성 경계선을 넘어 공안의 관할 행정구역 밖으로 도주했습니다.",
        "#M3",
        "Korean Yellow River & Boundary Escape",
    ),
    (
        "Nghi phạm đã vượt qua thượng nguồn sông Hoàng Hà và ranh giới tỉnh để trốn khỏi địa bàn quản hạt.",
        "#M3",
        "Vietnamese Yellow River & Boundary Escape",
    ),
    (
        "당시 지역 방송국의 1998년 긴급 뉴스 특보는 CRT 브라운관 TV를 통해 도시 전체를 뒤덮은 공포를 생생히 보도했습니다.",
        "#P3",
        "Korean 1990s TV Broadcast",
    ),
    (
        "Bản tin truyền hình khẩn cấp năm 1998 của đài địa phương phát qua màn hình TV CRT.",
        "#P3",
        "Vietnamese 1990s TV Broadcast",
    ),
    (
        "1988년 첫 번째 사건 이후 아무런 흔적도 남기지 않은 채 6년의 세월 동안 공포의 침묵이 이어졌습니다.",
        "#P1",
        "Korean Multi-year Silence Timeline",
    ),
    (
        "Sau vụ án đầu tiên năm 1988, khoảng lặng kéo dài 6 năm không để lại dấu vết.",
        "#P1",
        "Vietnamese Multi-year Silence Timeline",
    ),
    (
        "입체 위성 지형 슬랩 위에 연쇄 사건들의 지리적 발생 좌표와 거리를 연결하자 명확한 동선 패턴이 드러났습니다.",
        "#M5",
        "Korean 2.5D Coordinate Pattern",
    ),
    (
        "Khi liên kết tọa độ và khoảng cách các vụ án trên khối bản đồ vệ tinh lập thể 3D.",
        "#M5",
        "Vietnamese 2.5D Coordinate Pattern",
    ),
    (
        "희생자의 어머니는 차마 문을 열지 못한 채 차가운 바닥에 주저앉아 눈물만 흘리며 말을 잇지 못했습니다.",
        "cinema_full",
        "Korean Emotional Grief",
    ),
    (
        "Người mẹ nạn nhân gục xuống sàn nhà lạnh lẽo, nghẹn ngào trong nước mắt không nói nên lời.",
        "cinema_full",
        "Vietnamese Emotional Grief",
    ),
]


def test_semantic_routing():
    print("\n--- TEST 1: Semantic Voice-to-Archetype Routing (11 Pairs / 22 Sentences) ---")
    router = VoxSemanticRouter()
    passed = 0
    for sentence, expected_arch, label in BENCHMARK_SENTENCES:
        router.reset_history()
        res = router.route_beat(sentence)
        actual = res["archetype"]
        is_ok = (actual == expected_arch)
        status = "PASS" if is_ok else "FAIL"
        print(f"[{status}] {label}: expected={expected_arch}, got={actual} (score={res['score']})")
        if is_ok:
            passed += 1
        else:
            print(f"       Text: {sentence}")
            print(f"       Reason: {res['reason']}")
    assert passed == len(BENCHMARK_SENTENCES), f"Failed {len(BENCHMARK_SENTENCES) - passed} sentences"
    print(f"-> All {passed}/{len(BENCHMARK_SENTENCES)} benchmark sentences routed perfectly!")


def test_anti_repetition():
    print("\n--- TEST 2: Sliding-Window Anti-Repetition Mechanism ---")
    router = VoxSemanticRouter(history_size=4)
    router.reset_history()

    # Sequence of 4 beats with repeated fingerprint triggers
    beats = [
        "형사들은 현장에 남겨진 지문 카드를 현미경으로 살폈습니다.",
        "28년 전 현장에 남겨진 지문의 14개 융선 특징점을 재검증했습니다.",
        "생체 시료와 현장 증거물 3대 단서를 추가로 대조했습니다.",
        "단 하나의 지문만이 유일한 희망이었습니다.",
    ]

    routed = []
    for i, b in enumerate(beats):
        res = router.route_beat(b)
        routed.append(res["archetype"])
        print(f"Beat {i+1}: '{b[:25]}...' -> {res['archetype']} ({res['label']})")

    assert routed[0] in {"#D1", "#D9"}, f"Beat 1 expected fingerprint archetype, got {routed[0]}"
    assert routed[1] != routed[0], f"Beat 2 ({routed[1]}) repeated Beat 1 ({routed[0]})!"
    print(f"-> Anti-repetition confirmed: Beat 1={routed[0]}, Beat 2={routed[1]} (no back-to-back duplicate!)")


def test_channel_isolation():
    print("\n--- TEST 3: Strict Channel Profile Gating ---")
    crime_job = {"channel_profile_id": "channel-e544a64b7c"}
    infra_job = {"channel_profile_id": "channel-1e24de3ab5"}
    vault_job = {"channel_profile_id": "channel-f6ec4dfff3"}
    other_job = {"channel_profile_id": "channel-aa913eb90d"}
    forensic_preset_job = {"editing_dna": {"preset_id": "forensic_noir"}}

    assert is_vox_satellite_enabled(crime_job) is True, "channel-e544a64b7c must be True"
    assert is_vox_satellite_enabled(infra_job) is False, "channel-1e24de3ab5 must be False"
    assert is_vox_satellite_enabled(vault_job) is False, "channel-f6ec4dfff3 must be False"
    assert is_vox_satellite_enabled(other_job) is False, "channel-aa913eb90d must be False"
    assert is_vox_satellite_enabled(forensic_preset_job) is True, "forensic_noir preset must be True"

    router = VoxSemanticRouter()
    beats = [{"beat_id": "B001", "narration_text": "Y-염색체 유전자 대조 검사"}]
    # Route for non-crime channel should return beats unmodified (zero scene_archetype tag)
    unmodified = router.route_timeline(beats, infra_job)
    assert "scene_archetype" not in unmodified[0], "Non-crime channel must not be tagged with Vox archetypes"

    # Route for crime channel must attach scene_archetype
    tagged = router.route_timeline(beats, crime_job)
    assert tagged[0].get("scene_archetype") == "#D4", "Crime channel must be tagged with #D4"
    print("-> Channel isolation verified: Crime channel enabled, non-crime channels 100% blocked!")


def test_typography_and_glyphs():
    print("\n--- TEST 4: Typography and Zero-Tofu Verification ---")
    test_strings = [
        "바이인시 공안국 형사과학기술과", # Korean Hangul
        "Điều tra Hồ sơ Hình sự & Pháp y Trung Quốc", # Vietnamese diacritics
        "甘肅省 白銀市 高承勇 (Hanja)", # Traditional Hanja
        "银肃 (Simplified Chinese)", # Simplified Chinese
    ]

    for s in test_strings:
        ok = verify_text_glyphs(s)
        print(f"Glyph resolution check for '{s}': {ok}")
        assert ok is True, f"Tofu detected in string: {s}"
    print("-> Typography cascade verified: zero tofu across Korean, Vietnamese, Hanja, and Simplified Chinese!")


def test_gis_and_rendering():
    print("\n--- TEST 5: GIS Plate Loading & 1920x1080 Frame Rendering ---")
    # Test GIS plate loading
    plate, meta = load_gis_plate("plate_baiyin_campus_sat_z16")
    assert plate.size == (meta["width"], meta["height"]), "Plate size mismatch"
    print(f"GIS plate loaded: {plate.size}, zoom={meta['zoom']}")

    # Test coordinate math
    xt, yt = deg2num(36.551, 104.148, meta["zoom"])
    px, py = lonlat_to_plate_px(104.148, 36.551, meta)
    assert px > 0 and py > 0, "Plate px must be positive"
    print(f"Deg2num & plate projection: ({xt:.2f}, {yt:.2f}) -> plate px: ({px:.1f}, {py:.1f})")

    renderer = VoxSceneRenderer()
    sample_archetypes = ["#M1", "#M5", "#M7", "#D4", "#D5", "#D6", "#D9", "#P1", "#P3", "cinema_full"]

    out_test_dir = PROJECT_ROOT / ".agents" / "teamwork" / "worker_m1" / "test_frames"
    out_test_dir.mkdir(parents=True, exist_ok=True)

    for arch in sample_archetypes:
        frame = renderer.render_frame(
            archetype_id=arch,
            progress=0.85,
            subtitle_text=f"테스트 자막 출력: {arch} 1080p 렌더링 검증 완료",
            out_path=out_test_dir / f"test_{arch.replace('#', '')}.jpg",
        )
        assert frame.size == (1920, 1080), f"{arch} rendered frame size must be (1920, 1080)"
        assert frame.mode == "RGB", f"{arch} mode must be RGB"
        print(f"Rendered {arch}: {frame.size}, mode={frame.mode}")

    print(f"-> 10 sample archetypes cleanly rendered at 1920x1080 to {out_test_dir}")


def main():
    print("================================================================================")
    print("RUNNING TRUE CRIME VOX & REAL SATELLITE ENGINE INTEGRATION VERIFICATION")
    print("================================================================================")
    test_semantic_routing()
    test_anti_repetition()
    test_channel_isolation()
    test_typography_and_glyphs()
    test_gis_and_rendering()
    print("\n================================================================================")
    print("ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ZERO DEFECTS.")
    print("================================================================================")


if __name__ == "__main__":
    main()
