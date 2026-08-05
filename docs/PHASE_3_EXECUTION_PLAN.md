# Phase 3 Execution Plan — Cursor-like Developer Workspace

Companion to `Upgrade.md` Phase 3. Staged PRs to `develop`; stop after each merge.

## Stages

| Stage | Scope | Status |
|---|---|---|
| A | Unified `/workspace` shell: file tree + Monaco + git status/branch strip; path-scoped writes | **Done** (#89) |
| B | Embed workspace-scoped terminal (App Runner) + Mentrix timeline panel | **Done** (#90) |
| C | Diff + hunk apply/revert + agent change markers | **Done** (#91) |
| D | Inline Ask / explain / generate tests / fix selection + context selector | **This PR** |
| E | Symbols/refs jump + worktree display | Pending |

## Stage D files

- `frontend/src/components/MonacoCodeEditor.tsx` — selection change callbacks
- `frontend/src/components/WorkspaceInlinePanel.tsx` — context chips + Ask/Explain/Tests/Fix + apply
- `frontend/src/pages/DeveloperWorkspace.tsx` — Ask panel toggle wiring
- Reuses `askQuestion`, `buildGenerate`, `reviewAnalyze` / `reviewFixPrompt` (no new backend)

## Guardrails

- Inline actions only operate on the open workspace file buffer; Apply & Save still path-scoped.
- Context chips: Selection / File / Repo (`repo_id` when Active Project set).

## Stop

After Stage D merges, wait for approval before Stage E.
