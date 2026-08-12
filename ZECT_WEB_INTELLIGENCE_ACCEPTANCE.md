# ZECT Web Intelligence (C) — Acceptance

**Date:** 2026-08-12  
**Branch:** `feat/zect-web-intelligence-c`  
**PR:** https://github.com/KarthikKaruppasamy880/ZECT/pull/135  
**Base:** `develop` @ `e06bb421b85131acc0681dd0e6b932ceed2803bf` (B MERGED/FROZEN)  
**Prompt:** `prompts/Cursor Prompt — Execute C Web Intelligence.md`  
**Remediation:** `prompts/ZECT_WEB_INTELLIGENCE_PR135_SECURITY_REMEDIATION.md`  
**Stop condition:** STOP after C — **D (Learning expand) not started.**

## Frozen baselines preserved

| Gate | Status |
|------|--------|
| Present A1–A8 / LIVE_VIABLE | FROZEN |
| Phases 5–13 | FROZEN |
| B Document Intelligence | **MERGED / FROZEN** (`e06bb42`) |
| Connector Gateway / Permission Broker / ContextEngine / Model Gateway | Extended, not replaced |

## Verdict

**PASS (MVP + PR #135 security remediation)** with honest **PARTIAL** for general web search, YouTube transcripts, and Reddit/public discussions.

All external content tagged **`UNTRUSTED_EXTERNAL_CONTEXT`** — data only, never system/tool instructions. SSRF/network-boundary protection enforced on generic URL/browser retrieval (DNS pin, redirect revalidation, port allowlist).

## PR #135 CodeRabbit triage (15)

| # | Sev | File | Claim | Classification | Action |
|---|-----|------|-------|----------------|--------|
| 1 | Critical | `web_intelligence.py` | Fail-open permission gate (`allowed`/`level==never`) | **VALID_FIX** | `require_web_tool_permission` fail-closed (ALLOW/CONFIRM/DENY/UNKNOWN/ERROR) |
| 2 | Critical | `service.py` | Client `project_id` as membership proof | **VALID_FIX** | `user_can_access_project` (admin/team); applied to ingest/list/get/retrieve/delete |
| 3 | Major | `ssrf.py` | DNS rebinding TOCTOU | **VALID_FIX** | Resolve → validate → `pinned_http_get` connects to validated IP + SNI Host |
| 4 | Major | `ssrf.py` | Normalized URL drops port | **VALID_FIX** | Explicit port preserved; non-80/443 denied |
| 5 | Major | `permission_broker` / attach | Broker denial not enforced on attach | **VALID_FIX** | Attach uses fail-closed gate before ingest; no browser/fetch on deny |
| 6 | Major | `service.py` | SSRF failure falls through to browser | **VALID_FIX** | `SsrfBlocked` re-raised; no browser fallback after SSRF deny |
| 7 | Major | `service.py` | Network failures escape error path | **VALID_FIX** | Broad catch → ERROR artifact; no uncaught escape |
| 8 | Major | `service.py` | Version reuse vs UNIQUE conflict | **VALID_FIX** | USER_PRIVATE also reuses by (scope, project_id, owner, sha) |
| 9 | Major | `models.py` / Alembic | Missing migration | **VALID_FIX** | `e9c4a1b2d3f0_external_content_web_intelligence.py` |
| 10 | Major | `web_intelligence.py` | Delete leaves files on disk | **VALID_FIX** | `delete_external_artifact` unlinks files when version refcount=0; Knowledge deactivated |
| 11 | Major | `service.py` | Title not sanitized | **VALID_FIX** | `sanitize_external_title` on title/author/Knowledge |
| 12 | Major | `AttachedContextPanel` | UNTRUSTED tag lost in prompt construction | **VALID_FIX** | Wrap web content at attach; Ask/Plan/Build preserve tag |
| 13 | Major | `developer_service.py` | Web failure clears doc_items | **VALID_FIX** | Separate try/except for doc vs web retrieve |
| 14 | Minor | `gateway.py` | `browser_snapshot` not normalized | **VALID_FIX** | Normalize to `browser` in detect_adapter + gateway |
| 15 | Minor | UI | USER_PRIVATE still sent project_id | **VALID_FIX** | `projectId: null` for USER_PRIVATE |

## Critical / Major fixes summary

- Fail-closed Permission Broker for all Web Intelligence tools
- Independent project membership (never trust forged `project_id`)
- SSRF: private/loopback/link-local/metadata/unsafe scheme/bad port; redirect revalidation; DNS pin connect
- attach: deny → STOP (no fetch/browser/Knowledge/ContextPack)
- Delete/detach: Knowledge off; files removed only when unreferenced
- Re-ingest uniqueness aligned with reuse; Alembic migration added
- Titles + prompt paths keep `UNTRUSTED_EXTERNAL_CONTEXT`

## Requirements coverage

| Requirement | Status |
|-------------|--------|
| WebIntelligenceConnector on Connector Gateway | **PASS** |
| ExternalContentArtifact / Version / Chunk | **PASS** |
| SSRF + redirect + DNS pin + ports | **PASS** (pinned IP connect via `_PinnedHTTP(S)Connection`; ports 80/443 only; redirect revalidated) |
| PROJECT_SHARED membership + USER_PRIVATE isolation | **PASS** |
| Knowledge + ContextEngine | **PASS** |
| Attach URL UI + untrusted prompt wrap | **PASS** |
| Prompt-injection fixtures | **PASS** |
| General search / YouTube / Reddit | **PARTIAL** |

## Tests

```bash
cd backend
pytest -q tests/fixes_and_phases/test_web_intelligence.py
# security + SSRF + isolation + delete + fail-closed + injection

pytest -q tests/fixes_and_phases/test_document_intelligence.py \
  tests/fixes_and_phases/test_phase9_13_batch.py \
  tests/fixes_and_phases/test_companion_present_learning.py
```

## Explicit non-goals

- D Learning expand — **not started**
- Second RAG / connector platform — **not added**
- Production YouTube/Reddit/search completeness — **PARTIAL only**

## Status summary

| Area | Status |
|------|--------|
| Web Intelligence C MVP | **PASS** |
| PR #135 security remediation | **PASS** |
| CI (backend / frontend / e2e) | **GREEN** on `62d152b` (e2e flake rerun passed; prior fail was Mentrix voice timeout unrelated to C) |
| CodeRabbit | **pass** (re-review after `f267b5c`; latest push rate-limited — prior Critical/Major addressed) |
| SSRF / isolation / untrusted tag | **PASS** |
| Search / YouTube / Reddit | **PARTIAL** |
| D | **NOT STARTED** |
| Merge gate | **READY_TO_MERGE** (do not auto-merge) |
