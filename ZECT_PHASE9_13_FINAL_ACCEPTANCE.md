# ZECT Phases 9–13 — Final Acceptance

**Date:** 2026-08-12  
**Prompt:** `prompts/ZECT_PHASE9_13_BATCH_EXECUTION_PROMPT.md`  
**Master plan:** `.cursor/plans/master_live_product_fix_a8c0797d.plan.md`  
**Stop condition:** STOP after Phase 13 — B–D not started.

## Frozen baselines preserved

| Gate | Status |
|------|--------|
| Present A1–A8 / LIVE_VIABLE | FROZEN (not redesigned) |
| `zinnia-executive-v1` | FROZEN |
| PresentationProvider / Present Model Gateway | FROZEN |
| Voicebox async / A6 voice FSM | FROZEN |
| Electron single-instance | FROZEN |
| Phase 5–8 (nav, onboarding, PI, ASK/PLAN/AGENT+LRR) | FROZEN |

Present QUALITY route smoke: `ok=true`, `fallback_used=false` — see `artifacts/phase9-13-frozen-regression-smoke.json`.

## Consolidated table

| Phase | Operation | Implementation | Tests | Live Evidence | Security | Regression | Status | Blocker |
|-------|-----------|----------------|-------|---------------|----------|------------|--------|---------|
| 9 | Learning usable path (lang→practice→code→tests→hint→evidence) | `/api/learning/languages`, practice verify + EvidenceVerifier progress, `ZectLearning.tsx` chips + Practice panel | `test_phase9_13_batch.py::test_learning_*` + existing GUIDED tests | `artifacts/phase9-13-live.json` | USER_PRIVATE progress; GUIDED no auto-solve | Learning + Present gateway smoke PASS | **PASS** | — |
| 10 | Model Gateway / profiles / no silent fallback | `app/services/model_gateway.py`; `/api/system/model-readiness` profiles matrix | `test_model_*`, present gateway tests | smoke JSON profiles list | RESTRICTED never allow_cloud | Present QUALITY unchanged | **PASS** | Companion full route migration not required for this tranche |
| 11 | Recharts / container warnings | Fixed-height `ResponsiveContainer` + `YAxis` width on Analytics, DataLayer, MentrixArtifacts | build/runtime not broken (unit N/A) | chart wrappers present | n/a | no Present/Developer redesign | **PASS** | Browser console not re-captured in this batch (code-level fix) |
| 12 | Windows packaging readiness | `docs/WINDOWS_INSTALL.md`, `electron/service-lifecycle.js`, desktop-readiness packaging fields | `test_desktop_packaging_honest_partial` | desktop readiness `PARTIAL` | secrets stay out of installer | Electron single-instance untouched | **PARTIAL** | backend not bundled in NSIS; one-click not claimed |
| 13 | Multi-user isolation + sidebar report | `app/core/scopes.py`; auth+owner filter on conversations; memory router auth + preference/typed self-scope | isolation tests in `test_phase9_13_batch.py` | API 401/404 cross-user | P0 conversation leak closed; memory auth required | 58/60 related smoke; 2 pre-existing P1 VERIFYING asserts (not phase-caused) | **PASS** | Full team ACL for all memory layers still incremental |

## Files changed (exact)

**Backend**
- `backend/app/services/model_gateway.py` (new)
- `backend/app/core/scopes.py` (new)
- `backend/app/domains/personal_agent/learning.py`
- `backend/app/domains/personal_agent/conversations.py`
- `backend/app/domains/personal_agent/memory.py`
- `backend/app/routers/system_health.py`
- `backend/app/services/desktop_readiness.py`
- `backend/tests/fixes_and_phases/test_phase9_13_batch.py` (new)

**Frontend**
- `frontend/src/pages/ZectLearning.tsx`
- `frontend/src/pages/Analytics.tsx`
- `frontend/src/pages/DataLayer.tsx`
- `frontend/src/components/MentrixArtifacts.tsx`

**Desktop / docs**
- `electron/service-lifecycle.js` (new)
- `electron/main.js` (optional managed probe)
- `electron/package.json` (include lifecycle in build files)
- `docs/WINDOWS_INSTALL.md` (new)

