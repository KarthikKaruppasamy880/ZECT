# Windows install & launch (ZECT desktop)

Status: **PARTIAL** — NSIS/portable targets, single-instance lock, and backend sidecar **launcher** ship. Bundled Python runtime is produced at installer build time. Voicebox/Presenton remain optional external. Clean-machine NSIS proof is a separate gate.

## Target flow

```text
Install ZECT
→ Launch ZECT
→ bundled API sidecar starts (userData sqlite + encryption key)
→ Login
→ Companion / Projects / Developer / Learning / Present
→ Quit (managed processes stop)
→ Relaunch (userData preserved)
```

## Runtime classification

| Piece | Classification |
|-------|----------------|
| Electron shell | **PACKAGED** |
| Frontend `dist` | **PACKAGED** (build before `npm run build:win`) |
| Backend API sidecar | **PACKAGED** launcher (`run-api.ps1`); runtime via `bundle_sidecar.py` at build |
| SQLite + encryption key | **PACKAGED** under Electron `userData` (`data/`, `config/`) |
| Voicebox / Chatterbox | **OPTIONAL** (extraResources slot; not required for login) |
| Presenton | **OPTIONAL** / external Docker |
| Local model runtime | **NOT_REQUIRED** for baseline login |
| `start-local.ps1` / Vite | Dev-only; not used in packaged launch |

## What works today

| Piece | Status |
|-------|--------|
| Electron single-instance lock | Implemented |
| `electron-builder` NSIS + portable | Configured |
| Sidecar launcher | `electron/resources/backend/run-api.ps1` |
| Sidecar entry | `zect_api_entry.py` (no reload) |
| Auto-start when packaged | `startBackendSidecar` + `waitForApi` |
| userData `logs` / `config` / `data` | Created on launch |
| Managed child shutdown | `stopManagedChildren` on `will-quit` |
| Secrets in installer | Forbidden — per-user `userData/config/.env` only |
| API on `:8000` | Canonical packaged port |

## Packaged Windows build

```powershell
cd frontend; npm run build
cd ..\electron; npm run build:win
```

`build:win` runs `backend/packaging/bundle_sidecar.py` (copies sources, creates `python-runtime` venv, pip-installs pinned `requirements.txt`) then electron-builder. Runtime is gitignored.

Artifacts land in `electron/dist-electron/`.

## First-run config (not in installer)

Create `%APPDATA%\ZECT\config\.env` on the user machine (or Electron `userData/config/.env`):

```dotenv
ZECT_USERNAME=you@company.com
ZECT_PASSWORD=choose-locally
```

`ENCRYPTION_KEY` is generated into `userData/config/encryption.key` on first sidecar start. Never commit it.

## Remaining gates

- Clean-machine NSIS install on a machine with **no** system Python / repo checkout — prove separately; do not fabricate PASS.
- Voicebox + Presenton remain optional; Present/Voice features need them when used.

## Shutdown / upgrades

- Quit via the app window; second launch focuses the existing process.
- `/api/system/desktop-readiness` reports launcher/runtime/classification.
- Replace NSIS install; preserve `userData`.
