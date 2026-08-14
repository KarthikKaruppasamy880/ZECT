# ZECT — RELEASE CANDIDATE FINAL CLOSURE

## Mission
Current verdict: `RELEASE_CANDIDATE_PARTIAL`. Close only remaining release gates before R5+.

Revalidate first: PPTX generation/Zinnia/gallery/clone voice passed; Editor and Export partial; clean packaged runtime unproven; real multi-repo PR negative gate passed; production fixes remain local because GitHub auth failed.

## 1. Publish existing fixes
Verify Git truth and branch `feat/r16-r26-r36-final-proof`. Never echo credentials. If approved GitHub auth is available: push branch → PR to develop → CI → Ultra Review → substantive external review if available → fix Critical/Major on same PR → merge → sync → smoke. If auth unavailable, mark this gate `BLOCKED_EXTERNAL`; never fabricate remote proof.

## 2. Present Editor
From real ZECT `/present`, prove generated deck opens in ZECT editor: thumbnails, slide selection, visible canvas/content, supported text editing, notes, save/persist, >=1 AI rewrite/regenerate action, leave/return without losing saved state. Classify charts/images/elements/tables separately. Headed Playwright mandatory; standalone Presenton UI is not acceptance.

## 3. Present Export
From ZECT UI:
`generate → edit/save → Export PPTX → real file → nonzero → parse/open validation → expected slides/content/template`.
Verify notes survive when intended. Backend temporary PPTX alone is not UI export PASS.

## 4. Clone + standard voice
Final Present UI must support authenticated user's clone, >=1 standard/ZECT voice where configured, and No Narration.

Clone proof: `deck → notes → clone → rehearse >=2 slides → real Chatterbox audio → exactly one audio_owner`.
Standard proof: select standard voice → narrate → exactly one audio_owner.

Verify cross-user clone denial, no clone+PCM/double voice, slide-notes-audio identity, explicit fallback, honest failure, and live Disconnect/wake behavior where practical.

## 5. Clean Windows NSIS
Use clean Windows VM/machine/equivalent with no source checkout/system-Python dependency/manual Vite/uvicorn/pre-existing dev services.

Prove:
`install → launch installed app → packaged backend starts → managed services readiness → login → Companion → Projects → Developer → Learning → Present → close → processes stop → relaunch/state persists`.

Collect installer version/hash, process/service health, logs/screenshots. If no clean environment exists, mark `BLOCKED_EXTERNAL: CLEAN_WINDOWS_ENVIRONMENT_REQUIRED`; do not fake it with more code.

## 6. Packaged Present/Voice
In installed app verify Present route, truthful provider lifecycle, Zinnia registry without user env-var manipulation, generation if supported topology, clone/standard narration if supported, editor/export. If Presenton/Voicebox are intentionally managed external dependencies, document the contract and truthful UX; do not call them bundled.

## 7. Finish multi-repo aggregate proof
Existing negative proof:
`Repo A PASS + Repo B mandatory FAIL → WorkItem NOT READY`.

Now fix Repo B on SAME disposable PR → push → CI/tests/review → current evidence for all mandatory PRs → AcceptanceVerifier + EvidenceVerifier → prove `READY_TO_SHIP`.

Where practical change a PR head after verification and prove stale evidence invalidates.

Do not auto-merge disposable PRs unless explicitly needed/safe.

## 8. Fixture cleanup
Previous disposable repo DELETE returned 403. Do not weaken authorization. Determine whether owner/admin/manual cleanup is required. Document leftovers. If current credentials cannot delete them, mark cleanup `BLOCKED_EXTERNAL`.

## 9. Final headed acceptance
After production fixes merge to synced `develop`, headed E2E: Companion, Projects, WorkItems, Processes, Developer, Learning, Present generation/editor/export, clone voice, standard voice, multi-repo. Do not substitute unit/API proof for user-facing gates.

## 10. Security/regression
Run frozen regression plus cross-user/project/repo, voice-clone isolation, template ownership, forged IDs/evidence, prompt injection, SSRF, unauthorized filesystem/network/tools, secrets and multi-repo stale evidence.

## 11. Acceptance
Update canonical/final/R4/blocker/R1.6-R3.6 acceptance docs. Final gate table:
`WINDOWS_CLEAN_INSTALL | PACKAGED_BACKEND | PRESENT_PPTX_GENERATION | ZINNIA_VERIFIED | TEMPLATE_GALLERY | PRESENT_EDITOR | PRESENT_EXPORT | CLONED_VOICE | STANDARD_VOICE | NO_OVERLAP | DISCONNECT_FSM_LIVE | PACKAGED_PRESENT | PACKAGED_VOICEBOX | MULTI_REPO_REAL_PRS | MULTI_REPO_BLOCKED_GATE | MULTI_REPO_READY_AFTER_FIX | FULL_HEADED_E2E | SECURITY | FROZEN_REGRESSION`.

Statuses: `PASS | PARTIAL | BLOCKED | BLOCKED_EXTERNAL | REGRESSION`.

## Merge discipline
Production: `tests → headed E2E → security → Ultra Review → CI → fix blockers → merge develop → sync → smoke`. Never expose credentials/force merge around auth failure.

## Stop
STOP before R5 KV cache, R6 advanced Documents, R7 broader Web, R8 Graphify, R9 agents.

Return exactly:
`RELEASE_CANDIDATE_PASS | RELEASE_CANDIDATE_PARTIAL | BLOCKED | BLOCKED_EXTERNAL`.
