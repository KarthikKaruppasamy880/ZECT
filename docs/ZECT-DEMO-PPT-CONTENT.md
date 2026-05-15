# ZECT Demo Presentation — Slide-by-Slide Content

**Purpose:** Speaker notes and slide content for a live ZECT demo to management/stakeholders.
**Audience:** Engineering leadership, Product managers, Zinnia management
**Duration:** 30-45 minutes (with live demo)
**Screenshots:** All referenced screenshots are in `docs/screenshots/`

---

## Slide 1: Title Slide

**Title:** ZECT — Zinnia Engineering Control Tower
**Subtitle:** AI-Powered Engineering Delivery Platform v2.0
**Tagline:** "One platform for the entire software delivery lifecycle"
**Visual:** ZECT logo + sidebar screenshot (`screenshots/01-dashboard.png`)

**Speaker Notes:**
> ZECT is an internally developed platform that consolidates our engineering workflows — from asking questions about code to deploying to production — into a single, self-hosted web application. Today I'll walk you through every feature, show you how it works live, and explain why this is critical for Zinnia.

---

## Slide 2: The Problem We Solve

**Title:** Why ZECT?

| Problem | Before ZECT | With ZECT |
|---------|-------------|-----------|
| Tool fragmentation | 5-8 tools per feature delivery | 1 unified platform |
| No AI governance | Unknown AI spend, no controls | Per-user budgets, full audit trail |
| No cross-project view | Each team in silos | Dashboard with all projects |
| Security risk | Code sent to external SaaS | Self-hosted, zero data leakage |
| No compliance | Manual audit reports | Automated audit trail |
| Inconsistent workflows | Every team different | Standardized 5-stage process |

**Speaker Notes:**
> Before ZECT, our teams used separate tools for code review, planning, building, and deployment — with no visibility across projects and no control over AI spending. ZECT eliminates all of these gaps.

---

## Slide 3: Platform Overview

**Title:** 33 Screens, 5 Functional Areas, 67+ API Endpoints

**Layout:** Show the 5 sidebar groups:
1. **Navigation** (10 items) — Dashboard, Projects, Orchestration, Repo Analysis, Blueprint, Doc Generator, Code Review, Analytics, Docs Center, Settings
2. **Workflow Stages** (12 items) — Ask, Plan, Build, Review, Deploy, Skills, Token Controls, App Runner, File Explorer, Git Ops, CI Monitor, Repo Workspace
3. **Zinnia Intelligence** (7 items) — Memory, Dream Engine, Data Layer, Data Flywheel, Permissions, Transfer, Skills Engine
4. **Features** (7 items) — Knowledge Base, Playbooks, Scheduled Tasks, Secrets, Code Index, Session Insights, Conversations
5. **Enterprise** (5 items) — Audit Trail, Rules Engine, Integrations, Export/Share, Output History

**Visual:** Full sidebar screenshot (`screenshots/01-dashboard.png`)

**Speaker Notes:**
> ZECT has 33 sidebar items organized into 5 sections. This is not a prototype — every screen is fully functional with real backend endpoints. Let me walk you through each section.

---

## Slide 4: Dashboard

**Title:** Real-Time Engineering Dashboard
**Screenshot:** `screenshots/01-dashboard.png`

**Key Points:**
- Active projects count with status indicators
- Stage distribution (how many projects in Ask, Plan, Build, Review, Deploy)
- Risk alerts
- Quick-access cards to all major features

**Speaker Notes:**
> The dashboard gives engineering managers instant visibility. You see how many projects are active, what stage each is in, and any risk alerts. No need to check 5 different tools.

---

## Slide 5: Projects & Orchestration

**Title:** Multi-Project Management
**Screenshots:** `screenshots/02-projects.png`, `screenshots/03-orchestration.png`

**Key Points:**
- Create/edit projects with metadata, stage tracking, and repo associations
- Orchestration view with Kanban-style boards
- Cross-project dependency tracking
- Resource allocation and timeline management

**Speaker Notes:**
> Unlike AI coding tools that work on one session at a time, ZECT manages multiple projects simultaneously. The orchestration view shows cross-project dependencies — critical when our teams work on related services.

