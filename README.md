# ZECT — Engineering Delivery Control Tower

An internal AI-governed engineering productivity platform for Zinnia that standardizes how teams plan, code, review, and deploy software.

## Overview

ZECT provides a structured 5-stage delivery pipeline:

| Stage | Purpose |
|-------|---------|
| **Ask Mode** | Gather business goals, users, constraints, and dependencies |
| **Plan Mode** | Define architecture, APIs, database schema, and deployment strategy |
| **Build Phase** | Track frontend, backend, and integration development progress |
| **Review** | Automated code analysis with severity-classified findings |
| **Deployment Readiness** | Pre-production checklist for infrastructure, security, monitoring |

## Tech Stack

- **Framework:** Next.js 15 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Data:** Mock JSON (prototype phase — no backend required)

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── page.tsx           # Dashboard
│   ├── projects/
│   │   ├── page.tsx       # Projects list
│   │   ├── new/page.tsx   # Create project wizard
│   │   └── [id]/
│   │       ├── layout.tsx # Project detail layout with stage tracker
│   │       ├── ask/       # Ask Mode stage
│   │       ├── plan/      # Plan Mode stage
│   │       ├── build/     # Build Phase stage
│   │       ├── review/    # Review stage
│   │       └── deploy/    # Deployment Readiness stage
│   └── docs/page.tsx      # Docs Center
├── components/
│   ├── layout/            # Sidebar, Header
│   ├── dashboard/         # MetricCard, ProjectCard, RecentActivity
│   ├── projects/          # StageTracker
│   ├── stages/            # Ask, Plan, Build, Review, Deploy views
│   └── shared/            # Card, StatusPill, ProgressBar, SeverityBadge
├── data/                  # Mock JSON data
├── lib/                   # Utility functions
└── types/                 # TypeScript interfaces
```

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Executive overview with metrics, project cards, activity feed |
| Projects | `/projects` | Filterable project list with search |
| Create Project | `/projects/new` | 3-step wizard to create a new project |
| Ask Mode | `/projects/[id]/ask` | Requirements summary and breakdown |
| Plan Mode | `/projects/[id]/plan` | Architecture and implementation plan |
| Build Phase | `/projects/[id]/build` | Task tracking with progress bars |
| Review | `/projects/[id]/review` | Code analysis findings by severity |
| Deployment | `/projects/[id]/deploy` | Pre-production readiness checklist |
| Docs Center | `/docs` | Searchable documentation hub |

## Design

- Dark left sidebar with navigation
- Light content area with rounded cards
- Enterprise-grade polish suitable for leadership demos
- Responsive layout optimized for desktop
- Status pills, progress bars, and severity badges

## Prototype Scope

This is a **frontend prototype** with mock data. No backend, no authentication, no real AI calls.

### Seeded Mock Projects

| Project | Stage | Team |
|---------|-------|------|
| Policy Admin Modernization | Build | Platform Engineering |
| Claims Processing API | Review | Claims Engineering |
| Agent Portal Redesign | Plan | Product Engineering |
| Underwriting Rules Engine | Deploy | Underwriting Tech |
| Customer Notifications Service | Complete | Platform Engineering |
| Document Intelligence Pipeline | Ask | AI/ML Engineering |

## Recommended Next Phase

1. Add state persistence (localStorage or backend API)
2. Build FastAPI backend with PostgreSQL
3. Integrate real AI analysis via LLM providers
4. Add authentication and role-based access
5. Implement real deployment readiness checks
6. Add CI/CD pipeline configuration

## License

Internal use only — Zinnia.
