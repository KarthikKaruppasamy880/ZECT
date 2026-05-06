# ZECT — Feature Roadmap & Gap Analysis

## Executive Summary

| Aspect | ZECT (Current) | Industry-Leading AI Dev Tools |
|--------|----------------|-------------------------------|
| **Type** | Web-based engineering control tower | Autonomous AI software engineers |
| **Focus** | Project management + AI-assisted dev workflows | Fully autonomous code generation & execution |
| **AI Autonomy** | Human-in-the-loop (user drives each step) | Autonomous agent (plans & executes independently) |
| **Target Users** | Engineering managers + developers | Any developer needing AI pair programming |

---

## Feature-by-Feature Analysis

### 1. Code Generation & AI Assistance

| Feature | ZECT | Industry Standard | Status |
|---------|------|-------------------|--------|
| Ask questions about code | Yes (Ask Mode) | Yes | Comparable |
| Generate implementation plans | Yes (Plan Mode) | Yes (auto-plans) | ZECT requires manual input; autonomous tools auto-plan from task description |
| Generate code from plans | Yes (Build Phase) | Yes (autonomous) | **Gap**: Autonomous tools write full files; ZECT generates snippets user must apply |
| Code review | Yes (Review Phase) | Yes (inline PR review) | **Gap**: Some tools review actual PRs on GitHub; ZECT reviews pasted snippets |
| Auto-fix issues | Partial (Auto-Fix Loop UI) | Yes | **Gap**: Autonomous tools iterate on errors automatically |

### 2. Execution Environment

| Feature | ZECT | Industry Standard | Status |
|---------|------|-------------------|--------|
| Embedded terminal | Yes (App Runner) | Yes (full shell) | Built — App Runner with terminal, processes, live preview |
| Run commands | Yes (App Runner) | Yes | Built |
| Live browser preview | Yes (iframe preview) | Yes (full browser) | Built — iframe-based preview in App Runner |
| File system access | Yes (File Explorer) | Yes (full filesystem) | Built — file tree, search, new file creation |
| Git operations | Yes (Git Ops page) | Full git CLI | Built — status, commit, branches, log, create PR |
| Docker support | Docker Compose for deployment | Full Docker access | Comparable for deployment |

### 3. Project Management

| Feature | ZECT | Industry Standard | Status |
|---------|------|-------------------|--------|
| Multi-project dashboard | Yes (6+ projects) | No (session-based) | **ZECT advantage** |
| Stage tracking (Ask/Plan/Build/Review/Deploy) | Yes | No (linear flow) | **ZECT advantage** |
| Team analytics | Yes | No | **ZECT advantage** |
| Token budget controls | Yes (per-user) | Organization-level | **ZECT advantage** — more granular |
| Audit trail | Yes | Session logs | **ZECT advantage** |
| Multi-repo orchestration | Yes | Single repo per session | **ZECT advantage** |

### 4. Integrations

| Feature | ZECT | Industry Standard | Status |
|---------|------|-------------------|--------|
| GitHub integration | Yes (repos, PRs, commits) | Yes (full Git) | Comparable |
| Jira integration | Yes (configured) | Via MCP tools | Comparable |
| Slack integration | Yes (configured) | Yes (native) | Comparable |
| CI/CD monitoring | Yes (CI Monitor page) | Yes (waits for CI) | Built — workflow runs, job details |
| MCP protocol | Yes (6 servers) | Yes (native) | Comparable |

### 5. AI Model Support

| Feature | ZECT | Industry Standard | Status |
|---------|------|-------------------|--------|
| Model selection | Yes (per-feature) | Fixed (single model) | **ZECT advantage** — user chooses model |
| Free model support | Yes (OpenRouter) | No | **ZECT advantage** |
| Local LLM (Ollama) | Documented, configurable | No | **ZECT advantage** — potential |
| Token tracking | Yes (detailed per-call) | Organization dashboard | **ZECT advantage** |

### 6. Deployment & Distribution

