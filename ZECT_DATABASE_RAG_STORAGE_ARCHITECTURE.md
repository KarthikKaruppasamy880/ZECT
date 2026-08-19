# ZECT Database / RAG / Storage Architecture

**Date:** 2026-08-19  
**Canonical develop:** `797534df747ce7f5e41412273bd5965a32220fe3` (PR **#167** human-merged)  
**Prompt:** `prompts/ZECT_PERFORMANCE_RELIABILITY_OBSERVABILITY_AND_ARCHITECTURE_CLOSURE.md` §7  
**Rule:** Documentation follows **code**, not assumptions. PostgreSQL/pgvector are not labeled as RAG stores unless implemented.

## Code answers

| # | Question | Answer |
|---|----------|--------|
| 1 | Is PostgreSQL canonical server/application DB? | **Yes, for server/docker.** `docker-compose.yml` sets `DATABASE_URL=postgresql+psycopg://...`. `init_db()` runs `alembic upgrade heads` only when `database_mode() == "server_postgres"`. Unreachable Postgres **does not** fall back to SQLite. |
| 2 | Is PostgreSQL also RAG vector DB? | **No.** RAG vectors live in the **same application database** (Postgres *or* SQLite) as ordinary TEXT JSON columns. |
| 3 | Is pgvector used? | **No.** No `pgvector` import, no `CREATE EXTENSION vector`, no `vector` column. `docker-compose` uses stock `postgres:16-alpine`. |
| 4 | What vector store is used? | **SQLAlchemy tables + in-process cosine:** `embedding_chunks.embedding_json` (bag-of-tokens) and `code_embeddings.embedding` (OpenAI `text-embedding-3-small` JSON list). |
| 5 | Is SQLite intentional desktop/local mode? | **Yes.** `desktop_sqlite` is the packaged Electron store (`ZECT_USER_DATA/data/zect.db`). Schema via `create_all` + additive columns. Alembic is **not** run against the live sidecar SQLite file (pool deadlock). |
| 6 | Which data uses Alembic? | **Server Postgres boot only.** Incremental revisions plus catch-up `f1a6c7d8e9b0`. Desktop SQLite uses `create_all` + `_add_missing_columns`. |
| 7 | Which indexes are rebuildable? | Lattice JSON graphs, `embedding_chunks`, `code_embeddings`, `code_symbols`, structural blueprints, document/web chunks. User CRUD (projects, work items, knowledge, memory, auth) requires DB backup. |

Misleading comments (`pgvector-ready`, “pgvector when available”) were corrected in this PR to match the implementation.

## Component table

| Component | Store | schema/table/index | migration owner | local/server mode | persistence | backup/recovery | source files | status |
|-----------|-------|--------------------|-----------------|-------------------|-------------|-----------------|--------------|--------|
| Application/transaction DB | SQLite or PostgreSQL (SQLAlchemy) | ORM tables in `app.models` (~80) | Postgres: Alembic; SQLite: `create_all` | `desktop_sqlite` default; `server_postgres` when URL is postgres | Durable | SQLite: `backup_sqlite_database()` (WAL checkpoint + copy); Postgres: operator `pg_dump` (no app wrapper) | `database.py`, `db_url.py`, `models.py` | Implemented |
| Sessions / auth | App DB | `users`, `auth_tokens`, `user_sessions`, `persistent_sessions`, `session_messages` | ORM + catch-up | Both | Durable | DB backup | `models.py` | Implemented |
| Projects / repos | App DB | `projects`, `repos` | ORM + catch-up | Both | Durable | DB backup | `models.py` | Implemented |
| WorkItems | App DB + filesystem | `work_items`, `work_item_events`; `.zect/work/{id}/` | ORM + catch-up | Both | DB + PLAN.md / EVIDENCE.json | Rebuild PLAN from DB metadata; artifacts are engineering SoT | `models.py`, `artifact_store.py` | Implemented |
| Lattice graph | Filesystem JSON + RAM | `{LATTICE_CACHE_DIR}/{sha1}.json`, `_GRAPH_CACHE` | None (rebuildable) | Both | File + RAM | Re-run `/api/lattice/ingest` | `lattice/indexer.py` | Implemented |
| Lattice blueprint | App DB | `lattice_structural_blueprints` | ORM + catch-up | Both | Durable | Rebuild `build_structural_blueprint` | `structural_blueprint.py` | Implemented |
| RAG (Lattice path) | App DB | `embedding_chunks` (`embedding_json` TEXT) | ORM | Both | Durable | Re-index `index_directory` | `rag/retriever.py` | Implemented — bag-of-tokens, not pgvector |
| Build semantic index | App DB | `code_embeddings` (JSON floats) | ORM | Both | Durable | Re-run `index_repo_semantic` | `build_intel/` | Implemented — Python cosine |
| Knowledge Base | App DB | `knowledge_entries` | ORM | Both | Durable | Re-import | `knowledge_base.py` | Implemented — SQL `ILIKE`, not vector |
| Document Intelligence | App DB + files | `document_*`; `.zect/documents/` | ORM + catch-up | Both | DB + markdown | Re-ingest | `document_intelligence/service.py` | Implemented — no second vector index |
| Web Intelligence | App DB + files | `external_content_*`; `.zect/web/` | Alembic `e9c4a1b2d3f0` | Both | DB + markdown | Re-fetch | `web_intelligence/service.py` | Implemented |
| Verified Memory (UI) | App DB | `typed_memory_records` (+ legacy memory tables) | ORM | Both | Durable | DB backup | `companion_scope.py`, `memory.py` | Implemented — not a separate table named verified_memory |
| LLM response cache | App DB | `llm_response_caches` | ORM | Both | Durable | Truncate-safe | `response_cache.py` | Implemented |
| Coding missions | Filesystem + RAM | `{ZECT_USER_DATA}/data/coding_missions/{id}.json` | None | Both | JSON + RAM | Reload from disk | `coding_engine/lifecycle.py` | Implemented |
| Git worktrees | Filesystem | `zect-coding-worktrees/` | None | Both | Git dirs | Preserved on cancel | `lifecycle.py` | Implemented |
| PPTX / templates | Filesystem | user Documents/`.zect/present-*` | None | Both | Files | User-managed | `pptx_paths.py` | Implemented |
| pgvector / Chroma / FAISS / Qdrant / Redis | — | — | — | — | — | — | comments only (now corrected) | **Not implemented** |

## Modes (intentional dual-store)

```text
DATABASE_URL postgres*  → server_postgres → Alembic heads → fail closed
otherwise              → desktop_sqlite  → create_all + additive columns
```

Packaged Electron (`electron/resources/backend/zect_api_entry.py`) sets `sqlite:///{userData}/data/zect.db`.

## Rebuildable vs not

**Rebuildable:** Lattice graphs, RAG chunks, code embeddings/symbols, structural blueprints, document/web chunk tables, LLM cache.

**Not rebuildable from code alone:** users/auth, projects, work items + events, knowledge CRUD, typed memory, cloned voices, audit logs.
