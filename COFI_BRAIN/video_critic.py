"""Automated producer review rules for COFI videos."""

from __future__ import annotations


def critic_report(video: dict) -> dict:
    issues = []
    if video.get("hook_strength", 0) < 7:
        issues.append("Hook needs stronger curiosity gap")
    if video.get("visual_repetition", 0) > 30:
        issues.append("Reduce repeated visuals")
    if video.get("pacing", 10) < 7:
        issues.append("Improve pacing and scene changes")
    return {
        "score": max(0, 100 - len(issues) * 15),
        "issues": issues,
        "approved": not issues,
    }
