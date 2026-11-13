from __future__ import annotations

import os
import sys

if os.name == "nt":
    os.environ.setdefault("AGY_CLI_DISABLE_AUTO_UPDATE", "1")
    try:
        import ctypes
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    except Exception:
        pass
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        import subprocess as _sp
        if not getattr(_sp.Popen, "_cofi_no_console_guard", False):
            _orig_popen_init = _sp.Popen.__init__
            _NO_WIN = getattr(_sp, "CREATE_NO_WINDOW", 0x08000000)
            _NEW_CON = getattr(_sp, "CREATE_NEW_CONSOLE", 0x00000010)
            _DETACHED = getattr(_sp, "DETACHED_PROCESS", 0x00000008)

            def _silent_popen_init(self, *args, **kwargs):
                flags = int(kwargs.get("creationflags") or 0)
                flags = (flags & ~_NEW_CON & ~_DETACHED) | _NO_WIN
                kwargs["creationflags"] = flags
                return _orig_popen_init(self, *args, **kwargs)

            _sp.Popen.__init__ = _silent_popen_init  # type: ignore[method-assign]
            _sp.Popen._cofi_no_console_guard = True  # type: ignore[attr-defined]

import asyncio
import json
from queue import Empty, Queue
from pathlib import Path
from threading import Thread
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from documentary.service import DocumentaryService
from COFI_BRAIN.source_repair_agent import SourceRepairAgent

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
REPAIR_AGENT = SourceRepairAgent(str(ROOT))
REPAIR_AGENT.save_capabilities()
FALLBACK_POSTER_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" width="100%" height="100%">'
    b'<rect width="320" height="180" fill="#08131d"/>'
    b'<circle cx="160" cy="90" r="26" fill="#0e2337" stroke="#2a4d6f" stroke-width="1.5"/>'
    b'<polygon points="153,77 173,90 153,103" fill="#83dbf7"/>'
    b'</svg>'
)


class CreateJobRequest(BaseModel):
    title: str | None = None
    topic: str | None = None
    source_url: str | None = None
    market: str = "KR"
    language: str = "ko"
    notes: str = ""
    target_duration_minutes: float = Field(default=5, ge=2, le=180)
    plan_engine: str = "codex"
    footage_mode: str = "vision_codex"
    visual_strategy: str = "full_footage"
    ai_media_mode: str = "mixed"
    ai_visual: dict[str, Any] = Field(default_factory=dict)
    voice: dict[str, Any] = Field(default_factory=dict)
    production_recipe: dict[str, Any] = Field(default_factory=dict)
    topic_discovery: dict[str, Any] = Field(default_factory=dict)
    channel_profile_id: str | None = None
    channel_plan_item_id: int | None = None
    playbook_id: str | None = None
    creative_brief: dict[str, Any] = Field(default_factory=dict)
    narrative_angle: str | None = None
    writing_style: str | None = None
    hook_archetype: str | None = None
    editing_archetypes: list[str] | str | None = None
    opening_hook: str | None = None
    custom_rules: str | None = None
    outline: dict[str, Any] | list[dict[str, Any]] | None = None
    workspace_root: str | None = None
    seo_keyword_dna: dict[str, Any] | None = None
    thumbnail_dna: dict[str, Any] | None = None
    start_plan: bool = False
    run_plan: bool = False


class RadarImportRequest(BaseModel):
    scan_id: int
    video_id: str
    target_duration_minutes: float = Field(default=5, ge=2, le=180)
    plan_engine: str = "codex"
    visual_strategy: str = "full_footage"
    ai_media_mode: str = "mixed"
    ai_visual: dict[str, Any] = Field(default_factory=dict)
    language: str | None = None
    market: str | None = None
    notes: str = ""
    voice: dict[str, Any] = Field(default_factory=dict)
    channel_profile_id: str | None = None
    playbook_id: str | None = None
    creative_brief: dict[str, Any] = Field(default_factory=dict)
    outline: dict[str, Any] | list[dict[str, Any]] | None = None
    workspace_root: str | None = None


class CreativeBriefRequest(BaseModel):
    title: str | None = None
    playbook_id: str | None = None
    creative_brief: dict[str, Any] | None = None
    narrative_angle: str | None = None
    writing_style: str | None = None
    hook_archetype: str | None = None
    editing_archetypes: list[str] | str | None = None
    editing_grammar: list[str] | str | None = None
    opening_hook: str | None = None
    custom_rules: str | None = None
    notes: str | None = None


class OutlineUpdateRequest(BaseModel):
    outline: dict[str, Any] | list[dict[str, Any]] | None = None
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    opening_hook: str | None = None
    thesis: str | None = None


class OutlineGenerateRequest(BaseModel):
    creative_brief: dict[str, Any] | None = None
    notes: str | None = None
    instruction: str | None = None
    chapter_count: int | None = None


class ScriptUpdateRequest(BaseModel):
    script: str | None = None
    research: str | None = None


class SmartCacheCleanRequest(BaseModel):
    mode: str = "safe_ephemeral"
    selected_job_id: str | None = None
    target_job_ids: list[str] | None = None
    include_tier1: bool = True
    reclaim_ram: bool = True
    dry_run: bool = False


class PlaybookRequest(BaseModel):
    id: str | None = None
    name: str
    description: str = ""
    market: str = "KR"
    language: str = "ko"
    visual_strategy: str = "hybrid"
    ai_media_mode: str = "mixed"
    creative_brief: dict[str, Any] = Field(default_factory=dict)


class ExtractPlaybookRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    custom_rules: str | None = None


class PitchAnglesRequest(BaseModel):
    topic: str | None = None
    title: str | None = None
    market: str = "KR"
    language: str = "ko"
    notes: str = ""
    channel_profile_id: str | None = None


class VoiceSettingsRequest(BaseModel):
    voice_id: str | None = None
    speed: float = Field(default=1.0, ge=0.8, le=1.2)
    mode: str = "balanced"


class VoiceDesignRequest(BaseModel):
    name: str
    language: str = "vi"
    instruct: str
    auto_preview: bool = True


class VoiceTtsPreviewRequest(BaseModel):
    text: str
    voice_id: str | None = None
    language: str | None = None
    speed: float = Field(default=1.0, ge=0.7, le=1.5)
    mode: str = "balanced"


class AIVisualSettingsRequest(BaseModel):
    task_type: str | None = None
    model: str | None = None
    image_model: str | None = None
    video_model: str | None = None
    aspect_ratio: str | None = None
    veo_enabled: bool | None = None
    style_mode: str | None = None
    style_preset: str | None = None
    custom_style: str | None = None
    ai_media_mode: str | None = None
    coverage_mode: str | None = None
    reference_image_name: str | None = None
    reference_image_data_url: str | None = None
    clear_style_reference: bool | None = None


class ProductionSettingsRequest(BaseModel):
    visual_strategy: str | None = None
    ai_media_mode: str | None = None


class AIAccountSettingsRequest(BaseModel):
    model: str | None = None


class ChatProviderRequest(BaseModel):
    provider: str


class EditChatRequest(BaseModel):
    message: str = ""
    selected_beat_id: str | None = None
    selected_timestamp_sec: float | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=4)


class ProducerChatRequest(BaseModel):
    message: str = ""
    selected_job_id: str | None = None
    app_tab: str | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=4)
    goal_mode: bool = False
    model: str | None = None
    provider: str | None = None


class RadarMarketScanRequest(BaseModel):
    market: str = "KR"
    seeds: list[str] = Field(default_factory=list)
    days: int = Field(default=7, ge=1, le=365)
    max_videos: int = Field(default=60, ge=10, le=500)
    max_channel_subscribers: int = Field(default=100_000, ge=100, le=10_000_000)
    max_channel_age_days: int = Field(default=90, ge=1, le=3650)
    min_proof_channels: int = Field(default=3, ge=1, le=10)
    min_breakout_videos: int = Field(default=4, ge=1, le=20)
    niche_granularity: str = "micro"
    content_type: str = "factual_documentary"
    production_mode: str | None = None


class RadarChannelScanRequest(BaseModel):
    channel_ref: str
    label: str | None = None
    content_type: str = "factual_documentary"


class RadarChannelDiscoveryRequest(BaseModel):
    channel_id: str
    market: str = "KR"
    days: int = Field(default=30, ge=1, le=365)
    max_videos: int = Field(default=80, ge=10, le=500)


class RadarTranslateRequest(BaseModel):
    texts: list[str] = Field(default_factory=list, max_length=80)


class RadarSaveNicheRequest(BaseModel):
    note: str | None = None


class ChannelProfileRequest(BaseModel):
    label: str | None = None
    own_channel_ref: str = ""
    competitor_refs: list[str] = Field(default_factory=list)
    market: str = "KR"
    default_language: str | None = None
    default_duration_minutes: float | None = Field(default=None, ge=2, le=180)
    default_visual_strategy: str | None = None
    default_ai_media_mode: str | None = None
    default_ai_style_mode: str | None = None
    default_ai_custom_style: str | None = None
    dna_mode: str | None = None
    voice_and_structure: str | None = None
    allowed_topics: str | None = None
    forbidden_topics: str | None = None
    monetization_safety_policy: str | None = None
    reference_image_policy: str | None = None
    default_creative_brief: dict[str, Any] | None = None
    editorial_dna: dict[str, Any] | None = None
    editing_dna: dict[str, Any] | None = None
    self_learning_memory: dict[str, Any] | None = None
    seo_keyword_dna: dict[str, Any] | None = None
    thumbnail_dna: dict[str, Any] | None = None


class ChannelPlanStatusRequest(BaseModel):
    status: str


class ParallelDispatchRequest(BaseModel):
    dept_id: str | list[str] | None = "all"
    department_id: str | None = None
    agent_id: str | None = None
    job_id: str | None = None
    selected_job_id: str | None = None
    specialist_id: str | None = None


_PARALLEL_RUNTIME_CACHE: dict[str, dict[str, Any]] = {}


