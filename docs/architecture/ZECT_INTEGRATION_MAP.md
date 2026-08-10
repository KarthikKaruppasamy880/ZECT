# ZECT Integration Map

**Canonical parent:** [`ZECT_SYSTEM_ARCHITECTURE.md`](../../ZECT_SYSTEM_ARCHITECTURE.md)  
**Evidence:** [`ZECT_PRODUCT_ACCEPTANCE.md`](../../ZECT_PRODUCT_ACCEPTANCE.md)

## WorkItem sources

| Source | Path | Notes |
|--------|------|-------|
| User | `POST /api/work-items` | Direct create |
| Jira | `POST /api/work-items/ingest` (`source=jira`) + `/api/jira/*` | Live ingest when `JIRA_*` configured |
| Camunda | ingest `source=camunda` + `/api/process/*` | Live when Camunda base URL configured |

Adapter: `backend/app/services/work_items/source_adapter.py` (P1 live — not P0 stubs-only).

## Fabric / process

| Surface | Prefix | Role |
|---------|--------|------|
| Fabric | `/api/fabric` | surfaces, classify, run |
| Mentrix Process | `/api/process` | Camunda status/deploy/start/incidents |
| Developer handoff | `POST /api/mentrix/developer/fabric-handoff` | WorkItem → Fabric |

## Git / PR / CI

| Surface | Role |
|---------|------|
| Mentrix Delivery Runs (`/mentrix`, `/api/mentrix/runs*`) | Ship path Lattice → plan → build → gates → approve → PR |
| Git Ops / CI Monitor UI | Delivery section |
| `MENTRIX_PR_DRY_RUN` | Safe PR behavior in CI/dev |

Close-loop: `POST /api/mentrix/developer/close-loop` (dry_run accepted in P1 tests).

## Ultra Review

| Endpoint | Role |
|----------|------|
| `/api/ultrareview/*` | Existing review sessions |
| `POST /api/ultrareview/lanes` | 3-lane merger (requirements / engineering / security) — **no second LLM** |
| `GET /api/ultrareview/work-item/{id}/context` | WI context for review |

## Security (boundary)

| Piece | Shipped behavior |
|-------|------------------|
| `POST /api/system/security-scan` | MentrixSecurityAgentScanner → DB findings |
| UI | `/security-incidents` |
| Not shipped | Native deep malware daemon rewrite |

## Optional connectors (env-gated)

Slack, SMTP, Datadog, Confluence MCP, Presenton/Zoom — present in `.env.example`; not Mentrix spine SoT. System health marks Jira/Camunda `not_configured` when unset.

## Mentrix Personal Ops (Companion)

| Surface | Role |
|---------|------|
| `MentrixConnector` gateway | `backend/app/services/mentrix/connectors/` — native → MCP → desktop/browser |
| `GET /api/personal-actions/connectors/health` | Connector health + capability/permission matrix |
| `PersonalAction` | Canonical actionable personal work (Email/Calendar/Slack/Jira/GitHub/WorkItems) |
| `POST /api/personal-actions/daily-brief` | Aggregates information + PersonalActions |
| Schedule `task_type=daily_brief` | Same assembly via schedule ticker |
| M365 / Graph | First-class Outlook mail+calendar when `MS_GRAPH_*` set; IMAP/SMTP fallback |
| Session Allow | `POST /api/permissions/grants/session` → CapabilityGrant TTL skips per-step desktop Allow |
| Desktop FS | Electron `mkdir` / `list_dir` / `move_path` (allowlisted; never delete) |

Suggested PersonalAction verbs: Analyze · Fix · Draft · Reply · Prepare · Organize · Continue.
