# ZECT Multi-repo R3.5 Acceptance

**Branch:** `feat/r3.5-multi-repo-agent-delivery`  
**Date:** 2026-08-13  
**Spec:** Next roadmap §R3.5 (full multi-repo AGENT delivery)  
**Base:** develop @ `baa75ed` (merge of PR 147)

## Verdict

**PARTIAL** — isolated per-repo AGENT worktrees, per-repo coder/tests/review/PR records, and aggregate READY_TO_SHIP gates are implemented and proven (pytest + headed e2e). Live GitHub PR create is **not** claimed PASS (`pr_status: local_branch_only`; no GitHub remote/token on disposable fixtures).

Do not start R5. PRs are never auto-merged.

## Capability matrix

| Capability | Result | Notes |
|---|---|---|
| Isolated worktree per authorized repo | PASS | Sibling `{clone}-worktrees/wi-{id}`; main checkout + dirty files unchanged |
| Coder + tests per worktree | PASS | Deterministic marker smoke, or pytest when `tests/test_*.py` exists |
| Aggregate TEST_RESULTS | PASS | `{ ok, by_repository }`; sibling failure is not hidden |
| Frontend BLOCKED + others PASS → NOT READY | PASS (pytest) | Missing `local_path` → `blocked` |
| Ultra Review per repo | PARTIAL | Uses `run_ultra_review` when available; never fabricates CLEAN if tests failed |
| PR per repo | PARTIAL | `PULL_REQUESTS.json`; GitHub create attempted only with token+github origin; else `local_branch_only` (no fake URL) |
| Auto-merge | PASS (not done) | Never merges |
| AcceptanceVerifier pending/blocked/failed/stale | PASS | Mandatory repo status must be pass/passed/completed/verified/ready_to_ship |
| EvidenceVerifier stale HEAD | PASS | Recorded `head_sha` ≠ live worktree/PR HEAD refuses READY_TO_SHIP |
| READY_TO_SHIP authority | PASS | Only AcceptanceVerifier + EvidenceVerifier (`allow_gate`) |
| Developer UI | PASS (headed e2e) | `developer-multi-repo-status`, `developer-repo-row-{id}` |
| Headed e2e (2 repos, one failing) | PASS | Two worktrees; repo-a smoke pass; repo-b pytest fail; aggregate NOT READY |
| Live GitHub PR | NOT PROVEN | `local_branch_only` — do not claim GitHub PR PASS |

## Proofs

```text
pytest backend/tests/fixes_and_phases/test_multi_repo_developer.py --noconftest -q
# 10 passed

npx playwright test e2e/multi-repo-agent.spec.ts --headed
# 2 passed (auth setup + R3.5 agent)
```

Evidence: `test-results/multi-repo-r35/evidence.json` (headed e2e, 2026-08-13)

## Honest blockers

1. **GitHub PR create** remains `local_branch_only` without `GITHUB_TOKEN` and a `github.com` origin. This run does not claim GitHub PR PASS.
2. Non-deterministic Mentrix native coder (LLM) is not the R3.5 proof path; tests use `deterministic=True` / `ZECT_CODING_AGENT_DETERMINISTIC_SMOKE`.
3. Headed e2e requires API on `http://127.0.0.1:8000` and login from `backend/.env` (`ZECT_USERNAME` / `ZECT_PASSWORD`), not the docs default.
4. `require_authentication` now resolves PEP 563 annotations on the original handler so uvicorn can boot (PlanRequest / PersonalActionCreate). Needed for live e2e; not a GitHub PR implementation.

## Stop

R3.5 delivery on this branch. Do not merge from the agent. Do not start R5.
