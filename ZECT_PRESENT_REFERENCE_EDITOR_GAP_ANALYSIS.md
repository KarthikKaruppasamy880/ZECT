# ZECT Present — Reference Editor Gap Analysis (E0)

**Status:** E0 complete. **Stop for human review. No editor patches in this pass.**

| Field | Value |
|---|---|
| Date | 2026-08-24 |
| Branch recorded | `feat/developer-ask-approve-build` (uncommitted Present work **not** included) |
| Canonical `develop` SHA | `f8fd6cf` (`origin/develop` at analysis time; same SHA as `git rev-parse origin/develop`) |
| Last Present-related merge on that SHA | `Merge pull request #184` (companion HUD / present preview) — treat this SHA as the E0 baseline, not a later unmerged Present-fix branch |
| ZECT Present | Vite `http://127.0.0.1:5173/present` → API `http://127.0.0.1:8000` |
| Reference editor | Presenton `http://127.0.0.1:5000` per `ZECT_PRESENT_UX_PARITY_GAP.md` |
| Live Presenton this session | **Down** (`Unable to connect` on `:5000`). Side-by-side pixels were **not** captured. Behavioral comparison uses that gap doc + ZECT source/runtime. |
| Same real template | `prompts/Template.pptx` is in-tree; gallery id `zinnia-executive-v1` is the product Zinnia shell |
| Headed P0 (`ZECT_LIVE_P0=1`) | **Not run** (flag unset). Do not treat skipped P0 as PASS. |

## E0 regression (no Present code changes)

Ran existing Present specs against the live API on `:8000` after Developer ASK/PLAN work. **Did not patch Present.**

| Spec | Result |
|---|---|
| `frontend/e2e/present-product.spec.ts` | PASS (gallery → Zinnia → generate workspace → notes) |
| `frontend/e2e/present-editor-export.spec.ts` | PASS (open allowlisted PPTX, edit notes, export) |
| `frontend/e2e/present-p0-headed.spec.ts` | Skipped (`ZECT_LIVE_P0` unset) |

These specs prove **product chrome and a notes/export path**, not visual template-open fidelity. A green Present product spec is **not** an editor-parity PASS.

## Architecture already in tree (prove / falsify)

### What ZECT actually has

```
Prompt / Template id / uploaded PPTX
        ↓
TemplateDefinition JSON (theme swatches, layout names, optional cover PNG)
        ↓  generate (default still Presenton-backed; native opt-in :8010)
PPTX bytes on disk
        ↓
document.py  →  { slides: [{ text, notes, blocks, geometry? }] }
        ↓                    ↓
slide_preview.py          PresentEditor.tsx
 COM PNG / LibreOffice     <img> raster + HTML hit-box overlay
 else OOXML wireframe      (grid fallback when cx/cy missing)
        ↓
document_io.py writes notes/text back into PPTX (sidecar if round-trip fails)
```

This is **not** the canonical target in `prompts/ZECT_PRESENT_STUDIO_EDITOR_PARITY_ROOT_CAUSE_MASTER.md`. Canvas, thumbnails, and serialization do **not** share one exclusive `PresentationDocument` that is also the editable source of truth. The editable surface is a **screenshot (when COM/LO works) plus CSS boxes**; when COM fails it is **PIL rectangles + labels**.

### Root problem — proved in source (live Presenton not required)

| Symptom | Proof in this tree |
|---|---|
| Template click does not open the real template in Edit | `PresentCreate.tsx` `selectTemplate` loads `mentrixPresentationTemplatePreview` (swatches / layout names / cover data URL) and stays on create/generate. `present-template-use` navigates to `/present/create?template=…`, not an editor loaded from master/layout XML. |
| HTML/OOXML diagnostic boxes instead of a faithful slide | `slide_preview.py` `render_slide_png_bytes` draws filled rectangles + truncated labels. `PresentEditor.tsx` shows `present-editor-preview-kind` = “Approximate layout — PowerPoint did not rasterize this slide” when `previewKind === "ooxml"`. |
| Giant / overlapping placeholders | Overlay uses EMU `%` when `geometry.cx/cy > 0`; **else** `absolute inset-[8%] grid grid-cols-2` (`present-editor-block-overlay`). Missing geometry becomes large tiles over the slide. |
| Thumbnails vs canvas disagree | Thumbs are `mentrixPresentSlidePreview` images; canvas is the same API **plus** an independent HTML overlay. Overlay-only selection is not in the PNG. |
| Group / placeholder inheritance | `extract_slide_blocks` / `pptx_parse` supply per-shape EMU; master/layout inheritance is not a first-class editor model. Unused placeholders can still become overlay hits. |
| COM failure collapses fidelity | `_try_com_png` (win32com) then LibreOffice then OOXML wireframe. `ZECT_LIVE_PPT_COM=0` forces skip. Failure is silent (`except: return False`). |
| Save / reopen / export diverge | `document_io.apply_document_to_pptx` writes text/notes/some visuals; UI copy says sidecar remains SoT if OOXML round-trip fails (`PresentEditor` save status). Overlay edits are not a full shape tree commit. |
| Fixes work for one deck, regress another | Multiple geometry/repair paths (`inspect_and_repair_pptx`, `_copy_missing_geometry`, overlay CSS). No single golden `PresentationDocument` + geometry layer. |

