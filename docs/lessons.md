# Lessons

Defects and surprises the green suite did not catch on its own, with what changed. New entries go on top.

## A catalog and its files drift the moment two people edit them

What looked fine: agent files and `catalog.json` were both hand-written and both looked complete.
What was true: nothing stopped a file saying `reports_to: sales/manager` while the catalog said `sales/sales-manager`, or a role referencing `marketing/brand-manager`, which never existed.
How it was caught: writing the validator before the second batch of files, and running it on the first.
What changed: `validate.py` compares every front matter field with the catalog entry, resolves every `dept/slug` reference in prose, and checks for exactly one root and no cycles. CI runs it on every push.

## "No week language" is ambiguous

What looked fine: a rule against build-schedule language ("week 1", "phase 2").
What was true: writers read it as banning the word "week" and rewrote "a good week" to "a good month", while a 13-week cash forecast is simply the name of the artefact.
How it was caught: writer reports flagged the conflict.
What changed: the validator's regex targets `week N`, `phase N` and `repo N of M` only. Prose cadence words are fine.

## A strict front matter parser is a feature, not a limitation

What looked fine: using a YAML library would accept anything.
What was true: anything includes nested maps, anchors and multi-line strings that the three exporters would then have to handle, and that a contributor would use by accident.
What changed: `frontmatter.py` accepts scalars, null and single-line flow lists, and rejects everything else with a line number. The repo has no dependencies.

## Escalation cannot be faked in a runtime that has no agent-to-agent calls

What looked fine: every agent says who it escalates to.
What was true: Claude Code subagents cannot invoke each other, so a prompt saying "hand this to `sales/sales-manager`" would have done nothing.
What changed: the Claude Code exporter appends a Team section that tells the agent to end with `ESCALATE: <role id>` and a memo, which the main session routes. The Managed Agents and n8n exporters say what escalation means in their runtime instead of pretending it is uniform.

## A company description can outvote the question

What looked fine: term overlap with context terms at half weight.
What was true: a 20-line company description about payroll put the Payroll Specialist on a panel about trade-show leads, because many half-weight hits beat a few full-weight ones.
How it was caught: a test that fed a repetitive context and checked the top result.
What changed: roles with zero problem-term matches now rank after every role with at least one, whatever their score. Context breaks ties and adds depth; it never picks the lead.

## argparse and a trailing positional

What looked fine: `lesson add --role sales/sdr check the opt-out list`.
What was true: argparse assigns a `nargs="*"` positional the moment it sees the first option, so the words after `--role` were "unrecognized arguments". `parse_intermixed_args` does not work with subparsers either.
What changed: the lesson text is one quoted positional. The CLI test passes it that way and the help says so.

## A test that guesses a generated name

What looked fine: `fail_for={"Steven"}`.
What was true: names are hashed from role ids, and the four-role panel for that problem had no Steven, so the "one panelist fails" test was testing nothing.
What changed: the test builds the panel first and fails the actual first panelist.

## Renaming the folder silently broke the venv

What looked fine: tests passed, then the repo folder was renamed for the GitHub rename.
What was true: the editable install in `.venv` still pointed at the old path, so `python -m orgchart` raised `ModuleNotFoundError` while the source sat right there.
How it was caught: a subagent's validator run.
What changed: `pip install -e .` again after any move. CI never sees this because it installs fresh; a local checkout does.
