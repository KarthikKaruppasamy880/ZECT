# Phase 3 Execution Plan — Cursor-like Developer Workspace

Companion to `Upgrade.md` Phase 3. Staged PRs to `develop`; stop after each merge.

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Unified `/workspace` shell: file tree + Monaco + git status/branch strip; path-scoped writes | **Done** (#89) |
| B | Embed workspace-scoped terminal (App Runner) + Mentrix timeline panel | **Done** (#90) |
| C | Diff + hunk apply/revert + agent change markers | **This PR** |
| D | Inline Ask / explain / generate tests / fix selection + context selector | Pending |
| E | Symbols/refs jump + worktree display | Pending |

## Stage C files

- `frontend/src/lib/diffHunks.ts` (+ tests) — parse/apply/revert unified hunks client-side
- `frontend/src/components/WorkspaceDiffPanel.tsx` — DiffViewer + hunk checkboxes + Apply/Revert
- `frontend/src/pages/DeveloperWorkspace.tsx` — Diff toggle, tree markers (agent/git)
- `frontend/src/lib/api.ts` — `diffCompare`, `gitRestore`
- `backend/app/domains/repository/git_ops.py` — `POST /api/git/restore`
- `docs/PHASE_3_EXECUTION_PLAN.md`, `docs/ROADMAP.md`

## Guardrails

- Editor saves / restore targets only under the active workspace root.
- Terminal cwd remains the workspace root (Stage B).
- Hunk apply/revert mutates the editor buffer only until Apply & Save / `fileWrite`.

## Stop

After Stage C merges, wait for approval before Stage D.
