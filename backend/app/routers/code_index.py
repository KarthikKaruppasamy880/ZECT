"""Code Index — symbol search and codebase indexing."""

import os
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models import CodeSymbol, Repo

router = APIRouter(prefix="/api/code-index", tags=["code-index"])

# Language-specific regex patterns for symbol extraction
PATTERNS = {
    "python": {
        "function": re.compile(r"^(?:async\s+)?def\s+(\w+)\s*\(", re.MULTILINE),
        "class": re.compile(r"^class\s+(\w+)", re.MULTILINE),
        "variable": re.compile(r"^(\w+)\s*=\s*", re.MULTILINE),
        "import": re.compile(r"^(?:from\s+\S+\s+)?import\s+(.+)", re.MULTILINE),
    },
    "typescript": {
        "function": re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE),
        "class": re.compile(r"(?:export\s+)?class\s+(\w+)", re.MULTILINE),
        "interface": re.compile(r"(?:export\s+)?interface\s+(\w+)", re.MULTILINE),
        "type": re.compile(r"(?:export\s+)?type\s+(\w+)", re.MULTILINE),
        "variable": re.compile(r"(?:export\s+)?(?:const|let|var)\s+(\w+)", re.MULTILINE),
    },
    "javascript": {
        "function": re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE),
        "class": re.compile(r"(?:export\s+)?class\s+(\w+)", re.MULTILINE),
        "variable": re.compile(r"(?:export\s+)?(?:const|let|var)\s+(\w+)", re.MULTILINE),
    },
}

LANG_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
}


class IndexRequest(BaseModel):
    repo_path: str
    repo_id: Optional[int] = None
    file_extensions: list = [".py", ".ts", ".tsx", ".js", ".jsx"]
    max_files: int = 500


@router.get("/search")
def search_symbols(
    query: str,
    symbol_type: Optional[str] = None,
    language: Optional[str] = None,
    repo_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Search indexed code symbols."""
    try:
        q = db.query(CodeSymbol).filter(
            CodeSymbol.symbol_name.ilike(f"%{query}%")
        )
        if symbol_type:
            q = q.filter(CodeSymbol.symbol_type == symbol_type)
        if language:
            q = q.filter(CodeSymbol.language == language)
        if repo_id:
            q = q.filter(CodeSymbol.repo_id == repo_id)
        items = q.order_by(CodeSymbol.symbol_name).limit(limit).all()
        return [_sym_to_dict(s) for s in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index")
def index_repo(data: IndexRequest, db: Session = Depends(get_db)):
    """Index a repository's code symbols (Lattice-first, regex fallback)."""
    try:
        if not os.path.isdir(data.repo_path):
            raise HTTPException(status_code=400, detail=f"Directory not found: {data.repo_path}")

        # Clear previous index for this repo
        if data.repo_id:
            db.query(CodeSymbol).filter(CodeSymbol.repo_id == data.repo_id).delete()

        # Prefer Lattice AST graph symbols when enabled
        if os.getenv("LATTICE_ENABLED", "true").lower() not in ("0", "false"):
            try:
                from app.services.lattice.indexer import ingest_path

                graph = ingest_path(
                    data.repo_path,
                    project_key=data.repo_path,
                    max_files=data.max_files,
                )
                indexed_count = 0
                for node in graph.nodes:
                    if node.kind in ("file",):
                        continue
                    symbol = CodeSymbol(
                        repo_id=data.repo_id,
                        file_path=node.path,
                        symbol_name=node.name,
                        symbol_type=node.kind,
                        language=node.language or "",
                        line_start=node.line or 0,
                        signature=f"{node.kind} {node.name}",
                        is_exported=True,
                    )
                    db.add(symbol)
                    indexed_count += 1
                db.commit()
                return {
                    "status": "indexed",
                    "engine": "lattice",
                    "files_processed": graph.files_indexed,
                    "symbols_indexed": indexed_count,
                    "repo_path": data.repo_path,
                    "languages": graph.languages,
                }
            except Exception:
                db.rollback()
                # Fall through to legacy regex indexer

        indexed_count = 0
        files_processed = 0

        for root, _dirs, files in os.walk(data.repo_path):
            # Skip hidden directories and common non-code dirs
            if any(skip in root for skip in ["node_modules", ".git", "__pycache__", ".venv", "dist", "build"]):
                continue
            for fname in files:
                ext = os.path.splitext(fname)[1]
                if ext not in data.file_extensions:
                    continue
                if files_processed >= data.max_files:
                    break

                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, data.repo_path)
                lang = LANG_MAP.get(ext, "")
                patterns = PATTERNS.get(lang, {})

                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    lines = content.split("\n")
                except Exception:
                    continue

                files_processed += 1

                for sym_type, pattern in patterns.items():
                    for match in pattern.finditer(content):
                        name = match.group(1).strip()
                        if not name or name.startswith("_") and sym_type == "variable":
                            continue
                        # Calculate line number
                        line_start = content[:match.start()].count("\n") + 1
                        # Get signature (the matched line)
                        sig = lines[line_start - 1].strip() if line_start <= len(lines) else ""

                        symbol = CodeSymbol(
                            repo_id=data.repo_id,
                            file_path=rel_path,
                            symbol_name=name,
                            symbol_type=sym_type,
                            language=lang,
                            line_start=line_start,
                            signature=sig[:500],
                            is_exported="export" in sig.lower() if lang in ("typescript", "javascript") else not name.startswith("_"),
                        )
                        db.add(symbol)
                        indexed_count += 1

        db.commit()
        return {
            "status": "indexed",
            "files_processed": files_processed,
            "symbols_indexed": indexed_count,
            "repo_path": data.repo_path,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def index_stats(repo_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get indexing statistics."""
    try:
        from sqlalchemy import func
        q = db.query(CodeSymbol)
        if repo_id:
            q = q.filter(CodeSymbol.repo_id == repo_id)
        total = q.count()
        by_type = dict(
            q.with_entities(CodeSymbol.symbol_type, func.count(CodeSymbol.id))
            .group_by(CodeSymbol.symbol_type).all()
        )
        by_language = dict(
            q.with_entities(CodeSymbol.language, func.count(CodeSymbol.id))
            .group_by(CodeSymbol.language).all()
        )
        return {
            "total_symbols": total,
            "by_type": by_type,
            "by_language": by_language,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{path:path}")
def get_file_symbols(path: str, repo_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get all symbols in a specific file."""
    try:
        q = db.query(CodeSymbol).filter(CodeSymbol.file_path == path)
        if repo_id:
            q = q.filter(CodeSymbol.repo_id == repo_id)
        items = q.order_by(CodeSymbol.line_start).all()
        return [_sym_to_dict(s) for s in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _sym_to_dict(s: CodeSymbol) -> dict:
    return {
        "id": s.id,
        "repo_id": s.repo_id,
        "file_path": s.file_path,
        "symbol_name": s.symbol_name,
        "symbol_type": s.symbol_type,
        "language": s.language,
        "line_start": s.line_start,
        "line_end": s.line_end,
        "signature": s.signature,
        "docstring": s.docstring,
        "parent_symbol": s.parent_symbol,
        "is_exported": s.is_exported,
        "indexed_at": s.indexed_at.isoformat() if s.indexed_at else None,
    }
