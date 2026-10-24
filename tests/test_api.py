from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json

from fastapi.testclient import TestClient

from app import create_app
from documentary.service import DocumentaryService
from documentary.store import JobStore


def test_importing_app_module_does_not_construct_default_documentary_service(monkeypatch) -> None:
    import documentary.service as service_module

    class ExplodingService:
        def __init__(self, *args, **kwargs):
            raise AssertionError("importing app.py must not construct the production service")

    monkeypatch.setattr(service_module, "DocumentaryService", ExplodingService)
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("cofi_documentary_import_probe", app_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert callable(module.app)


class NoopGateway:
    def run(self, job, phase, workspace, log_callback=None):
        raise AssertionError("gateway should not run in this API test")


class TranslationGateway:
    def __init__(self):
        self.calls = 0

    def run_prompt(self, prompt, workspace, label, log_callback=None, use_remotion_root=False):
        self.calls += 1
        return SimpleNamespace(
            returncode=0,
            last_message='t0@@@Bản dịch tiếng Việt',
            log_path=Path(workspace) / "translation.log",
        )


def test_ai_account_login_endpoint_delegates_to_service():
    class AccountService:
        def __init__(self):
            self.calls = []

        def ai_account_login(self, provider):
            self.calls.append(provider)
            return {"ok": True, "provider": provider, "action": "started"}

    service = AccountService()
    client = TestClient(create_app(service))

    response = client.post("/api/ai-accounts/codex/login")

    assert response.status_code == 200
    assert response.json()["provider"] == "codex"
    assert service.calls == ["codex"]


def test_ai_account_settings_endpoint_delegates_to_service():
    class AccountService:
        def __init__(self):
            self.calls = []

        def update_ai_account_settings(self, provider, payload):
            self.calls.append((provider, payload))
            return {"ok": True, "provider": provider, "model": payload.get("model") or ""}

    service = AccountService()
    client = TestClient(create_app(service))

    response = client.patch("/api/ai-accounts/gemini/settings", json={"model": "gemini-3.1-pro-high"})

    assert response.status_code == 200
    assert response.json()["model"] == "gemini-3.1-pro-high"
    assert service.calls == [("gemini", {"model": "gemini-3.1-pro-high"})]


def test_source_repair_status_endpoints_delegate_to_service():
    class RepairService:
        def list_source_repairs(self):
            return [{"id": "repair-1", "status": "running"}]

        def get_source_repair(self, repair_id):
            assert repair_id == "repair-1"
            return {"id": repair_id, "status": "fixed"}

    client = TestClient(create_app(RepairService()))

    assert client.get("/api/source-repairs").json()[0]["status"] == "running"
    assert client.get("/api/source-repairs/repair-1").json()["status"] == "fixed"


def test_api_creates_and_lists_job(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))

    response = client.post("/api/jobs", json={"title": "China debt", "language": "ko"})
    assert response.status_code == 200
    job = response.json()
    assert job["title"] == "China debt"

    listed = client.get("/api/jobs").json()
    assert listed[0]["id"] == job["id"]


def test_api_creates_job_in_selected_workspace_root_and_reports_size(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path / "app",
        store=JobStore(tmp_path / "app" / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))
    selected_root = tmp_path / "video-projects"

    response = client.post(
        "/api/jobs",
        json={"title": "Stored elsewhere", "workspace_root": str(selected_root)},
    )

    assert response.status_code == 200
    job = response.json()
    workspace = Path(job["workspace"])
    assert workspace.parent == selected_root.resolve()
    assert workspace.name == job["id"]
    assert workspace.joinpath("input.json").exists()
    assert job["storage_bytes"] >= workspace.joinpath("input.json").stat().st_size
    assert job["workspace_root"] == str(selected_root.resolve())


