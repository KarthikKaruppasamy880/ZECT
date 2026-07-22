# Mentrix Companion — Company Personal Agent (HUD)

Mentrix Companion is the ZECT personal operator: weather, Slack, email, research, content/ads, reporting, internal docs, notes, Mentrix Image board, desktop Computer Mode, and Mentrix Delivery — with permission-gated tools and a streaming HUD.

## Harness vs Loop

| Concept | Meaning in ZECT |
|---------|-----------------|
| **Harness** | Single-run safety: permission broker, Allow overlay, org policy, Realtime mint (`client_secrets`), tool schemas, Delivery gates on `/mentrix`. |
| **Loop** | Stay-alive personal agent: Layout-level session + floating dock, wake continuity across routes, Skills/Dream context injection, sessionStorage chat tail. |

ForgeLoop Delivery remains the upgrade **harness**. Mentrix HUD + dock is the always-on **loop**.

## Surfaces

| Route | Role |
|-------|------|
| `/mentrix-home` | Full Mentrix HUD (orb, Connect Voice, Mic picker, Display, Computer Mode, Artifacts, Live Log) |
| *(all authenticated routes)* | Persistent Mentrix dock (orb + Connect Voice + mini chat) — survives navigation; hidden when HUD is open |
| `/mentrix` | Mentrix Delivery (ForgeLoop gates → Approve → PR) |
| `/skills` | Labs — Skill Library (Mentrix **reads** selected skill into turn context) |
| `/dream-engine` | Labs — Dream Engine (Mentrix **consumes** staged lessons; does not run the dream cycle) |

Desktop wake (`Hey Mentrix` / `Ctrl+Shift+Space`) expands the **persistent dock** and starts Connect Voice (Realtime) without hard-reloading the SPA.

### Navigate intents

| Phrase | Behavior |
|--------|----------|
| Dashboard / app home | SPA navigate to `/` — dock + voice stay up |
| Mentrix / control tower / desktop app | `/mentrix-home` |
| Go to desktop / OS desktop / computer mode | Computer tools (`computer_open_app` / screenshot) — **not** Dashboard `/` |
| Lattice / Sandbox / Delivery / … | Existing `NAV_MAP` routes; dock survives |

## Voice (Connect Voice)

1. **Preflight:** On `/mentrix-home` load, Mentrix probes `POST /api/mentrix/companion/realtime/session` and shows **Realtime ready** (green) or **Realtime unavailable — {reason}** (amber) with **Retry Realtime**.
2. **Mint API (GA):** Backend calls OpenAI `POST /v1/realtime/client_secrets` (not the retired `/v1/realtime/sessions`). Default model: `gpt-realtime` (`MENTRIX_REALTIME_MODEL`).
3. **Primary UX:** Pick your **headset mic**, click **Connect Voice**, speak naturally. Mentrix replies with Realtime audio. **No “Send corrected” / tone / Windows dictation path.**
4. **If Realtime fails:** Use typed Quick asks or **Retry Realtime**. Fix `OPENAI_API_KEY` and restart backend — OpenAI chat key ≠ automatic Realtime if mint is broken.

**Mic picker:** Lists `audioinput` devices; choice persists in `localStorage` (`mentrix_mic_device_id`). Prefer a headset over the laptop array mic.

**Stability:** Connect Voice waits until the mic is open before unlocking the button (prevents double-start races). Capture uses AudioWorklet (ScriptProcessor fallback). Each connect remints a fresh ephemeral key. Electron reloads the page if the renderer crashes (blank window). DevTools opens only when `ZECT_DEVTOOLS=1`.

Realtime tools include personal ops: `weather_report`, `slack_digest`, `slack_send`, `email_digest`, `email_send`, plus ZECT Delivery / Lattice / notes / media / computer.

## Integrations (OpenAI ≠ Slack ≠ Jira)

| Env | Purpose |
|-----|---------|
| `OPENAI_API_KEY` | Mentrix LLM + Realtime voice |
| `MENTRIX_REALTIME=1` | Enable Realtime mint |
| `MENTRIX_REALTIME_MODEL=gpt-realtime` | Realtime model |
| `SLACK_BOT_TOKEN` | Slack digest / send |
| `SLACK_DEFAULT_CHANNEL` | Default channel (e.g. `#engineering`) |
| `MCP_JIRA_URL` or `JIRA_BASE_URL` | Jira base URL |
| `JIRA_EMAIL` + `JIRA_API_TOKEN` | Jira auth |

