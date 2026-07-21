"""AST / regex grounding — flag invented APIs not in allowlist."""

from __future__ import annotations

import ast
import builtins
import re
from typing import Any

# Common stdlib / builtins always allowed
_BUILTIN_NAMES = set(dir(builtins)) | {
    "self",
    "cls",
    "super",
    "print",
    "len",
    "range",
    "str",
    "int",
    "float",
    "list",
    "dict",
    "set",
    "tuple",
    "bool",
    "bytes",
    "object",
    "Exception",
    "ValueError",
    "TypeError",
    "KeyError",
    "AttributeError",
    "True",
    "False",
    "None",
    "Optional",
    "Any",
    "List",
    "Dict",
    "Promise",
    "console",
    "Math",
    "JSON",
    "Array",
    "Object",
    "Map",
    "Set",
    "Error",
    "require",
    "module",
    "exports",
    "window",
    "document",
}


def _idents_from_text(text: str) -> set[str]:
    return set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b", text or ""))


def build_allowlist(
    *,
    scout: dict | None = None,
    blueprint: dict | None = None,
    extra: list[str] | None = None,
) -> set[str]:
    allow = set(_BUILTIN_NAMES)
    for h in (scout or {}).get("graph_hits") or []:
        for key in ("name", "symbol", "path"):
            val = h.get(key) or ""
            if val:
                allow |= _idents_from_text(str(val).replace("/", " ").replace(".", " "))
                allow.add(str(val).split(".")[-1])
    bp = blueprint or {}
    allow |= _idents_from_text(bp.get("prompt") or "")
    allow |= _idents_from_text(bp.get("enhanced_prompt") or "")
    for path in bp.get("files_sampled") or []:
        allow |= _idents_from_text(str(path).replace("/", " ").replace(".", " "))
    contract = bp.get("design_contract") or {}
    for m in contract.get("required_mentions") or []:
        allow |= _idents_from_text(str(m))
    for name in extra or []:
        allow |= _idents_from_text(str(name))
    return allow


def _extract_python_defs(code: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return names
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _extract_python_calls(code: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return names
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _extract_regex_calls(code: str) -> set[str]:
    names = set(re.findall(r"\.([A-Za-z_][A-Za-z0-9_]*)\s*\(", code or ""))
    names |= set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", code or ""))
    names |= set(re.findall(r"(?:import|from|require)\s+['\"]?([A-Za-z_][A-Za-z0-9_.]*)", code or ""))
    return {n.split(".")[-1] for n in names if n}


def validate_grounding(
    code: str,
    *,
    language: str = "python",
    allowlist: set[str] | None = None,
    scout: dict | None = None,
    blueprint: dict | None = None,
) -> dict[str, Any]:
    """Return ok=False when call/attr names are not in allowlist (invented_api)."""
    allow = allowlist if allowlist is not None else build_allowlist(scout=scout, blueprint=blueprint)
    # Always allow names defined in the generated file itself (not calls)
    lang = (language or "python").lower()
    if lang in ("python", "py"):
        defined = _extract_python_defs(code)
        calls = _extract_python_calls(code)
    else:
        calls = _extract_regex_calls(code)
        defined = set(re.findall(r"(?:function|const|let|var|class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", code or ""))

    allow |= defined
    # Soft mode: only flag camelCase/PascalCase method-like unknowns with 2+ segments pattern
    invented: list[str] = []
    for name in sorted(calls):
        if name in allow:
            continue
        if name.startswith("_"):
            continue
        # Ignore very short / common noise
        if len(name) < 4:
            continue
        # Heuristic: invented APIs look like specific domain methods
        if re.search(r"[A-Z]", name) or name.endswith(("ById", "ByEmail", "Async", "Handler")):
            invented.append(name)
        elif name not in allow and name[0].islower() and "_" in name and len(name) > 8:
            # snake_case domain methods not in allowlist
            invented.append(name)

    findings = [
        {
            "severity": "high",
            "category": "invented_api",
            "message": f"Invented API call '{n}' not found in Lattice/blueprint allowlist",
            "suggestion": f"Use a symbol from reference/blueprint instead of inventing {n}",
        }
        for n in invented[:20]
    ]
    return {
        "ok": len(invented) == 0,
        "invented": invented[:20],
        "findings": findings,
        "allowlist_size": len(allow),
        "gate": "grounding",
    }
