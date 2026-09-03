"""CP-09A -- mode/role-aware Tool Governance for `run_command`.

AgentWritePolicy (CP-07) is a hard, per-path/per-action gate on write_file/
apply_patch -- but shell execution was never covered by it, and a shell
command can trivially write/delete/rename/commit/push without ever calling
write_file/apply_patch at all (flagged as a known residual risk in CP-07,
promised for closure "before CP-10"). Before this module, `run_command`'s
only check was `_DESTRUCTIVE_CMD` in mentrix_agent_tools.py -- a small,
hand-picked pattern list (rm -rf, git push, git reset --hard, ...) that
required approval, but every OTHER command -- including `sed -i`,
`git commit`, `git checkout --`, an arbitrary Python script that rewrites
files -- ran completely unchecked, regardless of role, Mission, or plan
state.

This module classifies every command into one of nine categories and
draws the enforcement line at exactly the categories that could bypass
file-write/git policy: READ_ONLY/BUILD/TEST/APP_RUNNER may run without a
human in the loop (that's the whole point of an autonomous build/test
loop); FILE_MUTATING/GIT_MUTATING/DEPLOYMENT/DESTRUCTIVE/UNKNOWN always
require explicit human approval -- fail closed, never silently auto-run,
matching AgentWritePolicy's own "block, never downgrade" posture. This is
heuristic pattern-matching over a shell string, not a real shell parser:
a compound command that hides a mutation behind a benign-looking prefix
(e.g. "pytest && sed -i ...") can still slip past the leading-pattern
checks below -- documented, not silently pretended away. The full command
is *also* still subject to `_DESTRUCTIVE_CMD`'s always-block check.
"""

from __future__ import annotations

import re

CATEGORY_READ_ONLY = "READ_ONLY"
CATEGORY_BUILD = "BUILD"
CATEGORY_TEST = "TEST"
CATEGORY_APP_RUNNER = "APP_RUNNER"
CATEGORY_FILE_MUTATING = "FILE_MUTATING"
CATEGORY_GIT_MUTATING = "GIT_MUTATING"
CATEGORY_DEPLOYMENT = "DEPLOYMENT"
CATEGORY_DESTRUCTIVE = "DESTRUCTIVE"
CATEGORY_UNKNOWN = "UNKNOWN"

ALL_CATEGORIES = frozenset(
    {
        CATEGORY_READ_ONLY, CATEGORY_BUILD, CATEGORY_TEST, CATEGORY_APP_RUNNER,
        CATEGORY_FILE_MUTATING, CATEGORY_GIT_MUTATING, CATEGORY_DEPLOYMENT,
        CATEGORY_DESTRUCTIVE, CATEGORY_UNKNOWN,
    }
)

# The only categories a governed agent role may ever auto-run without a
# human approving first. Everything else -- including UNKNOWN, since an
# unrecognized command is exactly the case CP-09A's mandate says must
# "fail closed or require explicit approval" -- needs_approval.
AUTO_ALLOWED_CATEGORIES = frozenset(
    {CATEGORY_READ_ONLY, CATEGORY_BUILD, CATEGORY_TEST, CATEGORY_APP_RUNNER}
)

# Checked in this order -- most severe first, then the benign build/test
# allowlist BEFORE the generic file-mutation pattern, so "pytest --junit-
# xml=out.xml" or "npm test > log.txt" classify as TEST, not
# FILE_MUTATING, on the strength of the known-good tool invocation.
_DESTRUCTIVE_RE = re.compile(
    r"\b(rm\s+-rf|del\s+/[sf]|format\s+|rmdir\s+/s|git\s+push(\s|$)|git\s+reset\s+--hard|"
    r"Remove-Item\s+.*-Recurse|drop\s+table|truncate\s+table)\b",
    re.I,
)
_DEPLOYMENT_RE = re.compile(
    r"\b(docker\s+push|kubectl\s+(apply|delete)|terraform\s+apply|helm\s+(install|upgrade)|"
    r"npm\s+publish|twine\s+upload|serverless\s+deploy|eb\s+deploy|az\s+deploy)\b",
    re.I,
)
_GIT_MUTATING_RE = re.compile(
    r"\bgit\s+(commit|push|reset|checkout|clean|merge|rebase|cherry-pick|revert|"
    r"branch\s+-[dD]|tag\s+-[dD]|stash\s+(pop|drop|clear))\b",
    re.I,
)
_BUILD_RE = re.compile(
    r"\b(npm\s+(run\s+build|ci|install)|yarn\s+(build|install)|pnpm\s+(build|install)|"
    r"pip\s+install|poetry\s+install|mvn\s+(compile|package|install)|gradlew?\s+build|"
    r"make(\s|$)|go\s+build|cargo\s+build|tsc\b|webpack\b|docker\s+build)\b",
    re.I,
)
_TEST_RE = re.compile(
    r"\b(pytest|npm\s+(run\s+)?test|yarn\s+test|pnpm\s+test|jest|vitest|mvn\s+test|"
    r"gradlew?\s+test|go\s+test|cargo\s+test|eslint|mypy|ruff|flake8|tox)\b",
    re.I,
)
_APP_RUNNER_RE = re.compile(
    r"\b(npm\s+(run\s+)?(dev|start|serve)|yarn\s+(dev|start)|uvicorn\b|flask\s+run|"
    r"python\s+-m\s+http\.server)\b",
    re.I,
)
_FILE_MUTATING_RE = re.compile(
    r"(>>?\s*[^&|]|\bsed\s+-i\b|\bSet-Content\b|\bcp\s|\bmv\s|\bcopy\s|\bmove\s|"
    r"\brm\s|\bdel\s|\btouch\s|\bmkdir\s|\bNew-Item\b|\bRemove-Item\b)",
    re.I,
)
_READ_ONLY_RE = re.compile(
    r"^\s*(ls|dir|cat|type|grep|find|which|where|pwd|cd|head|tail|wc|"
    r"git\s+(status|diff|log|branch|show)|npm\s+(list|ls|--version)|"
    r"python\s+--version|node\s+--version|echo\s+[^>|]*$)\b",
    re.I,
)


def classify_command(command: str) -> str:
    """Deterministic, regex-based classification -- no LLM call, matching
    the "keep deterministic work out of the LLM" rule everything else in
    this pipeline already follows."""
    c = (command or "").strip()
    if not c:
        return CATEGORY_UNKNOWN
    if _DESTRUCTIVE_RE.search(c):
        return CATEGORY_DESTRUCTIVE
    if _DEPLOYMENT_RE.search(c):
        return CATEGORY_DEPLOYMENT
    if _GIT_MUTATING_RE.search(c):
        return CATEGORY_GIT_MUTATING
    if _BUILD_RE.search(c):
        return CATEGORY_BUILD
    if _TEST_RE.search(c):
        return CATEGORY_TEST
    if _APP_RUNNER_RE.search(c):
        return CATEGORY_APP_RUNNER
    if _FILE_MUTATING_RE.search(c):
        return CATEGORY_FILE_MUTATING
    if _READ_ONLY_RE.search(c):
        return CATEGORY_READ_ONLY
    return CATEGORY_UNKNOWN


def requires_approval(command: str) -> tuple[bool, str]:
    """Returns (needs_approval, category). Every category outside
    AUTO_ALLOWED_CATEGORIES needs approval -- including UNKNOWN, which is
    the deliberate fail-closed default for anything this heuristic
    doesn't recognize, not just the hand-picked DESTRUCTIVE list."""
    category = classify_command(command)
    return category not in AUTO_ALLOWED_CATEGORIES, category
