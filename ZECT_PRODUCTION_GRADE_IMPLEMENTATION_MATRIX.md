# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-17  
**Canonical develop:** `origin/develop` = `c37f24a86943ae1f9683a834f59d995a5423096d` (PR **#157** human-merged).  
**This working branch:** `feat/coding-agent-production`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md`  
**No auto-merge.** S8C / S8D / Graphify / KV-cache / OCR-XLSX / broader Web / new-agent roadmap / Present+Voice tranche: **not started**.

Companion PASS and Coding Agent PASS do **not** make overall ZECT production-ready.

## Git truth

| Item | Value |
|------|--------|
| Merged | #156 Developer multi-root; #157 Companion production |
| This PR | Coding Agent production lifecycle A–G |
| Unrelated WIP | 4 stashes + leftover acceptance markdown / `prompts/` / `.zect/skills/` — **not** claimed complete |
| Presenton | Product default (`:8000`). Native Present opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native`) |

Nothing local-only is called complete. Missing evidence is not PASS.

## Matrix

| Surface | Capability | files | commit / PR | on develop? | browser | Electron | security | operational | status | blocker |
|---------|------------|-------|-------------|-------------|---------|----------|----------|-------------|--------|---------|
| Companion | HUD/dock orchestration, provenance, canonical handoffs | `MentrixCompanion.tsx`, `companion.py`, `companion_scope.py`, `permission_broker.py` | **#157** | **yes** | headed missions A–G **PASS** | Electron HUD/handoff/reconnect **PASS** | broker + unauthorized repo skip | Local Jira env set → Work Items identity; Camunda unset | **PASS** (orchestration) | Live Jira create-issue API not in Companion; semantic cross-repo refs not implemented |
| Developer chrome | Explorer \| Editor \| Agent + bottom tabs, persist, maximize | `DeveloperWorkspace.tsx`, `workspaceChrome.ts` | #154+#156 | **yes** | headed hygiene + search tab | Electron restore #156 | path jail on active root | layout persist | **PASS** (chrome) | Overall ZECT still PARTIAL |
| Developer multi-root | Merged A+B+C explorer, locked terminals, search, git jail, Electron restore | `WorkspaceRootsRail.tsx`, `workspace_search.py`, `workspace_multi_root.py` | #156 | **yes** | headed `workspace-multi-root.spec.ts` | headed restore spec **PASS** | bound_root + pathspec jail | ROOT_UNAVAILABLE + session persist | **PASS** | Semantic cross-repo refs not implemented; live GitHub multi-PR `BLOCKED_EXTERNAL` |
| Lattice / context | Canonical states + SHA STALE | `indexer.py`, `lattice.py`, `WorkspaceContextUsedPanel.tsx` | #154 | yes | header chip + Context tab | not re-run this SHA | repo-scoped status | STALE on commit move | **PARTIAL** | Per-root indexing UX incomplete; Graphify out of scope |
| Coding Agent | PLAN → worktree → edit/test/review/git | `lifecycle.py`, `MentrixCodingAgentPanel.tsx`, `mentrix_agent_tools.py` | **this PR** | **no** until merge | `coding-agent-production.spec.ts` | `coding-agent-electron.spec.ts` (skip ≠ core skip) | eval/secrets fail-closed; git always-confirm | in-memory missions; sibling BLOCKED | **this PR** | Live GitHub `BLOCKED_EXTERNAL`; restart persistence tranche E |
| WorkItem / multi-repo agent | ASK/PLAN/AGENT + isolated worktrees | `multi_repo_agent.py`, `DeveloperMultiRepoStatus.tsx` | #144/#148 | yes | status strip | n/a | authorized repo ids | aggregate READY | **PARTIAL** | Live GitHub PR / READY_AFTER_FIX `BLOCKED_EXTERNAL` |
| Ultra Review | Findings + closed loop | `ultrareview.py`, coding-agent `review_diff` | #138+this | yes | unit | n/a | MERGE_ELIGIBLE / mission block | fixture git | **PARTIAL** | Live GitHub optional; CodeRabbit skip ≠ PASS |
| Present | Dashboard→Create→Review→Export Quality/Fast | Present pages, inspector, renderer XOR | #153/#154 | yes | headed P0 (session) | Generate→Review→Export (session) | 409 critical block | Presenton default | **PARTIAL** | Tranche B not started; COM evidence not in git |
| Voice | Clone / stock / none, overlap, reconnect | `CloneVoicePanel.tsx`, `speak.ts`, `realtime.py` | prior | yes | selectors + mute | Electron Connect Voice control | ownership unit | Voicebox | **PARTIAL** | Tranche B not started |
| Projects / WorkItems / Processes | Fixture isolation, sample process | `fixture_isolation.py`, WorkItems UI | #150+#154 | yes | hygiene e2e | n/a | provenance hide | sample only | **PARTIAL** | Real Jira/Camunda `BLOCKED_EXTERNAL` |
| Security | Broker, SSRF, sandbox, untrusted context | `permission_broker.py`, `ssrf.py`, sandbox tests | prior+#157+this | yes | unit/CI | n/a | companion injection + git write confirm | no live campaign | **PARTIAL** | Full-product threat campaign is tranche D |
| Install / recovery | Alembic, sidecar, LRR restart unit | `alembic/`, packaging tests | #146 | yes | n/a | sidecar exists | n/a | NSIS unproven | **PARTIAL** | Clean-machine NSIS `BLOCKED_EXTERNAL`; coding-agent in-memory store |
| Performance / soak | LRR endurance script | `live_lrr_endurance.py` | prior | script only | n/a | n/a | n/a | no CI soak | **FAIL** (evidence) | No bounded soak at this SHA |
| Observability | Some correlation on findings | SecurityFinding, companion | prior | yes | n/a | n/a | avoid secret logs | not global | **PARTIAL** | No repo-wide `x-correlation-id` middleware |
| Accessibility | SplitPane ARIA, some labels | scattered | #154 | yes | not audited | not audited | n/a | n/a | **PARTIAL** | No WCAG sweep (tranche G) |

## Suggested PR sequence (human-merge each)

| PR | Topic | This session |
|----|--------|----------------|
| B | Developer multi-root / workspace UX | **#156 merged** |
| A | Companion production closure | **#157 merged** |
| C | Coding-agent missions A–G | **this PR — stop at READY_TO_MERGE_CODING_AGENT, no auto-merge** |
| D | Present + Voice re-proof | not started |
| E | WorkItems / Processes / Lattice per-root | not started |
| F | Security / ops / soak / a11y | not started |

## This PR (Coding Agent production)

Human-merge after CI. Remaining **outside** this tranche:

- Present Generate/Export / Voice clone proof (tranche B)
- WorkItems / Processes / Lattice per-root (tranche C)
- Live Jira / Camunda / GitHub PR (`BLOCKED_EXTERNAL` without credentials)
- Graphify / S8C / S8D

## Verdict so far

**ZECT_PRODUCTION_PARTIAL.** Canonical develop is healthy post-#157. This PR completes the Mentrix Coding Agent production-lifecycle gate for human merge; it does **not** make overall ZECT production-grade.
