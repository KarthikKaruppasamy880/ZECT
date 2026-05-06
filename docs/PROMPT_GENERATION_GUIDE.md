# ZECT Prompt Generation Guide

> How ZECT generates AI-ready prompts from GitHub repositories — Standard and Focused modes.

---

## Overview

ZECT's core value proposition is turning any GitHub repository into a **single copy-paste prompt** that you can feed into any AI coding tool to recreate, extend, or understand the project. This guide explains exactly how that process works.

---

## Two Generation Modes

### 1. Standard Mode (Multi-Repo Blueprint)

**Purpose:** Analyze one or more repos and generate a comprehensive prompt covering everything.

**API Endpoint:** `POST /api/analysis/blueprint`

**Input:**
```json
{
  "repos": [
    { "owner": "facebook", "repo": "react" },
    { "owner": "vercel", "repo": "next.js" }
  ]
}
```

**Output:**
```json
{
  "prompt": "I want to build a project like facebook/react — ...",
  "token_estimate": 4500,
  "repos_analyzed": 2
}
```

### 2. Focused Mode (Single Feature/Layer)

**Purpose:** Generate a prompt scoped to a specific feature or architectural layer of a single repo.

**API Endpoint:** `POST /api/analysis/blueprint/focused`

**Input:**
```json
{
  "owner": "facebook",
  "repo": "react",
  "focus_area": "authentication",
  "goal": "understand and replicate"
}
```

**Output:**
```json
{
  "prompt": "I want to understand and replicate the authentication part of ...",
  "token_estimate": 2100,
  "focus_area": "authentication",
  "repo_name": "facebook/react"
}
```

---

## Standard Mode — Step-by-Step Process

### Step 1: Repository Analysis

For each repo in the request, ZECT calls `_analyze_repo()` which:

1. **Fetches repo metadata** via GitHub API (`PyGithub`)
   - Full name, description, primary language, stars, forks, open issues, default branch

2. **Fetches the file tree** (up to 300 files)
   ```python
   tree = repo.get_git_tree(repo.default_branch, recursive=True)
   for item in tree.tree[:300]:
       tree_items.append(item.path)
   ```

3. **Reads the README** (first 8,000 characters)
   ```python
   content = repo.get_readme()
   readme = content.decoded_content.decode("utf-8")[:8000]
   ```

4. **Detects dependencies** from well-known files:
   | File | Package Manager |
   |------|----------------|
   | `package.json` | npm (parses `dependencies` + `devDependencies` keys) |
   | `requirements.txt` | pip |
   | `pyproject.toml` | poetry/pip |
   | `Cargo.toml` | cargo |
   | `go.mod` | go |
   | `Gemfile` | bundler |
   | `pom.xml` | maven |
   | `build.gradle` | gradle |

5. **Infers architecture notes** from the file tree:
   - `src/` present -> "Source code in src/ directory"
   - `app/` present -> "Application code in app/ directory"
   - `test` anywhere -> "Test files detected"
   - `docker` anywhere -> "Docker configuration present"
   - `.github/workflows` -> "GitHub Actions CI/CD workflows configured"
   - `api` in top 50 paths -> "API layer detected"
   - Primary language from GitHub metadata

### Step 2: Prompt Synthesis (`_build_prompt`)

The `_build_prompt()` function takes the analysis results and generates a conversational, outcome-focused prompt:

#### Single Repo Template:
```
I want to build a project like {full_name} — {description}, built with {language}.
Here is everything you need to know about the original repository so you can
recreate it from scratch with the same architecture, patterns, and quality.

## Repository: {full_name}
**Description:** {description}
**Primary Language:** {language}
**Default Branch:** {default_branch}
**Stars:** {stars} | **Forks:** {forks}

### Architecture Notes
- {note_1}
- {note_2}
...

### Dependencies
**npm:** react, typescript, vite, ...

### File Structure
```
src/App.tsx
src/components/...
...
```

### README (excerpt)
```markdown
{first 4000 chars of README}
```

---

## What I Need You To Do

Using the repository analysis above:
1. Recreate the full project structure following the file layout shown
2. Install all listed dependencies using the correct package manager
3. Implement the core architecture as described in the architecture notes
4. Follow the patterns and conventions visible in the file structure
5. Ensure the project builds, lints cleanly, and all tests pass
6. Match the README description, goals, and feature set
7. Use production-quality code — proper error handling, types, and documentation

Start with the project scaffold, then implement each module.
```

