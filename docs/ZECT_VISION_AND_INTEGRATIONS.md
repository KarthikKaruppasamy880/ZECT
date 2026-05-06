# ZECT Vision, Database Strategy, and Integration Plan

## Table of Contents
1. [Database: SQLite vs PostgreSQL](#1-database-sqlite-vs-postgresql)
2. [Jira Integration](#2-jira-integration)
3. [ZECT Vision — Building an Autonomous Engineering Platform](#3-zect-vision--building-an-autonomous-engineering-platform)

---

## 1. Database: SQLite vs PostgreSQL

### Current State: SQLite
ZECT currently uses **SQLite** (`zect.db` file). This works for local development and single-user testing but has limitations at scale.

### Comparison

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| **Setup** | Zero config, file-based | Requires server process |
| **Concurrent writes** | Single writer at a time | Full multi-user concurrency |
| **Scalability** | Good up to ~100 concurrent users | Handles thousands of connections |
| **Production readiness** | Prototyping only | Production-grade |
| **Cloud deployment** | Ephemeral on containers (data lost on restart) | Persistent, managed services (RDS, Cloud SQL) |
| **JSON support** | Basic | Full JSONB with indexing |
| **Full-text search** | FTS5 extension | Built-in tsvector |
| **Backup/Restore** | File copy | pg_dump, point-in-time recovery |
| **Cost** | Free | Free (self-hosted) or ~$15-50/mo (managed) |

### Recommendation: **Migrate to PostgreSQL**

SQLite is NOT suitable for production because:
1. **Container deployments lose data** — SQLite is a file; if your Docker container restarts, the DB file is gone unless you mount a volume
2. **No concurrent writes** — only one request can write at a time; multiple users will hit lock errors
3. **No managed backups** — you'd need custom scripts to backup a SQLite file

### Migration Plan (Code Changes Required)

**The migration is minimal** because ZECT uses SQLAlchemy ORM — the same models work with both databases.

**Step 1: Install PostgreSQL driver**
```bash
cd backend
poetry add psycopg2-binary
```

**Step 2: Update DATABASE_URL environment variable**
```bash
# Local development
DATABASE_URL=postgresql://zect_user:zect_pass@localhost:5432/zect_db

# AWS RDS
DATABASE_URL=postgresql://zect_user:<password>@zect-db.xxxx.us-east-1.rds.amazonaws.com:5432/zect_db
```

**Step 3: No code changes needed** — `database.py` already reads `DATABASE_URL` from env:
```python
DATABASE_URL = os.getenv("DATABASE_URL", _default_db)
```

**Step 4: Run database init** — SQLAlchemy `create_all()` creates tables automatically on startup.

### PostgreSQL Setup Options

| Option | Cost | Best For |
|--------|------|----------|
| **Docker Compose** (local) | Free | Local development |
| **AWS RDS** | ~$15/mo (db.t3.micro) | Production |
| **Supabase** | Free tier available | Quick start |
| **Neon** | Free tier (0.5 GB) | Serverless |
| **Railway** | ~$5/mo | Simple deployment |

### Docker Compose for Local PostgreSQL
```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: zect_db
      POSTGRES_USER: zect_user
      POSTGRES_PASSWORD: zect_pass
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### What's Stored in the Database

| Table | Records | Purpose |
|-------|---------|---------|
| `projects` | 6 demo + user-created | Project metadata, stage, completion %, risk alerts |
| `repos` | GitHub repos linked to projects | Owner, repo name, CI status, coverage |
| `settings` | App configuration | API keys, feature toggles, preferences |
| `token_logs` | Every LLM API call | Action, feature, model, token counts, cost, timestamp |

**Future tables (planned):**
| Table | Purpose |
|-------|---------|
| `code_reviews` | Persisted review results with findings, scores, timestamps |
| `jira_tasks` | Synced Jira issues with repo mapping |
| `build_runs` | Code generation and build execution logs |
| `pr_history` | PR creation/merge tracking |
| `users` | Multi-user support with roles |

---

## 2. Jira Integration

### How It Would Work

```
┌─────────────────────────────────────────────────────────────┐
│                      JIRA CLOUD                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  Backlog  │───▶│In Progress│───▶│  Done    │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│       │                │               ▲                     │
│       │ webhook        │ webhook       │ API update          │
└───────┼────────────────┼───────────────┼─────────────────────┘
        ▼                ▼               │
┌─────────────────────────────────────────────────────────────┐
│                      ZECT BACKEND                            │
│                                                              │
│  1. Receive webhook ──▶ Parse Jira issue details             │
│  2. Map to ZECT project + repo                               │
│  3. Generate code via AI ──▶ Create branch + PR              │
│  4. Run ZECT Code Review on the PR                           │
│  5. Assign human reviewer                                    │
│  6. On PR merge ──▶ Update Jira status to Done               │
│  7. Log tokens + cost to dashboard                           │
└─────────────────────────────────────────────────────────────┘
```

### Workflow: Jira Issue → Code → PR → Review → Complete

1. **New Jira issue created** → Jira sends webhook to ZECT
2. **ZECT parses issue** → extracts title, description, acceptance criteria, linked repo
3. **ZECT generates code** → uses AI to write implementation based on issue details
4. **ZECT creates PR** → pushes code to a new branch, opens PR on GitHub
5. **ZECT runs Code Review** → auto-reviews its own generated code for bugs/vulns
6. **Human reviews PR** → ZECT assigns the reviewer from Jira assignee field
7. **PR merged** → ZECT updates Jira issue status to "Done" via API
8. **Dashboard updated** → tokens, cost, and task completion tracked

### Configuration Required

**Step 1: Jira API Token**
- Go to https://id.atlassian.com/manage-profile/security/api-tokens
- Create an API token
- Add to ZECT settings:
  ```
  JIRA_BASE_URL=https://your-org.atlassian.net
  JIRA_USER_EMAIL=your-email@company.com
  JIRA_API_TOKEN=your-api-token
  JIRA_PROJECT_KEY=ZECT  (or your Jira project key)
  ```

**Step 2: Jira Webhook (for real-time sync)**
- Go to Jira → Settings → System → Webhooks
- Add webhook URL: `https://your-zect-domain.com/api/jira/webhook`
- Select events: Issue Created, Issue Updated, Issue Transitioned
- This sends real-time notifications when issues change

**Step 3: Project Mapping in ZECT**
- In ZECT Settings page, map Jira projects to GitHub repos:
  ```
  Jira Project "ZECT" → GitHub repo "KarthikKaruppasamy880/ZECT"
  Jira Project "ZEF"  → GitHub repo "KarthikKaruppasamy880/ZEF"
  ```

**Step 4: Jira Custom Fields (optional)**
- Add custom fields to Jira issues for:
  - `Target Repo` — which GitHub repo to generate code in
  - `Target Branch` — base branch for the PR
  - `Reviewer` — who should review the generated code

### Jira API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /rest/api/3/issue/{key}` | Fetch issue details |
| `GET /rest/api/3/search` | Search issues by project/status |
| `PUT /rest/api/3/issue/{key}` | Update issue status |
| `POST /rest/api/3/issue/{key}/comment` | Add PR link as comment |
| `GET /rest/api/3/issue/{key}/transitions` | Get available status transitions |
| `POST /rest/api/3/issue/{key}/transitions` | Move issue to new status |

### Python Library
```bash
poetry add jira  # Official Jira Python library
```

```python
from jira import JIRA

jira = JIRA(
    server="https://your-org.atlassian.net",
    basic_auth=("email@company.com", "api-token")
)

# Get issue
issue = jira.issue("ZECT-123")
print(issue.fields.summary)
print(issue.fields.description)

# Update status
jira.transition_issue(issue, "Done")

# Add comment
jira.add_comment(issue, "PR created: https://github.com/...")
```

---

## 3. ZECT Vision — Building an Autonomous Engineering Platform

### Autonomous Engineering Capabilities

| Capability | ZECT Current State | What's Needed |
|-----------|-------------------|---------------|
| **Understands codebase** | Repo Analysis + Blueprint | Already built |
| **Generates code from tasks** | Ask Mode (Q&A only) | Need: Code Generation engine |
| **Creates PRs automatically** | PR Viewer (read-only) | Need: PR Creation from AI output |
| **Reviews code** | ZECT Code Review Engine | Just built |
| **Runs code locally** | Not available | Need: Sandboxed execution environment |
| **Shows generated changes** | Not available | Need: Diff viewer for AI-generated code |
| **Iterates on feedback** | Not available | Need: Feedback loop with AI |
| **Tracks progress** | Dashboard + Analytics | Already built |
| **Integrates with Jira** | Not available | Planned (see above) |

### ZECT's Path to Full Autonomous Functionality

#### Phase 1: Code Generation Engine (Next Priority)
**What it does:** Takes a task description (from Jira or manual input) and generates code.

```
User Input: "Add pagination to the /api/projects endpoint"
    ↓
ZECT AI analyses repo structure (existing Blueprint)
    ↓
Generates code changes (new/modified files)
    ↓
Shows diff preview in ZECT UI
    ↓
User reviews → approves → ZECT creates PR
```

**Key components:**
- `code_generator.py` — AI service that generates code from task + repo context
- Code diff viewer in frontend — shows generated changes before committing
- Branch creation + PR automation via GitHub API

#### Phase 2: Build & Run Preview
**What it does:** Runs the generated code in a sandboxed environment so you can see it working.

**Options:**
1. **Docker-based sandboxing** — spin up containers to run the project
2. **GitHub Codespaces integration** — use GitHub's cloud IDE
3. **Local dev server proxy** — ZECT starts the dev server and proxies the output

**This is the most complex phase** — it requires:
- Container orchestration (Docker SDK for Python)
- Port forwarding / preview URLs
- Build log streaming to the ZECT frontend
- Resource limits and cleanup

#### Phase 3: Feedback Loop & Iteration
**What it does:** After reviewing AI-generated code, you can give feedback and ZECT iterates.

```
You: "The pagination should use cursor-based, not offset-based"
    ↓
ZECT regenerates with updated instructions
    ↓
Shows new diff (changes from previous version)
    ↓
You approve → PR updated
```

#### Phase 4: Full Autonomous Pipeline
```
Jira Issue Created
    ↓
ZECT picks up task automatically
    ↓
Analyses repo + generates code
    ↓
Runs ZECT Code Review on generated code
    ↓
Creates PR with all changes
    ↓
Assigns human reviewer
    ↓
Human approves → PR merged
    ↓
Jira issue marked Done
    ↓
Dashboard shows completion + token cost
```

### Architecture for Future ZECT

```
┌──────────────────────────────────────────────────────────┐
│                    ZECT FRONTEND (React)                   │
│                                                            │
│  Dashboard │ Projects │ Code Review │ Code Generator       │
│  Ask Mode  │ Plan Mode│ Jira Board  │ Build Preview        │
│  Blueprint │ Docs     │ Analytics   │ Settings             │
└──────────────────────────┬───────────────────────────────┘
                           │ REST API
┌──────────────────────────┴───────────────────────────────┐
│                    ZECT BACKEND (FastAPI)                  │
│                                                            │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ LLM Service │  │ GitHub       │  │ Jira Service    │  │
│  │ (OpenAI)    │  │ Service      │  │ (webhooks+API)  │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Code Review │  │ Code         │  │ Build/Run       │  │
│  │ Engine      │  │ Generator    │  │ Service (Docker) │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐                        │
│  │ Token       │  │ Repo         │                        │
│  │ Tracker     │  │ Analyser     │                        │
│  └─────────────┘  └──────────────┘                        │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────┐
│              PostgreSQL Database                           │
│  projects │ repos │ settings │ token_logs │ code_reviews  │
│  jira_tasks │ build_runs │ pr_history │ users             │
└──────────────────────────────────────────────────────────┘
```

### Implementation Priority

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| **P0** | PostgreSQL migration | 1 day | Production readiness |
| **P0** | Code Review Engine | Done | Bug/vuln detection |
| **P1** | Code Generation from tasks | 1-2 weeks | Core autonomous feature |
| **P1** | Jira integration (basic) | 1 week | Task automation |
| **P2** | PR auto-creation from generated code | 3-5 days | Workflow automation |
| **P2** | Generated code diff viewer | 3-5 days | User sees changes before commit |
| **P3** | Build/Run preview (Docker) | 2-3 weeks | See code running |
| **P3** | Feedback loop / iteration | 1-2 weeks | Refine AI output |
| **P4** | Multi-user / roles | 1-2 weeks | Team collaboration |
| **P4** | Full autonomous pipeline | 2-3 weeks | End-to-end automation |

---

## Summary

**Immediate actions (this sprint):**
1. ZECT Code Review Engine — **DONE**
2. PostgreSQL migration — ready to implement (minimal code change)
3. Jira integration analysis — **DONE** (this document)

**Next sprint:**
1. Code Generation engine (AI writes code from task descriptions)
2. Jira webhook integration (auto-receive tasks)
3. PR auto-creation (push generated code to GitHub)

**Future sprints:**
1. Build/Run preview environment
2. Feedback loop for iterating on generated code
3. Full autonomous pipeline (Jira → Code → Review → PR → Merge → Done)

The path from current ZECT to a fully autonomous engineering platform is clear and achievable in phases. Each phase adds standalone value while building toward the full vision.
