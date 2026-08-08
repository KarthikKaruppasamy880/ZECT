# Personal Agent — Current State Audit

**Updated:** 2026-08-08 (desktop Notepad++ / long-notes / Present prefetch / coding readiness)  
**Authoritative status:** Prefer [`CAPABILITY_MATRIX.md`](./CAPABILITY_MATRIX.md), [`CODING_READINESS.md`](./CODING_READINESS.md), and [`IMPLEMENTATION_ROADMAP.md`](./IMPLEMENTATION_ROADMAP.md) over historical PA-0 snapshots.  
**Source brief:** [`docs/screenshots/DesktopControl.md`](../screenshots/DesktopControl.md)

---

## Executive summary

ZECT Mentrix personal-agent spine is **implemented** for typed + spoken Companion, MentrixOrchestrator + permission broker, Email/Slack draft-before-send, local Notes, Calendar read/demo, durable file organize, Electron Computer Mode (allowlisted apps including **Notepad++**), and desktop bridge. Long editor content uses **`desktop_write_note`** (not SendKeys). Remaining gaps are mostly **deferred product depth** (Notion live, LiveKit, full UIA, Calendar OAuth write, Zoom **schedule** API, open-any-app), not missing spine.

---

## Working

| Area | Evidence |
|------|----------|
| Mentrix Delivery runs | `domains/agent_run/mentrix.py`, `forge_loop/orchestrator.py` |
| Companion + orchestrator | `services/mentrix/companion.py`, `orchestrator.py`, `permission_broker.py` |
| Clone TTS + ZECT Voicebox | `domains/voice/voice_clone.py`, `adapters/llm/chatterbox_client.py`, `services/zect-voicebox/` |
| OpenAI Realtime voice | `services/mentrix/realtime.py` (calendar/meeting + connector_architecture + coding_engine_status) |
| Electron Computer Mode | `electron/main.js`, `computer.js` — Notepad++ path resolve; FG wait before type; type max 500; never-delete |
| Long notes to editor | `desktop_write_note` + open notepad/notepad++ (continue/finish reuses last draft) |
| Active desktop target | Companion HUD `computer-active-target` chip (ui_inspect poll) |
| Desktop audit | Electron ring + `POST /api/audit/desktop` |
| Permissions / grants / emergency stop | `domains/permissions/*`; Electron honors stop |
| Slack / email | Providers + `outbound_drafts.py`; compose via `email_send` draft+Allow (not Outlook typing) |
| Calendar read/draft | `/api/calendar/*` + ICS/demo provider; companion + Realtime tools |
| File organize | Durable SHA plans + UI `/file-organize` |
| Skills / schedules | `skills_engine.py`, `scheduler.py`, schedule grants |
| Connector architecture Mermaid | Companion tool `connector_architecture` → Artifacts (subgraphs + deferred list) |
| Coding readiness honesty | [`CODING_READINESS.md`](./CODING_READINESS.md) + tool `coding_engine_status` |

---

## Partial / improved

| Area | Notes |
|------|-------|
| Desktop automation | Allowlisted apps + a11y before/after verify; clicks still best-effort |
| Present Deck clone TTS | Slide N+1 prefetch + ~500 char script cap; sync Voicebox `/generate` still dominates latency |
| Mobile ↔ desktop bridge | Durable JSON spill (`desktop_bridge.py`) |
| BrowserRuntime | Session isolation + DOM verify; ReasoningBrowser stub remains |
| Gmail list | OAuth list when configured; IMAP fallback |
| Electron computer audit | Local ring buffer — not fully unified with `/api/audit` |
| Dual Slack/email paths | Companion + MCP + integration routers (prefer providers + outbound_drafts) |

---

## Deferred / placeholder

| Item | Status |
|------|--------|
| LiveKit Agents | Missing / deferred |
| Notion live API | Placeholder adapter |
| Full Windows UIA tree | Foreground verify only |
| Google Calendar OAuth write | ICS/demo + draft-with-approval shipped |
| Open arbitrary desktop apps | Hard allowlist only (by design) |
| Zoom **schedule** meeting | Open/join only — `capability_refuse` for schedule/book |
| Streaming clone TTS | Out of scope — full-clip `/generate` |

---

## Connector env checklist (spoken/typed honesty)

| Connector | Required env / gate |
|-----------|---------------------|
| Slack digest/send | `SLACK_BOT_TOKEN` (+ optional `SLACK_DEFAULT_CHANNEL`) |
| Email digest | `MENTRIX_IMAP_HOST`, `MENTRIX_IMAP_USER`, `MENTRIX_IMAP_PASSWORD` |
| Email send | SMTP integration + Allow on draft |
| Calendar | `MENTRIX_CALENDAR_ICS_URL` or `MENTRIX_CALENDAR_DEMO=1` |
| Desktop | Electron **Computer Mode** ON; app must be allowlisted (incl. `notepad++.exe`) |
| Realtime voice | `OPENAI_API_KEY`; clone TTS optional via Voicebox `:17493` |
| Notepad++ path | Optional `NOTEPADPP_DESKTOP_PATH` if not under Program Files |

---

## Safety policy (unchanged)

See [`SAFETY_POLICY.md`](./SAFETY_POLICY.md): draft-before-send, never-delete, spoken = typed permissions, API → MCP → browser → a11y → keys last.

---

## Tests

- `backend/tests/fixes_and_phases/test_realtime_import.py` — Realtime module import smoke
- `electron/computer.allowlist.test.js` — Notepad++ allowlist + type cap
- `frontend/e2e/mentrix-*.spec.ts` — Companion / voice / smoke
- Voice / permissions suites under `backend/tests/fixes_and_phases/`
