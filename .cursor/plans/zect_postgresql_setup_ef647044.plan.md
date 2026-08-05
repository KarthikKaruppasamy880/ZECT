---
name: ZECT PostgreSQL setup
overview: Create a local `zect_db` database, point ZECT’s backend at it with a SQLAlchemy URL that matches the installed **psycopg v3** driver, then start the API so `init_db()` and startup seeding run. Adjust the user’s `DATABASE_URL` line accordingly.
todos:
  - id: create-db
    content: Run CREATE DATABASE zect_db; verify connection (psql \c or pgAdmin)
    status: completed
  - id: env-url
    content: Set backend/.env DATABASE_URL to postgresql+psycopg://user:pass@localhost:5432/zect_db
    status: completed
  - id: run-backend
    content: poetry install; poetry run uvicorn from backend with reload
    status: completed
  - id: verify
    content: Healthz, table counts, GET /api/settings for 10 settings rows
    status: completed
isProject: false
---

# ZECT local PostgreSQL setup (Windows)

## What the app actually does (verified in code)

- **Table creation:** `[backend/app/database.py](c:\Users\karuppk\Downloads\ZECT\backend\app\database.py)` `init_db()` calls `Base.metadata.create_all(bind=engine)`. Models in `[backend/app/models.py](c:\Users\karuppk\Downloads\ZECT\backend\app\models.py)` map to: `**projects**`, `**repos**`, `**settings**`, `**token_logs**` (matches your list; column sets align with the models).
- **Demo data on first run:** `[backend/app/main.py](c:\Users\karuppk\Downloads\ZECT\backend\app\main.py)` `on_startup` runs `init_db()` then `seed_demo_projects()`. That seeds **6 projects** and **2 `repos` rows** (only the first two projects have GitHub-style repo links). The other four projects have **no** linked repos in the seed.
- **10 settings:** Not created at server startup. `[backend/app/routers/settings.py](c:\Users\karuppk\Downloads\ZECT\backend\app\routers\settings.py)` calls `seed_settings()` on the **first** `GET /api/settings` when the `settings` table is empty, inserting **10** `DEFAULT_SETTINGS` rows. So: “10 settings on first start” is true after the UI (or any client) hits the settings list once, not necessarily the moment the process starts.

## 1. Create the database (SQL / psql)

**Option A – `psql` (command line, typical on Windows with PostgreSQL):**

```sql
CREATE DATABASE zect_db;
```

Then connect and verify (your step 2):

- In **psql**: `\c zect_db` then e.g. `\conninfo` or `SELECT current_database();`
- In **pgAdmin**: connect to the server, create DB `zect_db`, or refresh and open it.

Note: `\c zect_db` is a **psql** meta-command; it is not valid in generic “SQL only” windows—use it inside `psql` or use pgAdmin’s Connect.

## 2. Critical: `DATABASE_URL` must use **psycopg v3**

`[backend/pyproject.toml](c:\Users\karuppk\Downloads\ZECT\backend\pyproject.toml)` declares `**psycopg` v3** (`psycopg[binary]`), not `psycopg2`. A bare URL like:

`postgresql://postgres:newpwd@localhost:5432/zect_db`

often makes SQLAlchemy look for **psycopg2**, which is **not** in this project and can fail at import/connect time.

**Recommended URL for this codebase:**

```env
DATABASE_URL=postgresql+psycopg://postgres:newpwd@localhost:5432/zect_db
```

Replace `newpwd` with the real password for the `postgres` role (or change user/password to match your local cluster). If the password contains `@`, `#`, etc., URL-encode it in the connection string.

Keep other keys as needed (e.g. `OPENAI_API_KEY`, `GITHUB_TOKEN`) in the same file—see `[backend/.env.example](c:\Users\karuppk\Downloads\ZECT\backend\.env.example)`.

## 3. Update `[backend/.env](c:\Users\karuppk\Downloads\ZECT\backend\.env)`

- Set `**DATABASE_URL**` to the `**postgresql+psycopg://...**` form above (not only `postgresql://...` unless you separately add `psycopg2-binary` and intend to use it).
- Ensure no conflicting old SQLite default if you previously used SQLite only.

## 4. Ensure PostgreSQL accepts the connection

- Service running, port **5432** (or change host/port in the URL).
- Role `**postgres**` password matches what you put in the URL (or use another role with `CREATEDB`/connect rights and update the URL).

## 5. Install deps and start the backend

From repo `**backend**` folder:

```powershell
cd c:\Users\karuppk\Downloads\ZECT\backend
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 6. Smoke checks

- `GET http://localhost:8000/healthz` returns `{"status":"ok"}`.
- In PostgreSQL, `\dt` (psql) or pgAdmin: confirm `**projects**`, `**repos**`, `**settings**`, `**token_logs**` exist.
- Confirm **6** rows in `**projects**`, **2** in `**repos**` after first startup.
- Open the app or call `**GET /api/settings**` once; confirm **10** rows in `**settings**`.

## Summary diagram

```mermaid
flowchart LR
  subgraph win [Windows]
    PG[(PostgreSQL zect_db)]
  end
  subgraph zect [ZECT backend]
    ENV[backend/.env DATABASE_URL]
    UV[uvicorn app.main:app]
    DB layer[SQLAlchemy engine]
    INIT[init_db create_all]
    SEED[seed_demo_projects]
  end
  ENV --> DB layer
  UV --> INIT
  INIT --> PG
  SEED --> PG
```



## Risks / edge cases

- Wrong driver URL (`postgresql://` without **psycopg** dialect) → connection or dialect errors.
- Existing SQLite `zect.db` ignored once `DATABASE_URL` points to Postgres; data does not migrate automatically.
- If `projects` already has rows from an earlier run, **startup seed skips** adding demo projects (`count() > 0` guard in `seed_demo_projects()`).

