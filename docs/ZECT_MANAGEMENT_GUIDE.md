# ZECT — Management Guide
## Zinnia Engineering Delivery Control Tower

**Prepared for:** Zinnia Engineering Leadership & Management  
**Version:** 1.0 | April 2026  
**Classification:** Internal Use Only

---

## Executive Summary

ZECT (Zinnia Engineering Delivery Control Tower) is a **web-based AI-powered engineering management platform** that centralizes project tracking, AI-assisted code generation, automated code review, deployment management, and enterprise governance into a single tool. It replaces the need for multiple disconnected tools by providing a unified control tower for engineering delivery.

The platform is organized into **4 sections with 33 navigation items**, each serving a specific function in the software delivery lifecycle.

---

## Table of Contents

1. [Section 1: NAVIGATION (10 items)](#1-navigation)
2. [Section 2: WORKFLOW STAGES (11 items)](#2-workflow-stages)
3. [Section 3: ZINNIA INTELLIGENCE (7 items)](#3-zinnia-intelligence)
4. [Section 4: ENTERPRISE (5 items)](#4-enterprise)
5. [Where ZECT Can Be Used](#where-zect-can-be-used)
6. [Business Value Summary](#business-value-summary)

---

## 1. NAVIGATION

The Navigation section provides the **core management and visibility layer** — dashboards, project tracking, repository intelligence, AI-powered documentation, and code review.

---

### 1.1 Dashboard

**What it is:**  
The central command center that provides a real-time overview of all engineering activity across Zinnia.

**What it shows (based on actual implementation):**
- **4 KPI Cards:** Total Projects, Active Projects, Avg Token Savings %, Risk Alerts count
- **Token Usage Control Panel:** Total API calls, total tokens consumed, estimated cost in USD — broken down by feature (Ask, Plan, Build, etc.) and by AI model (GPT-4o, GPT-4o-mini, etc.), with a recent activity log showing every API call
- **Stage Distribution Chart:** Visual bar chart showing how many projects are in each stage (Ask, Plan, Build, Review, Deploy)
- **Project Cards:** Top 6 projects with name, current stage badge, team, repo count, completion % progress bar

**Workflow:**
1. Open ZECT → Dashboard loads automatically
2. Review KPI cards for a quick health check
3. Click "Details" on Token Usage to see cost breakdown by feature and model
4. Click any project card to drill into that project
5. Click "View all" to go to the full Projects page

**How it is useful to Zinnia:**
- **Management visibility:** One screen shows the health of all engineering projects
- **Cost control:** Real-time LLM token spending visible at a glance — management can see exactly how much AI features cost per feature and per model
- **Risk awareness:** Risk alerts surface projects that need attention immediately

---

### 1.2 Projects

**What it is:**  
A project portfolio management page where all engineering projects are created, tracked, and filtered.

**What it shows:**
- **Project cards** in a grid layout, each showing: name, status badge (active/completed/on-hold), current stage badge (Ask/Plan/Build/Review/Deploy), completion %, token savings %, risk alert count, team name, repo count
- **Filter buttons:** All, Active, Completed, On-Hold
- **"New Project" button** to create a project

**Workflow:**
1. Navigate to Projects from sidebar
2. Filter by status (Active/Completed/On-Hold) to focus on specific projects
3. Click "+ New Project" to create a new project (enter name, description, team, repos)
4. Click any project card to see its full detail page with stages, repos, and history

**How it is useful to Zinnia:**
- **Portfolio view:** See all projects at once with key metrics
- **Status tracking:** Filter to see only active work, completed deliverables, or paused projects
- **Team visibility:** Each card shows which team owns the project

---

### 1.3 Orchestration

**What it is:**  
A multi-repository management view that shows all GitHub repositories linked across all projects, with live GitHub metadata (stars, forks, issues, language).

**What it shows:**
- **3 summary cards:** Total Repos, Total Projects, Connected count
- **Repository cards** for every repo linked to any project, showing: owner/repo name, parent project link, GitHub description, primary language, stars, forks, open issues, connection status
- **Direct links** to open each repo on GitHub

**Workflow:**
1. Navigate to Orchestration
2. See the total repo count and how many are successfully connected
3. Review each repo card for GitHub health (open issues, stars)
4. Click "Open" to jump to the repo on GitHub
5. Click the project name link to navigate to that project's detail page

**How it is useful to Zinnia:**
- **Cross-project visibility:** When multiple projects share repos, Orchestration shows the full picture
- **GitHub health monitoring:** See open issues and activity across all repos from one screen
- **Connection validation:** Instantly see if any repos have lost connection to GitHub

---

### 1.4 Repo Analysis

**What it is:**  
An automated GitHub repository analyzer that fetches and displays a repository's structure, README, dependencies, and architecture notes — without needing to clone the repo locally.

**What it shows:**
- **Two modes:** Single Repo analysis, Multi-Repo analysis (compare multiple repos side by side)
- **Analysis results per repo:** Full name, description, language, stars, forks, open issues
- **Expandable sections:** Architecture Notes, Dependencies (from package.json, requirements.txt, etc.), File Structure tree, README content excerpt
- **Smart input:** Paste a full GitHub URL or type owner/repo — it auto-parses both formats

**Workflow:**
1. Navigate to Repo Analysis
2. Choose Single or Multi-Repo mode
3. Enter owner and repository name (or paste a GitHub URL)
4. Click "Analyze" or "Analyze All"
5. Expand each result to see architecture notes, dependency list, file tree, and README

**How it is useful to Zinnia:**
- **Due diligence:** Quickly analyze any GitHub repo before adopting it as a dependency or evaluating vendor code
- **Architecture understanding:** See a repo's structure and tech stack without cloning it
- **Multi-repo comparison:** Compare multiple repos side by side (e.g., evaluating libraries)
- **Onboarding:** New engineers can understand a repo's architecture from the analysis results

---

### 1.5 Blueprint

**What it is:**  
An AI-powered tool that synthesizes one or more GitHub repositories into a single comprehensive prompt ("blueprint") that can be pasted into any AI coding tool to recreate or understand the entire project.

**What it shows:**
- **Two modes:**
  - **Standard:** Analyze 1+ repos → generate a full blueprint prompt
  - **Focused:** Analyze one repo with a specific focus area (e.g., "authentication", "database schema") and an optional goal
- **Generated blueprint:** A large text prompt containing the repo's architecture, file structure, dependencies, and patterns — ready to copy/paste
- **Token estimate:** Shows how many tokens the prompt will consume
- **AI Enhancement:** One-click "Enhance with AI" that uses OpenAI to improve the blueprint's clarity and add priorities
- **Copy to Clipboard** button for each blueprint

**Workflow:**
1. Navigate to Blueprint
2. Choose Standard or Focused mode
3. Enter repo(s) — supports URL paste
4. Click "Generate Blueprint" or "Generate Focused Blueprint"
5. Review the generated prompt, click "Copy to Clipboard"
6. Optionally click "Enhance with AI" for an improved version
7. Paste the blueprint into any AI coding tool (Cursor, Windsurf, Claude, etc.)

**How it is useful to Zinnia:**
- **Knowledge transfer:** Generate a complete project description that any AI tool can use to understand and work on the codebase
- **Migration planning:** Create a focused blueprint of a specific layer (e.g., "database schema") to plan migrations
- **Vendor evaluation:** Generate blueprints of potential vendor repos to understand their architecture
- **AI-assisted development:** Engineers paste blueprints into AI tools to get context-aware coding help

---

### 1.6 Doc Generator

**What it is:**  
An automated documentation generator that creates structured documentation for any GitHub repository — with selectable sections.

**What it shows:**
- **Section selector:** Toggle which documentation sections to generate: Overview, Architecture, API Reference, Setup Guide, Testing, Deployment
- **Generated sections:** Each section expandable/collapsible, with individual copy buttons
- **Token count** for the generated documentation
- **"Copy All Sections"** button to copy everything at once

**Workflow:**
1. Navigate to Doc Generator
2. Enter owner and repo
3. Select which documentation sections to generate (default: all 6)
4. Click "Generate Documentation"
5. Expand each section to review
6. Copy individual sections or all sections at once

**How it is useful to Zinnia:**
- **Documentation automation:** Instead of manually writing docs, generate them from the actual codebase
- **Standardized format:** Every repo gets documentation in the same structure
- **Selective generation:** Only generate the sections you need (e.g., just API Reference for a microservice)

---

### 1.7 Code Review

**What it is:**  
A full-featured AI-powered code review engine that analyzes Pull Requests, code snippets, or entire repositories for bugs, security vulnerabilities, performance issues, and architectural problems.

**What it shows:**
- **5 review modes:**
  1. **PR Review:** Analyze a GitHub Pull Request by number
  2. **Snippet Review:** Paste any code for instant review
  3. **Full Repo Scan:** Scan an entire repository on a specific branch
  4. **Auto-Fix Loop:** Iteratively review and suggest fixes for a PR (configurable max iterations)
  5. **Webhook Config:** Set up automatic reviews on every PR via GitHub webhooks
- **Quality Score Ring:** Visual 0-100 quality score with color coding
- **Severity breakdown:** Critical, High, Medium, Low, Info — with counts
- **Finding cards:** Each issue shows title, severity badge, file location, line number, description, code snippet, and suggested fix
- **Category filters:** Filter findings by Bugs, Vulnerabilities, Performance, Code Quality, Architecture, Best Practices
- **Inline PR comments:** Automatically post review comments directly to GitHub PRs
- **Fix Prompt Generator:** One-click generation of a structured prompt to fix all issues
- **Rules Engine integration:** Toggle to evaluate custom rules alongside AI review

**Workflow:**
1. Navigate to Code Review
2. Select mode (PR, Snippet, Repo, Auto-Fix, or Webhook)
3. Enter the repository details and PR number (or paste code)
4. Click "Run Review"
5. Review the quality score and severity breakdown
6. Expand each finding to see the problem, code, and suggested fix
7. Click "Post Inline Comments" to push findings directly to the GitHub PR
8. Click "Get Fix Prompt" to generate a structured fix prompt for AI tools
9. Optionally configure webhooks for automatic reviews on every PR

**How it is useful to Zinnia:**
- **Automated quality gate:** Every PR gets a quality score before merge — no manual review needed for basic issues
- **Security scanning:** Catches vulnerabilities (SQL injection, XSS, hardcoded secrets) that manual reviewers miss
- **Consistent standards:** AI applies the same review criteria to every PR, eliminating reviewer bias
- **Developer productivity:** Auto-fix loop suggests and applies fixes iteratively
- **GitHub integration:** Inline comments appear directly in the PR, fitting into existing GitHub workflow
- **Webhook automation:** Set up once and every new PR automatically gets reviewed

---

### 1.8 Analytics

**What it is:**  
A visual analytics dashboard with interactive charts showing project metrics, team performance, and stage distribution.

**What it shows:**
- **6 KPI cards:** Total Projects, Active Projects, Avg Token Savings %, Risk Alerts, Total Repos, Avg Completion %
- **Stage Distribution bar chart:** How many projects are in each stage (Ask, Plan, Build, Review, Deploy)
- **Project Status pie chart:** Active vs Completed vs On-Hold projects
- **Team Performance bar chart:** Average completion % by team
- **Project Breakdown table:** Every project listed with team, stage, completion %, token savings %, and risk alerts — sortable

**Workflow:**
1. Navigate to Analytics
2. Review KPI cards for overall health
3. Check Stage Distribution to see if projects are bottlenecked at any stage
4. Review Team Performance chart to compare team velocity
5. Scroll to the Project Breakdown table for detailed per-project metrics

**How it is useful to Zinnia:**
- **Executive reporting:** Charts can be screenshotted for leadership presentations
- **Bottleneck detection:** If most projects are stuck in "Review" stage, that signals a review capacity problem
- **Team comparison:** Compare completion rates across teams to identify high performers or teams needing support
- **Resource allocation:** Data-driven decisions on where to invest engineering resources

---

### 1.9 Docs Center

**What it is:**  
A centralized documentation hub that aggregates all project documentation, guides, and references in one searchable location.

**How it is useful to Zinnia:**
- **Single source of truth:** Engineers find all docs in one place instead of scattered across wikis, READMEs, and Confluence
- **Knowledge management:** Reduces onboarding time for new team members

---

### 1.10 Settings

**What it is:**  
The platform configuration page for API keys, user profiles, and system settings.

**Key settings:**
- **OpenAI API Key:** Required for AI features (Ask, Plan, Build, Code Review, Blueprint Enhancement)
- **GitHub Token:** Required for repository analysis and PR review features
- **User Profile:** Name, email, role
- **Theme:** Light/dark mode toggle

**How it is useful to Zinnia:**
- **Self-service configuration:** Engineers configure their own API keys without admin intervention
- **Security:** API keys stored locally, never committed to code

---

## 2. WORKFLOW STAGES

The Workflow Stages section maps to the **5-phase software delivery lifecycle** (Ask → Plan → Build → Review → Deploy) plus supporting tools for skills, tokens, running apps, file management, git operations, and CI monitoring.

---

### 2.1 Ask Mode

**What it is:**  
An AI-powered chat interface for asking any engineering question — architecture decisions, debugging help, code review, best practices.

**What it shows:**
- **Chat interface** with user/assistant message bubbles
- **Model selector** dropdown (GPT-4o-mini, GPT-4o, GPT-3.5-turbo, Claude, etc.)
- **File attachment panel:** Attach files, repos, or code snippets as context
  - **Browse Files:** Upload files from your local machine
  - **Manual entry:** Add file paths, repo URLs, or code snippets
- **Suggested prompts:** Pre-built starter questions (microservices migration, auth patterns, API design, CI/CD setup)
- **Code output formatting:** Responses with code blocks are syntax-highlighted
- **Copy response** button on each assistant message
- **Token & model tracking:** Each response shows tokens used and which model was used
- **Prompt Hygiene Tips:** Collapsible panel with best practices for writing effective prompts

**Workflow:**
1. Navigate to Ask Mode
2. (Optional) Select a different AI model from the dropdown
3. (Optional) Attach relevant files or code snippets for context
4. Type a question and press Enter
5. Review the AI response with formatted code blocks
6. Click "Copy full response" to copy any answer
7. Continue the conversation with follow-up questions

**How it is useful to Zinnia:**
- **Instant expert access:** Engineers get immediate answers to architecture and debugging questions
- **Context-aware answers:** Attach project files so the AI understands the specific codebase
- **Knowledge sharing:** Copy responses to share with the team
- **Model flexibility:** Choose between fast/cheap models for simple questions or powerful models for complex analysis

---

### 2.2 Plan Mode

**What it is:**  
An AI-powered engineering plan generator that creates detailed, phased implementation plans from a project or feature description.

**What it shows:**
- **Description input:** Multi-line text area for describing the project/feature
- **File attachment panel:** Same as Ask Mode — attach files, repos, or snippets for context
- **Advanced options:** Repo context (paste README or analysis output), Constraints (budget, timeline, team size)
- **Model selector** dropdown
- **Generated plan:** Formatted as a structured engineering plan with named phases
- **Phase tags:** Visual badges showing each phase (e.g., "Phase 1: Setup", "Phase 2: Core API", etc.)
- **Token count and model used** displayed
- **Copy Plan** button

**Workflow:**
1. Navigate to Plan Mode
2. Describe the project or feature in detail
3. (Optional) Attach context files and set constraints
4. Click "Generate Engineering Plan"
5. Review the phased plan with phase tags
6. Click "Copy Plan" to share or paste into a task tracker

**How it is useful to Zinnia:**
- **Consistent planning:** Every feature gets a structured, phased plan — not ad-hoc
- **Time estimation:** Plans include phases that can be mapped to sprint stories
- **Stakeholder communication:** Generated plans are presentable to management
- **Constraint-aware:** Plans account for budget, timeline, and team size if provided

---

### 2.3 Build Phase

**What it is:**  
An AI code generation tool that produces production-ready code from plan steps, with file attachment support, auto-fix loop, and direct PR creation.

**What it shows:**
- **Plan Step input:** Describe what code to generate (e.g., "REST API endpoint for user auth with JWT")
- **Tech Stack and Target File Path** inputs
- **File attachment panel:** Attach existing files for context
- **Model selector**
- **Generated Code output:** Syntax-highlighted, with file path, language, explanation, and token count
- **File history:** All generated files shown in sidebar with copy/download buttons
- **Auto-Fix Loop:** Run a command, and if it fails, AI analyzes the error and retries (configurable max retries)
- **Create PR panel:** Stage, commit, push, and create a GitHub PR — all from within ZECT

**Workflow:**
1. Navigate to Build Phase
2. Describe the plan step / feature you need code for
3. (Optional) Set tech stack, target file path, and attach context files
4. Click "Generate Code"
5. Review the generated code and explanation
6. Use Auto-Fix Loop to run tests and automatically fix failures
7. Open the Create PR panel to commit and push directly to GitHub

**How it is useful to Zinnia:**
- **Accelerated development:** Generate boilerplate and complex code from descriptions
- **Multi-file context:** Attach existing files so generated code fits the project's patterns
- **Auto-fix:** Reduces the edit-run-debug cycle by automatically fixing errors
- **PR workflow:** No need to leave ZECT — commit, push, and create PRs from the same page

---

### 2.4 Review Phase

**What it is:**  
An AI code quality gate that analyzes pasted code for security, performance, and maintainability — and generates fix prompts.

**What it shows:**
- **Code input:** Multi-line code editor for pasting code
- **Language selector:** TypeScript, JavaScript, Python, Java, Go, Rust, C#
- **Severity filter:** Critical only, High+, Medium+, Low+, All
- **Quality score card:** PASSED or FAILED with a 0-100 score
- **Findings list:** Each finding shows severity badge, message, category, line number, and suggested fix
- **"Generate Fix Prompt" button:** Creates a structured prompt that can be pasted into any AI tool to fix all issues
- **Auto-Fixed Code:** AI-generated fixed version of the code

**Workflow:**
1. Navigate to Review Phase
2. Paste code, select language and minimum severity
3. Click "Run Review"
4. Review the PASS/FAIL verdict and quality score
5. Expand each finding to see the problem and fix suggestion
6. Click "Generate Fix Prompt" to get a structured fix prompt
7. Review the auto-fixed code

**How it is useful to Zinnia:**
- **Quality gate:** Every piece of code gets a quality score before integration
- **Automated fixes:** AI generates the fix prompt and auto-fixed code
- **Multi-language:** Supports all major languages used at Zinnia

---

### 2.5 Deployment

**What it is:**  
An AI-powered deployment planning tool that generates deployment checklists, runbooks, and rollback plans.

**What it shows:**
- **Two modes:**
  - **Checklist:** Interactive pre-deploy / deploy / post-deploy checklist with checkboxes, criticality markers, and automation badges
  - **Runbook:** Full deployment runbook with estimated downtime and risk level
- **Input fields:** Project name, tech stack, environment (staging/production), deployment type (standard/canary/blue-green), infrastructure (AWS/GCP/Azure/on-prem)
- **Rollback plan:** Separate section with step-by-step rollback procedures

**Workflow:**
1. Navigate to Deployment
2. Choose Checklist or Runbook mode
3. Enter project details, environment, and infrastructure
4. Click "Generate"
5. For checklists: Use interactive checkboxes during deployment
6. For runbooks: Review the full procedure, downtime estimate, and risk level

**How it is useful to Zinnia:**
- **Standardized deployments:** Every deployment follows the same checklist structure
- **Risk assessment:** AI estimates downtime and risk level for each deployment
- **Rollback readiness:** Automatically generates rollback procedures
- **Compliance:** Checklists create an auditable record of deployment steps

---

### 2.6 Skill Library

**What it is:**  
A reusable AI skill template library — global or scoped per-repo — with auto-detection of code patterns.

**What it shows:**
- **Skills grid:** Each skill shows name, description, category, scope (Global/Per-Repo), usage count, and tags
- **Category filters:** All, General, Testing, Deployment, Review, Architecture
- **Scope filters:** All, Global, Per-Repo (with repo dropdown)
- **Auto-Detect:** Paste code → AI detects reusable patterns → suggest skills to save
- **Create form:** Name, description, category, template, tags, and scope (global or per-repo)

**Workflow:**
1. Navigate to Skill Library
2. Filter by category or scope
3. Click "Auto-Detect" to paste code and discover patterns
4. Click "Save as Skill" on detected patterns
5. Or click "New Skill" to manually create a skill template
6. Use skills across projects for consistent AI-assisted development

**How it is useful to Zinnia:**
- **Knowledge capture:** Reusable patterns are saved as skills instead of being lost
- **Per-repo customization:** Skills can be scoped to specific repos
- **Pattern discovery:** Auto-detect finds patterns engineers may not recognize as reusable

---

### 2.7 Token Controls

**What it is:**  
A comprehensive LLM token usage monitoring, budgeting, and analytics platform with per-user tracking, team breakdowns, and trend analysis.

**What it shows:**
- **5 tabs:** Overview, User Activity, Teams, Budget, Trends
- **Overview:** Total calls, total tokens, total cost, today's tokens — plus budget progress bars, model breakdown (% usage per model with cost), active users quick view, and recent usage log table
- **User Activity:** Per-user token usage, cost, last active time — click a user to see their detailed breakdown by feature
- **Teams:** Team-level usage aggregation
- **Budget:** Set daily token limits, monthly token limits, monthly cost limits (USD), alert threshold %, preferred model, enforce limits toggle, and allowed models list
- **Trends:** 30-day usage trends

**Workflow:**
1. Navigate to Token Controls
2. Review the Overview tab for spending summary
3. Check Model Breakdown to see which models consume the most
4. Go to Budget tab to set daily/monthly limits and cost caps
5. Review User Activity to see individual spending
6. Check Trends for usage patterns over time

**How it is useful to Zinnia:**
- **Cost governance:** Set hard limits on AI token spending per day/month
- **Per-user accountability:** See exactly who is spending how much on which features
- **Model optimization:** Data shows if engineers use expensive models when cheaper ones would work
- **Budget alerts:** Automatic alerts when spending approaches the threshold
- **SSO-ready:** Designed for enterprise SSO integration for user identification

---

### 2.8 App Runner

**What it is:**  
A built-in terminal and process manager that lets users configure, run, and test applications directly inside ZECT — with live preview.

**What it shows:**
- **3 tabs:** Terminal, Configure, Processes
- **Terminal:** Full command-line interface with syntax-highlighted output, command history (arrow keys), working directory setting, one-shot "Run" and background "Start Process" buttons
- **Configure:** Point to a repo path, set install and startup commands, preview port, environment variables — and launch with one click
- **Processes:** List of all running and stopped processes with PID, uptime, exit code, live output view
- **Live Preview:** When a dev server runs, shows the app in an iframe panel

**Workflow:**
1. Navigate to App Runner
2. Use the Terminal tab to run commands (like `npm test`, `git status`)
3. Use "Start Process" to start long-running servers (like `npm run dev`)
4. Switch to Configure tab to set up a project's install/start/preview configuration
5. View running processes in the Processes tab, stop or remove as needed

**How it is useful to Zinnia:**
- **No context switching:** Developers run and test apps without leaving ZECT
- **Process management:** Monitor all running processes from one place
- **One-click setup:** Configure once, launch with one click
- **Live preview:** See the running app directly in ZECT

---

### 2.9 File Explorer

**What it is:**  
A web-based file browser for navigating and viewing project files on the server.

**How it is useful to Zinnia:**
- **Remote file access:** Browse project files without SSH
- **Quick code reading:** View file contents without cloning repos locally

---

### 2.10 Git Operations

**What it is:**  
A web UI for common Git operations — viewing status, staging, committing, pushing, and branch management.

**How it is useful to Zinnia:**
- **Git without CLI:** Developers who prefer a GUI can manage Git operations from ZECT
- **Integrated workflow:** Git operations stay within the ZECT workflow instead of switching to a terminal

---

### 2.11 CI Monitor

**What it is:**  
A CI/CD pipeline monitoring view that shows build status, test results, and deployment state across projects.

**How it is useful to Zinnia:**
- **Pipeline visibility:** See all CI/CD pipelines from one screen
- **Build status tracking:** Monitor which builds are passing or failing
- **Integrated view:** CI results shown alongside the project they belong to

---

## 3. ZINNIA INTELLIGENCE

The Zinnia Intelligence section is ZECT's **proprietary AI memory and learning system** — a unique capability that makes ZECT remember, learn, and improve over time. This is the key differentiator from generic AI tools.

---

### 3.1 Memory System

**What it is:**  
A 4-layer memory architecture (working, episodic, semantic, personal) that gives ZECT persistent memory across sessions and projects.

**What it shows:**
- **5 tabs:** Brain State, Episodes, Lessons, Decisions, Search
- **Brain State overview:** Active tasks, active episodes, accepted lessons, pending review count, total episodes, rejected lessons, active decisions — with recent episodes and a pending review queue
- **Episodes tab:** Raw experience log showing every action ZECT has taken — with action name, outcome, harness, success/failure indicator, importance/salience/pain scores, and token usage
- **Lessons tab:** Learned patterns with claim text, conditions, status (staged/accepted/rejected/provisional), confidence %, evidence count — plus a "Teach a Lesson" form for one-shot learning
- **Decisions tab:** Active architectural and process decisions being tracked
- **Search tab:** Full-text search across all memory layers

**Key actions:**
- **Graduate a lesson:** Accept a staged lesson → it becomes permanent knowledge
- **Reject a lesson:** Mark a staged lesson as incorrect → it will not be used
- **Teach a lesson:** Manually teach ZECT something (e.g., "Always run tests before pushing")

**Workflow:**
1. Navigate to Memory System
2. Review Brain State for a health check of ZECT's knowledge
3. Check the Pending Review queue — graduate or reject staged lessons
4. Use the Lessons tab to teach ZECT new rules manually
5. Search across all memory layers for specific knowledge

**How it is useful to Zinnia:**
- **Organizational learning:** ZECT accumulates knowledge from every project and engineer interaction
- **Quality improvement:** As ZECT learns from past mistakes (episodes), future recommendations improve
- **Institutional memory:** Knowledge persists across team changes and project transitions
- **Human oversight:** Staged lessons require human approval before becoming permanent knowledge

---

### 3.2 Dream Engine

**What it is:**  
An automated pattern extraction system that runs "dream cycles" — analyzing episodic memories, clustering similar events, extracting patterns, staging them as candidate lessons, prefiltering noise, decaying old memories, and archiving stale workspaces.

**What it shows:**
- **Dream Cycle controls:** Configurable max age (days) and minimum occurrences threshold
- **Last Run result card:** Episodes processed, clusters found, candidates staged, candidates prefiltered, episodes decayed, workspaces archived
- **Run History table:** All previous dream cycles with status, timestamps, and metrics

**Workflow:**
1. Navigate to Dream Engine
2. Set max age (default: 14 days) and min occurrences (default: 3)
3. Click "Run Dream Cycle"
4. Review results: how many patterns were found and staged as candidate lessons
5. Go to Memory System → Lessons to review and approve/reject the candidates
6. Optionally use "Manual Decay" to clean up very old episodes

**How it is useful to Zinnia:**
- **Automated pattern discovery:** ZECT finds patterns humans might miss
- **Self-improvement:** The Dream Engine is how ZECT learns from experience without being explicitly taught
- **Memory hygiene:** Old, irrelevant episodes are automatically decayed to keep the knowledge base fresh
- **Scalable learning:** Works across all projects simultaneously

---

### 3.3 Data Layer

**What it is:**  
A cross-agent event monitoring and analytics platform with KPIs, interactive charts, and exportable data.

**What it shows:**
- **3 tabs:** Analytics Dashboard, Event Log, Daily Reports
- **Analytics Dashboard:** 6 KPI cards (Total Events, Total Tokens, Total Cost, Success Rate, Avg Duration, Throughput/Day) + 4 interactive charts (Daily Event Trend line chart, By Harness pie chart, By Category bar chart, By Model bar chart)
- **Event Log:** Detailed table with harness, event type, category, description, tokens, cost, success/fail, timestamp — with pagination (15 per page)
- **Daily Reports:** Auto-generated daily summaries with event count, total tokens, cost, success rate, and a viewable markdown report
- **Time filter:** 1 day, 7 days, 14 days, 30 days
- **Export CSV:** One-click CSV export of all event data

**Workflow:**
1. Navigate to Data Layer
2. Set the time period (1/7/14/30 days)
3. Review KPI cards for high-level metrics
4. Check charts for patterns (which harness/category/model is most active)
5. Switch to Event Log to see individual events
6. Switch to Daily Reports for auto-generated summaries
7. Click "Export CSV" to download data for external analysis

**How it is useful to Zinnia:**
- **Operational visibility:** Every AI action across all agents is tracked and visualized
- **Cost analysis:** Know exactly what AI features cost, broken down by category and model
- **Success rate monitoring:** Track if AI operations are succeeding or failing
- **Compliance reporting:** Daily reports and CSV exports support audit requirements

---

### 3.4 Data Flywheel

**What it is:**  
A continuous improvement system where approved runs become training traces, which become context cards, which become evaluation test cases — creating a virtuous cycle of improvement.

**How it is useful to Zinnia:**
- **Continuous improvement:** Each successful interaction makes the system better
- **Test case generation:** Real usage generates test cases automatically
- **Quality feedback loop:** Failed operations are analyzed and feed back into improvements

---

### 3.5 Permissions

**What it is:**  
A 3-tier action enforcement system that controls what ZECT can do automatically vs. what requires human approval vs. what is never allowed.

**What it shows:**
- **Permission rules** with action name, tier (allow/require-approval/never-allowed), and scope
- **Add Rule** form to create new permission rules
- **Pagination** for large rule sets (10 per page)

**How it is useful to Zinnia:**
- **Safety guardrails:** Prevent ZECT from taking dangerous actions without approval
- **Compliance:** Some actions (e.g., production deployment) can be set to always require human approval
- **Customizable:** Each team can set their own permission rules

---

### 3.6 Transfer & Onboard

**What it is:**  
A brain state export/import system with a 6-question onboarding wizard for new project setup.

**How it is useful to Zinnia:**
- **Knowledge portability:** Export ZECT's learned knowledge from one project and import it into another
- **Rapid onboarding:** New projects get the benefit of lessons learned from previous projects
- **Team transitions:** When engineers move between teams, ZECT's knowledge follows

---

### 3.7 Skills Engine

**What it is:**  
A database-backed skill registry with trigger-based matching and execution logging — the operational layer that matches incoming tasks to the right skills.

**What it shows:**
- **Skills list** with name, trigger pattern, status, execution count — with pagination (10 per page)
- **Execution log** showing when skills were triggered and what happened

**How it is useful to Zinnia:**
- **Automated task routing:** Incoming requests are matched to the right skill automatically
- **Execution tracking:** See which skills are used most and how they perform
- **Database-backed:** All skill data persists across sessions (migrated from in-memory to database)

---

## 4. ENTERPRISE

The Enterprise section provides **governance, compliance, and collaboration features** required for enterprise-grade operation.

---

### 4.1 Audit Trail

**What it is:**  
A complete, immutable log of every system operation — creates, updates, deletes, logins, exports, and reviews — with IP address tracking.

**What it shows:**
- **4 stats cards:** Total Entries, Last 24h activity, Action Types count, Resource Types count
- **Filter dropdowns:** Filter by action (create/update/delete/login/export/review) and by resource type (project/repo/skill/setting/review/rule)
- **Entries table:** Timestamp, Action badge (color-coded), Resource type and name, Details, IP address
- **Built-in guide** explaining how to use the audit trail

**Workflow:**
1. Navigate to Audit Trail
2. Review stats cards for activity volume
3. Filter by action type (e.g., "delete") or resource type (e.g., "project")
4. Review individual entries for timestamp, action, resource, and IP
5. Use Export/Share to download logs for compliance reports

**How it is useful to Zinnia:**
- **Compliance:** SOC 2, SOX, and insurance regulatory requirements need an audit trail
- **Security investigation:** Track who did what, when, and from which IP address
- **Change history:** See every modification to projects, settings, rules, etc.
- **Automatic logging:** No manual effort — every action is captured automatically

---

### 4.2 Rules Engine

**What it is:**  
A customizable rules engine for enforcing code review standards, quality gates, deployment policies, naming conventions, and security patterns.

**What it shows:**
- **Rules list:** Each rule shows name, severity badge (critical/high/medium/low/info), type badge (review/quality gate/deploy/naming/security), active/disabled status, description, and regex condition
- **Create Rule form:** Name, type, severity, action (warn/block/auto-fix/notify), description, regex condition
- **Test Rules section:** Paste code to test which rules match before deploying them
- **Built-in guide** with regex examples

**Workflow:**
1. Navigate to Rules Engine
2. Click "New Rule" to create a rule
3. Set the rule type (review/quality gate/deploy/naming/security)
4. Enter a regex pattern (e.g., `console\.log|debugger` to catch debug statements)
5. Set the action: Warn, Block (prevent merge/deploy), Auto Fix, or Notify
6. Test the rule by pasting code in the "Test Rules" section
7. Deploy the rule — it will be enforced during code reviews

**How it is useful to Zinnia:**
- **Custom standards:** Define Zinnia-specific rules that AI enforces consistently
- **Quality gates:** Block PRs that contain critical patterns (e.g., `TODO` in production code)
- **Security enforcement:** Catch hardcoded secrets, unsafe patterns, and vulnerability indicators
- **Test before deploy:** Validate rules against sample code before making them active

---

### 4.3 Integrations

**What it is:**  
A configuration hub for connecting ZECT with external services — currently supporting Jira and Slack.

**What it shows:**
- **Jira card:** Connection status, base URL, email, linked tickets count — with configuration form for URL, email, API token, and project key
- **Slack card:** Connection status, workspace name, default channel, notification toggles (review alerts, deploy alerts, budget alerts) — with configuration form for bot token, workspace, channel
- **Test message:** Send a test message to Slack to verify the connection
- **Built-in guide** with setup instructions for each integration

**Workflow:**
1. Navigate to Integrations
2. Click "Configure" on the Jira card → enter Atlassian URL, email, API token, project key → Save
3. Click "Configure" on the Slack card → enter bot token, workspace, channel → Save
4. Send a test message to verify Slack connection

**How it is useful to Zinnia:**
- **Jira sync:** Create Jira tickets directly from code review findings — no manual copy/paste
- **Slack notifications:** Get real-time alerts in Slack when reviews complete, deployments happen, or budget thresholds are reached
- **Existing workflow:** Integrates with tools Zinnia already uses (Jira, Slack)

---

### 4.4 Export/Share

**What it is:**  
A data export tool for downloading project data, review results, audit logs, and analytics in various formats for sharing or compliance.

**How it is useful to Zinnia:**
- **Compliance reports:** Export audit trails and analytics for regulatory submissions
- **Executive reporting:** Download charts and data for leadership presentations
- **Data portability:** Export project data to other systems

---

### 4.5 Output History

**What it is:**  
A historical record of all AI-generated outputs — plans, blueprints, code, reviews, documentation — organized chronologically.

**How it is useful to Zinnia:**
- **Traceability:** See exactly what AI generated, when, and for which project
- **Reuse:** Find and reuse previous AI outputs instead of regenerating
- **Quality review:** Management can review what AI has been generating

---

## Where ZECT Can Be Used

| Use Case | ZECT Features Used |
|---|---|
| **Sprint planning** | Plan Mode, Analytics |
| **Code development** | Build Phase, Ask Mode, Skill Library |
| **Pull request review** | Code Review, Rules Engine |
| **Pre-deployment checks** | Deployment, Review Phase |
| **New project setup** | Blueprint, Doc Generator, Repo Analysis |
| **Onboarding new engineers** | Repo Analysis, Memory System, Docs Center |
| **Cost management** | Token Controls, Data Layer |
| **Compliance auditing** | Audit Trail, Export/Share, Permissions |
| **Knowledge management** | Memory System, Dream Engine, Skills Engine |
| **Vendor code evaluation** | Repo Analysis, Blueprint, Code Review |
| **Team performance tracking** | Analytics, Dashboard, Data Layer |
| **CI/CD monitoring** | CI Monitor, Deployment |
| **Integration with existing tools** | Integrations (Jira, Slack), Git Operations |

---

## Business Value Summary

| Metric | Impact |
|---|---|
| **Code review coverage** | 100% automated — every PR gets reviewed by AI |
| **Security scanning** | Automated detection of vulnerabilities, secrets, and unsafe patterns |
| **Documentation generation** | Auto-generated docs reduce documentation backlog |
| **Cost transparency** | Per-user, per-feature, per-model token spending tracked in real-time |
| **Deployment safety** | Generated checklists and rollback plans for every deployment |
| **Institutional knowledge** | Memory System captures and retains organizational knowledge |
| **Developer productivity** | AI-assisted code generation, planning, and debugging |
| **Compliance readiness** | Full audit trail, permission controls, and data export |
| **Continuous improvement** | Dream Engine and Data Flywheel create a self-improving system |

---

*Document generated from analysis of the actual ZECT codebase — all descriptions are based on the implemented functionality as of April 2026.*
