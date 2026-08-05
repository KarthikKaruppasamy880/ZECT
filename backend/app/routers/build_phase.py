"""Build Phase — Full AI code generation from plan steps."""

import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from openai import OpenAI, APIError
from app.infrastructure.auth.deps import CurrentUser, get_current_user
from app.infrastructure.auth.rbac import log_audit
from app.infrastructure.budget import enforce_token_budget
from app.infrastructure.database import get_db
from app.models import Repo
from app.token_tracker import log_tokens

router = APIRouter(prefix="/api/build", tags=["build"])


def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")
    return OpenAI(api_key=key)


def _parse_multi_file_response(content: str) -> list[dict]:
    """Parse the ===FILE: <path>=== ... ===END FILE=== repeating format the
    multi-file system prompt asks the model to use."""
    import re

    blocks = re.split(r"===FILE:\s*(.+?)\s*===", content)
    results: list[dict] = []
    # blocks[0] is any preamble before the first marker — discard. Remaining
    # entries alternate [file_path, body, file_path, body, ...].
    for i in range(1, len(blocks), 2):
        file_path = blocks[i].strip()
        body = blocks[i + 1] if i + 1 < len(blocks) else ""
        body = body.split("===END FILE===")[0]

        language = "text"
        explanation = ""
        for line in body.split("\n"):
            if line.startswith("LANGUAGE:"):
                language = line.replace("LANGUAGE:", "").strip().lower()
            elif line.startswith("EXPLANATION:"):
                explanation = line.replace("EXPLANATION:", "").strip()

        code = body
        if "```" in body:
            parts = body.split("```")
            if len(parts) >= 2:
                code_block = parts[1]
                code_lines = code_block.split("\n")
                if code_lines and not code_lines[0].strip().startswith(
                    ("import", "from", "const", "let", "var", "def", "class", "package", "#")
                ):
                    code_lines = code_lines[1:]
                code = "\n".join(code_lines).strip()

        results.append({
            "file_path": file_path, "language": language,
            "explanation": explanation, "generated_code": code,
        })
    return results


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class BuildRequest(BaseModel):
    plan_step: str
    project_context: str | None = None
    tech_stack: str | None = None
    file_path: str | None = None
    repo_id: int | None = None  # auto-inject context from cloned repo
    write_to_repo: bool = False  # write generated code to the cloned repo


class BuildResponse(BaseModel):
    generated_code: str
    file_path: str
    language: str
    explanation: str
    model: str
    tokens_used: int
    file_existed: bool = False
    diff: dict | None = None  # unified + side_by_side + stats, only when file_existed
    rule_violations: list[dict] = []  # free deterministic pre-check, before any human review


class MultiFileBuildRequest(BaseModel):
    plan_step: str
    target_files: list[str]  # explicit set of files this step should touch together
    tech_stack: str | None = None
    repo_id: int | None = None
    project_context: str | None = None


class FileChange(BaseModel):
    file_path: str
    language: str
    generated_code: str
    explanation: str
    file_existed: bool = False
    diff: dict | None = None
    rule_violations: list[dict] = []


class MultiFileBuildResponse(BaseModel):
    files: list[FileChange]
    model: str
    tokens_used: int


MAX_MULTI_FILE_TARGETS = 8  # bound cost/latency of one coordinated generation call


class ApplyFileEntry(BaseModel):
    file_path: str
    code: str


class ApplyMultiRequest(BaseModel):
    repo_id: int
    files: list[ApplyFileEntry]
    commit_message: str | None = None  # if set, one checkpoint commit covering all files


class ApplyMultiResponse(BaseModel):
    written: list[str]
    committed: bool = False
    commit_warning: str | None = None


class VerifyAndFixRequest(BaseModel):
    repo_id: int
    test_command: str
    max_retries: int = 3


class ApplyRequest(BaseModel):
    repo_id: int
    file_path: str
    code: str
    commit_message: str | None = None  # if set, checkpoints the write as a real git commit


class ApplyResponse(BaseModel):
    written: bool
    file_path: str
    committed: bool = False
    commit_warning: str | None = None  # e.g. git_ops's path allowlist rejected this workspace


