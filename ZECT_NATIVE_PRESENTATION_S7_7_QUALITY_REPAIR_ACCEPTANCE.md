# ZECT Native Presentation S7.7 Quality Repair Acceptance

**Date:** 2026-08-14  
**Presenton default:** unchanged. Native remains opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native` on `:8010`).  
**S8C / S8D:** not started.  
**Official S7 verdict:** still **`NATIVE_NOT_READY`** until the human blinded scorecard is completed. This session does not recompute it.

## Gate

**`READY_FOR_FRESH_HUMAN_AB_REVIEW`** for V2 Present quality path (headed native LLM+QualityCritic proven; fresh packs ready). Official S7 stays **`NATIVE_NOT_READY`** until you score. Quality defects are treated as product bugs (critic/repair). Automated critic PASS is **not** S7 READY. Do not fill scores in this session. Do not read or reveal `PRIVATE_MAPPING.json`.

## Observed defects (product quality, not “valid PPTX”)

| Defect | Root cause | Repair |
|--------|------------|--------|
| Unwanted / placeholder tables (`Workstream \| Status \| Owner` + Watch/A/B) | Keyword `roadmap`/`workstream`/`decision` mapped to TABLE; `ensure_visual_blocks` invented rows from prose | TABLE only with real delimited/structured rows; prose stays bullets |
| Title/body collision and cramped content | `content_region()` used **layout[0]**; body fill + visual paint in the same box | `LayoutComposer` uses the **selected** layout placeholders; title-safe visual region; clamp instead of drop |
| Repetitive layouts | First matching “title and content” / Title Page | Score Zinnia layout names; penalize reuse |
| Truncated text | Long bullets written into placeholders | Critic `truncated_text` → shorten / split (max 6 bullets, 140 chars) |
| Invented names/dates | Planner/example copy | Grounding scrub → `TBD`; Fast-Basic still labeled degraded |
| Irrelevant image | Keyword/figure default | IMAGE only when the slide story supports it; critic drops otherwise |
| Chart from a lone “Q3” token | `\d` anywhere counted as numeric evidence | CHART needs a series (≥2 categories) or an explicit example/illustrative request |
| Excessive whitespace | Wrong body box from the first master layout | Compose from selected placeholders; flag sparse occupancy |

## Semantic content-selection

`SlideIntent` → `TEXT | BULLETS | METRICS | IMAGE | CHART | TABLE | COMPARISON | TIMELINE | PROCESS | ARCHITECTURE | DIAGRAM`

- **TABLE:** only when the plan/source has consistent columns/rows (pipe/tab or an existing table block). Never turn ordinary bullets into placeholder tables.
- **CHART:** quantitative series **or** the user asked for illustrative/example data.
- **IMAGE:** supports the slide story (figure/screenshot/authorized asset). Decorative mismatch is dropped.

## Grounding / anti-hallucination

Facts classify as `SOURCE_GROUNDED | USER_PROVIDED | PROJECT_GROUNDED | GENERATED_EXAMPLE | UNKNOWN`.

Missing owners/dates/KPIs are omitted or `TBD`. Invented person-name patterns and ungrounded calendar dates are scrubbed. Speaker notes use the same policy. Example charts/tables must keep example provenance.

## LayoutComposer

Input: `TemplateDefinition + SlideIntent + ContentBlocks + VisualPlan`.  
Output: `master_layout_name`, title/body/visual regions from **that** layout’s placeholders (nested `geometry`), not `layouts[0]`.

Zinnia 16:9 definition used locally: `.zect/present-templates/definitions/zinnia-executive-v1.json` (Arial, accent2 `#FF7500`, SHA256 `74cb1f7a50c2dcd3ce6c1a41547c45f9666fcb1e353801b87a174c63ecf70dc2`). `zinnia_verified=true` remains necessary and **not** sufficient for quality PASS.

## PresentationQualityCritic

Per slide: `PASS | REPAIRABLE | FAIL`.  
Checks: overlap, out-of-bounds, title collision, truncation, placeholder/inappropriate table, inappropriate chart, irrelevant image, repeated layout, whitespace/cramp, ungrounded names.

Deck metrics on native generate: `overlap_count`, `out_of_bounds_count`, `clipped_text_count`, `min_font_size`, `text_density`, `whitespace_ratio`, `repeated_layout_count`, `table_appropriateness`, `image_relevance_status`, `ungrounded_fact_count`, `repair_attempts`, `final_quality_status`.

