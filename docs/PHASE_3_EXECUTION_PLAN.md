# Phase 3 Execution Plan — Cursor-like Developer Workspace

Companion to `Upgrade.md` Phase 3. Staged PRs to `develop`; stop after each merge.

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Unified `/workspace` shell: file tree + Monaco + git status/branch strip; path-scoped writes | **Done** (#89) |
| B | Embed workspace-scoped terminal (App Runner) + Mentrix timeline panel | **Done** (#90) |
| C | Diff + hunk apply/revert + agent change markers | **Done** (#91) |
| D | Inline Ask / explain / generate tests / fix selection + context selector | **Done** (#92) |
| E | Symbols/refs jump + worktree display | **This PR** |

## Stage E files

- `GET /api/git/worktrees` + `gitWorktrees` client
- `getFileSymbols` client + `WorkspaceSymbolsPanel` (search + file outline → jump)
- Monaco `revealLine` for go-to-line
- Worktree badge on git strip when multiple worktrees exist

## Phase 3 complete when Stage E merges

Next: Phase 4 (PR review platform). Phase 9 remains ON HOLD.
