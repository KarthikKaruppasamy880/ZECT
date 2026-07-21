# Mentrix Quality Preflight

Checked before Mentrix implementation (doctrine: reuse → deepen → replace).

## Reuse
- Auth UI: `backend/app/routers/auth.py`, `frontend/src/pages/Login.tsx`
- Agent Mode shell: `agent_mode.py`, `agent_orchestrator.py`, `AgentMode.tsx`
- Code Review: `code_review.py`, `review_service.py`
- Rules, Sandbox, Build, Repo Analysis, Memory, Electron, GitHub, token_tracker

## Replace / deepen
- MCP stub execute → live hub
- In-memory auth tokens → DB `auth_tokens` + middleware
- Dual `/api/review` → review-phase prefix split
- Regex code index → Lattice AST
- Prompt-only agent → Mentrix ForgeLoop

## Do not rewrite
- FastAPI/React app shells, Projects, Electron builder config
