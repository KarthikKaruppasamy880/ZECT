"""AI-powered code review engine for ZECT.

Analyses PR diffs to identify bugs, vulnerabilities, code quality issues,
structural problems, and provides severity-classified, line-by-line feedback.
"""

import os
import json
from openai import OpenAI, APIError
from app.token_tracker import log_tokens


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
