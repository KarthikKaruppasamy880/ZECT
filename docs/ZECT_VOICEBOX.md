# ZECT Voicebox

ZECT-branded local clone TTS HTTP engine for Mentrix (**Chatterbox** client).

Mentrix talks only to **ZECT Voicebox** on `:17493`. For real clone quality today, this service **proxies** to upstream [jamiepine/voicebox](https://github.com/jamiepine/voicebox) on `:17494`. ZECT owns this wrapper’s brand and license; upstream remains under its own license. This repo does **not** ship ML model weights.

## Quick start (Docker / Rancher)

```powershell
# Docker Desktop or Rancher Desktop must be running
powershell -File services/zect-voicebox/scripts/up.ps1
```

Then in `backend/.env`:

```env
CHATTERBOX_BASE_URL=http://127.0.0.1:17493
```

Restart the ZECT API. Companion → **Voice** should show Chatterbox **online**; **Test speak** unlocks for your clone.

### Compose services

| Service | Host port | Role |
|---------|-----------|------|
| `zect-voicebox` | 17493 | Mentrix target (branded proxy) |
| `voicebox-upstream` | 17494 | Upstream Voicebox (build from `third_party/voicebox`) |

Rancher Desktop: import/run [`docker-compose.zect-voicebox.yml`](../docker-compose.zect-voicebox.yml) the same way.

## Without Docker (API shell only)

```powershell
cd services/zect-voicebox
pip install -r requirements.txt
$env:ZECT_VOICEBOX_UPSTREAM_URL = "http://127.0.0.1:17494"
python -m uvicorn app.main:app --host 127.0.0.1 --port 17493
```

`GET /profiles` returns `[]` if upstream is down (Mentrix still treats the engine as reachable). Clone **generate** needs upstream online.

## API (Mentrix contract)

- `GET /health` — `{ brand: "zect-voicebox", backend, upstream_online }`
- `GET/POST /profiles`, `DELETE /profiles/{id}`
- `POST /profiles/{id}/samples` (multipart + `reference_text`)
- `POST /generate` → mirrors audio to `GET /audio/{filename}`

## Tests

```powershell
cd services/zect-voicebox
pytest tests/test_api.py -q
```

## Honest limits

- First upstream model download can take a long time and needs disk/GPU RAM (CPU works, slower).
- LiveKit Agents is a different realtime-agent stack — not used here.
- Replacing the upstream proxy with ZECT-owned ML models is a later project; Mentrix will not need API changes.
