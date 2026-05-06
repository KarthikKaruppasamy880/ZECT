"""File Explorer API — read, write, list, and search files in local repos.

Closes the "File System Access" gap vs Devin: ZECT can now read/write
files directly on disk instead of only via the GitHub API.
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/files", tags=["file-explorer"])

# Safety: only allow access under these roots
ALLOWED_ROOTS = ["/home", "/tmp", "/var", "/opt"]


def _safe_path(raw: str) -> Path:
    """Resolve and validate that the path is under an allowed root."""
    p = Path(raw).resolve()
    if not any(str(p).startswith(root) for root in ALLOWED_ROOTS):
        raise HTTPException(status_code=403, detail=f"Access denied: path must be under {ALLOWED_ROOTS}")
    return p


# ── Models ────────────────────────────────────────────────────────────────

class FileEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int = 0
    extension: str = ""


class FileContent(BaseModel):
    path: str
    content: str
    size: int
    lines: int
    language: str = ""


class WriteFileRequest(BaseModel):
    path: str
    content: str
    create_dirs: bool = True


class CreateFileRequest(BaseModel):
    path: str
    content: str = ""
    create_dirs: bool = True


class RenameRequest(BaseModel):
    old_path: str
    new_path: str


class SearchRequest(BaseModel):
    directory: str
    pattern: str
    file_extensions: list[str] | None = None
    max_results: int = 50


class SearchResult(BaseModel):
    file: str
    line: int
    content: str


# ── Helpers ───────────────────────────────────────────────────────────────

LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescriptreact",
    ".jsx": "javascriptreact", ".html": "html", ".css": "css", ".json": "json",
    ".md": "markdown", ".yml": "yaml", ".yaml": "yaml", ".sh": "bash",
    ".sql": "sql", ".rs": "rust", ".go": "go", ".java": "java",
    ".rb": "ruby", ".php": "php", ".c": "c", ".cpp": "cpp",
    ".h": "c", ".hpp": "cpp", ".toml": "toml", ".xml": "xml",
    ".env": "dotenv", ".dockerfile": "dockerfile", ".tf": "hcl",
}


def _detect_language(path: Path) -> str:
    name = path.name.lower()
    if name == "dockerfile":
        return "dockerfile"
    if name == "makefile":
        return "makefile"
    return LANG_MAP.get(path.suffix.lower(), "")


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/list", response_model=list[FileEntry])
def list_directory(path: str = Query(...), show_hidden: bool = False):
    """List files and directories at the given path."""
    p = _safe_path(path)
    if not p.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries: list[FileEntry] = []
    try:
        for item in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if not show_hidden and item.name.startswith("."):
                continue
            try:
                size = item.stat().st_size if item.is_file() else 0
            except OSError:
                size = 0
            entries.append(FileEntry(
                name=item.name,
                path=str(item),
                is_dir=item.is_dir(),
                size=size,
                extension=item.suffix,
            ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    return entries


@router.get("/read", response_model=FileContent)
def read_file(path: str = Query(...)):
    """Read file content."""
    p = _safe_path(path)
    if not p.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if p.stat().st_size > 2_000_000:  # 2 MB limit
        raise HTTPException(status_code=413, detail="File too large (max 2 MB)")

    try:
        content = p.read_text(errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot read file: {e}")

    return FileContent(
        path=str(p),
        content=content,
        size=p.stat().st_size,
        lines=content.count("\n") + 1,
        language=_detect_language(p),
    )


@router.post("/write")
def write_file(req: WriteFileRequest):
    """Write content to a file (create or overwrite)."""
    p = _safe_path(req.path)
    if req.create_dirs:
        p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(req.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot write file: {e}")
    return {"status": "ok", "path": str(p), "size": len(req.content)}


@router.post("/create")
def create_file(req: CreateFileRequest):
    """Create a new file (fails if already exists)."""
    p = _safe_path(req.path)
    if p.exists():
        raise HTTPException(status_code=409, detail="File already exists")
    if req.create_dirs:
        p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(req.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot create file: {e}")
    return {"status": "created", "path": str(p)}


@router.delete("/delete")
def delete_file(path: str = Query(...)):
    """Delete a file."""
    p = _safe_path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if p.is_dir():
        raise HTTPException(status_code=400, detail="Cannot delete directory via this endpoint")
    try:
        p.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot delete file: {e}")
    return {"status": "deleted", "path": str(p)}


@router.post("/rename")
def rename_file(req: RenameRequest):
    """Rename/move a file or directory."""
    old = _safe_path(req.old_path)
    new = _safe_path(req.new_path)
    if not old.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    if new.exists():
        raise HTTPException(status_code=409, detail="Destination already exists")
    try:
        old.rename(new)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot rename: {e}")
    return {"status": "renamed", "old_path": str(old), "new_path": str(new)}


@router.post("/search", response_model=list[SearchResult])
def search_files(req: SearchRequest):
    """Search file contents for a pattern (simple grep)."""
    p = _safe_path(req.directory)
    if not p.is_dir():
        raise HTTPException(status_code=400, detail="Directory not found")

    results: list[SearchResult] = []
    import re
    try:
        regex = re.compile(req.pattern, re.IGNORECASE)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regex pattern")

    for root, dirs, files in os.walk(p):
        # Skip hidden and common ignore dirs
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "venv", ".git", "dist", "build")]
        for fname in files:
            if req.file_extensions:
                ext = Path(fname).suffix.lower()
                if ext not in req.file_extensions:
                    continue
            fpath = Path(root) / fname
            try:
                if fpath.stat().st_size > 1_000_000:
                    continue
                text = fpath.read_text(errors="replace")
                for i, line in enumerate(text.split("\n"), 1):
                    if regex.search(line):
                        results.append(SearchResult(file=str(fpath), line=i, content=line.strip()[:200]))
                        if len(results) >= req.max_results:
                            return results
            except (PermissionError, OSError):
                continue
    return results


@router.get("/tree")
def file_tree(path: str = Query(...), depth: int = 3):
    """Get a file tree structure (for sidebar navigation)."""
    p = _safe_path(path)
    if not p.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    def _build_tree(dir_path: Path, current_depth: int) -> list[dict]:
        if current_depth <= 0:
            return []
        items = []
        try:
            for item in sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if item.name.startswith(".") or item.name in ("node_modules", "__pycache__", "venv", "dist", "build", ".git"):
                    continue
                entry = {
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                }
                if item.is_dir():
                    entry["children"] = _build_tree(item, current_depth - 1)
                else:
                    entry["size"] = item.stat().st_size
                    entry["extension"] = item.suffix
                items.append(entry)
        except PermissionError:
            pass
        return items

    return _build_tree(p, depth)
