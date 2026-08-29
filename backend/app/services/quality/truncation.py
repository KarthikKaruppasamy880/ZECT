"""Truncation-safe LLM generation — finish_reason=length continuation stitch."""

from __future__ import annotations

import ast
import re
from typing import Any, Callable


def brace_balance_ok(text: str) -> bool:
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack: list[str] = []
    in_str = False
    quote = ""
    escape = False
    for ch in text:
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_str = False
            continue
        if ch in ("'", '"'):
            in_str = True
            quote = ch
            continue
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in pairs.values():
            if not stack or stack.pop() != ch:
                return False
    return len(stack) == 0


def structural_ok(code: str, language: str = "python") -> dict[str, Any]:
    blockers: list[str] = []
    if not (code or "").strip():
        return {"ok": False, "blockers": ["empty_code"]}
    if not brace_balance_ok(code):
        blockers.append("brace_imbalance")
    lang = (language or "").lower()
    if lang in ("python", "py"):
        try:
            ast.parse(code)
        except SyntaxError as exc:
            blockers.append(f"ast_syntax:{exc.msg}")
    return {"ok": len(blockers) == 0, "blockers": blockers}


def stitch_continuation(base: str, cont: str) -> str:
    """Append continuation without repeating overlapping prefix."""
    base = base or ""
    cont = (cont or "").lstrip()
    if not cont:
        return base
    # Drop leading fence/language lines from continuation
    if cont.startswith("```"):
        parts = cont.split("```")
        if len(parts) >= 2:
            block = parts[1]
            lines = block.split("\n")
            if lines and re.match(r"^[a-zA-Z0-9_+-]+$", lines[0].strip()):
                lines = lines[1:]
            cont = "\n".join(lines).strip()
    overlap = min(80, len(base), len(cont))
    for n in range(overlap, 12, -1):
        if base.endswith(cont[:n]):
            return base + cont[n:]
    return base + ("\n" if base and not base.endswith("\n") else "") + cont


def complete_with_continuations(
    client: Any,
    *,
    messages: list[dict[str, str]],
    model: str = "gpt-4o-mini",
    max_tokens: int = 4000,
    temperature: float = 0.2,
    max_continuations: int = 3,
    language_hint: str = "python",
    create_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Call chat completions; if finish_reason=length, continue and stitch."""
    create = create_fn or (lambda **kwargs: client.chat.completions.create(**kwargs))
    msgs = list(messages)
    content = ""
    finish_reason = "stop"
    continuations = 0
    total_tokens = 0
    prompt_tokens = 0
    completion_tokens = 0

    for round_i in range(max_continuations + 1):
        resp = create(
            model=model,
            messages=msgs,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = resp.choices[0]
        chunk = choice.message.content or ""
        finish_reason = getattr(choice, "finish_reason", None) or "stop"
        if resp.usage:
            total_tokens += resp.usage.total_tokens or 0
            prompt_tokens += resp.usage.prompt_tokens or 0
            completion_tokens += resp.usage.completion_tokens or 0

        if round_i == 0:
            content = chunk
        else:
            content = stitch_continuation(content, chunk)
            continuations += 1

        if finish_reason != "length":
            break
        if round_i >= max_continuations:
            break
        seed = content[-800:] if len(content) > 800 else content
        msgs = list(messages) + [
            {"role": "assistant", "content": content},
            {
                "role": "user",
                "content": (
                    "Your previous response was truncated (finish_reason=length). "
                    "Continue verbatim from here; do not repeat earlier text.\n\n"
                    f"---TAIL---\n{seed}\n---END TAIL---"
                ),
            },
        ]

    # Prefer fenced code for structural checks when present
    code_for_check = content
    if "```" in content:
        parts = content.split("```")
        if len(parts) >= 2:
            block = parts[1]
            lines = block.split("\n")
            if lines and not lines[0].strip().startswith(
                ("import", "from", "const", "let", "var", "def", "class", "package", "#")
            ):
                lines = lines[1:]
            code_for_check = "\n".join(lines).strip()

    structure = structural_ok(code_for_check, language_hint)
    truncated = finish_reason == "length" or not structure["ok"]
    return {
        "content": content,
        "finish_reason": finish_reason,
        "continuations": continuations,
        "truncated": truncated and finish_reason == "length",
        "structure_ok": structure["ok"],
        "structure_blockers": structure["blockers"],
        "tokens_used": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "code_preview": code_for_check,
    }
