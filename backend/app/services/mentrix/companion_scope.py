"""Mentrix Companion orchestration — scope envelope, provenance, canonical handoffs.

Companion is not a second IDE, coding-agent runtime, Present editor, RAG engine,
or WorkItem store. It binds the active Project / authorized roots, tags context
with identity, and hands off to canonical ZECT surfaces.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any
from urllib.parse import urlencode

from sqlalchemy.orm import Session

# Honest product limitation (Developer multi-root IDE / PR #156).
SEMANTIC_CROSS_REPO_REFERENCES = False

_SECRET_NAME_RE = re.compile(
    r"(password|secret|token|api[_-]?key|authorization|private[_-]?key)",
    re.I,
)
_SECRET_VALUE_RE = re.compile(
    r"(?i)(password|secret|token|api[_-]?key)\s*[:=]\s*\S+",
)

HANDOFF_PATHS: dict[str, str] = {
    "workspace": "/workspace",
    "present": "/present",
    "present_create": "/present/create",
    "work_items": "/work-items",
    "projects": "/projects",
    "fabric": "/fabric",
    "processes": "/work-items",
    "companion": "/mentrix-home",
    "lattice": "/lattice",
}


def redact_secrets(text: str) -> str:
    raw = str(text or "")
    return _SECRET_VALUE_RE.sub(lambda m: f"{m.group(1)}=[redacted]", raw)


def _git_head(path: str) -> str:
    root = (path or "").strip()
    if not root or not os.path.isdir(root):
        return ""
    try:
        out = subprocess.check_output(
            ["git", "-C", root, "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2,
            text=True,
        )
        return (out or "").strip()[:40]
    except Exception:  # noqa: BLE001
        return ""


def external_connectors() -> dict[str, dict[str, Any]]:
    """Honest connector readiness — never fake PASS when unset."""
    jira = bool(
        (os.getenv("JIRA_BASE_URL") or os.getenv("MCP_JIRA_URL") or "").strip()
        and (os.getenv("JIRA_EMAIL") or "").strip()
        and (os.getenv("JIRA_API_TOKEN") or "").strip()
    )
    camunda = bool((os.getenv("ZECT_CAMUNDA_BASE_URL") or "").strip())
    voicebox = bool((os.getenv("ZECT_VOICEBOX_URL") or os.getenv("VOICEBOX_URL") or "").strip())
    presenton = (os.getenv("ZECT_PRESENTATION_PROVIDER") or "presenton").strip().lower() != "none"
    return {
        "jira": {
            "ready": jira,
            "status": "ready" if jira else "BLOCKED_EXTERNAL",
            "detail": "JIRA_BASE_URL + JIRA_EMAIL + JIRA_API_TOKEN" if not jira else "",
        },
        "camunda": {
            "ready": camunda,
            "status": "ready" if camunda else "BLOCKED_EXTERNAL",
            "detail": "ZECT_CAMUNDA_BASE_URL unset" if not camunda else "",
        },
        "voicebox": {
            "ready": voicebox,
            "status": "ready" if voicebox else "degraded",
            "detail": "Voicebox URL unset — stock/browser TTS fallback" if not voicebox else "",
        },
        "present": {
            "ready": presenton,
            "status": "ready" if presenton else "BLOCKED_EXTERNAL",
            "detail": "",
        },
    }


def authorized_roots(db: Session, project_id: int | None) -> list[dict[str, Any]]:
    if not project_id:
        return []
    from app.models import Project, Repo

    project = db.query(Project).filter(Project.id == int(project_id)).first()
    if not project:
        return []
    rows = db.query(Repo).filter(Repo.project_id == int(project_id)).order_by(Repo.id.asc()).all()
    out: list[dict[str, Any]] = []
    for repo in rows:
        path = str(repo.local_path or "")
        sha = _git_head(path) or ""
        label = f"{repo.owner}/{repo.repo_name}".strip("/") or f"repo-{repo.id}"
        lattice_state = "NOT_APPLICABLE"
        from app.services.lattice.indexer import derive_project_key, get_lattice_status

        lattice_key = derive_project_key(str(repo.owner or ""), str(repo.repo_name or ""))
        try:
            st = get_lattice_status(lattice_key, db=db, repository_id=int(repo.id))
            lattice_state = str(st.get("state") or "NOT_APPLICABLE")
        except Exception:  # noqa: BLE001
            lattice_state = "NOT_APPLICABLE"
        out.append(
            {
                "id": int(repo.id),
                "label": label,
                "path": path,
                "commit_sha": sha,
                "indexed_at": repo.indexed_at.isoformat() if getattr(repo, "indexed_at", None) else "",
                "clone_status": str(repo.clone_status or ""),
                "lattice_state": lattice_state,
                "lattice_project_key": lattice_key,
                "authorized": True,
            }
        )
    return out


def filter_requested_repos(
    authorized: list[dict[str, Any]],
    requested: list[int] | None,
) -> tuple[list[int], list[int]]:
    allowed = {int(r["id"]) for r in authorized}
    if not requested:
        return sorted(allowed), []
    kept: list[int] = []
    skipped: list[int] = []
    for raw in requested:
        try:
            rid = int(raw)
        except (TypeError, ValueError):
            continue
        if rid in allowed:
            kept.append(rid)
        else:
            skipped.append(rid)
    return kept, skipped


def handoff_url(surface: str, envelope: dict[str, Any], extra: dict[str, str] | None = None) -> str:
    path = HANDOFF_PATHS.get(surface) or "/mentrix-home"
    q: dict[str, str] = {}
    if envelope.get("project_id"):
        q["project_id"] = str(envelope["project_id"])
    if envelope.get("workspace_id"):
        q["workspace_id"] = str(envelope["workspace_id"])
    if envelope.get("work_item_id"):
        q["work_item_id"] = str(envelope["work_item_id"])
    repo_ids = envelope.get("repo_ids") or []
    if repo_ids:
        q["repo_ids"] = ",".join(str(i) for i in repo_ids)
    if envelope.get("active_root_id"):
        q["repository_id"] = str(envelope["active_root_id"])
    if envelope.get("plan_ref"):
        q["plan_ref"] = str(envelope["plan_ref"])[:120]
    if extra:
        for key, val in extra.items():
            if val:
                q[str(key)] = str(val)[:500]
    if not q:
        return path
    return f"{path}?{urlencode(q)}"


def build_companion_scope(
    db: Session,
    *,
    project_id: int | None = None,
    repository_ids: list[int] | None = None,
    work_item_id: int | None = None,
    workspace_id: str = "",
    active_root_id: int | None = None,
    created_by: str = "",
) -> dict[str, Any]:
    from app.models import Project, WorkItem

    roots = authorized_roots(db, project_id)
    kept, skipped = filter_requested_repos(roots, repository_ids)
    root_by_id = {int(r["id"]): r for r in roots}
    all_ids = [int(r["id"]) for r in roots]
    # Display every authorized root. Tool/handoff repo_ids: requested∩authorized, else all.
    scoped_ids = kept if repository_ids else all_ids
    scoped_roots = roots

    project_name = ""
    if project_id:
        proj = db.query(Project).filter(Project.id == int(project_id)).first()
        project_name = str(getattr(proj, "name", "") or "") if proj else ""

    wi = None
    wi_title = ""
    plan_ref = ""
    evidence_ref = ""
    source = ""
    external_id = ""
    if work_item_id:
        wi = db.query(WorkItem).filter(WorkItem.id == int(work_item_id)).first()
        if wi:
            if project_id and wi.project_id and int(wi.project_id) != int(project_id):
                wi = None
            else:
                wi_title = str(wi.title or "")
                plan_ref = str(wi.plan_hash or "")
                evidence_ref = str(wi.current_commit_sha or wi.base_commit_sha or "")
                source = str(wi.source or "")
                external_id = str(wi.external_id or "")
                if wi.repository_id and int(wi.repository_id) in root_by_id and int(wi.repository_id) not in scoped_ids:
                    scoped_ids = list(dict.fromkeys([*scoped_ids, int(wi.repository_id)]))

    active = active_root_id if active_root_id in scoped_ids else (scoped_ids[0] if scoped_ids else None)
    ws = (workspace_id or project_name or "").strip()
    commit_shas = {str(r["id"]): r.get("commit_sha") or "" for r in scoped_roots}
    envelope = {
        "project_id": int(project_id) if project_id else None,
        "project_name": project_name,
        "workspace_id": ws,
        "work_item_id": int(wi.id) if wi else None,
        "work_item_title": wi_title,
        "work_item_source": source,
        "external_id": external_id,
        "repo_ids": scoped_ids,
        "active_root_id": active,
        "roots": scoped_roots,
        "commit_shas": commit_shas,
        "plan_ref": plan_ref,
        "evidence_ref": evidence_ref,
        "semantic_cross_repo_references": SEMANTIC_CROSS_REPO_REFERENCES,
        "skipped_unauthorized_repo_ids": skipped,
        "created_by": created_by or "",
        "connectors": external_connectors(),
        "companion_edits_code": False,
        "companion_edits_present": False,
    }
    envelope["handoffs"] = {
        surface: handoff_url(surface, envelope)
        for surface in ("workspace", "present", "present_create", "work_items", "projects", "fabric", "processes")
    }
    return envelope


def bind_tool_args(name: str, args: dict[str, Any] | None, envelope: dict[str, Any]) -> dict[str, Any]:
    """Inject identity envelope. Never attach unauthorized repo ids."""
    out = dict(args or {})
    if envelope.get("project_id") and not out.get("project_id"):
        out["project_id"] = envelope["project_id"]
    if envelope.get("work_item_id") and not out.get("work_item_id"):
        out["work_item_id"] = envelope["work_item_id"]
    if envelope.get("workspace_id") and not out.get("project_key"):
        out["project_key"] = envelope["workspace_id"]
    authorized = {int(i) for i in (envelope.get("repo_ids") or [])}

    requested_ids: list[int] = []
    raw_ids = out.get("repository_ids")
    if isinstance(raw_ids, list):
        for item in raw_ids:
            try:
                requested_ids.append(int(item))
            except (TypeError, ValueError):
                continue
    if out.get("repository_id") not in (None, "", 0, "0"):
        try:
            requested_ids.append(int(out["repository_id"]))
        except (TypeError, ValueError):
            pass

    skipped: list[int] = []
    kept: list[int] = []
    for rid in requested_ids:
        if authorized and rid not in authorized:
            skipped.append(rid)
        elif authorized:
            kept.append(rid)
        else:
            skipped.append(rid)

    if requested_ids:
        out["repository_ids"] = list(dict.fromkeys(kept))
        if kept:
            out["repository_id"] = kept[0]
        else:
            out.pop("repository_id", None)
            out["repo_authorization"] = "denied"
        out["skipped_unauthorized_repo_ids"] = list(dict.fromkeys(skipped))
    elif authorized and name in (
        "mentrix_developer_ask",
        "mentrix_developer_plan",
        "companion_intelligence",
        "coding_agent_start",
        "work_item_open_or_create",
    ):
        out["repository_ids"] = list(authorized)
        active = envelope.get("active_root_id")
        out["repository_id"] = active if active in authorized else next(iter(authorized))

    shas = envelope.get("commit_shas") or {}
    if shas and not out.get("base_commit_sha"):
        rid = out.get("repository_id") or envelope.get("active_root_id")
        out["base_commit_sha"] = str(shas.get(str(rid)) or next(iter(shas.values()), "") or "")
    return out


def tag_hits_with_identity(
    hits: list[dict[str, Any]] | None,
    roots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tagged: list[dict[str, Any]] = []
    for hit in hits or []:
        row = dict(hit)
        path = str(row.get("path") or "")
        matched = None
        for root in roots:
            rp = str(root.get("path") or "").replace("\\", "/").rstrip("/")
            hp = path.replace("\\", "/")
            if rp and hp.startswith(rp):
                matched = root
                break
        if matched:
            row["repository_id"] = matched.get("id")
            row["repo_label"] = matched.get("label")
            row["commit_sha"] = matched.get("commit_sha") or row.get("commit_sha") or ""
        else:
            row.setdefault("repository_id", None)
            row.setdefault("repo_label", "")
            row.setdefault("commit_sha", "")
        row["semantic_cross_repo_references"] = SEMANTIC_CROSS_REPO_REFERENCES
        tagged.append(row)
    return tagged


def provenance_rows(
    *,
    envelope: dict[str, Any],
    lattice_hits: list[dict[str, Any]] | None = None,
    knowledge_hits: list[dict[str, Any]] | None = None,
    memory_hits: list[dict[str, Any]] | None = None,
    pi: dict[str, Any] | None = None,
    used_tools: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Only mark a source used when this turn actually consumed it."""
    tools = set(used_tools or [])
    lattice_used = bool(lattice_hits) or "lattice_query" in tools or "companion_intelligence" in tools
    knowledge_used = bool(knowledge_hits)
    memory_used = bool(memory_hits)
    pi_fresh = str(((pi or {}).get("freshness") or {}).get("lattice") or "")
    roots = envelope.get("roots") or []
    stale = any(str(r.get("lattice_state") or "") == "STALE" for r in roots)
    if pi_fresh.upper() == "STALE":
        stale = True

    def _status(used: bool, empty_ok: bool = True) -> str:
        if used and stale and "lattice" in (used_tools or []):
            return "stale"
        if used:
            return "used"
        return "not_used" if empty_ok else "missing"

    wi = envelope.get("work_item_id")
    return [
        {
            "id": "project",
            "label": "Project",
            "status": "used" if envelope.get("project_id") else "missing",
            "detail": envelope.get("project_name") or "No active Project",
        },
        {
            "id": "roots",
            "label": "Authorized roots",
            "status": "used" if roots else "missing",
            "detail": ", ".join(str(r.get("label") or r.get("id")) for r in roots) or "none",
        },
        {
            "id": "work_item",
            "label": "WorkItem",
            "status": "used" if wi else "not_used",
            "detail": envelope.get("work_item_title") or (f"#{wi}" if wi else "none this turn"),
        },
        {
            "id": "lattice",
            "label": "Lattice",
            "status": "stale" if lattice_used and stale else ("used" if lattice_hits else "not_used"),
            "detail": f"{len(lattice_hits or [])} hit(s)" if lattice_hits else "not queried or no hits",
        },
        {
            "id": "knowledge",
            "label": "Knowledge",
            "status": _status(knowledge_used),
            "detail": f"{len(knowledge_hits or [])} hit(s)" if knowledge_hits else "not used",
        },
        {
            "id": "memory",
            "label": "Verified Memory",
            "status": _status(memory_used),
            "detail": f"{len(memory_hits or [])} hit(s)" if memory_hits else "not used",
        },
        {
            "id": "semantic",
            "label": "Semantic cross-repo refs",
            "status": "not_used",
            "detail": "not implemented",
        },
    ]


