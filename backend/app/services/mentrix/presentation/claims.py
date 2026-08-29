"""Claim verification for Mentrix Present — UNVERIFIED must not be presented as fact."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
CONFLICTING = "CONFLICTING"
SOURCE_MISSING = "SOURCE_MISSING"

STATUSES = (VERIFIED, UNVERIFIED, CONFLICTING, SOURCE_MISSING)


def make_claim(
    claim: str,
    *,
    source: str = "",
    verification_status: str = UNVERIFIED,
    sensitivity: str = "INTERNAL",
    slide_reference: str = "",
) -> dict[str, Any]:
    status = (verification_status or UNVERIFIED).upper()
    if status not in STATUSES:
        status = UNVERIFIED
    return {
        "id": uuid4().hex[:12],
        "claim": (claim or "").strip()[:1000],
        "source": (source or "").strip()[:500],
        "verification_status": status,
        "sensitivity": (sensitivity or "INTERNAL").upper(),
        "slide_reference": (slide_reference or "").strip()[:120],
        "present_as_fact": status == VERIFIED,
    }


def extract_claims_from_text(text: str, *, sensitivity: str = "INTERNAL") -> list[dict[str, Any]]:
    """Heuristic: split sentences that look like factual claims (numbers/%/dates)."""
    import re

    claims: list[dict[str, Any]] = []
    for sent in re.split(r"(?<=[.!?])\s+", (text or "").strip()):
        s = sent.strip()
        if len(s) < 20:
            continue
        if re.search(r"\d|%|\$|Q[1-4]|FY\d{2,4}|million|billion", s, re.I):
            claims.append(
                make_claim(
                    s,
                    source="",
                    verification_status=UNVERIFIED if not s else UNVERIFIED,
                    sensitivity=sensitivity,
                )
            )
    return claims[:40]


def filter_presentable(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Only VERIFIED claims may be presented as fact; others marked for review."""
    out = []
    for c in claims:
        row = dict(c)
        if row.get("verification_status") != VERIFIED:
            row["present_as_fact"] = False
            row["speaker_note"] = f"Do not state as fact ({row.get('verification_status')})."
        else:
            row["present_as_fact"] = True
        out.append(row)
    return out


def claims_table_markdown(claims: list[dict[str, Any]]) -> str:
    lines = ["# Claim / Evidence Table", "", "| Claim | Source | Status | Slide | Present as fact |", "|---|---|---|---|---|"]
    for c in claims:
        lines.append(
            f"| {(c.get('claim') or '')[:80]} | {(c.get('source') or '—')[:40]} | "
            f"{c.get('verification_status')} | {c.get('slide_reference') or '—'} | "
            f"{'yes' if c.get('present_as_fact') else 'no'} |"
        )
    return "\n".join(lines)
