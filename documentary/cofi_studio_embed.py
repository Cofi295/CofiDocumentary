from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DOCUMENTARY_ROOT = Path(__file__).resolve().parents[1]
BUNDLED_MEDIA_FACTORY_ROOT = DOCUMENTARY_ROOT / "vendor" / "media_factory"


class CofiStudioEmbedManager:
    """Runs Documentary's bundled Media Factory as an embedded tool surface.

    The runtime source ships inside CofiDocumentary so AI Visual does not require
    a separate CofiStudio installation. Mutable account/session/queue state lives
    under CofiDocumentary/data/media_factory and survives source refreshes.
    """

    def __init__(
        self,
        studio_root: str | Path | None = None,
        *,
        port: int | None = None,
        log_dir: str | Path | None = None,
        state_dir: str | Path | None = None,
    ):
        configured_root = studio_root or os.getenv("COFI_MEDIA_FACTORY_DIR") or os.getenv("COFI_STUDIO_DIR")
        self.studio_root = Path(configured_root or BUNDLED_MEDIA_FACTORY_ROOT).resolve()
        self.port = int(port or os.getenv("COFI_STUDIO_EMBED_PORT", "8894"))
        self.state_dir = Path(
            state_dir
            or os.getenv("COFI_MEDIA_FACTORY_STATE_DIR")
            or DOCUMENTARY_ROOT / "data" / "media_factory"
        ).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path(log_dir or self.state_dir / "logs").resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._process: subprocess.Popen[Any] | None = None
        self._http_client: Any = None
        self._health_cache: tuple[float, dict[str, Any] | None] | None = None
        self._runtime_status_cache: tuple[float, dict[str, Any]] | None = None

    def _get_http_client(self) -> Any:
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.Client(
                    timeout=35.0,
                    limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
                )
            except Exception:
                self._http_client = False
        return self._http_client if self._http_client is not False else None

    def _invalidate_runtime_cache(self) -> None:
        self._runtime_status_cache = None
        self._health_cache = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def media_factory_url(self) -> str:
        return f"{self.base_url}/embed/media-factory"

    def _python_executable(self) -> str:
        candidates = (
            self.studio_root / ".venv" / "Scripts" / "python.exe",
            self.studio_root / "venv" / "Scripts" / "python.exe",
        )
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return sys.executable

    def _runtime_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["COFI_MEDIA_FACTORY_STATE_DIR"] = str(self.state_dir)
        env["COFI_MEDIA_FACTORY_FRONTEND_DIST"] = str((self.studio_root / "frontend" / "dist").resolve())
        return env

    def _health_payload(self) -> dict[str, Any] | None:
        now = time.monotonic()
        if self._health_cache is not None and (now - self._health_cache[0]) < 2.5:
            return self._health_cache[1]
        payload = None
        client = self._get_http_client()
        try:
            if client is not None:
                resp = client.get(f"{self.base_url}/api/health", timeout=0.8)
                if resp.status_code == 200:
                    payload = resp.json()
            else:
                with urlopen(f"{self.base_url}/api/health", timeout=0.65) as response:
                    if response.status == 200:
                        payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            payload = None
        if not isinstance(payload, dict) or payload.get("app") != "Cofi Studio" or payload.get("status") != "ok":
            payload = None
        self._health_cache = (now, payload)
        return payload

    def _request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        timeout: float = 35.0,
    ) -> Any:
        client = self._get_http_client()
        if client is not None:
            try:
                resp = client.request(
                    method=method,
                    url=f"{self.base_url}{path}",
                    json=payload if payload is not None else None,
                    timeout=timeout,
                )
            except Exception as exc:
                raise RuntimeError(f"Không kết nối được Media Factory tại {self.base_url}: {exc}") from exc
            if resp.status_code >= 400:
                raw = resp.text
                try:
                    detail = resp.json().get("detail")
                except Exception:
                    detail = raw.strip()
                raise RuntimeError(str(detail or f"Media Factory HTTP {resp.status_code}"))
            if not resp.text:
                return {}
            try:
                return resp.json()
            except Exception as exc:
                raise RuntimeError("Media Factory trả về dữ liệu không hợp lệ") from exc

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw).get("detail")
            except (ValueError, AttributeError):
                detail = raw.strip()
            raise RuntimeError(str(detail or f"Media Factory HTTP {exc.code}")) from exc
        except (OSError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"Không kết nối được Media Factory tại {self.base_url}: {exc}") from exc
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Media Factory trả về dữ liệu không hợp lệ") from exc

    def list_scenes(self) -> list[dict[str, Any]]:
        try:
            raw = self._request_json("/api/scenes", timeout=5.0)
            if isinstance(raw, list):
                return [s for s in raw if isinstance(s, dict)]
        except Exception:
            pass
        return []

    def clear_all_scenes(self) -> dict[str, Any]:
        self._invalidate_runtime_cache()
        if os.getenv("PYTEST_CURRENT_TEST") and getattr(self._request_json, "__func__", None) is CofiStudioEmbedManager._request_json:
            return {"ok": True, "skipped_in_pytest": True}
        try:
            res = self._request_json("/api/scenes", method="DELETE", timeout=15.0)
            return res if isinstance(res, dict) else {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def runtime_status(self, *, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if not force and self._runtime_status_cache is not None and (now - self._runtime_status_cache[0]) < 0.8:
            return dict(self._runtime_status_cache[1])
        try:
            accounts_raw = self._request_json("/api/providers/google/accounts")
        except RuntimeError:
            if not (callable(self._request_json) and getattr(self._request_json, "__name__", "") == "<lambda>"):
                self.start(timeout_seconds=15.0)
                accounts_raw = self._request_json("/api/providers/google/accounts")
            else:
                raise
        accounts = accounts_raw if isinstance(accounts_raw, list) else []
        # Auto-recover sessions once on first runtime query or if any ready account has enabled=False
        needs_auto_recover = not getattr(self, "_auto_recovered_once", False) or any(
            isinstance(acc, dict)
            and str(acc.get("status") or "").lower() == "ready"
            and acc.get("enabled") is False
            for acc in accounts
        )
        if needs_auto_recover:
            self._auto_recovered_once = True
            try:
                checked = self.check_all_accounts()
                if isinstance(checked, dict) and isinstance(checked.get("accounts"), list):
                    accounts = checked["accounts"]
            except Exception:
                pass
        queue_info = self._request_json("/api/queue/status")
        workers: list[dict[str, Any]] = []
        try:
            workers_raw = self._request_json("/api/workers", timeout=5.0)
            if isinstance(workers_raw, list):
                workers = [w for w in workers_raw if isinstance(w, dict)]
        except Exception:
            workers = []
        result = {
            **self.status(),
            "accounts": accounts,
            "queue": queue_info,
            "workers": workers,
        }
        self._runtime_status_cache = (time.monotonic(), result)
        return dict(result)

    def queue_action(self, action: str) -> dict[str, Any]:
        self._invalidate_runtime_cache()
        normalized = str(action or "").strip().lower()
        if normalized not in {"pause", "resume"}:
            raise ValueError("Queue action phải là pause hoặc resume")
        result = self._request_json(f"/api/queue/{normalized}", method="POST")
        return result if isinstance(result, dict) else {"ok": True}

    def account_action(self, account_id: str, action: str) -> dict[str, Any]:
        target_id = str(account_id or "").strip()
        normalized = str(action or "").strip().lower()
        if target_id in {"_all", "all"}:
            if normalized in {"check", "check-all", "check_all", "recover", "renew", "resume"}:
                return self.check_all_accounts()
            if normalized in {"prune-dead", "prune_dead", "prune"}:
                return self.prune_dead_accounts()
            raise ValueError(f"Bulk account action không hợp lệ: {action}")
        if normalized == "delete":
            self._request_json(
                f"/api/providers/google/accounts/{target_id}",
                method="DELETE",
            )
            return {"ok": True, "deleted": True, "account_id": target_id}
        if normalized == "check":
            try:
                result = self._request_json(
                    f"/api/providers/google/accounts/{target_id}/check",
                    method="POST",
                    timeout=35.0,
                )
                return result if isinstance(result, dict) else {"ok": True}
            except RuntimeError:
                result = self._request_json(
                    f"/api/providers/google/accounts/{target_id}/renew",
                    method="POST",
                    timeout=35.0,
                )
                try:
                    self._request_json(
                        f"/api/providers/google/accounts/{target_id}",
                        method="PATCH",
                        payload={"enabled": True, "image_enabled": True},
                    )
                except RuntimeError:
                    pass
                return result if isinstance(result, dict) else {"ok": True}
        if normalized not in {"renew", "verify"}:
            raise ValueError("Account action phải là renew, verify, check hoặc delete")
        result = self._request_json(
            f"/api/providers/google/accounts/{target_id}/{normalized}",
            method="POST",
        )
        return result if isinstance(result, dict) else {"ok": True}

    def create_account_login(self) -> dict[str, Any]:
        result = self._request_json(
            "/api/providers/google/accounts/login",
            method="POST",
            payload={},
        )
        return result if isinstance(result, dict) else {"ok": True}

    def check_all_accounts(self) -> dict[str, Any]:
        try:
            result = self._request_json(
                "/api/providers/google/accounts/check_all",
                method="POST",
                payload={},
                timeout=60.0,
            )
            if isinstance(result, dict) and "accounts" in result:
                return result
        except RuntimeError:
            pass

        try:
            self._request_json("/api/providers/google/accounts/resume_all", method="POST", payload={}, timeout=20.0)
        except RuntimeError:
            pass

        accounts_raw = self._request_json("/api/providers/google/accounts", timeout=15.0)
        accounts = accounts_raw if isinstance(accounts_raw, list) else []
        recovered_count = 0
        for account in accounts:
            if not isinstance(account, dict):
                continue
            acc_id = str(account.get("id") or "").strip()
            if not acc_id:
                continue
            status = str(account.get("status") or "").strip().lower()
            session_present = bool(account.get("session_present"))
            if status == "ready" and account.get("enabled") is False:
                try:
                    self._request_json(
                        f"/api/providers/google/accounts/{acc_id}",
                        method="PATCH",
                        payload={"enabled": True, "image_enabled": True},
                    )
                    recovered_count += 1
                except RuntimeError:
                    pass
            elif status != "ready" and session_present:
                try:
                    self._request_json(
                        f"/api/providers/google/accounts/{acc_id}/renew",
                        method="POST",
                        timeout=25.0,
                    )
                    self._request_json(
                        f"/api/providers/google/accounts/{acc_id}",
                        method="PATCH",
                        payload={"enabled": True, "image_enabled": True},
                    )
                    recovered_count += 1
                except RuntimeError:
                    pass

        accounts_raw = self._request_json("/api/providers/google/accounts", timeout=15.0)
        accounts = accounts_raw if isinstance(accounts_raw, list) else []
        active_count = sum(
            1
            for acc in accounts
            if isinstance(acc, dict) and str(acc.get("status") or "").lower() == "ready" and acc.get("enabled") is not False
        )
        return {
            "ok": True,
            "active_count": active_count,
            "total_count": len(accounts),
            "recovered_count": recovered_count,
            "dead_count": max(0, len(accounts) - active_count),
            "accounts": accounts,
        }

    def prune_dead_accounts(self) -> dict[str, Any]:
        try:
            result = self._request_json(
                "/api/providers/google/accounts/prune_dead",
                method="POST",
                payload={},
                timeout=60.0,
            )
            if isinstance(result, dict) and "kept_count" in result:
                return result
        except RuntimeError:
            pass

        # First try recovering any valid sessions before pruning
        try:
            self.check_all_accounts()
        except Exception:
            pass

        accounts_raw = self._request_json("/api/providers/google/accounts", timeout=15.0)
        accounts = accounts_raw if isinstance(accounts_raw, list) else []
        kept: list[dict[str, Any]] = []
        deleted: list[dict[str, Any]] = []
        for account in accounts:
            if not isinstance(account, dict):
                continue
            acc_id = str(account.get("id") or "").strip()
            if not acc_id:
                continue
            status = str(account.get("status") or "").strip().lower()
            session_present = bool(account.get("session_present"))
            live_session = bool(account.get("live_session"))
            is_dead = (
                status in {"auth_expired", "error", "dead", "disconnected", "login_required"}
                or (status != "ready" and not session_present and not live_session)
            )
            if is_dead:
                try:
                    self._request_json(
                        f"/api/providers/google/accounts/{acc_id}",
                        method="DELETE",
                    )
                    deleted.append({
                        "id": acc_id,
                        "email": account.get("email"),
                        "status": status,
                        "last_error": account.get("last_error"),
                    })
                except RuntimeError:
                    kept.append(account)
            else:
                kept.append(account)
        return {
            "ok": True,
            "kept_count": len(kept),
            "deleted_count": len(deleted),
            "deleted": deleted,
            "accounts": kept,
        }

    def clean_profile_caches(self) -> dict[str, Any]:
        self._invalidate_runtime_cache()
        try:
            result = self._request_json(
                "/api/providers/google/accounts/clean-cache",
                method="POST",
                payload={},
                timeout=60.0,
            )
            if isinstance(result, dict) and "freed_mb" in result:
                return result
        except Exception:
            pass

        try:
            from vendor.media_factory.backend.app.db import Database
            from vendor.media_factory.backend.app.providers.google import GoogleFlowAccountManager
            from vendor.media_factory.backend.app.secrets import KeyringSecretStore

            db_path = self.state_dir / "cofi_studio.db"
            if not db_path.exists():
                db_path = self.state_dir / "media_factory.db"
            secret_store = KeyringSecretStore(storage_dir=self.state_dir / "secrets" / "google-flow")
            manager = GoogleFlowAccountManager(
                Database(db_path),
                secret_store,
                profile_root=self.state_dir / "google-flow-profiles",
            )
            return manager.clean_profile_caches()
        except Exception as exc:
            return {
                "ok": False,
                "status": "error",
                "error": str(exc),
                "total_size_mb": 0.0,
                "freed_mb": 0.0,
                "orphan_profiles_removed": 0,
                "orphan_sessions_removed": 0,
                "cleaned_profiles_count": 0,
            }

    def generate(self, scene: dict[str, Any]) -> dict[str, Any]:
        result = self._request_json(
            "/api/providers/google/generate",
            method="POST",
            payload={"scene": scene},
            timeout=330.0,
        )
        if not isinstance(result, dict):
            raise RuntimeError("Media Factory không trả về kết quả test hợp lệ")
        return result

    def _port_open(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=0.25):
                return True
        except OSError:
            return False

    def status(self) -> dict[str, Any]:
        payload = self._health_payload()
        running = payload is not None
        return {
            "ok": running,
            "running": running,
            "url": self.media_factory_url if running else None,
            "base_url": self.base_url,
            "port": self.port,
            "studio_root": str(self.studio_root),
            "state_dir": str(self.state_dir),
            "bundled": self.studio_root == BUNDLED_MEDIA_FACTORY_ROOT.resolve(),
            "owned": bool(self._process is not None and self._process.poll() is None),
            "error": None if running else "Media Factory tích hợp chưa chạy.",
        }

    def start(self, timeout_seconds: float = 20.0) -> dict[str, Any]:
        current = self.status()
        if current["ok"]:
            return current
        if self._port_open():
            raise RuntimeError(f"Cổng {self.port} đang được ứng dụng khác sử dụng.")

        backend = self.studio_root / "backend"
        frontend_index = self.studio_root / "frontend" / "dist" / "index.html"
        if not backend.is_dir():
            raise RuntimeError(f"Không tìm thấy Media Factory tích hợp: {backend}")
        if not frontend_index.is_file():
            raise RuntimeError("Media Factory tích hợp thiếu frontend build.")

        runtime_module = "standalone_runtime:app" if (backend / "standalone_runtime.py").is_file() else "app.main:app"

        stdout_path = self.log_dir / "cofi-studio-embed.stdout.log"
        stderr_path = self.log_dir / "cofi-studio-embed.stderr.log"
        command = [
            self._python_executable(),
            "-m",
            "uvicorn",
            runtime_module,
            "--app-dir",
            str(backend),
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
            startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        with stdout_path.open("a", encoding="utf-8") as stdout, stderr_path.open("a", encoding="utf-8") as stderr:
            self._process = subprocess.Popen(
                command,
                cwd=str(self.studio_root),
                stdout=stdout,
                stderr=stderr,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                startupinfo=startupinfo,
                env=self._runtime_env(),
            )

        deadline = time.monotonic() + max(2.0, timeout_seconds)
        while time.monotonic() < deadline:
            if self._health_payload() is not None:
                return self.status()
            if self._process.poll() is not None:
                break
            time.sleep(0.15)

        detail = ""
        try:
            detail = stderr_path.read_text(encoding="utf-8", errors="replace")[-1200:].strip()
        except OSError:
            pass
        raise RuntimeError(f"Không khởi động được Media Factory tích hợp.{(' ' + detail) if detail else ''}")

    def stop(self, timeout_seconds: float = 5.0) -> dict[str, Any]:
        process = self._process
        if process is None:
            return self.status()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=max(1.0, timeout_seconds))
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
        self._process = None
        return self.status()
