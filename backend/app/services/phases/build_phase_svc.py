"""Build Phase wrappers — generate / from-plan for ForgeLoop."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


def _openai_ready() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _generation_ready() -> bool:
    """Gate for the offline stub below. _generate_core (used whenever this
    gate passes) already branches between Anthropic and OpenAI via
    resolve_generation_model() — but this gate only ever checked
    OPENAI_API_KEY, so an Anthropic-only deployment (no OpenAI key at all)
    hit the offline placeholder on every build step instead of calling
    Claude, despite the app's own documented Anthropic-preferred behavior."""
    from app.services.llm.anthropic_client import anthropic_available

    return _openai_ready() or anthropic_available()


def _infer_lang(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cs": "csharp",
        ".rb": "ruby",
    }.get(ext, "text")


def run_build_generate(
    plan_step: str,
    *,
    project_context: str = "",
    tech_stack: str = "",
    file_path: str | None = None,
    repo_id: int | None = None,
    write_to_repo: bool = False,
    workspace: str = "",
    db: Any = None,
    expected_files: list[str] | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Generate code for one plan step. Offline stub writes a marker file when workspace set."""
    expected_files = expected_files or ([file_path] if file_path else [])

    if not _generation_ready():
        target = (expected_files[0] if expected_files else None) or file_path or "generated/upgrade_stub.py"
        code = (
            f"# Mentrix offline build stub\n"
            f"# Plan step: {plan_step[:200]}\n"
            f"def mentrix_upgrade_placeholder():\n"
            f"    \"\"\"Generated without OPENAI_API_KEY — replace in live runs.\"\"\"\n"
            f"    return True\n"
        )
        written: list[str] = []
        root = None
        if write_to_repo and workspace:
            root = Path(workspace)
        elif write_to_repo and repo_id and db is not None:
            from app.models import Repo

            repo = db.query(Repo).filter(Repo.id == repo_id).first()
            if repo and repo.local_path:
                root = Path(repo.local_path)
        if root and root.is_dir():
            out = root / target
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(code, encoding="utf-8")
            written.append(str(target).replace("\\", "/"))
        return {
            "generated_code": code,
            "file_path": target,
            "language": _infer_lang(target),
            "explanation": "Offline Mentrix build stub",
            "model": "offline",
            "tokens_used": 0,
            "files_expected": expected_files or [target],
            "files_written": written,
            "offline": True,
        }

    from app.routers.build_phase import BuildRequest

    req = BuildRequest(
        plan_step=plan_step,
        project_context=project_context or None,
        tech_stack=tech_stack or None,
        file_path=file_path,
        repo_id=repo_id,
        write_to_repo=write_to_repo and bool(repo_id),
    )
    # generate_code expects FastAPI Depends(db) — call core path when possible
    result = _generate_core(req, db=db, workspace=workspace, write_workspace=write_to_repo, user_id=user_id)
    files_written = list(result.get("files_written") or [])
    if write_to_repo and workspace and result.get("file_path") and result.get("generated_code"):
        out = Path(workspace) / result["file_path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result["generated_code"], encoding="utf-8")
        rel = str(result["file_path"]).replace("\\", "/")
        if rel not in files_written:
            files_written.append(rel)
    result["files_expected"] = expected_files or [result.get("file_path")]
    result["files_written"] = files_written
    return result


def _generate_core(
    req: Any, *, db: Any, workspace: str, write_workspace: bool = False, user_id: int | None = None
) -> dict[str, Any]:
    from openai import APIError, OpenAI

    from app.services.llm.anthropic_client import create_fn as anthropic_create_fn
    from app.services.llm.anthropic_client import resolve_generation_model
    from app.token_tracker import log_tokens

    # Prefer Claude Sonnet for generation quality when configured — current
    # benchmarks (SWE-Bench) put it ahead of gpt-4o-mini specifically on
    # real repo-editing tasks. Falls back to the existing OpenAI path
    # untouched when ANTHROPIC_API_KEY isn't set — no regression either way.
    # Set CODEGEN_MODEL to force a specific model (e.g. gpt-5.4) instead.
    use_anthropic, model_name = resolve_generation_model()
    client = None if use_anthropic else OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    context = req.project_context or ""
    if req.repo_id and db is not None and not context:
        from app.services.build_intel.retriever import search as semantic_search

        query = f"{req.plan_step} {req.file_path or ''}".strip()
        hits = semantic_search(db, req.repo_id, query, top_k=6, user_id=user_id)
        if hits:
            context = "\n\n".join(
                f"--- {h['file_path']} (lines {h['line_start']}-{h['line_end']}) ---\n{h['content']}"
                for h in hits
            )
        else:
            from app.routers.llm import _build_repo_context

            context = _build_repo_context(db, req.repo_id, max_chars=4000)

    if not context and db is not None:
        from app.services import context_store

        saved = context_store.load(db, user_id, "blueprint", ["hld_document"])
        if saved.get("hld_document"):
            context = saved["hld_document"][:4000]

    system_prompt = (
        "You are ZECT Mentrix Build Agent. Generate production-ready code for one plan step.\n"
        "Respond in this exact format:\n"
        "FILE_PATH: <suggested file path>\n"
        "LANGUAGE: <programming language>\n"
        "EXPLANATION: <brief explanation>\n"
        "```<language>\n<code>\n```"
    )
    user_content = f"Plan Step: {req.plan_step}"
    if req.tech_stack:
        user_content += f"\nTech Stack: {req.tech_stack}"
    if context:
        user_content += f"\nProject Context: {context[:4000]}"
    if req.file_path:
        user_content += f"\nTarget File: {req.file_path}"

    try:
        from app.services.quality.truncation import complete_with_continuations

        lang_hint = _infer_lang(req.file_path or "") or "python"
        completed = complete_with_continuations(
            client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            model=model_name,
            max_tokens=4000,
            temperature=0.2,
            language_hint=lang_hint,
            create_fn=anthropic_create_fn if use_anthropic else None,
        )
        content = completed["content"]
        tokens = completed["tokens_used"]
        file_path = req.file_path or "generated/output.ts"
        language = "typescript"
        explanation = ""
        code = content
        for line in content.split("\n"):
            if line.startswith("FILE_PATH:"):
                file_path = line.replace("FILE_PATH:", "").strip()
            elif line.startswith("LANGUAGE:"):
                language = line.replace("LANGUAGE:", "").strip().lower()
            elif line.startswith("EXPLANATION:"):
                explanation = line.replace("EXPLANATION:", "").strip()
        if "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                code_block = parts[1]
                code_lines = code_block.split("\n")
                if code_lines and not code_lines[0].strip().startswith(
                    ("import", "from", "const", "let", "var", "def", "class", "package", "#")
                ):
                    code_lines = code_lines[1:]
                code = "\n".join(code_lines).strip()
        log_tokens(
            action="build_generate",
            feature="build_phase",
            model=model_name,
            prompt_tokens=completed.get("prompt_tokens") or 0,
            completion_tokens=completed.get("completion_tokens") or 0,
            total_tokens=tokens,
            user_id=user_id,
        )
        from app.services.build_intel.file_ops import diff_against_existing, write_file

        files_written: list[str] = []
        diff = None
        file_existed = False
        repo_local_path: str | None = None
        if req.repo_id and db is not None:
            from app.models import Repo

            repo = db.query(Repo).filter(Repo.id == req.repo_id).first()
            if repo and repo.local_path:
                repo_local_path = repo.local_path
                file_existed, diff = diff_against_existing(repo.local_path, file_path, code)

        if req.write_to_repo and repo_local_path:
            write_file(repo_local_path, file_path, code)
            files_written.append(file_path)

        out = {
            "generated_code": code,
            "file_path": file_path,
            "language": language,
            "explanation": explanation,
            "model": model_name,
            "tokens_used": tokens,
            "files_written": files_written,
            "offline": False,
            "finish_reason": completed.get("finish_reason"),
            "continuations": completed.get("continuations"),
            "structure_ok": completed.get("structure_ok"),
            "structure_blockers": completed.get("structure_blockers") or [],
            "truncated": bool(completed.get("truncated")),
            "file_existed": file_existed,
            "diff": diff,
        }
        if completed.get("truncated") or not completed.get("structure_ok"):
            out["incomplete"] = True
            out["error"] = "truncated_or_structure:" + ",".join(out["structure_blockers"] or ["length"])
        return out
    except APIError as e:
        return {
            "generated_code": "",
            "file_path": req.file_path or "",
            "language": "text",
            "explanation": f"Build failed: {e.message}",
            "model": "error",
            "tokens_used": 0,
            "files_written": [],
            "offline": True,
            "error": str(e),
        }
    except Exception as e:
        # Anthropic's SDK raises its own exception hierarchy, not openai.APIError —
        # this path is Claude-only when use_anthropic is true, hence the broad catch.
        if not use_anthropic:
            raise
        return {
            "generated_code": "",
            "file_path": req.file_path or "",
            "language": "text",
            "explanation": f"Build failed: {e}",
            "model": "error",
            "tokens_used": 0,
            "files_written": [],
            "offline": True,
            "error": str(e),
        }


def run_build_from_plan(
    full_plan: str,
    *,
    step_index: int = 0,
    tech_stack: str = "",
    project_context: str = "",
    workspace: str = "",
    write_to_repo: bool = False,
    repo_id: int | None = None,
    db: Any = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Parse plan into steps and build the current step."""
    # Lightweight step parse without requiring OpenAI
    headers = re.findall(r"^#{1,3}\s+(.+)$", full_plan or "", re.MULTILINE)
    if headers:
        steps = [{"title": h, "description": h} for h in headers]
    else:
        steps = [{"title": "Implementation", "description": (full_plan or "")[:500]}]
    idx = min(max(step_index, 0), len(steps) - 1)
    current = steps[idx]
    plan_step = f"{current.get('title', '')}: {current.get('description', '')}"
    built = run_build_generate(
        plan_step,
        project_context=project_context,
        tech_stack=tech_stack,
        write_to_repo=write_to_repo,
        workspace=workspace,
        repo_id=repo_id,
        db=db,
        expected_files=[],
        user_id=user_id,
    )
    return {
        "steps": steps,
        "current_step": current,
        "step_index": idx,
        **built,
    }
