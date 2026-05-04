# ZECT Local Configuration Guide

> Complete guide to setting up and running ZECT on your local machine.

---

## Prerequisites

| Tool | Minimum Version | Check Command |
|------|----------------|---------------|
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Python | 3.11+ | `python3 --version` |
| Poetry | 1.5+ | `poetry --version` |
| Git | 2.30+ | `git --version` |

---

## Quick Start (5 Minutes)

```bash
# 1. Clone the repository
git clone https://github.com/KarthikKaruppasamy880/ZECT.git
cd ZECT

# 2. Backend setup
cd backend
cp .env.example .env
# Edit .env with your credentials (see Environment Variables below)
poetry install
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Environment Variables

### Backend (`backend/.env`)

```env
# ─── Authentication (REQUIRED) ───────────────────────────────────
# Login credentials for the ZECT web UI
ZECT_USERNAME=admin
ZECT_PASSWORD=changeme

# ─── GitHub API (OPTIONAL) ───────────────────────────────────────
# Personal Access Token for repo analysis
# Without this: 60 requests/hour (unauthenticated)
# With this: 5,000 requests/hour
# Create at: https://github.com/settings/tokens/new?scopes=repo
GITHUB_TOKEN=

# ─── OpenAI API (OPTIONAL) ───────────────────────────────────────
# Required for: Ask Mode, Plan Mode, Blueprint Enhancement
# Get your key at: https://platform.openai.com/api-keys
OPENAI_API_KEY=

# ─── Database (OPTIONAL) ─────────────────────────────────────────
# Default: SQLite file at ./zect.db
# For PostgreSQL: postgresql://user:pass@localhost:5432/zect
DATABASE_URL=sqlite:///./zect.db
```

### Frontend (`frontend/.env` or `frontend/.env.local`)

```env
# Backend API URL (default: http://localhost:8000)
# Change this if your backend runs on a different port or host
VITE_API_URL=http://localhost:8000
```

---

## Detailed Setup

### Backend

```bash
cd backend

# Install dependencies with Poetry
poetry install

# Create environment file
cp .env.example .env

# Edit with your favorite editor
nano .env   # or vim, code, etc.

