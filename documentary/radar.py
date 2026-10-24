from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlparse

import requests


class RadarUnavailableError(RuntimeError):
    pass


class RadarClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8775",
        session: Any | None = None,
        *,
        radar_home: str | Path | None = None,
        startup_wait_seconds: float = 8.0,
        startup_poll_interval: float = 0.25,
    ):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        default_home = Path(__file__).resolve().parents[2] / "CofiRadar"
        configured_home = radar_home or os.getenv("COFI_RADAR_HOME") or default_home
        self.radar_home = Path(configured_home)
        self.startup_wait_seconds = max(0.0, float(startup_wait_seconds))
        self.startup_poll_interval = max(0.0, float(startup_poll_interval))
        self._startup_lock = Lock()

    def _is_local(self) -> bool:
        host = (urlparse(self.base_url).hostname or "").lower()
        return host in {"127.0.0.1", "localhost", "::1"}

    def _health_probe(self) -> bool:
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=0.8)
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False

    def _start_local_radar(self) -> bool:
        if not self._is_local():
            return False
        app_path = self.radar_home / "app.py"
        if not app_path.exists():
            return False
        with self._startup_lock:
            if self._health_probe():
                return True
            parsed = urlparse(self.base_url)
            env = os.environ.copy()
            env["COFI_RADAR_PORT"] = str(parsed.port or 8775)
            creationflags = 0
            startupinfo = None
            if os.name == "nt":
                creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
                creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
                startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
            try:
                subprocess.Popen(
                    [sys.executable, str(app_path)],
                    cwd=str(self.radar_home),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                    startupinfo=startupinfo,
                    close_fds=True,
                )
            except OSError:
                return False
            deadline = time.monotonic() + self.startup_wait_seconds
            while True:
                if self._health_probe():
                    return True
                if time.monotonic() >= deadline:
                    return False
                time.sleep(self.startup_poll_interval)

    def _connection_error(self, exc: Exception) -> RadarUnavailableError:
        return RadarUnavailableError(
            f"COFI Radar chưa chạy tại {self.base_url}. "
            f"Đã thử tự khởi động từ {self.radar_home} nhưng dịch vụ chưa sẵn sàng."
        )

    def _get(self, path: str, **params: Any) -> Any:
        try:
            response = self.session.get(f"{self.base_url}{path}", params=params or None, timeout=30)
        except requests.ConnectionError as exc:
            if not self._start_local_radar():
                raise self._connection_error(exc) from exc
            try:
                response = self.session.get(f"{self.base_url}{path}", params=params or None, timeout=30)
            except requests.ConnectionError as retry_exc:
                raise self._connection_error(retry_exc) from retry_exc
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, payload: dict[str, Any], *, timeout_seconds: float = 180) -> Any:
        timeout_seconds = max(1.0, float(timeout_seconds))
        try:
            response = self.session.post(f"{self.base_url}{path}", json=payload, timeout=timeout_seconds)
        except requests.ConnectionError as exc:
            if not self._start_local_radar():
                raise self._connection_error(exc) from exc
            try:
                response = self.session.post(f"{self.base_url}{path}", json=payload, timeout=timeout_seconds)
            except requests.ConnectionError as retry_exc:
                raise self._connection_error(retry_exc) from retry_exc
        response.raise_for_status()
        return response.json()

    def health(self) -> dict[str, Any]:
        try:
            data = self._get("/api/health")
            return {"ok": True, "url": self.base_url, "data": data}
        except (requests.RequestException, RadarUnavailableError) as exc:
            return {"ok": False, "url": self.base_url, "error": str(exc)}

    def scans(self, limit: int = 20) -> list[dict[str, Any]]:
        data = self._get("/api/scans", limit=limit)
        return data if isinstance(data, list) else []

    def scan(self, scan_id: int) -> dict[str, Any]:
        data = self._get(f"/api/scans/{scan_id}")
        return data if isinstance(data, dict) else {"id": scan_id}

    def scan_videos(self, scan_id: int) -> list[dict[str, Any]]:
        data = self._get(f"/api/scans/{scan_id}/videos")
        return data if isinstance(data, list) else []

    def market_feed(self, scan_id: int) -> dict[str, Any]:
        data = self._get(f"/api/scans/{scan_id}/feed")
        return data if isinstance(data, dict) else {"scan": {"id": scan_id}}

    def market_scan(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._post("/api/scans/market", payload)
        return data if isinstance(data, dict) else {"result": data}

    def channel_scan(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._post("/api/scans/channel", payload)
        return data if isinstance(data, dict) else {"result": data}

    def channel_discover(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._post("/api/channels/discover", payload)
        return data if isinstance(data, dict) else {"result": data}

    def niches(self, scan_id: int | None = None) -> list[dict[str, Any]]:
        params = {"scan_id": scan_id} if scan_id is not None else {}
        data = self._get("/api/niches", **params)
        return data if isinstance(data, list) else []

    def niche_detail(self, niche_id: int) -> dict[str, Any]:
        data = self._get(f"/api/niches/{niche_id}")
        return data if isinstance(data, dict) else {"id": niche_id}

    def save_niche(self, niche_id: int, *, note: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"kind": "niche", "ref_id": str(niche_id)}
        if note:
            payload["note"] = note
        data = self._post("/api/evidence", payload)
        return data if isinstance(data, dict) else {"ok": True, "ref_id": str(niche_id)}

    def my_channels(self) -> list[dict[str, Any]]:
        data = self._get("/api/my-channels")
        return data if isinstance(data, list) else []

    def channel_today_scan(
        self,
        channel_id: str,
        *,
        hours: int = 48,
        limit: int = 5,
        max_videos: int = 60,
    ) -> dict[str, Any]:
        data = self._post(
            f"/api/my-channels/{channel_id}/today-scan",
            {"hours": hours, "limit": limit, "max_videos": max_videos},
            timeout_seconds=300,
        )
        return data if isinstance(data, dict) else {"result": data}

    def create_plan(
        self,
        niche_id: int,
        *,
        requested_count: int = 30,
        my_channel_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"niche_id": int(niche_id), "requested_count": int(requested_count)}
        if my_channel_id:
            payload["my_channel_id"] = my_channel_id
        data = self._post("/api/plans", payload)
        return data if isinstance(data, dict) else {"result": data}

    def plan_items(self, plan_id: int) -> list[dict[str, Any]]:
        data = self._get(f"/api/plans/{int(plan_id)}/items")
        return data if isinstance(data, list) else []

    def update_plan_item_status(self, item_id: int, status: str) -> dict[str, Any]:
        response = self.session.patch(
            f"{self.base_url}/api/plan-items/{int(item_id)}",
            json={"status": status},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {"ok": True, "id": int(item_id), "status": status}

    def today(self) -> list[dict[str, Any]]:
        data = self._get("/api/today")
        return data if isinstance(data, list) else []
