# ZECT Workflow Documentation

**Status:** Complete Analysis  
**Date:** July 23, 2026  
**Version:** 3.0.0

---

## Executive Summary

ZECT is a production-grade AI-governed engineering delivery platform with **6 fully-implemented workflow modules** orchestrated through a unified FastAPI backend (59 routers), React frontend (51 pages), and Electron desktop application.

All modules are **fully functional and integrated**:
- **Workspace** — Project/repo management with 50+ database models
- **Understand** — Code analysis via Lattice service with symbol graphs
- **Deliver** — Multi-phase orchestration (Ask→Plan→Build→Review→Deploy)
- **Quality** — Code review with CWE/OWASP mapping and approval workflows
- **Enterprise** — RBAC, audit trails, token budgets, cost tracking
- **Labs** — Memory system, Dream Engine, Data Flywheel, Playbooks, Skills Engine

---

## Module 1: WORKSPACE — Project & Repository Management

### Purpose
Centralized project and repository management, providing the foundation for all downstream workflows.

### Entry Points
- **Backend Router:** `/api/projects` (59 routes total)
- **Frontend Pages:** `Projects.tsx`, `ProjectDetail.tsx`, `CreateProject.tsx`, `RepoWorkspace.tsx`

### User Journey

```
1. User creates project via CreateProject.tsx
   ↓
2. Selects/adds GitHub repositories
   ↓
3. System auto-indexes repo structure (Lattice)
   ↓
4. Project visible in Projects list with status badge
   ↓
5. Project provides entry point to Understand/Deliver/Quality modules
```

### Backend Workflow

```
POST /api/projects
  ↓ FastAPI validates via ProjectCreate schema
  ↓ Create Project record (status=active, current_stage=ask)
  ↓ For each repo: Clone + run Lattice indexing
  ↓ Return project_id + repo list
  
GET /api/projects
  ↓ List all projects with status, completion%, token_savings
  
PUT /api/projects/{id}
  ↓ Update project stage (ask → plan → build → review → deploy)
```

### Data Flow

```
User Input (ProjectCreate)
  ↓
Projects table (name, description, team, status, current_stage)
  ↓
Repos table (project_id, owner, repo_name, clone_status, local_path)
  ↓
CodeSymbol table (indexed symbols via Lattice)
  ↓
Displayed in UI with status badges
```

### Key Entities

| Entity | Purpose | Rows |
|--------|---------|------|
| Project | Delivery pipeline grouping | 1-1000 |
| Repo | GitHub repository reference | 5-50 per project |
| CodeSymbol | Indexed code entities | 1000-100K per repo |

### Integration Points

| Module | Integration | Direction |
|--------|-------------|-----------|
| Understand | Triggers Lattice indexing | →  |
| Deliver | Reads project scope for orchestration | ← |
| Quality | Creates review sessions per project | ← |
| Enterprise | Applies permissions, audit logs | ↔ |
| Labs | Provides context for memory/Dream | → |

### Status: ✅ COMPLETE
- 100% feature coverage
- All CRUD operations implemented
- Status tracking, completion metrics, team scoping
- No gaps identified

---

## Module 2: UNDERSTAND — Code Analysis & Repository Intelligence

### Purpose
Deep repository analysis, code graph construction, knowledge extraction, and semantic search.

### Entry Points
- **Backend Routers:** `/api/lattice`, `/api/code-index`, `/api/analysis` (3 routers)
- **Frontend Pages:** `LatticeGraph.tsx`, `CodeIndex.tsx`, `RepoAnalysis.tsx`

### User Journey

```
1. User clicks "Analyze" on project
   ↓
2. Lattice ingests repo structure
   ↓
3. System indexes all symbols (functions, classes, endpoints)
   ↓
4. User searches code via CodeIndex or views graph
   ↓
5. Graph shows relationships, dependencies, architecture
   ↓
6. Mentor queries lattice for code recommendations
```

### Backend Workflow — Lattice Service

