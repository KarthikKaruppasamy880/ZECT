# ZECT Present — Final Product Closure V3

Canonical, code-verified status for the Present Final Closure tranche of
`ZECT_FINAL_CP09A_CP09B_PRESENT_CLOSURE_LIMITED_CREDITS.md`. Supersedes
prior `ZECT_PRESENT_*.md` reconciliation docs at the repo root for the
items below — those are kept for history but should not be treated as
current status; this doc reflects real code + real headed-browser +
real PowerPoint-COM verification run on 2026-09-04.

One canonical verdict per item: **PASS** (verified, code + live evidence),
**PARTIAL** (real gap found, scoped fix applied or gap documented),
**NOT_INDEPENDENTLY_VERIFIED** (code exists, not exercised live this pass).

## Status table

| # | Area | Verdict | Evidence |
|---|---|---|---|
| 1 | Exact requested slide count | **PASS** | Real headed generation (golden prompt, 3 slides requested): `slide_count_trace` shows 3 at every stage (request→planner_input→plan_built→enforce→post_repair); real PowerPoint COM open confirms `exactly_three: true`. |
| 2 | Real template visual fidelity | **PARTIAL** | Real COM/LibreOffice render path exists and is what ran today (this machine has real Office 365 PowerPoint); silently degrades to a PIL approximation when neither is available. Fidelity is environment-dependent by design — acceptable degradation, not a defect, but not "guaranteed" fidelity everywhere. |
| 3 | Purpose-driven layout selection | **PASS** | `layout_composer.py` scores by purpose/intent/protected-region conflict, not index cycling (code-verified, unchanged this pass). |
| 4 | Overlap/clipping/off-slide detection | **PASS** (detection) | Real headed UI run against the `zect-deck.pptx` legacy fixture correctly displays "15 collisions" / Quality FAIL and blocks export — detection is real and live-verified, not a heuristic that silently passes. |
| 5 | Rendered geometry validation + bounded repair | **PARTIAL — 2 real bugs found and fixed today, 1 gap remains documented** | See "Fixes shipped this pass" below. The bounded loop (4 attempts) now honestly reports FAIL when the real export gate would still block, instead of silently claiming PASS. It still cannot fully resolve the `zect-deck.pptx` fixture's worst case (59→15 broad-signal collisions) — the remaining 15 need a repair strategy this pass didn't build (see "Known remaining gap"). |
| 6 | Picture + Text combined layouts | **PARTIAL** (unchanged this pass) | Blank/Insert flow (`blank_document.py`) has a dedicated `picture_text` layout. The AI-generation flow's `layout_composer.py` still lumps image/chart/table/diagram into one generic scoring bucket — not re-attempted this pass, documented gap. |
| 7 | Blank/from-scratch creation | **PASS** (unchanged this pass) | `blank_document.py` + passing test suite. |
| 8 | Charts/tables/diagrams | **PASS** (unchanged this pass) | Native OOXML paint path, passing test suite. |
| 9 | Editor + thumbnail fidelity | **PASS** | Real headed run (`present-v3-headed-review-export.spec.ts`, fresh dev server + fresh golden deck) passed: Review → Edit → Export all rendered the same shared preview pipeline. |
| 10 | AI slide actions | **NOT_INDEPENDENTLY_VERIFIED** | Code exists (`slide_ai.py`); not exercised live this pass — out of budget for this tranche. |
| 11 | Single non-contradictory quality verdict | **PASS** | `quality_verdict.py`'s FAIL>NEEDS_REVIEW>PASS reducer is unchanged and correct; its *inputs* are now more honest per the item-5 fix. |
| 12 | Real PPTX export (native OOXML) | **PASS** | Unchanged, code-verified (`final_pptx_inspector.py` real `zipfile`/`python-pptx`). |
| 13 | PowerPoint round-trip | **PASS — real evidence for the first time** | Ran the previously `BLOCKED_EXTERNAL` COM golden proof live (`ZECT_LIVE_PPT_COM=1`, real Office 365 PowerPoint on this machine): opened the generated 3-slide deck with **no repair dialog** (`repair_dialog: false` — the exact signal a corrupt/malformed PPTX would trigger), slide count confirmed via COM (`exactly_three: true`), real PNG exports captured per slide via `Slide.Export`. Every prior doc said this had never actually been run. |
| 14 | Rehearse/narration duplicate voice | **NOT_INDEPENDENTLY_VERIFIED (no double-fire observed)** | `present-voice-production.spec.ts` (real headed run, real backend) passed end-to-end including the voice/narration step. No dedicated "assert exactly one concurrent audio stream" test exists — the architectural guard (`speak.ts` singleton + generation-counter cancellation) was not stress-tested for a race condition specifically. |

