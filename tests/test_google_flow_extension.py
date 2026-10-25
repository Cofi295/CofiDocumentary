import json
from pathlib import Path

from vendor.media_factory.backend.app.providers.google import BrowserLoginWorker


EXTENSION_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "media_factory" / "extension"


def test_flow_extension_is_loadable_and_scoped_to_local_controller():
    manifest = json.loads((EXTENSION_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == 3
    assert "update_url" not in manifest
    assert manifest["background"]["service_worker"] == "background.js"
    assert manifest["action"]["default_popup"] == "popup.html"
    assert "http://127.0.0.1/*" in manifest["host_permissions"]
    assert "https://flow.google.com/*" in manifest["content_scripts"][0]["matches"]
    assert "https://labs.google/*" in manifest["content_scripts"][0]["matches"]


def test_flow_extension_controls_accounts_and_shared_job_queue():
    source = "\n".join(
        (EXTENSION_ROOT / name).read_text(encoding="utf-8")
        for name in ("background.js", "content.js", "popup.js")
    )

    for endpoint in (
        "/sync/config",
        "/sync/theme",
        "/sync/render",
    ):
        assert endpoint in source
    assert "_throttleMedia" in source
    assert "X-Tab-Status" in source
    assert "X-Ext-Id" in source


def test_flow_worker_loads_bundled_extension_when_manifest_exists(tmp_path):
    extension_dir = tmp_path / "extension"
    extension_dir.mkdir()
    (extension_dir / "manifest.json").write_text("{}", encoding="utf-8")

    args = BrowserLoginWorker._extension_launch_args(extension_dir)

    assert args == [
        f"--disable-extensions-except={extension_dir.resolve()}",
        f"--load-extension={extension_dir.resolve()}",
    ]


def test_hidden_worker_uses_real_chrome_window_instead_of_headless_mode():
    args = BrowserLoginWorker._hidden_worker_launch_args()

    assert "--headless=new" not in args
    assert "--disable-gpu" not in args
    assert "--new-window" in args
    assert "--window-position=9999,9999" in args


def test_auth_bridge_never_dispatches_tasks_to_closed_tab_peers():
    from vendor.media_factory.backend.app.providers.auth_bridge import ExtensionAuthBridge

    bridge = ExtensionAuthBridge(port=0)
    bridge._pending_tasks.append({
        "requestId": "req-1",
        "siteKey": "site-key",
        "action": "IMAGE_GENERATION",
        "enqueued_at": 100.0,
    })

    assert bridge.pop_pending_task(tab_status="closed", ext_id="desktop-chrome") is None
    assert bridge.pop_pending_task(tab_status="missing", ext_id="desktop-chrome") is None
    assert len(bridge._pending_tasks) == 1

    popped = bridge.pop_pending_task(tab_status="ready", ext_id="flow-worker")
    assert popped is not None
    assert popped["requestId"] == "req-1"


