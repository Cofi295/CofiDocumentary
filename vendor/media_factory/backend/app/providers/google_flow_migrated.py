from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from ..watermark_remover import strip_gemini_watermark
from .base import (
    ProviderAuthError,
    ProviderError,
    ProviderQuotaError,
    scene_output_directory,
    scene_output_stem,
)
from .auth_bridge import get_extension_bridge, DEFAULT_SITE_KEY


FLOW_API_ROOT = "https://aisandbox-pa.googleapis.com/v1"
FLOW_AUTH_SESSION_URL = "https://labs.google/fx/api/auth/session"
FLOW_MIGRATED_SESSION_URL = "https://flow.google.com/fx/api/auth/session"

_XSSI_PREFIX = ")]}'"
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
_UUID_SEARCH_RE = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
_PUBLIC_ERROR_RE = re.compile(r"PUBLIC_ERROR_[A-Z0-9_]+")

SUBMIT_RPC = "eb1hJf"
STATUS_RPCS = {"jwpduf", "as29s"}
UPLOAD_RPC = "maseQ"
IMAGE_SUBMIT_RPC = "ogiZ0b"

STATUS_RUNNING = 2
STATUS_DONE = 3
STATUS_SUBMITTED = 6

READY_ANCHOR = ".settings-trigger-button"
OVERLAY = ".cdk-overlay-pane"
RADIOGROUP = "[role='radiogroup']"
RADIO = "[role='radio']"
MENU_ITEM = "[role='menuitem']"
COMPOSER = "[contenteditable='true']"
TOOLBAR_ADD = "xpath=//button[.//mat-icon[normalize-space()='add']][not(ancestor::flow-prompt-box)]"
EMPTY_CHIP = "flow-prompt-box button.empty-chip"
BOUND_CHIP = "flow-prompt-box button.chip-container:has(img)"
PICKER = "flow-add-menu-popover-content"
MOBILE_PICKER = "[role='dialog'].mobile-overlay"
PICKER_SEARCH = "input[type='text']"
PICKER_OPTION = "button.asset-item[role='option']"
PICKER_CONFIRM = "button.detail-add-to-prompt-btn"
MENTION_CHIP = ".mention-chip"


def _flow_public_error_codes(text: str) -> tuple[str, ...]:
    """Return stable, de-duplicated public Flow error codes from a batch reply."""
    if not text:
        return ()
    return tuple(dict.fromkeys(_PUBLIC_ERROR_RE.findall(text)))


@dataclass(frozen=True)
class MigratedGeneration:
    workflow_id: str
    project_id: str
    media_id: str
    status: int | None
    video_url: str | None = None
    poster_url: str | None = None
    size_bytes: int | None = None

    @property
    def is_done(self) -> bool:
        return self.status == STATUS_DONE

    @property
    def is_running(self) -> bool:
        return self.status in {STATUS_RUNNING, STATUS_SUBMITTED}

    @property
    def is_failed(self) -> bool:
        return self.status is not None and not self.is_done and not self.is_running


@dataclass(frozen=True)
class MigratedImage:
    media_id: str
    workflow_id: str
    project_id: str
    seed: int
    prompt: str
    image_url: str
    dimensions: tuple[int, int]
    display_name: str | None = None


def _as_list(value: object) -> list[Any] | None:
    return value if isinstance(value, list) else None


def _at(value: object, *path: int) -> Any:
    current: Any = value
    for index in path:
        items = _as_list(current)
        if items is None or index >= len(items):
            return None
        current = items[index]
    return current


def _url(value: Any) -> str | None:
    return value if isinstance(value, str) and value.startswith("https://") else None


def parse_frames(text: str) -> list[tuple[str, Any]]:
    if not text:
        return []
    body = text.lstrip()
    if body.startswith(_XSSI_PREFIX):
        body = body[len(_XSSI_PREFIX) :]
    decoder = json.JSONDecoder()
    frames: list[tuple[str, Any]] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line.startswith("["):
            continue
        try:
            decoded, _ = decoder.raw_decode(line)
        except ValueError:
            continue
        chunk = _as_list(decoded)
        if chunk is None:
            continue
        for raw_item in chunk:
            item = _as_list(raw_item)
            if (
                item is not None
                and len(item) >= 3
                and item[0] == "wrb.fr"
                and isinstance(item[1], str)
                and isinstance(item[2], str)
            ):
                try:
                    payload = json.loads(item[2])
                except ValueError:
                    payload = None
                frames.append((item[1], payload))
    return frames


def _walk_records(node: object) -> list[list[Any]]:
    items = _as_list(node)
    if items is None:
        return []
    found: list[list[Any]] = []
    if (
        len(items) >= 6
        and items[3] == "CAE"
        and all(isinstance(items[index], str) and _UUID_RE.match(items[index]) for index in (0, 1, 2))
    ):
        found.append(items)
    for child in items:
        found.extend(_walk_records(child))
    return found


def _walk_lists(node: object) -> list[list[Any]]:
    items = _as_list(node)
    if items is None:
        return []
    found = [items]
    for child in items:
        found.extend(_walk_lists(child))
    return found


def generation_records(rpcid: str, payload: Any) -> list[MigratedGeneration]:
    records: list[MigratedGeneration] = []
    for rec in _walk_records(payload):
        status_cell = _as_list(_at(rec, 5, 8))
        status: Any = status_cell[0] if status_cell else None
        size = _at(rec, 5, 13)
        records.append(
            MigratedGeneration(
                workflow_id=rec[0],
                project_id=rec[1],
                media_id=rec[2],
                status=status if isinstance(status, int) else None,
                video_url=_url(_at(rec, 7, 0, 8)),
                poster_url=_url(_at(rec, 5, 10)),
                size_bytes=size if isinstance(size, int) else None,
            )
        )
    if not records and rpcid in {SUBMIT_RPC, *STATUS_RPCS}:
        raise ProviderError(f"Google Flow migrated response {rpcid} did not contain a generation record.")
    return records


