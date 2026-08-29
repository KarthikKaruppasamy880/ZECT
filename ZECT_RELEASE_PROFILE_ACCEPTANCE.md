# ZECT Release Profile Acceptance

**Date:** 2026-08-19  
**Canonical develop:** `0dd7becb2c98b7e6c368bee10392925d1f3d57f2` (PRs **#169–#172** human-merged)  
**Branch:** `develop` after **#172**  
**Stop:** human merge only, no auto-merge.

Release-profile reconciliation (#169) remains in force. Graphify/Lattice spine (#170), `zect.ps1` (#171), and desktop/Present control (#172) are **on develop**. Optional GitHub / Jira / Camunda / Presenton / Voicebox / NSIS remain **BLOCKED_EXTERNAL** and do not block Core.

## Verdicts

| Profile | Verdict |
|---------|---------|
| **ZECT_CORE** | **ZECT_CORE_READY** |
| **ZECT_DESKTOP_WINDOWS** | **ZECT_DESKTOP_WINDOWS_PARTIAL** (Electron CI required; NSIS unproven) |
| GitHub | **BLOCKED_EXTERNAL** |
| Jira | **BLOCKED_EXTERNAL** |
| Camunda | **BLOCKED_EXTERNAL** |
| Presenton | **BLOCKED_EXTERNAL** |
| Voicebox | **BLOCKED_EXTERNAL** |
| Monolith `ZECT_PRODUCTION_READY` | **not awarded** |

Optional connectors do not block Core. `server_postgres` stay fail-closed when a postgres URL is set.

## PostgreSQL (code, not guessed)

| Mode | When | Mandatory? | Core? |
|------|------|------------|-------|
| `desktop_sqlite` | default `.env.example`, CI `DATABASE_URL=sqlite://…`, packaged Electron `ZECT_USER_DATA` | SQLite yes | **yes** — this is Core |
| `server_postgres` | `DATABASE_URL` scheme `postgres*` (`docker-compose.yml`) | PostgreSQL **yes**; unreachable does not fall back to SQLite | **no** — different operational mode |
| Live Alembic on a real server | `ZECT_TEST_POSTGRES_URL` | unproven | does not block Core |

Sources: `backend/app/infrastructure/database.py`, `db_url.py`, `backend/.env.example`, `docker-compose.yml`, `ZECT_DATABASE_RAG_STORAGE_ARCHITECTURE.md`.

## Electron CI

Ubuntu `test:e2e:core` cannot run `electron.exe`. This PR adds job `e2e-electron` on `windows-latest`:
- `electron/npm ci` then assert `electron.exe`
- `ZECT_REQUIRE_ELECTRON=1` so a missing binary **fails** (skip ≠ PASS)
- `npm run test:e2e:electron` → `full-release-e2e-electron.spec.ts`

If that job fails, **ZECT_DESKTOP_WINDOWS** stays PARTIAL with the job log as the exact blocker. Do not treat a skip as PASS.

CI (PR **#169**, SHA `1a4e4b66afbb`): run **32260773891** backend / frontend / e2e / **e2e-electron** **success**.

## Mandatory dependencies not weakened

Auth enforcement, Permission Broker, sqlite Core store, postgres fail-closed for server mode, headed `test:e2e:core`, security pytest. Presenton remains the Present **default provider** until S8C; live Generate is still an optional certification.

Mentrix Ultra Review: **PASS**, score 85, 0 critical, `gpt-4o-mini`.
