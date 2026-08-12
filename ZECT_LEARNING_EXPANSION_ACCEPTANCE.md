# ZECT Learning Expansion (D) — Acceptance

**Date:** 2026-08-12  
**Branch:** `feat/zect-learning-expansion-d`  
**Status:** **IMPLEMENTED — READY FOR PR** (not merged; freeze after merge to `develop`)  
**Base:** `develop` @ `d466660168cfc7e4e4d13816c1a920c985b672a9` (C MERGED/FROZEN) + freeze docs `caa51bf`  
**Plan:** `ZECT_LEARNING_EXPANSION_D_PLAN.md` / `prompts/ZECT_LEARNING_EXPANSION_D_PLAN.md`  
**Stop condition:** **STOP after D** — do not auto-start Ultra Review, packaging, Graphify, OCR/XLSX, or other roadmap work.

## Frozen baselines preserved

| Gate | Status |
|------|--------|
| Present A1–A8 / LIVE_VIABLE | FROZEN |
| Phases 5–7 | FROZEN |
| Phase 8 ASK / PLAN / AGENT + Developer / LRR | FROZEN (handoff target only) |
| Phase 9–13 Learning catalog + isolation | FROZEN (extended, not replaced) |
| B Document Intelligence | MERGED / FROZEN (`e06bb42`) — optional untrusted study notes |
| C Web Intelligence | MERGED / FROZEN (`d466660`) — optional untrusted study notes |
| EvidenceVerifier / Skills / Mentrix / ContextEngine | Reused — **no second system** |

## Three mandatory rules (enforced)

| # | Rule | Enforcement |
|---|------|-------------|
| 1 | Progress/mastery **evidence-backed** by exercise/test/project results — never LLM assertion alone | Practice verify → EvidenceVerifier; `user_confirmed` alone cannot complete; mastery uses accumulated verified evidence |
| 2 | **GUIDED** preserves learner ownership — Mentrix explains / questions / progressive hints; no silent full solution/commit | Mentor `reject_guided_full_solution` + progressive hint ladder; PAIR/DEMO/AUTONOMOUS may use Coding Agent via Developer handoff per mode/policy |
| 3 | Skill graduation needs **accumulated** verified evidence; one completion ≠ mastery | `MIN_VERIFIED_LESSONS_FOR_PROFICIENCY` (≥2) + verified tests threshold; single-lesson graduate returns 400 |

## Work packages

| WP | Deliverable | Status |
|----|-------------|--------|
| D1 | Curriculum Path/Lesson seeds (`python-fundamentals`, `typescript-basics`) | **PASS** |
| D2 | Practice FSM + EvidenceVerifier gates | **PASS** |
| D3 | Mentrix Mentor progressive hints (GUIDED no auto-solve) | **PASS** |
| D4 | Developer WorkItem handoff + SkillDefinition draft (approval_required) | **PASS** |
| D5 | `ZectLearning.tsx` path/lesson/practice/hint/evidence/handoff/graduate | **PASS** |
| D6 | Isolation + security tests (`test_learning_expansion.py`) | **PASS** |
| D7 | This acceptance artifact | **PASS** |

## Key surfaces

| Layer | Location |
|-------|----------|
| Curriculum | `backend/app/services/learning/curriculum.py` |
| Practice FSM | `backend/app/services/learning/practice_fsm.py` |
| Mentor | `backend/app/services/learning/mentor.py` |
| Mastery | `backend/app/services/learning/mastery.py` |
| Handoff / graduate | `backend/app/services/learning/handoff.py` |
| API (extend Phase 9) | `backend/app/domains/personal_agent/learning.py` |
| UI | `frontend/src/pages/ZectLearning.tsx` |
| Tests | `backend/tests/fixes_and_phases/test_learning_expansion.py` |

## Isolation / security

- Learning projects scoped via `_owned_project` — cross-user lookup returns **404** (no existence leak).
- Progress / drafts remain **USER_PRIVATE**.
- B Document / C Web study notes stay optional **untrusted** context with existing provenance rules — never elevated to system/tool instructions.
- Skill graduate drafts require Permission Broker path with `approval_required=True`.

## Frozen regression smoke (2026-08-12)

```bash
cd backend
pytest -q tests/fixes_and_phases/test_learning_expansion.py \
  tests/fixes_and_phases/test_web_intelligence.py \
  tests/fixes_and_phases/test_document_intelligence.py \
  tests/fixes_and_phases/test_phase9_13_batch.py \
  tests/fixes_and_phases/test_companion_present_learning.py
# → 60 passed
```

## Honest PARTIAL / non-goals

| Item | Status |
|------|--------|
| Full multi-language deep curricula beyond Python + TypeScript seeds | **PARTIAL** — catalog + chips remain; more paths can seed later |
| Live Coding Agent auto-run inside GUIDED practice | **NOT DONE** (by design — GUIDED forbids; PAIR/DEMO/AUTONOMOUS via Developer handoff) |
| Second Learning/RAG/agent/evidence system | **NOT ADDED** |
| Ultra Review / packaging / Graphify / OCR-XLSX | **NOT STARTED** (stop after D) |
| Org-wide multi-tenant curricula platform | **OUT OF SCOPE** |

## Verdict

**PASS (feature branch)** — D1–D7 complete on `feat/zect-learning-expansion-d` with evidence-backed progress, GUIDED ownership, accumulated mastery, and frozen B/C/Phase9–13/Present smoke green (**60 passed**).

**Next (manual):** open PR to `develop` when ready; freeze after merge. Do not auto-start post-D roadmap work.