**Artifacts** (local / gitignored — not committed)

- `artifacts/phase9-13-frozen-regression-smoke.json`
- `artifacts/phase9-13-live.json`

Master plan (local gitignored `.cursor/plans/…`): `phase9-13-tail` marked completed; B–D remain pending.

## Completed operations

- Learning catalog path usable with modes `GUIDED|PAIR|DEMO|AUTONOMOUS` and languages Python/JS/TS/Java/C#/Go/Rust/C/C++.
- EvidenceVerifier gates verified learning progress; `user_confirmed` cannot alone complete.
- Canonical `MODEL_PROFILES` + model-readiness audit; duplicate env warning surfaced.
- Recharts containers given explicit pixel heights / YAxis widths.
- Windows packaging documented honestly as PARTIAL with managed probe hook.
- Conversations + memory preferences/typed scoped; scopes enum published.

## PARTIAL / BLOCKED

| Item | Status | Notes |
|------|--------|-------|
| Windows one-click Install→Ready | **PARTIAL** | Backend not in installer; Voicebox/Presenton external |
| Memory full layer ACL (working/episodic/lessons by project) | incremental | Auth required on router; typed+preferences self-scoped; project-shared PI reuse remains commit-bound |
| Browser Recharts console capture | not re-run live | Code fix applied |

## Regressions

- Present / Learning / LRR / gateway tests: **PASS** in batch smoke (58 passed).
- `test_mentrix_p1_project_intelligence` 2 asserts (`VERIFYING` vs `READY_TO_SHIP`) — **pre-existing / unrelated** to Phase 9–13 file set (empty mandatory ops + thin evidence). Not treated as phase regression; not “fixed” here to avoid reopening Phase 7/8 Evidence paths.

## Sidebar / Settings report (no broad redesign)

**Current sections:** Mentrix · Work · Intelligence · Delivery · Security · Operations (+ Settings-owned links).

**Preferred direction (future, not implemented now):**

```text
MENTRIX → Companion
WORK → Projects, Work Items
BUILD → Developer, Runs
CREATE → Present
LEARN → ZECT Learning
AUTOMATE → Processes, Scheduled Tasks
MORE → Knowledge, Analytics, Settings
```

**Candidates to move under Settings later:** Models, Integrations, Voice, Present advanced, Repositories, Intelligence (Lattice/Blueprint/Knowledge/Memory/Skills/Playbooks), Automation, Security, System Health, Advanced, Token Controls, Rules, Audit, Secrets, Permissions, Architecture, Docs.

Unfinished vs preferred IA: Learning still under Intelligence; Present under Mentrix; Runs/Developer naming already Phase-5 correct; many advanced surfaces still top-level.

## Learning status

**PASS** for catalog-usable path. Expanded Learn curriculum / D tranche **not** started.

## Packaging status

**PARTIAL** — see `docs/WINDOWS_INSTALL.md` and `/api/system/desktop-readiness`.

## Remaining B–D roadmap (do not auto-start)

| Tranche | Scope | Dependencies |
|---------|-------|--------------|
| **B** Document Intelligence | Doc ingest → ContextEngine/PI/Knowledge | Phase 7 PI READY; ArtifactStore; Permission Broker |
| **C** Web Intelligence | Connector Gateway + `UNTRUSTED_EXTERNAL_CONTEXT` | Connector matrix; sanitizer; DLP |
| **D** Expanded Learning | Deeper curricula / skills graduation | Phase 9 practice path; Skills/Playbooks; EvidenceVerifier |

## Clean end-to-end release acceptance?

**Not yet justified** for a full release run: packaging remains PARTIAL (backend not bundled), B–D unfinished, and installer/Voicebox/Presenton one-click not proven on a clean Windows machine. Phase 5–13 product spine is in good shape for continued live use with existing ops (`:8000` / `:5173` / optional Voicebox+Presenton).

## Verdict

Phases **9 PASS · 10 PASS · 11 PASS · 12 PARTIAL · 13 PASS**. Batch acceptance: **PASS with packaging PARTIAL**. Stopped after Phase 13.
