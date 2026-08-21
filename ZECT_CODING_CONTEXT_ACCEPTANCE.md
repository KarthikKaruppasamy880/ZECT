# Developer ASK / PLAN / AGENT context (PR1)

ASK and PLAN send `repo_id` and `project_id` (not a folder path as file context). Backend ContextPack is Knowledge + Lattice `hybrid_retrieve` + Blueprint, token-capped.

## Operator strip

`Context used · Lattice N hits | Lattice NOT INDEXED · Knowledge · Blueprint`

ZAF-devin NOT INDEXED still injects README/tree via `repo_id`. Mentrix Local offline: ASK/PLAN fail honestly (503), not a silent heuristic success.

## AGENT

Approve & Build with `propose_if_empty` proposes bounded patches from PLAN + ContextPack when `patches_by_repo` is empty. Zero auto-merge. LLM offline → `llm_offline` (no empty-worktree success).
