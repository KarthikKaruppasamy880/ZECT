# ZECT AI-Agnostic Usage Guide

> Use ZECT-generated blueprints and analysis with **any** AI coding tool — no vendor lock-in.

## Core Principle

ZECT generates **plain-text prompts** from GitHub repository analysis. These prompts are tool-agnostic — they work with any AI assistant that accepts text input. No plugins, no integrations, no API keys for the AI tool itself.

## How It Works

```
GitHub Repo → ZECT Analysis → Plain-Text Prompt → Copy → Paste into ANY AI Tool
```

ZECT uses the **GitHub API** to fetch repository metadata, file structure, README, and dependencies. It then synthesizes this into a structured prompt you can copy to your clipboard and paste anywhere.

---

## Using ZECT With Each AI Tool

### Cursor

1. Generate a blueprint in ZECT (Standard or Focused mode)
2. Click **Copy to Clipboard**
3. Open Cursor, press `Cmd+L` (or `Ctrl+L`) to open the AI chat
4. Paste the blueprint
5. Add your request: _"Recreate this project"_ or _"Add a new auth module following these patterns"_
6. Cursor generates code with full project context

**Best for:** New feature development, code generation with existing patterns

### Claude Code

1. Generate a blueprint in ZECT
2. Click **Copy to Clipboard**
3. Open Claude Code terminal
4. Paste the blueprint as the initial prompt
5. Claude Code creates files, installs dependencies, and implements the project

**Best for:** Full project scaffolding, complex refactoring, architecture decisions

### OpenAI Codex / ChatGPT

1. Generate a blueprint in ZECT
2. Click **Copy to Clipboard**
3. Open ChatGPT or Codex
4. Paste the blueprint
5. Ask: _"Build this project step by step"_ or _"Explain the architecture and suggest improvements"_

**Best for:** Understanding codebases, getting architecture explanations, learning patterns

### Windsurf

1. Generate a blueprint in ZECT
2. Click **Copy to Clipboard**
3. Open Windsurf's AI assistant (Cascade)
4. Paste the blueprint
5. Ask Windsurf to implement, extend, or analyze the project

**Best for:** Collaborative coding, real-time code generation

### Devin

1. Generate a blueprint in ZECT
2. Click **Copy to Clipboard**
3. Start a new Devin session
4. Paste the blueprint as the task description
5. Devin autonomously builds the project, runs tests, and creates PRs

**Best for:** Autonomous project creation, end-to-end implementation without manual coding

### Any Other AI Tool

The blueprint is plain markdown text. It works with:
- **Amazon Q Developer** — paste into the chat
- **GitHub Copilot Chat** — paste into the chat panel
- **Cody (Sourcegraph)** — paste as context
- **JetBrains AI** — paste into the AI assistant
- **Any LLM API** — send as the user message with a system prompt

---

## Blueprint Modes

### Standard Mode

Generates a comprehensive prompt covering the **entire repository**:
- Full file structure
- All dependencies
- Architecture notes
- README excerpt
- Conversational instructions for the AI

**Use when:** You want to recreate or understand the full project.

### Focused Mode

Generates a prompt **scoped to a specific feature or layer**:
- Files related to the focus area
- Full tree for context
- Architecture notes
- Goal-specific instructions

**Use when:** You want to understand or replicate a specific part (e.g., auth, API, database).

**Focus area examples:**
- `authentication` — login, session, token management
- `API layer` — routes, controllers, middleware
- `database` — models, migrations, queries
- `CI/CD` — GitHub Actions, Docker, deployment
- `testing` — test files, test utilities, coverage

---

## Repo Analysis (Without Blueprint)

ZECT also provides raw repo analysis (without synthesizing into a prompt). Use this when you want to:
- Inspect a repo's structure before deciding what to build
- Compare multiple repos' architectures
- Generate documentation for a repo

### Single Repo Analysis

Navigate to **Repo Analysis** → enter owner/repo → click **Analyze**. Shows:
- Metadata (stars, forks, language, branch)
- Architecture notes (detected patterns)
- Dependencies (by package manager)
- File structure (up to 300 files)
- README excerpt

### Multi-Repo Analysis

Add multiple repos and analyze them together. Useful for understanding how multiple services in a system relate to each other.

---

## Documentation Generator

ZECT can generate 6 documentation sections from any repo:

| Section | What It Generates |
|---------|-------------------|
| Overview | Description, language, stats |
| Architecture | Patterns, key directories |
| API Reference | Detected route/controller files |
| Setup Guide | Prerequisites, install commands |
| Testing | Test files, run commands |
| Deployment | Docker, CI/CD configuration |

Each section can be copied individually or all at once.

---

## API Key Requirements

| Feature | GitHub Token Required? | OpenAI Key Required? |
|---------|----------------------|---------------------|
| Repo Analysis | Recommended (increases rate limit) | No |
| Blueprint Generator (Standard) | Recommended | No |
| Blueprint Generator (Focused) | Recommended | No |
| Blueprint Enhancement (AI) | Recommended | **Yes** |
| Documentation Generator | Recommended | No |
| Ask Mode | No | **Yes** |
| Plan Mode | No | **Yes** |

**Blueprint generation is AI-agnostic** — ZECT generates prompts locally from GitHub data. The AI processing happens in whatever tool you paste the prompt into.

**AI-powered features** (Ask Mode, Plan Mode, Blueprint Enhancement) require an OpenAI API key configured in Settings. These features use GPT-4o-mini.

**GitHub Token:** Optional but recommended. Without it, you get 60 API requests/hour. With it, you get 5,000/hour. Configure in **Settings** → **GitHub API Key**.

### Token Usage Tracking

All token-consuming operations are tracked in the database with full audit trail:
- Total API calls, tokens consumed, and estimated cost visible on the **Dashboard**
- Breakdown by feature (Ask Mode, Plan Mode, Blueprint, Doc Gen, Repo Analysis)
- Breakdown by model (gpt-4o-mini, github-api)
- Recent activity log with per-operation details

---

## Tips for Best Results

1. **Add context after pasting** — After pasting the blueprint, add your specific request (e.g., _"Add a user profile page following the existing patterns"_)
2. **Use Focused mode for large repos** — Standard blueprints for very large repos may hit context limits. Use Focused mode to scope to what you need.
3. **Multi-repo for microservices** — When working with a microservice architecture, generate a multi-repo blueprint to give the AI full system context.
4. **Token estimates help** — Check the token estimate shown after generation to make sure it fits within your AI tool's context window.
5. **Iterate** — Generate a blueprint, paste it, build something, then generate again with the updated repo for the next iteration.
