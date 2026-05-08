# ZECT Repo Connection Architecture

## Overview

The **Active Project/Repo Selector** is a global UI component that connects ZECT's workflow stages (Ask, Plan, Build) to a specific GitHub repository. When a project with linked repos is selected, all AI-powered workflows automatically receive the repository context — ensuring accurate, repo-aware responses without manual configuration on every request.

This is analogous to how **Devin sessions** are scoped to a specific repository: once you select a repo, every action in that session knows which codebase it's working with.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    ZECT Application Shell                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ActiveProjectProvider (React Context)                     │  │
│  │  ┌─────────────────┐  ┌──────────────────────────────┐   │  │
│  │  │ State:           │  │ Persistence:                  │   │  │
│  │  │ • projects[]     │  │ • localStorage:               │   │  │
│  │  │ • activeProject  │  │   zect_active_project_id      │   │  │
│  │  │ • activeRepo     │  │   zect_active_repo_id         │   │  │
│  │  │ • loading        │  │                               │   │  │
│  │  └─────────────────┘  └──────────────────────────────┘   │  │
│  │                                                            │  │
│  │  Computed:                                                 │  │
│  │  • repoFullName  → "owner/repo_name"                      │  │
│  │  • repoContextString → "Repository: owner/repo (branch)"  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                    │
│              ┌───────────────┼───────────────┐                   │
│              ▼               ▼               ▼                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Ask Mode    │  │  Plan Mode   │  │ Build Phase  │          │
│  │              │  │              │  │              │          │
│  │ useActive    │  │ useActive    │  │ useActive    │          │
│  │ Project()    │  │ Project()    │  │ Project()    │          │
│  │              │  │              │  │              │          │
│  │ → Injects    │  │ → Injects    │  │ → Injects    │          │
│  │   repo ctx   │  │   repo ctx   │  │   repo ctx   │          │
│  │   into API   │  │   into API   │  │   into API   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                              │                                    │
│                              ▼                                    │
│                    ┌──────────────────┐                          │
│                    │  Backend API      │                          │
│                    │  /api/ask         │                          │
│                    │  /api/plan        │                          │
│                    │  /api/build       │                          │
│                    │                   │                          │
│                    │  Receives full    │                          │
│                    │  repo context     │                          │
│                    └──────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### Project → Repos (1:N Relationship)

```typescript
interface Project {
  id: number;
  name: string;
  description: string;
  stage: string;
  team: string;
  repos: Repo[];       // 0 or more linked repos
  completion: number;
}

interface Repo {
  id: number;
  owner: string;        // GitHub username/org
  repo_name: string;    // Repository name
  default_branch: string; // e.g., "main", "develop"
  github_url: string;
  is_private: boolean;
}
```

### Key Rules:
- A project can have **0, 1, or many** repos linked
- When a project has **1 repo**, it's auto-selected
- When a project has **multiple repos**, user picks one from dropdown
- When a project has **0 repos**, the "Connected" status shows "No repo linked"

---

## Component Architecture

### 1. ActiveProjectContext (`/src/contexts/ActiveProjectContext.tsx`)

The core state management layer. Provides:

| Export | Type | Description |
|--------|------|-------------|
| `projects` | `Project[]` | All user's projects |
| `activeProject` | `Project \| null` | Currently selected project |
| `activeRepo` | `Repo \| null` | Currently selected repo |
| `loading` | `boolean` | Fetch state |
| `setActiveProject` | `(p) => void` | Change project (auto-selects first repo) |
| `setActiveRepo` | `(r) => void` | Change repo within project |
| `refreshProjects` | `() => void` | Refetch projects |
| `repoFullName` | `string \| null` | `"owner/repo_name"` |
| `repoContextString` | `string \| null` | Full context string for API |

### 2. ProjectSelector (`/src/components/ProjectSelector.tsx`)

The visual selector in the top bar:

- **Project dropdown**: Lists all projects with repo counts
- **Repo dropdown**: Shows when project has >1 repo
- **Status indicator**: Green "Connected" or "No repo linked"
- **Create link**: Quick access to create new project

### 3. Layout (`/src/components/Layout.tsx`)

Updated with sticky top bar containing ProjectSelector, visible on all pages.

### 4. Workflow Pages (Ask/Plan/Build)

Each page uses the `useActiveProject()` hook to:
1. Display the green "Connected to" banner
2. Auto-inject `repoContextString` into API requests

---

## How It Works: Step by Step

