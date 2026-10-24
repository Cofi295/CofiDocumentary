from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..tool_supervisor import ToolSupervisor


router = APIRouter(prefix='/api/tools', tags=['tools'])


class ToolStartRequest(BaseModel):
    workspace: str | None = None


def _supervisor(request: Request) -> ToolSupervisor:
    return request.app.state.tool_supervisor


@router.get('')
def list_tools(request: Request) -> list[dict]:
    return _supervisor(request).list_status()


@router.get('/{tool_id}')
def tool_status(tool_id: str, request: Request) -> dict:
    try:
        return _supervisor(request).status(tool_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/{tool_id}/start')
def start_tool(tool_id: str, request: Request, body: ToolStartRequest | None = None) -> dict:
    try:
        return _supervisor(request).start(tool_id, workspace=body.workspace if body else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=502, detail=f'Could not start tool: {exc}') from exc


@router.post('/{tool_id}/stop')
def stop_tool(tool_id: str, request: Request) -> dict:
    try:
        return _supervisor(request).stop(tool_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/{tool_id}/restart')
def restart_tool(tool_id: str, request: Request, body: ToolStartRequest | None = None) -> dict:
    try:
        return _supervisor(request).restart(tool_id, workspace=body.workspace if body else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=502, detail=f'Could not restart tool: {exc}') from exc


@router.get('/{tool_id}/log')
def tool_log(tool_id: str, request: Request, lines: int = Query(default=120, ge=1, le=1000)) -> dict:
    try:
        return _supervisor(request).read_log(tool_id, lines=lines)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
