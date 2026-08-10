"""Internal Mentrix engineering roles — not separate products.

Mentrix = user-facing intelligence
ForgeLoop = SDLC orchestrator
Automation Loops = triggers/budgets/checkpoints
Planner / Coding Agent / Test Agent / Review Agent = internal workers
AcceptanceVerifier + EvidenceVerifier = completion authority
"""

from __future__ import annotations

ROLE_PLANNER = "planner"
ROLE_CODER = "coding_agent"
ROLE_TESTER = "test_agent"
ROLE_REVIEWER = "review_agent"
ROLE_ACCEPTANCE = "acceptance_verifier"

FORBIDDEN_READY_TO_SHIP_ROLES = frozenset({ROLE_PLANNER, ROLE_CODER, ROLE_TESTER, ROLE_REVIEWER})

# Planner must never modify production source under these path prefixes
PLANNER_FORBIDDEN_WRITE_PREFIXES = (
    "backend/app/",
    "frontend/src/",
    "electron/",
)


def role_may_declare_ready_to_ship(role: str) -> bool:
    return (role or "").strip().lower() not in FORBIDDEN_READY_TO_SHIP_ROLES and role == ROLE_ACCEPTANCE


def planner_may_write_path(path: str) -> bool:
    """Planner may only write ArtifactStore planning artifacts, never production code."""
    p = (path or "").replace("\\", "/").lstrip("./")
    if p.endswith((".md", ".json")) and (".zect/work/" in p or p.startswith("PLAN") or "REQUIREMENTS" in p or "ACCEPTANCE" in p or "RISKS" in p or "EXECUTION_" in p):
        return True
    for prefix in PLANNER_FORBIDDEN_WRITE_PREFIXES:
        if p.startswith(prefix) or f"/{prefix}" in f"/{p}":
            return False
    # Default deny for source-like paths
    if p.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java")):
        return False
    return True