LIVE_PARALLEL_STUDIO_STAGE_CSS = r"""
/* ============================================================================
 * SÂN KHẤU 15 PHÒNG BAN — CHIA LÔ CHẠY SONG SONG (LIVE PARALLEL STUDIO STAGE)
 * ============================================================================ */
.ao-parallel-stage-mount {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 14px;
  position: relative;
  z-index: 3;
}
.ao-floorplan-wrap.is-chibi-mode .ao-parallel-stage-mount {
  display: none !important;
}
.ao-parallel-command-bar {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.96) 0%, rgba(8, 28, 48, 0.96) 55%, rgba(19, 28, 46, 0.98) 100%);
  border: 1px solid rgba(56, 189, 248, 0.42);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 12px 32px rgba(2, 6, 23, 0.55), inset 0 1px 0 rgba(125, 211, 252, 0.22);
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
  overflow: hidden;
}
.ao-parallel-command-bar::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 85% 20%, rgba(56, 189, 248, 0.14), transparent 55%),
              radial-gradient(circle at 15% 80%, rgba(16, 185, 129, 0.12), transparent 50%);
  pointer-events: none;
}
.ao-parallel-cmd-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
  position: relative;
  z-index: 1;
}
.ao-parallel-cmd-title-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 280px;
  flex: 1;
}
.ao-parallel-cmd-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ao-parallel-mode-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #022c22;
  background: linear-gradient(90deg, #34d399 0%, #38bdf8 100%);
  box-shadow: 0 0 14px rgba(52, 211, 153, 0.45);
}
.ao-parallel-speedup-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: #fde68a;
  background: rgba(245, 158, 11, 0.16);
  border: 1px solid rgba(251, 191, 36, 0.45);
}
.ao-parallel-cmd-title-group h4 {
  margin: 0;
  font-size: 15.5px;
  font-weight: 800;
  color: #f8fafc;
  letter-spacing: -0.01em;
}
.ao-parallel-cmd-title-group p {
  margin: 0;
  font-size: 12px;
  color: #cbd5e1;
  line-height: 1.45;
}
.ao-parallel-kpi-pills {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 2px;
}
.ao-parallel-kpi-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 11.5px;
  color: #e2e8f0;
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.25);
}
.ao-parallel-kpi-chip strong {
  color: #38bdf8;
  font-family: 'JetBrains Mono', monospace;
}
.ao-parallel-cmd-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  position: relative;
  z-index: 1;
}
.ao-parallel-cta-all-btn {
  cursor: pointer;
  border: 1px solid rgba(250, 204, 21, 0.75);
  background: linear-gradient(135deg, #f59e0b 0%, #ea580c 55%, #0284c7 100%);
  color: #fff;
  font-weight: 800;
  font-size: 12.5px;
  padding: 10px 16px;
  border-radius: 11px;
  box-shadow: 0 6px 20px rgba(245, 158, 11, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.35);
  transition: transform 0.15s ease, box-shadow 0.2s ease, filter 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.45);
}
.ao-parallel-cta-all-btn:hover {
  transform: translateY(-1px);
  filter: brightness(1.08);
  box-shadow: 0 10px 26px rgba(245, 158, 11, 0.52);
}
.ao-parallel-cta-all-btn:active {
  transform: translateY(0);
}
.ao-parallel-cta-all-btn.is-dispatching {
  background: linear-gradient(135deg, #10b981 0%, #0284c7 100%);
  border-color: #6ee7b7;
  animation: aoParallelPulseGlow 0.9s infinite alternate;
}
.ao-parallel-subview-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(2, 6, 23, 0.72);
  padding: 4px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  flex-wrap: wrap;
}
.ao-parallel-mode-btn {
  cursor: pointer;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 11.5px;
  font-weight: 700;
  padding: 6px 11px;
  border-radius: 7px;
  transition: all 0.15s ease;
}
.ao-parallel-mode-btn:hover {
  color: #f8fafc;
  background: rgba(56, 189, 248, 0.12);
}
.ao-parallel-mode-btn.active {
  color: #0f172a;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  box-shadow: 0 2px 10px rgba(56, 189, 248, 0.35);
}

/* 2.5D Interactive Studio Floorplan (15 Studio Pods across 5 Pipeline Zones) */
.ao-parallel-25d-floorplan {
  background: radial-gradient(ellipse at top, rgba(14, 116, 144, 0.18), rgba(7, 18, 32, 0.96) 70%);
  border: 1px solid rgba(56, 189, 248, 0.32);
  border-radius: 14px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: relative;
  overflow: hidden;
}
.ao-parallel-25d-floorplan.is-wave-running {
  border-color: rgba(52, 211, 153, 0.82);
  box-shadow: 0 0 32px rgba(16, 185, 129, 0.28), inset 0 0 24px rgba(56, 189, 248, 0.16);
}
.ao-floorplan-25d-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}
.ao-floorplan-25d-header strong {
  color: #f8fafc;
  font-size: 13.5px;
}
.ao-floorplan-25d-legend {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 11px;
  color: #cbd5e1;
}
.ao-stage-zones-stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.ao-stage-zone {
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 12px;
  padding: 12px;
  position: relative;
}
.ao-stage-zone.zone-parallel-visual {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.92) 0%, rgba(30, 27, 75, 0.65) 50%, rgba(6, 78, 59, 0.45) 100%);
  border: 1.5px solid rgba(56, 189, 248, 0.55);
  box-shadow: 0 8px 26px rgba(14, 165, 233, 0.16);
}
.ao-stage-zone-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.ao-stage-zone-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 800;
  color: #f1f5f9;
}
.ao-stage-zone-badge {
  font-size: 10.5px;
  font-family: 'JetBrains Mono', monospace;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.15);
  color: #7dd3fc;
  border: 1px solid rgba(56, 189, 248, 0.35);
}
.ao-stage-pods-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(265px, 1fr));
  gap: 11px;
}

/* Special Visual Parallel Tri-Stream Hub (@visuals -> [@footage || @vox || @ai_visual]) */
.ao-visual-tri-hub {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ao-visual-tri-splitter-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  padding: 8px 12px;
  border-radius: 10px;
  background: rgba(2, 132, 199, 0.16);
  border: 1px dashed rgba(56, 189, 248, 0.55);
  font-size: 11.5px;
  color: #e0f2fe;
}
.ao-visual-tri-branches {
  display: grid;
  grid-template-columns: repeat(3, minmax(240px, 1fr));
  gap: 12px;
  position: relative;
}
@media (max-width: 1180px) {
  .ao-visual-tri-branches {
    grid-template-columns: 1fr;
  }
}
.ao-tri-branch-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
}
.ao-tri-branch-tag {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  background: rgba(15, 23, 42, 0.88);
  border: 1px solid rgba(56, 189, 248, 0.42);
  color: #7dd3fc;
}

/* Studio Pod (Each of the 15 Department Desks on the 2.5D Stage) */
.ao-studio-pod {
  background: linear-gradient(165deg, rgba(15, 23, 42, 0.95) 0%, rgba(9, 16, 29, 0.96) 100%);
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-top: 3px solid var(--pod-accent, #38bdf8);
  border-radius: 12px;
  padding: 11px 12px;
  display: flex;
  flex-direction: column;
  gap: 9px;
  cursor: pointer;
  transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.2s ease;
  position: relative;
  overflow: hidden;
}
.ao-studio-pod:hover {
  transform: translateY(-2px);
  border-color: var(--pod-accent, #38bdf8);
  box-shadow: 0 10px 24px rgba(2, 6, 23, 0.65), 0 0 16px rgba(56, 189, 248, 0.22);
}
.ao-studio-pod.is-selected-pod {
  border-color: #38bdf8;
  box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.42), 0 12px 28px rgba(2, 6, 23, 0.72);
}
.ao-studio-pod.pod-vox-flagship {
  background: linear-gradient(165deg, rgba(23, 37, 84, 0.88) 0%, rgba(15, 23, 42, 0.96) 100%);
  border-color: rgba(250, 204, 21, 0.55);
}
.ao-studio-pod-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.ao-studio-pod-id {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}
.ao-studio-pod-emoji {
  font-size: 18px;
  line-height: 1;
}
.ao-studio-pod-titles {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.ao-studio-pod-code-line {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}
.ao-studio-pod-code {
  font-size: 10px;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  padding: 1px 6px;
  border-radius: 5px;
  background: rgba(56, 189, 248, 0.16);
  color: #7dd3fc;
}
.ao-studio-pod-speed {
  font-size: 10px;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  padding: 1px 6px;
  border-radius: 5px;
  background: rgba(16, 185, 129, 0.18);
  color: #6ee7b7;
}
.ao-studio-pod-titles strong {
  font-size: 12px;
  color: #f8fafc;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ao-pod-run-btn {
  cursor: pointer;
  border: 1px solid rgba(56, 189, 248, 0.48);
  background: rgba(14, 116, 144, 0.28);
  color: #e0f2fe;
  font-size: 10.5px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 7px;
  white-space: nowrap;
  transition: all 0.15s ease;
}
.ao-pod-run-btn:hover {
  background: #0284c7;
  color: #fff;
  border-color: #7dd3fc;
}

/* Pod Command Row: Lead (👑) + Deputy (🛡️) */
.ao-pod-commanders {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}
.ao-pod-commander-btn {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 7px;
  border-radius: 7px;
  background: rgba(30, 41, 59, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.2);
  color: #e2e8f0;
  font-size: 10.5px;
  text-align: left;
  overflow: hidden;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.ao-pod-commander-btn:hover {
  border-color: #facc15;
  background: rgba(250, 204, 21, 0.12);
}
.ao-pod-commander-btn code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #93c5fd;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Animated Handoff Beam between Lead -> Parallel Specialist Lanes -> Deputy */
.ao-handoff-beam {
  height: 3px;
  width: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.15), rgba(52, 211, 153, 0.9), rgba(250, 204, 21, 0.85), rgba(56, 189, 248, 0.15));
  background-size: 200% 100%;
  animation: aoHandoffBeamFlow 2.1s linear infinite;
}
@keyframes aoHandoffBeamFlow {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
@keyframes aoParallelPulseGlow {
  0% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.35); }
  100% { box-shadow: 0 0 24px rgba(56, 189, 248, 0.75); }
}

/* Pod Parallel Specialist Lanes (⚡ Lô #1..#N running simultaneously) */
.ao-pod-lanes-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.ao-pod-lane-chip {
  cursor: pointer;
  display: flex;
   flex-direction: column;
  gap: 3px;
  padding: 5px 7px;
  border-radius: 7px;
  background: rgba(2, 6, 23, 0.68);
  border: 1px solid rgba(56, 189, 248, 0.22);
  transition: all 0.14s ease;
}
.ao-pod-lane-chip:hover {
  border-color: #38bdf8;
  background: rgba(14, 116, 144, 0.22);
}
.ao-pod-lane-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 10.5px;
}
.ao-pod-lane-id {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 700;
  color: #f8fafc;
  min-width: 0;
}
.ao-pod-lane-id code {
  color: #67e8f9;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ao-pod-lane-items {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9.5px;
  color: #fde68a;
  background: rgba(245, 158, 11, 0.14);
  padding: 1px 5px;
  border-radius: 4px;
  white-space: nowrap;
}
.ao-pod-lane-bar {
  height: 4px;
  border-radius: 999px;
  background: rgba(51, 65, 85, 0.7);
  overflow: hidden;
}
.ao-pod-lane-bar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #38bdf8, #34d399);
  transition: width 0.35s ease;
}

/* Parallel Lanes Matrix (Bảng Phân Lô Song Song Chi Tiết) */
.ao-parallel-lanes-matrix {
  background: linear-gradient(160deg, rgba(15, 23, 42, 0.96) 0%, rgba(7, 15, 28, 0.98) 100%);
  border: 1px solid rgba(52, 211, 153, 0.38);
  border-radius: 14px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 10px 28px rgba(2, 6, 23, 0.5);
}
.ao-matrix-dept-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}
.ao-matrix-dept-tab {
  cursor: pointer;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(15, 23, 42, 0.8);
  color: #cbd5e1;
  font-size: 11px;
  font-weight: 700;
  padding: 5px 9px;
  border-radius: 8px;
  transition: all 0.14s ease;
}
.ao-matrix-dept-tab:hover {
  border-color: #38bdf8;
  color: #fff;
}
.ao-matrix-dept-tab.active {
  background: linear-gradient(90deg, rgba(14, 165, 233, 0.32), rgba(16, 185, 129, 0.28));
  border-color: #38bdf8;
  color: #fff;
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.3);
}
.ao-matrix-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.ao-matrix-head-info h4 {
  margin: 0 0 4px;
  font-size: 14.5px;
  color: #f8fafc;
}
.ao-matrix-head-info p {
  margin: 0;
  font-size: 11.5px;
  color: #94a3b8;
}
.ao-matrix-tracks-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ao-matrix-lane-row {
  display: grid;
  grid-template-columns: 120px minmax(210px, 1.2fr) minmax(220px, 1.5fr) 170px 150px 185px;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(2, 6, 23, 0.72);
  border: 1px solid rgba(56, 189, 248, 0.24);
  border-left: 4px solid #34d399;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.ao-matrix-lane-row:hover {
  border-color: #38bdf8;
  background: rgba(15, 23, 42, 0.92);
}
@media (max-width: 1240px) {
  .ao-matrix-lane-row {
    grid-template-columns: 1fr;
  }
}
.ao-lane-badge-col {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.ao-lane-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 800;
  color: #6ee7b7;
}
.ao-lane-batch-tag {
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  padding: 2px 7px;
  border-radius: 5px;
  background: rgba(56, 189, 248, 0.16);
  color: #7dd3fc;
  width: fit-content;
}
.ao-lane-who-col strong {
  display: block;
  font-size: 12px;
  color: #f8fafc;
}
.ao-lane-who-col code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #38bdf8;
}
.ao-lane-duty-col {
  font-size: 11.5px;
  color: #cbd5e1;
  line-height: 1.4;
}
.ao-lane-duty-col small {
  display: block;
  color: #94a3b8;
  margin-top: 2px;
}
.ao-lane-scope-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ao-lane-items-pill {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  font-weight: 700;
  color: #fde68a;
  background: rgba(245, 158, 11, 0.14);
  border: 1px solid rgba(251, 191, 36, 0.35);
  padding: 3px 7px;
  border-radius: 6px;
}
.ao-lane-thread-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #94a3b8;
}
.ao-lane-prog-col {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.ao-lane-prog-head {
  display: flex;
  justify-content: space-between;
  font-size: 10.5px;
  font-family: 'JetBrains Mono', monospace;
  color: #6ee7b7;
}
.ao-lane-actions-col {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.ao-lane-act-btn {
  cursor: pointer;
  border: 1px solid rgba(56, 189, 248, 0.38);
  background: rgba(14, 116, 144, 0.24);
  color: #e0f2fe;
  font-size: 10.5px;
  font-weight: 700;
  padding: 5px 8px;
  border-radius: 7px;
  transition: all 0.14s ease;
}
.ao-lane-act-btn:hover {
  background: #0284c7;
  color: #fff;
}
.ao-lane-act-btn.primary {
  background: rgba(16, 185, 129, 0.24);
  border-color: rgba(52, 211, 153, 0.52);
  color: #d1fae5;
}
.ao-lane-act-btn.primary:hover {
  background: #059669;
  color: #fff;
}

/* Specialist Live Monitor Modal / Drawer (Màn Hình Giám Sát Chuyên Viên) */
.ao-spec-monitor-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.76);
  backdrop-filter: blur(5px);
  z-index: 99999;
  display: none;
  align-items: center;
  justify-content: flex-end;
}
.ao-spec-monitor-backdrop.is-open {
  display: flex;
}
.ao-spec-monitor-panel {
  width: min(640px, 95vw);
  height: 100vh;
  background: linear-gradient(165deg, #0b1528 0%, #07101e 100%);
  border-left: 1px solid rgba(56, 189, 248, 0.45);
  box-shadow: -16px 0 48px rgba(0, 0, 0, 0.75);
  display: flex;
  flex-direction: column;
  color: #f8fafc;
  overflow: hidden;
}
.ao-spec-monitor-head {
  padding: 16px 18px;
  background: rgba(15, 23, 42, 0.92);
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.ao-spec-monitor-body {
  padding: 16px 18px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;
}
.ao-spec-monitor-section {
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 11px;
  padding: 12px 14px;
}
.ao-spec-monitor-section h5 {
  margin: 0 0 8px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #7dd3fc;
}
.ao-spec-monitor-kv-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
.ao-spec-monitor-kv {
  background: rgba(2, 6, 23, 0.65);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 8px;
  padding: 8px 10px;
}
.ao-spec-monitor-kv span {
  display: block;
  font-size: 10.5px;
  color: #94a3b8;
}
.ao-spec-monitor-kv strong {
  font-size: 12px;
  color: #f8fafc;
  font-family: 'JetBrains Mono', monospace;
}
.ao-spec-monitor-cmd-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ao-spec-monitor-cmd-input {
  width: 100%;
  background: rgba(2, 6, 23, 0.88);
  border: 1px solid rgba(56, 189, 248, 0.42);
  border-radius: 8px;
  padding: 9px 11px;
  color: #f8fafc;
  font-size: 12px;
}
"""


