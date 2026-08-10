# Mentrix Long-Running Live Acceptance

**Date:** 2026-08-10  
**PR #131:** merged → `develop` @ `8f992fc`  
**Machine run id:** `lrr-9000ec22117142c4`  
**WorkItem:** `47` (User source, non-production)  
**Raw JSON:** `MENTRIX_LONG_RUNNING_LIVE_ACCEPTANCE.json`

## Verdict

**LIVE_VIABLE**

| Gate | Result |
|------|--------|
| PR #131 CI (backend/frontend/e2e) after Critical fixes | SUCCESS / MERGEABLE CLEAN → **merged** |
| Critical CodeRabbit (authz, atomic lease, fabricated evidence) | **fixed before merge** |
| Controlled disposable-repo endurance | **LIVE_VIABLE** |
| Jira ticket ingest for this run | **BLOCKED_EXTERNAL** (User WorkItem used by design) |
| Production PR / merge of generated code | **NOT DONE** (by design) |

## PR #131 validation summary

Against `develop` before merge:

- Local regression: long-running + engineering + automation loops **41 passed**; companion learning suite included in earlier **60 passed** batch
- Frontend `tsc -b`: clean
- CI on head `73b7a20`: backend / frontend / e2e / CodeRabbit **SUCCESS**
- Critical findings fixed: per-run ownership, atomic lease claim, no fabricated READY_TO_SHIP evidence, worker failure path, simulated≠completed

## Live endurance setup

| Item | Value |
|------|--------|
| Duration | **19.92 s** |
| Worktree | `.zect/live-endurance/run-1786389776` (disposable git repo) |
| Base SHA | `202b1e0d9f6230d6c45a3980bd6d39f17d4acd80` |
| Final SHA | `28ecb545ddbbca38b730fb8fce75e1c0394ccaec` |
| Coding engine | `mentrix_native` (OpenAI configured) |
| Model profile telemetry | `mentrix_native:QUALITY` (8/8 ops) |
| Autonomy | L2 assisted |
| Operations | **8 / 8 completed** |
| Files changed | `pkg/mod_001.py` … `pkg/mod_008.py` (8) |
| Production merge | **false** |

Spine exercised:

```text
MentrixPlanner → LongRunningAgentRuntime ticks (real worktree file+git commits)
  → pause/resume → recover_after_restart
  → MentrixTestAgent (real pytest) → MentrixReviewAgent
  → AcceptanceVerifier + EvidenceVerifier (ship=false, PR-ready evidence only)
```

## Pause / resume evidence

| Step | Evidence |
|------|----------|
| After OP-001..004 | `completed=4`, `resume=OP-005`, SHA `0a62391…` |
| Pause | `status=PAUSED` |
| Resume | `ok=true`, `resume_operation=OP-005` |
| After +2 ops | `completed=6`, `resume=OP-007` |

## Backend/worker restart evidence

`recover_after_restart()` cleared lease (`worker_id=""`, `lease_expires_at=null`) and preserved `resume_operation=OP-007` with `completed=6`. New worker `live-worker-2` finished OP-007..008 without redoing completed ops. Git log shows one commit per OP, no duplicates.

## Tests / review / acceptance

| Stage | Result |
|-------|--------|
| pytest (`tests` + `pkg`) | **pass** (`1 passed`, exit 0) — seed smoke; module self-checks present in generated files |
| Review Agent | **clean**, 0 blocking |
| AcceptanceVerifier | **ready_to_ship=true**, `shipped=false` (explicit no auto-ship) |
| Intermediate finalize before Test/Review | correctly **FAILED_VERIFICATION** (`test_or_review_not_clean`) — proves no fabricated pass |

## Budgets / telemetry

Budgets present on run (`max_runtime_seconds=300`, `max_tokens=50000`, `max_cost_usd=5`, `max_actions=200`, coder test/review cycles).  
Per-op telemetry persisted (8 entries) with `requested_model`, `actual_model`, `provider`, `latency_ms`, `work_item_id`, `operation_id`.  
Token/cost USD metering for OpenAI chat Planner call was not separately billed in this controlled file+git coding path; planner used Mentrix Planner offline/LLM path with configured OpenAI.

## PR status

**NOT_CREATED_BY_DESIGN** — disposable local commits only; no push/merge of generated code to production remotes.

## Blockers

| Item | Status |
|------|--------|
| Jira-backed WorkItem for this endurance | **BLOCKED_EXTERNAL** (User WorkItem + disposable repo used) |
| Auto production PR | intentionally skipped |
| Full LLM edit-loop per op (beyond mentrix_native-selected bounded worktree executor) | not claimed as separate product; ops applied as real git-committed file mutations under selected engine |

## Non-claims

Not production deployment; not unlimited autonomy; not zero hallucination; not a second Mentrix/ForgeLoop; not automatic merge of generated code.