def test_deleting_job_removes_its_selected_workspace(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path / "app",
        store=JobStore(tmp_path / "app" / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    job = service.create_job({"title": "Delete custom", "workspace_root": str(tmp_path / "projects")})
    workspace = Path(job["workspace"])

    service.delete_job(job["id"])

    assert not workspace.exists()


def test_workspace_folder_picker_endpoint_delegates_to_service():
    class PickerService:
        def select_workspace_root(self):
            return {"path": r"B:\\Videos"}

    response = TestClient(create_app(PickerService())).post("/api/storage/select-folder")

    assert response.status_code == 200
    assert response.json() == {"path": r"B:\\Videos"}


def test_api_rejects_unknown_phase(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))
    job = client.post("/api/jobs", json={"title": "Topic"}).json()

    response = client.post(f"/api/jobs/{job['id']}/run/nope")
    assert response.status_code == 400


def test_api_exposes_export_progress(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))
    job = client.post("/api/jobs", json={"title": "Export progress"}).json()

    response = client.get(f"/api/jobs/{job['id']}/export-progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["percent"] == 0
    assert payload["stage"] == "waiting"


def test_job_media_serves_only_files_inside_job_workspace(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))
    job = client.post("/api/jobs", json={"title": "Media job"}).json()
    workspace = Path(job["workspace"])
    media = workspace / "media" / "still.jpg"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"fake-jpg")
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"outside")

    ok = client.get(f"/api/jobs/{job['id']}/media", params={"path": str(media)})
    blocked = client.get(f"/api/jobs/{job['id']}/media", params={"path": str(outside)})

    assert ok.status_code == 200
    assert ok.content == b"fake-jpg"
    assert blocked.status_code == 400


def test_chat_attachment_upload_accepts_png_and_serves_same_bytes(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))
    png = b"\x89PNG\r\n\x1a\n" + b"image-body"

    uploaded = client.post(
        "/api/chat-attachments",
        params={"filename": "frame.png"},
        content=png,
        headers={"Content-Type": "image/png"},
    )

    assert uploaded.status_code == 200
    attachment = uploaded.json()
    assert attachment["name"] == "frame.png"
    assert attachment["mime_type"] == "image/png"
    assert attachment["size_bytes"] == len(png)
    assert "path" not in attachment
    served = client.get(attachment["url"])
    assert served.status_code == 200
    assert served.content == png


def test_chat_attachment_upload_rejects_non_image_payload(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))

    response = client.post(
        "/api/chat-attachments",
        params={"filename": "fake.png"},
        content=b"not-an-image",
        headers={"Content-Type": "image/png"},
    )

    assert response.status_code == 400


def test_live_footage_endpoint_hides_unapproved_downloads(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))
    job = client.post("/api/jobs", json={"title": "Live footage"}).json()
    workspace = Path(job["workspace"])
    media_root = workspace / "media" / "codex"
    (media_root / "_preview").mkdir(parents=True)
    (media_root / "B001_clip.mp4").write_bytes(b"video")
    (media_root / "B001_contact.jpg").write_bytes(b"contact-sheet")
    (media_root / "_preview" / "B001_preview.mp4").write_bytes(b"preview")

    response = client.get(f"/api/jobs/{job['id']}/live-footage")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 0
    assert payload["items"] == []


def test_live_footage_endpoint_ignores_internal_download_manifest(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    library_root = tmp_path / "footage-library"
    library_root.mkdir(parents=True)
    service.footage_coordinator.footage_engine.retriever.library_root = library_root
    client = TestClient(create_app(service))
    job = client.post("/api/jobs", json={"title": "Shared live footage"}).json()
    workspace = Path(job["workspace"])
    clip = library_root / "sources" / "source-a" / "windows" / "window-a" / "clip.mp4"
    clip.parent.mkdir(parents=True)
    clip.write_bytes(b"video-live")
    (workspace / "footage_live_downloads.json").write_text(json.dumps({
        "version": 1,
        "items": [{
            "beat_id": "B007",
            "path": str(clip),
            "source_url": "https://source.test/live",
            "name": "clip.mp4",
            "kind": "video",
        }],
    }), encoding="utf-8")

    response = client.get(f"/api/jobs/{job['id']}/live-footage")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 0
    assert payload["items"] == []


def test_live_footage_endpoint_lists_only_approved_selected_media(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))
    job = client.post("/api/jobs", json={"title": "Approved footage"}).json()
    workspace = Path(job["workspace"])
    approved = workspace / "media" / "vision" / "B007" / "FT-B007-02.mp4"
    approved.parent.mkdir(parents=True)
    approved.write_bytes(b"approved-video")
    (workspace / "footage_approved_live.json").write_text(json.dumps({
        "version": 1,
        "items": [{
            "candidate_id": "FT-B007-02",
            "beat_id": "B007",
            "path": str(approved),
            "source_url": "https://source.test/approved",
            "name": approved.name,
            "kind": "sourced_video",
            "reason": "Matches the voice beat exactly.",
            "decision": "ACCEPT",
        }],
    }), encoding="utf-8")

    response = client.get(f"/api/jobs/{job['id']}/live-footage")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["candidate_id"] == "FT-B007-02"
    assert payload["items"][0]["beat_id"] == "B007"
    assert payload["items"][0]["decision"] == "ACCEPT"
    assert payload["items"][0]["reason"] == "Matches the voice beat exactly."


