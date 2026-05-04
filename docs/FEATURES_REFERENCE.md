# ZECT Features Reference

> Granular reference for every ZECT feature — endpoints, inputs, outputs, and usage.

---

## 1. Repo Analysis

**Page:** `/repo-analysis` | **API:** `POST /api/analysis/repo`

### What It Does

Fetches a GitHub repository's metadata, file tree, README, dependencies, and architecture notes. Returns structured data for inspection or further processing.

### Input

| Field | Type | Required | Example |
|-------|------|----------|---------|
| `owner` | string | Yes | `KarthikKaruppasamy880` |
| `repo` | string | Yes | `ZECT` |

### Output (RepoAnalysisResult)

| Field | Type | Description |
|-------|------|-------------|
| `full_name` | string | `owner/repo` |
| `description` | string | Repo description from GitHub |
| `language` | string | Primary language |
| `default_branch` | string | Default branch name |
| `stars` | number | Star count |
| `forks` | number | Fork count |
| `open_issues` | number | Open issue count |
| `tree` | string[] | File paths (up to 300) |
| `readme_content` | string | README text (up to 8,000 chars) |
| `dependencies` | Record<string, string[]> | Dependencies by package manager |
| `architecture_notes` | string[] | Detected patterns |

### Architecture Detection

ZECT detects these patterns from the file tree:

| Pattern | Detection Rule |
|---------|---------------|
| `src/` directory | Standard source layout |
| `app/` directory | Application-centric layout |
| Docker | `Dockerfile`, `docker-compose.yml` |
| CI/CD | `.github/workflows/` |
| Tests | `test/`, `tests/`, `__tests__/`, `spec/` |
| Monorepo | `packages/`, `apps/` |

### Dependency Parsing

Supported files:

| File | Package Manager |
|------|----------------|
| `package.json` | npm |
| `requirements.txt` | pip |
| `pyproject.toml` | poetry/pip |
| `Cargo.toml` | cargo |
| `go.mod` | go |
| `Gemfile` | bundler |
| `pom.xml` | maven |
| `build.gradle` | gradle |

---

## 2. Multi-Repo Analysis

**Page:** `/repo-analysis` (Multi-Repo tab) | **API:** `POST /api/analysis/multi-repo`

### What It Does

Analyzes multiple repos in a single request. Returns an array of `RepoAnalysisResult` — one per repo.

### Input

```json
{
  "repos": [
    { "owner": "KarthikKaruppasamy880", "repo": "ZECT" },
    { "owner": "KarthikKaruppasamy880", "repo": "ZEF" }
  ]
}
```

### Output

Array of `RepoAnalysisResult` (same schema as single-repo).

---

## 3. Blueprint Generator — Standard Mode

**Page:** `/blueprint` (Standard tab) | **API:** `POST /api/analysis/blueprint`

### What It Does

Analyzes one or more repos and synthesizes a single conversational, AI-ready prompt. The prompt is designed to be pasted into any AI coding tool to recreate or extend the project.

### Input

```json
{
  "repos": [
    { "owner": "KarthikKaruppasamy880", "repo": "ZECT" }
  ]
}
```

### Output (BlueprintResult)

| Field | Type | Description |
|-------|------|-------------|
| `prompt` | string | The generated AI-ready prompt (markdown) |
| `token_estimate` | number | Approximate token count (chars / 4) |
| `repos_analyzed` | number | Number of repos included |

### Prompt Structure

The generated prompt includes:
1. **Conversational intro** — natural-language description of what to build
2. **Per-repo sections** — metadata, architecture, dependencies, file tree, README
3. **Instructions** — step-by-step directions for the AI tool

### Prompt Style

- **Conversational** — written as a natural request, not a technical spec
- **Outcome-focused** — tells the AI what to achieve, not just what exists
- **Comprehensive** — includes everything the AI needs to start building

---

## 4. Blueprint Generator — Focused Mode

**Page:** `/blueprint` (Focused tab) | **API:** `POST /api/analysis/blueprint/focused`

### What It Does

Generates a prompt **scoped to a specific feature or layer** of a single repository. Filters the file tree to show files related to the focus area and generates goal-specific instructions.

### Input

| Field | Type | Required | Example |
|-------|------|----------|---------|
| `owner` | string | Yes | `KarthikKaruppasamy880` |
| `repo` | string | Yes | `ZECT` |
| `focus_area` | string | Yes | `authentication` |
| `goal` | string | No | `understand and replicate` |

### Output (FocusedBlueprintResult)

| Field | Type | Description |
|-------|------|-------------|
| `prompt` | string | The focused prompt (markdown) |
| `token_estimate` | number | Approximate token count |
| `focus_area` | string | The requested focus area |
| `repo_name` | string | `owner/repo` |

### Focus Area Examples

| Focus Area | What Gets Highlighted |
|------------|----------------------|
| `authentication` | auth, login, session, token files |
| `API layer` | route, api, endpoint, controller files |
| `database` | model, migration, schema, query files |
| `testing` | test, spec files and utilities |
| `CI/CD` | workflow, docker, deploy files |
| `frontend` | component, page, style files |

