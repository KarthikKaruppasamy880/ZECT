# ZECT Repository Analysis Report

**Engineering Delivery Control Tower — End-to-End Analysis**
*Generated from actual codebase at `KarthikKaruppasamy880/ZECT` (develop branch)*

---

## 1. Executive Summary

ZECT (Engineering Delivery Control Tower) is a full-stack AI-governed engineering productivity platform built for **Zinnia engineering teams**. It provides a unified control tower that combines **real GitHub integration** (PRs, diffs, commits, CI status), **AI-powered code generation/review/planning** (via OpenAI), **multi-repo analysis with blueprint generation**, and a **5-stage delivery pipeline** (Ask → Plan → Build → Review → Deploy). The core value proposition is giving engineering teams a single pane of glass for delivery management with AI acceleration at every stage, plus token/cost governance to control LLM spend.

---

## 2. Tech Stack

| Layer | Technology | Source File |
|-------|-----------|-------------|
| **Frontend Framework** | React 18.3 + TypeScript 5.6 | `frontend/package.json` |
| **Frontend Build** | Vite 6.0 | `frontend/package.json` |
| **Frontend Routing** | react-router-dom 7.14 | `frontend/src/App.tsx` |
| **Frontend Styling** | Tailwind CSS 3.4 + tailwindcss-animate | `frontend/package.json` |
| **Frontend Charts** | Recharts 2.12 | `frontend/package.json` |
| **Frontend Icons** | Lucide React 0.364 | `frontend/package.json` |
| **Backend Framework** | FastAPI 0.136 (Python 3.12+) | `backend/pyproject.toml` |
| **Backend Server** | Uvicorn (bundled with FastAPI[standard]) | `backend/pyproject.toml` |
| **ORM** | SQLAlchemy 2.0.49 | `backend/pyproject.toml` |
| **Database** | PostgreSQL (default) / SQLite (fallback) | `backend/app/database.py` |
| **DB Driver** | psycopg 3.3.3 (binary) | `backend/pyproject.toml` |
| **GitHub Integration** | PyGithub 2.9.1 | `backend/app/github_service.py` |
| **LLM Provider** | OpenAI SDK 2.33 (gpt-4o-mini default) | `backend/app/routers/llm.py` |
| **Multi-LLM Routing** | OpenRouter (via OpenAI-compatible API) | `backend/app/routers/model_selection.py` |
| **Auth Model** | Simple token-based (env-var credentials, in-memory sessions) | `backend/app/routers/auth.py` |
| **HTTP Client** | httpx 0.28 | `backend/pyproject.toml` |

---

## 3. Architecture Diagram

```mermaid
graph TD
    subgraph Browser ["Browser (localhost:5173)"]
        React["React 18 + Vite"]
        Router["react-router-dom (22 routes)"]
        API_Client["lib/api.ts (typed fetch wrapper)"]
    end

    subgraph FastAPI_Backend ["FastAPI Backend (localhost:8000)"]
        CORS["CORS Middleware (allow all origins)"]
        GlobalHandler["Global Exception Handler → JSON 500s"]
        
        subgraph Routers ["16 Router Modules"]
            Auth["auth.py → /api/auth"]
            Projects["projects.py → /api/projects"]
            GitHub_R["github.py → /api/github"]
            RepoAnalysis["repo_analysis.py → /api/analysis"]
            LLM["llm.py → /api/llm"]
            Build["build_phase.py → /api/build"]
            Review["review_phase.py → /api/review"]
            Deploy["deploy_phase.py → /api/deploy"]
            CodeReview["code_review.py → /api/review"]
            Skills["skills.py → /api/skills"]
            TokenCtrl["token_controls.py → /api/tokens"]
            Models["model_selection.py → /api/models"]
            Orch["orchestration.py → /api/orchestration"]
            Context["context_management.py → /api/context"]
            Analytics["analytics.py → /api/analytics"]
            Settings["settings.py → /api/settings"]
        end
        
        TokenTracker["token_tracker.py (fail-safe logging)"]
        GH_Service["github_service.py (PyGithub wrapper)"]
        ReviewService["review_service.py (AI review engine)"]
    end

    subgraph External ["External APIs"]
        GitHub_API["GitHub API (repos, PRs, commits, CI)"]
        OpenAI_API["OpenAI API (gpt-4o-mini)"]
        OpenRouter["OpenRouter API (free models)"]
    end

    subgraph Database ["PostgreSQL / SQLite"]
        DB[(10 Tables)]
    end

    React --> API_Client
    API_Client -->|HTTP JSON| CORS
    CORS --> Routers
    Routers --> TokenTracker
    Routers --> GH_Service
    Routers --> ReviewService
    GH_Service --> GitHub_API
    LLM --> OpenAI_API
    Build --> OpenAI_API
    Review --> OpenAI_API
    Models --> OpenRouter
    Models --> OpenAI_API
    Routers --> DB
    TokenTracker --> DB
```

