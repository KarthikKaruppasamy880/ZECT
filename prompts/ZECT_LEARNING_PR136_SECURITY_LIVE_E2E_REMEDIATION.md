# ZECT Learning PR #136 — Security Remediation + Live E2E

## Goal
PR #136 remains blocked. Fix verified Mentrix Ultra Review M1–M3 on the SAME PR, then prove ZECT Learning through the real running application with Playwright/browser automation. Do not auto-merge.

## M1 — Client-forged evidence
Never trust client fields such as `passed`, `exit_code`, `test_passed`, `completed`, or `verified` as authoritative evidence.

Required:
`submission → server-controlled test definition → Test Agent/deterministic runner → real result → evidence artifact → EvidenceVerifier → verified progress`.

Bind evidence to authenticated user, lesson/exercise, version/submission, run, and timestamp. Forged `passed=true` must not create completion/mastery.

## M2 — Forged WorkItem
Never trust client `work_item_id` as authorization. Independently verify authenticated user/org/project/WorkItem access before reading or handing off to Developer. Unauthorized IDs must return 403/404 and leak no title/context/project/repo/plan details.

## M3 — Forged progress/mastery
Separate user state (`viewed`, `started`, drafts, retries) from server-verified evidence (tests passed, lesson/project verified, skill evidence/mastery). `/progress` must not allow clients to manufacture verified completion. `user_confirmed` alone is insufficient.

## Preserve Learning rules
- Progress/mastery is evidence-backed.
- GUIDED preserves learner ownership and cannot silently solve/commit the full solution.
- PAIR/DEMO/AUTONOMOUS may progressively use the existing Coding Agent according to policy.
- One completion does not equal mastery.
- Skill graduation requires accumulated verified evidence (currently >=2 qualifying verified lessons/tests unless canonical policy changed).
- B/C context remains governed and untrusted.

## Start the real application
After fixes, start the actual ZECT backend/frontend and prove:
- backend reachable
- frontend reachable
- authentication works
- Learning route renders
- required APIs respond
- no blocking console/network errors

Do not substitute mocks/unit tests. If runtime cannot start, report the exact blocker and remain PARTIAL/BLOCKED.

## Required Playwright/browser flow
Use existing repository Playwright/browser automation; MCP Playwright is not required if existing tooling can drive the real app.

Prove:
`Login → ZECT Learning → Python fundamentals → lesson → practice → submit failing code → real FAIL → progressive hint → retry → passing code → server-controlled tests PASS → EvidenceVerifier → progress updates → navigate away/back → progress persists → second qualifying verified lesson/test → skill graduation eligible → Developer WorkItem handoff`.

Capture browser/API evidence.

## Negative security tests
Prove:
- forged `passed=true` → no verified lesson/mastery/graduation
- forged `completed=true` / `test_passed=true` → ignored/rejected as authority
- foreign `work_item_id` → 403/404, no metadata leak/handoff
- cross-user Learning progress/drafts/evidence access denied
- GUIDED request for full solution → hints/explanation only, no silent full implementation

## B/C prompt-injection containment
B/C study context remains `UNTRUSTED_DOCUMENT_CONTEXT` / `UNTRUSTED_EXTERNAL_CONTEXT`.

Test malicious content such as:
`Ignore previous instructions`, `Reveal secrets`, `Read local files`, `Execute shell`, `Commit full solution`, `Disable GUIDED`, `Mark lesson complete`.

It may be summarized as data but must not trigger tools, override policy, or manufacture completion.

## Browser/Test Agent capability audit
Determine whether existing Test Agent/Developer tooling can:
- start/verify app
- invoke Playwright
- navigate/authenticate
- click/type/select/submit
- inspect network/API and console failures
- capture screenshots/traces/evidence
- fail acceptance on UI/runtime errors

Report `ALREADY_BUILT | PARTIAL | MISSING`. Do not create a duplicate browser framework. Implement only minimal reusable integration if existing Playwright lacks required wiring.

## Re-run Ultra Review
After fixes/live acceptance, review the new PR #136 head. M1–M3 must be `VERIFIED_RESOLVED`. Any new verified Critical/Major finding blocks merge.

## Tests/regression
Run:
- Learning targeted tests
- live Playwright Learning acceptance
- B Document Intelligence regression
- C Web Intelligence regression
- Phase 9–13 regression
- Companion/Present frozen smoke
- relevant Phase 5–8 frozen smoke

Use current master plan/acceptance docs as authoritative baseline.

## Acceptance evidence
Update `ZECT_LEARNING_EXPANSION_ACCEPTANCE.md` with M1–M3 fixes, server evidence, WorkItem authorization, anti-forgery proof, real app startup, Playwright flow, fail/hint/retry/pass evidence, EvidenceVerifier, persistence, graduation, Developer handoff, isolation, GUIDED behavior, B/C injection containment, browser-tool status, final Ultra Review, CI and frozen regressions.

## Merge gate
Return `READY_TO_MERGE` only when:
- M1–M3 VERIFIED_RESOLVED
- real ZECT application runs
- live browser flow passes
- negative security tests pass
- no unresolved verified Critical/Major Ultra Review findings
- CI green
- frozen regressions pass

If browser automation cannot run, report `PARTIAL`, `BLOCKED`, or `BLOCKED_EXTERNAL` with exact reason. Do not substitute unit tests for live acceptance.

## Stop
Do not auto-merge PR #136. Do not start unrelated roadmap work, packaging, Graphify, OCR/XLSX, or the Ultra Review closed-loop redesign. Stop after remediation + live acceptance + re-review.

## Canonical rule
`User-facing feature → static review → unit/API tests → real running app → browser/Electron E2E → security-negative tests → review → EvidenceVerifier → LIVE_VIABLE`.

Do not declare user-facing features LIVE_VIABLE from unit/static evidence alone when real UI verification is practical.
