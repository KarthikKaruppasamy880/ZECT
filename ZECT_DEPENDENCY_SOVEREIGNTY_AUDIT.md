# ZECT Dependency Sovereignty Audit (S1)

**Date:** 2026-08-14  
**Spec:** `prompts/ZECT_OSS_SOVEREIGNTY_NATIVE_ENGINES_PLAN.md` (S1 only)  
**Git:** `develop` = `origin/develop` = `98e19e64045543ea306d7e1ff003e9df9992d9ef`  
**PR #150:** merged (Core UX). Presenton **not** removed. S2 implemented on `feat/present-s2-template-provider` (see `ZECT_PRESENT_S2_ACCEPTANCE.md`). Native generate **not** claimed.  
**Companion plan:** `ZECT_NATIVE_PRESENTATION_ENGINE_PLAN.md`

## Verdict

**S1 recommendation for native presentation work: GO**

Proceed to S2 (Template Intelligence + introduce `PresentationProvider`) against this SHA using the reconciled plan. Do not remove Presenton. Do not start S2 in this session.

Overall sovereignty status: **SOVEREIGNTY_PARTIAL** — audit complete; native engine not implemented; several legal/pin items remain and do not block S2.

### Why GO (not REVISE / BLOCKED)

- Differentiated Present IP (UI, canonical template ids, registry, notes sidecar, zip/XML parse, audience/claims/sensitivity) is already ZECT-owned.
- Presenton is an unpinned HTTP engine for **prompt → PPTX bytes** only. That is the correct `REPLACE_WITH_ZECT_NATIVE` target.
- No GPL/AGPL/LGPL fields in `frontend/package-lock.json` or `electron/package-lock.json` production/dev trees.
- Copyleft that exists (PyGithub LGPL, ClamAV GPL-2.0, Git GPL-2.0) is **outside** the presentation generate path.
- Legal flags below are real but do not prevent introducing a provider interface and a native template importer.

**REVISE was applied inside the native plan**, not as a stop: the original roadmap assumed a `PresentationProvider` ABC that **does not exist** on this SHA (`presenton_client.generate_presentation` is called directly).

## Method (licenses not guessed)

| Source | What was read |
|--------|----------------|
| `frontend/package-lock.json` + `node_modules/*/LICENSE` | Direct npm deps, pinned versions |
| `electron/package-lock.json` + `electron/node_modules/electron/LICENSE` | Electron 28.3.3 MIT text |
| `backend/poetry.lock` | Docker/backend pins |
| `backend/requirements.txt` | NSIS sidecar install list (unpinned lower-bounds) |
| Installed `importlib.metadata` classifiers | Local venv evidence (may lag lock) |
| PyPI JSON | FastAPI 0.136.0 `license_expression=MIT`; PyGithub 2.9.1 LGPL classifier + `COPYING.LESSER`; atlassian-python-api 3.41.21 Apache-2.0; slack-sdk 3.34.0 MIT (lock is 3.41.0, same project); python-pptx 1.0.2 MIT (candidate, **not** a current dep) |
| https://raw.githubusercontent.com/presenton/presenton/main/LICENSE | Apache-2.0, Copyright 2025 presenton |
| https://raw.githubusercontent.com/resemble-ai/chatterbox/master/LICENSE | MIT (code). Model weights **not** in that file |
| Cisco-Talos/clamav `COPYING.txt` + GitHub license metadata | GPL-2.0 |
| `THIRD_PARTY_NOTICES.md`, `services/zect-voicebox/LICENSE`, `NOTICE` | Product notices |
| Docker/compose files | Runtime images; Presenton **not** in-repo compose |

Hiding provider branding does **not** remove license obligations. `THIRD_PARTY_NOTICES.md` must stay for any distribution that included those components.

## Landscape facts (current develop)