def image_records(rpcid: str, payload: Any) -> list[MigratedImage]:
    """Decode completed images returned by Flow's migrated image composer."""
    workflow_meta: dict[str, tuple[str, str | None]] = {}
    lists = _walk_lists(payload)
    for node in lists:
        if len(node) < 5 or not isinstance(node[0], str) or not _UUID_RE.match(node[0]):
            continue
        meta = _as_list(node[3])
        project_id = node[4]
        if meta is None or not isinstance(project_id, str) or not _UUID_RE.match(project_id):
            continue
        title = meta[0] if meta and isinstance(meta[0], str) else None
        workflow_meta[node[0]] = (project_id, title)

    records: list[MigratedImage] = []
    for node in lists:
        if len(node) < 7:
            continue
        media_id, workflow_id = node[0], node[2]
        if not (
            isinstance(media_id, str)
            and _UUID_RE.match(media_id)
            and isinstance(workflow_id, str)
            and _UUID_RE.match(workflow_id)
        ):
            continue
        container = _as_list(node[6])
        details = _as_list(_at(container, 0)) if container is not None else None
        dims = _as_list(_at(container, 2)) if container is not None else None
        if details is None or dims is None or len(details) <= 13 or len(dims) < 2:
            continue
        image_url = _url(details[13])
        seed, prompt = _at(details, 1), _at(details, 7)
        width, height = dims[0], dims[1]
        meta = workflow_meta.get(workflow_id)
        if not (
            image_url
            and isinstance(seed, int)
            and isinstance(prompt, str)
            and isinstance(width, int)
            and isinstance(height, int)
            and meta is not None
        ):
            continue
        records.append(
            MigratedImage(
                media_id=media_id,
                workflow_id=workflow_id,
                project_id=meta[0],
                seed=seed,
                prompt=prompt,
                image_url=image_url,
                dimensions=(width, height),
                display_name=meta[1],
            )
        )
    if not records:
        raise ProviderError(f"Google Flow migrated response {rpcid} did not contain a completed image record.")
    return records


def _rpcid(url: str) -> str | None:
    match = re.search(r"[?&]rpcids=([A-Za-z0-9]+)", url)
    return match.group(1) if match else None


def _exact(text: str) -> re.Pattern[str]:
    return re.compile(r"^\s*" + re.escape(text) + r"\s*$")


def _ligature(page: Any, name: str) -> Any:
    return page.locator("mat-icon").filter(has_text=_exact(name))


def _browser_post_json(page: Any, url: str, access_token: str | None, body: dict[str, Any]) -> dict[str, Any]:
    if not hasattr(page, "evaluate"):
        raise ProviderError("Page object does not support evaluate.")
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
        {"url": url, "accessToken": access_token, "body": body},
    )
    if not isinstance(result, dict) or not result.get("ok"):
        payload = result.get("payload") if isinstance(result, dict) and isinstance(result.get("payload"), dict) else {}
        err = payload.get("error") if isinstance(payload, dict) else None
        msg = (
            (err.get("message") if isinstance(err, dict) else None)
            or (err.get("status") if isinstance(err, dict) else None)
            or payload.get("message")
            or ""
        )
        status = result.get("status") if isinstance(result, dict) else "unknown"
        status_int = int(status) if isinstance(status, (int, str)) and str(status).isdigit() else 0
        upper_msg = str(msg).upper()
        if "RECAPTCHA" in upper_msg or "UNUSUAL_ACTIVITY" in upper_msg:
            raise ProviderError(f"Direct request to {url} failed with HTTP {status}: {msg}")
        if status_int == 401 or any(m in upper_msg for m in ("UNAUTHENTICATED", "INVALID AUTHENTICATION", "ACCESS_TOKEN_REFRESH_NEEDED")):
            raise ProviderAuthError(f"Direct request to {url} failed with HTTP {status}: {msg}")
        if status_int == 403:
            if any(m in upper_msg for m in ("PERMISSION_DENIED", "ACCESS_DENIED")):
                raise ProviderAuthError(f"Direct request to {url} failed with HTTP {status}: {msg}")
            raise ProviderError(f"Direct request to {url} failed with HTTP {status}: {msg}")
        if status_int == 429 or any(m in upper_msg for m in ("RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED")):
            raise ProviderQuotaError(f"Direct request to {url} failed with HTTP {status}: {msg}")
        raise ProviderError(f"Direct request to {url} failed with HTTP {status}: {msg}")
    return result.get("payload") or {}


