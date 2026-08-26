# ZECT PRESENT --- FINAL ROOT-CAUSE LAYOUT GENERATION CLOSURE V3

## Authority

Current verdict: `ZECT_PRESENT_PRODUCT_PARTIAL`. Latest human
screenshots override automated READY claims. Preserve working
exact-count enforcement, Insert/Chart/Table/Diagram/Presenter and export
blocking. No auto-merge. Do not declare PRODUCT_READY.

## Why repeated fixes have not solved it

Previous work fixed symptoms (3→6 defaults, duplicate IDs, export
blocking, Picture+Text, quality status), but the live product still
allows:

`correct count + wrong template semantics + poor layout selection + bad composition + ineffective repair = bad presentation`.

The remaining root system is:
`PPTX → Template parser → TemplateDefinition → Layout semantics → SlidePlan → LayoutPlanner → LayoutComposer → PresentationDocument → rendered browser geometry → QualityCritic → RepairEngine`.

Do not patch only final coordinates/CSS.

## 1. Reproduce the exact human failure

Use the real UI: - Prompt:
`Difference between AI Agentic and the Graph, loop and KV catch with LLM fine tuning` -
Template: `A1_Zinnia_PPT_Template` - Slides: `3` - Audience: `General`

Capture Create screen, Confirm Outline, request/job, 3 SlidePlans,
template/layout semantics, selected layout/reason per slide, composed
document, rendered bounds, quality findings, repair attempts and final
screenshots. Preserve this as the Golden Failure Fixture.

## 2. Eliminate contradictory slide-count semantics

The human screenshot shows `Slides=3` while Confirm Outline says
`Target ~6 slides`. Fix this completely.

When explicit count exists, `requested_slide_count=3` replaces/removes
audience/default/approximate/model/template/cached/previous count hints.
LLM/planner prompts must say exactly 3. Confirm Outline must say
`Target: 3 slides`.

Hard assertion:
`request=3 → job=3 → outline=3 → SlidePlan=3 → document=3 → Review=3 → PPTX=3`.
Fail immediately at the boundary that violates it. Never generate 6 then
truncate.

## 3. Semantic template classification

Classify every master/layout shape:
`MASTER_DECORATION, LAYOUT_DECORATION, TITLE_PLACEHOLDER, SUBTITLE_PLACEHOLDER, BODY_PLACEHOLDER, IMAGE_PLACEHOLDER, CHART_PLACEHOLDER, TABLE_PLACEHOLDER, FOOTER, LOGO, PROTECTED_BRAND_ELEMENT, EDITABLE_CONTENT_REGION, UNKNOWN`.

Use placeholder type, master/layout provenance, shape name,
relationship, z-order, geometry, repetition across layouts, theme and
existing content.

Decoration is NOT a content region. The orange Zinnia bars/curves must
be classified/protected correctly.

## 4. TemplateLayoutSemanticMap

For every usable layout persist:
`layout_id, name, purpose_tags, title_region, subtitle_region, body_regions, image_regions, chart_regions, table_regions, protected_regions, decorative_shapes, footer_regions, logo_regions, safe_content_bounds, capacity, visual_balance_profile`.

Templates without reliable mapping remain `TEMPLATE_NOT_READY`.

## 5. Development-only semantic debugger

Add an Advanced/dev overlay for
TITLE/BODY/IMAGE/CHART/TABLE/SAFE/PROTECTED/DECORATION/LOGO/FOOTER.
Capture the exact failing Zinnia layout overlay as evidence. Never
export this overlay.

## 6. Structured SlidePlan

Each exact slide must have:
`purpose, title, key_message, content_hierarchy, visual_intent, preferred_layout_role, required_visual_objects, content_density, source_refs, speaker_notes_intent`.

Plan the slide before placing text. No arbitrary fragments followed by
random placement.

## 7. Purpose-driven LayoutPlanner

Hard FAIL on slide-index/modulo/random/first-layout cycling.

Score layouts using:
`purpose + visual intent + content type/volume + placeholder compatibility + capacity + safe/protected regions + visual balance + deck diversity`.

Persist selected layout, score, reasons and rejected candidates.

## 8. Capacity-aware LayoutComposer

