from pathlib import Path

from documentary.store import JobStore


def test_store_creates_persistent_job_with_phase_defaults(tmp_path: Path):
    store = JobStore(tmp_path / "jobs")
    job = store.create({"title": "Nepal flood", "workspace": str(tmp_path / "workspace")})

    assert job["id"]
    assert job["title"] == "Nepal flood"
    assert job["status"] == "ready"
    assert list(job["phases"]) == ["plan", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc"]
    assert all(item["status"] == "pending" for item in job["phases"].values())
    assert store.get(job["id"])["title"] == "Nepal flood"


def test_store_update_merges_top_level_fields(tmp_path: Path):
    store = JobStore(tmp_path / "jobs")
    job = store.create({"title": "A", "workspace": str(tmp_path / "workspace")})

    updated = store.update(job["id"], {"status": "running", "current_phase": "plan"})

    assert updated["status"] == "running"
    assert updated["current_phase"] == "plan"
    assert store.list()[0]["id"] == job["id"]


def test_store_migrates_legacy_project_past_footage_as_visuals_succeeded(tmp_path: Path):
    store = JobStore(tmp_path / "jobs")
    job = store.create({"title": "Legacy", "workspace": str(tmp_path / "workspace")})
    path = store._path(job["id"])
    raw = __import__("json").loads(path.read_text(encoding="utf-8"))
    raw["phases"].pop("visuals", None)
    raw["phases"]["footage"]["status"] = "succeeded"
    path.write_text(__import__("json").dumps(raw), encoding="utf-8")

    migrated = store.get(job["id"])

    assert migrated["phases"]["visuals"]["status"] == "succeeded"
    assert "Legacy project" in migrated["phases"]["visuals"]["last_message"]


def test_store_recovers_running_job_as_interrupted(tmp_path: Path):
    store = JobStore(tmp_path / "jobs")
    job = store.create({"title": "Dang do", "workspace": str(tmp_path / "workspace")})
    store.update(job["id"], {
        "status": "running",
        "current_phase": "footage",
        "phases": {"footage": {"status": "running"}},
    })

    recovered = store.recover_interrupted()
    current = store.get(job["id"])

    assert job["id"] in recovered
    assert current["status"] == "interrupted"
    assert current["phases"]["footage"]["status"] == "interrupted"

