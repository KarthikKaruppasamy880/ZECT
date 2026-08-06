# Local Chatterbox (clone TTS)

ZECT talks to a locally-running synthesis engine at `CHATTERBOX_BASE_URL` (default `http://127.0.0.1:17493`). Prefer **[ZECT Voicebox](ZECT_VOICEBOX.md)** (branded Mentrix engine) on that port. Electron can manage or **bundle** a sidecar binary — ZECT still does **not** host synthesis in the cloud.

“Offline” means that process is not answering `GET /profiles` — it does **not** mean your clone was deleted from ZECT.

## Configure

In `backend/.env`:

```env
CHATTERBOX_BASE_URL=http://127.0.0.1:17493
```

Restart the ZECT API after changing this.

## Start the engine (recommended)

```powershell
powershell -File services/zect-voicebox/scripts/up.ps1
```

That starts **ZECT Voicebox** on `:17493` (proxies upstream Voicebox on `:17494` for real clone). See [`ZECT_VOICEBOX.md`](ZECT_VOICEBOX.md).

Then confirm:

```bash
curl http://127.0.0.1:17493/profiles
curl http://127.0.0.1:17493/health
```

A successful `/profiles` response means Present can narrate with your clone (generate still needs upstream models ready).

1. In Companion → **Voice**: clone/save a sample if you have not already, then **Test speak**.
2. In **Present Deck**: leave voice on **My default** (or a named clone) and use **Narrate** / **Present & narrate**.

## Behavior

| Voice choice | Engine |
|---|---|
| My default / My voice (clone) | Chatterbox / ZECT Voicebox only — **no** silent OpenAI or browser fallback |
| OpenAI stock voice in the Present dropdown | OpenAI TTS (requires `OPENAI_API_KEY`) |

Check engine status in Voice / Present UI (`GET /api/mentrix/voice/engine-status`), or when speak returns **503** with a start-local-engine message.

Sample saved in ZECT DB ≠ Chatterbox online. See also [`RUNBOOK_LOCAL.md`](RUNBOOK_LOCAL.md) and Companion Voice notes in [`ZECT_OPERATOR_WORKFLOW_GUIDE.md`](ZECT_OPERATOR_WORKFLOW_GUIDE.md).

## Electron managed launch (optional)

Electron can start/stop a local Chatterbox-compatible engine:

```env
CHATTERBOX_BASE_URL=http://127.0.0.1:17493
# Prefer compose (ZECT Voicebox). Or point at uvicorn from services/zect-voicebox:
# CHATTERBOX_START_CMD=python -m uvicorn app.main:app --host 127.0.0.1 --port 17493
CHATTERBOX_BIN=C:\path\to\chatterbox-server.exe
CHATTERBOX_AUTO_START=1
```

From the desktop app (preload):

- `window.zectDesktop.mentrix.chatterboxStatus()`
- `window.zectDesktop.mentrix.chatterboxStart()`
- `window.zectDesktop.mentrix.chatterboxStop()`

Present / Clone Voice still use `GET /api/mentrix/voice/engine-status` for API health.

## Electron binary bundling (sidecar)

ZECT Desktop can **ship a sidecar folder** with the installer (electron-builder `extraResources` → `resources/chatterbox`).

1. Place a ZECT Voicebox / compatible binary in `electron/resources/chatterbox/bin/` (see `manifest.json`).
2. Or fetch a private zip via `CHATTERBOX_BUNDLE_URL` + `npm run chatterbox:fetch --prefix electron`.
3. Build the desktop app (`npm run build:win` in `electron/`).

**Resolve order:** `CHATTERBOX_BIN` → bundled `bin/*` → `CHATTERBOX_START_CMD`.

ZECT **does not commit ML model weights** to git. Operators run [`ZECT_VOICEBOX.md`](ZECT_VOICEBOX.md) compose or supply a licensed binary. Clone-only Present rules still apply: no silent OpenAI fallback for clone voice.
