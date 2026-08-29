"""Systemic secret/PII redaction for logs and audit details (Phase 5 Stage C)."""

from __future__ import annotations

import json
import re
from typing import Any

# Common secret-bearing key names (case-insensitive)
_SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|credential|private[_-]?key|access[_-]?key)",
    re.IGNORECASE,
)

# Inline patterns often leaked into free-text logs
_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(bearer\s+)[a-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(password\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(secret\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"xox[baprs]-[a-zA-Z0-9-]{10,}"),
]


def redact_mapping(data: dict[str, Any] | None) -> dict[str, Any]:
    """Redact sensitive values in a dict (shallow + one nested level)."""
    if not data:
        return {}
    out: dict[str, Any] = {}
    for k, v in data.items():
        if _SENSITIVE_KEY_RE.search(str(k)):
            out[k] = "***"
        elif isinstance(v, dict):
            out[k] = redact_mapping(v)
        elif isinstance(v, str):
            out[k] = redact_text(v)
        else:
            out[k] = v
    return out


def redact_text(text: str | None) -> str:
    if not text:
        return ""
    out = str(text)
    for pat in _PATTERNS:
        out = pat.sub(lambda m: (m.group(1) + "***") if m.lastindex else "***", out)
    return out


def redact_secrets(value: Any) -> Any:
    """Redact secrets in str / dict / JSON-looking strings."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, (list, tuple)):
        return [redact_secrets(v) for v in value]
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            return json.dumps(redact_secrets(parsed), default=str)
        except Exception:
            pass
    return redact_text(value)


def contains_raw_secret(value: Any) -> bool:
    """True when free text / nested values appear to contain raw secrets (Phase 10)."""
    if value is None:
        return False
    if isinstance(value, dict):
        for k, v in value.items():
            if _SENSITIVE_KEY_RE.search(str(k)) and v not in (None, "", "***"):
                return True
            if contains_raw_secret(v):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(contains_raw_secret(v) for v in value)
    text = str(value)
    if not text.strip():
        return False
    for pat in _PATTERNS:
        if pat.search(text):
            return True
    return False
