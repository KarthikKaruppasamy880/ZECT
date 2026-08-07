# ZECT Voicebox

ZECT-branded **native** local clone TTS HTTP engine for Mentrix (**Chatterbox** client).

Mentrix talks only to **ZECT Voicebox** on `:17493`. This service stores profiles/samples locally and synthesizes speech on the machine — **no third-party upstream proxy**.

This repo does **not** ship ML model weights. Optional real clone quality uses `requirements-ml.txt` (Chatterbox Multilingual); without ML, stub WAV keeps the Mentrix speak pipeline working (`ZECT_VOICEBOX_ALLOW_STUB=1`, default).

## Quick start (Docker / Rancher)

**Rancher Desktop:** Preferences → Container Engine → **dockerd (moby)**. Wait until the VM is Running. If `docker info` fails, try `docker context use default`.

```powershell
powershell -File services/zect-voicebox/scripts/up.ps1
```

Then in `backend/.env`:

```env
CHATTERBOX_BASE_URL=http://127.0.0.1:17493
CHATTERBOX_SPEAK_TIMEOUT=120
```

Use **`127.0.0.1`**, not `localhost` (Windows IPv6 often breaks health checks).

Restart the ZECT API. Companion → **Voice** should show Chatterbox **online**; **Test speak** unlocks.

Browser check: http://127.0.0.1:17493/ (JSON index), `/health` (`backend: native`, `models_ready`), `/profiles`.

## Without Docker

```powershell
cd services/zect-voicebox
pip install -r requirements.txt
# Optional real clone:
# pip install -r requirements-ml.txt
$env:ZECT_VOICEBOX_ALLOW_STUB = "1"
python -m uvicorn app.main:app --host 127.0.0.1 --port 17493
```

## API (Mentrix contract)

- `GET /health` — `{ brand, backend: "native", models_ready, synth }`
- `GET/POST /profiles`, `DELETE /profiles/{id}`
- `POST /profiles/{id}/samples` (multipart + `reference_text`)
- `POST /generate` → `{ audio_path: "/audio/..." }` (synchronous)
- `GET /audio/{filename}`

Mentrix may send `engine: "qwen"`; ZECT maps generate to the native synthesizer (`chatterbox` or `stub`).

## Env

| Variable | Default | Meaning |
|----------|---------|---------|
| `ZECT_VOICEBOX_SYNTH` | `auto` | `auto` / `chatterbox` / `stub` |
| `ZECT_VOICEBOX_ALLOW_STUB` | `1` | Allow stub WAV when ML missing |
| `ZECT_VOICEBOX_DATA_DIR` | `./data` | Profiles + audio |
| `ZECT_VOICEBOX_MODEL_DIR` | `./data/models` | HF / model cache |

## Tests

```powershell
cd services/zect-voicebox
pytest tests/test_api.py -q
```

## Honest limits

- Stub synth proves the Mentrix pipeline; install `requirements-ml.txt` for real zero-shot clone timbre.
- First ML download is large and needs disk/RAM (GPU optional, CPU slower).
- LiveKit Agents is a different stack — not used here.
- See `NOTICE` for MIT attribution of adapted open server patterns.
