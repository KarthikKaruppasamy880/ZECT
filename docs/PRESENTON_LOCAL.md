# Presenton (self-host) for Mentrix Present Deck

Mentrix **Generate deck** calls your local Presenton instance, downloads the PPTX into Documents/Desktop, and fills Present Deck path. No Presenton Cloud key required when you self-host with your own LLM keys / Ollama.

## Run Presenton (Docker)

```bash
docker run -d --name presenton \
  -p 5000:80 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e LLM=openai \
  -e OPENAI_MODEL=gpt-4o-mini \
  -e AUTH_USERNAME=zect-presenton \
  -e AUTH_PASSWORD=change-me-local \
  -e DISABLE_IMAGE_GENERATION=true \
  -v presenton_data:/app_data \
  ghcr.io/presenton/presenton:latest
```

Presenton **0.9+** requires an admin account and `LLM=<provider>` (e.g. `openai`). Without those, Mentrix sees `428 setup_required` / `Invalid LLM provider` — treat as **BLOCKED_EXTERNAL**, never fake PASS.

Adjust image tag / ports per [Presenton docs](https://docs.presenton.ai/). Some builds use port `5001`.

## Point ZECT at Presenton

In `backend/.env`:

```env
PRESENTON_BASE_URL=http://127.0.0.1:5000
# Presenton 0.9+ uses session login (Mentrix client posts /api/v1/auth/login):
PRESENTON_USERNAME=zect-presenton
PRESENTON_PASSWORD=change-me-local
# Optional API key instead of username/password:
PRESENTON_API_KEY=
# Admin bootstrap only — seeds the ZECT registry once for canonical zinnia-executive-v1.
# Not the normal-user path. Users resolve templates via the ZECT registry mapping.
# ZINNIA_PRESENTON_TEMPLATE_ID=your-presenton-master-id
```

Restart the ZECT backend. Integrations → Zoom + Presenton card shows readiness. Companion → Voice → Present Deck → pick **Template** + **Slides** → **Generate deck**. Product Present (`/present`) defaults to canonical **`zinnia-executive-v1`**.

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

Canonical ZECT id: **`zinnia-executive-v1`** (aliases `zinnia-exec`, `zinnia-executive`). Delivery/risk use `zinnia-delivery-v1` / `zinnia-risk-v1`.

`ZINNIA_PRESENTON_TEMPLATE_ID` is **admin seed into the ZECT registry only** (executive-v1). After seed, `.zect/present-templates/canonical-mapping.json` (or `ZECT_PRESENT_TEMPLATE_ROOT`) is the source of truth. Normal users never read the env var; unmapped Zinnia cards stay `TEMPLATE_NOT_READY` / `zinnia_verified=false`.

1. Upload a real master in Presenton (“bring your design”) and note the provider template id.
2. Admin: `POST /api/mentrix/presentation/templates/mapping` with `zect_id=zinnia-executive-v1` and that provider id (or set the env once so ZECT copies it into the registry).
3. Optional: Present Deck → Template → **Custom template id…** for a one-off generate. Do not treat Presenton built-ins (`modern` / `general` / `standard` / `swift`) as a Zinnia PASS.

## Present Deck after generate

1. Choose **Template** and **Slides** (3–20), enter a prompt, click **Generate deck**.
2. Path auto-fills under Documents/Desktop.
3. Electron: **Open presentation** → **Open Zoom** (optional join URL).
4. **You** join the meeting and share the PowerPoint window.
5. **Narrate talking points** with your Chatterbox clone (or an OpenAI stock voice).

Generate stays disabled until `PRESENTON_BASE_URL` is set. Open presentation / Open Zoom require the Electron app. Clone narrate requires Chatterbox online — see [`CHATTERBOX_LOCAL.md`](CHATTERBOX_LOCAL.md).
