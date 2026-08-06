# Phase 10 Execution Plan — Memory, Skills, Automation

Companion to `Upgrade.md` Phase 10.

| Stage | Scope | Status |
|---|---|---|
| A | Schedule trigger → Mentrix with permission + idempotency | Done (#101) |
| B | Typed memory taxonomy + retention/delete/export + secret-on-write; skill contract gates; watches + due-run + max_attempts | **This PR** |

## Memory types (explicit)

`conversation_history` · `project_knowledge` · `user_preferences` · `reusable_procedures` · `integration_metadata` · `security_incidents`

APIs: `/api/memory/types`, `/typed`, `/typed/export`, `/retention`

## Skills

Approval, allowed tools, timeout, owner/provenance, schemas, test_cases — enforced on `/api/skills-engine/execute/{id}`. Script body never auto-runs for imported skills.

## Automations

`POST /api/schedules/due/run`, `max_attempts` pause, `/api/automation-watches` evaluate.
