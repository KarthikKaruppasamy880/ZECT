# ZECT Current Branch Closeout — Before Sovereignty

**Date:** 2026-08-13  
**Spec:** `prompts/ZECT_CURRENT_BRANCH_CLOSEOUT_BEFORE_SOVEREIGNTY.md`  
**Branch:** `feat/release-closure-core-ux` @ `1d97637`  
**origin/develop:** `45f4407fc2c5603db572e7b23b88289226557aeb`  
**Sovereignty plan:** **NOT STARTED** (`prompts/ZECT_OSS_SOVEREIGNTY_NATIVE_ENGINES_PLAN.md` unread for implementation)

## Verdict

**BLOCKED_EXTERNAL** for publish/merge.  
**PARTIAL** for locally closed Core UX.  
**Not** `READY_FOR_SOVEREIGNTY_AUDIT` — canonical `develop` is unchanged.

GitHub CLI is not logged in. Per operator: human will create the PR for this branch after login. This session does not invent PATs or dump credential helpers.

## Git truth

| Field | Value |
|-------|--------|
| Local branch | `feat/release-closure-core-ux` |
| Parent | `184aa78` (R1.6–R3.6 acceptance) |
| Production commits on this branch vs `45f4407` | `92e206e` + `184aa78` + `1d97637` |
| `gh auth` | not logged in |
| Push / PR / CI / Ultra Review on origin | **BLOCKED_EXTERNAL** |
| Merge SHA | none |

## What this closeout includes (production)

- Present editor + UI PPTX export (allowlisted paths, notes sidecar)
- Developer SplitPane workbench (Explorer \| Editor \| Agent, toggle/reset)
- Timeline string-payload harden
- Projects fixture hide + search (hide, do not delete by pattern)
- Sample Process → WorkItem; Jira/Camunda ingest UI on existing adapter
- Untrusted-external tagging on ingest
- Voice selectors: clone / stock / No narration
- Headed specs: `present-editor-export.spec.ts`, `core-ux-hygiene.spec.ts`
- Acceptance docs for Core UX and preserved R1.6–R4 gates

Not committed: `.zect/`, `test-results/`, `backend/.env`, sovereignty plan, canonical-audit spec, leftover `(1).md` dump.

## Locally re-proven (ZECT UI, not Presenton)

See prior session + this closeout headed re-run notes in the commit/PR body.

| Gate | Status |
|------|--------|
| Present editor | PASS (headed) |
| Present export | PASS (headed) |
| Projects/WorkItems/Processes/Developer toggles | PASS (headed) |
| Voice selectors visible | PASS (headed) |
| Clone ≥2 slides live Chatterbox | NOT RE-RUN — prior 1-slide PASS preserved |
| Standard voice live speak | PARTIAL (selector only) |
| Disconnect live | UNIT_PASS only |
| Multi-repo READY_AFTER_FIX | Spec updated; live GitHub re-run **BLOCKED_EXTERNAL** (no `gh`; leftover DELETE 403) |
| Clean-machine NSIS / packaged Present/Voice | **BLOCKED_EXTERNAL** |

## Human PR steps (when authenticated)

```text
gh auth login
git fetch origin
git push -u origin feat/release-closure-core-ux
gh pr create --base develop --head feat/release-closure-core-ux --title "feat: Core UX Present editor/export and workbench hygiene" --body-file - 
```

Target **develop**, never main. After CI + Ultra Review: fix valid Critical/Major on the same PR, then merge, sync, post-merge smoke. Only then is `READY_FOR_SOVEREIGNTY_AUDIT` allowed.

## Stop

STOP. Do not start S1 / native-engine sovereignty.