There is **no minibot runner** inside ZECT. If another app (minibot / App Runner) already has Slack/Jira tokens, **copy them into `backend/.env`** (never commit). Mentrix HUD shows non-secret chips via `GET /api/mentrix/companion/integrations` (OpenAI / Slack / Jira ready or not).

## Personal ops

| Tool | Backend | Notes |
|------|---------|--------|
| `weather_report` | Open-Meteo (no key) | City → temp / conditions / short forecast; Artifacts markdown |
| `slack_digest` | `SLACK_BOT_TOKEN` | Recent messages from `SLACK_DEFAULT_CHANNEL` |
| `slack_send` | Slack API | **Always-ask** Allow overlay |
| `email_digest` | `MENTRIX_IMAP_*` | Read-only subjects; setup message if unset |
| `email_send` | SMTP | **Always-ask**; needs `SMTP_HOST` |

Mentrix research uses DuckDuckGo-style lookup — **not Exa**. Never invent Slack/email contents when tools report unconfigured.

## Skills + Dream context (Labs → Mentrix)

- Active skill id: `localStorage.mentrix_active_skill_id` (HUD/dock picker; optional None).
- On each typed turn and Connect Voice start: `GET /api/mentrix/companion/agent-context?skill_id=&project_id=` packs **Active skill** text + up to 3 staged Dream lesson claims (`Learned patterns (Dream)`).
- Empty/unconfigured → silent no-op (no error toast).
- Dream cycle itself still runs only from Labs `/dream-engine`; Mentrix does not invent lessons.

## Streaming API

- `GET /api/mentrix/companion/stream?message=...` — SSE: `thinking`, `tool_start`, `tool_end`, `artifact`, `token`, `navigate`, `pending_confirm`, `done`, `error` (optional `agent_context`, `skill_id`)
- `GET /api/mentrix/companion/agent-context` — Skills + staged Dream text for injection
- `POST /api/mentrix/companion/stream/resume` — continue after Allow
- `POST /api/mentrix/companion/turn` — non-stream fallback (Playwright)

## ZECT workflows

Voice/text can navigate core routes (Delivery, Lattice, Sandbox, Ask, Plan, Docs, Integrations, Build, …) and run tools: `delivery_status`, `start_delivery`, `lattice_query`, `research_news`, notes, diagnose (Mermaid), media board, desktop actions.

## Mentrix Image board

Numbered generations/edits under `backend/data/mentrix_media/` (gitignored). Tools: `media_generate`, `media_edit`, `media_list` (confirm-gated). Artifacts show images via `/api/mentrix/companion/media/{n}`.

## Computer Mode

Off by default. **Windows and macOS:** allowlisted open app, desktop screenshot, path read (secrets denied), click / type / scroll / UI inspect after Allow. Idle auto-off. Always-ask for high-risk actions.

## Security

- Every tool → Mentrix permission broker.
- Sensitive tools **always ask** via Allow? overlay (Enter / Esc) — including Slack/email send.
- Org policy export/import on HUD.
- Audits: permission audits + `mentrix_tool_*`.
- Never commit API keys; use `backend/.env` only.

## Desktop smoke (Realtime voice)

1. `OPENAI_API_KEY` + `MENTRIX_REALTIME_MODEL=gpt-realtime` in `backend/.env`; kill stale port 8000; restart backend + Electron.
2. HUD shows **Realtime ready** (not unavailable / openai_404).
3. Select headset in **Mic**, click **Connect Voice** → Live Log `Connect Voice — OpenAI Realtime`.
4. Say “Hi” / weather question — spoken reply, no Send corrected.
5. Optional: set `SLACK_BOT_TOKEN` / Jira env for digests; chips show Slack/Jira ready.

## Post-merge restart

After merging Mentrix PRs into `develop`, restart backend, frontend, and Electron (or double-click the ZECT Mentrix desktop shortcut) so the persistent dock session + Realtime mint path load.

## Artifacts

Host types: `markdown`, `mermaid`, `table`, `chart`, `note`, `image`, `progress`, `record`.
