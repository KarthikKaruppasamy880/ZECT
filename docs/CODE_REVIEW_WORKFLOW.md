# ZECT Code Review — How It Works

> **Purpose:** ZECT's AI Code Review engine is designed to be the go-to tool for the Zinnia engineering team across **new projects**, **existing projects**, and **legacy migration work**. It catches bugs, vulnerabilities, architectural issues, and code quality problems before they reach production.

---

## How the Review Works (End-to-End Flow)

```
Developer opens PR  →  ZECT fetches PR diff from GitHub
                              ↓
                    Files parsed (additions, deletions, patches)
                              ↓
                    AI analyzes each file for:
                    • Logic errors & bugs
                    • Security vulnerabilities
                    • Performance issues
                    • Code quality & best practices
                    • Architectural problems
                    • Anti-patterns
                              ↓
                    Findings classified by severity:
                    🔴 Critical  — Must fix before merge
                    🟠 High      — Should fix before merge
                    🟡 Medium    — Fix soon
                    🔵 Low/Info  — Suggestions for improvement
                              ↓
                    Review summary generated:
                    • Quality score (0-100)
                    • Issue count by category
                    • Line-by-line feedback
                    • Code fix suggestions
                    • Strengths identified
                    • Actionable recommendations
                              ↓
                    Token usage logged to database
                    (cost tracking, audit trail)
                              ↓
                    Results displayed in ZECT UI
```

---

## Use Cases for Zinnia Teams

### 1. New Project Development
When building new services (e.g., a new microservice or React app):

| What ZECT Reviews | Why It Matters |
|---|---|
| **Architecture patterns** | Catches tight coupling, missing error boundaries, poor separation of concerns early |
| **Security scanning** | Identifies hardcoded secrets, SQL injection risks, XSS vulnerabilities before they're deployed |
| **Best practices** | Ensures consistent code quality across teams — proper TypeScript typing, error handling, logging |
| **Performance** | Flags N+1 queries, memory leaks, unnecessary re-renders in React components |

**Example:** A developer builds a new claims intake API. ZECT reviews the PR and flags:
- Missing input validation on policy number field (High)
- SQL query inside a loop — potential N+1 issue (Medium)
- No rate limiting on public endpoint (Critical)
- Good use of dependency injection pattern (Strength)

### 2. Existing Project Maintenance
When making changes to production systems:

| What ZECT Reviews | Why It Matters |
|---|---|
| **Regression detection** | Identifies when changes might break existing behavior |
| **Dependency analysis** | Flags when changes affect shared utilities or interfaces |
| **Test coverage gaps** | Suggests areas that need test coverage based on changed code |
| **Breaking changes** | Catches API contract changes that could affect consumers |

**Example:** A developer updates the notification service. ZECT reviews and flags:
- Changed function signature breaks 3 callers in other files (Critical)
- Removed null check that was protecting against edge case (High)
- Good refactoring — reduced complexity by 40% (Strength)

### 3. Legacy Project Migration
When migrating from legacy systems to modern architecture:

| What ZECT Reviews | Why It Matters |
|---|---|
| **Pattern detection** | Identifies legacy anti-patterns that shouldn't be carried into new code |
| **Security upgrade** | Catches deprecated crypto, auth patterns, and insecure defaults from legacy code |
| **Modern best practices** | Ensures migrated code follows current standards (async/await, TypeScript, proper error handling) |
| **Data integrity** | Flags potential data loss or transformation errors during migration |

**Example:** Migrating the policy admin system from monolith to microservices. ZECT reviews and flags:
- Legacy callback pattern should use async/await in new service (Medium)
- Hardcoded database connection string from legacy config (Critical)
- Missing data validation that legacy system handled at DB level (High)
- Good use of repository pattern for data access (Strength)

---

## Review Modes

### Mode 1: PR Review
- Enter GitHub owner, repo name, and PR number
- ZECT fetches the full PR diff from GitHub API
- Analyzes all changed files with full context
- Returns findings with exact file paths and line numbers
- Best for: **Pre-merge code review**

### Mode 2: Code Snippet Review
- Paste any code block directly into ZECT
- Select the programming language
- Get instant review without needing a PR
- Best for: **Quick checks on code blocks, Stack Overflow answers, AI-generated code**

---

## What the AI Detects

### Bugs & Logic Errors
- Null/undefined access without guards
- Off-by-one errors in loops
- Race conditions in async code
- Incorrect type coercions
- Dead code paths
- Unreachable code after return/throw

