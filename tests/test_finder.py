import pytest

from orgchart.finder import find, tokens
from orgchart.names import NAMES, assign, name_for


def test_tokens_drop_stopwords_and_short_words():
    assert tokens("We need to fix the CRM and our RAG pipeline") == {"fix", "crm", "rag", "pipeline"}


def test_support_problem_finds_support_roles_first(catalog):
    hits = find(catalog, "support tickets pile up and customers wait days for a reply", limit=5)
    ids = [m.role.id for m in hits]
    assert any(i.startswith("customer/") for i in ids[:3]), ids
    assert all(m.matched for m in hits)


def test_data_problem_finds_data_roles(catalog):
    hits = find(catalog, "build a RAG pipeline over our contracts with evals and a vector database", limit=5)
    ids = [m.role.id for m in hits]
    assert any(i.startswith("data-ai/") for i in ids[:3]), ids


def test_context_counts_less_than_the_problem(catalog):
    ctx = "We are a payroll and accounting firm. " * 20
    with_ctx = find(catalog, "leads from the trade show are not followed up", ctx, limit=3)
    problem_terms = {"leads", "trade", "show", "followed", "prospecting", "outbound", "pipeline"}
    # payroll roles match the context strongly, but a context-only match must never take the top spot
    assert set(with_ctx[0].matched) & problem_terms, with_ctx[0].role.id
    assert not with_ctx[0].role.id.startswith("finance/")


def test_empty_problem_is_an_error(catalog):
    with pytest.raises(ValueError):
        find(catalog, "   ")


def test_nonsense_problem_returns_empty_not_crash(catalog):
    assert find(catalog, "zzzz qqqq xxxx") == []


def test_exclude_and_limit(catalog):
    hits = find(catalog, "renewal churn health score", limit=2, exclude={"customer/renewals-specialist"})
    assert len(hits) == 2
    assert "customer/renewals-specialist" not in [m.role.id for m in hits]


def test_names_are_stable_and_unique_within_a_panel():
    assert name_for("sales/sdr") == name_for("sales/sdr")
    ids = [f"dept/role-{i}" for i in range(len(NAMES) + 3)]
    names = assign(ids)
    assert len(set(names.values())) == len(ids)
    assert all(n in NAMES or n.startswith("Panelist-") for n in names.values())


def test_hero_names_are_pinned_and_never_reused():
    from orgchart.names import PINNED
    assert name_for("data-ai/data-ai-solutions-architect") == "Steven"
    assert name_for("c-suite/chief-of-staff") == "Lena"
    ids = [f"dept/role-{i}" for i in range(30)]
    assert not set(assign(ids).values()) & set(PINNED.values())
