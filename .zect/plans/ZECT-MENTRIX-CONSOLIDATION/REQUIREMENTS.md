# REQUIREMENTS — ZECT Mentrix Consolidation P0

Traceability IDs **R1–R22** map to EXECUTION_MANIFEST `requirements[]`.

## Core (R1–R8)

| ID | Requirement | Pri | Acceptance |
|----|-------------|-----|------------|
| R1 | MentrixDeveloperService owns ASK/PLAN/AGENT orchestration | P0 | Unit + API |
| R2 | Canonical WorkItem model with SDLC status enums | P0 | Schema + tests |
| R3 | ArtifactStore owns PLAN.md; MentrixRun dual-write only | P0 | SoT + dual-write test |
| R4 | MentrixContextEngine builds bounded ContextPack | P0 | Pack schema test |
| R5 | ProjectIntelligenceService P0 interface contract | P0 | Snapshot test |
| R6 | Knowledge and Memory remain semantically different | P0 | Separate keys/stores |
| R7 | ForgeLoop Ask/Plan via openai_compat; native build fail-closed | P0 | Gateway + fail-closed tests |
| R8 | EvidenceVerifier gates READY_TO_SHIP; LLM text alone cannot COMPLETE | P0 | Verifier unit |

## Revision (R9–R22)

| ID | Requirement | Pri | Acceptance |
|----|-------------|-----|------------|
| R9 | WorkItem has repository_id, repository_ref, base_commit_sha | P0 | Model fields |
| R10 | WorkItemEvent mandatory, append-only (no update/delete) | P0 | Append-only test |
| R11 | Canonical WorkItem.status SDLC + side enums | P0 | Enum match SDLC doc |
| R12 | plan_version, plan_hash, approved_plan_hash; reapproval on material PLAN.md change | P0 | Reapproval test |
| R13 | ContextPack item provenance: source_type, source_id, repository, commit_sha, retrieval_score, freshness, verification_state, token_count, selection_reason | P0 | Provenance keys |
| R14 | PI includes Lattice, Blueprint, Knowledge, Memory, related_work, skill_selection, playbook_selection, freshness (Skills/Playbooks may be empty) | P0 | Contract test |
| R15 | Manifest ops: requirement_ids, dependencies, mandatory, attempts, max_attempts, evidence_ids | P0 | Schema |
| R16 | Checkpoints: op start, file changes, command, verification, completion, failure, blocking | P0 | Checkpoint types |
| R17 | Resume identity: worktree_path, base_commit_sha, current_commit_sha | P0 | EXECUTION_STATE + resume test |
| R18 | EvidenceVerifier: operation + requirement + acceptance coverage; typed evidence enum | P0 | Coverage matrix |
| R19 | Model telemetry: requested/actual provider+model, fallback_used, fallback_reason, latency_ms, work_item_id, agent_run_id, operation_id | P0 | Telemetry fields |
| R20 | Fallback policies never\|ask\|automatic; never must not send context to cloud | P0 | Three policy tests |
| R21 | WorkItemSourceAdapter Protocol + stubs (no full Jira/Camunda/GitHub ingest) | P0 | Import + stub |
| R22 | P0 E2E: WorkItem→Plan→approve→Agent→file change→verify→checkpoint→EvidenceVerifier→READY_TO_SHIP; real Coding Agent smoke OP-023b | P0 | OP-023b + OP-035 green |

## NFR

| ID | Requirement |
|----|-------------|
| NFR-001 | Fail-closed when required; no silent mock/cloud fallback |
| NFR-002 | Preserve unrelated tracked/untracked files |
| NFR-003 | No P1/P2/P3 product work in this execution |
| NFR-004 | After every op: verify, evidence, checkpoint, update EXECUTION_MANIFEST |
| NFR-005 | Do not mark P0 COMPLETE if any mandatory op/AC incomplete → BLOCKED |

## Out of scope (P1+)

Full Jira/Camunda WorkItem ingestion, Ultra Review redesign, sidebar redesign, System Health, full Skills/Playbooks migrate.
