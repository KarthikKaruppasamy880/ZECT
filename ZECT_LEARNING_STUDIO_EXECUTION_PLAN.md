# Learning Studio Execution Plan

Companion to `ZECT_AI_LEARNING_STUDIO_PLAN.md` (the ticket) and
`ZECT_DEVELOPER_CODING_AGENT_ACCEPTANCE.md` (which lists this as the one
remaining named gap: "Learning Studio — plan only"). This is the file-by-file
plan the ticket itself says a future `feat/learning-studio` PR needs before
any code changes.

## Scope boundary — read this first

**This is a net-new, additive feature. It does not touch the existing
`/learning` page.** `frontend/src/pages/ZectLearning.tsx` (784 lines) and
`backend/app/domains/personal_agent/learning.py` (1145 lines) are a real,
working project-based coding-tutor system — languages, paths, projects,
mentor Q&A, practice verification, mastery tracking, skill graduation. That
system teaches general programming skills and is unrelated to what the
ticket describes. Confirmed by grep: neither file references Lattice or
`KnowledgeEntry` anywhere — they don't overlap in data or purpose with what
follows. Do not merge, rename, or delete anything there.

"Learning Studio" per the ticket is a *different* thing: a catalog/lesson/
quiz surface grounded in **this workspace's own indexed content** (Lattice
graph + Knowledge Base entries), for learning about the codebase/company
knowledge you've actually indexed — not a programming-language curriculum.

## Existing interfaces to reuse (no new indexing pipeline needed)

| Need | Existing function | File |
|---|---|---|
| Lattice search/explain | `query_graph()`, `explain()`, `neighbors()` | `app/services/lattice/indexer.py` |
| Lattice freshness gate | `get_lattice_status()` — returns NOT_CONFIGURED/NOT_INDEXED/INDEXING/READY/STALE/ERROR/NOT_APPLICABLE | `app/services/lattice/indexer.py:733` |
| Knowledge Base search | `search_entries()` (`POST /search`), `retrieve_knowledge_for_context()` | `app/domains/repository/knowledge_base.py` |
| Hybrid code+doc retrieval | `hybrid_retrieve()` | `app/services/rag/retriever.py:130` |

The ticket's own "out of scope" list already says no new tables — this is
achievable as a pure retrieval + presentation layer, generating
catalog/lesson/quiz content live from the above at request time, not a new
content-authoring/storage system.

## Backend — one new file

`app/domains/personal_agent/learning_studio.py` (new router, mounted under
the existing Personal Agent domain — matches `TARGET_ARCHITECTURE.md`'s
diagram; no new top-level domain needed for one router):

- `GET /learning-studio/status?project_key=` — thin wrapper over
  `get_lattice_status()`. If not READY, the frontend must show "re-index"
  and stop — **never fall through to generating a syllabus anyway**. This
  is the ticket's bullet 4 and the single most important gate in this
  feature; test it first.
- `GET /learning-studio/catalog?project_key=` — build topic list from
  `query_graph()` node categories (modules/classes with doc-comments) +
  `list_categories()`/`search_entries()` from Knowledge Base. Each catalog
  entry carries a `source_refs: [{type: "lattice"|"knowledge", id, path}]`
  — no entry without at least one real source ref.
- `GET /learning-studio/lesson/{topic_id}?project_key=` — assembles lesson
  body from `explain()` (Lattice) and/or the matched `KnowledgeEntry` body,
  with inline citations back to `source_refs`. If an LLM is used to
  *phrase* the lesson prose, the prompt must include the grounding content
  and the response must be rejected/retried if it introduces a claim not
  traceable to a source_ref (mirror `review_phase_svc.py`'s
  grounding-check pattern already in this codebase).
- `POST /learning-studio/quiz/{topic_id}/generate` — same grounding
  contract: every question must cite the `source_ref` it was generated
  from. Reject generation if the lesson has zero source_refs (do not
  fabricate a quiz for an empty lesson).

## Frontend — new tab, not a new sidebar item

Do **not** add a new primary-nav entry (sidebar already has "ZECT
Learning" pointing at the unrelated PBL system, and the ticket says
Developer must not host this). Add a **"Studio" tab inside the existing
`ZectLearning.tsx`** page, next to its current Paths/Projects/Mentor tabs:

- New tab renders catalog → lesson → quiz, each state driven by the
  `/learning-studio/status` gate (mirror the existing
  `context-used-lattice` state-badge pattern already used elsewhere in this
  codebase for NOT_INDEXED/STALE/READY display — same states, same visual
  language, nothing new to invent).
- `MentrixCompanion.tsx` gets a small "Open Learning Studio" link
  (ticket bullet 3: Companion can open it) pointing at `/learning?tab=studio`.
- If `project_key` has no Lattice index yet, the tab's only action is
  "Re-index" (links to the existing Lattice ingest flow) — no placeholder
  syllabus, no "coming soon" fake content.

## Explicitly out of scope for the first PR

- New DB tables (ticket says so directly; catalog/lesson/quiz are
  generated live, not authored/stored — quiz *attempt history*, if wanted
  later, is a separate follow-up, not part of this PR).
- Any change to the existing `/learning` PBL/mentor/practice system.
- A standalone `/learning-studio` route — it's a tab, not a page.

## Test plan

- `test_learning_studio_status_gate.py` — STALE/NOT_INDEXED short-circuits
  catalog/lesson/quiz endpoints with a clear re-index response; READY
  proceeds.
- `test_learning_studio_grounding.py` — catalog/lesson/quiz entries always
  carry `source_refs`; mock the LLM to try returning an ungrounded claim
  and assert it's rejected (same shape as the existing offline-heuristic /
  grounding tests already in `tests/fixes_and_phases/`).
- Frontend: a render test for the new Studio tab's three states
  (not-indexed / loading / grounded-content-with-citations), following the
  existing pattern in `MentrixCompanion.layout.test.tsx`.

## Verification checkpoint

Full backend suite (`cd backend && python -m pytest -q`) unchanged pass
count plus the new tests above; `tsc --noEmit` clean; existing
`ZectLearning.tsx`/`learning.py` tests unchanged (proves no regression to
the unrelated PBL system this PR must not touch).
