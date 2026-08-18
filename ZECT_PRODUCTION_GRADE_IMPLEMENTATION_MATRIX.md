# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-18  
**Canonical develop:** `origin/develop` = `9394508ba6f6f024a240c12dd294d626036afc7d` (PR **#161** human-merged).  
**This working branch:** `feat/runtime-recovery`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md`  
**No auto-merge.** S8C / S8D / Graphify / KV-cache / OCR-XLSX / broader Web / new-agent roadmap: **not started**.

Companion PASS, Coding Agent PASS (lifecycle), Present/Voice PARTIAL, Work intelligence PASS (lifecycle), Security campaign PASS, and this recovery campaign do **not** make overall ZECT production-ready.

## Git truth

| Item | Value |
|------|--------|
| Merged | #156–**#161** (Security on develop) |
| This PR | Install / upgrade / migration / recovery proof + durable coding-agent missions |
| Unrelated WIP | leftover acceptance markdown / `prompts/` / `.zect/skills/` — **not** claimed complete |
| Presenton | Product default. Native Present opt-in. **Not flipped.** |

Nothing local-only is called complete. Missing evidence is not PASS.

## Matrix

| Surface | Capability | files | commit / PR | on develop? | browser | Electron | security | operational | status | blocker |
|---------|------------|-------|-------------|-------------|---------|----------|----------|-------------|--------|---------|
| Companion | HUD/dock orchestration | `MentrixCompanion.tsx` | **#157** | **yes** | headed **PASS** | Electron **PASS** | broker | Camunda unset | **PASS** (orchestration) | Live Jira create |
| Developer multi-root | Explorer, terminals, git jail | `WorkspaceRootsRail.tsx` | #156 | **yes** | headed | restore **PASS** | bound_root | ROOT_UNAVAILABLE | **PASS** | Live GitHub `BLOCKED_EXTERNAL` |
| Lattice | Per-root SHA / STALE | `indexer.py` | **#160** | **yes** | headed | skip ≠ core | repo-scoped | STALE | **PASS** | Graphify out of scope |
| Coding Agent | PLAN → worktree → review → git | `lifecycle.py` | **#158** + **this PR** | **no** until merge | coding-agent e2e | electron skip ≠ core | git confirm | **durable JSON** | **PASS** (lifecycle + restart) | Live GitHub `BLOCKED_EXTERNAL` |
| WorkItem | ASK/PLAN/AGENT + UI | `WorkItemDetailPanel.tsx` | **#160** | **yes** | headed | skip ≠ core | verifier 403 | aggregate READY | **PASS** | Live GitHub `BLOCKED_EXTERNAL` |
| Present / Voice | Dashboard→Export; clone | Present pages | **#159** | **yes** | headed | skip ≠ core | 409 overlap | Presenton default | **PARTIAL** | Live Generate / Voicebox `BLOCKED_EXTERNAL` |
| Security | Threat campaign + path jail | `allowed_paths.py` | **#161** | **yes** | headed | Electron **PASS** | prefix jail | OAuth unset | **PASS** (campaign) | Live OAuth/GitHub/Voicebox |
| Install / recovery | Alembic chain, sidecar, mission persist | `lifecycle.py`, `service-lifecycle.js` | **this PR** | **no** until merge | `runtime-recovery-production.spec.ts` | electron skip ≠ core | mission id jail | NSIS unproven | **PARTIAL** | Clean-machine NSIS |
| Performance / soak | LRR endurance script | `live_lrr_endurance.py` | prior | yes | n/a | n/a | n/a | no CI soak | **FAIL** (evidence) | Tranche F |
| Accessibility | SplitPane ARIA | #154 | yes | not audited | not audited | n/a | n/a | **PARTIAL** | Tranche G |

## Suggested PR sequence (human-merge each)

| PR | Topic | This session |
|----|--------|----------------|
| A–D | Coding Agent, Present/Voice, Work intelligence, Security | **#158–#161 merged** |
| E | Install / upgrade / recovery | **this PR — stop at READY_TO_MERGE_RECOVERY, no auto-merge** |
| F–I | Soak, a11y, full-release E2E, final audit | not started |

## This PR (Recovery)

Human-merge after CI. Remaining **outside** this tranche:

- Clean-machine Windows NSIS (`BLOCKED_EXTERNAL`)
- Live Postgres Alembic cutover (packaged sqlite `create_all`)
- Soak / a11y / full-release E2E (tranches F–H)
- Graphify / S8C / S8D

## Verdict so far

**ZECT_PRODUCTION_PARTIAL.** Canonical develop is healthy post-#161. This PR makes coding-agent missions survive backend restart and records honest recovery gates; it does **not** make overall ZECT production-grade.
