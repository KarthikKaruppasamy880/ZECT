# Mentrix typed memory (operators)

Companion can store short preference/procedure facts. This is **not** full desktop omniscience.

## Types

`GET /api/memory/types` lists the taxonomy (preference, procedure, episode, decision, lesson, etc.).

## Companion “remember”

Phrases like “remember that…” / “note that…” map to Companion `note_add` and/or typed memory records when wired. Prefer Settings → **Preferred name** for how Mentrix addresses you.

## Operator expectations

| Do | Don't |
|---|---|
| Store durable prefs / procedures | Assume Mentrix sees every app/window |
| Scope by project when possible | Expect unlimited retention without policy |
| Review typed memory via memory APIs | Claim zero-forget / full OS awareness in UI |

Retention policies live under personal-agent memory retention endpoints. Secrets never belong in memory records.
