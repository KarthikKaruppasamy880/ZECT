# D — ZECT Learning Expansion — Execution Plan

**Branch:** `feat/zect-learning-expansion-d`  
**Base:** `develop` @ `d466660168cfc7e4e4d13816c1a920c985b672a9` (C MERGED/FROZEN)  
**Status:** **PLANNING ONLY — STOP before implementation**  
**Date:** 2026-08-12

## Purpose

Expand ZECT Learning beyond the Phase 9 **catalog-usable** path into a deeper **Learn → Practice → Code → Test → Evidence → Verified Progress → Project/Skills graduation** loop — without creating a second assistant, RAG, orchestrator, or evidence system.

## Frozen baselines (must not reopen)

| Gate | Merge / status |
|------|----------------|
| Present A1–A8 / LIVE_VIABLE | FROZEN |
| Phases 5–7 | FROZEN |
| **Phase 8** ASK / PLAN / AGENT + LRR + Developer Workspace | FROZEN |
| **Phase 9–13** Learning catalog + gateway + isolation | MERGED `3bffa7d` / FROZEN |
| **B Document Intelligence** | MERGED `e06bb42` / FROZEN |
| **C Web Intelligence** | MERGED `d466660` / FROZEN |
| Model Gateway / Permission Broker / Connector Gateway / ContextEngine / EvidenceVerifier | Extend only |

Do **not** restore unrelated stash/WIP.

---

## Reconciliation — what already exists vs what D adds

### Already shipped (do not rebuild)

| Layer | Existing asset | Implication for D |
|-------|----------------|-------------------|
| Phase 9 Learning API | `backend/app/domains/personal_agent/learning.py` — languages, sources, resources, projects, progress, practice/verify | **Extend** endpoints/progress model; do not fork |
| Phase 9 UI | `frontend/src/pages/ZectLearning.tsx` — Explore → Practice → Evidence | **Extend** path/lesson UX; keep Mentrix spine |
| Catalog | `LearningSource` / `LearningResource` / `LearningProject` + PBL sync | Reuse; deepen curricula metadata |
| Modes | `GUIDED \| PAIR \| DEMO \| AUTONOMOUS` | Preserve GUIDED no auto-solve |
| Evidence | `EvidenceVerifier` via `_verify_learning_evidence` | Sole completion authority; no LLM “done” |
| Languages | Python, JS/TS, Java, C#, Go, Rust, C/C++ chips | Keep; add path depth per language |
| Phase 8 Developer | Developer Workspace, ContextPack, LRR, Coding/Test agents | Learning **hands off** to Developer/Coding Agent for Project stage — no parallel IDE |
| Phase 8 ASK/PLAN/AGENT | WorkItem + run state authoritative | Learning Project may link a WorkItem; never invent a second run store |
| Skills / Playbooks | `skills_engine`, `SkillDefinition`, playbooks | Graduation target = Skill/Playbook promotion, not new skill platform |
| B Documents | Document Intelligence + AttachedContextPanel | Optional lesson attachments as USER_PRIVATE docs; reuse B ingest |
| C Web | Web Intelligence + `UNTRUSTED_EXTERNAL_CONTEXT` | External tutorials remain **link-only or untrusted attach**; never system instructions |
| Isolation | USER_PRIVATE progress; PROJECT_SHARED repo intel | Personal Learning progress stays USER_PRIVATE |

### Gaps D must close (expanded Learning)

| Gap | Spec source | D deliverable |
|-----|-------------|----------------|
| Thin “path” (resource → project) without lesson graph | Phase 9–13 batch prompt; Phase9 acceptance “Expanded Learn curriculum not started” | Explicit **Learning Path → Topic/Lesson** model + ordered steps |
| Practice not consistently wired to Code → Tests → Hint → Retry | Same | Structured practice session FSM with EvidenceVerifier gates |
| Weak Skills graduation | Phase9_13 acceptance D tranche | Verified progress → optional SkillDefinition/Playbook draft (Permission Broker) |
| Mentor / hint quality vs GUIDED solve risk | Phase 9 rules | Hint API that cannot submit full solution in GUIDED |
| No first-class handoff to Developer Workspace | Phase 8 ownership | “Open in Developer / start Coding Agent” from verified Project stage |
| Curriculum content mostly PBL links | Catalog sync | Seed deeper internal lesson stubs + keep external attribution/license/policy |
| Docs/Web not part of learning context | B+C merged | Optional attach of USER_PRIVATE doc/web as **untrusted study notes** into ContextPack for mentor/practice only |

