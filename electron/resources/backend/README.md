# Backend sidecar (packaging)

Committed:

- `run-api.ps1` — managed launcher (requires `-UserData`)
- `zect_api_entry.py` — production uvicorn entry (no reload)

Produced at installer build (`python backend/packaging/bundle_sidecar.py`), gitignored:

- `python-runtime/` — venv with pinned `requirements.txt`
- `src/` — copy of `backend/` without `.env` / tests / data
- `zect-api.exe` — optional frozen binary

Do not commit secrets, `.env`, or a full venv.
