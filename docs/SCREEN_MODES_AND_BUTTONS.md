# ZECT Screen Modes & Button Reference

> Complete reference for every screen, its modes, and interactive elements.

---

## 1. Login Page

**URL:** `/login` (redirects here when unauthenticated)

### Layout
- Centered card on dark slate-900 background
- ZECT logo and "Welcome Back" heading

### Fields
| Field | Type | Placeholder | Validation |
|-------|------|-------------|------------|
| Email | text | `your.email@zinnia.com` | Required |
| Password | password | `Enter your password` | Required |

### Buttons
| Button | Action | State Changes |
|--------|--------|---------------|
| **Sign In** | Submits credentials to `POST /api/auth/login` | On success: stores token in `localStorage`, redirects to Dashboard. On error: shows red error banner "Invalid credentials. Please try again." |

### Behavior
- Session persists via `localStorage` token until logout or token expiration
- On page load, verifies existing token via `GET /api/auth/verify`
- If token valid, auto-redirects to Dashboard

---

## 2. Dashboard

**URL:** `/` (root)

### Layout
- Header: "Dashboard" title with subtitle
- Metrics row: 4 metric cards
- Stage Distribution bar
- Projects grid (all projects)

### Metric Cards (Read-Only)
| Card | Icon | Data Source |
|------|------|-------------|
| Total Projects | Layers icon (blue) | `analytics.total_projects` |
| Active Projects | TrendingUp icon (green) | `analytics.active_projects` |
| Avg Token Savings | BarChart icon (purple) | `analytics.avg_token_savings` |
| Risk Alerts | AlertTriangle icon (red) | `analytics.total_risk_alerts` |

### Buttons / Interactive Elements
| Element | Action |
|---------|--------|
| **View all** link | Navigates to `/projects` |
| **Project card** (clickable) | Navigates to `/projects/{id}` |
| **Stage badges** in distribution | Display only (ask, plan, build, review, deploy counts) |

### Stage Distribution
Shows count of projects in each workflow stage: Ask, Plan, Build, Review, Deploy.

---

## 3. Projects List

**URL:** `/projects`

### Layout
- Header with "New Project" button
- Filter bar with status buttons
- Project cards grid

### Buttons
| Button | Action | Visual |
|--------|--------|--------|
| **+ New Project** | Navigates to `/projects/new` | Blue button, top-right |
| **All** | Shows all projects | Blue when active |
| **active** | Filters to active projects only | Gray outline when inactive |
| **completed** | Filters to completed projects only | Gray outline when inactive |
| **on-hold** | Filters to on-hold projects only | Gray outline when inactive |
| **Project card** (clickable) | Navigates to `/projects/{id}` | Hover shadow effect |

### Project Card Display
Each card shows:
- Project name + status badge (active/completed/on-hold) + stage badge
- Description text
- Completion %, Token Savings %, Risk Alerts count
- Team name and repo count

---

## 4. Create Project

**URL:** `/projects/new`

### Layout
- Form card with input fields
- Back link to projects

### Fields
| Field | Type | Required | Placeholder |
|-------|------|----------|-------------|
| Project Name | text | Yes | "Project name" |
| Description | textarea | No | "Describe the project..." |
| Team | text | No | "Team name" |
| Repo Owner | text | No | "GitHub owner (e.g., facebook)" |
| Repo Name | text | No | "Repository name (e.g., react)" |

### Buttons
| Button | Action | Behavior |
|--------|--------|----------|
| **Create Project** | `POST /api/projects` with form data | On success: navigates to `/projects/{newId}`. On error: shows error message. Disabled while loading (shows spinner). |

### Validation
- Name is required (shows error if empty)
- If repo owner and repo name are both provided, links the repo to the project

---

## 5. Project Detail

**URL:** `/projects/:id`

### Modes (Tabs)
| Tab | Content |
|-----|---------|
| **Overview** (default) | Project metadata, description, linked repos |
| **Pull Requests** | PRs from first linked repo via GitHub API |
| **Commits** | Recent commits from first linked repo |
| **CI/CD** | GitHub Actions workflow runs |

### Buttons
| Button | Action |
|--------|--------|
| **Back to Projects** | Navigates to `/projects` |
| **Tab buttons** (Overview / PRs / Commits / CI/CD) | Switches active tab |
| **PR row** (clickable) | Navigates to `/pr/{owner}/{repo}/{number}` |

