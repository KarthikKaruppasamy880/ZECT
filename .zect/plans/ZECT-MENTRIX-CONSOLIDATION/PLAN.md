# PLAN.md â€” ZECT Mentrix Consolidation P0

**work_item_key:** ZECT-MENTRIX-CONSOLIDATION
**plan_version:** 1
**status:** ACCEPTABLE_WITH_KNOWN_PREEXISTING_TEST_INFRA_ISSUES
**scope:** P0 only
**note:** Not fully repository-green; TI-001/TI-002 deferred; P1 not started

## Objective

Close Mentrix consolidation P0: WorkItem + events, ArtifactStore PLAN ownership, ContextEngine provenance, ProjectIntelligence contract, MentrixDeveloperService, gateway unify, fail-closed native build, evidence/checkpoints/resume, telemetry/fallback, Coding Agent smoke, E2E READY_TO_SHIP.

## Locked decisions

1. ArtifactStore owns PLAN.md; MentrixRun.result_json["plan"] is dual-write only.
2. WorkItem requires repository_id, repository_ref, base_commit_sha; append-only WorkItemEvent; SDLC enums.
3. ContextPack full provenance; PI full contract; Knowledge â‰  Memory.
4. Manifest ops: requirement_ids, deps, mandatory, attempts, max_attempts, evidence_ids.
5. Rich checkpoints; resume with worktree + commits; typed evidence; telemetry with fallback_*.
6. Fallback policies `never|ask|automatic` (`never` must not send to cloud).
7. Real Coding Agent smoke (OP-023b); WorkItemSourceAdapter stubs; E2E OP-035.
8. No P1/P2/P3 implementations in this execution.

## Plan hash / reapproval rules

- `plan_hash` = SHA-256 of canonical PLAN.md bytes (UTF-8, normalized newlines).
- Approving a plan sets `approved_plan_hash = plan_hash` and status `PLAN_APPROVED`.
- Any material PLAN.md write that changes `plan_hash` while `approved_plan_hash` was set:
  - clears approval (`approved_plan_hash = null`),
  - bumps `plan_version`,
  - sets status `NEEDS_HUMAN_DECISION` (or returns to `PLANNED`),
  - requires reapproval before AGENT/EXECUTING.
- Cosmetic-only edits that do not change hash keep approval.

## Phase A (docs) â€” GATE before product code

All of `docs/architecture/ZECT_*.md` listed in the Cursor plan + this folder's REQUIREMENTS/PLAN/ACCEPTANCE/RISKS/EXECUTION_MANIFEST.

## Phase B â€” Mandatory ops (see EXECUTION_MANIFEST.json)

OP-001â€¦OP-009 docs â†’ OP-010/011/015 WorkItem â†’ OP-012/012b ArtifactStore â†’ OP-013/014 Context/PI â†’ OP-016 SourceAdapter â†’ OP-020/021/024 Developer â†’ OP-022/023/023b gateway/smoke â†’ OP-030â€¦034 evidence/telemetry â†’ OP-035 E2E â†’ OP-040/041 gate.

## Non-goals

P1 Jira/Camunda full adapters, Ultra Review redesign, sidebar P2, System Health, full Skills filesystem migrate, Playwright suite green.