1. **Two Python manifests.** Docker (`backend/Dockerfile`) installs **Poetry**. NSIS sidecar (`backend/packaging/bundle_sidecar.py`) installs **`requirements.txt`**. Pins diverge (e.g. FastAPI poetry `0.136.0` vs installed/local `0.115.0`; openai poetry `2.33.0`).
2. **Presenton is not vendored.** Operator runs `ghcr.io/presenton/presenton:latest` (`docs/PRESENTON_LOCAL.md`). ZECT talks HTTP only. Image tag is **unpinned**.
3. **No `PresentationProvider` type** in the tree. Wire calls: `GET /api/v1/ppt/template/all`, `POST /api/v1/ppt/presentation/generate`, `POST /api/v1/auth/login`, GET download URL.
4. **User PPTX upload does not push to Presenton.** Registry stores bytes under `.zect/present-templates/`; `presenton_template_id` stays unset until an admin bind.
5. **PPTX parse/export today** uses stdlib `zipfile` + XML (`pptx_parse.py`) and allowlisted file download. Notes persist in a sidecar. There is **no** python-pptx / layout renderer.
6. **Playwright** is a frontend **devDependency** (e2e) and an optional backend adapter **not** listed in `requirements.txt`.
7. **ClamAV** is optional compose (`clamav/clamav:1.4`), not in the Electron extraResources list.
8. `backend/pyproject.toml` authors still say `Devin AI <…@users.noreply.github.com>` — content-ownership defect, not an OSS engine.

---

## Decision table

Columns: Dependency | Purpose | Where used | License (evidence) | Distributed? | External only? | User branding? | Data boundary | Replaceability | Lock-in | Maintenance | Differentiation | Decision | Priority

### A. Presentation / Voice / Desktop (S2–S8 / S10 relevant)