---

## 4. Frontend Map — All Routes

Source: `frontend/src/App.tsx` (22 routes inside `<Layout>`)

| # | Path | Page Component | Purpose | Primary API Calls (`lib/api.ts`) |
|---|------|---------------|---------|----------------------------------|
| 1 | `/` | `Dashboard` | Executive overview: metrics, project cards, stage chart, token widget | `getProjects()`, `getAnalytics()`, `getTokenDashboard()` |
| 2 | `/projects` | `Projects` | Filterable project list with status badges | `getProjects(status?)` |
| 3 | `/projects/new` | `CreateProject` | Create project + link GitHub repos | `createProject(data)` |
| 4 | `/projects/:id` | `ProjectDetail` | PRs, commits, CI status for linked repos | `getProject(id)`, `getGitHubPulls()`, `getGitHubCommits()`, `getGitHubWorkflowRuns()` |
| 5 | `/projects/:id/pr/:owner/:repo/:number` | `PRViewer` | File-by-file diff with line numbers | `getGitHubPull()`, `getGitHubPullFiles()` |
| 6 | `/analytics` | `Analytics` | Bar/pie charts, team performance, project table | `getAnalytics()` |
| 7 | `/settings` | `Settings` | Feature toggles, API key config modals (GitHub + OpenAI) | `getSettings()`, `updateSetting()`, `configureApiKey()`, `configureLLMKey()`, `getApiKeyStatus()`, `getLLMStatus()` |
| 8 | `/orchestration` | `Orchestration` | Multi-repo dashboard with GitHub data | `getGitHubRepos()`, `getGitHubRepo()` |
| 9 | `/repo-analysis` | `RepoAnalysis` | Single + multi-repo GitHub analysis | `analyzeRepo()`, `analyzeMultiRepo()` |
| 10 | `/blueprint` | `BlueprintGenerator` | AI-ready prompt generation (Standard + Focused) | `generateBlueprint()`, `generateFocusedBlueprint()`, `enhanceBlueprint()` |
| 11 | `/doc-generator` | `DocGenerator` | Granular documentation generation (6 section types) | `generateDocs()` |
| 12 | `/ask` | `AskMode` | AI-powered Q&A chat with model selector + file attachments | `askQuestion()` or `POST /api/models/chat` |
| 13 | `/plan` | `PlanMode` | AI-powered project planning with model selector + file attachments | `generatePlan()` or `POST /api/models/chat` |
| 14 | `/docs` | `Docs` | Documentation hub (links to all guides) | None (static links) |
| 15 | `/code-review` | `CodeReview` | AI code review for PRs and snippets | `reviewPR()`, `reviewSnippet()` |
| 16 | `/build` | `BuildPhase` | AI code generation from plan steps + file attachments | `buildGenerate()`, `buildFromPlan()` |
| 17 | `/review` | `ReviewPhase` | AI code quality gate with fix prompt generation | `reviewAnalyze()`, `reviewFixPrompt()` |
| 18 | `/deploy` | `DeployPhase` | Deployment checklist + runbook generation | `deployChecklist()`, `deployRunbook()` |
| 19 | `/skills` | `SkillLibrary` | Skill CRUD + AI pattern detection | `getSkills()`, `createSkill()`, `updateSkill()`, `deleteSkill()`, `detectSkillPatterns()` |
| 20 | `/token-controls` | `TokenControls` | Token budget/model controls, per-user tracking, trends | `getTokenUsageFull()`, `getTokenBudget()`, `updateTokenBudget()`, `getModelBreakdown()`, `getUsersActivity()`, `getUsageTrends()`, `checkTokenLimit()` |
| 21 | `/stages/:stage` | `StagePage` | Workflow stage guide (5 stages) | None (static content) |
| 22 | (pre-auth) | `Login` | Login form | `login()`, `verifyToken()` |

---

## 5. Backend Map — All Routers

Source: `backend/app/main.py` (16 router modules registered)

