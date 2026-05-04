# ZECT — Backend Architecture

## Overview

The ZECT backend is a **FastAPI** application providing RESTful APIs for project management, GitHub integration, AI-powered code review, token tracking, and repository analysis.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | FastAPI | Async REST API framework |
| Server | Uvicorn | ASGI server |
| ORM | SQLAlchemy 2.x | Database abstraction |
| Validation | Pydantic v2 | Request/response schemas |
| GitHub | PyGithub | GitHub API integration |
| AI | OpenAI SDK | LLM API calls |
| Database | SQLite / PostgreSQL | Data persistence |
| Auth | Custom middleware | Session-based authentication |

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app initialization, CORS, middleware
│   ├── database.py          # SQLAlchemy engine, session factory
│   ├── models.py            # ORM models (projects, repos, settings, token_logs)
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── token_tracker.py     # Token usage logging and cost calculation
│   ├── github_service.py    # GitHub API wrapper (repos, PRs, files)
│   ├── review_service.py    # AI code review logic (prompt + analysis)
│   └── routers/
│       ├── auth.py          # Login/logout endpoints
│       ├── projects.py      # CRUD for projects
│       ├── settings.py      # Feature toggles and configuration
│       ├── github.py        # GitHub integration endpoints
│       ├── code_review.py   # AI code review endpoints
│       ├── llm.py           # Ask Mode, Plan Mode, Blueprint AI
│       ├── analytics.py     # Token usage dashboard and metrics
│       └── repo_analysis.py # Repository structure analysis
├── .env                     # Environment variables (gitignored)
├── .env.example             # Template for .env
├── pyproject.toml           # Poetry dependencies
└── poetry.lock              # Locked dependency versions
```

---

## API Router Reference

### Authentication (`/api/auth`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/auth/login` | Authenticate user, return token |
| POST | `/api/auth/logout` | Invalidate session |

### Projects (`/api/projects`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/projects` | List all projects |
| GET | `/api/projects/{id}` | Get project detail |
| POST | `/api/projects` | Create new project |
| PUT | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |

### GitHub (`/api/github`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/github/repos/{owner}/{repo}` | Get repo metadata |
| GET | `/api/github/repos/{owner}/{repo}/tree` | Get file tree |
| GET | `/api/github/repos/{owner}/{repo}/readme` | Get README content |
| GET | `/api/github/repos/{owner}/{repo}/pulls` | List pull requests |
| GET | `/api/github/repos/{owner}/{repo}/pulls/{pr}` | Get PR detail + diff |

### Code Review (`/api/code-review`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/code-review/pr` | Review a PR (AI-powered) |
| POST | `/api/code-review/snippet` | Review a code snippet |

### LLM (`/api/llm`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/llm/ask` | Ask Mode — Q&A with repo context |
| POST | `/api/llm/plan` | Plan Mode — generate engineering plan |
| POST | `/api/llm/blueprint` | Blueprint — generate full-repo prompt |

### Analytics (`/api/analytics`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/analytics/overview` | Project metrics summary |
| GET | `/api/analytics/token-dashboard` | Token usage stats |
| GET | `/api/analytics/token-logs` | Raw token usage logs |

### Repo Analysis (`/api/repo-analysis`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/repo-analysis/analyze` | Analyze single repo structure |
| POST | `/api/repo-analysis/multi` | Analyze multiple repos |

### Settings (`/api/settings`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/settings` | Get all settings |
| PUT | `/api/settings/{key}` | Update a setting |

---

## Database Schema

### `projects` Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Auto-increment ID |
| name | String | Project name |
| description | Text | Project description |
| team | String | Owning team |
| status | String | active, completed, on-hold |
| stage | String | Ask Mode, Plan Mode, Build Phase, Review, Deploy |
| completion | Integer | Completion percentage (0-100) |
| token_savings | Float | Token savings percentage |
| risk_alerts | Integer | Number of active risk alerts |
| created_at | DateTime | Creation timestamp |

### `repos` Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Auto-increment ID |
| project_id | Integer (FK) | Linked project |
| owner | String | GitHub owner/org |
| name | String | Repository name |
| url | String | Full GitHub URL |

### `settings` Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Auto-increment ID |
| key | String (unique) | Setting identifier |
| value | String | Setting value |
| description | String | Human description |

### `token_logs` Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Auto-increment ID |
| action | String | Feature that triggered the call |
| model | String | Model used |
| prompt_tokens | Integer | Input tokens |
| completion_tokens | Integer | Output tokens |
| estimated_cost | Float | Estimated cost in USD |
| timestamp | DateTime | When the call was made |

---

## Authentication Flow

```
1. Client sends POST /api/auth/login { email, password }
2. Backend validates against ZECT_USERNAME / ZECT_PASSWORD env vars
3. On success: returns { token, user } 
4. Client stores token in localStorage
5. Client sends token in Authorization header for all subsequent requests
6. Backend middleware validates token on protected routes
```

---

## Database Configuration

The backend supports both SQLite and PostgreSQL via the `DATABASE_URL` environment variable:

```env
# SQLite (development)
DATABASE_URL=sqlite:///./zect.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:password@localhost:5432/zect_db
```

Tables are auto-created on startup via `Base.metadata.create_all()`. Demo data is seeded if the database is empty.

---

## Error Handling

| Status | Meaning | When |
|--------|---------|------|
| 200 | Success | Normal response |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid auth token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Unexpected failure |
| 503 | Service Unavailable | AI provider down/unconfigured |

---

## Running the Backend

```bash
# Install dependencies
cd backend
poetry install --no-root

# Configure environment
cp .env.example .env
# Edit .env with your values

# Start development server
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Security

1. **CORS** — configured to allow frontend origin only
2. **Auth middleware** — validates token on all `/api/` routes
3. **Secrets in .env** — never committed, never exposed to client
4. **SQL injection prevention** — SQLAlchemy parameterized queries
5. **Input validation** — Pydantic schemas validate all inputs
6. **Rate limiting** — (planned) per-user API rate limits
