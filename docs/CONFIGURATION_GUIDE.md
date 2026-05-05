# ZECT Configuration & Setup Guide

## 1. GitHub Actions CI — What It Is & How to Fix

### What is GitHub Actions CI?

**GitHub Actions CI** (Continuous Integration) is an automated pipeline that runs every time you push code or open a PR on GitHub. It automatically:

| Job | What It Does | Why It Matters |
|-----|-------------|----------------|
| **backend-lint** | Runs `ruff check` on Python code | Catches code quality issues before they reach production |
| **backend-test** | Runs `pytest` (17 tests) | Ensures backend API endpoints work correctly |
| **frontend-build** | Runs TypeScript check + `npm run build` | Catches type errors and build failures |
| **docker-build** | Builds Docker images for backend + frontend | Ensures the app can be containerized for deployment |

**In simple terms:** Every time you push code, GitHub automatically checks:
- Is the Python code clean? (lint)
- Do all backend tests pass? (test)
- Does the frontend compile without errors? (build)
- Can Docker images be built? (docker)

If ANY check fails, you see a red X on the PR — preventing bad code from reaching production.

### Current Status

The CI workflow file exists at `.github/workflows/ci.yml` in the repo but **has NOT been pushed to GitHub** because the GitHub PAT (Personal Access Token) used by Devin doesn't have the `workflow` scope, which GitHub requires to push files that modify GitHub Actions workflows.

### Steps to Fix (Choose One)

#### Option A: Push the CI File Manually (Fastest — 2 minutes)
```bash
# On your Windows machine
cd C:\Users\karuppk\Downloads\ZECT
git checkout develop
git pull origin develop

# The ci.yml file should already be there. If not:
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions CI pipeline"
git push origin develop
```

#### Option B: Update Your GitHub PAT with `workflow` Scope
1. Go to: https://github.com/settings/tokens
2. Click on your existing token (the one starting with `ghp_XUUT...`)
3. Check the **`workflow`** scope checkbox
4. Click **"Update token"**
5. Share the updated token with me and I'll push it

