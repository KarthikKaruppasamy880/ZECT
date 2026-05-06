# ZECT Tool — Complete Functionality Guide & Gap Analysis

## 1. Navigation Sections — What Each Does & Current Status

| Section | Purpose | Status | What's Missing |
|---------|---------|--------|----------------|
| **Dashboard** | Token usage control, project overview, cost tracking | Working | Model selection control, usage limits |
| **Projects** | Create/manage engineering projects with stages | Working | Auto-stage progression |
| **Orchestration** | Multi-agent workflow coordination | UI Only | Needs backend agent dispatch logic |
| **Repo Analysis** | Analyze any GitHub repo structure | Working | Needs deeper analysis (dependencies, patterns) |
| **Blueprint** | AI-generated architecture blueprint from repo | Working | Auto-save as Skill template |
| **Doc Generator** | Generate documentation from code | Working | — |
| **Code Review** | AI-powered PR review (like CodeRabbit) | Working | Needs auto-fix prompt generation |
| **Analytics** | Usage analytics, cost breakdown | Working | Per-model breakdown |
| **Docs Center** | Internal docs viewer | Working | — |
| **Settings** | LLM config, API keys, model selection | Working | Rate limit controls |
| **Ask Mode** | Chat with AI about engineering questions | Working | Skills auto-save |
| **Plan Mode** | Generate phased engineering plans | Working | Auto-create project from plan |
| **Build Phase** | Execute plan steps with AI | Placeholder | **Needs full implementation** |
| **Review** | Review built code for quality | Placeholder | **Needs full implementation** |
| **Deployment** | Deploy reviewed code | Placeholder | **Needs full implementation** |

---

## 2. Test Cases for Each Section

### Dashboard
```
TEST: View token usage summary
STEPS: Login → Dashboard loads → See total API calls, tokens, estimated cost
EXPECTED: Shows real numbers from PostgreSQL, updates after each AI call
```

### Ask Mode
```
TEST: Ask engineering question and see code output
STEPS: Navigate to Ask Mode → Type "Write a Python FastAPI health check endpoint" → Press Enter
EXPECTED: AI responds with code block displayed in dark-themed CodeOutput panel with Copy/Download buttons
```

### Plan Mode
```
TEST: Generate phased engineering plan
STEPS: Navigate to Plan Mode → Type "Migrate a monolithic Java app to microservices" → Click Generate
EXPECTED: Returns multi-phase plan with phases listed as badges, full plan in CodeOutput panel
```

### Blueprint Generator
```
TEST: Generate repo blueprint
STEPS: Navigate to Blueprint → Enter GitHub repo URL → Click Generate
EXPECTED: Returns architecture diagram, tech stack, file structure analysis, and migration prompt
```

### Code Review (vs Review)
```
TEST: AI-powered PR review
STEPS: Navigate to Code Review → Select project with linked repo → Select PR → Click Analyze
EXPECTED: Returns security issues, code quality findings, and a "Fix Prompt" for each issue
```

### Repo Analysis
```
TEST: Analyze repository structure
STEPS: Navigate to Repo Analysis → Enter repo owner/name → Click Analyze
EXPECTED: Returns file tree, tech stack detection, complexity metrics
```

---

## 3. How ZECT Works for Different Project Types

### New Project
```
1. Dashboard → Create Project (name, description, team, tech stack)
2. Ask Mode → "How should I architect a claims processing microservice?"
3. Plan Mode → Generate phased plan from the Ask Mode discussion
4. Blueprint → Generate architecture blueprint (auto-saved as Skill template)
5. Build Phase → AI builds code following the plan (step by step)
6. Review → AI reviews the built code for quality/security
7. Deployment → Deploy to staging/production
```

### Existing Project
```
1. Projects → Link existing GitHub repo
2. Repo Analysis → Analyze current structure, identify tech debt
3. Code Review → Review open PRs with AI (find bugs, security issues)
4. Ask Mode → "How do I refactor this service to improve performance?"
5. Plan Mode → Generate improvement plan
6. Build Phase → AI implements improvements
7. Review → Validate changes
```

