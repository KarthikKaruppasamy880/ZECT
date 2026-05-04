# ZECT — Skills Registry

## Overview

The Skills Registry is the central catalog of all available skills in ZECT. It defines metadata, inputs, outputs, triggers, and status for each registered skill.

---

## Registry Format

```yaml
skills:
  - id: repo-analysis
    name: Repository Analysis
    version: 1.0.0
    category: analysis
    type: code-backed
    trigger: manual
    description: Analyze a GitHub repository structure, dependencies, and architecture
    inputs:
      - name: owner
        type: string
        required: true
      - name: repo
        type: string
        required: true
    outputs:
      - name: analysis_result
        type: object
        description: Structured repo analysis data
    endpoint: /api/repo-analysis/analyze
    status: active

  - id: multi-repo-analysis
    name: Multi-Repo Analysis
    version: 1.0.0
    category: analysis
    type: code-backed
    trigger: manual
    description: Analyze multiple repositories and identify cross-repo patterns
    inputs:
      - name: repos
        type: array
        required: true
        items: { owner: string, repo: string }
    outputs:
      - name: analysis_results
        type: array
      - name: relationships
        type: object
    endpoint: /api/repo-analysis/multi
    status: active

  - id: blueprint-standard
    name: Standard Blueprint Generation
    version: 1.0.0
    category: blueprint
    type: hybrid
    trigger: manual
    description: Generate a full project blueprint prompt from repo analysis
    inputs:
      - name: repos
        type: array
        required: true
    outputs:
      - name: blueprint
        type: string
        description: Copy-paste ready prompt for AI coding tools
    endpoint: /api/llm/blueprint
    status: active

  - id: blueprint-focused
    name: Focused Blueprint Generation
    version: 1.0.0
    category: blueprint
    type: hybrid
    trigger: manual
    description: Generate a focused blueprint for a specific feature/layer
    inputs:
      - name: repos
        type: array
        required: true
      - name: focus_area
        type: string
        required: true
        description: "e.g., auth, database, API, frontend"
    outputs:
      - name: blueprint
        type: string
    endpoint: /api/llm/blueprint
    status: active

  - id: code-review-pr
    name: PR Code Review
    version: 1.0.0
    category: review
    type: code-backed
    trigger: manual
    description: AI-powered code review of a pull request
    inputs:
      - name: owner
        type: string
        required: true
      - name: repo
        type: string
        required: true
      - name: pr_number
        type: integer
        required: true
    outputs:
      - name: findings
        type: array
        description: List of issues found (bugs, security, performance)
      - name: fix_prompt
        type: string
        description: Ready-to-paste fix prompt for AI tools
    endpoint: /api/code-review/pr
    status: active

  - id: code-review-snippet
    name: Code Snippet Review
    version: 1.0.0
    category: review
    type: code-backed
    trigger: manual
    description: Review a code snippet for issues
    inputs:
      - name: code
        type: string
        required: true
      - name: language
        type: string
        required: false
    outputs:
      - name: findings
        type: array
    endpoint: /api/code-review/snippet
    status: active

  - id: doc-generation
    name: Documentation Generation
    version: 1.0.0
    category: documentation
    type: hybrid
    trigger: manual
    description: Generate granular documentation for a repository
    inputs:
      - name: owner
        type: string
        required: true
      - name: repo
        type: string
        required: true
      - name: sections
        type: array
        required: true
        description: "overview, architecture, api, setup, testing, deployment"
    outputs:
      - name: documentation
        type: object
        description: Generated docs per section
    endpoint: /api/llm/docs
    status: active

  - id: ask-mode
    name: Ask Mode
    version: 1.0.0
    category: workflow
    type: code-backed
    trigger: manual
    description: Conversational AI assistant for engineering questions
    inputs:
      - name: question
        type: string
        required: true
      - name: repo_context
        type: array
        required: false
    outputs:
      - name: answer
        type: string
    endpoint: /api/llm/ask
    status: active

  - id: plan-mode
    name: Plan Mode
    version: 1.0.0
    category: workflow
    type: code-backed
    trigger: manual
    description: Generate phased engineering plans
    inputs:
      - name: description
        type: string
        required: true
      - name: constraints
        type: object
        required: false
    outputs:
      - name: plan
        type: object
        description: Phased plan with milestones
    endpoint: /api/llm/plan
    status: active

  - id: token-analysis
    name: Token Usage Analysis
    version: 1.0.0
    category: analytics
    type: code-backed
    trigger: manual | scheduled
    description: Analyze token usage patterns and suggest optimizations
    inputs:
      - name: time_range
        type: string
        required: false
        default: "7d"
    outputs:
      - name: usage_report
        type: object
    endpoint: /api/analytics/token-dashboard
    status: active
```

---

## Registry API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/skills` | List all registered skills |
| GET | `/api/skills/{id}` | Get skill details |
| POST | `/api/skills/{id}/invoke` | Trigger a skill |
| GET | `/api/skills/{id}/status` | Check skill execution status |

---

## Adding a New Skill

1. Create `SKILL.md` in `.agents/skills/{skill-name}/`
2. Add entry to the registry YAML
3. Implement backend endpoint (if code-backed)
4. Add frontend UI trigger (if manual)
5. Test the skill end-to-end
6. Set status to `active`
