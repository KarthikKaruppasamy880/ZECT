# ZECT Mentrix Companion Production Acceptance

**Date:** 2026-08-17  
**Canonical develop:** `9f88885778bb0315ccc694156903bcd19d6745a0` (PR **#156** human-merged)  
**This branch:** `feat/mentrix-companion-production`  
**Prompt:** `prompts/ZECT_MENTRIX_COMPANION_PRODUCTION_CLOSURE.md`  
**No auto-merge.** Coding Agent A–G / S8C / S8D / Graphify / KV cache / OCR-XLSX / broader Web / new agents: **not started**.

Companion PASS does **not** make overall ZECT production-ready.

## Responsibility

Companion is the orchestration surface only.

`User → Companion → active Project/workspace/repos → authorized PI/Lattice/Knowledge → WorkItem → ASK/PLAN → Developer/Coding Agent → progress/evidence → Present → Voice → Process/ticket → status/artifacts`

Companion does **not** edit source files, Present decks, Lattice graphs, or WorkItem engines. Handoff envelope: `project_id + workspace_id + work_item_id + repo_ids + commit SHAs + plan/evidence refs`.

Semantic cross-repo references: **not implemented** (honest, inherited from #156).

## Gates

| Gate | Result | Evidence |
|------|--------|----------|
| Baseline #156 merged | **PASS** | develop `9f88885` |
| UX expanded / compact / floating | **PASS** | HUD + dock `z-40` `max-h-[70vh]`; cancel/retry; scope strip |
| Multi-root awareness | **PASS** | `companion_scope.py` + HUD/dock strip; unauthorized repo ids skipped |
| Context / provenance | **PASS** | chips `used` / `not_used` / `stale` / `missing`; unused sources not claimed |
| Mission A Intelligence | **PASS** (headed + unit) | architecture intent → `companion_intelligence`; same-named files tagged by root |
| Mission B WorkItem → PLAN → coding handoff | **PASS** (orchestration) | create/open WorkItem then `/workspace?envelope`; Companion never claims file edits |
| Mission C Multi-repo | **PASS** (unit + headed envelope) | sibling PASS+FAIL ⇒ aggregate **BLOCKED**; both roots in `repo_ids` |
| Mission D Present | **PASS** (handoff) | `/present` / `/present/create` — ZECT Present, not Presenton UI; Companion does not duplicate editor |
| Mission E Voice | **PASS** (controls) | TTS mute, Connect Voice, clone panel, Present handoff from Voice tab; conversational ≠ Present narration |
| Mission F Process/ticket | **PASS** (orchestration) + honest connector gate | Local Jira **configured**: WorkItem `source=jira` + `/work-items?project_id=`; unset: `BLOCKED_EXTERNAL` and **no auto-navigate** (unit) |
| Mission G Failure/recovery | **PASS** | cancel/retry; session preserved; prompt injection still confirm-gated; no retry storm |
| Long-running progress | **PASS** | `progress` SSE + HUD stage/repos/blocker |
| Artifacts | **PASS** | open canonical surfaces; secret redaction helper |
| Permission / desktop | **PASS** | broker fail-closed (`desktop_delete` never); unauthorized repo skipped |
| Session / reconnect | **PASS** (Electron) | HUD + scope after Electron restart |
| Integration surfaces | **PASS** | dock on Projects / WorkItems / Workspace / Present; does not cover sidebar |
| Viewports 1280/1366/1440/1920 | **PASS** | headed `companion-production-missions.spec.ts` |
| Electron missions | **PASS** | `companion-electron-missions.spec.ts` HUD, multi-root scope, intelligence, Workspace/Present handoff, reconnect |
| Security | **PASS** (unit) | tenant/project/repo skip, injection still Allow-gated, `.env` desktop block (prior) |
| Reliability | **PASS** | AbortController cancel, duplicate-send blocked while loading, 45s timeout |
| Mentrix Ultra Review | **PASS** | `test-results/companion-production/ultra-review-companion.json` — score 85, **0** Critical; 1 Medium (malformed `repository_ids` skipped) |
| CodeRabbit | **SKIPPED** | unavailable/manual — never counted as PASS |

## Tests

- Backend: `tests/test_companion_production.py` + existing `tests/test_mentrix_companion.py` — **52 passed**
- Headed: `frontend/e2e/companion-production-missions.spec.ts` (in `test:e2e:core`) — **PASS** (A–G, viewports, dock)
- Existing HUD smoke: `frontend/e2e/mentrix-companion.spec.ts` — **PASS**
- Electron: `frontend/e2e/companion-electron-missions.spec.ts` — **PASS** (binary present)
- Screenshots: `frontend/test-results/companion-production/` and `test-results/companion-electron/`

## Limitations (honest)

- Live Jira **create-issue API** is not implemented in Companion; when Jira env is set, Companion creates a WorkItem with `source=jira` and hands off to Work Items. Camunda unset here remains **BLOCKED_EXTERNAL** for process engine.
- Live Jira / Camunda / M365 / Slack send without credentials: **BLOCKED_EXTERNAL** — never faked PASS
- Semantic cross-repo references: **not implemented** (inherited from #156)
- Voicebox clone synthesis: degraded stock/browser fallback when Voicebox URL unset
- Presenton Docker: Present **handoff** proven; live Generate/Export remains Present’s own gate
- Companion does not run Coding Agent Missions A–G (next tranche)
- CodeRabbit unavailable/manual = **SKIPPED**, never PASS

## Verdict

**READY_TO_MERGE_COMPANION** after CI green and **human merge** of this PR. Do not start Coding Agent A–G in this run.
