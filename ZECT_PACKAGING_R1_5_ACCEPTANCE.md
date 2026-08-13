# ZECT Packaging R1.5 Acceptance

**Branch:** `feat/r1.5-one-click-packaging`  
**Date:** 2026-08-13  
**Spec:** `prompts/ZECT_R4_5_RELEASE_BLOCKER_CLOSURE.md` §R1.5  
**Base:** `f37aa81`

## Classification

| Runtime | Class |
|---------|-------|
| Electron | PACKAGED |
| Frontend dist | PACKAGED |
| Backend sidecar launcher | PACKAGED (`run-api.ps1`) |
| Backend python-runtime | PACKAGED at `build:win` (gitignored) |
| SQLite / encryption key | PACKAGED in `userData` |
| Voicebox | OPTIONAL |
| Presenton | OPTIONAL |
| Local model | NOT_REQUIRED |
| Vite / system uvicorn / repo checkout | Dev only |

## Closed gaps vs R1

- Packaged auto-start sidecar + wait-for-API
- Per-user sqlite + generated encryption key (no installer `.env`)
- No baked credentials in launcher
- `bundle_sidecar.py` copies sources (no `.env`) and installs pinned requirements
- Managed shutdown unchanged

## Proofs

```text
pytest tests/fixes_and_phases/test_packaging_sidecar.py --noconftest
pytest tests/fixes_and_phases/test_phase9_13_batch.py::test_desktop_packaging_honest_partial --noconftest
node electron/service-lifecycle.node-test.js
```

Sidecar live: `run-api.ps1 -UserData <temp>` → `/docs` 200 (when python-runtime present).

## Honest remaining

| Gate | Status |
|------|--------|
| Clean-machine NSIS with no system Python | **BLOCKED_EXTERNAL** unless a dedicated install VM run is recorded |
| Voicebox / Presenton one-click | OPTIONAL — not required for login |

Do not claim full one-click PASS without the clean-machine NSIS gate.
