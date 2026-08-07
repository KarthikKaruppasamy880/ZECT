# ZECT Coding Engine (CodingRuntime)

ZECT exposes a stable **CodingAgentRuntime** with public providers `mock` | `remote` only.
Third-party Agent Server product names must not appear in routes, UI, or DB values.

## Providers

| `ZECT_CODING_ENGINE` | Behavior |
|---|---|
| `mock` (default) | In-process `MockCodingRuntime` — CI-safe |
| `remote` | HTTP client to an independently running Agent Server (`AgentServerCodingEngine`) |

## Env (server-side only)

```bash
ZECT_CODING_ENGINE=remote
ZECT_CODING_ENGINE_URL=http://127.0.0.1:3010
ZECT_CODING_ENGINE_API_KEY=zect-dev-coding-engine-key
ZECT_CODING_ENGINE_TIMEOUT=30
ZECT_CODING_ENGINE_RETRIES=2
ZECT_CODING_ENGINE_ISOLATION=auto
ZECT_CODING_ENGINE_ISOLATION_STRICT=0
```

Never send the API key to the browser.

## Start the remote Agent Server

```powershell
docker compose -f docker-compose.zect-coding-engine.yml up -d
```

Pin `ZECT_CODING_ENGINE_IMAGE` to a released tag (see compose file). Do not install from an unpinned `main` in production.

Health:

```bash
curl -s http://127.0.0.1:8000/api/coding-engine/health
```

Expect `"provider":"remote"` and `"ready":true` when the Agent Server is up.

## Mentrix Delivery bridge

`POST /api/mentrix/runs` and Companion `start_delivery` both enqueue `run_mentrix_in_background`, which calls `prepare_coding_engine_slice` when `ZECT_CODING_ENGINE=remote` (isolated worktree / optional Docker sandbox, then ForgeLoop).

## Notices

See `THIRD_PARTY_NOTICES.md` for the optional Agent Server MIT notice.
