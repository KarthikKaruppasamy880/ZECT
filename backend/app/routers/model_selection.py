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
    # OpenRouter (free models)
    {"id": "meta-llama/llama-3.1-8b-instruct:free", "name": "Llama 3.1 8B (Free)", "provider": "openrouter", "cost_per_1k_input": 0, "cost_per_1k_output": 0, "free": True, "quality": "good", "speed": "fast"},
    {"id": "mistralai/mistral-7b-instruct:free", "name": "Mistral 7B (Free)", "provider": "openrouter", "cost_per_1k_input": 0, "cost_per_1k_output": 0, "free": True, "quality": "good", "speed": "fast"},
    {"id": "google/gemma-2-9b-it:free", "name": "Gemma 2 9B (Free)", "provider": "openrouter", "cost_per_1k_input": 0, "cost_per_1k_output": 0, "free": True, "quality": "good", "speed": "fast"},
    {"id": "qwen/qwen-2.5-7b-instruct:free", "name": "Qwen 2.5 7B (Free)", "provider": "openrouter", "cost_per_1k_input": 0, "cost_per_1k_output": 0, "free": True, "quality": "good", "speed": "fast"},
    # Anthropic (via OpenRouter or direct)
    {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "openrouter", "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015, "free": False, "quality": "best", "speed": "medium"},
    {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "provider": "openrouter", "cost_per_1k_input": 0.00025, "cost_per_1k_output": 0.00125, "free": False, "quality": "good", "speed": "fastest"},
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
    """Get the appropriate OpenAI-compatible client for the provider."""
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise HTTPException(status_code=503, detail="OpenAI API key not configured. Set OPENAI_API_KEY in backend/.env")
        return OpenAI(api_key=key), "openai"
    elif provider == "openrouter":
        key = os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise HTTPException(status_code=503, detail="No API key configured. Set OPENROUTER_API_KEY or OPENAI_API_KEY in backend/.env")
        return OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1"), "openrouter"
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
    openrouter_key = bool(os.getenv("OPENROUTER_API_KEY", ""))
    return {
        "openai_configured": openai_key,
        "openrouter_configured": openrouter_key or openai_key,
        "available_providers": [
            p for p, configured in [("openai", openai_key), ("openrouter", openrouter_key or openai_key)]
            if configured
        ],
    }


@router.post("/chat", response_model=ChatResponse)
def chat_with_model(req: ChatRequest):
    """Send a chat completion request to the selected model."""
    model_info = _find_model(req.model)
    provider = model_info["provider"]
    client, provider_name = _get_client(provider)

    try:
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
            provider=provider_name,
            tokens_used=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=round(cost, 6),
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"Model API error: {e.message}")
