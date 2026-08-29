# ZECT System Architecture

> **HISTORICAL.** Canonical current architecture is [`ZECT_CANONICAL_ARCHITECTURE.md`](ZECT_CANONICAL_ARCHITECTURE.md) and storage truth is [`ZECT_DATABASE_RAG_STORAGE_ARCHITECTURE.md`](ZECT_DATABASE_RAG_STORAGE_ARCHITECTURE.md). Mentrix spine notes below remain useful; do not treat PostgreSQL as the only DB or as pgvector RAG.

**Status:** HISTORICAL (P0–P3 spine)  
**Branch / evidence:** `develop` @ `f80fda4` / `bdd0b35`  
**Acceptance:** [`ZECT_PRODUCT_ACCEPTANCE.md`](ZECT_PRODUCT_ACCEPTANCE.md)  
**Scope rule:** Do not claim features beyond acceptance. `claim_fully_local: false`.

---

## Product spine (shipped)

```text
User / Companion
  → ASK / PLAN / AGENT (MentrixDeveloperService)
  → WorkItem (+ Project / Repo identity)
  → Project Intelligence
       (Lattice + Blueprint + Knowledge + Memory
        + Skills + Playbooks + related work + freshness)
  → ContextEngine (ContextPack + provenance)
  → Fabric (process handoff)
  → Mentrix Coding Agent (mentrix_native)
  → ForgeLoop (SDLC orchestration)
  → Ultra Review (3-lane merge; no second review LLM)
  → EvidenceVerifier
  → Git / PR / CI
  → Jira / Camunda close-loop (dry_run supported)
```

Incomplete requirements/operations **cannot** become `READY_TO_SHIP` / `DONE` without EvidenceVerifier (`allow_gate=True`). Default model fallback policy is **`never`** (no silent cloud context).

---

## Canonical owners

| Concern | Canonical owner | Must not own |
|---------|-----------------|--------------|
| PLAN.md + plan hash / reapproval | WorkItem **ArtifactStore** (`.zect/work/<id>/`) | Standalone `/plan` page, LLM chat |
| EXECUTION_MANIFEST / STATE / EVIDENCE | ArtifactStore | MentrixRun alone |
| WorkItem lifecycle | `WorkItem.status` | Companion ephemeral state |
| Append-only audit | `WorkItemEvent` | Overwrites |
| ContextPack | Mentrix **ContextEngine** | Dumping whole Lattice |
| Code edits | Mentrix **Coding Agent** (`mentrix_native`) | Parallel silent mock engine |
| SDLC ship gate | **EvidenceVerifier** → `READY_TO_SHIP` | LLM “done” text |
| Knowledge vs Memory | Separate via ProjectIntelligence | Collapsed single store |
| Skill **execution** SoT | `SkillDefinition` (DB) | Raw FS alone |
| Skill packs (portable) | `.zect/skills/*/SKILL.md` + bi-sync | Foreign skill runtime |
| Security findings UI path | ZECT Security Agent store | Foreign AV rewrite (deferred) |
| Desktop automation | Existing Electron Computer Mode | New desktop agent (deferred) |

---

## API layers (merged)

| Layer | Prefix | Role |
|-------|--------|------|
| Work Items | `/api/work-items` | CRUD, ingest (user/jira/camunda), events, gated transitions |
| Mentrix Developer | `/api/mentrix/developer` | ask, plan, approve-plan, agent, resume, PI, fabric-handoff, close-loop |
| Companion / Delivery | `/api/mentrix` | companion turn/stream, desktop-bridge, runs |
| Lattice | `/api/lattice` | ingest, graph, query, RAG, blueprint |
| Fabric | `/api/fabric` | surfaces, classify, run |
| Process (Camunda) | `/api/process` | status, deploy, start, incidents |
| Jira integration | `/api/jira` | status/config/tickets (ingest via work-items) |
| Ultra Review | `/api/ultrareview` | snippet/sessions + `/lanes` + WI context |
| Coding Agent | `/api/coding-agent` | sessions / stream / approve |
| System (P2/P3 ops) | `/api/system` | health, model-readiness, skills-fs sync, security-scan, desktop-readiness |

---

## Supporting architecture docs (canonical set)

| Doc | Topic |
|-----|--------|
| [`docs/architecture/ZECT_RUNTIME_ARCHITECTURE.md`](docs/architecture/ZECT_RUNTIME_ARCHITECTURE.md) | Runtime components & process boundaries |
| [`docs/architecture/ZECT_DEVELOPER_FLOW.md`](docs/architecture/ZECT_DEVELOPER_FLOW.md) | Developer UX / sidebar / Context Used |
| [`docs/architecture/ZECT_PROJECT_INTELLIGENCE_FLOW.md`](docs/architecture/ZECT_PROJECT_INTELLIGENCE_FLOW.md) | PI snapshot & Skills bi-sync |
| [`docs/architecture/ZECT_SDLC_AND_WORKITEM_FLOW.md`](docs/architecture/ZECT_SDLC_AND_WORKITEM_FLOW.md) | Statuses, gates, EvidenceVerifier |
| [`docs/architecture/ZECT_MODEL_AND_LOCAL_AI_MATRIX.md`](docs/architecture/ZECT_MODEL_AND_LOCAL_AI_MATRIX.md) | Providers, fallback, local-AI matrix |
| [`docs/architecture/ZECT_INTEGRATION_MAP.md`](docs/architecture/ZECT_INTEGRATION_MAP.md) | Jira, Camunda, Git/PR, Fabric |
| [`docs/architecture/ZECT_DEPLOYMENT_AND_ENVIRONMENT.md`](docs/architecture/ZECT_DEPLOYMENT_AND_ENVIRONMENT.md) | Startup, env, CI |
| [`docs/architecture/ZECT_RELEASE_SCOPE_AND_DEFERRED_EPICS.md`](docs/architecture/ZECT_RELEASE_SCOPE_AND_DEFERRED_EPICS.md) | Shipped vs deferred epics |

Related ownership ledger (still useful): [`docs/architecture/ZECT_DATA_FLOW_AND_OWNERSHIP.md`](docs/architecture/ZECT_DATA_FLOW_AND_OWNERSHIP.md) — interpret with P1+ adapters live, not “stubs only”.

---

## Acceptance evidence (summary)

From [`ZECT_PRODUCT_ACCEPTANCE.md`](ZECT_PRODUCT_ACCEPTANCE.md):

- Core spine pytest + gates: **PASS**
- Skills DB↔FS bidirectional: **PASS**
- Core Playwright (`test:e2e:core`): **33 passed** local; CI e2e **PASS** on #128
- Local-AI: **not fully local**; Ultra Review + Embeddings **CLOUD_ONLY** when keyed
- Deferred only: ZECT-native malware engine; advanced Computer Mode; deeper fully-local AI where PARTIAL/CLOUD_ONLY

---

## Explicit non-claims

- No parallel Ask/Plan/Context/Coding/Review engines  
- No foreign AV / ClamAV rewrite  
- No advanced desktop rewrite  
- No claim of fully local AI stack  
- No P4/P5 architecture phases in this release