# Start the development server (auto-reload on file changes)
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**What happens on startup:**
1. SQLite database created at `./zect.db` (if it doesn't exist)
2. Database tables created: `projects`, `repos`, `settings`, `token_logs`
3. 6 demo projects seeded (only if the `projects` table is empty)
4. 10 default settings seeded (only if the `settings` table is empty)
5. API available at `http://localhost:8000`
6. API docs (Swagger) at `http://localhost:8000/docs`
7. Health check at `http://localhost:8000/healthz`

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server (hot-reload)
npm run dev
# -> http://localhost:5173

# Build for production
npm run build
# -> Output in dist/

# Preview production build
npm run preview

# Run linting
npm run lint

# Type checking
npx tsc --noEmit
```

---

## Database

### SQLite (Default)

- **Location:** `backend/zect.db`
- **Auto-created:** Yes, on first startup
- **Migrations:** Not required — tables are created via `Base.metadata.create_all()`
- **Reset:** Delete `zect.db` and restart the backend

### Tables

| Table | Purpose |
|-------|---------|
| `projects` | Engineering projects with stage, completion, team info |
| `repos` | GitHub repos linked to projects |
| `settings` | Feature toggles and configuration options |
| `token_logs` | Audit log of all token-consuming operations |

### PostgreSQL (Optional)

To use PostgreSQL instead of SQLite:

```bash
# Install PostgreSQL
sudo apt install postgresql

# Create database
sudo -u postgres createdb zect
sudo -u postgres createuser zectuser -P

# Update .env
DATABASE_URL=postgresql://zectuser:yourpassword@localhost:5432/zect
```

Install the PostgreSQL driver:
```bash
cd backend
poetry add psycopg2-binary
```

---

## API Keys Configuration

### GitHub Token

Required for: Repo Analysis, Blueprint Generation, Doc Generation, PR Viewer, Orchestration.

**Create a token:**
1. Go to https://github.com/settings/tokens/new
2. Select scopes: `repo` (read access)
3. Click "Generate token"
4. Copy the `ghp_...` token

**Configure in ZECT (two options):**

1. **Environment variable:** Add `GITHUB_TOKEN=ghp_...` to `backend/.env`
2. **Runtime via UI:** Go to Settings -> GitHub API Key -> Configure -> Paste token -> Save

### OpenAI API Key

Required for: Ask Mode, Plan Mode, Blueprint Enhancement.

**Get a key:**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the `sk-...` key

**Configure in ZECT (two options):**

1. **Environment variable:** Add `OPENAI_API_KEY=sk-...` to `backend/.env`
2. **Runtime via UI:** Go to Settings -> OpenAI API Key -> Configure -> Paste key -> Save

---

## Running Both Servers

### Option 1: Two Terminal Windows

```bash
# Terminal 1 - Backend
cd ZECT/backend
poetry run uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd ZECT/frontend
npm run dev
```

### Option 2: Using a Process Manager

Create a `Procfile`:
```
backend: cd backend && poetry run uvicorn app.main:app --reload --port 8000
frontend: cd frontend && npm run dev
```

Run with `foreman` or `honcho`:
```bash
pip install honcho
honcho start
```

---

## Troubleshooting

### "Module not found" errors in backend
```bash
cd backend
poetry install  # Re-install all dependencies
```

### "CORS error" in browser console
Ensure the backend is running on port 8000 and the frontend's `VITE_API_URL` points to `http://localhost:8000`.

### "Invalid credentials" on login
Check that `ZECT_USERNAME` and `ZECT_PASSWORD` are set in `backend/.env`. If they are empty, login is disabled.

### Port already in use
```bash
# Find and kill the process using the port
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:5173 | xargs kill -9  # Frontend
```

### Database reset
```bash
# Delete the SQLite database
rm backend/zect.db
# Restart the backend — it will recreate the DB and seed demo data
```

### GitHub API rate limit exceeded
Configure a GitHub token in Settings or set `GITHUB_TOKEN` in `.env`. Unauthenticated requests are limited to 60/hour; authenticated requests get 5,000/hour.

### OpenAI API errors
1. Check your API key is valid at https://platform.openai.com/api-keys
2. Check your OpenAI account has credits
3. Verify the key starts with `sk-`

---

## Development Tips

### Backend API Documentation
Visit `http://localhost:8000/docs` for interactive Swagger UI with all endpoints documented.

### Hot Reload
- **Backend:** `--reload` flag on uvicorn watches for Python file changes
- **Frontend:** Vite's HMR (Hot Module Replacement) updates the browser instantly on file changes

### Code Quality
```bash
# Frontend linting
cd frontend && npm run lint

# Frontend type checking
cd frontend && npx tsc --noEmit

# Backend — run with Python linters
cd backend && poetry run ruff check .
```

### File Structure
```
ZECT/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, startup, seeding
│   │   ├── database.py          # SQLAlchemy engine, session
│   │   ├── models.py            # DB models (Project, Repo, Setting, TokenLog)
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── github_service.py    # GitHub API wrapper
│   │   ├── token_tracker.py     # Token usage persistence
│   │   └── routers/
│   │       ├── projects.py      # CRUD for projects
│   │       ├── github.py        # GitHub API proxy
│   │       ├── settings.py      # Feature toggles, config
│   │       ├── analytics.py     # Dashboard analytics + token dashboard
│   │       ├── repo_analysis.py # Repo analysis, blueprint, docs gen
│   │       ├── llm.py           # Ask/Plan/Blueprint AI (OpenAI)
│   │       └── auth.py          # Login/logout/verify
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Router setup
│   │   ├── lib/api.ts           # API client functions
│   │   ├── types/index.ts       # TypeScript interfaces
│   │   ├── components/
│   │   │   └── Sidebar.tsx      # Navigation sidebar
│   │   └── pages/               # All 16 pages
│   ├── package.json
│   └── vite.config.ts
└── docs/                        # Documentation files
```
