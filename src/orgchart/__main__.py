"""Command line entry point: python -m orgchart <command>."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalog import load_catalog
from .compose import Answers, Team, ask_in_terminal, compose
from .export import TARGETS, export_team
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


def main(argv: list[str] | None = None) -> int:
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
