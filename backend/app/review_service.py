"""AI-powered code review engine for ZECT.

Analyses PR diffs, code snippets, and full repositories to identify bugs,
vulnerabilities, code quality issues, structural problems, and provides
severity-classified, line-by-line feedback.
"""

import os
import json
from openai import OpenAI, APIError
from app.token_tracker import log_tokens


# File extensions we consider reviewable source code
REVIEWABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb",
    ".php", ".cs", ".cpp", ".c", ".h", ".hpp", ".swift", ".kt",
    ".scala", ".vue", ".svelte", ".html", ".css", ".scss", ".sql",
    ".sh", ".bash", ".yaml", ".yml", ".toml", ".json", ".xml",
    ".tf", ".hcl", ".dockerfile", ".graphql", ".proto",
}

# Files/directories to skip during full-repo scan
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", "dist", "build",
    ".venv", "venv", "env", ".tox", ".mypy_cache", ".pytest_cache",
    "coverage", ".nyc_output", ".turbo", ".cache", "vendor",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Pipfile.lock", "Cargo.lock", "composer.lock", "go.sum",
}


REVIEW_SYSTEM_PROMPT = """You are ZECT Review Engine — an expert AI code reviewer for the Zinnia Engineering Control Tower.

Analyse the provided PR diff and produce a comprehensive code review. Your review MUST be returned as valid JSON with this exact structure:

{
  "summary": "2-3 sentence overall summary of the changes",
  "quality_score": <integer 0-100>,
  "total_issues": <integer>,
  "categories": {
    "bugs": <count>,
    "vulnerabilities": <count>,
    "performance": <count>,
    "code_quality": <count>,
    "architecture": <count>,
    "best_practices": <count>
  },
  "findings": [
    {
      "severity": "critical|high|medium|low|info",
      "category": "bugs|vulnerabilities|performance|code_quality|architecture|best_practices",
      "title": "Short title of the issue",
      "description": "Detailed explanation of the issue and why it matters",
      "file": "path/to/file.ext",
      "line": <line number or null>,
      "suggestion": "Recommended fix or improvement",
      "code_snippet": "relevant code snippet if applicable"
    }
  ],
  "strengths": ["list of positive aspects of the code"],
  "recommendations": ["list of high-level recommendations"]
}

Review criteria:
1. BUGS: Logic errors, off-by-one, null/undefined access, race conditions, edge cases
2. VULNERABILITIES: Hardcoded secrets, SQL injection, XSS, CSRF, auth gaps, insecure deserialization
3. PERFORMANCE: N+1 queries, unnecessary re-renders, memory leaks, blocking operations
4. CODE QUALITY: Dead code, duplicated logic, poor naming, missing types, unclear intent
5. ARCHITECTURE: Tight coupling, circular dependencies, layer violations, anti-patterns
6. BEST PRACTICES: Missing error handling, no input validation, missing tests, poor logging

Be thorough but avoid false positives. Only flag real issues. Be specific with line numbers and file paths."""


def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise ValueError("OpenAI API key not configured. Go to Settings and add your OPENAI_API_KEY.")
    return OpenAI(api_key=key)


def review_pr_diff(
    owner: str,
    repo: str,
    pr_number: int,
    pr_title: str,
    pr_body: str | None,
    files: list[dict],
) -> dict:
    """Analyse a PR diff using AI and return structured review results.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        pr_title: PR title
        pr_body: PR description
        files: List of file dicts with filename, status, additions, deletions, patch
    """
    client = _get_client()

    # Build the diff context
    diff_parts: list[str] = []
    for f in files:
        patch = f.get("patch") or ""
        if patch:
            diff_parts.append(f"--- {f['filename']} ({f['status']}) +{f.get('additions', 0)}/-{f.get('deletions', 0)} ---\n{patch}")

    diff_text = "\n\n".join(diff_parts)

    # Truncate if too long (keep within context window)
    if len(diff_text) > 30000:
        diff_text = diff_text[:30000] + "\n\n... [diff truncated for length]"

    user_content = f"""Review this Pull Request:

**PR #{pr_number}: {pr_title}**
Repository: {owner}/{repo}
{f"Description: {pr_body}" if pr_body else ""}

**Changed Files ({len(files)}):**
{diff_text}

Provide your review as valid JSON following the specified structure."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=4000,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        tokens = resp.usage.total_tokens if resp.usage else 0
        prompt_tok = resp.usage.prompt_tokens if resp.usage else 0
        completion_tok = resp.usage.completion_tokens if resp.usage else 0

        log_tokens(
            action="code_review",
            feature="code_review",
            model="gpt-4o-mini",
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            total_tokens=tokens,
        )

        review = json.loads(content)

        # Ensure required fields exist with defaults
        review.setdefault("summary", "Review completed.")
        review.setdefault("quality_score", 50)
        review.setdefault("total_issues", len(review.get("findings", [])))
        review.setdefault("categories", {})
        review.setdefault("findings", [])
        review.setdefault("strengths", [])
        review.setdefault("recommendations", [])
        review["tokens_used"] = tokens
        review["model"] = "gpt-4o-mini"
        review["pr_number"] = pr_number
        review["repo"] = f"{owner}/{repo}"

        return review

    except APIError as e:
        raise ValueError(f"OpenAI API error: {e.message}")
    except json.JSONDecodeError:
        return {
            "summary": "Review completed but response was not valid JSON.",
            "quality_score": 0,
            "total_issues": 0,
            "categories": {},
            "findings": [],
            "strengths": [],
            "recommendations": [],
            "tokens_used": 0,
            "model": "gpt-4o-mini",
            "pr_number": pr_number,
            "repo": f"{owner}/{repo}",
        }


def review_code_snippet(code: str, language: str = "unknown") -> dict:
    """Review a standalone code snippet (not a PR diff).

    Args:
        code: The code to review
        language: Programming language hint
    """
    client = _get_client()

    user_content = f"""Review this {language} code snippet:

