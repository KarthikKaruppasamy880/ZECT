# Chatterbox sidecar (bundled with ZECT Electron)

Preferred path for operators: run **[ZECT Voicebox](../../../docs/ZECT_VOICEBOX.md)** via

`powershell -File services/zect-voicebox/scripts/up.ps1`

so Mentrix hits `http://127.0.0.1:17493` (branded proxy). Optionally drop a compatible HTTP engine binary in `bin/` so ZECT Desktop can start it without compose.

## Expected API (port 17493)

- `GET /profiles`
- `POST /profiles`, `POST /profiles/{id}/samples`
- `POST /generate`
- `GET /audio/{filename}`
- `GET /health` (ZECT Voicebox branding)

## Layout

```text
resources/chatterbox/
  manifest.json
  bin/                  ← place executable here (not committed)
  scripts/fetch-*.ps1
```

## Build

1. Put binary in `electron/resources/chatterbox/bin/` (see `manifest.json` names), **or** use ZECT Voicebox compose / uvicorn.
2. Or run `scripts/fetch-chatterbox.ps1` with `CHATTERBOX_BUNDLE_URL` pointing at your private release zip.
3. `npm run build:win` — electron-builder copies this folder to `resources/chatterbox` inside the app.

At runtime Electron resolves: `CHATTERBOX_BIN` → bundled `resources/chatterbox/bin/*` → `CHATTERBOX_START_CMD`.