def test_live_footage_endpoint_reports_partial_current_batch_progress_without_committing_checkpoint(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))
    job = client.post("/api/jobs", json={"title": "Live footage progress"}).json()
    workspace = Path(job["workspace"])
    checkpoint_path = workspace / "footage_checkpoint.json"
    checkpoint_path.write_text(json.dumps({
        "status": "running",
        "batch_size": 4,
        "completed_beats": 4,
        "total_beats": 8,
        "status_message": "Đang tìm tư liệu B005, B006, B007, B008 · batch 2/2",
        "workers": {"codex": {
            "assigned_beat_ids": [f"B{i:03d}" for i in range(1, 9)],
            "completed_beat_ids": [f"B{i:03d}" for i in range(1, 5)],
            "current_batch": 2,
            "total_batches": 2,
        }},
    }), encoding="utf-8")
    batch_dir = workspace / ".producer" / "footage_codex" / "batches"
    batch_dir.mkdir(parents=True)
    (batch_dir / "batch_0002.json").write_text(json.dumps({
        "worker": "codex",
        "status": "in_progress",
        "candidates": [
            {"candidate_id": "C-B005", "beat_id": "B005", "decision": "REVIEW"},
            {"candidate_id": "C-B006", "beat_id": "B006", "decision": "ACCEPT"},
        ],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }), encoding="utf-8")

    response = client.get(f"/api/jobs/{job['id']}/live-footage")

    assert response.status_code == 200
    payload = response.json()
    assert payload["progress"]["canonical_completed_beats"] == 4
    assert payload["progress"]["completed_beats"] == 6
    assert payload["progress"]["in_batch_completed_beat_ids"] == ["B005", "B006"]
    assert payload["progress"]["percent"] == 75
    stored = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert stored["completed_beats"] == 4
    assert stored["workers"]["codex"]["completed_beat_ids"] == ["B001", "B002", "B003", "B004"]


def test_live_footage_progress_exposes_stage_percent_separately_from_weighted_overall_percent(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))
    job = client.post("/api/jobs", json={"title": "Stage progress"}).json()
    workspace = Path(job["workspace"])
    (workspace / "footage_checkpoint.json").write_text(json.dumps({
        "status": "running",
        "completed_beats": 0,
        "total_beats": 271,
        "tool_progress": {
            "stage": "ranking",
            "completed_beats": 0,
            "total_beats": 271,
            "rank_completed": 147,
            "rank_total": 271,
        },
        "workers": {"codex": {"current_batch": 0, "total_batches": 68}},
    }), encoding="utf-8")

    payload = client.get(f"/api/jobs/{job['id']}/live-footage").json()

    assert payload["progress"]["percent"] == 25
    assert payload["progress"]["stage_percent"] == 54
    assert payload["progress"]["display_label"] == "SEMANTIC RANK"
    assert payload["progress"]["current_batch"] == 0


def test_footage_ui_shows_only_approved_media_while_phase_is_running() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")

    assert "/live-footage" in app_js
    assert "livePayload?.progress?.completed_beats" in app_js
    assert "FILE TẠM" not in app_js
    assert "ĐÃ DUYỆT" in app_js
    assert "Footage đã chọn" in app_js
    assert "Chuyển AI" in app_js
    assert "renderFootageWorkspace(current)" in app_js
    assert 'toolStage === "reviewing"' in app_js
    assert "stage_percent" in app_js


def test_ai_visual_ui_refreshes_generated_media_while_phase_is_running() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")

    assert 'state.appTab === "ai_visual" && current?.phases?.ai_visual?.status === "running"' in app_js
    assert "renderAIVisualWorkspace(current)" in app_js
    assert "Chi tiết kỹ thuật · AI Visual JSON" not in app_js
    assert "Veo không tạo được clip nên giữ ảnh:" not in app_js


def test_qc_player_preserves_video_node_during_live_progress_refresh() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")

    assert 'root.dataset.qcVideoUrl === videoUrl' in app_js
    assert 'root.dataset.qcStatus === qcStatus' in app_js
    assert 'const videoRevision = finalManifest.sha256' in app_js
    assert '&v=${encodeURIComponent(videoRevision)}' in app_js
    assert 'preload="auto"' in app_js