```
POST /api/lattice/ingest
  ↓ Parse all files in repo (language-specific regex)
  ↓ Extract symbols: functions, classes, methods, endpoints, variables
  ↓ Build dependency graph (calls, imports, references)
  ↓ Build structural blueprint (tech stack, architecture, god nodes)
  ↓ Store in CodeSymbol, EmbeddingChunk tables
  ↓ Return blueprint JSON

POST /api/lattice/query
  ↓ Full-text search on symbol names + docs
  ↓ Return ranked hits with kind (function, class, endpoint, etc.)

POST /api/lattice/path
  ↓ Find dependency path: source → target
  ↓ Return edges + intermediate nodes

POST /api/lattice/blueprint
  ↓ Synthesize structural blueprint from indexed graph
  ↓ Return: tech_stack, api_endpoints, functions, classes, dependencies, god_nodes
```

### Data Flow

```
Repository (cloned to disk)
  ↓
Language-specific parsers (regex-based for Python, TS, JS)
  ↓
CodeSymbol table (50K-100K rows per repo)
  ├─ file_path, symbol_name, kind, signature, docstring
  └─ line_start, line_end, parent_symbol
  
EmbeddingChunk table (1K-10K chunks for RAG)
  ├─ content (code snippet + docs)
  └─ embedding_json (vector representation)

LatticeStructuralBlueprint (1 per repo)
  ├─ file_tree_json
  ├─ functions_json
  ├─ classes_json
  ├─ api_endpoints_json
  ├─ dependency_graph_json
  ├─ tech_stack_json
  └─ god_nodes_json (architectural hubs)
```

### Key Capabilities

| Capability | Status | Details |
|------------|--------|---------|
| Symbol indexing | ✅ READY | Functions, classes, methods, variables |
| Dependency graph | ✅ READY | Call chains, import paths, references |
| Blueprint synthesis | ✅ READY | Tech stack, architecture, patterns |
| RAG retrieval | ✅ READY | Hybrid search (keyword + semantic) |
| Path finding | ✅ READY | Dependency chains between symbols |
| Explanation | ✅ READY | Relationship descriptions |

### Integration Points

| Module | Integration | Direction |
|--------|-------------|-----------|
| Workspace | Triggered by repo add | ← |
| Deliver | Provides context for generation | → |
| Quality | Pattern analysis for reviews | → |
| Labs | Feeds into Dream/Data Flywheel | → |
| Mentrix | Query tool in Companion | ← |

### Limitations & Gaps

| Gap | Impact | Fix |
|-----|--------|-----|
| No Tree-Sitter AST | Can't analyze types/calls deeply | Integrate Tree-sitter per language |
| No semantic analysis | Missing implicit relationships | Add type inference layer |
| Regex-based parsing | May miss edge cases | Switch to proper parsers |

### Status: ✅ COMPLETE (with gaps noted)
- Core functionality 100% implemented
- Deep code understanding requires Tree-Sitter (future enhancement)

---

## Module 3: DELIVER — Build Execution & Code Generation

### Purpose
Orchestrated, multi-phase delivery pipeline from requirements through code generation to deployment.

### Entry Points
- **Backend Routers:** `/api/build`, `/api/deploy`, `/api/orchestration`, `/api/mentrix` (4 routers)
- **Frontend Pages:** `AskMode.tsx`, `PlanMode.tsx`, `BuildPhase.tsx`, `DeployPhase.tsx`, `AppRunner.tsx`

### User Journey — Full Workflow

```
1. User enters Ask mode: "Port C service to TypeScript"
   ↓
2. Workspace + Lattice context injected
   ↓
3. LLM generates structured plan (8 stages)
   ↓
4. User reviews → click "Approve"
   ↓
5. Build phase executes:
   - Scout: Collect repo context
   - Planner: Decompose into tasks
   - Builder: Generate code
   - Reviewer: AI code review
   - Fixer: Auto-recovery
   - Integrator: File modifications
   ↓
6. Quality gates applied (lint, sandbox, review, API eval)
   ↓
7. User approves → PR created on GitHub
   ↓
8. Deploy phase generates runbook + checklist
```

### Backend Workflow — Orchestration (ForgeLoop)

**State Machine:**
```
created → running → awaiting_approval → approved → pr_created → completed
               ↓
           needs_human (blocker)
               ↓
           failed / cancelled
```

**Agent Roles (8 total):**
1. **Scout** — Collect Lattice + RAG context
2. **Planner** — Decompose goal into stages
3. **Builder** — Generate code
4. **Reviewer** — AI code review, find issues
5. **Fixer** — Auto-recovery for lint/test failures
6. **Integrator** — Apply changes to repo
7. **Ops** — Deployment orchestration
8. **Orchestrator** — FSM + phase coordination

