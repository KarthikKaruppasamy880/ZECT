# ZECT Gap Analysis (P0 + P1)

States: COMPLETE | PARTIAL | DUPLICATED | DISCONNECTED | MOCK | MISSING | DEFERRED | P0_BUILD | P1_COMPLETE

| Capability | Current State | Evidence | Gap | Target | Required Change | Priority |
|---|---|---|---|---|---|---|
| Companion | PARTIAL | companion.py | Not sole router | MentrixDeveloperService front door | Route developer intents | P0 |
| Developer Workspace | PARTIAL | DeveloperWorkspace.tsx | Not primary ASK/PLAN/AGENT | Mentrix Developer | Wire service | P0 |
| Ask | COMPLETE | MentrixDeveloperService.ask + PI | — | Gateway path | P0/P1 | P0 |
| Plan | COMPLETE | ArtifactStore PLAN.md | — | Canonical PLAN.md | ArtifactStore | P0 |
| Agent / Coding Agent | COMPLETE | mentrix_native | — | Sole executor | Fail-closed native | P0 |
| ForgeLoop | COMPLETE | orchestrator + ownership.py | — | mentrix_native SoT | OP-032 | P1 |
| Fabric | COMPLETE | fabric_handoff.py | — | Approved WI/PLAN | OP-031 | P1 |
| Ultra Review | COMPLETE | ultra_review_context.py | 3-lane redesign deferred | Consume WI/ContextPack | OP-033 | P1 |
| Lattice | PARTIAL | PI freshness flags | Full durable store | Durable+freshness | Minimal P1 | P1 |
| Blueprint | COMPLETE | PI → LatticeStructuralBlueprint | Multi generators remain | PI consume | OP-020 | P1 |
| Knowledge | COMPLETE | retrieve_knowledge_for_context via PI | — | PI contract | OP-020 | P1 |
| Memory | COMPLETE | TypedMemoryRecord via PI | — | Separate from KB | OP-020 | P1 |
| Skills | COMPLETE | SkillDefinition selection in PI | FS migrate deferred | PI selection | OP-021 | P1 |
| Playbooks | COMPLETE | Playbook selection in PI | — | PI selection | OP-021 | P1 |
| Jira full | COMPLETE | JiraSourceAdapter + ingest + close_loop | Live env optional | Full ingest | OP-010/040 | P1 |
| Camunda full | COMPLETE | CamundaSourceAdapter + ingest + close | Live env optional | Task→WI | OP-011/040 | P1 |
| WorkItem identity | COMPLETE | models.WorkItem | — | WorkItem model | OP-010 | P0 |
| WorkItemEvent | COMPLETE | WorkItemEvent append-only | — | Events | OP-015 | P0 |
| Status enums | COMPLETE | domains/work_items/status.py | — | Enums | OP-010 | P0 |
| PLAN ownership | COMPLETE | ArtifactStore | Dual-write MentrixRun | ArtifactStore | OP-012 | P0 |
| Plan reapproval | COMPLETE | plan_hash/approved_plan_hash | — | Reapproval | OP-012b | P0 |
| ContextPack provenance | COMPLETE | MentrixContextEngine | — | ContextEngine | OP-013 | P0 |
| ProjectIntelligence | COMPLETE | ProjectIntelligenceService live fill | — | PI service | OP-020/021 | P1 |
| Manifest ops schema | COMPLETE | EXECUTION_MANIFEST.json | — | Schema | OP-030 | P0 |
| Checkpoints rich | COMPLETE | checkpoints.py | — | Recorder | OP-030 | P0 |
| Resume worktree/commits | COMPLETE | EXECUTION_STATE + resume() | — | EXECUTION_STATE | OP-032 | P0 |
| EvidenceVerifier | COMPLETE | evidence_verifier.py | — | Verifier | OP-031 | P0 |
| Typed evidence | COMPLETE | EVIDENCE_TYPES | — | Evidence model | OP-031 | P0 |
| Model telemetry | COMPLETE | telemetry.py | — | Telemetry | OP-033 | P0 |
| Fallback never/ask/auto | COMPLETE | fallback_policy.py | — | Policy module | OP-034 | P0 |
| Coding Agent smoke | COMPLETE | test OP-023b | — | Smoke | OP-023b | P0 |
| SourceAdapter | COMPLETE | Jira + Camunda + user | — | Adapters | OP-010/011 | P1 |
| Ownership doc | COMPLETE | ZECT_DATA_FLOW_AND_OWNERSHIP.md | — | — | Phase A | P0 |
| P0 E2E READY_TO_SHIP | COMPLETE | test_e2e_work_item_to_ready_to_ship | — | Integration | OP-035 | P0 |
| MentrixDeveloperService | COMPLETE | developer_service.py + API | — | Service | OP-020 | P0 |
| Close-loop external | COMPLETE | close_loop.py dry_run default | Live write optional | PR/Jira/Camunda | OP-040 | P1 |
| Connectivity suite | COMPLETE | test_mentrix_p1_project_intelligence.py | — | Spine tests | OP-050 | P1 |
| TI-001 auth fixture | COMPLETE | main.py ZECT_PYTEST preserve + conftest | — | Authed HTTP | OP-001 | P1 |
| TI-002 Vitest/e2e | COMPLETE | vite.config + npm test exclude | — | Unit-only | OP-002 | P1 |
| Sidebar / Health | COMPLETE | Sidebar.tsx + SystemHealth | — | Target nav + health | OP-100/120 | P2 |
| E2E Playwright suite | PARTIAL | smoke nav updated | Full suite flakes | Smoke + nav | OP-150 | P2 |
| Skills FS migrate | COMPLETE | `.zect/skills` dual-read | Full DB migrate deferred | Dual-read | OP-130 | P2 |
| Ultra Review 3-lane redesign | COMPLETE | ultra_review_lanes.py | Deep LLM lanes deferred | Merger over findings | OP-140 | P2 |
| SecurityScanner | COMPLETE | security_scanner.py | Native deep scan deferred | Interface + adapter | OP-200 | P3 |
| Local model readiness | COMPLETE | /api/system/model-readiness | — | Gateway hook | OP-210 | P3 |
| Work Items UX | COMPLETE | WorkItems.tsx | — | List page | OP-110 | P2 |
| Project Intelligence UX | COMPLETE | ProjectIntelligence.tsx | — | PI page | OP-110 | P2 |
| Context Used panel | COMPLETE | WorkspaceContextUsedPanel | Ideal ASK/PLAN/AGENT chrome partial | PI provenance rail | OP-CTX | P2 |
