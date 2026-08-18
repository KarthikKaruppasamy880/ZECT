# ZECT Runtime Recovery Acceptance

**Date:** 2026-08-18  
**Canonical develop (pre-PR):** `9394508` (PR **#161** human-merged — Security)  
**This PR branch:** `feat/runtime-recovery`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md` tranche E  
**Stop label:** `READY_TO_MERGE_RECOVERY` — human merge only, no auto-merge.

## Verdict

**PARTIAL.** Restart/cancel/resume and fail-closed optional providers are proven. Windows one-click / clean-machine NSIS remains **BLOCKED_EXTERNAL**.

| Gate | Result |
|------|--------|
| Clean install (sqlite `create_all`) | **PASS** (packaged sidecar path) |
| Alembic revision chain | **PASS** (linear `bfe9cfe5fde9` → `e9c4a1b2d3f0`) |
| Alembic `upgrade heads` | **PASS** when the `alembic` package is importable; otherwise not a live Postgres PASS |
| DB migration failure | **PASS** (unknown revision raises; corrupt coding-agent JSON → `mission_corrupt`) |
| Backend restart during coding agent | **PASS** (durable JSON; cache clear still `get_mission`) |
| LRR restart recovery | **PASS** (`test_backend_restart_recovery`) |
| Present deck files after process simulation | **PASS** (list recent decks) |
| Occupied port / already-listening API | **PASS** (`sidecarStartDecision` → `api_already_listening`) |
| Stale managed process cleanup | **PASS** (`stopManagedChildren`) |
| Missing optional Presenton | **PASS** (`blocked_external`) |
| Expired credential | **PASS** (401/403) |
| Moved/missing workspace root | **PASS** (`ROOT_UNAVAILABLE`) |
| Cancel / resume no duplicate commits | **PASS** (coding-agent mission G) |
| Headed System Health | **PASS** when `runtime-recovery-production.spec.ts` runs with API up |
| Electron System Health | **PASS** locally (`runtime-recovery-electron.spec.ts`); skip ≠ core PASS if `electron.exe` missing |
| Windows NSIS / clean-machine one-click | **BLOCKED_EXTERNAL: CLEAN_WINDOWS_ENVIRONMENT_REQUIRED** |
| CodeRabbit | **SKIPPED** ≠ PASS |

Overall ZECT remains **ZECT_PRODUCTION_PARTIAL**. This tranche does not start soak, a11y, Graphify, or S8C/S8D.

## Fixes in this PR

1. **High — coding-agent missions were in-memory.** Missions now persist as redacted JSON under `ZECT_CODING_MISSIONS_DIR` / `ZECT_USER_DATA/data/coding_missions`. `get_mission` reloads after process restart. Mission ids are UUID-shaped (no path traversal). Corrupt files fail closed (`409 mission_corrupt`).
2. **Occupied-port policy is explicit** in `electron/service-lifecycle.js` (`sidecarStartDecision`). Packaged Electron already skipped sidecar when `/docs` was up; the helper is now unit-tested.

## Honest limits

- Packaged Windows still uses sqlite `init_db()` / `create_all`, not a live Postgres Alembic cutover.
- `electron-builder` NSIS target exists (`oneClick: false`) but no clean-machine installer proof was run.
- Live Presenton / Voicebox / GitHub remain **BLOCKED_EXTERNAL** when unset.
- Headed e2e does not kill occupying processes or run NSIS.

## Stop

Human-merge this PR. Do **not** start tranche F (performance / soak) until `origin/develop` contains this merge.
