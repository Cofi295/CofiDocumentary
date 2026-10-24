"""Runtime permission view for COFI agents.

Keeps the chatbot-facing agent aware of the capabilities granted by COFI.
"""

from pathlib import Path
import json


class PermissionGateway:
    def __init__(self, root: Path | None = None):
        self.root = root or Path(__file__).resolve().parent
        self.permission_file = self.root / "knowledge" / "codex_session_permissions.json"

    def get_permissions(self) -> dict:
        if not self.permission_file.exists():
            return {"enabled": False}
        return json.loads(self.permission_file.read_text(encoding="utf-8"))

    def status_message(self) -> str:
        permissions = self.get_permissions()
        return (
            "COFI Master Agent permissions: "
            + ", ".join(k for k, v in permissions.items() if v is True)
            + "."
        )
