# ZECT Present S4 Acceptance — Native PPTX renderer

**Date:** 2026-08-14  
**Branch:** `feat/present-s4-native-renderer`  
**Library:** python-pptx **1.0.2 MIT** in `backend/pyproject.toml` and `backend/requirements.txt`  
**Presenton:** remains **default**. Native is experimental (`ZECT_PRESENTATION_PROVIDER=zect_native`).

## Verdict

**S4_PASS (experimental)** — native provider renders a validated PPTX from PresentationPlan + TemplateDefinition. Charts/images remain **PARTIAL**. Default generate is still Presenton.

## Tests

`test_native_renderer.py` + updated service test: native generate writes a valid PPTX, does not call Presenton, `zinnia_verified=true` only when a Zinnia master TemplateDefinition is applied. Unmapped Zinnia → 409 `TEMPLATE_NOT_READY` (never silent `modern`).

## Honest limits

- Charts, images remain **PARTIAL**. Tables are optional.
- XML entity expansion is rejected (`<!DOCTYPE` / `<!ENTITY`) without adding `defusedxml`.
- `poetry.lock` is regenerated so Docker `poetry install` includes python-pptx 1.0.2.
