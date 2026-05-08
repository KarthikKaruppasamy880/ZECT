# ZECT App — Setup, Testing & Architecture Summary

## Overview
ZECT (Zinnia Engineering Control Tower) is a full-stack AI-assisted engineering tool with a FastAPI backend and React/TypeScript frontend.

## Repository
- **Repo**: KarthikKaruppasamy880/ZECT
- **Branches**: `develop` (active development), `main` (production sync)
- **Backend**: `/backend` — Python/FastAPI, SQLite (default), PostgreSQL (production)
- **Frontend**: `/frontend` — React 18 + TypeScript + Vite + TailwindCSS + shadcn/ui

## Quick Start

### Backend
```bash
cd backend
cp .env.example .env   # Edit with your DB URL, API keys, credentials
pip install -e ".[test]"
uvicorn app.main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8001 npx vite --host 0.0.0.0 --port 5173
```

### Login
- URL: `http://localhost:5173`
- Credentials: Set `ZECT_USERNAME` and `ZECT_PASSWORD` in `backend/.env`

## Architecture

### Backend Stack
- **Framework**: FastAPI with automatic OpenAPI docs at `/docs`
- **Database**: SQLAlchemy ORM, SQLite (dev) or PostgreSQL (prod)
- **Auth**: Simple username/password login (JWT tokens)
- **LLM Integration**: Anthropic Claude via direct API (configurable in Settings)
- **Encryption**: Fernet encryption for secrets manager

### Frontend Stack
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS + shadcn/ui components
- **Routing**: React Router v6
- **State**: React hooks + context

### Key Backend Routers
| Router | Path | Purpose |
|--------|------|---------|
| conversations | `/api/conversations` | Chat history for Ask/Plan/Build |
| knowledge_base | `/api/knowledge` | Knowledge articles CRUD |
| playbooks | `/api/playbooks` | Automation playbooks CRUD |
| scheduler | `/api/schedules` | Cron-based task scheduling |
| secrets_manager | `/api/secrets` | Encrypted secrets vault |
| code_index | `/api/code-index` | Code symbol search & indexing |
| session_insights | `/api/session-insights` | Usage analytics & metrics |
| app_runner | `/api/app-runner` | Process management & live preview |

### Frontend Pages (17 sidebar items)
1. **Dashboard** (`/`) — Overview stats, projects, token usage
2. **Ask Mode** (`/ask`) — AI Q&A with file attachments
3. **Plan Mode** (`/plan`) — AI-assisted planning with model selection
4. **Build Phase** (`/build`) — Code generation with templates
5. **Code Review** (`/code-review`) — PR review, snippet analysis, repo scanning
6. **Knowledge Base** (`/knowledge-base`) — Searchable knowledge articles
7. **Playbooks** (`/playbooks`) — Reusable automation workflows
8. **Scheduled Tasks** (`/scheduled-tasks`) — Cron job management
9. **Secrets Manager** (`/secrets`) — Encrypted credential storage
10. **Code Index** (`/code-index`) — Codebase symbol search
11. **Session Insights** (`/session-insights`) — Usage analytics
12. **Conversations** (`/conversations`) — Full chat history
13. **Settings** (`/settings`) — API keys, toggles, model config
14. **App Runner** (`/app-runner`) — Run apps with live preview
15. **Token Controls** (`/token-controls`) — Per-user token limits & monitoring
16. **Docs Center** (`/docs`) — In-app documentation & management guide
17. **Import/Export** (`/import-export`) — Data portability

## Database Models
- `Conversation` — mode, messages (JSON), model, tokens, files
- `KnowledgeArticle` — title, content, category, tags
- `Playbook` — name, description, steps (JSON), category
- `ScheduledTask` — name, cron expression, command, enabled
- `Secret` — name, encrypted_value, scope, description
- `CodeSymbol` — name, type, file_path, language, line numbers
- `SessionEvent` — event_type, event_metadata, session_id, timestamps

## Environment Variables (backend/.env)
```env
DATABASE_URL=sqlite:///./zect.db
GITHUB_TOKEN=ghp_...
ZECT_USERNAME=user@example.com
ZECT_PASSWORD=YourPassword
ANTHROPIC_API_KEY=sk-ant-...       # Optional, for AI features
OPENAI_API_KEY=sk-...              # Optional, alternative LLM
FERNET_KEY=...                     # Auto-generated for secrets encryption
```

## Deployment Options
1. **Local Development** — SQLite + Vite dev server
2. **Docker Compose** — See `docker-compose.yml` in repo root
3. **AWS EC2** — PostgreSQL + Nginx reverse proxy + systemd
4. **Ollama** — Local LLM support (no cloud API needed)

## Testing
- Backend: `pytest` with `.[test]` extras
- Frontend: Vite dev server with hot reload
- E2E: Manual testing via browser (see playbook)

## Key Documents in Repo
- `docs/ZECT_MANAGEMENT_GUIDE_v2.md` — Full feature workflow guide
- `docs/reports/ZECT-Full-E2E-Test-Report-v2.md` — Latest E2E test results
- `docs/guides/` — Deployment guides, LLM setup, Docker config
- `.devin/playbooks/` — Devin automation playbooks
- `.devin/knowledge/` — Devin knowledge notes (this file)
