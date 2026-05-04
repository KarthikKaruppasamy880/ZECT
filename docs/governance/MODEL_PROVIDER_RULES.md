# ZECT — Model Provider Rules

## Overview

ZECT supports multiple AI model providers through an abstraction layer. This document defines the rules for selecting, configuring, and switching between providers.

---

## Supported Providers

| Provider | Models | Status |
|----------|--------|--------|
| **OpenAI** | GPT-4o, GPT-4o-mini, GPT-4-turbo | Active |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 4 | Planned |
| **AWS Bedrock** | Claude, Titan, Llama via AWS | Planned |
| **Azure OpenAI** | GPT-4o, GPT-4o-mini (Azure-hosted) | Planned |
| **Google Gemini** | Gemini 2.5 Pro, Gemini 2.5 Flash | Planned |
| **Local/Self-hosted** | Ollama, vLLM, LM Studio | Planned |

---

## Provider Selection Rules

### Rule 1: Use the Cheapest Adequate Model

| Task Complexity | Recommended Tier | Examples |
|----------------|------------------|----------|
| Simple (formatting, summaries) | Tier 1 (cheap) | gpt-4o-mini, haiku, gemini-flash |
| Medium (code review, Q&A) | Tier 2 (standard) | gpt-4o, sonnet |
| Complex (architecture, planning) | Tier 3 (premium) | gpt-4o, sonnet, gemini-pro |

### Rule 2: Fallback Chain

If the primary provider fails, fall back to the next in chain:

```
Primary: OpenAI (gpt-4o-mini)
  ↓ (if 429/500/timeout)
Fallback 1: Anthropic (claude-3-5-haiku)
  ↓ (if fails)
Fallback 2: Google (gemini-2.5-flash)
  ↓ (if all fail)
Error: "All AI providers unavailable"
```

### Rule 3: Provider-Specific Constraints

| Provider | Rate Limit | Context Window | Notes |
|----------|-----------|----------------|-------|
| OpenAI | 10,000 RPM (Tier 5) | 128K tokens | Most reliable |
| Anthropic | 4,000 RPM | 200K tokens | Largest context |
| AWS Bedrock | Per-region limits | Varies by model | Enterprise compliance |
| Azure OpenAI | Per-deployment limits | 128K tokens | Data residency |
| Gemini | 1,500 RPM | 1M tokens | Largest context window |
| Local | Unlimited | Model-dependent | No cost, slower |

---

## Configuration

### Environment Variables

```env
# Primary provider
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Fallback providers (optional)
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_KEY=...

# Local provider (optional)
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3.2
```

### Provider Configuration in Settings UI

The Settings page allows toggling between providers:

| Setting | Options | Default |
|---------|---------|---------|
| AI Provider | OpenAI, Anthropic, Bedrock, Azure, Gemini, Local | OpenAI |
| Model (per task) | Provider-specific model list | Provider default |
| Fallback enabled | On/Off | On |
| Max retries | 1-5 | 3 |
| Timeout (seconds) | 10-120 | 30 |

---

## Provider Interface Contract

All providers must implement this interface:

```python
class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Send a prompt and get a response."""
        pass
    
    @abstractmethod
    def get_model_list(self) -> list[str]:
        """Return available models for this provider."""
        pass
    
    @abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Calculate cost for the given usage."""
        pass
    
    @abstractmethod
    def get_context_window(self, model: str) -> int:
        """Return max context window for the model."""
        pass
```

---

## Switching Providers

### When to Switch

| Scenario | Action |
|----------|--------|
| Primary provider rate-limited | Auto-fallback |
| Provider has outage | Auto-fallback |
| Cost optimization needed | Admin changes default |
| Data residency requirement | Switch to Azure/Bedrock |
| Offline/air-gapped environment | Switch to Local |
| Context window too small | Switch to Gemini/Claude |

### How to Switch

1. **Automatic** — Fallback chain handles provider failures
2. **Manual (Settings UI)** — Admin changes default provider
3. **Per-request** — API supports `provider` parameter override
4. **Per-feature** — Configure different providers for different features

---

## Cost Comparison

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Best For |
|-------|----------------------|------------------------|----------|
| gpt-4o-mini | $0.15 | $0.60 | Simple tasks |
| gpt-4o | $2.50 | $10.00 | Complex analysis |
| claude-3-5-haiku | $0.25 | $1.25 | Fast, cheap |
| claude-3-5-sonnet | $3.00 | $15.00 | Best quality |
| gemini-2.5-flash | $0.15 | $0.60 | Large context |
| gemini-2.5-pro | $1.25 | $10.00 | Complex reasoning |
| Local (Ollama) | $0.00 | $0.00 | No cost, private |

---

## Vendor Lock-in Prevention

1. **Standard interface** — All providers implement the same abstract class
2. **Standard request/response** — Unified `LLMRequest` / `LLMResponse` models
3. **No provider-specific features** — Only use features available across providers
4. **Prompt format** — Use plain text/markdown prompts (no provider-specific XML/tags)
5. **Easy switching** — One environment variable change switches all calls
6. **Cost abstraction** — Token tracking works regardless of provider
