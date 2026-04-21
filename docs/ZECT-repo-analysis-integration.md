# ZECT — Repo Analysis & Prompt Generation Integration

## How to Achieve 100% Repository Analysis for Legacy, New, and Existing Projects

> This document analyzes the reverse-engineering prompt-generation pattern and provides a complete strategy and prompts for building this capability natively into ZECT (Zinnia Engineering Delivery Control Tower).

---

## 1. What the Pattern Does (High-Level)

The core idea is simple but powerful:

1. **Input:** A user provides a GitHub repository URL (or `owner/repo` slug)
2. **Context Extraction:** The system pulls three things from GitHub's API:
   - **Repository metadata** — description, primary language, stars, topics, default branch
   - **File tree** — the full recursive directory structure (optionally filtered to depth-1 for the LLM)
   - **README contents** — decoded from base64 via the GitHub Contents API
3. **LLM Synthesis:** All three are assembled into a structured user message and sent to an LLM with a system prompt that says: "Given this repo context, produce a synthetic user prompt that would recreate this project from scratch"
4. **Output:** A natural-language prompt (~120-200 words) that captures what the project does and how someone would ask an AI tool to build it

### Why This Matters for ZECT

ZECT's 5-stage workflow (Ask > Plan > Build > Review > Deploy) can use this pattern in **three critical scenarios**:

| Scenario | How Repo Analysis Helps |
|---|---|
| **Legacy repo migration** | Analyze the existing codebase, extract its architecture/patterns/stack, and generate a structured migration brief that feeds directly into Ask Mode |
| **New project creation** | Analyze a reference/template repo to generate a starting prompt with the right stack, patterns, and architecture decisions pre-loaded |
| **Existing project enhancement** | Analyze the current repo to understand what's already built, then generate a focused prompt for the specific enhancement needed |

---

## 2. Technical Architecture for ZECT Integration

### 2.1 Data Flow

```
User pastes repo URL
        |
        v
[GitHub API Layer]
  |-- GET /repos/{owner}/{repo}           --> metadata (language, description, topics, stars)
  |-- GET /repos/{owner}/{repo}/branches/{branch}  --> branch SHA
  |-- GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1  --> full file tree
  |-- GET /repos/{owner}/{repo}/readme    --> README content (base64 decoded)
        |
        v
[Context Assembly Layer]
  |-- Format file tree as ASCII directory listing
  |-- Truncate README to ~8,000 chars if needed
  |-- Build structured user message with metadata + tree + README
        |
        v
[LLM Prompt Generation Layer]
  |-- System prompt tailored to the scenario (migration / new / enhancement)
  |-- User message = assembled repo context
  |-- LLM returns synthesized prompt or analysis
        |
        v
[ZECT Workflow Integration]
  |-- Output feeds into Ask Mode as pre-populated requirements
  |-- Or feeds into Plan Mode as architecture context
  |-- Cached for re-use (optional Supabase/DB layer)
```

### 2.2 GitHub API Functions Needed

ZECT needs four core API functions:

| Function | Purpose | API Endpoint |
|---|---|---|
| `getRepoMeta(owner, repo)` | Get description, language, stars, topics, default branch | `GET /repos/{owner}/{repo}` |
| `getFileTree(owner, repo, branch)` | Get full recursive file tree | `GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1` |
| `getReadme(owner, repo, branch)` | Get README content (base64 decoded) | `GET /repos/{owner}/{repo}/readme` |
| `readFile(owner, repo, path, branch)` | Read any specific file (package.json, etc.) | `GET /repos/{owner}/{repo}/contents/{path}` |

**Key implementation details:**
- Always try `main` branch first, fall back to `master` if 404
- Use `GITHUB_TOKEN` for authenticated requests (higher rate limits: 5,000/hr vs 60/hr)
- Handle errors gracefully: 401 (auth), 403 (rate limit), 404 (not found)
- Decode file contents from base64: `Buffer.from(content, 'base64').toString('utf-8')`

### 2.3 File Tree Formatting

The file tree needs to be converted from GitHub's flat array format into a human-readable ASCII tree:

```
Input (GitHub API):
[
  { path: "src", type: "tree" },
  { path: "src/app", type: "tree" },
  { path: "src/app/page.tsx", type: "blob" },
  { path: "package.json", type: "blob" }
]

Output (formatted):
owner/repo/
├── src/
│   └── app/
│       └── page.tsx
└── package.json
```

