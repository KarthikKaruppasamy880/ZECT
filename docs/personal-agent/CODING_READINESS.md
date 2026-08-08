# Mentrix coding readiness

**Short answer:** Mentrix **Delivery / ForgeLoop** (upgrade → bugfix → deliver → gates → approve/PR) is **built and working**. A full autonomous **coding agent** is **not** the default.

| Layer | Status |
|-------|--------|
| Mentrix Delivery FSM + UI | Working (`/mentrix`, `domains/agent_run/mentrix.py`) |
| ForgeLoop orchestrator | Working (`services/forge_loop/orchestrator.py`) |
| Worker kickoff | Working (`workers/mentrix_worker.py`) |
| `ZECT_CODING_ENGINE=mock` (default) | Placeholder artifacts — **not** real remote coding |
| `ZECT_CODING_ENGINE=remote` + Agent Server | Optional closer-to-coding runtime |
| Companion “build me an app” | Routes through Delivery/tools — not Cursor-class agent |

Ask Mentrix: **“Is the coding engine ready?”** (tool `coding_engine_status`) for a live Artifacts summary.

See also [`CAPABILITY_MATRIX.md`](./CAPABILITY_MATRIX.md) and [`docs/ZECT_CODING_ENGINE.md`](../ZECT_CODING_ENGINE.md).