### Stage Progress Indicator
Visual 5-stage progress bar: Ask -> Plan -> Build -> Review -> Deploy
- Current stage highlighted
- Previous stages shown as completed

### Linked Repos Section
Shows each linked repo with: full name, language, stars, forks, open issues.

---

## 6. PR Viewer

**URL:** `/pr/:owner/:repo/:number`

### Layout
- PR metadata header (title, author, branches, stats)
- File changes list with diff viewer

### Display Elements
| Element | Data |
|---------|------|
| PR Title | PR title text |
| Author | PR author username |
| Branches | `head_branch` -> `base_branch` |
| Stats | `+additions` / `-deletions` / `files changed` |
| Status badge | open/closed/merged |

### Buttons
| Button | Action |
|--------|--------|
| **Back** | Navigates back to project detail |
| **File name** (clickable) | Expands/collapses file diff |

### Diff Viewer
Each file shows:
- Filename with status (added/modified/removed)
- Addition/deletion counts
- Unified diff view with syntax highlighting (green for additions, red for deletions)

---

## 7. Analytics

**URL:** `/analytics`

### Layout
- Metrics row (4 cards)
- Charts grid (bar chart, pie chart, team table)

### Charts
| Chart | Type | Data |
|-------|------|------|
| Stage Distribution | Bar chart (Recharts) | Projects per stage |
| Project Status | Pie chart (Recharts) | Active vs completed vs on-hold |
| Team Performance | Table | Team name, project count, avg completion |
| Project Breakdown | Data table | All projects with metrics |

### Interactive Elements
- Charts are rendered with Recharts library (tooltips on hover)
- No action buttons on this page — it is read-only analytics

---

## 8. Settings

**URL:** `/settings`

### Layout
- API Key Cards row (3 cards)
- Feature Toggles section
- Configuration Options section

### API Key Cards

#### GitHub API Key Card
| Element | Action |
|---------|--------|
| Status indicator | Green dot = configured, Amber dot = not configured |
| Rate limit display | Shows remaining/total requests |
| **Configure/Update** button | Opens GitHub API Key modal |

#### OpenAI API Key Card
| Element | Action |
|---------|--------|
| Status indicator | Green dot = configured, Amber dot = not configured |
| Model display | Shows current model (gpt-4o-mini) |
| **Configure/Update** button | Opens OpenAI API Key modal |

#### Token Usage Card
| Element | Action |
|---------|--------|
| **View Log** button | Opens Token Usage modal |

### Modals

#### GitHub API Key Modal
| Element | Action |
|---------|--------|
| Token input (password) | Enter `ghp_...` token |
| **Cancel** button | Closes modal |
| **Save** button | Calls `POST /api/analysis/api-key`, validates token, updates status |

#### OpenAI API Key Modal
| Element | Action |
|---------|--------|
| API Key input (password) | Enter `sk-...` key |
| **Cancel** button | Closes modal |
| **Save** button | Calls `POST /api/llm/configure-key`, validates key, updates status |

#### Token Usage Modal
| Element | Data |
|---------|------|
| Total tokens | Sum of all consumed tokens |
| Usage log table | Action name, token count, timestamp for each operation |

### Feature Toggles
| Toggle | Default | Description |
|--------|---------|-------------|
| Auto-sync repos | ON | Automatically sync repo data |
| PR notifications | ON | Notify on PR activity |
| CI monitoring | ON | Monitor CI/CD pipelines |
| Code review reminders | OFF | Remind about pending reviews |

### Configuration Options (Select Dropdowns)
| Option | Choices | Default |
|--------|---------|---------|
| Branch naming convention | `feature/`, `fix/`, `dev/`, `release/` | `feature/` |
| PR review workflow | `required`, `optional`, `auto-merge` | `required` |
| Notification channel | `in-app`, `email`, `slack`, `teams` | `in-app` |

---

## 9. Orchestration

**URL:** `/orchestration`

### Layout
- Header: "Multi-Repo Orchestration"
- Repo cards grid (all repos across all projects)

### Display Elements
Each repo card shows:
- Repo full name (owner/repo)
- Parent project name
- Language, stars, forks, open issues
- Last synced timestamp

### Buttons
| Button | Action |
|--------|--------|
| **Repo card** | Display only — shows repo details inline |

