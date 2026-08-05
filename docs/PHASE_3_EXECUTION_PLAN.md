# Phase 3 Execution Plan — Cursor-like Developer Workspace

Companion to `Upgrade.md` Phase 3. Staged PRs to `develop`; stop after each merge.

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Unified `/workspace` shell: file tree + Monaco + git status/branch strip; path-scoped writes | **This PR** |
| B | Embed workspace-scoped terminal (App Runner) + Mentrix timeline panel | Pending |
| C | Diff + hunk apply/revert + agent change markers | Pending |
| D | Inline Ask / explain / generate tests / fix selection + context selector | Pending |
| E | Symbols/refs jump + worktree display | Pending |

## Stage A files

- `frontend/src/pages/DeveloperWorkspace.tsx`
- `frontend/src/components/MonacoCodeEditor.tsx`
- `frontend/src/lib/workspacePaths.ts` — path containment for writes
- Route `/workspace` + Sidebar entry
- `docs/PHASE_3_EXECUTION_PLAN.md`, `docs/ROADMAP.md`

## Guardrail

Editor saves only via `/api/files/write` and only when the target path is under the active Mentrix/ActiveProject workspace root (client-side check; server allowlist remains authoritative).

## Stop

After Stage A merges, wait for approval before Stage B.
