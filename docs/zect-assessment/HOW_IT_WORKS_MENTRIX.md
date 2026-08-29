# How Mentrix Works (User Guide)

Post-implementation guide for the Mentrix Best-in-Class UX + Lattice Intelligence plan.

## Day-to-day delivery workflow

1. **Login** to ZECT.
2. Bind a repo under **Projects** or **Repo Workspace**.
3. Optional: **Understand → Lattice Graph** → ingest path + project key.
4. Open **Workflow → Mentrix Delivery** (`/mentrix`).
5. Set workspace path + Lattice project key, pick mode (`deliver` / `upgrade` / `chat`…).
6. Type a goal → **Mentrix engage**.
7. Watch the **step rail**: Lattice → Plan/Build → Gates → Ultra Review → Approve → PR.
8. When gates are green → **Approve** → **Create PR**.

You do **not** paste code into Snippet Review for normal delivery. Mentrix Ultra Review runs automatically inside the run.

## Ultra Review surfaces

| Where | Use when |
|-------|----------|
| Mentrix run (automatic) | Build / upgrade / deliver — before Approve |
| Quality → Mentrix Ultra Review | Existing GitHub PR / repo scan |
| Deliver → Snippet Review | Manual paste only (lab / ad-hoc) |

## Lattice code intelligence

Lattice indexes files into a local JSON graph (no Neo4j). **Graphify-class depth ships as Lattice** — parse, path, explain, god-nodes — without a third-party graph install:

- Symbols, imports, **resolved imports**, **calls**
- **Endpoint / business** heuristic nodes (FastAPI/Flask/Express)
- **Structural RepoBlueprint** after ingest: tech stack, APIs, functions/classes, deps, configs
- APIs: query, path, neighbors, explain, god-nodes, blueprint + deep prompt, RAG search
- Mentrix Scout uses graph hits + structural blueprint + neighbor/explain packs
- Blueprint UI **From Lattice** prefers the deep prompt when a local index exists
- Repo Workspace clone → auto Lattice ingest → Mentrix workspace/project key autofill

## Desktop voice (Electron)

| Action | How |
|--------|-----|
| Wake | Say **Hey Mentrix** / **Mentrix engage** (Web Speech STT → IPC) |
| Hotkey fallback | `Ctrl/Cmd+Shift+Space` |
| Menu | Mentrix → Open Mentrix |
| TTS | Enable **Speak status (TTS)** on Mentrix page |

Browser-only local: type goals on `/mentrix` (no OS wake listening).

## Labs (Memory, Dream, Flywheel…)

Labs APIs require auth. Pages now use `apiFetch` with Bearer. They remain **experimental** — not the primary delivery path.

## What was fixed in this plan

- Assessment pack under `docs/zect-assessment/`
- Labs 401s (Bearer via `apiFetch`)
- Workflow sidebar → Mentrix Delivery
- Mentrix step rail + empty-state guidance
- Snippet Review rename + banner
- Lattice calls/path/neighbors/explain + scout enrichment
- Electron STT IPC + Mentrix TTS toggle
- Playwright: Mentrix step rail, Labs auth, Snippet Review

## Deferred (by design)

- Neo4j (JSON Lattice + Postgres/SQLite blueprints for v1)
- External graph CLI installs (Graphify-class depth is Lattice)
- Full Dream Engine production productization
- User-extensible hooks plugin framework
