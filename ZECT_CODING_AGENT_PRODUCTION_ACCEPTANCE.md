# ZECT Coding Agent Production Acceptance

**Date:** 2026-08-17  
**Canonical develop at branch point:** `c37f24a86943ae1f9683a834f59d995a5423096d` (PR **#157** human-merged).  
**This PR branch:** `feat/coding-agent-production`  
**No auto-merge.** Present/Voice tranche is **not started**.

## Verdict

**READY_TO_MERGE_CODING_AGENT** only after human merge of this focused PR and CI green.  
This tranche does **not** make overall ZECT production-ready.

| Gate | Result | Evidence |
|------|--------|----------|
| Missions A–G (disposable git) | **PASS** (pytest) | `backend/tests/test_coding_agent_production.py` |
| PLAN before worktrees/edits | **PASS** | `start_mission` stays `awaiting_plan_approval` |
| Isolated worktree; main checkout unchanged | **PASS** | mission G asserts source `n.py` still `N = 1` |
| Sibling PASS+FAIL ⇒ BLOCKED | **PASS** | mission F; `approve_git` raises until repair |
| Cancel / resume / no duplicate commits | **PASS** | mission G SHA list unchanged on second git approval |
| Security defect + eval() fail-closed | **PASS** | missions D and E |
| Git commit/push always confirm | **PASS** | `git_commit` needs `_approved`; broker always-confirm |
| Live GitHub without token | **BLOCKED_EXTERNAL** (honest) | mission `test_github_push_blocked_external_without_token`; local READY_TO_MERGE still allowed |
| Headed UI | **PASS** | `frontend/e2e/coding-agent-production.spec.ts` — mission A PLAN/tests/cancel/resume/git; mission F sibling BLOCKED |
| Electron pane | **PASS** | `frontend/e2e/coding-agent-electron.spec.ts` (binary present) |
| Mentrix Ultra Review | **PASS** (0 critical) | `run_ultra_review` on production files: score 85, `gpt-4o-mini`; high KeyError on missing mission is mapped to HTTP 404. CodeRabbit **SKIPPED** ≠ PASS |
| Persistence across backend restart | **PARTIAL** | in-memory `_MISSIONS`; recovery is tranche E |
| Auto-merge | **never** | `no_auto_merge: true` |

## Lifecycle proved

`Requirement → PLAN → approval → isolated worktree/branch → edit → commands → tests → diagnose/repair → diff → security → Ultra Review → commit → push/PR (or BLOCKED_EXTERNAL) → READY_TO_MERGE`

Companion does **not** edit code. Chat tab remains the native tool loop; Mission tab is the production orchestrator. Deterministic patches still go through `execute_tool` (`write_file` / `apply_patch` / `run_command`).

## Honest limits (not PASS)

- Live GitHub push/PR without a valid token, or `MENTRIX_PR_DRY_RUN=1` → **BLOCKED_EXTERNAL**.
- CodeRabbit unavailable/manual → **SKIPPED**, never PASS.
- In-memory mission store does not survive backend restart (tranche E).
- LLM chat path is not a substitute for A–G proof; A–G use real disposable git + deterministic patches.
