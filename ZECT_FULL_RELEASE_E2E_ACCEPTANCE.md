# ZECT Full Release E2E Acceptance

**Date:** 2026-08-19  
**Canonical develop (pre-PR):** `55255f0b05240815a1547c0ea33d4317706acc99` (PR **#166** human-merged)  
**Branch:** `feat/full-release-e2e`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md` — Tranche H only  
**Stop label:** `READY_TO_MERGE_FULL_RELEASE_E2E` — human merge only, no auto-merge.  
**Do not start** Tranche I, S8C/S8D, Graphify, KV-cache, OCR/XLSX, broader Web, new agents.

## Verdict

One coherent headed journey **PASS** (29s). Local Electron journey **PASS** (32s, not shell-only). Live Presenton Generate, Voicebox, Jira/Camunda ingest, and PowerPoint COM were not converted to PASS.

Overall ZECT remains **ZECT_PRODUCTION_PARTIAL**. Tranche I is not in this PR.

## Browser journey (required)

`Login → Project → multi-root Developer → Companion → WorkItem → Coding Agent (tests/review) → Present → Voice → Process/status`

Spec: `frontend/e2e/full-release-e2e-production.spec.ts` (in `test:e2e:core`).

| Step | Proof |
|------|--------|
| Login | `projects-page` after auth; login form absent |
| Project | User project visible; `provenance=test` fixture hidden |
| Multi-root Developer | Two registered roots, explorer file, terminal |
| Companion | HUD + both roots on scope strip |
| WorkItem | Sample process WorkItem detail |
| Coding Agent | PLAN approve → tests **pass** → diff/review (`awaiting_git_approval`). Live GitHub PR not clicked |
| Present | Zinnia template + Create AI controls; blank → Review → Export PPTX. Live Generate not clicked when disabled |
| Voice | Companion Voice / clone panel; live Voicebox recorded, not faked |
| Process | Fabric sample + connector chips; live ingest not clicked |

## Electron journey (required; shell load is not PASS)

Spec: `frontend/e2e/full-release-e2e-electron.spec.ts` (not in CI core).

Login/session, Companion HUD, Developer multi-root + editor/terminal + coding mission to PLAN, Present template/blank/export gate, Voice panel, close + relaunch same `userData` and restore roots.

PowerPoint COM / live Generate / Voicebox = **BLOCKED_EXTERNAL** unless independently proven.

## Frozen regression

CI `npm run test:e2e:core` is the frozen headed run of merged product suites (A–G specs + this journey). Inventory: `backend/tests/test_full_release_e2e_inventory.py`.

Mentrix Ultra Review: **passed**, score 85, **0 critical**.

## Honest non-PASS

- Live Presenton Generate, Voicebox, Jira/Camunda, GitHub, PowerPoint COM, clean-machine NSIS, live Postgres
- Electron skip without binary ≠ PASS
- CodeRabbit skip-review widget ≠ PASS

## Stop

Human-merge this PR after CI. Next focused tranche after merge: **I** final review/release audit. Do not start S8C.
