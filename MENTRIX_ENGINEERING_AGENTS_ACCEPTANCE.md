# Mentrix Engineering Agents — Product Acceptance

**Date:** 2026-08-10  
**Branch:** `feat/mentrix-companion-present-learning-hardening` (PR #130)  
**Spec:** `prompts/MENTRIX_ENGINEERING_AGENTS_AUTOMATION_LOOPS_PROMPT.md`

## Verdict

| Item | Status |
|------|--------|
| Planner / Test / Review / Acceptance as **internal** Mentrix roles | **VIABLE** |
| Engineering loops on existing `MentrixAutomationLoop` (no second engine) | **VIABLE** |
| Reuse WorkItem, ArtifactStore, EvidenceVerifier, Coding Agent, Ultra Review schema | **VIABLE** |
| Role boundaries (no READY_TO_SHIP except Acceptance+Evidence) | **VIABLE** (unit) |
| Budgets / circuit breaker / no-progress / checkpoint resume | **VIABLE** (unit) |
| L3 still obeys high-risk + data-classification policy | **VIABLE** (unit) |
| Live Jira → PR ship with real workspace edits | **BLOCKED_EXTERNAL** without live connectors / coding LLM |

**Overall:** **VIABLE** for the engineering-agent spine on Automation Loops; live end-to-end delivery remains gated by connectors and model/workspace policy.

## Canonical architecture (reuse only)

```text
Mentrix (user-facing)
  → MentrixAutomationLoop (triggers / budgets / checkpoint / gate)
    → WorkItem + ArtifactStore + ContextEngine + ProjectIntelligence
      → MentrixPlanner → PLAN.md / REQUIREMENTS / ACCEPTANCE / RISKS / MANIFEST
      → MentrixCodingAgentRole → mentrix_native (MentrixDeveloperService)
      → MentrixTestAgent → TEST_RESULTS.json
      → MentrixReviewAgent (Ultra Review finding schema) → REVIEW.json
      → AcceptanceVerifier → EvidenceVerifier → READY_TO_SHIP (allow_gate)
```

No second ForgeLoop, WorkItem system, ContextEngine, memory store, model gateway, or Coding Agent.

## Role boundaries

| Role | Writes | READY_TO_SHIP |
|------|--------|---------------|
| Planner | ArtifactStore planning artifacts only | **Denied** |
| Coding Agent | Approved manifest ops via `mentrix_native` | **Denied** |
| Test Agent | `TEST_RESULTS.json` | **Denied** |
| Review Agent | `REVIEW.json` | **Denied** |
| AcceptanceVerifier | Evidence + status gate | **Only** with EvidenceVerifier + `allow_gate=True` |

## Loop definitions (L1 default)

| Key | Purpose |
|-----|---------|
| `engineering_delivery` | Full Planner→approve→Coder↔Test↔Review→Acceptance |
| `bug_fix` | Defect WorkItem delivery spine |
| `jira_delivery` | Jira-oriented engineering spine |
| `ci_fix` | CI failure → fix spine |
| `pr_review_fix` | Verified review blockers → coder |

Registered in `BUILTIN_LOOPS` alongside the first five personal loops (10 total). Dispatched by `MentrixAutomationLoop._phase_engineering` → `EngineeringLoopRunner`.

## Autonomy

| Level | Engineering behavior |
|-------|----------------------|
| L0 | Observe only |
| L1 (default) | Plan; await approval / human ship gate |
| L2 | Assisted dry-run spine (policy `allow_l2`) |
| L3 | May ship only when policy `allow_l3` and Acceptance+Evidence pass; **never** bypasses DENY/CONFIRM high-risk |

## Model routing

Planner uses existing Model Gateway / `resolve_model_route` telemetry (requested/actual/provider/fallback/latency). Coding Agent uses `selected_coding_engine()` / `get_mentrix_native_runtime()`. Test Agent prefers deterministic tools (`inject_result` in unit tests). Acceptance/Evidence are deterministic rules.

## Budgets & circuit breaker

`LoopBudget` fields: `max_runtime_seconds`, `max_tokens`, `max_cost_usd`, `max_actions`, `max_retries`, `max_files_changed`, `max_coder_test_cycles`, `max_coder_review_cycles`, `max_same_failure`, `no_progress_threshold`.

Identical failures → `CircuitBreaker` → `NEEDS_HUMAN_DECISION`. No-progress signature → escalation. Checkpoint/resume via `EXECUTION_STATE.json` + `record_checkpoint`.

## Permission / security

`evaluate_high_risk_action`: `git_push` / `pr_merge` / `deployment` / `external_message` → CONFIRM; `secret_access` / `destructive_filesystem` / confidential exfil → DENY. L3 sets `l3_bypasses_permissions: false`.

## Executable evidence

```text
cd backend
python -m pytest tests/fixes_and_phases/test_engineering_agents.py tests/fixes_and_phases/test_automation_loops.py -q
# 29 passed (2026-08-10)
```

### Required tests (prompt §16)

| # | Behavior | Test |
|---|----------|------|
| 1 | Planner cannot edit production code | `test_01_planner_cannot_edit_production_code` |
| 2 | Planner cannot READY_TO_SHIP | `test_02_planner_cannot_ready_to_ship` |
| 3 | Coder cannot READY_TO_SHIP | `test_03_coder_cannot_ready_to_ship` |
| 4 | Coder only approved manifest ops | `test_04_coder_only_approved_manifest_ops` |
| 5 | Test failure routes to Coder | `test_05_test_failure_routes_back_to_coder` |
| 6 | Verified blocking review → Coder | `test_06_verified_blocking_review_routes_to_coder` |
| 7 | Unverified review does not edit | `test_07_unverified_review_does_not_route_edits` |
| 8 | Incomplete requirement blocked | `test_08_incomplete_requirement_blocks_acceptance` |
| 9 | Incomplete acceptance blocked | `test_09_incomplete_acceptance_blocks` |
| 10 | 100 ops cannot finish at 99/100 | `test_10_hundred_ops_cannot_finish_at_99` |
| 11 | Circuit breaker | `test_11_circuit_breaker_on_repeated_failures` |
| 12 | No-progress escalation | `test_12_no_progress_escalates` |
| 13 | Resume from checkpoint | `test_13_resume_from_checkpoint` |
| 14 | L3 obeys permissions | `test_14_l3_obeys_permissions` |
| 15 | L3 obeys data classification | `test_15_l3_obeys_data_classification` |
| 16 | Token/cost budgets | `test_16_budgets_enforced` |
| 17 | Native coding path | `test_17_coding_agent_native_path` |
| 18 | Full flow + evidence | `test_18_full_flow_ready_to_ship_with_evidence` |
| 19 | Failed tests block ship | `test_19_failed_tests_prevent_ready_to_ship` |
| 20 | Blocking review blocks ship | `test_20_blocking_review_prevents_ready_to_ship` |

API smoke: `test_engineering_delivery_via_automation_loop` → `POST /api/mentrix/automation-loops/run` with `engineering_delivery`.

## Key implementation paths

- `backend/app/services/mentrix/engineering_agents/` — roles, planner, test, review, acceptance, policy, engineering_loop
- `backend/app/services/mentrix/automation_loops/definitions.py` — five engineering loop defs
- `backend/app/services/mentrix/automation_loops/runtime.py` — `_phase_engineering`
- `backend/app/services/work_items/artifact_store.py` — `TEST_RESULTS.json`, `REVIEW.json`
- `backend/tests/fixes_and_phases/test_engineering_agents.py`

## External blockers

- Live Jira/GitHub/CI connector outcomes: **BLOCKED_EXTERNAL**
- Live workspace coding without `ZECT_CODING_AGENT_DETERMINISTIC_SMOKE` / configured LLM: environment-dependent
- L2/L3 engineering autonomy requires explicit LoopPolicy `allow_l2` / `allow_l3`

## Remaining gaps

- Richer Planner mapping of multi-requirement Jira issues into multi-op manifests (current default OP-1 scaffold)
- Test Agent suite selection vs full CI matrix is bounded; production should pass explicit `pytest_args`
- PR creation / Camunda update after READY_TO_SHIP still uses existing Mentrix/Git paths (not reimplemented here)

## Non-claims

Not perfect codegen; not zero hallucinations; not unrestricted autonomy; not fully local unless runtime configured; not a second product surface for Planner/Coder/Tester/Reviewer.
