# Multi-Repo Analysis Guide

> Step-by-step guide for analyzing multiple GitHub repositories simultaneously with ZECT.

## Overview

ZECT's Multi-Repo Analysis lets you analyze several repositories in a single request. This is useful for understanding cross-repo dependencies, comparing architectures, or preparing multi-repo blueprints.

## Prerequisites

1. ZECT backend running (`poetry run uvicorn app.main:app --port 8000`)
2. ZECT frontend running (`npm run dev`)
3. (Recommended) GitHub Personal Access Token configured in Settings — multi-repo analysis consumes more API calls

## Step-by-Step

### Step 1: Navigate to Repo Analysis

Click **Repo Analysis** in the sidebar, or go to `/repo-analysis`.

### Step 2: Select Multi-Repo Mode

Click the **Multi-Repo** tab.

### Step 3: Add Repositories

You start with one empty row. For each repo:

| Field | Example | Description |
|-------|---------|-------------|
| Owner | `KarthikKaruppasamy880` | GitHub org or user |
| Repo | `ZECT` | Repository name |

Click **Add Repo** to add more rows. Click the trash icon to remove a row.

**Example setup for analyzing your full stack:**

| # | Owner | Repo |
|---|-------|------|
| 1 | KarthikKaruppasamy880 | ZECT |
| 2 | KarthikKaruppasamy880 | ZEF |

### Step 4: Click Analyze All

ZECT will analyze each repo sequentially and return results for all.

### Step 5: Review Results

Each repo appears as an expandable card showing:
- Metadata (stars, forks, language, issues)
- Architecture notes
- Dependencies by package manager
- File structure
- README excerpt

### Step 6: Compare Repos

Use the results to compare:
- **Tech stacks** — which languages and frameworks each repo uses
- **Architecture patterns** — monorepo vs multi-repo, src/ vs app/ structure
- **Dependency overlap** — shared packages across repos
- **CI/CD setup** — which repos have GitHub Actions

## API Endpoint

```
POST /api/analysis/multi-repo
Content-Type: application/json

{
  "repos": [
    { "owner": "KarthikKaruppasamy880", "repo": "ZECT" },
    { "owner": "KarthikKaruppasamy880", "repo": "ZEF" }
  ]
}
```

### Response

Returns an array of `RepoAnalysisResult` objects (same structure as single repo analysis).

## Rate Limit Considerations

Each repo in a multi-repo analysis makes 2-10 GitHub API calls depending on the number of dependency files. For N repos:

| Token Status | Approx. Calls | Safe Batch Size |
|-------------|---------------|-----------------|
| No token (60/hr) | ~5 per repo | 10 repos |
| With PAT (5,000/hr) | ~5 per repo | 500+ repos |

## Use Cases

### 1. Cross-Team Architecture Review

Analyze all repos owned by your organization to understand the full technology landscape.

### 2. Dependency Audit

Compare `package.json` / `requirements.txt` across repos to find version mismatches or outdated packages.

### 3. Blueprint Generation Input

Use multi-repo analysis results as input for the Blueprint Generator to create a comprehensive AI prompt covering your entire system.

### 4. Migration Planning

Analyze both old and new repos side-by-side to plan a migration path.

## Tips

- Start with 2-3 repos to test, then scale up
- Configure a GitHub token before analyzing many repos
- Large repos (>1,000 files) will have truncated file trees
- Results are displayed in the order you entered the repos
