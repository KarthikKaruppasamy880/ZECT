# ZECT Environment Setup Guide

Step-by-step commands to configure ZECT for local development and production deployment.

---

## 1. Prerequisites

```bash
# Required
node --version   # v18+ required
python --version # 3.12+ required
pip install poetry
```

## 2. Clone the Repository

```bash
git clone https://github.com/KarthikKaruppasamy880/ZECT.git
cd ZECT
```

## 3. Backend Setup

```bash
cd backend

# Install dependencies
poetry install

# Create .env file
cat > .env << 'EOF'
# === Required ===
ZECT_USERNAME=your.email@company.com
ZECT_PASSWORD=YourSecurePassword

# === GitHub Integration (required for Repo Analysis, Blueprint, Doc Generator) ===
# Create at: https://github.com/settings/tokens
# Scopes needed: repo (read)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# === OpenAI Integration (required for Ask Mode, Plan Mode, Blueprint AI Enhancement) ===
# Get key at: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF

# Start the backend
poetry run fastapi dev app/main.py
# Backend runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cat > .env << 'EOF'
# For local development:
VITE_API_URL=http://localhost:8000

# For production (replace with your deployed backend URL):
# VITE_API_URL=https://your-backend.fly.dev
EOF

# Start the frontend
npm run dev
# Frontend runs at http://localhost:5173
```

## 5. API Keys Configuration

### GitHub Personal Access Token (PAT)

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Select scopes: `repo` (read access)
4. Copy the token (starts with `ghp_`)
5. Add to backend `.env` as `GITHUB_TOKEN=ghp_...`
6. **OR** configure at runtime: Go to **Settings** in the ZECT UI and click **Configure** under "GitHub API Key"

### OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Click **"Create new secret key"**
3. Copy the key (starts with `sk-`)
4. Add to backend `.env` as `OPENAI_API_KEY=sk-...`
5. **OR** configure at runtime: Go to **Settings** in the ZECT UI and click **Configure** under "OpenAI API Key"

> **Note:** Runtime configuration (via Settings UI) does not persist across server restarts. For permanent configuration, use the `.env` file.

## 6. What Each Key Enables

| Feature | GitHub Token | OpenAI Key | No Keys |
|---------|:---:|:---:|:---:|
| Dashboard | - | - | Works |
| Projects CRUD | - | - | Works |
| Analytics | - | - | Works |
| Settings | - | - | Works |
| Repo Analysis | Required | - | Public repos only (60 req/hr) |
| Blueprint Generator | Required | - | Public repos only |
| Blueprint AI Enhancement | Required | Required | Not available |
| Doc Generator | Required | - | Public repos only |
| Ask Mode | - | Required | Not available |
| Plan Mode | - | Required | Not available |
| Orchestration | Required | - | Public repos only |
| PR Viewer | Required | - | Not available |

## 7. Production Deployment

### Backend (Fly.io)

```bash
cd backend

# Set environment variables on Fly.io
fly secrets set ZECT_USERNAME="your.email@company.com"
fly secrets set ZECT_PASSWORD="YourSecurePassword"
fly secrets set GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
fly secrets set OPENAI_API_KEY="sk-xxxxxxxxxxxx"
```

### Frontend

```bash
cd frontend

# Update .env with deployed backend URL
echo "VITE_API_URL=https://your-backend.fly.dev" > .env

# Build
npm run build

# Deploy the dist/ folder to your static hosting (Vercel, Netlify, CDN, etc.)
```

## 8. Verify Setup

```bash
# Test backend health
curl http://localhost:8000/healthz
# Expected: {"status":"ok"}

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your.email@company.com","password":"YourSecurePassword"}'
# Expected: {"token":"...","username":"..."}

# Test GitHub integration
curl -X POST http://localhost:8000/api/analysis/repo \
  -H "Content-Type: application/json" \
  -d '{"owner":"KarthikKaruppasamy880","repo":"ZECT"}'
# Expected: repo analysis JSON

# Test LLM integration
curl -X GET http://localhost:8000/api/llm/status
# Expected: {"configured":true,"model":"gpt-4o-mini"}
```

## 9. Troubleshooting

| Issue | Solution |
|-------|----------|
| `401 Invalid credentials` | Check `ZECT_USERNAME` and `ZECT_PASSWORD` in `.env` |
| `404 Repository not found` | Check `GITHUB_TOKEN` is set and has `repo` scope |
| `403 Rate limit exceeded` | Add a `GITHUB_TOKEN` (unauthenticated limit is 60 req/hr) |
| `503 OpenAI API key not configured` | Add `OPENAI_API_KEY` to `.env` or configure in Settings |
| `502 OpenAI API error` | Check your OpenAI API key is valid and has credits |
| Frontend can't connect to backend | Check `VITE_API_URL` in frontend `.env` matches backend URL |
