import threading
import time

from vendor.media_factory.backend.app.db import Database
from vendor.media_factory.backend.app.providers.google import (
    BrowserLoginWorker,
    FLOW_AUTH_SESSION_URL,
    FLOW_HOME_URL,
    GoogleFlowAccountManager,
    GoogleFlowBrowserClient,
)


class _SecretStore:
    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}

    def get_google_session(self, account_id: str) -> dict | None:
        return self.sessions.get(account_id)

    def set_google_session(self, account_id: str, payload: dict) -> None:
        self.sessions[account_id] = payload

    def delete_google_session(self, account_id: str) -> None:
        self.sessions.pop(account_id, None)


class _NoopLoginWorker:
    @staticmethod
    def has_live_session(_account_id: str) -> bool:
        return False


class _RecordingResumeWorker:
    def __init__(self) -> None:
        self.resumed: list[tuple[str, object]] = []

    @staticmethod
    def has_reusable_profile(_profile_dir) -> bool:
        return True

    def resume_session(self, account_id, profile_dir, _on_complete, _on_error) -> None:
        self.resumed.append((account_id, profile_dir))


def _start_live_session(worker: BrowserLoginWorker, account_id: str):
    thread = threading.Thread(
        target=worker._serve_live_session,
        args=(account_id, object()),
        daemon=True,
    )
    thread.start()
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and not worker.has_live_session(account_id):
        time.sleep(0.01)
    assert worker.has_live_session(account_id)
    return thread


def test_resume_waits_for_previous_capture_thread_to_finish(tmp_path, monkeypatch):
    worker = BrowserLoginWorker()
    account_id = "account-1"
    capture_started = threading.Event()

    def fake_capture(*_args, **_kwargs):
        capture_started.set()

    monkeypatch.setattr(worker, "_capture_session", fake_capture)

    with worker._live_sessions_lock:
        worker._starting_sessions.add(account_id)

    def finish_previous_capture():
        time.sleep(0.05)
        with worker._live_sessions_lock:
            worker._starting_sessions.discard(account_id)

    previous = threading.Thread(target=finish_previous_capture, daemon=True)
    previous.start()

    worker.resume_session(account_id, tmp_path, lambda *_args, **_kwargs: None, lambda *_args: None)
    previous.join(timeout=1.0)

    assert capture_started.wait(0.5), "resume_session dropped the restart while the old capture thread was exiting"


def test_live_session_command_timeout_starts_when_callback_begins():
    worker = BrowserLoginWorker()
    account_id = "account-timeout"
    session_thread = _start_live_session(worker, account_id)
    first_started = threading.Event()
    release_first = threading.Event()
    second_result: dict[str, object] = {}

    def first_callback(_context):
        first_started.set()
        release_first.wait(1.0)
        return "first"

    first_thread = threading.Thread(
        target=lambda: worker.execute_in_session(account_id, first_callback, timeout_seconds=1.0),
        daemon=True,
    )
    first_thread.start()
    assert first_started.wait(0.5)

    def run_second():
        try:
            second_result["value"] = worker.execute_in_session(
                account_id,
                lambda _context: "second",
                timeout_seconds=0.05,
            )
        except BaseException as exc:
            second_result["error"] = exc

    second_thread = threading.Thread(target=run_second, daemon=True)
    second_thread.start()
    time.sleep(0.1)
    release_first.set()
    second_thread.join(timeout=1.0)
    first_thread.join(timeout=1.0)
    worker.close_session(account_id)
    session_thread.join(timeout=1.0)

    assert second_result.get("value") == "second"
    assert "error" not in second_result


