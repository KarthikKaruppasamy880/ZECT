"""Ask / Plan / enhance-blueprint — callable from ForgeLoop."""

from __future__ import annotations

import os
import re
from typing import Any


def _openai_ready() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def run_ask(
    question: str,
    *,
    repo_context: str = "",
    repo_id: int | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Clarify requirements (Ask Mode). Offline fallback when no API key."""
    context = repo_context or ""
    if repo_id and db is not None and not context:
        from app.routers.llm import _build_repo_context

        context = _build_repo_context(db, repo_id)

    if not _openai_ready():
        return {
            "answer": (
                f"Ask (offline): clarify target language, modules to port, and acceptance tests for: "
                f"{question[:300]}"
            ),
            "model": "offline",
            "tokens_used": 0,
            "offline": True,
            "context_chars": len(context),
        }

    from openai import APIError, OpenAI

    from app.token_tracker import log_tokens

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    system_prompt = (
        "You are ZECT Mentrix Ask — clarify upgrade requirements. "
        "Be concise; list open questions and assumed defaults for any-language → any-language ports."
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append({
            "role": "user",
            "content": f"Repository / Lattice context:\n\n{context[:8000]}",
        })
    messages.append({"role": "user", "content": question})
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=2000,
            temperature=0.3,
        )
        answer = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else 0
        log_tokens(
            action="ask_question",
            feature="ask_mode",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )
        return {"answer": answer, "model": "gpt-4o-mini", "tokens_used": tokens, "offline": False}
    except APIError as e:
        return {
            "answer": f"Ask failed: {e.message}",
            "model": "error",
            "tokens_used": 0,
            "offline": True,
            "error": str(e),
        }


def run_plan(
    project_description: str,
    *,
    repo_context: str = "",
    constraints: str = "",
    repo_id: int | None = None,
    db: Any = None,
    upgrade: bool = False,
) -> dict[str, Any]:
    """Structured engineering plan. Upgrade mode forces phased inventory→port→tests→eval."""
    context = repo_context or ""
    if repo_id and db is not None and not context:
        from app.routers.llm import _build_repo_context

        context = _build_repo_context(db, repo_id)

    if not _openai_ready():
        phases = [
            "Inventory APIs and modules",
            "Port module 1 (core)",
            "Port module 2 (integrations)",
            "Tests and API evals",
            "Mentrix Ultra Review + lint",
            "Human approve → PR",
        ]
        plan_text = (
            f"# Upgrade plan\n\nGoal: {project_description[:500]}\n\n"
            + "\n".join(f"## Phase {i+1}: {p}" for i, p in enumerate(phases))
        )
        steps = [
            {"step": i + 1, "title": p, "action": p, "files": [], "phase": p}
            for i, p in enumerate(phases)
        ]
        return {
            "plan": plan_text,
            "phases": phases,
            "steps": steps,
            "model": "offline",
            "tokens_used": 0,
            "offline": True,
        }

    from openai import APIError, OpenAI

    from app.token_tracker import log_tokens

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    extra = ""
    if upgrade:
        extra = (
            " This is a language/platform upgrade. Phases MUST include: "
            "inventory → port module N → tests → API eval → review. "
            "Support any source→target language pair implied by the goal."
        )
    system_prompt = (
        "You are ZECT Mentrix Planner — senior engineering planner."
        f"{extra} "
        "Generate a detailed phased plan with markdown headers. "
        "Include architecture, risks, and acceptance criteria."
    )
    user_content = f"Project Description:\n{project_description}"
    if context:
        user_content += f"\n\nContext:\n{context[:6000]}"
    if constraints:
        user_content += f"\n\nConstraints:\n{constraints}"

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
        phases = re.findall(r"^#{1,3}\s+(.+)$", plan_text, re.MULTILINE)[:20]
        if not phases:
            phases = [f"Phase {i+1}" for i in range(4)]
        steps = [
            {"step": i + 1, "title": p, "action": p, "files": [], "phase": p}
            for i, p in enumerate(phases)
        ]
        log_tokens(
            action="generate_plan",
            feature="plan_mode",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )
        return {
            "plan": plan_text,
            "phases": phases,
            "steps": steps,
            "model": "gpt-4o-mini",
            "tokens_used": tokens,
            "offline": False,
        }
    except APIError as e:
        phases = [
            "Inventory APIs and modules",
            "Port modules",
            "Tests and API evals",
            "Mentrix Ultra Review + lint",
            "Human approve → PR",
        ]
        plan_text = f"# Upgrade plan (fallback)\n\n{project_description[:500]}\n\n" + "\n".join(
            f"## {p}" for p in phases
        )
        return {
            "plan": plan_text,
            "phases": phases,
            "steps": [{"step": i + 1, "title": p, "action": p, "files": [], "phase": p} for i, p in enumerate(phases)],
            "model": "error",
            "tokens_used": 0,
            "offline": True,
            "error": str(e),
        }


def run_enhance_blueprint(raw_blueprint: str, instructions: str = "") -> dict[str, Any]:
    if not _openai_ready() or not raw_blueprint.strip():
        return {
            "enhanced_prompt": raw_blueprint or instructions or "(empty blueprint)",
            "model": "offline",
            "tokens_used": 0,
            "offline": True,
        }
    from openai import APIError, OpenAI

    from app.token_tracker import log_tokens

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Enhance this migration blueprint into a clear Mentrix upgrade prompt. "
                        "Keep actionable file/module lists."
                    ),
                },
                {
                    "role": "user",
                    "content": f"{instructions}\n\n{raw_blueprint[:10000]}" if instructions else raw_blueprint[:10000],
                },
            ],
            max_tokens=3000,
            temperature=0.3,
        )
        text = resp.choices[0].message.content or raw_blueprint
        tokens = resp.usage.total_tokens if resp.usage else 0
        log_tokens(
            action="enhance_blueprint",
            feature="blueprint",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )
        return {"enhanced_prompt": text, "model": "gpt-4o-mini", "tokens_used": tokens, "offline": False}
    except APIError as e:
        return {
            "enhanced_prompt": raw_blueprint,
            "model": "error",
            "tokens_used": 0,
            "offline": True,
            "error": str(e),
        }