### Security Vulnerabilities
- Hardcoded secrets, API keys, passwords
- SQL injection via string concatenation
- Cross-Site Scripting (XSS) risks
- Cross-Site Request Forgery (CSRF) gaps
- Insecure deserialization
- Missing authentication/authorization checks
- Sensitive data in logs or error messages

### Performance Issues
- N+1 database queries
- Missing database indexes (suggested by query patterns)
- Memory leaks (unclosed resources, event listener buildup)
- Unnecessary re-renders in React components
- Large bundle imports when tree-shaking is possible
- Synchronous operations that should be async

### Code Quality
- Functions too long or too complex (cyclomatic complexity)
- Poor naming conventions
- Missing or incorrect TypeScript types
- Inconsistent error handling
- Code duplication
- Missing input validation

### Architecture
- Tight coupling between modules
- Circular dependencies
- God objects / God functions
- Missing abstraction layers
- Violation of SOLID principles
- Missing error boundaries in React

### Best Practices
- Missing tests for critical paths
- Incomplete error handling (catch blocks that swallow errors)
- Missing logging for important operations
- Inconsistent API response formats
- Missing documentation for public APIs

---

## Token Tracking & Cost Control

Every review call is tracked in the database:

| Field | Description |
|---|---|
| `action` | "code_review" or "snippet_review" |
| `feature` | "Code Review" |
| `model` | "gpt-4o-mini" (cost-efficient) |
| `prompt_tokens` | Input tokens sent to AI |
| `completion_tokens` | Output tokens received |
| `total_tokens` | Total tokens consumed |
| `estimated_cost` | USD cost estimate |
| `timestamp` | When the review happened |

**Cost Estimates (gpt-4o-mini):**
- Small PR (1-5 files, ~200 lines): ~$0.001-0.003
- Medium PR (5-15 files, ~500 lines): ~$0.003-0.008
- Large PR (15+ files, ~1000+ lines): ~$0.008-0.020

The Dashboard Token Control Panel shows:
- Total API calls across all features
- Total tokens consumed (prompt + completion)
- Total estimated cost in USD
- Breakdown by feature (Ask Mode, Plan Mode, Blueprint, Code Review)
- Recent activity log

---

## Configuration

### Required Environment Variables
```env
OPENAI_API_KEY=sk-...          # OpenAI API key for AI analysis
GITHUB_TOKEN=ghp_...           # GitHub PAT for fetching PR diffs
ZECT_USERNAME=user@zinnia.com  # Login credential
ZECT_PASSWORD=SecurePass123    # Login credential
```

### API Endpoints
```
POST /api/review/pr         — Review a GitHub PR
  Body: { "owner": "org", "repo": "repo-name", "pr_number": 42 }

POST /api/review/snippet    — Review a code snippet
  Body: { "code": "function foo() {...}", "language": "typescript" }
```

---

## Future Enhancements (Roadmap)

| Phase | Feature | Status |
|---|---|---|
| **Current** | PR diff review with severity classification | Done |
| **Current** | Code snippet review | Done |
| **Current** | Token tracking and cost dashboard | Done |
| **Next** | Auto-trigger review on PR creation (GitHub webhook) | Planned |
| **Next** | Review history — compare reviews over time | Planned |
| **Next** | Team-specific rules (e.g., "Zinnia security policy") | Planned |
| **Future** | Auto-fix suggestions with one-click apply | Planned |
| **Future** | Integration with Jira — link findings to tasks | Planned |
| **Future** | Custom review profiles per project type | Planned |
| **Future** | Review metrics dashboard — team improvement over time | Planned |

---

## How ZECT Compares to Manual Review

| Aspect | Manual Review | ZECT AI Review |
|---|---|---|
| **Speed** | Hours to days | Seconds |
| **Consistency** | Varies by reviewer | Same standards every time |
| **Coverage** | Reviewers miss things when tired | Analyzes every line |
| **Security** | Requires security expertise | Built-in vulnerability detection |
| **Knowledge** | Limited to reviewer's experience | Trained on millions of code patterns |
| **Cost** | Engineer time ($100+/hour) | ~$0.01 per review |
| **Availability** | Business hours only | 24/7 |
| **Bias** | Can be influenced by relationships | Objective analysis |

> **Note:** ZECT AI Review is designed to **complement** human reviewers, not replace them. The AI catches mechanical issues so human reviewers can focus on business logic, design decisions, and mentoring.