Measure title/body capacity, regions, minimum readable font,
image/chart/table capacity, margins and protected conflicts. Estimate
actual wrapping using intended font/size/width before committing.

Map semantic blocks to semantic regions. If incompatible, choose another
layout/re-plan/repair. Never place generated content into
decoration/master geometry or generic global boxes.

## 9. Protect template/master geometry

Generated content must not overlap protected
branding/logo/footer/critical decoration unless the layout explicitly
defines a compatible region. The decoration itself is not necessarily
wrong; incorrect content placement through it is.

## 10. Typography/hierarchy

Require readable title/subtitle/body hierarchy, spacing and alignment.
Detect tiny orphan labels, duplicate labels, overflow fragments, body
split across unrelated boxes, hidden titles and excessive accidental
whitespace. Never shrink merely until technically fitting.

## 11. Rendered browser geometry is quality truth

After composition render in the actual PresentDocument canvas and
collect computed bounding rect, visible rect, overflow, font size, line
height, z-order/intersections and canvas bounds for every visible
element.

QualityCritic must use rendered measurements, not only planned OOXML/EMU
geometry. The supplied human screenshots MUST fail automatically.

## 12. One authoritative quality verdict

Never show `0 collisions / 0 clipped` while reporting
`rendered_overlap`.

Expose one deck verdict: `PASS | NEEDS_REVIEW | FAIL`, with consistent
submetrics:
`rendered_overlaps, clipped_elements, low_value_slides, template_conflicts, duplicate_ids, document_semantics, media, export_integrity`.

Any Critical prevents PASS.

## 13. Visual-composition quality

Beyond intersection math, deterministically evaluate alignment, spacing,
density, hierarchy, balance, large accidental whitespace, tiny isolated
content, template obstruction, repeated content and near-empty slides.
LLM visual critique may supplement deterministic checks but cannot be
the only gate.

## 14. Automatic per-slide RepairEngine

The current `bad deck → Review → Export blocked` flow is insufficient.

Required:
`Compose → Render → Critic FAIL → Repair → alternate compatible layout/reflow/recompose → Render → Critic → repeat`.

Strategies: 1. next highest-scoring compatible layout; 2. remap semantic
blocks; 3. summarize excessive content; 4. merge duplicate fragments; 5.
resize within readability bounds; 6. improve spacing/alignment; 7. move
visuals to semantic regions; 8. remove accidental empty blocks; 9.
regenerate only the failing slide if needed.

Bound attempts. Preserve good slides. Only exhausted failures become
NEEDS_REVIEW.

Track `quality_before, repair_attempts, quality_after, final_layout` per
slide.

## 15. Golden slide acceptance

Every generated slide must have clear purpose, readable title/body,
meaningful hierarchy, appropriate layout, zero rendered
overlap/clipping/protected-region conflict, no accidental
blank/near-empty/tiny orphan/duplicate content and acceptable template
fidelity.

All 3 must pass.

## 16. Review UI cleanup

Normal Review/Edit should be visual. Move raw Slide text forms,
`IMAGE · DOCUMENT` internals, raw block forms/coordinates/parser
metadata under Properties→Advanced where needed.

Normal UI: `slide rail | large canvas | AI/Properties/Insert`, plus
Quality/Rehearse/Export. Selecting an object shows semantic properties.

## 17. Export

Do NOT weaken Critical export blocking. When blocked, show
slide-specific reasons plus Open Quality/Repair.

After PASS: - Browser: actual download event + filename + byte count. -
Electron: Save As → write → verify exists → saved path → Open File/Open
Folder. - PowerPoint: exactly 3, no repair, correct master/theme,
readable/editable content.

## 18. External-source research rule

External presentation source may be studied for template analysis,
layout representation, generation, editing and export concepts, but
runtime architecture remains ZECT-owned. Do not merely copy UI while
retaining a broken composer. If any source is actually reused/adapted,
comply with applicable license/notice requirements internally;
user-facing product remains ZECT.

## 19. Golden evidence

For one `generation_job_id`, save evidence containing
requested/outline/plan/document/review/PPTX counts plus per-slide
purpose, selected layout/score/reason, quality before, repairs, quality
after and final layout. No hidden transitions.

