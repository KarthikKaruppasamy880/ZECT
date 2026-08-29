"""Phase 4 Stage C — deterministic checks → ReviewFinding-shaped dicts.

Secrets / TODO heuristics + Rules Engine matches. Lint stderr parsing deferred
until a structured parser exists (Upgrade.md Stage C residual).
"""

from __future__ import annotations

import re
from typing import Any

# Shared with Mentrix Ultra Review offline fallback
HARDCODED_CREDENTIAL_RE = re.compile(
    r"(?:api[_-]?key|secret|password|credential|token)\s*[:=]\s*['\"]\S",
    re.IGNORECASE,
)
INCOMPLETE_MARKER_RE = re.compile(r"\bTODO\b|\bFIXME\b|\.\.\.\s*$|NotImplementedError", re.MULTILINE)

# Extra high-confidence secret shapes (from transfer scanner, narrowed)
_EXTRA_SECRET_RES = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "Possible AWS access key id"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "Possible GitHub personal access token"),
    (re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"), "Private key material in source"),
]


def _lang_from_path(path: str) -> str:
    lower = (path or "").lower()
    if lower.endswith((".py",)):
        return "python"
    if lower.endswith((".ts", ".tsx")):
        return "typescript"
    if lower.endswith((".js", ".jsx")):
        return "javascript"
    return "text"


def _scan_text(code: str, *, file_path: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lines = code.splitlines()

    def add(title: str, severity: str, category: str, line: int | None, message: str, suggestion: str):
        findings.append(
            {
                "title": title,
                "severity": severity,
                "category": category,
                "file": file_path,
                "file_path": file_path,
                "line": line,
                "start_line": line,
                "description": message,
                "explanation": message,
                "suggestion": suggestion,
                "suggested_fix": suggestion,
                "source": "deterministic",
                "confidence": 0.95,
            }
        )

    for i, line in enumerate(lines, start=1):
        if HARDCODED_CREDENTIAL_RE.search(line):
            add(
                "Possible hardcoded credential",
                "critical",
                "security",
                i,
                f"Credential-like assignment on line {i}",
                "Use a secrets manager; never hardcode credentials.",
            )
        for rx, title in _EXTRA_SECRET_RES:
            if rx.search(line):
                add(title, "critical", "security", i, f"{title} on line {i}", "Rotate and remove from source.")
        if INCOMPLETE_MARKER_RE.search(line):
            add(
                "Incomplete implementation marker",
                "high",
                "maintainability",
                i,
                f"TODO/FIXME/NotImplemented on line {i}",
                "Complete implementation before merge.",
            )
    return findings


def _scan_patch(filename: str, patch: str) -> list[dict[str, Any]]:
    """Scan added lines in a unified diff patch (lines starting with '+')."""
    if not patch:
        return []
    # Reconstruct approximate new-file content from '+' lines for regex scan
    added: list[tuple[int, str]] = []
    new_line = 0
    for raw in patch.splitlines():
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            new_line = int(m.group(1)) - 1 if m else new_line
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            new_line += 1
            added.append((new_line, raw[1:]))
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        elif raw.startswith("\\"):
            continue
        else:
            # context line
            if raw.startswith(" "):
                new_line += 1
    text = "\n".join(t for _, t in added)
    # Prefer line numbers from added map when scanning whole text would lose them
    findings: list[dict[str, Any]] = []
    for line_no, content in added:
        mini = _scan_text(content, file_path=filename)
        for f in mini:
            f["line"] = line_no
            f["start_line"] = line_no
            findings.append(f)
    # Also run whole-text for multiline private key blocks
    if "-----BEGIN" in text:
        findings.extend(_scan_text(text, file_path=filename))
    # Dedupe identical title+line
    seen: set[tuple] = set()
    out: list[dict[str, Any]] = []
    for f in findings:
        key = (f.get("title"), f.get("line"), f.get("file"))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def _rules_findings(code: str, language: str, file_path: str, db: Any) -> list[dict[str, Any]]:
    if db is None or not code.strip():
        return []
    try:
        from app.services.build_intel.file_ops import check_rule_violations

        hits = check_rule_violations(db, code, language)
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for h in hits or []:
        out.append(
            {
                "title": h.get("rule_name") or "Rules Engine match",
                "severity": (h.get("severity") or "medium").lower(),
                "category": "rules",
                "file": file_path,
                "file_path": file_path,
                "line": None,
                "description": h.get("message") or "",
                "explanation": h.get("message") or "",
                "suggestion": f"Address rule action: {h.get('action') or 'review'}",
                "suggested_fix": f"Address rule action: {h.get('action') or 'review'}",
                "source": "deterministic",
                "confidence": 0.95,
            }
        )
    return out


def collect_deterministic_findings(
    *,
    files: list[dict[str, Any]] | None = None,
    code: str | None = None,
    language: str = "unknown",
    db: Any = None,
    file_path: str = "snippet",
) -> list[dict[str, Any]]:
    """Return legacy finding dicts with source=deterministic for pipeline merge."""
    findings: list[dict[str, Any]] = []

    if files:
        for f in files:
            name = f.get("filename") or f.get("file") or "unknown"
            patch = f.get("patch") or ""
            findings.extend(_scan_patch(name, patch))
            # Rules against added lines only
            added_body = "\n".join(
                ln[1:] for ln in patch.splitlines() if ln.startswith("+") and not ln.startswith("+++")
            )
            findings.extend(_rules_findings(added_body, _lang_from_path(name), name, db))
    elif code is not None:
        findings.extend(_scan_text(code, file_path=file_path))
        findings.extend(_rules_findings(code, language or "text", file_path, db))

    return findings
