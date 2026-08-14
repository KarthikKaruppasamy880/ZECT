# ZECT Native Presentation S6.5 — Visual-content parity

**Date:** 2026-08-14  
**Branch:** `feat/present-s65-visual-parity`  
**Against:** `develop` `64e4564` (PR #151 merge)  
**Presenton:** remains **default**. Native remains opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native`). Presenton adapter/runtime/config were **not** removed.

## Verdict

**S6_5_PARTIAL** — canonical visual blocks, AssetResolver, editable PPTX charts/tables/images, mixed-content layout, Zinnia-verified native generate, editor round-trip, and headed export/reopen are implemented and tested. Live clone/stock/No Narration on a native-default product path is **not** claimed. S7 live Presenton-vs-native benchmark is **not** started (requires this PR to be human-merged).

## Independent status

| Gate | Status | Evidence |
|------|--------|----------|
| TEXT | PASS | Placeholder title/body; `test_native_renderer`, `test_presentation_document` |
| NOTES | PASS | OOXML notes round-trip; S6 re-prove `test_s6_native_reprove` |
| TABLES | PASS | Canonical `TableBlock` → real `a:tbl`; overflow truncated with `table_truncated` / `table_too_large`; editor TSV |
| IMAGES | PASS | `AssetResolver` PNG/JPEG/GIF/WEBP; SVG/URL/HTML rejected; embed `ppt/media`; editor upload/replace/delete |
| CHARTS | PASS | python-pptx column/bar/line/pie/donut; example provenance; `ppt/charts`; editor title/categories |
| LAYOUT_SELECTION | PASS | `layout.choose_layout` + TemplateDefinition BODY geometry; overflow/collision recorded, not silent-drop |
| ZINNIA_FIDELITY | PASS | Native generate with ready master → `zinnia_verified=true`; never silent `modern` |
| USER_TEMPLATE_FIDELITY | PASS | `test_s6_user_template_native_generate_no_presenton` |
| EDITOR | PASS | `PresentVisualBlocks` + headed `present-s65-visual.spec.ts` |
| EXPORT | PASS | Headed save → download → reopen chart title + image block |
| CLONE_VOICE | PARTIAL | Unit cross-user denial + native TTS independence PASS. Live clone ≥2 slides / one `audio_owner` / Disconnect FSM **not** re-run on native path this session (Voicebox live not started; not downgraded to a false PASS) |
| STANDARD_VOICE | PARTIAL | Stock options remain in Present UI (`present-editor-export`); not re-proven narrating a native-generated deck live |
| NO_NARRATION | PARTIAL | `voice=none` still in Present UI; not re-proven on native generate this session |
| NO_PRESENTON_NATIVE_CALL | PASS | `generate_presentation` patched `assert_not_called` on native Zinnia, user-template, and visual generate |

## Architecture

Canonical kinds live in `blocks.py`, not as renderer helpers: `text | image | chart | table | metric | quote | diagram`. Each has stable id, slide, layout intent, geometry, content, provenance, validation. `visual.py` paints; `layout.py` places; `charts.py` builds editable charts; `asset_resolver.py` is the only image store (no second Document/Web system, no URL fetch).

## Security

- Images: magic-byte MIME, 8MB cap, PIL decode + pixel cap, SVG/active XML rejected, URL filenames rejected, owner-scoped `sha256` paths, cross-user `asset_not_found`.
- RESTRICTED still fail-closed before Presenton (`restricted_external_provider`).
- LLM still Model Gateway only (`planner.py` → `llm_phase._chat`).
- Example chart/table/metric data is provenance-tagged `example` / `generated`.

## Tests

- Pytest: `test_s6_native_reprove.py`, `test_asset_resolver.py`, `test_visual_parity.py` plus frozen presentation suite — PASS
- Headed: `e2e/present-s65-visual.spec.ts` — PASS (2026-08-14)
- Gate 0 Presenton-default headed smoke: `core-ux-hygiene`, `present-product`, `present-editor-export` (retry after login race) — PASS on `64e4564`

## Mentrix Ultra Review (branch-introduced)

| ID | Sev | Finding | Classification | Disposition |
|----|-----|---------|----------------|-------------|
| UR-S65-1 | Critical | Image URL fetch / XSS via SVG | ALREADY_FIXED | No URL fetch; SVG/HTML/DOCTYPE rejected; magic+PIL |
| UR-S65-2 | Critical | Cross-user asset read | ALREADY_FIXED | Load only from owner directory; 404 |
| UR-S65-3 | Critical | Native generate calls Presenton | ALREADY_FIXED | Service/provider tests assert not called |
| UR-S65-4 | Major | Invented KPIs presented as fact | ALREADY_FIXED | Example provenance + titles |
| UR-S65-5 | Major | Large tables render unreadable | ALREADY_FIXED | Truncate/reject with validation errors |
| UR-S65-6 | Major | Silent drop of overflow visuals | ALREADY_FIXED | `layout_overflow` / collision errors; not painted |
| UR-S65-7 | Minor | Editor picture replace uses private `shape._element` | OUT_OF_SCOPE | Same python-pptx constraint as existing `_sldIdLst` slide clear |

## Not in this PR

- S7 live Presenton vs ZectNative benchmark / blinded A/B
- S8C default switch
- S8D Presenton removal
- KV cache, Graphify, OCR/XLSX, extra agents
