# ZECT — Repository / Branch / PR / Worktree UX Acceptance

**Branch:** `feat/zect-repo-branch-pr-worktree-ux`  
**Date:** 2026-08-13  
**Status:** PASS (headed live Flows A–F)  
**Merge:** DO NOT auto-merge (explicit stop)

## 1. Audit matrix (Phase 6 reuse)

| Capability | Classification | Location / notes |
|---|---|---|
| Create Project | ALREADY_BUILT → VISIBLE_AND_WORKING (extended) | `CreateProject.tsx` — empty / registered / local / clone / GitHub meta |
| Open Existing Local Repo | MISSING → VISIBLE_AND_WORKING | `POST /api/repos/register-local`, `RepoOnboardingPanel` |
| Browse local folder | PARTIAL | Path input (OS native file picker not required for acceptance) |
| Clone Git URL | PARTIAL → VISIBLE_AND_WORKING | `POST /api/repos/clone-url` + Projects UI destination |
| Discover local repos | MISSING → VISIBLE_AND_WORKING | `POST /api/repos/discover` under `allowed_roots` only |
| Attach registered repo | PARTIAL → VISIBLE_AND_WORKING | `POST /api/projects/{id}/repos` with `repo_id` |
| Select Repo | PARTIAL → VISIBLE_AND_WORKING | `ProjectRepoSelector` + onboard link |
| Repo activation | ALREADY_BUILT | `ActiveProjectContext` + Mentrix workspace write |
| Branch listing | ALREADY_BUILT | `GET /api/repos/{id}/branches` |
| Remote branch listing | ALREADY_BUILT | same |
| Fetch | ALREADY_BUILT / PARTIAL | pull/fetch via existing clone service; worktree path fetches |
| Safe branch switch | PARTIAL → VISIBLE_AND_WORKING | `dirty_action` on checkout + UI modal |
| Dirty-repo handling | MISSING → VISIBLE_AND_WORKING | Cancel / Stash / Force discard (explicit) |
| PR listing | ALREADY_BUILT (multi-repo fix) | `ProjectDetail` selected-repo tabs (was `repos[0]` only) |
| PR URL/number open | MISSING → VISIBLE_AND_WORKING | Open PR by number + head branch → worktree |
| PR → head resolution | PARTIAL → WORKING | resolve local/`origin` refs to SHA |
| Git worktree create/reuse | BACKEND_ONLY → WORKING | `POST /api/repos/{id}/pr-worktree` (`zect-pr-N`) |
| Developer worktree binding | PARTIAL → WORKING | `writeMentrixWorkspace(worktree_path, …)` |
| LRR worktree binding | PARTIAL | existing `worktree_path` on long-running start unchanged |
| PI stale/re-index after HEAD | PARTIAL | checkout returns `pi_hint: STALE`; Lattice chip Not indexed |

## 2. Architecture reused (no second catalog)

- Phase 6 `Project` / `Repo` models and `repo_clone` workspace
- `allowed_paths.path_under_allowed_roots`
- Existing GitHub PR list APIs
- Active project/repo context + Lattice status chip

New service only: `backend/app/services/repo_onboarding.py`

## 3. Implemented wiring

**Backend**
- `register-local`, `discover`, `clone-url`, `identity`, dirty-safe `checkout`, `pr-worktree`
- Attach-by-`repo_id` on `POST /api/projects/{id}/repos`

**Frontend**
- `RepoOnboardingPanel` on `/projects` and project detail
- Create Project setup modes
- Dirty checkout modal in `ProjectRepoSelector`
- Multi-repo PR tabs + Open worktree / Open by number

## 4. Live headed Playwright

**Command:**

```text
npx playwright test e2e/repo-branch-pr-worktree-ux.spec.ts --headed --project=chromium --trace=on
```

**Result:** `2 passed` (auth setup + Flows A–F) against real uvicorn `:8000` + Vite `:5173`

**Artifacts:** `frontend/test-results/repo-ux-headed/`

| File | Flow |
|---|---|
| `01-projects-onboarding.png` | Onboarding CTAs visible |
| `02-flow-a-bound.png` / `03-flow-a-active.png` | A — open local bind/activate |
| `04-flow-b-branch.png` | B — branch switch |
| `05-flow-c-dirty-block.png` / `06-flow-c-stash.png` | C — dirty block + stash |
| `07-flow-e-discover.png` | E — discover |
| `08-flow-d-clone.png` | D — clone `file://` bare remote (no credentials) |
| `09-flow-f-worktree.png` | F — PR worktree UI |
| `flow-f-worktree.json` / `evidence.json` | API worktree identity |

**Worktree evidence (controlled fixture):**

```json
{
  "ok": true,
  "branch": "zect-pr-99",
  "main_unchanged": true,
  "worktree_path": "...\\app-repo-a-...-worktrees\\pr-99"
}
```

Main checkout was not switched for the worktree operation (`main_unchanged: true`).

Disposable Git fixtures under OS temp only — **real ZECT working copy not reset/cleaned**.

## 5. Automated tests

```text
pytest tests/fixes_and_phases/test_repo_onboarding_ux.py
→ 22 passed
```

Covers: inspect/register/dedupe, attach, discover boundary, dirty checkout, PR worktree isolation, path denial, API routes.

## 6. Security notes

- Paths gated by `allowed_roots`
- Discover requires explicit user-approved root
- Tokens redacted on clone errors; never shown in UI
- Dirty discard requires explicit `force_discard`
- Client IDs are not treated as auth proof beyond existing session Bearer (Phase 13 stack unchanged)

## 7. Frozen regression

Targeted onboarding suite green (`22 passed`). Full Present A1–A8 / B / C / D mega-suite not re-executed in this stop window; no intentional changes to those frozen surfaces.

Smoke: real `/healthz` OK; headed Flows A–F PASS.

## 8. Remaining PARTIAL / BLOCKED

| Item | Status |
|---|---|
| Native OS folder picker | PARTIAL — path text entry works |
| Live GitHub PR list for private repos | BLOCKED_EXTERNAL without token/network |
| Automatic Lattice re-index after every checkout | PARTIAL — STALE/Not indexed signaled; user/agent re-index via existing PI |
| LRR auto-bind from PR button | PARTIAL — workspace path set; LRR start still takes explicit `worktree_path` |
| ASK/PLAN/AGENT cross-repo aggregate EvidenceVerifier | PARTIAL — multi-repo attach/switch LIVE_E2E proven; full cross-repo agent aggregate not claimed |

## 9. Multi-Repo LIVE_E2E (2026-08-13)

**Command:** `npx playwright test e2e/multi-repo-live.spec.ts --headed`

**Result:** PASS — attach A/B/C disposable fixtures to one Project, UI repo count ≥2, switch selector to second repo with distinct identity; Developer route smoke.

**Artifacts:** `frontend/test-results/multi-repo-live/`

| Proof | Status |
|---|---|
| Project → Repo A+B+C attach | LIVE_E2E |
| Select/switch repos | LIVE_E2E |
| Independent branch labels visible | LIVE_E2E (fixture branches) |
| Duplicate attach safe | API covered |
| ASK/PLAN/AGENT multi-PR aggregate | PARTIAL (not fully headed in this tranche) |

## 10. Stop condition

STOP after multi-repo LIVE_E2E acceptance update. Remaining ASK/PLAN/AGENT aggregate stays PARTIAL until a dedicated agent tranche.
