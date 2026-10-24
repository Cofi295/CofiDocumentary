from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, HttpUrl

from ..db import DEFAULT_SETTINGS, Database
from ..queue import QueueSupervisor


router = APIRouter(prefix='/api')

REFERENCE_IMAGE_EXTENSIONS = {'.jpeg', '.jpg', '.png', '.webp'}


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default='', max_length=4000)
    status: str = Field(default='active', min_length=1, max_length=64)


class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    status: str | None = Field(default=None, min_length=1, max_length=64)


class ProviderProfileCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=160)
    enabled: bool = True
    status: str = Field(default='ready', min_length=1, max_length=64)
    notes: str = Field(default='', max_length=4000)
    credential: str | None = None


class ProviderProfilePatch(BaseModel):
    provider: str | None = Field(default=None, min_length=1, max_length=120)
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    enabled: bool | None = None
    status: str | None = Field(default=None, min_length=1, max_length=64)
    notes: str | None = Field(default=None, max_length=4000)
    credential: str | None = None


class SettingsPatch(BaseModel):
    default_model: str | None = Field(default=None, min_length=1, max_length=120)
    default_aspect_ratio: str | None = Field(default=None, min_length=1, max_length=32)
    default_concurrency: int | None = Field(default=None, ge=1, le=10)
    default_mode: Literal['manual', 'hybrid', 'codex'] | None = None
    output_directory: str | None = Field(default=None, min_length=1, max_length=2048)
    image_output_directory: str | None = Field(default=None, min_length=1, max_length=2048)
    video_output_directory: str | None = Field(default=None, min_length=1, max_length=2048)
    ref_image_dir: str | None = Field(default=None, max_length=2048)
    ref_match_mode: Literal['exact'] | None = None
    worker_delay_seconds: float | None = Field(default=None, ge=0, le=300)
    worker_delay_min_seconds: float | None = Field(default=None, ge=0, le=300)
    worker_delay_max_seconds: float | None = Field(default=None, ge=0, le=300)
    images_per_prompt: int | None = Field(default=None, ge=1, le=4)
    videos_per_prompt: int | None = Field(default=None, ge=1, le=4)
    image_subdir_mode: bool | None = None
    video_subdir_mode: bool | None = None
    upscale_1k: bool | None = None
    upscale_2k: bool | None = None
    upscale_4k: bool | None = None
    video_resolution: Literal['720p', '1080p', '4K'] | None = None
    video_pair_mode: Literal['PAIR_MODE_START_END', 'PAIR_MODE_START_ONLY'] | None = None
    auto_disable_on_quota: bool | None = None
    remove_watermark: bool | None = None
    auto_retry_enabled: bool | None = None
    max_retry_attempts: int | None = Field(default=None, ge=0, le=10)
    retry_delay_seconds: float | None = Field(default=None, ge=0, le=300)
    autosave: bool | None = None


class AffiliateCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    source_url: HttpUrl | None = None
    target_platform: str = Field(min_length=1, max_length=120)
    commission_note: str = Field(default='', max_length=1000)
    status: Literal['Discover', 'Script', 'Media', 'Publish', 'Tracking'] = 'Discover'
    linked_media_scene_ids: list[str] = Field(default_factory=list)


class AffiliatePatch(BaseModel):
    product_name: str | None = Field(default=None, min_length=1, max_length=200)
    source_url: HttpUrl | None = None
    target_platform: str | None = Field(default=None, min_length=1, max_length=120)
    commission_note: str | None = Field(default=None, max_length=1000)
    status: Literal['Discover', 'Script', 'Media', 'Publish', 'Tracking'] | None = None
    linked_media_scene_ids: list[str] | None = None


class LongformCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    target_duration: int = Field(ge=1)
    aspect_ratio: str = Field(min_length=1, max_length=32)
    scene_count: int = Field(default=0, ge=0)
    linked_workflow_id: str | None = Field(default=None, max_length=200)
    status: str = Field(default='draft', min_length=1, max_length=64)


class LongformPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    target_duration: int | None = Field(default=None, ge=1)
    aspect_ratio: str | None = Field(default=None, min_length=1, max_length=32)
    scene_count: int | None = Field(default=None, ge=0)
    linked_workflow_id: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, min_length=1, max_length=64)


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_queue(request: Request) -> QueueSupervisor:
    return request.app.state.queue


def clean_payload(payload: BaseModel, *, exclude_unset: bool = False) -> dict[str, Any]:
    values = payload.model_dump(mode='json', exclude_unset=exclude_unset)
    values.pop('credential', None)
    return values


def require_updated(resource: dict[str, Any] | None, detail: str):
    if resource is None:
        raise HTTPException(status_code=404, detail=detail)
    return resource


def find_exact_reference_image(directory: str, key: str) -> str | None:
    normalized_key = key.strip().casefold()
    if not directory or not normalized_key:
        return None

    root = Path(directory).expanduser()
    if not root.is_dir():
        return None

    matches = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_file()
            and path.suffix.casefold() in REFERENCE_IMAGE_EXTENSIONS
            and path.stem.casefold() == normalized_key
        ),
        key=lambda path: path.name.casefold(),
    )
    return str(matches[0].resolve()) if matches else None


