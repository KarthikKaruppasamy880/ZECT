# ZECT Present — V3 Layout Generation Closure

**Verdict:** `ZECT_PRESENT_PRODUCTION_RELEASE_CANDIDATE` — golden V3 + legacy deck repair proof passes (`present_production_release_proof.py`).

**Golden (2026-08-26):** 3 slides, outline `Target: 3 slides`, `final_quality_status=PASS`, `overlap_count=0`, `rendered_overlap_count=0`. A1 template re-imported to `zinnia-executive-v1` (20 layouts, semantic enrichment).

**Production PR (#191):** OOXML duplicate-overlap repair, semantic label/body inspector tuning, Review slide PNG preview, quality banner OOXML vs rendered metrics.

**Previous gate:** V2 human review **FAILED** (outline ~6 vs slides=3, rendered_overlap, contradictory quality summary, raw Edit UI).

## V3 tranche delivered (LAY1–LAY7)

| Layer | Fix |
|-------|-----|
| LAY1 | `prepare_prompt_deck` + `prompt_adapter` honor `requested_slide_count`; Confirm Outline shows `Target: 3 slides` |
| LAY2 | `template_semantics.py` — shape roles, `TemplateLayoutSemanticMap`, protected regions |
| LAY3 | Purpose-driven `pick_template_layout` with rejection/score reasons |
| LAY4 | `compose_regions` clamps to `safe_content_bounds` away from decoration |
| LAY5 | Unified quality gate metrics (`rendered_overlap_count`, `template_conflict_count`) |
| LAY6 | Repair tries alternate layouts via `_layout_exclude` + `change_layout` on overlap |
| LAY7 | Edit route uses visual `variant="edit"` — raw Slide text/IMAGE blocks only in studio+Advanced |

## Tests

`backend/tests/fixes_and_phases/test_present_layout_v3.py` — 10 new tests (19 passed with plan suite).

## Golden proof

Script: `backend/scripts/present_golden_v3_proof.py`  
Artifact: `backend/artifacts/present-golden-v3/golden_v3_report.json`

## Next allowed stop

`READY_FOR_HUMAN_PRESENT_LAYOUT_GENERATION_REVIEW_V3` — only after headed UI reproduces 3 acceptable Zinnia slides with `final_quality_status=PASS`, zero rendered overlap/clipping, export enabled, PowerPoint opens clean.

**Not declared:** PRODUCT_READY
