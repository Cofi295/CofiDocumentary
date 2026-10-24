from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Protocol


VALID_MATCH_LEVELS = {"FACTUAL_EXACT", "CONTEXTUAL_EXACT", "ATMOSPHERIC"}
VALID_EVIDENCE_STATUSES = {"CONFIRMED", "UNKNOWN", "CONTRADICTED"}


def _normalized_level(value: Any) -> str:
    level = str(value or "CONTEXTUAL_EXACT").strip().upper()
    return level if level in VALID_MATCH_LEVELS else "CONTEXTUAL_EXACT"


@dataclass(slots=True)
class MatchContract:
    level: str = "CONTEXTUAL_EXACT"
    required_fields: dict[str, str] = field(default_factory=dict)
    forbidden_substitutions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.level = _normalized_level(self.level)
        self.required_fields = {
            str(key).strip(): str(value).strip()
            for key, value in (self.required_fields or {}).items()
            if str(key).strip() and str(value).strip()
        }
        self.forbidden_substitutions = [
            str(value).strip()
            for value in (self.forbidden_substitutions or [])
            if str(value).strip()
        ]

    @classmethod
    def from_beat(cls, beat: dict[str, Any]) -> "MatchContract":
        explicit = beat.get("verification_requirements")
        requirements = dict(explicit) if isinstance(explicit, dict) else {}
        visual_description = str(beat.get("visual_description") or "").strip()
        if visual_description and "visual_context" not in requirements:
            requirements["visual_context"] = visual_description
        forbidden = beat.get("forbidden_substitutions")
        if not isinstance(forbidden, list):
            forbidden = []
        explicit_level = str(beat.get("verification_level") or "").strip()
        if explicit_level:
            level = explicit_level
        elif str(beat.get("source_priority") or "").strip().lower() == "must_real":
            level = "FACTUAL_EXACT"
        elif "atmospheric" in str(beat.get("visual_type") or "").strip().lower():
            level = "ATMOSPHERIC"
        else:
            level = "CONTEXTUAL_EXACT"
        return cls(
            level=level,
            required_fields=requirements,
            forbidden_substitutions=forbidden,
        )

    def as_prompt_payload(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "required_fields": self.required_fields,
            "forbidden_substitutions": self.forbidden_substitutions,
        }


class VisionProvider(Protocol):
    name: str

    def health(self) -> dict[str, Any]:
        ...

    def verify(
        self,
        *,
        voice_text: str,
        frames: list[str | Path],
        transcript: str = "",
        metadata: dict[str, Any] | None = None,
        contract: MatchContract | None = None,
    ) -> dict[str, Any]:
        ...


def _json_object_from_text(value: str) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError("Vision provider returned an empty response")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.I | re.S)
    candidates = [fenced.group(1)] if fenced else []
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start:end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise RuntimeError("Vision provider did not return a JSON object")


def _clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    return max(0.0, min(1.0, score))


def _normalize_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    raw_fields = payload.get("fields")
    if isinstance(raw_fields, dict):
        for key, value in raw_fields.items():
            item = value if isinstance(value, dict) else {}
            status = str(item.get("status") or "UNKNOWN").strip().upper()
            if status not in VALID_EVIDENCE_STATUSES:
                status = "UNKNOWN"
            fields[str(key)] = {
                "status": status,
                "evidence": str(item.get("evidence") or "").strip(),
            }
    forbidden = payload.get("forbidden_detected")
    if not isinstance(forbidden, list):
        forbidden = []
    return {
        **payload,
        "semantic_score": _clamp_score(payload.get("semantic_score")),
        "fields": fields,
        "forbidden_detected": [str(item).strip() for item in forbidden if str(item).strip()],
        "summary": str(payload.get("summary") or "").strip(),
    }


class EvidenceVerifier:
    def __init__(
        self,
        *,
        factual_accept_score: float = 0.88,
        contextual_accept_score: float = 0.80,
        atmospheric_accept_score: float = 0.68,
    ) -> None:
        self.accept_scores = {
            "FACTUAL_EXACT": float(factual_accept_score),
            "CONTEXTUAL_EXACT": float(contextual_accept_score),
            "ATMOSPHERIC": float(atmospheric_accept_score),
        }

    def decide(self, contract: MatchContract, evidence: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_evidence(evidence)
        field_results = normalized["fields"]
        contradicted: list[str] = []
        unknown: list[str] = []
        for field_name in contract.required_fields:
            status = str((field_results.get(field_name) or {}).get("status") or "UNKNOWN").upper()
            if status == "CONTRADICTED":
                contradicted.append(field_name)
            elif status != "CONFIRMED":
                unknown.append(field_name)

        forbidden = list(normalized.get("forbidden_detected") or [])
        score = float(normalized["semantic_score"])
        threshold = self.accept_scores[contract.level]
        if contradicted or forbidden:
            decision = "REJECT"
        elif unknown:
            decision = "REVIEW"
        elif score >= threshold:
            decision = "ACCEPT"
        else:
            decision = "REVIEW"
        return {
            **normalized,
            "decision": decision,
            "auto_accept": decision == "ACCEPT",
            "threshold": threshold,
            "unconfirmed_required_fields": unknown,
            "contradicted_required_fields": contradicted,
        }
