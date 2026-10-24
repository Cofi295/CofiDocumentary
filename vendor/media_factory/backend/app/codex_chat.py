from __future__ import annotations

import json
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .agent_jobs import ACTIVE_STATUSES, AgentJobSupervisor


class CodexChatService:
    """Small persistent chat facade on top of the existing Codex job supervisor."""

    def __init__(
        self,
        project_root: Path,
        supervisor: AgentJobSupervisor,
        *,
        data_dir: Path | None = None,
        timeout_seconds: float = 1800,
    ) -> None:
        self.project_root = project_root.resolve()
        self.supervisor = supervisor
        self.data_dir = (data_dir or self.project_root / 'data' / 'codex-chat').resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_dir = self.data_dir / 'attachments'
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds
        self._lock = threading.RLock()

    _ATTACHMENT_ID_RE = re.compile(r'^[a-f0-9]{32}$')
    _IMAGE_TYPES = {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/webp': '.webp',
        'image/gif': '.gif',
    }
    _MAX_IMAGE_BYTES = 12 * 1024 * 1024
    _MAX_ATTACHMENTS_PER_TURN = 8

    @property
    def state_path(self) -> Path:
        return self.data_dir / 'state.json'

    @property
    def history_path(self) -> Path:
        return self.data_dir / 'history.jsonl'

    def _load_state(self) -> dict[str, Any]:
        try:
            value = json.loads(self.state_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def _save_state(self, payload: dict[str, Any]) -> None:
        temp = self.state_path.with_suffix('.tmp')
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self.state_path)

    def _append_history(self, role: str, content: str, *, attachments: list[dict[str, Any]] | None = None) -> None:
        entry = {'role': role, 'content': content, 'created_at': time.time()}
        if attachments:
            entry['attachments'] = attachments
        with self.history_path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def save_attachment(self, *, filename: str, content_type: str, payload: bytes) -> dict[str, Any]:
        media_type = str(content_type or '').split(';', 1)[0].strip().lower()
        suffix = self._IMAGE_TYPES.get(media_type)
        if suffix is None:
            raise ValueError('only PNG, JPEG, WebP, and GIF images are supported')
        if not payload:
            raise ValueError('image attachment is empty')
        if len(payload) > self._MAX_IMAGE_BYTES:
            raise ValueError('image attachment is larger than 12 MB')

        attachment_id = uuid.uuid4().hex
        safe_name = Path(str(filename or f'image{suffix}')).name[:180] or f'image{suffix}'
        image_path = self.attachments_dir / f'{attachment_id}{suffix}'
        metadata_path = self.attachments_dir / f'{attachment_id}.json'
        image_path.write_bytes(payload)
        metadata = {
            'id': attachment_id,
            'name': safe_name,
            'content_type': media_type,
            'size': len(payload),
            'url': f'/api/codex-chat/attachments/{attachment_id}',
            'path': str(image_path),
        }
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
        return {key: value for key, value in metadata.items() if key != 'path'}

    def _attachment_record(self, attachment_id: str) -> dict[str, Any]:
        normalized = str(attachment_id or '').strip().lower()
        if not self._ATTACHMENT_ID_RE.fullmatch(normalized):
            raise ValueError('invalid image attachment id')
        metadata_path = self.attachments_dir / f'{normalized}.json'
        try:
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError('image attachment was not found') from exc
        if not isinstance(metadata, dict):
            raise ValueError('image attachment metadata is invalid')
        image_path = Path(str(metadata.get('path') or '')).resolve()
        if image_path.parent != self.attachments_dir.resolve() or not image_path.is_file():
            raise ValueError('image attachment file was not found')
        return metadata

    def attachment_path(self, attachment_id: str) -> Path:
        return Path(str(self._attachment_record(attachment_id)['path']))

    def _resolve_attachments(self, attachment_ids: list[str] | None) -> tuple[list[dict[str, Any]], list[str]]:
        ids = list(attachment_ids or [])
        if len(ids) > self._MAX_ATTACHMENTS_PER_TURN:
            raise ValueError(f'a maximum of {self._MAX_ATTACHMENTS_PER_TURN} images can be attached per message')
        metadata: list[dict[str, Any]] = []
        paths: list[str] = []
        for attachment_id in ids:
            record = self._attachment_record(attachment_id)
            metadata.append({key: value for key, value in record.items() if key != 'path'})
            paths.append(str(record['path']))
        return metadata, paths

    def history(self, *, limit: int = 100) -> list[dict[str, Any]]:
        self._sync_pending_reply()
        return self._read_history(limit=limit)

    def _read_history(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if not self.history_path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.history_path.read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get('role') in {'user', 'assistant'}:
                rows.append(item)
        return rows[-max(1, min(limit, 300)):]

    def status(self) -> dict[str, Any]:
        self._sync_pending_reply()
        return self._status_without_sync()

    def _status_without_sync(self) -> dict[str, Any]:
        state = self._load_state()
        job_id = str(state.get('job_id') or '').strip() or None
        job = None
        if job_id:
            try:
                job = self.supervisor.get_job(job_id)
            except KeyError:
                job_id = None
        return {
            'available': bool(self.supervisor.engine_status()['codex']['available']),
            'job_id': job_id,
            'session_id': job.get('session_id') if job else None,
            'status': job.get('status') if job else 'idle',
            'busy': bool(job and job.get('status') in ACTIVE_STATUSES),
        }

    def _sync_pending_reply(self) -> None:
        with self._lock:
            state = self._load_state()
            job_id = str(state.get('job_id') or '').strip()
            if not job_id:
                return
            history = self._read_history(limit=2)
            legacy_missing_reply = bool(history and history[-1].get('role') == 'user')
            if not state.get('pending_reply') and not legacy_missing_reply:
                return
            try:
                job = self.supervisor.get_job(job_id)
            except KeyError:
                return
            if job.get('status') != 'completed':
                return
            log = self.supervisor.read_log(job_id, lines=40)
            reply = str(log.get('last_message') or '').strip() or 'Codex đã hoàn tất nhưng không trả về nội dung.'
            self._append_history('assistant', reply)
            state['pending_reply'] = False
            state['completed_at'] = time.time()
            self._save_state(state)

    @staticmethod
    def _project_output_stage(app_path: str | None) -> str | None:
        path = '/' + str(app_path or '').strip().strip('/').lower()
        if path in {'/radar', '/research'}:
            return 'research'
        stage = path.lstrip('/')
        if stage in {'script', 'voice', 'scenes', 'visuals', 'footage', 'editor', 'qc', 'export'}:
            return stage
        return None

    def _load_session_permissions(self) -> dict[str, Any]:
        candidates = [
            self.project_root / 'COFI_BRAIN' / 'knowledge' / 'codex_session_permissions.json',
            self.project_root / 'codex_session_permissions.json',
        ]
        for path in candidates:
            try:
                value = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(value, dict):
                return value
        return {}

    def _context_prompt(self, message: str, *, app_path: str | None, selected_project_id: str | None, mode: str | None, attachment_count: int = 0) -> str:
        context = {
            'app_path': app_path or '/dashboard',
            'selected_project_id': selected_project_id,
            'mode': mode or 'hybrid',
        }
        if selected_project_id and self.supervisor.manifest_store:
            try:
                manifest = self.supervisor.manifest_store.ensure(selected_project_id)
                context['project_manifest_path'] = manifest.get('manifest_path')
                context['production_settings'] = manifest.get('production_settings')
            except KeyError:
                pass
        permissions = self._load_session_permissions()
        context['codex_permissions'] = permissions
        return (
            'You are the embedded Codex assistant inside Cofi Studio. '
            'The CofiStudio project root is your working directory. '
            'Use the repository and local tools when the user asks you to inspect, fix, or change the app. '
            'Cofi Studio is also an execution workspace for producing videos. '
            'When the user asks for a production outcome (for example: research a channel, choose today\'s topic, optimize it, and make/export the video), '
            'do not stop after recommendations once you have enough evidence. Use the selected project, Project Manifest, CofiStudio APIs, and local production tools '
            'to execute the downstream stages that are already automatable: research -> script -> voice -> scenes -> visuals -> footage -> editor -> qc -> export. '
            'Save useful outputs in the project workspace and advance/publish project stages as work completes. '
            'Before producing a stage, read production_settings from the selected Project Manifest and treat them as hard constraints. '
            'Script length uses exactly one active criterion from production_settings.script.length_mode. '
            'If it is characters, keep the finished script inside character_min..character_max and ignore duration_minutes as a target. '
            'If it is duration, target duration_minutes and do not force a character count. '
            'When visual_clean_output is enabled, also produce a clean visual-text artifact from the script: no numbering, timestamps, scene labels or commentary; one independently illustratable visual unit per line. '
            'For visual_break_mode=sentence_and_visual_clause, always break at sentence-ending punctuation and also break at a comma only when the clauses on both sides can be illustrated as meaningfully different images. '
            'Scene mapping timing must follow the actual voice/SRT plus those visual units; do not invent or enforce a fixed seconds-per-scene target. '
            'Use scenes.visual_style, custom_style, visual_instructions, character_reference, split_mode and visual_lines_per_prompt as the visual prompt constraints. '
            'If automation.mode is controlled, honor pause_after_script and pause_after_scenes instead of silently running past those review gates. '
            'Only stop when a genuinely required user decision or an unavailable external capability blocks execution; otherwise keep executing. '
            'Respond to the user in Vietnamese by default and keep the final reply concise. '
            'Current Cofi Studio UI context:\n'
            f'{json.dumps(context, ensure_ascii=False)}\n\n'
            f'Attached images: {attachment_count}\n\n'
            f'User request:\n{message.strip() or "Please inspect the attached image(s) and respond to what they show."}'
        )

    def _wait_for_turn(self, job_id: str) -> dict[str, Any]:
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            job = self.supervisor.get_job(job_id)
            if job.get('status') not in ACTIVE_STATUSES:
                return job
            time.sleep(0.2)
        self.supervisor.pause(job_id)
        raise RuntimeError('Codex chat timed out before the turn completed')

    def send(
        self,
        message: str,
        *,
        app_path: str | None = None,
        selected_project_id: str | None = None,
        mode: str | None = None,
        attachment_ids: list[str] | None = None,
        wait: bool = True,
    ) -> dict[str, Any]:
        text = str(message or '').strip()
        attachment_metadata, image_paths = self._resolve_attachments(attachment_ids)
        if not text and not image_paths:
            raise ValueError('message or image attachment is required')
        if not self.supervisor.engine_status()['codex']['available']:
            raise RuntimeError('Codex CLI is not installed')

        prompt = self._context_prompt(
            text,
            app_path=app_path,
            selected_project_id=selected_project_id,
            mode=mode,
            attachment_count=len(image_paths),
        )
        output_stage = self._project_output_stage(app_path)
        with self._lock:
            state = self._load_state()
            job_id = str(state.get('job_id') or '').strip()
            job: dict[str, Any] | None = None
            if job_id:
                try:
                    job = self.supervisor.get_job(job_id)
                except KeyError:
                    job_id = ''

            if job and job.get('status') in ACTIVE_STATUSES:
                raise RuntimeError('Codex is still processing the previous chat message')

            self._append_history('user', text, attachments=attachment_metadata)
            if job and job.get('session_id') and job.get('status') in {'completed', 'paused', 'interrupted', 'failed'}:
                job = self.supervisor.resume(
                    job_id,
                    prompt=prompt,
                    image_paths=image_paths,
                    project_id=selected_project_id,
                    output_key=output_stage,
                )
            else:
                job = self.supervisor.create_job(
                    name='Cofi Studio Codex Chat',
                    engine='codex',
                    stage='codex-chat',
                    workspace=str(self.project_root),
                    prompt=prompt,
                    project_id=selected_project_id,
                    output_key=output_stage or 'codex-chat',
                    image_paths=image_paths,
                )
                job_id = job['id']
            previous_state = self._load_state()
            self._save_state({
                'job_id': job_id,
                'created_at': previous_state.get('created_at') or time.time(),
                'pending_reply': True,
                'selected_project_id': selected_project_id,
                'output_stage': output_stage,
            })

            if not wait:
                return {
                    'reply': '',
                    'history': self._read_history(limit=100),
                    'status': self._status_without_sync(),
                }

            finished = self._wait_for_turn(job_id)
            if finished.get('status') != 'completed':
                raise RuntimeError(f"Codex chat ended with status {finished.get('status') or 'unknown'}")
            log = self.supervisor.read_log(job_id, lines=40)
            reply = str(log.get('last_message') or '').strip() or 'Codex đã hoàn tất nhưng không trả về nội dung.'
            self._append_history('assistant', reply)
            state = self._load_state()
            state['pending_reply'] = False
            state['completed_at'] = time.time()
            self._save_state(state)
            return {
                'reply': reply,
                'history': self._read_history(limit=100),
                'status': self._status_without_sync(),
            }

    def reset(self) -> dict[str, Any]:
        with self._lock:
            state = self._load_state()
            job_id = str(state.get('job_id') or '').strip()
            if job_id:
                try:
                    job = self.supervisor.get_job(job_id)
                    if job.get('status') in ACTIVE_STATUSES:
                        self.supervisor.cancel(job_id)
                except KeyError:
                    pass
            if self.state_path.exists():
                self.state_path.unlink()
            if self.history_path.exists():
                retired = self.data_dir / f'history-{int(time.time())}.jsonl'
                self.history_path.replace(retired)
            return self.status()
