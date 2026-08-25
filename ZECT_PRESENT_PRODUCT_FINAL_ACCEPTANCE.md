# ZECT Present — product final acceptance (E12)

**Reviewed:** 2026-08-25 — closure tranche on `feat/present-product-ready-closure` atop merged PR **#187**.

| Milestone | SHA |
|---|---|
| **#186 merge (`develop` base)** | `5d916f194838e35c9e376b6179ada26604d1578c` |
| **#187 merge (canonical `develop`)** | `75aebb15bfea52df4c31d5a41d8a4de77a03ac87` — merged 2026-08-25T11:23:59Z |

## Real Zinnia master (located — not synthetic)

| Field | Value |
|---|---|
| **Path** | `.zect/present-templates/masters/zinnia-executive-v1.pptx` (also `~/Documents/zinnia-executive-v1.pptx`, same bytes) |
| **SHA256** | `74cb1f7a50c2dcd3ce6c1a41547c45f9666fcb1e353801b87a174c63ecf70dc2` |
| **Bytes** | 12,275,249 |
| **Definition** | `.zect/present-templates/definitions/zinnia-executive-v1.json` — 18 layouts, accent2 `#FF7500`, `native_ready: true` |
| **Fallback `prompts/Template.pptx`** | 212 KB — **not** used for Zinnia fidelity PASS |

## Verdict: `ZECT_PRESENT_PRODUCT_PARTIAL`

Root-cause fix landed for Zinnia hero image (`ppt/media/image12.png` ~1.93 MB excluded by `_MAX_PART_BYTES`). Headed browser + Electron acceptance PASS locally with real master. **Clone-voice full Presenter audio** and **backend process restart** remain open.

| Phase | Status | Evidence |
|---|---|---|
| E0–E7, E9–E10 | Core | On `develop` after #186+#187 |
| E5–E6 | Core | `PresentDocumentCanvas` shared with thumbs |
| E8 | **PASS (local)** | COM open-without-repair; COM-vs-canvas SSIM proxy **0.4938** (≥ 0.42); save/reopen text OK |
| E11 | **Partial** | Grounded scripts 8/8 slides; **stock:nova full audio PASS** (`ZECT_LIVE_VOICE_STOCK=1`); **clone voice not re-run** (Voicebox offline at `127.0.0.1:17493`) |
| E12 | **PASS (local opt-in)** | Browser viewports 1280–1920; Electron 22-slide rail + maximize/restore + restart reopen |

### Root cause fixed (this PR)

- `backend/app/services/pptx_parse.py`: `_MAX_MEDIA_BYTES = 8MB` for `ppt/media/*` parts so large Zinnia hero resolves to `asset_id` instead of being dropped.
- Regression: `test_zinnia_large_hero_image_resolves_to_asset_id`

### Local proof (2026-08-25)

**Backend COM (`ZECT_LIVE_PPT_COM=1`):**
```bash
python backend/scripts/present_product_fidelity_proof.py test-results/present-product-ready/zinnia-canvas-representative.png
```
→ `com_vs_canvas_ssim_proxy: 0.4938`, `com_vs_canvas_pass: true`, `repair: false`

**Headed browser + Electron (`ZECT_LIVE_PRESENT_READY=1`):**
```bash
set ZECT_LIVE_PRESENT_READY=1
set ZECT_LIVE_PPT_COM=1
set ZECT_LIVE_VOICE_STOCK=1
cd frontend && npm run test:e2e:present-ready
```
→ 6 browser + 1 electron tests PASS (2026-08-25)

| Artifact | Path |
|---|---|
| Browser evidence | `test-results/present-product-ready/evidence.json` |
| COM raster | `test-results/present-product-ready/zinnia-com-representative.png` |
| Canvas raster | `test-results/present-product-ready/zinnia-canvas-representative.png` |
| Fidelity JSON | `test-results/present-product-ready/fidelity-proof.json` |
| Electron evidence | `test-results/present-product-ready-electron/evidence.json` |
| Viewport shells | `test-results/present-product-ready/shell-*.png` |

### Still required for `ZECT_PRESENT_PRODUCT_READY`

1. **Clone voice Presenter full audio** — start ZECT Voicebox (`services/zect-voicebox/scripts/up.ps1`, `models_ready: true`), re-run with saved clone (Karthik) on ≥7-slide mixed deck; prove no overlap/cutoff/skips.
2. **Backend process restart + reopen** — prove edited Zinnia deck survives API stop/start (Electron restart reopen PASS; browser reload PASS; cold API restart not yet captured).
3. **CI green** on closure PR (Zinnia master gitignored — fidelity tests remain opt-in locally).

Green `present-product` / synthetic PPTX / canvas-only screenshots / “PowerPoint opened” alone are **not** visual-fidelity PASS.

## Opt-in commands

```bash
# Terminal 1: API + frontend per docs/RUNBOOK_LOCAL.md
# Terminal 2:
set ZECT_LIVE_PRESENT_READY=1
set ZECT_LIVE_PPT_COM=1
set ZECT_LIVE_VOICE_STOCK=1   # stock TTS; requires OPENAI_API_KEY in backend/.env
cd frontend && npm run test:e2e:present-ready
```
