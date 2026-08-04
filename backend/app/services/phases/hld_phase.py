"""HLD (High-Level Design) generator — the LLM call Blueprint never had.

run_blueprint() (blueprint_phase.py) and build_deep_prompt() (structural_blueprint.py)
both only template Lattice's structural data into a prompt string; neither calls an
LLM or produces a design document a human can read. This reuses their data-gathering
(_run_scout for graph/RAG/god-node context, run_blueprint for the structural-to-text
formatting) and adds the one genuinely new step: an LLM call that synthesizes that
data into component breakdown / data-flow / Mermaid diagram / risks / recommendations,
routed through Anthropic when configured, same as build_phase_svc.py's pattern.
"""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

_SYSTEM_PROMPT = (
    "You are ZECT's High-Level Design (HLD) generator. Given a structural summary of a "
    "codebase (tech stack, API endpoints, dependency graph, god nodes, key symbols), "
    "produce a real architecture design document grounded only in the data given — do not "
    "invent components that aren't evidenced in the structural summary. Respond in exactly "
    "this markdown structure:\n\n"
    "## Component Breakdown\n<each major component/module found and its responsibility>\n\n"
    "## Data Flow\n<narrative of how data/requests move through the system>\n\n"
    "## Architecture Diagram\n```mermaid\n<a mermaid flowchart of the components and their relationships>\n```\n\n"
    "## Risks & Technical Debt\n<concrete risks visible in the structural data — god nodes, "
    "tight coupling, missing tests — not generic advice>\n\n"
    "## Recommendations\n<3-5 concrete, prioritized next steps>"
)


def run_hld_generate(
    db: Session,
    project_key: str,
    goal: str = "Produce a high-level design document for this codebase",
    user_id: int | None = None,
) -> dict[str, Any]:
    from openai import APIError, OpenAI

    from app.services.forge_loop.orchestrator import _run_scout
    from app.services.llm.anthropic_client import create_fn as anthropic_create_fn
    from app.services.llm.anthropic_client import resolve_generation_model
    from app.services.phases.blueprint_phase import run_blueprint
    from app.services.quality.truncation import complete_with_continuations
    from app.token_tracker import log_tokens

    events: list[dict] = []
    scout = _run_scout(db, goal, project_key, events)
    structural_prompt = run_blueprint(goal, project_key=project_key, scout=scout)["prompt"]

    use_anthropic, model_name = resolve_generation_model()
    client = None if use_anthropic else OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    try:
        completed = complete_with_continuations(
            client,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": structural_prompt[:12000]},
            ],
            model=model_name,
            max_tokens=4000,
            temperature=0.2,
            language_hint="text",
            create_fn=anthropic_create_fn if use_anthropic else None,
        )
    except APIError as e:
        raise ValueError(f"OpenAI API error: {e.message}")

    tokens = completed["tokens_used"]
    log_tokens(
        action="hld_generate",
        feature="hld",
        model=model_name,
        prompt_tokens=completed.get("prompt_tokens") or 0,
        completion_tokens=completed.get("completion_tokens") or 0,
        total_tokens=tokens,
        user_id=user_id,
    )

    from app.services import context_store

    context_store.save(db, user_id, "blueprint", "hld_document", completed["content"])

    return {
        "hld_document": completed["content"],
        "project_key": project_key,
        "model": model_name,
        "tokens_used": tokens,
        "structural_summary_used": structural_prompt[:12000],
    }
