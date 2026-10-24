"""Durable, reconnectable execution state for Cofi Producer Chat."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Event, RLock, Thread
from typing import Any, Callable
from uuid import uuid4
import json
import os
import time
import traceback


TERMINAL_CHAT_RUN_STATUSES = {"succeeded", "failed", "cancelled"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pid_is_alive(pid: int | None) -> bool:
    if not pid or int(pid) <= 0:
        return False
    if int(pid) == os.getpid():
        return True
    try:
        if os.name == "nt":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return int(exit_code.value) == STILL_ACTIVE
                return True
            finally:
                kernel32.CloseHandle(handle)
        else:
            os.kill(int(pid), 0)
            return True
    except Exception:
        return False


class ChatRunManager:
    def __init__(self, root: str | Path, *, recover: bool = True):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._threads: dict[str, Thread] = {}
        self._cancel_events: dict[str, Event] = {}
        if recover:
            self.recover_interrupted()

    def _directory(self, run_id: str) -> Path:
        value = str(run_id or "").strip()
        if not value or not all(char.isalnum() or char in "-_" for char in value):
            raise ValueError("Mã phiên chat không hợp lệ.")
        return self.root / value

    def _state_path(self, run_id: str) -> Path:
        return self._directory(run_id) / "run.json"

    def _events_path(self, run_id: str) -> Path:
        return self._directory(run_id) / "events.jsonl"

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            for attempt in range(8):
                try:
                    os.replace(temporary, path)
                    return
                except PermissionError:
                    if attempt == 7:
                        raise
                    time.sleep(min(0.05 * 2**attempt, 0.4))
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def create(self, payload: dict[str, Any], provider: str) -> dict[str, Any]:
        selected = str(provider or "auto").strip().lower()
        if selected not in {"codex", "gemini", "auto"}:
            raise ValueError("Provider chat phải là codex, gemini hoặc auto.")
        now = _now()
        run = {
            "id": f"chat-{uuid4().hex[:16]}",
            "provider": selected,
            "status": "queued",
            "owner_pid": os.getpid(),
            "payload": dict(payload),
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "finished_at": None,
            "last_seq": 0,
            "result": None,
            "error": None,
            "cancel_requested": False,
        }
        with self._lock:
            self._write_json(self._state_path(run["id"]), run)
            self._events_path(run["id"]).touch()
        return dict(run)

    def get(self, run_id: str) -> dict[str, Any]:
        path = self._state_path(run_id)
        if not path.exists():
            raise KeyError(run_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _update(self, run_id: str, **changes: Any) -> dict[str, Any]:
        with self._lock:
            run = self.get(run_id)
            if run.get("status") in TERMINAL_CHAT_RUN_STATUSES and changes.get("status") == "cancelling":
                changes.pop("status", None)
            run.update(changes)
            run["updated_at"] = _now()
            self._write_json(self._state_path(run_id), run)
            return dict(run)

    def append_event(self, run_id: str, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            run = self.get(run_id)
            record = dict(event)
            record["seq"] = int(run.get("last_seq") or 0) + 1
            record.setdefault("at", _now())
            with self._events_path(run_id).open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
            run["last_seq"] = record["seq"]
            run["updated_at"] = _now()
            self._write_json(self._state_path(run_id), run)
            return record

    def events(self, run_id: str, after: int = 0) -> list[dict[str, Any]]:
        self.get(run_id)
        records: list[dict[str, Any]] = []
        try:
            lines = self._events_path(run_id).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return records
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict) and int(event.get("seq") or 0) > int(after or 0):
                records.append(event)
        return records

    def latest_active(self, *, selected_job_id: str | None = None) -> dict[str, Any] | None:
        selected_scope = str(selected_job_id or "").strip()
        candidates: list[dict[str, Any]] = []
        for path in self.root.glob("*/run.json"):
            try:
                run = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            payload = run.get("payload") if isinstance(run.get("payload"), dict) else {}
            run_scope = str(payload.get("selected_job_id") or "").strip()
            if run_scope != selected_scope or run.get("status") in TERMINAL_CHAT_RUN_STATUSES:
                continue
            candidates.append(run)
        if not candidates:
            return None
        candidates.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return candidates[0]

    def start(
        self,
        payload: dict[str, Any],
        provider: str,
        worker: Callable[[dict[str, Any], Callable[[dict[str, Any]], dict[str, Any]], Event], dict[str, Any]],
    ) -> dict[str, Any]:
        selected_scope = str((payload or {}).get("selected_job_id") or "").strip()
        with self._lock:
            for existing_id, ev in list(self._cancel_events.items()):
                try:
                    existing_run = self.get(existing_id)
                except Exception:
                    continue
                ex_payload = existing_run.get("payload") if isinstance(existing_run.get("payload"), dict) else {}
                ex_scope = str(ex_payload.get("selected_job_id") or "").strip()
                if ex_scope == selected_scope and existing_run.get("status") not in TERMINAL_CHAT_RUN_STATUSES:
                    ev.set()
        run = self.create(payload, provider)
        run_id = run["id"]
        cancel_event = Event()

        def execute() -> None:
            self._update(run_id, status="running", started_at=_now())
            self.append_event(run_id, {"type": "started", "provider": provider, "message": f"{provider.title()} đã bắt đầu phiên làm việc."})
            try:
                result = worker(self.get(run_id), lambda event: self.append_event(run_id, event), cancel_event)
                if cancel_event.is_set():
                    self.append_event(run_id, {"type": "cancelled", "message": "Đã dừng phiên làm việc theo yêu cầu."})
                    self._update(run_id, status="cancelled", result=None, finished_at=_now())
                else:
                    self.append_event(run_id, {"type": "result", "result": result})
                    self._update(run_id, status="succeeded", result=result, finished_at=_now())
            except Exception as exc:
                if cancel_event.is_set():
                    self.append_event(run_id, {"type": "cancelled", "message": "Đã dừng phiên làm việc theo yêu cầu."})
                    self._update(run_id, status="cancelled", result=None, error=None, finished_at=_now())
                else:
                    (self._directory(run_id) / "controller-error.log").write_text(traceback.format_exc(), encoding="utf-8")
                    self.append_event(run_id, {"type": "error", "message": str(exc)})
                    self._update(run_id, status="failed", error=str(exc), finished_at=_now())
            finally:
                with self._lock:
                    self._threads.pop(run_id, None)
                    self._cancel_events.pop(run_id, None)

        thread = Thread(target=execute, daemon=True, name=run_id)
        with self._lock:
            self._threads[run_id] = thread
            self._cancel_events[run_id] = cancel_event
        thread.start()
        return run

    def cancel(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            run = self.get(run_id)
            if run.get("status") in TERMINAL_CHAT_RUN_STATUSES:
                return run
            self._update(run_id, cancel_requested=True, status="cancelling")
            self.append_event(run_id, {"type": "cancel_requested", "message": "Đang yêu cầu dừng phiên làm việc…"})
            event = self._cancel_events.get(run_id)
            if event:
                event.set()
        return self.get(run_id)

    def wait(self, run_id: str, timeout: float | None = None) -> dict[str, Any]:
        with self._lock:
            thread = self._threads.get(run_id)
        if thread:
            thread.join(timeout=timeout)
        return self.get(run_id)

    def recover_interrupted(self) -> None:
        now_ts = time.time()
        for path in self.root.glob("*/run.json"):
            try:
                run = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if run.get("status") in TERMINAL_CHAT_RUN_STATUSES:
                continue
            owner_pid = run.get("owner_pid")
            if owner_pid and _pid_is_alive(int(owner_pid)) and int(owner_pid) != os.getpid():
                continue
            if not owner_pid:
                try:
                    if now_ts - path.stat().st_mtime < 300:
                        continue
                except OSError:
                    pass
            run.update(
                status="failed",
                finished_at=_now(),
                updated_at=_now(),
                error="Phiên chat bị gián đoạn khi ứng dụng khởi động lại. Hãy gửi lại yêu cầu để chạy một phiên mới.",
            )
            self._write_json(path, run)

    def stream(self, run_id: str, after: int = 0, *, heartbeat_seconds: float = 10.0):
        sequence = int(after or 0)
        last_heartbeat = time.monotonic()
        while True:
            records = self.events(run_id, sequence)
            for record in records:
                sequence = max(sequence, int(record.get("seq") or 0))
                yield record
            run = self.get(run_id)
            if run.get("status") in TERMINAL_CHAT_RUN_STATUSES and sequence >= int(run.get("last_seq") or 0):
                break
            if time.monotonic() - last_heartbeat >= heartbeat_seconds:
                yield {"type": "heartbeat", "seq": sequence, "at": _now()}
                last_heartbeat = time.monotonic()
            time.sleep(0.15)
