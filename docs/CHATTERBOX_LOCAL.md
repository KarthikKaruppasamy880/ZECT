# ZECT Voicebox (local Mentrix Chatterbox engine)

Native clone TTS for Mentrix Companion Voice / Present.

```powershell
powershell -File services/zect-voicebox/scripts/up.ps1
```

That starts **ZECT Voicebox** on `:17493`. See [`ZECT_VOICEBOX.md`](ZECT_VOICEBOX.md).

```env
CHATTERBOX_BASE_URL=http://127.0.0.1:17493
CHATTERBOX_SPEAK_TIMEOUT=120
```

Prefer `127.0.0.1` over `localhost` on Windows.

Without ML deps, stub synth still returns WAV so Test speak can complete; install `services/zect-voicebox/requirements-ml.txt` for real clone quality.
