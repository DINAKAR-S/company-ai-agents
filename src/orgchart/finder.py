"""Find the roles whose skills match a problem.

Plain term overlap, no model call. The problem and company context are
tokenised; each role is scored by how many of those terms appear in its title,
tags, triggers, Skills section and What-you-do section, with the title and tags
weighted highest. The result says which terms matched, so a user can see why a
role was picked and a contributor can tune a role's tags when it is missed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .catalog import Catalog, Role

_WORD = re.compile(r"[a-z][a-z0-9+-]{2,}")
STOPWORDS = {"the", "and", "for", "with", "that", "this", "from", "into", "are", "our", "you", "your", "have", "has", "not", "can", "will", "how", "what", "when", "where", "why", "which", "who", "whom", "but", "all", "any", "more", "most", "some", "such", "than", "then", "them", "they", "their", "there", "these", "those", "about", "after", "before", "over", "under", "also", "just", "like", "need", "needs", "want", "wants", "use", "using", "used", "make", "makes", "made", "get", "gets", "got", "one", "two", "three", "per", "each", "every", "other", "another", "very", "much", "many", "lot", "lots", "way", "ways", "thing", "things", "able", "does", "doing", "done", "work", "works", "working", "company", "companies", "team", "teams", "people", "person", "problem", "problems", "solve", "solving", "should", "would", "could", "may", "might", "must", "because", "while", "being", "been", "were", "was", "its", "own", "out", "off", "onto", "upon", "via"}
WEIGHTS = {"title": 3.0, "tags": 3.0, "triggers": 1.5, "skills": 2.0, "tasks": 1.0, "integrations": 1.5}
# Shorthand people type versus the words the role files use. A query term expands to itself plus its aliases.
ALIASES = {
    "rag": ["retrieval", "llm", "embeddings"], "llm": ["model", "prompt", "ai"], "llms": ["model", "prompt", "ai"],
    "chatbot": ["assistant", "conversational", "support"], "bot": ["assistant", "automation"],
    "ai": ["machine", "learning", "model"], "ml": ["machine", "learning", "model"],
    "vector": ["embeddings", "retrieval"], "evals": ["evaluation", "eval"], "eval": ["evaluation"],
    "crm": ["pipeline", "leads", "accounts"], "leads": ["prospecting", "outbound", "pipeline"],
    "tickets": ["support", "helpdesk"], "ticket": ["support", "helpdesk"], "churn": ["renewal", "retention"],
    "invoices": ["billing", "receivable"], "invoice": ["billing", "receivable"], "hiring": ["recruiting", "candidates"],
    "automation": ["workflow", "pipeline"], "automate": ["workflow", "automation"], "dashboard": ["analytics", "reporting"],
    "security": ["access", "vulnerability", "compliance"], "gdpr": ["privacy", "consent"], "soc2": ["compliance", "controls"],
}


def tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in STOPWORDS}


def expand(terms: set[str]) -> set[str]:
    out = set(terms)
    for t in terms:
        out.update(ALIASES.get(t, ()))
    return out


def _section(body: str, heading: str) -> str:
    if heading not in body:
        return ""
    return body.split(heading, 1)[1].split("\n## ", 1)[0]


def role_terms(role: Role) -> dict[str, set[str]]:
    return {
        "title": tokens(role.title),
        "tags": tokens(" ".join(role.tags)),
        "triggers": tokens(" ".join(t.replace("_", " ") for t in role.triggers)),
        "integrations": tokens(" ".join(i.replace("-", " ") for i in role.integrations)),
        "skills": tokens(_section(role.body, "## Skills")),
        "tasks": tokens(_section(role.body, "## What you do")),
    }


@dataclass
class Match:
    role: Role
    score: float
    matched: list[str]


def find(catalog: Catalog, problem: str, context: str = "", limit: int = 6,
         exclude: set[str] | None = None) -> list[Match]:
    """Rank roles for a problem statement. Context terms count at half weight,
    because a company description mentions everything the company does and
    would otherwise drown the actual question."""
    if not problem or not problem.strip():
        raise ValueError("problem statement is empty")
    q = expand(tokens(problem))
    c = expand(tokens(context)) - q
    exclude = exclude or set()
    scored: list[tuple[int, Match]] = []
    for role in catalog.roles.values():
        if role.id in exclude:
            continue
        terms = role_terms(role)
        score, hits, problem_hits = 0.0, set(), 0
        for field, w in WEIGHTS.items():
            inter_q = terms[field] & q
            inter_c = terms[field] & c
            score += w * len(inter_q) + 0.5 * w * len(inter_c)
            problem_hits += len(inter_q)
            hits |= inter_q | inter_c
        if score > 0:
            scored.append((problem_hits, Match(role, round(score, 2), sorted(hits))))
    # A role that matches only the company description never outranks one that matches the question.
    scored.sort(key=lambda t: (-(t[0] > 0), -t[1].score, t[1].role.id))
    return [m for _, m in scored][: max(1, limit)]
