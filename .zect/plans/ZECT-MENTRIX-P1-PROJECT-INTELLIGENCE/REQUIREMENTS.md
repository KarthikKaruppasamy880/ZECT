# REQUIREMENTS â€” Mentrix P1 Project Intelligence + SDLC Connectivity

**Work item key:** ZECT-MENTRIX-P1-PROJECT-INTELLIGENCE
**Depends on:** P0 merged (`WorkItem`, `ArtifactStore`, `MentrixContextEngine`, `ProjectIntelligenceService` contract, `MentrixDeveloperService`, `EvidenceVerifier`, `WorkItemSourceAdapter` stubs)
**Rule:** Reuse P0 services â€” **do not** duplicate ContextEngine, DeveloperService, Coding Agent, or model gateway.

## Target spine

```
Jira/Camunda â†’ WorkItem â†’ Project/Repo
  â†’ ProjectIntelligence(Lattice + Blueprint + Knowledge + Memory + Related Work + Skills + Playbooks)
  â†’ ContextEngine â†’ Ask/Plan/Agent â†’ Fabric â†’ Coding Agent â†’ ForgeLoop
  â†’ Ultra Review â†’ EvidenceVerifier â†’ PR / Jira / Camunda
```

## Functional requirements

| ID | Requirement | Pri |
|----|-------------|-----|
| R1 | Implement `WorkItemSourceAdapter` for **Jira** and **Camunda** (ingest â†’ WorkItem with project/repo identity) | P1 |
| R2 | Bind WorkItem to **Project** + **repository_id/ref/base_commit_sha** (resolve missing refs fail-closed or NEEDS_HUMAN) | P1 |
| R3 | Flesh `ProjectIntelligenceService` with real Lattice, Blueprint, Knowledge, Memory, Related Work, Skills, Playbooks (no empty stubs unless source absent) | P1 |
| R4 | Keep Knowledge â‰  Memory semantics; PI returns both distinctly into ContextPack provenance | P1 |
| R5 | Wire MentrixDeveloperService Ask/Plan/Agent through enriched PI â†’ ContextEngine (no parallel context builder) | P1 |
| R6 | Fabric classify/run consumes approved PLAN / WorkItem context when surface matches | P1 |
| R7 | ForgeLoop build continues to use `mentrix_native` Coding Agent; dual-write plan remains ArtifactStore-owned | P1 |
| R8 | Ultra Review lane consumes WorkItem evidence + ContextPack (no second review engine) | P1 |
| R9 | EvidenceVerifier gates READY_TO_SHIP; on success optionally comment/transition Jira and complete Camunda task | P1 |
| R10 | PR create path updates WorkItem status + external adapters (idempotent) | P1 |
| R11 | **TI-001:** Fix pytest auth fixture vs `load_dotenv(override=True)` so authed HTTP tests pass locally/CI | P1 |
| R12 | **TI-002:** Exclude Playwright `e2e/**` from Vitest / fix `npm test` script | P1 |
| R13 | Full connectivity + gap regression tests for the P1 spine (integration, not mocks-only) | P1 |
| R14 | Durable Lattice freshness flags consumed by PI (minimal durable store if still in-memory) | P1 |

## Non-goals (P2+)

- Sidebar / Mentrix Developer UX redesign
- System Health dashboard
- Full Skills filesystem migrate to `.zect/skills` (beyond PI selection + execute hooks)
- Full Playwright suite green as DoD (smoke only unless TI work expands)

## NFR

| ID | Requirement |
|----|-------------|
| NFR-1 | Fail-closed: no silent mock/cloud when policy=`never` |
| NFR-2 | No parallel MentrixDeveloperService / ContextEngine / Coding Agent |
| NFR-3 | Preserve unrelated tracked/untracked files during execution |
| NFR-4 | Every op updates EXECUTION_MANIFEST + evidence |