### Data Source
Fetches all projects via `GET /api/projects`, then for each linked repo calls `GET /api/github/repos/{owner}/{repo}` to get live GitHub data.

---

## 10. Repo Analysis

**URL:** `/repo-analysis`

### Modes (Tabs)
| Tab | Description |
|-----|-------------|
| **Single Repo** (default) | Analyze one repository |
| **Multi-Repo** | Analyze multiple repositories together |

### Single Repo Mode

#### Fields
| Field | Type | Placeholder |
|-------|------|-------------|
| Owner | text | `e.g., facebook` |
| Repository | text | `e.g., react` |

Accepts: `owner/repo`, `https://github.com/owner/repo`, or separate owner + repo fields.

#### Buttons
| Button | Action |
|--------|--------|
| **Analyze** | Calls `POST /api/analysis/repo`, shows results below |

### Multi-Repo Mode

#### Fields
- Dynamic list of owner/repo pairs (add more with button)

#### Buttons
| Button | Action |
|--------|--------|
| **Add Repo** | Adds a new owner/repo input row |
| **Remove** (X icon) | Removes a repo row |
| **Analyze All** | Calls `POST /api/analysis/multi-repo`, shows all results |

### Results Display
Expandable accordion for each repo showing:
- **Metadata**: stars, forks, language, default branch, open issues
- **Architecture Notes**: detected patterns (src/, app/, Docker, CI/CD, tests)
- **Dependencies**: grouped by package manager
- **File Tree**: up to 300 files
- **README**: first 8,000 characters

---

## 11. Blueprint Generator

**URL:** `/blueprint`

### Modes (Tabs)
| Tab | Description |
|-----|-------------|
| **Standard** | Multi-repo blueprint generation |
| **Focused** | Single-repo, scoped to a specific feature/layer |

### Standard Mode

#### Fields
- Dynamic list of owner/repo pairs

#### Buttons
| Button | Action |
|--------|--------|
| **Add Repo** | Adds a new repo input row |
| **Remove** (X icon) | Removes a repo row |
| **Generate Blueprint** | Calls `POST /api/analysis/blueprint`, synthesizes AI-ready prompt |
| **Copy to Clipboard** | Copies the generated prompt text |
| **Enhance with AI** | Calls `POST /api/llm/enhance-blueprint` (requires OpenAI key) |

### Focused Mode

#### Fields
| Field | Type | Required | Placeholder |
|-------|------|----------|-------------|
| Owner | text | Yes | `e.g., facebook` |
| Repository | text | Yes | `e.g., react` |
| Focus Area | text | Yes | `e.g., authentication, API layer, database` |
| Goal | text | No | `e.g., understand and replicate` |

#### Buttons
| Button | Action |
|--------|--------|
| **Generate Focused Blueprint** | Calls `POST /api/analysis/blueprint/focused` |
| **Copy to Clipboard** | Copies the focused prompt text |

### Results Display
- Generated prompt in a scrollable code block
- Token estimate badge (approximate token count)
- Repos analyzed count (Standard mode)
- Focus area and repo name (Focused mode)

---

## 12. Doc Generator

**URL:** `/doc-generator`

### Fields
| Field | Type | Required |
|-------|------|----------|
| Owner | text | Yes |
| Repository | text | Yes |

### Section Checkboxes
| Section | Default | What It Generates |
|---------|---------|-------------------|
| Overview | ON | Repo description, language, stats |
| Architecture | ON | Detected patterns, key directories |
| API Reference | ON | Route/controller/handler files |
| Setup Guide | ON | Prerequisites, install commands |
| Testing | ON | Test files, framework-specific run commands |
| Deployment | ON | Docker, CI/CD configuration |

### Buttons
| Button | Action |
|--------|--------|
| **Generate Documentation** | Calls `POST /api/analysis/docs/generate` |
| **Copy** (per section) | Copies individual section content |
| **Copy All Sections** | Copies all generated documentation |
| **Section header** (clickable) | Expands/collapses section content |

---

## 13. Ask Mode

**URL:** `/ask` (also accessible via `/stages/ask` sidebar link)

### Layout
- Chat interface with message history
- Optional repo context panel
- Suggestion cards (when empty)