| # | Router Module | Prefix | Key Endpoints | Responsibility | Dependencies |
|---|--------------|--------|---------------|----------------|-------------|
| 1 | `auth.py` | `/api/auth` | `POST /login`, `POST /logout`, `GET /verify` | Simple token auth (env-var credentials, in-memory sessions) | `os`, `secrets` |
| 2 | `projects.py` | `/api/projects` | CRUD: `GET /`, `POST /`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`, `POST /{id}/repos` | Project management with repo linking | SQLAlchemy `Project`, `Repo` models |
| 3 | `github.py` | `/api/github` | `GET /repos/{owner}`, `GET /repos/{owner}/{repo}`, pulls, commits, actions/runs | GitHub API proxy (7 endpoints) | `github_service.py` → PyGithub |
| 4 | `repo_analysis.py` | `/api/analysis` | `POST /repo`, `POST /multi-repo`, `POST /blueprint`, `POST /blueprint/focused`, `POST /docs/generate`, `GET /tokens`, `POST /api-key`, `GET /api-key/status` | Repo analysis, blueprint gen, doc gen, GitHub API key config | `github_service`, `token_tracker` |
| 5 | `llm.py` | `/api/llm` | `POST /ask`, `POST /plan`, `POST /enhance-blueprint`, `POST /configure-key`, `GET /status` | OpenAI-powered Ask, Plan, Blueprint enhancement | OpenAI SDK, `token_tracker` |
| 6 | `code_review.py` | `/api/review` | `POST /pr`, `POST /snippet` | AI code review for PRs and snippets | `github_service`, `review_service` |
| 7 | `build_phase.py` | `/api/build` | `POST /generate`, `POST /from-plan` | AI code generation from plan steps | OpenAI SDK, `token_tracker` |
| 8 | `review_phase.py` | `/api/review` | `POST /analyze`, `POST /fix-prompt` | AI code quality gate + auto-fix prompt | OpenAI SDK, `token_tracker` |
| 9 | `deploy_phase.py` | `/api/deploy` | `POST /checklist`, `POST /runbook` | Deployment checklist + runbook generation | OpenAI SDK, `token_tracker` |
| 10 | `skills.py` | `/api/skills` | CRUD: `GET /`, `POST /`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`, `POST /{id}/use`, `POST /detect` | Skill library with AI pattern detection | SQLAlchemy `Skill`, OpenAI SDK |
| 11 | `token_controls.py` | `/api/tokens` | `GET /usage`, `GET /budget`, `PUT /budget`, `GET /models`, `GET /users`, `GET /users/{id}`, `GET /teams`, `GET /trends`, `GET /check-limit` | Token governance: budgets, per-user tracking, team analytics, trends, limit enforcement | SQLAlchemy `TokenLog`, `TokenBudget`, `User`, `UserSession` |
| 12 | `model_selection.py` | `/api/models` | `GET /`, `GET /status`, `POST /chat` | Multi-provider model routing (OpenAI + OpenRouter) | OpenAI SDK (both providers) |
| 13 | `orchestration.py` | `/api/orchestration` | `POST /dispatch`, `GET /agents` | Multi-agent task dispatch and workflow management | OpenAI SDK, `token_tracker` |
| 14 | `context_management.py` | `/api/context` | `POST /save`, `POST /load`, `DELETE /clear/{page}`, `GET /pages`, `GET /recommendations/{page}` | Per-page context store (in-memory, per-session) | In-memory dict |
| 15 | `analytics.py` | `/api/analytics` | `GET /overview`, `GET /token-dashboard` | Project analytics + token usage dashboard | SQLAlchemy `Project`, `Repo`, `token_tracker` |
| 16 | `settings.py` | `/api/settings` | `GET /`, `PUT /{key}` | Settings CRUD with auto-seeded defaults | SQLAlchemy `Setting` |

**Note:** `code_review.py` and `review_phase.py` both mount on `/api/review` — they share the prefix but have non-overlapping endpoint paths (`/pr`, `/snippet` vs `/analyze`, `/fix-prompt`).

---

## 6. Core User Journeys (File Traces)

### 6.1 Login → Verify Token

```
1. User enters credentials on Login page
   → frontend/src/pages/Login.tsx
2. Calls login(username, password)
   → frontend/src/lib/api.ts:204 → POST /api/auth/login
3. Backend validates against env vars
   → backend/app/routers/auth.py:36 login()
   → secrets.compare_digest(req.username, ZECT_USERNAME)
   → secrets.compare_digest(req.password, ZECT_PASSWORD)
4. Returns token (secrets.token_urlsafe(32))
   → Stored in _active_tokens set (in-memory)
5. Frontend stores in localStorage("zect_token")
   → frontend/src/App.tsx:48 handleLogin()
6. On reload, App.tsx:34 calls verifyToken(token)
   → GET /api/auth/verify?token=...
   → auth.py:55 checks _active_tokens set
```

### 6.2 Repo Analysis (Single + Multi)

```
Single Repo:
1. User enters owner/repo on RepoAnalysis page
   → frontend/src/pages/RepoAnalysis.tsx
2. Calls analyzeRepo(owner, repo)
   → api.ts:76 → POST /api/analysis/repo {owner, repo}
3. Backend fetches from GitHub
   → repo_analysis.py:96 _analyze_repo(owner, repo)
   → github_service.py:11 get_github() → PyGithub client
   → gh.get_repo(f"{owner}/{repo}")
   → Fetches: tree (repo.get_git_tree), README (repo.get_readme), deps (package.json/pyproject.toml)
4. Logs tokens (fail-safe)
   → repo_analysis.py:22 _log_tokens() → token_tracker.py:21 log_tokens()
   → INSERT INTO token_logs
5. Returns RepoAnalysisResult (tree, readme, dependencies, languages, stats)

Multi Repo:
1. User adds multiple repos
   → POST /api/analysis/multi-repo {repos: [{owner, repo}, ...]}
   → repo_analysis.py:382 analyze_multiple_repos()
   → Calls _analyze_repo() for each repo
```

