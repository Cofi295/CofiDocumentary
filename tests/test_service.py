import json
import threading
from concurrent.futures import Future
from pathlib import Path

import pytest

from documentary.codex_gateway import StageResult
import documentary.service as service_module
from documentary.service import DocumentaryService
from documentary.store import JobStore


class FakeGateway:
    def __init__(self, blocker: threading.Event | None = None):
        self.blocker = blocker
        self.calls = []

    def run(self, job, phase, workspace, log_callback=None):
        self.calls.append((job["id"], phase))
        workspace = Path(workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        if self.blocker:
            self.blocker.wait(timeout=3)
        contract = job["production_recipe"]["quality_contract"]
        target = contract["target_duration_sec"]
        scene_count = contract["min_scene_count"]
        scene_ids = [f"B{i + 1:03d}" for i in range(scene_count)]
        rendered = workspace / "release" / "video.mp4"

        if phase == "plan":
            (workspace / "research.md").write_text("ok", encoding="utf-8")
            (workspace / "script.md").write_text("ok", encoding="utf-8")
            (workspace / "visual_manifest.json").write_text(json.dumps({
                "target_duration_sec": target,
                "beats": [{"beat_id": scene_id, "narration_text": "test", "target_duration_sec": target / scene_count} for scene_id in scene_ids],
            }), encoding="utf-8")
        elif phase == "edit":
            pass
        elif phase == "qc":
            rendered.parent.mkdir(parents=True, exist_ok=True)
            rendered.write_bytes(b"fake-video")
            (workspace / "render_manifest.json").write_text(json.dumps({
                "video_path": str(rendered), "duration_seconds": target, "fps": 30,
                "resolution": {"width": 1920, "height": 1080},
            }), encoding="utf-8")
            (workspace / "director_report.md").write_text("ACCEPT", encoding="utf-8")
            (workspace / "final_manifest.json").write_text(json.dumps({
                "video_path": str(rendered), "duration_seconds": target, "fps": 30,
                "resolution": {"width": 1920, "height": 1080}, "final_qc_status": "ACCEPT",
                "inspected_actual_render": True, "sha256": "abc123",
                "qc": {"blocker_count": 0, "unresolved_quality_count": 0,
                       "blackdetect_over_0_02s": 0, "silence_over_0_8s_below_minus48db": 0},
            }), encoding="utf-8")
        return StageResult(returncode=0, last_message="done", log_path=workspace / f"{phase}.jsonl")


class FailsAfterWritingPlanGateway(FakeGateway):
    def run(self, job, phase, workspace, log_callback=None):
        result = super().run(job, phase, workspace, log_callback=log_callback)
        if phase == "plan":
            return StageResult(returncode=1, last_message="model capacity after artifacts", log_path=result.log_path)
        return result


class TransientChatGateway(FakeGateway):
    def __init__(self):
        super().__init__()
        self.chat_calls = 0
        self.reset_calls = []

    def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False):
        self.chat_calls += 1
        if self.chat_calls == 1:
            return StageResult(1, "connection reset by peer", Path(workspace) / ".producer" / label)
        return StageResult(0, "Đã sửa cảnh hiện tại.", Path(workspace) / ".producer" / label)

    def reset_reusable_session(self, workspace, label, reason="manual_reset"):
        self.reset_calls.append((label, reason))
        return True


class AttachmentReconnectGateway(FakeGateway):
    def __init__(self):
        super().__init__()
        self.chat_calls = 0
        self.reset_calls = []

    def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False, image_paths=None):
        self.chat_calls += 1
        if self.chat_calls < 3:
            return StageResult(
                1,
                "ChatGPT did not accept all prompt attachments",
                Path(workspace) / ".producer" / label,
            )
        return StageResult(0, "Đã kết nối lại và nhận đủ ảnh.", Path(workspace) / ".producer" / label)

    def reset_reusable_session(self, workspace, label, reason="manual_reset"):
        self.reset_calls.append((label, reason))
        return True


class RateLimitedChatGateway(FakeGateway):
    def __init__(self):
        super().__init__()
        self.chat_calls = 0
        self.reset_calls = []

    def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False):
        self.chat_calls += 1
        return StageResult(1, "Too many requests: thao tác quá nhanh", Path(workspace) / ".producer" / label)

    def reset_reusable_session(self, workspace, label, reason="manual_reset"):
        self.reset_calls.append((label, reason))
        return True


class BlockingChatGateway(FakeGateway):
    def __init__(self):
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()

    def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False):
        self.entered.set()
        self.release.wait(timeout=3)
        return StageResult(0, "Đã sửa xong.", Path(workspace) / ".producer" / label)


class ImageChatGateway(FakeGateway):
    def __init__(self):
        super().__init__()
        self.chat_calls = []

    def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False, image_paths=None):
        self.chat_calls.append({
            "prompt": prompt,
            "workspace": Path(workspace),
            "label": label,
            "use_remotion_root": use_remotion_root,
            "image_paths": [Path(path) for path in (image_paths or [])],
        })
        if label.startswith("producer_chat"):
            message = json.dumps({"reply": "Tôi đã xem ảnh.", "actions": []}, ensure_ascii=False)
        else:
            message = "Tôi đã xem ảnh và cập nhật cảnh."
        return StageResult(0, message, Path(workspace) / ".producer" / label)


class RadarAuditGateway(FakeGateway):
    def __init__(self, verdict="approve", adjustment=-4):
        super().__init__()
        self.verdict = verdict
        self.adjustment = adjustment
        self.audit_calls = 0

    def run_prompt(self, prompt, workspace, label, log_callback=None, use_remotion_root=False):
        self.audit_calls += 1
        payload = {
            "audits": [
                {
                    "id": "niche-1",
                    "verdict": self.verdict,
                    "adjustment": self.adjustment,
                    "reasons": ["Bằng chứng đến từ nhiều kênh độc lập."],
                    "flags": [],
                }
            ]
        }
        return StageResult(
            returncode=0,
            last_message=json.dumps(payload, ensure_ascii=False),
            log_path=Path(workspace) / f"{label}.jsonl",
        )


class FakeMicroRadarClient:
    def __init__(self):
        self.calls = 0
        self.saved_niches = []

    def market_feed(self, scan_id):
        self.calls += 1
        topic = {
            "id": "niche-1",
            "label": "china economy debt crisis explained",
            "win_confidence": 84.0,
            "confidence_band": "very_strong",
            "winning_channels": 3,
            "breakout_videos": 5,
            "median_vph": 2100,
            "median_outlier": 7.2,
            "confidence_reasons": ["3 kênh nhỏ/mới độc lập đang có video thắng"],
            "channels": [
                {"channel_id": "c1", "title": "One", "subscribers": 6000, "channel_age_days": 40, "win_count": 2},
                {"channel_id": "c2", "title": "Two", "subscribers": 9000, "channel_age_days": 55, "win_count": 2},
                {"channel_id": "c3", "title": "Three", "subscribers": 12000, "channel_age_days": 70, "win_count": 1},
            ],
            "videos": [
                {"id": "v1", "title": "Debt crisis explained", "channel_id": "c1", "views": 120000, "vph": 2200, "outlier": 8.0},
                {"id": "v2", "title": "Debt crisis deep dive", "channel_id": "c2", "views": 100000, "vph": 1900, "outlier": 6.5},
            ],
        }
        return {
            "scan": {"id": scan_id, "market": "US"},
            "granularity": "micro",
            "emerging_themes": [dict(topic)],
            "momentum_topics": [dict(topic)],
            "counts": {"emerging_themes": 1, "momentum_topics": 1},
        }

    def save_niche(self, niche_id, *, note=None):
        self.saved_niches.append((niche_id, note))
        return {"ok": True, "kind": "niche", "ref_id": str(niche_id), "note": note}


