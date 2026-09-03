"""MentrixDeveloperService — ASK / PLAN / AGENT orchestration (P0)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.work_items import service as wi_svc
from app.domains.work_items.events import append_event
from app.domains.work_items.status import (
    STATUS_EXECUTING,
    STATUS_IMPLEMENTED,
    STATUS_NEEDS_HUMAN_DECISION,
    STATUS_PLAN_APPROVED,
    STATUS_PLANNED,
    STATUS_READY_TO_SHIP,
    STATUS_VERIFYING,
)
from app.models import MentrixRun, WorkItem, WorkItemEvent
from app.services.work_items.artifact_store import ArtifactStore
from app.services.work_items.checkpoints import load_execution_state, record_checkpoint
from app.services.work_items import context_package as cp_module
from app.services.work_items.context_engine import MentrixContextEngine, ProvenanceItem
from app.services.work_items.evidence_verifier import EvidenceVerifier
from app.services.work_items.fallback_policy import resolve_model_route
from app.services.work_items.project_intelligence import ProjectIntelligenceService
from app.services.work_items.multi_repo_context import (
    build_affected_repos_manifest,
    merge_context_packs,
    repo_binding,
    resolve_authorized_repository_ids,
)
from app.services.work_items.telemetry import TelemetryTimer, build_telemetry


def _context_used_summary(pi: dict[str, Any] | None) -> dict[str, Any]:
    """Compact, durable summary of a resolved ProjectIntelligenceSnapshot dict
    (developer_service's `built["pi"]`, i.e. snapshot().to_dict()) -- the
    same {knowledge, lattice_hits, lattice_indexed, lattice_state, blueprint}
    shape agent_context.py's compose_rich_agent_context_pack() already
    computes for Mission's "Context Used" strip, and the frontend's
    contextFromDeveloperPi() already renders for a live ask() response. Ask
    persists THIS instead of the full context_pack/project_intelligence
    blob -- small enough to store per-turn, but enough to re-render the
    Context Used strip on history replay (tab switch / refresh / restart)
    without the user having to ask a new question first."""
    pi = pi or {}
    lattice = pi.get("lattice") or {}
    hits = list(lattice.get("hits") or [])
    state = str(lattice.get("status") or lattice.get("state") or "").strip().upper() or "NOT_APPLICABLE"
    blueprint = pi.get("blueprint") or {}
    knowledge = pi.get("knowledge") or []
    return {
        "knowledge": bool(knowledge),
        "lattice_hits": len(hits),
        "lattice_indexed": state == "READY",
        "lattice_state": state,
        "blueprint": bool(blueprint.get("snippet")),
    }


class MentrixDeveloperService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.context_engine = MentrixContextEngine()
        self.pi = ProjectIntelligenceService()
        self.verifier = EvidenceVerifier()

    def _store(self, work_item_id: int) -> ArtifactStore:
        return ArtifactStore(work_item_id)

    def _ensure_work_item(
        self,
        *,
        work_item_id: int | None,
        title: str,
        project_id: int | None,
        repository_id: int | None,
        repository_ref: str,
        base_commit_sha: str,
        actor: str,
    ) -> WorkItem:
        if work_item_id:
            return wi_svc.get_work_item(self.db, work_item_id)
        return wi_svc.create_work_item(
            self.db,
            title=title[:200],
            description=title,
            project_id=project_id,
            repository_id=repository_id,
            repository_ref=repository_ref,
            base_commit_sha=base_commit_sha,
            created_by=actor,
        )

    def _resolve_user_id(self, actor_or_created_by: str) -> int | None:
        s = (actor_or_created_by or "").strip()
        if not s:
            return None
        try:
            if s.isdigit():
                return int(s)
        except ValueError:
            pass
        try:
            from app.models import User

            u = self.db.query(User).filter(User.email == s).first()
            return int(u.id) if u else None
        except Exception:  # noqa: BLE001
            return None

    def _build_pack(
        self,
        wi: WorkItem,
        goal: str,
        *,
        repository_id: int | None = None,
        repository_ref: str = "",
        base_commit_sha: str = "",
    ) -> dict[str, Any]:
        rid = repository_id if repository_id is not None else wi.repository_id
        ref = repository_ref or wi.repository_ref or ""
        sha = base_commit_sha or wi.base_commit_sha or ""
        project_key = ""
        try:
            # The Lattice indexes per repository root under
            # derive_project_key(owner, repo) -- the same key the frontend
            # computes -- so a Project display name would look up a graph
            # that was never written (finding F6). Only fall back to the
            # project name for a work item with no repository at all.
            from app.services.lattice.indexer import project_key_for_repository

            project_key = project_key_for_repository(self.db, rid)
            if not project_key and wi.project_id and self.db is not None:
                from app.models import Project

                p = self.db.query(Project).filter(Project.id == wi.project_id).first()
                project_key = (getattr(p, "name", None) or getattr(p, "key", None) or "") if p else ""
        except Exception:  # noqa: BLE001
            project_key = ""
        snap = self.pi.snapshot(
            project_id=wi.project_id,
            project_key=str(project_key or ""),
            repository_id=rid,
            db=self.db,
            query=goal,
        )
        doc_items: list = []
        web_items: list = []
        try:
            from app.services.document_intelligence.service import retrieve_document_context
            from app.services.web_intelligence.service import retrieve_web_context

            actor_uid = self._resolve_user_id(getattr(wi, "created_by", "") or "")
            if actor_uid:
                try:
                    doc_items, _meta = retrieve_document_context(
                        self.db,
                        user_id=actor_uid,
                        query=goal,
                        project_id=wi.project_id,
                        max_tokens=800,
                    )
                except Exception:  # noqa: BLE001
                    doc_items = []
                try:
                    web_items, _wmeta = retrieve_web_context(
                        self.db,
                        user_id=actor_uid,
                        query=goal,
                        project_id=wi.project_id,
                        max_tokens=800,
                    )
                except Exception:  # noqa: BLE001
                    web_items = []
        except Exception:  # noqa: BLE001
            pass
        file_items = self._workspace_file_items(
            repository_ids=[int(rid)] if rid else [],
            query=goal,
        )
        pack = self.context_engine.build(
            work_item_id=wi.id,
            repository_id=rid,
            repository_ref=ref,
            base_commit_sha=sha,
            goal=goal,
            knowledge_hits=snap.knowledge,
            memory_hits=snap.memory,
            lattice_hits=list((snap.lattice or {}).get("hits") or []),
            blueprint_snippet=str((snap.blueprint or {}).get("snippet") or ""),
            extra_items=list(doc_items) + list(web_items) + file_items,
        )
        return {"pack": pack.to_dict(), "pi": snap.to_dict(), "pack_obj": pack}

    _ASK_STOP = frozenset(
        {
            "what",
            "which",
            "where",
            "when",
            "this",
            "that",
            "with",
            "from",
            "file",
            "files",
            "does",
            "define",
            "defines",
            "token",
        }
    )

    def _workspace_file_items(self, *, repository_ids: list[int], query: str) -> list[ProvenanceItem]:
        """Grep authorized local roots so ASK is file-grounded before Lattice is indexed."""
        from app.infrastructure.allowed_paths import path_under_allowed_roots
        from app.models import Repo

        tokens = [
            t
            for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", query or "")
            if t.lower() not in self._ASK_STOP
        ]
        tokens = sorted(set(tokens), key=len, reverse=True)[:5]
        if not tokens or not repository_ids:
            return []
        regexes = [re.compile(re.escape(t), re.IGNORECASE) for t in tokens]
        skip_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}
        items: list[ProvenanceItem] = []
        for rid in repository_ids:
            repo = self.db.query(Repo).filter(Repo.id == int(rid)).first()
            local = str(getattr(repo, "local_path", "") or "") if repo else ""
            if not local:
                continue
            try:
                root = path_under_allowed_roots(local)
            except ValueError:
                continue
            if not root.is_dir():
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]
                for name in filenames:
                    if name.startswith("."):
                        continue
                    fpath = Path(dirpath) / name
                    try:
                        if fpath.stat().st_size > 400_000:
                            continue
                        text = fpath.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        continue
                    rel = str(fpath.relative_to(root)).replace("\\", "/")
                    for i, line in enumerate(text.splitlines(), 1):
                        if any(rx.search(line) for rx in regexes):
                            items.append(
                                ProvenanceItem(
                                    source_type="workspace_file",
                                    source_id=f"{rel}:{i}",
                                    content=f"{rel}:{i}: {line.strip()[:240]}",
                                    repository=str(rid),
                                    freshness="current",
                                    verification_state="file_search",
                                    selection_reason="authorized_local_grep",
                                    retrieval_score=1.0,
                                )
                            )
                            if len(items) >= 12:
                                return items
                            break
        return items

    # CP-02 anti-hallucination gate (finding A1): a class/file/route-shaped
    # name in ASK's prose answer is a factual claim -- "this exists in the
    # repository" -- and the CMS benchmark proved the model will invent
    # plausible-sounding ones (CampaignWizard, ApprovalService,
    # POST /campaigns/initiate) when real grounding is weak. The system
    # prompt (llm_phase.run_ask) asks the model not to; this is the second,
    # code-level check that doesn't depend on the model actually listening
    # (the same two-layer pattern Roo Code uses for tool permissions).
    _ANSWER_FILENAME_RE = re.compile(r"\b[\w][\w\-]*\.[A-Za-z][A-Za-z0-9]{0,8}\b")
    _CLASS_LIKE_RE = re.compile(r"\b(?:[A-Z][a-z0-9]+){2,}\b")
    _API_ROUTE_RE = re.compile(r"\b(?:GET|POST|PUT|DELETE|PATCH)\s+/[\w{}:/-]+")

    def _check_answer_grounding(self, answer: str, pack_obj: Any) -> dict[str, Any]:
        """Backward-compatible shape for existing callers/tests: plain
        verified/unverified name lists. Delegates to _build_evidence_ledger()
        (CP-04) so there is exactly one place that decides what counts as
        grounded, not two independently-drifting implementations."""
        ledger = self._build_evidence_ledger(answer, pack_obj, repo_id=None, repo_sha="")
        return {
            "verified": sorted(e.entity for e in ledger if e.status == cp_module.STATUS_VERIFIED),
            "unverified": sorted(e.entity for e in ledger if e.status == cp_module.STATUS_NOT_FOUND),
            "checked": True,
        }

    def _build_evidence_ledger(
        self, answer: str, pack_obj: Any, *, repo_id: int | None, repo_sha: str
    ) -> list[cp_module.EvidenceLedgerEntry]:
        """CP-04 Evidence Ledger: which class/file/route-shaped names in
        `answer` actually appear in the retrieved context, typed and with
        the specific provenance backing each VERIFIED claim -- the
        structured replacement for a prose "Unverified references" banner
        that a later phase (PLAN) would otherwise have to re-interpret from
        free text. Runs even when there is no context at all -- in that
        case every named entity is NOT_FOUND, which is the correct signal
        (finding A1)."""
        text = answer or ""
        typed_candidates: dict[str, str] = {}  # entity -> entity_type, first match wins
        for m in self._ANSWER_FILENAME_RE.finditer(text):
            typed_candidates.setdefault(m.group(0), "file")
        for m in self._CLASS_LIKE_RE.finditer(text):
            typed_candidates.setdefault(m.group(0), "class")
        for m in self._API_ROUTE_RE.finditer(text):
            typed_candidates.setdefault(m.group(0), "api_route")
        if not typed_candidates:
            return []
        items = list(getattr(pack_obj, "items", None) or [])
        ledger: list[cp_module.EvidenceLedgerEntry] = []
        for name in sorted(typed_candidates):
            entity_type = typed_candidates[name]
            matches = [it for it in items if name.lower() in str(getattr(it, "content", "") or "").lower()]
            # A content match is the actual evidence -- keep it even when the
            # matching item has no source_id (a falsy-ref filter here would
            # silently drop the match itself, not just its label, and wrongly
            # report a genuinely-grounded entity as NOT_FOUND).
            refs = [str(getattr(it, "source_id", "") or "unspecified") for it in matches][:5]
            status = cp_module.STATUS_VERIFIED if matches else cp_module.STATUS_NOT_FOUND
            ledger.append(
                cp_module.EvidenceLedgerEntry(
                    entity=name,
                    entity_type=entity_type,
                    status=status,
                    repo_id=repo_id,
                    repo_sha=repo_sha,
                    evidence_refs=refs,
                )
            )
        return ledger

    # CP-04: the canonical ASK -> PLAN structured hand-off. WorkItem.
    # context_snapshot_json already existed in the schema (serialized in
    # every WorkItem response) but nothing ever wrote to it -- PLAN
    # inherited ASK's findings only as a formatted Markdown blob the
    # frontend built and passed back as the `goal` string, which is exactly
    # why CP-02's warning banner risked being read as part of the
    # requirement instead of as structured evidence. Persisting/loading the
    # ContextPackage here, keyed by WorkItem, is what lets PLAN (and later
    # AGENT) consume one canonical, typed object instead of re-parsing prose.
    def _persist_context_package(
        self,
        wi: WorkItem,
        *,
        requirement: str,
        ask_findings: str,
        evidence_ledger: list[cp_module.EvidenceLedgerEntry],
    ) -> cp_module.ContextPackage:
        prior = self._load_context_package(wi)
        merged_ledger = (
            cp_module.merge_evidence_ledgers(prior.evidence_ledger, evidence_ledger) if prior else evidence_ledger
        )
        try:
            from app.services.document_intelligence.service import list_work_item_attachments

            attachments = [
                {"id": a["id"], "filename": a["filename"], "content_version_id": a["content_version_id"]}
                for a in list_work_item_attachments(self.db, work_item_id=wi.id)
            ]
        except Exception:  # noqa: BLE001
            attachments = []
        pkg = cp_module.build_context_package(
            work_item_id=wi.id,
            primary_repo_id=wi.repository_id,
            repo_sha=wi.base_commit_sha or "",
            requirement=requirement,
            ask_findings=ask_findings,
            evidence_ledger=merged_ledger,
            attachments=attachments,
            resolved_mentions=(prior.resolved_mentions if prior else []),
            scope_decisions=(prior.scope_decisions if prior else {}),
        )
        wi.context_snapshot_json = json.dumps(pkg.to_dict())
        self.db.commit()
        return pkg

    def _load_context_package(self, wi: WorkItem) -> cp_module.ContextPackage | None:
        raw = (wi.context_snapshot_json or "").strip()
        if not raw or raw == "{}":
            return None
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return None
        if not data:
            return None
        return cp_module.ContextPackage.from_dict(data)

    # CP-04 deterministic guard (companion to the CMS regression: ASK's
    # ledger marks CampaignManagement.java / POST /campaigns/initiate
    # NOT_FOUND, and PLAN must not silently treat them as pre-existing
    # modify-targets). A NOT_FOUND entity is only acceptable in the plan
    # text when it's explicitly qualified as new. CP-06 promotes this
    # detection into a hard approval-time gate (plan_validator.py); the
    # scanning logic itself now lives in plan_generator.find_not_found_leaks
    # so both the generation-time warning banner and the approval-time gate
    # share one implementation instead of drifting apart.
    def _check_plan_against_not_found(self, plan_text: str, pkg: cp_module.ContextPackage) -> set[str]:
        from app.services.work_items import plan_generator

        return plan_generator.find_not_found_leaks(plan_text, pkg.not_found_entities())

    def _build_multi_repo(
        self,
        wi: WorkItem,
        goal: str,
        repository_ids: list[int],
        *,
        primary_repository_id: int | None = None,
    ) -> dict[str, Any]:
        # The authoritative primary is the WorkItem's own sticky binding when
        # it has one; repository_ids[0] is only a fallback for a WorkItem
        # that hasn't bound to a repo yet (finding A2 / CP-01).
        primary_rid = primary_repository_id or wi.repository_id or (repository_ids[0] if repository_ids else None)
        per_repo: list[dict[str, Any]] = []
        packs = []
        pi_by_repo: dict[str, Any] = {}
        for rid in repository_ids:
            binding = repo_binding(self.db, rid)
            if not binding.get("authorized"):
                continue
            built = self._build_pack(
                wi,
                goal,
                repository_id=rid,
                repository_ref=str(binding.get("repository_ref") or ""),
                base_commit_sha=str(binding.get("base_commit_sha") or ""),
            )
            pack_obj = built.get("pack_obj")
            if pack_obj:
                packs.append(pack_obj)
            per_repo.append(
                {
                    **binding,
                    "context_pack": built.get("pack"),
                    "project_intelligence": built.get("pi"),
                }
            )
            pi_by_repo[str(rid)] = built.get("pi")
        merged = (
            merge_context_packs(packs, primary_repository_id=primary_rid)
            if packs
            else self.context_engine.build(goal=goal)
        )
        primary_key = str(primary_rid) if primary_rid is not None else (str(repository_ids[0]) if repository_ids else "")
        return {
            "pack": merged.to_dict(),
            "pi": pi_by_repo.get(primary_key, pi_by_repo.get(str(repository_ids[0])) if repository_ids else {}),
            "pack_obj": merged,
            "context_by_repository": per_repo,
            "affected_repos": [b for b in per_repo],
        }

    def ask(
        self,
        *,
        question: str,
        work_item_id: int | None = None,
        project_id: int | None = None,
        repository_id: int | None = None,
        repository_ids: list[int] | None = None,
        repository_ref: str = "",
        base_commit_sha: str = "",
        actor: str = "",
        images: list[str] | None = None,
    ) -> dict[str, Any]:
        wi = self._ensure_work_item(
            work_item_id=work_item_id,
            title=f"Ask: {question[:80]}",
            project_id=project_id,
            repository_id=repository_id,
            repository_ref=repository_ref,
            base_commit_sha=base_commit_sha,
            actor=actor,
        )
        authorized = resolve_authorized_repository_ids(
            self.db,
            project_id=project_id or wi.project_id,
            repository_ids=repository_ids,
            # The WorkItem's own binding wins once set -- a WorkItem is
            # scoped to one primary repo for its whole lifetime, so a later
            # call must not let a differently-active repo in the caller's
            # UI silently rebind it (finding A2 / CP-01). Only a brand-new
            # WorkItem (wi.repository_id still unset) takes the request's
            # repository_id as its first binding.
            repository_id=wi.repository_id or repository_id,
        )
        if len(authorized) > 1:
            built = self._build_multi_repo(wi, question, authorized, primary_repository_id=wi.repository_id)
        else:
            built = self._build_pack(wi, question)
            if authorized:
                built["affected_repos"] = [repo_binding(self.db, authorized[0])]
            else:
                built["affected_repos"] = []
            built["context_by_repository"] = []
        timer = TelemetryTimer()
        from app.adapters.llm.openai_compat import (
            mentrix_llm_chat_model,
            mentrix_local_llm_configured,
            openai_compat_available,
        )
        from app.services.phases import llm_phase

        route = resolve_model_route(
            local_configured=mentrix_local_llm_configured(),
            cloud_configured=bool((__import__("os").getenv("OPENAI_API_KEY") or "").strip()),
            local_model=mentrix_llm_chat_model(),
        )
        if route.blocked and route.provider == "none":
            # Still allow offline clarifying answer via llm_phase offline path
            pass
        result = llm_phase.run_ask(
            question,
            repo_context=(built.get("pack_obj") or MentrixContextEngine().build(goal=question)).text_blob(),
            repo_id=wi.repository_id,
            db=self.db,
            images=images or None,
        )
        tel = build_telemetry(
            requested_provider="local" if mentrix_local_llm_configured() else "cloud",
            requested_model=mentrix_llm_chat_model(),
            actual_provider=route.provider if not result.get("offline") else "offline",
            actual_model=str(result.get("model") or ""),
            fallback_used=route.fallback_used,
            fallback_reason=route.fallback_reason,
            latency_ms=timer.latency_ms(),
            work_item_id=wi.id,
            operation_id="ask",
        )
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="ask",
            payload={"question": question[:500], "telemetry": tel},
            commit=True,
        )
        answer = str(result.get("answer") or "")
        pack_obj = built.get("pack_obj")
        ledger = self._build_evidence_ledger(
            answer, pack_obj, repo_id=wi.repository_id, repo_sha=wi.base_commit_sha or ""
        )
        grounding = {
            "verified": sorted(e.entity for e in ledger if e.status == cp_module.STATUS_VERIFIED),
            "unverified": sorted(e.entity for e in ledger if e.status == cp_module.STATUS_NOT_FOUND),
            "checked": True,
        }
        if grounding["unverified"]:
            warning = (
                "⚠️ **Unverified references** — not found in the retrieved repository context, "
                "so they may be invented rather than real: "
                + ", ".join(grounding["unverified"][:12])
                + ". Treat these as illustrative, not confirmed, unless independently verified.\n\n---\n\n"
            )
            answer = warning + answer
        source_lines = [
            str(getattr(it, "content", "") or "")
            for it in (getattr(pack_obj, "items", None) or [])
            if str(getattr(it, "source_type", "") or "") == "workspace_file"
        ]
        if source_lines and not any(line.split(":", 1)[0] in answer for line in source_lines if line):
            answer = answer.rstrip() + "\n\nSources:\n" + "\n".join(source_lines[:8])
        # Full (untruncated) turn, persisted separately from the truncated
        # "ask" audit event above -- this is what ask_history() replays to
        # restore the conversation across navigation/refresh/restart.
        # context_used is a compact summary of built["pi"] (the same
        # project_intelligence returned in this call's HTTP response) --
        # persisting it here is what lets the Context Used strip survive a
        # reload instead of going blank until the next fresh ask() call.
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="ask_turn",
            payload={
                "question": question,
                "answer": answer,
                "model": str(tel.get("actual_model") or tel.get("requested_model") or ""),
                "offline": bool(result.get("offline")),
                # Only a count is persisted, never the image bytes -- this
                # audit log is not an image store; images are single-turn.
                "image_count": len(images or []),
                "context_used": _context_used_summary(built.get("pi")),
                "grounding": grounding,
            },
            commit=True,
        )
        context_package = self._persist_context_package(
            wi, requirement=question, ask_findings=answer, evidence_ledger=ledger
        )
        return {
            "work_item_id": wi.id,
            "answer": answer,
            "context_pack": built["pack"],
            "context_by_repository": built.get("context_by_repository") or [],
            "affected_repos": built.get("affected_repos") or [],
            "project_intelligence": built["pi"],
            "telemetry": tel,
            "grounding": grounding,
            "result": result,
            "context_package": context_package.to_dict(),
        }

    def ask_history(self, work_item_id: int) -> list[dict[str, Any]]:
        """Ordered Ask turns for a work item -- what AskPane replays on mount
        to restore the conversation. Read-only; never mutates anything."""
        rows = (
            self.db.query(WorkItemEvent)
            .filter(
                WorkItemEvent.work_item_id == work_item_id,
                WorkItemEvent.event_type == "ask_turn",
            )
            .order_by(WorkItemEvent.id)
            .all()
        )
        turns: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(row.payload_json or "{}")
            except (TypeError, ValueError):
                payload = {}
            turn = {
                "question": str(payload.get("question") or ""),
                "answer": str(payload.get("answer") or ""),
                "model": str(payload.get("model") or ""),
                "offline": bool(payload.get("offline")),
                "image_count": int(payload.get("image_count") or 0),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            # Additive: rows persisted before context_used existed have no
            # such key -- leave it absent rather than backfilling a fake
            # summary, so the frontend can tell "unknown" from "empty".
            context_used = payload.get("context_used")
            if isinstance(context_used, dict):
                turn["context_used"] = context_used
            grounding = payload.get("grounding")
            if isinstance(grounding, dict):
                turn["grounding"] = grounding
            turns.append(turn)
        return turns

    def plan(
        self,
        *,
        goal: str,
        work_item_id: int | None = None,
        project_id: int | None = None,
        repository_id: int | None = None,
        repository_ids: list[int] | None = None,
        repository_ref: str = "",
        base_commit_sha: str = "",
        constraints: str = "",
        actor: str = "",
    ) -> dict[str, Any]:
        wi = self._ensure_work_item(
            work_item_id=work_item_id,
            title=f"Plan: {goal[:80]}",
            project_id=project_id,
            repository_id=repository_id,
            repository_ref=repository_ref,
            base_commit_sha=base_commit_sha,
            actor=actor,
        )
        # CP-04: PLAN's authoritative evidence is the ContextPackage ASK
        # persisted for this WorkItem, not whatever prose (including a
        # CP-02 warning banner) the caller's `goal` string happens to
        # contain. May be None for a WorkItem that never went through ASK.
        context_package = self._load_context_package(wi)
        store = self._store(wi.id)
        record_checkpoint(store, checkpoint_type="op_start", operation_id="plan")
        authorized = resolve_authorized_repository_ids(
            self.db,
            project_id=project_id or wi.project_id,
            repository_ids=repository_ids,
            # Same sticky-binding rule as ask() -- see comment there.
            repository_id=wi.repository_id or repository_id,
        )
        if len(authorized) > 1:
            built = self._build_multi_repo(wi, goal, authorized, primary_repository_id=wi.repository_id)
        else:
            built = self._build_pack(wi, goal)
            if authorized:
                built["affected_repos"] = [repo_binding(self.db, authorized[0])]
            else:
                built["affected_repos"] = []
            built["context_by_repository"] = []
        affected = list(built.get("affected_repos") or [])
        manifest = build_affected_repos_manifest(affected, worktree_root=str(store.root / "worktrees"))
        store.write_json("EXECUTION_MANIFEST.json", manifest)
        store.write_json("AFFECTED_REPOS.json", {"affected_repos": affected})
        from app.services.phases import llm_phase
        from app.services.work_items import plan_generator

        repo_local_path = str(repo_binding(self.db, wi.repository_id).get("local_path") or "") if wi.repository_id else ""
        architecture = plan_generator.detect_repo_architecture(repo_local_path) if repo_local_path else (
            plan_generator.RepoArchitecture(primary_language="unknown", build_system="unknown")
        )
        repo_context = (built.get("pack_obj") or MentrixContextEngine().build(goal=goal)).text_blob()
        ledger_block = context_package.evidence_ledger_prompt_block() if context_package else ""
        result = llm_phase.run_grounded_plan(
            goal,
            evidence_ledger_block=ledger_block,
            architecture_summary=f"{architecture.primary_language}/{architecture.build_system}",
            repo_context=repo_context,
            constraints=constraints,
        )
        narrative_sections = plan_generator.parse_narrative_sections(str(result.get("narrative") or ""))
        seeded = plan_generator.seed_file_impacts_from_ledger(context_package) if context_package else []
        proposed = [
            plan_generator.FileImpact.from_dict(d)
            for d in (result.get("proposed_file_impacts") or [])
            if isinstance(d, dict)
        ]
        accepted, rejected_reasons = plan_generator.validate_file_impacts(
            seeded + proposed,
            context_package=context_package or cp_module.build_context_package(
                work_item_id=wi.id, primary_repo_id=wi.repository_id, repo_sha=wi.base_commit_sha or "",
                requirement=goal, ask_findings="", evidence_ledger=[],
            ),
            repo_root=repo_local_path or ".",
            architecture=architecture,
        )
        plan_text = plan_generator.render_grounded_plan_markdown(
            goal=goal,
            context_package=context_package,
            architecture=architecture,
            accepted_impacts=accepted,
            rejected_reasons=rejected_reasons,
            narrative_sections=narrative_sections,
        )
        placeholder_hits = plan_generator.find_placeholder_violations(plan_text)
        if placeholder_hits:
            plan_text = (
                "⚠️ **Unresolved template content detected and must be replaced before approval**: "
                + ", ".join(sorted(set(placeholder_hits))) + ".\n\n---\n\n" + plan_text
            )
        if context_package:
            leaked = self._check_plan_against_not_found(plan_text, context_package)
            if leaked:
                plan_text = (
                    "⚠️ **Plan references entities ASK could not verify** — the following were marked "
                    "NOT_FOUND in the repository and must not be treated as existing targets to modify "
                    "unless explicitly justified as CREATE_NEW: " + ", ".join(sorted(leaked)) + ".\n\n---\n\n"
                    + plan_text
                )
        if len(affected) > 1:
            repo_lines = "\n".join(
                f"- {r.get('label')} (repo_id={r.get('repository_id')}, ref={r.get('repository_ref')}, "
                f"commit={(r.get('base_commit_sha') or '')[:12] or 'missing'})"
                for r in affected
            )
            plan_text = (
                f"## Affected repositories\n{repo_lines}\n\n"
                f"Each execution operation is bound to repo_id + worktree under artifacts/worktrees/.\n\n"
                f"{plan_text}"
            )
        # CP-06: canonicalize once, here, before anything hashes or persists
        # it -- plan_store.save_plan()/load_plan() round-trips the
        # repo-local copy through .strip(), so hashing an un-stripped
        # plan_text here would make _resolve_current_plan_text() (which
        # prefers that repo-local copy) compute a different hash than this
        # one on the very next validation call, falsely reporting a
        # freshly-generated, never-touched plan as STALE.
        plan_text = plan_text.strip()
        written = store.write_plan(plan_text)
        new_hash = written["plan_hash"]
        # CP-06: machine-readable contract proving the rendered plan text
        # and the accepted file impacts are in sync as of this plan_hash --
        # plan_validator.py re-checks this at approval time since the
        # filesystem/evidence state generation relied on can drift before
        # someone clicks Approve.
        store.write_json(
            "FILE_IMPACTS.json",
            {
                "work_item_id": wi.id,
                "primary_repo_id": wi.repository_id,
                "repo_sha": wi.base_commit_sha or "",
                "plan_hash": new_hash,
                "file_impacts": [i.to_dict() for i in accepted],
                "rejected_file_impacts": rejected_reasons,
            },
        )
        # CP-05: write the same grounded plan to the primary repo's real
        # .zect/plans/ so it appears in Explorer/Monaco immediately, without
        # requiring the separate manual "Save Plan" click this previously
        # depended on entirely.
        repo_plan_path = ""
        if repo_local_path:
            try:
                from app.infrastructure.allowed_paths import path_under_allowed_roots
                from app.services.coding_engine.plan_store import save_plan as _save_repo_plan

                allowed_root = str(path_under_allowed_roots(repo_local_path))
                saved = _save_repo_plan(
                    work_item_or_run=str(wi.id), title="coding", markdown=plan_text, workspace=allowed_root
                )
                repo_plan_path = str(saved.get("path") or "")
            except Exception:  # noqa: BLE001
                repo_plan_path = ""
        material_change = bool(wi.approved_plan_hash and wi.approved_plan_hash != new_hash)
        wi.plan_version = int(wi.plan_version or 0) + 1
        wi.plan_hash = new_hash
        if material_change:
            wi.approved_plan_hash = None
            wi.status = STATUS_NEEDS_HUMAN_DECISION
            append_event(
                self.db,
                work_item_id=wi.id,
                event_type="plan_reapproval_required",
                payload={"plan_hash": new_hash, "previous_approved": True},
            )
        else:
            wi.status = STATUS_PLANNED
        # Dual-write MentrixRun compatibility mirror
        run = MentrixRun(
            project_id=wi.project_id,
            mode="plan",
            goal=goal,
            status="completed",
            result_json=json.dumps({"plan": plan_text, "work_item_id": wi.id}, default=str),
            created_by=actor,
        )
        self.db.add(run)
        self.db.flush()
        wi.mentrix_run_id = run.id
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="plan_written",
            payload={
                "plan_hash": new_hash,
                "plan_version": wi.plan_version,
                "artifact_path": written["path"],
                "mentrix_run_id": run.id,
            },
        )
        self.db.commit()
        self.db.refresh(wi)
        record_checkpoint(store, checkpoint_type="completion", operation_id="plan", payload={"plan_hash": new_hash})
        return {
            "work_item_id": wi.id,
            "plan": plan_text,
            "plan_hash": new_hash,
            "plan_version": wi.plan_version,
            "status": wi.status,
            "reapproval_required": material_change,
            "artifact_path": written["path"],
            "context_pack": built["pack"],
            "context_by_repository": built.get("context_by_repository") or [],
            "affected_repos": affected,
            "execution_manifest": manifest,
            "project_intelligence": built["pi"],
            "mentrix_run_id": run.id,
            "context_package": context_package.to_dict() if context_package else None,
            "repo_plan_path": repo_plan_path,
            "architecture": architecture.to_dict(),
            "file_impacts": [i.to_dict() for i in accepted],
            "rejected_file_impacts": rejected_reasons,
            "validation": self.validate_plan(work_item_id=wi.id),
        }

    def _resolve_current_plan_text(self, wi: WorkItem, store: ArtifactStore) -> str:
        # The repo-local .zect/plans/<id>-coding.plan.md is what Explorer/
        # Monaco actually show and let the user edit -- if it exists, it is
        # the plan text about to be approved, not necessarily the internal
        # ArtifactStore mirror written at the last plan() call.
        repo_local_path = str(repo_binding(self.db, wi.repository_id).get("local_path") or "") if wi.repository_id else ""
        if repo_local_path:
            try:
                from app.infrastructure.allowed_paths import path_under_allowed_roots
                from app.services.coding_engine.plan_store import load_plan as _load_repo_plan

                allowed_root = str(path_under_allowed_roots(repo_local_path))
                loaded = _load_repo_plan(f"{wi.id}-coding", workspace=allowed_root)
                text = str(loaded.get("markdown") or "")
                if text.strip():
                    return text
            except Exception:  # noqa: BLE001
                pass
        return store.read_plan()

    def _validate_plan_impl(self, wi: WorkItem) -> tuple["plan_validator.PlanValidationResult", str]:
        from app.services.work_items import plan_generator, plan_validator
        from app.services.work_items.artifact_store import plan_hash_bytes

        store = self._store(wi.id)
        plan_text = self._resolve_current_plan_text(wi, store)
        current_hash = plan_hash_bytes(plan_text) if plan_text.strip() else ""
        sidecar = store.read_json("FILE_IMPACTS.json", default=None) or None
        repo_local_path = str(repo_binding(self.db, wi.repository_id).get("local_path") or "") if wi.repository_id else ""
        architecture = (
            plan_generator.detect_repo_architecture(repo_local_path)
            if repo_local_path
            else plan_generator.RepoArchitecture(primary_language="unknown", build_system="unknown")
        )
        context_package = self._load_context_package(wi)
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
        return result, plan_text

    def validate_plan(self, *, work_item_id: int) -> dict[str, Any]:
        wi = wi_svc.get_work_item(self.db, work_item_id)
        result, _plan_text = self._validate_plan_impl(wi)
        return result.to_dict()

    def approve_plan(self, *, work_item_id: int, actor: str = "") -> dict[str, Any]:
        wi = wi_svc.get_work_item(self.db, work_item_id)
        store = self._store(wi.id)
        plan = store.read_plan()
        if not plan.strip():
            raise HTTPException(status_code=400, detail="plan_missing")
        h = store.plan_hash()
        wi.plan_hash = h
        wi.approved_plan_hash = h
        wi.status = STATUS_PLAN_APPROVED
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="plan_approved",
            payload={"approved_plan_hash": h, "actor": actor},
        )
        self.db.commit()
        self.db.refresh(wi)
        record_checkpoint(store, checkpoint_type="completion", operation_id="approve_plan", payload={"hash": h})
        return wi_svc.serialize_work_item(wi)

    def start_agent(
        self,
        *,
        work_item_id: int,
        goal: str = "",
        workspace: str = "",
        actor: str = "",
        deterministic: bool = False,
    ) -> dict[str, Any]:
        import os
        from pathlib import Path

        wi = wi_svc.get_work_item(self.db, work_item_id)
        if wi.status not in (STATUS_PLAN_APPROVED, STATUS_EXECUTING, STATUS_NEEDS_HUMAN_DECISION):
            # Allow EXECUTING resume; require approve unless deterministic e2e helper
            if wi.approved_plan_hash != wi.plan_hash or not wi.approved_plan_hash:
                raise HTTPException(status_code=409, detail="plan_not_approved")
        store = self._store(wi.id)
        record_checkpoint(store, checkpoint_type="op_start", operation_id="agent")
        manifest = store.read_json("EXECUTION_MANIFEST.json", default={}) or {}
        from app.services.work_items.multi_repo_agent import is_multi_repo_manifest, run_multi_repo_agent

        if is_multi_repo_manifest(manifest):
            wi.status = STATUS_EXECUTING
            append_event(
                self.db,
                work_item_id=wi.id,
                event_type="agent_started",
                payload={"goal": (goal or store.read_plan()[:500] or wi.title)[:500], "actor": actor, "multi_repo": True},
            )
            self.db.commit()
            use_det = deterministic or (os.getenv("ZECT_CODING_AGENT_DETERMINISTIC_SMOKE") or "").strip() in (
                "1",
                "true",
                "yes",
            )
            agent_goal = goal or store.read_plan()[:1500] or wi.title
            return run_multi_repo_agent(
                self.db,
                wi,
                store,
                goal=agent_goal,
                actor=actor,
                deterministic=use_det,
            )

        ws = (workspace or wi.worktree_path or "").strip()
        if not ws:
            # default worktree under artifact store
            ws = str(store.root / "worktree")
            Path(ws).mkdir(parents=True, exist_ok=True)
        wi.worktree_path = ws
        wi.status = STATUS_EXECUTING
        agent_goal = goal or store.read_plan()[:1500] or wi.title
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="agent_started",
            payload={"workspace": ws, "goal": agent_goal[:500], "actor": actor},
        )
        self.db.commit()

        use_det = deterministic or (os.getenv("ZECT_CODING_AGENT_DETERMINISTIC_SMOKE") or "").strip() in (
            "1",
            "true",
            "yes",
        )
        files_written: list[str] = []
        events_tail: list[Any] = []
        run_id = ""
        engine = "mentrix_native"

        if use_det:
            from app.services.coding_engine.mentrix_agent_tools import execute_tool, resolve_workspace

            root = resolve_workspace(ws)
            # real read/edit/run/diff path (same tools Coding Agent uses)
            execute_tool("list_dir", {"path": "."}, workspace=root)
            w = execute_tool(
                "write_file",
                {"path": "mentrix_p0_agent_marker.py", "content": "# mentrix p0\nprint('ok')\n"},
                workspace=root,
            )
            r = execute_tool("read_file", {"path": "mentrix_p0_agent_marker.py"}, workspace=root)
            cmd = execute_tool("run_command", {"command": "python mentrix_p0_agent_marker.py"}, workspace=root)
            files_written = ["mentrix_p0_agent_marker.py"] if w.get("ok") else []
            events_tail = [
                {"event": "tool", "name": "write_file", "ok": w.get("ok"), "file_diff": w.get("file_diff")},
                {"event": "tool", "name": "read_file", "ok": r.get("ok")},
                {"event": "tool", "name": "run_command", "ok": cmd.get("ok"), "exit": cmd.get("exit_code")},
            ]
            run_id = f"deterministic-{wi.id}"
            record_checkpoint(
                store,
                checkpoint_type="file_change",
                operation_id="agent",
                payload={"files": files_written},
                worktree_path=ws,
                base_commit_sha=wi.base_commit_sha or "",
                current_commit_sha=wi.current_commit_sha or wi.base_commit_sha or "",
            )
            record_checkpoint(
                store,
                checkpoint_type="command_execution",
                operation_id="agent",
                payload={"command": "python mentrix_p0_agent_marker.py", "result": cmd},
            )
        else:
            from app.services.coding_engine.mentrix_native_build import run_mentrix_native_build

            native = run_mentrix_native_build(
                goal=agent_goal,
                workspace=ws,
                expected_files=["mentrix_p0_agent_marker.py"],
                project_id=wi.project_id,
                repo_id=wi.repository_id,
                work_item_id=wi.id,
            )
            files_written = list(native.get("files_written") or [])
            events_tail = list(native.get("events_tail") or [])
            run_id = str(native.get("run_id") or "")
            engine = str(native.get("engine") or "mentrix_native")
            record_checkpoint(
                store,
                checkpoint_type="file_change",
                operation_id="agent",
                payload={"files": files_written, "native": native.get("ok")},
                worktree_path=ws,
                base_commit_sha=wi.base_commit_sha or "",
                current_commit_sha=wi.current_commit_sha or "",
            )

        wi.status = STATUS_IMPLEMENTED if files_written else STATUS_EXECUTING
        wi.current_commit_sha = wi.current_commit_sha or wi.base_commit_sha or ""
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="agent_completed_slice",
            payload={"run_id": run_id, "files_written": files_written, "engine": engine},
        )
        self.db.commit()
        self.db.refresh(wi)
        return {
            "work_item_id": wi.id,
            "status": wi.status,
            "run_id": run_id,
            "files_written": files_written,
            "events_tail": events_tail,
            "engine": engine,
            "worktree_path": ws,
        }

    def continue_agent(self, *, work_item_id: int, goal: str = "", actor: str = "") -> dict[str, Any]:
        return self.start_agent(work_item_id=work_item_id, goal=goal, actor=actor)

    def cancel_agent(self, *, work_item_id: int, actor: str = "") -> dict[str, Any]:
        wi = wi_svc.transition_status(
            self.db,
            work_item_id,
            "CANCELLED",
            reason="agent_cancelled",
            actor=actor,
        )
        store = self._store(work_item_id)
        record_checkpoint(store, checkpoint_type="blocking", operation_id="cancel", payload={"actor": actor})
        return wi_svc.serialize_work_item(wi)

    def resume(self, *, work_item_id: int, actor: str = "") -> dict[str, Any]:
        wi = wi_svc.get_work_item(self.db, work_item_id)
        store = self._store(wi.id)
        state = load_execution_state(store)
        wi.worktree_path = state.get("worktree_path") or wi.worktree_path
        wi.base_commit_sha = state.get("base_commit_sha") or wi.base_commit_sha
        wi.current_commit_sha = state.get("current_commit_sha") or wi.current_commit_sha
        append_event(
            self.db,
            work_item_id=wi.id,
            event_type="resume",
            payload={"state": state, "actor": actor},
        )
        self.db.commit()
        self.db.refresh(wi)
        return {
            "work_item": wi_svc.serialize_work_item(wi),
            "execution_state": state,
            "resume_operation": state.get("resume_operation"),
        }

    def verify_and_ready_to_ship(
        self,
        *,
        work_item_id: int,
        mandatory_operation_ids: list[str],
        requirement_ids: list[str],
        acceptance_ids: list[str],
        evidence: list[dict[str, Any]],
        actor: str = "EvidenceVerifier",
    ) -> dict[str, Any]:
        wi = wi_svc.get_work_item(self.db, work_item_id)
        store = self._store(wi.id)
        wi.status = STATUS_VERIFYING
        self.db.commit()
        record_checkpoint(store, checkpoint_type="verification", operation_id="verify")
        from app.services.work_items.multi_repo_agent import collect_current_heads

        result = self.verifier.verify(
            mandatory_operation_ids=mandatory_operation_ids,
            requirement_ids=requirement_ids,
            acceptance_ids=acceptance_ids,
            evidence=evidence,
            current_heads=collect_current_heads(store),
        )
        store.write_json(
            "EVIDENCE.json",
            {"evidence": evidence, "verification": result.to_dict()},
        )
        close_loop_result: dict[str, Any] | None = None
        if result.ready_to_ship:
            wi = wi_svc.transition_status(
                self.db,
                work_item_id,
                STATUS_READY_TO_SHIP,
                reason="evidence_verified",
                allow_gate=True,
                actor=actor,
            )
            record_checkpoint(store, checkpoint_type="completion", operation_id="ready_to_ship")
            # OP-040: optional external close (dry_run by default — no live Jira/Camunda)
            try:
                from app.services.work_items.close_loop import close_external_loop

                close_loop_result = close_external_loop(
                    self.db,
                    work_item_id=wi.id,
                    dry_run=True,
                )
            except Exception as exc:  # noqa: BLE001
                close_loop_result = {"ok": False, "error": str(exc)[:300]}
        else:
            append_event(
                self.db,
                work_item_id=wi.id,
                event_type="verification_failed",
                payload=result.to_dict(),
                commit=True,
            )
            record_checkpoint(
                store,
                checkpoint_type="failure",
                operation_id="verify",
                payload=result.to_dict(),
            )
        out: dict[str, Any] = {
            "work_item": wi_svc.serialize_work_item(wi),
            "verification": result.to_dict(),
        }
        if close_loop_result is not None:
            out["close_loop"] = close_loop_result
        return out