### Legacy Project Migration
```
1. Repo Analysis → Deep scan of legacy codebase
2. Blueprint → Generate "as-is" architecture blueprint (captures current state)
3. Ask Mode → "How should I modernize this from Java 8 monolith to Spring Boot microservices?"
4. Plan Mode → Generate migration plan with phases:
   - Phase 1: Strangler fig pattern setup
   - Phase 2: Extract first microservice
   - Phase 3: Data migration
   - etc.
5. Build Phase → AI builds migration code, service by service
6. Code Review → Validate each migration step
7. Deployment → Blue/green deployment to minimize risk
```

---

## 4. Skills Auto-Save Workflow

### How It Should Work:
```
When user completes Ask → Plan → Build cycle:
1. System detects successful pattern (e.g., "React component creation")
2. Auto-extracts the prompt template used
3. Saves as a Skill with:
   - Name: "Create React Component with Tests"
   - Template: The prompt pattern that worked
   - Context: What repo/project type it applies to
   - Tags: [react, component, testing]
4. Next time user has similar task → Skill suggested automatically
5. User can edit/customize saved Skills
```

### Current State: NOT YET IMPLEMENTED
### What Needs Building:
- Skill detection engine (pattern recognition from successful workflows)
- Skill CRUD API endpoints
- Skill suggestion engine (match context → suggest relevant skills)
- UI: Skill library browser, edit/create interface

---

## 5. Orchestration — How It Works

### Purpose:
Orchestration coordinates multiple AI agents working in parallel on different parts of a project.

### How It Should Work:
```
Example: "Build a user authentication system"

Orchestration breaks this into:
├── Agent 1: Build database schema (models, migrations)
├── Agent 2: Build API endpoints (auth routes, middleware)
├── Agent 3: Build frontend (login form, auth context)
└── Agent 4: Build tests (unit, integration)

Each agent:
1. Gets assigned a sub-task from the plan
2. Works independently with its own context
3. Reports progress back to Orchestration
4. Orchestration merges results and resolves conflicts
```

### Current State: UI shows workflow visualization, but no backend dispatch
### What Needs Building:
- Task decomposition engine (break plan into parallel sub-tasks)
- Agent dispatch system (assign sub-tasks to AI sessions)
- Progress tracking (real-time status of each agent)
- Merge/conflict resolution (combine outputs)

---

## 6. Code Review vs Review — The Difference

| | **Code Review** (Navigation) | **Review** (Workflow Stage) |
|---|---|---|
| **When** | Anytime — for open PRs | After Build Phase completes |
| **What** | Reviews existing PRs on GitHub | Reviews code you just built with AI |
| **Input** | GitHub PR (diff) | Code generated in Build Phase |
| **Output** | Issues + Fix Prompts | Approve / Request Changes |
| **Like** | CodeRabbit (external review) | Pull Request Review (internal QA) |

### Code Review (sidebar nav):
- Connects to GitHub repo
- Pulls PR diffs
- AI analyzes for: security, performance, code quality, patterns
- Generates "Fix Prompt" → send to agent to auto-fix

### Review (workflow stage):
- Happens AFTER Build Phase
- Reviews what the AI just built
- Checks against the original Plan
- Validates: tests pass, no regressions, matches requirements
- Gate: must pass before Deployment

---

## 7. Blueprint — Complete 100% Workflow

