"""Agent Orchestrator — autonomous multi-step execution engine.

Chains Ask → Plan → Build → Review → Deploy stages automatically,
with checkpoint support for human-in-the-loop review.
"""

from __future__ import annotations

import os
import json
import time
import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import Session

from app.models import AgentRun, AgentStep


class StageType(str, Enum):
    ASK = "ask"
    PLAN = "plan"
    BUILD = "build"
    REVIEW = "review"
    DEPLOY = "deploy"


STAGE_ORDER = [StageType.ASK, StageType.PLAN, StageType.BUILD, StageType.REVIEW, StageType.DEPLOY]


def _call_llm(prompt: str, system_msg: str, model: str = "gpt-4o-mini") -> dict:
    """Call the configured LLM provider."""
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        return {"content": "Configure an LLM API key to enable Agent Mode.", "tokens": 0, "model": model}

    from openai import OpenAI
    client = OpenAI(api_key=key)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        max_tokens=4000,
        temperature=0.2,
    )
    tokens = resp.usage.total_tokens if resp.usage else 0

    from app.token_tracker import log_tokens
    log_tokens(
        action="agent_mode",
        feature="agent_mode",
        model=model,
        prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
        completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
        total_tokens=tokens,
    )

    return {
        "content": resp.choices[0].message.content or "",
        "tokens": tokens,
        "model": model,
    }


def _execute_stage(stage: StageType, task: str, context: str, model: str) -> dict:
    """Execute a single stage of the agent pipeline."""
    task_ctx = f"Task: {task}\n\nContext: {context}\n\n"
    prompts = {
        StageType.ASK: (
            "You are an expert software analyst. "
            "Analyze the task and provide a clear understanding.",
            task_ctx + (
                "Provide a thorough analysis including:\n"
                "1. Requirements breakdown\n"
                "2. Key questions answered\n"
                "3. Technical considerations\n"
                "4. Potential risks"
            ),
        ),
        StageType.PLAN: (
            "You are an expert software architect. "
            "Create a detailed implementation plan.",
            task_ctx + (
                "Create a step-by-step plan including:\n"
                "1. Architecture decisions\n"
                "2. File changes needed\n"
                "3. Dependencies\n"
                "4. Estimated complexity per task\n"
                "5. Testing strategy"
            ),
        ),
        StageType.BUILD: (
            "You are an expert software engineer. "
            "Generate the implementation code.",
            task_ctx + (
                "Generate the code implementation:\n"
                "1. All necessary code changes\n"
                "2. New files if needed\n"
                "3. Import statements\n"
                "4. Error handling\n"
                "5. Type annotations"
            ),
        ),
        StageType.REVIEW: (
            "You are an expert code reviewer. "
            "Review the implementation for quality.",
            task_ctx + (
                "Review the implementation:\n"
                "1. Code quality assessment (1-10)\n"
                "2. Bug detection\n"
                "3. Security vulnerabilities\n"
                "4. Performance issues\n"
                "5. Suggestions for improvement\n"
                "6. Approval recommendation (approve/request_changes)"
            ),
        ),
        StageType.DEPLOY: (
            "You are a deployment specialist. "
            "Create a deployment plan.",
            task_ctx + (
                "Generate deployment details:\n"
                "1. Pre-deployment checklist\n"
                "2. Deployment steps\n"
                "3. Environment variables needed\n"
                "4. Rollback plan\n"
                "5. Post-deployment verification"
            ),
        ),
    }

    system_msg, prompt = prompts[stage]
    start = time.time()
    result = _call_llm(prompt, system_msg, model)
    duration_ms = int((time.time() - start) * 1000)

    return {
        "stage": stage.value,
        "output": result["content"],
        "tokens_used": result["tokens"],
        "model": result["model"],
        "duration_ms": duration_ms,
        "status": "completed",
    }


