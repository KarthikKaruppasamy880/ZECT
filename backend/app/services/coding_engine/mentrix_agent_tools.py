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
    {
        "type": "function",
        "function": {
            "name": "git_pull",
            "description": "Fast-forward only git pull in this workspace. Marks Lattice STALE. Never starts a coding mission.",
            "parameters": {
                "type": "object",
                "properties": {"remote": {"type": "string", "description": "Remote name (default origin)"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_checkout",
            "description": "Checkout a branch only inside an isolated git worktree. Refused on the live clone.",
            "parameters": {
                "type": "object",
                "properties": {"branch": {"type": "string"}},
                "required": ["branch"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_pr_worktree",
            "description": "Create or reuse an isolated worktree for a later PR. Does not git checkout the live clone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {"type": "integer"},
                    "pr_number": {"type": "integer"},
                    "head_branch": {"type": "string"},
                    "head_sha": {"type": "string"},
                },
                "required": ["repo_id", "pr_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_app",
            "description": (
                "Start this workspace's application in the background. If command is omitted, "
                "discovers the real start command from package.json/pyproject/etc instead of "
                "guessing -- if more than one candidate exists, returns candidates for you to "
                "choose from (call again with an explicit command)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Optional explicit start command"},
                    "recipe_id": {"type": "string", "description": "Optional discovered recipe id to use"},
                    "label": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restart_app",
            "description": (
                "Restart the app. If process_id is given, restarts ONLY that one "
                "already-tracked process (the affected service) with its original "
                "command/cwd, leaving any other process this mission started "
                "untouched. Without process_id, stops every process this mission "
                "started in this workspace, then starts it again (whole-workspace restart)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "process_id": {"type": "string", "description": "Restart only this tracked process (affected-service restart)"},
                    "command": {"type": "string", "description": "Optional explicit start command"},
                    "recipe_id": {"type": "string"},
                    "label": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_app",
            "description": "Stop every process this mission started in this workspace. Never touches unrelated ports/processes.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "health_check",
            "description": "Poll a port until it accepts connections and answers HTTP, bounded by timeout_s.",
            "parameters": {
                "type": "object",
                "properties": {
                    "port": {"type": "integer"},
                    "path": {"type": "string", "description": "HTTP path to probe, default /"},
                    "timeout_s": {"type": "number", "description": "Max seconds to wait, default 20"},
                },
                "required": ["port"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_navigate",
            "description": "Open a URL in a real browser and capture console errors + failed network requests.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_snapshot",
            "description": "Get the visible text of the current/given page plus console+network evidence.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click an element by CSS selector (optionally navigating to url first).",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}, "selector": {"type": "string"}},
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_type",
            "description": "Type text into a form field by CSS selector (optionally navigating to url first). Never used on password fields.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "selector": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["selector", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_select",
            "description": "Choose an <select> option by value (optionally navigating to url first).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "selector": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["selector", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": "Take a screenshot (optionally navigating to url first). Saved to workspace evidence; returns its relative path.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}, "full_page": {"type": "boolean"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_wait_for",
            "description": "Wait for an element's state (default visible) or a fixed time if no selector given.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "selector": {"type": "string"},
                    "state": {"type": "string", "description": "visible|hidden|attached|detached"},
                    "timeout_ms": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_assert_text",
            "description": "Assert an element (default body) contains expected text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "selector": {"type": "string"},
                    "expected": {"type": "string"},
                },
                "required": ["expected"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_assert_visible",
            "description": "Assert an element by CSS selector is visible.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}, "selector": {"type": "string"}},
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_console_errors",
            "description": "Return console errors/warnings observed on the given (or current) page.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_network_failures",
            "description": "Return failed requests and HTTP 4xx/5xx responses observed on the given (or current) page.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
            },
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
            # Pin child PYTHONPATH to this workspace so nested pytest cannot
            # import a sibling worktree's modules (CI pytest 9 / Linux).
            child_env["PYTHONPATH"] = str(root)
            if "pytest" in cmd:
                child_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
                child_env["PYTEST_ADDOPTS"] = ""
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

    if name == "git_pull":
        from app.services.coding_engine.sync_pull import ff_pull_root

        return ff_pull_root(str(root), remote=str(args.get("remote") or "origin"))

    if name == "git_checkout":
        git_meta = root / ".git"
        if git_meta.is_dir():
            return {
                "ok": False,
                "error": "refused_live_clone_checkout",
                "hint": "Use open_pr_worktree so the live ZOAS/ZAF clone stays on its current branch.",
            }
        branch = str(args.get("branch") or "").strip()
        if not branch:
            return {"ok": False, "error": "branch_required"}
        try:
            completed = subprocess.run(
                ["git", "checkout", "--", branch] if False else ["git", "checkout", branch],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return {
            "ok": completed.returncode == 0,
            "branch": branch,
            "stdout": (completed.stdout or "")[-1500:],
            "stderr": (completed.stderr or "")[-800:],
        }

    if name == "open_pr_worktree":
        try:
            repo_id = int(args.get("repo_id") or 0)
            pr_number = int(args.get("pr_number") or 0)
        except (TypeError, ValueError):
            return {"ok": False, "error": "repo_id_and_pr_number_required"}
        if repo_id <= 0 or pr_number <= 0:
            return {"ok": False, "error": "repo_id_and_pr_number_required"}
        head = str(args.get("head_branch") or "").strip()
        sha = str(args.get("head_sha") or "").strip()
        try:
            from app.infrastructure.database import SessionLocal
            from app.services.repo_onboarding import ensure_pr_worktree
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"pr_worktree_unavailable:{exc}"}
        db = SessionLocal()
        try:
            out = ensure_pr_worktree(
                db,
                repo_id=repo_id,
                pr_number=pr_number,
                head_branch=head,
                head_sha=sha,
            )
            out = dict(out or {})
            out.setdefault("ok", True)
            out["main_unchanged"] = True
            return out
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        finally:
            db.close()

    if name in ("start_app", "restart_app"):
        from app.domains.workspace.app_runner import (
            restart_owned_process,
            spawn_owned_process,
            stop_owned_processes_in_workspace,
        )
        from app.services.workspace.runtime_discovery import (
            discover_runtime_recipes,
            resolve_recipe,
            save_confirmed_profile,
        )

        # Affected-service restart: given an already-tracked process_id, stop
        # and re-spawn exactly that one process with its original command/cwd
        # -- never touches any other service this (or another) workspace owns.
        # Falls through to the discover/spawn path below only when no
        # process_id is given, preserving the prior whole-workspace behavior.
        restart_process_id = str(args.get("process_id") or "").strip()
        if name == "restart_app" and restart_process_id:
            info = restart_owned_process(restart_process_id)
            if info is None:
                return {"ok": False, "error": f"unknown_process_id:{restart_process_id}"}
            return {"ok": True, "process_id": info.id, "pid": info.pid, "label": info.label, "restarted": True}

        if name == "restart_app":
            stop_owned_processes_in_workspace(str(root))

        command = str(args.get("command") or "").strip()
        recipe_id = str(args.get("recipe_id") or "").strip()
        cwd = str(root)
        chosen: dict[str, Any] | None = None
        if not command:
            discovered = discover_runtime_recipes(str(root))
            recipes = list(discovered.get("recipes") or [])
            if recipe_id:
                chosen = next((r for r in recipes if r.get("id") == recipe_id), None)
                if not chosen:
                    return {"ok": False, "error": f"unknown_recipe_id:{recipe_id}"}
            elif not recipes:
                return {"ok": False, "error": "no_start_command_discovered"}
            elif len(recipes) == 1:
                # Only one real candidate -- nothing to disambiguate. Every
                # discovered recipe carries confirmRequired for the human-UI
                # picker elsewhere; within an already-approved mission this
                # tool loop already runs shell commands via run_command at
                # the same trust level, so a single unambiguous recipe here
                # is not a new risk tier.
                chosen = recipes[0]
            else:
                return {
                    "ok": False,
                    "needs_recipe_choice": True,
                    "candidates": recipes,
                    "default_id": discovered.get("default_id"),
                    "hint": "Call start_app again with recipe_id or an explicit command.",
                }
            resolved = resolve_recipe(str(root), chosen["id"])
            command = chosen.get("command") or ""
            cwd = resolved.get("cwd") or str(root)
            if not command:
                return {"ok": False, "error": "recipe_has_no_command"}

        label = str(args.get("label") or "").strip()
        try:
            info = spawn_owned_process(command, cwd, label=label)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"start_failed:{exc}"}
        if chosen is not None:
            # Remember the confirmed choice so the next start_app call on
            # this repo doesn't have to re-discover/re-disambiguate.
            save_confirmed_profile(str(root), chosen)
        return {
            "ok": True,
            "process_id": info.id,
            "pid": info.pid,
            "label": info.label,
            "command": command,
            "cwd": cwd,
        }

    if name == "stop_app":
        from app.domains.workspace.app_runner import stop_owned_processes_in_workspace

        stopped = stop_owned_processes_in_workspace(str(root))
        return {"ok": True, "stopped": stopped}

    if name == "health_check":
        from app.services.workspace.health_check import wait_for_port_healthy

        try:
            port = int(args.get("port"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "port_required"}
        result = wait_for_port_healthy(
            "127.0.0.1",
            port,
            path=str(args.get("path") or "/"),
            timeout_s=float(args.get("timeout_s") or 20.0),
        )
        return {"ok": bool(result.get("ok")), **result}

    _BROWSER_TOOL_MAP = {
        "browser_navigate": "navigate",
        "browser_snapshot": "snapshot",
        "browser_click": "click",
        "browser_type": "fill",
        "browser_select": "select_option",
        "browser_screenshot": "screenshot",
        "browser_wait_for": "wait_for",
        "browser_assert_text": "assert_text",
        "browser_assert_visible": "assert_visible",
        "browser_console_errors": "console_errors",
        "browser_network_failures": "network_failures",
    }
    if name in _BROWSER_TOOL_MAP:
        from app.services.browser.runtime import get_browser_runtime

        out = get_browser_runtime().run(_BROWSER_TOOL_MAP[name], dict(args))
        if name == "browser_screenshot" and isinstance(out.get("png_bytes"), (bytes, bytearray)):
            import base64
            import uuid as _uuid

            shots_dir = root / ".zect" / "evidence" / "screenshots"
            shots_dir.mkdir(parents=True, exist_ok=True)
            fname = f"{_uuid.uuid4().hex[:12]}.png"
            (shots_dir / fname).write_bytes(out["png_bytes"])
            out = {k: v for k, v in out.items() if k != "png_bytes"}
            out["screenshot_path"] = f".zect/evidence/screenshots/{fname}"
            out["screenshot_preview_b64"] = base64.b64encode(
                (shots_dir / fname).read_bytes()[:2000]
            ).decode("ascii")
        return {"ok": out.get("status") == "ok", **out}

    return {"ok": False, "error": f"unknown_tool:{name}"}
