# ZECT Gap Analysis (P0 revised)

States: COMPLETE | PARTIAL | DUPLICATED | DISCONNECTED | MOCK | MISSING | DEFERRED | P0_BUILD

| Capability | Current State | Evidence | Gap | Target | Required Change | Priority |
|---|---|---|---|---|---|---|
| Companion | PARTIAL | companion.py | Not sole router | MentrixDeveloperService front door | Route developer intents | P0 |
| Developer Workspace | PARTIAL | DeveloperWorkspace.tsx | Not primary ASK/PLAN/AGENT | Mentrix Developer | Wire service | P0 |
| Ask | DUPLICATED | llm.py + llm_phase.py | Dual model paths | One via gateway | Unify openai_compat | P0 |
| Plan | DUPLICATED | /plan vs MentrixRun | No ArtifactStore PLAN.md | Canonical PLAN.md | ArtifactStore + dual-write | P0 |
| Agent / Coding Agent | PARTIAL | coding_engine_mentrix.py | Not sole Build | Sole executor | Fail-closed native | P0 |
| ForgeLoop | COMPLETE | orchestrator.py | No op accounting | Manifest + verifier | Hook | P0 |
| Fabric | PARTIAL | domains/fabric | Manual | Auto from PLAN | P1 auto | P1 |
| Ultra Review | PARTIAL | review_service.py | No 3-lane | Redesign | P1 | P1 |
| Lattice | PARTIAL | in-memory cache | Ephemeral | Durable+freshness | P1 | P1 |
| Blueprint | DUPLICATED | multi generators | Split | One service | P1 | P1 |
| Knowledge | PARTIAL | knowledge_base.py | Not all paths | PI contract | Wire PI | P0 |
| Memory | PARTIAL | TypedMemory | No validation_status | Separate from KB | PI API | P0 |
| Skills | PARTIAL | DB SkillDefinition | Empty selection OK P0 | Contract | PI stub | P0 |
| Playbooks | PARTIAL | playbook_executor | Weak Coding Agent | Contract | PI stub | P0 |
| Jira full | PARTIAL | adapters | No WorkItem pipeline | Full ingest | P1 | P1 |
| Camunda full | PARTIAL | process REST | Deploy/start only | Task→WI | P1 | P1 |
| WorkItem identity | COMPLETE | models.WorkItem | — | WorkItem model | OP-010 | P0 |
| WorkItemEvent | COMPLETE | WorkItemEvent append-only | — | Events | OP-015 | P0 |
| Status enums | COMPLETE | domains/work_items/status.py | — | Enums | OP-010 | P0 |
| PLAN ownership | COMPLETE | ArtifactStore | Dual-write MentrixRun | ArtifactStore | OP-012 | P0 |
| Plan reapproval | COMPLETE | plan_hash/approved_plan_hash | — | Reapproval | OP-012b | P0 |
| ContextPack provenance | COMPLETE | MentrixContextEngine | — | ContextEngine | OP-013 | P0 |
| ProjectIntelligence | COMPLETE | ProjectIntelligenceService | Skills/Playbooks empty OK | PI service | OP-014 | P0 |
| Manifest ops schema | COMPLETE | EXECUTION_MANIFEST.json | — | Schema | OP-030 | P0 |
| Checkpoints rich | COMPLETE | checkpoints.py | — | Recorder | OP-030 | P0 |
| Resume worktree/commits | COMPLETE | EXECUTION_STATE + resume() | — | EXECUTION_STATE | OP-032 | P0 |
| EvidenceVerifier | COMPLETE | evidence_verifier.py | — | Verifier | OP-031 | P0 |
| Typed evidence | COMPLETE | EVIDENCE_TYPES | — | Evidence model | OP-031 | P0 |
| Model telemetry | COMPLETE | telemetry.py | — | Telemetry | OP-033 | P0 |
| Fallback never/ask/auto | COMPLETE | fallback_policy.py | — | Policy module | OP-034 | P0 |
| Coding Agent smoke | COMPLETE | test OP-023b deterministic native tools | — | Smoke | OP-023b | P0 |
| SourceAdapter | COMPLETE | WorkItemSourceAdapter stubs | — | Interface | OP-016 | P0 |
| Ownership doc | COMPLETE | ZECT_DATA_FLOW_AND_OWNERSHIP.md | — | — | Phase A | P0 |
| P0 E2E READY_TO_SHIP | COMPLETE | test_e2e_work_item_to_ready_to_ship | — | Integration | OP-035 | P0 |
| MentrixDeveloperService | COMPLETE | developer_service.py + API | — | Service | OP-020 | P0 |
| Sidebar / Health | PARTIAL | Sidebar.tsx | Sprawl | P2 | Defer | P2 |
| E2E Playwright suite | PARTIAL | 13 fail/53 pass | Flakes | Green | P1 | P1 |