def test_radar_channel_cards_show_full_channel_identity_and_join_date() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")

    assert "function channelJoinDate" in app_js
    assert 'channel?.published_at || channel?.channel_published_at' in app_js
    assert 'channel.thumbnail_url || channel.avatar_url || channel.channel_thumbnail_url' in app_js
    assert 'Tạo <b>${escapeHtml(channelJoinDate(channel))}</b>' in app_js
    assert 'channel.total_videos' in app_js
    assert 'channel.country' in app_js


def test_radar_micro_results_use_scan_filters_and_clear_stale_results_while_scanning() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "static" / "app.js").read_text(encoding="utf-8")
    index_html = (root / "static" / "index.html").read_text(encoding="utf-8")

    assert "function syncMarketScanFormFromFeed" in app_js
    assert "KÊNH ĐẠT BỘ LỌC MICRO" in app_js
    assert 'feed.granularity' in app_js
    assert 'channelAgeDays(channel)' in app_js
    assert '$("#radarResults").innerHTML' in app_js
    assert "Đang quét lượt mới" in app_js
    assert "Tuổi kênh tối đa (ngày)" in index_html


def test_footage_ui_does_not_render_review_or_reject_candidates_as_usable_media_cards() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")

    assert "displayCandidates" in app_js
    assert "assetByCandidate.has" in app_js
    assert "reviewedLocalPaths" in app_js
    assert "Không đưa vào video · cần thay thế hoặc duyệt lại" not in app_js


def test_footage_ui_has_tools_first_run_pause_stop_and_retry_controls() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")

    assert 'data-footage-control="pause"' in app_js
    assert 'data-footage-control="stop"' in app_js
    assert 'data-footage-control="rerun"' in app_js
    assert "Chạy tìm bằng tools" in app_js
    assert "AI không tự research web" in app_js
    assert "/pipeline/footage/edit" not in app_js



def test_documentary_has_radar_import_and_resume_endpoints(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    app = create_app(service)
    routes = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if hasattr(route, "methods")}
    assert any(path == "/api/jobs/from-radar" and "POST" in methods for path, methods in routes)
    assert any(path == "/api/jobs/{job_id}/resume" and "POST" in methods for path, methods in routes)
    assert any(path == "/api/jobs/{job_id}/remotion" and "GET" in methods for path, methods in routes)
    assert any(path == "/api/jobs/{job_id}/footage/pause" and "POST" in methods for path, methods in routes)
    assert any(path == "/api/jobs/{job_id}/footage/resume" and "POST" in methods for path, methods in routes)
    assert any(path == "/api/jobs/{job_id}/footage/stop" and "POST" in methods for path, methods in routes)


def test_radar_translation_endpoint_uses_codex_and_caches_result(tmp_path: Path):
    gateway = TranslationGateway()
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=gateway,
        remotion_dir=tmp_path / "CofiRemotion",
    )
    client = TestClient(create_app(service))

    first = client.post("/api/radar/translate", json={"texts": ["Original title"]})
    second = client.post("/api/radar/translate", json={"texts": ["Original title"]})

    assert first.status_code == 200
    assert first.json()["translations"][0] == {"source": "Original title", "vi": "Bản dịch tiếng Việt"}
    assert second.json()["translations"][0]["vi"] == "Bản dịch tiếng Việt"
    assert gateway.calls == 1


