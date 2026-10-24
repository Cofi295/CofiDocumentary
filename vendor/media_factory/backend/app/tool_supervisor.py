from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Literal


ToolKind = Literal['web', 'native', 'cli']


@dataclass(frozen=True)
class ToolDefinition:
    id: str
    name: str
    stage: str
    kind: ToolKind
    root: Path
    command: tuple[str, ...] = ()
    url: str | None = None
    health_url: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    description: str = ''
    executable: str | None = None


@dataclass
class ToolProcess:
    process: subprocess.Popen | None = None
    log_handle: object | None = None
    started_at: float | None = None
    owned: bool = False


def _first_existing(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.is_file()), None)


def _resolve_python(root: Path) -> str:
    local = _first_existing([
        root / '.venv' / 'Scripts' / 'python.exe',
        root / 'venv' / 'Scripts' / 'python.exe',
    ])
    return str(local) if local else sys.executable


def _resolve_command(name: str) -> str | None:
    return shutil.which(name)


def _http_alive(url: str, timeout: float = 0.45) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= int(getattr(response, 'status', 200)) < 500
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _canonical_cofivoice_url() -> str:
    return os.environ.get('COFI_VOICE_URL', '').strip().rstrip('/') or 'http://127.0.0.1:8000'


def _find_shared_cofivoice_url(configured: str | None = None) -> str | None:
    configured = str(configured or '').strip().rstrip('/')
    candidates = [configured] if configured else []
    candidates.extend(['http://127.0.0.1:8000', 'http://127.0.0.1:8776'])
    seen: set[str] = set()
    for base_url in candidates:
        if not base_url or base_url in seen:
            continue
        seen.add(base_url)
        if _http_alive(f'{base_url}/api/health'):
            return base_url
    return None


def build_default_tool_definitions(project_root: Path) -> list[ToolDefinition]:
    tools_root = Path(os.environ.get('COFI_TOOLS_ROOT', project_root.parent)).resolve()
    radar_root = tools_root / 'CofiRadar'
    voice_root = tools_root / 'CofiVoice'
    voice_url = _canonical_cofivoice_url()
    voice_port = urlparse(voice_url).port or 8000
    original_spt_root = tools_root / 'SRT-To-Prompt_backup_20260731'
    spt_root = project_root / 'vendor' / 'spt'
    spt_python = _resolve_python(original_spt_root)
    remotion_root = tools_root / 'CofiRemotion'
    capcut_exe = tools_root / '[Windows] AutoCapCut dành cho windows' / 'AutoCapCut_v43' / 'AutoCapCut.exe'

    npx = _resolve_command('npx.cmd') or _resolve_command('npx') or 'npx.cmd'
    codex = _resolve_command('codex.exe') or _resolve_command('codex') or 'codex'
    gemini = _resolve_command('gemini.cmd') or _resolve_command('gemini') or 'gemini'

    return [
        ToolDefinition(
            id='cofi-radar',
            name='CofiRadar',
            stage='radar',
            kind='web',
            root=radar_root,
            command=(_resolve_python(radar_root), 'app.py'),
            url='http://127.0.0.1:8775/',
            health_url='http://127.0.0.1:8775/api/health',
            env={'COFI_RADAR_PORT': '8775'},
            description='YouTube trend intelligence, niche validation, channel planning, Today queue and evidence library.',
        ),
        ToolDefinition(
            id='cofi-voice',
            name='CofiVoice',
            stage='voice',
            kind='web',
            root=voice_root,
            command=(_resolve_python(voice_root), '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', str(voice_port)),
            url=f'{voice_url}/',
            health_url=f'{voice_url}/api/health',
            env={'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'},
            description='Full CofiVoice UI and API: TTS jobs, resume/reroll, voice cloning, voice design, previews and downloads.',
        ),
        ToolDefinition(
            id='cofi-remotion',
            name='CofiRemotion',
            stage='editor',
            kind='web',
            root=remotion_root,
            command=(npx, 'remotion', 'studio', '--port=8777', '--no-open'),
            url='http://127.0.0.1:8777/',
            health_url='http://127.0.0.1:8777/',
            description='Full Remotion Studio for programmable editing, preview, motion design, subtitles and render workflows.',
        ),
        ToolDefinition(
            id='spt-scenes',
            name='SPT · Prompt + SRT',
            stage='scenes',
            kind='native',
            root=spt_root,
            command=(spt_python, 'app.py'),
            env={'COFI_STUDIO_SPT_STAGE': 'scenes'},
            description='SPT stage 1 with ASR/SRT, merge modes, prompt generation, hook analysis, styles, batch and exports.',
        ),
        ToolDefinition(
            id='spt-editor',
            name='SPT · Assembly + CapCut',
            stage='editor',
            kind='native',
            root=spt_root,
            command=(spt_python, 'app.py'),
            env={'COFI_STUDIO_SPT_STAGE': 'editor'},
            description='SPT stage 2 with media mapping, transitions, presets, timeline preview and CapCut project creation.',
        ),
        ToolDefinition(
            id='auto-capcut',
            name='AutoCapCut',
            stage='export',
            kind='native',
            root=capcut_exe.parent,
            command=(str(capcut_exe),),
            executable=str(capcut_exe),
            description='Original AutoCapCut desktop application, launched unchanged for full feature parity.',
        ),
        ToolDefinition(
            id='codex-cli',
            name='Codex CLI',
            stage='research',
            kind='cli',
            root=project_root,
            command=(codex,),
            executable=codex,
            description='Full native Codex CLI in a Windows Terminal tab.',
        ),
        ToolDefinition(
            id='gemini-cli',
            name='Gemini CLI',
            stage='research',
            kind='cli',
            root=project_root,
            command=(gemini,),
            executable=None if gemini == 'gemini' else gemini,
            description='Full native Gemini CLI in a Windows Terminal tab when installed.',
        ),
    ]


