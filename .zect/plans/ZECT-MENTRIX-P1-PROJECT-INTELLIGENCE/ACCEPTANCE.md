# ACCEPTANCE.md — Mentrix P1

P1 is **COMPLETE** only when all below pass. Otherwise **BLOCKED** with resume op.

## Test infrastructure

- [x] TI-001: `ZECT_PYTEST=1` preserves auth/DB env across `load_dotenv(override=True)` (`main.py` + `conftest.py`)
- [x] TI-002: `npm test` / Vitest excludes Playwright `e2e/**` (57 unit tests pass, 0 e2e collected)

## Ingest + binding

- [x] Jira adapter creates/updates WorkItem with external_id + project/repo fields
- [x] Camunda adapter creates/updates WorkItem from process task
- [x] Missing repository identity → NEEDS_HUMAN_DECISION (not silent default)

## Project Intelligence

- [x] Snapshot includes Lattice, Blueprint, Knowledge, Memory, related_work, skill_selection, playbook_selection, freshness keys
- [x] Knowledge and Memory remain separate keys/stores
- [x] ContextEngine fed by live PI via MentrixDeveloperService

## Spine connectivity

- [x] Ask/Plan/Agent via MentrixDeveloperService use live PI (no parallel context system)
- [x] Fabric handoff from approved WorkItem/PLAN (`fabric_handoff.py` + `/fabric-handoff`)
- [x] ForgeLoop mentrix_native ownership asserted (`ownership.py`)
- [x] Ultra Review consumes WorkItem/ContextPack evidence (`ultra_review_context.py` + GET `/api/ultrareview/work-item/{id}/context`)
- [x] EvidenceVerifier → READY_TO_SHIP → close_loop dry_run (Jira/Camunda/PR)

## Tests / docs

- [x] Connectivity suite: `test_mentrix_p1_project_intelligence.py` (12 passed) + P0 (18 passed)
- [x] `docs/architecture/ZECT_GAP_ANALYSIS.md` P1 rows updated
- [x] EXECUTION_MANIFEST all mandatory ops completed
- [x] No duplicate DeveloperService / ContextEngine / Coding Agent introduced

## Explicit non-DoD

- Full Playwright suite green (unless expanded later)
- Sidebar redesign / System Health
- Skills filesystem migrate to `.zect/skills`
