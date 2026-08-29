# ZECT — S7.5 NATIVE PRESENTATION QUALITY CLOSURE

## Mission
Do not start S8C/S8D. Current official S7 verdict is `NATIVE_NOT_READY`. Mechanics are proven; quality parity is not. Preserve Presenton as default.

Known blockers from S7: native benchmark used heuristic fallback instead of equal LLM planning; executive/architecture decks were text-heavy; visuals triggered mainly by keywords; real organization Zinnia master was not used; blinded human A/B was missing. Security/voice/editor/export/native zero-Presenton-call proofs must remain green.

## 0 Baseline
Start synchronized `develop`; verify PR #152 merged, S7 acceptance is `NATIVE_NOT_READY`, Presenton default/native opt-in. Run frozen + native smoke.

## 1 Equal-quality native planner
Make production-quality native generation use ZECT Model Gateway → structured `PresentationPlan` JSON → schema validation/bounded repair → VisualPlan → renderer. Heuristic mode may remain only as explicitly labeled degraded fallback and cannot count toward parity.

Record requested/actual model, provider, `planner_mode=LLM|HEURISTIC_FALLBACK`, latency/tokens/fallback reason. Every S7.5 native quality case must use `planner_mode=LLM` or count as failed.

## 2 Latency
Profile context retrieval, prompt build, model queue/TTFT/completion, schema repair, visual planning, asset resolution, rendering, validation. Fix duplicate/repeated model calls, excessive context, unnecessary retries/serial passes before considering KV cache. Do not bypass quality for speed. Record before/after.

## 3 Presentation intelligence
Strengthen deck-level objective/audience/narrative arc/opening/sections/decision/CTA/tone/visual strategy. Each slide: purpose, specific title, key message, supporting points, evidence refs, visual story/type, layout intent, notes intent, transition.

Detect duplicate/generic titles, repetitive structures, missing progression/conclusion, excessive text and weak specificity.

## 4 VisualPlanner
Build ZECT-owned VisualPlanner over canonical blocks. For every slide choose based on purpose/data:
`NONE | IMAGE | CHART | TABLE | DIAGRAM | METRIC | COMPARISON | TIMELINE | PROCESS | ARCHITECTURE`.
Do not rely on simple keywords. Do not invent factual chart values. If no trustworthy data exists, use conceptual/non-factual visual treatment or text.

## 5 Images
Improve AssetResolver using authorized user/project assets, Document Intelligence assets, approved Web Intelligence assets, approved image-generation provider and ZECT brand assets. Enforce permissions/provenance/licensing metadata where available/sensitivity/offline/RESTRICTED policy. Do not add random images merely to increase media count.

## 6 Charts/tables/metrics
Choose editable chart types from data semantics; preserve provenance; readable labels/series; no fabricated factual values. Tables only when clearer than prose/chart; summarize/split dense tables. Metrics distinguish actual from example/generated values.

## 7 Diagrams/architecture
Technical decks must not default to text-only. Support canonical structured flow/architecture/process/sequence/dependency/before-after diagrams where practical. Commodity renderers may sit behind ZECT block abstraction; they are not canonical data.

## 8 Real Zinnia
Use the real authorized organization Zinnia master, not synthetic `make_master_pptx_bytes()`, for final quality acceptance:
`real Zinnia PPTX → Template Intelligence → READY → native generate → zinnia_verified=true`.
Validate theme/fonts/colors/layouts/geometry plus title/content/image/chart/table/summary slides. If unavailable, mark exact gate `BLOCKED_EXTERNAL`; synthetic master cannot prove final brand fidelity.

## 9 Template-aware composition
VisualPlanner/Layout Engine must select layouts from actual TemplateDefinition needs/geometry. Validate overflow, overlap, title collision, crop, chart/table readability, empty placeholders and balance. Choose another layout/split/error rather than dropping content.

## 10 Equal benchmark
Rerun the same S7 corpus: executive, architecture, roadmap, metrics/charts, document-grounded, image-heavy, table/data, real Zinnia, user/org template, overflow stress. Same prompt/audience/language/slide count/template intent/context and comparable quality model class. Document unavoidable differences. Native quality cases require LLM planner.

## 11 Mandatory blinded human A/B
Generate randomized anonymized Deck A/B pairs without revealing provider. Score 1–5: narrative coherence, prompt relevance, titles, visual hierarchy, template fidelity, layout, density/readability, image relevance, chart/table quality, executive usefulness, technical usefulness, notes, overall quality; record A/B/Tie and comments. Prefer multiple humans. Model rubric may be secondary only; generator/model cannot be sole judge.

## 12 Deterministic checks
Both providers: PPTX validity, slide count, empty slides, title uniqueness, layout variety, overflow/overlap, media/broken media, chart/table validity, notes, template fidelity, editor load/round-trip, export/reopen.
Native additionally: planner mode/model, zero Presenton generation calls, provenance coverage.

## 13 Performance
Measure total/LLM/asset/render/validation latency, cold/warm, tokens/resources. Native need not equal Presenton speed if quality/security/local ownership justify difference, but unexplained multi-minute UX is unacceptable. Define a product latency target from evidence. Do not add KV-cache work here without separate approval.

## 14 Degraded mode
If Model Gateway unavailable, do not silently present heuristic output as equivalent quality. UI should explicitly offer Retry / Fast-Basic generation / approved fallback provider as policy permits. User must know degraded mode is used.

## 15 Security
Re-prove RESTRICTED/CONFIDENTIAL policy, untrusted document/web context, template/asset ownership, cross-user, path safety, malicious PPTX/images, prompt injection, artifact authorization and secret isolation. Quality work must not weaken S7 security PASS.

## 16 Acceptance
Create `ZECT_NATIVE_PRESENTATION_S7_5_QUALITY_ACCEPTANCE.md` covering Model Gateway planner, fallback rate, latency, plan/visual quality, real Zinnia, images/charts/tables/metrics/diagrams, template-aware layout, deterministic benchmark, blinded A/B, security and zero-Presenton-call proof.

Then rerun official S7 and update `ZECT_NATIVE_PRESENTATION_PARITY_ACCEPTANCE.md` with exactly:
`NATIVE_READY_FOR_DEFAULT | NATIVE_READY_WITH_LIMITATIONS | NATIVE_NOT_READY`.

Do not call ready merely because native succeeds/faster/PPTX opens/visuals exist. Ordinary presentation quality must be acceptable. Do not auto-accept limitations affecting executive/architecture/roadmap/image/chart use cases.

## 17 Gate
Do NOT start S8C in this run. If final S7 is `NATIVE_READY_FOR_DEFAULT`, return `READY_FOR_S8C` and STOP for human review. Otherwise return `NOT_READY_FOR_S8C` with exact blockers.

## PR discipline
Use focused PRs where useful: Q1 LLM planning+profiling; Q2 VisualPlanner/assets; Q3 diagrams/template composition; Q4 real Zinnia hardening; Q5 benchmark/A-B evidence. Every production PR: tests → headed E2E → security → Ultra Review → substantive external review if available → fix Critical/Major → CI → approved merge → sync → regression.

## STOP
Do not start S8C automatically, S8D, KV cache, OCR/XLSX, broader Web, Graphify or new agents.

Goal:
`ZECT Native Presentation >= acceptable Presenton-quality UX + ZECT-owned architecture + Model Gateway + Template Intelligence + security/governance + editor/voice/export`.
