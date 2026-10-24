from __future__ import annotations

import http.server
import json
import logging
import threading
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_THEME_VER = 0x5A
DEFAULT_SITE_KEY = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"
BRIDGE_PORT = 18923


def _serialize_theme(plaintext: str) -> str:
    encoded: list[str] = []
    for ch in plaintext:
        code = ord(ch)
        if code > 0x7F:
            escaped = f"\\u{code:04x}"
            for c in escaped:
                encoded.append(f"{(ord(c) ^ _THEME_VER):02x}")
        else:
            encoded.append(f"{(code ^ _THEME_VER):02x}")
    return "".join(encoded)


def _deserialize_theme(hex_str: str) -> str:
    bytes_arr: list[int] = []
    for i in range(0, len(hex_str), 2):
        byte = int(hex_str[i : i + 2], 16)
        bytes_arr.append(byte ^ _THEME_VER)
    return bytes(bytes_arr).decode("utf-8", errors="ignore")


class _BridgeHandler(http.server.BaseHTTPRequestHandler):
    bridge: ExtensionAuthBridge

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self) -> None:
        self.bridge.last_contact = time.time()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if self.path.startswith("/sync/status"):
            ext_id = str(self.headers.get("X-Ext-Id") or "").strip()
            if ext_id:
                self.bridge.record_extension_seen(ext_id)
            self.wfile.write(b'{"status":"ok"}')
        elif self.path.startswith("/sync/config"):
            cfg = {
                "recaptcha_ent_key": DEFAULT_SITE_KEY,
                "recaptcha_url": "https://flow.google.com/about",
                "recaptcha_script_url": f"https://www.google.com/recaptcha/enterprise.js?render={DEFAULT_SITE_KEY}",
                "recaptcha_action": "IMAGE_GENERATION",
                "canAutoOpen": True,
                "isFlow": True,
                "domains": [
                    "https://flow.google.com/*",
                    "https://labs.google/fx/*",
                    "https://labs.google/*",
                    "https://aisandbox-pa.googleapis.com/*",
                ],
            }
            self.wfile.write(json.dumps(cfg).encode("utf-8"))
        elif self.path.startswith("/sync/theme"):
            ext_id = str(self.headers.get("X-Ext-Id") or "").strip()
            tab_status = str(self.headers.get("X-Tab-Status") or "").strip().lower()
            self.bridge.record_extension_poll(ext_id, tab_status)
            task = self.bridge.pop_pending_task(ext_id=ext_id, tab_status=tab_status)
            if task is not None:
                enc = _serialize_theme(json.dumps(task))
                self.wfile.write(json.dumps({"d": enc}).encode("utf-8"))
            else:
                self.wfile.write(b"{}")
        else:
            self.wfile.write(b"{}")

    def do_POST(self) -> None:
        self.bridge.last_contact = time.time()
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

        if self.path.startswith("/sync/render"):
            try:
                data = json.loads(body.decode("utf-8"))
                enc = data.get("d")
                if enc:
                    dec = _deserialize_theme(enc)
                    payload = json.loads(dec)
                    req_id = payload.get("r")
                    token = payload.get("t")
                    err = payload.get("e")
                    self.bridge.complete_task(req_id, token, err)
            except Exception as exc:
                logger.warning("Extension render decoding error: %s", exc)


class ExtensionAuthBridge:
    def __init__(self, port: int = BRIDGE_PORT) -> None:
        self.port = port
        self.server: http.server.ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._pending_tasks: list[dict[str, Any]] = []
        self._waiting_results: dict[str, tuple[threading.Event, list[Any]]] = {}
        self._ext_states: dict[str, dict[str, Any]] = {}
        self.last_contact: float = 0.0

    def record_extension_seen(self, ext_id: str) -> None:
        if not ext_id:
            return
        with self._lock:
            state = self._ext_states.setdefault(ext_id, {})
            state["last_seen"] = time.time()

    def record_extension_poll(self, ext_id: str, tab_status: str) -> None:
        if not ext_id:
            return
        with self._lock:
            state = self._ext_states.setdefault(ext_id, {})
            state["last_seen"] = time.time()
            state["tab_status"] = tab_status

    def start(self) -> bool:
        with self._lock:
            if self.server is not None:
                return True
            try:
                handler = type("ConfiguredBridgeHandler", (_BridgeHandler,), {"bridge": self})
                self.server = http.server.ThreadingHTTPServer(("127.0.0.1", self.port), handler)
                self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="glabs-extension-bridge")
                self.thread.start()
                logger.info("ExtensionAuthBridge running on 127.0.0.1:%s", self.port)
                return True
            except OSError as exc:
                logger.warning("ExtensionAuthBridge port %s unavailable (maybe G-Labs running): %s", self.port, exc)
                self.server = None
                self.thread = None
                return False

    def stop(self) -> None:
        with self._lock:
            if self.server:
                try:
                    self.server.shutdown()
                    self.server.server_close()
                except Exception:
                    pass
                self.server = None
                self.thread = None

    def is_connected(self) -> bool:
        return self.server is not None

    def pop_pending_task(self, *, ext_id: str = "", tab_status: str = "") -> dict[str, Any] | None:
        now = time.time()
        with self._lock:
            if not self._pending_tasks:
                return None
            # If this extension instance reports its Flow tab is closed/missing,
            # check whether another active extension instance has an open Flow tab
            # or if the task was just queued (< 4s ago) so the worker tab can claim it first.
            if tab_status in {"closed", "missing"}:
                has_open_peer = any(
                    peer_id != ext_id
                    and peer.get("tab_status") in {"open", "ready"}
                    and (now - float(peer.get("last_seen") or 0.0)) < 6.0
                    for peer_id, peer in self._ext_states.items()
                )
                oldest_age = now - float(self._pending_tasks[0].get("_queued_at") or now)
                if has_open_peer or oldest_age < 4.0:
                    return None
            task = dict(self._pending_tasks.pop(0))
            task.pop("_queued_at", None)
            return task

    def complete_task(self, req_id: str | None, token: str | None, error: str | None) -> None:
        if not req_id:
            return
        with self._lock:
            holder = self._waiting_results.get(req_id)
            if holder:
                event, container = holder
                container.append((token, error))
                event.set()

    def get_token(self, site_key: str = DEFAULT_SITE_KEY, action: str = "IMAGE_GENERATION", timeout: float = 12.0) -> str | None:
        if self.server is None:
            self.start()
        if self.server is None:
            return None
        req_id = str(uuid.uuid4())
        event = threading.Event()
        container: list[Any] = []

        with self._lock:
            self._waiting_results[req_id] = (event, container)
            self._pending_tasks.append({
                "r": req_id,
                "s": site_key,
                "a": action,
                "_queued_at": time.time(),
            })

        finished = event.wait(timeout)
        with self._lock:
            self._waiting_results.pop(req_id, None)

        if not finished or not container:
            return None

        token, err = container[0]
        if err:
            logger.warning("Extension mint reported error: %s", err)
            return None
        return str(token) if token else None


_GLOBAL_BRIDGE: ExtensionAuthBridge | None = None
_BRIDGE_LOCK = threading.Lock()


def get_extension_bridge() -> ExtensionAuthBridge:
    global _GLOBAL_BRIDGE
    with _BRIDGE_LOCK:
        if _GLOBAL_BRIDGE is None:
            _GLOBAL_BRIDGE = ExtensionAuthBridge()
            _GLOBAL_BRIDGE.start()
        return _GLOBAL_BRIDGE


get_auth_bridge = get_extension_bridge

