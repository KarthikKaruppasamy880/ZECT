# ZECT User Manual

## Zinnia Engineering Control Tower - Complete User Guide

**Version:** 2.0
**Last Updated:** April 2026
**Audience:** Zinnia Engineering Teams

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Login & Authentication](#2-login--authentication)
3. [Sidebar Navigation Overview](#3-sidebar-navigation-overview)
4. [Navigation Section](#4-navigation-section)
5. [Workflow Stages Section](#5-workflow-stages-section)
6. [Zinnia Intelligence Section](#6-zinnia-intelligence-section)
7. [Enterprise Section](#7-enterprise-section)
8. [Keyboard Shortcuts & Tips](#8-keyboard-shortcuts--tips)
9. [API Configuration](#9-api-configuration)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Getting Started

### What is ZECT?

ZECT (Zinnia Engineering Control Tower) is a web-based internal platform that provides:

- **Code review** with AI-powered analysis (bugs, vulnerabilities, performance, architecture)
- **Project orchestration** across the full software delivery lifecycle (Ask, Plan, Build, Review, Deploy)
- **Token/cost tracking** for all AI-powered features with per-user budgets
- **Zinnia Intelligence** -- a 4-layer memory system, dream engine, data flywheel, permissions protocol, and skills engine
- **Enterprise controls** -- audit trail, rules engine, integrations, and export/share

### Prerequisites

| Requirement | Details |
|---|---|
| Node.js | v18 or higher |
| Python | 3.10 or higher |
| Database | SQLite (default) or PostgreSQL |
| LLM API Key | OpenAI, Anthropic, or Ollama (for AI features) |
| Browser | Chrome, Firefox, Edge, or Safari (latest) |

### Installation

```bash
# Clone the repository
git clone https://github.com/KarthikKaruppasamy880/ZECT.git
cd ZECT

# Start the backend
cd backend
pip install -r requirements.txt
ZECT_USERNAME="your-email" ZECT_PASSWORD="your-password" uvicorn app.main:app --host 0.0.0.0 --port 8001

# Start the frontend (in a new terminal)
cd frontend
npm install
VITE_API_URL=http://localhost:8001 npm run dev -- --port 5173
```

Open `http://localhost:5173` in your browser.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ZECT_USERNAME` | Yes | Login username (email) |
| `ZECT_PASSWORD` | Yes | Login password |
| `VITE_API_URL` | Yes | Backend API URL (e.g., `http://localhost:8001`) |
| `OPENAI_API_KEY` | For AI features | OpenAI API key for code review, ask mode, plan mode |
| `DATABASE_URL` | Optional | PostgreSQL connection string (defaults to SQLite) |

---

## 2. Login & Authentication

### Login Screen

When you open ZECT, you are presented with a login screen:

1. Enter your **email address** (the value set in `ZECT_USERNAME`)
2. Enter your **password** (the value set in `ZECT_PASSWORD`)
3. Click **Sign In**

### Session Management

- Your session token is stored in the browser's `localStorage` as `zect_token`
- Sessions persist across browser refreshes
- To sign out, click the **Sign Out** button at the bottom of the sidebar

### Token Verification

On each page load, ZECT verifies your token with the backend. If the token is expired or invalid, you are automatically redirected to the login screen.

---

## 3. Sidebar Navigation Overview

The ZECT sidebar is divided into **4 sections** with a total of **33 navigation items**:

| Section | Items | Purpose |
|---|---|---|
| **Navigation** | 10 items | Core platform features |
| **Workflow Stages** | 11 items | Software delivery lifecycle |
| **Zinnia Intelligence** | 7 items | AI memory, learning, and governance |
| **Enterprise** | 5 items | Audit, compliance, and integrations |

### Sidebar Controls

- **Collapse/Expand**: Click the chevron icon at the top-right of the sidebar, or use `Ctrl+B` (Windows/Linux) / `Cmd+B` (Mac)
- **Collapsed Mode**: Shows only icons; hover over any icon to see the label tooltip
- **Mobile**: On screens smaller than 768px, the sidebar becomes an overlay. Tap the hamburger menu icon (top-left) to open/close
- **Active Page**: The current page is highlighted with a white text + dark background in the sidebar

---

## 4. Navigation Section

### 4.1 Dashboard

**Path:** `/` | **Icon:** LayoutDashboard

The Dashboard is your home screen. It shows:

- **Metric Cards**: Total Projects, Active Projects, Avg Token Savings, Risk Alerts
- **Token Usage Control Panel**: Total API Calls, Total Tokens, Estimated Cost
  - Click **Details** to expand the breakdown by feature, by model, and recent activity table
- **Stage Distribution Chart**: Visual bar chart showing how many projects are in each stage (Ask, Plan, Build, Review, Deploy)
- **Projects Grid**: The 6 most recent projects with name, stage badge, team, repo count, and completion percentage
  - Click **View all** to go to the Projects page

### 4.2 Projects

**Path:** `/projects` | **Icon:** FolderKanban

Manage all your engineering projects:

- **Project List**: All projects displayed as cards with name, description, current stage, team, and completion percentage
- **Create New Project**: Click the "New Project" button to create a project
  - Fill in: Name, Description, Team, Repos (comma-separated), Current Stage
- **Project Detail** (`/projects/:id`): Click any project card to see:
  - Project metadata (team, repos, stage, dates)
  - Stage progression timeline
  - PR viewer for linked repositories
  - Risk alerts and action items

### 4.3 Orchestration

**Path:** `/orchestration` | **Icon:** GitBranch

Visualize and manage the project delivery pipeline:

- **Pipeline View**: See all projects organized by their current stage
- **Stage Transitions**: Move projects between stages (Ask -> Plan -> Build -> Review -> Deploy)
- **Dependencies**: View cross-project dependencies
- **Timeline**: Gantt-style view of project timelines

### 4.4 Repo Analysis

**Path:** `/repo-analysis` | **Icon:** Microscope

Analyze any GitHub repository:

1. Enter the **Owner** and **Repo** name
2. Click **Analyze**
3. View the results:
   - Repository structure and size
   - Tech stack detection
   - Code quality metrics
   - Dependency analysis
   - Security scan results

### 4.5 Blueprint

**Path:** `/blueprint` | **Icon:** Sparkles

AI-powered project blueprint generator:

1. Describe your project requirements in the text area
2. Optionally attach reference files
3. Select the AI model (defaults to `gpt-4o-mini`)
4. Click **Generate Blueprint**
5. View the generated:
   - Architecture design
   - Component breakdown
   - API schema
   - Database schema
   - Implementation roadmap

**Token Usage**: Each blueprint generation uses tokens. The cost is tracked in Token Controls.

### 4.6 Doc Generator

**Path:** `/doc-generator` | **Icon:** BookOpen

Generate documentation from your codebase:

1. Enter the **Owner** and **Repo**
2. Select documentation type:
   - API Documentation
   - User Guide
   - Architecture Overview
   - README
3. Click **Generate**
4. View, copy, or download the generated documentation

### 4.7 Code Review

**Path:** `/code-review` | **Icon:** ShieldCheck

AI-powered code review engine with 5 modes:

#### PR Review Mode
1. Enter **Owner**, **Repo**, and **PR Number**
2. Optionally enable **Rules Engine** toggle
3. Click **Run Review**
4. View results:
   - **Quality Score Ring**: 0-100 score with color coding (green=80+, yellow=60+, red=<40)
   - **Severity Summary**: Critical, High, Medium, Low, Info counts
   - **Category Breakdown**: Bugs, Vulnerabilities, Performance, Code Quality, Architecture, Best Practices
   - **Findings List**: Expandable cards with description, code snippet, and fix suggestion
   - **Get Prompt**: Copy a fix prompt to paste into any AI tool

#### Snippet Review Mode
1. Paste code into the text area
2. Select the language
3. Click **Run Review**
4. View findings with suggestions

#### Full Repo Scan Mode
1. Enter **Owner** and **Repo**
2. Optionally enter branch name and file patterns (comma-separated)
3. Click **Run Review**
4. View comprehensive repo-wide analysis

#### Auto-Fix Loop Mode
1. Enter **Owner**, **Repo**, and **PR Number**
2. Set **Max Iterations** (default: 3)
3. Toggle **Auto-Comment** on/off
4. Click **Run Review**
5. ZECT iteratively reviews and suggests fixes until quality passes or max iterations reached

#### Webhook Configuration Mode
1. Enter **Owner** and **Repo**
2. Toggle **Enabled**, **Auto-Review**, **Auto-Comment**
3. Set webhook secret
4. Click **Save** to configure automatic PR reviews

#### Inline Review Features
- **Review & Post Inline**: Runs review and posts findings as inline comments directly on the GitHub PR
- **Post Custom Comment**: Add your own comments with optional file path and line number
- **View Comments**: See all existing PR comments

### 4.8 Analytics

**Path:** `/analytics` | **Icon:** BarChart3

View engineering analytics:

- **Overview Metrics**: Total projects, active projects, completed, at-risk
- **Stage Distribution**: Projects by stage
- **Token Savings**: AI efficiency metrics
- **Risk Alerts**: Outstanding risk alerts across projects
- **Trend Charts**: Project velocity over time

### 4.9 Docs Center

**Path:** `/docs` | **Icon:** FileText

Central documentation hub:

- Browse all project documentation
- Search across docs
- View auto-generated API docs
- Access team runbooks and guides

### 4.10 Settings

**Path:** `/settings` | **Icon:** Settings

Platform configuration:

- **Theme**: Toggle between Light and Dark mode
- **API Configuration**: Set LLM API keys, model preferences
- **Notifications**: Configure alert preferences
- **Profile**: View and edit your profile
- **Database**: View database connection info

---

## 5. Workflow Stages Section

### 5.1 Ask Mode

**Path:** `/ask` | **Icon:** MessageSquare

Chat-based interface for asking questions about your codebase:

1. Select or enter the **repository** context
2. Optionally attach files for context
3. Type your question in the chat input
4. Select the AI **model** from the dropdown
5. Press **Send** or hit Enter
6. View the AI response with code snippets, explanations, and references

**Features:**
- Conversation history persists during the session
- File attachment panel for providing code context
- Model selector (GPT-4o-mini, GPT-4o, Claude 3.5 Sonnet, etc.)
- Copy response to clipboard
- Token usage displayed per message

### 5.2 Plan Mode

**Path:** `/plan` | **Icon:** ClipboardList

Generate implementation plans from requirements:

1. Describe what you want to build
2. Optionally attach reference files
3. Select the AI model
4. Click **Generate Plan**
5. View the structured plan:
   - Task breakdown with subtasks
   - Effort estimates
   - Dependencies
   - Risk assessment
   - Suggested architecture

### 5.3 Build Phase

**Path:** `/build` | **Icon:** Hammer

Track and manage active builds:

- **Active Builds**: View in-progress builds with status
- **Build Queue**: Pending build requests
- **Build History**: Past builds with outcomes
- File attachment panel for providing build context
- Model selector for AI-assisted builds
- Token usage tracking per build

### 5.4 Review Phase

**Path:** `/review` | **Icon:** Shield

Manage code reviews:

- **Pending Reviews**: PRs awaiting review
- **In-Progress**: Currently being reviewed
- **Completed**: Past reviews with quality scores
- Quick-link to the full Code Review engine

### 5.5 Deployment

**Path:** `/deploy` | **Icon:** Rocket

Deployment management:

- **Deploy Queue**: Pending deployments
- **Active Deployments**: Currently deploying
- **Deployment History**: Past deployments with status
- **Rollback**: One-click rollback to previous versions

### 5.6 Skill Library

**Path:** `/skills` | **Icon:** BookOpen

Browse and manage AI skills:

- **Skill Catalog**: All available skills with descriptions
- **Skill Details**: Click any skill to see triggers, steps, and usage examples
- **Categories**: Filter by category (development, testing, security, documentation)
- **Usage Stats**: How often each skill has been invoked

### 5.7 Token Controls

**Path:** `/token-controls` | **Icon:** Coins

Comprehensive token and cost management with 5 tabs:

#### Overview Tab
- **Summary Cards**: Total Calls, Total Tokens, Total Cost, Today's Tokens
- **Budget Progress**: Visual progress bars for monthly token and cost limits
- **Model Breakdown**: Usage percentage per model with bar charts
- **Active Users**: Quick view of top 5 users by token usage
- **Recent Usage Log**: Table of recent API calls with action, feature, model, tokens, cost, time

#### User Activity Tab
- **User List**: All users with their total token usage and cost
- **User Detail View**: Click any user to see:
  - Usage breakdown by feature
  - Usage breakdown by model
  - Recent activity timeline
  - Per-user cost tracking

#### Teams Tab
- **Team Overview**: Usage aggregated by team
- **Team Comparison**: Side-by-side team usage metrics
- **Team Members**: Drill down into individual team member usage

#### Budget Tab
- **Daily Token Limit**: Set maximum tokens per day
- **Monthly Token Limit**: Set maximum tokens per month
- **Monthly Cost Limit**: Set maximum USD spend per month
- **Alert Threshold**: Percentage at which budget alerts trigger (default: 80%)
- **Preferred Model**: Default model for all features
- **Enforce Limits**: Toggle hard enforcement (blocks requests when limits exceeded)
- **Save Budget**: Apply budget configuration

#### Trends Tab
- **Usage Over Time**: Line chart showing token usage trends over 30 days
- **Cost Trends**: Daily cost breakdown
- **Feature Trends**: Which features are consuming the most tokens over time

### 5.8 App Runner

**Path:** `/app-runner` | **Icon:** MonitorPlay

Run and test applications directly inside ZECT with 3 tabs:

#### Terminal Tab
- **Command Input**: Type commands and press **Run** for one-shot execution
- **Start Process**: Click to run long-lived processes (dev servers, watchers)
- **Working Directory**: Set the directory where commands execute
- **Output**: Color-coded terminal output (green=stdout, red=stderr, cyan=commands, yellow=process events)
- **Command History**: Use Up/Down arrow keys to navigate previous commands
- **Clear**: Reset the terminal output

#### Configure Tab
- **Repo Path**: Absolute path to the project on disk
- **Install Command**: Command to install dependencies (e.g., `npm install`)
- **Startup Command**: Command to start the dev server (e.g., `npm run dev`)
- **Preview Port**: Port for the live preview iframe (e.g., `5173`)
- **Environment Variables**: Key=value pairs, one per line
- **Launch**: One-click install + start + preview

#### Processes Tab
- **Process List**: All running and stopped processes with PID, uptime, output line count
- **Live Output**: Click any process to see its real-time output
- **Stop**: Stop a running process
- **Remove**: Remove a stopped process from the list

#### Preview Panel
- When a dev server is running, the right side shows a live **iframe preview** of the app
- Set the correct port in the Configure tab
- Click the external link icon to open in a new browser tab

### 5.9 File Explorer

**Path:** `/file-explorer` | **Icon:** FolderOpen

Browse repository files:

- **Tree View**: Navigate the folder structure
- **File Viewer**: View file contents with syntax highlighting
- **Search**: Search for files by name
- **File Info**: Size, last modified, permissions

### 5.10 Git Operations

**Path:** `/git-ops` | **Icon:** GitBranch

Git management interface:

- **Branch Management**: View, create, switch, delete branches
- **Commit History**: View commit log with diffs
- **Status**: Current working tree status
- **Pull/Push**: Sync with remote
- **Stash**: Manage stashed changes

### 5.11 CI Monitor

**Path:** `/ci-monitor` | **Icon:** Activity

Monitor CI/CD pipelines:

- **Pipeline Status**: Active, passed, failed pipelines
- **Build Logs**: View detailed build output
- **Test Results**: Test suite pass/fail summary
- **Deployment Status**: Current deployment state
- **Alerts**: Failed pipeline notifications

---

## 6. Zinnia Intelligence Section

### 6.1 Memory System

**Path:** `/memory` | **Icon:** Brain

4-layer memory architecture for persistent AI context:

#### Brain State Panel
- **Status**: Healthy/Degraded/Offline indicator
- **Memory Counts**: Total working, episodic, semantic, and personal memories
- **Last Updated**: When the brain state was last refreshed

#### Working Memory
Short-term memory for the current session:
1. Click **New Working Memory** to add
2. Fill in: Key, Value, Agent
3. Click **Save**
4. Working memories are listed with key, value, agent, and timestamp
5. Click the trash icon to delete

#### Episodic Memory
Long-term memory of past events and sessions:
1. Click **New Episode** to add
2. Fill in: Summary, Outcome, Participants, Agent
3. Click **Save**
4. Episodes are listed with summary, outcome, participants, agent, and timestamp
5. Click the trash icon to delete

#### Semantic Memory
Factual knowledge and patterns learned over time:
1. Click **New Fact** to add
2. Fill in: Fact, Category, Confidence (0.0-1.0), Agent
3. Click **Save**
4. Facts are listed with fact text, category, confidence score, and timestamp
5. Click the trash icon to delete

#### Personal Memory
User preferences and behavioral patterns:
1. Click **New Preference** to add
2. Fill in: Key, Value, Agent
3. Click **Save**
4. Preferences are listed with key, value, agent, and timestamp
5. Click the trash icon to delete

**Toast Notifications**: All API errors show a red toast notification in the top-right corner with the error message. Success operations show a green toast.

### 6.2 Dream Engine

**Path:** `/dream-engine` | **Icon:** Sparkles

Offline consolidation process that strengthens useful memories and decays old ones:

#### Running a Dream Cycle
1. Click **Run Dream Cycle**
2. The engine:
   - Consolidates episodic memories into semantic facts
   - Identifies patterns across sessions
   - Strengthens frequently-used memories
   - Creates new semantic entries from episodic patterns
3. View the results: consolidated count, new facts, patterns found
4. Success toast: "Dream cycle completed"

#### Decay Old Episodes
1. Click **Decay Old Episodes**
2. The engine removes episodes older than the retention threshold
3. View the count of decayed episodes
4. Success toast: "Decayed N old episodes"

#### Dream Run History
- View all past dream runs with: run ID, timestamp, consolidated count, new facts
- Track consolidation effectiveness over time

### 6.3 Data Layer

**Path:** `/data-layer` | **Icon:** Layers

Cross-agent event tracking and KPI dashboard:

#### KPI Dashboard
- **Total Events**: Number of tracked events
- **Unique Agents**: Number of distinct agents reporting
- **Avg Duration**: Average event duration
- **Error Rate**: Percentage of events with errors

#### Daily Report
- Click **Generate Report** to create a daily summary
- View: Total events, unique agents, top event types, error summary

#### Event Log
- **Table View**: All events with columns: Agent, Event Type, Duration, Metadata, Timestamp
- **Pagination**: 15 events per page with page navigation (Showing X-Y of Z)
- **Add Event**: Click to log a new event manually
  - Fill in: Agent, Event Type, Duration (ms), Metadata (JSON)

### 6.4 Data Flywheel

**Path:** `/data-flywheel` | **Icon:** Repeat

Continuous improvement loop that turns approved runs into training data:

#### Flywheel Pipeline
The flywheel has 4 stages:

1. **Approved Runs** (Tab 1)
   - View all approved agent runs
   - Each run shows: Agent, Task, Duration, Quality Score
   - Click **Approve** to promote a run to trace stage

2. **Traces** (Tab 2)
   - Approved runs become traces for analysis
   - Each trace shows: Run ID, Agent, Steps, Quality
   - Click **Approve** to promote to context card

3. **Context Cards** (Tab 3)
   - Traces become context cards for future sessions
   - Each card shows: Summary, Patterns, Best Practices
   - Click **Approve** to promote to eval case

4. **Eval Cases** (Tab 4)
   - Context cards become evaluation test cases
   - Each case shows: Input, Expected Output, Quality Threshold
   - Used for regression testing of AI quality

**Toast Notifications**: "Trace approved", "Context card approved", etc. on success. Error toasts on failure.

### 6.5 Permissions

**Path:** `/permissions` | **Icon:** ShieldAlert

3-tier action enforcement protocol:

#### Permission Tiers
- **Allow**: Action executes automatically without human intervention
- **Require Approval**: Action queues for human review before execution
- **Never Allow**: Action is blocked entirely

#### Managing Rules
1. **View Rules**: All rules listed with Agent, Action, Tier, and timestamp
2. **Pagination**: 10 rules per page with page navigation
3. **Add Rule**: Click **Add Rule**
   - Select Agent (or "all" for global)
   - Enter Action name (e.g., "deploy_production", "delete_database")
   - Select Tier: Allow, Require Approval, or Never Allow
   - Click **Save**
4. **Delete Rule**: Click the trash icon next to any rule
5. **Pending Approvals**: View actions waiting for human approval
   - Click **Approve** or **Deny** for each pending action

### 6.6 Transfer & Onboarding

**Path:** `/transfer` | **Icon:** ArrowRightLeft

Brain state export/import with onboarding wizard:

#### Export Brain State
1. Select export type: **Full** or **Minimal**
   - Full: All 4 memory layers + preferences + skills
   - Minimal: Only semantic + personal memories
2. Click **Export**
3. Download the JSON bundle file
4. Success toast: "Full export successful" or "Minimal export successful"

#### Import Brain State
1. Click **Import**
2. Paste the JSON bundle into the text area (or upload a file)
3. Click **Import Bundle**
4. The system loads all memories from the bundle
5. Validation: Invalid JSON shows error toast "Invalid JSON bundle data"

#### Onboarding Wizard
For new agents/users, the 6-question wizard collects:

1. **Preferred communication style** (concise/detailed/balanced)
2. **Primary programming languages**
3. **Preferred frameworks**
4. **Code review strictness** (lenient/balanced/strict)
5. **Documentation preference** (minimal/moderate/comprehensive)
6. **Risk tolerance** (conservative/moderate/aggressive)

Click **Complete Onboarding** to save all preferences.
Success toast: "Onboarding complete! Preferences saved."

### 6.7 Skills Engine

**Path:** `/skills-engine` | **Icon:** Wrench

Database-backed skill registry with trigger matching:

#### Viewing Skills
- **Skills List**: All registered skills with name, description, triggers, and category
- **Pagination**: 10 skills per page with page navigation
- **Seed Skills**: Pre-loaded skills for common tasks (code review, testing, documentation, etc.)

#### Adding a Skill
1. Click **Add Skill**
2. Fill in:
   - **Name**: Unique skill name (e.g., "security-audit")
   - **Description**: What the skill does
   - **Triggers**: Comma-separated trigger phrases (e.g., "audit security, check vulnerabilities")
   - **Category**: Skill category (e.g., "security", "development", "testing")
   - **Steps**: JSON array of step objects
3. Click **Save**

#### Trigger Matching
- Enter a natural language query in the **Match** input
- Click **Find Matching Skills**
- The engine returns skills whose triggers match the query

#### Execution Logs
- View all skill execution history
- Each log shows: Skill Name, Agent, Input, Output, Duration, Timestamp
- Track which skills are used most frequently

---

## 7. Enterprise Section

### 7.1 Audit Trail

**Path:** `/audit-trail` | **Icon:** ScrollText

Complete audit log of all platform activities:

- **Event Log**: Every action taken in ZECT with user, action, timestamp, and details
- **Filter**: Filter by date range, user, action type
- **Search**: Full-text search across audit entries
- **Export**: Download audit log as CSV or JSON
- **Compliance**: Meets SOC 2 and ISO 27001 audit requirements

### 7.2 Rules Engine

**Path:** `/rules` | **Icon:** Scale

Define and manage automation rules:

- **Rule List**: All active rules with name, trigger condition, and action
- **Create Rule**: Define trigger conditions and automated responses
  - Trigger: Event type, threshold, pattern match
  - Action: Notify, block, auto-approve, escalate
- **Rule History**: View rule execution history
- **Enable/Disable**: Toggle rules on/off without deleting

### 7.3 Integrations

**Path:** `/integrations` | **Icon:** Plug

Connect ZECT to external services:

- **Available Integrations**: GitHub, GitLab, Jira, Slack, Teams, PagerDuty
- **Connected**: View active integrations with status
- **Configure**: Set up API keys, webhooks, and permissions for each integration
- **Webhooks**: Manage incoming and outgoing webhook configurations
- **SSO**: Configure Single Sign-On providers (SAML, OIDC)

### 7.4 Export/Share

**Path:** `/export` | **Icon:** Download

Export and share platform data:

- **Export Formats**: JSON, CSV, PDF, Markdown
- **Data Types**: Projects, analytics, audit logs, reviews, token usage
- **Scheduled Exports**: Set up recurring data exports
- **Share Links**: Generate shareable links for reports and dashboards
- **API Export**: Programmatic data export via REST API

### 7.5 Output History

**Path:** `/output-history` | **Icon:** History

View all AI-generated outputs:

- **Output List**: All generated content (reviews, plans, blueprints, docs)
- **Filter**: Filter by type, date, model, feature
- **View**: Click any output to see the full content
- **Re-run**: Re-generate any previous output with updated parameters
- **Compare**: Side-by-side comparison of different output versions

---

## 8. Keyboard Shortcuts & Tips

| Shortcut | Action |
|---|---|
| `Ctrl+B` / `Cmd+B` | Toggle sidebar collapse/expand |
| `Enter` | Submit forms, send messages |
| `Up/Down Arrow` | Navigate command history (App Runner) |
| `Escape` | Close modals and overlays |

### Tips

- **Collapsed Sidebar**: Hover over any icon to see the label as a tooltip
- **Mobile**: Tap outside the sidebar overlay to close it
- **Toast Notifications**: Error toasts auto-dismiss after 5 seconds; click X to dismiss immediately
- **Pagination**: Pages with more items than the page size show pagination controls at the bottom
- **Code Splitting**: Heavy pages (Code Review, Build, Review, Deploy, Skill Library) load on-demand for faster initial page load

---

## 9. API Configuration

### Setting Up LLM API Key

For AI-powered features (Ask Mode, Plan Mode, Blueprint, Code Review, Doc Generator):

1. Create a `.env` file in the `backend/` directory:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```
2. Restart the backend server
3. All AI features will now use this key

### Supported LLM Providers

| Provider | Models | Setup |
|---|---|---|
| OpenAI | gpt-4o-mini, gpt-4o, gpt-3.5-turbo | Set `OPENAI_API_KEY` |
| Anthropic | claude-3.5-sonnet, claude-3-haiku | Set `ANTHROPIC_API_KEY` |
| Ollama (Local) | llama-3.1-8b, codellama, mistral | Install Ollama, set `OLLAMA_BASE_URL` |

### Database Configuration

**SQLite (Default)**:
- No configuration needed
- Data stored in `backend/zect.db`

**PostgreSQL**:
1. Create a database:
   ```sql
   CREATE DATABASE zect;
   CREATE USER zect_user WITH PASSWORD 'your-password';
   GRANT ALL PRIVILEGES ON DATABASE zect TO zect_user;
   ```
2. Set the environment variable:
   ```
   DATABASE_URL=postgresql://zect_user:your-password@localhost:5432/zect
   ```
3. Restart the backend

---

## 10. Troubleshooting

### Common Issues

| Issue | Solution |
|---|---|
| Login fails | Verify `ZECT_USERNAME` and `ZECT_PASSWORD` environment variables are set correctly on the backend |
| AI features return errors | Check that `OPENAI_API_KEY` is set and valid |
| "Network error" toast | Verify the backend is running on the correct port and `VITE_API_URL` matches |
| Pages load slowly | Code-splitting is enabled; first load of Code Review/Build/Review/Deploy/Skills may take a moment |
| Pagination not showing | Pagination only appears when there are more items than the page size (15 for events, 10 for rules/skills) |
| Token budget alerts | Go to Token Controls > Budget tab to increase limits |
| Database errors | For PostgreSQL, verify `DATABASE_URL` is correct and the database exists |

### Getting Help

- **Internal Support**: Contact the Zinnia Engineering Platform team
- **GitHub Issues**: Report bugs at https://github.com/KarthikKaruppasamy880/ZECT/issues
- **Documentation**: See the `docs/` folder in the repository

---

*ZECT - Zinnia Engineering Control Tower*
*Built by Zinnia Engineering*