**Filtering options:**
- Filter by depth (depth-1 for quick overview, full for detailed analysis)
- Filter by path (scope to specific subdirectories)
- Sort: directories first, then alphabetical

### 2.4 LLM Integration

**Provider options (in priority order):**
1. **OpenRouter** — multi-model gateway, recommended (supports Gemini, Claude, GPT-4, etc.)
2. **Google AI Studio** — direct Gemini access
3. **Any OpenAI-compatible API** — same request format works

**Request structure:**
```json
{
  "model": "google/gemini-2.5-pro",
  "messages": [
    { "role": "system", "content": "<scenario-specific system prompt>" },
    { "role": "user", "content": "<assembled repo context>" }
  ]
}
```

### 2.5 Caching Strategy

To avoid redundant API calls and LLM invocations:
- Cache by `owner/repo` key
- Store in Supabase (or any DB): `{ owner, repo, prompt, cached_at }`
- Upsert on conflict (owner, repo)
- In-flight deduplication: use a `Map<string, Promise>` to prevent parallel requests for the same repo

---

## 3. Three Scenario-Specific System Prompts for ZECT

### 3.1 Legacy Repo Migration Prompt

```
You are an expert enterprise architect specializing in legacy system migration.

## Task

You are given **repository metadata**, a **file tree**, and the **README** for an existing legacy system. Produce a **comprehensive migration analysis brief** that a Zinnia engineering team can use to plan and execute a modernization effort.

## What the output must include

1. **Current State Assessment**
   - Tech stack identification (languages, frameworks, databases, infrastructure)
   - Architecture pattern (monolith, microservices, layered, etc.)
   - Estimated codebase complexity (based on file count, directory depth, naming patterns)
   - Key dependencies and integration points

2. **Migration Risk Analysis**
   - Critical dependencies that may block migration
   - Data migration concerns (based on model/schema files if visible)
   - Integration points that need careful handling
   - Estimated effort level (S/M/L/XL)

3. **Recommended Migration Strategy**
   - Suggested target architecture
   - Phased migration approach (strangler fig, big bang, parallel run)
   - Priority order for module migration
   - Quick wins vs. heavy lifts

4. **Generated Ask Mode Prompt**
   - A natural-language prompt that a team member could paste into ZECT's Ask Mode to kick off the migration project
   - Should capture the full scope, constraints, and goals

## Formatting

Use markdown with clear headers. Be specific and actionable. Reference actual file paths and patterns you observe in the tree. Do not invent features not supported by the evidence.
```

### 3.2 New Project Creation Prompt

```
You are an expert full-stack engineer who helps teams start new projects efficiently.

## Task

You are given **repository metadata**, a **file tree**, and the **README** for a reference/template project. Produce a **new project specification** that captures the architecture patterns, tech decisions, and project structure so a team can create a similar (but original) project for Zinnia's internal use.

## What the output must include

1. **Architecture Blueprint**
   - Identified tech stack and why it was chosen
   - Project structure pattern (app router, API routes, component organization)
   - Key architectural decisions visible from the structure
   - Data flow patterns

2. **Reusable Patterns**
   - Component architecture style
   - State management approach
   - API/routing patterns
   - Configuration and environment setup

3. **Generated Ask Mode Prompt**
   - A natural-language prompt (~200-400 words) that a team member could paste into ZECT's Ask Mode to create a new project inspired by this reference
   - Must NOT copy the original — should describe the desired outcome in original Zinnia language
   - Should specify the stack, key features, and architecture preferences

4. **Recommended Customizations for Zinnia**
   - What to keep from the reference
   - What to change for enterprise use
   - Security, compliance, and scalability considerations

## Formatting

Use markdown with clear headers. Be honest about what you can and cannot determine from the file tree alone.
```

### 3.3 Existing Project Enhancement Prompt

```
You are an expert software engineer who understands large codebases quickly.

## Task

You are given **repository metadata**, a **file tree**, and the **README** for an existing Zinnia project. A team member wants to add new functionality or improve the project. Produce an **enhancement analysis** that helps them plan the work within ZECT's workflow.

## What the output must include

1. **Codebase Understanding**
   - Current tech stack and architecture
   - Key directories and their purposes
   - Patterns used (naming conventions, component structure, API design)
   - Current state of testing, CI/CD, documentation

2. **Enhancement Readiness Assessment**
   - Areas well-structured for extension
   - Areas that may need refactoring first
   - Missing foundations (tests, types, docs) that should be addressed
   - Dependency health (based on package files if visible)

3. **Generated Ask Mode Prompt**
   - A template prompt the team member can customize with their specific enhancement request
   - Pre-loaded with codebase context so the AI assistant understands the existing architecture
   - Structured to work with ZECT's 5-stage workflow

4. **Impact Analysis Starter**
   - Files/directories most likely affected by common enhancement types
   - Integration points to watch
   - Testing areas that need attention

## Formatting

Use markdown with clear headers. Reference specific file paths from the tree.
```

