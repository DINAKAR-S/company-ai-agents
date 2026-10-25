# orgchart-agents

A company org chart of AI agents. 128 role definitions across 13 departments, each one a ready system prompt with reporting lines, approval gates and escalation rules. An interviewer that picks a team for your company. Exporters that write that team out as Claude Code subagents, Anthropic Managed Agents files, or n8n AI Agent prompts.

## The scenario

Monday morning at a twelve-person B2B software company. Forty leads came back from a trade show as a spreadsheet. Three support tickets are waiting. A customer's renewal is due in thirty days. The founder opens a chat with a general model and types "help me with these leads". She gets a friendly paragraph of advice and a list of generic email templates. She spends the morning doing the work herself.

Same Monday, same company, with this repo cloned:

```
python -m orgchart hire
```

Seven questions later (stage, headcount, how they sell, which tools, what hurts: she says leads and support, six agents to start) the composer prints a team: a Chief of Staff agent to route requests, an SDR, an Account Executive, a Content Lead, a Tier 1 Support agent, a Tier 2 Support Engineer, each with the reason it was picked. One command writes them into `.claude/agents/`. The founder types "here are 40 leads from the show, find the right contact at each and draft a first email" and the SDR agent returns a table of contacts with a confidence rating, ten prioritised accounts, ten drafts under 120 words each marked "awaiting approval", and the list of companies where nothing was found. It did not send anything. Its prompt forbids that. When a lead asks about pricing, the SDR agent ends its reply with `ESCALATE: sales/account-executive` and a memo, because that is what the SDR role does in a real company.

The agents are not magic. They are what a careful operator would write as a job description for each seat, turned into a prompt, with the rules a company would want before letting software near its CRM.

## Situation, without, with

| Situation | Without this repo | With this repo |
|---|---|---|
| "What AI agents does my company need?" | Browse a list of 100 engineering subagents, guess | Answer seven questions; the composer picks and explains each pick |
| A sales, finance, HR or legal role | Write the prompt from scratch | 128 roles, every department, same structure, validated |
| Agent needs a boss | Flat list, no escalation | Every role has `reports_to` and `escalates_to`; exporters make escalation explicit per runtime |
| Safety before the agent touches a system of record | Hope the model is careful | Every prompt refuses external sends and record changes without human approval; a test enforces it across all 128 |
| Same team on Claude Code, Managed Agents and n8n | Three hand-written versions | One source file, three exporters |
| Contributor adds a role with a typo in `reports_to` | Nobody notices until it breaks | Validator rejects it in CI, with a line that says which id is wrong |
| Skills backed by evidence | Author's opinion | Pipeline to count skills across real job postings per role; scaffolded, not yet run (see below) |

Rows that other collections already do: large curated lists of Claude Code subagents exist (wshobson/agents, VoltAgent/awesome-claude-code-subagents, davila7/claude-code-templates) and several are deeper on engineering roles than this repo is. This repo's difference is the whole company, the hierarchy, the composer, and the runtime exporters, not a better backend-engineer prompt.

## Run it in sixty seconds

```
git clone https://github.com/DINAKAR-S/orgchart-agents
cd orgchart-agents
python -m pip install -e .
python -m orgchart tree                       # the whole chart
python -m orgchart show sales/sdr             # one agent
python -m orgchart hire --out team.json       # answer the questions
python -m orgchart export --team team.json --to claude-code --out ./my-company
```

No dependencies beyond Python 3.10+. `pip install -e .` only registers the `orgchart` command; `PYTHONPATH=src python -m orgchart ...` works without installing.

Prefer a chat to a terminal? Copy `onboarding/interviewer/AGENT.md` into `.claude/agents/` and ask Claude Code "what agents does my company need". It runs the same two commands for you.

## What it does today

