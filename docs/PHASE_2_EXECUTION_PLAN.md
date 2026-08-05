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
| C | Mentrix/Build vertical slice wire-up (opt-in remote) | **This PR** |
| D | Docker isolation + harden | Pending |

## Stage C files

- `backend/app/services/coding_engine/mentrix_bridge.py` — provision + engine poll → Mentrix events
- `backend/app/workers/mentrix_worker.py` — call bridge before ForgeLoop; dispose after
- `backend/app/domains/agent_run/mentrix.py` — expose `engine_provider` / `workspace_id` / `engine_run_id`
- `backend/app/domains/agent_run/build_phase.py` — stamp `coding_engine` on Build responses
- `backend/tests/test_coding_engine_stage_c.py`

## Behavior

- `ZECT_CODING_ENGINE=mock` (default): stamp `engine_provider=mock`; ForgeLoop unchanged
- `ZECT_CODING_ENGINE=remote` + workspace: worktree → remote start → poll events into MentrixRun → ForgeLoop on worktree → dispose with patch artifacts

## Verification

- Full `pytest` green
- Branding gate on public surfaces
- Stop for Stage D approval after merge