def create_agent_run(
    db: Session,
    task: str,
    stages: list[str] | None = None,
    model: str = "gpt-4o-mini",
    repo_context: str = "",
    auto_advance: bool = True,
) -> dict:
    """Create and start an agent run with the specified stages."""
    run_id = str(uuid.uuid4())[:12]
    stage_list = stages or [s.value for s in STAGE_ORDER]

    run = AgentRun(
        run_id=run_id,
        task=task,
        stages=json.dumps(stage_list),
        model=model,
        repo_context=repo_context[:5000],
        auto_advance=auto_advance,
        status="running",
        current_stage_index=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    total_tokens = 0
    context = repo_context

    for i, stage_name in enumerate(stage_list):
        run.current_stage_index = i
        db.commit()

        stage = StageType(stage_name)
        result = _execute_stage(stage, task, context, model)
        total_tokens += result["tokens_used"]

        step = AgentStep(
            agent_run_id=run.id,
            stage=stage_name,
            step_index=i,
            input_context=context[:3000],
            output=result["output"],
            tokens_used=result["tokens_used"],
            duration_ms=result["duration_ms"],
            status=result["status"],
            model=result["model"],
        )
        db.add(step)
        db.commit()

        # Feed output as context to next stage
        context = (
            f"Previous stage ({stage_name}) output:\n"
            f"{result['output']}\n\n"
            f"Original context: {repo_context}"
        )

        if not auto_advance and i < len(stage_list) - 1:
            run.status = "paused"
            run.current_stage_index = i + 1
            run.total_tokens = total_tokens
            db.commit()
            return _format_run(run, db)

    run.status = "completed"
    run.total_tokens = total_tokens
    run.completed_at = datetime.now(timezone.utc)
    db.commit()

    return _format_run(run, db)


def resume_agent_run(db: Session, run_id: str, model: str | None = None) -> dict:
    """Resume a paused agent run from its current stage."""
    run = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
    if not run:
        return {"error": "Run not found"}
    if run.status != "paused":
        return {"error": f"Run is {run.status}, not paused"}

    stage_list = json.loads(run.stages)
    used_model = model or run.model

    # Get last step output for context
    last_step = db.query(AgentStep).filter(
        AgentStep.agent_run_id == run.id
    ).order_by(AgentStep.step_index.desc()).first()

    context = last_step.output if last_step else run.repo_context
    total_tokens = run.total_tokens or 0
    run.status = "running"
    db.commit()

    for i in range(run.current_stage_index, len(stage_list)):
        run.current_stage_index = i
        db.commit()

        stage = StageType(stage_list[i])
        result = _execute_stage(stage, run.task, context, used_model)
        total_tokens += result["tokens_used"]

        step = AgentStep(
            agent_run_id=run.id,
            stage=stage_list[i],
            step_index=i,
            input_context=context[:3000],
            output=result["output"],
            tokens_used=result["tokens_used"],
            duration_ms=result["duration_ms"],
            status=result["status"],
            model=result["model"],
        )
        db.add(step)
        db.commit()

        context = (
            f"Previous stage ({stage_list[i]}) output:\n"
            f"{result['output']}\n\n"
            f"Original context: {run.repo_context}"
        )

        if not run.auto_advance and i < len(stage_list) - 1:
            run.status = "paused"
            run.current_stage_index = i + 1
            run.total_tokens = total_tokens
            db.commit()
            return _format_run(run, db)

    run.status = "completed"
    run.total_tokens = total_tokens
    run.completed_at = datetime.now(timezone.utc)
    db.commit()

    return _format_run(run, db)


def get_agent_run(db: Session, run_id: str) -> dict | None:
    """Get an agent run with all its steps."""
    run = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
    if not run:
        return None
    return _format_run(run, db)


def list_agent_runs(db: Session, limit: int = 20, offset: int = 0) -> list[dict]:
    """List all agent runs."""
    runs = db.query(AgentRun).order_by(AgentRun.created_at.desc()).offset(offset).limit(limit).all()
    return [_format_run(r, db) for r in runs]


def _format_run(run: AgentRun, db: Session) -> dict:
    steps = db.query(AgentStep).filter(
        AgentStep.agent_run_id == run.id
    ).order_by(AgentStep.step_index).all()

    return {
        "id": run.id,
        "run_id": run.run_id,
        "task": run.task,
        "stages": json.loads(run.stages),
        "model": run.model,
        "status": run.status,
        "current_stage_index": run.current_stage_index,
        "auto_advance": run.auto_advance,
        "total_tokens": run.total_tokens or 0,
        "repo_context": run.repo_context,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "steps": [
            {
                "id": s.id,
                "stage": s.stage,
                "step_index": s.step_index,
                "output": s.output,
                "tokens_used": s.tokens_used,
                "duration_ms": s.duration_ms,
                "status": s.status,
                "model": s.model,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in steps
        ],
    }
