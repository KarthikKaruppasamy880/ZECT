# Skills Engine — per-project packs (operators)

## Scoping

- Seed skills have `project_id=null` (global).
- Project skills attach via `project_id` on create / Skills Engine UI filter.
- Companion active skill (`mentrix_active_skill_id` + Mentrix skill picker) injects `manifest.template` into Mentrix Scout/Planner context.

## Operator recipe

| Repo / goal | Suggested pack |
|---|---|
| ZOAS / Mentrix Delivery ship | Delivery-oriented seeds + project-specific ZOAS skill if registered |
| Multi-repo work | Filter Skills Engine by active project; attach only packs for that `project_id` |
| New greenfield | Use “Use for new project” from Skills Engine to scaffold |

## API

- `GET /api/skills-engine/skills?project_id=<id>` — global seeds + that project's skills
- Match / execute accept optional `project_id`

Never claim a skill pack guarantees bug-free codegen.
