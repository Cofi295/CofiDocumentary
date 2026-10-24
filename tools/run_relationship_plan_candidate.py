from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from documentary.codex_gateway import CodexGateway


ROOT = Path(r"B:\ALL_TOOLS\CofiDocumentary")
JOB_ID = "20260911-151108-5894066c"
STAGING = ROOT / "workspaces" / JOB_ID / ".relationship_rewrite_candidate2"


def main() -> None:
    job_path = ROOT / "data" / "jobs" / JOB_ID / "job.json"
    job = json.loads(job_path.read_text(encoding="utf-8"))
    STAGING.mkdir(parents=True, exist_ok=True)
    gateway = CodexGateway(r"B:\ALL_TOOLS\CofiRemotion", session_root=STAGING)
    gateway.run(job, "plan", STAGING)
    print("PLAN_DONE")


if __name__ == "__main__":
    main()
