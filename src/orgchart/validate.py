"""Every rule a contributor's pull request has to satisfy, as one list of strings.

An empty list means the repo is consistent. The CLI exits non-zero otherwise and
CI runs it on every push, so a broken reporting line or a dangling role
reference never reaches the default branch.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import frontmatter
from .catalog import (
    LEVELS,
    MODEL_HINTS,
    REQUIRED_KEYS,
    REQUIRED_SECTIONS,
    ROLE_ID,
    TOOLS,
    agent_path,
    load_index,
)

EM_DASH = chr(0x2014)  # the em-dash, spelled out so the source file itself never contains one
# A role reference looks like `sales/sdr`. We only treat it as a reference when
# the left side is a known department, so URLs and paths in prose do not trip it.
_REF = re.compile(r"`?\b([a-z0-9-]+)/([a-z0-9-]+)\b`?")
# Lines that would leak a build schedule into a public artefact.
_SCHEDULE = re.compile(r"\b(week\s+\d+|phase\s+\d+|repo\s+\d+\s+of\s+\d+)\b", re.IGNORECASE)


def validate(root: str | Path) -> list[str]:
    root = Path(root)
    problems: list[str] = []
    index = load_index(root)
    departments = set(index["departments"])
    entries = {e["id"]: e for e in index["roles"]}

    # Index-level checks
    ids = [e["id"] for e in index["roles"]]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        problems.append(f"catalog.json: duplicate ids {dupes}")
    roots = [e["id"] for e in index["roles"] if e["reports_to"] is None]
    if len(roots) != 1:
        problems.append(f"catalog.json: expected exactly one root role (reports_to null), found {roots}")
    for e in index["roles"]:
        rid = e["id"]
        if not ROLE_ID.match(rid):
            problems.append(f"{rid}: id must look like 'department/slug' (lowercase, digits, hyphens)")
            continue
        if rid.split("/")[0] != e["department"] or e["department"] not in departments:
            problems.append(f"{rid}: department {e['department']!r} does not match id prefix or is unknown")
        if e["level"] not in LEVELS:
            problems.append(f"{rid}: level {e['level']!r} not in {LEVELS}")
        if e["reports_to"] is not None and e["reports_to"] not in entries:
            problems.append(f"{rid}: reports_to {e['reports_to']!r} is not a catalog role")

    # Cycle check over the index graph
    for rid in entries:
        seen, cur = set(), rid
        while cur is not None:
            if cur in seen:
                problems.append(f"{rid}: reporting chain contains a cycle at {cur}")
                break
            seen.add(cur)
            cur = entries.get(cur, {}).get("reports_to")

    # Every role has a file that agrees with the index, and no stray files exist
    on_disk = set()
    for p in (root / "agents").glob("*/*/AGENT.md"):
        on_disk.add(f"{p.parent.parent.name}/{p.parent.name}")
    for stray in sorted(on_disk - set(entries)):
        problems.append(f"agents/{stray}/AGENT.md exists but {stray} is not in catalog.json")

    for e in index["roles"]:
        rid = e["id"]
        path = agent_path(root, rid)
        if not path.exists():
            problems.append(f"{rid}: missing {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        try:
            data, body = frontmatter.parse(text)
        except frontmatter.FrontMatterError as ex:
            problems.append(f"{rid}: front matter error: {ex}")
            continue
        for k in REQUIRED_KEYS:
            if k not in data:
                problems.append(f"{rid}: front matter missing {k!r}")
        if list(data)[: len(REQUIRED_KEYS)] != list(REQUIRED_KEYS):
            problems.append(f"{rid}: front matter keys must be in order {list(REQUIRED_KEYS)}")
        for k in ("id", "title", "department", "reports_to", "level"):
            if k in data and data[k] != e[k]:
                problems.append(f"{rid}: front matter {k}={data[k]!r} disagrees with catalog.json {e[k]!r}")
        if data.get("model_hint") not in MODEL_HINTS:
            problems.append(f"{rid}: model_hint {data.get('model_hint')!r} not in {MODEL_HINTS}")
        for t in data.get("tools") or []:
            if t not in TOOLS:
                problems.append(f"{rid}: unknown tool {t!r}; allowed: {TOOLS}")
        for k in ("tools", "integrations", "triggers", "tags"):
            if not isinstance(data.get(k), list) or not data.get(k):
                problems.append(f"{rid}: {k} must be a non-empty flow list")
        esc = data.get("escalates_to")
        if esc is not None and esc not in entries:
            problems.append(f"{rid}: escalates_to {esc!r} is not a catalog role")
        if esc == rid:
            problems.append(f"{rid}: escalates_to itself")
        if e["reports_to"] is None and esc is not None:
            problems.append(f"{rid}: the root role must escalate to null (the human owner)")
        for s in REQUIRED_SECTIONS:
            if s not in body:
                problems.append(f"{rid}: body missing section {s!r}")
        if EM_DASH in text:
            problems.append(f"{rid}: contains an em-dash")
        if _SCHEDULE.search(body):
            problems.append(f"{rid}: body contains build-schedule language (week N, phase N)")
        for m in _REF.finditer(body):
            dept, slug = m.group(1), m.group(2)
            if dept in departments and f"{dept}/{slug}" not in entries:
                problems.append(f"{rid}: body references unknown role {dept}/{slug}")
        lines = body.count("\n") + 1
        if lines < 40:
            problems.append(f"{rid}: body is only {lines} lines; the template needs real content in every section")
    return problems
