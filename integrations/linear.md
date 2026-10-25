# Linear

Capability: `ticketing`. Issues, projects, cycles, comments.

## Reach it from each runtime

- **Claude Code**: Linear's official MCP server in `.mcp.json`. Engineering agents read issues freely; creating or closing issues is an approved action.
- **Managed Agents**: vault credential plus the MCP server in `mcp_servers`.
- **n8n**: Linear node, or the GraphQL API through an HTTP Request node.

## Environment variables

- `LINEAR_API_KEY`: personal or OAuth key for a bot user, read scope by default.

## Agents that use it

`engineering/engineering-manager`, `engineering/backend-engineer`, `engineering/frontend-engineer`, `engineering/qa-engineer`, `engineering/release-manager`, `product-design/product-manager`, `product-design/technical-product-manager`, `customer/support-tier2`, `operations/scrum-master`.
