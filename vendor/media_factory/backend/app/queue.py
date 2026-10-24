from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .db import Database
from .providers.base import MediaProvider, ProviderAuthError, ProviderQuotaError, is_retryable_provider_error, prompt_slug
from .schemas import JobStatus, SceneStatus, WorkerState


class QueueSupervisor:
    def __init__(
        self,
        db: Database,
        provider: MediaProvider,
        *,
        concurrency: int = 10,
        worker_delay_seconds: float = 0,
        worker_delay_min_seconds: float | None = None,
        worker_delay_max_seconds: float | None = None,
        jitter_source: Callable[[float, float], float] | None = None,
        quota_cooldown_seconds: float = 2.0,
    ):
        self.db = db
        self.provider = provider
        self._concurrency = concurrency
        self._worker_delay_seconds = max(0.0, worker_delay_seconds)
        legacy_delay = self._worker_delay_seconds
        minimum = legacy_delay if worker_delay_min_seconds is None else max(0.0, float(worker_delay_min_seconds))
        maximum = minimum if worker_delay_max_seconds is None else max(0.0, float(worker_delay_max_seconds))
        self._worker_delay_min_seconds = minimum
        self._worker_delay_max_seconds = max(minimum, maximum)
        self._jitter_source = jitter_source or random.uniform
        self._quota_cooldown_seconds = max(0.0, quota_cooldown_seconds)
        self._running_count = 0
        self._paused = False
        self._gate = asyncio.Condition()
        self._dequeue_gate = asyncio.Lock()
        self._dispatch_gates: dict[str, asyncio.Lock] = {}
        self._last_dispatch_at: dict[str, float] = {}
        self._job_queue: asyncio.Queue[str] = asyncio.Queue()
        self._tasks: list[asyncio.Task[None]] = []
        self._retry_tasks: set[asyncio.Task[None]] = set()
        self._started = False
        self.workers: list[dict[str, Any]] = [
            {
                'id': f'worker-{index:02d}',
                'name': f'Worker {index:02d}',
                'state': WorkerState.READY.value,
                'progress': 0,
                'job_id': None,
            }
            for index in range(1, 11)
        ]

    @property
    def concurrency(self) -> int:
        return self._concurrency

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def worker_delay_seconds(self) -> float:
        return self._worker_delay_seconds

    @property
    def worker_delay_min_seconds(self) -> float:
        return self._worker_delay_min_seconds

    @property
    def worker_delay_max_seconds(self) -> float:
        return self._worker_delay_max_seconds

    async def start(self) -> None:
        if self._started:
            return
        self._recover_stale_running_jobs()
        queued_jobs = self.db.list_jobs(JobStatus.QUEUED.value)
        persisted_pause = bool(self.db.get_settings().get('queue_paused', False))
        policy_blocked = any(self._is_policy_block_error(job.get('error')) for job in queued_jobs)
        self._paused = persisted_pause or policy_blocked
        if policy_blocked and not persisted_pause:
            self._persist_pause_state(True)
        self._started = True
        for worker in self.workers:
            self._tasks.append(asyncio.create_task(self._worker_loop(worker)))
        for job in queued_jobs:
            await self._job_queue.put(job['id'])

    def _recover_stale_running_jobs(self) -> None:
        for job in self.db.list_jobs(JobStatus.RUNNING.value):
            self.db.update_job(
                job['id'],
                {
                    'status': JobStatus.FAILED.value,
                    'progress': 0,
                    'worker_id': None,
                    'error': 'Interrupted by application restart',
                },
            )
            scene = self.db.get_scene(job['scene_id'])
            if scene is not None and scene['status'] == SceneStatus.RUNNING.value:
                self.db.set_scene_runtime(scene['id'], status=SceneStatus.FAILED.value, progress=0)

    async def stop(self) -> None:
        self._started = False
        retry_tasks = list(self._retry_tasks)
        for task in retry_tasks:
            task.cancel()
        for task in retry_tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._retry_tasks.clear()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()

    async def clear_all_scenes(self) -> int:
        """Cancel queued/running work, clear all scenes/jobs, then restart workers."""
        was_paused = self._paused
        await self.stop()
        deleted_count = self.db.delete_all_scenes()
        self._job_queue = asyncio.Queue()
        self._running_count = 0
        self._dequeue_gate = asyncio.Lock()
        self._dispatch_gates = {}
        self._last_dispatch_at = {}
        for worker in self.workers:
            worker.update(state=WorkerState.READY.value, progress=0, job_id=None)
        self._paused = was_paused
        await self.start()
        return deleted_count

    async def set_concurrency(self, value: int) -> int:
        if not 1 <= value <= 10:
            raise ValueError('concurrency must be between 1 and 10')
        async with self._gate:
            self._concurrency = value
            self._gate.notify_all()
        return self._concurrency

    def set_worker_delay(self, value: float) -> float:
        self._worker_delay_seconds = max(0.0, float(value))
        self._worker_delay_min_seconds = self._worker_delay_seconds
        self._worker_delay_max_seconds = self._worker_delay_seconds
        return self._worker_delay_seconds

    def set_worker_delay_range(self, minimum: float, maximum: float) -> tuple[float, float]:
        normalized_minimum = max(0.0, float(minimum))
        normalized_maximum = max(normalized_minimum, float(maximum))
        self._worker_delay_min_seconds = normalized_minimum
        self._worker_delay_max_seconds = normalized_maximum
        return self._worker_delay_min_seconds, self._worker_delay_max_seconds

    def _dispatch_pacing_key(self, scene: dict[str, Any], provider_slot: Any) -> str:
        resolver = getattr(self.provider, 'dispatch_pacing_key', None)
        if callable(resolver):
            value = resolver(scene, provider_slot)
            if value is not None:
                return str(value)
        return '__global__'

    async def _wait_for_dispatch_delay(self, pacing_key: str = '__global__') -> None:
        gate = self._dispatch_gates.setdefault(pacing_key, asyncio.Lock())
        async with gate:
            loop = asyncio.get_running_loop()
            now = loop.time()
            last_dispatch_at = self._last_dispatch_at.get(pacing_key, 0.0)
            if last_dispatch_at > 0:
                dispatch_delay = self._jitter_source(
                    self._worker_delay_min_seconds,
                    self._worker_delay_max_seconds,
                )
                remaining = last_dispatch_at + max(0.0, dispatch_delay) - now
                if remaining > 0:
                    await asyncio.sleep(remaining)
            self._last_dispatch_at[pacing_key] = loop.time()

    def _requires_dispatch_pacing(self, scene: dict[str, Any]) -> bool:
        checker = getattr(self.provider, 'requires_dispatch_pacing', None)
        if callable(checker):
            return bool(checker(scene))
        return True

    async def pause(self) -> None:
        async with self._gate:
            self._paused = True
        self._persist_pause_state(True)

    async def resume(self) -> None:
        self._persist_pause_state(False)
        async with self._gate:
            self._paused = False
            self._gate.notify_all()

    def _persist_pause_state(self, paused: bool) -> None:
        self.db.patch_resource('settings', 'default', {'queue_paused': bool(paused)})

    def list_workers(self) -> list[dict[str, Any]]:
        return [{**worker, 'concurrency': self._concurrency} for worker in self.workers]

    @staticmethod
    def _new_batch_token() -> str:
        return f"{datetime.now().strftime('%H%M%S_%m%d%Y')}_{uuid4().hex[:6]}"

    @staticmethod
    def _is_policy_block_error(value: object) -> bool:
        message = str(value or '').lower()
        return 'manual verification' in message or (
            'recaptcha' in message and 'unusual activity' in message
        )

    @staticmethod
    def _task_subdirectory(task_type: str, batch_token: str) -> str:
        task_label = 'I2V' if task_type == 'image_to_video' else 'Image'
        return f'Task_{task_label}_{batch_token}'

    async def enqueue_scene(self, scene_id: str, *, batch_token: str | None = None) -> dict[str, Any]:
        active = self.db.get_active_job_for_scene(scene_id)
        if active is not None:
            return active
        job = self.db.create_job(scene_id, batch_token=batch_token or self._new_batch_token())
        self.db.set_scene_runtime(scene_id, status=SceneStatus.QUEUED.value, progress=0)
        await self._job_queue.put(job['id'])
        return job

    async def enqueue_scenes(self, scene_ids: list[str]) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        batch_token = self._new_batch_token()
        seen: set[str] = set()
        for scene_id in scene_ids:
            if scene_id in seen:
                continue
            seen.add(scene_id)
            if self.db.get_scene(scene_id) is None or self.db.get_active_job_for_scene(scene_id) is not None:
                continue
            jobs.append(await self.enqueue_scene(scene_id, batch_token=batch_token))
        return jobs

    async def enqueue_all(self) -> list[dict[str, Any]]:
        scene_ids: list[str] = []
        for scene in self.db.list_scenes():
            output_path = str(scene.get('output_path') or '').strip()
            if output_path and Path(output_path).is_file():
                continue
            scene_ids.append(scene['id'])
        return await self.enqueue_scenes(scene_ids)

    async def _acquire_slot(self) -> None:
        async with self._gate:
            await self._gate.wait_for(lambda: not self._paused and self._running_count < self._concurrency)
            self._running_count += 1

    async def _release_slot(self) -> None:
        async with self._gate:
            self._running_count = max(0, self._running_count - 1)
            self._gate.notify_all()

    async def _pause_requested(self) -> bool:
        async with self._gate:
            return self._paused

    async def _requeue_for_pause(self, job_id: str, scene_id: str) -> None:
        self.db.update_job(
            job_id,
            {
                'status': JobStatus.QUEUED.value,
                'progress': 0,
                'worker_id': None,
            },
        )
        self.db.set_scene_runtime(scene_id, status=SceneStatus.QUEUED.value, progress=0)
        await self._job_queue.put(job_id)

    async def _enqueue_retry_after_delay(self, job_id: str, delay_seconds: float) -> None:
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        if not self._started:
            return
        job = self.db.get_job(job_id)
        if job is None or job['status'] != JobStatus.QUEUED.value:
            return
        if self.db.get_scene(job['scene_id']) is None:
            return
        await self._job_queue.put(job_id)

    def _schedule_retry(
        self,
        *,
        scene_id: str,
        attempt_index: int,
        batch_token: str | None,
        exc: Exception,
        settings: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not bool(settings.get('auto_retry_enabled', True)):
            return None
        max_retries = max(0, int(settings.get('max_retry_attempts', 2)))
        if attempt_index > max_retries or not is_retryable_provider_error(exc):
            return None

        retry_job = self.db.create_job(scene_id, batch_token=batch_token)
        self.db.set_scene_runtime(scene_id, status=SceneStatus.QUEUED.value, progress=0)
        base_delay = max(0.0, float(settings.get('retry_delay_seconds', 2.0)))
        delay_seconds = min(60.0, base_delay * (2 ** max(0, attempt_index - 1)))
        if isinstance(exc, ProviderQuotaError):
            delay_seconds = max(delay_seconds, self._quota_cooldown_seconds)
        task = asyncio.create_task(self._enqueue_retry_after_delay(retry_job['id'], delay_seconds))
        self._retry_tasks.add(task)
        task.add_done_callback(self._retry_tasks.discard)
        return retry_job

    async def _worker_loop(self, worker: dict[str, Any]) -> None:
        while True:
            job_id: str | None = None
            acquired = False
            provider_slot_acquired = False
            provider_slot: Any = None
            scene: dict[str, Any] | None = None
            quota_cooldown = False
            try:
                # Keep dequeue order stable when configured concurrency is lower
                # than the number of worker tasks. Without this gate every worker
                # can reserve a queued job before it gets a run slot, allowing
                # newer jobs to repeatedly overtake older reserved jobs.
                async with self._dequeue_gate:
                    job_id = await self._job_queue.get()
                    await self._acquire_slot()
                    acquired = True
                job = self.db.get_job(job_id)
                if job is None or job['status'] != JobStatus.QUEUED.value:
                    continue
                scene = self.db.get_scene(job['scene_id'])
                if scene is None:
                    self.db.update_job(job_id, {'status': JobStatus.FAILED.value, 'error': 'Scene not found'})
                    continue

                existing_output = str(scene.get('output_path') or '').strip()
                if existing_output and Path(existing_output).is_file() and Path(existing_output).stat().st_size > 100_000:
                    worker['progress'] = 100
                    self.db.update_job(
                        job_id,
                        {
                            'status': JobStatus.COMPLETED.value,
                            'progress': 100,
                            'output_path': existing_output,
                        },
                    )
                    continue

                settings = self.db.get_settings()
                sequence_index = self.db.get_job_batch_sequence_index(job_id)
                batch_scene_count = self.db.get_job_batch_scene_count(job_id)
                attempt_index = self.db.get_job_attempt_index(job_id)
                run_index = self.db.get_job_run_index(job_id)
                is_video = scene['task_type'] == 'image_to_video'
                output_directory = Path(
                    settings['video_output_directory'] if is_video else settings['image_output_directory']
                ).expanduser()
                use_subdirectory = bool(
                    settings.get('video_subdir_mode', True) if is_video else settings.get('image_subdir_mode', False)
                )
                batch_token = str(job.get('batch_token') or self._new_batch_token())
                if not job.get('batch_token'):
                    self.db.update_job(job_id, {'batch_token': batch_token})
                if use_subdirectory:
                    output_directory = output_directory / self._task_subdirectory(scene['task_type'], batch_token)
                repeat_count = min(4, max(1, int(settings.get('videos_per_prompt' if is_video else 'images_per_prompt', 1))))
                # Individually submitted scenes are separate one-item batches. Many
                # concurrent runs can therefore share sequence_index == 1 and the same
                # prompt slug. Give only those one-item batches a unique suffix so the
                # established naming for normal multi-scene batches stays unchanged.
                unique_job_suffix = f'_{str(job_id)[:8]}' if batch_scene_count == 1 else ''
                base_stem = f"{sequence_index}_Prompt_{sequence_index}_{prompt_slug(scene['prompt'])}"
                run_suffix = '' if run_index == 1 else f'_run{run_index}'
                retry_suffix = '' if attempt_index == 1 else f'_r{attempt_index}'

                provider_slot = await self.provider.acquire_job_slot(scene)
                provider_slot_acquired = True
                if await self._pause_requested():
                    await self._requeue_for_pause(job_id, scene['id'])
                    continue

                slot_email = str(provider_slot.get('email') or '').strip() if isinstance(provider_slot, dict) else ''
                worker.update(
                    state=WorkerState.RUNNING.value,
                    progress=5,
                    job_id=job_id,
                    account_email=slot_email or None,
                )
                self.db.update_job(
                    job_id,
                    {
                        'status': JobStatus.RUNNING.value,
                        'progress': 5,
                        'worker_id': worker['name'],
                    },
                )
                self.db.set_scene_runtime(scene['id'], status=SceneStatus.RUNNING.value, progress=5)

                output_paths: list[str] = []
                deferred_for_pause = False
                for output_index in range(1, repeat_count + 1):
                    loop = asyncio.get_running_loop()

                    def report_provider_progress(
                        provider_progress: int,
                        _stage: str | None = None,
                        *,
                        current_output_index: int = output_index,
                    ) -> None:
                        normalized = max(0, min(100, int(provider_progress)))
                        segment_start = 5 + int((current_output_index - 1) / repeat_count * 90)
                        segment_end = 5 + int(current_output_index / repeat_count * 90)
                        mapped = min(
                            94,
                            segment_start + int((segment_end - segment_start) * normalized / 100),
                        )

                        def apply_progress() -> None:
                            current = int(worker.get('progress') or 0)
                            if mapped <= current:
                                return
                            worker['progress'] = mapped
                            self.db.update_job(job_id, {'progress': mapped})
                            if isinstance(scene, dict) and scene.get('id'):
                                self.db.set_scene_runtime(
                                    scene['id'],
                                    status=SceneStatus.RUNNING.value,
                                    progress=mapped,
                                )

                        loop.call_soon_threadsafe(apply_progress)

                    runtime_scene = {
                        **scene,
                        '_output_directory': str(output_directory),
                        '_output_stem': f'{base_stem}_s{output_index}{run_suffix}{retry_suffix}{unique_job_suffix}',
                        '_video_resolution': settings.get('video_resolution', '720p'),
                        '_video_pair_mode': settings.get('video_pair_mode', 'PAIR_MODE_START_END'),
                        '_remove_watermark': bool(settings.get('remove_watermark', True)),
                        '_progress_callback': report_provider_progress,
                        '_provider_job_slot': provider_slot,
                    }
                    if self._requires_dispatch_pacing(runtime_scene):
                        pacing_key = self._dispatch_pacing_key(runtime_scene, provider_slot)
                        await self._wait_for_dispatch_delay(pacing_key)
                    if await self._pause_requested():
                        await self._requeue_for_pause(job_id, scene['id'])
                        deferred_for_pause = True
                        break
                    gen_timeout = 900.0 if runtime_scene.get('task_type') == 'image_to_video' else 600.0
                    output_paths.append(str(await asyncio.wait_for(self.provider.generate(runtime_scene), timeout=gen_timeout)))
                    progress = max(5, min(95, 5 + int(output_index / repeat_count * 90)))
                    worker['progress'] = progress
                    self.db.update_job(job_id, {'progress': progress})
                    self.db.set_scene_runtime(scene['id'], status=SceneStatus.RUNNING.value, progress=progress)

                if deferred_for_pause:
                    continue

                output_path = output_paths[-1]

                worker['progress'] = 100
                self.db.update_job(
                    job_id,
                    {
                        'status': JobStatus.COMPLETED.value,
                        'progress': 100,
                        'output_path': output_path,
                    },
                )
                self.db.set_scene_runtime(
                    scene['id'],
                    status=SceneStatus.COMPLETED.value,
                    progress=100,
                    output_path=output_path,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                job = self.db.get_job(job_id)
                if job is not None:
                    is_policy_block = isinstance(exc, ProviderAuthError) and self._is_policy_block_error(exc)
                    if is_policy_block:
                        await self.pause()
                        self.db.update_job(
                            job_id,
                            {
                                'status': JobStatus.QUEUED.value,
                                'progress': 0,
                                'worker_id': None,
                                'error': str(exc),
                            },
                        )
                        self.db.set_scene_runtime(
                            job['scene_id'],
                            status=SceneStatus.QUEUED.value,
                            progress=0,
                        )
                        await self._job_queue.put(job_id)
                        continue
                    attempt_index = self.db.get_job_attempt_index(job_id)
                    settings = self.db.get_settings()
                    err_msg = str(exc).strip()
                    if not err_msg and isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
                        err_msg = f'Hết thời gian chờ tạo media ({gen_timeout}s)'
                    elif not err_msg:
                        err_msg = repr(exc)
                    self.db.update_job(
                        job_id,
                        {
                            'status': JobStatus.FAILED.value,
                            'progress': 0,
                            'error': err_msg,
                        },
                    )
                    retry_job = self._schedule_retry(
                        scene_id=job['scene_id'],
                        attempt_index=attempt_index,
                        batch_token=job.get('batch_token'),
                        exc=exc,
                        settings=settings,
                    )
                    if retry_job is None:
                        self.db.set_scene_runtime(job['scene_id'], status=SceneStatus.FAILED.value, progress=0)
                if isinstance(exc, ProviderQuotaError):
                    worker.update(state=WorkerState.QUOTA_EXHAUSTED.value, progress=0)
                    quota_cooldown = True
            finally:
                if provider_slot_acquired and scene is not None:
                    await self.provider.release_job_slot(scene, provider_slot)
                if acquired:
                    await self._release_slot()
                if quota_cooldown and self._quota_cooldown_seconds > 0:
                    await asyncio.sleep(self._quota_cooldown_seconds)
                worker.update(state=WorkerState.READY.value, progress=0, job_id=None, account_email=None)
                if job_id is not None:
                    self._job_queue.task_done()
