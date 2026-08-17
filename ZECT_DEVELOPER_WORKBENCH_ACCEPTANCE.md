# ZECT Developer Workbench Acceptance

**Date:** 2026-08-15  
**Route:** `/workspace` (`DeveloperWorkspace.tsx`)  
**Canonical develop:** `origin/develop` = `1b1cf40` (PR **#153** human-merged).  
**This branch:** `feat/developer-workspace-ux` (not on develop until human merge).

## Chrome (Cursor-class)

| Surface | Status |
|---------|--------|
| Explorer / Editor / Agent / bottom tools | Resizable `SplitPane` (`workspace-split-h`, `workspace-split-agent`, `workspace-split-v`) with drag handle + keyboard nudge |
| Editor-first defaults | Explorer 16% (max 32), agent split 76% editor, vertical 74% editor |
| Persistence | `zect_ws_chrome` for visibility / maximize / bottom tab; split percents stay in existing keys |
| Maximize / hide | `workspace-maximize-explorer\|editor\|agent\|bottom`; toggles clear maximize |
| Bottom tools | Tabs Terminal / Timeline / Context (not a 2–3 column grid). Context Used default off |
| Reset | `workspace-reset-layout` restores chrome + split keys |

## Lattice / stale repo / console noise

- Lattice header + Context Used share `NOT_CONFIGURED \| NOT_INDEXED \| INDEXING \| READY \| STALE \| ERROR \| NOT_APPLICABLE`.
- Indexed SHA vs live HEAD → `STALE` / `commit_moved` (`GET /api/lattice/status?repository_id=`).
- Stale `zect_active_project` ids are cleared **only** after a successful projects/repos list (failed fetch no longer wipes a live selection).
- `getRepoIdentity` / branches run only when the id is in the loaded catalog.
- Session 401/404 clears `zect_session_id`. Presence WS uses `getApiBase()` and stops after 3 failures. Context Used does not refetch on every render.

## Proof this session

- Headed P0: Context Used tab + Lattice state chip **passed**.
- `core-ux-hygiene.spec.ts`: maximize/hide/context **passed**.
- Viewport sweep at 1280×720 / 1366×768 / 1440×900 / 1920×1080: **PASS** on headed `workspace-multi-root.spec.ts` (this PR).
- Electron `/workspace` restore of ≥3 roots: **PASS** locally (`e2e/workspace-electron-restore.spec.ts`). See `ZECT_MULTI_ROOT_DEVELOPER_WORKSPACE_ACCEPTANCE.md`.

## Gate

**READY_TO_MERGE** with the Present P0 branch work (human merge only). Not S8C / Graphify / new agents.
