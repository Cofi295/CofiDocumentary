from __future__ import annotations

from pathlib import Path as FilePath
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response, status
from fastapi.responses import FileResponse

from ..db import Database
from ..queue import QueueSupervisor
from ..schemas import JobOut, RetryScenesRequest, SceneCreate, SceneOut, SceneUpdate, TaskType, WorkerOut

router = APIRouter(prefix='/api')


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_queue(request: Request) -> QueueSupervisor:
    return request.app.state.queue


@router.get('/scenes', response_model=list[SceneOut])
def list_scenes(request: Request):
    return get_db(request).list_scenes()


def _purge_stale_batch_on_first_scene(
    db: Database,
    scene_name: str,
    new_prompt: str,
    *,
    keep_scene_id: str | None = None,
) -> None:
    normalized_name = str(scene_name or '').strip()
    if normalized_name not in {'AI bổ sung · B001-V01', 'AI bổ sung · B001'}:
        return
    normalized_prompt = str(new_prompt or '').strip()
    if not normalized_prompt:
        return
    scenes = db.list_scenes()
    matching_first = [
        s for s in scenes
        if str(s.get('name') or '').strip() == normalized_name
    ]
    if not matching_first:
        return
    if all(str(s.get('prompt') or '').strip() == normalized_prompt for s in matching_first):
        return
    # A new Documentary job is staging Beat 1 with a different prompt while old job scenes remain.
    with db._connect() as connection:
        active = connection.execute(
            "SELECT 1 FROM jobs WHERE status IN ('queued', 'running') LIMIT 1"
        ).fetchone()
        if active is not None:
            return
        connection.execute('DELETE FROM jobs')
        connection.execute('DELETE FROM editor_items')
        if keep_scene_id:
            connection.execute('DELETE FROM scenes WHERE id != ?', (keep_scene_id,))
        else:
            connection.execute('DELETE FROM scenes')
        connection.commit()


@router.post('/scenes', response_model=SceneOut, status_code=status.HTTP_201_CREATED)
def create_scene(payload: SceneCreate, request: Request):
    setattr(get_queue(request), '_restage_requested', False)
    db = get_db(request)
    data = payload.model_dump(mode='json')
    _purge_stale_batch_on_first_scene(db, str(data.get('name') or ''), str(data.get('prompt') or ''))
    return db.create_scene(data)


@router.patch('/scenes/{scene_id}', response_model=SceneOut)
def update_scene(scene_id: str, payload: SceneUpdate, request: Request):
    db = get_db(request)
    existing = db.get_scene(scene_id)
    if existing is None:
        raise HTTPException(status_code=404, detail='Scene not found')
    values = payload.model_dump(exclude_unset=True, mode='json')
    if 'reference_images' in values:
        references = values.get('reference_images') or []
        values['reference_image'] = references[0] if references else None
    elif 'reference_image' in values:
        legacy = values.get('reference_image')
        values['reference_images'] = [legacy] if legacy else []
    if values.get('task_type') == TaskType.IMAGE_TO_VIDEO.value and values.get('duration_seconds') is None:
        values['duration_seconds'] = 8
    if 'prompt' in values and str(values.get('prompt') or '').strip() != str(existing.get('prompt') or '').strip():
        values['status'] = 'idle'
        values['progress'] = 0
        values['output_path'] = None
        _purge_stale_batch_on_first_scene(
            db,
            str(values.get('name') or existing.get('name') or ''),
            str(values.get('prompt') or ''),
            keep_scene_id=scene_id,
        )
    updated = db.update_scene(scene_id, values)
    if updated is None:
        raise HTTPException(status_code=404, detail='Scene not found')
    return updated