### Goal Examples

| Goal | Use Case |
|------|----------|
| `understand and replicate` | Learn how a feature works, then build it yourself |
| `migrate to new framework` | Move functionality from one framework to another |
| `add tests` | Write tests for existing functionality |
| `refactor` | Improve code quality while preserving behavior |
| `extend` | Add new capabilities to existing feature |

---

## 5. Documentation Generator

**Page:** `/doc-generator` | **API:** `POST /api/analysis/docs/generate`

### What It Does

Generates structured documentation for a repository based on its GitHub data. Supports 6 section types that can be toggled on/off.

### Input

| Field | Type | Required | Example |
|-------|------|----------|---------|
| `owner` | string | Yes | `KarthikKaruppasamy880` |
| `repo` | string | Yes | `ZECT` |
| `sections` | string[] | No | `["overview", "architecture"]` |

Default sections: `["overview", "architecture", "api", "setup", "testing", "deployment"]`

### Output (DocGenResult)

| Field | Type | Description |
|-------|------|-------------|
| `repo_name` | string | `owner/repo` |
| `sections` | DocSection[] | Generated documentation sections |
| `total_tokens` | number | Total tokens across all sections |

### Section Details

| Key | Title | Content |
|-----|-------|---------|
| `overview` | Overview | Repo description, language, stats, branch |
| `architecture` | Architecture | Detected patterns, key directories with file counts |
| `api` | API Reference | Files containing route/api/endpoint/controller/handler/view |
| `setup` | Setup Guide | Prerequisites, clone command, install commands per package manager |
| `testing` | Testing | Test files detected, framework-specific run commands |
| `deployment` | Deployment | Docker files, GitHub Actions workflows |

---

## 6. GitHub API Key Configuration

**Page:** `/settings` | **API:** `POST /api/analysis/api-key`

### What It Does

Configures a GitHub Personal Access Token at runtime. Validates the token, checks scopes, and returns rate limit info.

### Input

```json
{
  "github_token": "ghp_xxxxxxxxxxxx"
}
```

### Output (ApiKeyStatus)

| Field | Type | Description |
|-------|------|-------------|
| `configured` | boolean | Whether a valid token is set |
| `scopes` | string[] | OAuth scopes (e.g., `["repo"]`) |
| `rate_limit_remaining` | number | Remaining API requests |
| `rate_limit_total` | number | Total API requests allowed |

### Rate Limits

| State | Requests/Hour |
|-------|---------------|
| No token | 60 |
| With token | 5,000 |

### Status Check

`GET /api/analysis/api-key/status` — returns current key status without requiring the token.

---

## 7. Token Usage Tracking

**API:** `GET /api/analysis/tokens` | **Dashboard API:** `GET /api/analytics/token-dashboard`

### What It Does

Persists every token-consuming operation to the `token_logs` database table. Provides aggregated usage stats, cost tracking, and audit trail.

### Token Log API (`GET /api/analysis/tokens`)

Returns recent token usage entries (legacy format).

| Field | Type | Description |
|-------|------|-------------|
| `total_tokens` | number | Sum of all token usage |
| `log` | TokenLogEntry[] | Per-action entries |

### Token Dashboard API (`GET /api/analytics/token-dashboard`)

Returns comprehensive token usage summary for the Dashboard control panel.

| Field | Type | Description |
|-------|------|-------------|
| `total_calls` | number | Total number of API calls made |
| `total_tokens` | number | Total tokens consumed |
| `total_prompt_tokens` | number | Total input/prompt tokens |
| `total_completion_tokens` | number | Total output/completion tokens |
| `total_cost_usd` | number | Estimated total cost in USD |
| `by_feature` | Record<string, FeatureStats> | Breakdown by feature (calls, tokens, cost) |
| `by_model` | Record<string, ModelStats> | Breakdown by model (calls, tokens, cost) |
| `recent` | TokenLogEntry[] | Last 50 operations with full details |

### Database Schema (`token_logs` table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `action` | String | Operation name |
| `feature` | String | Feature category |
| `model` | String | Model used (e.g., gpt-4o-mini) |
| `prompt_tokens` | Integer | Input tokens |
| `completion_tokens` | Integer | Output tokens |
| `total_tokens` | Integer | Total tokens |
| `estimated_cost_usd` | Float | Cost estimate in USD |
| `created_at` | DateTime | Timestamp |

### Cost Estimation

Pricing per 1M tokens (GPT-4o-mini):
- Input: $0.15
- Output: $0.60
- GitHub API: $0.00

### Tracked Actions

| Action | Feature | When |
|--------|---------|------|
| `ask_question` | `ask_mode` | Ask Mode question |
| `generate_plan` | `plan_mode` | Plan Mode generation |
| `enhance_blueprint` | `blueprint` | Blueprint AI enhancement |
| `repo_analysis` | `repo_analysis` | Single/multi-repo analysis |
| `blueprint_generation` | `blueprint` | Standard blueprint generation |
| `focused_blueprint` | `blueprint` | Focused blueprint generation |
| `doc_generation` | `doc_gen` | Documentation generation |