```{language}
{code[:15000]}
```

Provide your review as valid JSON following the specified structure.
Use "snippet" as the file path and provide line numbers relative to the snippet."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=3000,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        tokens = resp.usage.total_tokens if resp.usage else 0
        prompt_tok = resp.usage.prompt_tokens if resp.usage else 0
        completion_tok = resp.usage.completion_tokens if resp.usage else 0

        log_tokens(
            action="code_review_snippet",
            feature="code_review",
            model="gpt-4o-mini",
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            total_tokens=tokens,
        )

        review = json.loads(content)
        review.setdefault("summary", "Snippet review completed.")
        review.setdefault("quality_score", 50)
        review.setdefault("total_issues", len(review.get("findings", [])))
        review.setdefault("categories", {})
        review.setdefault("findings", [])
        review.setdefault("strengths", [])
        review.setdefault("recommendations", [])
        review["tokens_used"] = tokens
        review["model"] = "gpt-4o-mini"

        return review

    except APIError as e:
        raise ValueError(f"OpenAI API error: {e.message}")
    except json.JSONDecodeError:
        return {
            "summary": "Snippet review completed but response was not valid JSON.",
            "quality_score": 0,
            "total_issues": 0,
            "categories": {},
            "findings": [],
            "strengths": [],
            "recommendations": [],
            "tokens_used": 0,
            "model": "gpt-4o-mini",
        }


# ---------------------------------------------------------------------------
# Full Repo Scan
# ---------------------------------------------------------------------------

REPO_REVIEW_SYSTEM_PROMPT = """You are ZECT Review Engine — an expert AI code reviewer for the Zinnia Engineering Control Tower.

Analyse the provided source files from a full repository scan and produce a comprehensive code review. Your review MUST be returned as valid JSON with this exact structure:

{
  "summary": "2-3 sentence overall summary of the repository quality",
  "quality_score": <integer 0-100>,
  "total_issues": <integer>,
  "categories": {
    "bugs": <count>,
    "vulnerabilities": <count>,
    "performance": <count>,
    "code_quality": <count>,
    "architecture": <count>,
    "best_practices": <count>
  },
  "findings": [
    {
      "severity": "critical|high|medium|low|info",
      "category": "bugs|vulnerabilities|performance|code_quality|architecture|best_practices",
      "title": "Short title of the issue",
      "description": "Detailed explanation of the issue and why it matters",
      "file": "path/to/file.ext",
      "line": <line number or null>,
      "suggestion": "Recommended fix or improvement",
      "code_snippet": "relevant code snippet if applicable"
    }
  ],
  "strengths": ["list of positive aspects of the code"],
  "recommendations": ["list of high-level recommendations"]
}

Review criteria:
1. BUGS: Logic errors, off-by-one, null/undefined access, race conditions, edge cases
2. VULNERABILITIES: Hardcoded secrets, SQL injection, XSS, CSRF, auth gaps, insecure deserialization
3. PERFORMANCE: N+1 queries, unnecessary re-renders, memory leaks, blocking operations
4. CODE QUALITY: Dead code, duplicated logic, poor naming, missing types, unclear intent
5. ARCHITECTURE: Tight coupling, circular dependencies, layer violations, anti-patterns
6. BEST PRACTICES: Missing error handling, no input validation, missing tests, poor logging

Be thorough but avoid false positives. Only flag real issues. Be specific with line numbers and file paths."""


