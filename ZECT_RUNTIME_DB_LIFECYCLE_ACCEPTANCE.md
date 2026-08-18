# ZECT Runtime / Database Lifecycle Acceptance

**Date:** 2026-08-18  
**Canonical develop (pre-PR):** `0e730ac3b9397d5b9c638669017c59a19d82e821` (PR **#162** human-merged — Recovery)  
**This PR branch:** `feat/runtime-db-lifecycle`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md` — production runtime/database lifecycle, then executable install/upgrade/recovery gates  
**Stop label:** `READY_TO_MERGE_RUNTIME_RECOVERY` — human merge only, no auto-merge.  
**Do not start tranche F (performance / load / soak) until this PR is human-merged.**

## Verdict

**READY_TO_MERGE_RUNTIME_RECOVERY** with honest external blockers. Desktop SQLite and the Postgres *boot contract* are proven in this environment. Live PostgreSQL apply and clean-machine Windows NSIS remain **BLOCKED_EXTERNAL**.

| Gate | Result |
|------|--------|
| Supported modes explicit (`desktop_sqlite` / `server_postgres`) | **PASS** |
| desktop_sqlite schema create (`create_all`) | **PASS** |
| desktop_sqlite additive upgrade from older `users` table | **PASS** |
| desktop_sqlite persist + restart | **PASS** |
| desktop_sqlite WAL concurrent read/write | **PASS** |
| desktop_sqlite backup = file copy after WAL checkpoint | **PASS** |
| Alembic linear chain `bfe9cfe5fde9` → `f1a6c7d8e9b0` | **PASS** |
| Alembic `upgrade heads` twice (sqlite file) | **PASS** |
| Alembic unknown revision raises | **PASS** |
| Alembic downgrade `-1` then upgrade (data remains) | **PASS** |
| server_postgres unreachable: no SQLite fallback | **PASS** |
| server_postgres `init_db` calls Alembic, not `create_all` | **PASS** (unit) |
| server_postgres Alembic failure / missing `users` fail closed | **PASS** (unit) |
| Live PostgreSQL `ZECT_TEST_POSTGRES_URL` apply | **BLOCKED_EXTERNAL** unless the env var is set |
| `/healthz` `database_mode` / dialect / lifecycle; no URL/secrets | **PASS** |
| Packaged sidecar default sqlite under `ZECT_USER_DATA` | **PASS** (source + unit) |
| Occupied-port sidecar (`api_already_listening`) | **PASS** (`electron/service-lifecycle.node-test.js`) |
| Coding-agent missions persist across restart | **PASS** (post-#162 regression) |
| Windows NSIS / clean-machine one-click | **BLOCKED_EXTERNAL: CLEAN_WINDOWS_ENVIRONMENT_REQUIRED** |
| Live Presenton / Voicebox / GitHub / Jira / Camunda | **BLOCKED_EXTERNAL** when unset — does not block ZECT-native DB tests |
| Headed `/healthz` + System Health database component | **PASS** in CI e2e (fresh API). Local :8000 was a pre-change occupying sidecar (not killed). New-code proof: `http://127.0.0.1:8001/healthz` returns `desktop_sqlite`. |
| Electron System Health | **SKIPPED** (`electron.exe` not installed) ≠ PASS |
| Frontend `npm run build` | **PASS** |
| Mentrix Ultra Review | **PASS** (0 critical; invalid high finding rejected) |

Overall ZECT remains **ZECT_PRODUCTION_PARTIAL**. This tranche does **not** start soak, a11y, Graphify, or S8C/S8D.

## Architecture (intentional)

| Mode | Selection | Boot schema | Not a defect |
|------|-----------|-------------|--------------|
| **desktop_sqlite** | Default; packaged Electron `ZECT_PACKAGED=1` + `DATABASE_URL=sqlite:///{userData}/data/zect.db` | `create_all` + `_add_missing_columns` + cloned_voices. Alembic is **not** run at sidecar boot (a second connection deadlocks live SQLite). `alembic upgrade heads` is proven on a dedicated engine and is the **server_postgres** boot path. | Local/desktop zero-config store |
| **server_postgres** | `DATABASE_URL=postgresql://...` | **Required** `alembic upgrade heads`. No `create_all` in `init_db`. Unreachable server raises — **no SQLite fallback** | Production/server lifecycle |

Honest history: revision `bfe9cfe5fde9` upgrade is empty (`pass`). Incremental revisions FK to `users` / `projects`. `alembic/env.py` bootstraps ORM tables when `users` is missing so a fresh `upgrade heads` can run. Catch-up revision `f1a6c7d8e9b0` (revises `e9c4a1b2d3f0`) runs idempotent `create_all` for databases already stamped. Prior revision files were **not** edited.

Backup: sqlite = file copy after `PRAGMA wal_checkpoint(TRUNCATE)`. Postgres = `pg_dump` (operator), not file copy.

## Post-merge #162 regression (this session)

Canonical `origin/develop` = `0e730ac3b9397d5b9c638669017c59a19d82e821` (`Merge pull request #162`).

## Mentrix Ultra Review

`backend/scripts/runtime_db_lifecycle_ultra_review.py` → `test-results/runtime-db-lifecycle/ultra-review.json`

- **passed:** true; **critical_findings:** 0; **score:** 85; **model:** gpt-4o-mini
- Finding marked **high** (“no SQLite fallback / unhandled exception”) is **rejected**. Fail-closed with no SQLite fallback is the server_postgres contract.
- Finding marked **medium** (bind defaulting to module `engine`) is accepted as the module-level `init_db()` path; tests pass an explicit bind.

CodeRabbit / other external review: **SKIPPED** until the PR exists; skip ≠ PASS.

## Stop

Human-merge this PR. Do **not** start tranche F until `origin/develop` contains this merge.
