# Windows install & launch (ZECT desktop)

Status: **PARTIAL** — NSIS/portable Electron targets exist; single-instance lock is implemented; the FastAPI backend is **not** fully bundled inside the installer yet.

## Target flow

```text
Install ZECT
→ Launch ZECT
→ required local services managed automatically
→ ZECT ready
```

## What works today

| Piece | Status |
|-------|--------|
| Electron single-instance lock | Implemented (`requestSingleInstanceLock` + focus existing window) |
| `electron-builder` NSIS + portable | Configured in `electron/package.json` |
| Frontend `dist` packaged into app | When `frontend/dist` built before `npm run build:win` (asar path `frontend/dist`) |
| userData `logs` / `config` / `data` | Created under Electron `userData` on launch |
| Managed child shutdown | `service-lifecycle.stopManagedChildren()` on `will-quit` |
| Chatterbox extraResources | Slot present under `electron/resources/chatterbox` |
| Backend extraResources slot | `electron/resources/backend/` (empty until sidecar shipped) |
| API on `:8000` | Canonical default; must be running until sidecar exists |
| Vite `:5173` | Dev only; packaged builds use `frontend/dist` |
| Voicebox / Presenton | Optional external services; do not fake PASS |
| Managed service probe | `electron/service-lifecycle.js` when `ZECT_MANAGE_SERVICES=1` |

## Developer install (current)

1. Clone repo; create `backend/.env` from `.env.example` (never commit secrets).
2. Start API: Python 3.12+ with `uvicorn` on `127.0.0.1:8000` (or set `VITE_API_URL` / `ZECT_API_URL`).
3. Start UI: `frontend` Vite on `:5173` **or** build `frontend/dist` and set `ZECT_USE_DIST=1`.
4. Launch desktop: `cd electron && npm start`.
5. Optional: set `ZECT_MANAGE_SERVICES=1` so Electron can probe and attempt `start-local.ps1`.

`scripts/start-local.ps1` may still use `:8020` for local convenience; it writes `frontend/.env.local` accordingly. Packaging readiness and desktop probes default to `:8000`.

## Packaged Windows build

```powershell
cd frontend; npm run build
cd ..\electron; npm run build:win
```

Artifacts land in `electron/dist-electron/`.

## Blockers for full one-click

- Backend runtime (Python deps / embedded uvicorn / `zect-api.exe`) not inside NSIS `extraResources/backend`.
- Voicebox + Presenton remain external; ordinary Present/Voice flows need them separately.
- Secrets/config must live under user data, not baked into the installer.
- Clean-machine install → Login → Companion/Projects/Developer/Learning/Present not yet proven without an external API.

## Shutdown / health / upgrades

- Prefer quitting via the app window; second launch focuses the existing process (single-instance).
- System Health UI → `/api/system/desktop-readiness` reports packaging honesty fields (`single_instance_lock`, `backend_bundled`, blockers).
- Upgrades: replace NSIS install; preserve user DB/secrets outside the install tree under `userData`.

Do **not** claim installer-ready / one-click PASS until backend lifecycle is bundled and verified on a clean Windows machine.
