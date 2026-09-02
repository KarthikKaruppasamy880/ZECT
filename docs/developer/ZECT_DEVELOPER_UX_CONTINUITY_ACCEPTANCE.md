# ZECT Developer UX-Continuity Acceptance — V1

Status: `READY_FOR_HUMAN_ZECT_DEVELOPER_UX_CONTINUITY_REVIEW_V1`

Scope: the 9-item acceptance tranche closing the remaining Developer
UX/state gaps ahead of `ZECT_DEVELOPER_V4_1_LIVE_AGENT_ACTIVITY_SKILLS_CONTEXT_ADDENDUM.md`.
No auto-merge. All four PRs are independently focused, CI-green, and
awaiting human review/merge.

| PR | Branch | Closes |
|---|---|---|
| [#229](https://github.com/KarthikKaruppasamy880/ZECT/pull/229) | `feat/v41-b-ask-context-persistence` | Item 1 |
| [#230](https://github.com/KarthikKaruppasamy880/ZECT/pull/230) | `feat/v41-c-explorer-diff-refresh` | Items 6, 7 |
| [#231](https://github.com/KarthikKaruppasamy880/ZECT/pull/231) | `feat/v41-a-durable-attachments` | Items 2, 3, 5 |
| [#232](https://github.com/KarthikKaruppasamy880/ZECT/pull/232) | `feat/v41-d-electron-ux-acceptance` | Item 8 (depends on #229-#231 merging first) |

Items 4 and 9 required no new PR — see their sections below.

---

## Item-by-item status

### 1. Persistent ASK history — CLOSED (#229)
Question/answer/model/offline/image_count already persisted and replayed
correctly. The gap was the resolved Context Used summary: it existed only
for the live call, so a reload showed a blank Context Used strip until a
new question was asked. `ask_turn` events now also carry a compact
`context_used` summary (same shape Mission's Context Used already uses),
and `AskPane` restores it from the last turn on mount. Resolved `@mention`
evidence needed no separate field — it's already folded into the
persisted, untruncated `question` text.

### 2. Native file attachments — CLOSED (#231)
Previously: each pane's attachment state was isolated and self-resetting;
an ASK attachment survived only as flattened text inside one `ask_turn`.
`DocumentArtifact` now carries `work_item_id` + `kind`; a new
parse-free `ingest_image()` persists screenshots too (previously only an
`image_count` ever reached storage). `GET /api/work-items/{id}/attachments`
is the one list ASK/PLAN/AGENT all read via the shared
`WorkItemAttachmentsStrip`. Linking happens at upload time if the WorkItem
already exists, or retroactively via `linkPendingTo()` the instant ASK's
first turn resolves one.

### 3. Clipboard screenshot paste — CLOSED (#231)
Paste-to-attach now works in ASK, PLAN, and AGENT (previously ASK only).
Pasted images persist durably (previously memory-only, lost on refresh).
A best-effort, non-blocking hint warns when the selected model doesn't
look vision-capable — no model-capability registry exists in ZECT today,
so this is a soft heuristic, not an enforced gate; a real rejection still
surfaces the provider's own error.

### 4. ASK → PLAN continuity — CLOSED (shipped in #228, already merged)
Already implemented and verified in the headed Electron run (#232):
clicking Create Plan seeds PLAN.md with the ASK conversation, resolved
evidence, attachments, and a findings summary, as a one-shot handoff that
does not silently re-seed on an unrelated later visit to PLAN.

### 5. PLAN attachment/context parity — CLOSED (#231)
PLAN and AGENT previously disabled images (`allowImages={false}`) and had
no paste handler — a deliberately reduced configuration of the shared
composer, not a second implementation. Both now match ASK exactly (same
`useComposerAttachments`, same `ComposerAttachmentBar`, same
`ContextUsedStrip`/`contextUsedSummaryText`).

### 6. PLAN.md UX — CLOSED (#226 merged; #230 fixes a related bug)
Real editable Markdown in Monaco, saved under
`<workspace>/.zect/plans/<slug>.plan.md`, editable/re-savable, hash-binding
exact and non-stale for Approve & Build (already merged). #230 fixes a
related bug found during this tranche: `.zect` was unconditionally filtered
out of the Explorer file tree, so a saved plan could never render there
(it was only reachable via the direct path-open button, which still works
correctly).

### 7. Explorer / Changes / Diff live refresh — CLOSED (#230)
Explorer tree and git-status refresh on every Mission file change were
already real. The gap: the per-file Diff panel didn't invalidate a
currently-open buffer when a Mission edited that file underneath, so it
kept showing stale content until a manual re-open. Fixed — a matching,
non-dirty open file now reloads automatically; a dirty (user-edited) one
is left untouched.

### 8. Electron acceptance — CLOSED (#232, pending #229-#231 merge)
Extended the only CI-wired Electron spec with a real end-to-end run:
native file attach, real clipboard screenshot paste (an actual
`ClipboardEvent`+`File` dispatched in the renderer, not a jsdom mock),
ASK→PLAN seeding, cross-pane attachment visibility, PLAN.md edit+save,
Approve & Build, Electron restart, and Mission re-attachment to live
(not frozen) server state. Passed locally against a real Electron build
twice (one earlier run hit transient local dev-machine resource
contention from two heavyweight Electron sessions back-to-back — not
expected on CI's dedicated runner).

### 9. Mission ID continuity ASK → PLAN → AGENT — CLOSED (redefined + verified, no new code)
Literally impossible as originally stated without new architecture: no
Mission exists until Approve & Build, and PLAN is deliberately
zero-edits-until-approval. Redefined per explicit sign-off:
- `work_item_id` is the real, already-durable continuity thread through
  ASK and PLAN (confirmed: both key off the same id, `PlanPane`'s
  `codingAgentGetPlan`/`codingAgentSavePlan` calls use it, `AskPane`'s
  history restore uses it).
- Once a Mission exists (Approve & Build), the *same* Mission id stays
  attached through AGENT across reload/tab-switch/Electron restart (the
  F4 fix, already merged in #227) — proven concretely by #232's Electron
  test, which asserts the Mission reappears in a real, non-idle phase
  after a full app restart rather than an empty start form.

---

## Manual test sequence

A live environment is running right now for hands-on verification —
**all four pending PRs (#229, #230, #231, #232) merged together locally**
(not yet on `develop`; this is a local integration build for your review):

- **Backend:** `http://127.0.0.1:8000` (health: `http://127.0.0.1:8000/healthz`)
- **Frontend dev server:** `http://127.0.0.1:5173`
- **A live Electron window is already open**, pointed at the above, using
  profile `C:\Users\karuppk\zect-manual-verify-profile` (persists across
  restarts — closing and reopening this Electron window will exercise the
  same restart-recovery path #232 tests).
- Login: username `test@zect.local`, password `test-pass-1234`.

Suggested walk-through in the open Electron window:

1. Sidebar → **Developer Workspace**. Import/register a local git folder if prompted (any folder works — a scratch repo is fine).
2. Open the **Mentrix Coding Agent** panel → **ASK** tab.
   - Type a question, click **Attach files**, pick any `.md`/`.txt` file → a chip appears.
   - Paste a screenshot (copy any image to your clipboard, click into the ASK textarea, `Ctrl+V`) → an image chip appears.
   - Click **Ask** → an answer renders.
3. Click **Create Plan**. PLAN tab should already contain your question, answer, and the attachment content — not a blank editor.
4. Still in PLAN: confirm the same attachment shows in the "Attached to this Mission" strip (no re-upload). Edit the plan text, click **Save Plan**, confirm the plan-path button renders and opens the file in the editor when clicked.
5. Click **Approve & Build**. Switch to the **AGENT** tab and confirm a real phase (not "idle") appears, with the same attachment strip visible there too.
6. Close the Electron window entirely, then relaunch it (same profile). Re-open the same workspace and the AGENT tab — the Mission should reappear in a real phase automatically, with no "start a mission" empty form.
7. In the Explorer tree (left panel), confirm `.zect/plans/<your-plan>.plan.md` is now visible (previously always hidden, regardless of refresh).

To shut everything down when done: close the Electron window, then stop the two background dev-server processes (backend `uvicorn`, frontend `vite`) started for this review.

---

## Stop

Do not start the CMS real-project benchmark or T1 V4.1 (Live Agent
Activity/Skills/Context) until this gate and the subsequent
`READY_FOR_HUMAN_ZECT_AGENT_ACTIVITY_CONTEXT_SKILLS_REVIEW_V1` gate are
both explicitly approved.
