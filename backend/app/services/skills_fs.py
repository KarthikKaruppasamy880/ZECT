"""Filesystem skills under .zect/skills/<name>/SKILL.md + bidirectional DB sync.

DB SkillDefinition remains execution source of truth.
FS packs are the portable authoring form under the primary .zect/skills root.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def skills_fs_roots() -> list[Path]:
    root = _repo_root()
    return [
        root / ".zect" / "skills",
        root / "skills",
        Path.cwd() / ".zect" / "skills",
        Path.cwd() / "skills",
    ]


def primary_skills_fs_root() -> Path:
    """Canonical write root for DB→FS export."""
    return _repo_root() / ".zect" / "skills"


def list_filesystem_skills(limit: int = 50) -> list[dict[str, Any]]:
    """Read SKILL.md packs; does not replace SkillDefinition DB execution SoT."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in skills_fs_roots():
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            name = skill_md.parent.name
            if name in seen:
                continue
            seen.add(name)
            try:
                text = skill_md.read_text(encoding="utf-8")
            except OSError:
                continue
            mtime = None
            try:
                mtime = skill_md.stat().st_mtime
            except OSError:
                pass
            out.append(
                {
                    "name": name,
                    "source": "filesystem",
                    "path": str(skill_md),
                    "description": text.strip().splitlines()[0][:240] if text.strip() else "",
                    "body_preview": text[:1500],
                    "script_body": text,
                    "mtime": mtime,
                }
            )
            if len(out) >= limit:
                return out
    return out


def _skill_body_from_row(row: Any) -> str:
    body = (getattr(row, "script_body", None) or "").strip()
    if body:
        return body if body.endswith("\n") else body + "\n"
    desc = (getattr(row, "description", None) or "").strip()
    name = getattr(row, "name", "skill")
    return f"# {name}\n\n{desc}\n" if desc else f"# {name}\n"


def sync_filesystem_skills_to_db(db: Any, *, limit: int = 50) -> dict[str, Any]:
    """Import FS packs into SkillDefinition (upsert by name). DB remains execution SoT."""
    from app.models import SkillDefinition

    packs = list_filesystem_skills(limit=limit)
    created = 0
    updated = 0
    skipped = 0
    now = datetime.now(timezone.utc)
    for pack in packs:
        name = pack["name"]
        existing = (
            db.query(SkillDefinition)
            .filter(SkillDefinition.name == name, SkillDefinition.is_active == True)  # noqa: E712
            .first()
        )
        body = pack.get("script_body") or pack.get("body_preview") or ""
        desc = pack.get("description") or f"Imported from {pack.get('path')}"
        if existing:
            # Prefer FS when body differs and FS looks like newer authoring, or DB empty
            db_body = (existing.script_body or "").strip()
            fs_body = (body or "").strip()
            if db_body == fs_body:
                skipped += 1
                continue
            # Conflict: if DB was locally edited (provenance local) keep DB unless FS newer + imported
            prov = (existing.provenance or "").strip().lower()
            if prov == "local" and db_body and fs_body != db_body:
                skipped += 1
                continue
            existing.description = desc
            existing.script_body = body
            existing.provenance = "imported"
            existing.updated_at = now
            manifest = dict(existing.manifest or {})
            manifest["source_path"] = pack.get("path")
            manifest["imported_from"] = "skills_fs"
            existing.manifest = manifest
            updated += 1
        else:
            db.add(
                SkillDefinition(
                    name=name,
                    version="1.0.0",
                    description=desc,
                    category="filesystem",
                    trigger_pattern="",
                    manifest={"source_path": pack.get("path"), "imported_from": "skills_fs"},
                    script_body=body,
                    is_seed=False,
                    is_active=True,
                    provenance="imported",
                    approval_required=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            created += 1
    db.commit()
    return {
        "ok": True,
        "direction": "fs_to_db",
        "scanned": len(packs),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "names": [p["name"] for p in packs],
    }


def sync_db_skills_to_filesystem(db: Any, *, limit: int = 50) -> dict[str, Any]:
    """Export active SkillDefinition rows to .zect/skills/<name>/SKILL.md."""
    from app.models import SkillDefinition

    root = primary_skills_fs_root()
    root.mkdir(parents=True, exist_ok=True)
    rows = (
        db.query(SkillDefinition)
        .filter(SkillDefinition.is_active == True)  # noqa: E712
        .order_by(SkillDefinition.name.asc())
        .limit(limit)
        .all()
    )
    written = 0
    skipped = 0
    names: list[str] = []
    for row in rows:
        name = (row.name or "").strip()
        if not name or "/" in name or "\\" in name or ".." in name:
            skipped += 1
            continue
        names.append(name)
        skill_dir = root / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        path = skill_dir / "SKILL.md"
        new_body = _skill_body_from_row(row)
        if path.is_file():
            try:
                old = path.read_text(encoding="utf-8")
            except OSError:
                old = ""
            if old.strip() == new_body.strip():
                skipped += 1
                continue
        path.write_text(new_body, encoding="utf-8")
        written += 1
        manifest = dict(row.manifest or {})
        manifest["exported_path"] = str(path)
        manifest["exported_at"] = datetime.now(timezone.utc).isoformat()
        row.manifest = manifest
        if not (row.provenance or "").strip():
            row.provenance = "local"
    db.commit()
    return {
        "ok": True,
        "direction": "db_to_fs",
        "root": str(root),
        "scanned": len(rows),
        "written": written,
        "skipped": skipped,
        "names": names,
    }


def sync_skills_bidirectional(db: Any, *, limit: int = 50) -> dict[str, Any]:
    """FS→DB then DB→FS so packs and SkillDefinition stay aligned.

    Conflict policy: local DB edits win over FS import; other rows accept FS body;
    then all active DB skills are exported to the primary .zect/skills root.
    """
    inbound = sync_filesystem_skills_to_db(db, limit=limit)
    outbound = sync_db_skills_to_filesystem(db, limit=limit)
    return {
        "ok": True,
        "direction": "bidirectional",
        "fs_to_db": inbound,
        "db_to_fs": outbound,
    }
