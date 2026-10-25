"""Turn answers about a company into a team of roles.

The rules are deliberately plain and visible. An LLM interviewer collects the
answers (see onboarding/interviewer/AGENT.md); this module decides, so the
result is reproducible and a contributor can read exactly why a role was
picked. Nothing here calls a model.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .catalog import Catalog

STAGES = ("idea", "early", "growth", "scale")
MOTIONS = ("self-serve", "sales-led", "both", "none")
PAINS = {
    "leads": ["sales/sdr", "sales/account-executive", "marketing/content-lead"],
    "closing": ["sales/account-executive", "sales/sales-engineer", "sales/deal-desk"],
    "support": ["customer/support-tier1", "customer/support-tier2", "customer/knowledge-base-manager"],
    "churn": ["customer/customer-success-manager", "customer/renewals-specialist", "customer/voice-of-customer-analyst"],
    "hiring": ["people/recruiter", "people/technical-recruiter", "people/onboarding-coordinator"],
    "finance": ["finance/fp-and-a-analyst", "finance/accounts-receivable", "finance/accounts-payable"],
    "shipping": ["engineering/engineering-manager", "engineering/qa-engineer", "engineering/release-manager"],
    "reliability": ["engineering/devops-sre", "engineering/security-engineer"],
    "data": ["data-ai/data-analyst", "data-ai/data-engineer", "data-ai/analytics-engineer"],
    "ai": ["data-ai/data-ai-solutions-architect", "data-ai/prompt-engineer", "data-ai/ml-engineer"],
    "marketing": ["marketing/content-lead", "marketing/seo-specialist", "marketing/social-media-manager"],
    "brand": ["marketing/product-marketer", "marketing/brand-designer", "marketing/pr-comms"],
    "compliance": ["legal/privacy-officer", "legal/security-compliance", "legal/contracts-manager"],
    "contracts": ["legal/contracts-manager", "sales/deal-desk"],
    "planning": ["executive-support/okr-coordinator", "operations/program-manager", "c-suite/chief-of-staff"],
    "product": ["product-design/product-manager", "product-design/ux-researcher", "product-design/product-designer"],
    "fundraising": ["strategy/investor-relations", "finance/fp-and-a-analyst", "executive-support/board-ops"],
    "pricing": ["strategy/pricing-strategist", "strategy/competitive-intelligence"],
    "operations": ["operations/project-manager", "operations/process-improvement", "operations/vendor-manager"],
    "it": ["operations/it-admin", "engineering/security-engineer"],
}
# Vendors a company says it uses imply roles that live in those tools.
TOOL_IMPLIES = {
    "attio": ["sales/revops"], "hubspot": ["sales/revops", "marketing/marketing-ops"],
    "salesforce": ["sales/revops"], "zendesk": ["customer/support-tier1"],
    "intercom": ["customer/support-tier1"], "greenhouse": ["people/recruiter"],
    "lever": ["people/recruiter"], "ashby": ["people/recruiter"],
    "quickbooks": ["finance/accounts-payable", "finance/accounts-receivable"],
    "xero": ["finance/accounts-payable", "finance/accounts-receivable"],
    "stripe": ["finance/billing-ops"], "jira": ["operations/scrum-master"],
    "linear": ["engineering/engineering-manager"], "github": ["engineering/backend-engineer"],
    "snowflake": ["data-ai/analytics-engineer"], "bigquery": ["data-ai/analytics-engineer"],
    "dbt": ["data-ai/analytics-engineer"], "figma": ["product-design/product-designer"],
    "notion": ["executive-support/internal-comms"], "slack": [],
}
ROUTER = "c-suite/chief-of-staff"


@dataclass
class Answers:
    company: str = "the company"
    stage: str = "early"
    headcount: int = 5
    industry: str = ""
    motion: str = "sales-led"
    tools: list[str] = field(default_factory=list)
    pains: list[str] = field(default_factory=list)
    max_roles: int = 12

    @classmethod
    def from_dict(cls, d: dict) -> Answers:
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        a = cls(**known)
        a.stage = a.stage if a.stage in STAGES else "early"
        a.motion = a.motion if a.motion in MOTIONS else "sales-led"
        a.headcount = max(0, _to_int(a.headcount, 0))
        a.tools = [str(t).lower().strip() for t in (a.tools or []) if t is not None and str(t).strip()]
        a.pains = [str(p).lower().strip() for p in (a.pains or []) if p is not None and str(p).strip()]
        a.max_roles = max(1, min(_to_int(a.max_roles, 12), 500))
        a.company = " ".join(str(a.company or "the company").split())[:120] or "the company"
        return a


def _to_int(value, default: int) -> int:
    """Caller values arrive as strings, floats, None or junk. Never crash on them."""
    if value is None or isinstance(value, bool):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


@dataclass
class Team:
    company: str
    answers: dict
    roles: list[dict]       # {id, reason}
    warnings: list[str]

    def ids(self) -> list[str]:
        return [r["id"] for r in self.roles]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, text: str) -> Team:
        d = json.loads(text)
        return cls(company=d["company"], answers=d["answers"], roles=d["roles"], warnings=d.get("warnings", []))

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.write_text(self.to_json() + "\n", encoding="utf-8")
        return p


def compose(catalog: Catalog, answers: Answers | dict) -> Team:
    a = answers if isinstance(answers, Answers) else Answers.from_dict(answers)
    picked: dict[str, str] = {}
    warnings: list[str] = []

    def add(role_id: str, reason: str) -> None:
        if role_id not in catalog.roles:
            warnings.append(f"rule wanted {role_id} but it is not in the catalog")
            return
        picked.setdefault(role_id, reason)

    # The router comes first: it reads a request and names who should take it.
    add(ROUTER, "routes every request to the right teammate and keeps the decision log")

    for pain in a.pains:
        if pain not in PAINS:
            warnings.append(f"unknown pain {pain!r} ignored; known: {sorted(PAINS)}")
            continue
        for rid in PAINS[pain]:
            add(rid, f"you said {pain!r} hurts")

    for tool in a.tools:
        if tool not in TOOL_IMPLIES:
            warnings.append(f"no rule for tool {tool!r}; it will still appear in integration recipes")
            continue
        for rid in TOOL_IMPLIES[tool]:
            add(rid, f"you use {tool}")

    if a.motion in ("sales-led", "both"):
        add("sales/sdr", "sales-led motion needs top-of-funnel")
        add("sales/account-executive", "sales-led motion needs someone to run deals")
    if a.motion in ("self-serve", "both"):
        add("product-design/growth-pm", "self-serve motion lives or dies on activation")
        add("marketing/email-marketer", "self-serve motion needs lifecycle email")

    # Stage and size decide how much management layer is worth having.
    if a.stage in ("growth", "scale") or a.headcount >= 50:
        for rid in list(picked):
            parent = catalog.roles[rid].reports_to
            if parent and catalog.roles[parent].level in ("manager", "director"):
                add(parent, f"manager for {rid} once the team is this size")
    if a.stage == "scale" or a.headcount >= 200:
        add("finance/controller", "scale stage needs a close process")
        add("legal/compliance-analyst", "scale stage needs a compliance owner")

    if not a.pains and not a.tools and a.motion == "none":
        warnings.append("no pains, tools or motion given; team is the router plus nothing. Answer at least one question.")

    roles = [{"id": rid, "reason": why} for rid, why in picked.items()]
    if len(roles) > a.max_roles:
        warnings.append(f"{len(roles)} roles matched; keeping the first {a.max_roles} (router first, then in the order your answers were given)")
        roles = roles[: a.max_roles]
    return Team(company=a.company, answers=asdict(a), roles=roles, warnings=warnings)


QUESTIONS = [
    ("company", "Company name?", "the company"),
    ("stage", f"Stage {STAGES}?", "early"),
    ("headcount", "How many people work there (a number)?", "5"),
    ("industry", "Industry in a few words?", ""),
    ("motion", f"How do you sell {MOTIONS}?", "sales-led"),
    ("tools", "Tools you already use (comma separated vendor names, e.g. attio, slack, github)?", ""),
    ("pains", f"What hurts most right now? Pick from {sorted(PAINS)} (comma separated)", ""),
    ("max_roles", "Maximum number of agents to start with?", "8"),
]


def ask_in_terminal(input_fn=input, print_fn=print) -> Answers:
    """Plain terminal interview. The LLM interviewer is optional sugar on top."""
    d: dict = {}
    for key, prompt, default in QUESTIONS:
        try:
            raw = input_fn(f"{prompt} [{default}] ").strip() or default
        except EOFError:
            # No terminal attached (CI, a pipe, an agent's shell): say what to do instead of a traceback.
            raise SystemExit("no input available; pass --answers answers.json instead of the interview") from None
        if key in ("tools", "pains"):
            d[key] = [x.strip() for x in raw.split(",") if x.strip()]
        elif key in ("headcount", "max_roles"):
            try:
                d[key] = int(raw)
            except ValueError:
                print_fn(f"  not a number, using {default}")
                d[key] = int(default)
        else:
            d[key] = raw
    return Answers.from_dict(d)
