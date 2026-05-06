# ZECT — Deployment Prompts for AI Agents

Ready-to-use prompts for any AI agent to deploy ZECT to various environments.

---

## Prompt: Local Windows Setup (PostgreSQL)

```
Set up the ZECT application locally on Windows with PostgreSQL.

Steps:
1. Navigate to C:\Users\karuppk\Downloads\ZECT
2. Backend setup:
   - cd backend
   - poetry install (or pip install -r requirements.txt if no Poetry)
   - Create .env file from .env.example
   - Set DATABASE_URL=postgresql://postgres:MY_PASSWORD@localhost:5432/zect_db
   - Set GITHUB_TOKEN=ghp_xxx
   - Set OPENAI_API_KEY=sk-xxx
   - Set ZECT_USERNAME=admin@company.com
   - Set ZECT_PASSWORD=SecurePass!
   - Run: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

3. Frontend setup (new terminal):
   - cd frontend
   - npm install
   - npm run dev

4. Create PostgreSQL database if not exists:
   - psql -U postgres
   - CREATE DATABASE zect_db;

5. Open http://localhost:5173 in browser
6. Backend API at http://localhost:8000/health

The app auto-creates all tables and seeds demo data on first start.
```

---

## Prompt: Deploy to AWS EC2

```
Deploy the ZECT application to an AWS EC2 instance.

Requirements:
- EC2: Ubuntu 24.04 LTS, t3.medium
- Database: RDS PostgreSQL 16 (db.t3.micro)
- Web server: Nginx as reverse proxy
- Process manager: systemd

Steps:
1. SSH into EC2 instance
2. Install Python 3.12, Node.js 20, Poetry, Nginx
3. Clone repo: git clone https://github.com/KarthikKaruppasamy880/ZECT.git
4. Backend: cd ZECT/backend && poetry install && create .env with DATABASE_URL pointing to RDS
5. Frontend: cd ZECT/frontend && npm install && npm run build
6. Create systemd service for uvicorn (4 workers, port 8000)
7. Configure Nginx:
   - Serve frontend/dist as static files at /
   - Proxy /api/* and /auth/* to localhost:8000
8. Enable HTTPS with certbot
9. Start services: systemctl start zect-backend && systemctl reload nginx

Refer to docs/EC2_DEPLOYMENT_GUIDE.md for full configuration details.
```

---

## Prompt: Deploy to AWS ECS/Fargate

```
Deploy the ZECT application to AWS ECS with Fargate (serverless containers).

Requirements:
- ECS Cluster with Fargate launch type
- ECR repositories for backend and frontend images
- RDS PostgreSQL 16 (Multi-AZ for production)
- Application Load Balancer
- AWS Secrets Manager for credentials

Steps:
1. Create ECR repositories: zect-backend, zect-frontend
2. Build Docker images:
   - backend/Dockerfile: Python 3.12 + Poetry + uvicorn
   - frontend/Dockerfile: Node 20 build + Nginx serve
3. Push images to ECR
4. Create RDS PostgreSQL instance (db.t3.micro, 20GB)
5. Store secrets in AWS Secrets Manager:
   - zect/production/database (DATABASE_URL)
   - zect/production/api-keys (GITHUB_TOKEN, OPENAI_API_KEY)
   - zect/production/auth (ZECT_USERNAME, ZECT_PASSWORD)
6. Create ECS cluster: zect-production
7. Register task definitions (backend: 512 CPU/1024 MEM, frontend: 256 CPU/512 MEM)
8. Create ALB with path-based routing (/api/* → backend, /* → frontend)
9. Create ECS services (desired count: 2 each)
10. Configure auto-scaling (CPU target: 70%)

Refer to docs/ECS_DEPLOYMENT_GUIDE.md for full configuration details.
```

---

## Prompt: Set Up CI/CD Pipeline

```
Set up a GitHub Actions CI/CD pipeline for ZECT that:

1. On push to develop branch:
   - Run ESLint on frontend
   - Run TypeScript type check
   - Run backend tests (if any)
   - Build frontend (npm run build)
   - Report status

2. On push to main branch:
   - All of the above, plus:
   - Build Docker images
   - Push to ECR
   - Update ECS services (rolling deployment)

3. Required GitHub Secrets:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - AWS_REGION (us-east-1)

Create .github/workflows/ci.yml and .github/workflows/deploy-ecs.yml
Refer to docs/ECS_DEPLOYMENT_GUIDE.md for the deploy workflow template.
```

---

## Prompt: Configure PostgreSQL Database

```
Configure PostgreSQL for the ZECT application.

I have PostgreSQL already installed locally. 

1. Connect to PostgreSQL: psql -U postgres
2. Create database: CREATE DATABASE zect_db;
3. (Optional) Create dedicated user:
   CREATE USER zect_user WITH PASSWORD 'ZectSecure2026!';
   GRANT ALL PRIVILEGES ON DATABASE zect_db TO zect_user;
   ALTER DATABASE zect_db OWNER TO zect_user;
4. Update backend/.env:
   DATABASE_URL=postgresql://postgres:MY_PASSWORD@localhost:5432/zect_db
5. Restart the backend server

The ZECT app (SQLAlchemy ORM) auto-creates these tables on startup:
- projects (engineering projects with stages, completion tracking)
- repos (GitHub repository connections)
- settings (feature toggles and configuration)
- token_logs (LLM API usage audit trail with cost tracking)

Demo data (6 projects, 2 repos, 10 settings) is seeded automatically.
```

---

## Prompt: Add OpenAI API Key

```
Configure the OpenAI API key for ZECT's AI features.

1. Get an API key from https://platform.openai.com/api-keys
2. Edit backend/.env file
3. Set: OPENAI_API_KEY=sk-your-key-here
4. Restart the backend server

This enables:
- Code Review Engine (AI-powered PR analysis)
- Ask Mode (conversational AI for engineering questions)
- Plan Mode (AI-generated engineering plans)
- Blueprint AI Enhancement (intelligent project analysis)
- Doc Generator AI Enhancement

All token usage is tracked in the token_logs table with:
- Model name, token counts, estimated cost
- Audit trail for compliance

Security: The key is stored only in .env (gitignored), used server-side only, 
never exposed to the frontend or browser.
```

---

## Prompt: Full Project Health Check

```
Perform a full health check on the ZECT application.

1. Backend:
   - curl http://localhost:8000/health → should return {"status": "ok"}
   - curl http://localhost:8000/api/projects → should return 6 projects
   - curl http://localhost:8000/api/settings → should return 10 settings
   - Check database connection is working

2. Frontend:
   - Open http://localhost:5173
   - Verify Dashboard loads with project cards
   - Navigate to all 15 sidebar pages
   - Check browser console for errors (should be 0)

3. Database:
   - Connect to PostgreSQL
   - Verify tables exist: projects, repos, settings, token_logs
   - Check row counts match expected values

4. AI Features (requires OPENAI_API_KEY):
   - Test Code Review: POST /api/code-review/snippet with sample code
   - Test Ask Mode: POST /api/llm/ask with a question
   - Check token_logs table for new entries after calls

Report any issues found with error messages and suggested fixes.
```
