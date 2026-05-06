# Session & Repository Details Report

## Session Referenced
- **Session ID**: `d11726fe90e543e79f84b5256b1a1637`
- **Note**: This session built the Focused Blueprint Mode, LLM integration, and documentation (PRs #6 and #7).

---

## Repository: KarthikKaruppasamy880/ZEF
- **URL**: https://github.com/KarthikKaruppasamy880/ZEF
- **Visibility**: Private
- **Stars**: 0 | **Forks**: 0
- **Description**: "Zinnia Engineering Foundation"
- **License**: MIT
- **Contributors**: 1 (KarthikKaruppasamy880)

### What It Is
**ZEF (Zinnia Engineering Foundation)** — A reusable internal engineering foundation that helps engineers work faster and more consistently across new and existing projects — with or without AI-assisted development tools.

### Philosophy
> "Context survives tool changes. Workflow survives team changes."

### Core Components
1. **Context Management** — file-based system (`docs/context/pointers.md` as single entry point) so any tool can resume any project
2. **Workflow Model** — 5-phase model: Orient -> Plan -> Execute -> Verify -> Close
3. **Playbooks** (9 total) — step-by-step procedures for recurring tasks:
   - Bug Fix, Feature Build, Code Review, Incident Response, Project Setup, Refactor
   - **Legacy Migration**, **Repo Analysis**, **Greenfield from Reference** (new)
4. **Skills** (7 total) — reusable capability modules:
   - Context Manager, Session Resume, Task Planner, Test-Driven Dev, PR Workflow, Token Efficiency
   - **Repo Analyzer** (new)
5. **Templates** — starter files for projects, decisions, sessions, tasks, and **prompt templates for repo analysis**
6. **Tool Adapters** (5) — adapters for popular AI coding tools

### Supported Tools
| Tool | Adapter | Status |
|------|---------|--------|
| IDE-based AI tools | `adapters/ide/` | Supported |
| Terminal-based AI tools | `adapters/terminal/` | Supported |
| Web-based AI platforms | `adapters/web/` | Supported |
| Autonomous AI agents | `adapters/agent/` | Supported |
| No AI tool | Core docs only | Supported |

### Repository Structure
```
ZEF/
├── README.md
├── AGENTS.md                    # AI agent operating contract
├── LICENSE (MIT)
├── docs/
│   ├── context/pointers.md      # Context entry point
│   ├── workflow/                 # Workflow model, session lifecycle, context mgmt
│   ├── guides/                  # Getting started, integration guides, cheat sheet, FAQ, audit report
│   └── examples/                # Ecommerce, API service, Component library examples
├── playbooks/                   # 9 playbooks (bug-fix, feature-build, etc.)
├── skills/                      # 7 skills (context-manager, repo-analyzer, etc.)
├── templates/
│   ├── project/                 # Pointers, domain-context, session-log, backlog
│   ├── workflow/                # Task-brief, decision-record, post-mortem, repo-analysis-brief, migration-plan
│   └── prompts/                 # 4 prompt templates for repo analysis
└── adapters/                    # Tool adapters for AI coding tools
```

### Repo Analysis Workflow (Key Feature)
ZEF includes ready-to-use **prompt templates** that you copy, fill in, and paste into any AI tool:

1. **Pick a template** from `templates/prompts/`:
   - `analyze-legacy-repo.md` — Legacy migration
   - `analyze-for-new-project.md` — New project from reference
   - `analyze-for-enhancement.md` — Enhance existing
   - `multi-repo-orchestration.md` — Multi-repo coordination
2. **Fill in brackets** (`[PASTE_REPO_URL_HERE]`, `[DESCRIBE_REASON]`, etc.)
3. **Paste into any AI coding tool**
4. **Review output** (tech stack, architecture, risks, implementation plan)
5. **Fill in the brief** (`templates/workflow/repo-analysis-brief.md`)
6. **Follow the playbook** for next steps

### ZECT Integration with ZEF
ZECT uses ZEF for:
- Workflow standards (5-phase delivery model)
- Playbook-driven development patterns
- Context management across AI sessions
- Prompt templates for repo analysis and enhancement

### Latest Activity
- 17 commits, 5 branches, 1 open PR
- Latest commit: `28e406f` — "Merge pull request #6 from KarthikKaruppasamy880/develop" (Apr 22, 2026)
