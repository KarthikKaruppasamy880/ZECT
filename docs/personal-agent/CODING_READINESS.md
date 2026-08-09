# Mentrix coding readiness

**Short answer:** Mentrix **Delivery / ForgeLoop** is built. **Mentrix Coding Agent** is the in-process tool loop (read/search/edit/run/git). **Product default** is `ZECT_CODING_ENGINE=mentrix_native`. CI may set `mock` explicitly for placeholders.

| Layer | Status |
|-------|--------|
| Mentrix Delivery FSM + UI | Working (`/mentrix`) |
| ForgeLoop orchestrator | Working |
| Mentrix Coding Agent (`mentrix_native`) | Real workspace tool loop — Developer Workspace panel + `/api/coding-agent` |
| `ZECT_CODING_ENGINE=mock` (CI only) | Placeholder artifacts when env set |
| `ZECT_CODING_ENGINE=remote` | Optional external Agent Server |
| Companion | `coding_agent_start` → `/workspace?session=…`; `coding_engine_status` honesty |

Ask Mentrix: **“Is the coding engine ready?”** or **“Start coding agent: add a README”**.

See also [`docs/ZECT_CODING_ENGINE.md`](../ZECT_CODING_ENGINE.md).
