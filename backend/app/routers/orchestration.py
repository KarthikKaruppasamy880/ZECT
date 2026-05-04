"""Orchestration Backend — Multi-agent task dispatch and workflow management."""

import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI, APIError
from app.token_tracker import log_tokens

router = APIRouter(prefix="/api/orchestration", tags=["orchestration"])


def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")
    return OpenAI(api_key=key)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TaskDispatchRequest(BaseModel):
    task_description: str
    project_context: str | None = None
    available_agents: list[str] = ["planner", "builder", "reviewer", "deployer", "documenter"]
    priority: str = "medium"  # low, medium, high, critical
    constraints: str | None = None


class AgentTask(BaseModel):
    agent: str
    task: str
    dependencies: list[str] = []
    estimated_tokens: int = 0
    priority: str = "medium"


class TaskDispatchResponse(BaseModel):
    workflow_id: str
    tasks: list[AgentTask]
    execution_order: list[list[str]]  # Parallel groups
    estimated_total_tokens: int
    estimated_cost_usd: float
    model: str
    tokens_used: int


class WorkflowStatusRequest(BaseModel):
    workflow_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/dispatch", response_model=TaskDispatchResponse)
def dispatch_task(req: TaskDispatchRequest):
    """Analyze a task and dispatch it to appropriate agents with dependency ordering."""
    client = _get_client()

    system_prompt = (
        "You are ZECT Orchestration Engine. Given a task, break it into subtasks "
        "and assign each to the appropriate agent. Agents available: planner (architecture/design), "
        "builder (code generation), reviewer (code review/testing), deployer (deployment/infra), "
        "documenter (docs/comments). Determine dependencies and parallel execution groups.\n\n"
        "Respond in JSON:\n"
        "{\n"
        '  "tasks": [\n'
        '    {"agent": "<agent>", "task": "<description>", "dependencies": ["<task_id>"], "estimated_tokens": <number>, "priority": "<level>"}\n'
        "  ],\n"
        '  "execution_order": [["task_0", "task_1"], ["task_2"]],\n'
        '  "estimated_total_tokens": <number>,\n'
        '  "estimated_cost_usd": <number>\n'
        "}\nOnly return valid JSON."
    )

    user_content = f"Task: {req.task_description}\nPriority: {req.priority}"
    if req.project_context:
        user_content += f"\nContext: {req.project_context[:2000]}"
    if req.constraints:
        user_content += f"\nConstraints: {req.constraints}"
    user_content += f"\nAvailable Agents: {', '.join(req.available_agents)}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1500,
            temperature=0.2,
        )
        content = resp.choices[0].message.content or "{}"
        tokens = resp.usage.total_tokens if resp.usage else 0

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            data = {"tasks": [], "execution_order": [], "estimated_total_tokens": 0, "estimated_cost_usd": 0}

        log_tokens(
            action="orchestration_dispatch",
            feature="orchestration",
            model="gpt-4o-mini",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=tokens,
        )

        import hashlib
        workflow_id = hashlib.md5(req.task_description.encode()).hexdigest()[:12]

        tasks = [AgentTask(**t) for t in data.get("tasks", [])]

        return TaskDispatchResponse(
            workflow_id=workflow_id,
            tasks=tasks,
            execution_order=data.get("execution_order", []),
            estimated_total_tokens=data.get("estimated_total_tokens", 0),
            estimated_cost_usd=data.get("estimated_cost_usd", 0),
            model="gpt-4o-mini",
            tokens_used=tokens,
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")


@router.get("/agents")
def list_agents():
    """List available agents and their capabilities."""
    return [
        {"id": "planner", "name": "Planner Agent", "capabilities": ["architecture", "design", "task breakdown", "estimation"], "status": "available"},
        {"id": "builder", "name": "Builder Agent", "capabilities": ["code generation", "implementation", "refactoring"], "status": "available"},
        {"id": "reviewer", "name": "Reviewer Agent", "capabilities": ["code review", "security audit", "performance analysis", "testing"], "status": "available"},
        {"id": "deployer", "name": "Deployer Agent", "capabilities": ["deployment", "infrastructure", "CI/CD", "monitoring"], "status": "available"},
        {"id": "documenter", "name": "Documenter Agent", "capabilities": ["documentation", "API docs", "README generation", "comments"], "status": "available"},
    ]
