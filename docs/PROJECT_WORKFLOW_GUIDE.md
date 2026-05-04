# ZECT Project Creation & Workflow Guide

> How projects are created, managed, and moved through the 5-stage delivery pipeline.

---

## The 5-Stage Delivery Model

ZECT follows a structured 5-stage workflow for every engineering project:

```
Ask  -->  Plan  -->  Build  -->  Review  -->  Deploy
```

Each stage has defined activities, deliverables, and gates that must be met before advancing.

---

## Project Creation

### Via the UI

1. Navigate to **Projects** in the sidebar
2. Click **"+ New Project"** (top-right blue button)
3. Fill in the form:

| Field | Required | Description |
|-------|----------|-------------|
| Project Name | Yes | Short, descriptive name (e.g., "Claims API v2") |
| Description | No | Detailed description of the project scope |
| Team | No | Team responsible (e.g., "Platform Engineering") |
| Repo Owner | No | GitHub owner (e.g., "KarthikKaruppasamy880") |
| Repo Name | No | Repository name (e.g., "ZECT") |

4. Click **"Create Project"**

### Via the API

```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Claims API v2",
    "description": "New claims processing API with real-time validation",
    "team": "Claims Engineering",
    "current_stage": "ask",
    "repos": [
      { "owner": "KarthikKaruppasamy880", "repo_name": "ZECT" }
    ]
  }'
```

### What Happens on Creation

1. **Database record created** — Project stored in SQLite `projects` table
2. **Default stage set** — Projects start in the "ask" stage
3. **Repos linked** — If owner/repo provided, a `repos` record is created linking to the project
4. **Timestamps set** — `created_at` and `updated_at` auto-populated
5. **Redirect** — UI navigates to the new project's detail page

---

## Project Lifecycle

### Stage 1: Ask Mode

**Purpose:** Understand the problem, gather requirements, explore the codebase.

**Activities:**
- Ask engineering questions via the AI chat interface
- Analyze existing repositories for patterns and architecture
- Gather requirements and constraints

**How to Use:**
1. Navigate to **Ask Mode** (sidebar -> Workflow -> Ask Mode)
2. Type your question in the chat input
3. Optionally add repo context (toggle "Add repo context")
4. Press Enter or click Send
5. Review the AI response

**Stage Gates:**
- Requirements understood
- Technical feasibility confirmed
- Scope defined

### Stage 2: Plan Mode

**Purpose:** Create a structured engineering plan with phases, milestones, and risk assessment.

**Activities:**
- Generate engineering plans from project descriptions
- Define phases and milestones
- Assess risks and resource requirements

**How to Use:**
1. Navigate to **Plan Mode** (sidebar -> Workflow -> Plan Mode)
2. Enter your project/feature description
3. Optionally expand "Advanced Options" to add repo context and constraints
4. Click **"Generate Engineering Plan"**
5. Review the phased plan
6. Click **"Copy Plan"** to share with your team

**Stage Gates:**
- Plan approved by tech lead
- Architecture decisions documented
- Resource allocation confirmed

### Stage 3: Build Phase

**Purpose:** Implement the solution following the plan.

**Key Activities:**
- Test-driven development
- Code reviews (inline via PR Viewer)
- CI/CD pipeline integration
- Feature branch management
- Documentation updates

**ZECT Features Used:**
- **Repo Analysis** — Understand existing codebase patterns
- **Blueprint Generator** — Generate AI prompts for implementation
- **Doc Generator** — Auto-generate documentation
- **PR Viewer** — Review pull requests with file diffs
- **Orchestration** — Monitor multi-repo status

**Stage Gates:**
- Code coverage meets threshold
- CI pipeline passing
- Security scan clean
- Patterns follow established conventions

### Stage 4: Review

**Purpose:** Quality assurance, security review, performance testing.

**Key Activities:**
- Security vulnerability scanning
- Performance/load testing
- Accessibility audit
- Code quality review
- Documentation review

**ZECT Features Used:**
- **PR Viewer** — Review code changes and file diffs
- **Analytics** — Track project health metrics
- **Settings** — Configure review severity thresholds

**Stage Gates:**
- No critical bugs unresolved
- Security audit passed
- Performance requirements met
- Accessibility standards met

### Stage 5: Deploy

**Purpose:** Release to production with monitoring and rollback capabilities.

**Key Activities:**
- Blue/green or canary deployment
- Health check verification
- Monitoring dashboard setup
- Runbook creation
- Rollback plan testing

**Stage Gates:**
- Staging environment verified
- Rollback plan tested
- Monitoring alerts configured
- Runbook reviewed

---

## Project Management

### Updating a Project

**Via UI:** Navigate to the project detail page. Fields can be updated through the API.

**Via API:**
```bash
curl -X PUT http://localhost:8000/api/projects/1 \
  -H "Content-Type: application/json" \
  -d '{
    "current_stage": "build",
    "completion_percent": 55.0,
    "status": "active"
  }'
```

### Linking Repositories

Repos are linked at project creation time. Each repo tracks:
- Owner and repo name
- Default branch
- CI status (passing/failing/pending/unknown)
- Code coverage percentage
- Last sync timestamp

### Project Statuses

| Status | Meaning |
|--------|---------|
| `active` | Currently being worked on |
| `completed` | All stages finished, deployed |
| `on-hold` | Paused, awaiting decision or resources |

### Deleting a Project

```bash
curl -X DELETE http://localhost:8000/api/projects/1
```

This cascades to delete all linked repos.

---

## Analytics Integration

The Dashboard and Analytics pages pull data from all projects:

| Metric | Source |
|--------|--------|
| Total/Active/Completed counts | Count by status |
| Stage Distribution | Count by `current_stage` |
| Average Completion | Mean of `completion_percent` |
| Average Token Savings | Mean of `token_savings` |
| Risk Alerts | Sum of `risk_alerts` across projects |
| Team Performance | Group by `team` field |

---

## Demo Projects (Auto-Seeded)

On first startup, ZECT seeds 6 demo projects to showcase the workflow:

| Project | Team | Stage | Completion |
|---------|------|-------|------------|
| Policy Admin Modernization | Platform Engineering | build | 55% |
| Claims Processing API | Claims Engineering | review | 78% |
| Agent Portal Redesign | Product Engineering | plan | 28% |
| Underwriting Rules Engine | Underwriting Tech | deploy | 92% |
| Customer Notifications Service | Platform Engineering | deploy | 100% |
| Document Intelligence Pipeline | AI/ML Engineering | ask | 8% |

These demonstrate projects at various stages of the delivery pipeline and are linked to real GitHub repos where applicable.

---

## Workflow Integration with ZEF

ZECT's workflow model aligns with ZEF's 5-phase delivery model:

| ZECT Stage | ZEF Phase | ZEF Playbooks |
|------------|-----------|---------------|
| Ask | Orient | Repo Analysis, Project Setup |
| Plan | Plan | Feature Build (planning phase) |
| Build | Execute | Feature Build, Bug Fix, Refactor |
| Review | Verify | Code Review, Security Review |
| Deploy | Close | Deployment, Post-mortem |

ZEF skills (Context Manager, Task Planner, etc.) are used throughout the workflow to maintain context across AI sessions.