| Dependency | Purpose | Where used | License | Distributed? | External only? | User branding? | Data boundary | Replaceability | Lock-in | Maintenance | Differentiation | Decision | Priority |
|------------|---------|------------|---------|--------------|----------------|----------------|---------------|----------------|---------|--------------|-----------------|----------|----------|
| Presenton (`ghcr.io/presenton/presenton:latest`) | Prompt → outline/slides/template apply → PPTX bytes | `presenton_client.py`, Mentrix `/presenton/*`, `/present` Generate | Apache-2.0 (upstream `LICENSE` on `main`, Copyright 2025 presenton). **Image unpinned** | Not in ZECT installer today. Operator Docker | Yes (HTTP `PRESENTON_BASE_URL`) | Hidden (notices only) | Prompt + template id leave ZECT; PPTX returns as bytes; Presenton may call **its own** LLM (`OPENAI_API_KEY` in container) | High behind a new provider ABC | **High** for generate | Upstream 0.9+ auth/428 | Engine, not product | **REPLACE_WITH_ZECT_NATIVE** (keep runtime until S8 D) | P0 |
| Presenton built-in ids `general/modern/standard/swift` | Fallback template names | `BUILTIN_TEMPLATES` | Same Apache-2.0 engine | N/A | Yes | Hidden | Provider ids must not be canonical ZECT ids | Native TemplateDefinition | High if treated as Zinnia | Low | None | **REMOVE** from Zinnia PASS path (already). Keep only as PresentonProvider fallback | P0 |
| ZECT Present UI / editor / gallery | Product surface | `ZectPresent.tsx`, `PresentEditor.tsx`, `PresentDeckPanel.tsx` | ZECT | Yes | No | ZECT | Canonical UI state | N/A — own it | Low | ZECT | **High** | KEEP (ZECT IP) | — |
| Template registry | Canonical ids + mapping file | `template_registry.py`, `.zect/present-templates/` | ZECT | Mapping/PPTX on disk | Mapping may store provider UUID | Hidden | Must survive provider swap | Native TemplateDefinition extends this | Medium until provider ids gone from mapping | ZECT | **High** | KEEP; extend in S2 | P0 |
| stdlib zipfile/XML PPTX parse | Slide text + notes | `pptx_parse.py` | Python PSF | Yes (stdlib) | No | No | Local files | Commodity OOXML lib later | Low | stdlib | Low (parse only) | **KEEP_AS_LIBRARY** | P2 |
| python-pptx (not installed) | Candidate S4 renderer | none yet | MIT (PyPI 1.0.2 classifier) | Would ship in sidecar if added | No | No | Local PPTX | Other OOXML stacks | Low | Active | Medium (renderer primitive, not product) | **KEEP_AS_LIBRARY** when added at S4 — do not add in S1 | P1 |
| Voicebox service | Clone TTS HTTP | `services/zect-voicebox`, port 17493 | ZECT code + MIT adapted NOTICE | Optional Docker / extraResources chatterbox scripts | Runtime | Mentrix/ZECT | Audio + profiles local | VoiceProvider | Medium | ZECT | High (router/FSM) | **KEEP_AS_RUNTIME** (ZECT service) | P2 |
| chatterbox-tts `>=0.1.0` | Zero-shot synth | Voicebox `requirements-ml.txt` | **Code** MIT (ResembleAI LICENSE). **Weights** not in LICENSE file | Weights downloaded to HF cache, not in git | Model download | Hidden | Voice samples / models | Other VoiceProvider | High for clone quality | ResembleAI | Low (commodity ML) | **KEEP_AS_LIBRARY** (synth) + **NEEDS_LEGAL_REVIEW** (weights/commercial) | P1 |
| PyTorch CPU wheels | ML runtime | Voicebox Dockerfile | BSD-style (typical; **not** re-read from a local LICENSE this session — flag) | Voicebox image | No | No | Models | Other tensors | High | Meta | None | **KEEP_AS_RUNTIME** + confirm LICENSE file at S10 | P2 |
| ffmpeg / libsndfile | Audio decode | Voicebox Dockerfile apt | LGPL/GPL mix typical for ffmpeg — **NEEDS_LEGAL_REVIEW** if Voicebox image is redistributed | Voicebox image | No | No | Audio | OS packages | Medium | Distro | None | **KEEP_AS_RUNTIME** + **NEEDS_LEGAL_REVIEW** if shipped | P2 |
| Electron `28.3.3` | Desktop shell | `electron/` | MIT (`electron/LICENSE` on disk) | Yes (NSIS) | No | App id `com.zinnia.zect` | Local | Tauri/etc. not in scope | High for desktop | Electron | None | **KEEP_AS_RUNTIME** | P3 |
| Chromium (bundled by Electron / Playwright) | Browser engine | Electron dist; Playwright e2e | BSD + third-party (Electron `dist/LICENSE`) | Yes in desktop | No | No | Local | Do not rewrite | High | Chromium | None | **KEEP_AS_RUNTIME** | P3 |
| Git CLI | Worktrees, commits, push | `multi_repo_agent.py`, LRR, tests | GPL-2.0 (Git project) | **Not** copied into extraResources (host Git) | Host tool | No | Repo contents | Keep Git | High | Git | None | **KEEP_AS_RUNTIME** | P3 |

### B. Backend libraries (Poetry lock unless noted)

