from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..workflow_engine import WorkflowEngine, validate_workflow

router = APIRouter(prefix='/api/workflows')


def get_engine(request: Request) -> WorkflowEngine:
    return request.app.state.workflow_engine


@router.get('/{workflow_id}')
def get_workflow(workflow_id: str, request: Request):
    return get_engine(request).get_or_create(workflow_id)


@router.put('/{workflow_id}')
def save_workflow(workflow_id: str, payload: dict[str, Any], request: Request):
    return get_engine(request).save(workflow_id, payload)


@router.post('/{workflow_id}/validate')
def validate_saved_workflow(workflow_id: str, request: Request):
    workflow = get_engine(request).get_or_create(workflow_id)
    errors = validate_workflow(workflow)
    return {'valid': not errors, 'errors': errors}


@router.post('/{workflow_id}/run')
async def run_workflow(workflow_id: str, request: Request):
    try:
        return await get_engine(request).run(workflow_id)
    except ValueError as exc:
        details = exc.args[0] if exc.args else ['Invalid workflow']
        raise HTTPException(status_code=422, detail=details) from exc
