# ZECT — Sample Test Cases

## Overview

This document provides sample test cases for validating ZECT functionality across all sidebar sections. These tests can be run manually or adapted for automated testing frameworks (Playwright, Cypress, Jest).

---

## 1. Authentication Tests

### TC-AUTH-001: Successful Login
- **Steps:** Navigate to `/`, enter email `karthik.karuppasamy@Zinnia.com` and password `Karthik@1234`, click Sign In
- **Expected:** Redirects to Dashboard, shows 6 projects
- **Failure Scenario:** Wrong password shows "Invalid credentials" error message

### TC-AUTH-002: Invalid Credentials
- **Steps:** Enter wrong email/password, click Sign In
- **Expected:** Error message displayed, stays on login page
- **Failure Scenario:** App crashes or shows generic error

### TC-AUTH-003: Session Persistence
- **Steps:** Log in, refresh the page
- **Expected:** User stays logged in (token stored in localStorage)

### TC-AUTH-004: Sign Out
- **Steps:** Click "Sign Out" in sidebar footer
- **Expected:** Redirects to login page, session cleared

---

## 2. Dashboard Tests

### TC-DASH-001: Dashboard Data Load
- **Steps:** Navigate to `/` after login
- **Expected:** Shows Total Projects (6), Active Projects (5), Avg Token Savings (35.7%), Risk Alerts (11)

### TC-DASH-002: Token Usage Panel
- **Steps:** View Token Usage Control section on dashboard
- **Expected:** Shows Total API Calls, Total Tokens, Estimated Cost with real data from backend

### TC-DASH-003: Stage Distribution Chart
- **Steps:** View Stage Distribution section
- **Expected:** Shows bar chart with ask, plan, build, review, deploy counts

### TC-DASH-004: Project Cards Navigation
- **Steps:** Click on any project card
- **Expected:** Navigates to `/projects/{id}` with project details

---

## 3. Projects Tests

### TC-PROJ-001: List All Projects
- **Steps:** Navigate to `/projects`
- **Expected:** Shows 6 project cards with name, status, completion %, team

### TC-PROJ-002: Filter by Status
- **Steps:** Click "active" filter button
- **Expected:** Shows only active projects (5), hides completed project

### TC-PROJ-003: Create New Project
- **Steps:** Click "New Project", fill form, submit
- **Expected:** New project appears in list with "active" status

### TC-PROJ-004: Empty State
- **Steps:** Filter by "on-hold" (no projects have this status)
- **Expected:** Shows "No projects found" message gracefully

---

## 4. Ask Mode Tests

### TC-ASK-001: Load Ask Mode Page
- **Steps:** Navigate to `/ask`
- **Expected:** Shows textarea, model selector with 9 models, quick prompts

### TC-ASK-002: Model Selection
- **Steps:** Change model dropdown to "Llama 3.1 8B (Free)"
- **Expected:** Model updates, shown in selector

### TC-ASK-003: Submit Question (with API key)
- **Steps:** Type a question, press Enter
- **Expected:** Shows loading state, then AI response with model/token info

### TC-ASK-004: Submit Question (without API key)
- **Steps:** Remove OPENAI_API_KEY from .env, type a question
- **Expected:** Shows error "OpenAI API key not configured" gracefully

### TC-ASK-005: Quick Prompt Selection
- **Steps:** Click "How should I structure a microservices migration?"
- **Expected:** Question auto-fills in textarea

### TC-ASK-006: File Attachment Panel
- **Steps:** Click "Add files, repos, snippets"
- **Expected:** Shows file attachment interface

---

## 5. Plan Mode Tests

### TC-PLAN-001: Load Plan Mode Page
- **Steps:** Navigate to `/plan`
- **Expected:** Shows description textarea, model selector, file attachment button

### TC-PLAN-002: Generate Plan (with API key)
- **Steps:** Enter "Build a REST API for user management", click Generate
- **Expected:** Shows loading, then structured plan with phases

### TC-PLAN-003: Generate Plan (empty input)
- **Steps:** Click "Generate Engineering Plan" with empty textarea
- **Expected:** Button disabled or shows validation error

### TC-PLAN-004: Advanced Options
- **Steps:** Click "Show advanced options"
- **Expected:** Shows additional configuration fields (constraints, etc.)

---

## 6. Build Phase Tests