---

## 4. ZECT Integration Points

### 4.1 Where This Fits in the ZECT UI

| ZECT Page | Integration |
|---|---|
| **Dashboard** | "Analyze Repo" button — quick repo analysis from the main dashboard |
| **Create New Project** | Step 1 of the wizard — paste a repo URL to pre-populate the project brief |
| **Ask Mode** | "Import from Repo" — analyze a repo and auto-fill the requirements |
| **Plan Mode** | "Analyze Existing Architecture" — pull in current architecture from a repo for impact analysis |
| **Orchestration** | "Add Repo" — analyze a repo to understand its role in the multi-repo ecosystem |

### 4.2 New API Routes Needed

```
POST /api/analyze-repo
  Body: { repoUrl: string, scenario: "migration" | "new" | "enhancement" }
  Returns: { analysis: string, askModePrompt: string, metadata: RepoMeta }

POST /api/repo-tree
  Body: { repoUrl: string, depth?: number, paths?: string[] }
  Returns: { tree: string, metadata: RepoMeta }

GET /api/repo-cache?owner=X&repo=Y
  Returns: { cached: boolean, analysis?: string, cachedAt?: string }
```

### 4.3 New Components Needed

```
components/
  repo-analyzer/
    RepoInput.tsx          — URL input with validation and example repos
    RepoAnalysisCard.tsx   — Display analysis results with copy/export
    ScenarioSelector.tsx   — Choose migration / new / enhancement
    RepoTreeViewer.tsx     — Interactive file tree display
    AnalysisHistory.tsx    — Previously analyzed repos
```

### 4.4 Data Model Additions

```typescript
// types/index.ts additions

interface RepoAnalysis {
  id: string;
  owner: string;
  repo: string;
  scenario: 'migration' | 'new' | 'enhancement';
  metadata: {
    description: string | null;
    language: string | null;
    stars: number;
    topics: string[];
    defaultBranch: string;
  };
  fileTree: string;
  readme: string;
  analysis: string;        // LLM-generated analysis
  askModePrompt: string;   // Generated prompt for Ask Mode
  analyzedAt: string;
  projectId?: string;      // Link to ZECT project if created from analysis
}
```

---

## 5. Implementation Phases for ZECT

### Phase 1: Core Repo Analysis (Prototype — Mock Data)
- [ ] Add "Analyze Repo" input to Dashboard
- [ ] Build `RepoInput` component with URL parsing/validation
- [ ] Build `RepoAnalysisCard` to display mock analysis results
- [ ] Add scenario selector (Migration / New Project / Enhancement)
- [ ] Mock the analysis output with realistic sample data
- [ ] Wire into "Create New Project" wizard as Step 1

### Phase 2: GitHub API Integration (Backend)
- [ ] Implement `getRepoMeta()`, `getFileTree()`, `getReadme()`, `readFile()`
- [ ] Implement file tree formatting (ASCII tree output)
- [ ] Build `POST /api/analyze-repo` route
- [ ] Add `GITHUB_TOKEN` environment variable support
- [ ] Handle rate limiting and error states in UI

### Phase 3: LLM Integration (Backend)
- [ ] Implement OpenRouter/Google AI Studio client
- [ ] Build context assembly (metadata + tree + README → user message)
- [ ] Implement three scenario-specific system prompts
- [ ] Add response caching (Supabase or database)
- [ ] In-flight deduplication for concurrent requests
- [ ] Add `OPENROUTER_API_KEY` environment variable support

### Phase 4: Workflow Integration
- [ ] Wire analysis output into Ask Mode (pre-populate requirements)
- [ ] Wire analysis output into Plan Mode (pre-load architecture context)
- [ ] Add "Import from Analysis" to Orchestration (add repo to multi-repo view)
- [ ] Build analysis history view
- [ ] Add export/share functionality for analysis results

### Phase 5: Advanced Features
- [ ] Deep file reading — go beyond README, read `package.json`, `tsconfig.json`, CI configs
- [ ] Custom focus prompts — user describes what aspect to analyze
- [ ] Multi-repo analysis — analyze multiple repos at once for orchestration planning
- [ ] Diff analysis — compare two repos or two branches
- [ ] Scheduled re-analysis — track how repos evolve over time