```
Step 1: INPUT — Enter repo URL (e.g., github.com/zinnia/legacy-claims-app)

Step 2: ANALYSIS — AI performs:
  - File structure scan
  - Tech stack detection (languages, frameworks, versions)
  - Architecture pattern identification (monolith, microservices, etc.)
  - Dependency graph
  - Entry points and API surface
  - Database schema detection

Step 3: BLUEPRINT OUTPUT:
  ┌─────────────────────────────────────────┐
  │ Architecture: Monolithic Java 8         │
  │ Framework: Spring MVC 4.x               │
  │ Database: Oracle 12c                    │
  │ Frontend: JSP + jQuery                  │
  │ Build: Maven                            │
  │ Tests: JUnit 4 (38% coverage)           │
  │ Entry Points: 47 REST endpoints         │
  │ LOC: 125,000                            │
  │ Complexity: HIGH                        │
  └─────────────────────────────────────────┘

Step 4: MIGRATION PROMPT (auto-generated):
  "Given this Java 8 Spring MVC monolith with 47 endpoints,
   generate a migration plan to Spring Boot 3.x microservices.
   Prioritize: claims-processing, policy-admin, billing.
   Constraints: zero-downtime, Oracle → PostgreSQL migration."

Step 5: SEND TO PLAN MODE → Generates phased migration plan
Step 6: SEND TO BUILD PHASE → AI builds service by service
Step 7: AUTO-SAVE AS SKILL → "Legacy Java → Spring Boot Migration" template
```

---

## 8. Token Management & Model Control (Dashboard)

### What's Currently Tracked:
- Total API calls
- Total tokens (prompt + completion)
- Estimated cost

### What Needs to Be Added:
```
┌─────────────────────────────────────────────┐
│ MODEL CONTROL PANEL                         │
├─────────────────────────────────────────────┤
│ Active Model: GPT-4o-mini                   │
│ Fallback Model: GPT-3.5-turbo              │
│                                             │
│ LIMITS:                                     │
│ ├── Daily token limit: [50,000] tokens      │
│ ├── Per-request max: [4,096] tokens         │
│ ├── Monthly budget: [$50.00]                │
│ └── Alert at: [80%] usage                   │
│                                             │
│ USAGE THIS MONTH:                           │
│ ├── GPT-4o-mini: 32,400 tokens ($0.48)     │
│ ├── GPT-4o: 8,200 tokens ($1.23)           │
│ └── Total: 40,600 tokens ($1.71)           │
│                                             │
│ CONTEXT MANAGEMENT:                         │
│ ├── Max context window: [128K] tokens       │
│ ├── Context strategy: [Sliding Window]      │
│ └── Include repo context: [Yes/No]          │
└─────────────────────────────────────────────┘
```

---

## 9. Context Management Strategy

### How Context Should Work:
```
Session Start:
├── Load project context (tech stack, conventions)
├── Load relevant Skills (matching tags)
├── Load recent conversation history (sliding window)
└── Estimate token budget remaining

During Session:
├── Track tokens used per request
├── Warn when approaching limit
├── Auto-summarize old context when window fills
└── Prioritize: recent context > project context > general

Smart Context:
├── When in Code Review → auto-include PR diff
├── When in Blueprint → auto-include repo structure
├── When in Build → auto-include plan + relevant files
└── When in Ask → include conversation history only
```

---

## 10. What Needs to Be Built (Priority Order)

### HIGH Priority (Core Functionality):
1. **Build Phase** — Full AI code generation from plan steps
2. **Review Phase** — AI code quality gate
3. **Deployment Phase** — Deployment orchestration
4. **Token Limit Controls** — Dashboard model/budget controls
5. **Fix Prompt Generation** — Code Review → auto-fix workflow

### MEDIUM Priority (Differentiators):
6. **Skills Auto-Save** — Pattern detection and template saving
7. **Orchestration Backend** — Multi-agent task dispatch
8. **Context Management** — Smart context loading per page
9. **Model Selection** — Per-task model routing

### LOWER Priority (Polish):
10. **Analytics Per-Model** — Breakdown by model used
11. **Skill Library** — Browse/search/edit saved skills
12. **Export/Share** — Export plans, blueprints as PDF/Markdown

---

## Summary: Making ZECT the Best AI Tool for Zinnia

ZECT's unique value proposition:
1. **Not just another chat** — It's a structured workflow (Ask → Plan → Build → Review → Deploy)
2. **Context-aware** — Knows your repo, your project, your constraints
3. **Token-controlled** — You control the cost, not the AI
4. **AI-agnostic** — Works with any LLM provider (OpenAI, Anthropic, Bedrock, etc.)
5. **Skills-driven** — Learns from successful patterns, gets better over time
6. **Blueprint-first** — Understand before you build (especially for legacy migration)
