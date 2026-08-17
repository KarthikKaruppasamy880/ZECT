# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-17  
**Canonical develop:** `origin/develop` = `a0bada0c771c9e2cc62061d1bb01cc099e021e13` (PR **#154** human-merged).  
**Local develop:** `a0bada0` — **equals** `origin/develop`.  
**This working branch:** `feat/developer-multi-root-workspace` (not on develop until human merge).  
**Prompt:** `prompts/ZECT_PRODUCTION_GRADE_FINAL_CLOSURE.md`  
**No auto-merge.** S8C / S8D / Graphify / KV-cache / OCR-XLSX / broader Web / new-agent roadmap: **not started**.

## Git truth

| Item | Value |
|------|--------|
| Open PRs targeting develop | #82 Lattice fixture (stale); #33 Active Project selector (`devin/` branch — do not touch) |
| Stashes preserved | 4 unrelated WIP stashes |
| Untracked preserved | `prompts/`, `.zect/skills/`, gap-analysis markdown, fixtures — **not** claimed complete |
| Presenton | Product default (`:8000`). Native Present opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native`) |

Nothing local-only is called complete.

## Matrix

| Surface | Capability | files | commit / PR | on develop? | browser | Electron | security | operational | status | blocker |
|---------|------------|-------|-------------|-------------|---------|----------|----------|-------------|--------|---------|
| Companion | HUD/dock orchestration, brokered tools, voice, handoffs | `MentrixCompanion.tsx`, `companion.py`, `permission_broker.py` | #139+ | yes | PARTIAL (e2e companion specs) | PARTIAL (dock/desktop bridge) | Permission broker unit | Live M365/Slack/Jira | **PARTIAL** | No single Companion→ship golden path; connectors `BLOCKED_EXTERNAL` |
| Developer chrome | Explorer \| Editor \| Agent + bottom tabs, persist, maximize | `DeveloperWorkspace.tsx`, `workspaceChrome.ts` | #154 | yes | PARTIAL (hygiene) | not re-run | path jail on active root | layout persist | **PARTIAL** | Viewport sweep / Electron `/workspace` not re-proven at `a0bada0` |
| Developer multi-root | Simultaneous Root A+B+C explorer | `WorkspaceRootsRail.tsx`, `workspaceRoots.ts`, `repo_git_identity` | this PR | **no** | unit + opt-in headed spec | not yet | remove ≠ delete disk | ROOT_UNAVAILABLE | **IN_PR** | Does **not** complete merged Explorer tree, per-root terminals, workspace search/symbols, repo-scoped Git safety proof, multi-repo WorkItem/Coding Agent proof, or Electron workspace restore |
| Lattice / context | Canonical states + SHA STALE | `indexer.py`, `lattice.py`, `WorkspaceContextUsedPanel.tsx` | #154 | yes | header chip + Context tab | not re-run | repo-scoped status | STALE on commit move | **PARTIAL** | Per-root indexing UX incomplete; Graphify out of scope |
| Coding Agent | Interactive edit loop | `MentrixCodingAgentPanel.tsx`, `mentrix_agent_tools.py` | prior | yes | panel in workspace | not mission-proven | path jail; cmd approval | worktree isolation | **PARTIAL** | Native tools lack commit/push/PR; Missions A–G unlabeled |
| WorkItem / multi-repo agent | ASK/PLAN/AGENT + isolated worktrees | `multi_repo_agent.py`, `DeveloperMultiRepoStatus.tsx` | #144/#148 | yes | status strip | n/a | authorized repo ids | aggregate READY | **PARTIAL** | Live GitHub PR / READY_AFTER_FIX `BLOCKED_EXTERNAL` |
| Ultra Review | Findings + closed loop | `ultrareview.py`, closed-loop tests | #138 | yes | unit | n/a | MERGE_ELIGIBLE | fixture git | **PARTIAL** | Live GitHub optional; CodeRabbit skip ≠ PASS |
| Present | Dashboard→Create→Review→Export Quality/Fast | Present pages, inspector, renderer XOR | #153/#154 | yes | headed P0 (session) | Generate→Review→Export (session) | 409 critical block | Presenton default | **PARTIAL** | COM evidence not in git; Presenton Docker often down; not re-run at `a0bada0` |
| Voice | Clone / stock / none, overlap, reconnect | `CloneVoicePanel.tsx`, `speak.ts`, `realtime.py` | prior | yes | selectors | F5/Right Electron | ownership unit | Voicebox | **PARTIAL** | ≥2-slide live clone and stock speak unproven at this SHA |
| Projects / WorkItems / Processes | Fixture isolation, sample process | `fixture_isolation.py`, WorkItems UI | #150+#154 | yes | hygiene e2e | n/a | provenance hide | sample only | **PARTIAL** | Real Jira/Camunda `BLOCKED_EXTERNAL` |
| Security | Broker, SSRF, sandbox, untrusted context | `permission_broker.py`, `ssrf.py`, sandbox tests | prior | yes | unit/CI | n/a | many unit tests | no live campaign | **PARTIAL** | No fresh threat campaign at `a0bada0` |
| Install / recovery | Alembic, sidecar, LRR restart unit | `alembic/`, packaging tests | #146 | yes | n/a | sidecar exists | n/a | NSIS unproven | **PARTIAL** | Clean-machine NSIS `BLOCKED_EXTERNAL` |
| Performance / soak | LRR endurance script | `live_lrr_endurance.py` | prior | script only | n/a | n/a | n/a | no CI soak | **FAIL** (evidence) | No bounded soak at this SHA |
| Observability | Some correlation on findings | SecurityFinding, companion | prior | yes | n/a | n/a | avoid secret logs | not global | **PARTIAL** | No repo-wide `x-correlation-id` middleware |
| Accessibility | SplitPane ARIA, some labels | scattered | #154 | yes | not audited | not audited | n/a | n/a | **PARTIAL** | No WCAG sweep |

## Suggested PR sequence (human-merge each)

| PR | Topic | This session |
|----|--------|----------------|
| B | Developer multi-root / workspace UX | **this PR — stop at READY_TO_MERGE, no auto-merge** |
| A | Companion production closure | not started |
| C | Coding-agent missions A–G | not started |
| D | Present + Voice re-proof on `a0bada0` | not started |
| E | WorkItems / Processes / Lattice per-root | not started |
| F | Security / ops / soak / a11y | not started |

## This PR does not complete multi-root

Human-merge the rail slice first. Remaining multi-root requirements (do not start until merged):

- Merged multi-root Explorer tree
- Per-root terminals
- Workspace-wide search/symbols
- Repo-scoped Git safety proof
- Multi-repo WorkItem / Coding Agent proof
- Electron workspace restore

## Verdict so far

**ZECT_PRODUCTION_PARTIAL.** Canonical develop is healthy post-#154. Production-grade is **not** earned from unit tests or prior-session Present/PowerPoint evidence. First implementation slice is multi-root explorer rails on top of existing chrome.
