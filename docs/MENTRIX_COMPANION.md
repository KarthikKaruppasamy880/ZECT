# Mentrix Companion — Company Personal Agent (HUD)

Mentrix Companion is the ZECT personal operator: weather, Slack, email, research, content/ads, reporting, internal docs, notes, Mentrix Image board, desktop Computer Mode, and Mentrix Delivery — with permission-gated tools and a streaming HUD.

## Surfaces

| Route | Role |
|-------|------|
| `/mentrix-home` | Mentrix HUD (orb, Connect Voice, Display, Computer Mode, Artifacts, Live Log) |
| `/mentrix` | Mentrix Delivery (ForgeLoop gates → Approve → PR) |

Desktop wake (`Hey Mentrix` / `Ctrl+Shift+Space`) opens **Companion HUD** and arms Connect Voice.

## Voice (Connect Voice)

1. **Preflight:** On `/mentrix-home` load, Mentrix probes `POST /api/mentrix/companion/realtime/session` and shows **Realtime ready** (green) or **Voice fallback — {reason}** (amber). Fix `OPENAI_API_KEY` before speaking.
2. **Primary:** OpenAI Realtime speech-to-speech when preflight succeeds. Backend mints an ephemeral client secret; the long-lived API key never goes to the renderer. Tools run via `POST /api/mentrix/companion/realtime/tool` (permission broker + Allow overlay). After Allow, Realtime resumes with tool output.
3. **Fallback:** Web Speech (browser) or Electron dictation → companion SSE stream → `speechSynthesis` TTS. Live Log shows `realtime_fallback`. Windows dictation is less accurate — prefer Realtime.

**Windows tips:** Use a headset as the default mic. Say **Hey Mentrix**, pause, then speak your command. Edit the **Heard** transcript before send if STT mishears (e.g. email vs event).

Realtime tools include personal ops: `weather_report`, `slack_digest`, `slack_send`, `email_digest`, `email_send`, plus ZECT Delivery / Lattice / notes / media / computer.

Optional Mentrix WS control channel: `WS /api/mentrix/companion/realtime?token=…`.

## Personal ops

| Tool | Backend | Notes |
|------|---------|--------|
| `weather_report` | Open-Meteo (no key) | City → temp / conditions / short forecast; Artifacts markdown |
| `slack_digest` | `SLACK_BOT_TOKEN` | Recent messages from `SLACK_DEFAULT_CHANNEL` |
| `slack_send` | Slack API | **Always-ask** Allow overlay |
| `email_digest` | `MENTRIX_IMAP_*` | Read-only subjects; setup message if unset |
| `email_send` | SMTP | **Always-ask**; needs `SMTP_HOST` |

Mentrix research uses DuckDuckGo-style lookup — **not Exa**. Never invent Slack/email contents when tools report unconfigured.

## Streaming API

- `GET /api/mentrix/companion/stream?message=...` — SSE: `thinking`, `tool_start`, `tool_end`, `artifact`, `token`, `navigate`, `pending_confirm`, `done`, `error`
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

## Desktop smoke (personal ops voice)

1. `OPENAI_API_KEY` in `backend/.env`; restart backend + Electron.
2. Connect Voice → Live Log `Connect Voice — OpenAI Realtime` (not only `realtime_fallback`).
3. Ask aloud: weather in a city; Slack digest; any email?
4. Slack send → Allow / Deny overlay.
5. Optional: set `SLACK_BOT_TOKEN` / `MENTRIX_IMAP_*` for live digests.

## Artifacts

Host types: `markdown`, `mermaid`, `table`, `chart`, `note`, `image`, `progress`, `record`.
