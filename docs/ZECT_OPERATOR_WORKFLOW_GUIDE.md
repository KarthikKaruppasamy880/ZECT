# ZECT Operator Workflow Guide

Step-by-step guide for any user to bring a repo into ZECT, understand it, fix bugs / upgrade, connect Jira incidents, review, open PRs, and deploy.

**Stack (local):** Backend `http://127.0.0.1:8000` · Frontend `http://127.0.0.1:5173` · Electron desktop (optional)  
**Login:** `admin@zect.local` / `zect-dev-local` (or your `ZECT_USERNAME` / `ZECT_PASSWORD` in `backend/.env`)

---

## 0. One-time setup

1. Copy `backend/.env.example` → `backend/.env` and set at least:
   - `OPENAI_API_KEY` (Mentrix / Ask / Plan)
   - `GITHUB_TOKEN` (clone private repos, create PRs, trigger deploy workflows)
   - Optional org integrations: `MCP_JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `DATADOG_API_KEY`, `DATADOG_APP_KEY`, `SLACK_BOT_TOKEN`
2. Start stack from repo root:
   - `.\RESTART_MENTRIX.ps1` (backend + frontend + Electron), or
   - Backend: `cd backend && py -3.12 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
   - Frontend: `cd frontend && npm run dev -- --host 127.0.0.1 --port 5173`
   - Electron: `cd electron && $env:ZECT_DEV='true'; $env:ZECT_DEV_URL='http://127.0.0.1:5173'; npm run start:dev`
3. Open **Integrations** → enable MCP servers (Jira, Datadog, GitHub, Slack, Playwright) that you configured.

---

## 1. Add / import / clone a repo

| Goal | Where | What to do |
|------|--------|------------|
| Register a project | **Projects** | Create/select a project (owner + name) |
| Clone from GitHub | **Repo Workspace** | Paste `owner/repo` or URL → Clone (needs `GITHUB_TOKEN` for private repos) |
| Use local folder | **Repo Workspace** / Mentrix workspace path | Point workspace at an existing clone under `ZECT_WORKSPACE_ROOT` |
| Set active context | Project selector (header) + Repo Workspace | Active project syncs Mentrix workspace + Lattice key (`owner-repo`) |

After clone: note **local path**, **project key** (e.g. `zinnia-zoas`), and Lattice status chip.

---

## 2. Understand the repo (Lattice → Blueprint)

1. **Lattice Graph** (`/lattice`)
   - Enter project key (or load from active project)
   - **Ingest + RAG** (first time) or **Load graph** (reload) once per repo
   - **Layers:** `combined` / `code` / `docs`
   - **Query** — symbol + RAG hits for Ask/Plan handoff
   - **Interactive graph** — click a node (or Fly to) to open the **Node details** inspector (name, kind, path, neighbors). **Explain** runs automatically and fills Path/Explain fields. Canvas shows a label on the selected node.
   - **Structural blueprint** + **Path / Explain** — architecture summary and A→B routes
2. **Code Index** (`/code-index`) — flat “go to symbol” search (function/class/variable). Use when you know a name; use Lattice when you need relationships, docs links, or Explain paths.
3. **Repo Analysis** (`/repo-analysis`) — tree + README-style overview
4. **Blueprint** (`/blueprint`)
   - Mode **From Lattice** → generate structural blueprint
   - Use **Use in Ask** / **Use in Plan** to carry context forward

Do this **once** per repo key; later Ask/Plan/Mentrix reuse it.

---

## 3. Ask → Plan → Build (classic Deliver path)

```text
Ask  →  Plan  →  Build  →  (optional) Review / Sandbox  →  Mentrix Delivery or Agent Mode  →  PR
```

1. **Ask** (`/ask`) — questions about the codebase (pass `repo_id` / Lattice context via workspace selector). Sticky blueprint: **Clear context** / **Reload from Lattice**.
2. **Plan** (`/plan`) — turn the ask into an implementation plan; same Clear / Reload controls as Ask.
3. **Doc Generator** (`/doc-generator`) — prefill owner/repo from header workspace; generate section docs via GitHub API + LLM (`GITHUB_TOKEN`). Not Mentrix Delivery / not Lattice Blueprint.
4. **Build** (`/build`) — generate/write code into the workspace when configured.
5. Prefer **Mentrix Delivery** (`/mentrix`) for gated upgrade/bugfix with Approve → Create PR. Check **Create real GitHub PR** only when you want dry-run off. Scorecard = grounded plan + gates green (never “100% / 0 error”).
6. Header **Presence** = collaboration WebSocket (online users), not Wi‑Fi.