### 6.3 Blueprint Generation (Standard + Focused)

```
Standard:
1. User selects repos → clicks "Generate Blueprint"
   → BlueprintGenerator.tsx → api.ts:80 generateBlueprint(repos)
   → POST /api/analysis/blueprint {repos: [...]}
2. Backend analyzes each repo, builds combined prompt
   → repo_analysis.py:391 generate_blueprint()
   → _analyze_repo() for each → _build_prompt() (line 202)
   → Concatenates: project overview, file trees, key files, dependencies
3. Returns BlueprintResult {prompt, repos_analyzed, total_tokens}

Focused:
1. User enters owner, repo, focus_area, optional goal
   → api.ts:82 generateFocusedBlueprint()
   → POST /api/analysis/blueprint/focused
2. Backend scopes analysis to focus area
   → repo_analysis.py:419 generate_focused_blueprint()
   → _analyze_repo() → _build_focused_prompt() (line 291)
   → Filters tree/files to focus_area, adds goal context
3. Returns FocusedBlueprintResult {prompt, focus_area, files_included, total_tokens}

Enhancement:
1. User clicks "Enhance with AI" on generated blueprint
   → api.ts:110 enhanceBlueprint(raw_blueprint)
   → POST /api/llm/enhance-blueprint
2. LLM improves prompt for AI coding tool consumption
   → llm.py:181 enhance_blueprint()
   → OpenAI gpt-4o-mini call with prompt engineering system prompt
```

### 6.4 Doc Generator

```
1. User enters owner/repo, selects section types
   → DocGenerator.tsx → api.ts:93 generateDocs(owner, repo, sections)
   → POST /api/analysis/docs/generate
2. Backend analyzes repo then generates each section
   → repo_analysis.py:491 generate_documentation()
   → _analyze_repo(owner, repo) → gets tree, readme, deps
   → For each section: _generate_doc_section() (line 510)
   → Calls OpenAI with section-specific system prompts
3. Returns DocGenResult {sections: [{title, content}], model, tokens_used}
```

### 6.5 Ask Mode + Plan Mode

```
Ask Mode:
1. User types question, optionally selects model, attaches files
   → AskMode.tsx
   → If using model selector: POST /api/models/chat (model_selection.py:120)
   → If default: api.ts:100 askQuestion() → POST /api/llm/ask
2. Backend sends to OpenAI with ZECT system prompt
   → llm.py:75 ask_question()
   → Includes optional repo_context (truncated to 8000 chars)
   → log_tokens() after success
3. Returns AskResponse {answer, model, tokens_used}

Plan Mode:
1. User enters project description + optional constraints
   → PlanMode.tsx → POST /api/llm/plan
2. Backend generates structured plan
   → llm.py:121 generate_plan()
   → System prompt requests: executive summary, architecture, phased plan, risks, timeline
   → Parses "## Phase X" headers from output into phases list
3. Returns PlanResponse {plan, phases: [...], model, tokens_used}
```

### 6.6 Build → Review → Deploy Pipeline

```
Build Phase:
1. User enters plan step + optional tech stack/context
   → BuildPhase.tsx → api.ts:132 buildGenerate()
   → POST /api/build/generate
2. build_phase.py:62 generate_code() → OpenAI with code gen prompt
   → Parses FILE_PATH, LANGUAGE, EXPLANATION, code block from response
3. Alternative: POST /api/build/from-plan → parse plan into steps, gen code per step

Review Phase:
1. User pastes code for review
   → ReviewPhase.tsx → api.ts:144 reviewAnalyze()
   → POST /api/review/analyze
2. review_phase.py:66 analyze_code() → OpenAI returns JSON with score, findings
   → Filters findings by severity_threshold
3. Auto-fix: POST /api/review/fix-prompt → generates fix prompt + corrected code

Deploy Phase:
1. User enters project name + environment
   → DeployPhase.tsx → api.ts:156 deployChecklist()
   → POST /api/deploy/checklist
2. deploy_phase.py:65 generate_checklist() → OpenAI returns checklist + runbook + rollback
3. Alternative: POST /api/deploy/runbook → detailed deployment runbook with downtime/risk assessment
```

### 6.7 Skill Library (CRUD + Pattern Detection)

