# ZECT Local Stack Control Acceptance

**Date:** 2026-08-19  
**Canonical develop:** `0dd7becb2c98b7e6c368bee10392925d1f3d57f2`  
**Branch:** merged via PR **#171**  
**Stop:** human merge only. No auto-merge.

## Verdict

**ZECT_LOCAL_STACK_CONTROL_READY** for `core` on this Windows operator run (`up` / `status` / `health` / `restart backend` / frontend PID preserved). Desktop Electron and optional Presenton/Voicebox remain uncertified here. Unit proofs **PASS**. Skip ≠ PASS. Optional Presenton / Voicebox / PowerPoint / GitHub remain **OPTIONAL_UNAVAILABLE** or **BLOCKED_EXTERNAL** when absent — they do not block Core.

| Check | Result |
|-------|--------|
| Config schema / ports 8020+5173 | **PASS** unit |
| Electron after backend/frontend | **PASS** unit (dependency order) |
| Unowned occupied port not killed | **PASS** unit |
| Secret redaction / env names not values | **PASS** unit |
| Optional Presenton unavailable | **PASS** unit |
| Restart one service leaves others | **PASS** unit |
| Real `down → up core → restart backend → health → down` | **PASS** live on this machine (frontend PID unchanged across backend restart). `up --profile desktop` is a separate Electron start. |
| `scripts/stop-local.ps1` kill-by-port | **NOT USED** by `zect down` |

CI / packaged API stays **:8000**.
