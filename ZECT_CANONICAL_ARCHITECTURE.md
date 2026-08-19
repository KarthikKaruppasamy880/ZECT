# ZECT Canonical Architecture

**Status:** Canonical current architecture (code-backed)  
**Date:** 2026-08-19  
**Canonical develop:** `55255f0b05240815a1547c0ea33d4317706acc99` (PR **#166** human-merged)  
**Storage truth:** [`ZECT_DATABASE_RAG_STORAGE_ARCHITECTURE.md`](ZECT_DATABASE_RAG_STORAGE_ARCHITECTURE.md)  
**Do not start:** S8C/S8D, Graphify, KV-cache expansion, OCR/XLSX, broader Web, new agents.

This file is the **only current** top-level architecture truth. Historical docs that contradict it are marked HISTORICAL below.

---

## Product

```text
User
  → Companion (MentrixCompanion.tsx, companion.py)
  → Developer / Coding Agent (DeveloperWorkspace.tsx, coding_engine/lifecycle.py)
  → Present (PresentationService + Presenton default / zect_native opt-in)
  → Projects / WorkItems / Processes (work_items, Fabric, Jira/Camunda OPTIONAL)
  → PI / Lattice (indexer.py JSON graphs + lattice_structural_blueprints)
  → Knowledge (knowledge_entries ILIKE — not a vector DB)
  → Learning / Skills / Playbooks (SkillDefinition DB + .zect/skills FS packs)
```

Companion does **not** silently edit code. Coding Agent owns worktrees/tests/review/git. Presenton remains the product default until an explicit S8C decision (out of scope).

## Orchestration

```text
Intent → Companion or direct surface
  → Project + WorkItem
  → ContextEngine (permission/provenance)
  → Permission Broker
  → PLAN (ArtifactStore PLAN.md)
  → Developer/Coding Agent  OR  Present  OR  Process
  → EvidenceVerifier
  → Ultra Review / quality gates
  → artifact / PR / status
  → HUMAN MERGE (no auto-merge)
```

## Coding

```text
Multi-root workspace → affected repos → isolated worktrees/branches
  → edit / commands / tests → evidence → Ultra Review
  → per-repo PR/CI → human merge
```

Sibling PASS+FAIL ⇒ BLOCKED. Cancel/resume skips recorded commit SHAs.

## Present

```text
Prompt/files/project evidence
  → Template Intelligence
  → Model Gateway / PresentationPlan
  → VisualPlanner → LayoutComposer → renderer
  → FinalPptxInspector → QualityCritic/repair
  → Review/Edit → Voice/Rehearse (Voicebox OPTIONAL)
  → PPTX / Present
```

RESTRICTED/CONFIDENTIAL decks cannot be sent to Presenton (`restricted_external_provider`).

## RAG / intelligence (actual path)

```text
Sources → ingest (lattice ingest_path / index_directory / document|web ingest)
  → parse/chunk
  → embeddings: bag-of-tokens in embedding_chunks OR OpenAI JSON in code_embeddings
  → STORE: same application DB (desktop_sqlite | server_postgres) as TEXT JSON
  → retrieval: in-process cosine (not pgvector)
  → ContextEngine → Permission Broker / provenance → model/agent
```

**Not implemented:** pgvector, Chroma, FAISS, Qdrant, Redis, Graphify.

## Data / storage

| Concern | Store |
|---------|--------|
| Projects, WorkItems, sessions, Knowledge, Memory | Application DB (`desktop_sqlite` or `server_postgres`) |
| Lattice graph | `LATTICE_CACHE_DIR` JSON + RAM |
| WorkItem PLAN/evidence | `.zect/work/{id}/` |
| Coding missions | durable JSON under `ZECT_USER_DATA` or `backend/data/coding_missions` |
| PPTX / templates | user folders / `.zect/present-*` |
| Telemetry (this tranche) | process ring buffer + optional JSONL; `AuditLog` for privileged actions |

## Security / trust

User / project / repo boundaries; Permission Broker; untrusted context; secrets redaction (`redact.py`); MCP args redacted before `MCPToolAudit`; filesystem jail (`allowed_paths`); subprocess/Git confirm; model/provider sensitivity blocks.

## Runtime / deployment

Browser frontend (Vite), Electron shell + sidecar, FastAPI, native Present renderer, Voicebox OPTIONAL, DBs as dual-mode, Presenton OPTIONAL, GitHub/Jira/Camunda/model/image/web providers OPTIONAL.

## Evidence / release

Tests → headed/Electron where relevant → security → Ultra Review → external review if available → CI → PR → **HUMAN MERGE**.

---

## Diagrams

Nodes without an implementation pointer are marked OPTIONAL or PLANNED.

### 1. System context

```mermaid
flowchart LR
  user[User]
  browser[Browser Vite frontend]
  electron[Electron shell]
  api[FastAPI app.main]
  sqlite[(desktop_sqlite zect.db)]
  pg[(server_postgres)]
  presenton[Presenton OPTIONAL]
  voicebox[Voicebox OPTIONAL]
  llm[Model gateway local or cloud OPTIONAL]
  gh[GitHub OPTIONAL]
  jira[Jira OPTIONAL]
  camunda[Camunda OPTIONAL]
  user --> browser
  user --> electron
  browser --> api
  electron --> api
  api --> sqlite
  api --> pg
  api --> presenton
  api --> voicebox
  api --> llm
  api --> gh
  api --> jira
  api --> camunda
```

### 2. Container / runtime

```mermaid
flowchart TB
  ui[frontend/src MentrixCompanion DeveloperWorkspace Present SystemHealth]
  elec[electron/main.js service-lifecycle.js]
  api[backend/app/main.py]
  mw[Auth RateLimit CorrelationId]
  domains[domains: work_items coding_agent lattice mentrix]
  svc[services: ContextEngine PermissionBroker PresentationService]
  db[(SQLAlchemy engine desktop_sqlite or server_postgres)]
  fs[.zect work lattice missions present]
  ui --> api
  elec --> api
  api --> mw --> domains --> svc
  svc --> db
  svc --> fs
```

### 3. Orchestration sequence

```mermaid
sequenceDiagram
  participant U as User
  participant C as Companion or UI
  participant W as WorkItem
  participant X as ContextEngine
  participant P as Permission Broker
  participant A as Coding Agent or Present or Process
  participant E as EvidenceVerifier
  participant H as Human merge
  U->>C: intent
  C->>W: bind Project+WorkItem
  W->>X: context pack + provenance
  X->>P: tool/repo permission
  P->>A: PLAN then execute
  A->>E: tests/review/quality
  E->>H: READY_TO_MERGE only
```

### 4. Coding-agent sequence

```mermaid
sequenceDiagram
  participant U as User
  participant L as lifecycle.start_mission
  participant WT as isolate_worktree
  participant T as run_repo_tests
  participant R as Ultra Review
  participant G as approve_git
  U->>L: goal + authorized roots
  L->>U: PLAN awaiting approval
  U->>L: approve_plan
  L->>WT: per-repo worktree/branch
  WT->>T: tests per root
  T->>R: sibling aggregate
  alt Critical/High or sibling FAIL
    R-->>U: blocked
  else passed
    R->>G: git approval required
    G->>U: READY_TO_MERGE no auto-merge
  end
```

### 5. Presentation sequence

```mermaid
sequenceDiagram
  participant U as User
  participant S as PresentationService
  participant N as Native or Presenton provider
  participant Q as Inspector + Critic
  U->>S: generate Quality or Fast
  alt RESTRICTED and Presenton
    S-->>U: 403 restricted_external_provider
  else cancelled run_id
    S-->>U: 409 generation_cancelled
  else ok
    S->>N: plan + render
    N->>Q: inspect/repair
    Q-->>U: PPTX + telemetry no bodies
  end
```

### 6. RAG / intelligence sequence

```mermaid
sequenceDiagram
  participant S as Sources repo/docs/web
  participant I as ingest_path / index_directory
  participant DB as App DB embedding_chunks or code_embeddings
  participant R as cosine retriever
  participant C as ContextEngine
  participant A as Agent
  S->>I: walk parse chunk
  I->>DB: JSON float vectors TEXT
  A->>R: query
  R->>DB: load rows
  R->>C: hits + Lattice path boost
  C->>A: permissioned pack
  Note over DB: Not pgvector. Same sqlite or postgres as WorkItems.
```

### 7. Multi-repo WorkItem sequence

```mermaid
sequenceDiagram
  participant W as WorkItem
  participant CE as ContextEngine
  participant M as start_mission
  participant R1 as Repo A worktree
  participant R2 as Repo B worktree
  participant V as EvidenceVerifier
  W->>CE: authorized repo_ids only
  CE->>M: roots
  M->>R1: isolate + test
  M->>R2: isolate + test
  R1->>V: PASS or FAIL
  R2->>V: PASS or FAIL
  alt any FAIL
    V-->>W: blocked sibling
  else all PASS + review
    V-->>W: READY_TO_MERGE per repo PR
  end
```

### 8. Deployment / trust boundaries

```mermaid
flowchart TB
  subgraph browser [Browser origin]
    spa[Vite SPA]
  end
  subgraph electron [Electron]
    shell[main.js]
    sidecar[packaged uvicorn sqlite]
  end
  subgraph apiTrust [API trust boundary]
    auth[AuthMiddleware]
    corr[X-Correlation-Id]
    broker[Permission Broker]
    jail[allowed_paths]
  end
  subgraph data [Data]
    sqlite[(desktop_sqlite)]
    pg[(server_postgres Alembic)]
    artifacts[.zect artifacts]
  end
  subgraph optional [OPTIONAL providers]
    pres[Presenton]
    vb[Voicebox]
    llm[LLM]
    ext[GitHub Jira Camunda]
  end
  spa --> auth
  shell --> sidecar
  sidecar --> auth
  auth --> corr --> broker --> jail
  jail --> sqlite
  jail --> pg
  jail --> artifacts
  broker -.-> pres
  broker -.-> vb
  broker -.-> llm
  broker -.-> ext
```

---

## Consistency / historical

| Document | Status |
|----------|--------|
| `ZECT_CANONICAL_ARCHITECTURE.md` | **Current** |
| `ZECT_DATABASE_RAG_STORAGE_ARCHITECTURE.md` | **Current** storage audit |
| `ZECT_SYSTEM_ARCHITECTURE.md` | HISTORICAL — Mentrix spine still useful; superseded for RAG/DB claims |
| `ZECT_ARCHITECTURE_AND_WORKFLOW.md` | HISTORICAL |
| `docs/architecture/*.md` | HISTORICAL supporting notes |

Contradictions rejected from older docs:

- PostgreSQL is **not** the only application DB (desktop SQLite is intentional).
- PostgreSQL is **not** a pgvector RAG store.
- Presenton is still default; native Present is opt-in.
- Graphify / S8C / KV-cache / OCR-XLSX / extra agents are **PLANNED / out of scope**.
