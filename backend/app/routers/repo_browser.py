"""Repo Browser Router — browse file tree, read files, search within cloned repos."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Repo

router = APIRouter(prefix="/api/repos", tags=["repo-browser"])

# File size limit for reading (2 MB)
MAX_FILE_SIZE = 2_000_000

# Directories to skip in tree building
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", ".cache", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "coverage",
    ".DS_Store", "target", "out", ".gradle",
}

# Extension → language mapping for syntax highlighting
LANGUAGE_MAP = {
    ".py": "python", ".pyx": "python", ".pyi": "python",
    ".ts": "typescript", ".tsx": "typescriptreact",
    ".js": "javascript", ".jsx": "javascriptreact",
    ".java": "java", ".go": "go", ".rs": "rust",
    ".rb": "ruby", ".php": "php",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
    ".cs": "csharp", ".swift": "swift", ".kt": "kotlin",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".less": "less",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".ini": "ini", ".cfg": "ini",
    ".md": "markdown", ".mdx": "markdown",
    ".sql": "sql", ".sh": "shell", ".bash": "shell",
    ".dockerfile": "dockerfile", ".xml": "xml",
    ".graphql": "graphql", ".gql": "graphql",
    ".env": "dotenv", ".gitignore": "gitignore",
    ".tf": "hcl", ".hcl": "hcl",
    ".vue": "vue", ".svelte": "svelte",
    ".r": "r", ".R": "r",
    ".lua": "lua", ".dart": "dart", ".ex": "elixir",
    ".exs": "elixir", ".erl": "erlang", ".clj": "clojure",
    ".scala": "scala", ".zig": "zig", ".nim": "nim",
    ".proto": "protobuf",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_repo_or_404(db: Session, repo_id: int) -> Repo:
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    if repo.clone_status != "cloned" or not repo.local_path:
        raise HTTPException(status_code=400, detail="Repo is not cloned. Clone it first via POST /api/repos/clone")
    if not os.path.isdir(repo.local_path):
        raise HTTPException(status_code=400, detail="Clone directory missing from disk")
    return repo


def _safe_resolve(repo_root: str, relative_path: str) -> Path:
    """Resolve a path safely, ensuring it stays within the repo root."""
    root = Path(repo_root).resolve()
    target = (root / relative_path).resolve()
    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=403, detail="Path traversal not allowed")
    return target


def _detect_language(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    name = os.path.basename(file_path).lower()
    if name == "dockerfile":
        return "dockerfile"
    if name == "makefile":
        return "makefile"
    if name in ("procfile", "gemfile", "rakefile"):
        return "ruby"
    return LANGUAGE_MAP.get(ext, "text")


def _is_binary(file_path: str) -> bool:
    """Quick heuristic to detect binary files."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
        return False
    except (OSError, PermissionError):
        return True


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class FileTreeNode(BaseModel):
    name: str
    path: str  # relative to repo root
    is_dir: bool
    size: int = 0
    extension: str = ""
    language: str = ""
    children: Optional[list["FileTreeNode"]] = None


class FileContentResponse(BaseModel):
    path: str
    content: str
    size: int
    lines: int
    language: str
    is_binary: bool = False


class SearchMatch(BaseModel):
    file: str  # relative path
    line: int
    content: str
    language: str = ""


class RepoStatsResponse(BaseModel):
    total_files: int
    total_lines: int
    disk_usage_mb: float
    languages: dict
    clone_branch: str
    last_pulled_at: Optional[str] = None