#### Multi-Repo Template:
When multiple repos are provided, the prompt combines them:
```
I want to build a project that combines patterns from these repositories:
{repo_1}, {repo_2}. Below is a detailed analysis of each repo.
Use this context to create a unified project that incorporates the best
architecture and patterns from all of them.
```

### Step 3: Token Estimation

Token count is estimated as `len(prompt) // 4` (rough character-to-token ratio).

---

## Focused Mode — Step-by-Step Process

### Step 1: Repository Analysis

Same as Standard Mode — full `_analyze_repo()` is called.

### Step 2: File Filtering

The focus area keywords are used to filter the file tree:

```python
focus_lower = focus_area.lower()
relevant_files = [
    p for p in analysis.tree
    if any(kw in p.lower() for kw in focus_lower.split())
]
```

For example, `focus_area="authentication"` would match:
- `src/auth/login.tsx`
- `backend/authentication/middleware.py`
- `tests/test_auth.py`

### Step 3: Focused Prompt Synthesis (`_build_focused_prompt`)

```
I want to {goal} the {focus_area} part of the {full_name} repository.
Here is the relevant context from the repo so you can help me.

## Repository: {full_name}
...

### Architecture Context
- {note_1}
...

### Files Related to "{focus_area}"
```
src/auth/login.tsx
src/auth/middleware.ts
...
```

### Full File Structure (for context)
```
{first 60 files}
```

### Dependencies
...

### README (excerpt)
...

---

## Focus: {focus_area}

My goal is to **{goal}** the {focus_area} functionality from this repo.
Please:
1. Explain how the {focus_area} is implemented in this codebase
2. Identify the key files and patterns used
3. Provide a step-by-step plan to implement this in my project
4. Include any gotchas, edge cases, or best practices to follow

Be specific and reference the actual file structure shown above.
```

---

## AI Enhancement (Optional)

After generating a blueprint, users can click **"Enhance with AI"** to improve the prompt using OpenAI's GPT-4o-mini:

**API Endpoint:** `POST /api/llm/enhance-blueprint`

The system prompt instructs the LLM to:
- Improve clarity and organization
- Add implementation priorities
- Suggest architecture patterns
- Optimize for maximum AI comprehension
- Keep the output as a single self-contained prompt

---

## Token Tracking

Every prompt generation operation is tracked in the database:

| Operation | Feature Tag | Token Calculation |
|-----------|------------|-------------------|
| Repo analysis | `repo_analysis` | `len(tree) + len(readme) // 4` |
| Standard blueprint | `blueprint` | `len(prompt) // 4` |
| Focused blueprint | `blueprint` | `len(prompt) // 4` |
| Doc generation | `doc_gen` | `sum(len(section) // 4)` |
| AI enhancement | `blueprint` | Actual OpenAI token count |

View token usage in:
- **Dashboard** -> Token Usage Control panel
- **Settings** -> Token Usage -> View Log

---

## Using Generated Prompts

### With Any AI Coding Tool
1. Generate blueprint in ZECT
2. Copy the prompt
3. Open your preferred AI coding tool
4. Paste the prompt into the AI chat, composer, or task input
5. The AI tool will scaffold and implement the project

The blueprint is plain text and works with any AI tool — IDE-based assistants, terminal-based tools, web-based platforms, or autonomous AI agents.

---

## Best Practices

1. **Start with Standard Mode** for full project understanding
2. **Use Focused Mode** when you only need a specific feature
3. **Enhance with AI** for production-grade prompts
4. **Combine with ZEF templates** for structured analysis workflows
5. **Monitor token usage** in the Dashboard to control costs
6. **Use a GitHub token** in Settings for higher rate limits (5000/hr vs 60/hr)
