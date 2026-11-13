"""Validate standalone NEXUS Agent source corpus (`agents/<division>/<id>.md`) and sync multi-tool targets.

Modeled on `msitarzewski/agency-agents` (`scripts/lint-agents.sh` + `scripts/convert.sh`):
- Single source of truth: `b:/ALL_TOOLS/CofiDocumentary/agents/<division>/<id>.md`
- Generated runtime targets:
  1. `.codex/agents/<id>.toml` (Codex CLI native specialist definitions)
  2. `.agents/skills/cofi-agency-<id>/SKILL.md` (Gemini CLI / Antigravity skill definitions)
  3. `agents/INDEX.json` (deterministic SHA-256 manifest of divisions, runbooks & specialists)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from documentary.agent_manager import AgentManager, AgentProfile  # noqa: E402


def _render_codex_toml(agent: AgentProfile) -> str:
    desc = f"{agent.name} ({agent.display_vi}) — {agent.mission}".replace('"', '\\"')
    instructions = (
        f"You are {agent.name} ({agent.id}) in Division '{agent.division}'.\n"
        f"Vibe: {agent.vibe}\n"
        f"Workspace Scope: {agent.workspace_scope}\n"
        f"Permitted Reads: {', '.join(agent.reads_artifacts)}\n"
        f"Permitted Writes: {', '.join(agent.writes_artifacts)}\n"
        f"Allowed Host Actions: {', '.join(agent.allowed_actions)}\n"
        f"QA Partner: {agent.qa_partner}\n\n"
        f"{agent.soul_markdown}\n\n"
        f"{agent.operations_markdown}\n"
    ).replace("'''", "'''")
    return (
        f"# GENERATED FROM {agent.source_path} — DO NOT EDIT DIRECTLY\n"
        f'name = "{agent.id}"\n'
        f'description = "{desc}"\n'
        f"developer_instructions = '''\n{instructions}'''\n"
    )


def _render_antigravity_skill(agent: AgentProfile) -> str:
    desc = f"[NEXUS {agent.division}] {agent.name} ({agent.display_vi}): {agent.mission}".replace('"', "'")
    return (
        "---\n"
        f"name: cofi-agency-{agent.id}\n"
        f'description: "{desc}"\n'
        "---\n\n"
        f"<!-- GENERATED FROM {agent.source_path} — DO NOT EDIT DIRECTLY -->\n\n"
        f"# {agent.emoji} {agent.name} (`{agent.id}` — {agent.display_vi})\n\n"
        f"> **Vibe**: {agent.vibe}\n"
        f"> **Workspace Scope**: `{agent.workspace_scope}` | **Reads**: `{', '.join(agent.reads_artifacts)}` | **Writes**: `{', '.join(agent.writes_artifacts)}`\n"
        f"> **Allowed Host Actions**: `{', '.join(agent.allowed_actions)}` | **QA Partner**: `{agent.qa_partner}`\n\n"
        f"{agent.body}\n"
    )


def sync_all(*, lint_only: bool = False) -> int:
    manager = AgentManager(agents_dir=ROOT / "agents", skills_dir=ROOT / "skills")
    lint = manager.lint_corpus()
    if not lint["passed"]:
        print("NEXUS CORPUS LINT FAILED:", file=sys.stderr)
        for err in lint["errors"]:
            print(f"  [ERROR] {err}", file=sys.stderr)
        return 1

    print(
        f"NEXUS Corpus Lint PASSED: {lint['agent_count']} specialists across "
        f"{lint['division_count']} divisions and {lint['runbook_count']} runbooks."
    )
    for warn in lint["warnings"]:
        print(f"  [WARN] {warn}")

    if lint_only:
        return 0

    codex_dir = ROOT / ".codex" / "agents"
    skills_out_dir = ROOT / ".agents" / "skills"
    codex_dir.mkdir(parents=True, exist_ok=True)
    skills_out_dir.mkdir(parents=True, exist_ok=True)

    index_entries = []
    for summary in manager.list_agents():
        agent = manager.get(summary["id"])
        src_file = ROOT / agent.source_path
        sha256 = hashlib.sha256(src_file.read_bytes()).hexdigest()

        toml_path = codex_dir / f"{agent.id}.toml"
        toml_path.write_bytes(_render_codex_toml(agent).encode("utf-8"))

        skill_dir = skills_out_dir / f"cofi-agency-{agent.id}"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_bytes = _render_antigravity_skill(agent).encode("utf-8")
        (skill_dir / "SKILL.md").write_bytes(skill_bytes)

        for extra_skills_root in (
            Path(r"C:\Users\koing\.gemini\config\skills"),
            Path(r"b:\.agents\skills"),
        ):
            if extra_skills_root.exists():
                extra_dir = extra_skills_root / f"cofi-agency-{agent.id}"
                extra_dir.mkdir(parents=True, exist_ok=True)
                (extra_dir / "SKILL.md").write_bytes(skill_bytes)

        entry = dict(summary)
        entry["sha256"] = sha256
        index_entries.append(entry)

    index_payload = {
        "schema_version": "1.0",
        "architecture": "nexus_single_model_multi_agent",
        "agent_count": len(index_entries),
        "divisions": manager.list_divisions(),
        "runbooks": manager.list_runbooks(),
        "agents": index_entries,
    }
    (ROOT / "agents" / "INDEX.json").write_bytes(
        (json.dumps(index_payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    print(f"Generated {len(index_entries)} Codex `.toml` agents -> {codex_dir}")
    print(f"Generated {len(index_entries)} Gemini/Antigravity skills -> {skills_out_dir}")
    print(f"Updated manifest -> {ROOT / 'agents' / 'INDEX.json'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint & convert CofiDocumentary NEXUS Agent corpus.")
    parser.add_argument("--lint-only", action="store_true", help="Validate standalone agent markdown files without generating targets.")
    args = parser.parse_args()
    return sync_all(lint_only=args.lint_only)


if __name__ == "__main__":
    raise SystemExit(main())