## Bounded repair loop

`compose → critic → repair → recompose` up to 3 attempts. Repairs: table→bullets, drop irrelevant image/chart, shorten/split, change layout, restack title/body.

LLM quality path: remaining hard FAIL (`overlap`, OOB, placeholder table, remaining invented names) returns `ok=false`, `error=quality_failed`, HTTP 422 — not a success deck.  
**Fast-Basic / `HEURISTIC_FALLBACK` stays `ok=true` and labeled `degraded`.**

## Tests / real Zinnia / headed

| Check | Result |
|-------|--------|
| `test_s77_quality_repair.py` (roadmap≠placeholder table, collision, truncation, repeated layouts, irrelevant image, whitespace, invented name/date, chart mismatch, repair loop, real Zinnia compose+render) | **15 passed** |
| `test_s75_quality.py` + `test_visual_parity.py` + `test_s7_parity_benchmark.py` (live skipped) | **27 passed, 1 skipped** with the S7.7 set |
| Real Zinnia master render | **PASS** — `masters/zinnia-executive-v1.pptx` (~12.3 MB) + definition; grounded pipe table kept; prose roadmap has no table |
| Headed UX comparison | **PASS** — `frontend/e2e/present-s77-quality.spec.ts` with `ZECT_LIVE_S77=1` (2 passed, native generate skipped on `:8000`) |
| Headed native generate on `:8010` | Skipped this run (`VITE_API_URL` is Presenton-default `:8000`). Native API on `:8010` was restarted with S7.7 code for optional follow-up |

Screenshots: `test-results/s7-parity/headed-s77/` (gitignored).

## Local product comparison (keep running)

| Product | URL / how | Status |
|---------|-----------|--------|
| ZECT API (Presenton **default**) | `http://127.0.0.1:8000/healthz` | **200** |
| ZECT browser Present | `http://127.0.0.1:5173/present` | **200** (Vite). Login first. |
| ZECT API docs | `http://127.0.0.1:8000/docs` | up |
| ZECT Electron | `electron`: `npm run start:dev` with `ZECT_DEV=true`, `ZECT_DEV_URL=http://127.0.0.1:5173`, `ZECT_API_URL=http://127.0.0.1:8000` | **running**; Present = Mentrix → Present (same `/present` UI) |
| Native opt-in API | `http://127.0.0.1:8010/healthz` (`ZECT_PRESENTATION_PROVIDER=zect_native`) | **restarted** with S7.7 critic/repair. Not the product default. |
| Presenton | `http://127.0.0.1:5000/` | **200**. `GET /api/v1/ppt/template/all` → **401** (login required, not `428 setup_required`) |
| Voicebox | `http://127.0.0.1:17493/health` | **200** |

Do not point the product default at `:8010`. Comparison generate in the browser uses Presenton via `:8000`.

### Safe Presenton local login / setup (no existing secrets)

This session did **not** print, extract, or read Presenton passwords, tokens, Docker env, `.env` values, or browser storage.

1. Open `http://127.0.0.1:5000/` in your browser.
2. **First-run / create-admin** (only if the UI or Mentrix reports `428 setup_required`): create a **local-dev-only** admin in that UI. Put the **same** username and password **you just typed** into `backend/.env` as `PRESENTON_USERNAME` / `PRESENTON_PASSWORD`. Restart the ZECT API on `:8000`.
3. **Login screen** (this environment: homepage 200 + templates 401): sign in with the local Presenton account **you** configured. Docs example username is `zect-presenton` (`docs/PRESENTON_LOCAL.md`). The password is whatever you set when creating that admin or starting the container — recover it from **your** password manager, not from Cursor, `docker inspect`, or `.env` dumps.
4. Optional: set `PRESENTON_API_KEY` instead of username/password (you create/paste the key; do not ask the agent to extract an existing one).
5. Point ZECT at Presenton with `PRESENTON_BASE_URL=http://127.0.0.1:5000` plus the credentials **you** placed in `.env`. Restart `:8000` after edits.
6. ZECT app login is separate (Mentrix login form). Use your ZECT local user. Do not paste `.env` into chat.

If you forgot the Presenton password: use Presenton’s own reset/create-user if offered. Do not use `docker inspect` to recover `AUTH_PASSWORD`. Recreating the container wipes local Presenton data.

