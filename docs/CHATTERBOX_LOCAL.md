# Local Chatterbox (clone TTS)

ZECT does **not** ship or host Chatterbox. Present / Test speak with your saved clone call **your** local synthesis engine at `CHATTERBOX_BASE_URL` (default `http://localhost:17493`).

“Offline” means that process is not answering `GET /profiles` — it does **not** mean your clone was deleted from ZECT.

## Configure

In `backend/.env`:

```env
CHATTERBOX_BASE_URL=http://localhost:17493
```

Restart the ZECT API after changing this.

## Start the engine

1. Start your local Chatterbox (or compatible) server so it listens on the URL above.
2. Confirm health:

```bash
curl http://localhost:17493/profiles
```

A successful response means Present can narrate with your clone.

3. In Companion → **Voice**: clone/save a sample if you have not already, then **Test speak**.
4. In **Present Deck**: leave voice on **My default** (or a named clone) and use **Narrate** / **Present & narrate**.

## Behavior

| Voice choice | Engine |
|---|---|
| My default / My voice (clone) | Chatterbox only — **no** silent OpenAI or browser fallback |
| OpenAI stock voice in the Present dropdown | OpenAI TTS (requires `OPENAI_API_KEY`) |

Check engine status in Voice / Present UI (`GET /api/mentrix/voice/engine-status`), or when speak returns **503** with a start-local-engine message.

Sample saved in ZECT DB ≠ Chatterbox online. See also [`RUNBOOK_LOCAL.md`](RUNBOOK_LOCAL.md) and Companion Voice notes in [`ZECT_OPERATOR_WORKFLOW_GUIDE.md`](ZECT_OPERATOR_WORKFLOW_GUIDE.md).
