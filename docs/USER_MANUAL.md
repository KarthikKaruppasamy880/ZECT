# ZECT User Manual

> Zinnia Engineering Delivery Control Tower — Complete User Guide

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard](#2-dashboard)
3. [Projects](#3-projects)
4. [Multi-Repo Orchestration](#4-multi-repo-orchestration)
5. [Repo Analysis](#5-repo-analysis)
6. [Blueprint Generator](#6-blueprint-generator)
7. [Documentation Generator](#7-documentation-generator)
8. [Workflow Stages](#8-workflow-stages)
9. [Analytics](#9-analytics)
10. [Settings & API Key Configuration](#10-settings--api-key-configuration)
11. [Docs Center](#11-docs-center)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Getting Started

### Prerequisites

- **Node.js 18+** and **npm** for the frontend
- **Python 3.11+** and **Poetry** for the backend
- **GitHub Personal Access Token** (optional, increases API rate limits)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/KarthikKaruppasamy880/ZECT.git
cd ZECT

# Start the backend
cd backend
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start the frontend (in a new terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### Configuring a GitHub Token

Navigate to **Settings** and click **Configure** on the GitHub API Key card. Enter your Personal Access Token (PAT) with `repo` read scope. This increases your GitHub API rate limit from 60 to 5,000 requests/hour.

---

## 2. Dashboard

The Dashboard is the home screen showing:

- **Metric cards** — Total Projects, Active Projects, Avg Token Savings, Risk Alerts
- **Token Usage Control** — real-time panel showing total API calls, total tokens consumed, estimated cost (USD), with expandable breakdown by feature and model, plus recent activity log
- **Stage Distribution** — bar chart showing project counts per delivery stage
- **Project cards** — all registered projects with status, completion bar, repo count, and team info

### Token Usage Control Panel

The dashboard includes a dedicated token control widget:

| Metric | Description |
|--------|-------------|
| Total API Calls | Number of LLM and GitHub API calls made |
| Total Tokens | Prompt + completion tokens consumed |
| Estimated Cost | USD cost based on model pricing (GPT-4o-mini rates) |

Click **"Details"** to expand:
- **Usage by Feature** — breakdown by ask_mode, plan_mode, blueprint, doc_gen, repo_analysis
- **Usage by Model** — breakdown by gpt-4o-mini, github-api, etc.
- **Recent Activity** — table of last 10 operations with action, feature, model, tokens, cost, and timestamp

All token data is persisted to the database (`token_logs` table) for full audit trail.

### Actions

| Action | How |
|--------|-----|
| View a project | Click any project card |
| Create a new project | Click "New Project" button |
| View token details | Click "Details" on Token Usage Control panel |
| Navigate to stages | Use the sidebar workflow stages |

---

## 3. Projects

### Project List

Shows all projects with:
- Name, description, status (active/planning/completed)
- Connected GitHub repos
- Team lead and member count
- Stage progress indicator

### Create a New Project

1. Click **New Project** (or navigate to `/projects/new`)
2. Fill in: Name, Description, Status, Stage
3. Add GitHub repos: enter `owner/repo` format (e.g., `KarthikKaruppasamy880/ZECT`)
4. Click **Create Project**

### Project Detail

Click any project to see:
- **Overview** — description, status, metadata
- **Connected Repos** — list of GitHub repos with language, stars, open issues
- **Pull Requests** — PRs from connected repos with status, author, dates
- **CI/CD Status** — workflow runs from GitHub Actions

Click any PR to open the **PR Viewer** with file-by-file diffs, commit history, and review comments.

---

## 4. Multi-Repo Orchestration

Navigate to **Orchestration** in the sidebar.

This page provides a cross-project view of all connected repositories:
- **Repo cards** grouped by project
- **Dependency health** indicators
- **CI status** across all repos
- **Coverage and activity** metrics

Use this to monitor multiple repositories across your engineering organization.

---

## 5. Repo Analysis

Navigate to **Repo Analysis** in the sidebar.

### Single Repo Analysis

1. Select **Single Repo** tab
2. Enter **Owner** (e.g., `facebook`) and **Repository** (e.g., `react`)
3. Click **Analyze**

### Multi-Repo Analysis

1. Select **Multi-Repo** tab
2. Add repos using **Add Repo** button
3. Enter Owner and Repository for each
4. Click **Analyze All**

### What You Get

For each analyzed repo:
- **Metadata** — stars, forks, open issues, language, default branch
- **Architecture Notes** — detected patterns (src/, app/, Docker, CI/CD, tests)
- **Dependencies** — parsed from package.json, requirements.txt, pyproject.toml, Cargo.toml, go.mod, Gemfile, pom.xml, build.gradle
- **File Structure** — full tree (up to 300 files)
- **README excerpt** — first 8,000 characters

Click any repo in the results to expand/collapse its details.

---

## 6. Blueprint Generator

Navigate to **Blueprint** in the sidebar.

The Blueprint Generator has two modes: **Standard** and **Focused**. Switch between them using the mode tabs.

### Standard Mode

1. Select the **Standard** tab
2. Add one or more repos (Owner + Repository)
3. Click **Generate Blueprint**
4. ZECT analyzes each repo (structure, README, dependencies, architecture)
5. Synthesizes a single copy-paste prompt
6. Click **Copy to Clipboard**
7. Paste into any AI tool (Cursor, Claude Code, Codex, Windsurf, etc.)

**What the Standard Blueprint Contains:**

- Repository metadata and description
- Architecture notes
- Full dependency list
- File structure (top 80 files)
- README excerpt
- AI instructions for recreating the project

### Focused Mode

1. Select the **Focused** tab
2. Enter the repo Owner and Repository name
3. Enter a **Focus Area** (e.g., `authentication`, `API layer`, `database schema`)
4. Optionally enter a **Goal** (e.g., `understand and replicate`, `migrate to new framework`)
5. Click **Generate Focused Blueprint**
6. The prompt is scoped to files related to the focus area
7. Click **Copy to Clipboard**

**What the Focused Blueprint Contains:**

- Files relevant to the focus area (highlighted first)
- Full file tree for context
- Architecture notes
- Goal-specific instructions for the AI tool

### Token Estimate

Both modes show an estimated token count so you can gauge if the prompt fits within your AI tool's context window.

---

## 7. Documentation Generator

Navigate to **Doc Generator** in the sidebar.

### How It Works

1. Enter **Owner** and **Repository**
2. Select which sections to generate (toggle on/off):
   - Overview
   - Architecture
   - API Reference
   - Setup Guide
   - Testing
   - Deployment
3. Click **Generate Documentation**
4. Expand any section to view content
5. Click **Copy** on individual sections or **Copy All Sections**

### Section Details

| Section | What It Generates |
|---------|-------------------|
| Overview | Repo description, language, stats, branch info |
| Architecture | Detected patterns, key directories with file counts |
| API Reference | Detected API/route/controller/handler files |
| Setup Guide | Prerequisites, clone command, install commands |
| Testing | Test files detected, run commands for detected test frameworks |
| Deployment | Docker files, CI/CD workflow files |

---

## 8. Workflow Stages

ZECT implements a 5-stage engineering delivery workflow. Navigate via the sidebar under **Workflow Stages**.

### Ask Mode

Gather requirements, define scope, validate assumptions. Deliverables include requirements documents, stakeholder sign-off, risk assessments.

### Plan Mode

Design architecture, plan sprints, create implementation roadmaps. Deliverables include ADRs, API designs, sprint plans.

### Build Phase

Implement features, write code, create tests. Deliverables include working code with unit tests, CI pipeline, code documentation.

### Review

Quality assurance, security audit, performance review. Deliverables include security audit reports, performance tests, accessibility compliance.

### Deployment

Release to production, monitor health, validate deployment. Deliverables include deployment runbooks, monitoring dashboards, rollback procedures.

Each stage page shows:
- **Key Activities** — what happens during this stage
- **Deliverables** — what this stage produces
- **Stage Gates** — criteria that must be met before proceeding

---

## 9. Analytics

Navigate to **Analytics** in the sidebar.

Shows engineering delivery metrics:
- Total projects, active projects, total repos
- Open PRs across all connected repos
- CI pass rate and average review time
- Charts for project distribution and activity trends

---

## 10. Settings & API Key Configuration

Navigate to **Settings** in the sidebar.

### GitHub API Key

1. Click **Configure** (or **Update** if already configured)
2. Enter your GitHub Personal Access Token
3. Click **Save**
4. The card shows: configured status, remaining API requests, rate limit

**Creating a token:**
Go to GitHub Settings > Developer settings > Personal access tokens > Generate new token. Select the `repo` scope (read access).

### OpenAI API Key

1. Click **Configure** on the OpenAI API Key card
2. Enter your OpenAI API key (starts with `sk-`)
3. Click **Save**
4. Required for: Ask Mode, Plan Mode, Blueprint Enhancement

### Token Usage Log

1. Click **View Log** on the Token Usage card
2. See total tokens consumed and a log of each action with timestamps
3. Each entry shows action name, token count, and timestamp
4. All data is persisted in the database for audit purposes

### Feature Toggles

Toggle features on/off:
- Automated Code Review
- Token Usage Tracking
- Deployment Gate Enforcement
- Risk Alert Notifications
- Auto-Generate Plan from Requirements
- Session Context Memory

### Configuration Options

- Default Starting Stage (Ask Mode / Plan Mode / Build Phase)
- Minimum Review Severity (Critical / High / Medium / Low / Info)
- Deployment Approval Mode (Anyone / Tech Lead / Tech Lead + PM / VP Engineering)
- Monthly Token Budget Alert (50% / 70% / 80% / 90% / No alert)

---

## 11. Docs Center

Navigate to **Docs Center** in the sidebar.

Central hub for all ZECT documentation, guides, and reference material. Links to:
- This User Manual
- Repo Analysis Guide
- Multi-Repo Analysis Guide
- Blueprint Generation Guide
- Ask/Plan/Development Workflow Guide
- Architecture & Usage Guide

---

## 12. Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Rate limit exceeded" error | Configure a GitHub API key in Settings |
| Repo analysis returns empty tree | Check that the repo exists and is public (or your token has access) |
| Blueprint is too large | Analyze fewer repos at once, or use repos with fewer files |
| Frontend shows "Failed to fetch" | Ensure the backend is running on port 8000 |
| Settings changes not saving | Refresh the page; check browser console for errors |

### Getting Help

- Check the [README](../README.md) for setup instructions
- Review individual guide files in the `docs/` directory
- Open an issue on the [ZECT GitHub repo](https://github.com/KarthikKaruppasamy880/ZECT/issues)
