# ZECT White Paper

## Zinnia Engineering Control Tower — Enterprise AI-Powered Engineering Platform

**Version:** 2.0 | **Date:** May 2026 | **Classification:** Internal — Zinnia Technology

---

## Executive Summary

ZECT (Zinnia Engineering Control Tower) is an internally developed, self-hosted, AI-powered engineering delivery platform purpose-built for Zinnia's software development lifecycle. Unlike SaaS-only AI coding assistants, ZECT provides a **complete engineering control plane** — covering project management, AI-assisted code workflows, repository integration, security controls, and enterprise compliance — all running on Zinnia's own infrastructure with zero data leaving the network.

ZECT consolidates 33+ screens across 5 functional areas into a single web application, enabling engineering teams to manage the full lifecycle from requirements analysis through deployment, with AI assistance at every step.

---

## 1. Problem Statement

Zinnia's engineering teams face several challenges:

| Challenge | Impact |
|-----------|--------|
| Fragmented tooling | Developers switch between 5-8 tools for a single feature delivery |
| No AI governance | No visibility into AI token usage, costs, or model selection |
| No unified project view | Engineering managers lack cross-project visibility |
| Security concerns | SaaS AI tools send proprietary code to external servers |
| Compliance gaps | Insurance industry requires audit trails for all code changes |
| Inconsistent workflows | Each team follows different processes for ask → plan → build → review → deploy |

---

## 2. Solution Overview

ZECT addresses all these challenges through a unified platform:

```
┌─────────────────────────────────────────────────────────┐
│                    ZECT Platform                         │
├─────────────┬─────────────┬─────────────┬──────────────┤
│ Navigation  │  Workflow   │  Zinnia     │  Enterprise  │
│ (Core)      │  Stages     │  Intelligence│  Controls   │
├─────────────┼─────────────┼─────────────┼──────────────┤
│ Dashboard   │ Ask Mode    │ Memory      │ Audit Trail  │
│ Projects    │ Plan Mode   │ Dream Engine│ Rules Engine │
│ Orchestrate │ Build Phase │ Data Layer  │ Integrations │
│ Repo Analyze│ Review Phase│ Data Flywheel│ Export/Share│
│ Blueprint   │ Deployment  │ Permissions │ Output Hist. │
│ Doc Gen     │ Skill Library│ Transfer   │              │
│ Code Review │ Token Ctrl  │ Skills Eng. │              │
│ Analytics   │ App Runner  │             │              │
│ Docs Center │ File Explorer│            │              │
│ Settings    │ Git Ops     │             │              │
│             │ CI Monitor  │             │              │
│             │ Repo Work.  │             │              │
├─────────────┴─────────────┴─────────────┴──────────────┤
│            + Features: Knowledge Base, Playbooks,       │
│            Scheduled Tasks, Secrets, Code Index,        │
│            Session Insights, Conversations              │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui |
| Backend | Python 3.10+ / FastAPI |
| Database | PostgreSQL (production) / SQLite (development) |
| AI Models | Configurable — OpenAI, Anthropic, local LLMs (Ollama) |
| Deployment | Docker Compose / AWS EC2 / AWS ECS |

---

## 3. Key Capabilities

### 3.1 AI-Assisted Software Delivery Lifecycle

ZECT implements a structured 5-stage workflow:

1. **Ask Mode** — Natural language questions about code, architecture, best practices. Supports file attachments for context.
2. **Plan Mode** — Generate implementation plans from requirements. AI produces step-by-step technical plans.
3. **Build Phase** — AI-powered code generation with model selection, file attachments, and write-to-repo capability.
4. **Review Phase** — Automated code review for bugs, vulnerabilities, performance, and architecture issues.
5. **Deployment** — Deployment checklist generation and tracking.

### 3.2 Deep Repository Integration

ZECT provides full local repository management:

- **Clone & Manage** — Clone GitHub repositories locally, switch branches, pull updates
- **File Browsing** — Navigate full file trees, view code with syntax highlighting for 30+ languages
- **Code Search** — Regex-powered search across entire repositories
- **Code Index** — Auto-index functions, classes, and exports across 8 languages (Python, TypeScript, JavaScript, Java, Go, Rust, Ruby, PHP)
- **Write-Back** — Build Phase can write generated code directly to repository files
- **Git Operations** — Commit, push, branch management, PR creation — all from within ZECT

### 3.3 Enterprise Controls

| Feature | Description |
|---------|-------------|
| **Audit Trail** | Complete logging of all AI operations, code changes, and user actions |
| **Token Controls** | Per-user, per-team budgets with threshold alerts (5 tabs: Overview, User Activity, Teams, Budget, Trends) |
| **Rules Engine** | Custom code quality rules, deployment gates, webhook kill switches |
| **Permissions** | Role-based access control for features and projects |
| **Secrets Manager** | Secure storage for API keys and credentials |

### 3.4 Zinnia Intelligence Layer

A proprietary 4-layer intelligence system:

1. **Memory System** — Project memory, skill memory, episodic and semantic memory storage
2. **Dream Engine** — Background processing for pattern discovery and optimization
3. **Data Layer** — Structured data management for project insights
4. **Data Flywheel** — Continuous improvement loop: usage → learning → better suggestions

### 3.5 Multi-Project Management

Unlike single-session AI tools, ZECT provides:

- **Dashboard** — Real-time overview of all projects, active stages, and risk alerts
- **Projects** — Create/manage multiple projects with metadata, stage tracking, and repo associations
- **Orchestration** — Cross-project dependency management with Kanban boards and resource tracking
- **Analytics** — Charts for stage distribution, project status, team performance, and completion metrics

---

## 4. Architecture

### System Architecture

```
┌──────────────────────────────────────────────┐
│              Client (Browser)                 │
│    React + TypeScript + Vite + Tailwind       │
└─────────────────────┬────────────────────────┘
                      │ REST API