def aggregate_sibling_status(per_repo: list[dict[str, Any]]) -> dict[str, Any]:
    """PASS + FAIL on siblings => aggregate BLOCKED. Never hide a sibling failure."""
    rows = list(per_repo or [])
    if not rows:
        return {
            "aggregate": "pending",
            "ready": False,
            "blocked": False,
            "per_repo": [],
            "reason": "no_repos",
        }
    statuses = [str(r.get("status") or "").lower() for r in rows]
    failed = [r for r in rows if str(r.get("status") or "").lower() in {"fail", "failed", "error", "blocked"}]
    passed = [r for r in rows if str(r.get("status") or "").lower() in {"pass", "passed", "ready", "ok"}]
    if failed:
        return {
            "aggregate": "BLOCKED",
            "ready": False,
            "blocked": True,
            "per_repo": rows,
            "failed_repo_ids": [r.get("repository_id") for r in failed],
            "reason": "sibling_failure",
            "evidence": failed,
        }
    if passed and len(passed) == len(rows):
        return {
            "aggregate": "READY",
            "ready": True,
            "blocked": False,
            "per_repo": rows,
            "reason": "all_siblings_pass",
        }
    if any(s in {"executing", "running", "pending"} for s in statuses):
        return {
            "aggregate": "EXECUTING",
            "ready": False,
            "blocked": False,
            "per_repo": rows,
            "reason": "in_progress",
        }
    return {
        "aggregate": "PENDING",
        "ready": False,
        "blocked": False,
        "per_repo": rows,
        "reason": "incomplete",
    }