| Dependency | Purpose | Where used | License | Distributed? | External only? | User branding? | Data boundary | Replaceability | Lock-in | Maintenance | Differentiation | Decision | Priority |
|------------|---------|------------|---------|--------------|----------------|----------------|---------------|----------------|---------|--------------|-----------------|----------|----------|
| FastAPI `0.136.0` | HTTP API | backend | MIT (`license_expression` PyPI 0.136.0) | Yes (sidecar via requirements) | No | No | App data | Starlette stack | Medium | Tiangolo | None | **KEEP_AS_LIBRARY** | P3 |
| uvicorn `0.46.0` | ASGI | backend / Voicebox | BSD-3-Clause (installed 0.32 metadata; project BSD) | Yes | No | No | — | Any ASGI | Low | Encode | None | **KEEP_AS_LIBRARY** | P3 |
| SQLAlchemy `2.0.49` | ORM | models | MIT (installed classifier) | Yes | No | No | DB | Other ORM | Medium | SQLAlchemy | None | **KEEP_AS_LIBRARY** | P3 |
| Alembic `1.18.4` | Migrations | backend | MIT (installed) | Yes | No | No | Schema | — | Medium | SQLAlchemy | None | **KEEP_AS_LIBRARY** | P3 |
| Pydantic 2.x | Validation | schemas | MIT (installed 2.9.2) | Yes | No | No | — | — | Medium | Pydantic | None | **KEEP_AS_LIBRARY** | P3 |
| httpx `0.28.1` | HTTP client | Presenton, Camunda, etc. | BSD-3-Clause (installed) | Yes | Calls out | No | Request bodies | urllib | Low | Encode | None | **KEEP_AS_LIBRARY** | P3 |
| python-dotenv `1.2.2` | Env load | startup | BSD-3-Clause | Yes | No | No | Secrets on disk | — | Low | — | None | **KEEP_AS_LIBRARY** | P3 |
| Jinja2 `3.1.6` | Templates | backend | BSD (installed classifier) | Yes | No | No | — | — | Low | Pallets | None | **KEEP_AS_LIBRARY** | P3 |
| aiosqlite `0.22.1` | SQLite asyncio | poetry; tests/CI sqlite | MIT (project; lock has no license field) | Optional | No | No | Local DB | SQLAlchemy | Low | — | None | **KEEP_AS_LIBRARY** | P3 |
| psycopg `3.3.3` | Postgres driver | Docker DATABASE_URL | LGPL-3.0 typical for psycopg3 — **lock has no license field**; **NEEDS_LEGAL_REVIEW** for sidecar if binary wheels ship | Docker / possibly sidecar | No | No | DB | Other drivers | Medium | psycopg | None | **KEEP_AS_LIBRARY** + **NEEDS_LEGAL_REVIEW** (confirm COPYING in wheel) | P1 |
| cryptography `46.0.7` | Vault/Fernet | security | Apache-2.0 OR BSD-3-Clause (installed) | Yes | No | No | Keys | — | Medium | PyCA | None | **KEEP_AS_LIBRARY** | P3 |
| PyJWT `2.13.0` (requirements) / lock `2.13.3` | JWT | auth | MIT (installed) | Yes | No | No | Tokens | — | Low | — | None | **KEEP_AS_LIBRARY** | P3 |
| python-multipart | Uploads | PPTX upload | Apache-2.0 (installed) | Yes | No | No | Files | — | Low | — | None | **KEEP_AS_LIBRARY** | P3 |
| boto3 (requirements, not poetry direct) | AWS secrets | vault | Apache-2.0 (installed 1.42.83) | Yes if sidecar uses requirements.txt | AWS | No | Secrets | Other secret stores | Medium | AWS | None | **KEEP_AS_CONNECTOR** | P2 |
| openai `2.33.0` | Cloud LLM/TTS SDK | Model gateway / TTS | Apache-2.0 (installed classifier) | Yes | OpenAI network | Hidden | Prompts | Other providers | High if called outside gateway | OpenAI | None | **KEEP_AS_CONNECTOR** | P1 |
| anthropic (requirements only) | Claude SDK | optional | Apache-2.0 typical — **not installed locally this session** | If sidecar installs requirements | Anthropic | Hidden | Prompts | Gateway | Medium | Anthropic | None | **KEEP_AS_CONNECTOR** + confirm LICENSE at next pin | P2 |
| PyGithub `2.9.1` | GitHub REST | `github_service.py`, PRs | **LGPL** (PyPI 2.9.1 classifier; `COPYING.LESSER`) | **Yes if sidecar pip-installs it** | GitHub.com | Hidden | Repo metadata | httpx+GitHub API | Medium | PyGithub | None | **KEEP_AS_LIBRARY** + **NEEDS_LEGAL_REVIEW** (LGPL in NSIS venv) | P0 |
| atlassian-python-api `3.41.21` | Jira REST | Jira adapter | Apache License 2.0 (PyPI 3.41.21 `license`) | Yes if poetry/sidecar | Jira | Hidden | Tickets | REST via httpx | Low | Atlassian wrapper | None | **KEEP_AS_CONNECTOR** | P2 |
| slack-sdk `3.41.0` | Slack | Slack connector | MIT (PyPI 3.34.0 classifier; lock 3.41.0 same package) | Yes | Slack | Hidden | Messages | Web API | Low | Slack | None | **KEEP_AS_CONNECTOR** | P3 |
| croniter (requirements only) | Schedules | scheduled tasks | MIT typical — **not installed / not in poetry.lock** | If sidecar | No | No | — | stdlib | Low | — | None | **KEEP_AS_LIBRARY** + confirm LICENSE when pinning | P3 |
| Playwright (optional backend; npm `@playwright/test` `1.51.0`) | Browser automation / e2e | `playwright_adapter.py`, frontend e2e | Apache-2.0 (`node_modules/@playwright/test/LICENSE`) | e2e not in product; backend optional not in requirements.txt | May launch Chromium | Mentrix Browser Automation | DOM | Other BrowserAutomationProvider | Low | Microsoft | None | **KEEP_AS_LIBRARY** | P3 |