LIVE_PARALLEL_STUDIO_STAGE_JS = r"""
(function () {
  if (window.__COFI_LIVE_PARALLEL_STAGE_BOOTED__) return;
  window.__COFI_LIVE_PARALLEL_STAGE_BOOTED__ = true;

  const PARALLEL_STAGE_ZONES = [
    {
      id: "zone_command",
      titleVi: "1. Khu Chỉ Huy & Chiến Lược (Command & Strategy Zone)",
      badgeVi: "DEPT-00 · DEPT-01 · Định hướng & Khóa DNA",
      agents: ["orchestrator", "radar"],
      isParallelVisualHub: false,
    },
    {
      id: "zone_preprod",
      titleVi: "2. Khu Tiền Kỳ & Kịch Bản (Pre-Production & Narrative Zone)",
      badgeVi: "DEPT-02 ➔ DEPT-03 ➔ DEPT-04 · Hồ sơ · Kịch bản · Voice SRT",
      agents: ["research", "script", "voice"],
      isParallelVisualHub: false,
    },
    {
      id: "zone_parallel_visual",
      titleVi: "3. Khu Sản Xuất Hình Ảnh Song Song [Footage ∥ VOX ∥ AI Visual]",
      badgeVi: "⚡ @visuals chia lô ➔ 3 Phim trường (@footage ∥ @vox ∥ @ai_visual) chạy ĐỒNG THỜI",
      agents: ["visuals", "footage", "vox", "ai_visual"],
      isParallelVisualHub: true,
    },
    {
      id: "zone_post_seo",
      titleVi: "4. Khu Hậu Kỳ & Đóng Gói Xuất Bản (Post-Production & SEO Zone)",
      badgeVi: "DEPT-09 @edit ∥ DEPT-10 @seo · Dựng Remotion & Đóng gói CTR",
      agents: ["edit", "seo"],
      isParallelVisualHub: false,
    },
    {
      id: "zone_qa_tech",
      titleVi: "5. Khu Kiểm Định Pháp Y & Kỹ Thuật (Forensic QA & Engineering Zone)",
      badgeVi: "DEPT-11..14 · @evidence_qa · @qc · @dev · @debug",
      agents: ["evidence_qa", "qc", "dev", "debug"],
      isParallelVisualHub: false,
    },
  ];

  const parallelUiState = {
    subView: "both", // "both" | "stage_25d" | "parallel_matrix"
    selectedDeptId: "vox",
    isDispatchingWave: false,
    lastWaveAt: "",
    departments: [],
    summary: {},
    selectedJobId: "",
    monitorTarget: null, // { deptId, memberId, rank }
    lastRenderSig: "",
  };

  function escHtml(v) {
    return String(v == null ? "" : v)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function ensureParallelStylesInjected() {
    if (document.getElementById("cofiParallelStageStyle")) return;
    const st = document.createElement("style");
    st.id = "cofiParallelStageStyle";
    st.textContent = window.__COFI_PARALLEL_STAGE_CSS_TEXT__ || "";
    document.head.appendChild(st);
  }

  function getActiveJobId() {
    if (window.__cofiAgentOfficeActiveJobId) return String(window.__cofiAgentOfficeActiveJobId);
    const sel = document.getElementById("agentOfficeJobSelect");
    if (sel && sel.value) return sel.value;
    const gsel = document.getElementById("globalProjectSelect");
    if (gsel && gsel.value) return gsel.value;
    return parallelUiState.selectedJobId || "";
  }

  function normalizeDepartmentParallel(dept) {
    if (!dept || typeof dept !== "object") return dept;
    const specs = Array.isArray(dept.specialists) ? dept.specialists : [];
    const nSpec = Math.max(1, specs.length);
    const pe = dept.parallel_engine && typeof dept.parallel_engine === "object" ? dept.parallel_engine : {};
    const rawBatches = Array.isArray(pe.batches) ? pe.batches : Array.isArray(dept.batches) ? dept.batches : [];
    const batchBySpec = {};
    rawBatches.forEach((b) => {
      if (b && b.specialist_id) batchBySpec[b.specialist_id] = b;
    });

    const totalBeats = 164;
    const normBatches = specs.map((sp, idx) => {
      const lane = Number(sp.parallel_lane || idx + 1);
      const batchId = sp.batch_id || `LÔ-0${lane}`;
      const sb = batchBySpec[sp.id] || {};
      const startB = Math.floor((idx * totalBeats) / nSpec) + 1;
      const endB = Math.max(startB, Math.floor(((idx + 1) * totalBeats) / nSpec));
      const defaultItems = `B${String(startB).padStart(3, "0")}–B${String(endB).padStart(3, "0")}`;
      const itemsLabel = sb.items_label || sp.items_label || defaultItems;
      const status = sb.status || sp.live_status || (dept.department_state === "done" ? "completed_verified" : "parallel_active");
      const pct = Number(
        sb.progress_pct != null
          ? sb.progress_pct
          : sp.progress_pct != null
          ? sp.progress_pct
          : status === "completed_verified"
          ? 100
          : 85
      );
      const workerThread = sb.worker_thread || sp.worker_thread || `pool-${dept.agent_id}-w0${lane}`;
      const elapsedMs = Number(sb.elapsed_ms || sp.elapsed_ms || (18 + lane * 6));
      const scopeVi = sb.batch_scope_vi || sp.batch_scope_vi || `Phân lô song song #${lane}/${nSpec} (${itemsLabel})`;
      const actionVi = sb.current_action_vi || sb.finding_vi || sp.current_action_vi || sp.task_detail_vi || sp.role_vi || "";

      sp.parallel_lane = lane;
      sp.batch_id = batchId;
      sp.batch_scope_vi = scopeVi;
      sp.items_label = itemsLabel;
      sp.live_status = status;
      sp.progress_pct = pct;
      sp.current_action_vi = actionVi;
      sp.worker_thread = workerThread;
      sp.elapsed_ms = elapsedMs;

      return {
        batch_id: batchId,
        parallel_lane: lane,
        specialist_id: sp.id,
        specialist_handle: sp.handle,
        specialist_name_vi: sp.title_vi,
        duty_vi: sp.role_vi || sp.task_detail_vi || "",
        batch_scope_vi: scopeVi,
        items_label: itemsLabel,
        status: status,
        progress_pct: pct,
        worker_thread: workerThread,
        elapsed_ms: elapsedMs,
        finding_vi: actionVi,
        current_action_vi: actionVi,
        artifact_key: sp.artifact_key || "artifact.json",
        input_from: sp.input_from || (dept.lead && dept.lead.handle) || "@lead",
        output_to: sp.output_to || (dept.deputy && dept.deputy.handle) || "@deputy",
      };
    });

    dept.parallel_engine = {
      enabled: true,
      mode: pe.mode || "parallel_specialist_pool",
      concurrency: Number(pe.concurrency || nSpec),
      active_workers: Number(pe.active_workers || nSpec),
      speedup_factor: pe.speedup_factor || (nSpec >= 6 ? "4.5x" : "4.2x"),
      pipeline_state: pe.pipeline_state || (dept.department_state === "done" ? "completed_verified" : "parallel_running"),
      parallel_architecture_vi:
        pe.parallel_architecture_vi ||
        `👑 Tổ trưởng chia ${nSpec} lô độc lập ➔ ⚡ ${nSpec} Chuyên viên chạy song song cùng lúc (Parallel Worker Pool) ➔ 🛡️ Tổ phó đối chiếu checklist & hợp nhất`,
      deputy_verification: pe.deputy_verification || null,
      lead_signoff: pe.lead_signoff || null,
      batches: normBatches,
    };
    return dept;
  }

  function renderStudioPodHtml(dept) {
    if (!dept) return "";
    normalizeDepartmentParallel(dept);
    const pe = dept.parallel_engine || {};
    const batches = Array.isArray(pe.batches) ? pe.batches : [];
    const lead = dept.lead || {};
    const deputy = dept.deputy || {};
    const isSel = parallelUiState.selectedDeptId === dept.agent_id;
    const isVox = dept.agent_id === "vox";

    const lanesHtml = batches
      .map((b) => {
        const shortRange = String(b.items_label || "B001–B041").split("(")[0].trim();
        const pct = Math.max(12, Math.min(100, Number(b.progress_pct || 100)));
        return `
          <div class="ao-pod-lane-chip" data-ao-open-spec-monitor="${escHtml(dept.agent_id)}:${escHtml(b.specialist_id)}" title="Bấm để mở Màn Hình Giám Sát Chuyên Viên ${escHtml(b.specialist_handle)} (${escHtml(b.batch_id)} · ${escHtml(b.items_label)})">
            <div class="ao-pod-lane-top">
              <span class="ao-pod-lane-id">⚡ ${escHtml(b.batch_id)} <code>${escHtml(b.specialist_handle)}</code></span>
              <span class="ao-pod-lane-items">${escHtml(shortRange)}</span>
            </div>
            <div class="ao-pod-lane-bar">
              <div class="ao-pod-lane-bar-fill" style="width:${pct}%;"></div>
            </div>
          </div>
        `;
      })
      .join("");

    return `
      <article class="ao-studio-pod${isSel ? " is-selected-pod" : ""}${isVox ? " pod-vox-flagship" : ""}" data-ao-select-parallel-dept="${escHtml(dept.agent_id)}" style="--pod-accent:${escHtml(dept.color || "#38bdf8")};">
        <div class="ao-studio-pod-head">
          <div class="ao-studio-pod-id">
            <span class="ao-studio-pod-emoji">${escHtml(dept.emoji || "🏛️")}</span>
            <div class="ao-studio-pod-titles">
              <div class="ao-studio-pod-code-line">
                <span class="ao-studio-pod-code">${escHtml(dept.code || "DEPT")}</span>
                <span class="ao-studio-pod-speed">⚡ ${escHtml(pe.speedup_factor || "4.2x")} · ${batches.length} Lô</span>
              </div>
              <strong title="${escHtml(dept.name_vi)}">${escHtml(dept.handle || `@${dept.agent_id}`)} · ${escHtml(dept.name_vi)}</strong>
            </div>
          </div>
          <button type="button" class="ao-pod-run-btn" data-ao-dispatch-parallel-dept="${escHtml(dept.agent_id)}" title="Kích hoạt chạy chia lô song song toàn bộ ${batches.length} chuyên viên của phòng ${escHtml(dept.handle)}">⚡ Chạy Chia Lô Phòng Này</button>
        </div>

        <div class="ao-pod-commanders">
          <button type="button" class="ao-pod-commander-btn" data-ao-open-spec-monitor="${escHtml(dept.agent_id)}:lead" title="Tổ trưởng ${escHtml(lead.title_vi || "")} — Bấm xem giám sát & giao việc">
            <span>👑</span>
            <code>${escHtml(lead.handle || `@${dept.agent_id}_lead`)}</code>
          </button>
          <button type="button" class="ao-pod-commander-btn" data-ao-open-spec-monitor="${escHtml(dept.agent_id)}:deputy" title="Tổ phó ${escHtml(deputy.title_vi || "")} — Bấm xem checklist nghiệm thu">
            <span>🛡️</span>
            <code>${escHtml(deputy.handle || `@${dept.agent_id}_deputy`)}</code>
          </button>
        </div>

        <div class="ao-handoff-beam" title="Tia dẫn truyền phân lô song song (Handoff Beam)"></div>

        <div class="ao-pod-lanes-list">
          ${lanesHtml}
        </div>
      </article>
    `;
  }

  function renderParallelLanesMatrixHtml(depts) {
    if (!Array.isArray(depts) || !depts.length) return "";
    const selectedDept = depts.find((d) => d.agent_id === parallelUiState.selectedDeptId) || depts.find((d) => d.agent_id === "vox") || depts[0];
    normalizeDepartmentParallel(selectedDept);
    const pe = selectedDept.parallel_engine || {};
    const batches = Array.isArray(pe.batches) ? pe.batches : [];
    const lead = selectedDept.lead || {};
    const deputy = selectedDept.deputy || {};

    const tabsHtml = depts
      .map((d) => {
        const activeCls = d.agent_id === selectedDept.agent_id ? " active" : "";
        const nSpec = Array.isArray(d.specialists) ? d.specialists.length : 4;
        return `<button type="button" class="ao-matrix-dept-tab${activeCls}" data-ao-select-parallel-dept="${escHtml(d.agent_id)}">${escHtml(d.emoji || "🏛️")} ${escHtml(d.code)} ${escHtml(d.handle)} (${nSpec} Lô)</button>`;
      })
      .join("");

    const lanesRowsHtml = batches
      .map((b) => {
        const pct = Math.max(0, Math.min(100, Number(b.progress_pct != null ? b.progress_pct : 100)));
        const stBadge =
          b.status === "completed_verified"
            ? "✅ ĐÃ XÁC MINH LÔ"
            : b.status === "parallel_active" || b.status === "parallel_running"
            ? "🟢 CHẠY SONG SONG"
            : "⚡ SẴN SÀNG LÔ";
        return `
          <div class="ao-matrix-lane-row" data-ao-lane="${escHtml(b.parallel_lane)}">
            <div class="ao-lane-badge-col">
              <span class="ao-lane-pill">⚡ LANE #${escHtml(b.parallel_lane)}</span>
              <span class="ao-lane-batch-tag">${escHtml(b.batch_id)}</span>
            </div>
            <div class="ao-lane-who-col">
              <strong>${escHtml(b.specialist_name_vi)}</strong>
              <code>${escHtml(b.specialist_handle)}</code>
            </div>
            <div class="ao-lane-duty-col">
              <div><strong>Nhiệm vụ:</strong> ${escHtml(b.duty_vi)}</div>
              <small>📌 ${escHtml(b.batch_scope_vi)}</small>
            </div>
            <div class="ao-lane-scope-col">
              <span class="ao-lane-items-pill">🎯 ${escHtml(b.items_label)}</span>
              <span class="ao-lane-thread-tag">🧵 ${escHtml(b.worker_thread)} · ${Number(b.elapsed_ms || 12).toFixed(1)}ms</span>
            </div>
            <div class="ao-lane-prog-col">
              <div class="ao-lane-prog-head">
                <span>${stBadge}</span>
                <strong>${pct}%</strong>
              </div>
              <div class="ao-pod-lane-bar">
                <div class="ao-pod-lane-bar-fill" style="width:${Math.max(10, pct)}%;"></div>
              </div>
            </div>
            <div class="ao-lane-actions-col">
              <button type="button" class="ao-lane-act-btn primary" data-ao-open-spec-monitor="${escHtml(selectedDept.agent_id)}:${escHtml(b.specialist_id)}" title="Mở Màn Hình Giám Sát Chuyên Viên">🔍 Giám Sát</button>
              <button type="button" class="ao-lane-act-btn" data-ao-dispatch-handle="${escHtml(b.specialist_handle)}" data-ao-dispatch-prompt="Thực thi lô ${escHtml(b.batch_id)} (${escHtml(b.items_label)}): ${escHtml(b.duty_vi)}" title="Giao việc riêng cho ${escHtml(b.specialist_handle)}">📨 Giao Riêng</button>
            </div>
          </div>
        `;
      })
      .join("");

    return `
      <section class="ao-parallel-lanes-matrix" id="aoParallelLanesMatrixSection">
        <div class="ao-matrix-dept-tabs" role="tablist" aria-label="Chọn Phòng Ban xem Bảng Phân Lô Song Song">
          ${tabsHtml}
        </div>
        <div class="ao-matrix-head">
          <div class="ao-matrix-head-info">
            <h4>🏛️ BẢNG PHÂN LÔ SONG SONG (PARALLEL LANES MATRIX) — ${escHtml(selectedDept.code)} · ${escHtml(selectedDept.name_vi)}</h4>
            <p>${escHtml(pe.parallel_architecture_vi)} · <strong>${batches.length} Luồng Chuyên Viên chạy ĐỒNG THỜI (Parallel Track)</strong> · Tăng tốc <strong>${escHtml(pe.speedup_factor || "4.2x")}</strong></p>
          </div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            <button type="button" class="ao-pod-run-btn" style="padding:7px 12px;font-size:11.5px;" data-ao-dispatch-parallel-dept="${escHtml(selectedDept.agent_id)}">⚡ Chạy Chia Lô Phòng ${escHtml(selectedDept.handle)} (${batches.length} Luồng)</button>
            <button type="button" class="ao-lane-act-btn" data-ao-open-spec-monitor="${escHtml(selectedDept.agent_id)}:lead">👑 Tổ trưởng ${escHtml(lead.handle)}</button>
            <button type="button" class="ao-lane-act-btn" data-ao-open-spec-monitor="${escHtml(selectedDept.agent_id)}:deputy">🛡️ Tổ phó ${escHtml(deputy.handle)}</button>
          </div>
        </div>
        <div class="ao-handoff-beam"></div>
        <div class="ao-matrix-tracks-grid">
          ${lanesRowsHtml}
        </div>
      </section>
    `;
  }

  function renderFullParallelStageHtml(depts, summary) {
    const byId = {};
    (depts || []).forEach((d) => {
      normalizeDepartmentParallel(d);
      byId[d.agent_id] = d;
    });

    const totalDepts = Number(summary.total_departments || depts.length || 15);
    const totalSpecs = Number(summary.total_specialists || 61);
    const totalLeads = Number(summary.total_leads || 15);
    const totalDeputies = Number(summary.total_deputies || 15);
    const show25d = parallelUiState.subView === "both" || parallelUiState.subView === "stage_25d";
    const showMatrix = parallelUiState.subView === "both" || parallelUiState.subView === "parallel_matrix";

    const zonesHtml = PARALLEL_STAGE_ZONES.map((z) => {
      if (z.isParallelVisualHub) {
        const visDept = byId.visuals;
        const ftgDept = byId.footage;
        const voxDept = byId.vox;
        const aiDept = byId.ai_visual;
        return `
          <section class="ao-stage-zone zone-parallel-visual" data-stage-zone="${escHtml(z.id)}">
            <div class="ao-stage-zone-head">
              <div class="ao-stage-zone-title">
                <span>🎬</span>
                <span>${escHtml(z.titleVi)}</span>
              </div>
              <span class="ao-stage-zone-badge">${escHtml(z.badgeVi)}</span>
            </div>
            <div class="ao-visual-tri-hub">
              <div style="max-width:100%;">
                ${renderStudioPodHtml(visDept)}
              </div>
              <div class="ao-visual-tri-splitter-banner">
                <span>🔀 <strong>BỘ CHIA LUỒNG THỊ GIÁC SONG SONG (PARALLEL VISUAL SPLITTER):</strong> Nhận 100% beat từ <code>@visuals</code> ➔ Kích hoạt đồng thời 3 nhánh độc lập:</span>
                <span><code>@footage</code> (Tư liệu thật) ∥ <code>@vox</code> (Đồ họa điều tra 8 NS) ∥ <code>@ai_visual</code> (Tái dựng AI 4D) ➔ Hội tụ về <code>@edit</code></span>
              </div>
              <div class="ao-handoff-beam"></div>
              <div class="ao-visual-tri-branches">
                <div class="ao-tri-branch-col">
                  <div class="ao-tri-branch-tag"><span>🎬 NHÁNH SONG SONG A · TƯ LIỆU THẬT</span><span>∥ PARALLEL</span></div>
                  ${renderStudioPodHtml(ftgDept)}
                </div>
                <div class="ao-tri-branch-col">
                  <div class="ao-tri-branch-tag" style="border-color:#facc15;color:#fde68a;"><span>📐 NHÁNH SONG SONG B · ĐỒ HỌA VOX (8 NS)</span><span>∥ PARALLEL</span></div>
                  ${renderStudioPodHtml(voxDept)}
                </div>
                <div class="ao-tri-branch-col">
                  <div class="ao-tri-branch-tag"><span>🖼️ NHÁNH SONG SONG C · ẢNH AI 4D</span><span>∥ PARALLEL</span></div>
                  ${renderStudioPodHtml(aiDept)}
                </div>
              </div>
            </div>
          </section>
        `;
      }

      const zoneDepts = z.agents.map((aid) => byId[aid]).filter(Boolean);
      return `
        <section class="ao-stage-zone" data-stage-zone="${escHtml(z.id)}">
          <div class="ao-stage-zone-head">
            <div class="ao-stage-zone-title">
              <span>🏛️</span>
              <span>${escHtml(z.titleVi)}</span>
            </div>
            <span class="ao-stage-zone-badge">${escHtml(z.badgeVi)}</span>
          </div>
          <div class="ao-stage-pods-grid">
            ${zoneDepts.map(renderStudioPodHtml).join("")}
          </div>
        </section>
      `;
    }).join("");

    return `
      <div class="ao-parallel-command-bar" id="aoParallelStageCommandBar">
        <div class="ao-parallel-cmd-top">
          <div class="ao-parallel-cmd-title-group">
            <div class="ao-parallel-cmd-eyebrow">
              <span class="ao-parallel-mode-pill">⚡ CHIA LÔ SONG SONG ĐA NHÁNH (PARALLEL WORKER POOL)</span>
              <span class="ao-parallel-speedup-pill">🚀 Tăng tốc trung bình: ~3.8x–4.5x (Peak 4.5x)</span>
              ${parallelUiState.lastWaveAt ? `<span class="ao-parallel-speedup-pill" style="color:#6ee7b7;border-color:#34d399;">✓ Đã chia lô lúc ${escHtml(parallelUiState.lastWaveAt)}</span>` : ""}
            </div>
            <h4>🎭 Sân Khấu 15 Phòng Ban — Chia Lô Chạy Song Song (Live Parallel Studio Stage)</h4>
            <p>Tổ trưởng chia lô (Batch Sharding) ➔ Toàn bộ Chuyên viên chạy song song cùng một lúc trên các luồng độc lập (<code>Lane 1..N</code>) ➔ Tổ phó đối chiếu checklist &amp; hợp nhất bàn giao.</p>
            <div class="ao-parallel-kpi-pills">
              <span class="ao-parallel-kpi-chip">🏛️ Phòng Ban: <strong>${totalDepts} Phòng</strong></span>
              <span class="ao-parallel-kpi-chip">👥 Tổng Nhân Sự: <strong>91 Agent (${totalLeads} Tổ trưởng + ${totalDeputies} Tổ phó + 61/${totalSpecs} Chuyên viên)</strong></span>
              <span class="ao-parallel-kpi-chip">⚡ Chế Độ: <strong>PARALLEL WORKER POOL (8 Luồng Xử Lý Thực)</strong></span>
              <span class="ao-parallel-kpi-chip">⏱️ Hệ Số Tăng Tốc: <strong>~3.8x–4.5x</strong></span>
            </div>
          </div>

          <div class="ao-parallel-cmd-actions">
            <button type="button" class="ao-parallel-cta-all-btn${parallelUiState.isDispatchingWave ? " is-dispatching" : ""}" id="aoDispatchAllParallelBtn" data-ao-dispatch-parallel-dept="all">
              <span>⚡ Kích Hoạt Chia Lô Chạy Song Song Toàn Sân Khấu (15 Phòng · 61 Chuyên Viên)</span>
            </button>
            <div class="ao-parallel-subview-switch" role="group" aria-label="Chuyển đổi chế độ xem Sân Khấu Song Song">
              <button type="button" class="ao-parallel-mode-btn${parallelUiState.subView === "both" ? " active" : ""}" data-ao-parallel-subview="both">⚡ Toàn Cảnh (2.5D + Phân Lô)</button>
              <button type="button" class="ao-parallel-mode-btn${parallelUiState.subView === "stage_25d" ? " active" : ""}" data-ao-parallel-subview="stage_25d">🎭 Sân Khấu Phim Trường 2.5D</button>
              <button type="button" class="ao-parallel-mode-btn${parallelUiState.subView === "parallel_matrix" ? " active" : ""}" data-ao-parallel-subview="parallel_matrix">🏛️ Sơ Đồ Phân Lô Song Song Chi Tiết</button>
            </div>
          </div>
        </div>
      </div>

      ${
        show25d
          ? `
        <div class="ao-parallel-25d-floorplan${parallelUiState.isDispatchingWave ? " is-wave-running" : ""}" id="aoParallelStudio25DFloorplan">
          <div class="ao-floorplan-25d-header">
            <strong>🎭 SÂN KHẤU PHIM TRƯỜNG 2.5D (INTERACTIVE STUDIO FLOORPLAN · 15 CỤM BÀN LÀM VIỆC · 5 KHU VỰC DÂY CHUYỀN)</strong>
            <div class="ao-floorplan-25d-legend">
              <span>👑 Tổ trưởng (Chia lô &amp; Ký duyệt)</span>
              <span>🛡️ Tổ phó (Rà Checklist &amp; Hợp nhất)</span>
              <span>⚡ Lô #1..#N (Chuyên viên chạy song song đồng thời)</span>
            </div>
          </div>
          <div class="ao-stage-zones-stack">
            ${zonesHtml}
          </div>
        </div>
      `
          : ""
      }

      ${showMatrix ? renderParallelLanesMatrixHtml(depts) : ""}
    `;
  }

  function ensureSpecialistMonitorMounted() {
    const dlg = document.getElementById("agentOfficeDialog") || document.body;
    let drawer = document.getElementById("aoSpecialistLiveMonitorDrawer");
    if (!drawer) {
      drawer = document.createElement("div");
      drawer.id = "aoSpecialistLiveMonitorDrawer";
      drawer.className = "ao-spec-monitor-backdrop";
      dlg.appendChild(drawer);
    } else if (dlg && drawer.parentElement !== dlg) {
      dlg.appendChild(drawer);
    }
    return drawer;
  }

  function openSpecialistLiveMonitor(deptId, memberKey) {
    const depts = parallelUiState.departments || [];
    const dept = depts.find((d) => d.agent_id === deptId) || depts[0];
    if (!dept) return;
    normalizeDepartmentParallel(dept);
    parallelUiState.selectedDeptId = dept.agent_id;
    parallelUiState.monitorTarget = { deptId: dept.agent_id, memberKey: memberKey };

    const pe = dept.parallel_engine || {};
    const batches = Array.isArray(pe.batches) ? pe.batches : [];
    const specs = Array.isArray(dept.specialists) ? dept.specialists : [];

    let roleBadge = "⚡ CHUYÊN VIÊN PHÂN LÔ SONG SONG (PARALLEL SPECIALIST)";
    let titleVi = "";
    let handle = "";
    let dutyVi = "";
    let batchId = "LÔ-ALL";
    let laneLabel = `Đồng bộ ${batches.length} Luồng`;
    let itemsLabel = "Toàn bộ dải Beat của Phòng";
    let scopeVi = pe.parallel_architecture_vi || "";
    let workerThread = `cofi-parallel-${dept.agent_id}-master`;
    let elapsedMs = Number(pe.elapsed_ms || 36);
    let progressPct = 100;
    let findingVi = "";
    let artifactKey = "department_parallel_state.json";
    let handoffPair = `${dept.lead?.handle || "@lead"} ➔ ${dept.deputy?.handle || "@deputy"}`;

    if (memberKey === "lead") {
      const lead = dept.lead || {};
      roleBadge = "👑 TẦNG 1 · TỔ TRƯỞNG CHỈ HUY & KÝ DUYỆT (DEPARTMENT LEAD)";
      titleVi = lead.title_vi || "Tổ trưởng";
      handle = lead.handle || `@${dept.agent_id}_lead`;
      dutyVi = lead.role_vi || "";
      findingVi = (pe.lead_signoff && pe.lead_signoff.summary_vi) || `Tổ trưởng chia ${batches.length} lô song song và ký duyệt: ${lead.approval_output_vi || ""}`;
      artifactKey = lead.approval_output_vi || "Master Sign-off";
    } else if (memberKey === "deputy") {
      const deputy = dept.deputy || {};
      roleBadge = "🛡️ TẦNG 2 · TỔ PHÓ RÀ SOÁT CHECKLIST & HỢP NHẤT LÔ (DEPARTMENT DEPUTY)";
      titleVi = deputy.title_vi || "Tổ phó";
      handle = deputy.handle || `@${dept.agent_id}_deputy`;
      dutyVi = deputy.role_vi || "";
      findingVi = (pe.deputy_verification && pe.deputy_verification.summary_vi) || `Tổ phó đối chiếu checklist ${batches.length}/${batches.length} lô song song.`;
      artifactKey = "Internal Checklist Gate (100%)";
    } else {
      const sp = specs.find((s) => s.id === memberKey || s.handle === memberKey) || specs[0] || {};
      const b = batches.find((x) => x.specialist_id === sp.id || x.specialist_handle === sp.handle) || batches[0] || {};
      titleVi = sp.title_vi || b.specialist_name_vi || "Chuyên viên";
      handle = sp.handle || b.specialist_handle || `@${dept.agent_id}_spec`;
      dutyVi = sp.role_vi || b.duty_vi || "";
      batchId = b.batch_id || sp.batch_id || "LÔ-01";
      laneLabel = `Lane #${b.parallel_lane || sp.parallel_lane || 1} / ${batches.length}`;
      itemsLabel = b.items_label || sp.items_label || "B001–B041";
      scopeVi = b.batch_scope_vi || sp.batch_scope_vi || "";
      workerThread = b.worker_thread || sp.worker_thread || `pool-${dept.agent_id}-w01`;
      elapsedMs = Number(b.elapsed_ms || sp.elapsed_ms || 24);
      progressPct = Number(b.progress_pct != null ? b.progress_pct : 100);
      findingVi = b.finding_vi || b.current_action_vi || sp.current_action_vi || sp.task_detail_vi || "";
      artifactKey = sp.artifact_key || "artifact.json";
      handoffPair = `📥 ${sp.input_from || dept.lead?.handle || "@lead"} ➔ 📤 ${sp.output_to || dept.deputy?.handle || "@deputy"}`;
    }

    const checklistItems = (dept.deputy && Array.isArray(dept.deputy.checklist_vi) ? dept.deputy.checklist_vi : [])
      .map((c) => `<li>✓ ${escHtml(c)}</li>`)
      .join("");

    const drawer = ensureSpecialistMonitorMounted();
    drawer.innerHTML = `
      <aside class="ao-spec-monitor-panel" role="dialog" aria-label="Màn Hình Giám Sát Chuyên Viên">
        <header class="ao-spec-monitor-head">
          <div>
            <div style="font-size:10.5px;font-weight:800;color:#34d399;letter-spacing:0.04em;margin-bottom:4px;">${escHtml(roleBadge)}</div>
            <h4 style="margin:0 0 4px;font-size:15px;color:#f8fafc;">${escHtml(titleVi)} <code style="color:#38bdf8;font-size:13px;">${escHtml(handle)}</code></h4>
            <div style="font-size:11.5px;color:#94a3b8;">${escHtml(dept.emoji || "🏛️")} ${escHtml(dept.code)} · ${escHtml(dept.name_vi)}</div>
          </div>
          <button type="button" class="icon-btn channel-profile-dialog-close" data-ao-close-spec-monitor="1" title="Đóng màn hình giám sát">×</button>
        </header>
        <div class="ao-spec-monitor-body">
          <div class="ao-spec-monitor-kv-grid">
            <div class="ao-spec-monitor-kv">
              <span>Luồng &amp; Mã Lô Song Song</span>
              <strong>⚡ ${escHtml(laneLabel)} · ${escHtml(batchId)}</strong>
            </div>
            <div class="ao-spec-monitor-kv">
              <span>Dải Beat Phụ Trách (Batch Scope)</span>
              <strong style="color:#fde68a;">🎯 ${escHtml(itemsLabel)}</strong>
            </div>
            <div class="ao-spec-monitor-kv">
              <span>Worker Thread &amp; Thời Gian</span>
              <strong style="color:#6ee7b7;">🧵 ${escHtml(workerThread)} (${elapsedMs.toFixed(1)}ms)</strong>
            </div>
            <div class="ao-spec-monitor-kv">
              <span>Tiến Độ &amp; Tăng Tốc</span>
              <strong style="color:#38bdf8;">${progressPct}% · 🚀 ${escHtml(pe.speedup_factor || "4.2x")}</strong>
            </div>
          </div>

          <section class="ao-spec-monitor-section">
            <h5>📌 Nhiệm Vụ Chuyên Môn &amp; Phạm Vi Phân Lô</h5>
            <p style="margin:0 0 6px;font-size:12.5px;color:#f1f5f9;line-height:1.45;"><strong>Chuyên môn:</strong> ${escHtml(dutyVi)}</p>
            <p style="margin:0 0 6px;font-size:12px;color:#cbd5e1;line-height:1.45;"><strong>Phạm vi lô:</strong> ${escHtml(scopeVi)}</p>
            <div style="font-size:11.5px;color:#93c5fd;font-family:'JetBrains Mono',monospace;">🔄 Luồng bàn giao: ${escHtml(handoffPair)} · 📦 Đầu ra: <code>${escHtml(artifactKey)}</code></div>
          </section>

          <section class="ao-spec-monitor-section" style="border-color:rgba(52,211,153,0.4);">
            <h5>🔬 Kết Quả Kiểm Tra Thật Từ Workspace (Real Workspace Telemetry)</h5>
            <p style="margin:0 0 8px;font-size:12.5px;color:#d1fae5;line-height:1.5;">${escHtml(findingVi)}</p>
            ${
              checklistItems
                ? `<div style="font-size:11.5px;color:#cbd5e1;"><strong>Checklist nghiệm thu nội bộ (${escHtml(dept.deputy?.handle || "@deputy")}):</strong><ul style="margin:5px 0 0;padding-left:18px;line-height:1.45;">${checklistItems}</ul></div>`
                : ""
            }
          </section>

          <section class="ao-spec-monitor-section">
            <h5>📨 Gửi Lệnh Điều Phối Riêng Cho ${escHtml(handle)}</h5>
            <div class="ao-spec-monitor-cmd-box">
              <input type="text" id="aoSpecMonitorCmdInput" class="ao-spec-monitor-cmd-input" value="Thực thi & kiểm tra lô ${escHtml(batchId)} (${escHtml(itemsLabel)}) — ${escHtml(titleVi)}" aria-label="Nhập lệnh điều phối riêng cho chuyên viên" />
              <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <button type="button" class="ao-parallel-cta-all-btn" style="padding:8px 14px;font-size:12px;" data-ao-send-spec-monitor-cmd="${escHtml(handle)}">📨 Gửi Lệnh Riêng Cho ${escHtml(handle)}</button>
                <button type="button" class="ao-pod-run-btn" style="padding:8px 12px;font-size:12px;" data-ao-dispatch-parallel-dept="${escHtml(dept.agent_id)}">⚡ Chạy Chia Lô Phòng ${escHtml(dept.handle)} Ngay</button>
              </div>
            </div>
          </section>
        </div>
      </aside>
    `;
    drawer.classList.add("is-open");
  }

  function closeSpecialistLiveMonitor() {
    const drawer = document.getElementById("aoSpecialistLiveMonitorDrawer");
    if (drawer) drawer.classList.remove("is-open");
    parallelUiState.monitorTarget = null;
  }

  function enhanceExistingDepartmentCards(depts) {
    const byId = {};
    (depts || []).forEach((d) => {
      normalizeDepartmentParallel(d);
      byId[d.agent_id] = d;
    });

    document.querySelectorAll(".ao-dept-card[data-ao-agent]").forEach((card) => {
      const aid = card.getAttribute("data-ao-agent");
      const dept = byId[aid];
      if (!dept) return;
      const pe = dept.parallel_engine || {};
      const batches = Array.isArray(pe.batches) ? pe.batches : [];

      let headRight = card.querySelector(".ao-dept-head-right");
      if (headRight && !headRight.querySelector("[data-ao-dispatch-parallel-dept]")) {
        const runBtn = document.createElement("button");
        runBtn.type = "button";
        runBtn.className = "ao-pod-run-btn";
        runBtn.setAttribute("data-ao-dispatch-parallel-dept", dept.agent_id);
        runBtn.textContent = `⚡ Chạy Chia Lô Phòng Này (${batches.length} Lô · ${pe.speedup_factor || "4.2x"})`;
        headRight.prepend(runBtn);
      }

      const specNodes = card.querySelectorAll(".ao-dept-spec-node");
      specNodes.forEach((node, idx) => {
        const b = batches[idx];
        if (!b) return;
        if (!node.querySelector(".ao-card-parallel-lane-bar")) {
          const laneDiv = document.createElement("div");
          laneDiv.className = "ao-card-parallel-lane-bar";
          laneDiv.style.cssText = "margin-top:6px;padding:5px 7px;border-radius:7px;background:rgba(16,185,129,0.12);border:1px solid rgba(52,211,153,0.35);font-size:10.5px;display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap;";
          laneDiv.innerHTML = `
            <span style="color:#6ee7b7;font-family:'JetBrains Mono',monospace;font-weight:700;">⚡ Lane #${escHtml(b.parallel_lane)} · ${escHtml(b.batch_id)} · 🎯 ${escHtml(String(b.items_label).split("(")[0].trim())} (${Number(b.progress_pct || 100)}%)</span>
            <button type="button" class="ao-lane-act-btn primary" style="padding:2px 7px;font-size:10px;" data-ao-open-spec-monitor="${escHtml(dept.agent_id)}:${escHtml(b.specialist_id)}">🔍 Giám Sát Live</button>
          `;
          node.appendChild(laneDiv);
        }
      });
    });
  }

  function renderParallelStageMounts(force) {
    ensureParallelStylesInjected();
    const depts = parallelUiState.departments || [];
    if (!depts.length) return;

    const stageWrap = document.getElementById("agentOfficeStageWrap");
    const canvas = document.getElementById("agentOfficeFloorplanCanvas");
    if (stageWrap && canvas) {
      let mount = document.getElementById("aoParallelStudioStageMount");
      if (!mount) {
        mount = document.createElement("section");
        mount.id = "aoParallelStudioStageMount";
        mount.className = "ao-parallel-stage-mount";
        stageWrap.insertBefore(mount, canvas);
      }
      const activeViewBtn = document.querySelector("[data-ao-view].active");
      const curView = activeViewBtn ? activeViewBtn.getAttribute("data-ao-view") : "departments";
      mount.style.display = curView === "departments" ? "flex" : "none";

      const sig = JSON.stringify({
        sub: parallelUiState.subView,
        sel: parallelUiState.selectedDeptId,
        wave: parallelUiState.isDispatchingWave,
        waveAt: parallelUiState.lastWaveAt,
        cnt: depts.length,
        p0: depts[0]?.parallel_engine?.pipeline_state,
      });
      if (force || sig !== parallelUiState.lastRenderSig) {
        parallelUiState.lastRenderSig = sig;
        mount.innerHTML = renderFullParallelStageHtml(depts, parallelUiState.summary || {});
      }
    }

    enhanceExistingDepartmentCards(depts);
  }

  async function triggerParallelDispatch(deptIdOrAll) {
    const target = deptIdOrAll || "all";
    parallelUiState.isDispatchingWave = true;
    if (target !== "all") {
      parallelUiState.selectedDeptId = target;
    }
    renderParallelStageMounts(true);

    try {
      const jobId = getActiveJobId();
      const resp = await fetch("/api/agent-departments/dispatch-parallel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dept_id: target, job_id: jobId }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (Array.isArray(data.departments) && data.departments.length) {
          parallelUiState.departments = data.departments;
        }
        if (data.summary && typeof data.summary === "object") {
          parallelUiState.summary = data.summary;
        }
        const now = new Date();
        parallelUiState.lastWaveAt = now.toLocaleTimeString("vi-VN", { hour12: false });
      }
    } catch (_e) {
      // Keep optimistic parallel wave state
    } finally {
      setTimeout(() => {
        parallelUiState.isDispatchingWave = false;
        renderParallelStageMounts(true);
        if (parallelUiState.monitorTarget) {
          openSpecialistLiveMonitor(parallelUiState.monitorTarget.deptId, parallelUiState.monitorTarget.memberKey);
        }
      }, 650);
    }
  }

  async function syncDepartmentsData() {
    try {
      const jobId = getActiveJobId();
      const q = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";
      const r = await fetch(`/api/agent-departments${q}`, { cache: "no-store" });
      if (!r.ok) return;
      const d = await r.json();
      if (Array.isArray(d.departments) && d.departments.length) {
        parallelUiState.departments = d.departments;
        parallelUiState.summary = d.summary || {};
        renderParallelStageMounts(false);
      }
    } catch (_e) {
      // Ignore background fetch error
    }
  }

  function bindParallelStageEvents() {
    document.addEventListener("click", (ev) => {
      const dispatchBtn = ev.target.closest("[data-ao-dispatch-parallel-dept]");
      if (dispatchBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const targetDept = dispatchBtn.getAttribute("data-ao-dispatch-parallel-dept") || "all";
        triggerParallelDispatch(targetDept);
        return;
      }

      const subviewBtn = ev.target.closest("[data-ao-parallel-subview]");
      if (subviewBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        parallelUiState.subView = subviewBtn.getAttribute("data-ao-parallel-subview") || "both";
        renderParallelStageMounts(true);
        return;
      }

      const monitorBtn = ev.target.closest("[data-ao-open-spec-monitor]");
      if (monitorBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const raw = monitorBtn.getAttribute("data-ao-open-spec-monitor") || "vox:lead";
        const parts = raw.split(":");
        openSpecialistLiveMonitor(parts[0] || "vox", parts[1] || "lead");
        renderParallelStageMounts(true);
        return;
      }

      if (ev.target.closest("[data-ao-close-spec-monitor]") || ev.target.id === "aoSpecialistLiveMonitorDrawer") {
        ev.preventDefault();
        ev.stopPropagation();
        closeSpecialistLiveMonitor();
        return;
      }

      const sendSpecBtn = ev.target.closest("[data-ao-send-spec-monitor-cmd]");
      if (sendSpecBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const handle = sendSpecBtn.getAttribute("data-ao-send-spec-monitor-cmd") || "@vox_lead";
        const inp = document.getElementById("aoSpecMonitorCmdInput");
        const cmdTxt = inp && inp.value.trim() ? inp.value.trim() : "";
        closeSpecialistLiveMonitor();
        const fakeBtn = document.createElement("button");
        fakeBtn.setAttribute("data-ao-dispatch-handle", handle);
        if (cmdTxt) fakeBtn.setAttribute("data-ao-dispatch-prompt", cmdTxt);
        fakeBtn.style.display = "none";
        document.body.appendChild(fakeBtn);
        fakeBtn.click();
        fakeBtn.remove();
        return;
      }

      const selectDeptEl = ev.target.closest("[data-ao-select-parallel-dept]");
      if (selectDeptEl) {
        const deptId = selectDeptEl.getAttribute("data-ao-select-parallel-dept");
        if (deptId) {
          parallelUiState.selectedDeptId = deptId;
          renderParallelStageMounts(true);
        }
      }

      if (ev.target.closest("[data-open-agent-office]") || ev.target.closest("[data-ao-view]") || ev.target.closest("[data-ao-tab]")) {
        setTimeout(() => {
          if (!parallelUiState.departments.length) {
            syncDepartmentsData();
          } else {
            renderParallelStageMounts(true);
          }
        }, 80);
      }
    });

    const obsTarget = document.getElementById("agentOfficeDialog") || document.body;
    const observer = new MutationObserver(() => {
      if (parallelUiState.departments.length) {
        enhanceExistingDepartmentCards(parallelUiState.departments);
        const mount = document.getElementById("aoParallelStudioStageMount");
        if (!mount || !mount.innerHTML.trim()) {
          renderParallelStageMounts(true);
        }
      }
    });
    observer.observe(obsTarget, { childList: true, subtree: true });

    syncDepartmentsData();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindParallelStageEvents);
  } else {
    bindParallelStageEvents();
  }
})();
"""


