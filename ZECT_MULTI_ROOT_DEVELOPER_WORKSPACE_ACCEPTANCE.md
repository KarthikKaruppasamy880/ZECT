# ZECT Multi-Root Developer Workspace Acceptance

**Date:** 2026-08-17  
**Canonical develop after #155:** `6fa05d8d9ec8a400464b4510fd4d94c18021cf5f`  
**Branch:** `feat/developer-multi-root-ide`  
**No auto-merge.** Graphify / S8C / Companion closure: **not started**.

## Proof this session

| Gate | Result |
|------|--------|
| Backend isolation / search / runner | **PASS** — `test_workspace_multi_root_ide.py` + onboarding/sandbox/allowed_paths/multi_repo_developer **55 passed** |
| Frontend unit | **PASS** — rail nested trees, session persist (no secrets), chrome |
| `npx tsc -b` | **PASS** |
| Headed hygiene | **PASS** — `e2e/core-ux-hygiene.spec.ts` |
| Headed 3-root workspace | **PASS** — `e2e/workspace-multi-root.spec.ts` (merged files, duplicate README, terminal cwd lock, search `other-content`, viewports 1280/1366/1440/1920, remove B keeps disk) |
| Electron restore ≥3 roots | **PASS** — `e2e/workspace-electron-restore.spec.ts` (local Electron binary; not in `test:e2e:core`) |
| Mentrix Ultra Review | **PASS** (diff review this SHA) — no valid branch-introduced Critical/Major left open |
| CodeRabbit | **SKIPPED** until PR (never PASS) |

## Requirements

| Requirement | Status |
|-------------|--------|
| Merged Explorer (`WORKSPACE` → all authorized roots + files) | **PASS** — files from every ready root visible together; duplicate names tagged `workspace-file-{repoId}-{name}` |
| Per-root terminals | **PASS** — session cwd locked; new terminal picks a root; Explorer switch does not retarget |
| Workspace search | **PASS** — scopes file / active root / workspace; hits carry `project_id + workspace_id + repo_id + commit_sha + path`; Bearer required |
| Symbols | **PARTIAL** — indexed search tagged per repo + commit SHA when identity is available; **semantic cross-repo references are not merged** |
| Repo-scoped Git safety | **PASS** — add/commit/restore pathspecs cannot escape the bound repo; `--force` rejected; sibling HEAD unchanged on status/checkout |
| Persistence | **PASS** — `zect_ws_roots` + `zect_ws_session` (editors/terminals/work item/project/repo); never secrets |
| Electron restore | **PASS** (this machine) — three roots visible after close/relaunch with dedicated `--user-data-dir` |
| Per-root Lattice | **PASS** — Explorer row shows canonical state, live vs indexed SHA, Index/Re-index/View; header chip + Context Used stay repo-scoped |
| Multi-repo WorkItem sibling failure | **PASS** (prior + re-run) — `test_multi_repo_developer.py`; aggregate not READY if B fails |
| IDE chrome | **PASS** — Terminal / Problems / Tests / Timeline / Evidence / Context / Search; Multi-Repo compact in Tests/Evidence |
| Security | **PASS** — runner `bound_root` + `..` reject; git sibling jail; catalog fetch no longer wipes repos on transient failure; remove ≠ disk delete |

## Mentrix Ultra Review (this diff)

| ID | Severity | Classification | Notes |
|----|----------|----------------|-------|
| Search unauthenticated | Critical | **ALREADY_FIXED** | `POST /api/workspace/search` now `Depends(get_current_user)` + global AuthMiddleware |
| Git pathspec sibling escape | Critical | **ALREADY_FIXED** | `relpaths_inside_repo` on add/commit/restore |
| Runner cwd outside bound root | Critical | **ALREADY_FIXED** | `bound_root` + resolve jail |
| Catalog wipe on 401 | Major | **ALREADY_FIXED** | `ActiveProjectContext` only replaces projects/repos after a successful list |
| Nested Index button in root select | Major | **ALREADY_FIXED** | actions sit beside Repair, not inside the select control |
| `".." in command` substring | Minor | **ACCEPTED** | false positives possible; fail-closed for bound terminals |
| Semantic cross-repo refs | — | **OUT_OF_SCOPE** | honest limitation flag `semantic_cross_repo_references: false` |
| Identity 200 vs `repo_not_found` | — | **OUT_OF_SCOPE** | `ROOT_UNAVAILABLE` 200 is intentional |

## Explicit limitations

- Semantic cross-repository “go to definition” across roots is **not** implemented.
- Electron restore spec is **not** in `test:e2e:core` (CI does not pack Electron). Proven locally when `electron/node_modules/electron/dist/electron.exe` exists.
- Live GitHub push/PR for the multi-repo WorkItem path remains `BLOCKED_EXTERNAL` when tokens/network are absent (unit/headed fixtures still fail-closed).
- This tranche does **not** make overall ZECT production-grade.

## Screenshots / traces

- Headed: `frontend/test-results/workspace-multi-root/01-three-roots.png`, `02-removed-zoas-disk-kept.png`
- Electron: `test-results/workspace-electron-restore/01-before-restart.png`, `02-after-restart.png`

## Gate

Human-merge this PR. Do not start Companion or later tranches in the same run.
