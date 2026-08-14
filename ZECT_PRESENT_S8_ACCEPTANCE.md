# ZECT Native Presentation S8 Acceptance

**Date:** 2026-08-14

## Gates

| Gate | Status |
|------|--------|
| **S8A** Presenton default / native experimental | **PASS** — `ZECT_PRESENTATION_PROVIDER` defaults to `presenton`; native via `zect_native` |
| **S8B** Opt-in + telemetry + rollback | **PARTIAL** — native responses include `telemetry.provider` / `opt_in`; rollback = unset env. No sustained metrics store |
| **S8C** Native default + Presenton fallback | **NOT STARTED** — blocked by S7 `NATIVE_NOT_READY` |
| **S8D** Remove Presenton runtime | **NOT STARTED** — Presenton not removed (required until sustained S8C) |

Presenton remains installed/configured as the default engine. Notices preserved.
