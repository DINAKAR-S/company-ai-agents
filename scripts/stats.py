"""Print every number the README claims, from the files themselves.

Run:  python scripts/stats.py
CI runs it on every push, so the README's proof block can be regenerated and
checked rather than trusted.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from orgchart import load_catalog, validate
from orgchart.validate import _REF


def main() -> int:
    problems = validate(ROOT)
    cat = load_catalog(ROOT)
    roles = list(cat.roles.values())
    lines = [len((r.body).splitlines()) + 12 for r in roles]  # 12 = front matter lines
    tasks = []
    refs = Counter()
    for r in roles:
        section = r.body.split("## What you do", 1)[1].split("## ", 1)[0]
        tasks.append(sum(1 for ln in section.splitlines() if ln.startswith("- ")))
        for m in _REF.finditer(r.body):
            rid = f"{m.group(1)}/{m.group(2)}"
            if rid in cat.roles and rid != r.id:
                refs[rid] += 1
    dangling = [p for p in problems if "unknown role" in p]
    approval = sum(1 for r in roles if re.search(r"approv", r.body.split("## Working rules", 1)[1].split("## ", 1)[0], re.IGNORECASE))
    levels = Counter(r.level for r in roles)
    hints = Counter(r.model_hint for r in roles)
    print("company-ai-agents proof")
    print(f"roles:                 {len(roles)}")
    print(f"departments:           {len(cat.departments)}")
    print(f"levels:                {dict(levels)}")
    print(f"model hints:           {dict(hints)}")
    print(f"lines per agent:       min {min(lines)}, median {sorted(lines)[len(lines)//2]}, max {max(lines)}")
    print(f"tasks per agent:       min {min(tasks)}, max {max(tasks)}")
    print(f"cross-role references: {sum(refs.values())} (dangling: {len(dangling)})")
    print(f"most referenced:       {', '.join(f'{k} ({v})' for k, v in refs.most_common(5))}")
    print(f"agents with an approval gate in Working rules: {approval} of {len(roles)}")
    print(f"validator problems:    {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
