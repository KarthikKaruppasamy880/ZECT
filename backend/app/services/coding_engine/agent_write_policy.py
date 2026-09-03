"""CP-07 -- the hard execution-security boundary between an approved PLAN
and any actual filesystem mutation the AGENT (Mentrix Coding Agent) makes.

CP-06 made "Approve & Build" a hard gate on the PLAN *document*, checked
once, before a Mission ever enters the editing phase. But the tool-calling
loop that actually writes bytes to disk (mentrix_agent_tools.execute_tool,
reached via lifecycle.py::_apply_patches for JSON-patch missions and
app.adapters.coding_engine_mentrix.py::_run_one_tool for the native
tool-loop) never checked a write's target path against the approved
FileImpact list at all -- only against the git-worktree jail (any path
inside the worktree was writable once a Mission passed CP-06's gate). A
plan can also go stale *after* approval (edited directly in Monaco) with
nothing re-checking it before the next write. This module closes both
gaps: every write_file/apply_patch call must be authorized here first.

Deliberately fail-CLOSED, unlike CP-06's approval gate: `_plan_validation_
gate` fails OPEN (returns None) when a Mission has no work_item_id, so
Missions that predate the WorkItem/PLAN pipeline entirely (patches
supplied directly, never grounded in ASK/PLAN -- see
test_coding_agent_production.py's "Missions A-G") keep working unmodified.
This module preserves that same *scope* boundary (a Mission with no
work_item_id was never covered by CP-06 and isn't newly gated here
either), but for any Mission that DOES carry a work_item_id, every
failure mode -- missing FILE_IMPACTS.json, a DB error, an unresolved
repository identity, an invalid/stale plan, an unplanned path -- must
BLOCK the write. CP-06's compatibility fail-open behavior must never
become an AGENT write bypass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The canonical registry of tool names that mutate a target repo's
# filesystem. delete_file/rename_file do not exist in mentrix_agent_tools'
# TOOL_SPECS today (the coding agent's LLM tool-calling loop has no way to
# delete or rename a file) -- listed here anyway so the gate is already
# correct the moment such a tool is ever added, instead of silently
# missing it.
WRITE_MUTATING_TOOLS = frozenset({"write_file", "apply_patch", "delete_file", "rename_file"})
_DELETE_TOOLS = frozenset({"delete_file"})


@dataclass
class WriteDecision:
    allowed: bool
    reason: str
    detail: str = ""
    matched_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "detail": self.detail,
            "matched_action": self.matched_action,
        }


@dataclass
class AgentWritePolicy:
    """A fresh-every-time snapshot of the one canonical AGENT write
    contract for a WorkItem -- never cached across a Mission's lifetime,
    because the entire point is catching drift (a plan edited, or the
    machine contract going missing/stale, after approval)."""

    work_item_id: int
    authorized: bool
    block_reason: str = ""
    block_detail: str = ""
    primary_repo_id: int | None = None
    plan_hash: str = ""
    file_impacts: list[Any] = field(default_factory=list)
    not_found_entities: set[str] = field(default_factory=set)


def build_agent_write_policy(db: Any, work_item_id: int) -> AgentWritePolicy:
    """The one canonical AGENT write contract -- reuses CP-06's
    plan_validator.validate_plan_for_approval() (the exact same VALID/
    INVALID/STALE check Approve & Build ran) rather than a second,
    independently re-derived notion of "is this plan OK". agent_context.py
    builds free-text *prompt* context for the model and must stay separate
    from this; this function is the machine-checkable write *contract*
    the runtime layer enforces, not something the model can talk its way
    around.
    """
    import json as _json

    from app.domains.work_items import service as wi_svc
    from app.services.work_items import plan_generator, plan_validator
    from app.services.work_items.artifact_store import ArtifactStore, plan_hash_bytes
    from app.services.work_items.context_package import ContextPackage
    from app.services.work_items.multi_repo_context import repo_binding

    try:
        wi = wi_svc.get_work_item(db, int(work_item_id))
    except Exception as exc:  # noqa: BLE001
        return AgentWritePolicy(
            work_item_id=work_item_id, authorized=False,
            block_reason="work_item_not_found", block_detail=str(exc)[:200],
        )

    try:
        store = ArtifactStore(wi.id)
        sidecar = store.read_json("FILE_IMPACTS.json", default=None) or None
        if not sidecar:
            return AgentWritePolicy(
                work_item_id=wi.id, authorized=False, block_reason="missing_machine_contract",
                block_detail="no FILE_IMPACTS.json recorded for this WorkItem -- run PLAN again before AGENT can write",
            )

        repo_local_path = str(repo_binding(db, wi.repository_id).get("local_path") or "") if wi.repository_id else ""
        architecture = (
            plan_generator.detect_repo_architecture(repo_local_path)
            if repo_local_path
            else plan_generator.RepoArchitecture(primary_language="unknown", build_system="unknown")
        )
        context_package = None
        raw = (wi.context_snapshot_json or "").strip()
        if raw and raw != "{}":
            data = _json.loads(raw)
            if data:
                context_package = ContextPackage.from_dict(data)

        # Resolve the plan text the SAME way CP-06's approval gate does
        # (the repo-local Monaco copy takes precedence over the internal
        # ArtifactStore mirror) so an edit made after approval, but before
        # this write, is caught here exactly as it would be at
        # re-approval time.
        from app.services.work_items.developer_service import MentrixDeveloperService

        svc = MentrixDeveloperService(db)
        plan_text = svc._resolve_current_plan_text(wi, store)
        current_hash = plan_hash_bytes(plan_text) if plan_text.strip() else ""

        result = plan_validator.validate_plan_for_approval(
            work_item_id=wi.id,
            primary_repo_id=wi.repository_id,
            base_commit_sha=wi.base_commit_sha or "",
            recorded_plan_hash=wi.plan_hash or "",
            plan_text=plan_text,
            current_plan_hash=current_hash,
            sidecar=sidecar,
            context_package=context_package,
            repo_root=repo_local_path or ".",
            architecture=architecture,
        )
        if not result.ok:
            detail = "; ".join(f"{f.rule}: {f.detail}" for f in result.findings) or result.status
            return AgentWritePolicy(
                work_item_id=wi.id, authorized=False, block_reason=f"plan_{result.status.lower()}",
                block_detail=detail, plan_hash=current_hash,
            )

        impacts = [
            plan_generator.FileImpact.from_dict(d)
            for d in (sidecar.get("file_impacts") or [])
            if isinstance(d, dict)
        ]
        return AgentWritePolicy(
            work_item_id=wi.id,
            authorized=True,
            primary_repo_id=sidecar.get("primary_repo_id"),
            plan_hash=current_hash,
            file_impacts=impacts,
            not_found_entities=context_package.not_found_entities() if context_package else set(),
        )
    except Exception as exc:  # noqa: BLE001
        return AgentWritePolicy(
            work_item_id=work_item_id, authorized=False,
            block_reason="policy_build_error", block_detail=f"{type(exc).__name__}: {exc}"[:200],
        )


def _normalize(path: str) -> str:
    # NOT str.lstrip("./") -- that strips a *set* of characters, not a
    # prefix, and would mangle "../../etc/passwd" into "etc/passwd",
    # destroying the very ".." traversal marker path_escapes_root() below
    # needs to see.
    normalized = (path or "").strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def authorize_write(
    policy: AgentWritePolicy,
    *,
    tool_name: str,
    repo_id: Any,
    path: str,
    workspace: Path,
) -> WriteDecision:
    """`Mission -> approved plan -> VALID -> current hash matches ->
    primary repo matches -> target path is authorized -> requested action
    matches FileImpact` -- in that order, each a distinct block reason so
    a human (or the model, via the returned error string) can tell exactly
    which link in the chain failed.
    """
    if not policy.authorized:
        return WriteDecision(allowed=False, reason=policy.block_reason or "write_blocked", detail=policy.block_detail)

    if policy.primary_repo_id is not None and repo_id is not None:
        try:
            same_repo = int(repo_id) == int(policy.primary_repo_id)
        except (TypeError, ValueError):
            same_repo = str(repo_id) == str(policy.primary_repo_id)
        if not same_repo:
            return WriteDecision(
                allowed=False, reason="wrong_repository",
                detail=f"target repo {repo_id!r} is not the plan's PRIMARY_WRITE repo ({policy.primary_repo_id})",
            )

    from app.services.work_items import plan_generator

    norm_path = _normalize(path)
    if not norm_path:
        return WriteDecision(allowed=False, reason="empty_path", detail="no path supplied")
    if plan_generator.path_escapes_root(norm_path, workspace):
        return WriteDecision(allowed=False, reason="path_escapes_authorized_root", detail=norm_path)

    if any(ent and ent.lower() in norm_path.lower() for ent in policy.not_found_entities):
        return WriteDecision(
            allowed=False, reason="not_found_entity",
            detail=f"{norm_path} was marked NOT_FOUND by ASK and is not an authorized existing target",
        )

    matched = None
    for impact in policy.file_impacts:
        if _normalize(impact.path).lower() == norm_path.lower():
            matched = impact
            break
    if matched is None:
        return WriteDecision(
            allowed=False, reason="unplanned_path",
            detail=f"{norm_path} is not listed in the approved plan's file impacts",
        )

    action = matched.action
    if action in (plan_generator.ACTION_REFERENCE_ONLY, plan_generator.ACTION_NO_CHANGE):
        return WriteDecision(allowed=False, reason="not_writable_action", detail=f"{norm_path} is marked {action} in the approved plan")

    if tool_name in _DELETE_TOOLS:
        if action != plan_generator.ACTION_DELETE_EXISTING:
            return WriteDecision(allowed=False, reason="delete_not_authorized", detail=f"{norm_path} is planned as {action}, not DELETE_EXISTING")
        return WriteDecision(allowed=True, reason="ok", matched_action=action)

    if action == plan_generator.ACTION_DELETE_EXISTING:
        return WriteDecision(allowed=False, reason="delete_target_not_deletable_here", detail=f"{norm_path} is marked DELETE_EXISTING; {tool_name} cannot be used against it")

    if action == plan_generator.ACTION_MODIFY_EXISTING:
        if not (workspace / norm_path).exists():
            return WriteDecision(allowed=False, reason="modify_target_missing", detail=f"{norm_path} is planned as MODIFY_EXISTING but does not exist in this worktree")
        return WriteDecision(allowed=True, reason="ok", matched_action=action)

    if action == plan_generator.ACTION_CREATE_NEW:
        return WriteDecision(allowed=True, reason="ok", matched_action=action)

    return WriteDecision(allowed=False, reason="unknown_action", detail=f"{norm_path} has unrecognized file-impact action {action!r}")


def evaluate_write(
    *,
    work_item_id: Any,
    repo_id: Any,
    tool_name: str,
    path: str,
    workspace: Path,
) -> WriteDecision:
    """Self-contained entry point for both call sites (lifecycle.py and
    coding_engine_mentrix.py are both deliberately DB-decoupled -- neither
    carries a Session this deep in the call stack), and the single place
    that records the durable per-decision evidence event. Any unexpected
    error anywhere in this path is a BLOCK, never a silent allow.
    """
    from app.domains.work_items.events import append_event
    from app.infrastructure.database import SessionLocal

    db = SessionLocal()
    try:
        try:
            wi_id = int(work_item_id)
        except (TypeError, ValueError):
            return WriteDecision(allowed=False, reason="unresolved_work_item", detail=f"work_item_id={work_item_id!r} is not resolvable")

        policy = build_agent_write_policy(db, wi_id)
        decision = authorize_write(policy, tool_name=tool_name, repo_id=repo_id, path=path, workspace=workspace)

        try:
            append_event(
                db,
                work_item_id=wi_id,
                event_type="agent_write_allowed" if decision.allowed else "agent_write_blocked",
                payload={
                    "tool": tool_name,
                    "path": path,
                    "repo_id": repo_id,
                    "reason": decision.reason,
                    "detail": decision.detail[:400],
                    "matched_action": decision.matched_action,
                },
                commit=True,
            )
        except Exception:  # noqa: BLE001 -- the write decision must stand even if the audit write fails
            pass

        return decision
    except Exception as exc:  # noqa: BLE001
        return WriteDecision(allowed=False, reason="policy_evaluation_error", detail=f"{type(exc).__name__}: {exc}"[:200])
    finally:
        db.close()


def is_write_mutating_tool(name: str) -> bool:
    return name in WRITE_MUTATING_TOOLS
