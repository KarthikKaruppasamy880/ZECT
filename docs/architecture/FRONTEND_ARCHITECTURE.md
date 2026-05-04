# ZECT — Frontend Architecture

## Overview

The ZECT frontend is a **React 18 + TypeScript** single-page application built with **Vite 6** for fast development and optimized production builds. It uses **Tailwind CSS** for styling and **Recharts** for data visualization.

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | React | 18.x |
| Language | TypeScript | 5.x |
| Build Tool | Vite | 6.x |
| Styling | Tailwind CSS | 4.x |
| Routing | React Router | 7.x |
| Charts | Recharts | 2.x |
| Icons | Lucide React | 0.4x |
| HTTP Client | Native Fetch API | — |

---

## Directory Structure

```
frontend/
├── src/
│   ├── App.tsx              # Root component, route definitions
│   ├── main.tsx             # Entry point, React DOM render
│   ├── components/
│   │   └── Sidebar.tsx      # Shared sidebar navigation
│   ├── pages/
│   │   ├── Dashboard.tsx    # Home page with metrics overview
│   │   ├── Projects.tsx     # Project listing with filters
│   │   ├── ProjectDetail.tsx# Individual project view
│   │   ├── CreateProject.tsx# New project form
│   │   ├── AskMode.tsx      # AI conversational assistant
│   │   ├── PlanMode.tsx     # AI engineering plan generator
│   │   ├── BlueprintGenerator.tsx  # Multi-repo blueprint synthesis
│   │   ├── CodeReview.tsx   # AI code review engine
│   │   ├── RepoAnalysis.tsx # Repository structure analysis
│   │   ├── DocGenerator.tsx # Documentation generator
│   │   ├── PRViewer.tsx     # Pull request viewer
│   │   ├── Orchestration.tsx# Multi-repo orchestration
│   │   ├── Analytics.tsx    # Metrics and charts
│   │   ├── Settings.tsx     # Feature toggles and configuration
│   │   ├── Docs.tsx         # Documentation center
│   │   └── Login.tsx        # Authentication page
│   ├── lib/
│   │   └── api.ts           # API client helper functions
│   ├── types/
│   │   └── index.ts         # TypeScript type definitions
│   └── index.css            # Global styles + Tailwind imports
├── public/                  # Static assets
├── package.json             # Dependencies
├── vite.config.ts           # Build configuration
├── tailwind.config.js       # Tailwind customization
└── tsconfig.json            # TypeScript configuration
```

---

## Page Architecture

### Navigation (15 pages)

| Category | Page | Route | Purpose |
|----------|------|-------|---------|
| **Navigation** | Dashboard | `/` | Metrics overview, token usage, projects |
| | Projects | `/projects` | Project listing with status filters |
| | Project Detail | `/projects/:id` | Single project view |
| | Create Project | `/projects/new` | New project creation form |
| | Orchestration | `/orchestration` | Multi-repo management |
| | Repo Analysis | `/repo-analysis` | GitHub repo structure analysis |
| | Blueprint | `/blueprint` | AI prompt/blueprint generator |
| | Doc Generator | `/doc-generator` | Documentation generation |
| | Code Review | `/code-review` | AI-powered code review |
| | Analytics | `/analytics` | Charts, metrics, breakdowns |
| | Docs Center | `/docs` | Documentation viewer |
| | Settings | `/settings` | Configuration and toggles |
| **Workflow** | Ask Mode | `/ask` | AI Q&A assistant |
| | Plan Mode | `/plan` | AI plan generator |
| | Build Phase | `/stages/build` | Build stage info |
| | Review | `/stages/review` | Review stage info |
| | Deployment | `/stages/deploy` | Deploy stage info |

---

## Component Patterns

### Layout Pattern

```tsx
// Every page follows this pattern:
<div className="flex h-screen">
  <Sidebar />
  <main className="flex-1 overflow-auto p-6">
    {/* Page content */}
  </main>
</div>
```

### API Communication Pattern

```tsx
// lib/api.ts provides typed API calls
import { api } from '../lib/api';

// Usage in components
const projects = await api.getProjects();
const review = await api.runCodeReview({ owner, repo, pr });
```

### State Management

- **Local state** via `useState` for component-level data
- **Effect hooks** via `useEffect` for data fetching on mount
- **No global state library** — props drilling kept shallow
- **Auth state** stored in `localStorage` (token-based)

---

## Responsive Design Requirements

### Breakpoints

| Breakpoint | Width | Target |
|-----------|-------|--------|
| `sm` | ≥640px | Mobile landscape |
| `md` | ≥768px | Tablet |
| `lg` | ≥1024px | Desktop |
| `xl` | ≥1280px | Large desktop |

### Mobile Compatibility

- **Sidebar**: Must collapse to icon-only rail on mobile, expandable via hamburger menu
- **Cards/Grids**: Switch from multi-column to single-column on small screens
- **Tables**: Horizontally scrollable on mobile
- **Forms**: Full-width inputs on mobile
- **Charts**: Responsive container sizing

### Browser Compatibility

| Browser | Minimum Version |
|---------|----------------|
| Chrome | 90+ |
| Firefox | 88+ |
| Safari | 14+ |
| Edge | 90+ |
| Mobile Safari | iOS 14+ |
| Chrome Android | 90+ |

---

## Styling Conventions

1. **Tailwind-first** — all styling via utility classes
2. **Dark theme** — dark background (`bg-slate-900`) with light text
3. **Card pattern** — `bg-slate-800 rounded-xl border border-slate-700 p-6`
4. **Active nav** — `bg-blue-600/20 text-blue-400 border-l-2 border-blue-400`
5. **Buttons** — primary: `bg-blue-600 hover:bg-blue-700`, secondary: `bg-slate-700`
6. **Status colors** — green (success), yellow (warning), red (error), blue (info)

---

## Key UI Components

### Sidebar (`components/Sidebar.tsx`)

- Fixed left sidebar with navigation links
- Two sections: "Navigation" and "Workflow Stages"
- Active route highlighting
- Sign Out button at bottom
- **TODO**: Collapsible/expandable toggle for mobile

### Dashboard (`pages/Dashboard.tsx`)

- Summary cards (Total Projects, Active, Token Savings, Alerts)
- Token Usage Control panel (API calls, tokens, cost)
- Stage Distribution visualization
- Project cards with progress bars

### Code Review Engine (`pages/CodeReview.tsx`)

- PR Review and Code Snippet tabs
- Input form (owner, repo, PR number)
- Results display with severity badges
- "Generate Fix Prompt" output for AI tools

---

## Build & Development

```bash
# Development
npm run dev          # Start Vite dev server on :5173

# Production build
npm run build        # Output to dist/

# Preview production build
npm run preview      # Serve dist/ locally

# Type checking
npx tsc --noEmit    # Check types without building
```

---

## Environment Variables

```env
# frontend/.env (optional)
VITE_API_URL=http://localhost:8000   # Backend API base URL
```

All environment variables must be prefixed with `VITE_` to be exposed to the client bundle.
