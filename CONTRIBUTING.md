# Contributing

The most useful contributions, in order: a role your company has that the catalog lacks; a better "What you do" list for a role you have actually done; an integration recipe for a vendor you use; a research run that puts counts on a Skills section.

## Add or change a role

1. Copy `agents/TEMPLATE.md` to `agents/<department>/<slug>/AGENT.md`. The slug is lowercase with hyphens.
2. Add the role to `catalog.json` (`id`, `title`, `department`, `reports_to`, `level`). The validator checks the two agree.
3. Write the body as the system prompt. Keep every section. "What you do" needs eight to twelve verb-first tasks that each produce an artefact. "Working rules" must keep the approval gate and the no-invented-facts rule.
4. Reference other roles by id only (`finance/controller`). The validator rejects ids that do not exist.
5. Run:

```
python -m orgchart validate
python -m pytest -q
```

Both must pass. CI runs them on Linux and Windows.

## Style

- Plain English, second person, no marketing language.
- No em-dashes. Use commas, colons or full stops.
- No customer names, personal names, or build schedules.
- Credentials appear only as environment variable names.
- KPIs are examples; say so once in the section.

## New department

Add it to `departments` in `catalog.json` with a one-line description, then add at least one role. A department's head reports to a C-suite role.

## Pull request checklist

- [ ] `python -m orgchart validate` prints `no problems`
- [ ] `python -m pytest -q` is green
- [ ] `python scripts/stats.py` numbers in the README are updated if they changed
- [ ] Any limitation you know of is added to the README's "What is not built yet" table rather than left for a reader to discover
