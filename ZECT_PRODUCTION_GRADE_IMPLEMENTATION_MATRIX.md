# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-18  
**Canonical develop:** `origin/develop` = `0e730ac3b9397d5b9c638669017c59a19d82e821` (PR **#162** human-merged).  
**This working branch:** `feat/runtime-db-lifecycle`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md`  
**No auto-merge.** S8C / S8D / Graphify / KV-cache / OCR-XLSX / broader Web / new-agent roadmap: **not started**.  
**Do not start tranche F (soak) until this runtime/DB PR is human-merged.**

Companion PASS, Coding Agent PASS (lifecycle), Present/Voice PARTIAL, Work intelligence PASS (lifecycle), Security campaign PASS, Recovery PARTIAL (NSIS external), and this runtime/DB campaign do **not** make overall ZECT production-ready.

## Git truth

| Item | Value |
|------|--------|
| Merged | #156–**#162** (Recovery on develop) |
| This PR | Explicit `desktop_sqlite` vs `server_postgres` Alembic lifecycle |
| Unrelated WIP | leftover acceptance markdown / `prompts/` / `.zect/skills/` — **not** claimed complete |
| Presenton | Product default. Native Present opt-in. **Not flipped.** |

Nothing local-only is called complete. Missing evidence is not PASS.

## Matrix

| Surface | Capability | files | commit / PR | on develop? | browser | Electron | security | operational | status | blocker |
|---------|------------|-------|-------------|-------------|---------|----------|----------|-------------|--------|---------|
| Companion | HUD/dock orchestration | `MentrixCompanion.tsx` | **#157** | **yes** | headed **PASS** | Electron **PASS** | broker | Camunda unset | **PASS** (orchestration) | Live Jira create |
| Developer multi-root | Explorer, terminals, git jail | `WorkspaceRootsRail.tsx` | #156 | **yes** | headed | restore **PASS** | bound_root | ROOT_UNAVAILABLE | **PASS** | Live GitHub `BLOCKED_EXTERNAL` |
| Lattice | Per-root SHA / STALE | `indexer.py` | **#160** | **yes** | headed | skip ≠ core | repo-scoped | STALE | **PASS** | Graphify out of scope |
| Coding Agent | PLAN → worktree → review → git | `lifecycle.py` | **#158** + **#162** | **yes** | coding-agent e2e | electron skip ≠ core | git confirm | **durable JSON** | **PASS** (lifecycle + restart) | Live GitHub `BLOCKED_EXTERNAL` |
| WorkItem | ASK/PLAN/AGENT + UI | `WorkItemDetailPanel.tsx` | **#160** | **yes** | headed | skip ≠ core | verifier 403 | aggregate READY | **PASS** | Live GitHub `BLOCKED_EXTERNAL` |
| Present / Voice | Dashboard→Export; clone | Present pages | **#159** | **yes** | headed | skip ≠ core | 409 overlap | Presenton default | **PARTIAL** | Live Generate / Voicebox `BLOCKED_EXTERNAL` |
| Security | Threat campaign + path jail | `allowed_paths.py` | **#161** | **yes** | headed | Electron **PASS** | prefix jail | OAuth unset | **PASS** (campaign) | Live OAuth/GitHub/Voicebox |
| Install / recovery | Sidecar, mission persist, occupied port | `lifecycle.py`, `service-lifecycle.js` | **#162** | **yes** | `runtime-recovery-production.spec.ts` | electron skip ≠ core | mission id jail | NSIS unproven | **PARTIAL** | Clean-machine NSIS |
| Runtime / DB | sqlite desktop + Alembic postgres | `database.py`, `alembic/env.py` | **this PR** | **no** until merge | healthz + System Health | sidecar sqlite default | no URL in healthz | live PG unset | **PASS** (desktop + boot contract) | Live Postgres / NSIS `BLOCKED_EXTERNAL` |
| Performance / soak | LRR endurance script | `live_lrr_endurance.py` | prior | yes | n/a | n/a | n/a | no CI soak | **FAIL** (evidence) | Tranche F — **not started** |
| Accessibility | SplitPane ARIA | SplitPane | #154 | yes | not audited | not audited | n/a | n/a | **PARTIAL** | Tranche G |

## Suggested PR sequence (human-merge each)

| PR | Topic | This session |
|----|--------|----------------|
| A–E | Coding Agent through Recovery | **#158–#162 merged** |
| Runtime / DB | Explicit sqlite vs Postgres Alembic | **this PR — stop at READY_TO_MERGE_RUNTIME_RECOVERY, no auto-merge** |
| F–I | Soak, a11y, full-release E2E, final audit | **not started** until this PR is human-merged |

## This PR (Runtime / DB lifecycle)

Human-merge after CI. Remaining **outside** this tranche:

- Live PostgreSQL (`ZECT_TEST_POSTGRES_URL` unset) = **BLOCKED_EXTERNAL**
- Clean-machine Windows NSIS = **BLOCKED_EXTERNAL**
- Soak / a11y / full-release E2E (tranches F–H)
- Graphify / S8C / S8D

## Verdict so far

**ZECT_PRODUCTION_PARTIAL.** Canonical develop is `0e730ac` post-#162. This PR makes desktop SQLite and server Postgres boot contracts explicit and proven where the environment allows; it does **not** make overall ZECT production-grade.
