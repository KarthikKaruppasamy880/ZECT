# ZECT SDLC and WorkItem Flow

**Canonical parent:** [`ZECT_SYSTEM_ARCHITECTURE.md`](../../ZECT_SYSTEM_ARCHITECTURE.md)  
**Evidence:** [`ZECT_PRODUCT_ACCEPTANCE.md`](../../ZECT_PRODUCT_ACCEPTANCE.md)  
**Code:** `backend/app/domains/work_items/status.py`, `service.py`, `evidence_verifier.py`

## Forward statuses

```text
NEW → INGESTED → ANALYZED → PLANNED → PLAN_APPROVED
  → EXECUTING → IMPLEMENTED → VERIFYING → REVIEWING
  → ACCEPTANCE_TESTING → READY_TO_SHIP → SHIP_APPROVED
  → PR_CREATED → CI_GREEN → DONE
```

## Side statuses

`BLOCKED` · `FAILED_VERIFICATION` · `NEEDS_HUMAN_DECISION` · `CANCELLED`

## Completion gates

`GATE_STATUSES = { READY_TO_SHIP, DONE }`

| Rule | Behavior |
|------|----------|
| HTTP `POST /api/work-items/{id}/transition` | Always `allow_gate=False` → **403** if targeting gate statuses |
| EvidenceVerifier pass via MentrixDeveloperService / close-loop | `allow_gate=True` permitted |
| LLM text alone | **Cannot** READY_TO_SHIP (`test_evidence_verifier_rejects_llm_only`) |

Typed evidence required (`EVIDENCE_TYPES`); coverage of mandatory ops / requirements / acceptance IDs.

## Artifact ownership

Under `.zect/work/<work_item_id>/` (or `ZECT_ARTIFACT_ROOT`):

| Artifact | Purpose |
|----------|---------|
| `PLAN.md` | Canonical plan text |
| `EXECUTION_MANIFEST.json` | Ops / req / acceptance IDs |
| `EXECUTION_STATE.json` | Checkpoint + resume identity (worktree, commits) |
| `EVIDENCE.json` | Typed evidence for verifier |

Plan reapproval: material PLAN change clears `approved_plan_hash`.

## Happy path (accepted)

1. Create / ingest WorkItem (user | jira | camunda)  
2. Plan → ArtifactStore + approve  
3. Agent / Coding Agent → file change + checkpoints  
4. Ultra Review lanes (optional quality)  
5. EvidenceVerifier → `READY_TO_SHIP`  
6. Git/PR/CI → close-loop dry_run to Jira/Camunda when configured  

Evidence: `test_e2e_work_item_to_ready_to_ship`, gate 403 test, P1 close-loop dry_run.
