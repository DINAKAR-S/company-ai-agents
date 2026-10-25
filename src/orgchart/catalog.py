"""Load catalog.json and every agents/<dept>/<slug>/AGENT.md into one graph."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import frontmatter

ROLE_ID = re.compile(r"^[a-z0-9-]+/[a-z0-9-]+$")
LEVELS = ("exec", "director", "manager", "ic")
MODEL_HINTS = ("fast", "balanced", "deep")
TOOLS = (
    "crm", "email", "calendar", "web_search", "documents", "spreadsheets", "code",
    "database", "analytics", "ticketing", "chat", "design", "files", "finance_system",
    "hr_system", "ats", "contracts", "monitoring", "cloud",
)
REQUIRED_KEYS = (
    "id", "title", "department", "reports_to", "level", "model_hint",
    "tools", "integrations", "triggers", "escalates_to", "tags",
)
REQUIRED_SECTIONS = (
    "## What you do", "## Skills", "## What you need", "## Working rules",
    "## Escalate when", "## Hand-offs", "## KPIs", "## Example",
)


@dataclass
class Role:
    id: str
    title: str
    department: str
    reports_to: str | None
    level: str
    model_hint: str = "balanced"
    tools: list[str] = field(default_factory=list)
    integrations: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    escalates_to: str | None = None
    tags: list[str] = field(default_factory=list)
    body: str = ""
    path: Path | None = None
    name: str = ""   # first name used on panels and the page; assigned once per catalog

    @property
    def slug(self) -> str:
        return self.id.replace("/", "-")

    @property
    def summary(self) -> str:
        """First sentence of the body, used for one-line descriptions."""
        first = self.body.strip().split("\n", 1)[0]
        first = re.sub(r"\*\*(.+?)\*\*", r"\1", first)
        m = re.match(r"(.+?[.!?])(\s|$)", first)
        return (m.group(1) if m else first).strip()


@dataclass
class Catalog:
    root: Path
    departments: dict[str, str]
    roles: dict[str, Role]
    index: list[dict]  # raw catalog.json entries, in file order
    style: str = ""    # house style appended to every exported prompt

    def children(self, role_id: str) -> list[Role]:
        return [r for r in self.roles.values() if r.reports_to == role_id]

    def chain(self, role_id: str) -> list[str]:
        """Reporting chain from the role up to the root, inclusive."""
        out, cur, seen = [], role_id, set()
        while cur is not None and cur not in seen:
            seen.add(cur)
            out.append(cur)
            cur = self.roles[cur].reports_to if cur in self.roles else None
        return out

    def by_department(self, dept: str) -> list[Role]:
        return [r for r in self.roles.values() if r.department == dept]


def house_style(root: Path) -> str:
    """agents/STYLE.md, minus its title and intro: the 'How you talk' section appended to every prompt."""
    p = root / "agents" / "STYLE.md"
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8")
    return text[text.index("## How you talk"):].rstrip() + "\n" if "## How you talk" in text else text


def agent_path(root: Path, role_id: str) -> Path:
    return root / "agents" / Path(*role_id.split("/")) / "AGENT.md"


def load_index(root: Path) -> dict:
    with open(root / "catalog.json", encoding="utf-8") as f:
        return json.load(f)


def load_role_file(path: Path) -> Role:
    data, body = frontmatter.parse(path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise frontmatter.FrontMatterError(f"{path}: missing keys {missing}")
    return Role(
        id=data["id"], title=data["title"], department=data["department"],
        reports_to=data["reports_to"], level=data["level"],
        model_hint=data["model_hint"], tools=list(data["tools"] or []),
        integrations=list(data["integrations"] or []), triggers=list(data["triggers"] or []),
        escalates_to=data["escalates_to"], tags=list(data["tags"] or []),
        body=body, path=path,
    )


def load_catalog(root: str | Path, strict: bool = True) -> Catalog:
    """Load the catalog. With strict=True any unreadable AGENT.md raises;
    with strict=False roles whose file is missing are loaded from the index only
    (body empty), which the validator uses to report every problem at once."""
    root = Path(root)
    index = load_index(root)
    roles: dict[str, Role] = {}
    for entry in index["roles"]:
        if not ROLE_ID.match(entry["id"]):
            # The id becomes a path. Anything but department/slug never reaches the filesystem.
            raise ValueError(f"{entry['id']!r} is not a valid role id (department/slug)")
        path = agent_path(root, entry["id"])
        if path.exists():
            roles[entry["id"]] = load_role_file(path)
        elif strict:
            raise FileNotFoundError(f"{entry['id']}: {path} not found")
        else:
            roles[entry["id"]] = Role(
                id=entry["id"], title=entry["title"], department=entry["department"],
                reports_to=entry["reports_to"], level=entry["level"],
            )
    from .names import global_names
    for rid, n in global_names(list(roles)).items():
        roles[rid].name = n
    return Catalog(root=root, departments=index["departments"], roles=roles, index=index["roles"], style=house_style(root))
