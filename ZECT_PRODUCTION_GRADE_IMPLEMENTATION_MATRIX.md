# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-17  
**Canonical develop:** `origin/develop` = `9f88885778bb0315ccc694156903bcd19d6745a0` (PR **#156** human-merged).  
**Local develop:** `9f88885` — **equals** `origin/develop`.  
**This working branch:** `feat/mentrix-companion-production`  
**Prompt:** `prompts/ZECT_MENTRIX_COMPANION_PRODUCTION_CLOSURE.md`  
**No auto-merge.** S8C / S8D / Graphify / KV-cache / OCR-XLSX / broader Web / new-agent roadmap / Coding Agent A–G: **not started**.

Companion PASS does **not** make overall ZECT production-ready.

## Git truth

| Item | Value |
|------|--------|
| Open PRs targeting develop | #82 Lattice fixture (stale); #33 Active Project selector (`devin/` branch — do not touch) |
| Stashes preserved | 4 unrelated WIP stashes |
| Untracked preserved | `prompts/`, `.zect/skills/`, other leftover acceptance markdown, fixtures — **not** claimed complete |
| Presenton | Product default (`:8000`). Native Present opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native`) |

Nothing local-only is called complete.

## Matrix

| Surface | Capability | files | commit / PR | on develop? | browser | Electron | security | operational | status | blocker |
|---------|------------|-------|-------------|-------------|---------|----------|----------|-------------|--------|---------|
| Companion | HUD/dock orchestration, provenance, canonical handoffs | `MentrixCompanion.tsx`, `companion.py`, `companion_scope.py`, `permission_broker.py` | this PR | **no** until merge | headed missions A–G **PASS** | Electron HUD/handoff/reconnect **PASS** | broker + unauthorized repo skip | Local Jira env set → Work Items identity handoff; Camunda unset | **PASS** (orchestration) | Live Jira create-issue API not in Companion; semantic cross-repo refs not implemented |
| Developer chrome | Explorer \| Editor \| Agent + bottom tabs, persist, maximize | `DeveloperWorkspace.tsx`, `workspaceChrome.ts` | #154+#156 | **yes** | headed hygiene + search tab | Electron restore #156 | path jail on active root | layout persist | **PASS** (chrome) | Overall ZECT still PARTIAL |
| Developer multi-root | Merged A+B+C explorer, locked terminals, search, git jail, Electron restore | `WorkspaceRootsRail.tsx`, `workspace_search.py`, `workspace_multi_root.py` | #156 | **yes** | headed `workspace-multi-root.spec.ts` | headed restore spec **PASS** | bound_root + pathspec jail | ROOT_UNAVAILABLE + session persist | **PASS** | Semantic cross-repo refs not implemented; live GitHub multi-PR `BLOCKED_EXTERNAL` |
| Lattice / context | Canonical states + SHA STALE | `indexer.py`, `lattice.py`, `WorkspaceContextUsedPanel.tsx` | #154 | yes | header chip + Context tab | not re-run | repo-scoped status | STALE on commit move | **PARTIAL** | Per-root indexing UX incomplete; Graphify out of scope |
| Coding Agent | Interactive edit loop | `MentrixCodingAgentPanel.tsx`, `mentrix_agent_tools.py` | prior | yes | panel in workspace | not mission-proven | path jail; cmd approval | worktree isolation | **PARTIAL** | Native tools lack commit/push/PR; Missions A–G unlabeled |
| WorkItem / multi-repo agent | ASK/PLAN/AGENT + isolated worktrees | `multi_repo_agent.py`, `DeveloperMultiRepoStatus.tsx` | #144/#148 | yes | status strip | n/a | authorized repo ids | aggregate READY | **PARTIAL** | Live GitHub PR / READY_AFTER_FIX `BLOCKED_EXTERNAL` |
| Ultra Review | Findings + closed loop | `ultrareview.py`, closed-loop tests | #138 | yes | unit | n/a | MERGE_ELIGIBLE | fixture git | **PARTIAL** | Live GitHub optional; CodeRabbit skip ≠ PASS |
| Present | Dashboard→Create→Review→Export Quality/Fast | Present pages, inspector, renderer XOR | #153/#154 | yes | headed P0 (session) | Generate→Review→Export (session) | 409 critical block | Presenton default | **PARTIAL** | COM evidence not in git; Presenton Docker often down; Companion handoff only this PR |
| Voice | Clone / stock / none, overlap, reconnect | `CloneVoicePanel.tsx`, `speak.ts`, `realtime.py` | prior | yes | selectors + mute | Electron Connect Voice control | ownership unit | Voicebox | **PARTIAL** | ≥2-slide live clone unproven; Companion conversational controls proven |
| Projects / WorkItems / Processes | Fixture isolation, sample process | `fixture_isolation.py`, WorkItems UI | #150+#154 | yes | hygiene e2e | n/a | provenance hide | sample only | **PARTIAL** | Real Jira/Camunda `BLOCKED_EXTERNAL` |
| Security | Broker, SSRF, sandbox, untrusted context | `permission_broker.py`, `ssrf.py`, sandbox tests | prior+this | yes | unit/CI | n/a | companion injection + repo skip | no live campaign | **PARTIAL** | No full-product threat campaign this SHA |
| Install / recovery | Alembic, sidecar, LRR restart unit | `alembic/`, packaging tests | #146 | yes | n/a | sidecar exists | n/a | NSIS unproven | **PARTIAL** | Clean-machine NSIS `BLOCKED_EXTERNAL` |
| Performance / soak | LRR endurance script | `live_lrr_endurance.py` | prior | script only | n/a | n/a | n/a | no CI soak | **FAIL** (evidence) | No bounded soak at this SHA |
| Observability | Some correlation on findings | SecurityFinding, companion | prior | yes | n/a | n/a | avoid secret logs | not global | **PARTIAL** | No repo-wide `x-correlation-id` middleware |
| Accessibility | SplitPane ARIA, some labels | scattered | #154 | yes | not audited | not audited | n/a | n/a | **PARTIAL** | No WCAG sweep |

## Suggested PR sequence (human-merge each)

| PR | Topic | This session |
|----|--------|----------------|
| B | Developer multi-root / workspace UX | **#156 merged** |
| A | Companion production closure | **this PR — stop at READY_TO_MERGE_COMPANION, no auto-merge** |
| C | Coding-agent missions A–G | not started |
| D | Present + Voice re-proof | not started |
| E | WorkItems / Processes / Lattice per-root | not started |
| F | Security / ops / soak / a11y | not started |

## This PR (Companion production)

Human-merge after CI. Remaining **outside** this tranche:

- Semantic cross-repo references
- Live Jira / Camunda / Slack send (`BLOCKED_EXTERNAL` without credentials)
- Coding Agent missions A–G
- Present Generate/Export re-proof / Graphify

## Verdict so far

**ZECT_PRODUCTION_PARTIAL.** Canonical develop is healthy post-#156. This PR completes the Mentrix Companion production-orchestration gate for human merge; it does **not** make overall ZECT production-grade.
