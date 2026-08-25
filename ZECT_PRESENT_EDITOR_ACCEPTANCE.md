# Present generate + native Studio editor

ZECT Present matches the Presenton operator flow on **Zinnia/org/user PPTX masters**. Community packs are not imported. No Presenton/Gamma branding in the UI. PPTX + python-pptx stay source of truth (`ZECT_PRESENTATION_PROVIDER=zect_native`). Do not iframe `:5000`.

## Generate + templates

- Route: `/present/create` — prompt, attach files, slide count, language, **PNG gallery** (Zinnia / organization / uploads only)
- Smart (confirm outline) or Standard, Auto slides, then **Generate**
- Generate lands on **Present Studio** (`/present/d/:deckId/edit`), not Review
- Upload auto-selects the new master; gallery cover PNG renders even when `native_ready` is false
- Preview route `/present/templates/:id` shows a slide PNG strip of the master
- Fast-Basic requires an explicit **Draft without model** checkbox (never silent)

## Present Studio

Dedicated full-viewport editor: `/present/d/:deckId/edit`

- Dashboard recent cards, Blank, and Import open Studio
- Review (`/present/d/:deckId`) stays quality + Rehearse/Export handoff; **Open Studio** is the primary edit
- Chrome: deck title, Undo/Redo, Save (primary), Export PPTX, shortcuts
- Sticky save status: Saved / Saving / Unsaved
- Right rail: **AI | Blocks | Texts | Charts | Tables | Images | Elements**
- Charts (click selected chart to change type, else insert): Bar, Horizontal Bar, Stacked, Horizontal Stack Bar, Line, Pie, Area, Donut, Scatter, Radar, Polar, Progress, Gauge
- Double-click chart/table → **Edit Data Table** → Save writes OOXML then refreshes slide PNG
- Canvas prefers a real raster (Windows PowerPoint COM when `ZECT_LIVE_PPT_COM=1`, else LibreOffice if installed). Otherwise OOXML layout preview is labeled **Layout preview — install PowerPoint for true slides**. Response header `X-Zect-Preview-Kind`: `com` | `libreoffice` | `ooxml`
- Overlay uses EMU geometry from `p:sp` / `p:pic` / `graphicFrame` (`data-block-id`). Fake 2-column CHART/SHAPE grid only when geometry is missing
- After chart type-change + Save, cached PNG is busted so a bar/radar is visible when COM/LibreOffice can rasterize
- AI chat is object-aware (current slide + selected block). No invented KPIs — attached docs / ContextPack only
- Speaker notes sit behind a control in Studio; they are not the primary canvas UI
- Export stays PPTX
- Gallery tabs: **Built-in** = Zinnia ids with master cover PNGs; **Custom** = org/user uploaded PPTX. No Presenton Community packs and no `:5000` iframe

## E4–E6 editor (this tranche)

- Zoom in / out / fit (`present-editor-zoom-*`); canvas frame width follows zoom
- Overlay uses shared `geometryPercentStyle`; invalid geometry does not cover the slide
- Select, drag, resize handle, keyboard nudge (arrows on a selected object), Delete object, Esc clears selection
- Layers list + object property EMU fields; thumbs reuse the same EMU overlay (`present-editor-thumb-canvas-*`)
- Undo/redo and Save remain slide-document + OOXML round-trip (`document_io.apply_document_to_pptx` atomic temp replace)

**Not PASS:** true on-canvas typography, crop/aspect image tools, PowerPoint-class snapping, COM-free pixel golden vs Zinnia masters.

