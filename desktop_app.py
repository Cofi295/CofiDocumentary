from __future__ import annotations

import os
import sys

if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    except Exception:
        pass

import json
import socket
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_PORT = int(os.environ.get("COFI_DOCUMENTARY_PORT", "8878"))
HOST = "127.0.0.1"


def read_json(url: str, timeout: float = 2) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        value = json.load(response)
    return value if isinstance(value, dict) else {}


def read_text(url: str, timeout: float = 2) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        return response.read().decode("utf-8", errors="replace")


def _port_is_open(port: int) -> bool:
    with socket.socket() as connection:
        connection.settimeout(0.35)
        return connection.connect_ex((HOST, port)) == 0


def probe_backend(port: int) -> str:
    """Return ``free``, ``ours`` or ``busy`` for a local TCP port."""
    if not _port_is_open(port):
        return "free"
    try:
        page = read_text(f"http://{HOST}:{port}/")
        if "COFI DOCUMENTARY" in page and 'id="globalCodexDock"' in page:
            return "ours"
    except Exception:
        pass
    return "busy"


def resolve_backend_port(preferred: int = DEFAULT_PORT) -> tuple[int, bool]:
    """Choose a backend port and say whether this process must start it."""
    state = probe_backend(preferred)
    if state == "ours":
        return preferred, False
    if state == "free":
        return preferred, True
    for port in range(preferred + 1, preferred + 20):
        if probe_backend(port) == "free":
            return port, True
    raise RuntimeError(f"Không tìm thấy cổng trống từ {preferred} đến {preferred + 19}.")


@dataclass
class BackendController:
    port: int
    owned: bool
    server: Any = None
    thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.port}"

    def start(self) -> None:
        if not self.owned:
            return
        import uvicorn

        config = uvicorn.Config("app:app", host=HOST, port=self.port, reload=False, log_level="warning")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, name="cofi-documentary-backend", daemon=True)
        self.thread.start()

    def wait_until_ready(self, timeout: float = 120) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if probe_backend(self.port) == "ours":
                return
            if self.owned and self.thread and not self.thread.is_alive():
                break
            time.sleep(0.25)
        raise RuntimeError("Backend CofiDocumentary không khởi động được.")

    def stop(self) -> None:
        if not self.owned or self.server is None:
            return
        self.server.should_exit = True
        if self.thread is not None:
            self.thread.join(timeout=8)


def maximize_with_work_area(window: Any) -> None:
    """Maximize a frameless WinForms window without covering the taskbar."""
    from System import Action
    from System.Drawing import Rectangle
    import System.Windows.Forms as WinForms

    native = window.native

    def _set_work_area() -> None:
        screen = WinForms.Screen.FromControl(native)
        work_area = screen.WorkingArea
        screen_bounds = screen.Bounds
        # WinForms expects MaximizedBounds relative to the selected monitor.
        # Absolute negative coordinates move a window one extra monitor to the
        # left when maximizing on a secondary display.
        native.MaximizedBounds = Rectangle(
            work_area.X - screen_bounds.X,
            work_area.Y - screen_bounds.Y,
            work_area.Width,
            work_area.Height,
        )

    native.Invoke(Action(_set_work_area))
    window.maximize()


class WindowControls:
    def __init__(self, window: Any = None) -> None:
        self._window = window
        self._maximized = False

    def minimize(self) -> None:
        self._window.minimize()

    def toggle_maximize(self) -> bool:
        if self._maximized:
            self._window.restore()
        else:
            maximize_with_work_area(self._window)
        self._maximized = not self._maximized
        return self._maximized

    def close(self) -> None:
        self._window.destroy()


def main() -> None:
    import webview

    port, owned = resolve_backend_port()
    backend = BackendController(port=port, owned=owned)
    backend.start()
    try:
        backend.wait_until_ready()
        webview.settings["ALLOW_DOWNLOADS"] = True
        controls = WindowControls()
        window = webview.create_window(
            "COFI DOCUMENTARY",
            backend.url,
            js_api=controls,
            width=1520,
            height=900,
            min_size=(1100, 680),
            resizable=True,
            background_color="#06101a",
            frameless=True,
            easy_drag=False,
            text_select=True,
        )
        controls._window = window
        webview.start(gui="edgechromium", debug=False)
    finally:
        backend.stop()


if __name__ == "__main__":
    main()