| Feature | ZECT | Industry Standard | Status |
|---------|------|-------------------|--------|
| Web app | Yes | Yes | Comparable |
| Desktop app (.exe) | Not yet | No (web only) | Neither has it |
| Self-hosted | Yes (Docker Compose) | No (SaaS only) | **ZECT advantage** — runs on your infra |
| Multi-user | Yes (SSO-ready) | Yes (org accounts) | Comparable |

---

## Remaining Gaps to Close (Priority Order)

### Critical Gaps (High Impact)

1. **Autonomous Execution** — Autonomous AI tools can take a task like "fix this bug" and autonomously: read code, plan fix, write code, run tests, create PR. ZECT requires the user to drive each step manually.
   - **Effort**: 4-6 weeks
   - **How**: Build an "Agent Mode" that chains Ask → Plan → Build → Review → Deploy automatically

2. **Auto-Fix Loop** — Some tools run code, see errors, fix them, and retry. ZECT has the UI for this but needs full backend implementation.
   - **Effort**: 3-4 weeks
   - **How**: Build an error-detection → AI-fix → re-run cycle into Build Phase

3. **Session Persistence** — Leading tools maintain context across a full session (hours). ZECT is stateless per-page.
   - **Effort**: 2-3 weeks
   - **How**: Add a "Session" model that tracks conversation + generated artifacts across pages

### Important Gaps (Medium Impact)

4. **CI/CD Auto-Fix** — Some tools wait for CI checks and fix failures automatically. ZECT shows workflow runs but doesn't auto-fix.
   - **Effort**: 2 weeks
   - **How**: Poll GitHub Actions, detect failures, suggest fixes via AI

5. **Knowledge Base** — Some tools build knowledge from past sessions. ZECT doesn't learn from usage yet.
   - **Effort**: 3-4 weeks
   - **How**: Store successful patterns, reuse in future prompts

6. **Enhanced Playbooks** — Some tools have reusable playbooks for common tasks. ZECT has Skills (similar concept) that need auto-execution capability.
   - **Effort**: 1-2 weeks (enhance existing Skills)
   - **How**: Add "auto-run" capability to Skills so they execute multi-step workflows

---

## What ZECT Does Better

| ZECT Advantage | Why It Matters |
|---------------|----------------|
| **Multi-project dashboard** | Engineering managers see all projects at once, not one session at a time |
| **Stage-based workflow** | Clear progression through Ask → Plan → Build → Review → Deploy |
| **Token budget controls** | Per-user, per-team spending limits with alerts — critical for enterprise |
| **Audit trail** | Full compliance logging for regulated industries (insurance) |
| **Self-hosted** | Runs on your own infrastructure — no data leaves the network |
| **Model flexibility** | Choose GPT-4o, Claude, free models, or local LLMs per feature |
| **Rules engine** | Custom code quality rules and deployment gates |
| **Multi-repo orchestration** | Manage cross-repo dependencies in one view |
| **Cost transparency** | See exact token costs per call, per user, per model |

---

## Recommended Roadmap

### Phase 1 (Completed): Execution Foundation
- [x] Embedded terminal (App Runner)
- [x] File explorer for local repos
- [x] Git operations page
- [x] CI/CD Monitor page
- [x] PR creation from Build Phase

### Phase 2 (Next — Weeks 1-4): Intelligence Layer
- [ ] Agent Mode (autonomous Ask → Plan → Build → Review chain)
- [ ] Auto-fix loop (detect errors → AI fix → re-run)
- [ ] Session persistence across pages

### Phase 3 (Weeks 5-8): Polish & Enterprise
- [ ] CI/CD failure detection and auto-fix suggestions
- [ ] Knowledge base from past sessions
- [ ] Enhanced Skills with auto-execution
- [ ] Desktop app (.exe) packaging

**Estimated time to reach full feature parity with industry leaders: 6-8 weeks**

ZECT's enterprise features (audit trail, token controls, multi-project management, self-hosted) already surpass industry-leading tools in areas critical for large organizations. The main gaps are in autonomous execution and session persistence.
