"""Execute playbook steps via Mentrix runs + optional LLM summaries."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import MentrixRun, Playbook, PlaybookRun


def substitute_variables(text: str, variables: dict | None) -> str:
    """Replace {{var}} placeholders; leave unknown keys intact."""
    if not text:
        return ""
    vars_map = {str(k): str(v) for k, v in (variables or {}).items()}

    def _repl(m: re.Match) -> str:
        key = m.group(1).strip()
        return vars_map.get(key, m.group(0))

    return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", _repl, text)


def _step_fields(step: dict | str, idx: int) -> tuple[str, str, str]:
    if isinstance(step, str):
        return f"Step {idx + 1}", step, "ask"
    title = str(step.get("title") or f"Step {idx + 1}")
    prompt = str(step.get("prompt") or step.get("content") or step.get("goal") or "")
    mode = str(step.get("mode") or "ask").lower()
    if mode not in ("ask", "plan", "build", "review", "bugfix", "deploy"):
        mode = "ask"
    return title, prompt, mode


def _llm_step_summary(prompt: str, knowledge: str) -> tuple[str, int]:
    """Best-effort short LLM answer for a playbook step. Returns (text, tokens)."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are ZECT Mentrix executing a playbook step. Be concise and actionable. "
                "Follow Knowledge Base conventions when provided."
            ),
        },
    ]
    if knowledge:
        messages.append({"role": "user", "content": knowledge[:3000]})
    messages.append({"role": "user", "content": prompt[:6000]})

    try:
        from app.adapters.llm.anthropic_client import anthropic_available, create_fn

        if anthropic_available():
            resp = create_fn(messages=messages, max_tokens=1200, temperature=0.3)
            text = (resp.choices[0].message.content or "").strip()
            tokens = getattr(getattr(resp, "usage", None), "total_tokens", 0) or 0
            return text[:4000], int(tokens)
    except Exception:
        pass

    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return (
            f"[Queued Mentrix step]\n{prompt[:1500]}\n\n"
            "(No LLM key configured — Mentrix run created for follow-up in Delivery.)",
            0,
        )
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=os.getenv("PLAYBOOK_LLM_MODEL", "gpt-4o-mini"),
            messages=messages,
            max_tokens=1200,
            temperature=0.3,
        )
        text = (resp.choices[0].message.content or "").strip()
        tokens = resp.usage.total_tokens if resp.usage else 0
        return text[:4000], int(tokens)
    except Exception as e:
        return f"[Step deferred] {prompt[:800]}\n\nLLM error: {e}", 0


def execute_playbook(
    db: Session,
    playbook: Playbook,
    *,
    variables_used: dict | None = None,
    user_id: int | None = None,
    project_id: int | None = None,
) -> PlaybookRun:
    """Create a PlaybookRun and execute each step (MentrixRun + LLM summary)."""
    variables = variables_used or {}
    steps = playbook.steps or []
    run = PlaybookRun(
        playbook_id=playbook.id,
        user_id=user_id,
        variables_used=variables,
        total_steps=len(steps),
        status="running",
        steps_completed=0,
        output_summary="",
    )
    db.add(run)
    playbook.usage_count = (playbook.usage_count or 0) + 1
    playbook.last_used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)

    knowledge = ""
    try:
        from app.domains.repository.knowledge_base import retrieve_knowledge_for_context

        pid = project_id or playbook.project_id
        knowledge, _ = retrieve_knowledge_for_context(
            db,
            query=playbook.name or playbook.description or "",
            project_id=pid,
            max_tokens=600,
            limit=4,
        )
    except Exception:
        pass

    summaries: list[str] = []
    total_tokens = 0
    mentrix_ids: list[int] = []
    pid = project_id or playbook.project_id

    try:
        for idx, step in enumerate(steps):
            title, prompt_raw, mode = _step_fields(step, idx)
            prompt = substitute_variables(prompt_raw, variables)
            if not prompt.strip():
                prompt = substitute_variables(title, variables)

            goal = f"[Playbook:{playbook.name}] {title}\n\n{prompt}"
            if knowledge:
                goal = f"{knowledge}\n\n{goal}"

            mrun = MentrixRun(
                project_id=pid,
                mode=mode,
                goal=goal[:4000],
                status="running",
                current_agent="playbook",
                events_json="[]",
                gates_json="{}",
                result_json=json.dumps(
                    {
                        "context": {
                            "source": "playbook",
                            "playbook_id": playbook.id,
                            "playbook_run_id": run.id,
                            "step": idx + 1,
                            "title": title,
                        }
                    }
                ),
                next_step="",
                created_by="playbook",
            )
            db.add(mrun)
            db.commit()
            db.refresh(mrun)
            mentrix_ids.append(mrun.id)

            try:
                from app.workers.mentrix_worker import run_mentrix_in_background

                run_mentrix_in_background(
                    mrun.id,
                    goal=goal[:4000],
                    mode=mode,
                    project_key="",
                    project_id=pid,
                    created_by="playbook",
                    workspace="",
                    source_lang=None,
                    target_lang=None,
                    repo_id=None,
                )
            except Exception:
                # Continue with LLM summary even if worker unavailable
                mrun.status = "queued"
                db.commit()

            summary, tokens = _llm_step_summary(prompt, knowledge)
            total_tokens += tokens
            summaries.append(f"### {title}\n{summary}")
            run.steps_completed = idx + 1
            run.total_tokens = total_tokens
            run.output_summary = "\n\n".join(summaries)[:8000]
            db.commit()

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        if mentrix_ids:
            run.output_summary = (
                (run.output_summary or "")
                + f"\n\nMentrix runs: {', '.join(f'#{i}' for i in mentrix_ids)}"
            )[:8000]
        db.commit()
        db.refresh(run)
        return run
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)[:1000]
        run.completed_at = datetime.now(timezone.utc)
        run.output_summary = ((run.output_summary or "") + f"\n\nFailed: {e}")[:8000]
        db.commit()
        db.refresh(run)
        return run
