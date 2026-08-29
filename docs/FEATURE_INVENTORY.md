# ZECT — Feature Inventory (Phase 0 Audit)

49 routes registered in `frontend/src/App.tsx`; 47 distinct links across 7 sidebar sections in `frontend/src/components/Sidebar.tsx`. Classification below is a first pass from static inspection — "partial" items may hide more/less real functionality than listed; flag any correction before Phase 1 planning.

## Orphaned / broken links

- **`/stages/:stage` (StagePage) — dead.** Registered route, no nav entry, no in-app link or `navigate()` call anywhere. Candidate for removal or hiding behind a feature flag per Phase 0's "hide unfinished items, don't delete yet" rule.
- No broken nav links found (every sidebar `href` resolves to a registered route).

## By sidebar section

### Workflow
| Route | Status | Note |
|---|---|---|
| Mentrix Companion `/mentrix-home` | **Working** | Realtime voice + chat; latency/cancellation fixed this session. |
| Incident Runbook `/mentrix-home?incident=1` | Working (deep-link variant) | Same page, incident-mode param. |
| Mentrix Delivery `/mentrix` | **Working** | ForgeLoop orchestrator UI. |

### Workspace
| Route | Status |
|---|---|
| Dashboard `/` | Working |
| Projects `/projects` | Working |
| Repo Workspace `/repo-workspace` | Not verified this pass |
| Settings `/settings` | Working |

### Understand
| Route | Status | Note |
|---|---|---|
| Lattice Graph `/lattice` | Working | Cytoscape.js rewrite shipped this session. |
| Repo Analysis `/repo-analysis` | Not verified | |
| Blueprint `/blueprint` | Working | Feeds Plan/Build context. |
| Doc Generator `/doc-generator` | Working | |
| Code Index `/code-index` | Not verified | |
| Docs Center `/docs` | Not verified | |

### Deliver
| Route | Status | Note |
|---|---|---|
| Agent Mode `/agent-mode` | Working, mode-mapping fix applied | Resolves build stages to "upgrade" mode. |
| Ask `/ask` | Working | |
| Plan `/plan` | Working | Persists to context store for Build handoff. |
| Build `/build` | **Fixed this session** | Previously rendered blank on Plan→Build handoff; previously hit a no-LLM stub for deliver-mode with no workspace. Both fixed. |
| Snippet Review `/review` | Working | Consolidated onto `review_service.py`. |
| Deploy `/deploy` | Not verified | |
| Orchestration `/orchestration` | Working | |

### Quality
| Route | Status |
|---|---|
| Mentrix Ultra Review `/code-review` | Working — consolidated engine |
| Rules Engine `/rules` | Working |
| Sandbox Gate `/sandbox` | **Partial/risky** — see THREAT_MODEL.md (Docker isolation has a silent host-fallback + a command-injection gap even when Docker is used) |
| CI Monitor `/ci-monitor` | Not verified |
| Git Operations `/git-ops` | Working — path-allowlisted |

### Enterprise
| Route | Status | Note |
|---|---|---|
| Integrations `/integrations` | Working | Real MCP adapters (GitHub/Jira/Slack/Confluence/Datadog/Email). |
| Audit Trail `/audit-trail` | Working | Canonical `domains.audit.audit_trail.log_audit` (rbac wrapper delegates). |
| Export/Share `/export` | Not verified | |
| Output History `/output-history` | Not verified | |
| Analytics `/analytics` | Not verified | |
| Token Controls `/token-controls` | Working — token tracking/budgets (Fix #4) | |
| Secrets Manager `/secrets` | Working — RBAC-gated, Fernet; `/resolve` refs (no plaintext for agents) | |

### Labs (16 items — mostly experimental/incubating)
| Route | Status | Note |
|---|---|---|
| Skill Library `/skills` | Not verified | |
| Skills Engine `/skills-engine` | Not verified | Possible overlap with Skill Library — check for duplicate concept in Phase 1. |
| Memory System `/memory` | Not verified | Possible overlap with Mentrix Notes. |
| Mentrix Notes `/mentrix-notes` | Working | Real note browsing + auto-logged exchanges. |
| Dream Engine `/dream-engine` | Not verified | |
| Data Layer `/data-layer` | Not verified | |
| Data Flywheel `/data-flywheel` | Not verified | |
| Permissions `/permissions` | Working | Rules, grants, diagnostics, emergency-stop (Phase 5 A–D). |
| Transfer & Onboard `/transfer` | Not verified | |
| Knowledge Base `/knowledge-base` | Not verified | Possible overlap with Lattice/Docs Center. |
| Playbooks `/playbooks` | Not verified | |
| Scheduled Tasks `/scheduled-tasks` | Not verified — confirm real cron/scheduling backend exists | |
| Session Insights `/session-insights` | Not verified | |
| Conversations `/conversations` | Not verified | |
| App Runner `/app-runner` | Working — admin RBAC + path allowlist + audit | Critical threat findings fixed; still privileged. |
| File Explorer `/file-explorer` | Working — path-allowlisted | Requires `ZECT_WORKSPACE_ROOT` set (Windows deploys won't match the Unix default roots otherwise). |

## Duplicate-concept candidates flagged for Phase 1 review

The Labs section has several route pairs that *may* be duplicate/overlapping concepts rather than distinct features — needs a hands-on check, not just naming similarity:
- **Skill Library** vs. **Skills Engine**
- **Memory System** vs. **Mentrix Notes**
- **Knowledge Base** vs. **Lattice Graph** vs. **Docs Center**

## Confirmed dead code (backend, not routes)

- `services/llm/voicebox_client.py`, `services/llm/elevenlabs_client.py` — legacy, only referenced by one test file each. Safe to remove or leave inert; flagged for Phase 1/11 cleanup.

## Confirmed live stub (backend)

- `services/phases/build_phase_svc.py:run_build_generate()` — offline placeholder path gated only on `OPENAI_API_KEY` presence, not `ANTHROPIC_API_KEY`. An Anthropic-only deployment would silently hit the stub instead of calling Claude. Not currently active (this environment has `OPENAI_API_KEY` set) but the gate condition doesn't match the app's documented Anthropic-preferred behavior — flag for a small fix in Phase 1.