def _mint_recaptcha_token(page: Any, action: str) -> str:
    best_token: str | None = None
    last_detail = "unknown"

    # 1. Mint directly in the account's own browser tab first (~0.5s, parallel across Chrome instances)
    if hasattr(page, "evaluate"):
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
              return {token: null, error: 'Service not ready after waiting'};
            }
            await new Promise((resolve) => enterprise.ready(resolve));
            const token = await enterprise.execute(siteKey, {action});
            return {token, error: null};
          } catch (error) {
            return {token: null, error: String(error)};
          }
        }
        """
        try:
            for attempt in range(2):
                res = page.evaluate(script, action)
                if isinstance(res, dict) and res.get("token"):
                    candidate = str(res["token"])
                    best_token = candidate
                    if len(candidate) >= 1000 or not hasattr(page, "context"):
                        return candidate
                    if attempt == 0:
                        if hasattr(page, "wait_for_timeout"):
                            page.wait_for_timeout(600)
                        else:
                            time.sleep(0.6)
                        continue
                elif isinstance(res, dict):
                    last_detail = str(res.get("error") or "unknown")
        except Exception as exc:
            last_detail = str(exc)

    # 2. Fallback to extension bridge on port 18923 if page.evaluate did not yield a full token
    if hasattr(page, "context"):
        bridge = get_extension_bridge()
        if bridge.is_connected():
            tok = bridge.get_token(DEFAULT_SITE_KEY, action, timeout=6.0)
            if tok and len(tok) >= 1000:
                return tok

    if best_token:
        return best_token
    if not hasattr(page, "evaluate"):
        raise ProviderError("Cannot mint reCAPTCHA: Page object does not support evaluate.")
    raise ProviderError(f"Google Flow reCAPTCHA could not be minted: {last_detail}")


def _get_page_access_token(page: Any, scene: dict[str, Any] | None = None) -> str:
    # Fast-path: use fresh token already resolved by caller (cached for 180s per account)
    if scene and isinstance(scene, dict):
        tok = scene.get("_access_token")
        if tok and isinstance(tok, str) and tok.startswith("ya29."):
            return tok

    # Try fetching fresh token from live session cookies via context.request
    context = getattr(page, "context", None)
    req_holder = context if context is not None and hasattr(context, "request") else page
    if hasattr(req_holder, "request"):
        req = getattr(req_holder, "request")
        if hasattr(req, "get"):
            for session_url in (FLOW_AUTH_SESSION_URL, FLOW_MIGRATED_SESSION_URL):
                try:
                    res = req.get(session_url)
                    if getattr(res, "ok", False):
                        data = res.json()
                        if isinstance(data, dict) and str(data.get("error") or "").upper() != "ACCESS_TOKEN_REFRESH_NEEDED":
                            tok = data.get("access_token") or data.get("accessToken")
                            if tok and isinstance(tok, str) and tok.startswith("ya29."):
                                return tok
                except Exception:
                    pass

    if hasattr(page, "evaluate"):
        try:
            token = page.evaluate(
                """
                async () => {
                  const urls = [
                    window.location && window.location.origin ? `${window.location.origin}/fx/api/auth/session` : null,
                    'https://flow.google.com/fx/api/auth/session',
                    'https://labs.google/fx/api/auth/session'
                  ].filter(Boolean);
                  for (const url of urls) {
                    try {
                      const res = await fetch(url, { credentials: 'include' });
                      if (res.ok) {
                        const data = await res.json();
                        if (data && data.error !== 'ACCESS_TOKEN_REFRESH_NEEDED') {
                          const tok = data.access_token || data.accessToken || null;
                          if (tok && String(tok).startsWith('ya29.')) return String(tok);
                        }
                      }
                    } catch (_) {}
                  }
                  return null;
                }
                """
            )
            if token and isinstance(token, str) and token.startswith("ya29."):
                return token
        except Exception:
            pass

    return "migrated-access-token"


def _find_nested_string(value: Any, key: str) -> str | None:
    if isinstance(value, dict):
        direct = value.get(key)
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        for nested in value.values():
            found = _find_nested_string(nested, key)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_nested_string(nested, key)
            if found:
                return found
    return None


class MigratedFlowVideoDriver:
    """Drive flow.google.com's Angular composer for start-frame video jobs."""

    MODEL_LABELS = {
        "veo_31_fast": ("Veo 3.1 - Fast", ("Lower Priority",)),
        "veo_31_lite": ("Veo 3.1 - Lite", ("Lower Priority",)),
        "veo_31_lite_relaxed": ("Lower Priority", ()),
        "veo_31_quality": ("Veo 3.1 - Quality", ()),
        "omni_flash": ("Omni 1.1 Flash", ()),
    }

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.records: dict[str, MigratedGeneration] = {}
        self._observed_pages: set[int] = set()

    def install_observer(self, page: Any) -> None:
        key = id(page)
        if key in self._observed_pages:
            return

        def on_response(response: Any) -> None:
            url = str(getattr(response, "url", ""))
            if "batchexecute" not in url or int(getattr(response, "status", 0) or 0) != 200:
                return
            try:
                text = response.text()
            except Exception:
                return
            for rpcid, payload in parse_frames(text):
                if rpcid not in {SUBMIT_RPC, *STATUS_RPCS}:
                    continue
                try:
                    parsed = generation_records(rpcid, payload)
                except ProviderError:
                    continue
                for record in parsed:
                    current = self.records.get(record.workflow_id)
                    if current is None or record.is_done or record.is_failed or record.video_url:
                        self.records[record.workflow_id] = record

        page.on("response", on_response)
        self._observed_pages.add(key)

    @staticmethod
    def _dismiss_obstructions(page: Any) -> None:
        try:
            bar = page.locator("#glue-cookie-notification-bar-1, .glue-cookie-notification-bar").first
            if bar.is_visible():
                reject = bar.locator("button.glue-cookie-notification-bar__reject").first
                if reject.count():
                    reject.click(timeout=3000)
        except Exception:
            pass
        try:
            pressed = page.locator("button.agent-mode-chip[aria-pressed='true']").first
            if pressed.count() and pressed.is_visible():
                pressed.click(timeout=4000)
                page.wait_for_timeout(300)
        except Exception:
            pass
        try:
            dialog = page.locator("[role='dialog']").first
            if dialog.is_visible():
                close = dialog.locator("button").filter(has=_ligature(page, "close")).first
                if close.count():
                    close.click(timeout=3000)
        except Exception:
            pass

    def _open_settings(self, page: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(3):
            self._dismiss_obstructions(page)
            trigger = page.locator(READY_ANCHOR).first
            trigger.wait_for(state="visible", timeout=10_000)
            try:
                trigger.click(timeout=5000)
                group = page.locator(RADIOGROUP).first
                group.wait_for(state="visible", timeout=8000)
                return group.locator("xpath=ancestor::div[contains(@class, 'cdk-overlay-pane')][1]")
            except Exception as exc:
                last_error = exc
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
                if attempt < 2:
                    page.wait_for_timeout(1500)
        assert last_error is not None
        raise last_error

    @staticmethod
    def _select_radio(page: Any, pane: Any, *, ligature: str | None = None, text: str | None = None, optional: bool = False) -> None:
        radios = pane.locator(RADIO)
        target = (
            radios.filter(has=_ligature(page, str(ligature))).first
            if ligature
            else radios.filter(has_text=_exact(str(text))).first
        )
        if not target.count():
            if optional:
                return
            wanted = ligature or text
            raise ProviderError(f"Google Flow migrated settings do not offer {wanted!r}.")
        if target.get_attribute("aria-checked") == "true":
            return
        target.click(timeout=4000)
        page.wait_for_timeout(200)
        if target.get_attribute("aria-checked") != "true":
            raise ProviderError(f"Google Flow migrated setting {ligature or text!r} did not become selected.")

    def _select_model(self, page: Any, pane: Any, model_id: str) -> None:
        matcher = self.MODEL_LABELS.get(model_id)
        if matcher is None:
            raise ProviderError(f"Unsupported migrated Google Flow video model: {model_id!r}")
        contains, excludes = matcher
        button = pane.locator("button").filter(has=_ligature(page, "arrow_drop_down")).first
        if not button.count():
            raise ProviderError("Google Flow migrated model picker is unavailable.")

        def matches(value: str) -> bool:
            folded = value.casefold()
            return contains.casefold() in folded and all(item.casefold() not in folded for item in excludes)

        current = str(button.text_content() or "")
        if matches(current):
            return
        button.click(timeout=4000)
        items = page.locator(MENU_ITEM)
        items.first.wait_for(state="visible", timeout=5000)
        offered = [str(value or "").strip() for value in items.all_text_contents()]
        hits = [index for index, value in enumerate(offered) if matches(value)]
        if len(hits) != 1:
            page.keyboard.press("Escape")
            raise ProviderError(
                f"Google Flow migrated model {model_id!r} is unavailable or ambiguous; offered: {', '.join(offered)}"
            )
        items.nth(hits[0]).click(timeout=4000)
        page.wait_for_timeout(250)

    @staticmethod
    def _close_settings(page: Any) -> None:
        for _ in range(3):
            if not page.locator(f"{OVERLAY}:visible").count():
                break
            page.keyboard.press("Escape")
            page.wait_for_timeout(250)

    def configure(self, page: Any, scene: dict[str, Any]) -> None:
        pane = self._open_settings(page)
        try:
            self._select_radio(page, pane, ligature="videocam")
            self._select_radio(page, pane, ligature="crop_free")
            self._select_model(page, pane, str(scene.get("model") or ""))
            aspect = str(scene.get("aspect_ratio") or "16:9")
            self._select_radio(page, pane, ligature="crop_9_16" if aspect == "9:16" else "crop_16_9")
            duration = int(scene.get("duration_seconds") or 8)
            self._select_radio(page, pane, text=f"{duration}s", optional=True)
            self._select_radio(page, pane, text="x1", optional=True)
        finally:
            self._close_settings(page)

    @staticmethod
    def _picker(page: Any) -> Any:
        mobile = page.locator(f"{MOBILE_PICKER}:visible").last
        if mobile.count() and mobile.is_visible():
            return mobile
        return page.locator(OVERLAY).filter(has=page.locator(PICKER)).last

    @classmethod
    def _wait_for_picker(cls, page: Any, timeout_ms: int = 8000) -> Any:
        deadline = time.monotonic() + max(0, timeout_ms) / 1000.0
        while time.monotonic() < deadline:
            mobile = page.locator(f"{MOBILE_PICKER}:visible").last
            if mobile.count() and mobile.is_visible():
                return mobile
            legacy = page.locator(OVERLAY).filter(has=page.locator(PICKER)).last
            if legacy.count() and legacy.is_visible():
                return legacy
            page.wait_for_timeout(100)
        return cls._picker(page)

    def upload_start_frame(self, page: Any, image_path: Path, project_id: str, scene: dict[str, Any] | None = None) -> tuple[str, str]:
        display_name = f"{image_path.stem}-{uuid.uuid4().hex[:8]}{image_path.suffix}"
        access_token = _get_page_access_token(page, scene)
        image_bytes = base64.b64encode(image_path.read_bytes()).decode("ascii")
        mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
        body = {
            "clientContext": {"projectId": project_id, "tool": "PINHOLE"},
            "imageBytes": image_bytes,
            "isUserUploaded": True,
            "isHidden": False,
            "fileName": image_path.name,
            "mimeType": mime_type,
        }
        res = _browser_post_json(page, f"{FLOW_API_ROOT}/flow/uploadImage", access_token, body)
        media = res.get("media") if isinstance(res, dict) else None
        media_id = (
            res.get("mediaId")
            or (media.get("name") if isinstance(media, dict) else None)
            or res.get("name")
        )
        if media_id and isinstance(media_id, str):
            return media_id, display_name
        raise ProviderError(f"Google Flow direct frame upload completed without a valid media id: {res}")

    def bind_start_frame(self, page: Any, display_name: str) -> None:
        for attempt in range(3):
            chip = page.locator(EMPTY_CHIP).first
            if not chip.count():
                raise ProviderError("Google Flow migrated Frames mode has no empty Start chip.")
            chip.click(timeout=4000)
            picker = self._wait_for_picker(page)
            search = picker.locator(PICKER_SEARCH).first
            try:
                search.wait_for(state="visible", timeout=8000)
            except Exception as exc:
                picker_count = page.locator(PICKER).count()
                visible_picker_count = page.locator(f"{PICKER}:visible").count()
                mobile_picker_count = page.locator(MOBILE_PICKER).count()
                visible_mobile_picker_count = page.locator(f"{MOBILE_PICKER}:visible").count()
                visible_overlays = page.locator(f"{OVERLAY}:visible")
                overlay_count = visible_overlays.count()
                visible_inputs = page.locator(
                    f"{MOBILE_PICKER}:visible input, {OVERLAY}:visible input"
                )
                input_details: list[str] = []
                for input_index in range(min(visible_inputs.count(), 8)):
                    candidate = visible_inputs.nth(input_index)
                    input_details.append(
                        "type={type!r},placeholder={placeholder!r},aria={aria!r}".format(
                            type=candidate.get_attribute("type"),
                            placeholder=candidate.get_attribute("placeholder"),
                            aria=candidate.get_attribute("aria-label"),
                        )
                    )
                overlay_text = ""
                if overlay_count:
                    try:
                        overlay_text = visible_overlays.last.inner_text(timeout=1000)[:600]
                    except Exception:
                        overlay_text = ""
                raise ProviderError(
                    "Google Flow migrated frame picker search is unavailable after clicking Start. "
                    f"pickers={picker_count}, visible_pickers={visible_picker_count}, "
                    f"mobile_pickers={mobile_picker_count}, "
                    f"visible_mobile_pickers={visible_mobile_picker_count}, "
                    f"visible_overlays={overlay_count}, inputs={input_details}, "
                    f"overlay_text={overlay_text!r}"
                ) from exc
            search.click(timeout=4000)
            search.fill(display_name)
            options = picker.locator(PICKER_OPTION).filter(has_text=display_name)
            try:
                options.first.wait_for(state="visible", timeout=8000)
            except Exception:
                page.keyboard.press("Escape")
                if attempt < 2:
                    time.sleep(2.0)
                    continue
                raise ProviderError(f"Google Flow migrated frame picker cannot find {display_name!r}.")
            options.first.click(timeout=4000)
            break
        try:
            picker.wait_for(state="hidden", timeout=1500)
        except Exception:
            confirm = self._picker(page).locator(PICKER_CONFIRM).first
            if confirm.count() and confirm.is_visible():
                confirm.click(timeout=4000)
            self._picker(page).wait_for(state="hidden", timeout=15_000)
        page.locator(BOUND_CHIP).first.wait_for(state="visible", timeout=5000)

    @staticmethod
    def type_prompt(page: Any, prompt: str) -> None:
        composer = page.locator(COMPOSER).first
        composer.wait_for(state="visible", timeout=8000)
        composer.click(timeout=5000)
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        page.keyboard.insert_text(prompt)

    def submit(self, page: Any, project_id: str, scene: dict[str, Any]) -> MigratedGeneration:
        references = list(scene.get("reference_images") or [])
        if not references and scene.get("reference_image"):
            references = [scene["reference_image"]]
        valid_refs: list[Path] = []
        for r in references:
            rp = Path(str(r))
            if not rp.is_file():
                raise ProviderError(f"Google Flow reference image does not exist: {rp}")
            valid_refs.append(rp)
        if not valid_refs and str(scene.get("task_type") or "") == "image_to_video":
            ref_fallback = scene.get("reference_image") or (references[0] if references else "")
            raise ProviderError(f"Google Flow migrated start frame does not exist: {ref_fallback}")
        if len(valid_refs) > 2:
            raise ProviderError("Google Flow image-to-video supports one start image and one optional end image.")

        # Direct REST API submission matching G-Labs VideoJobWorker:
        start_media_id = None
        end_media_id = None
        if len(valid_refs) >= 1:
            start_media_id, _display_name = self.upload_start_frame(page, valid_refs[0], project_id, scene)
        if len(valid_refs) >= 2:
            end_media_id, _end_display = self.upload_start_frame(page, valid_refs[1], project_id, scene)
        access_token = _get_page_access_token(page, scene)
        recaptcha_token = _mint_recaptcha_token(page, "MEDIA_GENERATION")
        model_id = str(scene.get("model") or "veo_31_fast")
        aspect = str(scene.get("aspect_ratio") or "16:9")
        aspect_enum = "VIDEO_ASPECT_RATIO_PORTRAIT" if aspect == "9:16" else "VIDEO_ASPECT_RATIO_LANDSCAPE"
        batch_id = str(uuid.uuid4())
        session_id = f";{int(time.time() * 1000)}"

        model_map = {
            "veo_31_lite_relaxed": "veo_3_1_i2v_lite_low_priority",
            "veo_31_lite": "veo_3_1_i2v_lite",
            "veo_31_fast": "veo_3_1_i2v_s_fast",
            "veo_31_quality": "veo_3_1_i2v_quality",
            "omni_flash": "omni_1_1_flash",
        }
        if end_media_id:
            if model_id == "veo_31_lite_relaxed":
                model_key = "veo_3_1_interpolation_lite_low_priority"
            else:
                model_key = "veo_3_1_interpolation_lite"
        else:
            model_key = model_map.get(model_id, "veo_3_1_i2v_s_fast")
            if model_id == "veo_31_fast":
                if aspect == "9:16":
                    model_key += "_portrait"
                if str(scene.get("_flow_account_tier") or "").lower() == "ultra":
                    model_key += "_ultra"

        raw_seed = scene.get("seed")
        seed = int(raw_seed) if raw_seed not in (None, "", 0, "0") else (secrets.randbelow(2_147_483_647) or 1)

        video_request: dict[str, Any] = {
            "aspectRatio": aspect_enum,
            "textInput": {"structuredPrompt": {"parts": [{"text": str(scene.get("prompt") or "")}]}},
            "videoModelKey": model_key,
            "metadata": {},
            "seed": seed,
            "mediaGenerationContext": {"batchId": batch_id},
        }
        if start_media_id:
            video_request["startImage"] = {"mediaId": start_media_id}
        if end_media_id:
            video_request["endImage"] = {"mediaId": end_media_id}

        resolution = str(scene.get("_video_resolution") or "").upper()
        spec_resolution = "VIDEO_RESOLUTION_1080P" if "1080" in resolution else "VIDEO_RESOLUTION_720P"

        payload = {
            "clientContext": {
                "projectId": project_id,
                "sessionId": session_id,
                "tool": "PINHOLE",
                "userPaygateTier": str(scene.get("_flow_paygate_tier") or "PAYGATE_TIER_TWO"),
                "recaptchaContext": {
                    "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB",
                    "token": recaptcha_token,
                },
            },
            "videoRequests": [video_request],
            "requests": [video_request],
            "outputSpec": {"resolution": spec_resolution},
            "mediaGenerationContext": {
                "batchId": batch_id,
                "audioFailurePreference": "RETURN_SILENCED_VIDEOS",
            },
            "useV2ModelConfig": True,
        }
        if end_media_id:
            route = "batchAsyncGenerateVideoStartAndEndImage"
        elif start_media_id:
            route = "batchAsyncGenerateVideoStartImage"
        else:
            route = "batchAsyncGenerateVideoText"
        res = _browser_post_json(
            page,
            f"{FLOW_API_ROOT}/video:{route}",
            access_token,
            payload,
        )
        media = res.get("media")
        first = media[0] if isinstance(media, list) and media else None
        gen_media_id = None
        if isinstance(first, dict):
            gen_media_id = first.get("name") or first.get("mediaId")
        if not gen_media_id and isinstance(res, dict):
            gen_media_id = res.get("name") or res.get("mediaId")
        if gen_media_id and isinstance(gen_media_id, str):
            record = MigratedGeneration(
                workflow_id=gen_media_id,
                project_id=project_id,
                media_id=gen_media_id,
                status=STATUS_RUNNING,
            )
            self.records[gen_media_id] = record
            return record
        raise ProviderError(f"Google Flow direct video submission completed without a media id: {res}")

    def poll(self, page: Any, workflow_id: str, scene: dict[str, Any] | None = None) -> MigratedGeneration | None:
        access_token = _get_page_access_token(page, scene)
        curr = self.records.get(workflow_id)
        project_id = curr.project_id if curr else ""
        res = _browser_post_json(
            page,
            f"{FLOW_API_ROOT}/video:batchCheckAsyncVideoGenerationStatus",
            access_token,
            {"media": [{"name": workflow_id, "projectId": project_id}]},
        )
        media = res.get("media")
        first = media[0] if isinstance(media, list) and media else None
        if isinstance(first, dict):
            metadata = first.get("mediaMetadata") if isinstance(first, dict) else None
            media_status = metadata.get("mediaStatus") if isinstance(metadata, dict) else None
            status_str = str(media_status.get("mediaGenerationStatus") or "") if isinstance(media_status, dict) else ""
            if status_str in {
                "MEDIA_GENERATION_STATUS_ACTIVE",
                "MEDIA_GENERATION_STATUS_PENDING",
                "MEDIA_GENERATION_STATUS_SCHEDULED",
                "MEDIA_GENERATION_STATUS_PROCESSING",
                "MEDIA_GENERATION_STATUS_SUBMITTED",
                "",
            }:
                record = MigratedGeneration(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    media_id=workflow_id,
                    status=STATUS_RUNNING,
                )
                self.records[workflow_id] = record
                return record
            if status_str == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                fife_url = _find_nested_string(first, "fifeUrl") or f"https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name={workflow_id}"
                record = MigratedGeneration(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    media_id=workflow_id,
                    status=STATUS_DONE,
                    video_url=fife_url,
                )
                self.records[workflow_id] = record
                return record
            if status_str in {"MEDIA_GENERATION_STATUS_FAILED", "MEDIA_GENERATION_STATUS_CANCELLED"}:
                error = media_status.get("error") if isinstance(media_status, dict) else None
                detail = str(error.get("message") or "") if isinstance(error, dict) else ""
                record = MigratedGeneration(
                    workflow_id=workflow_id,
                    project_id=project_id,
                    media_id=workflow_id,
                    status=4,
                )
                self.records[workflow_id] = record
                return record
        return self.records.get(workflow_id)

    def download(self, context: Any, record: MigratedGeneration, scene: dict[str, Any]) -> Path:
        resolution = str(scene.get("_video_resolution") or "720p")
        output_path = (
            scene_output_directory(scene, self.output_dir)
            / f"{scene_output_stem(scene)}_{resolution}.mp4"
        ).resolve()

        if record.video_url and "getMediaUrlRedirect" not in record.video_url:
            try:
                resp = context.request.get(record.video_url, timeout=120_000)
                body = resp.body()
                if getattr(resp, "ok", False) and (body[4:8] == b"ftyp" or "video/" in str(getattr(resp, "headers", {}).get("content-type", "")).lower()):
                    output_path.write_bytes(body)
                    return output_path
            except Exception:
                pass

        redirect_url = f"https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name={record.media_id}"
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            try:
                redirect = context.request.get(redirect_url, max_redirects=0, timeout=30_000)
                status = int(getattr(redirect, "status", 0))
                if status in {301, 302, 303, 307, 308}:
                    location = str(getattr(redirect, "headers", {}).get("location", ""))
                    if location:
                        media = context.request.get(location, timeout=120_000)
                        body = media.body()
                        content_type = str(getattr(media, "headers", {}).get("content-type", "")).lower()
                        if getattr(media, "ok", False) and ("video/" in content_type or body[4:8] == b"ftyp"):
                            output_path.write_bytes(body)
                            return output_path
            except Exception:
                pass
            time.sleep(1.5)

        tried: list[str] = []
        for url in (record.video_url, record.poster_url):
            if not url:
                continue
            host = (urlsplit(url).hostname or "").lower()
            if not (host.endswith("googleusercontent.com") or host.endswith("google.com")):
                continue
            response = context.request.get(url, timeout=180_000, max_redirects=0)
            if int(getattr(response, "status", 0) or 0) >= 300:
                tried.append(f"{host}:http{getattr(response, 'status', 'unknown')}")
                continue
            body = response.body()
            if body[4:8] != b"ftyp":
                tried.append(f"{host}:not-mp4")
                continue
            output_path.write_bytes(body)
            return output_path
        raise ProviderError(
            "Google Flow migrated generation finished but no downloadable MP4 was available"
            + (f" ({', '.join(tried)})" if tried else "")
            + "."
        )


class MigratedFlowImageDriver:
    """Drive image generation on flow.google.com with the persisted Chrome profile."""

    MODEL_LABELS = {
        "nano_banana_2_lite": ("Nano Banana 2 Lite", ()),
        "nano_banana_2": ("Nano Banana 2", ("Lite",)),
        "nano_banana_pro": ("Nano Banana Pro", ()),
    }
    ASPECT_LIGATURES = {
        "16:9": "crop_16_9",
        "9:16": "crop_9_16",
        "1:1": "crop_square",
        "4:3": "crop_landscape",
        "3:4": "crop_portrait",
    }

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self._shared = MigratedFlowVideoDriver(output_dir)

    def _select_model(self, page: Any, pane: Any, model_id: str) -> None:
        matcher = self.MODEL_LABELS.get(model_id)
        if matcher is None:
            raise ProviderError(f"Unsupported migrated Google Flow image model: {model_id!r}")
        contains, excludes = matcher
        button = pane.locator("button").filter(has=_ligature(page, "arrow_drop_down")).first
        if not button.count():
            raise ProviderError("Google Flow migrated image model picker is unavailable.")

        def matches(value: str) -> bool:
            folded = value.casefold()
            return contains.casefold() in folded and all(item.casefold() not in folded for item in excludes)

        if matches(str(button.text_content() or "")):
            return
        button.click(timeout=4000)
        items = page.locator(MENU_ITEM)
        items.first.wait_for(state="visible", timeout=5000)
        offered = [str(value or "").strip() for value in items.all_text_contents()]
        hits = [index for index, value in enumerate(offered) if matches(value)]
        if len(hits) != 1:
            page.keyboard.press("Escape")
            raise ProviderError(
                f"Google Flow migrated image model {model_id!r} is unavailable or ambiguous; offered: {', '.join(offered)}"
            )
        items.nth(hits[0]).click(timeout=4000)
        page.wait_for_timeout(250)

    def configure(self, page: Any, scene: dict[str, Any]) -> None:
        pane = self._shared._open_settings(page)
        try:
            self._shared._select_radio(page, pane, ligature="image")
            self._select_model(page, pane, str(scene.get("model") or ""))
            aspect = str(scene.get("aspect_ratio") or "16:9")
            ligature = self.ASPECT_LIGATURES.get(aspect)
            if ligature is None:
                raise ProviderError(f"Unsupported migrated Google Flow image aspect ratio: {aspect!r}")
            self._shared._select_radio(page, pane, ligature=ligature)
            self._shared._select_radio(page, pane, text="x1", optional=True)
        finally:
            self._shared._close_settings(page)

    @staticmethod
    def _clear_composer(page: Any) -> Any:
        composer = page.locator(COMPOSER).first
        composer.wait_for(state="visible", timeout=8000)
        composer.click(timeout=5000)
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        page.wait_for_timeout(600)
        return composer

    def _mention_reference(self, page: Any, composer: Any, display_name: str, expected_count: int) -> None:
        last_count = 0
        offered: list[str] = []
        for attempt in range(3):
            before = page.locator(MENTION_CHIP).count()
            composer.click(timeout=5000)
            page.keyboard.type("@", delay=120)
            page.wait_for_timeout(2200)
            page.keyboard.type(display_name, delay=100)
            page.wait_for_timeout(2500)
            offered = [str(value or "").strip() for value in page.locator(PICKER_OPTION).all_text_contents()]
            page.keyboard.press("Enter")
            page.wait_for_timeout(2500)
            last_count = page.locator(MENTION_CHIP).count()
            if last_count == expected_count:
                page.keyboard.type(" ", delay=80)
                return
            # Some Flow cohorts select the asset with Enter but keep the shared
            # library picker open until its own locale-independent confirm button
            # is clicked. The transparent CDK backdrop otherwise blocks every
            # later composer gesture.
            confirm = page.locator(f"{OVERLAY}:visible").locator(PICKER_CONFIRM).first
            if confirm.count() and confirm.is_visible():
                confirm.click(timeout=4000)
                page.wait_for_timeout(2500)
                last_count = page.locator(MENTION_CHIP).count()
                if last_count == expected_count:
                    page.keyboard.type(" ", delay=80)
                    return
            if attempt < 2:
                if page.locator(f"{OVERLAY}:visible").count():
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(300)
                for _ in range(len(display_name) + 1):
                    page.keyboard.press("Backspace")
                cleaned_count = page.locator(MENTION_CHIP).count()
                if cleaned_count < before:
                    raise ProviderError(
                        "Google Flow migrated mention retry removed an already attached reference; submit was cancelled."
                    )
                page.wait_for_timeout(2000)
        raise ProviderError(
            f"Google Flow migrated reference {display_name!r} was uploaded but no mention chip was attached "
            f"(expected {expected_count}, found {last_count}; picker offered: {', '.join(offered[:6]) or '<nothing>'})."
        )

    def _prepare_submit_payload(
        self, page: Any, project_id: str, scene: dict[str, Any]
    ) -> tuple[str, dict[str, Any], str, int, str, str]:
        access_token = _get_page_access_token(page, scene)
        references = list(scene.get("reference_images") or [])
        if not references and scene.get("reference_image"):
            references = [scene["reference_image"]]
        ref_media_ids: list[str] = []
        for ref_item in references:
            rp = Path(str(ref_item))
            if not rp.is_file():
                raise ProviderError(f"Google Flow reference image does not exist: {rp}")
            mid, _ = self._shared.upload_start_frame(page, rp, project_id, scene)
            ref_media_ids.append(mid)

        recaptcha_token = _mint_recaptcha_token(page, "IMAGE_GENERATION")
        model_id = str(scene.get("model") or "nano_banana_2")
        model_mapping = {
            "nano_banana_2_lite": "HARBOR_SEAL",
            "nano_banana_2": "NARWHAL",
            "nano_banana_pro": "GEM_PIX_2",
        }
        image_model_name = model_mapping.get(model_id, "NARWHAL")
        aspect = str(scene.get("aspect_ratio") or "16:9")
        aspect_map = {
            "16:9": "IMAGE_ASPECT_RATIO_LANDSCAPE",
            "9:16": "IMAGE_ASPECT_RATIO_PORTRAIT",
            "1:1": "IMAGE_ASPECT_RATIO_SQUARE",
            "4:3": "IMAGE_ASPECT_RATIO_FOUR_THREE",
            "3:4": "IMAGE_ASPECT_RATIO_THREE_FOUR",
        }
        aspect_enum = aspect_map.get(aspect, "IMAGE_ASPECT_RATIO_LANDSCAPE")
        raw_seed = scene.get("seed")
        seed = int(raw_seed) if raw_seed not in (None, "", 0, "0") else (secrets.randbelow(2_147_483_647) or 1)
        prompt = str(scene.get("prompt") or "")
        batch_id = str(uuid.uuid4())
        session_id = f";{int(time.time() * 1000)}"

        request: dict[str, Any] = {
            "imageModelName": image_model_name,
            "imageAspectRatio": aspect_enum,
            "structuredPrompt": {"parts": [{"text": prompt}]},
            "seed": seed,
        }
        if ref_media_ids:
            request["imageInputs"] = [
                {"name": mid, "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"}
                for mid in ref_media_ids
            ]

        payload = {
            "clientContext": {
                "projectId": project_id,
                "sessionId": session_id,
                "tool": "PINHOLE",
                "userPaygateTier": str(scene.get("_flow_paygate_tier") or "PAYGATE_TIER_TWO"),
                "recaptchaContext": {
                    "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB",
                    "token": recaptcha_token,
                },
            },
            "requests": [request],
            "mediaGenerationContext": {"batchId": batch_id},
            "useNewMedia": True,
        }
        return access_token, payload, batch_id, seed, prompt, aspect

    @staticmethod
    def _parse_submit_response(
        res: dict[str, Any],
        *,
        project_id: str,
        batch_id: str,
        seed: int,
        prompt: str,
        aspect: str,
    ) -> MigratedImage:
        media = res.get("media")
        first = media[0] if isinstance(media, list) and media else None
        image = first.get("image") if isinstance(first, dict) else None
        generated = image.get("generatedImage") if isinstance(image, dict) else None
        media_url = (
            (generated.get("fifeUrl") or generated.get("url") if isinstance(generated, dict) else None)
            or _find_nested_string(first, "fifeUrl")
        )
        media_id = (first.get("name") if isinstance(first, dict) else None) or batch_id
        if media_url and isinstance(media_url, str):
            dims = (1920, 1080) if aspect == "16:9" else (1080, 1920) if aspect == "9:16" else (1024, 1024)
            return MigratedImage(
                media_id=media_id,
                workflow_id=batch_id,
                project_id=project_id,
                seed=seed,
                prompt=prompt,
                image_url=media_url,
                dimensions=dims,
                display_name=None,
            )
        raise ProviderError(f"Google Flow REST image generation did not return a valid media URL: {res}")

    def submit(self, page: Any, project_id: str, scene: dict[str, Any]) -> MigratedImage:
        # Direct REST API submission matching G-Labs batchGenerateImages:
        access_token, payload, batch_id, seed, prompt, aspect = self._prepare_submit_payload(
            page, project_id, scene
        )
        res = _browser_post_json(
            page,
            f"{FLOW_API_ROOT}/projects/{project_id}/flowMedia:batchGenerateImages",
            access_token,
            payload,
        )
        return self._parse_submit_response(
            res,
            project_id=project_id,
            batch_id=batch_id,
            seed=seed,
            prompt=prompt,
            aspect=aspect,
        )

    def start_async_submit(self, page: Any, project_id: str, scene: dict[str, Any]) -> dict[str, Any]:
        """Fire batchGenerateImages in the browser without blocking the Playwright session queue."""
        if "submit" in self.__dict__:
            record = self.submit(page, project_id, scene)
            return {"state": "done", "record": record}
        access_token, payload, batch_id, seed, prompt, aspect = self._prepare_submit_payload(
            page, project_id, scene
        )
        url = f"{FLOW_API_ROOT}/projects/{project_id}/flowMedia:batchGenerateImages"
        ticket_id = f"img_{uuid.uuid4().hex}"
        if not hasattr(page, "evaluate"):
            res = _browser_post_json(page, url, access_token, payload)
            record = self._parse_submit_response(
                res,
                project_id=project_id,
                batch_id=batch_id,
                seed=seed,
                prompt=prompt,
                aspect=aspect,
            )
            return {"state": "done", "record": record}

        started = page.evaluate(
            """
            ({ticketId, url, accessToken, body}) => {
              try {
                if (!window.__cofiAsyncImageJobs || typeof window.__cofiAsyncImageJobs !== 'object') {
                  window.__cofiAsyncImageJobs = {};
                }
                window.__cofiAsyncImageJobs[ticketId] = { state: 'pending' };
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
                  window.__cofiAsyncImageJobs[ticketId] = {
                    state: 'done',
                    result: {ok: response.ok, status: response.status, payload}
                  };
                }).catch((error) => {
                  window.__cofiAsyncImageJobs[ticketId] = {
                    state: 'done',
                    result: {ok: false, status: 0, payload: {message: String(error)}}
                  };
                });
                return { started: true };
              } catch (err) {
                return { started: false, error: String(err) };
              }
            }
            """,
            {"ticketId": ticket_id, "url": url, "accessToken": access_token, "body": payload},
        )
        if not isinstance(started, dict) or not started.get("started"):
            # Fallback if page.evaluate is mocked in unit tests
            res = _browser_post_json(page, url, access_token, payload)
            record = self._parse_submit_response(
                res,
                project_id=project_id,
                batch_id=batch_id,
                seed=seed,
                prompt=prompt,
                aspect=aspect,
            )
            return {"state": "done", "record": record}

        return {
            "ticket_id": ticket_id,
            "state": "pending",
            "url": url,
            "project_id": project_id,
            "batch_id": batch_id,
            "seed": seed,
            "prompt": prompt,
            "aspect": aspect,
        }

    def poll_async_submit(self, page: Any, ticket: dict[str, Any]) -> MigratedImage | None:
        if ticket.get("state") == "done" and ticket.get("record") is not None:
            return ticket["record"]
        ticket_id = str(ticket.get("ticket_id") or "")
        proj_id = str(ticket.get("project_id") or "")
        url = str(ticket.get("url") or f"{FLOW_API_ROOT}/projects/{proj_id}/flowMedia:batchGenerateImages")
        state_obj = page.evaluate(
            """
            (ticketId) => {
              const jobs = window.__cofiAsyncImageJobs;
              if (!jobs || !jobs[ticketId]) return { state: 'missing' };
              const entry = jobs[ticketId];
              if (entry.state === 'done') {
                delete jobs[ticketId];
              }
              return entry;
            }
            """,
            ticket_id,
        )
        if not isinstance(state_obj, dict) or state_obj.get("state") == "pending":
            return None
        if state_obj.get("state") == "missing":
            raise ProviderError("Google Flow in-flight async image job state was lost (page navigated or reloaded).")
        result = state_obj.get("result")
        if not isinstance(result, dict) or not result.get("ok"):
            payload = result.get("payload") if isinstance(result, dict) and isinstance(result.get("payload"), dict) else {}
            err = payload.get("error") if isinstance(payload, dict) else None
            msg = (
                (err.get("message") if isinstance(err, dict) else None)
                or (err.get("status") if isinstance(err, dict) else None)
                or payload.get("message")
                or ""
            )
            status = result.get("status") if isinstance(result, dict) else "unknown"
            status_int = int(status) if isinstance(status, (int, str)) and str(status).isdigit() else 0
            upper_msg = str(msg).upper()
            if "RECAPTCHA" in upper_msg or "UNUSUAL_ACTIVITY" in upper_msg:
                raise ProviderError(f"Direct request to {url} failed with HTTP {status}: {msg}")
            if status_int == 401 or any(m in upper_msg for m in ("UNAUTHENTICATED", "INVALID AUTHENTICATION", "ACCESS_TOKEN_REFRESH_NEEDED")):
                raise ProviderAuthError(f"Direct request to {url} failed with HTTP {status}: {msg}")
            if status_int == 403:
                if any(m in upper_msg for m in ("PERMISSION_DENIED", "ACCESS_DENIED")):
                    raise ProviderAuthError(f"Direct request to {url} failed with HTTP {status}: {msg}")
                raise ProviderError(f"Direct request to {url} failed with HTTP {status}: {msg}")
            if status_int == 429 or any(m in upper_msg for m in ("RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED")):
                raise ProviderQuotaError(f"Direct request to {url} failed with HTTP {status}: {msg}")
            raise ProviderError(f"Direct request to {url} failed with HTTP {status}: {msg}")

        res_payload = result.get("payload") or {}
        return self._parse_submit_response(
            res_payload,
            project_id=str(ticket.get("project_id") or ""),
            batch_id=str(ticket.get("batch_id") or ""),
            seed=int(ticket.get("seed") or 1),
            prompt=str(ticket.get("prompt") or ""),
            aspect=str(ticket.get("aspect") or "16:9"),
        )

    def download(self, context: Any, record: MigratedImage, scene: dict[str, Any]) -> Path:
        host = (urlsplit(record.image_url).hostname or "").lower()
        if not (host.endswith("googleusercontent.com") or host.endswith("google.com")):
            raise ProviderError(f"Google Flow migrated image returned an untrusted download host: {host!r}.")
        response = context.request.get(record.image_url, timeout=120_000)
        if not getattr(response, "ok", False):
            raise ProviderError(
                f"Google Flow migrated image download failed with HTTP {getattr(response, 'status', 'unknown')}."
            )
        content_type = str(getattr(response, "headers", {}).get("content-type", "")).lower()
        extension = ".png" if "png" in content_type else ".webp" if "webp" in content_type else ".jpg"
        output_path = (scene_output_directory(scene, self.output_dir) / f"{scene_output_stem(scene)}{extension}").resolve()
        output_path.write_bytes(response.body())
        if scene.get("_remove_watermark"):
            try:
                strip_gemini_watermark(output_path)
            except Exception:
                pass
        return output_path

    def generate(self, page: Any, context: Any, project_id: str, scene: dict[str, Any]) -> Path:
        return self.download(context, self.submit(page, project_id, scene), scene)

