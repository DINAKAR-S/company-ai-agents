# For agents reading this repository

You are an AI agent (Claude Code, Codex, Cursor, Copilot, Gemini CLI, Aider, or any other) that has been pointed at this repo. This file tells you what is here and how to use it without reading everything.

## What this is

A catalog of AI agent definitions arranged as a company org chart. Each role is one Markdown file whose YAML front matter is metadata and whose body is a complete system prompt. A small Python package (`orgchart`, zero dependencies) finds roles for a problem, composes a team for a company, runs a named panel that debates a problem, remembers lessons, and exports teams to Claude Code, Anthropic Managed Agents, and n8n.

## Fast path by intent

| The person wants | Do this |
|---|---|
| "What agents does my company need?" | Read `onboarding/interviewer/AGENT.md` and act as it. It ends by running `python -m orgchart hire --answers answers.json` and an `export`. |
| "How do I solve <problem>?" | Read `onboarding/problem-solver/AGENT.md` and act as it. It runs `python -m orgchart find` then `python -m orgchart solve`. |
| "Be our <role> for a moment" | Read `agents/<department>/<slug>/AGENT.md`, then act as that role. `python -m orgchart list` gives every id. Append `agents/STYLE.md` to the prompt. |
| "Add a role" | Copy `agents/TEMPLATE.md`, add the role to `catalog.json`, run `python -m orgchart validate` until it prints `no problems`. See `CONTRIBUTING.md`. |
| "Run this on Managed Agents / n8n" | `python -m orgchart export --team team.json --to managed-agents|n8n --out <dir>`. The output is the runtime's native file layout. |

## Commands you can run

```
python -m orgchart validate                 # catalog and files consistent? exit 0 when yes
python -m orgchart list | tree | show <id>  # browse
python -m orgchart find "<problem>" [--context @file]            # ranked roles, no model call
python -m orgchart hire --answers answers.json --out team.json   # team by visible rules
python -m orgchart export --team team.json --to claude-code|managed-agents|n8n --out <dir>
python -m orgchart solve --problem "<text or @file>" --context @file [--size 6] [--dry-run] --out ./solution
python -m orgchart lesson add "<one sentence>" --role <id|panel> ; python -m orgchart lesson list
python -m pytest -q ; python scripts/stats.py
```

Install first: `python -m pip install -e .` (or set `PYTHONPATH=src`). `solve` without `--dry-run` needs `pip install -e ".[solve]"` and Anthropic credentials.

## Rules you must keep when acting as any role here

1. Nothing leaves the company and no system of record changes without a human saying yes for that specific action. Draft, show, wait.
2. Never invent facts, numbers, quotes or customer names. Say what you do not know.
3. Ask only the questions that change the outcome, with your best guess beside each. No questionnaires.
4. Credentials are environment variable names only, never values, never asked for in chat.
5. Escalation: on Claude Code end your reply with `ESCALATE: <role id>` and a memo; on n8n return `{"escalate_to": ..., "memo": ...}` as the last line; on Managed Agents name the role id in your final message.

## Shape of a role file

```
---
id: sales/sdr                      # department/slug, matches the folder
title: Sales Development Representative
department: sales
reports_to: sales/sales-manager    # null only for c-suite/ceo
level: ic                          # exec | director | manager | ic
model_hint: fast                   # fast | balanced | deep
tools: [crm, email, web_search]    # generic capabilities, see src/orgchart/catalog.py TOOLS
integrations: [attio, hubspot]     # example vendors, lowercase slugs
triggers: [new_inbound_lead]       # snake_case events
escalates_to: sales/sales-manager
tags: [outbound, prospecting]
---
You are the ... (the whole body is the system prompt)
## What you do / ## Skills / ## What you need / ## Working rules / ## Escalate when / ## Hand-offs / ## KPIs / ## Example
```

`catalog.json` is the index (id, title, department, reports_to, level) and must agree with every file; the validator checks both directions.

## Where things are

```
agents/<dept>/<slug>/AGENT.md   roles          agents/STYLE.md     house style, appended to every export
onboarding/                     front-door agents (problem-solver, interviewer)
src/orgchart/                   catalog, validate, finder, compose, solve, export, CLI
integrations/                   vendor recipes          research/   skills-from-postings pipeline
docs/solve.md                   panel protocol          docs/lessons.md   what went wrong and what changed
```

## What not to assume

- The research pipeline has not been run; Skills sections are editorial.
- Claude Code subagents cannot call each other; hierarchy is a marker the main session routes.
- `find` is term overlap with an alias table, not semantic search. Phrase problems in practitioner words.
