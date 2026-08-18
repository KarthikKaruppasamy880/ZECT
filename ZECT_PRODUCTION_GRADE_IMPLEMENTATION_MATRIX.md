# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-18  
**Canonical develop:** `origin/develop` = `962bb6b58e1108b2a3d697419a82351723baa317` (PR **#163** human-merged).  
**This working branch:** `feat/performance-reliability-architecture`  
**Prompt:** `prompts/ZECT_PERFORMANCE_RELIABILITY_OBSERVABILITY_AND_ARCHITECTURE_CLOSURE.md`  
**No auto-merge.** S8C / S8D / Graphify / KV-cache / OCR-XLSX / broader Web / new-agent roadmap: **not started**.

Companion PASS, Coding Agent PASS (lifecycle), Present/Voice PARTIAL, Work intelligence PASS (lifecycle), Security campaign PASS, Recovery PARTIAL (NSIS external), Runtime/DB PASS (desktop + boot contract), Performance **PARTIAL**. Overall ZECT is **not** production-ready.

## Git truth

| Item | Value |
|------|--------|
| Merged | #156–**#163** (Runtime/DB on develop) |
| This PR | Observability, bounded soak, storage/architecture truth |
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
| Runtime / DB | sqlite desktop + Alembic postgres | `database.py`, `alembic/env.py` | **#163** | **yes** | healthz + System Health | sidecar sqlite default | no URL in healthz | live PG unset | **PASS** (desktop + boot contract) | Live Postgres / NSIS `BLOCKED_EXTERNAL` |
| Performance / soak | Thresholds + telemetry + bounded soak | `observability.py`, `perf_thresholds.py` | **this PR** | **no** until merge | correlation e2e | electron skip ≠ core | redact MCP/telemetry | Voice/PG unset | **PARTIAL** | Voicebox / live PG / terminals soak |
| Architecture | Canonical + RAG/DB truth | `ZECT_CANONICAL_ARCHITECTURE.md` | **this PR** | **no** until merge | n/a | n/a | no pgvector claim | dual-mode DB | **PASS** (docs=code) | Graphify PLANNED |
| Accessibility | SplitPane ARIA | SplitPane | #154 | yes | not audited | not audited | n/a | n/a | **PARTIAL** | Tranche G |

## Suggested PR sequence (human-merge each)

| PR | Topic | This session |
|----|--------|----------------|
| A–E + runtime | Coding Agent through #163 | **merged** |
| F | Soak, observability, architecture | **this PR — stop for human merge, no auto-merge** |
| G–I | a11y, full-release E2E, final audit | **not started** until this PR is human-merged |

## This PR (Performance / observability / architecture)

Human-merge after CI. Remaining **outside** this tranche:

- Live PostgreSQL / Voicebox / Presenton / GitHub / Jira / Camunda = **BLOCKED_EXTERNAL**
- Clean-machine Windows NSIS = **BLOCKED_EXTERNAL**
- a11y / full-release E2E (tranches G–H)
- Graphify / S8C / S8D

## Verdict so far

**ZECT_PRODUCTION_PARTIAL.** Canonical develop is `962bb6b` post-#163. This PR adds bounded soak, safe telemetry, and code-backed architecture; it does **not** make overall ZECT production-grade.
