"""Mentrix presentation pipeline — Flow A/B helpers (Presenton remains generator)."""

from __future__ import annotations

from typing import Any

from app.services.mentrix.presentation.audience import get_audience, list_audiences, prompt_adapter
from app.services.mentrix.presentation.claims import (
    claims_table_markdown,
    extract_claims_from_text,
    filter_presentable,
    make_claim,
)
from app.services.mentrix.presentation.sensitivity import can_generate, classify_deck_material


def analyze_existing_deck(
    *,
    slides: list[dict[str, Any]] | None = None,
    notes_blob: str = "",
    audience_id: str = "general",
    sensitivity_hint: str | None = None,
) -> dict[str, Any]:
    """Flow A: parse context → classify → audience → claims → improved notes guidance."""
    slides = slides or []
    text_parts = [notes_blob]
    for s in slides:
        text_parts.append(str(s.get("notes") or ""))
        text_parts.append(str(s.get("text") or ""))
    blob = "\n".join(p for p in text_parts if p).strip()
    sens = classify_deck_material(blob, hint=sensitivity_hint)
    audience = get_audience(audience_id)
    claims = filter_presentable(extract_claims_from_text(blob, sensitivity=sens["sensitivity"]))
    improved_notes = []
    for i, s in enumerate(slides):
        raw = str(s.get("notes") or s.get("text") or "").strip()
        note = raw or f"Slide {i + 1}: cover key point for {audience['label']} audience."
        if sens["sensitivity"] in ("CONFIDENTIAL", "RESTRICTED"):
            note = f"[{sens['sensitivity']}] {note}"
        improved_notes.append({"index": s.get("index", i), "notes": note[:2000]})
    ok, reason = can_generate(sens)
    return {
        "ok": ok,
        "reason": reason,
        "flow": "existing_deck",
        "sensitivity": sens,
        "audience": audience,
        "claims": claims,
        "claims_markdown": claims_table_markdown(claims),
        "improved_notes": improved_notes,
        "rehearse_ready": ok and bool(slides or notes_blob),
        "zoom_share_required": True,
    }


def prepare_prompt_deck(
    *,
    prompt: str,
    audience_id: str = "general",
    sensitivity_hint: str | None = None,
    documents: list[str] | None = None,
) -> dict[str, Any]:
    """Flow B: prompt/docs → classify → audience → outline → claims → approval gate before Presenton."""
    docs = documents or []
    blob = "\n\n".join([prompt or "", *docs])
    sens = classify_deck_material(blob, hint=sensitivity_hint)
    audience = get_audience(audience_id)
    adapted = prompt_adapter(audience_id, prompt or "Delivery status brief")
    claims = filter_presentable(extract_claims_from_text(blob, sensitivity=sens["sensitivity"]))
    # Mark numeric claims SOURCE_MISSING until user verifies
    for c in claims:
        if not c.get("source"):
            c["verification_status"] = "SOURCE_MISSING"
            c["present_as_fact"] = False
    outline = [
        f"Title for {audience['label']}",
        "Context / status",
        "Key points",
        "Risks & decisions",
        "Next actions",
    ]
    ok, reason = can_generate(sens)
    return {
        "ok": ok,
        "reason": reason,
        "flow": "prompt_to_deck",
        "sensitivity": sens,
        "audience": audience,
        "adapted_prompt": adapted,
        "outline": outline,
        "claims": claims,
        "claims_markdown": claims_table_markdown(claims),
        "requires_user_approval": True,
        "n_slides_hint": audience.get("slide_count_hint") or 6,
        "presenton_ready": ok,
    }


def verify_claim(claim_id: str, claims: list[dict[str, Any]], *, source: str, status: str = "VERIFIED") -> list[dict[str, Any]]:
    out = []
    for c in claims:
        row = dict(c)
        if row.get("id") == claim_id:
            row["source"] = source
            row["verification_status"] = status
            row["present_as_fact"] = status == "VERIFIED"
        out.append(row)
    return filter_presentable(out)


__all__ = [
    "analyze_existing_deck",
    "prepare_prompt_deck",
    "verify_claim",
    "list_audiences",
    "make_claim",
]
