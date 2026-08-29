# ACCEPTANCE.md — P0 Mentrix Consolidation

P0 is **COMPLETE** only when every criterion below is met. Otherwise status is **BLOCKED** with resume op.

## Phase A

- [x] All docs under `docs/architecture/` listed in the plan exist on disk
- [x] REQUIREMENTS.md, PLAN.md, ACCEPTANCE.md, RISKS.md exist
- [x] EXECUTION_MANIFEST.json bootstrapped with ops OP-001…OP-041 fields

## WorkItem

- [x] WorkItem has repository_id, repository_ref, base_commit_sha
- [x] SDLC status enums match ZECT_SDLC_ARCHITECTURE.md
- [x] WorkItemEvent append-only; status changes emit events
- [x] WorkItem API create/get/list/transition

## Artifacts / Context / PI

- [x] ArtifactStore owns PLAN.md path; dual-write MentrixRun documented/tested
- [x] Plan hash change requires reapproval
- [x] ContextPack includes full provenance fields
- [x] ProjectIntelligence snapshot has lattice, blueprint, knowledge, memory, related_work, skill_selection, playbook_selection, freshness
- [x] Knowledge and Memory are separate keys/stores

## Developer service

- [x] MentrixDeveloperService ask/plan/agent implemented
- [x] API routes registered
- [x] Companion tools route to service

## Gateway / Coding Agent

- [x] llm_phase uses openai_compat (no raw OpenAI-only ForgeLoop path for ask/plan)
- [x] Native coding engine fail-closed when mock/cloud silent fallback forbidden
- [x] OP-023b Coding Agent smoke test green
- [x] OP-034 fallback policy tests green (`never` does not send to cloud)

## Evidence / Resume / E2E

- [x] Checkpoints include worktree + commit fields
- [x] EvidenceVerifier accepts typed evidence only for READY_TO_SHIP
- [x] Resume restores from checkpoint
- [x] OP-035 integration: WorkItem → READY_TO_SHIP green
- [x] Telemetry includes fallback_used, fallback_reason, providers/models

## Gate

- [x] EXECUTION_MANIFEST all mandatory ops `completed` with evidence_ids
- [x] No silent mock/cloud fallback where fail-closed required
- [x] Unrelated files preserved
- [x] Mandatory suite: `backend/tests/fixes_and_phases/test_mentrix_p0_consolidation.py` — **18 passed**

**P0 status: ACCEPTABLE WITH KNOWN PRE-EXISTING TEST INFRASTRUCTURE ISSUES** (2026-08-09)

- Whitespace gate (`git diff --check`): PASS after EOF fix in `mentrix_native_build.py`
- Re-verify: P0 18 passed; spine/Fabric/Coding Agent group 35 passed; non-auth `fixes_and_phases` 580 passed
- Not fully repository-green: backlog **TI-001** (auth fixture vs dotenv override), **TI-002** (Vitest/Playwright overlap) — P1/test-infra, not started
- See `P0_POST_BUILD_AUDIT.md`
