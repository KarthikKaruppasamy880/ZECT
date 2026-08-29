# RISKS.md â€” Mentrix P1

| ID | Risk | Impact | Mitigation |
|----|------|--------|------------|
| R1 | Jira/Camunda APIs incomplete locally | Ingest blocked | Adapter contracts + recorded fixtures; fail-closed without credentials |
| R2 | PI over-fetch blows token budget | Cost/latency | ContextEngine token_budget + provenance selection_reason |
| R3 | Dual MentrixRun vs WorkItem drift | Wrong SoT | ArtifactStore remains plan owner; MentrixRun mirror only |
| R4 | Ultra Review redesign creep | Scope blowup | Wire existing review_service only; no 3-lane redesign in P1 |
| R5 | TI-001/TI-002 delayed | CI noise | Mandatory first ops in P1 manifest |
| R6 | Fabric auto-run without approval | Unsafe edits | Require PLAN_APPROVED / human gate |
| R7 | New parallel agents invented | Architecture break | Code review gate: reuse P0 modules only |
| R8 | External transition double-fire | Jira/Camunda inconsistency | Idempotent adapter writes + WorkItemEvent audit |
