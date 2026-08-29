# Mentrix Packs and Mentrix brain

Mentrix Packs are portable skill + knowledge bundles for the Mentrix personal agent. All product surfaces use **Mentrix** naming only.

## Concepts

| Mentrix concept | Surface |
|-----------------|--------|
| Progressive skills | Skills Engine: manifest always; full template body when query matches `triggers` / `trigger_keywords` |
| Memory layers | `/api/memory` — **working**, **episodic**, **semantic**, **personal** |
| Permissions | `permission_broker` remains source of truth |
| Mentrix Packs | Import into Skills Engine + Knowledge Base |
| Mentrix brain export | `POST /api/memory/brain-export` → `backend/data/mentrix-brain/` |

## Progressive skills

Skill manifests may declare:

```json
{
  "triggers": ["incident", "runbook"],
  "allowed_tools": ["jira_get_issue", "docs_search"],
  "prohibited_ops": ["delete_file"],
  "template": "Full skill body injected only when a trigger matches…"
}
```

Companion `build_agent_context`:

- Always injects skill name + short description when a skill is selected.
- Injects full `template` only when the user message matches a trigger, or when no triggers are listed.

## Memory layers (operator view)

| Layer | Role |
|-------|------|
| working | Active tasks / scratch for the current session |
| episodic | Recent interaction episodes |
| semantic | Accepted lessons / durable knowledge |
| personal | Preferences and personal facts |

API prefix: `/api/memory`. Retention policies use the same Mentrix type names.

## Mentrix brain export

```http
POST /api/memory/brain-export?project_id=1&write_file=true
```

Returns Mentrix-brain JSON (`format: mentrix-brain-v1`) with skills manifests, typed memory, and layer labels. When `write_file=true`, writes under `backend/data/mentrix-brain/`.

Project-local alternative: copy export into `.mentrix/brain.json` in a workspace (optional ops convention).

## Pack import (minimal)

1. Create a Skill in Skills Engine with Mentrix Pack manifest fields above.
2. Add Knowledge Base snippets for durable pack docs.
3. Select the skill in Companion; mention a trigger phrase to load the full body.

## Deferred

- Full pack marketplace UI
- Nightly flywheel
- IDE adapters

## Related

- Mentrix Local LLM: `docs/guides/MENTRIX_LLM_GATEWAY.md`
- Permission broker: Mentrix Companion tools remain gated by org policy
