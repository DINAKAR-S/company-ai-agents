"""Export a Team to a runtime.

Three targets, one source file per role:

  claude-code      .claude/agents/<slug>.md       Claude Code subagents
  managed-agents   agents/<slug>.md + environments/cloud.yaml   for `ant apply`
  n8n              n8n/<slug>.json                system prompt + model for an AI Agent node

Every exporter appends a Team section to the prompt so the agent knows who it
reports to and who else is on the team. Claude Code subagents cannot call each
other, so escalation there is a marker the main session acts on; the Team
section says so in the prompt rather than pretending otherwise.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import frontmatter
from .catalog import Catalog, Role
from .compose import Team

TARGETS = ("claude-code", "managed-agents", "n8n")

CLAUDE_CODE_MODEL = {"fast": "haiku", "balanced": "sonnet", "deep": "opus"}
API_MODEL = {"fast": "claude-haiku-5-5", "balanced": "claude-sonnet-5-5", "deep": "claude-opus-5-5"}
# Generic capability -> Claude Code tool names. Anything not listed gets read-only tools.
CLAUDE_CODE_TOOLS = {
    "code": ["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
    "documents": ["Read", "Write", "Glob", "Grep"],
    "spreadsheets": ["Read", "Write", "Bash"],
    "files": ["Read", "Write", "Glob", "Grep"],
    "web_search": ["WebSearch", "WebFetch"],
    "database": ["Bash", "Read"],
    "analytics": ["Read", "Bash"],
    "monitoring": ["Bash", "Read"],
    "cloud": ["Bash", "Read"],
}


def _style(catalog: Catalog) -> str:
    return ("\n" + catalog.style) if catalog.style else ""


def _team_section(catalog: Catalog, team: Team, role: Role, runtime: str) -> str:
    members = [catalog.roles[r] for r in team.ids() if r in catalog.roles and r != role.id]
    lines = ["", "## Your team", ""]
    lines.append(f"You work for {team.company}.")
    if role.reports_to:
        lines.append(f"You report to **{role.reports_to}**"
                     + (" (on this team)." if role.reports_to in team.ids() else " (not on this team; escalate to the human instead)."))
    else:
        lines.append("You are the root of the chart. You escalate to the human owner.")
    if members:
        lines.append("")
        lines.append("Teammates you can hand work to, by id:")
        for m in members:
            lines.append(f"- `{m.id}` ({m.title}): {m.summary}")
    lines.append("")
    if runtime == "claude-code":
        lines.append("Escalation in this runtime: you cannot call another agent yourself. When a rule says escalate, "
                     "finish with a line `ESCALATE: <role id>` followed by the memo, and the main session will route it.")
    elif runtime == "managed-agents":
        lines.append("Escalation in this runtime: name the role id and the memo in your final message; the session "
                     "owner routes it, or a coordinator does when this agent runs in a multiagent roster.")
    else:
        lines.append("Escalation in this runtime: return `{\"escalate_to\": \"<role id>\", \"memo\": \"...\"}` as the "
                     "last line so the workflow can branch on it.")
    return "\n".join(lines) + "\n"


def _claude_code(catalog: Catalog, team: Team, role: Role, out: Path) -> Path:
    tools: list[str] = []
    for t in role.tools:
        for name in CLAUDE_CODE_TOOLS.get(t, ["Read"]):
            if name not in tools:
                tools.append(name)
    if not tools:
        tools = ["Read"]
    desc = f"{role.title}. {role.summary} Use for: {', '.join(role.triggers)}."
    fm = {
        "name": role.slug,
        "description": desc,
        "tools": ", ".join(tools),
        "model": CLAUDE_CODE_MODEL[role.model_hint],
    }
    path = out / ".claude" / "agents" / f"{role.slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter.dump(fm) + "\n" + role.body.rstrip() + "\n" + _team_section(catalog, team, role, "claude-code")
                    + _style(catalog), encoding="utf-8")
    return path


def _managed_agents(catalog: Catalog, team: Team, role: Role, out: Path) -> Path:
    web = "web_search" in role.tools
    # agent_toolset is the hosted sandbox toolset; web tools are off unless the
    # role lists web_search, because an agent with the web on by accident is a
    # data-exfiltration path, not a feature.
    fm_lines = [
        "---",
        f"name: {role.title}",
        f"model: {API_MODEL[role.model_hint]}",
        "tools:",
        "  - type: agent_toolset_20260401",
        "    default_config: {permission_policy: {type: always_ask}}",
        "    configs:",
        f"      - {{name: web_search, enabled: {'true' if web else 'false'}}}",
        f"      - {{name: web_fetch, enabled: {'true' if web else 'false'}}}",
        "---",
        "",
    ]
    path = out / "agents" / f"{role.slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(fm_lines) + role.body.rstrip() + "\n" + _team_section(catalog, team, role, "managed-agents")
                    + _style(catalog), encoding="utf-8")
    env = out / "environments" / "cloud.yaml"
    env.parent.mkdir(parents=True, exist_ok=True)
    if not env.exists():
        env.write_text(
            "name: orgchart-env\n"
            "config: {type: cloud, networking: {type: limited, allow_package_managers: true}}\n",
            encoding="utf-8",
        )
    return path


def _n8n(catalog: Catalog, team: Team, role: Role, out: Path) -> Path:
    payload = {
        "name": role.title,
        "id": role.id,
        "model": API_MODEL[role.model_hint],
        "systemMessage": role.body.rstrip() + "\n" + _team_section(catalog, team, role, "n8n") + _style(catalog),
        "suggestedTools": role.tools,
        "integrations": role.integrations,
        "triggers": role.triggers,
        "escalatesTo": role.escalates_to,
    }
    path = out / "n8n" / f"{role.slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _team_chart(catalog: Catalog, team: Team, out: Path) -> Path:
    lines = [f"# {team.company}: AI team", "", "| Role | Reports to | Model | Why |", "|---|---|---|---|"]
    for r in team.roles:
        role = catalog.roles.get(r["id"])
        if not role:
            continue
        lines.append(f"| `{role.id}` {role.title} | {role.reports_to or 'human owner'} | {role.model_hint} | {r['reason']} |")
    if team.warnings:
        lines += ["", "## Warnings", ""] + [f"- {w}" for w in team.warnings]
    path = out / "TEAM.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def export_team(catalog: Catalog, team: Team, target: str, out_dir: str | Path) -> list[Path]:
    if target not in TARGETS:
        raise ValueError(f"unknown target {target!r}; choose from {TARGETS}")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    writer = {"claude-code": _claude_code, "managed-agents": _managed_agents, "n8n": _n8n}[target]
    written: list[Path] = []
    for r in team.roles:
        role = catalog.roles.get(r["id"])
        if role is None:
            continue
        written.append(writer(catalog, team, role, out))
    written.append(_team_chart(catalog, team, out))
    return written
