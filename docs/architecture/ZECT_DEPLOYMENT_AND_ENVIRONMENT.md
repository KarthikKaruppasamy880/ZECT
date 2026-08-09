# ZECT Deployment and Environment

**Canonical parent:** [`ZECT_SYSTEM_ARCHITECTURE.md`](../../ZECT_SYSTEM_ARCHITECTURE.md)  
**Evidence:** [`ZECT_PRODUCT_ACCEPTANCE.md`](../../ZECT_PRODUCT_ACCEPTANCE.md)

## Local startup (typical)

1. **API** — `backend/`: `uvicorn app.main:app --host 127.0.0.1 --port 8000`  
2. **Frontend** — `frontend/`: `npm run dev -- --host 127.0.0.1 --port 5173`  
3. **Electron** — `electron/`: `npm start` (or package script) with API/UI URLs configured  

For Playwright / CI auth stability set `ZECT_PYTEST=1` so dotenv cannot stomp test credentials (TI-001).

## Required / core env

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy DB |
| `ZECT_USERNAME` / `ZECT_PASSWORD` | Local auth |
| `ZECT_AUTH_MODE` / `ZECT_AUTH_ENFORCE` | Auth mode |
| `ENCRYPTION_KEY` | Secrets vault (CI mints ephemeral) |
| `MENTRIX_ENABLED` | Mentrix feature flag |
| `LATTICE_ENABLED` / `RAG_ENABLED` | Lattice / RAG |
| `ZECT_CODING_ENGINE` | Prefer `mentrix_native` in product; CI may use `mock` |
| `ZECT_MODEL_FALLBACK_POLICY` | Default `never` |
| `ZECT_LLM_BASE_URL` | Optional local OpenAI-compatible gateway |
| `OPENAI_API_KEY` | Cloud LLM / embeddings / Ultra Review LLM |
| `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN` | Jira live |
| `ZECT_CAMUNDA_BASE_URL` or `CAMUNDA_BASE_URL` | Camunda live |
| `MENTRIX_PR_DRY_RUN` | PR safety |
| `VITE_API_URL` | Frontend → API |

Template: `backend/.env.example`.

## CI (`.github/workflows/ci.yml`)

| Job | What |
|-----|------|
| backend | `pytest` with test auth + sqlite |
| frontend | `npm run build` |
| e2e | Start API with `ZECT_PYTEST=1`, run **`npm run test:e2e:core`** |

Core e2e specs: mentrix-smoke, labs-productivity-spine, mentrix-companion, mentrix-incident, agent-workspace-shell, phase-completion-smoke.

## Dependencies (conceptual)

```text
DB + auth → API
API → Frontend / Electron
Optional: local LLM gateway, Jira, Camunda, OpenAI, Electron Computer Mode
```

Missing optional integrations degrade health components to `not_configured` / `degraded` — they do not invent parallel engines.
