"""Mentrix Coding Agent tools — path-jailed workspace primitives."""

from __future__ import annotations

import difflib
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from app.infrastructure.allowed_paths import path_under_allowed_roots
from app.services.build_intel.file_ops import safe_resolve_target, write_file

# Destructive shell patterns — require explicit approval even in auto-edit mode
_DESTRUCTIVE_CMD = re.compile(
    r"\b(rm\s+-rf|del\s+/[sf]|format\s+|rmdir\s+/s|git\s+push|git\s+reset\s+--hard|"
    r"Remove-Item\s+.*-Recurse|drop\s+table|truncate\s+table)\b",
    re.I,
)

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories under a relative path in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path (default '.')"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the workspace (relative path).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_chars": {"type": "integer", "description": "Max characters to return (default 12000)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search workspace text for a pattern (simple recursive grep).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "glob": {"type": "string", "description": "Optional filename substring filter"},
                    "max_hits": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with full contents (relative path).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": "Replace an exact old_text span with new_text in an existing file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command with cwd = workspace root. Prefer tests/linters over destructive ops.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "git status --short in the workspace.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "git diff (optional path) in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Commit workspace changes. Always requires approval. Never auto-merge.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_push",
            "description": "Push current branch to origin. Always requires approval. Unset GitHub is BLOCKED_EXTERNAL.",
            "parameters": {"type": "object", "properties": {"branch": {"type": "string"}}},
        },
    },
]


def resolve_workspace(workspace: str) -> Path:
    raw = (workspace or "").strip()
    if not raw:
        raise ValueError("workspace path required for Mentrix Coding Agent")
    return path_under_allowed_roots(raw)


def command_needs_approval(command: str) -> bool:
    return bool(_DESTRUCTIVE_CMD.search(command or ""))


def _rel(root: Path, target: Path) -> str:
    try:
        return str(target.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(target)


def execute_tool(
    name: str,
    args: dict[str, Any],
    *,
    workspace: Path,
    auto_approve_edits: bool = True,
) -> dict[str, Any]:
    """Execute one Mentrix Coding Agent tool. May return needs_approval=True."""
    try:
        return _execute_tool_inner(name, args, workspace=workspace, auto_approve_edits=auto_approve_edits)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}


