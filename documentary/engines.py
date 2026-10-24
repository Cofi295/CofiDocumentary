from __future__ import annotations

import os
from pathlib import Path
import shutil
from typing import Any

import requests


def resolve_executable(name: str) -> str | None:
    resolved = shutil.which(name)
    if resolved:
        return resolved

    direct = Path(name)
    if direct.is_file():
        return str(direct)

    if os.name != "nt":
        return None

    suffixes = [""] if direct.suffix else ["", ".exe", ".cmd", ".bat", ".com"]
    for raw_dir in os.environ.get("PATH", "").split(os.pathsep):
        directory = raw_dir.strip().strip('"')
        if not directory:
            continue
        for suffix in suffixes:
            candidate = Path(directory) / f"{name}{suffix}"
            if candidate.is_file():
                return str(candidate)
    return None


def executable_status(name: str) -> dict[str, Any]:
    path = resolve_executable(name)
    return {"ok": bool(path), "path": str(path or "")}


def http_status(url: str, *, timeout: float = 0.7) -> dict[str, Any]:
    try:
        response = requests.get(url, timeout=timeout)
        payload: Any = None
        try:
            payload = response.json()
        except Exception:
            payload = None
        return {"ok": response.ok, "url": url, "status_code": response.status_code, "data": payload}
    except requests.RequestException as exc:
        return {"ok": False, "url": url, "error": str(exc)}
