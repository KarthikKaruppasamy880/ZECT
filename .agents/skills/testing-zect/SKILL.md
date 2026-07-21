# ZECT / Mentrix Testing Skill

## Stack

- Frontend: Vite + React on `http://localhost:5173`
- Backend: FastAPI on `http://localhost:8000`
- Auth: local login → `localStorage.zect_token` → `Authorization: Bearer`
- Agent runtime: **ForgeLoop** (not LangGraph)
- Default local creds (if unset): `admin@zect.local` / `zect-dev-local`

## Start stack

```bash
# backend
cd backend
# activate venv; optional ZECT_USERNAME / ZECT_PASSWORD / DATABASE_URL
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm run dev
```

## Playwright E2E (source of truth)

```bash
cd frontend
npx playwright install chromium   # once
# API must be running on :8000
# Login: admin@zect.local / zect-dev-local (or ZECT_* from backend .env)
npm run test:e2e
```

Specs:

- `e2e/auth.setup.ts` — login storageState
- `e2e/mentrix-smoke.spec.ts` — Lattice, Mentrix chat/upgrade, Sandbox, Integrations
- `e2e/mentrix-approve-pr.spec.ts` — approve → create PR (dry_run)

Cursor Playwright MCP is for interactive debugging only; do not treat it as CI.

## Key Mentrix routes

| Route | Test id |
|-------|---------|
| Login (gate) | `login-username`, `login-password`, `login-submit` |
| `/lattice` | `lattice-page` |
| `/mentrix` | `mentrix-page`, `mentrix-chat`, `mentrix-engage`, `mentrix-live-status`, `mentrix-gates`, `mentrix-approve`, `mentrix-create-pr` |
| `/sandbox` | `sandbox-page`, `sandbox-check` |
| `/integrations` | `integrations-page`, `mcp-enable-panel` |

## Upgrade mode gates

1. incomplete_ok, lint_ok, sandbox_ready, review_ok (Mentrix Ultra Review), api_eval_ok  
2. Human `Approve` required (ack can override sandbox / Ultra Review / API eval — not incomplete)  
3. `Create PR` dry_run by default in UI  

## Backend pytest

```bash
cd backend
pytest -q
```

Prefer a fresh venv if `import sqlalchemy` / uvicorn hangs on the host machine; CI is authoritative.
