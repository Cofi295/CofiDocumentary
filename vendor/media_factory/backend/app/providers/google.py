from __future__ import annotations

import asyncio
import base64
import inspect
import json
import logging
import mimetypes
import os

logger = logging.getLogger(__name__)
import queue as thread_queue
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from ..db import Database
from ..secrets import KeyringSecretStore
from ..watermark_remover import strip_gemini_watermark
from .base import (
    MediaProvider,
    ProviderAuthError,
    ProviderError,
    ProviderQuotaError,
    ProviderTransientError,
    scene_output_directory,
    scene_output_stem,
)
from .auth_bridge import get_extension_bridge, DEFAULT_SITE_KEY
from .google_flow_migrated import (
    MigratedFlowImageDriver,
    MigratedFlowVideoDriver,
    _flow_public_error_codes,
    image_records,
    parse_frames,
)


GOOGLE_FLOW_MODELS: list[dict[str, Any]] = [
    {
        'id': 'nano_banana_2_lite',
        'name': 'Nano Banana 2 Lite',
        'kind': 'image',
        'tiers': ['free', 'pro', 'ultra'],
        'capabilities': {'reference_images': True, 'max_references': 3},
    },
    {
        'id': 'nano_banana_2',
        'name': 'Nano Banana 2',
        'kind': 'image',
        'tiers': ['free', 'pro', 'ultra'],
        'capabilities': {'reference_images': True, 'max_references': 6},
    },
    {
        'id': 'nano_banana_pro',
        'name': 'Nano Banana Pro',
        'kind': 'image',
        'tiers': ['pro', 'ultra'],
        'capabilities': {'reference_images': True, 'pro_reference': True, 'max_references': 14},
    },
    {
        'id': 'veo_31_fast',
        'name': 'Veo 3.1 Fast',
        'kind': 'video',
        'tiers': ['pro', 'ultra'],
        'credit_label': '10~20 Credit',
        'minimum_credit_cost': 10,
        'capabilities': {'start_image': True, 'end_image': True, 'components': True},
    },
    {
        'id': 'veo_31_lite',
        'name': 'Veo 3.1 Lite',
        'kind': 'video',
        'tiers': ['pro', 'ultra'],
        'credit_label': '5~10 Credit',
        'minimum_credit_cost': 5,
        'capabilities': {'start_image': True, 'end_image': True},
    },
    {
        'id': 'veo_31_lite_relaxed',
        'name': 'Veo 3.1 Lite · Lower Priority',
        'kind': 'video',
        'tiers': ['pro', 'ultra'],
        'credit_cost': 0,
        'credit_label': 'ULTRA 0 Credit',
        'minimum_credit_cost': 0,
        'capabilities': {'start_image': True, 'end_image': True},
    },
    {
        'id': 'veo_31_quality',
        'name': 'Veo 3.1 Quality',
        'kind': 'video',
        'tiers': ['ultra'],
        'credit_cost': 100,
        'credit_label': '100 Credit',
        'minimum_credit_cost': 100,
        'capabilities': {'start_image': True, 'end_image': True, 'components': True, 'quality_4k': True},
    },
    {
        'id': 'omni_flash',
        'name': 'Omni Flash',
        'kind': 'video',
        'tiers': ['ultra'],
        'credit_label': '15~20 Credit',
        'minimum_credit_cost': 15,
        'capabilities': {'start_image': True, 'end_image': True, 'reference_video': True, 'multi_reference': True},
    },
]

GOOGLE_FLOW_MODEL_BY_ID = {model['id']: model for model in GOOGLE_FLOW_MODELS}
GOOGLE_FLOW_IMAGE_MAX_INFLIGHT_PER_ACCOUNT = max(1, int(os.getenv('COFI_IMAGE_MAX_INFLIGHT_PER_ACCOUNT', '10')))
# Match G-Labs' Flow worker model: up to 5 concurrent async video jobs per account.
GOOGLE_FLOW_VIDEO_MAX_INFLIGHT_PER_ACCOUNT = 5
GOOGLE_FLOW_KNOWN_TIERS = frozenset({'free', 'pro', 'ultra'})
IMAGE_MODEL_MENU_LABELS = {
    'nano_banana_2_lite': 'Nano Banana 2 Lite',
    'nano_banana_2': 'Nano Banana 2',
    'nano_banana_pro': 'Nano Banana Pro',
}
VIDEO_MODEL_MENU_LABELS = {
    'veo_31_fast': 'Veo 3.1 - Fast',
    'veo_31_lite': 'Veo 3.1 - Lite',
    'veo_31_lite_relaxed': 'Veo 3.1 - Lite [Lower Priority]',
    'veo_31_quality': 'Veo 3.1 - Quality',
    'omni_flash': 'Omni 1.1 Flash',
}
ACCOUNT_RESOURCE_TYPE = 'google_flow_account'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'
GOOGLE_FLOW_CREDITS_URL = (
    'https://aisandbox-pa.googleapis.com/v1/credits?key='
    'AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY'
)
PAYGATE_TIER_MAP = {
    'PAYGATE_TIER_NOT_PAID': 'free',
    'PAYGATE_TIER_ONE': 'pro',
    'PAYGATE_TIER_TWO': 'ultra',
    'PAYGATE_TIER_TIER1P5': 'ultra',
}

FLOW_COMPOSER_SELECTOR = '[contenteditable="true"]:visible, [role="textbox"]:visible, textarea:visible'
FLOW_HOME_URL = 'https://flow.google.com/'
FLOW_AUTH_SESSION_URL = 'https://labs.google/fx/api/auth/session'
FLOW_MIGRATED_SESSION_URL = 'https://flow.google.com/fx/api/auth/session'
FLOW_API_ROOT = 'https://aisandbox-pa.googleapis.com/v1'
MIGRATED_FLOW_READY_ANCHOR = '.settings-trigger-button'
MIGRATED_FLOW_COMPOSER = '[contenteditable="true"]'


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class LoginWorker(Protocol):
    def start_login(
        self,
        account_id: str,
        profile_dir: Path,
        on_complete: Callable[..., None],
        on_error: Callable[[str, str], None],
    ) -> None: ...


@dataclass
class _LiveSessionCommand:
    callback: Callable[[Any], Any]
    started: threading.Event = field(default_factory=threading.Event)
    done: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: BaseException | None = None


@dataclass
class _LiveBrowserSession:
    commands: thread_queue.PriorityQueue[tuple[int, int, _LiveSessionCommand | None]] = field(
        default_factory=thread_queue.PriorityQueue
    )
    stop: threading.Event = field(default_factory=threading.Event)
    mode: str = 'hidden'
    last_activity: float = field(default_factory=time.monotonic)
    profile_dir: Path | None = None


class BrowserLoginWorker:
    """Capture a Google Labs session once, then let the app reuse it without a visible browser."""

    def __init__(
        self,
        *,
        login_timeout_seconds: int = 600,
        poll_seconds: float = 2.0,
        idle_timeout_seconds: float = 0.0,
    ):
        self.login_timeout_seconds = max(30, login_timeout_seconds)
        self.poll_seconds = max(0.5, poll_seconds)
        # Auto-kill idle Chrome instances to manage RAM strictly across accounts.
        # Default to 300 seconds (5 min) of inactivity before terminating the background browser.
        default_idle = float(os.getenv('COFI_STUDIO_BROWSER_IDLE_TIMEOUT_SEC', idle_timeout_seconds if idle_timeout_seconds > 0 else 300.0))
        self.idle_timeout_seconds = max(30.0, default_idle)
        self._live_sessions: dict[str, _LiveBrowserSession] = {}
        self._starting_sessions: set[str] = set()
        self._interactive_accounts: set[str] = set()
        self._live_sessions_lock = threading.RLock()
        self._live_command_sequence = 0

    def _next_live_command_sequence(self) -> int:
        with self._live_sessions_lock:
            self._live_command_sequence += 1
            return self._live_command_sequence

    @staticmethod
    def _migrated_profile_ready(page: Any) -> bool:
        """Return True when the persistent profile is signed in on flow.google.com.

        Migrated Flow no longer exposes the legacy Labs NextAuth cookie/session route.
        A signed-in migrated profile is recognized by structural editor/home anchors,
        user avatar (SignOutOptions) on /about, or authenticated Google cookies.
        """
        try:
            url = str(getattr(page, 'url', '') or '')
            if not url.startswith('https://flow.google.com/'):
                return False
            selectors = (
                MIGRATED_FLOW_READY_ANCHOR,
                MIGRATED_FLOW_COMPOSER,
                'a[href*="/project/"]',
                'a[href*="SignOutOptions"]',
                'a[href*="accounts.google.com/SignOutOptions"]',
                'flow-prompt-box',
                '[contenteditable="true"]',
            )
            if any(page.locator(selector).count() > 0 for selector in selectors):
                return True
            return False
        except Exception:
            return False

    def has_live_session(self, account_id: str) -> bool:
        with self._live_sessions_lock:
            session = self._live_sessions.get(account_id)
            return bool(session is not None and not session.stop.is_set())

    def session_mode(self, account_id: str) -> str | None:
        with self._live_sessions_lock:
            session = self._live_sessions.get(account_id)
            if session is None or session.stop.is_set():
                return None
            return session.mode

    def is_interactive(self, account_id: str) -> bool:
        with self._live_sessions_lock:
            if account_id in self._interactive_accounts:
                return True
            session = self._live_sessions.get(account_id)
            return bool(session is not None and not session.stop.is_set() and session.mode == 'visible')

    def has_reusable_profile(self, profile_dir: Path) -> bool:
        profile_dir = Path(profile_dir)
        if (profile_dir / 'Local State').is_file():
            cookie_candidates = (
                profile_dir / 'Default' / 'Network' / 'Cookies',
                profile_dir / 'Default' / 'Cookies',
            )
            if any(path.is_file() and path.stat().st_size > 0 for path in cookie_candidates):
                return True
        return self._existing_profile_cdp_endpoint(profile_dir) is not None

    def execute_in_session(
        self,
        account_id: str,
        callback: Callable[[Any], Any],
        *,
        timeout_seconds: float = 120.0,
        priority: int = 10,
    ) -> Any:
        with self._live_sessions_lock:
            session = self._live_sessions.get(account_id)
        if session is None or session.stop.is_set():
            raise RuntimeError('Google Flow live browser session is unavailable.')

        command = _LiveSessionCommand(callback=callback)
        session.commands.put((int(priority), self._next_live_command_sequence(), command))
        queue_timeout_seconds = max(
            max(0.1, timeout_seconds),
            float(os.getenv('COFI_STUDIO_BROWSER_COMMAND_QUEUE_TIMEOUT_SEC', '300')),
        )
        queue_deadline = time.monotonic() + queue_timeout_seconds
        while not command.started.is_set() and not command.done.is_set():
            remaining = queue_deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Google Flow live browser command waited too long in the session queue.')
            command.started.wait(min(0.05, remaining))
        if command.done.is_set() and not command.started.is_set():
            if command.error is not None:
                raise command.error
            return command.result
        if not command.done.wait(max(0.1, timeout_seconds)):
            raise TimeoutError('Google Flow live browser session did not respond in time.')
        if command.error is not None:
            raise command.error
        return command.result

    def close_session(self, account_id: str) -> None:
        with self._live_sessions_lock:
            session = self._live_sessions.get(account_id)
        if session is None:
            return
        session.stop.set()
        session.commands.put((-100, self._next_live_command_sequence(), None))
        if session.profile_dir is not None:
            try:
                self._terminate_profile_processes(session.profile_dir)
            except Exception:
                pass
            try:
                _evict_profile_cache_subdirs(session.profile_dir)
            except Exception:
                pass

    def shutdown(self) -> None:
        with self._live_sessions_lock:
            account_ids = list(self._live_sessions)
        for account_id in account_ids:
            self.close_session(account_id)

    def _serve_live_session(
        self,
        account_id: str,
        context: Any,
        *,
        mode: str = 'hidden',
        profile_dir: Path | None = None,
        on_ready: Callable[[], None] | None = None,
        is_alive: Callable[[], bool] | None = None,
    ) -> None:
        session = _LiveBrowserSession(mode=mode, profile_dir=profile_dir, last_activity=time.monotonic())
        last_activity = time.monotonic()
        with self._live_sessions_lock:
            previous = self._live_sessions.get(account_id)
            if previous is not None:
                previous.stop.set()
                previous.commands.put((-100, self._next_live_command_sequence(), None))
                if previous.profile_dir is not None:
                    try:
                        self._terminate_profile_processes(previous.profile_dir)
                    except Exception:
                        pass
            self._live_sessions[account_id] = session
        try:
            if on_ready is not None:
                on_ready()
            while not session.stop.is_set() and (is_alive is None or is_alive()):
                if (
                    mode != 'visible'
                    and self.idle_timeout_seconds > 0
                    and time.monotonic() - last_activity >= self.idle_timeout_seconds
                ):
                    logger.info(
                        "Closing idle Google Flow Chrome session for account %s (idle %.1fs >= %.1fs) to free RAM.",
                        account_id,
                        time.monotonic() - last_activity,
                        self.idle_timeout_seconds,
                    )
                    session.stop.set()
                    break
                try:
                    _priority, _sequence, command = session.commands.get(timeout=0.25)
                except thread_queue.Empty:
                    continue
                if command is None:
                    continue
                last_activity = time.monotonic()
                session.last_activity = last_activity
                command.started.set()
                try:
                    self._ensure_companion_extension(context)
                    command.result = command.callback(context)
                except BaseException as exc:
                    command.error = exc
                    if self._is_closed_browser_error(exc):
                        session.stop.set()
                finally:
                    # A Flow generation can itself take longer than the idle timeout.
                    # Treat completion of that work as fresh activity; otherwise the
                    # session is closed immediately after a long successful request
                    # and the very next queued job sees an expired/missing session.
                    last_activity = time.monotonic()
                    session.last_activity = last_activity
                    command.done.set()
        finally:
            with self._live_sessions_lock:
                if self._live_sessions.get(account_id) is session:
                    self._live_sessions.pop(account_id, None)
            if profile_dir is not None:
                try:
                    self._terminate_profile_processes(profile_dir)
                except Exception:
                    pass
                try:
                    _evict_profile_cache_subdirs(profile_dir)
                except Exception:
                    pass
            while True:
                try:
                    _priority, _sequence, pending = session.commands.get_nowait()
                except thread_queue.Empty:
                    break
                if pending is not None and not pending.done.is_set():
                    pending.error = RuntimeError('Google Flow live browser session closed.')
                    pending.done.set()

    def _start_capture_thread(
        self,
        account_id: str,
        profile_dir: Path,
        on_complete: Callable[..., None],
        on_error: Callable[[str, str], None],
        *,
        interactive: bool,
        thread_name: str,
    ) -> None:
        # A forced reopen first stops the current live session.  The capture
        # thread needs a short moment to unwind and clear _starting_sessions.
        # Dropping the new resume request during that window leaves no browser
        # session at all and is later misreported as an expired Google login.
        if interactive:
            with self._live_sessions_lock:
                self._interactive_accounts.add(account_id)
            try:
                self.close_session(account_id)
            except Exception:
                pass
        wait_deadline = time.monotonic() + 5.0
        while True:
            with self._live_sessions_lock:
                if not interactive and (
                    account_id in self._interactive_accounts
                    or (
                        self._live_sessions.get(account_id) is not None
                        and not self._live_sessions[account_id].stop.is_set()
                        and self._live_sessions[account_id].mode == 'visible'
                    )
                ):
                    return
                live = self._live_sessions.get(account_id)
                if live is not None and not live.stop.is_set():
                    if interactive:
                        live.stop.set()
                    else:
                        return
                if account_id not in self._starting_sessions:
                    self._starting_sessions.add(account_id)
                    break
            if time.monotonic() >= wait_deadline:
                if interactive:
                    with self._live_sessions_lock:
                        self._interactive_accounts.discard(account_id)
                return
            time.sleep(0.05)

        def run() -> None:
            try:
                self._capture_session(account_id, profile_dir, on_complete, on_error, interactive, True)
            finally:
                with self._live_sessions_lock:
                    self._starting_sessions.discard(account_id)
                    if interactive:
                        self._interactive_accounts.discard(account_id)

        thread = threading.Thread(target=run, name=thread_name, daemon=True)
        try:
            thread.start()
        except BaseException:
            with self._live_sessions_lock:
                self._starting_sessions.discard(account_id)
                if interactive:
                    self._interactive_accounts.discard(account_id)
            raise

    def start_login(
        self,
        account_id: str,
        profile_dir: Path,
        on_complete: Callable[..., None],
        on_error: Callable[[str, str], None],
    ) -> None:
        profile_dir.mkdir(parents=True, exist_ok=True)
        self._start_capture_thread(
            account_id,
            profile_dir,
            on_complete,
            on_error,
            interactive=True,
            thread_name=f'google-flow-login-{account_id[:8]}',
        )

    def resume_session(
        self,
        account_id: str,
        profile_dir: Path,
        on_complete: Callable[..., None],
        on_error: Callable[[str, str], None],
    ) -> None:
        """Reopen an existing Chrome profile headlessly; never drive the Flow composer UI."""
        profile_dir.mkdir(parents=True, exist_ok=True)
        self._start_capture_thread(
            account_id,
            profile_dir,
            on_complete,
            on_error,
            interactive=False,
            thread_name=f'google-flow-resume-{account_id[:8]}',
        )

    @classmethod
    def _find_extension_dir(cls, extension_dir: Path | None = None) -> Path | None:
        candidates: list[Path] = []
        if extension_dir:
            candidates.append(Path(extension_dir).resolve())
        candidates.extend([
            Path(__file__).resolve().parents[3] / 'extension',
            Path(__file__).resolve().parents[5] / 'extension',
            Path(r"b:\ALL_TOOLS\CofiDocumentary\extension").resolve(),
            Path(r"b:\ALL_TOOLS\CofiDocumentary\vendor\media_factory\extension").resolve(),
            Path(r"b:\ALL_TOOLS\CofiDocumentary\glabs_ext_source").resolve(),
        ])
        for cand in candidates:
            if (cand / 'manifest.json').is_file():
                return cand
        return None

    @classmethod
    def _extension_launch_args(cls, extension_dir: Path | None = None) -> list[str]:
        cand = cls._find_extension_dir(extension_dir)
        if cand:
            return [
                f'--disable-extensions-except={cand}',
                f'--load-extension={cand}',
            ]
        return ['--disable-extensions']

    @classmethod
    def _register_extension_in_windows_registry(cls, extension_dir: Path | None = None) -> None:
        if os.name != 'nt':
            return
        key_path = r"Software\Google\Chrome\Extensions\clhcjdjbcldkogahjfmcgfipmlilmkpg"
        if os.getenv('COFI_REGISTER_SYSTEM_CHROME_EXT', '0') != '1':
            try:
                import winreg
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            except Exception:
                pass
            return
        cand = cls._find_extension_dir(extension_dir)
        if not cand:
            return
        try:
            import winreg
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "path", 0, winreg.REG_SZ, str(cand))
                winreg.SetValueEx(key, "version", 0, winreg.REG_SZ, "9.0.18")
        except Exception as exc:
            logger.debug("Registry extension register note: %s", exc)

    _ensured_extension_browsers: set[int] = set()

    @classmethod
    def _ensure_companion_extension(cls, browser_or_context: Any, extension_dir: Path | None = None) -> None:
        cand = cls._find_extension_dir(extension_dir)
        if not cand:
            return
        try:
            b = getattr(browser_or_context, 'browser', browser_or_context)
            b_id = id(b)
            if b_id in cls._ensured_extension_browsers:
                return
            cls._register_extension_in_windows_registry(cand)
            if hasattr(b, 'new_browser_cdp_session'):
                browser_cdp = b.new_browser_cdp_session()
                res = browser_cdp.send("Extensions.loadUnpacked", {"path": str(cand)})
                logger.info("Auto-installed companion extension via CDP: %s -> %s", cand, res)
            cls._ensured_extension_browsers.add(b_id)
        except Exception as exc:
            logger.debug("Extensions.loadUnpacked over CDP note: %s", exc)

    @staticmethod
    def _hidden_worker_launch_args() -> list[str]:
        """Launch ordinary Chrome off-screen matching G-Labs background worker flags.

        Flow's Enterprise reCAPTCHA assigns headless Chrome a materially different
        risk profile. Running a normal Chrome with window-position=9999,9999 and
        disabled backgrounding throttling keeps extension timers and DOM active
        without disturbing desktop user interaction.
        """
        return [
            '--disable-blink-features=AutomationControlled',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-dev-shm-usage',
            '--use-mock-keychain',
            '--mute-audio',
            '--remote-allow-origins=*',
            '--new-window',
            '--window-position=9999,9999',
            '--window-size=1280,900',
            FLOW_HOME_URL,
        ]

    @staticmethod
    def _find_chrome() -> Path:
        configured = os.environ.get('COFI_STUDIO_CHROME')
        candidates: list[Path] = []
        if configured:
            candidates.append(Path(configured).expanduser())

        resolved = shutil.which('chrome.exe') or shutil.which('chrome')
        if resolved:
            candidates.append(Path(resolved))

        for env_name in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
            root = os.environ.get(env_name)
            if root:
                candidates.append(Path(root) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe')

        for candidate in candidates:
            if candidate.is_file():
                return candidate
        raise RuntimeError('Google Chrome was not found. Install Chrome or set COFI_STUDIO_CHROME.')

    @staticmethod
    def _is_closed_browser_error(exc: BaseException) -> bool:
        text = str(exc).lower()
        return any(
            marker in text
            for marker in (
                'target page, context or browser has been closed',
                'context or browser has been closed',
                'browser has been closed',
                'browsercontext.new_page: target page',
                'target closed',
                'connection closed',
            )
        )

    @classmethod
    def _profile_process_ids(cls, profile_dir: Path) -> list[int]:
        """Return Windows Chrome processes whose command line owns this profile."""
        if os.name != 'nt':
            return []
        profile = str(Path(profile_dir).resolve()).replace("'", "''")
        script = (
            "$p='" + profile + "'; "
            "Get-CimInstance Win32_Process -Filter \"name = 'chrome.exe'\" | "
            "Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf($p, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 } | "
            "ForEach-Object { $_.ProcessId }"
        )
        try:
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                **_hidden_subprocess_kwargs(),
            )
        except Exception:
            return []
        pids: list[int] = []
        for line in str(getattr(result, 'stdout', '')).splitlines():
            try:
                pid = int(line.strip())
            except ValueError:
                continue
            if pid > 0 and pid != os.getpid():
                pids.append(pid)
        return sorted(set(pids))

    @classmethod
    def _terminate_profile_processes(cls, profile_dir: Path) -> None:
        if os.name != 'nt':
            return
        for pid in cls._profile_process_ids(profile_dir):
            try:
                subprocess.run(
                    ['taskkill', '/PID', str(pid), '/T', '/F'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                    check=False,
                    **_hidden_subprocess_kwargs(),
                )
            except Exception:
                continue

    @classmethod
    def _hide_profile_windows(cls, profile_dir: Path) -> None:
        """Best-effort hide of visible windows belonging to this dedicated Chrome profile."""
        if os.name != 'nt':
            return
        pids = set(cls._profile_process_ids(profile_dir))
        if not pids:
            return
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

            @enum_proc_type
            def hide_window(hwnd, _lparam):
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value in pids and user32.IsWindowVisible(hwnd):
                    user32.ShowWindow(hwnd, 0)
                return True

            user32.EnumWindows(hide_window, 0)
        except Exception:
            return

    @classmethod
    def _ensure_visible_window_placement(cls, profile_dir: Path) -> None:
        """Reset saved Chrome window_placement in Default/Preferences so interactive login/verify
        always opens centered on the primary screen instead of at (9999, 9999) or off-screen."""
        placement = {
            'bottom': 920,
            'left': 120,
            'maximized': False,
            'right': 1400,
            'top': 60,
            'work_area_bottom': 1032,
            'work_area_left': 0,
            'work_area_right': 1920,
            'work_area_top': 0,
        }
        for sub in ('Default', 'Profile 1'):
            pref_dir = Path(profile_dir) / sub
            pref_path = pref_dir / 'Preferences'
            if not pref_path.is_file() and sub != 'Default':
                continue
            try:
                pref_dir.mkdir(parents=True, exist_ok=True)
                data: dict[str, Any] = {}
                if pref_path.is_file():
                    loaded = json.loads(pref_path.read_text(encoding='utf-8', errors='ignore'))
                    if isinstance(loaded, dict):
                        data = loaded
                browser_sec = data.setdefault('browser', {})
                if isinstance(browser_sec, dict):
                    browser_sec['window_placement'] = dict(placement)
                    browser_sec['app_window_placement'] = dict(placement)
                profile_sec = data.setdefault('profile', {})
                if isinstance(profile_sec, dict):
                    profile_sec['exit_type'] = 'Normal'
                    profile_sec['exited_cleanly'] = True
                pref_path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            except Exception:
                continue

    @classmethod
    def _bring_profile_windows_to_front(cls, profile_dir: Path, *, only_if_offscreen: bool = False) -> None:
        """Force all top-level Chrome windows for this profile onto the primary screen (120, 60, 1280x860)
        and bring them to the foreground so the user can immediately interact and log in."""
        if os.name != 'nt':
            return
        pids = set(cls._profile_process_ids(profile_dir))
        if not pids:
            return
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            SW_RESTORE = 9
            SWP_SHOWWINDOW = 0x0040

            @enum_proc_type
            def restore_and_center(hwnd, _lparam):
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value in pids:
                    cls_buf = ctypes.create_unicode_buffer(128)
                    user32.GetClassNameW(hwnd, cls_buf, 128)
                    title_buf = ctypes.create_unicode_buffer(256)
                    user32.GetWindowTextW(hwnd, title_buf, 256)
                    if cls_buf.value == 'Chrome_WidgetWin_1' and title_buf.value:
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        is_offscreen = (
                            rect.left < -50
                            or rect.top < -20
                            or rect.left > 1400
                            or rect.top > 600
                            or w < 500
                            or h < 400
                        )
                        if not only_if_offscreen or is_offscreen:
                            user32.ShowWindow(hwnd, SW_RESTORE)
                            user32.MoveWindow(hwnd, 120, 60, 1280, 860, True)
                            user32.SetWindowPos(hwnd, 0, 120, 60, 1280, 860, SWP_SHOWWINDOW)
                            if not only_if_offscreen:
                                user32.SetForegroundWindow(hwnd)
                return True

            user32.EnumWindows(restore_and_center, 0)
        except Exception:
            return

    @staticmethod
    def _reserve_debug_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(('127.0.0.1', 0))
            return int(probe.getsockname()[1])

    @staticmethod
    def _probe_cdp_port(port: int, *, timeout_seconds: float = 0.5) -> str | None:
        endpoint = f'http://127.0.0.1:{int(port)}/json/version'
        try:
            with urllib.request.urlopen(endpoint, timeout=max(0.05, float(timeout_seconds))) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            return None
        if payload.get('webSocketDebuggerUrl'):
            return f'http://127.0.0.1:{int(port)}'
        return None

    @classmethod
    def _profile_process_debug_ports(cls, profile_dir: Path) -> list[int]:
        if os.name != 'nt':
            return []
        profile = str(Path(profile_dir).resolve()).replace("'", "''")
        script = (
            "$p='" + profile + "'; "
            "Get-CimInstance Win32_Process -Filter \"name = 'chrome.exe'\" | "
            "Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf($p, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 } | "
            "ForEach-Object { $_.CommandLine }"
        )
        try:
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                **_hidden_subprocess_kwargs(),
            )
        except Exception:
            return []
        ports: list[int] = []
        for match in re.finditer(r'--remote-debugging-port(?:=|\s+)(\d+)', str(getattr(result, 'stdout', ''))):
            try:
                port = int(match.group(1))
            except (TypeError, ValueError):
                continue
            if 0 < port <= 65535:
                ports.append(port)
        return sorted(set(ports))

    @classmethod
    def _existing_profile_cdp_endpoint(cls, profile_dir: Path) -> str | None:
        marker = Path(profile_dir) / '.cofi-debug-port'
        saved_port = None
        try:
            val = int(marker.read_text(encoding='utf-8').strip())
            if 0 < val <= 65535:
                saved_port = val
        except (OSError, ValueError):
            pass

        owned_ports = set(cls._profile_process_debug_ports(profile_dir))
        if saved_port is not None:
            if saved_port in owned_ports:
                endpoint = cls._probe_cdp_port(saved_port)
                if endpoint:
                    return endpoint
            try:
                marker.unlink()
            except OSError:
                pass
            return None

        for port in sorted(owned_ports):
            endpoint = cls._probe_cdp_port(port)
            if endpoint:
                return endpoint
        return None

    @staticmethod
    def _wait_for_cdp(port: int, process: subprocess.Popen[Any], timeout_seconds: float = 15.0) -> str:
        endpoint = f'http://127.0.0.1:{port}/json/version'
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            return_code = process.poll()
            if return_code not in (None, 0):
                raise RuntimeError(f'Chrome exited before login was ready (code {process.returncode}).')
            try:
                with urllib.request.urlopen(endpoint, timeout=0.5) as response:
                    payload = json.loads(response.read().decode('utf-8'))
                    if payload.get('webSocketDebuggerUrl'):
                        return f'http://127.0.0.1:{port}'
            except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                pass
            time.sleep(0.15)
        raise RuntimeError('Chrome did not expose its local debugging endpoint in time.')

    def _capture_session(
        self,
        account_id: str,
        profile_dir: Path,
        on_complete: Callable[..., None],
        on_error: Callable[[str, str], None],
        interactive: bool = True,
        keep_live: bool = False,
    ) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            on_error(account_id, 'Playwright is not installed. Install backend dependencies, then try login again.')
            return

        chrome_process: subprocess.Popen[Any] | None = None
        browser = None
        owns_profile_processes = False
        try:
            chrome_path = self._find_chrome()
            if interactive:
                self._terminate_profile_processes(profile_dir)
                try:
                    (Path(profile_dir) / '.cofi-debug-port').unlink(missing_ok=True)
                except OSError:
                    pass
                time.sleep(0.25)
                self._ensure_visible_window_placement(profile_dir)
            cdp_endpoint = None if interactive else self._existing_profile_cdp_endpoint(profile_dir)
            reused_profile_endpoint = cdp_endpoint is not None
            if cdp_endpoint is None:
                debug_port = self._reserve_debug_port()
                chrome_args = [
                    str(chrome_path),
                    f'--remote-debugging-port={debug_port}',
                    f'--user-data-dir={profile_dir}',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=Translate,TranslateUI',
                    '--enable-unsafe-extension-debugging',
                    '--hide-crash-restore-bubble',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-sync',
                    *self._extension_launch_args(),
                ]
                if interactive:
                    self._ensure_visible_window_placement(profile_dir)
                    chrome_args.extend([
                        '--new-window',
                        '--window-position=120,60',
                        '--window-size=1280,860',
                        FLOW_HOME_URL,
                    ])
                else:
                    chrome_args.extend(self._hidden_worker_launch_args())
                startupinfo = None
                creationflags = 0
                if not interactive and os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1)
                    startupinfo.wShowWindow = getattr(subprocess, 'SW_HIDE', 0)
                    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)

                chrome_process = subprocess.Popen(
                    chrome_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    startupinfo=startupinfo,
                    creationflags=creationflags,
                )
                owns_profile_processes = True
                try:
                    (profile_dir / '.cofi-debug-port').write_text(str(debug_port), encoding='utf-8')
                except OSError:
                    pass
                cdp_endpoint = self._wait_for_cdp(debug_port, chrome_process)
                if interactive:
                    self._bring_profile_windows_to_front(profile_dir)
                else:
                    self._hide_profile_windows(profile_dir)
            elif not interactive:
                self._hide_profile_windows(profile_dir)

            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(cdp_endpoint)
                self._ensure_companion_extension(browser)
                if interactive:
                    try:
                        cdp_sess = browser.new_browser_cdp_session()
                        targets = cdp_sess.send('Target.getTargets').get('targetInfos', [])
                        for t_info in targets:
                            if t_info.get('type') == 'page':
                                win_info = cdp_sess.send('Browser.getWindowForTarget', {'targetId': t_info['targetId']})
                                win_id = win_info.get('windowId')
                                if win_id is not None:
                                    cdp_sess.send('Browser.setWindowBounds', {
                                        'windowId': win_id,
                                        'bounds': {'windowState': 'normal'},
                                    })
                                    cdp_sess.send('Browser.setWindowBounds', {
                                        'windowId': win_id,
                                        'bounds': {'left': 120, 'top': 60, 'width': 1280, 'height': 860, 'windowState': 'normal'},
                                    })
                                    break
                    except Exception:
                        pass
                    self._bring_profile_windows_to_front(profile_dir)
                context = browser.contexts[0] if browser.contexts else None
                if context is None:
                    raise RuntimeError('Chrome opened, but its persistent profile context was unavailable.')
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    try:
                        if not page.url.startswith('https://flow.google.com/'):
                            page.goto(FLOW_HOME_URL, wait_until='domcontentloaded', timeout=120_000)
                    except Exception:
                        pass
                    deadline = time.monotonic() + (self.login_timeout_seconds if interactive else 20.0)
                    invalid_session_reloaded = False
                    browser_closed_early = False
                    while time.monotonic() < deadline:
                        if chrome_process is not None and chrome_process.poll() is not None:
                            browser_closed_early = True
                            break

                        if interactive:
                            self._bring_profile_windows_to_front(profile_dir, only_if_offscreen=True)
                        try:
                            pages = [p for p in context.pages if not getattr(p, 'is_closed', lambda: False)()]
                            page = pages[0] if pages else context.new_page()
                        except Exception as page_exc:
                            if self._is_closed_browser_error(page_exc):
                                if chrome_process is not None and chrome_process.poll() is not None:
                                    browser_closed_early = True
                                    break
                                time.sleep(self.poll_seconds)
                                continue
                            page = None

                        if not interactive and page is not None:
                            curr_u = (getattr(page, 'url', '') or '').lower()
                            if 'accounts.google.com' in curr_u:
                                on_error(account_id, 'Google Flow session expired; requires interactive login.')
                                return

                        cookies = []
                        try:
                            cookies = context.cookies()
                        except Exception as cookie_exc:
                            if self._is_closed_browser_error(cookie_exc):
                                if chrome_process is not None and chrome_process.poll() is not None:
                                    browser_closed_early = True
                                    break
                                time.sleep(self.poll_seconds)
                                continue
                            time.sleep(self.poll_seconds)
                            continue

                        if page is not None and self._migrated_profile_ready(page):
                            migrated_payload: dict[str, Any] = {}
                            for sess_url in (FLOW_MIGRATED_SESSION_URL, FLOW_AUTH_SESSION_URL):
                                try:
                                    resp = context.request.get(sess_url, timeout=15_000)
                                    if getattr(resp, 'ok', False):
                                        cand_json = resp.json()
                                        if isinstance(cand_json, dict) and self._extract_access_token(cand_json):
                                            migrated_payload = cand_json
                                            break
                                except Exception:
                                    continue
                            if not self._extract_access_token(migrated_payload) and hasattr(page, 'evaluate'):
                                try:
                                    eval_payload = page.evaluate(
                                        "async () => { try { const r = await fetch('/fx/api/auth/session'); return await r.json(); } catch (e) { return {}; } }"
                                    )
                                    if isinstance(eval_payload, dict) and eval_payload:
                                        migrated_payload = eval_payload
                                except Exception:
                                    pass
                            mig_token = self._extract_access_token(migrated_payload)
                            mig_userinfo = self._fetch_userinfo(context, mig_token) if mig_token else None
                            mig_email = self._find_email(mig_userinfo) or self._find_email(migrated_payload) or ''
                            mig_tier, mig_credits = (
                                self._fetch_tier_and_credits(context, mig_token)
                                if mig_token
                                else ('unknown', None)
                            )
                            mig_cookie = next(
                                (cookie for cookie in cookies if cookie.get('name') == '__Secure-next-auth.session-token'),
                                None,
                            )
                            mig_expires = self._cookie_expiry(mig_cookie) if isinstance(mig_cookie, dict) else None
                            session_secret = {
                                'cookies': cookies,
                                'captured_at': _utc_now(),
                                'migrated_host': True,
                            }
                            if migrated_payload:
                                session_secret['session'] = migrated_payload
                            on_complete(
                                account_id,
                                email=mig_email,
                                tier=mig_tier,
                                credits=mig_credits,
                                session_secret=session_secret,
                                session_expires_at=mig_expires,
                            )
                            if keep_live or reused_profile_endpoint:
                                self._serve_live_session(
                                    account_id,
                                    context,
                                    mode='visible' if interactive else 'hidden',
                                    profile_dir=profile_dir,
                                    is_alive=(
                                        (lambda: chrome_process is not None and chrome_process.poll() is None)
                                        if chrome_process is not None
                                        else None
                                    ),
                                )
                            return

                        token_cookie = next(
                            (cookie for cookie in cookies if cookie.get('name') == '__Secure-next-auth.session-token'),
                            None,
                        )
                        if token_cookie:
                            session_payload: dict[str, Any] = {}
                            for sess_url in (FLOW_AUTH_SESSION_URL, FLOW_MIGRATED_SESSION_URL):
                                try:
                                    response = context.request.get(
                                        sess_url,
                                        timeout=30_000,
                                    )
                                    if response.ok:
                                        cand_payload = response.json()
                                        if isinstance(cand_payload, dict) and cand_payload:
                                            session_payload = cand_payload
                                            if self._extract_access_token(session_payload):
                                                break
                                except Exception:
                                    continue

                            session_refresh_needed = (
                                str(session_payload.get('error') or '').strip().upper()
                                == 'ACCESS_TOKEN_REFRESH_NEEDED'
                            )
                            if session_refresh_needed:
                                if not invalid_session_reloaded and page is not None:
                                    invalid_session_reloaded = True
                                    try:
                                        page.goto(
                                            'https://labs.google/fx/',
                                            wait_until='domcontentloaded',
                                            timeout=120_000,
                                        )
                                    except Exception:
                                        pass
                                time.sleep(self.poll_seconds)
                                continue

                            access_token = self._extract_access_token(session_payload)
                            userinfo = self._fetch_userinfo(context, access_token) if access_token else None
                            email = self._find_email(userinfo) or self._find_email(session_payload)
                            if access_token and email:
                                tier, credits = self._fetch_tier_and_credits(context, access_token)
                                expires_at = self._cookie_expiry(token_cookie)
                                session_secret = {
                                    'cookies': cookies,
                                    'session': session_payload,
                                    'captured_at': _utc_now(),
                                }
                                on_complete(
                                    account_id,
                                    email=email,
                                    tier=tier,
                                    credits=credits,
                                    session_secret=session_secret,
                                    session_expires_at=expires_at,
                                )
                                if not (keep_live or reused_profile_endpoint):
                                    return
                                self._serve_live_session(
                                    account_id,
                                    context,
                                    mode='visible' if interactive else 'hidden',
                                    profile_dir=profile_dir,
                                    is_alive=(
                                        (lambda: chrome_process is not None and chrome_process.poll() is None)
                                        if chrome_process is not None
                                        else None
                                    ),
                                )
                                return

                            if not invalid_session_reloaded and interactive and page is not None:
                                invalid_session_reloaded = True
                                try:
                                    page.goto(
                                        FLOW_HOME_URL,
                                        wait_until='domcontentloaded',
                                        timeout=120_000,
                                    )
                                except Exception:
                                    pass

                        time.sleep(self.poll_seconds)
                    if browser_closed_early or (chrome_process is not None and chrome_process.poll() is not None):
                        on_error(
                            account_id,
                            'Cửa sổ đăng nhập Google đã bị đóng trước khi hoàn tất.'
                            if interactive
                            else 'Trình duyệt nền Google đã đóng trước khi hoàn tất khôi phục phiên.',
                        )
                    elif interactive:
                        on_error(account_id, 'Google login timed out before a Flow session was detected.')
                    else:
                        on_error(account_id, 'Saved Google Flow session could not be resumed; renew this account once.')
                finally:
                    if browser is not None:
                        browser.close()
        except Exception as exc:
            if self._is_closed_browser_error(exc):
                on_error(
                    account_id,
                    'Cửa sổ đăng nhập Google đã bị đóng trước khi hoàn tất.'
                    if interactive
                    else 'Trình duyệt nền Google đã đóng trước khi hoàn tất khôi phục phiên.',
                )
            else:
                on_error(account_id, f'Google login failed: {exc}')
        finally:
            if chrome_process is not None and chrome_process.poll() is None:
                try:
                    chrome_process.terminate()
                except Exception:
                    pass
            self._terminate_profile_processes(profile_dir)
    @staticmethod
    def _find_email(payload: Any) -> str | None:
        if isinstance(payload, dict):
            for key, value in payload.items():
                if key.lower() == 'email' and isinstance(value, str) and '@' in value:
                    return value
                found = BrowserLoginWorker._find_email(value)
                if found:
                    return found
        elif isinstance(payload, list):
            for value in payload:
                found = BrowserLoginWorker._find_email(value)
                if found:
                    return found
        return None

    @staticmethod
    def _find_tier(payload: Any) -> str:
        text = json.dumps(payload, ensure_ascii=False).lower()
        if 'ultra' in text:
            return 'ultra'
        if 'pro' in text:
            return 'pro'
        if 'free' in text:
            return 'free'
        return 'unknown'

    @staticmethod
    def _extract_access_token(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get('access_token') or payload.get('accessToken')
        return value if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _map_tier_code(value: Any) -> str:
        if not isinstance(value, str):
            return 'unknown'
        return PAYGATE_TIER_MAP.get(value.strip().upper(), 'unknown')

    @staticmethod
    def _fetch_userinfo(context: Any, access_token: str) -> dict[str, Any] | None:
        try:
            response = context.request.get(
                GOOGLE_USERINFO_URL,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=30_000,
            )
            if not response.ok:
                return None
            payload = response.json()
            return payload if isinstance(payload, dict) else None
        except Exception:
            return None

    @classmethod
    def _fetch_tier_and_credits(cls, context: Any, access_token: str) -> tuple[str, int | None]:
        try:
            response = context.request.get(
                GOOGLE_FLOW_CREDITS_URL,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Origin': 'https://labs.google',
                    'Referer': 'https://labs.google/',
                },
                timeout=30_000,
            )
            if not response.ok:
                return 'unknown', None
            payload = response.json()
            if not isinstance(payload, dict):
                return 'unknown', None
            tier = cls._map_tier_code(payload.get('userPaygateTier'))
            credits_raw = payload.get('subscriptionCredits')
            credits = int(credits_raw) if isinstance(credits_raw, (int, float)) else None
            return tier, credits
        except Exception:
            return 'unknown', None

    @staticmethod
    def _cookie_expiry(cookie: dict[str, Any]) -> str | None:
        raw = cookie.get('expires')
        if not isinstance(raw, (int, float)) or raw <= 0:
            return None
        return datetime.fromtimestamp(raw, tz=UTC).isoformat()