### TC-BUILD-001: Load Build Phase Page
- **Steps:** Navigate to `/build`
- **Expected:** Shows plan step textarea, tech stack input, model selector, templates

### TC-BUILD-002: Quick Templates
- **Steps:** Click "Create a REST API endpoint with CRUD operations"
- **Expected:** Template text fills the plan step textarea

### TC-BUILD-003: Generate Code (with API key)
- **Steps:** Enter description, click "Generate Code"
- **Expected:** Shows loading, then generated code with syntax highlighting

### TC-BUILD-004: Generate Code (empty input)
- **Steps:** Click "Generate Code" with empty textarea
- **Expected:** Button disabled (it is disabled when textarea is empty)

### TC-BUILD-005: Context Files Panel
- **Steps:** Click "Add" button next to "Context Files (0)"
- **Expected:** Shows file/repo/snippet addition interface

---

## 7. Review Phase Tests

### TC-REV-001: Load Review Phase Page
- **Steps:** Navigate to `/review`
- **Expected:** Shows code textarea, model selector, language dropdown, severity filter

### TC-REV-002: Run Review (with API key)
- **Steps:** Paste code, select language, click "Run Review"
- **Expected:** Shows loading, then review findings with severity badges

### TC-REV-003: Run Review (empty code)
- **Steps:** Click "Run Review" with empty textarea
- **Expected:** Button disabled when no code entered

### TC-REV-004: Language Selection
- **Steps:** Change language dropdown from TypeScript to Python
- **Expected:** Language updates for review context

---

## 8. Deployment Phase Tests

### TC-DEP-001: Load Deployment Page
- **Steps:** Navigate to `/deploy`
- **Expected:** Shows Checklist/Runbook tabs, project name input, environment selectors

### TC-DEP-002: Generate Checklist
- **Steps:** Enter project name, select environment, click "Generate Checklist"
- **Expected:** Shows loading, then deployment checklist items

### TC-DEP-003: Switch to Runbook Tab
- **Steps:** Click "Runbook" tab
- **Expected:** Shows runbook-specific form fields (infrastructure, services)

### TC-DEP-004: Empty Project Name
- **Steps:** Try to generate with empty project name
- **Expected:** Button disabled or shows validation

---

## 9. Token Controls Tests

### TC-TOKEN-001: Load Token Controls Page
- **Steps:** Navigate to `/token-controls`
- **Expected:** Shows overview tab with Total Calls, Total Tokens, Total Cost

### TC-TOKEN-002: Tab Navigation
- **Steps:** Click each tab: Overview, User Activity, Teams, Budget, Trends
- **Expected:** Each tab loads appropriate content

### TC-TOKEN-003: Budget Configuration
- **Steps:** Go to Budget tab, change daily limit, click Save
- **Expected:** Budget saves successfully, shows confirmation

### TC-TOKEN-004: Empty State (No Usage)
- **Steps:** View page with fresh database (no token usage yet)
- **Expected:** Shows "No usage data yet" message gracefully

### TC-TOKEN-005: User Activity (No Users)
- **Steps:** Go to User Activity tab with no registered users
- **Expected:** Shows "No users registered yet. Users will appear here once SSO is configured."

---

## 10. Settings Tests

### TC-SET-001: Load Settings Page
- **Steps:** Navigate to `/settings`
- **Expected:** Shows API key cards, feature toggles, configuration options

### TC-SET-002: Toggle Feature
- **Steps:** Click "Automated Code Review" toggle
- **Expected:** Toggle switches state, persists on page refresh

### TC-SET-003: Configure API Key
- **Steps:** Click "Configure" on OpenAI API Key card
- **Expected:** Shows input field for API key entry

### TC-SET-004: Change Configuration Option
- **Steps:** Change "Default Starting Stage" dropdown
- **Expected:** Selection saves to backend

---

## 11. Orchestration Tests

### TC-ORCH-001: Load Orchestration Page
- **Steps:** Navigate to `/orchestration`
- **Expected:** Shows connected repos with stats (Total Repos, Projects, Connected)

### TC-ORCH-002: Repo Cards
- **Steps:** View repo cards
- **Expected:** Each card shows repo name, project link, GitHub link, stats

### TC-ORCH-003: No Repos Connected
- **Steps:** View with project that has no repos
- **Expected:** Shows appropriate empty state

---

## 12. Repo Analysis Tests

