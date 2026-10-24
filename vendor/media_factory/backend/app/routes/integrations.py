from __future__ import annotations

import asyncio
from typing import Final

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ..tool_supervisor import ToolSupervisor


router = APIRouter(prefix='/api/integrations', tags=['integrations'])


TOOL_TARGETS: Final[dict[str, str]] = {
    'radar': 'cofi-radar',
    'voice': 'cofi-voice',
}


def _supervisor(request: Request) -> ToolSupervisor:
    return request.app.state.tool_supervisor


async def _ensure_running(supervisor: ToolSupervisor, tool_id: str) -> None:
    status = supervisor.status(tool_id)
    if not status['available']:
        raise HTTPException(status_code=503, detail=f'{status["name"]} is unavailable')
    if not status['running'] and status.get('state') != 'starting':
        status = supervisor.start(tool_id)
        if status.get('error'):
            raise HTTPException(status_code=503, detail=status['error'])

    for _ in range(100):
        status = supervisor.status(tool_id)
        if status['running']:
            return
        if status.get('state') == 'exited':
            raise HTTPException(status_code=502, detail=f'{status["name"]} exited during startup')
        await asyncio.sleep(0.2)
    raise HTTPException(status_code=504, detail=f'{status["name"]} did not become ready in time')


def _rewrite_local_links(tool: str, content_type: str, body: bytes) -> bytes:
    if tool != 'voice' or 'application/json' not in content_type.lower():
        return body
    text = body.decode('utf-8', errors='replace')
    text = text.replace('"/static/', '"/api/integrations/voice/static/')
    return text.encode('utf-8')


@router.api_route('/{tool}/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
async def proxy_tool(tool: str, path: str, request: Request) -> Response:
    target = TOOL_TARGETS.get(tool)
    if not target:
        raise HTTPException(status_code=404, detail='Unknown integrated tool')

    tool_id = target
    supervisor = _supervisor(request)
    await _ensure_running(supervisor, tool_id)
    status = supervisor.status(tool_id)
    base_url = str(status.get('url') or '').rstrip('/')
    if not base_url:
        raise HTTPException(status_code=503, detail=f'{tool_id} has no service URL')
    target_url = f'{base_url}/{path.lstrip("/")}'
    if request.url.query:
        target_url = f'{target_url}?{request.url.query}'

    headers: dict[str, str] = {}
    for name in ('content-type', 'accept', 'accept-language', 'range'):
        value = request.headers.get(name)
        if value:
            headers[name] = value

    body = await request.body()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(900.0)) as client:
            upstream = await client.request(
                request.method,
                target_url,
                headers=headers,
                content=body if body else None,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f'{tool_id} request failed: {exc}') from exc

    content_type = upstream.headers.get('content-type', 'application/octet-stream')
    payload = _rewrite_local_links(tool, content_type, upstream.content)
    response_headers = {
        name: value
        for name, value in upstream.headers.items()
        if name.lower() in {'content-type', 'content-disposition', 'cache-control', 'accept-ranges'}
    }
    return Response(content=payload, status_code=upstream.status_code, headers=response_headers)
