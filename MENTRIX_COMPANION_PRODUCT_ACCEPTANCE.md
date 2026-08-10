# Mentrix Companion + Presentation + ZECT Learning — Product Acceptance

**Date:** 2026-07-27
**Branch evidence:** `feat/mentrix-companion-present-learning-hardening`
**Scope:** Companion voice/UX + permissions, Connector Gateway, PersonalAction/Daily Brief, connector depth, Presentation Flow A/B, desktop/browser fallback, classification/DLP + Developer Ask lattice_hits, ZECT Learning / Mentrix Learning Advisor.

## Verdict

| Area | Status |
|------|--------|
| Companion voice MIME + session grants + Zoom share gate | **VIABLE** (unit/UI evidence) |
| Connector health / permission matrix + untrusted tagging | **VIABLE** |
| PersonalAction shape + role-aware Daily Brief | **VIABLE** |
| Live M365 / Slack / Jira / GitHub calls | **BLOCKED_EXTERNAL** without env credentials |
| Presentation Flow A/B (audience, claims, sensitivity, Presenton) | **VIABLE** (API + UI; Presenton generate needs `PRESENTON_BASE_URL`) |
| Desktop mkdir/move/organize + never-delete | **VIABLE** (gateway + `electron/computer.js` evidence) |
| Classification / prompt-injection hardening + lattice_hits Ask | **VIABLE** |
| ZECT Learning catalog + modes + skill-gap recs | **VIABLE** (PBL sync live fetch may be **BLOCKED_EXTERNAL** offline) |
| Fully local / hallucination-free / unhackable / fully autonomous | **NOT CLAIMED** |

Overall: **VIABLE for gap-hardening acceptance** with explicit **BLOCKED_EXTERNAL** rows for live connector and optional Presenton/PBL network paths.

## Non-claims (explicit)

- Not hallucination-free.
- Not fully local AI.
- Not unhackable.
- Not fully autonomous (writes still Permission Broker + user confirm; Zoom never auto-shares; Guided learning never silently solves).
- Does not rehost third-party tutorial bodies from project-based-learning links.

---

## Persona matrix

| Persona | Daily Brief sections | Evidence |
|---------|----------------------|----------|
| executive / admin / lead | Decisions, Risks, Status | `assemble_daily_brief` role mapping |
| manager | Team blockers, PRs/Jira, Meetings | same |
| ea / assistant | Calendar, Inbox drafts, Meeting prep | same |
| developer (default) | Continue Agent, Review PR, Open Jira | same |

One Mentrix Companion only — no second assistant.

## Connector matrix

| Connector | Health when unset | Read | Write policy | Live call |
|-----------|-------------------|------|--------------|-----------|
| m365 | `missing_creds` | ALLOW | CONFIRM drafts | **BLOCKED_EXTERNAL** without Graph |
| email_imap_smtp | `missing_creds` | ALLOW | CONFIRM send | **BLOCKED_EXTERNAL** without IMAP/SMTP |
| slack | `missing_creds` | ALLOW | CONFIRM send | **BLOCKED_EXTERNAL** without `SLACK_BOT_TOKEN` |
| jira | `missing_creds` | ALLOW | (read) | **BLOCKED_EXTERNAL** without JIRA_* |
| github | `missing_creds` | ALLOW | (read) | **BLOCKED_EXTERNAL** without `GITHUB_TOKEN` |
| zoom | configured (desktop) | — | CONFIRM open/join; **DENY** schedule | Open/join only |
| filesystem | configured | ALLOW list | CONFIRM mkdir/move; **DENY** delete | Desktop Computer Mode |
| browser | configured | ALLOW snapshot | CONFIRM navigate | Allowlisted runtime |

UI: Integrations → Mentrix connector gateway table (`data-testid="connector-health-matrix"`).
API: `GET /api/personal-actions/connectors/health`.

Untrusted ingest: email/Slack/Jira/GitHub Daily Brief payloads wrapped with `role=untrusted_data` / `never_execute_as_system`.

## Daily Brief / PersonalAction

- Fields: `connector_id`, `description`, `due_at` (alias of `due`), `suggested_actions`.
- Verbs include: Draft Reply, Prepare Meeting, Continue Agent, Organize Files, Review PR, Open Jira, Approve.
- Evidence: `test_personal_action_shape_and_verbs`, `test_personal_action_crud_and_brief`.

## Presentation Flow A & B

