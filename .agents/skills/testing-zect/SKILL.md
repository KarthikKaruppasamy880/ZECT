# ZECT Testing Skill

## Overview
How to test the ZECT (Engineering Delivery Control Tower) Next.js prototype end-to-end.

## Prerequisites
- Node.js 18+ installed
- Dependencies installed (`npm install`)

## Dev Server Setup
```bash
cd /home/ubuntu/repos/ZECT
npm run dev
# Runs on http://localhost:3000
```

## Quality Checks (run before testing UI)
```bash
npm run lint       # ESLint — expect 0 errors
npx tsc --noEmit   # TypeScript — expect 0 errors
npm run build      # Next.js build — expect "Compiled successfully"
```

## Key Pages to Test

| Route | What to verify |
|---|---|
| `/` | Dashboard loads with 4 metric cards, project cards, activity feed |
| `/projects` | 6 project cards with search/filter, "Create New Project" button |
| `/analytics` | 6 metric cards (Total Projects=6, Active=5, Completed=1), stage distribution bars, team performance table |
| `/settings` | 6 feature toggles (4 ON, 2 OFF initially), 4 config selects, 8 integration cards, team roles |
| `/orchestration` | 12 repos across 3 projects, dependency health, CI status |
| `/docs` | Docs Center page loads |

## Project-Specific Stage Data
Each of the 6 projects has unique stage data in `src/data/project-stages.ts`. To verify:

- **proj-001 Build** (`/projects/proj-001/build`): Should show "Set up monorepo with Turborepo" (Sarah Chen), "Build premium calculation engine" (Marcus Johnson, 45%)
- **proj-002 Review** (`/projects/proj-002/review`): Should show 7 findings including "Claim Amount Overflow Not Handled" (critical)
- **proj-003 Review** (`/projects/proj-003/review`): Should show empty state: "No review findings yet"
- **proj-006 Ask** (`/projects/proj-006/ask`): Should show Document Intelligence requirements

## Edge Cases
- **Unmapped project ID**: Navigate to `/projects/proj-999/ask` — should show "No stage data available for this project yet" fallback UI, not Policy Admin data. Check browser console for `[ZECT]` warning.
- **Settings toggle interactivity**: Click any toggle — it should flip state (blue↔gray). State resets on page refresh (expected for prototype).
- **Empty review findings**: proj-003 has 0 findings — ReviewView should show empty message, not a blank list.

## Common Issues
- If dev server port 3000 is already in use, kill the existing process or use `PORT=3001 npm run dev`
- All data is mock data in `src/data/`. No backend or API calls are made.
- Settings toggles use local `useState` — no persistence across refreshes (expected for prototype phase).
- Analytics charts are pure CSS bars, not D3/Chart.js. Bar widths are percentage-based.

## Devin Secrets Needed
None — this is a frontend-only prototype with no authentication or API keys required.