---

## Slide 6: Repo Analysis & Blueprint Generator

**Title:** Analyze Any Repository in Seconds
**Screenshots:** `screenshots/04-repo-analysis.png`, `screenshots/05-blueprint.png`

**Key Points:**
- **Repo Analysis**: Fetch structure, README, dependencies, and architecture from any GitHub repo
- **Blueprint Generator**: Synthesize an entire repo into a single AI prompt for vibe-coding
- Supports single-repo and multi-repo analysis
- Standard and Focused blueprint modes

**Speaker Notes:**
> Repo Analysis is incredibly useful for onboarding to new codebases. Point it at any GitHub repo and get a complete analysis in seconds. The Blueprint Generator takes this further — it creates a single prompt that captures the entire project, so any AI tool can recreate it from scratch.

---

## Slide 7: AI Workflow — Ask → Plan → Build

**Title:** The AI Development Pipeline
**Screenshots:** `screenshots/11-ask-mode.png`, `screenshots/12-plan-mode.png`, `screenshots/13-build-phase.png`

**Key Points:**
- **Ask Mode**: Natural language questions with file attachments and model selection
- **Plan Mode**: Generate implementation plans from requirements
- **Build Phase**: AI code generation with model selection, file context, and write-to-repo capability
- Active project context auto-injects repo information into every AI call

**Speaker Notes:**
> This is the core workflow. Ask Mode is for exploration — "How does this auth system work?" Plan Mode generates step-by-step implementation plans. Build Phase generates actual code. What's special is that the active project context (top bar selector) automatically injects the current repo context into every AI call. And Build Phase can write code directly to your cloned repo — no copy-paste needed.

---

## Slide 8: Code Review Engine

**Title:** AI-Powered Code Review (5 Modes)
**Screenshot:** `screenshots/07-code-review.png`

**Key Points:**
- **PR Review**: Analyze actual GitHub PRs with inline comments
- **Snippet Review**: Paste any code for instant analysis
- **Full Repo Scan**: Scan entire repositories for issues
- **Auto-Fix Loop**: Detect issues → fix → verify cycle
- **Webhook**: Auto-trigger reviews on PR creation with Rules Engine kill switch

**Speaker Notes:**
> The Code Review Engine has 5 modes. PR Review connects directly to GitHub. The Auto-Fix Loop is powerful — it finds issues, generates fixes, and re-checks. The webhook mode auto-triggers reviews on every PR, with a kill switch in the Rules Engine if you need to pause it.

---

## Slide 9: Review & Deploy

**Title:** Complete the Cycle
**Screenshots:** `screenshots/14-review-phase.png`, `screenshots/15-deployment.png`

**Key Points:**
- **Review Phase**: Structured code review with AI analysis
- **Deployment**: Checklist generation, environment selection, deployment tracking

**Speaker Notes:**
> Review Phase provides structured analysis. Deployment generates checklists and tracks which environments have been deployed to. This completes the Ask → Plan → Build → Review → Deploy cycle.

---

## Slide 10: App Runner & File Explorer

**Title:** Built-In Development Environment
**Screenshots:** `screenshots/18-app-runner.png`, `screenshots/19-file-explorer.png`

**Key Points:**
- **App Runner**: Embedded terminal, background process management, live preview (iframe), configuration
- **File Explorer**: Full file tree browsing, file creation, search
- No need to leave ZECT to run commands or browse files

**Speaker Notes:**
> App Runner is like having a terminal built into ZECT. You can run servers, view live previews, manage background processes. File Explorer gives you full filesystem access. Together, they mean developers can stay in ZECT for their entire workflow.

---

## Slide 11: Git Operations & CI Monitor

**Title:** Git & CI Without Leaving ZECT
**Screenshots:** `screenshots/20-git-operations.png`, `screenshots/21-ci-monitor.png`

**Key Points:**
- **Git Ops**: Status, commit, branch, log, create PR — all from ZECT
- **CI Monitor**: View GitHub Actions workflows, job details, status tracking
- Repo Workspace ties everything together (clone, browse, search)

