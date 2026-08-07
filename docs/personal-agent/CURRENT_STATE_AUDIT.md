# Personal Agent — Current State Audit (PA-0)

**Date:** 2026-08-07  
**Branch:** `feature/personal-agent-pa-0-audit`  
**Source brief:** [`docs/screenshots/DesktopControl.md`](../screenshots/DesktopControl.md)  
**Scope:** Read-only audit of Mentrix personal-agent surfaces. **No product behavior changes.**

---

## Executive summary

ZECT already has a substantial Mentrix personal-agent spine: Delivery (ForgeLoop), Companion (tools + realtime), Electron Computer Mode, browser/MCP integrations, permissions/audit/secrets, skills, and schedules. Gaps against the DesktopControl product goal are mainly **unification** (typed/spoken/desktop do not share one command+policy schema), **calendar (missing)**, **verification after desktop/browser actions**, **browser allowlist default `*`**, and **file-organization depth** (in-memory plans, no SHA/Undo productization).

---

## Working

| Area | Evidence |
|------|----------|
| Mentrix Delivery runs | `backend/app/domains/agent_run/mentrix.py`, `services/forge_loop/orchestrator.py`, `workers/mentrix_worker.py` |
| Companion turns / stream / tools | `services/mentrix/companion.py`, `permission_broker.py`; UI `MentrixCompanion.tsx` |
| Clone TTS + ZECT Voicebox | `domains/voice/voice_clone.py`, `adapters/llm/chatterbox_client.py`, `services/zect-voicebox/` |
| OpenAI Realtime voice | `services/mentrix/realtime.py`, `frontend/src/lib/mentrixRealtime.ts` |
| Electron Computer Mode | `electron/main.js`, `computer.js`, `preload.js`; bridge `desktopBridge.ts` |
| Hard no-delete (desktop) | Companion `delete_never_allowed`; Electron `DELETE_ACTIONS` refuse |
| Permissions / grants / emergency stop | `domains/permissions/*` |
| Secrets manager | `domains/permissions/secrets_manager.py` |
| Audit trail API | `domains/audit/audit_trail.py` |
| Slack / email / Jira integrations | `domains/integration/*`, adapters; companion draft-before-send via `outbound_drafts.py` |
| Skills Engine + schedules | `domains/personal_agent/skills_engine.py`, `scheduler.py`, `schedule_executor.py` |
| MCP hub | `services/mcp/hub.py`, `domains/integration/mcp.py` |

---

## Partial

| Area | Gap |
|------|-----|
| Companion planner | Regex + LLM planner — not a single MentrixOrchestrator command schema |
| Desktop automation | Click/type often coordinates / SendKeys-style; weak verification |
| Mobile ↔ desktop bridge | In-memory queues (`desktop_bridge.py`) |
| BrowserRuntime | Playwright works when installed; ReasoningBrowserStub is placeholder |
| File organize | `file_organize.py` plan/approve/rollback exists but plans are in-memory; not full SHA/Undo product |
| IMAP / Gmail | Env-gated digest; Gmail MCP often thin/SMTP |
| Electron computer audit | Ring buffer in main process — not unified with `/api/audit` |
| Skills / schedules ops | UI+API present; FEATURE_INVENTORY notes uneven verification |
| Notion MCP | Placeholder adapter |

---

## Placeholders / dead / missing

| Item | Status |
|------|--------|
| Calendar provider / OAuth | **Missing** (ROADMAP: deferred; DesktopControl requires it later) |
| LiveKit Agents | Not used for Mentrix clone TTS |
| Shared `MentrixOrchestrator` + `ApprovalService` personal-agent APIs | **Missing** as named PA-1 interfaces (pieces exist as broker/permissions) |
| DesktopControl PA-1+ product flows | Not started |

---

## Unsafe / risk findings (priority)

1. **Browser allowlist default `*`** — `services/browser/allowlist.py` / `MENTRIX_BROWSER_ALLOWLIST=*` can allow unrestricted hosts.
2. **Brittle desktop clicks** — companion can emit fixed coordinates (`computer_click` at hardcoded points) without accessibility verification.
3. **Success without verification** — desktop/browser tools often report success after sending OS/DOM action without read-back.
4. **Secrets in renderer** — Electron preload exposes bridges; confirm no secret values cross into renderer (policy: secrets stay in main/backend vault). Audit did not find deliberate secret export; keep as ongoing risk.
5. **Frontend-only checks** — UI may hide actions, but server-side `permission_broker` + Electron refuse paths are the real gates; continue enforcing server/trusted-process only.
6. **Duplicate provider call paths** — Companion tools vs MCP adapters vs integration routers can reach Slack/email/Jira through multiple stacks (needs PA-1 normalization).

---

## Duplicate / direct provider call notes

- Slack: integration router + MCP slack adapter + companion `_exec_tool`.
- Email: SMTP integration + IMAP digest service + Gmail MCP thin path.
- Jira: integration domain + MCP jira adapter + companion tools.
- Browser: BrowserRuntime PlaywrightProvider vs MCP playwright adapter.

Recommended PA-1 action: single capability → one trusted executor behind Permission/Approval services.

---

## Tests observed (PA-0 — do not fix unrelated failures)

Run selectively during this phase (docs-only). Known suites:

- `backend/tests/fixes_and_phases/` — voice, permissions-related coverage
- `services/zect-voicebox/tests/` — Voicebox native API
- `frontend/e2e/mentrix-*.spec.ts` — Companion/voice e2e
- Electron: `electron/chatterbox.test.js`

Full CI green is **not** a PA-0 gate. Record failures when running local checks in the PR description; do not change product code to fix them in this phase.

---

## Recommended sequencing after approval

1. **PA-1** — Shared command + policy foundation (see `IMPLEMENTATION_ROADMAP.md`).
2. Harden browser allowlist default (can land with PA-1 safety or early PA-4 prep).
3. Do **not** expand desktop automation until PA-1 + PA-5.

---

## Rollback

Docs-only PR: revert commit / close PR. No migrations, no runtime flags.
