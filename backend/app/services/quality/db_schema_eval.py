"""Governed, read-only DB schema/ORM/migration inventory for the coding
agent's context pipeline.

Static analysis only -- no live database connection, no credentials, no
new dependency on a running Postgres/etc being reachable. Detects
SQLAlchemy model classes (this repo's own stack, and the platform's
default per CLAUDE.md) and Alembic migrations. A target repo using a
different ORM/migration tool (Django, Prisma, TypeORM, raw SQL) simply
reports empty lists rather than guessing at a scheme this module doesn't
understand -- see api_eval.py's inventory_apis() for the identical
philosophy applied to route/OpenAPI inventory.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Any

_ORM_BASE_HINTS = {"Base", "Model"}
_COLUMN_CALL_NAMES = {"Column", "mapped_column"}
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
_MAX_FILES_SCANNED = 4000


def _name_of(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _column_type_name(call: ast.Call) -> str:
    if not call.args:
        return "unknown"
    first = call.args[0]
    if isinstance(first, ast.Call):
        return _name_of(first.func) or "unknown"
    if isinstance(first, (ast.Name, ast.Attribute)):
        return _name_of(first) or "unknown"
    return "unknown"


def _is_column_call(value: ast.expr | None) -> bool:
    return isinstance(value, ast.Call) and _name_of(value.func) in _COLUMN_CALL_NAMES


def _parse_model_file(path: Path, *, workspace: Path) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError, ValueError):
        return []
    tables: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = [_name_of(b) for b in node.bases]
        looks_like_orm_model = any(
            b in _ORM_BASE_HINTS or (b or "").endswith("Base") for b in base_names
        )
        if not looks_like_orm_model:
            continue
        table_name = ""
        columns: list[dict[str, str]] = []
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if target.id == "__tablename__" and isinstance(stmt.value, ast.Constant):
                table_name = str(stmt.value.value)
            elif _is_column_call(stmt.value):
                columns.append({"name": target.id, "type": _column_type_name(stmt.value)})
        if not table_name and not columns:
            continue  # a same-named-Base class that isn't actually a mapped model
        try:
            rel = str(path.relative_to(workspace)).replace("\\", "/")
        except ValueError:
            rel = str(path)
        tables.append(
            {
                "model_class": node.name,
                "table_name": table_name or node.name.lower(),
                "columns": columns,
                "source": rel,
            }
        )
    return tables


def _parse_alembic_migrations(root: Path) -> list[dict[str, Any]]:
    migrations: list[dict[str, Any]] = []
    for versions_dir in root.rglob("alembic/versions"):
        if not versions_dir.is_dir():
            continue
        for fp in sorted(versions_dir.glob("*.py"))[:200]:
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rev = re.search(r'^revision\s*(?::[^=]+)?=\s*["\']([^"\']+)["\']', text, re.M)
            down = re.search(r'^down_revision\s*(?::[^=]+)?=\s*["\']([^"\']+)["\']', text, re.M)
            try:
                doc = ast.get_docstring(ast.parse(text)) or ""
            except SyntaxError:
                doc = ""
            message = doc.strip().splitlines()[0] if doc.strip() else fp.stem
            migrations.append(
                {
                    "revision": rev.group(1) if rev else "",
                    "down_revision": down.group(1) if down else "",
                    "message": message[:200],
                    "file": fp.name,
                }
            )
    return migrations


def inventory_db_schema(*, workspace: str = "") -> dict[str, Any]:
    """Static, read-only inventory of this workspace's ORM models
    (SQLAlchemy classes with __tablename__/Column) and migrations
    (Alembic revision files). No live DB connection, no credentials. A
    repo using a different ORM/migration tool reports empty lists rather
    than guessing."""
    root = Path(workspace) if workspace else None
    if not root or not root.is_dir():
        return {"tables": [], "migrations": [], "sources": [], "count": 0}

    tables: list[dict[str, Any]] = []
    sources: list[str] = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            scanned += 1
            if scanned > _MAX_FILES_SCANNED:
                break
            fp = Path(dirpath) / fn
            found = _parse_model_file(fp, workspace=root)
            if found:
                tables.extend(found)
                try:
                    sources.append(str(fp.relative_to(root)).replace("\\", "/"))
                except ValueError:
                    sources.append(str(fp))
        if scanned > _MAX_FILES_SCANNED:
            break

    migrations = _parse_alembic_migrations(root)
    return {
        "tables": tables[:200],
        "migrations": migrations[:100],
        "sources": sources[:50],
        "count": len(tables),
    }