def _execute_department_parallel_dispatch_safe(
    service: DocumentaryService,
    dept_id: str | list[str] | None = "all",
    job_id: str | None = None,
) -> dict[str, Any]:
    """Execute parallel specialist batches via documentary.agent_departments with safe fallback."""
    import documentary.agent_departments as agent_departments
    from documentary.agent_office import build_live_office_snapshot

    clean_dept_id = dept_id if dept_id else "all"
    req_job_id = str(job_id or "").strip() or None

    all_jobs = service.list_jobs()
    selected_job: dict[str, Any] | None = None
    if req_job_id:
        try:
            selected_job = service.get_job(req_job_id)
        except Exception:
            selected_job = next((j for j in all_jobs if j.get("id") == req_job_id), None)
    if selected_job is None and all_jobs:
        selected_job = next(
            (j for j in all_jobs if str(j.get("status") or "").lower() in {"running", "queued"}),
            all_jobs[0],
        )

    workspace_dir: Path | None = None
    if selected_job and selected_job.get("workspace"):
        workspace_dir = Path(str(selected_job["workspace"]))
    elif selected_job and selected_job.get("id"):
        workspace_dir = ROOT / "workspaces" / str(selected_job["id"])

    exec_fn = getattr(agent_departments, "execute_department_parallel_batches", None)
    if callable(exec_fn):
        exec_state = exec_fn(
            workspace_dir=workspace_dir,
            dept_id=clean_dept_id,
            job_snapshot=selected_job,
        )
    else:
        exec_state = {
            "schema_version": "1.0",
            "execution_mode": "parallel_specialist_pool",
            "max_workers": 8,
            "job_id": selected_job.get("id") if selected_job else (req_job_id or ""),
            "dispatched_departments": list(getattr(agent_departments, "DEPARTMENT_ORDER", ())),
            "departments": {},
        }

    eff_job_id = selected_job.get("id") if selected_job else req_job_id
    cache_key = str(eff_job_id or "__default__")
    if isinstance(exec_state.get("departments"), dict):
        job_cache = _PARALLEL_RUNTIME_CACHE.setdefault(cache_key, {})
        job_cache.update(exec_state["departments"])

    office_snap = build_live_office_snapshot(service, job_id=eff_job_id)
    departments_list = office_snap.get("departments", [])
    job_cache = _PARALLEL_RUNTIME_CACHE.get(cache_key) if isinstance(_PARALLEL_RUNTIME_CACHE.get(cache_key), dict) else {}
    for d in departments_list:
        if isinstance(d, dict):
            aid = str(d.get("agent_id") or "")
            cached_pe = (job_cache.get(aid) or {}).get("parallel_engine")
            if isinstance(cached_pe, dict):
                d["parallel_engine"] = cached_pe
                d["batches"] = cached_pe.get("batches", d.get("batches", []))

    return {
        "status": "ok",
        "ok": True,
        "job_id": eff_job_id,
        "dept_id": clean_dept_id,
        "parallel_execution": exec_state,
        "departments": departments_list,
        "summary": office_snap.get("departments_summary", {}),
        "active_parallel_workers": office_snap.get("active_parallel_workers", []),
        "agent_office": office_snap,
    }


