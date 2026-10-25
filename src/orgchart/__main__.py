"""Command line entry point: python -m orgchart <command>."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalog import load_catalog
from .compose import Answers, Team, ask_in_terminal, compose
from .export import TARGETS, export_team
from .finder import find
from .solve import (
    DEFAULT_LEAD,
    DEFAULT_MEMORY,
    GENERAL,
    Session,
    add_lesson,
    build_panel,
    has_credentials,
    load_lessons,
    record_lessons,
    solve,
    write_dry_run,
    write_outputs,
)
from .validate import validate


def _root(args) -> Path:
    return Path(args.root).resolve()


def cmd_validate(args) -> int:
    problems = validate(_root(args))
    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    cat = load_catalog(_root(args))
    print(f"ok: {len(cat.roles)} roles in {len(cat.departments)} departments, no problems")
    return 0


def cmd_tree(args) -> int:
    cat = load_catalog(_root(args), strict=False)

    def walk(role_id: str, depth: int) -> None:
        r = cat.roles[role_id]
        print(f"{'  ' * depth}{r.title}  ({r.id}, {r.level})")
        for c in sorted(cat.children(role_id), key=lambda x: (x.department, x.id)):
            walk(c.id, depth + 1)

    roots = [r.id for r in cat.roles.values() if r.reports_to is None]
    for root in roots:
        walk(root, 0)
    return 0


def cmd_show(args) -> int:
    cat = load_catalog(_root(args))
    r = cat.roles.get(args.role)
    if not r:
        print(f"no role {args.role!r}; try: python -m orgchart tree", file=sys.stderr)
        return 1
    print(r.path.read_text(encoding="utf-8"))
    return 0


def cmd_list(args) -> int:
    cat = load_catalog(_root(args), strict=False)
    for dept, desc in cat.departments.items():
        print(f"{dept}: {desc}")
        for r in cat.by_department(dept):
            print(f"  {r.id:45} {r.title}")
    return 0


def cmd_hire(args) -> int:
    cat = load_catalog(_root(args))
    if args.answers:
        try:
            raw = json.loads(Path(args.answers).read_text(encoding="utf-8"))
        except FileNotFoundError:
            print(f"answers file not found: {args.answers}", file=sys.stderr)
            return 2
        except json.JSONDecodeError as ex:
            print(f"answers file is not valid JSON: {ex}", file=sys.stderr)
            return 2
        if not isinstance(raw, dict):
            print("answers file must contain a JSON object", file=sys.stderr)
            return 2
        answers = Answers.from_dict(raw)
    else:
        answers = ask_in_terminal()
    team = compose(cat, answers)
    out = Path(args.out)
    team.save(out)
    print(f"\n{len(team.roles)} agents for {team.company}:")
    for r in team.roles:
        print(f"  {r['id']:45} {r['reason']}")
    for w in team.warnings:
        print(f"  warning: {w}")
    print(f"\nteam written to {out}. Next: python -m orgchart export --team {out} --to claude-code --out ./my-company")
    return 0


def cmd_export(args) -> int:
    cat = load_catalog(_root(args))
    try:
        team = Team.from_json(Path(args.team).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"team file not found: {args.team}", file=sys.stderr)
        return 2
    except (json.JSONDecodeError, KeyError, TypeError) as ex:
        print(f"team file is not a team.json written by `orgchart hire`: {ex}", file=sys.stderr)
        return 2
    written = export_team(cat, team, args.to, args.out)
    for p in written:
        print(p)
    print(f"{len(written)} files written for target {args.to}")
    return 0


def _read_text_arg(value, flag: str) -> str:
    """A flag can be inline text or @path to a file."""
    if not value:
        return ""
    if value.startswith("@"):
        path = Path(value[1:])
        if not path.exists():
            raise FileNotFoundError(f"{flag}: {path} not found")
        return path.read_text(encoding="utf-8", errors="replace")
    return value


def cmd_find(args) -> int:
    cat = load_catalog(_root(args))
    hits = find(cat, args.problem, _read_text_arg(args.context, "--context"), limit=args.limit)
    if not hits:
        print("no role matched; add detail to the problem (systems, symptoms, who is affected)")
        return 1
    for m in hits:
        print(f"{m.role.id:45} {m.score:6.1f}  {m.role.title}  [{', '.join(m.matched[:8])}]")
    return 0


def cmd_solve(args) -> int:
    cat = load_catalog(_root(args))
    problem = _read_text_arg(args.problem, "--problem")
    context = _read_text_arg(args.context, "--context")
    memory = None if args.no_memory else args.memory
    extra = [x.strip() for x in (args.panelist or []) if x.strip()]
    if args.dry_run:
        lessons, warnings = load_lessons(memory)
        panel, moderator, w = build_panel(cat, problem, context, args.size, args.lead, extra)
        s = Session(problem=problem.strip(), context=context.strip(), panel=panel, moderator=moderator,
                    warnings=warnings + w, lessons=lessons)
        for p in write_dry_run(s, args.out):
            print(p)
        print(f"dry run: {len(panel)} panelists + moderator, no model calls")
        return 0
    if not has_credentials():
        print("no Anthropic credentials found (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or `ant auth login`). "
              "Use --dry-run to see the panel and prompts without calling a model.", file=sys.stderr)
        return 2
    s = solve(cat, problem, context, size=args.size, lead=args.lead, extra=extra, memory=memory)
    written = write_outputs(s, args.out)
    for p in written:
        print(p)
    for w in s.warnings:
        print(f"warning: {w}")
    for e in s.errors:
        print(f"error: {e}", file=sys.stderr)
    if memory and (s.critiques or s.decision):
        n = record_lessons(s, memory)
        print(f"{n} lessons recorded in {memory} for the next panel")
    if s.decision:
        print(f"\n{s.moderator.name} ({s.moderator.role.title}) decided: {s.decision.get('decision', '')}")
    return 0 if s.decision and not s.errors else (1 if s.decision else 2)


def cmd_lesson(args) -> int:
    if args.action == "add":
        if not args.text:
            print("lesson add needs the lesson text", file=sys.stderr)
            return 2
        e = add_lesson(args.memory, args.role or GENERAL, args.text, source="manual")
        print(f"recorded for {e['role']}: {e['lesson']}")
        return 0
    lessons, warnings = load_lessons(args.memory)
    for w in warnings:
        print(f"warning: {w}")
    if not lessons:
        print(f"no lessons in {args.memory} yet; run `orgchart solve` or `orgchart lesson add`")
        return 0
    for x in lessons:
        print(f"{x.get('date', '')}  {x['role']:40} {x['lesson']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="orgchart", description="A company org chart of AI agents.")
    ap.add_argument("--root", default=".", help="repo root containing catalog.json (default: current directory)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="check catalog.json and every AGENT.md").set_defaults(fn=cmd_validate)
    sub.add_parser("tree", help="print the org chart").set_defaults(fn=cmd_tree)
    sub.add_parser("list", help="list roles by department").set_defaults(fn=cmd_list)
    p = sub.add_parser("show", help="print one agent file"); p.add_argument("role"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("hire", help="answer a few questions, get a team.json")
    p.add_argument("--answers", help="JSON file of answers instead of the terminal interview")
    p.add_argument("--out", default="team.json")
    p.set_defaults(fn=cmd_hire)
    p = sub.add_parser("export", help="write a team to a runtime")
    p.add_argument("--team", required=True)
    p.add_argument("--to", required=True, choices=TARGETS)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_export)
    p = sub.add_parser("find", help="rank roles for a problem statement (no model call)")
    p.add_argument("problem")
    p.add_argument("--context", help="company context, inline or @file")
    p.add_argument("--limit", type=int, default=8)
    p.set_defaults(fn=cmd_find)
    p = sub.add_parser("solve", help="a named panel of roles debates a problem and writes plan, edge cases, requirements")
    p.add_argument("--problem", required=True, help="the problem, inline or @file")
    p.add_argument("--context", help="company context, inline or @file (website text, docs, stack)")
    p.add_argument("--size", type=int, default=6, help="panelists including the lead (default 6)")
    p.add_argument("--lead", default=DEFAULT_LEAD, help=f"role id that opens the panel (default {DEFAULT_LEAD})")
    p.add_argument("--panelist", action="append", help="force a role onto the panel (repeatable)")
    p.add_argument("--memory", default=DEFAULT_MEMORY, help=f"lessons file read before and written after (default {DEFAULT_MEMORY})")
    p.add_argument("--no-memory", action="store_true", help="ignore and do not write lessons")
    p.add_argument("--out", default="./solution")
    p.add_argument("--dry-run", action="store_true", help="write the panel and prompts, call no model")
    p.set_defaults(fn=cmd_solve)
    p = sub.add_parser("lesson", help="list or add lessons the next panel will read")
    p.add_argument("action", choices=["list", "add"])
    p.add_argument("text", nargs="?", help="the lesson, in quotes")
    p.add_argument("--role", help=f"role id the lesson is for (default {GENERAL!r}, every panelist)")
    p.add_argument("--memory", default=DEFAULT_MEMORY)
    p.set_defaults(fn=cmd_lesson)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except (FileNotFoundError, ValueError) as ex:
        # Catalog problems (missing file, bad id, bad front matter) are reported, not dumped as tracebacks.
        print(f"error: {ex}", file=sys.stderr)
        print("run `python -m orgchart validate` for the full list", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
