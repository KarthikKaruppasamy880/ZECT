# ZECT team demo runbook

Use this for a clean 12-minute demo. Prefer **Demo Mode** (Settings → Advanced) so the sidebar stays on the Project → Workspace → Mentrix spine.

## Ports

| Service | Default |
|---|---|
| Frontend | `http://127.0.0.1:5173` |
| API | Match `frontend/.env.local` → `VITE_API_URL` (often `http://127.0.0.1:8020`) |

Start API on the same port the frontend expects.

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

Without Docker, ZECT falls back to **git worktree** isolation — demos still work.

## Demo spine (12 minutes)

1. **Login** → pick/create Project → Select Repo.
2. **Developer Workspace** (`/workspace`) — open a folder (lazy-loads deep trees), open a file in Monaco.
3. **Code Index** + **Lattice** — show repo intelligence.
4. **Blueprint** (optional) → **Mentrix Delivery** (`/mentrix`) — plan confirm / gates / PR path.
5. Optional: Security Incidents or draft Slack/email (draft-before-send).
6. **Architecture & Compare** only if stakeholders ask “why not Cursor?”

## Presenter notes

- **Agent Workspace** = Ask/Plan/Build shell (`/ask`). **Mentrix Delivery** = gated runs (`/mentrix`).
- **Dual voice:** Connect Voice owns audio; chat TTS is muted while Realtime is connected. Disconnect Voice to use Speak/Narrate TTS.
- Do not promise “0 errors” — show verify/autofix/gates + CI as the quality bar.

## Env flags

| Flag | Effect |
|---|---|
| `VITE_DEMO_MODE=true` | Force Demo Mode on (locks Settings toggle) |
| `VITE_DEMO_MODE=false` | Force Demo Mode off |
| (unset) | Toggle in Settings → Advanced |
