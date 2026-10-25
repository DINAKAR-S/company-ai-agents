"""Count skills across extracted postings and write counts into a role's Skills section.

The Skills section becomes a list of `- skill (n of N postings)` lines, ordered by
count, keeping any existing uncounted lines at the bottom so editorial additions
survive until a run confirms or drops them.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower().rstrip("."))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--min-share", type=float, default=0.2, help="keep skills mentioned in at least this share of postings")
    ap.add_argument("--max", type=int, default=12)
    a = ap.parse_args()

    data = json.loads(Path(a.inp).read_text(encoding="utf-8"))
    rows = [r for r in data["results"].values() if "error" not in r]
    n = len(rows)
    if n == 0:
        sys.exit("no successful extractions")
    counts = Counter()
    for r in rows:
        for s in {normalise(x) for x in r.get("skills", [])}:
            counts[s] += 1
    kept = [(s, c) for s, c in counts.most_common() if c / n >= a.min_share][: a.max]

    path = ROOT / "agents" / Path(*a.role.split("/")) / "AGENT.md"
    text = path.read_text(encoding="utf-8")
    head, rest = text.split("## Skills", 1)
    section, tail = rest.split("\n## ", 1)
    uncounted = [ln for ln in section.splitlines() if ln.startswith("- ") and "postings)" not in ln]
    new_lines = [f"- {s[0].upper() + s[1:]} ({c} of {n} postings)" for s, c in kept]
    new_section = "\n\n" + "\n".join(new_lines + uncounted) + "\n\n"
    path.write_text(head + "## Skills" + new_section + "## " + tail, encoding="utf-8")

    runs = ROOT / "research" / "runs.md"
    line = f"| {dt.date.today().isoformat()} | {a.role} | {n} | {data.get('model','')} | {data.get('input_tokens',0)} in / {data.get('output_tokens',0)} out |\n"
    if not runs.exists():
        runs.write_text("# Research runs\n\n| Date | Role | Postings | Model | Tokens |\n|---|---|---|---|---|\n", encoding="utf-8")
    with open(runs, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"{a.role}: {len(kept)} counted skills from {n} postings written; run logged in research/runs.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