def _render_index_html_with_parallel_stage(index_path: Path) -> str:
    """Inject the Live Parallel Studio Stage CSS, Mounts, and Controller into index.html."""
    raw_html = index_path.read_text(encoding="utf-8")
    if 'id="cofiParallelStageStyle"' in raw_html:
        return raw_html

    stage_Target = '<div class="ao-floorplan-canvas" id="agentOfficeFloorplanCanvas"></div>'
    if stage_Target in raw_html and 'id="aoParallelStudioStageMount"' not in raw_html:
        raw_html = raw_html.replace(
            stage_Target,
            '<section id="aoParallelStudioStageMount" class="ao-parallel-stage-mount"></section>\n          ' + stage_Target,
            1,
        )

    bundle = (
        f'\n  <style id="cofiParallelStageStyle">{LIVE_PARALLEL_STUDIO_STAGE_CSS}</style>\n'
        f'  <script id="cofiParallelStageCssSeed">window.__COFI_PARALLEL_STAGE_CSS_TEXT__ = {json.dumps(LIVE_PARALLEL_STUDIO_STAGE_CSS, ensure_ascii=False)};</script>\n'
        f'  <script id="cofiParallelStageScript">{LIVE_PARALLEL_STUDIO_STAGE_JS}</script>\n'
    )
    if "</body>" in raw_html:
        return raw_html.replace("</body>", bundle + "</body>", 1)
    return raw_html + bundle



