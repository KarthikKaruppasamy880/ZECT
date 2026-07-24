"""Model Selection — Per-task model routing with multi-provider support."""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI, APIError
from app.token_tracker import log_tokens

router = APIRouter(prefix="/api/models", tags=["models"])


# ---------------------------------------------------------------------------
# Supported Models Registry
# ---------------------------------------------------------------------------

MODELS = [
    # OpenAI
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "cost_per_1k_input": 0.00015, "cost_per_1k_output": 0.0006, "free": False, "quality": "high", "speed": "fast"},
    {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "cost_per_1k_input": 0.005, "cost_per_1k_output": 0.015, "free": False, "quality": "best", "speed": "medium"},
    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "openai", "cost_per_1k_input": 0.0005, "cost_per_1k_output": 0.0015, "free": False, "quality": "good", "speed": "fastest"},
    # Anthropic (direct)
    {"id": "claude-sonnet-5", "name": "Claude Sonnet 5", "provider": "anthropic", "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015, "free": False, "quality": "best", "speed": "medium"},
    {"id": "claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "anthropic", "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015, "free": False, "quality": "best", "speed": "medium"},
    {"id": "claude-3-haiku", "name": "Claude 3 Haiku", "provider": "anthropic", "cost_per_1k_input": 0.00025, "cost_per_1k_output": 0.00125, "free": False, "quality": "good", "speed": "fastest"},
]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    cost_per_1k_input: float
    cost_per_1k_output: float
    free: bool
    quality: str
    speed: str


class ChatRequest(BaseModel):
    messages: list[dict]  # [{"role": "system"|"user"|"assistant", "content": "..."}]
    model: str = "gpt-4o-mini"
    max_tokens: int = 2000
    temperature: float = 0.3
    feature: str = "general"  # for token tracking


class ChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    tokens_used: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client(provider: str) -> tuple[OpenAI, str]:
    """Get the OpenAI client. Anthropic is handled separately in chat_with_model —
    Anthropic's Messages API has a different request/response shape entirely
    (separate `system` param, content-block list, different token field names);
    it cannot be reached by pointing this same SDK at a different base_url."""
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise HTTPException(status_code=503, detail="OpenAI API key not configured. Set OPENAI_API_KEY in backend/.env")
        return OpenAI(api_key=key), "openai"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")


def _find_model(model_id: str) -> dict:
    """Find model info by ID."""
    for m in MODELS:
        if m["id"] == model_id:
            return m
    # Default fallback
    return MODELS[0]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ModelInfo])
@router.get("/", response_model=list[ModelInfo])
def list_models():
    """List all available models with their pricing and capabilities."""
    return [ModelInfo(**m) for m in MODELS]


@router.get("/status")
def get_model_status():
    """Check which providers are configured."""
    openai_key = bool(os.getenv("OPENAI_API_KEY", ""))
    anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY", ""))
    return {
        "openai_configured": openai_key,
        # Previously reported true whenever an OpenAI key existed, even with
        # no ANTHROPIC_API_KEY at all — Anthropic is a genuinely separate
        # provider/account, so this must not be inferred from OpenAI's key.
        "anthropic_configured": anthropic_key,
        "available_providers": [
            p for p, configured in [("openai", openai_key), ("anthropic", anthropic_key)]
            if configured
        ],
    }


@router.post("/chat", response_model=ChatResponse)
def chat_with_model(req: ChatRequest):
    """Send a chat completion request to the selected model."""
    model_info = _find_model(req.model)
    provider = model_info["provider"]

    try:
        if provider == "anthropic":
            from app.services.llm.anthropic_client import anthropic_available
            from app.services.llm.anthropic_client import create_fn as anthropic_create_fn

            if not anthropic_available():
                raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured.")
            resp = anthropic_create_fn(
                model=req.model,
                messages=req.messages,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
            )
        else:
            client, _ = _get_client(provider)
            resp = client.chat.completions.create(
                model=req.model,
                messages=req.messages,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
            )
        content = resp.choices[0].message.content or ""
        prompt_tokens = resp.usage.prompt_tokens if resp.usage else 0
        completion_tokens = resp.usage.completion_tokens if resp.usage else 0
        total_tokens = resp.usage.total_tokens if resp.usage else 0

        cost = (prompt_tokens / 1000 * model_info["cost_per_1k_input"]) + \
               (completion_tokens / 1000 * model_info["cost_per_1k_output"])

        log_tokens(
            action="chat",
            feature=req.feature,
            model=req.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        return ChatResponse(
            content=content,
            model=req.model,
            provider=provider,
            tokens_used=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=round(cost, 6),
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"Model API error: {e.message}")
