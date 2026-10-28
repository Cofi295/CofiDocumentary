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


_EXT_FILTER_MAP: dict[str, tuple[str, str, str]] = {
    ".mp4": ("Video MP4 (*.mp4)", "*.mp4", "mp4"),
    ".webm": ("Video WebM (*.webm)", "*.webm", "webm"),
    ".mov": ("Video QuickTime (*.mov)", "*.mov", "mov"),
    ".mkv": ("Video MKV (*.mkv)", "*.mkv", "mkv"),
    ".jpg": ("Ảnh JPEG (*.jpg;*.jpeg)", "*.jpg;*.jpeg", "jpg"),
    ".jpeg": ("Ảnh JPEG (*.jpg;*.jpeg)", "*.jpg;*.jpeg", "jpg"),
    ".png": ("Ảnh PNG (*.png)", "*.png", "png"),
    ".webp": ("Ảnh WebP (*.webp)", "*.webp", "webp"),
    ".gif": ("Ảnh GIF (*.gif)", "*.gif", "gif"),
    ".zip": ("File nén ZIP (*.zip)", "*.zip", "zip"),
    ".wav": ("Âm thanh WAV (*.wav)", "*.wav", "wav"),
    ".mp3": ("Âm thanh MP3 (*.mp3)", "*.mp3", "mp3"),
    ".m4a": ("Âm thanh M4A (*.m4a)", "*.m4a", "m4a"),
    ".srt": ("Phụ đề SRT (*.srt)", "*.srt", "srt"),
    ".vtt": ("Phụ đề WebVTT (*.vtt)", "*.vtt", "vtt"),
    ".json": ("Dữ liệu JSON (*.json)", "*.json", "json"),
    ".md": ("Tài liệu Markdown (*.md)", "*.md", "md"),
    ".txt": ("Tệp văn bản (*.txt)", "*.txt", "txt"),
}

_MIME_TO_EXT: dict[str, str] = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "application/x-subrip": ".srt",
    "text/srt": ".srt",
    "application/json": ".json",
    "text/markdown": ".md",
    "text/plain": ".txt",
}


def resolve_download_dialog_spec(
    result_file_path: str,
    mime_type: str = "",
    uri: str = "",
    content_disposition: str = "",
    all_files_label: str = "Tất cả tệp",
) -> tuple[str, str, str]:
    """Return ``(suggested_filename, default_ext, filter_string)`` for SaveFileDialog."""
    import re
    import urllib.parse

    candidate_name = ""
    if content_disposition:
        m_utf8 = re.search(r"filename\*=UTF-8''([^;\r\n]+)", content_disposition, re.IGNORECASE)
        if m_utf8:
            candidate_name = urllib.parse.unquote(m_utf8.group(1).strip().strip('"'))
        else:
            m_std = re.search(r'filename="?([^";\r\n]+)"?', content_disposition, re.IGNORECASE)
            if m_std:
                candidate_name = m_std.group(1).strip()

    if not candidate_name and result_file_path:
        candidate_name = os.path.basename(str(result_file_path).strip())

    uri_str = str(uri or "").strip()
    uri_path_param = ""
    uri_filename_param = ""
    if uri_str and not uri_str.startswith("data:"):
        try:
            parsed = urllib.parse.urlsplit(uri_str)
            qs = urllib.parse.parse_qs(parsed.query)
            if qs.get("filename"):
                uri_filename_param = str(qs["filename"][0] or "").strip()
            if qs.get("path"):
                uri_path_param = os.path.basename(str(qs["path"][0] or "").replace("\\", "/").strip())
        except Exception:
            pass

    if uri_filename_param:
        candidate_name = uri_filename_param
    elif (not candidate_name or candidate_name.lower() in {"media", "download", "file", "blob"}) and uri_path_param:
        candidate_name = uri_path_param

    mime_clean = str(mime_type or "").split(";", 1)[0].strip().lower()
    if not mime_clean and uri_str.startswith("data:"):
        m_data = re.match(r"^data:([^;,]+)", uri_str, re.IGNORECASE)
        if m_data:
            mime_clean = m_data.group(1).strip().lower()

    _, raw_ext = os.path.splitext(candidate_name)
    ext = raw_ext.lower()
    if ext not in _EXT_FILTER_MAP:
        _, path_ext = os.path.splitext(uri_path_param)
        if path_ext.lower() in _EXT_FILTER_MAP:
            ext = path_ext.lower()
        elif mime_clean in _MIME_TO_EXT:
            ext = _MIME_TO_EXT[mime_clean]

    stem = os.path.splitext(candidate_name)[0].strip() if candidate_name else ""
    if not stem or stem.lower() in {"media", "download", "blob"}:
        if uri_path_param:
            stem = os.path.splitext(uri_path_param)[0].strip() or "download"
        elif ext == ".mp4":
            stem = "video"
        elif ext in {".jpg", ".jpeg", ".png", ".webp"}:
            stem = "thumbnail"
        else:
            stem = "download"

    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", stem).strip(" ._") or "download"
    if ext in _EXT_FILTER_MAP:
        label, pattern, default_ext = _EXT_FILTER_MAP[ext]
        suggested_filename = f"{stem}.{default_ext}" if ext == ".jpeg" else f"{stem}{ext}"
        filter_string = f"{label}|{pattern}|{all_files_label} (*.*)|*.*"
        return suggested_filename, default_ext, filter_string

    suggested_filename = f"{stem}{ext}" if ext else stem
    default_ext = ext.lstrip(".")
    filter_string = f"{all_files_label} (*.*)|*.*"
    return suggested_filename, default_ext, filter_string


