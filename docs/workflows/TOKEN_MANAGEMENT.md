# ZECT — Token Management

## Overview

Token management ensures AI usage is tracked, costed, and controlled. Every API call to any LLM provider is logged with token counts, estimated cost, and metadata for audit and optimization.

---

## How Tokens are Estimated

### Pre-call Estimation

Before sending a request to the AI provider, ZECT estimates token count using:

```python
# Approximate: 1 token ≈ 4 characters (English text)
# More accurate: Use tiktoken library for OpenAI models

def estimate_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Estimate token count for a given text."""
    # Fast approximation
    return len(text) // 4
    
    # Accurate (requires tiktoken)
    # import tiktoken
    # enc = tiktoken.encoding_for_model(model)
    # return len(enc.encode(text))
```

### Post-call Actual Count

After receiving a response, actual token counts come from the provider's response:

```python
response.usage.prompt_tokens      # Input tokens (actual)
response.usage.completion_tokens  # Output tokens (actual)
response.usage.total_tokens       # Total (actual)
```

---

## How Usage is Tracked

### Token Log Entry

Every AI call creates a `token_logs` record:

| Field | Description | Example |
|-------|-------------|---------|
| `action` | Feature that triggered the call | "code_review", "ask", "plan" |
| `model` | Model used | "gpt-4o-mini" |
| `prompt_tokens` | Input token count | 2,450 |
| `completion_tokens` | Output token count | 890 |
| `estimated_cost` | Cost in USD | 0.0009 |
| `timestamp` | When the call happened | 2025-01-15T10:30:00Z |

### Cost Calculation

```python
PRICING = {
    # Model: {input_per_1M_tokens, output_per_1M_tokens}
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.25, "output": 1.25},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
}

def calculate_cost(model, prompt_tokens, completion_tokens):
    pricing = PRICING[model]
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost
```

---

## How to Reduce Token Waste

### Strategies

| Strategy | Impact | Implementation |
|----------|--------|----------------|
| **Cache repo context** | High | Don't re-fetch unchanged files |
| **Progressive context** | High | Start minimal, add more if needed |
| **Truncate intelligently** | Medium | Keep signatures, skip implementations |
| **Batch related requests** | Medium | Combine related questions |
| **Use cheaper models** | High | gpt-4o-mini for simple tasks |
| **Set max_tokens** | Low | Prevent runaway completions |

### Token Savings Tracking

ZECT calculates savings as:

```
savings_percent = (naive_tokens - actual_tokens) / naive_tokens * 100

Where:
- naive_tokens = full file content × number of requests
- actual_tokens = actual tokens used with caching/chunking
```

---

## How to Cache Repo Summaries

### Cache Architecture

```
┌─────────────────────────────────────┐
│ Request: "Review PR #10 on ZECT"    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Check cache for ZECT repo context   │
│ Key: ZECT@{latest_commit_sha}       │
└─────────────────┬───────────────────┘
                  │
          ┌───────┴───────┐
          │               │
     Cache HIT       Cache MISS
          │               │
          ▼               ▼
  Use cached         Fetch from
  context            GitHub API
  (0 tokens)         (fetch + cache)
```

### What to Cache

| Data | Cache Key | TTL |
|------|-----------|-----|
| File tree | `{owner}/{repo}@{sha}:tree` | 1 hour |
| README | `{owner}/{repo}@{sha}:readme` | 1 hour |
| Dependencies | `{owner}/{repo}@{sha}:deps` | 6 hours |
| Repo summary | `{owner}/{repo}@{sha}:summary` | 24 hours |

---

## How to Avoid Repeated Full Repo Scans

1. **SHA-based caching** — if repo hasn't changed (same SHA), use cached context
2. **Incremental analysis** — only analyze changed files since last scan
3. **Summary caching** — store repo-level summaries that don't need full re-scan
4. **Diff-based review** — for code review, only send the diff, not full files
5. **Tree-level analysis** — analyze file tree structure without fetching content

---

## Token Usage Dashboard

The Analytics page shows:

### Summary Cards
- **Total API Calls** — number of LLM requests made
- **Total Tokens** — prompt + completion tokens consumed
- **Estimated Cost** — total USD spent on AI calls

### Breakdown Views

| View | Shows |
|------|-------|
| By User | Token usage per team member |
| By Session | Token usage per session |
| By Tool/Feature | Usage by Ask/Plan/Review/Blueprint |
| By Model | Usage by model (gpt-4o vs gpt-4o-mini) |
| By Time | Daily/weekly/monthly trends |

### Budget Alerts

| Threshold | Action |
|-----------|--------|
| 50% of monthly budget | Info notification |
| 70% of monthly budget | Warning notification |
| 80% of monthly budget | Alert to team lead |
| 90% of monthly budget | Block non-critical requests |
| 100% of monthly budget | Block all AI requests, notify admin |

---

## Configuration

```env
# Token management settings (backend/.env)
TOKEN_MONTHLY_BUDGET=100000      # Monthly token budget
TOKEN_ALERT_THRESHOLD=80         # Alert at this % of budget
TOKEN_TRACKING_ENABLED=true      # Enable/disable tracking
TOKEN_COST_MODEL=actual          # "actual" or "estimated"
```

In ZECT Settings UI:
- **Token Usage Tracking** toggle — enable/disable
- **Monthly Token Budget Alert** — threshold percentage
