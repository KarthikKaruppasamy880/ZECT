# ZECT Present P0 Generation → Review → Export Acceptance

**Date:** 2026-08-14  
**Branch:** `feat/present-s75-quality-closure` (uncommitted P0 + prior S7.7/V2 work preserved)  
**Presenton default:** unchanged (`:8000`). Native remains opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native` on `:8010`).  
**S8C / S8D / blinded A/B regen:** not started.

## Gate

**Headed P0 (native `:8010`):** Dashboard → Create with AI → Quality Generate → Review/Edit → Export **passed**. Repeat with Fast **passed**. Developer layout: Context Used is a tools tab (default off); Lattice header and Context Used share `NOT_CONFIGURED | NOT_INDEXED | INDEXING | READY | STALE | ERROR | NOT_APPLICABLE`. Projects fixture audit after generate: no proven_test rows reappeared.

**PowerPoint:** Quality and Fast PPTX files opened in desktop PowerPoint (5 slides each). Inspector `hard_findings=[]`. Critical findings cannot be overridden by `accept_warnings`.

**Electron:** Present dashboard loaded in the Electron shell against the same Vite + native API. Full generate/export was proven in headed Chromium; Playwright Electron generate clicks were not a reliable second driver on this machine.

**Mentrix Ultra Review (P0 export-gate diff):** passed, score 85, **0 Critical**. One Medium (preview promise) is already `.catch`-guarded.

**S8C / S8D / blinded A/B regen:** not started. Do not auto-merge.

After CI on the PR to `develop`, this branch is **`READY_TO_MERGE`** (human merge only).

## Defects closed

| Defect | Root cause | Repair |
|--------|------------|--------|
| Slide title/body duplicated and overlapping in `zect-deck.pptx` | Editor covering dump at 0.5"×1.5"×9"×5" plus renderer placeholder **and** generated body; `compose_regions` set `visual = dict(body)` | XOR placeholder vs generated shape; clear layout sample text; split body/visual; strip covering dumps on inspect/save |
| Quality allowed export of colliding PPTX | Critic saw plan boxes; `validate_generated_pptx` is zip/slide-count only; Fast `degraded_override` could mark layout FAIL as PASS | `FinalPptxInspector` on saved OOXML; Fast still runs composer/inspector/critic; layout collisions still FAIL |
| `/present` was one long generate form | Product IA mixed dashboard, generate, editor, voice | Dashboard → Create / Blank / Import → Review/Edit → Rehearse → Export |
| Projects UI showed 1 card while ~64 rows remained | `exclude_fixtures=1` **hides** leftover E2E `provenance=user` rows; audit 404 from stale `:8000` | `POST /api/projects/fixtures/keep-cleanup` with explicit `keep_ids`; E2E posts `provenance=test` |
| Workspace Context Used stole a fourth column | Permanent column vs Explorer/Editor/Agent | Context Used is a bottom tools tab; default off |
| Lattice READY vs Context `unavailable` | PI default `"unavailable"` | Same `get_lattice_status()` states (`NOT_CONFIGURED` / `NOT_INDEXED` / `INDEXING` / `READY` / `STALE` / `ERROR` / `NOT_APPLICABLE`) |

## Operator project cleanup

Keep **ZOAS Eval** (id **7**) by audited id (not a product name allowlist). Dry-run then live `keep-cleanup` deleted **62** leftover rows. After cleanup, `GET /api/projects?exclude_fixtures=1` and `exclude_fixtures=0` both list only that project. Audit: 0 proven_test, 0 name_candidates, 1 authorized.

See `ZECT_DATA_HYGIENE_ACCEPTANCE.md`.

## Present routes

| Route | Surface |
|-------|---------|
| `/present` | Dashboard: Create with AI, Blank, Import, recent thumbs, templates |
| `/present/create` | Prompt + cover gallery + **Generate presentation** (Fast under Advanced) |
| `/present/blank` | Empty deck → Review |
| `/present/import` | PPTX upload → Review |
| `/present/templates` | Gallery |
| `/present/d/:deckId` | Review/Edit canvas (slide PNG + notes) |
| `/present/d/:deckId/rehearse` | Notes + Voicebox |
| `/present/d/:deckId/export` | Quality gate; hard inspector findings cannot be accepted; only non-critical warnings may be accepted |

Companion **Open Present** hands off to `/present/create`. Voice is not on Generate.

## Tests

`backend/tests/fixes_and_phases/test_p0_present_quality.py` + S7.7 critic tests: **28 passed**. Hygiene + lattice: **8 passed**.

- fixture / synthetic dump overlap detected and stripped
- placeholder vs generated mutual exclusion
- OOXML inspector
- editor save/export idempotence
- Fast and Quality both call inspector/critic
- Fast degraded does not override layout FAIL
- export blocked on `QUALITY_FAILED`
- keep-cleanup never deletes `keep_ids`
- KV-cache “reduces memory” wording flagged; recomputation wording not flagged

Frontend: generate on `/present/create` navigates to `/present/d/`.

## Headed PowerPoint proof (§22)

Must be run from the real ZECT UI against native `:8010`, Zinnia template, Quality then Fast, then open the file in desktop PowerPoint. This session does **not** treat inspector PASS as PowerPoint PASS.

## What this is not

- Not S8C/S8D
- Not a new blinded A/B pack
- Not Presenton branding / Template Studio / Community
- Presence 401 is out of scope
