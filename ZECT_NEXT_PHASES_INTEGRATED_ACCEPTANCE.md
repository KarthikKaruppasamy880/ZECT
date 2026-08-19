# ZECT Next-Phases Integrated Acceptance

**Date:** 2026-08-19  
**Canonical develop:** `0dd7becb2c98b7e6c368bee10392925d1f3d57f2` (PRs **#170**, **#171**, **#172** human-merged)  
**This PR branch:** `feat/next-phases-integrated-acceptance`  
**Stop:** human merge only. **No auto-merge.**

Prompt: `prompts/ZECT_GRAPHIFY_LATTICE_COMPANION_DESKTOP_PRESENT_MASTER_PHASES.md` integrated proof.

## Verdict

**ZECT_NEXT_PHASES_READY** for the **internal** governed path on this machine. Optional Presenton / Voicebox / PowerPoint COM / NSIS / live GitHub / Jira / Camunda remain **BLOCKED_EXTERNAL** or **OPTIONAL_UNAVAILABLE** and were **not** faked. Skip ≠ PASS. Monolith `ZECT_PRODUCTION_READY` is **not** awarded.

Graphify is the Lattice ingest + `GraphifySnapshot` adapter. There is no second RAG, index, or agent framework.

## Canonical SHA

`0dd7becb2c98b7e6c368bee10392925d1f3d57f2`

## Integrated internal path (live `:8020` / `:5173` via `./zect.ps1`)

| Step | Result |
|------|--------|
| Multi-root Project + two local git repos | **PASS** (`/api/projects`, `/api/repos/register-local`) |
| Graphify ingest | **PASS** (`POST /api/lattice/ingest` force) |
| Lattice READY@SHA | **PASS** (`GET /api/lattice/snapshot` kind=`GraphifySnapshot`, adapter=`lattice`, ux=`Lattice`, SHA match). Survived backend restart (JSON cache reload). |
| Lattice query | **PASS** (`POST /api/lattice/query` hits) |
| Companion turn | **PASS** HTTP 200. Spoken UX did not leak Graphify internals. This run selected `navigate` rather than `lattice_query` — dedicated Lattice query still PASS. |
| WorkItem | **PASS** |
| Graph-informed PLAN | **PASS** (`/api/mentrix/developer/plan`, 2 affected repos, context pack) |
| Coding Agent mission | **PASS** create → approve-plan → sibling tests **READY** (alpha-svc + beta-svc) → Ultra Review passed → `awaiting_git_approval`. Live GitHub PR **BLOCKED_EXTERNAL** (git push not claimed). |
| Companion → Present handoff URL | **PASS** `/present/create?project_id&work_item_id&prompt` |
| Present Generate | **BLOCKED_EXTERNAL** HTTP 502 `presenton_unreachable` (`PRESENTON_BASE_URL` names present; process not healthy) |
| Review/Edit UI | **PASS** headed `/present/create` workspace (Generate attempt allowed to fail) |
| Rehearse / Voice | **OPTIONAL_UNAVAILABLE** / **BLOCKED_EXTERNAL** (Voicebox `:17493` down; Connect Voice disabled when realtime preflight is not ready) |
| Export PPTX via Presenton | **BLOCKED_EXTERNAL** |
| Desktop PowerPoint COM | **OPTIONAL_UNAVAILABLE** (`zect doctor`) |
| NSIS | **BLOCKED_EXTERNAL** |

## `./zect.ps1` (canonical local stack)

| Command | Result |
|---------|--------|
| `doctor` | Python ok; PowerPoint / Presenton / Voicebox **OPTIONAL_UNAVAILABLE**; Camunda missing; optional env **names** present (not live PASS) |
| `up --profile core` | backend READY :8020, frontend READY :5173 (Windows `npm.CMD` resolution) |
| `status` / `health` | both READY |
| `restart backend` | new backend PID; frontend PID unchanged |
| `up --profile desktop` | Electron READY (owned PID). Restart electron left backend/frontend PIDs unchanged. |
| `down` | owned PIDs only; no `stop-local.ps1` kill-by-port |

Local API **8020** / UI **5173**. CI and packaged Electron API remain **8000**.

## Optional integrations (honest)

| Integration | Verdict |
|-------------|---------|
| Presenton | **BLOCKED_EXTERNAL** / **OPTIONAL_UNAVAILABLE** |
| Voicebox | **OPTIONAL_UNAVAILABLE** |
| PowerPoint COM | **OPTIONAL_UNAVAILABLE** |
| NSIS | **BLOCKED_EXTERNAL** |
| GitHub | **BLOCKED_EXTERNAL** (token name may be present; no live PR cert) |
| Jira | **BLOCKED_EXTERNAL** |
| Camunda | **BLOCKED_EXTERNAL** (`CAMUNDA_BASE_URL` missing) |

These do **not** block ZECT_CORE and do **not** block the internal `ZECT_NEXT_PHASES_READY` verdict. They remain uncertified. Live Generate → Voice → PowerPoint → GitHub is **not** claimed.

## Architecture reconciliation

`ZECT_CANONICAL_ARCHITECTURE.md` updated to code truth at SHA `0dd7bec…`: Graphify = Lattice adapter; `zect.ps1`; desktop PPTX jail; Presenton still default until S8C.

## Tests on this PR

| Gate | Result |
|------|--------|
| pytest Graphify + stack + security + spine | **PASS** (48 passed, 1 skipped) |
| frontend vitest | **PASS** 71 |
| Electron `computer.allowlist.test.js` | **PASS** 11 |
| Headed Playwright `workspace-multi-root` | **PASS** |
| Headed Playwright `present-product` (Generate may 502) | **PASS** UI |
| Headed Playwright Connect Voice (disabled when preflight not ready) | **PASS** |
| Mentrix Ultra Review | **PASS** score 85, 0 critical, `gpt-4o-mini` |
| Full backend pytest (local Windows) | **not claimed PASS** — `test_coding_engine_workspace_api` expects mock/remote while this machine defaults to `mentrix_native`; `test_confirm_sets_plan_confirmed_and_resumes` hits allowed_paths jail. Both are env/CI-skew, not this diff. Ubuntu CI sets `ZECT_CODING_ENGINE=mock`. |
| GitHub CI | this PR — do not auto-merge |