class BuildFromPlanRequest(BaseModel):
    full_plan: str
    step_index: int = 0
    tech_stack: str | None = None
    project_context: str | None = None


class BuildFromPlanResponse(BaseModel):
    steps: list[dict]
    current_step: dict
    generated_code: str
    file_path: str
    language: str
    explanation: str
    model: str
    tokens_used: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=BuildResponse)
def generate_code(
    req: BuildRequest,
    current_user: CurrentUser = Depends(enforce_token_budget),
    db: Session = Depends(get_db),
):
    """Generate code for a single plan step."""
    from app.services.llm.anthropic_client import create_fn as anthropic_create_fn
    from app.services.llm.anthropic_client import resolve_generation_model

    use_anthropic, model_name = resolve_generation_model()
    client = None if use_anthropic else _get_client()

    # Auto-inject repo context if repo_id provided — prefer semantic retrieval
    # over the repo (chunked + embedded, scoped to this plan step) once an
    # index exists; fall back to the old static snapshot if it doesn't yet.
    if req.repo_id and not req.project_context:
        repo = db.query(Repo).filter(Repo.id == req.repo_id).first()
        if repo and repo.clone_status == "cloned" and repo.local_path:
            from app.services.build_intel.retriever import search as semantic_search

            query = f"{req.plan_step} {req.file_path or ''}".strip()
            hits = semantic_search(db, req.repo_id, query, top_k=6, user_id=current_user.user_id)
            if hits:
                req.project_context = "\n\n".join(
                    f"--- {h['file_path']} (lines {h['line_start']}-{h['line_end']}) ---\n{h['content']}"
                    for h in hits
                )
            else:
                from app.routers.llm import _build_repo_context
                req.project_context = _build_repo_context(db, req.repo_id, max_chars=4000)

    system_prompt = (
        "You are ZECT AI Build Agent — an expert code generator. Given a plan step, "
        "generate production-ready code. Follow best practices:\n"
        "- Clean, well-structured code with proper error handling\n"
        "- Include type annotations and docstrings\n"
        "- Follow SOLID principles\n"
        "- Include necessary imports\n"
        "- Add inline comments for complex logic\n\n"
        "Respond in this exact format:\n"
        "FILE_PATH: <suggested file path>\n"
        "LANGUAGE: <programming language>\n"
        "EXPLANATION: <brief explanation of what this code does>\n"
        "```<language>\n<code>\n```"
    )

    user_content = f"Plan Step: {req.plan_step}"
    if req.tech_stack:
        user_content += f"\nTech Stack: {req.tech_stack}"
    if req.project_context:
        user_content += f"\nProject Context: {req.project_context[:4000]}"
    if req.file_path:
        user_content += f"\nTarget File: {req.file_path}"

    try:
        from app.services.quality.truncation import complete_with_continuations

        completed = complete_with_continuations(
            client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            model=model_name,
            max_tokens=4000,
            temperature=0.2,
            language_hint="python",
            create_fn=anthropic_create_fn if use_anthropic else None,
        )
        content = completed["content"]
        tokens = completed["tokens_used"]

        # Parse response
        file_path = "generated/output.ts"
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

        # Extract code block
        if "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                code_block = parts[1]
                # Remove language identifier from first line
                code_lines = code_block.split("\n")
                if code_lines and not code_lines[0].strip().startswith(("import", "from", "const", "let", "var", "def", "class", "package", "#")):
                    code_lines = code_lines[1:]
                code = "\n".join(code_lines).strip()

        log_tokens(
            action="build_generate",
            feature="build_phase",
            model=model_name,
            prompt_tokens=completed.get("prompt_tokens") or 0,
            completion_tokens=completed.get("completion_tokens") or 0,
            total_tokens=tokens,
            user_id=current_user.user_id,
        )

        # Diff against the existing file when there is one — informational,
        # doesn't change write_to_repo's existing behavior below. Lets the UI
        # show what would change and offer a review-before-write path via
        # POST /api/build/apply instead of only ever overwriting blind.
        from app.services.build_intel.file_ops import check_rule_violations, diff_against_existing, write_file

        file_existed = False
        diff = None
        repo_local_path: str | None = None
        if req.repo_id and file_path:
            repo = db.query(Repo).filter(Repo.id == req.repo_id).first()
            if repo and repo.clone_status == "cloned" and repo.local_path:
                repo_local_path = repo.local_path
                file_existed, diff = diff_against_existing(repo.local_path, file_path, code)

        # Phase 5: Write generated code to cloned repo if requested
        if req.write_to_repo and repo_local_path:
            write_file(repo_local_path, file_path, code)

        rule_violations = check_rule_violations(db, code, language)

        return BuildResponse(
            generated_code=code,
            file_path=file_path,
            language=language,
            explanation=explanation,
            model=model_name,
            tokens_used=tokens,
            file_existed=file_existed,
            diff=diff,
            rule_violations=rule_violations,
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")
    except Exception as e:
        if not use_anthropic:
            raise
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {e}")


@router.post("/apply", response_model=ApplyResponse)
def apply_generated_code(
    req: ApplyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Write previously-generated code to disk after human review of the diff.

    This is the only way /generate's output reaches disk when write_to_repo
    wasn't set — review-then-apply, not generate-and-overwrite. Optionally
    checkpoints the write as a real git commit (reuses git_ops.py's git_commit
    exactly as-is, including its existing path-allowlist check — not bypassed).
    """
    from app.services.build_intel.file_ops import write_file

    repo = db.query(Repo).filter(Repo.id == req.repo_id).first()
    if not repo or repo.clone_status != "cloned" or not repo.local_path:
        raise HTTPException(status_code=400, detail="Repo is not cloned")

    try:
        write_file(repo.local_path, req.file_path, req.code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="build_apply",
        resource_id=req.repo_id,
        resource_type="repo",
        details={"file_path": req.file_path, "bytes": len(req.code)},
    )

    committed = False
    commit_warning = None
    if req.commit_message:
        from app.routers.git_ops import GitCommitRequest, git_commit

        try:
            result = git_commit(GitCommitRequest(
                repo_path=repo.local_path, message=req.commit_message, files=[req.file_path],
            ))
            committed = result.get("status") == "committed"
            if not committed:
                commit_warning = result.get("message", "commit did not complete")
        except HTTPException as e:
            # Don't fail the whole apply over a checkpoint failure — the file
            # write above already succeeded and is the primary action.
            commit_warning = str(e.detail)

    return ApplyResponse(
        written=True, file_path=req.file_path, committed=committed, commit_warning=commit_warning,
    )


@router.post("/generate-multi", response_model=MultiFileBuildResponse)
def generate_multi_file(
    req: MultiFileBuildRequest,
    current_user: CurrentUser = Depends(enforce_token_budget),
    db: Session = Depends(get_db),
):
    """Generate coordinated changes across multiple files for one plan step in
    a single model call — the model sees all target files together so imports,
    signatures, and naming stay consistent across them, unlike calling
    /generate independently per file with no awareness of the others."""
    if not req.target_files:
        raise HTTPException(status_code=400, detail="target_files must not be empty")
    if len(req.target_files) > MAX_MULTI_FILE_TARGETS:
        raise HTTPException(status_code=400, detail=f"target_files exceeds the {MAX_MULTI_FILE_TARGETS}-file limit per call")

    from app.services.llm.anthropic_client import create_fn as anthropic_create_fn
    from app.services.llm.anthropic_client import resolve_generation_model

    use_anthropic, model_name = resolve_generation_model()
    client = None if use_anthropic else _get_client()

    project_context = req.project_context
    if req.repo_id and not project_context:
        from app.services.build_intel.retriever import search as semantic_search

        seen: set[tuple[str, int]] = set()
        parts: list[str] = []
        for target_file in req.target_files:
            hits = semantic_search(db, req.repo_id, f"{req.plan_step} {target_file}", top_k=4, user_id=current_user.user_id)
            for h in hits:
                key = (h["file_path"], h["line_start"])
                if key in seen:
                    continue
                seen.add(key)
                parts.append(f"--- {h['file_path']} (lines {h['line_start']}-{h['line_end']}) ---\n{h['content']}")
        if parts:
            project_context = "\n\n".join(parts)
        else:
            from app.routers.llm import _build_repo_context
            project_context = _build_repo_context(db, req.repo_id, max_chars=4000)

    system_prompt = (
        "You are ZECT AI Build Agent — an expert code generator. Generate production-ready code for "
        "ALL of the listed files as ONE coordinated change for a single plan step. Keep the files "
        "consistent with each other: matching function signatures, shared imports, consistent naming.\n"
        f"Files to generate, in this order: {', '.join(req.target_files)}\n\n"
        "Respond with EACH file in this exact repeating block, one per file, in the order listed:\n"
        "===FILE: <path>===\n"
        "LANGUAGE: <language>\n"
        "EXPLANATION: <brief explanation>\n"
        "```<language>\n<code>\n```\n"
        "===END FILE==="
    )
    user_content = f"Plan Step: {req.plan_step}"
    if req.tech_stack:
        user_content += f"\nTech Stack: {req.tech_stack}"
    if project_context:
        user_content += f"\nProject Context: {project_context[:6000]}"

    try:
        from app.services.quality.truncation import complete_with_continuations

        completed = complete_with_continuations(
            client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            model=model_name,
            max_tokens=min(4000 * len(req.target_files), 16000),
            temperature=0.2,
            language_hint="text",  # mixed languages across files — skip the single-language structural check
            create_fn=anthropic_create_fn if use_anthropic else None,
        )
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e.message}")
    except Exception as e:
        if not use_anthropic:
            raise
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {e}")

    tokens = completed["tokens_used"]
    log_tokens(
        action="build_generate_multi",
        feature="build_phase",
        model=model_name,
        prompt_tokens=completed.get("prompt_tokens") or 0,
        completion_tokens=completed.get("completion_tokens") or 0,
        total_tokens=tokens,
        user_id=current_user.user_id,
    )

    from app.services.build_intel.file_ops import check_rule_violations, diff_against_existing

    parsed = _parse_multi_file_response(completed["content"])
    repo = db.query(Repo).filter(Repo.id == req.repo_id).first() if req.repo_id else None
    repo_local_path = repo.local_path if repo and repo.clone_status == "cloned" and repo.local_path else None

    files: list[FileChange] = []
    for entry in parsed:
        file_existed, diff = (False, None)
        if repo_local_path:
            file_existed, diff = diff_against_existing(repo_local_path, entry["file_path"], entry["generated_code"])
        violations = check_rule_violations(db, entry["generated_code"], entry["language"])
        files.append(FileChange(
            file_path=entry["file_path"],
            language=entry["language"],
            generated_code=entry["generated_code"],
            explanation=entry["explanation"],
            file_existed=file_existed,
            diff=diff,
            rule_violations=violations,
        ))

    return MultiFileBuildResponse(files=files, model=model_name, tokens_used=tokens)


@router.post("/apply-multi", response_model=ApplyMultiResponse)
def apply_multi_file(
    req: ApplyMultiRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Batch version of /apply — writes every reviewed file, then one checkpoint
    commit covering all of them if commit_message is set."""
    from app.services.build_intel.file_ops import write_file

    if not req.files:
        raise HTTPException(status_code=400, detail="files must not be empty")

    repo = db.query(Repo).filter(Repo.id == req.repo_id).first()
    if not repo or repo.clone_status != "cloned" or not repo.local_path:
        raise HTTPException(status_code=400, detail="Repo is not cloned")

    written: list[str] = []
    for entry in req.files:
        try:
            write_file(repo.local_path, entry.file_path, entry.code)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"{entry.file_path}: {e}")
        written.append(entry.file_path)

    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="build_apply_multi",
        resource_id=req.repo_id,
        resource_type="repo",
        details={"file_paths": written},
    )

    committed = False
    commit_warning = None
    if req.commit_message:
        from app.routers.git_ops import GitCommitRequest, git_commit

        try:
            result = git_commit(GitCommitRequest(
                repo_path=repo.local_path, message=req.commit_message, files=written,
            ))
            committed = result.get("status") == "committed"
            if not committed:
                commit_warning = result.get("message", "commit did not complete")
        except HTTPException as e:
            commit_warning = str(e.detail)

    return ApplyMultiResponse(written=written, committed=committed, commit_warning=commit_warning)


