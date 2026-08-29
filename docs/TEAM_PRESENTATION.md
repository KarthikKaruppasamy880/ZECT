# ZECT team presentation (Mentrix)

Talk track for showing ZECT as a **real coding agent** — not a toy demo mode. No third-party product names in slides or UI.

Full architecture: [`ARCHITECTURE_AND_WORKFLOWS.md`](ARCHITECTURE_AND_WORKFLOWS.md), [`TARGET_ARCHITECTURE.md`](TARGET_ARCHITECTURE.md). Local ports/isolation: [`RUNBOOK_LOCAL.md`](RUNBOOK_LOCAL.md).

## One-sentence pitch

ZECT Mentrix is a delivery control tower: open a project, edit in Developer Workspace, index the repo, run gated Ask → Plan → Build → Review → Deploy, and speed repeat work with Labs (Skills, Playbooks, Knowledge, Schedules, Memory, Permissions).

## Spine (12 minutes)

1. **Login** → create/select **Project** → select repo.
2. **Developer Workspace** (`/workspace`) — browse deep folders, open files in Monaco, optional terminal.
3. **Code Index** + **Lattice** (+ optional **Blueprint**) — repo intelligence.
4. **Agent Workspace** (`/ask`) — Ask / Plan / Build phases.
5. **Mentrix Delivery** (`/mentrix`) — gates, verify, approve, PR path.
6. **Labs productivity** — Knowledge (context), Skills / Playbooks (repeat), Scheduled Tasks (automation), Memory + Permissions.

## Labs that matter for “10x”

| Lab | What to say |
|---|---|
| Knowledge Base | Team conventions and prompt snippets injected into Mentrix — less paste, fewer tokens |
| Skills Engine | Reusable procedures; scaffold a new project from a skill template |
| Playbooks | Multi-step Mentrix workflows with variables |
| Scheduled Tasks | Cron/interval Mentrix or playbook runs |
| Memory System | Long-lived preferences and typed project knowledge |
| Permissions | Capability gates before agent and schedule actions |

Advanced Labs (Security, Notes, Transfer, Conversations, Architecture diagrams) live under **More Labs**. Experimental pages (Dream Engine, Data Layer, etc.) stay routable via Docs/deep links but are not in the main nav.

## Presenter notes

- **Agent Workspace** = Ask/Plan/Build shell. **Mentrix Delivery** = gated delivery runs.
- Dual voice: Connect Voice owns audio; chat TTS is muted while Realtime is connected.
- Do **not** promise “0 errors.” Show verify, autofix, gates, and CI as the quality bar.
- Branding: ZECT Mentrix only — adapters stay unnamed in product UI; legal attribution in `THIRD_PARTY_NOTICES.md`.

## Suggested slide order

1. Problem → delivery control tower  
2. Architecture diagram (Architecture Labs page or `ARCHITECTURE_AND_WORKFLOWS.md`)  
3. Live: Project → Workspace → Index → Mentrix  
4. Live: Knowledge + Skill/Playbook + Schedule  
5. Governance: Permissions, Secrets, Audit  
6. Q&A / local runbook  