### Step 1: Configure GitHub Token (Settings Page)

Navigate to **Settings** → **Integrations** → Enter your GitHub Personal Access Token.

This gives ZECT access to your repositories. Each user has their own token, so they only see their own repos.

```
Settings → GitHub Token → Save
```

### Step 2: Create a Project

Navigate to **Projects** → **Create New Project**. Fill in:
- Project name
- Description
- Team
- Stage (Ask/Plan/Build/Review/Deploy)

### Step 3: Link GitHub Repository to Project

In the project detail page:
1. Click "Add Repository"
2. Select from your available GitHub repos (fetched via your token)
3. The repo is now linked to this project

You can link **multiple repos** to a single project (e.g., frontend + backend repos).

### Step 4: Select Project in Top Bar

Click the **project selector** button in the top navigation bar. A dropdown appears with all your projects and their repo counts.

Click a project to select it.

### Step 5: Select Repo (If Multiple)

If the project has multiple repos, a second dropdown button appears. Click it to choose which repo you want to work with.

If the project has only 1 repo, it's auto-selected.

### Step 6: Ask/Plan/Build Auto-Use That Repo

Navigate to any workflow page. You'll see:
- A green banner: "Connected to: owner/repo (branch)"
- Project name shown on the right

When you submit a question (Ask), generate a plan (Plan), or generate code (Build), the repo context is **automatically included** in the API call — no need to manually specify it.

---

## Persistence

| localStorage Key | Value | Purpose |
|-----------------|-------|---------|
| `zect_active_project_id` | Project ID (number) | Remember selected project |
| `zect_active_repo_id` | Repo ID (number) | Remember selected repo |

On page reload:
1. Context reads saved IDs from localStorage
2. After fetching projects, finds matching project/repo
3. Restores selection automatically

---

## Per-User Isolation

```
User A (token: ghp_AAA...)    User B (token: ghp_BBB...)
       │                              │
       ▼                              ▼
  Their repos only              Their repos only
  - repo-1                      - repo-X
  - repo-2                      - repo-Y
       │                              │
       ▼                              ▼
  Their projects only           Their projects only
  - Project Alpha               - Project Gamma
  - Project Beta                - Project Delta
```

Each user's GitHub token determines which repos they see. Projects are scoped per user. There is no cross-user data leakage.

---

## Comparison to Devin Sessions

| Feature | Devin | ZECT |
|---------|-------|------|
| Session scope | Repository-based | Project + Repo based |
| Context injection | Automatic per session | Automatic per selected project |
| Multi-repo | One repo per session | Multiple repos per project |
| Persistence | Session-based | localStorage (permanent until changed) |
| Switching | Create new session | Click dropdown |
| Branch awareness | Full git context | Shows default branch |

**Key similarity**: Both tools ensure that every AI interaction is aware of which codebase it's working with, without requiring the user to re-specify it every time.

---

## API Context Injection

When a repo is selected, the following context is prepended to every API call:

```
Project: Policy Admin Modernization
Repository: KarthikKaruppasamy880/ZECT (branch: main)
GitHub URL: https://github.com/KarthikKaruppasamy880/ZECT
```

This gives the LLM full awareness of:
- Which project the user is working on
- Which specific repository to reference
- The default branch for git operations

---

## File Structure

```
frontend/src/
├── contexts/
│   └── ActiveProjectContext.tsx    # Global state management
├── components/
│   ├── ProjectSelector.tsx         # Top bar UI component
│   └── Layout.tsx                  # Updated with ProjectSelector
├── pages/
│   ├── AskMode.tsx                 # Uses useActiveProject()
│   ├── PlanMode.tsx                # Uses useActiveProject()
│   └── BuildPhase.tsx              # Uses useActiveProject()
└── App.tsx                         # Wraps with ActiveProjectProvider
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No projects in dropdown | Check API: `GET /api/projects` returns data |
| "No repo linked" | Add a repo to the project via project settings |
| Context not injected | Verify `repoContextString` is not null in devtools |
| Selection lost on refresh | Check localStorage has `zect_active_project_id` |
| Wrong repo shown | Click repo dropdown to switch between project repos |

---

## Future Enhancements

1. **Branch selector**: Allow switching branches (not just default)
2. **Multi-repo context**: Send context from multiple repos simultaneously
3. **Repo-specific prompts**: Auto-suggest based on repo's tech stack
4. **Real-time sync**: WebSocket updates when repo changes externally
5. **Team-shared selections**: Allow team-wide default project/repo
