# ZECT local stack controller

Use this instead of memorizing backend / Vite / Electron commands.

```powershell
./zect.ps1 up --profile desktop
./zect.ps1 status
./zect.ps1 health
./zect.ps1 logs backend
./zect.ps1 restart backend
./zect.ps1 restart electron
./zect.ps1 down
./zect.ps1 doctor
```

Profiles:

| Profile | Services |
|---------|----------|
| `core` | backend `:8020` + Vite `:5173` |
| `desktop` | core + Electron (after backend/frontend health) |
| `full` | desktop + optional Presenton `:5000` + Voicebox `:17493` |

## Ports (repo truth)

| Surface | Port | Notes |
|---------|------|--------|
| Local API (`scripts/start-local.ps1`, `zect.ps1`) | **8020** | `GET /healthz` |
| Local Vite | **5173** | |
| CI / packaged Electron API | **8000** | Do not change CI to 8020 |
| Presenton (optional) | 5000 | `OPTIONAL_UNAVAILABLE` if not running |
| Voicebox (optional) | 17493 | `OPTIONAL_UNAVAILABLE` if not running |

## Ownership

Runtime state is ignored `.zect/stack/` (PIDs + logs). `zect down` stops **only controller-owned PIDs**. It does **not** call `scripts/stop-local.ps1`, which kills by port and every `electron` process.

If `:8020` or `:5173` is already occupied by a process this controller did not start, `zect up` returns **ERROR** / `EXTERNAL` and leaves that process running.

Optional Presenton / Voicebox never fail a required profile as PASS. Missing optional services are `OPTIONAL_UNAVAILABLE`.

## Existing scripts

`config/zect-stack.yaml` references the same commands as `scripts/start-local.ps1`. Keep those in sync. `scripts/restart-local.ps1` still exists for the old `-StopFirst` path; prefer `zect.ps1 restart`.

## Environment

Copy `backend/.env.example` to `backend/.env`. `zect doctor` prints **env names** as present/missing — never secret values.

## Smoke

`down → up --profile core → health → restart backend → health → up --profile desktop → Electron → restart electron → down`

Do not `taskkill electron.exe` globally.
