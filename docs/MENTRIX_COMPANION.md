# Mentrix Companion — Company Personal Agent

Mentrix Companion is the ZECT personal agent for every desktop user: research, content/ads, reporting, internal docs, communications, and Mentrix Delivery — with permission-gated tools.

## Surfaces

| Route | Role |
|-------|------|
| `/mentrix-home` | Companion Home (avatar, chat, Mentrix Board, Computer Mode toggle) |
| `/mentrix` | Mentrix Delivery (ForgeLoop gates → Approve → PR) |

Desktop wake (`Hey Mentrix` / `Ctrl+Shift+Space`) opens **Companion Home**.

## Security

- Every tool goes through the Mentrix permission broker → Permissions Protocol.
- Sensitive tools (send, desktop, image upload, Delivery start/approve/PR) **always ask** via confirm modal.
- Org policy export/import: `GET/POST /api/mentrix/companion/policy`.
- Audits: permission audits + platform audit `mentrix_tool_*`.

## API

- `POST /api/mentrix/companion/turn` — message + optional `confirmed_tools`
- `GET /api/mentrix/companion/tools`
- `GET /api/mentrix/companion/policy`
- `POST /api/mentrix/companion/policy/import`

## Computer Mode

Off by default. When ON (desktop Electron), Mentrix may open **allowlisted** apps, capture the window, or queue click/type — each after user confirm. Idle auto-off (default 10 minutes). Secrets paths (`.env`, keys, credential stores) are default **never**.

## Org share pack

Use **Export org policy** / **Import org policy** on Companion Home (or `GET/POST /api/mentrix/companion/policy`) so every company install shares the same Mentrix tiers, allowlists, and connector scopes.