---

## 6. Environment Variables Required

```env
# GitHub API (for repo analysis)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# LLM Provider (choose one)
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxx
# OPENROUTER_MODEL=google/gemini-2.5-pro   (optional, defaults to gemini-2.5-pro)

# Or use Google AI Studio directly
# GOOGLE_GENERATIVE_AI_API_KEY=xxxxxxxxxxxx

# Cache (optional)
# SUPABASE_URL=https://xxxx.supabase.co
# SUPABASE_PUBLISHABLE_KEY=xxxxxxxxxxxx
```

---

## 7. Key Design Decisions

| Decision | Recommendation | Rationale |
|---|---|---|
| File tree depth for LLM | Depth 1 for quick analysis, full for deep analysis | Keeps token costs manageable while providing enough context |
| README truncation | 8,000 characters max | Prevents token overflow while capturing key information |
| LLM model | Gemini 2.5 Pro via OpenRouter | Best cost/quality ratio for code understanding tasks |
| Caching | Cache by owner/repo/scenario | Avoid redundant LLM calls; cache invalidation on re-analyze |
| Auth | GitHub token optional but recommended | Unauthenticated: 60 req/hr; Authenticated: 5,000 req/hr |
| Error handling | Graceful degradation | If GitHub API fails, show partial results. If LLM fails, show raw context |

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| GitHub API rate limiting | Use authenticated requests, cache aggressively, deduplicate in-flight requests |
| Large repos overwhelming the LLM | Filter tree by depth, truncate README, focus on key files only |
| Private repo access | Require user-provided GitHub token with appropriate scopes |
| LLM hallucination | Ground analysis strictly in file tree evidence; include confidence indicators |
| Cost at scale | Cache results, use efficient models, rate-limit per user |
| Sensitive code exposure | Process server-side only, never store full file contents, respect .gitignore |

---

## 9. Prompt to Build This in ZECT

> **Copy this prompt into ZECT Ask Mode or any AI assistant to start building the repo analysis feature:**

```
Build a Repository Analysis feature for the ZECT (Engineering Delivery Control Tower) Next.js application. This feature lets users paste a GitHub repository URL and get a comprehensive analysis that feeds into ZECT's 5-stage workflow (Ask > Plan > Build > Review > Deploy).

The feature needs:

1. A RepoInput component — accepts GitHub URLs or owner/repo format, validates input, shows example repos, and lets users choose an analysis scenario: Legacy Migration, New Project, or Existing Enhancement.

2. GitHub API integration (server-side) — four functions: getRepoMeta (description, language, stars, topics), getFileTree (recursive directory listing), getReadme (decoded content), and readFile (any specific file). Must handle main/master fallback, rate limiting, and authentication via GITHUB_TOKEN env var.

3. File tree formatter — converts GitHub's flat file array into ASCII directory tree format. Supports depth filtering and path scoping.

4. LLM integration via OpenRouter — assembles repo metadata + file tree + README into a structured message, sends to Gemini 2.5 Pro with scenario-specific system prompts, returns structured analysis with a generated Ask Mode prompt.

5. Three scenario-specific system prompts that produce: current state assessment, risk analysis, recommended strategy, and a ready-to-use Ask Mode prompt.

6. API route: POST /api/analyze-repo with caching and in-flight deduplication.

7. Results display component showing the analysis, generated prompts, and option to create a ZECT project from the analysis.

Tech stack: Next.js 15 App Router, TypeScript, Tailwind CSS. No external UI libraries. Keep it consistent with the existing ZECT enterprise design (dark sidebar, light content area).

Start with the mock/prototype version using sample data, then wire up the real APIs.
```

---

## 10. Summary

The repo analysis pattern is a powerful capability that transforms ZECT from a workflow tool into an **intelligent project bootstrapper**. By analyzing any GitHub repository — legacy, new, or existing — ZECT can:

- **Auto-generate migration briefs** for legacy modernization projects
- **Pre-populate project specifications** when creating new projects from reference repos
- **Provide architectural context** for enhancement work on existing codebases
- **Feed directly into the 5-stage workflow** with structured, evidence-based inputs

This eliminates the cold-start problem where teams spend days understanding a codebase before they can even write the first Ask Mode requirements. With repo analysis, they paste a URL and get a structured brief in seconds.