## 20. Permanent tests

Add: - `test_explicit_count_removes_audience_hint` -
`test_outline_exact_requested_count` -
`test_template_shape_semantic_classification` -
`test_decoration_not_content_region` -
`test_layout_planner_purpose_driven` -
`test_layout_capacity_rejects_overflow` -
`test_rendered_overlap_detected` -
`test_quality_summary_matches_rendered_findings` -
`test_repair_switches_layout` - `test_repair_preserves_good_slides` -
`test_protected_template_region` - `test_near_empty_slide_rejected` -
`test_golden_zinnia_three_slide_generation`

Plus headed Browser/Electron acceptance. Synthetic fixtures cannot
replace the exact real Zinnia fixture.

## 21. Runtime matrix

Run golden deck at 1280×720, 1366×768, 1440×900, 1920×1080 and Electron
maximize/restore. Viewport scaling must not alter slide semantics.

## 22. Regression protection

Re-run Blank layouts, Insert Text/Image/Shape/Icon, native Chart/Table,
Diagram, save/reopen, AI edits, original PPTX fidelity, exact 1/3/6/20,
Presenter clone/stock/no narration, Browser/Electron export, security,
Ultra Review and CI.

## 23. Focused tranches

`LAY1 count/outline contradiction → LAY2 semantic classifier/map → LAY3 purpose-driven planner → LAY4 capacity composer → LAY5 rendered geometry/unified quality → LAY6 per-slide repair → LAY7 Review cleanup → LAY8 headed Zinnia golden → LAY9 Export/PowerPoint/regression`.

Each: sync develop → implement → tests → headed evidence →
Electron/PowerPoint as relevant → security → Ultra Review → CI → PR →
human merge. No auto-merge.

## 24. Final human gate

Do not return V2 READY again. Next allowed stop:

`READY_FOR_HUMAN_PRESENT_LAYOUT_GENERATION_REVIEW_V3`

Only when:
`requested=3, outline=3, plan=3, document=3, review=3, pptx=3`, Confirm
Outline never says \~6, all 3 slides are visually acceptable,
`rendered_overlap=0, clipped=0, template_conflict=0, duplicate_ids=0, near_empty=0`,
`final_quality_status=PASS`, automatic repair is proven, export becomes
enabled only after PASS, Browser/Electron export is proven, PowerPoint
opens without repair.

Leave backend/frontend/Electron running and the exact golden deck open.
Do not declare PRODUCT_READY.

# FINAL CURSOR COMMAND

Read `ZECT_PRESENT_FINAL_ROOT_CAUSE_LAYOUT_GENERATION_CLOSURE_V3.md`
completely.

The previous V2 human review FAILED. Keep
`ZECT_PRESENT_PRODUCT_PARTIAL`.

Do not patch another isolated coordinate/default/CSS rule. The
screenshots prove the remaining failure is architectural: contradictory
count semantics remain in the outline, template/master decoration is not
semantically understood, layout selection/composition is poor, rendered
quality contradicts its own summary, and RepairEngine allows visibly
broken slides into Review.

Reproduce the exact real Zinnia + explicit-3 human flow and instrument
one generation_job_id end-to-end. Remove `Target ~6 slides`; build
TemplateLayoutSemanticMap; add dev semantic overlay; replace
index/random layout cycling with purpose-driven scored LayoutPlanner;
make LayoutComposer semantic/capacity-aware; protect decoration/master
regions; make actual rendered browser geometry authoritative for
overlap/clipping; unify quality metrics/verdict; implement automatic
per-slide alternate-layout/reflow/recompose repair before Review.

Preserve proven Insert/Chart/Table/Diagram/Presenter and Critical export
blocking. Do not ask the human to test another isolated patch.

Run the exact golden UI test until it produces exactly 3 visually
acceptable Zinnia slides with zero overlap/clipping/template
conflict/duplicate IDs/near-empty slides and final_quality_status=PASS.
Then prove Browser/Electron export and real PowerPoint.

No auto-merge. No PRODUCT_READY. Stop only at
`READY_FOR_HUMAN_PRESENT_LAYOUT_GENERATION_REVIEW_V3`.