class FakeVoice:
    def run(self, job, workspace):
        workspace = Path(workspace)
        visual = json.loads((workspace / "visual_manifest.json").read_text(encoding="utf-8"))
        beats = []
        cursor = 0.0
        for beat in visual["beats"]:
            duration = float(beat["target_duration_sec"])
            beats.append({"beat_id": beat["beat_id"], "text": beat["narration_text"], "start_sec": cursor, "end_sec": cursor + duration})
            cursor += duration
        (workspace / "audio").mkdir(exist_ok=True)
        narration = workspace / "audio" / "narration.wav"
        narration.write_bytes(b"fake-wav")
        (workspace / "voice_manifest.json").write_text(json.dumps({"narration_path": str(narration), "duration_sec": cursor, "beats": beats}), encoding="utf-8")
        (workspace / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\ntest\n", encoding="utf-8")
        return StageResult(0, "voice done", workspace / "voice_manifest.json")

    def health(self):
        return {"ok": True, "url": "fake"}

    def voices(self):
        return []


class FakeFootage:
    def run(self, job, workspace):
        workspace = Path(workspace)
        contract = job["production_recipe"]["quality_contract"]
        visual = json.loads((workspace / "visual_manifest.json").read_text(encoding="utf-8"))
        beat_ids = [beat["beat_id"] for beat in visual["beats"]]
        candidates = []
        assets = []
        unique_sources = contract["min_unique_video_sources"]
        for i in range(contract["min_video_clip_uses"]):
            cid = f"video-{i}"
            path = workspace / f"video-{i}.mp4"
            path.write_bytes(b"video")
            candidates.append({"candidate_id": cid, "decision": "ACCEPT", "visually_inspected_actual_content": True})
            assets.append({"id": f"V{i}", "beat_id": beat_ids[i % len(beat_ids)], "kind": "sourced_video", "path": str(path), "source": {"candidate_id": cid, "url": f"https://source.test/{i % unique_sources}"}})
        for i in range(contract["min_sourced_still_uses"]):
            cid = f"still-{i}"
            path = workspace / f"still-{i}.jpg"
            path.write_bytes(b"still")
            candidates.append({"candidate_id": cid, "decision": "ACCEPT", "visually_inspected_actual_content": True})
            assets.append({"id": f"I{i}", "beat_id": beat_ids[i % len(beat_ids)], "kind": "sourced_still", "path": str(path), "source": {"candidate_id": cid, "url": f"https://image.test/{i}"}})
        native = [{"id": f"N{i}", "beat_id": beat_ids[i % len(beat_ids)], "kind": "remotion_native_motion"} for i in range(contract["min_native_motion_treatments"])]
        for name, worker in (("footage_codex.json", "codex"), ("footage_gemini.json", "gemini")):
            (workspace / name).write_text(json.dumps({"worker": worker, "status": "completed", "candidates": [], "assets": [], "native_treatments": []}), encoding="utf-8")
        (workspace / "footage_review.json").write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
        (workspace / "asset_registry.json").write_text(json.dumps({"assets": assets, "native_treatments": native}), encoding="utf-8")
        return StageResult(0, "footage done", workspace / "footage_review.json")


class RepairTrackingFootage(FakeFootage):
    def __init__(self):
        self.full_runs = 0
        self.repairs = []

    def run(self, job, workspace):
        self.full_runs += 1
        return super().run(job, workspace)

    def repair(self, job, workspace, beat_ids):
        self.repairs.append(list(beat_ids))
        return StageResult(0, "repair done", Path(workspace) / "footage_review.json")


class FakeExportRenderCache:
    def finalize(self, job, workspace, beats):
        workspace = Path(workspace)
        rendered = workspace / "release" / "video.mp4"
        rendered.parent.mkdir(parents=True, exist_ok=True)
        rendered.write_bytes(b"final-video")
        manifest = {
            "video_path": str(rendered),
            "duration_seconds": 120.0,
            "fps": 30,
            "resolution": {"width": 1920, "height": 1080},
            "render_mode": "background_chunk_cache",
        }
        (workspace / "render_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    def status(self, workspace):
        return {"status": "ready", "ready_chunks": 2, "total_chunks": 2}



def make_service(tmp_path: Path, gateway=None, footage_coordinator=None):
    store = JobStore(tmp_path / "jobs")
    return DocumentaryService(
        root=tmp_path,
        store=store,
        gateway=gateway or FakeGateway(),
        voice_engine=FakeVoice(),
        footage_coordinator=footage_coordinator or FakeFootage(),
        remotion_dir=tmp_path / "CofiRemotion",
    )


def test_new_jobs_default_to_semantic_ai_footage_mode(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Semantic footage default"})

    assert job["footage_mode"] == "vision_codex"


def test_ai_visual_settings_save_style_reference_inside_job_workspace(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "AI visual style reference"})

    saved = service.update_ai_visual_settings(job["id"], {
        "style_mode": "preset",
        "style_preset": "Người Que US",
        "coverage_mode": "full_ai",
        "reference_image_name": "mau.png",
        "reference_image_data_url": "data:image/png;base64,aW1hZ2UtYnl0ZXM=",
    })

    reference = Path(saved["style_reference_image"])
    assert reference.exists()
    assert reference.read_bytes() == b"image-bytes"
    assert reference.parent == Path(job["workspace"]) / "media" / "style_reference"
    assert saved["style_mode"] == "preset"
    assert saved["style_preset"] == "Người Que US"
    assert saved["coverage_mode"] == "full_ai"


def test_gemini_model_setting_persists_and_updates_gateway(tmp_path: Path):
    class ConfigurableGemini:
        executable = "agy"
        transport = "antigravity"
        default_model = ""

        def auth_status(self):
            return {
                "ready": True,
                "auth_method": "antigravity-cli",
                "models": [
                    {"id": "gemini-3.8-flash-high", "label": "Gemini 3.8 Flash (High)"},
                    {"id": "gemini-3.1-pro-high", "label": "Gemini 3.1 Pro (High)"},
                ],
            }

    first_gateway = ConfigurableGemini()
    DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=FakeGateway(),
        gemini_gateway=first_gateway,
        voice_engine=FakeVoice(),
        footage_coordinator=FakeFootage(),
        remotion_dir=tmp_path / "CofiRemotion",
    ).update_ai_account_settings("gemini", {"model": "gemini-3.1-pro-high"})

    assert first_gateway.default_model == "gemini-3.1-pro-high"
    saved = json.loads((tmp_path / "data" / "ai_account_settings.json").read_text(encoding="utf-8"))
    assert saved["gemini_model"] == "gemini-3.1-pro-high"

    second_gateway = ConfigurableGemini()
    DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=FakeGateway(),
        gemini_gateway=second_gateway,
        voice_engine=FakeVoice(),
        footage_coordinator=FakeFootage(),
        remotion_dir=tmp_path / "CofiRemotion",
    )

    assert second_gateway.default_model == "gemini-3.1-pro-high"


def test_health_does_not_mark_app_dead_only_because_codex_is_offline(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    monkeypatch.setattr(service_module, "executable_status", lambda value: {"ok": False, "executable": value})
    monkeypatch.setattr(service.remotion_manager, "status", lambda: {"ok": True})
    monkeypatch.setattr(service.cofi_studio_embed_manager, "status", lambda: {"ok": True})
    monkeypatch.setattr(service.radar_client, "health", lambda: {"ok": True})
    monkeypatch.setattr(service, "_chatgpt_web_bridge_health", lambda: {"ok": False})

    health = service.health()

    assert health["ok"] is True
    assert health["codex_cli"]["ok"] is False
    assert health["capabilities"]["codex"]["optional"] is True


def test_manual_edit_rerun_resets_completed_progress_and_live_event(tmp_path: Path, monkeypatch):
    class RerunGateway(FakeGateway):
        def __init__(self):
            super().__init__()
            self.reset_calls = []

        def reset_reusable_session(self, workspace, label, reason="manual_reset"):
            self.reset_calls.append((Path(workspace), label, reason))
            return True

    gateway = RerunGateway()
    service = make_service(tmp_path, gateway=gateway)
    job = service.create_job({"title": "Live rerun"})
    workspace = Path(job["workspace"])
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "edit_progress.json").write_text(json.dumps({
        "version": 1,
        "assigned_beat_ids": ["B001", "B002"],
        "completed_beat_ids": ["B001", "B002"],
        "status": "completed",
    }), encoding="utf-8")
    (workspace / "live_edit_event.json").write_text(json.dumps({"sequence": 7}), encoding="utf-8")
    public_live = service.remotion_dir / "public" / "live-edit" / f"{job['id']}.json"
    public_live.parent.mkdir(parents=True, exist_ok=True)
    public_live.write_text(json.dumps({"sequence": 7}), encoding="utf-8")

    started = {}
    monkeypatch.setattr(service, "start", lambda job_id, phase: started.update(job_id=job_id, phase=phase) or service.get_job(job_id))

    service.rerun(job["id"], "edit")

    assert not (workspace / "edit_progress.json").exists()
    assert not (workspace / "live_edit_event.json").exists()
    assert not public_live.exists()
    assert gateway.reset_calls == []
    assert started == {"job_id": job["id"], "phase": "edit"}


