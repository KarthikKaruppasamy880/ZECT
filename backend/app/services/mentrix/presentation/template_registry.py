"""User/org presentation template registry (ZECT-branded; provider ids stay hidden)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.infrastructure.allowed_paths import path_under_allowed_roots

_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def _root() -> Path:
    import os

    env = (os.environ.get("ZECT_PRESENT_TEMPLATE_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path(__file__).resolve().parents[5] / ".zect" / "present-templates").resolve()


def _user_dir(user_id: str | int) -> Path:
    d = _root() / f"user-{user_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _meta_path(user_id: str | int) -> Path:
    return _user_dir(user_id) / "registry.json"


def _load(user_id: str | int) -> list[dict[str, Any]]:
    p = _meta_path(user_id)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return list(data.get("templates") or [])
    except Exception:
        return []


def _save(user_id: str | int, templates: list[dict[str, Any]]) -> None:
    p = _meta_path(user_id)
    p.write_text(json.dumps({"templates": templates}, indent=2), encoding="utf-8")


def list_builtin_zinnia() -> list[dict[str, Any]]:
    return [
        {
            "id": "zinnia-exec",
            "name": "Zinnia — Executive brief",
            "scope": "ORG",
            "kind": "zinnia",
            "preview": "Status snapshot, decisions, owners, next 7 days.",
        },
        {
            "id": "zinnia-delivery",
            "name": "Zinnia — Delivery status",
            "scope": "ORG",
            "kind": "zinnia",
            "preview": "Workstream health, milestones, blockers, leadership ask.",
        },
        {
            "id": "zinnia-risk",
            "name": "Zinnia — Risk & next actions",
            "scope": "ORG",
            "kind": "zinnia",
            "preview": "Top risks, mitigations, owners, timeline impact.",
        },
    ]


def list_org_masters() -> list[dict[str, Any]]:
    """Org-scoped masters — distinct from Zinnia prompt presets (no silent clone)."""
    import os

    master = (os.getenv("ZINNIA_PRESENTON_TEMPLATE_ID") or "").strip()
    rows = [
        {
            "id": "org-standard",
            "name": "Org — Standard brief",
            "scope": "ORG",
            "kind": "org_master",
            "preview": "Organization-standard deck shell (maps via Presenton when configured).",
            "presenton_template_id": master or None,
        },
        {
            "id": "org-delivery",
            "name": "Org — Delivery review",
            "scope": "ORG",
            "kind": "org_master",
            "preview": "Delivery health for leadership forums.",
            "presenton_template_id": master or None,
        },
    ]
    return rows


def list_templates(user_id: str | int) -> dict[str, Any]:
    mine = _load(user_id)
    return {
        "ok": True,
        "zinnia": list_builtin_zinnia(),
        "organization": list_org_masters(),
        "my_templates": mine,
        "template_root": str(_root()),
    }


async def register_user_pptx(user_id: str | int, upload: UploadFile, *, name: str | None = None) -> dict[str, Any]:
    filename = (upload.filename or "template.pptx").strip()
    if not filename.lower().endswith(".pptx"):
        return {"ok": False, "error": "pptx_required"}
    raw = await upload.read()
    if not raw or len(raw) > 40 * 1024 * 1024:
        return {"ok": False, "error": "invalid_or_too_large"}
    tid = f"user-{uuid.uuid4().hex[:12]}"
    safe_name = _SAFE.sub("_", (name or Path(filename).stem)[:80]) or "template"
    dest = _user_dir(user_id) / f"{tid}.pptx"
    dest.write_bytes(raw)
    if not path_under_allowed_roots(str(dest)) and not str(dest).startswith(str(_root())):
        # Allow under dedicated template root even if outside default Desktop roots
        pass
    entry = {
        "id": tid,
        "name": safe_name,
        "scope": "USER_PRIVATE",
        "kind": "user_pptx",
        "filename": filename,
        "path": str(dest),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "preview": f"Uploaded PPTX template ({len(raw)} bytes).",
    }
    templates = _load(user_id)
    templates.insert(0, entry)
    _save(user_id, templates)
    return {"ok": True, "template": entry}


def get_template(user_id: str | int, template_id: str) -> dict[str, Any] | None:
    for t in list_builtin_zinnia():
        if t["id"] == template_id:
            return t
    for t in _load(user_id):
        if t.get("id") == template_id:
            return t
    return None


def preview_template(user_id: str | int, template_id: str) -> dict[str, Any]:
    t = get_template(user_id, template_id)
    if not t:
        return {"ok": False, "error": "not_found"}
    return {
        "ok": True,
        "template_id": t["id"],
        "name": t.get("name"),
        "scope": t.get("scope"),
        "kind": t.get("kind"),
        "preview": t.get("preview") or t.get("name"),
        "provider_uuid_hidden": True,
    }
