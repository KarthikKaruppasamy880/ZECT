# ZECT Work Management Production Acceptance

**Date:** 2026-08-18  
**Canonical develop:** `51150db` (PR **#159** Present + Voice, human-merged)  
**This PR:** `feat/work-intelligence-production`  
**Stop label:** `READY_TO_MERGE_WORK_INTELLIGENCE`  
**Graphify:** not started (out of scope)

## Verdict: **PARTIAL**

WorkItem / Process / Lattice production proof is in this PR. Live Jira/Camunda and live GitHub PR remain honest external gates. This tranche does **not** make overall ZECT production-ready.

| Area | Result | Evidence |
|------|--------|----------|
| Projects fixture isolation | **PASS** | Provenance=test hidden from default list; keep-cleanup empty `keep_ids` → 400; legitimate project remains. Headed e2e + `test_work_intelligence_production.py`. |
| WorkItems Project → ASK/PLAN/AGENT | **PASS** (lifecycle APIs) | HTTP ASK/PLAN; AGENT deterministic isolated worktrees; HTTP `READY_TO_SHIP`/`DONE` without EvidenceVerifier → **403**. UI detail: source, project, repos, status, plan, agent, evidence, aggregate. |
| EvidenceVerifier | **PASS** | LLM-only / empty evidence cannot READY_TO_SHIP; typed TEST_RESULT can. Agent does not auto-merge (`local_branch_only`, no `pr_url`). |
| Processes sample + ingest fixture | **PASS** | Sample `source=camunda`, `external_id=SAMPLE-ORDER-VALIDATION`, untrusted tag, idempotent reuse. Jira/Camunda ingest with raw preserves source + external_id. |
| Live Jira / Camunda | **BLOCKED_EXTERNAL** | Pytest: unset connectors → `jira_status`/`camunda_status` = `BLOCKED_EXTERNAL`; live ingest without raw → HTTP **503**. Headed Processes chips may stay `unknown` if the live DB pool is saturated — that is not a live PASS. Never fake ticket/process completion. |
| Lattice per-root | **PASS** (no Graphify) | Distinct `owner-repo` keys; live vs indexed SHA; STALE on commit-move; re-index does not leak sibling SHA. Developer rail + header chip. |
| Headed browser | **PASS** (this spec) | `frontend/e2e/work-intelligence-production.spec.ts` in `test:e2e:core` (16.7s local). |
| Electron | **PASS** (this machine) | `frontend/e2e/work-intelligence-electron.spec.ts` — skip if `electron.exe` missing (skip ≠ core PASS). |
| CodeRabbit | **SKIPPED** | Unavailable ≠ PASS. |
| Mentrix Ultra Review | recorded | `backend/scripts/work_intelligence_ultra_review.py`: passed, 0 critical, score 85, 1 non-critical finding. CodeRabbit **SKIPPED**. |

## Honest limits

- In-memory coding-agent missions remain tranche E.
- Live GitHub push/PR without token = `BLOCKED_EXTERNAL`.
- Semantic cross-repo Lattice merge / Graphify = out of scope.
- Full-product security campaign = tranche D.

## UI

Work Items list is unchanged. Selected item now has `WorkItemDetailPanel` (source/project/repos/status/plan/agent/evidence + `DeveloperMultiRepoStatus` aggregate) plus existing `LongRunningRunPanel`. Processes shows Jira/Camunda connector chips; live ingest is not clicked when blocked.
