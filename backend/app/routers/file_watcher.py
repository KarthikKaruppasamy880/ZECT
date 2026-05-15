"""File Watcher API — monitor cloned repos for external changes."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.file_watcher import (
    start_watching,
    stop_watching,
    get_changes,
    get_watcher_status,
    list_watchers,
)

router = APIRouter(prefix="/api/file-watcher", tags=["file-watcher"])


class WatchRequest(BaseModel):
    repo_id: int
    repo_path: str
    interval: int = 5


@router.post("/start")
def start_watch(req: WatchRequest):
    """Start watching a repository for file changes."""
    return start_watching(req.repo_id, req.repo_path, req.interval)


@router.post("/stop/{repo_id}")
def stop_watch(repo_id: int):
    """Stop watching a repository."""
    return stop_watching(repo_id)


@router.get("/changes/{repo_id}")
def get_repo_changes(repo_id: int, since: int = 0):
    """Get file changes for a watched repository."""
    changes = get_changes(repo_id, since)
    return {"repo_id": repo_id, "changes": changes, "count": len(changes)}


@router.get("/status/{repo_id}")
def watcher_status(repo_id: int):
    """Get watcher status for a repository."""
    status = get_watcher_status(repo_id)
    if not status:
        return {"repo_id": repo_id, "running": False}
    return status


@router.get("/list")
def list_all_watchers():
    """List all active file watchers."""
    watchers = list_watchers()
    return {"watchers": watchers, "count": len(watchers)}
