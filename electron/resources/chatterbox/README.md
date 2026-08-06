# Chatterbox sidecar (bundled with ZECT Electron)

Drop a **Voicebox / Chatterbox-compatible** HTTP engine binary in `bin/` so ZECT Desktop can start it without `CHATTERBOX_START_CMD`.

## Expected API (port 17493)

- `GET /profiles`
- `POST /profiles`, `POST /profiles/{id}/samples`
- `POST /generate`

## Layout

```text
resources/chatterbox/
  manifest.json
  bin/                  ← place executable here (not committed)
  scripts/fetch-*.ps1
```

## Build

1. Put binary in `electron/resources/chatterbox/bin/` (see `manifest.json` names).
2. Or run `scripts/fetch-chatterbox.ps1` with `CHATTERBOX_BUNDLE_URL` pointing at your private release zip.
3. `npm run build:win` — electron-builder copies this folder to `resources/chatterbox` inside the app.

At runtime Electron resolves: `CHATTERBOX_BIN` → bundled `resources/chatterbox/bin/*` → `CHATTERBOX_START_CMD`.
