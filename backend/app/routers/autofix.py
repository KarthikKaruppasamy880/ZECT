"""Auto-Fix API — detect errors, AI-fix, re-run loop.

ZECT can detect errors from command output, generate AI fixes,
and re-run automatically.
"""

import os
import subprocess
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/autofix", tags=["autofix"])


# ── Models ────────────────────────────────────────────────────────────────

class AutoFixRequest(BaseModel):
    command: str
    cwd: str | None = None
    error_output: str | None = None  # If already have error output
    file_path: str | None = None
    file_content: str | None = None
    language: str | None = None
    max_retries: int = 3


class AutoFixStep(BaseModel):
    attempt: int
    action: str  # "run", "analyze", "fix", "success", "give_up"
    command: str | None = None
    error: str | None = None
    fix_description: str | None = None
    fix_code: str | None = None
    file_path: str | None = None
    output: str | None = None


class AutoFixResponse(BaseModel):
    success: bool
    total_attempts: int
    steps: list[AutoFixStep]
    final_output: str
    tokens_used: int


class AnalyzeErrorRequest(BaseModel):
    error_output: str
    command: str | None = None
    file_path: str | None = None
    file_content: str | None = None
    language: str | None = None


class AnalyzeErrorResponse(BaseModel):
    error_type: str
    root_cause: str
    suggested_fixes: list[dict]
    auto_fixable: bool
    confidence: str
    tokens_used: int


class ApplyFixRequest(BaseModel):
    file_path: str
    original_content: str
    fix_code: str
    fix_type: str  # "replace_file", "patch", "insert_line", "delete_line"
    line_number: int | None = None


# ── Helpers ───────────────────────────────────────────────────────────────

