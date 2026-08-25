# ZECT Present — PresentationDocument model (E1)

Canonical in-memory deck used by parse, editor, thumbs, save, quality critic, and export.

```text
kind: PresentationDocument
schema_version: 2
path, provider
slide_cx, slide_cy          # EMU; widescreen default 9144000 × 5143500
visuals                     # has_image / has_chart / has_table counts
slides[]:
  index, text, notes, layout_selected?, visual_intent?
  blocks[]:
    id, kind, geometry {x,y,cx,cy,rot}, parent_geometry?
    content, provenance, validation
```

## Geometry

One module: `backend/app/services/mentrix/presentation/geometry.py` and `frontend/src/lib/presentGeometry.ts`.

- Missing or zero `cx`/`cy` is invalid. Overlays **must not** expand to cover the slide.
- Group/placeholder children: `compose_child_geometry(parent, child)` = parent origin + child offset.
- Quality critic overlap / off-slide uses the same predicates.

## Construction

| Source | Function |
|---|---|
| Plan | `document_from_plan` |
| PPTX bytes | `document_from_pptx_bytes` |
| Parse + sidecar | `normalize_document` after `merge_sidecar_slides` |

`POST /api/mentrix/present/parse-pptx-path` returns `slides` (editor payload) **and** `document` (schema 2).

## Remaining

Slide XML plus **locked** master/layout graphics (non-placeholder pictures/shapes) are parsed into the same block list. COM raster remains a **proof** path, not the editor model. Full run-level typography and every imported SmartArt variant are not a golden Zinnia visual PASS until headed COM comparison exists.
