# ZECT Management Guide — Complete Workflow Reference

**Zinnia Engineering Control Tower (ZECT)**  
**Version:** 2.0 — Full Implementation Plan Edition  
**Last Updated:** May 7, 2026

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard](#2-dashboard)
3. [Ask Mode](#3-ask-mode)
4. [Plan Mode](#4-plan-mode)
5. [Build Phase](#5-build-phase)
6. [Code Review Engine](#6-code-review-engine)
7. [Knowledge Base](#7-knowledge-base)
8. [Playbooks](#8-playbooks)
9. [Scheduled Tasks](#9-scheduled-tasks)
10. [Secrets Manager](#10-secrets-manager)
11. [Code Index](#11-code-index)
12. [Session Insights](#12-session-insights)
13. [Conversations](#13-conversations)
14. [Settings](#14-settings)
15. [Token Controls](#15-token-controls)
16. [App Runner](#16-app-runner)
17. [Other Sidebar Pages](#17-other-sidebar-pages)
18. [Backend API Reference](#18-backend-api-reference)
19. [Database & Models](#19-database--models)
20. [Deployment & Setup](#20-deployment--setup)

---

## 1. Getting Started

### Prerequisites
- **Node.js 18+** (for frontend)
- **Python 3.10+** (for backend)
- **SQLite** (default) or **PostgreSQL** (production)

### Quick Start (Development)

```bash
# Clone the repo
git clone https://github.com/KarthikKaruppasamy880/ZECT.git
cd ZECT

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[test]"
cp .env.example .env      # Edit with your credentials
uvicorn app.main:app --reload --port 8001

# Frontend (new terminal)
cd frontend
npm install
VITE_API_URL=http://localhost:8001 npx vite --port 5173
```

### Environment Variables (.env)
```
DATABASE_URL=sqlite:///./zect.db
GITHUB_TOKEN=ghp_your_token_here
OPENAI_API_KEY=sk-your_key_here
ZECT_USERNAME=your.email@zinnia.com
ZECT_PASSWORD=YourPassword123
ZECT_ENCRYPT_KEY=your-fernet-key   # For secrets encryption
```

### Login
1. Open `http://localhost:5173` in your browser
2. Enter your email and password (from `.env` file)
3. Click **Sign In** — you'll land on the Dashboard

---

## 2. Dashboard

**Route:** `/`  
**Purpose:** Overview of all engineering projects, token usage, and stage distribution.

### What You See
- **Stats Cards:** Total Projects, Active Projects, Avg Token Savings, Risk Alerts
- **Token Usage Control:** Total API Calls, Total Tokens, Estimated Cost
- **Stage Distribution:** Visual breakdown of projects across Ask/Plan/Build/Review/Deploy
- **Projects Grid:** All projects with completion percentages and stage badges

### How to Use
1. **View project status** — Each card shows the project name, current stage, description, team, and completion %
2. **Click a project** — Opens the project detail view
3. **Click "View all"** — Goes to the full Projects page
4. **Token Usage "Details"** — Expands to show per-model breakdown

---

## 3. Ask Mode

**Route:** `/ask`  
**Purpose:** Ask any engineering question — architecture, debugging, code review, best practices.

### What You See
- **Left Panel:** Conversation History sidebar (past sessions)
- **Main Panel:** Chat interface with model selector, file attachment, prompt tips
- **Quick Prompts:** Pre-built questions to get started

### Workflow
1. **Select an AI Model** — Top-right dropdown: GPT-4o Mini (default), GPT-4o, GPT-3.5 Turbo, Claude 3.5 Sonnet, Claude 3 Haiku
2. **Attach Context** (optional) — Click "+ Add files, repos, snippets" to add relevant code for context
3. **Type your question** — Or click a quick prompt like "How should I structure a microservices migration?"
4. **Press Enter** — The AI responds with a detailed answer
5. **Conversation History** — Previous sessions appear in the left sidebar. Click to resume any conversation.

### Key Features
- **Model Selector:** 5 models with quality/speed indicators and pricing
- **File Attachments:** Add code files, repo URLs, or code snippets for context
- **Prompt Tips:** Collapsible section with tips for better prompts
- **Conversation Persistence:** All conversations saved to DB and accessible from sidebar

---

## 4. Plan Mode

**Route:** `/plan`  
**Purpose:** Generate detailed, phased engineering plans for any project or feature.

### What You See
- **Left Panel:** Conversation History sidebar
- **Main Panel:** Project description input, model selector with pricing, file attachment, advanced options

### Workflow
1. **Select Model** — Choose AI model (pricing shown: e.g., $0.00015/1K in)
2. **Describe Your Project** — Enter a detailed description in the textarea
3. **Attach Context** (optional) — Add files/repos/snippets for the AI to reference
4. **Show Advanced Options** (optional) — Additional configuration for plan output format
5. **Click "Generate Engineering Plan"** — AI creates a phased plan with milestones, tasks, dependencies
6. **Review & Iterate** — Ask follow-up questions to refine the plan

### Output Includes
- Phased development timeline
- Technology stack recommendations
- Risk assessment
- Resource allocation suggestions
- Dependency mapping

---

## 5. Build Phase

**Route:** `/build`  
**Purpose:** Generate production-ready code from plan steps using AI.

### What You See
- **Left Panel:** Conversation History sidebar
- **Main Panel:** Plan step input, tech stack, target file path, model selector
- **Right Panel:** Context Files, Auto-Fix Loop, Create PR sections
- **Bottom:** Quick Templates (6 pre-built code generation templates)

### Workflow
1. **Describe the Plan Step** — Enter what code you want generated (e.g., "Create a REST API endpoint for user authentication")
2. **Set Tech Stack** (optional) — e.g., "TypeScript, React, FastAPI"
3. **Set Target File Path** (optional) — e.g., "src/api/auth.ts"
4. **Select Model** — With pricing info
5. **Add Context Files** — Click "+" to add existing code for reference
6. **Click "Generate Code"** — AI produces production-ready code
7. **Auto-Fix Loop** — Expand to run lint/test/fix cycles automatically
8. **Create PR** — Expand to create a GitHub PR directly from generated code

### Quick Templates
- Create a REST API endpoint with CRUD operations
- Build a React component with state management
- Write unit tests with mocking
- Create a database migration script
- Build a CI/CD pipeline (GitHub Actions)
- Create auth middleware with JWT

---

## 6. Code Review Engine

**Route:** `/code-review`  
**Purpose:** AI-powered code analysis — identifies bugs, vulnerabilities, performance issues.

### 5 Tabs

#### Tab 1: PR Review
1. Enter **Repository Owner** (e.g., KarthikKaruppasamy880)
2. Enter **Repository Name** (e.g., ZECT)
3. Enter **PR Number**
4. Optionally check "Also evaluate Rules Engine rules"
5. Click **"Run ZECT Review"** — AI analyzes the PR diff
6. Click **"Review & Post to GitHub"** — Posts inline comments directly to the PR

#### Tab 2: Snippet Review
1. Paste code into the textarea
2. Select the language
3. Click review — AI analyzes the snippet for issues

#### Tab 3: Full Repo Scan
1. Enter repo owner/name
2. Click scan — AI performs a comprehensive codebase analysis
3. Results include: security vulnerabilities, performance issues, code quality

#### Tab 4: Auto-Fix Loop
1. Enter repo details
2. Click "Start Auto-Fix" — AI identifies issues and generates fixes
3. Review each fix before applying

#### Tab 5: Webhook Configuration
1. Set up a webhook URL for automatic PR reviews
2. Configure trigger events (PR opened, PR updated, etc.)
3. Set review rules and thresholds

---

## 7. Knowledge Base

**Route:** `/knowledge-base`  
**Purpose:** Persistent tips, instructions, project notes — your team's engineering knowledge.

### What You See
- **Search Bar** — Search across all entries by keyword
- **Category Filter** — All Categories, General, Coding, Review, Deploy, Architecture, Testing, Debug
- **Entry Cards** — Each showing title, category, content preview, timestamps

### Workflow

#### Create a New Entry
1. Click **"+ New Entry"** (top-right purple button)
2. Fill in:
   - **Title** — e.g., "How to handle JWT token refresh"
   - **Category** — Select from dropdown (Coding, Review, Deploy, etc.)
   - **Content** — Markdown-supported text with your knowledge
   - **Tags** — Optional comma-separated tags for searchability
3. Click **Save** — Entry is stored in the database

#### Search & Filter
1. Type in the search bar to filter by keyword
2. Use the category dropdown to narrow by type
3. Results update in real-time

#### Edit / Delete
1. Click on an entry to expand it
2. Click **Edit** to modify, or **Delete** to remove
3. All changes are persisted to the database

### API Endpoints
- `GET /api/knowledge` — List all entries (with pagination)
- `POST /api/knowledge` — Create new entry
- `PUT /api/knowledge/{id}` — Update entry
- `DELETE /api/knowledge/{id}` — Delete entry
- `GET /api/knowledge/search?q=term` — Full-text search
- `GET /api/knowledge/categories` — List all categories

---

## 8. Playbooks

**Route:** `/playbooks`  
**Purpose:** Reusable prompt templates and multi-step automated workflows.

### What You See
- **Category Tabs** — All, General, Onboarding, Review, Deploy, Debug, Migration, Testing
- **Playbook Cards** — Name, description, category, step count, last run info
- **"+ New Playbook"** button

### Workflow

#### Create a Playbook
1. Click **"+ New Playbook"**
2. Fill in:
   - **Name** — e.g., "New Developer Onboarding"
   - **Description** — What this playbook does
   - **Category** — Select from tabs
   - **Steps** — Add ordered steps, each with:
     - Step title
     - Prompt template (with `{{variable}}` placeholders)
     - Expected output description
3. Click **Save**

#### Run a Playbook
1. Click a playbook card to open it
2. Click **"Run"** — Executes all steps in sequence
3. View run history with timestamps and results
4. Each run creates a record in the database

#### Edit / Delete
1. Open a playbook
2. Click Edit to modify steps/metadata
3. Click Delete to remove

### API Endpoints
- `GET /api/playbooks` — List all playbooks
- `POST /api/playbooks` — Create new playbook
- `PUT /api/playbooks/{id}` — Update playbook
- `DELETE /api/playbooks/{id}` — Delete playbook
- `POST /api/playbooks/{id}/run` — Execute a playbook
- `GET /api/playbooks/{id}/runs` — Get run history

---

## 9. Scheduled Tasks

**Route:** `/scheduled-tasks`  
**Purpose:** Cron-based recurring automated tasks.

### What You See
- **"+ New Schedule"** button (orange)
- **Schedule Cards** — Name, cron expression, next run, status (active/paused), last run result

### Workflow

#### Create a Schedule
1. Click **"+ New Schedule"**
2. Fill in:
   - **Name** — e.g., "Nightly Security Scan"
   - **Cron Expression** — e.g., `0 2 * * *` (daily at 2 AM)
   - **Task Type** — What to execute (playbook, review, scan, etc.)
   - **Configuration** — Task-specific settings
3. Click **Save**

#### Manage Schedules
1. **Toggle** — Enable/disable a schedule without deleting it
2. **Manual Trigger** — Run the task immediately outside the schedule
3. **View Runs** — See execution history with success/failure status
4. **Edit/Delete** — Modify or remove schedules

### API Endpoints
- `GET /api/schedules` — List all schedules
- `POST /api/schedules` — Create new schedule
- `PUT /api/schedules/{id}` — Update schedule
- `DELETE /api/schedules/{id}` — Delete schedule
- `POST /api/schedules/{id}/toggle` — Enable/disable
- `POST /api/schedules/{id}/trigger` — Manual execution

---

## 10. Secrets Manager

**Route:** `/secrets`  
**Purpose:** Encrypted storage for API keys, tokens, and credentials.

### Security
- **Fernet symmetric encryption** — All secret values are encrypted at rest
- **ZECT_ENCRYPT_KEY** — Set in `.env` for production; auto-generated if not set
- Values are never stored in plaintext in the database

### What You See
- **Encryption Notice** — Yellow banner explaining Fernet encryption
- **"+ Add Secret"** button (green)
- **Secret Cards** — Name, scope, masked value, timestamps

### Workflow

#### Add a Secret
1. Click **"+ Add Secret"**
2. Fill in:
   - **Name** — e.g., "OPENAI_API_KEY"
   - **Value** — The actual secret (will be encrypted)
   - **Scope** — org, user, or repo (determines visibility)
   - **Description** (optional) — What this secret is for
3. Click **Save** — Value is Fernet-encrypted before storage

#### View / Rotate / Delete
1. Secret values are always masked (shown as `••••••••`)
2. Click **Rotate** to generate/set a new value
3. Click **Delete** to remove (irreversible)

### Scopes
- **org** — Available to all users in the organization
- **user** — Personal to the current user only
- **repo** — Scoped to a specific repository

### API Endpoints
- `GET /api/secrets` — List all secrets (values masked)
- `POST /api/secrets` — Create new encrypted secret
- `DELETE /api/secrets/{id}` — Delete secret
- `POST /api/secrets/{id}/rotate` — Rotate secret value

---

## 11. Code Index

**Route:** `/code-index`  
**Purpose:** Search functions, classes, variables across your codebase.

### What You See
- **Search Bar** — Type to search symbols
- **Type Filter** — All Types, Function, Class, Variable, Import, Interface, Type, Method
- **Language Filter** — All Languages, Python, TypeScript, JavaScript, Java, Go, Rust, Ruby, C, C++
- **"Stats"** button — View indexing statistics
- **"Index Repo"** button — Trigger repository indexing

### Workflow

#### Index a Repository
1. Click **"Index Repo"** (teal button)
2. Enter the repository path on disk
3. Click **Start Indexing** — The backend parses all source files and extracts symbols
4. Progress is shown in real-time

#### Search Symbols
1. Type a symbol name (e.g., "authenticate")
2. Optionally filter by type (Function, Class, etc.)
3. Optionally filter by language (Python, TypeScript, etc.)
4. Click **Search** — Results show file path, line number, symbol type, and code preview

#### View Stats
1. Click **"Stats"** — Shows total symbols, breakdown by type and language

### API Endpoints
- `GET /api/code-index/search?q=term&type=function&language=python` — Search symbols
- `POST /api/code-index/index` — Index a repository
- `GET /api/code-index/stats` — Get indexing statistics
- `GET /api/code-index/file/{path}` — Get symbols in a specific file

---

## 12. Session Insights

**Route:** `/session-insights`  
**Purpose:** Usage analytics, cost tracking, and quality metrics.

### What You See
- **Time Range Selector** — Last 7/14/30/90 days
- **4 Metric Cards:**
  - Total Sessions (with active count)
  - Total Tokens (with request count)
  - Total Cost (with per-request average)
  - Quality Score (with review count)
- **Model Usage** — Breakdown of which AI models were used and how much
- **Feature Usage** — Which ZECT features are most used

### Workflow
1. **Select Time Range** — Choose Last 7/14/30/90 days from dropdown
2. **Review Metrics** — All 4 cards update automatically
3. **Analyze Model Usage** — See which models consume the most tokens
4. **Track Feature Adoption** — See which ZECT features your team uses most

### API Endpoints
- `GET /api/session-insights/overview?days=30` — Summary metrics
- `GET /api/session-insights/sessions` — Session list
- `GET /api/session-insights/model-usage?days=30` — Per-model breakdown
- `GET /api/session-insights/feature-usage?days=30` — Per-feature breakdown
- `GET /api/session-insights/daily-breakdown?days=30` — Day-by-day stats

---

## 13. Conversations

**Route:** `/conversations`  
**Purpose:** Session history across all modes (Ask, Plan, Build, Review, Deploy).

### What You See
- **Mode Tabs** — All, Ask, Plan, Build, Review, Deploy
- **"+ New Conversation"** button
- **"Show Archived"** toggle
- **Left Panel** — Conversation list with titles and timestamps
- **Right Panel** — Selected conversation's message thread

### Workflow

#### Browse Conversations
1. Click a **mode tab** to filter (e.g., "Ask" shows only Ask Mode conversations)
2. Click a conversation in the left panel to view its messages in the right panel
3. Toggle **"Show Archived"** to include archived conversations

#### Create New Conversation
1. Click **"+ New Conversation"**
2. Select the mode and enter a title
3. Start sending messages

#### Archive / Delete
1. Open a conversation
2. Click **Archive** to hide it (can be restored)
3. Click **Delete** to permanently remove

### API Endpoints
- `GET /api/conversations?mode=ask` — List conversations (with mode filter)
- `POST /api/conversations` — Create new conversation
- `PUT /api/conversations/{id}` — Update conversation
- `DELETE /api/conversations/{id}` — Delete conversation
- `GET /api/conversations/{id}/messages` — Get messages in a conversation
- `POST /api/conversations/{id}/messages` — Add a message

---

## 14. Settings

**Route:** `/settings`  
**Purpose:** Configure ZECT behavior and integrations.

### Sections

#### API Keys (Top Row)
- **GitHub API Key** — Your personal access token for PR review, code access
- **OpenAI API Key** — Powers Ask Mode, Plan Mode, and Blueprint AI
- **Token Usage** — View usage log with per-request details

#### Secrets Manager Card
- Quick link to the full Secrets Manager page (`/secrets`)
- Shows encrypted credential count

#### Feature Toggles (6 toggles)
1. **Automated Code Review** — Auto-run reviews when build phase completes
2. **Token Usage Tracking** — Track AI token consumption
3. **Deployment Gate Enforcement** — Block deploys with unresolved findings
4. **Risk Alert Notifications** — Slack/email alerts for risk detection
5. **Auto-Generate Plan from Requirements** — AI plans from approved requirements
6. **Session Context Memory** — Persist context across AI sessions

#### Configuration Options (4 dropdowns)
1. **Default Starting Stage** — Ask Mode / Plan Mode / Build Phase
2. **Minimum Review Severity** — Critical / High / Medium / Low / Info
3. **Deployment Approval Mode** — Anyone / Tech Lead / Tech Lead + PM / VP Engineering
4. **Monthly Token Budget Alert** — 50% / 70% / 80% / 90% / No alert

---

## 15. Token Controls

**Route:** `/token-controls`  
**Purpose:** Per-user monitoring, budgets, and model spending analytics.

### 5 Tabs

#### Overview
- 4 metric cards: Total Calls, Total Tokens, Total Cost, Today's Tokens
- Model Breakdown table
- Active Users list

#### User Activity
- Per-user token consumption
- Request history with timestamps

#### Teams
- Team-level aggregated token usage
- Budget allocation per team

#### Budget
- Set monthly token budgets
- Alert thresholds
- Budget vs actual tracking

#### Trends
- Usage trends over time
- Model adoption curves
- Cost forecasting

---

## 16. App Runner

**Route:** `/app-runner`  
**Purpose:** Configure, run, and test applications directly inside ZECT.

### 3 Tabs

#### Terminal
- **ZECT Terminal** — Full command-line interface in the browser
- **Working Directory** — Set the directory for command execution
- **Run** — Execute one-shot commands (e.g., `npm test`)
- **Start Process** — Launch long-running servers (e.g., `npm run dev`)
- **Live Preview** — Enter a URL (e.g., `http://localhost:5173`) to see your app

#### Configure
- Set environment variables for the runner
- Configure startup commands
- Set working directory defaults

#### Processes
- View running background processes
- Stop/restart processes
- View process logs

---

## 17. Other Sidebar Pages

### Navigation Section
| Page | Route | Description |
|------|-------|-------------|
| Projects | `/projects` | View/manage all engineering projects |
| Orchestration | `/orchestration` | Multi-project workflow orchestration |
| Repo Analysis | `/repo-analysis` | AI-powered repository analysis |
| Blueprint | `/blueprint` | Architecture design and API planning |
| Doc Generator | `/doc-generator` | Auto-generate documentation from code |
| Analytics | `/analytics` | Project-level analytics dashboard |
| Docs Center | `/docs` | Browse generated documentation |

### Workflow Stages Section
| Page | Route | Description |
|------|-------|-------------|
| Review Phase | `/review` | Code review workflow management |
| Deployment | `/deploy` | Deployment pipeline management |
| Skill Library | `/skills` | Browse and manage reusable skills |
| File Explorer | `/file-explorer` | Browse project files in-browser |
| Git Operations | `/git-ops` | Git commands and branch management |
| CI Monitor | `/ci-monitor` | Monitor CI/CD pipeline runs |

### Zinnia Intelligence Section
| Page | Route | Description |
|------|-------|-------------|
| Memory System | `/memory` | Persistent context and recall |
| Dream Engine | `/dream-engine` | Background insight generation |
| Data Layer | `/data-layer` | Data pipeline management |
| Data Flywheel | `/data-flywheel` | Learning loop optimization |
| Permissions | `/permissions` | Access control management |
| Transfer & Onboard | `/transfer` | Knowledge transfer workflows |
| Skills Engine | `/skills-engine` | AI skill development |

### Enterprise Section
| Page | Route | Description |
|------|-------|-------------|
| Audit Trail | `/audit-trail` | Operation logging and compliance |
| Rules Engine | `/rules` | Custom review rules |
| Integrations | `/integrations` | Jira, Slack, and other integrations |
| Export/Share | `/export` | Export sessions and reports |
| Output History | `/output-history` | Browse all AI-generated outputs |

---

## 18. Backend API Reference

### Base URL
```
http://localhost:8001/api
```

### Authentication
```
POST /api/auth/login
Body: { "username": "email", "password": "pass" }
Response: { "access_token": "...", "token_type": "bearer" }
```

### Full Route Map
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/conversations` | List conversations |
| POST | `/api/conversations` | Create conversation |
| PUT | `/api/conversations/{id}` | Update conversation |
| DELETE | `/api/conversations/{id}` | Delete conversation |
| GET | `/api/conversations/{id}/messages` | Get messages |
| POST | `/api/conversations/{id}/messages` | Add message |
| GET | `/api/knowledge` | List knowledge entries |
| POST | `/api/knowledge` | Create entry |
| PUT | `/api/knowledge/{id}` | Update entry |
| DELETE | `/api/knowledge/{id}` | Delete entry |
| GET | `/api/knowledge/search?q=` | Search entries |
| GET | `/api/playbooks` | List playbooks |
| POST | `/api/playbooks` | Create playbook |
| PUT | `/api/playbooks/{id}` | Update playbook |
| DELETE | `/api/playbooks/{id}` | Delete playbook |
| POST | `/api/playbooks/{id}/run` | Execute playbook |
| GET | `/api/playbooks/{id}/runs` | Run history |
| GET | `/api/schedules` | List schedules |
| POST | `/api/schedules` | Create schedule |
| PUT | `/api/schedules/{id}` | Update schedule |
| DELETE | `/api/schedules/{id}` | Delete schedule |
| POST | `/api/schedules/{id}/toggle` | Toggle schedule |
| POST | `/api/schedules/{id}/trigger` | Manual trigger |
| GET | `/api/secrets` | List secrets (masked) |
| POST | `/api/secrets` | Create encrypted secret |
| DELETE | `/api/secrets/{id}` | Delete secret |
| POST | `/api/secrets/{id}/rotate` | Rotate secret |
| GET | `/api/code-index/search` | Search symbols |
| POST | `/api/code-index/index` | Index repository |
| GET | `/api/code-index/stats` | Index statistics |
| GET | `/api/session-insights/overview` | Summary metrics |
| GET | `/api/session-insights/model-usage` | Model breakdown |
| GET | `/api/session-insights/feature-usage` | Feature breakdown |

---

## 19. Database & Models

### New Models (from Implementation Plan)

```
Conversation
├── id, title, mode (ask/plan/build/review/deploy)
├── is_archived, created_at, updated_at
└── messages → ConversationMessage[]

ConversationMessage
├── id, conversation_id, role (user/assistant/system)
├── content, model_used, tokens_used
└── created_at

KnowledgeEntry
├── id, title, category, content
├── tags (JSON), is_pinned
└── created_at, updated_at

Playbook
├── id, name, description, category
├── is_active
├── steps → PlaybookStep[]
└── created_at, updated_at

PlaybookStep
├── id, playbook_id, order, title
├── prompt_template, expected_output
└── created_at

Schedule
├── id, name, cron_expression
├── task_type, config (JSON)
├── is_enabled, last_run_at, next_run_at
└── created_at, updated_at

SecretEntry
├── id, name, encrypted_value
├── scope (org/user/repo), description
└── created_at, updated_at

CodeSymbol
├── id, name, symbol_type, language
├── file_path, line_number, signature
├── repo_path
└── indexed_at
```

---

## 20. Deployment & Setup

### Docker Compose (Recommended for Production)
```bash
docker-compose up -d
# Backend: http://localhost:8001
# Frontend: http://localhost:5173
```

### PostgreSQL (Production)
1. Install PostgreSQL
2. Create database: `CREATE DATABASE zect;`
3. Update `.env`: `DATABASE_URL=postgresql://user:pass@localhost:5432/zect`
4. The app auto-creates tables on first start

### AWS EC2 Deployment
1. Launch Ubuntu 22.04 instance
2. Install Node.js 18+, Python 3.10+
3. Clone repo, install dependencies
4. Use `systemd` services for backend/frontend
5. Configure Nginx reverse proxy
6. Set up SSL with Let's Encrypt

### Sync Branches
```bash
# Always work on develop, merge to main when ready
git checkout develop
git pull origin develop

# When ready for production
git checkout main
git merge develop
git push origin main
```

---

*Generated by ZECT — Zinnia Engineering Control Tower*
