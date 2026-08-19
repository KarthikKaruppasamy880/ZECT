# ZECT Graphify / Lattice Contract

**Date:** 2026-08-19  
**Canonical develop:** `8c18b83b981f71a4e6e318923d35a78c8e1fe79e` (PR **#169** human-merged)  
**Rule:** Graphify constructs repository intelligence. Lattice remains the governed provenance/query/context layer. **No second RAG, index, or agent framework.**

Graphify = what exists / how connected.  
Lattice = what authorized intelligence is usable now.

`Repos → Graphify ingest → GraphifySnapshot(repo, SHA) → Lattice(freshness, auth, provenance, query) → ContextEngine → Companion / Developer / Coding Agent / PI / WorkItems`

## Identities

| Identity | Canonical | Notes |
|----------|-----------|--------|
| Project | `projects.id` | Authorization boundary |
| Workspace root | registered `repos.local_path` | Multi-root Developer |
| Repo | `repos.id` + `owner/repo_name` | Permission Broker |
| Lattice/Graphify key | `derive_project_key(owner, repo_name)` | Must match frontend `deriveProjectKey` |
| Commit SHA | git `HEAD` via `git_head_sha(local_path)` | Live SHA |
| Indexed SHA | `lattice_structural_blueprints.indexed_commit_sha` + snapshot `commit_sha` | STALE when live ≠ indexed |

## Node kinds (supported)

`file`, `class`, `function`, `method`, `endpoint`, `doc`, `test` (G2), ownership via `GraphNode.group` from CODEOWNERS when present.

## Edge kinds (supported)

Intra-repo: `contains`, `imports`, `imports_file`, `calls`, `test_of`.

Cross-repo (G3): only `package_dependency`, `api_contract`, `import`, `schema`, `test_fixture`, `configured`.  
**Never** connect repos from name similarity. Each cross-repo edge requires `source_repo`, `source_sha`, `target_repo`, `target_sha`, `type`, `evidence`, `confidence`.

## Snapshot

`GraphifySnapshot` is an adapter over the existing Lattice graph JSON + `get_lattice_status`. It is **not** a second store.

States (shared Header / Explorer / PI / Context):  
`NOT_CONFIGURED | NOT_INDEXED | INDEXING | READY | STALE | ERROR | NOT_APPLICABLE`  
(`REGRESSION` remains Lattice-internal). SHA change → STALE. Successful ingest → READY@SHA.

## Provenance / auth / incremental / errors

- Auth: existing `/api/lattice/*` `get_current_user` + repo authorization. Graph evidence **never** grants edit permission.
- Incremental: if `commit_sha` matches live HEAD and `force` is false, ingest returns the cached graph (`incremental=true`).
- Parse failures are isolated per file (`graph.errors`); they do not abort the whole ingest.
- Cancel: existing `LatticeCancelled` / `POST /api/lattice/ingest/cancel`.
- Pollution skipped: vendor/generated/secret/binary dirs and files (see `SKIP_DIRS` / skip suffixes).

## Code classification

| Path | Class | Why |
|------|--------|-----|
| `backend/app/services/lattice/indexer.py` | **EXTEND** | Canonical ingest; incremental SHA skip, tests, CODEOWNERS, pollution skip |
| `backend/app/domains/repository/lattice.py` | **EXTEND** | Snapshot + cross-repo + `force` rebuild |
| `backend/app/services/lattice/graphify_snapshot.py` | **ADD** | One adapter GraphifySnapshot → Lattice |
| `backend/app/services/lattice/cross_repo.py` | **ADD** | Evidence-backed cross-repo edges only |
| `backend/app/services/lattice/structural_blueprint.py` | **REUSE** | Indexed SHA persistence |
| `backend/app/services/work_items/context_engine.py` | **REUSE** | Provenance model; graph never grants write |
| `backend/app/services/work_items/project_intelligence.py` | **EXTEND** | Expose `local_path` so PI Index runs Lattice ingest |
| `backend/app/services/mentrix/companion.py` `lattice_query` | **REUSE** | Companion intelligence (G7) already queries Lattice |
| `frontend/src/pages/LatticeGraph.tsx` | **REUSE** | Explorer |
| `frontend/src/pages/ProjectIntelligence.tsx` | **EXTEND** | Index/Re-index calls Lattice ingest |
| `backend/app/services/auto_indexer.py` | **REPLACE later** | Duplicate symbols; not removed this phase |
| `build_intel/indexer.py` | **REUSE** | Separate Build semantic store |
| New Graphify service / vector DB | **REMOVE (do not add)** | Would duplicate Lattice |

## Out of scope this spine

G6 richer impact PLAN (ContextEngine already consumes PI hits). G7 UX copy must say Lattice, not Graphify internals. D1–P3 and `zect.ps1` are other focused PRs.
