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
| A | Workspace provisioner (git worktree), factory `ZECT_CODING_ENGINE`, `/api/coding-engine/health`, notices | **This PR** |
| B | Remote HTTP/WS adapter + event translation (mocked in CI) | Pending |
| C | Mentrix/Build vertical slice wire-up (opt-in remote) | Pending |
| D | Docker isolation + harden | Pending |

## Stage A files

- `backend/app/services/coding_engine/workspace.py` — provision / dispose / artifacts
- `backend/app/adapters/coding_runtime.py` — factory switch
- `backend/app/adapters/coding_engine_remote.py` — remote stub (health probe; run methods Stage B)
- `backend/app/domains/workspace/coding_engine.py` — thin HTTP surface
- `backend/tests/test_coding_engine_stage_a.py`
- `THIRD_PARTY_NOTICES.md`, `backend/.env.example`, `docs/ROADMAP.md`

## Env

```
ZECT_CODING_ENGINE=mock          # mock | remote
ZECT_CODING_ENGINE_URL=          # remote Agent Server base URL (server-side only)
ZECT_CODING_ENGINE_API_KEY=      # session key; never sent to browser
ZECT_ENGINE_WORKSPACE_ROOT=      # allowlisted root for per-run worktrees
```

## Verification

- Full `pytest` green
- Branding grep: no third-party product name under `frontend/` or public route paths
- Stop for Stage B approval after merge
