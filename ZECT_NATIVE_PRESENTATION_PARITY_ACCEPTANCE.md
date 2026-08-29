# ZECT Native Presentation Parity Acceptance (S7)

**Date:** 2026-08-14  
**Against:** `develop` `c32b97590067d1eb7c07d3abba36917b23365f3c` (human merge of PR #152) plus S7.5/S7.6 work on `feat/present-s75-quality-closure`  
**Presenton default:** unchanged. Native remains opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native`).  
**S8C:** not started.  
**S7.5 detail:** `ZECT_NATIVE_PRESENTATION_S7_5_QUALITY_ACCEPTANCE.md`  
**Human A/B scorecard:** `ZECT_NATIVE_PRESENTATION_HUMAN_AB_SCORECARD.md` (empty — waiting on human)

## Readiness

**NATIVE_NOT_READY**

Do **not** switch the product default. Do **not** start S8C. S7.6 closed the remaining **evidence production** gates; it did **not** complete blinded human scoring, so the official verdict cannot move.

## S6.5 / S7.6 re-prove

Frozen pytest (S7.5 session, including S7.5 unit tests): **122 passed, 1 skipped**. Packaging/template/S7.5 quality/S7 security smoke this session: **24 passed**.

| Gate | Status | Evidence |
|------|--------|----------|
| Frozen native/security/template/voice unit | PASS | 122 passed, 1 skipped |
| Native Zinnia generate (headed, LLM planner) | **PASS (S7.6)** | Playwright headed `present-s76-llm-native.spec.ts` 2 passed (59.4s generate+editor). `provider=zect_native`, `planner_mode=LLM`, `model=gpt-4o-mini`, `zinnia_verified=true`, `template_sent=zinnia-executive-v1`. Screenshots/video/trace: `test-results/s7-parity/headed-llm-native/` |
| Zero Presenton generation calls on native success | PASS | S7.6 benchmark `native_presenton_generation_calls=0`; headed generate used native API `:8010` |
| Image / chart / table editor + export | PASS | Headed editor notes + export 1,970,961 bytes; prior `present-s65-visual.spec.ts` |
| Cloned voice / stock / No Narration | PRIOR_PASS | Prior headed clone/stock/none on this SHA |

## Presenton comparison environment (S7.6)

**PASS** (not `BLOCKED_EXTERNAL`).

- Container `presenton` (`ghcr.io/presenton/presenton:latest`, image `eede239c987b`), `127.0.0.1:5000->80/tcp`, HTTP 200
- LLM: openai / `gpt-4o-mini`; `DISABLE_IMAGE_GENERATION=true`; auth via env (secrets not recorded)
- Smoke through ZECT `PresentationService(PresentonProvider)`: **ok**, ~61 s, `zinnia_verified=true`, mapped UUID `e7ac06b6-36e7-4460-b476-00bcaa98207d`
- Runtime record: `test-results/s7-parity/presenton-runtime.json`
- Standalone Presenton UI was **not** used as product acceptance

## Real organization Zinnia master (S7.6)

**PASS** (not `BLOCKED_EXTERNAL`). Synthetic `make_master_pptx_bytes()` was **not** used for this run.

- Source: `artifacts/zinnia-master-source.pptx` (12,275,249 bytes)
- SHA256: `74cb1f7a50c2dcd3ce6c1a41547c45f9666fcb1e353801b87a174c63ecf70dc2`
- Import: `native_ready=true`, 18 layouts, 16:9, Arial, accent2 `#FF7500`
- Proof: `test-results/s7-parity/zinnia-import.json`

## S7.6 equal live benchmark

Identical corpus (10 cases), native `require_llm=True`, real imported Zinnia master (not pytest tmp synthetic). Raw: `test-results/s7-parity/s76-evidence.json`. Duration ~13.7 min.

| | Native | Presenton |
|--|--------|-----------|
| Success | **10 / 10** | **10 / 10** (overflow first attempt HTTP 400 outline failure; identical retry succeeded) |
| Quality success (`planner_mode=LLM`) | **10 / 10** | n/a (Presenton engine) |
| Mean latency (success) | ~15.7 s (range 11.1–20.8 s) | ~56.7 s on first 9; overflow retry after 400 |
| `zinnia_verified` | true on Zinnia cases; **false** on `user_template` (USER id, expected) | true via registry UUID |
| Planner | Model Gateway `gpt-4o-mini` every success | Presenton openai `gpt-4o-mini` |
| Native → Presenton HTTP generate | **0 calls** | — |
| Blinded human A/B packs | **true** (10/10 pairs) | scored: **false** |

Overflow Presenton 400: `Failed to generate presentation outlines with requested number of slides.` Identical 8-slide retry produced a PPTX. Packs include that retry. Cursor did **not** score the decks.

## Security comparison (`test_s7_security_comparison`)

PASS. Native RESTRICTED/CONFIDENTIAL does not call Presenton. Untrusted context is wrapped in `<<<CONTEXT_UNTRUSTED … CONTEXT_UNTRUSTED>>>` and is not system instructions. Presenton path still returns `restricted_external_provider` 403 before generate.

## Blinded quality

**Packs are ready. Human scores are not.** Cursor must not fill the scorecard.

- Packs: `test-results/s7-parity/human-ab/<case>/Deck_A.pptx` + `Deck_B.pptx`
- Scorecard: `ZECT_NATIVE_PRESENTATION_HUMAN_AB_SCORECARD.md` (empty 1–5 / Preferred)
- Private mapping exists and is withheld until the human returns scores
- Secondary model rubric is not a substitute

## Why not NATIVE_READY_FOR_DEFAULT

1. Mandatory blinded human A/B (primary subjective gate) is **unscored**.  
2. Limitations are **not** auto-accepted. Native still does not match Presenton’s “image on every slide” habit (by design); humans must judge brand/layout/narrative.  
3. Speed/success (10/10 LLM, ~16 s native, Presenton up, real Zinnia, headed LLM) is **not** sufficient without completed human scoring.

## Why not NATIVE_READY_WITH_LIMITATIONS

That status would invite S8C after a human signs carve-outs. Unscored A/B is a default-switch blocker, not an optional limitation.

## What S7.6 closed (not enough to switch)

- Presenton comparison environment generate through ZECT adapter  
- Real org Zinnia PPTX imported as TemplateDefinition (`native_ready`)  
- Headed Login → Present → Zinnia → Generate with `planner_mode=LLM` + editor notes/export/reopen  
- Equal 10-case Presenton vs native corpus + randomized blinded packs  

## S8C / S8D

S8C not started (requires `NATIVE_READY_FOR_DEFAULT` after human scoring).  
S8D not started.

## READY_FOR_S8C

**NOT_READY_FOR_S8C**

Blockers:

1. Official S7 verdict is `NATIVE_NOT_READY`.  
2. Blinded Presenton-vs-ZECT human A/B packs exist but **SCORECARD is empty**.  
3. Presenton remains product default until an authorized S8C after `NATIVE_READY_FOR_DEFAULT`.