---

## 4. Mentrix Delivery: upgrade or bugfix (ZOAS path)

Canonical path for ZOAS (or any gated Delivery repo):

```text
Clone → Lattice ingest → Engage (context pack) → Confirm plan → Build/gates
→ Approve → Create PR → Ultra Review + Semgrep check → fix residuals
```

1. Open **Mentrix Delivery** (`/mentrix`).
2. Confirm **Workspace path** + **Lattice project key** (auto from Repo Workspace). Context pack is required for upgrade/bugfix — Engage returns 400 if workspace/key (and Lattice index when enabled) are missing.
3. Set **Mode**:
   - `upgrade` — feature / port / enhancement
   - `bugfix` — targeted fix
4. Write a clear **goal** → **Mentrix engage**.
5. When status is **`awaiting_plan_confirm`**: review/edit the Fix Plan / Plan steps + files → **Confirm plan**. Build does not continue until confirmed. Scorecard language: *grounded plan + gates green* (never “100% / 0 error”).
6. Watch Live Status: Lattice → Plan → Build → Gates (lint, sandbox, Ultra Review, API eval, optional Semgrep) → Approve → PR.
7. When status is awaiting approval:
   - Review gates
   - Optionally acknowledge residual issues (does **not** waive `plan_confirmed`, `security_critical`, or checked Semgrep/`sast_ok` on create-pr)
   - **Approve** → **Create PR** (dry-run by default unless configured otherwise)
8. If `MENTRIX_SAST_REQUIRED=true`, after PR creation Mentrix polls GitHub Check Runs (Semgrep). Status may be **`awaiting_sast`** until green — use **Refresh SAST** (`POST /api/mentrix/runs/{id}/refresh-sast`) or the Ultra Review SAST panel.

**Agent Mode** (`/agent-mode`): same workspace; keep `build` in stages so Mentrix upgrade writes files; then **App Runner** to run locally.

---

## 5. Jira incident → fix → PR comment

1. Open **Mentrix Companion** → **Incident** tab, or sidebar **Incident Runbook** (`/mentrix-home?incident=1`). Same Companion shell — not a separate app.
2. Enter issue key (e.g. `INC-123`) → **Load** (needs Jira MCP env).
3. Optional: **Query Datadog** for related errors.
4. **Use in Mentrix Delivery** — prefills goal + issue key.
5. Engage upgrade/bugfix → **Confirm plan** → Approve → Create PR.
6. Comment PR URL on the ticket (Delivery can attempt this when issue key is set; or use Incident panel **Comment PR on ticket**).

Companion voice tools also understand: “Load Jira INC-123”, “search incidents”, “query Datadog logs …”.

---

## 6. Ultra Review + Semgrep SAST (quality / security)

1. **Quality → Mentrix Ultra Review** (`/code-review`).
2. Tabs:
   - **PR Review** — owner/repo/PR# → run Ultra Review (optionally post GitHub comments). Under PR Review, the **SAST (Semgrep)** panel reads GitHub Check conclusions for a branch/SHA (`GET /api/code-review/sast-status`). Enable Semgrep Cloud / Action on the GitHub repo; set `MENTRIX_SAST_REQUIRED` + `MENTRIX_SAST_CHECK_NAMES` in `backend/.env`.
   - **Snippet Review** — paste code for ad-hoc LLM Ultra Review. **Not a substitute for PR/CI SAST.**
   - **Full Repo / Auto-Fix / Webhook** — alternate paths
3. Mentrix Delivery already runs Ultra Review as a **gate** before Approve. Semgrep is a separate gate via GitHub Checks (not an in-process Semgrep CLI).
4. Fix findings:
   - Same PR: push more commits / re-run Mentrix with “fix Ultra Review findings on PR #N”
   - Or open a follow-up PR linked to the same Jira key via Incident Runbook

**Sandbox Gate** (`/sandbox`) — hard check before PR when required by policy.

---

## 7. Deploy (GitHub Actions → AWS)