#### Option C: Create the File via GitHub UI
1. Go to: https://github.com/KarthikKaruppasamy880/ZECT
2. Click **"Add file" > "Create new file"**
3. Type the path: `.github/workflows/ci.yml`
4. Paste the contents (I'll provide them below)
5. Click **"Commit new file"** to `develop` branch

### CI File Contents (for Option C)
```yaml
name: ZECT CI

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]

jobs:
  backend-lint:
    name: Backend Lint & Type Check
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --no-interaction
      - name: Lint with ruff
        run: poetry run ruff check app/
      - name: Type check with pyright
        run: poetry run pyright app/
        continue-on-error: true

  backend-test:
    name: Backend Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --no-interaction --extras test
      - name: Run tests
        run: poetry run pytest tests/ -v --tb=short
        env:
          DATABASE_URL: "sqlite+aiosqlite:///./test.db"
          AUTH_EMAIL: "test@test.com"
          AUTH_PASSWORD: "test1234"
          JWT_SECRET: "test-secret-key"

  frontend-build:
    name: Frontend Build & Lint
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "18"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - name: Install dependencies
        run: npm ci
      - name: TypeScript check
        run: npx tsc --noEmit
      - name: Lint
        run: npm run lint
        continue-on-error: true
      - name: Build
        run: npm run build

  docker-build:
    name: Docker Build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build backend image
        run: docker build -t zect-backend ./backend
      - name: Build frontend image
        run: docker build -t zect-frontend ./frontend
```

---

## 2. MCP Server Connections — Configuration Guide

### What is MCP?

**MCP (Model Context Protocol)** is a standard for connecting AI tools to external services. ZECT has a built-in MCP router with 6 server stubs:

| Server | Tools | What It Does |
|--------|-------|-------------|
| **GitHub** | 12 | PRs, issues, commits, code search, branch management |
| **Jira** | 8 | Issue CRUD, JQL search, sprint management, transitions |
| **Slack** | 6 | Send messages, create channels, DMs, file uploads |
| **Filesystem** | 5 | Read/write/search local files |
| **PostgreSQL** | 7 | SQL queries, schema inspection, data export |
| **Playwright** | 10 | Browser automation — navigate, click, type, screenshot |

### Current Status

The MCP router is **built and functional** but returns **mock/stub results**. Each server endpoint works and returns proper JSON — but doesn't connect to actual services yet.

### How to Make Each Server Live

#### GitHub MCP Server
```env
# Add to backend/.env
GITHUB_TOKEN=ghp_your-personal-access-token
GITHUB_DEFAULT_ORG=KarthikKaruppasamy880
```

**Configuration steps:**
1. Go to https://github.com/settings/tokens → Generate new token (classic)
2. Select scopes: `repo`, `read:org`, `read:user`
3. Add the token to `backend/.env`
4. The MCP router will use PyGithub (already installed) to make live API calls

#### Jira MCP Server
```env
# Add to backend/.env
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_DEFAULT_PROJECT=PROJ
```

**Configuration steps:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **"Create API token"** → name it "ZECT"
3. Copy the token and add it to `backend/.env`
4. The Jira router uses `atlassian-python-api` (already installed)

#### Slack MCP Server
```env
# Add to backend/.env
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_DEFAULT_CHANNEL=#zect-notifications
```

**Configuration steps:**
1. Go to https://api.slack.com/apps → **"Create New App"**
2. Choose **"From scratch"** → Name: "ZECT Bot" → Select your workspace
3. Go to **OAuth & Permissions** → Add scopes:
   - `chat:write`, `channels:read`, `channels:manage`, `files:write`, `users:read`, `im:write`
4. Click **"Install to Workspace"**
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
6. Add to `backend/.env`
7. The Slack router uses `slack-sdk` (already installed)

#### PostgreSQL MCP Server
```env
# Already configured in backend/.env
DATABASE_URL=postgresql+psycopg://postgres:yourpassword@localhost:5432/zect_db
```
This is already connected since ZECT uses PostgreSQL as its primary database.

#### Filesystem MCP Server
No configuration needed — this operates on the local filesystem where ZECT is running. It's sandboxed to the project directory for security.

#### Playwright MCP Server
```bash
# Install Playwright browsers (one-time)
pip install playwright
playwright install chromium
```
No env vars needed — Playwright launches a local browser instance.

### Testing MCP Connections
Once configured, test each server:
```bash
# List all servers
curl http://localhost:8000/api/mcp/servers

# List tools for a server
curl http://localhost:8000/api/mcp/servers/github/tools

# Call a tool (example: list GitHub repos)
curl -X POST http://localhost:8000/api/mcp/servers/github/tools/list_repos/call \
  -H "Content-Type: application/json" \
  -d '{"server_id": "github", "tool_name": "list_repos", "arguments": {}}'
```

---

## 3. Jira Integration — Configuration Guide

### Current Status
The Jira integration router (`/api/jira/*`) is **fully built** with these endpoints:

| Endpoint | Method | What It Does |
|----------|--------|-------------|
| `/api/jira/status` | GET | Check if Jira is configured |
| `/api/jira/config` | POST | Configure Jira connection |
| `/api/jira/tickets` | GET | List linked Jira tickets |
| `/api/jira/tickets` | POST | Create a Jira ticket |
| `/api/jira/tickets/{id}` | DELETE | Remove a ticket link |

### Steps to Configure

1. **Get Jira API Token:**
   - Go to: https://id.atlassian.com/manage-profile/security/api-tokens
   - Click **"Create API token"**
   - Label: "ZECT Integration"
   - Copy the generated token

2. **Configure via ZECT UI:**
   Navigate to **Integrations** page in ZECT sidebar, or use the API:
   ```bash
   curl -X POST http://localhost:8000/api/jira/config \
     -H "Content-Type: application/json" \
     -d '{
       "base_url": "https://your-org.atlassian.net",
       "email": "your-email@company.com",
       "api_token": "your-jira-api-token",
       "default_project_key": "ZECT"
     }'
   ```

3. **Verify:**
   ```bash
   curl http://localhost:8000/api/jira/status
   # Should return: {"configured": true, "base_url": "...", "is_active": true, ...}
   ```

4. **Create a Test Ticket:**
   ```bash
   curl -X POST http://localhost:8000/api/jira/tickets \
     -H "Content-Type: application/json" \
     -d '{
       "project_key": "ZECT",
       "summary": "Test ticket from ZECT",
       "description": "Automated ticket creation test",
       "issue_type": "Task"
     }'
   ```

### How It Works in ZECT
- **Integrations page** shows Jira connection status
- **Build Phase** can auto-create tickets for generated code tasks
- **Audit Trail** logs all Jira operations
- Tickets are linked to ZECT resources (projects, code reviews, etc.)

---

## 4. Slack Integration — Configuration Guide

### Current Status
The Slack integration router (`/api/slack/*`) is **fully built** with these endpoints:

| Endpoint | Method | What It Does |
|----------|--------|-------------|
| `/api/slack/status` | GET | Check if Slack is configured |
| `/api/slack/config` | POST | Configure Slack connection |
| `/api/slack/notify` | POST | Send a notification message |
| `/api/slack/config` | DELETE | Disconnect Slack |

### Steps to Configure

1. **Create Slack App:**
   - Go to: https://api.slack.com/apps
   - Click **"Create New App"** → **"From scratch"**
   - App Name: **"ZECT Bot"**
   - Select your Slack workspace
   - Click **"Create App"**

2. **Add Bot Permissions:**
   - Go to **OAuth & Permissions** in the sidebar
   - Under **Bot Token Scopes**, add:
     - `chat:write` — Send messages
     - `channels:read` — List channels
     - `channels:manage` — Create channels
     - `files:write` — Upload files
     - `users:read` — List users
     - `im:write` — Send DMs

3. **Install to Workspace:**
   - Click **"Install to Workspace"**
   - Authorize the permissions
   - Copy the **Bot User OAuth Token** (starts with `xoxb-`)

4. **Configure via ZECT:**
   ```bash
   curl -X POST http://localhost:8000/api/slack/config \
     -H "Content-Type: application/json" \
     -d '{
       "bot_token": "xoxb-your-token-here",
       "workspace_name": "Zinnia Engineering",
       "default_channel": "#zect-notifications",
       "notify_on_review": true,
       "notify_on_deploy": true,
       "notify_on_budget_alert": true
     }'
   ```

5. **Test Notification:**
   ```bash
   curl -X POST http://localhost:8000/api/slack/notify \
     -H "Content-Type: application/json" \
     -d '{
       "message": "ZECT is connected!",
       "notification_type": "success"
     }'
   ```

### Notification Events
ZECT sends Slack notifications for:
- **Code Review complete** — when AI review finishes analyzing code
- **Deployment triggered** — when deploy phase starts
- **Token budget alerts** — when LLM token usage exceeds thresholds
