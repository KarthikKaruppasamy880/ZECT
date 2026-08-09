"""Model Selection — Per-task model routing with multi-provider support."""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI, APIError
from app.adapters.llm.openai_compat import (
    MENTRIX_LOCAL_MODELS,
    get_openai_compat_client,
    mentrix_local_llm_configured,
    mentrix_llm_chat_model,
    probe_mentrix_local_llm,
)
from app.token_tracker import log_tokens

router = APIRouter(prefix="/api/models", tags=["models"])


# ---------------------------------------------------------------------------
# Supported Models Registry
# ---------------------------------------------------------------------------

MODELS = [
    # Mentrix Local LLM (OpenAI-compatible gateway)
    *MENTRIX_LOCAL_MODELS,
    # OpenAI
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "cost_per_1k_input": 0.00015, "cost_per_1k_output": 0.0006, "free": False, "quality": "high", "speed": "fast"},
    {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "cost_per_1k_input": 0.005, "cost_per_1k_output": 0.015, "free": False, "quality": "best", "speed": "medium"},
    # Pricing below is an estimate, not confirmed against OpenAI's published
    # rate card — correct cost_per_1k_input/output once real GPT-5.4 pricing
    # is known; it only affects the cost_usd shown in Token Controls/Analytics,
    # not model selection or generation itself.
    {"id": "gpt-5.4", "name": "GPT-5.4", "provider": "openai", "cost_per_1k_input": 0.005, "cost_per_1k_output": 0.015, "free": False, "quality": "best", "speed": "medium"},
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
    """Get chat client for openai or mentrix_local providers."""
    if provider == "mentrix_local":
        if not mentrix_local_llm_configured():
            raise HTTPException(
                status_code=503,
                detail="Mentrix Local LLM not configured. Set ZECT_LLM_BASE_URL.",
            )
        try:
            return get_openai_compat_client(), "mentrix_local"
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    if provider == "openai":
        if mentrix_local_llm_configured():
            # Prefer Mentrix Local when gateway is configured (same OpenAI SDK path).
            try:
                return get_openai_compat_client(), "mentrix_local"
            except RuntimeError:
                pass
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key not configured. Set OPENAI_API_KEY in backend/.env",
            )
        return OpenAI(api_key=key), "openai"
    raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")


def _find_model(model_id: str) -> dict:
    """Find model info by ID."""
    for m in MODELS:
        if m["id"] == model_id:
            return m
    # Unknown id → treat as Mentrix Local when gateway is up, else openai default
    if mentrix_local_llm_configured():
        return {
            "id": model_id,
            "name": model_id,
            "provider": "mentrix_local",
            "cost_per_1k_input": 0.0,
            "cost_per_1k_output": 0.0,
            "free": True,
            "quality": "good",
            "speed": "medium",
        }
    for m in MODELS:
        if m["id"] == "gpt-4o-mini":
            return m
    return MODELS[0]

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ModelInfo])
@router.get("/", response_model=list[ModelInfo])
def list_models():
    """List all available models with their pricing and capabilities."""
    models = list(MODELS)
    # Merge live Mentrix Local models when gateway is up
    probe = probe_mentrix_local_llm()
    if probe.get("online") and probe.get("models"):
        known = {m["id"] for m in models}
        for mid in probe["models"]:
            if mid not in known:
                models.append(
                    {
                        "id": mid,
                        "name": f"Mentrix Local — {mid}",
                        "provider": "mentrix_local",
                        "cost_per_1k_input": 0.0,
                        "cost_per_1k_output": 0.0,
                        "free": True,
                        "quality": "good",
                        "speed": "medium",
                    }
                )
    return [ModelInfo(**m) for m in models]


@router.get("/gateway")
def mentrix_llm_gateway_status():
    """Probe Mentrix Local LLM OpenAI-compatible /v1/models."""
    probe = probe_mentrix_local_llm()
    return {
        **probe,
        "default_model": mentrix_llm_chat_model(),
        "chat_model_env": mentrix_llm_chat_model(),
    }


@router.get("/status")
def get_model_status():
    """Check which providers are configured."""
    openai_key = bool(os.getenv("OPENAI_API_KEY", ""))
    anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY", ""))
    local = mentrix_local_llm_configured()
    probe = probe_mentrix_local_llm() if local else {"online": False}
    providers = []
    if local:
        providers.append("mentrix_local")
    if openai_key:
        providers.append("openai")
    if anthropic_key:
        providers.append("anthropic")
    return {
        "openai_configured": openai_key,
        "anthropic_configured": anthropic_key,
        "mentrix_local_configured": local,
        "mentrix_local_online": bool(probe.get("online")),
        "available_providers": providers,
    }


@router.post("/chat", response_model=ChatResponse)
def chat_with_model(req: ChatRequest):
    """Send a chat completion request to the selected model."""
    model_info = _find_model(req.model)
    provider = model_info["provider"]

    try:
        if provider == "anthropic":
            from app.adapters.llm.anthropic_client import anthropic_available
            from app.adapters.llm.anthropic_client import create_fn as anthropic_create_fn

            if not anthropic_available():
                raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured.")
            resp = anthropic_create_fn(
                model=req.model,
                messages=req.messages,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
            )
            used_provider = "anthropic"
        else:
            client, used_provider = _get_client(provider)
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
            provider=used_provider,
            tokens_used=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=round(cost, 6),
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"Model API error: {e.message}")
