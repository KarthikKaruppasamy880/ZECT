# ZECT — S7.6 FINAL PARITY EVIDENCE + HUMAN A/B

## Mission
Do not redesign native engine or start S8C/S8D. Current verdict remains `NATIVE_NOT_READY / NOT_READY_FOR_S8C`.

S7.5 already proved native quality uses ZECT Model Gateway, 10/10 quality cases used `planner_mode=LLM`, charts/images/tables exist, zero Presenton generation calls on native success, mean measured native generation ~16s, security PASS, heuristic is explicitly degraded, and frozen suite was 122 passed/1 skipped.

Close only remaining evidence gates: Presenton comparison environment, REAL organization Zinnia master, headed LLM-native browser proof, and blinded HUMAN A/B.

## 0 Baseline
Start synchronized `develop`; verify S7/S7.5 acceptance and frozen smoke. Presenton stays default; native stays opt-in. Do not change defaults.

## 1 Presenton comparison environment
Start the existing authorized local Presenton runtime and verify health plus generation through ZECT `PresentationService/PresentonProvider`. Standalone Presenton UI is comparison reference only, never ZECT product acceptance. Record reproducible runtime version/image/config without secrets. If unavailable, return `BLOCKED_EXTERNAL: PRESENTON_COMPARISON_ENVIRONMENT`; never fabricate decks.

## 2 REAL Zinnia master
Do not use synthetic `make_master_pptx_bytes()` for final brand acceptance. Import the actual authorized Zinnia organization PPTX:
`real PPTX → secure Template Intelligence → TemplateDefinition → preview → READY`.
Verify SHA/theme/fonts/colors/masters/layouts/placeholders/geometry/assets/backgrounds and title/content/image/chart/table/summary compatibility. ZECT identity remains canonical. Use provider mapping only for Presenton comparison if required. If unavailable: `BLOCKED_EXTERNAL: REAL_ZINNIA_MASTER_REQUIRED`.

## 3 Headed NEW LLM-native proof
Real ZECT UI, native opt-in:
`Login → Present → New → real Zinnia → prompt → Generate → editor → notes → export/reopen`.
Evidence must show `provider=zect_native`, `planner_mode=LLM`, actual Model Gateway route/model, structured plan, VisualPlanner, native renderer, `zinnia_verified=true`, zero Presenton generation calls, real PPTX and required images/charts/tables. Capture headed Playwright screenshots/trace/video where supported. API-only proof is insufficient.

## 4 Equal S7 corpus
Run identical Presenton/native pairs with same prompt/audience/language/slide count/template intent/authorized context. Native quality cases require `planner_mode=LLM`.

At least: executive, technical architecture, roadmap, metrics/chart, document-grounded, image-heavy, table/data, REAL Zinnia Executive, user/org template, overflow/layout stress.

Record both: validity, success, latency, slides, template fidelity, layout variety, overflow/overlap, media/broken assets, charts/tables, notes, editor round-trip, export/reopen, security. Native also records Model Gateway/planner mode and zero Presenton calls.

## 5 BLINDED A/B packs
Cursor prepares but DOES NOT SCORE human review.

For every comparable case randomly assign provider outputs A/B, remove provider names from reviewer-visible filenames/metadata where practical, retain a private mapping, and provide PPTX plus useful preview PDF/images if possible.

Create `test-results/s7-parity/human-ab/` with anonymized A/B decks, prompt/template goal, scorecard and private mapping. Do not reveal mapping before scoring.

## 6 Human scorecard
Create `ZECT_NATIVE_PRESENTATION_HUMAN_AB_SCORECARD.md`.

For each pair human scores 1–5:
Narrative coherence; Prompt relevance; Slide-title quality; Visual hierarchy; Template/brand fidelity; Layout quality; Content density/readability; Image relevance; Chart/table usefulness; Executive usefulness; Technical usefulness; Speaker notes; Overall quality.

Also `Preferred: A | B | Tie` and comments. Support multiple humans if available.

CRITICAL: Cursor/LLM must NOT fill human scores. STOP and ask the user to inspect anonymized decks and complete the scorecard.

## 7 Resume after human scoring
Only after completed human scorecard is supplied: validate completeness, join private mapping, calculate provider-level means/medians/preferences, preserve raw comments and do not rewrite unfavorable ratings. Model rubric may be secondary only.

## 8 Final parity decision
Update S7.5 quality acceptance and `ZECT_NATIVE_PRESENTATION_PARITY_ACCEPTANCE.md` with exactly:
`NATIVE_READY_FOR_DEFAULT | NATIVE_READY_WITH_LIMITATIONS | NATIVE_NOT_READY`.

Ready requires real Zinnia fidelity, headed native LLM planner, equal comparison, completed blinded human A/B, acceptable deterministic/visual/editor/export quality, security PASS, zero Presenton calls on native success and no unresolved Critical/Major. Speed/success alone is insufficient.

If ordinary executive/technical/visual quality is materially weaker, remain `NATIVE_NOT_READY` with precise remediation targets.

## 9 S8C gate
Do NOT start S8C automatically. If final verdict is `NATIVE_READY_FOR_DEFAULT`, return `READY_FOR_S8C` and STOP for human approval. Otherwise return `NOT_READY_FOR_S8C` with blockers.

## 10 No scope expansion
Do not start S8C automatically, S8D, KV cache, OCR/XLSX, broader Web, Graphify or new agents. Do not rebuild S2–S6 without concrete evidence of a defect.

## Final stop
Required two-step interaction:
`Cursor generates real parity decks + blinded packs → STOP FOR HUMAN SCORING → human completes scorecard → Cursor resumes final S7 decision`.

Never fabricate the human A/B gate.
