"""Review Phase — thin adapter over the canonical reviewer in review_service.py.

Previously this duplicated code_review.py's LLM-calling logic almost verbatim
under a different brand ("Mentrix Ultra Review" vs "ZECT Review Engine") —
confirmed by direct comparison: same 6 review categories, same JSON schema,
same severity scale, different prompt wording, same OpenAI call. That's the
"two systems doing the same thing under different names" pattern found
elsewhere in this codebase this session (Mentrix Companion/Delivery,
build_phase.py/build_phase_svc.py) — consolidated here so there's one real
reviewer (review_service.py), not two drifting copies.

/analyze now delegates to review_code_snippet() and adapts its richer response
shape back to this router's existing contract, so nothing calling this
endpoint needs to change. /fix-prompt is kept as real, distinct logic — it's a
generic "fix any snippet, no GitHub PR required" tool, genuinely different
from code_review.py's /auto-fix-loop (which requires and posts to a real PR).
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from openai import OpenAI, APIError
from app.infrastructure.auth.deps import CurrentUser
from app.infrastructure.budget import enforce_token_budget
from app.infrastructure.database import get_db
from app.token_tracker import log_tokens

router = APIRouter(prefix="/api/review-phase", tags=["review-phase"])


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
    category: str  # bugs, vulnerabilities, performance, code_quality, architecture, best_practices
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

_SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


@router.post("/analyze", response_model=ReviewResponse)
def analyze_code(
    req: ReviewRequest,
    current_user: CurrentUser = Depends(enforce_token_budget),
    db: Session = Depends(get_db),
):
    """AI code quality analysis — delegates to the canonical review engine."""
    from app.review_service import review_code_snippet

    code = req.code
    if req.context:
        code = f"# Context: {req.context[:500]}\n\n{req.code}"

    try:
        result = review_code_snippet(code=code, language=req.language, user_id=current_user.user_id, db=db)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")

    threshold_idx = (
        _SEVERITY_ORDER.index(req.severity_threshold) if req.severity_threshold in _SEVERITY_ORDER else 2
    )
    findings = []
    for f in result.get("findings", []):
        f_severity = f.get("severity", "info")
        if f_severity in _SEVERITY_ORDER and _SEVERITY_ORDER.index(f_severity) <= threshold_idx:
            title = f.get("title", "")
            description = f.get("description", "")
            findings.append(ReviewFinding(
                severity=f_severity,
                category=f.get("category", "code_quality"),
                line=f.get("line"),
                message=f"{title} — {description}" if title and description else (title or description),
                suggestion=f.get("suggestion", ""),
            ))

    quality_score = result.get("quality_score", 50)
    return ReviewResponse(
        passed=quality_score >= 70,
        score=quality_score,
        findings=findings,
        summary=result.get("summary", ""),
        model=result.get("model", "gpt-4o-mini"),
        tokens_used=result.get("tokens_used", 0),
    )


@router.post("/fix-prompt", response_model=FixPromptResponse)
def generate_fix_prompt(
    req: FixPromptRequest,
    current_user: CurrentUser = Depends(enforce_token_budget),
):
    """Generate a fix prompt + corrected code from review findings — works on
    any snippet, no GitHub PR required (distinct from /api/review/auto-fix-loop,
    which requires and posts to a real PR)."""
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
            user_id=current_user.user_id,
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