@router.post("/verify-and-fix")
def verify_and_fix(
    req: VerifyAndFixRequest,
    current_user: CurrentUser = Depends(enforce_token_budget),
    db: Session = Depends(get_db),
):
    """Run the repo's real test/build command after applying Build's changes,
    auto-fixing on failure. Reuses autofix.py's existing run_and_fix loop
    (run → AI-analyze failure → apply fix → retry) against the actual cloned
    repo directory — this is the "iterate and verify" step, not a new loop.
    """
    from app.routers.autofix import AutoFixRequest, run_and_fix

    repo = db.query(Repo).filter(Repo.id == req.repo_id).first()
    if not repo or repo.clone_status != "cloned" or not repo.local_path:
        raise HTTPException(status_code=400, detail="Repo is not cloned")

    result = run_and_fix(AutoFixRequest(
        command=req.test_command,
        cwd=repo.local_path,
        max_retries=req.max_retries,
    ))

    log_audit(
        db=db,
        user_id=current_user.user_id,
        action="build_verify_and_fix",
        resource_id=req.repo_id,
        resource_type="repo",
        details={"command": req.test_command, "success": result.success, "attempts": result.total_attempts},
    )

    return result


@router.post("/from-plan", response_model=BuildFromPlanResponse)
def build_from_plan(
    req: BuildFromPlanRequest,
    current_user: CurrentUser = Depends(enforce_token_budget),
    db: Session = Depends(get_db),
):
    """Parse a plan into steps and generate code for the specified step."""
    client = _get_client()

    # First, parse the plan into discrete steps
    parse_prompt = (
        "Extract the implementation steps from this engineering plan. "
        "Return a JSON array of objects with 'title' and 'description' fields. "
        "Only return the JSON array, nothing else."
    )

    try:
        parse_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": parse_prompt},
                {"role": "user", "content": req.full_plan[:6000]},
            ],
            max_tokens=2000,
            temperature=0.1,
        )
        import json
        steps_text = parse_resp.choices[0].message.content or "[]"
        # Clean up potential markdown code fence
        if steps_text.startswith("```"):
            steps_text = steps_text.split("```")[1]
            if steps_text.startswith("json"):
                steps_text = steps_text[4:]
        steps = json.loads(steps_text.strip())
    except (json.JSONDecodeError, IndexError):
        steps = [{"title": "Implementation", "description": req.full_plan[:500]}]

    if not steps:
        steps = [{"title": "Implementation", "description": req.full_plan[:500]}]

    # Get the current step
    idx = min(req.step_index, len(steps) - 1)
    current_step = steps[idx]

    # Generate code for this step
    build_req = BuildRequest(
        plan_step=f"{current_step.get('title', '')}: {current_step.get('description', '')}",
        tech_stack=req.tech_stack,
        project_context=req.project_context,
    )
    result = generate_code(build_req, current_user=current_user, db=db)

    parse_tokens = parse_resp.usage.total_tokens if parse_resp.usage else 0
    log_tokens(
        action="build_parse_plan",
        feature="build_phase",
        model="gpt-4o-mini",
        prompt_tokens=parse_resp.usage.prompt_tokens if parse_resp.usage else 0,
        completion_tokens=parse_resp.usage.completion_tokens if parse_resp.usage else 0,
        total_tokens=parse_tokens,
        user_id=current_user.user_id,
    )

    return BuildFromPlanResponse(
        steps=steps,
        current_step=current_step,
        generated_code=result.generated_code,
        file_path=result.file_path,
        language=result.language,
        explanation=result.explanation,
        model=result.model,
        tokens_used=result.tokens_used + parse_tokens,
    )
