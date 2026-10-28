from __future__ import annotations

PHASES = ("plan", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc")

REQUIRED_ARTIFACTS = {
    "plan": ("research.md", "script.md", "visual_manifest.json"),
    "voice": ("voice_manifest.json", "subtitles.srt", "audio/narration.wav"),
    "visuals": ("visual_manifest.json", "visual_prompts.json"),
    "footage": ("footage_codex.json", "footage_gemini.json", "footage_review.json", "asset_registry.json"),
    "ai_visual": ("ai_visual_manifest.json", "asset_registry.json"),
    "edit": ("edit_session.json", "edit_checkpoint.json"),
    "seo": ("seo_package.json",),
    "qc": ("render_manifest.json", "director_report.md", "final_manifest.json"),
}


def effective_phases(job: dict[str, object] | None = None) -> tuple[str, ...]:
    strategy = str((job or {}).get("visual_strategy") or "full_footage").strip().lower()
    profile_id = str(
        (job or {}).get("channel_profile_id")
        or ((job or {}).get("channel_profile_snapshot") or {}).get("id")
        if isinstance((job or {}).get("channel_profile_snapshot"), dict)
        else (job or {}).get("channel_profile_id")
        or ""
    ).strip()
    if strategy == "footage_first":
        strategy = "full_footage"
    elif strategy in {"semi_content", "ban_content", "edit_footage"}:
        strategy = "edit_direct_footage"
    if strategy in {"full_ai", "edit_direct_footage"} or profile_id == "channel-cn-cyber-finance-kr":
        return tuple(phase for phase in PHASES if phase != "footage")
    if strategy == "full_footage":
        return tuple(phase for phase in PHASES if phase != "ai_visual")
    return PHASES


def phase_state() -> dict[str, object]:
    return {
        "status": "pending",
        "started_at": None,
        "finished_at": None,
        "error": None,
        "last_message": None,
    }