class SearchRequest(BaseModel):
    pattern: str
    file_extensions: Optional[list[str]] = None
    max_results: int = 100


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{repo_id}/tree")
def repo_tree(
    repo_id: int,
    path: str = "",
    depth: int = 3,
    db: Session = Depends(get_db),
):
    """Get the file tree of a cloned repo. Supports depth control and sub-path."""
    repo = _get_repo_or_404(db, repo_id)
    target = _safe_resolve(repo.local_path, path) if path else Path(repo.local_path)

    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    root = Path(repo.local_path).resolve()

    def _build_tree(dir_path: Path, current_depth: int) -> list[dict]:
        if current_depth <= 0:
            return []
        items = []
        try:
            entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in entries:
                if item.name in SKIP_DIRS or item.name.startswith("."):
                    continue
                rel = str(item.relative_to(root))
                entry: dict = {
                    "name": item.name,
                    "path": rel,
                    "is_dir": item.is_dir(),
                }
                if item.is_dir():
                    entry["children"] = _build_tree(item, current_depth - 1)
                else:
                    try:
                        entry["size"] = item.stat().st_size
                    except OSError:
                        entry["size"] = 0
                    entry["extension"] = item.suffix
                    entry["language"] = _detect_language(str(item))
                items.append(entry)
        except PermissionError:
            pass
        return items

    return _build_tree(target, depth)


@router.get("/{repo_id}/file")
def repo_file(
    repo_id: int,
    path: str = Query(..., description="Relative file path within the repo"),
    db: Session = Depends(get_db),
):
    """Read a specific file from the cloned repo by relative path."""
    repo = _get_repo_or_404(db, repo_id)
    target = _safe_resolve(repo.local_path, path)

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if target.is_dir():
        raise HTTPException(status_code=400, detail="Path is a directory, not a file")

    file_size = target.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large ({file_size} bytes). Max is {MAX_FILE_SIZE}.")

    language = _detect_language(str(target))

    if _is_binary(str(target)):
        return {
            "path": path,
            "content": "[Binary file — cannot display]",
            "size": file_size,
            "lines": 0,
            "language": language,
            "is_binary": True,
        }

    try:
        content = target.read_text(errors="replace")
        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

    return {
        "path": path,
        "content": content,
        "size": file_size,
        "lines": line_count,
        "language": language,
        "is_binary": False,
    }


@router.post("/{repo_id}/search")
def repo_search(
    repo_id: int,
    req: SearchRequest,
    db: Session = Depends(get_db),
):
    """Search file contents within a cloned repo using regex."""
    repo = _get_repo_or_404(db, repo_id)
    root = Path(repo.local_path)

    try:
        regex = re.compile(req.pattern, re.IGNORECASE)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regex pattern")

    results: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if req.file_extensions:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in req.file_extensions:
                    continue
            fpath = os.path.join(dirpath, fname)
            try:
                if os.path.getsize(fpath) > 1_000_000:
                    continue
                if _is_binary(fpath):
                    continue
                rel = str(Path(fpath).relative_to(root))
                with open(fpath, "r", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append({
                                "file": rel,
                                "line": i,
                                "content": line.strip()[:200],
                                "language": _detect_language(fpath),
                            })
                            if len(results) >= req.max_results:
                                return results
            except (PermissionError, OSError):
                continue

    return results


@router.get("/{repo_id}/file-stats")
def repo_file_stats(repo_id: int, db: Session = Depends(get_db)):
    """Get file count, total size, language breakdown for a cloned repo."""
    repo = _get_repo_or_404(db, repo_id)

    return {
        "total_files": repo.total_files or 0,
        "total_lines": repo.total_lines or 0,
        "disk_usage_mb": repo.disk_usage_mb or 0.0,
        "languages": (repo.index_stats or {}).get("languages", {}),
        "clone_branch": repo.clone_branch or "",
        "last_pulled_at": str(repo.last_pulled_at) if repo.last_pulled_at else None,
    }


class WriteFileRequest(BaseModel):
    path: str
    content: str


@router.post("/{repo_id}/write-file")
def repo_write_file(
    repo_id: int,
    req: WriteFileRequest,
    db: Session = Depends(get_db),
):
    """Write content to a file in the cloned repo (for code write-back)."""
    repo = _get_repo_or_404(db, repo_id)
    target = _safe_resolve(repo.local_path, req.path)

    # Create parent directories if needed
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        target.write_text(req.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing file: {e}")

    return {
        "status": "written",
        "path": req.path,
        "size": len(req.content),
        "lines": req.content.count("\n") + (1 if req.content and not req.content.endswith("\n") else 0),
    }
