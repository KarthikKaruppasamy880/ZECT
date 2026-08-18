# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-18  
**Canonical develop:** `origin/develop` = `51150dbd9b14d7504fba6f3919a4d1e577d73cf8` (PR **#159** human-merged).  
**This working branch:** `feat/work-intelligence-production`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md`  
**No auto-merge.** S8C / S8D / Graphify / KV-cache / OCR-XLSX / broader Web / new-agent roadmap: **not started**.

Companion PASS, Coding Agent PASS, Present/Voice PARTIAL, and Work intelligence **partial** proof do **not** make overall ZECT production-ready.

## Git truth

| Item | Value |
|------|--------|
| Merged | #156 Developer multi-root; #157 Companion; **#158 Coding Agent**; **#159 Present + Voice** |
| This PR | Projects / WorkItems / Processes / Lattice per-root production proof |
| Unrelated WIP | leftover acceptance markdown / `prompts/` / `.zect/skills/` — **not** claimed complete |
| Presenton | Product default (`:8000`). Native Present opt-in. **Not flipped.** |

Nothing local-only is called complete. Missing evidence is not PASS.

## Matrix

| Surface | Capability | files | commit / PR | on develop? | browser | Electron | security | operational | status | blocker |
|---------|------------|-------|-------------|-------------|---------|----------|----------|-------------|--------|---------|
| Companion | HUD/dock orchestration, provenance, canonical handoffs | `MentrixCompanion.tsx`, `companion.py` | **#157** | **yes** | headed missions A–G **PASS** | Electron HUD/handoff **PASS** | broker | Local Jira env; Camunda unset | **PASS** (orchestration) | Live Jira create-issue not in Companion |
| Developer chrome | Explorer \| Editor \| Agent + bottom tabs | `DeveloperWorkspace.tsx` | #154+#156 | **yes** | headed | Electron restore #156 | path jail | layout persist | **PASS** (chrome) | Overall ZECT still PARTIAL |
| Developer multi-root | Merged explorer, terminals, search, git jail | `WorkspaceRootsRail.tsx` | #156 | **yes** | headed | headed restore **PASS** | bound_root | ROOT_UNAVAILABLE | **PASS** | Semantic cross-repo refs; live GitHub `BLOCKED_EXTERNAL` |
| Lattice / context | Canonical states + SHA STALE per root | `indexer.py`, `lattice.py`, roots rail | **this PR** + #154 | **no** until merge | header + per-root SHA | skip ≠ core | repo-scoped keys | STALE on commit | **PASS** (per-root; no Graphify) | Graphify out of scope |
| Coding Agent | PLAN → worktree → edit/test/review/git | `lifecycle.py`, `MentrixCodingAgentPanel.tsx` | **#158** | **yes** | `coding-agent-production.spec.ts` | `coding-agent-electron.spec.ts` | git always-confirm | in-memory missions | **PASS** (lifecycle) | Live GitHub `BLOCKED_EXTERNAL`; restart persistence tranche E |
| WorkItem / multi-repo agent | ASK/PLAN/AGENT + isolated worktrees + UI detail | `multi_repo_agent.py`, `WorkItemDetailPanel.tsx` | **this PR** | **no** until merge | `work-intelligence-production.spec.ts` | `work-intelligence-electron.spec.ts` (skip ≠ core) | authorized repo ids; 403 without verifier | aggregate READY | **PASS** (lifecycle + UI) | Live GitHub `BLOCKED_EXTERNAL` |
| Ultra Review | Findings + closed loop | `ultrareview.py` | #138+#158+#159 | yes | unit | n/a | MERGE_ELIGIBLE | fixture git | **PARTIAL** | CodeRabbit skip ≠ PASS |
| Present | Dashboard→Create→Review→Export Quality/Fast | Present pages, inspector, import fail-closed | **#159** | **yes** | `present-voice-production.spec.ts` | `present-voice-electron.spec.ts` (skip ≠ core) | 409 critical block; invalid PPTX 400 | Presenton default | **PARTIAL** | Live Generate `BLOCKED_EXTERNAL` without Presenton; COM opt-in |
| Voice | Clone / stock / none, overlap, cancel | `CloneVoicePanel.tsx`, `speak.ts`, `voice_clone.py` | **#159** | **yes** | selectors + engine status | Electron clone panel | cross-user 404 | Voicebox | **PARTIAL** | Voicebox/stock live speak `BLOCKED_EXTERNAL` |
| Projects / Processes | Fixture isolation, sample + ingest, connector chips | `fixture_isolation.py`, `MentrixFabric.tsx` | **this PR** | **no** until merge | hygiene + work-intelligence e2e | Electron processes | provenance hide | sample + fixture ingest | **PARTIAL** | Real Jira/Camunda `BLOCKED_EXTERNAL` |
| Security | Broker, SSRF, sandbox | `permission_broker.py` | prior+#157+#158 | yes | unit/CI | n/a | companion + git confirm | no live campaign | **PARTIAL** | Full-product threat campaign is tranche D |
| Install / recovery | Alembic, sidecar | `alembic/` | #146 | yes | n/a | sidecar exists | n/a | NSIS unproven | **PARTIAL** | Clean-machine NSIS; coding-agent in-memory |
| Performance / soak | LRR endurance script | `live_lrr_endurance.py` | prior | script only | n/a | n/a | n/a | no CI soak | **FAIL** (evidence) | No bounded soak |
| Observability | Some correlation | SecurityFinding | prior | yes | n/a | n/a | avoid secret logs | not global | **PARTIAL** | No repo-wide `x-correlation-id` |
| Accessibility | SplitPane ARIA | scattered | #154 | yes | not audited | not audited | n/a | n/a | **PARTIAL** | No WCAG sweep (tranche G) |

## Suggested PR sequence (human-merge each)

| PR | Topic | This session |
|----|--------|----------------|
| B | Developer multi-root / workspace UX | **#156 merged** |
| A | Companion production closure | **#157 merged** |
| C | Coding-agent missions A–G | **#158 merged** |
| D | Present + Voice re-proof | **#159 merged** |
| E | WorkItems / Processes / Lattice per-root | **this PR — stop at READY_TO_MERGE_WORK_INTELLIGENCE, no auto-merge** |
| F | Security / ops / soak / a11y | not started |

## This PR (Work intelligence)

Human-merge after CI. Remaining **outside** this tranche:

- Live Jira / Camunda ticket/process completion (`BLOCKED_EXTERNAL` when unset)
- Live GitHub PR
- Graphify / S8C / S8D
- Security campaign, recovery, soak, a11y, full-release E2E (tranches D–H)

## Verdict so far

**ZECT_PRODUCTION_PARTIAL.** Canonical develop is healthy post-#159. This PR completes WorkItem/Process/Lattice production-lifecycle proof with honest external gates; it does **not** make overall ZECT production-grade.