def test_radar_market_scan_defaults_to_micro_niche_mode(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    service.radar_market_scan = lambda payload: payload
    client = TestClient(create_app(service))

    response = client.post("/api/radar/scans/market", json={"market": "US", "seeds": []})

    assert response.status_code == 200
    assert response.json()["niche_granularity"] == "micro"


def test_api_exposes_radar_niche_save_endpoint(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    captured = {}

    def fake_save(niche_id, note=None):
        captured["niche_id"] = niche_id
        captured["note"] = note
        return {"ok": True, "ref_id": str(niche_id)}

    service.radar_save_niche = fake_save
    client = TestClient(create_app(service))

    response = client.post("/api/radar/niches/17/save", json={"note": "Chốt để xây kênh"})

    assert response.status_code == 200
    assert response.json()["ref_id"] == "17"
    assert captured == {"niche_id": 17, "note": "Chốt để xây kênh"}


def test_radar_ui_has_ranked_top_five_and_save_niche_action() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")

    assert "ranked_candidates" in app_js
    assert "TOP 5 NGÁCH THỊ TRƯỜNG" in app_js
    assert "Lưu ngách để xây kênh" in app_js
    assert "/api/radar/niches/${encodeURIComponent(nicheId)}/save" in app_js


def test_codex_chat_ui_has_image_picker_preview_and_attachment_payloads() -> None:
    root = Path(__file__).resolve().parents[1]
    index_html = (root / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "static" / "app.js").read_text(encoding="utf-8")

    assert "producerCodexImageInput" in index_html
    assert "producerCodexAttachmentPreview" in index_html
    assert "editChatImageInput" in app_js
    assert "editChatAttachmentPreview" in app_js
    assert "attachment_ids" in app_js
    assert "/api/chat-attachments" in app_js


def test_codex_chat_supports_pasting_screenshot_images_from_clipboard() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "static" / "app.js").read_text(encoding="utf-8")

    assert "appendPastedChatImages" in app_js
    assert "event.clipboardData?.items" in app_js
    assert "input.onpaste = async event =>" in app_js
    assert '$("#editChatInput")?.addEventListener("paste"' in app_js


def test_global_codex_chat_is_available_on_every_tab_and_tracks_live_context() -> None:
    root = Path(__file__).resolve().parents[1]
    index_html = (root / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "static" / "app.js").read_text(encoding="utf-8")

    assert "globalCodexDock" in index_html
    assert "globalCodexMessages" in index_html
    assert "globalCodexInput" in index_html
    assert "globalCodexProgress" in index_html
    assert "renderGlobalProducerChat" in app_js
    assert "/api/producer-chat/context" in app_js
    assert "state.appTab" in app_js
    assert "globalCodexProgressHtml" in app_js


def test_app_startup_ensures_required_local_backends() -> None:
    class StartupService:
        def __init__(self):
            self.started = 0
            self.stopped = 0

        def start_required_backends(self):
            self.started += 1
            return {"cofi_voice": {"ok": True}, "cofi_radar": {"ok": True}}

        def stop_cofi_studio_embed(self):
            self.stopped += 1
            return {"ok": True}

    service = StartupService()
    api = create_app(service=service)

    with TestClient(api) as client:
        assert client.get("/").status_code == 200

    assert service.started == 1
    assert service.stopped == 1


def test_global_codex_progress_falls_back_to_overall_percent_when_live_percent_missing() -> None:
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "static" / "app.js").read_text(encoding="utf-8")

    assert "Number(live.percent ?? Number.NaN)" in app_js
    assert "Number(job.overall_percent ?? Number.NaN)" in app_js
    assert "`${overallPercent}%`" in app_js


def test_ai_visual_runtime_routes_drive_visible_controls() -> None:
    class RuntimeService:
        def ai_visual_runtime(self, job_id):
            return {"job": {"id": job_id}, "queue": {"paused": True}, "accounts": []}

        def ai_visual_test(self, job_id):
            return {"ok": True, "output_path": f"C:/outputs/{job_id}.png", "bytes": 123}

        def ai_visual_video_test(self, job_id):
            return {"ok": True, "output_path": f"C:/outputs/{job_id}.mp4", "bytes": 456}

        def ai_visual_runtime_queue(self, action):
            return {"paused": action == "pause"}

        def ai_visual_runtime_account(self, account_id, action):
            return {"id": account_id, "action": action}

    client = TestClient(create_app(RuntimeService()))

    assert client.get("/api/jobs/job-1/ai-visual-runtime").json()["queue"]["paused"] is True
    assert client.post("/api/jobs/job-1/ai-visual-test").json()["bytes"] == 123
    assert client.post("/api/jobs/job-1/ai-visual-video-test").json()["bytes"] == 456
    assert client.post("/api/cofi-studio/runtime/queue/resume").json()["paused"] is False
    assert client.post("/api/cofi-studio/runtime/accounts/acc-1/verify").json()["action"] == "verify"


