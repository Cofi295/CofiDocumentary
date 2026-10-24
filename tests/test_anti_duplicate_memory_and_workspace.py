"""
End-to-End & Unit Verification Test Suite for:
1. 2-Layer Anti-Duplicate Topic Memory & Pre-Flight System (AC1)
2. True Reference Image Fidelity & Job Workspace Persistence (AC2)
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from documentary.ai_visual import AIVisualCoordinator
from documentary.service import DocumentaryService
from documentary.visuals import _prompt_for
from server import create_app
from services.case_similarity import check_case_similarity, is_duplicate_case

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def app_client() -> TestClient:
    app = create_app()
    with TestClient(app) as client:
        yield client


class TestAntiDuplicateTopicMemoryAndPreflight:
    """Verifies AC1: 2-layer anti-duplicate topic memory and pre-flight check."""

    def test_topic_memory_crud_api(self, app_client: TestClient) -> None:
        profile_id = "channel-e544a64b7c"

        # 1. GET topic memory
        resp = app_client.get(f"/api/radar/channel-profiles/{profile_id}/topic-memory")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert data["count"] >= 2

        # Check backfilled entries for Baiyin and Lao Rongzhi
        titles = [item.get("title", "") for item in data["items"]]
        assert any("라오룽즈" in t or "Lao Rongzhi" in t or "신분을 세탁" in t for t in titles)
        assert any("바이인" in t or "Baiyin" in t or "학교 매점" in t for t in titles)

        # 2. POST add new topic memory
        new_topic = {
            "title": "24년간 땅속에 숨겨진 붉은 장미 — 중국 최대 은행 금고 증발 사건",
            "topic": "중국 최대 은행 지점장 3인의 20년 해외 도피극",
            "source": "manual_test",
        }
        add_resp = app_client.post(f"/api/radar/channel-profiles/{profile_id}/topic-memory", json=new_topic)
        assert add_resp.status_code == 200, add_resp.text
        add_data = add_resp.json()
        assert add_data["status"] == "ok"
        entry = add_data["entry"]
        assert entry["id"]
        assert entry["title"] == new_topic["title"]
        assert len(entry.get("tags", [])) > 0

        # 3. DELETE topic memory entry
        del_resp = app_client.delete(f"/api/radar/channel-profiles/{profile_id}/topic-memory/{entry['id']}")
        assert del_resp.status_code == 200, del_resp.text
        del_data = del_resp.json()
        assert del_data["status"] == "ok"
        assert del_data["deleted_entry_id"] == entry["id"]

    def test_topic_discovery_strictly_excludes_produced_cases(self) -> None:
        doc_service = DocumentaryService(ROOT)
        profile_id = "channel-e544a64b7c"

        result = doc_service.channel_profile_today(profile_id, target_duration_minutes=30)
        candidates = result.get("today") or result.get("candidates") or []
        assert len(candidates) >= 4, f"Expected at least 4 candidates, got {len(candidates)}"

        for cand in candidates:
            cand_title = cand.get("title", "")
            # Assert Baiyin (Job 20261019-185102-31983814) is NOT returned
            is_baiyin = is_duplicate_case(
                cand_title,
                "28년간 학교 매점 아저씨로 숨어 지낸 '바이인시 미제 사건'의 진범"
            )
            assert not is_baiyin, f"Produced Baiyin case leaked into today candidates: {cand_title}"

            # Assert Lao Rongzhi (Job 20261017-164519-fd65f7e1) is NOT returned
            is_lao = is_duplicate_case(
                cand_title,
                "20년간 신분을 세탁한 '미소의 악마' — 라오룽즈 사건"
            )
            assert not is_lao, f"Produced Lao Rongzhi case leaked into today candidates: {cand_title}"

            # Assert candidate is flagged as unproduced
            assert cand.get("already_produced") is False

    def test_two_layer_preflight_check(self, app_client: TestClient) -> None:
        profile_id = "channel-e544a64b7c"

        # Case A: Duplicate check on produced Baiyin case
        baiyin_query = "28년간 학교 매점 아저씨로 숨어 지낸 바이인시 연쇄살인 사건"
        resp = app_client.get(
            f"/api/radar/channel-profiles/{profile_id}/preflight-check",
            params={"stage": "topic", "topic": baiyin_query, "title": baiyin_query}
        )
        assert resp.status_code == 200, resp.text
        summary = resp.json().get("preflight_summary", {})

        assert summary.get("duplicate_risk") is True
        assert summary.get("passed") is False

        # Pass 2 must catch memory duplicate
        mem_check = summary.get("profile_memory_check", {})
        assert mem_check.get("duplicate_found") is True
        assert mem_check.get("matched_job_id") == "20261019-185102-31983814"

        # Case B: Clean check on fresh, unproduced topic
        fresh_query = "태양광 발전 패널의 수명 종료와 2030년 글로벌 폐기물 위기"
        resp2 = app_client.get(
            f"/api/radar/channel-profiles/{profile_id}/preflight-check",
            params={"stage": "topic", "topic": fresh_query, "title": fresh_query}
        )
        assert resp2.status_code == 200, resp2.text
        summary2 = resp2.json().get("preflight_summary", {})
        assert summary2.get("duplicate_risk") is False
        assert summary2.get("profile_memory_check", {}).get("duplicate_found") is False


class TestReferenceImageFidelityAndWorkspacePersistence:
    """Verifies AC2: True reference image fidelity and job workspace persistence."""

    def test_job_service_workspace_initialization_and_sync(self, app_client: TestClient) -> None:
        # 1x1 transparent png data url
        tiny_png = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
            "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
        job_payload = {
            "title": "테스트 프로젝트 — 100% Xanh tiền & Workspace Kiểm thử",
            "topic": "Hồ sơ kiểm thử workspace và ảnh tham chiếu",
            "channel_profile_id": "channel-e544a64b7c",
            "market": "KR",
            "language": "ko",
            "target_duration_minutes": 5,
            "visual_strategy": "full_ai",
            "ai_media_mode": "image",
            "ai_visual": {
                "style_mode": "custom",
                "custom_style": "Minimalist yellow character animation with clean ink line art",
            },
            "reference_image_data_url": tiny_png,
            "reference_image_name": "yellow_character_sample.png",
        }

        resp = app_client.post("/api/jobs", json=job_payload)
        assert resp.status_code == 200, resp.text
        job = resp.json()

        job_id = job.get("id")
        assert job_id
        workspace_path = job.get("workspace")
        assert workspace_path and Path(workspace_path).is_dir()
        ws_dir = Path(workspace_path)

        try:
            # Verify required workspace files exist
            assert (ws_dir / "input.json").is_file()
            assert (ws_dir / "creative_brief.json").is_file()
            assert (ws_dir / "outline.json").is_file()
            assert (ws_dir / "ai_visual_settings.json").is_file()

            # Verify style reference image was saved
            ref_image = ws_dir / "media" / "style_reference" / "yellow_character_sample.png"
            assert ref_image.is_file()
            assert ref_image.stat().st_size > 0

            # Verify style_mode was not overwritten to stickman preset
            ai_visual = job.get("ai_visual") or {}
            assert ai_visual.get("style_mode") == "custom"
            assert ai_visual.get("style_preset") != "Người que (Stickman)"

            # Verify job was synced to profile topic memory
            mem_resp = app_client.get("/api/radar/channel-profiles/channel-e544a64b7c/topic-memory")
            assert mem_resp.status_code == 200
            mem_items = mem_resp.json().get("items", [])
            matched_mem = [item for item in mem_items if item.get("job_id") == job_id]
            assert len(matched_mem) >= 1
        finally:
            import shutil
            mem_resp = app_client.get("/api/radar/channel-profiles/channel-e544a64b7c/topic-memory")
            if mem_resp.status_code == 200:
                for item in mem_resp.json().get("items", []):
                    if item.get("job_id") == job_id and item.get("id"):
                        app_client.delete(f"/api/radar/channel-profiles/channel-e544a64b7c/topic-memory/{item['id']}")
            shutil.rmtree(ws_dir, ignore_errors=True)
            shutil.rmtree(ROOT / "data" / "jobs" / str(job_id), ignore_errors=True)

    def test_repaired_job_31983814_integrity(self) -> None:
        ws_dir = ROOT / "workspaces" / "20261019-185102-31983814"
        assert ws_dir.is_dir(), "Workspace for repaired job 20261019-185102-31983814 must exist"

        # Check essential files
        assert (ws_dir / "input.json").is_file()
        assert (ws_dir / "creative_brief.json").is_file()
        assert (ws_dir / "ai_visual_settings.json").is_file()
        assert (ws_dir / "script.md").is_file()
        assert (ws_dir / "subtitles.srt").is_file()

        # Check job store entry
        job_file = ROOT / "data" / "jobs" / "20261019-185102-31983814" / "job.json"
        assert job_file.is_file()
        job_data = json.loads(job_file.read_text(encoding="utf-8"))

        ai_visual = job_data.get("ai_visual") or {}
        assert ai_visual.get("style_mode") == "custom"
        assert ai_visual.get("style_preset") != "Người que (Stickman)"

        ref_img_path = job_data.get("style_reference_image") or ai_visual.get("style_reference_image")
        assert ref_img_path
        assert Path(ref_img_path).is_file()

    def test_ai_visual_prompt_reference_fidelity(self) -> None:
        sample_ref = ROOT / "workspaces" / "20261019-185102-31983814" / "media" / "style_reference" / "style_reference.png"
        assert sample_ref.is_file(), f"Reference image {sample_ref} must exist"
        ref_path = str(sample_ref)

        # 1. documentary.visuals._prompt_for
        unit = "형사들이 그의 두 팔을 붙잡아 제압했을 때, 가오청융은 단 한마디의 항의도 보이지 않았습니다."
        metadata = {
            "visual_description": "Nhân vật vàng đứng quan sát hiện trường",
            "purpose": "hook_paradox",
            "framing_motion_intent": "Slow cinematic pan",
        }
        style_settings = {
            "style_mode": "custom",
            "style_prompt": "Cold Forensic Noir with yellow character",
            "style_reference_image": ref_path,
        }
        prompt_vp = _prompt_for(unit, metadata, "ai_visual", style_settings=style_settings)
        prompt_vp_lower = prompt_vp.lower()

        assert "white rounded full-body stickman" not in prompt_vp_lower
        assert "white marshmallow mascot" not in prompt_vp_lower
        assert "attached reference image" in prompt_vp_lower
        assert "exact character colors" in prompt_vp_lower

        # 2. AIVisualCoordinator._prompt
        ai_service = AIVisualCoordinator()
        card = {
            "beat_id": "b01",
            "visual_description": "Nhân vật màu vàng đang đi bộ",
            "narration_text": "단 한마디의 항의도 보이지 않았습니다.",
            "purpose": "hook_paradox",
            "framing_motion_intent": "Cinematic pan",
        }
        prompt_ai = ai_service._prompt(
            card,
            aspect_ratio="16:9",
            preset_prompt="Yellow skin character with black lineart",
            has_style_reference=True,
        )
        prompt_ai_lower = prompt_ai.lower()

        assert "white rounded full-body stickman" not in prompt_ai_lower
        assert "white marshmallow mascot" not in prompt_ai_lower
        assert "reference image is attached" in prompt_ai_lower or "attached visual style reference image" in prompt_ai_lower
        assert "exact character colors" in prompt_ai_lower

    def test_ui_elements_present_in_static_files(self) -> None:
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        # UI Step 0 topic memory ledger
        assert "channelTopicMemorySection" in html
        assert "topicMemoryList" in html
        assert "addTopicMemoryBtn" in html
        assert "renderTopicMemoryList" in js

        # UI Step 00 style reference live preview
        assert "createStyleReferencePreviewContainer" in html
        assert "createStyleReferencePreviewImg" in html
        assert "createStyleReferenceBadge" in html
        assert "clearCreateStyleReferenceBtn" in html
        assert "clearCreateStyleReferenceBtn" in js
        assert "currentCreateStyleReferenceDataUrl" in js

        # Two-layer Pre-flight Pass 1 & Pass 2
        assert "Pass 1 (YouTube Kênh)" in js
        assert "Pass 2 (Bộ nhớ Hồ sơ)" in js
