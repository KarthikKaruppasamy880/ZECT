from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Desktop Mentrix only — browser must not enable without allowlist root
ALLOWED_ROOT = os.getenv("MENTRIX_FS_ROOT", "")


def execute(tool_name: str, arguments: dict, *, config: dict, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"status": "disabled"}
    root = config.get("root") or ALLOWED_ROOT
    if not root:
        return {
            "status": "not_configured",
            "message": "Set MENTRIX_FS_ROOT for desktop filesystem tools",
            "dry_run": {"tool": tool_name, "arguments": arguments},
        }
    root_path = Path(root).resolve()
    rel = arguments.get("path", ".")
    target = (root_path / rel).resolve()
    if not str(target).startswith(str(root_path)):
        raise PermissionError("Path escapes MENTRIX_FS_ROOT")
    if tool_name == "read_file":
        return {"path": str(target), "content": target.read_text(encoding="utf-8", errors="ignore")[:100000]}
    if tool_name == "list_dir":
        entries = [{"name": p.name, "is_dir": p.is_dir()} for p in sorted(target.iterdir())[:500]]
        return {"path": str(target), "entries": entries}
    if tool_name == "write_file":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(arguments.get("content", ""), encoding="utf-8")
        return {"path": str(target), "bytes": len(arguments.get("content", ""))}
    return {"status": "unknown_tool", "tool": tool_name}