### C. Frontend direct (lock + LICENSE files)

All **KEEP_AS_LIBRARY**. Distributed in `frontend/dist` inside Electron. Not external. No user-facing third-party brand. Low lock-in except React/Vite.

| Package | Pin | License (file on disk) |
|---------|-----|------------------------|
| react / react-dom | 18.3.1 | MIT (Facebook) |
| react-router-dom | 7.14.2 | MIT |
| monaco-editor | 0.56.0 | MIT (Microsoft) |
| @monaco-editor/react | 4.7.0 | MIT |
| mermaid | 11.16.0 | MIT |
| cytoscape | 3.34.0 | MIT |
| cytoscape-cose-bilkent | 4.1.0 | MIT |
| react-cytoscapejs | 2.0.0 | MIT |
| recharts | 2.12.4 | MIT |
| lucide-react | 0.364.0 | **ISC** (LICENSE file) |
| class-variance-authority | 0.7.1 | Apache-2.0 |
| clsx / tailwind-merge / tailwindcss-animate | 2.1.1 / 3.5.0 / 1.0.7 | MIT |
| vite | 6.4.2 | MIT (dev; builds dist) |
| typescript | 5.6.3 | Apache-2.0 (dev) |
| vitest | 4.1.5 | MIT (dev) |
| tailwindcss | 3.4.16 | MIT (dev) |

Copyleft scan of entire frontend + electron lock `license` fields: **0** GPL/AGPL/LGPL/SSPL matches.

### D. Runtime images / connectors / process / coding

