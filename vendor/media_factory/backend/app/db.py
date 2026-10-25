from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .schemas import JobStatus, SceneStatus


DEFAULT_SETTINGS: dict[str, Any] = {
    'default_model': 'Local Demo',
    'default_aspect_ratio': '16:9',
    'default_concurrency': 10,
    'queue_paused': False,
    'default_mode': 'hybrid',
    'output_directory': 'data/outputs',
    'image_output_directory': 'data/outputs/images',
    'video_output_directory': 'data/outputs/videos',
    'ref_image_dir': '',
    'ref_match_mode': 'exact',
    'worker_delay_seconds': 0,
    'worker_delay_min_seconds': 10,
    'worker_delay_max_seconds': 15,
    'images_per_prompt': 1,
    'videos_per_prompt': 1,
    'image_subdir_mode': False,
    'video_subdir_mode': True,
    'upscale_1k': True,
    'upscale_2k': False,
    'upscale_4k': False,
    'video_resolution': '720p',
    'video_pair_mode': 'PAIR_MODE_START_END',
    'auto_disable_on_quota': True,
    'remove_watermark': True,
    'auto_retry_enabled': True,
    'max_retry_attempts': 2,
    'retry_delay_seconds': 2.0,
    'autosave': True,
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA journal_mode = WAL')
        connection.execute('PRAGMA busy_timeout = 30000')
        connection.execute('PRAGMA foreign_keys = ON')
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                '''
                CREATE TABLE IF NOT EXISTS scenes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    negative_prompt TEXT,
                    reference_image TEXT,
                    model TEXT NOT NULL,
                    aspect_ratio TEXT NOT NULL,
                    duration_seconds INTEGER,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    output_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    scene_id TEXT NOT NULL,
                    batch_token TEXT,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    worker_id TEXT,
                    error TEXT,
                    output_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_scene_id ON jobs(scene_id);
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workflow_runs (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_workflow_runs_workflow_id ON workflow_runs(workflow_id);

                CREATE TABLE IF NOT EXISTS editor_items (
                    id TEXT PRIMARY KEY,
                    scene_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    duration_seconds INTEGER,
                    order_index INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_editor_items_order ON editor_items(order_index, created_at, id);

                CREATE TABLE IF NOT EXISTS local_resources (
                    resource_type TEXT NOT NULL,
                    id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(resource_type, id)
                );

                CREATE INDEX IF NOT EXISTS idx_local_resources_type_created
                    ON local_resources(resource_type, created_at, id);
                '''
            )
            scene_columns = {row['name'] for row in connection.execute('PRAGMA table_info(scenes)').fetchall()}
            if 'reference_images' not in scene_columns:
                connection.execute("ALTER TABLE scenes ADD COLUMN reference_images TEXT NOT NULL DEFAULT '[]'")
                connection.execute(
                    "UPDATE scenes SET reference_images = json_array(reference_image) WHERE reference_image IS NOT NULL AND reference_image != ''"
                )
            job_columns = {row['name'] for row in connection.execute('PRAGMA table_info(jobs)').fetchall()}
            if 'batch_token' not in job_columns:
                connection.execute('ALTER TABLE jobs ADD COLUMN batch_token TEXT')
            now = utc_now()
            connection.execute(
                '''
                INSERT OR IGNORE INTO local_resources (resource_type, id, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    'settings',
                    'default',
                    json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, separators=(',', ':')),
                    now,
                    now,
                ),
            )

    @staticmethod
    def _normalize_scene_references(values: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(values)
        has_list = 'reference_images' in normalized
        has_legacy = 'reference_image' in normalized
        if has_list:
            references = normalized.get('reference_images') or []
            normalized['reference_images'] = json.dumps(list(references), ensure_ascii=False, separators=(',', ':'))
            normalized['reference_image'] = references[0] if references else None
        elif has_legacy:
            legacy = normalized.get('reference_image')
            normalized['reference_images'] = json.dumps([legacy] if legacy else [], ensure_ascii=False, separators=(',', ':'))
        return normalized

    @staticmethod
    def _decode_scene(row: dict[str, Any]) -> dict[str, Any]:
        decoded = dict(row)
        raw = decoded.get('reference_images')
        try:
            references = json.loads(raw) if isinstance(raw, str) else list(raw or [])
        except (TypeError, ValueError, json.JSONDecodeError):
            references = []
        if not references and decoded.get('reference_image'):
            references = [decoded['reference_image']]
        decoded['reference_images'] = references
        decoded['reference_image'] = references[0] if references else None
        return decoded

    def create_scene(self, values: dict[str, Any]) -> dict[str, Any]:
        scene_id = uuid4().hex
        now = utc_now()
        row = self._normalize_scene_references({
            'id': scene_id,
            **values,
            'status': SceneStatus.IDLE.value,
            'progress': 0,
            'output_path': None,
            'created_at': now,
            'updated_at': now,
        })
        with self._connect() as connection:
            connection.execute(
                '''
                INSERT INTO scenes (
                    id, name, task_type, prompt, negative_prompt, reference_image, reference_images,
                    model, aspect_ratio, duration_seconds, status, progress,
                    output_path, created_at, updated_at
                ) VALUES (
                    :id, :name, :task_type, :prompt, :negative_prompt, :reference_image, :reference_images,
                    :model, :aspect_ratio, :duration_seconds, :status, :progress,
                    :output_path, :created_at, :updated_at
                )
                ''',
                row,
            )
        return self._decode_scene(row)

    def list_scenes(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute('SELECT * FROM scenes ORDER BY created_at, id').fetchall()
        return [self._decode_scene(dict(row)) for row in rows]

    def get_scene(self, scene_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute('SELECT * FROM scenes WHERE id = ?', (scene_id,)).fetchone()
        return self._decode_scene(dict(row)) if row else None

    def get_scene_sequence_index(self, scene_id: str) -> int:
        for index, scene in enumerate(self.list_scenes(), start=1):
            if scene['id'] == scene_id:
                return index
        raise KeyError(f'Unknown scene: {scene_id}')

    def get_job_batch_sequence_index(self, job_id: str) -> int:
        """Return the stable 1-based prompt order inside a generation batch."""
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f'Unknown job: {job_id}')
        batch_token = job.get('batch_token')
        if not batch_token:
            return 1
        seen: set[str] = set()
        ordered_scene_ids: list[str] = []
        with self._connect() as connection:
            rows = connection.execute(
                'SELECT scene_id FROM jobs WHERE batch_token = ? ORDER BY rowid ASC',
                (batch_token,),
            ).fetchall()
        for candidate in rows:
            scene_id = candidate['scene_id']
            if scene_id in seen:
                continue
            seen.add(scene_id)
            ordered_scene_ids.append(scene_id)
        try:
            return ordered_scene_ids.index(job['scene_id']) + 1
        except ValueError as exc:
            raise KeyError(f'Job scene is missing from batch: {job_id}') from exc

    def get_job_batch_scene_count(self, job_id: str) -> int:
        """Return the number of distinct scenes submitted in this job's batch."""
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f'Unknown job: {job_id}')
        batch_token = job.get('batch_token')
        if not batch_token:
            return 1
        with self._connect() as connection:
            row = connection.execute(
                'SELECT COUNT(DISTINCT scene_id) AS scene_count FROM jobs WHERE batch_token = ?',
                (batch_token,),
            ).fetchone()
        return max(1, int(row['scene_count']))

    def update_scene(self, scene_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        if not values:
            return self.get_scene(scene_id)
        values = self._normalize_scene_references({**values, 'updated_at': utc_now()})
        assignments = ', '.join(f'{key} = ?' for key in values)
        parameters = [*values.values(), scene_id]
        with self._connect() as connection:
            cursor = connection.execute(f'UPDATE scenes SET {assignments} WHERE id = ?', parameters)
            if cursor.rowcount == 0:
                return None
        return self.get_scene(scene_id)

    def delete_scene(self, scene_id: str) -> bool:
        with self._connect() as connection:
            connection.execute('DELETE FROM jobs WHERE scene_id = ?', (scene_id,))
            connection.execute('DELETE FROM editor_items WHERE scene_id = ?', (scene_id,))
            cursor = connection.execute('DELETE FROM scenes WHERE id = ?', (scene_id,))
            return cursor.rowcount > 0

    def delete_all_scenes_if_idle(self) -> int | None:
        """Delete every scene atomically, or return None when any job is active."""
        with self._connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            active = connection.execute(
                'SELECT 1 FROM jobs WHERE status IN (?, ?) LIMIT 1',
                (JobStatus.QUEUED.value, JobStatus.RUNNING.value),
            ).fetchone()
            if active is not None:
                connection.rollback()
                return None
            count_row = connection.execute('SELECT COUNT(*) AS scene_count FROM scenes').fetchone()
            deleted_count = int(count_row['scene_count'])
            connection.execute('DELETE FROM jobs')
            connection.execute('DELETE FROM editor_items')
            connection.execute('DELETE FROM scenes')
            connection.commit()
            return deleted_count

    def delete_all_scenes(self) -> int:
        """Delete every scene and its jobs after the queue has been stopped."""
        with self._connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            count_row = connection.execute('SELECT COUNT(*) AS scene_count FROM scenes').fetchone()
            deleted_count = int(count_row['scene_count'])
            connection.execute('DELETE FROM jobs')
            connection.execute('DELETE FROM editor_items')
            connection.execute('DELETE FROM scenes')
            connection.commit()
            return deleted_count

    def set_scene_runtime(
        self,
        scene_id: str,
        *,
        status: str,
        progress: int,
        output_path: str | None = None,
    ) -> dict[str, Any] | None:
        values: dict[str, Any] = {'status': status, 'progress': progress}
        if output_path is not None:
            values['output_path'] = output_path
        elif status == JobStatus.QUEUED.value:
            values['output_path'] = None
        return self.update_scene(scene_id, values)

    def create_job(self, scene_id: str, *, batch_token: str | None = None) -> dict[str, Any]:
        job_id = uuid4().hex
        now = utc_now()
        row = {
            'id': job_id,
            'scene_id': scene_id,
            'batch_token': batch_token,
            'status': JobStatus.QUEUED.value,
            'progress': 0,
            'worker_id': None,
            'error': None,
            'output_path': None,
            'created_at': now,
            'updated_at': now,
        }
        with self._connect() as connection:
            connection.execute(
                '''
                INSERT INTO jobs (
                    id, scene_id, batch_token, status, progress, worker_id, error,
                    output_path, created_at, updated_at
                ) VALUES (
                    :id, :scene_id, :batch_token, :status, :progress, :worker_id, :error,
                    :output_path, :created_at, :updated_at
                )
                ''',
                row,
            )
        return row

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
        return dict(row) if row else None

    def get_job_attempt_index(self, job_id: str) -> int:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f'Unknown job: {job_id}')
        with self._connect() as connection:
            if job.get('batch_token'):
                row = connection.execute(
                    '''
                    SELECT COUNT(*) AS attempt_index
                    FROM jobs
                    WHERE scene_id = ? AND batch_token = ?
                      AND (
                        created_at < ?
                        OR (created_at = ? AND id <= ?)
                      )
                    ''',
                    (job['scene_id'], job['batch_token'], job['created_at'], job['created_at'], job['id']),
                ).fetchone()
            else:
                row = connection.execute(
                    '''
                    SELECT COUNT(*) AS attempt_index
                    FROM jobs
                    WHERE scene_id = ? AND batch_token IS NULL
                      AND (
                        created_at < ?
                        OR (created_at = ? AND id <= ?)
                      )
                    ''',
                    (job['scene_id'], job['created_at'], job['created_at'], job['id']),
                ).fetchone()
        return max(1, int(row['attempt_index']))

    def get_job_run_index(self, job_id: str) -> int:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f'Unknown job: {job_id}')
        with self._connect() as connection:
            row = connection.execute(
                '''
                SELECT COUNT(DISTINCT COALESCE(batch_token, id)) AS run_index
                FROM jobs
                WHERE scene_id = ?
                  AND (
                    created_at < ?
                    OR (created_at = ? AND id <= ?)
                  )
                ''',
                (job['scene_id'], job['created_at'], job['created_at'], job['id']),
            ).fetchone()
        return max(1, int(row['run_index']))

    def list_jobs(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection:
            if status is None:
                rows = connection.execute('SELECT * FROM jobs ORDER BY created_at DESC, id DESC LIMIT 2000').fetchall()
            else:
                rows = connection.execute(
                    'SELECT * FROM jobs WHERE status = ? ORDER BY created_at, id',
                    (status,),
                ).fetchall()
        return [dict(row) for row in rows]

    def get_active_job_for_scene(self, scene_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                '''
                SELECT * FROM jobs
                WHERE scene_id = ? AND status IN (?, ?)
                ORDER BY created_at DESC
                LIMIT 1
                ''',
                (scene_id, JobStatus.QUEUED.value, JobStatus.RUNNING.value),
            ).fetchone()
        return dict(row) if row else None

    def update_job(self, job_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        if not values:
            return self.get_job(job_id)
        values = {**values, 'updated_at': utc_now()}
        assignments = ', '.join(f'{key} = ?' for key in values)
        parameters = [*values.values(), job_id]
        with self._connect() as connection:
            cursor = connection.execute(f'UPDATE jobs SET {assignments} WHERE id = ?', parameters)
            if cursor.rowcount == 0:
                return None
        return self.get_job(job_id)

    def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute('SELECT payload FROM workflows WHERE id = ?', (workflow_id,)).fetchone()
        return json.loads(row['payload']) if row else None

    def save_workflow(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        serialized = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
        with self._connect() as connection:
            connection.execute(
                '''
                INSERT INTO workflows (id, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
                ''',
                (workflow_id, serialized, now, now),
            )
        return payload

    def save_workflow_run(self, run_id: str, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                'INSERT INTO workflow_runs (id, workflow_id, payload, created_at) VALUES (?, ?, ?, ?)',
                (run_id, workflow_id, json.dumps(payload, ensure_ascii=False, separators=(',', ':')), utc_now()),
            )
        return payload

    def list_workflow_runs(self, workflow_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                'SELECT payload FROM workflow_runs WHERE workflow_id = ? ORDER BY created_at DESC',
                (workflow_id,),
            ).fetchall()
        return [json.loads(row['payload']) for row in rows]

    def create_editor_item(self, scene: dict[str, Any]) -> dict[str, Any]:
        item_id = uuid4().hex
        now = utc_now()
        media_type = 'video' if scene['task_type'] == 'image_to_video' else 'image'
        with self._connect() as connection:
            order_index = connection.execute(
                'SELECT COALESCE(MAX(order_index), -1) + 1 AS next_index FROM editor_items'
            ).fetchone()['next_index']
            row = {
                'id': item_id,
                'scene_id': scene['id'],
                'name': scene['name'],
                'source_path': scene['output_path'],
                'media_type': media_type,
                'duration_seconds': scene.get('duration_seconds'),
                'order_index': order_index,
                'created_at': now,
            }
            connection.execute(
                '''
                INSERT INTO editor_items (
                    id, scene_id, name, source_path, media_type,
                    duration_seconds, order_index, created_at
                ) VALUES (
                    :id, :scene_id, :name, :source_path, :media_type,
                    :duration_seconds, :order_index, :created_at
                )
                ''',
                row,
            )
        return row

    def list_editor_items(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                'SELECT * FROM editor_items ORDER BY order_index, created_at, id'
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_editor_item(self, item_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute('DELETE FROM editor_items WHERE id = ?', (item_id,))
        return cursor.rowcount > 0

    @staticmethod
    def _resource_from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            'id': row['id'],
            **json.loads(row['payload']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
        }

    def list_resources(self, resource_type: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                '''
                SELECT id, payload, created_at, updated_at
                FROM local_resources
                WHERE resource_type = ?
                ORDER BY created_at, id
                ''',
                (resource_type,),
            ).fetchall()
        return [self._resource_from_row(row) for row in rows]

    def get_resource(self, resource_type: str, resource_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                '''
                SELECT id, payload, created_at, updated_at
                FROM local_resources
                WHERE resource_type = ? AND id = ?
                ''',
                (resource_type, resource_id),
            ).fetchone()
        return self._resource_from_row(row) if row else None

    def create_resource(
        self,
        resource_type: str,
        values: dict[str, Any],
        *,
        resource_id: str | None = None,
        replace: bool = False,
    ) -> dict[str, Any]:
        identifier = resource_id or uuid4().hex
        now = utc_now()
        serialized = json.dumps(values, ensure_ascii=False, separators=(',', ':'))
        with self._connect() as connection:
            if replace:
                existing = connection.execute(
                    'SELECT created_at FROM local_resources WHERE resource_type = ? AND id = ?',
                    (resource_type, identifier),
                ).fetchone()
                created_at = existing['created_at'] if existing else now
                connection.execute(
                    '''
                    INSERT INTO local_resources (resource_type, id, payload, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(resource_type, id) DO UPDATE SET
                        payload = excluded.payload,
                        updated_at = excluded.updated_at
                    ''',
                    (resource_type, identifier, serialized, created_at, now),
                )
            else:
                connection.execute(
                    '''
                    INSERT INTO local_resources (resource_type, id, payload, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (resource_type, identifier, serialized, now, now),
                )
        created = self.get_resource(resource_type, identifier)
        assert created is not None
        return created

    def patch_resource(
        self,
        resource_type: str,
        resource_id: str,
        values: dict[str, Any],
    ) -> dict[str, Any] | None:
        current = self.get_resource(resource_type, resource_id)
        if current is None:
            return None
        payload = {
            key: value
            for key, value in current.items()
            if key not in {'id', 'created_at', 'updated_at'}
        }
        payload.update(values)
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                '''
                UPDATE local_resources
                SET payload = ?, updated_at = ?
                WHERE resource_type = ? AND id = ?
                ''',
                (
                    json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
                    now,
                    resource_type,
                    resource_id,
                ),
            )
        return self.get_resource(resource_type, resource_id)

    def delete_resource(self, resource_type: str, resource_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                'DELETE FROM local_resources WHERE resource_type = ? AND id = ?',
                (resource_type, resource_id),
            )
        return cursor.rowcount > 0

    def get_settings(self) -> dict[str, Any]:
        stored = self.get_resource('settings', 'default')
        if stored is None:
            return {'id': 'default', **DEFAULT_SETTINGS}
        settings = {'id': 'default', **DEFAULT_SETTINGS, **stored}
        if 'worker_delay_min_seconds' not in stored and 'worker_delay_max_seconds' not in stored and 'worker_delay_seconds' in stored:
            legacy_delay = max(0.0, float(stored.get('worker_delay_seconds') or 0))
            settings['worker_delay_min_seconds'] = legacy_delay
            settings['worker_delay_max_seconds'] = legacy_delay
        mode = str(settings.get('default_mode') or '').strip().lower()
        settings['default_mode'] = mode if mode in {'manual', 'hybrid', 'codex'} else DEFAULT_SETTINGS['default_mode']
        settings['upscale_1k'] = True
        settings['upscale_2k'] = False
        settings['upscale_4k'] = False
        settings['video_resolution'] = '720p'
        return settings
