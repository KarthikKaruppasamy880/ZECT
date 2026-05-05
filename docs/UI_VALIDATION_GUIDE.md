# ZECT — UI Design Validation Guide

## Overview

This guide helps you validate the ZECT UI design, layout, responsiveness, and overall functionality after setting up the application locally.

---

## 1. Visual Design Checklist

### Color Scheme
- [x] Dark sidebar (`bg-slate-900`) with white text
- [x] Light main content area (`bg-slate-50`)
- [x] Accent colors: Blue (primary actions), Purple (Blueprint), Green (success/Token Controls), Orange (warnings)
- [x] Consistent hover states on all interactive elements

### Typography
- [x] Page titles: `text-2xl font-bold text-slate-900`
- [x] Section headers: `text-lg font-semibold`
- [x] Body text: `text-sm text-slate-600`
- [x] Sidebar labels: `text-sm text-slate-300`

### Icons
- [x] Lucide React icons used consistently throughout
- [x] Each sidebar item has a unique, meaningful icon
- [x] Icon sizes: `h-4 w-4` (sidebar), `h-5 w-5` (page headers), `h-6 w-6` (hero sections)

---

## 2. Layout Validation

### Desktop (1920x1080 and above)
1. Open the app at full desktop width
2. Verify:
   - Sidebar is 224px wide (`w-56`) in expanded state
   - Main content fills remaining space
   - No horizontal scrollbars
   - Cards/grids use multi-column layouts
   - Charts render fully without clipping

### Tablet (768px - 1024px)
1. Resize browser to tablet width
2. Verify:
   - Sidebar remains visible but may be collapsible
   - Content adapts to narrower viewport
   - Form fields stack vertically where needed
   - Tables remain readable

### Mobile (< 768px)
1. Resize browser to 375px width (or use DevTools mobile emulation)
2. Verify:
   - Sidebar hidden, hamburger menu visible (top-left)
   - Tapping hamburger opens overlay sidebar
   - Tapping X or outside closes sidebar
   - Content is single-column
   - Buttons are full-width on mobile
   - Text is readable without zooming

---

## 3. Sidebar Validation

### Expanded State
- Header shows "Zinnia Engineering Delivery Control Tower"
- Collapse button (chevron `<`) visible in header area
- Navigation section shows 10 items with icons + labels
- Workflow Stages section shows 7 items with icons + labels
- Footer shows "Zinnia Eng / Internal Platform" + Sign Out button
- Bottom collapse toggle shows chevron + "Collapse" text

### Collapsed State
- Header shows only "Z" letter
- Sidebar width is 64px (`w-16`)
- Only icons visible, no text labels
- Expand button (chevron `>`) visible
- Tooltip appears on hover showing item name

### Keyboard Shortcut
- Press `Ctrl+B` to toggle sidebar
- Works from any page
- Animation is smooth (transition-all duration-300)

---

## 4. Page-by-Page Validation

### Dashboard (`/`)
- [ ] Shows 4 metric cards (Total Projects, Active, Token Savings, Risk Alerts)
- [ ] Token Usage Control panel with real-time data
- [ ] Stage Distribution bar chart (ask/plan/build/review/deploy)
- [ ] Project cards with completion progress bars
- [ ] "View all" link navigates to `/projects`

### Projects (`/projects`)
- [ ] Project list with cards showing status badges
- [ ] Filter buttons: All, active, completed, on-hold
- [ ] "New Project" button (top right)
- [ ] Each card shows: name, status, stage, completion %, savings %, team, repos count

### Orchestration (`/orchestration`)
- [ ] Stats row: Total Repos, Projects, Connected
- [ ] Repo cards with GitHub links
- [ ] Status indicators (Connected badge)
- [ ] Loading state while fetching from GitHub

### Repo Analysis (`/repo-analysis`)
- [ ] Tab toggle: Single Repo / Multi-Repo
- [ ] Owner and Repository input fields
- [ ] "Analyze" button with search icon
- [ ] Results area (empty until analysis run)

### Blueprint (`/blueprint`)
- [ ] Tab toggle: Standard / Focused
- [ ] Owner/Repository inputs
- [ ] "Add Another Repo" button
- [ ] "Generate Blueprint" button (purple)
- [ ] "How It Works" explanation section

### Doc Generator (`/doc-generator`)
- [ ] Owner/Repository inputs
- [ ] Section checkboxes (Overview, Architecture, API Reference, Setup Guide, Testing, Deployment)
- [ ] "Generate Documentation" button (green)

### Code Review (`/code-review`)
- [ ] Tab toggle: PR Review / Code Snippet
- [ ] PR Review: Owner, Repo Name, PR Number inputs
- [ ] Code Snippet: Large textarea for pasting code
- [ ] "Run ZECT Review" button

