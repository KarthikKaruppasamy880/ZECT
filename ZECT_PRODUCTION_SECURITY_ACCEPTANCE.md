# ZECT Production Security Acceptance

**Date:** 2026-08-18  
**Canonical develop (pre-PR):** `071028e` (PR **#160** human-merged — Work intelligence)  
**This PR branch:** `feat/security-production`  
**Prompt:** `prompts/ZECT_REMAINING_PRODUCTION_GRADE_MASTER_CLOSURE.md` tranche D  
**Stop label:** `READY_TO_MERGE_SECURITY` — human merge only, no auto-merge.

## Verdict

**PARTIAL** for live externals. **No unresolved Critical/High on this campaign SHA** after the path-jail prefix fix.

| Gate | Result |
|------|--------|
| Cross-user / project / repo isolation | **PASS** (unit + HTTP voice 404) |
| Traversal / prefix sibling / symlink-out | **PASS** (prefix bypass closed; symlink skip if OS cannot create links ≠ PASS) |
| Wrong-root Git | **PASS** |
| Command injection (sandbox argv; runner admin + escape) | **PASS** |
| Prompt injection / untrusted ingest | **PASS** |
| Malicious PPTX zip-slip | **PASS** |
| SSRF (localhost / metadata / file / private) | **PASS** (unit) |
| Secrets redaction / audit | **PASS** (unit) |
| Git write always-confirm + desktop_delete never | **PASS** |
| Unauthenticated privileged APIs | **PASS** (401/403) |
| Unauthorized GitHub push/PR | **BLOCKED_EXTERNAL** (no token → no `pr_url`; not a live GitHub PASS) |
| OAuth / Entra | **BLOCKED_EXTERNAL** (local auth; login-url 400/503; client_secret never in authorize URL) |
| Live Voicebox reconnect / overlap | **BLOCKED_EXTERNAL** (engine-status honest; stream resume no duplicate fallback) |
| Headed Privileged UI | **PASS** when `test:e2e:core` includes `security-production.spec.ts` and API is up |
| Electron | **PASS** locally (`security-electron.spec.ts`); skip if `electron.exe` missing — skip ≠ core PASS |
| CodeRabbit | **SKIPPED** — unavailable ≠ PASS |
| Mentrix Ultra Review | see `test-results/security-production/ultra-review.json` |

Overall ZECT remains **ZECT_PRODUCTION_PARTIAL**. This tranche does not start recovery, soak, a11y, Graphify, or S8C/S8D.

## Threat campaign

Evidence file: `backend/tests/test_security_production.py` (CI-viable). Headed: `frontend/e2e/security-production.spec.ts`. Electron: `frontend/e2e/security-electron.spec.ts`.

| Threat | Proof | Result |
|--------|--------|--------|
| Cross-user / project / repo | Companion scope skips foreign repo ids / WorkItems; voice speak 404 for another user's `voice_id` | **PASS** |
| Traversal / symlink | `is_path_under_root` + `Path.resolve()`; `ws-evil` denied when root is `ws`; symlink-out denied (skip if OS cannot symlink) | **PASS** |
| Wrong-root Git | `git_add` sibling path 400; force remote name 400 | **PASS** |
| Command injection | Docker sandbox `shell=False` argv list; `_reject_command_escape`; execute admin-only | **PASS** |
| Prompt injection / malicious repo | `sanitize_for_prompt` cannot close fence; Jira ingest `[untrusted-external]` | **PASS** |
| Malicious PPTX | zip-slip + non-zip `UnsafePptxError` | **PASS** |
| SSRF | `validate_url_for_fetch` blocks loopback/metadata/`file:`/RFC1918 | **PASS** (unit; not a live network pentest) |
| Secrets / Git / OAuth | `redact_mapping` / audit details; OIDC URL has no `client_secret`; unset OAuth/GitHub = **BLOCKED_EXTERNAL** | **PASS** (fail-closed) + **BLOCKED_EXTERNAL** live |
| Untrusted / restricted context | untrusted fence + ingest tag | **PASS** |
| Escalation / tool abuse | `desktop_delete` never even with confirm; `git_push` always-confirm without seed rules | **PASS** |
| Unauthorized push/PR | `_push_or_block` GitHub origin without token → `blocked_external` | **BLOCKED_EXTERNAL** |
| Artifact / voice ownership | foreign `voice_id` 404 | **PASS** |
| Reconnect duplication | companion stream after disconnect keeps partial only (no duplicate fallback) | **PASS** (unit). Live Voicebox **BLOCKED_EXTERNAL** |
| Privileged actions auditable | `PermissionAudit` row for deny/confirm; unauth `/api/permissions/*` 401 | **PASS** |

## Fixes in this PR

1. **High — path jail prefix bypass.** `path_under_allowed_roots` used `str(p).startswith(root)`, so `...\ws-evil` matched root `...\ws`. Replaced with `is_path_under_root` (`Path.relative_to` + Windows `normcase` + separator).
2. **High — git write default-allow if seed rules missing.** `git_commit` / `git_push` / `git_create_pr` added to `ALWAYS_CONFIRM_TOOLS` so Companion git write cannot silently grant.

No unresolved Critical/High from this campaign. Residual: App Runner still `shell=True` for **admin** one-shot execute (product feature, not non-admin escalation). Live Entra/GitHub/Voicebox/Jira/Camunda remain **BLOCKED_EXTERNAL**.

## Honest limits

- Live OAuth handshake is not executed.
- Live GitHub push/PR is not executed.
- Live SSRF against cloud metadata is not executed beyond unit policy.
- Headed e2e does not click Jira/Camunda ingest or Emergency Stop.
- Electron skip ≠ PASS.
- CodeRabbit skip ≠ PASS.
- In-memory coding-agent missions remain a tranche E recovery topic.

## Stop

Human-merge this PR. Do **not** start tranche E (install/recovery) until `origin/develop` contains this merge.
