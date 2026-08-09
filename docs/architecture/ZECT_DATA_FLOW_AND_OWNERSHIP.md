# ZECT Data Flow and Ownership (P0)

## Ownership table

| Concern | Canonical owner (P0) | Compatibility dual-write | Must not own |
|---------|----------------------|--------------------------|--------------|
| PLAN.md text + hash | WorkItem ArtifactStore `.zect/work/<id>/PLAN.md` | `MentrixRun.result_json["plan"]` | Standalone `/plan` as SoT |
| EXECUTION_MANIFEST / STATE / EVIDENCE | ArtifactStore | MentrixRun events summary | LLM chat |
| WorkItem lifecycle status | WorkItem.status enum | MentrixRun.status for Delivery UI | Companion ephemeral |
| Append-only audit | WorkItemEvent | MentrixRun.events_json | Overwrites |
| ContextPack | MentrixContextEngine | companion/agent_context callers | Whole Lattice dump |
| Code edits | Mentrix Coding Agent `mentrix_native` | ForgeLoop build delegates | Silent mock build in product |
| SDLC gates | ForgeLoop | WorkItem READY_TO_SHIP after EvidenceVerifier | LLM done text |
| Knowledge vs Memory | Separate stores via ProjectIntelligence | â€” | Single collapsed vector DB |
| Future Jira/Camunda/GitHub | WorkItemSourceAdapter contract | Stubs only in P0 | Full P1 ingest in P0 |

## Data flow

```
WorkItemSourceAdapter â†’ WorkItem â†’ WorkItemEvent (append-only)
WorkItem â†’ ArtifactStore (PLAN.md, MANIFEST, STATE, EVIDENCE)
MentrixDeveloperService â†’ ContextEngine + ProjectIntelligence + Coding Agent
Coding Agent / ForgeLoop â†’ ArtifactStore checkpoints
EvidenceVerifier â†’ ArtifactStore + WorkItem.status READY_TO_SHIP
```

## Plan reapproval

`plan_version`, `plan_hash`, `approved_plan_hash` on WorkItem.
Material PLAN.md change after approve clears `approved_plan_hash` and requires reapproval.