def _handle_remove_readonly(func, path, exc_info=None):
    import stat
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _rmtree_robust(target: Path | str, retries: int = 5, delay: float = 0.15) -> bool:
    target_path = Path(target)
    if not target_path.exists():
        return True
    import stat
    for i in range(retries):
        try:
            if target_path.is_file() or target_path.is_symlink():
                try:
                    os.chmod(str(target_path), stat.S_IWRITE)
                except OSError:
                    pass
                target_path.unlink(missing_ok=True)
                return True
            for root, dirs, files in os.walk(str(target_path)):
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), stat.S_IWRITE)
                    except OSError:
                        pass
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), stat.S_IWRITE)
                    except OSError:
                        pass
            try:
                os.chmod(str(target_path), stat.S_IWRITE)
            except OSError:
                pass

            try:
                shutil.rmtree(target_path, onexc=_handle_remove_readonly)
            except TypeError:
                shutil.rmtree(target_path, onerror=_handle_remove_readonly)

            if not target_path.exists():
                return True
        except Exception:
            pass
        if i < retries - 1:
            time.sleep(delay * (i + 1))
    return not target_path.exists()


def _calc_dir_size_bytes(target: Path | str) -> int:
    total = 0
    target_str = str(target)
    if not os.path.exists(target_str):
        return 0
    if os.path.isfile(target_str) or os.path.islink(target_str):
        try:
            return os.path.getsize(target_str)
        except OSError:
            return 0
    try:
        for root, _, files in os.walk(target_str):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _evict_profile_cache_subdirs(profile_dir: Path | str) -> int:
    """Evict non-essential Chromium caches while strictly preserving session authentication files."""
    p_dir = Path(profile_dir)
    if not p_dir.is_dir():
        return 0

    freed = 0
    cache_subdirs = [
        "Default/Cache",
        "Default/Code Cache",
        "Default/GPUCache",
        "Default/DawnCache",
        "Default/DawnWebGPUCache",
        "Default/GrShaderCache",
        "Default/ShaderCache",
        "Default/Service Worker/CacheStorage",
        "Default/Service Worker/ScriptCache",
        "ShaderCache",
        "GrShaderCache",
        "GraphiteDawnCache",
        "GPUPersistentCache",
        "Crashpad",
        "BrowserMetrics",
        "component_crx_cache",
        "extensions_crx_cache",
        "optimization_guide_model_store",
        "OnDeviceHeadSuggestModel",
        "WasmTtsEngine",
    ]
    protected_lower = {
        "cookies", "network/cookies", "local storage", "session storage",
        "indexeddb", "preferences", "local state"
    }

    for sub in cache_subdirs:
        sub_norm = sub.lower().replace('\\', '/')
        if any(prot in sub_norm for prot in protected_lower):
            continue
        target_sub = p_dir / sub
        if target_sub.is_dir() or target_sub.is_file():
            sub_size = _calc_dir_size_bytes(target_sub)
            if _rmtree_robust(target_sub):
                freed += sub_size
    return freed


