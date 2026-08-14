"""Allowlisted PPTX paths for ZECT Present download/parse (Documents/Desktop/Downloads)."""

from __future__ import annotations

import os
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


def _under_allowlist(path: Path) -> bool:
    for root in pptx_output_roots():
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def resolve_allowlisted_pptx(path_str: str) -> Path:
    raw = (path_str or "").strip().strip('"')
    if not raw:
        raise ValueError("path_required")
    path = Path(raw).expanduser().resolve()
    if path.suffix.lower() != ".pptx":
        raise ValueError("pptx_required")
    if not path.is_file():
        raise FileNotFoundError("not_found")
    if not _under_allowlist(path):
        raise PermissionError("path_not_allowlisted")
    return path


def notes_sidecar_for_pptx(pptx: Path) -> Path:
    """Sidecar next to an allowlisted PPTX. Never follow a symlink out of the allowlist."""
    sidecar = pptx.parent / f"{pptx.stem}.notes.json"
    if sidecar.is_symlink():
        raise PermissionError("sidecar_symlink")
    resolved_parent = sidecar.parent.resolve()
    if resolved_parent != pptx.parent.resolve() or not _under_allowlist(resolved_parent):
        raise PermissionError("sidecar_path_rejected")
    return resolved_parent / sidecar.name


def write_notes_sidecar(sidecar: Path, text: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if nofollow:
        flags |= nofollow
    fd = os.open(str(sidecar), flags, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
