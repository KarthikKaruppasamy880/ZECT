# Zinnia Intelligence System — User Manual

> Complete guide to the Zinnia Memory System, Dream Engine, Data Layer, Skills Engine, Permissions, and Transfer features in ZECT.

## Table of Contents

1. [Overview](#overview)
2. [Memory System](#memory-system)
3. [Dream Engine](#dream-engine)
4. [Data Layer](#data-layer)
5. [Data Flywheel](#data-flywheel)
6. [Permissions](#permissions)
7. [Transfer & Onboarding](#transfer--onboarding)
8. [Skills Engine](#skills-engine)
9. [API Reference](#api-reference)
10. [Configuration](#configuration)

---

## Overview

The Zinnia Intelligence System adds a structured memory and learning layer to ZECT. It enables the tool to:

- **Remember** what happened across sessions (episodic memory)
- **Learn** from patterns and mistakes (semantic memory / lessons)
- **Track** agent activity and costs (data layer)
- **Enforce** safety rules on operations (permissions)
- **Transfer** knowledge between projects (transfer bundles)
- **Match** the right skill to the right task (skills engine)

All features are accessible via the sidebar under **Zinnia Intelligence**.

---

## Memory System

### What It Does

The Memory System stores and retrieves knowledge across 4 layers:

| Layer | Purpose | Retention |
|---|---|---|
| **Working Memory** | Current task state (files, hypotheses, next step) | Archived after 2 days inactive |
| **Episodic Memory** | What happened in past sessions | Decayed after 30 days |
| **Semantic Memory** | Distilled lessons and decisions | Permanent (human-reviewed) |
| **Personal Memory** | Your preferences and constraints | Permanent, never shared |

### How to Use

**Navigate to:** Sidebar > Zinnia Intelligence > Memory System

#### Tabs

- **Working Memory** — View and create workspace snapshots for your current task
- **Episodic** — Browse past events, filter by skill, success/failure, importance
- **Lessons** — View graduated lessons, search by keyword, filter by status
- **Decisions** — View architectural decisions with rationale
- **Preferences** — Set your code style, workflow, and constraint preferences

#### Key Operations

| Operation | What It Does | API Endpoint |
|---|---|---|
| **Recall** | Find relevant lessons for a given intent | `POST /api/memory/recall` |
| **Reflect** | Log a significant event to episodic memory | `POST /api/memory/reflect` |
| **Learn** | Teach a lesson directly (one-shot) | `POST /api/memory/learn` |
| **Search** | Full-text search across all memory layers | `GET /api/memory/search?q=...` |

---

## Dream Engine

### What It Does

The Dream Engine automatically extracts patterns from episodic memory and stages candidate lessons for human review. It runs periodically or on-demand.

### Pipeline

1. **Load** recent episodes (last 14 days)
2. **Cluster** similar events by lexical similarity
3. **Extract** patterns from clusters with 3+ members
4. **Stage** candidate lessons (idempotent — same pattern = same candidate)
5. **Prefilter** junk candidates (too short, too vague, duplicates)
6. **Decay** old episodes (> 30 days)
7. **Archive** stale workspaces (> 2 days inactive)

### How to Use

**Navigate to:** Sidebar > Zinnia Intelligence > Dream Engine

- **Run Dream Cycle** — Click to trigger a manual dream cycle
- **Run History** — View past dream cycle results (candidates staged, episodes decayed)
- **Review Queue** — See pending candidates waiting for your review
  - **Graduate** — Accept a candidate as a permanent lesson
  - **Reject** — Reject with a reason
  - **Reopen** — Move a rejected candidate back to pending

---

## Data Layer

### What It Does

Tracks all agent activity across tools (ZECT, and any other harness) with token usage, cost estimates, and success rates. Provides dashboards and daily reports.

### How to Use

**Navigate to:** Sidebar > Zinnia Intelligence > Data Layer

#### Dashboard Panels

- **KPI Cards** — Total events, success rate, tokens used, cost
- **Events Over Time** — Line chart of activity by day
- **Category Breakdown** — Pie chart of work distribution
- **Harness Breakdown** — Compare activity across AI tools
- **Model Breakdown** — Token usage and cost by LLM model

#### Daily Reports

- Auto-generated summaries with trends and breakdowns
- Compare to previous periods
- Export as CSV for external analysis

#### Export

- `GET /api/data-layer/export/csv` — Export events as CSV-compatible JSON
- Filter by project, harness, date range

---

## Data Flywheel

### What It Does

Converts approved agent runs into training-ready artifacts:

1. **Traces** — Redacted input/output pairs from approved runs
2. **Context Cards** — Clustered patterns from traces
3. **Eval Cases** — Input/expected/actual triplets for testing AI quality

### How to Use

**Navigate to:** Sidebar > Zinnia Intelligence > Data Flywheel

- **Traces** — Browse and approve redacted traces
- **Context Cards** — View clustered patterns
- **Eval Cases** — Create and run evaluation test cases

---

## Permissions

### What It Does

Enforces safety rules on all agent operations using a 3-tier model:

| Level | Behavior | Examples |
|---|---|---|
| **Always Allowed** | No approval needed | Read files, run tests, search |
| **Requires Approval** | Human must confirm | Merge PRs, deploy, delete files |
| **Never Allowed** | Blocked entirely | Force push, access secrets, drop DB |

### How to Use

**Navigate to:** Sidebar > Zinnia Intelligence > Permissions

- **Rules** — View and edit permission rules
- **Create Rule** — Add new permission rules with pattern matching
- **Audit Log** — View all permission checks (granted, denied, pending)
- **Hook Patterns** — Define regex patterns for high-risk operation detection

---

## Transfer & Onboarding

### What It Does

**Transfer:** Export your brain state (memory, lessons, preferences, skills) as a bundle and import it into another project.

**Onboarding:** A 6-question wizard that collects your preferences when starting a new project.

### How to Use

**Navigate to:** Sidebar > Zinnia Intelligence > Transfer & Onboard

#### Transfer

- **Export** — Package your current memory into a transfer bundle
  - Select components: lessons, decisions, episodes, preferences, skills
  - Automatic secret detection scanning
  - SHA-256 checksums for integrity
- **Import** — Load a bundle into the current project
  - Preview changes before importing
  - Merge logic prevents duplicates

#### Onboarding

- **Start Onboarding** — Answer 6 questions about your preferences
  1. Preferred code style
  2. Development approach (TDD, code-first, design-first)
  3. Commit size preference
  4. Communication style
  5. Constraints (hard limits)
  6. Testing philosophy
- **Feature Toggles** — Enable/disable optional features

---

## Skills Engine

### What It Does

A registry of reusable skills with trigger-based matching. When you express an intent (e.g., "debug this API"), the engine finds the best matching skill.

### Seed Skills (8 built-in)

| Skill | Category | Purpose |
|---|---|---|
| zinnia-code-review | quality | Code review with configurable rulesets |
| zinnia-debug | engineering | Systematic debugging workflow |
| zinnia-deploy | operations | Pre-deploy checklist with approval gate |
| zinnia-git-safety | operations | Safety constraints on git operations |
| zinnia-memory-manager | meta | Reflection cycles and consolidation |
| zinnia-skillforge | meta | Create new skills from patterns |
| zinnia-blueprint | design | Project blueprint generation |
| zinnia-migration | engineering | Legacy migration assistance |

### How to Use

**Navigate to:** Sidebar > Zinnia Intelligence > Skills Engine

- **Registry** — Browse all skills, filter by category
- **Trigger Match** — Enter an intent and see which skills match
- **Execution Logs** — View skill execution history
- **Create Skill** — Add a custom skill with triggers and steps

---

## API Reference

All Zinnia Intelligence APIs are under the `/api/` prefix.

### Memory

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/memory/working` | Create working memory entry |
| GET | `/api/memory/working` | List working memory entries |
| POST | `/api/memory/episodic` | Log episodic event |
| GET | `/api/memory/episodic` | List episodic events |
| POST | `/api/memory/lessons` | Create a lesson |
| GET | `/api/memory/lessons` | List lessons |
| POST | `/api/memory/decisions` | Create a decision |
| GET | `/api/memory/decisions` | List decisions |
| POST | `/api/memory/preferences` | Save user preferences |
| GET | `/api/memory/preferences` | Get user preferences |
| POST | `/api/memory/recall` | Recall relevant lessons |
| POST | `/api/memory/reflect` | Log a reflection |
| POST | `/api/memory/learn` | One-shot lesson teaching |
| GET | `/api/memory/search` | Full-text search |

### Dream Engine

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/dream-engine/run` | Trigger dream cycle |
| GET | `/api/dream-engine/runs` | List dream cycle runs |
| GET | `/api/dream-engine/candidates` | List pending candidates |
| POST | `/api/dream-engine/graduate/{id}` | Graduate a candidate |
| POST | `/api/dream-engine/reject/{id}` | Reject a candidate |

### Data Layer

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/data-layer/events` | Log an agent event |
| GET | `/api/data-layer/events` | List agent events |
| POST | `/api/data-layer/dashboard` | Get analytics dashboard |
| POST | `/api/data-layer/daily-report` | Generate daily report |
| GET | `/api/data-layer/daily-reports` | List daily reports |
| GET | `/api/data-layer/export/csv` | Export events as CSV |

### Permissions

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/permissions/rules` | Create permission rule |
| GET | `/api/permissions/rules` | List permission rules |
| POST | `/api/permissions/check` | Check if action is allowed |
| GET | `/api/permissions/audit` | View audit log |

### Transfer

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/transfer/export` | Export brain state |
| POST | `/api/transfer/import` | Import brain state |
| GET | `/api/transfer/bundles` | List transfer bundles |
| POST | `/api/transfer/onboarding` | Submit onboarding answers |

### Skills Engine

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/skills-engine/skills` | List all skills |
| GET | `/api/skills-engine/skills/{id}` | Get skill details |
| POST | `/api/skills-engine/skills` | Create a skill |
| POST | `/api/skills-engine/match` | Match skills to intent |
| POST | `/api/skills-engine/executions` | Log skill execution |
| GET | `/api/skills-engine/executions` | List execution logs |

---

## Configuration

### Database

The Zinnia Intelligence System uses the same database as ZECT. Tables are created automatically on first startup.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./zect.db` | Database connection string |
| `DREAM_CYCLE_INTERVAL_HOURS` | `6` | Dream cycle auto-run interval |
| `EPISODIC_DECAY_DAYS` | `30` | Days before episodes are archived |
| `WORKSPACE_INACTIVE_DAYS` | `2` | Days before workspaces are archived |

### PostgreSQL Setup

For production use, switch to PostgreSQL:

```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/zect
```

All tables will be created automatically on first startup.
