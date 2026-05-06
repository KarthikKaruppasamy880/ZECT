# Model Configuration Guide

## How to Configure LLM Models in ZECT

ZECT supports multiple LLM providers including **free models**. This guide shows you step-by-step how to configure each provider.

---

## Step 1: Navigate to Backend Configuration

All API keys go in `backend/.env` file:

```bash
# Windows (from your ZECT folder)
cd backend
notepad .env

# Mac/Linux
cd backend
nano .env
```

---

## Step 2: Configure Providers

### Option A: OpenAI (Paid Models)

**Models Available:** GPT-4o, GPT-4o Mini, GPT-3.5 Turbo

1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key and add to `backend/.env`:

```env
OPENAI_API_KEY=sk-your-openai-key-here
```

**Pricing:**
| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| GPT-4o Mini | $0.15 | $0.60 |
| GPT-4o | $5.00 | $15.00 |
| GPT-3.5 Turbo | $0.50 | $1.50 |

---

### Option B: OpenRouter (Free + Paid Models)

**Free Models Available:** Llama 3.1 8B, Mistral 7B, Gemma 2 9B, Qwen 2.5 7B
**Paid Models Available:** Claude 3.5 Sonnet, Claude 3 Haiku, GPT-4o, and 100+ more

1. Go to https://openrouter.ai/keys
2. Sign up (free account gives you access to free models)
3. Create an API key
4. Add to `backend/.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key-here
```

**Free Models (no credit card needed):**
| Model | Quality | Speed | Cost |
|-------|---------|-------|------|
| Llama 3.1 8B | Good | Fast | FREE |
| Mistral 7B | Good | Fast | FREE |
| Gemma 2 9B | Good | Fast | FREE |
| Qwen 2.5 7B | Good | Fast | FREE |

---

### Option C: Both (Recommended)

For maximum flexibility, configure both:

```env
OPENAI_API_KEY=sk-your-openai-key-here
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key-here
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/zect_db
```

This gives you access to ALL models — choose per-task in the UI.

---

## Step 3: Select Models in the UI

After configuring keys, every AI page (Ask, Plan, Build, Review) has a **Model Selector** dropdown:

1. Open ZECT in browser (`http://localhost:5173`)
2. Navigate to any AI page (Ask Mode, Plan Mode, Build Phase, Review Phase)
3. Look for the "Model Selection" dropdown
4. Choose your preferred model:
   - **Free Models** — Use for exploration, planning, simple queries
   - **GPT-4o Mini** — Best value for most tasks
   - **GPT-4o / Claude 3.5 Sonnet** — Best quality for critical reviews

---

## Step 4: Set Budget Limits (Optional)

Navigate to **Token Controls** in the sidebar to:

1. Set daily/monthly token limits
2. Set cost budgets (USD)
3. Choose preferred default model
4. Get alerts when usage hits threshold

---

## Step 5: Verify Configuration

1. Start the backend: `cd backend && poetry run uvicorn app.main:app --reload`
2. Visit `http://localhost:8000/api/models/status` to check which providers are configured
3. Visit `http://localhost:8000/api/models` to see all available models

---

## Configuration Summary

```env
# backend/.env — Full configuration example

# Required: At least one of these
OPENAI_API_KEY=sk-your-openai-key-here
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key-here

# Database (PostgreSQL)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/zect_db

# Optional: GitHub token for repo analysis
GITHUB_TOKEN=ghp_your-github-token-here
```

---

## Using an Existing OpenAI API Key

If you already have an OpenAI API key from another tool or subscription:
1. Locate your existing OpenAI API key
2. Copy the key
3. Paste into `backend/.env` as `OPENAI_API_KEY`

Note: Any valid OpenAI API key works in ZECT regardless of where it was originally created.

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| "OpenAI API key not configured" | Add `OPENAI_API_KEY` to `backend/.env` |
| "No API key configured" | Add either `OPENAI_API_KEY` or `OPENROUTER_API_KEY` |
| Free models not working | Add `OPENROUTER_API_KEY` (get free at openrouter.ai/keys) |
| 429 Rate Limit | Wait 60s or switch to a different model |
| Model not available | Check your API key has access to that model |

---

## Security Notes

- Never commit `.env` files to git (already in `.gitignore`)
- Never share API keys in chat or code
- Use environment variables in production (EC2/ECS)
- Rotate keys regularly
- Set budget limits to prevent accidental overuse
