# Mentrix Long-Running Engineering Runtime — Acceptance

**Date:** 2026-08-10  
**Branch:** `feat/mentrix-long-running-engineering-runtime`  
**Baseline:** `develop` @ `2976dfd` (merged PR #130)  
**Spec:** `prompts/ZECT_MENTRIX_LONG_RUNNING_ENGINEERING_RUNTIME_PROMPT.md`

## Verdict

| Gate | Status |
|------|--------|
| PR #130 merge (CI backend/frontend/e2e/CodeRabbit SUCCESS, MERGEABLE CLEAN) | **DONE** |
| Durable LongRunningAgentRuntime on existing spine (no parallel engines) | **VIABLE** |
| Pause / resume | **VIABLE** (unit) |
| Backend restart recovery | **VIABLE** (unit) |
| Worker lease prevents double execution | **VIABLE** (unit) |
| 100+ operation WorkItem → READY_TO_SHIP with evidence | **VIABLE** (unit) |
| 99/100 rejects completion | **VIABLE** (unit) |
| Live Jira→workspace coding hours-long run | **BLOCKED_EXTERNAL** without connectors/LLM |

**Overall:** **VIABLE** for durable long-running engineering execution semantics. Live multi-hour coding against real repos remains environment-gated.

## Merged baseline

- Merged https://github.com/KarthikKaruppasamy880/ZECT/pull/130 into `develop` (`2976dfd`)
- Remote HEAD at merge: companion + Present + Learning + MentrixAutomationLoop (five personal loops) @ `2d2fbef`
- New feature branch created from updated `develop` (not continued on #130 branch)
- Engineering agents + long-running runtime landed on this branch

## Runtime architecture

```text
Mentrix
  → MentrixAutomationLoop (triggers/budgets)
  → LongRunningAgentRuntime (durable op lifecycle / lease / restart)
  → WorkItem + ArtifactStore + ContextEngine + ProjectIntelligence
  → ForgeLoop / mentrix_native Coding Agent
  → Test Agent / Review Agent
  → AcceptanceVerifier + EvidenceVerifier
  → Permission Broker + Model Gateway
```

Job state lives in ZECT (`mentrix_long_running_runs` + ArtifactStore), not in one HTTP/LLM context.

## Role boundaries

Unchanged from engineering-agents acceptance: only AcceptanceVerifier+EvidenceVerifier may READY_TO_SHIP. Planner/Coder/Tester/Reviewer cannot.

## Durable run model

`LongRunningAgentRun` fields: `run_id`, `work_item_id`, `loop_run_id`, worktree/SHAs, `current_operation_id`, budgets, telemetry, `worker_id`, lease timestamps, heartbeat, status.

Statuses (truthful only): RUNNING | PAUSED | BLOCKED | NEEDS_HUMAN_DECISION | FAILED_VERIFICATION | CANCELLED | READY_TO_SHIP.

## Worker / lease

- `claim(worker_id)` — single active executor; expired lease reclaimable
- `heartbeat` extends lease
- `recover_after_restart()` clears leases, preserves resume_operation
- Background: `run_long_running_batch_in_background` (own DB session, like mentrix_worker)

## API

`/api/mentrix/long-running/start|/{id}|pause|resume|cancel|tick|/recover`

UI: `LongRunningRunPanel` on Work Items (ops progress, model, pause/resume/cancel/tick).

## Loop definitions

Engineering loops remain on MentrixAutomationLoop: `engineering_delivery`, `bug_fix`, `jira_delivery`, `ci_fix`, `pr_review_fix` (L1 default).

## Budgets / circuit breaker / model policy

Token, cost, runtime, actions enforced. Circuit breaker on identical failure signatures. Model profiles FAST|QUALITY|MAX|LOCAL|RESTRICTED|CUSTOM; RESTRICTED denies cloud switch; per-op telemetry persisted.

## Executable evidence

```text
cd backend
python -m pytest tests/fixes_and_phases/test_long_running_runtime.py \
  tests/fixes_and_phases/test_engineering_agents.py -q
# 34 passed (2026-08-10)
```

### Mandatory proofs (prompt §22 / §25)

| Requirement | Test |
|-------------|------|
| Pause/resume | `test_pause_resume` |
| Backend restart recovery | `test_backend_restart_recovery` |
| Worker lease safety | `test_worker_lease_prevents_double_execution` |
| Stale worktree | `test_stale_worktree_detected` |
| 100+ ops → READY_TO_SHIP | `test_hundred_plus_ops_ready_to_ship` |
| 99/100 blocks | `test_99_of_100_blocks_completion` |
| Token/cost/runtime budgets | `test_token_cost_runtime_budgets` |
| Model switch policy + telemetry | `test_model_switch_logged_and_policy` |
| L3 permissions + restricted model | `test_l3_permission_and_restricted_model` |
| Circuit breaker | `test_circuit_breaker_on_repeated_failure` |
| Idempotent resume | `test_idempotent_op_completion_on_resume` |
| PR/CI cannot bypass EvidenceVerifier | `test_pr_ci_cannot_bypass_evidence` |
| Planner/Coder/Tester/Reviewer gates | `test_engineering_agents.py` (20 behaviors) |

## Remaining blockers

- Live connector-driven Jira delivery: **BLOCKED_EXTERNAL**
- Real mentrix_native multi-hour coding requires configured LLM + worktree
- Full Playwright e2e for long-running UI not claimed here

## Non-claims

Not perfect codegen; not zero hallucination; not unlimited autonomy; not fully local unless configured; not a second Mentrix/ForgeLoop/WorkItem system.
