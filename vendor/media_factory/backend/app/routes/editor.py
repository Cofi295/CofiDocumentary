from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from ..db import Database


router = APIRouter(prefix='/api/editor')


class EditorItemCreate(BaseModel):
    scene_id: str


def get_db(request: Request) -> Database:
    return request.app.state.db


@router.get('/items')
def list_editor_items(request: Request):
    return get_db(request).list_editor_items()


@router.post('/items', status_code=status.HTTP_201_CREATED)
def create_editor_item(payload: EditorItemCreate, request: Request):
    db = get_db(request)
    scene = db.get_scene(payload.scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail='Scene not found')
    if not scene.get('output_path'):
        raise HTTPException(status_code=422, detail='Scene has no output to hand off')
    return db.create_editor_item(scene)


@router.delete('/items/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_editor_item(item_id: str, request: Request):
    if not get_db(request).delete_editor_item(item_id):
        raise HTTPException(status_code=404, detail='Editor item not found')
    return Response(status_code=status.HTTP_204_NO_CONTENT)
