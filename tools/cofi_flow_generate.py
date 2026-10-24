from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: cofi_flow_generate.py REQUEST.json")
    request_path = Path(sys.argv[1]).resolve()
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    studio_root = Path(str(payload["studio_root"])).resolve()
    backend = studio_root / "backend"
    sys.path.insert(0, str(backend))

    from app.db import Database
    from app.providers.google import GoogleFlowAccountManager, GoogleFlowHeadlessClient, GoogleMediaProvider
    from app.secrets import KeyringSecretStore

    db = Database(studio_root / "data" / "cofi_studio.db")
    secrets = KeyringSecretStore(storage_dir=studio_root / "data" / "secrets" / "google-flow")
    manager = GoogleFlowAccountManager(db, secrets, profile_root=studio_root / "data" / "google-flow-profiles")
    manager.resume_saved_sessions()
    output_dir = Path(str(payload["scene"].get("_output_directory") or request_path.parent)).resolve()
    provider = GoogleMediaProvider(
        output_dir,
        manager,
        flow_client=GoogleFlowHeadlessClient(output_dir, manager),
    )
    try:
        output_path = asyncio.run(provider.generate(dict(payload["scene"])))
        print(json.dumps({"output_path": str(Path(output_path).resolve())}, ensure_ascii=False))
        return 0
    finally:
        manager.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
