from pathlib import Path
from PIL import Image

from documentary.thumbnail_studio import (
    build_default_thumbnail_design,
    discover_job_candidate_images,
    enforce_seo_package_expert_rules,
    sanitize_youtube_policy_text,
    sync_thumbnail_design_with_seo_pack,
)


def test_sanitize_youtube_policy_text_removes_sensitive_terms():
    raw_ko = "[중국 실화 사건] 연쇄살인사건 살인마가 시체를 숨긴 충격 현장"
    cleaned_ko, hits_ko = sanitize_youtube_policy_text(raw_ko)
    assert "연쇄살인사건" not in cleaned_ko
    assert "살인마" not in cleaned_ko
    assert "시체" not in cleaned_ko
    assert "최악의 미제사건" in cleaned_ko
    assert "1급 수배범" in cleaned_ko
    assert len(hits_ko) >= 3

    raw_vi = "Kẻ sát nhân giết người hàng loạt phi tang xác chết"
    cleaned_vi, hits_vi = sanitize_youtube_policy_text(raw_vi)
    assert "sát nhân" not in cleaned_vi.lower()
    assert "giết người" not in cleaned_vi.lower()
    assert "xác chết" not in cleaned_vi.lower()
    assert len(hits_vi) >= 3


def test_enforce_seo_package_expert_rules_locks_primary_keyword_and_policy():
    job = {
        "id": "job-test-expert",
        "language": "ko",
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "primary_title_keyword_meaning_vi": "Vụ Án Có Thật ở Trung Quốc",
            "keyword_placement_rule": "smart_seo_flexible",
            "mandatory_hashtags": ["#중국실화사건", "#특급수배록"],
        },
    }
    seo_pack = {
        "generated_at": "2026-10-20T13:30:00Z",
        "recommended_title": "13년 잠적한 살인범이 인기 배우였다니 | 길광 도주 사건",
        "title_options": [
            "13년 잠적한 살인범이 인기 배우였다니 | 길광 도주 사건",
            "[중국에서 있었던 실제 사례] 연쇄살인사건 용의자의 두 얼굴 | 길광 사건",
        ],
        "description": "이 영상은 살인사건 현장의 시체 단서를 추적합니다.",
        "keywords": ["살인범", "길광 사건"],
        "tags": ["살인사건", "실화"],
        "hashtags": ["#실화"],
        "thumbnail": {
            "overlay_text": "살인범의 두 얼굴\n충격 정체!",
            "overlay_text_options": [
                {
                    "badge": "중국 실화 사건",
                    "line_1": "드라마 30편 명품 조연",
                    "line_2": "소름 돋는 진짜 정체!",
                }
            ],
        },
    }
    updated, changed = enforce_seo_package_expert_rules(seo_pack, job)
    assert changed is True
    assert updated["recommended_title"].startswith("[중국 실화 사건]")
    assert "살인범" not in updated["recommended_title"]
    for t in updated["title_options"]:
        assert "중국 실화 사건" in t
        assert "살인" not in t
    assert "살인" not in updated["description"]
    assert "시체" not in updated["description"]
    assert "#중국실화사건" in updated["hashtags"]
    assert updated["youtube_policy_guardrail"]["status"] == "GREEN_SAFE"
    assert updated["youtube_policy_guardrail"]["primary_title_keyword_locked"] == "중국 실화 사건"


def test_discover_candidates_and_sync_design_replaces_stale_text_and_style_ref(tmp_path: Path):
    ws = tmp_path / "ws"
    (ws / "media" / "style_reference").mkdir(parents=True)
    (ws / "media" / "ai").mkdir(parents=True)

    style_img = ws / "media" / "style_reference" / "style_reference.png"
    Image.new("RGB", (640, 360), (255, 255, 255)).save(style_img)

    ai_img = ws / "media" / "ai" / "B001-V01_ai_keyframe.png"
    Image.new("RGB", (1280, 720), (15, 25, 45)).save(ai_img)

    job = {"id": "job-sync", "language": "ko", "title": "[중국 실화 사건] 13년 잠적한 1급 수배범 | 길광 사건"}
    cands = discover_job_candidate_images("job-sync", ws, job)
    assert cands[0]["category"] == "ai_scene"
    assert cands[-1]["category"] == "style_reference"

    # Simulate a stale design created before seo_package.json existed
    stale_design = build_default_thumbnail_design("job-sync", ws, job, seo_pack={}, candidates=[cands[-1]])
    stale_design["variants"][0]["line_1"] = "28년 숨어 지낸 범인"
    stale_design["variants"][0]["line_2"] = "단 하나의 결정적 단서"
    stale_design["variants"][0]["background_path"] = "media/style_reference/style_reference.png"

    seo_pack = {
        "generated_at": "2026-10-20T14:00:00Z",
        "recommended_title": "[중국 실화 사건] 13년 잠적한 1급 수배범이 인기 드라마 배우였다니 | 길광 도주 사건",
        "thumbnail": {
            "overlay_text_options": [
                {
                    "badge": "중국 실화 사건",
                    "line_1": "드라마 30편 명품 조연",
                    "line_2": "소름 돋는 진짜 정체!",
                    "paired_title": "[중국 실화 사건] 13년 잠적한 1급 수배범이 인기 드라마 배우였다니 | 길광 도주 사건",
                }
            ]
        },
    }

    synced = sync_thumbnail_design_with_seo_pack(stale_design, seo_pack, job, cands)
    assert synced is True
    assert stale_design["variants"][0]["line_1"] == "드라마 30편 명품 조연"
    assert stale_design["variants"][0]["line_2"] == "소름 돋는 진짜 정체!"
    assert "style_reference" not in stale_design["variants"][0]["background_path"]


def test_stickman_prompt_has_no_character_color_words(tmp_path: Path):
    from documentary.ai_visual import AIVisualCoordinator
    from documentary.visuals import _prompt_for

    ref_file = tmp_path / "style_reference.png"
    ref_file.write_bytes(b"fake-png")
    preset_prompt = AIVisualCoordinator._style_preset_prompt("Người que (Stickman)")
    assert preset_prompt
    assert "reference" in preset_prompt.lower()

    beat = {
        "beat_id": "B021-V01",
        "narration_text": "지나가던 행인을 상대로 현금과 귀중품을 빼앗으려던 노상 강도 일당이었습니다.",
        "visual_description": "In a snowy alley in Qiqihar, four street robbers surround a passerby.",
        "purpose": "Reconstruct the 1998 Qiqihar alley robbery.",
        "framing_motion_intent": "Tense medium-wide alley shot.",
    }
    ai_prompt = AIVisualCoordinator._prompt(
        beat,
        aspect_ratio="16:9",
        preset_prompt=preset_prompt,
        has_style_reference=True,
    )
    stp_prompt = _prompt_for(
        beat["narration_text"],
        beat,
        "ai_visual",
        style_settings={
            "style_mode": "preset",
            "style_preset": "Người que (Stickman)",
            "style_prompt": preset_prompt,
            "style_reference_image": str(ref_file),
        },
    )
    for forbidden in ("white head", "white stick", "golden-yellow", "#fdd835", "yellow skin", "black-line"):
        assert forbidden not in ai_prompt.lower()
        assert forbidden not in stp_prompt.lower()

