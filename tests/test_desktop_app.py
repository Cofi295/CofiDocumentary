from __future__ import annotations

import sys
import types
from unittest.mock import Mock
from pathlib import Path

import desktop_app


def test_probe_backend_recognizes_documentary_health(monkeypatch) -> None:
    monkeypatch.setattr(
        desktop_app,
        "read_text",
        lambda url, timeout=2: '<title>COFI DOCUMENTARY</title><div id="globalCodexDock">',
    )

    assert desktop_app.probe_backend(8878) == "ours"


def test_probe_backend_rejects_unrelated_page(monkeypatch) -> None:
    monkeypatch.setattr(desktop_app, "read_text", lambda url, timeout=2: "another local app")

    assert desktop_app.probe_backend(8878) == "busy"


def test_resolve_backend_port_reuses_existing_documentary(monkeypatch) -> None:
    monkeypatch.setattr(desktop_app, "probe_backend", lambda port: "ours" if port == 8878 else "free")

    assert desktop_app.resolve_backend_port(8878) == (8878, False)


def test_resolve_backend_port_skips_unrelated_listener(monkeypatch) -> None:
    states = {8878: "busy", 8879: "busy", 8880: "free"}
    monkeypatch.setattr(desktop_app, "probe_backend", lambda port: states.get(port, "free"))

    assert desktop_app.resolve_backend_port(8878) == (8880, True)


def test_backend_controller_only_stops_owned_server() -> None:
    external = desktop_app.BackendController(port=8878, owned=False)
    external.server = Mock()
    external.stop()
    assert external.server.should_exit is not True

    owned = desktop_app.BackendController(port=8879, owned=True)
    owned.server = Mock()
    owned.thread = Mock()
    owned.stop()
    assert owned.server.should_exit is True
    owned.thread.join.assert_called_once()


def test_window_controls_call_native_window(monkeypatch) -> None:
    window = Mock()
    fit_to_work_area = Mock()
    monkeypatch.setattr(desktop_app, "maximize_with_work_area", fit_to_work_area)
    controls = desktop_app.WindowControls(window)
    assert not hasattr(controls, "window")
    controls.minimize()
    controls.toggle_maximize()
    controls.toggle_maximize()
    controls.close()
    window.minimize.assert_called_once()
    fit_to_work_area.assert_called_once_with(window)
    window.maximize.assert_not_called()
    window.restore.assert_called_once()
    window.destroy.assert_called_once()


def test_desktop_shell_is_frameless_and_browser_controls_are_conditional() -> None:
    source = Path(desktop_app.__file__).read_text(encoding="utf-8")
    html = (Path(desktop_app.__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
    assert "frameless=True" in source
    assert "easy_drag=False" in source
    assert "text_select=True" in source
    assert 'id="desktopTitlebar"' in html
    assert 'id="desktopMinimizeBtn"' in html
    assert 'id="desktopMaximizeBtn"' in html
    assert 'id="desktopCloseBtn"' in html


def test_maximize_uses_void_winforms_delegate() -> None:
    source = Path(desktop_app.__file__).read_text(encoding="utf-8")
    assert "from System import Action" in source
    assert "native.Invoke(Action(_set_work_area))" in source
    assert "Func[Type]" not in source


def test_maximize_applies_work_area_before_maximizing(monkeypatch) -> None:
    screen_bounds = types.SimpleNamespace(X=-1920, Y=0)
    working_area = types.SimpleNamespace(X=-1920, Y=0, Width=1920, Height=1032)

    class FakeAction:
        def __init__(self, callback):
            self.callback = callback

        def __call__(self):
            return self.callback()

    system = types.ModuleType("System")
    system.__path__ = []
    system.Action = FakeAction
    windows = types.ModuleType("System.Windows")
    windows.__path__ = []
    forms = types.ModuleType("System.Windows.Forms")
    forms.Screen = types.SimpleNamespace(
        FromControl=lambda native: types.SimpleNamespace(
            Bounds=screen_bounds,
            WorkingArea=working_area,
        )
    )
    drawing = types.ModuleType("System.Drawing")
    drawing.Rectangle = lambda x, y, width, height: (x, y, width, height)
    system.Windows = windows
    windows.Forms = forms
    monkeypatch.setitem(sys.modules, "System", system)
    monkeypatch.setitem(sys.modules, "System.Drawing", drawing)
    monkeypatch.setitem(sys.modules, "System.Windows", windows)
    monkeypatch.setitem(sys.modules, "System.Windows.Forms", forms)

    native = types.SimpleNamespace(MaximizedBounds=None)

    def invoke(action) -> None:
        action()

    native.Invoke = invoke
    window = Mock()
    window.native = native

    desktop_app.maximize_with_work_area(window)

    assert native.MaximizedBounds == (0, 0, 1920, 1032)
    window.maximize.assert_called_once_with()


def test_resolve_download_dialog_spec_preserves_video_and_image_types() -> None:
    fname, ext, flt = desktop_app.resolve_download_dialog_spec(
        r"C:\Users\user\Downloads\media",
        mime_type="video/mp4",
        uri="http://127.0.0.1:8878/api/jobs/job123/media?path=release/video.mp4&download=1&filename=video_job123.mp4",
    )
    assert fname == "video_job123.mp4"
    assert ext == "mp4"
    assert flt.startswith("Video MP4 (*.mp4)|*.mp4|")

    fname_img, ext_img, flt_img = desktop_app.resolve_download_dialog_spec(
        r"C:\Users\user\Downloads\thumbnail_job123_v1.jpg",
        mime_type="image/jpeg",
        uri="data:image/jpeg;base64,/9j/4AAQ",
    )
    assert fname_img == "thumbnail_job123_v1.jpg"
    assert ext_img == "jpg"
    assert flt_img.startswith("Ảnh JPEG (*.jpg;*.jpeg)|*.jpg;*.jpeg|")


def test_ensure_chosen_file_extension_restores_deleted_extension() -> None:
    assert desktop_app.ensure_chosen_file_extension(r"C:\video_duong_nuu_hoa", "mp4") == r"C:\video_duong_nuu_hoa.mp4"
    assert desktop_app.ensure_chosen_file_extension(r"C:\thumb_1", "jpg") == r"C:\thumb_1.jpg"
    assert desktop_app.ensure_chosen_file_extension(r"C:\already_named.mp4", "mp4") == r"C:\already_named.mp4"