```
CRUD:
1. SkillLibrary.tsx → api.ts:168-175
   → GET /api/skills (list, filter by category)
   → POST /api/skills (create)
   → PUT /api/skills/{id} (update)
   → DELETE /api/skills/{id} (delete)
2. skills.py CRUD endpoints → SQLAlchemy Skill model
   → Tags stored as JSON string, parsed on read

Pattern Detection:
1. User pastes code → "Detect Patterns"
   → api.ts:176 detectSkillPatterns()
   → POST /api/skills/detect
2. skills.py:217 detect_patterns() → OpenAI analyzes code
   → Returns detected_patterns + suggested_skills to auto-save
```

### 6.8 Token Dashboard / Token Tracker

```
Dashboard Widget:
1. Dashboard.tsx → api.ts:57 getTokenDashboard()
   → GET /api/analytics/token-dashboard
   → analytics.py:13 token_dashboard() → token_tracker.py:58 get_usage_summary()
   → Aggregates: total_calls, total_tokens, by_feature, by_model, recent 50

Token Controls Page:
1. TokenControls.tsx → multiple API calls:
   → GET /api/tokens/usage (full summary)
   → GET /api/tokens/budget (budget status with alerts)
   → GET /api/tokens/models (per-model breakdown)
   → GET /api/tokens/users (all user activity)
   → GET /api/tokens/trends?days=30 (daily trend data)
2. Budget management: PUT /api/tokens/budget (set limits, alerts, model preferences)
3. Limit check: GET /api/tokens/check-limit (pre-request enforcement)

How Logging Works:
- Every LLM call in every router calls token_tracker.log_tokens()
  → Creates TokenLog row with: action, feature, model, prompt/completion/total tokens, cost, timestamp
  → Fail-safe: wrapped in try/except, never crashes the request
```

### 6.9 GitHub: PR Viewer, Commits, CI Runs

```
1. ProjectDetail.tsx loads linked repos from project
   → For each repo: getGitHubPulls(), getGitHubCommits(), getGitHubWorkflowRuns()
   → All route through github.py → github_service.py → PyGithub
2. PR Viewer: /projects/:id/pr/:owner/:repo/:number
   → PRViewer.tsx → getGitHubPull() + getGitHubPullFiles()
   → github_service.py:115 get_pull_files() → returns patch diffs
   → DiffViewer.tsx renders file-by-file diff with line numbers
```

---

## 7. Data Model

Source: `backend/app/models.py` — 10 SQLAlchemy models

| # | Table | Purpose | Key Columns | Relationships |
|---|-------|---------|-------------|---------------|
| 1 | `users` | User accounts (SSO-ready) | `email`, `name`, `role` (admin/lead/developer/viewer), `team`, `department`, `sso_provider`, `sso_id`, `is_active` | → sessions, token_logs, budgets, generated_outputs |
| 2 | `token_logs` | Audit log for every token-consuming operation | `user_id` (FK, nullable), `session_id` (FK), `action`, `feature`, `model`, `provider`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `estimated_cost_usd`, `latency_ms`, `status`, `error_message` | → user |
| 3 | `projects` | Engineering projects | `name`, `description`, `team`, `status` (active/completed/on-hold), `current_stage` (ask/plan/build/review/deploy), `completion_percent`, `token_savings`, `risk_alerts` | → repos |
| 4 | `repos` | GitHub repos linked to projects | `project_id` (FK), `owner`, `repo_name`, `default_branch`, `ci_status`, `coverage_percent` | → project |
| 5 | `settings` | Platform configuration | `key`, `value`, `setting_type` (toggle/select/text), `label`, `description`, `options` (JSON) | — |
| 6 | `skills` | Reusable skill templates | `name`, `description`, `category`, `template`, `trigger_pattern`, `tags` (JSON), `usage_count` | — |
| 7 | `token_budgets` | Budget limits per user or global | `user_id` (FK, nullable=global), `scope`, `daily_token_limit`, `monthly_token_limit`, `daily_cost_limit_usd`, `monthly_cost_limit_usd`, `alert_threshold_percent`, `preferred_model`, `allowed_models`, `enforce_limits` | → user |
| 8 | `user_sessions` | Per-user work sessions | `user_id` (FK), `project_id` (FK), `session_type`, `title`, `status`, `total_tokens_used`, `total_cost_usd`, `models_used`, `messages_count` | → user, context_files, generated_outputs |
| 9 | `context_files` | Attached files/repos/snippets per session | `session_id` (FK), `name`, `file_type`, `content`, `char_count`, `token_estimate` | → session |
| 10 | `generated_outputs` | All AI-generated code/plans/reviews | `user_id` (FK), `session_id` (FK), `output_type`, `feature`, `title`, `prompt_used`, `output_content`, `language`, `file_path`, `model_used`, `tokens_used`, `cost_usd`, `quality_score`, `was_accepted` | → user, session |

