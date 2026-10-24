import sys
import os
from pathlib import Path

# Ensure root is in path
ROOT = Path(r"B:\ALL_TOOLS\CofiDocumentary").resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from documentary.vox_engine import (
    VoxSemanticRouter,
    is_vox_satellite_enabled,
    VoxSceneRenderer,
    verify_text_glyphs,
    split_balanced_korean,
)

def test_channel_isolation():
    print("=== TEST 1: CHANNEL ISOLATION ===")
    assert is_vox_satellite_enabled({"channel_profile_id": "channel-e544a64b7c"}) is True
    assert is_vox_satellite_enabled({"channel_profile_id": "channel-1e24de3ab5"}) is False
    assert is_vox_satellite_enabled({"channel_profile_id": "channel-aa913eb90d"}) is False
    assert is_vox_satellite_enabled({"channel_profile_id": "channel-f6ec4dfff3"}) is False
    assert is_vox_satellite_enabled({"visual_strategy": "forensic_noir"}) is True
    assert is_vox_satellite_enabled({"visual_strategy": "true_crime_noir_ai"}) is True
    assert is_vox_satellite_enabled({"visual_strategy": "full_footage"}) is False
    print("PASS: Channel isolation strictness verified.")

def test_semantic_routing():
    print("\n=== TEST 2: SEMANTIC ROUTING (16 DIVERSE SENTENCES) ===")
    router = VoxSemanticRouter()
    test_cases = [
        ("Y-염색체 유전자 족보 추적을 통해 마침내 가오씨 가문의 부계 혈통으로 수사망이 좁혀졌습니다.", "#D4"),
        ("경찰은 학교 캠퍼스 매점 건물의 옥상과 지붕 주변을 신속하게 포위하고 급습을 감행했습니다.", "#M1"),
        ("해가 지면 반경 3km 이내의 밤거리는 적외선 감시와 함께 삼엄한 야간 통제 및 외출 금지가 내려졌습니다.", "#M7"),
        ("현미경 확대 검사 결과 14개 특징점이 완벽히 일치하여 단 하나의 지문으로 범인을 특정했습니다.", "#D9"),
        ("심문실에서 피의자는 자신의 범행을 자필 진술서와 차분한 목소리로 모두 시인하고 자백했습니다.", "#D5"),
        ("공안부는 20만 위안의 현상금과 함께 몽타주 스케치가 담긴 1급 수배령을 전국에 전파했습니다.", "#D6"),
        ("용의자는 간쑤성 란저우와 바이인시 경계선을 넘어 황하 강을 건너 행정구역 밖으로 도주로를 확보했습니다.", "#M3"),
        ("1990년대 당시 방송 뉴스 화면에서는 연쇄 사건에 대한 앵커의 긴급 보도자료가 연일 보도되었습니다.", "#P3"),
        ("그 후 28년이라는 긴 세월 동안 사건은 미제로 남은 채 깊은 침묵과 공백 속에 묻혀 있었습니다.", "#P1"),
        ("희생자의 어머니는 차가운 바닥에 주저앉아 오열하며 비통한 눈물로 말을 잇지 못했습니다.", "cinema_full"),
        ("Kết quả xét nghiệm ADN dòng họ và phả hệ gia tộc đã giúp khoanh vùng nghi phạm thuộc gia tộc họ Cao.", "#D4"),
        ("Lực lượng công an tiến hành bao vây tiệm tạp hóa trường học và đột kích bắt giữ đối tượng.", "#M1"),
        ("Lệnh truy nã đỏ cấp A cùng phác họa chân dung nghi phạm và 20 vạn tiền thưởng được công bố.", "#D6"),
        ("Dưới kính hiển vi, 14 điểm đặc trưng vân ngón tay hoàn toàn trùng khớp với dấu vết hiện trường.", "#D9"),
        ("Tại phòng thẩm vấn, nghi phạm đã thừa nhận toàn bộ tội ác trong bản cung và băng ghi âm lời khai.", "#D5"),
        ("Người mẹ nạn nhân gục ngã trong nước mắt đau đớn và thương tâm tột cùng.", "cinema_full"),
    ]

    for sentence, expected in test_cases:
        router.reset_history()
        decision = router.route_beat(sentence)
        actual = decision["archetype"]
        print(f"[{actual == expected}] '{sentence[:30]}...' -> {actual} (expected {expected}, score={decision['score']:.1f})")
        assert actual == expected, f"Mismatch for '{sentence}': got {actual}, expected {expected}"

    print("PASS: All 16 semantic routing test cases passed.")