---

## 8. Project Management

**Page:** `/projects` | **API:** `/api/projects`

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all (optional `?status=` filter) |
| POST | `/api/projects` | Create with optional repo links |
| GET | `/api/projects/{id}` | Get with linked repos |
| PUT | `/api/projects/{id}` | Update fields |
| DELETE | `/api/projects/{id}` | Delete project and repos |

### Project Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Project name |
| `description` | string | Description |
| `team` | string | Team name |
| `status` | string | `active`, `planning`, `completed` |
| `current_stage` | string | Current delivery stage |
| `completion_percent` | number | 0-100 |
| `repos` | Repo[] | Linked GitHub repositories |

---

## 9. GitHub Integration

**API:** `/api/github/repos/{owner}/{repo}/...`

### Endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /repos/{owner}` | All repos for an owner/org |
| `GET /repos/{owner}/{repo}` | Single repo details |
| `GET /repos/{owner}/{repo}/pulls` | Pull requests |
| `GET /repos/{owner}/{repo}/pulls/{number}` | Single PR with details |
| `GET /repos/{owner}/{repo}/pulls/{number}/files` | PR file diffs |
| `GET /repos/{owner}/{repo}/commits` | Recent commits |
| `GET /repos/{owner}/{repo}/actions/runs` | CI/CD workflow runs |

---

## 10. Analytics

**Page:** `/analytics` | **API:** `GET /api/analytics/overview`

### Output (AnalyticsOverview)

| Field | Type | Description |
|-------|------|-------------|
| `total_projects` | number | Total project count |
| `active_projects` | number | Projects with status `active` |
| `completed_projects` | number | Projects with status `completed` |
| `avg_completion` | number | Average completion percentage |
| `total_repos` | number | Total linked repos |
| `total_risk_alerts` | number | Sum of risk alerts |
| `stage_distribution` | Record<string, number> | Projects per stage |

---

## 11. Settings

**Page:** `/settings` | **API:** `/api/settings`

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | List all settings (auto-seeds defaults) |
| PUT | `/api/settings/{key}` | Update setting value |

### Default Settings

| Key | Label | Type | Default |
|-----|-------|------|---------|
| `auto-review` | Automated Code Review | toggle | `true` |
| `token-tracking` | Token Usage Tracking | toggle | `true` |
| `deploy-gates` | Deployment Gate Enforcement | toggle | `true` |
| `risk-alerts` | Risk Alert Notifications | toggle | `false` |
| `auto-plan` | Auto-Generate Plan from Requirements | toggle | `false` |
| `session-context` | Session Context Memory | toggle | `true` |
| `default-stage` | Default Starting Stage | select | `Ask Mode` |
| `review-severity` | Minimum Review Severity | select | `Medium` |
| `deploy-approval` | Deployment Approval Mode | select | `Tech Lead + PM` |
| `token-budget` | Monthly Token Budget Alert | select | `80% of budget` |

---

## 12. LLM Integration

**API:** `/api/llm`

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/llm/ask` | Ask engineering questions (Ask Mode) |
| POST | `/api/llm/plan` | Generate engineering plans (Plan Mode) |
| POST | `/api/llm/enhance-blueprint` | Enhance blueprint with AI |
| POST | `/api/llm/configure-key` | Configure OpenAI API key at runtime |
| GET | `/api/llm/status` | Check if LLM key is configured |

### Ask Mode (`POST /api/llm/ask`)

| Input Field | Type | Required | Description |
|-------------|------|----------|-------------|
| `question` | string | Yes | Engineering question |
| `repo_context` | string | No | Repo analysis context |

| Output Field | Type | Description |
|--------------|------|-------------|
| `answer` | string | AI-generated answer |
| `model` | string | Model used (gpt-4o-mini) |
| `tokens_used` | number | Tokens consumed |

### Plan Mode (`POST /api/llm/plan`)

| Input Field | Type | Required | Description |
|-------------|------|----------|-------------|
| `description` | string | Yes | Project/feature description |
| `repo_context` | string | No | Repo analysis context |
| `constraints` | string | No | Technical constraints |

| Output Field | Type | Description |
|--------------|------|-------------|
| `plan` | string | Full engineering plan |
| `phases` | string[] | Extracted phase names |
| `model` | string | Model used |
| `tokens_used` | number | Tokens consumed |

### Blueprint Enhancement (`POST /api/llm/enhance-blueprint`)

| Input Field | Type | Required | Description |
|-------------|------|----------|-------------|
| `blueprint` | string | Yes | Raw blueprint to enhance |
| `instructions` | string | No | Enhancement instructions |

| Output Field | Type | Description |
|--------------|------|-------------|
| `enhanced_prompt` | string | Improved blueprint |
| `model` | string | Model used |
| `tokens_used` | number | Tokens consumed |