**Execution Modes:**
- `chat` — Simple Q&A (Scout + Orchestrator)
- `understand` — Repository analysis (Scout only)
- `deliver` — Full pipeline (all phases)
- `review_only` — Code review (Reviewer + Fixer)
- `ops` — Deployment (Ops + Integrator)
- `upgrade` — Language migration (full pipeline)

### Data Flow — Code Generation

```
User Request (goal, mode, project_id)
  ↓
MentrixRun created (status=running)
  ↓
Scout Phase:
  ├─ Fetch project from Workspace
  ├─ Query Lattice for repo structure
  ├─ Retrieve RAG chunks for context
  └─ Build context_json (8KB max)
  ↓
Planner Phase:
  ├─ LLM analyzes goal + context
  ├─ Generates plan (stages, tasks, decisions)
  └─ Store in MentrixRun.gates_json
  ↓
Builder Phase:
  ├─ For each stage: LLM generates code
  ├─ Store in GeneratedOutput table
  └─ Apply language-specific formatting
  ↓
Reviewer Phase:
  ├─ Run code review (AI + linting)
  ├─ Classify findings (bug, security, style)
  ├─ Return issues to Builder
  └─ Fixer attempts recovery (max 3 attempts)
  ↓
Approval Gate:
  ├─ User views generated code + review findings
  ├─ Approves or requests changes
  └─ Update MentrixRun.approved_by
  ↓
Integrator Phase:
  ├─ Create branch on GitHub
  ├─ Commit generated code
  ├─ Create pull request
  └─ Return PR URL
  ↓
MentrixRun.status = pr_created
```

### Quality Gates

| Gate | Blocks | Behavior |
|------|--------|----------|
| `lint_ok` | BUILD | Must pass linting (ruff, eslint) |
| `sandbox_ready` | BUILD | Code structure valid |
| `review_ok` | BUILD | No critical/high findings |
| `api_eval_ok` | BUILD | API contracts preserved |
| `incomplete_ok` | BUILD | If forced, allow incomplete |

### Key Entities

| Table | Purpose | Rows |
|-------|---------|------|
| MentrixRun | Orchestration run | 1-100 per project |
| AgentRun | Agent execution context | 1:1 with MentrixRun |
| AgentStep | Individual agent work | 6-20 per run |
| GeneratedOutput | Code/plan/review artifacts | 5-50 per run |

### Integration Points

| Module | Integration | Direction |
|--------|-------------|-----------|
| Workspace | Reads project scope | ← |
| Understand | Consumes Lattice context | ← |
| Quality | Invokes code review gate | → |
| Enterprise | Approval workflows | ← |
| Labs | Event logging, trace data | → |
| Mentrix | Entry point (start_delivery) | ← |

### Status: ✅ COMPLETE
- All phases fully implemented
- FSM orchestration working
- Quality gates enforced
- GitHub PR creation tested

---

## Module 4: QUALITY — Testing, Code Review & Validation

### Purpose
Multi-dimensional code quality assessment, automated review, and approval workflows.

### Entry Points
- **Backend Routers:** `/api/review`, `/api/review-phase`, `/api/ultrareview`, `/api/rules` (4 routers)
- **Frontend Pages:** `CodeReview.tsx`, `ReviewPhase.tsx`, `PRViewer.tsx`

### User Journey

```
1. User submits code for review (snippet, PR, or full repo)
   ↓
2. AI review agent analyzes code
   ↓
3. Findings extracted with severity + CWE mapping
   ↓
4. Rules engine applies custom rules
   ↓
5. Quality score calculated (0-100)
   ↓
6. Review gating decision: pass/fail/needs_approval
   ↓
7. If findings exist: Fixer auto-suggests fixes
   ↓
8. User reviews fixes → approve or request changes
```

### Backend Workflow — Code Review

