# ZECT — Current Architecture (Phase 0 Audit)

Snapshot as of this audit. Reflects what is actually running today, not aspirational design.

## Stack

- **Backend:** FastAPI (Python), SQLAlchemy ORM, SQLite by default (env-configurable), routers under `backend/app/routers/`, business logic under `backend/app/services/`.
- **Frontend:** React + TypeScript (Vite), React Router, deployed both as a web app and inside Electron.
- **Desktop shell:** Electron (`frontend/electron/`) — `main.js` creates the `BrowserWindow` with `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true` (secure defaults, verified). Desktop-only capabilities (window activation, SendKeys-style input, dictation, Slack/Zoom/PowerPoint launch) live in `electron/computer.js`, `win-wake.js`, `shortcuts.js`, `dictation.js`, invoked via `child_process.spawn`/`execFile` with fixed executables — not shell string concatenation.
- **Database:** SQLAlchemy models in `backend/app/models.py` (`ClonedVoice`, `MentrixRun`, `MCPServerConfig`, `SecretEntry`, `LLMResponseCache`, etc.) — no separate migration tool observed in this audit pass (worth confirming Alembic usage or lack thereof in Phase 1).
- **Background work:** No dedicated worker/queue process was found — long operations (build generation, orchestrator runs) execute synchronously inside request handlers or via `_kickoff_background_run`-style in-process async tasks, not a separate worker fleet. This is a real gap against the target architecture's "background workers" principle.

## Backend organization (current, not domain/adapter split)

```
backend/app/
  routers/           # FastAPI endpoints — one file per feature area
  services/
    mentrix/         # Companion (voice + chat), notes, permission broker, realtime
    forge_loop/      # Orchestrator — Mentrix Delivery state machine (MentrixRun)
    phases/          # Ask/Plan/Build/Review service logic (build_phase_svc.py etc.)
    llm/             # Model-selection, Chatterbox/OpenAI TTS clients, provider clients
    mcp/             # MCP hub + adapters (github, jira, confluence, slack, datadog, email)
    lattice/         # Knowledge-graph indexer/query
    quality/         # Lint runner, rules engine, gates policy, incomplete-file gate
    rag/, build_intel/, security/
  core/auth/         # RBAC, CurrentUser, permission decorators
  security/vault.py  # Fernet-based secret encryption for app-managed secrets
```

This is organized **by feature**, not by the `api/domains/adapters/infrastructure/workers` split proposed in the target architecture — see TARGET_ARCHITECTURE.md.

## Key subsystems already live

- **Mentrix Companion** — chat + realtime voice assistant. Voice uses OpenAI's Realtime API directly over WebSocket (client_secrets flow), not a third-party voice framework. Cloned-voice TTS goes through a local "Chatterbox" synthesis engine (`CHATTERBOX_BASE_URL`) with an OpenAI TTS fallback.
- **Mentrix Delivery / ForgeLoop orchestrator** — a `MentrixRun` state machine (`running → awaiting_approval/needs_human → approved → pr_created`, or `failed/cancelled`) with persisted `events_json`/`gates_json`, human-gated PR creation (`git_ops.create_pull_request`), and MCP-backed Slack/email/Jira/Confluence/Datadog actions.
- **Ask / Plan / Build / Review** — four **separate** pages, each calling backend generation endpoints directly (Anthropic/OpenAI via `resolve_generation_model`). Not unified into one workspace screen.
- **Lattice** — a knowledge-graph index over indexed repos/docs, queried by Companion and rendered as an interactive graph (cytoscape.js).
- **Integrations** — real MCP adapters for GitHub, Jira, Slack, Confluence, Datadog, Email; admin-configured server credentials, not per-user OAuth.
- **RBAC + audit** — role-based decorators, `log_audit` calls across state-changing endpoints, a permission broker with confirm/pending-approval semantics for Companion tool calls.
- **Secrets** — Fernet-encrypted secret storage (`security/vault.py` + `SecretsManager` router) for app-managed secrets; the app's *own* admin login credential is a plaintext `.env` value (standard for a `.env` file, but distinct from the vault-protected path).

## Verified test status (full suite, no deselects)

- Backend: `443 passed, 7 failed, 26 errors` (Python 3.12, system install — the project's own `.venv` is broken, missing pip-installed packages). All 33 failures/errors trace to **two environment issues, not product defects**:
  1. `pytest-asyncio` not installed (an optional test extra) — breaks 6-7 async RBAC tests.
  2. `auth.py`'s `_auth_creds()` reloads `.env` with `override=True` on every call, stomping the test suite's injected test credentials with real `.env` credentials mid-run — cascades into 26 fixture-setup errors in `test_enterprise_routers.py`/`test_mentrix_platform.py`.
- Frontend: `36 passed (36)`, clean.

See THREAT_MODEL.md for the `auth.py` reload behavior's production implications.

## Notable dead/legacy code found

- `backend/app/services/llm/voicebox_client.py` — explicit "legacy alias" shim, only imported by one test file.
- `backend/app/services/llm/elevenlabs_client.py` — superseded by Chatterbox per project history; not imported by any live router/service, only a test file.
- `frontend/src/pages/StagePage.tsx` (`/stages/:stage`) — registered route, no nav link, no in-app navigation to it anywhere. Orphaned.

## Already consolidated (no action needed)

Code review used to have three duplicate LLM-calling implementations (`review_phase.py`, `ultrareview.py`, `review_phase_svc.py`) — all three now explicitly delegate to one canonical `backend/app/review_service.py`, confirmed via in-code comments referencing the consolidation. No further work needed here.