def intelligence_pack(
    db: Session,
    envelope: dict[str, Any],
    query: str,
) -> dict[str, Any]:
    """Project Intelligence + Lattice with identity tags. Never invent unused context."""
    from app.services.work_items.project_intelligence import ProjectIntelligenceService

    q = (query or "").strip()
    pid = envelope.get("project_id")
    pkey = str(envelope.get("workspace_id") or envelope.get("project_name") or "")
    rid = envelope.get("active_root_id")
    snap = ProjectIntelligenceService().snapshot(
        project_id=pid,
        project_key=pkey,
        repository_id=rid,
        db=db,
        query=q,
    )
    pi = snap.to_dict()
    lattice = pi.get("lattice") or {}
    raw_hits = list(lattice.get("hits") or [])
    tagged = tag_hits_with_identity(raw_hits, envelope.get("roots") or [])
    knowledge = list(pi.get("knowledge") or [])
    memory = list(pi.get("memory") or [])
    same_name: dict[str, list[dict[str, Any]]] = {}
    for hit in tagged:
        name = str(hit.get("name") or os.path.basename(str(hit.get("path") or "")) or "").strip()
        if not name:
            continue
        same_name.setdefault(name, []).append(
            {
                "repository_id": hit.get("repository_id"),
                "repo_label": hit.get("repo_label"),
                "path": hit.get("path"),
                "commit_sha": hit.get("commit_sha"),
            }
        )
    collisions = {k: v for k, v in same_name.items() if len(v) > 1}
    provenance = provenance_rows(
        envelope=envelope,
        lattice_hits=tagged,
        knowledge_hits=knowledge,
        memory_hits=memory,
        pi=pi,
        used_tools=["companion_intelligence"],
    )
    spoken_bits = []
    if envelope.get("project_name"):
        spoken_bits.append(f"Project {envelope['project_name']}")
    if envelope.get("roots"):
        spoken_bits.append(
            f"{len(envelope['roots'])} authorized root(s): "
            + ", ".join(str(r.get("label")) for r in envelope["roots"][:6])
        )
    if tagged:
        spoken_bits.append(f"Lattice {len(tagged)} hit(s) with repo/commit identity.")
    else:
        spoken_bits.append("Lattice not used or no hits — not claiming unused context.")
    if collisions:
        spoken_bits.append(
            "Same-named symbols/files exist across roots; semantic cross-repo references are not implemented."
        )
    if envelope.get("skipped_unauthorized_repo_ids"):
        spoken_bits.append("Unauthorized repository ids were skipped.")
    return {
        "ok": True,
        "spoken_summary": " ".join(spoken_bits)[:800],
        "pi": pi,
        "lattice_hits": tagged,
        "knowledge_hits": knowledge,
        "memory_hits": memory,
        "same_named_collisions": collisions,
        "semantic_cross_repo_references": SEMANTIC_CROSS_REPO_REFERENCES,
        "provenance": provenance,
        "envelope": {
            "project_id": envelope.get("project_id"),
            "workspace_id": envelope.get("workspace_id"),
            "work_item_id": envelope.get("work_item_id"),
            "repo_ids": envelope.get("repo_ids"),
            "commit_shas": envelope.get("commit_shas"),
        },
        "board": {
            "type": "table",
            "title": "Context used this turn",
            "data": {
                "columns": ["source", "status", "detail"],
                "rows": [[p["label"], p["status"], p["detail"]] for p in provenance],
            },
        },
    }