## Headed UX comparison

Capability reference only. Do **not** copy Presenton pixels or branding into ZECT.

| Capability | Presenton behavior | ZECT behavior | Gap | Required ZECT fix |
|------------|-------------------|---------------|-----|-------------------|
| Entry / auth | Local UI at `:5000`; templates API 401 until session login | ZECT login then `/present`; provider hidden | Separate IdPs | Keep; never embed Presenton chrome |
| Prompt | Presenton has its own prompt/outline flow (login-gated; landing screenshot this run was a loading graphic, not a branded capture) | Gallery prompt + Generate panel textarea (`present-deck-prompt`) | ZECT prompt is on New + Generate | Optional: persist gallery prompt into Generate (already localStorage-backed) |
| Outline / planning | Presenton plans inside its app | Model Gateway plan on native; Presenton generate on default | Native plan not shown as an outline stepper | Later: show plan beats before generate (not S8C) |
| Template selection | Presenton masters inside Presenton | Zinnia / Org / My gallery; canonical `zinnia-executive-v1` | Good | Keep registry mapping; never silent `modern` |
| Generate progress | Presenton progress UI | Status line on Present Deck; Fast-Basic + Retry Gateway | Weaker progress than a dedicated wizard | Progress % / stage labels |
| Editor / thumbnails | Presenton editor after generate | `present-editor` after a deck exists; thumbs on path fill | Editor false until generate | Expected; generate then edit |
| Text / notes | Presenton notes | Notes field + rewrite box + editor notes | Split across gallery vs panel | Unify notes into editor after generate |
| Images / charts / tables | Presenton visual pipeline | Native critic+composer; Presenton default still used for product generate | Native quality now gated; default still Presenton | Human A/B before switching default |
| Rewrite / regenerate | Presenton regenerate | Fast-Basic, Retry Gateway, rewrite textarea | No per-slide rewrite in panel | Per-slide rewrite after editor is open |
| Export | Presenton download | Path + Open PPTX (Electron) + editor export | Browser vs desktop | Keep Electron for PowerPoint/Zoom |
| Errors | Presenton HTTP errors | Lifecycle pill, status, `quality_failed` on native FAIL | Native 422 is new | Surface critic findings in the status line |
| Voice / Zoom | N/A in Presenton | Voicebox narrate + Zoom join | ZECT-only | Keep |

## Security

- RESTRICTED/CONFIDENTIAL still blocked before LLM.
- Untrusted context wrapping unchanged.
- No secrets committed. `.zect/present-templates/` and `test-results/` remain gitignored.
- Presenton credentials were not extracted.

## V2 routing fix (not a default-provider switch)

Product browser remains Presenton-backed `:8000`. Controlled native proof:

- Playwright `ZECT_NATIVE_HEADED=1` (or `VITE_API_URL` containing `8010`)
- `ZECT_NATIVE_API_URL` default `http://127.0.0.1:8010`
- `sessionStorage.zect_api_origin` (loopback only) so the **same** Vite UI calls native generate
- Restored `getProject` (blank app was a missing named export)
- Playwright `baseURL` is `http://127.0.0.1:5173`

**Headed native generate (real `/present` UI):** Playwright `2 passed`. `provider=zect_native`, `planner_mode=LLM`, `zinnia_verified=true`, `final_quality_status=PASS`, URL on `:8010`, zero Presenton `:5000` generate calls.

Fresh blinded packs: `test-results/s7-parity/human-ab/`. Pre-S7.7 archive: `human-ab-pre-s77-history/`. Mapping not revealed; scorecard not filled.

## Remaining quality gaps

- Human blinded A/B is still mandatory; do not treat critic PASS as S7 READY.
- `overflow_layout` has only one PPTX — skip Preferred for that case.
- Electron Present generate was not re-run.
- Presenton standalone editor was not fully toured (session login).

## PRs (do not auto-merge)

Recommended split (implemented together on this branch; split if you prefer review size):

- Q6 QualityPolicy + critic + regression tests  
- Q7 LayoutComposer + semantic intent + grounding  
- Q8 repair loop + headed S7.7 acceptance  

Target `develop`. Tests → headed E2E → security → Ultra Review → human merge.

## STOP

S8C, S8D, KV cache, OCR/XLSX, broader Web, Graphify, and new agents were not started.
