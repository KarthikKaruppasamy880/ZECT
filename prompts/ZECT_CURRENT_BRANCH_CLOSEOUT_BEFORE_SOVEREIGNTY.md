# ZECT — CURRENT BRANCH CLOSEOUT BEFORE SOVEREIGNTY

## Goal
Do NOT start `ZECT_OSS_SOVEREIGNTY_NATIVE_ENGINES_PLAN.md` yet. Current Core UX/release fixes are still local on `feat/release-closure-core-ux`. First publish, review, merge and re-prove them. Preserve honest external blockers.

## 1. Git/auth
Verify branch/commits/working tree/origin develop. Never print credentials. If GitHub auth is unavailable, require approved human `gh auth login`/credential setup; never create/show PATs or dump credential-helper output.

When auth exists:
`fetch → verify divergence → push feat/release-closure-core-ux → PR to develop`.
No force merge/push unless policy explicitly permits.

## 2. Review PR
Wait backend/frontend/e2e CI. Run Mentrix Ultra Review; use substantive CodeRabbit if available. Classify findings `CRITICAL | MAJOR | MINOR | FALSE_POSITIVE | ALREADY_FIXED | OUT_OF_SCOPE`. Fix all valid branch-introduced Critical/Major findings on SAME PR and rerun tests/review.

## 3. Re-prove claimed Core UX
Headed ZECT UI:
- Present editor: thumbnails, slide selection, notes persistence, supported edit/refine.
- Present export: UI export creates valid non-empty parseable PPTX.
- Projects: search + fixture hiding without unsafe deletion.
- WorkItems/Processes: sample Process→WorkItem→Project + ingest.
- Developer: Explorer/Agent/Tools toggles and no new blocking runtime errors.
- Voice selectors: clone, stock/default, No Narration.

Standalone Presenton UI is not acceptance.

## 4. Re-prove locally possible open gates
### Clone >=2 slides
`deck → slide1 notes/audio → slide2 notes/audio`; real Chatterbox, correct binding, exactly one audio_owner, no overlap/double voice.

### Standard voice
Live stock/default path where configured. If provider/model unavailable, report exact blocker.

### Disconnect live
Where feasible: `Connect → Disconnect → wake ignored → explicit Connect`; prefer live over unit-only proof.

### Multi-repo READY_AFTER_FIX
Reuse disposable fixture:
`mandatory sibling FAIL → NOT READY → fix same fixture PR → CI/tests/review → refresh evidence → READY_TO_SHIP`.
If GitHub permission blocks, mark `BLOCKED_EXTERNAL`.

### Fixture cleanup
DELETE=403 must not be solved by weakening authorization. Use correct owner/admin cleanup or document external blocker.

## 5. Honest external blockers
Do not fabricate:
- clean-machine Windows NSIS proof if no clean VM/machine;
- packaged Present/Voicebox proof without packaged environment;
- GitHub operations without credentials/permissions.
Keep `BLOCKED_EXTERNAL/PARTIAL`.

## 6. Merge
When production PR CI/review/security and locally provable gates are green:
`merge → develop → sync → local==origin/develop → frozen smoke → headed sanity Present/Developer/Projects/WorkItems/Processes`.
Record merge SHA.

## 7. Update truth
Update Core UX, final baseline, canonical audit and release-blocker/R1.6-R3.6 acceptance docs. Separate `MERGED_AND_PROVEN | PARTIAL | BLOCKED_EXTERNAL`.

## 8. Sovereignty start gate
Only after Core UX is merged into synchronized `develop` should `ZECT_OSS_SOVEREIGNTY_NATIVE_ENGINES_PLAN.md` begin.

Before S1 confirm:
`branch=develop; local==origin/develop; Core UX PR merged; post-merge smoke green; no unresolved branch-introduced Critical/Major`.

External clean-machine packaging blockers may remain documented; they do not require native-engine implementation before the S1 dependency audit.

## Stop
STOP after merge/sync/post-merge acceptance. Do not start S1 automatically.

Return:
`READY_FOR_SOVEREIGNTY_AUDIT | PARTIAL | BLOCKED_EXTERNAL`
with merge SHA and remaining blockers.