### TC-REPO-001: Load Repo Analysis Page
- **Steps:** Navigate to `/repo-analysis`
- **Expected:** Shows Single Repo / Multi-Repo tabs with owner/repo inputs

### TC-REPO-002: Analyze Real Repo
- **Steps:** Enter "KarthikKaruppasamy880" / "ZECT", click Analyze
- **Expected:** Shows repo structure, README, dependencies, architecture

### TC-REPO-003: Analyze Non-Existent Repo
- **Steps:** Enter "nonexistent" / "fakerepo", click Analyze
- **Expected:** Shows error "Repository not found" gracefully

---

## 13. Blueprint Tests

### TC-BP-001: Load Blueprint Page
- **Steps:** Navigate to `/blueprint`
- **Expected:** Shows Standard/Focused tabs, owner/repo inputs, "How It Works" info

### TC-BP-002: Generate Blueprint
- **Steps:** Enter owner/repo, click "Generate Blueprint"
- **Expected:** Shows loading, then generated blueprint prompt

### TC-BP-003: Focused Mode
- **Steps:** Switch to Focused tab
- **Expected:** Shows additional "Focus Area" and "Goal" fields

---

## 14. Skill Library Tests

### TC-SKILL-001: Load Skill Library
- **Steps:** Navigate to `/skills`
- **Expected:** Shows category filters, "No skills saved yet" empty state

### TC-SKILL-002: Create New Skill
- **Steps:** Click "New Skill", fill form, submit
- **Expected:** Skill appears in list with name, description, category

### TC-SKILL-003: Filter by Category
- **Steps:** Click "Testing" category filter
- **Expected:** Shows only testing-category skills (or empty state)

### TC-SKILL-004: Auto-Detect Patterns
- **Steps:** Click "Auto-Detect" (requires API key)
- **Expected:** Opens code input for pattern detection

---

## 15. Sidebar Navigation Tests

### TC-NAV-001: Sidebar Collapse
- **Steps:** Click collapse button (chevron in header)
- **Expected:** Sidebar collapses to icon-only rail (w-16)

### TC-NAV-002: Sidebar Expand
- **Steps:** Click expand button when collapsed
- **Expected:** Sidebar expands to full width (w-56) with labels

### TC-NAV-003: Keyboard Shortcut
- **Steps:** Press Ctrl+B
- **Expected:** Sidebar toggles between collapsed and expanded

### TC-NAV-004: Active Page Highlight
- **Steps:** Navigate to any page
- **Expected:** Current page highlighted in sidebar navigation

### TC-NAV-005: Mobile Hamburger Menu
- **Steps:** View on mobile viewport (< 768px)
- **Expected:** Shows hamburger button, sidebar overlays on toggle

---

## 16. Error Handling Tests

### TC-ERR-001: Backend Down
- **Steps:** Stop backend server, try to load Dashboard
- **Expected:** Shows error message "Failed to fetch" or network error, doesn't crash

### TC-ERR-002: Invalid Auth Token
- **Steps:** Manually corrupt localStorage token, refresh
- **Expected:** Redirects to login page

### TC-ERR-003: API 500 Error
- **Steps:** Cause backend error (e.g., database corruption)
- **Expected:** Frontend shows user-friendly error message

### TC-ERR-004: Network Timeout
- **Steps:** Throttle network to very slow speed
- **Expected:** Shows loading states, eventually shows timeout error

---

## Running These Tests

### Manual Testing
1. Start backend: `cd backend && uvicorn app.main:app --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Execute test cases in order

### Automated Testing (Playwright)
```typescript
import { test, expect } from '@playwright/test';

test('TC-AUTH-001: Successful Login', async ({ page }) => {
  await page.goto('http://localhost:5173');
  await page.fill('input[type="text"]', 'karthik.karuppasamy@Zinnia.com');
  await page.fill('input[type="password"]', 'Karthik@1234');
  await page.click('button[type="submit"]');
  await expect(page.locator('h1')).toContainText('Dashboard');
});

test('TC-DASH-001: Dashboard Data Load', async ({ page }) => {
  // After login
  await expect(page.locator('text=6 Total Projects')).toBeVisible();
  await expect(page.locator('text=5 Active Projects')).toBeVisible();
});

test('TC-NAV-001: Sidebar Collapse', async ({ page }) => {
  await page.click('button[title*="Collapse"]');
  await expect(page.locator('aside')).toHaveClass(/w-16/);
});
```
