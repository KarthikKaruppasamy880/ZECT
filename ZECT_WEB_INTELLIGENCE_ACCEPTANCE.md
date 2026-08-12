# ZECT Web Intelligence (C) — Acceptance

**Date:** 2026-08-12  
**Branch:** `feat/zect-web-intelligence-c`  
**Base:** `develop` @ `e06bb421b85131acc0681dd0e6b932ceed2803bf` (B MERGED/FROZEN)  
**Prompt:** `prompts/Cursor Prompt — Execute C Web Intelligence.md`  
**Plan:** `.cursor/plans/zect_web_intelligence_c_plan.md`  
**Stop condition:** STOP after C — **D (Learning expand) not started.**

## Frozen baselines preserved

| Gate | Status |
|------|--------|
| Present A1–A8 / LIVE_VIABLE | FROZEN |
| Phases 5–13 | FROZEN |
| B Document Intelligence | **MERGED / FROZEN** (`e06bb42`) |
| Connector Gateway / Permission Broker / ContextEngine / Model Gateway | Extended, not replaced |

## Verdict

**PASS (MVP)** with honest **PARTIAL** for general web search, YouTube transcripts, and Reddit/public discussions.

All external content tagged **`UNTRUSTED_EXTERNAL_CONTEXT`** — data only, never system/tool instructions. SSRF/network-boundary protection enforced on generic URL/browser retrieval.

## Requirements coverage

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| WebIntelligenceConnector on Connector Gateway | `connectors/gateway.py` id=`web` | **PASS** |
| ExternalContentArtifact / Version / Chunk | `models.py` | **PASS** |
| Approved URL retrieval | `fetch_url` + SSRF | **PASS** |
| RSS/Atom | `fetch_rss` | **PASS** |
| GitHub via trusted path | `fetch_github` (raw/API hosts) | **PASS** |
| Browser snapshot + confirm | adapter=browser + Permission Broker ALWAYS_CONFIRM | **PASS** |
| SSRF deny localhost/private/metadata/unsafe schemes | `web_intelligence/ssrf.py` + redirect revalidation + size/timeout/content-type | **PASS** |
| PROJECT_SHARED requires project_id | retrieve/list/get gates | **PASS** |
| USER_PRIVATE owner isolation | per-owner content versions | **PASS** |
| Provenance / freshness | sha, url, connector, adapter, heading/offset; stale excluded | **PASS** |
| Knowledge + ContextEngine | `source=web_intelligence` excluded from generic dumps; `extra_items` in developer pack | **PASS** |
| Attach URL UI | `AttachedContextPanel` | **PASS** |
| Prompt-injection fixtures | malicious strings sanitized; fence neutralized | **PASS** |
| General search / YouTube / Reddit | listed in `partial_capabilities` | **PARTIAL** |

## API surface

| Method | Path |
|--------|------|
| POST | `/api/web/attach` |
| GET | `/api/web` |
| GET | `/api/web/{id}` |
| GET | `/api/web/{id}/markdown` |
| POST | `/api/web/retrieve` |
| DELETE | `/api/web/{id}` |

## Tests

```bash
cd backend
pytest -q tests/fixes_and_phases/test_web_intelligence.py
# → 10 passed (SSRF, injection, shared/private, stale, browser confirm, connector, PARTIAL caps)

# Frozen + B:
pytest -q tests/fixes_and_phases/test_document_intelligence.py \
  tests/fixes_and_phases/test_phase9_13_batch.py \
  tests/fixes_and_phases/test_companion_present_learning.py
# Combined with C: 46 passed
```

## Explicit non-goals

- D Learning expand — **not started**
- Second RAG / connector platform — **not added**
- Production YouTube/Reddit/search completeness — **PARTIAL only**

## Status summary

| Area | Status |
|------|--------|
| Web Intelligence C MVP | **PASS** |
| SSRF / isolation / untrusted tag | **PASS** |
| Search / YouTube / Reddit | **PARTIAL** |
| D | **NOT STARTED** |
