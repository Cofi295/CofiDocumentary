from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..project_manifests import ProjectManifestStore


router = APIRouter(prefix='/api/projects', tags=['project-manifests'])


class ManifestPatch(BaseModel):
    current_stage: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=300)
    channel: str | None = Field(default=None, max_length=300)
    workflow_mode: str | None = Field(default=None, max_length=64)
    production_settings: dict[str, Any] | None = None


class StagePatch(BaseModel):
    status: str | None = Field(default=None, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    advance: bool = False


def _store(request: Request) -> ProjectManifestStore:
    return request.app.state.project_manifests


@router.get('/{project_id}/manifest')
def get_manifest(project_id: str, request: Request) -> dict:
    try:
        return _store(request).ensure(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch('/{project_id}/manifest')
def patch_manifest(project_id: str, body: ManifestPatch, request: Request) -> dict:
    values = body.model_dump(exclude_none=True)
    try:
        return _store(request).patch(project_id, values)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch('/{project_id}/manifest/stages/{stage}')
def patch_stage(project_id: str, stage: str, body: StagePatch, request: Request) -> dict:
    values = dict(body.payload)
    if body.status is not None:
        values['status'] = body.status
    try:
        return _store(request).update_stage(project_id, stage, values, advance=body.advance)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