**Schema auto-creation:** `database.py:27 init_db()` calls `Base.metadata.create_all()` on startup — no Alembic migrations.

---

## 8. Configuration & Secrets

### Backend (`backend/.env.example` + actual code)

| Variable | Required | Default | Purpose | Source File |
|----------|----------|---------|---------|-------------|
| `DATABASE_URL` | No | `postgresql://postgres:postgres@localhost:5432/zect_db` | Database connection string | `database.py:6-7` |
| `GITHUB_TOKEN` | No | `""` (60 req/hr unauthenticated) | GitHub API access | `github_service.py:13` |
| `OPENAI_API_KEY` | For AI features | `""` | OpenAI API (Ask, Plan, Build, Review, Deploy, Blueprint enhance) | `llm.py:13`, `build_phase.py:13`, etc. |
| `OPENROUTER_API_KEY` | No | Falls back to `OPENAI_API_KEY` | OpenRouter multi-model access (free models) | `model_selection.py:77` |
| `ZECT_USERNAME` | For auth | `""` | Login credential | `auth.py:13` |
| `ZECT_PASSWORD` | For auth | `""` | Login credential | `auth.py:14` |

### Frontend (`frontend/.env.example`)

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `VITE_API_URL` | No | `http://localhost:8000` | Backend API base URL |

---

## 9. Fallbacks & Failure Modes

| Scenario | What Happens | Source |
|----------|-------------|--------|
| **No GitHub token** | Falls back to unauthenticated GitHub API (60 requests/hour rate limit) | `github_service.py:17` — `Github()` with no token |
| **GitHub rate limit hit** | `GithubException` with `status=403` → HTTP 403 to frontend with message | `repo_analysis.py:107-108` |
| **GitHub repo not found** | `GithubException` with `status=404` → HTTP 404 | `repo_analysis.py:104-105` |
| **No OpenAI API key** | HTTP 503 "OpenAI API key not configured" for all AI features | Every `_get_client()` in `llm.py:14`, `build_phase.py:14`, `review_phase.py:14`, `deploy_phase.py:14`, `skills.py:27`, `orchestration.py:15` |
| **OpenAI API error** | `APIError` caught → HTTP 502 "OpenAI API error: {message}" | Every LLM endpoint's `except APIError` |
| **DB error on token logging** | Fail-safe: error printed to stdout, request proceeds normally | `token_tracker.py:54` — `except Exception as e: print(...)` |
| **DB error on token dashboard** | Returns empty dashboard data | `analytics.py:17` — `except Exception: return {...empty...}` |
| **Auth not configured** | HTTP 503 "Authentication not configured" | `auth.py:37-38` |
| **Global unhandled exception** | Caught by global handler → JSON 500 with CORS headers (prevents browser CORS error masking) | `main.py:27-41` |
| **Context store reset** | In-memory context clears on server restart | `context_management.py:52` |

---

## 10. Gaps vs Enterprise Readiness

### Implemented Code vs Documented Vision

| Area | Status | Details |
|------|--------|---------|
| **Authentication** | **Partially implemented** | Simple env-var username/password with in-memory token set (`auth.py`). SSO fields exist in `User` model (`sso_provider`, `sso_id`) but SSO flow is **NOT implemented** — documented vision only. |
| **RBAC** | **Schema only** | `User.role` field exists (admin/lead/developer/viewer) but **no authorization middleware** checks roles. Any authenticated user can access all endpoints. |
| **Database Migrations** | **NOT implemented** | Uses `create_all()` on startup. No Alembic. Schema changes require manual DB drops or migration scripts. **Critical gap for production.** |
| **Multi-LLM Providers** | **Implemented** | `model_selection.py` supports OpenAI + OpenRouter (Llama, Mistral, Gemma, Qwen, Claude). Model selector dropdown is on AI pages. |
| **Jira Integration** | **Documented vision only** | `ZECT_VISION_AND_INTEGRATIONS.md` describes Jira integration plans. **Zero implemented code.** |
| **Slack Integration** | **Documented vision only** | Mentioned in vision docs. **Not implemented.** |
| **PostgreSQL Production** | **Implemented** | `database.py` defaults to PostgreSQL. `pool_pre_ping=True` for connection health checks. SQLite fallback available. |
| **Token Governance** | **Fully implemented** | Per-user budgets, daily/monthly limits, model restrictions, alert thresholds, limit enforcement check. Tables: `token_budgets`, `token_logs`. |
| **Context Management** | **Partially implemented** | In-memory store per page (`context_management.py:52`). Resets on restart. `ContextFile` model exists for DB persistence but **not wired up** to the in-memory store. |
| **Generated Output History** | **Schema only** | `GeneratedOutput` model exists (code, plans, reviews, quality_score, was_accepted). **No endpoint or UI writes to this table yet.** |
| **User Sessions** | **Schema only** | `UserSession` model exists with full tracking fields. **No endpoint creates/manages sessions yet.** |
| **Export/Share** | **NOT implemented** | No PDF/Markdown export for blueprints, plans, or reviews. Documented as future feature. |
| **Multi-tenant** | **NOT implemented** | Single-org design. No tenant isolation. |
| **Rate Limiting** | **NOT implemented** | No API rate limiting beyond token budget checks. |
| **Audit Trail** | **Partially implemented** | `token_logs` provides full LLM audit trail. No audit trail for CRUD operations (project create/delete, settings changes). |
| **Testing** | **NOT implemented** | Zero test files. No pytest, no Jest/Vitest. |
| **CI/CD** | **NOT implemented** | No GitHub Actions, no Dockerfile, no docker-compose. |
| **Responsive/Mobile** | **Documented requirement only** | `UI_UX_REQUIREMENTS.md` lists responsive requirements. Sidebar uses Tailwind responsive classes but **no systematic mobile testing or adaptive layouts.** |

