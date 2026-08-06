# ZECT Voicebox

Mentrix-compatible clone TTS HTTP engine (product brand: **ZECT Voicebox** / Chatterbox client).

See [`docs/ZECT_VOICEBOX.md`](../../docs/ZECT_VOICEBOX.md).

```powershell
# Unit tests
pytest tests/test_api.py -q

# Local (no Docker) — Mentrix online when this answers /profiles
$env:ZECT_VOICEBOX_UPSTREAM_URL = "http://127.0.0.1:17494"
python -m uvicorn app.main:app --host 127.0.0.1 --port 17493

# Full stack (Docker Desktop / Rancher)
powershell -File scripts/up.ps1
```
