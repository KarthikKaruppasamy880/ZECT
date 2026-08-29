# ZECT Developer Flow

**Canonical parent:** [`ZECT_SYSTEM_ARCHITECTURE.md`](../../ZECT_SYSTEM_ARCHITECTURE.md)  
**Evidence:** [`ZECT_PRODUCT_ACCEPTANCE.md`](../../ZECT_PRODUCT_ACCEPTANCE.md)

## UX composition (P2 shipped)

App chrome: **Mentrix Delivery Control Tower** (`frontend/src/components/Sidebar.tsx`).

| Section | Primary links |
|---------|----------------|
| Mentrix | Mentrix Companion (`/mentrix-home`), Developer (`/workspace`), Agent Workspace (`/ask`) |
| Work | Projects, Work Items (`/work-items`), Processes (`/fabric`) |
| Intelligence | Project Intelligence, Knowledge Base, Skills Engine, Playbooks, Lattice, Blueprint |
| Delivery | Runs (`/mentrix`), Quality, Git & CI, CI Monitor, Sandbox (+ Agent Mode if flagged) |
| Security | Security (`/security-incidents`), Incident Runbook |
| Operations | System Health, Integrations, Scheduled Tasks, Analytics + **More settings** |

Ask / Plan / Build phase tools live in the **Agent Workspace rail** (`AgentWorkspaceShell`), not as top-level sidebar duplicates.

## Developer Workspace

- Route: `/workspace`
- Right rail: **Context Used** panel (`WorkspaceContextUsedPanel`) — statuses `used` / `missing` / `stale` / `not_used` / `unverified`
- Reuses existing APIs only: Project Intelligence, Work Items, model-readiness (no second context engine)

## ASK / PLAN / AGENT path

1. User opens Companion or Agent Workspace / Developer APIs  
2. `POST /api/mentrix/developer/ask|plan` → MentrixDeveloperService  
3. ContextEngine builds provenance ContextPack; ProjectIntelligence contributes PI snapshot  
4. Plan written to ArtifactStore `PLAN.md` + WorkItem plan hashes  
5. `POST .../approve-plan` required before agent execution  
6. `POST .../agent/start` → Coding Agent / ForgeLoop  
7. Checkpoints → `EXECUTION_STATE.json`; `POST .../resume` restores identity (does not invent a second loop)  
8. EvidenceVerifier → only then `READY_TO_SHIP`

## Companion

- Routes under `/api/mentrix/companion/*`  
- Uses openai_compat gateway when configured  
- Desktop tools require Electron Computer Mode + policy/approval — readiness only in `/api/system/desktop-readiness`

## Pages added in P2/P3 ops surface

| Page | Route |
|------|-------|
| Work Items | `/work-items` |
| Project Intelligence | `/project-intelligence` |
| System Health | `/system-health` (skills bi-sync button, model + desktop readiness) |
