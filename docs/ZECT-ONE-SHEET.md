# ZECT — One-Sheet Executive Summary

## Zinnia Engineering Control Tower v2.0

---

### What Is ZECT?

ZECT is a **self-hosted, AI-powered engineering delivery platform** that consolidates the entire software development lifecycle — from requirements analysis through deployment — into a single web application. Built by Zinnia for Zinnia, it runs entirely on internal infrastructure with zero data leaving the network.

---

### At a Glance

| Metric | Value |
|--------|-------|
| **Screens** | 33 fully functional |
| **Backend Endpoints** | 67+ REST APIs |
| **Sidebar Sections** | 5 (Navigation, Workflow, Intelligence, Features, Enterprise) |
| **Supported AI Models** | OpenAI, Anthropic, Ollama (local) — configurable per feature |
| **Languages Indexed** | 8 (Python, TypeScript, JavaScript, Java, Go, Rust, Ruby, PHP) |
| **Syntax Highlighting** | 30+ languages |
| **Database** | PostgreSQL (production) / SQLite (dev) |
| **Deployment** | Docker Compose / AWS EC2 / AWS ECS Fargate |

---

### Five Functional Areas

| Area | Screens | Purpose |
|------|---------|---------|
| **Navigation** | Dashboard, Projects, Orchestration, Repo Analysis, Blueprint, Doc Generator, Code Review, Analytics, Docs Center, Settings | Core project management and analysis |
| **Workflow Stages** | Ask, Plan, Build, Review, Deploy, Skills, Token Controls, App Runner, File Explorer, Git Ops, CI Monitor, Repo Workspace | Full AI-assisted development lifecycle |
| **Zinnia Intelligence** | Memory, Dream Engine, Data Layer, Data Flywheel, Permissions, Transfer, Skills Engine | Proprietary learning and intelligence layer |
| **Features** | Knowledge Base, Playbooks, Scheduled Tasks, Secrets, Code Index, Session Insights, Conversations | Supporting infrastructure and automation |
| **Enterprise** | Audit Trail, Rules Engine, Integrations, Export/Share, Output History | Compliance, governance, and control |

---

### Key Differentiators

| What | Why It Matters |
|------|---------------|
| **Self-hosted** | All data stays on Zinnia infrastructure — critical for insurance compliance |
| **Multi-project dashboard** | Engineering managers see all projects at once, not one session at a time |
| **Per-user token budgets** | Control AI spending per person and per team with threshold alerts |
| **Full audit trail** | Every AI operation logged — timestamp, user, model, tokens, cost |
| **Model flexibility** | Choose the best AI model per feature — no vendor lock-in |
| **Deep repo integration** | Clone, browse, index, search, and write code directly to repos |
| **Stage-based workflow** | Standardized Ask → Plan → Build → Review → Deploy pipeline |

---

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui |
| Backend | Python 3.10+ / FastAPI / SQLAlchemy |
| Database | PostgreSQL (RDS) |
| AI Integration | Provider-agnostic — configurable API keys per model |
| Deployment | Docker Compose on AWS EC2 or ECS Fargate |

---

### Deployment Architecture

```
Route 53 (DNS) → ALB (HTTPS) → Frontend (S3/CloudFront) + Backend (ECS/EC2) → RDS PostgreSQL
```

- **Simple**: Docker Compose on a single EC2 instance (30 min setup)
- **Scalable**: AWS ECS Fargate with auto-scaling (2-4 hour setup)

---

### Roadmap

| Version | Status | Key Features |
|---------|--------|-------------|
| **v2.0** | Done | 33 screens, 67+ endpoints, deep repo integration, enterprise controls |
| **v3.0** | 6-8 weeks | Agent Mode (autonomous execution), Auto-Fix Loop, Session Persistence |
| **v3.5** | 12 weeks | CI/CD auto-remediation, Knowledge Base learning, Desktop App |

---

### Business Value

- **20-40%** reduction in boilerplate coding time
- **50-70%** faster initial code review with AI pre-analysis
- **100%** project visibility across all teams in one dashboard
- **Full compliance** with automated audit trail (no manual reporting)
- **Zero data leakage** — self-hosted on Zinnia infrastructure
- **Replace 3-5 tools** with one unified platform

---

**Repository:** `KarthikKaruppasamy880/ZECT`
**Documentation:** 80+ markdown files in `docs/` folder
**Screenshots:** 42 screen captures in `docs/screenshots/`

*Zinnia Technology — May 2026*
