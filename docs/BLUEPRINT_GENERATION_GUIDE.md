# Blueprint Generation Guide

> Step-by-step guide for generating AI-ready vibe-coding prompts from GitHub repositories.

## Overview

The Blueprint Generator is ZECT's flagship feature. It analyzes one or more GitHub repositories and synthesizes a single copy-paste prompt that you can paste into any AI coding tool (Cursor, Claude Code, Codex, Windsurf, etc.) to recreate or extend the project from scratch.

## How It Works

```
GitHub Repo(s) → ZECT Analysis → Structured Prompt → Copy to Clipboard → Paste into AI Tool
```

1. ZECT fetches repo metadata, file structure, README, and dependencies via GitHub API
2. Synthesizes everything into a structured markdown prompt
3. You copy it to your clipboard with one click
4. Paste into any AI tool to start vibe-coding

## Two Modes

| Mode | Use Case | Scope |
|------|----------|-------|
| **Standard** | Full project recreation or understanding | Entire repo(s) |
| **Focused** | Specific feature or layer analysis | Single repo, scoped to a focus area |

Both modes are available from the Blueprint page via tabs.

## Prerequisites

1. ZECT backend running (`poetry run uvicorn app.main:app --port 8000`)
2. ZECT frontend running (`npm run dev`)
3. (Recommended) GitHub PAT configured in Settings for higher rate limits

## Step-by-Step

### Step 1: Navigate to Blueprint Generator

Click **Blueprint** in the sidebar, or go to `/blueprint`.

### Step 2: Choose a Mode

Select **Standard** or **Focused** from the mode tabs at the top.

### Step 3 (Standard): Add Repositories

Enter the Owner and Repository name. For multi-repo blueprints, click **Add Another Repo**.

**Example — Single repo:**

| Owner | Repo |
|-------|------|
| KarthikKaruppasamy880 | ZECT |

**Example — Multi-repo system:**

| Owner | Repo |
|-------|------|
| KarthikKaruppasamy880 | ZECT |
| KarthikKaruppasamy880 | ZEF |

### Step 4 (Standard): Click Generate Blueprint

ZECT analyzes each repo and builds the prompt. This takes a few seconds per repo.

### Step 3 (Focused): Enter Focus Details

| Field | Required | Example |
|-------|----------|--------|
| Owner | Yes | `KarthikKaruppasamy880` |
| Repository | Yes | `ZECT` |
| Focus Area | Yes | `authentication`, `API layer`, `database` |
| Goal | No | `understand and replicate` (default) |

Click **Generate Focused Blueprint**.

### Step 5: Review the Blueprint

The generated blueprint includes:

| Section | Content |
|---------|---------|
| Header | "Project Blueprint — AI-Ready Prompt" |
| Per-repo metadata | Description, language, default branch |
| Architecture notes | Detected patterns (src/, Docker, CI/CD, tests) |
| Dependencies | Full dependency list by package manager |
| File structure | Top 60 files from the repo tree |
| README excerpt | First 3,000 characters |
| AI instructions | Step-by-step instructions for the AI tool |

### Step 6: Copy to Clipboard

Click **Copy to Clipboard**. The button turns green with "Copied!" confirmation.

### Step 7: Paste into Your AI Tool

Open your preferred AI coding tool and paste the blueprint:

- **Cursor** — Open a new chat, paste the blueprint, add your request
- **Claude Code** — Start a new conversation, paste, then describe what you want to build
- **Codex** — Use as a system prompt or paste into the context
- **Windsurf** — Paste into the AI assistant chat

### Step 8: Start Vibe-Coding

The AI tool now has full context about your project's structure, dependencies, and conventions. Ask it to:

- Recreate the project from scratch
- Add new features following existing patterns
- Refactor or upgrade specific components
- Write tests matching the project's testing framework

## API Endpoints

### Standard Mode

```
POST /api/analysis/blueprint
Content-Type: application/json

{
  "repos": [
    { "owner": "KarthikKaruppasamy880", "repo": "ZECT" }
  ]
}
```

Response:

```json
{
  "prompt": "I want to build a project like...",
  "token_estimate": 4500,
  "repos_analyzed": 1
}
```

### Focused Mode

```
POST /api/analysis/blueprint/focused
Content-Type: application/json

{
  "owner": "KarthikKaruppasamy880",
  "repo": "ZECT",
  "focus_area": "authentication",
  "goal": "understand and replicate"
}
```

Response:

```json
{
  "prompt": "I want to understand and replicate the authentication part of...",
  "token_estimate": 2100,
  "focus_area": "authentication",
  "repo_name": "KarthikKaruppasamy880/ZECT"
}
```

## Token Estimates

The blueprint shows an approximate token count. Use this to check if it fits within your AI tool's context window:

| AI Tool | Context Window | Max Blueprint Size |
|---------|---------------|-------------------|
| Cursor | 128K tokens | ~500K chars |
| Claude Code | 200K tokens | ~800K chars |
| Codex | 128K tokens | ~500K chars |
| Windsurf | 128K tokens | ~500K chars |

A typical single-repo blueprint is 2,000-10,000 tokens.

## Tips

- For very large repos, the file tree is capped at 80 items in the blueprint
- Use Focused mode to scope analysis to a specific feature — ideal for large repos
- Multi-repo blueprints are larger — check the token estimate before pasting
- Add your own instructions after pasting the blueprint for best results
- The blueprint is AI-tool-agnostic — works with any tool that accepts text input
- For legacy migration, combine the blueprint with specific migration instructions

## Use Cases

### New Project from Template

Analyze an existing well-structured repo, generate a blueprint, and ask the AI to create a new project following the same patterns but with different business logic.

### Legacy Migration

Analyze the legacy repo, generate a blueprint, then ask the AI to modernize the architecture while preserving the business logic.

### Feature Enhancement

Analyze the current repo, generate a blueprint for context, then ask the AI to add specific features following existing conventions.

### Cross-Repo Integration

Analyze multiple repos, generate a combined blueprint, then ask the AI to build an integration layer connecting them.
