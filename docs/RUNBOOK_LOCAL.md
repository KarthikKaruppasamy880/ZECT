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

## Mentrix phased Build (large projects)

Large goals use **Plan → human confirm → batched Build → Workspace review → Approve → PR**:

1. Mentrix Delivery (`/mentrix`) — start upgrade/bugfix/deliver with workspace + Lattice key.
2. Confirm the plan (`files_expected` listed). Build will not start until confirmed.
3. After each file batch, status is `awaiting_batch_confirm` — open **Workspace** (`/workspace?run=<id>`) to review diffs, then **Confirm batch**.
4. Gates (incomplete / grounding / lint / Ultra Review) must be green; incomplete or missing expected files **cannot** approve.
5. Human **Approve**, then **Create PR**. Quality bar is gated delivery — not “100% / zero error.”

Env knobs: `MENTRIX_BUILD_BATCH_SIZE` (default 6), `MENTRIX_MAX_FILES_PER_RUN` (default 40), `MENTRIX_REQUIRE_PLAN_CONFIRM`.

## Quality bar

Gates + verify + approve + CI. Do not claim zero-defect codegen.

## Local Chatterbox (clone TTS)

Present / Test speak with your saved clone need a local engine at `CHATTERBOX_BASE_URL` (default `http://127.0.0.1:17493`). Preferred: run ZECT Voicebox — see [`ZECT_VOICEBOX.md`](ZECT_VOICEBOX.md) and [`CHATTERBOX_LOCAL.md`](CHATTERBOX_LOCAL.md).