| Flow | Path | Evidence |
|------|------|----------|
| A Existing deck | analyze → sensitivity → audience → claims → improved notes → rehearse → open PPTX → Zoom → **explicit share approve** → narrate | `/api/mentrix/presentation/analyze-deck`, Present Deck Analyze + share checkbox |
| B Prompt → deck | prepare → classify → audience → outline/claims → Presenton generate | `/api/mentrix/presentation/prepare-prompt` wired before generate |
| Claims | UNVERIFIED never `present_as_fact` | `test_claims_unverified_not_present_as_fact` |
| Sensitivity | CONFIDENTIAL/RESTRICTED forbid external web; no silent cloud | `test_sensitivity_confidential_forbids_external_web` |
| Zoom | No Meeting API schedule; share approval UI gate | `test_zoom_schedule_denied`, PresentDeckPanel `shareApproved` |

Confidential deck: model route uses `fallback_policy` `never` for cloud when classified CONFIDENTIAL/RESTRICTED — may block generate if no local LLM (**VIABLE** policy; runtime depends on local model).

Voice: CI expects `audio/wav` + `X-Mentrix-TTS-Content-Type` (`test_voice_cloning` / `test_voice_mime_regression`).

## Desktop / browser fallback

- `electron/computer.js`: `refuseDelete` → `delete_never_allowed`; mkdir/move present.
- Gateway filesystem `delete` invoke denied.
- Evidence: `test_electron_computer_js_never_delete_export`, `test_filesystem_delete_denied_via_gateway`.

## Security / Developer Ask

| Control | Result |
|---------|--------|
| Classification PUBLIC→RESTRICTED | Heuristic classify + model policy | **VIABLE** |
| Prompt injection (hostile email/Slack) | Sanitized as UNTRUSTED_DATA | **VIABLE** (`test_prompt_injection_hostile_email_not_system`) |
| Lattice hits in Ask pack | `project_intelligence.query_graph` → `developer_service` → `context_engine` | **VIABLE** (`test_context_engine_accepts_lattice_hits`) |
| Model telemetry | `telemetry` on Ask (requested/actual/fallback) | **VIABLE** (code path) |

## ZECT Learning / Mentrix Learning Advisor

Product surface: Mentrix → Learning (`/learning`, Sidebar **ZECT Learning**).

| Item | Result |
|------|--------|
| LearningSource / Resource / Project models | Present |
| PBL catalog | Metadata + external links + MIT attribution; `content_policy=external_link_only` | **VIABLE** parser; live README fetch **BLOCKED_EXTERNAL** if network blocked |
| GUIDED | `auto_complete_forbidden`; no coding agent auto-solve | **VIABLE** |
| PAIR / DEMO / AUTONOMOUS | Route to Developer / Coding Agent | **VIABLE** |
| Progress | Explicit events only (`started` / milestone / test_passed / user_confirmed) | **VIABLE** |
| WorkItem skill-gap | Suggest Learn First / Pair / Continue Agent; `blocks_work=false`; leak guard | **VIABLE** |

## Tests run (evidence)

Command (local, 2026-07-27):

```text
pytest backend/tests/fixes_and_phases/test_voice_cloning.py \
  backend/tests/fixes_and_phases/test_personal_ops.py \
  backend/tests/fixes_and_phases/test_companion_present_learning.py -q
```

**Result: 61 passed** (voice cloning + personal ops + companion/present/learning hardening).

Coverage includes: voice MIME wav, connector matrix policy fields, PersonalAction verbs, presentation audiences/flows, untrusted tagging, no-delete, learning parser/GUIDED/skill-gap, lattice_hits pack.

## External credential / source blockers

| Dependency | Status if unset |
|------------|-----------------|
| Microsoft Graph | BLOCKED_EXTERNAL |
| IMAP/SMTP | BLOCKED_EXTERNAL |
| Slack / Jira / GitHub tokens | BLOCKED_EXTERNAL |
| PRESENTON_BASE_URL | Generate deck blocked (analyze/prepare still work) |
| PBL raw README network | Sync may fail; parser still unit-tested |
| Local LLM for RESTRICTED decks | Generate may block by design |

## Remaining gaps

- Live connector E2E with real credentials not exercised in CI.
- Presenton end-to-end deck bytes not asserted without Docker Presenton.
- Electron mkdir/move runtime smoke still requires desktop app session.
- Learning Skills/Memory updates on verified progress are stubbed to progress/evidence JSON (no parallel Skills engine).

## Architecture reuse confirmation

No second assistant, memory, permission, context, or coding gateway was introduced. Learning and Present harden Mentrix Companion on the existing spine (Knowledge / Memory / Skills / ProjectIntelligence / WorkItems / Coding Agent / Presenton / Permission Broker).
