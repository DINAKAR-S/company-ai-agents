# Onboarding: from "what do I need?" to a team

Two parts, deliberately split:

1. **The interviewer** (`interviewer/AGENT.md`) is an LLM prompt. It talks to a person and produces `answers.json`. Install it as a Claude Code subagent (copy to `.claude/agents/`) or paste it as the system prompt of any chat model.
2. **The composer** (`src/orgchart/compose.py`) is plain Python. It reads `answers.json` and picks roles by visible rules. No model call, so two people with the same answers get the same team, and a contributor can read exactly why a role was picked.

You can skip the interviewer entirely:

```
python -m orgchart hire
```

asks the same questions in the terminal.

## answers.json

| Field | Values | Effect |
|---|---|---|
| `company` | text | appears in the Team section of every exported prompt |
| `stage` | `idea`, `early`, `growth`, `scale` | growth and scale add the manager above each picked IC; scale adds a controller and a compliance analyst |
| `headcount` | number | 50+ behaves like growth, 200+ like scale |
| `motion` | `self-serve`, `sales-led`, `both`, `none` | sales-led adds SDR and AE; self-serve adds growth PM and lifecycle email |
| `tools` | vendor slugs | some vendors imply a role (Attio or HubSpot imply RevOps, Zendesk implies Tier 1 support) |
| `pains` | keys from `compose.py` `PAINS` | each pain adds up to three roles |
| `max_roles` | number | hard cap; the router is always kept |

The router (`c-suite/chief-of-staff`) is always first. It reads a request and names which teammate should take it, so a user with eight agents does not have to remember eight names.