### Critical Gaps for Zinnia Enterprise Rollout

1. **No Alembic migrations** — schema changes will break production
2. **No SSO implementation** — only env-var credentials
3. **No RBAC enforcement** — role field exists but is unused
4. **No tests** — zero unit/integration/E2E tests
5. **No CI/CD pipeline** — no automated quality gates
6. **No Dockerfile/docker-compose** — manual deployment only
7. **In-memory auth tokens** — lost on server restart, no persistence
8. **In-memory context store** — lost on server restart
9. **No export functionality** — can't export blueprints/plans/reviews
10. **No Jira/Slack integrations** — only documented as vision

---

## 11. Highest-Value Features for Zinnia Developers (Ranked)

| Rank | Feature | Why It Matters |
|------|---------|---------------|
| **1** | **Blueprint + Focused Blueprint** | Converts any GitHub repo into a single AI-ready prompt that can be pasted into Cursor/Claude Code/Codex. Focused mode scopes to a specific feature. This is the "killer feature" — saves hours of manual context assembly. |
| **2** | **Ask Mode with Repo Context** | Chat with AI about engineering topics. Can attach repo analysis as context so AI knows your codebase. Model selector lets you choose free (Llama) or paid (GPT-4o) models. |
| **3** | **Real GitHub Integration** | Not mock data — live PRs, diffs, commits, CI status from actual GitHub repos. Engineers see their real delivery state in one place. |
| **4** | **Plan Mode** | Structured engineering plan generation with phased milestones, risks, and timeline. Directly feeds into Build Phase. |
| **5** | **Build Phase (Code Generation)** | Generate production code from plan steps. Can parse a full plan into steps and generate code per step. Direct pipeline from Plan → Build. |
| **6** | **Token Governance Dashboard** | Per-user budgets, daily/monthly limits, model restrictions, team analytics. Essential for controlling LLM costs at org scale. |
| **7** | **Code Review (Quality Gate)** | AI reviews code for security, performance, bugs, style. Returns score + findings + auto-fix prompts. Severity filtering. |
| **8** | **Doc Generator (6 section types)** | Generates overview, architecture, API, setup, testing, deployment docs from repo analysis. Fills documentation debt. |
| **9** | **Skill Library** | Save reusable patterns/templates. AI-powered pattern detection auto-suggests skills from code. Organizational knowledge capture. |
| **10** | **Orchestration Engine** | Multi-agent task dispatch (planner/builder/reviewer/deployer/documenter). Dependency ordering and parallel execution groups. |
| **11** | **Deploy Phase** | Generates deployment checklists, runbooks, rollback plans. Risk assessment and downtime estimation. |

---

## 12. Recommended "How to Get 10x Value" Workflow

### Optimal Screen Order for a New Project

```
1. REPO ANALYSIS → Understand what you have
   - Start at /repo-analysis
   - Analyze your main repo (single) to see structure, deps, languages
   - If multi-repo project, use multi-repo analysis

2. BLUEPRINT → Create your AI-ready prompt
   - Go to /blueprint
   - Generate standard blueprint for the full repo
   - Use Focused Blueprint if you're working on a specific feature
   - Click "Enhance with AI" to improve the prompt
   - Copy the blueprint → paste into Cursor/Claude Code/Codex

3. ASK MODE → Explore unknowns
   - Go to /ask
   - Ask questions about architecture, debugging, code review
   - Attach repo context from Step 1 for grounded answers
   - Use free models (Llama 3.1 8B) for exploratory questions
   - Use GPT-4o-mini for precision answers

4. PLAN MODE → Structure your work
   - Go to /plan
   - Describe what you want to build
   - Add repo context + constraints
   - Get phased plan with milestones

5. BUILD PHASE → Generate code
   - Go to /build
   - Paste plan steps from Step 4
   - Generate code for each step
   - Review generated code in the output panel

6. REVIEW PHASE → Quality gate
   - Go to /review
   - Paste generated code for review
   - Check score and findings
   - Use "Generate Fix Prompt" for auto-corrections

7. DEPLOY PHASE → Ship safely
   - Go to /deploy
   - Generate deployment checklist
   - Get runbook with rollback procedure
```

