# ZECT Gap Analysis â€” P1 planning update (review)

States: COMPLETE | PARTIAL | DUPLICATED | DISCONNECTED | MOCK | MISSING | DEFERRED | P0_COMPLETE | P1_PLANNED

This file is the **P1 planning overlay**. Canonical live doc remains `docs/architecture/ZECT_GAP_ANALYSIS.md` (updated during P1 OP-051). Do not implement P1 from this doc alone without EXECUTION_MANIFEST.

| Capability | Post-P0 State | P1 Target | Required Change | Pri |
|---|---|---|---|---|
| WorkItem identity | P0_COMPLETE | Bound to Project/Repo on ingest | Adapters set repo fields | P1 |
| WorkItemEvent | P0_COMPLETE | Emit ingest/external transitions | Event types for jira/camunda | P1 |
| SourceAdapter Jira | Stub NotImplemented | Ingest + update | Implement adapter | P1 |
| SourceAdapter Camunda | Stub NotImplemented | Taskâ†’WorkItem | Implement adapter | P1 |
| ProjectIntelligence fill | Contract + empty stubs | Live Lattice/Blueprint/KB/Memory/Skills/Playbooks/Related | Fill service | P1 |
| Knowledge vs Memory | Separate (P0) | Provenance into ContextPack | Wire retrieve paths | P1 |
| ContextEngine | Provenance schema P0 | Fed by live PI | No new engine | P1 |
| MentrixDeveloperService | P0_COMPLETE | Uses live PI | Wire snapshot | P1 |
| Fabric from PLAN | Manual | Auto classify/run from approved WI | Handoff | P1 |
| Coding Agent | Sole editor (P0) | Unchanged ownership | Reuse mentrix_native | P1 |
| ForgeLoop | Delivery FSM | Dual-write only | Keep ArtifactStore SoT | P1 |
| Ultra Review | Engine exists | Consume WI/ContextPack | Wire inputs (no redesign) | P1 |
| Evidence â†’ external | READY_TO_SHIP local | PR + Jira + Camunda close | Adapters out | P1 |
| Lattice durability | PARTIAL in-memory | Freshness for PI | Minimal durable/freshness | P1 |
| TI-001 auth fixture | FAIL pre-existing | Green authed HTTP | Fix dotenv/fixture | P1 |
| TI-002 Vitest/e2e | FAIL pre-existing | npm test unit-only | Exclude e2e | P1 |
| Connectivity E2E | MISSING | Spine integration suite | OP-050 | P1 |
| Sidebar / Health / Skills FS migrate | DEFERRED | â€” | P2 | P2 |
| Ultra Review 3-lane redesign | DEFERRED | â€” | P2/P1+ | P2 |

## Connectivity test matrix (P1 OP-050)

1. Jira issue â†’ WorkItem(NEWâ†’INGESTED) + project/repo
2. Camunda task â†’ WorkItem
3. PI snapshot non-empty keys when fixtures present
4. Ask/Plan/Agent ContextPack includes KBâ‰ Memory provenance
5. Approve plan â†’ Fabric â†’ Coding Agent file change
6. Ultra Review finding typed evidence
7. EvidenceVerifier â†’ READY_TO_SHIP â†’ PR URL + Jira comment + Camunda complete (mocked externals OK if contract-tested)
8. TI-001 + TI-002 green

## Architecture reuse reminder

Reuse P0: `MentrixDeveloperService`, `MentrixContextEngine`, `ArtifactStore`, `ProjectIntelligenceService`, `EvidenceVerifier`, `WorkItemSourceAdapter`, `openai_compat`/`fallback_policy`, Mentrix Coding Agent. **No parallel systems.**
