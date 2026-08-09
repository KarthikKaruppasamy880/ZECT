"""ArtifactStore — canonical on-disk owner of PLAN.md / manifest / evidence per WorkItem."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


ARTIFACT_NAMES = (
    "PLAN.md",
    "REQUIREMENTS.md",
    "ACCEPTANCE.md",
    "RISKS.md",
    "EXECUTION_MANIFEST.json",
    "EXECUTION_STATE.json",
    "EVIDENCE.json",
)


def _repo_root() -> Path:
    # backend/app/services/work_items/artifact_store.py → repo root
    return Path(__file__).resolve().parents[4]


def work_item_dir(work_item_id: int, *, root: Path | None = None) -> Path:
    base = root or Path(os.getenv("ZECT_ARTIFACT_ROOT") or (_repo_root() / ".zect" / "work"))
    return Path(base) / str(work_item_id)


def ensure_store(work_item_id: int, *, root: Path | None = None) -> Path:
    d = work_item_dir(work_item_id, root=root)
    d.mkdir(parents=True, exist_ok=True)
    return d


def plan_hash_bytes(content: str) -> str:
    normalized = content.replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


class ArtifactStore:
    """Canonical PLAN.md owner for a WorkItem."""

    def __init__(self, work_item_id: int, *, root: Path | None = None) -> None:
        self.work_item_id = work_item_id
        self.root = ensure_store(work_item_id, root=root)

    def path(self, name: str) -> Path:
        if name not in ARTIFACT_NAMES and ".." in name:
            raise ValueError(f"invalid artifact name: {name}")
        return self.root / name

    def write_text(self, name: str, content: str) -> Path:
        p = self.path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def read_text(self, name: str, default: str = "") -> str:
        p = self.path(name)
        if not p.exists():
            return default
        return p.read_text(encoding="utf-8")

    def write_json(self, name: str, data: Any) -> Path:
        return self.write_text(name, json.dumps(data, indent=2, default=str) + "\n")

    def read_json(self, name: str, default: Any = None) -> Any:
        raw = self.read_text(name, default="")
        if not raw.strip():
            return default if default is not None else {}
        return json.loads(raw)

    def write_plan(self, content: str) -> dict[str, str]:
        self.write_text("PLAN.md", content)
        h = plan_hash_bytes(content)
        return {"path": str(self.path("PLAN.md")), "plan_hash": h}

    def read_plan(self) -> str:
        return self.read_text("PLAN.md", "")

    def plan_hash(self) -> str:
        return plan_hash_bytes(self.read_plan()) if self.path("PLAN.md").exists() else ""
