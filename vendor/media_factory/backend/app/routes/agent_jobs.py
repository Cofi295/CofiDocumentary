from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..agent_jobs import AgentJobSupervisor


router = APIRouter(prefix='/api/agent-jobs', tags=['agent-jobs'])


class AgentJobCreate(BaseModel):
    name: str = Field(default='Agent job', min_length=1, max_length=160)
    engine: str = 'codex'
    stage: str = 'research'
    workspace: str
    prompt: str = Field(min_length=1)
    project_id: str | None = None
    output_key: str | None = Field(default=None, max_length=64)


class AgentJobResume(BaseModel):
    prompt: str | None = None


def _jobs(request: Request) -> AgentJobSupervisor:
    return request.app.state.agent_jobs


@router.get('/engines')
def engines(request: Request) -> dict:
    return _jobs(request).engine_status()


@router.get('')
def list_jobs(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> list[dict]:
    return _jobs(request).list_jobs(limit=limit)


@router.post('')
def create_job(body: AgentJobCreate, request: Request) -> dict:
    try:
        return _jobs(request).create_job(
            name=body.name,
            engine=body.engine,
            stage=body.stage,
            workspace=body.workspace,
            prompt=body.prompt,
            project_id=body.project_id,
            output_key=body.output_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get('/{job_id}')
def get_job(job_id: str, request: Request) -> dict:
    try:
        return _jobs(request).get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/{job_id}/pause')
def pause_job(job_id: str, request: Request) -> dict:
    try:
        return _jobs(request).pause(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/{job_id}/resume')
def resume_job(job_id: str, body: AgentJobResume, request: Request) -> dict:
    try:
        return _jobs(request).resume(job_id, prompt=body.prompt)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/{job_id}/cancel')
def cancel_job(job_id: str, request: Request) -> dict:
    try:
        return _jobs(request).cancel(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get('/{job_id}/log')
def job_log(job_id: str, request: Request, lines: int = Query(default=200, ge=1, le=2000)) -> dict:
    try:
        return _jobs(request).read_log(job_id, lines=lines)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
