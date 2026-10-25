# company-ai-agents

128 AI agents arranged as a company org chart, for companies of 5 to 100 people who need automation done this quarter, not next year. Every agent is a ready system prompt with a reporting line, an approval gate and escalation rules. A composer picks a team for your company. A named panel of specialists debates your problem and hands back a plan, the edge cases, and the requirements. Exporters write the team out for Claude Code, Anthropic Managed Agents, or n8n.

## The scenario

Monday morning at a twelve-person B2B software company. Forty leads came back from a trade show as a spreadsheet. Three support tickets are waiting. A customer's renewal is due in thirty days. The founder opens a chat with a general model and types "help me with these leads". She gets a friendly paragraph of advice and a list of generic email templates. She spends the morning doing the work herself.

Same Monday, same company, with this repo cloned. She opens Claude Code and pastes one line:

```
Read onboarding/problem-solver/AGENT.md and act as that agent. Here is our website text and the tools we use: ...
Our problem: leads from events are never followed up, and support tickets pile up after every release.
```

The Problem Solver asks two questions, writes down what it learned, and seats a panel: Steven (Data and AI Solutions Architect) opens, Priya (Sales Development Representative), Mateo (Support Escalation Lead), Aisha (Revenue Operations Manager), Hiroshi (Customer Success Manager), and Lena (Chief of Staff) moderates. Each gives a position: approach, steps, what in the present setup will break (the helpdesk API rate limit at her ticket volume, the CRM with three duplicate records per company), edge cases a careful engineer would test for, and the questions the company must answer. They read each other's positions and argue. Lena decides, and writes `plan.md`, `edge-cases.md` and `requirements.md`. Ten minutes. The founder reads the three edge cases most likely to bite her and the first thing to do this afternoon.

Then she asks for the team itself:

```
python -m orgchart hire
```

Seven questions later the composer prints six agents with the reason each was picked and writes them into `.claude/agents/`. She types "here are 40 leads from the show, find the right contact at each and draft a first email" and the SDR agent returns a table of contacts with confidence ratings, ten prioritised accounts, ten drafts under 120 words each marked "awaiting approval", and the list of companies where nothing was found. It did not send anything. Its prompt forbids that. When a lead asks about pricing, the SDR agent ends its reply with `ESCALATE: sales/account-executive` and a memo, because that is what an SDR does in a real company.

The agents are not magic. They are what a careful operator would write as a job description for each seat, turned into a prompt, with the rules a company would want before letting software near its CRM. The panel is six opinionated specialists and a moderator producing a strong first draft in minutes, not a final design.

## Situation, without, with

| Situation | Without this repo | With this repo |
|---|---|---|
| "What AI agents does my company need?" | Browse a list of 100 engineering subagents, guess | Answer seven questions; the composer picks and explains each pick |
| "How do I solve this?" with a real company context | One model, one opinion, no pushback | A named panel debates it over three rounds and writes plan, edge cases and requirements |
| The panel should know what it got wrong last time | Start from zero every time | Lessons file: what the panel missed is injected into the next panel; you can add your own |
| A sales, finance, HR or legal role | Write the prompt from scratch | 128 roles, every department, same structure, validated |
| Agent needs a boss | Flat list, no escalation | Every role has `reports_to` and `escalates_to`; exporters make escalation explicit per runtime |
| Safety before the agent touches a system of record | Hope the model is careful | Every prompt refuses external sends and record changes without human approval; a test enforces it across all 128 |
| Same team on Claude Code, Managed Agents and n8n | Three hand-written versions | One source file, three exporters |
| Contributor adds a role with a typo in `reports_to` | Nobody notices until it breaks | Validator rejects it in CI, with a line that says which id is wrong |
| Skills backed by evidence | Author's opinion | Pipeline to count skills across real job postings per role; scaffolded, not yet run (see below) |

Rows that other collections already do: large curated lists of Claude Code subagents exist (wshobson/agents, VoltAgent/awesome-claude-code-subagents, davila7/claude-code-templates) and several are deeper on engineering roles than this repo is. This repo's difference is the whole company, the hierarchy, the composer, the debating panel, and the runtime exporters, not a better backend-engineer prompt.

