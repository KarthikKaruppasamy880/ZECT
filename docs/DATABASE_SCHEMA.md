# ZECT Database Schema Documentation

> Complete reference for the ZECT SQLite database — all tables, columns, relationships, and seed data.

---

## Overview

ZECT uses **SQLite** as its default database, managed via **SQLAlchemy ORM**. The database is auto-created on first startup and seeded with demo data.

- **File location:** `backend/zect.db`
- **Engine:** SQLite 3 (or PostgreSQL via `DATABASE_URL` env var)
- **ORM:** SQLAlchemy 2.x with declarative base
- **Auto-migration:** Tables created via `Base.metadata.create_all(engine)`

---

## Entity-Relationship Diagram

```
┌─────────────────────┐       ┌─────────────────────┐
│      projects       │       │       repos          │
├─────────────────────┤       ├─────────────────────┤
│ id (PK)             │──┐    │ id (PK)             │
│ name                │  │    │ project_id (FK) ────┘
│ description         │  │    │ owner               │
│ team                │  │    │ repo_name            │
│ status              │  │    │ default_branch       │
│ current_stage       │       │ ci_status            │
│ completion_percent  │       │ coverage_percent     │
│ token_savings       │       │ last_synced          │
│ risk_alerts         │       └─────────────────────┘
│ created_at          │
│ updated_at          │
└─────────────────────┘

┌─────────────────────┐       ┌─────────────────────┐
│      settings       │       │     token_logs       │
├─────────────────────┤       ├─────────────────────┤
│ id (PK)             │       │ id (PK)             │
│ key (UNIQUE)        │       │ action              │
│ value               │       │ feature             │
│ setting_type        │       │ model               │
│ label               │       │ prompt_tokens       │
│ description         │       │ completion_tokens   │
│ options             │       │ total_tokens        │
└─────────────────────┘       │ estimated_cost_usd  │
                              │ created_at          │
                              └─────────────────────┘
```

---

## Table: `projects`

Stores engineering projects tracked through the 5-stage delivery pipeline.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer | No | Auto-increment | Primary key |
| `name` | String | No | — | Project name |
| `description` | Text | Yes | `""` | Detailed description |
| `team` | String | Yes | `""` | Responsible team |
| `status` | String | Yes | `"active"` | `active`, `completed`, `on-hold` |
| `current_stage` | String | Yes | `"ask"` | `ask`, `plan`, `build`, `review`, `deploy` |
| `completion_percent` | Float | Yes | `0.0` | 0.0 to 100.0 |
| `token_savings` | Float | Yes | `0.0` | Estimated token savings percentage |
| `risk_alerts` | Integer | Yes | `0` | Number of active risk alerts |
| `created_at` | DateTime | Yes | `now(UTC)` | Record creation timestamp |
| `updated_at` | DateTime | Yes | `now(UTC)` | Last update timestamp (auto-updates) |

**Relationships:**
- `repos` — One-to-many relationship with `repos` table (cascade delete)

**Indexes:**
- `id` — Primary key index

---

## Table: `repos`

GitHub repositories linked to projects.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer | No | Auto-increment | Primary key |
| `project_id` | Integer | No | — | Foreign key to `projects.id` |
| `owner` | String | No | — | GitHub owner (user or org) |
| `repo_name` | String | No | — | Repository name |
| `default_branch` | String | Yes | `"main"` | Default git branch |
| `ci_status` | String | Yes | `"unknown"` | `passing`, `failing`, `pending`, `unknown` |
| `coverage_percent` | Float | Yes | `0.0` | Code coverage percentage |
| `last_synced` | DateTime | Yes | `null` | Last GitHub sync timestamp |

**Relationships:**
- `project` — Many-to-one relationship with `projects` table

**Foreign Keys:**
- `project_id` -> `projects.id` (cascade delete via relationship)

---

## Table: `settings`

Feature toggles and configuration options for the ZECT platform.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer | No | Auto-increment | Primary key |
| `key` | String | No | — | Unique setting identifier |
| `value` | String | Yes | `""` | Current value |
| `setting_type` | String | Yes | `"text"` | `toggle`, `select`, `text` |
| `label` | String | Yes | `""` | Human-readable label |
| `description` | String | Yes | `""` | Setting description |
| `options` | String | Yes | `""` | JSON array of options (for `select` type) |