### Explicit non-goals (D)

- Second Mentrix / companion / RAG / ContextEngine
- Second EvidenceVerifier or shipping authority
- Auto-solving GUIDED exercises
- Replacing Phase 8 Developer / LRR
- Expanding general Search / YouTube / Reddit beyond C PARTIAL
- Reopening Present / packaging installer claims
- Multi-tenant org curricula platform (keep USER_PRIVATE first)

---

## Target user flow (canonical)

```text
Choose Language / Skill
→ Learning Path (ordered)
→ Topic / Lesson
→ Practice prompt
→ Code (sandbox / practice verify)
→ Run Tests (EvidenceVerifier)
→ Hint (GUIDED: partial only)
→ Retry
→ Evidence recorded
→ Verified Progress
→ Project (optional WorkItem / Developer handoff)
→ Skills graduation (optional Skill/Playbook draft)
```

---

## Work packages (implementation order — when approved)

### D0 — Branch hygiene & acceptance skeleton
- Keep `feat/zect-learning-expansion-d` based on frozen `develop`
- Add `ZECT_LEARNING_EXPANSION_ACCEPTANCE.md` (empty gates) when implementation starts
- Frozen smoke before/after: C + B + phase9_13 + companion_present

### D1 — Curriculum model
- Path / Lesson entities (or JSON progress schema on `LearningProject`) with order, skill tags, difficulty
- Preserve source URL, license, content_policy, attribution
- Seed 1–2 deep paths per priority language (start: Python + TypeScript)

### D2 — Practice FSM + Evidence
- Events: `lesson_started`, `practice_attempt`, `hint_used`, `test_passed`, `user_confirmed`, `completed`
- `user_confirmed` alone **cannot** complete
- Wire practice verify → EvidenceVerifier (extend existing `_verify_learning_evidence`)
- GUIDED: reject payloads that look like full auto-solutions from mentor

### D3 — Mentrix Learning Advisor integration
- Mentor/hint via existing Mentrix tools + Permission Broker
- ContextPack may include: lesson text + optional B/C untrusted notes (tagged)
- No new LLM gateway

### D4 — Developer / Skills handoff
- From verified Project: create/link WorkItem → open Developer Workspace / Coding Agent
- Optional “Graduate to Skill” → SkillDefinition draft (CONFIRM)
- Playbook step optional; do not rebuild playbook engine

### D5 — UI
- Extend `ZectLearning.tsx`: path navigator, lesson panel, hint/retry, evidence timeline, handoff CTAs
- Persist language/path/project selection (Phase 5 state patterns)
- No IA redesign of frozen Present/Developer shells

### D6 — Security & isolation
- Learning progress USER_PRIVATE by default
- Fail-closed Permission Broker for mentor/code/skill tools
- Untrusted doc/web study notes never elevated to system/tool instructions
- Tests: cross-user progress isolation; GUIDED no auto-solve; evidence gate; handoff auth

### D7 — Acceptance & freeze
- Fill `ZECT_LEARNING_EXPANSION_ACCEPTANCE.md`
- PR to `develop`; freeze after merge
- Stop; do not auto-start packaging or other roadmaps

---

## Test / regression gate (mandatory)

```bash
cd backend
pytest -q tests/fixes_and_phases/test_web_intelligence.py \
  tests/fixes_and_phases/test_document_intelligence.py \
  tests/fixes_and_phases/test_phase9_13_batch.py \
  tests/fixes_and_phases/test_companion_present_learning.py
# plus new test_learning_expansion.py when implementing
```

Preserve Present smoke via `test_companion_present_learning.py`.

---

## Decision summary

| Question | Answer |
|----------|--------|
| New Learning product? | **No** — expand Phase 9 path |
| New RAG / agent? | **No** |
| Completion authority? | **EvidenceVerifier only** |
| Code practice host? | Existing practice verify → later Developer/Coding Agent |
| Docs/Web role? | Optional untrusted study context via B/C |
| Skills role? | Graduation target, not new platform |
| Start coding now? | **NO — STOP after this plan** |

---

## Stop condition

Planning complete on `feat/zect-learning-expansion-d`.  
**Do not implement D until explicitly approved.**
