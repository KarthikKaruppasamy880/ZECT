# ZECT Free Models Configuration Guide

## Overview

ZECT supports **multiple AI model providers** — including completely free models via **OpenRouter**. This guide explains how to configure and use free models so your team can start using ZECT's AI features (Ask, Plan, Build, Review) at **zero cost**.

---

## Available Models in ZECT

### Free Models (via OpenRouter)

| Model | Provider | Quality | Speed | Cost |
|-------|----------|---------|-------|------|
| **Llama 3.1 8B** | Meta (via OpenRouter) | Good | Fast | **Free** |
| **Mistral 7B Instruct** | Mistral (via OpenRouter) | Good | Fast | **Free** |
| **Gemma 2 9B** | Google (via OpenRouter) | Good | Fast | **Free** |
| **Qwen 2.5 7B** | Qwen (via OpenRouter) | Good | Fast | **Free** |

### Paid Models

| Model | Provider | Quality | Speed | Cost (per 1K tokens) |
|-------|----------|---------|-------|---------------------|
| **GPT-4o Mini** | OpenAI | High | Fast | $0.00015 input / $0.0006 output |
| **GPT-4o** | OpenAI | Best | Medium | $0.005 input / $0.015 output |
| **GPT-3.5 Turbo** | OpenAI | Good | Fastest | $0.0005 input / $0.0015 output |
| **Claude 3.5 Sonnet** | Anthropic (via OpenRouter) | Best | Medium | $0.003 input / $0.015 output |
| **Claude 3 Haiku** | Anthropic (via OpenRouter) | Good | Fastest | $0.00025 input / $0.00125 output |

---

## Step 1: Get a Free OpenRouter API Key

1. Go to **[https://openrouter.ai](https://openrouter.ai)**
2. Click **"Sign Up"** (you can use Google/GitHub login)
3. Once logged in, go to **[https://openrouter.ai/keys](https://openrouter.ai/keys)**
4. Click **"Create Key"**
5. Name it something like `ZECT-dev`
6. Copy the key — it starts with `sk-or-v1-...`

> **Note:** OpenRouter gives you free credits for free-tier models. No credit card required.

---

## Step 2: Configure ZECT Backend

### Option A: Using `.env` file (Recommended for local development)

Edit `backend/.env` and add:

```env
# For free models via OpenRouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional: Also set OpenAI key if you want paid models too
# OPENAI_API_KEY=sk-your-openai-key-here
```

### Option B: Using environment variables

```bash
# Linux/Mac
export OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Windows PowerShell
$env:OPENROUTER_API_KEY = "sk-or-v1-your-key-here"

# Windows CMD
set OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Option C: Using Docker Compose

Edit `.env` in the project root:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Then restart:

```bash
docker compose down && docker compose up -d
```

---

## Step 3: Select Models in the UI

Every AI-powered page in ZECT has a **Model Selector** dropdown in the top-right corner:

1. Open any AI page: **Ask Mode**, **Plan Mode**, **Build Phase**, or **Review**
2. Click the **model dropdown** (shows current model like "GPT-4o Mini")
3. Free models are marked with a **"Free"** badge
4. Select any free model to use it at zero cost

### Model Selector Features

- Shows model name, provider, quality rating, and speed
- Free models highlighted with green "Free" badge
- Model selection persists per-page during your session
- Token usage tracked regardless of model choice

---

## Step 4: Verify Configuration

### Check API Status

```bash
# Check which providers are configured
curl http://localhost:8000/api/models/status
```

Expected response:
```json
{
  "openai_configured": false,
  "openrouter_configured": true,
  "available_providers": ["openrouter"]
}
```

### List Available Models

```bash
curl http://localhost:8000/api/models
```

### Test a Free Model

```bash
curl -X POST http://localhost:8000/api/models/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello, what is 2+2?"}],
    "model": "meta-llama/llama-3.1-8b-instruct:free",
    "feature": "test"
  }'
```

---

## How It Works Internally

### Provider Routing

ZECT automatically routes requests to the correct provider:

```
User selects model → ZECT checks provider → Routes to correct API
                                          ├─ OpenAI models → api.openai.com
                                          ├─ OpenRouter models → openrouter.ai/api/v1
                                          └─ Anthropic models → via OpenRouter
```

### API Key Fallback Logic

```
1. If model provider is "openai" → Uses OPENAI_API_KEY
2. If model provider is "openrouter" → Uses OPENROUTER_API_KEY
3. If OPENROUTER_API_KEY not set → Falls back to OPENAI_API_KEY
   (OpenAI keys work on OpenRouter for paid models)
```

This means if you only have an OpenAI key, you can still use OpenRouter models (but only paid ones, not free-tier).

---

## Recommended Setup for Teams

### Budget-Conscious Setup (Free Only)

```env
# backend/.env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
# No OpenAI key needed — use free models only
```

**Best for:** Teams evaluating ZECT, personal projects, learning

### Hybrid Setup (Free + Paid)

```env
# backend/.env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENAI_API_KEY=sk-your-openai-key-here
```

**Best for:** Teams that want free models for routine tasks and premium models for complex code review/generation

### Enterprise Setup (Full Access)

```env
# backend/.env
OPENAI_API_KEY=sk-your-openai-key-here
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Combined with Token Controls:
- Set daily/monthly token limits per user
- Set budget alerts at 80% threshold
- Enforce limits to prevent overspend
- Track usage by team, user, and model

---

## Token Controls Integration

ZECT tracks every API call regardless of model:

| Feature | What's Tracked |
|---------|---------------|
| **Per-call logging** | Model, tokens, cost, latency, feature used |
| **Daily/Monthly budgets** | Configurable per-user or global limits |
| **Usage trends** | 30-day charts by model, feature, team |
| **Cost alerts** | Notifications when usage hits threshold |
| **Model breakdown** | See which models consume the most tokens |

Access Token Controls at: **Sidebar → Token Controls**

---

## Troubleshooting

### "OpenAI API key not configured" error
- You need at least one API key set (`OPENAI_API_KEY` or `OPENROUTER_API_KEY`)
- After adding the key to `.env`, restart the backend server

### "Model API error" when using free models
- Free models on OpenRouter have rate limits (~20 requests/minute)
- Try a different free model if one is overloaded
- Wait 60 seconds and retry

### Models not showing in dropdown
- Ensure backend is running (`curl http://localhost:8000/api/models`)
- Check browser console for API errors
- Verify `.env` file is in the correct location (`backend/.env`)

### OpenRouter free models returning errors
- Some free models may be temporarily unavailable
- OpenRouter rotates free model availability
- Check [OpenRouter status](https://openrouter.ai/docs#models) for current availability

---

## Quick Reference

| What | Where |
|------|-------|
| Get OpenRouter key | [openrouter.ai/keys](https://openrouter.ai/keys) |
| Configure key | `backend/.env` → `OPENROUTER_API_KEY=...` |
| Select model in UI | Model dropdown (top-right of AI pages) |
| Check provider status | `GET /api/models/status` |
| List all models | `GET /api/models` |
| View token usage | Sidebar → Token Controls |
| Set budgets | Token Controls → Budget Settings |