def _run_command(command: str, cwd: str | None = None, timeout: int = 60) -> dict:
    """Run a command and capture output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd or os.path.expanduser("~"),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": "Command timed out", "success": False}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e), "success": False}


def _ai_analyze_error(error_output: str, command: str = "", file_path: str = "", file_content: str = "", language: str = "") -> dict:
    """Use AI to analyze an error and suggest fixes."""
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        return {
            "error_type": "unknown",
            "root_cause": "Configure OpenAI API key for AI-powered error analysis",
            "suggested_fixes": [{"description": "Check error output manually", "code": None, "confidence": "low"}],
            "auto_fixable": False,
            "confidence": "low",
            "tokens_used": 0,
        }

    from openai import OpenAI
    client = OpenAI(api_key=key)

    context = f"Error Output:\n{error_output[:3000]}\n"
    if command:
        context += f"\nCommand: {command}"
    if file_path:
        context += f"\nFile: {file_path}"
    if language:
        context += f"\nLanguage: {language}"
    if file_content:
        context += f"\nFile Content:\n{file_content[:4000]}"

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": (
                "You are an expert debugger. Analyze the error and provide fixes.\n"
                "Return a JSON object with:\n"
                "- error_type: category (syntax, import, type, runtime, build, lint, test)\n"
                "- root_cause: one-line explanation\n"
                "- suggested_fixes: array of {description, code, file_path, confidence, fix_type}\n"
                "  fix_type: 'replace_file' | 'patch' | 'command'\n"
                "  code: the fixed code or command to run\n"
                "- auto_fixable: boolean\n"
                "- confidence: high/medium/low\n"
                "Return ONLY the JSON, no markdown."
            )},
            {"role": "user", "content": context},
        ],
        max_tokens=3000,
        temperature=0.1,
    )

    import json
    content = resp.choices[0].message.content or "{}"
    if "```" in content:
        parts = content.split("```")
        content = parts[1]
        if content.startswith("json"):
            content = content[4:]

    tokens = resp.usage.total_tokens if resp.usage else 0

    from app.token_tracker import log_tokens
    log_tokens(
        action="autofix_analyze",
        feature="autofix",
        model="gpt-4o-mini",
        prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
        completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
        total_tokens=tokens,
    )

    try:
        result = json.loads(content.strip())
        result["tokens_used"] = tokens
        return result
    except json.JSONDecodeError:
        return {
            "error_type": "unknown",
            "root_cause": "AI response could not be parsed",
            "suggested_fixes": [],
            "auto_fixable": False,
            "confidence": "low",
            "tokens_used": tokens,
        }


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeErrorResponse)
def analyze_error(req: AnalyzeErrorRequest):
    """Analyze an error and suggest fixes (without applying them)."""
    result = _ai_analyze_error(
        error_output=req.error_output,
        command=req.command or "",
        file_path=req.file_path or "",
        file_content=req.file_content or "",
        language=req.language or "",
    )
    return AnalyzeErrorResponse(
        error_type=result.get("error_type", "unknown"),
        root_cause=result.get("root_cause", "Unknown"),
        suggested_fixes=result.get("suggested_fixes", []),
        auto_fixable=result.get("auto_fixable", False),
        confidence=result.get("confidence", "low"),
        tokens_used=result.get("tokens_used", 0),
    )


@router.post("/run-and-fix", response_model=AutoFixResponse)
def run_and_fix(req: AutoFixRequest):
    """Run a command, detect errors, auto-fix, and retry (up to max_retries).

    This is the core auto-fix loop:
    1. Run the command
    2. If it fails, analyze the error with AI
    3. Apply the suggested fix
    4. Re-run the command
    5. Repeat until success or max retries
    """
    steps: list[AutoFixStep] = []
    total_tokens = 0

    for attempt in range(1, req.max_retries + 1):
        # Step 1: Run the command
        steps.append(AutoFixStep(
            attempt=attempt,
            action="run",
            command=req.command,
        ))

        if req.error_output and attempt == 1:
            # Use provided error output for first attempt
            run_result = {"exit_code": 1, "stdout": "", "stderr": req.error_output, "success": False}
        else:
            run_result = _run_command(req.command, req.cwd)

        output = run_result["stdout"] + run_result["stderr"]
        steps[-1].output = output[:2000]

        if run_result["success"]:
            steps.append(AutoFixStep(
                attempt=attempt,
                action="success",
                output=output[:2000],
            ))
            return AutoFixResponse(
                success=True,
                total_attempts=attempt,
                steps=steps,
                final_output=output,
                tokens_used=total_tokens,
            )

        # Step 2: Analyze the error
        steps.append(AutoFixStep(
            attempt=attempt,
            action="analyze",
            error=output[:2000],
        ))

        file_content = ""
        if req.file_path:
            try:
                from pathlib import Path
                file_content = Path(req.file_path).read_text(errors="replace")[:5000]
            except Exception:
                pass

        analysis = _ai_analyze_error(
            error_output=output,
            command=req.command,
            file_path=req.file_path or "",
            file_content=file_content or req.file_content or "",
            language=req.language or "",
        )
        total_tokens += analysis.get("tokens_used", 0)

        if not analysis.get("suggested_fixes"):
            steps.append(AutoFixStep(
                attempt=attempt,
                action="give_up",
                error="No fixes suggested by AI",
            ))
            break

        # Step 3: Apply the first suggested fix
        fix = analysis["suggested_fixes"][0]
        fix_desc = fix.get("description", "Unknown fix")
        fix_code = fix.get("code", "")
        fix_type = fix.get("fix_type", "")
        fix_file = fix.get("file_path", req.file_path)

        steps.append(AutoFixStep(
            attempt=attempt,
            action="fix",
            fix_description=fix_desc,
            fix_code=fix_code[:2000] if fix_code else None,
            file_path=fix_file,
        ))

        # Apply the fix
        if fix_type == "command" and fix_code:
            cmd_result = _run_command(fix_code, req.cwd)
            steps[-1].output = (cmd_result["stdout"] + cmd_result["stderr"])[:1000]
        elif fix_type == "replace_file" and fix_code and fix_file:
            try:
                from pathlib import Path
                Path(fix_file).write_text(fix_code)
                steps[-1].output = f"File {fix_file} updated"
            except Exception as e:
                steps[-1].output = f"Failed to write file: {e}"
        elif fix_type == "patch" and fix_code and fix_file:
            try:
                from pathlib import Path
                Path(fix_file).write_text(fix_code)
                steps[-1].output = f"File {fix_file} patched"
            except Exception as e:
                steps[-1].output = f"Failed to patch file: {e}"

    # If we get here, all retries exhausted
    steps.append(AutoFixStep(
        attempt=req.max_retries,
        action="give_up",
        error=f"Max retries ({req.max_retries}) exhausted",
    ))

    return AutoFixResponse(
        success=False,
        total_attempts=req.max_retries,
        steps=steps,
        final_output=steps[-2].output if len(steps) >= 2 else "No output",
        tokens_used=total_tokens,
    )


@router.post("/apply-fix")
def apply_fix(req: ApplyFixRequest):
    """Apply a specific fix to a file."""
    from pathlib import Path
    p = Path(req.file_path).resolve()
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if req.fix_type == "replace_file":
        p.write_text(req.fix_code)
        return {"status": "applied", "fix_type": "replace_file", "file": str(p)}
    elif req.fix_type == "insert_line" and req.line_number is not None:
        lines = p.read_text().split("\n")
        lines.insert(req.line_number - 1, req.fix_code)
        p.write_text("\n".join(lines))
        return {"status": "applied", "fix_type": "insert_line", "line": req.line_number}
    elif req.fix_type == "delete_line" and req.line_number is not None:
        lines = p.read_text().split("\n")
        if 0 < req.line_number <= len(lines):
            del lines[req.line_number - 1]
            p.write_text("\n".join(lines))
        return {"status": "applied", "fix_type": "delete_line", "line": req.line_number}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown fix_type: {req.fix_type}")