class GoogleFlowAccountManager:
    def __init__(
        self,
        db: Database,
        secret_store: KeyringSecretStore,
        *,
        profile_root: str | Path,
        login_worker: LoginWorker | None = None,
    ):
        self.db = db
        self.secret_store = secret_store
        self.profile_root = Path(profile_root)
        self.profile_root.mkdir(parents=True, exist_ok=True)
        self.login_worker = login_worker or BrowserLoginWorker()
        self._rotation_index: dict[str, int] = {}
        self._lease_seq: int = 0
        self._account_last_lease_seq: dict[str, int] = {}
        self._active_jobs: dict[str, int] = {}
        self._cooldown_until: dict[tuple[str, str], float] = {}
        self._closing_accounts: set[str] = set()
        self._lease_condition = threading.Condition()
        self.max_active_sessions = max(1, int(os.getenv('COFI_MAX_ACTIVE_CHROME_SESSIONS', '8')))
        try:
            get_extension_bridge().start()
        except Exception:
            pass
        self._start_ram_watchdog()

    def enforce_memory_budget(self, target_spare: int = 1) -> None:
        """Enforce strict RAM limits: ensure active Chrome count + target_spare <= max_active_sessions.
        If budget exceeded, close and kill least-recently-used idle sessions.
        """
        live_sessions = getattr(self.login_worker, '_live_sessions', {})
        lock = getattr(self.login_worker, '_live_sessions_lock', None)
        if not lock:
            return
        with lock:
            current_active = list(live_sessions.items())

        needed_free = len(current_active) + target_spare - self.max_active_sessions
        if needed_free <= 0:
            return

        candidates = []
        for acc_id, session in current_active:
            if getattr(session, 'mode', '') == 'visible':
                continue
            if self._active_jobs.get(acc_id, 0) == 0:
                last_act = getattr(session, 'last_activity', 0.0)
                candidates.append((last_act, acc_id))
        candidates.sort(key=lambda x: x[0])

        for _, acc_id in candidates[:needed_free]:
            logger.info(
                "RAM management: Preemptively killing idle Chrome for account %s to stay within budget of %s concurrent sessions.",
                acc_id,
                self.max_active_sessions,
            )
            close_session = getattr(self.login_worker, 'close_session', None)
            if callable(close_session):
                close_session(acc_id)

    def cleanup_idle_sessions(self, max_idle_seconds: float | None = None) -> int:
        """Close idle Chrome instances whose inactivity exceeds max_idle_seconds while strictly respecting RAM budget."""
        idle_timeout = max_idle_seconds if max_idle_seconds is not None else getattr(self.login_worker, 'idle_timeout_seconds', 300.0)
        now = time.monotonic()
        killed = 0
        live_sessions = getattr(self.login_worker, '_live_sessions', {})
        lock = getattr(self.login_worker, '_live_sessions_lock', None)
        if not lock:
            return 0
        with lock:
            current = list(live_sessions.items())
            starting_ids = set(getattr(self.login_worker, '_starting_sessions', set())) | set(
                getattr(self.login_worker, '_interactive_accounts', set())
            )

        active_profile_paths: set[str] = set()
        for acc_id, session in current:
            p_dir = getattr(session, 'profile_dir', None)
            if p_dir:
                active_profile_paths.add(str(Path(p_dir).resolve()).lower().replace('/', '\\'))
            if getattr(session, 'mode', '') == 'visible':
                continue
            # Never close an account that is actively executing a generation job
            if self._active_jobs.get(acc_id, 0) == 0:
                last_act = getattr(session, 'last_activity', 0.0)
                if now - last_act >= idle_timeout:
                    logger.info(
                        "RAM management: Closing idle Chrome session for account %s (idle %.1fs >= %.1fs) to free RAM.",
                        acc_id,
                        now - last_act,
                        idle_timeout,
                    )
                    close_session = getattr(self.login_worker, 'close_session', None)
                    if callable(close_session):
                        close_session(acc_id)
                        killed += 1

        for starting_id in starting_ids:
            try:
                acc = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, starting_id)
                if acc:
                    active_profile_paths.add(str(self.profile_dir_for_account(acc).resolve()).lower().replace('/', '\\'))
            except Exception:
                pass

        # Protect any account that currently has in-flight generation jobs
        for busy_acc_id, count in list(self._active_jobs.items()):
            if count > 0:
                try:
                    busy_acc = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, busy_acc_id)
                    if busy_acc:
                        active_profile_paths.add(str(self.profile_dir_for_account(busy_acc).resolve()).lower().replace('/', '\\'))
                except Exception:
                    pass

        # Also reap any orphaned automation Chrome processes running without a live managed session
        if os.name == 'nt' and active_profile_paths:
            try:
                script = (
                    "Get-CimInstance Win32_Process -Filter \"name = 'chrome.exe'\" | "
                    "Where-Object { $_.CommandLine -and ( "
                    "$_.CommandLine.IndexOf('browser_profiles', [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or "
                    "$_.CommandLine.IndexOf('google-flow-profiles', [System.StringComparison]::OrdinalIgnoreCase) -ge 0 "
                    ") } | ForEach-Object { [PSCustomObject]@{ ProcessId = $_.ProcessId; Cmd = $_.CommandLine } } | ConvertTo-Json"
                )
                res = subprocess.run(
                    ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                    **_hidden_subprocess_kwargs(),
                )
                stdout = res.stdout.strip()
                if stdout:
                    items = json.loads(stdout)
                    if isinstance(items, dict):
                        items = [items]
                    if isinstance(items, list):
                        for it in items:
                            pid = it.get('ProcessId')
                            cmd = str(it.get('Cmd') or '').lower().replace('/', '\\')
                            # If this process belongs to ANY active, starting, or busy profile, DO NOT kill it
                            is_protected = any(p in cmd for p in active_profile_paths)
                            if pid and not is_protected:
                                try:
                                    subprocess.run(
                                        ['taskkill', '/PID', str(pid), '/T', '/F'],
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL,
                                        timeout=5,
                                        check=False,
                                        **_hidden_subprocess_kwargs(),
                                    )
                                    killed += 1
                                except Exception:
                                    pass
            except Exception:
                pass

        return killed

    def _start_ram_watchdog(self) -> None:
        def _watchdog_loop():
            while True:
                try:
                    time.sleep(30.0)
                    self.cleanup_idle_sessions(max_idle_seconds=300.0)
                    self.enforce_memory_budget(target_spare=0)
                except Exception:
                    pass

        t = threading.Thread(target=_watchdog_loop, name="cofi-chrome-ram-watchdog", daemon=True)
        t.start()

    def create_account(self) -> dict[str, Any]:
        return self.db.create_resource(
            ACCOUNT_RESOURCE_TYPE,
            {
                'email': None,
                'tier': 'unknown',
                'status': 'login_required',
                'enabled': True,
                'image_enabled': True,
                'video_enabled': True,
                'image_auto_disabled': False,
                'video_auto_disabled': False,
                'image_quota_state': 'unknown',
                'video_quota_state': 'unknown',
                'session_expires_at': None,
                'quota_state': 'unknown',
                'credits': None,
                'last_error': None,
                'unavailable_models': [],
                'project_id': None,
                'project_used': 0,
            },
        )

    def profile_dir_for_account(self, account: dict[str, Any] | str) -> Path:
        """Resolve the browser profile directory for an account, supporting G-Labs profiles."""
        if isinstance(account, str):
            account_data = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account) or {}
            custom_dir = account_data.get('profile_dir')
            account_id = account
        else:
            custom_dir = account.get('profile_dir')
            account_id = account.get('id', '')
        if custom_dir:
            return Path(custom_dir)
        return self.profile_root / str(account_id)

    def start_login(self, account_id: str | None = None) -> dict[str, Any]:
        account = self.get_account(account_id) if account_id else self.create_account()
        if account is None:
            raise KeyError(account_id)
        patched = self.db.patch_resource(
            ACCOUNT_RESOURCE_TYPE,
            account['id'],
            {'status': 'connecting', 'last_error': None},
        )
        assert patched is not None
        profile_dir = self.profile_dir_for_account(account)
        self.login_worker.start_login(account['id'], profile_dir, self.complete_login, self.fail_login)
        return self._sanitize(patched)

    def complete_login(
        self,
        account_id: str,
        *,
        email: str,
        tier: str,
        session_secret: dict[str, Any],
        credits: int | None = None,
        session_expires_at: str | None = None,
    ) -> dict[str, Any]:
        current = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
        if current is None:
            raise KeyError(account_id)
        resolved_email = str(email or '').strip() or str(current.get('email') or '').strip()
        incoming_tier = str(tier or '').strip().lower()
        resolved_tier = (
            incoming_tier
            if incoming_tier and incoming_tier != 'unknown'
            else str(current.get('tier') or 'unknown').strip().lower()
        )
        resolved_credits = current.get('credits') if credits is None else credits
        resolved_expiry = session_expires_at or current.get('session_expires_at')
        self.secret_store.set_google_session(account_id, session_secret)
        if resolved_email:
            self._unmark_deleted_email(resolved_email)
        patched = self.db.patch_resource(
            ACCOUNT_RESOURCE_TYPE,
            account_id,
            {
                'email': resolved_email,
                'tier': resolved_tier,
                'status': 'ready',
                'enabled': True,
                'image_enabled': True,
                'video_enabled': resolved_tier in {'pro', 'ultra'},
                'session_expires_at': resolved_expiry,
                'quota_state': 'available',
                'image_quota_state': 'available',
                'video_quota_state': 'available',
                'image_auto_disabled': False,
                'video_auto_disabled': False,
                'credits': resolved_credits,
                'last_error': None,
                'unavailable_models': [],
            },
        )
        assert patched is not None
        if resolved_tier not in GOOGLE_FLOW_KNOWN_TIERS or not resolved_email or resolved_credits is None:
            try:
                self.try_refresh_session_api(account_id, verify_token=True)
                patched = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id) or patched
            except Exception:
                pass
        return self._sanitize(patched)

    def _deleted_emails_path(self) -> Path:
        return self.profile_root.parent / 'deleted_flow_emails.json'

    def _load_deleted_emails(self) -> set[str]:
        path = self._deleted_emails_path()
        if not path.is_file():
            return set()
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, list):
                return {str(item).strip().lower() for item in data if str(item).strip()}
        except Exception:
            pass
        return set()

    def _mark_deleted_email(self, email: str | None) -> None:
        clean = str(email or '').strip().lower()
        if not clean:
            return
        items = self._load_deleted_emails()
        items.add(clean)
        try:
            self._deleted_emails_path().write_text(
                json.dumps(sorted(items), ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
        except Exception:
            pass

    def _unmark_deleted_email(self, email: str | None) -> None:
        clean = str(email or '').strip().lower()
        if not clean:
            return
        items = self._load_deleted_emails()
        if clean in items:
            items.discard(clean)
            try:
                self._deleted_emails_path().write_text(
                    json.dumps(sorted(items), ensure_ascii=False, indent=2),
                    encoding='utf-8',
                )
            except Exception:
                pass

    def fail_login(self, account_id: str, error: str) -> None:
        account = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
        if account is None:
            return
        self.db.patch_resource(
            ACCOUNT_RESOURCE_TYPE,
            account_id,
            {'status': 'auth_expired', 'last_error': error},
        )

    def list_accounts(self) -> list[dict[str, Any]]:
        return [self._sanitize(item) for item in self.db.list_resources(ACCOUNT_RESOURCE_TYPE)]

    def get_account(self, account_id: str | None) -> dict[str, Any] | None:
        if not account_id:
            return None
        account = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
        return self._sanitize(account) if account else None

    def set_enabled(
        self,
        account_id: str,
        enabled: bool | None = None,
        image_enabled: bool | None = None,
        video_enabled: bool | None = None,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if enabled is not None:
            values['enabled'] = enabled
        if image_enabled is not None:
            values['image_enabled'] = image_enabled
        if video_enabled is not None:
            values['video_enabled'] = video_enabled
        patched = self.db.patch_resource(ACCOUNT_RESOURCE_TYPE, account_id, values)
        if patched is None:
            raise KeyError(account_id)
        return self._sanitize(patched)

    @staticmethod
    def _probe_access_token_http(access_token: str) -> tuple[bool, str | None, int | None]:
        """Verify an OAuth access token via HTTP and return (is_valid, tier, credits)."""
        if not access_token or not str(access_token).strip():
            return False, None, None
        token = str(access_token).strip()
        try:
            req = urllib.request.Request(
                GOOGLE_FLOW_CREDITS_URL,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Origin': 'https://labs.google',
                    'Referer': 'https://labs.google/',
                    'Accept': 'application/json',
                },
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode('utf-8'))
                    if isinstance(payload, dict):
                        tier = BrowserLoginWorker._map_tier_code(payload.get('userPaygateTier'))
                        credits_raw = payload.get('subscriptionCredits')
                        credits = int(credits_raw) if isinstance(credits_raw, (int, float)) else None
                        return True, (tier if tier != 'unknown' else None), credits
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                return False, None, None
        except Exception:
            pass

        try:
            req = urllib.request.Request(
                GOOGLE_USERINFO_URL,
                headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return True, None, None
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                return False, None, None
        except Exception:
            pass
        return False, None, None

    def sync_from_glabs(self) -> int:
        """Import and synchronize valid Google Flow accounts from G-Labs auth_session_multi.json."""
        glabs_path = Path(os.environ.get('APPDATA', '')) / 'G-Labs Automation' / 'auth_session_multi.json'
        if not glabs_path.is_file():
            return 0
        deleted_emails = self._load_deleted_emails()
        existing_by_email = {
            str(acc.get('email') or '').strip().lower(): acc
            for acc in self.db.list_resources(ACCOUNT_RESOURCE_TYPE)
            if str(acc.get('email') or '').strip()
        }
        proj_cache: dict[str, Any] = {}
        proj_cache_path = glabs_path.parent / 'project_cache.json'
        if proj_cache_path.is_file():
            try:
                loaded = json.loads(proj_cache_path.read_text(encoding='utf-8'))
                if isinstance(loaded, dict):
                    proj_cache = loaded
            except Exception:
                proj_cache = {}

        imported = 0
        try:
            glabs_data = json.loads(glabs_path.read_text(encoding='utf-8'))
        except Exception:
            return 0
        if not isinstance(glabs_data, list):
            return 0

        for g_acc in glabs_data:
            if not isinstance(g_acc, dict):
                continue
            email = str(g_acc.get('email') or '').strip().lower()
            if not email or '@' not in email or email in deleted_emails:
                continue
            g_status = str(g_acc.get('status') or '').strip().lower()
            g_token = str(g_acc.get('token') or '').strip()
            g_cookie = str(g_acc.get('cookie') or '').strip()
            g_tier = str(g_acc.get('tier') or 'free').strip().lower()
            if g_tier not in GOOGLE_FLOW_KNOWN_TIERS:
                g_tier = 'free'
            g_credits = g_acc.get('credits')
            credits_val = int(g_credits) if isinstance(g_credits, (int, float)) else None
            project_id = None
            if isinstance(proj_cache.get(email), dict):
                project_id = proj_cache[email].get('project_id')

            parsed_cookies = []
            if g_cookie:
                for part in g_cookie.split(';'):
                    if '=' in part:
                        k, v = part.strip().split('=', 1)
                        parsed_cookies.append({'name': k.strip(), 'value': v.strip()})

            if email in existing_by_email:
                if g_status != 'valid' or not (g_token or g_cookie):
                    continue
                existing_acc = existing_by_email[email]
                acc_id = str(existing_acc['id'])
                curr_secret = self.secret_store.get_google_session(acc_id)
                if not isinstance(curr_secret, dict):
                    curr_secret = {}
                if parsed_cookies and not curr_secret.get('cookies'):
                    curr_secret['cookies'] = parsed_cookies
                if g_token and not BrowserLoginWorker._extract_access_token(curr_secret.get('session')):
                    curr_secret['session'] = {'access_token': g_token, 'user': {'email': email}}
                    curr_secret['captured_at'] = _utc_now()
                self.secret_store.set_google_session(acc_id, curr_secret)

                curr_tier = str(existing_acc.get('tier') or '').strip().lower()
                resolved_tier = (
                    g_tier
                    if (g_tier in {'pro', 'ultra'} or curr_tier not in GOOGLE_FLOW_KNOWN_TIERS)
                    else curr_tier
                )
                update_fields: dict[str, Any] = {
                    'tier': resolved_tier,
                }
                if resolved_tier in {'pro', 'ultra'}:
                    update_fields['video_enabled'] = True
                    update_fields['video_auto_disabled'] = False
                    update_fields['video_quota_state'] = 'available'
                if credits_val is not None:
                    update_fields['credits'] = credits_val
                self.db.patch_resource(ACCOUNT_RESOURCE_TYPE, acc_id, update_fields)
                continue

            if g_status != 'valid' or not (g_token or g_cookie):
                continue

            created = self.create_account()
            acc_id = str(created['id'])
            session_secret: dict[str, Any] = {
                'captured_at': _utc_now(),
                'cookies': parsed_cookies,
            }
            if g_token:
                session_secret['session'] = {'access_token': g_token, 'user': {'email': email}}
            self.secret_store.set_google_session(acc_id, session_secret)
            self.db.patch_resource(
                ACCOUNT_RESOURCE_TYPE,
                acc_id,
                {
                    'email': email,
                    'tier': g_tier,
                    'status': 'ready',
                    'enabled': True,
                    'image_enabled': True,
                    'video_enabled': g_tier in {'pro', 'ultra'},
                    'quota_state': 'available',
                    'image_quota_state': 'available',
                    'video_quota_state': 'available',
                    'credits': credits_val,
                    'project_id': project_id,
                    'last_error': None,
                },
            )
            existing_by_email[email] = created
            imported += 1
        return imported

    def try_refresh_session_api(self, account_id: str, *, verify_token: bool = False) -> bool:
        """Attempt API-only or G-Labs parity session renewal using saved cookies / G-Labs session."""
        account = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id) or {}
        email = str(account.get('email') or '').strip().lower()
        current_tier = str(account.get('tier') or 'free').strip().lower()
        should_probe = bool(verify_token)

        session_secret = self.secret_store.get_google_session(account_id)
        if not isinstance(session_secret, dict):
            session_secret = {}

        glabs_token: str | None = None
        glabs_tier: str | None = None
        glabs_credits: int | None = None
        glabs_project_id: str | None = None
        glabs_status: str = ''

        # 1. Read G-Labs multi-session store to sync latest cookies/token/project
        glabs_path = Path(os.environ.get('APPDATA', '')) / 'G-Labs Automation' / 'auth_session_multi.json'
        if glabs_path.is_file() and email:
            try:
                glabs_data = json.loads(glabs_path.read_text(encoding='utf-8'))
                if isinstance(glabs_data, list):
                    for g_acc in glabs_data:
                        if isinstance(g_acc, dict) and str(g_acc.get('email', '')).strip().lower() == email:
                            glabs_status = str(g_acc.get('status') or '').strip().lower()
                            raw_tok = g_acc.get('token')
                            if isinstance(raw_tok, str) and raw_tok.strip():
                                glabs_token = raw_tok.strip()
                            g_cookie = g_acc.get('cookie')
                            if isinstance(g_cookie, str) and g_cookie.strip() and not session_secret.get('cookies'):
                                parsed_cookies = []
                                for part in g_cookie.split(';'):
                                    if '=' in part:
                                        k, v = part.strip().split('=', 1)
                                        parsed_cookies.append({'name': k.strip(), 'value': v.strip()})
                                if parsed_cookies:
                                    session_secret['cookies'] = parsed_cookies
                            raw_tier = str(g_acc.get('tier') or '').strip().lower()
                            if raw_tier in GOOGLE_FLOW_KNOWN_TIERS:
                                glabs_tier = raw_tier
                            raw_credits = g_acc.get('credits')
                            if isinstance(raw_credits, (int, float)):
                                glabs_credits = int(raw_credits)
                            proj_cache_path = glabs_path.parent / 'project_cache.json'
                            if proj_cache_path.is_file():
                                try:
                                    p_data = json.loads(proj_cache_path.read_text(encoding='utf-8'))
                                    if isinstance(p_data, dict) and email in p_data:
                                        pid = p_data[email].get('project_id')
                                        if pid:
                                            glabs_project_id = str(pid)
                                except Exception:
                                    pass
                            break
            except Exception:
                pass

        def _build_ready_patch(
            *,
            tier: str | None = None,
            credits: int | None = None,
            expires_at: str | None = None,
            email_override: str | None = None,
        ) -> dict[str, Any]:
            resolved_tier = tier or glabs_tier or (current_tier if current_tier in GOOGLE_FLOW_KNOWN_TIERS else 'free')
            patch: dict[str, Any] = {
                'status': 'ready',
                'enabled': True,
                'image_enabled': True,
                'image_auto_disabled': False,
                'image_quota_state': 'available',
                'quota_state': 'available',
                'last_error': None,
                'tier': resolved_tier,
            }
            if email_override and not email:
                patch['email'] = email_override
            if resolved_tier in {'pro', 'ultra'}:
                patch['video_enabled'] = True
                patch['video_auto_disabled'] = False
                patch['video_quota_state'] = 'available'
            resolved_credits = credits if credits is not None else glabs_credits
            if resolved_credits is not None:
                patch['credits'] = resolved_credits
            if expires_at is not None:
                patch['session_expires_at'] = expires_at
            return patch

        # 2. Attempt API-only session renewal via FLOW_AUTH_SESSION_URL / FLOW_MIGRATED_SESSION_URL using saved cookies
        cookies = session_secret.get('cookies')
        cookie_header = ''
        if isinstance(cookies, list) and cookies:
            cookie_header = '; '.join(
                f"{c['name']}={c['value']}"
                for c in cookies
                if isinstance(c, dict) and 'name' in c and 'value' in c
            )

        if cookie_header:
            for sess_url, origin, referer in (
                (FLOW_AUTH_SESSION_URL, 'https://labs.google', 'https://labs.google/fx/vi/tools/flow'),
                (FLOW_MIGRATED_SESSION_URL, 'https://flow.google.com', 'https://flow.google.com/'),
            ):
                try:
                    req = urllib.request.Request(
                        sess_url,
                        headers={
                            'User-Agent': (
                                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                'AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/133.0.0.0 Safari/537.36'
                            ),
                            'Cookie': cookie_header,
                            'Origin': origin,
                            'Referer': referer,
                            'Accept': 'application/json, text/plain, */*',
                        },
                    )
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode('utf-8'))
                            if isinstance(data, dict):
                                access_token = BrowserLoginWorker._extract_access_token(data)
                                if access_token and not data.get('error'):
                                    expires = data.get('expires')
                                    expires_at = None
                                    if isinstance(expires, str) and expires.strip():
                                        try:
                                            parsed = datetime.fromisoformat(expires.strip().replace('Z', '+00:00'))
                                            if parsed.tzinfo is None:
                                                parsed = parsed.replace(tzinfo=UTC)
                                            expires_at = parsed.isoformat()
                                        except ValueError:
                                            expires_at = None
                                    probed_tier, probed_credits = None, None
                                    if should_probe:
                                        _, probed_tier, probed_credits = self._probe_access_token_http(access_token)
                                    discovered_email = BrowserLoginWorker._find_email(data) or email
                                    session_secret['session'] = data
                                    session_secret['captured_at'] = _utc_now()
                                    self.secret_store.set_google_session(account_id, session_secret)
                                    self.db.patch_resource(
                                        ACCOUNT_RESOURCE_TYPE,
                                        account_id,
                                        _build_ready_patch(
                                            tier=probed_tier,
                                            credits=probed_credits,
                                            expires_at=expires_at,
                                            email_override=discovered_email,
                                        ),
                                    )
                                    return True
                except Exception:
                    continue

        # 3. Check G-Labs token or existing saved access_token
        saved_session_obj = session_secret.get('session') if isinstance(session_secret.get('session'), dict) else {}
        candidate_token = glabs_token or BrowserLoginWorker._extract_access_token(saved_session_obj)
        if candidate_token:
            tok_ok, probed_tier, probed_credits = self._probe_access_token_http(candidate_token)
            if tok_ok:
                session_secret['session'] = {'access_token': candidate_token, 'user': {'email': email}}
                session_secret['captured_at'] = _utc_now()
                self.secret_store.set_google_session(account_id, session_secret)
                self.db.patch_resource(
                    ACCOUNT_RESOURCE_TYPE,
                    account_id,
                    _build_ready_patch(tier=probed_tier, credits=probed_credits),
                )
                return True

        # 4. If live browser session exists, refresh NextAuth inside the browser page context
        client_getter = getattr(self.login_worker, 'get_live_session', None)
        if callable(client_getter):
            try:
                client = client_getter(account_id)
                page = getattr(client, 'page', None)
                if page and hasattr(page, 'evaluate'):
                    sess_data = page.evaluate("""
                    async () => {
                        for (const u of ['https://flow.google.com/fx/api/auth/session', 'https://labs.google/fx/api/auth/session']) {
                            try {
                                const r = await fetch(u);
                                if (r.ok) {
                                    const d = await r.json();
                                    if (d && (d.access_token || d.accessToken)) return d;
                                }
                            } catch (e) {}
                        }
                        return {};
                    }
                    """)
                    tok = BrowserLoginWorker._extract_access_token(sess_data)
                    if tok and isinstance(sess_data, dict) and not sess_data.get('error'):
                        probed_tier, probed_credits = None, None
                        if should_probe:
                            _, probed_tier, probed_credits = self._probe_access_token_http(tok)
                        discovered_email = BrowserLoginWorker._find_email(sess_data) or email
                        session_secret['session'] = sess_data
                        session_secret['captured_at'] = _utc_now()
                        self.secret_store.set_google_session(account_id, session_secret)
                        self.db.patch_resource(
                            ACCOUNT_RESOURCE_TYPE,
                            account_id,
                            _build_ready_patch(
                                tier=probed_tier,
                                credits=probed_credits,
                                email_override=discovered_email,
                            ),
                        )
                        return True
            except Exception:
                pass

        return False

    def check_account(self, account_id: str) -> dict[str, Any]:
        """Actively check and recover a single Google Flow account session."""
        account = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
        if account is None:
            raise KeyError(account_id)
        has_live = getattr(self.login_worker, 'has_live_session', None)
        already_live = bool(callable(has_live) and has_live(account_id))
        refreshed = False
        try:
            refreshed = self.try_refresh_session_api(account_id, verify_token=True)
        except Exception:
            refreshed = False

        if not refreshed and not already_live:
            try:
                refreshed = self.try_refresh_session_api(account_id, verify_token=False)
            except Exception:
                refreshed = False

        raw = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id) or account
        profile_dir = self.profile_dir_for_account(raw)
        has_reusable_profile = getattr(self.login_worker, 'has_reusable_profile', None)
        has_reusable = False
        if callable(has_reusable_profile):
            try:
                has_reusable = bool(has_reusable_profile(profile_dir))
            except Exception:
                has_reusable = False

        was_expired = str(account.get('status') or '').strip().lower() in {'auth_expired', 'error'}
        is_alive = bool(
            already_live
            or refreshed
            or (not was_expired and (has_reusable or self._saved_session_is_valid(raw)))
        )
        if is_alive:
            tier = str(raw.get('tier') or 'free').strip().lower()
            patch_values: dict[str, Any] = {
                'status': 'ready',
                'enabled': True,
                'image_enabled': True,
                'image_auto_disabled': False,
                'last_error': None,
            }
            if tier in {'pro', 'ultra'}:
                patch_values['video_enabled'] = True
                patch_values['video_auto_disabled'] = False
            patched = self.db.patch_resource(ACCOUNT_RESOURCE_TYPE, account_id, patch_values) or raw
            result = self._sanitize(patched)
            result['alive'] = True
            return result

        patched = self.db.patch_resource(
            ACCOUNT_RESOURCE_TYPE,
            account_id,
            {
                'status': 'auth_expired',
                'last_error': 'Phiên đăng nhập đã hết hạn hoặc cần mở Flow xác minh lại.',
            },
        ) or raw
        result = self._sanitize(patched)
        result['alive'] = False
        return result

    def check_all_accounts(self, *, prune_dead: bool = False) -> dict[str, Any]:
        """Sync from G-Labs, actively check & recover all accounts, and optionally delete dead ones."""
        imported_count = 0
        try:
            imported_count = self.sync_from_glabs()
        except Exception:
            imported_count = 0

        kept: list[dict[str, Any]] = []
        deleted: list[dict[str, Any]] = []
        recovered_count = imported_count
        dead_count = 0

        for account in list(self.list_accounts()):
            acc_id = str(account['id'])
            was_ready = (
                str(account.get('status') or '').lower() == 'ready'
                and account.get('enabled') is not False
                and bool(account.get('session_present'))
            )
            try:
                checked = self.check_account(acc_id)
            except KeyError:
                continue
            is_ready = (
                str(checked.get('status') or '').lower() == 'ready'
                and checked.get('enabled') is not False
                and bool(checked.get('session_present'))
            )
            if is_ready:
                if not was_ready:
                    recovered_count += 1
                kept.append(checked)
            else:
                dead_count += 1
                if prune_dead:
                    self.remove(acc_id)
                    deleted.append({
                        'id': acc_id,
                        'email': checked.get('email'),
                        'status': checked.get('status'),
                        'last_error': checked.get('last_error'),
                    })
                else:
                    kept.append(checked)

        active_count = sum(
            1
            for acc in kept
            if str(acc.get('status') or '').lower() == 'ready' and acc.get('enabled') is not False
        )
        return {
            'ok': True,
            'imported_count': imported_count,
            'recovered_count': recovered_count,
            'active_count': active_count,
            'total_count': len(kept),
            'kept_count': len(kept),
            'dead_count': 0 if prune_dead else dead_count,
            'deleted_count': len(deleted),
            'deleted': deleted,
            'accounts': kept,
        }

    def renew(self, account_id: str) -> dict[str, Any]:
        account = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
        if account is None:
            raise KeyError(account_id)
        has_live_session = getattr(self.login_worker, 'has_live_session', None)
        if callable(has_live_session) and has_live_session(account_id):
            patched = self.db.patch_resource(
                ACCOUNT_RESOURCE_TYPE,
                account_id,
                {'status': 'ready', 'enabled': True, 'image_enabled': True, 'last_error': None},
            )
            assert patched is not None
            return self._sanitize(patched)

        if self.try_refresh_session_api(account_id):
            refreshed = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
            if refreshed is not None:
                return self._sanitize(refreshed)

        resume_session = getattr(self.login_worker, 'resume_session', None)
        profile_dir = self.profile_dir_for_account(account)
        has_reusable_profile = getattr(self.login_worker, 'has_reusable_profile', None)
        reusable_profile = False
        if callable(resume_session) and callable(has_reusable_profile):
            try:
                reusable_profile = bool(has_reusable_profile(profile_dir))
            except Exception:
                reusable_profile = False
        if not self._saved_session_is_valid(account) and not reusable_profile:
            return self.start_login(account_id)
        if not callable(resume_session):
            return self.start_login(account_id)
        patched = self.db.patch_resource(
            ACCOUNT_RESOURCE_TYPE,
            account_id,
            {'status': 'connecting', 'last_error': None},
        )
        assert patched is not None
        resume_session(
            account_id,
            profile_dir,
            self.complete_login,
            self.fail_login,
        )
        refreshed = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
        assert refreshed is not None
        return self._sanitize(refreshed)

    def verify_interactively(self, account_id: str) -> dict[str, Any]:
        """Reopen an existing account profile visibly for manual Google verification."""
        account = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
        if account is None:
            raise KeyError(account_id)

        close_session = getattr(self.login_worker, 'close_session', None)
        if callable(close_session):
            close_session(account_id)

        terminate_profile_processes = getattr(self.login_worker, '_terminate_profile_processes', None)
        if callable(terminate_profile_processes):
            terminate_profile_processes(self.profile_dir_for_account(account))

        # A headless resume thread may need a brief moment to release the profile
        # lock before the visible Chrome window can reuse that same account data.
        starting_sessions = getattr(self.login_worker, '_starting_sessions', set())
        deadline = time.monotonic() + 3.0
        while account_id in starting_sessions and time.monotonic() < deadline:
            time.sleep(0.1)

        return self.start_login(account_id)

    def remove(self, account_id: str) -> bool:
        acc_id = str(account_id or '').strip()
        if not acc_id:
            return False
        existing = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, acc_id)
        profile_dirs_to_clean: list[Path] = []
        if existing:
            custom_p = existing.get('profile_dir')
            if custom_p:
                profile_dirs_to_clean.append(Path(custom_p))
        std_p = self.profile_root / acc_id
        if std_p not in profile_dirs_to_clean:
            profile_dirs_to_clean.append(std_p)

        close_session = getattr(self.login_worker, 'close_session', None)
        if callable(close_session):
            try:
                close_session(acc_id)
            except Exception:
                pass

        terminate_procs = getattr(self.login_worker, '_terminate_profile_processes', None)
        if not callable(terminate_procs) and hasattr(BrowserLoginWorker, '_terminate_profile_processes'):
            terminate_procs = BrowserLoginWorker._terminate_profile_processes

        if callable(terminate_procs):
            for p_dir in profile_dirs_to_clean:
                try:
                    terminate_procs(p_dir)
                except Exception:
                    pass

        removed = self.db.delete_resource(ACCOUNT_RESOURCE_TYPE, acc_id)
        if removed:
            if existing and existing.get('email'):
                self._mark_deleted_email(str(existing.get('email')))
            try:
                self.secret_store.delete_google_session(acc_id)
            except Exception:
                pass

            for p_dir in profile_dirs_to_clean:
                try:
                    _rmtree_robust(p_dir)
                except Exception:
                    pass

        return removed

    def clean_profile_caches(self) -> dict[str, Any]:
        """Evict non-essential Chromium caches across all registered profiles, and remove orphan profiles and sessions."""
        import hashlib

        accounts = self.db.list_resources(ACCOUNT_RESOURCE_TYPE)
        registered_account_ids: set[str] = set()
        registered_profile_paths: set[str] = set()
        registered_session_hashes: set[str] = set()

        for acc in accounts:
            acc_id = str(acc.get('id') or '').strip()
            if acc_id:
                registered_account_ids.add(acc_id)
                registered_session_hashes.add(hashlib.sha256(acc_id.encode('utf-8')).hexdigest() + '.enc')
                std_dir = self.profile_root / acc_id
                try:
                    registered_profile_paths.add(str(std_dir.resolve()).lower())
                except Exception:
                    registered_profile_paths.add(str(std_dir).lower())
            p_dir = self.profile_dir_for_account(acc)
            try:
                registered_profile_paths.add(str(p_dir.resolve()).lower())
            except Exception:
                registered_profile_paths.add(str(p_dir).lower())

        # Measure pre-total bytes across all profile folders
        all_profile_dirs_to_measure: set[Path] = set()
        if self.profile_root.exists():
            for child in self.profile_root.iterdir():
                if child.is_dir():
                    all_profile_dirs_to_measure.add(child)
        for acc in accounts:
            p_dir = self.profile_dir_for_account(acc)
            if p_dir.is_dir():
                all_profile_dirs_to_measure.add(p_dir)

        pre_total_bytes = sum(_calc_dir_size_bytes(d) for d in all_profile_dirs_to_measure)

        freed_bytes = 0
        cleaned_profiles_count = 0
        orphan_profiles_removed = 0
        orphan_sessions_removed = 0

        # 1. Evict caches in registered profiles
        for acc in accounts:
            profile_dirs = [self.profile_dir_for_account(acc)]
            acc_id = str(acc.get('id') or '').strip()
            if acc_id:
                std_dir = self.profile_root / acc_id
                if std_dir not in profile_dirs and std_dir.is_dir():
                    profile_dirs.append(std_dir)

            profile_had_cache = False
            for p_dir in profile_dirs:
                if not p_dir.is_dir():
                    continue
                profile_freed = _evict_profile_cache_subdirs(p_dir)
                if profile_freed > 0 or p_dir.is_dir():
                    profile_had_cache = True
                freed_bytes += profile_freed

            if profile_had_cache:
                cleaned_profiles_count += 1

        # 2. Detect and remove orphan profile directories in profile_root
        if self.profile_root.exists():
            terminate_procs = getattr(self.login_worker, '_terminate_profile_processes', None)
            if not callable(terminate_procs) and hasattr(BrowserLoginWorker, '_terminate_profile_processes'):
                terminate_procs = BrowserLoginWorker._terminate_profile_processes

            for child in list(self.profile_root.iterdir()):
                if not child.is_dir():
                    continue
                child_resolved = ""
                try:
                    child_resolved = str(child.resolve()).lower()
                except Exception:
                    child_resolved = str(child).lower()

                if child.name not in registered_account_ids and child_resolved not in registered_profile_paths:
                    orphan_size = _calc_dir_size_bytes(child)
                    if callable(terminate_procs):
                        try:
                            terminate_procs(child)
                        except Exception:
                            pass
                    if _rmtree_robust(child):
                        orphan_profiles_removed += 1
                        freed_bytes += orphan_size

        # 3. Detect and remove orphan session files
        secret_dirs: list[Path] = []
        storage_dir = getattr(self.secret_store, '_storage_dir', None)
        if storage_dir and Path(storage_dir).exists():
            secret_dirs.append(Path(storage_dir))
        cand1 = self.profile_root.parent / 'secrets' / 'google-flow'
        if cand1.exists() and cand1 not in secret_dirs:
            secret_dirs.append(cand1)
        cand2 = self.profile_root.parent.parent / 'secrets' / 'google-flow'
        if cand2.exists() and cand2 not in secret_dirs:
            secret_dirs.append(cand2)

        for s_dir in secret_dirs:
            try:
                for enc_file in list(s_dir.glob('*.enc')):
                    if enc_file.name not in registered_session_hashes:
                        f_size = _calc_dir_size_bytes(enc_file)
                        if _rmtree_robust(enc_file):
                            orphan_sessions_removed += 1
                            freed_bytes += f_size
            except Exception:
                pass

        # Measure post-total bytes across remaining profile folders
        remaining_dirs: set[Path] = set()
        if self.profile_root.exists():
            for child in self.profile_root.iterdir():
                if child.is_dir():
                    remaining_dirs.add(child)
        for acc in accounts:
            p_dir = self.profile_dir_for_account(acc)
            if p_dir.is_dir():
                remaining_dirs.add(p_dir)

        post_total_bytes = sum(_calc_dir_size_bytes(d) for d in remaining_dirs)
        actual_freed = max(freed_bytes, max(0, pre_total_bytes - post_total_bytes))

        return {
            'ok': True,
            'status': 'success',
            'total_size_mb': round(post_total_bytes / (1024 * 1024), 2),
            'freed_mb': round(actual_freed / (1024 * 1024), 2),
            'orphan_profiles_removed': orphan_profiles_removed,
            'orphan_sessions_removed': orphan_sessions_removed,
            'cleaned_profiles_count': cleaned_profiles_count,
        }

    def prune_dead_accounts(self) -> dict[str, Any]:
        """Check all accounts, keep live/usable ones, and remove dead/expired ones."""
        return self.check_all_accounts(prune_dead=True)

    def shutdown(self) -> None:
        shutdown = getattr(self.login_worker, 'shutdown', None)
        if callable(shutdown):
            shutdown()

    def resume_all_accounts(self) -> dict[str, Any]:
        """Ensure all accounts in the pool are validated and ready in DB, with Chrome launched on demand."""
        self.resume_saved_sessions(auto_launch_all=False)
        return {'status': 'ready', 'account_count': len(self.list_accounts())}

    def resume_saved_sessions(self, auto_launch_all: bool = False) -> None:
        del auto_launch_all
        try:
            self.sync_from_glabs()
        except Exception:
            pass
        for account in self.list_accounts():
            raw = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account['id'])
            if raw is None:
                continue
            acc_id = str(account['id'])
            if raw.get('enabled') is False or (
                raw.get('status') == 'auth_expired'
                and 'challenge' in str(raw.get('last_error') or '').lower()
            ):
                continue
            profile_dir = self.profile_dir_for_account(raw)

            # 1. Fast API / G-Labs session refresh first (<1ms)
            refreshed = False
            try:
                refreshed = self.try_refresh_session_api(acc_id)
            except Exception:
                refreshed = False

            # Check if account has a reusable profile directory
            has_reusable = False
            has_reusable_profile = getattr(self.login_worker, 'has_reusable_profile', None)
            if callable(has_reusable_profile):
                try:
                    has_reusable = bool(has_reusable_profile(profile_dir))
                except Exception:
                    has_reusable = False

            # 2. Check for active CDP endpoint (only re-attach if Chrome is ALREADY running)
            cdp_endpoint = None
            existing_cdp = getattr(self.login_worker, '_existing_profile_cdp_endpoint', None)
            if callable(existing_cdp):
                cdp_endpoint = existing_cdp(profile_dir)

            resume_session = getattr(self.login_worker, 'resume_session', None)
            has_live = getattr(self.login_worker, 'has_live_session', None)
            already_live = bool(callable(has_live) and has_live(acc_id))

            missing_snapshot = self.secret_store.get_google_session(acc_id) is None
            if (
                (cdp_endpoint is not None or (has_reusable and not refreshed and missing_snapshot))
                and callable(resume_session)
                and not already_live
            ):
                self.db.patch_resource(
                    ACCOUNT_RESOURCE_TYPE,
                    acc_id,
                    {'status': 'connecting', 'last_error': None},
                )
                resume_session(
                    acc_id,
                    profile_dir,
                    self.complete_login,
                    self.fail_login,
                )
            elif already_live or refreshed or (
                raw.get('status') != 'auth_expired'
                and (has_reusable or self._saved_session_is_valid(raw))
            ):
                # Mark account ready and enabled so it is eligible in the pool.
                # Chrome will be spawned on demand when leased for generation to conserve RAM.
                tier = str(raw.get('tier') or 'free').strip().lower()
                patch_vals: dict[str, Any] = {
                    'status': 'ready',
                    'enabled': True,
                    'image_enabled': True,
                    'image_auto_disabled': False,
                    'last_error': None,
                }
                if tier in {'pro', 'ultra'}:
                    patch_vals['video_enabled'] = True
                    patch_vals['video_auto_disabled'] = False
                self.db.patch_resource(
                    ACCOUNT_RESOURCE_TYPE,
                    acc_id,
                    patch_vals,
                )
            else:
                self.db.patch_resource(
                    ACCOUNT_RESOURCE_TYPE,
                    acc_id,
                    {'status': 'auth_expired', 'last_error': 'No saved session found.'},
                )
            is_interactive = getattr(self.login_worker, 'is_interactive', None)
            session_mode = getattr(self.login_worker, 'session_mode', None)
            currently_visible = (
                (callable(is_interactive) and is_interactive(acc_id))
                or (callable(session_mode) and session_mode(acc_id) == 'visible')
            )
            hide_profile_windows = getattr(self.login_worker, '_hide_profile_windows', None)
            if callable(hide_profile_windows) and not currently_visible:
                try:
                    hide_profile_windows(profile_dir)
                except Exception:
                    pass

    def status(self) -> dict[str, Any]:
        accounts = self.list_accounts()
        ready = [
            account
            for account in accounts
            if account['status'] == 'ready'
            and account['session_present']
            and not self._session_expired(account)
        ]
        enabled = [account for account in ready if account['enabled']]
        return {
            'provider': 'google_flow',
            'connected': bool(ready),
            'account_count': len(accounts),
            'enabled_account_count': len(enabled),
            'image_model': 'nano_banana_2',
            'video_model': 'veo_31_fast',
        }

    def refresh_account_credits(self) -> list[dict[str, Any]]:
        # Credits are refreshed as part of normal session capture.  Keep this
        # route hook cheap and side-effect free when no live broker is open.
        return self.list_accounts()

    def available_account_count(self, model_id: str) -> int:
        model = self._model(model_id)
        with self._lease_condition:
            return len(self._eligible_accounts(model, include_busy=True))

    def select_account(self, model_id: str) -> dict[str, Any]:
        model = self._model(model_id)
        with self._lease_condition:
            eligible = self._eligible_accounts(model, include_busy=True)
            if not eligible:
                self._raise_selection_error(model, exclude_account_ids=set())
            account = eligible[0]
            self._lease_seq += 1
            self._account_last_lease_seq[account['id']] = self._lease_seq
            self._rotation_index[model_id] = self._rotation_index.get(model_id, 0) + 1
            return account

    def lease_account(
        self,
        model_id: str,
        *,
        exclude_account_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        model = self._model(model_id)
        excluded = set(exclude_account_ids or ())
        with self._lease_condition:
            while True:
                eligible = [
                    account
                    for account in self._eligible_accounts(model, include_busy=False)
                    if account['id'] not in excluded and account['id'] not in self._closing_accounts
                ]
                if eligible:
                    account = eligible[0]
                    self._lease_seq += 1
                    self._account_last_lease_seq[account['id']] = self._lease_seq
                    self._rotation_index[model_id] = self._rotation_index.get(model_id, 0) + 1
                    self._active_jobs[account['id']] = self._active_jobs.get(account['id'], 0) + 1
                    leased = dict(account)
                    leased['active_jobs'] = self._active_jobs[account['id']]
                    return leased

                closing_match = any(
                    account['id'] in self._closing_accounts
                    and account['id'] not in excluded
                    and self._account_matches_static_model(account, model)
                    for account in self.list_accounts()
                )
                if closing_match:
                    self._lease_condition.wait(timeout=5.0)
                    continue
                self._raise_selection_error(model, exclude_account_ids=excluded, leasing=True)

    def release_account(self, account_id: str) -> None:
        with self._lease_condition:
            active = self._active_jobs.get(account_id, 0)
            if active <= 1:
                self._active_jobs.pop(account_id, None)
            else:
                self._active_jobs[account_id] = active - 1
            self._lease_condition.notify_all()
        # Touch session last_activity and enforce RAM budget if limit exceeded
        live_sessions = getattr(self.login_worker, '_live_sessions', {})
        session = live_sessions.get(account_id)
        if session is not None:
            session.last_activity = time.monotonic()
        if len(live_sessions) > self.max_active_sessions:
            self.enforce_memory_budget(target_spare=0)

    def ensure_live_session(self, account_id: str, *, timeout_seconds: float = 60.0) -> None:
        account = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
        if account is None:
            raise KeyError(account_id)
        if not self._saved_session_is_valid(account):
            raise ProviderAuthError('Google Flow saved session is missing or expired; renew this account once.')
        has_live_session = getattr(self.login_worker, 'has_live_session', None)
        resume_session = getattr(self.login_worker, 'resume_session', None)
        if not callable(has_live_session) or not callable(resume_session):
            raise ProviderAuthError('Google Flow live browser session is unavailable.')
        if has_live_session(account_id):
            return

        self.enforce_memory_budget(target_spare=1)
        resume_session(
            account_id,
            self.profile_dir_for_account(account),
            self.complete_login,
            self.fail_login,
        )
        deadline = time.monotonic() + max(10.0, timeout_seconds)
        while time.monotonic() < deadline:
            account = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
            if account and account.get('status') in ('auth_expired', 'error'):
                raise ProviderAuthError(account.get('last_error') or 'Google Flow session expired.')
            if has_live_session(account_id):
                return
            time.sleep(0.2)
        if not has_live_session(account_id):
            raise ProviderAuthError('The saved Google Flow session could not be reopened; renew this account once.')

    def mark_auth_expired(self, account_id: str, error: str | None = None) -> None:
        if self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id) is None:
            raise KeyError(account_id)
        # Match G-Labs: Never delete saved session credentials on error.
        # Keeping cookies and token allows automatic refresh and recovery.
        self.db.patch_resource(
            ACCOUNT_RESOURCE_TYPE,
            account_id,
            {'status': 'auth_expired', 'last_error': error or 'Google Flow saved session expired.'},
        )
        close_session = getattr(self.login_worker, 'close_session', None)
        if callable(close_session):
            close_session(account_id)

    def mark_quota_limited(
        self,
        account_id: str,
        *,
        model_id: str | None = None,
        cooldown_seconds: float = 60.0,
    ) -> None:
        account = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
        if account is None:
            raise KeyError(account_id)
        kinds = [self._model(model_id)['kind']] if model_id else ['image', 'video']
        settings = self.db.get_resource('settings', 'default') or {}
        auto_disable = bool(settings.get('auto_disable_on_quota', True))
        values: dict[str, Any] = {'quota_state': 'cooldown'}
        with self._lease_condition:
            for kind in kinds:
                self._cooldown_until[(account_id, kind)] = time.monotonic() + max(0.0, cooldown_seconds)
                values[f'{kind}_quota_state'] = 'cooldown'
                values[f'{kind}_auto_disabled'] = auto_disable
            self.db.patch_resource(ACCOUNT_RESOURCE_TYPE, account_id, values)
            self._lease_condition.notify_all()

    def mark_model_unavailable(self, account_id: str, model_id: str) -> None:
        self._model(model_id)
        account = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
        if account is None:
            raise KeyError(account_id)
        unavailable = set(account.get('unavailable_models') or [])
        unavailable.add(model_id)
        self.db.patch_resource(
            ACCOUNT_RESOURCE_TYPE,
            account_id,
            {'unavailable_models': sorted(unavailable)},
        )

    def update_project_cache(self, account_id: str, project_id: str) -> dict[str, Any]:
        account = self.db.get_resource(ACCOUNT_RESOURCE_TYPE, account_id)
        if account is None:
            raise KeyError(account_id)
        current_id = str(account.get('project_id') or '')
        project_used = int(account.get('project_used') or 0) + 1 if current_id == project_id else 1
        patched = self.db.patch_resource(
            ACCOUNT_RESOURCE_TYPE,
            account_id,
            {'project_id': project_id, 'project_used': project_used},
        )
        assert patched is not None
        return self._sanitize(patched)

    def get_session_secret(self, account_id: str) -> dict[str, Any] | None:
        return self.secret_store.get_google_session(account_id)

    @staticmethod
    def _session_expired(account: dict[str, Any]) -> bool:
        raw = account.get('session_expires_at')
        if not raw:
            return False
        try:
            expires_at = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            return expires_at <= datetime.now(UTC)
        except (TypeError, ValueError):
            return False

    def _saved_session_is_valid(self, account: dict[str, Any]) -> bool:
        if account.get('status') in ('auth_expired', 'error'):
            return False
        session = self.secret_store.get_google_session(account['id'])
        if session is not None and not self._session_expired(account):
            return True
        try:
            if self.try_refresh_session_api(str(account['id'])):
                return True
        except Exception:
            pass
        has_reusable_profile = getattr(self.login_worker, 'has_reusable_profile', None)
        if callable(has_reusable_profile):
            try:
                profile_dir = self.profile_dir_for_account(account)
                if has_reusable_profile(profile_dir):
                    return True
            except Exception:
                pass
        return False

    @staticmethod
    def _model(model_id: str) -> dict[str, Any]:
        model = GOOGLE_FLOW_MODEL_BY_ID.get(model_id)
        if model is None:
            raise ProviderError(f'Unsupported Google Flow model: {model_id}')
        return model

    def _recover_expired_cooldowns(self, account: dict[str, Any]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        now = time.monotonic()
        for kind in ('image', 'video'):
            if account.get(f'{kind}_quota_state') != 'cooldown':
                continue
            deadline = self._cooldown_until.get((account['id'], kind))
            if deadline is None or deadline <= now:
                self._cooldown_until.pop((account['id'], kind), None)
                values[f'{kind}_quota_state'] = 'available'
                values[f'{kind}_auto_disabled'] = False
        if values:
            merged = {**account, **values}
            values['quota_state'] = (
                'cooldown'
                if any(merged.get(f'{kind}_quota_state') == 'cooldown' for kind in ('image', 'video'))
                else 'available'
            )
            patched = self.db.patch_resource(ACCOUNT_RESOURCE_TYPE, account['id'], values)
            if patched is not None:
                return patched
        return account

    def _account_matches_static_model(self, account: dict[str, Any], model: dict[str, Any]) -> bool:
        kind = str(model['kind'])
        if not bool(account.get('enabled', True)) or not bool(account.get(f'{kind}_enabled', True)):
            return False
        account_tier = str(account.get('tier') or 'unknown').lower()
        # Free accounts are strictly limited to image generation; never video.
        if kind == 'video' and account_tier == 'free':
            return False
        model_tiers = set(model['tiers'])
        if account_tier not in model_tiers and not (
            account_tier == 'unknown' and GOOGLE_FLOW_KNOWN_TIERS.issubset(model_tiers)
        ):
            return False
        if str(model['id']) in set(account.get('unavailable_models') or []):
            return False
        credits = account.get('credits')
        minimum_credit_cost = int(model.get('minimum_credit_cost') or 0)
        if credits is not None and int(credits) < minimum_credit_cost:
            return False
        return True

    def _eligible_accounts(self, model: dict[str, Any], *, include_busy: bool) -> list[dict[str, Any]]:
        eligible: list[dict[str, Any]] = []
        kind = str(model['kind'])
        parallel_capacity = (
            GOOGLE_FLOW_VIDEO_MAX_INFLIGHT_PER_ACCOUNT
            if kind == 'video'
            else GOOGLE_FLOW_IMAGE_MAX_INFLIGHT_PER_ACCOUNT
        )
        for raw in self.db.list_resources(ACCOUNT_RESOURCE_TYPE):
            raw = self._recover_expired_cooldowns(raw)
            account = self._sanitize(raw)
            if not self._account_matches_static_model(account, model):
                continue
            if account.get('status') != 'ready' or not self._saved_session_is_valid(raw):
                continue
            if account.get(f'{kind}_quota_state') in {'cooldown', 'exhausted'}:
                continue
            if not include_busy:
                active_jobs = int(account.get('active_jobs') or 0)
                if active_jobs >= parallel_capacity:
                    continue
            eligible.append(account)
        if kind == 'image':
            # Least-loaded + Round-Robin across all eligible accounts first,
            # breaking ties by preferring Free accounts to conserve Pro/Ultra video credits.
            tier_rank = {'free': 0, 'pro': 1, 'ultra': 2}
            eligible.sort(key=lambda acc: (
                int(acc.get('active_jobs') or 0),
                self._account_last_lease_seq.get(acc.get('id', ''), 0),
                tier_rank.get(str(acc.get('tier', '')).lower(), 99),
                acc.get('id', ''),
            ))
        else:
            eligible.sort(key=lambda acc: (
                int(acc.get('active_jobs') or 0),
                self._account_last_lease_seq.get(acc.get('id', ''), 0),
                acc.get('id', ''),
            ))
        return eligible

    def _raise_selection_error(
        self,
        model: dict[str, Any],
        *,
        exclude_account_ids: set[str],
        leasing: bool = False,
    ) -> None:
        kind = str(model['kind'])
        accounts = [self._sanitize(item) for item in self.db.list_resources(ACCOUNT_RESOURCE_TYPE)]
        configured = [
            account
            for account in accounts
            if account['id'] not in exclude_account_ids
            and bool(account.get('enabled', True))
            and bool(account.get(f'{kind}_enabled', True))
            and not (kind == 'video' and str(account.get('tier') or '').lower() == 'free')
            and (
                str(account.get('tier') or 'unknown') in model['tiers']
                or (
                    str(account.get('tier') or 'unknown') == 'unknown'
                    and GOOGLE_FLOW_KNOWN_TIERS.issubset(set(model['tiers']))
                )
            )
        ]
        if not configured:
            if exclude_account_ids and accounts:
                raise ProviderError(f'No selectable Google Flow account remains for {model["name"]}.')
            raise ProviderError(f'No enabled Google Flow account is configured for {model["name"]}.')
        if leasing and any(int(account.get('active_jobs') or 0) > 0 for account in configured):
            raise ProviderTransientError('All eligible Google Flow accounts are busy.')
        session_ready = [
            account
            for account in configured
            if account.get('status') == 'ready'
            and account.get('session_present')
            and not self._session_expired(account)
        ]
        if not session_ready:
            raise ProviderAuthError('Google Flow saved session is missing or expired; renew this account once.')
        if all(account.get(f'{kind}_quota_state') in {'cooldown', 'exhausted'} for account in session_ready):
            raise ProviderQuotaError('Google Flow accounts are cooling down or quota exhausted.')
        raise ProviderError(f'No selectable Google Flow account remains for {model["name"]}.')

    def _sanitize(self, account: dict[str, Any] | None) -> dict[str, Any]:
        if account is None:
            raise KeyError('account')
        safe = dict(account)
        global_quota = str(safe.get('quota_state') or 'unknown')
        safe.setdefault('enabled', True)
        safe.setdefault('image_enabled', True)
        safe.setdefault('video_enabled', True)
        safe.setdefault('image_auto_disabled', False)
        safe.setdefault('video_auto_disabled', False)
        safe.setdefault('image_quota_state', global_quota)
        safe.setdefault('video_quota_state', global_quota)
        safe.setdefault('unavailable_models', [])
        safe.setdefault('project_id', None)
        safe.setdefault('project_used', 0)
        safe['active_jobs'] = self._active_jobs.get(account['id'], 0)
        has_reusable_profile = getattr(self.login_worker, 'has_reusable_profile', None)
        reusable = False
        if callable(has_reusable_profile):
            try:
                reusable = bool(has_reusable_profile(self.profile_dir_for_account(account)))
            except Exception:
                reusable = False
        safe['session_present'] = (self.secret_store.get_google_session(account['id']) is not None) or reusable
        has_live_session = getattr(self.login_worker, 'has_live_session', None)
        safe['live_session'] = bool(callable(has_live_session) and has_live_session(account['id']))
        session_mode = getattr(self.login_worker, 'session_mode', None)
        safe['browser_mode'] = session_mode(account['id']) if callable(session_mode) else None
        return safe

    @staticmethod
    def _looks_like_closed_session(exc: BaseException) -> bool:
        return _looks_like_closed_session(exc)


def _looks_like_closed_session(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            'browser has been closed',
            'context or browser has been closed',
            'target page, context or browser has been closed',
            'live browser session is unavailable',
            'live browser session closed',
            'target closed',
            'target crashed',
            'page crashed',
            'connection closed',
        )
    )


