# ZECT — Engineering Delivery Control Tower

A fullstack AI-governed engineering productivity platform for Zinnia that provides real GitHub integration, PR diff viewing, CI status monitoring, and multi-repo orchestration. Built using the [Zinnia Engineering Foundation (ZEF)](https://github.com/KarthikKaruppasamy880/ZEF) as the standards backbone.

## Overview

ZECT connects to the GitHub API to show real repository data, pull request diffs, commit history, and CI/CD status — providing engineering teams with a unified control tower for delivery management.

### Key Features

- **Real GitHub Integration** — Live repository data, pull requests with file-by-file diffs, commit history, and CI/CD workflow status
- **PR Diff Viewer** — View code changes with unified diff display, line numbers, additions/deletions, and file-level summaries
- **Multi-Repo Orchestration** — Monitor all repositories across projects with real-time GitHub data
- **Project Management** — CRUD projects linked to GitHub repositories with 5-stage delivery pipeline tracking
- **Analytics Dashboard** — Project metrics, stage distribution charts, team performance, and token savings
- **Platform Settings** — Feature toggles and configuration options with persistent storage
- **Workflow Stage Guides** — Detailed explanation pages for each delivery stage (Ask, Plan, Build, Review, Deploy)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (Python) + SQLAlchemy + SQLite |
| **Frontend** | React 18 + TypeScript + Vite + Tailwind CSS |
| **GitHub API** | PyGithub — repos, PRs, diffs, commits, CI workflows |
| **Charts** | Recharts |
| **Icons** | Lucide React |

## Getting Started

### Prerequisites

- Python 3.12+ with Poetry
- Node.js 18+ with npm
- GitHub personal access token (optional — enables private repo access and higher rate limits)

### Backend Setup

```bash
cd backend

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env to add your GITHUB_TOKEN (optional)

# Start development server
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend runs at http://localhost:8000. API docs at http://localhost:8000/docs.

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000

# Start development server
npm run dev

# Quality checks
npm run lint          # ESLint — 0 errors
npx tsc --noEmit      # TypeScript — 0 errors
npm run build         # Production build — success
```

Frontend runs at http://localhost:5173.

## Project Structure

```
ZECT/
├── backend/                       # FastAPI backend
│   ├── app/
│   │   ├── main.py                # FastAPI app, CORS, startup seed
│   │   ├── database.py            # SQLAlchemy + SQLite setup
│   │   ├── models.py              # Project, Repo, Setting models
│   │   ├── schemas.py             # Pydantic request/response schemas
│   │   ├── github_service.py      # GitHub API integration (PyGithub)
│   │   └── routers/
│   │       ├── projects.py        # Project CRUD endpoints
│   │       ├── github.py          # GitHub API proxy endpoints
│   │       ├── settings.py        # Settings CRUD with defaults
│   │       └── analytics.py       # Analytics overview endpoint
│   ├── pyproject.toml             # Poetry dependencies
│   └── .env.example               # Environment template
├── frontend/                      # React + Vite frontend
│   ├── src/
│   │   ├── App.tsx                # Router with 10 routes
│   │   ├── lib/api.ts             # API client (typed fetch wrapper)
│   │   ├── types/index.ts         # TypeScript interfaces
│   │   ├── components/
│   │   │   ├── Layout.tsx         # Sidebar + content layout
│   │   │   ├── Sidebar.tsx        # Dark sidebar navigation
│   │   │   └── DiffViewer.tsx     # PR diff viewer with line numbers
│   │   └── pages/
│   │       ├── Dashboard.tsx      # Metrics, project cards, stage chart
│   │       ├── Projects.tsx       # Filterable project list
│   │       ├── ProjectDetail.tsx  # Project detail with PRs, commits, CI
│   │       ├── PRViewer.tsx       # PR diff viewer (file-by-file)
│   │       ├── CreateProject.tsx  # Create project with repo linking
│   │       ├── Analytics.tsx      # Charts and project breakdown
│   │       ├── Settings.tsx       # Toggle and select settings
│   │       ├── Orchestration.tsx  # Multi-repo orchestration view
│   │       ├── Docs.tsx           # Documentation hub
│   │       └── StagePage.tsx      # Workflow stage guide
│   ├── package.json
│   └── .env.example               # Frontend env template
├── docs/                          # Additional documentation
└── README.md
```

## API Endpoints

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all projects (optional `?status=` filter) |
| POST | `/api/projects` | Create project with optional repo links |
| GET | `/api/projects/{id}` | Get project with linked repos |
| PUT | `/api/projects/{id}` | Update project fields |
| DELETE | `/api/projects/{id}` | Delete project and repos |

### GitHub Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/github/repos/{owner}` | List repositories for owner/org |
| GET | `/api/github/repos/{owner}/{repo}` | Get repository details |
| GET | `/api/github/repos/{owner}/{repo}/pulls` | List pull requests |
| GET | `/api/github/repos/{owner}/{repo}/pulls/{number}` | Get PR details |
| GET | `/api/github/repos/{owner}/{repo}/pulls/{number}/files` | Get PR file diffs |
| GET | `/api/github/repos/{owner}/{repo}/commits` | List recent commits |
| GET | `/api/github/repos/{owner}/{repo}/actions/runs` | List CI/CD workflow runs |

### Settings & Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | List all settings (auto-seeds defaults) |
| PUT | `/api/settings/{key}` | Update setting value |
| GET | `/api/analytics/overview` | Aggregated project analytics |

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Executive overview with metrics, project cards, stage chart |
| Projects | `/projects` | Filterable project list with status badges |
| Create Project | `/projects/new` | Create project with GitHub repo linking |
| Project Detail | `/projects/:id` | PRs, commits, CI status for linked repos |
| PR Diff Viewer | `/projects/:id/pr/:owner/:repo/:number` | File-by-file diff with line numbers |
| Analytics | `/analytics` | Bar/pie charts, team performance, project table |
| Settings | `/settings` | Feature toggles and configuration options |
| Orchestration | `/orchestration` | Multi-repo dashboard with GitHub data |
| Docs Center | `/docs` | Engineering documentation links |
| Stage Guide | `/stages/:stage` | Workflow stage details, activities, gates |

## Quality

```
Frontend Lint:      0 errors
Frontend TypeCheck: 0 errors
Frontend Build:     Compiled successfully (2125 modules)
Backend:            All endpoints tested and passing
```

## ZEF Integration

This project uses [ZEF (Zinnia Engineering Foundation)](https://github.com/KarthikKaruppasamy880/ZEF) for:
- Workflow standards (5-phase delivery model)
- Playbook-driven development patterns
- Context management across AI sessions
- Prompt templates for repo analysis and enhancement

## License

Internal use only — Zinnia.