class ToolSupervisor:
    def __init__(self, project_root: Path, *, definitions: list[ToolDefinition] | None = None, log_dir: Path | None = None):
        self.project_root = project_root.resolve()
        self.definitions = {item.id: item for item in (definitions or build_default_tool_definitions(self.project_root))}
        self.log_dir = (log_dir or self.project_root / 'data' / 'tool-logs').resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._processes: dict[str, ToolProcess] = {}
        self._lock = RLock()

    def _definition(self, tool_id: str) -> ToolDefinition:
        try:
            return self.definitions[tool_id]
        except KeyError as exc:
            raise KeyError(f'Unknown tool: {tool_id}') from exc

    @staticmethod
    def _url_alive(url: str | None, timeout: float = 0.45) -> bool:
        if not url:
            return False
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return 200 <= int(response.status) < 500
        except (urllib.error.URLError, OSError, TimeoutError, socket.timeout, ValueError):
            return False

    @staticmethod
    def _command_available(definition: ToolDefinition) -> bool:
        if definition.kind == 'cli':
            executable = definition.executable or definition.command[0] if definition.command else None
            return bool(executable and (Path(executable).is_file() or shutil.which(executable)))
        if definition.executable:
            return Path(definition.executable).is_file()
        if not definition.root.exists() or not definition.command:
            return False
        executable = definition.command[0]
        return Path(executable).is_file() or bool(shutil.which(executable))

    def _owned_process(self, tool_id: str) -> ToolProcess | None:
        entry = self._processes.get(tool_id)
        if not entry or not entry.process:
            return entry
        if entry.process.poll() is not None:
            try:
                if entry.log_handle:
                    entry.log_handle.close()
            except Exception:
                pass
            entry.owned = False
        return entry

    def status(self, tool_id: str) -> dict:
        definition = self._definition(tool_id)
        with self._lock:
            entry = self._owned_process(tool_id)
            effective_url = definition.url
            effective_health_url = definition.health_url
            if definition.id == 'cofi-voice':
                shared_url = _find_shared_cofivoice_url(definition.url)
                if shared_url:
                    effective_url = f'{shared_url}/'
                    effective_health_url = f'{shared_url}/api/health'
            web_alive = self._url_alive(effective_health_url) if definition.kind == 'web' else False
            process_alive = bool(entry and entry.process and entry.process.poll() is None)
            running = web_alive if definition.kind == 'web' else process_alive
            if running:
                state = 'running'
            elif definition.kind == 'web' and process_alive:
                state = 'starting'
            else:
                state = 'stopped'
            if entry and entry.process and entry.process.poll() is not None and not web_alive:
                state = 'exited'
            return {
                'id': definition.id,
                'name': definition.name,
                'stage': definition.stage,
                'kind': definition.kind,
                'description': definition.description,
                'available': self._command_available(definition),
                'running': running,
                'state': state,
                'url': effective_url,
                'health_url': effective_health_url,
                'pid': entry.process.pid if process_alive and entry and entry.process else None,
                'owned': bool(entry and entry.owned and process_alive),
                'started_at': entry.started_at if entry else None,
                'root': str(definition.root),
                'log_path': str(self.log_dir / f'{definition.id}.log') if definition.kind == 'web' else None,
            }

    def list_status(self) -> list[dict]:
        return [self.status(tool_id) for tool_id in self.definitions]

    @staticmethod
    def _creation_flags() -> int:
        if os.name != 'nt':
            return 0
        return int(getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)) | int(getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    @staticmethod
    def _detached_flags() -> int:
        if os.name != 'nt':
            return 0
        return (
            int(getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
            | int(getattr(subprocess, 'DETACHED_PROCESS', 0))
            | int(getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        )

    @staticmethod
    def _startupinfo():
        if os.name != 'nt':
            return None
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= int(getattr(subprocess, 'STARTF_USESHOWWINDOW', 1))
        startupinfo.wShowWindow = int(getattr(subprocess, 'SW_HIDE', 0))
        return startupinfo

    def _spawn_web(self, definition: ToolDefinition) -> ToolProcess:
        log_path = self.log_dir / f'{definition.id}.log'
        log_handle = open(log_path, 'a', encoding='utf-8', buffering=1)
        env = os.environ.copy()
        env.update(definition.env)
        process = subprocess.Popen(
            list(definition.command),
            cwd=definition.root,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=self._creation_flags(),
            startupinfo=self._startupinfo(),
        )
        return ToolProcess(process=process, log_handle=log_handle, started_at=time.time(), owned=True)

    def _spawn_native(self, definition: ToolDefinition) -> ToolProcess:
        env = os.environ.copy()
        env.update(definition.env)
        process = subprocess.Popen(
            list(definition.command),
            cwd=definition.root,
            env=env,
            creationflags=self._detached_flags(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=self._startupinfo(),
        )
        return ToolProcess(process=process, started_at=time.time(), owned=True)

    def _spawn_cli(self, definition: ToolDefinition, workspace: str | None) -> ToolProcess:
        resolved_workspace = Path(workspace).expanduser().resolve() if workspace else definition.root
        if not resolved_workspace.exists():
            resolved_workspace = definition.root
        show_console = os.environ.get('COFI_SHOW_CLI_WINDOWS', '').strip().lower() in {'1', 'true', 'yes', 'on'}
        if os.name == 'nt' and not show_console:
            log_path = self.log_dir / f'{definition.id}.log'
            log_handle = open(log_path, 'a', encoding='utf-8', buffering=1)
            env = os.environ.copy()
            env.update(definition.env)
            process = subprocess.Popen(
                list(definition.command),
                cwd=resolved_workspace,
                env=env,
                creationflags=self._creation_flags(),
                startupinfo=self._startupinfo(),
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )
            return ToolProcess(process=process, log_handle=log_handle, started_at=time.time(), owned=True)
        wt = _resolve_command('wt.exe') or _resolve_command('wt')
        command = list(definition.command)
        if wt:
            args = [wt, 'new-tab', '--title', definition.name, '-d', str(resolved_workspace), *command]
        else:
            cmd = _resolve_command('cmd.exe') or 'cmd.exe'
            args = [cmd, '/k', f'cd /d "{resolved_workspace}" && "{command[0]}"']
        process = subprocess.Popen(
            args,
            cwd=resolved_workspace,
            creationflags=self._detached_flags(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return ToolProcess(process=process, started_at=time.time(), owned=True)

    def start(self, tool_id: str, *, workspace: str | None = None) -> dict:
        definition = self._definition(tool_id)
        with self._lock:
            if not self._command_available(definition):
                status = self.status(tool_id)
                status['error'] = f'{definition.name} is not installed or its launcher cannot be found.'
                return status
            current = self.status(tool_id)
            if definition.kind == 'web' and (current['running'] or current['state'] == 'starting'):
                return current
            if definition.kind != 'web' and current['running']:
                return current

            if definition.kind == 'web':
                self._processes[tool_id] = self._spawn_web(definition)
            elif definition.kind == 'cli':
                self._processes[tool_id] = self._spawn_cli(definition, workspace)
            else:
                self._processes[tool_id] = self._spawn_native(definition)

            return self.status(tool_id)

    def stop(self, tool_id: str) -> dict:
        definition = self._definition(tool_id)
        with self._lock:
            entry = self._owned_process(tool_id)
            if entry and entry.process and entry.process.poll() is None and entry.owned:
                entry.process.terminate()
                try:
                    entry.process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    entry.process.kill()
                try:
                    if entry.log_handle:
                        entry.log_handle.close()
                except Exception:
                    pass
            return self.status(definition.id)

    def restart(self, tool_id: str, *, workspace: str | None = None) -> dict:
        self.stop(tool_id)
        return self.start(tool_id, workspace=workspace)

    def read_log(self, tool_id: str, *, lines: int = 120) -> dict:
        definition = self._definition(tool_id)
        path = self.log_dir / f'{definition.id}.log'
        if not path.is_file():
            return {'id': tool_id, 'path': str(path), 'lines': []}
        text = path.read_text(encoding='utf-8', errors='replace').splitlines()
        return {'id': tool_id, 'path': str(path), 'lines': text[-max(1, min(lines, 1000)):]}
