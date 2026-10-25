# Google Workspace (Gmail, Calendar, Drive, Sheets)

Capabilities: `email`, `calendar`, `documents`, `spreadsheets`, `files`.

## Reach it from each runtime

- **Claude Code**: Google Workspace MCP servers exist for Gmail, Calendar and Drive; list the one you trust in `.mcp.json`. Drafting is fine; sending needs an approval step, which every agent prompt here already demands.
- **Managed Agents**: OAuth tokens as vault credentials; Gmail and Calendar through an MCP server, Sheets exports through the sandbox's Python plus the Drive API.
- **n8n**: Gmail, Google Calendar, Google Sheets and Google Drive nodes with OAuth2 credentials. Put a human approval node before any Gmail "send".

## Environment variables

- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN`: a dedicated service identity, not a person's account, with the narrowest scopes (`gmail.compose` over `gmail.send`, `calendar.events`, `drive.file`).

## Agents that use it

`executive-support/executive-assistant`, `sales/sdr`, `sales/account-executive`, `people/recruiter`, `people/onboarding-coordinator`, `finance/accounts-receivable`, `marketing/email-marketer`.
