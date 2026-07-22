# Mentrix Architecture

ZECT is the product. **Mentrix** is the user-facing agent. Internally:

| Layer | Name |
|-------|------|
| Graph | **Lattice** (Graphify-class, ZECT-native — symbols, imports, calls, path/explain, endpoints) |
| Runtime | **ForgeLoop** (custom FSM — **not LangGraph**) |
| Vectors | Postgres pgvector (JSON cosine fallback for SQLite/dev) |
| Tools | MCP hub (GitHub, Jira, Confluence, Slack, Datadog, Filesystem, Email) |
| Review | **Mentrix Ultra Review** (ZECT-branded; no third-party review product names) |
| Primary UX | **Workflow → Mentrix Delivery** (`/mentrix`) with step rail |

See also: [docs/zect-assessment/HOW_IT_WORKS_MENTRIX.md](zect-assessment/HOW_IT_WORKS_MENTRIX.md).

## Not LangGraph

Orchestration is a hand-rolled mode pipeline (`MODE_PIPELINE` in `backend/app/services/forge_loop/orchestrator.py`). Memory `next_step` / episodic “harness” tags are ZECT telemetry, not LangGraph.

## Agents (8)

1. Orchestrator — supervises the run  
2. Scout — Lattice + RAG  
3. Planner — plan + human gate  
4. Builder — Build Phase wrappers (`services/phases`)  
5. Reviewer — Mentrix Ultra Review + quality gates  
6. Fixer — scoped carry-forward autofix / recovery  
7. Integrator — MCP **execute** (Slack/email/Datadog outbound when goal asks)  
8. Ops — Datadog / ops queries (execute when configured)  

Users only see **Mentrix**.

## Upgrade mode (any language → any language)

```text
Goal → Lattice → Blueprint (design_contract) → Ask → Plan
  → API inventory → Mentrix Ultra Review (preflight)
  → Build (truncation-safe) → Grounding → incomplete-file
  → Acceptance/contract → Lint → Sandbox → Ultra Review (postflight)
  → API eval → (fail → error_classifier → Fixer) → Integrator MCP
  → Human Approve → Create PR (hard completion)
```

Callable wrappers live under `backend/app/services/phases/` so ForgeLoop does **not** HTTP self-call Ask/Plan/Build/Review routers.

### Anti-hallucination doctrine (Mentrix-native — not MinionBot)

| Defense | Module |
|---------|--------|
| Truncation-safe generate | `quality/truncation.py` — `finish_reason=length` continuation stitch + brace/AST |
| Grounding (invented API) | `quality/grounding.py` — AST/regex vs Lattice/blueprint allowlist |
| Design contract | Blueprint `design_contract` + `quality/acceptance.py` |
| Acceptance criteria | Satisfaction heuristics (not empty-field presence) |
| Error classifier | `quality/error_classifier.py` — SYNTAX/LOGIC/VALIDATION/TIMEOUT/SECURITY |
| Hard PR completion | create-pr re-checks gates; rejected files block |
| Acknowledge governance | Waiver audit events; security/secrets never waiveable |

### Gate doctrine — ship only when 100% green

LLMs can err. ZECT **refuses incomplete** work: a run cannot claim done or open a PR with missing files, failed lint, failed API evals, grounding/contract failures, or Mentrix Ultra Review critical findings (acknowledge only for sandbox/review/api_eval — never incomplete/contract/grounding/security).

| Gate | Mechanism |
|------|-----------|
| Truncation | `finish_reason` + structural checks on Build |
| Grounding | Invented API names fail gate |
| Incomplete files | `files_expected` vs `files_written`; deny-list TODOs / empty / truncated |
| Contract / acceptance | Required mentions + criteria satisfaction |
| Lint | `lint_runner`; upgrade defaults `MENTRIX_LINT_STRICT` |
| Sandbox | PR readiness policy |
| Mentrix Ultra Review | Critical findings block approve |
| API eval | Inventory + schema presence (+ optional HTTP smoke) |
| Human approve | `POST /api/mentrix/runs/{id}/approve` |
| Create PR | Hard re-check; requires `approved_at`; no silent partial ship |

### Golden eval harness (observability)

`quality/eval_harness.py` + `tests/fixtures/mentrix_golden/` score grounding/incomplete/acceptance offline. **Non-blocking** today (`GET /api/mentrix/eval/golden`); promote to merge gate once pass-rate signal is trusted.

### Live status

Mentrix UI polls `GET /api/mentrix/runs/{id}` and renders phase events (`phase`, `progress`, `next_step`).

