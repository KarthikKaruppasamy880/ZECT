# ZECT Present — product final acceptance (E12)

**Reviewed:** 2026-08-25 — final closure tranche on `feat/present-product-ready-closure` atop merged PR **#187**.

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

Backend COM proof on the real Zinnia clone (11 slides, slide-0 kinds: image/shape/text) **PASS** locally (`ZECT_LIVE_PPT_COM=1`): save/reopen, export validate, open-without-repair, COM raster export. Headed/Electron viewport matrix + Presenter **full live audio** + COM-vs-canvas raster golden require opt-in headed run (`ZECT_LIVE_PRESENT_READY=1`).

| Phase | Status | Evidence |
|---|---|---|
| E0–E7, E9–E10 | Core | On `develop` after #186+#187 |
| E5–E6 | Core | `PresentDocumentCanvas` shared with thumbs |
| E8 | Partial→Core* | Local COM open-without-repair + raster on real Zinnia clone; COM-vs-canvas SSIM proxy in `present_product_fidelity_proof.py` when canvas PNG supplied |
| E11 | Partial | API grounded scripts for all slides on mixed deck; live stock/clone **full audio** = `ZECT_LIVE_VOICE_STOCK=1` |
| E12 | Partial | Opt-in `present-product-ready-acceptance.spec.ts` — 1280–1920 matrix; Electron 20+ / maximize not re-run this SHA |

### Local backend proof (2026-08-25)
- `ZECT_LIVE_PPT_COM=1 python backend/scripts/present_product_fidelity_proof.py` → `verdict: true`
- Artifacts: `test-results/present-product-ready/fidelity-proof.json`, `zinnia-com-representative.png`

### Opt-in headed proof (not CI — `.zect/` gitignored)
```bash
# Terminal 1: API + frontend per docs/RUNBOOK_LOCAL.md
# Terminal 2:
set ZECT_LIVE_PRESENT_READY=1
set ZECT_LIVE_PPT_COM=1
cd frontend && npm run test:e2e:present-ready
# Optional full Presenter audio:
set ZECT_LIVE_VOICE_STOCK=1
```

## Still required for `ZECT_PRESENT_PRODUCT_READY`

1. Headed run of `present-product-ready-acceptance.spec.ts` with evidence in `test-results/present-product-ready/` (all tests PASS, not skipped)
2. COM-vs-canvas raster proxy ≥ threshold on representative Zinnia slide (script enforces when canvas PNG captured)
3. Presenter **full audio** completion on mixed ≥7-slide deck (`ZECT_LIVE_VOICE_STOCK=1` or live clone + Voicebox)
4. Electron viewport matrix including maximize/restore and 20+ slide rail
5. Mandatory CI green on closure PR + Ultra Review 0 Critical/High

Green `present-product` / `present-document-canvas` e2e alone is **not** visual-fidelity PASS.