async def save_settings(payload: SettingsPatch, request: Request, *, replace: bool = False):
    db = get_db(request)
    values = clean_payload(payload, exclude_unset=True)
    if values.get('video_resolution') not in {None, '720p'}:
        raise HTTPException(status_code=422, detail='Only 720p video output is verified with the current Google Flow runtime.')
    if values.get('upscale_1k') is False or values.get('upscale_2k') is True or values.get('upscale_4k') is True:
        raise HTTPException(status_code=422, detail='Only the verified 1K image path is enabled; Flow 2K/4K upscale remains unverified.')
    current = db.get_settings()
    merged = {
        key: value
        for key, value in current.items()
        if key not in {'id', 'created_at', 'updated_at'}
    }
    if replace:
        merged = {**DEFAULT_SETTINGS, **values}
    else:
        merged.update(values)
    if 'worker_delay_seconds' in values and 'worker_delay_min_seconds' not in values and 'worker_delay_max_seconds' not in values:
        merged['worker_delay_min_seconds'] = values['worker_delay_seconds']
        merged['worker_delay_max_seconds'] = values['worker_delay_seconds']
    delay_minimum = max(0.0, float(merged.get('worker_delay_min_seconds', 0)))
    delay_maximum = max(0.0, float(merged.get('worker_delay_max_seconds', delay_minimum)))
    if delay_maximum < delay_minimum:
        raise HTTPException(status_code=422, detail='worker_delay_max_seconds must be greater than or equal to worker_delay_min_seconds')
    if 'default_concurrency' in values:
        await get_queue(request).set_concurrency(values['default_concurrency'])
    if {'worker_delay_seconds', 'worker_delay_min_seconds', 'worker_delay_max_seconds'} & values.keys():
        get_queue(request).set_worker_delay_range(delay_minimum, delay_maximum)
    return db.create_resource('settings', merged, resource_id='default', replace=True)


@router.get('/projects')
def list_projects(request: Request):
    return get_db(request).list_resources('projects')


@router.post('/projects', status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, request: Request):
    created = get_db(request).create_resource('projects', clean_payload(payload))
    manifests = getattr(request.app.state, 'project_manifests', None)
    if not manifests:
        return created
    manifests.ensure(created['id'])
    return get_db(request).get_resource('projects', created['id'])


@router.patch('/projects/{project_id}')
def patch_project(project_id: str, payload: ProjectPatch, request: Request):
    return require_updated(
        get_db(request).patch_resource('projects', project_id, clean_payload(payload, exclude_unset=True)),
        'Project not found',
    )


@router.delete('/projects/{project_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, request: Request):
    if not get_db(request).delete_resource('projects', project_id):
        raise HTTPException(status_code=404, detail='Project not found')
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/provider-profiles')
def list_provider_profiles(request: Request):
    return get_db(request).list_resources('provider_profiles')


@router.post('/provider-profiles', status_code=status.HTTP_201_CREATED)
def create_provider_profile(payload: ProviderProfileCreate, request: Request):
    return get_db(request).create_resource('provider_profiles', clean_payload(payload))


@router.patch('/provider-profiles/{profile_id}')
def patch_provider_profile(profile_id: str, payload: ProviderProfilePatch, request: Request):
    return require_updated(
        get_db(request).patch_resource(
            'provider_profiles',
            profile_id,
            clean_payload(payload, exclude_unset=True),
        ),
        'Provider profile not found',
    )


@router.get('/settings')
def get_settings(request: Request):
    return get_db(request).get_settings()


@router.get('/settings/reference-images/match')
def match_reference_image(key: str, request: Request):
    settings = get_db(request).get_settings()
    match_mode = settings.get('ref_match_mode', 'exact')
    if match_mode != 'exact':
        raise HTTPException(status_code=422, detail=f'Unsupported reference match mode: {match_mode}')
    path = find_exact_reference_image(str(settings.get('ref_image_dir') or ''), key)
    return {'key': key, 'match_mode': match_mode, 'path': path}


@router.post('/settings/pick-directory')
def pick_settings_directory():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected = filedialog.askdirectory(title='Cofi Studio - Chọn thư mục lưu')
        root.destroy()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'Folder picker is unavailable: {exc}') from exc
    return {'path': selected or ''}


@router.post('/settings', status_code=status.HTTP_201_CREATED)
async def create_settings(payload: SettingsPatch, request: Request):
    return await save_settings(payload, request)


@router.put('/settings')
async def put_settings(payload: SettingsPatch, request: Request):
    return await save_settings(payload, request)


@router.patch('/settings/{settings_id}')
async def patch_settings(settings_id: str, payload: SettingsPatch, request: Request):
    if settings_id != 'default':
        raise HTTPException(status_code=404, detail='Settings not found')
    return await save_settings(payload, request)


@router.get('/affiliate/items')
def list_affiliate_items(request: Request):
    return get_db(request).list_resources('affiliate_items')


@router.post('/affiliate/items', status_code=status.HTTP_201_CREATED)
def create_affiliate_item(payload: AffiliateCreate, request: Request):
    return get_db(request).create_resource('affiliate_items', clean_payload(payload))


@router.patch('/affiliate/items/{item_id}')
def patch_affiliate_item(item_id: str, payload: AffiliatePatch, request: Request):
    return require_updated(
        get_db(request).patch_resource(
            'affiliate_items', item_id, clean_payload(payload, exclude_unset=True)
        ),
        'Affiliate item not found',
    )


@router.delete('/affiliate/items/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_affiliate_item(item_id: str, request: Request):
    if not get_db(request).delete_resource('affiliate_items', item_id):
        raise HTTPException(status_code=404, detail='Affiliate item not found')
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/longform/projects')
def list_longform_projects(request: Request):
    return get_db(request).list_resources('longform_projects')


@router.post('/longform/projects', status_code=status.HTTP_201_CREATED)
def create_longform_project(payload: LongformCreate, request: Request):
    return get_db(request).create_resource('longform_projects', clean_payload(payload))


@router.patch('/longform/projects/{project_id}')
def patch_longform_project(project_id: str, payload: LongformPatch, request: Request):
    return require_updated(
        get_db(request).patch_resource(
            'longform_projects', project_id, clean_payload(payload, exclude_unset=True)
        ),
        'Longform project not found',
    )
