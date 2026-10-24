from pathlib import Path

from runtime_logs import prepare_log


def test_runtime_logs_stay_in_dedicated_folder_and_limit_old_files(tmp_path: Path):
    logs = tmp_path / "logs"
    logs.mkdir()
    for number in range(8):
        (logs / f"backend-20260901-00000{number}-1.log").write_text("old", encoding="utf-8")
    other = logs / "desktop-20260901-000000-1.log"
    other.write_text("keep", encoding="utf-8")

    current = prepare_log(tmp_path, "backend", keep=7)

    assert current.parent == logs
    assert current.exists()
    assert len(list(logs.glob("backend-*.log"))) == 7
    assert other.exists()


def test_launchers_write_through_runtime_log_directory():
    root = Path(__file__).resolve().parents[1]
    for launcher, kind in (("run.bat", "backend"), ("run_desktop.bat", "desktop")):
        source = (root / launcher).read_text(encoding="utf-8")
        assert f"runtime_logs.py {kind}" in source
        assert '"%COFI_RUNTIME_LOG%"' in source
