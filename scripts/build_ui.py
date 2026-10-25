"""Build docs/index.html: a single-file browser for the catalog.

No server, no dependencies, no framework. The catalog is embedded as JSON so the
page works from a file:// URL and from GitHub Pages. Rebuild after changing any
agent file:  python scripts/build_ui.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from orgchart import load_catalog
from orgchart.finder import ALIASES, STOPWORDS

# Small companies ask for these first; the page lists departments in this order.
DEPT_ORDER = ["marketing", "sales", "customer", "people", "finance", "operations", "data-ai",
              "product-design", "engineering", "legal", "strategy", "executive-support", "c-suite"]

TEMPLATE = (Path(__file__).resolve().parent / "ui_template.html").read_text(encoding="utf-8")


def terms(role):
    from orgchart.finder import role_terms
    return {k: sorted(v) for k, v in role_terms(role).items()}


def main() -> int:
    cat = load_catalog(ROOT)
    roles = []
    for r in cat.roles.values():
        roles.append({
            "id": r.id, "title": r.title, "department": r.department, "reports_to": r.reports_to,
            "escalates_to": r.escalates_to, "level": r.level, "model_hint": r.model_hint, "tags": r.tags,
            "summary": r.summary, "body": r.body, "name": r.name, "terms": terms(r),
        })
    data = {"departments": cat.departments, "roles": roles, "style": cat.style}
    html = (TEMPLATE.replace("__COUNT__", str(len(roles))).replace("__DEPTS__", str(len(cat.departments)))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__STOP__", json.dumps(sorted(STOPWORDS)))
            .replace("__ALIASES__", json.dumps(ALIASES))
            .replace("__DEPT_ORDER__", json.dumps(DEPT_ORDER)))
    out = ROOT / "docs" / "index.html"
    out.write_text(html, encoding="utf-8", newline="\n")
    print(f"{out} ({out.stat().st_size // 1024} KB, {len(roles)} roles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
