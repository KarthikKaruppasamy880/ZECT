# How ZEF is Used for ZECT

Guide explaining how the Zinnia Engineering Foundation (ZEF) repository supports and accelerates ZECT development.

---

## What is ZEF?

ZEF (Zinnia Engineering Foundation) is a shared repository containing:

- **Coding standards** and conventions for all Zinnia engineering teams
- **Legacy migration playbooks** for upgrading existing systems
- **Repo analysis prompt templates** for AI-assisted code understanding
- **Project templates** for starting new projects with best practices
- **Security guidelines** for credential management and compliance

**Repository:** https://github.com/KarthikKaruppasamy880/ZEF

---

## How ZEF Powers ZECT

### 1. Repo Analysis Prompt Templates

ZEF provides ready-to-use prompt templates in `templates/prompts/` that ZECT's Blueprint Generator uses as a pattern:

| ZEF Template | ZECT Feature |
|---|---|
| `analyze-for-enhancement.md` | Blueprint Generator — analyzes repo structure |
| `analyze-for-migration.md` | Repo Analysis — understands legacy systems |
| `analyze-for-security.md` | Security audit context in blueprints |

**How to use:**
1. Open the ZEF template from `templates/prompts/`
2. Fill in the `[REPO_URL]`, `[TECH_STACK]`, and other bracketed placeholders
3. Paste into any AI coding tool for instant analysis

### 2. Coding Standards

ZEF's `standards/` directory defines the conventions ZECT follows:

- **TypeScript conventions** — React component patterns, naming, imports
- **Python conventions** — FastAPI router structure, Pydantic models
- **API design** — REST endpoint naming, error response format
- **Git workflow** — Branch naming, commit messages, PR process

### 3. Legacy Migration Playbooks

When ZECT analyzes a legacy repository, it follows ZEF's migration playbooks:

- `playbooks/legacy-to-modern/` — Step-by-step migration guides
- `playbooks/assessment/` — How to evaluate a legacy codebase
- `playbooks/incremental-upgrade/` — Gradual modernization strategies

### 4. Security Guidelines

ZEF's security guidelines are applied in ZECT:

- API keys stored in environment variables, never in code
- Token-based authentication with session management
- Constant-time password comparison to prevent timing attacks
- CORS configuration for production deployments

---

## Using ZEF to Build New Features in ZECT

### Step 1: Find the Right Template

```bash
# Clone ZEF
git clone https://github.com/KarthikKaruppasamy880/ZEF.git

# Browse templates
ls ZEF/templates/prompts/
```

### Step 2: Fill in the Template

Open the template that matches your task. For example, to add a new ZECT feature:

```markdown
# From: templates/prompts/analyze-for-enhancement.md

## Repository: https://github.com/KarthikKaruppasamy880/ZECT
## Goal: Add real-time notification system
## Tech Stack: React, FastAPI, SQLite
## Constraints: Must work with existing auth system
```

### Step 3: Generate the Blueprint

Paste the filled template into ZECT's Blueprint Generator or directly into an AI coding assistant.

### Step 4: Follow ZEF Standards

When implementing, reference ZEF's coding standards:
- `standards/typescript/` for frontend code
- `standards/python/` for backend code
- `standards/api-design/` for new endpoints

---

## Using ZEF for Legacy Project Migration

If you're migrating a legacy project and want to use ZECT to assist:

1. **Analyze the legacy repo** using ZECT's Repo Analysis page
2. **Generate a migration blueprint** using ZECT's Blueprint Generator
3. **Follow ZEF's migration playbook** from `playbooks/legacy-to-modern/`
4. **Use ZECT's Plan Mode** to create a phased migration plan
5. **Track progress** in ZECT's Projects page

---

## ZEF Repository Structure

```
ZEF/
├── README.md                    # Getting started guide
├── docs/
│   ├── guides/                  # Integration guides
│   │   ├── getting-started.md
│   │   ├── integrate-new-project.md
│   │   └── integrate-existing-project.md
│   └── reference/               # Reference documentation
├── standards/                   # Coding standards
│   ├── typescript/
│   ├── python/
│   └── api-design/
├── templates/                   # Reusable templates
│   ├── prompts/                 # AI prompt templates
│   ├── projects/                # Project scaffolds
│   └── workflows/               # CI/CD templates
├── playbooks/                   # Step-by-step guides
│   ├── legacy-to-modern/
│   ├── assessment/
│   └── incremental-upgrade/
└── skills/                      # Automation skills
    └── repo-analysis/
```

---

## Quick Reference

| I want to... | Use this ZEF resource |
|---|---|
| Analyze a repo for migration | `templates/prompts/analyze-for-migration.md` |
| Start a new project | `docs/guides/integrate-new-project.md` |
| Add ZEF to existing project | `docs/guides/integrate-existing-project.md` |
| Review coding standards | `standards/` directory |
| Plan a legacy migration | `playbooks/legacy-to-modern/` |
| Generate an AI prompt | `templates/prompts/` directory |
| Set up security properly | `standards/security/` |