def test_qc_rerun_hides_stale_export_metadata_before_new_render(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Fresh export"})
    workspace = Path(job["workspace"])
    release = workspace / "release" / "video.mp4"
    release.parent.mkdir(parents=True, exist_ok=True)
    release.write_bytes(b"previous-export")
    (workspace / "render_manifest.json").write_text(json.dumps({"video_path": str(release)}), encoding="utf-8")
    (workspace / "final_manifest.json").write_text(json.dumps({"video_path": str(release), "sha256": "old"}), encoding="utf-8")
    (workspace / "director_report.md").write_text("old report", encoding="utf-8")
    combine_log = workspace / ".render_cache" / "combine.log"
    combine_log.parent.mkdir(parents=True, exist_ok=True)
    combine_log.write_text("old combine", encoding="utf-8")

    monkeypatch.setattr(service, "start", lambda job_id, phase: service.get_job(job_id))
    rerun = service.rerun(job["id"], "qc")

    assert release.exists()
    assert not (workspace / "render_manifest.json").exists()
    assert not (workspace / "final_manifest.json").exists()
    assert not (workspace / "director_report.md").exists()
    assert not combine_log.exists()
    assert rerun["phases"]["qc"]["status"] == "pending"


def test_seo_rerun_removes_stale_packaging_before_new_worker(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Fresh SEO packaging"})
    workspace = Path(job["workspace"])
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "seo_package.json").write_text(json.dumps({"recommended_title": "old"}), encoding="utf-8")
    (workspace / "seo_reference_context.json").write_text(json.dumps({"profile_id": "old"}), encoding="utf-8")

    started = {}
    monkeypatch.setattr(
        service,
        "start",
        lambda job_id, phase: started.update(job_id=job_id, phase=phase) or service.get_job(job_id),
    )

    rerun = service.rerun(job["id"], "seo")

    assert started == {"job_id": job["id"], "phase": "seo"}
    assert rerun["phases"]["seo"]["status"] == "pending"
    assert not (workspace / "seo_package.json").exists()
    assert not (workspace / "seo_reference_context.json").exists()


def test_rerun_voice_invalidates_visuals_and_both_hybrid_visual_branches(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Refresh visuals after voice change", "visual_strategy": "hybrid"})
    workspace = Path(job["workspace"])
    media = workspace / "media" / "codex" / "B001.mp4"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"existing-footage")
    (workspace / "asset_registry.json").write_text(json.dumps({
        "assets": [{"id": "a1", "beat_id": "B001", "path": str(media)}],
    }), encoding="utf-8")
    (workspace / "ai_visual_manifest.json").write_text(json.dumps({"generated": []}), encoding="utf-8")
    (workspace / "coverage_matrix.json").write_text("{}", encoding="utf-8")
    (workspace / "preflight_report.json").write_text("{}", encoding="utf-8")
    (workspace / "edit_progress.json").write_text("{}", encoding="utf-8")
    (workspace / "render_manifest.json").write_text("{}", encoding="utf-8")
    service.store.update(job["id"], {
        "status": "completed",
        "phases": {phase: {"status": "succeeded"} for phase in (
            "plan", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc"
        )},
    })
    started = {}
    monkeypatch.setattr(service, "start", lambda job_id, phase: started.update(job_id=job_id, phase=phase) or service.get_job(job_id))

    rerun = service.rerun(job["id"], "voice")

    assert started == {"job_id": job["id"], "phase": "voice"}
    assert rerun["phases"]["voice"]["status"] == "pending"
    assert rerun["phases"]["visuals"]["status"] == "pending"
    assert rerun["phases"]["footage"]["status"] == "pending"
    assert rerun["phases"]["ai_visual"]["status"] == "pending"
    assert rerun["phases"]["edit"]["status"] == "pending"
    assert rerun["phases"]["seo"]["status"] == "pending"
    assert rerun["phases"]["qc"]["status"] == "pending"
    assert media.read_bytes() == b"existing-footage"
    assert not (workspace / "asset_registry.json").exists()
    assert (workspace / "ai_visual_manifest.json").exists()
    assert json.loads((workspace / "ai_visual_manifest.json").read_text(encoding="utf-8"))["status"] == "reset_after_voice_rerun"
    assert not (workspace / "coverage_matrix.json").exists()
    assert not (workspace / "preflight_report.json").exists()
    assert not (workspace / "edit_progress.json").exists()
    assert not (workspace / "render_manifest.json").exists()


def test_voice_to_edit_pipeline_regenerates_visuals_and_full_footage_branch(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Voice pipeline reuses visuals"})
    service.store.update(job["id"], {
        "phases": {
            "plan": {"status": "succeeded"},
            "voice": {"status": "succeeded"},
            "visuals": {"status": "succeeded"},
            "footage": {"status": "succeeded"},
            "edit": {"status": "succeeded"},
        },
    })
    submitted = {}

    class FakeExecutor:
        def submit(self, func, *args):
            submitted["args"] = args
            return type("Future", (), {"done": lambda self: False})()

    service._executor = FakeExecutor()

    queued = service.run_pipeline(job["id"], "voice", "edit")

    assert submitted["args"] == (job["id"], ["voice", "visuals", "footage", "edit"])
    assert queued["current_phase"] == "voice"
    assert queued["phases"]["visuals"]["status"] == "pending"
    assert queued["phases"]["footage"]["status"] == "pending"


def test_start_voice_backend_uses_cofivoice_virtualenv_python(tmp_path: Path, monkeypatch) -> None:
    voice_dir = tmp_path / "CofiVoice"
    voice_python = voice_dir / "venv" / "Scripts" / "python.exe"
    voice_python.parent.mkdir(parents=True)
    voice_python.write_bytes(b"")
    (voice_dir / "app.py").write_text("app = object()\n", encoding="utf-8")
    monkeypatch.setenv("COFI_VOICE_DIR", str(voice_dir))

    class OfflineVoice:
        base_url = "http://127.0.0.1:8000"

        def health(self):
            return {"ok": False, "url": self.base_url}

    launched = {}

    class FakeProcess:
        pid = 12345

        def poll(self):
            return None

    def fake_popen(command, **kwargs):
        launched["command"] = command
        launched["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr("documentary.service.subprocess.Popen", fake_popen)
    service = DocumentaryService(
        root=tmp_path / "documentary",
        store=JobStore(tmp_path / "jobs"),
        gateway=FakeGateway(),
        voice_engine=OfflineVoice(),
        remotion_dir=tmp_path / "CofiRemotion",
    )

    result = service.start_voice_backend()

    assert Path(launched["command"][0]) == voice_python
    assert launched["command"][1:4] == ["-m", "uvicorn", "app:app"]
    assert launched["kwargs"]["env"]["PYTHONIOENCODING"] == "utf-8"
    assert result["starting"] is True


def test_start_voice_backend_reuses_existing_shared_cofivoice(tmp_path: Path, monkeypatch) -> None:
    class SharedVoice:
        base_url = "http://127.0.0.1:8000"

        def health(self):
            return {"ok": False, "url": self.base_url}

        def discover(self):
            self.base_url = "http://127.0.0.1:8776"
            return {"ok": True, "url": self.base_url, "status_code": 200}

    def fail_popen(*_args, **_kwargs):
        raise AssertionError("must not start a second CofiVoice process")

    monkeypatch.setattr("documentary.service.subprocess.Popen", fail_popen)
    service = DocumentaryService(
        root=tmp_path / "documentary",
        store=JobStore(tmp_path / "jobs"),
        gateway=FakeGateway(),
        voice_engine=SharedVoice(),
        remotion_dir=tmp_path / "CofiRemotion",
    )

    result = service.start_voice_backend()

    assert result["ok"] is True
    assert result["starting"] is False
    assert result["shared"] is True
    assert result["url"] == "http://127.0.0.1:8776"


def test_phase_order_rejects_voice_before_plan(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Topic"})

    with pytest.raises(ValueError, match="plan"):
        service.start(job["id"], "voice")


def test_edit_chat_recovers_transient_disconnect_without_duplicate_history(tmp_path: Path):
    gateway = TransientChatGateway()
    service = make_service(tmp_path, gateway=gateway)
    job = service.create_job({"title": "Recover edit chat"})

    result = service.edit_chat(job["id"], "đổi footage đoạn này")

    history = service.edit_chat_history(job["id"])
    assert result["reply"] == "Đã sửa cảnh hiện tại."
    assert gateway.chat_calls == 2
    assert gateway.reset_calls == []
    assert [item["role"] for item in history] == ["user", "assistant"]
    assert history[0]["content"] == "đổi footage đoạn này"


def test_edit_chat_question_does_not_invalidate_finished_video(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path, gateway=ImageChatGateway())
    job = service.create_job({"title": "Finished documentary"})
    invalidations = []
    monkeypatch.setattr(service.render_cache, "_source_signature", lambda: "unchanged-source")
    monkeypatch.setattr(service, "_mark_qc_stale_after_edit", lambda *args: invalidations.append("qc"))
    monkeypatch.setattr(service.render_cache, "invalidate", lambda *args, **kwargs: invalidations.append("cache"))
    monkeypatch.setattr(service.render_cache, "rebuild_async", lambda *args, **kwargs: invalidations.append("render"))

    service.edit_chat(job["id"], "Video cuối ở đâu?")

    assert invalidations == []


def test_chat_reconnects_three_times_when_chatgpt_rejects_prompt_attachments(tmp_path: Path):
    gateway = AttachmentReconnectGateway()
    service = make_service(tmp_path, gateway=gateway)
    job = service.create_job({"title": "Reconnect attachment chat"})

    result = service.edit_chat(job["id"], "xem lại ảnh này")

    assert result["reply"] == "Đã kết nối lại và nhận đủ ảnh."
    assert gateway.chat_calls == 3
    assert gateway.reset_calls == []


def test_edit_chat_stops_immediately_when_chatgpt_is_rate_limited(tmp_path: Path):
    gateway = RateLimitedChatGateway()
    service = make_service(tmp_path, gateway=gateway)
    job = service.create_job({"title": "Rate limited edit chat"})

    with pytest.raises(RuntimeError, match="Too many requests"):
        service.edit_chat(job["id"], "đổi footage đoạn này")

    assert gateway.chat_calls == 1
    assert gateway.reset_calls == []
    assert service._active_edit_jobs == set()


def test_edit_chat_blocks_export_or_other_production_until_source_edit_finishes(tmp_path: Path):
    gateway = BlockingChatGateway()
    service = make_service(tmp_path, gateway=gateway)
    job = service.create_job({"title": "Serialize edit and export"})
    failures = []

    worker = threading.Thread(
        target=lambda: service.edit_chat(job["id"], "chỉnh timing đoạn cuối"),
        daemon=True,
    )
    worker.start()
    assert gateway.entered.wait(timeout=2)

    with pytest.raises(RuntimeError, match="đang chỉnh sửa preview"):
        service.start(job["id"], "plan")
    with pytest.raises(RuntimeError, match="đang xử lý một yêu cầu edit"):
        service.edit_chat(job["id"], "gửi thêm một edit nữa")

    gateway.release.set()
    worker.join(timeout=3)
    if worker.is_alive():
        failures.append("edit chat worker did not finish")

    assert failures == []
    assert service._active_edit_jobs == set()


def test_edit_chat_can_send_image_only_and_persists_attachment_history(tmp_path: Path):
    gateway = ImageChatGateway()
    service = make_service(tmp_path, gateway=gateway)
    job = service.create_job({"title": "Image edit chat"})
    attachment = service.save_chat_attachment(
        b"\x89PNG\r\n\x1a\nimage-body",
        "reference.png",
        "image/png",
    )

    result = service.edit_chat(job["id"], "", attachment_ids=[attachment["id"]])

    assert result["reply"] == "Tôi đã xem ảnh và cập nhật cảnh."
    call = gateway.chat_calls[0]
    assert call["label"] == "edit_chat"
    assert call["image_paths"] == [service.resolve_chat_attachment_path(attachment["id"])]
    assert "ATTACHED IMAGES" in call["prompt"]
    history = service.edit_chat_history(job["id"])
    assert history[0]["content"] == ""
    assert history[0]["attachments"][0]["id"] == attachment["id"]
    assert "path" not in history[0]["attachments"][0]


def test_producer_chat_can_send_image_with_text_to_same_reusable_session(tmp_path: Path):
    gateway = ImageChatGateway()
    service = make_service(tmp_path, gateway=gateway)
    attachment = service.save_chat_attachment(
        b"\xff\xd8\xffimage-body",
        "screen.jpg",
        "image/jpeg",
    )

    result = service.producer_chat(
        "xem ảnh này",
        attachment_ids=[attachment["id"]],
        app_tab="codex",
    )

    assert result["reply"] == "Tôi đã xem ảnh."
    call = gateway.chat_calls[0]
    assert call["label"] == "producer_chat_global"
    assert call["image_paths"] == [service.resolve_chat_attachment_path(attachment["id"])]
    assert "ATTACHED IMAGES" in call["prompt"]
    history = service.producer_chat_history()
    assert history[0]["attachments"][0]["name"] == "screen.jpg"


def test_producer_chat_executes_markdown_escaped_control_and_stores_plain_reply(tmp_path: Path, monkeypatch):
    class EscapedControlGateway(FakeGateway):
        def __init__(self):
            super().__init__()
            self.message = ""

        def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False, image_paths=None):
            return StageResult(0, self.message, Path(workspace) / ".producer" / label)

    gateway = EscapedControlGateway()
    service = make_service(tmp_path, gateway=gateway)
    job = service.create_job({"title": "Escaped producer control"})
    gateway.message = (
        rf'{{"reply":"Đang chạy lại Plan.","actions":\['
        rf'{{"type":"rerun\_phase","job\_id":"{job["id"]}","phase":"plan"}}\]}}'
    )
    calls = []

    def fake_rerun(job_id, phase):
        calls.append((job_id, phase))
        return {**service.get_job(job_id), "status": "queued", "current_phase": phase}

    monkeypatch.setattr(service, "rerun", fake_rerun)

    result = service.producer_chat("chạy lại plan", selected_job_id=job["id"], app_tab="codex")

    assert calls == [(job["id"], "plan")]
    assert result["reply"] == "Đang chạy lại Plan."
    assert result["actions"] == [{
        "type": "rerun_phase",
        "status": "ok",
        "job_id": job["id"],
        "phase": "plan",
        "job_status": "queued",
    }]
    history = service.producer_chat_history(selected_job_id=job["id"])
    assert history[-1]["content"] == "Đang chạy lại Plan."
    assert '"actions"' not in history[-1]["content"]


def test_producer_chat_history_hides_legacy_control_json_from_ui(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Legacy producer history"})
    history_path = Path(job["workspace"]) / "producer_chat_history.jsonl"
    history_path.write_text(json.dumps({
        "role": "assistant",
        "content": r'{"reply":"Đã nhận lệnh.","actions":\[{"type":"rerun\_phase","job\_id":"abc","phase":"plan"}\]}',
        "created_at": "2026-09-06T05:03:29+00:00",
    }, ensure_ascii=False) + "\n", encoding="utf-8")

    history = service.producer_chat_history(selected_job_id=job["id"])

    assert history[0]["content"] == "Đã nhận lệnh."


def test_producer_chat_does_not_claim_execution_when_action_fails(tmp_path: Path, monkeypatch):
    class FailedActionGateway(FakeGateway):
        def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False, image_paths=None):
            return StageResult(
                0,
                json.dumps({
                    "reply": "Đang chạy lại Plan.",
                    "actions": [{"type": "rerun_phase", "job_id": self.job_id, "phase": "plan"}],
                }, ensure_ascii=False),
                Path(workspace) / ".producer" / label,
            )

    gateway = FailedActionGateway()
    service = make_service(tmp_path, gateway=gateway)
    job = service.create_job({"title": "Failed producer action"})
    gateway.job_id = job["id"]

    def fail_rerun(job_id, phase):
        raise RuntimeError("another job is already running")

    monkeypatch.setattr(service, "rerun", fail_rerun)

    result = service.producer_chat("chạy lại plan", selected_job_id=job["id"], app_tab="codex")

    assert result["reply"] == "Không thực hiện được: rerun_phase: another job is already running"
    assert "Đang chạy" not in result["reply"]
    assert service.producer_chat_history(selected_job_id=job["id"])[-1]["content"] == result["reply"]


def test_repair_code_action_queues_real_source_repair_with_requested_provider(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    calls = []

    def fake_start(error, source="", provider="auto"):
        calls.append((error, source, provider))
        return {"id": "repair-1", "status": "queued", "provider": provider}

    monkeypatch.setattr(service.source_repair_agent, "start_job", fake_start)

    result, selected_job_id, ui_actions = service._execute_producer_action(
        {"type": "repair_code", "error": "API trả lỗi 500", "source": "chat", "provider": "gemini"},
        None,
    )

    assert calls == [("API trả lỗi 500", "chat", "gemini")]
    assert result["status"] == "queued"
    assert result["repair_job"]["id"] == "repair-1"
    assert selected_job_id is None
    assert ui_actions == []


def test_explicit_chat_provider_routes_only_to_selected_gateway(tmp_path: Path):
    class ChatGateway:
        def __init__(self, name):
            self.name = name
            self.calls = []
            self.available = True

        def auth_status(self):
            return {"ready": True}

        def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
            self.calls.append((prompt, label))
            if "VERIFIED EXECUTION EVIDENCE" in prompt:
                return StageResult(0, f"{self.name} đã kiểm tra xong và đây là báo cáo tự nhiên.", Path(workspace) / label)
            return StageResult(0, json.dumps({"reply": f"{self.name} done", "actions": []}), Path(workspace) / label)

        def run_prompt(self, prompt, workspace, label, **kwargs):
            if self.name == "gemini":
                raise AssertionError("Gemini chat must keep and rotate its CLI conversation")
            self.calls.append((prompt, label))
            return StageResult(0, json.dumps({"reply": f"{self.name} done", "actions": []}), Path(workspace) / label)

    codex = ChatGateway("codex")
    gemini = ChatGateway("gemini")
    service = DocumentaryService(
        root=tmp_path, store=JobStore(tmp_path / "jobs"), codex_gateway=codex,
        gemini_gateway=gemini, voice_engine=FakeVoice(), footage_coordinator=FakeFootage(),
        remotion_dir=tmp_path / "CofiRemotion",
    )

    service.update_chat_provider("gemini")
    result = service.producer_chat("hello")

    assert result["reply"] == "gemini done"
    assert len(gemini.calls) == 1
    assert all(label == "producer_chat_global" for _, label in gemini.calls)
    assert codex.calls == []


def test_gemini_main_chat_answers_thumbnail_status_with_full_context(tmp_path: Path):
    class FastGateway:
        transport = "antigravity"

        def __init__(self):
            self.calls = []

        def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
            self.calls.append((prompt, label, kwargs))
            assert label.startswith("producer_chat_")
            return StageResult(0, json.dumps({
                "reply": "Thumbnail mới đã lưu; chưa xác minh nội dung hình.", "actions": [],
            }, ensure_ascii=False), Path(workspace) / label)

    service = make_service(tmp_path)
    gateway = FastGateway()
    service.gemini_gateway = gateway
    job = service.create_job({"title": "Kênh đào Bình Lục"})
    (Path(job["workspace"]) / "thumbnail.jpg").write_bytes(b"thumbnail")

    result = service.producer_chat("Đã làm lại thumb chưa?", selected_job_id=job["id"], locked_provider="gemini")

    assert "Thumbnail mới đã lưu" in result["reply"]
    assert len(gateway.calls) == 1
    assert '"exists": true' in gateway.calls[0][0].lower()
    assert "AVAILABLE SPECIALISTS" in gateway.calls[0][0]


def test_gemini_main_chat_queues_thumbnail_rerun(tmp_path: Path, monkeypatch):
    class FastGateway:
        transport = "antigravity"

        def __init__(self):
            self.calls = []

        def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
            self.calls.append(label)
            assert label.startswith("producer_chat_")
            return StageResult(0, json.dumps({
                "reply": "Đã xếp hàng làm lại thumbnail.",
                "actions": [{"type": "rerun_phase", "job_id": job["id"], "phase": "seo"}],
            }, ensure_ascii=False), Path(workspace) / label)

    service = make_service(tmp_path)
    gateway = FastGateway()
    service.gemini_gateway = gateway
    job = service.create_job({"title": "Kênh đào Bình Lục"})
    reruns = []
    monkeypatch.setattr(service, "rerun", lambda job_id, phase: reruns.append((job_id, phase)) or {**service.get_job(job_id), "status": "queued"})

    result = service.producer_chat("Làm lại thumb cho đúng chủ đề", selected_job_id=job["id"], locked_provider="gemini")

    assert reruns == [(job["id"], "seo")]
    assert result["actions"][0]["job_status"] == "queued"
    assert len(gateway.calls) >= 1


def test_main_chat_delegates_worker_then_approves_exact_action(tmp_path: Path, monkeypatch):
    class CompanyGateway:
        def __init__(self):
            self.calls = []

        def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
            self.calls.append((prompt, label))
            if label.startswith("agent-"):
                content = {"status": "needs_action", "report": "Đã kiểm tra; bước voice đang chờ chạy.",
                           "proposed_actions": [{"type": "run_phase", "job_id": job["id"], "phase": "voice"}]}
            elif "reviewing a specialist's report" in prompt:
                content = {"actions": [{"type": "run_phase", "job_id": job["id"], "phase": "voice"}]}
            elif "VERIFIED EXECUTION EVIDENCE" in prompt:
                return StageResult(0, "Nhân viên đã kiểm tra; Voice đã được xếp chạy.", Path(workspace) / label)
            else:
                content = {"reply": "Tôi giao việc cho nhân viên Voice.", "actions": [
                    {"type": "delegate_agent", "agent_id": "voice", "task": "Kiểm tra voice và đề xuất bước tiếp"}
                ]}
            return StageResult(0, json.dumps(content, ensure_ascii=False), Path(workspace) / label)

    service = make_service(tmp_path)
    gateway = CompanyGateway()
    service.gemini_gateway = gateway
    job = service.create_job({"title": "Video thử"})
    started = []
    monkeypatch.setattr(service, "start", lambda job_id, phase: started.append((job_id, phase)) or {"status": "queued"})

    result = service.producer_chat("Kiểm tra và chạy voice", selected_job_id=job["id"], locked_provider="gemini")

    assert started == [(job["id"], "voice")]
    assert [item["type"] for item in result["actions"]] == ["delegate_agent", "run_phase"]
    assert result["actions"][0]["approved_actions"] == [{"type": "run_phase", "job_id": job["id"], "phase": "voice"}]
    assert list((tmp_path / ".producer" / "agent_reports").glob("agent-*.json"))
    assert any(label.startswith("agent-") for _, label in gateway.calls)
    assert any('"workspace_path"' in prompt for prompt, label in gateway.calls if label.startswith("agent-"))


def test_main_chat_cannot_run_unproposed_worker_action(tmp_path: Path, monkeypatch):
    class RejectGateway:
        def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
            if label.startswith("agent-"):
                value = {"status": "needs_action", "report": "Cần chạy voice.",
                         "proposed_actions": [{"type": "run_phase", "job_id": job["id"], "phase": "voice"}]}
            elif "reviewing a specialist's report" in prompt:
                value = {"actions": [{"type": "run_phase", "job_id": job["id"], "phase": "qc"}]}
            elif "VERIFIED EXECUTION EVIDENCE" in prompt:
                return StageResult(0, "Đã nhận báo cáo; chưa chạy hành động nào.", Path(workspace) / label)
            else:
                value = {"reply": "Giao nhân viên kiểm tra.", "actions": [
                    {"type": "delegate_agent", "agent_id": "voice", "task": "Kiểm tra bước voice"}
                ]}
            return StageResult(0, json.dumps(value, ensure_ascii=False), Path(workspace) / label)

    service = make_service(tmp_path)
    service.gemini_gateway = RejectGateway()
    job = service.create_job({"title": "Video thử"})
    started = []
    monkeypatch.setattr(service, "start", lambda *args: started.append(args))

    result = service.producer_chat("Kiểm tra voice", selected_job_id=job["id"], locked_provider="gemini")

    assert started == []
    assert result["actions"][0]["approved_actions"] == []


def test_explicit_worker_request_runs_even_when_model_only_claims_it_did(tmp_path: Path):
    class ForgetfulGateway:
        def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
            if label.startswith("agent-"):
                value = {"status": "completed", "report": "Plan succeeded theo context.", "proposed_actions": []}
                text = json.dumps(value, ensure_ascii=False)
            elif "VERIFIED EXECUTION EVIDENCE" in prompt:
                text = "QA đã báo Plan succeeded theo context."
            else:
                text = json.dumps({"reply": "Theo QA, Plan đã xong.", "actions": []}, ensure_ascii=False)
            return StageResult(0, text, Path(workspace) / label)

    service = make_service(tmp_path)
    service.gemini_gateway = ForgetfulGateway()
    job = service.create_job({"title": "Video thử"})

    result = service.producer_chat("Giao Quality kiểm tra Plan của dự án này", selected_job_id=job["id"], locked_provider="gemini")

    assert result["actions"][0]["type"] == "delegate_agent"
    assert result["actions"][0]["agent_id"] == "qc"
    assert result["actions"][0]["report"] == "Plan succeeded theo context."


def test_explicit_assignment_keeps_user_scope_when_model_broadens_task(tmp_path: Path):
    class BroadeningGateway:
        def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
            if label.startswith("agent-"):
                text = json.dumps({"status": "completed", "report": "Plan succeeded.", "proposed_actions": []})
            elif "VERIFIED EXECUTION EVIDENCE" in prompt:
                text = "Quality đã xác nhận trạng thái Plan."
            else:
                text = json.dumps({"reply": "Đang giao việc.", "actions": [{
                    "type": "delegate_agent", "agent_id": "qc",
                    "task": "Đọc toàn bộ research.md, script.md và visual_manifest.json để kiểm tra chất lượng",
                }]}, ensure_ascii=False)
            return StageResult(0, text, Path(workspace) / label)

    service = make_service(tmp_path)
    service.gemini_gateway = BroadeningGateway()
    job = service.create_job({"title": "Scope check"})
    user_message = "Giao Quality chỉ kiểm tra trạng thái Plan trong context, không đọc file"

    result = service.producer_chat(user_message, selected_job_id=job["id"], locked_provider="gemini")

    report_path = tmp_path / ".producer" / "agent_reports" / f"{result['actions'][0]['report_id']}.json"
    evidence = json.loads(report_path.read_text(encoding="utf-8"))
    assert evidence["task"] == user_message
    assert "Đọc toàn bộ research.md" not in evidence["task"]


def test_chat_replaces_false_ai_visual_running_claim_after_navigation(tmp_path: Path):
    class MisreportingGateway:
        def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
            if "VERIFIED EXECUTION EVIDENCE" in prompt:
                text = "AI Visual đang vận hành và tạo ảnh/video."
            else:
                text = json.dumps({"reply": "AI Visual đang vận hành.", "actions": [
                    {"type": "navigate", "tab": "ai_visual"}
                ]}, ensure_ascii=False)
            return StageResult(0, text, Path(workspace) / label)

    service = make_service(tmp_path)
    service.gemini_gateway = MisreportingGateway()
    job = service.create_job({"title": "Status guard", "visual_strategy": "full_ai"})

    result = service.producer_chat("Chuyển sang tạo ảnh/video được không?", selected_job_id=job["id"], locked_provider="gemini")

    assert result["actions"] == [{"type": "navigate", "status": "ok", "tab": "ai_visual"}]
    assert "ai_visual: pending" in result["reply"]
    assert "App chưa xác nhận" in result["reply"]
    assert "đang vận hành" not in result["reply"]


@pytest.mark.parametrize("approved", [True, False])
def test_chairman_review_controls_next_pipeline_phase(tmp_path: Path, monkeypatch, approved: bool):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Company pipeline"})
    phases_run = []
    monkeypatch.setattr(service, "_run_phase", lambda current, phase, workspace: (
        phases_run.append(phase) or StageResult(0, f"{phase} done", workspace / phase)
    ))
    monkeypatch.setattr(service, "_validate_artifacts", lambda *args: None)
    monkeypatch.setattr(service, "_review_phase_handoff", lambda *args: (approved, "Đã duyệt" if approved else "Cần kiểm tra thêm"))

    service._run_sequence(job["id"], ["plan", "voice"], "gemini")

    state = service.get_job(job["id"])
    assert phases_run == (["plan", "voice"] if approved else ["plan"])
    assert state["phases"]["plan"]["status"] == "succeeded"
    assert state["phases"]["voice"]["status"] == ("succeeded" if approved else "pending")
    if not approved:
        assert state["status"] == "ready"
        assert state["chairman_hold_reason"] == "Cần kiểm tra thêm"


def test_chairman_phase_review_persists_approval_evidence(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Company review"})
    service.store.update(job["id"], {"phases": {"plan": {"status": "succeeded", "last_message": "Artifacts validated"}}})
    monkeypatch.setattr(service, "_run_chat_prompt", lambda *args, **kwargs: StageResult(
        0, json.dumps({"approve_next": True, "reason": "Đã kiểm tra Plan."}, ensure_ascii=False), tmp_path / "review.log"
    ))

    approved, reason = service._review_phase_handoff(job["id"], "plan", "voice", "gemini")

    record_path = Path(job["workspace"]) / ".producer" / "company_reviews" / "plan_to_voice.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert (approved, reason) == (True, "Đã kiểm tra Plan.")
    assert record["approved"] is True
    assert record["provider"] == "gemini"
    assert record["agent_id"] == "script"
    assert record["next_phase"] == "voice"


def test_edit_chat_uses_selected_gemini_gateway(tmp_path: Path):
    class GeminiChatGateway:
        available = True

        def __init__(self):
            self.calls = []

        def auth_status(self):
            return {"ready": True}

        def run_prompt(self, prompt, workspace, label, **kwargs):
            self.calls.append(label)
            return StageResult(0, "Gemini trả lời trong Edit.", Path(workspace) / label)

        def run_prompt_reusable(self, *args, **kwargs):
            return self.run_prompt(*args, **kwargs)

    gemini = GeminiChatGateway()
    service = DocumentaryService(
        root=tmp_path, store=JobStore(tmp_path / "jobs"), codex_gateway=FakeGateway(),
        gemini_gateway=gemini, voice_engine=FakeVoice(), footage_coordinator=FakeFootage(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    job = service.create_job({"title": "Gemini Edit"})
    service.update_chat_provider("gemini")

    result = service.edit_chat(job["id"], "Cho tôi biết trạng thái video")

    assert result["reply"] == "Gemini trả lời trong Edit."
    assert gemini.calls == ["edit_chat"]


def test_producer_chat_uses_selected_provider_for_terminal_report_without_backend_template(tmp_path: Path):
    class NaturalReportGateway(FakeGateway):
        def __init__(self):
            super().__init__()
            self.chat_prompts = []

        def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
            self.chat_prompts.append(prompt)
            if len(self.chat_prompts) == 1:
                return StageResult(0, json.dumps({"reply": "Đang xem.", "actions": []}, ensure_ascii=False), Path(workspace) / label)
            return StageResult(0, "Mình đã xem đúng trạng thái hiện tại. Chưa có thao tác nào cần chạy, nên mình không báo khống là đã sửa xong.", Path(workspace) / label)

    gateway = NaturalReportGateway()
    service = make_service(tmp_path, gateway=gateway)

    result = service.producer_chat("xem giúp trạng thái", locked_provider="codex")

    assert result["reply"] == "Mình đã xem đúng trạng thái hiện tại. Chưa có thao tác nào cần chạy, nên mình không báo khống là đã sửa xong."
    assert len(gateway.chat_prompts) == 2
    assert "VERIFIED EXECUTION EVIDENCE" in gateway.chat_prompts[1]
    assert '"action_results": []' in gateway.chat_prompts[1]


def test_locked_provider_overrides_model_repair_provider(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    calls = []
    monkeypatch.setattr(
        service.source_repair_agent,
        "start_job",
        lambda error, source="", provider="auto": calls.append(provider) or {
            "id": "repair-locked", "status": "queued", "provider": provider,
        },
    )

    result, _, _ = service._execute_producer_action(
        {"type": "repair_code", "error": "broken", "provider": "gemini"},
        None,
        locked_provider="codex",
    )

    assert calls == ["codex"]
    assert result["repair_job"]["provider"] == "codex"


def test_producer_chat_waits_for_repair_and_only_publishes_verified_terminal_reply(tmp_path: Path, monkeypatch):
    class RepairGateway(FakeGateway):
        def run_prompt_reusable(self, prompt, workspace, label, **kwargs):
            return StageResult(
                0,
                json.dumps({
                    "reply": "Đang sửa.",
                    "actions": [{"type": "repair_code", "error": "broken resume", "provider": "gemini"}],
                }, ensure_ascii=False),
                Path(workspace) / ".producer" / label,
            )

    service = make_service(tmp_path, gateway=RepairGateway())
    providers = []
    snapshots = iter([
        {"id": "repair-wait", "status": "queued", "provider": "codex", "stream_events": []},
        {
            "id": "repair-wait", "status": "verifying", "provider_used": "codex",
            "live": {"message": "pytest đang chạy"},
            "stream_events": [{"kind": "command", "message": "pytest -q tests/test_resume.py"}],
        },
        {
            "id": "repair-wait", "status": "fixed", "provider_used": "codex",
            "source_changes": ["documentary/footage.py"],
            "verification": {"command": ["pytest", "-q", "tests/test_resume.py"], "returncode": 0},
            "stream_events": [{"kind": "command", "message": "pytest -q tests/test_resume.py"}],
        },
    ])
    monkeypatch.setattr(
        service.source_repair_agent,
        "start_job",
        lambda error, source="", provider="auto": providers.append(provider) or {
            "id": "repair-wait", "status": "queued", "provider": provider,
        },
    )
    monkeypatch.setattr(service.source_repair_agent, "get_job", lambda _repair_id: next(snapshots))
    monkeypatch.setattr(service_module.time, "sleep", lambda _seconds: None)
    events = []

    result = service.producer_chat(
        "fix resume",
        locked_provider="codex",
        event_callback=events.append,
    )

    assert providers == ["codex"]
    assert "Codex đã sửa code và kiểm thử đạt" in result["reply"]
    assert "documentary/footage.py" in result["reply"]
    assert "tests/test_resume.py" in result["reply"]
    assert any(event.get("type") == "repair_event" for event in events)
    terminal = [event for event in events if event.get("type") == "stage" and event.get("stage") == "completed"]
    assert len(terminal) == 1
    assert "documentary/footage.py" in terminal[0]["message"]
    assert "tests/test_resume.py" in terminal[0]["message"]
    assert service.producer_chat_history()[-1]["content"] == result["reply"]


def test_failed_source_repair_explains_why_no_change_is_not_a_completed_fix(tmp_path: Path):
    service = make_service(tmp_path)
    reply = service._source_repair_final_reply({
        "status": "failed",
        "provider": "gemini",
        "error_message": "CLI kết thúc nhưng không thay đổi file mã nguồn nào; không thể xác nhận đã sửa code.",
        "attempts": [{"provider": "gemini", "returncode": 0, "status": "completed"}],
        "source_changes": [],
    })

    assert "Gemini đã chạy và kết thúc bình thường" in reply
    assert "không ghi thay đổi nào vào file mã nguồn" in reply
    assert "yêu cầu sửa code vẫn chưa hoàn thành" in reply
    assert "không báo sai là đã sửa xong" in reply
    assert "Chạy lại tác vụ sửa" in reply


def test_producer_action_can_stop_footage_directly(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Producer stops footage"})
    calls = []

    def fake_control(job_id, action):
        calls.append((job_id, action))
        return {"ok": True, "control": {"state": "stop_requested"}, "job": service.get_job(job_id)}

    monkeypatch.setattr(service, "footage_control", fake_control)

    result, selected_job_id, ui_actions = service._execute_producer_action(
        {"type": "stop_footage", "job_id": job["id"]},
        job["id"],
    )

    assert calls == [(job["id"], "stop")]
    assert result["status"] == "ok"
    assert result["control_state"] == "stop_requested"
    assert selected_job_id == job["id"]
    assert {"type": "navigate", "tab": "footage"} in ui_actions


def test_running_footage_rerun_action_uses_restart_instead_of_start_guard(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Producer restarts running footage"})
    service.store.update(job["id"], {
        "status": "running",
        "current_phase": "footage",
        "phases": {"footage": {"status": "running"}},
    })
    calls = []

    def fake_restart(job_id):
        calls.append(job_id)
        return {"ok": True, "status": "restart_queued", "job_id": job_id}

    monkeypatch.setattr(service, "restart_footage", fake_restart, raising=False)

    result, _, _ = service._execute_producer_action(
        {"type": "rerun_phase", "job_id": job["id"], "phase": "footage"},
        job["id"],
    )

    assert calls == [job["id"]]
    assert result["status"] == "waiting"
    assert result["restart_status"] == "restart_queued"


def test_producer_chat_waits_until_queued_footage_restart_is_running(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Wait for real restart"})
    before = "2026-09-12T00:00:00+00:00"
    service.store.update(job["id"], {
        "status": "running",
        "current_phase": "footage",
        "phases": {"footage": {"status": "running", "started_at": before}},
    })
    snapshots = iter([
        {"status": "stopping", "current_phase": "footage", "phases": {"footage": {"status": "running", "started_at": before}}},
        {"status": "queued", "current_phase": "footage", "phases": {"footage": {"status": "queued", "started_at": before}}},
        {"status": "running", "current_phase": "footage", "phases": {"footage": {"status": "running", "started_at": "2026-09-12T00:01:00+00:00"}}},
    ])
    monkeypatch.setattr(service, "get_job", lambda _job_id: next(snapshots))
    monkeypatch.setattr(service_module.time, "sleep", lambda _seconds: None)
    events = []

    restarted = service._wait_for_footage_restart(
        job["id"], previous_started_at=before, event_callback=events.append, cancel_event=None,
    )

    assert restarted["status"] == "running"
    assert restarted["phases"]["footage"]["started_at"] != before
    assert any(event.get("stage") == "restarting" for event in events)


def test_producer_chat_can_dispatch_one_background_pipeline_action(tmp_path: Path, monkeypatch):
    class PipelineGateway(FakeGateway):
        def run_prompt_reusable(self, prompt, workspace, label, use_remotion_root=False, image_paths=None):
            return StageResult(
                0,
                json.dumps({
                    "reply": "Đã bắt đầu AI Visual → Edit.",
                    "actions": [{
                        "type": "run_pipeline",
                        "job_id": self.job_id,
                        "from_phase": "ai_visual",
                        "through_phase": "edit",
                    }],
                }, ensure_ascii=False),
                Path(workspace) / ".producer" / label,
            )

    gateway = PipelineGateway()
    service = make_service(tmp_path, gateway=gateway)
    job = service.create_job({"title": "Producer pipeline"})
    gateway.job_id = job["id"]
    calls = []

    def fake_run_pipeline(job_id, from_phase, through_phase, *, chairman_provider=None):
        calls.append((job_id, from_phase, through_phase))
        return {**service.get_job(job_id), "status": "queued", "current_phase": from_phase}

    monkeypatch.setattr(service, "run_pipeline", fake_run_pipeline, raising=False)

    result = service.producer_chat("thêm AI rồi edit", selected_job_id=job["id"], app_tab="codex")

    assert calls == [(job["id"], "ai_visual", "edit")]
    assert result["reply"] == "Đã bắt đầu AI Visual → Edit."
    assert result["actions"][0]["status"] == "ok"


def test_run_pipeline_queues_requested_phase_range_as_one_background_sequence(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Background producer pipeline", "visual_strategy": "hybrid"})
    service.store.update(job["id"], {
        "status": "ready",
        "phases": {
            "plan": {"status": "succeeded"},
            "voice": {"status": "succeeded"},
            "visuals": {"status": "succeeded"},
            "footage": {"status": "succeeded"},
            "ai_visual": {"status": "succeeded"},
            "edit": {"status": "succeeded"},
        },
    })
    submitted = {}

    class DummyFuture:
        def done(self):
            return False

    def fake_submit(fn, *args):
        submitted["fn"] = fn
        submitted["args"] = args
        return DummyFuture()

    monkeypatch.setattr(service._executor, "submit", fake_submit)

    queued = service.run_pipeline(job["id"], "ai_visual", "edit")

    assert submitted["fn"] == service._run_sequence
    assert submitted["args"] == (job["id"], ["ai_visual", "edit"])
    assert queued["status"] == "queued"
    assert queued["current_phase"] == "ai_visual"
    assert queued["phases"]["ai_visual"]["status"] == "pending"
    assert queued["phases"]["edit"]["status"] == "pending"
    assert queued["phases"]["qc"]["status"] == "pending"


def test_ai_visual_success_refreshes_coverage_snapshot_without_blocking(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Coverage refresh"})
    workspace = Path(job["workspace"])
    calls = []

    monkeypatch.setattr(
        service,
        "_run_phase",
        lambda current_job, phase, current_workspace: StageResult(
            returncode=0,
            last_message="AI Visual done",
            log_path=current_workspace / "ai_visual_manifest.json",
        ),
    )
    monkeypatch.setattr(service, "_validate_artifacts", lambda phase, current_workspace, current_job: None)
    monkeypatch.setattr(
        service_module,
        "build_preflight",
        lambda current_workspace: calls.append(Path(current_workspace)) or {
            "status": "FAIL",
            "missing_beats": ["B099"],
            "coverage_percent": 99,
        },
    )

    service._run_sequence(job["id"], ["ai_visual"])

    updated = service.get_job(job["id"])
    assert calls == [workspace]
    assert updated["phases"]["ai_visual"]["status"] == "succeeded"
    assert updated["status"] == "ready"


def test_producer_chat_context_reports_current_tab_pipeline_and_live_footage_progress(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Global Codex context"})
    workspace = Path(job["workspace"])
    service.store.update(job["id"], {
        "status": "running",
        "current_phase": "footage",
        "phases": {
            "plan": {"status": "succeeded"},
            "voice": {"status": "succeeded"},
            "visuals": {"status": "succeeded"},
            "footage": {"status": "running"},
        },
    })
    (workspace / "footage_checkpoint.json").write_text(json.dumps({
        "status": "running",
        "completed_beats": 12,
        "total_beats": 36,
        "status_message": "Đang tìm tư liệu B013-B016 · batch 4/9",
        "workers": {"codex": {"current_batch": 4, "total_batches": 9}},
    }), encoding="utf-8")
    (workspace / "asset_registry.json").write_text(json.dumps({
        "assets": [],
        "ai_fallback_beats": ["B013", "B014"],
    }), encoding="utf-8")

    context = service.producer_chat_context(job["id"], "footage")

    assert context["app_tab"] == "footage"
    assert context["selected_job"]["id"] == job["id"]
    assert context["selected_job"]["current_phase"] == "footage"
    assert context["selected_job"]["phase_number"] == 4
    assert context["selected_job"]["phases"]["plan"] == "succeeded"
    assert context["live_progress"] == {
        "phase": "footage",
        "completed": 12,
        "total": 36,
        "percent": 33,
        "status_message": "Đang tìm tư liệu B013-B016 · batch 4/9",
        "current_batch": 4,
        "total_batches": 9,
        "ai_fallback_count": 2,
        "ai_fallback_beat_ids": ["B013", "B014"],
    }


def test_footage_progress_snapshot_advances_during_tool_search(tmp_path: Path):
    service = make_service(tmp_path)
    snapshot = service._footage_progress_snapshot(tmp_path, {
        "status": "running",
        "completed_beats": 0,
        "total_beats": 271,
        "workers": {"codex": {"current_batch": 0, "total_batches": 68}},
        "tool_progress": {
            "stage": "searching",
            "completed_beats": 0,
            "total_beats": 271,
            "search_completed": 120,
            "search_total": 240,
            "search_provider": "yt_dlp",
            "search_query": "archival footage",
        },
    })

    assert snapshot["completed_beats"] == 0
    assert snapshot["percent"] == 10
    assert snapshot["tool_stage"] == "searching"
    assert snapshot["search_completed"] == 120
    assert snapshot["search_total"] == 240
    assert snapshot["display_completed"] == 120
    assert snapshot["display_total"] == 240
    assert snapshot["display_unit"] == "lượt"
    assert snapshot["display_label"] == "TOOLS ĐANG TÌM NGUỒN"


def test_footage_progress_snapshot_advances_during_semantic_rank(tmp_path: Path):
    service = make_service(tmp_path)
    snapshot = service._footage_progress_snapshot(tmp_path, {
        "status": "running",
        "completed_beats": 0,
        "total_beats": 271,
        "workers": {"codex": {"current_batch": 0, "total_batches": 68}},
        "tool_progress": {
            "stage": "ranking",
            "completed_beats": 0,
            "total_beats": 271,
            "search_completed": 240,
            "search_total": 240,
            "rank_completed": 136,
            "rank_total": 271,
        },
    })

    assert snapshot["percent"] == 25
    assert snapshot["tool_stage"] == "ranking"
    assert snapshot["rank_completed"] == 136
    assert snapshot["rank_total"] == 271
    assert snapshot["display_completed"] == 136
    assert snapshot["display_total"] == 271
    assert snapshot["display_unit"] == "beat"
    assert snapshot["display_label"] == "SEMANTIC RANK"


def test_producer_chat_prompt_receives_same_live_context_as_global_chat_ui(tmp_path: Path):
    gateway = ImageChatGateway()
    service = make_service(tmp_path, gateway=gateway)
    job = service.create_job({"title": "Context prompt"})
    service.store.update(job["id"], {"status": "running", "current_phase": "voice", "phases": {"voice": {"status": "running"}}})

    service.producer_chat("đang làm tới đâu", selected_job_id=job["id"], app_tab="voice")

    prompt = gateway.chat_calls[0]["prompt"]
    assert "CURRENT APP CONTEXT" in prompt
    assert '"app_tab": "voice"' in prompt
    assert '"current_phase": "voice"' in prompt


def test_micro_radar_feed_codex_audit_adjusts_confidence_and_is_cached(tmp_path: Path):
    gateway = RadarAuditGateway(verdict="approve", adjustment=-4)
    radar = FakeMicroRadarClient()
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=gateway,
        radar_client=radar,
        voice_engine=FakeVoice(),
        footage_coordinator=FakeFootage(),
        remotion_dir=tmp_path / "CofiRemotion",
    )

    first = service.radar_market_feed(22)
    second = service.radar_market_feed(22)

    candidate = first["emerging_themes"][0]
    assert candidate["win_confidence"] == 84.0
    assert candidate["audited_confidence"] == 80.0
    assert candidate["codex_verdict"] == "approve"
    assert candidate["codex_reasons"]
    assert first["codex_audit"]["status"] == "ok"
    assert second["emerging_themes"][0]["audited_confidence"] == 80.0
    assert gateway.audit_calls == 1


def test_micro_radar_feed_codex_reject_removes_candidate(tmp_path: Path):
    gateway = RadarAuditGateway(verdict="reject", adjustment=-20)
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=gateway,
        radar_client=FakeMicroRadarClient(),
        voice_engine=FakeVoice(),
        footage_coordinator=FakeFootage(),
        remotion_dir=tmp_path / "CofiRemotion",
    )

    feed = service.radar_market_feed(23)

    assert feed["emerging_themes"] == []
    assert feed["momentum_topics"] == []
    assert feed["counts"]["emerging_themes"] == 0
    assert feed["codex_audit"]["status"] == "ok"


def test_micro_radar_feed_watch_candidate_stays_out_of_go_list(tmp_path: Path):
    gateway = RadarAuditGateway(verdict="watch", adjustment=0)
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=gateway,
        radar_client=FakeMicroRadarClient(),
        voice_engine=FakeVoice(),
        footage_coordinator=FakeFootage(),
        remotion_dir=tmp_path / "CofiRemotion",
    )

    feed = service.radar_market_feed(24)

    assert feed["emerging_themes"] == []
    assert feed["momentum_topics"]
    assert feed["momentum_topics"][0]["audited_confidence"] < 80
    assert feed["momentum_topics"][0]["codex_verdict"] == "watch"


def test_documentary_can_save_ranked_radar_niche_for_channel_building(tmp_path: Path):
    radar = FakeMicroRadarClient()
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=FakeGateway(),
        radar_client=radar,
        voice_engine=FakeVoice(),
        footage_coordinator=FakeFootage(),
        remotion_dir=tmp_path / "CofiRemotion",
    )

    result = service.radar_save_niche(17, note="Top 5 #1 · chốt để xây kênh")

    assert result["ok"] is True
    assert result["ref_id"] == "17"
    assert radar.saved_niches == [(17, "Top 5 #1 · chốt để xây kênh")]


def test_continue_runs_exactly_one_phase_then_waits_for_user_review(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Topic"})

    service.start(job["id"], "all")
    service.wait(job["id"], timeout=5)
    after_plan = service.get_job(job["id"])

    assert after_plan["status"] == "ready"
    assert after_plan["phases"]["plan"]["status"] == "succeeded"
    assert after_plan["phases"]["voice"]["status"] == "pending"

    service.start(job["id"], "all")
    service.wait(job["id"], timeout=5)
    after_voice = service.get_job(job["id"])

    assert after_voice["phases"]["plan"]["status"] == "succeeded"
    assert after_voice["phases"]["voice"]["status"] == "succeeded"
    assert after_voice["phases"]["footage"]["status"] == "pending"


def test_export_progress_uses_real_render_and_combine_state(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Export progress"})
    workspace = Path(job["workspace"])
    service.store.update(job["id"], {
        "status": "running",
        "current_phase": "qc",
        "phases": {"qc": {"status": "running"}},
    })
    (workspace / "render_cache_manifest.json").write_text(json.dumps({
        "status": "rendering",
        "ready_chunks": 2,
        "total_chunks": 4,
    }), encoding="utf-8")

    rendering = service.export_progress(job["id"])
    assert rendering["stage"] == "rendering"
    assert rendering["percent"] == 40

    (workspace / "render_cache_manifest.json").write_text(json.dumps({
        "status": "ready",
        "ready_chunks": 4,
        "total_chunks": 4,
    }), encoding="utf-8")
    combine_log = workspace / ".render_cache" / "combine.log"
    combine_log.parent.mkdir(parents=True, exist_ok=True)
    combine_log.write_text("Combined 500/1000 frames (50.0%)", encoding="utf-8")

    combining = service.export_progress(job["id"])
    assert combining["stage"] == "combining"
    assert combining["combine_percent"] == 50.0
    assert combining["percent"] == 85

    (workspace / "render_manifest.json").write_text(json.dumps({"video_path": "release/video.mp4"}), encoding="utf-8")
    validating = service.export_progress(job["id"])
    assert validating["stage"] == "validating"
    assert validating["percent"] == 95

    service.store.update(job["id"], {
        "status": "completed",
        "current_phase": None,
        "phases": {"qc": {"status": "succeeded"}},
    })
    completed = service.export_progress(job["id"])
    assert completed["stage"] == "completed"
    assert completed["percent"] == 100


def test_qc_phase_exports_locally_without_calling_codex_director(tmp_path: Path, monkeypatch):
    gateway = FakeGateway()
    service = DocumentaryService(
        root=tmp_path,
        store=JobStore(tmp_path / "jobs"),
        gateway=gateway,
        voice_engine=FakeVoice(),
        footage_coordinator=FakeFootage(),
        render_cache=FakeExportRenderCache(),
        remotion_dir=tmp_path / "CofiRemotion",
    )
    job = service.create_job({"title": "Local export", "production_recipe": {"target_duration_sec": 120}})
    workspace = Path(job["workspace"])
    (workspace / "visual_manifest.json").write_text(json.dumps({
        "beats": [{"beat_id": "B001", "target_duration_sec": 120}],
    }), encoding="utf-8")
    (workspace / "render_cache_manifest.json").write_text(json.dumps({"status": "ready"}), encoding="utf-8")
    monkeypatch.setattr(service, "_probe_export_video", lambda path: {
        "duration_seconds": 120.0,
        "fps": 30.0,
        "width": 1920,
        "height": 1080,
        "video_frames": 3600,
        "audio_duration_seconds": 120.0,
        "has_audio": True,
    }, raising=False)
    monkeypatch.setattr(service, "_scan_export_content", lambda path, duration: {
        "black_segments": [], "silence_segments": [], "black_min_sec": 1.0, "silence_min_sec": 3.0,
    }, raising=False)

    result = service._run_phase(job, "qc", workspace)

    assert (job["id"], "qc") not in gateway.calls
    assert result.returncode == 0
    final_manifest = json.loads((workspace / "final_manifest.json").read_text(encoding="utf-8"))
    assert final_manifest["export_validation_mode"] == "technical_auto"
    assert final_manifest["viewer_qc_source"] == "edit_phase"
    assert final_manifest["video_frames"] == 3600
    assert "Codex" not in result.last_message


def test_codex_web_bridge_health_reports_offline_when_bridge_port_is_closed(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    monkeypatch.setattr(service, "_port_open", lambda host, port: False)

    bridge = service._chatgpt_web_bridge_health()

    assert bridge == {
        "ok": False,
        "address": "127.0.0.1:17841",
        "status": "offline",
        "active_job_id": None,
        "active_phase": None,
        "worker_status": None,
        "status_message": None,
        "completed_beats": None,
        "total_beats": None,
    }


def test_codex_web_bridge_health_reports_running_active_footage_worker(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Bridge status"})
    service.store.update(job["id"], {"status": "running", "current_phase": "footage"})
    service._active_job_id = job["id"]
    workspace = Path(job["workspace"])
    (workspace / "footage_checkpoint.json").write_text(json.dumps({
        "completed_beats": 4,
        "total_beats": 36,
        "status_message": "Đang tìm tư liệu B005-B008 · batch 2/9",
        "workers": {"codex": {"status": "running"}},
    }), encoding="utf-8")
    monkeypatch.setattr(service, "_port_open", lambda host, port: True)

    bridge = service._chatgpt_web_bridge_health()

    assert bridge["ok"] is True
    assert bridge["status"] == "running"
    assert bridge["active_job_id"] == job["id"]
    assert bridge["active_phase"] == "footage"
    assert bridge["worker_status"] == "running"
    assert bridge["completed_beats"] == 4
    assert bridge["total_beats"] == 36
    assert bridge["status_message"] == "Đang tìm tư liệu B005-B008 · batch 2/9"


def test_resume_recovers_completed_footage_checkpoint_before_starting_ai_visual(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Recover completed footage", "visual_strategy": "hybrid"})
    workspace = Path(job["workspace"])
    service.store.update(job["id"], {
        "status": "interrupted",
        "current_phase": "footage",
        "phases": {
            "plan": {"status": "succeeded"},
            "voice": {"status": "succeeded"},
            "visuals": {"status": "succeeded"},
            "footage": {"status": "interrupted", "error": "Phiên trước bị ngắt."},
        },
    })
    (workspace / "footage_checkpoint.json").write_text(json.dumps({
        "status": "completed",
        "completed_beats": 36,
        "total_beats": 36,
        "workers": {"codex": {"status": "completed"}},
    }), encoding="utf-8")
    calls = []
    monkeypatch.setattr(service, "_run_sequence", lambda job_id, phases: calls.append((job_id, phases)))

    resumed = service.start(job["id"], "all")
    service.wait(job["id"], timeout=5)

    updated = service.get_job(job["id"])
    assert resumed["current_phase"] == "ai_visual"
    assert updated["phases"]["footage"]["status"] == "succeeded"
    assert updated["phases"]["footage"]["error"] is None
    assert calls == [(job["id"], ["ai_visual"])]


def test_resume_recovers_completed_footage_checkpoint_when_job_is_ready_without_current_phase(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Recover completed repair from ready state", "visual_strategy": "hybrid"})
    workspace = Path(job["workspace"])
    service.store.update(job["id"], {
        "status": "ready",
        "current_phase": None,
        "footage_repair_beat_ids": ["B003", "B007"],
        "phases": {
            "plan": {"status": "succeeded"},
            "voice": {"status": "succeeded"},
            "visuals": {"status": "succeeded"},
            "footage": {"status": "pending"},
        },
    })
    (workspace / "footage_checkpoint.json").write_text(json.dumps({
        "status": "completed",
        "completed_beats": 36,
        "total_beats": 36,
        "workers": {"codex": {"status": "completed"}},
    }), encoding="utf-8")
    calls = []
    monkeypatch.setattr(service, "_run_sequence", lambda job_id, phases: calls.append((job_id, phases)))

    resumed = service.start(job["id"], "all")
    service.wait(job["id"], timeout=5)

    updated = service.get_job(job["id"])
    assert resumed["current_phase"] == "ai_visual"
    assert updated["phases"]["footage"]["status"] == "succeeded"
    assert updated["footage_repair_beat_ids"] == []
    assert calls == [(job["id"], ["ai_visual"])]


def test_rerun_footage_uses_fresh_tools_first_full_run_instead_of_legacy_research_repair(tmp_path: Path, monkeypatch):
    footage = RepairTrackingFootage()
    service = make_service(tmp_path, footage_coordinator=footage)
    job = service.create_job({"title": "Repair missing coverage"})
    workspace = Path(service.get_job(job["id"])["workspace"])
    (workspace / "preflight_report.json").write_text(json.dumps({
        "status": "FAIL",
        "missing_beats": ["B003", "B007"],
        "coverage_percent": 80,
    }), encoding="utf-8")
    (workspace / "visual_manifest.json").write_text(json.dumps({
        "beats": [{"beat_id": "B001", "narration_text": "test"}],
    }), encoding="utf-8")
    service.store.update(job["id"], {
        "status": "ready",
        "current_phase": None,
        "phases": {
            "plan": {"status": "succeeded"},
            "voice": {"status": "succeeded"},
            "visuals": {"status": "succeeded"},
            "footage": {"status": "succeeded"},
        },
    })
    monkeypatch.setattr(service, "_validate_artifacts", lambda phase, workspace, job: None)

    service.rerun(job["id"], "footage")
    service.wait(job["id"], timeout=5)

    updated = service.get_job(job["id"])
    assert footage.full_runs == 1
    assert footage.repairs == []
    assert updated["phases"]["footage"]["status"] == "succeeded"
    assert updated.get("footage_repair_beat_ids") == []


def test_footage_control_updates_real_coordinator_control_state(tmp_path: Path):
    class ControlledFootage(FakeFootage):
        def __init__(self):
            self.states = {}

        def set_control(self, workspace, state):
            key = str(Path(workspace).resolve())
            self.states[key] = state
            return {"state": state}

        def control_state(self, workspace):
            return {"state": self.states.get(str(Path(workspace).resolve()), "running")}

    footage = ControlledFootage()
    service = make_service(tmp_path, footage_coordinator=footage)
    job = service.create_job({"title": "Footage controls"})
    service.store.update(job["id"], {
        "status": "running",
        "current_phase": "footage",
        "phases": {"footage": {"status": "running"}},
    })

    paused = service.footage_control(job["id"], "pause")
    resumed = service.footage_control(job["id"], "resume")
    stopped = service.footage_control(job["id"], "stop")

    assert paused["control"]["state"] == "paused"
    assert resumed["control"]["state"] == "running"
    assert stopped["control"]["state"] == "stop_requested"


def test_restart_footage_stops_active_worker_then_resumes_checkpoint_after_it_finishes(tmp_path: Path, monkeypatch):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Restart active footage"})
    service.store.update(job["id"], {
        "status": "running",
        "current_phase": "footage",
        "phases": {"footage": {"status": "running"}},
    })
    checkpoint_path = Path(job["workspace"]) / "footage_checkpoint.json"
    checkpoint_path.write_text(json.dumps({
        "status": "stopped",
        "control_state": "stopped",
        "completed_beats": 72,
        "workers": {"codex": {"completed_beat_ids": ["B001", "B002"]}},
    }), encoding="utf-8")
    active = Future()
    service._active_job_id = job["id"]
    service._active_future = active
    calls = []

    monkeypatch.setattr(
        service,
        "footage_control",
        lambda job_id, action: calls.append(("control", job_id, action)) or {"ok": True},
    )
    monkeypatch.setattr(
        service,
        "start",
        lambda job_id, phase: calls.append(("start", job_id, phase)) or service.get_job(job_id),
    )
    monkeypatch.setattr(
        service,
        "rerun",
        lambda _job_id, _phase: (_ for _ in ()).throw(AssertionError("restart must preserve the Footage checkpoint")),
    )

    result = service.restart_footage(job["id"])

    assert result["status"] == "restart_queued"
    assert calls == [("control", job["id"], "stop")]
    active.set_result(None)
    assert calls[-1] == ("start", job["id"], "footage")
    resumed_checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert resumed_checkpoint["status"] == "running"
    assert resumed_checkpoint["completed_beats"] == 72
    assert resumed_checkpoint["workers"]["codex"]["completed_beat_ids"] == ["B001", "B002"]


def test_footage_stop_result_marks_phase_interrupted_instead_of_failed(tmp_path: Path, monkeypatch):
    class StoppingFootage(FakeFootage):
        def run(self, job, workspace):
            return StageResult(130, "Đã dừng tìm tư liệu theo yêu cầu.", Path(workspace) / "footage_control.json")

    service = make_service(tmp_path, footage_coordinator=StoppingFootage())
    job = service.create_job({"title": "Stop footage"})
    service.store.update(job["id"], {
        "status": "ready",
        "current_phase": None,
        "phases": {
            "plan": {"status": "succeeded"},
            "voice": {"status": "succeeded"},
            "visuals": {"status": "succeeded"},
            "footage": {"status": "pending"},
        },
    })

    service.start(job["id"], "footage")
    service.wait(job["id"], timeout=5)

    updated = service.get_job(job["id"])
    assert updated["status"] == "ready"
    assert updated["current_phase"] is None
    assert updated["phases"]["footage"]["status"] == "interrupted"
    assert updated["phases"]["footage"]["error"] is None


def test_plan_accepts_valid_artifacts_when_engine_exits_after_writing_them(tmp_path: Path):
    service = make_service(tmp_path, gateway=FailsAfterWritingPlanGateway())
    job = service.create_job({"title": "Artifact recovery"})

    service.start(job["id"], "plan")
    service.wait(job["id"], timeout=5)
    updated = service.get_job(job["id"])

    assert updated["status"] == "ready"
    assert updated["current_phase"] is None
    assert updated["phases"]["plan"]["status"] == "succeeded"


def test_only_one_job_runs_at_a_time(tmp_path: Path):
    blocker = threading.Event()
    service = make_service(tmp_path, gateway=FakeGateway(blocker))
    first = service.create_job({"title": "One"})
    second = service.create_job({"title": "Two"})

    service.start(first["id"], "plan")
    with pytest.raises(RuntimeError, match="another job"):
        service.start(second["id"], "plan")
    blocker.set()
    service.wait(first["id"], timeout=5)


def test_quality_contract_scales_to_thirty_minutes(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Long documentary", "target_duration_minutes": 30})
    contract = job["production_recipe"]["quality_contract"]

    assert job["production_recipe"]["target_duration_sec"] == 1800
    assert contract["min_scene_count"] >= 48
    assert contract["min_video_clip_uses"] >= 80
    assert contract["min_native_motion_treatments"] == 0
    assert contract["allow_standalone_native_motion"] is False
    assert contract["require_media_anchored_annotation_motion"] is True


def test_job_rejects_duration_outside_two_to_thirty_minutes(tmp_path: Path):
    service = make_service(tmp_path)
    with pytest.raises(ValueError, match="between 2 and 30 minutes"):
        service.create_job({"title": "Too short", "target_duration_minutes": 1})


def test_footage_quality_gate_accepts_explicit_ai_fallback_without_real_clip_quota(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Quality gate", "target_duration_minutes": 2, "visual_strategy": "hybrid"})
    workspace = Path(job["workspace"])
    contract = job["production_recipe"]["quality_contract"]
    scene_ids = [f"B{i + 1:03d}" for i in range(contract["min_scene_count"])]
    (workspace / "visual_manifest.json").write_text(json.dumps({
        "target_duration_sec": 120,
        "beats": [{"beat_id": scene_id} for scene_id in scene_ids],
    }), encoding="utf-8")
    (workspace / "footage_codex.json").write_text("{}", encoding="utf-8")
    (workspace / "footage_gemini.json").write_text("{}", encoding="utf-8")
    (workspace / "footage_review.json").write_text(json.dumps({"candidates": []}), encoding="utf-8")
    (workspace / "asset_registry.json").write_text(json.dumps({
        "assets": [],
        "native_treatments": [],
        "ai_fallback_beats": scene_ids,
    }), encoding="utf-8")

    service._validate_artifacts("footage", workspace, job)


def test_footage_quality_gate_keeps_must_real_as_hard_requirement(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "Must real gate", "target_duration_minutes": 2})
    workspace = Path(job["workspace"])
    contract = job["production_recipe"]["quality_contract"]
    scene_ids = [f"B{i + 1:03d}" for i in range(contract["min_scene_count"])]
    beats = [{"beat_id": scene_id} for scene_id in scene_ids]
    beats[0]["source_priority"] = "must_real"
    (workspace / "visual_manifest.json").write_text(json.dumps({
        "target_duration_sec": 120,
        "beats": beats,
    }), encoding="utf-8")
    (workspace / "footage_codex.json").write_text("{}", encoding="utf-8")
    (workspace / "footage_gemini.json").write_text("{}", encoding="utf-8")
    (workspace / "footage_review.json").write_text(json.dumps({"candidates": []}), encoding="utf-8")
    (workspace / "asset_registry.json").write_text(json.dumps({
        "assets": [],
        "native_treatments": [],
        "ai_fallback_beats": scene_ids,
    }), encoding="utf-8")

    with pytest.raises(RuntimeError, match="missing must_real source coverage: B001"):
        service._validate_artifacts("footage", workspace, job)


def test_producer_chat_context_reports_ai_visual_pause_and_error_details(tmp_path: Path):
    service = make_service(tmp_path)
    job = service.create_job({"title": "AI Visual context test"})
    workspace = Path(job["workspace"])
    service.store.update(job["id"], {
        "status": "running",
        "current_phase": "ai_visual",
        "phases": {
            "plan": {"status": "succeeded"},
            "voice": {"status": "succeeded"},
            "visuals": {"status": "succeeded"},
            "footage": {"status": "succeeded"},
            "ai_visual": {"status": "running"},
        },
    })
    (workspace / "ai_visual_manifest.json").write_text(json.dumps({
        "status": "paused",
        "pause_warning": "Tất cả tài khoản Google Flow đều bị tạm dừng",
        "target_beat_ids": ["B001", "B002"],
        "remaining_missing_beats": ["B002"],
        "current_beat_id": "B002",
        "generated": [{"beat_id": "B001", "image_path": "img.png"}],
        "errors": [{"beat_id": "B002", "stage": "image", "error": "HTTP 429 Too Many Requests"}],
    }), encoding="utf-8")

    context = service.producer_chat_context(job["id"], "overview")

    assert context["app_tab"] == "overview"
    live = context["live_progress"]
    assert live["phase"] == "ai_visual"
    assert live["completed"] == 1
    assert live["total"] == 2
    assert live["percent"] == 50
    assert live["is_paused"] is True
    assert "Tất cả tài khoản Google Flow" in live["pause_warning"]
    assert "[TẠM DỪNG]" in live["status_message"]
    assert live["error_count"] == 1
    assert live["last_error"] == "HTTP 429 Too Many Requests"
    assert live["current_beat_id"] == "B002"
