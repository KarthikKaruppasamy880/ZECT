# ZECT — Docker One-Command Setup Guide

Run the entire ZECT stack (Backend + Frontend + PostgreSQL) with a single command. No Node.js, Python, or PostgreSQL installation required — just Docker.

## Prerequisites

- **Docker Desktop** installed ([Download](https://www.docker.com/products/docker-desktop/))
- **Git** installed

## Quick Start (One Command)

```bash
# 1. Clone the repo
git clone https://github.com/KarthikKaruppasamy880/ZECT.git
cd ZECT

# 2. Create your .env file (copy and edit)
cp .env.example .env
# Edit .env with your API keys (see Configuration below)

# 3. Run everything
docker compose up --build
```

**That's it!** Open http://localhost:5173 in your browser.

## What Runs

| Service | Port | Description |
|---------|------|-------------|
| **Frontend** | http://localhost:5173 | React dashboard (Vite + Tailwind) |
| **Backend** | http://localhost:8000 | FastAPI REST API (130+ endpoints) |
| **PostgreSQL** | localhost:5432 | Database (auto-created, persistent) |

## Configuration (.env file)

Create a `.env` file in the project root:

```env
# Required — Login credentials
ZECT_USERNAME=karthik.karuppasamy@Zinnia.com
ZECT_PASSWORD=YourPassword123

# Optional — GitHub integration (for repo analysis, PR review)
GITHUB_TOKEN=ghp_your-github-token

# Optional — AI features (code generation, review, planning)
OPENAI_API_KEY=sk-your-openai-key

# Optional — Free AI models via OpenRouter
OPENROUTER_API_KEY=sk-or-your-key

# Optional — Jira integration
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-token

# Optional — Slack notifications
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
```

## Commands

```bash
# Start all services
docker compose up --build

# Start in background (detached)
docker compose up -d --build

# View logs
docker compose logs -f

# View logs for one service
docker compose logs -f backend

# Stop all services
docker compose down

# Stop and remove all data (database reset)
docker compose down -v

# Rebuild after code changes
docker compose up --build
```

## Without Docker (Manual Setup)

If you prefer running without Docker:

### Backend
```bash
cd backend
pip install -e ".[test]"
cp .env.example .env   # edit with your keys
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Database
- **SQLite (default)**: No setup needed — auto-creates `zect.db`
- **PostgreSQL**: Set `DATABASE_URL=postgresql://postgres:password@localhost:5432/zect_db` in `backend/.env`

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                  │     │                  │     │                  │
│   Frontend       │────▶│   Backend        │────▶│  PostgreSQL      │
│   React + Vite   │     │   FastAPI        │     │  (or SQLite)     │
│   Port 5173      │     │   Port 8000      │     │  Port 5432       │
│                  │     │                  │     │                  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        │                       ├──▶ OpenAI API (code gen, review)
        │                       ├──▶ GitHub API (repo analysis)
        │                       ├──▶ Jira API (ticket management)
        │                       └──▶ Slack API (notifications)
        │
        └──▶ Browser (http://localhost:5173)
```

## Sidebar Pages

| Page | What It Does |
|------|-------------|
| **Dashboard** | Overview — projects, token usage, risk alerts |
| **Ask Mode** | Ask AI questions about code, architecture, best practices |
| **Plan Mode** | Generate project plans with AI |
| **Build Phase** | Generate code from plans with file attachments |
| **Review Phase** | AI code review with severity ratings |
| **Deploy Phase** | Deployment checklists and runbooks |
| **Code Review** | Full AI-powered PR review engine |
| **Skill Library** | Save/reuse AI skill templates (global or per-repo) |
| **Token Controls** | Monitor token usage, set budgets, per-user tracking |
| **Audit Trail** | Full audit log of all operations |
| **Rules Engine** | Custom rules for code quality gates |
| **Output History** | Browse all generated code/plans/reviews |
| **Export/Share** | Export to PDF/Markdown |
| **Integrations** | Configure Jira, Slack, GitHub connections |
| **Settings** | App configuration |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 8000 already in use | `docker compose down` then retry, or change port in docker-compose.yml |
| Port 5173 already in use | Same as above |
| Database connection refused | Wait 10 seconds for PostgreSQL to start, or check `docker compose logs db` |
| OpenAI errors | Add `OPENAI_API_KEY` to `.env` — AI features need this |
| GitHub 401 errors | Add `GITHUB_TOKEN` to `.env` with `repo` scope |
| Frontend blank page | Clear browser cache, or check `docker compose logs frontend` |
