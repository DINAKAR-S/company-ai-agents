# solve: a named panel debates your problem

`python -m orgchart solve` takes your company context and a problem, seats a panel of roles from the catalog, gives each a first name, runs three rounds through the Messages API, and writes four files.

## Who is in the room

- **Lead**: `data-ai/data-ai-solutions-architect` by default (`--lead` to change). Opens the panel.
- **Panelists**: the top matches from `orgchart find` for the problem, up to `--size` (default 6, including the lead). `--panelist <id>` forces a role in.
- **Moderator**: `c-suite/chief-of-staff`. Does not argue; decides and writes.

Names come from a fixed list by hashing the role id, so the same role is always the same person across runs, and two roles on one panel never share a name. The names are labels for readability, nothing more.

## The three rounds

| Round | Who | Gets | Returns (strict JSON schema) |
|---|---|---|---|
| 1 Position | each panelist, in its own role prompt | context + problem + lessons from earlier panels | approach, steps, risks, edge cases, requirements, what breaks in the present setup, mitigations, questions for the company |
| 2 Critique | each panelist | all round 1 positions, by name | best approach and why, disagreements, edge cases everyone missed, changes to own position |
| 3 Decision | moderator, on the deep model | everything | decision, `plan.md`, `edge-cases.md`, `requirements.md`, open questions |

Panelists run on the model their `model_hint` maps to (fast, balanced, deep). The moderator always decides on the deep model.

## Output

```
solution/
  panel.json        who sat, which model, matched terms, rounds completed, errors, warnings
  debate.md         full transcript by round and name
  plan.md           phases, owners by role id, what done looks like
  edge-cases.md     table: case, expected behaviour, how to test
  requirements.md   functional, data, security and privacy, operational; each testable
```

If a panelist's call fails, the session continues without it and the failure is listed in `panel.json` and at the bottom of `debate.md`. If round 1 produces nothing, the session stops and says so. A failed moderator leaves `debate.md` and `panel.json` only.

## Lessons: the panel learns

After a run, what the panel missed until critique and what it had to leave open is appended to `orgchart-lessons.jsonl` (`--memory` to move it, `--no-memory` to skip). The next run injects those lessons into every panelist's prompt under "Lessons from earlier panels": the whole-panel lessons for everyone, plus the ones attributed to that role.

You can add lessons yourself, which is the fastest way to make the panel fit your company:

```
python -m orgchart lesson add "Our helpdesk API allows 100 requests a minute; anything that polls will hit it" --role panel
python -m orgchart lesson add "Finance closes on the 3rd; do not propose month-end changes" --role finance/controller
python -m orgchart lesson list
```

Lessons are plain JSON lines. Edit or delete them with any text editor. A malformed line is skipped and reported, never fatal.

## Without an API key

```
python -m orgchart solve --problem "..." --context @context.md --dry-run
```

writes `solution/panel.md`: who was seated, why, and the full round 1 prompt for each panelist. Paste those into any model you have.

## Cost

A six-person panel is 13 calls: six positions, six critiques, one decision. With a typical one-page context the whole run is a few tens of thousands of tokens. `--size 4` roughly halves it. The exact token counts are in the response usage of each call; the script does not hide them from you, it just does not add them up yet.
