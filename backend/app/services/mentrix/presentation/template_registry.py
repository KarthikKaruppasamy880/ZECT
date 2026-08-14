"""User/org presentation template registry (ZECT-branded; provider ids stay hidden).

Canonical ZECT ids (e.g. zinnia-executive-v1) map to provider templates via this
registry — not via a normal-user env var. Env may seed the registry once for admin
bootstrap; after that the mapping file is the source of truth.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.infrastructure.allowed_paths import path_under_allowed_roots

_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")

# Presenton built-ins are never a Zinnia/org master PASS.
FALLBACK_PROVIDER_IDS = frozenset({"modern", "general", "standard", "swift", ""})

LIFECYCLE_STARTING = "STARTING"
LIFECYCLE_READY = "READY"
LIFECYCLE_TEMPLATE_NOT_READY = "TEMPLATE_NOT_READY"
LIFECYCLE_PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
LIFECYCLE_GENERATION_FAILED = "GENERATION_FAILED"

_CANONICAL_ZINNIA: list[dict[str, Any]] = [
    {
        "id": "zinnia-executive-v1",
        "aliases": ("zinnia-exec", "zinnia-executive"),
        "name": "Zinnia — Executive brief",
        "scope": "ORG",
        "kind": "zinnia",
        "preview": "Status snapshot, decisions, owners, next 7 days.",
    },
    {
        "id": "zinnia-delivery-v1",
        "aliases": ("zinnia-delivery",),
        "name": "Zinnia — Delivery status",
        "scope": "ORG",
        "kind": "zinnia",
        "preview": "Workstream health, milestones, blockers, leadership ask.",
    },
    {
        "id": "zinnia-risk-v1",
        "aliases": ("zinnia-risk",),
        "name": "Zinnia — Risk & next actions",
        "scope": "ORG",
        "kind": "zinnia",
        "preview": "Top risks, mitigations, owners, timeline impact.",
    },
]

_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _row in _CANONICAL_ZINNIA:
    _ALIAS_TO_CANONICAL[str(_row["id"])] = str(_row["id"])
    for _alias in _row.get("aliases") or ():
        _ALIAS_TO_CANONICAL[str(_alias)] = str(_row["id"])


def _root() -> Path:
    env = (os.environ.get("ZECT_PRESENT_TEMPLATE_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path(__file__).resolve().parents[5] / ".zect" / "present-templates").resolve()


def _user_dir(user_id: str | int) -> Path:
    d = _root() / f"user-{user_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _org_dir() -> Path:
    d = _root() / "org"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _meta_path(user_id: str | int) -> Path:
    return _user_dir(user_id) / "registry.json"


def _org_meta_path() -> Path:
    return _org_dir() / "registry.json"


def _mapping_path() -> Path:
    return _root() / "canonical-mapping.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_list(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("templates") or [])
    except Exception:
        return []


def _save_list(path: Path, templates: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"templates": templates}, indent=2), encoding="utf-8")


def canonical_id(choice: str | None) -> str:
    raw = (choice or "").strip()
    if not raw:
        return ""
    return _ALIAS_TO_CANONICAL.get(raw, raw)


def is_verified_provider_id(provider_id: str | None) -> bool:
    tid = (provider_id or "").strip()
    return bool(tid) and tid not in FALLBACK_PROVIDER_IDS


def load_mapping() -> dict[str, Any]:
    p = _mapping_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            rows = data.get("mappings") if "mappings" in data else data
            return dict(rows) if isinstance(rows, dict) else {}
    except Exception:
        return {}
    return {}


def save_mapping(mapping: dict[str, Any]) -> None:
    p = _mapping_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"mappings": mapping}, indent=2), encoding="utf-8")


def seed_admin_mapping_from_env() -> dict[str, Any] | None:
    """Copy env master into the registry once for zinnia-executive-v1 only.

    Normal users do not read the env var. Delivery/risk stay unmapped until
    explicitly registered — one env id is not a PASS for every Zinnia card.
    """
    env_id = (os.getenv("ZINNIA_PRESENTON_TEMPLATE_ID") or "").strip()
    if not is_verified_provider_id(env_id):
        return None
    mapping = load_mapping()
    key = "zinnia-executive-v1"
    existing = mapping.get(key) if isinstance(mapping.get(key), dict) else {}
    if is_verified_provider_id(str((existing or {}).get("provider_template_id") or "")):
        return existing
    row = {
        "provider_template_id": env_id,
        "source": "registry",
        "seeded_from": "ZINNIA_PRESENTON_TEMPLATE_ID",
        "ready": True,
        "registered_at": _now(),
    }
    mapping[key] = row
    save_mapping(mapping)
    return row


def register_provider_mapping(
    zect_id: str,
    provider_template_id: str,
    *,
    actor: str = "",
    source: str = "admin",
) -> dict[str, Any]:
    zect = canonical_id(zect_id) or (zect_id or "").strip()
    pid = (provider_template_id or "").strip()
    if not zect:
        return {"ok": False, "error": "zect_id_required"}
    if not is_verified_provider_id(pid):
        return {"ok": False, "error": "provider_id_not_a_master", "detail": pid or "empty"}
    mapping = load_mapping()
    row = {
        "provider_template_id": pid,
        "source": "registry",
        "registered_by": (actor or "")[:120],
        "register_source": source,
        "ready": True,
        "registered_at": _now(),
    }
    mapping[zect] = row
    save_mapping(mapping)
    return {"ok": True, "zect_id": zect, "mapping": row}


def get_provider_mapping(zect_id: str | None) -> dict[str, Any] | None:
    seed_admin_mapping_from_env()
    key = canonical_id(zect_id) or (zect_id or "").strip()
    if not key:
        return None
    mapping = load_mapping()
    row = mapping.get(key)
    return row if isinstance(row, dict) else None


def maybe_bind_from_provider_templates(templates: list[dict[str, Any]]) -> list[str]:
    """Bind canonical ZECT ids when Presenton lists an exact id/name match. Never fabricate."""
    bound: list[str] = []
    mapping = load_mapping()
    index: dict[str, str] = {}
    for item in templates or []:
        if not isinstance(item, dict):
            continue
        tid = str(item.get("id") or "").strip()
        name = str(item.get("name") or "").strip().lower().replace(" ", "-")
        if not is_verified_provider_id(tid):
            continue
        index[tid.lower()] = tid
        if name:
            index[name] = tid
    for row in _CANONICAL_ZINNIA:
        zid = str(row["id"])
        existing = mapping.get(zid) if isinstance(mapping.get(zid), dict) else {}
        if is_verified_provider_id(str((existing or {}).get("provider_template_id") or "")):
            continue
        candidates = [zid, *list(row.get("aliases") or ())]
        hit = ""
        for c in candidates:
            hit = index.get(c.lower()) or ""
            if hit:
                break
        if not hit:
            continue
        mapping[zid] = {
            "provider_template_id": hit,
            "source": "registry",
            "register_source": "presenton_exact_match",
            "ready": True,
            "registered_at": _now(),
        }
        bound.append(zid)
    if bound:
        save_mapping(mapping)
    return bound


def list_builtin_zinnia() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in _CANONICAL_ZINNIA:
        mapped = get_provider_mapping(str(row["id"]))
        pid = str((mapped or {}).get("provider_template_id") or "")
        from app.services.mentrix.presentation.template_definition import native_ready as _native_ready

        native = _native_ready(str(row["id"]))
        out.append(
            {
                "id": row["id"],
                "name": row["name"],
                "scope": row["scope"],
                "kind": row["kind"],
                "preview": row["preview"],
                "aliases": list(row.get("aliases") or ()),
                "mapped": is_verified_provider_id(pid) or native,
                "native_ready": native,
                "provider_uuid_hidden": True,
            }
        )
    return out


def _load_org() -> list[dict[str, Any]]:
    return _load_list(_org_meta_path())


def _public_row(
    row: dict[str, Any],
    *,
    default_scope: str = "USER_PRIVATE",
    default_kind: str = "user_pptx",
) -> dict[str, Any]:
    entry = dict(row)
    pid = str(entry.get("presenton_template_id") or "")
    entry.pop("presenton_template_id", None)
    entry.pop("path", None)
    entry.setdefault("scope", default_scope)
    entry.setdefault("kind", default_kind)
    from app.services.mentrix.presentation.template_definition import native_ready as _native_ready

    native = _native_ready(str(entry.get("id") or ""))
    entry["native_ready"] = native
    entry["mapped"] = bool(entry.get("mapped")) or is_verified_provider_id(pid) or native
    entry["provider_uuid_hidden"] = True
    return entry


def list_org_masters() -> list[dict[str, Any]]:
    """Org-scoped masters — distinct from Zinnia prompt presets (no silent clone)."""
    rows = [
        {
            "id": "org-standard",
            "name": "Org — Standard brief",
            "scope": "ORG",
            "kind": "org_master",
            "preview": "Organization-standard deck shell (maps via registry when configured).",
        },
        {
            "id": "org-delivery",
            "name": "Org — Delivery review",
            "scope": "ORG",
            "kind": "org_master",
            "preview": "Delivery health for leadership forums.",
        },
    ]
    for row in rows:
        mapped = get_provider_mapping(str(row["id"]))
        pid = str((mapped or {}).get("provider_template_id") or "")
        from app.services.mentrix.presentation.template_definition import native_ready as _native_ready

        native = _native_ready(str(row["id"]))
        row["mapped"] = is_verified_provider_id(pid) or native
        row["native_ready"] = native
        row["provider_uuid_hidden"] = True
    uploaded = []
    for t in _load_org():
        uploaded.append(_public_row(t, default_scope="ORG", default_kind="org_pptx"))
    return rows + uploaded


def list_templates(user_id: str | int) -> dict[str, Any]:
    mine = [_public_row(t) for t in _load_list(_meta_path(user_id))]
    zinnia = list_builtin_zinnia()
    organization = list_org_masters()
    lifecycle = provider_lifecycle(
        configured=None,
        reachable=None,
        template_id="zinnia-executive-v1",
        user_id=user_id,
    )
    return {
        "ok": True,
        "zinnia": zinnia,
        "organization": organization,
        "my_templates": mine,
        "template_root": str(_root()),
        "canonical_ids": [r["id"] for r in _CANONICAL_ZINNIA],
        "lifecycle": lifecycle,
        "mappings_ready": {
            r["id"]: bool(r.get("mapped")) for r in zinnia
        },
    }


async def register_user_pptx(
    user_id: str | int,
    upload: UploadFile,
    *,
    name: str | None = None,
    scope: str = "USER",
) -> dict[str, Any]:
    filename = (upload.filename or "template.pptx").strip()
    if not filename.lower().endswith(".pptx"):
        return {"ok": False, "error": "pptx_required"}
    raw = await upload.read()
    if not raw or len(raw) > 40 * 1024 * 1024:
        return {"ok": False, "error": "invalid_or_too_large"}
    org_scope = (scope or "USER").strip().upper() in {"ORG", "ORGANIZATION", "ORG_SHARED"}
    prefix = "org" if org_scope else "user"
    tid = f"{prefix}-{uuid.uuid4().hex[:12]}"
    safe_name = _SAFE.sub("_", (name or Path(filename).stem)[:80]) or "template"
    dest_dir = _org_dir() if org_scope else _user_dir(user_id)
    dest = dest_dir / f"{tid}.pptx"
    dest.write_bytes(raw)
    if not path_under_allowed_roots(str(dest)) and not str(dest).startswith(str(_root())):
        pass
    native_ready_flag = False
    preview = f"Uploaded PPTX template ({len(raw)} bytes)."
    try:
        from app.services.mentrix.presentation.template_importer import UnsafePptxError, import_pptx_bytes

        imported = import_pptx_bytes(
            raw,
            zect_id=tid,
            scope="ORG" if org_scope else "USER",
            name=safe_name,
            source_filename=filename,
        )
        definition = imported.get("definition") or {}
        native_ready_flag = bool(definition.get("ready"))
        preview = str(definition.get("preview") or preview)
    except UnsafePptxError as exc:
        dest.unlink(missing_ok=True)
        return {"ok": False, "error": "unsafe_or_invalid_pptx", "detail": str(exc)}
    entry = {
        "id": tid,
        "name": safe_name,
        "scope": "ORG" if org_scope else "USER_PRIVATE",
        "kind": "org_pptx" if org_scope else "user_pptx",
        "filename": filename,
        "path": str(dest),
        "created_at": _now(),
        "preview": preview,
        "presenton_template_id": None,
        "mapped": native_ready_flag,
        "native_ready": native_ready_flag,
        "provider_uuid_hidden": True,
    }
    if org_scope:
        templates = _load_org()
        templates.insert(0, entry)
        _save_list(_org_meta_path(), templates)
    else:
        templates = _load_list(_meta_path(user_id))
        templates.insert(0, entry)
        _save_list(_meta_path(user_id), templates)
    return {"ok": True, "template": _public_row(entry, default_scope=entry["scope"], default_kind=entry["kind"])}


def import_canonical_master(
    zect_id: str,
    data: bytes,
    *,
    name: str = "",
    filename: str = "",
) -> dict[str, Any]:
    """Admin: import a Zinnia/org PPTX master into TemplateDefinition without Presenton."""
    zid = canonical_id(zect_id) or (zect_id or "").strip()
    if not zid.startswith("zinnia-") and not zid.startswith("org-"):
        return {"ok": False, "error": "canonical_id_required"}
    if not data or len(data) > 40 * 1024 * 1024:
        return {"ok": False, "error": "invalid_or_too_large"}
    dest_dir = _root() / "masters"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{_SAFE.sub('_', zid)[:80]}.pptx"
    dest.write_bytes(data)
    try:
        from app.services.mentrix.presentation.template_importer import UnsafePptxError, import_pptx_bytes

        scope = "ZINNIA" if zid.startswith("zinnia-") else "ORG"
        imported = import_pptx_bytes(
            data,
            zect_id=zid,
            scope=scope,
            name=name or zid,
            source_filename=filename,
        )
    except UnsafePptxError as exc:
        dest.unlink(missing_ok=True)
        return {"ok": False, "error": "unsafe_or_invalid_pptx", "detail": str(exc)}
    definition = imported.get("definition") or {}
    from app.services.mentrix.presentation.template_definition import public_definition

    return {
        "ok": True,
        "template_id": zid,
        "native_ready": bool(definition.get("ready")),
        "definition": public_definition(definition),
    }


def source_pptx_path(zect_id: str, user_id: str | int | None = None) -> Path | None:
    """Local master PPTX for native generate — never a Presenton UUID."""
    zid = canonical_id(zect_id) or (zect_id or "").strip()
    if not zid:
        return None
    master = _root() / "masters" / f"{_SAFE.sub('_', zid)[:80]}.pptx"
    if master.is_file():
        return master
    for row in _load_org():
        if str(row.get("id") or "") == zid:
            p = Path(str(row.get("path") or ""))
            if p.is_file():
                return p
    if user_id is not None:
        for row in _load_list(_meta_path(user_id)):
            if str(row.get("id") or "") == zid:
                p = Path(str(row.get("path") or ""))
                if p.is_file():
                    return p
    return None


def bind_uploaded_template_provider(
    user_id: str | int,
    template_id: str,
    provider_template_id: str,
) -> dict[str, Any]:
    pid = (provider_template_id or "").strip()
    if not is_verified_provider_id(pid):
        return {"ok": False, "error": "provider_id_not_a_master"}
    tid = (template_id or "").strip()
    if tid.startswith("org-") or tid.startswith("user-"):
        # Prefer per-template field on the uploaded row
        updated = _set_upload_provider_id(user_id, tid, pid)
        if updated:
            return {"ok": True, "template": updated}
    return register_provider_mapping(tid, pid, actor=str(user_id), source="upload_bind")


def _set_upload_provider_id(user_id: str | int, template_id: str, provider_id: str) -> dict[str, Any] | None:
    if template_id.startswith("org-"):
        rows = _load_org()
        path = _org_meta_path()
    else:
        rows = _load_list(_meta_path(user_id))
        path = _meta_path(user_id)
    found = None
    for row in rows:
        if row.get("id") == template_id:
            row["presenton_template_id"] = provider_id
            row["mapped"] = True
            found = row
            break
    if found is None:
        return None
    _save_list(path, rows)
    return found


def get_template(user_id: str | int, template_id: str) -> dict[str, Any] | None:
    want = canonical_id(template_id) or template_id
    for t in list_builtin_zinnia():
        if t["id"] == want or t["id"] == template_id:
            return t
        if template_id in (t.get("aliases") or []):
            return t
    for t in list_org_masters():
        if t.get("id") == template_id or t.get("id") == want:
            return t
    for t in _load_list(_meta_path(user_id)):
        if t.get("id") == template_id:
            return t
    return None


def preview_template(user_id: str | int, template_id: str) -> dict[str, Any]:
    t = get_template(user_id, template_id)
    if not t:
        return {"ok": False, "error": "not_found"}
    mapped = get_provider_mapping(t["id"]) or {}
    upload_pid = str(t.get("presenton_template_id") or "")
    from app.services.mentrix.presentation.template_definition import native_ready as _native_ready

    native = _native_ready(str(t["id"]))
    ready = (
        is_verified_provider_id(str(mapped.get("provider_template_id") or ""))
        or is_verified_provider_id(upload_pid)
        or native
    )
    return {
        "ok": True,
        "template_id": t["id"],
        "canonical_id": canonical_id(t["id"]) or t["id"],
        "name": t.get("name"),
        "scope": t.get("scope"),
        "kind": t.get("kind"),
        "preview": t.get("preview") or t.get("name"),
        "mapped": ready,
        "lifecycle": LIFECYCLE_READY if ready else LIFECYCLE_TEMPLATE_NOT_READY,
        "provider_uuid_hidden": True,
    }


def provider_lifecycle(
    *,
    configured: bool | None,
    reachable: bool | None,
    template_id: str | None = None,
    user_id: str | int | None = None,
    generation_failed: bool = False,
) -> str:
    if generation_failed:
        return LIFECYCLE_GENERATION_FAILED
    if configured is False or reachable is False:
        return LIFECYCLE_PROVIDER_UNAVAILABLE
    if configured is None and reachable is None:
        # Registry-only view (no provider probe yet)
        tid = canonical_id(template_id) or (template_id or "")
        from app.services.mentrix.presentation.template_definition import native_ready as _native_ready

        if _native_ready(tid):
            return LIFECYCLE_READY
        if tid.startswith("zinnia-") or tid.startswith("org-"):
            mapped = get_provider_mapping(tid)
            if not is_verified_provider_id(str((mapped or {}).get("provider_template_id") or "")):
                return LIFECYCLE_TEMPLATE_NOT_READY
        if tid.startswith("user-") and user_id is not None:
            t = get_template(user_id, tid)
            if not t or not is_verified_provider_id(str((t or {}).get("presenton_template_id") or "")):
                return LIFECYCLE_TEMPLATE_NOT_READY
        return LIFECYCLE_READY
    if configured and reachable is None:
        return LIFECYCLE_STARTING
    tid = canonical_id(template_id) or (template_id or "")
    if tid.startswith("zinnia-") or tid.startswith("org-"):
        mapped = get_provider_mapping(tid)
        if not is_verified_provider_id(str((mapped or {}).get("provider_template_id") or "")):
            return LIFECYCLE_TEMPLATE_NOT_READY
    if tid.startswith("user-") and user_id is not None:
        t = get_template(user_id, tid)
        pid = str((t or {}).get("presenton_template_id") or "")
        if not is_verified_provider_id(pid):
            return LIFECYCLE_TEMPLATE_NOT_READY
    return LIFECYCLE_READY
