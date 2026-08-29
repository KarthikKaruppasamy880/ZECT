# Fixes & Phases test suite

Tests for the security fixes (Fix #1–5) and Build/orchestrator upgrade
phases (Phase 1–4, Phase A–F) added in this body of work. Grouped here
instead of flat under `tests/` so future phases in the same effort have
an obvious home — add new test files for follow-up fixes/phases here.

| File | Covers |
|---|---|
| `test_encryption.py` | Fix #1 — Fernet encryption |
| `test_cors.py` | Fix #2 — CORS whitelist |
| `test_rbac.py` | Fix #3 — RBAC enforcement |
| `test_rate_limiting.py` | Fix #4 — per-user token budgets/rate limiting |
| `test_build_intel.py` | Phase 1 — semantic RAG retrieval for Build |
| `test_anthropic_client.py` | Anthropic/Claude Sonnet routing |
| `test_build_diff_apply.py` | Phase 2 — diff-based review-before-write |
| `test_build_multi_and_verify.py` | Phase 3/4 — multi-file generation, verify-and-fix |
| `test_review_consolidation.py` | Phase A — unified review engine |
| `test_hld_phase.py` | Phase B — LLM-backed HLD generator |
| `test_context_store.py` | Phase C — DB-backed Context Store |
| `test_orchestrator_build_loop.py` | Phase D — orchestrator builds every plan step |
| `test_orchestrator_sandbox.py` | Phase E — sandbox gate runs real tests |
| `test_review_phase_svc.py` | Phase E — orchestrator's Ultra Review delegates to the canonical engine |
