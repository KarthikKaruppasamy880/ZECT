# ZECT Developer + Coding Agent reconciliation

Architecture (canonical):
`Developer = engineering cockpit; Coding Agent = executor; Delivery = ship pipeline; Graphify/Lattice = intelligence; WorkItem = durable work; Processes = external intake`.

Do not delete working backend because UI is duplicated. READY means no known release-blocking Critical/High, not “100% / zero error.”

## Classification

| Surface | Classification | Notes |
|---|---|---|
| Developer `/workspace` | KEEP | Single IDE cockpit |
| Mentrix Coding Agent panel | FIX | ASK / PLAN / AGENT / HISTORY (was Mission / Chat) |
| Ask Mode `/ask` | MOVE_TO_DEVELOPER + KEEP route | APIs `/api/llm/ask` stay; e2e still hits Agent Workspace shell |
| Plan Mode `/plan` | MOVE_TO_DEVELOPER + KEEP route | PLAN.md in `.zect/plans/` (gitignored) |
| Build Phase `/build` | DEPRECATE as coding path | LINK to Mentrix Delivery |
| Review / Deploy rails | ADVANCED_VIEW | Quality / `workflow_dispatch` deep links |
| Mentrix Delivery `/mentrix` | KEEP | Prepare PR hands same WorkItem + mission |
| Sidebar Agent Workspace | KEEP for CI/e2e | Hide from primary nav only after headed e2e updated; Developer is cockpit |
| Agent Mode `/agent-mode` | ADVANCED_VIEW | Settings flag; do not retire until compatibility audit |
| Delivery Runs / Quality / Git & CI / Sandbox | ADVANCED_VIEW | LINK_FROM_DEVELOPER summaries |
| Terminal Start app `npm run dev` at clone root | FIX | Runtime Discovery (ZOAS nested `zinnia-modern`) |
| Bottom Tests tab | FIX | Live last-run output + multi-repo status |
| Graphify / Lattice | KEEP | Intelligence; re-index when STALE |
| Jira / Camunda | KEEP | BLOCKED_EXTERNAL if connector down; WorkItem flow stays |
| Present Deck 500-char cap | FIX | Presenter Intelligence + full audio |
| Builtin org template Delete | FIX | Hide Delete; human error not raw `not_found` |
| Learning Studio | MISSING | Plan-only this wave (`ZECT_AI_LEARNING_STUDIO_PLAN.md`) |

## Contracts

- Plan artifact: `.zect/plans/<workitem-or-run>-<slug>.md`
- Runtime recipe: `{ id, kind, command, cwdRel, port?, confirmRequired, evidence }` — no secrets; Postgres not started by ZECT
- Ship handoff: `{ work_item_id, coding_mission_id, delivery_run_id }` — reject duplicate open Delivery run