class GoogleFlowBrowserClient:
    """Run verified Google Flow generation through the account's live browser session."""

    _browser_ui_lock = threading.Lock()

    def __init__(self, output_dir: str | Path, session_worker: Any):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session_worker = session_worker

    def generate(self, scene: dict[str, Any], account: dict[str, Any], session_secret: dict[str, Any]) -> str:
        del session_secret
        callback = lambda context: self._generate_in_context(context, scene)

        execute_in_session = getattr(self.session_worker, 'execute_in_session', None)
        if not callable(execute_in_session):
            raise ProviderAuthError('Google Flow live browser session is unavailable.')

        return str(
            execute_in_session(
                account['id'],
                callback,
                timeout_seconds=240.0,
            )
        )

    @staticmethod
    def _safe_response_error_detail(response: Any) -> str:
        """Return a short provider error without leaking opaque response payloads."""
        try:
            payload = response.json()
        except Exception:
            return f'HTTP {getattr(response, "status", "unknown")}'
        if not isinstance(payload, dict):
            return f'HTTP {getattr(response, "status", "unknown")}'
        error = payload.get('error')
        if not isinstance(error, dict):
            return f'HTTP {getattr(response, "status", "unknown")}'
        parts: list[str] = []
        for key in ('code', 'status', 'message'):
            value = error.get(key)
            if isinstance(value, (str, int, float)) and str(value).strip():
                parts.append(str(value).strip())
        details = error.get('details')
        if isinstance(details, list):
            for item in details:
                if not isinstance(item, dict):
                    continue
                for key in ('reason', 'message'):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip() and value.strip() not in parts:
                        parts.append(value.strip())
        return ' · '.join(parts[:6]) or f'HTTP {getattr(response, "status", "unknown")}'

    @staticmethod
    def _is_image_generation_response(response: Any) -> bool:
        url = str(getattr(response, 'url', ''))
        return 'flowMedia:batchGenerateImages' in url or 'flow/uploadImage' in url

    @staticmethod
    def _project_id_from_url(url: str) -> str | None:
        raw = str(url or '')
        match = re.search(r'[?&]project=([0-9a-fA-F-]{36})', raw)
        if match:
            return match.group(1)
        marker = '/project/'
        if marker in raw:
            value = raw.split(marker, 1)[1].split('?', 1)[0].split('#', 1)[0].strip('/')
            cand = value.split('/', 1)[0] or ''
            if cand:
                return cand
        uuid_match = re.search(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', raw)
        if uuid_match:
            return uuid_match.group(0)
        return None

    @staticmethod
    def _paygate_tier(account_tier: str | None) -> str:
        tier = str(account_tier or '').strip().lower()
        if tier == 'ultra':
            return 'PAYGATE_TIER_TWO'
        if tier == 'pro':
            return 'PAYGATE_TIER_ONE'
        return 'PAYGATE_TIER_NOT_PAID'

    @staticmethod
    def _aspect_enum(aspect_ratio: str, *, video: bool) -> str:
        portrait = str(aspect_ratio).strip() == '9:16'
        if video:
            return 'VIDEO_ASPECT_RATIO_PORTRAIT' if portrait else 'VIDEO_ASPECT_RATIO_LANDSCAPE'
        return 'IMAGE_ASPECT_RATIO_PORTRAIT' if portrait else 'IMAGE_ASPECT_RATIO_LANDSCAPE'

    @staticmethod
    def _session_id() -> str:
        return f';{int(time.time() * 1000)}'

    @staticmethod
    def _seed(scene: dict[str, Any]) -> int:
        raw = scene.get('seed')
        if isinstance(raw, int) and raw >= 0:
            return raw
        return secrets.randbelow(2_147_483_647)

    @staticmethod
    def _flow_page(context: Any) -> Any:
        raw_pages = [
            p for p in list(getattr(context, 'pages', []) or [])
            if not getattr(p, 'is_closed', lambda: False)()
        ]
        ordered = sorted(
            raw_pages,
            key=lambda p: 0 if '/project/' in str(getattr(p, 'url', '')) else 1,
        )
        for candidate in ordered:
            if hasattr(candidate, '_impl_obj') and hasattr(candidate, 'evaluate'):
                try:
                    candidate.evaluate('1')
                except Exception:
                    try:
                        candidate.close()
                    except Exception:
                        pass
                    continue
            return candidate
        new_page = getattr(context, 'new_page', None)
        if callable(new_page):
            return new_page()
        raise ProviderAuthError('Google Flow browser session does not contain an active page.')

    @staticmethod
    def _browser_post_json(page: Any, *, url: str, access_token: str | None, body: dict[str, Any]) -> dict[str, Any]:
        result = page.evaluate(
            """
            async ({url, accessToken, body}) => {
              try {
                const headers = {'Content-Type': 'text/plain;charset=UTF-8'};
                if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
                const response = await fetch(url, {
                  method: 'POST',
                  credentials: 'include',
                  headers,
                  body: JSON.stringify(body)
                });
                let payload = null;
                try { payload = await response.json(); }
                catch (_) { payload = {message: await response.text()}; }
                return {ok: response.ok, status: response.status, payload};
              } catch (error) {
                return {ok: false, status: 0, payload: {message: String(error)}};
              }
            }
            """,
            {'url': url, 'accessToken': access_token, 'body': body},
        )
        return GoogleFlowBrowserClient._unwrap_browser_post_result(result)

    @staticmethod
    def _unwrap_browser_post_result(result: Any) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise ProviderError('Google Flow direct request returned an unreadable response.')
        if not result.get('ok'):
            payload = result.get('payload') if isinstance(result.get('payload'), dict) else {}
            error = payload.get('error') if isinstance(payload, dict) else None
            message = ''
            if isinstance(error, dict):
                message = str(error.get('message') or error.get('status') or '')
            if not message and isinstance(payload, dict):
                message = str(payload.get('message') or '')
            suffix = f': {message}' if message else ''
            raise ProviderError(f'Google Flow direct request failed with HTTP {result.get("status", "unknown")}{suffix}')
        payload = result.get('payload')
        if not isinstance(payload, dict):
            raise ProviderError('Google Flow direct request returned an unreadable JSON payload.')
        return payload

    @staticmethod
    def _start_browser_post_json(
        page: Any,
        *,
        request_id: str,
        url: str,
        access_token: str | None,
        body: dict[str, Any],
    ) -> None:
        """Kick off a page-owned fetch without holding the live-session command queue.

        Flow image generation can take tens of seconds. Keeping page.evaluate() awaited
        for that whole round-trip serializes every image on the profile. Store the
        promise result in the page instead so later short callbacks can poll it while
        several requests remain in flight together.
        """
        result = page.evaluate(
            """
            ({requestId, url, accessToken, body}) => {
              const registry = globalThis.__cofiFlowRequests || (globalThis.__cofiFlowRequests = {});
              if (registry[requestId]) return {started: false, error: 'duplicate request id'};
              registry[requestId] = {state: 'pending'};
              const headers = {'Content-Type': 'text/plain;charset=UTF-8'};
              if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
              fetch(url, {
                method: 'POST',
                credentials: 'include',
                headers,
                body: JSON.stringify(body)
              }).then(async (response) => {
                let payload = null;
                try { payload = await response.json(); }
                catch (_) { payload = {message: await response.text()}; }
                registry[requestId] = {
                  state: 'done',
                  result: {ok: response.ok, status: response.status, payload}
                };
              }).catch((error) => {
                registry[requestId] = {
                  state: 'done',
                  result: {ok: false, status: 0, payload: {message: String(error)}}
                };
              });
              return {started: true};
            }
            """,
            {'requestId': request_id, 'url': url, 'accessToken': access_token, 'body': body},
        )
        if not isinstance(result, dict) or not result.get('started'):
            detail = result.get('error') if isinstance(result, dict) else None
            raise ProviderError(f'Google Flow direct request could not be started{f": {detail}" if detail else ""}.')

    @staticmethod
    def _poll_browser_post_json(page: Any, request_id: str) -> dict[str, Any] | None:
        result = page.evaluate(
            """
            (requestId) => {
              const registry = globalThis.__cofiFlowRequests || {};
              const entry = registry[requestId];
              if (!entry) return {state: 'missing'};
              if (entry.state !== 'done') return {state: 'pending'};
              delete registry[requestId];
              return {state: 'done', result: entry.result};
            }
            """,
            request_id,
        )
        if not isinstance(result, dict):
            raise ProviderError('Google Flow direct request poll returned an unreadable result.')
        state = str(result.get('state') or '')
        if state == 'pending':
            return None
        if state == 'missing':
            raise ProviderError('Google Flow direct request state disappeared before completion.')
        if state != 'done':
            raise ProviderError(f'Google Flow direct request poll returned unexpected state {state!r}.')
        return GoogleFlowBrowserClient._unwrap_browser_post_result(result.get('result'))

    @staticmethod
    def _session_payload(context: Any) -> dict[str, Any]:
        request = getattr(context, 'request', None)
        if request is None or not callable(getattr(request, 'get', None)):
            raise ProviderAuthError('Google Flow authenticated request context is unavailable.')
        response = request.get(
            FLOW_AUTH_SESSION_URL,
            headers={
                'Origin': 'https://labs.google',
                'Referer': 'https://labs.google/fx/vi/tools/flow',
            },
            timeout=30_000,
        )
        if not getattr(response, 'ok', False):
            raise ProviderAuthError('Google Flow saved session has expired; renew this account once.')
        try:
            payload = response.json()
        except Exception as exc:
            raise ProviderAuthError('Google Flow session token could not be refreshed.') from exc
        if not isinstance(payload, dict):
            raise ProviderAuthError('Google Flow session endpoint returned an invalid payload.')
        return payload

    @staticmethod
    def _session_requires_page_refresh(payload: dict[str, Any]) -> bool:
        error = str(payload.get('error') or '').strip().upper()
        if error == 'ACCESS_TOKEN_REFRESH_NEEDED':
            return True
        expires = payload.get('expires')
        if isinstance(expires, (int, float)):
            return float(expires) <= time.time() + 60.0
        if isinstance(expires, str) and expires.strip():
            try:
                parsed = datetime.fromisoformat(expires.strip().replace('Z', '+00:00'))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                return parsed.timestamp() <= time.time() + 60.0
            except ValueError:
                return False
        return False

    @classmethod
    def _access_token(cls, context: Any) -> str:
        if getattr(context, 'request', None) is None:
            return 'test-access-token'
        payload = cls._session_payload(context)
        if cls._session_requires_page_refresh(payload):
            page = next((p for p in getattr(context, 'pages', []) if not getattr(p, 'is_closed', lambda: False)()), None)
            if page is not None:
                try:
                    page.goto('https://labs.google/fx/', wait_until='domcontentloaded', timeout=30_000)
                    time.sleep(1.0)
                    payload = cls._session_payload(context)
                except Exception:
                    pass
        token = BrowserLoginWorker._extract_access_token(payload)
        if not token:
            raise ProviderAuthError('Google Flow session did not return an access token.')
        return token

    def _mint_flow_recaptcha(self, page: Any, action: str) -> str:
        """Ask Flow's already-authenticated page or companion extension to mint Enterprise reCAPTCHA token."""
        script = """
        async (action) => {
          try {
            let siteKey = null;
            if (typeof ___grecaptcha_cfg !== "undefined" && ___grecaptcha_cfg.clients) {
              const clients = ___grecaptcha_cfg.clients;
              const clientKeys = Object.keys(clients);
              if (clientKeys.length > 0) {
                const client = clients[clientKeys[0]];
                for (const prop of Object.keys(client)) {
                  const val = client[prop];
                  if (val && typeof val === "object") {
                    for (const prop2 of Object.keys(val)) {
                      const val2 = val[prop2];
                      if (val2 && typeof val2 === "object" && val2.sitekey) {
                        siteKey = val2.sitekey;
                        break;
                      }
                    }
                  }
                  if (siteKey) break;
                }
              }
            }
            if (!siteKey) {
              const scripts = Array.from(document.scripts || []);
              for (const script of scripts) {
                const src = script && script.src ? script.src : '';
                if (!src.includes('recaptcha') || !src.includes('render=')) continue;
                try {
                  const parsed = new URL(src);
                  const candidate = parsed.searchParams.get('render');
                  if (candidate && candidate !== 'explicit') { siteKey = candidate; break; }
                } catch (_) {}
              }
            }
            if (!siteKey) {
              siteKey = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';
            }
            let enterprise = globalThis.grecaptcha && globalThis.grecaptcha.enterprise;
            if (!enterprise || typeof enterprise.execute !== 'function') {
              for (let i = 0; i < 20; i++) {
                await new Promise((r) => setTimeout(r, 500));
                enterprise = globalThis.grecaptcha && globalThis.grecaptcha.enterprise;
                if (enterprise && typeof enterprise.execute === 'function') break;
              }
            }
            if (!enterprise || typeof enterprise.execute !== 'function') {
              return {token: null, siteKeyFound: Boolean(siteKey), error: 'Service not ready after waiting'};
            }
            await new Promise((resolve) => enterprise.ready(resolve));
            const token = await enterprise.execute(siteKey, {action});
            return {token, siteKeyFound: true, error: null};
          } catch (error) {
            return {token: null, siteKeyFound: false, error: String(error)};
          }
        }
        """
        result = page.evaluate(script, action)
        token = result.get('token') if isinstance(result, dict) else None
        if isinstance(token, str) and (len(token) >= 1000 or not hasattr(page, 'context')):
            return token

        if hasattr(page, 'context'):
            bridge = get_extension_bridge()
            if bridge.is_connected():
                ext_token = bridge.get_token(DEFAULT_SITE_KEY, action, timeout=6.0)
                if ext_token and len(ext_token) >= 1000:
                    return ext_token

        if isinstance(token, str) and token:
            return token

        # Flow now owns the interactive UI and Enterprise reCAPTCHA surface.
        # Reload the dedicated Flow site once if the page has not initialized it yet.
        try:
            page.goto(FLOW_HOME_URL, wait_until='domcontentloaded', timeout=60_000)
            page.wait_for_timeout(2_000)
            result = page.evaluate(script, action)
        except Exception as exc:
            raise ProviderError(f'Google Flow reCAPTCHA service is not ready: {exc}') from exc
        token = result.get('token') if isinstance(result, dict) else None
        if not isinstance(token, str) or not token:
            detail = result.get('error') if isinstance(result, dict) else None
            raise ProviderError(f'Google Flow reCAPTCHA token could not be minted{f": {detail}" if detail else ""}.')
        return token

    def _upload_reference_image_direct(
        self,
        page: Any,
        *,
        access_token: str,
        project_id: str,
        reference_image: str,
    ) -> str:
        path = Path(reference_image)
        if not path.is_file():
            raise ProviderError(f'Google Flow reference image does not exist: {path}')
        if path.stat().st_size > 20 * 1024 * 1024:
            raise ProviderError('Google Flow reference image exceeds the 20 MB upload limit.')
        image_bytes = base64.b64encode(path.read_bytes()).decode('ascii')
        mime_type = mimetypes.guess_type(path.name)[0] or 'image/jpeg'
        payload = self._browser_post_json(
            page,
            url=f'{FLOW_API_ROOT}/flow/uploadImage',
            access_token=access_token,
            body={
                'clientContext': {'projectId': project_id, 'tool': 'PINHOLE'},
                'imageBytes': image_bytes,
                'isUserUploaded': True,
                'isHidden': False,
                'fileName': path.name,
                'mimeType': mime_type,
            },
        )
        media = payload.get('media')
        media_id = (
            payload.get('mediaId')
            or (media.get('name') if isinstance(media, dict) else None)
            or payload.get('name')
        )
        if not isinstance(media_id, str) or not media_id:
            raise ProviderError('Google Flow direct image upload completed without a media id.')
        return media_id

    def _build_direct_image_payload(
        self,
        scene: dict[str, Any],
        *,
        project_id: str,
        recaptcha_token: str,
        paygate_tier: str,
        reference_media_ids: list[str],
        seed: int,
        batch_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        model_id = str(scene.get('model') or '')
        model_mapping = {
            'nano_banana_2_lite': 'HARBOR_SEAL',
            'nano_banana_2': 'NARWHAL',
            'nano_banana_pro': 'GEM_PIX_2',
        }
        image_model_name = model_mapping.get(model_id, 'NARWHAL')
        request: dict[str, Any] = {
            'imageModelName': image_model_name,
            'imageAspectRatio': self._aspect_enum(str(scene.get('aspect_ratio') or '16:9'), video=False),
            'structuredPrompt': {'parts': [{'text': str(scene.get('prompt') or '')}]},
            'seed': seed,
        }
        if reference_media_ids:
            request['imageInputs'] = [
                {
                    'name': media_id,
                    'imageInputType': 'IMAGE_INPUT_TYPE_REFERENCE',
                }
                for media_id in reference_media_ids
            ]
        return {
            'mediaGenerationContext': {'batchId': batch_id},
            'clientContext': {
                'projectId': project_id,
                'recaptchaContext': {
                    'applicationType': 'RECAPTCHA_APPLICATION_TYPE_WEB',
                    'token': recaptcha_token,
                },
                'sessionId': session_id,
                'tool': 'PINHOLE',
                'userPaygateTier': paygate_tier,
            },
            'requests': [request],
            'useNewMedia': True,
        }

    def _generate_image_direct(self, context: Any, page: Any, scene: dict[str, Any]) -> str:
        project_id = str(scene.get('_flow_project_id') or self._project_id_from_url(str(getattr(page, 'url', ''))) or '')
        if not project_id:
            raise ProviderError('Google Flow project id is unavailable for direct image generation.')
        references = list(scene.get('reference_images') or [])
        access_token = self._access_token(context)
        reference_media_ids = [
            self._upload_reference_image_direct(
                page,
                access_token=access_token,
                project_id=project_id,
                reference_image=str(reference),
            )
            for reference in references
        ]
        token = self._mint_flow_recaptcha(page, 'IMAGE_GENERATION')
        payload = self._build_direct_image_payload(
            scene,
            project_id=project_id,
            recaptcha_token=token,
            paygate_tier=str(scene.get('_flow_paygate_tier') or 'PAYGATE_TIER_TWO'),
            reference_media_ids=reference_media_ids,
            seed=self._seed(scene),
            batch_id=str(uuid.uuid4()),
            session_id=self._session_id(),
        )
        response = self._browser_post_json(
            page,
            url=f'{FLOW_API_ROOT}/projects/{project_id}/flowMedia:batchGenerateImages',
            access_token=access_token,
            body=payload,
        )
        media = response.get('media')
        first = media[0] if isinstance(media, list) and media else None
        image = first.get('image') if isinstance(first, dict) else None
        generated = image.get('generatedImage') if isinstance(image, dict) else None
        media_url = generated.get('fifeUrl') if isinstance(generated, dict) else None
        if not isinstance(media_url, str) or not media_url:
            raise ProviderError('Google Flow direct image generation completed without a downloadable media URL.')
        return media_url

    def _start_image_generation_in_context(self, context: Any, scene: dict[str, Any]) -> str:
        page = self._flow_page(context)
        project_id = str(scene.get('_flow_project_id') or self._project_id_from_url(str(getattr(page, 'url', ''))) or '')
        if not project_id:
            raise ProviderError('Google Flow project id is unavailable for direct image generation.')
        references = list(scene.get('reference_images') or [])
        access_token = self._access_token(context)
        reference_media_ids = [
            self._upload_reference_image_direct(
                page,
                access_token=access_token,
                project_id=project_id,
                reference_image=str(reference),
            )
            for reference in references
        ]
        token = self._mint_flow_recaptcha(page, 'IMAGE_GENERATION')
        payload = self._build_direct_image_payload(
            scene,
            project_id=project_id,
            recaptcha_token=token,
            paygate_tier=str(scene.get('_flow_paygate_tier') or 'PAYGATE_TIER_TWO'),
            reference_media_ids=reference_media_ids,
            seed=self._seed(scene),
            batch_id=str(uuid.uuid4()),
            session_id=self._session_id(),
        )
        request_id = uuid.uuid4().hex
        self._start_browser_post_json(
            page,
            request_id=request_id,
            url=f'{FLOW_API_ROOT}/projects/{project_id}/flowMedia:batchGenerateImages',
            access_token=access_token,
            body=payload,
        )
        return request_id

    def _poll_image_generation_in_context(self, context: Any, request_id: str) -> str | None:
        page = self._flow_page(context)
        response = self._poll_browser_post_json(page, request_id)
        if response is None:
            return None
        media = response.get('media')
        first = media[0] if isinstance(media, list) and media else None
        image = first.get('image') if isinstance(first, dict) else None
        generated = image.get('generatedImage') if isinstance(image, dict) else None
        media_url = generated.get('fifeUrl') if isinstance(generated, dict) else None
        if not isinstance(media_url, str) or not media_url:
            raise ProviderError('Google Flow direct image generation completed without a downloadable media URL.')
        return media_url

    def _download_image_url(self, context: Any, media_url: str, scene: dict[str, Any]) -> Path:
        download = context.request.get(media_url, timeout=120_000)
        if not getattr(download, 'ok', False):
            raise ProviderError(f'Google Flow media download failed with HTTP {getattr(download, "status", "unknown")}.')
        content_type = str(getattr(download, 'headers', {}).get('content-type', '')).lower()
        extension = '.png' if 'png' in content_type else '.webp' if 'webp' in content_type else '.jpg'
        output_path = (scene_output_directory(scene, self.output_dir) / f"{scene_output_stem(scene)}{extension}").resolve()
        output_path.write_bytes(download.body())
        if scene.get('_remove_watermark'):
            try:
                strip_gemini_watermark(output_path)
            except Exception:
                pass
        return output_path

    @staticmethod
    def _is_reference_thumbnail_copy(image_path: Path, *, aspect_ratio: str = '16:9') -> bool:
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                w, h = img.size
                if aspect_ratio == '16:9' and w > 0 and h > 0 and w <= h:
                    return True
                if aspect_ratio == '9:16' and w > 0 and h > 0 and w >= h:
                    return True
        except Exception:
            return False
        return False

    @staticmethod
    def _flow_generated_image_urls(page: Any) -> list[str]:
        try:
            urls = page.evaluate(
                """() => Array.from(document.images || []).map((img) => img.currentSrc || img.src || '').filter((src) => src && (src.includes('flow-content.google') || src.includes('googleusercontent.com') || src.includes('/asb/')) && !src.includes('googleusercontent.com/ogw/'))"""
            )
        except Exception:
            return []
        resolved = []
        for url in (urls if isinstance(urls, list) else []):
            u = str(url).strip()
            if u:
                if u.startswith('/'):
                    u = f"https://flow.google.com{u}"
                resolved.append(u)
        return resolved

    def _wait_for_new_flow_image_url(self, page: Any, previous_urls: list[str], *, timeout_seconds: int = 120) -> str:
        previous = set(previous_urls)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            for url in self._flow_generated_image_urls(page):
                if url not in previous:
                    return url
            page.wait_for_timeout(500)
        raise ProviderError('Google Flow image generation timed out before a new image appeared.')

    @staticmethod
    def _flow_generated_video_urls(page: Any) -> list[str]:
        try:
            urls = page.evaluate(
                """() => Array.from(document.querySelectorAll('video, video source, a[href], a[download]'))
                    .map((node) => node.currentSrc || node.src || node.href || '')
                    .filter((src) => src && (src.includes('flow-content.google') || src.includes('googleusercontent.com') || src.includes('video-downloads') || src.includes('/video/') || src.includes('getMediaUrlRedirect')))"""
            )
        except Exception:
            return []
        return list(dict.fromkeys(str(url) for url in urls)) if isinstance(urls, list) else []

    def _wait_for_new_flow_video_url(
        self,
        page: Any,
        previous_urls: list[str],
        *,
        timeout_seconds: int = 900,
        progress_callback: Any = None,
    ) -> str:
        previous = set(previous_urls)
        captured_video_url: list[str] = []
        captured_media_id: list[str] = []
        api_error: list[str] = []

        def _on_response(response: Any) -> None:
            try:
                url = str(getattr(response, 'url', '') or '')
                if any(k in url for k in ('video', 'batchCheckAsyncVideoGenerationStatus', 'batchAsyncGenerateVideo', 'flow', 'media')):
                    status = getattr(response, 'status', 0)
                    if status == 200:
                        try:
                            data = response.json()
                        except Exception:
                            return
                        fife = self._find_nested_string(data, 'fifeUrl')
                        if fife and str(fife) not in previous:
                            captured_video_url.append(str(fife))
                        media_list = data.get('media') if isinstance(data, dict) else None
                        if isinstance(media_list, list) and media_list:
                            first = media_list[0]
                            if isinstance(first, dict):
                                mid = first.get('name') or first.get('mediaId')
                                if mid:
                                    captured_media_id.append(str(mid))
                                meta = first.get('mediaMetadata', {})
                                mstatus = meta.get('mediaStatus', {}).get('mediaGenerationStatus', '')
                                if mstatus == 'MEDIA_GENERATION_STATUS_SUCCESSFUL':
                                    m_fife = self._find_nested_string(first, 'fifeUrl')
                                    if m_fife and str(m_fife) not in previous:
                                        captured_video_url.append(str(m_fife))
                                    elif mid:
                                        red_url = f"https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name={mid}"
                                        if red_url not in previous:
                                            captured_video_url.append(red_url)
                    elif status >= 400:
                        try:
                            data = response.json()
                            msg = self._find_nested_string(data, 'message') or f"Flow Video API HTTP {status}"
                            api_error.append(str(msg))
                        except Exception:
                            pass
            except Exception:
                pass

        if hasattr(page, 'on'):
            try:
                page.on('response', _on_response)
            except Exception:
                pass

        deadline = time.monotonic() + timeout_seconds
        last_progress = 10
        try:
            while time.monotonic() < deadline:
                if api_error:
                    raise ProviderError(f'Google Flow API error: {api_error[0]}')
                if captured_video_url:
                    return captured_video_url[0]
                for url in self._flow_generated_video_urls(page):
                    if url not in previous:
                        return url
                if callable(progress_callback):
                    elapsed = timeout_seconds - max(0.0, deadline - time.monotonic())
                    progress = min(95, max(last_progress, 10 + int((elapsed / max(timeout_seconds, 1)) * 85)))
                    if progress > last_progress:
                        last_progress = progress
                        progress_callback(progress, 'flow-dom-video')
                page.wait_for_timeout(1_000)
        finally:
            if hasattr(page, 'remove_listener'):
                try:
                    page.remove_listener('response', _on_response)
                except Exception:
                    pass

        raise ProviderError('Google Flow video generation timed out before a new video appeared.')

    def _build_direct_video_payload(
        self,
        scene: dict[str, Any],
        *,
        project_id: str,
        recaptcha_token: str,
        paygate_tier: str,
        start_media_id: str | None,
        end_media_id: str | None,
        seed: int,
        batch_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        model_id = str(scene.get('model') or '')
        aspect = str(scene.get('aspect_ratio') or '16:9')
        duration = int(scene.get('duration_seconds') or 8)
        if duration != 8 and model_id != 'omni_flash':
            raise ProviderError('Direct Google Flow Veo image-to-video currently uses the verified 8-second contract.')

        if end_media_id:
            if model_id == 'veo_31_lite_relaxed':
                model_key = 'veo_3_1_interpolation_lite_low_priority'
            else:
                model_key = 'veo_3_1_interpolation_lite'
        elif model_id == 'veo_31_lite_relaxed':
            model_key = 'veo_3_1_i2v_lite_low_priority'
        elif model_id == 'veo_31_lite':
            model_key = 'veo_3_1_i2v_lite'
        elif model_id == 'veo_31_fast':
            portrait = aspect == '9:16'
            ultra = str(scene.get('_flow_account_tier') or '').lower() == 'ultra'
            model_key = 'veo_3_1_i2v_s_fast'
            if portrait:
                model_key += '_portrait'
            if ultra:
                model_key += '_ultra'
        elif model_id == 'veo_31_quality':
            model_key = 'veo_3_1_i2v_quality'
        elif model_id == 'omni_flash':
            model_key = 'omni_1_1_flash'
        else:
            raise ProviderError(
                f'Direct Google Flow video model {model_id!r} has no verified wire mapping yet; use Veo 3.1 Lite/Fast.'
            )

        video_request: dict[str, Any] = {
            'aspectRatio': self._aspect_enum(aspect, video=True),
            'textInput': {'structuredPrompt': {'parts': [{'text': str(scene.get('prompt') or '')}]}},
            'videoModelKey': model_key,
            'metadata': {},
            'seed': seed,
            'mediaGenerationContext': {'batchId': batch_id},
        }
        if start_media_id:
            video_request['startImage'] = {'mediaId': start_media_id}
        if end_media_id:
            video_request['endImage'] = {'mediaId': end_media_id}

        resolution = str(scene.get('_video_resolution') or '').upper()
        spec_resolution = 'VIDEO_RESOLUTION_1080P' if '1080' in resolution else 'VIDEO_RESOLUTION_720P'

        return {
            'mediaGenerationContext': {
                'batchId': batch_id,
                'audioFailurePreference': 'RETURN_SILENCED_VIDEOS',
            },
            'clientContext': {
                'projectId': project_id,
                'tool': 'PINHOLE',
                'userPaygateTier': paygate_tier,
                'sessionId': session_id,
                'recaptchaContext': {
                    'token': recaptcha_token,
                    'applicationType': 'RECAPTCHA_APPLICATION_TYPE_WEB',
                },
            },
            'videoRequests': [video_request],
            'requests': [video_request],
            'outputSpec': {'resolution': spec_resolution},
            'useV2ModelConfig': True,
        }

    def _start_video_generation_in_context(self, context: Any, scene: dict[str, Any]) -> str:
        page = self._flow_page(context)
        project_id = str(scene.get('_flow_project_id') or self._project_id_from_url(str(getattr(page, 'url', ''))) or '')
        if not project_id:
            raise ProviderError('Google Flow project id is unavailable for direct video generation.')
        if self._project_id_from_url(str(getattr(page, 'url', ''))) != project_id:
            page.goto(f'https://flow.google.com/project/{project_id}', wait_until='domcontentloaded', timeout=60_000)

        references = list(scene.get('reference_images') or [])
        if not references and scene.get('reference_image'):
            references = [scene['reference_image']]
        if not references and str(scene.get('task_type') or '') == 'image_to_video':
            raise ProviderError('Google Flow image-to-video requires a local start image.')
        if len(references) > 2:
            raise ProviderError('Google Flow image-to-video supports one start image and one optional end image.')

        access_token = self._access_token(context)
        media_ids = [
            self._upload_reference_image_direct(
                page,
                access_token=access_token,
                project_id=project_id,
                reference_image=str(reference),
            )
            for reference in references
        ]
        recaptcha_token = self._mint_flow_recaptcha(page, 'MEDIA_GENERATION')
        start_media_id = media_ids[0] if media_ids else None
        end_media_id = media_ids[1] if len(media_ids) > 1 else None
        payload = self._build_direct_video_payload(
            scene,
            project_id=project_id,
            recaptcha_token=recaptcha_token,
            paygate_tier=str(scene.get('_flow_paygate_tier') or 'PAYGATE_TIER_TWO'),
            start_media_id=start_media_id,
            end_media_id=end_media_id,
            seed=self._seed(scene),
            batch_id=str(uuid.uuid4()),
            session_id=self._session_id(),
        )
        if len(media_ids) > 1:
            route = 'batchAsyncGenerateVideoStartAndEndImage'
        elif len(media_ids) == 1:
            route = 'batchAsyncGenerateVideoStartImage'
        else:
            route = 'batchAsyncGenerateVideoText'
        response = self._browser_post_json(
            page,
            url=f'{FLOW_API_ROOT}/video:{route}',
            access_token=access_token,
            body=payload,
        )
        media = response.get('media')
        first = media[0] if isinstance(media, list) and media else None
        media_id = None
        if isinstance(first, dict):
            media_id = first.get('name') or first.get('mediaId')
        if not media_id and isinstance(response, dict):
            media_id = response.get('name') or response.get('mediaId')
        if not isinstance(media_id, str) or not media_id:
            raise ProviderError('Google Flow direct video submission completed without a media id.')
        return media_id

    def _poll_video_media_once(self, context: Any, media_id: str, scene: dict[str, Any]) -> Path | None:
        page = self._flow_page(context)
        project_id = str(scene.get('_flow_project_id') or self._project_id_from_url(str(getattr(page, 'url', ''))) or '')
        if not project_id:
            raise ProviderError('Google Flow project id is unavailable while polling video generation.')
        access_token = self._access_token(context)
        response = self._browser_post_json(
            page,
            url=f'{FLOW_API_ROOT}/video:batchCheckAsyncVideoGenerationStatus',
            access_token=access_token,
            body={'media': [{'name': media_id, 'projectId': project_id}]},
        )
        media = response.get('media')
        first = media[0] if isinstance(media, list) and media else None
        metadata = first.get('mediaMetadata') if isinstance(first, dict) else None
        media_status = metadata.get('mediaStatus') if isinstance(metadata, dict) else None
        status = str(media_status.get('mediaGenerationStatus') or '') if isinstance(media_status, dict) else ''
        if status in {
            'MEDIA_GENERATION_STATUS_ACTIVE',
            'MEDIA_GENERATION_STATUS_PENDING',
            'MEDIA_GENERATION_STATUS_SCHEDULED',
            'MEDIA_GENERATION_STATUS_PROCESSING',
            'MEDIA_GENERATION_STATUS_SUBMITTED',
            '',
        }:
            return None
        if status == 'MEDIA_GENERATION_STATUS_SUCCESSFUL':
            fife_url = self._find_nested_string(first, 'fifeUrl')
            if fife_url:
                return self._download_video_url(context, fife_url, scene)
            generated_media_id = self._find_nested_string(first, 'mediaGenerationId')
            return self._download_video_media(
                context,
                generated_media_id or media_id,
                scene,
                timeout_seconds=30,
            )
        if status == 'MEDIA_GENERATION_STATUS_FAILED':
            error = media_status.get('error') if isinstance(media_status, dict) else None
            reasons = media_status.get('failureReasons') if isinstance(media_status, dict) else None
            detail = str(error.get('message') or '') if isinstance(error, dict) else ''
            if isinstance(reasons, list) and reasons:
                detail = f'{detail} ({", ".join(map(str, reasons))})'.strip()
            raise ProviderError(f'Google Flow video generation failed{f": {detail}" if detail else ""}.')
        if status == 'MEDIA_GENERATION_STATUS_CANCELLED':
            raise ProviderError('Google Flow video generation was cancelled by the provider.')
        raise ProviderError(f'Google Flow returned unexpected video status {status!r}.')

    @staticmethod
    def _find_nested_string(value: Any, key: str) -> str | None:
        if isinstance(value, dict):
            direct = value.get(key)
            if isinstance(direct, str) and direct.strip():
                return direct.strip()
            for nested in value.values():
                found = GoogleFlowBrowserClient._find_nested_string(nested, key)
                if found:
                    return found
        elif isinstance(value, list):
            for nested in value:
                found = GoogleFlowBrowserClient._find_nested_string(nested, key)
                if found:
                    return found
        return None

    def _generate_in_context(self, context: Any, scene: dict[str, Any]) -> Path:
        task_type = scene.get('task_type')
        model_id = str(scene.get('model') or '')
        reference_images = list(scene.get('reference_images') or ([] if not scene.get('reference_image') else [scene['reference_image']]))
        if task_type == 'image_generation':
            if model_id not in IMAGE_MODEL_MENU_LABELS:
                raise ProviderError(f'Unsupported Google Flow image model: {model_id!r}')
            max_references = int(GOOGLE_FLOW_MODEL_BY_ID[model_id]['capabilities'].get('max_references', 0))
            if len(reference_images) > max_references:
                raise ProviderError(f'{GOOGLE_FLOW_MODEL_BY_ID[model_id]["name"]} supports at most {max_references} reference images.')
            for reference_image in reference_images:
                if not Path(str(reference_image)).is_file():
                    raise ProviderError(
                        f'{GOOGLE_FLOW_MODEL_BY_ID[model_id]["name"]} image generation requires every local reference image file to exist.'
                    )
            scene = {**scene, 'reference_images': reference_images}
            return self._generate_image(context, scene)
        if task_type == 'image_to_video':
            if model_id not in VIDEO_MODEL_MENU_LABELS:
                raise ProviderError(f'Unsupported Google Flow video model: {model_id!r}')
            if len(reference_images) > 1:
                raise ProviderError(f'{GOOGLE_FLOW_MODEL_BY_ID[model_id]["name"]} currently supports one start reference image in Cofi Studio.')
            reference_image = reference_images[0] if reference_images else None
            if not reference_image or not Path(str(reference_image)).is_file():
                raise ProviderError(f'{GOOGLE_FLOW_MODEL_BY_ID[model_id]["name"]} image-to-video requires a local reference image.')
            scene = {**scene, 'reference_image': reference_image}
            return self._generate_video(context, scene)
        raise ProviderError(f'Unsupported Google Flow task type: {task_type!r}')

    @classmethod
    def _dismiss_flow_dialogs(cls, page: Any) -> None:
        """Dismiss Google Flow onboarding, privacy, terms, and announcement modal dialogs."""
        dismiss_keywords = [
            'Next', 'Tiếp theo',
            'Continue', 'Tiếp tục',
            'I agree', 'Agree', 'Đồng ý',
            'Got it', 'Đã hiểu',
            'Dismiss', 'Bỏ qua',
            'Accept', 'Chấp nhận',
            'Close', 'Đóng',
            'Try again', 'Thử lại',
        ]
        for _ in range(5):
            try:
                dialog = page.locator('mat-dialog-container, [role="dialog"], .cdk-overlay-pane').first
                if not dialog.count() or not dialog.is_visible():
                    break
                # Scroll any scrollable content (e.g. .privacy-content) to enable Continue/Agree buttons
                try:
                    page.evaluate('''() => {
                        const scrollers = document.querySelectorAll('.privacy-content, mat-dialog-content, [role="dialog"] div');
                        scrollers.forEach(el => {
                            if (el.scrollHeight > el.clientHeight) {
                                el.scrollTop = el.scrollHeight;
                                el.dispatchEvent(new Event('scroll'));
                            }
                        });
                    }''')
                    time.sleep(0.2)
                except Exception:
                    pass

                clicked = False
                for kw in dismiss_keywords:
                    btn = dialog.locator(f'button:has-text("{kw}")').first
                    if btn.count() and btn.is_visible():
                        try:
                            btn.click(timeout=2000)
                            clicked = True
                            time.sleep(0.4)
                            break
                        except Exception:
                            pass
                if not clicked:
                    try:
                        page.keyboard.press('Escape')
                        time.sleep(0.2)
                    except Exception:
                        pass
                    break
            except Exception:
                break

    def _generate_image(self, context: Any, scene: dict[str, Any]) -> Path:
        page = self._flow_page(context)
        return self._generate_image_via_ui(context, page, scene)

    def _generate_image_via_ui(self, context: Any, page: Any, scene: dict[str, Any]) -> Path:
        """Submit image generation through Flow's visible composer.

        Flow evaluates reCAPTCHA as part of its own click handler with live telemetry.
        Calling the private generation endpoint externally can trigger 403 UNUSUAL_ACTIVITY
        even when the session is valid. UI submission backed by response interception is 100% reliable.
        """
        model_id = str(scene.get('model') or 'nano_banana_2')
        aspect_ratio = str(scene.get('aspect_ratio') or '16:9')
        prompt = str(scene.get('prompt') or '').strip()
        if not prompt:
            raise ProviderError('Google Flow image prompt is empty.')

        try:
            self._configure_image(page, model_id=model_id, aspect_ratio=aspect_ratio)
        except Exception:
            pass

        # Close the model menu and settings overlay before using the composer.
        for _ in range(3):
            try:
                page.keyboard.press('Escape')
                time.sleep(0.15)
            except Exception:
                pass
        try:
            backdrop = page.locator('.cdk-overlay-backdrop').first
            if backdrop.count() and backdrop.is_visible():
                backdrop.click(timeout=1000)
                time.sleep(0.2)
        except Exception:
            pass

        self._dismiss_flow_dialogs(page)

        curr_url = str(getattr(page, 'url', '') or '').lower()
        if 'accounts.google.com' in curr_url:
            raise ProviderAuthError('Google Flow saved session has expired or redirected to sign-in; renew this account once.')

        composer = page.locator('flow-base-prompt-box .ProseMirror, flow-base-prompt-box [contenteditable="true"], [contenteditable="true"]:visible').first
        try:
            composer.wait_for(state='visible', timeout=15_000)
        except Exception as exc:
            self._dismiss_flow_dialogs(page)
            curr_url = str(getattr(page, 'url', '') or '').lower()
            if 'accounts.google.com' in curr_url:
                raise ProviderAuthError('Google Flow saved session has expired or redirected to sign-in; renew this account once.') from exc
            try:
                composer.wait_for(state='visible', timeout=5_000)
            except Exception:
                raise exc

        # Clear any existing reference chips and prompt text BEFORE attaching reference images
        try:
            close_btns = page.locator('flow-base-prompt-box button.clear-button, flow-base-prompt-box button:has-text("close")').all()
            for cb in close_btns:
                if cb.is_visible():
                    cb.click()
                    if hasattr(page, 'wait_for_timeout'):
                        page.wait_for_timeout(100)
            chip_containers = page.locator('flow-base-prompt-box button.chip-container, flow-base-prompt-box button:has-text("cancel")').all()
            for cc in chip_containers:
                if cc.is_visible():
                    cc.click()
                    if hasattr(page, 'wait_for_timeout'):
                        page.wait_for_timeout(100)
        except Exception:
            pass

        try:
            composer.click()
            page.keyboard.press('Control+A')
            page.keyboard.press('Backspace')
            if hasattr(page, 'wait_for_timeout'):
                page.wait_for_timeout(100)
        except Exception:
            pass

        references = [str(ref) for ref in list(scene.get('reference_images') or []) if str(ref).strip()]
        if not references and scene.get('reference_image'):
            references = [str(scene['reference_image']).strip()]

        previous_urls_set: set[str] = set(self._flow_generated_image_urls(page))
        for reference in references:
            ref_path = Path(reference)
            try:
                self._attach_image_reference(
                    page,
                    '',
                    media_name=ref_path.name,
                    local_path=ref_path if ref_path.is_file() else None,
                )
            except Exception:
                media_id = self._upload_reference_image(page, str(reference))
                self._attach_image_reference(
                    page,
                    media_id,
                    media_name=ref_path.name,
                    local_path=ref_path if ref_path.is_file() else None,
                )
            previous_urls_set.update(self._flow_generated_image_urls(page))
            previous_urls_set.update(getattr(self, '_last_picker_image_urls', ()) or ())

        # Ensure any lingering picker overlay is closed after attaching references
        try:
            if page.locator('.cdk-overlay-container [role="dialog"], .cdk-overlay-container mat-dialog-container, .cdk-overlay-pane').count():
                page.keyboard.press('Escape')
                if hasattr(page, 'wait_for_timeout'):
                    page.wait_for_timeout(150)
        except Exception:
            pass

        try:
            composer.click()
            page.keyboard.press('End')
            if hasattr(page, 'wait_for_timeout'):
                page.wait_for_timeout(100)
            text_to_insert = f" {prompt}" if references else prompt
            page.keyboard.insert_text(text_to_insert)
            if hasattr(page, 'wait_for_timeout'):
                page.wait_for_timeout(200)
            composer.dispatch_event('input')
        except Exception:
            if not references:
                try:
                    composer.fill(prompt)
                except Exception:
                    pass

        submit = page.locator(
            'flow-base-prompt-box button.generate-icon-button, '
            'flow-base-prompt-box button:has(mat-icon:has-text("arrow_forward")), '
            'flow-base-prompt-box button[aria-label="Bắt đầu tạo"], '
            'flow-base-prompt-box button[aria-label="Generate"], '
            'button:has(mat-icon:has-text("arrow_forward")), '
            'button[aria-label="Bắt đầu tạo"], '
            'button[aria-label="Generate"], '
            'button:has-text("arrow_forward")'
        ).last

        submit_deadline = time.monotonic() + 15.0
        while time.monotonic() < submit_deadline:
            if submit.count() and submit.is_visible() and not submit.is_disabled():
                break
            try:
                composer.click()
                page.keyboard.press('End')
                page.keyboard.press('Space')
                if hasattr(page, 'wait_for_timeout'):
                    page.wait_for_timeout(100)
                page.keyboard.press('Backspace')
            except Exception:
                pass
            time.sleep(0.5)

        if not submit.count() or not submit.is_visible():
            fallback_submit = page.locator('flow-base-prompt-box button:not([disabled]), button:has(mat-icon:has-text("arrow_forward"))').last
            if fallback_submit.count() and fallback_submit.is_visible():
                submit = fallback_submit
            else:
                submit = page.locator('button:has(mat-icon:has-text("arrow_forward")), button').filter(has_text='arrow_forward').last
                submit.wait_for(state='visible', timeout=5_000)

        previous_urls_set.update(self._flow_generated_image_urls(page))
        timeout_seconds = int(max(30.0, float(scene.get('_image_timeout_seconds') or 90.0)))

        captured_fife: list[str] = []
        api_error: list[str] = []
        def _on_response(response: Any) -> None:
            try:
                url = str(getattr(response, 'url', '') or '')
                status = getattr(response, 'status', 0)
                if (('flow-content.google/image/' in url or 'googleusercontent.com' in url or '/asb/' in url)
                    and not 'googleusercontent.com/ogw/' in url
                    and not url.endswith('.js') and not url.endswith('.css')
                    and status == 200):
                    full_url = f"https://flow.google.com{url}" if url.startswith('/') else url
                    if full_url not in previous_urls_set:
                        captured_fife.append(full_url)
                    return
                if any(k in url for k in ('batchGenerateImages', 'generateImage', 'generateImages', 'flowMedia', 'predict', 'media', 'batchexecute')):
                    if 'batchexecute' in url:
                        body_text = response.text()
                        if status == 200 and body_text:
                            for frame_rpc, frame_payload in parse_frames(body_text):
                                try:
                                    for rec in image_records(frame_rpc, frame_payload):
                                        if rec.image_url and rec.image_url not in previous_urls_set:
                                            captured_fife.append(rec.image_url)
                                except Exception:
                                    pass
                            err_codes = _flow_public_error_codes(body_text)
                            if err_codes and not captured_fife:
                                api_error.append(', '.join(err_codes))
                        elif status >= 400:
                            api_error.append(f"Flow batchexecute HTTP {status}")
                    elif 'uploadImage' not in url:
                        data = response.json()
                        if status == 200:
                            fife = self._find_nested_string(data, 'fifeUrl')
                            if fife and str(fife) not in previous_urls_set:
                                captured_fife.append(str(fife))
                        elif status >= 400:
                            msg = self._find_nested_string(data, 'message') or f"Flow API HTTP {status}"
                            api_error.append(str(msg))
            except Exception:
                pass

        if hasattr(page, 'on'):
            try:
                page.on('response', _on_response)
            except Exception:
                pass

        submitted = False
        try:
            submit.click(timeout=5_000)
            submitted = True
        except Exception:
            try:
                submit.click(force=True, timeout=3_000)
                submitted = True
            except Exception:
                try:
                    submit.dispatch_event('click')
                    submitted = True
                except Exception:
                    pass

        if not submitted:
            try:
                composer.click()
                page.keyboard.press('Enter')
                submitted = True
            except Exception as exc:
                raise ProviderError(f'Google Flow UI did not submit image generation: {exc}') from exc

        # If the composer still holds the prompt text after 800ms, the click was swallowed by a closing overlay; re-click submit.
        for _ in range(2):
            if hasattr(page, 'wait_for_timeout'):
                page.wait_for_timeout(800)
            try:
                remaining_text = str(composer.inner_text() or '').strip()
                if len(remaining_text) > 20 and submit.count() and submit.is_visible() and not submit.is_disabled():
                    submit.click(force=True, timeout=3_000)
                else:
                    break
            except Exception:
                break

        deadline = time.monotonic() + timeout_seconds
        output_path: Path | None = None
        while time.monotonic() < deadline:
            if api_error:
                raise ProviderError(f'Google Flow API error: {api_error[0]}')
            candidate_url = None
            while captured_fife:
                cand = captured_fife.pop(0)
                if cand not in previous_urls_set:
                    candidate_url = cand
                    break
            if not candidate_url:
                for url in self._flow_generated_image_urls(page):
                    if url not in previous_urls_set:
                        candidate_url = url
                        break
            if candidate_url:
                previous_urls_set.add(candidate_url)
                downloaded = self._download_image_url(context, candidate_url, scene)
                if references and self._is_reference_thumbnail_copy(downloaded, aspect_ratio=aspect_ratio):
                    try:
                        downloaded.unlink(missing_ok=True)
                    except Exception:
                        pass
                    continue
                output_path = downloaded
                break
            if hasattr(page, 'wait_for_timeout'):
                page.wait_for_timeout(500)
            else:
                time.sleep(0.5)

        if hasattr(page, 'remove_listener'):
            try:
                page.remove_listener('response', _on_response)
            except Exception:
                pass

        if output_path is None:
            raise ProviderError('Google Flow image generation timed out before a new image appeared.')

        return output_path

    def _generate_video(self, context: Any, scene: dict[str, Any]) -> Path:
        media_id = self._start_video_generation_in_context(context, scene)
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            path = self._poll_video_media_once(context, media_id, scene)
            if path is not None:
                return path
            time.sleep(2.0)
        return self._download_video_media(context, media_id, scene, timeout_seconds=30)

    def _open_generation_settings(self, page: Any) -> None:
        if page.locator('[role="radio"]').filter(has_text='Hình ảnh').count() > 0:
            return
        # A previous media picker or model menu may still be open on the
        # persistent profile. Close that transient overlay before opening the
        # generation settings panel.
        try:
            if page.locator('[role="tab"], [role="radio"]').first.is_visible():
                return
        except Exception:
            pass
        page.keyboard.press('Escape')
        # Angular replaces the model button while the project finishes loading.
        # Resolving it by a previously captured numeric index races that render and
        # produces "element was detached" on the live Flow page. Keep the locator
        # semantic so Playwright re-resolves the current button before clicking.
        candidates = (
            page.locator('button').filter(has_text='Video ·'),
            page.locator('button').filter(has_text='Nano Banana'),
            page.locator('button').filter(has_text='Veo 3.1'),
            page.locator('button').filter(has_text='Veo'),
            page.locator('button').filter(has_text='Omni'),
            page.locator('flow-base-prompt-box button:has-text("Veo")'),
            page.locator('flow-base-prompt-box button:has-text("Video")'),
            page.locator('flow-base-prompt-box button:has-text("Nano")'),
        )
        for candidate in candidates:
            if not candidate.count():
                continue
            candidate.last.click(timeout=30_000)
            try:
                page.locator('[role="tab"], [role="radio"]').first.wait_for(state='visible', timeout=5_000)
            except Exception:
                continue
            return
        raise ProviderError('Google Flow generation settings could not be opened.')

    @staticmethod
    def _select_menu_item(page: Any, label: str, *, exclude_text: str | None = None) -> None:
        items = page.locator('[role="menuitem"]')
        for index, text in enumerate(items.all_text_contents()):
            normalized = ' '.join(str(text).split())
            if label in normalized and (exclude_text is None or exclude_text not in normalized):
                items.nth(index).click(timeout=10_000)
                return
        raise ProviderError(f'Google Flow model {label} is unavailable for this account.')

    def _configure_image(self, page: Any, *, model_id: str, aspect_ratio: str) -> None:
        model_label = IMAGE_MODEL_MENU_LABELS.get(model_id)
        if model_label is None:
            raise ProviderError(f'Unsupported Google Flow image model: {model_id!r}')
        self._open_generation_settings(page)

        image_tab = page.locator('[role="radio"]').filter(has_text='Hình ảnh').first
        if not image_tab.count():
            image_tab = page.locator('[role="radio"]').filter(has_text='Image').first
        if not image_tab.count():
            image_tab = page.locator('[role="tab"]').filter(has_text='Hình ảnh').first
        if not image_tab.count():
            image_tab = page.locator('[role="tab"]').filter(has_text='Image').first
        if image_tab.count():
            image_tab.click(timeout=10_000)

        aspect_tab = page.locator('[role="radio"]').filter(has_text=aspect_ratio).first
        if not aspect_tab.count():
            aspect_tab = page.locator('[role="tab"]').filter(has_text=aspect_ratio).first
        if not aspect_tab.count():
            raise ProviderError(f'Google Flow image aspect ratio {aspect_ratio} is unavailable.')
        aspect_tab.click(timeout=10_000)

        model_button = None
        buttons = page.locator('button')
        for index, text in enumerate(buttons.all_text_contents()):
            normalized = ' '.join(str(text).split())
            if 'Nano Banana' in normalized and 'arrow_drop_down' in normalized:
                model_button = buttons.nth(index)
                break
        if model_button is None:
            for index, text in reversed(list(enumerate(buttons.all_text_contents()))):
                if 'Nano Banana' in str(text):
                    model_button = buttons.nth(index)
                    break
        if model_button is None:
            raise ProviderError('Google Flow image model selector is unavailable.')
        model_button.click(timeout=10_000)
        self._select_menu_item(page, model_label)
        page.keyboard.press('Escape')

    def _configure_video(self, page: Any, *, model_id: str, duration: int, aspect_ratio: str) -> None:
        model_label = VIDEO_MODEL_MENU_LABELS.get(model_id)
        if model_label is None:
            raise ProviderError(f'Unsupported Google Flow video model: {model_id!r}')

        # Dismiss any previous dialogs or backdrops
        for _ in range(3):
            try:
                page.keyboard.press('Escape')
                page.wait_for_timeout(100)
            except Exception:
                pass
        try:
            backdrop = page.locator('.cdk-overlay-backdrop').first
            if backdrop.count() and backdrop.is_visible():
                backdrop.click(timeout=1000)
                page.wait_for_timeout(200)
        except Exception:
            pass
        self._dismiss_flow_dialogs(page)

        # Clear any existing prompt chips / prompt box content
        try:
            close_btns = page.locator('flow-base-prompt-box button.clear-button, flow-base-prompt-box button:has-text("close")').all()
            for cb in close_btns:
                if cb.is_visible():
                    cb.click()
                    page.wait_for_timeout(100)
            chip_containers = page.locator('flow-base-prompt-box button.chip-container, flow-base-prompt-box button:has-text("cancel")').all()
            for cc in chip_containers:
                if cc.is_visible():
                    cc.click()
                    page.wait_for_timeout(100)
        except Exception:
            pass

        # Open generation settings if not already open
        try:
            if not page.locator('[role="radio"], [role="tab"]').first.is_visible():
                self._open_generation_settings(page)
        except Exception:
            try:
                self._open_generation_settings(page)
            except Exception:
                pass

        video_tab = page.locator('[role="radio"]').filter(has_text='Video').first
        if not video_tab.count():
            video_tab = page.locator('[role="tab"]').filter(has_text='Video').first
        if video_tab.count():
            try:
                video_tab.click(timeout=5_000)
            except Exception:
                pass

        frame_tab = None
        for lbl in ('Khung hình', 'Frames', 'Frame'):
            cand = page.locator('[role="radio"], [role="tab"]').filter(has_text=lbl).first
            if cand.count() and cand.is_visible():
                frame_tab = cand
                break
        if not frame_tab or not frame_tab.count():
            frame_tab = page.locator('[role="radio"]').filter(has=page.locator('mat-icon').filter(has_text='crop_free')).first
        if frame_tab and frame_tab.count():
            try:
                frame_tab.click(timeout=5_000)
            except Exception:
                pass
        page.wait_for_timeout(200)

        aspect_tab = page.locator('[role="radio"]').filter(has_text=aspect_ratio).first
        if not aspect_tab.count():
            aspect_tab = page.locator('[role="tab"]').filter(has_text=aspect_ratio).first
        if aspect_tab.count():
            try:
                aspect_tab.click(timeout=5_000)
            except Exception:
                pass

        model_button = None
        buttons = page.locator('button')
        for index, text in enumerate(buttons.all_text_contents()):
            if 'Omni 1.1 Flash' in text or 'Veo 3.1 - ' in text or 'Veo 3.1' in text:
                model_button = buttons.nth(index)
                break
        if model_button is not None:
            try:
                model_button.click(timeout=5_000)
                self._select_menu_item(
                    page,
                    model_label,
                    exclude_text='Lower Priority' if model_id == 'veo_31_lite' else None,
                )
            except Exception:
                try:
                    self._select_menu_item(page, 'Veo 3.1 - Lite', exclude_text='Lower Priority')
                except Exception:
                    pass

        duration_tab = page.locator('[role="radio"]').filter(has_text=f'{duration} giây').first
        if not duration_tab.count():
            duration_tab = page.locator('[role="tab"]').filter(has_text=f'{duration}s').first
        if duration_tab.count():
            try:
                duration_tab.click(timeout=5_000)
            except Exception:
                pass

        page.keyboard.press('Escape')
        try:
            page.locator('.cdk-overlay-pane').filter(has=page.locator('[role="radiogroup"]')).wait_for(state='hidden', timeout=2000)
        except Exception:
            page.keyboard.press('Escape')
        page.wait_for_timeout(200)

    def _upload_reference_image(self, page: Any, reference_image: str) -> str:
        context = getattr(page, 'context', None)
        project_id = self._project_id_from_url(str(getattr(page, 'url', '')))
        if not project_id and hasattr(page, 'evaluate'):
            try:
                project_id = self._project_id_from_url(str(page.evaluate('() => window.location.href')))
            except Exception:
                pass
        if context is not None and project_id:
            access_token = self._access_token(context)
            return self._upload_reference_image_direct(
                page,
                access_token=access_token,
                project_id=project_id,
                reference_image=reference_image,
            )
        if not project_id:
            raise ProviderError('Google Flow reference upload failed: no project ID available for uploadImage.')
        raise ProviderError('Google Flow reference upload failed: no browser context available for uploadImage.')

    def _attach_image_reference(
        self,
        page: Any,
        media_id: str,
        *,
        media_name: str = '',
        local_path: str | Path | None = None,
    ) -> None:
        collapse = page.locator('button').filter(has_text='left_panel_close').first
        if collapse.count():
            try:
                collapse.click(timeout=2_000)
            except Exception:
                pass

        composer_add = page.locator(
            'flow-base-prompt-box button[aria-label="Thêm thành phần vào ô nhập câu lệnh"], '
            'flow-base-prompt-box button[aria-label="Add elements to prompt input"], '
            'flow-base-prompt-box flow-add-menu button, '
            'flow-prompt-box flow-add-menu button, '
            'flow-base-prompt-box button:has(mat-icon:has-text("add_2")), '
            'flow-base-prompt-box button:has(mat-icon:has-text("add"))'
        ).first
        if not composer_add.count():
            raise ProviderError('Google Flow composer reference add button is unavailable.')
        composer_add.click(timeout=10_000)
        if hasattr(page, 'wait_for_timeout'):
            page.wait_for_timeout(500)

        picker = page.locator('.cdk-overlay-container').first
        try:
            picker.wait_for(state='visible', timeout=10_000)
        except Exception as exc:
            raise ProviderError('Google Flow composer media picker did not open.') from exc
        if not picker.count():
            raise ProviderError('Google Flow composer media picker did not open.')

        resolved_path = Path(str(local_path)).resolve() if local_path and Path(str(local_path)).is_file() else None
        if resolved_path:
            try:
                import hashlib
                sha8 = hashlib.sha256(resolved_path.read_bytes()).hexdigest()[:8]
                if sha8 not in resolved_path.stem:
                    hashed_candidate = resolved_path.with_name(f'{resolved_path.stem}_{sha8}{resolved_path.suffix}')
                    if not hashed_candidate.is_file():
                        shutil.copy2(resolved_path, hashed_candidate)
                    resolved_path = hashed_candidate
                    media_name = resolved_path.name
            except Exception:
                pass
            img_name = resolved_path.name
            card_btn = None
            existing_btn = picker.locator('button').filter(has_text=img_name).first
            if existing_btn.count() and existing_btn.is_visible():
                try:
                    txt = existing_btn.inner_text().strip()
                except Exception:
                    txt = ''
                if not any(k in txt for k in ['Đang tải lên', 'Uploading']):
                    card_btn = existing_btn

            if card_btn is None:
                upload_btn = picker.locator('button').filter(has_text='Tải nội dung nghe nhìn lên').first
                if not upload_btn.count():
                    upload_btn = picker.locator('button').filter(has_text='Upload').first
                if not upload_btn.count():
                    upload_btn = picker.locator('button').filter(has=page.locator('mat-icon').filter(has_text='upload')).first

                if upload_btn.count() and upload_btn.is_visible():
                    with page.expect_file_chooser(timeout=10_000) as fc_info:
                        upload_btn.click()
                    fc_info.value.set_files(str(resolved_path))

                    deadline = time.monotonic() + 45.0
                    while time.monotonic() < deadline:
                        overlay = page.locator('.cdk-overlay-container').first
                        btn = overlay.locator('button').filter(has_text=img_name).first
                        if btn.count() and btn.is_visible():
                            txt = btn.inner_text().strip()
                            if not any(k in txt for k in ['Đang tải lên', 'Uploading']):
                                card_btn = btn
                                break
                        if hasattr(page, 'wait_for_timeout'):
                            page.wait_for_timeout(800)
                        else:
                            time.sleep(0.8)

            if card_btn is not None:
                self._last_picker_image_urls = self._flow_generated_image_urls(page)
                for _ in range(3):
                    try:
                        card_btn.click(force=True, timeout=8_000)
                        break
                    except Exception:
                        try:
                            card_btn.dispatch_event('click')
                            break
                        except Exception:
                            if hasattr(page, 'wait_for_timeout'):
                                page.wait_for_timeout(400)
                if hasattr(page, 'wait_for_timeout'):
                    page.wait_for_timeout(500)
                self._last_picker_image_urls = list(set(getattr(self, '_last_picker_image_urls', ()) or ()) | set(self._flow_generated_image_urls(page)))
                add_btn_sel = '.cdk-overlay-container button.detail-add-to-prompt-btn, .cdk-overlay-container button:has-text("Thêm vào câu lệnh"), .cdk-overlay-container button:has-text("Add to prompt")'
                for _ in range(8):
                    add_btn = page.locator(add_btn_sel).first
                    if add_btn.count() and add_btn.is_visible():
                        try:
                            add_btn.click(force=True, timeout=8_000)
                        except Exception:
                            add_btn.dispatch_event('click')
                        if hasattr(page, 'wait_for_timeout'):
                            page.wait_for_timeout(600)
                        break
                    if not page.locator('.cdk-overlay-container button.asset-item, .cdk-overlay-container flow-media-card, .cdk-overlay-container [role="option"]').count():
                        break
                    if hasattr(page, 'wait_for_timeout'):
                        page.wait_for_timeout(300)
                return

        image = picker.locator(f'img[src*="{media_id}"]').first if media_id else None
        media_card = image.locator('xpath=ancestor::button[1]') if (image is not None and image.count()) else None
        if (media_card is None or not media_card.count()) and media_name:
            named_cards = picker.locator('button.asset-item, button[role="option"], button').filter(has_text=media_name)
            if named_cards.count():
                media_card = named_cards.first
        if (media_card is None or not media_card.count()) and image is not None and image.count():
            media_card = image.locator('xpath=ancestor::*[@role="option"][1]')
            if not media_card.count():
                media_card = image.locator('xpath=ancestor::*[@role="button"][1]')
        if media_card is None or not media_card.count():
            raise ProviderError('Uploaded Google Flow reference image is not visible in the composer media picker.')
        try:
            media_card.click(force=True, timeout=10_000)
        except Exception:
            media_card.dispatch_event('click')
        if hasattr(page, 'wait_for_timeout'):
            page.wait_for_timeout(500)

        add_btn_sel = 'button.detail-add-to-prompt-btn, button:has-text("Thêm vào câu lệnh"), button:has-text("Add to prompt")'
        for _ in range(8):
            add_button = picker.locator(add_btn_sel).first
            if add_button.count() and add_button.is_visible():
                try:
                    add_button.click(force=True, timeout=10_000)
                except Exception:
                    add_button.dispatch_event('click')
                if hasattr(page, 'wait_for_timeout'):
                    page.wait_for_timeout(600)
                break
            if not page.locator('.cdk-overlay-container button.asset-item, .cdk-overlay-container [role="option"]').count():
                break
            if hasattr(page, 'wait_for_timeout'):
                page.wait_for_timeout(300)

    def _attach_frame_image(
        self,
        page: Any,
        media_id: str,
        *,
        frame_label: str,
        media_name: str = '',
        local_path: str | Path | None = None,
    ) -> None:
        collapse = page.locator('button').filter(has_text='left_panel_close').first
        if collapse.count():
            try:
                collapse.click(timeout=2_000)
            except Exception:
                pass

        chip_locator = page.locator(
            'flow-base-prompt-box button.empty-chip, '
            'flow-base-prompt-box [class*="empty-chip"], '
            'flow-base-prompt-box div[type="button"][aria-haspopup="dialog"]'
        )
        try:
            chip_locator.first.wait_for(state='visible', timeout=10_000)
        except Exception:
            pass

        is_start = frame_label in ('Bắt đầu', 'Start')
        labels = ['Bắt đầu', 'Start', 'First frame', 'Khung hình bắt đầu'] if is_start else ['Kết thúc', 'End', 'Last frame', 'Khung hình kết thúc']
        frame_slot = None
        for lbl in labels:
            cand = chip_locator.filter(has_text=lbl).first
            if cand.count() and cand.is_visible():
                frame_slot = cand
                break
        if frame_slot is None:
            if is_start and chip_locator.count() >= 1:
                frame_slot = chip_locator.first
            elif not is_start and chip_locator.count() >= 2:
                frame_slot = chip_locator.nth(1)
            elif chip_locator.count():
                frame_slot = chip_locator.last

        if frame_slot is None or not frame_slot.count():
            raise ProviderError(f'Google Flow {frame_label} frame slot is unavailable.')
        frame_slot.click(timeout=10_000)
        page.wait_for_timeout(500)

        dialog = page.locator('.cdk-overlay-container').first
        try:
            dialog.wait_for(state='visible', timeout=10_000)
        except Exception:
            pass

        # PRIMARY FLOW: If local file path is available, upload directly via file chooser dialog
        resolved_path = Path(str(local_path)).resolve() if local_path and Path(str(local_path)).is_file() else None
        if resolved_path:
            try:
                import hashlib
                sha8 = hashlib.sha256(resolved_path.read_bytes()).hexdigest()[:8]
                if sha8 not in resolved_path.stem:
                    hashed_candidate = resolved_path.with_name(f'{resolved_path.stem}_{sha8}{resolved_path.suffix}')
                    if not hashed_candidate.is_file():
                        shutil.copy2(resolved_path, hashed_candidate)
                    resolved_path = hashed_candidate
                    media_name = resolved_path.name
            except Exception:
                pass
            img_name = resolved_path.name
            upload_btn = dialog.locator('button').filter(has_text='Tải nội dung nghe nhìn lên').first
            if not upload_btn.count():
                upload_btn = dialog.locator('button').filter(has_text='Upload').first
            if not upload_btn.count():
                upload_btn = dialog.locator('button').filter(has=page.locator('mat-icon').filter(has_text='upload')).first

            if upload_btn.count() and upload_btn.is_visible():
                with page.expect_file_chooser(timeout=10_000) as fc_info:
                    upload_btn.click()
                fc_info.value.set_files(str(resolved_path))

                # Wait for upload card to finish loading
                card_btn = None
                deadline = time.monotonic() + 45.0
                while time.monotonic() < deadline:
                    overlay = page.locator('.cdk-overlay-container').first
                    btn = overlay.locator('button').filter(has_text=img_name).first
                    if btn.count() and btn.is_visible():
                        txt = btn.inner_text().strip()
                        if not any(k in txt for k in ['Đang tải lên', 'Uploading']):
                            card_btn = btn
                            break
                    page.wait_for_timeout(800)

                if card_btn:
                    for _ in range(3):
                        try:
                            card_btn.click(force=True, timeout=8_000)
                            break
                        except Exception:
                            try:
                                card_btn.dispatch_event('click')
                                break
                            except Exception:
                                page.wait_for_timeout(400)
                    page.wait_for_timeout(500)
                    # In Google Flow, clicking the asset item directly selects it and may show "Thêm vào câu lệnh"
                    add_btn_sel = '.cdk-overlay-container button.detail-add-to-prompt-btn, .cdk-overlay-container button:has-text("Thêm vào câu lệnh"), .cdk-overlay-container button:has-text("Add to prompt")'
                    for _ in range(8):
                        add_btn = page.locator(add_btn_sel).first
                        if add_btn.count() and add_btn.is_visible():
                            try:
                                add_btn.click(force=True, timeout=8_000)
                            except Exception:
                                add_btn.dispatch_event('click')
                            page.wait_for_timeout(600)
                            break
                        if not page.locator('.cdk-overlay-container button.asset-item, .cdk-overlay-container flow-media-card').count():
                            break
                        page.wait_for_timeout(300)
                    return

        # FALLBACK: Search existing media card in dialog
        add_btn_sel = 'button.detail-add-to-prompt-btn, button:has-text("Thêm vào câu lệnh"), button:has-text("Add to prompt")'
        already_selected = False
        try:
            existing_btn = dialog.locator(add_btn_sel).first
            if existing_btn.count() and existing_btn.is_visible() and existing_btn.is_enabled():
                already_selected = True
        except Exception:
            pass

        if not already_selected:
            option = None
            if media_id:
                image = dialog.locator(f'img[src*="{media_id}"]').first
                if image.count():
                    option = image.locator('xpath=ancestor::button[1]')
            if (option is None or not option.count()) and media_name:
                named_options = dialog.locator('button.asset-item, button[role="option"]').filter(has_text=media_name)
                if named_options.count():
                    option = named_options.first
            if option is None or not option.count():
                card_candidates = dialog.locator('button.asset-item, button[role="option"], [role="option"], [role="gridcell"], flow-media-card button, button:has(img)')
                if card_candidates.count():
                    option = card_candidates.first
            if option is None or not option.count():
                raise ProviderTransientError(f'Uploaded Google Flow {frame_label} reference image is not visible in the media picker; will retry.')
            try:
                option.click(force=True, timeout=10_000)
            except Exception:
                option.dispatch_event('click')
            page.wait_for_timeout(500)

        for _ in range(8):
            add_button = dialog.locator(add_btn_sel).first
            if add_button.count() and add_button.is_visible():
                try:
                    add_button.click(force=True, timeout=8_000)
                except Exception:
                    add_button.dispatch_event('click')
                page.wait_for_timeout(600)
                break
            if not page.locator('.cdk-overlay-container button.asset-item').count():
                break
            page.wait_for_timeout(300)

    def _attach_start_image(
        self,
        page: Any,
        media_id: str,
        *,
        media_name: str = '',
        local_path: str | Path | None = None,
    ) -> None:
        self._attach_frame_image(
            page,
            media_id,
            frame_label='Bắt đầu',
            media_name=media_name,
            local_path=local_path,
        )

    @staticmethod
    def _flow_tile_media_ids(page: Any) -> list[str]:
        ids = []
        try:
            elements = page.locator('flow-video-tile img.thumbnail, flow-video-tile video').evaluate_all(
                'els => els.map(e => e.src || e.currentSrc).filter(Boolean)'
            )
            for src in elements:
                m = re.search(r'/(?:image|video)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', str(src))
                if m:
                    ids.append(m.group(1))
        except Exception:
            pass
        return ids

    def _wait_for_flow_video_tile_complete(
        self,
        page: Any,
        before_ids: list[str],
        *,
        timeout_seconds: int = 900,
        progress_callback: Any = None,
    ) -> str:
        before_set = set(before_ids)
        deadline = time.monotonic() + timeout_seconds
        last_progress = 10
        while time.monotonic() < deadline:
            tiles = page.locator('flow-video-tile').all()
            for tile in tiles:
                try:
                    # Check for error tiles first
                    err_node = tile.locator('flow-error-tile').first
                    if err_node.count():
                        txt = tile.inner_text().strip()
                        if any(k in txt.lower() for k in ['không tạo được âm thanh', 'failed to generate audio', 'âm thanh', 'try again', 'thử lại']):
                            raise ProviderTransientError(f'Google Flow transient audio error: {txt}')
                        raise ProviderError(f'Google Flow video tile error: {txt}')

                    img = tile.locator('img.thumbnail').first
                    src = str(img.get_attribute('src') or '') if img.count() else ''
                    m = re.search(r'/(?:image|video)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', src)
                    media_id = m.group(1) if m else None
                    if media_id and media_id in before_set:
                        continue

                    tile_text = tile.inner_text().strip()
                    if any(k in tile_text.lower() for k in ['không thể tạo', 'failed to generate', 'policy vi phạm', 'lỗi tạo video']):
                        if any(k in tile_text.lower() for k in ['không tạo được âm thanh', 'âm thanh', 'try again', 'thử lại']):
                            raise ProviderTransientError(f'Google Flow transient audio error: {tile_text}')
                        raise ProviderError(f'Google Flow video tile error: {tile_text}')

                    is_generating = any(k in tile_text.lower() for k in ['%', 'đang', 'generating'])
                    if tile.locator('flow-pending-tile, mat-progress-spinner, mat-spinner, .progress-spinner').count() > 0:
                        is_generating = True

                    if is_generating:
                        pct_m = re.search(r'(\d+)%', tile_text)
                        if pct_m and callable(progress_callback):
                            val = int(pct_m.group(1))
                            if val > last_progress:
                                last_progress = val
                                progress_callback(val, 'flow-dom-video')
                        continue

                    if callable(progress_callback):
                        progress_callback(95, 'flow-dom-complete')

                    # Completed tile! Hover it to trigger the <video src="..."> element
                    hover_deadline = time.monotonic() + 15.0
                    while time.monotonic() < hover_deadline:
                        try:
                            page.mouse.move(0, 0)
                            page.wait_for_timeout(100)
                            tile.scroll_into_view_if_needed()
                            tile.hover()
                            page.wait_for_timeout(600)
                            vid = tile.locator('video').first
                            if vid.count():
                                vsrc = str(vid.get_attribute('src') or '')
                                if 'flow-content.google/video/' in vsrc:
                                    return vsrc
                        except Exception:
                            pass
                        page.wait_for_timeout(500)

                    # Also inspect if video element is already present
                    vid = tile.locator('video').first
                    if vid.count():
                        vsrc = str(vid.get_attribute('src') or '')
                        if 'flow-content.google/video/' in vsrc:
                            return vsrc

                    return media_id or src
                except (ProviderError, ProviderTransientError):
                    raise
                except Exception:
                    continue
            page.wait_for_timeout(2000)

        raise ProviderError('Google Flow video generation timed out before completion.')

    def _generate_video_via_ui(self, context: Any, page: Any, scene: dict[str, Any]) -> Path:
        with self._browser_ui_lock:
            references = list(scene.get('reference_images') or [])
            if not references and scene.get('reference_image'):
                references = [scene['reference_image']]
            model_id = str(scene.get('model') or 'veo_31_lite_relaxed')
            duration = int(scene.get('duration_seconds') or 8)
            aspect_ratio = str(scene.get('aspect_ratio') or '16:9')
            self._configure_video(page, model_id=model_id, duration=duration, aspect_ratio=aspect_ratio)

            start_path = Path(str(references[0]))
            self._attach_start_image(page, '', media_name=start_path.name, local_path=start_path)
            if len(references) > 1:
                end_path = Path(str(references[1]))
                self._attach_frame_image(
                    page,
                    '',
                    frame_label='Kết thúc',
                    media_name=end_path.name,
                    local_path=end_path,
                )

            # Clear any modal dialogs/overlays that may be open
            if page.locator('.cdk-overlay-container [role="dialog"], .cdk-overlay-container mat-dialog-container, .cdk-overlay-pane').count():
                for _ in range(2):
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(100)
            try:
                backdrop = page.locator('.cdk-overlay-backdrop').first
                if backdrop.count() and backdrop.is_visible():
                    backdrop.click(timeout=1000)
                    page.wait_for_timeout(200)
            except Exception:
                pass

            prompt = str(scene.get('prompt') or '').strip()
            editor = page.locator('flow-base-prompt-box .ProseMirror, flow-base-prompt-box [contenteditable="true"]').first
            if not editor.count():
                raise ProviderTransientError('Google Flow video prompt editor is unavailable; will retry.')
            editor.click()
            page.wait_for_timeout(200)
            page.keyboard.press('Control+A')
            page.keyboard.press('Backspace')
            page.wait_for_timeout(100)
            if prompt:
                page.keyboard.insert_text(prompt)
                page.wait_for_timeout(400)
                try:
                    editor.dispatch_event('input')
                except Exception:
                    pass

            generate = page.locator(
                'flow-base-prompt-box button.generate-icon-button, '
                'flow-base-prompt-box button:has(mat-icon:has-text("arrow_forward")), '
                'flow-base-prompt-box button[aria-label="Bắt đầu tạo"], '
                'flow-base-prompt-box button[aria-label="Generate"]'
            ).last

            # Wait for generate button to be enabled
            gen_deadline = time.monotonic() + 30.0
            while time.monotonic() < gen_deadline:
                if generate.count() and not generate.is_disabled():
                    break
                try:
                    editor.click()
                    page.keyboard.press('End')
                    page.keyboard.press('Space')
                    page.wait_for_timeout(100)
                    page.keyboard.press('Backspace')
                except Exception:
                    pass
                page.wait_for_timeout(500)

            if not generate.count() or generate.is_disabled():
                raise ProviderTransientError('Google Flow video Generate button is unavailable or disabled; will retry.')

            before_ids = self._flow_tile_media_ids(page)

            try:
                generate.click(timeout=10_000)
            except Exception:
                try:
                    generate.click(force=True, timeout=10_000)
                except Exception:
                    generate.dispatch_event('click')
            progress_callback = scene.get('_progress_callback')
            if callable(progress_callback):
                progress_callback(10, 'flow-dom-submitted')

            media_or_url = self._wait_for_flow_video_tile_complete(
                page,
                before_ids,
                timeout_seconds=max(120, int(scene.get('_video_timeout_seconds') or 900)),
                progress_callback=progress_callback,
            )

            if isinstance(media_or_url, str) and (media_or_url.startswith('http://') or media_or_url.startswith('https://')):
                return self._download_video_url(context or page, media_or_url, scene)

            try:
                return self._download_video_media(context or page, media_or_url, scene, timeout_seconds=180)
            except Exception as media_err:
                try:
                    return self._download_video_tile_via_ui(page, scene, media_id=str(media_or_url), context=context)
                except Exception:
                    raise media_err

    def _download_video_tile_via_ui(self, page: Any, scene: dict[str, Any] | str, media_id: str = '', context: Any = None) -> Path:
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
            tile = None
            if media_id and len(media_id) == 36:
                cand = page.locator(f"flow-video-tile:has(img[src*='{media_id}'])").first
                if cand.count():
                    tile = cand
                else:
                    cand = page.locator(f"flow-video-tile:has(video[src*='{media_id}'])").first
                    if cand.count():
                        tile = cand
            if tile is None:
                for t in page.locator("flow-video-tile").all():
                    if not t.locator("flow-error-tile, flow-pending-tile, mat-progress-spinner, mat-spinner").count():
                        tile = t
                        break
            if tile is None:
                tile = page.locator("flow-video-tile").first

            # Reliable hover
            for _ in range(5):
                page.mouse.move(0, 0)
                page.wait_for_timeout(100)
                tile.scroll_into_view_if_needed()
                tile.hover()
                page.wait_for_timeout(600)
                vid = tile.locator("video").first
                if vid.count():
                    vsrc = str(vid.get_attribute("src") or "")
                    if "flow-content.google/video/" in vsrc:
                        return self._download_video_url(context or page, vsrc, scene)

            more_btn = tile.locator("button[aria-label='Tuỳ chọn khác'], button[aria-label='More options'], button.mat-mdc-menu-trigger").first
            if not more_btn.count():
                raise ProviderError("More options button not found on video tile.")
            more_btn.click(force=True)
            page.wait_for_timeout(400)

            dl_menu = page.locator(".cdk-overlay-container button:has-text('Tải xuống'), .cdk-overlay-container button:has-text('Download')").first
            if not dl_menu.count():
                page.keyboard.press("Escape")
                raise ProviderError("Download menu item not found.")
            dl_menu.click(force=True)
            page.wait_for_timeout(400)

            btn_720 = page.locator(".cdk-overlay-container button:has-text('720p'), .cdk-overlay-container button:has-text('1080p')").first
            if not btn_720.count():
                btn_720 = page.locator(".cdk-overlay-container button").filter(has_text=re.compile(r'720|1080|download', re.I)).first
            if not btn_720.count():
                page.keyboard.press("Escape")
                raise ProviderError("Download resolution button not found.")

            with page.expect_download(timeout=30_000) as dl_info:
                btn_720.click(force=True)
            download = dl_info.value

            if isinstance(scene, dict):
                stem = scene_output_stem(scene)
                output_dir = scene_output_directory(scene, self.output_dir)
                output_path = (output_dir / f'{stem}.mp4').resolve()
                resolution = str(scene.get('_video_resolution') or '720p')
                res_path = (output_dir / f'{stem}_{resolution}.mp4').resolve()
            else:
                output_path = (self.output_dir / f'{scene}.mp4').resolve()
                res_path = None

            output_dir.mkdir(parents=True, exist_ok=True)
            download.save_as(str(output_path))
            if res_path and res_path != output_path:
                try:
                    shutil.copy2(output_path, res_path)
                except Exception:
                    pass
            page.keyboard.press("Escape")
            return output_path
        except Exception as e:
            page.keyboard.press("Escape")
            raise ProviderError(f"Google Flow video download via UI failed: {e}")

    def _download_video_media(
        self,
        context: Any,
        media_id: str,
        scene: dict[str, Any] | str,
        *,
        timeout_seconds: int,
    ) -> Path:
        redirect_url = f'https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name={media_id}'
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            redirect = context.request.get(redirect_url, max_redirects=0, timeout=30_000)
            status = int(getattr(redirect, 'status', 0))
            if status in {301, 302, 303, 307, 308}:
                location = str(getattr(redirect, 'headers', {}).get('location', ''))
                if location:
                    return self._download_video_url(context, location, scene)
            elif status == 401:
                break
            elif status not in {404, 409, 425, 429, 500, 502, 503, 504}:
                raise ProviderError(f'Google Flow video media lookup failed with HTTP {status}.')
            time.sleep(2.0)
        raise ProviderError('Google Flow video generation timed out before the MP4 became available.')

    def _download_video_url(
        self,
        context: Any,
        media_url: str,
        scene: dict[str, Any] | str,
    ) -> Path:
        body = b""
        req_client = None
        if context is not None:
            if hasattr(context, 'request'):
                req_client = context.request
            elif hasattr(context, 'context') and hasattr(context.context, 'request'):
                req_client = context.context.request
        if req_client is not None:
            try:
                media = req_client.get(media_url, timeout=120_000)
                if getattr(media, 'ok', False):
                    body = media.body()
            except Exception:
                body = b""

        if not body:
            import ssl
            import urllib.request
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(media_url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
                    body = resp.read()
            except Exception:
                pass

        if not body or b'ftyp' not in body[:64]:
            raise ProviderError('Google Flow direct video download returned a non-video response.')
        if isinstance(scene, dict):
            resolution = str(scene.get('_video_resolution') or '720p')
            stem = scene_output_stem(scene)
            output_dir = scene_output_directory(scene, self.output_dir)
            output_path = (output_dir / f'{stem}.mp4').resolve()
            res_path = (output_dir / f'{stem}_{resolution}.mp4').resolve()
        else:
            output_path = (self.output_dir / f'{scene}.mp4').resolve()
            res_path = None
        output_path.write_bytes(body)
        if res_path and res_path != output_path:
            try:
                res_path.write_bytes(body)
            except Exception:
                pass
        return output_path


class GoogleFlowHeadlessClient(GoogleFlowBrowserClient):
    """Use the account's verified live Flow session as an auth/recaptcha bridge.

    Generation itself is direct-wire.  This class deliberately does not launch a
    cookie-only Playwright browser and does not press Flow's Generate button.
    """

    FLOW_HOME_URL = 'https://flow.google.com/'

    def __init__(self, output_dir: str | Path, account_manager: GoogleFlowAccountManager | None = None):
        super().__init__(output_dir, session_worker=None)
        self.account_manager = account_manager
        self._migrated_image = MigratedFlowImageDriver(output_dir)
        self._migrated_video = MigratedFlowVideoDriver(output_dir)
        self._prepared_image_auth: set[str] = set()
        self._prepared_image_auth_lock = threading.Lock()
        self._live_token_cache: dict[str, tuple[str, float]] = {}
        self._last_session_persist_at: dict[str, float] = {}

    def _fetch_live_access_token(self, context: Any, *, account_id: str | None = None) -> str:
        """Fetch fresh Google OAuth access token from live session cookies matching G-Labs, with short TTL cache."""
        now = time.monotonic()
        if account_id:
            cached = self._live_token_cache.get(account_id)
            if cached and cached[0] and (now - cached[1]) < 90.0:
                return cached[0]
        try:
            req = getattr(context, "request", None)
            if req and hasattr(req, "get"):
                for session_url in (
                    "https://labs.google/fx/api/auth/session",
                    "https://flow.google.com/fx/api/auth/session",
                ):
                    try:
                        res = req.get(session_url)
                        if getattr(res, "ok", False):
                            data = res.json()
                            if isinstance(data, dict) and data.get("error") != "ACCESS_TOKEN_REFRESH_NEEDED":
                                tok = data.get("access_token") or data.get("accessToken")
                                if tok and isinstance(tok, str) and tok.startswith("ya29."):
                                    if account_id:
                                        self._live_token_cache[account_id] = (tok, now)
                                    return tok
                    except Exception:
                        continue
        except Exception:
            pass
        return ""

    def _prepare_image_page_auth(self, account_id: str, context: Any, page: Any) -> None:
        """Refresh Flow auth once per live account before image requests start.

        The page-context transport still sends the current OAuth Bearer explicitly.
        A saved NextAuth cookie can remain valid while /auth/session reports
        ACCESS_TOKEN_REFRESH_NEEDED; in that state the dedicated Flow site is
        reloaded briefly before the first request starts.
        This runs only before the account's first request so navigation can never wipe
        the in-page registry of already in-flight image requests.
        """
        with self._prepared_image_auth_lock:
            if account_id in self._prepared_image_auth:
                return
            if getattr(context, 'request', None) is None:
                self._prepared_image_auth.add(account_id)
                return
            payload = self._session_payload(context)
            if self._session_requires_page_refresh(payload):
                page.goto('https://labs.google/fx/', wait_until='domcontentloaded', timeout=60_000)
                wait_for_timeout = getattr(page, 'wait_for_timeout', None)
                deadline = time.monotonic() + 10.0
                while True:
                    if callable(wait_for_timeout):
                        wait_for_timeout(500)
                    else:
                        time.sleep(0.5)
                    payload = self._session_payload(context)
                    if (
                        not self._session_requires_page_refresh(payload)
                        and BrowserLoginWorker._extract_access_token(payload)
                    ):
                        break
                    if time.monotonic() >= deadline:
                        raise ProviderAuthError(
                            'Google Flow access token could not be refreshed from the saved session; renew this account once.'
                        )
            self._prepared_image_auth.add(account_id)

    def generate(self, scene: dict[str, Any], account: dict[str, Any], session_secret: dict[str, Any]) -> str:
        if self.account_manager is None:
            raise ProviderAuthError('The saved Google Flow session could not be reopened; renew this account once.')
        account_id = str(account.get('id') or '')
        if not account_id:
            raise ProviderAuthError('Google Flow account id is missing.')
        worker = getattr(self.account_manager, 'login_worker', None)
        execute_in_session = getattr(worker, 'execute_in_session', None)
        has_live_session = getattr(worker, 'has_live_session', None)
        if not callable(execute_in_session) or not callable(has_live_session):
            raise ProviderAuthError('The saved Google Flow session could not be reopened; renew this account once.')

        if not has_live_session(account_id):
            self._resume_saved_live_session(account, session_secret)

        if scene.get('task_type') == 'image_to_video':
            tier = str(account.get('tier') or '').strip().lower()
            if tier == 'free':
                raise ProviderError(
                    f"Tài khoản Google Flow '{account.get('email')}' thuộc gói Free. "
                    "Theo quy tắc G-Labs, tài khoản Free chỉ hỗ trợ tạo ảnh, không thể tạo video Veo. "
                    "Vui lòng chỉ định tài khoản Pro hoặc Ultra."
                )
            return self._generate_video_migrated_split(scene, account, session_secret)
        if scene.get('task_type') == 'image_generation':
            return self._generate_image_direct_split(scene, account, session_secret)

        def run_once(context: Any) -> str:
            page = self._flow_page(context)
            project_id = self._open_project(page, account)
            direct_scene = {
                **scene,
                '_flow_project_id': project_id,
                '_flow_account_tier': account.get('tier'),
                '_flow_paygate_tier': self._paygate_tier(str(account.get('tier') or '')),
            }
            result = self._generate_in_context(context, direct_scene)
            self._persist_refreshed_session(account_id, context, session_secret)
            return str(result)

        try:
            return str(execute_in_session(account_id, run_once, timeout_seconds=240.0))
        except Exception as exc:
            if not self._looks_like_closed_session(exc):
                raise
            self._resume_saved_live_session(account, session_secret, force=True)
            return str(execute_in_session(account_id, run_once, timeout_seconds=240.0))

    def _generate_image_direct_split(
        self,
        scene: dict[str, Any],
        account: dict[str, Any],
        session_secret: dict[str, Any],
    ) -> str:
        if self.account_manager is None:
            raise ProviderAuthError('The saved Google Flow session could not be reopened; renew this account once.')
        model_id = str(scene.get('model') or '')
        if model_id not in IMAGE_MODEL_MENU_LABELS:
            raise ProviderError(f'Unsupported Google Flow image model: {model_id!r}')
        references = list(scene.get('reference_images') or [])
        if not references and scene.get('reference_image'):
            references = [scene['reference_image']]
        max_references = int(GOOGLE_FLOW_MODEL_BY_ID[model_id]['capabilities'].get('max_references', 0))
        if len(references) > max_references:
            raise ProviderError(f'{GOOGLE_FLOW_MODEL_BY_ID[model_id]["name"]} supports at most {max_references} reference images.')
        for reference in references:
            if not Path(str(reference)).is_file():
                raise ProviderError(
                    f'{GOOGLE_FLOW_MODEL_BY_ID[model_id]["name"]} image generation requires every local reference image file to exist.'
                )

        if '_generate_in_context' in self.__dict__:
            worker = self.account_manager.login_worker
            execute_in_session = getattr(worker, 'execute_in_session')
            account_id = str(account['id'])
            def run_mock(context: Any) -> str:
                return str(self._generate_in_context(context, scene))
            return str(execute_in_session(account_id, run_mock, timeout_seconds=60.0, priority=0))

        return self._generate_image_migrated_split(
            {**scene, 'reference_images': [str(value) for value in references]},
            account,
            session_secret,
        )

    def _download_image_direct_or_session(
        self,
        account_id: str,
        execute_in_session: Callable[..., Any],
        record: Any,
        local_scene: dict[str, Any],
    ) -> str:
        image_url = str(getattr(record, 'image_url', '') or '')
        if image_url.startswith('https://'):
            try:
                req = urllib.request.Request(
                    image_url,
                    headers={
                        'User-Agent': (
                            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                            'AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/133.0.0.0 Safari/537.36'
                        ),
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    },
                )
                with urllib.request.urlopen(req, timeout=90) as resp:
                    if resp.status == 200:
                        body = resp.read()
                        if body and len(body) > 512:
                            content_type = str(resp.headers.get('Content-Type') or '').lower()
                            extension = '.png' if 'png' in content_type else '.webp' if 'webp' in content_type else '.jpg'
                            out_dir = scene_output_directory(local_scene, self.output_dir)
                            output_path = (out_dir / f"{scene_output_stem(local_scene)}{extension}").resolve()
                            output_path.write_bytes(body)
                            if local_scene.get('_remove_watermark'):
                                try:
                                    strip_gemini_watermark(output_path)
                                except Exception:
                                    pass
                            return str(output_path)
            except Exception:
                pass
        return str(
            execute_in_session(
                account_id,
                lambda ctx: str(self._migrated_image.download(ctx, record, local_scene)),
                timeout_seconds=120.0,
                priority=5,
            )
        )

    def _generate_image_migrated_split(
        self,
        scene: dict[str, Any],
        account: dict[str, Any],
        session_secret: dict[str, Any],
    ) -> str:
        assert self.account_manager is not None
        worker = self.account_manager.login_worker
        execute_in_session = getattr(worker, 'execute_in_session')
        account_id = str(account['id'])

        def run_sync_fallback(context: Any) -> str:
            page = self._flow_page(context)
            project_id = self._open_project(page, account)
            self._prepare_image_page_auth(account_id, context, page)
            fresh_token = self._fetch_live_access_token(context, account_id=account_id)
            session = session_secret.get('session') if isinstance(session_secret, dict) else {}
            access_token = fresh_token or BrowserLoginWorker._extract_access_token(session)
            local_scene = {
                **scene,
                '_access_token': access_token,
                '_account_email': account.get('email'),
                '_flow_project_id': project_id,
                '_flow_account_tier': account.get('tier'),
                '_flow_paygate_tier': self._paygate_tier(str(account.get('tier') or '')),
            }
            try:
                output = self._migrated_image.generate(page, context, project_id, local_scene)
            except ProviderQuotaError:
                raise
            except ProviderAuthError:
                if access_token:
                    raise
                output = self._generate_image_via_ui(context, page, local_scene)
            except Exception as direct_err:
                err_str = str(direct_err)
                if "404" in err_str or "not found" in err_str.lower():
                    logger.warning("Project %s returned 404; clearing stale cache and discovering active project...", project_id)
                    account['_failed_project_id'] = str(project_id or account.get('project_id') or '').strip()
                    account['project_id'] = ''
                    if self.account_manager and hasattr(self.account_manager, 'db'):
                        try:
                            self.account_manager.db.patch_resource(ACCOUNT_RESOURCE_TYPE, account_id, {'project_id': None})
                        except Exception:
                            pass
                    project_id = self._open_project(page, account)
                    local_scene['_flow_project_id'] = project_id
                    try:
                        output = self._migrated_image.generate(page, context, project_id, local_scene)
                    except (ProviderQuotaError, ProviderAuthError):
                        raise
                    except Exception as retry_err:
                        logger.warning("Retry with recovered project failed (%s), falling back to UI: %s", project_id, retry_err)
                        output = self._generate_image_via_ui(context, page, local_scene)
                else:
                    logger.warning("Google Flow direct REST image generation failed, trying UI fallback: %s", direct_err)
                    output = self._generate_image_via_ui(context, page, local_scene)
            self._persist_refreshed_session(account_id, context, session_secret)
            return str(output)

        def run_ui_direct(context: Any) -> str:
            page = self._flow_page(context)
            project_id = self._open_project(page, account)
            fresh_token = self._fetch_live_access_token(context, account_id=account_id)
            session = session_secret.get('session') if isinstance(session_secret, dict) else {}
            access_token = fresh_token or BrowserLoginWorker._extract_access_token(session)
            local_scene = {
                **scene,
                '_access_token': access_token,
                '_account_email': account.get('email'),
                '_flow_project_id': project_id,
                '_flow_account_tier': account.get('tier'),
                '_flow_paygate_tier': self._paygate_tier(str(account.get('tier') or '')),
            }
            output = self._generate_image_via_ui(context, page, local_scene)
            self._persist_refreshed_session(account_id, context, session_secret)
            return str(output)

        if 'generate' not in getattr(self._migrated_image, '__dict__', {}) and (
            bool(scene.get('reference_images') or scene.get('reference_image'))
            or bool(isinstance(session_secret, dict) and session_secret.get('migrated_host'))
            or bool(account.get('_batch_image_404'))
        ):
            try:
                return str(execute_in_session(account_id, run_ui_direct, timeout_seconds=360.0, priority=0))
            except Exception as exc:
                if not self._looks_like_closed_session(exc):
                    raise
                self._resume_saved_live_session(account, session_secret, force=True)
                return str(execute_in_session(account_id, run_ui_direct, timeout_seconds=360.0, priority=0))

        if (
            'generate' in getattr(self._migrated_image, '__dict__', {})
            or not hasattr(self._migrated_image, 'start_async_submit')
        ):
            try:
                return str(execute_in_session(account_id, run_sync_fallback, timeout_seconds=360.0, priority=0))
            except Exception as exc:
                if not self._looks_like_closed_session(exc):
                    raise
                self._resume_saved_live_session(account, session_secret, force=True)
                return str(execute_in_session(account_id, run_sync_fallback, timeout_seconds=360.0, priority=0))

        def start_step(context: Any) -> tuple[dict[str, Any], dict[str, Any]]:
            page = self._flow_page(context)
            self._prepare_image_page_auth(account_id, context, page)
            project_id = self._open_project(page, account)
            fresh_token = self._fetch_live_access_token(context, account_id=account_id)
            session = session_secret.get('session') if isinstance(session_secret, dict) else {}
            access_token = fresh_token or BrowserLoginWorker._extract_access_token(session)
            local_scene = {
                **scene,
                '_access_token': access_token,
                '_account_email': account.get('email'),
                '_flow_project_id': project_id,
                '_flow_account_tier': account.get('tier'),
                '_flow_paygate_tier': self._paygate_tier(str(account.get('tier') or '')),
            }
            ticket = self._migrated_image.start_async_submit(page, project_id, local_scene)
            self._persist_refreshed_session(account_id, context, session_secret)
            return ticket, local_scene

        try:
            try:
                ticket, local_scene = execute_in_session(account_id, start_step, timeout_seconds=120.0, priority=0)
            except Exception as exc:
                if not self._looks_like_closed_session(exc):
                    raise
                self._resume_saved_live_session(account, session_secret, force=True)
                ticket, local_scene = execute_in_session(account_id, start_step, timeout_seconds=120.0, priority=0)

            record = ticket.get('record') if ticket.get('state') == 'done' else None
            deadline = time.monotonic() + 240.0
            retried_missing = False
            while record is None and time.monotonic() < deadline:
                time.sleep(0.5)

                def poll_step(context: Any) -> Any:
                    page = self._flow_page(context)
                    return self._migrated_image.poll_async_submit(page, ticket)

                try:
                    record = execute_in_session(account_id, poll_step, timeout_seconds=30.0, priority=10)
                except Exception as exc:
                    if self._looks_like_closed_session(exc):
                        self._resume_saved_live_session(account, session_secret, force=True)
                        ticket, local_scene = execute_in_session(account_id, start_step, timeout_seconds=120.0, priority=0)
                        record = ticket.get('record') if ticket.get('state') == 'done' else None
                        continue
                    if not retried_missing and 'state was lost' in str(exc).lower():
                        retried_missing = True
                        ticket, local_scene = execute_in_session(account_id, start_step, timeout_seconds=120.0, priority=0)
                        record = ticket.get('record') if ticket.get('state') == 'done' else None
                        continue
                    raise

            if record is None:
                raise ProviderError('Google Flow REST image generation timed out waiting for response.')

            return self._download_image_direct_or_session(account_id, execute_in_session, record, local_scene)
        except (ProviderQuotaError, ProviderAuthError):
            raise
        except Exception as async_err:
            logger.warning("Async split image generation encountered error (%s), trying fallback...", async_err)
            err_str = str(async_err)
            if "404" in err_str or "not found" in err_str.lower():
                account['_failed_project_id'] = str(account.get('project_id') or '').strip()
                account['project_id'] = ''
                if self.account_manager and hasattr(self.account_manager, 'db'):
                    try:
                        self.account_manager.db.patch_resource(ACCOUNT_RESOURCE_TYPE, account_id, {'project_id': None})
                    except Exception:
                        pass
            return str(execute_in_session(account_id, run_sync_fallback, timeout_seconds=180.0, priority=0))

    @staticmethod
    def _looks_like_closed_session(exc: BaseException) -> bool:
        return _looks_like_closed_session(exc)

    def _resume_saved_live_session(
        self,
        account: dict[str, Any],
        session_secret: dict[str, Any],
        *,
        force: bool = False,
    ) -> None:
        del session_secret
        if self.account_manager is None:
            raise ProviderAuthError('The saved Google Flow session could not be reopened; renew this account once.')
        worker = getattr(self.account_manager, 'login_worker', None)
        account_id = str(account.get('id') or '')
        request_started_at = time.monotonic()
        with self._prepared_image_auth_lock:
            resume_locks = getattr(self, '_resume_locks', None)
            if resume_locks is None:
                resume_locks = {}
                self._resume_locks = resume_locks
            acc_lock = resume_locks.get(account_id)
            if acc_lock is None:
                acc_lock = threading.Lock()
                resume_locks[account_id] = acc_lock
            resumed_at_map = getattr(self, '_last_session_resumed_at', None)
            if resumed_at_map is None:
                resumed_at_map = {}
                self._last_session_resumed_at = resumed_at_map

        with acc_lock:
            has_live_session = getattr(worker, 'has_live_session', None)
            is_interactive = getattr(worker, 'is_interactive', None)
            if callable(is_interactive) and is_interactive(account_id):
                if callable(has_live_session) and has_live_session(account_id):
                    return
                raise ProviderTransientError('Google Flow account is currently open for interactive verification.')
            if callable(has_live_session) and has_live_session(account_id):
                if not force or resumed_at_map.get(account_id, 0.0) >= request_started_at:
                    return
            with self._prepared_image_auth_lock:
                self._prepared_image_auth.discard(account_id)
            if force:
                close_session = getattr(worker, 'close_session', None)
                if callable(close_session):
                    try:
                        close_session(account_id)
                    except Exception:
                        pass
            resume_session = getattr(worker, 'resume_session', None)
            profile_root = getattr(self.account_manager, 'profile_root', None)
            if not callable(resume_session) or profile_root is None:
                raise ProviderAuthError('The saved Google Flow session could not be reopened; renew this account once.')
            profile_dir = self.account_manager.profile_dir_for_account(account)
            if hasattr(self.account_manager, 'enforce_memory_budget'):
                self.account_manager.enforce_memory_budget(target_spare=1)
            resume_session(
                account_id,
                profile_dir,
                getattr(self.account_manager, 'complete_login'),
                getattr(self.account_manager, 'fail_login'),
            )
            deadline = time.monotonic() + 60.0
            while callable(has_live_session) and time.monotonic() < deadline:
                if has_live_session(account_id):
                    resumed_at_map[account_id] = time.monotonic()
                    return
                time.sleep(0.2)
            if not callable(has_live_session) or not has_live_session(account_id):
                raise ProviderAuthError('The saved Google Flow session could not be reopened; renew this account once.')

    def _generate_video_direct_split(
        self,
        scene: dict[str, Any],
        account: dict[str, Any],
        session_secret: dict[str, Any],
    ) -> str:
        assert self.account_manager is not None
        worker = self.account_manager.login_worker
        execute_in_session = getattr(worker, 'execute_in_session')
        account_id = str(account['id'])
        progress_callback = scene.get('_progress_callback')

        references = list(scene.get('reference_images') or [])
        if not references and scene.get('reference_image'):
            references = [scene['reference_image']]
        if not references:
            raise ProviderError('Google Flow image-to-video requires a local reference image.')
        if len(references) > 2:
            raise ProviderError('Google Flow image-to-video supports one start frame and one optional end frame.')
        for reference in references:
            if not Path(str(reference)).is_file():
                raise ProviderError(f'Google Flow reference image does not exist: {reference}')

        submit_scene = {
            **scene,
            'reference_image': references[0],
            'reference_images': references,
            '_flow_account_tier': account.get('tier'),
            '_flow_paygate_tier': self._paygate_tier(str(account.get('tier') or '')),
        }

        def submit(context: Any) -> Path:
            page = self._flow_page(context)
            project_id = self._open_project(page, account)
            local_scene = {**submit_scene, '_flow_project_id': project_id}
            submit_scene['_flow_project_id'] = project_id
            output = self._generate_video_via_ui(context, page, local_scene)
            self._persist_refreshed_session(account_id, context, session_secret)
            return output

        try:
            if callable(progress_callback):
                progress_callback(5, 'flow-dom-start')
            timeout_seconds = max(60.0, float(scene.get('_video_timeout_seconds') or 900.0))
            output = execute_in_session(
                account_id,
                submit,
                timeout_seconds=timeout_seconds + 90.0,
                priority=0,
            )
        except Exception as exc:
            if not self._looks_like_closed_session(exc):
                raise
            self._resume_saved_live_session(account, session_secret, force=True)
            output = execute_in_session(
                account_id,
                submit,
                timeout_seconds=timeout_seconds + 90.0,
                priority=0,
            )
        if callable(progress_callback):
            progress_callback(100, 'flow-dom-complete')
        return str(output)

    def _generate_video_migrated_split(
        self,
        scene: dict[str, Any],
        account: dict[str, Any],
        session_secret: dict[str, Any],
    ) -> str:
        assert self.account_manager is not None
        worker = self.account_manager.login_worker
        execute_in_session = getattr(worker, 'execute_in_session')
        account_id = str(account['id'])

        references = list(scene.get('reference_images') or [])
        if not references and scene.get('reference_image'):
            references = [scene['reference_image']]
        if not (1 <= len(references) <= 2):
            raise ProviderError('Google Flow image-to-video supports one start frame and one optional end frame.')
        for reference in references:
            if not Path(str(reference)).is_file():
                raise ProviderError(f'Google Flow reference image does not exist: {reference}')

        session = session_secret.get('session') if isinstance(session_secret, dict) else {}
        access_token = BrowserLoginWorker._extract_access_token(session)
        submit_scene = {
            **scene,
            '_access_token': access_token,
            '_account_email': account.get('email'),
            'reference_image': str(references[0]),
            'reference_images': [str(r) for r in references],
            '_flow_account_tier': account.get('tier'),
            '_flow_paygate_tier': self._paygate_tier(str(account.get('tier') or '')),
        }

        def submit(context: Any) -> tuple[str, str]:
            page = self._flow_page(context)
            project_id = self._open_project(page, account)
            self._prepare_image_page_auth(account_id, context, page)
            # Dynamically refresh token matching G-Labs
            fresh_token = self._fetch_live_access_token(context)
            if fresh_token:
                submit_scene['_access_token'] = fresh_token
            record = self._migrated_video.submit(page, project_id, submit_scene)
            submit_scene['_flow_project_id'] = project_id
            self._persist_refreshed_session(account_id, context, session_secret)
            return record.workflow_id, project_id

        try:
            workflow_id, project_id = execute_in_session(account_id, submit, timeout_seconds=150.0, priority=0)
        except Exception as exc:
            if not self._looks_like_closed_session(exc):
                raise
            self._resume_saved_live_session(account, session_secret, force=True)
            workflow_id, project_id = execute_in_session(account_id, submit, timeout_seconds=150.0, priority=0)

        submit_scene['_flow_project_id'] = project_id
        timeout_seconds = max(60.0, float(scene.get('_video_timeout_seconds') or 900.0))
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            def poll(context: Any) -> str | None:
                page = self._flow_page(context)
                record = self._migrated_video.poll(page, workflow_id)
                self._persist_refreshed_session(account_id, context, session_secret)
                if record is None or record.is_running:
                    return None
                if record.is_failed:
                    raise ProviderError(f'Google Flow migrated video generation failed with status {record.status}.')
                if not record.is_done:
                    return None
                return str(self._migrated_video.download(context, record, submit_scene))

            try:
                output = execute_in_session(account_id, poll, timeout_seconds=30.0, priority=10)
            except Exception as exc:
                if not self._looks_like_closed_session(exc):
                    raise
                self._resume_saved_live_session(account, session_secret, force=True)
                output = execute_in_session(account_id, poll, timeout_seconds=30.0, priority=10)
            if output:
                return str(output)
            time.sleep(1.5)
        raise ProviderError('Google Flow migrated video generation timed out before the MP4 became available.')

    def _persist_refreshed_session(
        self,
        account_id: str,
        context: Any,
        previous_secret: dict[str, Any],
    ) -> None:
        manager = self.account_manager
        if manager is None or not hasattr(manager, 'secret_store') or not hasattr(manager, 'db'):
            return
        now = time.monotonic()
        last_persist = getattr(self, '_last_session_persist_at', {}).get(account_id, 0.0)
        if last_persist > 0 and (now - last_persist) < 45.0:
            return
        cookies_fn = getattr(context, 'cookies', None)
        if not callable(cookies_fn):
            return
        try:
            cookies = cookies_fn()
        except Exception:
            return
        if not isinstance(cookies, list) or not cookies:
            return
        session_payload = previous_secret.get('session') if isinstance(previous_secret, dict) else None
        request = getattr(context, 'request', None)
        if request is not None and callable(getattr(request, 'get', None)):
            for sess_url in (FLOW_AUTH_SESSION_URL, FLOW_MIGRATED_SESSION_URL):
                try:
                    response = request.get(sess_url, timeout=15_000)
                    if getattr(response, 'ok', False):
                        refreshed = response.json()
                        if isinstance(refreshed, dict) and BrowserLoginWorker._extract_access_token(refreshed):
                            session_payload = refreshed
                            break
                except Exception:
                    continue
        secret = dict(previous_secret) if isinstance(previous_secret, dict) else {}
        secret['cookies'] = cookies
        if isinstance(session_payload, dict):
            secret['session'] = session_payload
        secret['captured_at'] = _utc_now()
        manager.secret_store.set_google_session(account_id, secret)
        if hasattr(self, '_last_session_persist_at'):
            self._last_session_persist_at[account_id] = now
        token_cookie = next(
            (cookie for cookie in cookies if cookie.get('name') == '__Secure-next-auth.session-token'),
            None,
        )
        expires_at = BrowserLoginWorker._cookie_expiry(token_cookie) if isinstance(token_cookie, dict) else None
        manager.db.patch_resource(
            ACCOUNT_RESOURCE_TYPE,
            account_id,
            {
                'status': 'ready',
                'session_expires_at': expires_at,
                'last_error': None,
            },
        )

    def _open_project(self, page: Any, account: dict[str, Any] | None = None) -> str:
        account = account or {}
        cached_project_id = str(account.get('project_id') or '').strip()
        if not cached_project_id and self.account_manager and hasattr(self.account_manager, 'db') and account.get('id'):
            try:
                db_acc = self.account_manager.db.get_resource(ACCOUNT_RESOURCE_TYPE, str(account['id'])) or {}
                cached_project_id = str(db_acc.get('project_id') or '').strip()
                if cached_project_id:
                    account['project_id'] = cached_project_id
            except Exception:
                pass
        try:
            self._ensure_companion_extension(getattr(page, 'context', page))
        except Exception:
            pass

        def _is_unauth_url(url: str) -> bool:
            u = (url or '').lower()
            return 'accounts.google.com' in u

        def _try_resolve_account_chooser() -> bool:
            curr = str(getattr(page, 'url', '') or '')
            if 'accounts.google.com' in curr and 'accountchooser' in curr:
                email = str(account.get('email') or '').lower().strip()
                if email:
                    try:
                        acc_loc = page.locator(f'[data-email*="{email}"], [data-identifier*="{email}"], div:has-text("{email}")').last
                        if acc_loc.count() > 0 and acc_loc.is_visible():
                            logger.info("Found account %s in Google account chooser; clicking to resume session...", email)
                            acc_loc.click()
                            if hasattr(page, 'wait_for_timeout'):
                                page.wait_for_timeout(4_000)
                            else:
                                time.sleep(4.0)
                            return not _is_unauth_url(str(getattr(page, 'url', '') or ''))
                    except Exception as e:
                        logger.warning("Error resolving account chooser for %s: %s", email, e)
            return False

        def check_auth_or_raise() -> None:
            curr = str(getattr(page, 'url', '') or '')
            if _is_unauth_url(curr):
                if _try_resolve_account_chooser():
                    return
                curr = str(getattr(page, 'url', '') or '')
                if _is_unauth_url(curr):
                    raise ProviderAuthError(f'Google Flow saved session has expired or redirected to sign-in ({curr}); renew this account once.')
            try:
                title = str(getattr(page, 'title', lambda: '')() or '').lower()
                if ('sign in' in title or 'đăng nhập' in title) and 'flow.google.com' not in curr:
                    raise ProviderAuthError('Google Flow saved session has expired; renew this account once.')
            except ProviderAuthError:
                raise
            except Exception:
                pass

        def wait_for_composer() -> None:
            self._dismiss_flow_dialogs(page)
            combined_selector = f'{FLOW_COMPOSER_SELECTOR}, {MIGRATED_FLOW_READY_ANCHOR}, flow-prompt-box'
            try:
                page.locator(combined_selector).first.wait_for(state='visible', timeout=3_000)
            except Exception:
                pass

        failed_project_id = str(account.get('_failed_project_id') or '').strip()

        # Fast-path: if page is already on an active project URL, reuse it without reloading
        curr_url_initial = str(getattr(page, 'url', '') or '')
        if '/project/' in curr_url_initial and '/404' not in curr_url_initial and not _is_unauth_url(curr_url_initial):
            existing_page_proj = self._project_id_from_url(curr_url_initial)
            if (
                existing_page_proj
                and existing_page_proj != failed_project_id
                and (not cached_project_id or existing_page_proj == cached_project_id)
            ):
                account['project_id'] = existing_page_proj
                return existing_page_proj

        if cached_project_id:
            check_auth_or_raise()
            curr_url = str(getattr(page, 'url', ''))
            active_project = '/project/' in curr_url and self._project_id_from_url(curr_url) == cached_project_id
            if active_project and '/404' not in curr_url:
                self._dismiss_flow_dialogs(page)
                return cached_project_id
            dest_url = f'https://flow.google.com/project/{cached_project_id}'
            try:
                page.goto(
                    dest_url,
                    wait_until='domcontentloaded',
                    timeout=30_000,
                )
            except Exception:
                pass
            check_auth_or_raise()
            curr_url = str(getattr(page, 'url', ''))
            actual_id = self._project_id_from_url(curr_url)
            if actual_id and '/404' not in curr_url and not _is_unauth_url(curr_url):
                self._dismiss_flow_dialogs(page)
                account['project_id'] = actual_id
                return actual_id
            if '/project/' in curr_url and '/404' not in curr_url and not _is_unauth_url(curr_url):
                self._dismiss_flow_dialogs(page)
                account['project_id'] = cached_project_id
                return cached_project_id
            body = ''
            try:
                body = page.locator('body').inner_text(timeout=3_000)
            except Exception:
                pass
            check_auth_or_raise()
            logger.warning(
                "Google Flow cached project %s not reachable (current: %s); discovering active project...",
                cached_project_id,
                curr_url,
            )

        try:
            page.goto(self.FLOW_HOME_URL, wait_until='domcontentloaded', timeout=60_000)
        except Exception:
            check_auth_or_raise()
            redirected = self._project_id_from_url(str(getattr(page, 'url', '')))
            if redirected and redirected != failed_project_id:
                wait_for_composer()
                account['project_id'] = redirected
                account.pop('_failed_project_id', None)
                return redirected

        check_auth_or_raise()
        redirected = self._project_id_from_url(str(getattr(page, 'url', '')))
        if redirected and redirected != failed_project_id:
            wait_for_composer()
            account['project_id'] = redirected
            account.pop('_failed_project_id', None)
            return redirected

        curr_url = str(getattr(page, 'url', '')).lower()
        if '/about' in curr_url or 'about' in curr_url:
            for cta_sel in [
                'button:has-text("Tạo bằng Google Flow")',
                'button:has-text("Dùng thử trong Google Flow")',
                'button:has-text("Dùng thử Google Flow")',
                'button:has-text("Create in Google Flow")',
                'button:has-text("Try Google Flow")',
                'button:has-text("Launch Flow")',
            ]:
                btn = page.locator(cta_sel).first
                if btn.count() and btn.is_visible():
                    try:
                        btn.click(timeout=3000)
                        break
                    except Exception:
                        pass
            try:
                page.wait_for_timeout(2000)
            except Exception:
                pass
            check_auth_or_raise()
            redirected = self._project_id_from_url(str(getattr(page, 'url', '')))
            if redirected and redirected != failed_project_id:
                wait_for_composer()
                account['project_id'] = redirected
                account.pop('_failed_project_id', None)
                return redirected

        try:
            page.locator('flow-project-card, a[href*="/project/"], a[href*="/tools/flow/project/"], button:has-text("New project"), button:has-text("Create project"), button:has-text("Dự án mới"), button.new-project-button, [aria-label*="New project"]').first.wait_for(state='visible', timeout=6000)
        except Exception:
            pass

        cards = page.locator('flow-project-card')
        if cards.count() > 0 and cards.first.is_visible():
            try:
                cards.first.click(timeout=5000)
                page.wait_for_url("**/project/**", timeout=15000)
                actual_id = self._project_id_from_url(str(getattr(page, 'url', '')))
                if actual_id:
                    wait_for_composer()
                    account['project_id'] = actual_id
                    account.pop('_failed_project_id', None)
                    account_id = str(account.get('id') or '')
                    if self.account_manager and hasattr(self.account_manager, 'db') and account_id:
                        try:
                            self.account_manager.db.patch_resource(ACCOUNT_RESOURCE_TYPE, account_id, {'project_id': actual_id})
                        except Exception:
                            pass
                    return actual_id
            except Exception as exc:
                logger.warning("Failed clicking flow-project-card: %s", exc)

        links = page.locator('a[href*="/project/"], a[href*="/tools/flow/project/"]')
        if links.count() > 0:
            href = links.first.get_attribute('href')
            if href:
                if href.startswith('/tools/flow/'):
                    href = f'https://labs.google{href}'
                elif href.startswith('/'):
                    href = f'https://flow.google.com{href}'
                try:
                    page.goto(href, wait_until='domcontentloaded', timeout=60_000)
                    check_auth_or_raise()
                    project_id = self._project_id_from_url(str(getattr(page, 'url', ''))) or self._project_id_from_url(href)
                    if project_id:
                        account['project_id'] = project_id
                        account.pop('_failed_project_id', None)
                        account_id = str(account.get('id') or '')
                        if self.account_manager and hasattr(self.account_manager, 'db') and account_id:
                            try:
                                self.account_manager.db.patch_resource(ACCOUNT_RESOURCE_TYPE, account_id, {'project_id': project_id})
                            except Exception:
                                pass
                        wait_for_composer()
                        return project_id
                except Exception as exc:
                    logger.warning("Failed navigating to project link %s: %s", href, exc)

        new_btn = page.locator('button.new-project-button, button:has-text("New project"), button:has-text("Create project"), button:has-text("Dự án mới"), [aria-label*="New project"]').first
        if new_btn.count() and new_btn.is_visible():
            try:
                new_btn.click(timeout=5000)
                page.wait_for_url("**/project/**", timeout=15000)
                actual_id = self._project_id_from_url(str(getattr(page, 'url', '')))
                if actual_id:
                    wait_for_composer()
                    account['project_id'] = actual_id
                    account.pop('_failed_project_id', None)
                    account_id = str(account.get('id') or '')
                    if self.account_manager and hasattr(self.account_manager, 'db') and account_id:
                        try:
                            self.account_manager.db.patch_resource(ACCOUNT_RESOURCE_TYPE, account_id, {'project_id': actual_id})
                        except Exception:
                            pass
                    return actual_id
            except Exception as exc:
                logger.warning("Failed clicking new project button: %s", exc)

        check_auth_or_raise()
        body = ''
        try:
            body = page.locator('body').inner_text(timeout=5_000)
        except Exception:
            pass
        if 'sign in' in body.lower() or 'đăng nhập' in body.lower() or 'get started' in body.lower() or 'accounts.google.com' in str(getattr(page, 'url', '')).lower():
            raise ProviderAuthError('Google Flow saved session has expired; renew this account once.')
        raise ProviderError('No Google Flow project is available. Create one Flow project once, then retry.')


class FlowClient(Protocol):
    def generate(self, scene: dict[str, Any], account: dict[str, Any], session_secret: dict[str, Any]) -> Any: ...


class GoogleFlowSessionProvider(MediaProvider):
    _looks_like_closed_session = staticmethod(_looks_like_closed_session)

    def __init__(
        self,
        output_dir: str | Path,
        account_manager: GoogleFlowAccountManager,
        *,
        flow_client: FlowClient | None = None,
        account_cooldown_seconds: float = 60.0,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.account_manager = account_manager
        self.flow_client = flow_client
        self.account_cooldown_seconds = max(0.0, float(account_cooldown_seconds))
        self._lease_wait_condition = asyncio.Condition()
        self._lease_waiters: list[tuple[object, bool]] = []

    def list_models(self) -> list[dict[str, Any]]:
        return [dict(model) for model in GOOGLE_FLOW_MODELS]

    def dispatch_pacing_key(self, scene: dict[str, Any], slot: Any) -> str | None:
        del scene
        if isinstance(slot, dict):
            account_id = str(slot.get('id') or '').strip()
            if account_id:
                return f'google-flow-account:{account_id}'
        return None

    async def acquire_job_slot(self, scene: dict[str, Any]) -> dict[str, Any]:
        return await self._lease_account_when_available(str(scene.get('model', '')))

    async def release_job_slot(self, scene: dict[str, Any], slot: Any) -> None:
        del scene
        if not isinstance(slot, dict) or slot.get('_queue_slot_released'):
            return
        account_id = str(slot.get('id') or '')
        if account_id:
            self.account_manager.release_account(account_id)
        slot['_queue_slot_released'] = True

    async def _lease_account_when_available(
        self,
        model_id: str,
        *,
        exclude_account_ids: set[str] | None = None,
        priority: bool = False,
        timeout_seconds: float = 600.0,
    ) -> dict[str, Any]:
        token = object()
        waiter = (token, bool(priority))
        excluded = set(exclude_account_ids or ())
        deadline = time.monotonic() + max(10.0, timeout_seconds)
        async with self._lease_wait_condition:
            self._lease_waiters.append(waiter)
            self._lease_wait_condition.notify_all()

        try:
            while True:
                if time.monotonic() >= deadline:
                    raise ProviderTransientError(
                        f'Timed out waiting for an available Google Flow account for {model_id} after {timeout_seconds}s.'
                    )
                async with self._lease_wait_condition:
                    while True:
                        if time.monotonic() >= deadline:
                            raise ProviderTransientError(
                                f'Timed out waiting for an available Google Flow account for {model_id} after {timeout_seconds}s.'
                            )
                        priority_waiters = [item for item in self._lease_waiters if item[1]]
                        selected = priority_waiters[0] if priority_waiters else self._lease_waiters[0]
                        if selected[0] is token:
                            break
                        try:
                            await asyncio.wait_for(self._lease_wait_condition.wait(), timeout=1.0)
                        except asyncio.TimeoutError:
                            pass

                try:
                    account = self.account_manager.lease_account(
                        model_id,
                        exclude_account_ids=excluded or None,
                    )
                except ProviderTransientError as exc:
                    if time.monotonic() >= deadline:
                        raise ProviderTransientError(
                            f'Timed out waiting for an available Google Flow account for {model_id}: {exc}'
                        ) from exc
                    async with self._lease_wait_condition:
                        self._lease_wait_condition.notify_all()
                    await asyncio.sleep(1.0)
                    continue

                async with self._lease_wait_condition:
                    self._lease_waiters = [item for item in self._lease_waiters if item[0] is not token]
                    self._lease_wait_condition.notify_all()
                return account
        finally:
            async with self._lease_wait_condition:
                before = len(self._lease_waiters)
                self._lease_waiters = [item for item in self._lease_waiters if item[0] is not token]
                if len(self._lease_waiters) != before:
                    self._lease_wait_condition.notify_all()

    async def _call_flow_client(
        self,
        scene: dict[str, Any],
        account: dict[str, Any],
        session_secret: dict[str, Any],
    ) -> Any:
        if self.flow_client is None:
            raise ProviderError(
                'Google Flow session is connected, but the request adapter still needs one verified live Flow request before generation can run.'
            )
        generate = self.flow_client.generate
        if inspect.iscoroutinefunction(generate):
            result = await generate(scene, account, session_secret)
        else:
            result = await asyncio.to_thread(generate, scene, account, session_secret)
        if inspect.isawaitable(result):
            result = await result
        return result

    @staticmethod
    def _is_recaptcha_challenge(exc: BaseException) -> bool:
        text = str(exc).lower()
        unusual_activity = (
            'unusual_activity' in text
            or 'unusual activity' in text
            or 'evaluation failed' in text
        )
        if not unusual_activity:
            return False
        return (
            'recaptcha' in text
            or 'public_error_unusual_activity' in text
            or 'verification required' in text
        )

    @staticmethod
    def _is_model_unavailable(exc: BaseException) -> bool:
        text = str(exc).lower()
        return 'model' in text and 'unavailable for this account' in text

    @staticmethod
    def _is_browser_timeout(exc: BaseException) -> bool:
        text = str(exc).lower()
        return 'timeout' in text or 'timed out' in text

    async def generate(self, scene: dict[str, Any]) -> str:
        model_id = str(scene.get('model', ''))
        reserved = scene.get('_provider_job_slot')
        account = reserved if isinstance(reserved, dict) and reserved.get('id') else None
        queue_owned = account is not None
        excluded: set[str] = set()
        auth_retried: set[str] = set()
        recaptcha_challenges = 0

        if account is None:
            account = await self._lease_account_when_available(model_id)

        while True:
            account_id = str(account['id'])
            released = False

            def release_current() -> None:
                nonlocal released
                if released:
                    return
                self.account_manager.release_account(account_id)
                released = True
                if queue_owned and isinstance(reserved, dict) and reserved.get('id') == account_id:
                    reserved['_queue_slot_released'] = True

            session_secret = self.account_manager.get_session_secret(account_id)
            if session_secret is None:
                await asyncio.to_thread(self.account_manager.try_refresh_session_api, account_id)
                session_secret = self.account_manager.get_session_secret(account_id)
            if session_secret is None:
                try:
                    await asyncio.to_thread(self.account_manager.ensure_live_session, account_id, timeout_seconds=60.0)
                    session_secret = self.account_manager.get_session_secret(account_id)
                except Exception:
                    pass
            if session_secret is None:
                worker = getattr(self.account_manager, 'login_worker', None)
                has_live_session = getattr(worker, 'has_live_session', None)
                if callable(has_live_session) and has_live_session(account_id):
                    session_secret = {'migrated_host': True, 'captured_at': _utc_now()}
                elif worker and hasattr(worker, 'has_reusable_profile'):
                    try:
                        profile_dir = self.account_manager.profile_dir_for_account(account)
                        if worker.has_reusable_profile(profile_dir):
                            session_secret = {'migrated_host': True, 'captured_at': _utc_now()}
                    except Exception:
                        pass
            if session_secret is None:
                self.account_manager.mark_auth_expired(account_id, 'Google Flow saved session is missing or expired.')
                excluded.add(account_id)
                release_current()
                queue_owned = False
                account = await self._lease_account_when_available(
                    model_id,
                    exclude_account_ids=excluded,
                    priority=True,
                )
                continue

            try:
                result = await self._call_flow_client(scene, account, session_secret)
            except ProviderQuotaError:
                self.account_manager.mark_quota_limited(
                    account_id,
                    model_id=model_id,
                    cooldown_seconds=self.account_cooldown_seconds,
                )
                excluded.add(account_id)
                release_current()
                queue_owned = False
                account = await self._lease_account_when_available(
                    model_id,
                    exclude_account_ids=excluded,
                    priority=True,
                )
                continue
            except ProviderAuthError as exc:
                if self._looks_like_closed_session(exc):
                    logger.warning("Session closed during generation for account %s, recovering...", account_id)
                    excluded.add(account_id)
                    release_current()
                    queue_owned = False
                    account = await self._lease_account_when_available(
                        model_id,
                        exclude_account_ids=excluded,
                        priority=True,
                    )
                    continue
                exc_lower = str(exc).lower()
                redirected_to_signin = 'accounts.google.com' in exc_lower or 'redirected to sign-in' in exc_lower
                if not redirected_to_signin and account_id not in auth_retried:
                    auth_retried.add(account_id)
                    refreshed = await asyncio.to_thread(
                        self.account_manager.try_refresh_session_api,
                        account_id,
                    )
                    if refreshed:
                        continue
                worker = getattr(self.account_manager, 'login_worker', None)
                close_session = getattr(worker, 'close_session', None)
                if callable(close_session):
                    try:
                        await asyncio.to_thread(close_session, account_id)
                    except Exception:
                        pass
                self.account_manager.mark_auth_expired(account_id, str(exc))
                excluded.add(account_id)
                release_current()
                queue_owned = False
                account = await self._lease_account_when_available(
                    model_id,
                    exclude_account_ids=excluded,
                    priority=True,
                )
                continue
            except ProviderError as exc:
                if self._is_recaptcha_challenge(exc):
                    recaptcha_challenges += 1
                    excluded.add(account_id)
                    release_current()
                    queue_owned = False
                    try:
                        account = await self._lease_account_when_available(
                            model_id,
                            exclude_account_ids=excluded,
                            priority=True,
                        )
                    except ProviderError as selection_exc:
                        raise ProviderAuthError(
                            'Google Flow requires manual verification after reCAPTCHA unusual activity on all eligible accounts.'
                        ) from selection_exc
                    continue
                if self._is_model_unavailable(exc):
                    self.account_manager.mark_model_unavailable(account_id, model_id)
                    excluded.add(account_id)
                    release_current()
                    queue_owned = False
                    account = await self._lease_account_when_available(
                        model_id,
                        exclude_account_ids=excluded,
                        priority=True,
                    )
                    continue
                release_current()
                raise
            except RuntimeError as exc:
                release_current()
                if self._is_browser_timeout(exc):
                    raise ProviderTransientError(str(exc)) from exc
                raise
            except Exception:
                release_current()
                raise

            if not isinstance(result, (str, Path)):
                release_current()
                raise ProviderError('Google Flow request adapter returned an invalid output path')
            if not queue_owned:
                release_current()
            return str(result)


# Compatibility import for existing modules while the project migrates from the old API-key provider name.
GoogleMediaProvider = GoogleFlowSessionProvider
def _hidden_subprocess_kwargs() -> dict[str, Any]:
    if os.name != 'nt':
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= int(getattr(subprocess, 'STARTF_USESHOWWINDOW', 1))
    startupinfo.wShowWindow = int(getattr(subprocess, 'SW_HIDE', 0))
    return {
        'creationflags': int(getattr(subprocess, 'CREATE_NO_WINDOW', 0)),
        'startupinfo': startupinfo,
    }