1. Ensure the **GitHub repo** has a workflow (e.g. `deploy.yml`) that deploys to AWS (App Runner, ECS, etc.).
2. Open **Deploy** (`/deploy`).
3. Generate checklist/runbook if needed.
4. **Trigger workflow**: owner, repo, workflow file, ref, environment → triggers via GitHub API (`GITHUB_TOKEN`).
5. Permission broker may require **Allow** for deploy actions.
6. Watch GitHub Actions / AWS console for the actual deployment (ZECT triggers; AWS config lives in the repo’s workflow + cloud account).

---

## 8. Browser vs Electron (surfaces)

| Surface | Use for |
|---------|---------|
| **Browser** (`http://127.0.0.1:5173`) | Engineering: Mentrix Delivery, Lattice, Ultra Review, Plan/Build, Integrations. Board **Present / Narrate** works here; PPTX/Zoom Present Deck needs Electron. |
| **Electron** (`electron/` `npm run start:dev`) | Personal OS assistant: Computer Mode, PowerPoint/Zoom Present Deck, desktop screenshot/read, allowlisted app open, **write note** under Desktop/Documents |

- Delete / unlink / rmdir is **never** allowed (permissions + Electron refuse). Prefer `desktop_write_note` over fragile Notepad typing for docs.
- Mentrix Delivery in the browser does **not** need Computer Mode.
- Semgrep SAST stays on **GitHub Check Runs** (enable Semgrep Action/Cloud on the repo; ZECT reads conclusions). Not an in-process Semgrep CLI inside Mentrix Build.

---

## 9. Mentrix Companion (personal agent + Chatterbox voice)

One shell (`/mentrix-home`) with tabs: **Chat** | **Incident** | **Voice**. Sidebar **Incident Runbook** deep-links into Incident; Voice lives only inside Companion (no separate Labs entry).

| Task | How |
|------|-----|
| Chat / ops | Companion → **Chat** |
| Clone voice (Chatterbox) | Companion → **Voice** (`?voice=1`) → record/upload → **Save voice to ZECT** |
| Manage voices | List saved clones → **Use** (default for Present/sessions) or **Delete** anytime |
| Speak as you | TTS on + **Connect Voice**; **Present / Narrate** uses the **default** DB voice |
| Present Board (no files) | Companion → **Present / Narrate** — speaks Mentrix Board artifacts / last reply with Chatterbox (not PowerPoint files) |
| Prepared PPTX + Zoom | Companion → **Voice** → **Present Deck** — **Generate deck** (Presenton / `PRESENTON_BASE_URL`) or paste `.pptx` under Desktop/Documents/Downloads (OneDrive OK; strip quotes) → **Open presentation** → **Open Zoom** (optional join URL / `ZOOM_DEFAULT_JOIN_URL`) → **you** join the meeting and share PowerPoint → **Narrate talking points** with default clone. No Meeting SDK / auto-share. |
| Incident | Companion → **Incident** or `?incident=1` |
| Desktop notes | Electron Computer Mode → Allow write note file (never delete) |

**Present paths**

- **A. Mentrix Board** — ask Mentrix for a brief/artifacts → **Present / Narrate** (browser or Electron). No `.pptx` import.
- **B. Prepared PPTX + Zoom** — Electron Computer Mode opens PowerPoint + Zoom for a local deck; ZECT does **not** join Zoom or auto screen-share. You share the PowerPoint window.

**Persistence:** Samples + metadata are stored in ZECT (`cloned_voices` + `backend/data/voices/`). Present and Realtime sessions use the default clone via `/api/mentrix/voice/speak`. Local synthesis uses the Chatterbox engine (`CHATTERBOX_BASE_URL`, optional; legacy `VOICEBOX_BASE_URL` still accepted). The UI does not ask you to “connect Voicebox.” Last Present Deck path/notes are remembered in browser `localStorage` only.

**Long replies:** Connect Voice + cloned voice finalizes each OpenAI response once (no duplicate chat bubbles / double speak).

---

## 10. Models (choose different models)

ZECT exposes models via **`/api/models`** ([`backend/app/routers/model_selection.py`](../backend/app/routers/model_selection.py)):

- OpenAI: `gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo`
- Anthropic: `claude-sonnet-5`, `claude-3.5-sonnet`, `claude-3-haiku`

