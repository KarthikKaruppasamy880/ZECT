# Mentrix Automation Loops — Product Acceptance

**Date:** 2026-08-10
**Branch:** `feat/mentrix-companion-present-learning-hardening` (PR #130)
**Pattern reference:** cobusgreyling/loop-engineering (MIT) — concepts only; no competing runtime installed.

## Verdict

| Item | Status |
|------|--------|
| Thin MentrixAutomationLoop over existing spine | **VIABLE** |
| First five loops (L0/L1 default) | **VIABLE** |
| Budgets / checkpoint / kill-pause-resume | **VIABLE** |
| Circuit breaker → NEEDS_HUMAN_DECISION | **VIABLE** (unit) |
| L2/L3 require explicit policy | **VIABLE** |
| No second ForgeLoop / Memory / STATE.md store | **VIABLE** |
| Live connector-driven loop outcomes | **BLOCKED_EXTERNAL** without creds |

## Autonomy

| Level | Behavior | Default |
|-------|----------|---------|
| L0 Observe | Connector/matrix observation; no mutating recommendations required | Daily Brief default |
| L1 Recommend | Produce recommendations / PersonalAction upserts / claim review | PR/CI, Jira, Present, Follow-up defaults |
| L2 Assisted | Optional WorkItem creation under allow_l2 | Off unless configured |
| L3 Autonomous | READY_TO_PRESENT / auto follow-up only with allow_l3 | Off unless configured |

## First five loops

| Loop | Key | Target | Default | Cadence hook |
|------|-----|--------|---------|--------------|
| Daily Brief | `daily_brief` | PersonalAction | L0 | `automation_loop:daily_brief` Schedule |
| PR/CI Watch | `pr_ci_watch` | WorkItem | L1 | `automation_loop:pr_ci_watch` |
| Jira Triage | `jira_triage` | WorkItem + PI | L1 | `automation_loop:jira_triage` |
| Presentation Prep | `presentation_prep` | Present pipeline | L1 | manual / schedule |
| Personal Follow-up | `personal_followup` | PersonalAction | L1 | `automation_loop:personal_followup` |

Runtime path: Trigger/Schedule → WorkItem or PersonalAction → Context/Skill/Playbook (existing) → Mentrix connector/Coding Agent → EvidenceVerifier-shaped evidence → Policy/Human gate → LoopCheckpoint persist → next iteration.

## Security isolation

- LoopDefinition / LoopRun scoped by `user_id`
- PersonalAction list/patch/upsert/daily-brief open-actions filtered by authenticated user
- Learning progress/mentor project ownership enforced
- WorkItem skill recommend authorized by creator/admin
- Untrusted fence neutralization for connector text

## Budgets (defaults)

max_runtime_seconds, max_tokens, max_cost_usd, max_actions, max_retries, max_same_failure — stored on LoopDefinition.budget_json; actions_used enforced before run.

## Circuit breaker

Identical consecutive failures trip to `NEEDS_HUMAN_DECISION` after `max_same_failure` (default 3). Evidence: `test_circuit_breaker_trips_on_same_failure`.

## Evidence rules

- Every successful iteration appends typed evidence with artifacts (no LLM-only completion)
- Kill / pause / resume control plane on `/api/mentrix/automation-loops/{key}/…`

## Tests

- `test_automation_loops.py` — breaker, builtins, L2 policy, user-scoped PersonalActions, daily_brief L0 run, pause/resume/kill, sanitize fence
- Companion/Present/Learning + P0–P3 suites re-run on push

## Remaining blockers

- Live M365/Slack/Jira/GitHub loop observations: **BLOCKED_EXTERNAL**
- Presenton deck bytes for presentation_prep READY_TO_PRESENT: needs Presenton + L3 policy
- Docstring coverage CodeRabbit gate may still warn (non-blocking if CI jobs green)

## Non-claims

Not a second orchestrator; not fully autonomous by default; not hallucination-free; not fully local.
