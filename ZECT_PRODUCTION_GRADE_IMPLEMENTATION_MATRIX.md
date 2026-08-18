# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-18  
**Canonical develop:** `origin/develop` = `76f5a58b53f973fc748359db5a9858cb884a5b38` (PR **#158** human-merged).  
**This working branch:** `feat/present-voice-production`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md`  
**No auto-merge.** S8C / S8D / Graphify / KV-cache / OCR-XLSX / broader Web / new-agent roadmap / WorkItems-Lattice tranche: **not started**.

Companion PASS, Coding Agent PASS, and Present/Voice **partial** proof do **not** make overall ZECT production-ready.

## Git truth

| Item | Value |
|------|--------|
| Merged | #156 Developer multi-root; #157 Companion; **#158 Coding Agent** |
| This PR | Present + Voice production lifecycle proof and honest provider gates |
| Unrelated WIP | leftover acceptance markdown / `prompts/` / `.zect/skills/` — **not** claimed complete |
| Presenton | Product default (`:8000`). Native Present opt-in (`ZECT_PRESENTATION_PROVIDER=zect_native`). **Not flipped.** |

Nothing local-only is called complete. Missing evidence is not PASS.

## Matrix

| Surface | Capability | files | commit / PR | on develop? | browser | Electron | security | operational | status | blocker |
|---------|------------|-------|-------------|-------------|---------|----------|----------|-------------|--------|---------|
| Companion | HUD/dock orchestration, provenance, canonical handoffs | `MentrixCompanion.tsx`, `companion.py` | **#157** | **yes** | headed missions A–G **PASS** | Electron HUD/handoff **PASS** | broker | Local Jira env; Camunda unset | **PASS** (orchestration) | Live Jira create-issue not in Companion |
| Developer chrome | Explorer \| Editor \| Agent + bottom tabs | `DeveloperWorkspace.tsx` | #154+#156 | **yes** | headed | Electron restore #156 | path jail | layout persist | **PASS** (chrome) | Overall ZECT still PARTIAL |
| Developer multi-root | Merged explorer, terminals, search, git jail | `WorkspaceRootsRail.tsx` | #156 | **yes** | headed | headed restore **PASS** | bound_root | ROOT_UNAVAILABLE | **PASS** | Semantic cross-repo refs; live GitHub `BLOCKED_EXTERNAL` |
| Lattice / context | Canonical states + SHA STALE | `indexer.py`, `lattice.py` | #154 | yes | header chip | not this SHA | repo-scoped | STALE on commit | **PARTIAL** | Per-root UX; Graphify out of scope |
| Coding Agent | PLAN → worktree → edit/test/review/git | `lifecycle.py`, `MentrixCodingAgentPanel.tsx` | **#158** | **yes** | `coding-agent-production.spec.ts` | `coding-agent-electron.spec.ts` | git always-confirm | in-memory missions | **PASS** (lifecycle) | Live GitHub `BLOCKED_EXTERNAL`; restart persistence tranche E |
| WorkItem / multi-repo agent | ASK/PLAN/AGENT + isolated worktrees | `multi_repo_agent.py` | #144/#148 | yes | status strip | n/a | authorized repo ids | aggregate READY | **PARTIAL** | Tranche C not started |
| Ultra Review | Findings + closed loop | `ultrareview.py` | #138+#158 | yes | unit | n/a | MERGE_ELIGIBLE | fixture git | **PARTIAL** | CodeRabbit skip ≠ PASS |
| Present | Dashboard→Create→Review→Export Quality/Fast | Present pages, inspector, import fail-closed | **this PR** | **no** until merge | `present-voice-production.spec.ts` | `present-voice-electron.spec.ts` (skip ≠ core) | 409 critical block; invalid PPTX 400 | Presenton default | **PARTIAL** | Live Generate `BLOCKED_EXTERNAL` without Presenton; COM opt-in |
| Voice | Clone / stock / none, overlap, cancel | `CloneVoicePanel.tsx`, `speak.ts`, `voice_clone.py` | **this PR** | **no** until merge | selectors + engine status | Electron clone panel | cross-user 404 | Voicebox | **PARTIAL** | Voicebox/stock live speak `BLOCKED_EXTERNAL` |
| Projects / WorkItems / Processes | Fixture isolation, sample process | `fixture_isolation.py` | #150+#154 | yes | hygiene e2e | n/a | provenance hide | sample only | **PARTIAL** | Real Jira/Camunda `BLOCKED_EXTERNAL` |
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
| D | Present + Voice re-proof | **this PR — stop at READY_TO_MERGE_PRESENT_VOICE, no auto-merge** |
| E | WorkItems / Processes / Lattice per-root | not started |
| F | Security / ops / soak / a11y | not started |

## This PR (Present + Voice production)

Human-merge after CI. Remaining **outside** this tranche:

- Live Presenton Quality generate / live PowerPoint COM (`BLOCKED_EXTERNAL` without those runtimes)
- WorkItems / Processes / Lattice per-root (tranche C)
- Live Jira / Camunda / GitHub PR
- Graphify / S8C / S8D

## Verdict so far

**ZECT_PRODUCTION_PARTIAL.** Canonical develop is healthy post-#158. This PR completes Present/Voice production-lifecycle proof with honest external gates; it does **not** make overall ZECT production-grade.