def test_producer_chat_context_endpoint_returns_current_tab_and_progress(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    job = service.create_job({"title": "Context endpoint"})
    service.store.update(job["id"], {"status": "running", "current_phase": "voice", "phases": {"voice": {"status": "running"}}})
    client = TestClient(create_app(service))

    response = client.get("/api/producer-chat/context", params={"selected_job_id": job["id"], "app_tab": "voice"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["app_tab"] == "voice"
    assert payload["selected_job"]["id"] == job["id"]
    assert payload["selected_job"]["current_phase"] == "voice"


def test_producer_chat_history_is_scoped_and_clear_only_affects_current_project(tmp_path: Path):
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=NoopGateway(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    job_a = service.create_job({"title": "Project A"})
    job_b = service.create_job({"title": "Project B"})
    service._append_producer_chat_history("user", "A only", selected_job_id=job_a["id"])
    service._append_producer_chat_history("user", "B only", selected_job_id=job_b["id"])
    client = TestClient(create_app(service))

    history_a = client.get("/api/producer-chat", params={"selected_job_id": job_a["id"]})
    history_b = client.get("/api/producer-chat", params={"selected_job_id": job_b["id"]})

    assert history_a.status_code == 200
    assert history_b.status_code == 200
    assert [item["content"] for item in history_a.json()] == ["A only"]
    assert [item["content"] for item in history_b.json()] == ["B only"]

    cleared = client.delete("/api/producer-chat", params={"selected_job_id": job_a["id"]})

    assert cleared.status_code == 200
    assert client.get("/api/producer-chat", params={"selected_job_id": job_a["id"]}).json() == []
    assert [item["content"] for item in client.get("/api/producer-chat", params={"selected_job_id": job_b["id"]}).json()] == ["B only"]


def test_producer_chat_ui_switches_history_by_project_and_has_clear_controls() -> None:
    root = Path(__file__).resolve().parents[1]
    index_html = (root / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "static" / "app.js").read_text(encoding="utf-8")

    assert "producerCodexClearBtn" in index_html
    assert "globalCodexClearBtn" in index_html
    assert "producerChatHistoryUrl" in app_js
    assert 'method: "DELETE"' in app_js
    assert "renderGlobalProducerChat({ loadHistory: true })" in app_js
    assert "e.target.closest('button, input, select, textarea, a')" in app_js
    assert "pointercancel" in app_js


def test_producer_chat_ui_follows_source_repair_until_terminal_status() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")

    assert "followSourceRepairs" in app_js
    assert "/api/source-repairs/${encodeURIComponent(repairId)}" in app_js
    assert 'new Set(["fixed", "failed"])' in app_js
    assert "Đã sửa code và kiểm thử đạt" in app_js
    assert "repairProgressHtml" in app_js
    assert "stream_events" in app_js
    assert "repair-live-log" in app_js


def test_producer_chat_live_ui_groups_real_activity_and_preserves_terminal_report() -> None:
    root = Path(__file__).resolve().parents[1]
    index_html = (root / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "static" / "app.js").read_text(encoding="utf-8")
    styles = (root / "static" / "styles.css").read_text(encoding="utf-8")

    assert "chatActivityLabel" in app_js
    assert "chat-activity-timeline" in app_js
    assert "event.message || result?.reply" in app_js
    assert "31 sự kiện" not in app_js
    assert ".chat-activity-step" in styles
    assert "chat-agent-experience-v3" in index_html


def test_producer_chat_stream_endpoint_forwards_cli_events_and_final_result():
    class StreamingChatService:
        def producer_chat(self, message, selected_job_id=None, app_tab=None, attachment_ids=None, log_callback=None):
            assert message == "fix it"
            assert callable(log_callback)
            log_callback('{"type":"item.started","item":{"type":"command_execution","command":"pytest -q"}}')
            return {"reply": "done", "history": [], "actions": [], "ui_actions": []}

    client = TestClient(create_app(StreamingChatService()))
    response = client.post("/api/producer-chat/stream", json={"message": "fix it"})

    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events[0]["type"] == "started"
    assert events[1]["type"] == "cli_event"
    assert "pytest -q" in events[1]["line"]
    assert events[-1]["type"] == "result"
    assert events[-1]["result"]["reply"] == "done"


def test_durable_producer_chat_run_endpoints_create_replay_inspect_and_cancel():
    class DurableChatService:
        def __init__(self):
            self.cancelled = []

        def start_producer_chat_run(self, payload):
            assert payload["message"] == "fix it"
            return {"id": "chat-1", "provider": "gemini", "status": "queued", "last_seq": 0}

        def get_producer_chat_run(self, run_id):
            if run_id != "chat-1":
                raise KeyError(run_id)
            return {"id": run_id, "provider": "gemini", "status": "running", "last_seq": 2}

        def find_active_producer_chat_run(self, selected_job_id=None):
            assert selected_job_id == "job-1"
            return {"id": "chat-1", "provider": "gemini", "status": "running", "last_seq": 2}

        def producer_chat_run_events(self, run_id, after=0):
            assert run_id == "chat-1"
            assert after == 1
            yield {"type": "stage", "stage": "verifying", "seq": 2}

        def cancel_producer_chat_run(self, run_id):
            self.cancelled.append(run_id)
            return {"id": run_id, "status": "cancelling"}

        def stop_cofi_studio_embed(self):
            return None

    service = DurableChatService()
    client = TestClient(create_app(service))

    created = client.post("/api/producer-chat/runs", json={"message": "fix it"})
    active = client.get("/api/producer-chat/runs/active", params={"selected_job_id": "job-1"})
    inspected = client.get("/api/producer-chat/runs/chat-1")
    replayed = client.get("/api/producer-chat/runs/chat-1/events", params={"after": 1})
    cancelled = client.post("/api/producer-chat/runs/chat-1/cancel")

    assert created.status_code == 200
    assert created.json()["provider"] == "gemini"
    assert active.json()["id"] == "chat-1"
    assert inspected.json()["status"] == "running"
    assert [json.loads(line)["seq"] for line in replayed.text.splitlines()] == [2]
    assert cancelled.json()["status"] == "cancelling"
    assert service.cancelled == ["chat-1"]


def test_producer_chat_ui_consumes_ndjson_stream_for_both_chat_surfaces() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")

    assert 'fetch("/api/producer-chat/runs"' in app_js
    assert "/api/producer-chat/runs/active" in app_js
    assert "response.body.getReader()" in app_js
    assert "renderChatLiveProgress" in app_js
    assert "globalCodexThinking" in app_js
    assert "producerCodexThinking" in app_js


def test_producer_chat_ui_uses_durable_runs_reconnect_and_same_card_repair_events() -> None:
    app_js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")

    assert 'fetch("/api/producer-chat/runs"' in app_js
    assert "chatRunStorageKey" in app_js
    assert "connectProducerChatRun" in app_js
    assert "events?after=" in app_js
    assert "/cancel" in app_js
    assert '["succeeded", "failed", "cancelled"].includes' in app_js
    assert "stored.provider || selectedAiLabel(), 0" in app_js
    assert 'event.type === "repair_event"' in app_js
    assert "followSourceRepairs(result.actions || [], messages)" not in app_js


def test_headless_voice_endpoints_clone_design_preview_and_delete():
    class HeadlessVoiceService:
        def voice_options(self):
            return [
                {
                    "id": "v-ko-1",
                    "name": "K1",
                    "type": "clone",
                    "language": "ko",
                    "country_code": "KR",
                    "country_label": "Hàn Quốc",
                    "flag": "🇰🇷",
                    "proxy_preview_url": "/api/voice/preview-audio/v-ko-1",
                }
            ]

        def clone_voice(self, *, name, language, audio_bytes, filename="sample.wav", ref_text=None, recorded=False):
            assert name == "Giọng Hàn Mới"
            assert language == "ko"
            assert audio_bytes == b"RIFF-fake-wav"
            return {"id": "v-clone-new", "name": name, "type": "clone", "language": language, "country_code": "KR"}

        def design_voice(self, *, name, language, instruct, auto_preview=True):
            assert name == "Narrator US"
            assert language == "en"
            assert "authoritative" in instruct
            assert auto_preview is True
            return {"id": "v-design-new", "name": name, "type": "design", "language": language, "instruct": instruct}

        def preview_voice(self, voice_id):
            return {"voice_id": voice_id, "proxy_preview_url": f"/api/voice/preview-audio/{voice_id}"}

        def delete_voice(self, voice_id):
            return {"deleted": True, "voice_id": voice_id}

        def stop_cofi_studio_embed(self):
            return None

    import base64
    client = TestClient(create_app(HeadlessVoiceService()))

    voices_resp = client.get("/api/voice/voices")
    assert voices_resp.status_code == 200
    assert voices_resp.json()[0]["country_code"] == "KR"

    clone_resp = client.post(
        "/api/voice/clone",
        json={
            "name": "Giọng Hàn Mới",
            "language": "ko",
            "filename": "sample.wav",
            "audio_base64": base64.b64encode(b"RIFF-fake-wav").decode("ascii"),
        },
    )
    assert clone_resp.status_code == 200
    assert clone_resp.json()["id"] == "v-clone-new"

    design_resp = client.post(
        "/api/voice/design",
        json={
            "name": "Narrator US",
            "language": "en",
            "instruct": "Deep authoritative documentary voice",
            "auto_preview": True,
        },
    )
    assert design_resp.status_code == 200
    assert design_resp.json()["type"] == "design"

    prev_resp = client.post("/api/voice/voices/v-design-new/preview")
    assert prev_resp.status_code == 200
    assert prev_resp.json()["proxy_preview_url"] == "/api/voice/preview-audio/v-design-new"

    del_resp = client.delete("/api/voice/voices/v-design-new")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True


def test_flow_runtime_account_prune_and_delete_endpoints():
    class FlowRuntimeAccountService:
        def ai_visual_runtime_prune_dead_accounts(self):
            return {
                "ok": True,
                "kept_count": 7,
                "deleted_count": 18,
                "deleted": [{"id": "dead-1", "email": "dead@example.com", "status": "auth_expired"}],
                "accounts": [{"id": "live-1", "email": "live@example.com", "status": "ready"}],
            }

        def ai_visual_runtime_account(self, account_id, action):
            return {"ok": True, "deleted": action == "delete", "account_id": account_id, "action": action}

        def ai_visual_runtime_account_login(self):
            return {"id": "new-acc", "status": "connecting"}

        def stop_cofi_studio_embed(self):
            return None

    client = TestClient(create_app(FlowRuntimeAccountService()))

    prune_resp = client.post("/api/cofi-studio/runtime/accounts/prune-dead")
    assert prune_resp.status_code == 200
    assert prune_resp.json()["kept_count"] == 7
    assert prune_resp.json()["deleted_count"] == 18

    del_resp = client.delete("/api/cofi-studio/runtime/accounts/acc-123")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    login_resp = client.post("/api/cofi-studio/runtime/accounts/login")
    assert login_resp.status_code == 200
    assert login_resp.json()["status"] == "connecting"


def test_headless_voice_ui_and_flow_account_popup_contracts() -> None:
    root = Path(__file__).resolve().parents[1]
    index_html = (root / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "static" / "app.js").read_text(encoding="utf-8")

    assert "cofiVoiceFrame" not in app_js
    assert 'id="flowAccountsDialog"' in index_html
    assert "openFlowAccountsPopupBtn" in app_js
    assert "pruneDeadFlowAccountsBtn" in app_js
    assert "/api/cofi-studio/runtime/accounts/prune-dead" in app_js
    assert "/api/voice/clone" in app_js
    assert "/api/voice/design" in app_js


def test_antigravity_chat_ui_and_session_endpoints() -> None:
    root = Path(__file__).resolve().parents[1]
    index_html = (root / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "static" / "app.js").read_text(encoding="utf-8")
    styles = (root / "static" / "styles.css").read_text(encoding="utf-8")

    # Verify Antigravity model selector and UI elements
    assert 'id="globalChatModelSelect"' in index_html
    assert 'id="producerChatModelSelect"' in index_html
    assert "gemini-4-argon-high" in index_html
    assert "claude-opus-5-5-high" in index_html
    assert "claude-sonnet-5-5-high" in index_html
    assert "gpt-oss-120b-medium" in index_html
    assert "renderAntigravityMarkdown" in app_js
    assert "renderAntigravityStepsHtml" in app_js
    assert ".agy-composer-box" in styles
    assert ".agy-thought-block" in styles
    assert ".agy-tool-step" in styles

    class AntigravitySessionMockService:
        def new_producer_chat_session(self, selected_job_id=None):
            return {
                "ok": True,
                "conversation_id": "conv-new-123",
                "reply": "Đã mở phiên Antigravity mới.",
                "history": [],
                "selected_job_id": selected_job_id,
            }

        def compact_producer_chat_session(self, selected_job_id=None):
            return {
                "ok": True,
                "conversation_id": "conv-compact-456",
                "reply": "Đã nén ngữ cảnh.",
                "history": [{"role": "assistant", "content": "Đã nén ngữ cảnh."}],
                "selected_job_id": selected_job_id,
            }

        def stop_cofi_studio_embed(self):
            return None

    client = TestClient(create_app(AntigravitySessionMockService()))

    new_resp = client.post("/api/producer-chat/new", json={"selected_job_id": "job-1"})
    assert new_resp.status_code == 200
    assert new_resp.json()["conversation_id"] == "conv-new-123"

    compact_resp = client.post("/api/producer-chat/compact", json={"selected_job_id": "job-1"})
    assert compact_resp.status_code == 200
    assert compact_resp.json()["conversation_id"] == "conv-compact-456"