### Blueprint vs Focused Blueprint vs Ask vs Plan

| Use Case | Tool | When |
|----------|------|------|
| "I need to understand this entire repo" | **Standard Blueprint** | Starting a new project, onboarding to a codebase |
| "I need to build a specific feature" | **Focused Blueprint** | Adding auth, building an API endpoint, UI component |
| "I have a specific question" | **Ask Mode** | Debugging, architecture decisions, best practices |
| "I need a structured implementation plan" | **Plan Mode** | Sprint planning, feature breakdown, migration planning |

### Prompt Hygiene Tips

1. **Always attach repo context** — Ask and Plan are 10x better when grounded in actual repo data
2. **Use Focused Blueprint** over Standard when working on one area — less noise, more relevant context
3. **Free models for brainstorming, paid for precision** — Use Llama/Mistral for exploring ideas, GPT-4o-mini for code generation
4. **Build → Review loop** — Generate code, then immediately review it for quality before using
5. **Save skills for patterns** — When you spot a repeating pattern, save it as a skill so the team reuses it

---

## Appendix: Full Endpoint List

<details>
<summary>All 60+ endpoints from router decorators</summary>

### Auth (`/api/auth`)
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/verify`

### Projects (`/api/projects`)
- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/{id}`
- `PUT /api/projects/{id}`
- `DELETE /api/projects/{id}`
- `POST /api/projects/{id}/repos`

### GitHub (`/api/github`)
- `GET /api/github/repos/{owner}`
- `GET /api/github/repos/{owner}/{repo}`
- `GET /api/github/repos/{owner}/{repo}/pulls`
- `GET /api/github/repos/{owner}/{repo}/pulls/{number}`
- `GET /api/github/repos/{owner}/{repo}/pulls/{number}/files`
- `GET /api/github/repos/{owner}/{repo}/commits`
- `GET /api/github/repos/{owner}/{repo}/actions/runs`

### Repo Analysis (`/api/analysis`)
- `POST /api/analysis/repo`
- `POST /api/analysis/multi-repo`
- `POST /api/analysis/blueprint`
- `POST /api/analysis/blueprint/focused`
- `POST /api/analysis/docs/generate`
- `GET /api/analysis/tokens`
- `POST /api/analysis/api-key`
- `GET /api/analysis/api-key/status`

### LLM (`/api/llm`)
- `POST /api/llm/ask`
- `POST /api/llm/plan`
- `POST /api/llm/enhance-blueprint`
- `POST /api/llm/configure-key`
- `GET /api/llm/status`

### Code Review (`/api/review`)
- `POST /api/review/pr`
- `POST /api/review/snippet`
- `POST /api/review/analyze`
- `POST /api/review/fix-prompt`

### Build Phase (`/api/build`)
- `POST /api/build/generate`
- `POST /api/build/from-plan`

### Deploy Phase (`/api/deploy`)
- `POST /api/deploy/checklist`
- `POST /api/deploy/runbook`

### Skills (`/api/skills`)
- `GET /api/skills/`
- `POST /api/skills/`
- `GET /api/skills/{id}`
- `PUT /api/skills/{id}`
- `DELETE /api/skills/{id}`
- `POST /api/skills/{id}/use`
- `POST /api/skills/detect`

### Token Controls (`/api/tokens`)
- `GET /api/tokens/usage`
- `GET /api/tokens/budget`
- `PUT /api/tokens/budget`
- `GET /api/tokens/models`
- `GET /api/tokens/users`
- `GET /api/tokens/users/{id}`
- `GET /api/tokens/teams`
- `GET /api/tokens/trends`
- `GET /api/tokens/check-limit`

### Model Selection (`/api/models`)
- `GET /api/models/`
- `GET /api/models/status`
- `POST /api/models/chat`

### Orchestration (`/api/orchestration`)
- `POST /api/orchestration/dispatch`
- `GET /api/orchestration/agents`

### Context Management (`/api/context`)
- `POST /api/context/save`
- `POST /api/context/load`
- `DELETE /api/context/clear/{page}`
- `GET /api/context/pages`
- `GET /api/context/recommendations/{page}`

### Analytics (`/api/analytics`)
- `GET /api/analytics/overview`
- `GET /api/analytics/token-dashboard`

### Settings (`/api/settings`)
- `GET /api/settings`
- `PUT /api/settings/{key}`

### Health
- `GET /healthz`

</details>

---

*Report generated from actual codebase analysis. All file paths and symbol references verified against source code.*