def test_live_session_prioritizes_submit_over_queued_poll():
    worker = BrowserLoginWorker()
    account_id = "account-priority"
    session_thread = _start_live_session(worker, account_id)
    blocker_started = threading.Event()
    release_blocker = threading.Event()
    execution_order: list[str] = []

    def blocker(_context):
        execution_order.append("blocker")
        blocker_started.set()
        release_blocker.wait(1.0)
        return "blocker"

    blocker_thread = threading.Thread(
        target=lambda: worker.execute_in_session(account_id, blocker, timeout_seconds=1.0, priority=5),
        daemon=True,
    )
    blocker_thread.start()
    assert blocker_started.wait(0.5)

    poll_thread = threading.Thread(
        target=lambda: worker.execute_in_session(
            account_id,
            lambda _context: execution_order.append("poll") or "poll",
            timeout_seconds=1.0,
            priority=10,
        ),
        daemon=True,
    )
    poll_thread.start()
    time.sleep(0.03)
    submit_thread = threading.Thread(
        target=lambda: worker.execute_in_session(
            account_id,
            lambda _context: execution_order.append("submit") or "submit",
            timeout_seconds=1.0,
            priority=0,
        ),
        daemon=True,
    )
    submit_thread.start()
    time.sleep(0.03)
    release_blocker.set()

    for thread in (blocker_thread, poll_thread, submit_thread):
        thread.join(timeout=1.0)
    worker.close_session(account_id)
    session_thread.join(timeout=1.0)

    assert execution_order == ["blocker", "submit", "poll"]


def test_recaptcha_retry_stays_on_dedicated_flow_site(tmp_path):
    class FakePage:
        def __init__(self):
            self.evaluations = 0
            self.goto_urls: list[str] = []

        def evaluate(self, _script, _action):
            self.evaluations += 1
            if self.evaluations == 1:
                return {"token": None, "error": "Service not ready"}
            return {"token": "flow-token", "error": None}

        def goto(self, url, **_kwargs):
            self.goto_urls.append(url)

        def wait_for_timeout(self, _ms):
            return None

    page = FakePage()
    client = GoogleFlowBrowserClient(tmp_path, session_worker=None)

    assert client._mint_flow_recaptcha(page, "FLOW_IMAGE_GENERATION") == "flow-token"
    assert page.goto_urls == [FLOW_HOME_URL]
    assert FLOW_HOME_URL == "https://flow.google.com/"
    assert FLOW_AUTH_SESSION_URL == "https://labs.google/fx/api/auth/session"


def test_migrated_flow_profile_can_be_recognized_without_legacy_nextauth_cookie():
    class FakeLocator:
        def __init__(self, count: int):
            self._count = count

        def count(self):
            return self._count

    class FakePage:
        url = "https://flow.google.com/"

        def locator(self, selector):
            if selector == 'a[href*="/project/"]':
                return FakeLocator(1)
            return FakeLocator(0)

    assert BrowserLoginWorker._migrated_profile_ready(FakePage()) is True


def test_migrated_capture_keeps_existing_account_identity_and_tier(tmp_path):
    db = Database(tmp_path / "media_factory.db")
    secrets = _SecretStore()
    manager = GoogleFlowAccountManager(
        db,
        secrets,  # type: ignore[arg-type]
        profile_root=tmp_path / "profiles",
        login_worker=_NoopLoginWorker(),  # type: ignore[arg-type]
    )
    account = manager.create_account()
    account_id = account["id"]
    db.patch_resource(
        "google_flow_account",
        account_id,
        {
            "email": "owner@example.com",
            "tier": "ultra",
            "credits": 12345,
            "session_expires_at": "2026-10-20T00:00:00+00:00",
        },
    )

    updated = manager.complete_login(
        account_id,
        email="",
        tier="unknown",
        credits=None,
        session_secret={"cookies": [{"name": "SID"}], "migrated_host": True},
        session_expires_at=None,
    )

    assert updated["status"] == "ready"
    assert updated["email"] == "owner@example.com"
    assert updated["tier"] == "ultra"
    assert updated["credits"] == 12345
    assert updated["session_expires_at"] == "2026-10-20T00:00:00+00:00"
    assert secrets.sessions[account_id]["migrated_host"] is True


def test_saved_chrome_profile_is_reusable_after_browser_stops(tmp_path):
    profile_dir = tmp_path / "profiles" / "account-1"
    cookie_db = profile_dir / "Default" / "Network" / "Cookies"
    cookie_db.parent.mkdir(parents=True)
    cookie_db.write_bytes(b"persisted chrome cookie database")
    (profile_dir / "Local State").write_text("{}", encoding="utf-8")

    worker = BrowserLoginWorker()

    assert worker.has_reusable_profile(profile_dir) is True


def test_stale_debug_port_marker_cannot_attach_another_apps_chrome(tmp_path, monkeypatch):
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    (profile_dir / ".cofi-debug-port").write_text("49281", encoding="utf-8")
    worker = BrowserLoginWorker()
    monkeypatch.setattr(worker, "_profile_process_debug_ports", lambda _profile: [])
    monkeypatch.setattr(worker, "_probe_cdp_port", lambda _port: "http://127.0.0.1:49281")

    assert worker._existing_profile_cdp_endpoint(profile_dir) is None


