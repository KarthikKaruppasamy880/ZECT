# ZECT Production-Grade Implementation Matrix

**Date:** 2026-08-19  
**Canonical develop:** `origin/develop` = `0dd7becb2c98b7e6c368bee10392925d1f3d57f2` (PRs **#170–#172** human-merged).  
**No auto-merge.** Graphify is Lattice ingest + `GraphifySnapshot`. `zect.ps1` is the local stack controller. Desktop file picker + Present evidence handoff are on develop. S8C Presenton-default-flip / KV-cache / extra agents: **not started**.

## Profile summary

| Profile | Verdict |
|---------|---------|
| ZECT_CORE | **ZECT_CORE_READY** |
| ZECT_DESKTOP_WINDOWS | **ZECT_DESKTOP_WINDOWS_PARTIAL** |
| GitHub / Jira / Camunda / Presenton / Voicebox | **BLOCKED_EXTERNAL** each |
| Monolith ZECT_PRODUCTION_READY | **not awarded** |

Optional connectors do not block Core. PostgreSQL does not block Core (sqlite default; postgres mandatory only for `server_postgres`).

## Git truth

| Item | Value |
|------|--------|
| Merged | #156–**#172** |
| This PR | Release-profile reconciliation + Windows Electron CI job |
| Presenton | Product default. Live Generate optional certification. **Not flipped.** |

## Matrix

| Surface | Capability | files | commit / PR | on develop? | browser | Electron | security | operational | status | blocker |
|---------|------------|-------|-------------|-------------|---------|----------|----------|-------------|--------|---------|
| Companion | HUD/dock | `MentrixCompanion.tsx` | **#157** + **#165** | **yes** | Core **PASS** | Desktop | broker | Camunda unset | **PASS** Core | Live Jira create **BLOCKED_EXTERNAL** |
| Developer multi-root | Explorer, terminals | `WorkspaceRootsRail.tsx` | #156 | **yes** | Core **PASS** | restore | bound_root | sqlite | **PASS** Core | Live GitHub **BLOCKED_EXTERNAL** |
| Lattice / Graphify | Per-root SHA + GraphifySnapshot | `indexer.py`, `graphify_snapshot.py` | **#160** + **#170** | **yes** | Core **PASS** | n/a | repo-scoped | READY@SHA | **PASS** Core | No second RAG; live GitHub cert **BLOCKED_EXTERNAL** |
| Coding Agent | PLAN → review | `lifecycle.py` | **#158** + **#165** | **yes** | Core **PASS** | Windows CI | git confirm | durable JSON | **PASS** Core | GitHub cert **BLOCKED_EXTERNAL** |
| WorkItem | ASK/PLAN/AGENT | `WorkItemDetailPanel.tsx` | **#160** | **yes** | Core **PASS** | skip ≠ ubuntu core | verifier | READY | **PASS** Core | GitHub/Jira/Camunda certs |
| Present / Voice | Dashboard→Export | Present pages | **#159** | **yes** | Core blank/export **PASS** | Windows CI | 409 | Presenton default | **PASS** Core; certs external | Presenton/Voicebox **BLOCKED_EXTERNAL** |
| Security | Threat campaign | `allowed_paths.py` | **#161** | **yes** | Core **PASS** | Desktop | prefix jail | OAuth unset | **PASS** Core | Live OAuth external |
| Install / NSIS | One-click | `electron/package.json` | **#162** | **yes** | n/a | n/a | n/a | unproven | **BLOCKED_EXTERNAL** | Desktop PARTIAL |
| Runtime / DB | Dual mode | `database.py` | **#163** | **yes** | healthz sqlite | sidecar sqlite | no URL in healthz | postgres fail-closed | **PASS** Core | Live PG does not block Core |
| Performance / soak | Thresholds | soak tests | **#164** + **#165** | **yes** | Core **PASS** | skip ≠ ubuntu | redact | Voice/PG unset | **PASS** Core internals | Voice/PG certs |
| Accessibility | Keyboard/a11y | Layout, Sidebar | **#166** | **yes** | Core **PASS** | local PASS | n/a | n/a | **PASS** Core | CodeRabbit **SKIPPED** |
| Full-release E2E | Coherent journey | `full-release-e2e-*.spec.ts` | **#167** + this PR | **yes** / Electron CI this PR | Ubuntu core **PASS** | `e2e-electron` Windows | n/a | n/a | Core **PASS**; Desktop CI this job | NSIS |
| Architecture | RAG/DB + Graphify=Lattice | architecture md | SHA `0dd7bec` | **yes** | n/a | n/a | no pgvector | dual-mode + `zect.ps1` | **PASS** | S8C/KV-cache PLANNED |

## This PR

Human-merge after CI (including `e2e-electron`). Do not start roadmap prompts until merge.
