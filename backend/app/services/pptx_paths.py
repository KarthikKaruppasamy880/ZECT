"""Allowlisted PPTX paths for ZECT Present download/parse (Documents/Desktop/Downloads)."""

from __future__ import annotations

from pathlib import Path


def pptx_output_roots() -> list[Path]:
    home = Path.home()
    candidates = [
        home / "Documents",
        home / "OneDrive" / "Documents",
        home / "Desktop",
        home / "OneDrive" / "Desktop",
        home / "Downloads",
        home / "OneDrive" / "Downloads",
    ]
    return [p.resolve() for p in candidates if p.is_dir()]


def resolve_allowlisted_pptx(path_str: str) -> Path:
    raw = (path_str or "").strip().strip('"')
    if not raw:
        raise ValueError("path_required")
    path = Path(raw).expanduser().resolve()
    if path.suffix.lower() != ".pptx":
        raise ValueError("pptx_required")
    if not path.is_file():
        raise FileNotFoundError("not_found")
    for root in pptx_output_roots():
        try:
            path.relative_to(root)
            return path
        except ValueError:
            continue
    raise PermissionError("path_not_allowlisted")