**Falsify next (E1+ only, after review):** a headed run where template click loads master/layout into a canvas whose pixels match PowerPoint export for `prompts/Template.pptx` **without** COM, and thumbs === canvas from the same document state.

## Capability matrix

Columns: **Reference behavior | ZECT behavior | ZECT code path | Root cause | ZECT-native target | Reuse / migrate | Acceptance evidence**

| Capability | Reference (Presenton / local editor) | ZECT now | ZECT code path | Root cause | ZECT-native target | Reuse / migrate | Acceptance evidence |
|---|---|---|---|---|---|---|---|
| Document / slide model | One in-memory deck the canvas edits | Split: PPTX on disk + sidecar slides JSON + raster PNG + overlay blocks | `backend/app/services/mentrix/presentation/document.py`; `frontend/src/components/PresentEditor.tsx` | Document is a DTO around parse/sidecar, not the canvas SoT | Typed `PresentationDocument` (slide, theme/master, relationships, elements) is the only SoT | Keep `document.py` as seed; do not add a fourth model | Golden JSON for real Zinnia slides; round-trip equals parse |
| Master / layout / template | Clicking a template loads masters/layouts as the visual base | Gallery stores `TemplateDefinition` (theme, layout **names**, cover). Generate consumes an id. Edit does not instantiate master XML | `template_definition.py`, `template_importer.py`, `template_registry.py` | Template is metadata + optional PNG, not a bound master/layout tree | `TemplateDefinition` includes masters/layouts/placeholders with EMU; editor slide mode vs template-edit mode | Importer zip-safety stays; extend definition, don’t flatten to screenshot | Template click → editor shows brand chrome + placeholders at real geometry |
| Template upload | Upload PPTX → inspect masters → visual preview → save reusable template | Upload registers a definition; zip bomb checks exist; preview may be cover/swatch | `PresentCreate.tsx` `onUpload`; `template_importer.py` | Upload path is registry + JSON, not “open this PPTX as the editable template” | Same ingest → definition **and** open editor on that definition | Keep zip limits / no path traversal | Upload Zinnia PPTX → preview strip is real slides → Use opens those slides |
| Visual template gallery | Thumbnail of slide 1 / masters | Theme swatch + fonts + layout names + scope/readiness; cover_data_url when present | `PresentCreate.tsx`, `PresentTemplateCardView`, `gallery_visual()` | Gallery is identity/readiness, not raster of the real master | Cards = first-slide (or layout) raster from definition | Do not copy Presenton branding | `zect-present-template-zinnia-executive-v1` shows a real slide thumb |
| Template click / open | Templates → click → editor shows that template | Click selects id + text preview; `present-template-use` → create query param; generate workspace, not Edit-of-template | `PresentCreate.tsx` `selectTemplate`; `PresentTemplatePreview.tsx` | Product IA routes to Generate, not Edit Template | Distinct **Use** (generate) vs **Edit template** (Template Studio) | Keep ZECT IA; add Template Studio later (E3) | Click Zinnia → Edit shows real composition, not names-only |
| Canvas renderer | Shape tree composited at slide aspect | `<img>` of PNG + HTML buttons for hit testing | `PresentEditor.tsx` ~653–730 | Canvas is not a renderer of the document; it is preview + overlay | One geometry layer; invalid geometry fails closed (no full-slide cover) | Do not clone Presenton UI | Headed: no giant boxes; aspect matches EMU slide size |
| Thumbnails | Same compositor, scaled | `mentrixPresentSlidePreview` PNG list | `PresentEditor.tsx` `present-editor-thumbs`; API slide-preview | Thumbs omit overlay; OOXML thumbs are wireframes | Thumbs = downscale of same `PresentationDocument` render | Shared raster/render module | Golden: thumb ≈ canvas for text, image, chart, table, group, Zinnia master |
| Text | Inline edit on the shape | Textarea / notes / AI rewrite; not true on-canvas typography | `present-editor-text`, `present-editor-notes`; `document_io._write_slide_text` | Text is slide-level blob + notes, not runs in placeholder trees | Element model: title/body/bullets with alignment/overflow | Keep notes/rehearse as ZECT extra | Edit title in canvas → save → reopen → PPTX has that run |
| Image | Crop/fit/move/resize | Parse flags `has_image`; overlay hit; save path can drop/replace pictures | `inspect_pptx_visuals`; `document_io._drop_pictures` | Images are media + optional overlay, not first-class crop/transform | Image element with crop/aspect | Keep media zip members | Replace image, aspect preserved, export matches |
| Shape | Native shapes | Overlay borders; OOXML fallback is labeled rects | `slide_preview.render_slide_png_bytes`; overlay CSS | Shapes are diagnostics unless COM raster exists | Shape fill/stroke/z-order in document | No CSS-only “fixes” | Move/resize persists in PPTX |
| Chart | Editable chart data | `present-editor-block-hit-chart`; python-pptx / visual fallback | `visual.py`, `PresentEditDataTable` | Chart is prompt heuristic + partial OOXML | Chart data model; no invented series | Keep critic/repair **after** model exists | Edit data → save → PowerPoint shows same values |
| Table | Editable grid | Table block + `_update_table` | `document_io._update_table` | Table update is best-effort on existing tbl | Table rows/cols/text in document | Keep | Add row → export |
| Diagram / group | Group transforms | Partial EMU; groups not a real editor object | `pptx_parse` / overlay | Group parent transforms not a geometry layer | Group + child offsets | — | Grouped Zinnia lockup matches PPTX |
| Selection / drag / resize / layers | Full | Click overlay; no drag/resize/z-order | `present-editor-block-hit-*` | Hit-test only | Selection bounds, drag/resize, layers | — | Headed keyboard + mouse |
| Undo / redo | Stack on document | In-memory slide clone stack + local persist | `PresentEditor.tsx` undo/redo | Undo is React state, not document ops | Command stack on `PresentationDocument` | Keep Ctrl+Z UX | Undo survives save/reopen policy |
| AI edit | In-editor rewrite | `mentrixPresentSlideAi` + chart heuristic | `applyAi` | AI writes copy/notes, not the shape tree | AI returns document patches | Keep attach_excerpts | AI edit visible on canvas and in PPTX |
| Persistence | One file | Sidecar + optional OOXML write | `mentrixPresentSaveNotes` / `document_io.py` | Dual SoT by design today | Single write of document → PPTX | Sidecar only as crash recovery | Save → reopen bytes equal editor state |
| PPTX serialization | Native save | python-pptx + inspect/repair | `document_io.py`, `final_pptx_inspector.py` | Serializer is not the inverse of a full document | Explicit serializer from document | Keep zip validation | PowerPoint opens; no repair-needed for golden decks |
| Preview / raster | Editor compositor | COM → LO → OOXML wireframe | `slide_preview.py` | Raster is a **fallback chain**, not the editor | Raster is optional proof; editor never depends on COM | COM/LO as **export proof only** | `ZECT_LIVE_PPT_COM=0` still looks like the real slide |
| Export | Download PPTX | Browser download + Electron open-path | `present-editor-export`; Electron helpers | Fine as a shell; fidelity is the serializer | Same document → file | Keep Electron open | Export hash/golden |
| Browser / Electron | Browser app vs desktop | Vite + Electron; Voice/Zoom are ZECT-only | `PresentStudio.tsx`, Electron present routes | Not the fidelity bug | Keep ZECT desktop extras | Do not copy Presenton | Same editor in both shells |

