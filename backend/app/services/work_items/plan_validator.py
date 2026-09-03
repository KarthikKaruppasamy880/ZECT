"""CP-06 -- deterministic hard pre-approval gate for PLAN.

Not another warning system: CP-04/CP-05 already prepend visible banners for
specific defects (unverified answer references, NOT_FOUND leaks, unresolved
placeholders) but a banner is still just text the user could approve past.
This module is the actual gate -- approve_plan() must call it fresh every
time and refuse to proceed unless the result is VALID. No repair happens
here; an INVALID or STALE plan is returned to PLAN/Revise, never silently
patched into something approvable.

Built on top of CP-05's plan_generator primitives (find_placeholder_violations,
validate_file_impacts, _SECTION_ORDER) -- this module re-applies them to the
plan's *current* persisted state at approval time, since a MODIFY_EXISTING
path proven to exist at generation time can be deleted by the time someone
clicks Approve, and a user can edit the repo-local .plan.md directly in
Monaco without ever calling plan() again.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.work_items import plan_generator as pg
from app.services.work_items.context_package import ContextPackage, build_context_package

STATUS_VALID = "VALID"
STATUS_INVALID = "INVALID"
STATUS_STALE = "STALE"


@dataclass
class ValidationFinding:
    rule: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlanValidationResult:
    status: str
    plan_hash: str
    findings: list[ValidationFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == STATUS_VALID

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "plan_hash": self.plan_hash,
            "findings": [f.to_dict() for f in self.findings],
        }


def validate_plan_for_approval(
    *,
    work_item_id: int,
    primary_repo_id: int | None,
    base_commit_sha: str,
    recorded_plan_hash: str,
    plan_text: str,
    current_plan_hash: str,
    sidecar: dict[str, Any] | None,
    context_package: ContextPackage | None,
    repo_root: str,
    architecture: pg.RepoArchitecture,
) -> PlanValidationResult:
    """`recorded_plan_hash` is whatever hash the WorkItem last recorded from
    a plan() call; `current_plan_hash` is freshly computed from `plan_text`
    (the plan bytes actually about to be approved) right now. A mismatch
    between them is exactly "the user edited .plan.md since it was last
    generated" -- STALE, not merely INVALID, since the content itself may
    still be perfectly fine; it just hasn't been validated in this form yet.
    """
    findings: list[ValidationFinding] = []
    stale = recorded_plan_hash != current_plan_hash

    if not plan_text.strip():
        findings.append(ValidationFinding("plan_empty", "the plan has no content"))
        return PlanValidationResult(status=STATUS_INVALID, plan_hash=current_plan_hash, findings=findings)

    sidecar = sidecar or {}

    # 1. plan belongs to the current WorkItem
    sidecar_wi = sidecar.get("work_item_id")
    if sidecar_wi is not None and int(sidecar_wi) != int(work_item_id):
        findings.append(ValidationFinding("plan_ownership", f"machine contract belongs to WorkItem {sidecar_wi}, not {work_item_id}"))

    # 2. primary_repository_id matches
    sidecar_repo = sidecar.get("primary_repo_id")
    if sidecar_wi is not None and sidecar_repo != primary_repo_id:
        findings.append(
            ValidationFinding("primary_repo_mismatch", f"machine contract recorded repo {sidecar_repo}, WorkItem is now bound to {primary_repo_id}")
        )

    # 3. base repository SHA is recorded
    if not (base_commit_sha or "").strip():
        findings.append(ValidationFinding("missing_base_sha", "no base repository commit SHA is recorded for this WorkItem"))

    # 4. required plan sections exist
    missing_sections = [s for s in pg._SECTION_ORDER if f"## {s}" not in plan_text]
    if missing_sections:
        findings.append(ValidationFinding("missing_sections", "missing mandated section(s): " + ", ".join(missing_sections)))

    # 5. no unresolved placeholders/TODO template artifacts
    placeholder_hits = pg.find_placeholder_violations(plan_text)
    if placeholder_hits:
        findings.append(ValidationFinding("unresolved_placeholder", "unresolved placeholder content: " + ", ".join(sorted(set(placeholder_hits)))))

    # NOT_FOUND entities cannot become existing-file actions -- including in
    # free prose with no structured file-impact entry at all (the exact
    # shape of the original CMS hallucination: a narrative claim, not a
    # JSON proposal). developer_service.py already prepends a warning
    # banner for this at generation time; CP-06 must not let that stay a
    # mere warning the user can approve past.
    if context_package is not None:
        prose_leaks = pg.find_not_found_leaks(plan_text, context_package.not_found_entities())
        if prose_leaks:
            findings.append(
                ValidationFinding(
                    "not_found_leak_in_narrative",
                    "NOT_FOUND entities described as existing in the plan's prose without an explicit "
                    "CREATE_NEW/proposed qualifier: " + ", ".join(sorted(prose_leaks)),
                )
            )

    # 6-12, 10 (NOT_FOUND), 11 (repo-root escape), 12 (duplicates): re-run
    # the same deterministic per-impact rules against the CURRENT filesystem
    # and evidence state, not the state at generation time.
    raw_impacts = sidecar.get("file_impacts") or []
    impacts = [pg.FileImpact.from_dict(d) for d in raw_impacts if isinstance(d, dict)]
    pkg_for_check = context_package or build_context_package(
        work_item_id=work_item_id, primary_repo_id=primary_repo_id, repo_sha=base_commit_sha,
        requirement="", ask_findings="", evidence_ledger=[],
    )
    if impacts:
        reaccepted, rerejected = pg.validate_file_impacts(
            impacts, context_package=pkg_for_check, repo_root=repo_root, architecture=architecture
        )
        if rerejected:
            findings.append(
                ValidationFinding(
                    "file_impact_revalidation_failed",
                    "one or more previously-accepted file impacts no longer validate: " + "; ".join(rerejected),
                )
            )
        # 9. every implementation target tied to requirement/evidence references
        untied = [i.path for i in reaccepted if not i.requirement_ids and not i.evidence_refs]
        if untied:
            findings.append(
                ValidationFinding(
                    "untied_file_impact",
                    "file impact(s) with no requirement_ids or evidence_refs: " + ", ".join(untied),
                )
            )
        # 13. plan machine contract vs rendered .plan.md are synchronized --
        # every accepted impact's path must actually appear in the text a
        # human would read and approve.
        missing_from_render = [i.path for i in reaccepted if i.path not in plan_text]
        if missing_from_render:
            findings.append(
                ValidationFinding(
                    "plan_contract_desync",
                    "machine contract lists path(s) not present in the rendered plan text: " + ", ".join(missing_from_render),
                )
            )
    elif sidecar:
        # A sidecar exists but has zero impacts -- only worth flagging if we
        # actually have a sidecar to compare against; a WorkItem with no
        # sidecar at all (pre-CP-06 plan, or plan() never ran) is handled by
        # the "missing_machine_contract" finding below instead.
        pass

    if not sidecar:
        findings.append(
            ValidationFinding(
                "missing_machine_contract",
                "no machine-readable file-impact contract found for this plan -- run Revise to regenerate it",
            )
        )
    elif sidecar.get("plan_hash") and sidecar.get("plan_hash") != current_plan_hash:
        stale = True
        findings.append(
            ValidationFinding(
                "plan_contract_desync",
                f"machine contract was recorded for plan_hash {str(sidecar.get('plan_hash'))[:12]} but the current plan is {current_plan_hash[:12]}",
            )
        )

    if stale:
        return PlanValidationResult(status=STATUS_STALE, plan_hash=current_plan_hash, findings=findings)
    if findings:
        return PlanValidationResult(status=STATUS_INVALID, plan_hash=current_plan_hash, findings=findings)
    return PlanValidationResult(status=STATUS_VALID, plan_hash=current_plan_hash, findings=[])
