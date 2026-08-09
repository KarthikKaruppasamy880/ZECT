"""Filesystem skills under .zect/skills/<name>/SKILL.md (P2 dual-read)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    # backend/app/services/skills_fs.py → repo root
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
                }
            )
            if len(out) >= limit:
                return out
    return out
