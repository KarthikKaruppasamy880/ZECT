# Backend sidecar slot (packaging)

Place a bundled API binary or launcher here before claiming packaging **PASS**:

- `zect-api.exe` — preferred Windows sidecar entrypoint
- `run-api.ps1` — alternate managed launcher
- `uvicorn.exe` — optional embedded runner

Until one of these files exists, `desktop_readiness` and `service-lifecycle` report `backend_bundled: false` and packaging status **PARTIAL**.

Do not commit secrets or a full Python venv into this folder.
