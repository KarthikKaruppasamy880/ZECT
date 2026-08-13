# ZECT Present R2 — Cross-environment PPTX reliability

**Branch:** `feat/r2-present-pptx-reliability`  
**Date:** 2026-08-13  
**Spec:** Next roadmap §R2  
**Base:** develop @ `06a76a8` (R1 packaging PARTIAL merged)

## Audit → result

| Capability | Before | After |
|---|---|---|
| Zinnia / Org / User gallery | PARTIAL (org=zinnia clone) | Org masters distinct (`org-*`); user PPTX still local |
| prompt→deck | PARTIAL / BLOCKED_EXTERNAL | Same; structured failures + retries |
| document→deck | MISSING | Still deferred (no UI pass of documents) |
| selected template sent | PARTIAL (UI pre-map) | UI sends `ui_template_choice`; API uses `resolved.template_id` |
| `zinnia_verified` | PARTIAL | Honest false without master; true only with env/custom |
| editable PPTX export | PARTIAL | Unchanged path when Presenton up |
| notes / clone rehearsal | PARTIAL | Unchanged |
| Presenton 502/timeout | PARTIAL | Bounded retries + structured `blocked_external` |
| headed ZECT UI E2E | PARTIAL | Captures `template_sent` / `zinnia_verified` / blocked |
| packaged Presenton | BLOCKED_EXTERNAL | Still external; template root via `ZECT_PRESENT_TEMPLATE_ROOT` |

## Verdict

**PARTIAL** — reliability/honesty improved; full PPTX + `zinnia_verified=true` still **BLOCKED_EXTERNAL** without Presenton + `ZINNIA_PRESENTON_TEMPLATE_ID`.

## Proofs

```text
pytest backend/tests/fixes_and_phases/test_presenton_client.py --noconftest -q
pytest backend/tests/fixes_and_phases/test_present_template_registry.py --noconftest -q
npx playwright test e2e/present-product.spec.ts --headed
```

## Stop

Do not claim Present complete. Proceed to R3 after merge.
