# Repo Analysis Guide

> Step-by-step guide for analyzing a single GitHub repository with ZECT.

## Overview

ZECT's Repo Analysis feature fetches real-time data from the GitHub API to provide a comprehensive view of any public (or token-accessible) repository. This includes file structure, README content, dependencies, and architecture patterns.

## Prerequisites

1. ZECT backend running (`poetry run uvicorn app.main:app --port 8000`)
2. ZECT frontend running (`npm run dev`)
3. (Optional) GitHub Personal Access Token configured in Settings for higher rate limits

## Step-by-Step: Single Repo Analysis

### Step 1: Navigate to Repo Analysis

Click **Repo Analysis** in the sidebar, or go to `/repo-analysis`.

### Step 2: Select Single Repo Mode

Click the **Single Repo** tab (selected by default).

### Step 3: Enter Repository Details

| Field | Example | Description |
|-------|---------|-------------|
| Owner | `facebook` | GitHub organization or user |
| Repository | `react` | Repository name |

### Step 4: Click Analyze

Click the **Analyze** button. ZECT will:

1. Fetch repository metadata (description, language, stars, forks, issues)
2. Fetch the full file tree (up to 300 items)
3. Fetch and decode the README file (up to 8,000 characters)
4. Detect dependencies from well-known files:
   - `package.json` (npm)
   - `requirements.txt` (pip)
   - `pyproject.toml` (poetry/pip)
   - `Cargo.toml` (cargo)
   - `go.mod` (go)
   - `Gemfile` (bundler)
   - `pom.xml` (maven)
   - `build.gradle` (gradle)
5. Infer architecture notes from the file structure

### Step 5: Review Results

Click the repo card to expand and see:

- **Architecture Notes** — detected patterns (e.g., "Source code in src/ directory", "Docker configuration present")
- **Dependencies** — grouped by package manager with individual package names
- **File Structure** — scrollable list of all files in the repo
- **README excerpt** — first 3,000 characters of the README

## API Endpoint

```
POST /api/analysis/repo
Content-Type: application/json

{
  "owner": "facebook",
  "repo": "react"
}
```

### Response

```json
{
  "owner": "facebook",
  "repo": "react",
  "full_name": "facebook/react",
  "description": "The library for web and native user interfaces.",
  "language": "JavaScript",
  "default_branch": "main",
  "stars": 220000,
  "forks": 45000,
  "open_issues": 1200,
  "tree": ["src/", "src/React.js", "..."],
  "readme_content": "# React\n...",
  "dependencies": {
    "npm": ["react", "react-dom", "scheduler"]
  },
  "architecture_notes": [
    "Source code in src/ directory",
    "Test files detected",
    "GitHub Actions CI/CD workflows configured",
    "Primary language: JavaScript"
  ]
}
```

## Rate Limits

| Token Status | Rate Limit |
|-------------|------------|
| No token | 60 requests/hour |
| With PAT | 5,000 requests/hour |

Configure your token in **Settings > GitHub API Key** to increase limits.

## Token Usage

Each analysis logs token consumption. View usage in **Settings > Token Usage > View Log**.

Token estimate = number of tree items + (README length / 4).

## Tips

- For large repos (>1,000 files), only the first 300 tree items are fetched
- README content is capped at 8,000 characters
- Dependencies are capped at 50 items per package manager
- If you hit rate limits, configure a GitHub PAT in Settings
