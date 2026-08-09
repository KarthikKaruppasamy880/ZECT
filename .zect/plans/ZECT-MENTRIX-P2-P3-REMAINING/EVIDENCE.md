# EVIDENCE — Mentrix P2 Context Used + UX

| ID | Evidence |
|----|----------|
| EV-CTX | `WorkspaceContextUsedPanel` + `lib/contextUsed.ts` maps PI/WorkItem/model-readiness → used/missing/stale/not_used/unverified |
| EV-CTX-UI | `DeveloperWorkspace` right rail always shows `data-testid="workspace-context-used"` |
| EV-CTX-UT | `frontend/src/lib/contextUsed.test.ts` (3 cases) |
| EV-CTX-E2E | Playwright `Developer Workspace shows Context Used panel` |
| EV-COMPAT | Backend P0+P1+P2: 34 passed; frontend build + 60 unit tests |

## Deferred (do not claim)

Full Playwright green · native deep scanner · Skills DB↔FS sync · advanced desktop · deeper local-model stack
