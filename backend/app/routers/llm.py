"""LLM-powered endpoints for Ask Mode, Plan Mode, and enhanced Blueprint."""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI, APIError
from app.token_tracker import log_tokens

router = APIRouter(prefix="/api/llm", tags=["llm"])


def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key not configured. Go to Settings and add your OPENAI_API_KEY.",
        )
    return OpenAI(api_key=key)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str
    repo_context: str | None = None  # optional repo analysis context


class AskResponse(BaseModel):
    answer: str
    model: str
    tokens_used: int


class PlanRequest(BaseModel):
    project_description: str
    repo_context: str | None = None
    constraints: str | None = None


class PlanResponse(BaseModel):
    plan: str
    phases: list[str]
    model: str
    tokens_used: int


class EnhanceBlueprintRequest(BaseModel):
    raw_blueprint: str
    instructions: str | None = None


class EnhanceBlueprintResponse(BaseModel):
    enhanced_prompt: str
    model: str
    tokens_used: int


class LLMKeyConfig(BaseModel):
    openai_api_key: str


class LLMKeyStatus(BaseModel):
    configured: bool
    model: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest):
    """Ask any engineering question, optionally with repo context."""
    client = _get_client()

    system_prompt = (
        "You are ZECT AI — an expert software engineering assistant for the "
        "Zinnia Engineering Control Tower. You help engineers understand codebases, "
        "debug issues, design architecture, and make technical decisions. "
        "Be concise, practical, and specific. Use code examples when helpful."
    )

    messages = [{"role": "system", "content": system_prompt}]

    if req.repo_context:
        messages.append({
            "role": "user",
            "content": f"Here is the repository context for reference:\n\n{req.repo_context[:8000]}",
        })

    messages.append({"role": "user", "content": req.question})

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=2000,
            temperature=0.3,
        )
        answer = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else 0
        prompt_tok = resp.usage.prompt_tokens if resp.usage else 0
        completion_tok = resp.usage.completion_tokens if resp.usage else 0
        log_tokens(
            action="ask_question",
            feature="ask_mode",
            model="gpt-4o-mini",
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            total_tokens=tokens,
        )
        return AskResponse(answer=answer, model="gpt-4o-mini", tokens_used=tokens)
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")


@router.post("/plan", response_model=PlanResponse)
def generate_plan(req: PlanRequest):
    """Generate a structured engineering plan for a project."""
    client = _get_client()

    system_prompt = (
        "You are ZECT AI — a senior engineering planner. Given a project description, "
        "generate a detailed, phased engineering plan. Include:\n"
        "1. Executive summary\n"
        "2. Technical architecture decisions\n"
        "3. Phased implementation plan with milestones\n"
        "4. Risk assessment\n"
        "5. Resource and timeline estimates\n"
        "Format with clear markdown headers and bullet points."
    )

    user_content = f"Project Description:\n{req.project_description}"
    if req.repo_context:
        user_content += f"\n\nExisting Repository Context:\n{req.repo_context[:6000]}"
    if req.constraints:
        user_content += f"\n\nConstraints:\n{req.constraints}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=3000,
            temperature=0.4,
        )
        plan_text = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else 0

        # Extract phase titles from the plan
        phases = []
        for line in plan_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## Phase") or stripped.startswith("### Phase"):
                phases.append(stripped.lstrip("#").strip())
            elif stripped.startswith("**Phase"):
                phases.append(stripped.strip("*").strip())

        if not phases:
            phases = ["Phase 1: Foundation", "Phase 2: Core Features", "Phase 3: Polish & Deploy"]

        log_tokens(
            action="generate_plan",
            feature="plan_mode",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )
        return PlanResponse(plan=plan_text, phases=phases, model="gpt-4o-mini", tokens_used=tokens)
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")


@router.post("/enhance-blueprint", response_model=EnhanceBlueprintResponse)
def enhance_blueprint(req: EnhanceBlueprintRequest):
    """Enhance a raw blueprint prompt with LLM-powered improvements."""
    client = _get_client()

    system_prompt = (
        "You are ZECT AI — a prompt engineering expert. Take the raw repository blueprint "
        "and enhance it into a production-grade prompt that can be pasted into any AI coding "
        "tool (Cursor, Claude Code, Codex, Windsurf) to recreate or extend the project. "
        "Improve clarity, add implementation priorities, suggest architecture patterns, "
        "and organize the information for maximum AI comprehension. "
        "Keep the output as a single self-contained prompt."
    )

    user_content = f"Raw Blueprint:\n\n{req.raw_blueprint[:12000]}"
    if req.instructions:
        user_content += f"\n\nAdditional Instructions:\n{req.instructions}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=4000,
            temperature=0.3,
        )
        enhanced = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else 0
        log_tokens(
            action="enhance_blueprint",
            feature="blueprint",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )
        return EnhanceBlueprintResponse(
            enhanced_prompt=enhanced, model="gpt-4o-mini", tokens_used=tokens
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")


@router.post("/configure-key", response_model=LLMKeyStatus)
def configure_llm_key(config: LLMKeyConfig):
    """Configure the OpenAI API key at runtime."""
    key = config.openai_api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    # Validate the key by making a test call
    try:
        test_client = OpenAI(api_key=key)
        test_client.models.list()
    except APIError as e:
        raise HTTPException(status_code=400, detail=f"Invalid OpenAI API key: {e.message}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid OpenAI API key. Please check and try again.")

    os.environ["OPENAI_API_KEY"] = key
    return LLMKeyStatus(configured=True, model="gpt-4o-mini")


@router.get("/status", response_model=LLMKeyStatus)
def get_llm_status():
    """Check if LLM API key is configured."""
    key = os.getenv("OPENAI_API_KEY", "")
    return LLMKeyStatus(configured=bool(key), model="gpt-4o-mini" if key else "")
