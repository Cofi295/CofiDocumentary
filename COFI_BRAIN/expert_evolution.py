"""COFI Expert Evolution core.

Stores producer knowledge, reviews completed work and turns observations
into reusable production rules.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ExpertEvolutionEngine:
    def __init__(self, root: Path | None = None):
        self.root = root or Path(__file__).resolve().parent
        self.experience = self.root / "experience"
        self.knowledge = self.root / "knowledge"
        self.experience.mkdir(exist_ok=True)
        self.knowledge.mkdir(exist_ok=True)

    def learn(self, observation: dict[str, Any], domain: str = "youtube_documentary") -> dict[str, Any]:
        """Store reusable production experience.

        The agent can improve its playbook from measured results, but learned
        rules are stored as knowledge candidates so they can be reviewed before
        becoming permanent production policy.
        """
        memory_file = self.root / "memory" / "lessons_learned.jsonl"
        memory_file.parent.mkdir(exist_ok=True)
        record = {
            "domain": domain,
            "observation": observation,
        }
        with memory_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def review_video(self, result: dict[str, Any]) -> dict[str, Any]:
        score = 100
        lessons = []
        if result.get("retention", 100) < 50:
            score -= 20
            lessons.append("Improve first minute retention and story tension")
        if result.get("ctr", 100) < 5:
            score -= 15
            lessons.append("Improve title and thumbnail packaging")
        report = {"score": max(score, 0), "lessons": lessons}
        path = self.experience / "latest_review.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    def profile(self) -> dict[str, Any]:
        return {
            "role": "YouTube documentary producer",
            "learning_mode": "continuous_improvement",
            "experience_years": 10,
            "skills": [
                "storytelling",
                "audience psychology",
                "documentary editing",
                "monetization strategy",
                "niche_strategy",
                "youtube_packaging",
                "production_pipeline_optimization",
            ],
        }