## Delivery loop (codegen / bugfix)

```text
Goal → Scout → Planner → Builder → Lint → Sandbox → Reviewer
  → (on fail) Error → Fixer model → next_step (re_lint|re_sandbox|re_review|await_human)
  → Human Approve → Create PR
```

### Error recovery

Events look like:

```json
{
  "event": "recovery",
  "agent": "fixer",
  "error": "...",
  "model": "fixer",
  "next_step": "re_lint",
  "attempt": 1
}
```

Capped by `MENTRIX_MAX_RECOVERY` (default 3). After cap: status `needs_human`.

## MCP outbound (Wave 1)

When the user goal mentions Slack / email / Datadog, Integrator/Ops call `execute_tool`:

- `slack.send_message` (`SLACK_BOT_TOKEN`)
- `email.send_email` (`SMTP_*`)
- `datadog.query_logs` (`DATADOG_*`)

Rules Engine still blocks secrets. Enable adapters under Integrations UI (`/api/mcp/configs`).

**Wave 2 (out of this ship):** Slack Events inbound reply bot; email inbox poll.

## Prompt / context / harness

| Layer | Live behavior |
|-------|----------------|
| Prompts | Phase wrappers / review_service / autofix hold LLM system prompts; ForgeLoop injects Rules + `skills/*/SKILL.md` |
| Context | Scout uses Lattice + RAG; blueprint + Ask feed Plan/Build |
| Harness | Quality chain: incomplete → lint → sandbox → Ultra Review → API eval → approve → PR |

## Mentrix Companion (personal company agent)

- Route `/mentrix-home` — avatar, chat, Mentrix Board, Computer Mode toggle, always-ask confirms
- API: `/api/mentrix/companion/turn|tools|policy` — permission-brokered tools for research, content, reporting, docs, comms, Delivery, desktop
- Org policy export/import for shareable company installs
- See [`docs/MENTRIX_COMPANION.md`](MENTRIX_COMPANION.md)

## Lattice intelligence

Graphify-class code intelligence **ships as Lattice** inside ZECT — users never install a separate graph CLI or Neo4j.

- Indexer: `backend/app/services/lattice/indexer.py` — AST/regex parse, optional tree-sitter enrichment, resolved relative imports (`imports_file`), `calls` edges, `endpoint`/`business` nodes, path/neighbors/explain, god-nodes (degree) + connected-component communities
- Structural RepoBlueprint: `structural_blueprint.py` — APIs, symbols, deps, tech stack, configs, business_context; stored in `lattice_structural_blueprints`
- APIs: `/api/lattice/ingest|graph|query|path|neighbors|explain|god-nodes|communities|blueprint|blueprint/prompt|rag/search`
- Ingest builds/persists structural blueprint; Scout injects blueprint + neighbor/explain packs into ForgeLoop / Mentrix planning
- UI: Blueprint **From Lattice**, Lattice stats panel, Mentrix autofill from Repo Workspace (`zect_mentrix_workspace`)

## Review UX

| Surface | Role |
|---------|------|
| Mentrix ForgeLoop Ultra Review | Automatic gate on deliver/upgrade |
| Quality → Mentrix Ultra Review (`/code-review`) | PR/repo product review |
| Deliver → Snippet Review (`/review`) | Manual paste only |

## Wake phrases (desktop)

- Mentrix / Hey Mentrix / Mentrix engage (Web Speech STT → `mentrix-stt-transcript` IPC)
- Hotkey: `Ctrl/Cmd+Shift+Space`
- TTS: optional “Speak status” on Mentrix page (`speechSynthesis`)
- Matching helper: `electron/wake.js`

## Auth

`ZECT_AUTH_MODE=local|oidc|hybrid`. Bearer on `/api/*` except health, login, auth config, OIDC, GitHub review webhook.

Local/hybrid non-production: if `ZECT_USERNAME` / `ZECT_PASSWORD` unset → `admin@zect.local` / `zect-dev-local` (logged once at login). Never applied when `ENV=production`.

## Playwright E2E

```bash
cd frontend
npx playwright test
```

Covers login → Lattice → Mentrix (incl. upgrade chat) → Sandbox → Integrations and approve-to-PR gates.

## Fine-tune (Phase 9)

Preference samples via `/api/mentrix/fine-tune/*`. LoRA optional after RAG quality bar.

## Local verification

```bash
cd backend
# use a venv; set DATABASE_URL=sqlite:///./test_zect.db
pytest -q
```

CI: `.github/workflows/ci.yml` (pytest + frontend build + Playwright e2e).
