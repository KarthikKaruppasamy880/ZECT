"""LLM-powered endpoints for Ask Mode, Plan Mode, and enhanced Blueprint."""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from openai import OpenAI, APIError

from app.database import get_db
from app.models import Repo
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
    repo_id: int | None = None  # auto-inject context from cloned repo


class AskResponse(BaseModel):
    answer: str
    model: str
    tokens_used: int


class PlanRequest(BaseModel):
    project_description: str
    repo_context: str | None = None
    repo_id: int | None = None  # auto-inject context from cloned repo
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

def _build_repo_context(db: Session, repo_id: int, max_chars: int = 8000) -> str:
    """Build a context string from a cloned repo for AI injection."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo or repo.clone_status != "cloned" or not repo.local_path:
        return ""
    root = Path(repo.local_path)
    if not root.is_dir():
        return ""

    parts = [f"Repository: {repo.owner}/{repo.repo_name} (branch: {repo.clone_branch or repo.default_branch})"]

    # Add README if present
    for readme_name in ["README.md", "readme.md", "README.rst", "README.txt"]:
        readme = root / readme_name
        if readme.exists():
            try:
                content = readme.read_text(errors="replace")[:3000]
                parts.append(f"\n--- README ---\n{content}")
            except OSError:
                pass
            break

    # Add file tree (top 2 levels)
    skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".cache"}
    tree_lines = []
    for item in sorted(root.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if item.name in skip or item.name.startswith("."):
            continue
        prefix = "📁 " if item.is_dir() else "📄 "
        tree_lines.append(f"  {prefix}{item.name}")
        if item.is_dir():
            try:
                for sub in sorted(item.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:15]:
                    if sub.name in skip or sub.name.startswith("."):
                        continue
                    sp = "📁 " if sub.is_dir() else "📄 "
                    tree_lines.append(f"    {sp}{sub.name}")
            except PermissionError:
                pass
    if tree_lines:
        parts.append(f"\n--- File Structure ---\n" + "\n".join(tree_lines[:80]))

    # Add stats
    stats = repo.index_stats or {}
    if stats.get("languages"):
        lang_str = ", ".join(f"{k}: {v} lines" for k, v in sorted(stats["languages"].items(), key=lambda x: -x[1])[:8])
        parts.append(f"\n--- Languages ---\n{lang_str}")
        parts.append(f"Total files: {repo.total_files}, Total lines: {repo.total_lines}")

    # Add key config files if they exist
    for cfg_name in ["package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod", "pom.xml"]:
        cfg = root / cfg_name
        if cfg.exists():
            try:
                content = cfg.read_text(errors="replace")[:1500]
                parts.append(f"\n--- {cfg_name} ---\n{content}")
            except OSError:
                pass
            break

    full = "\n".join(parts)
    return full[:max_chars]


@router.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest, db: Session = Depends(get_db)):
    """Ask any engineering question, optionally with repo context."""
    client = _get_client()

    system_prompt = (
        "You are ZECT AI — an expert software engineering assistant for the "
        "Zinnia Engineering Control Tower. You help engineers understand codebases, "
        "debug issues, design architecture, and make technical decisions. "
        "Be concise, practical, and specific. Use code examples when helpful."
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Auto-inject repo context if repo_id provided
    context = req.repo_context or ""
    if req.repo_id and not context:
        context = _build_repo_context(db, req.repo_id)

    if context:
        messages.append({
            "role": "user",
            "content": f"Here is the repository context for reference:\n\n{context[:8000]}",
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
def generate_plan(req: PlanRequest, db: Session = Depends(get_db)):
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

    # Auto-inject repo context if repo_id provided
    context = req.repo_context or ""
    if req.repo_id and not context:
        context = _build_repo_context(db, req.repo_id)

    user_content = f"Project Description:\n{req.project_description}"
    if context:
        user_content += f"\n\nExisting Repository Context:\n{context[:6000]}"
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
        "tool to recreate or extend the project. "
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
