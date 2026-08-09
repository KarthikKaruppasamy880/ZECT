# REQUIREMENTS — Mentrix P2 UX + P3 native interfaces

**Work item key:** ZECT-MENTRIX-P2-P3-REMAINING
**Depends on:** P0 + P1 merged on develop
**Rule:** Reuse MentrixDeveloperService / ContextEngine / Coding Agent / Ultra Review engine — no parallel systems.

## P2 — UX Simplification

| ID | Requirement |
|----|-------------|
| R1 | Sidebar regrouped to MENTRIX / WORK / INTELLIGENCE / DELIVERY / SECURITY / OPERATIONS / SETTINGS |
| R2 | Work Items page lists WorkItems via existing `/api/work-items` |
| R3 | Project Intelligence page shows live PI snapshot via developer API |
| R4 | System Health surface aggregates readiness (API, auth, coding engine, Lattice, Jira/Camunda config) |
| R5 | Skills filesystem dual-read from `.zect/skills/*/SKILL.md` into Skills listing/PI (DB remains SoT for execution) |
| R6 | Ultra Review 3-lane merger (Requirements / Engineering / Security) over existing findings — no second review LLM |
| R7 | Playwright smoke updated for new nav; critical smoke paths green locally when stack up |

## P3 — Scoped native infrastructure (interfaces only)

| ID | Requirement |
|----|-------------|
| R8 | `SecurityScanner` interface + adapter wrapping existing Security Agent path |
| R9 | Local model readiness endpoint hook (openai_compat / gateway status) — no new model stack |

## Non-goals

- Full Playwright suite green as hard DoD (smoke + nav updates)
- Full desktop automation rewrite
- New coding/review engines