**Speaker Notes:**
> Git Operations provides everything you need — status, commit, branch management, PR creation. CI Monitor shows your GitHub Actions pipelines in real-time. Combined with Repo Workspace, you have a complete development environment.

---

## Slide 12: Repo Workspace (Deep Integration)

**Title:** Full Repository Management
**Screenshot:** `screenshots/22-repo-workspace.png`

**Key Points:**
- 3 tabs: Clone & Manage, File Browser, Code Search
- Clone any GitHub repo locally
- Browse full file trees with syntax highlighting (30+ languages)
- Regex search across entire codebases
- Auto-indexing on clone (8 languages)
- Write-back from Build Phase

**Speaker Notes:**
> Repo Workspace is our deep repository integration. Clone any GitHub repo, browse every file with full syntax highlighting, search with regex, and our auto-indexer catalogs all functions and classes. When Build Phase generates code, it writes directly to these cloned repos. This is how we close the loop from AI generation to actual code.

---

## Slide 13: Token Controls

**Title:** AI Cost Governance
**Screenshot:** `screenshots/17-token-controls.png`

**Key Points:**
- 5 tabs: Overview, User Activity, Teams, Budget, Trends
- Per-user token tracking with cost breakdown
- Team-level budgets and alerts
- Threshold controls (warning at 80%, block at 100%)
- Trend analysis for cost optimization

**Speaker Notes:**
> This is critical for enterprise. Every AI call is tracked — which user, which model, how many tokens, what it cost. You can set per-user and per-team budgets with alerts. This prevents surprise bills and gives full visibility into AI spend.

---

## Slide 14: Zinnia Intelligence

**Title:** Proprietary Intelligence Layer
**Screenshots:** `screenshots/23-memory-system.png`, `screenshots/24-dream-engine.png`, `screenshots/26-data-flywheel.png`

**Key Points:**
- **Memory System**: Project memory, skill memory, episodic and semantic recall
- **Dream Engine**: Background pattern discovery and optimization
- **Data Layer**: Structured project insight management
- **Data Flywheel**: Continuous improvement loop (usage → learning → better suggestions)
- **Permissions**: Role-based feature access
- **Transfer & Onboard**: Knowledge transfer workflows
- **Skills Engine**: Reusable skill management

**Speaker Notes:**
> Zinnia Intelligence is our proprietary layer. The Memory System remembers what worked across projects. The Dream Engine processes patterns in the background. The Data Flywheel ensures the system gets better with use. This is unique to ZECT — no competing tool has this.

---

## Slide 15: Enterprise Controls

**Title:** Compliance & Governance
**Screenshots:** `screenshots/37-audit-trail.png`, `screenshots/38-rules-engine.png`, `screenshots/39-integrations.png`

**Key Points:**
- **Audit Trail**: Complete logging of all operations
- **Rules Engine**: Custom code quality rules, deployment gates, kill switches
- **Integrations**: Jira, Slack, GitHub — configurable connectors
- **Export/Share**: Export project data, reports, generated outputs
- **Output History**: Browse all AI-generated artifacts with token/cost tracking

**Speaker Notes:**
> For insurance, compliance is non-negotiable. Audit Trail logs every AI operation. Rules Engine lets you set gates — "no deployment without code review" or "pause auto-reviews." Integrations connect to Jira and Slack. Output History is your searchable archive of every AI output.

---

## Slide 16: Features Hub

**Title:** Knowledge, Playbooks & Automation
**Screenshots:** `screenshots/30-knowledge-base.png`, `screenshots/31-playbooks.png`, `screenshots/32-scheduled-tasks.png`

**Key Points:**
- **Knowledge Base**: Store and retrieve organizational knowledge
- **Playbooks**: Reusable workflow templates
- **Scheduled Tasks**: Automated recurring operations
- **Secrets Manager**: Secure credential storage
- **Code Index**: Auto-indexed repository catalog
- **Session Insights**: Analytics on development sessions
- **Conversations**: Chat history and context management

**Speaker Notes:**
> The Features section provides the supporting infrastructure. Knowledge Base stores what your team learns. Playbooks are reusable templates for common workflows. Scheduled Tasks automate recurring operations. Secrets Manager securely stores API keys and credentials.

