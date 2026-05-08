# ZECT E2E Testing & Review Playbook

Use this playbook to do a full end-to-end test and review of the ZECT application.

## Prerequisites
- ZECT repo cloned at `/home/ubuntu/repos/ZECT`
- Backend `.env` configured with `DATABASE_URL`, `GITHUB_TOKEN`, `ZECT_USERNAME`, `ZECT_PASSWORD`

## Steps

### 1. Start Backend Server
```bash
cd /home/ubuntu/repos/ZECT/backend
pip install -e ".[test]"
uvicorn app.main:app --reload --port 8001
```

### 2. Start Frontend Server
```bash
cd /home/ubuntu/repos/ZECT/frontend
npm install
VITE_API_URL=http://localhost:8001 npx vite --host 0.0.0.0 --port 5173
```

### 3. Login
- Navigate to `http://localhost:5173`
- Use credentials from `.env` (`ZECT_USERNAME` / `ZECT_PASSWORD`)

### 4. Test Each Page (15 pages)
For each page, navigate via sidebar and verify:
- Page loads without errors
- UI elements render (buttons, forms, tables, cards)
- Data comes from real backend API (not mocked)
- Empty states show correctly for fresh DB

**Pages to test:**
1. Dashboard (`/`) — Stats cards, projects grid, token usage
2. Ask Mode (`/ask`) — Conversation history, model selector, file attach
3. Plan Mode (`/plan`) — History sidebar, model selector with pricing
4. Build Phase (`/build`) — History sidebar, quick templates, auto-fix
5. Code Review (`/code-review`) — 5 tabs (PR/Snippet/Repo Scan/Auto-Fix/Webhook)
6. Knowledge Base (`/knowledge-base`) — Search, 8 categories, CRUD
7. Playbooks (`/playbooks`) — Category tabs, create/run playbooks
8. Scheduled Tasks (`/scheduled-tasks`) — Cron scheduling, toggle, trigger
9. Secrets Manager (`/secrets`) — Fernet encryption, scope-based access
10. Code Index (`/code-index`) — Symbol search, type/language filters
11. Session Insights (`/session-insights`) — 4 metric cards, time range filter
12. Conversations (`/conversations`) — Mode tabs, split-pane, archive
13. Settings (`/settings`) — API keys, 6 feature toggles, 4 config options
14. App Runner (`/app-runner`) — Terminal, configure, processes, live preview
15. Token Controls (`/token-controls`) — 5 tabs, per-user monitoring

### 5. Verify Backend APIs
```bash
curl -s http://localhost:8001/api/conversations | python3 -m json.tool
curl -s http://localhost:8001/api/knowledge | python3 -m json.tool
curl -s http://localhost:8001/api/playbooks | python3 -m json.tool
curl -s http://localhost:8001/api/schedules | python3 -m json.tool
curl -s http://localhost:8001/api/secrets | python3 -m json.tool
curl -s http://localhost:8001/api/code-index/stats | python3 -m json.tool
curl -s http://localhost:8001/api/session-insights/overview | python3 -m json.tool
```

### 6. Record Results
- Start screen recording before testing
- Annotate each page test with pass/fail
- Generate test report with screenshots
- Send recording + report to user

### 7. Sync Branches
```bash
git checkout develop && git push origin develop
# Create PR from develop to main or merge locally:
# git checkout main && git merge develop && git push origin main
```

---

## Troubleshooting

### Backend won't start
- Check `.env` file exists in `backend/` with correct `DATABASE_URL`
- Run `pip install -e ".[test]"` to ensure all dependencies installed
- Check port 8001 is free: `lsof -i :8001`

### Frontend won't start
- Run `npm install` in `frontend/`
- Check `VITE_API_URL` points to the running backend
- If port 5173 is busy, Vite auto-switches to 5174

### Login fails
- Verify `ZECT_USERNAME` and `ZECT_PASSWORD` in `backend/.env`
- Check backend is running and accessible at the configured port

### Empty pages
- Empty states with 0 items = fresh DB, NOT a bug
- Create test data via the UI or API to see populated views