def test_anti_repetition_mechanism():
    print("\n=== TEST 3: ANTI-REPETITION RECENCY PENALTY ===")
    router = VoxSemanticRouter()
    # Sentence with both fingerprint (#D1) and minutiae comparator (#D9) keywords
    sentence_a = "지문 대조 결과 14개 특징점 현미경 일치"
    
    # First time:
    d1 = router.route_beat(sentence_a)
    print(f"Beat 1: {d1['archetype']} (score={d1['score']:.1f})")
    
    # Second time with identical input: history has Beat 1
    d2 = router.route_beat(sentence_a)
    print(f"Beat 2 (same tokens): {d2['archetype']} (score={d2['score']:.1f})")
    assert d2["archetype"] != d1["archetype"], f"Expected anti-repetition to rotate, but got {d2['archetype']} twice in a row!"
    print("PASS: Sliding-window recency penalty prevents identical back-to-back archetypes.")

def test_typography_and_tofu():
    print("\n=== TEST 4: TYPOGRAPHY CASCADE & GLYPH VERIFICATION ===")
    test_texts = [
        "28년간 학교 매점 주인으로 숨어 지낸 중국 최악의 연쇄살인범",
        "간쑤성 바이인시 중급인민법원 형사판결문 (2017) 감04형초 제18호",
        "피고인: 가오청융 (高承勇) - 사형(死刑) 선고",
        "Kẻ sát nhân nguy hiểm nhất ẩn mình 28 năm làm chủ tiệm tạp hóa",
        "Xét nghiệm Y-STR ADN dòng họ phả hệ 14 điểm đặc trưng",
    ]
    for text in test_texts:
        res = verify_text_glyphs(text, font_size=24, bold=True)
        print(f"Glyph check '{text[:25]}...': {res}")
        assert res is True, f"Glyph check failed for '{text}'"

    lines = split_balanced_korean("28년간 학교 매점 주인으로 숨어 지낸 중국 최악의 연쇄살인범", max_chars=20)
    print(f"Balanced split: {lines}")
    assert len(lines) == 2
    print("PASS: Typography fallback cascade and balanced wrapping verified with 0 tofu.")

def test_scene_rendering():
    print("\n=== TEST 5: SCENE RENDERING EXECUTION (1920x1080) ===")
    renderer = VoxSceneRenderer()
    sample_archetypes = ["#M1", "#M7", "#D4", "#D9", "#P3", "cinema_full"]
    out_dir = ROOT / ".agents" / "teamwork" / "auditor_integrity" / "rendered_samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    for arch in sample_archetypes:
        out_file = out_dir / f"test_{arch.replace('#', '')}.jpg"
        img = renderer.render_frame(
            archetype_id=arch,
            progress=0.8,
            subtitle_text="테스트 자막: 28년 만에 lật mở đại án Bạch Ngân (高承勇)",
            out_path=out_file,
        )
        print(f"Rendered {arch}: size={img.size}, mode={img.mode}, saved to {out_file.name}")
        assert img.size == (1920, 1080), f"Invalid size {img.size} for {arch}"
        assert out_file.exists() and out_file.stat().st_size > 50000, f"File {out_file} invalid or too small"

    print("PASS: Real 1920x1080 frame rendering verified for all sample archetypes.")

if __name__ == "__main__":
    try:
        test_channel_isolation()
        test_semantic_routing()
        test_anti_repetition_mechanism()
        test_typography_and_tofu()
        test_scene_rendering()
        print("\n==============================================")
        print("ALL EMPIRICAL INTEGRITY TESTS PASSED SUCCESSFULLY!")
        print("==============================================")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
