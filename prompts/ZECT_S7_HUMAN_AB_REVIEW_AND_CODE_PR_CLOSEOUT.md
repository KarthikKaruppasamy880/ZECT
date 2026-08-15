# ZECT — S7 HUMAN A/B REVIEW + CODE/PR CLOSEOUT

## Mission
Prepare existing blinded A/B decks for local PowerPoint review AND audit/commit/publish all intended S7.5/S7.6 code, tests and acceptance docs. Do not score decks, reveal mapping, switch provider defaults, start S8C/S8D or auto-merge.

Official verdict remains `NATIVE_NOT_READY / NOT_READY_FOR_S8C`.

## 1 Git truth
Fetch and record current branch, HEAD, origin/develop, working tree/staged/untracked/stashes and commits since the last merged native baseline/PR #152. Identify what is committed/pushed/PR'd/merged/local/untracked.

Produce:
`Path | Purpose | Product code? | Test? | Doc? | Generated/runtime? | Commit? | PR? | Action`.

Never expose credentials.

## 2 Classify all changes
Use:
`PRODUCTION_CODE | PRODUCTION_TEST | E2E_TEST | ACCEPTANCE_DOC | ARCHITECTURE_DOC | PROMPT_PLAN | REVIEW_MATERIAL | GENERATED_TEST_ARTIFACT | RUNTIME_DATA | CACHE | SECRET_SENSITIVE | UNRELATED_WIP`.

Commit intended native planner/VisualPlanner/layout/template/security code and authoritative tests. Commit tracked acceptance docs where policy permits. Normally exclude generated A/B PPTX/PDF/PNG, traces/videos/logs/caches/runtime uploads. Preserve unrelated WIP. Never expose/accidentally commit `PRIVATE_MAPPING.json` if it is review-blinding/runtime data. Check/harden `.gitignore` only for genuine artifact-leak risk.

## 3 Validate production diff
For every production change explain purpose and S7.5/S7.6 linkage. Run focused backend/unit, frontend/e2e, security and frozen regression. Verify Presenton-default regression safety, native zero-Presenton-call proof and Model Gateway planner/security behavior. Run Mentrix Ultra Review on final diff; fix valid branch-introduced Critical/Major findings. Do not change product code merely to simplify review opening.

## 4 Clean commits
Use repository conventions; suggested grouping:
1. `feat(present): harden native LLM planning and visual quality`
2. `test(present): add S7 native quality and parity coverage`
3. `docs(present): record S7.5/S7.6 acceptance and human review gate`

Before each commit show exact file list and ensure no secrets/generated/runtime artifacts.

## 5 Push/PR
If GitHub auth exists: push focused branch → PR to develop → backend/frontend/e2e CI → live Mentrix Ultra Review → substantive CodeRabbit if available → fix valid Critical/Major on same PR → rerun gates. Presenton remains default. DO NOT merge; stop at `READY_TO_MERGE`.

If auth unavailable, preserve local commits and report `BLOCKED_EXTERNAL` for push/PR only.

## 6 PowerPoint human-review packs
Use existing `test-results/s7-parity/human-ab/` and empty `ZECT_NATIVE_PRESENTATION_HUMAN_AB_SCORECARD.md`.

For all 10 cases preserve generated `Deck_A.pptx` and `Deck_B.pptx` exactly. Do not regenerate/modify them. Verify each exists, non-zero, valid PPTX/ZIP and opens with installed PowerPoint-compatible application where available. Chrome download is not required.

Create `test-results/s7-parity/human-ab/HUMAN_REVIEW_INDEX.md` listing case, prompt/template goal, local Deck A path, Deck B path and scorecard section.

Optionally create safe Windows `OPEN_FOR_REVIEW.cmd` helper(s) to open A/B in Microsoft PowerPoint/default associated app. No provider identity, mapping exposure, unsafe filename command construction or file mutation.

Optionally generate PDF/PNG previews only with an already-available reliable local converter and without modifying source PPTX. Lack of previews does not block review; do not install a large office suite just for this.

## 7 Preserve blinding
Do NOT open/read/print/summarize/expose `PRIVATE_MAPPING.json` before human scoring. Do not reveal or infer which provider generated A/B from metadata, file size or style.

Cursor/LLM must NOT fill human scores.

## 8 Human handoff
STOP and report:
- branch + commit SHAs;
- PR URL/status or auth blocker;
- exact committed production/test/docs files;
- excluded files and reason;
- CI/Ultra Review status;
- `HUMAN_REVIEW_INDEX.md` path;
- scorecard path;
- paths to 20 PPTX files;
- instruction to open A/B in PowerPoint, score blindly, and return completed scorecard.

Only a later task, after human scoring, may read private mapping, calculate provider results, update S7 verdict and decide S8C readiness.

## Stop
Return:
`READY_FOR_HUMAN_REVIEW_AND_PR | READY_FOR_HUMAN_REVIEW_PR_BLOCKED_EXTERNAL | BLOCKED`.

Do not start S8C/S8D/KV cache/OCR-XLSX/broader Web/Graphify/new agents.
