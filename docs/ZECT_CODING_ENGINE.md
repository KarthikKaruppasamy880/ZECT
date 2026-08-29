# ZECT Coding Engine / Mentrix Coding Agent

ZECT exposes a stable **CodingAgentRuntime** with public providers:

| `ZECT_CODING_ENGINE` | Behavior |
|---|---|
| `mentrix_native` (**product default**) | **Mentrix Coding Agent** — tool loop (read/search/edit/run/git) |
| `mock` (CI only — set env explicitly) | In-process placeholders |
| `remote` | HTTP client to an independently running Agent Server |

Third-party Agent Server product names must not appear in routes, UI, or DB values.

## Mentrix Coding Agent (recommended for real coding)

```bash
ZECT_CODING_ENGINE=mentrix_native
ZECT_CODING_ENGINE_ISOLATION=worktree
# LLM (Mentrix Local gateway or cloud)
ZECT_LLM_BASE_URL=http://127.0.0.1:11434/v1
ZECT_LLM_API_KEY=local
ZECT_LLM_CHAT_MODEL=qwen2.5:7b
# or OPENAI_API_KEY / ANTHROPIC_API_KEY
```

API:

- `POST /api/coding-agent/sessions` — start
- `GET /api/coding-agent/sessions/{id}/stream` — SSE events
- `POST .../approve`, `.../cancel`, `.../message`

UI: Developer Workspace → **Mentrix Coding Agent** panel.

Delivery: when `mentrix_native` is set (product default), ForgeLoop **build** uses the Mentrix Coding Agent against the run workspace.

## Remote Agent Server (optional)

```powershell
docker compose -f docker-compose.zect-coding-engine.yml up -d
```

See also [`docs/personal-agent/CODING_READINESS.md`](personal-agent/CODING_READINESS.md).
