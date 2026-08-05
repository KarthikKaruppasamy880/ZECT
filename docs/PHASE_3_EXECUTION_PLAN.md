# Phase 3 Execution Plan — Cursor-like Developer Workspace

Companion to `Upgrade.md` Phase 3. Staged PRs to `develop`; stop after each merge.

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Unified `/workspace` shell: file tree + Monaco + git status/branch strip; path-scoped writes | **Done** (#89) |
| B | Embed workspace-scoped terminal (App Runner) + Mentrix timeline panel | **This PR** |
| C | Diff + hunk apply/revert + agent change markers | Pending |
| D | Inline Ask / explain / generate tests / fix selection + context selector | Pending |
| E | Symbols/refs jump + worktree display | Pending |

## Stage B files

- `frontend/src/components/WorkspaceTerminal.tsx` — App Runner execute/start/stop with `cwd` = workspace root
- `frontend/src/components/WorkspaceMentrixTimeline.tsx` — run list + `sequence_id` events (2s poll while running)
- `frontend/src/pages/DeveloperWorkspace.tsx` — bottom dual panel
- `docs/PHASE_3_EXECUTION_PLAN.md`, `docs/ROADMAP.md`

## Guardrails

- Editor saves only under the active workspace root (Stage A).
- Terminal always uses that same root as `cwd` (server allowlist remains authoritative).

## Stop

After Stage B merges, wait for approval before Stage C.
