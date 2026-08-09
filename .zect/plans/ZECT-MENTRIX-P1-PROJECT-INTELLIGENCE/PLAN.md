# PLAN.md â€” Mentrix P1 Project Intelligence + Connectivity

**work_item_key:** ZECT-MENTRIX-P1-PROJECT-INTELLIGENCE
**plan_version:** 1
**status:** PLANNED (not implemented)
**base:** develop after P0 merge
**branch (intended):** `feat/mentrix-p1-project-intelligence`

## Objective

Connect external work sources and fill Project Intelligence so Mentrix Ask/Plan/Agent â†’ Fabric â†’ Coding Agent â†’ ForgeLoop â†’ Ultra Review â†’ EvidenceVerifier â†’ PR/Jira/Camunda is one spine on top of **P0 services**.

## Locked reuse (from P0)

| Capability | Owner (reuse) |
|------------|---------------|
| WorkItem / WorkItemEvent | `domains/work_items` |
| PLAN.md | `ArtifactStore` |
| ContextPack | `MentrixContextEngine` |
| Ask/Plan/Agent entry | `MentrixDeveloperService` |
| Model path | `openai_compat` + `fallback_policy` |
| Code edits | Mentrix Coding Agent (`mentrix_native`) |
| READY_TO_SHIP gate | `EvidenceVerifier` |
| Source contract | `WorkItemSourceAdapter` (extend stubs) |

**Forbidden:** second coding agent, second context engine, second developer service, MentrixRun as plan SoT.

## Work packages

1. **TI cleanup** â€” TI-001 auth fixture, TI-002 Vitest/e2e exclude
2. **Ingest** â€” Jira + Camunda adapters â†’ WorkItem + project/repo binding
3. **ProjectIntelligence fill** â€” Lattice, Blueprint, KB, Memory, related WorkItems, Skills, Playbooks, freshness
4. **Developer path** â€” MentrixDeveloperService uses live PI snapshot
5. **Fabric handoff** â€” approved plan / WI context â†’ Fabric classify/run â†’ Coding Agent
6. **Delivery quality** â€” ForgeLoop + Ultra Review consume WI/evidence; dual-write plan only
7. **Close loop** â€” EvidenceVerifier â†’ READY_TO_SHIP â†’ PR + Jira comment/transition + Camunda complete
8. **Connectivity tests** â€” end-to-end gap suite + update `ZECT_GAP_ANALYSIS.md`

## Out of scope

P2 sidebar/UX, System Health, full Skills filesystem migrate, claiming full Playwright green.

## Plan hash / reapproval

Same P0 rules: ArtifactStore owns PLAN.md; material hash change clears `approved_plan_hash`.
