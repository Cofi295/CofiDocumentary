from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_chat_dock_cannot_be_dragged_and_stays_at_right_edge():
    script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
    assert "initGlobalCodexDrag" not in script
    assert "dock.style.left =" not in script
    assert ".global-codex-dock { position: fixed; right: 0 !important; left: auto !important; top: 0 !important; bottom: 0 !important;" in styles
    assert ".global-codex-head {" in styles
    assert "cursor: move" not in styles.split(".global-codex-head {")[1].split("}")[0]


def test_desktop_chat_sits_below_window_controls():
    styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
    titlebar = styles.split("body.desktop-mode .desktop-titlebar {")[1].split("}")[0]
    dock = styles.split("body.desktop-mode .global-codex-dock {")[1].split("}")[0]
    panel = styles.split("body.desktop-mode .global-codex-panel {")[1].split("}")[0]
    assert "height: 34px" in titlebar
    assert "top: 34px !important" in dock
    assert "height: calc(100vh - 34px)" in panel


def test_chat_message_text_overrides_legacy_webview_selection_block():
    styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    selector = styles.split(".producer-codex-messages .producer-codex-message {")[1].split("}")[0]
    assert "-webkit-user-select: text !important" in selector
    assert "user-select: text !important" in selector
    assert "20260913-chat-text-select" in html


def test_chat_messages_keep_their_content_height_and_fit_the_dock():
    styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")
    panel = styles.rsplit(".global-codex-panel {", 1)[1].split("}", 1)[0]
    dock_messages = styles.rsplit(".global-codex-messages {", 1)[1].split("}", 1)[0]
    message = styles.rsplit(".global-codex-messages .producer-codex-message {", 1)[1].split("}", 1)[0]
    assert "grid-template-columns: minmax(0, 1fr)" in panel
    assert "width: 100%" in dock_messages
    assert "min-width: 0" in dock_messages
    assert "box-sizing: border-box" in dock_messages
    assert "flex: 0 0 auto" in message
    assert "max-width: 94%" in message
    assert "height: auto" in message
