# ZECT Local Stack Control Acceptance

**Date:** 2026-08-19  
**Branch:** `feat/local-stack-control`  
**Stop:** human merge only. No auto-merge.

## Verdict

**ZECT_LOCAL_STACK_CONTROL_PARTIAL** until a human runs the real Windows smoke on a clean machine. Unit proofs **PASS**. Skip ≠ PASS. Optional Presenton / Voicebox / PowerPoint / GitHub remain **OPTIONAL_UNAVAILABLE** or **BLOCKED_EXTERNAL** when absent — they do not block Core.

| Check | Result |
|-------|--------|
| Config schema / ports 8020+5173 | **PASS** unit |
| Electron after backend/frontend | **PASS** unit (dependency order) |
| Unowned occupied port not killed | **PASS** unit |
| Secret redaction / env names not values | **PASS** unit |
| Optional Presenton unavailable | **PASS** unit |
| Restart one service leaves others | **PASS** unit |
| Real `down → up core → desktop → down` | **PARTIAL** — operator smoke |
| `scripts/stop-local.ps1` kill-by-port | **NOT USED** by `zect down` |

CI / packaged API stays **:8000**.
