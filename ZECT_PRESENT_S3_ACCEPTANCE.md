# ZECT Present S3 Acceptance — PresentationPlan

**Date:** 2026-08-14  
**Branch:** `feat/present-s3-presentation-plan`  
**Depends on:** S2 `6eb13a8` (PresentationService + importer)  
**Presenton:** remains **default** generate engine. Native PPTX generate is **not** claimed (S4).

## Verdict

**S3_PASS** — structured `PresentationPlan` via existing Model Gateway (`llm_phase._chat` / openai_compat). Untrusted context is wrapped and never placed in the system prompt. RESTRICTED/CONFIDENTIAL decks are not sent to Presenton.

## What shipped

| Item | Status |
|------|--------|
| Plan schema (objective, audience, narrative, slides, blocks, evidence, visual/layout/notes intent) | PASS |
| LLM only through Model Gateway | PASS — no Presenton `LLM=` / container key |
| Bounded repair + heuristic fallback | PASS |
| Untrusted context tagged `CONTEXT_UNTRUSTED` | PASS |
| Sensitivity fail-closed for external Presenton | PASS — `restricted_external_provider` HTTP 403 |
| Native PPTX | **Not in S3** |
| Presenton removed | **No** |

## Tests

`test_presentation_plan.py` + architecture planner isolation: **PASS** (28 with S2 registry/service/arch).

## Mentrix Ultra Review (branch-introduced)

| ID | Sev | Finding | Classification | Disposition |
|----|-----|---------|----------------|-------------|
| UR-S3-1 | Critical | Untrusted docs as system instructions | ALREADY_FIXED | Wrapped; system prompt forbids obeying them |
| UR-S3-2 | Critical | RESTRICTED sent to Presenton | ALREADY_FIXED | Service fail-closed before adapter |
| UR-S3-3 | Major | Invalid LLM JSON accepted | ALREADY_FIXED | validate + one repair + heuristic |

## Next

S4 native layout + python-pptx renderer (experimental opt-in). Keep Presenton default.
