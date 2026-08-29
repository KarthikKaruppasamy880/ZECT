# ZECT Native Presentation S7.5 Quality Acceptance

**Date:** 2026-08-14  
**Branch:** `feat/present-s75-quality-closure` (uncommitted) on synchronized `develop` `c32b97590067d1eb7c07d3abba36917b23365f3c` (PR #152 merged)  
**Presenton default:** unchanged. Native remains opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native`).  
**S8C:** not started.

## Result

S7.5 closed the **heuristic planner** gap: production-quality native generate now uses ZECT Model Gateway (`llm_phase._chat`, PUBLIC/INTERNAL `policy=automatic`) → structured `PresentationPlan` → schema validation / bounded repair / nested-JSON coerce → VisualPlanner → renderer.

It did **not** close quality parity vs Presenton. Official S7 remains **`NATIVE_NOT_READY`**. Do not start S8C.

## Model Gateway planner

| Check | Status | Evidence |
|-------|--------|----------|
| PUBLIC plans request `policy=automatic` | PASS | `test_s75_quality.py::test_public_plan_requests_automatic_gateway_policy` |
| Heuristic is labeled `HEURISTIC_FALLBACK` + `degraded` | PASS | same + generate response telemetry |
| `require_llm=True` does not count heuristic as success | PASS | `test_require_llm_does_not_count_heuristic_as_parity` |
| Fast-Basic skips Gateway and is labeled | PASS | `test_fast_basic_skips_gateway_and_labels_degraded`; UI Retry / Fast-Basic |
| Nested LLM `narrative.arc` coerced to `slides[]` | PASS | Live `gpt-4o-mini` first returned slides under `narrative.arc`; coerce + prompt fix; `test_coerce_nested_narrative_arc_into_slides` |
| Live corpus `planner_mode=LLM` | **10 / 10** | `test-results/s75-parity/evidence.json` and official `test-results/s7-parity/evidence.json` |
| Native → Presenton HTTP generate | **0** | both live runs |

Requested/actual model on live success: `gpt-4o-mini`. Fallback rate on the LLM-required corpus: **0**.

UI: Generate tries Model Gateway then labeled Fast-Basic; explicit **Fast-Basic generation** and **Retry Model Gateway**. Presenton is not used automatically on the native path.

## Latency profile (S7.5 live, 10 LLM successes)

From `test-results/s75-parity/latency_profile.json`:

| Stage | Mean |
|-------|------|
| LLM plan | 15879 ms |
| Visual plan | ~0 ms |
| Render | 154 ms |
| Total generate | 16041 ms |

Official S7 live (same corpus, `require_llm=True`): ~9–32 s per deck (metrics_charts 32 s including repair). Product target from this evidence: **native LLM plan+render should finish in well under 3 minutes per typical 5-slide deck**. Unexplained multi-minute UX after the PPTX exists is a client wait bug, not planning time. KV cache was not added.

Presenton was **not reachable** this session, so there is no new Presenton latency sample. Prior S7 on this SHA: Presenton success mean ~72 s.

## Plan / visual quality

VisualPlanner assigns purpose-driven `NONE|IMAGE|CHART|TABLE|DIAGRAM|METRIC|…` (not prompt-keyword only). Invalid LLM chart/table payloads are replaced with **example-provenance** blocks (no invented factual numbers).

Official S7 native OOXML (`inspect_pptx_visuals`):

| Case | Planner | Notable visuals |
|------|---------|-----------------|
| executive_update | LLM | chart + table |
| technical_architecture | LLM | 4 diagram blocks + table (diagrams are shapes, not `ppt/charts`) |
| roadmap | LLM | table |
| metrics_charts | LLM | chart + table (invalid LLM chart data replaced with example series) |
| document_grounded | LLM | table; untrusted context wrapped |
| image_heavy | LLM | embedded image |
| table_data | LLM | table (prompt no longer trips CONFIDENTIAL) |
| zinnia_executive | LLM | table |
| user_template | LLM | table; `zinnia_verified=false` |
| overflow_layout | LLM | chart + table; 8 slides |

Native does **not** stamp decorative images on every slide (Presenton previously did). That is intentional (no random media to inflate counts) and remains a subjective-quality gap until human A/B.

## Real Zinnia

S7.5: **`BLOCKED_EXTERNAL`** (synthetic pytest master only).

**S7.6 closed this gate.** Imported `artifacts/zinnia-master-source.pptx` SHA256 `74cb1f7a50c2dcd3ce6c1a41547c45f9666fcb1e353801b87a174c63ecf70dc2` (12.3 MB, 18 layouts, Arial, accent2 `#FF7500`). `native_ready=true`. Proof: `test-results/s7-parity/zinnia-import.json`. Synthetic `make_master_pptx_bytes()` was not used for S7.6 brand evidence.

## Images / charts / tables / diagrams / template composition

- Images: authorized `asset_id` or generated placeholder with example provenance; no URL fetch.
- Charts: editable OOXML column/bar/line/pie/donut; example series when evidence has no trustworthy numbers.
- Tables: used for workstream/decision comparison; dense tables truncated with validation, not silent drop.
- Diagrams: flow / process / architecture painted via canonical blocks.
- Layouts: TemplateDefinition layout names preferred when picking python-pptx layouts; overflow marked, not dropped.

## Deterministic benchmark

Both providers: this run only native (Presenton unreachable). Native: PPTX valid, expected slide counts, notes present, editor OOXML round-trip true on S7.5 script cases, zero Presenton generate calls, `planner_mode=LLM` on all 10 quality cases.

## Blinded human A/B

S7.5: **Not performed** (Presenton decks missing).

**S7.6 packs are ready; human scores are not.** Randomized A/B PPTX pairs: `test-results/s7-parity/human-ab/`. Empty scorecard: `ZECT_NATIVE_PRESENTATION_HUMAN_AB_SCORECARD.md`. Cursor must not score. Official verdict stays `NATIVE_NOT_READY` until the human returns this file filled.

## Security

`test_s7_security_comparison` PASS. RESTRICTED/CONFIDENTIAL still fail-closed; native does not call Presenton; untrusted context stays in `<<<CONTEXT_UNTRUSTED … CONTEXT_UNTRUSTED>>>`. Quality work did not weaken S6/S7 security tests (frozen suite green).

## Frozen / native smoke

Frozen + S7.5 unit: **122 passed, 1 skipped**.

**S7.6 headed LLM-native:** Playwright `present-s76-llm-native.spec.ts` **2 passed**. Evidence: `test-results/s7-parity/headed-llm-native/` (`provider=zect_native`, `planner_mode=LLM`, `gpt-4o-mini`, `zinnia_verified=true`, video + screenshots + export).

Presenton comparison environment was started for S7.6 (`127.0.0.1:5000`, generate smoke ok). Equal 10/10 Presenton vs native corpus is in `test-results/s7-parity/s76-evidence.json`.

## S8C

Not started. Return remains **`NOT_READY_FOR_S8C`** until blinded human A/B is scored and the official S7 verdict is no longer `NATIVE_NOT_READY`.
