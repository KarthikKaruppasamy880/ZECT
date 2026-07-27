"""Root-cause analysis + fix plan — the LLM step bugfix mode needed that
neither run_blueprint() (pure templating) nor run_plan() (a generic phased
plan, not error-aware) provide: given a reproduction attempt's output and the
Lattice components it traces through, explain WHY it's failing and produce a
concrete, numbered fix plan Build can execute directly.
"""

from __future__ import annotations

import os
import re
from typing import Any


def run_root_cause_analysis(
    *,
    goal: str,
    reproduction: dict[str, Any],
    trace: dict[str, Any],
    blueprint: dict[str, Any],
    db: Any = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    from openai import APIError, OpenAI

    from app.services.llm.anthropic_client import DEFAULT_MODEL as ANTHROPIC_MODEL
    from app.services.llm.anthropic_client import anthropic_available
    from app.services.llm.anthropic_client import create_fn as anthropic_create_fn
    from app.services.quality.truncation import complete_with_continuations
    from app.token_tracker import log_tokens

    use_anthropic = anthropic_available()
    client = None if use_anthropic else OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model_name = ANTHROPIC_MODEL if use_anthropic else "gpt-4o-mini"

    repro_text = (
        f"Reproduction attempted: {reproduction.get('attempted')}\n"
        f"Command: {reproduction.get('command')}\n"
        f"Confirmed failing: {reproduction.get('success') is False}\n"
        f"Output:\n{(reproduction.get('output') or '')[:3000]}"
    )
    trace_text = "\n".join(
        f"- {n.get('kind', '')} {n.get('name', '')} @ {n.get('path', '')}"
        for n in (trace.get("nodes") or [])[:20]
    ) or "(no impacted components traced)"

    system_prompt = (
        "You are ZECT's bug-fix root-cause analyst. Given an issue description, a "
        "reproduction attempt's output, and the codebase components it traces through, "
        "identify the ROOT CAUSE (not just symptoms) and produce a concrete, numbered fix "
        "plan. Ground every claim in the evidence given — do not invent files or APIs not "
        "mentioned. Respond in exactly this markdown structure:\n\n"
        "## Root Cause\n<what is actually wrong and why>\n\n"
        "## Affected Components\n<bullet list of the specific files/symbols involved>\n\n"
        "## Fix Plan\n1. <first concrete step>\n2. <second step>\n(one numbered step per line)"
    )
    user_content = (
        f"Issue: {goal[:2000]}\n\n"
        f"## Reproduction\n{repro_text}\n\n"
        f"## Impacted components (Lattice trace)\n{trace_text}\n\n"
        f"## Structural context\n{(blueprint.get('prompt') or '')[:4000]}"
    )

    try:
        completed = complete_with_continuations(
            client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            model=model_name,
            max_tokens=3000,
            temperature=0.2,
            language_hint="text",
            create_fn=anthropic_create_fn if use_anthropic else None,
        )
    except APIError as e:
        raise ValueError(f"OpenAI API error: {e.message}")

    text = completed["content"]
    analysis = text.split("## Fix Plan")[0].strip() if "## Fix Plan" in text else text

    fix_steps: list[str] = []
    if "## Fix Plan" in text:
        plan_block = text.split("## Fix Plan", 1)[1]
        fix_steps = [m.group(1).strip() for m in re.finditer(r"^\s*\d+[.)]\s*(.+)$", plan_block, re.MULTILINE)]
    if not fix_steps:
        fix_steps = ["Fix the reported issue based on the root-cause analysis above"]

    tokens = completed["tokens_used"]
    log_tokens(
        action="bugfix_root_cause",
        feature="bugfix",
        model=model_name,
        prompt_tokens=completed.get("prompt_tokens") or 0,
        completion_tokens=completed.get("completion_tokens") or 0,
        total_tokens=tokens,
        user_id=user_id,
    )

    return {
        "analysis": analysis,
        "fix_plan_text": text,
        "fix_steps": fix_steps,
        "model": model_name,
        "tokens_used": tokens,
    }
