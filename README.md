# company-ai-agents

**An AI team for a company of 5 to 100 people. 135 roles, every department, each one a ready prompt. Tell Sam your problem, he brings the right specialists, they argue, you get a plan.**

![Sam and the panel: Steven, Priya, Mateo, Aisha, Hiroshi, Lena](docs/assets/hero.jpg)

Browse every role, search by problem, copy the prompt: **https://dinakar-s.github.io/company-ai-agents/**

## Try it in two minutes

```
git clone https://github.com/DINAKAR-S/company-ai-agents
cd company-ai-agents
python -m pip install -e .
```

Then open Claude Code in that folder and paste:

```
Read onboarding/problem-solver/AGENT.md and act as that agent.
Company: <your website text, what you sell, the tools you use, headcount>
Problem: <what hurts>
```

Sam reads what you gave him, shows a one-screen picture of your company so you can correct it, asks at most two questions, and seats a panel. Steven (Data and AI Solutions Architect) opens. Priya (Sales Development), Mateo (Support Escalation), Aisha (Revenue Ops), Hiroshi (Customer Success) argue the approach, say what in your current setup will break, and list the edge cases. Lena (Chief of Staff) decides and writes three files: `plan.md`, `edge-cases.md`, `requirements.md`. Ten minutes. Nothing is sent, posted or changed anywhere; every agent here refuses to act on a live system without a human yes.

No Claude Code? Everything also runs from the terminal, and any agent that reads this repo finds its instructions in [AGENTS.md](AGENTS.md).

## What you get

| | |
|---|---|
| **Sam, the Problem Solver** | The front door. Learns your company, shows it back to you, asks only what changes the answer, runs the panel, remembers what it got wrong. `onboarding/problem-solver/AGENT.md` |
| **135 roles** | Marketing (LinkedIn ghostwriter, Reddit writer, Instagram creator, short-video scriptwriter, newsletter writer, SEO, ads, PR...), sales (SDR, AE, call coach, RevOps, deal desk...), support and success, people and HR (recruiter, HR ops, onboarding, comp...), finance (AR, AP, FP&A, payroll...), operations, data and dashboards, product, engineering, legal, strategy, the C-suite. |
| **A panel that debates** | `solve`: lead, top matches, moderator. Position, critique, decision. Writes the debate and the three files. |
| **Memory** | `lesson`: what a panel missed goes into a file the next panel reads. Add your own in one line. |
| **A team for your company** | `hire`: seven questions, a team with the reason for every pick. |
| **Three runtimes** | `export` to Claude Code subagents, Anthropic Managed Agents (`ant apply` layout), or n8n AI Agent prompts. One source file. |
| **House style** | Every prompt talks the same way: straight to the point, one light line when it fits, asks only what it needs. `agents/STYLE.md`, appended to every export. |

## The commands

```
python -m orgchart find "leads from events are never followed up"     # who should be in the room
python -m orgchart solve --problem @problem.md --context @context.md   # the panel (needs an API key)
python -m orgchart solve --problem "..." --dry-run                      # the panel's prompts, no key
python -m orgchart lesson add "our helpdesk API allows 100 req/min"    # teach the next panel
python -m orgchart hire --out team.json                                # your team
python -m orgchart export --team team.json --to claude-code --out .    # or managed-agents, n8n
python -m orgchart tree | list | show sales/sdr | validate
```

`solve` without `--dry-run` needs `pip install -e ".[solve]"` and `ANTHROPIC_API_KEY` (or `ant auth login`). Everything else is zero-dependency Python 3.10+.

## Use one role anywhere

Every role is a Markdown file whose body is the system prompt.

| Where | How |
|---|---|
| Claude Code | `Read agents/marketing/linkedin-ghostwriter/AGENT.md and act as that agent. Here are my last ten posts: ...` or `export --to claude-code` for a whole team into `.claude/agents/` |
| Cursor, Windsurf, Cline, Copilot, Codex, Gemini CLI, Aider | Point it at the file, or paste the body into the tool's rules or instructions file |
| Managed Agents | `export --to managed-agents`, then `ant apply` |
| n8n | `export --to n8n`, paste `systemMessage` into an AI Agent node |
| ChatGPT, Gemini, any chat | Paste the body as the first message |
| Your code | `from orgchart import load_catalog; load_catalog(".").roles["sales/sdr"].body` |

The web page does the copying for you: pick a role, "Copy the prompt" or "Copy as Claude Code subagent".

## Honest notes

| What | Today |
|---|---|
| The panel is a first draft | Six opinionated specialists and a moderator, in minutes. Strong start, not a final design. |
| Skills are editorial | A pipeline exists to count skills across real job postings per role (`research/`). It has not been run yet. |
| Hierarchy runs where the runtime allows | Claude Code subagents cannot call each other; escalation is a marker the main session routes. Managed Agents can delegate with a roster you configure. n8n branches on a JSON marker. |
| `find` is word overlap | With an alias table, not semantic search. Use practitioner words: tickets, leads, invoices, candidates, churn. |
| Depth is even | Every role is 80 to 95 lines. If you have done one of these jobs, you will see what to add. That is the pull request this repo wants most. |
| Catalog is a software company | Manufacturing, clinics, agencies need roles this chart does not have yet. New departments are a pull request away. |

Other collections of Claude Code subagents exist (wshobson/agents, VoltAgent/awesome-claude-code-subagents, davila7/claude-code-templates) and go deeper on engineering. This repo's difference is the whole company, the hierarchy, Sam, the panel, the memory, and the three runtimes.

## Proof

From `python scripts/stats.py`, run by CI on every push on Linux and Windows:

```
roles: 135   departments: 13   approval gate in every role: 135 of 135
cross-role references: 1400+, dangling: 0   validator problems: 0   tests: 77
```

## Layout

```
agents/<dept>/<slug>/AGENT.md   one prompt per role        agents/STYLE.md   house style
onboarding/                     Sam (problem-solver), interviewer (hire)
src/orgchart/                   finder, composer, solve, lessons, exporters, validator, CLI
docs/index.html                 the browser page (scripts/build_ui.py)   docs/solve.md   the panel protocol
integrations/                   Attio, HubSpot, Slack, Google Workspace, Linear recipes
research/                       skills-from-job-postings pipeline
AGENTS.md  llms.txt             for agents reading this repo
```

MIT. Contributions: `CONTRIBUTING.md`. Names in the image and the transcripts are labels, not people.
