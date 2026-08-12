# ZECT Document Intelligence (B) — Acceptance

**Date:** 2026-08-12  
**Branch:** `feat/zect-document-intelligence-b`  
**Prompt:** Document Intelligence §B (+ SHA-256 dedupe/versioning + provenance freshness additions)  
**Master plan:** `.cursor/plans/master_live_product_fix_a8c0797d.plan.md`  
**Stop condition:** STOP after B — **C (Web Intelligence) and D (Learning expand) not started.**

## Frozen baselines preserved

| Gate | Status |
|------|--------|
| Present A1–A8 / LIVE_VIABLE | FROZEN (not redesigned) |
| `zinnia-executive-v1` | FROZEN |
| PresentationProvider / Present Model Gateway | FROZEN |
| Voicebox async / A6 voice FSM | FROZEN |
| Electron single-instance | FROZEN |
| Phase 5–13 (nav, onboarding, PI, ASK/PLAN/AGENT+LRR, Learning, gateway, isolation) | FROZEN |

## Verdict

**PASS with honest PARTIAL capabilities** for OCR/scanned PDF, XLSX, and image-layout/table/formula completeness.

Document Intelligence reuses Mentrix spine only: KnowledgeEntry indexing, MentrixContextEngine / ProvenanceItem, Permission Broker actions, Phase-13 scopes (`USER_PRIVATE` / `PROJECT_SHARED`). **No second RAG/vector/memory system.**

## Requirements coverage

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| Upload / parse / store documents | `POST /api/documents/upload`; disk under `.zect/documents/` (or `ZECT_DOCUMENT_ROOT`) | **PASS** |
| Formats MVP: TXT/MD/DOCX/PDF-text/PPTX | `parse_document` in `services/document_intelligence/service.py` | **PASS** (PDF text when pypdf/PyPDF2 present) |
| OCR / scanned PDF | Stub / text-extract only; capability flagged | **PARTIAL** |
| XLSX | Not production parser; listed in `partial_capabilities` | **PARTIAL** |
| Image layout / table / formula completeness | DOCX tables/formulas not fully recovered; flagged | **PARTIAL** |
| SHA-256 content-version identity | `DocumentContentVersion` unique on scope+project+owner+sha256 | **PASS** |
| PROJECT_SHARED reuse same parsed version | Second upload same bytes → `reused_shared_version=true`, same `content_version_id` | **PASS** |
| USER_PRIVATE owner-isolated even if hashes match | Separate content versions per owner; cross-user retrieve denied | **PASS** |
| New versions do not silently reuse stale chunks | Supersede marks old chunks `freshness=stale`; retrieve requires current + sha match | **PASS** |
| Provenance on chunks / source map | artifact_id, content_version_id, sha256, page/slide/heading/offset | **PASS** |
| Retrieval exposes freshness; no stale in ContextPack | `retrieve_document_context` + ContextEngine stale filter | **PASS** |
| Knowledge + ContextEngine bridge | KnowledgeEntry on ingest; ASK pack `extra_items` | **PASS** |
| Permission Broker | `document_upload` / `document_retrieve` → companion docs actions | **PASS** |
| Shared Add Context UI | `AttachedContextPanel` Upload Document + provenance chips | **PASS** |
| Untrusted tagging | `UNTRUSTED_DOCUMENT_CONTEXT` / sanitize_for_prompt | **PASS** |

## API surface

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/documents/upload` | multipart file + scope/project |
| GET | `/api/documents` | list current artifacts (owner + shared) |
| GET | `/api/documents/{id}` | metadata + source_map |
| GET | `/api/documents/{id}/markdown` | markdown + freshness/sha |
| POST | `/api/documents/retrieve` | provenance items + optional ContextPack |
| DELETE | `/api/documents/{id}` | supersede (owner) |

## Files changed (exact)

**Backend**
- `backend/app/models.py` — `DocumentContentVersion`, `DocumentArtifact`, `DocumentChunk`
- `backend/app/services/document_intelligence/` — parsers, ingest, retrieve
- `backend/app/domains/repository/document_intelligence.py` — HTTP API
- `backend/app/domains/repository/__init__.py`
- `backend/app/api/register.py`
- `backend/app/services/mentrix/permission_broker.py`
- `backend/app/services/work_items/context_engine.py` — refuse stale document extras
- `backend/app/services/work_items/developer_service.py` — document extras in ContextPack
- `backend/tests/fixes_and_phases/test_document_intelligence.py`

**Frontend**
- `frontend/src/lib/api.ts` — document client helpers
- `frontend/src/components/AttachedContextPanel.tsx` — Upload Document + provenance

**Docs**
- `ZECT_DOCUMENT_INTELLIGENCE_ACCEPTANCE.md` (this file)

## Tests

```bash
cd backend
pytest -q tests/fixes_and_phases/test_document_intelligence.py
# → 7 passed (parsers, shared reuse, private isolation, stale exclusion, provenance, PDF PARTIAL, API upload/retrieve)

# Frozen smoke (preserve):
pytest -q tests/fixes_and_phases/test_phase9_13_batch.py tests/fixes_and_phases/test_companion_present_learning.py
# → 27 passed
```

## Security / isolation

- Auth required on all document routes.
- `USER_PRIVATE` filtered by `user_id`.
- `PROJECT_SHARED` keyed by project + sha reuse; private versions never shared across owners.
- Document text sanitized and tagged untrusted before prompt injection.
- Stale / superseded versions excluded from retrieve and ContextPack.

## Explicit non-goals (this tranche)

- C Web Intelligence — **not started**
- D Learning expand — **not started**
- Second vector DB / parallel memory store — **not added**
- Production OCR / XLSX / full layout fidelity — **PARTIAL only**

## Status summary

| Area | Status |
|------|--------|
| Document Intelligence B core | **PASS** |
| Dedupe / versioning / freshness | **PASS** |
| OCR / XLSX / layout-table-formula | **PARTIAL** |
| C / D | **NOT STARTED** (stop condition honored) |
