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

Restart the ZECT backend. Integrations → Zoom + Presenton card shows readiness. Companion → Voice → Present Deck → pick **Template** + **Slides** → **Generate deck**.

## Templates

Built-in Presenton template names (always available in the Present Deck picker, even if Presenton is down for listing):

| Id | Label |
|----|--------|
| `general` | General |
| `modern` | Modern |
| `standard` | Standard |
| `swift` | Swift |

When Presenton is reachable, ZECT also loads remote templates via `GET /api/v1/ppt/template/all` and shows them in the same dropdown.

### Custom masters (Zinnia / team)

1. Upload masters in the Presenton UI (“bring your design”).
2. Note the template id Presenton assigns.
3. In Present Deck → Template → **Custom template id…** → paste that id → Generate.

## Present Deck after generate

1. Choose **Template** and **Slides** (3–20), enter a prompt, click **Generate deck**.
2. Path auto-fills under Documents/Desktop.
3. Electron: **Open presentation** → **Open Zoom** (optional join URL).
4. **You** join the meeting and share the PowerPoint window.
5. **Narrate talking points** with your Chatterbox clone (or an OpenAI stock voice).

Generate stays disabled until `PRESENTON_BASE_URL` is set. Open presentation / Open Zoom require the Electron app. Clone narrate requires Chatterbox online — see [`CHATTERBOX_LOCAL.md`](CHATTERBOX_LOCAL.md).