## Run it in sixty seconds

```
git clone https://github.com/DINAKAR-S/company-ai-agents
cd company-ai-agents
python -m pip install -e .
python -m orgchart tree                                   # the whole chart
python -m orgchart show sales/sdr                         # one agent
python -m orgchart find "support tickets pile up after every release"   # who should be in the room
python -m orgchart hire --out team.json                   # answer the questions, get a team
python -m orgchart export --team team.json --to claude-code --out ./my-company
```

No dependencies beyond Python 3.10+ for everything above. The panel (`solve`) calls the Anthropic API and needs `pip install -e ".[solve]"` plus `ANTHROPIC_API_KEY` or `ant auth login`; `solve --dry-run` needs neither.

## Use it from Claude Code

Open Claude Code in the cloned folder and paste one of these.

**Solve a problem** (the panel):

```
Read onboarding/problem-solver/AGENT.md and act as that agent.
Company: <paste your website text, product description, tools, headcount>
Problem: <what hurts>
```

**Build my team** (the composer):

```
Read onboarding/interviewer/AGENT.md and act as that agent. Ask me the questions, then run the commands.
```

**Just one role, right now:**

```
Read agents/finance/accounts-receivable/AGENT.md and act as that agent. Here is our ageing report: ...
```

To make them permanent, copy the files into `.claude/agents/` (or run `export --to claude-code`, which does that for a whole team with the right tools and model per role). The Problem Solver and Interviewer talk like colleagues: short, a little funny, honest about what is hard. The panel's written outputs stay plain.

## Use it from any other IDE or agent

Every agent is a Markdown file whose body is the system prompt. Anything that accepts a system prompt accepts these.

| Where | How |
|---|---|
| Cursor, Windsurf, Cline, Continue | Add the repo as a rules or docs folder, or paste an `AGENT.md` body into a custom mode or rules file. `onboarding/problem-solver/AGENT.md` works as a rule that drives the CLI through the agent's terminal. |
| GitHub Copilot, Codex CLI, Gemini CLI, Aider | Point the tool at the file: "read agents/sales/sdr/AGENT.md and act as it". For a persistent setup, copy the body into the tool's instructions file (`.github/copilot-instructions.md`, `AGENTS.md`, `GEMINI.md`, `.aider.conf.yml` read-file list). |
| Anthropic Managed Agents | `python -m orgchart export --team team.json --to managed-agents --out ./managed`, then `ant apply ./managed/agents ./managed/environments`. Hosted, scheduled, no server of yours. |
| n8n | `python -m orgchart export --team team.json --to n8n --out ./n8n`, then paste each file's `systemMessage` into an AI Agent node's system prompt. The last line of an agent reply carries `{"escalate_to": ...}` so the workflow can branch. |
| ChatGPT, Gemini, any chat | Paste the body of one `AGENT.md` as the first message or custom instructions. You lose the hierarchy and approval wiring but keep the role. |
| Your own code | `from orgchart import load_catalog; cat = load_catalog("."); cat.roles["sales/sdr"].body` is the prompt. `find`, `compose`, `solve` and `export_team` are plain functions. |

The rule that makes this portable: no agent file depends on a runtime feature. Tools and vendors are named generically in front matter and the exporters do the mapping.

## What it does today

