# RISKS.md — P0 Mentrix Consolidation

| ID | Risk | Impact | Mitigation | Residual |
|----|------|--------|------------|----------|
| R-001 | Dual plan stores (ArtifactStore vs MentrixRun) diverge | Delivery UI stale | Dual-write + hash gate | Medium until Delivery migrates |
| R-002 | llm_phase gateway change breaks ForgeLoop ask/plan | Delivery regressions | Tests + fail-closed telemetry | Medium |
| R-003 | Coding Agent smoke needs real gateway/env | OP-023b blocked | Document blocker + resume OP-023b | High if no local LLM |
| R-004 | E2E OP-035 needs DB + worktree + verifier | BLOCKED P0 | Persist exact resume op | High |
| R-005 | Accidental mock/cloud silent fallback | False COMPLETE | OP-034 policy tests; never fail-closed | Critical if skipped |
| R-006 | Scope creep into P1/P2/P3 | Delay | Hard stop; out-of-scope list | Low if enforced |
| R-007 | Unrelated file churn | Noise / conflict | Touch only P0 paths | Low |
| R-008 | WorkItem migration on existing DB | Schema break | Additive columns + defaults | Medium |
| R-009 | Companion dual Ask paths confuse users | UX debt | Route new tools; keep old until P2 | Medium |
| R-010 | Incomplete evidence → READY_TO_SHIP | Bad ship | EvidenceVerifier gate | Critical if bypassed |
