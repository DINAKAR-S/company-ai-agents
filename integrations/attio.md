# Attio

Capability: `crm`. Objects: people, companies, deals, notes, tasks, lists.

## Reach it from each runtime

- **Claude Code**: add Attio's MCP server to `.mcp.json` (or any community Attio MCP server), then list its tools in the subagent's `tools:` line. Without an MCP server, the agent can call the REST API through `Bash` with `curl` and the environment variable below; keep writes behind approval as the agent prompts already require.
- **Managed Agents**: store the key as a vault `environment_variable` credential and give the agent an Attio MCP server in `mcp_servers`, or a custom tool whose results you supply from your side. The agent never sees the key either way.
- **n8n**: Attio node (or HTTP Request node with a predefined Attio credential). Pass the agent's JSON output into the node's field mapping. Branch on the last line `{"escalate_to": ...}` when present.

## Environment variables

- `ATTIO_API_KEY`: workspace API key with read scope, plus write scope only for agents allowed to create records after approval.

## Agents that use it

`sales/sdr`, `sales/bdr`, `sales/account-executive`, `sales/account-manager`, `sales/revops`, `customer/customer-success-manager`, `customer/renewals-specialist`, `marketing/marketing-ops`. Check `python -m orgchart list` for the current set; the agent files are the source of truth.
