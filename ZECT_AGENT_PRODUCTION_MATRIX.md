# ZECT Agent Production Matrix

**Date:** 2026-08-17  
**Canonical develop:** `c37f24a` (PR #157 Companion human-merged).  
**This working branch:** `feat/coding-agent-production`  
**Rule:** An internal service class is not an agent. One responsibility each.

| Agent | purpose | inputs | tools | permissions | context | outputs | human gate | tests | browser | Electron | recovery | production status |
|-------|---------|--------|-------|-------------|---------|---------|------------|-------|---------|----------|----------|-------------------|
| Mentrix Companion | Orchestrate Developer/Present/Work; do not duplicate them | chat, voice, project/repo | brokered tools | permission broker; always-confirm writes | PI/Lattice/memory/skills | navigate, artifacts | Allow overlay | companion unit + e2e | PASS (PR #157) | PASS (PR #157) | stream resume | **PASS** (orchestration) on develop |
| Mentrix Coding Agent | Canonical edit/test/review/git loop | goal, authorized roots, optional patches | list/read/write/patch/run/git_status/git_diff/git_commit/git_push + lifecycle | path jail; git always-confirm; PLAN then git approval | agent_context + worktrees | mission JSON, diffs, READY_TO_MERGE | PLAN + git; no auto-merge | `test_coding_agent_production.py` A–G | headed production spec | Electron pane (skip ≠ core skip) | cancel/resume; in-memory store PARTIAL | **this PR** |
| Developer / WorkItem agent | ASK→PLAN→AGENT→evidence | WorkItem, repo ids | Developer API, ArtifactStore, EvidenceVerifier | approve_plan | multi-repo packs | PLAN, manifests, status | READY_TO_SHIP via verifier | multi-repo pytest | UI thinner | n/a | checkpoints | **PARTIAL** |
| Multi-Repo Agent | Isolated worktree per affected repo | EXECUTION_MANIFEST | worktrees, tests, review lanes | authorized repos only | per-repo packs | aggregate gates | no auto-merge | `test_multi_repo_developer.py` | status strip | n/a | sibling failure blocks | **PARTIAL** |
| Ultra Review | Review + closed-loop fix | PR/snippet/diff | `/api/ultrareview`, `run_ultra_review` | post-approval GitHub fixes | ReviewFinding | MERGE_ELIGIBLE / mission block | security not waiveable | closed-loop + coding-agent review | n/a | n/a | fixture | **PARTIAL** (CodeRabbit SKIPPED ≠ PASS) |
| Learning mentor | Guided practice; handoff to Developer | lesson, mode | `/api/learning/*` | GUIDED forbids auto-solve | curriculum | progress, WorkItem | explicit events | companion/learning tests | PARTIAL | n/a | n/a | **PARTIAL** |
| ZECT Security (malware) | Scan / quarantine assist | path | `/api/security/malware/*` | path policy | detection adapter | scan status | quarantine confirm | threat tests | n/a | n/a | daemon | **PARTIAL** |
| Mentrix Delivery (ForgeLoop) | Delivery FSM | goal, workspace | gates, approve, create PR | human approve before PR | MentrixRun | PR URL | approve | e2e approve-pr | PARTIAL | n/a | dry_run default | **PARTIAL** |
| Presentation | Grounded PPTX | prompt/deck | presentation_api, inspector | sensitivity / export 409 | claims | PPTX | export blocked on critical | P0 quality tests | PARTIAL | session PASS | Presenton | **PARTIAL** — tranche B not started |

Not agents: generic IR ingest, collaboration presence WebSocket, Lattice indexer, fixture isolation.
