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
| B | Remote HTTP adapter + event translation (mocked in CI); `/api/coding-engine/runs*` | **Done** |
| C | Mentrix/Build vertical slice wire-up (opt-in remote) | **Done** |
| D | Isolation harden (Docker optional; worktree default/fallback) | **This PR** |

## Stage D files

- `backend/app/services/coding_engine/isolation.py` — mode resolve + restricted env
- `backend/app/services/coding_engine/docker_sandbox.py` — optional container wrap
- `backend/app/services/coding_engine/workspace.py` — `provision_isolated_workspace` / dispose
- Mentrix bridge uses isolated provision; health reports isolation fields
- `backend/tests/test_coding_engine_stage_d.py`

## Isolation env

```
ZECT_CODING_ENGINE_ISOLATION=worktree   # worktree | docker | auto  (default worktree)
ZECT_CODING_ENGINE_ISOLATION_STRICT=0   # 1 = fail if docker requested but unavailable
ZECT_CODING_ENGINE_SANDBOX_IMAGE=python:3.12-slim
```

Hosts without Docker (including many Windows setups) keep **worktree** isolation.
Docker is used only when the daemon is actually available.

## Phase 2 complete when Stage D merges

Stop for approval before Upgrade.md Phase 3.
