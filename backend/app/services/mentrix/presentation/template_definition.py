"""Canonical ZECT TemplateDefinition — provider UUIDs are adapter-only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.mentrix.presentation import template_registry as tmpl

PARSER_VERSION = "1"

SCOPE_ZINNIA = "ZINNIA"
SCOPE_ORG = "ORG"
SCOPE_USER = "USER"


def _def_dir() -> Path:
    d = tmpl._root() / "definitions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def definition_path(zect_id: str) -> Path:
    safe = tmpl._SAFE.sub("_", (zect_id or "").strip())[:80] or "unknown"
    return _def_dir() / f"{safe}.json"


def public_definition(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    bindings = out.get("provider_bindings")
    if isinstance(bindings, dict):
        out["provider_bindings"] = {"presenton": bool(str(bindings.get("presenton") or "").strip())}
    else:
        out["provider_bindings"] = {}
    out.pop("provider_template_id", None)
    out["provider_uuid_hidden"] = True
    return out


def load_definition(zect_id: str) -> dict[str, Any] | None:
    path = definition_path(zect_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def save_definition(row: dict[str, Any]) -> dict[str, Any]:
    zid = str(row.get("id") or "").strip()
    if not zid:
        raise ValueError("template_id_required")
    path = definition_path(zid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, indent=2), encoding="utf-8")
    return row


def native_ready(zect_id: str) -> bool:
    row = load_definition(tmpl.canonical_id(zect_id) or zect_id)
    return bool(row and row.get("ready") is True)


def list_ready_ids() -> list[str]:
    out: list[str] = []
    root = _def_dir()
    for path in sorted(root.glob("*.json")):
        row = load_definition(path.stem)
        if row and row.get("ready") is True:
            out.append(str(row.get("id") or path.stem))
    return out
