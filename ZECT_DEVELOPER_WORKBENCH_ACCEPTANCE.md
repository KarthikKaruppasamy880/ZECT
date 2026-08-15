# ZECT Developer Workbench Acceptance

**Date:** 2026-08-14  
**Route:** `/workspace` (`DeveloperWorkspace.tsx`)  
**On develop:** shell, Monaco, terminal, timeline, SplitPane persistence — **yes** (`origin/develop` `c32b975` includes historic workspace PRs).  
**This session:** Lattice/PI state wiring; no Coding Agent / LRR / Ultra Review rebuild.

## Present on develop

| Surface | Status |
|---------|--------|
| Explorer + Monaco editor | Present |
| Agent panel | Present (`MentrixCodingAgentPanel`) |
| Terminal / Mentrix timeline | Present |
| Diff / inline Ask / symbols | Present |
| `SplitPane` drag + `localStorage` + keyboard nudge | Present (`workspace-split-agent` and related keys) |
| `resetSplitLayout` | Present |
| Multi-repo status | Present (`DeveloperMultiRepoStatus`) |
| Repo onboarding | Present; should collapse after activation (existing panel) |
| Active project/repo | `ActiveProjectContext` |

## V2 additions (not yet on develop)

- PI / Lattice canonical `state` instead of `unavailable`/`ok`.
- Index Repository action from PI (`POST /api/repos/{id}/index`).
- Shared control CSS tokens (not yet applied to every workspace chrome).

## Not re-proven this session

- Headed Playwright at 1280×720 / 1366×768 / 1440×900 / 1920×1080  
- Electron `/workspace` parity  
- `'str' object has no attribute 'get'` historically fixed in run-to-dict tests; not re-hunted on live UI  

## Gate

**PARTIAL.** Workbench exists on develop. V2 P1 remaining: viewport + Electron sweep, apply `zect-btn`/`zect-select` consistently, headed PI Index on a real cloned repo.
