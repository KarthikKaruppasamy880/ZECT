# ZECT local runbook

Ports, isolation, and startup for Mentrix development and team walkthroughs. Presentation talk track: [`TEAM_PRESENTATION.md`](TEAM_PRESENTATION.md).

## Ports

| Service | Default |
|---|---|
| Frontend | `http://127.0.0.1:5173` |
| API | Match `frontend/.env.local` → `VITE_API_URL` (often `http://127.0.0.1:8020`) |

Start the API on the same port the frontend expects.

## Rancher Desktop (coding-engine isolation)

1. Rancher Desktop → Preferences → Container Engine = **dockerd (moby)**.
2. Confirm: `docker version` and `docker ps`.
3. In `backend/.env`:

```env
ZECT_CODING_ENGINE_ISOLATION=auto
ZECT_CODING_ENGINE_ISOLATION_STRICT=0
ZECT_CODING_ENGINE_SANDBOX_IMAGE=python:3.12-slim
```

4. Optional: `docker pull python:3.12-slim`
5. Restart API; coding-engine health should report Docker available when the daemon is up.

Without Docker, ZECT falls back to **git worktree** isolation — workflows still work.

## Schedule worker hook

Due schedules are polled via:

```http
POST /api/schedules/due/run
```

Wire a cron/job runner (or call manually during demos) so **Scheduled Tasks** fire Mentrix or playbook runs.

## Quality bar

Gates + verify + approve + CI. Do not claim zero-defect codegen.
