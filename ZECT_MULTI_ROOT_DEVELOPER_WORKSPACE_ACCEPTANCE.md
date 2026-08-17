# ZECT Multi-Root Developer Workspace Acceptance

**Date:** 2026-08-17  
**Canonical develop:** `a0bada0` (PR #154).  
**Branch:** `feat/developer-multi-root-workspace`  
**No auto-merge.** This PR does **not** claim full multi-root completion. Graphify / S8C / next production tranche: **not started**.

## In this PR (rail slice only)

| Requirement | Status |
|-------------|--------|
| Authorized-roots rail listing project repos together | **PASS** — `WorkspaceRootsRail`; file tree still follows the **active** root |
| Per-root branch / dirty / remote / Lattice / authorized | **PARTIAL** — identity + Lattice on each row |
| Add local / clone / attach registered | **PASS** — reuses `RepoOnboardingPanel` (does not duplicate onboarding) |
| Remove from workspace, never delete disk | **PASS** — `zect_ws_roots` exclusion list only |
| Missing root → `ROOT_UNAVAILABLE` + Repair | **PASS** — `repo_git_identity` + Repair opens import on that root |

## Explicitly out of scope (remaining multi-root)

This PR does **not** complete:

1. Merged multi-root Explorer tree (`WORKSPACE / ZECT / ZOAS / other-authorized-root` with files under each root at once)
2. Per-root terminals (cwd locked to the selected authorized root; cannot escape)
3. Workspace-wide search / symbols with root labels and `project_id + workspace_id + repo_id + commit_sha + path`
4. Repo-scoped Git safety proof (independent branch/worktree/diff/commit/PR per root in the Explorer)
5. Multi-repo WorkItem / Coding Agent proof (identify both repos, isolated worktrees, sibling failure blocks aggregate READY)
6. Electron workspace restore of authorized roots after restart

Do not start that work until this PR is **human-merged**.

## Proof this PR

- Vitest: `workspaceRoots.test.ts`, `WorkspaceRootsRail.test.tsx`
- Pytest: `test_repo_onboarding_ux.py` including `ROOT_UNAVAILABLE`
- Hygiene: roots rail visible when explorer file tree is shown
- Headed 3-root: `frontend/e2e/workspace-multi-root.spec.ts` (not in `test:e2e:core`)

## Gate

**READY_TO_MERGE** for the rail slice only (human merge). Full multi-root IDE remains **PARTIAL**.
