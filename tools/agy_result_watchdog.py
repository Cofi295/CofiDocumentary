"""Background watchdog that prevents hung single-turn agy_real.exe (--input-format text)
processes from wedging CofiDocumentary before a server restart."""
from __future__ import annotations

import ctypes
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(r"B:\ALL_TOOLS\CofiDocumentary")
PROCESS_TERMINATE = 0x0001


def terminate_with_exit_code_zero(pid: int) -> bool:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, int(pid))
    if not handle:
        return False
    try:
        return bool(kernel32.TerminateProcess(handle, 0))
    finally:
        kernel32.CloseHandle(handle)


def list_text_agy_processes() -> list[dict]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process -Filter \"Name='agy_real.exe'\" | "
            "Where-Object { $_.CommandLine -match '--input-format\\s+text' } | "
            "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
        ),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8, creationflags=0x08000000)
        raw = (res.stdout or "").strip()
        if not raw:
            return []
        data = json.loads(raw)
        return [data] if isinstance(data, dict) else list(data)
    except Exception:
        return []


def kill_child_mcp_nodes(parent_pid: int) -> None:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            f"Get-CimInstance Win32_Process -Filter \"ParentProcessId={int(parent_pid)} AND Name='node.exe'\" | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        ),
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=5, creationflags=0x08000000)
    except Exception:
        pass


def active_events_files() -> list[Path]:
    files: list[Path] = []
    prod = ROOT / ".producer"
    if prod.exists():
        files.extend(prod.glob("*/events.jsonl"))
    ws = ROOT / "workspaces"
    if ws.exists():
        files.extend(ws.glob("*/.producer/*/events.jsonl"))
    return files


def has_completed_result(log_path: Path) -> bool:
    try:
        if not log_path.exists():
            return False
        last_path = log_path.parent / "last_message.txt"
        # If last_message.txt was already updated at or after events.jsonl, this run is already done
        if last_path.exists() and last_path.stat().st_mtime >= log_path.stat().st_mtime:
            return False
        text = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for raw_line in reversed(text[-10:]):
            line = raw_line.strip()
            if not line:
                continue
            if '"event":"result"' in line.replace(" ", "") or '"type":"result"' in line.replace(" ", ""):
                evt = json.loads(line)
                if isinstance(evt, dict) and str(evt.get("event") or evt.get("type") or "").lower() == "result":
                    return True
    except Exception:
        return False
    return False


def main() -> None:
    seen_completed_at: dict[tuple[int, str], float] = {}
    while True:
        try:
            procs = list_text_agy_processes()
            if procs:
                completed_logs = [p for p in active_events_files() if has_completed_result(p)]
                now = time.time()
                for proc in procs:
                    pid = int(proc.get("ProcessId") or 0)
                    if not pid:
                        continue
                    for log_path in completed_logs:
                        key = (pid, str(log_path))
                        first_seen = seen_completed_at.setdefault(key, now)
                        if now - first_seen >= 4.0:
                            kill_child_mcp_nodes(pid)
                            time.sleep(0.5)
                            terminate_with_exit_code_zero(pid)
                            seen_completed_at.pop(key, None)
        except Exception:
            pass
        time.sleep(2.5)


if __name__ == "__main__":
    main()
