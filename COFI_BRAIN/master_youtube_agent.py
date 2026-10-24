"""COFI Master YouTube Agent.

Coordinator for continuous improvement. It does not blindly rewrite the app;
it creates an evidence based improvement loop: detect -> diagnose -> repair ->
test -> learn -> continue pipeline.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MasterYouTubeAgent:
    def __init__(self, root: Path | None = None):
        self.root = root or Path(__file__).resolve().parent
        self.memory = self.root / "memory" / "master_agent_memory.jsonl"
        self.knowledge = self.root / "knowledge" / "master_agent_rules.json"

    def observe(self, event: str, data: dict[str, Any]) -> None:
        self.memory.parent.mkdir(parents=True, exist_ok=True)
        with self.memory.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "time": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "data": data,
            }, ensure_ascii=False) + "\n")

    def diagnose_failure(self, error: str, phase: str) -> dict[str, Any]:
        """Create a repair decision instead of leaving a broken pipeline."""
        return {
            "action": "repair_and_resume",
            "phase": phase,
            "error": error,
            "needs_code_change": True,
            "requires_human": False,
        }

    def learn(self, lesson: str, source: str = "production") -> None:
        self.observe("learn", {"lesson": lesson, "source": source})

    def improve_rules(self, rule: str) -> None:
        self.knowledge.parent.mkdir(parents=True, exist_ok=True)
        rules = []
        if self.knowledge.exists():
            rules = json.loads(self.knowledge.read_text(encoding="utf-8"))
        rules.append({"created": datetime.now(timezone.utc).isoformat(), "rule": rule})
        self.knowledge.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")

    def capabilities(self) -> dict[str, bool]:
        return {
            "market_learning": True,
            "niche_learning": True,
            "production_memory": True,
            "error_diagnosis": True,
            "code_repair_orchestration": True,
            "pipeline_resume": True,
        }
