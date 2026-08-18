# ZECT Runtime Architecture

> **HISTORICAL supporting note.** Canonical parent is now [`ZECT_CANONICAL_ARCHITECTURE.md`](../../ZECT_CANONICAL_ARCHITECTURE.md). Dual-mode `desktop_sqlite` / `server_postgres` is documented there.

**Former parent:** [`ZECT_SYSTEM_ARCHITECTURE.md`](../../ZECT_SYSTEM_ARCHITECTURE.md)  
**Evidence:** [`ZECT_PRODUCT_ACCEPTANCE.md`](../../ZECT_PRODUCT_ACCEPTANCE.md)

## Runtime topology

| Process | Role | Typical bind |
|---------|------|----------------|
| FastAPI (`uvicorn app.main:app`) | API, Mentrix spine, Lattice, Fabric, system health | `127.0.0.1:8000` |
| Vite frontend | Mentrix Delivery Control Tower UI | `127.0.0.1:5173` |
| Electron | Desktop shell + Computer Mode bridge | local OS |
| Optional local LLM gateway | OpenAI-compatible `/v1` for Ask/Plan/Companion/Coding | `ZECT_LLM_BASE_URL` |
| Optional Camunda | Process engine via `/api/process` | `ZECT_CAMUNDA_BASE_URL` / `CAMUNDA_BASE_URL` |

## In-process Mentrix spine (backend)

```text
HTTP / WS
  → routers (api/register.py)
  → MentrixDeveloperService
       ├─ MentrixContextEngine
       ├─ ProjectIntelligenceService
       ├─ ArtifactStore (.zect/work/<id>/)
       ├─ Coding Agent adapter (mentrix_native)
       ├─ ForgeLoop orchestrator (compat + build)
       └─ EvidenceVerifier → WorkItem GATE statuses
```

Key modules:

| Component | Path |
|-----------|------|
| Developer service | `backend/app/services/work_items/developer_service.py` |
| Context engine | `backend/app/services/work_items/context_engine.py` |
| Project intelligence | `backend/app/services/work_items/project_intelligence.py` |
| Artifact store | `backend/app/services/work_items/artifact_store.py` |
| Evidence verifier | `backend/app/services/work_items/evidence_verifier.py` |
| Checkpoints / resume state | `backend/app/services/work_items/checkpoints.py` |
| ForgeLoop | `backend/app/services/forge_loop/orchestrator.py` |
| Coding runtime | `backend/app/adapters/coding_engine_mentrix.py` |
| LLM gateway | `backend/app/adapters/llm/openai_compat.py` |
| Companion | `backend/app/services/mentrix/companion.py` |
| System health / P3 surfaces | `backend/app/routers/system_health.py` |

## Data at rest (runtime)

| Store | Purpose |
|-------|---------|
| SQL DB (`DATABASE_URL`) | WorkItem, WorkItemEvent, SkillDefinition, SecurityFinding/Incident, projects/repos |
| `.zect/work/<id>/` | PLAN.md, EXECUTION_MANIFEST.json, EXECUTION_STATE.json, EVIDENCE.json |
| `.zect/skills/*/SKILL.md` | Portable skill packs (synced with DB) |
| `backend/data/` | Lattice dumps, desktop bridge queue (runtime; not product SoT) |

## Security / desktop runtime boundary (shipped)

- **SecurityScanner** (`MentrixSecurityAgentScanner`) reads Security Agent DB findings and routes to `/security-incidents`. It is **not** a native deep malware daemon.
- **Desktop readiness** reports Electron/`computer.js` / bridge queue presence. Advanced Computer Mode automation remains a **deferred epic**.

## Health endpoints

- `GET /healthz` — liveness  
- `GET /api/system/health` — component readiness (API, auth, coding engine, model gateway, jira, camunda, lattice, work items, desktop, skills_fs)  
- `GET /api/system/model-readiness` — route + matrix (`claim_fully_local: false`)  
- `GET /api/system/desktop-readiness` — Electron/Computer Mode presence
