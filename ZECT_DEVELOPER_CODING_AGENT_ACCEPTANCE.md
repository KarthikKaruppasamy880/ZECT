# Developer + Coding Agent — acceptance

READY means no known release-blocking Critical/High.

## Architecture

`Developer=engineering cockpit; Coding Agent=executor; Delivery=ship pipeline; Graphify/Lattice=intelligence; WorkItem=durable work; Processes=external intake`.

## Cockpit

- ASK / PLAN / AGENT / HISTORY in Developer Coding Agent panel.
- ASK: `/api/llm/ask` only — zero file edits (no coding session).
- PLAN: Save / Revise / Approve & Build (`codingAgentApprovePlan`). `.zect/plans` gitignored.
- AGENT: existing mission (worktree, tests, review, git). Cancel / resume / retry. No auto-merge.
- Prepare PR starts **one** Mentrix Delivery run for that WorkItem + mission. Duplicate → 409.
- Agent Workspace `/ask` `/plan` remain for e2e; Open in Developer banners added.

## Verdict

`ZECT_DEVELOPER_CODING_EXPERIENCE_PARTIAL` until headed Electron + ZOAS clone Run App is operator-proven. Agent Workspace hidden from primary nav (route stays live for e2e via direct URL). Known remaining: Learning Studio not implemented (plan only).
