"""Create bounded, per-launch logs outside the project root."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import sys


def prepare_log(root: Path, kind: str, *, keep: int = 7) -> Path:
    if kind not in {"backend", "desktop"}:
        raise ValueError("Unknown runtime log kind")
    logs = (root / "logs").resolve()
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    current = logs / f"{kind}-{stamp}-{os.getpid()}.log"
    current.touch(exist_ok=False)
    previous = sorted((path for path in logs.glob(f"{kind}-*.log") if path != current), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in previous[max(1, keep) - 1:]:
        try:
            path.unlink()
        except OSError:
            pass  # A still-open log must not prevent the app from starting.
    return current


if __name__ == "__main__":
    print(prepare_log(Path(__file__).resolve().parent, sys.argv[1]))
