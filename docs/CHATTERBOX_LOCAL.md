# Local Chatterbox (clone TTS)

ZECT talks to a locally-running synthesis engine at `CHATTERBOX_BASE_URL` (default `http://127.0.0.1:17493`). Electron can manage or **bundle** a sidecar binary (see bundling section below) — ZECT still does **not** host synthesis in the cloud.

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

## Electron managed launch (optional)

Electron can start/stop a local Chatterbox-compatible engine:

```env
CHATTERBOX_BASE_URL=http://127.0.0.1:17493
CHATTERBOX_START_CMD=python -m your_chatterbox_server
# or
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

1. Place a Voicebox/Chatterbox-compatible binary in:

   `electron/resources/chatterbox/bin/`  
   (names: `chatterbox-server.exe`, `Voicebox.exe`, … — see `manifest.json`)

2. Or fetch a private zip:

   ```powershell
   $env:CHATTERBOX_BUNDLE_URL = "https://your-artifacts/chatterbox-win-x64.zip"
   npm run chatterbox:fetch --prefix electron
   ```

3. Build the desktop app (`npm run build:win` in `electron/`). The sidecar is copied next to the app as `resources/chatterbox`.

4. On launch, Electron **auto-starts** the bundled binary when present (or when `CHATTERBOX_AUTO_START=1`). Companion → Voice shows Start/Stop for the bundled engine.

**Resolve order:** `CHATTERBOX_BIN` → bundled `bin/*` → `CHATTERBOX_START_CMD`.

ZECT **does not commit ML model weights** to git (size + licensing). Operators supply the licensed engine binary before packaging. Clone-only Present rules still apply: no silent OpenAI fallback for clone voice.
