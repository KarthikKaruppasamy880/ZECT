# Presenton (self-host) for Mentrix Present Deck

Mentrix **Generate deck** calls your local Presenton instance, downloads the PPTX into Documents/Desktop, and fills Present Deck path. No Presenton Cloud key required when you self-host with your own LLM keys / Ollama.

## Run Presenton (Docker)

```bash
docker run -d --name presenton \
  -p 5000:80 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v presenton_data:/app_data \
  ghcr.io/presenton/presenton:latest
```

Adjust image tag / ports per [Presenton docs](https://docs.presenton.ai/). Some builds use port `5001`.

## Point ZECT at Presenton

In `backend/.env`:

```env
PRESENTON_BASE_URL=http://127.0.0.1:5000
# Optional if your Presenton build requires auth:
PRESENTON_API_KEY=
PRESENTON_USERNAME=
PRESENTON_PASSWORD=
```

Restart the ZECT backend. Integrations → Zoom + Presenton card shows readiness. Companion → Voice → Present Deck → **Generate deck**.

## Templates (Zinnia / team)

Upload masters in the Presenton UI (“bring your design”), note the template id, then pass it via API later (Mentrix currently defaults to `general`; extend `template` in Generate deck when you have a Zinnia master id).

## Present Deck after generate

1. Path auto-fills under Documents.
2. Electron: **Open presentation** → **Open Zoom** (optional join URL).
3. **You** join the meeting and share the PowerPoint window.
4. **Narrate talking points** with your Chatterbox clone.
