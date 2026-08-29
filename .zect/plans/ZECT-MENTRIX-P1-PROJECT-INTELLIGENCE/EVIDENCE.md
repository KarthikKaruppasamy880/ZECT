# EVIDENCE — Mentrix P1 Project Intelligence

| ID | Op | Evidence |
|----|-----|----------|
| EV-001 | OP-001 | `backend/app/main.py` preserves auth/DB under `ZECT_PYTEST`; `backend/tests/conftest.py` sets flag before import |
| EV-002 | OP-002 | `frontend/vite.config.ts` + `package.json` exclude `**/e2e/**`; `npm test` → 57 passed / 11 files |
| EV-010 | OP-010 | `JiraSourceAdapter` + `ingest_work_item`; tests `test_jira_ingest_fixture_binds_repo`, `test_ingest_missing_repo_needs_human` |
| EV-011 | OP-011 | `CamundaSourceAdapter` + ingest; test `test_camunda_ingest_fixture` |
| EV-020 | OP-020 | `project_intelligence.py` Lattice/Blueprint/KB/Memory |
| EV-021 | OP-021 | Skills/Playbooks/related_work/freshness; test `test_project_intelligence_knowledge_memory_distinct` |
| EV-030 | OP-030 | `MentrixDeveloperService._build_pack` passes query into PI; test `test_developer_ask_uses_live_pi` |
| EV-031 | OP-031 | `fabric_handoff.py` + `/api/mentrix/developer/fabric-handoff`; test `test_fabric_handoff_requires_approved_plan` |
| EV-032 | OP-032 | `ownership.py` ForgeLoop mentrix_native + ArtifactStore PLAN SoT; test `test_forgeloop_ownership_mentrix_native_and_artifact_store` |
| EV-033 | OP-033 | `ultra_review_context.py` + ultrareview route; test `test_ultrareview_consumes_work_item_context` |
| EV-040 | OP-040 | `close_loop.py` + verify_and_ready_to_ship dry_run; test `test_evidence_ready_to_ship_triggers_close_loop_dry_run` |
| EV-050 | OP-050 | `test_connectivity_spine_smoke` + full P1 file 12 passed |
| EV-051 | OP-051 | `docs/architecture/ZECT_GAP_ANALYSIS.md` P1 rows COMPLETE |
| EV-060 | OP-060 | ACCEPTANCE all mandatory checked; no parallel engines; gate COMPLETE |

## Commands

```
cd backend
python -m pytest tests/fixes_and_phases/test_mentrix_p0_consolidation.py tests/fixes_and_phases/test_mentrix_p1_project_intelligence.py -q
# 30 passed

cd frontend
npm test
# 57 passed (e2e excluded)
```