- **128 roles, 13 departments, 4 levels.** C-suite, engineering, data and AI, product and design, sales, marketing, customer success and support, finance, people, operations, legal, strategy, executive support. `python -m orgchart list` shows them all.
- **One file per role**, `agents/<department>/<slug>/AGENT.md`. Front matter carries id, reporting line, level, model hint, generic tools, example vendors, triggers and tags. The body is the system prompt: what you do, skills, what you need, working rules, escalate when, hand-offs, KPIs, an example request with the shape of the answer.
- **A finder** (`find`): ranks roles for a problem by term overlap with their title, tags, skills and tasks, with a small alias table so "RAG" reaches the roles that say "retrieval". A role matching only your company description never outranks one matching the question. No model call.
- **A panel** (`solve`): lead + top matches + moderator, first names assigned by hashing the role id, three rounds (position, critique, decision) through the Messages API with strict JSON schemas, writes `debate.md`, `plan.md`, `edge-cases.md`, `requirements.md`, `panel.json`. One failed call does not end the session; what completed is written and the error recorded. Details in `docs/solve.md`.
- **Lessons** (`lesson`): what a panel missed until critique and what it had to leave open goes into `orgchart-lessons.jsonl` and into the next panel's prompts. Add your own with one command. The panel gets better for your company over time, in a file you can read and edit.
- **A composer** (`hire`) with visible rules: pains map to roles, vendors imply roles, sales motion adds the funnel, growth stage adds the manager above each pick. Same answers, same team, reason printed for every pick.
- **Three exporters.** `claude-code` writes `.claude/agents/<slug>.md` with the right tool list and model tier. `managed-agents` writes `agents/<slug>.md` plus `environments/cloud.yaml` in the layout `ant apply` reads, web tools off unless the role needs them. `n8n` writes one JSON per role. Each adds a Team section so the agent knows its teammates and how escalation works in that runtime.
- **A validator** (`validate`): ids, reporting lines, exactly one root, no cycles, required sections, front matter order, allowed tools, every `dept/slug` reference in prose resolves, no em-dashes, no build-schedule language.
- **Two front-door agents** for Claude Code: `onboarding/problem-solver` (talks, finds, runs the panel, records lessons) and `onboarding/interviewer` (asks, composes, exports).
- **Integration recipes** for Attio, HubSpot, Slack, Google Workspace and Linear: how each runtime reaches the vendor, which environment variables, which agents use it. Names only, never values.
- **A research pipeline** (`research/`) that collects job postings for a role, extracts skills with the Message Batches API under a strict schema, and writes counts into the role's Skills section with a dated run log.

## What is not built yet

| Gap | What it means for you today |
|---|---|
| Research pipeline has not been run across the catalog | Skills sections are editorial. No file shows a count it did not earn. Run `research/pipeline/` on a role and open a pull request to change that. |
| Panel runs sequentially and does not total its cost | Thirteen calls for a six-person panel, one after another; a few minutes. Token usage is in each API response but the script does not add it up yet. `--size 4` roughly halves both. |
| Hierarchy executes only where the runtime allows it | On Claude Code, subagents cannot call each other; escalation is a marker the main session acts on. On Managed Agents, real delegation needs a multiagent roster you configure. On n8n, you branch on the JSON marker. |
| Finder is term overlap, not understanding | Phrase the problem with the words a practitioner would use (systems, symptoms, who is affected). The alias table covers common shorthand; add to it when a role you expected is missed. |
| Depth is even, not deep | Every role is 80 to 95 lines. A senior practitioner in any one role will find things to add. That is the contribution the repo most wants. |
| Five integration recipes | Other vendors work through the generic capability names in each file, but you write the wiring. |
| Composer rules are hand-written | Twenty pain areas and nineteen vendors. A pain outside the list is reported as a warning, not guessed. |
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
tests:                 73 (pytest), on Linux and Windows, Python 3.10 and 3.12
```

Regenerate: `python scripts/stats.py`. Tests: `python -m pytest -q`. The suite checks properties, not snapshots: every chain reaches the CEO, no manager reports to a lower level, every role refuses to act externally without approval, hostile composer inputs are normalised, a context-only match never leads the finder, a panelist failing does not end the panel, everything failing still writes the transcript, lessons round-trip into the next panel's prompts, a second export overwrites cleanly.

## Layout

```
catalog.json                 index of roles: id, title, department, reports_to, level
agents/<dept>/<slug>/AGENT.md   one prompt per role
agents/TEMPLATE.md           copy this for a new role
src/orgchart/                frontmatter parser, catalog, validator, finder, composer, solve, exporters, CLI
onboarding/                  problem-solver and interviewer agents, how answers become a team
integrations/                vendor recipes, env var names only
research/                    job-posting pipeline (collect, extract, merge)
docs/solve.md                the panel protocol, lessons, cost
docs/lessons.md              what went wrong building this and what changed
scripts/stats.py             the numbers above
tests/                       pytest, property-based where it matters
```

## License

MIT.