def open_or_create_work_item(
    db: Session,
    envelope: dict[str, Any],
    *,
    title: str,
    description: str = "",
    source: str = "companion",
    external_id: str = "",
    created_by: str = "",
) -> dict[str, Any]:
    from app.domains.work_items import service as wi_svc
    from app.models import WorkItem

    wid = envelope.get("work_item_id")
    if wid:
        wi = db.query(WorkItem).filter(WorkItem.id == int(wid)).first()
        if not wi:
            return {"ok": False, "error": "work_item_not_found", "spoken_summary": "WorkItem not found."}
        if envelope.get("project_id") and wi.project_id and int(wi.project_id) != int(envelope["project_id"]):
            return {
                "ok": False,
                "error": "work_item_project_mismatch",
                "spoken_summary": "That WorkItem belongs to another project.",
            }
        ser = wi_svc.serialize_work_item(wi)
        return {
            "ok": True,
            "created": False,
            "work_item_id": wi.id,
            "work_item": ser,
            "spoken_summary": f"Opened WorkItem #{wi.id}: {wi.title}. Companion does not edit code.",
            "navigate": handoff_url("work_items", {**envelope, "work_item_id": wi.id}),
        }

    if external_id:
        existing = (
            db.query(WorkItem)
            .filter(WorkItem.source == (source or "companion"), WorkItem.external_id == external_id)
            .first()
        )
        if existing:
            if envelope.get("project_id") and existing.project_id and int(existing.project_id) != int(envelope["project_id"]):
                return {
                    "ok": False,
                    "error": "work_item_project_mismatch",
                    "spoken_summary": "That ticket maps to another project.",
                }
            ser = wi_svc.serialize_work_item(existing)
            return {
                "ok": True,
                "created": False,
                "work_item_id": existing.id,
                "work_item": ser,
                "spoken_summary": f"Reopened WorkItem #{existing.id} from {source} {external_id}.",
                "navigate": handoff_url("work_items", {**envelope, "work_item_id": existing.id}),
            }

    clean_title = (title or "").strip() or "Companion work item"
    repo_ids = list(envelope.get("repo_ids") or [])
    primary = envelope.get("active_root_id") or (repo_ids[0] if repo_ids else None)
    shas = envelope.get("commit_shas") or {}
    wi = wi_svc.create_work_item(
        db,
        title=clean_title[:240],
        description=description or "",
        source=source or "companion",
        external_id=external_id or "",
        project_id=envelope.get("project_id"),
        repository_id=primary,
        repository_ref="",
        base_commit_sha=str(shas.get(str(primary)) or ""),
        created_by=created_by or envelope.get("created_by") or "",
    )
    snap = {
        "repo_ids": repo_ids,
        "commit_shas": shas,
        "workspace_id": envelope.get("workspace_id") or "",
        "opened_from": "mentrix_companion",
    }
    wi.context_snapshot_json = json.dumps(snap)
    db.add(wi)
    db.commit()
    db.refresh(wi)
    ser = wi_svc.serialize_work_item(wi)
    env2 = {**envelope, "work_item_id": wi.id, "work_item_title": wi.title}
    return {
        "ok": True,
        "created": True,
        "work_item_id": wi.id,
        "work_item": ser,
        "envelope": {
            "project_id": env2.get("project_id"),
            "workspace_id": env2.get("workspace_id"),
            "work_item_id": wi.id,
            "repo_ids": repo_ids,
            "commit_shas": shas,
        },
        "spoken_summary": (
            f"Created WorkItem #{wi.id} for {len(repo_ids) or 0} authorized root(s). "
            "Opening Work Items — Companion does not edit files."
        ),
        "navigate": handoff_url("workspace", env2, extra={"goal": clean_title[:200]}),
        "handoff": env2.get("handoffs") if isinstance(env2.get("handoffs"), dict) else handoff_url("workspace", env2),
    }


