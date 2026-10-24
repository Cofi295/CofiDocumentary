from __future__ import annotations

import os
from pathlib import Path

from app.main import create_app


RUNTIME_ROOT = Path(__file__).resolve().parents[1]
cofi_doc_state = Path(__file__).resolve().parents[3] / "data" / "media_factory"
default_state = cofi_doc_state if cofi_doc_state.exists() else RUNTIME_ROOT / "data"
STATE_DIR = Path(
    os.getenv("COFI_MEDIA_FACTORY_STATE_DIR")
    or default_state
).resolve()
FRONTEND_DIST = Path(
    os.getenv("COFI_MEDIA_FACTORY_FRONTEND_DIST")
    or RUNTIME_ROOT / "frontend" / "dist"
).resolve()

STATE_DIR.mkdir(parents=True, exist_ok=True)

app = create_app(
    db_path=STATE_DIR / "cofi_studio.db",
    output_dir=STATE_DIR / "outputs",
    frontend_dist=FRONTEND_DIST,
)