---

## Slide 17: Documentation & Analysis Tools

**Title:** Built-In Documentation Suite
**Screenshots:** `screenshots/06-doc-generator.png`, `screenshots/09-docs-center.png`

**Key Points:**
- **Doc Generator**: Auto-generate documentation for any repo (overview, architecture, API reference, setup, testing, deployment)
- **Docs Center**: Central hub for all project documentation
- **Skill Library**: Browse and manage reusable development skills

**Speaker Notes:**
> Doc Generator is invaluable for legacy projects. Point it at any repo and it generates comprehensive documentation — architecture, API reference, setup guides. Docs Center provides a central hub for all project documentation.

---

## Slide 18: Deployment Architecture

**Title:** Self-Hosted, Secure, Scalable

**Key Points:**
- Docker Compose for simple deployments (EC2)
- AWS ECS Fargate for auto-scaling
- PostgreSQL (RDS) for production database
- All data stays on Zinnia infrastructure
- CI/CD via GitHub Actions

```
Route 53 → ALB → Frontend (S3/CloudFront) + Backend (ECS/EC2) → RDS PostgreSQL
```

**Speaker Notes:**
> ZECT is self-hosted. We deploy via Docker Compose on EC2 or AWS ECS for auto-scaling. The database is PostgreSQL on RDS. All code, all data, all AI interactions stay on our infrastructure. Zero data leaves Zinnia's network.

---

## Slide 19: Competitive Advantage

**Title:** ZECT vs. Industry AI Coding Tools

| Capability | ZECT | Typical AI Tools |
|-----------|------|-----------------|
| Self-hosted | Yes | No (SaaS only) |
| Multi-project | Yes (6+) | No (1 session) |
| Token budgets | Per-user/team | Org-level only |
| Audit trail | Full | Session logs |
| Model choice | Per-feature | Fixed |
| Repository integration | Clone + browse + index + write | Separate sandbox |
| Cost transparency | Per-call tracking | Monthly invoice |

**Speaker Notes:**
> This slide is key. ZECT's enterprise features — self-hosting, audit trail, per-user token budgets, multi-project management — are things no AI coding tool offers. The industry tools are better at autonomous execution today, but our enterprise controls are unique.

---

## Slide 20: Roadmap & Next Steps

**Title:** What's Next

| Phase | Timeline | Features |
|-------|----------|----------|
| v2.0 (Current) | Done | 33 screens, 67+ endpoints, deep repo integration |
| v3.0 | 6-8 weeks | Agent Mode (autonomous execution), Auto-Fix Loop, Session Persistence |
| v3.5 | 12 weeks | CI/CD auto-remediation, Enhanced Knowledge Base, Desktop App |

**Speaker Notes:**
> We're at v2.0 with a solid foundation. The next big milestone is Agent Mode — where ZECT can autonomously chain Ask → Plan → Build → Review without human intervention. This puts us on par with the best autonomous AI coding tools, while keeping our enterprise advantages.

---

## Slide 21: Live Demo Flow

**Title:** Live Demo (15-20 minutes)

**Recommended demo sequence:**
1. Login → Dashboard overview (2 min)
2. Create/select a project → Show projects list (2 min)
3. Ask Mode → Ask a question with repo context (2 min)
4. Plan Mode → Generate implementation plan (2 min)
5. Build Phase → Generate code → Show write-to-repo (3 min)
6. Repo Workspace → Show cloned repo, file browser, search (3 min)
7. Code Review → Review a PR or snippet (2 min)
8. Token Controls → Show usage tracking (1 min)
9. Analytics → Show charts and metrics (1 min)
10. Audit Trail → Show compliance logging (1 min)

---

## Slide 22: Q&A

**Title:** Questions?

**Contact:** Engineering Team
**Repo:** `KarthikKaruppasamy880/ZECT`
**Docs:** See `docs/` folder in the repository

---

*Document Location: `docs/ZECT-DEMO-PPT-CONTENT.md`*
*Screenshots Location: `docs/screenshots/` (42 screenshots, all screens captured)*