**Constraints:**
- `key` is UNIQUE

**Default Settings (seeded on first access):**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `auto-review` | toggle | `true` | Automated code review on build complete |
| `token-tracking` | toggle | `true` | Track AI token consumption |
| `deploy-gates` | toggle | `true` | Block deploys on unresolved findings |
| `risk-alerts` | toggle | `false` | Slack/email notifications for risk alerts |
| `auto-plan` | toggle | `false` | Auto-generate plans from requirements |
| `session-context` | toggle | `true` | Persist context across AI sessions |
| `default-stage` | select | `Ask Mode` | Default starting stage for new projects |
| `review-severity` | select | `Medium` | Minimum review severity to surface |
| `deploy-approval` | select | `Tech Lead + PM` | Who must approve deployments |
| `token-budget` | select | `80% of budget` | Monthly token budget alert threshold |

---

## Table: `token_logs`

Persistent audit log for every token-consuming operation (LLM calls, GitHub API calls, repo analysis).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | Integer | No | Auto-increment | Primary key |
| `action` | String | No | — | Operation name (e.g., `ask_question`, `generate_plan`) |
| `feature` | String | Yes | `""` | Feature category (see below) |
| `model` | String | Yes | `""` | Model used (e.g., `gpt-4o-mini`, `github-api`) |
| `prompt_tokens` | Integer | Yes | `0` | Input tokens consumed |
| `completion_tokens` | Integer | Yes | `0` | Output tokens generated |
| `total_tokens` | Integer | Yes | `0` | Total tokens (prompt + completion) |
| `estimated_cost_usd` | Float | Yes | `0.0` | Estimated cost in USD |
| `created_at` | DateTime | Yes | `now(UTC)` | Timestamp of the operation |

**Feature Categories:**

| Feature | Actions Logged |
|---------|---------------|
| `ask_mode` | `ask_question` |
| `plan_mode` | `generate_plan` |
| `blueprint` | `generate_blueprint`, `generate_focused_blueprint`, `enhance_blueprint` |
| `doc_gen` | `generate_docs` |
| `repo_analysis` | `analyze_repo`, `analyze_multi_repo` |

**Cost Estimation:**

Pricing is based on GPT-4o-mini rates (per 1M tokens):
- Input: $0.15 / 1M tokens
- Output: $0.60 / 1M tokens
- GitHub API calls: $0.00 (free)

---

## Demo Seed Data

On first startup (when `projects` table is empty), 6 demo projects are seeded:

| # | Project | Team | Stage | Completion | Repos |
|---|---------|------|-------|------------|-------|
| 1 | Policy Admin Modernization | Platform Engineering | build | 55% | ZECT |
| 2 | Claims Processing API | Claims Engineering | review | 78% | ZEF |
| 3 | Agent Portal Redesign | Product Engineering | plan | 28% | — |
| 4 | Underwriting Rules Engine | Underwriting Tech | deploy | 92% | — |
| 5 | Customer Notifications Service | Platform Engineering | deploy | 100% | — |
| 6 | Document Intelligence Pipeline | AI/ML Engineering | ask | 8% | — |

---

## API Endpoints for Database Operations

### Projects CRUD
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all projects |
| GET | `/api/projects/{id}` | Get project by ID |
| POST | `/api/projects` | Create new project |
| PUT | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project (cascades repos) |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | List all settings |
| PUT | `/api/settings/{key}` | Update a setting value |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/overview` | Aggregated project metrics |
| GET | `/api/analytics/token-dashboard` | Token usage summary with breakdowns |

### Token Usage
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analysis/tokens` | Token usage log (recent 100 entries) |

---

## Database Connection

### Code Reference

```python
# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./zect.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Resetting the Database

```bash
# Delete the SQLite file
rm backend/zect.db

# Restart the backend — database auto-recreated with demo data
poetry run uvicorn app.main:app --reload
```
