# ZECT Present vs Presenton — UX Parity Gap

**Date:** 2026-08-14  
**Reference only.** Do not copy Presenton branding, pixels, or proprietary code.  
**Presenton:** `http://127.0.0.1:5000/` (local admin login; **do not extract secrets**).  
**ZECT Present (product default):** Vite `http://127.0.0.1:5173/present` → API `:8000` (Presenton-backed).  
**Native opt-in:** API `:8010` `ZECT_PRESENTATION_PROVIDER=zect_native`.

## Comparison

| Area | Presenton (reference) | ZECT now | Gap | ZECT action |
|------|----------------------|----------|-----|-------------|
| Home | Creation-first after login | Prompt + visual gallery + Generate CTA | Closer than name-only cards | Keep ZECT IA |
| Visual templates | Thumbnail masters | Theme swatch + fonts + layout names + scope/readiness | Not a raster of slide 1 yet | TemplateDefinition swatches; real PPTX thumbs later |
| Prompt / docs / project | Presenton sources | Prompt + upload template; project context weaker | Attach/project context | P1 |
| Progress | Wizard stages | Understanding → story → visuals → compose → quality → repair → finalize | Timer-based until generate returns | Bind to native telemetry when on `:8010` |
| Quality | Presenton internal | QualityCritic + repair on native; Fast-Basic labeled degraded | Default provider still Presenton | Human A/B before default switch |
| Editor | Full editor | `present-editor` after deck path | Weaker than Presenton | Keep; do not clone UI |
| Notes / rewrite | In-editor | Notes + rewrite box | Split | Unify after generate |
| Voice / Zoom | N/A | Voicebox + Electron Zoom | ZECT-only | Keep |
| Export | Download | Path + Open PPTX (Electron) | Browser vs desktop | Keep Electron for desktop |

## Headed this session

S7.7 UX spec compares ZECT `/present` vs Presenton landing. Presenton templates API is **401** until the operator logs in with **their** local admin (documented example username in `docs/PRESENTON_LOCAL.md` is not a password dump).

Native generate from the **same** Vite origin is wired via `sessionStorage.zect_api_origin` (loopback only) + `ZECT_NATIVE_HEADED=1`. It was **not** executed to LLM PASS in this continuation.

## Stop

Do not treat a valid PPTX as product PASS. Do not score blinded A/B here.
