"""Solve a problem the way a room of specialists would: position, critique, decision.

Round 1  every panelist, in its own role prompt, proposes an approach with
         steps, risks, edge cases and requirements.
Round 2  every panelist reads the others' positions and says which is best,
         what is missed, and what it changes in its own.
Round 3  the moderator (Chief of Staff) decides and writes plan.md,
         edge-cases.md and requirements.md.

The model calls go through one injectable function so the whole protocol is
testable without a network, and `--dry-run` writes the panel and the prompts
and stops. Partial failures are written out, not swallowed: whatever rounds
completed land in debate.md with the error recorded in panel.json.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .catalog import Catalog, Role
from .export import API_MODEL
from .finder import Match, find
from .names import assign

DEFAULT_LEAD = "data-ai/data-ai-solutions-architect"
DEFAULT_MEMORY = "orgchart-lessons.jsonl"
GENERAL = "panel"            # lessons that apply to every panelist
MAX_LESSONS_PER_ROLE = 8
MAX_GENERAL_LESSONS = 6
MODERATOR = "c-suite/chief-of-staff"
MAX_CONTEXT_CHARS = 60_000
CallFn = Callable[[str, str, str, dict], dict]  # (model, system, user, json_schema) -> parsed dict

POSITION_SCHEMA = {
    "type": "object",
    "properties": {
        "approach": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "edge_cases": {"type": "array", "items": {"type": "string"}},
        "requirements": {"type": "array", "items": {"type": "string"}},
        "what_breaks_in_the_current_setup": {"type": "array", "items": {"type": "string"}},
        "mitigations": {"type": "array", "items": {"type": "string"}},
        "questions_for_the_company": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["approach", "steps", "risks", "edge_cases", "requirements", "what_breaks_in_the_current_setup",
                 "mitigations", "questions_for_the_company"],
    "additionalProperties": False,
}
BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "what_i_understand": {"type": "string"},
        "deciding_constraint": {"type": "string"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "questions_for_the_company": {
            "type": "array",
            "items": {"type": "object", "properties": {"question": {"type": "string"}, "my_guess": {"type": "string"}},
                      "required": ["question", "my_guess"], "additionalProperties": False},
        },
        "roles_to_consult": {
            "type": "array",
            "items": {"type": "object", "properties": {"role_id": {"type": "string"}, "question": {"type": "string"}},
                      "required": ["role_id", "question"], "additionalProperties": False},
        },
    },
    "required": ["what_i_understand", "deciding_constraint", "assumptions", "questions_for_the_company", "roles_to_consult"],
    "additionalProperties": False,
}
CRITIQUE_SCHEMA = {
    "type": "object",
    "properties": {
        "best_approach_from": {"type": "string"},
        "why": {"type": "string"},
        "disagreements": {"type": "array", "items": {"type": "string"}},
        "missed_edge_cases": {"type": "array", "items": {"type": "string"}},
        "changes_to_my_position": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["best_approach_from", "why", "disagreements", "missed_edge_cases", "changes_to_my_position"],
    "additionalProperties": False,
}
DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string"},
        "plan_md": {"type": "string"},
        "edge_cases_md": {"type": "string"},
        "requirements_md": {"type": "string"},
        "architecture_mermaid": {"type": "string"},
        "setup_md": {"type": "string"},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["decision", "plan_md", "edge_cases_md", "requirements_md", "architecture_mermaid", "setup_md",
                 "open_questions"],
    "additionalProperties": False,
}


def load_lessons(path):
    """Read the lessons file. A missing file is an empty memory; a bad line is skipped and reported."""
    if not path:
        return [], []
    p = Path(path)
    if not p.exists():
        return [], []
    lessons, warnings = [], []
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
            if not isinstance(d, dict) or "lesson" not in d or "role" not in d:
                raise ValueError("missing role or lesson")
            lessons.append(d)
        except (json.JSONDecodeError, ValueError) as ex:
            warnings.append(f"lessons file line {n} skipped: {ex}")
    return lessons, warnings


def add_lesson(path, role: str, lesson: str, source: str = "") -> dict:
    """Append one lesson. Exact duplicates for the same role are not written twice."""
    lesson = " ".join(lesson.split())
    if not lesson:
        raise ValueError("lesson text is empty")
    existing, _ = load_lessons(path)
    for e in existing:
        if e["role"] == role and e["lesson"] == lesson:
            return e
    entry = {"date": dt.date.today().isoformat(), "role": role, "lesson": lesson, "source": source[:200]}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def lessons_for(lessons: list, role_id: str):
    mine = [x["lesson"] for x in lessons if x["role"] == role_id][-MAX_LESSONS_PER_ROLE:]
    general = [x["lesson"] for x in lessons if x["role"] == GENERAL][-MAX_GENERAL_LESSONS:]
    return mine, general


def record_lessons(s, path) -> int:
    """What this session learned, written for the next one: edge cases the whole panel missed
    (general), what each critic noticed (attributed to its role), and the open questions."""
    n = 0
    src = s.problem[:120]
    for name, c in s.critiques.items():
        role_id = next((p.role.id for p in s.panel if p.name == name), None)
        for missed in c.get("missed_edge_cases", []):
            if missed.strip():
                add_lesson(path, GENERAL, f"A panel on '{src}' missed this edge case until critique: {missed}", src)
                n += 1
                if role_id:
                    add_lesson(path, role_id, f"You caught in critique what your first position missed: {missed}", src)
                    n += 1
    if s.decision:
        for q in s.decision.get("open_questions", []):
            if q.strip():
                add_lesson(path, GENERAL, f"Ask early, a panel on '{src}' had to leave it open: {q}", src)
                n += 1
    return n


@dataclass
class Panelist:
    role: Role
    name: str
    matched: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.name} ({self.role.title})"


@dataclass
class Session:
    problem: str
    context: str
    panel: list[Panelist]
    moderator: Panelist
    positions: dict[str, dict] = field(default_factory=dict)   # name -> position
    critiques: dict[str, dict] = field(default_factory=dict)   # name -> critique
    decision: dict | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    lessons: list[dict] = field(default_factory=list)
    style: str = ""
    brief: dict | None = None                                   # the lead's round 0
    consult: dict[str, str] = field(default_factory=dict)       # role id -> the lead's question for it
    max_extra_seats: int = 3
    catalog_ids: set = field(default_factory=set)


def build_panel(catalog: Catalog, problem: str, context: str, size: int = 6,
                lead: str = DEFAULT_LEAD, extra: list[str] | None = None) -> tuple[list[Panelist], Panelist, list[str]]:
    warnings: list[str] = []
    if lead not in catalog.roles:
        warnings.append(f"lead {lead!r} not in catalog; using {DEFAULT_LEAD}")
        lead = DEFAULT_LEAD
    chosen: list[str] = [lead]
    for rid in extra or []:
        if rid in catalog.roles and rid not in chosen:
            chosen.append(rid)
        elif rid not in catalog.roles:
            warnings.append(f"requested panelist {rid!r} is not in the catalog")
    matches: list[Match] = find(catalog, problem, context, limit=size * 2, exclude=set(chosen) | {MODERATOR})
    matched_terms = {m.role.id: m.matched for m in matches}
    for m in matches:
        if len(chosen) >= size:
            break
        chosen.append(m.role.id)
    if len(chosen) < 2:
        warnings.append("no roles matched the problem beyond the lead; add detail to the problem statement")
    names = assign(chosen + [MODERATOR])
    panel = [Panelist(catalog.roles[r], names[r], matched_terms.get(r, [])) for r in chosen]
    moderator = Panelist(catalog.roles[MODERATOR], names[MODERATOR])
    return panel, moderator, warnings


def _persona(p: Panelist, panel: list[Panelist], lessons=None, style: str = "") -> str:
    others = ", ".join(x.label for x in panel if x is not p)
    text = (
        f"{p.role.body.rstrip()}\n\n## This panel\n\n"
        f"Your name on this panel is {p.name}. You are on a problem-solving panel with: {others}. "
        "Speak as a senior practitioner who has shipped this before. Be concrete: name the systems, data, "
        "failure modes and numbers you would need. Say plainly what in the company's present setup will break "
        "(rate limits, quotas, existing integrations, data quality, team capacity) and what you would do about it. "
        "Disagree when you disagree. Do not invent facts about the company; ask instead."
    )
    if style:
        text += "\n\n" + style
    mine, general = lessons_for(lessons or [], p.role.id)
    if mine or general:
        text += ("\n\n## Lessons from earlier panels\n\nThese were learned the hard way. "
                 "Check each against this problem before you answer.\n")
        for x in mine + general:
            text += f"- {x}\n"
    return text


def _brief(s: Session) -> str:
    return f"## Company context\n\n{s.context or '(none given)'}\n\n## Problem\n\n{s.problem}\n"


def round0_prompt(s: Session) -> tuple[str, str]:
    """The lead reads the problem first and says who it needs and what it would ask them."""
    lead = s.panel[0]
    others = "\n".join(f"- `{p.role.id}`: {p.role.title}" for p in s.panel[1:])
    catalog_hint = ", ".join(sorted(s.catalog_ids))[:4000] if s.catalog_ids else ""
    user = (_brief(s) + f"\n## Already seated with you\n{others or '- (nobody yet)'}\n\n"
            "Before anyone speaks: say what you understand the problem to be, the one constraint that will decide "
            "the design, the assumptions you are making, the questions the company must answer (each with your best "
            "guess so they can just say yes), and which colleagues you need to consult with the exact question for "
            "each. Use role ids from this list only: " + catalog_hint + ". Ask only for roles whose answer changes "
            "the design; three is usually enough.")
    return _persona(lead, s.panel, s.lessons, s.style), user


def seat_consulted(catalog: Catalog, s: Session) -> list[str]:
    """Seat the roles the lead asked for, if they exist and are not already there. Returns the ids added."""
    added: list[str] = []
    if not s.brief:
        return added
    present = {p.role.id for p in s.panel} | {MODERATOR}
    for item in s.brief.get("roles_to_consult", []):
        rid, q = item.get("role_id", "").strip(), item.get("question", "").strip()
        if rid in present:
            if q:
                s.consult[rid] = q
            continue
        if rid not in catalog.roles:
            s.warnings.append(f"lead asked for {rid!r}, which is not a catalog role; skipped")
            continue
        if len(added) >= s.max_extra_seats:
            s.warnings.append(f"lead asked for {rid!r} but the panel is full; skipped")
            continue
        s.panel.append(Panelist(catalog.roles[rid], "", ["asked for by the lead"]))
        present.add(rid)
        added.append(rid)
        if q:
            s.consult[rid] = q
    if added:
        names = assign([p.role.id for p in s.panel] + [MODERATOR])
        for p in s.panel:
            p.name = names[p.role.id]
        s.moderator.name = names[MODERATOR]
    return added


def round1_prompt(s: Session, p: Panelist) -> tuple[str, str]:
    lead_note = ""
    if s.brief and p is s.panel[0]:
        lead_note = "\n## Your own brief from round 0\n" + json.dumps(s.brief, indent=2) + "\n"
    elif s.brief:
        lead_note = (f"\n## The lead's brief\n{s.brief.get('what_i_understand', '')}\n"
                     f"Deciding constraint, as the lead sees it: {s.brief.get('deciding_constraint', '')}\n")
        if p.role.id in s.consult:
            lead_note += f"\n**{s.panel[0].name} asked you specifically:** {s.consult[p.role.id]}\nAnswer that first.\n"
    user = (_brief(s) + lead_note + "\nGive your position: the approach you would take, concrete steps, risks, "
            "edge cases a careful engineer would test for, requirements the solution must meet, what in the "
            "present setup will break and how you would mitigate each item, and the questions you would ask "
            "the company before starting.")
    return _persona(p, s.panel, s.lessons, s.style), user


def round2_prompt(s: Session, p: Panelist) -> tuple[str, str]:
    others = "\n\n".join(
        f"### {name}\n{json.dumps(pos, indent=2)}" for name, pos in s.positions.items() if name != p.name
    )
    mine = json.dumps(s.positions.get(p.name, {}), indent=2)
    user = (_brief(s) + f"\n## Your position\n{mine}\n\n## The other positions\n{others}\n\n"
            "Which approach is best and why? Where do you disagree? Which edge cases did everyone miss? "
            "What do you change in your own position after reading theirs? Name people by their panel name.")
    return _persona(p, s.panel, s.lessons, s.style), user


def round3_prompt(s: Session) -> tuple[str, str]:
    m = s.moderator
    system = (f"{m.role.body.rstrip()}\n\n## This panel\n\nYour name is {m.name}. You moderated a panel of: "
              + ", ".join(p.label for p in s.panel) +
              ". You decide. Write for the person who asked, not for the panel. Markdown bodies must be complete "
              "documents with headings. Every requirement is testable. Every edge case says what should happen."
              + ("\n\n" + s.style if s.style else ""))
    transcript = "\n\n".join(
        f"## Round 1: {name}\n{json.dumps(pos, indent=2)}" for name, pos in s.positions.items()
    ) + "\n\n" + "\n\n".join(
        f"## Round 2: {name}\n{json.dumps(c, indent=2)}" for name, c in s.critiques.items()
    )
    user = (_brief(s) + "\n" + transcript +
            "\n\nDecide the approach. Produce plan_md (phases, owners by role id, what done looks like), "
            "edge_cases_md (a table: case, expected behaviour, how to test), requirements_md (functional, "
            "data, security and privacy, operational; each one testable), architecture_mermaid (a Mermaid "
            "flowchart of the chosen solution: systems as nodes, data flow as arrows, the human approval step "
            "shown; source only, no code fence), setup_md (everything the company must set up before step one: "
            "accounts, environment variable names for each credential and where to create the key, who owns "
            "each; never ask for or include a credential value), and the open questions the company must answer.")
    return system, user


def api_call(model: str, system: str, user: str, schema: dict) -> dict:
    """Default transport: one Messages API call with a strict JSON schema output."""
    try:
        import anthropic
    except ImportError as ex:
        raise RuntimeError("pip install anthropic, then set ANTHROPIC_API_KEY or run `ant auth login`") from ex
    client = anthropic.Anthropic()
    kwargs = {"model": model, "max_tokens": 16000, "system": system,
                  "messages": [{"role": "user", "content": user}],
                  "output_config": {"format": {"type": "json_schema", "schema": schema}}}
    try:
        # Server-side refusal fallback: a declined request is re-run on a fallback model inside the same call.
        response = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
    except TypeError:
        # Older SDK without the fallbacks parameter: same request, no fallback.
        response = client.messages.create(**kwargs)
    if response.stop_reason == "refusal":
        detail = getattr(response, "stop_details", None)
        raise RuntimeError(f"model declined ({getattr(detail, 'category', None)}): {getattr(detail, 'explanation', '')}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("response hit max_tokens before the JSON was complete")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def _model_for(p: Panelist) -> str:
    return API_MODEL[p.role.model_hint]


def solve(catalog: Catalog, problem: str, context: str = "", size: int = 6, lead: str = DEFAULT_LEAD,
          extra: list[str] | None = None, call: CallFn | None = None, memory=None) -> Session:
    if not problem or not problem.strip():
        raise ValueError("problem statement is empty")
    lessons, warnings = load_lessons(memory)
    if len(context) > MAX_CONTEXT_CHARS:
        warnings.append(f"context truncated from {len(context)} to {MAX_CONTEXT_CHARS} characters")
        context = context[:MAX_CONTEXT_CHARS]
    panel, moderator, w = build_panel(catalog, problem, context, size, lead, extra)
    s = Session(problem=problem.strip(), context=context.strip(), panel=panel, moderator=moderator,
                warnings=warnings + w, lessons=lessons, style=catalog.style)
    s.catalog_ids = set(catalog.roles)
    call = call or api_call

    # Round 0: the lead reads first and says who it needs. A failed brief is recorded and the panel proceeds as found.
    system, user = round0_prompt(s)
    try:
        s.brief = call(_model_for(s.panel[0]), system, user, BRIEF_SCHEMA)
        seat_consulted(catalog, s)
    except Exception as ex:  # noqa: BLE001
        s.errors.append(f"round 0, {s.panel[0].label}: {ex}")

    for p in s.panel:
        system, user = round1_prompt(s, p)
        try:
            s.positions[p.name] = call(_model_for(p), system, user, POSITION_SCHEMA)
        except Exception as ex:  # noqa: BLE001 - record and continue; one failed panelist must not end the session
            s.errors.append(f"round 1, {p.label}: {ex}")
    if not s.positions:
        s.errors.append("round 1 produced no positions; stopping")
        return s
    for p in s.panel:
        if p.name not in s.positions:
            continue
        system, user = round2_prompt(s, p)
        try:
            s.critiques[p.name] = call(_model_for(p), system, user, CRITIQUE_SCHEMA)
        except Exception as ex:  # noqa: BLE001
            s.errors.append(f"round 2, {p.label}: {ex}")
    system, user = round3_prompt(s)
    try:
        s.decision = call(_model_for(s.moderator) if s.moderator.role.model_hint == "deep" else API_MODEL["deep"],
                          system, user, DECISION_SCHEMA)
    except Exception as ex:  # noqa: BLE001
        s.errors.append(f"round 3, moderator: {ex}")
    return s


def _md_list(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items) if items else "- (none)"


def write_outputs(s: Session, out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    panel_json = {
        "problem": s.problem,
        "panel": [{"name": p.name, "role": p.role.id, "title": p.role.title, "model": _model_for(p), "matched": p.matched} for p in s.panel],
        "moderator": {"name": s.moderator.name, "role": s.moderator.role.id},
        "rounds_completed": {"brief": s.brief is not None, "positions": len(s.positions), "critiques": len(s.critiques),
                             "decision": s.decision is not None},
        "consulted": s.consult,
        "errors": s.errors, "warnings": s.warnings,
    }
    p = out / "panel.json"; p.write_text(json.dumps(panel_json, indent=2) + "\n", encoding="utf-8"); written.append(p)

    lines = ["# Debate", "", f"**Problem:** {s.problem}", "", "## Panel", ""]
    for pl in s.panel:
        lines.append(f"- **{pl.name}**, {pl.role.title} (`{pl.role.id}`)" + (f", matched: {', '.join(pl.matched)}" if pl.matched else ""))
    lines.append(f"- **{s.moderator.name}**, {s.moderator.role.title}, moderator")
    if s.brief:
        b = s.brief
        lines += ["", f"## Round 0: {s.panel[0].name} reads the problem", "", b.get("what_i_understand", ""), "",
                  f"**Deciding constraint:** {b.get('deciding_constraint', '')}", "", "**Assumptions**",
                  _md_list(b.get("assumptions", [])), "", "**Questions for the company (with the lead's guess)**",
                  _md_list([f"{q.get('question', '')} (guess: {q.get('my_guess', '')})" for q in b.get("questions_for_the_company", [])]),
                  "", "**Consulted**", _md_list([f"`{r.get('role_id', '')}`: {r.get('question', '')}" for r in b.get("roles_to_consult", [])]), ""]
    lines += ["", "## Round 1: positions", ""]
    for name, pos in s.positions.items():
        lines += [f"### {name}", "", f"**Approach:** {pos.get('approach','')}", "", "**Steps**", _md_list(pos.get("steps", [])), "",
                  "**Risks**", _md_list(pos.get("risks", [])), "", "**Edge cases**", _md_list(pos.get("edge_cases", [])), "",
                  "**Requirements**", _md_list(pos.get("requirements", [])), "",
                  "**What breaks in the present setup**", _md_list(pos.get("what_breaks_in_the_current_setup", [])), "",
                  "**Mitigations**", _md_list(pos.get("mitigations", [])), "", "**Questions for the company**",
                  _md_list(pos.get("questions_for_the_company", [])), ""]
    lines += ["## Round 2: critiques", ""]
    for name, c in s.critiques.items():
        lines += [f"### {name}", "", f"**Best approach:** {c.get('best_approach_from','')}. {c.get('why','')}", "",
                  "**Disagreements**", _md_list(c.get("disagreements", [])), "", "**Edge cases everyone missed**",
                  _md_list(c.get("missed_edge_cases", [])), "", "**Changes to my position**",
                  _md_list(c.get("changes_to_my_position", [])), ""]
    lines += ["## Round 3: decision", ""]
    if s.decision:
        lines += [f"**{s.moderator.name}:** {s.decision.get('decision','')}", "", "**Open questions**",
                  _md_list(s.decision.get("open_questions", [])), ""]
    else:
        lines += ["(no decision; see errors in panel.json)", ""]
    if s.errors:
        lines += ["## Errors", "", _md_list(s.errors), ""]
    p = out / "debate.md"; p.write_text("\n".join(lines), encoding="utf-8"); written.append(p)

    if s.decision:
        plan = s.decision.get("plan_md", "").rstrip()
        mermaid = s.decision.get("architecture_mermaid", "").strip().strip("`")
        if mermaid.lower().startswith("mermaid\n"):
            mermaid = mermaid.split("\n", 1)[1]
        if mermaid:
            plan += "\n\n## Architecture\n\n```mermaid\n" + mermaid.rstrip() + "\n```"
        p = out / "plan.md"; p.write_text(plan + "\n", encoding="utf-8"); written.append(p)
        for fname, key in (("edge-cases.md", "edge_cases_md"), ("requirements.md", "requirements_md")):
            p = out / fname
            p.write_text(s.decision.get(key, "").rstrip() + "\n", encoding="utf-8")
            written.append(p)
        setup = s.decision.get("setup_md", "").strip()
        if setup:
            p = out / "setup.md"; p.write_text(setup + "\n", encoding="utf-8"); written.append(p)
    return written


def write_dry_run(s: Session, out_dir: str | Path) -> list[Path]:
    """Write the panel and every prompt for round 1, so a user can run them by hand or inspect them."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    lines = ["# Panel (dry run, no model calls)", "", f"**Problem:** {s.problem}", ""]
    for p in s.panel:
        lines.append(f"- **{p.name}**, {p.role.title} (`{p.role.id}`, {_model_for(p)})" + (f", matched: {', '.join(p.matched)}" if p.matched else ""))
    lines.append(f"- **{s.moderator.name}**, {s.moderator.role.title}, moderator")
    if s.lessons:
        lines += ["", f"Lessons loaded from earlier panels: {len(s.lessons)}"]
    if s.warnings:
        lines += ["", "## Warnings", "", _md_list(s.warnings)]
    system0, user0 = round0_prompt(s)
    lines += ["", f"## Round 0 prompt ({s.panel[0].label} reads first)", "", "**System**", "", "```", system0, "```", "",
              "**User**", "", "```", user0, "```", "", "## Round 1 prompts", ""]
    for p in s.panel:
        system, user = round1_prompt(s, p)
        lines += [f"### {p.label}", "", "**System**", "", "```", system, "```", "", "**User**", "", "```", user, "```", ""]
    path = out / "panel.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return [path]


def has_credentials() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or (Path.home() / ".config" / "anthropic").exists())