## Presenton vs ZECT (from `ZECT_PRESENT_UX_PARITY_GAP.md`, not re-cloned)

Presenton remains a **behavioral** benchmark only. Do not copy branding, pixels, or proprietary code. If any Presenton file is proposed for reuse later, E1+ must record repo, commit, paths, license, and obligations **before** reuse. This E0 recommends **ZECT-native document + geometry**, not a Presenton embed.

Default generate is still Presenton-backed (`ZECT_PRESENTATION_PROVIDER` native is opt-in `:8010`). Editor work must not assume Presenton is the canvas.

## Files inspected (read-only)

- `frontend/src/components/PresentEditor.tsx`
- `frontend/src/pages/present/PresentStudio.tsx`
- `frontend/src/pages/present/PresentCreate.tsx`
- `frontend/src/pages/present/PresentTemplatePreview.tsx`
- `backend/app/services/mentrix/presentation/document.py`
- `backend/app/services/mentrix/presentation/document_io.py`
- `backend/app/services/mentrix/presentation/slide_preview.py`
- `backend/app/services/mentrix/presentation/template_definition.py`
- `backend/app/services/mentrix/presentation/template_importer.py`

## E0 verdict

The unacceptable editor behavior is **architectural**, not a missing CSS tweak:

1. **Template selection is an id + gallery preview, not loading a visual master/layout into Edit.**
2. **The “canvas” is a raster (COM/LO) or an OOXML wireframe, with HTML boxes on top.** COM failure therefore *is* the editor.
3. **There is no single `PresentationDocument` driving thumbs, canvas, save, and export.**

E1 should start with document + geometry unification and golden tests on real Zinnia slides. **Do not** add another isolated placeholder/CSS workaround.

**STOP.** E1–E12 wait for human approval of this E0.
