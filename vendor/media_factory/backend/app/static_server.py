from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, Response


def install_frontend_routes(application: FastAPI, dist_dir: str | Path) -> None:
    dist = Path(dist_dir).resolve()
    index = dist / 'index.html'

    def missing_build_response() -> PlainTextResponse:
        return PlainTextResponse(
            'Cofi Studio frontend production build is missing. '
            'Run the frontend build first (npm run build in frontend) or use the Vite development server.',
            status_code=503,
        )

    no_cache_headers = {'Cache-Control': 'no-cache, no-store, must-revalidate'}

    @application.get('/', include_in_schema=False)
    def frontend_root() -> Response:
        if not index.is_file():
            return missing_build_response()
        return FileResponse(index, media_type='text/html', headers=no_cache_headers)

    @application.get('/{spa_path:path}', include_in_schema=False)
    def frontend_spa(spa_path: str) -> Response:
        if spa_path == 'api' or spa_path.startswith('api/'):
            raise HTTPException(status_code=404, detail='API route not found')
        if not index.is_file():
            return missing_build_response()

        candidate = (dist / spa_path).resolve()
        if candidate == dist or dist not in candidate.parents:
            raise HTTPException(status_code=404, detail='Static path not found')
        if candidate.is_file():
            return FileResponse(candidate, headers=no_cache_headers)
        return FileResponse(index, media_type='text/html', headers=no_cache_headers)
