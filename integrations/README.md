# Integration recipes

Agent files name generic capabilities (`crm`, `ticketing`) and example vendors (`attio`, `zendesk`). A recipe says how one vendor is actually reached from each runtime, which environment variables it needs, and which agents in the catalog use it. Values are never written here or anywhere else in this repo.

| Vendor | Capability | Recipe |
|---|---|---|
| Attio | crm | [attio.md](attio.md) |
| HubSpot | crm, email | [hubspot.md](hubspot.md) |
| Slack | chat | [slack.md](slack.md) |
| Gmail / Google Workspace | email, calendar, documents | [google-workspace.md](google-workspace.md) |
| Linear | ticketing | [linear.md](linear.md) |

## Adding a recipe

Copy any file here, keep the three headings (Reach it from each runtime, Environment variables, Agents that use it), and open a pull request. Run `python -m orgchart list` to find the agent ids for the last section.
