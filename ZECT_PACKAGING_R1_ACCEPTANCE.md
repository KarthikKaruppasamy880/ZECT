# ZECT Packaging R1 Acceptance

**Branch:** `feat/r1-desktop-packaging-partial`  
**Date:** 2026-08-13  
**Spec:** `prompts/ZECT_NEXT_ROADMAP_KV_CACHE_DOCUMENT_WEB_GRAPH_AGENTS.md` §R1  
**Frozen base:** `db405a9` (pre-merge)

## Audit

| Cap | Classification | Evidence |
|-----|----------------|----------|
| NSIS / portable targets | ALREADY_BUILT | `electron/package.json` |
| Frontend dist packaging | PARTIAL → improved path `frontend/dist` | builder `files` map |
| Single-instance lock | MISSING → **IMPLEMENTED** | `requestSingleInstanceLock` + `second-instance` |
| Managed probe / start | ALREADY_BUILT | `service-lifecycle.js` |
| Managed shutdown | MISSING → **IMPLEMENTED** | `stopManagedChildren` on `will-quit` |
| userData logs/config/data | MISSING → **IMPLEMENTED** | `ensureUserDataDirs` |
| Canonical API port :8000 | PARTIAL → **aligned** | lifecycle + `api.ts` default + docs |
| Backend sidecar slot | MISSING → **slot only** | `electron/resources/backend/README.md` |
| Backend bundled one-click | **BLOCKED** | no `zect-api.exe` / embedded runtime |
| Voicebox / Presenton | **BLOCKED_EXTERNAL** | unchanged |
| Clean-machine Install→Ready | **NOT_PROVEN** | requires bundled API |

## Verdict

**PARTIAL** — closable desktop lifecycle gaps closed; one-click packaging **not** claimed.

## Proofs

```text
pytest backend/tests/fixes_and_phases/test_phase9_13_batch.py::test_desktop_packaging_honest_partial -q
pytest backend/tests/fixes_and_phases/test_phase9_13_batch.py::test_service_lifecycle_exports_stop_and_single_instance_docs -q
```

`GET /api/system/desktop-readiness` → `packaging.status=PARTIAL`, `single_instance_lock=true`, `backend_bundled=false`.

## Stop

Do not flip packaging to PASS without backend sidecar + clean Windows install proof. Proceed to R2 after merge.
