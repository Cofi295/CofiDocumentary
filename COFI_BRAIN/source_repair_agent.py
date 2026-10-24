"""Durable full-access Codex/Gemini source repair for COFI Documentary."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import RLock, Thread
from typing import Any, Callable, Sequence
from types import SimpleNamespace
from uuid import uuid4
import json
import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import time
import traceback


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SourceRepairAgent:
    _SOURCE_SUFFIXES = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
        ".json", ".toml", ".yaml", ".yml", ".txt",
    }
    _IGNORED_SOURCE_DIRS = {
        ".git", ".producer", "__pycache__", "data", "media", "workspaces",
        "node_modules",
    }
    def __init__(self, project_root: str, *, runner: Callable[..., Any] | None = None,
                 executable_finder: Callable[[str], str | None] | None = None,
                 test_command: Sequence[str] | None = None, timeout_seconds: int | None = None):
        self.project_root = Path(project_root).resolve()
        self.log_dir = self.project_root / "COFI_BRAIN" / "memory"
        self.permission_file = self.project_root / "COFI_BRAIN" / "knowledge" / "codex_permissions.json"
        self.jobs_dir = self.project_root / ".producer" / "source_repairs"
        self._runner = runner or subprocess.run
        self._find = executable_finder or shutil.which
        configured = str(os.getenv("COFI_REPAIR_TEST_COMMAND") or "").strip()
        self.test_command = list(test_command) if test_command else (
            shlex.split(configured, posix=os.name != "nt") if configured else
            [sys.executable, "-m", "pytest", "-q", "tests/test_source_repair_agent.py",
             "tests/test_api.py", "--basetemp=.pytest_source_repair"]
        )
        self.timeout_seconds = int(timeout_seconds or os.getenv("COFI_REPAIR_TIMEOUT_SECONDS", "1800"))
        self._lock = RLock()
        self._threads: dict[str, Thread] = {}

    def get_capabilities(self) -> dict[str, Any]:
        return {"enabled": True, "project_root": str(self.project_root),
                "providers": ["codex", "gemini", "auto"], "read_source": True,
                "write_source": True, "run_commands": True, "run_tests": True,
                "read_logs": True, "restart_application": True,
                "background_jobs": True, "independent_verification": True,
                "destructive_changes": False}

    def save_capabilities(self) -> None:
        self._write_json(self.permission_file, self.get_capabilities())

    def _source_snapshot(self) -> dict[str, str]:
        snapshot: dict[str, str] = {}
        for path in self.project_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in self._SOURCE_SUFFIXES:
                continue
            relative = path.relative_to(self.project_root)
            if any(part in self._IGNORED_SOURCE_DIRS or part.startswith(".pytest") for part in relative.parts):
                continue
            try:
                snapshot[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
        return snapshot

    @staticmethod
    def _changed_sources(before: dict[str, str], after: dict[str, str]) -> list[str]:
        return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)

    def _path(self, repair_id: str) -> Path:
        value = str(repair_id or "").strip()
        if not value or not all(c.isalnum() or c in "-_" for c in value):
            raise ValueError("Mã repair không hợp lệ.")
        return self.jobs_dir / value / "job.json"

    def _save(self, job: dict[str, Any]) -> dict[str, Any]:
        job["updated_at"] = _now()
        persisted = dict(job)
        persisted.pop("stream_events", None)
        persisted.pop("progress_percent", None)
        with self._lock:
            self._write_json(self._path(job["id"]), persisted)
        return dict(job)

    def _append_live_event(self, job: dict[str, Any], event: dict[str, str]) -> None:
        live = job.get("live") if isinstance(job.get("live"), dict) else {}
        events = live.get("events") if isinstance(live.get("events"), list) else []
        events.append({"at": _now(), **event})
        live["events"] = events[-80:]
        live["event_count"] = len(events)
        job["live"] = live
        self._save(job)

    def create_job(self, error: str, source: str = "", provider: str = "auto") -> dict[str, Any]:
        error, provider = str(error or "").strip(), str(provider or "auto").strip().lower()
        if not error:
            raise ValueError("Thiếu mô tả lỗi cần sửa code.")
        if provider not in {"auto", "codex", "gemini"}:
            raise ValueError("Provider sửa code phải là codex, gemini hoặc auto.")
        now = _now()
        return self._save({"id": f"repair-{uuid4().hex[:12]}", "error": error,
                           "source": str(source or "chat").strip() or "chat", "provider": provider,
                           "provider_used": None, "status": "queued", "created_at": now,
                           "updated_at": now, "started_at": None, "finished_at": None,
                           "attempts": [], "verification": None, "error_message": None})

    def start_job(self, error: str, source: str = "", provider: str = "auto") -> dict[str, Any]:
        job = self.create_job(error, source, provider)
        thread = Thread(target=self.execute_job, args=(job["id"],), daemon=True, name=job["id"])
        with self._lock:
            self._threads[job["id"]] = thread
        thread.start()
        return job

    def get_job(self, repair_id: str) -> dict[str, Any]:
        path = self._path(repair_id)
        if not path.exists():
            raise KeyError(repair_id)
        job = json.loads(path.read_text(encoding="utf-8"))
        job["stream_events"] = self._stream_events(job)
        status = str(job.get("status") or "queued")
        job["progress_percent"] = {
            "queued": 2, "running": min(82, 8 + len(job["stream_events"])),
            "verifying": 92, "fixed": 100, "failed": 100,
        }.get(status, 0)
        return job

    @staticmethod
    def _event_summary(payload: dict[str, Any]) -> dict[str, str] | None:
        event_type = str(payload.get("type") or payload.get("event") or "").lower()
        item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
        update = payload.get("step_update") if isinstance(payload.get("step_update"), dict) else {}
        if event_type in {"item.started", "item.completed"}:
            item_type = str(item.get("type") or "")
            if item_type == "command_execution":
                return {"kind": "command", "message": str(item.get("command") or "Đang chạy lệnh")[:600]}
            if item_type == "agent_message":
                return {"kind": "message", "message": str(item.get("text") or "")[:600]}
        if event_type == "step_update":
            state = str(update.get("state") or "").lower()
            tool = str(update.get("tool_name") or (update.get("tool_info") or {}).get("name") or "công cụ")
            if str(update.get("step_type") or "") == "tool":
                return {"kind": "tool", "message": f"{tool} · {state or 'running'}"}
            if str(update.get("step_type") or "") == "agent_response" and state:
                return {"kind": "message", "message": f"AI response · {state}"}
        if event_type == "result":
            result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
            message = str(result.get("response") or payload.get("message") or "AI đã trả kết quả")
            return {"kind": "result", "message": message[:600]}
        return None

    def _stream_events(self, job: dict[str, Any], limit: int = 80) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for attempt in job.get("attempts") or []:
            path_value = attempt.get("event_log")
            if not path_value:
                continue
            try:
                lines = Path(str(path_value)).read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line in lines[-limit:]:
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    text = line.strip()
                    if text:
                        events.append({"kind": "log", "message": text[:600]})
                    continue
                if isinstance(payload, dict):
                    summary = self._event_summary(payload)
                    if summary and summary.get("message"):
                        events.append(summary)
        return events[-limit:]

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        jobs = []
        for path in self.jobs_dir.glob("*/job.json") if self.jobs_dir.exists() else []:
            try:
                jobs.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError):
                continue
        return sorted(jobs, key=lambda x: str(x.get("created_at") or ""), reverse=True)[:max(1, int(limit))]

    def _prompt(self, job: dict[str, Any]) -> str:
        return f"""You are the autonomous senior repair engineer for COFI Documentary.