```
POST /api/review/pr
  ↓ Fetch PR diff from GitHub
  ↓ Parse changed files + context
  ↓ Submit to LLM with review prompt
  ↓ LLM returns findings (JSON):
     [
       {
         "file": "src/main.py",
         "line": 42,
         "category": "security",
         "severity": "critical",
         "title": "SQL injection",
         "description": "...",
         "suggestion": "Use parameterized queries",
         "cwe_id": "CWE-89",
         "owasp": "A03:2021"
       }
     ]
  ↓ Store in ReviewFinding table
  ↓ Calculate quality score
  ↓ Return findings + score to UI

POST /api/review/autofix
  ↓ For each finding: generate fix
  ↓ Apply fix to repo
  ↓ Re-run review to verify
  ↓ Repeat up to 3 times
  ↓ Report final status (fixed/unfixable)
```

### Quality Gates

**Categories:**
- Bug (logic errors, crashes)
- Security (vulnerabilities, data exposure)
- Performance (inefficiency, resource leaks)
- Style (formatting, naming)
- Architecture (patterns, abstractions)
- Best Practice (design patterns, standards)

**Severity Levels:**
- Critical (blocks merge)
- High (requires review)
- Medium (should fix)
- Low (nice to have)
- Info (informational)

### Rules Engine

**Custom Rules Format:**
```python
Rule:
  - action_pattern: regex (e.g., "force_push_main")
  - rule_type: "security|quality_gate|deploy|naming"
  - condition: JSON matching logic
  - action: "warn|block|auto_fix|notify"
  - severity: "critical|high|medium"
```

**Example Rules (Predefined):**
- No force-push to main
- All commits require review
- No hardcoded secrets
- Test coverage > 80%
- No console.log in production

### Key Entities

| Table | Purpose | Rows |
|-------|---------|------|
| ReviewSession | Code review context | 1-100 per project |
| ReviewFinding | Individual findings | 5-200 per session |
| Rule | Custom validation rules | 5-50 per org |

### Capabilities vs. Status

| Capability | Status | Details |
|------------|--------|---------|
| AI code review | ✅ READY | LLM-based finding extraction |
| Multi-category analysis | ✅ READY | Bug, security, perf, style, arch |
| CWE/OWASP mapping | ✅ READY | Vulnerability classification |
| Auto-fix suggestion | ✅ READY | LLM generates fixes |
| Auto-fix verification | ✅ READY | Re-review after fix |
| Custom rules engine | ✅ READY | Configurable enforcement |
| GitHub webhook integration | ✅ READY | Auto-review on PR |

### Integration Points

| Module | Integration | Direction |
|--------|-------------|-----------|
| Understand | Pattern analysis from code graph | ← |
| Deliver | Review gate for Build phase | ← |
| Enterprise | Audit logging, approval workflows | ← |
| Labs | Event logging, traces | → |

### Status: ✅ COMPLETE
- All review capabilities implemented
- CWE/OWASP mapping integrated
- Auto-fix loop functional
- Rules engine enforced

---

## Module 5: ENTERPRISE — Multi-User, Permissions, Audit & Governance

### Purpose
Organization-wide governance: RBAC, permissions, audit trails, cost tracking, compliance.

### Entry Points
- **Backend Routers:** `/api/permissions`, `/api/audit`, `/api/export`, `/api/tokens` (4 routers)
- **Frontend Pages:** `Permissions.tsx`, `AuditTrail.tsx`, `Settings.tsx`

### User Journey — Admin

```
1. Admin logs in to Settings → Permissions
   ↓
2. Views current permission rules (40+ predefined)
   ↓
3. Creates custom rule: "Require approval for force_push"
   ↓
4. Assigns to project or global
   ↓
5. Rule enforced on all future operations
   ↓
6. Audit trail shows all rule matches + enforcement
```

### Authorization Model

**Role Hierarchy:**
```
admin           (full access, can modify rules)
  ↓
lead            (manage team, approve operations)
  ↓
developer       (create, review, deploy within scope)
  ↓
viewer          (read-only access)
```

**Permission Rules (40+ predefined):**

| Rule | Scope | Default | Comment |
|------|-------|---------|---------|
| `read_file` | git | allow | Always allowed |
| `create_branch` | git | allow | Safe operation |
| `merge_pr` | git | require_approval | High impact |
| `force_push_main` | git | never | Dangerous |
| `start_delivery` | companion | require_approval | AI workflow |
| `approve_delivery` | companion | require_approval | Human gate |
| `create_pr` | companion | require_approval | Code integration |
| `slack_send` | integration | require_approval | External comms |
| `email_send` | integration | require_approval | External comms |
| `deploy_production` | deploy | never | Only admin |
| `modify_secrets` | admin | never | Dangerous |

