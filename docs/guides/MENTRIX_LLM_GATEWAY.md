# Mentrix Local LLM gateway

Mentrix Local LLM is ZECT’s local chat path: an OpenAI-compatible `/v1` endpoint on your machine. Ask, Plan, and Companion typed chat use `ZECT_LLM_BASE_URL` when set. Connect Voice / Realtime stays on the existing cloud realtime path.

## Why local

| Concern | Mentrix Local LLM |
|---------|-------------------|
| Prompts leave the machine? | No — inference stays on localhost |
| Purchase required for chat experiments? | No — seed a small open-weight model |
| UI branding | Mentrix Local LLM / Mentrix LLM gateway only |

## Quick start (Rancher Desktop)

1. Start Rancher Desktop with **dockerd (moby)**.
2. From the repo root:

```powershell
cd services\mentrix-llm
.\scripts\up.ps1
```

Default seed model id: `qwen2.5:7b` (override: `.\scripts\up.ps1 -SeedModel llama3.1`).

3. Configure `backend/.env`:

```env
ZECT_LLM_BASE_URL=http://127.0.0.1:11434/v1
ZECT_LLM_API_KEY=local
ZECT_LLM_CHAT_MODEL=qwen2.5:7b
MENTRIX_COMPANION_MODEL=qwen2.5:7b
```

4. Restart the ZECT API. In Ask / Plan / Companion, choose a **Mentrix Local** model. Status chip: **Mentrix Local LLM online** when `GET /api/models/gateway` succeeds.

## How ZECT routes chat

```
Ask / Plan / Companion  →  ZECT backend  →  ZECT_LLM_BASE_URL/v1
                                              ↓
                                    Mentrix Local LLM (Rancher)
```

Factory: `backend/app/adapters/llm/openai_compat.py`

| Env | Role |
|-----|------|
| `ZECT_LLM_BASE_URL` | OpenAI-compatible base (include `/v1`) |
| `ZECT_LLM_API_KEY` | Placeholder key for local (`local`) |
| `ZECT_LLM_CHAT_MODEL` | Default model id when UI omits `model` |
| `MENTRIX_COMPANION_MODEL` | Companion default (falls back to chat model) |

If `ZECT_LLM_BASE_URL` is unset, Ask/Plan/Companion use cloud `OPENAI_API_KEY` as before.

## Verify

```powershell
# Gateway
Invoke-RestMethod http://127.0.0.1:11434/v1/models

# ZECT probe (auth as usual)
Invoke-RestMethod http://127.0.0.1:8020/api/models/gateway
```

Ask Mode should return the selected `model` in the response body.

## Out of scope

- Delivery codegen model swap
- Embeddings
- Realtime voice provider change
- Multi-cloud free-tier proxy stacks

## Related

- Mentrix Packs / Mentrix brain: `docs/personal-agent/MENTRIX_PACKS.md`
- Runtime license text: `THIRD_PARTY_NOTICES.md` (Mentrix Local LLM runtime)
