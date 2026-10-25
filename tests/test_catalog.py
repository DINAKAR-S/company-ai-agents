"""Properties of the catalog itself. These are the gates a contributor's PR hits."""

import re

from orgchart import validate
from orgchart.catalog import LEVELS, REQUIRED_SECTIONS


def test_repo_validates_clean(root):
    assert validate(root) == []


def test_exactly_one_root_and_it_is_the_ceo(catalog):
    roots = [r for r in catalog.roles.values() if r.reports_to is None]
    assert [r.id for r in roots] == ["c-suite/ceo"]
    assert roots[0].escalates_to is None


def test_every_chain_reaches_the_ceo(catalog):
    for rid in catalog.roles:
        chain = catalog.chain(rid)
        assert chain[-1] == "c-suite/ceo", f"{rid} chain ends at {chain[-1]}"
        assert len(chain) == len(set(chain)), f"{rid} chain repeats a role"


def test_every_department_has_at_least_one_role(catalog):
    for dept in catalog.departments:
        assert catalog.by_department(dept), dept


def test_no_manager_reports_to_a_lower_level(catalog):
    rank = {lvl: i for i, lvl in enumerate(LEVELS)}
    for r in catalog.roles.values():
        if r.reports_to:
            boss = catalog.roles[r.reports_to]
            assert rank[boss.level] <= rank[r.level], f"{r.id} ({r.level}) reports to {boss.id} ({boss.level})"


def test_bodies_have_every_section_in_order(catalog):
    for r in catalog.roles.values():
        positions = [r.body.find(s) for s in REQUIRED_SECTIONS]
        assert all(p >= 0 for p in positions), r.id
        assert positions == sorted(positions), f"{r.id}: sections out of order"


def test_what_you_do_has_eight_to_twelve_tasks(catalog):
    for r in catalog.roles.values():
        section = r.body.split("## What you do", 1)[1].split("## ", 1)[0]
        bullets = [ln for ln in section.splitlines() if ln.startswith("- ")]
        assert 8 <= len(bullets) <= 12, f"{r.id}: {len(bullets)} tasks"


def test_working_rules_require_human_approval(catalog):
    """Every agent must refuse to act externally without a human. This is the one
    property that makes the catalog safe to hand to a stranger."""
    for r in catalog.roles.values():
        section = r.body.split("## Working rules", 1)[1].split("## ", 1)[0].lower()
        assert "approval" in section or "approve" in section, f"{r.id}: no approval rule"
        assert "never invent" in section or "do not invent" in section or "never fabricate" in section, f"{r.id}: no anti-fabrication rule"


def test_no_credential_values_anywhere(catalog):
    """Env var names are fine; anything that looks like a real key is not."""
    looks_like_secret = re.compile(r"(sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|xox[bp]-[A-Za-z0-9-]{10,})")
    for r in catalog.roles.values():
        assert not looks_like_secret.search(r.body), r.id


def test_summary_is_one_sentence(catalog):
    for r in catalog.roles.values():
        s = r.summary
        assert 20 <= len(s) <= 400, f"{r.id}: {s!r}"
        assert s.endswith((".", "!", "?")), r.id
