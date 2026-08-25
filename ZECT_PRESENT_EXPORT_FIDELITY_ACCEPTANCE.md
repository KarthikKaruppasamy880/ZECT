# ZECT Present — export fidelity acceptance (E8 / E9)

## Save / reopen

`open → edit text / notes / chart-table data / move object → Save → close → reopen`.

- Save writes notes sidecar first, then `apply_document_to_pptx` via a `.zect-tmp.pptx` + `os.replace` (atomic).
- If OOXML round-trip fails, sidecar remains source of truth and the UI says so. That is **PARTIAL**, not silent success.
- Parse returns `document` (schema 2) plus `slides` for the editor.

## Export

- Quality gate (`mentrixPresentQualityGate`) inspects the PPTX and attaches `document_critic` (advisory; critic FAIL does **not** auto-block export).
- Inspector hard findings still block export (`export_blocked` / `hard_blocked`). Warnings can be accepted when allowed.
- Download is the allowlisted PPTX bytes.

## Remaining

- Full COM golden (`PresentationDocument → PPTX → PowerPoint COM → raster`) is **BLOCKED_EXTERNAL** without `ZECT_LIVE_PPT_COM=1` and a headed machine.
- Overlay geometry edits persist in the document/sidecar; not every drag is proven as a python-pptx shape-tree rewrite for every kind.
- PowerPoint “needs repair” is not re-proven in this tranche on a live desktop.
