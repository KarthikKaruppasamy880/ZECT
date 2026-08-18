# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-18  
**Canonical develop:** `origin/develop` = `071028e290817a22ea1be0ab3944af3d3822e1de` (PR **#160** human-merged).  
**This working branch:** `feat/security-production`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md`  
**No auto-merge.** S8C / S8D / Graphify / KV-cache / OCR-XLSX / broader Web / new-agent roadmap: **not started**.

Companion PASS, Coding Agent PASS, Present/Voice PARTIAL, Work intelligence PASS (lifecycle), and this Security campaign do **not** make overall ZECT production-ready.

## Git truth

| Item | Value |
|------|--------|
| Merged | #156 Developer multi-root; #157 Companion; **#158 Coding Agent**; **#159 Present + Voice**; **#160 Work intelligence** |
| This PR | Security / governance threat campaign + path-jail prefix fix |
| Unrelated WIP | leftover acceptance markdown / `prompts/` / `.zect/skills/` — **not** claimed complete |
| Presenton | Product default (`:8000`). Native Present opt-in. **Not flipped.** |

Nothing local-only is called complete. Missing evidence is not PASS.

## Matrix

| Surface | Capability | files | commit / PR | on develop? | browser | Electron | security | operational | status | blocker |
|---------|------------|-------|-------------|-------------|---------|----------|----------|-------------|--------|---------|
| Companion | HUD/dock orchestration, provenance, canonical handoffs | `MentrixCompanion.tsx`, `companion.py` | **#157** | **yes** | headed missions A–G **PASS** | Electron HUD/handoff **PASS** | broker | Local Jira env; Camunda unset | **PASS** (orchestration) | Live Jira create-issue not in Companion |
| Developer chrome | Explorer \| Editor \| Agent + bottom tabs | `DeveloperWorkspace.tsx` | #154+#156 | **yes** | headed | Electron restore #156 | path jail | layout persist | **PASS** (chrome) | Overall ZECT still PARTIAL |
| Developer multi-root | Merged explorer, terminals, search, git jail | `WorkspaceRootsRail.tsx` | #156 | **yes** | headed | headed restore **PASS** | bound_root | ROOT_UNAVAILABLE | **PASS** | Semantic cross-repo refs; live GitHub `BLOCKED_EXTERNAL` |
| Lattice / context | Canonical states + SHA STALE per root | `indexer.py`, `lattice.py`, roots rail | **#160** | **yes** | header + per-root SHA | skip ≠ core | repo-scoped keys | STALE on commit | **PASS** (per-root; no Graphify) | Graphify out of scope |
| Coding Agent | PLAN → worktree → edit/test/review/git | `lifecycle.py`, `MentrixCodingAgentPanel.tsx` | **#158** | **yes** | `coding-agent-production.spec.ts` | `coding-agent-electron.spec.ts` | git always-confirm | in-memory missions | **PASS** (lifecycle) | Live GitHub `BLOCKED_EXTERNAL`; restart persistence tranche E |
| WorkItem / multi-repo agent | ASK/PLAN/AGENT + isolated worktrees + UI detail | `multi_repo_agent.py`, `WorkItemDetailPanel.tsx` | **#160** | **yes** | `work-intelligence-production.spec.ts` | `work-intelligence-electron.spec.ts` (skip ≠ core) | authorized repo ids; 403 without verifier | aggregate READY | **PASS** (lifecycle + UI) | Live GitHub `BLOCKED_EXTERNAL` |
| Ultra Review | Findings + closed loop | `ultrareview.py` | #138+#158+#159+#160 | yes | unit | n/a | MERGE_ELIGIBLE | fixture git | **PARTIAL** | CodeRabbit skip ≠ PASS |
| Present | Dashboard→Create→Review→Export Quality/Fast | Present pages, inspector, import fail-closed | **#159** | **yes** | `present-voice-production.spec.ts` | `present-voice-electron.spec.ts` (skip ≠ core) | 409 critical block; invalid PPTX 400 | Presenton default | **PARTIAL** | Live Generate `BLOCKED_EXTERNAL` without Presenton; COM opt-in |
| Voice | Clone / stock / none, overlap, cancel | `CloneVoicePanel.tsx`, `speak.ts`, `voice_clone.py` | **#159** | **yes** | selectors + engine status | Electron clone panel | cross-user 404 | Voicebox | **PARTIAL** | Voicebox/stock live speak `BLOCKED_EXTERNAL` |
| Projects / Processes | Fixture isolation, sample + ingest, connector chips | `fixture_isolation.py`, `MentrixFabric.tsx` | **#160** | **yes** | hygiene + work-intelligence e2e | Electron processes | provenance hide | sample + fixture ingest | **PARTIAL** | Real Jira/Camunda `BLOCKED_EXTERNAL` |
| Security | Threat campaign, path jail, broker, SSRF | `allowed_paths.py`, `permission_broker.py`, `test_security_production.py` | **this PR** | **no** until merge | `security-production.spec.ts` | `security-electron.spec.ts` (skip ≠ core) | prefix jail closed; git always-confirm | no live OAuth/GitHub pentest | **PASS** (campaign) | Live OAuth/GitHub/Voicebox `BLOCKED_EXTERNAL` |
| Install / recovery | Alembic, sidecar | `alembic/` | #146 | yes | n/a | sidecar exists | n/a | NSIS unproven | **PARTIAL** | Clean-machine NSIS; coding-agent in-memory (tranche E) |
| Performance / soak | LRR endurance script | `live_lrr_endurance.py` | prior | script only | n/a | n/a | n/a | no CI soak | **FAIL** (evidence) | No bounded soak (tranche F) |
| Observability | Some correlation | SecurityFinding | prior | yes | n/a | n/a | avoid secret logs | not global | **PARTIAL** | No repo-wide `x-correlation-id` |
| Accessibility | SplitPane ARIA | scattered | #154 | yes | not audited | not audited | n/a | n/a | **PARTIAL** | No WCAG sweep (tranche G) |

## Suggested PR sequence (human-merge each)

| PR | Topic | This session |
|----|--------|----------------|
| A | Coding-agent missions A–G | **#158 merged** |
| B | Present + Voice re-proof | **#159 merged** |
| C | WorkItems / Processes / Lattice per-root | **#160 merged** |
| D | Security / governance threat campaign | **this PR — stop at READY_TO_MERGE_SECURITY, no auto-merge** |
| E–I | Recovery, soak, a11y, full-release E2E, final audit | not started |

## This PR (Security)

Human-merge after CI. Remaining **outside** this tranche:

- Live Entra OAuth / live GitHub PR (`BLOCKED_EXTERNAL` when unset)
- Live Voicebox reconnect campaign (`BLOCKED_EXTERNAL` when engine offline)
- Live Jira / Camunda
- Graphify / S8C / S8D
- Recovery, soak, a11y, full-release E2E (tranches E–H)

## Verdict so far

**ZECT_PRODUCTION_PARTIAL.** Canonical develop is healthy post-#160. This PR closes the path-jail prefix bypass and records an honest threat campaign; it does **not** make overall ZECT production-grade.
