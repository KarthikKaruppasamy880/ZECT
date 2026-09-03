"""CP-04 -- the canonical ASK -> PLAN (-> AGENT) structured context package.

This is the one structured object ASK, PLAN, and later AGENT all read and
write, replacing the "hope the prose survives" transfer where PLAN inherited
ASK's findings only as a formatted Markdown blob (built client-side in
buildAskSeedMarkdown() and passed back as the `goal` string) -- including,
after CP-02, the "Unverified references" warning banner baked directly into
that same prose. Nothing separated "this is verified" from "this is not" in
a way a later phase could act on deterministically; it was all just text.

Do not add a second context store/engine here. This module defines the
canonical PACKAGE SHAPE and a thin build/persist/load API around the
existing ContextPack/ProvenanceItem machinery (context_engine.py) and the
existing WorkItem.context_snapshot_json column (already part of the schema,
previously write-only-never-read). ASK and PLAN both already share
developer_service.py's _build_pack()/_build_multi_repo() for retrieval --
this module packages THEIR output plus the Evidence Ledger into one
JSON-serializable, budget-aware object, so a later phase (CP-05's plan
generator, CP-07's write guard) has one canonical interface to consume
instead of inventing its own.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Evidence Ledger entity types and statuses -- the mandate's exact vocabulary.
ENTITY_TYPES = ("file", "class", "api_route", "symbol")
STATUS_VERIFIED = "VERIFIED"
STATUS_NOT_FOUND = "NOT_FOUND"
STATUS_PROPOSED = "PROPOSED"
LEDGER_STATUSES = (STATUS_VERIFIED, STATUS_NOT_FOUND, STATUS_PROPOSED)

# How many chars of an already-computed prose finding to keep in the
# canonical package -- enough for PLAN to read the gist, far short of
# "the complete ASK transcript" the mandate explicitly forbids copying.
_ASK_FINDINGS_SUMMARY_CHARS = 3000


@dataclass
class EvidenceLedgerEntry:
    """One repository claim, typed and provable -- not a sentence in a
    warning banner. `evidence_refs` are ProvenanceItem.source_id values that
    back a VERIFIED entry (e.g. "calc.py" or "calc.py:12"); always empty for
    NOT_FOUND, since there is nothing to point at."""

    entity: str
    entity_type: str  # one of ENTITY_TYPES
    status: str  # one of LEDGER_STATUSES
    repo_id: int | None = None
    repo_sha: str = ""
    evidence_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "EvidenceLedgerEntry":
        return EvidenceLedgerEntry(
            entity=str(d.get("entity") or ""),
            entity_type=str(d.get("entity_type") or "symbol"),
            status=str(d.get("status") or STATUS_NOT_FOUND),
            repo_id=d.get("repo_id"),
            repo_sha=str(d.get("repo_sha") or ""),
            evidence_refs=list(d.get("evidence_refs") or []),
        )


@dataclass
class ContextPackage:
    """The canonical structured hand-off. Every field here is either a
    compact reference/summary or a bounded, deduplicated set -- the full
    ASK conversation, full document text, full repo tree, etc. stay in
    WorkItem/ArtifactStore/Mission storage where they were already durable;
    this object is what gets handed to a model prompt, not a second copy of
    everything ASK ever saw."""

    work_item_id: int | None
    primary_repo_id: int | None
    repo_sha: str
    requirement: str
    ask_findings_summary: str
    evidence_ledger: list[EvidenceLedgerEntry] = field(default_factory=list)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    resolved_mentions: list[dict[str, Any]] = field(default_factory=list)
    scope_decisions: dict[str, Any] = field(default_factory=dict)
    mission_memory_ref: str = ""
    token_budget: int = 8000

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_item_id": self.work_item_id,
            "primary_repo_id": self.primary_repo_id,
            "repo_sha": self.repo_sha,
            "requirement": self.requirement,
            "ask_findings_summary": self.ask_findings_summary,
            "evidence_ledger": [e.to_dict() for e in self.evidence_ledger],
            "attachments": self.attachments,
            "resolved_mentions": self.resolved_mentions,
            "scope_decisions": self.scope_decisions,
            "mission_memory_ref": self.mission_memory_ref,
            "token_budget": self.token_budget,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ContextPackage":
        return ContextPackage(
            work_item_id=d.get("work_item_id"),
            primary_repo_id=d.get("primary_repo_id"),
            repo_sha=str(d.get("repo_sha") or ""),
            requirement=str(d.get("requirement") or ""),
            ask_findings_summary=str(d.get("ask_findings_summary") or ""),
            evidence_ledger=[EvidenceLedgerEntry.from_dict(e) for e in (d.get("evidence_ledger") or [])],
            attachments=list(d.get("attachments") or []),
            resolved_mentions=list(d.get("resolved_mentions") or []),
            scope_decisions=dict(d.get("scope_decisions") or {}),
            mission_memory_ref=str(d.get("mission_memory_ref") or ""),
            token_budget=int(d.get("token_budget") or 8000),
        )

    def verified_entities(self) -> set[str]:
        return {e.entity for e in self.evidence_ledger if e.status == STATUS_VERIFIED}

    def not_found_entities(self) -> set[str]:
        return {e.entity for e in self.evidence_ledger if e.status == STATUS_NOT_FOUND}

    def proposed_entities(self) -> set[str]:
        return {e.entity for e in self.evidence_ledger if e.status == STATUS_PROPOSED}

    def evidence_ledger_prompt_block(self) -> str:
        """A compact, explicit block for the PLAN prompt -- the structured
        replacement for "hope the model reads the warning banner in the
        prose and understands it." Deliberately terse: one line per entity,
        not a paragraph."""
        if not self.evidence_ledger:
            return ""
        lines = ["## Evidence Ledger (from ASK -- authoritative, do not contradict)"]
        for e in sorted(self.evidence_ledger, key=lambda x: (x.status, x.entity)):
            if e.status == STATUS_VERIFIED:
                refs = ", ".join(e.evidence_refs[:3]) or "unspecified"
                lines.append(f"- VERIFIED {e.entity_type}: {e.entity} (evidence: {refs})")
            elif e.status == STATUS_NOT_FOUND:
                lines.append(
                    f"- NOT_FOUND {e.entity_type}: {e.entity} -- do not treat as an existing file/route/class "
                    "to modify; it may only be proposed as new, explicitly labeled CREATE_NEW."
                )
            else:
                lines.append(f"- PROPOSED {e.entity_type}: {e.entity} -- new, not yet existing.")
        return "\n".join(lines)


def merge_evidence_ledgers(
    existing: list[EvidenceLedgerEntry], new: list[EvidenceLedgerEntry]
) -> list[EvidenceLedgerEntry]:
    """Dedupe by (entity, entity_type); a later, more specific status wins
    over an earlier one for the same entity (e.g. a later VERIFIED
    supersedes an earlier NOT_FOUND once real evidence turns up), but never
    the reverse -- once VERIFIED, a later pass finding no fresh evidence
    must not silently downgrade it back to NOT_FOUND."""
    by_key: dict[tuple[str, str], EvidenceLedgerEntry] = {(e.entity, e.entity_type): e for e in existing}
    for entry in new:
        key = (entry.entity, entry.entity_type)
        prior = by_key.get(key)
        if prior is None or prior.status != STATUS_VERIFIED:
            by_key[key] = entry
    return list(by_key.values())


def build_context_package(
    *,
    work_item_id: int | None,
    primary_repo_id: int | None,
    repo_sha: str,
    requirement: str,
    ask_findings: str,
    evidence_ledger: list[EvidenceLedgerEntry],
    attachments: list[dict[str, Any]] | None = None,
    resolved_mentions: list[dict[str, Any]] | None = None,
    scope_decisions: dict[str, Any] | None = None,
    mission_memory_ref: str = "",
    token_budget: int = 8000,
) -> ContextPackage:
    return ContextPackage(
        work_item_id=work_item_id,
        primary_repo_id=primary_repo_id,
        repo_sha=repo_sha,
        requirement=requirement[:2000],
        ask_findings_summary=(ask_findings or "")[:_ASK_FINDINGS_SUMMARY_CHARS],
        evidence_ledger=evidence_ledger,
        attachments=attachments or [],
        resolved_mentions=resolved_mentions or [],
        scope_decisions=scope_decisions or {},
        mission_memory_ref=mission_memory_ref,
        token_budget=token_budget,
    )
