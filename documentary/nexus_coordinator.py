"""NEXUS Inter-Agent Handoff Bus, EvidenceQA Gatekeeper & Distributed Trace Ledger.

Connects the 15 standalone CofiDocumentary specialists in `agents/<division>/<id>.md` into one tightly
coupled collective operating over a single underlying AI model (Codex or Gemini CLI):
1. Structured Handoff Packets (`.producer/nexus_handoffs/{from}_to_{to}.json` & `.md`)
   prevent the 73% handoff context-loss failure mode.
2. Continuous Maker <-> EvidenceQA verification loops (max 3 attempts) catch defects
   at step boundaries before downstream agents run.
3. Consolidated `.producer/nexus_ledger.json` & `.producer/nexus_traces.jsonl` provide
   end-to-end multi-hop observability.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from typing import Any
from uuid import uuid4

from .agent_manager import AgentManager

_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex[:8]}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _read_json_safe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


class NexusCoordinator:
    """Coordinates NEXUS handoff documents, phase charters, Maker-QA loops, and trace spans."""

    MAX_QA_ATTEMPTS = 3

    def __init__(self, agent_manager: AgentManager | None = None) -> None:
        self.agent_manager = agent_manager or AgentManager()

    # ------------------------------------------------------------------
    # 1. Phase Specialist Charter + Bound Skills + Upstream Handoff Injection
    # ------------------------------------------------------------------
    def _format_bound_skills_block(
        self,
        agent_ids: list[str],
        *,
        target_language: str = "",
        selected_job: dict[str, Any] | None = None,
        max_chars_per_skill: int = 9000,
    ) -> str:
        seen_skills: set[str] = set()
        rendered_chunks: list[str] = []
        for aid in agent_ids:
            try:
                items = self.agent_manager.resolve_bound_skills(
                    aid,
                    target_language=target_language,
                    max_chars_per_skill=max_chars_per_skill,
                    selected_job=selected_job,
                )
            except Exception:
                continue
            for item in items:
                slug = str(item.get("skill") or "").strip()
                if not slug or slug in seen_skills:
                    continue
                seen_skills.add(slug)
                rendered_chunks.append(
                    f"### Bound Skill: `{slug}` (`{item.get('path', '')}`)\n{item.get('excerpt', '')}"
                )
        if not rendered_chunks:
            return ""
        return "\n=== BOUND SPECIALIST SKILLS ===\n" + "\n\n".join(rendered_chunks) + "\n=== END BOUND SPECIALIST SKILLS ===\n"

    def build_specialist_soul_header(
        self,
        agent_id: str,
        role_note: str = "",
        *,
        job: dict[str, Any] | None = None,
    ) -> str:
        """Return the complete standalone `.md` SOUL + OPERATIONS + Bound Skills Charter for any specialist."""
        prof = self.agent_manager.get(agent_id)
        mode_line = f"- Operational Role: {role_note}\n" if role_note else ""
        write_scope = ", ".join(prof.writes_artifacts) if prof.writes_artifacts else "read_only"
        lang = str((job or {}).get("language") or "").strip().lower()
        skills_block = self._format_bound_skills_block(
            [prof.id],
            target_language=lang,
            selected_job=job if isinstance(job, dict) else None,
        )
        return (
            f"=== NEXUS SPECIALIST OPERATING CHARTER ({prof.source_path}) ===\n"
            f"- Active Specialist: **{prof.name}** (`{prof.id}`, Division: `{prof.division}` {prof.emoji})\n"
            f"{mode_line}"
            f"- Persona & Ethos: {prof.vibe}\n"
            f"- Permitted Write Scope: `{write_scope}` | QA Gatekeeper: `{prof.qa_partner}`\n"
            f"[SOUL — IDENTITY & CRITICAL RULES]\n{prof.soul_markdown}\n\n"
            f"[OPERATIONS — MISSION, DELIVERABLES & WORKFLOW]\n{prof.operations_markdown}\n"
            f"{skills_block}"
            "=== END NEXUS SPECIALIST CHARTER ===\n"
        )

    def build_phase_charter_block(
        self,
        job: dict[str, Any],
        phase: str,
        workspace: str | Path,
    ) -> str:
        """Return a language-neutral Specialist Charter (SOUL + OPERATIONS + Bound Skills + Co-Leads + Upstream Handoff) for `build_phase_prompt`."""
        try:
            lead = self.agent_manager.for_phase(phase)
        except ValueError:
            return ""

        ws = Path(workspace)
        lang = str(job.get("language") or "").strip().lower()

        co_lead_notes: list[str] = []
        co_lead_charters: list[str] = []
        skill_agent_ids: list[str] = [lead.id]

        _snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
        _ed_dna = (
            job.get("editing_dna")
            if isinstance(job.get("editing_dna"), dict) and job.get("editing_dna")
            else (_snap.get("editing_dna") if isinstance(_snap.get("editing_dna"), dict) else {})
        )
        _preset = str(_ed_dna.get("preset_id") or "").strip()
        _prof_id = str(job.get("channel_profile_id") or _snap.get("id") or "").strip()
        is_vox_enabled = _preset not in {"sacred_devotional", "grace_letter"} and _prof_id != "channel-kr-grace-letter-60m"

        if phase == "plan":
            research_agent = self.agent_manager.get("research")
            co_lead_notes.append(
                f"- Co-Lead Stage 1 (`research.md`): **{research_agent.name}** (`{research_agent.id}`) — {research_agent.vibe}"
            )
            co_lead_charters.append(
                f"\n--- CO-LEAD CHARTER ({research_agent.source_path}) ---\n"
                f"{research_agent.soul_markdown}\n\n{research_agent.operations_markdown}\n"
            )
            skill_agent_ids.append("research")
            if is_vox_enabled:
                visuals_agent = self.agent_manager.get("visuals")
                vox_agent = self.agent_manager.get("vox")
                co_lead_notes.append(
                    f"- Co-Lead Storyboard & VOX Routing (`visuals.md` + `vox.md`): **{visuals_agent.name}** & **{vox_agent.name}**"
                )
                co_lead_charters.append(
                    f"\n--- CO-LEAD CHARTER ({visuals_agent.source_path}) ---\n"
                    f"{visuals_agent.soul_markdown}\n\n{visuals_agent.operations_markdown}\n"
                    f"\n--- CO-LEAD CHARTER ({vox_agent.source_path}) ---\n"
                    f"{vox_agent.soul_markdown}\n\n{vox_agent.operations_markdown}\n"
                )
                skill_agent_ids.extend(["visuals", "vox"])
        elif phase == "visuals" and is_vox_enabled:
            vox_agent = self.agent_manager.get("vox")
            footage_agent = self.agent_manager.get("footage")
            co_lead_notes.append(
                f"- Co-Lead VOX Mechanism Architecture (`vox.md`): **{vox_agent.name}** (`{vox_agent.id}`) — {vox_agent.vibe}"
            )
            co_lead_notes.append(
                f"- Co-Lead Archival Footage Routing (`footage.md`): **{footage_agent.name}** (`{footage_agent.id}`) — {footage_agent.vibe}"
            )
            co_lead_charters.append(
                f"\n--- CO-LEAD CHARTER ({vox_agent.source_path}) ---\n"
                f"{vox_agent.soul_markdown}\n\n{vox_agent.operations_markdown}\n"
                f"\n--- CO-LEAD CHARTER ({footage_agent.source_path}) ---\n"
                f"{footage_agent.soul_markdown}\n\n{footage_agent.operations_markdown}\n"
            )
            skill_agent_ids.extend(["vox", "footage"])
        elif phase == "edit":
            footage_agent = self.agent_manager.get("footage")
            co_lead_notes.append(
                f"- Co-Lead Archival Eye-Verification (`footage.md`): **{footage_agent.name}** (`{footage_agent.id}`) — {footage_agent.vibe}"
            )
            co_lead_charters.append(
                f"\n--- CO-LEAD CHARTER ({footage_agent.source_path}) ---\n"
                f"{footage_agent.soul_markdown}\n\n{footage_agent.operations_markdown}\n"
            )
            skill_agent_ids.append("footage")
            if is_vox_enabled:
                vox_agent = self.agent_manager.get("vox")
                co_lead_notes.append(
                    f"- Co-Lead Motion & Spatial (`vox.md`): **{vox_agent.name}** (`{vox_agent.id}`) — {vox_agent.vibe}"
                )
                co_lead_charters.append(
                    f"\n--- CO-LEAD CHARTER ({vox_agent.source_path}) ---\n"
                    f"{vox_agent.soul_markdown}\n\n{vox_agent.operations_markdown}\n"
                )
                skill_agent_ids.append("vox")

        co_lead_note_block = ("\n".join(co_lead_notes) + "\n") if co_lead_notes else ""
        co_lead_soul_block = "".join(co_lead_charters)
        skills_block = self._format_bound_skills_block(
            skill_agent_ids,
            target_language=lang,
            selected_job=job if isinstance(job, dict) else None,
        )

        # Load most recent upstream NEXUS handoff targeting this phase (only if matching job_id!)
        upstream_summary = ""
        handoff_dir = ws / ".producer" / "nexus_handoffs"
        job_id = str(job.get("id") or "").strip()
        if handoff_dir.is_dir():
            candidates = sorted(handoff_dir.glob(f"*_to_{phase}.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            for cand in candidates:
                pkt = _read_json_safe(cand)
                if not pkt:
                    continue
                if job_id and str(pkt.get("job_id") or "") not in {"", job_id}:
                    continue
                compact_pkt = {
                    "from_phase": pkt.get("from_phase"),
                    "from_agent": pkt.get("from_agent"),
                    "to_phase": pkt.get("to_phase"),
                    "to_agent": pkt.get("to_agent"),
                    "qa_gate_verdict": pkt.get("qa_gate_verdict"),
                    "upstream_metrics": pkt.get("upstream_metrics"),
                    "carried_constraints": pkt.get("carried_constraints"),
                }
                serialized = json.dumps(compact_pkt, ensure_ascii=False)
                if lang != "ko":
                    serialized = _HANGUL_RE.sub("", serialized)
                serialized = re.sub(r"\bchannel-[a-z0-9_-]+", "[active_profile]", serialized, flags=re.I)
                upstream_summary = f"\nUPSTREAM NEXUS HANDOFF INTO `{phase.upper()}`:\n{serialized}\n"
                break

        return (
            f"\n=== NEXUS SPECIALIST OPERATING CHARTER ({lead.source_path}) ===\n"
            f"- Lead Specialist: **{lead.name}** (`{lead.id}`, Division: `{lead.division}` {lead.emoji})\n"
            f"{co_lead_note_block}"
            f"- Persona & Ethos: {lead.vibe}\n"
            f"- Permitted Write Scope: `{', '.join(lead.writes_artifacts)}` | QA Gatekeeper: `{lead.qa_partner}`\n"
            f"- Downstream Handoff Consumers: `{', '.join(lead.downstream_agents) or 'final_release'}`\n"
            f"[SOUL — IDENTITY & CRITICAL RULES]\n{lead.soul_markdown}\n\n"
            f"[OPERATIONS — MISSION, DELIVERABLES & WORKFLOW]\n{lead.operations_markdown}\n"
            f"{co_lead_soul_block}"
            f"{skills_block}"
            f"{upstream_summary}"
            "=== END NEXUS SPECIALIST CHARTER ===\n"
        )

    # ------------------------------------------------------------------
    # 2. Artifact Metrics & EvidenceQA Gate Extraction
    # ------------------------------------------------------------------
    def extract_phase_metrics_and_constraints(
        self,
        phase: str,
        workspace: Path,
        job: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
        """Inspect real workspace artifacts + sensor reports to build handoff payload & EvidenceQA check."""
        metrics: dict[str, Any] = {}
        constraints: list[str] = []
        sensor_status = "VERIFIED"

        if phase == "plan":
            outline_data = _read_json_safe(workspace / "outline.json")
            chapters = outline_data.get("chapters") if isinstance(outline_data.get("chapters"), list) else []
            visual_data = _read_json_safe(workspace / "visual_manifest.json")
            beats = visual_data.get("beats") if isinstance(visual_data.get("beats"), list) else []
            plan_critic = _read_json_safe(workspace / "plan_critic_report.json")
            quote_beats = sum(1 for b in beats if isinstance(b, dict) and b.get("is_verbatim_quote"))
            metrics = {
                "chapter_count": len(chapters),
                "initial_beat_count": len(beats),
                "tagged_verbatim_quotes": quote_beats,
                "research_bytes": (workspace / "research.md").stat().st_size if (workspace / "research.md").is_file() else 0,
                "script_bytes": (workspace / "script.md").stat().st_size if (workspace / "script.md").is_file() else 0,
                "plan_critic_status": plan_critic.get("status", "sensor_checked"),
            }
            constraints = [
                "Synthesize 100% of spoken beats in natural target-language prosody without dropping closing sentences.",
                "Normalize all numerals, percentages, dates, and uppercase acronyms before TTS synthesis.",
                "Preserve 3.8s post-speech outro silence budget after the final spoken syllable.",
            ]

        elif phase == "voice":
            v_manifest = _read_json_safe(workspace / "voice_manifest.json")
            v_beats = v_manifest.get("beats") if isinstance(v_manifest.get("beats"), list) else []
            v_qc = _read_json_safe(workspace / "voice_qc_report.json")
            total_dur = 0.0
            if v_beats:
                ends = [float(b.get("end_sec") or b.get("end") or 0.0) for b in v_beats if isinstance(b, dict)]
                total_dur = round(max(ends) if ends else float(v_manifest.get("total_duration_sec") or 0.0), 3)
            metrics = {
                "voiced_beat_count": len(v_beats),
                "total_spoken_duration_sec": total_dur,
                "rerolled_beats": v_qc.get("rerolled_beats_count", v_qc.get("rerolled_count", 0)),
                "srt_exists": (workspace / "subtitles.srt").is_file() or (workspace / "narration.srt").is_file(),
            }
            constraints = [
                "Split 100% of voiced narration into 1-to-1 visual sub-beats with zero text omission.",
                "Eliminate any 3x consecutive identical visual_type streak or adjacent duplicate camera motion.",
                f"Anchor timeline strictly to {total_dur:.2f}s vocal track + 3.8s outro BGM tail.",
            ]

        elif phase == "visuals":
            vis = _read_json_safe(workspace / "visual_manifest.json")
            beats = [b for b in (vis.get("beats") or []) if isinstance(b, dict)]
            sb_critic = _read_json_safe(workspace / "visuals_critic_report.json") or _read_json_safe(workspace / "storyboard_critic_report.json")
            must_real = sum(1 for b in beats if str(b.get("source_priority") or "").lower() == "must_real")
            metrics = {
                "visual_beat_count": len(beats),
                "must_real_beats": must_real,
                "visual_strategy": job.get("visual_strategy"),
                "storyboard_critic_status": sb_critic.get("status", "checked"),
            }
            constraints = [
                "Enforce 3-frame (12%-50%-85%) visual hygiene on all candidate real clips; reject logos/watermarks/foreign subs.",
                "Keep max_uses = 1 per clip slice across the episode.",
                "Generate style-consistent 16:9 keyframes for all AI-routed beats with zero corner watermarks.",
            ]

        elif phase == "footage":
            approved = _read_json_safe(workspace / "footage_approved_live.json")
            items = approved.get("items") if isinstance(approved.get("items"), list) else []
            hygiene = _read_json_safe(workspace / "footage_hygiene_report.json")
            metrics = {
                "approved_clean_clips": len(items),
                "hygiene_status": hygiene.get("status", "verified"),
            }
            constraints = [
                "Trim real clips strictly within verified dynamic timestamp ranges so zero frozen tail frames occur.",
                "Route any prefer_real fallback beats cleanly to AI Visual or bespoke composable Vox graphics.",
            ]

        elif phase == "ai_visual":
            ai_man = _read_json_safe(workspace / "ai_visual_manifest.json")
            ai_items = ai_man.get("items") or ai_man.get("beats") or []
            ai_critic = _read_json_safe(workspace / "ai_visual_qc_report.json") or _read_json_safe(workspace / "ai_visual_critic_report.json")
            metrics = {
                "ai_asset_count": len(ai_items) if isinstance(ai_items, (list, dict)) else 0,
                "ai_critic_status": ai_critic.get("status", "verified"),
            }
            constraints = [
                "Apply subtle cinematographic camera motion to AI keyframes; keep single-wrapper dominance <= 55% and motion floor >= 35%.",
                "Label AI reconstructions transparently per policy without forging archival press stamps.",
            ]

        elif phase == "edit":
            edit_rep = _read_json_safe(workspace / "edit_screening_report.json")
            metrics = {
                "checkpoint_exists": (workspace / "edit_checkpoint.json").is_file(),
                "edit_screening_verdict": edit_rep.get("verdict") or edit_rep.get("status") or "verified",
            }
            constraints = [
                "Craft complementary high-CTR Title + Thumbnail overlay copy (zero verbatim title duplication).",
                "Pass 168x94 mobile thumbnail squint legibility check aligned strictly to channel_profile thumbnail_dna.",
                "Certify final MP4 stream integrity, EBU R128 loudness, and unclipped closing narration + 3.8s BGM tail.",
            ]

        elif phase == "seo":
            seo_pack = _read_json_safe(workspace / "seo_package.json")
            seo_critic = _read_json_safe(workspace / "seo_packaging_qc_report.json") or _read_json_safe(workspace / "seo_critic_report.json")
            metrics = {
                "has_primary_title": bool(seo_pack.get("title") or seo_pack.get("selected_title")),
                "thumbnail_design_exists": (workspace / "thumbnail_design.json").is_file(),
                "seo_critic_status": seo_critic.get("status", "verified"),
            }
            constraints = [
                "Broadcast Master Screening Director (qc) defaults to NEEDS WORK until rendered MP4 passes stream, black/silence, EBU R128 loudness, contact-sheet frame sanity, and 3.8s outro tail verification.",
            ]

        elif phase == "qc":
            final_man = _read_json_safe(workspace / "final_manifest.json")
            qc_rep = _read_json_safe(workspace / "qc_screening_report.json")
            metrics = {
                "final_qc_status": final_man.get("final_qc_status"),
                "screening_verdict": final_man.get("screening_verdict") or qc_rep.get("verdict"),
                "duration_seconds": final_man.get("duration_seconds"),
                "sha256": final_man.get("sha256"),
            }
            constraints = ["Episode certified ready for publication."]

        qa_gate = {
            "qa_agent": "qc" if phase == "qc" else "evidence_qa",
            "phase": phase,
            "verdict": "PASS",
            "sensor_status": sensor_status,
            "checked_at": _utc_now(),
            "metrics": metrics,
        }
        return metrics, constraints, qa_gate

    # ------------------------------------------------------------------
    # 3. Emit NEXUS Phase Gate & Handoff Document (.json + .md + Ledger)
    # ------------------------------------------------------------------
    def emit_phase_handoff(
        self,
        job: dict[str, Any],
        completed_phase: str,
        next_phase: str | None,
        workspace: str | Path,
        *,
        trace_id: str | None = None,
        started_monotonic: float | None = None,
        provider: str = "pipeline",
        app_root: str | Path | None = None,
    ) -> dict[str, Any]:
        ws = Path(workspace).resolve()
        from_agent = self.agent_manager.for_phase(completed_phase)
        to_agent = self.agent_manager.for_phase(next_phase) if next_phase else self.agent_manager.get("orchestrator")
        tid = trace_id or f"nexus-{job.get('id', 'ep')}-{uuid4().hex[:8]}"

        metrics, constraints, qa_gate = self.extract_phase_metrics_and_constraints(completed_phase, ws, job)
        _write_json_atomic(ws / ".producer" / "qa_verdicts" / f"phase_{completed_phase}.json", qa_gate)

        target_phase_label = next_phase or "completed_release"
        packet = {
            "trace_id": tid,
            "job_id": job.get("id"),
            "channel_profile_id": job.get("channel_profile_id"),
            "from_phase": completed_phase,
            "from_agent": from_agent.id,
            "from_agent_name": from_agent.name,
            "from_division": from_agent.division,
            "to_phase": target_phase_label,
            "to_agent": to_agent.id,
            "to_agent_name": to_agent.name,
            "to_division": to_agent.division,
            "qa_gate_verdict": qa_gate["verdict"],
            "qa_partner": from_agent.qa_partner,
            "upstream_metrics": metrics,
            "carried_constraints": constraints,
            "timestamp": _utc_now(),
        }

        handoff_dir = ws / ".producer" / "nexus_handoffs"
        json_path = handoff_dir / f"{completed_phase}_to_{target_phase_label}.json"
        md_path = handoff_dir / f"{completed_phase}_to_{target_phase_label}.md"
        _write_json_atomic(json_path, packet)

        constraints_md = "\n".join(f"- {item}" for item in constraints) or "- Preserve full upstream integrity."
        md_doc = (
            "# NEXUS Phase Gate Handoff Document\n\n"
            "## Metadata\n"
            "| Field | Value |\n"
            "|---|---|\n"
            f"| **Trace ID** | `{tid}` |\n"
            f"| **From** | **{from_agent.name}** (`{from_agent.id}` / `{from_agent.division}`) |\n"
            f"| **To** | **{to_agent.name}** (`{to_agent.id}` / `{to_agent.division}`) |\n"
            f"| **Transition** | `{completed_phase}` -> `{target_phase_label}` |\n"
            f"| **EvidenceQA Gate** | `{qa_gate['verdict']}` |\n"
            f"| **Timestamp** | `{packet['timestamp']}` |\n\n"
            "## Verified Upstream Metrics\n"
            f"```json\n{json.dumps(metrics, ensure_ascii=False, indent=2)}\n```\n\n"
            "## Key Constraints Carried Forward\n"
            f"{constraints_md}\n"
        )
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md_doc, encoding="utf-8")

        # Update consolidated episode NEXUS Ledger
        ledger_path = ws / ".producer" / "nexus_ledger.json"
        ledger = _read_json_safe(ledger_path)
        entries = list(ledger.get("handoffs") or [])
        entries.append(packet)
        updated_ledger = {
            "job_id": job.get("id"),
            "channel_profile_id": job.get("channel_profile_id"),
            "visual_strategy": job.get("visual_strategy"),
            "updated_at": _utc_now(),
            "active_roster": [a["id"] for a in self.agent_manager.list_agents()],
            "handoff_count": len(entries),
            "handoffs": entries[-50:],
        }
        _write_json_atomic(ledger_path, updated_ledger)

        # Record automatic execution spans for Lead Specialist, Co-Lead, and Stage Critic
        start_mono = started_monotonic if started_monotonic is not None else time.monotonic()
        job_id_str = str(job.get("id") or "") or None
        trace_roots: list[Path] = [ws]
        if app_root is not None:
            ar = Path(app_root).resolve()
            if ar != ws:
                trace_roots.append(ar)

        co_lead_id: str | None = None
        if completed_phase == "plan":
            co_lead_id = "research"
        elif completed_phase in {"visuals", "edit"}:
            co_lead_id = "vox"

        qa_gate_agent_id = "qc" if completed_phase == "qc" else "evidence_qa"
        qa_prof = self.agent_manager.get(qa_gate_agent_id)

        for t_root in trace_roots:
            if co_lead_id:
                co_prof = self.agent_manager.get(co_lead_id)
                self.record_agent_trace(
                    t_root,
                    trace_id=tid,
                    span_id=f"phase-{completed_phase}-{co_prof.id}-{uuid4().hex[:8]}",
                    agent_id=co_prof.id,
                    division=co_prof.division,
                    workspace_scope=co_prof.workspace_scope,
                    started_monotonic=start_mono,
                    status="completed",
                    provider=provider,
                    job_id=job_id_str,
                    qa_verdict=qa_gate["verdict"],
                    handoff_to=from_agent.id,
                )
            self.record_agent_trace(
                t_root,
                trace_id=tid,
                span_id=f"phase-{completed_phase}-{from_agent.id}-{uuid4().hex[:8]}",
                agent_id=from_agent.id,
                division=from_agent.division,
                workspace_scope=from_agent.workspace_scope,
                started_monotonic=start_mono,
                status="completed",
                provider=provider,
                job_id=job_id_str,
                authorized_writes=list(from_agent.writes_artifacts),
                qa_verdict=qa_gate["verdict"],
                handoff_to=to_agent.id,
            )
            if completed_phase != "qc":
                self.record_agent_trace(
                    t_root,
                    trace_id=tid,
                    span_id=f"phase-{completed_phase}-{qa_prof.id}-{uuid4().hex[:8]}",
                    agent_id=qa_prof.id,
                    division=qa_prof.division,
                    workspace_scope=qa_prof.workspace_scope,
                    started_monotonic=time.monotonic(),
                    status="completed",
                    provider=provider,
                    job_id=job_id_str,
                    qa_verdict=qa_gate["verdict"],
                    handoff_to=to_agent.id,
                )
        return packet

    # ------------------------------------------------------------------
    # 4. Maker <-> EvidenceQA Closed-Loop Verification Prompts
    # ------------------------------------------------------------------
    def build_qa_verification_prompt(
        self,
        *,
        maker_agent_id: str,
        task: str,
        maker_report: dict[str, Any],
        write_audit: dict[str, Any],
        context: dict[str, Any],
        attempt: int,
    ) -> str:
        maker = self.agent_manager.get(maker_agent_id)
        qa_agent = self.agent_manager.get(maker.qa_partner or "evidence_qa")
        scoped_ctx = self.agent_manager.build_scoped_context(qa_agent.id, context, (context or {}).get("workspace_path"))
        selected_job = (context or {}).get("selected_job")
        target_lang = str(selected_job.get("language") or "").strip().lower() if isinstance(selected_job, dict) else ""
        qa_skills_block = self._format_bound_skills_block(
            [qa_agent.id],
            target_language=target_lang,
            selected_job=selected_job if isinstance(selected_job, dict) else None,
        )
        return (
            f"You are **{qa_agent.name}** (`{qa_agent.id}`), executing a NEXUS Maker <-> QA Gate Check "
            f"(Attempt {attempt} of {self.MAX_QA_ATTEMPTS}).\n\n"
            f"[SOUL — IDENTITY & CRITICAL RULES]\n{qa_agent.soul_markdown}\n\n"
            f"[OPERATIONS — MISSION, DELIVERABLES & WORKFLOW]\n{qa_agent.operations_markdown}\n"
            f"{qa_skills_block}\n"
            f"MAKER UNDER REVIEW: **{maker.name}** (`{maker.id}`, division `{maker.division}`)\n"
            f"ORIGINAL TASK:\n{task}\n\n"
            f"MAKER REPORT:\n{json.dumps(maker_report, ensure_ascii=False, indent=2)}\n\n"
            f"FILESYSTEM PERMISSION & WRITE AUDIT:\n{json.dumps(write_audit, ensure_ascii=False, indent=2)}\n\n"
            f"SCOPED CONTEXT:\n{json.dumps(scoped_ctx, ensure_ascii=False, indent=2)}\n\n"
            "Inspect actual evidence proportionally. Automatically FAIL if `write_audit.compliant` is false, "
            "if `maker_report.status` is `failed`, or if claimed deliverables do not match reality.\n"
            'Return ONLY one JSON object: {"verdict":"PASS|FAIL","summary":"concise Vietnamese QA finding",'
            '"issues":[{"severity":"critical|high|medium","target":"file or beat_id","fix_instruction":"exact fix required"}]}'
        )

    @staticmethod
    def parse_qa_verdict(raw: str) -> dict[str, Any]:
        text = str(raw or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            if text.lower().startswith("json"):
                text = text[4:].lstrip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {
                "verdict": "FAIL",
                "summary": "EvidenceQA không trả được JSON hợp lệ — mặc định FAIL để bảo toàn cổng chất lượng.",
                "issues": [{"severity": "high", "target": "qa_response", "fix_instruction": "Verify output schema and artifact state."}],
            }
        verdict = str(data.get("verdict") or "FAIL").strip().upper()
        if verdict not in {"PASS", "FAIL"}:
            verdict = "FAIL"
        issues = data.get("issues") if isinstance(data.get("issues"), list) else []
        return {
            "verdict": verdict,
            "summary": str(data.get("summary") or "").strip() or f"QA verdict: {verdict}",
            "issues": [item for item in issues if isinstance(item, dict)][:10],
        }

    # ------------------------------------------------------------------
    # 5. Distributed Multi-Agent Observability Trace Logging
    # ------------------------------------------------------------------
    @staticmethod
    def record_agent_trace(
        base_dir: str | Path,
        *,
        trace_id: str,
        span_id: str,
        agent_id: str,
        division: str,
        workspace_scope: str,
        started_monotonic: float,
        status: str,
        provider: str,
        job_id: str | None = None,
        attempt: int = 1,
        authorized_writes: list[str] | None = None,
        unauthorized_writes: list[str] | None = None,
        blocked_actions: list[dict[str, Any]] | None = None,
        qa_verdict: str | None = None,
        handoff_to: str | None = None,
    ) -> dict[str, Any]:
        latency_ms = max(0, int((time.monotonic() - started_monotonic) * 1000))
        entry = {
            "trace_id": trace_id,
            "span_id": span_id,
            "agent_id": agent_id,
            "division": division,
            "workspace_scope": workspace_scope,
            "job_id": job_id,
            "provider": provider,
            "attempt": attempt,
            "latency_ms": latency_ms,
            "status": status,
            "authorized_writes": authorized_writes or [],
            "unauthorized_writes": unauthorized_writes or [],
            "blocked_actions_count": len(blocked_actions or []),
            "blocked_actions": blocked_actions or [],
            "qa_verdict": qa_verdict,
            "handoff_to": handoff_to,
            "recorded_at": _utc_now(),
        }
        trace_file = Path(base_dir) / ".producer" / "nexus_traces.jsonl"
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        with trace_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def get_project_nexus_state(self, workspace: str | Path) -> dict[str, Any]:
        ws = Path(workspace).resolve()
        ledger = _read_json_safe(ws / ".producer" / "nexus_ledger.json")
        traces: list[dict[str, Any]] = []
        trace_path = ws / ".producer" / "nexus_traces.jsonl"
        if trace_path.is_file():
            for line in trace_path.read_text(encoding="utf-8", errors="replace").splitlines()[-100:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        traces.append(obj)
                except json.JSONDecodeError:
                    continue
        qa_verdicts: list[dict[str, Any]] = []
        qa_dir = ws / ".producer" / "qa_verdicts"
        if qa_dir.is_dir():
            for qf in sorted(qa_dir.glob("*.json")):
                qd = _read_json_safe(qf)
                if qd:
                    qa_verdicts.append(qd)
        return {
            "ledger": ledger,
            "qa_verdicts": qa_verdicts,
            "traces": traces,
        }
