# Phase 2 Execution Plan — Coding Engine Provider

Companion to `Upgrade.md` Phase 2 and `TARGET_ARCHITECTURE.md`. Staged PRs to
`develop`; stop after each merge for approval.

## Branding

Public contracts use `mock` / `remote` / `sandboxed_v1` only. Third-party agent
server names must not appear in routes, UI, DB columns, or user-visible API
JSON. Attribution lives in `THIRD_PARTY_NOTICES.md`. Internal adapter module
names are implementation detail.

## Stages

| Stage | PR scope | Status |
|---|---|---|
| A | Workspace provisioner (git worktree), factory `ZECT_CODING_ENGINE`, `/api/coding-engine/health`, notices | **Done** |
| B | Remote HTTP adapter + event translation (mocked in CI); `/api/coding-engine/runs*` | **This PR** |
| C | Mentrix/Build vertical slice wire-up (opt-in remote) | Pending |
| D | Docker isolation + harden | Pending |

## Stage B files

- `backend/app/adapters/coding_engine_events.py` — remote → `RuntimeEvent` map
- `backend/app/adapters/coding_engine_remote.py` — start/stream/cancel/approve + retries
- `backend/app/adapters/coding_runtime.py` — process singleton for run continuity
- `backend/app/domains/workspace/coding_engine.py` — thin run APIs
- `backend/tests/test_coding_engine_stage_b.py`

## Env

```
ZECT_CODING_ENGINE=mock          # mock | remote
ZECT_CODING_ENGINE_URL=          # remote Agent Server base URL (server-side only)
ZECT_CODING_ENGINE_API_KEY=      # session key; never sent to browser
ZECT_CODING_ENGINE_TIMEOUT=30
ZECT_CODING_ENGINE_RETRIES=2
ZECT_ENGINE_WORKSPACE_ROOT=      # allowlisted root for per-run worktrees
```

## Verification

- Full `pytest` green
- Branding: no third-party product name under `frontend/` or public route paths
- Stop for Stage C approval after merge