- **128 roles, 13 departments, 4 levels.** C-suite, engineering, data and AI, product and design, sales, marketing, customer success and support, finance, people, operations, legal, strategy, executive support. `python -m orgchart list` shows them all.
- **One file per role**, `agents/<department>/<slug>/AGENT.md`. Front matter carries id, reporting line, level, model hint, generic tools, example vendors, triggers and tags. The body is the system prompt: what you do, skills, what you need, working rules, escalate when, hand-offs, KPIs, an example request with the shape of the answer.
- **A composer** (`src/orgchart/compose.py`) with visible rules: pains map to roles, vendors imply roles, sales motion adds the funnel, growth stage adds the manager above each pick. No model call, so the same answers always give the same team and the reason for every pick is printed.
- **Three exporters.** `claude-code` writes `.claude/agents/<slug>.md` with the right tool list and model tier. `managed-agents` writes `agents/<slug>.md` plus `environments/cloud.yaml` in the layout `ant apply` reads, web tools off unless the role needs them. `n8n` writes one JSON per role with the system message and suggested tools for an AI Agent node. Each adds a Team section so the agent knows its teammates and how escalation works in that runtime.
- **A validator** (`python -m orgchart validate`) that checks the catalog against every file: ids, reporting lines, exactly one root, no cycles, required sections, front matter order, allowed tools, every `dept/slug` reference in prose resolves, no em-dashes, no build-schedule language.
- **Integration recipes** for Attio, HubSpot, Slack, Google Workspace and Linear: how each runtime reaches the vendor, which environment variables, which agents use it. Names only, never values.
- **A research pipeline** (`research/`) that collects job postings for a role, extracts skills with the Message Batches API under a strict schema, and writes counts into the role's Skills section with a dated run log.

## What is not built yet

| Gap | What it means for you today |
|---|---|
| Research pipeline has not been run across the catalog | Skills sections are editorial. No file shows a count it did not earn, and no claim is made that the skills came from the market yet. Run `research/pipeline/` on a role and open a pull request to change that. |
| Hierarchy executes only where the runtime allows it | On Claude Code, subagents cannot call each other; escalation is a marker the main session acts on. On Managed Agents, real delegation needs a multiagent roster you configure. On n8n, you branch on the JSON marker. The exporters say so in each prompt rather than hide it. |
| Depth is even, not deep | Every role is 80 to 95 lines. A senior practitioner in any one role will find things to add. That is the contribution the repo most wants. |
| Five integration recipes | Other vendors work through the generic capability names in each file, but you write the wiring. |
| Composer rules are hand-written | They cover twenty pain areas and nineteen vendors. A pain outside the list is reported as a warning, not guessed. |
| No web UI | Terminal and chat only. |
| Catalog modelled on a general software company | Manufacturing, healthcare, agencies and other shapes need roles this chart does not have. New departments are a pull request away (`CONTRIBUTING.md`). |

## Proof

Every number here comes from `python scripts/stats.py`, which CI runs on each push.

```
roles:                 128
departments:           13
levels:                exec 11, director 11, manager 5, ic 101
model hints:           deep 55, balanced 59, fast 14
tasks per agent:       9 to 11 (8 to 12 enforced by test)
cross-role references: 1415, dangling: 0
agents with an approval gate in Working rules: 128 of 128
validator problems:    0
```

Regenerate: `python scripts/stats.py`. Tests: `python -m pytest -q`. The test suite checks properties, not snapshots: every chain reaches the CEO, no manager reports to a lower level, every role refuses to act externally without approval, hostile composer inputs are normalised, a second export overwrites cleanly, a stale team file referencing a removed role is skipped rather than crashing.

## Layout

```
catalog.json                 index of roles: id, title, department, reports_to, level
agents/<dept>/<slug>/AGENT.md   one prompt per role
agents/TEMPLATE.md           copy this for a new role
src/orgchart/                frontmatter parser, catalog loader, validator, composer, exporters, CLI
onboarding/                  interviewer agent + how answers become a team
integrations/                vendor recipes, env var names only
research/                    job-posting pipeline (collect, extract, merge)
scripts/stats.py             the numbers above
tests/                       pytest, property-based where it matters
docs/lessons.md              what went wrong and what changed
```

## License

MIT.
