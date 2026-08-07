# Personal Agent — Capability Matrix (PA-0)

Status: `working` | `partial` | `placeholder` | `missing` | `unsafe`

| capability | existing implementation | files | backend endpoint | trusted execution process | provider | permission | approval requirement | verification method | tests | status | recommended action |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Mentrix Delivery run | ForgeLoop orchestrator + worker | `domains/agent_run/mentrix.py`, `services/forge_loop/orchestrator.py`, `workers/mentrix_worker.py` | `/api/mentrix/runs*` | backend worker | LLM + coding tools | auth + project scope | human approve before PR | gates / review artifacts | backend mentrix tests, e2e | working | Keep; do not replace with personal-agent orchestrator |
| Companion typed turn | companion.py tool loop | `services/mentrix/companion.py`, `MentrixCompanion.tsx` | `/api/mentrix/companion/*` | backend | multi-tool | `permission_broker` | ALWAYS_CONFIRM tools | tool result text | e2e smoke | partial | Unify under MentrixOrchestrator (PA-1) |
| Companion spoken / Realtime | OpenAI Realtime + tool confirm | `realtime.py`, `mentrixRealtime.ts` | WS + client secrets | backend + browser audio | OpenAI Realtime | same broker for tools | confirmRealtimeTools | session events | e2e voice | working | Connect to shared command schema (PA-7) |
| Clone TTS / Test speak | voice_clone + ZECT Voicebox | `voice_clone.py`, `chatterbox_client.py`, `services/zect-voicebox/` | `/api/mentrix/voice/*`, `:17493` | Voicebox container / uvicorn | Chatterbox ML / stub | auth | n/a (local synth) | audio bytes | voice_cloning + voicebox tests | working | Keep; PA-7 latency work later |
| Electron Computer Mode | main + computer.js | `electron/main.js`, `computer.js`, `preload.js` | IPC `mentrix-computer` | Electron main | OS | app allowlist | user consent / broker | weak (action ack) | manual / limited | partial | PA-5 a11y + verify |
| Desktop delete | hard refuse | companion + Electron | IPC | Electron main | n/a | policy | n/a | refuse | unit paths | working | Keep server-side forever |
| Mobile desktop bridge | in-memory queue | `desktop_bridge.py`, `MobileCompanion.tsx` | `/api/mentrix/desktop-bridge/*` | backend + Electron poll | ZECT | auth | same as desktop tools | ack | partial e2e | partial | Persist queue; PA-5 |
| Browser navigate/click/fill | BrowserRuntime Playwright | `services/browser/runtime.py`, `adapters/playwright_adapter.py` | companion tools / MCP | backend Playwright | Chromium | allowlist | ALWAYS_CONFIRM browser_* | DOM snapshot optional | browser docs | unsafe default | Tighten allowlist; PA-4 verify |
| MCP hub | hub + adapters | `services/mcp/hub.py`, `domains/integration/mcp.py` | `/api/mcp/*` | backend | multi | MCP enable | per-tool | adapter response | mcp tests | working | Route through PA-1 capabilities |
| Slack notify / digest | integration + companion | `slack_integration.py`, `adapters/slack.py` | `/api/integrations/slack*`, companion | backend | Slack API | secrets | draft confirm for send | API response id | integration tests | working | PA-2/3 draft+approve |
| Email SMTP send | email integration | `email_integration.py`, `email_adapter.py` | `/api/integrations/email*` | backend | SMTP | secrets | draft confirm | provider response | partial | working | PA-2/3 |
| Email IMAP digest | email_inbox | `email_inbox.py` | companion tools | backend | IMAP | env | n/a read | message list | thin | partial | PA-2 allowlists |
| Gmail MCP | gmail_adapter | `adapters/gmail_adapter.py` | MCP | backend | Gmail/SMTP | secrets | draft | thin | docs | partial | PA-2 real OAuth |
| Jira issues / search | jira domain + MCP | `jira_integration.py`, `adapters/jira.py` | `/api/jira*`, companion | backend | Jira | secrets | comment tools confirm | issue key | tests | working | Keep; cite in drafts PA-2 |
| Calendar read/write | — | — | — | — | — | — | — | — | — | missing | PA-2/3 CalendarProvider |
| File organize plan | file_organize domain | `domains/personal_agent/file_organize.py` | `/api/personal-agent/file-organize*` | backend | FS | allowlist | approve_plan | path list | thin | partial | PA-6 SHA/Undo |
| FS allowlist | allowed_paths | `infrastructure/allowed_paths.py` | used by tools | backend | FS | roots env | n/a | path check | unit | working | Extend for PA-6 exclusions |
| Permissions rules/grants | permissions domain | `domains/permissions/*` | `/api/permissions*` | backend | ZECT | RBAC | approve grant | DB | tests | working | Become PermissionService (PA-1) |
| Secrets vault | secrets_manager | `secrets_manager.py` | `/api/secrets*` | backend | vault | admin | n/a | encrypted at rest | tests | working | Never expose to renderer |
| Audit trail | audit_trail | `audit_trail.py` | `/api/audit*` | backend | ZECT | auth | n/a | append-only log | tests | working | AuditService + desktop events (PA-1) |
| Emergency stop | permissions + schedule_executor | permissions UI | `/api/permissions/emergency-stop` | backend | ZECT | admin | n/a | flag check | tests | working | Wire to desktop kill (PA-1/5) |
| Skills Engine | skills_engine | `skills_engine.py`, `SkillsEngine.tsx` | `/api/skills-engine*` | backend | ZECT | auth | per skill | execution rows | partial | working | PA-9 governance fields |
| Scheduled tasks | scheduler + executor | `scheduler.py`, `schedule_executor.py` | `/api/schedules*` | backend worker | ZECT | grants | limited | idempotency key | partial | working | Separate grants PA-9 |
| Notion MCP | notion adapter | `adapters/notion*.py` | MCP | backend | Notion | secrets | — | — | — | placeholder | Defer or implement later |
| LiveKit voice agents | — | — | — | — | — | — | — | — | — | missing | Out of scope for personal-agent voice |

## Legend notes

- **Approval requirement** “ALWAYS_CONFIRM” = `permission_broker.ALWAYS_CONFIRM_TOOLS`.
- **Trusted execution process** = process that must enforce policy (not the LLM, not the React UI alone).