| Dependency | Purpose | Where used | License | Distributed? | External only? | User branding? | Data boundary | Replaceability | Lock-in | Maintenance | Differentiation | Decision | Priority |
|------------|---------|------------|---------|--------------|----------------|----------------|---------------|----------------|---------|--------------|-----------------|----------|----------|
| postgres:16-alpine | DB | `docker-compose.yml` | PostgreSQL License (upstream; image not unpacked this session) | Dev/prod Docker, not NSIS extraResources | Optional vs sqlite | No | All canonical data | sqlite already used in CI | Medium | PGDG | None | **KEEP_AS_RUNTIME** | P3 |
| python:3.12-slim | App image | backend + voicebox Dockerfiles | PSF | Images | No | No | — | — | High | CPython | None | **KEEP_AS_RUNTIME** | P3 |
| node:18-alpine | Frontend build | `frontend/Dockerfile` | MIT (Node) | Build stage | No | No | — | — | Medium | Node | None | **KEEP_AS_RUNTIME** | P3 |
| nginx:alpine | Static UI | frontend runtime stage | BSD-2-Clause (nginx) | Frontend container | No | No | — | — | Low | nginx | None | **KEEP_AS_RUNTIME** | P3 |
| ollama/ollama:**latest** | Mentrix Local LLM | `services/mentrix-llm/docker-compose.yml` | MIT (THIRD_PARTY_NOTICES + upstream). **Tag unpinned** | Optional container | Local models | Mentrix Local LLM | Prompts/weights in volume | Other OpenAI-compat | Medium | Ollama | None | **KEEP_AS_RUNTIME** + pin tag | P1 |
| ghcr.io/all-hands-ai/openhands:**0.32** | Optional coding engine | `docker-compose.zect-coding-engine.yml` | MIT (THIRD_PARTY_NOTICES; OpenHands) | Optional | Engine HTTP | Hidden (`ZECT_CODING_ENGINE=remote`) | Workspace mount | `mentrix_native` | Medium | OpenHands | None | **KEEP_AS_CONNECTOR** | P2 |
| clamav/clamav:**1.4** | Malware scan | `services/zect-security-scan` | **GPL-2.0** (`COPYING.txt` / GitHub license) | Optional compose **only** | Local daemon 3310 | Hidden | Files scanned | Other DetectionProvider | Low if optional | Cisco-Talos | None | **KEEP_AS_CONNECTOR** (DetectionProvider). **Never** link into main backend process / NSIS | P0 |
| Camunda REST | BPM | `camunda_client`, `/api/process` | Proprietary + source editions — **connector only**, no Camunda SDK in poetry | External | Yes `ZECT_CAMUNDA_BASE_URL` | Mentrix Process | Process vars | Native Process Engine (S9) | Medium | Camunda | Process **domain** is ZECT | **KEEP_AS_CONNECTOR** | P2 |
| Jira Cloud/Server | Tickets | JiraSourceAdapter | Atlassian ToS + Apache wrapper | External | Yes | Hidden | Issues | Keep connector | Medium | Atlassian | WorkItem mapping is ZECT | **KEEP_AS_CONNECTOR** | P2 |
| GitHub.com | PRs/repos | PyGithub + git CLI | GitHub ToS | External | Yes | Hidden | Repos | Keep connector | High | GitHub | Evidence/WorkItem is ZECT | **KEEP_AS_CONNECTOR** | P2 |
| Slack | Notify | slack-sdk | Slack ToS + MIT SDK | External | Yes | Hidden | Messages | Keep connector | Low | Slack | None | **KEEP_AS_CONNECTOR** | P3 |
| OpenAI / other LLM APIs | Generation | Model gateway; **also Presenton container env** | Provider ToS | External | Yes | Hidden | Prompts | Gateway must stay canonical | High | Vendors | None | **KEEP_AS_CONNECTOR** | P1 |
| Microsoft 365 Graph / IMAP SMTP | Mail | connectors/gateway.py | Microsoft ToS | External | Yes | Hidden | Mail | Keep connector | Medium | Microsoft | None | **KEEP_AS_CONNECTOR** | P3 |
| Zoom join URL | Present flow | Electron / Present Deck | Zoom ToS | External | Yes | Product says Open Zoom | Join URL only | Keep | Low | Zoom | None | **KEEP_AS_CONNECTOR** | P3 |

### E. Explicit REMOVE / do-not-do

| Item | Decision | Notes |
|------|----------|--------|
| Presenton runtime (now) | **Do not REMOVE** | S8 D only after native default + sustained proof |
| Presenton UI source | Already not vendored | Do not vendor |
| Rewrite Chromium/Electron/Playwright/Git/Jira/Camunda | **REMOVE** from sovereignty rewrite scope | Plan § What NOT to rewrite |
| `weasyprint` | **REMOVE** from implied deps | Dockerfile apt comments mention pango/cairo “for weasyprint” but weasyprint is **not** in poetry/requirements |
| Devin author string in `pyproject.toml` | Fix on a focused chore PR (not S2) | Content ownership |

---

## Presenton capability map (what ZECT actually depends on)

See also `ZECT_NATIVE_PRESENTATION_ENGINE_PLAN.md` §2.