def _collect_repo_files(gh_repo: object, path: str = "", branch: str | None = None) -> list[dict]:
    """Recursively collect reviewable source files from a GitHub repo.

    Returns a list of dicts with 'path', 'content', 'size' keys.
    Respects SKIP_DIRS, SKIP_FILES, and REVIEWABLE_EXTENSIONS.
    """
    collected: list[dict] = []
    total_chars = 0
    max_total_chars = 200_000  # stay within reasonable AI context limits

    try:
        kwargs = {"path": path}
        if branch:
            kwargs["ref"] = branch
        contents = gh_repo.get_contents(**kwargs)
    except Exception:
        return collected

    if not isinstance(contents, list):
        contents = [contents]

    for item in contents:
        if total_chars >= max_total_chars:
            break

        name = item.name
        item_path = item.path

        if item.type == "dir":
            if name.lower() in SKIP_DIRS or name.startswith("."):
                continue
            sub_files = _collect_repo_files(gh_repo, item_path, branch)
            for sf in sub_files:
                if total_chars >= max_total_chars:
                    break
                collected.append(sf)
                total_chars += sf["size"]
        else:
            if name in SKIP_FILES:
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in REVIEWABLE_EXTENSIONS:
                continue
            if item.size and item.size > 50_000:
                continue  # skip very large files

            try:
                content = item.decoded_content.decode("utf-8", errors="replace")
            except Exception:
                continue

            file_chars = len(content)
            if total_chars + file_chars > max_total_chars:
                # Truncate this file to fit
                remaining = max_total_chars - total_chars
                content = content[:remaining] + "\n... [truncated]"
                file_chars = remaining

            collected.append({
                "path": item_path,
                "content": content,
                "size": file_chars,
            })
            total_chars += file_chars

    return collected


def review_repo_files(
    owner: str,
    repo: str,
    branch: str | None = None,
    file_patterns: list[str] | None = None,
) -> dict:
    """Scan an entire GitHub repository and run AI code review on all source files.

    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch to scan (default: repo default branch)
        file_patterns: Optional list of glob patterns to filter files (e.g. ["*.py", "src/**"])
    """
    from app.github_service import get_github
    import fnmatch

    gh = get_github()
    gh_repo = gh.get_repo(f"{owner}/{repo}")

    scan_branch = branch or gh_repo.default_branch

    # Collect all reviewable files
    all_files = _collect_repo_files(gh_repo, "", scan_branch)

    # Filter by patterns if provided
    if file_patterns:
        filtered = []
        for f in all_files:
            for pattern in file_patterns:
                if fnmatch.fnmatch(f["path"], pattern):
                    filtered.append(f)
                    break
        all_files = filtered

    if not all_files:
        return {
            "summary": "No reviewable source files found in the repository.",
            "quality_score": 100,
            "total_issues": 0,
            "categories": {"bugs": 0, "vulnerabilities": 0, "performance": 0, "code_quality": 0, "architecture": 0, "best_practices": 0},
            "findings": [],
            "strengths": ["Repository scanned successfully"],
            "recommendations": [],
            "tokens_used": 0,
            "model": "gpt-4o-mini",
            "repo": f"{owner}/{repo}",
            "branch": scan_branch,
            "files_scanned": 0,
            "total_lines": 0,
        }

    # Build file content blocks for AI
    file_blocks: list[str] = []
    total_lines = 0
    for f in all_files:
        lines = f["content"].count("\n") + 1
        total_lines += lines
        file_blocks.append(f"=== FILE: {f['path']} ({lines} lines) ===\n{f['content']}")

    files_text = "\n\n".join(file_blocks)

    # Truncate if needed
    if len(files_text) > 60_000:
        files_text = files_text[:60_000] + "\n\n... [remaining files truncated for context limit]"

    client = _get_client()

    user_content = f"""Perform a FULL REPOSITORY CODE REVIEW:

**Repository:** {owner}/{repo}
**Branch:** {scan_branch}
**Files Scanned:** {len(all_files)}
**Total Lines:** {total_lines}

{files_text}

Provide your comprehensive review as valid JSON following the specified structure.
Focus on the most impactful issues. Check every file for security vulnerabilities, bugs, and code quality."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": REPO_REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=4000,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        tokens = resp.usage.total_tokens if resp.usage else 0
        prompt_tok = resp.usage.prompt_tokens if resp.usage else 0
        completion_tok = resp.usage.completion_tokens if resp.usage else 0

        log_tokens(
            action="code_review_repo_scan",
            feature="code_review",
            model="gpt-4o-mini",
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            total_tokens=tokens,
        )

        review = json.loads(content)

        # Ensure required fields
        review.setdefault("summary", "Repository scan completed.")
        review.setdefault("quality_score", 50)
        review.setdefault("total_issues", len(review.get("findings", [])))
        review.setdefault("categories", {})
        review.setdefault("findings", [])
        review.setdefault("strengths", [])
        review.setdefault("recommendations", [])
        review["tokens_used"] = tokens
        review["model"] = "gpt-4o-mini"
        review["repo"] = f"{owner}/{repo}"
        review["branch"] = scan_branch
        review["files_scanned"] = len(all_files)
        review["total_lines"] = total_lines
        review["scanned_files"] = [f["path"] for f in all_files]

        return review

    except APIError as e:
        raise ValueError(f"OpenAI API error: {e.message}")
    except json.JSONDecodeError:
        return {
            "summary": "Repo scan completed but AI response was not valid JSON.",
            "quality_score": 0,
            "total_issues": 0,
            "categories": {},
            "findings": [],
            "strengths": [],
            "recommendations": [],
            "tokens_used": 0,
            "model": "gpt-4o-mini",
            "repo": f"{owner}/{repo}",
            "branch": scan_branch,
            "files_scanned": len(all_files),
            "total_lines": total_lines,
        }