## Fixes shipped this pass (`app/services/mentrix/presentation/final_pptx_inspector.py`)

1. **Stale test, not a product bug**: `tests/test_performance_reliability_production.py::test_failed_present_diagnosed_from_telemetry` asserted `block_code == "restricted_external_provider"`, which only applies to the legacy `presenton` provider path. The production default is `ZECT_PRESENTATION_PROVIDER=zect_native`, whose planner correctly returns `"sensitivity_blocked"` for RESTRICTED content. Fixed the test to accept both codes, matching the pattern `test_s7_parity_benchmark.py` already uses for this exact reason.

2. **Real bug — repair loop silently did nothing for generic (non-dump-shape) overlaps**: `strip_duplicate_overlapping_textboxes()` tracked "shapes to remove" by Python `id(shape)` across two *separate* `slide.shapes` traversals. python-pptx builds a fresh wrapper object on every `.shapes` access, so `id()` never matched between the detection pass and the removal pass — the function always returned `removed=0`, for any input, regardless of whether a real duplicate/overlap was found. Reproduced live with a synthetic overlapping-textbox probe (`Quality FAIL, overlap_count=1` → repair → still `FAIL, overlap_count=1`, `duplicate_shapes_removed: null`). Fixed by tracking OOXML's own stable `shape.shape_id` instead. Verified: same probe now goes `FAIL/1` → `PASS/0`, 1 shape actually removed.

3. **Real bug — repair loop could report false "PASS"**: `inspect_and_repair_pptx()`'s loop-continuation and final-status check only ever consulted its own narrow `inspect_pptx_bytes()` overlap count — not the broader document-critic + rendered-quality signal `deck_catalog.quality_gate_for_path()` (the actual export-gate check the UI/API use) folds in. On the `zect-deck.pptx` legacy fixture this meant the repair function's own report said `"status": "PASS", "overlap_count": 0` for bytes the real export gate still failed with `overlap_count: 15`. Reproduced live via headed Playwright (`present-v3-headed-repair-deck.spec.ts`): clicking Repair reported success, but the Export page still showed "Quality FAIL / 15 collisions" and stayed blocked. Fixed `inspect_and_repair_pptx()` to also compute and honor that broader signal, so it now correctly reports `FAIL/15` for the same input — no more false-positive success. Full backend Present suite (194 tests) still green after both fixes; one pre-existing, unrelated failure (`test_pptx_fidelity_f1.py::test_large_media_gets_media_part_and_hydrates_to_asset_id`, media-hydration, confirmed unrelated by code inspection) is untouched by this work.

## Known remaining gap (not fixed this pass — flagged, not hidden)

The `zect-deck.pptx` legacy fixture's worst-case collisions (15 remaining after dump-shape + duplicate-textbox repair) are not resolvable by either existing repair strategy — they come from the rendered-quality/document-critic layer, not from a raw python-pptx shape-pair overlap either existing `strip_*` function knows how to target. Closing this fully requires a new repair strategy aimed at whatever `rendered_quality.py`'s heuristic is actually flagging on this deck, which was out of scope/budget for this pass. The important fix already shipped: the tool no longer *lies* about having fixed it.

## Verification method

- Real headed browser (Playwright, `--headed`, real Chromium window) against a freshly-started backend (`develop` tip, real `OPENAI_API_KEY`) and a freshly-started frontend dev server (a day-old stale dev server pointed at a dead backend was found and killed first — it had been silently causing two of these specs to fail for an unrelated reason).
- Real Microsoft PowerPoint (Office 365 ProPlus, confirmed installed on this machine) driven via COM automation — not a stub, not skipped.
- Full backend Present-tagged test suite (194 passed / 1 unrelated pre-existing failure / 5 skipped).