| Presenton capability | ZECT uses it today? | ZECT code | ZectNative must replace? |
|----------------------|---------------------|-----------|--------------------------|
| HTTP generate `POST /api/v1/ppt/presentation/generate` (`content`, `n_slides`, `language`, `template`, `export_as=pptx`, optional `instructions`) | **YES — load-bearing** | `generate_presentation()` | **YES** — Prompt/Intent + Outline + Slide plan + layout + PPTX render + export |
| Download PPTX from returned `path` / `edit_path` | **YES** | same | **YES** — Exporter writes allowlisted local PPTX |
| Template list `GET /api/v1/ppt/template/all?include_defaults=true` | **YES** (status/reachability + optional bind-by-name) | `list_templates()` | **NO** as product gallery. Gallery is ZECT registry. Native lists TemplateDefinitions |
| Session login `POST /api/v1/auth/login` + cookie / bearer | **YES** (engine auth) | `_session_headers()` | **NO** — native is in-process; drop Presenton auth |
| Built-in templates general/modern/standard/swift | Fallback when down / unmapped | `BUILTIN_TEMPLATES` | **NO** as Zinnia. Optional PresentonProvider-only |
| Apply uploaded master UUID to generate | **YES** if registry mapping exists | `resolve_presenton_template_id` | **YES** — Template Intelligence applies ZECT TemplateDefinition |
| Presenton “bring your design” upload UI | Operator/admin **outside** ZECT | `docs/PRESENTON_LOCAL.md` | **YES** for user/org PPTX → TemplateDefinition (ZECT already stores PPTX bytes) |
| Push ZECT-uploaded PPTX into Presenton | **NO** (gap) | `register_user_pptx` sets `presenton_template_id=None` | Native importer closes this without Presenton |
| Presenton editor / admin UI / streaming progress / image gen | **NO** (image gen disabled in runbook) | UI is ZECT; `DISABLE_IMAGE_GENERATION=true` | Native may add Asset resolver later; not current parity of unused features |
| Presenton Cloud | **NO** | Self-host only | Do not add |
| LLM inside Presenton container | **YES implicitly** (engine calls its `LLM=` provider) | Not ZECT Model Gateway | **YES** — native must use ZECT Model Gateway only |
| presentation_id / presenton_path | Stored in generate response | API return | **Must not** be canonical. Store ZECT artifact ids |

**Data portability risk:** `canonical-mapping.json` currently stores `provider_template_id` (Presenton UUID). S2 must keep ZECT ids as source of truth and treat provider ids as adapter-only.

---

## Legal / pin backlog (human review)

| ID | Item | Blocks S2? |
|----|------|------------|
| L1 | PyGithub 2.9.1 **LGPL** in packaged Python venv | No |
| L2 | ClamAV **GPL-2.0** — keep compose-isolated; never statically merge | No |
| L3 | Chatterbox **model weights** license / commercial use | No (S6/S10) |
| L4 | ffmpeg in Voicebox image if redistributed | No |
| L5 | psycopg wheel COPYING (likely LGPL) if sidecar includes it | No |
| L6 | Presenton `:latest` — pin before any ZECT-distributed engine image | No (not shipping it in NSIS) |
| L7 | ollama `:latest` pin | No |
| L8 | Electron Chromium NOTICE completeness in installer | No |
| L9 | `pyproject.toml` Devin author | No |
| L10 | Dual poetry vs requirements.txt (supply-chain / license drift) | No, but fix before claiming packaged license completeness |

---

## Architecture tests (S2)

`backend/tests/fixes_and_phases/test_presentation_architecture.py` forbids `presenton_client` imports from `app/domains` and Presenton client/types in `ZectPresent.tsx`. `PresentonProvider` lives in `backend/app/adapters/presentation/`.

## Stop

S1 complete. S2 landed on a focused branch; Presenton remains default. Do not start KV cache, Graphify, OCR/XLSX, broader Web, or additional agents.

Native presentation recommendation: **GO**.
