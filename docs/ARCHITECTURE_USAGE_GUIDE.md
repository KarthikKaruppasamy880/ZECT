# Architecture & Usage Guide

> Technical architecture overview and usage patterns for ZECT.

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                   │
│  React 18 + TypeScript + Tailwind CSS + Vite         │
│  Port: 5173 (dev) / static build (production)        │
├─────────────────────────────────────────────────────┤
│                         API                          │
│              HTTP REST (JSON over fetch)              │
├─────────────────────────────────────────────────────┤
│                  Backend (FastAPI)                    │
│  Python 3.11+ + SQLAlchemy + PyGithub                │
│  Port: 8000                                          │
├─────────────────────────────────────────────────────┤
│              Database (SQLite)                        │
│  Projects, Repos, Settings tables                    │
│  File: zect.db (local) or /data/app.db (deployed)    │
├─────────────────────────────────────────────────────┤
│              External: GitHub API                     │
│  Repos, PRs, Commits, Actions, File Trees            │
└─────────────────────────────────────────────────────┘
```

## Backend Architecture

### Directory Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, startup, seed data
│   ├── database.py           # SQLAlchemy engine, session, init_db
│   ├── models.py             # SQLAlchemy models (Project, Repo, Setting)
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── github_service.py     # PyGithub wrapper with rate limit backoff
│   └── routers/
│       ├── __init__.py
│       ├── projects.py       # CRUD for projects and repos
│       ├── github.py         # GitHub API proxy endpoints
│       ├── settings.py       # Feature toggles and config
│       ├── analytics.py      # Aggregated metrics
│       └── repo_analysis.py  # Repo analysis, blueprints, docs, API key
├── pyproject.toml            # Poetry dependencies
└── poetry.lock
```

### API Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Health check |
| GET | `/api/projects` | List all projects |
| POST | `/api/projects` | Create a project |
| GET | `/api/projects/{id}` | Get project detail |
| PUT | `/api/projects/{id}` | Update a project |
| DELETE | `/api/projects/{id}` | Delete a project |
| GET | `/api/settings` | List all settings |
| PUT | `/api/settings/{key}` | Update a setting |
| GET | `/api/analytics/overview` | Get analytics summary |
| GET | `/api/github/repos/{owner}` | List GitHub repos |
| GET | `/api/github/repos/{owner}/{repo}` | Get repo info |
| GET | `/api/github/repos/{owner}/{repo}/pulls` | List PRs |
| GET | `/api/github/repos/{owner}/{repo}/pulls/{n}` | Get PR detail |
| GET | `/api/github/repos/{owner}/{repo}/pulls/{n}/files` | Get PR files |
| GET | `/api/github/repos/{owner}/{repo}/commits` | List commits |
| GET | `/api/github/repos/{owner}/{repo}/actions/runs` | List CI runs |
| POST | `/api/analysis/repo` | Analyze single repo |
| POST | `/api/analysis/multi-repo` | Analyze multiple repos |
| POST | `/api/analysis/blueprint` | Generate blueprint prompt |
| POST | `/api/analysis/docs/generate` | Generate documentation |
| GET | `/api/analysis/tokens` | Get token usage log |
| POST | `/api/analysis/api-key` | Configure GitHub API key |
| GET | `/api/analysis/api-key/status` | Check API key status |

### Database Models

**Project**
- id, name, description, status, stage, team_lead, team_size, created_at, updated_at

**Repo**
- id, project_id (FK), owner, name, full_name

**Setting**
- id, key, value, label, description, setting_type, options

### GitHub Service

`github_service.py` wraps PyGithub with:
- Automatic rate limit detection and exponential backoff
- Configurable token via environment variable or runtime API
- Graceful error handling for all GitHub API calls

## Frontend Architecture

### Directory Structure

```
frontend/
├── src/
│   ├── main.tsx              # React entry point
│   ├── App.tsx               # Router with 14 routes
│   ├── components/
│   │   ├── Layout.tsx        # Shell with sidebar + content area
│   │   ├── Sidebar.tsx       # Navigation sidebar (10 nav + 5 stages)
│   │   └── DiffViewer.tsx    # PR file diff viewer
│   ├── pages/
│   │   ├── Dashboard.tsx     # Home — metrics, projects, activity
│   │   ├── Projects.tsx      # Project list
│   │   ├── ProjectDetail.tsx # Single project with repos, PRs, CI
│   │   ├── CreateProject.tsx # New project wizard
│   │   ├── PRViewer.tsx      # PR detail with diffs
│   │   ├── Analytics.tsx     # Charts and metrics
│   │   ├── Settings.tsx      # Config + API key modal + token counter
│   │   ├── Orchestration.tsx # Multi-repo overview
│   │   ├── RepoAnalysis.tsx  # Single + multi repo analysis
│   │   ├── BlueprintGenerator.tsx # AI prompt generation
│   │   ├── DocGenerator.tsx  # Granular documentation
│   │   ├── Docs.tsx          # Docs center
│   │   └── StagePage.tsx     # Workflow stage detail
│   ├── lib/
│   │   └── api.ts            # API client (fetch wrapper)
│   └── types/
│       └── index.ts          # TypeScript interfaces
├── .env                      # VITE_API_URL
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── vite.config.ts
```

### Routes

| Path | Page | Description |
|------|------|-------------|
| `/` | Dashboard | Home screen |
| `/projects` | Projects | Project list |
| `/projects/new` | CreateProject | New project form |
| `/projects/:id` | ProjectDetail | Project detail |
| `/projects/:id/pr/:owner/:repo/:number` | PRViewer | PR viewer |
| `/analytics` | Analytics | Metrics dashboard |
| `/settings` | Settings | Configuration |
| `/orchestration` | Orchestration | Multi-repo view |
| `/repo-analysis` | RepoAnalysis | Repo analysis |
| `/blueprint` | BlueprintGenerator | Blueprint generation |
| `/doc-generator` | DocGenerator | Documentation generation |
| `/docs` | Docs | Documentation center |
| `/stages/:stage` | StagePage | Workflow stage |

### API Client Pattern

All API calls go through `api.ts`:

```typescript
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}
```

## Deployment Architecture

### Backend (Fly.io)

- FastAPI app deployed as a Docker container
- Persistent SQLite volume mounted at `/data`
- Database at `/data/app.db`
- Environment: `DATABASE_URL`, `GITHUB_TOKEN`

### Frontend (Static CDN)

- Vite production build (`npm run build` → `dist/`)
- Static files served via CDN
- `VITE_API_URL` set to deployed backend URL

## Usage Patterns

### Pattern 1: Quick Repo Audit

1. Go to Repo Analysis
2. Enter any public repo
3. Get instant architecture overview

### Pattern 2: AI-Powered Development

1. Go to Blueprint Generator
2. Enter your target repo
3. Copy the generated prompt
4. Paste into your AI tool and start coding

### Pattern 3: Project Tracking

1. Create a project in ZECT
2. Connect GitHub repos
3. Monitor PRs, CI, and progress from the Dashboard

### Pattern 4: Documentation Generation

1. Go to Doc Generator
2. Select sections you need
3. Copy generated docs for your repo's wiki or README

### Pattern 5: Multi-Repo Management

1. Go to Orchestration for cross-repo view
2. Use Multi-Repo Analysis for detailed comparison
3. Generate multi-repo blueprints for system-wide AI prompts

## Security

- GitHub tokens are stored in memory only (not persisted to disk)
- No credentials are logged or exposed in API responses
- CORS is configured to allow frontend origin only
- All GitHub API calls go through the backend (tokens never exposed to frontend)
