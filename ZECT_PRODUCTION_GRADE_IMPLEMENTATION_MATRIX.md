# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-18  
**Canonical develop:** `origin/develop` = `69816ea0435024a3cf1a441eea71db3fc157d1e2` (PR **#165** human-merged).  
**This working branch:** `feat/ux-accessibility-release-sweep`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md`  
**No auto-merge.** S8C / S8D / Graphify / KV-cache / OCR-XLSX / broader Web / new-agent roadmap: **not started**. Tranche H **not started**.

Companion PASS (orchestration + soak on develop). Coding Agent PASS. Present/Voice PARTIAL (live Generate/Voicebox external). Work intelligence PASS. Security campaign PASS. Recovery PARTIAL (NSIS). Runtime/DB PASS. Performance PARTIAL (Voice/PG external). Accessibility **this PR**. Overall ZECT is **not** production-ready.

## Git truth

| Item | Value |
|------|--------|
| Merged | #156–**#165** (concurrent soak/isolation on develop) |
| This PR | Tranche G accessibility + product UX sweep |
| Unrelated WIP | leftover gap markdown / `prompts/` / `.zect/skills/` — **not** claimed complete |
| Presenton | Product default. Native Present opt-in. **Not flipped.** |

Nothing local-only is called complete. Missing evidence is not PASS.

## Matrix

| Surface | Capability | files | commit / PR | on develop? | browser | Electron | security | operational | status | blocker |
|---------|------------|-------|-------------|-------------|---------|----------|----------|-------------|--------|---------|
| Companion | HUD/dock orchestration | `MentrixCompanion.tsx` | **#157** + **#165** | **yes** | headed **PASS** | Electron **PASS** | broker | Camunda unset | **PASS** (orchestration) | Live Jira create |
| Developer multi-root | Explorer, terminals, git jail | `WorkspaceRootsRail.tsx` | #156 | **yes** | headed | restore **PASS** | bound_root | ROOT_UNAVAILABLE | **PASS** | Live GitHub `BLOCKED_EXTERNAL` |
| Lattice | Per-root SHA / STALE | `indexer.py` | **#160** | **yes** | headed | skip ≠ core | repo-scoped | STALE | **PASS** | Graphify out of scope |
| Coding Agent | PLAN → worktree → review → git | `lifecycle.py` | **#158** + **#165** | **yes** | coding-agent e2e | electron skip ≠ core | git confirm | **durable JSON** | **PASS** | Live GitHub `BLOCKED_EXTERNAL` |
| WorkItem | ASK/PLAN/AGENT + UI | `WorkItemDetailPanel.tsx` | **#160** | **yes** | headed | skip ≠ core | verifier 403 | aggregate READY | **PASS** | Live GitHub `BLOCKED_EXTERNAL` |
| Present / Voice | Dashboard→Export; clone | Present pages | **#159** | **yes** | headed | skip ≠ core | 409 overlap | Presenton default | **PARTIAL** | Live Generate / Voicebox `BLOCKED_EXTERNAL` |
| Security | Threat campaign + path jail | `allowed_paths.py` | **#161** | **yes** | headed | Electron **PASS** | prefix jail | OAuth unset | **PASS** (campaign) | Live OAuth/GitHub/Voicebox |
| Install / recovery | Sidecar, mission persist, occupied port | `lifecycle.py`, `service-lifecycle.js` | **#162** | **yes** | runtime-recovery e2e | electron skip ≠ core | mission id jail | NSIS unproven | **PARTIAL** | Clean-machine NSIS |
| Runtime / DB | sqlite desktop + Alembic postgres | `database.py` | **#163** | **yes** | healthz | sidecar sqlite | no URL in healthz | live PG unset | **PASS** | Live Postgres / NSIS `BLOCKED_EXTERNAL` |
| Performance / soak | Thresholds + telemetry + isolation | `observability.py`, soak tests | **#164** + **#165** | **yes** | concurrent e2e | electron skip ≠ core | redact MCP/telemetry | Voice/PG unset | **PARTIAL** | Voicebox / live PG |
| Accessibility / UX | Skip, keyboard, 1280–1920, named controls | Layout, Sidebar, SplitPane, pages | **this PR #166** | **no** until merge | headed **PASS** CI e2e | local Electron **PASS** | no new attack surface | n/a | **PASS** pending human merge | Live connectors; CodeRabbit **SKIPPED** |
| Architecture | Canonical + RAG/DB truth | architecture md | **#165** SHA bump | **yes** | n/a | n/a | no pgvector claim | dual-mode DB | **PASS** (docs=code) | Graphify PLANNED |

## Suggested PR sequence (human-merge each)

| PR | Topic | This session |
|----|--------|----------------|
| A–F leftover | through #165 concurrent soak | **merged** |
| G | Accessibility + UX sweep | **this PR — stop for human merge** |
| H–I | full-release E2E, final audit | **not started** |

## This PR (Tranche G)

Human-merge after CI. Remaining **outside** this tranche:

- Live PostgreSQL / Voicebox / Presenton / GitHub / Jira / Camunda = **BLOCKED_EXTERNAL**
- Clean-machine Windows NSIS = **BLOCKED_EXTERNAL**
- Full-release E2E (tranche H)
- Graphify / S8C / S8D

## Verdict so far

**ZECT_PRODUCTION_PARTIAL.** Canonical develop is `69816ea` post-#165. This PR closes the accessibility/UX release sweep; it does **not** make overall ZECT production-grade.