@router.delete('/scenes/{scene_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_scene(scene_id: str, request: Request):
    import time
    db = get_db(request)
    active = db.get_active_job_for_scene(scene_id)
    if active is not None:
        raise HTTPException(status_code=409, detail='Cannot delete a scene while it is queued or running')
    existing = db.get_scene(scene_id)
    if not db.delete_scene(scene_id):
        raise HTTPException(status_code=404, detail='Scene not found')
    queue = get_queue(request)
    deleted_list = list(getattr(queue, '_deleted_scenes', []))
    deleted_list.append({
        'id': scene_id,
        'name': str((existing or {}).get('name') or ''),
        'deleted_at': time.time(),
    })
    setattr(queue, '_deleted_scenes', deleted_list[-200:])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete('/scenes')
async def delete_all_scenes(request: Request):
    import time
    queue = get_queue(request)
    setattr(queue, '_restage_requested', False)
    deleted_count = await queue.clear_all_scenes()
    setattr(queue, '_last_cleared_at', time.time())
    setattr(queue, '_deleted_scenes', [])
    return {'deleted_count': deleted_count}


@router.post('/scenes/{scene_id}/run', response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def run_scene(scene_id: str, request: Request):
    db = get_db(request)
    if db.get_scene(scene_id) is None:
        raise HTTPException(status_code=404, detail='Scene not found')
    return await get_queue(request).enqueue_scene(scene_id)


@router.post('/scenes/run-all', response_model=list[JobOut], status_code=status.HTTP_202_ACCEPTED)
async def run_all(request: Request):
    queue = get_queue(request)
    if not get_db(request).list_scenes():
        setattr(queue, '_restage_requested', True)
        return []
    return await queue.enqueue_all()


@router.post('/scenes/retry-all', response_model=list[JobOut], status_code=status.HTTP_202_ACCEPTED)
async def retry_all(request: Request):
    queue = get_queue(request)
    scene_ids = [scene['id'] for scene in get_db(request).list_scenes()]
    if not scene_ids:
        setattr(queue, '_restage_requested', True)
        return []
    return await queue.enqueue_scenes(scene_ids)


@router.post('/scenes/retry-errors', response_model=list[JobOut], status_code=status.HTTP_202_ACCEPTED)
async def retry_errors(request: Request):
    scene_ids = [scene['id'] for scene in get_db(request).list_scenes() if scene['status'] == 'failed']
    return await get_queue(request).enqueue_scenes(scene_ids)


@router.post('/scenes/retry-selected', response_model=list[JobOut], status_code=status.HTTP_202_ACCEPTED)
async def retry_selected(payload: RetryScenesRequest, request: Request):
    db = get_db(request)
    missing = [scene_id for scene_id in payload.scene_ids if db.get_scene(scene_id) is None]
    if missing:
        raise HTTPException(status_code=404, detail=f"Scene not found: {missing[0]}")
    return await get_queue(request).enqueue_scenes(payload.scene_ids)


@router.get('/jobs', response_model=list[JobOut])
def list_jobs(request: Request):
    return get_db(request).list_jobs()


@router.get('/workers', response_model=list[WorkerOut])
def list_workers(request: Request):
    return get_queue(request).list_workers()


@router.post('/queue/concurrency/{value}')
async def set_concurrency(
    request: Request,
    value: int = Path(ge=1, le=10),
):
    concurrency = await get_queue(request).set_concurrency(value)
    return {'concurrency': concurrency}


@router.get('/queue/status')
def queue_status(request: Request):
    queue = get_queue(request)
    scenes = get_db(request).list_scenes()
    counts: dict[str, int] = {'total': len(scenes), 'completed': 0, 'running': 0, 'queued': 0, 'failed': 0, 'draft': 0}
    for s in scenes:
        st = str(s.get('status') or 'draft').lower()
        counts[st] = counts.get(st, 0) + 1
    return {
        'paused': queue.paused,
        'concurrency': queue.concurrency,
        'restage_requested': bool(getattr(queue, '_restage_requested', False)),
        'last_cleared_at': getattr(queue, '_last_cleared_at', None),
        'deleted_scenes': list(getattr(queue, '_deleted_scenes', []))[-100:],
        'scene_counts': counts,
    }


@router.post('/queue/pause')
async def pause_queue(request: Request):
    queue = get_queue(request)
    await queue.pause()
    return {'paused': True, 'concurrency': queue.concurrency}


@router.post('/queue/resume')
async def resume_queue(request: Request):
    queue = get_queue(request)
    await queue.resume()
    return {'paused': False, 'concurrency': queue.concurrency}


def _is_allowed_media_path(request: Request, path: FilePath) -> bool:
    resolved = path.resolve()
    db = get_db(request)
    settings = db.get_settings()
    roots = [
        request.app.state.output_dir,
        request.app.state.upload_dir,
        FilePath(settings['image_output_directory']).expanduser().resolve(),
        FilePath(settings['video_output_directory']).expanduser().resolve(),
    ]
    if any(resolved == root or root in resolved.parents for root in roots):
        return True

    # Keep old generated media and configured scene references previewable after the user
    # changes output folders, without turning /api/files into an arbitrary filesystem reader.
    known_paths = [
        item.get('output_path')
        for item in [*db.list_scenes(), *db.list_jobs()]
        if item.get('output_path')
    ]
    for scene in db.list_scenes():
        if scene.get('reference_image'):
            known_paths.append(scene['reference_image'])
        for ref in (scene.get('reference_images') or []):
            if ref:
                known_paths.append(ref)
    return any(FilePath(str(value)).expanduser().resolve() == resolved for value in known_paths)


@router.post('/uploads/reference')
async def upload_reference_image(
    request: Request,
    filename: str = Query(min_length=1, max_length=255),
):
    content_type = (request.headers.get('content-type') or '').split(';', 1)[0].lower()
    if not content_type.startswith('image/'):
        raise HTTPException(status_code=415, detail='Reference upload must be an image')
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail='Reference image is empty')
    if len(body) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='Reference image exceeds 25 MB')

    suffix = FilePath(filename).suffix.lower()
    if suffix not in {'.png', '.jpg', '.jpeg', '.webp', '.gif'}:
        suffix = {
            'image/jpeg': '.jpg',
            'image/webp': '.webp',
            'image/gif': '.gif',
        }.get(content_type, '.png')
    upload_dir: FilePath = request.app.state.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = (upload_dir / f'{uuid4().hex}{suffix}').resolve()
    path.write_bytes(body)
    return {'path': str(path), 'filename': FilePath(filename).name}