Project root: {self.project_root}
Failure source: {job['source']}
Failure: {job['error']}

Work directly inside this project root. You are authorized to read and edit source, inspect logs,
run commands, and run tests. Diagnose the root cause, reproduce it with a focused failing test when
possible, apply the smallest complete fix, and run relevant tests. Preserve unrelated user changes
and data. Do not change anything outside the project root. Do not stop at a plan: fix and verify it.
End with a concise summary of files changed and tests run."""

    def _command(self, provider: str, prompt: str) -> tuple[list[str], str | None]:
        if provider == "codex":
            executable = self._find(provider)
            if not executable:
                raise FileNotFoundError(f"Không tìm thấy {provider} CLI trong PATH.")
            return [executable, "exec", "--dangerously-bypass-approvals-and-sandbox",
                    "--skip-git-repo-check", "-C", str(self.project_root), "-"], prompt
        configured_agy = str(os.getenv("COFI_ANTIGRAVITY_BIN") or "").strip()
        shared_agy = self.project_root.parent / "agy" / "bin" / "agy.exe"
        agy = configured_agy or self._find("agy") or (str(shared_agy) if shared_agy.exists() else "") or (str(local_agy) if local_agy.exists() else "")
        if agy:
            return [str(agy), "--dangerously-skip-permissions", "--input-format", "text",
                    "--output-format", "stream-json"], prompt
        # The old Gemini OAuth CLI path can be installed as gemini.cmd but is
        # rejected by Google with UNSUPPORTED_CLIENT for this workflow. Keep
        # repair jobs on the supported Antigravity transport instead of silently
        # launching the invalid legacy client.
        raise FileNotFoundError("Không tìm thấy Antigravity CLI (agy). Gemini CLI cũ bị vô hiệu cho source repair vì UNSUPPORTED_CLIENT.")

    def _run(self, command: list[str], input_text: str | None = None) -> Any:
        kwargs: dict[str, Any] = {
            "cwd": str(self.project_root),
            "input": input_text,
            "text": True,
            "capture_output": True,
            "timeout": self.timeout_seconds,
            "check": False,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
            startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
            kwargs["startupinfo"] = startupinfo
        return self._runner(command, **kwargs)

    def _add_attempt(self, job: dict[str, Any], provider: str, command: list[str], result: Any) -> None:
        directory = self._path(job["id"]).parent
        number = len(job["attempts"]) + 1
        out, err = directory / f"attempt-{number}-{provider}.stdout.log", directory / f"attempt-{number}-{provider}.stderr.log"
        out.write_text(str(result.stdout or ""), encoding="utf-8")
        err.write_text(str(result.stderr or ""), encoding="utf-8")
        job["attempts"].append({"provider": provider, "returncode": int(result.returncode),
                                "command": command, "stdout_log": str(out), "stderr_log": str(err)})
        self._save(job)

    def _run_attempt(self, job: dict[str, Any], provider: str, command: list[str], input_text: str | None) -> Any:
        if self._runner is not subprocess.run:
            result = self._run(command, input_text)
            self._add_attempt(job, provider, command, result)
            return result

        directory = self._path(job["id"]).parent
        number = len(job["attempts"]) + 1
        event_log = directory / f"attempt-{number}-{provider}.events.jsonl"
        stdout_log = directory / f"attempt-{number}-{provider}.stdout.log"
        stderr_log = directory / f"attempt-{number}-{provider}.stderr.log"
        attempt = {
            "provider": provider, "returncode": None, "status": "running", "command": command,
            "event_log": str(event_log), "stdout_log": str(stdout_log), "stderr_log": str(stderr_log),
        }
        job["attempts"].append(attempt)
        job["live"] = {"stage": "coding", "message": f"{provider.title()} đang khởi động…", "event_count": 0}
        self._save(job)
        shell = str(command[0]).lower().endswith((".cmd", ".bat"))
        launch: Any = subprocess.list2cmdline(command) if shell else command
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
            startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        process = subprocess.Popen(
            launch, cwd=str(self.project_root), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", shell=shell,
            creationflags=creationflags, startupinfo=startupinfo,
        )
        assert process.stdout is not None
        if process.stdin is not None:
            if input_text:
                process.stdin.write(input_text)
            process.stdin.close()
        started = time.monotonic()
        last_saved = 0.0
        count = 0
        with event_log.open("w", encoding="utf-8") as events, stdout_log.open("w", encoding="utf-8") as output:
            for line in process.stdout:
                output.write(line)
                output.flush()
                events.write(line)
                events.flush()
                count += 1
                now = time.monotonic()
                if now - last_saved >= 0.35:
                    summary = None
                    try:
                        payload = json.loads(line)
                        summary = self._event_summary(payload) if isinstance(payload, dict) else None
                    except json.JSONDecodeError:
                        pass
                    job["live"] = {
                        "stage": "coding", "message": (summary or {}).get("message") or f"Đã nhận {count} sự kiện CLI",
                        "event_count": count, "elapsed_seconds": round(now - started, 1),
                    }
                    self._save(job)
                    last_saved = now
        returncode = process.wait(timeout=self.timeout_seconds)
        attempt.update(returncode=int(returncode), status="completed" if returncode == 0 else "failed")
        job["live"] = {
            "stage": "coding", "message": f"{provider.title()} đã kết thúc với mã {returncode}",
            "event_count": count, "elapsed_seconds": round(time.monotonic() - started, 1),
        }
        self._save(job)
        return SimpleNamespace(returncode=returncode, stdout=stdout_log.read_text(encoding="utf-8", errors="replace"), stderr="")

    def execute_job(self, repair_id: str) -> dict[str, Any]:
        job = self.get_job(repair_id)
        if job.get("status") in {"fixed", "failed"}:
            return job
        job.update(status="running", started_at=_now(), error_message=None)
        self._save(job)
        selected = None
        source_before = self._source_snapshot()
        try:
            # A manually selected provider is a hard contract. Do not silently
            # fail over to another model because that makes the UI report a
            # different worker than the user requested.
            order = [job["provider"]] if job["provider"] != "auto" else ["codex", "gemini"]
            self._append_live_event(job, {
                "kind": "provider",
                "message": f"Đã khóa provider: {job['provider']}. Danh sách chạy: {', '.join(order)}",
            })
            for provider in order:
                try:
                    command, input_text = self._command(provider, self._prompt(job))
                    result = self._run_attempt(job, provider, command, input_text)
                    self._append_live_event(job, {
                        "kind": "provider_result",
                        "message": f"{provider.title()} kết thúc với mã {int(result.returncode)}.",
                    })
                    if int(result.returncode) == 0:
                        selected = provider
                        break
                except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
                    job["attempts"].append({"provider": provider, "returncode": None, "error": str(exc)})
                    self._save(job)
            if not selected:
                raise RuntimeError("Codex/Gemini CLI không sửa thành công. Xem attempt logs.")
            source_changes = self._changed_sources(source_before, self._source_snapshot())
            job["source_changes"] = source_changes
            self._save(job)
            if not source_changes:
                raise RuntimeError("CLI kết thúc nhưng không thay đổi file mã nguồn nào; không thể xác nhận đã sửa code.")
            job.update(provider_used=selected, status="verifying")
            job["live"] = {"stage": "verifying", "message": "Đang chạy kiểm thử độc lập…", "event_count": len(self._stream_events(job))}
            self._save(job)
            check = self._run(self.test_command)
            log = self._path(job["id"]).parent / "verification.log"
            log.write_text(str(check.stdout or "") + "\n" + str(check.stderr or ""), encoding="utf-8")
            job["verification"] = {"command": self.test_command, "returncode": int(check.returncode), "log": str(log)}
            if int(check.returncode) != 0:
                raise RuntimeError(f"Kiểm thử độc lập thất bại với mã {check.returncode}.")
            job.update(status="fixed", finished_at=_now(), error_message=None)
            job["live"] = {"stage": "fixed", "message": "Sửa code và kiểm thử đã đạt.", "event_count": len(self._stream_events(job))}
        except Exception as exc:
            job.update(status="failed", finished_at=_now(), error_message=str(exc), error=str(exc))
            job["live"] = {"stage": "failed", "message": str(exc), "event_count": len(self._stream_events(job))}
            (self._path(job["id"]).parent / "controller-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        finally:
            with self._lock:
                self._threads.pop(repair_id, None)
        return self._save(job)

    def record_result(self, job: dict[str, Any], result: str) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        with (self.log_dir / "source_repairs.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"job": job, "result": result}, ensure_ascii=False) + "\n")

    def capture_exception(self, exc: Exception, source: str = "") -> dict[str, Any]:
        return self.create_job("".join(traceback.format_exception_only(type(exc), exc)).strip(), source)

    def save_patch_plan(self, job: dict[str, Any], actions: list[str]) -> None:
        self.record_result(job, json.dumps({"type": "patch_plan", "actions": actions}, ensure_ascii=False))

    def mark_fixed(self, job: dict[str, Any], summary: str) -> None:
        target = self.get_job(job["id"]) if job.get("id") else dict(job)
        target.update(status="fixed", finished_at=_now())
        self._save(target)
        self.record_result(target, summary)
