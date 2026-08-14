# ZECT Native Presentation Parity Acceptance (S7)

**Date:** 2026-08-14  
**Against:** stacked local branches S2–S6 on top of `develop` `98e19e6`  
**Presenton default:** unchanged

## Readiness

**NATIVE_NOT_READY** for default switch (S8C).

Experimental opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native`) is implemented with unit proof. It is **not** approved as the product default.

## Why not READY_FOR_DEFAULT

| Gate | Evidence |
|------|----------|
| Identical live prompts/templates through PresentonProvider vs ZectNative | **Missing** — no live Presenton generate benchmark this session |
| Blinded human quality comparison | **Missing** |
| Template/layout fidelity vs Zinnia masters | Unit only; not live org masters |
| Overflow / variety / latency / resources | **Not measured** |
| Headed native Zinnia → editor → notes → clone/stock voice → export with no Presenton network | **Missing** |
| Charts/images/tables | **PARTIAL** (text/notes/table subset) |
| Human merge of S2–S6 into `develop` | **BLOCKED_EXTERNAL** (see S8) |

Do **not** proceed to S8C.

## Deterministic unit comparison (not a substitute for S7 live)

Native path: plan → python-pptx → zip/XML validate → allowlisted path. Presenton path unchanged. Restricted content is not sent to Presenton (`restricted_external_provider`).
