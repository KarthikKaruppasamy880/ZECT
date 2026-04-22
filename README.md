# ZECT — Engineering Delivery Control Tower

An internal AI-governed engineering productivity platform for Zinnia that standardizes how teams plan, code, review, and deploy software. Built using the [Zinnia Engineering Foundation (ZEF)](https://github.com/KarthikKaruppasamy880/ZEF) as the standards backbone.

## Overview

ZECT provides a structured 5-stage delivery pipeline with multi-repo orchestration, analytics, and platform-wide configuration:

| Stage | Purpose |
|-------|---------|
| **Ask Mode** | Gather business goals, users, constraints, and dependencies |
| **Plan Mode** | Define architecture, APIs, database schema, and deployment strategy |
| **Build Phase** | Track frontend, backend, and integration development progress |
| **Review** | Automated code analysis with severity-classified findings |
| **Deployment Readiness** | Pre-production checklist for infrastructure, security, monitoring |

### Key Features

- **Multi-Repo Orchestration** — 12 repositories across 3 projects with dependency health maps, CI status, sync tracking, and cross-repo event timelines
- **Project-Specific Stage Data** — Each of the 6 seeded projects has unique requirements, plans, tasks, review findings, and deploy checklists
- **Analytics Dashboard** — Stage distribution, weekly activity charts, team performance, repository health overview
- **Platform Settings** — Feature toggles, configuration options, integration status, team roles and permissions
- **Workflow Stage Guides** — Detailed explanation pages for each stage with gate criteria and example outputs

## Tech Stack

- **Framework:** Next.js 16 (App Router with Turbopack)
- **Language:** TypeScript (strict mode)
- **Styling:** Tailwind CSS v4
- **Data:** Mock TypeScript data modules (prototype phase — no backend required)
- **Build:** 0 lint errors, 0 type errors, 0 build warnings

## Getting Started

```bash
# Clone the repository
git clone https://github.com/KarthikKaruppasamy880/ZECT.git
cd ZECT

# Install dependencies
npm install

# Start development server
npm run dev

# Quality checks
npm run lint          # ESLint
npx tsc --noEmit      # TypeScript type check
npm run build         # Production build
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

## Project Structure

```
src/
├── app/                           # Next.js App Router pages
│   ├── page.tsx                   # Dashboard
│   ├── analytics/page.tsx         # Analytics & Reporting
│   ├── settings/page.tsx          # Platform Settings
│   ├── orchestration/page.tsx     # Global Multi-Repo Orchestration
│   ├── docs/page.tsx              # Docs Center
│   ├── stages/                    # Workflow stage guide pages
│   │   ├── ask/page.tsx           # Ask Mode guide
│   │   ├── plan/page.tsx          # Plan Mode guide
│   │   ├── build/page.tsx         # Build Phase guide
│   │   ├── review/page.tsx        # Review guide
│   │   └── deploy/page.tsx        # Deployment guide
│   └── projects/
│       ├── page.tsx               # Projects list with search
│       ├── new/page.tsx           # Create project wizard
│       └── [id]/
│           ├── layout.tsx         # Project detail layout with stage tracker
│           ├── page.tsx           # Auto-redirect to current stage
│           ├── ask/page.tsx       # Project-specific Ask Mode
│           ├── plan/page.tsx      # Project-specific Plan Mode
│           ├── build/page.tsx     # Project-specific Build Phase
│           ├── review/page.tsx    # Project-specific Review
│           ├── deploy/page.tsx    # Project-specific Deployment
│           └── orchestration/     # Project-level repo orchestration
├── components/
│   ├── layout/                    # Sidebar, Header
│   ├── dashboard/                 # MetricCard, ProjectCard, RecentActivity
│   ├── orchestration/             # RepoCard, DependencyMap, Timeline, Summary
│   ├── projects/                  # StageTracker
│   ├── stages/                    # AskModeView, PlanModeView, BuildPhaseView, ReviewView, DeployReadinessView
│   └── shared/                    # Card, StatusPill, ProgressBar, SeverityBadge
├── data/
│   ├── projects.ts                # 6 seeded projects with metrics
│   ├── project-stages.ts          # Project-specific stage data for all 6 projects
│   ├── orchestration.ts           # 12 repos, 14 dependencies, 17 events across 3 projects
│   ├── dashboard.ts               # Dashboard metrics and activity
│   └── stage-details.ts           # Sample stage data (shared/fallback)
├── lib/utils.ts                   # Utility functions
└── types/index.ts                 # TypeScript interfaces
```

## Pages (19 routes)

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Executive overview with metrics, project cards, activity feed |
| Projects | `/projects` | Filterable project list with search |
| Create Project | `/projects/new` | 3-step wizard to create a new project |
| Ask Mode | `/projects/[id]/ask` | Project-specific requirements summary |
| Plan Mode | `/projects/[id]/plan` | Project-specific architecture and API plan |
| Build Phase | `/projects/[id]/build` | Project-specific task tracking with progress |
| Review | `/projects/[id]/review` | Project-specific code analysis findings |
| Deployment | `/projects/[id]/deploy` | Project-specific readiness checklist |
| Project Orchestration | `/projects/[id]/orchestration` | Project-level multi-repo view |
| Global Orchestration | `/orchestration` | Cross-project repo health and events |
| Analytics | `/analytics` | Stage distribution, team performance, charts |
| Settings | `/settings` | Feature toggles, integrations, team roles |
| Docs Center | `/docs` | Searchable documentation hub |
| Ask Mode Guide | `/stages/ask` | Workflow stage explanation and gate criteria |
| Plan Mode Guide | `/stages/plan` | Workflow stage explanation and gate criteria |
| Build Phase Guide | `/stages/build` | Workflow stage explanation and gate criteria |
| Review Guide | `/stages/review` | Workflow stage explanation and gate criteria |
| Deployment Guide | `/stages/deploy` | Workflow stage explanation and gate criteria |

## Design

- **Sidebar:** Dark (slate-900) with navigation, workflow stages, and branding
- **Content area:** Light (slate-50) with rounded white cards
- **Enterprise-grade:** Premium internal product feel, suitable for leadership demos
- **Responsive:** Optimized for desktop and tablet viewports
- **UI elements:** Status pills, progress bars, severity badges, stage trackers, dependency maps

## Prototype Scope

This is a **frontend prototype** with comprehensive mock data. No backend, no authentication, no real AI calls.

### Seeded Mock Projects (6)

| Project | Current Stage | Team | Completion |
|---------|--------------|------|------------|
| Policy Admin Modernization | Build | Platform Engineering | 55% |
| Claims Processing API | Review | Claims Engineering | 78% |
| Agent Portal Redesign | Plan | Product Engineering | 28% |
| Underwriting Rules Engine | Deploy | Underwriting Tech | 92% |
| Customer Notifications Service | Complete | Platform Engineering | 100% |
| Document Intelligence Pipeline | Ask | AI/ML Engineering | 8% |

### Multi-Repo Orchestration (12 repos, 3 projects)

| Project | Repos | Dependencies | Events |
|---------|-------|-------------|--------|
| Policy Admin Modernization | 4 (web, API, shared-types, infra) | 4 | 3 |
| Claims Processing API | 5 (intake, adjudication, shared-models, event-bus, portal) | 6 | 5 |
| Agent Portal Redesign | 3 (web, BFF, design-system) | 2 | 2 |

## Quality

```
Lint:       0 errors, 0 warnings
TypeCheck:  0 errors
Build:      Compiled successfully (Turbopack)
Routes:     19 total (12 static, 7 dynamic)
```

## Recommended Next Phase

1. Add state persistence (localStorage or backend API)
2. Build FastAPI backend with PostgreSQL
3. Integrate real AI analysis via LLM providers
4. Add authentication and role-based access control
5. Implement real deployment readiness checks
6. Add CI/CD pipeline configuration
7. Connect to real GitHub/GitLab APIs for repo orchestration
8. Add real-time WebSocket updates for stage transitions

## ZEF Integration

This project uses [ZEF (Zinnia Engineering Foundation)](https://github.com/KarthikKaruppasamy880/ZEF) for:
- Workflow standards (5-phase model)
- Playbook-driven development patterns
- Context management across AI sessions
- Prompt templates for repo analysis and enhancement

## License

Internal use only — Zinnia.