def _delete_managed_files(root: FilePath, *, keep: set[FilePath] | None = None) -> tuple[int, int]:
    if not root.exists():
        return 0, 0
    keep = keep or set()
    files_deleted = 0
    bytes_cleared = 0
    for path in sorted(root.rglob('*'), reverse=True):
        if path.is_file():
            resolved = path.resolve()
            if resolved in keep:
                continue
            try:
                size = path.stat().st_size
                path.unlink()
            except FileNotFoundError:
                continue
            files_deleted += 1
            bytes_cleared += size
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
    return files_deleted, bytes_cleared


@router.post('/cache/clear')
def clear_media_cache(request: Request):
    db = get_db(request)
    referenced_uploads = {
        FilePath(str(scene['reference_image'])).expanduser().resolve()
        for scene in db.list_scenes()
        if scene.get('reference_image')
    }
    upload_files, upload_bytes = _delete_managed_files(
        request.app.state.upload_dir,
        keep=referenced_uploads,
    )
    cache_files, cache_bytes = _delete_managed_files(request.app.state.cache_dir)
    clear_provider_cache = getattr(request.app.state.google_provider, 'clear_upload_cache', None)
    provider_upload_cache_entries = int(clear_provider_cache()) if callable(clear_provider_cache) else 0
    return {
        'files_deleted': upload_files + cache_files,
        'bytes_cleared': upload_bytes + cache_bytes,
        'uploads_deleted': upload_files,
        'cache_files_deleted': cache_files,
        'provider_upload_cache_entries_cleared': provider_upload_cache_entries,
    }


@router.get('/files')
def serve_media_file(request: Request, path: str = Query(min_length=1, max_length=4096)):
    candidate = FilePath(path)
    if not candidate.is_absolute() or not _is_allowed_media_path(request, candidate):
        raise HTTPException(status_code=403, detail='Media path is outside the Cofi Studio workspace')
    resolved = candidate.resolve()
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail='Media file not found')
    return FileResponse(resolved)
