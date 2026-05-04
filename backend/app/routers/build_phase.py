"""Build Phase — Full AI code generation from plan steps."""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI, APIError
from app.token_tracker import log_tokens

router = APIRouter(prefix="/api/build", tags=["build"])


def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")
    return OpenAI(api_key=key)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class BuildRequest(BaseModel):
    plan_step: str
    project_context: str | None = None
    tech_stack: str | None = None
    file_path: str | None = None


class BuildResponse(BaseModel):
    generated_code: str
    file_path: str
    language: str
    explanation: str
    model: str
    tokens_used: int


class BuildFromPlanRequest(BaseModel):
    full_plan: str
    step_index: int = 0
    tech_stack: str | None = None
    project_context: str | None = None


class BuildFromPlanResponse(BaseModel):
    steps: list[dict]
    current_step: dict
    generated_code: str
    file_path: str
    language: str
    explanation: str
    model: str
    tokens_used: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=BuildResponse)
def generate_code(req: BuildRequest):
    """Generate code for a single plan step."""
    client = _get_client()

    system_prompt = (
        "You are ZECT AI Build Agent — an expert code generator. Given a plan step, "
        "generate production-ready code. Follow best practices:\n"
        "- Clean, well-structured code with proper error handling\n"
        "- Include type annotations and docstrings\n"
        "- Follow SOLID principles\n"
        "- Include necessary imports\n"
        "- Add inline comments for complex logic\n\n"
        "Respond in this exact format:\n"
        "FILE_PATH: <suggested file path>\n"
        "LANGUAGE: <programming language>\n"
        "EXPLANATION: <brief explanation of what this code does>\n"
        "```<language>\n<code>\n```"
    )

    user_content = f"Plan Step: {req.plan_step}"
    if req.tech_stack:
        user_content += f"\nTech Stack: {req.tech_stack}"
    if req.project_context:
        user_content += f"\nProject Context: {req.project_context[:4000]}"
    if req.file_path:
        user_content += f"\nTarget File: {req.file_path}"

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

        # Parse response
        file_path = "generated/output.ts"
        language = "typescript"
        explanation = ""
        code = content

        for line in content.split("\n"):
            if line.startswith("FILE_PATH:"):
                file_path = line.replace("FILE_PATH:", "").strip()
            elif line.startswith("LANGUAGE:"):
                language = line.replace("LANGUAGE:", "").strip().lower()
            elif line.startswith("EXPLANATION:"):
                explanation = line.replace("EXPLANATION:", "").strip()

        # Extract code block
        if "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                code_block = parts[1]
                # Remove language identifier from first line
                code_lines = code_block.split("\n")
                if code_lines and not code_lines[0].strip().startswith(("import", "from", "const", "let", "var", "def", "class", "package", "#")):
                    code_lines = code_lines[1:]
                code = "\n".join(code_lines).strip()

        log_tokens(
            action="build_generate",
            feature="build_phase",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )

        return BuildResponse(
            generated_code=code,
            file_path=file_path,
            language=language,
            explanation=explanation,
            model="gpt-4o-mini",
            tokens_used=tokens,
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")


@router.post("/from-plan", response_model=BuildFromPlanResponse)
def build_from_plan(req: BuildFromPlanRequest):
    """Parse a plan into steps and generate code for the specified step."""
    client = _get_client()

    # First, parse the plan into discrete steps
    parse_prompt = (
        "Extract the implementation steps from this engineering plan. "
        "Return a JSON array of objects with 'title' and 'description' fields. "
        "Only return the JSON array, nothing else."
    )

    try:
        parse_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": parse_prompt},
                {"role": "user", "content": req.full_plan[:6000]},
            ],
            max_tokens=2000,
            temperature=0.1,
        )
        import json
        steps_text = parse_resp.choices[0].message.content or "[]"
        # Clean up potential markdown code fence
        if steps_text.startswith("```"):
            steps_text = steps_text.split("```")[1]
            if steps_text.startswith("json"):
                steps_text = steps_text[4:]
        steps = json.loads(steps_text.strip())
    except (json.JSONDecodeError, IndexError):
        steps = [{"title": "Implementation", "description": req.full_plan[:500]}]

    if not steps:
        steps = [{"title": "Implementation", "description": req.full_plan[:500]}]

    # Get the current step
    idx = min(req.step_index, len(steps) - 1)
    current_step = steps[idx]

    # Generate code for this step
    build_req = BuildRequest(
        plan_step=f"{current_step.get('title', '')}: {current_step.get('description', '')}",
        tech_stack=req.tech_stack,
        project_context=req.project_context,
    )
    result = generate_code(build_req)

    parse_tokens = parse_resp.usage.total_tokens if parse_resp.usage else 0
    log_tokens(
        action="build_parse_plan",
        feature="build_phase",
        model="gpt-4o-mini",
        prompt_tokens=parse_resp.usage.prompt_tokens if parse_resp.usage else 0,
        completion_tokens=parse_resp.usage.completion_tokens if parse_resp.usage else 0,
        total_tokens=parse_tokens,
    )

    return BuildFromPlanResponse(
        steps=steps,
        current_step=current_step,
        generated_code=result.generated_code,
        file_path=result.file_path,
        language=result.language,
        explanation=result.explanation,
        model=result.model,
        tokens_used=result.tokens_used + parse_tokens,
    )
