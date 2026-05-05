"""Review Phase — AI code quality gate with fix prompt generation."""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI, APIError
from app.token_tracker import log_tokens

router = APIRouter(prefix="/api/review", tags=["review"])


def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")
    return OpenAI(api_key=key)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    code: str
    language: str = "typescript"
    context: str | None = None
    severity_threshold: str = "medium"  # critical, high, medium, low, info


class ReviewFinding(BaseModel):
    severity: str  # critical, high, medium, low, info
    category: str  # security, performance, maintainability, bug, style
    line: int | None = None
    message: str
    suggestion: str


class ReviewResponse(BaseModel):
    passed: bool
    score: int  # 0-100
    findings: list[ReviewFinding]
    summary: str
    model: str
    tokens_used: int


class FixPromptRequest(BaseModel):
    code: str
    findings: list[dict]
    language: str = "typescript"


class FixPromptResponse(BaseModel):
    fix_prompt: str
    fixed_code: str
    changes_summary: str
    model: str
    tokens_used: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=ReviewResponse)
def analyze_code(req: ReviewRequest):
    """AI code quality analysis — acts as a quality gate."""
    client = _get_client()

    system_prompt = (
        "You are ZECT AI Code Reviewer — a senior code quality expert. "
        "Analyze the provided code for:\n"
        "1. Security vulnerabilities (SQL injection, XSS, secrets exposure)\n"
        "2. Performance issues (N+1 queries, memory leaks, inefficient algorithms)\n"
        "3. Maintainability problems (code smell, complexity, naming)\n"
        "4. Bugs and logic errors\n"
        "5. Style and best practice violations\n\n"
        "Respond in this exact JSON format:\n"
        "{\n"
        '  "score": <0-100>,\n'
        '  "passed": <true if score >= 70>,\n'
        '  "summary": "<2-3 sentence summary>",\n'
        '  "findings": [\n'
        "    {\n"
        '      "severity": "<critical|high|medium|low|info>",\n'
        '      "category": "<security|performance|maintainability|bug|style>",\n'
        '      "line": <line number or null>,\n'
        '      "message": "<what is wrong>",\n'
        '      "suggestion": "<how to fix it>"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Only return valid JSON, nothing else."
    )

    user_content = f"Language: {req.language}\n\nCode to review:\n```{req.language}\n{req.code[:8000]}\n```"
    if req.context:
        user_content += f"\n\nContext: {req.context[:2000]}"

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

        import json
        # Clean markdown code fence if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            data = {"score": 50, "passed": False, "summary": "Unable to parse review results.", "findings": []}

        # Filter by severity threshold
        severity_order = ["critical", "high", "medium", "low", "info"]
        threshold_idx = severity_order.index(req.severity_threshold) if req.severity_threshold in severity_order else 2
        
        findings = []
        for f in data.get("findings", []):
            f_severity = f.get("severity", "info")
            if f_severity in severity_order and severity_order.index(f_severity) <= threshold_idx:
                findings.append(ReviewFinding(
                    severity=f_severity,
                    category=f.get("category", "style"),
                    line=f.get("line"),
                    message=f.get("message", ""),
                    suggestion=f.get("suggestion", ""),
                ))

        log_tokens(
            action="review_analyze",
            feature="review_phase",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )

        return ReviewResponse(
            passed=data.get("passed", False),
            score=data.get("score", 50),
            findings=findings,
            summary=data.get("summary", ""),
            model="gpt-4o-mini",
            tokens_used=tokens,
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")


@router.post("/fix-prompt", response_model=FixPromptResponse)
def generate_fix_prompt(req: FixPromptRequest):
    """Generate a fix prompt from review findings — auto-fix workflow."""
    client = _get_client()

    system_prompt = (
        "You are ZECT AI Fix Agent. Given code and its review findings, "
        "generate:\n"
        "1. A prompt that can be sent to any AI coding tool to fix all issues\n"
        "2. The corrected code with all issues fixed\n"
        "3. A summary of changes made\n\n"
        "Respond in this format:\n"
        "FIX_PROMPT:\n<the prompt to fix the issues>\n\n"
        "FIXED_CODE:\n```<language>\n<corrected code>\n```\n\n"
        "CHANGES:\n<bullet list of changes made>"
    )

    findings_text = "\n".join([
        f"- [{f.get('severity', 'medium').upper()}] {f.get('message', '')} → {f.get('suggestion', '')}"
        for f in req.findings
    ])

    user_content = (
        f"Language: {req.language}\n\n"
        f"Original Code:\n```{req.language}\n{req.code[:6000]}\n```\n\n"
        f"Review Findings:\n{findings_text}"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=4000,
            temperature=0.2,
        )
        content = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else 0

        # Parse response sections
        fix_prompt = ""
        fixed_code = ""
        changes = ""

        if "FIX_PROMPT:" in content:
            parts = content.split("FIX_PROMPT:")
            remainder = parts[1] if len(parts) > 1 else ""
            if "FIXED_CODE:" in remainder:
                fix_prompt = remainder.split("FIXED_CODE:")[0].strip()
                remainder = remainder.split("FIXED_CODE:")[1]
                if "CHANGES:" in remainder:
                    code_part = remainder.split("CHANGES:")[0].strip()
                    changes = remainder.split("CHANGES:")[1].strip()
                else:
                    code_part = remainder.strip()
                # Extract code from code block
                if "```" in code_part:
                    code_parts = code_part.split("```")
                    if len(code_parts) >= 2:
                        code_block = code_parts[1]
                        lines = code_block.split("\n")
                        if lines and not lines[0].strip().startswith(("import", "from", "const", "def", "class")):
                            lines = lines[1:]
                        fixed_code = "\n".join(lines).strip()
                else:
                    fixed_code = code_part
            else:
                fix_prompt = remainder.strip()
        else:
            fix_prompt = content
            fixed_code = req.code

        log_tokens(
            action="review_fix_prompt",
            feature="review_phase",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )

        return FixPromptResponse(
            fix_prompt=fix_prompt or "Fix the identified issues in the code.",
            fixed_code=fixed_code or req.code,
            changes_summary=changes or "Applied review fixes.",
            model="gpt-4o-mini",
            tokens_used=tokens,
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")