Usage is logged with `log_tokens()` into ZECT’s DB (token / cost tracking). Mentrix phases also select models per task when configured.

**Compared to task-based routing elsewhere:** some internal platforms auto-route by `task_type` and emit `llm_token_usage` to Datadog. ZECT today:

| Capability | ZECT today | Gap |
|------------|------------|-----|
| Multi-model registry | Yes (`/api/models`) | Wire every Mentrix phase to user-selected model |
| Token/cost in ZECT DB | Yes (`token_tracker`) | — |
| Datadog log facets for LLM usage | MCP can **query** Datadog; Mentrix does **not** auto-emit `llm_token_usage` like a full routing provider | Add structured Datadog emit on each LLM call if platform team requires parity |

Set `OPENAI_API_KEY` / Anthropic keys in `backend/.env`. Prefer a **ZECT service account** for shared org Jira/Datadog/GitHub.

---

## 11. Security & vulnerability process — what exists vs gaps

### What ZECT already does

- Ultra Review findings (bugs, vulns, CWE/OWASP-oriented categories)
- Semgrep via GitHub Check Runs (`sast_ok` when `MENTRIX_SAST_REQUIRED=true`)
- Rules Engine (`security` rule type) can block MCP / deploy actions
- Sandbox gate before PR
- Mentrix gates: plan confirm, incomplete / lint / sandbox / review / API eval / SAST + human Approve
- Audit trail for sensitive actions
- Secrets Manager page (org secrets; do not commit `.env`)
- Companion desktop: create/read allowlisted notes; **delete never**

### Gaps for “Zinnia platform review → production”

| Need | Status |
|------|--------|
| Continuous vuln feed (Dependabot / Snyk / GitHub Security Advisories) into Mentrix | Not automated — run Full Repo Ultra Review + Semgrep on GitHub + external scanners |
| Formal “Security ticket → evidence pack → platform review” workflow | Partial (Jira Incident + Delivery + PR comment); no dedicated Security queue UI |
| Signed approval + migration checklist for prod | Deploy checklist exists; no enforced multi-approver security sign-off |
| Auto-open Jira Security issues from Ultra Review criticals | Not built — manual create/link today |
| Datadog security signals → Incident Runbook | Manual Datadog query; not auto-linked |
| Separate QA environment gate before prod deploy | Depends on GitHub workflow environments; ZECT only triggers |

**Recommended operating model for vulns**

1. Full Repo / PR **Ultra Review** → export findings  
2. Create/link Jira (**Security** or Incident) via Integrations / Incident Runbook  
3. Mentrix `bugfix` with workspace + Lattice → **Confirm plan** → gates  
4. Same-PR fixes until gates green; Ultra Review the PR + **Semgrep** Check success  
5. Platform team review using Audit Trail + PR + Deploy checklist  
6. Trigger deploy workflow to **non-prod → QA → prod** environments in GitHub Actions  

---

## 12. MSTF / Code Red (MinionBot only)

ZECT does **not** implement Multi-Surface Transaction Fabric (MSTF) / Code Red multi-surface codegen. That ships in **MinionBot**. See `docs/MSTF_MULTI_SURFACE_TRANSACTION_FABRIC.md` and Docs Center → MSTF. Mentrix may call MinionBot APIs later; do not add Lattice into MinionBot for this gap.

---

## Quick path cheat sheet

| I want to… | Go to |
|------------|--------|
| Clone a repo | Repo Workspace |
| See graph | Lattice |
| Spec from graph | Blueprint (From Lattice) |
| Q&A | Ask |
| Implementation plan | Plan |
| Generate code | Build or Mentrix Delivery / Agent Mode |
| ZOAS Delivery | Mentrix: Engage → Confirm plan → Approve → PR → Semgrep |
| Fix from Jira | Incident Runbook → Mentrix Delivery |
| Deep review | Mentrix Ultra Review (+ SAST panel) |
| Ship | Approve → Create PR → Deploy trigger |
| Desktop assistant | Electron Computer Mode (write notes; never delete) |
| My voice | Mentrix Companion → Voice (Chatterbox) |
| Symbol search | Code Index |
| Graph + Explain | Lattice (click node → inspector) |
| MSTF / Code Red | MinionBot (docs/MSTF_…) — not ZECT |