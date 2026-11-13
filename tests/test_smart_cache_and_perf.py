from __future__ import annotations

import json
from pathlib import Path

from documentary.cache_manager import (
    auto_hygiene_after_job_export,
    clean_smart_cache,
    scan_cache_report,
)
from documentary.store import JobStore


def _create_mock_job_workspace(
    workspaces_dir: Path,
    job_id: str,
    *,
    status: str = "completed",
    has_release_mp4: bool = True,
) -> tuple[Path, dict]:
    ws = workspaces_dir / job_id
    ws.mkdir(parents=True, exist_ok=True)
    if has_release_mp4:
        rel_dir = ws / "release"
        rel_dir.mkdir(parents=True, exist_ok=True)
        (rel_dir / "final_video.mp4").write_bytes(b"V" * (600 * 1024))

    # Protected files
    (ws / "script.md").write_text("# Script", encoding="utf-8")
    (ws / "visual_manifest.json").write_text('{"beats":[]}', encoding="utf-8")
    audio_dir = ws / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    (audio_dir / "narration.wav").write_bytes(b"W" * 4096)
    (ws / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    thumb_dir = ws / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    (thumb_dir / "thumb.jpg").write_bytes(b"T" * 2048)

    # Tier 1 ephemeral render cache
    rc_dir = ws / ".render_cache" / "universal_segments"
    rc_dir.mkdir(parents=True, exist_ok=True)
    (rc_dir / "seg_001.mp4").write_bytes(b"S" * 8192)

    # Tier 2 intermediate files
    beats_dir = ws / "audio" / "beats"
    beats_dir.mkdir(parents=True, exist_ok=True)
    (beats_dir / "B001.wav").write_bytes(b"B" * 4096)
    edit_plates_dir = ws / "media" / "edit_plates"
    edit_plates_dir.mkdir(parents=True, exist_ok=True)
    (edit_plates_dir / "plate1.jpg").write_bytes(b"P" * 4096)
    media_clip_dir = ws / "media" / "footage"
    media_clip_dir.mkdir(parents=True, exist_ok=True)
    (media_clip_dir / "B001_clip.mp4").write_bytes(b"C" * 8192)

    job = {
        "id": job_id,
        "title": f"Title {job_id}",
        "status": status,
        "workspace": str(ws),
        "phases": {
            "qc": {"status": "succeeded" if status == "completed" else status},
        },
    }
    (ws / "job.json").write_text(json.dumps(job), encoding="utf-8")
    return ws, job


def test_job_store_mtime_cache_avoids_redundant_disk_reads(tmp_path: Path, monkeypatch):
    store = JobStore(tmp_path)
    created = store.create({"id": "job-cache-1", "title": "Cache Test"})
    assert created["id"] == "job-cache-1"

    # Prime the cache
    first = store.get("job-cache-1")
    assert first is not None
    assert first["title"] == "Cache Test"

    read_calls = 0
    orig_read_text = Path.read_text

    def counting_read_text(self: Path, *args, **kwargs):
        nonlocal read_calls
        if self.name == "job.json":
            read_calls += 1
        return orig_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)

    # Subsequent get() and list() with unchanged mtime/size must hit RAM cache (0 disk reads)
    second = store.get("job-cache-1")
    listed = store.list()
    assert second is not None and second["title"] == "Cache Test"
    assert len(listed) == 1
    assert read_calls == 0

    # Updating the job updates the cache and persists to disk
    updated = store.update("job-cache-1", {"title": "Updated Title"})
    assert updated["title"] == "Updated Title"
    assert store.get("job-cache-1")["title"] == "Updated Title"


