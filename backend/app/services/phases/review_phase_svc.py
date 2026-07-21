"""Mentrix Ultra Review — callable wrapper around review_phase / heuristics."""

from __future__ import annotations

import json
import os
import re
from typing import Any


def _openai_ready() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def run_ultra_review(
    code: str,
    *,
    language: str = "python",
    context: str = "",
    severity_threshold: str = "medium",
    goal: str = "",
) -> dict[str, Any]:
    """Best-in-class Mentrix Ultra Review (ZECT-branded)."""
    if not code.strip() and goal:
        code = f"# Goal context for review\n# {goal[:2000]}\n"

    if not _openai_ready() or not code.strip():
        findings: list[dict[str, Any]] = []
        blob = (code + "\n" + goal).lower()
        if "password" in blob or "secret" in blob or "api_key" in blob:
            findings.append({
                "severity": "critical",
                "category": "security",
                "line": None,
                "message": "Possible credential handling in upgrade scope",
                "suggestion": "Use secrets manager; never hardcode credentials.",
            })
        # Truncation / incomplete markers
        if re.search(r"\bTODO\b|\bFIXME\b|\.\.\.\s*$|NotImplementedError", code):
            findings.append({
                "severity": "high",
                "category": "maintainability",
                "line": None,
                "message": "Incomplete markers in generated code",
                "suggestion": "Complete implementation before approve.",
            })
        critical = sum(1 for f in findings if f.get("severity") == "critical")
        score = 90 if not findings else (35 if critical else 65)
        return {
            "brand": "Mentrix Ultra Review",
            "passed": critical == 0,
            "score": score,
            "quality_score": score,
            "findings": findings,
            "summary": "Mentrix Ultra Review (offline heuristics).",
            "critical_findings": critical,
            "model": "offline",
            "tokens_used": 0,
            "offline": True,
        }

    from openai import APIError, OpenAI

    from app.token_tracker import log_tokens

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    system_prompt = (
        "You are Mentrix Ultra Review — ZECT's best-in-class PR/code reviewer. "
        "Analyze for security, performance, maintainability, bugs, and style. "
        "Respond ONLY with JSON:\n"
        '{"score":0-100,"passed":bool,"summary":"...","findings":['
        '{"severity":"critical|high|medium|low|info","category":"...","line":null,'
        '"message":"...","suggestion":"..."}]}'
    )
    user_content = f"Language: {language}\n\n```{language}\n{code[:8000]}\n```"
    if context:
        user_content += f"\n\nContext: {context[:2000]}"
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=3000,
            temperature=0.1,
        )
        content = resp.choices[0].message.content or "{}"
        tokens = resp.usage.total_tokens if resp.usage else 0
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            data = {"score": 50, "passed": False, "summary": "Unable to parse review.", "findings": []}

        severity_order = ["critical", "high", "medium", "low", "info"]
        threshold_idx = (
            severity_order.index(severity_threshold) if severity_threshold in severity_order else 2
        )
        findings = []
        for f in data.get("findings", []):
            sev = f.get("severity", "info")
            if sev in severity_order and severity_order.index(sev) <= threshold_idx:
                findings.append({
                    "severity": sev,
                    "category": f.get("category", "style"),
                    "line": f.get("line"),
                    "message": f.get("message", ""),
                    "suggestion": f.get("suggestion", ""),
                })
        critical = sum(1 for f in findings if f.get("severity") == "critical")
        score = int(data.get("score", 50))
        log_tokens(
            action="ultra_review",
            feature="mentrix_ultra_review",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )
        return {
            "brand": "Mentrix Ultra Review",
            "passed": critical == 0 and bool(data.get("passed", score >= 70)),
            "score": score,
            "quality_score": score,
            "findings": findings,
            "summary": data.get("summary", ""),
            "critical_findings": critical,
            "model": "gpt-4o-mini",
            "tokens_used": tokens,
            "offline": False,
        }
    except APIError as e:
        return {
            "brand": "Mentrix Ultra Review",
            "passed": False,
            "score": 0,
            "quality_score": 0,
            "findings": [{
                "severity": "high",
                "category": "bug",
                "line": None,
                "message": f"Review API error: {e.message}",
                "suggestion": "Retry Mentrix Ultra Review",
            }],
            "summary": "Mentrix Ultra Review failed",
            "critical_findings": 0,
            "model": "error",
            "tokens_used": 0,
            "offline": True,
            "error": str(e),
        }