### Backend Workflow — Permission Checking

```
User executes action (e.g., merge_pr)
  ↓
check_tool_permission(action, user_id, project_id)
  ↓
Query PermissionRule matching action_pattern
  ↓
Decision:
  - ALLOW: Execute immediately
  - REQUIRE_APPROVAL: Show confirmation modal
  - NEVER: Block + return error
  ↓
Log in PermissionAudit table
  ↓
Return result to UI
```

### Token & Cost Tracking

**TokenBudget Entity:**
```python
TokenBudget:
  - scope: global|team|user
  - daily_token_limit: int
  - monthly_token_limit: int
  - daily_cost_limit_usd: float
  - monthly_cost_limit_usd: float
  - alert_threshold_percent: int
  - enforce_limits: bool
```

**TokenLog Entity (per request):**
```python
TokenLog:
  - user_id, session_id
  - action (ask, plan, build, review, deploy)
  - feature, model (gpt-4, gpt-4o-mini)
  - prompt_tokens, completion_tokens, total_tokens
  - estimated_cost_usd
  - latency_ms, status (success, error, rate_limited)
```

### Audit Trail

**AuditLog Entity:**
```python
AuditLog:
  - user_id, action (create, update, delete, login, logout, export)
  - resource_type (project, repo, rule, secret, user)
  - resource_id, resource_name
  - details: JSON (what changed, why)
  - ip_address, user_agent
  - timestamp
```

**Queryable Fields:**
- Date range filter
- User filter
- Action filter
- Resource type filter
- Severity filter (only important changes)

### Key Entities

| Table | Purpose | Rows |
|-------|---------|------|
| User | User accounts | 1-10K |
| PermissionRule | Access control rules | 40-100 |
| PermissionAudit | Rule enforcement log | 100-1M |
| AuditLog | Complete activity log | 1M-100M |
| TokenBudget | Spending limits | 1-100 |
| TokenLog | Token consumption | 1-100M |

### Integration Points

| Module | Integration | Direction |
|--------|-------------|-----------|
| All modules | Permission enforcement | ↔ |
| Deliver | Approval gates | ← |
| Labs | User preferences stored | ↔ |

### Status: ✅ COMPLETE
- RBAC fully implemented
- 40+ predefined rules
- Audit trail comprehensive
- Token budgets enforced
- Cost tracking per user/model

---

## Module 6: LABS — Experimental Features & Advanced Capabilities

### Purpose
Advanced AI capabilities: learning systems, memory management, training data pipelines, automation.

### Submodules

#### 6.1 Memory System (4-Layer Architecture)

**Layers:**

1. **Working Memory**
   - Active task state, open files, hypotheses
   - Auto-archived after 2 days inactivity
   - Per-project, per-user

2. **Episodic Memory**
   - Raw experience log: what was done, outcome
   - Success/failure tracking
   - Salience decay (0.0-1.0)
   - Importance scoring (1-10)

3. **Semantic Memory**
   - Distilled lessons (via Dream Engine)
   - Architectural decisions with rationale
   - Confidence scoring
   - Applicability conditions

4. **Personal Memory**
   - User preferences (code style, workflow)
   - Feature flags
   - Never merged into semantic memory

**Entry Point:** `/api/memory`

#### 6.2 Dream Engine (Automated Learning Loop)

**Workflow:**
```
1. Cluster episodic episodes by similarity (threshold: 0.3)
2. Extract common patterns from clusters (min_occurrences: 3)
3. Stage candidates for human review
4. Prefilter low-confidence candidates
5. Decay old/stale episodes (max_age: 30 days)
```

**Output:** Lessons staged in Lessons table for human graduation

**Entry Point:** `/api/dream`

#### 6.3 Data Layer (Cross-Agent Monitoring)

**Capabilities:**
- Event tracking across all workflows (ask, plan, build, review, deploy)
- KPI dashboard (throughput, reliability, avg_cost)
- Daily automated reports
- Harness breakdown (zect, devin, cursor, etc.)
- Category breakdown (coding, review, deploy, planning, debugging)

