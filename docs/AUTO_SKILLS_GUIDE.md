# ZECT Auto Skills Guide

> How ZECT automatically detects, catalogs, and surfaces repository skills for engineering teams.

---

## What Are Auto Skills?

Auto Skills are ZECT's mechanism for automatically discovering the capabilities, patterns, and technical knowledge embedded in a repository. When you analyze a repo through ZECT, the system extracts actionable "skills" — reusable pieces of engineering knowledge that can be applied across projects.

---

## How Auto Skills Are Detected

### 1. Repository Analysis Phase

When you trigger a repo analysis (via the **Repo Analysis** page or **Blueprint Generator**), ZECT performs the following:

```
POST /api/analysis/repo
{
  "owner": "facebook",
  "repo": "react"
}
```

The backend (`backend/app/routers/repo_analysis.py`) then:

1. **Fetches the file tree** — Up to 300 files from the repo via GitHub API (`get_git_tree`)
2. **Reads the README** — First 8,000 characters of the repo's README
3. **Detects dependencies** — Scans well-known dependency files:
   - `package.json` (npm)
   - `requirements.txt` (pip)
   - `pyproject.toml` (poetry/pip)
   - `Cargo.toml` (cargo)
   - `go.mod` (go)
   - `Gemfile` (bundler)
   - `pom.xml` (maven)
   - `build.gradle` (gradle)
4. **Infers architecture notes** — Pattern-matching on the file tree:
   - `src/` directory detected -> "Source code in src/ directory"
   - `app/` directory detected -> "Application code in app/ directory"
   - `test` in any path -> "Test files detected"
   - `docker` in any path -> "Docker configuration present"
   - `.github/workflows` -> "GitHub Actions CI/CD workflows configured"
   - `api` in top paths -> "API layer detected"
   - Primary language from GitHub metadata

### 2. Skill Extraction Categories

| Skill Category | Source | Example |
|---------------|--------|---------|
| **Language & Framework** | GitHub metadata + dependencies | "React 18 with TypeScript" |
| **Build System** | Dependency files | "Vite build, npm package manager" |
| **Testing** | File tree patterns | "Jest unit tests, Cypress e2e" |
| **CI/CD** | `.github/workflows` | "GitHub Actions with lint + test + deploy" |
| **Containerization** | Dockerfile, docker-compose | "Docker multi-stage build" |
| **API Architecture** | File tree + dependencies | "FastAPI REST API with SQLAlchemy ORM" |
| **Authentication** | File patterns | "JWT auth with refresh tokens" |
| **Database** | Dependencies + config files | "PostgreSQL with Alembic migrations" |

### 3. Architecture Notes Generation

The architecture notes are auto-generated in the `_analyze_repo()` function:

```python
arch_notes: list[str] = []
if any("src/" in p for p in tree_items):
    arch_notes.append("Source code in src/ directory")
if any("app/" in p for p in tree_items):
    arch_notes.append("Application code in app/ directory")
if any("test" in p.lower() for p in tree_items):
    arch_notes.append("Test files detected")
if any("docker" in p.lower() for p in tree_items):
    arch_notes.append("Docker configuration present")
if any(".github/workflows" in p for p in tree_items):
    arch_notes.append("GitHub Actions CI/CD workflows configured")
if any("api" in p.lower() for p in tree_items[:50]):
    arch_notes.append("API layer detected")
if repo.language:
    arch_notes.append(f"Primary language: {repo.language}")
```

---

## How Skills Feed Into Blueprints

### Standard Blueprint (Multi-Repo)

Skills from multiple repos are merged into a single AI-ready prompt:

```
User Flow:
1. Add repos to Blueprint Generator
2. Click "Generate Blueprint"
3. ZECT analyzes each repo (extracting skills)
4. Skills are synthesized into a comprehensive prompt
5. Prompt includes: architecture, dependencies, file structure, README
```

The `_build_prompt()` function combines all extracted skills:
- Architecture patterns from each repo
- Dependency lists organized by package manager
- File structure (top 80 files per repo)
- README excerpts for context

### Focused Blueprint (Single Feature)

Skills are filtered to a specific area:

```
User Flow:
1. Enter owner/repo
2. Specify focus area (e.g., "authentication")
3. Optionally set a goal (e.g., "replicate")
4. Click "Generate Focused Blueprint"
5. ZECT filters the file tree to relevant files
6. Generates a focused prompt scoped to that skill
```

The `_build_focused_prompt()` function:
- Filters tree items matching the focus keywords
- Includes relevant files prominently
- Adds full tree for context
- Generates focused instructions

---

## How Skills Are Used in the Workflow

### 1. Ask Mode (Skill Discovery)
```
"How does authentication work in this codebase?"
-> Paste repo context into Ask Mode
-> ZECT AI explains the authentication skill from the repo
```

### 2. Plan Mode (Skill Application)
```
"Plan a new microservice using patterns from our existing API"
-> Paste repo analysis as context
-> ZECT AI creates a plan leveraging detected skills
```

### 3. Blueprint Enhancement
```
Generate blueprint -> Click "Enhance with AI"
-> ZECT AI improves the prompt with:
   - Implementation priorities
   - Architecture pattern suggestions
   - Best practices from detected skills
```

---

## ZEF Integration for Skills

ZECT integrates with ZEF (Zinnia Engineering Foundation) which provides structured skill definitions:

### ZEF Skills (7 Built-In)
| Skill | Purpose |
|-------|---------|
| Context Manager | Manage project context across sessions |
| Session Resume | Resume work from previous sessions |
| Task Planner | Break down work into actionable tasks |
| Test-Driven Dev | TDD workflow skill |
| PR Workflow | Pull request creation and review |
| Token Efficiency | Optimize token usage in AI interactions |
| Repo Analyzer | Analyze repository patterns and architecture |

### ZEF Playbooks (9 Built-In)
| Playbook | When to Use |
|----------|-------------|
| Bug Fix | Fixing defects |
| Feature Build | Building new features |
| Code Review | Reviewing pull requests |
| Incident Response | Handling production incidents |
| Project Setup | Initializing new projects |
| Refactor | Restructuring code |
| Legacy Migration | Migrating legacy systems |
| Repo Analysis | Analyzing repository patterns |
| Greenfield from Reference | Building new projects from reference repos |

---

## Token Tracking for Skills

Every skill extraction operation is tracked:

```python
_log_tokens("repo_analysis", len(tree_items) + (len(readme) // 4))
_log_tokens("blueprint_generation", token_estimate)
_log_tokens("focused_blueprint", token_estimate)
_log_tokens("doc_generation", total_tokens)
```

View your token usage in **Settings -> Token Usage -> View Log**.

---

## Adding Custom Skills

While ZECT auto-detects skills from repos, you can enhance detection by:

1. **Well-structured README** — Clear architecture descriptions help ZECT extract better skills
2. **Standard file conventions** — Using `src/`, `tests/`, `.github/workflows/` patterns
3. **Dependency files** — Keeping `package.json`, `pyproject.toml`, etc. up to date
4. **Architecture docs** — Adding `ARCHITECTURE.md` or `docs/` folder with design docs

The auto skills system improves with each repo analyzed — the more repos you analyze, the richer the skill catalog becomes for your organization.
