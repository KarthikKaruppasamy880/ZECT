# ZECT Voicebox

Native Mentrix Chatterbox engine on `127.0.0.1:17493`.

```powershell
pip install -r requirements.txt
$env:ZECT_VOICEBOX_ALLOW_STUB='1'
python -m uvicorn app.main:app --host 127.0.0.1 --port 17493
```

Optional ML: `pip install -r requirements-ml.txt`

Docker / Rancher: `powershell -File scripts/up.ps1` from repo root (see `docs/ZECT_VOICEBOX.md`).
