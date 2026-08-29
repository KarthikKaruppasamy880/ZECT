# ZECT SDLC Architecture

## Canonical WorkItem.status (P0)

```
NEW â†’ INGESTED â†’ ANALYZED â†’ PLANNED â†’ PLAN_APPROVED â†’ EXECUTING â†’ IMPLEMENTED
  â†’ VERIFYING â†’ REVIEWING â†’ ACCEPTANCE_TESTING â†’ READY_TO_SHIP â†’ SHIP_APPROVED
  â†’ PR_CREATED â†’ CI_GREEN â†’ DONE
```

Side: `BLOCKED`, `FAILED_VERIFICATION`, `NEEDS_HUMAN_DECISION`, `CANCELLED`

Only EvidenceVerifier / orchestrator may set READY_TO_SHIP / DONE. LLM text cannot.

## Manifest op status

`pending` | `running` | `completed` | `failed` | `blocked` | `skipped-with-approval`

## ForgeLoop coexistence

ForgeLoop remains Mentrix Delivery FSM (`MentrixRun`).
P0 WorkItem + ArtifactStore are canonical for plan/evidence.
Dual-write plan to MentrixRun.result_json for Delivery UI compatibility.

## Fabric

Classify/refuse/run â†’ Coding Agent (exists). Auto-from-PLAN is P1.

## Evidence types

FILE_EXISTS, FILE_CHANGED, COMMAND_EXIT, TEST_RESULT, BUILD_RESULT, LINT_RESULT, TYPECHECK_RESULT, API_RESULT, UI_RESULT, SECURITY_RESULT, REVIEW_FINDING, HUMAN_APPROVAL
