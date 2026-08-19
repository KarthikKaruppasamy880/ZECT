# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-19  
**Canonical develop:** `origin/develop` = `55255f0b05240815a1547c0ea33d4317706acc99` (PR **#166** human-merged).  
**This working branch:** `feat/full-release-e2e`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md`  
**No auto-merge.** S8C / S8D / Graphify / KV-cache / OCR-XLSX / broader Web / new-agent roadmap: **not started**. Tranche I **not started**.

Companion PASS. Coding Agent PASS. Present/Voice PARTIAL (live Generate/Voicebox external). Work intelligence PASS. Security campaign PASS. Recovery PARTIAL (NSIS). Runtime/DB PASS. Performance PARTIAL (Voice/PG external). Accessibility PASS (#166). Full-release E2E **this PR**. Overall ZECT is **not** production-ready.

## Git truth

| Item | Value |
|------|--------|
| Merged | #156–**#166** (UX accessibility on develop) |
| This PR | Tranche H full-release E2E |
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
| Accessibility / UX | Skip, keyboard, 1280–1920, named controls | Layout, Sidebar, SplitPane, pages | **#166** | **yes** | headed **PASS** CI e2e | local Electron **PASS** | no new attack surface | n/a | **PASS** | Live connectors; CodeRabbit **SKIPPED** |
| Full-release E2E | Coherent browser + Electron journey | `full-release-e2e-*.spec.ts` | **this PR #167** | **no** until merge | headed journey + frozen core **PASS** CI | local Electron journey **PASS** | no new attack surface | n/a | **PASS** pending human merge | Live Generate/Voice/COM; CodeRabbit **SKIPPED** |
| Architecture | Canonical + RAG/DB truth | architecture md | **#165** SHA bump | **yes** | n/a | n/a | no pgvector claim | dual-mode DB | **PASS** (docs=code) | Graphify PLANNED |

## Suggested PR sequence (human-merge each)

| PR | Topic | This session |
|----|--------|----------------|
| A–G leftover | through #166 UX sweep | **merged** |
| H | Full-release E2E | **this PR — stop for human merge** |
| I | final audit | **not started** |

## This PR (Tranche H)

Human-merge after CI. Remaining **outside** this tranche:

- Live PostgreSQL / Voicebox / Presenton Generate / GitHub / Jira / Camunda / PowerPoint COM = **BLOCKED_EXTERNAL**
- Clean-machine Windows NSIS = **BLOCKED_EXTERNAL**
- Final review / release audit (tranche I)
- Graphify / S8C / S8D

## Verdict so far

**ZECT_PRODUCTION_PARTIAL.** Canonical develop is `55255f0` post-#166. This PR closes the full-release E2E journey; it does **not** make overall ZECT production-grade.
