# Slack

Capability: `chat`. Read channels for context, post drafts for approval, receive approvals.

## Reach it from each runtime

- **Claude Code**: a Slack MCP server in `.mcp.json`. Give agents read on the channels they need and post only to a staging channel where a human reacts to approve.
- **Managed Agents**: vault credential plus the MCP server, or a webhook from the session's events to a Slack app you run.
- **n8n**: Slack node. The simplest approval gate is a Slack "Send and Wait for Approval" step between the agent's draft and the node that acts on it.

## Environment variables

- `SLACK_BOT_TOKEN`: bot token scoped to `channels:read`, `channels:history`, `chat:write`. Add `users:read` only for roles that need names.

## Agents that use it

Almost every role can report through Slack. Roles that must read it: `executive-support/internal-comms`, `customer/support-escalation`, `engineering/devops-sre`, `operations/program-manager`, `c-suite/chief-of-staff`.