def _execute_tool_inner(
    name: str,
    args: dict[str, Any],
    *,
    workspace: Path,
    auto_approve_edits: bool = True,
) -> dict[str, Any]:
    root = workspace.resolve()
    args = args or {}

    if name == "list_dir":
        rel = (args.get("path") or ".").strip() or "."
        target = safe_resolve_target(str(root), rel)
        if not target.is_dir():
            return {"ok": False, "error": f"not_a_directory:{rel}"}
        entries = []
        for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:200]:
            entries.append({"name": child.name, "is_dir": child.is_dir(), "path": _rel(root, child)})
        return {"ok": True, "entries": entries}

    if name == "read_file":
        rel = str(args.get("path") or "").strip()
        if not rel:
            return {"ok": False, "error": "path_required"}
        target = safe_resolve_target(str(root), rel)
        if not target.is_file():
            return {"ok": False, "error": f"not_found:{rel}"}
        max_chars = int(args.get("max_chars") or 12000)
        text = target.read_text(encoding="utf-8", errors="replace")
        truncated = len(text) > max_chars
        return {
            "ok": True,
            "path": rel.replace("\\", "/"),
            "content": text[:max_chars],
            "truncated": truncated,
            "bytes": target.stat().st_size,
        }

    if name == "search_code":
        query = str(args.get("query") or "")
        if not query:
            return {"ok": False, "error": "query_required"}
        glob_f = str(args.get("glob") or "").strip().lower()
        max_hits = min(int(args.get("max_hits") or 40), 80)
        hits: list[dict[str, Any]] = []
        skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
            for fn in filenames:
                if glob_f and glob_f not in fn.lower():
                    continue
                fp = Path(dirpath) / fn
                try:
                    if fp.stat().st_size > 800_000:
                        continue
                    text = fp.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if query in line:
                        hits.append(
                            {
                                "path": _rel(root, fp),
                                "line": i,
                                "text": line[:240],
                            }
                        )
                        if len(hits) >= max_hits:
                            return {"ok": True, "hits": hits, "capped": True}
        return {"ok": True, "hits": hits, "capped": False}

    if name == "write_file":
        rel = str(args.get("path") or "").strip()
        content = args.get("content")
        if not rel or content is None:
            return {"ok": False, "error": "path_and_content_required"}
        if not auto_approve_edits:
            return {
                "ok": False,
                "needs_approval": True,
                "action": "write_file",
                "args": {"path": rel, "content": content},
                "summary": f"Write {rel} ({len(str(content))} chars)",
            }
        before = ""
        target_preview = safe_resolve_target(str(root), rel)
        if target_preview.is_file():
            before = target_preview.read_text(encoding="utf-8", errors="replace")
        # Optional ZECT Security Agent scan-on-write (fail closed only when engine ready + infected)
        try:
            from app.adapters.detection_malware import (
                malware_engine_status,
                malware_scan_writes_enabled,
                scan_file,
            )

            if malware_scan_writes_enabled() and malware_engine_status().get("ready"):
                import tempfile

                Path(root / ".zect").mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    delete=False,
                    dir=str(root / ".zect"),
                    suffix=".scan",
                ) as tmp:
                    tmp.write(str(content))
                    tmp_path = tmp.name
                try:
                    scanned = scan_file(tmp_path)
                    if scanned.get("infected"):
                        return {
                            "ok": False,
                            "error": "malware_blocked",
                            "provider": "zect_security_agent",
                            "signature": scanned.get("signature"),
                        }
                finally:
                    try:
                        Path(tmp_path).unlink(missing_ok=True)
                    except Exception:  # noqa: BLE001
                        pass
        except Exception:  # noqa: BLE001
            pass
        write_file(str(root), rel, str(content))
        diff = "\n".join(
            difflib.unified_diff(
                before.splitlines(),
                str(content).splitlines(),
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
                lineterm="",
            )
        )
        return {
            "ok": True,
            "path": rel.replace("\\", "/"),
            "written": True,
            "diff": diff[:8000],
            "file_diff": True,
        }

    if name == "apply_patch":
        rel = str(args.get("path") or "").strip()
        old = args.get("old_text")
        new = args.get("new_text")
        if not rel or old is None or new is None:
            return {"ok": False, "error": "path_old_new_required"}
        target = safe_resolve_target(str(root), rel)
        if not target.is_file():
            return {"ok": False, "error": f"not_found:{rel}"}
        before = target.read_text(encoding="utf-8", errors="replace")
        if str(old) not in before:
            return {"ok": False, "error": "old_text_not_found"}
        if not auto_approve_edits:
            return {
                "ok": False,
                "needs_approval": True,
                "action": "apply_patch",
                "args": {"path": rel, "old_text": old, "new_text": new},
                "summary": f"Patch {rel}",
            }
        after = before.replace(str(old), str(new), 1)
        write_file(str(root), rel, after)
        diff = "\n".join(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
                lineterm="",
            )
        )
        return {
            "ok": True,
            "path": rel.replace("\\", "/"),
            "patched": True,
            "diff": diff[:8000],
            "file_diff": True,
        }

    if name == "run_command":
        cmd = str(args.get("command") or "").strip()
        if not cmd:
            return {"ok": False, "error": "command_required"}
        if command_needs_approval(cmd) or not auto_approve_edits:
            return {
                "ok": False,
                "needs_approval": True,
                "action": "run_command",
                "args": {"command": cmd, "timeout": int(args.get("timeout") or 60)},
                "summary": f"Run: {cmd[:120]}",
            }
        timeout = min(int(args.get("timeout") or 60), 180)
        try:
            child_env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST")}
            completed = subprocess.run(
                cmd,
                shell=True,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=child_env,
            )
            out = (completed.stdout or "")[-6000:]
            err = (completed.stderr or "")[-2000:]
            return {
                "ok": completed.returncode == 0,
                "exit_code": completed.returncode,
                "stdout": out,
                "stderr": err,
                "command": cmd,
                "command_output": True,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"timeout_after_{timeout}s", "command": cmd}

    if name == "git_status":
        try:
            completed = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return {"ok": completed.returncode == 0, "status": completed.stdout or "", "stderr": completed.stderr or ""}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    if name == "git_diff":
        cmd = ["git", "diff"]
        rel = str(args.get("path") or "").strip()
        if rel:
            safe_resolve_target(str(root), rel)
            cmd.append("--")
            cmd.append(rel)
        try:
            completed = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=30)
            return {
                "ok": completed.returncode == 0,
                "diff": (completed.stdout or "")[:12000],
                "stderr": completed.stderr or "",
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    if name == "git_commit":
        if not args.pop("_approved", False):
            return {
                "ok": False,
                "needs_approval": True,
                "action": "git_commit",
                "args": {"message": str(args.get("message") or "zect coding-agent")},
                "summary": "git commit (never auto-merge)",
            }
        from app.services.coding_engine.lifecycle import _commit_if_needed

        fake = {"worktree_path": str(root), "committed_shas": []}
        return _commit_if_needed(fake, str(args.get("message") or "zect coding-agent"))

    if name == "git_push":
        if not args.pop("_approved", False):
            return {
                "ok": False,
                "needs_approval": True,
                "action": "git_push",
                "args": {"branch": str(args.get("branch") or "")},
                "summary": "git push (BLOCKED_EXTERNAL without GitHub)",
            }
        from app.services.coding_engine.lifecycle import _push_or_block

        fake = {
            "worktree_path": str(root),
            "branch": str(args.get("branch") or ""),
            "head_sha": "",
        }
        return _push_or_block(fake)

    return {"ok": False, "error": f"unknown_tool:{name}"}
