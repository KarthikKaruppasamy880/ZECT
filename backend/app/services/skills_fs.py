"""Filesystem skills under .zect/skills/<name>/SKILL.md + DB sync (P3)."""

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
            out.append(
                {
                    "name": name,
                    "source": "filesystem",
                    "path": str(skill_md),
                    "description": text.strip().splitlines()[0][:240] if text.strip() else "",
                    "body_preview": text[:1500],
                    "script_body": text,
                }
            )
            if len(out) >= limit:
                return out
    return out


def sync_filesystem_skills_to_db(db: Any, *, limit: int = 50) -> dict[str, Any]:
    """Import FS packs into SkillDefinition (upsert by name). DB remains execution SoT."""
    from app.models import SkillDefinition

    packs = list_filesystem_skills(limit=limit)
    created = 0
    updated = 0
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
            existing.description = desc
            existing.script_body = body
            existing.provenance = "imported"
            existing.updated_at = now
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
        "scanned": len(packs),
        "created": created,
        "updated": updated,
        "names": [p["name"] for p in packs],
    }
