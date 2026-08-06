# Mentrix MCP — Gmail & Notion

## Notion (stub)

- MCP `server_id`: `notion`
- Without `NOTION_API_TOKEN` / `NOTION_TOKEN`: every call returns `status: not_configured` (no fake success).
- Even with a token env present, the adapter remains a stub until a Later phase enables live Notion API.

## Gmail (thin path)

- MCP `server_id`: `gmail`
- Requires `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, and `GMAIL_REFRESH_TOKEN`.
- If not set: returns `not_configured` and points operators to the **email** MCP adapter (`SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD`).
- When Gmail env is set, send currently delegates through the SMTP email adapter (thin bridge) — full Gmail API is Later.

## Browser allowlist

Companion browser intents use BrowserRuntime with `MENTRIX_BROWSER_ALLOWLIST` (comma-separated hosts, or `*` for all https).