def create_app(service: DocumentaryService | None = None) -> FastAPI:
    service = service or DocumentaryService(
        ROOT,
        remotion_dir=os.getenv("COFI_REMOTION_DIR", r"B:\ALL_TOOLS\CofiRemotion"),
        radar_url=os.getenv("COFI_RADAR_URL", "http://127.0.0.1:8775"),
        voice_url=os.getenv("COFI_VOICE_URL", "http://127.0.0.1:8000"),
        remotion_studio_port=int(os.getenv("COFI_REMOTION_STUDIO_PORT", "8890")),
        cofi_studio_embed_port=int(os.getenv("COFI_STUDIO_EMBED_PORT", "8894")),
    )
    api = FastAPI(title="COFI DOCUMENTARY", version="0.2.0")
    api.state.service = service

    @api.get("/static/agent_office.js")
    def serve_enhanced_agent_office_js():
        ao_path = STATIC_DIR / "agent_office.js"
        base_js = ao_path.read_text(encoding="utf-8") if ao_path.exists() else ""
        css_seed = f"\nwindow.__COFI_PARALLEL_STAGE_CSS_TEXT__ = {json.dumps(LIVE_PARALLEL_STUDIO_STAGE_CSS, ensure_ascii=False)};\n"
        return Response(
            content=base_js + css_seed + LIVE_PARALLEL_STUDIO_STAGE_JS,
            media_type="application/javascript; charset=utf-8",
        )

    if STATIC_DIR.exists():
        api.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    class _FastNoStoreMiddleware:
        """Pure ASGI header middleware that avoids BaseHTTPMiddleware stream buffering on large video FileResponses."""

        def __init__(self, app_inner):
            self.app_inner = app_inner

        async def __call__(self, scope, receive, send):
            if scope.get("type") != "http":
                await self.app_inner(scope, receive, send)
                return
            path = scope.get("path") or ""
            is_media_stream = path.endswith("/media")
            should_no_store = (not is_media_stream) and (
                path == "/" or path.startswith("/static/") or path.startswith("/api/")
            )
            if not should_no_store:
                await self.app_inner(scope, receive, send)
                return

            async def _send_with_headers(message):
                if message.get("type") == "http.response.start":
                    headers = list(message.get("headers") or [])
                    existing = {k.lower() for k, _ in headers}
                    if b"cache-control" not in existing:
                        headers.append((b"cache-control", b"no-store, no-cache, must-revalidate, max-age=0"))
                    if b"pragma" not in existing:
                        headers.append((b"pragma", b"no-cache"))
                    if b"expires" not in existing:
                        headers.append((b"expires", b"0"))
                    message = {**message, "headers": headers}
                await send(message)

            await self.app_inner(scope, receive, _send_with_headers)

    api.add_middleware(_FastNoStoreMiddleware)

    @api.get("/api/health")
    def health(cached: bool = Query(default=False)):
        try:
            return service.health(cached=cached)
        except TypeError:
            return service.health()

    @api.get("/api/hardware-profile")
    def hardware_profile(force: bool = Query(default=False)):
        fn = getattr(service, "hardware_profile", None)
        if callable(fn):
            return fn(force_refresh=force)
        from documentary.render_cache import detect_hardware_profile

        return detect_hardware_profile(force_refresh=force)

    @api.post("/api/hardware-profile/reclaim-vram")
    def reclaim_idle_vram():
        fn = getattr(service, "reclaim_idle_vram", None)
        if callable(fn):
            return fn()
        return {"ok": False}

    @api.get("/api/system/cache-report")
    def system_cache_report(selected_job_id: str | None = Query(default=None)):
        fn = getattr(service, "cache_report", None)
        if callable(fn):
            return fn(selected_job_id=selected_job_id)
        return {"ok": False, "error": "cache_report_unavailable"}

    @api.post("/api/system/cache-clean")
    def system_cache_clean(body: SmartCacheCleanRequest):
        fn = getattr(service, "clean_cache", None)
        if not callable(fn):
            raise HTTPException(status_code=503, detail="clean_cache_unavailable")
        try:
            return fn(
                mode=body.mode,
                selected_job_id=body.selected_job_id,
                target_job_ids=body.target_job_ids,
                include_tier1=body.include_tier1,
                reclaim_ram=body.reclaim_ram,
                dry_run=body.dry_run,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/cache-clean")
    def job_cache_clean(job_id: str, mode: str = Query(default="slim_completed")):
        fn = getattr(service, "clean_cache", None)
        if not callable(fn):
            raise HTTPException(status_code=503, detail="clean_cache_unavailable")
        try:
            return fn(
                mode=mode,
                target_job_ids=[job_id],
                include_tier1=True,
                reclaim_ram=False,
                dry_run=False,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/realtime-pulse")
    def realtime_pulse(selected_job_id: str | None = Query(default=None)):
        pulse_fn = getattr(service, "realtime_pulse", None)
        if callable(pulse_fn):
            return pulse_fn(selected_job_id)
        jobs_list = service.list_jobs()
        return {"signature": str(len(jobs_list)), "jobs_count": len(jobs_list), "live": {}}

    @api.get("/api/events")
    async def realtime_events(request: Request, selected_job_id: str | None = Query(default=None)):
        async def _stream():
            last_sig = ""
            ticks_since_ping = 0
            while True:
                if await request.is_disconnected():
                    break
                try:
                    pulse_fn = getattr(service, "realtime_pulse", None)
                    payload = pulse_fn(selected_job_id) if callable(pulse_fn) else {"signature": ""}
                    sig = str(payload.get("signature") or "")
                    if sig != last_sig:
                        last_sig = sig
                        ticks_since_ping = 0
                        yield f"event: pulse\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    else:
                        ticks_since_ping += 1
                        if ticks_since_ping >= 15:
                            ticks_since_ping = 0
                            yield ": ping\n\n"
                except Exception:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.75)

        return StreamingResponse(
            _stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @api.get("/api/system/trail-status")
    def trail_status():
        return service.trail_status()

    @api.post("/api/system/trail-sync")
    def trail_sync():
        return service.trail_sync()

    @api.post("/api/ai-accounts/{provider}/login")
    def ai_account_login(provider: str):
        try:
            return service.ai_account_login(provider)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @api.patch("/api/ai-accounts/{provider}/settings")
    def ai_account_settings(provider: str, body: AIAccountSettingsRequest):
        try:
            return service.update_ai_account_settings(provider, body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @api.patch("/api/chat-provider")
    def chat_provider(body: ChatProviderRequest):
        try:
            return service.update_chat_provider(body.provider)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/jobs")
    def jobs(summary: bool = Query(default=False)):
        try:
            return service.list_jobs(summary=summary)
        except TypeError:
            return service.list_jobs()

    @api.post("/api/storage/select-folder")
    def select_storage_folder():
        try:
            return service.select_workspace_root()
        except (OSError, RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs")
    def create_job(body: CreateJobRequest):
        try:
            return service.create_job(body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/from-radar")
    def create_job_from_radar(body: RadarImportRequest):
        overrides = body.model_dump(exclude={"scan_id", "video_id"}, exclude_none=True)
        try:
            return service.create_job_from_radar(body.scan_id, body.video_id, overrides)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không thể lấy chủ đề từ Radar: {exc}") from exc

    @api.get("/api/jobs/{job_id}")
    def job_detail(job_id: str):
        try:
            return service.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.delete("/api/jobs/{job_id}")
    def delete_job(job_id: str):
        try:
            return service.delete_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.patch("/api/jobs/{job_id}/voice")
    def update_voice(job_id: str, body: VoiceSettingsRequest):
        try:
            return service.update_voice_settings(job_id, body.model_dump())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/ai-visual-settings")
    def ai_visual_settings(job_id: str):
        try:
            return service.ai_visual_settings(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.get("/api/ai-visual/style-presets")
    def ai_visual_style_presets():
        return service.ai_visual_style_presets()

    @api.patch("/api/jobs/{job_id}/ai-visual-settings")
    def update_ai_visual_settings(job_id: str, body: AIVisualSettingsRequest):
        try:
            return service.update_ai_visual_settings(job_id, body.model_dump(exclude_none=True))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.patch("/api/jobs/{job_id}/production-settings")
    def update_production_settings(job_id: str, body: ProductionSettingsRequest):
        try:
            return service.update_production_settings(job_id, body.model_dump(exclude_none=True))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/cofi-studio/embed")
    def cofi_studio_embed_status():
        return service.cofi_studio_embed_status()

    @api.post("/api/cofi-studio/embed/start")
    def cofi_studio_embed_start():
        try:
            return service.cofi_studio_embed_status(start=True)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/ai-visual-runtime")
    def ai_visual_runtime(job_id: str):
        try:
            return service.ai_visual_runtime(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/ai-visual-reset")
    def ai_visual_reset(job_id: str):
        try:
            return service.ai_visual_reset(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/ai-visual-test")
    def ai_visual_test(job_id: str):
        try:
            return service.ai_visual_test(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/ai-visual-video-test")
    def ai_visual_video_test(job_id: str):
        try:
            return service.ai_visual_video_test(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/queue/{action}")
    def ai_visual_runtime_queue(action: str):
        try:
            return service.ai_visual_runtime_queue(action)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/accounts/login")
    def ai_visual_runtime_account_login():
        try:
            return service.ai_visual_runtime_account_login()
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/accounts/prune-dead")
    def ai_visual_runtime_prune_dead_accounts():
        try:
            return service.ai_visual_runtime_prune_dead_accounts()
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/accounts/check-all")
    def ai_visual_runtime_check_all_accounts():
        try:
            return service.ai_visual_runtime_check_all_accounts()
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/accounts/clean-cache")
    def ai_visual_runtime_clean_cache():
        try:
            return service.ai_visual_runtime_clean_profile_caches()
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/v1/accounts/google-flow/clean-cache")
    def ai_visual_runtime_clean_cache_v1_alias():
        return ai_visual_runtime_clean_cache()

    @api.delete("/api/cofi-studio/runtime/accounts/{account_id}")
    def ai_visual_runtime_account_delete(account_id: str):
        try:
            return service.ai_visual_runtime_account(account_id, "delete")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/cofi-studio/runtime/accounts/{account_id}/{action}")
    def ai_visual_runtime_account(account_id: str, action: str):
        try:
            return service.ai_visual_runtime_account(account_id, action)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/run/{phase}")
    def run_phase(job_id: str, phase: str):
        try:
            return service.start(job_id, phase)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/resume")
    def resume_job(job_id: str):
        try:
            return service.start(job_id, "all")
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/rerun/{phase}")
    def rerun_phase(job_id: str, phase: str):
        try:
            return service.rerun(job_id, phase)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/pipeline/{from_phase}/{through_phase}")
    def run_pipeline(job_id: str, from_phase: str, through_phase: str):
        try:
            return service.run_pipeline(job_id, from_phase, through_phase)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/logs/{phase}", response_class=PlainTextResponse)
    def logs(
        job_id: str,
        phase: str,
        tail_bytes: int | None = Query(default=None, ge=1024, le=2_000_000),
    ):
        try:
            try:
                return service.phase_log(job_id, phase, tail_bytes=tail_bytes)
            except TypeError:
                return service.phase_log(job_id, phase)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/artifact/{name}", response_class=PlainTextResponse)
    def artifact(job_id: str, name: str):
        try:
            return service.read_artifact(job_id, name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"Chưa có artifact {name}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/media")
    def job_media(
        job_id: str,
        path: str = Query(..., min_length=1),
        poster: bool = Query(default=False),
        download: bool = Query(default=False),
        filename: str | None = Query(default=None),
    ):
        try:
            if poster:
                resolved = service.resolve_poster_path(job_id, path)
                if resolved.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                    return FileResponse(resolved, media_type="image/jpeg")
                return Response(content=FALLBACK_POSTER_SVG, media_type="image/svg+xml")
            resolved = service.resolve_media_path(job_id, path)
            ext = resolved.suffix.lower()
            mime_map = {
                ".mp4": "video/mp4",
                ".webm": "video/webm",
                ".mov": "video/quicktime",
                ".mkv": "video/x-matroska",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".gif": "image/gif",
                ".wav": "audio/wav",
                ".mp3": "audio/mpeg",
                ".m4a": "audio/mp4",
                ".srt": "application/x-subrip",
                ".zip": "application/zip",
            }
            media_type = mime_map.get(ext)
            dl_name = str(filename or "").strip()
            if dl_name:
                dl_name = Path(dl_name).name
                if ext and not dl_name.lower().endswith(ext):
                    dl_name = f"{dl_name}{ext}"
            elif resolved.name.lower() == "video.mp4":
                dl_name = f"video_{job_id}.mp4"
            else:
                dl_name = resolved.name
            return FileResponse(
                resolved,
                media_type=media_type,
                filename=dl_name,
                content_disposition_type="attachment" if download else "inline",
            )
        except KeyError as exc:
            if poster:
                return Response(content=FALLBACK_POSTER_SVG, media_type="image/svg+xml")
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except FileNotFoundError as exc:
            if poster:
                return Response(content=FALLBACK_POSTER_SVG, media_type="image/svg+xml")
            raise HTTPException(status_code=404, detail="Không tìm thấy media") from exc
        except ValueError as exc:
            if poster:
                return Response(content=FALLBACK_POSTER_SVG, media_type="image/svg+xml")
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/media/local-action")
    def job_media_local_action(job_id: str, body: dict[str, Any] = Body(default_factory=dict)):
        """Execute direct OS-level file actions (reveal in Explorer or instant local disk copy) without HTTP download streaming."""
        raw_path = str(body.get("path") or "").strip()
        action = str(body.get("action") or "reveal").strip().lower()
        filename = str(body.get("filename") or "").strip() or None
        destination_path = str(body.get("destination_path") or "").strip() or None
        open_folder_after = bool(body.get("open_folder_after", True))
        move = bool(body.get("move", False))
        if not raw_path:
            raise HTTPException(status_code=400, detail="Thiếu đường dẫn media")
        try:
            if action == "reveal":
                return service.reveal_media_in_explorer(job_id, raw_path)
            if action in {"save_copy", "copy", "save", "move", "transfer"}:
                return service.save_local_media_copy(
                    job_id,
                    raw_path,
                    suggested_filename=filename,
                    destination_path=destination_path,
                    open_folder_after=open_folder_after,
                    move=(action in {"move", "transfer"} or move),
                )
            raise HTTPException(status_code=400, detail=f"Hành động không hợp lệ: {action}")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy media") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (RuntimeError, OSError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/live-footage")
    def live_footage(job_id: str):
        try:
            return service.list_live_footage(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.post("/api/jobs/{job_id}/footage/pause")
    def pause_footage(job_id: str):
        try:
            return service.footage_control(job_id, "pause")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/footage/resume")
    def resume_footage(job_id: str):
        try:
            return service.footage_control(job_id, "resume")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/footage/stop")
    def stop_footage(job_id: str):
        try:
            return service.footage_control(job_id, "stop")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/remotion")
    def remotion_status(job_id: str):
        try:
            return service.remotion_status(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.get("/api/jobs/{job_id}/export-progress")
    def export_progress(job_id: str):
        try:
            return service.export_progress(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.post("/api/jobs/{job_id}/remotion/start")
    def remotion_start(job_id: str):
        try:
            return service.start_remotion(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/edit-chat")
    def edit_chat_history(job_id: str):
        try:
            return service.edit_chat_history(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.post("/api/jobs/{job_id}/edit-chat")
    def edit_chat(job_id: str, body: EditChatRequest):
        try:
            return service.edit_chat(
                job_id,
                body.message,
                selected_beat_id=body.selected_beat_id,
                selected_timestamp_sec=body.selected_timestamp_sec,
                attachment_ids=body.attachment_ids,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/producer-chat")
    def producer_chat_history(selected_job_id: str | None = Query(default=None)):
        try:
            return service.producer_chat_history(selected_job_id=selected_job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.delete("/api/producer-chat")
    def clear_producer_chat_history(selected_job_id: str | None = Query(default=None)):
        try:
            return service.clear_producer_chat_history(selected_job_id=selected_job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.post("/api/producer-chat/compact")
    def compact_producer_chat_session(selected_job_id: str | None = Query(default=None)):
        try:
            return service.compact_producer_chat_session(selected_job_id=selected_job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/producer-chat/new")
    def new_producer_chat_session(selected_job_id: str | None = Query(default=None)):
        try:
            return service.new_producer_chat_session(selected_job_id=selected_job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/producer-chat/context")
    def producer_chat_context(
        selected_job_id: str | None = Query(default=None),
        app_tab: str | None = Query(default=None),
    ):
        try:
            return service.producer_chat_context(selected_job_id, app_tab)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc

    @api.post("/api/producer-chat")
    def producer_chat(body: ProducerChatRequest):
        try:
            return service.producer_chat(
                body.message,
                selected_job_id=body.selected_job_id,
                app_tab=body.app_tab,
                attachment_ids=body.attachment_ids,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/producer-chat/runs")
    def start_producer_chat_run(body: ProducerChatRequest, request: Request):
        try:
            payload = body.model_dump()
            payload["api_base_url"] = str(request.base_url).rstrip("/")
            return service.start_producer_chat_run(payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.get("/api/producer-chat/runs/active")
    def find_active_producer_chat_run(selected_job_id: str | None = Query(default=None)):
        return service.find_active_producer_chat_run(selected_job_id=selected_job_id)

    @api.get("/api/producer-chat/runs/{run_id}")
    def get_producer_chat_run(run_id: str):
        try:
            return service.get_producer_chat_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat") from exc

    @api.get("/api/producer-chat/runs/{run_id}/events")
    def producer_chat_run_events(run_id: str, after: int = Query(default=0, ge=0)):
        try:
            service.get_producer_chat_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat") from exc

        def event_stream():
            for event in service.producer_chat_run_events(run_id, after=after):
                yield json.dumps(event, ensure_ascii=False) + "\n"

        return StreamingResponse(event_stream(), media_type="application/x-ndjson")

    @api.post("/api/producer-chat/runs/{run_id}/cancel")
    def cancel_producer_chat_run(run_id: str):
        try:
            return service.cancel_producer_chat_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat") from exc

    @api.post("/api/producer-chat/stream")
    def producer_chat_stream(body: ProducerChatRequest):
        def event_stream():
            queue: Queue[dict[str, Any]] = Queue()

            def emit(line: str) -> None:
                queue.put({"type": "cli_event", "line": str(line or "")[:12000]})

            def worker() -> None:
                try:
                    result = service.producer_chat(
                        body.message,
                        selected_job_id=body.selected_job_id,
                        app_tab=body.app_tab,
                        attachment_ids=body.attachment_ids,
                        log_callback=emit,
                    )
                    queue.put({"type": "result", "result": result})
                except Exception as exc:
                    queue.put({"type": "error", "message": str(exc)})

            Thread(target=worker, daemon=True, name="producer-chat-stream").start()
            yield json.dumps({"type": "started"}, ensure_ascii=False) + "\n"
            while True:
                try:
                    event = queue.get(timeout=10)
                except Empty:
                    yield json.dumps({"type": "heartbeat"}) + "\n"
                    continue
                yield json.dumps(event, ensure_ascii=False) + "\n"
                if event.get("type") in {"result", "error"}:
                    break

        return StreamingResponse(event_stream(), media_type="application/x-ndjson")

    @api.get("/api/source-repairs")
    def source_repairs():
        return service.list_source_repairs()

    @api.get("/api/source-repairs/{repair_id}")
    def source_repair(repair_id: str):
        try:
            return service.get_source_repair(repair_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy repair job") from exc

    @api.post("/api/chat-attachments")
    async def upload_chat_attachment(request: Request, filename: str = Query(default="image", max_length=240)):
        try:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > service.CHAT_IMAGE_MAX_BYTES:
                raise ValueError("Ảnh vượt quá 10 MB.")
            data = await request.body()
            return service.save_chat_attachment(data, filename, request.headers.get("content-type"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/chat-attachments/{attachment_id}")
    def chat_attachment_file(attachment_id: str):
        try:
            attachment = service.chat_attachment(attachment_id)
            return FileResponse(
                service.resolve_chat_attachment_path(attachment_id),
                media_type=attachment.get("mime_type"),
                filename=attachment.get("name"),
                content_disposition_type="inline",
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy ảnh đính kèm") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/voice/voices")
    def voice_options():
        try:
            return service.voice_options()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"CofiVoice chưa sẵn sàng: {exc}") from exc

    @api.post("/api/voice/start")
    def voice_start():
        try:
            return service.start_voice_backend()
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @api.post("/api/voice/clone")
    async def voice_clone(
        request: Request,
        name: str = Query(default="", max_length=160),
        language: str = Query(default="vi", max_length=16),
        ref_text: str = Query(default="", max_length=2000),
        filename: str = Query(default="sample.wav", max_length=240),
        recorded: bool = Query(default=False),
    ):
        try:
            content_type = (request.headers.get("content-type") or "").lower()
            if "application/json" in content_type:
                import base64 as _b64
                payload = await request.json()
                name = str(payload.get("name") or name).strip()
                language = str(payload.get("language") or language or "vi").strip()
                ref_text = str(payload.get("ref_text") or ref_text or "").strip()
                filename = str(payload.get("filename") or filename or "sample.wav").strip()
                recorded = bool(payload.get("recorded", recorded))
                raw_b64 = str(payload.get("audio_base64") or payload.get("data_url") or "").strip()
                if "," in raw_b64 and raw_b64.startswith("data:"):
                    raw_b64 = raw_b64.split(",", 1)[1]
                audio_bytes = _b64.b64decode(raw_b64) if raw_b64 else b""
            else:
                audio_bytes = await request.body()
            return service.clone_voice(
                name=name,
                language=language,
                audio_bytes=audio_bytes,
                filename=filename,
                ref_text=ref_text or None,
                recorded=recorded,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không thể clone giọng nói: {exc}") from exc

    @api.post("/api/voice/design")
    def voice_design(body: VoiceDesignRequest):
        try:
            return service.design_voice(
                name=body.name,
                language=body.language,
                instruct=body.instruct,
                auto_preview=body.auto_preview,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không thể thiết kế giọng nói: {exc}") from exc

    @api.post("/api/voice/voices/{voice_id}/preview")
    def voice_generate_preview(voice_id: str):
        try:
            return service.preview_voice(voice_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tạo được mẫu nghe thử: {exc}") from exc

    @api.get("/api/voice/preview-audio/{voice_id}")
    def voice_preview_audio(voice_id: str):
        try:
            path = service.resolve_voice_preview_path(voice_id)
            return FileResponse(path, media_type="audio/wav", filename=f"{voice_id}.wav")
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được mẫu nghe thử: {exc}") from exc

    @api.post("/api/voice/tts-preview")
    def voice_tts_preview(body: VoiceTtsPreviewRequest):
        try:
            wav_bytes = service.synthesize_voice_sample(
                text=body.text,
                voice_id=body.voice_id,
                language=body.language,
                speed=body.speed,
                mode=body.mode,
            )
            return Response(content=wav_bytes, media_type="audio/wav")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không đọc thử được câu mẫu: {exc}") from exc

    @api.delete("/api/voice/voices/{voice_id}")
    def voice_delete(voice_id: str):
        try:
            return service.delete_voice(voice_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không xóa được giọng nói: {exc}") from exc

    @api.get("/api/radar/scans")
    def radar_scans(limit: int = Query(default=20, ge=1, le=100)):
        try:
            return service.radar_scans(limit)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"COFI RADAR chưa sẵn sàng: {exc}") from exc

    @api.get("/api/radar/scans/{scan_id}/videos")
    def radar_videos(scan_id: int):
        try:
            return service.radar_videos(scan_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được video Radar: {exc}") from exc

    @api.get("/api/radar/scans/{scan_id}/feed")
    def radar_market_feed(scan_id: int):
        try:
            return service.radar_market_feed(scan_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được feed Radar: {exc}") from exc

    @api.post("/api/radar/translate")
    def radar_translate(body: RadarTranslateRequest):
        try:
            return service.radar_translate(body.texts)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không dịch được dữ liệu Radar: {exc}") from exc

    @api.get("/api/radar/scans/{scan_id}")
    def radar_scan(scan_id: int):
        try:
            return service.radar_scan(scan_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được lượt quét Radar: {exc}") from exc

    @api.post("/api/radar/scans/market")
    def radar_market_scan(body: RadarMarketScanRequest):
        try:
            return service.radar_market_scan(body.model_dump())
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Quét thị trường thất bại: {exc}") from exc

    @api.post("/api/radar/scans/channel")
    def radar_channel_scan(body: RadarChannelScanRequest):
        try:
            return service.radar_channel_scan(body.model_dump())
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Quét kênh thất bại: {exc}") from exc

    @api.post("/api/radar/channels/discover")
    def radar_channel_discover(body: RadarChannelDiscoveryRequest):
        try:
            return service.radar_channel_discover(body.model_dump())
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Quét chủ đề theo DNA kênh thất bại: {exc}") from exc

    @api.get("/api/radar/niches")
    def radar_niches(scan_id: int | None = None):
        try:
            return service.radar_niches(scan_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được ngách: {exc}") from exc

    @api.get("/api/radar/niches/{niche_id}")
    def radar_niche_detail(niche_id: int):
        try:
            return service.radar_niche_detail(niche_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được bằng chứng ngách: {exc}") from exc

    @api.post("/api/radar/niches/{niche_id}/save")
    def radar_save_niche(niche_id: int, body: RadarSaveNicheRequest):
        try:
            return service.radar_save_niche(niche_id, note=body.note)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không lưu được ngách Radar: {exc}") from exc

    @api.get("/api/radar/my-channels")
    def radar_my_channels():
        try:
            return service.radar_my_channels()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được kênh: {exc}") from exc

    @api.get("/api/radar/today")
    def radar_today():
        try:
            return service.radar_today()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được hàng đợi hôm nay: {exc}") from exc

    @api.get("/api/radar/channel-profiles")
    def channel_profiles():
        return service.list_channel_profiles()

    @api.post("/api/radar/channel-profiles")
    def create_channel_profile(body: ChannelProfileRequest):
        try:
            return service.save_channel_profile(body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tạo được hồ sơ kênh: {exc}") from exc

    @api.patch("/api/radar/channel-profiles/{profile_id}")
    def update_channel_profile(profile_id: str, body: ChannelProfileRequest):
        try:
            return service.save_channel_profile(body.model_dump(), profile_id=profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không cập nhật được hồ sơ kênh: {exc}") from exc

    @api.delete("/api/radar/channel-profiles/{profile_id}")
    def delete_channel_profile(profile_id: str):
        try:
            return service.delete_channel_profile(profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không xóa được hồ sơ kênh: {exc}") from exc

    @api.get("/api/radar/channel-profiles/{profile_id}/topic-memory")
    def get_channel_profile_topic_memory(profile_id: str):
        try:
            items = service.get_channel_profile_topic_memory(profile_id)
            return {"profile_id": profile_id, "topic_memory": items, "items": items, "count": len(items)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được bộ nhớ đề tài: {exc}") from exc

    @api.post("/api/radar/channel-profiles/{profile_id}/topic-memory")
    async def add_channel_profile_topic_memory(profile_id: str, request: Request):
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Payload must be a JSON object")
            entry = service.add_channel_profile_topic_memory(profile_id, body)
            items = service.get_channel_profile_topic_memory(profile_id)
            return {"status": "ok", "entry": entry, "items": items, "count": len(items)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không thêm được đề tài vào bộ nhớ: {exc}") from exc

    @api.delete("/api/radar/channel-profiles/{profile_id}/topic-memory/{entry_id}")
    def delete_channel_profile_topic_memory(profile_id: str, entry_id: str):
        try:
            res = service.delete_channel_profile_topic_memory(profile_id, entry_id)
            items = service.get_channel_profile_topic_memory(profile_id)
            return {"status": "ok", "deleted_entry_id": entry_id, "items": items, "count": len(items)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy đề tài trong bộ nhớ") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không xóa được đề tài khỏi bộ nhớ: {exc}") from exc

    @api.post("/api/radar/channel-profiles/{profile_id}/refresh")
    def refresh_channel_profile(profile_id: str):
        try:
            return service.refresh_channel_profile(profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không quét lại được hồ sơ kênh: {exc}") from exc

    @api.post("/api/radar/channel-profiles/{profile_id}/today")
    def channel_profile_today(
        profile_id: str,
        target_duration_minutes: float | None = Query(default=None, ge=2, le=180),
        discovery_mode: str | None = Query(default=None),
        force_refresh: bool = Query(default=False),
        topic_stream: str | None = Query(default=None),
        reset_history: bool = Query(default=False),
        body: dict[str, Any] | None = Body(default=None),
    ):
        payload = body if isinstance(body, dict) else {}
        resolved_stream = str(topic_stream or payload.get("topic_stream") or "").strip() or None
        resolved_reset = bool(reset_history or payload.get("reset_history"))
        raw_exclude = payload.get("exclude_titles")
        exclude_titles = (
            [str(x).strip() for x in raw_exclude if str(x).strip()]
            if isinstance(raw_exclude, list)
            else None
        )
        try:
            return service.channel_profile_today(
                profile_id,
                target_duration_minutes=target_duration_minutes,
                discovery_mode=discovery_mode,
                force_refresh=force_refresh,
                topic_stream=resolved_stream,
                exclude_titles=exclude_titles,
                reset_history=resolved_reset,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            service.mark_channel_profile_activity_error(profile_id, exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            service.mark_channel_profile_activity_error(profile_id, exc)
            raise HTTPException(status_code=502, detail=f"Không gợi ý được video hôm nay: {exc}") from exc

    @api.delete("/api/radar/channel-profiles/{profile_id}/suggested-topic-history")
    def clear_channel_profile_suggested_history(profile_id: str):
        try:
            return service.clear_suggested_topic_history(profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không xóa được lịch sử gợi ý: {exc}") from exc

    @api.get("/api/radar/channel-profiles/{profile_id}/activity")
    def channel_profile_activity(profile_id: str):
        try:
            return service.channel_profile_activity(profile_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc

    @api.post("/api/radar/channel-profiles/{profile_id}/plan-30-days")
    def create_channel_profile_plan(
        profile_id: str,
        rebuild: bool = Query(default=False),
        refresh_codex: bool = Query(default=True),
    ):
        try:
            return service.channel_profile_plan(profile_id, rebuild=rebuild, refresh_codex=refresh_codex)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            service.mark_channel_profile_activity_error(profile_id, exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            service.mark_channel_profile_activity_error(profile_id, exc)
            raise HTTPException(status_code=502, detail=f"Không tạo được kế hoạch 30 ngày: {exc}") from exc

    @api.get("/api/radar/channel-profiles/{profile_id}/plan")
    def get_channel_profile_plan(profile_id: str):
        try:
            return service.channel_profile_plan(profile_id, rebuild=False, refresh_profile=False)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không tải được kế hoạch kênh: {exc}") from exc

    @api.patch("/api/radar/channel-profiles/{profile_id}/plan-items/{item_id}")
    def update_channel_profile_plan_item(profile_id: str, item_id: int, body: ChannelPlanStatusRequest):
        try:
            return service.update_channel_profile_plan_item(profile_id, item_id, body.status)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ kênh") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không cập nhật được tiến độ kế hoạch: {exc}") from exc

    # ------------------------------------------------------------------
    # CREATIVE STUDIO, PLAYBOOKS, OUTLINES & PITCHING ROUTES
    # ------------------------------------------------------------------

    @api.get("/api/creative/catalog")
    def get_creative_catalog():
        return service.creative_catalog()

    @api.get("/api/creative/draft")
    def get_creative_draft():
        return service.get_ui_draft()

    @api.post("/api/creative/draft")
    async def update_creative_draft(request: Request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        return service.update_ui_draft(payload)

    @api.post("/api/jobs/{job_id}/approve-next")
    def approve_next_phase(job_id: str):
        try:
            return service.approve_next_phase(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.post("/api/creative/pitch-angles")
    def pitch_creative_angles(body: PitchAnglesRequest):
        try:
            return service.pitch_creative_angles(body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Không tạo được đề xuất góc nhìn: {exc}") from exc

    @api.get("/api/playbooks")
    def list_playbooks():
        items = service.list_playbooks()
        return {"items": items, "playbooks": items}

    @api.post("/api/playbooks")
    def save_playbook(body: PlaybookRequest):
        try:
            return service.save_playbook(body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.delete("/api/playbooks/{playbook_id}")
    def delete_playbook(playbook_id: str):
        try:
            return service.delete_playbook(playbook_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/extract-playbook")
    def extract_playbook_from_job(job_id: str, body: ExtractPlaybookRequest | None = None):
        try:
            return service.extract_playbook_from_job(job_id, body.model_dump(exclude_none=True) if body else None)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.patch("/api/jobs/{job_id}/creative-brief")
    def update_job_creative_brief(job_id: str, body: CreativeBriefRequest):
        try:
            return service.update_creative_brief(job_id, body.model_dump(exclude_none=True))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/api/jobs/{job_id}/outline")
    def get_job_outline(job_id: str):
        try:
            return service.get_job_outline(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc

    @api.patch("/api/jobs/{job_id}/outline")
    def update_job_outline(job_id: str, body: OutlineUpdateRequest):
        try:
            return service.update_job_outline(job_id, body.model_dump())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/outline/generate")
    def generate_job_outline(job_id: str, body: OutlineGenerateRequest | None = None):
        try:
            return service.generate_job_outline(job_id, body.model_dump(exclude_none=True) if body else None)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.put("/api/jobs/{job_id}/script")
    def update_job_script(job_id: str, body: ScriptUpdateRequest):
        try:
            return service.update_job_script(job_id, body.model_dump(exclude_none=True))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # ------------------------------------------------------------------
    # THUMBNAIL STUDIO ROUTES (FABRIC.JS LAYER ENGINE + NANOTHUMBNAIL)
    # ------------------------------------------------------------------

    @api.get("/api/jobs/{job_id}/thumbnail-studio")
    def get_thumbnail_studio(job_id: str):
        try:
            return service.thumbnail_studio_state(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/design")
    async def save_thumbnail_studio_design(job_id: str, request: Request):
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                payload = {}
            return service.save_thumbnail_design(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/auto-design")
    async def auto_design_thumbnail_studio(job_id: str, request: Request):
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            return service.auto_design_thumbnail(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/generate-bg")
    async def generate_thumbnail_studio_bg(job_id: str, request: Request):
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            return service.generate_thumbnail_background(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/upload-image")
    async def upload_thumbnail_studio_image(job_id: str, request: Request):
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("Payload không hợp lệ")
            return service.upload_thumbnail_image(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/export")
    async def export_thumbnail_studio_image(job_id: str, request: Request):
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("Payload không hợp lệ")
            return service.export_thumbnail_image(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/export-ab-pack")
    async def export_thumbnail_ab_pack_route(job_id: str, request: Request):
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            return service.export_thumbnail_ab_pack(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/thumbnail-studio/select-winner")
    async def select_thumbnail_winner_route(job_id: str, request: Request):
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            return service.select_thumbnail_winner(job_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/jobs/{job_id}/lock-thumbnail-dna")
    async def lock_job_thumbnail_dna_route(job_id: str, request: Request):
        try:
            notes = ""
            overrides: dict = {}
            try:
                body = await request.json()
                if isinstance(body, dict):
                    notes = str(body.get("notes") or body.get("override_name") or "")
                    overrides = body
            except Exception:
                pass
            from services.thumbnail_dna_service import ThumbnailDnaService
            tds = ThumbnailDnaService()
            return tds.lock_job_thumbnail_dna_to_channel(job_id, notes=notes, overrides=overrides)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/api/radar/channel-profiles/{profile_id}/lock-thumbnail-dna")
    async def lock_channel_profile_thumbnail_dna_route(profile_id: str, request: Request):
        try:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            from services.thumbnail_dna_service import ThumbnailDnaService
            tds = ThumbnailDnaService()
            return tds.lock_channel_profile_thumbnail_dna(profile_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


    @api.get("/api/agent-departments")
    @api.get("/api/agency/departments")
    @api.get("/api/agents/departments")
    def get_agent_departments_legacy(job_id: str | None = None):
        return service.get_agent_departments(job_id=job_id)

    @api.post("/api/agent-departments/dispatch-parallel")
    @api.post("/api/agency/dispatch-parallel")
    @api.post("/api/agents/dispatch-parallel")
    async def dispatch_agent_departments_parallel_legacy(
        request: Request,
        dept_id: str | None = Query(default=None),
        job_id: str | None = Query(default=None),
    ):
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        eff_dept = body.get("dept_id") or body.get("department_id") or body.get("agent_id") or dept_id or "all"
        eff_job = body.get("job_id") or body.get("selected_job_id") or job_id
        return _execute_department_parallel_dispatch_safe(service, dept_id=eff_dept, job_id=eff_job)

    @api.get("/api/agency/office-live")
    @api.get("/api/studio/office-live")
    def get_agency_office_live_legacy(job_id: str | None = None, pinned: bool = False):
        from documentary.agent_office import build_live_office_snapshot

        return build_live_office_snapshot(service, job_id=job_id, pinned=bool(pinned))

    @api.get("/api/state")
    def get_studio_state_legacy(job_id: str | None = None):
        from documentary.agent_office import build_live_office_snapshot

        office_snap = build_live_office_snapshot(service, job_id=job_id)
        return {
            "status": "ok",
            "selected_job": office_snap.get("selected_job"),
            "jobs": office_snap.get("jobs_list", []),
            "agent_office": office_snap,
            "agent_departments": office_snap.get("departments", []),
            "agent_departments_summary": office_snap.get("departments_summary", {}),
        }

    @api.get("/")
    def index():
        path = STATIC_DIR / "index.html"
        if path.exists():
            return Response(
                content=_render_index_html_with_parallel_stage(path),
                media_type="text/html; charset=utf-8",
            )
        return {"app": "COFI DOCUMENTARY", "api": "/api/health"}

    @api.on_event("startup")
    def startup_required_backends():
        starter = getattr(service, "start_required_backends", None)
        if callable(starter):
            api.state.required_backends = starter()

    @api.on_event("shutdown")
    def shutdown_embedded_tools():
        service.stop_cofi_studio_embed()

    return api


_default_app: FastAPI | None = None


async def app(scope, receive, send):
    """Lazy ASGI entrypoint so importing this module never mutates production job state."""
    global _default_app
    if _default_app is None:
        from server import create_app as create_modular_app
        _default_app = create_modular_app()
    await _default_app(scope, receive, send)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("COFI_DOCUMENTARY_PORT", "8878")), reload=False)
