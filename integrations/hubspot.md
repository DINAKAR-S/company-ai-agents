# HubSpot

Capability: `crm`, `email`. Objects: contacts, companies, deals, tickets, sequences, marketing emails.

## Reach it from each runtime

- **Claude Code**: HubSpot's official MCP server, listed in `.mcp.json`; expose only the tools the role needs (an SDR does not need `delete_contact`).
- **Managed Agents**: vault credential plus the MCP server in `mcp_servers`, or custom tools answered from your side.
- **n8n**: HubSpot node with the private app credential. Sequences and marketing sends stay behind a human approval node; the agent prompts already refuse to send on their own.

## Environment variables

- `HUBSPOT_ACCESS_TOKEN`: private app token with the smallest scope set that covers the agent's "What you do" list.

## Agents that use it

`sales/sdr`, `sales/account-executive`, `sales/revops`, `marketing/email-marketer`, `marketing/marketing-ops`, `customer/support-tier1`, `customer/customer-success-manager`.
