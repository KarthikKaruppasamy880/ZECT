"""Optional tree-sitter pass for Lattice (falls back to AST/regex in indexer).

Users never install Graphify. tree-sitter packages are optional; if missing,
`extract_symbols` returns [] and the AST/regex indexer remains authoritative.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_LANG_BY_EXT = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
}


def tree_sitter_available() -> bool:
    try:
        import tree_sitter  # noqa: F401
        return True
    except ImportError:
        return False


def extract_symbols(path: str, source: str | None = None) -> list[dict[str, Any]]:
    """Return [{kind, name, line}] using tree-sitter when grammars are installed."""
    if not tree_sitter_available():
        return []
    p = Path(path)
    lang_name = _LANG_BY_EXT.get(p.suffix.lower())
    if not lang_name:
        return []
    try:
        from tree_sitter import Language, Parser
    except ImportError:
        return []

    language = _load_language(lang_name)
    if language is None:
        return []
    text = source
    if text is None:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []
    parser = Parser(language)
    tree = parser.parse(text.encode("utf-8"))
    root = tree.root_node
    out: list[dict[str, Any]] = []
    _walk(root, text.encode("utf-8"), out, lang_name)
    return out


def _load_language(lang_name: str):
    """Try tree_sitter_* packages (optional deps)."""
    try:
        from tree_sitter import Language
    except ImportError:
        return None
    mapping = {
        "python": "tree_sitter_python",
        "javascript": "tree_sitter_javascript",
        "typescript": "tree_sitter_typescript",
        "tsx": "tree_sitter_typescript",
    }
    mod_name = mapping.get(lang_name)
    if not mod_name:
        return None
    try:
        mod = __import__(mod_name)
        if lang_name == "tsx" and hasattr(mod, "language_tsx"):
            return Language(mod.language_tsx())
        if lang_name == "typescript" and hasattr(mod, "language_typescript"):
            return Language(mod.language_typescript())
        if hasattr(mod, "language"):
            return Language(mod.language())
    except Exception:  # noqa: BLE001
        return None
    return None


def _walk(node, source: bytes, out: list[dict[str, Any]], lang: str) -> None:
    kind_map = {
        "function_definition": "function",
        "function_declaration": "function",
        "method_definition": "method",
        "class_definition": "class",
        "class_declaration": "class",
        "arrow_function": "function",
    }
    mapped = kind_map.get(node.type)
    if mapped:
        name = _node_name(node, source)
        if name:
            out.append({"kind": mapped, "name": name, "line": node.start_point[0] + 1})
    for child in node.children:
        _walk(child, source, out, lang)


def _node_name(node, source: bytes) -> str:
    for child in node.children:
        if child.type in ("identifier", "property_identifier", "type_identifier"):
            return source[child.start_byte : child.end_byte].decode("utf-8", errors="ignore")
        if child.type == "name":
            return source[child.start_byte : child.end_byte].decode("utf-8", errors="ignore")
    return ""
