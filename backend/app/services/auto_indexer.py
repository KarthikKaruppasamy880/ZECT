"""Auto-Indexer Service — automatically index code symbols after clone/pull."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import CodeSymbol, Repo

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", ".cache", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "coverage",
    "target", "out", ".gradle",
}

MAX_FILES = 2000
MAX_FILE_SIZE = 2_000_000  # 2 MB

# Language patterns for symbol extraction
PATTERNS: dict[str, dict[str, re.Pattern]] = {
    "python": {
        "function": re.compile(r"^(?:async\s+)?def\s+(\w+)\s*\(", re.MULTILINE),
        "class": re.compile(r"^class\s+(\w+)", re.MULTILINE),
        "variable": re.compile(r"^([A-Z][A-Z_0-9]+)\s*=", re.MULTILINE),
        "import": re.compile(r"^(?:from\s+\S+\s+)?import\s+(.+)", re.MULTILINE),
    },
    "typescript": {
        "function": re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE),
        "class": re.compile(r"(?:export\s+)?class\s+(\w+)", re.MULTILINE),
        "interface": re.compile(r"(?:export\s+)?interface\s+(\w+)", re.MULTILINE),
        "type": re.compile(r"(?:export\s+)?type\s+(\w+)\s*=", re.MULTILINE),
        "variable": re.compile(r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*[=:]", re.MULTILINE),
        "import": re.compile(r"import\s+.*?from\s+['\"](.+?)['\"]", re.MULTILINE),
    },
    "javascript": {
        "function": re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE),
        "class": re.compile(r"(?:export\s+)?class\s+(\w+)", re.MULTILINE),
        "variable": re.compile(r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*[=:]", re.MULTILINE),
        "import": re.compile(r"(?:import|require)\s*\(?['\"](.+?)['\"]", re.MULTILINE),
    },
    "java": {
        "function": re.compile(r"(?:public|private|protected|static)\s+\w+\s+(\w+)\s*\(", re.MULTILINE),
        "class": re.compile(r"(?:public|private|protected)?\s*(?:abstract\s+)?class\s+(\w+)", re.MULTILINE),
        "interface": re.compile(r"(?:public\s+)?interface\s+(\w+)", re.MULTILINE),
        "import": re.compile(r"import\s+([\w.]+)", re.MULTILINE),
    },
    "go": {
        "function": re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", re.MULTILINE),
        "type": re.compile(r"^type\s+(\w+)\s+(?:struct|interface)", re.MULTILINE),
        "variable": re.compile(r"^(?:var|const)\s+(\w+)", re.MULTILINE),
        "import": re.compile(r'"([\w./]+)"', re.MULTILINE),
    },
    "rust": {
        "function": re.compile(r"(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", re.MULTILINE),
        "class": re.compile(r"(?:pub\s+)?struct\s+(\w+)", re.MULTILINE),
        "type": re.compile(r"(?:pub\s+)?enum\s+(\w+)", re.MULTILINE),
        "interface": re.compile(r"(?:pub\s+)?trait\s+(\w+)", re.MULTILINE),
        "import": re.compile(r"use\s+([\w:]+)", re.MULTILINE),
    },
    "ruby": {
        "function": re.compile(r"^\s*def\s+(\w+)", re.MULTILINE),
        "class": re.compile(r"^\s*class\s+(\w+)", re.MULTILINE),
        "variable": re.compile(r"^\s*([A-Z][A-Z_0-9]+)\s*=", re.MULTILINE),
    },
    "php": {
        "function": re.compile(r"(?:public|private|protected|static)?\s*function\s+(\w+)", re.MULTILINE),
        "class": re.compile(r"class\s+(\w+)", re.MULTILINE),
        "interface": re.compile(r"interface\s+(\w+)", re.MULTILINE),
    },
}

EXT_TO_LANG = {
    ".py": "python", ".pyx": "python", ".pyi": "python",
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript",
    ".java": "java", ".go": "go", ".rs": "rust",
    ".rb": "ruby", ".php": "php",
}


def index_repo(db: Session, repo_id: int) -> dict:
    """Index all code symbols in a cloned repo. Replaces existing symbols."""
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        return {"error": "Repo not found"}
    if repo.clone_status != "cloned" or not repo.local_path:
        return {"error": "Repo is not cloned"}
    if not os.path.isdir(repo.local_path):
        return {"error": "Clone directory missing"}

    root = Path(repo.local_path)

    # Delete existing symbols for this repo
    db.query(CodeSymbol).filter(CodeSymbol.repo_id == repo_id).delete()
    db.flush()

    symbols_added = 0
    files_scanned = 0
    errors = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if files_scanned >= MAX_FILES:
                break

            fpath = os.path.join(dirpath, fname)
            ext = os.path.splitext(fname)[1].lower()
            lang = EXT_TO_LANG.get(ext)
            if not lang:
                continue

            patterns = PATTERNS.get(lang, {})
            if not patterns:
                continue

            try:
                size = os.path.getsize(fpath)
                if size > MAX_FILE_SIZE:
                    continue

                with open(fpath, "r", errors="replace") as f:
                    content = f.read()

                rel_path = str(Path(fpath).relative_to(root))
                files_scanned += 1

                for symbol_type, pattern in patterns.items():
                    for match in pattern.finditer(content):
                        name = match.group(1).strip()
                        if not name or len(name) < 2:
                            continue

                        # Calculate line number
                        line_start = content[:match.start()].count("\n") + 1

                        # Get the full line as signature
                        line_end_pos = content.find("\n", match.start())
                        if line_end_pos == -1:
                            line_end_pos = len(content)
                        signature = content[match.start():line_end_pos].strip()[:200]

                        symbol = CodeSymbol(
                            repo_id=repo_id,
                            file_path=rel_path,
                            symbol_name=name,
                            symbol_type=symbol_type,
                            language=lang,
                            line_start=line_start,
                            line_end=line_start,
                            signature=signature,
                            is_exported=True,
                            indexed_at=datetime.now(timezone.utc),
                        )
                        db.add(symbol)
                        symbols_added += 1

            except (OSError, PermissionError) as e:
                errors.append(f"{fname}: {e}")
                continue

        if files_scanned >= MAX_FILES:
            break

    # Update repo indexed timestamp
    repo.indexed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "indexed",
        "files_scanned": files_scanned,
        "symbols_added": symbols_added,
        "errors": errors[:10],
    }