def test_startup_resumes_persisted_profile_when_session_snapshot_is_missing(tmp_path):
    db = Database(tmp_path / "media_factory.db")
    secrets = _SecretStore()
    worker = _RecordingResumeWorker()
    manager = GoogleFlowAccountManager(
        db,
        secrets,  # type: ignore[arg-type]
        profile_root=tmp_path / "profiles",
        login_worker=worker,  # type: ignore[arg-type]
    )
    account = manager.create_account()
    db.patch_resource(
        "google_flow_account",
        account["id"],
        {"status": "auth_expired", "last_error": "snapshot missing"},
    )

    manager.resume_saved_sessions()

    assert worker.resumed == [(account["id"], tmp_path / "profiles" / account["id"])]
    restored = manager.get_account(account["id"])
    assert restored is not None
    assert restored["status"] == "connecting"
    assert restored["last_error"] is None


def test_unauthenticated_about_landing_page_with_launch_button_is_not_ready():
    class FakeLocator:
        def __init__(self, count: int):
            self._count = count

        def count(self):
            return self._count

    class FakeAboutPage:
        url = "https://flow.google.com/about"

        def locator(self, selector):
            if selector in ('button:has-text("Launch")', 'button:has-text("Khởi chạy")'):
                return FakeLocator(1)
            return FakeLocator(0)

    assert BrowserLoginWorker._migrated_profile_ready(FakeAboutPage()) is False


def test_ensure_visible_window_placement_resets_offscreen_preferences(tmp_path):
    import json

    pref_dir = tmp_path / "Default"
    pref_dir.mkdir(parents=True)
    pref_file = pref_dir / "Preferences"
    pref_file.write_text(
        json.dumps(
            {
                "browser": {
                    "window_placement": {
                        "left": 9999,
                        "top": 9999,
                        "right": 11279,
                        "bottom": 10899,
                        "maximized": False,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    BrowserLoginWorker._ensure_visible_window_placement(tmp_path)
    updated = json.loads(pref_file.read_text(encoding="utf-8"))
    placement = updated["browser"]["window_placement"]
    assert placement["left"] == 120
    assert placement["top"] == 60
    assert placement["right"] == 1400
    assert placement["bottom"] == 920


def test_concurrent_forced_resume_does_not_domino_kill_fresh_session(tmp_path):
    from vendor.media_factory.backend.app.providers.google import GoogleFlowHeadlessClient

    class _CountingWorker:
        def __init__(self):
            self.live = False
            self.close_calls = 0
            self.resume_calls = 0
            self.first_entered = threading.Event()
            self.release_first = threading.Event()

        def has_live_session(self, _account_id: str) -> bool:
            return self.live

        def is_interactive(self, _account_id: str) -> bool:
            return False

        def close_session(self, _account_id: str) -> None:
            self.close_calls += 1
            self.live = False

        def resume_session(self, _account_id, _profile_dir, _on_complete, _on_error) -> None:
            self.resume_calls += 1
            if self.resume_calls == 1:
                self.first_entered.set()
                self.release_first.wait(1.0)
            self.live = True

    worker = _CountingWorker()
    db = Database(tmp_path / "media_factory.db")
    secrets = _SecretStore()
    manager = GoogleFlowAccountManager(
        db,
        secrets,  # type: ignore[arg-type]
        profile_root=tmp_path / "profiles",
        login_worker=worker,  # type: ignore[arg-type]
    )
    provider = GoogleFlowHeadlessClient(tmp_path / "out", account_manager=manager)
    account = {"id": "acc-1"}

    t1 = threading.Thread(
        target=lambda: provider._resume_saved_live_session(account, {}, force=True),
        daemon=True,
    )
    t2 = threading.Thread(
        target=lambda: provider._resume_saved_live_session(account, {}, force=True),
        daemon=True,
    )
    t1.start()
    assert worker.first_entered.wait(0.5)
    t2.start()
    time.sleep(0.05)
    worker.release_first.set()
    t1.join(timeout=2.0)
    t2.join(timeout=2.0)

    assert worker.resume_calls == 1
    assert worker.close_calls == 1
    assert worker.live is True