def test_smart_cache_protects_running_jobs_and_preserves_deliverables(tmp_path: Path):
    workspaces_dir = tmp_path / "workspaces"
    remotion_dir = tmp_path / "CofiRemotion"
    pub_jobs = remotion_dir / "public" / "jobs"
    pub_jobs.mkdir(parents=True)

    ws_done, job_done = _create_mock_job_workspace(workspaces_dir, "job-done", status="completed", has_release_mp4=True)
    ws_run, job_run = _create_mock_job_workspace(workspaces_dir, "job-running", status="running", has_release_mp4=False)
    ws_sel, job_sel = _create_mock_job_workspace(workspaces_dir, "job-selected", status="completed", has_release_mp4=True)

    for jid in ("job-done", "job-running", "job-selected"):
        m_dir = pub_jobs / jid
        m_dir.mkdir(parents=True, exist_ok=True)
        (m_dir / "mirror.mp4").write_bytes(b"M" * 4096)

    jobs = [job_done, job_run, job_sel]
    report = scan_cache_report(
        workspaces_dir=workspaces_dir,
        remotion_dir=remotion_dir,
        jobs=jobs,
        active_job_ids={"job-running"},
        selected_job_id="job-selected",
    )
    assert report["ok"] is True
    # Only job-done's mirror in public/jobs should be marked for Tier 1 removal
    assert report["tiers"]["safe_ephemeral"]["breakdown"]["remotion_public_mirror"]["jobs_count"] == 1
    # Both job-done and job-selected have completed .render_cache
    assert report["tiers"]["safe_ephemeral"]["breakdown"]["render_cache"]["jobs_count"] == 2
    assert report["tiers"]["slim_completed"]["jobs_count"] == 2

    # Execute Tier 1 (safe_ephemeral)
    res_t1 = clean_smart_cache(
        mode="safe_ephemeral",
        workspaces_dir=workspaces_dir,
        remotion_dir=remotion_dir,
        jobs=jobs,
        active_job_ids={"job-running"},
        selected_job_id="job-selected",
        reclaim_ram=False,
    )
    assert res_t1["ok"] is True
    assert not (pub_jobs / "job-done").exists()
    assert (pub_jobs / "job-running").exists()
    assert (pub_jobs / "job-selected").exists()
    assert not (ws_done / ".render_cache").exists()
    assert (ws_run / ".render_cache").exists()
    # Tier 2 files untouched in Tier 1 mode
    assert (ws_done / "audio" / "beats" / "B001.wav").exists()

    # Execute Tier 2 (slim_completed)
    res_t2 = clean_smart_cache(
        mode="slim_completed",
        workspaces_dir=workspaces_dir,
        remotion_dir=remotion_dir,
        jobs=jobs,
        active_job_ids={"job-running"},
        selected_job_id="job-selected",
        reclaim_ram=False,
    )
    assert res_t2["ok"] is True
    # Intermediate beats & edit_plates removed on completed job
    assert not (ws_done / "audio" / "beats").exists()
    assert not (ws_done / "media" / "edit_plates").exists()
    # Core deliverables 100% preserved!
    assert (ws_done / "release" / "final_video.mp4").exists()
    assert (ws_done / "audio" / "narration.wav").exists()
    assert (ws_done / "subtitles.srt").exists()
    assert (ws_done / "script.md").exists()
    assert (ws_done / "thumbnails" / "thumb.jpg").exists()
    assert (ws_done / "media" / "footage" / "B001_clip.mp4").exists()
    # Running job 100% untouched!
    assert (ws_run / "audio" / "beats" / "B001.wav").exists()


def test_auto_hygiene_after_job_export_cleans_render_cache_and_old_mirrors(tmp_path: Path):
    workspaces_dir = tmp_path / "workspaces"
    remotion_dir = tmp_path / "CofiRemotion"
    pub_jobs = remotion_dir / "public" / "jobs"
    pub_jobs.mkdir(parents=True)

    ws_done, _ = _create_mock_job_workspace(workspaces_dir, "job-new", status="completed", has_release_mp4=True)
    for jid in ("job-old-1", "job-old-2", "job-new"):
        d = pub_jobs / jid
        d.mkdir(parents=True, exist_ok=True)
        (d / "asset.mp4").write_bytes(b"A" * 4096)

    res = auto_hygiene_after_job_export(
        workspace=ws_done,
        job_id="job-new",
        remotion_dir=remotion_dir,
        active_job_ids=set(),
    )
    assert res["ok"] is True
    assert not (ws_done / ".render_cache").exists()
    assert (pub_jobs / "job-new").exists()
    assert not (pub_jobs / "job-old-1").exists()
    assert not (pub_jobs / "job-old-2").exists()
