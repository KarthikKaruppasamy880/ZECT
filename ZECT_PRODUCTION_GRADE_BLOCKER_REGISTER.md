# ZECT Production-Grade Blocker Register

**Date:** 2026-08-19  
**Canonical develop:** `394cf272c9332754ad9b0b9d5819921ad81fccd6` (PR **#168** human-merged)  
**Branch:** `feat/release-profile-reconciliation`  
**Rule:** Skip / `BLOCKED_EXTERNAL` ≠ PASS. Optional connectors do not block ZECT_CORE.

PostgreSQL from code (`database.py`, `db_url.py`, `.env.example`, `docker-compose.yml`):
- Core / CI / packaged Electron default = `desktop_sqlite`.
- `DATABASE_URL` postgres* = `server_postgres` (Alembic required, no SQLite fallback).
- Live Alembic apply remains unproven unless `ZECT_TEST_POSTGRES_URL` is set.

## Optional connectors (do not block ZECT_CORE)

Remain **BLOCKED_EXTERNAL** until live proof. Not Core mandatory dependencies.

| ID | Certification | Result | Why not PASS |
|----|---------------|--------|--------------|
| LIVE_GITHUB_PR | GitHub | **BLOCKED_EXTERNAL** | Coding Agent headed journey stops at git approval; live push/PR not executed. |
| LIVE_JIRA_INGEST | Jira | **BLOCKED_EXTERNAL** | Full-release journey does not click live ingest. |
| LIVE_CAMUNDA | Camunda | **BLOCKED_EXTERNAL** | `CAMUNDA_BASE_URL` unset; ingest 503. |
| LIVE_PRESENTON_GENERATE | Presenton | **BLOCKED_EXTERNAL** | Live Generate not executed (`ZECT_LIVE_PRESENT` unset). Presenton is optional vs Core; still the Present product default until S8C. |
| LIVE_VOICEBOX | Voicebox | **BLOCKED_EXTERNAL** | Voicebox URL unset; skip ≠ PASS. |

## Desktop (does not block ZECT_CORE)

| ID | Gate | Result | Why not PASS |
|----|------|--------|--------------|
| CLEAN_WINDOWS_NSIS | Clean-machine Windows installer | **BLOCKED_EXTERNAL** | NSIS target exists; no clean-machine proof. Keeps **ZECT_DESKTOP_WINDOWS** PARTIAL. |
| LIVE_PPT_COM | PowerPoint COM | **BLOCKED_EXTERNAL** | Opt-in unset. Optional desktop capability, not a Core dependency. |

## Mode-specific (does not block ZECT_CORE)

| ID | Gate | Result | Why not PASS |
|----|------|--------|--------------|
| LIVE_POSTGRES | Live `server_postgres` Alembic apply | **BLOCKED_EXTERNAL** | `ZECT_TEST_POSTGRES_URL` unset. Mandatory **when** postgres URL is set (fail closed). Not required for Core sqlite. |

## Review

| ID | Gate | Result |
|----|------|--------|
| CODERABBIT_SKIPPED | Substantive CodeRabbit review | **SKIPPED** (widget ≠ PASS). Does not block ZECT_CORE. |

## Closed this reconciliation

| ID | Gate | Result |
|----|------|--------|
| CI_ELECTRON_WINDOWS | Electron in GitHub Actions | **PASS** — `e2e-electron` on `windows-latest` with `ZECT_REQUIRE_ELECTRON=1`. [run 32260773891](https://github.com/KarthikKaruppasamy880/ZECT/actions/runs/32260773891). Ubuntu `test:e2e:core` still does not launch Electron (correct). |
