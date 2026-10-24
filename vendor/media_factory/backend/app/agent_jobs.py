from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TERMINAL_STATUSES = {'completed', 'failed', 'cancelled'}
ACTIVE_STATUSES = {'queued', 'running', 'pausing', 'resuming'}


def _now() -> float:
    return time.time()


def _find_executable(*names: str) -> str | None:
    for name in names:
        value = shutil.which(name)
        if value:
            return value
    return None


def _process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    if os.name == 'nt':
        try:
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1)
            startupinfo.wShowWindow = getattr(subprocess, 'SW_HIDE', 0)
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            text = result.stdout.strip()
            return bool(text and 'No tasks are running' not in text and f'"{pid}"' in text)
        except (OSError, subprocess.TimeoutExpired):
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _deep_find_session_id(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ('thread_id', 'session_id', 'conversation_id'):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for nested in value.values():
            found = _deep_find_session_id(nested)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _deep_find_session_id(nested)
            if found:
                return found
    return None


class AgentJobSupervisor:
    def __init__(self, project_root: Path, *, data_dir: Path | None = None, manifest_store: Any | None = None):
        self.project_root = project_root.resolve()
        self.data_dir = (data_dir or self.project_root / 'data' / 'agent-jobs').resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.codex = _find_executable('codex.exe', 'codex')
        self.gemini = _find_executable('gemini.cmd', 'gemini.exe', 'gemini')
        self.manifest_store = manifest_store
        self._processes: dict[str, subprocess.Popen] = {}
        self._handles: dict[str, object] = {}
        self._watchers: dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        self._recover_jobs()

    def engine_status(self) -> dict[str, dict[str, Any]]:
        return {
            'codex': {'available': bool(self.codex), 'executable': self.codex},
            'gemini': {'available': bool(self.gemini), 'executable': self.gemini},
        }

    def _job_dir(self, job_id: str) -> Path:
        return self.data_dir / job_id

    def _record_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / 'job.json'

    def _log_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / 'stdout.jsonl'

    def _last_message_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / 'last_message.txt'

    def _save(self, record: dict[str, Any]) -> dict[str, Any]:
        record['updated_at'] = _now()
        job_dir = self._job_dir(record['id'])
        job_dir.mkdir(parents=True, exist_ok=True)
        temp = job_dir / 'job.json.tmp'
        temp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self._record_path(record['id']))
        return record

    def _load(self, job_id: str) -> dict[str, Any]:
        path = self._record_path(job_id)
        if not path.is_file():
            raise KeyError(f'Unknown agent job: {job_id}')
        return json.loads(path.read_text(encoding='utf-8'))

    def _recover_jobs(self) -> None:
        for path in self.data_dir.glob('*/job.json'):
            try:
                record = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                continue
            record = self._parse_events(record)
            if record.get('status') in ACTIVE_STATUSES:
                if _process_alive(record.get('pid')):
                    record['status'] = 'running'
                    record['recovered'] = True
                else:
                    last_message = self._last_message_path(record['id'])
                    if (
                        record.get('current_step') == 'turn.completed'
                        and last_message.is_file()
                        and last_message.read_text(encoding='utf-8', errors='ignore').strip()
                    ):
                        record['status'] = 'completed'
                        record['pid'] = None
                        record['exit_code'] = 0
                        record['error'] = None
                        record['finished_at'] = record.get('finished_at') or _now()
                    else:
                        record['status'] = 'interrupted'
                        record['pid'] = None
                saved = self._save(record)
                if saved['status'] == 'completed':
                    self._publish_handoff(saved)

    def list_jobs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in self.data_dir.glob('*/job.json'):
            try:
                record = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                continue
            if record.get('stage') == 'codex-chat':
                continue
            records.append(record)
        records.sort(key=lambda item: float(item.get('updated_at') or 0), reverse=True)
        return records[: max(1, min(limit, 500))]

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._parse_events(self._load(job_id))
            last_message = self._last_message_path(job_id)
            completed_turn = (
                record.get('current_step') == 'turn.completed'
                and last_message.is_file()
                and bool(last_message.read_text(encoding='utf-8', errors='ignore').strip())
            )
            if record.get('status') == 'interrupted' and completed_turn:
                record['status'] = 'completed'
                record['pid'] = None
                record['exit_code'] = 0
                record['error'] = None
                record['finished_at'] = record.get('finished_at') or _now()
                saved = self._save(record)
                self._publish_handoff(saved)
                return saved
            if record.get('status') in ACTIVE_STATUSES and record.get('pid') and not _process_alive(record['pid']):
                process = self._processes.get(job_id)
                if process:
                    exit_code = process.poll()
                    if exit_code is not None:
                        return self._finalize_record(record, exit_code)
                else:
                    record['status'] = 'completed' if completed_turn else 'interrupted'
                    record['pid'] = None
                    if completed_turn:
                        record['exit_code'] = 0
                        record['error'] = None
                        record['finished_at'] = record.get('finished_at') or _now()
                    saved = self._save(record)
                    if saved['status'] == 'completed':
                        self._publish_handoff(saved)
                    return saved
            return record

    def create_job(
        self,
        *,
        name: str,
        engine: str,
        stage: str,
        workspace: str,
        prompt: str,
        project_id: str | None = None,
        output_key: str | None = None,
        image_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        engine = engine.strip().lower()
        if engine not in {'codex', 'gemini'}:
            raise ValueError('engine must be codex or gemini')
        if engine == 'codex' and not self.codex:
            raise RuntimeError('Codex CLI is not installed')
        if engine == 'gemini' and not self.gemini:
            raise RuntimeError('Gemini CLI is not installed')
        resolved_workspace = Path(workspace).expanduser().resolve()
        if not resolved_workspace.is_dir():
            raise ValueError(f'Workspace does not exist: {resolved_workspace}')
        if not prompt.strip():
            raise ValueError('prompt cannot be empty')

        resolved_image_paths: list[str] = []
        for raw_path in image_paths or []:
            image_path = Path(str(raw_path)).expanduser().resolve()
            if not image_path.is_file():
                raise ValueError(f'Image attachment does not exist: {image_path}')
            resolved_image_paths.append(str(image_path))

        job_id = uuid.uuid4().hex
        now = _now()
        record = {
            'id': job_id,
            'name': name.strip() or f'{stage} job',
            'engine': engine,
            'stage': stage.strip().lower(),
            'workspace': str(resolved_workspace),
            'prompt': prompt,
            'project_id': project_id,
            'output_key': (output_key or stage).strip().lower(),
            'image_paths': resolved_image_paths,
            'status': 'queued',
            'pid': None,
            'session_id': None,
            'current_step': 'queued',
            'event_count': 0,
            'retry_count': 0,
            'created_at': now,
            'updated_at': now,
            'started_at': None,
            'finished_at': None,
            'exit_code': None,
            'error': None,
            'recovered': False,
            'log_path': str(self._log_path(job_id)),
            'last_message_path': str(self._last_message_path(job_id)),
        }
        self._save(record)
        return self.start(job_id)

    def _build_command(self, record: dict[str, Any], *, resume: bool = False, continuation: str | None = None) -> list[str]:
        engine = record['engine']
        workspace = Path(record['workspace'])
        last_message = str(self._last_message_path(record['id']))
        if engine == 'codex':
            if not self.codex:
                raise RuntimeError('Codex CLI is not installed')
            common: list[str] = [self.codex, 'exec']
            if resume:
                session_id = record.get('session_id')
                if not session_id:
                    raise RuntimeError('This Codex job has no saved session id to resume')
                command = [*common, 'resume', '--json', '-o', last_message]
                for image_path in record.get('image_paths') or []:
                    command.extend(['-i', str(image_path)])
                if not (workspace / '.git').exists():
                    command.append('--skip-git-repo-check')
                command.extend([session_id, continuation or 'Continue the task from the last completed checkpoint.'])
                return command
            command = [*common, '--json', '-C', str(workspace), '-o', last_message]
            for image_path in record.get('image_paths') or []:
                command.extend(['-i', str(image_path)])
            if not (workspace / '.git').exists():
                command.append('--skip-git-repo-check')
            command.append(record['prompt'])
            return command

        if not self.gemini:
            raise RuntimeError('Gemini CLI is not installed')
        # Gemini CLI versions differ. The standard non-interactive form uses -p.
        # Keep the native terminal path available even if a future version changes
        # its streaming flags; persistent JSON event parsing is only enabled when
        # the installed CLI accepts this invocation.
        prompt = continuation if resume and continuation else record['prompt']
        return [self.gemini, '-p', prompt]

    @staticmethod
    def _creation_flags() -> int:
        if os.name != 'nt':
            return 0
        return int(getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)) | int(getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    @staticmethod
    def _startupinfo():
        if os.name != 'nt':
            return None
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= int(getattr(subprocess, 'STARTF_USESHOWWINDOW', 1))
        startupinfo.wShowWindow = int(getattr(subprocess, 'SW_HIDE', 0))
        return startupinfo

    @staticmethod
    def _request_process_stop(process: subprocess.Popen) -> None:
        """Ask the CLI to stop cleanly so remote/session state can settle.

        A hard terminate on Windows can kill the local Codex process before it
        has a chance to cancel/close the active turn. That leaves the persisted
        session resumable on disk but still busy on the remote bridge. Prefer a
        console break (SIGINT on POSIX), then escalate only if the process does
        not exit promptly.
        """
        if process.poll() is not None:
            return

        try:
            if os.name == 'nt':
                ctrl_break = getattr(signal, 'CTRL_BREAK_EVENT', None)
                if ctrl_break is not None:
                    process.send_signal(ctrl_break)
                else:
                    process.terminate()
            else:
                process.send_signal(signal.SIGINT)
        except (OSError, ValueError):
            try:
                process.terminate()
            except OSError:
                return

        def escalate() -> None:
            try:
                process.wait(timeout=8)
                return
            except subprocess.TimeoutExpired:
                pass
            try:
                process.terminate()
                process.wait(timeout=3)
                return
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                process.kill()
            except OSError:
                pass

        threading.Thread(target=escalate, name=f'agent-stop-{process.pid}', daemon=True).start()

    @staticmethod
    def _chatgpt_web_config_path() -> Path | None:
        configured = os.environ.get('CODEX_CHATGPT_WEB_HOME', '').strip()
        candidates: list[Path] = []
        if configured:
            candidates.append(Path(configured).expanduser() / 'config.json')
        candidates.append(Path.home() / '.codex-chatgpt-web' / 'config.json')
        if os.name == 'nt':
            for drive in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                candidates.append(Path(f'{drive}:\\.codex-chatgpt-web\\config.json'))
        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate).lower()
            if key in seen:
                continue
            seen.add(key)
            if candidate.is_file():
                return candidate
        return None

    def _cancel_remote_codex_thread(self, record: dict[str, Any]) -> bool:
        if record.get('engine') != 'codex' or not record.get('session_id'):
            return False
        config_path = self._chatgpt_web_config_path()
        if not config_path:
            return False
        try:
            config = json.loads(config_path.read_text(encoding='utf-8'))
            host = str(config.get('host') or '127.0.0.1').strip()
            port = int(config.get('port') or 17841)
            control_token = str(config.get('controlToken') or '').strip()
            if not control_token:
                return False
            payload = json.dumps({'threadId': record['session_id']}).encode('utf-8')
            request = Request(
                f'http://{host}:{port}/admin/cancel-thread',
                data=payload,
                headers={
                    'authorization': f'Bearer {control_token}',
                    'content-type': 'application/json',
                },
                method='POST',
            )
            with urlopen(request, timeout=12) as response:
                body = json.loads(response.read().decode('utf-8'))
            return body.get('status') == 'ok' and int(body.get('cancelled_browser_turns') or 0) > 0
        except (OSError, ValueError, json.JSONDecodeError, HTTPError, URLError, TimeoutError):
            return False

    def _spawn(self, record: dict[str, Any], *, resume: bool = False, continuation: str | None = None) -> dict[str, Any]:
        command = self._build_command(record, resume=resume, continuation=continuation)
        job_id = record['id']
        job_dir = self._job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        handle = open(self._log_path(job_id), 'a', encoding='utf-8', buffering=1)
        if resume:
            handle.write(json.dumps({'type': 'cofi.resume', 'at': _now(), 'session_id': record.get('session_id')}) + '\n')
        process = subprocess.Popen(
            command,
            cwd=record['workspace'],
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=self._creation_flags(),
            startupinfo=self._startupinfo(),
        )
        self._processes[job_id] = process
        self._handles[job_id] = handle
        record['status'] = 'resuming' if resume else 'running'
        record['pid'] = process.pid
        record['started_at'] = record.get('started_at') or _now()
        record['finished_at'] = None
        record['exit_code'] = None
        record['error'] = None
        record['current_step'] = 'agent running'
        if resume:
            record['retry_count'] = int(record.get('retry_count') or 0) + 1
        self._save(record)

        watcher = threading.Thread(
            target=self._watch,
            args=(job_id, process, handle),
            name=f'agent-job-{job_id[:8]}',
            daemon=True,
        )
        self._watchers[job_id] = watcher
        watcher.start()
        return record

    def start(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._load(job_id)
            if record['status'] in {'running', 'resuming'} and _process_alive(record.get('pid')):
                return record
            if record['status'] in TERMINAL_STATUSES:
                raise RuntimeError(f"Cannot start a {record['status']} job; create a new job or resume an interrupted one")
            return self._spawn(record)

    def _parse_events(self, record: dict[str, Any]) -> dict[str, Any]:
        path = self._log_path(record['id'])
        if not path.is_file():
            return record
        event_count = 0
        session_id = record.get('session_id')
        current_step = record.get('current_step') or 'running'
        try:
            for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event_count += 1
                session_id = session_id or _deep_find_session_id(payload)
                event_type = payload.get('type') if isinstance(payload, dict) else None
                if isinstance(event_type, str) and event_type:
                    current_step = event_type
        except OSError:
            return record
        record['event_count'] = event_count
        record['session_id'] = session_id
        record['current_step'] = current_step
        return record

    def _watch(self, job_id: str, process: subprocess.Popen, handle: object) -> None:
        while process.poll() is None:
            time.sleep(0.5)
            with self._lock:
                try:
                    record = self._parse_events(self._load(job_id))
                    if record.get('status') == 'resuming':
                        record['status'] = 'running'
                    self._save(record)
                except Exception:
                    pass

        exit_code = process.returncode
        with self._lock:
            try:
                record = self._load(job_id)
                # get_job() may have already finalized the stopped process and a
                # resume may now own this same job id. Never let the old watcher
                # overwrite the state of the newer process.
                if record.get('pid') == process.pid:
                    self._finalize_record(record, exit_code)
            finally:
                try:
                    handle.close()
                except Exception:
                    pass
                if self._handles.get(job_id) is handle:
                    self._handles.pop(job_id, None)
                if self._processes.get(job_id) is process:
                    self._processes.pop(job_id, None)
                if self._watchers.get(job_id) is threading.current_thread():
                    self._watchers.pop(job_id, None)

    def _finalize_record(self, record: dict[str, Any], exit_code: int) -> dict[str, Any]:
        record = self._parse_events(record)
        if record.get('status') in {'pausing', 'paused'}:
            record['status'] = 'paused'
        elif record.get('status') == 'cancelled':
            pass
        elif exit_code == 0:
            record['status'] = 'completed'
            record['error'] = None
        else:
            record['status'] = 'failed'
            record['error'] = f'Agent process exited with code {exit_code}'
        record['pid'] = None
        record['exit_code'] = exit_code
        record['finished_at'] = _now() if record['status'] in TERMINAL_STATUSES else None
        saved = self._save(record)
        if saved['status'] == 'completed':
            self._publish_handoff(saved)
        return saved

    def _publish_handoff(self, record: dict[str, Any]) -> None:
        if not self.manifest_store or not record.get('project_id'):
            return
        try:
            self.manifest_store.update_stage(
                record['project_id'],
                record.get('output_key') or record.get('stage') or 'research',
                {
                    'status': 'completed',
                    'job_id': record['id'],
                    'engine': record['engine'],
                    'session_id': record.get('session_id'),
                    'last_message_path': record.get('last_message_path'),
                    'log_path': record.get('log_path'),
                    'workspace': record.get('workspace'),
                },
                advance=True,
            )
        except Exception:
            # A finished worker must stay finished even if project metadata cannot
            # be published. The job log remains the source of truth for recovery.
            pass

    def pause(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._parse_events(self._load(job_id))
            if record.get('status') not in {'running', 'resuming'}:
                return record
            process = self._processes.get(job_id)
            record['status'] = 'pausing'
            record['current_step'] = 'pause requested'
            self._save(record)
            self._cancel_remote_codex_thread(record)
            if process and process.poll() is None:
                self._request_process_stop(process)
            else:
                record['status'] = 'interrupted'
                record['pid'] = None
                self._save(record)
            return record

    def resume(
        self,
        job_id: str,
        *,
        prompt: str | None = None,
        image_paths: list[str] | None = None,
        project_id: str | None = None,
        output_key: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            record = self._parse_events(self._load(job_id))
            if record['engine'] != 'codex':
                raise RuntimeError('Persistent resume is currently supported for Codex jobs; open Gemini full CLI for native session control')
            if record.get('status') not in {'paused', 'interrupted', 'failed', 'completed'}:
                return record
            if not record.get('session_id'):
                raise RuntimeError('No Codex session id was captured before interruption')
            resolved_image_paths: list[str] = []
            for raw_path in image_paths or []:
                image_path = Path(str(raw_path)).expanduser().resolve()
                if not image_path.is_file():
                    raise ValueError(f'Image attachment does not exist: {image_path}')
                resolved_image_paths.append(str(image_path))
            record['image_paths'] = resolved_image_paths
            if project_id is not None:
                record['project_id'] = project_id
            if output_key:
                record['output_key'] = output_key.strip().lower()
            return self._spawn(record, resume=True, continuation=prompt)

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._load(job_id)
            process = self._processes.get(job_id)
            record['status'] = 'cancelled'
            record['current_step'] = 'cancelled'
            record['finished_at'] = _now()
            self._save(record)
            if process and process.poll() is None:
                self._request_process_stop(process)
            return record

    def read_log(self, job_id: str, *, lines: int = 200) -> dict[str, Any]:
        self._load(job_id)
        path = self._log_path(job_id)
        content = path.read_text(encoding='utf-8', errors='replace').splitlines() if path.is_file() else []
        last_message_path = self._last_message_path(job_id)
        last_message = last_message_path.read_text(encoding='utf-8', errors='replace') if last_message_path.is_file() else ''
        return {
            'id': job_id,
            'path': str(path),
            'lines': content[-max(1, min(lines, 2000)):],
            'last_message': last_message,
        }
