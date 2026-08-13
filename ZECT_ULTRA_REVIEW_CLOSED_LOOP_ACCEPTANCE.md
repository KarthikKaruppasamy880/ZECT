# ZECT Ultra Review — Closed-Loop PR Engineering Acceptance

**Branch:** `feat/zect-ultra-review-closed-loop`  
**Date:** 2026-08-13  
**Spec:** `prompts/ZECT_ULTRA_REVIEW_CLOSED_LOOP_PR_ENGINEERING.md`  
**Prior merge:** Repo UX PR [#137](https://github.com/KarthikKaruppasamy880/ZECT/pull/137) MERGED (`530cd08`)  
**Disposable / this PR:** DO NOT auto-merge until human review

## Final status: **PASS** (unit + disposable Git fixture; live GitHub PR optional / PARTIAL)

---

## 1. Audit matrix (pre-implementation)

| Capability | Status before | Status after |
|---|---|---|
| Ultra Review engine | ALREADY_BUILT | reused |
| ForgeLoop | ALREADY_BUILT | reused (not duplicated) |
| 6-class finding routing | MISSING | **BUILT** |
| Structured closed-loop finding schema | PARTIAL | **EXTENDED** |
| Same-PR remediation orchestrator | PARTIAL | **BUILT** |
| Coding/Test/Planner route targets | PARTIAL | **WIRED** (routing map) |
| AcceptanceVerifier | ALREADY_BUILT | reused (optional hook) |
| EvidenceVerifier | ALREADY_BUILT | reused via AcceptanceVerifier |
| READY_TO_SHIP | ALREADY_BUILT | gated from findings |
| MERGE_ELIGIBLE | MISSING | **BUILT** |
| Loop safety max review cycles | PARTIAL | **BUILT** (`ZECT_UR_MAX_REVIEW_CYCLES`) |
| Security → hard block | PARTIAL | **BUILT** |
| Blind CodeRabbit compare | MISSING | **BUILT** (harness) |
| Closed-loop acceptance artifact | MISSING | **THIS FILE** |

## 2. Reused components

- `review_service` / `/api/ultrareview` history + `start-fix-run`
- `AcceptanceVerifier`, `EvidenceVerifier`, `ArtifactStore`
- Phase-4 `finding_schema.py` (extended conceptually; closed-loop schema lives alongside)
- Engineering agent role names as route targets (no new agents)

## 3. Implemented gaps

| Path | Role |
|---|---|
| `backend/app/services/ultra_review/finding_router.py` | Schema + `LOCAL_FIX`…`ARCHITECTURE_CHANGE` + gates |
| `backend/app/services/ultra_review/closed_loop.py` | Same-PR cycle orchestrator |
| `backend/app/services/ultra_review/coderabbit_benchmark.py` | Blind Mentrix-first compare |
| `backend/app/domains/agent_run/ultrareview.py` | `POST /closed-loop/run`, `/classify`, `/coderabbit-compare` |
| `backend/tests/fixes_and_phases/test_ultra_review_closed_loop.py` | Proofs |

## 4. Finding schema / routing

Fields: `finding_id`, `run_id`, `work_item_id`, `pr_id`, `repository_id`, `commit_sha`, `severity`, `category`, `file`, `line`, `claim`, `evidence`, `requirement_id`, `security_policy_id`, `plan_impact`, `architecture_impact`, `recommended_action`, `verification_status`, `created_at`, `resolved_at`.

Routes: `LOCAL_FIX | TEST_GAP | SECURITY | PLAN_REVISION | SCOPE_CHANGE | ARCHITECTURE_CHANGE`

## 5. Proofs (automated)

```text
pytest tests/fixes_and_phases/test_ultra_review_closed_loop.py
→ 12 passed
```

| Requirement | Evidence | Status |
|---|---|---|
| LOCAL_FIX → coder → resolve → READY_TO_SHIP | `test_local_fix_cycle_resolves_same_pr_dry_run` | PASS |
| TEST_GAP classify | `test_classify_test_gap` | PASS |
| SECURITY blocks ship/merge then fix clears | `test_security_cycle_forces_block_then_resolve` | PASS |
| PLAN_REVISION → planner / needs_plan | `test_plan_revision_needs_planner` | PASS |
| Same-PR head change on disposable git | `test_same_pr_real_git_fixture` (tmp_path only) | PASS |
| Re-review gates after resolve | same tests assert `MERGE_ELIGIBLE` / `READY_TO_SHIP` | PASS |
| AcceptanceVerifier hook | orchestrator optional when `work_item_id`+db | PARTIAL (wired; not forced in unit without WI fixture) |
| EvidenceVerifier | via AcceptanceVerifier | PARTIAL |
| Loop / circuit breaker | `test_max_review_cycles_circuit_breaker` | PASS |
| Human approval behavior | plan/security routes require planner/gate; no auto-merge | PASS |
| Blind CodeRabbit | `test_coderabbit_blind_protocol` | PASS |
| Auto-merge | always `auto_merge: false` | PASS |

## 6. Disposable Git fixture (not the real ZECT checkout)

`test_same_pr_real_git_fixture` creates a temp repo, seeds a secret finding, commits a fix on the same branch, asserts `new_head_sha != old_head_sha`, gates open, **no merge**.

## 7. Blind CodeRabbit comparison

Harness enforces Mentrix-first (`mentrix_ran_first`). Metrics only; claim text: *No superiority claim — metrics only*.

Live CodeRabbit API pull: **BLOCKED_EXTERNAL** unless configured separately.

## 8. Remaining PARTIAL / BLOCKED

| Item | Status |
|---|---|
| Full live GitHub disposable PR (create PR via network) | PARTIAL / BLOCKED_EXTERNAL without token |
| Developer UI closed-loop state machine panel | PARTIAL — API ready; UI not redesigned (per stop: no Developer redesign) |
| Wire every Ultra Review session automatically into EngineeringLoopRunner | PARTIAL — `/closed-loop/run` + existing `start-fix-run` coexist |
| Forced AcceptanceVerifier in every dry-run | PARTIAL — requires WorkItem artifacts |

## 9. Frozen regression

Repo UX onboarding suite previously green (22). Closed-loop suite **12 passed**. No Present/Voice/Learning/packaging changes in this branch.

## 10. Stop

STOP after this acceptance.  
**Do not auto-merge** this closed-loop PR.  
Do not replace CodeRabbit, redesign Developer, or start unrelated roadmap work.
