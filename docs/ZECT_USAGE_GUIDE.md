# ZECT Usage Guide

Complete guide to using every feature in ZECT (Zinnia Engineering Control Tower).

---

## Table of Contents

1. [Login](#1-login)
2. [Dashboard](#2-dashboard)
3. [Projects](#3-projects)
4. [Repo Analysis](#4-repo-analysis)
5. [Blueprint Generator](#5-blueprint-generator)
6. [Doc Generator](#6-doc-generator)
7. [Ask Mode](#7-ask-mode)
8. [Plan Mode](#8-plan-mode)
9. [Orchestration](#9-orchestration)
10. [Analytics](#10-analytics)
11. [Settings](#11-settings)

---

## 1. Login

**URL:** `/login`

Enter your credentials (username and password) to access the application. All features require authentication.

- Username: Your company email
- Password: Your configured password
- Session persists via localStorage token until you log out

---

## 2. Dashboard

**URL:** `/` (root)

Overview of your engineering delivery status:

- **Project Cards** — Quick view of all projects with status, tech stack, and team size
- **Metrics Row** — Total projects, active projects, total repos, team members
- **Activity Feed** — Recent actions across all projects
- **Quick Actions** — Jump to Repo Analysis, Blueprint Generator, or Doc Generator

---

## 3. Projects

**URL:** `/projects`

Manage your engineering projects:

- **View Projects** — Card grid showing all projects with status badges
- **Create Project** — Click "Create Project" to add a new project with:
  - Name, description, tech stack
  - GitHub repos (comma-separated)
  - Team members, project status
- **Project Detail** — Click any project to see:
  - Stage progress (Ask, Plan, Build, Review, Deploy, Docs)
  - Repository list
  - Team members
  - Activity timeline

---

## 4. Repo Analysis

**URL:** `/repo-analysis`

Analyze any GitHub repository's structure, tech stack, and architecture.

**How to use:**
1. Enter the repository in any of these formats:
   - Full URL: `https://github.com/owner/repo`
   - Short form: `owner/repo`
   - Just the repo name (uses your GitHub username as owner)
2. Click **"Analyze Repository"**
3. View results:
   - **Summary** — Language breakdown, stars, forks, default branch
   - **File Tree** — Complete directory structure
   - **README** — Rendered README content
   - **Dependencies** — Detected from package.json, pyproject.toml, etc.

**Requirements:** GitHub Personal Access Token (configure in Settings)

---

## 5. Blueprint Generator

**URL:** `/blueprint`

Generate a single copy-paste prompt from a GitHub repository that you can use in any AI coding tool to vibe-code the project from scratch.

**How to use:**
1. Enter the repository (same formats as Repo Analysis)
2. Click **"Generate Blueprint"**
3. The tool analyzes: file structure, README, dependencies, architecture
4. Result: A comprehensive synthetic prompt ready to paste into any AI coding assistant
5. Click **"Copy to Clipboard"** to copy the prompt

**AI Enhancement (requires OpenAI key):**
1. After generating a blueprint, click **"Enhance with AI"**
2. The LLM improves the prompt with better structure, clarity, and completeness
3. View the enhanced version alongside the original
4. Copy whichever version you prefer

**Requirements:**
- GitHub Token (for blueprint generation)
- OpenAI API Key (for AI enhancement only — base blueprint works without it)

---

## 6. Doc Generator

**URL:** `/docs`

Generate documentation for any GitHub repository automatically.

**How to use:**
1. Enter the repository (same formats as Repo Analysis)
2. Click **"Generate Documentation"**
3. The tool creates structured documentation from the repo's code and README
4. Copy or download the generated docs

**Requirements:** GitHub Personal Access Token

---

## 7. Ask Mode

**URL:** `/ask`

Ask any engineering question and get AI-powered answers. Optionally provide repository context for smarter, more relevant responses.

**How to use:**
1. Type your question in the chat input
2. (Optional) Expand "Repository Context" and paste relevant code, README, or architecture details
3. Press Enter or click Send
4. View the AI response with model info and token usage

**Quick suggestions:**
- "How to structure a React app with authentication?"
- "Best practices for FastAPI project layout?"
- "Explain microservices vs monolith trade-offs"

**Features:**
- Chat history within the session
- Keyboard shortcuts: Enter to send, Shift+Enter for newline
- Token usage display per response
- Model identification (gpt-4o-mini)

**Requirements:** OpenAI API Key (configure in Settings)

---

## 8. Plan Mode

**URL:** `/plan`

Generate structured engineering plans for any project or feature.

**How to use:**
1. Enter a project or feature description (e.g., "Build a real-time notification system with WebSocket support")
2. (Optional) Click "Advanced Options" to add:
   - **Repository Context** — Paste existing code/architecture for context-aware planning
   - **Constraints** — Budget, timeline, tech restrictions
3. Click **"Generate Plan"**
4. View the structured plan with:
   - **Phases** — Extracted milestone phases displayed as badges
   - **Full Plan** — Detailed implementation steps
   - **Token Usage** — How many tokens were used
5. Click **"Copy Plan"** to copy to clipboard

**Requirements:** OpenAI API Key (configure in Settings)

---

## 9. Orchestration

**URL:** `/orchestration`

Multi-repository dashboard showing the status of all repositories in a project.

**How to use:**
1. View the repository grid with status indicators
2. Each repo card shows: name, language, last updated, analysis status
3. Click on a repo to see detailed analysis
4. Use for coordinating work across multiple repositories

**Requirements:** GitHub Personal Access Token

---

## 10. Analytics

**URL:** `/analytics`

Visual charts and metrics about your projects and repositories.

**Charts include:**
- Project status distribution (pie chart)
- Repository language breakdown
- Team size per project
- Activity timeline

---

## 11. Settings

**URL:** `/settings`

Configure API keys and application settings.

### API Key Cards

| Card | Purpose | How to Get |
|------|---------|------------|
| **GitHub API Key** | Repo Analysis, Blueprint, Doc Generator, Orchestration | https://github.com/settings/tokens |
| **OpenAI API Key** | Ask Mode, Plan Mode, Blueprint AI Enhancement | https://platform.openai.com/api-keys |

### Configuring an API Key

1. Click **"Configure"** on the key card
2. Enter your API key in the modal
3. Click **"Save Key"**
4. Status indicator turns green when configured
5. Key is validated before saving

> **Note:** Runtime keys do not persist across server restarts. For permanent configuration, add keys to the backend `.env` file. See [ENV_SETUP_GUIDE.md](./ENV_SETUP_GUIDE.md).

### Additional Settings

- **Theme** — Application theme configuration
- **User Profile** — View logged-in user info
- **Logout** — End your session

---

## Feature Dependency Matrix

| Feature | Works Offline | Needs GitHub Token | Needs OpenAI Key |
|---------|:---:|:---:|:---:|
| Dashboard | Yes | - | - |
| Projects | Yes | - | - |
| Analytics | Yes | - | - |
| Settings | Yes | - | - |
| Repo Analysis | - | Yes | - |
| Blueprint Generator | - | Yes | - |
| Blueprint AI Enhancement | - | Yes | Yes |
| Doc Generator | - | Yes | - |
| Ask Mode | - | - | Yes |
| Plan Mode | - | - | Yes |
| Orchestration | - | Yes | - |

---

## Tips

1. **Paste full GitHub URLs** — The app auto-parses `https://github.com/owner/repo` into the correct owner/repo format
2. **Configure keys first** — Go to Settings before using Repo Analysis or Ask Mode
3. **Use Ask Mode for learning** — Ask about architecture patterns, best practices, or debugging help
4. **Use Plan Mode for kickoff** — Generate implementation plans before starting any new feature
5. **Blueprint + AI Enhancement** — Generate a base blueprint, then enhance with AI for a polished prompt ready for any AI coding tool
