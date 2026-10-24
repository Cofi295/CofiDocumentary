from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..codex_chat import CodexChatService


router = APIRouter(prefix='/api/codex-chat', tags=['codex-chat'])


class CodexChatMessage(BaseModel):
    message: str = ''
    app_path: str | None = None
    selected_project_id: str | None = None
    mode: str | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=8)


class CodexChatAttachmentUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=180)
    content_type: str = Field(min_length=1, max_length=80)
    data_base64: str = Field(min_length=1)


def _chat(request: Request) -> CodexChatService:
    return request.app.state.codex_chat


@router.get('/status')
def status(request: Request) -> dict:
    return _chat(request).status()


@router.get('')
def history(request: Request, limit: int = Query(default=100, ge=1, le=300)) -> list[dict]:
    return _chat(request).history(limit=limit)


@router.post('', status_code=202)
def send(body: CodexChatMessage, request: Request) -> dict:
    try:
        return _chat(request).send(
            body.message,
            app_path=body.app_path,
            selected_project_id=body.selected_project_id,
            mode=body.mode,
            attachment_ids=body.attachment_ids,
            wait=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post('/attachments', status_code=201)
def upload_attachment(body: CodexChatAttachmentUpload, request: Request) -> dict:
    try:
        payload = base64.b64decode(body.data_base64, validate=True)
        return _chat(request).save_attachment(
            filename=body.filename,
            content_type=body.content_type,
            payload=payload,
        )
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/attachments/{attachment_id}')
def attachment(attachment_id: str, request: Request) -> FileResponse:
    try:
        path = _chat(request).attachment_path(attachment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path)


@router.post('/reset')
def reset(request: Request) -> dict:
    return _chat(request).reset()