### Interactive Elements
| Element | Action |
|---------|--------|
| **Add repo context** toggle | Shows/hides textarea for pasting repo analysis or README content |
| **Suggestion cards** (4 predefined) | Clicking fills the input with the suggestion text |
| **Message input** (textarea) | Type your question |
| **Send button** | Sends question to `POST /api/llm/ask` |

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| **Enter** | Send message |
| **Shift+Enter** | New line in message |

### Message Display
- User messages: blue bubbles, right-aligned
- AI responses: white bubbles with blue bot icon, left-aligned
- Loading state: spinning loader in bot bubble
- Token count shown below each AI response
- Error banner shown below chat area on failure

---

## 14. Plan Mode

**URL:** `/plan` (also accessible via `/stages/plan` sidebar link)

### Layout
- Input form card
- Advanced options (collapsible)
- Results section

### Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Project / Feature Description | textarea | Yes | What you want to plan |
| Repo Context | textarea | No | Paste existing code/architecture (advanced) |
| Constraints | textarea | No | Budget, timeline, tech restrictions (advanced) |

### Buttons
| Button | Action |
|--------|--------|
| **Show/Hide advanced options** | Toggles Repo Context and Constraints fields |
| **Generate Engineering Plan** | Calls `POST /api/llm/plan`, shows structured plan |
| **Copy Plan** | Copies the full plan text to clipboard |

### Results Display
- Phase badges (extracted from plan text)
- Full plan in scrollable code block
- Token count and phase count

---

## 15. Stage Pages (Build, Review, Deploy)

**URL:** `/stages/:stage` where stage = `build`, `review`, or `deploy`

### Layout
- Back to Dashboard link
- Stage header with icon and description
- Three-column grid: Activities, Deliverables, Stage Gates

### Display (Read-Only, No Action Buttons)
| Column | Content |
|--------|---------|
| **Key Activities** | Checklist of what happens during this stage |
| **Deliverables** | What this stage produces (green check icons) |
| **Stage Gates** | Criteria to meet before proceeding (checkbox icons) |

### Stage Data
| Stage | Activities | Deliverables | Gates |
|-------|-----------|--------------|-------|
| Build | 5 activities (TDD, code reviews, CI/CD, etc.) | 5 deliverables (working code, tests, docs, etc.) | 4 gates (coverage, CI green, security, patterns) |
| Review | 5 activities (security scan, perf test, etc.) | 5 deliverables (audit report, perf results, etc.) | 4 gates (no critical bugs, security, perf, a11y) |
| Deploy | 5 activities (blue/green deploy, health check, etc.) | 5 deliverables (runbook, dashboards, rollback, etc.) | 4 gates (staging verified, rollback tested, etc.) |

---

## 16. Docs Center

**URL:** `/docs`

### Layout
- Header: "Docs Center"
- Resource cards grid (2 columns)

### Resource Cards
| Card | Link | External? |
|------|------|-----------|
| ZEF — Zinnia Engineering Foundation | `https://github.com/KarthikKaruppasamy880/ZEF` | Yes (new tab) |
| ZECT Architecture Guide | `#` (placeholder) | No |
| Multi-Repo Orchestration | `#` (placeholder) | No |
| Security & Compliance | `#` (placeholder) | No |
| Getting Started | `#` (placeholder) | No |

### Buttons
| Element | Action |
|---------|--------|
| **Card** (clickable) | External links open in new tab; placeholder links do nothing |

---

## Global Navigation (Sidebar)

### Navigation Section
| Item | URL | Icon |
|------|-----|------|
| Dashboard | `/` | LayoutDashboard |
| Projects | `/projects` | FolderKanban |
| Orchestration | `/orchestration` | GitBranch |
| Repo Analysis | `/repo-analysis` | Microscope |
| Blueprint | `/blueprint` | Sparkles |
| Doc Generator | `/doc-generator` | BookOpen |
| Analytics | `/analytics` | BarChart3 |
| Docs Center | `/docs` | FileText |
| Settings | `/settings` | Settings |

### Workflow Stages Section
| Item | URL | Icon |
|------|-----|------|
| Ask Mode | `/stages/ask` | MessageSquare |
| Plan Mode | `/stages/plan` | ClipboardList |
| Build Phase | `/stages/build` | Hammer |
| Review | `/stages/review` | Search |
| Deployment | `/stages/deploy` | Rocket |

### Footer
| Element | Action |
|---------|--------|
| **Sign Out** button | Calls `POST /api/auth/logout`, clears localStorage token, redirects to Login |
