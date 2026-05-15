"""File Watcher Service — monitor cloned repos for external changes.

Uses polling-based file monitoring (no OS-level watcher dependency)
to detect changes in cloned repositories and notify the frontend.
"""

from __future__ import annotations

import os
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread, Event

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build", ".next"}

_watchers: dict[int, "RepoWatcher"] = {}


class FileChange:
    def __init__(self, path: str, change_type: str, old_hash: str = "", new_hash: str = ""):
        self.path = path
        self.change_type = change_type  # added, modified, deleted
        self.old_hash = old_hash
        self.new_hash = new_hash
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "change_type": self.change_type,
            "timestamp": self.timestamp,
        }


class RepoWatcher:
    """Watches a repository directory for file changes using polling."""

    def __init__(self, repo_id: int, repo_path: str, interval: int = 5):
        self.repo_id = repo_id
        self.repo_path = repo_path
        self.interval = interval
        self._snapshot: dict[str, str] = {}  # relative_path -> md5 hash
        self._changes: list[FileChange] = []
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._running = False

    def _hash_file(self, path: Path) -> str:
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def _take_snapshot(self) -> dict[str, str]:
        snapshot = {}
        root = Path(self.repo_path)
        if not root.is_dir():
            return snapshot

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                fpath = Path(dirpath) / fname
                rel = str(fpath.relative_to(root))
                snapshot[rel] = self._hash_file(fpath)

        return snapshot

    def _detect_changes(self, old: dict[str, str], new: dict[str, str]) -> list[FileChange]:
        changes = []
        for path, new_hash in new.items():
            if path not in old:
                changes.append(FileChange(path, "added", "", new_hash))
            elif old[path] != new_hash:
                changes.append(FileChange(path, "modified", old[path], new_hash))
        for path in old:
            if path not in new:
                changes.append(FileChange(path, "deleted", old[path], ""))
        return changes

    def _poll_loop(self):
        self._snapshot = self._take_snapshot()
        while not self._stop_event.is_set():
            self._stop_event.wait(self.interval)
            if self._stop_event.is_set():
                break
            new_snapshot = self._take_snapshot()
            changes = self._detect_changes(self._snapshot, new_snapshot)
            if changes:
                self._changes.extend(changes)
                # Keep only last 500 changes
                if len(self._changes) > 500:
                    self._changes = self._changes[-500:]
            self._snapshot = new_snapshot

    def start(self):
        if self._running:
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        self._running = True

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._running = False

    def get_changes(self, since: int = 0) -> list[dict]:
        """Get changes, optionally since a specific index."""
        return [c.to_dict() for c in self._changes[since:]]

    def get_status(self) -> dict:
        return {
            "repo_id": self.repo_id,
            "repo_path": self.repo_path,
            "running": self._running,
            "interval": self.interval,
            "total_files": len(self._snapshot),
            "total_changes": len(self._changes),
        }

    def clear_changes(self):
        self._changes.clear()


def start_watching(repo_id: int, repo_path: str, interval: int = 5) -> dict:
    """Start watching a repository for changes."""
    if repo_id in _watchers:
        _watchers[repo_id].stop()
    watcher = RepoWatcher(repo_id, repo_path, interval)
    watcher.start()
    _watchers[repo_id] = watcher
    return watcher.get_status()


def stop_watching(repo_id: int) -> dict:
    """Stop watching a repository."""
    if repo_id not in _watchers:
        return {"error": "Not watching this repo"}
    _watchers[repo_id].stop()
    status = _watchers[repo_id].get_status()
    del _watchers[repo_id]
    return status


def get_changes(repo_id: int, since: int = 0) -> list[dict]:
    """Get file changes for a watched repository."""
    if repo_id not in _watchers:
        return []
    return _watchers[repo_id].get_changes(since)


def get_watcher_status(repo_id: int) -> dict | None:
    """Get status of a file watcher."""
    if repo_id not in _watchers:
        return None
    return _watchers[repo_id].get_status()


def list_watchers() -> list[dict]:
    """List all active file watchers."""
    return [w.get_status() for w in _watchers.values()]