┌─────────────────────▼────────────────────────┐
│           FastAPI Backend (Python)            │
│  38 routers │ 35+ SQLAlchemy models          │
│  67+ endpoints │ Auto-indexer │ Clone Service │
└──────┬──────────────┬────────────────────────┘
       │              │
┌──────▼──────┐ ┌─────▼─────────┐
│ PostgreSQL  │ │ LLM Provider  │
│ (RDS/Local) │ │ (Configurable)│
└─────────────┘ └───────────────┘
```

### Backend API Domains (38 Routers)

| Domain | Endpoints | Description |
|--------|-----------|-------------|
| Projects | `/api/projects/*` | CRUD, stages, repos |
| LLM | `/api/llm/*` | Ask, plan, build, review |
| Repo Clone | `/api/repos/*` | Clone, pull, branches, checkout |
| Repo Browser | `/api/repos/*/browse/*` | File tree, read, search, write |
| Code Review | `/api/code-review/*` | PR review, snippet, full-repo scan |
| Analytics | `/api/analytics/*` | Stage distribution, team metrics |
| Token Controls | `/api/token/*` | Usage tracking, budgets |
| Audit | `/api/audit/*` | Trail logging and querying |
| Git Operations | `/api/git/*` | Status, commit, branch, PR |
| CI Monitor | `/api/ci/*` | GitHub Actions workflows |
| Settings | `/api/settings/*` | User preferences, API keys |
| + 27 more | Various | Full-featured backend |

---

## 5. Competitive Positioning

### What ZECT Does Differently

| Capability | ZECT | Typical AI Coding Tools |
|-----------|------|------------------------|
| Self-hosted / air-gapped | Yes — runs on Zinnia infrastructure | No — SaaS only |
| Multi-project dashboard | Yes — 6+ projects simultaneously | No — single session |
| Token budget controls | Per-user, per-team granular | Organization-level only |
| Audit trail | Full compliance logging | Session logs only |
| Model flexibility | Choose per-feature (OpenAI, Anthropic, Ollama) | Fixed single model |
| Stage-based workflow | Ask → Plan → Build → Review → Deploy | Linear / unstructured |
| Repository integration | Clone, browse, index, write-back, search | Requires separate VM/sandbox |
| Cost transparency | Per-call, per-user, per-model cost tracking | Monthly invoice only |

### Where ZECT Needs Investment

| Gap | Description | Effort |
|-----|-------------|--------|
| Autonomous execution | Chain stages automatically without user intervention | 4-6 weeks |
| Auto-fix loop | Detect errors → AI fix → re-run cycle | 3-4 weeks |
| Session persistence | Maintain context across pages/stages | 2-3 weeks |
| CI/CD auto-fix | Auto-fix failing CI checks | 2 weeks |

---

## 6. Security & Compliance

- **Self-hosted**: All code and data remain on Zinnia infrastructure
- **No external data transfer**: LLM API calls contain only the specific context sent by the user
- **Audit trail**: Every AI operation is logged with timestamp, user, model, tokens, and cost
- **Secrets management**: Encrypted storage for API keys with role-based access
- **Rules engine**: Configurable gates for code quality and deployment approval
- **Role-based access**: Permissions system controls feature access per user/team

---

## 7. Deployment Options

| Option | Best For | Setup Time |
|--------|----------|------------|
| Docker Compose (EC2) | Small-medium teams, quick start | 30 minutes |
| AWS ECS Fargate | Large teams, auto-scaling | 2-4 hours |
| Kubernetes | Enterprise-scale, multi-region | 1-2 days |

All options support PostgreSQL (RDS), environment-based configuration, and CI/CD deployment pipelines.

---

## 8. ROI & Business Value

| Metric | Expected Impact |
|--------|-----------------|
| Developer productivity | 20-40% reduction in boilerplate code writing time |
| Code review speed | 50-70% faster initial review with AI pre-analysis |
| Project visibility | 100% — all projects visible in single dashboard |
| AI cost control | Per-user budgets prevent runaway token spend |
| Compliance | Full audit trail eliminates manual compliance reporting |
| Tool consolidation | Replace 3-5 separate tools with one platform |

---

## 9. Roadmap

### Completed (v2.0)
- 33 screens across 5 sidebar sections
- 67+ backend endpoints
- Deep repository integration (clone, browse, index, write-back)
- Active project context with global selector
- Enterprise controls (audit, rules, permissions, token budgets)
- Zinnia Intelligence layer (memory, dream engine, data flywheel)

### Next (v3.0 — Estimated 6-8 weeks)
- Agent Mode (autonomous multi-step execution)
- Auto-fix loop with error detection
- Session persistence across pages
- CI/CD failure auto-remediation
- Enhanced knowledge base from past sessions
- Desktop application packaging

---

## 10. Conclusion

ZECT is not just an AI coding assistant — it is a **complete engineering delivery control tower** that provides the governance, visibility, and AI capabilities Zinnia's engineering organization needs. Its self-hosted architecture, enterprise controls, and multi-project management capabilities differentiate it from commodity AI coding tools while providing a foundation for increasingly autonomous AI-assisted development.

---

*Zinnia Technology — Internal Document — May 2026*
