# ZECT Present Template Gallery Acceptance

**Date:** 2026-08-14  
**Gate:** **PARTIAL** — visual cards from TemplateDefinition; not photographic slide-1 thumbs.

## Required vs shipped

| Requirement | Status |
|-------------|--------|
| Thumbnail | Theme color strip from TemplateDefinition (`thumbnail_kind=theme_swatch`) |
| Hover/focus/selected | Border + ring on selected card |
| ZECT / ORG / MY scope | Chip from `scope` |
| Title + style description | `name` + `preview` |
| Representative layouts | First layout names + `layout_count` |
| Colors / fonts | `visual.colors`, `visual.fonts` |
| Readiness | `READY` / `TEMPLATE_NOT_READY` |
| Preview | Preview panel; errors from `visual.error` (e.g. `definition_missing`) |
| Use / Generate | Primary `Generate presentation` (`zect-present-continue-generate`) |
| No Presenton UUIDs | `provider_uuid_hidden`; gallery_visual strips bindings |

## API

`GET /api/mentrix/presentation/templates` and `POST .../templates/preview` include `visual` and `readiness`.

`gallery_visual()` in `template_definition.py` is the single public preview helper.

## Test

`test_gallery_visual_hides_provider_uuid_and_exposes_theme` in `test_s77_quality_repair.py`.

## Remaining

Rasterize cover + layout thumbs from the master PPTX (still ZECT-owned, no Presenton UUID). Headed screenshot baselines optional, not sole acceptance.
