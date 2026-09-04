# ZECT Developer V4 — Golden Acceptance Run

Run date: 2026-09-02
ZECT tree: worktree `ZECT-golden-acceptance-v2`, HEAD `983f810` (`origin/develop`, i.e. all of
Developer V4 phases D/E merged: PRs #215–#221, #223, #224).
Fixture: `C:\Users\karuppk\Downloads\zect-golden-fixture-account-lockout` — controlled internal
fixture (FastAPI + static frontend + pytest, one intentional single-line bug). **Not ZOAS**, not a
production repo, per the V5 master's constraint.

Environment: backend `py -3.12 -m uvicorn app.main:app --host 127.0.0.1 --port 8000` (no
`--reload`, see Findings F1); frontend `npm run dev` (Vite) on `localhost:5173`; driven through the
**real headed UI** in a browser. Model: `gpt-4o-mini` via a real `OPENAI_API_KEY`.
`ZECT_MODEL_FALLBACK_POLICY=automatic` set in this local `.env` only — the product default
(`never`) intentionally blocks cloud LLM calls when no local model is configured; overridden for
this local run, not changed in the product.

Mission produced by this run: **`1cbaf80d-d122-469b-8e44-067e03661eda`**, WorkItem `1`,
final phase `ready_to_merge`, commit `d35d44914a22b2852f1ae87086e7ec45d7cebc46`.

## Required journey — result per step

| Step | Result | Evidence |
|---|---|---|
| Open controlled fixture | PASS | Imported via UI "Import Already-Cloned Local Repo" → activated as workspace root; file tree, git branch (`main`), and PTY `cwd` all bound to the fixture path |
| Graphify → Lattice READY @ current SHA | PASS | Clicked Index in the UI; `/lattice` page shows `READY`, real extracted graph (5 files, 8 symbols, 28 edges, 3 endpoints: `GET /`, `POST /login`, `POST /reset`), sidebar shows `head e27ea0e · idx e27ea0e` (index SHA == HEAD SHA, not stale) |
| ASK → attach file → @mention → grounded response | PASS (attach: partial, see F5) | Typed `@file:app/main.py` in the ASK composer; "Context used (413/8000 tokens): mention:file:app/main.py"; answer correctly identified the exact root cause; real citations to `README.md:10`, `app/main.py:3`, `tests/test_lockout.py:21` |
| Navigate away/back → exact history | PASS | Navigated `/workspace` → `/settings` → `/workspace`; question, resolved context and answer all still present, byte-identical; terminal `cwd` also preserved |
| PLAN → real `.zect/plans` file | PASS (with F2, F3) | "Revise" produced a real ~4KB research-backed plan; "Save Plan" wrote a genuine file on disk: `.zect/plans/1-coding.md` with `zect-plan` metadata header |
| Edit/save plan | PASS | Edited plan text in the UI editor, re-saved; on-disk file updated (sha256 `6ff57fa8…`) |
| Approve exact hash | PASS | `plan_approved` event: "PLAN approved @8f43249ce6e7"; mission `plan_hash` == `plan_approved_hash` == `8f43249ce6e78af5b255e073cabae2e0a21c9f7eaf630dd1d82b989093a1fcd4`; `plan_approved: true` |
| AGENT → real multi-file edits visible in Explorer/Editor/Diff | PASS (with F4) | Mission worktree `…-1cbaf80d` appeared in the tree ("worktrees 2 · main"); opened `app/main.py` in the real editor; on-disk fix present |
| Intentional test fail → DEBUG repair → tests pass | PASS | `diagnose_attempt` (Debugger 1/2) → `diagnose_result` "repair attempt 1 -> pass (1 file(s) touched)" → `tests: pass`. Fix is the exact correct root cause: `attempts += 1; _failed_attempts[req.username] = attempts` |
| App Runner → health → browser verification | PASS | `browser_verify_attempt` (Tester 1/2) → `browser_verify_result` "attempt 1 -> verified"; `browser_verification: {ran: true, verified: true, attempts: 1}` recorded **on the Mission** |
| REVIEW → EvidenceVerifier | PASS | `evidence_verify_result` "verified (0 finding(s))"; `evidence_verification: {ok: true, findings: []}` |
| Ultra Review | PASS | Real `gpt-4o-mini` review (`offline: false`), score 70, `critical_findings: 0`, two genuine medium findings surfaced (not suppressed), `passed: true` |
| Delivery handoff → SAME Mission | PASS (via API, see F4) | `approve-git` on the **same** mission id returned `phase: ready_to_merge` with `committed_shas: ["d35d449…"]`. No new Mission and no second engine: `/api/agent/runs` shows exactly one `coding_engine_mission` entry for this work |
| Git safe proof | PASS | Real commit in the isolated worktree, authored `Mentrix Coding Agent <mentrix-coding-agent@zect.local>`, `app/main.py | 3 ++-`. Push deliberately not attempted (local fixture has no remote) |
| Backend restart → SAME Mission restored | PASS | Backend force-killed (`Stop-Process -Force`, not graceful), fresh process started; same mission re-queried: `phase: ready_to_merge`, both hashes intact, `committed_shas` intact — read from the durable on-disk store |
| Electron restart → SAME Mission restored | NOT EXERCISED | This pass was browser-only; Electron was not started. Recorded honestly rather than claimed |

## Hard-fail conditions — none triggered

| Hard fail | Status |
|---|---|
| Ask history disappears | Not triggered — history survived navigation exactly |
| PLAN is not a real editor file | Not triggered — real file on disk, editable and re-saved |
| Human plan approval bypassed | Not triggered — hash-bound approval, `plan_hash == plan_approved_hash` |
| Agent output exists only in chat | Not triggered — real worktree + real file edit + real commit on disk (but see F4 for a UI reachability gap) |
| Terminal is not genuine PTY | Not triggered — real PTY bound to the fixture `cwd`, accepted typed input and echoed a real Windows shell banner |
| Lattice is stale | Not triggered — `idx` SHA == `head` SHA (but see F6 for a status-reporting inconsistency) |
| Browser verification disconnected from Mission | Not triggered — `browser_verification` recorded on the Mission with a matching timeline event |
| Delivery creates a new plan/Mission or runs another coding engine | Not triggered — same mission id throughout; one `coding_engine_mission` entry |
| File-writing path auto-approves | Not triggered — `Approve & Build` was an explicit human action; git commit required a separate explicit approval call |

## Findings (recorded, not fixed in this pass)

**F1 — `zect.ps1 up` default `--reload` backend mode (pre-existing).** Worked around by running
uvicorn without `--reload`, matching the previously recorded behaviour. Not re-investigated here.

**F2 — PLAN drafts are stored under the ZECT harness, not the target workspace.** `plan_store._root()`
resolves to `<zect-repo>/.zect/plans` when `ZECT_PLAN_ROOT` is unset, so plans for **every**
workspace land in one shared directory, namespaced only by `<work_item_or_run>-<title>` slug
(here `1-coding.md`). Also the file extension is `.md`, not the `*.plan.md` the V4 wording implies.
Functionally fine for this run; worth an explicit product decision.

**F3 — PLAN draft is not reloaded into the editor after the pane remounts.** Switching from PLAN to
another AGENT sub-tab and back leaves the markdown editor **empty**, even though the saved file is
intact on disk, and no "load saved plan" affordance was found in the PLAN pane. Contrast with ASK,
whose history reloads correctly. A user would believe their plan was lost.

**F4 — No UI path re-attaches an existing Mission to the AGENT (Ship/PR) pane.** After
`Approve & Build` succeeded and the mission ran to `awaiting_git_approval`, the AGENT tab still
showed `phase · idle` / "Start a mission to generate PLAN", with empty FILES/TESTS/EVIDENCE and an
unusable "Approve git" button. Neither `?run=<mission-uuid>` nor `?work_item_id=1` loads it
(`deepRunId` is only honoured for legacy **numeric** run ids: `/^\d+$/` → `mentrixGetRun`). The
mission was fully real server-side, and its files were browsable via Explorer, but the final
git-approval step had to be driven through the API rather than the button. **This is the most
user-visible gap found in this run** and is a strong candidate for the first V4.1 fix.

**F5 — Native file-attach and screenshot-paste were not mechanically driven.** The composer exposes
"Attach files" and "or paste a screenshot", and the code paths are unit-tested
(`test_ask_vision_attachments.py`, `MentrixCodingAgentPanel.attachments.test.tsx`), but an OS file
picker and a real clipboard image paste are outside what this browser-automation surface can drive.
`@mention`-based file context **was** exercised end-to-end instead. Recorded as an acceptance-run
coverage gap, not a proven product gap.

**F6 — Lattice status is reported inconsistently across surfaces.** With Lattice genuinely `READY`
(`idx == head`), the mission's own recorded `context_used` still shows
`{lattice_indexed: false, lattice_hits: 0}`, and the small "Context used · Lattice NOT INDEXED"
caption appears in the ASK/PLAN panes. The top-bar badge also lagged until a tab switch. Since
`context_used` feeds what the model is told, this is more than cosmetic and should be reconciled in
V4.1's Context Manager work.

**F7 — Compiled bytecode committed.** The mission's commit included `__pycache__/*.pyc` files
alongside the real `app/main.py` fix (it also added a `.gitignore` line in the same commit, too late
to exclude them). Minor hygiene issue in the commit-staging step.

**F8 — Runs list mixes Ask/Plan activity with real Missions.** `/api/agent/runs` returns both the
real `coding_engine_mission` entry and a separate `engine: "mentrix"`, `id: 1` entry created by the
earlier Plan "Revise" call (with no events). Not a second coding engine — no files were touched by
it — but the unified list can read as two executions of one goal.

## Conclusion

The canonical Developer V4 journey **passes** on current `develop` against a controlled fixture,
driven through the real headed UI, with a real model, real worktree isolation, real Debugger repair
of a real failing test, real browser verification tied to the Mission, real EvidenceVerifier and
Ultra Review, a real hash-bound human approval, a real commit, and proven durability across a
forced backend crash. No hard-fail condition was triggered.

Eight findings are recorded above. F4 (Mission unreachable from the AGENT pane) and F6 (Lattice
status inconsistency reaching model context) are the two that materially affect the product
experience and should be scheduled before/with V4.1. Electron restart (and native attach/paste)
were not exercised in this pass and are stated as such rather than claimed.
