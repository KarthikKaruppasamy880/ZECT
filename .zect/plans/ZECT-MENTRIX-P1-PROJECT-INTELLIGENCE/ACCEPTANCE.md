# ACCEPTANCE.md â€” Mentrix P1

P1 is **COMPLETE** only when all below pass. Otherwise **BLOCKED** with resume op.

## Test infrastructure

- [ ] TI-001: authed HTTP tests (`auth_token`) pass with local `.env` present
- [ ] TI-002: `npm test` / Vitest does not collect Playwright `e2e/**`

## Ingest + binding

- [ ] Jira adapter creates/updates WorkItem with external_id + project/repo fields
- [ ] Camunda adapter creates/updates WorkItem from process task
- [ ] Missing repository identity â†’ NEEDS_HUMAN_DECISION (not silent default)

## Project Intelligence

- [ ] Snapshot includes non-stub Lattice, Blueprint, Knowledge, Memory, related_work, skill_selection, playbook_selection, freshness when sources exist
- [ ] Knowledge and Memory remain separate keys/stores
- [ ] ContextEngine items carry full provenance from PI sources

## Spine connectivity

- [ ] Ask/Plan/Agent via MentrixDeveloperService use live PI (no parallel context system)
- [ ] Fabric run can consume WorkItem/approved plan context
- [ ] ForgeLoop mentrix_native build still sole code editor path
- [ ] Ultra Review consumes WorkItem/ContextPack evidence inputs
- [ ] EvidenceVerifier â†’ READY_TO_SHIP â†’ PR + optional Jira/Camunda updates

## Tests / docs

- [ ] Connectivity/gap integration suite green
- [ ] `docs/architecture/ZECT_GAP_ANALYSIS.md` P1 rows not MISSING
- [ ] EXECUTION_MANIFEST all mandatory ops completed with evidence
- [ ] No duplicate DeveloperService / ContextEngine / Coding Agent introduced

## Explicit non-DoD

- Full Playwright suite green (unless expanded later)
- Sidebar redesign / System Health
