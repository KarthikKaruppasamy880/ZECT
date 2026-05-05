# ZECT — Local Setup & Configuration Guide

## Overview

ZECT (Zinnia Engineering Control Tower) is a fullstack AI-governed engineering productivity platform. This guide covers how to set up and run both the frontend and backend locally on your machine.

---

## Prerequisites

| Tool | Version | Check Command |
|------|---------|---------------|
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Python | 3.10+ | `python --version` |
| pip | 22+ | `pip --version` |
| Git | 2.30+ | `git --version` |
| PostgreSQL | 14+ (optional) | `psql --version` |

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/KarthikKaruppasamy880/ZECT.git
cd ZECT
git checkout develop
```

---

## Step 2: Backend Setup

### 2.1 Create Python Virtual Environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2.2 Install Dependencies

```bash
pip install fastapi uvicorn sqlalchemy python-dotenv pydantic aiofiles python-multipart PyGithub openai psycopg2-binary
```

### 2.3 Configure Environment Variables

Create a `.env` file in the `backend/` folder:

```bash
# backend/.env

# Required: OpenAI API Key (for AI features)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional: OpenRouter API Key (for free models like Llama, Mistral)
OPENROUTER_API_KEY=sk-or-your-openrouter-key-here

# Optional: GitHub Token (for repo analysis, orchestration)
GITHUB_TOKEN=ghp_your-github-token-here

# Database (default: SQLite, optional: PostgreSQL)
# For SQLite (default - no config needed):
# DATABASE_URL=sqlite:///./zect.db

# For PostgreSQL:
# DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/zect_db
```

### 2.4 Database Setup

**Option A: SQLite (Default — Zero Configuration)**
- The database file (`zect.db`) is auto-created on first startup
- No additional setup required

**Option B: PostgreSQL (Recommended for Production)**

1. Open pgAdmin or psql and create the database:
```sql
CREATE DATABASE zect_db;
```

2. Update `backend/.env`:
```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/zect_db
```

3. Tables are auto-created on first startup via SQLAlchemy `create_all()`

### 2.5 Start the Backend Server

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify it's running:
```bash
curl http://localhost:8000/healthz
# Expected: {"status":"ok"}
```

---

## Step 3: Frontend Setup

### 3.1 Install Dependencies

```bash
cd frontend
npm install
```

### 3.2 Configure API URL (Optional)

By default, the frontend connects to `http://localhost:8000`. To change this, create a `.env` file in `frontend/`:

```bash
# frontend/.env (optional)
VITE_API_URL=http://localhost:8000
```

### 3.3 Start the Frontend Dev Server

```bash
npm run dev
```

The app will be available at: **http://localhost:5173**

---

## Step 4: Login

Use these default credentials:
- **Email:** `karthik.karuppasamy@Zinnia.com`
- **Password:** `Karthik@1234`

---

## Step 5: Verify Everything Works

1. Open http://localhost:5173 in your browser
2. Log in with the credentials above
3. You should see the Dashboard with 6 demo projects
4. Navigate through all sidebar sections to verify they load

---

## API Endpoints Summary

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| Health | `/healthz` | GET | Server status |
| Auth | `/api/auth/login` | POST | Login |
| Projects | `/api/projects` | GET | List projects |
| Settings | `/api/settings` | GET | App settings |
| Analytics | `/api/analytics/overview` | GET | Overview metrics |
| Token Dashboard | `/api/analytics/token-dashboard` | GET | Token usage |
| Token Usage | `/api/tokens/usage` | GET | Full token data |
| Token Budget | `/api/tokens/budget` | GET/PUT | Budget config |
| Token Models | `/api/tokens/models` | GET | Model breakdown |
| Token Users | `/api/tokens/users` | GET | User activity |
| Token Teams | `/api/tokens/teams` | GET | Team usage |
| Token Trends | `/api/tokens/trends` | GET | Usage trends |
| Models | `/api/models/` | GET | Available models |
| Models Status | `/api/models/status` | GET | Provider status |
| Models Chat | `/api/models/chat` | POST | Chat completion |
| LLM Ask | `/api/llm/ask` | POST | Ask question |
| LLM Plan | `/api/llm/plan` | POST | Generate plan |
| Build | `/api/build/generate` | POST | Generate code |
| Review | `/api/review/analyze` | POST | Analyze code |
| Deploy | `/api/deploy/checklist` | POST | Deploy checklist |
| Skills | `/api/skills` | GET/POST | Skill library |
| Orchestration | `/api/orchestration/repos` | GET | Repo status |
| GitHub | `/api/github/repos/{owner}` | GET | GitHub repos |

---

## Configuration Details

### LLM Models Available

| Model | Provider | Free | Quality |
|-------|----------|------|---------|
| GPT-4o Mini | OpenAI | No | High |
| GPT-4o | OpenAI | No | Best |
| GPT-3.5 Turbo | OpenAI | No | Good |
| Llama 3.1 8B | OpenRouter | Yes | Good |
| Mistral 7B | OpenRouter | Yes | Good |
| Gemma 2 9B | OpenRouter | Yes | Good |
| Qwen 2.5 7B | OpenRouter | Yes | Good |
| Claude 3.5 Sonnet | OpenRouter | No | Best |
| Claude 3 Haiku | OpenRouter | No | Good |

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes (for AI features) | OpenAI API key |
| `OPENROUTER_API_KEY` | Optional | For free models via OpenRouter |
| `GITHUB_TOKEN` | Optional | GitHub PAT for repo analysis |
| `DATABASE_URL` | Optional | PostgreSQL connection string |

---

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (need 3.10+)
- Install missing packages: `pip install fastapi uvicorn sqlalchemy python-dotenv pydantic aiofiles python-multipart PyGithub openai`
- Check port 8000 is free: `netstat -an | findstr 8000` (Windows) or `lsof -i :8000` (Mac/Linux)

### Frontend won't start
- Check Node version: `node --version` (need 18+)
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check port 5173 is free

### CORS errors
- Ensure backend is running on port 8000
- Ensure frontend `.env` has correct `VITE_API_URL`
- Backend CORS is configured to allow all origins by default

### Database errors
- Delete `backend/zect.db` and restart the server (auto-recreates)
- For PostgreSQL: verify `DATABASE_URL` is correct and the database exists

### AI features show "Not configured"
- Add `OPENAI_API_KEY` to `backend/.env`
- Restart the backend server after changing `.env`

---

## Database Schema

The database contains 10+ tables for multi-user, multi-project, multi-session architecture:

| Table | Purpose |
|-------|---------|
| `users` | User accounts (SSO-ready) |
| `projects` | Engineering projects |
| `repos` | GitHub repository connections |
| `settings` | App configuration |
| `user_sessions` | Per-user work sessions |
| `context_files` | Attached files/repos/snippets |
| `generated_outputs` | AI-generated outputs (audit) |
| `token_logs` | Every API call logged |
| `token_budgets` | Per-user/team budgets |
| `skills` | Reusable AI skill templates |

---

## Windows-Specific Notes

- Use `venv\Scripts\activate` (not `source venv/bin/activate`)
- Use `set OPENAI_API_KEY=sk-xxx` in CMD (not `export`)
- Or use PowerShell: `$env:OPENAI_API_KEY="sk-xxx"`
- If `psycopg2-binary` fails, install Visual C++ Build Tools or use `pip install psycopg2-binary --only-binary :all:`