def progress_snapshot(
    *,
    stage: str,
    envelope: dict[str, Any],
    blocker: str = "",
    per_repo: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sibling = aggregate_sibling_status(per_repo or [])
    return {
        "task": envelope.get("work_item_title") or "Companion orchestration",
        "stage": stage,
        "affected_repos": envelope.get("repo_ids") or [],
        "roots": [r.get("label") for r in (envelope.get("roots") or [])],
        "blocker": blocker,
        "cancelable": True,
        "sibling": sibling,
        "companion_edits_code": False,
    }


def process_ticket_handoff(
    envelope: dict[str, Any],
    *,
    issue_key: str = "",
    db: Session | None = None,
    created_by: str = "",
) -> dict[str, Any]:
    connectors = envelope.get("connectors") or external_connectors()
    jira = connectors.get("jira") or {}
    camunda = connectors.get("camunda") or {}
    if not jira.get("ready") and not camunda.get("ready"):
        return {
            "ok": False,
            "blocked_external": True,
            "error": "BLOCKED_EXTERNAL",
            "spoken_summary": (
                "Jira and Mentrix Process are not configured. "
                "Cannot create a live ticket — BLOCKED_EXTERNAL. Work Items remain available."
            ),
            "handoff": handoff_url("work_items", envelope),
            "connectors": connectors,
        }
    source = "jira" if jira.get("ready") else "camunda"
    extra = {"issue_key": issue_key} if issue_key else None
    created: dict[str, Any] = {}
    env2 = dict(envelope)
    if db is not None:
        created = open_or_create_work_item(
            db,
            envelope,
            title=(f"{issue_key} — process ticket" if issue_key else "Companion process/ticket handoff"),
            description=(
                "Opened from Mentrix Companion. Companion does not create Jira or Camunda tickets itself."
            ),
            source=source,
            external_id=issue_key,
            created_by=created_by,
        )
        if created.get("work_item_id"):
            env2["work_item_id"] = created["work_item_id"]
            wi = created.get("work_item") if isinstance(created.get("work_item"), dict) else {}
            env2["work_item_title"] = wi.get("title") if isinstance(wi, dict) else None
    nav = handoff_url("work_items", env2, extra=extra)
    wid = env2.get("work_item_id")
    return {
        "ok": True,
        "blocked_external": False,
        "work_item_id": wid,
        "work_item": created.get("work_item"),
        "source": source,
        "spoken_summary": (
            f"{source} is configured. "
            + (f"WorkItem #{wid} opened with source identity preserved. " if wid else "")
            + "Opening Work Items. Companion does not edit Jira or Camunda."
        ),
        "navigate": nav,
        "connectors": connectors,
    }