def ensure_chosen_file_extension(chosen_path: str, default_ext: str) -> str:
    """Append ``default_ext`` when the user renames a file in SaveFileDialog and omits the extension."""
    cleaned = str(chosen_path or "").strip()
    ext_clean = str(default_ext or "").strip().lstrip(".")
    if not cleaned or not ext_clean:
        return cleaned
    _, current_ext = os.path.splitext(cleaned)
    if not current_ext:
        return f"{cleaned}.{ext_clean}"
    return cleaned


def install_smart_webview_download_handler() -> None:
    """Upgrade pywebview EdgeChrome download dialog so file format/extension is always preserved."""
    try:
        import winreg
        import webview.platforms.edgechromium as ec
        from webview import settings as webview_settings

        def _smart_on_download_starting(self: Any, sender: Any, args: Any) -> None:
            if not webview_settings.get("ALLOW_DOWNLOADS"):
                args.Cancel = True
                return

            dialog = ec.WinForms.SaveFileDialog()
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
                ) as windows_key:
                    dialog.InitialDirectory = winreg.QueryValueEx(
                        windows_key, "{374DE290-123F-4565-9164-39C4925E467B}"
                    )[0]
            except Exception:
                pass

            op = getattr(args, "DownloadOperation", None)
            mime_type = str(getattr(op, "MimeType", "") or "")
            uri = str(getattr(op, "Uri", "") or "")
            content_disposition = str(getattr(op, "ContentDisposition", "") or "")
            all_files_label = "Tất cả tệp"
            try:
                all_files_label = self.pywebview_window.localization.get(
                    "windows.fileFilter.allFiles", "Tất cả tệp"
                )
            except Exception:
                pass

            suggested_filename, default_ext, filter_string = resolve_download_dialog_spec(
                str(getattr(args, "ResultFilePath", "") or ""),
                mime_type=mime_type,
                uri=uri,
                content_disposition=content_disposition,
                all_files_label=all_files_label,
            )

            dialog.Filter = filter_string
            dialog.FilterIndex = 1
            dialog.RestoreDirectory = True
            dialog.AddExtension = True
            if default_ext:
                dialog.DefaultExt = default_ext
            dialog.FileName = suggested_filename

            result = dialog.ShowDialog(self.form)
            if result == ec.WinForms.DialogResult.OK:
                args.ResultFilePath = ensure_chosen_file_extension(dialog.FileName, default_ext)
            else:
                args.Cancel = True

        ec.EdgeChrome.on_download_starting = _smart_on_download_starting
    except Exception:
        pass


def main() -> None:
    import webview

    port, owned = resolve_backend_port()
    backend = BackendController(port=port, owned=owned)
    backend.start()
    try:
        backend.wait_until_ready()
        webview.settings["ALLOW_DOWNLOADS"] = True
        install_smart_webview_download_handler()
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
