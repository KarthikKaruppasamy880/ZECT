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

### Any AI Coding Tool

1. Generate a blueprint in ZECT (Standard or Focused mode)
2. Click **Copy to Clipboard**
3. Open your preferred AI coding tool
4. Paste the blueprint into the AI assistant's chat or prompt input
5. Add your request: _"Recreate this project"_ or _"Add a new auth module following these patterns"_
6. The AI tool generates code with full project context

The blueprint is plain markdown text. It works with any AI tool that accepts text input:
- **IDE-based AI assistants** — paste into the AI chat panel
- **Terminal-based AI tools** — paste as the initial prompt
- **Web-based AI platforms** — paste into the chat interface
- **Autonomous AI agents** — paste as the task description
- **Any LLM API** — send as the user message with a system prompt

**Best for:** Code generation, project scaffolding, architecture decisions, understanding codebases

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