**Entry Point:** `/api/data-layer`

#### 6.4 Data Flywheel (Training Data Pipeline)

**4-Stage Pipeline:**
1. **Traces** — Redacted input/output from approved runs
2. **Context Cards** — Clustered patterns from traces
3. **Eval Cases** — Test cases extracted from cards
4. **Fine-Tuning** — Training data for model improvement

**Entry Point:** `/api/flywheel`

#### 6.5 Additional Labs Features

| Feature | Entry Point | Purpose |
|---------|------------|---------|
| Knowledge Base | `/api/knowledge-base` | Persistent tips, instructions, notes |
| Playbooks | `/api/playbooks` | Reusable prompt templates + workflows |
| Scheduled Tasks | `/api/scheduler` | Cron-based recurring jobs |
| Conversations | `/api/conversations` | Named threads with persistence |
| Secrets Manager | `/api/secrets` | Encrypted credential storage |
| Skills Engine | `/api/skills-engine` | Reusable AI skill templates |
| Agent Mode | `/api/agent-mode` | Autonomous multi-step runs |
| Persistent Sessions | `/api/persistent-sessions` | Cross-page context |

### Key Entities

| Table | Purpose |
|-------|---------|
| WorkingMemory | Active task state |
| EpisodicMemory | Experience log |
| Lesson | Learned patterns |
| Decision | Architectural decisions |
| UserPreference | User-specific settings |
| DreamCycleRun | Learning cycle history |
| AgentEvent | Cross-harness monitoring |
| DailyReport | KPI summaries |
| FlywheelTrace | Training data source |
| FlywheelContextCard | Pattern clusters |
| FlywheelEvalCase | Test cases |

### Status: ✅ COMPLETE
- All Labs subsystems fully implemented
- Memory system with 4 layers operational
- Dream Engine clustering + staging working
- Data Flywheel pipeline ready for fine-tuning

---

## Module Integration Matrix

```
Workspace       → Understand (code analysis)
                → Deliver (build tasks)
                → Quality (review sessions)
                → Enterprise (audit logs)

Understand      ← Workspace (repo context)
                → Deliver (blueprint input)
                → Quality (pattern analysis)
                → Labs (episodic memory)

Deliver         ← Workspace (project scope)
                ← Understand (blueprints)
                → Quality (review gates)
                → Labs (event logging, traces)
                → Enterprise (approval gates)

Quality         ← Understand (code analysis)
                ← Deliver (generated code)
                → Enterprise (audit logs)
                → Labs (event logging, traces)

Enterprise      ← All modules (audit everything)
                → All modules (permission enforcement)
                → Labs (user preferences, constraints)

Labs            ← All modules (event + trace data)
                → Memory (decision making)
                → Dream Engine (pattern extraction)
                → Data Layer (KPI aggregation)
                → Data Flywheel (training data)
```

---

## User Workflows by Role

### Developer

```
1. Open Projects → Create new project
2. Link GitHub repos → System auto-indexes (Understand)
3. Enter Mentrix (Ask mode) → Describe task
4. Review plan → Approve
5. Build phase runs automatically
6. Review generated code + AI findings
7. Approve → PR created automatically
8. System tracks token usage, cost
```

### Lead/Manager

```
1. Open Analytics dashboard
2. View KPIs: throughput, reliability, team efficiency
3. Open AuditTrail → review recent actions
4. Permissions → create/modify rules
5. Settings → configure token budgets
6. View team's learning progress (Dream Engine)
```

### Admin

```
1. Settings → Manage users, roles, SSO
2. Permissions → Org-wide policy
3. Secrets Manager → Rotate API keys
4. AuditTrail → Compliance monitoring
5. Data Layer → Monitor costs, resource usage
```

---

## Conclusion

ZECT is a **production-ready, fully-integrated platform** with:
- **6 complete workflow modules** (Workspace, Understand, Deliver, Quality, Enterprise, Labs)
- **50+ database models** with full relationships
- **59 API routers** handling all operations
- **51 frontend pages** covering all user journeys
- **Electron desktop app** for voice/desktop integration
- **Advanced AI capabilities** (memory, learning, orchestration)

All modules are interconnected and fully functional. No major gaps in core functionality; enhancements are in areas like Tree-Sitter integration and advanced semantic analysis.