### Analytics (`/analytics`)
- [ ] 6 metric cards (Total Projects, Active, Token Savings, Risk Alerts, Total Repos, Avg Completion)
- [ ] Stage Distribution chart (bar)
- [ ] Project Status chart (donut)
- [ ] Team Performance chart (bar)
- [ ] Project Breakdown table with sortable columns

### Docs Center (`/docs`)
- [ ] 5 documentation cards in grid layout
- [ ] ZEF link opens GitHub repo
- [ ] Cards have icons and descriptions

### Settings (`/settings`)
- [ ] API key configuration cards (GitHub, OpenAI, Token Usage)
- [ ] Feature Toggles section with switches
- [ ] Configuration Options with dropdowns
- [ ] Status indicators (configured/not configured)

### Ask Mode (`/ask`)
- [ ] Model selector dropdown with 9 models (3 groups)
- [ ] "Add files, repos, snippets" button
- [ ] Large textarea with placeholder
- [ ] 4 quick prompt buttons
- [ ] Send button (disabled when empty)

### Plan Mode (`/plan`)
- [ ] Model selector with cost info
- [ ] Description textarea
- [ ] File attachment button
- [ ] Advanced options toggle
- [ ] "Generate Engineering Plan" button

### Build Phase (`/build`)
- [ ] Plan step textarea (required)
- [ ] Tech stack and file path inputs
- [ ] Model selector with cost info
- [ ] Context Files panel (collapsible)
- [ ] 6 Quick Templates buttons
- [ ] "Generate Code" button (disabled when empty)

### Review Phase (`/review`)
- [ ] Code textarea (required)
- [ ] Model selector
- [ ] Language dropdown (7 languages)
- [ ] Min Severity dropdown (5 levels)
- [ ] "Run Review" button (disabled when empty)

### Deployment (`/deploy`)
- [ ] Tab toggle: Checklist / Runbook
- [ ] Project Name input (required)
- [ ] Tech Stack input
- [ ] Environment, Deployment Type, Infrastructure dropdowns
- [ ] "Generate Checklist/Runbook" button

### Skill Library (`/skills`)
- [ ] "Auto-Detect" and "New Skill" buttons
- [ ] Category filter buttons (All, general, testing, deployment, review, architecture)
- [ ] Skill cards or empty state message
- [ ] Each skill shows name, description, category, usage count

### Token Controls (`/token-controls`)
- [ ] 5 tabs: Overview, User Activity, Teams, Budget, Trends
- [ ] Overview: Total Calls, Total Tokens, Total Cost, Today's Tokens
- [ ] Model Breakdown section
- [ ] Active Users section
- [ ] Budget tab with editable limits
- [ ] SSO-Ready badge

---

## 5. Interaction Validation

### Forms
- [ ] Required fields marked with `*`
- [ ] Disabled buttons when required fields are empty
- [ ] Loading spinners on form submission
- [ ] Success/error messages after API calls
- [ ] Form fields clear after successful submission (where appropriate)

### Error States
- [ ] API errors show user-friendly messages (not raw JSON)
- [ ] Network failures show retry option or helpful message
- [ ] 401 errors redirect to login
- [ ] 503 errors show "Service not configured" message

### Loading States
- [ ] Skeleton loaders or spinners during data fetch
- [ ] Pages don't flash empty then fill with data
- [ ] Long-running operations show progress indication

### Navigation
- [ ] All sidebar links navigate correctly
- [ ] Active page is highlighted in sidebar
- [ ] Browser back/forward buttons work
- [ ] Direct URL access works (e.g., typing `/analytics` in address bar)

---

## 6. Performance Validation

### Page Load Times
- Dashboard: < 2 seconds
- Projects: < 1 second
- Analytics: < 2 seconds (with charts)
- Token Controls: < 1 second
- All other pages: < 1 second

### No Console Errors
1. Open browser DevTools (F12) > Console tab
2. Navigate through all pages
3. Verify: No red error messages in console
4. Warning messages are acceptable but should be minimal

---

## 7. Browser Compatibility

Test on:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

Key things to verify:
- CSS grid/flexbox layouts render correctly
- SVG icons display properly
- Form controls are styled consistently
- Animations are smooth

---

## 8. Accessibility Basics

- [ ] All interactive elements are keyboard-accessible
- [ ] Form labels are associated with inputs
- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] Focus indicators visible on keyboard navigation
- [ ] Screen reader can navigate sidebar and main content

---

## Quick Validation Workflow

1. **Start servers** — Backend on :8000, Frontend on :5173
2. **Login** — Use test credentials
3. **Dashboard check** — Verify data loads, charts render
4. **Click every sidebar item** — Each page loads without error
5. **Collapse/expand sidebar** — Click button + Ctrl+B
6. **Mobile check** — Resize to 375px, test hamburger menu
7. **Console check** — Open DevTools, verify no errors
8. **API check** — Go to Settings, verify API key status shown correctly
